import pulp
import pandas as pd
import requests
from io import StringIO

# Load and clean players
def load_players(sheet_url):
    data = requests.get(sheet_url).text
    df = pd.read_csv(StringIO(data))
    df.columns = [c.strip() for c in df.columns]

    # Fill missing numeric fields
    numeric_cols = ["PROJECTED POINTS", "Salary", "Usage", "DVP", "Value"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Ensure idx column exists
    if "idx" not in df.columns:
        df["idx"] = df.index

    return df.to_dict(orient="records")

# Build a single optimized lineup
def solve_one(players):
    model = pulp.LpProblem("NBA_Optimizer", pulp.LpMaximize)

    # Decision variable: x[p] = 1 if player is selected
    x = {p["idx"]: pulp.LpVariable(f"x_{p['idx']}", cat="Binary") for p in players}

    # Objective: maximize projected + DVP + usage bonus
    model += pulp.lpSum(
        x[p["idx"]] * (
            p["PROJECTED POINTS"]
            + 0.1 * p["DVP"]
            + 0.5 * p["Usage"]
        ) for p in players
    )

    # Constraints
    model += pulp.lpSum(x[p["idx"]] * p["Salary"] for p in players) <= 50000
    model += pulp.lpSum(x[p["idx"]] for p in players) == 8

    model.solve(pulp.PulpSolverDefault)

    lineup = [p for p in players if x[p["idx"]].value() == 1]
    total_salary = sum(p["Salary"] for p in lineup)
    total_proj = sum(p["PROJECTED POINTS"] for p in lineup)

    return {"players": lineup, "salary": total_salary, "proj": round(total_proj, 1)}

def generate_top_k(players, k):
    lineups = []
    used_ids = set()

    for i in range(k):
        lineup = solve_one(players)
        if not lineup:
            break
        lineup["num"] = i + 1
        lineups.append(lineup)

        # Exclude selected players from next run
        used_ids.update(p["idx"] for p in lineup["players"])
        players = [p for p in players if p["idx"] not in used_ids]

        if len(players) < 8:
            break

    return lineups
