"""Main FastAPI application for Assay."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from assay.database import init_db

from .rate_limit import limiter
from .routes import router
from .web_routes import router as web_router

app = FastAPI(
    title="Assay",
    description="The quality layer for agentic software — package agent-friendliness ratings",
    version="0.1.0",
)

# Attach rate limiter to app state (required by slowapi)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — allow all origins for MVP
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(router)

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
