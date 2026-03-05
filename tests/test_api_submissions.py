"""Tests for evaluation submission API."""

import os

import pytest


# Minimal valid evaluation payload
def _eval_payload(**overrides):
    base = {
        "id": "test-submit",
        "name": "Test Submit",
        "category": "developer-tools",
        "what_it_does": "A test package for submission",
        "interface": {"has_rest_api": True, "has_mcp_server": False},
        "auth": {"methods": ["api_key"]},
        "agent_readiness": {
            "mcp_server_quality": 60,
            "documentation_accuracy": 75,
            "error_message_quality": 70,
        },
        "af_score_components": {
            "mcp_score": 60,
            "api_doc_score": 75,
            "error_handling_score": 70,
            "auth_complexity_score": 80,
            "rate_limit_clarity_score": 65,
        },
        "security_score_components": {
            "tls_enforcement": 100,
            "auth_strength": 80,
            "scope_granularity": 60,
            "dependency_hygiene": 70,
            "secret_handling": 75,
        },
        "reliability_score_components": {
            "uptime_documented": 80,
            "version_stability": 75,
            "breaking_changes_history": 90,
            "error_recovery": 70,
        },
    }
    base.update(overrides)
    return base


@pytest.fixture(autouse=True)
def _set_api_key():
    """Set a test API key for submission auth."""
    os.environ["SUBMISSION_API_KEYS"] = "test-key-123,other-key-456"
    yield
    os.environ.pop("SUBMISSION_API_KEYS", None)


# --- Auth tests ---


def test_submit_requires_api_key(client):
    """POST without X-Api-Key returns 422 (missing header)."""
    resp = client.post("/v1/evaluations", json=_eval_payload())
    assert resp.status_code == 422


def test_submit_rejects_invalid_key(client):
    """POST with wrong key returns 401."""
    resp = client.post(
        "/v1/evaluations",
        json=_eval_payload(),
        headers={"X-Api-Key": "wrong-key"},
    )
    assert resp.status_code == 401


def test_submit_accepts_valid_key(client, make_category):
    """POST with valid key succeeds."""
    make_category(slug="developer-tools", name="Developer Tools")
    resp = client.post(
        "/v1/evaluations",
        json=_eval_payload(),
        headers={"X-Api-Key": "test-key-123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "pending_review"
    assert data["package_id"] == "test-submit"


def test_submit_accepts_second_key(client, make_category):
    """Both configured keys work."""
    make_category(slug="developer-tools", name="Developer Tools")
    resp = client.post(
        "/v1/evaluations",
        json=_eval_payload(),
        headers={"X-Api-Key": "other-key-456"},
    )
    assert resp.status_code == 200


# --- Submission flow tests ---


def test_submit_creates_pending_record(client, db, make_category):
    """Submission creates a pending_evaluations row."""
    from assay.models import PendingEvaluation

    make_category(slug="developer-tools", name="Developer Tools")
    client.post(
        "/v1/evaluations",
        json=_eval_payload(),
        headers={"X-Api-Key": "test-key-123"},
    )
    pending = db.query(PendingEvaluation).first()
    assert pending is not None
    assert pending.package_id == "test-submit"
    assert pending.status == "pending"
    assert "test-key" in pending.submitted_by


def test_list_pending_evaluations(client, db, make_category):
    """GET /v1/evaluations/pending returns pending items."""
    make_category(slug="developer-tools", name="Developer Tools")
    # Submit two
    for i in range(2):
        client.post(
            "/v1/evaluations",
            json=_eval_payload(id=f"pkg-{i}", name=f"Package {i}"),
            headers={"X-Api-Key": "test-key-123"},
        )

    resp = client.get(
        "/v1/evaluations/pending",
        headers={"X-Api-Key": "test-key-123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["evaluations"]) == 2


# --- Approve / Reject ---


def test_approve_evaluation(client, db, make_category):
    """Approving loads the evaluation into the main DB."""
    from assay.models import Package

    make_category(slug="developer-tools", name="Developer Tools")
    # Submit
    client.post(
        "/v1/evaluations",
        json=_eval_payload(),
        headers={"X-Api-Key": "test-key-123"},
    )
    # Get pending ID
    resp = client.get(
        "/v1/evaluations/pending",
        headers={"X-Api-Key": "test-key-123"},
    )
    eval_id = resp.json()["evaluations"][0]["id"]

    # Approve
    resp = client.post(
        f"/v1/evaluations/{eval_id}/approve",
        headers={"X-Api-Key": "test-key-123"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"

    # Package should now exist in main DB
    pkg = db.query(Package).filter_by(id="test-submit").first()
    assert pkg is not None
    assert pkg.af_score is not None
    assert pkg.security_score is not None
    assert pkg.reliability_score is not None


def test_reject_evaluation(client, db, make_category):
    """Rejecting marks the evaluation as rejected."""

    make_category(slug="developer-tools", name="Developer Tools")
    client.post(
        "/v1/evaluations",
        json=_eval_payload(),
        headers={"X-Api-Key": "test-key-123"},
    )
    resp = client.get(
        "/v1/evaluations/pending",
        headers={"X-Api-Key": "test-key-123"},
    )
    eval_id = resp.json()["evaluations"][0]["id"]

    resp = client.post(
        f"/v1/evaluations/{eval_id}/reject",
        headers={"X-Api-Key": "test-key-123"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"

    # Should not appear in pending list
    resp = client.get(
        "/v1/evaluations/pending",
        headers={"X-Api-Key": "test-key-123"},
    )
    assert resp.json()["total"] == 0


def test_approve_already_approved_fails(client, db, make_category):
    """Can't approve an already-approved evaluation."""
    make_category(slug="developer-tools", name="Developer Tools")
    client.post(
        "/v1/evaluations",
        json=_eval_payload(),
        headers={"X-Api-Key": "test-key-123"},
    )
    resp = client.get(
        "/v1/evaluations/pending",
        headers={"X-Api-Key": "test-key-123"},
    )
    eval_id = resp.json()["evaluations"][0]["id"]

    # Approve first time
    client.post(
        f"/v1/evaluations/{eval_id}/approve",
        headers={"X-Api-Key": "test-key-123"},
    )
    # Try again
    resp = client.post(
        f"/v1/evaluations/{eval_id}/approve",
        headers={"X-Api-Key": "test-key-123"},
    )
    assert resp.status_code == 400


def test_approve_nonexistent_fails(client):
    """Approving a nonexistent ID returns 404."""
    resp = client.post(
        "/v1/evaluations/9999/approve",
        headers={"X-Api-Key": "test-key-123"},
    )
    assert resp.status_code == 404


def test_submit_minimal_payload(client, make_category):
    """Minimal submission (just id + name) is accepted."""
    make_category(slug="other", name="Other")
    resp = client.post(
        "/v1/evaluations",
        json={"id": "minimal-pkg", "name": "Minimal"},
        headers={"X-Api-Key": "test-key-123"},
    )
    assert resp.status_code == 200
