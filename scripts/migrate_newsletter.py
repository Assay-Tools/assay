"""Migration: Add newsletter infrastructure columns and tables.

Adds to email_subscribers:
  - confirmed_at (TIMESTAMP WITH TIME ZONE)
  - confirmation_token (VARCHAR(64), UNIQUE)
  - unsubscribe_token (VARCHAR(64), UNIQUE)

Creates newsletter_issues table.

Safe to run multiple times — checks before adding.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import inspect, text

from assay.database import engine


def migrate():
    inspector = inspect(engine)

    with engine.begin() as conn:
        # -- email_subscribers: add new columns if missing --
        existing = {c["name"] for c in inspector.get_columns("email_subscribers")}

        if "confirmed_at" not in existing:
            conn.execute(text(
                "ALTER TABLE email_subscribers ADD COLUMN confirmed_at TIMESTAMP WITH TIME ZONE"
            ))
            print("Added email_subscribers.confirmed_at")

        if "confirmation_token" not in existing:
            conn.execute(text(
                "ALTER TABLE email_subscribers ADD COLUMN confirmation_token VARCHAR(64) UNIQUE"
            ))
            print("Added email_subscribers.confirmation_token")

        if "unsubscribe_token" not in existing:
            conn.execute(text(
                "ALTER TABLE email_subscribers ADD COLUMN unsubscribe_token VARCHAR(64) UNIQUE"
            ))
            print("Added email_subscribers.unsubscribe_token")

        # -- newsletter_issues table --
        if "newsletter_issues" not in inspector.get_table_names():
            conn.execute(text("""
                CREATE TABLE newsletter_issues (
                    id SERIAL PRIMARY KEY,
                    subject VARCHAR(500) NOT NULL,
                    content_html TEXT NOT NULL,
                    content_text TEXT NOT NULL,
                    recipients_count INTEGER DEFAULT 0,
                    sent_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            print("Created newsletter_issues table")

        # -- Backfill unsubscribe tokens for existing subscribers --
        from secrets import token_urlsafe
        rows = conn.execute(text(
            "SELECT id FROM email_subscribers WHERE unsubscribe_token IS NULL"
        )).fetchall()
        for row in rows:
            conn.execute(
                text("UPDATE email_subscribers SET unsubscribe_token = :token WHERE id = :id"),
                {"token": token_urlsafe(32), "id": row[0]},
            )
        if rows:
            print(f"Backfilled unsubscribe tokens for {len(rows)} existing subscribers")

    print("Migration complete.")


if __name__ == "__main__":
    migrate()
