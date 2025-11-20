from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import joblib
import numpy as np

# -----------------------------
# Paths & model loading
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")

traffic_bundle_path = os.path.join(MODELS_DIR, "traffic_models.pkl")

if not os.path.exists(traffic_bundle_path):
    raise FileNotFoundError(f"traffic_models.pkl not found at {traffic_bundle_path}")

traffic_bundle = joblib.load(traffic_bundle_path)

# These MUST exist (you already trained them)
speed_model = traffic_bundle["speed_model"]
delay_model = traffic_bundle["delay_model"]
slot_encoder = traffic_bundle["slot_encoder"]

# This may or may not exist depending on when you trained the model
risk_clf = traffic_bundle.get("risk_clf", None)

app = Flask(__name__)
CORS(app)


# ---------------------------------------------------
#  Passenger Demand Logic (rule-based but dynamic)
# ---------------------------------------------------

# Base demand per route (tune as you like)
ROUTE_BASE_LOAD = {
    1: 30,
    2: 55,
    3: 75,
    4: 60,
    5: 105,   # known high-demand
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
    return 1.15 if weather == 1 else 1.0


def holiday_factor(holiday: int) -> float:
    """
    Holiday impact:
      • 0 = working day → 1.0
      • 1 = holiday     → 0.85 (fewer commuters overall)
    """
    return 0.85 if holiday == 1 else 1.0


def compute_passenger_demand(route_id: int, hour: int, weather: int, holiday: int) -> int:
    """
    Final passenger demand = base(route) × hour_factor × weather_factor × holiday_factor + small noise
    """
    base = ROUTE_BASE_LOAD.get(route_id, 60)
    h_f = hour_factor(hour)
    w_f = weather_factor(weather)
    hol_f = holiday_factor(holiday)

    demand = base * h_f * w_f * hol_f

    # tiny deterministic "noise" so that even same combination has small variation
    noise = ((route_id * 7 + hour * 3 + weather * 5 + holiday * 11) % 10) - 5  # -5..+4
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


# ---------------------------------------------------
#  /predict/traffic
# ---------------------------------------------------
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

    # Encode time_slot
    try:
        slot_enc = slot_encoder.transform([str(time_slot)])[0]
    except Exception:
        # If unseen, fallback to first known class
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


# ---------------------------------------------------
#  /predict/passengers
# ---------------------------------------------------
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


# ---------------------------------------------------
#  /predict/all  (Traffic + Passengers + Bus Allocation)
# ---------------------------------------------------
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

    # Accident / traffic risk (use ML if available, else rule-based fallback)
    accident_risk = "Medium"
    if risk_clf is not None:
        try:
            risk_prob = risk_clf.predict_proba(X_traffic)[0]
            risk_label_idx = int(np.argmax(risk_prob))
            risk_map = {0: "Low", 1: "Medium", 2: "High"}
            accident_risk = risk_map.get(risk_label_idx, "Medium")
        except Exception:
            # fallback if model shape mismatches
            if delay >= 8 or live_cong >= 70:
                accident_risk = "High"
            elif delay >= 4 or live_cong >= 50:
                accident_risk = "Medium"
            else:
                accident_risk = "Low"
    else:
        # No trained classifier present
        if delay >= 8 or live_cong >= 70:
            accident_risk = "High"
        elif delay >= 4 or live_cong >= 50:
            accident_risk = "Medium"
        else:
            accident_risk = "Low"

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

    # ---------- Bus allocation (rule-based) ----------
    # Assume standard bus capacity, and aim for ~80% target load per bus
    BUS_CAPACITY = 40          # adjust if you want 50-seaters
    TARGET_LOAD = 0.8          # we prefer not to fully pack the bus

    effective_capacity = BUS_CAPACITY * TARGET_LOAD
    if effective_capacity <= 0:
        recommended_buses = 1
    else:
        recommended_buses = int(np.ceil(passenger_demand / effective_capacity))
        recommended_buses = max(1, recommended_buses)

    # Overcrowding risk based on true capacity vs passengers
    max_safe_passengers = recommended_buses * BUS_CAPACITY
    if passenger_demand > max_safe_passengers:
        overcrowding_risk = "High"
    elif passenger_demand > max_safe_passengers * 0.9:
        overcrowding_risk = "Medium"
    else:
        overcrowding_risk = "Low"

    return jsonify(
        {
            "predicted_passengers": int(passenger_demand),
            "recommended_buses": int(recommended_buses),
            "overcrowding_risk": overcrowding_risk,
            "accident_risk": accident_risk,
            "speed_kmph": round(speed, 2),
            "delay_min_per_10km": round(delay, 2),
        }
    )


if __name__ == "__main__":
    # Local debugging only; Render uses `gunicorn app:app`
    app.run(host="0.0.0.0", port=5000, debug=True)
