# app.py - Combined frontend + backend for SHEild Danger Prediction Engine
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime, timezone
import os
from danger_engine import DangerEngine, NearbySafeZones, VersionInfo

API_KEY = os.getenv("DPE_API_KEY", "dev-key")  # change in Render env vars for production

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app, resources={r"/api/*": {"origins": "*"}})

engine = DangerEngine()
zones = NearbySafeZones()

@app.get("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "name": "Danger Prediction Engine",
        "version": VersionInfo.version,
        "time_utc": datetime.now(timezone.utc).isoformat()
    })

@app.get("/api/safe-zones")
def safe_zones():
    try:
        lat = float(request.args.get("lat")) if request.args.get("lat") else None
        lon = float(request.args.get("lon")) if request.args.get("lon") else None
        radius_km = float(request.args.get("radius_km", 5))
    except ValueError:
        return jsonify({"error": "Invalid lat/lon/radius"}), 400

    items = zones.list(lat=lat, lon=lon, radius_km=radius_km)
    return jsonify({"count": len(items), "items": items})

def _auth_ok(req):
    return req.headers.get("x-api-key", "") == API_KEY

@app.post("/api/predict")
def predict():
    if not _auth_ok(request):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    result = engine.score(data)
    return jsonify(result)

@app.post("/api/alert")
def alert():
    if not _auth_ok(request):
        return jsonify({"error": "Unauthorized"}), 401
    payload = request.get_json(silent=True) or {}
    return jsonify({
        "status": "queued",
        "echo": payload,
        "note": "Replace with actual notifier for production."
    }), 202

# Serve frontend
@app.route("/")
def serve_index():
    return send_from_directory(app.static_folder, "index.html")

# Catch-all for static files (CSS, JS, images)
@app.route("/<path:path>")
def serve_static_file(path):
    return send_from_directory(app.static_folder, path)

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
