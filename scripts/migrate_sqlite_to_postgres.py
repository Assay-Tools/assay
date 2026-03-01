#!/usr/bin/env python3
"""Migrate all data from SQLite to PostgreSQL.

Usage:
    python scripts/migrate_sqlite_to_postgres.py <sqlite_path> <postgres_url>

Example:
    python scripts/migrate_sqlite_to_postgres.py ./assay.db postgresql://user:pass@host:5432/assay
"""

import sys
from sqlalchemy import create_engine, inspect, text, Boolean
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

BATCH_SIZE = 500


def migrate_table_raw(sqlite_engine, pg_engine, model):
    """Migrate a table using raw INSERT for speed (avoids ORM overhead)."""
    table = model.__table__
    table_name = table.name
    columns = [c.name for c in table.columns]

    # Identify boolean columns (SQLite stores as 0/1, Postgres needs True/False)
    bool_cols = {c.name for c in table.columns if isinstance(c.type, Boolean)}

    with sqlite_engine.connect() as sqlite_conn:
        rows = sqlite_conn.execute(text(f"SELECT * FROM {table_name}")).fetchall()

    count = len(rows)
    if count == 0:
        print(f"  {table_name}: 0 records, skipping")
        return

    print(f"  {table_name}: migrating {count} records...", end=" ", flush=True)

    # Build parameterized INSERT
    col_list = ", ".join(columns)
    param_list = ", ".join(f":{c}" for c in columns)
    insert_sql = text(f"INSERT INTO {table_name} ({col_list}) VALUES ({param_list})")

    def fix_row(row):
        d = dict(zip(columns, row))
        for col in bool_cols:
            if d[col] is not None:
                d[col] = bool(d[col])
        return d

    with pg_engine.begin() as pg_conn:
        # Process in batches
        for i in range(0, count, BATCH_SIZE):
            batch = rows[i:i + BATCH_SIZE]
            params = [fix_row(row) for row in batch]
            pg_conn.execute(insert_sql, params)
            if count > BATCH_SIZE:
                print(f"{min(i + BATCH_SIZE, count)}/{count}", end=" ", flush=True)

    print("done")


def migrate(sqlite_path: str, postgres_url: str):
    sqlite_engine = create_engine(f"sqlite:///{sqlite_path}")
    pg_engine = create_engine(postgres_url)

    # Drop and recreate all tables (clean slate)
    print("Dropping existing tables...")
    Base.metadata.drop_all(bind=pg_engine)
    print("Creating tables in PostgreSQL...")
    Base.metadata.create_all(bind=pg_engine)

    try:
        for model in MODELS:
            migrate_table_raw(sqlite_engine, pg_engine, model)

        print("\nMigration complete!")

        # Verify counts
        print("\nVerification:")
        with sqlite_engine.connect() as sc, pg_engine.connect() as pc:
            for model in MODELS:
                tn = model.__tablename__
                sqlite_count = sc.execute(text(f"SELECT COUNT(*) FROM {tn}")).scalar()
                pg_count = pc.execute(text(f"SELECT COUNT(*) FROM {tn}")).scalar()
                status = "OK" if sqlite_count == pg_count else "MISMATCH"
                print(f"  {tn}: SQLite={sqlite_count}, Postgres={pg_count} [{status}]")

    except Exception as e:
        print(f"\nError during migration: {e}")
        raise


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    migrate(sys.argv[1], sys.argv[2])
