from pydantic import BaseModel
from typing import Optional, List
from datetime import date


class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    mobile_number: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str


class TransactionCreate(BaseModel):
    amount: float
    type: str
    category: str
    description: str
    date: Optional[date] = None


class BudgetCreate(BaseModel):
    category: str
    monthly_limit: float


class FinancialProfileResponse(BaseModel):
    monthly_income: float
    side_income: float
    total_assets: float
    loans: float
    net_worth: float
    safe_expense_limit: float

    class Config:
        from_attributes = True


class FinancialProfileCreate(BaseModel):
    # Step 1 — Identity
    full_name:      Optional[str]   = ""
    dob:            Optional[str]   = ""
    pan:            Optional[str]   = ""
    aadhaar:        Optional[str]   = ""
    mobile:         Optional[str]   = ""
    email_addr:     Optional[str]   = ""
    address_line1:  Optional[str]   = ""
    city:           Optional[str]   = ""
    state:          Optional[str]   = ""
    pincode:        Optional[str]   = ""
    occupation:     Optional[str]   = ""
    employer:       Optional[str]   = ""
    income_bracket: Optional[str]   = ""

    # Step 2 — Income
    monthly_income: float = 0
    side_income:    float = 0
    rental_income:  float = 0
    passive_income: float = 0

    # Step 3 — Assets (all individual)
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

    # Step 4 — Liabilities (all individual)
    home_loan:      float = 0
    car_loan:       float = 0
    personal_loan:  float = 0
    education_loan: float = 0
    business_loan:  float = 0
    other_loans:    float = 0
    credit_card:    float = 0
    fixed_expenses: float = 0


# ── Auth schemas ──
class MobileSchema(BaseModel):
    mobile_number: str

class OTPSchema(BaseModel):
    mobile_number: str
    otp: str

class EmailSchema(BaseModel):
    email: str

class NewPasswordSchema(BaseModel):
    new_password: str

# ── AI Bot schemas ──
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []

class SmartTransaction(BaseModel):
    text: str