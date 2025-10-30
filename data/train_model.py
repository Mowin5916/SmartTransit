import pandas as pd
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor
import joblib, sys
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

df = pd.read_csv('merged_encoded.csv')
if 'Passenger_Count' not in df.columns:
    print('ERROR: Passenger_Count not found')
    sys.exit(1)

X = df.drop(columns=['Date','Passenger_Count'])
y = df['Passenger_Count']

X = X.apply(pd.to_numeric, errors='coerce').fillna(0)
y = pd.to_numeric(y, errors='coerce').fillna(0)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = XGBRegressor(n_estimators=200, max_depth=6, learning_rate=0.1, random_state=42, verbosity=0)
model.fit(X_train, y_train)

preds = model.predict(X_test)

mae = mean_absolute_error(y_test, preds)
mse = mean_squared_error(y_test, preds)
rmse = mse ** 0.5  # manually compute RMSE
r2 = r2_score(y_test, preds)

print('MAE:', round(mae, 3))
print('RMSE:', round(rmse, 3))
print('R2:', round(r2, 3))

joblib.dump(model, '../models/passenger_xgb.pkl')
print('✅ Model trained and saved to ../models/passenger_xgb.pkl')
