import os
import httpx
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from app import models


GROQ_API_KEY = os.getenv("GROQ_API_KEY", "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")
GROQ_MODEL = "llama-3.3-70b-versatile"


def build_financial_context(user_id: int, db: Session) -> str:
    now = datetime.now()

    profile = db.query(models.FinancialProfile).filter(
        models.FinancialProfile.user_id == user_id
    ).first()

    snapshot = db.query(models.MonthlySnapshot).filter(
        models.MonthlySnapshot.user_id == user_id,
        models.MonthlySnapshot.month == now.month,
        models.MonthlySnapshot.year == now.year
    ).first()

    total_income = db.query(func.sum(models.Transaction.amount)).filter(
        models.Transaction.user_id == user_id,
        models.Transaction.type == "income"
    ).scalar() or 0

    total_expense = db.query(func.sum(models.Transaction.amount)).filter(
        models.Transaction.user_id == user_id,
        models.Transaction.type == "expense"
    ).scalar() or 0

    cat_results = db.query(
        models.Transaction.category,
        func.sum(models.Transaction.amount)
    ).filter(
        models.Transaction.user_id == user_id,
        models.Transaction.type == "expense",
        extract("month", models.Transaction.date) == now.month,
        extract("year", models.Transaction.date) == now.year
    ).group_by(models.Transaction.category).all()

    cat_breakdown = "\n".join(
        f"  {cat.title()}: ₹{int(total):,}" for cat, total in cat_results
    ) or "  No expenses recorded this month"

    budgets = db.query(models.Budget).filter(
        models.Budget.user_id == user_id
    ).all()

    budget_lines = []
    for b in budgets:
        spent = db.query(func.sum(models.Transaction.amount)).filter(
            models.Transaction.user_id == user_id,
            models.Transaction.type == "expense",
            models.Transaction.category == b.category,
            extract("month", models.Transaction.date) == now.month,
            extract("year", models.Transaction.date) == now.year
        ).scalar() or 0
        pct = round(spent / b.monthly_limit * 100, 1) if b.monthly_limit > 0 else 0
        status = "🔴 OVER" if pct >= 100 else ("🟠 HIGH" if pct >= 80 else "🟢 OK")
        budget_lines.append(
            f"  {b.category.title()}: ₹{int(spent):,} / ₹{int(b.monthly_limit):,} ({pct}%) {status}"
        )
    budget_str = "\n".join(budget_lines) or "  No budgets configured"

    net_worth = 0
    total_assets = 0
    if profile:
        total_assets = (
            profile.stocks + profile.bonds + profile.real_estate +
            profile.gold + profile.cash_savings
        )
        net_worth = total_assets - profile.loans

    monthly_income  = snapshot.income   if snapshot else 0
    monthly_expense = snapshot.expense  if snapshot else 0
    monthly_savings = snapshot.savings  if snapshot else 0
    savings_rate    = round((monthly_savings / monthly_income * 100), 1) if monthly_income > 0 else 0

    days_passed = now.day
    projected_expense = round((monthly_expense / days_passed) * 30, 0) if days_passed > 0 else 0
    projected_savings = monthly_income - projected_expense

    system_prompt = f"""You are FinanceAI Advisor — a sharp, friendly, senior personal finance expert for Indian users.
You have COMPLETE access to this user's real financial data. Use it precisely in every response.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TODAY: {now.strftime("%A, %d %B %Y")}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 MONTHLY SNAPSHOT — {now.strftime("%B %Y")}
  Income:          ₹{int(monthly_income):,}
  Expenses:        ₹{int(monthly_expense):,}
  Savings:         ₹{int(monthly_savings):,}
  Savings Rate:    {savings_rate}%
  Projected Exp:   ₹{int(projected_expense):,} (by month-end)
  Projected Save:  ₹{int(projected_savings):,} (by month-end)

💳 EXPENSE BREAKDOWN (This Month)
{cat_breakdown}

🎯 BUDGET STATUS
{budget_str}

💰 INCOME PROFILE
  Monthly Salary:  ₹{int(profile.monthly_income if profile else 0):,}
  Side Income:     ₹{int(profile.side_income if profile else 0):,}
  Lifetime Income: ₹{int(total_income):,}
  Lifetime Spend:  ₹{int(total_expense):,}

🏦 WEALTH & NET WORTH
  Stocks:          ₹{int(profile.stocks if profile else 0):,}
  Bonds:           ₹{int(profile.bonds if profile else 0):,}
  Real Estate:     ₹{int(profile.real_estate if profile else 0):,}
  Gold:            ₹{int(profile.gold if profile else 0):,}
  Cash Savings:    ₹{int(profile.cash_savings if profile else 0):,}
  Total Assets:    ₹{int(total_assets):,}
  Total Loans:     ₹{int(profile.loans if profile else 0):,}
  NET WORTH:       ₹{int(net_worth):,}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 YOUR PERSONALITY & RESPONSE RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TONE: Confident, warm, direct. Like a trusted CA friend — not robotic, not overly formal.

RESPONSE FORMAT:
- Start with a 1-line direct answer to the question
- Follow with 2-3 specific supporting points using the user's EXACT numbers
- End with 1 clear actionable next step or insight
- Use ₹ always. Never use "Rs." or "$"
- Use bullet points or short paragraphs — never walls of text
- Max 200 words unless a detailed breakdown is genuinely needed

SMART BEHAVIORS:
- For purchase questions ("can I buy X?"): calculate affordability = (monthly_savings - expense) and check if X < 30% of monthly savings
- For investment questions: give ranked options (high/medium/low risk) based on their actual portfolio gaps
- For loan questions: calculate EMI impact on monthly cash flow using their actual income
- For savings questions: give a specific number target, not vague advice
- For "what if" scenarios (salary hike, big purchase): do the math live and show before/after numbers
- For goal planning: calculate exact months needed = goal_amount / monthly_savings

NEVER DO:
- Never repeat the same opening line twice in a conversation
- Never say "I don't have access to..." — you have ALL the data above
- Never give generic advice without using their actual numbers
- Never add unnecessary disclaimers like "this is not financial advice"
- Never be confused about the data — Net Worth is ₹{int(net_worth):,}, Savings Rate is {savings_rate}%
- Never end with "feel free to ask" — it's filler

INDIAN CONTEXT:
- Know Indian instruments: PPF, ELSS, NPS, SGB, FD, RD, NSC, Sukanya Samridhi
- Reference Indian banks (SBI, HDFC, ICICI, Axis) when relevant
- Know typical Indian expenses: rent, EMI, groceries, fuel costs in INR
- Be aware of Section 80C, 80D tax saving limits
"""
    return system_prompt.strip()


async def chat_with_bot(user_id: int, message: str, history: list, db: Session) -> str:
    system_prompt = build_financial_context(user_id, db)

    messages = [{"role": "system", "content": system_prompt}]
    for h in history[-14:]:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message})

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": GROQ_MODEL,
                    "max_tokens": 600,
                    "temperature": 0.7,
                    "messages": messages
                }
            )

        if response.status_code != 200:
            return f"⚠️ Bot error {response.status_code}: {response.text}"

        data = response.json()
        return data["choices"][0]["message"]["content"]

    except Exception as e:
        return f"⚠️ Connection error: {str(e)}"