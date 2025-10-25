from flask import Flask, render_template, request
from lineup_optimizer import load_players, generate_top_k
import os

app = Flask(__name__)

SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTF0d2pT0myrD7vjzsB2IrEzMa3o1lylX5_GYyas_5UISsgOud7WffGDxSVq6tJhS45UaxFOX_FolyT/pub?gid=324730904&single=true&output=csv"

@app.route("/")
def home():
    return """
    <h2>🏀 NBA DraftKings Lineup Optimizer</h2>
    <form action='/optimize'>
        <label>Number of lineups (1–50): </label>
        <input type='number' name='n' value='5' min='1' max='50'/>
        <button type='submit'>Optimize</button>
    </form>
    """

@app.route("/optimize")
def optimize():
    n = int(request.args.get("n", 5))
    players = load_players(SHEET_URL)
    if len(players) < 8:
        return "<h3>❌ Not enough players loaded from sheet.</h3>"

    results = generate_top_k(players, n)
    if not results:
        return "<h3>⚠️ No feasible lineups found.</h3>"

    formatted = []
    for i, r in enumerate(results, 1):
        formatted.append({
            "num": i,
            "salary": int(r["salary"]),
            "proj": round(r["projected"], 2),
            "players": [
                {
                    "slot": slot,
                    "name": p["PLAYER"],
                    "pos": p["POS"],
                    "salary": int(p["SALARY"]),
                    "proj": round(p["PROJECTED"], 1)
                }
                for slot, p in zip(["PG","SG","SF","PF","C","G","F","UTIL"], r["lineup_players"])
            ]
        })

    return render_template("lineups.html", lineups=formatted)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
