"""Rate limiting configuration for the Assay API."""

import ipaddress

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

# Railway's internal load balancer uses 100.64.0.0/10 (RFC 6598 shared space).
# request.client.host always shows a Railway internal IP, not the real client.
# Real client IPs are in the X-Forwarded-For header.
_RAILWAY_PROXY_NETWORK = ipaddress.ip_network("100.64.0.0/10")


def _get_real_ip(request: Request) -> str:
    """Extract real client IP, reading through Railway's proxy layer.

    Railway sets X-Forwarded-For with the actual client IP. The
    request.client.host is always a 100.64.x.x Railway internal IP,
    making the default get_remote_address useless for rate limiting.

    Takes the leftmost non-Railway IP from X-Forwarded-For. Falls back
    to the leftmost IP in the header (if all are Railway IPs), then to
    get_remote_address if the header is absent.
    """
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        candidates = [ip.strip() for ip in forwarded_for.split(",")]
        for ip_str in candidates:
            try:
                addr = ipaddress.ip_address(ip_str)
                if addr not in _RAILWAY_PROXY_NETWORK:
                    return ip_str
            except ValueError:
                continue
        # All IPs were Railway-internal — take leftmost as best guess
        if candidates[0]:
            return candidates[0]
    return get_remote_address(request)


# Shared limiter instance — used by both app.py (middleware) and routes.py (decorators).
# In-memory storage is fine for single-process Railway deployment.
limiter = Limiter(
    key_func=_get_real_ip,
    headers_enabled=True,  # Return X-RateLimit-* headers
)

# Free tier: 100 API calls per day per IP.
API_RATE_LIMIT = "100/day"

# Web browse routes: 500 page views per day per IP.
# Enough for any human researcher; stops automated catalog scrapers that
# enumerate thousands of package pages per session.
WEB_RATE_LIMIT = "500/day"
