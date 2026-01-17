# app.py
"""
SmartTransit main Flask backend (updated).
- Serves a health root endpoint
- /predict : returns demand prediction (uses local joblib model + reference CSV)
- /api/ask_ai : proxy to RAG service (http://localhost:8001/chat by default)
Configuration via environment variables:
- MODEL_PATH (default: models/passenger_xgb.pkl)
- DATA_PATH  (default: data/merged_encoded.csv)
- RAG_URL    (default: http://localhost:8001/chat)
"""
import os
import logging
from flask import Flask, request, jsonify
import pandas as pd
import joblib
import requests
from requests.exceptions import RequestException
from flask_cors import CORS

# --- Configuration ---
MODEL_PATH = os.environ.get("MODEL_PATH", os.path.join("models", "passenger_xgb.pkl"))
DATA_PATH = os.environ.get("DATA_PATH", os.path.join("data", "merged_encoded.csv"))
RAG_URL = os.environ.get("RAG_URL", "http://localhost:8001/chat")
API_TIMEOUT = int(os.environ.get("API_TIMEOUT", "10"))  # seconds for external calls

# --- App setup ---
app = Flask(__name__)
CORS(app)  # allow cross-origin requests while developing (adjust for production)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("smarttransit")

# --- Load model and reference data (graceful) ---
model = None
ref_data = None
X_COLUMNS = []

def safe_load_model_and_data():
    global model, ref_data, X_COLUMNS
    try:
        if os.path.exists(MODEL_PATH):
            model = joblib.load(MODEL_PATH)
            logger.info(f"✅ Model loaded from {MODEL_PATH}")
        else:
            logger.warning(f"Model file not found at {MODEL_PATH}")

        if os.path.exists(DATA_PATH):
            ref_data = pd.read_csv(DATA_PATH, low_memory=False)
            logger.info(f"✅ Reference data loaded from {DATA_PATH} (shape={ref_data.shape})")
            # derive feature columns (exclude obvious target/date columns)
            X_COLUMNS = [c for c in ref_data.columns if c.lower() not in ("date", "passenger_count", "passengers", "target")]
            logger.info(f"Feature columns derived: {len(X_COLUMNS)} columns")
        else:
            logger.warning(f"Reference CSV not found at {DATA_PATH}")
    except Exception as e:
        logger.exception("Failed to load model or reference data: %s", e)

safe_load_model_and_data()

# --- Root / health check ---
@app.route("/", methods=["GET"])
def home():
    status = {
        "message": "🚌 SmartTransit API is running",
        "model_loaded": bool(model),
        "ref_data_loaded": bool(ref_data),
        "rag_available_at": RAG_URL
    }
    return jsonify(status)

# --- Predict route (GET) ---
@app.route("/predict", methods=["GET"])
def predict():
    if model is None or ref_data is None:
        return jsonify({"error": "Model or reference data not loaded on server. Check server logs."}), 500

    try:
        # read inputs (fallback defaults if missing)
        route = request.args.get("route_id") or request.args.get("route") or 0
        time_slot = request.args.get("time_slot") or request.args.get("time") or 0
        weather = request.args.get("weather") or 0
        live_cong = request.args.get("live_congestion") or request.args.get("live_cong") or 70
        delay = request.args.get("delay_minutes") or request.args.get("delay") or 10
        live_speed = request.args.get("live_speed") or request.args.get("live_speed_kmph") or 15.5

        # safe casting
        route = int(float(route))
        time_slot = int(float(time_slot))
        weather = int(float(weather))
        live_cong = float(live_cong)
        delay = float(delay)
        live_speed = float(live_speed)

        # Build base sample using the derived X_COLUMNS
        sample = {}
        # Try to match common column names; if a name exists in X_COLUMNS, set it appropriately
        # This keeps the model input aligned with training schema
        for col in X_COLUMNS:
            lc = col.lower()
            if "route" in lc and "id" in lc:
                sample[col] = route
            elif "time" in lc and ("slot" in lc or "hour" in lc):
                sample[col] = time_slot
            elif "weather" in lc:
                sample[col] = weather
            elif "congest" in lc or "live_congestion" in lc:
                sample[col] = live_cong
            elif "delay" in lc:
                sample[col] = delay
            elif "speed" in lc:
                sample[col] = live_speed
            else:
                # default zero for other features
                sample[col] = 0

        df_sample = pd.DataFrame([sample], columns=X_COLUMNS)

        # Predict
        pred = model.predict(df_sample)[0]
        pred_val = float(pred)

        traffic_flag = "⚠️ Heavy traffic" if (live_cong > 75 or delay > 12) else "✅ Normal flow"

        return jsonify({
            "predicted_passengers": round(pred_val, 2),
            "traffic_status": traffic_flag,
            "used_features_count": len(X_COLUMNS)
        })

    except Exception as e:
        logger.exception("Prediction failed: %s", e)
        return jsonify({"error": str(e)}), 400

# --- Copilot proxy route to RAG server (POST) ---
@app.route("/api/ask_ai", methods=["POST"])
def ask_ai():
    """
    Expects JSON body: { "query": "...", "top_k": 3 }
    Forwards to the configured RAG server and returns the response.
    """
    try:
        payload = request.get_json(force=True)
        if not payload or "query" not in payload:
            return jsonify({"error": "Missing 'query' in request body."}), 400

        top_k = int(payload.get("top_k", 5))
        # build request for rag server
        rag_req = {"query": payload["query"], "top_k": top_k}
        try:
            resp = requests.post(RAG_URL, json=rag_req, timeout=API_TIMEOUT)
            resp.raise_for_status()
        except RequestException as re:
            logger.exception("Error contacting RAG server at %s : %s", RAG_URL, re)
            return jsonify({"error": "RAG server unreachable", "details": str(re)}), 502

        # forward rag response as-is
        return jsonify(resp.json())

    except Exception as e:
        logger.exception("ask_ai failed: %s", e)
        return jsonify({"error": str(e)}), 500

# --- Run application ---
if __name__ == "__main__":
    # Use host 0.0.0.0 so render/container bindings work if you run directly
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
