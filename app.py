from flask import Flask, render_template, request
from lineup_optimizer import load_players, generate_top_k
import os

app = Flask(__name__)
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTF0d2pT0myrD7vjzsB2IrEzMa3o1lylX5_GYyas_5UISsgOud7WffGDxSVq6tJhS45UaxFOX_FolyT/pub?gid=324730904&single=true&output=csv"

@app.route("/", methods=["GET"])
def player_pool():
    players = load_players(SHEET_URL)
    return render_template("player_pool.html", players=players)

@app.route("/optimize", methods=["POST"])
def optimize():
    count = int(request.form.get("player_count"))
    players = []
    for i in range(count):
        if request.form.get(f"include_{i}"):
            players.append({
                "idx": i,  # <-- add unique index
                "PLAYER": request.form[f"player_{i}"],
                "POS": request.form[f"pos_{i}"],
                "TEAM": request.form[f"team_{i}"],
                "SALARY": float(request.form[f"salary_{i}"]),
                "PROJECTED": float(request.form[f"proj_{i}"]),
                "DVP": float(request.form.get(f"dvp_{i}", 0)),
                "USAGE": float(request.form.get(f"usage_{i}", 0))
            })

    if len(players) < 8:
        return "<h3>❌ Not enough players selected.</h3>"

    results = generate_top_k(players, 10)
    formatted = []
    for i,r in enumerate(results,1):
        formatted.append({
            "num": i,
            "salary": int(r["salary"]),
            "proj": round(r["projected"],2),
            "players":[
                {"slot": slot, "name": p["PLAYER"], "pos": p["POS"],
                 "salary": int(p["SALARY"]), "proj": round(p["PROJECTED"],1)}
                for slot, p in zip(["PG","SG","SF","PF","C","G","F","UTIL"], r["lineup_players"])
            ]
        })
    return render_template("lineups.html", lineups=formatted)

if __name__ == "__main__":
    port = int(os.environ.get("PORT",5000))
    app.run(debug=True, host="0.0.0.0", port=port)
