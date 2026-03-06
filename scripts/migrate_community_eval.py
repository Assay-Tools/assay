"""Migration: Add evaluator_engine and rubric_version to evaluation_runs.

Adds columns for tracking which AI engine produced each evaluation and
which rubric version was used. Backfills existing rows with 'claude' / '1.0'.

Usage:
    uv run python scripts/migrate_community_eval.py
    uv run python scripts/migrate_community_eval.py --db postgresql://...
"""

import argparse
import sys

from sqlalchemy import create_engine, inspect, text

from assay.config import settings


def migrate(db_url: str) -> None:
    engine = create_engine(db_url)
    inspector = inspect(engine)

    columns = {c["name"] for c in inspector.get_columns("evaluation_runs")}

    with engine.begin() as conn:
        if "evaluator_engine" not in columns:
            print("Adding evaluator_engine column to evaluation_runs...")
            conn.execute(text(
                "ALTER TABLE evaluation_runs ADD COLUMN evaluator_engine VARCHAR(100)"
            ))
            conn.execute(text(
                "UPDATE evaluation_runs SET evaluator_engine = 'claude' WHERE evaluator_engine IS NULL"
            ))
            print("  Done. Backfilled existing rows with 'claude'.")
        else:
            print("evaluator_engine column already exists, skipping.")

        if "rubric_version" not in columns:
            print("Adding rubric_version column to evaluation_runs...")
            conn.execute(text(
                "ALTER TABLE evaluation_runs ADD COLUMN rubric_version VARCHAR(20)"
            ))
            conn.execute(text(
                "UPDATE evaluation_runs SET rubric_version = '1.0' WHERE rubric_version IS NULL"
            ))
            print("  Done. Backfilled existing rows with '1.0'.")
        else:
            print("rubric_version column already exists, skipping.")

    print("Migration complete.")


def main():
    parser = argparse.ArgumentParser(description="Add community evaluation columns")
    parser.add_argument("--db", type=str, default=None, help="Database URL (defaults to settings)")
    args = parser.parse_args()

    db_url = args.db or settings.database_url
    print(f"Migrating: {db_url.split('@')[-1] if '@' in db_url else db_url}")
    migrate(db_url)


if __name__ == "__main__":
    main()
