from flask import Flask, render_template, request
from lineup_optimizer import load_players, generate_top_k

app = Flask(__name__)

# Example Google Sheet CSV URL
SHEET_URL = "YOUR_GOOGLE_SHEET_CSV_URL"

@app.route("/")
def index():
    players = load_players(SHEET_URL)
    # Add a 'slot' field for table display/editing
    for p in players:
        p['slot'] = ""
    return render_template("players.html", players=players)

@app.route("/optimize", methods=["POST"])
def optimize():
    try:
        count = int(request.form.get("player_count") or 10)
    except ValueError:
        count = 10

    # Rebuild players list from table data
    players = []
    idxs = request.form.getlist("idx")
    names = request.form.getlist("name")
    positions = request.form.getlist("pos")
    salaries = request.form.getlist("salary")
    projected_points = request.form.getlist("proj")
    usage = request.form.getlist("usage")
    dvp = request.form.getlist("dvp")

    for i in range(len(names)):
        try:
            players.append({
                "idx": int(idxs[i]),
                "PLAYER": names[i],
                "POS": positions[i].upper(),
                "SALARY": float(salaries[i]),
                "PROJECTED": float(projected_points[i]),
                "USAGE": float(usage[i]) if usage[i] else 0,
                "DVP": float(dvp[i]) if dvp[i] else 0
            })
        except Exception:
            continue

    lineups = generate_top_k(players, k=count)

    # Format lineups for template
    formatted = []
    for num, l in enumerate(lineups, 1):
        formatted.append({
            "num": num,
            "salary": l["salary"],
            "proj": l["projected"],
            "players": [
                {
                    "slot": s,
                    "name": p["PLAYER"],
                    "pos": p["POS"],
                    "salary": p["SALARY"],
                    "proj": p["PROJECTED"]
                } for s, p in zip(["PG","SG","SF","PF","C","G","F","UTIL"], l["lineup_players"])
            ]
        })
    return render_template("lineups.html", lineups=formatted)

if __name__ == "__main__":
    app.run(debug=True)
