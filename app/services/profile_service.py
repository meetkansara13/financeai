from sqlalchemy.orm import Session
from .. import models


def save_or_update_profile(user_id: int, data, db: Session):
    profile = db.query(models.FinancialProfile).filter(
        models.FinancialProfile.user_id == user_id
    ).first()

    if not profile:
        profile = models.FinancialProfile(user_id=user_id)
        db.add(profile)

    def g(field, default=0):
        return getattr(data, field, default) or default

    def gs(field):
        return getattr(data, field, "") or ""

    # Step 1 — Identity
    profile.full_name      = gs("full_name")
    profile.dob            = gs("dob")
    profile.pan            = gs("pan")
    profile.aadhaar        = gs("aadhaar")
    profile.mobile         = gs("mobile")
    profile.email_addr     = gs("email_addr")
    profile.address_line1  = gs("address_line1")
    profile.city           = gs("city")
    profile.state          = gs("state")
    profile.pincode        = gs("pincode")
    profile.occupation     = gs("occupation")
    profile.employer       = gs("employer")
    profile.income_bracket = gs("income_bracket")

    # Step 2 — Income
    profile.monthly_income = g("monthly_income")
    profile.side_income    = g("side_income")
    profile.rental_income  = g("rental_income")
    profile.passive_income = g("passive_income")

    # Step 3 — Assets
    profile.stocks          = g("stocks")
    profile.mutual_funds    = g("mutual_funds")
    profile.bonds           = g("bonds")
    profile.crypto          = g("crypto")
    profile.real_estate     = g("real_estate")
    profile.gold            = g("gold")
    profile.vehicles        = g("vehicles")
    profile.cash_savings    = g("cash_savings")
    profile.fixed_deposits  = g("fixed_deposits")
    profile.insurance_value = g("insurance_value")

    # Step 4 — Liabilities
    profile.home_loan      = g("home_loan")
    profile.car_loan       = g("car_loan")
    profile.personal_loan  = g("personal_loan")
    profile.education_loan = g("education_loan")
    profile.business_loan  = g("business_loan")
    profile.other_loans    = g("other_loans")
    profile.credit_card    = g("credit_card")
    profile.fixed_expenses = g("fixed_expenses")

    # Legacy aggregate
    profile.loans = (g("home_loan") + g("car_loan") + g("personal_loan") +
                     g("education_loan") + g("business_loan") + g("other_loans"))

    db.commit()
    db.refresh(profile)
    return profile


def get_profile_analysis(user_id: int, db: Session):
    profile = db.query(models.FinancialProfile).filter(
        models.FinancialProfile.user_id == user_id
    ).first()

    if not profile:
        return None

    total_income = (
        (profile.monthly_income or 0) + (profile.side_income    or 0) +
        (profile.rental_income  or 0) + (profile.passive_income or 0)
    )
    total_assets = (
        (profile.stocks          or 0) + (profile.mutual_funds   or 0) +
        (profile.bonds           or 0) + (profile.crypto         or 0) +
        (profile.real_estate     or 0) + (profile.gold           or 0) +
        (profile.vehicles        or 0) + (profile.cash_savings   or 0) +
        (profile.fixed_deposits  or 0) + (profile.insurance_value or 0)
    )
    total_liabilities = (
        (profile.home_loan      or 0) + (profile.car_loan       or 0) +
        (profile.personal_loan  or 0) + (profile.education_loan or 0) +
        (profile.business_loan  or 0) + (profile.other_loans    or 0) +
        (profile.credit_card    or 0)
    )
    net_worth = total_assets - total_liabilities

    return {
        # Identity
        "full_name":      profile.full_name      or "",
        "dob":            profile.dob            or "",
        "pan":            profile.pan            or "",
        "aadhaar":        profile.aadhaar        or "",
        "mobile":         profile.mobile         or "",
        "email_addr":     profile.email_addr     or "",
        "address_line1":  profile.address_line1  or "",
        "city":           profile.city           or "",
        "state":          profile.state          or "",
        "pincode":        profile.pincode        or "",
        "occupation":     profile.occupation     or "",
        "employer":       profile.employer       or "",
        "income_bracket": profile.income_bracket or "",

        # Income
        "monthly_income": profile.monthly_income or 0,
        "side_income":    profile.side_income    or 0,
        "rental_income":  profile.rental_income  or 0,
        "passive_income": profile.passive_income or 0,
        "total_income":   total_income,

        # Assets (all individual)
        "stocks":          profile.stocks          or 0,
        "mutual_funds":    profile.mutual_funds    or 0,
        "bonds":           profile.bonds           or 0,
        "crypto":          profile.crypto          or 0,
        "real_estate":     profile.real_estate     or 0,
        "gold":            profile.gold            or 0,
        "vehicles":        profile.vehicles        or 0,
        "cash_savings":    profile.cash_savings    or 0,
        "fixed_deposits":  profile.fixed_deposits  or 0,
        "insurance_value": profile.insurance_value or 0,
        "total_assets":    total_assets,

        # Liabilities (all individual)
        "home_loan":      profile.home_loan      or 0,
        "car_loan":       profile.car_loan       or 0,
        "personal_loan":  profile.personal_loan  or 0,
        "education_loan": profile.education_loan or 0,
        "business_loan":  profile.business_loan  or 0,
        "other_loans":    profile.other_loans    or 0,
        "credit_card":    profile.credit_card    or 0,
        "fixed_expenses": profile.fixed_expenses or 0,
        "total_liabilities": total_liabilities,
        "loans":          profile.loans          or 0,

        # Computed
        "net_worth":          net_worth,
        "safe_expense_limit": total_income * 0.7,
    }