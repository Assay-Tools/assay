"""Migration: Add multi-dimensional scorecard columns.

Adds security_score and reliability_score to packages table,
and new sub-component columns to package_agent_readiness table.

Safe to run multiple times — uses IF NOT EXISTS / checks for column existence.
"""

import os
import sys

from sqlalchemy import create_engine, text


def get_db_url():
    """Get database URL from environment variable, or default to local SQLite."""
    return os.getenv("DATABASE_URL", "sqlite:///./assay.db")


def column_exists(conn, table: str, column: str, dialect: str) -> bool:
    """Check if a column already exists."""
    if dialect == "sqlite":
        result = conn.execute(text(f"PRAGMA table_info({table})"))
        columns = [row[1] for row in result]
        return column in columns
    else:
        # PostgreSQL
        result = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = :table AND column_name = :column"
        ), {"table": table, "column": column})
        return result.fetchone() is not None


def migrate(db_url: str):
    engine = create_engine(db_url)
    dialect = "sqlite" if "sqlite" in db_url else "postgresql"

    # New columns for packages table
    pkg_columns = [
        ("security_score", "FLOAT"),
        ("reliability_score", "FLOAT"),
    ]

    # New columns for package_agent_readiness table
    ar_columns = [
        ("security_score", "FLOAT"),
        ("reliability_score", "FLOAT"),
        ("auth_complexity", "FLOAT"),
        ("rate_limit_clarity", "FLOAT"),
        ("tls_enforcement", "FLOAT"),
        ("auth_strength", "FLOAT"),
        ("scope_granularity", "FLOAT"),
        ("dependency_hygiene", "FLOAT"),
        ("secret_handling", "FLOAT"),
        ("security_notes", "TEXT"),
        ("uptime_documented", "FLOAT"),
        ("version_stability", "FLOAT"),
        ("breaking_changes_history", "FLOAT"),
        ("error_recovery", "FLOAT"),
    ]

    with engine.begin() as conn:
        added = 0

        for col_name, col_type in pkg_columns:
            if not column_exists(conn, "packages", col_name, dialect):
                conn.execute(text(f"ALTER TABLE packages ADD COLUMN {col_name} {col_type}"))
                print(f"  + packages.{col_name}")
                added += 1
            else:
                print(f"  = packages.{col_name} (exists)")

        for col_name, col_type in ar_columns:
            if not column_exists(conn, "package_agent_readiness", col_name, dialect):
                conn.execute(text(
                    f"ALTER TABLE package_agent_readiness ADD COLUMN {col_name} {col_type}"
                ))
                print(f"  + package_agent_readiness.{col_name}")
                added += 1
            else:
                print(f"  = package_agent_readiness.{col_name} (exists)")

        # Backfill: copy existing security_posture_score data to new security columns
        # where available (from af_score_components stored in evaluation_runs.raw_output)
        # For now, just set security_score from mcp_security_score as a reasonable default
        conn.execute(text("""
            UPDATE package_agent_readiness
            SET security_score = mcp_security_score
            WHERE security_score IS NULL AND mcp_security_score IS NOT NULL
        """))

        # Copy to packages table too
        if dialect == "sqlite":
            conn.execute(text("""
                UPDATE packages
                SET security_score = (
                    SELECT par.security_score
                    FROM package_agent_readiness par
                    WHERE par.package_id = packages.id
                )
                WHERE security_score IS NULL
            """))
        else:
            conn.execute(text("""
                UPDATE packages p
                SET security_score = par.security_score
                FROM package_agent_readiness par
                WHERE par.package_id = p.id AND p.security_score IS NULL
            """))

        print(f"\nMigration complete: {added} columns added")


if __name__ == "__main__":
    db_url = sys.argv[1] if len(sys.argv) > 1 else get_db_url()
    print(f"Migrating: {db_url[:50]}...")
    migrate(db_url)
