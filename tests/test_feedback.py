"""Tests for feedback submission feature."""

from assay.models import Feedback


class TestFeedbackPage:
    def test_feedback_page_renders(self, client):
        resp = client.get("/feedback")
        assert resp.status_code == 200
        assert "Share Feedback" in resp.text
        assert 'action="/feedback"' in resp.text

    def test_submit_feedback(self, client, db):
        resp = client.post(
            "/feedback",
            data={
                "feedback_type": "scoring",
                "message": "The score for package X seems too low.",
                "email": "test@example.com",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert "submitted=ok" in resp.headers["location"]

        fb = db.query(Feedback).first()
        assert fb is not None
        assert fb.feedback_type == "scoring"
        assert "package X" in fb.message
        assert fb.email == "test@example.com"

    def test_submit_feedback_no_email(self, client, db):
        resp = client.post(
            "/feedback",
            data={"feedback_type": "general", "message": "Great tool!", "email": ""},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert "submitted=ok" in resp.headers["location"]

        fb = db.query(Feedback).first()
        assert fb.email is None

    def test_submit_feedback_empty_message(self, client):
        resp = client.post(
            "/feedback",
            data={"feedback_type": "bug", "message": "   ", "email": ""},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert "submitted=invalid" in resp.headers["location"]

    def test_submit_feedback_invalid_type_defaults_to_general(self, client, db):
        resp = client.post(
            "/feedback",
            data={"feedback_type": "hacking", "message": "Some feedback", "email": ""},
            follow_redirects=False,
        )
        assert resp.status_code == 303

        fb = db.query(Feedback).first()
        assert fb.feedback_type == "general"

    def test_success_message_shown(self, client):
        resp = client.get("/feedback?submitted=ok")
        assert resp.status_code == 200
        assert "Thank you" in resp.text
