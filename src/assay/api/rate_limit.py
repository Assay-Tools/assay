"""Rate limiting configuration for the Assay API."""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Shared limiter instance — used by both app.py (middleware) and routes.py (decorators).
# In-memory storage is fine for single-process Railway deployment.
limiter = Limiter(
    key_func=get_remote_address,
    headers_enabled=True,  # Return X-RateLimit-* headers
)

# Free tier: 100 API calls per day per IP.
# Web pages (HTML routes) are not rate-limited.
API_RATE_LIMIT = "100/day"
