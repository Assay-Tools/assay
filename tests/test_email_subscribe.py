"""Tests for email subscription feature with double opt-in."""

from unittest.mock import patch

from assay.models import EmailSubscriber


class TestEmailSubscribe:
    def test_subscribe_success(self, client, db):
        with patch("assay.notifications.email.send_subscription_confirmation", return_value=True):
            resp = client.post(
                "/subscribe",
                data={"email": "test@example.com"},
                follow_redirects=False,
            )
        assert resp.status_code == 303
        assert "subscribed=ok" in resp.headers["location"]

        sub = db.query(EmailSubscriber).filter_by(email="test@example.com").first()
        assert sub is not None
        assert sub.confirmed is False
        assert sub.confirmation_token is not None
        assert sub.unsubscribe_token is not None

    def test_subscribe_duplicate_unconfirmed_resends(self, client, db):
        """Second signup for unconfirmed email resends confirmation."""
        with patch("assay.notifications.email.send_subscription_confirmation", return_value=True) as mock_send:
            client.post("/subscribe", data={"email": "dup@example.com"}, follow_redirects=False)
            resp = client.post(
                "/subscribe",
                data={"email": "dup@example.com"},
                follow_redirects=False,
            )
        assert resp.status_code == 303
        assert "subscribed=ok" in resp.headers["location"]
        assert mock_send.call_count == 2

        count = db.query(EmailSubscriber).filter_by(email="dup@example.com").count()
        assert count == 1

    def test_subscribe_duplicate_confirmed_shows_already(self, client, db):
        """Confirmed subscriber gets 'already' message."""
        with patch("assay.notifications.email.send_subscription_confirmation", return_value=True):
            client.post("/subscribe", data={"email": "confirmed@example.com"}, follow_redirects=False)

        sub = db.query(EmailSubscriber).filter_by(email="confirmed@example.com").first()
        sub.confirmed = True
        db.commit()

        with patch("assay.notifications.email.send_subscription_confirmation", return_value=True):
            resp = client.post(
                "/subscribe",
                data={"email": "confirmed@example.com"},
                follow_redirects=False,
            )
        assert resp.status_code == 303
        assert "subscribed=already" in resp.headers["location"]

    def test_subscribe_invalid_email(self, client):
        resp = client.post(
            "/subscribe",
            data={"email": "not-an-email"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert "subscribed=invalid" in resp.headers["location"]

    def test_subscribe_normalizes_email(self, client, db):
        with patch("assay.notifications.email.send_subscription_confirmation", return_value=True):
            resp = client.post(
                "/subscribe",
                data={"email": "  Test@Example.COM  "},
                follow_redirects=False,
            )
        assert resp.status_code == 303
        sub = db.query(EmailSubscriber).filter_by(email="test@example.com").first()
        assert sub is not None

    def test_confirm_subscription(self, client, db):
        """Clicking confirmation link sets confirmed=True."""
        with patch("assay.notifications.email.send_subscription_confirmation", return_value=True):
            client.post("/subscribe", data={"email": "confirm@example.com"}, follow_redirects=False)

        sub = db.query(EmailSubscriber).filter_by(email="confirm@example.com").first()
        assert sub.confirmed is False
        token = sub.confirmation_token

        resp = client.get(f"/confirm?token={token}", follow_redirects=False)
        assert resp.status_code == 303
        assert "subscribed=confirmed" in resp.headers["location"]

        db.refresh(sub)
        assert sub.confirmed is True
        assert sub.confirmed_at is not None

    def test_confirm_invalid_token(self, client):
        resp = client.get("/confirm?token=bogus", follow_redirects=False)
        assert resp.status_code == 303
        assert "subscribed=invalid_token" in resp.headers["location"]

    def test_unsubscribe(self, client, db):
        """Unsubscribe link sets unsubscribed_at."""
        with patch("assay.notifications.email.send_subscription_confirmation", return_value=True):
            client.post("/subscribe", data={"email": "unsub@example.com"}, follow_redirects=False)

        sub = db.query(EmailSubscriber).filter_by(email="unsub@example.com").first()
        sub.confirmed = True
        db.commit()
        token = sub.unsubscribe_token

        resp = client.get(f"/unsubscribe?token={token}", follow_redirects=False)
        assert resp.status_code == 303
        assert "unsubscribed=ok" in resp.headers["location"]

        db.refresh(sub)
        assert sub.unsubscribed_at is not None

    def test_unsubscribe_invalid_token(self, client):
        resp = client.get("/unsubscribe?token=bogus", follow_redirects=False)
        assert resp.status_code == 303
        assert "subscribed=invalid_token" in resp.headers["location"]

    def test_resubscribe_after_unsubscribe(self, client, db):
        """Unsubscribed user can re-subscribe and gets new confirmation."""
        with patch("assay.notifications.email.send_subscription_confirmation", return_value=True) as mock_send:
            client.post("/subscribe", data={"email": "resub@example.com"}, follow_redirects=False)

            sub = db.query(EmailSubscriber).filter_by(email="resub@example.com").first()
            sub.confirmed = True
            from datetime import datetime, timezone
            sub.unsubscribed_at = datetime.now(timezone.utc)
            db.commit()

            resp = client.post(
                "/subscribe",
                data={"email": "resub@example.com"},
                follow_redirects=False,
            )

        assert resp.status_code == 303
        assert "subscribed=ok" in resp.headers["location"]

        db.refresh(sub)
        assert sub.unsubscribed_at is None
        assert sub.confirmed is False
        assert mock_send.call_count == 2

    def test_homepage_shows_subscribe_form(self, client, sample_packages):
        resp = client.get("/")
        assert resp.status_code == 200
        assert 'action="/subscribe"' in resp.text
        assert "Stay in the loop" in resp.text

    def test_homepage_shows_confirmation_message(self, client, sample_packages):
        resp = client.get("/?subscribed=ok")
        assert resp.status_code == 200
        assert "Check your inbox" in resp.text

    def test_homepage_shows_confirmed_message(self, client, sample_packages):
        resp = client.get("/?subscribed=confirmed")
        assert resp.status_code == 200
        assert "confirmed" in resp.text.lower()
