from datetime import datetime
from sqlalchemy import extract
from app import models


def create_or_update_snapshot(user_id, db):
    """
    Creates or updates the current month's financial snapshot.
    """

    current_month = datetime.now().month
    current_year = datetime.now().year

    # Get only current month transactions (optimized query)
    transactions = db.query(models.Transaction).filter(
        models.Transaction.user_id == user_id,
        extract('month', models.Transaction.date) == current_month,
        extract('year', models.Transaction.date) == current_year
    ).all()

    income = sum(t.amount for t in transactions if t.type == "income")
    expense = sum(t.amount for t in transactions if t.type == "expense")

    existing = db.query(models.MonthlySnapshot).filter(
        models.MonthlySnapshot.user_id == user_id,
        models.MonthlySnapshot.month == current_month,
        models.MonthlySnapshot.year == current_year
    ).first()

    if existing:
        existing.income = income
        existing.expense = expense
        existing.savings = income - expense
    else:
        snapshot = models.MonthlySnapshot(
            user_id=user_id,
            month=current_month,
            year=current_year,
            income=income,
            expense=expense,
            savings=income - expense
        )
        db.add(snapshot)

    db.commit()