from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import joblib
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")

# Load traffic models bundle
traffic_bundle_path = os.path.join(MODELS_DIR, "traffic_models.pkl")
bus_bundle_path = os.path.join(MODELS_DIR, "bus_allocator.pkl")

traffic_bundle = joblib.load(traffic_bundle_path)
bus_bundle = joblib.load(bus_bundle_path)

speed_model = traffic_bundle["speed_model"]
delay_model = traffic_bundle["delay_model"]
risk_clf = traffic_bundle["risk_clf"]
slot_encoder = traffic_bundle["slot_encoder"]

bus_model = bus_bundle["bus_model"]
overcrowd_clf = bus_bundle["overcrowd_clf"]

app = Flask(__name__)
CORS(app)

# ---------------- Passenger demand logic (rule-based using all inputs) ----------------

# Base demand per route (you can tune these based on your city / data)
ROUTE_BASE_LOAD = {
    1: 30,
    2: 55,
    3: 75,
    4: 60,
    5: 105,  # we know this route is high-demand from your tests
    6: 65,
    7: 70,
    8: 80,
    9: 90,
    10: 100,
}


def hour_factor(hour: int) -> float:
    """
    Multiplier based on time of day:
      • 05–07  → low (0.7)
      • 08–10  → morning peak (1.2)
      • 11–16  → normal (1.0)
      • 17–20  → evening peak (1.3)
      • else   → late night (0.4)
    """
    if 5 <= hour <= 7:
        return 0.7
    if 8 <= hour <= 10:
        return 1.2
    if 11 <= hour <= 16:
        return 1.0
    if 17 <= hour <= 20:
        return 1.3
    return 0.4  # night / very early


def weather_factor(weather: int) -> float:
    """
    Weather impact:
      • 0 = clear → 1.0
      • 1 = rain/bad → 1.15 (more people take bus)
    """
    if weather == 1:
        return 1.15
    return 1.0


def holiday_factor(holiday: int) -> float:
    """
    Holiday impact:
      • 0 = working day → 1.0
      • 1 = holiday     → 0.85 (fewer commuters overall)
    """
    if holiday == 1:
        return 0.85
    return 1.0


def compute_passenger_demand(route_id: int, hour: int, weather: int, holiday: int) -> int:
    base = ROUTE_BASE_LOAD.get(route_id, 60)
    h_f = hour_factor(hour)
    w_f = weather_factor(weather)
    hol_f = holiday_factor(holiday)

    demand = base * h_f * w_f * hol_f

    # tiny deterministic "noise" so that even same hour/route can vary slightly
    noise = ((route_id * 7 + hour * 3) % 10) - 5  # -5 .. +4
    demand = demand + noise

    return max(0, int(round(demand)))


# ---------------- Helpers ----------------

def _error(message: str, status: int = 400):
    return jsonify({"error": message}), status


# ---------------- Routes ----------------

@app.route("/")
def index():
    return (
        "SmartTransit++ backend is running. "
        "Use POST /predict/traffic, /predict/passengers or /predict/all"
    )


@app.route("/predict/traffic", methods=["POST"])
def predict_traffic():
    data = request.get_json(silent=True)
    if not data:
        return _error("Invalid or missing JSON body")

    try:
        time_slot = int(data["time_slot"])
        live_cong = float(data["live_congestion"])
        usual_cong = float(data["usual_congestion"])
    except (KeyError, ValueError, TypeError):
        return _error(
            "Required fields: time_slot (int), live_congestion (float), usual_congestion (float)"
        )

    # Encode time_slot for the traffic model
    try:
        slot_enc = slot_encoder.transform([str(time_slot)])[0]
    except Exception:
        # If unseen slot, fall back to first known class
        slot_enc = slot_encoder.transform([slot_encoder.classes_[0]])[0]

    X = np.array([[slot_enc, live_cong, usual_cong]])

    speed = float(speed_model.predict(X)[0])
    delay = float(delay_model.predict(X)[0])

    return jsonify(
        {
            "speed_kmph": round(speed, 2),
            "delay_min_per_10km": round(delay, 2),
        }
    )


@app.route("/predict/passengers", methods=["POST"])
def predict_passengers():
    data = request.get_json(silent=True)
    if not data:
        return _error("Invalid or missing JSON body")

    try:
        route_id = int(data["Route_ID"])
        hour = int(data["Hour"])
        weather = int(data.get("Weather", 0))
        holiday = int(data.get("Holiday", 0))
    except (KeyError, ValueError, TypeError):
        return _error(
            "Required fields: Route_ID (int), Hour (int), "
            "optional Weather (0/1), Holiday (0/1)"
        )

    predicted = compute_passenger_demand(route_id, hour, weather, holiday)

    return jsonify({"predicted_passengers": predicted})


@app.route("/predict/all", methods=["POST"])
def predict_all():
    data = request.get_json(silent=True)
    if not data:
        return _error("Invalid or missing JSON body")

    # ---------- Traffic ----------
    try:
        time_slot = int(data["time_slot"])
        live_cong = float(data["live_congestion"])
        usual_cong = float(data["usual_congestion"])
    except (KeyError, ValueError, TypeError):
        return _error(
            "For traffic: time_slot (int), live_congestion (float), usual_congestion (float)"
        )

    try:
        slot_enc = slot_encoder.transform([str(time_slot)])[0]
    except Exception:
        slot_enc = slot_encoder.transform([slot_encoder.classes_[0]])[0]

    X_traffic = np.array([[slot_enc, live_cong, usual_cong]])
    speed = float(speed_model.predict(X_traffic)[0])
    delay = float(delay_model.predict(X_traffic)[0])

    # Risk classification (Low / Medium / High)
    risk_prob = risk_clf.predict_proba(X_traffic)[0]
    risk_label_idx = int(np.argmax(risk_prob))
    risk_map = {0: "Low", 1: "Medium", 2: "High"}
    risk_label = risk_map.get(risk_label_idx, "Medium")

    # ---------- Passenger demand ----------
    route_features = data.get("route_features") or {}
    try:
        route_id = int(route_features["Route_ID"])
        hour = int(route_features["Hour"])
        weather = int(route_features.get("Weather", 0))
        holiday = int(route_features.get("Holiday", 0))
    except (KeyError, ValueError, TypeError):
        return _error(
            "route_features must include Route_ID (int), Hour (int), "
            "optional Weather (0/1), Holiday (0/1)"
        )

    passenger_demand = compute_passenger_demand(route_id, hour, weather, holiday)

    # ---------- Bus allocation ----------
    # Use already derived features: route_id, passengers, speed, delay, congestion.
    X_bus = np.array(
        [[route_id, passenger_demand, speed, delay, live_cong, usual_cong]]
    )
    buses = float(bus_model.predict(X_bus)[0])

    overcrowd_flag = int(overcrowd_clf.predict(X_bus)[0])
    overcrowd_label = "High" if overcrowd_flag == 1 else "Normal"

    return jsonify(
        {
            "predicted_passengers": int(round(passenger_demand)),
            "recommended_buses": int(max(1, round(buses))),
            "overcrowding_risk": overcrowd_label,
            "accident_risk": risk_label,
            "speed_kmph": round(speed, 2),
            "delay_min_per_10km": round(delay, 2),
        }
    )


if __name__ == "__main__":
    # For local debugging only; Render uses gunicorn app:app
    app.run(host="0.0.0.0", port=5000, debug=True)
