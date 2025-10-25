import io
import requests
import pandas as pd
import pulp


# ✅ Load players from Google Sheet CSV
def load_players(sheet_url):
    """
    Loads player data from a Google Sheet (CSV export link).
    Returns a list of player dicts used for optimization.
    """
    try:
        csv_data = requests.get(sheet_url).text
        df = pd.read_csv(io.StringIO(csv_data))

        # Normalize column names
        df.columns = [c.strip().upper() for c in df.columns]

        # Ensure salary and projection are numeric
        if "SALARY" in df.columns:
            df["SALARY"] = (
                df["SALARY"]
                .astype(str)
                .str.replace(r"[\$,]", "", regex=True)
                .astype(float)
            )

        if "PROJECTED POINTS" in df.columns:
            df["PROJ"] = df["PROJECTED POINTS"].astype(float)
        elif "PROJ" not in df.columns:
            df["PROJ"] = 0.0

        # Ensure required columns exist
        if "PLAYER" not in df.columns:
            df["PLAYER"] = df.index.astype(str)
        if "TEAM" not in df.columns:
            df["TEAM"] = "UNK"
        if "USAGE" not in df.columns:
            df["USAGE"] = 0.0

        # Add an index for solver variable naming
        df["idx"] = range(len(df))

        players = df.to_dict(orient="records")
        return players
    except Exception as e:
        print(f"Error loading players: {e}")
        return []


# ✅ Solve one lineup
def solve_one(players, exclusion_sets):
    for p in players:
        p["proj"] = float(p.get("proj") or 0)
        p["salary"] = float(p.get("salary") or 0)

    prob = pulp.LpProblem("DFS", pulp.LpMaximize)
    x = {p["idx"]: pulp.LpVariable(f"x_{p['idx']}", cat="Binary") for p in players}

    prob += pulp.lpSum([p["proj"] * x[p["idx"]] for p in players]), "TotalProjectedPoints"
    prob += pulp.lpSum([p["salary"] * x[p["idx"]] for p in players]) <= 50000, "SalaryCap"
    prob += pulp.lpSum([x[p["idx"]] for p in players]) == 8, "RosterSize"

    for excl in exclusion_sets:
        prob += pulp.lpSum([x[p["idx"]] for p in players if p["PLAYER"] in excl]) <= len(excl) - 1

    solver = pulp.PULP_CBC_CMD(msg=False)
    prob.solve(solver)

    lineup = [p for p in players if pulp.value(x[p["idx"]]) == 1]
    total_salary = sum(p["salary"] for p in lineup)
    total_proj = sum(p["proj"] for p in lineup)
    return lineup, total_salary, total_proj


# ✅ Generate multiple unique lineups
def generate_top_k(players, k=10):
    top_lineups = []
    exclusion_sets = []
    for _ in range(k):
        lineup, salary, proj = solve_one(players, exclusion_sets)
        if not lineup:
            break
        top_lineups.append({"lineup": lineup, "salary": salary, "proj": proj})
        exclusion_sets.append([p["PLAYER"] for p in lineup])
    return top_lineups
