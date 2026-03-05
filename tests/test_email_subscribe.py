"""Tests for email subscription feature."""

from assay.models import EmailSubscriber


class TestEmailSubscribe:
    def test_subscribe_success(self, client, db):
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

    def test_subscribe_duplicate(self, client, db):
        # First subscription
        client.post("/subscribe", data={"email": "dup@example.com"}, follow_redirects=False)
        # Second attempt
        resp = client.post(
            "/subscribe",
            data={"email": "dup@example.com"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert "subscribed=already" in resp.headers["location"]

        count = db.query(EmailSubscriber).filter_by(email="dup@example.com").count()
        assert count == 1

    def test_subscribe_invalid_email(self, client):
        resp = client.post(
            "/subscribe",
            data={"email": "not-an-email"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert "subscribed=invalid" in resp.headers["location"]

    def test_subscribe_normalizes_email(self, client, db):
        resp = client.post(
            "/subscribe",
            data={"email": "  Test@Example.COM  "},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        sub = db.query(EmailSubscriber).filter_by(email="test@example.com").first()
        assert sub is not None

    def test_homepage_shows_subscribe_form(self, client, sample_packages):
        resp = client.get("/")
        assert resp.status_code == 200
        assert 'action="/subscribe"' in resp.text
        assert "Stay in the loop" in resp.text

    def test_homepage_shows_success_message(self, client, sample_packages):
        resp = client.get("/?subscribed=ok")
        assert resp.status_code == 200
        assert "You're subscribed" in resp.text
