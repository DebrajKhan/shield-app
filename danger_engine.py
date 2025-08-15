# danger_engine.py
from __future__ import annotations
from typing import Dict, Any, List, Optional
from datetime import datetime
from math import radians, sin, cos, asin, sqrt

class VersionInfo:
    version = "1.0.0"

def _safe_float(x, default=None):
    try: return float(x)
    except (TypeError, ValueError): return default

def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = radians(lat2-lat1)
    dlon = radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    c = 2 * asin((a)**0.5)
    return R * 2 * asin((a)**0.5) if a>0 else 0.0

class NearbySafeZones:
    """Demo list with Kolkata & generic locations; replace with real data later."""
    def __init__(self):
        self._zones = [
            {"title":"Kolkata Police Helpdesk (Demo)","lat":22.5729,"lon":88.3639,"tags":["Official","24/7"]},
            {"title":"24/7 Pharmacy (Demo)","lat":22.5698,"lon":88.3692,"tags":["Open 24/7","Verified"]},
            {"title":"Well-lit Cafe (Demo)","lat":22.5755,"lon":88.3605,"tags":["Crowded","Charging"]},
            {"title":"Metro Station Gate (Demo)","lat":22.5737,"lon":88.3620,"tags":["CCTV","Transit"]},
            {"title":"Hospital OPD (Demo)","lat":22.5762,"lon":88.3667,"tags":["Medical","Security"]}
        ]

    def list(self, lat: Optional[float]=None, lon: Optional[float]=None, radius_km: float=5.0):
        if lat is None or lon is None:
            return self._zones
        out = []
        for z in self._zones:
            d = _haversine_km(lat, lon, z["lat"], z["lon"])
            if d <= radius_km:
                item = dict(z); item["distance_km"] = round(d, 2)
                out.append(item)
        out.sort(key=lambda x: x.get("distance_km", 0))
        return out

class DangerEngine:
    KEYWORDS = {
        "immediate_danger": ["help","sos","stalk","following","threat","danger","attack","harass"],
        "unease": ["scared","unsafe","alone","dark","anxious"]
    }

    def score(self, data: Dict[str, Any]) -> Dict[str, Any]:
        score = 0.0; reasons: List[str] = []; actions: List[str] = []; level = "low"
        lat = _safe_float(data.get("lat")); lon = _safe_float(data.get("lon"))
        timestamp = data.get("timestamp"); heart = _safe_float(data.get("heart_rate"))
        resting = _safe_float(data.get("resting_bpm"))
        motion = data.get("motion") or {}; context = data.get("context") or {}
        user_text = (data.get("user_text") or "").lower()

        # Time of day
        try:
            t = datetime.fromisoformat(timestamp.replace("Z","+00:00")) if timestamp else None
            hour = t.hour if t else None
        except Exception:
            hour = None
        if hour is not None:
            if hour >= 22 or hour < 5: score += 18; reasons.append("late_night")
            elif hour >= 19 or hour < 7: score += 8; reasons.append("evening_hours")

        # Context
        lighting = (context.get("lighting") or "").lower()
        crowd = (context.get("crowd") or "").lower()
        if lighting in ("dark","dim"): score += 12; reasons.append(f"lighting_{lighting}")
        if crowd in ("empty",): score += 10; reasons.append("low_crowd_density")

        # Heart-rate anomaly
        if heart and resting and resting > 0:
            pct = (heart - resting) / resting
            if pct >= 0.6: score += 28; reasons.append("heart_rate_spike_60pct_plus")
            elif pct >= 0.35: score += 18; reasons.append("heart_rate_spike_35pct_plus")
            elif pct >= 0.2: score += 10; reasons.append("heart_rate_spike_20pct_plus")

        # Motion
        if motion.get("fall"): score += 35; reasons.append("fall_detected")
        if motion.get("shake"): score += 10; reasons.append("device_shake")
        spd = _safe_float(motion.get("speed_kmh"))
        if spd is not None and spd > 12: score += 8; reasons.append("high_speed")

        # NLP-ish keywords
        if user_text:
            if any(k in user_text for k in self.KEYWORDS["immediate_danger"]):
                score += 40; reasons.append("text_immediate_danger_keywords")
            elif any(k in user_text for k in self.KEYWORDS["unease"]):
                score += 15; reasons.append("text_unease_keywords")

        # Area baseline (simple bucket)
        if lat is not None and lon is not None:
            bucket = int(abs(lat*7 + lon*13)) % 5
            hazard = [0, 6, 10, 14, 20][bucket]
            score += hazard; reasons.append(f"area_baseline_{hazard}")

        score = max(0, min(100, round(score, 1)))
        if score >= 75: level = "critical"
        elif score >= 45: level = "elevated"
        else: level = "low"

        if level == "critical":
            actions += ["Trigger SOS now","Share live location","Move to nearest safe zone","Call emergency services"]
        elif level == "elevated":
            actions += ["Stay on call with a trusted contact","Change route to a well-lit area","Head towards a safe zone"]
        else:
            actions += ["Stay aware of surroundings","Keep phone accessible","Consider sharing route with a friend"]

        zones = NearbySafeZones().list(lat=lat, lon=lon, radius_km=5.0) if (lat is not None and lon is not None) else []
        return {"score": score, "level": level, "reasons": reasons, "recommended_actions": actions, "nearby_safe_zones": zones}
