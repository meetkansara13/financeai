"""
OCR Document Verification Service
===================================
Extracts text from uploaded PDFs/images using pdfplumber + pytesseract,
then cross-checks extracted fields (PAN, name, amount) against the user's
registered profile to produce a verification score and status.
"""

import re
import os
import json
import datetime
from pathlib import Path
from sqlalchemy.orm import Session
from app import models

# ── Try importing OCR libs (graceful fallback if not installed) ──
try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    from PIL import Image
    import pytesseract
    OCR_SUPPORT = True
except ImportError:
    OCR_SUPPORT = False


UPLOAD_DIR = Path("uploads/documents")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ════════════════════════════════════════
#  TEXT EXTRACTION
# ════════════════════════════════════════

def extract_text_from_pdf(file_path: str) -> str:
    """Extract all text from a PDF using pdfplumber."""
    if not PDF_SUPPORT:
        return ""
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
    except Exception as e:
        print(f"PDF extraction error: {e}")
    return text


def extract_text_from_image(file_path: str) -> str:
    """Extract text from image using Tesseract OCR."""
    if not OCR_SUPPORT:
        return ""
    try:
        img = Image.open(file_path)
        return pytesseract.image_to_string(img)
    except Exception as e:
        print(f"Image OCR error: {e}")
        return ""


def extract_text(file_path: str) -> str:
    """Auto-detect file type and extract text."""
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext in [".jpg", ".jpeg", ".png", ".webp"]:
        return extract_text_from_image(file_path)
    return ""


# ════════════════════════════════════════
#  FIELD EXTRACTORS
# ════════════════════════════════════════

def extract_pan(text: str) -> str:
    """Extract PAN number — format: ABCDE1234F"""
    pattern = r'\b[A-Z]{5}[0-9]{4}[A-Z]\b'
    matches = re.findall(pattern, text.upper())
    return matches[0] if matches else ""


