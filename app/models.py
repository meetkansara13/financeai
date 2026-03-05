from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from .database import Base
import datetime


class User(Base):
    __tablename__ = "users"
    id       = Column(Integer, primary_key=True, index=True)
    name     = Column(String)
    email    = Column(String, unique=True, index=True)
    password = Column(String)
    mobile_number      = Column(String, nullable=True)
    otp_code           = Column(String, nullable=True)
    otp_expiry         = Column(DateTime, nullable=True)
    reset_token        = Column(String, nullable=True)
    reset_token_expiry = Column(DateTime, nullable=True)
    transactions = relationship("Transaction", back_populates="owner")


class Transaction(Base):
    __tablename__ = "transactions"
    id          = Column(Integer, primary_key=True, index=True)
    amount      = Column(Float)
    type        = Column(String)
    category    = Column(String)
    description = Column(String)
    date        = Column(Date, default=datetime.date.today)
    user_id     = Column(Integer, ForeignKey("users.id"))
    owner       = relationship("User", back_populates="transactions")


class Budget(Base):
    __tablename__ = "budgets"
    id            = Column(Integer, primary_key=True, index=True)
    category      = Column(String)
    monthly_limit = Column(Float)
    user_id       = Column(Integer, ForeignKey("users.id"))


class FinancialProfile(Base):
    __tablename__ = "financial_profiles"
    id      = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)

    # ── Step 1: Identity ──
    full_name      = Column(String,  default="")
    dob            = Column(String,  default="")
    pan            = Column(String,  default="")
    aadhaar        = Column(String,  default="")
    mobile         = Column(String,  default="")
    email_addr     = Column(String,  default="")
    address_line1  = Column(String,  default="")
    city           = Column(String,  default="")
    state          = Column(String,  default="")
    pincode        = Column(String,  default="")
    occupation     = Column(String,  default="")
    employer       = Column(String,  default="")
    income_bracket = Column(String,  default="")

    # ── Step 2: Income ──
    monthly_income = Column(Float, default=0)
    side_income    = Column(Float, default=0)
    rental_income  = Column(Float, default=0)
    passive_income = Column(Float, default=0)

    # ── Step 3: Assets (all individual) ──
    stocks         = Column(Float, default=0)
    mutual_funds   = Column(Float, default=0)
    bonds          = Column(Float, default=0)
    crypto         = Column(Float, default=0)
    real_estate    = Column(Float, default=0)
    gold           = Column(Float, default=0)
    vehicles       = Column(Float, default=0)
    cash_savings   = Column(Float, default=0)
    fixed_deposits = Column(Float, default=0)
    insurance_value= Column(Float, default=0)

    # ── Step 4: Liabilities (all individual) ──
    home_loan      = Column(Float, default=0)
    car_loan       = Column(Float, default=0)
    personal_loan  = Column(Float, default=0)
    education_loan = Column(Float, default=0)
    business_loan  = Column(Float, default=0)
    other_loans    = Column(Float, default=0)
    credit_card    = Column(Float, default=0)
    fixed_expenses = Column(Float, default=0)

    # ── Legacy aggregated fields (kept for backward compat) ──
    loans          = Column(Float, default=0)

    user = relationship("User")


class MonthlySnapshot(Base):
    __tablename__ = "monthly_snapshots"
    id      = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    month   = Column(Integer)
    year    = Column(Integer)
    income  = Column(Float, default=0)
    expense = Column(Float, default=0)
    savings = Column(Float, default=0)
    user    = relationship("User")


class DocumentVerification(Base):
    __tablename__ = "document_verifications"
    id             = Column(Integer, primary_key=True, index=True)
    user_id        = Column(Integer, ForeignKey("users.id"))
    doc_type       = Column(String, index=True)
    filename       = Column(String)
    file_path      = Column(String)
    extracted_text = Column(String, default="")
    extracted_pan  = Column(String, default="")
    extracted_name = Column(String, default="")
    extracted_amount = Column(Float, default=0)
    status         = Column(String, default="pending")
    match_score    = Column(Float, default=0)
    failure_reason = Column(String, default="")
    uploaded_at    = Column(DateTime, default=datetime.datetime.utcnow)
    verified_at    = Column(DateTime, nullable=True)
    user = relationship("User")