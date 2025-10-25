import pandas as pd
import pulp


def load_players(csv_url):
    df = pd.read_csv(csv_url)
    df.fillna(0, inplace=True)  # replace missing numbers with 0
    df.reset_index(inplace=True)
    df.rename(columns={"index": "idx"}, inplace=True)
    return df.to_dict(orient="records")

def load_players(csv_url):
    # Load CSV
    df = pd.read_csv(csv_url)

    # Strip spaces in column names
    df.columns = [c.strip().replace(" ", "_") for c in df.columns]

    # Ensure numeric columns are properly converted
    def clean_num(x):
        if pd.isna(x):
            return 0.0
        if isinstance(x, str):
            x = x.replace("$", "").replace(",", "").strip()
        try:
            return float(x)
        except:
            return 0.0

    # Convert numeric columns
    for col in ["Salary", "Usage", "PROJECTED_POINTS"]:
        if col in df.columns:
            df[col] = df[col].apply(clean_num)
        else:
            df[col] = 0.0

    # Add unique index for optimizer
    df.reset_index(inplace=True)
    df.rename(columns={"index": "idx"}, inplace=True)

    # Convert to list of dicts for your optimizer
    return df.to_dict(orient="records")



# Generate optimized lineups
def generate_top_k(players, k=10):
    try:
        results = []
        exclusion_sets = []

        for i in range(k):
            sol = solve_one(players, exclusion_sets)
            if sol:
                results.append(sol)
                exclusion_sets.append([p["PLAYER"] for p in sol["players"]])
            else:
                break

        return results
    except Exception as e:
        return {"error": str(e)}


# Solve one lineup
def solve_one(players, exclusion_sets):
    prob = pulp.LpProblem("LineupOptimization", pulp.LpMaximize)

    # Variables: one binary per player
    x = {p["idx"]: pulp.LpVariable(f"x_{p['idx']}", cat="Binary") for p in players}

    # Objective: maximize projected points (weighted by usage)
    prob += pulp.lpSum(
        x[p["idx"]] * (p.get("PROJECTED_POINTS", 0) or 0) * (1 + (p.get("Usage", 0) or 0) / 100)
        for p in players
    )

    # Salary cap
    prob += pulp.lpSum(x[p["idx"]] * (p.get("Salary", 0) or 0) for p in players) <= 50000

    # Roster size
    prob += pulp.lpSum(x[p["idx"]] for p in players) == 8

    # Exclude already chosen lineups
    for excl in exclusion_sets:
        prob += pulp.lpSum(x[p["idx"]] for p in players if p["PLAYER"] in excl) <= len(excl) - 1

    prob.solve(pulp.PULP_CBC_CMD(msg=False))

    chosen = [p for p in players if pulp.value(x[p["idx"]]) == 1]
    if not chosen:
        return None

    total_salary = sum(p.get("Salary", 0) or 0 for p in chosen)
    total_points = sum(p.get("PROJECTED_POINTS", 0) or 0 for p in chosen)

    return {"players": chosen, "salary": total_salary, "projected": total_points}
