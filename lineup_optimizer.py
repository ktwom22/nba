# lineup_optimizer.py
import pandas as pd
import pulp
import requests
import io
import csv

SLOTS = ["PG", "SG", "SF", "PF", "C", "G", "F", "UTIL"]
SALARY_CAP = 50000
UNDER_4K_THRESHOLD = 4000
MAX_UNDER_4K = 2

def load_players(sheet_url):
    """Load and clean player data from Google Sheet CSV with DVP and Usage."""
    data = requests.get(sheet_url).text
    lines = data.strip().splitlines()
    reader = csv.reader(lines)

    header_idx = None
    for i, row in enumerate(reader):
        joined = " ".join(row).upper()
        if "PLAYER" in joined and "POS" in joined:
            header_idx = i
            break
    if header_idx is None:
        raise RuntimeError("Couldn't find header row in CSV")

    df = pd.read_csv(io.StringIO(data), skiprows=header_idx)

    # Standardize column names
    rename_map = {}
    for col in df.columns:
        c = col.strip().upper()
        if c == "POS":
            rename_map[col] = "POS"
        elif "PLAYER" in c:
            rename_map[col] = "PLAYER"
        elif "SALARY" in c:
            rename_map[col] = "Salary"
        elif "PROJECTED" in c or "PROJ" in c:
            rename_map[col] = "PROJECTED POINTS"
        elif "DVP" in c:
            rename_map[col] = "DVP"
        elif "USUAGE" in c or "USAGE" in c:
            rename_map[col] = "USUAGE"

    df = df.rename(columns=rename_map)

    # Clean numeric columns
    df["Salary"] = df["Salary"].apply(
        lambda v: float(str(v).replace("$", "").replace(",", "").strip()) if pd.notna(v) else 0
    )
    df["PROJECTED POINTS"] = pd.to_numeric(df["PROJECTED POINTS"], errors="coerce")
    df["DVP"] = pd.to_numeric(df.get("DVP", 0), errors="coerce").fillna(0)
    df["USUAGE"] = pd.to_numeric(df.get("USUAGE", 0), errors="coerce").fillna(0)

    df = df[df["Salary"] > 0]
    df = df[df["PROJECTED POINTS"] > 0]

    # Normalize DVP and Usage for weighting
    max_dvp = df["DVP"].max() if not df["DVP"].empty else 1
    max_usage = df["USUAGE"].max() if not df["USUAGE"].empty else 1

    players = []
    for idx, row in df.iterrows():
        players.append({
            "idx": int(idx),
            "PLAYER": str(row["PLAYER"]),
            "POS": str(row["POS"]).upper(),
            "SALARY": float(row["Salary"]),
            "PROJECTED": float(row["PROJECTED POINTS"]),
            "DVP_NORM": float(row["DVP"]) / max_dvp,
            "USAGE_NORM": float(row["USUAGE"]) / max_usage
        })
    return players

def player_fits_slot(pos, slot):
    allowed = {
        "PG": ["PG"],
        "SG": ["SG"],
        "SF": ["SF"],
        "PF": ["PF"],
        "C": ["C"],
        "G": ["PG", "SG"],
        "F": ["SF", "PF"],
        "UTIL": ["PG", "SG", "SF", "PF", "C"]
    }
    return any(a in pos for a in allowed[slot])

def weighted_proj(player, dvp_weight=0.5, usage_weight=0.5):
    """
    Combines original projected points with DVP and Usage.
    Higher DVP and Usage increase effective projected points.
    """
    return player["PROJECTED"] + dvp_weight * player["DVP_NORM"] + usage_weight * player["USAGE_NORM"]

def solve_one(players, exclusion_sets):
    prob = pulp.LpProblem("DK_Lineup", pulp.LpMaximize)
    x = {(p["idx"], s): pulp.LpVariable(f"x_{p['idx']}_{s}", cat="Binary")
         for p in players for s in SLOTS if player_fits_slot(p["POS"], s)}

    # Objective: maximize weighted projected points
    prob += pulp.lpSum(x[i, s] * weighted_proj(p)
                       for p in players for s in SLOTS if (i := p["idx"], s) in x)

    # One player per slot
    for s in SLOTS:
        prob += pulp.lpSum(x[i, s] for p in players if (i := p["idx"], s) in x) == 1

    # Player only once per lineup
    for p in players:
        prob += pulp.lpSum(x[p["idx"], s] for s in SLOTS if (p["idx"], s) in x) <= 1

    # Salary cap
    prob += pulp.lpSum(x[i, s] * p["SALARY"]
                       for p in players for s in SLOTS if (i := p["idx"], s) in x) <= SALARY_CAP

    # Max players under $4k
    prob += pulp.lpSum(x[i, s] for p in players if p["SALARY"] < UNDER_4K_THRESHOLD
                       for s in SLOTS if (i := p["idx"], s) in x) <= MAX_UNDER_4K

    # Exclusion sets to prevent duplicate lineups
    for E in exclusion_sets:
        prob += pulp.lpSum(x[i, s] for i in E for s in SLOTS if (i, s) in x) <= len(E) - 1

    solver = pulp.PULP_CBC_CMD(msg=False)
    result = prob.solve(solver)
    if pulp.LpStatus[result] != "Optimal":
        return None

    # Build the lineup
    chosen = {s: next(p for p in players if p["idx"] == i)
              for (i, s), var in x.items() if pulp.value(var) == 1}

    lineup = [chosen[s] for s in SLOTS]
    return {
        "lineup_players": lineup,
        "salary": sum(p["SALARY"] for p in lineup),
        "projected": sum(p["PROJECTED"] for p in lineup),
        "player_idxs": set(p["idx"] for p in lineup)
    }

def generate_top_k(players, k=10):
    exclusion_sets, results = [], []
    for _ in range(k):
        sol = solve_one(players, exclusion_sets)
        if not sol:
            break
        results.append(sol)
        exclusion_sets.append(sol["player_idxs"])
    return results
