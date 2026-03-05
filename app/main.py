from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from .database import engine, SessionLocal, get_db
from . import models, schemas
from .auth import hash_password, verify_password, create_access_token
from .auth import get_current_user
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, extract
from datetime import datetime, timedelta
from .utils import success_response
from fastapi import APIRouter
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Request
from fastapi.staticfiles import StaticFiles
from .services.analytics_service import get_dashboard_kpis, get_category_breakdown, get_monthly_trend, get_transactions
from .services.budget_service import create_budget, get_budget_status
from .services.ai_service import generate_ai_insights
from .services.ai_engine import generate_advanced_insights
from .services.profile_service import save_or_update_profile, get_profile_analysis
from .services.bot_service import chat_with_bot
from .services.ocr_verification_service import verify_document, get_verification_status
from app.api.ml_routes import router as ml_router
from app.services.snapshot_service import create_or_update_snapshot
from app.services.smart_transaction_engine import process_smart_transaction
from app.ml.expense_forecast.predict import predict_month_end_expense
from .services.notification_service import send_otp_sms, send_reset_email as notify_reset_email
from .services.market_service import get_market_data_cached
from .services.news_service import get_news_insights
import re, os, random, secrets


models.Base.metadata.create_all(bind=engine)

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

api_v1 = APIRouter(prefix="/api/v1", tags=["v1"])


