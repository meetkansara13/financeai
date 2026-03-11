from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv
load_dotenv()
from .database import engine, SessionLocal, get_db
from . import models, schemas
from .auth import hash_password, verify_password, create_access_token, get_current_user
from .security import (
    SecurityHeadersMiddleware, CORS_CONFIG,
    rate_limit, check_login_lockout, record_failed_login, clear_failed_login
)
from .utils import success_response
from fastapi import APIRouter
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
import secrets
import os
import re

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    docs_url=None,        # disable /docs in production
    redoc_url=None,       # disable /redoc in production
    openapi_url=None,     # disable /openapi.json in production
)

# ── MIDDLEWARE (order matters — outermost first) ──────────────────────────────
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CORSMiddleware, **CORS_CONFIG)


# ── GLOBAL ERROR HANDLER — never leak internals ───────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Log internally but return a safe generic message
    import traceback
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again later."}
    )


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

api_v1 = APIRouter(prefix="/api/v1", tags=["v1"])


# ══════════════════════════════════════
# PAGE ROUTES
# ══════════════════════════════════════

@app.get("/",               response_class=HTMLResponse)
def root(request: Request):                    return templates.TemplateResponse("landing.html",       {"request": request})
@app.get("/login",          response_class=HTMLResponse)
def login_page(request: Request):              return templates.TemplateResponse("login.html",          {"request": request})
@app.get("/register",       response_class=HTMLResponse)
def register_page(request: Request):           return templates.TemplateResponse("register.html",       {"request": request})
@app.get("/forgot-password",response_class=HTMLResponse)
def forgot_password_page(request: Request):    return templates.TemplateResponse("forgot-password.html",{"request": request})
@app.get("/dashboard",      response_class=HTMLResponse)
def dashboard_page(request: Request):          return templates.TemplateResponse("dashboard.html",      {"request": request})
@app.get("/analytics",      response_class=HTMLResponse)
def analytics_page(request: Request):          return templates.TemplateResponse("analytics.html",      {"request": request})
@app.get("/transactions",   response_class=HTMLResponse)
def transactions_page(request: Request):       return templates.TemplateResponse("transactions.html",   {"request": request})
@app.get("/budgets",        response_class=HTMLResponse)
def budgets_page(request: Request):            return templates.TemplateResponse("budgets.html",        {"request": request})
@app.get("/ai",             response_class=HTMLResponse)
def ai_page(request: Request):                 return templates.TemplateResponse("ai.html",             {"request": request})
@app.get("/wealth",         response_class=HTMLResponse)
def wealth_page(request: Request):             return templates.TemplateResponse("wealth_planner.html", {"request": request})
@app.get("/profile",        response_class=HTMLResponse)
def profile_page(request: Request):            return templates.TemplateResponse("profile.html",        {"request": request})
@app.get("/settings",       response_class=HTMLResponse)
def settings_page(request: Request):           return templates.TemplateResponse("settings.html",       {"request": request})
@app.get("/invite",         response_class=HTMLResponse)
def invite_page(request: Request):             return templates.TemplateResponse("invite.html",         {"request": request})
@app.get("/gift",           response_class=HTMLResponse)
def gift_page(request: Request):               return templates.TemplateResponse("gift.html",           {"request": request})
@app.get("/wallet",         response_class=HTMLResponse)
def wallet_page(request: Request):             return templates.TemplateResponse("wallet.html",         {"request": request})
@app.get("/notifications",  response_class=HTMLResponse)
def notifications_page(request: Request):      return templates.TemplateResponse("notifications.html",  {"request": request})


# ══════════════════════════════════════
# AUTH
# ══════════════════════════════════════

