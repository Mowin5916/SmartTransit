# backend/app.py
import os
import json
from importlib import import_module
from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import pandas as pd
import numpy as np
from pathlib import Path

app = Flask(__name__)
CORS(app)

BASE = Path(__file__).resolve().parent
MODELS_DIR = BASE / "models"

# ---------- Helper: load joblib safely ----------
def safe_load(p: Path):
    if not p.exists():
        return None
    return joblib.load(str(p))

# ---------- Helper: discover expected features for passenger model ----------
def discover_passenger_features(model, models_dir):
    # 1) If there's a companion JSON listing features
    j = models_dir / "passenger_feature_names.json"
    if j.exists():
        try:
            return json.loads(j.read_text())
        except Exception:
            pass

    # 2) sklearn newer attribute
    feat = getattr(model, "feature_names_in_", None)
    if feat is not None:
        return list(feat)

    # 3) XGBoost Booster stored names (if model is XGBRegressor)
    try:
        booster = getattr(model, "get_booster", None)
        if booster is not None:
            b = model.get_booster()
            names = getattr(b, "feature_names", None)
            if names:
                return list(names)
    except Exception:
        pass

    # 4) If there is a bundle file with feature_cols (common pattern)
    bundle_pkl = models_dir / "passenger_bundle.pkl"
    if bundle_pkl.exists():
        try:
            b = joblib.load(str(bundle_pkl))
            if isinstance(b, dict) and "feature_cols" in b:
                return list(b["feature_cols"])
        except Exception:
            pass

    # 5) fallback: no idea
    return None