@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("landing.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


# ══════════════════════════════════════
# AUTH
# ══════════════════════════════════════

@api_v1.post("/register")
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_pw = hash_password(user.password)
    new_user = models.User(name=user.name, email=user.email, password=hashed_pw, mobile_number=getattr(user,'mobile_number',None))
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return success_response("User registered successfully", {
        "user_id": new_user.id,
        "email": new_user.email
    })

@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@api_v1.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    db_user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not db_user or not verify_password(form_data.password, db_user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access_token = create_access_token(data={"sub": db_user.email})
    return {"access_token": access_token, "token_type": "bearer"}


# ── Forgot Password ──

@app.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page(request: Request):
    return templates.TemplateResponse("forgot-password.html", {"request": request})

@api_v1.post("/forgot-password/send-otp")
def send_otp(data: schemas.MobileSchema, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.mobile_number == data.mobile_number).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    otp = str(random.randint(100000, 999999))
    user.otp_code = otp
    user.otp_expiry = datetime.utcnow() + timedelta(minutes=5)
    db.commit()
    sent = send_otp_sms(data.mobile_number, otp)
    if not sent:
        print("OTP (SMS fallback):", otp)
    return success_response("OTP sent successfully")

@api_v1.post("/forgot-password/verify-otp")
def verify_otp(data: schemas.OTPSchema, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.mobile_number == data.mobile_number).first()
    if not user or user.otp_code != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    if datetime.utcnow() > user.otp_expiry:
        raise HTTPException(status_code=400, detail="OTP expired")
    return success_response("OTP verified")

@api_v1.post("/forgot-password/send-email")
def send_reset_email(data: schemas.EmailSchema, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email not found")
    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_expiry = datetime.utcnow() + timedelta(minutes=15)
    db.commit()
    reset_link = f"http://127.0.0.1:8000/reset-password/{token}"
    sent = notify_reset_email(data.email, token)
    if not sent:
        print("Reset link fallback:", reset_link)
    return success_response("Reset link sent to email")

@api_v1.post("/reset-password/{token}")
def reset_password(token: str, data: schemas.NewPasswordSchema, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.reset_token == token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid token")
    if datetime.utcnow() > user.reset_token_expiry:
        raise HTTPException(status_code=400, detail="Token expired")
    user.password = hash_password(data.new_password)
    user.reset_token = None
    user.reset_token_expiry = None
    db.commit()
    return success_response("Password reset successful")


# ══════════════════════════════════════
# TRANSACTIONS
# ══════════════════════════════════════

@api_v1.post("/transactions")
def add_transaction(
    transaction: schemas.TransactionCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    new_transaction = models.Transaction(
        amount=transaction.amount,
        type=transaction.type,
        category=transaction.category,
        description=transaction.description,
        user_id=current_user.id
    )
    db.add(new_transaction)
    db.commit()
    db.refresh(new_transaction)
    create_or_update_snapshot(current_user.id, db)
    return success_response("Transaction added successfully", {
        "transaction_id": new_transaction.id,
        "amount": new_transaction.amount,
        "category": new_transaction.category
    })


@api_v1.post("/smart-transaction")
def smart_transaction(
    data: schemas.SmartTransaction,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return process_smart_transaction(data.text, current_user, db)


@api_v1.get("/transactions-list")
def transactions_list(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return get_transactions(current_user.id, db)


@api_v1.delete("/transactions/{txn_id}")
def delete_transaction(
    txn_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    txn = db.query(models.Transaction).filter(
        models.Transaction.id == txn_id,
        models.Transaction.user_id == current_user.id
    ).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(txn)
    db.commit()
    return {"message": "Deleted successfully"}


@api_v1.get("/recent-transactions")
def recent_transactions(
    month: int = None,
    year: int = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    now = datetime.now()
    month = month or now.month
    year = year or now.year
    transactions = db.query(models.Transaction).filter(
        models.Transaction.user_id == current_user.id,
        func.extract('month', models.Transaction.date) == month,
        func.extract('year', models.Transaction.date) == year
    ).order_by(models.Transaction.date.desc()).limit(10).all()
    return [
        {
            "amount": t.amount,
            "type": t.type,
            "category": t.category,
            "description": t.description,
            "date": t.date.strftime("%d %b")
        }
        for t in transactions
    ]


@api_v1.get("/category-breakdown-month")
def category_breakdown_month(
    month: int = None,
    year: int = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    now = datetime.now()
    month = month or now.month
    year = year or now.year
    results = db.query(
        models.Transaction.category,
        func.sum(models.Transaction.amount)
    ).filter(
        models.Transaction.user_id == current_user.id,
        models.Transaction.type == "expense",
        func.extract("month", models.Transaction.date) == month,
        func.extract("year", models.Transaction.date) == year
    ).group_by(models.Transaction.category).all()
    return {
        "labels": [r[0] for r in results],
        "values": [float(r[1]) for r in results]
    }


# ══════════════════════════════════════
# SUMMARY & HEALTH
# ══════════════════════════════════════

@api_v1.get("/monthly-summary")
def monthly_summary(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    now = datetime.now()
    transactions = db.query(models.Transaction).filter(
        models.Transaction.user_id == current_user.id
    ).all()
    income  = sum(t.amount for t in transactions if t.date.month == now.month and t.date.year == now.year and t.type == "income")
    expense = sum(t.amount for t in transactions if t.date.month == now.month and t.date.year == now.year and t.type == "expense")
    return success_response("Monthly summary fetched", {
        "month": now.month, "income": income, "expense": expense, "net_savings": income - expense
    })


@api_v1.get("/financial-health")
def financial_health(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    transactions = db.query(models.Transaction).filter(models.Transaction.user_id == current_user.id).all()
    income  = sum(t.amount for t in transactions if t.type == "income")
    expense = sum(t.amount for t in transactions if t.type == "expense")
    if income == 0:
        return success_response("Financial health calculated", {"score": 0, "message": "No income data"})
    savings_rate = (income - expense) / income
    score = 40 if savings_rate > 0.4 else 25 if savings_rate > 0.2 else 10
    if expense < income:  score += 30
    if expense > income * 0.9: score -= 20
    score = max(0, min(score, 100))
    return success_response("Financial health calculated", {
        "score": score, "income": income, "expense": expense,
        "savings_rate": round(savings_rate * 100, 2)
    })


# ══════════════════════════════════════
# ANALYTICS
# ══════════════════════════════════════

@api_v1.get("/dashboard-data")
def dashboard_data(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_dashboard_kpis(current_user.id, db)

@api_v1.get("/category-breakdown")
def category_breakdown(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    results = db.query(models.Transaction.category, func.sum(models.Transaction.amount)).filter(
        models.Transaction.user_id == current_user.id, models.Transaction.type == "expense"
    ).group_by(models.Transaction.category).all()
    return [{"category": r[0], "total": r[1]} for r in results]

@api_v1.get("/category-breakdown-advanced")
def category_breakdown_advanced(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_category_breakdown(current_user.id, db)

@api_v1.get("/monthly-trend")
def monthly_trend(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_monthly_trend(current_user.id, db)

@api_v1.get("/advanced-insights")
def advanced_insights(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return generate_advanced_insights(current_user.id, db)

@api_v1.get("/ai-insights")
def ai_insights(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return generate_ai_insights(current_user.id, db)

@api_v1.get("/overspending-alert")
def overspending_alert(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    transactions = db.query(models.Transaction).filter(models.Transaction.user_id == current_user.id).all()
    income  = sum(t.amount for t in transactions if t.type == "income")
    expense = sum(t.amount for t in transactions if t.type == "expense")
    if income > 0 and expense > income * 0.9:
        return {"alert": "Overspending risk 🚨 Expenses > 90% of income"}
    return {"alert": None}


# ══════════════════════════════════════
# BUDGETS
# ══════════════════════════════════════

@api_v1.post("/budgets")
def save_budget(
    budget: schemas.BudgetCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return create_budget(current_user.id, budget.category, budget.monthly_limit, db)

@api_v1.get("/budgets-status")
def budget_status(
    month: int = None, year: int = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    now = datetime.now()
    month = month or now.month
    year  = year  or now.year
    budgets = db.query(models.Budget).filter(models.Budget.user_id == current_user.id).all()
    results = []
    for budget in budgets:
        spent = db.query(func.sum(models.Transaction.amount)).filter(
            models.Transaction.user_id == current_user.id,
            models.Transaction.type == "expense",
            models.Transaction.category == budget.category,
            func.extract('month', models.Transaction.date) == month,
            func.extract('year',  models.Transaction.date) == year
        ).scalar() or 0
        percentage = (spent / budget.monthly_limit) * 100 if budget.monthly_limit > 0 else 0
        results.append({"category": budget.category, "spent": spent, "limit": budget.monthly_limit, "percentage": round(percentage, 2)})
    return results


# ══════════════════════════════════════
# PROFILE
# ══════════════════════════════════════

@api_v1.post("/financial-profile")
def save_profile(
    profile: schemas.FinancialProfileCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    save_or_update_profile(current_user.id, profile, db)
    return {"message": "Profile saved successfully"}

@api_v1.get("/financial-profile")
def get_profile(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    result = get_profile_analysis(current_user.id, db)
    if not result:
        raise HTTPException(status_code=404, detail="Profile not found")
    return result


# ══════════════════════════════════════
# WEALTH
# ══════════════════════════════════════

@api_v1.get("/wealth-summary")
def wealth_summary(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(models.FinancialProfile).filter(
        models.FinancialProfile.user_id == current_user.id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    total_assets = profile.stocks + profile.bonds + profile.real_estate + profile.gold + profile.cash_savings
    net_worth    = total_assets - profile.loans
    now = datetime.now()
    transactions = db.query(models.Transaction).filter(models.Transaction.user_id == current_user.id).all()
    monthly_income  = sum(t.amount for t in transactions if t.date.month == now.month and t.date.year == now.year and t.type == "income")
    monthly_expense = sum(t.amount for t in transactions if t.date.month == now.month and t.date.year == now.year and t.type == "expense")
    savings_rate = ((monthly_income - monthly_expense) / monthly_income * 100) if monthly_income > 0 else 0
    return {
        "portfolio_value": total_assets, "total_liabilities": profile.loans,
        "net_worth": net_worth, "monthly_income": monthly_income,
        "monthly_expense": monthly_expense, "savings_rate": round(savings_rate, 2)
    }


@api_v1.get("/dashboard-overview")
def dashboard_overview(
    month: int = None, year: int = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    now   = datetime.now()
    month = month or now.month
    year  = year  or now.year
    snapshot = db.query(models.MonthlySnapshot).filter(
        models.MonthlySnapshot.user_id == current_user.id,
        models.MonthlySnapshot.month   == month,
        models.MonthlySnapshot.year    == year
    ).first()
    monthly_income  = snapshot.income   if snapshot else 0
    monthly_expense = snapshot.expense  if snapshot else 0
    monthly_savings = snapshot.savings  if snapshot else 0
    profile = db.query(models.FinancialProfile).filter(
        models.FinancialProfile.user_id == current_user.id
    ).first()
    if not profile:
        return {"monthly": {"income": monthly_income, "expense": monthly_expense, "savings": monthly_savings}, "overall": None}
    income_sum  = db.query(func.sum(models.Transaction.amount)).filter(models.Transaction.user_id == current_user.id, models.Transaction.type == "income").scalar()  or 0
    expense_sum = db.query(func.sum(models.Transaction.amount)).filter(models.Transaction.user_id == current_user.id, models.Transaction.type == "expense").scalar() or 0
    cash_balance = income_sum - expense_sum
    total_assets = profile.stocks + profile.bonds + profile.real_estate + profile.gold + cash_balance
    net_worth    = total_assets - profile.loans
    debt_ratio   = (profile.loans / total_assets * 100) if total_assets > 0 else 0
    return {
        "selected_month": month, "selected_year": year,
        "monthly": {"income": monthly_income, "expense": monthly_expense, "savings": monthly_savings},
        "overall": {"assets": total_assets, "liabilities": profile.loans, "net_worth": net_worth, "debt_ratio": round(debt_ratio, 2)}
    }


@api_v1.get("/savings-prediction")
def savings_prediction(
    month: int = None, year: int = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    now   = datetime.now()
    month = month or now.month
    year  = year  or now.year
    snapshot = db.query(models.MonthlySnapshot).filter(
        models.MonthlySnapshot.user_id == current_user.id,
        models.MonthlySnapshot.month   == month,
        models.MonthlySnapshot.year    == year
    ).first()
    if not snapshot:
        return {"predicted_expense": 0, "predicted_savings": 0, "prediction_month": f"{month}-{year}"}
    predicted_expense = predict_month_end_expense(snapshot.expense, snapshot.income)
    predicted_savings = snapshot.income - predicted_expense
    if predicted_savings > snapshot.income * 0.3:
        message = f"📈 Excellent! On track to save ₹{int(predicted_savings):,} this month."
    elif predicted_savings > 0:
        message = f"💡 Moderate savings expected: ₹{int(predicted_savings):,}. Consider cutting non-essentials."
    else:
        message = f"⚠️ Overspend risk! Projected deficit of ₹{abs(int(predicted_savings)):,} by month end."
    return {
        "prediction_month": f"{month}-{year}",
        "current_income": snapshot.income, "current_expense": snapshot.expense,
        "predicted_expense": predicted_expense, "predicted_savings": predicted_savings,
        "savings_message": message
    }


@api_v1.post("/ai-purchase-decision")
def ai_purchase_decision(
    amount: float,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    now = datetime.now()
    transactions = db.query(models.Transaction).filter(models.Transaction.user_id == current_user.id).all()
    income  = sum(t.amount for t in transactions if t.date.month == now.month and t.date.year == now.year and t.type == "income")
    expense = sum(t.amount for t in transactions if t.date.month == now.month and t.date.year == now.year and t.type == "expense")
    remaining = income - expense
    if amount <= remaining * 0.5:       decision = "✅ You can afford this purchase comfortably."
    elif amount <= remaining:           decision = "⚠️ Purchase possible but your savings will reduce significantly."
    else:                               decision = "❌ Not recommended. This exceeds your remaining monthly budget."
    return {"decision": decision, "remaining_after_purchase": remaining - amount}


# ══════════════════════════════════════
# AI BOT
# ══════════════════════════════════════

@api_v1.post("/ai-bot")
async def ai_bot(
    request: schemas.ChatRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    reply = await chat_with_bot(
        user_id=current_user.id,
        message=request.message,
        history=[h.dict() for h in request.history],
        db=db
    )
    return {"reply": reply}


# ══════════════════════════════════════
# DOCUMENT UPLOAD & OCR VERIFICATION
# ══════════════════════════════════════

@api_v1.post("/upload-document")
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = Form(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload PDF/image → OCR extracts PAN + name + amount
    → cross-checks against profile → stores result → returns score.
    doc_type: salary_slip | itr | demat | property | loan | credit_card
    """
    allowed = ["salary_slip", "itr", "demat", "property", "loan", "credit_card"]
    if doc_type not in allowed:
        raise HTTPException(status_code=400, detail=f"Invalid doc_type. Must be one of: {allowed}")
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 10MB.")
    result = await verify_document(
        file_bytes=contents,
        filename=file.filename,
        doc_type=doc_type,
        user_id=current_user.id,
        db=db
    )
    return result


@api_v1.get("/verification-status")
def verification_status(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns overall verification % and per-category breakdown."""
    return get_verification_status(current_user.id, db)


# ══════════════════════════════════════
# PAGE ROUTES
# ══════════════════════════════════════


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/analytics", response_class=HTMLResponse)
def analytics_page(request: Request):
    return templates.TemplateResponse("analytics.html", {"request": request})

@app.get("/transactions", response_class=HTMLResponse)
def transactions_page(request: Request):
    return templates.TemplateResponse("transactions.html", {"request": request})

@app.get("/budgets", response_class=HTMLResponse)
def budgets_page(request: Request):
    return templates.TemplateResponse("budgets.html", {"request": request})

@app.get("/ai", response_class=HTMLResponse)
def ai_page(request: Request):
    return templates.TemplateResponse("ai.html", {"request": request})

@app.get("/wealth", response_class=HTMLResponse)
def wealth_page(request: Request):
    return templates.TemplateResponse("wealth_planner.html", {"request": request})


@api_v1.get("/market-data")
def market_data(current_user: models.User = Depends(get_current_user)):
    """Returns live investment prices from Yahoo Finance."""
    try:
        data = get_market_data_cached()
        return {"instruments": data, "status": "ok"}
    except Exception as e:
        return {"instruments": [], "status": "error", "detail": str(e)}


@api_v1.get("/news-insights")
def news_insights(current_user: models.User = Depends(get_current_user)):
    """Returns AI financial insights derived from latest Indian news."""
    import os
    gnews_key = os.getenv("GNEWS_API_KEY", "")
    return get_news_insights(gnews_api_key=gnews_key)


app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(ml_router)
app.include_router(api_v1)