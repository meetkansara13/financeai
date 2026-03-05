import re
from datetime import datetime
from sqlalchemy.orm import Session
from app import models
from app.services.snapshot_service import create_or_update_snapshot


# ==============================
# Extended Category + Asset Map
# ==============================

CATEGORY_MAP = {
    "food":          ["swiggy", "zomato", "restaurant", "cafe", "burger", "pizza",
                      "dominos", "mcdonalds", "kfc", "starbucks", "lunch", "dinner",
                      "breakfast", "tea", "coffee", "blinkit", "dunzo", "biryani",
                      "dhaba", "canteen", "food court", "snacks", "bakery", "juice",
                      "chaiwala", "chai", "thali", "dosa", "idli", "paratha"],

    "transport":     ["uber", "ola", "rapido", "fuel", "petrol", "diesel", "metro",
                      "bus", "auto", "cab", "irctc", "train", "flight",
                      "indigo", "airindia", "rickshaw", "parking", "toll", "spicejet",
                      "vistara", "highway", "transport", "travel"],

    "groceries":     ["grocery", "groceries", "kirana", "supermarket",
                      "milk", "eggs", "bread", "rice", "dal", "atta",
                      "flour", "oil", "sugar", "salt", "spices", "masala", "zepto",
                      "bigbasket", "jiomart", "grofers", "daily needs", "provisions"],

    "vegetables":    ["vegetable", "sabzi", "sabziwala", "tomato", "potato", "onion",
                      "spinach", "carrot", "cauliflower", "cabbage", "peas", "beans",
                      "bhindi", "brinjal", "cucumber", "capsicum", "coriander", "leafy"],

    "fruits":        ["fruit", "apple", "banana", "mango", "grapes", "orange",
                      "watermelon", "papaya", "guava", "strawberry", "kiwi",
                      "pineapple", "pomegranate", "lychee", "chikoo"],

    "sports":        ["gym", "fitness", "yoga", "sport", "sports", "football",
                      "cricket", "badminton", "tennis", "swimming", "cycling",
                      "basketball", "basket ball", "volleyball", "hockey", "kabaddi",
                      "chess", "running", "marathon", "athletics", "wrestling", "boxing",
                      "karate", "taekwondo", "archery", "golf", "squash",
                      "table tennis", "ping pong", "racket", "bat", "ball",
                      "jersey", "kit", "stadium", "ground", "court",
                      "soccer", "soccere", "football kit", "cricket kit",
                      "match ticket", "ipl ticket", "nike", "adidas", "puma",
                      "decathlon", "coaching", "training fee",
                      "fitness band", "protein", "whey", "creatine", "supplement"],

    "beauty":        ["beauty", "salon", "parlour", "parlor", "spa", "makeup",
                      "cosmetics", "skincare", "haircut", "hair color", "manicure",
                      "pedicure", "waxing", "threading", "facial", "facials",
                      "lipstick", "foundation", "moisturizer", "serum", "sunscreen",
                      "shampoo", "conditioner", "nykaa", "sugar cosmetics",
                      "lakme", "loreal", "maybelline", "mac cosmetics", "perfume",
                      "deodorant", "body lotion", "face wash", "toner", "kajal",
                      "nail polish", "eyeliner", "blush", "highlighter"],

    "shopping":      ["amazon", "flipkart", "meesho", "myntra", "ajio",
                      "reliance", "dmart", "big bazaar", "mall", "clothes", "shirt",
                      "shoes", "jeans", "jacket", "watch", "belt", "bag",
                      "handbag", "wallet", "sunglasses", "accessories", "fashion",
                      "kurta", "saree", "dress", "top", "trouser", "shorts",
                      "tshirt", "hoodie", "sweater", "blanket", "bedsheet"],

    "entertainment": ["netflix", "hotstar", "prime", "spotify", "youtube", "movie",
                      "cinema", "pvr", "inox", "concert", "game", "playstation",
                      "xbox", "gaming", "steam", "disney+", "zee5", "sonyliv",
                      "bookmyshow", "event", "party", "club", "pub", "bar",
                      "amusement", "waterpark", "theme park", "picnic"],

    "health":        ["hospital", "doctor", "medicine", "pharmacy", "apollo", "clinic",
                      "chemist", "medplus", "health", "dental", "eye", "optician",
                      "diagnostic", "lab test", "blood test", "xray", "scan",
                      "ambulance", "surgery", "physiotherapy", "ayurveda",
                      "netmeds", "1mg", "practo", "consultation"],

    "education":     ["college", "school", "course", "udemy", "coursera", "fees",
                      "tuition", "books", "stationery", "coaching", "institute",
                      "exam fee", "certification", "workshop", "seminar",
                      "notebook", "pen", "pencil"],

    "utilities":     ["electricity", "water", "gas", "wifi", "internet", "broadband",
                      "airtel", "jio", "bsnl", "vi", "recharge", "bill", "rent",
                      "maintenance", "society charges", "cable", "dth", "tataplay",
                      "dish tv", "lpg", "cylinder"],

    "assets":        ["gold", "silver", "bitcoin", "crypto", "stock", "shares",
                      "mutual fund", "sip", "property", "plot", "land", "fd",
                      "fixed deposit", "ppf", "nps", "insurance", "laptop", "phone",
                      "mobile", "pc", "computer", "iphone", "macbook", "tv",
                      "refrigerator", "ac", "washing machine", "car", "bike",
                      "scooter", "vehicle"],
}

