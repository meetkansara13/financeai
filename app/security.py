"""
Rate limiting, CORS, security headers, and brute-force protection.
"""
import os
import time
import secrets
from collections import defaultdict
from typing import Dict, Tuple
from fastapi import Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


# ── IN-MEMORY RATE LIMITER ────────────────────────────────────────────────────
# For production with multiple workers, replace with Redis.

class _RateLimitStore:
    """Thread-safe-enough for single-process FastAPI / uvicorn."""
    def __init__(self):
        # {key: (count, window_start)}
        self._store: Dict[str, Tuple[int, float]] = defaultdict(lambda: (0, time.time()))
        self._failed_logins: Dict[str, Tuple[int, float]] = defaultdict(lambda: (0, time.time()))

    def check(self, key: str, limit: int, window_seconds: int) -> bool:
        """Returns True if allowed, False if rate-limited."""
        count, start = self._store[key]
        now = time.time()
        if now - start > window_seconds:
            self._store[key] = (1, now)
            return True
        if count >= limit:
            return False
        self._store[key] = (count + 1, start)
        return True

    def record_failed_login(self, key: str):
        count, start = self._failed_logins[key]
        now = time.time()
        if now - start > 900:  # 15-minute window
            self._failed_logins[key] = (1, now)
        else:
            self._failed_logins[key] = (count + 1, start)

    def is_locked_out(self, key: str) -> bool:
        count, start = self._failed_logins[key]
        if time.time() - start > 900:  # window expired
            return False
        return count >= 10  # 10 failures → 15-min lockout

    def clear_failed_logins(self, key: str):
        self._failed_logins[key] = (0, time.time())


_store = _RateLimitStore()


def rate_limit(key: str, limit: int, window_seconds: int):
    """Call from a route to enforce rate limiting."""
    if not _store.check(key, limit, window_seconds):
        raise HTTPException(
            status_code=429,
            detail=f"Too many requests. Please wait and try again.",
            headers={"Retry-After": str(window_seconds)},
        )


def check_login_lockout(identifier: str):
    if _store.is_locked_out(identifier):
        raise HTTPException(
            status_code=429,
            detail="Account temporarily locked due to too many failed attempts. Try again in 15 minutes.",
            headers={"Retry-After": "900"},
        )


def record_failed_login(identifier: str):
    _store.record_failed_login(identifier)


def clear_failed_login(identifier: str):
    _store.clear_failed_logins(identifier)


# ── SECURITY HEADERS MIDDLEWARE ───────────────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        # Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        # XSS protection (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        # Only send referrer to same origin
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Remove server fingerprint
        if "server" in response.headers:
            del response.headers["server"]
        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        # Permissions policy — disable unnecessary browser features
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )

        return response


# ── CORS CONFIG ───────────────────────────────────────────────────────────────

def get_cors_origins() -> list:
    origins_env = os.getenv("ALLOWED_ORIGINS", "")
    if origins_env:
        return [o.strip() for o in origins_env.split(",") if o.strip()]
    # Development fallback — restrict to localhost only
    return ["http://localhost:8000", "http://127.0.0.1:8000"]


CORS_CONFIG = dict(
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)