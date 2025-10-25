from flask import Flask, render_template, request, jsonify
from lineup_optimizer import load_players, generate_top_k, SALARY_CAP

app = Flask(__name__)

# 👇 Replace this with your published Google Sheet CSV link
SHEET_URL = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/export?format=csv"


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
        # Parse user-selected players
        selected_players = request.json.get("players", [])
        player_count = int(request.json.get("player_count", 10))
        salary_cap = int(request.json.get("salary_cap", SALARY_CAP))

        results = generate_top_k(selected_players, player_count, salary_cap)
        return jsonify({"success": True, "results": results})
    except Exception as e:
        print("Error optimizing:", e)
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
