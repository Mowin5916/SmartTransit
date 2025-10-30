from flask import Flask, request, jsonify
import pandas as pd
import joblib
import os

app = Flask(__name__)

# === Load model and reference data ===
MODEL_PATH = os.path.join("models", "passenger_xgb.pkl")
DATA_PATH = os.path.join("data", "merged_encoded.csv")

model = None
data = None

try:
    model = joblib.load(MODEL_PATH)
    data = pd.read_csv(DATA_PATH)
    print("✅ Model and data loaded successfully!")
except Exception as e:
    print("❌ Error loading model or data:", e)

# === Home route ===
@app.route('/')
def home():
    return jsonify({"message": "🚌 SmartTransit API is running successfully!"})

# === Predict route ===
@app.route('/predict', methods=['GET'])
def predict():
    if model is None or data is None:
        return jsonify({"error": "Model or reference data not loaded on server. Check server logs."}), 500

    try:
        # Get parameters
        route = int(request.args.get('route_id', 0))
        time_slot = int(request.args.get('time_slot', 0))
        weather = int(request.args.get('weather', 0))
        live_cong = float(request.args.get('live_congestion', 70))
        delay = float(request.args.get('delay_minutes', 10))
        live_speed = float(request.args.get('live_speed', 15.5))

        # Build input row
        sample = {
            'Route_ID': route,
            'Time_Slot': time_slot,
            'Weather_Condition': weather,
            'Live_Congestion': live_cong,
            'Delay_Minutes': delay,
            'Live_Speed_kmph': live_speed
        }

        df_sample = pd.DataFrame([sample])

        # Align columns with model
        X_columns = [c for c in data.columns if c not in ['Date', 'Passenger_Count']]
        for col in X_columns:
            if col not in df_sample.columns:
                df_sample[col] = 0

        pred = model.predict(df_sample[X_columns])[0]

        alert = "⚠️ Heavy traffic" if live_cong > 75 or delay > 12 else "✅ Normal flow"

        return jsonify({
            "predicted_passengers": round(float(pred), 2),
            "traffic_status": alert
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    app.run(debug=True)
