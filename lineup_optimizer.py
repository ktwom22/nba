import pandas as pd
import requests
from io import StringIO
import pulp

def load_players(sheet_url):
    data = requests.get(sheet_url).text
    df = pd.read_csv(StringIO(data))
    df.columns = [c.strip() for c in df.columns]

    # Clean Salary
    df["Salary"] = df["Salary"].replace('[\$,]', '', regex=True).astype(float)

    # Ensure numeric columns
    for col in ["PROJECTED POINTS", "Usage"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    if "idx" not in df.columns:
        df["idx"] = df.index

    # Check required columns
    for col in ["Player", "Team"]:
        if col not in df.columns:
            raise ValueError(f"CSV must have '{col}' column")

    return df.to_dict(orient="records")


def solve_one(players, exclusion_set=None):
    if exclusion_set is None:
        exclusion_set = set()

    prob = pulp.LpProblem("LineupOptimization", pulp.LpMaximize)

    x = {}
    for p in players:
        if p.get("Include", True) and p["idx"] not in exclusion_set:
            x[p["idx"]] = pulp.LpVariable(f"x_{p['idx']}", cat="Binary")

    # Objective: maximize projected points
    prob += pulp.lpSum([x[p["idx"]] * p["PROJECTED POINTS"] for p in players if p["idx"] in x])

    # Salary cap
    prob += pulp.lpSum([x[p["idx"]] * p["Salary"] for p in players if p["idx"] in x]) <= 50000

    # Solve
    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    lineup = [p for p in players if x.get(p["idx"]) and x[p["idx"]].varValue > 0.5]
    total_proj = sum(p["PROJECTED POINTS"] for p in lineup)
    total_salary = sum(p["Salary"] for p in lineup)

    return {"lineup": lineup, "proj": total_proj, "salary": total_salary}


def generate_top_k(players, k=10):
    used_indices = set()
    top_lineups = []
    for _ in range(k):
        result = solve_one(players, exclusion_set=used_indices)
        top_lineups.append({
            "lineup": result["lineup"],
            "proj": result["proj"],
            "salary": result["salary"]
        })
        used_indices.update([p["idx"] for p in result["lineup"]])
    return top_lineups
