from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime, timezone
import os
from flask_socketio import SocketIO, emit
import json

# Mock danger_engine classes since the module wasn't provided
class DangerEngine:
    def score(self, data):
        # Mock danger prediction - replace with actual ML model
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
        # Mock safe zones for Kolkata - replace with actual database
        kolkata_zones = [
            {
                "id": 1,
                "name": "Shyama Charan Lahiri Sarani Police Station",
                "lat": 22.5726,
                "lon": 88.3639,
                "type": "police_station",
                "verified": True,
                "open_24_7": True
            },
            {
                "id": 2,
                "name": "Apollo Pharmacy Park Street",
                "lat": 22.5449,
                "lon": 88.3534,
                "type": "pharmacy",
                "verified": True,
                "open_24_7": True
            },
            {
                "id": 3,
                "name": "Cafe Coffee Day Park Street",
                "lat": 22.5506,
                "lon": 88.3515,
                "type": "cafe",
                "verified": True,
                "open_24_7": False
            },
            {
                "id": 4,
                "name": "SSKM Hospital Emergency",
                "lat": 22.5054,
                "lon": 88.3423,
                "type": "hospital",
                "verified": True,
                "open_24_7": True
            }
        ]
        return kolkata_zones

class VersionInfo:
    version = "1.0.0"

API_KEY = os.getenv("DPE_API_KEY", "dev-key")

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app, resources={r"/*": {"origins": "*"}})

# Socket.IO setup
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

engine = DangerEngine()
zones = NearbySafeZones()

# Store locations in memory (replace with database in production)
user_locations = {}

# ------------------- API Routes -------------------

@app.get("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "name": "SHEild Safety Engine",
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

@app.post("/api/locations")
def receive_location():
    """Receive and store user location data"""
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
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Emit location update to connected clients (for real-time tracking)
    socketio.emit('location_update', {
        "device_id": device_id,
        "lat": lat,
        "lon": lon,
        "timestamp": user_locations[device_id]["timestamp"]
    })
    
    return jsonify({"status": "received", "device_id": device_id})

@app.post("/api/detect")
def detect_panic():
    """Mock panic detection endpoint - replace with actual computer vision"""
    data = request.get_json(silent=True) or {}
    image_data = data.get("image", "")
    
    # Mock panic detection (replace with actual CV model)
    import random
    panic_detected = random.choice([True, False])
    confidence = random.uniform(0.6, 0.95) if panic_detected else random.uniform(0.1, 0.4)
    
    result = {
        "panic": panic_detected,
        "confidence": confidence,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # If panic detected, emit emergency alert
    if panic_detected:
        socketio.emit('panic_detected', result)
    
    return jsonify(result)

@app.post("/api/alert")
def alert():
    """Send emergency SMS alert"""
    payload = request.get_json(silent=True) or {}
    message_text = payload.get("message", "🚨 Emergency! SOS triggered from SHEild app. Please send help.")
    
    try:
        # Try to use Twilio if credentials are available
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        
        if account_sid and auth_token:
            from twilio.rest import Client
            client = Client(account_sid, auth_token)
            
            to_number = payload.get("to") or os.getenv("TWILIO_TO_NUMBER")
            from_number = os.getenv("TWILIO_FROM_NUMBER")
            
            if not to_number or not from_number:
                return jsonify({"error": "Missing phone numbers in environment variables"}), 400
            
            message = client.messages.create(
                body=message_text,
                from_=from_number,
                to=to_number
            )
            
            return jsonify({
                "status": "sent",
                "message_sid": message.sid,
                "note": "SMS alert sent successfully via Twilio",
                "message": message_text
            }), 200
        else:
            # Mock response when Twilio not configured
            print(f"MOCK SMS ALERT: {message_text}")
            return jsonify({
                "status": "sent",
                "note": "Mock SMS alert sent (Twilio not configured)",
                "message": message_text
            }), 200
            
    except Exception as e:
        print(f"SMS Alert Error: {str(e)}")
        return jsonify({"error": f"Failed to send SMS: {str(e)}"}), 500

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

# User sends message to police dashboard
@socketio.on('user_message')
def handle_user_message(data):
    print("Message from user:", data)
    # Broadcast to all connected clients (police dashboard will receive this)
    emit('user_message', {
        'user_id': data.get('user_id', 'User'),
        'message': data.get('message', ''),
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'session_id': request.sid
    }, broadcast=True)

# Police sends reply to user
@socketio.on('police_message')
def handle_police_message(data):
    print("Reply from police:", data)
    # Broadcast police reply to all users
    emit('police_reply', {
        'message': data.get('message', ''),
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'from': 'Police'
    }, broadcast=True)

# Emergency SOS alert
@socketio.on('emergency_alert')
def handle_emergency(data):
    print("🚨 EMERGENCY ALERT:", data)
    # Broadcast emergency to all connected clients
    emit('emergency_alert', {
        'user_id': data.get('user_id', 'Unknown'),
        'location': data.get('location', {}),
        'message': data.get('message', 'Emergency situation reported'),
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'alert_type': 'SOS'
    }, broadcast=True)

# Heartbeat monitoring
@socketio.on('heartbeat_data')
def handle_heartbeat(data):
    bpm = data.get('bpm', 0)
    user_id = data.get('user_id', 'Unknown')
    
    # Simple anomaly detection
    if bpm > 150 or bpm < 40:  # Potential emergency
        emit('heartbeat_alert', {
            'user_id': user_id,
            'bpm': bpm,
            'alert': 'Abnormal heart rate detected',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }, broadcast=True)

# ------------------- Run App -------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    # Use Eventlet for production-safe Socket.IO server
    import eventlet
    import eventlet.wsgi
    socketio.run(app, host="0.0.0.0", port=port)
