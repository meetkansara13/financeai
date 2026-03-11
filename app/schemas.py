from pydantic import BaseModel, EmailStr, field_validator, model_validator
from typing import Optional, List
from datetime import date
import re


# ── VALIDATORS ──────────────────────────────────────────────────────────────

def _safe_str(v: Optional[str], max_len: int = 200) -> Optional[str]:
    """Strip, limit length, reject null bytes."""
    if v is None:
        return v
    v = str(v).strip().replace("\x00", "")
    return v[:max_len]


# ── AUTH ─────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    mobile_number: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        v = _safe_str(v, 100)
        if not v or len(v) < 2:
            raise ValueError("Name must be at least 2 characters")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v) > 128:
            raise ValueError("Password too long")
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("Password must contain at least one letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one number")
        return v

    @field_validator("mobile_number")
    @classmethod
    def validate_mobile(cls, v):
        if v is None:
            return v
        v = re.sub(r"\D", "", v)
        if len(v) < 10 or len(v) > 15:
            raise ValueError("Invalid mobile number")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class MobileSchema(BaseModel):
    mobile_number: str

    @field_validator("mobile_number")
    @classmethod
    def validate_mobile(cls, v):
        v = re.sub(r"\D", "", v)
        if len(v) < 10 or len(v) > 15:
            raise ValueError("Invalid mobile number")
        return v


class OTPSchema(BaseModel):
    mobile_number: str
    otp: str

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, v):
        v = v.strip()
        if not re.fullmatch(r"\d{6}", v):
            raise ValueError("OTP must be 6 digits")
        return v


class EmailSchema(BaseModel):
    email: EmailStr


class NewPasswordSchema(BaseModel):
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v) > 128:
            raise ValueError("Password too long")
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("Password must contain at least one letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one number")
        return v


# ── TRANSACTIONS ─────────────────────────────────────────────────────────────

ALLOWED_TYPES       = {"income", "expense"}
ALLOWED_CATEGORIES  = {
    "Food", "Transport", "Shopping", "Entertainment", "Health", "Education",
    "Bills", "Rent", "Salary", "Freelance", "Investment", "Business",
    "Travel", "Personal", "Savings", "Other", "EMI", "Insurance",
    "Groceries", "Dining", "Utilities", "Medical", "Subscriptions",
}


class TransactionCreate(BaseModel):
    amount: float
    type: str
    category: str
    description: str
    date: Optional[date] = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Amount must be positive")
        if v > 100_000_000:
            raise ValueError("Amount too large")
        return round(v, 2)

    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        v = v.strip().lower()
        if v not in ALLOWED_TYPES:
            raise ValueError(f"Type must be one of: {ALLOWED_TYPES}")
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v):
        v = _safe_str(v, 50)
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v):
        return _safe_str(v, 300)


# ── BUDGETS ──────────────────────────────────────────────────────────────────

class BudgetCreate(BaseModel):
    category: str
    monthly_limit: float

    @field_validator("monthly_limit")
    @classmethod
    def validate_limit(cls, v):
        if v <= 0:
            raise ValueError("Budget limit must be positive")
        if v > 100_000_000:
            raise ValueError("Budget limit too large")
        return round(v, 2)

    @field_validator("category")
    @classmethod
    def validate_category(cls, v):
        return _safe_str(v, 50)


# ── FINANCIAL PROFILE ─────────────────────────────────────────────────────────

class FinancialProfileResponse(BaseModel):
    monthly_income: float
    side_income: float
    total_assets: float
    loans: float
    net_worth: float
    safe_expense_limit: float

    class Config:
        from_attributes = True


def _non_negative(v: float) -> float:
    if v < 0:
        raise ValueError("Value cannot be negative")
    if v > 1_000_000_000:
        raise ValueError("Value too large")
    return round(v, 2)


class FinancialProfileCreate(BaseModel):
    # Step 1 — Identity
    full_name:      Optional[str] = ""
    dob:            Optional[str] = ""
    pan:            Optional[str] = ""
    aadhaar:        Optional[str] = ""
    mobile:         Optional[str] = ""
    email_addr:     Optional[str] = ""
    address_line1:  Optional[str] = ""
    city:           Optional[str] = ""
    state:          Optional[str] = ""
    pincode:        Optional[str] = ""
    occupation:     Optional[str] = ""
    employer:       Optional[str] = ""
    income_bracket: Optional[str] = ""

    # Step 2 — Income
    monthly_income: float = 0
    side_income:    float = 0
    rental_income:  float = 0
    passive_income: float = 0

    # Step 3 — Assets
    stocks:          float = 0
    mutual_funds:    float = 0
    bonds:           float = 0
    crypto:          float = 0
    real_estate:     float = 0
    gold:            float = 0
    vehicles:        float = 0
    cash_savings:    float = 0
    fixed_deposits:  float = 0
    insurance_value: float = 0

    # Step 4 — Liabilities
    home_loan:      float = 0
    car_loan:       float = 0
    personal_loan:  float = 0
    education_loan: float = 0
    business_loan:  float = 0
    other_loans:    float = 0
    credit_card:    float = 0
    fixed_expenses: float = 0

    @field_validator("pan")
    @classmethod
    def validate_pan(cls, v):
        if v and not re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", v.strip().upper()):
            raise ValueError("Invalid PAN format")
        return v.strip().upper() if v else v

    @field_validator("aadhaar")
    @classmethod
    def validate_aadhaar(cls, v):
        if v:
            digits = re.sub(r"\D", "", v)
            if len(digits) != 12:
                raise ValueError("Aadhaar must be 12 digits")
        return v

    @field_validator(
        "monthly_income","side_income","rental_income","passive_income",
        "stocks","mutual_funds","bonds","crypto","real_estate","gold",
        "vehicles","cash_savings","fixed_deposits","insurance_value",
        "home_loan","car_loan","personal_loan","education_loan",
        "business_loan","other_loans","credit_card","fixed_expenses",
        mode="before"
    )
    @classmethod
    def validate_financials(cls, v):
        return _non_negative(float(v or 0))

    @field_validator("full_name","dob","mobile","email_addr","address_line1",
                     "city","state","pincode","occupation","employer","income_bracket",
                     mode="before")
    @classmethod
    def sanitise_strings(cls, v):
        return _safe_str(v, 200)


# ── AI BOT ───────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str
    content: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        if v not in {"user", "assistant", "system"}:
            raise ValueError("Invalid role")
        return v

    @field_validator("content")
    @classmethod
    def validate_content(cls, v):
        return _safe_str(v, 2000)


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []

    @field_validator("message")
    @classmethod
    def validate_message(cls, v):
        v = _safe_str(v, 1000)
        if not v:
            raise ValueError("Message cannot be empty")
        return v

    @field_validator("history")
    @classmethod
    def validate_history(cls, v):
        if len(v) > 50:
            return v[-50:]  # keep only last 50 messages
        return v


class SmartTransaction(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def validate_text(cls, v):
        v = _safe_str(v, 500)
        if not v:
            raise ValueError("Text cannot be empty")
        return v