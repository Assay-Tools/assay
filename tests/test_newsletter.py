"""Tests for the newsletter pipeline: collector, writer, sender."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from assay.models import Category, EmailSubscriber, NewsletterIssue, Package, ScoreSnapshot
from assay.newsletter.collector import WeeklyDigest, collect_weekly_data
from assay.newsletter.sender import get_active_subscribers, send_newsletter_issue
from assay.newsletter.writer import generate_subject, parse_newsletter_output


# -- Fixtures --


@pytest.fixture()
def seeded_db(db):
    """DB with categories, packages, and snapshots for newsletter testing."""
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=3)
    old = now - timedelta(days=14)

    cat = Category(slug="testing", name="Testing", description="Test tools")
    db.add(cat)

    # Package discovered this week
    new_pkg = Package(
        id="new-tool",
        name="New Tool",
        category_slug="testing",
        package_type="mcp_server",
        stars=42,
        created_at=week_ago,
    )
    db.add(new_pkg)

    # Package with score changes
    mover = Package(
        id="mover-pkg",
        name="Mover Package",
        category_slug="testing",
        package_type="api",
        af_score=75,
        security_score=80,
        reliability_score=70,
        last_evaluated=week_ago,
        created_at=old,
    )
    db.add(mover)

    # Old snapshot
    db.add(ScoreSnapshot(
        package_id="mover-pkg",
        af_score=60,
        security_score=70,
        reliability_score=65,
        recorded_at=old,
    ))
    # New snapshot
    db.add(ScoreSnapshot(
        package_id="mover-pkg",
        af_score=75,
        security_score=80,
        reliability_score=70,
        recorded_at=week_ago,
    ))

    # Newly evaluated package (first snapshot this week)
    newly_eval = Package(
        id="fresh-eval",
        name="Fresh Eval",
        category_slug="testing",
        package_type="sdk",
        af_score=82,
        security_score=90,
        reliability_score=75,
        last_evaluated=week_ago,
        created_at=old,
    )
    db.add(newly_eval)
    db.add(ScoreSnapshot(
        package_id="fresh-eval",
        af_score=82,
        security_score=90,
        reliability_score=75,
        recorded_at=week_ago,
    ))

    db.commit()
    return db


@pytest.fixture()
def subscribers(db):
    """Create test subscribers in various states."""
    from secrets import token_urlsafe

    confirmed = EmailSubscriber(
        email="active@example.com",
        confirmed=True,
        confirmed_at=datetime.now(timezone.utc),
        confirmation_token=token_urlsafe(32),
        unsubscribe_token=token_urlsafe(32),
    )
    unconfirmed = EmailSubscriber(
        email="pending@example.com",
        confirmed=False,
        confirmation_token=token_urlsafe(32),
        unsubscribe_token=token_urlsafe(32),
    )
    unsubscribed = EmailSubscriber(
        email="gone@example.com",
        confirmed=True,
        confirmed_at=datetime.now(timezone.utc),
        unsubscribed_at=datetime.now(timezone.utc),
        confirmation_token=token_urlsafe(32),
        unsubscribe_token=token_urlsafe(32),
    )
    db.add_all([confirmed, unconfirmed, unsubscribed])
    db.commit()
    return {"confirmed": confirmed, "unconfirmed": unconfirmed, "unsubscribed": unsubscribed}


# -- Collector tests --


class TestCollector:
    def test_collects_new_packages(self, seeded_db):
        digest = collect_weekly_data(seeded_db)
        ids = [p.package_id for p in digest.new_packages]
        assert "new-tool" in ids

    def test_collects_score_movers(self, seeded_db):
        digest = collect_weekly_data(seeded_db)
        mover_ids = [m.package_id for m in digest.score_movers]
        assert "mover-pkg" in mover_ids

    def test_score_mover_deltas(self, seeded_db):
        digest = collect_weekly_data(seeded_db)
        mover = next(m for m in digest.score_movers if m.package_id == "mover-pkg")
        assert mover.af_delta == 15
        assert mover.security_delta == 10

    def test_collects_newly_evaluated(self, seeded_db):
        digest = collect_weekly_data(seeded_db)
        ids = [n.package_id for n in digest.newly_evaluated]
        assert "fresh-eval" in ids

    def test_collects_category_stats(self, seeded_db):
        digest = collect_weekly_data(seeded_db)
        testing_cat = next(
            (c for c in digest.category_stats if c.slug == "testing"), None,
        )
        assert testing_cat is not None
        assert testing_cat.total_evaluated >= 2

    def test_ecosystem_totals(self, seeded_db):
        digest = collect_weekly_data(seeded_db)
        assert digest.total_packages >= 3
        assert digest.total_evaluated >= 2

    def test_empty_db(self, db):
        digest = collect_weekly_data(db)
        assert digest.total_packages == 0
        assert len(digest.new_packages) == 0
        assert len(digest.score_movers) == 0


# -- Writer tests --


class TestWriter:
    def test_generate_subject_with_movers(self):
        digest = WeeklyDigest(
            week_start=datetime(2026, 3, 1, tzinfo=timezone.utc),
            week_end=datetime(2026, 3, 7, tzinfo=timezone.utc),
        )
        from assay.newsletter.collector import NewPackage, ScoreChange
        digest.score_movers = [
            ScoreChange(
                package_id="test", name="TestPkg", category=None,
                old_af=60, new_af=75, af_delta=15,
                old_security=70, new_security=80, security_delta=10,
                old_reliability=65, new_reliability=70, reliability_delta=5,
            ),
        ]
        digest.newly_evaluated = []
        digest.new_packages = [
            NewPackage(package_id="a", name="A", category=None, package_type="api", stars=10),
        ]

        subject = generate_subject(digest)
        assert "Mar 07" in subject
        assert "TestPkg" in subject

    def test_generate_subject_empty_data(self):
        digest = WeeklyDigest(
            week_start=datetime(2026, 3, 1, tzinfo=timezone.utc),
            week_end=datetime(2026, 3, 7, tzinfo=timezone.utc),
        )
        subject = generate_subject(digest)
        assert "Assay Weekly" in subject

    def test_parse_newsletter_output(self):
        raw = "<html><body>Hello</body>\n</html>\n---PLAINTEXT---\nHello plain"
        html, text = parse_newsletter_output(raw)
        assert "<html>" in html
        assert "Hello plain" in text

    def test_parse_newsletter_output_no_separator(self):
        raw = "<html><body>Only HTML</body></html>"
        html, text = parse_newsletter_output(raw)
        assert html == text  # Falls back to same content

    def test_save_digest_for_session(self, seeded_db, tmp_path):
        from assay.newsletter.writer import save_digest_for_session
        import assay.newsletter.writer as writer_mod

        # Point to temp dir
        original = writer_mod.NEWSLETTER_DIR
        writer_mod.NEWSLETTER_DIR = tmp_path / "newsletters"

        try:
            digest = collect_weekly_data(seeded_db)
            prompt_path = save_digest_for_session(digest)

            assert prompt_path.exists()
            assert "TONE & STYLE" in prompt_path.read_text()

            data_files = list((tmp_path / "newsletters" / "pending").glob("digest-*.json"))
            assert len(data_files) == 1
        finally:
            writer_mod.NEWSLETTER_DIR = original


# -- Sender tests --


class TestSender:
    def test_get_active_subscribers(self, db, subscribers):
        active = get_active_subscribers(db)
        emails = [s.email for s in active]
        assert "active@example.com" in emails
        assert "pending@example.com" not in emails
        assert "gone@example.com" not in emails

    @patch("assay.newsletter.sender.send_newsletter")
    def test_send_newsletter_issue(self, mock_send, db, subscribers):
        mock_send.return_value = True
        issue = send_newsletter_issue(
            db, "Test Subject", "<html>test</html>", "test", dry_run=False,
        )
        assert issue.recipients_count == 1  # Only the confirmed subscriber
        assert issue.sent_at is not None
        mock_send.assert_called_once()

    @patch("assay.newsletter.sender.send_newsletter")
    def test_send_dry_run(self, mock_send, db, subscribers):
        issue = send_newsletter_issue(
            db, "Dry Run", "<html>dry</html>", "dry", dry_run=True,
        )
        assert issue.recipients_count == 1
        assert issue.sent_at is None
        mock_send.assert_not_called()

    def test_issue_saved_to_db(self, db, subscribers):
        with patch("assay.newsletter.sender.send_newsletter", return_value=True):
            send_newsletter_issue(db, "Saved", "<html>s</html>", "s")

        issues = db.query(NewsletterIssue).all()
        assert len(issues) == 1
        assert issues[0].subject == "Saved"
