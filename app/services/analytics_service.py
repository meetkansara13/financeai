from sqlalchemy.orm import Session
from sqlalchemy import func
from .. import models
from datetime import datetime


def get_dashboard_kpis(user_id: int, db: Session):

    transactions = db.query(models.Transaction).filter(
        models.Transaction.user_id == user_id
    ).all()

    income = sum(t.amount for t in transactions if t.type == "income")
    expense = sum(t.amount for t in transactions if t.type == "expense")

    savings = income - expense
    savings_rate = (savings / income * 100) if income > 0 else 0

    # Financial Score Logic (Improved)
    score = 0

    if savings_rate > 40:
        score += 40
    elif savings_rate > 25:
        score += 30
    elif savings_rate > 15:
        score += 20
    else:
        score += 10

    if expense < income * 0.7:
        score += 30
    elif expense < income * 0.85:
        score += 20
    else:
        score += 5

    if savings > 0:
        score += 20

    score = min(score, 100)

    return {
        "income": income,
        "expense": expense,
        "savings": savings,
        "savings_rate": round(savings_rate, 2),
        "score": score
    }


def get_category_breakdown(user_id: int, db: Session):

    results = db.query(
        models.Transaction.category,
        func.sum(models.Transaction.amount)
    ).filter(
        models.Transaction.user_id == user_id,
        models.Transaction.type == "expense"
    ).group_by(models.Transaction.category).all()

    labels = []
    values = []

    for r in results:
        labels.append(r[0])
        values.append(float(r[1]))

    return {
        "labels": labels,
        "values": values
    }
    
def get_monthly_trend(user_id: int, db: Session):

    from sqlalchemy import extract
    import calendar

    results = db.query(
        extract("month", models.Transaction.date).label("month"),
        models.Transaction.type,
        func.sum(models.Transaction.amount)
    ).filter(
        models.Transaction.user_id == user_id
    ).group_by("month", models.Transaction.type).all()

    # Prepare empty structure for 12 months
    monthly_data = {
        m: {"income": 0, "expense": 0}
        for m in range(1, 13)
    }

    for month, txn_type, total in results:
        month = int(month)
        monthly_data[month][txn_type] = float(total)

    labels = []
    income = []
    expense = []

    for m in range(1, 13):
        labels.append(calendar.month_abbr[m])
        income.append(monthly_data[m]["income"])
        expense.append(monthly_data[m]["expense"])

    return {
        "labels": labels,
        "income": income,
        "expense": expense
    }

def get_transactions(user_id: int, db: Session):

    transactions = db.query(models.Transaction).filter(
        models.Transaction.user_id == user_id
    ).order_by(models.Transaction.date.desc()).all()

    return [
        {
            "id": t.id,
            "amount": t.amount,
            "type": t.type,
            "category": t.category,
            "description": t.description,
            "date": t.date.strftime("%Y-%m-%d")
        }
        for t in transactions
    ]