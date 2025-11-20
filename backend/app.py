from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import joblib
import numpy as np

# -----------------------------
# Paths and model loading
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")

traffic_bundle_path = os.path.join(MODELS_DIR, "traffic_models.pkl")
bus_bundle_path = os.path.join(MODELS_DIR, "bus_allocator.pkl")

traffic_bundle = joblib.load(traffic_bundle_path)
bus_bundle = joblib.load(bus_bundle_path)

# Traffic models (with safe .get for optional keys)
speed_model = traffic_bundle.get("speed_model")
delay_model = traffic_bundle.get("delay_model")
slot_encoder = traffic_bundle.get("slot_encoder", None)
risk_clf = traffic_bundle.get("risk_clf", None)   # might not exist in this pickle

# Bus allocator models
bus_model = bus_bundle.get("bus_model")
overcrowd_clf = bus_bundle.get("overcrowd_clf")

app = Flask(__name__)
CORS(app)

# -----------------------------
# Rule-based passenger demand
# -----------------------------

# Base demand per route (tune as needed)
ROUTE_BASE_LOAD = {
    1: 30,
    2: 55,
    3: 75,
    4: 60,
    5: 105,   # high demand route
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
      • 0 = clear   → 1.0
      • 1 = rain    → 1.15 (more people take bus)
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
    """
    Final passenger demand = base_by_route * hour_factor * weather_factor * holiday_factor (+ small deterministic noise)
    This ensures:
      • Different routes have different base loads
      • Same route but different hour / weather / holiday gives different predictions
    """
    base = ROUTE_BASE_LOAD.get(route_id, 60)
    h_f = hour_factor(hour)
    w_f = weather_factor(weather)
    hol_f = holiday_factor(holiday)

    demand = base * h_f * w_f * hol_f

    # Tiny deterministic noise by route/hour so calls don't look perfectly flat
    noise = ((route_id * 7 + hour * 3) % 10) - 5  # -5 .. +4
    demand = demand + noise

    return max(0, int(round(demand)))


# -----------------------------
# Helpers
# -----------------------------
def _error(message: str, status: int = 400):
    return jsonify({"error": message}), status


def _encode_time_slot(time_slot: int):
    """
    Use LabelEncoder from the traffic bundle if available; otherwise,
    just feed the raw time_slot to the models.
    """
    if slot_encoder is None:
        return float(time_slot)

    try:
        return float(slot_encoder.transform([str(time_slot)])[0])
    except Exception:
        # Fallback: first known class if time_slot isn't in classes
        return float(slot_encoder.transform([slot_encoder.classes_[0]])[0])


def _compute_accident_risk_from_delay_and_congestion(delay, live_cong):
    """
    Fallback: if we don't have risk_clf, derive a simple risk level
    from delay and congestion (just for display).
    """
    score = 0.5 * float(delay) + 0.5 * float(live_cong)

    if score < 20:
        return "Low"
    elif score < 50:
        return "Medium"
    else:
        return "High"


# -----------------------------
# Routes
# -----------------------------
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

    # Encode / prepare features
    slot_val = _encode_time_slot(time_slot)
    X = np.array([[slot_val, live_cong, usual_cong]])

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
            "Required fields: Route_ID (int), Hour (int), optional Weather (0/1), Holiday (0/1)"
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

    slot_val = _encode_time_slot(time_slot)
    X_traffic = np.array([[slot_val, live_cong, usual_cong]])

    speed = float(speed_model.predict(X_traffic)[0])
    delay = float(delay_model.predict(X_traffic)[0])

    # Accident / traffic risk
    if risk_clf is not None:
        try:
            risk_prob = risk_clf.predict_proba(X_traffic)[0]
            risk_label_idx = int(np.argmax(risk_prob))
            risk_map = {0: "Low", 1: "Medium", 2: "High"}
            accident_risk = risk_map.get(risk_label_idx, "Medium")
        except Exception:
            accident_risk = _compute_accident_risk_from_delay_and_congestion(
                delay, live_cong
            )
    else:
        # Fallback rule-based risk if no classifier in bundle
        accident_risk = _compute_accident_risk_from_delay_and_congestion(
            delay, live_cong
        )

    # ---------- Passenger demand ----------
    route_features = data.get("route_features") or {}
    try:
        route_id = int(route_features["Route_ID"])
        hour = int(route_features["Hour"])
        weather = int(route_features.get("Weather", 0))
        holiday = int(route_features.get("Holiday", 0))
    except (KeyError, ValueError, TypeError):
        return _error(
            "route_features must include Route_ID (int), Hour (int), optional Weather (0/1), Holiday (0/1)"
        )

    passenger_demand = compute_passenger_demand(route_id, hour, weather, holiday)

    # ---------- Bus allocation ----------
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
            "accident_risk": accident_risk,
            "speed_kmph": round(speed, 2),
            "delay_min_per_10km": round(delay, 2),
        }
    )


if __name__ == "__main__":
    # Local debugging only; Render uses gunicorn app:app
    app.run(host="0.0.0.0", port=5000, debug=True)
