import os
import joblib
from datetime import datetime
from calendar import monthrange
from app.ml.common.feature_engineering import build_expense_features

BASE_DIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")

model = None

def _load_model():
    global model
    if model is None:
        if not os.path.exists(MODEL_PATH):
            return None
        model = joblib.load(MODEL_PATH)
    return model


def predict_month_end_expense(current_expense, income):
    m = _load_model()
    if m is None:
        # Model not available — return a simple linear estimate
        return round(current_expense * 1.1, 2)

    today = datetime.now().day
    current_month = datetime.now().month
    current_year = datetime.now().year

    total_days = monthrange(current_year, current_month)[1]

    features = build_expense_features(
        current_expense,
        today,
        total_days,
        income
    )

    prediction = m.predict(features)[0]
    return round(prediction, 2)