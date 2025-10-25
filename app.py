from flask import Flask, render_template, request, jsonify
from lineup_optimizer import load_players, generate_top_k

app = Flask(__name__)

SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTF0d2pT0myrD7vjzsB2IrEzMa3o1lylX5_GYyas_5UISsgOud7WffGDxSVq6tJhS45UaxFOX_FolyT/pub?gid=324730904&single=true&output=csv"

@app.route("/")
def index():
    try:
        players = load_players(SHEET_URL)
    except Exception as e:
        return f"Error loading players: {e}"
    return render_template("index.html", players=players)

@app.route("/optimize", methods=["POST"])
def optimize():
    try:
        data = request.get_json()
        players = data.get("players", [])
        count = int(data.get("player_count", 10))
        results = generate_top_k(players, count)
        return jsonify({"lineups": results})
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
