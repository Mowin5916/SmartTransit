from flask import Flask, request, jsonify
import joblib
import pandas as pd
import numpy as np
from math import ceil
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allow frontend → backend

# ==============================
# LOAD MODELS
# ==============================
passenger_model = joblib.load("models/passenger_xgb.pkl")
traffic_bundle = joblib.load("models/traffic_models.pkl")
bus_bundle = joblib.load("models/bus_allocator.pkl")

speed_model = traffic_bundle["speed_model"]
delay_model = traffic_bundle["delay_model"]
slot_encoder = traffic_bundle["slot_encoder"]
bus_capacity = bus_bundle["bus_capacity"]
bus_regressor = bus_bundle["regressor"]
bus_classifier = bus_bundle["classifier"]
bus_features = bus_bundle["feature_cols"]

# ==============================
# HELPER: Safe Time Slot Encode
# ==============================
def encode_time_slot(ts):
    try:
        ts = str(ts)
        if slot_encoder and ts in slot_encoder.classes_:
            return slot_encoder.transform([ts])[0]
        return 0
    except:
        return 0

# ==============================
# 1️⃣ PASSENGER PREDICTION
# ==============================
@app.route("/predict/passengers", methods=["POST"])
def predict_passengers():
    data = request.json

    try:
        df = pd.DataFrame([data])
        df = df.apply(pd.to_numeric, errors="ignore").fillna(0)

        # drop unnecessary
        if "Passenger_Count" in df.columns:
            df = df.drop(columns=["Passenger_Count"])

        pred = passenger_model.predict(df)[0]
        return jsonify({"predicted_passengers": int(pred)})

    except Exception as e:
        return jsonify({"error": str(e)})


# ==============================
# 2️⃣ TRAFFIC PREDICTION
# ==============================
@app.route("/predict/traffic", methods=["POST"])
def predict_traffic():
    data = request.json

    ts = data.get("time_slot", 0)
    live = float(data.get("live_congestion", 50))
    usual = float(data.get("usual_congestion", 50))

    enc = encode_time_slot(ts)
    X = np.array([[enc, live, usual]])

    speed = float(speed_model.predict(X)[0])
    delay = float(delay_model.predict(X)[0])

    return jsonify({
        "speed_kmph": round(speed, 2),
        "delay_min_per_10km": round(delay, 2)
    })


# ==============================
# 3️⃣ BUS ALLOCATION & CROWD RISK
# ==============================
@app.route("/predict/buses", methods=["POST"])
def predict_buses():
    data = request.json

    try:
        # INPUT:
        # predicted_passengers, speed, delay, time_slot

        pp = data.get("predicted_passengers")
        speed = data.get("speed_kmph")
        delay = data.get("delay_min_per_10km")
        ts = data.get("time_slot", 0)

        ts_enc = encode_time_slot(ts)

        # Feature vector
        row = {
            "pred_passengers": pp,
            "pred_speed_kmph": speed,
            "pred_delay_min_per_10km": delay,
        }

        if "Time_Slot_enc" in bus_features:
            row["Time_Slot_enc"] = ts_enc

        df = pd.DataFrame([row])[bus_features]

        # Predict buses + crowd
        buses = int(round(bus_regressor.predict(df)[0]))
        crowd = int(bus_classifier.predict(df)[0])

        return jsonify({
            "recommended_buses": buses,
            "overcrowding_risk": "High" if crowd == 1 else "Normal"
        })

    except Exception as e:
        return jsonify({"error": str(e)})


# ==============================
# 4️⃣ MASTER ENDPOINT – For Frontend
# ==============================
@app.route("/predict/all", methods=["POST"])
def full_prediction():
    """
    INPUT:
    {
        "time_slot": 2,
        "live_congestion": 57.2,
        "usual_congestion": 45,
        "route_features": {... your input for passenger model ...}
    }
    """

    data = request.json

    # 1) PASSENGERS
    df = pd.DataFrame([data["route_features"]])
    df = df.apply(pd.to_numeric, errors="ignore").fillna(0)
    pred_pass = int(passenger_model.predict(df)[0])

    # 2) TRAFFIC
    ts = data.get("time_slot", 0)
    enc = encode_time_slot(ts)

    live = float(data.get("live_congestion", 50))
    usual = float(data.get("usual_congestion", 50))

    Xtraffic = np.array([[enc, live, usual]])
    speed = float(speed_model.predict(Xtraffic)[0])
    delay = float(delay_model.predict(Xtraffic)[0])

    # 3) BUSES
    row = {
        "pred_passengers": pred_pass,
        "pred_speed_kmph": speed,
        "pred_delay_min_per_10km": delay,
        "Time_Slot_enc": enc
    }

    df2 = pd.DataFrame([row])[bus_features]
    buses = int(round(bus_regressor.predict(df2)[0]))
    crowd = int(bus_classifier.predict(df2)[0])

    return jsonify({
        "predicted_passengers": pred_pass,
        "speed_kmph": round(speed, 2),
        "delay_min_per_10km": round(delay, 2),
        "recommended_buses": buses,
        "overcrowding_risk": "High" if crowd == 1 else "Normal"
    })


# ==============================
# RUN SERVER
# ==============================
if __name__ == "__main__":
    app.run(debug=True)
