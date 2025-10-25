import pandas as pd
import pulp
import requests
from io import StringIO

SALARY_CAP = 50000  # Default cap


def load_players(sheet_url):
    """Load player data from Google Sheet CSV."""
    data = requests.get(sheet_url).text
    df = pd.read_csv(StringIO(data))
    df.columns = [c.strip().lower() for c in df.columns]

    players = []
    for i, row in df.iterrows():
        try:
            players.append({
                "idx": i,
                "pos": str(row.get("pos") or row.get("position") or "").strip(),
                "player": str(row.get("player") or ""),
                "team": str(row.get("team") or ""),
                "opp": str(row.get("opp") or ""),
                "dvp": float(row.get("dvp") or 0),
                "projected_points": float(row.get("projected points") or row.get("proj") or 0),
                "usuage": float(row.get("usuage") or row.get("usage") or 0),
                "salary": float(str(row.get("salary") or "0").replace("$", "").replace(",", "")),
            })
        except Exception as e:
            print("Skipping player due to error:", e)
            continue

    return players


def solve_one(players, salary_cap=SALARY_CAP):
    """Solve one optimal lineup using linear programming."""
    # ✅ Assign idxs if missing (e.g., from UI POST)
    for i, p in enumerate(players):
        if "idx" not in p:
            p["idx"] = i

    roster_slots = ["PG", "SG", "SF", "PF", "C", "G", "F", "UTIL"]
    prob = pulp.LpProblem("NBA_Lineup", pulp.LpMaximize)

    # Decision variables
    x = {}
    for p in players:
        eligible_positions = str(p.get("pos", "")).split("/")
        for s in roster_slots:
            if s == "UTIL" or any(ep in s for ep in eligible_positions):
                x[(p["idx"], s)] = pulp.LpVariable(f"x_{p['idx']}_{s}", cat="Binary")

    # Objective: maximize weighted projection
    prob += pulp.lpSum(
        x[(p["idx"], s)] * (
            p.get("projected_points", 0)
            + 0.1 * p.get("dvp", 0)
            + 0.05 * p.get("usuage", 0)
        )
        for (p_idx, s), var in x.items()
        for p in players if p["idx"] == p_idx
    )

    # Constraints
    for s in roster_slots:
        prob += pulp.lpSum(x[p["idx"], s] for p in players if (p["idx"], s) in x) == 1
    for p in players:
        prob += pulp.lpSum(x[p["idx"], s] for s in roster_slots if (p["idx"], s) in x) <= 1
    prob += pulp.lpSum(
        x[p["idx"], s] * p["salary"]
        for p in players for s in roster_slots if (p["idx"], s) in x
    ) <= salary_cap

    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    selected = []
    for (p_idx, s), var in x.items():
        if pulp.value(var) == 1:
            p = next(pl for pl in players if pl["idx"] == p_idx)
            selected.append(p)

    total_salary = sum(p["salary"] for p in selected)
    if len(selected) != 8 or total_salary > salary_cap:
        return []

    unique_selected = {p["idx"]: p for p in selected}.values()
    return list(unique_selected)


def generate_top_k(players, k, salary_cap=SALARY_CAP):
    """Generate top k unique lineups."""
    all_lineups = []
    used_player_sets = []

    for _ in range(k):
        sol = solve_one(players, salary_cap)
        if not sol:
            break

        lineup_players = [p["player"] for p in sol]
        if lineup_players in used_player_sets:
            continue
        used_player_sets.append(lineup_players)

        total_proj = sum(p["projected_points"] for p in sol)
        total_salary = sum(p["salary"] for p in sol)

        all_lineups.append({
            "lineup": sol,
            "projected": round(total_proj, 2),
            "salary": total_salary
        })

    return all_lineups
