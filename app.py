from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime, timezone
import os
from danger_engine import DangerEngine, NearbySafeZones, VersionInfo
from twilio.rest import Client  

API_KEY = os.getenv("DPE_API_KEY", "dev-key") 

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
    payload = request.get_json(silent=True) or {}
    message_text = payload.get("message", "🚨 Emergency! SOS triggered. Please send help.")

    try:
        # Twilio client
        client = Client(
            os.getenv("TWILIO_ACCOUNT_SID"),
            os.getenv("TWILIO_AUTH_TOKEN")
        )

        # Send SMS to verified number
        to_number = payload.get("to") or os.getenv("TWILIO_TO_NUMBER")
        from_number = os.getenv("TWILIO_FROM_NUMBER")

        # Debug logs
        print("Sending SMS from:", from_number)
        print("Sending SMS to:", to_number)
        print("Message:", message_text)

        client.messages.create(
            body=message_text,
            from_=from_number,
            to=to_number
        )

        return jsonify({
            "status": "sent",
            "note": "SMS alert sent successfully.",
            "message": message_text
        }), 200

    except Exception as e:
        print("Error sending SMS:", e)
        return jsonify({"error": str(e)}), 500

# Serve frontend
@app.route("/")
def serve_index():
    return send_from_directory(app.static_folder, "index.html")

# Catch-all for static files and frontend routes
@app.route("/<path:path>")
def serve_static_file(path):
    file_path = os.path.join(app.static_folder, path)
    if os.path.isfile(file_path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
