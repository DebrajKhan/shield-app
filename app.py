from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime, timezone
import os
from flask_socketio import SocketIO, emit

# ------------------- Mock Danger Engine -------------------

class DangerEngine:
    def score(self, data):
        import random
        danger_level = random.uniform(0.1, 0.8)
        factors = ["low_lighting", "isolated_area"] if danger_level > 0.5 else ["well_lit", "populated"]
        return {
            "danger_level": danger_level,
            "factors": factors,
            "recommendation": "Stay alert" if danger_level > 0.5 else "Area seems safe"
        }

class NearbySafeZones:
    def list(self, lat=None, lon=None, radius_km=5):
        return [
            {"id":1,"name":"Shyama Charan Lahiri Sarani Police Station","lat":22.5726,"lon":88.3639,"type":"police_station","verified":True,"open_24_7":True},
            {"id":2,"name":"Apollo Pharmacy Park Street","lat":22.5449,"lon":88.3534,"type":"pharmacy","verified":True,"open_24_7":True},
            {"id":3,"name":"Cafe Coffee Day Park Street","lat":22.5506,"lon":88.3515,"type":"cafe","verified":True,"open_24_7":False},
            {"id":4,"name":"SSKM Hospital Emergency","lat":22.5054,"lon":88.3423,"type":"hospital","verified":True,"open_24_7":True}
        ]

class VersionInfo:
    version = "1.0.0"

# ------------------- Flask & Socket.IO Setup -------------------

API_KEY = os.getenv("DPE_API_KEY", "dev-key")
app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

engine = DangerEngine()
zones = NearbySafeZones()

# ------------------- In-Memory Storage -------------------

user_locations = {}

# ------------------- Helper Functions -------------------

def _auth_ok(req):
    return req.headers.get("x-api-key", "") == API_KEY

def current_time():
    return datetime.now(timezone.utc).isoformat()

# ------------------- API Routes -------------------

@app.get("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "name": "SHEild Safety Engine",
        "version": VersionInfo.version,
        "time_utc": current_time()
    })

@app.get("/api/safe-zones")
def safe_zones():
    try:
        lat = float(request.args.get("lat")) if request.args.get("lat") else None
        lon = float(request.args.get("lon")) if request.args.get("lon") else None
        radius_km = float(request.args.get("radius_km", 5))
    except ValueError:
        return jsonify({"error": "Invalid lat/lon/radius"}), 400

    return jsonify({"count": len(zones.list()), "items": zones.list(lat, lon, radius_km)})

@app.get("/api/city-coords")
def city_coords():
    return jsonify({"lat": 22.5726, "lng": 88.3639})

@app.post("/api/predict")
def predict():
    if not _auth_ok(request):
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify(engine.score(request.get_json(silent=True) or {}))

@app.post("/api/locations")
def receive_location():
    data = request.get_json(silent=True) or {}
    device_id = data.get("device_id", "unknown")
    lat = data.get("lat")
    lon = data.get("lon")
    accuracy = data.get("accuracy", 0)

    if lat is None or lon is None:
        return jsonify({"error": "Missing lat/lon"}), 400

    user_locations[device_id] = {
        "lat": lat,
        "lon": lon,
        "accuracy": accuracy,
        "timestamp": current_time()
    }

    socketio.emit('location_update', {
        "device_id": device_id,
        "lat": lat,
        "lon": lon,
        "timestamp": user_locations[device_id]["timestamp"]
    })

    return jsonify({"status": "received", "device_id": device_id})

# ------------------- Frontend Routes -------------------

@app.route("/")
def serve_index():
    return send_from_directory(".", "sheild_frontend2.html")

@app.route("/police")
def police_dashboard():
    return send_from_directory(".", "police_dashboard.html")

@app.route("/<path:path>")
def serve_static_file(path):
    try:
        return send_from_directory(".", path)
    except:
        return send_from_directory(".", "sheild_frontend2.html")

# ------------------- Socket.IO Events -------------------

@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")
    emit('connected', {'status': 'Connected to SHEild server'})

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")

@socketio.on('user_message')
def handle_user_message(data):
    emit('user_message', {
        'user_id': data.get('user_id', 'User'),
        'message': data.get('message', ''),
        'timestamp': current_time(),
        'session_id': request.sid
    }, broadcast=True)

@socketio.on('police_message')
def handle_police_message(data):
    emit('police_reply', {
        'message': data.get('message', ''),
        'timestamp': current_time(),
        'from': 'Police'
    }, broadcast=True)

@socketio.on('emergency_alert')
def handle_emergency(data):
    emit('emergency_alert', {
        'user_id': data.get('user_id', 'Unknown'),
        'location': data.get('location', {}),
        'message': data.get('message', 'Emergency situation reported'),
        'timestamp': current_time(),
        'alert_type': 'SOS'
    }, broadcast=True)

# ------------------- Run App -------------------

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    import eventlet
    socketio.run(app, host="0.0.0.0", port=port)
