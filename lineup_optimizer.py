import pandas as pd
import pulp
import requests

def load_players(sheet_url):
    data = requests.get(sheet_url).text
    df = pd.read_csv(pd.compat.StringIO(data))
    df.fillna(0, inplace=True)

    # Normalize column names
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Add idx for HTML checkboxes
    df["idx"] = range(len(df))

    # Ensure numeric fields are clean
    for col in ["projected_points", "salary", "usuage", "dvp"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df.to_dict(orient="records")

def solve_one(players, exclusion_sets):
    prob = pulp.LpProblem("NBA_Lineup", pulp.LpMaximize)
    positions = ["PG", "SG", "SF", "PF", "C", "G", "F", "UTIL"]

    x = {(p["idx"], s): pulp.LpVariable(f"x_{p['idx']}_{s}", cat="Binary")
         for p in players for s in positions}

    # Objective: Maximize projection weighted by DVP and usage
    prob += pulp.lpSum(
        x[p["idx"], s] * (
            p["projected_points"] + 0.1 * p.get("dvp", 0) + 0.05 * p.get("usuage", 0)
        )
        for p in players for s in positions
    )

    # Salary cap
    prob += pulp.lpSum(x[p["idx"], s] * p["salary"] for p in players for s in positions) <= 50000

    # One player per slot
    for s in positions:
        prob += pulp.lpSum(x[p["idx"], s] for p in players) == 1

    # Each player max once
    for p in players:
        prob += pulp.lpSum(x[p["idx"], s] for s in positions) <= 1

    # Solve
    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    selected = []
    for p in players:
        for s in positions:
            if pulp.value(x[p["idx"], s]) == 1:
                selected.append(p)
    return selected

def generate_top_k(players, k=10):
    results = []
    exclusion_sets = set()

    for i in range(k):
        sol = solve_one(players, exclusion_sets)
        if not sol:
            break
        total_proj = sum(p["projected_points"] for p in sol)
        total_salary = sum(p["salary"] for p in sol)
        results.append({
            "num": i + 1,
            "players": sol,
            "proj": round(total_proj, 2),
            "salary": total_salary
        })
        exclusion_sets.add(frozenset(p["idx"] for p in sol))
    return results
