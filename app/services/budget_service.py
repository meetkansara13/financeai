from sqlalchemy.orm import Session
from .. import models
from sqlalchemy import func
from datetime import datetime


def create_budget(user_id: int, category: str, limit: float, db: Session):

    existing = db.query(models.Budget).filter(
        models.Budget.user_id == user_id,
        models.Budget.category == category
    ).first()

    if existing:
        existing.monthly_limit = limit
    else:
        new_budget = models.Budget(
            category=category,
            monthly_limit=limit,
            user_id=user_id
        )
        db.add(new_budget)

    db.commit()

    return {"message": "Budget saved"}

def get_budget_status(user_id: int, db: Session):

    budgets = db.query(models.Budget).filter(
        models.Budget.user_id == user_id
    ).all()

    results = []

    for budget in budgets:

        spent = db.query(func.sum(models.Transaction.amount)).filter(
            models.Transaction.user_id == user_id,
            models.Transaction.type == "expense",
            models.Transaction.category == budget.category
        ).scalar() or 0

        percentage = (spent / budget.monthly_limit) * 100 if budget.monthly_limit > 0 else 0

        results.append({
            "category": budget.category,
            "spent": spent,
            "limit": budget.monthly_limit,
            "percentage": round(percentage, 2)
        })

    return results