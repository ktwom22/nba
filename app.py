from flask import Flask, render_template, request
from lineup_optimizer import load_players, generate_top_k

app = Flask(__name__)

# 🔗 Replace this with your real Google Sheet CSV link
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTF0d2pT0myrD7vjzsB2IrEzMa3o1lylX5_GYyas_5UISsgOud7WffGDxSVq6tJhS45UaxFOX_FolyT/pub?gid=324730904&single=true&output=csv"

@app.route("/")
def index():
    try:
        players = load_players(SHEET_URL)
    except Exception as e:
        players = []
        print("Error loading players:", e)
    return render_template("index.html", players=players)

@app.route("/optimize", methods=["POST"])
def optimize():
    import json
    player_data = request.form.get("players")
    count = int(request.form.get("player_count", 10))
    players = json.loads(player_data)
    results = generate_top_k(players, count)
    return render_template("results.html", lineups=results)

if __name__ == "__main__":
    app.run(debug=True)
