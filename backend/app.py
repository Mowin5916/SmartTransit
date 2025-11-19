# backend/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import pandas as pd
import numpy as np
import os
import traceback

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")

# ---------- Helper to load models with safety ----------
def safe_load(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Model file not found: {path}")
    return joblib.load(path)

# ---------- Load passenger model and try to detect feature columns ----------
passenger_model_path = os.path.join(MODELS_DIR, "passenger_xgb.pkl")
passenger_model = None
passenger_feature_cols = None

try:
    passenger_model = safe_load(passenger_model_path)
    # Try common places for saved feature list:
    # 1) model.feature_names_in_ (sklearn/xgboost when trained with pandas)
    if hasattr(passenger_model, "feature_names_in_"):
        passenger_feature_cols = list(getattr(passenger_model, "feature_names_in_"))
    # 2) maybe the saved object is a dict/bundle with 'feature_cols'
    elif isinstance(passenger_model, dict) and "feature_cols" in passenger_model:
        passenger_feature_cols = list(passenger_model["feature_cols"])
        passenger_model = passenger_model.get("model", passenger_model)  # unwrap
    else:
        # try loading an auxiliary file models/passenger_feature_cols.pkl or .json
        aux_json = os.path.join(MODELS_DIR, "passenger_feature_cols.json")
        aux_pkl = os.path.join(MODELS_DIR, "passenger_feature_cols.pkl")
        if os.path.exists(aux_json):
            import json
            passenger_feature_cols = json.load(open(aux_json, "r"))
        elif os.path.exists(aux_pkl):
            passenger_feature_cols = joblib.load(aux_pkl)
        else:
            passenger_feature_cols = None
except Exception as e:
    passenger_model = None
    passenger_feature_cols = None
    print("⚠️ Passenger model load error:", e)

# ---------- Load traffic models bundle ----------
traffic_bundle_path = os.path.join(MODELS_DIR, "traffic_models.pkl")
speed_model = delay_model = slot_encoder = None
try:
    traffic_bundle = safe_load(traffic_bundle_path)
    # Expecting structure like: {"speed_model": ..., "delay_model": ..., "slot_encoder": ...}
    if isinstance(traffic_bundle, dict):
        speed_model = traffic_bundle.get("speed_model")
        delay_model = traffic_bundle.get("delay_model")
        slot_encoder = traffic_bundle.get("slot_encoder")
    else:
        # fallback: if raw models were saved separately, try sensible names
        speed_model = getattr(traffic_bundle, "speed_model", None)
        delay_model = getattr(traffic_bundle, "delay_model", None)
except Exception as e:
    print("⚠️ Traffic model load error:", e)

# ---------- Load bus allocator bundle ----------
bus_bundle_path = os.path.join(MODELS_DIR, "bus_allocator.pkl")
bus_regressor = bus_classifier = bus_features = None
try:
    bus_bundle = safe_load(bus_bundle_path)
    if isinstance(bus_bundle, dict):
        bus_regressor = bus_bundle.get("regressor") or bus_bundle.get("model")
        bus_classifier = bus_bundle.get("classifier")
        bus_features = bus_bundle.get("feature_cols") or bus_bundle.get("feature_cols", None)
    else:
        # If raw model, no bundle data
        bus_regressor = bus_bundle
except Exception as e:
    print("⚠️ Bus allocator load error:", e)

# ---------- Helper functions ----------
def build_passenger_df(route_features: dict):
    """
    Build a DataFrame aligned to passenger model features.
    - If passenger_feature_cols is available, use that and fill missing with 0.
    - Otherwise use the keys provided by route_features.
    """
    if route_features is None:
        raise ValueError("route_features must be provided (JSON body key: route_features).")

    # If model expects certain features, create that skeleton
    if passenger_feature_cols:
        row = {c: 0 for c in passenger_feature_cols}
        # map provided features into the row for any matching names
        for k, v in route_features.items():
            if k in row:
                row[k] = v
        df = pd.DataFrame([row], columns=passenger_feature_cols)
    else:
        # no feature list known -> trust the input keys
        df = pd.DataFrame([route_features])
    # Ensure numeric columns are numeric
    df = df.apply(pd.to_numeric, errors="coerce").fillna(0)
    return df

def encode_time_slot(ts):
    """Encode time slot with slot_encoder if available, otherwise try simple mapping."""
    if slot_encoder is None:
        # fallback: if ts is numeric return as int else 0
        try:
            return int(ts)
        except:
            return 0
    try:
        # slot_encoder might be sklearn LabelEncoder or similar
        return int(slot_encoder.transform([str(ts)])[0])
    except Exception:
        try:
            return int(ts)
        except:
            return 0

# ---------- Endpoints ----------

@app.route("/predict/passengers", methods=["POST"])
def predict_passengers():
    try:
        payload = request.get_json(force=True)
        # accept either raw features or nested route_features
        route_features = payload.get("route_features") if isinstance(payload, dict) and "route_features" in payload else payload
        df = build_passenger_df(route_features)
        if passenger_model is None:
            return jsonify({"error": "Passenger model not loaded on server."}), 500
        # If passenger_model is a bundle dict, try to extract model object
        model_to_call = passenger_model.get("model") if isinstance(passenger_model, dict) and "model" in passenger_model else passenger_model
        pred = model_to_call.predict(df)[0]
        return jsonify({"predicted_passengers": int(round(float(pred)))})
    except Exception as e:
        tb = traceback.format_exc()
        return jsonify({"error": str(e), "traceback": tb}), 500

@app.route("/predict/traffic", methods=["POST"])
def predict_traffic():
    try:
        payload = request.get_json(force=True) or {}
        ts = payload.get("time_slot", 0)
        live = float(payload.get("live_congestion", 50))
        usual = float(payload.get("usual_congestion", 50))

        ts_enc = encode_time_slot(ts)
        X = np.array([[ts_enc, live, usual]])
        if speed_model is None or delay_model is None:
            return jsonify({"error": "Traffic models not loaded."}), 500
        speed = float(speed_model.predict(X)[0])
        delay = float(delay_model.predict(X)[0])
        return jsonify({"speed_kmph": round(speed,2), "delay_min_per_10km": round(delay,2)})
    except Exception as e:
        tb = traceback.format_exc()
        return jsonify({"error": str(e), "traceback": tb}), 500

@app.route("/predict/buses", methods=["POST"])
def predict_buses():
    try:
        payload = request.get_json(force=True) or {}
        # expected inputs:
        pp = payload.get("predicted_passengers") or payload.get("pred_passengers")
        speed = payload.get("speed_kmph")
        delay = payload.get("delay_min_per_10km")
        ts = payload.get("time_slot", 0)

        if pp is None:
            return jsonify({"error": "predicted_passengers key is required"}), 400

        ts_enc = encode_time_slot(ts)

        # assemble features for bus model
        if bus_features:
            row = {c: 0 for c in bus_features}
            # try mapping known names
            mapping = {
                "pred_passengers": pp,
                "predicted_passengers": pp,
                "pred_passengers_count": pp,
                "pred_speed_kmph": speed,
                "pred_delay_min_per_10km": delay,
                "Time_Slot_enc": ts_enc,
                "Time_Slot": ts_enc
            }
            for k,v in mapping.items():
                if k in row and v is not None:
                    row[k] = v
            df = pd.DataFrame([row], columns=bus_features).apply(pd.to_numeric, errors="coerce").fillna(0)
        else:
            df = pd.DataFrame([{"pred_passengers": pp, "pred_speed_kmph": speed or 0, "pred_delay_min_per_10km": delay or 0, "Time_Slot_enc": ts_enc}])
            df = df.apply(pd.to_numeric, errors="coerce").fillna(0)

        if bus_regressor is None:
            return jsonify({"error": "Bus allocator regressor not loaded"}), 500

        buses = int(round(bus_regressor.predict(df)[0]))
        crowd = None
        if bus_classifier:
            crowd = int(bus_classifier.predict(df)[0])

        return jsonify({"recommended_buses": buses, "overcrowding_risk": ("High" if crowd==1 else "Normal") if crowd is not None else "Unknown"})
    except Exception as e:
        tb = traceback.format_exc()
        return jsonify({"error": str(e), "traceback": tb}), 500

@app.route("/predict/all", methods=["POST"])
def predict_all():
    try:
        payload = request.get_json(force=True) or {}
        # passenger
        route_features = payload.get("route_features")
        df_pass = build_passenger_df(route_features)
        if passenger_model is None:
            return jsonify({"error": "Passenger model not loaded."}), 500
        model_to_call = passenger_model.get("model") if isinstance(passenger_model, dict) and "model" in passenger_model else passenger_model
        pred_pass = int(round(float(model_to_call.predict(df_pass)[0])))

        # traffic
        ts = payload.get("time_slot", 0)
        live = float(payload.get("live_congestion", 50))
        usual = float(payload.get("usual_congestion", 50))
        ts_enc = encode_time_slot(ts)
        Xtraffic = np.array([[ts_enc, live, usual]])
        if speed_model is None or delay_model is None:
            return jsonify({"error": "Traffic models not loaded."}), 500
        speed = float(speed_model.predict(Xtraffic)[0])
        delay = float(delay_model.predict(Xtraffic)[0])

        # buses
        bus_payload = {"predicted_passengers": pred_pass, "speed_kmph": speed, "delay_min_per_10km": delay, "time_slot": ts}
        # reuse predict_buses logic (but inline for simplicity)
        if bus_features:
            row = {c: 0 for c in bus_features}
            mapvals = {"pred_passengers": pred_pass, "pred_speed_kmph": speed, "pred_delay_min_per_10km": delay, "Time_Slot_enc": ts_enc}
            for k,v in mapvals.items():
                if k in row:
                    row[k] = v
            df_bus = pd.DataFrame([row], columns=bus_features).apply(pd.to_numeric, errors="coerce").fillna(0)
        else:
            df_bus = pd.DataFrame([{"pred_passengers": pred_pass, "pred_speed_kmph": speed, "pred_delay_min_per_10km": delay, "Time_Slot_enc": ts_enc}]).apply(pd.to_numeric, errors="coerce").fillna(0)

        buses = int(round(bus_regressor.predict(df_bus)[0])) if bus_regressor else None
        crowd = int(bus_classifier.predict(df_bus)[0]) if bus_classifier else None

        out = {
            "predicted_passengers": pred_pass,
            "speed_kmph": round(speed,2),
            "delay_min_per_10km": round(delay,2),
            "recommended_buses": buses,
            "overcrowding_risk": ("High" if crowd==1 else "Normal") if crowd is not None else "Unknown"
        }
        return jsonify(out)
    except Exception as e:
        tb = traceback.format_exc()
        return jsonify({"error": str(e), "traceback": tb}), 500

# default route to show service is live
@app.route("/", methods=["GET"])
def root():
    return "SmartTransit++ backend is running. Use POST /predict/all", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
