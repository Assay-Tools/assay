"""Stripe payment routes for report purchases and monitoring subscriptions."""

import logging
from datetime import datetime, timezone
from pathlib import Path

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from starlette.responses import FileResponse, Response

from assay.config import settings
from assay.database import get_db
from assay.models import Order, Package

from .rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["payments"])

# Project root for resolving report file paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


def _ensure_stripe():
    """Set Stripe API key and verify it's configured."""
    if not settings.stripe_secret_key:
        raise HTTPException(
            status_code=503,
            detail="Payment system is not configured",
        )
    stripe.api_key = settings.stripe_secret_key


# --- Checkout session creation ---


@router.post("/v1/checkout/report")
@limiter.limit("20/day")
def create_report_checkout(
    request: Request,
    response: Response,
    package_id: str,
    db: Session = Depends(get_db),
):
    """Create a Stripe Checkout session for a $99 package report."""
    _ensure_stripe()

    if not settings.stripe_price_report:
        raise HTTPException(
            status_code=503,
            detail="Report pricing not configured",
        )

    pkg = db.query(Package).filter(Package.id == package_id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail=f"Package '{package_id}' not found")

    if pkg.af_score is None:
        raise HTTPException(
            status_code=400,
            detail="Package has not been evaluated yet — no report available",
        )

    # Create order record
    order = Order(
        package_id=package_id,
        order_type="report",
        amount_cents=9900,
    )
    db.add(order)
    db.commit()

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[{
                "price": settings.stripe_price_report,
                "quantity": 1,
            }],
            metadata={
                "order_id": str(order.id),
                "package_id": package_id,
                "order_type": "report",
            },
            success_url=f"{settings.app_url}/orders/{order.id}/success",
            cancel_url=f"{settings.app_url}/packages/{package_id}",
        )
    except stripe.StripeError as e:
        logger.error("Stripe checkout creation failed: %s", e)
        raise HTTPException(status_code=502, detail="Payment service error")

    order.stripe_session_id = session.id
    db.commit()

    return {
        "checkout_url": session.url,
        "order_id": order.id,
        "session_id": session.id,
    }


@router.post("/v1/checkout/monitoring")
@limiter.limit("20/day")
def create_monitoring_checkout(
    request: Request,
    response: Response,
    package_id: str,
    db: Session = Depends(get_db),
):
    """Create a Stripe Checkout session for $3/mo package monitoring."""
    _ensure_stripe()

    if not settings.stripe_price_monitoring:
        raise HTTPException(
            status_code=503,
            detail="Monitoring pricing not configured",
        )

    pkg = db.query(Package).filter(Package.id == package_id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail=f"Package '{package_id}' not found")

    order = Order(
        package_id=package_id,
        order_type="monitoring_subscription",
        amount_cents=300,
    )
    db.add(order)
    db.commit()

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{
                "price": settings.stripe_price_monitoring,
                "quantity": 1,
            }],
            metadata={
                "order_id": str(order.id),
                "package_id": package_id,
                "order_type": "monitoring_subscription",
            },
            success_url=f"{settings.app_url}/orders/{order.id}/success",
            cancel_url=f"{settings.app_url}/packages/{package_id}",
        )
    except stripe.StripeError as e:
        logger.error("Stripe checkout creation failed: %s", e)
        raise HTTPException(status_code=502, detail="Payment service error")

    order.stripe_session_id = session.id
    db.commit()

    return {
        "checkout_url": session.url,
        "order_id": order.id,
        "session_id": session.id,
    }


# --- Webhook handler ---


@router.post("/v1/webhooks/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Stripe webhook events."""
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Not configured")

    stripe.api_key = settings.stripe_secret_key
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing stripe-signature")

    try:
        if settings.stripe_webhook_secret:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.stripe_webhook_secret,
            )
        else:
            # Dev mode — no signature verification
            import json
            event = stripe.Event.construct_from(
                json.loads(payload), stripe.api_key,
            )
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.error("Webhook parse error: %s", e)
        raise HTTPException(status_code=400, detail="Invalid payload")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(data, db)
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_cancelled(data, db)
    elif event_type == "customer.subscription.updated":
        _handle_subscription_updated(data, db)
    else:
        logger.debug("Unhandled Stripe event: %s", event_type)

    return {"status": "ok"}


def _handle_checkout_completed(session_data: dict, db: Session):
    """Process a completed checkout session."""
    session_id = session_data.get("id")
    metadata = session_data.get("metadata", {})
    order_id = metadata.get("order_id")

    if not order_id:
        logger.warning("Checkout completed without order_id in metadata: %s", session_id)
        return

    order = db.query(Order).filter(Order.id == int(order_id)).first()
    if not order:
        logger.warning("Order not found for checkout: %s", order_id)
        return

    order.status = "paid"
    order.paid_at = datetime.now(timezone.utc)
    order.stripe_payment_intent = session_data.get("payment_intent")
    order.stripe_customer_id = session_data.get("customer")
    order.customer_email = session_data.get("customer_details", {}).get("email")
    order.stripe_subscription_id = session_data.get("subscription")

    db.commit()
    logger.info(
        "Order %d paid: %s for %s",
        order.id, order.order_type, order.package_id,
    )

    # Generate report for report orders
    if order.order_type == "report":
        try:
            from assay.reports.delivery import generate_report_for_order
            generate_report_for_order(order, db)
        except Exception:
            logger.exception("Report generation failed for order %d", order.id)


def _handle_subscription_cancelled(sub_data: dict, db: Session):
    """Mark subscription orders as cancelled."""
    sub_id = sub_data.get("id")
    orders = db.query(Order).filter(
        Order.stripe_subscription_id == sub_id,
        Order.status == "paid",
    ).all()
    for order in orders:
        order.status = "cancelled"
    db.commit()
    logger.info("Subscription %s cancelled (%d orders)", sub_id, len(orders))


def _handle_subscription_updated(sub_data: dict, db: Session):
    """Log subscription updates."""
    sub_id = sub_data.get("id")
    status = sub_data.get("status")
    logger.info("Subscription %s updated: status=%s", sub_id, status)


# --- Order status ---


@router.get("/v1/orders/{order_id}")
@limiter.limit("100/day")
def get_order_status(
    request: Request,
    response: Response,
    order_id: int,
    db: Session = Depends(get_db),
):
    """Check the status of an order."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return {
        "id": order.id,
        "package_id": order.package_id,
        "order_type": order.order_type,
        "status": order.status,
        "amount_cents": order.amount_cents,
        "currency": order.currency,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "paid_at": order.paid_at.isoformat() if order.paid_at else None,
        "report_path": order.report_path,
    }


# --- Report download ---


@router.get("/v1/orders/{order_id}/download")
@limiter.limit("50/day")
def download_report(
    request: Request,
    response: Response,
    order_id: int,
    db: Session = Depends(get_db),
):
    """Download the generated report for a paid order."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != "paid":
        raise HTTPException(status_code=402, detail="Order has not been paid")

    if not order.report_path:
        raise HTTPException(status_code=404, detail="Report not yet generated")

    report_file = PROJECT_ROOT / order.report_path

    if not report_file.exists():
        raise HTTPException(status_code=404, detail="Report file not found")

    return FileResponse(
        path=str(report_file),
        filename=f"assay-report-{order.package_id}.md",
        media_type="text/markdown",
    )
