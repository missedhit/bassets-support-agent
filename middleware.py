"""
Middleware for the Bassets Support Agent API.

Provides:
- Security headers (CSP, X-Frame-Options, etc.)
- Request logging with request IDs
- Rate limiting via slowapi
"""

import logging
import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from config import APP_ENV

logger = logging.getLogger("bassets.api")


# ---------------------------------------------------------------------------
# Security Headers
# ---------------------------------------------------------------------------

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )

        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "script-src 'self'; "
            "connect-src 'self'"
        )

        return response


# ---------------------------------------------------------------------------
# Request Logging
# ---------------------------------------------------------------------------

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with timing and a unique request ID."""

    async def dispatch(self, request: Request, call_next):
        request_id = uuid.uuid4().hex[:8]
        start = time.time()

        response = await call_next(request)

        duration_ms = int((time.time() - start) * 1000)
        response.headers["X-Request-ID"] = request_id

        # Skip logging for static file requests in production
        path = request.url.path
        if path.startswith("/static/") and APP_ENV == "production":
            return response

        logger.info(
            "%s %s -> %s (%dms) [%s]",
            request.method,
            path,
            response.status_code,
            duration_ms,
            request_id,
        )

        return response


# ---------------------------------------------------------------------------
# Rate Limiting Setup
# ---------------------------------------------------------------------------

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri="memory://",
)
