import pulp

def solve_one(players, exclusion_sets):
    """
    Solves one optimized lineup using linear programming (Pulp).
    """
    # ✅ Fix 1: Clean player data to prevent NoneType errors
    for p in players:
        p["proj"] = float(p.get("proj") or 0)
        p["salary"] = float(p.get("salary") or 0)

    prob = pulp.LpProblem("DFS", pulp.LpMaximize)

    # Create binary variables for each player
    x = {p["idx"]: pulp.LpVariable(f"x_{p['idx']}", cat="Binary") for p in players}

    # ✅ Objective: maximize projected points (weighted if needed)
    prob += pulp.lpSum([p["proj"] * x[p["idx"]] for p in players]), "TotalProjectedPoints"

    # Salary cap constraint
    prob += pulp.lpSum([p["salary"] * x[p["idx"]] for p in players]) <= 50000, "SalaryCap"

    # Roster size constraint (8-player DK lineup)
    prob += pulp.lpSum([x[p["idx"]] for p in players]) == 8, "RosterSize"

    # Avoid reusing players from exclusion sets (to create variety)
    for excl in exclusion_sets:
        prob += pulp.lpSum([x[p["idx"]] for p in players if p["PLAYER"] in excl]) <= len(excl) - 1

    # ✅ Fix 2: use modern solver
    solver = pulp.PULP_CBC_CMD(msg=False)
    prob.solve(solver)

    lineup = [p for p in players if pulp.value(x[p["idx"]]) == 1]
    total_salary = sum(p["salary"] for p in lineup)
    total_proj = sum(p["proj"] for p in lineup)

    return lineup, total_salary, total_proj


def generate_top_k(players, k=10):
    """
    Generates top K unique lineups by re-solving with exclusion constraints.
    """
    top_lineups = []
    exclusion_sets = []

    for _ in range(k):
        lineup, salary, proj = solve_one(players, exclusion_sets)

        if not lineup:
            break

        top_lineups.append({
            "lineup": lineup,
            "salary": salary,
            "proj": proj
        })

        # Add current lineup to exclusion list to force variety
        exclusion_sets.append([p["PLAYER"] for p in lineup])

    return top_lineups
