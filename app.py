from flask import Flask, render_template, request
from lineup_optimizer import load_players, generate_top_k

app = Flask(__name__)

# ✅ Replace with your real CSV export URL from Google Sheets
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTF0d2pT0myrD7vjzsB2IrEzMa3o1lylX5_GYyas_5UISsgOud7WffGDxSVq6tJhS45UaxFOX_FolyT/pub?gid=324730904&single=true&output=csv"

@app.route("/")
def index():
    try:
        players = load_players(SHEET_URL)
    except Exception as e:
        print("Error loading players:", e)
        players = []
    return render_template("index.html", players=players)

@app.route("/optimize", methods=["POST"])
def optimize():
    try:
        included_players = request.form.getlist("include_player")
        count = request.form.get("player_count")
        count = int(count) if count else 10

        players = load_players(SHEET_URL)
        filtered = [p for p in players if str(p["idx"]) in included_players]

        results = generate_top_k(filtered, count)
        return render_template("results.html", lineups=results)
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
