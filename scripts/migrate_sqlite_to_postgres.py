#!/usr/bin/env python3
"""Migrate all data from SQLite to PostgreSQL.

Usage:
    python scripts/migrate_sqlite_to_postgres.py <sqlite_path> <postgres_url>

Example:
    python scripts/migrate_sqlite_to_postgres.py ./assay.db postgresql://user:pass@host:5432/assay
"""

import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# Add src to path
sys.path.insert(0, "src")

from assay.database import Base
from assay.models.package import (
    Package, PackageInterface, PackageAuth, PackagePricing,
    PackagePerformance, PackageRequirements, PackageAgentReadiness,
    Category, EvaluationRun,
)


# Order matters for foreign keys
MODELS = [
    Category,
    Package,
    PackageInterface,
    PackageAuth,
    PackagePricing,
    PackagePerformance,
    PackageRequirements,
    PackageAgentReadiness,
    EvaluationRun,
]


def migrate(sqlite_path: str, postgres_url: str):
    sqlite_engine = create_engine(f"sqlite:///{sqlite_path}")
    pg_engine = create_engine(postgres_url)

    # Create all tables in Postgres
    print("Creating tables in PostgreSQL...")
    Base.metadata.create_all(bind=pg_engine)

    sqlite_session = Session(sqlite_engine)
    pg_session = Session(pg_engine)

    try:
        for model in MODELS:
            table_name = model.__tablename__
            records = sqlite_session.query(model).all()
            count = len(records)

            if count == 0:
                print(f"  {table_name}: 0 records, skipping")
                continue

            print(f"  {table_name}: migrating {count} records...", end=" ", flush=True)

            # Detach from SQLite session and merge into Postgres
            for record in records:
                sqlite_session.expunge(record)
                pg_session.merge(record)

            pg_session.flush()
            print("done")

        pg_session.commit()
        print("\nMigration complete!")

        # Verify counts
        print("\nVerification:")
        for model in MODELS:
            sqlite_count = sqlite_session.query(model).count()
            pg_count = pg_session.query(model).count()
            status = "OK" if sqlite_count == pg_count else "MISMATCH"
            print(f"  {model.__tablename__}: SQLite={sqlite_count}, Postgres={pg_count} [{status}]")

    except Exception as e:
        pg_session.rollback()
        print(f"\nError during migration: {e}")
        raise
    finally:
        sqlite_session.close()
        pg_session.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    migrate(sys.argv[1], sys.argv[2])
