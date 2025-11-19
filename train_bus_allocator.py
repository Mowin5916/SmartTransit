# train_bus_allocator.py
# Trains Bus Allocation AI using passenger & traffic predictions

import pandas as pd
import numpy as np
import joblib
import os
from math import ceil
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, accuracy_score, classification_report

# ===========================
# CONFIG
# ===========================
BUS_CAPACITY = 50  # recommended capacity
PASSENGER_MODEL_PATH = "models/passenger_xgb.pkl"
TRAFFIC_MODELS_PATH = "models/traffic_models.pkl"
INPUT_DATA = "data/merged_encoded.csv"
OUT_MODEL_PATH = "models/bus_allocator.pkl"
RANDOM_STATE = 42

# ===========================
# Helper to safely load files
# ===========================
def safe_load(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} not found.")
    return joblib.load(path)

print("📌 Loading data and models...")

# Load dataset
df = pd.read_csv(INPUT_DATA)
if "Passenger_Count" not in df.columns:
    raise SystemExit("ERROR: 'Passenger_Count' missing in merged_encoded.csv")

# Load passenger prediction model
passenger_model = safe_load(PASSENGER_MODEL_PATH)

# Load traffic models bundle
traffic_bundle = safe_load(TRAFFIC_MODELS_PATH)
speed_model = traffic_bundle["speed_model"]
delay_model = traffic_bundle["delay_model"]
slot_encoder = traffic_bundle.get("slot_encoder", None)

# =================================
# Prepare input for passenger model
# =================================
print("📌 Generating passenger predictions...")

X_passenger_input = df.drop(
    columns=[c for c in ["Date", "Passenger_Count"] if c in df.columns],
    errors="ignore"
).copy()

X_passenger_input = X_passenger_input.apply(pd.to_numeric, errors="coerce").fillna(0)

pred_passengers = passenger_model.predict(X_passenger_input)

# =================================
# Prepare input for traffic models
# =================================

print("📌 Preparing traffic features...")

traffic_features = pd.DataFrame()

# ------- TIME SLOT ENCODING (FIXED BLOCK) -------
if "Time_Slot" in df.columns:

    # CASE 1 → Time_Slot is numeric (0,1,2,3)
    if pd.api.types.is_numeric_dtype(df["Time_Slot"]):
        traffic_features["Time_Slot_enc"] = df["Time_Slot"]

    # CASE 2 → Time_Slot is string (Morning, Afternoon, ...)
    else:
        if slot_encoder is not None:
            def safe_encode(x):
                if x in slot_encoder.classes_:
                    return slot_encoder.transform([x])[0]
                else:
                    return 0  # default fallback
            traffic_features["Time_Slot_enc"] = df["Time_Slot"].astype(str).apply(safe_encode)
        else:
            traffic_features["Time_Slot_enc"] = pd.factorize(df["Time_Slot"].astype(str))[0]

else:
    traffic_features["Time_Slot_enc"] = 0
# -------------------------------------------------

# Congestion columns detection
cong_cols = [c for c in df.columns if "congestion" in c.lower()]
if len(cong_cols) >= 1:
    traffic_features["Live_Congestion_Level(%)"] = df[cong_cols[0]].astype(float).fillna(df[cong_cols[0]].mean())
else:
    traffic_features["Live_Congestion_Level(%)"] = 50.0

usual_cols = [c for c in df.columns if "usual" in c.lower()]
if len(usual_cols) >= 1:
    traffic_features["Usual_Congestion_Level(%)"] = df[usual_cols[0]].astype(float).fillna(df[usual_cols[0]].mean())
else:
    traffic_features["Usual_Congestion_Level(%)"] = traffic_features["Live_Congestion_Level(%)"]

# Predict traffic metrics
print("📌 Generating traffic model outputs...")

X_traffic = traffic_features[["Time_Slot_enc", "Live_Congestion_Level(%)", "Usual_Congestion_Level(%)"]]

pred_speed = speed_model.predict(X_traffic)
pred_delay = delay_model.predict(X_traffic)

# =================================
# Build final training table
# =================================
df_train = df.copy()
df_train["pred_passengers"] = np.round(pred_passengers).astype(int)
df_train["pred_speed_kmph"] = np.round(pred_speed, 2)
df_train["pred_delay_min_per_10km"] = np.round(pred_delay, 2)

# True buses needed = ceil(actual passengers / bus capacity)
df_train["required_buses_true"] = df_train["Passenger_Count"].apply(
    lambda p: int(ceil(p / BUS_CAPACITY))
)

# Overcrowding label = 1 if >85% capacity
df_train["overcrowd_true"] = (df_train["Passenger_Count"] > (0.85 * BUS_CAPACITY)).astype(int)

# Features used for allocator model
feature_cols = [
    "pred_passengers",
    "pred_speed_kmph",
    "pred_delay_min_per_10km",
]

# Add Time Slot if exists
if "Time_Slot_enc" in traffic_features.columns:
    df_train["Time_Slot_enc"] = traffic_features["Time_Slot_enc"]
    feature_cols.append("Time_Slot_enc")

# Final X and y
X = df_train[feature_cols]
y_reg = df_train["required_buses_true"]
y_clf = df_train["overcrowd_true"]

# Train-test split
if len(X) >= 80:
    X_train, X_test, y_reg_train, y_reg_test = train_test_split(X, y_reg, test_size=0.2, random_state=RANDOM_STATE)
    Xc_train, Xc_test, y_clf_train, y_clf_test = train_test_split(X, y_clf, test_size=0.2, random_state=RANDOM_STATE)
else:
    X_train, X_test = X, X
    y_reg_train, y_reg_test = y_reg, y_reg
    Xc_train, Xc_test = X, X
    y_clf_train, y_clf_test = y_clf, y_clf

print(f"📌 Training models on {len(X_train)} samples...")

# Train models
regressor = RandomForestRegressor(n_estimators=200, random_state=RANDOM_STATE)
classifier = RandomForestClassifier(n_estimators=200, random_state=RANDOM_STATE)

regressor.fit(X_train, y_reg_train)
classifier.fit(Xc_train, y_clf_train)

# Evaluate
reg_pred = regressor.predict(X_test)
clf_pred = classifier.predict(Xc_test)

print("\n📊 BUS ALLOCATOR PERFORMANCE")
print("MAE (buses):", round(mean_absolute_error(y_reg_test, reg_pred), 3))

print("\nSample Predictions (true vs predicted):")
print(pd.DataFrame({
    "true_buses": list(y_reg_test)[:10],
    "pred_buses": list(np.round(reg_pred).astype(int))[:10]
}))

print("\n📌 Overcrowding Classifier")
print("Accuracy:", round(accuracy_score(y_clf_test, clf_pred), 3))
print(classification_report(y_clf_test, clf_pred, zero_division=0))

# Save bundled model
os.makedirs("models", exist_ok=True)

bundle = {
    "regressor": regressor,
    "classifier": classifier,
    "feature_cols": feature_cols,
    "bus_capacity": BUS_CAPACITY
}

joblib.dump(bundle, OUT_MODEL_PATH)

print(f"\n✅ Bus Allocator saved successfully → {OUT_MODEL_PATH}")
