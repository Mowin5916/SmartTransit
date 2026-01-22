from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import joblib
import numpy as np

# --------------------------------
# App setup
# --------------------------------
app = Flask(__name__)
CORS(app)

# --------------------------------
# Model loading
# --------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")

traffic_bundle_path = os.path.join(MODELS_DIR, "traffic_models.pkl")

if not os.path.exists(traffic_bundle_path):
    raise FileNotFoundError("traffic_models.pkl not found")

traffic_bundle = joblib.load(traffic_bundle_path)

speed_model = traffic_bundle["speed_model"]
delay_model = traffic_bundle["delay_model"]
slot_encoder = traffic_bundle["slot_encoder"]
risk_clf = traffic_bundle.get("risk_clf")

# --------------------------------
# Passenger demand logic
# --------------------------------
ROUTE_BASE_LOAD = {
    1: 30, 2: 55, 3: 75, 4: 60, 5: 105,
    6: 65, 7: 70, 8: 80, 9: 90, 10: 100,
}

def hour_factor(hour):
    if 8 <= hour <= 10: return 1.2
    if 17 <= hour <= 20: return 1.3
    if 5 <= hour <= 7: return 0.7
    return 1.0

def compute_passenger_demand(route_id, hour, weather, holiday):
    base = ROUTE_BASE_LOAD.get(route_id, 60)
    demand = base * hour_factor(hour)
    if weather == 1: demand *= 1.15
    if holiday == 1: demand *= 0.85
    return max(0, int(round(demand)))

# --------------------------------
# Health check
# --------------------------------
@app.route("/")
def home():
    return jsonify({"status": "SmartTransit backend running"})

# --------------------------------
# Combined prediction endpoint
# --------------------------------
@app.route("/predict/all", methods=["POST"])
def predict_all():
    data = request.get_json()

    time_slot = int(data["time_slot"])
    live_cong = float(data["live_congestion"])
    usual_cong = float(data["usual_congestion"])

    slot_enc = slot_encoder.transform([str(time_slot)])[0]
    X = np.array([[slot_enc, live_cong, usual_cong]])

    speed = float(speed_model.predict(X)[0])
    delay = float(delay_model.predict(X)[0])

    route_features = data["route_features"]
    route_id = int(route_features["Route_ID"])
    hour = int(route_features["Hour"])
    weather = int(route_features.get("Weather", 0))
    holiday = int(route_features.get("Holiday", 0))

    passengers = compute_passenger_demand(route_id, hour, weather, holiday)

    BUS_CAPACITY = 40
    recommended_buses = max(1, int(np.ceil(passengers / (BUS_CAPACITY * 0.8))))

    overcrowding_risk = (
        "High" if passengers > recommended_buses * BUS_CAPACITY
        else "Medium" if passengers > recommended_buses * BUS_CAPACITY * 0.9
        else "Low"
    )

    return jsonify({
        "predicted_passengers": passengers,
        "recommended_buses": recommended_buses,
        "overcrowding_risk": overcrowding_risk,
        "speed_kmph": round(speed, 2),
        "delay_min_per_10km": round(delay, 2),
    })

# --------------------------------
# 🚨 Arduino passenger counter endpoint
# --------------------------------
PASSENGER_COUNT = {}

from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Supabase environment variables not set")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


@app.route("/sensor/update", methods=["POST"])
def sensor_update():
    data = request.get_json()
    bus_id = data.get("bus_id")
    delta = int(data.get("delta", 0))

    if not bus_id:
        return jsonify({"error": "bus_id required"}), 400

    print(f"[SENSOR] bus_id={bus_id}, delta={delta}")

    # 1️⃣ Fetch current occupancy
    res = supabase.table("buses") \
        .select("current_occupancy") \
        .eq("id", bus_id) \
        .single() \
        .execute()

    if not res.data:
        return jsonify({"error": "Bus not found"}), 404

    current = res.data["current_occupancy"] or 0
    new_value = max(0, current + delta)

    # 2️⃣ Update occupancy
    update_res = supabase.table("buses") \
        .update({"current_occupancy": new_value}) \
        .eq("id", bus_id) \
        .execute()

    print(f"[SENSOR] Updated occupancy → {new_value}")

    return jsonify({
        "bus_id": bus_id,
        "count": new_value
    })

if __name__ == "__main__":
    print("🚀 SmartTransit backend starting...")
    app.run(host="0.0.0.0", port=5000, debug=True)
