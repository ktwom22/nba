import pandas as pd
import pulp
import requests
from io import StringIO

SALARY_CAP = 50000

def load_players(sheet_url):
    data = requests.get(sheet_url).text
    df = pd.read_csv(StringIO(data))

    # Normalize columns
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Clean salary field ✅
    if "salary" in df.columns:
        df["salary"] = df["salary"].astype(str).replace({"[$,]": ""}, regex=True)
        df["salary"] = pd.to_numeric(df["salary"], errors="coerce").fillna(0)

    # Ensure numeric columns exist
    for col in ["projected_points", "usuage", "dvp"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["idx"] = range(len(df))
    df.fillna("", inplace=True)
    return df.to_dict(orient="records")

def solve_one(players):
    positions = ["PG", "SG", "SF", "PF", "C", "G", "F", "UTIL"]
    prob = pulp.LpProblem("NBA_Lineup", pulp.LpMaximize)

    x = {(p["idx"], s): pulp.LpVariable(f"x_{p['idx']}_{s}", cat="Binary")
         for p in players for s in positions}

    # Objective weighted by DVP and usage
    prob += pulp.lpSum(
        x[p["idx"], s] * (
            p.get("projected_points", 0)
            + 0.1 * p.get("dvp", 0)
            + 0.05 * p.get("usuage", 0)
        )
        for p in players for s in positions
    )

    # Constraints
    for s in positions:
        prob += pulp.lpSum(x[p["idx"], s] for p in players) == 1
    for p in players:
        prob += pulp.lpSum(x[p["idx"], s] for s in positions) <= 1

    prob += pulp.lpSum(x[p["idx"], s] * p["salary"]
                       for p in players for s in positions) <= SALARY_CAP

    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    selected = []
    for p in players:
        for s in positions:
            if pulp.value(x[p["idx"], s]) == 1:
                selected.append(p)
    return selected

def generate_top_k(players, k=10):
    results = []
    seen = set()

    for i in range(k):
        sol = solve_one(players)
        if not sol:
            break
        ids = tuple(sorted(p["idx"] for p in sol))
        if ids in seen:
            break
        seen.add(ids)
        total_proj = sum(p["projected_points"] for p in sol)
        total_salary = sum(p["salary"] for p in sol)
        results.append({
            "num": i + 1,
            "players": sol,
            "proj": round(total_proj, 2),
            "salary": total_salary
        })
    return results