ASSET_KEYWORDS = set(CATEGORY_MAP["assets"])

INCOME_KEYWORDS = [
    "salary", "received", "income", "credited", "credit",
    "bonus", "refund", "cashback", "dividend", "interest",
    "rent received", "freelance", "got paid", "payment received"
]

EXPENSE_KEYWORDS = [
    "paid", "spent", "bought", "purchase", "purchased",
    "debit", "debited", "charged", "bill", "fee"
]

# Priority order: specific categories first, generic last
PRIORITY_ORDER = [
    "sports", "beauty", "vegetables", "fruits", "groceries",
    "health", "food", "education", "entertainment", "transport",
    "utilities", "assets", "shopping"
]


def detect_category(text: str) -> str:
    """
    Smart auto-categorization using keyword matching with priority order.
    Specific categories (sports, beauty, vegetables, fruits) are checked
    before generic ones (shopping, other) to avoid misclassification.
    Examples:
      - 'paid 500 for football'   => sports
      - 'paid 200 for sabzi'      => vegetables
      - 'bought face wash'        => beauty
      - 'paid for cricket kit'    => sports
      - 'bought from nykaa'       => beauty
    """
    for cat in PRIORITY_ORDER:
        keywords = CATEGORY_MAP.get(cat, [])
        if any(kw in text for kw in keywords):
            return cat
    return "other"


def is_asset_purchase(text: str, category: str) -> bool:
    return category == "assets"


def process_smart_transaction(text: str, current_user: models.User, db: Session):
    original_text = text
    text = text.lower()

    # ── 1. Extract Amount ──
    amount_match = re.search(r"[\d,]+(\.\d+)?", text)
    raw = amount_match.group().replace(",", "") if amount_match else "0"
    amount = float(raw)

    # ── 2. Detect Type ──
    if any(kw in text for kw in INCOME_KEYWORDS):
        txn_type = "income"
    else:
        txn_type = "expense"

    # ── 3. Detect Category ──
    category = detect_category(text)

    # ── 4. Asset flag ──
    asset_purchase = is_asset_purchase(text, category)

    # ── 5. Save Transaction ──
    new_txn = models.Transaction(
        amount=amount,
        type=txn_type,
        category=category,
        description=original_text,
        user_id=current_user.id
    )
    db.add(new_txn)
    db.commit()
    db.refresh(new_txn)

    # ── 6. Snapshot ──
    create_or_update_snapshot(current_user.id, db)

    # ── 7. Monthly Totals ──
    now = datetime.now()
    all_txns = db.query(models.Transaction).filter(
        models.Transaction.user_id == current_user.id
    ).all()

    monthly_income = sum(
        t.amount for t in all_txns
        if t.date.month == now.month and t.date.year == now.year and t.type == "income"
    )
    monthly_expense = sum(
        t.amount for t in all_txns
        if t.date.month == now.month and t.date.year == now.year and t.type == "expense"
    )
    monthly_savings = monthly_income - monthly_expense

    # ── 8. Budget Check ──
    budget_warning = None
    budget = db.query(models.Budget).filter(
        models.Budget.user_id == current_user.id,
        models.Budget.category == category
    ).first()

    if budget:
        cat_spent = sum(
            t.amount for t in all_txns
            if t.date.month == now.month and t.date.year == now.year
            and t.type == "expense" and t.category == category
        )
        pct = (cat_spent / budget.monthly_limit * 100) if budget.monthly_limit > 0 else 0
        if pct >= 100:
            budget_warning = f"🔴 Budget exceeded for {category.upper()}! Spent ₹{int(cat_spent)} of ₹{int(budget.monthly_limit)}"
        elif pct >= 80:
            budget_warning = f"🟠 {category.upper()} budget at {round(pct,1)}% — only ₹{int(budget.monthly_limit - cat_spent)} left"

    # ── 9. Savings message ──
    days_passed = now.day
    total_days = 30
    if days_passed > 0 and monthly_expense > 0:
        projected_expense = (monthly_expense / days_passed) * total_days
        projected_savings = monthly_income - projected_expense
        if projected_savings > 0:
            savings_msg = f"📈 On track to save ₹{int(projected_savings):,} this month"
        else:
            savings_msg = f"⚠️ Overspend risk — projected deficit of ₹{abs(int(projected_savings)):,}"
    else:
        savings_msg = "Add more transactions for prediction"

    return {
        "message": "Smart transaction added",
        "transaction": {
            "id": new_txn.id,
            "amount": amount,
            "type": txn_type,
            "category": category,
            "is_asset": asset_purchase
        },
        "monthly": {
            "income": monthly_income,
            "expense": monthly_expense,
            "savings": monthly_savings
        },
        "budget_warning": budget_warning,
        "savings_message": savings_msg,
        "asset_purchase": asset_purchase
    }