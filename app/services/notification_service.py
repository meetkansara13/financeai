"""
Notification Service
====================
SMS via Twilio (free trial) — real OTP delivery to phone
Email via Gmail SMTP — real reset link delivery
"""

import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ══════════════════════════════════════
# CONFIG
# ══════════════════════════════════════

TWILIO_ACCOUNT_SID  = "AC95c28fe90a8a48295b2d936ef2161d35"
TWILIO_AUTH_TOKEN   = "d5d4a9147a61d13df6ec60348fbbfb88"
TWILIO_PHONE_NUMBER = "+17077395689"

SMTP_EMAIL     = "meet.kansara2006@gmail.com"
SMTP_PASSWORD  = "pzxl utbb znvt pdej"
SMTP_FROM_NAME = "FinanceAI"

APP_BASE_URL = "http://127.0.0.1:8000"


# ══════════════════════════════════════
# SEND OTP VIA TWILIO
# ══════════════════════════════════════

def send_otp_sms(mobile: str, otp: str) -> bool:
    # Normalize to E.164 (+91XXXXXXXXXX)
    mobile = mobile.replace(" ", "").replace("-", "").strip()
    if mobile.startswith("+91"):
        pass                                    # already +91XXXXXXXXXX
    elif mobile.startswith("91") and len(mobile) == 12:
        mobile = "+" + mobile                   # 919429211962 → +919429211962
    elif mobile.startswith("0"):
        mobile = "+91" + mobile[1:]             # 09429... → +919429...
    else:
        mobile = "+91" + mobile                 # 9429211962 → +919429211962

    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
    payload = {
        "To":   mobile,
        "From": TWILIO_PHONE_NUMBER,
        "Body": f"Your FinanceAI verification code is: {otp}. Valid for 5 minutes. Do not share this with anyone."
    }

    try:
        res  = requests.post(url, data=payload, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN), timeout=10)
        data = res.json()
        print(f"[TWILIO] Status: {data.get('status')} | To: {mobile} | SID: {data.get('sid')}")
        # If there's an error code, print it
        if data.get("code"):
            print(f"[TWILIO] Error code {data.get('code')}: {data.get('message')}")
        return data.get("status") in ("queued", "sent", "delivered")
    except Exception as e:
        print(f"[TWILIO] Exception: {e}")
        return False


# ══════════════════════════════════════
# SEND RESET EMAIL VIA GMAIL SMTP
# ══════════════════════════════════════

def send_reset_email(to_email: str, reset_token: str) -> bool:
    reset_link = f"{APP_BASE_URL}/reset-password/{reset_token}"

    html_body = f"""
    <div style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;background:#0e1118;color:#e2e8f0;padding:32px;border-radius:16px;">
        <div style="font-size:24px;font-weight:700;margin-bottom:8px;">💹 <span style="color:#c9a84c;">Finance</span>AI</div>
        <hr style="border-color:rgba(255,255,255,0.07);margin:16px 0;">
        <h2 style="color:#f0f2f8;font-size:20px;">Reset Your Password</h2>
        <p style="color:#64748b;font-size:14px;line-height:1.6;">
            We received a request to reset your FinanceAI account password.
            Click the button below to set a new password. This link expires in
            <strong style="color:#c9a84c;">15 minutes</strong>.
        </p>
        <div style="text-align:center;margin:28px 0;">
            <a href="{reset_link}"
               style="display:inline-block;padding:14px 32px;background:linear-gradient(135deg,#c9a84c,#e8c872);
                      color:#0d0b04;font-weight:700;font-size:15px;border-radius:10px;text-decoration:none;">
                Reset Password →
            </a>
        </div>
        <p style="color:#475569;font-size:12px;">
            If you didn't request this, ignore this email — your password won't change.<br>
            Or copy this link: <a href="{reset_link}" style="color:#c9a84c;">{reset_link}</a>
        </p>
        <hr style="border-color:rgba(255,255,255,0.07);margin-top:24px;">
        <p style="color:#334155;font-size:11px;text-align:center;">FinanceAI · Secure Financial Management</p>
    </div>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Reset Your FinanceAI Password"
    msg["From"]    = f"{SMTP_FROM_NAME} <{SMTP_EMAIL}>"
    msg["To"]      = to_email
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, to_email, msg.as_string())
        print(f"[EMAIL] Reset link sent to {to_email}")
        return True
    except Exception as e:
        print(f"[EMAIL] Error: {e}")
        return False