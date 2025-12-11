from flask import Flask, jsonify, request
from flask_cors import CORS
import time

app = Flask(__name__)
CORS(app)

STATUS = {
    "timestamp": None,
    "nifty_ltp": None,
    "legs": {},
    "net_credit": None,
    "pnl": None,
    "logs": [],
    "exit_reason": None
}

@app.route("/api/update", methods=["POST"])
def update():
    global STATUS
    data = request.get_json()
    STATUS.update(data)
    return jsonify({"ok": True})

@app.route("/api/status")
def status():
    return jsonify(STATUS)

if __name__ == "__main__":
    print("Backend running...")
    app.run(host="0.0.0.0", port=5000)
