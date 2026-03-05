from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import Session
from app import models

def generate_advanced_insights(user_id: int, db: Session):

    now = datetime.now()
    current_month = now.month
    current_year = now.year

    transactions = db.query(models.Transaction).filter(
        models.Transaction.user_id == user_id,
        func.extract('month', models.Transaction.date) == current_month,
        func.extract('year', models.Transaction.date) == current_year
    ).all()

    income = sum(t.amount for t in transactions if t.type == "income")
    expense = sum(t.amount for t in transactions if t.type == "expense")

    savings = income - expense

    insights = []
    alerts = []

    # ==============================
    # 1️⃣ Savings Analysis
    # ==============================
    savings_rate = 0
    if income > 0:
        savings_rate = (savings / income)

        if savings_rate < 0.1:
            alerts.append("⚠ Very low savings rate this month.")
        elif savings_rate < 0.25:
            insights.append("💡 Moderate savings. Try reaching 30% savings rate.")
        else:
            insights.append("📈 Excellent savings performance this month.")

    # ==============================
    # 2️⃣ Budget Violations
    # ==============================
    budgets = db.query(models.Budget).filter(
        models.Budget.user_id == user_id
    ).all()

    for budget in budgets:
        spent = sum(
            t.amount for t in transactions
            if t.category == budget.category and t.type == "expense"
        )

        percentage = (spent / budget.monthly_limit) if budget.monthly_limit > 0 else 0

        if percentage >= 1:
            alerts.append(f"🔴 Overspent in {budget.category.upper()} by ₹{round(spent - budget.monthly_limit, 2)}")
        elif percentage >= 0.8:
            alerts.append(f"🟠 {budget.category.upper()} budget almost exhausted ({round(percentage*100, 1)}%)")

    # ==============================
    # 3️⃣ Category Dominance
    # ==============================
    category_totals = {}
    for t in transactions:
        if t.type == "expense":
            category_totals[t.category] = category_totals.get(t.category, 0) + t.amount

    if category_totals:
        highest_category = max(category_totals, key=category_totals.get)
        insights.append(f"📊 Highest spending category: {highest_category.upper()}")

    # ==============================
    # 4️⃣ Risk Indicator
    # ==============================
    risk_level = "LOW"
    expense_ratio = 0

    if income > 0:
        expense_ratio = expense / income

        if expense_ratio > 0.9:
            risk_level = "HIGH"
        elif expense_ratio > 0.7:
            risk_level = "MEDIUM"

    # ==============================
    # 5️⃣ Monthly Projection
    # ==============================
    days_passed = now.day
    total_days = 30

    projected_expense = (expense / days_passed) * total_days if days_passed > 0 else expense

    if projected_expense > income:
        alerts.append("⚠ At current pace, you may exceed your income by month-end.")

    # ==============================
    # 6️⃣ Financial Score (0–100)
    # ==============================
    financial_score = 0

    # Savings Performance (40%)
    if savings_rate >= 0.4:
        financial_score += 40
    else:
        financial_score += savings_rate * 100 * 0.4

    # Expense Discipline (30%)
    if expense_ratio <= 0.5:
        financial_score += 30
    else:
        financial_score += (1 - expense_ratio) * 100 * 0.3

    # Emergency Strength (30%)
    if expense > 0:
        months_cover = savings / expense
        if months_cover >= 6:
            financial_score += 30
        else:
            financial_score += (months_cover / 6) * 30

    financial_score = round(min(financial_score, 100), 2)

    # ==============================
    # 7️⃣ 5-Year Projection
    # ==============================
    monthly_savings = savings / 12 if savings > 0 else 0
    annual_return = 0.10
    r = annual_return / 12
    months = 60

    future_projection = 0
    if monthly_savings > 0:
        future_projection = monthly_savings * (((1 + r) ** months - 1) / r)

    # ==============================
    # 8️⃣ Safe Expense Limit
    # ==============================
    safe_expense_limit = income * 0.5

    return {
        "risk_level": risk_level,
        "financial_score": financial_score,
        "net_worth": savings,
        "future_projection_5yr": round(future_projection, 2),
        "expense_ratio": round(expense_ratio, 2),
        "savings_rate": round(savings_rate, 2),
        "safe_expense_limit": round(safe_expense_limit, 2),
        "projected_expense": round(projected_expense, 2),
        "suggestions": insights,
        "alerts": alerts
    }