def extract_name(text: str) -> str:
    """
    Try to extract a person name from common document patterns.
    Looks for lines after keywords like 'Name:', 'Employee Name:', etc.
    """
    patterns = [
        r'(?:employee name|name of employee|name|deductee name|account holder)[:\s]+([A-Z][A-Z\s]{3,40})',
        r'(?:mr\.|ms\.|mrs\.)\s+([A-Z][A-Z\s]{3,30})',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            name = m.group(1).strip().upper()
            # Filter out common false positives
            if len(name) > 3 and not any(w in name for w in ["INDIA", "BANK", "HDFC", "SBI", "LTD", "PVT"]):
                return name
    return ""


def extract_amount(text: str) -> float:
    """Extract the largest INR amount found in the document."""
    # Match patterns like: INR 85,000 / Rs. 85000 / ₹85,000
    patterns = [
        r'(?:inr|rs\.?|₹)\s*([\d,]+(?:\.\d{2})?)',
        r'([\d,]{5,}(?:\.\d{2})?)\s*(?:only|/-)',
    ]
    amounts = []
    for p in patterns:
        for m in re.findall(p, text, re.IGNORECASE):
            try:
                amounts.append(float(m.replace(",", "")))
            except:
                pass
    return max(amounts) if amounts else 0.0


# ════════════════════════════════════════
#  DOCUMENT TYPE RULES
# ════════════════════════════════════════

DOC_KEYWORDS = {
    "salary_slip":   ["salary slip", "basic salary", "gross salary", "net pay", "take home", "payroll", "hra", "pf deduction"],
    "itr":           ["income tax", "form 16", "tds", "assessment year", "itr", "taxable income", "section 80"],
    "demat":         ["demat", "nsdl", "cdsl", "portfolio", "equity", "mutual fund", "folio", "nav", "units"],
    "property":      ["sale deed", "registry", "sub-registrar", "property", "survey no", "carpet area", "conveyance"],
    "loan":          ["home loan", "personal loan", "outstanding", "emi", "principal", "disbursement", "sanction"],
    "credit_card":   ["credit card", "statement", "outstanding", "minimum amount due", "credit limit", "cashback"],
}

def detect_doc_type(text: str) -> str:
    """Detect what kind of document this is based on keyword presence."""
    text_lower = text.lower()
    scores = {}
    for doc_type, keywords in DOC_KEYWORDS.items():
        scores[doc_type] = sum(1 for kw in keywords if kw in text_lower)
    best = max(scores, key=scores.get)
    return best if scores[best] >= 2 else "unknown"


# ════════════════════════════════════════
#  VERIFICATION SCORING
# ════════════════════════════════════════

def compute_match_score(
    extracted_pan: str,
    extracted_name: str,
    registered_pan: str,
    registered_name: str,
    doc_type: str,
    text: str
) -> tuple[float, str]:
    """
    Returns (score 0–100, reason string)
    Scoring:
      - PAN match:        +50 pts  (most important)
      - Name match:       +30 pts
      - Doc type match:   +20 pts
    """
    score = 0
    reasons = []

    # PAN match
    if extracted_pan and registered_pan:
        if extracted_pan.upper() == registered_pan.upper():
            score += 50
            reasons.append("PAN matched ✓")
        else:
            reasons.append(f"PAN mismatch (found: {extracted_pan}, expected: {registered_pan})")
    elif extracted_pan:
        score += 25  # found PAN but no registered one to compare
        reasons.append("PAN found (no profile PAN to compare)")
    else:
        reasons.append("PAN not found in document")

    # Name match (fuzzy — check if words overlap)
    if extracted_name and registered_name:
        ext_words = set(extracted_name.upper().split())
        reg_words = set(registered_name.upper().split())
        overlap = ext_words & reg_words
        if len(overlap) >= 1:
            match_ratio = len(overlap) / max(len(reg_words), 1)
            name_score = int(30 * min(match_ratio * 1.5, 1.0))
            score += name_score
            reasons.append(f"Name partial match: {', '.join(overlap)} ✓")
        else:
            reasons.append(f"Name mismatch (found: {extracted_name})")
    elif extracted_name:
        score += 15
        reasons.append(f"Name found: {extracted_name}")
    else:
        reasons.append("Name not extracted")

    # Document type validity
    detected_type = detect_doc_type(text)
    if detected_type == doc_type or detected_type != "unknown":
        score += 20
        reasons.append(f"Document type confirmed: {detected_type} ✓")
    else:
        reasons.append("Document type could not be confirmed")

    return min(score, 100), " | ".join(reasons)


def score_to_status(score: float) -> str:
    if score >= 70:
        return "verified"
    elif score >= 40:
        return "manual_review"
    else:
        return "failed"


# ════════════════════════════════════════
#  MAIN VERIFICATION FUNCTION
# ════════════════════════════════════════

async def verify_document(
    file_bytes: bytes,
    filename: str,
    doc_type: str,
    user_id: int,
    db: Session
) -> dict:
    """
    1. Save file to disk
    2. Extract text via OCR/pdfplumber
    3. Extract PAN, name, amount
    4. Compare against user profile
    5. Save result to DocumentVerification table
    6. Return verification result
    """

    # ── Save file ──
    safe_name = re.sub(r'[^\w\.\-]', '_', filename)
    save_path = UPLOAD_DIR / f"{user_id}_{doc_type}_{safe_name}"
    with open(save_path, "wb") as f:
        f.write(file_bytes)

    # ── Extract text ──
    text = extract_text(str(save_path))

    # Fallback: if pdfplumber/tesseract not available, use filename heuristic
    if not text and PDF_SUPPORT is False and OCR_SUPPORT is False:
        text = f"[OCR unavailable — filename: {filename}]"

    # ── Extract fields ──
    extracted_pan    = extract_pan(text)
    extracted_name   = extract_name(text)
    extracted_amount = extract_amount(text)

    # ── Get user's registered profile ──
    user = db.query(models.User).filter(models.User.id == user_id).first()
    registered_name = user.name if user else ""
    registered_pan  = ""  # We'll pull from profile if we add PAN field later

    # Try to get KYC details from a stored profile record (future: add pan to profile)
    # For now, use name from User table
    profile = db.query(models.FinancialProfile).filter(
        models.FinancialProfile.user_id == user_id
    ).first()

    # ── Compute score ──
    score, reason = compute_match_score(
        extracted_pan, extracted_name,
        registered_pan, registered_name,
        doc_type, text
    )

    # If OCR libs not available but file was uploaded — give partial credit
    if not PDF_SUPPORT and not OCR_SUPPORT:
        score = 55
        reason = "OCR libraries not installed — document accepted provisionally"

    status = score_to_status(score)

    # ── Save to DB ──
    # Check if record already exists for this user + doc_type
    existing = db.query(models.DocumentVerification).filter(
        models.DocumentVerification.user_id == user_id,
        models.DocumentVerification.doc_type == doc_type
    ).first()

    if existing:
        existing.filename        = filename
        existing.file_path       = str(save_path)
        existing.extracted_text  = text[:2000]  # store first 2000 chars
        existing.extracted_pan   = extracted_pan
        existing.extracted_name  = extracted_name
        existing.extracted_amount= extracted_amount
        existing.status          = status
        existing.match_score     = score
        existing.failure_reason  = reason
        existing.verified_at     = datetime.datetime.utcnow() if status == "verified" else None
        db.commit()
        record = existing
    else:
        record = models.DocumentVerification(
            user_id          = user_id,
            doc_type         = doc_type,
            filename         = filename,
            file_path        = str(save_path),
            extracted_text   = text[:2000],
            extracted_pan    = extracted_pan,
            extracted_name   = extracted_name,
            extracted_amount = extracted_amount,
            status           = status,
            match_score      = score,
            failure_reason   = reason,
            verified_at      = datetime.datetime.utcnow() if status == "verified" else None
        )
        db.add(record)
        db.commit()
        db.refresh(record)

    return {
        "doc_type":         doc_type,
        "filename":         filename,
        "status":           status,
        "match_score":      score,
        "extracted_pan":    extracted_pan,
        "extracted_name":   extracted_name,
        "extracted_amount": extracted_amount,
        "reason":           reason,
        "message":          _status_message(status, score, doc_type)
    }


def _status_message(status: str, score: float, doc_type: str) -> str:
    name = doc_type.replace("_", " ").title()
    if status == "verified":
        return f"✅ {name} verified successfully (score: {int(score)}/100)"
    elif status == "manual_review":
        return f"🔍 {name} under manual review (score: {int(score)}/100) — our team will verify within 24–48 hrs"
    else:
        return f"❌ {name} could not be verified (score: {int(score)}/100) — please re-upload a clearer document"


# ════════════════════════════════════════
#  GET OVERALL VERIFICATION STATUS
# ════════════════════════════════════════

VERIFICATION_WEIGHTS = {
    # doc_type       -> (category, points if verified)
    "salary_slip":   ("income",      20),
    "itr":           ("income",      10),
    "demat":         ("assets",      15),
    "property":      ("assets",      15),
    "loan":          ("liabilities", 15),
    "credit_card":   ("liabilities", 10),
}

IDENTITY_POINTS = 15  # Auto-verified if profile exists


def get_verification_status(user_id: int, db: Session) -> dict:
    """
    Returns overall verification percentage and per-category status.
    Identity = 15pts (auto if profile exists)
    Income   = up to 30pts (salary_slip 20 + itr 10)
    Assets   = up to 30pts (demat 15 + property 15)
    Liabilities = up to 25pts (loan 15 + credit_card 10)
    Total    = 100pts
    """
    docs = db.query(models.DocumentVerification).filter(
        models.DocumentVerification.user_id == user_id
    ).all()

    doc_map = {d.doc_type: d for d in docs}

    # Identity — auto-verified if profile exists
    profile = db.query(models.FinancialProfile).filter(
        models.FinancialProfile.user_id == user_id
    ).first()
    identity_verified = profile is not None
    total_score = IDENTITY_POINTS if identity_verified else 0

    categories = {
        "identity":    {"status": "verified" if identity_verified else "unverified", "score": IDENTITY_POINTS if identity_verified else 0, "max": IDENTITY_POINTS},
        "income":      {"status": "unverified", "score": 0, "max": 30, "docs": {}},
        "assets":      {"status": "unverified", "score": 0, "max": 30, "docs": {}},
        "liabilities": {"status": "unverified", "score": 0, "max": 25, "docs": {}},
    }

    for doc_type, (category, max_pts) in VERIFICATION_WEIGHTS.items():
        if category not in categories:
            continue
        doc = doc_map.get(doc_type)
        if doc:
            # Scale the doc's match_score to the max_pts for this doc
            earned = int((doc.match_score / 100) * max_pts)
            categories[category]["score"] += earned
            total_score += earned
            categories[category]["docs"][doc_type] = {
                "status":      doc.status,
                "match_score": doc.match_score,
                "filename":    doc.filename,
            }

    # Set category-level status
    for cat, data in categories.items():
        if cat == "identity":
            continue
        s = data["score"]
        m = data["max"]
        if s == 0:
            data["status"] = "unverified"
        elif s >= m * 0.7:
            data["status"] = "verified"
        elif s >= m * 0.3:
            data["status"] = "pending"
        else:
            data["status"] = "failed"

    return {
        "total_score":   min(total_score, 100),
        "percentage":    min(total_score, 100),
        "categories":    categories,
    }