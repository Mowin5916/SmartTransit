# app.py - SmartTransit API (paste entire file, overwrite existing)

from flask import Flask, request, jsonify
import pandas as pd
import joblib
import os

app = Flask(__name__)

# --- Helpers ---
def safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default

def ensure_columns(df_sample, template_cols):
    # ensure df_sample has all template columns in same order
    for c in template_cols:
        if c not in df_sample.columns:
            df_sample[c] = 0
    return df_sample[template_cols]

# --- Load model & reference data (on import) ---
MODEL_PATH = os.path.join("models", "passenger_xgb.pkl")
DATA_PATH = os.path.join("data", "merged_encoded.csv")

# load model
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Model not found at {MODEL_PATH}. Put passenger_xgb.pkl in the models/ folder.")
model = joblib.load(MODEL_PATH)

# load example encoded dataset (used to get feature columns and encodings)
if not os.path.exists(DATA_PATH):
    raise FileNotFoundError(f"Reference data not found at {DATA_PATH}. Put merged_encoded.csv in the data/ folder.")
data = pd.read_csv(DATA_PATH)

# deduce feature columns used at training (drop Date and Passenger_Count if present)
FEATURE_COLS = [c for c in data.columns if c not in ("Date", "Passenger_Count")]

@app.route('/')
def home():
    return jsonify({"message": "🚌 SmartTransit API is running!", "features_expected": FEATURE_COLS})

@app.route('/predict', methods=['GET'])
def predict():
    try:
        # read inputs from query params (use encoded numeric values for categorical args)
        route = safe_float(request.args.get('route_id', 0))
        time_slot = safe_float(request.args.get('time_slot', 0))
        weather = safe_float(request.args.get('weather', 0))
        congestion = safe_float(request.args.get('live_congestion', 58.0))
        delay = safe_float(request.args.get('delay_minutes', 7.5))
        live_speed = safe_float(request.args.get('live_speed', 15.5))
        temp = safe_float(request.args.get('temperature', 0.0))
        rainfall = safe_float(request.args.get('rainfall', 0.0))

        # build sample row (use numeric encoded values if your dataset used encoding)
        sample = {
            "Route_ID": route,
            "Time_Slot": time_slot,
            "Weather_Condition": weather,
            "Live_Congestion": congestion,
            "Delay_Minutes": delay,
            "Live_Speed_kmph": live_speed,
            "Temperature_C_x": temp,
            "Rainfall_mm_x": rainfall
        }

        df_sample = pd.DataFrame([sample])

        # align columns to what model expects (fill missing with 0)
        df_sample = ensure_columns(df_sample, FEATURE_COLS)

        # convert to numeric and predict
        X = df_sample.apply(pd.to_numeric, errors="coerce").fillna(0)
        pred = model.predict(X)[0]
        pred_int = int(round(float(pred)))

        alert = "⚠️ Heavy traffic or delay" if (congestion > 75 or delay > 10) else "✅ Normal flow"

        return jsonify({
            "predicted_passengers": pred_int,
            "raw_prediction": float(pred),
            "alert": alert,
            "input_used": sample
        })
    except Exception as e:
        # return the error for easier debugging
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    # run on localhost port 5000 (development server)
    app.run(debug=True, host="127.0.0.1", port=5000)
