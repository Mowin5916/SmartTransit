import pandas as pd
import joblib
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.metrics import mean_absolute_error, r2_score, classification_report
import os

print("📌 Loading datasets...")

# Load original + synthetic data
df_real = pd.read_csv("data/traffic_data.csv")
df_syn = pd.read_csv("data/traffic_synthetic.csv")

# Combine both → strong training dataset
df = pd.concat([df_real, df_syn], ignore_index=True)
df = df.dropna().reset_index(drop=True)

print(f"📌 Combined dataset shape: {df.shape}")

# Encode categories
slot_le = LabelEncoder()
risk_le = LabelEncoder()

df["Time_Slot_enc"] = slot_le.fit_transform(df["Time_Slot"].astype(str))
df["Accident_Risk_enc"] = risk_le.fit_transform(df["Accident_Risk_Level"].astype(str))

# Features
X = df[["Time_Slot_enc", "Live_Congestion_Level(%)", "Usual_Congestion_Level(%)"]]
y_speed = df["Live_Speed_kmph"]
y_delay = df["Delay_Minutes_per_10km"]
y_risk = df["Accident_Risk_enc"]

# Train-test split (now meaningful with 1000 rows)
X_train, X_test, y_speed_train, y_speed_test = train_test_split(
    X, y_speed, test_size=0.2, random_state=42
)

_, _, y_delay_train, y_delay_test = train_test_split(
    X, y_delay, test_size=0.2, random_state=42
)

_, _, y_risk_train, y_risk_test = train_test_split(
    X, y_risk, test_size=0.2, random_state=42
)

# Train models
speed_model = RandomForestRegressor(n_estimators=300, random_state=42)
delay_model = RandomForestRegressor(n_estimators=300, random_state=42)
risk_model = RandomForestClassifier(n_estimators=300, random_state=42)

speed_model.fit(X_train, y_speed_train)
delay_model.fit(X_train, y_delay_train)
risk_model.fit(X_train, y_risk_train)

# Evaluate
speed_pred = speed_model.predict(X_test)
delay_pred = delay_model.predict(X_test)
risk_pred = risk_model.predict(X_test)

print("\n📊 SPEED MODEL")
print("MAE:", round(mean_absolute_error(y_speed_test, speed_pred), 3))
print("R2:", round(r2_score(y_speed_test, speed_pred), 3))

print("\n📊 DELAY MODEL")
print("MAE:", round(mean_absolute_error(y_delay_test, delay_pred), 3))
print("R2:", round(r2_score(y_delay_test, delay_pred), 3))

print("\n📊 ACCIDENT RISK CLASSIFIER")
print(classification_report(y_risk_test, risk_pred, zero_division=0))

# Save models
os.makedirs("models", exist_ok=True)

bundle = {
    "speed_model": speed_model,
    "delay_model": delay_model,
    "risk_model": risk_model,
    "slot_encoder": slot_le,
    "risk_encoder": risk_le,
    "feature_cols": list(X.columns)
}

joblib.dump(bundle, "models/traffic_models.pkl")

print("\n✅ Strong Traffic AI Model Saved → models/traffic_models.pkl")