@api_v1.post("/register")
def register(user: schemas.UserCreate, request: Request, db: Session = Depends(get_db)):
    # Rate limit: 5 registrations per IP per hour
    rate_limit(f"register:{request.client.host}", limit=5, window_seconds=3600)

    existing = db.query(models.User).filter(models.User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = models.User(
        name=user.name,
        email=user.email,
        password=hash_password(user.password),
        mobile_number=user.mobile_number,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return success_response("User registered successfully", {
        "user_id": new_user.id,
        "email": new_user.email,
    })


@api_v1.post("/login")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    ip = request.client.host
    email = form_data.username.lower().strip()

    # Rate limit: 20 attempts per IP per 15 minutes
    rate_limit(f"login:ip:{ip}", limit=20, window_seconds=900)

    # Account lockout check
    check_login_lockout(f"login:user:{email}")

    db_user = db.query(models.User).filter(models.User.email == email).first()
    if not db_user or not verify_password(form_data.password, db_user.password):
        record_failed_login(f"login:user:{email}")
        # Same error for both "user not found" and "wrong password" — no enumeration
        raise HTTPException(status_code=401, detail="Invalid email or password")

    clear_failed_login(f"login:user:{email}")
    access_token = create_access_token(data={"sub": db_user.email})
    return {"access_token": access_token, "token_type": "bearer"}


# ── Forgot Password ──────────────────────────────────────────────────────────

@api_v1.post("/forgot-password/send-otp")
def send_otp(data: schemas.MobileSchema, request: Request, db: Session = Depends(get_db)):
    rate_limit(f"otp:{request.client.host}", limit=5, window_seconds=600)

    user = db.query(models.User).filter(models.User.mobile_number == data.mobile_number).first()
    # Always return success — don't reveal whether mobile is registered
    if user:
        otp = str(secrets.randbelow(900000) + 100000)   # cryptographically secure
        user.otp_code   = otp
        user.otp_expiry = datetime.utcnow() + timedelta(minutes=5)
        db.commit()
        sent = send_otp_sms(data.mobile_number, otp)
        if not sent:
            print("OTP (SMS fallback):", otp)  # server log only

    return success_response("If this number is registered, an OTP has been sent")


@api_v1.post("/forgot-password/verify-otp")
def verify_otp(data: schemas.OTPSchema, request: Request, db: Session = Depends(get_db)):
    rate_limit(f"otp-verify:{request.client.host}", limit=10, window_seconds=600)

    user = db.query(models.User).filter(models.User.mobile_number == data.mobile_number).first()
    if not user or not user.otp_code:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    if datetime.utcnow() > user.otp_expiry:
        raise HTTPException(status_code=400, detail="OTP expired")
    if not secrets.compare_digest(user.otp_code, data.otp):   # timing-safe comparison
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # Clear OTP after successful use — one-time only
    user.otp_code   = None
    user.otp_expiry = None
    db.commit()
    return success_response("OTP verified")


@api_v1.post("/forgot-password/send-email")
def send_reset_email(data: schemas.EmailSchema, request: Request, db: Session = Depends(get_db)):
    rate_limit(f"reset-email:{request.client.host}", limit=5, window_seconds=600)

    user = db.query(models.User).filter(models.User.email == data.email).first()
    # Always return success — don't reveal whether email is registered
    if user:
        token = secrets.token_urlsafe(32)
        user.reset_token        = token
        user.reset_token_expiry = datetime.utcnow() + timedelta(minutes=15)
        db.commit()
        sent = notify_reset_email(data.email, token)
        if not sent:
            print("Reset token (fallback):", token)  # server log only

    return success_response("If this email is registered, a reset link has been sent")


@api_v1.post("/reset-password/{token}")
def reset_password(token: str, data: schemas.NewPasswordSchema, request: Request, db: Session = Depends(get_db)):
    rate_limit(f"reset-pw:{request.client.host}", limit=10, window_seconds=600)

    if len(token) > 100:
        raise HTTPException(status_code=400, detail="Invalid token")

    user = db.query(models.User).filter(models.User.reset_token == token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    if datetime.utcnow() > user.reset_token_expiry:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user.password           = hash_password(data.new_password)
    user.reset_token        = None
    user.reset_token_expiry = None
    db.commit()
    return success_response("Password reset successful")


# ══════════════════════════════════════
# TRANSACTIONS
# ══════════════════════════════════════

@api_v1.post("/transactions")
def add_transaction(
    transaction: schemas.TransactionCreate,
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rate_limit(f"txn:{current_user.id}", limit=60, window_seconds=60)

    new_txn = models.Transaction(
        amount=transaction.amount,
        type=transaction.type,
        category=transaction.category,
        description=transaction.description,
        date=transaction.date,
        user_id=current_user.id,
    )
    db.add(new_txn)
    db.commit()
    db.refresh(new_txn)
    create_or_update_snapshot(current_user.id, db)
    return success_response("Transaction added successfully", {
        "transaction_id": new_txn.id,
        "amount": new_txn.amount,
        "category": new_txn.category,
    })


@api_v1.post("/smart-transaction")
def smart_transaction(
    data: schemas.SmartTransaction,
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rate_limit(f"smart-txn:{current_user.id}", limit=30, window_seconds=60)
    return process_smart_transaction(data.text, current_user, db)


@api_v1.get("/transactions-list")
def transactions_list(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_transactions(current_user.id, db)


@api_v1.delete("/transactions/{txn_id}")
def delete_transaction(
    txn_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    txn = db.query(models.Transaction).filter(
        models.Transaction.id == txn_id,
        models.Transaction.user_id == current_user.id,   # ownership enforced
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
    db: Session = Depends(get_db),
):
    now   = datetime.now()
    month = month or now.month
    year  = year  or now.year
    if not (1 <= month <= 12) or not (2000 <= year <= 2100):
        raise HTTPException(status_code=400, detail="Invalid month or year")

    txns = db.query(models.Transaction).filter(
        models.Transaction.user_id == current_user.id,
        func.extract("month", models.Transaction.date) == month,
        func.extract("year",  models.Transaction.date) == year,
    ).order_by(models.Transaction.date.desc()).limit(10).all()

    return [
        {"amount": t.amount, "type": t.type, "category": t.category,
         "description": t.description, "date": t.date.strftime("%d %b")}
        for t in txns
    ]


@api_v1.get("/category-breakdown-month")
def category_breakdown_month(
    month: int = None,
    year: int = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now   = datetime.now()
    month = month or now.month
    year  = year  or now.year
    if not (1 <= month <= 12) or not (2000 <= year <= 2100):
        raise HTTPException(status_code=400, detail="Invalid month or year")

    results = db.query(
        models.Transaction.category,
        func.sum(models.Transaction.amount),
    ).filter(
        models.Transaction.user_id == current_user.id,
        models.Transaction.type == "expense",
        func.extract("month", models.Transaction.date) == month,
        func.extract("year",  models.Transaction.date) == year,
    ).group_by(models.Transaction.category).all()

    return {"labels": [r[0] for r in results], "values": [float(r[1]) for r in results]}


# ══════════════════════════════════════
# SUMMARY & HEALTH
# ══════════════════════════════════════

@api_v1.get("/monthly-summary")
def monthly_summary(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    now = datetime.now()
    txns = db.query(models.Transaction).filter(models.Transaction.user_id == current_user.id).all()
    income  = sum(t.amount for t in txns if t.date.month == now.month and t.date.year == now.year and t.type == "income")
    expense = sum(t.amount for t in txns if t.date.month == now.month and t.date.year == now.year and t.type == "expense")
    return success_response("Monthly summary fetched", {
        "month": now.month, "income": income, "expense": expense, "net_savings": income - expense
    })


@api_v1.get("/financial-health")
def financial_health(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    txns    = db.query(models.Transaction).filter(models.Transaction.user_id == current_user.id).all()
    income  = sum(t.amount for t in txns if t.type == "income")
    expense = sum(t.amount for t in txns if t.type == "expense")
    if income == 0:
        return success_response("Financial health calculated", {"score": 0, "message": "No income data"})
    savings_rate = (income - expense) / income
    score = 40 if savings_rate > 0.4 else 25 if savings_rate > 0.2 else 10
    if expense < income:   score += 30
    if expense > income * 0.9: score -= 20
    score = max(0, min(score, 100))
    return success_response("Financial health calculated", {
        "score": score, "income": income, "expense": expense,
        "savings_rate": round(savings_rate * 100, 2),
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
    txns    = db.query(models.Transaction).filter(models.Transaction.user_id == current_user.id).all()
    income  = sum(t.amount for t in txns if t.type == "income")
    expense = sum(t.amount for t in txns if t.type == "expense")
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
    db: Session = Depends(get_db),
):
    return create_budget(current_user.id, budget.category, budget.monthly_limit, db)


@api_v1.get("/budgets-status")
def budget_status(
    month: int = None, year: int = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now   = datetime.now()
    month = month or now.month
    year  = year  or now.year
    if not (1 <= month <= 12) or not (2000 <= year <= 2100):
        raise HTTPException(status_code=400, detail="Invalid month or year")

    budgets = db.query(models.Budget).filter(models.Budget.user_id == current_user.id).all()
    results = []
    for b in budgets:
        spent = db.query(func.sum(models.Transaction.amount)).filter(
            models.Transaction.user_id == current_user.id,
            models.Transaction.type == "expense",
            models.Transaction.category == b.category,
            func.extract("month", models.Transaction.date) == month,
            func.extract("year",  models.Transaction.date) == year,
        ).scalar() or 0
        pct = (spent / b.monthly_limit * 100) if b.monthly_limit > 0 else 0
        results.append({"category": b.category, "spent": spent,
                         "limit": b.monthly_limit, "percentage": round(pct, 2)})
    return results


# ══════════════════════════════════════
# PROFILE
# ══════════════════════════════════════

@api_v1.post("/financial-profile")
def save_profile(
    profile: schemas.FinancialProfileCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    save_or_update_profile(current_user.id, profile, db)
    return {"message": "Profile saved successfully"}

@api_v1.get("/financial-profile")
def get_profile(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = get_profile_analysis(current_user.id, db)
    if not result:
        raise HTTPException(status_code=404, detail="Profile not found")
    return result


# ══════════════════════════════════════
# WEALTH
# ══════════════════════════════════════

@api_v1.get("/wealth-summary")
def wealth_summary(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(models.FinancialProfile).filter(
        models.FinancialProfile.user_id == current_user.id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    total_assets = profile.stocks + profile.bonds + profile.real_estate + profile.gold + profile.cash_savings
    net_worth    = total_assets - profile.loans
    now = datetime.now()
    txns = db.query(models.Transaction).filter(models.Transaction.user_id == current_user.id).all()
    monthly_income  = sum(t.amount for t in txns if t.date.month == now.month and t.date.year == now.year and t.type == "income")
    monthly_expense = sum(t.amount for t in txns if t.date.month == now.month and t.date.year == now.year and t.type == "expense")
    savings_rate = ((monthly_income - monthly_expense) / monthly_income * 100) if monthly_income > 0 else 0
    return {"portfolio_value": total_assets, "total_liabilities": profile.loans,
            "net_worth": net_worth, "monthly_income": monthly_income,
            "monthly_expense": monthly_expense, "savings_rate": round(savings_rate, 2)}


@api_v1.get("/dashboard-overview")
def dashboard_overview(
    month: int = None, year: int = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now   = datetime.now()
    month = month or now.month
    year  = year  or now.year
    if not (1 <= month <= 12) or not (2000 <= year <= 2100):
        raise HTTPException(status_code=400, detail="Invalid month or year")

    snapshot = db.query(models.MonthlySnapshot).filter(
        models.MonthlySnapshot.user_id == current_user.id,
        models.MonthlySnapshot.month == month,
        models.MonthlySnapshot.year  == year,
    ).first()
    monthly_income  = snapshot.income  if snapshot else 0
    monthly_expense = snapshot.expense if snapshot else 0
    monthly_savings = snapshot.savings if snapshot else 0
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
        "overall": {"assets": total_assets, "liabilities": profile.loans, "net_worth": net_worth, "debt_ratio": round(debt_ratio, 2)},
    }


@api_v1.get("/savings-prediction")
def savings_prediction(
    month: int = None, year: int = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now   = datetime.now()
    month = month or now.month
    year  = year  or now.year
    snapshot = db.query(models.MonthlySnapshot).filter(
        models.MonthlySnapshot.user_id == current_user.id,
        models.MonthlySnapshot.month == month,
        models.MonthlySnapshot.year  == year,
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
        "savings_message": message,
    }


@api_v1.post("/ai-purchase-decision")
def ai_purchase_decision(
    amount: float,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if amount <= 0 or amount > 100_000_000:
        raise HTTPException(status_code=400, detail="Invalid amount")
    now  = datetime.now()
    txns = db.query(models.Transaction).filter(models.Transaction.user_id == current_user.id).all()
    income  = sum(t.amount for t in txns if t.date.month == now.month and t.date.year == now.year and t.type == "income")
    expense = sum(t.amount for t in txns if t.date.month == now.month and t.date.year == now.year and t.type == "expense")
    remaining = income - expense
    if amount <= remaining * 0.5:    decision = "✅ You can afford this purchase comfortably."
    elif amount <= remaining:        decision = "⚠️ Purchase possible but your savings will reduce significantly."
    else:                            decision = "❌ Not recommended. This exceeds your remaining monthly budget."
    return {"decision": decision, "remaining_after_purchase": remaining - amount}


# ══════════════════════════════════════
# AI BOT
# ══════════════════════════════════════

@api_v1.post("/ai-bot")
async def ai_bot(
    request_data: schemas.ChatRequest,
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rate_limit(f"ai-bot:{current_user.id}", limit=30, window_seconds=60)
    reply = await chat_with_bot(
        user_id=current_user.id,
        message=request_data.message,
        history=[h.dict() for h in request_data.history],
        db=db,
    )
    return {"reply": reply}


# ══════════════════════════════════════
# DOCUMENT UPLOAD & OCR
# ══════════════════════════════════════

ALLOWED_DOC_TYPES = {"salary_slip", "itr", "demat", "property", "loan", "credit_card"}
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@api_v1.post("/upload-document")
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = Form(...),
    request: Request = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rate_limit(f"upload:{current_user.id}", limit=10, window_seconds=3600)

    if doc_type not in ALLOWED_DOC_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid doc_type.")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Invalid file type. Allowed: PDF, JPG, PNG.")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Max 10MB.")

    # Basic magic-byte check
    magic = {b"%PDF": ".pdf", b"\xff\xd8\xff": ".jpg", b"\x89PNG": ".png"}
    detected = next((ext for sig, ext in magic.items() if contents.startswith(sig)), None)
    if detected and detected != ext:
        raise HTTPException(status_code=400, detail="File content does not match extension.")

    return await verify_document(
        file_bytes=contents, filename=file.filename,
        doc_type=doc_type, user_id=current_user.id, db=db,
    )


@api_v1.get("/verification-status")
def verification_status(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_verification_status(current_user.id, db)


# ══════════════════════════════════════
# MARKET & NEWS
# ══════════════════════════════════════

@api_v1.get("/market-data")
def market_data(current_user: models.User = Depends(get_current_user)):
    try:
        return {"instruments": get_market_data_cached(), "status": "ok"}
    except Exception:
        return {"instruments": [], "status": "error", "detail": "Market data temporarily unavailable"}


@api_v1.get("/news-insights")
def news_insights(current_user: models.User = Depends(get_current_user)):
    gnews_key = os.getenv("GNEWS_API_KEY", "")
    return get_news_insights(gnews_api_key=gnews_key)


# ── Mount static & include routers ───────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(ml_router)
app.include_router(api_v1)