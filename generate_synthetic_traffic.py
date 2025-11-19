import pandas as pd
import numpy as np
import random

# Load original dataset
df = pd.read_csv("data/traffic_data.csv")

synthetic_rows = []

time_slots = ["Morning", "Afternoon", "Evening", "Night"]

risk_levels = ["Low", "Medium", "High"]

# Generate 1000 synthetic rows
for i in range(1000):

    # pick a base row
    base = df.sample(1).iloc[0]

    # time slot might shift
    slot = random.choice(time_slots)

    # vary congestion realistically
    live_cong = max(5, min(95, base["Live_Congestion_Level(%)"] + np.random.normal(0, 10)))
    usual_cong = max(5, min(95, base["Usual_Congestion_Level(%)"] + np.random.normal(0, 6)))

    # speed decreases with congestion
    live_speed = max(5, 50 - (live_cong * 0.3) + np.random.normal(0, 2))

    # delay increases with congestion
    delay = max(0.2, (live_cong / 10) + np.random.normal(0, 1))

    # accident risk based on congestion
    if live_cong > 70:
        risk = "High"
    elif live_cong > 40:
        risk = "Medium"
    else:
        risk = "Low"

    synthetic_rows.append({
        "Date": "2025-10-" + str(random.randint(1, 30)),
        "Time_Slot": slot,
        "Live_Congestion_Level(%)": round(live_cong, 2),
        "Usual_Congestion_Level(%)": round(usual_cong, 2),
        "Live_Speed_kmph": round(live_speed, 2),
        "Delay_Minutes_per_10km": round(delay, 2),
        "Accident_Risk_Level": risk
    })

# Save synthetic dataset
syn_df = pd.DataFrame(synthetic_rows)
syn_df.to_csv("data/traffic_synthetic.csv", index=False)

print("✅ Generated 1000 synthetic rows → saved as traffic_synthetic.csv")
