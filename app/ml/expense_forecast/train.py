import numpy as np
import joblib
import os
from sklearn.linear_model import LinearRegression

# ------------------------------
# Simulated training data
# ------------------------------

X = []
y = []

for income in [30000, 50000, 80000]:
    for expense in [10000, 20000, 30000]:
        for day in [10, 15, 20]:
            total_days = 30
            expense_ratio = expense / income
            daily_avg = expense / day
            remaining = total_days - day

            features = [
                expense,
                day,
                total_days,
                expense_ratio,
                daily_avg,
                remaining
            ]

            predicted_month_end = daily_avg * total_days

            X.append(features)
            y.append(predicted_month_end)

X = np.array(X)
y = np.array(y)

model = LinearRegression()
model.fit(X, y)

# ------------------------------
# Save model correctly
# ------------------------------

BASE_DIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")

joblib.dump(model, MODEL_PATH)

print("Model trained and saved successfully.")
print("Saved at:", MODEL_PATH)