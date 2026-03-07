"""Main FastAPI application for Assay."""

import logging
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from assay.database import init_db

from .admin_routes import router as admin_router
from .auth_routes import router as auth_router
from .payments import router as payments_router
from .rate_limit import limiter
from .routes import router
from .submission_routes import router as submission_router
from .usage import api_call_counts, api_error_counts
from .web_routes import router as web_router

api_logger = logging.getLogger("assay.api_usage")

app = FastAPI(
    title="Assay",
    summary="The quality layer for agentic software",
    description=(
        "Independent agent-friendliness ratings for MCP servers, APIs, and SDKs. "
        "Assay scores packages on documentation accuracy, error quality, security "
        "posture, and more — so agents and developers can pick the right tool."
    ),
    version="0.1.0",
    contact={"name": "Assay Tools", "url": "https://assay.tools"},
    license_info={"name": "MIT"},
    openapi_tags=[
        {"name": "packages", "description": "Browse, search, and inspect evaluated packages"},
        {"name": "categories", "description": "Package categories and per-category listings"},
        {"name": "compare", "description": "Side-by-side package comparison"},
        {"name": "stats", "description": "Sitewide statistics and score distribution"},
        {"name": "contribute", "description": "Evaluation queue for community contributors"},
        {
            "name": "evaluations",
            "description": "Submit and manage package evaluations (API key required)",
        },
        {"name": "system", "description": "Health checks and operational endpoints"},
    ],
)

# Attach rate limiter to app state (required by slowapi)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — allow all origins for public API (no credentials with wildcard origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Security headers


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        path = request.url.path
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Allow embedding for /embed/ routes, DENY everywhere else
        if path.startswith("/embed/"):
            pass  # No X-Frame-Options for embeddable routes
        else:
            response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Content-Security-Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://js.stripe.com; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self' https://api.stripe.com; "
            "frame-src https://js.stripe.com; "
            "frame-ancestors 'none'"
        )
        # Cache-Control for API responses (5 min for reads, scores update infrequently)
        if path.startswith("/v1/") and request.method == "GET":
            if "Cache-Control" not in response.headers:
                response.headers["Cache-Control"] = "public, max-age=300"
        return response


class APIUsageMiddleware(BaseHTTPMiddleware):
    """Track API call volume, response times, and errors."""

    async def dispatch(self, request, call_next):
        path = request.url.path
        # Only track /v1/ API endpoints (not web pages or static files)
        if not path.startswith("/v1/"):
            return await call_next(request)

        start = time.monotonic()
        response = await call_next(request)
        elapsed = time.monotonic() - start

        # Track counters
        api_call_counts[path] += 1
        if response.status_code >= 400:
            api_error_counts[path] += 1

        # Log slow requests
        if elapsed > 2.0:
            api_logger.warning(
                "Slow API: %s %s %.2fs status=%d",
                request.method, path, elapsed, response.status_code,
            )

        return response


