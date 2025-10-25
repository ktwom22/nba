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

    rename_map = {}
    for col in df.columns:
        c = col.strip().upper()
        if c == "POS": rename_map[col] = "POS"
        elif "PLAYER" in c: rename_map[col] = "PLAYER"
        elif "SALARY" in c: rename_map[col] = "SALARY"
        elif "PROJECTED" in c or "PROJ" in c: rename_map[col] = "PROJECTED"
        elif "DVP" in c: rename_map[col] = "DVP"
        elif "USAGE" in c: rename_map[col] = "USAGE"
    df = df.rename(columns=rename_map)

    df["SALARY"] = pd.to_numeric(df["SALARY"].replace({'\$':'', ',':''}, regex=True))
    df["PROJECTED"] = pd.to_numeric(df["PROJECTED"], errors="coerce")
    df["DVP"] = pd.to_numeric(df.get("DVP", 0))
    df["USAGE"] = pd.to_numeric(df.get("USAGE", 0))

    df = df[df["SALARY"] > 0]
    df = df[df["PROJECTED"] > 0]

    players = []
    for idx, row in df.iterrows():
        players.append({
            "idx": int(idx),
            "PLAYER": str(row["PLAYER"]),
            "POS": str(row["POS"]).upper(),
            "TEAM": row.get("TEAM",""),
            "SALARY": float(row["SALARY"]),
            "PROJECTED": float(row["PROJECTED"]),
            "DVP": float(row.get("DVP",0)),
            "USAGE": float(row.get("USAGE",0))
        })
    return players

def player_fits_slot(pos, slot):
    allowed = {
        "PG": ["PG"], "SG": ["SG"], "SF": ["SF"], "PF": ["PF"], "C": ["C"],
        "G": ["PG","SG"], "F": ["SF","PF"], "UTIL": ["PG","SG","SF","PF","C"]
    }
    return any(a in pos for a in allowed[slot])

def solve_one(players, exclusion_sets):
    prob = pulp.LpProblem("DK_Lineup", pulp.LpMaximize)
    x = {(p["idx"], s): pulp.LpVariable(f"x_{p['idx']}_{s}", cat="Binary")
         for p in players for s in SLOTS if player_fits_slot(p["POS"], s)}

    # Weight projected points by DVP and Usage
    prob += pulp.lpSum(x[i,s] * (p["PROJECTED"] + 0.1*p["DVP"] + 0.1*p["USAGE"])
                       for p in players for s in SLOTS if (i:=p["idx"], s) in x)

    for s in SLOTS:
        prob += pulp.lpSum(x[i,s] for p in players if (i:=p["idx"], s) in x) == 1

    for p in players:
        prob += pulp.lpSum(x[p["idx"],s] for s in SLOTS if (p["idx"], s) in x) <= 1

    prob += pulp.lpSum(x[i,s]*p["SALARY"] for p in players for s in SLOTS if (i:=p["idx"], s) in x) <= SALARY_CAP
    prob += pulp.lpSum(x[i,s] for p in players if p["SALARY"] < UNDER_4K_THRESHOLD
                       for s in SLOTS if (i:=p["idx"], s) in x) <= MAX_UNDER_4K

    for E in exclusion_sets:
        prob += pulp.lpSum(x[i,s] for i in E for s in SLOTS if (i,s) in x) <= len(E)-1

    solver = pulp.PULP_CBC_CMD(msg=False)
    result = prob.solve(solver)
    if pulp.LpStatus[result] != "Optimal": return None

    chosen = {s: next(p for p in players if p["idx"]==i) for (i,s), var in x.items() if pulp.value(var)==1}
    lineup = [chosen[s] for s in SLOTS]
    return {"lineup_players": lineup,
            "salary": sum(p["SALARY"] for p in lineup),
            "projected": sum(p["PROJECTED"] for p in lineup),
            "player_idxs": set(p["idx"] for p in lineup)}

def generate_top_k(players, k=10):
    exclusion_sets, results = [], []
    for _ in range(k):
        sol = solve_one(players, exclusion_sets)
        if not sol: break
        results.append(sol)
        exclusion_sets.append(sol["player_idxs"])
    return results
