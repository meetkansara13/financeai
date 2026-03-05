from sqlalchemy.orm import Session
from sqlalchemy import func
from .. import models


def generate_ai_insights(user_id: int, db: Session):

    transactions = db.query(models.Transaction).filter(
        models.Transaction.user_id == user_id
    ).all()

    insights = []

    income = sum(t.amount for t in transactions if t.type == "income")
    expense = sum(t.amount for t in transactions if t.type == "expense")

    if income == 0:
        return ["No income data available yet."]

    savings = income - expense
    savings_rate = (savings / income) * 100

    # Savings insight
    if savings_rate < 20:
        insights.append("⚠ Your savings rate is below 20%. Consider reducing non-essential spending.")
    elif savings_rate < 35:
        insights.append("📊 Moderate savings performance. There is room for optimization.")
    else:
        insights.append("📈 Excellent savings discipline maintained.")

    # Category dominance insight
    category_totals = {}

    for t in transactions:
        if t.type == "expense":
            category_totals[t.category] = category_totals.get(t.category, 0) + t.amount

    if category_totals:
        top_category = max(category_totals, key=category_totals.get)
        top_value = category_totals[top_category]

        percentage = (top_value / expense) * 100 if expense > 0 else 0

        insights.append(
            f"💸 You spent {round(percentage, 1)}% of total expenses on {top_category}."
        )

        if percentage > 35:
            insights.append(f"🚨 High concentration of spending in {top_category} category.")

    # Risk indicator
    if expense > income * 0.85:
        insights.append("🔴 Risk Alert: Expenses exceed 85% of income.")

    return insights