app.add_middleware(APIUsageMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# API routes
app.include_router(router)
app.include_router(submission_router)
app.include_router(payments_router)
app.include_router(admin_router)

# Auth routes (GitHub OAuth)
app.include_router(auth_router)

# Web frontend routes
app.include_router(web_router)

# Static files and templates for web frontend
_src_dir = Path(__file__).parent.parent  # src/assay/
_templates_dir = _src_dir / "templates"
_static_dir = _src_dir / "static"

if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

# Jinja2 templates — available for web frontend routes
templates = Jinja2Templates(directory=str(_templates_dir))


@app.on_event("startup")
def startup():
    """Create tables and run pending migrations."""
    init_db()
    _run_migrations()


def _run_migrations():
    """Add new columns if they don't exist. Safe to run repeatedly."""
    import logging

    from sqlalchemy import text

    from assay.database import engine

    logger = logging.getLogger("assay.migrations")

    # Define new columns to add (table, column, type)
    new_columns = [
        ("packages", "security_score", "FLOAT"),
        ("packages", "reliability_score", "FLOAT"),
        ("package_agent_readiness", "security_score", "FLOAT"),
        ("package_agent_readiness", "reliability_score", "FLOAT"),
        ("package_agent_readiness", "auth_complexity", "FLOAT"),
        ("package_agent_readiness", "rate_limit_clarity", "FLOAT"),
        ("package_agent_readiness", "tls_enforcement", "FLOAT"),
        ("package_agent_readiness", "auth_strength", "FLOAT"),
        ("package_agent_readiness", "scope_granularity", "FLOAT"),
        ("package_agent_readiness", "dependency_hygiene", "FLOAT"),
        ("package_agent_readiness", "secret_handling", "FLOAT"),
        ("package_agent_readiness", "security_notes", "TEXT"),
        ("package_agent_readiness", "uptime_documented", "FLOAT"),
        ("package_agent_readiness", "version_stability", "FLOAT"),
        ("package_agent_readiness", "breaking_changes_history", "FLOAT"),
        ("package_agent_readiness", "error_recovery", "FLOAT"),
        # Discovery pipeline columns
        ("packages", "package_type", "VARCHAR(50) DEFAULT 'mcp_server'"),
        ("packages", "discovery_source", "VARCHAR(100)"),
        ("packages", "priority", "VARCHAR(10) DEFAULT 'low'"),
        ("packages", "stars", "INTEGER"),
        ("packages", "legacy_id", "VARCHAR(255)"),
        # Community evaluation columns (Phase 1+2)
        ("evaluation_runs", "evaluator_engine", "VARCHAR(100)"),
        ("evaluation_runs", "rubric_version", "VARCHAR(20)"),
        # Order security — unguessable access tokens
        ("orders", "access_token", "VARCHAR(64)"),
    ]

    dialect = "sqlite" if "sqlite" in str(engine.url) else "postgresql"

    with engine.begin() as conn:
        for table, column, col_type in new_columns:
            # Check if column exists
            if dialect == "sqlite":
                result = conn.execute(text(f"PRAGMA table_info({table})"))
                exists = column in [row[1] for row in result]
            else:
                result = conn.execute(text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_name = :table AND column_name = :column"
                ), {"table": table, "column": column})
                exists = result.fetchone() is not None

            if not exists:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
                logger.info("Added column %s.%s", table, column)

        # Backfill discovery_source for existing packages
        conn.execute(text("""
            UPDATE packages SET discovery_source = 'github'
            WHERE discovery_source IS NULL
        """))

        # Widen discovery_source to TEXT and convert plain strings to JSON lists
        if dialect == "postgresql":
            conn.execute(text(
                "ALTER TABLE packages ALTER COLUMN discovery_source TYPE TEXT"
            ))
        # Convert legacy plain-string values to JSON list format
        conn.execute(text("""
            UPDATE packages
            SET discovery_source = '["' || discovery_source || '"]'
            WHERE discovery_source IS NOT NULL
              AND discovery_source NOT LIKE '[%'
        """))

        # Backfill security_score from legacy mcp_security_score
        conn.execute(text("""
            UPDATE package_agent_readiness
            SET security_score = mcp_security_score
            WHERE security_score IS NULL AND mcp_security_score IS NOT NULL
        """))
        if dialect == "sqlite":
            conn.execute(text("""
                UPDATE packages SET security_score = (
                    SELECT par.security_score FROM package_agent_readiness par
                    WHERE par.package_id = packages.id
                ) WHERE security_score IS NULL
            """))
        else:
            conn.execute(text("""
                UPDATE packages p SET security_score = par.security_score
                FROM package_agent_readiness par
                WHERE par.package_id = p.id AND p.security_score IS NULL
            """))

        # Backfill evaluator_engine for existing evaluation runs
        conn.execute(text("""
            UPDATE evaluation_runs SET evaluator_engine = 'claude'
            WHERE evaluator_engine IS NULL
        """))
        conn.execute(text("""
            UPDATE evaluation_runs SET rubric_version = '1.0'
            WHERE rubric_version IS NULL
        """))

        # Backfill access_token for existing orders
        import secrets as _secrets
        result = conn.execute(text(
            "SELECT id FROM orders WHERE access_token IS NULL"
        ))
        for row in result:
            conn.execute(
                text("UPDATE orders SET access_token = :token WHERE id = :id"),
                {"token": _secrets.token_urlsafe(32), "id": row[0]},
            )