# ---------- Feature alignment ----------
def align_features(input_dict, expected_features):
    """Return single-row dataframe with columns in expected_features order.
       Missing features will be filled with 0. Extra features are ignored."""
    df = pd.DataFrame([input_dict])
    # keep only numeric-ish columns and those in expected_features
    out = pd.DataFrame(columns=expected_features)
    for c in expected_features:
        if c in df.columns:
            out[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
        else:
            out[c] = 0
    return out.astype(float)

# ---------- Load models ----------
passenger_model = safe_load(MODELS_DIR / "passenger_xgb.pkl")
# also attempt to load a passenger bundle if present (label encoders + features)
passenger_bundle = safe_load(MODELS_DIR / "passenger_bundle.pkl")
if passenger_bundle and isinstance(passenger_bundle, dict) and "feature_cols" in passenger_bundle:
    passenger_feature_names = passenger_bundle["feature_cols"]
else:
    passenger_feature_names = None

# if still None, try to discover from the model
if passenger_feature_names is None and passenger_model is not None:
    passenger_feature_names = discover_passenger_features(passenger_model, MODELS_DIR)

# load traffic bundle (expected structure seen earlier)
traffic_bundle = safe_load(MODELS_DIR / "traffic_models.pkl") or {}
speed_model = traffic_bundle.get("speed_model")
delay_model = traffic_bundle.get("delay_model")
slot_encoder = traffic_bundle.get("slot_encoder")  # may be None

# load bus allocator bundle
bus_bundle = safe_load(MODELS_DIR / "bus_allocator.pkl") or {}
bus_regressor = bus_bundle.get("regressor")
bus_classifier = bus_bundle.get("classifier")
bus_features = bus_bundle.get("feature_cols", [])
bus_capacity = bus_bundle.get("bus_capacity", 40)

# ---------- small helpers ----------
def encode_time_slot(ts):
    if slot_encoder is None:
        # if encoder missing, try basic mapping
        mapping = {"Morning": 0, "Afternoon": 1, "Evening": 2, "Night": 3}
        return mapping.get(str(ts), 0)
    try:
        return int(slot_encoder.transform([str(ts)])[0])
    except Exception:
        return 0

# ---------- Endpoints ----------
@app.route("/predict/passengers", methods=["POST"])
def predict_passengers():
    if passenger_model is None:
        return jsonify({"error": "Passenger model not found on server."}), 500

    data = request.get_json(force=True) or {}
    # If a top-level object contains route_features, accept that
    if "route_features" in data and isinstance(data["route_features"], dict):
        features = data["route_features"]
    else:
        features = data

    # if we don't know expected features, return helpful message
    if passenger_feature_names is None:
        # try to provide model-derived names (best-effort)
        derived = getattr(passenger_model, "feature_names_in_", None)
        return jsonify({
            "error": "Passenger model feature list unknown on server.",
            "hint": "When training, save the feature order to models/passenger_feature_names.json or passenger_bundle.pkl",
            "model_feature_names_in_attr": list(derived) if derived is not None else None,
            "received_keys": list(features.keys())
        }), 400

    # align
    X = align_features(features, passenger_feature_names)
    try:
        pred = passenger_model.predict(X)[0]
        return jsonify({"predicted_passengers": int(round(float(pred)))})
    except Exception as e:
        return jsonify({"error": "model prediction failed", "detail": str(e)}), 500

@app.route("/predict/traffic", methods=["POST"])
def predict_traffic():
    data = request.get_json(force=True) or {}
    ts = data.get("time_slot", 0)
    live = float(data.get("live_congestion", data.get("live_congestion_level", 50)))
    usual = float(data.get("usual_congestion", 50))
    enc = encode_time_slot(ts)
    X = np.array([[enc, live, usual]])
    if speed_model is None or delay_model is None:
        return jsonify({"error": "Traffic models are not loaded on server."}), 500
    speed = float(speed_model.predict(X)[0])
    delay = float(delay_model.predict(X)[0])
    return jsonify({"speed_kmph": round(speed, 3), "delay_min_per_10km": round(delay, 3)})

@app.route("/predict/buses", methods=["POST"])
def predict_buses():
    data = request.get_json(force=True) or {}
    pred_pass = data.get("predicted_passengers", data.get("pred_passengers"))
    speed = data.get("speed_kmph")
    delay = data.get("delay_min_per_10km")
    ts = data.get("time_slot", 0)
    if pred_pass is None or speed is None or delay is None:
        return jsonify({"error": "required fields: predicted_passengers, speed_kmph, delay_min_per_10km"}), 400

    # prepare features for bus model
    row = {"pred_passengers": float(pred_pass), "pred_speed_kmph": float(speed), "pred_delay_min_per_10km": float(delay)}
    if "Time_Slot_enc" in bus_features:
        row["Time_Slot_enc"] = encode_time_slot(ts)
    if not bus_regressor:
        return jsonify({"error": "bus allocator model not available"}), 500
    df = pd.DataFrame([row])
    # ensure bus feature alignment
    for c in bus_features:
        if c not in df.columns:
            df[c] = 0
    df = df[bus_features]
    try:
        buses = int(round(float(bus_regressor.predict(df)[0])))
        crowd = int(bus_classifier.predict(df)[0]) if bus_classifier else 0
        return jsonify({"recommended_buses": buses, "overcrowding_risk": ("High" if crowd == 1 else "Normal")})
    except Exception as e:
        return jsonify({"error": "bus allocator prediction failed", "detail": str(e)}), 500

@app.route("/predict/all", methods=["POST"])
def predict_all():
    data = request.get_json(force=True) or {}

    # --- passengers ---
    p_input = data.get("route_features", data)
    if passenger_feature_names is None:
        return jsonify({"error": "passenger feature names not available on server; update models/passenger_feature_names.json"}), 400
    Xp = align_features(p_input, passenger_feature_names)
    try:
        pred_pass = int(round(float(passenger_model.predict(Xp)[0])))
    except Exception as e:
        return jsonify({"error": "passenger prediction failed", "detail": str(e)}), 500

    # --- traffic ---
    ts = data.get("time_slot", 0)
    live = float(data.get("live_congestion", 50))
    usual = float(data.get("usual_congestion", 50))
    enc = encode_time_slot(ts)
    if speed_model is None or delay_model is None:
        return jsonify({"error": "traffic models not loaded"}), 500
    Xt = np.array([[enc, live, usual]])
    speed = float(speed_model.predict(Xt)[0])
    delay = float(delay_model.predict(Xt)[0])

    # --- buses ---
    row = {"pred_passengers": pred_pass, "pred_speed_kmph": speed, "pred_delay_min_per_10km": delay}
    if "Time_Slot_enc" in bus_features:
        row["Time_Slot_enc"] = encode_time_slot(ts)
    if not bus_regressor:
        return jsonify({"error": "bus allocator model not available"}), 500
    db = pd.DataFrame([row])
    for c in bus_features:
        if c not in db.columns:
            db[c] = 0
    db = db[bus_features]
    try:
        buses = int(round(float(bus_regressor.predict(db)[0])))
        crowd = int(bus_classifier.predict(db)[0]) if bus_classifier else 0
    except Exception as e:
        return jsonify({"error": "bus allocator failed", "detail": str(e)}), 500

    return jsonify({
        "predicted_passengers": pred_pass,
        "speed_kmph": round(speed,3),
        "delay_min_per_10km": round(delay,3),
        "recommended_buses": buses,
        "overcrowding_risk": ("High" if crowd == 1 else "Normal")
    })


if __name__ == "__main__":
    # when running locally we still allow PORT env var
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
