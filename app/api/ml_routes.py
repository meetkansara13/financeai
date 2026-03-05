from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user
from app import models

from app.ml.expense_forecast.predict import predict_month_end_expense
from app.ml.asset_risk.predict import predict_asset_risk

router = APIRouter(prefix="/api/v1/ml", tags=["ML"])


@router.get("/expense-forecast")
def expense_forecast(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    prediction = predict_month_end_expense(current_user.id, db)
    print("+"*20)
    print(prediction)
    print("+"*20)
    
    return {
        "predicted_expense": prediction
    }


@router.get("/asset-risk")
def asset_risk(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    risk = predict_asset_risk(current_user.id, db)
    return {
        "risk_score": risk
    }