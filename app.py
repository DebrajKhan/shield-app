from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime, timezone
import os
from danger_engine import DangerEngine, NearbySafeZones, VersionInfo
from twilio.rest import Client  
from flask_socketio import SocketIO, emit

API_KEY = os.getenv("DPE_API_KEY", "dev-key") 

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app, resources={r"/api/": {"origins": ""}})

# Socket.IO setup
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

engine = DangerEngine()
zones = NearbySafeZones()

# ------------------- API Routes -------------------

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

@app.get("/api/city-coords")
def city_coords():
    # Kolkata coordinates
    return jsonify({"lat": 22.5726, "lng": 88.3639})

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
        client = Client(
            os.getenv("TWILIO_ACCOUNT_SID"),
            os.getenv("TWILIO_AUTH_TOKEN")
        )

        to_number = payload.get("to") or os.getenv("TWILIO_TO_NUMBER")
        from_number = os.getenv("TWILIO_FROM_NUMBER")

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
        return jsonify({"error": str(e)}), 500

# ------------------- Frontend Routes -------------------

@app.route("/")
def serve_index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/<path:path>")
def serve_static_file(path):
    file_path = os.path.join(app.static_folder, path)
    if os.path.isfile(file_path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, "index.html")

# ------------------- Socket.IO Events -------------------

# User sends message to police dashboard
@socketio.on('user_message')
def handle_user_message(data):
    print("Message from user:", data)
    # Forward message to all connected clients (police dashboard)
    emit('user_message', data, broadcast=True)

# Police (you) sends message to user
@socketio.on('police_message')
def handle_police_message(data):
    print("Reply from police:", data)
    # Forward message to all connected users
    emit('user_message', data, broadcast=True)

# Optional: connection logs
@socketio.on('connect')
def handle_connect():
    print("Client connected")

@socketio.on('disconnect')
def handle_disconnect():
    print("Client disconnected")

    # Police dashboard route
@app.route("/police")
def police_dashboard():
    return send_from_directory(app.static_folder, "police_dashboard.html")


# ------------------- Run App -------------------
if __name__ == "_main_":
    port = int(os.getenv("PORT", "8000"))
    # Use eventlet for real-time
    socketio.run(app, host="0.0.0.0", port=port)