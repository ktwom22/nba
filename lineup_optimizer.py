import pandas as pd
import requests
from io import StringIO
import pulp

SALARY_CAP = 50000  # Adjust based on contest

def load_players(sheet_url):
    data = requests.get(sheet_url).text
    df = pd.read_csv(StringIO(data))
    df.columns = [c.strip() for c in df.columns]

    # Clean Salary column
    if "Salary" in df.columns:
        df["Salary"] = df["Salary"].replace('[\$,]', '', regex=True).astype(float)

    numeric_cols = ["PROJECTED POINTS", "Usage", "DVP", "Value"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    if "idx" not in df.columns:
        df["idx"] = df.index

    return df.to_dict(orient="records")

def solve_one(players, exclusion_sets=None):
    if exclusion_sets is None:
        exclusion_sets = []

    prob = pulp.LpProblem("LineupOptimization", pulp.LpMaximize)
    x = {(p["idx"], s): pulp.LpVariable(f"x_{p['idx']}_{s}", cat="Binary")
         for s in range(1) for p in players}

    # Objective: maximize projected points
    prob += pulp.lpSum(x[p["idx"], 0] * p["PROJECTED POINTS"] for p in players)

    # Salary cap
    prob += pulp.lpSum(x[p["idx"], 0] * p["Salary"] for p in players) <= SALARY_CAP

    # Only include players not excluded
    for ex_set in exclusion_sets:
        prob += pulp.lpSum(x[p["idx"], 0] for p in players if p["Player"] in ex_set) <= len(ex_set) - 1

    prob.solve(pulp.PULP_CBC_CMD(msg=0))
    lineup = [p for p in players if x[p["idx"], 0].varValue > 0.5]
    return lineup

def generate_top_k(players, k=10):
    lineups = []
    exclusion_sets = []
    for _ in range(k):
        lineup = solve_one(players, exclusion_sets)
        if not lineup:
            break
        lineups.append({
            "players": lineup,
            "total_salary": sum(p["Salary"] for p in lineup),
            "projected": sum(p["PROJECTED POINTS"] for p in lineup)
        })
        exclusion_sets.append([p["Player"] for p in lineup])
    return lineups
