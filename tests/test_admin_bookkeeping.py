"""Tests for admin bookkeeping/transaction endpoints."""

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _patch_admin_settings():
    """Patch admin API key for all tests."""
    with patch("assay.api.admin_routes.settings") as mock:
        mock.admin_api_keys = "test-admin-key"
        yield mock


ADMIN_HEADERS = {"X-Api-Key": "test-admin-key"}


class TestTransactionExport:
    def test_list_transactions_json(self, client, db):
        from assay.models import Order

        order = Order(
            package_id="top-api",
            order_type="report",
            amount_cents=9900,
            status="paid",
            customer_email="buyer@example.com",
        )
        db.add(order)
        db.commit()

        resp = client.get("/admin/transactions", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["total_orders"] == 1
        assert data["summary"]["paid_orders"] == 1
        assert data["summary"]["total_revenue_cents"] == 9900
        assert len(data["transactions"]) == 1
        assert data["transactions"][0]["customer_email"] == "buyer@example.com"

    def test_list_transactions_csv(self, client, db):
        from assay.models import Order

        order = Order(
            package_id="top-api",
            order_type="report",
            amount_cents=9900,
            status="paid",
        )
        db.add(order)
        db.commit()

        resp = client.get(
            "/admin/transactions?format=csv",
            headers=ADMIN_HEADERS,
        )
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "top-api" in resp.text

    def test_list_transactions_filter_status(self, client, db):
        from assay.models import Order

        db.add(Order(package_id="a", order_type="report", amount_cents=9900, status="paid"))
        db.add(Order(package_id="b", order_type="report", amount_cents=9900, status="pending"))
        db.commit()

        resp = client.get("/admin/transactions?status=paid", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["total_orders"] == 1

    def test_transactions_require_auth(self, client):
        resp = client.get("/admin/transactions")
        assert resp.status_code == 403

    def test_transactions_wrong_key(self, client):
        resp = client.get(
            "/admin/transactions",
            headers={"X-Api-Key": "wrong-key"},
        )
        assert resp.status_code == 403


class TestRevenueSummary:
    def test_revenue_summary(self, client, db):
        from datetime import datetime, timezone  # noqa: I001

        from assay.models import Order

        o1 = Order(
            package_id="a",
            order_type="report",
            amount_cents=9900,
            status="paid",
        )
        o1.paid_at = datetime(2026, 3, 1, tzinfo=timezone.utc)
        o2 = Order(
            package_id="b",
            order_type="monitoring_subscription",
            amount_cents=300,
            status="paid",
        )
        o2.paid_at = datetime(2026, 3, 2, tzinfo=timezone.utc)
        db.add_all([o1, o2])
        db.commit()

        resp = client.get("/admin/revenue", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_revenue_cents"] == 10200
        assert data["paid_orders"] == 2
        assert "report" in data["by_type"]
        assert "monitoring_subscription" in data["by_type"]
        assert "2026-03" in data["by_month"]

    def test_revenue_empty(self, client):
        resp = client.get("/admin/revenue", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_revenue_cents"] == 0
        assert data["paid_orders"] == 0

    def test_revenue_requires_auth(self, client):
        resp = client.get("/admin/revenue")
        assert resp.status_code == 403
