from flask import Flask, render_template, request, jsonify
from lineup_optimizer import load_players, generate_top_k

app = Flask(__name__)

# Replace with your CSV export URL of Google Sheet
SHEET_URL = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/export?format=csv"

@app.route("/", methods=["GET"])
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
        players = data.get("players")
        count = int(data.get("player_count", 10))
        results = generate_top_k(players, count)
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": f"Error optimizing: {e}"})

if __name__ == "__main__":
    app.run(debug=True)
