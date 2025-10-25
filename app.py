from flask import Flask, render_template, request
from lineup_optimizer import load_players, generate_top_k

app = Flask(__name__)

# ⚠️ Replace this with your actual public Google Sheet CSV export URL
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTF0d2pT0myrD7vjzsB2IrEzMa3o1lylX5_GYyas_5UISsgOud7WffGDxSVq6tJhS45UaxFOX_FolyT/pub?gid=324730904&single=true&output=csv"

@app.route("/")
def index():
    try:
        players = load_players(SHEET_URL)
        return render_template("index.html", players=players)
    except Exception as e:
        return f"Error loading players: {e}"

@app.route("/optimize", methods=["POST"])
def optimize():
    try:
        included_ids = request.form.getlist("include_player")
        all_players = load_players(SHEET_URL)

        # Only include players that are checked
        selected_players = [p for p in all_players if str(p["idx"]) in included_ids]
        if not selected_players:
            selected_players = all_players

        num_lineups = int(request.form.get("num_lineups", 10))
        results = generate_top_k(selected_players, num_lineups)

        return render_template("results.html", lineups=results)
    except Exception as e:
        return f"Error optimizing: {e}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
