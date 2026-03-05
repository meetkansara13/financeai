import os
import joblib
from datetime import datetime
from calendar import monthrange
from app.ml.common.feature_engineering import build_expense_features

BASE_DIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")

model = joblib.load(MODEL_PATH)


def predict_month_end_expense(current_expense, income):
    

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

    prediction = model.predict(features)[0]

    return round(prediction, 2)