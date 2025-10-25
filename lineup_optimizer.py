# lineup_optimizer.py
import pulp
import requests
import csv
from io import StringIO

SLOTS = ["PG", "SG", "SF", "PF", "C", "G", "F", "UTIL"]
SALARY_CAP = 50000
UNDER_4K_THRESHOLD = 4000
MAX_UNDER_4K = 2

def load_players(sheet_url):
    """Load and clean player data from Google Sheet CSV without pandas."""
    data = requests.get(sheet_url).text
    lines = data.strip().splitlines()
    reader = csv.reader(lines)

    # find header row
    header_idx = None
    for i, row in enumerate(reader):
        joined = " ".join(row).upper()
        if "PLAYER" in joined and "POS" in joined:
            header_idx = i
            break
    if header_idx is None:
        raise RuntimeError("Couldn't find header row in CSV")

    rows = list(csv.reader(lines))
    headers = rows[header_idx]
    players = []

    for row in rows[header_idx + 1:]:
        row_dict = dict(zip(headers, row))
        try:
            name = row_dict.get("PLAYER") or row_dict.get("Player")
            pos = (row_dict.get("POS") or row_dict.get("Pos") or "").upper()
            salary_raw = row_dict.get("SALARY") or row_dict.get("Salary") or "0"
            salary = float(salary_raw.replace("$", "").replace(",", "").strip())
            proj_raw = row_dict.get("PROJECTED POINTS") or row_dict.get("Proj") or "0"
            projected = float(proj_raw.strip())
        except Exception:
            continue
        if salary > 0 and projected > 0:
            players.append({
                "idx": len(players),
                "PLAYER": name,
                "POS": pos,
                "SALARY": salary,
                "PROJECTED": projected
            })
    return players

def player_fits_slot(pos, slot):
    allowed = {
        "PG": ["PG"],
        "SG": ["SG"],
        "SF": ["SF"],
        "PF": ["PF"],
        "C": ["C"],
        "G": ["PG", "SG"],
        "F": ["SF", "PF"],
        "UTIL": ["PG", "SG", "SF", "PF", "C"]
    }
    return any(a in pos for a in allowed[slot])

def solve_one(players, exclusion_sets):
    prob = pulp.LpProblem("DK_Lineup", pulp.LpMaximize)
    x = {(p["idx"], s): pulp.LpVariable(f"x_{p['idx']}_{s}", cat="Binary")
         for p in players for s in SLOTS if player_fits_slot(p["POS"], s)}

    prob += pulp.lpSum(x[i, s] * p["PROJECTED"]
                       for p in players for s in SLOTS if (i := p["idx"], s) in x)

    # exactly one player per slot
    for s in SLOTS:
        prob += pulp.lpSum(x[i, s] for p in players if (i := p["idx"], s) in x) == 1

    # a player only in one slot
    for p in players:
        prob += pulp.lpSum(x[p["idx"], s] for s in SLOTS if (p["idx"], s) in x) <= 1

    # salary cap
    prob += pulp.lpSum(x[i, s] * p["SALARY"]
                       for p in players for s in SLOTS if (i := p["idx"], s) in x) <= SALARY_CAP

    # max under $4k
    prob += pulp.lpSum(x[i, s] for p in players if p["SALARY"] < UNDER_4K_THRESHOLD
                       for s in SLOTS if (i := p["idx"], s) in x) <= MAX_UNDER_4K

    # exclude previous lineups
    for E in exclusion_sets:
        prob += pulp.lpSum(x[i, s] for i in E for s in SLOTS if (i, s) in x) <= len(E) - 1

    solver = pulp.PULP_CBC_CMD(msg=False)
    result = prob.solve(solver)
    if pulp.LpStatus[result] != "Optimal":
        return None

    chosen = {s: next(p for p in players if p["idx"] == i)
              for (i, s), var in x.items() if pulp.value(var) == 1}

    lineup = [chosen[s] for s in SLOTS]
    return {
        "lineup_players": lineup,
        "salary": sum(p["SALARY"] for p in lineup),
        "projected": sum(p["PROJECTED"] for p in lineup),
        "player_idxs": set(p["idx"] for p in lineup)
    }

def generate_top_k(players, k=10):
    exclusion_sets, results = [], []
    for _ in range(k):
        sol = solve_one(players, exclusion_sets)
        if not sol:
            break
        results.append(sol)
        exclusion_sets.append(sol["player_idxs"])
    return results
