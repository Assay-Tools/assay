"""Tests for security hardening — CORS, headers, input sanitization, auth separation."""


class TestSecurityHeaders:
    def test_x_content_type_options(self, client):
        resp = client.get("/")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, client):
        resp = client.get("/")
        assert resp.headers.get("X-Frame-Options") == "DENY"

    def test_hsts(self, client):
        resp = client.get("/")
        assert "max-age=" in resp.headers.get("Strict-Transport-Security", "")

    def test_referrer_policy(self, client):
        resp = client.get("/")
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


class TestCORS:
    def test_cors_no_credentials(self, client):
        resp = client.options(
            "/v1/packages",
            headers={"Origin": "https://example.com", "Access-Control-Request-Method": "GET"},
        )
        # With allow_credentials=False and allow_origins=["*"],
        # credentials header should not be present or should be false
        cred = resp.headers.get("Access-Control-Allow-Credentials")
        assert cred is None or cred == "false"


class TestSortFieldWhitelist:
    def test_valid_sort_field(self, client, make_package):
        make_package(id="pkg-a", name="A")
        resp = client.get("/v1/packages?sort=af_score:desc")
        assert resp.status_code == 200

    def test_invalid_sort_field_rejected(self, client):
        resp = client.get("/v1/packages?sort=password:desc")
        assert resp.status_code == 400
        assert "Invalid sort field" in resp.json()["detail"]

    def test_sort_whitelist_shown_in_error(self, client):
        resp = client.get("/v1/packages?sort=secret:asc")
        assert resp.status_code == 400
        assert "Allowed:" in resp.json()["detail"]


class TestAdminKeySeparation:
    def test_submitter_cannot_approve(self, client, db, monkeypatch):
        """Submitter key should not work for admin endpoints when admin keys are set."""
        monkeypatch.setenv("SUBMISSION_API_KEYS", "submit-key-123")
        monkeypatch.setenv("ADMIN_API_KEYS", "admin-key-456")

        resp = client.get(
            "/v1/evaluations/pending",
            headers={"X-Api-Key": "submit-key-123"},
        )
        assert resp.status_code == 403

    def test_admin_key_works_for_admin_endpoints(self, client, db, monkeypatch):
        monkeypatch.setenv("SUBMISSION_API_KEYS", "submit-key-123")
        monkeypatch.setenv("ADMIN_API_KEYS", "admin-key-456")

        resp = client.get(
            "/v1/evaluations/pending",
            headers={"X-Api-Key": "admin-key-456"},
        )
        assert resp.status_code == 200

    def test_admin_rejects_submission_keys(self, client, db, monkeypatch):
        """When no ADMIN_API_KEYS set, submission keys should NOT grant admin access."""
        monkeypatch.setenv("SUBMISSION_API_KEYS", "shared-key-789")
        monkeypatch.delenv("ADMIN_API_KEYS", raising=False)
        from assay.config import settings
        monkeypatch.setattr(settings, "admin_api_keys", "")

        resp = client.get(
            "/v1/evaluations/pending",
            headers={"X-Api-Key": "shared-key-789"},
        )
        assert resp.status_code == 403
