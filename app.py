from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime, timezone
import os
from danger_engine import DangerEngine, NearbySafeZones, VersionInfo
from twilio.rest import Client  
from flask_socketio import SocketIO, emit
from encryption_utils import encrypt_data, decrypt_data

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
    return jsonify({"lat": 22.5726, "lng": 88.3639})

def _auth_ok(req):
    return req.headers.get("x-api-key", "") == API_KEY

@app.post("/api/predict")
def predict():
    if not _auth_ok(request):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}

    # Encrypt incoming data (Zero-Knowledge)
    encrypted_data = encrypt_data(str(data))
    
    # Optional: store encrypted_data in DB
    # Example: save_to_db(user_id, encrypted_data)

    # Decrypt for processing
    decrypted_data = decrypt_data(encrypted_data)

    result = engine.score(eval(decrypted_data))  # Convert back to dict safely if needed
    # Encrypt result before returning
    encrypted_result = encrypt_data(str(result))

    # Send decrypted result for frontend use
    return jsonify(eval(decrypt_data(encrypted_result)))

@app.post("/api/alert")
def alert():
    payload = request.get_json(silent=True) or {}
    message_text = payload.get("message", "🚨 Emergency! SOS triggered. Please send help.")

    # Encrypt message for zero-knowledge storage/logging if needed
    encrypted_message = encrypt_data(message_text)
    # Optional: store encrypted_message in DB

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
    return send_from_directory(app.static_folder, "sheild_frontend2.html")

@app.route("/<path:path>")
def serve_static_file(path):
    file_path = os.path.join(app.static_folder, path)
    if os.path.isfile(file_path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, "sheild_frontend2.html")


# ------------------- Socket.IO Events (Encrypted) -------------------

@socketio.on('user_message')
def handle_user_message(data):
    try:
        # Encrypt message before broadcasting
        message_text = data.get("message", "")
        encrypted_message = encrypt_data(message_text)

        # Broadcast the encrypted message
        emit('user_message', {"message": encrypted_message, "sender": "user"}, broadcast=True)
        print("Encrypted message from user broadcasted")
    except Exception as e:
        print("Error encrypting user message:", str(e))

@socketio.on('police_message')
def handle_police_message(data):
    try:
        # Encrypt police reply before broadcasting
        message_text = data.get("message", "")
        encrypted_message = encrypt_data(message_text)

        # Broadcast the encrypted message
        emit('user_message', {"message": encrypted_message, "sender": "police"}, broadcast=True)
        print("Encrypted message from police broadcasted")
    except Exception as e:
        print("Error encrypting police message:", str(e))

@socketio.on('connect')
def handle_connect():
    print("Client connected")

@socketio.on('disconnect')
def handle_disconnect():
    print("Client disconnected")

@app.route("/police")
def police_dashboard():
    return send_from_directory(app.static_folder, "police_dashboard.html")

# ------------------- Run App -------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    socketio.run(app, host="0.0.0.0", port=port, debug=True, allow_unsafe_werkzeug=True)
