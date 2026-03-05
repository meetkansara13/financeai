import numpy as np

def build_expense_features(current_expense, day_of_month, total_days, income):
    """
    Build feature vector for expense prediction model.
    """

    expense_ratio = current_expense / income if income > 0 else 0
    daily_avg = current_expense / day_of_month if day_of_month > 0 else 0
    remaining_days = total_days - day_of_month

    return np.array([
        current_expense,
        day_of_month,
        total_days,
        expense_ratio,
        daily_avg,
        remaining_days
    ]).reshape(1, -1)