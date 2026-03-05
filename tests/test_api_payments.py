"""Tests for Stripe payment endpoints."""

import json
from unittest.mock import MagicMock, patch

import pytest

# Patch settings at module level so it's picked up by all tests
_STRIPE_SETTINGS = {
    "stripe_secret_key": "sk_test_fake",
    "stripe_webhook_secret": "whsec_test_fake",
    "stripe_price_report": "price_report_test",
    "stripe_price_monitoring": "price_monitoring_test",
    "app_url": "https://test.assay.tools",
}


@pytest.fixture(autouse=True)
def _patch_settings():
    """Patch payment settings for all tests."""
    with patch("assay.api.payments.settings") as mock_settings:
        for k, v in _STRIPE_SETTINGS.items():
            setattr(mock_settings, k, v)
        yield mock_settings


class TestReportCheckout:
    @patch("assay.api.payments.stripe")
    def test_create_checkout(self, mock_stripe, client, sample_packages):
        mock_session = MagicMock()
        mock_session.id = "cs_test_123"
        mock_session.url = "https://checkout.stripe.com/test"
        mock_stripe.checkout.Session.create.return_value = mock_session

        resp = client.post("/v1/checkout/report?package_id=top-api")
        assert resp.status_code == 200
        data = resp.json()
        assert data["checkout_url"] == "https://checkout.stripe.com/test"
        assert data["session_id"] == "cs_test_123"
        assert "order_id" in data

    def test_checkout_package_not_found(self, client):
        resp = client.post("/v1/checkout/report?package_id=nonexistent")
        assert resp.status_code == 404

    def test_checkout_unevaluated_package(self, client, sample_packages):
        resp = client.post("/v1/checkout/report?package_id=new-pkg")
        assert resp.status_code == 400
        assert "not been evaluated" in resp.json()["detail"]


class TestMonitoringCheckout:
    @patch("assay.api.payments.stripe")
    def test_create_monitoring_checkout(
        self, mock_stripe, client, sample_packages,
    ):
        mock_session = MagicMock()
        mock_session.id = "cs_test_456"
        mock_session.url = "https://checkout.stripe.com/mon"
        mock_stripe.checkout.Session.create.return_value = mock_session

        resp = client.post("/v1/checkout/monitoring?package_id=top-api")
        assert resp.status_code == 200
        data = resp.json()
        assert data["checkout_url"] == "https://checkout.stripe.com/mon"


class TestWebhook:
    @patch("assay.api.payments.stripe")
    @patch("assay.reports.delivery.generate_report_for_order")
    def test_checkout_completed_webhook(
        self, mock_generate, mock_stripe, client, sample_packages, db,
    ):
        from assay.models import Order

        mock_generate.return_value = "reports/output/packages/top-api-order-1.md"

        order = Order(
            package_id="top-api",
            order_type="report",
            amount_cents=9900,
            stripe_session_id="cs_test_789",
        )
        db.add(order)
        db.commit()
        order_id = order.id

        event_data = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_789",
                    "payment_intent": "pi_test_abc",
                    "customer": "cus_test_xyz",
                    "subscription": None,
                    "customer_details": {"email": "buyer@example.com"},
                    "metadata": {
                        "order_id": str(order_id),
                        "package_id": "top-api",
                        "order_type": "report",
                    },
                },
            },
        }

        mock_stripe.Webhook.construct_event.return_value = event_data

        resp = client.post(
            "/v1/webhooks/stripe",
            content=json.dumps(event_data),
            headers={
                "Content-Type": "application/json",
                "stripe-signature": "test_sig",
            },
        )
        assert resp.status_code == 200

        db.expire_all()
        updated_order = db.query(Order).filter(Order.id == order_id).first()
        assert updated_order.status == "paid"
        assert updated_order.customer_email == "buyer@example.com"
        mock_generate.assert_called_once()

    def test_webhook_rejects_missing_secret(self, client, _patch_settings):
        _patch_settings.stripe_webhook_secret = ""
        resp = client.post(
            "/v1/webhooks/stripe",
            content="{}",
            headers={
                "Content-Type": "application/json",
                "stripe-signature": "test_sig",
            },
        )
        assert resp.status_code == 503

    def test_webhook_missing_signature(self, client):
        resp = client.post(
            "/v1/webhooks/stripe",
            content="{}",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 400


class TestOrderStatus:
    def test_get_order(self, client, sample_packages, db):
        from assay.models import Order

        order = Order(
            package_id="top-api",
            order_type="report",
            amount_cents=9900,
            status="paid",
        )
        db.add(order)
        db.commit()

        resp = client.get(f"/v1/orders/{order.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["package_id"] == "top-api"
        assert data["status"] == "paid"
        assert data["amount_cents"] == 9900

    def test_get_nonexistent_order(self, client):
        resp = client.get("/v1/orders/9999")
        assert resp.status_code == 404


class TestReportDownload:
    def test_download_paid_report(self, client, db, tmp_path):
        from assay.models import Order

        # Create a report file
        report_file = tmp_path / "reports" / "output" / "packages" / "top-api-order-1.md"
        report_file.parent.mkdir(parents=True)
        report_file.write_text("# Test Report\nContent here.")

        order = Order(
            package_id="top-api",
            order_type="report",
            amount_cents=9900,
            status="paid",
            report_path="reports/output/packages/top-api-order-1.md",
        )
        db.add(order)
        db.commit()

        with patch("assay.api.payments.PROJECT_ROOT", tmp_path):
            resp = client.get(f"/v1/orders/{order.id}/download")
            assert resp.status_code == 200

    def test_download_unpaid_order(self, client, db):
        from assay.models import Order

        order = Order(
            package_id="top-api",
            order_type="report",
            amount_cents=9900,
            status="pending",
        )
        db.add(order)
        db.commit()

        resp = client.get(f"/v1/orders/{order.id}/download")
        assert resp.status_code == 402

    def test_download_no_report(self, client, db):
        from assay.models import Order

        order = Order(
            package_id="top-api",
            order_type="report",
            amount_cents=9900,
            status="paid",
            report_path=None,
        )
        db.add(order)
        db.commit()

        resp = client.get(f"/v1/orders/{order.id}/download")
        assert resp.status_code == 404

    def test_download_nonexistent_order(self, client):
        resp = client.get("/v1/orders/9999/download")
        assert resp.status_code == 404


class TestOrderSuccessPage:
    def test_success_page_paid(self, client, sample_packages, db):
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

        resp = client.get(f"/orders/{order.id}/success")
        assert resp.status_code == 200
        assert "Payment Successful" in resp.text
        assert "buyer@example.com" in resp.text

    def test_success_page_pending(self, client, db):
        from assay.models import Order

        order = Order(
            package_id="top-api",
            order_type="report",
            amount_cents=9900,
            status="pending",
        )
        db.add(order)
        db.commit()

        resp = client.get(f"/orders/{order.id}/success")
        assert resp.status_code == 200
        assert "Payment Processing" in resp.text

    def test_success_page_not_found(self, client):
        resp = client.get("/orders/9999/success")
        assert resp.status_code == 200
        assert "Order Not Found" in resp.text


class TestNotConfigured:
    def test_checkout_without_stripe_key(self, client, sample_packages):
        with patch("assay.api.payments.settings") as mock:
            mock.stripe_secret_key = ""
            resp = client.post("/v1/checkout/report?package_id=top-api")
            assert resp.status_code == 503
