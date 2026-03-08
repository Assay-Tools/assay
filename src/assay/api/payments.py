"""Stripe payment routes for report purchases and monitoring subscriptions."""

import logging
import threading
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from starlette.responses import FileResponse, Response

from assay.config import settings
from assay.database import SessionLocal, get_db
from assay.models import Order, Package
from assay.reports.delivery import PROJECT_ROOT

from .rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["payments"])


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

    # Create order, flush to get ID, then create Stripe session.
    # Only commit if Stripe succeeds — rollback on failure.
    order = Order(
        package_id=package_id,
        order_type="report",
        amount_cents=9900,
    )
    db.add(order)
    db.flush()  # Assigns order.id without committing

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[{
                "price": settings.stripe_price_report,
                "quantity": 1,
            }],
            payment_intent_data={
                "description": f"Assay Evaluation Report — {pkg.name}",
            },
            metadata={
                "order_id": str(order.id),
                "package_id": package_id,
                "order_type": "report",
            },
            success_url=f"{settings.app_url}/orders/{order.access_token}/success",
            cancel_url=f"{settings.app_url}/packages/{package_id}",
        )
    except stripe.StripeError as e:
        db.rollback()
        logger.error("Stripe checkout creation failed: %s", e)
        raise HTTPException(status_code=502, detail="Payment service error")

    order.stripe_session_id = session.id
    db.commit()

    return {
        "checkout_url": session.url,
        "order_id": order.id,
        "session_id": session.id,
    }


@router.post("/v1/checkout/brief")
@limiter.limit("50/day")
def create_brief_checkout(
    request: Request,
    response: Response,
    package_id: str,
    db: Session = Depends(get_db),
):
    """Create a Stripe Checkout session for a $3 Package Brief."""
    _ensure_stripe()

    if not settings.stripe_price_brief:
        raise HTTPException(status_code=503, detail="Brief pricing not configured")

    pkg = db.query(Package).filter(Package.id == package_id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail=f"Package '{package_id}' not found")

    if pkg.af_score is None:
        raise HTTPException(status_code=400, detail="Package has not been evaluated yet")

    order = Order(
        package_id=package_id,
        order_type="brief",
        amount_cents=300,
    )
    db.add(order)
    db.flush()

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[{"price": settings.stripe_price_brief, "quantity": 1}],
            payment_intent_data={
                "description": f"Assay Package Brief — {pkg.name}",
            },
            metadata={
                "order_id": str(order.id),
                "package_id": package_id,
                "order_type": "brief",
            },
            success_url=f"{settings.app_url}/orders/{order.access_token}/success",
            cancel_url=f"{settings.app_url}/packages/{package_id}",
        )
    except stripe.StripeError as e:
        db.rollback()
        logger.error("Stripe checkout creation failed: %s", e)
        raise HTTPException(status_code=502, detail="Payment service error")

    order.stripe_session_id = session.id
    db.commit()

    return {
        "checkout_url": session.url,
        "order_id": order.id,
        "session_id": session.id,
    }


@router.post("/v1/checkout/support")
@limiter.limit("20/day")
def create_support_checkout(
    request: Request,
    response: Response,
):
    """Create a Stripe Checkout session for Support the Mission (custom amount)."""
    _ensure_stripe()

    if not settings.stripe_price_support:
        raise HTTPException(status_code=503, detail="Support pricing not configured")

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[{"price": settings.stripe_price_support, "quantity": 1}],
            payment_intent_data={
                "description": "Support Assay's Mission",
            },
            metadata={
                "order_type": "support",
            },
            success_url=f"{settings.app_url}/support/thanks",
            cancel_url=f"{settings.app_url}",
        )
    except stripe.StripeError as e:
        logger.error("Stripe checkout creation failed: %s", e)
        raise HTTPException(status_code=502, detail="Payment service error")

    return {
        "checkout_url": session.url,
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

    # Create order, flush to get ID, then create Stripe session.
    # Only commit if Stripe succeeds — rollback on failure.
    order = Order(
        package_id=package_id,
        order_type="monitoring_subscription",
        amount_cents=300,
    )
    db.add(order)
    db.flush()

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
            success_url=f"{settings.app_url}/orders/{order.access_token}/success",
            cancel_url=f"{settings.app_url}/packages/{package_id}",
        )
    except stripe.StripeError as e:
        db.rollback()
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
@limiter.limit("120/minute")
async def stripe_webhook(request: Request, response: Response, db: Session = Depends(get_db)):
    """Handle Stripe webhook events."""
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Not configured")

    if not settings.stripe_webhook_secret:
        logger.error("STRIPE_WEBHOOK_SECRET not set — refusing webhook")
        raise HTTPException(
            status_code=503,
            detail="Webhook signature verification not configured",
        )

    stripe.api_key = settings.stripe_secret_key
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret,
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

    # Send confirmation email immediately (non-blocking)
    if order.customer_email:
        _send_confirmation_async(
            order.id, order.customer_email, order.package_id, order.order_type,
            order.access_token,
        )
        # Sync to CRM (fire-and-forget)
        _crm_record_purchase_async(
            order.customer_email, order.order_type, order.package_id, order.id,
        )

    # Generate report in background thread so webhook returns fast
    if order.order_type in ("report", "brief"):
        _generate_report_async(order.id)


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


# --- Background tasks ---


def _generate_report_async(order_id: int):
    """Run report generation in a background thread with its own DB session."""
    def _worker():
        db = SessionLocal()
        try:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                logger.error("Background report gen: order %d not found", order_id)
                return
            if order.report_path:
                logger.info("Report already generated for order %d, skipping", order_id)
                return
            from assay.reports.delivery import generate_report_for_order
            report_path = generate_report_for_order(order, db)
            if report_path and order.customer_email:
                from assay.notifications.email import send_report_ready
                send_report_ready(order.customer_email, order.id, order.package_id, report_path, order.access_token)
        except Exception:
            logger.exception("Background report generation failed for order %d", order_id)
        finally:
            db.close()

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


def _crm_record_purchase_async(
    email: str, order_type: str, package_id: str, order_id: int,
):
    """Record purchase in CRM in background thread."""
    def _worker():
        try:
            from assay.integrations.crm import on_purchase
            on_purchase(email, order_type, package_id, order_id)
        except Exception:
            logger.debug("CRM purchase sync skipped", exc_info=True)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


def _send_confirmation_async(
    order_id: int, email: str, package_id: str, order_type: str,
    access_token: str = "",
):
    """Send order confirmation email in background thread."""
    def _worker():
        try:
            from assay.notifications.email import send_order_confirmation
            send_order_confirmation(email, order_id, package_id, order_type, access_token)
        except Exception:
            logger.exception("Failed to send confirmation email for order %d", order_id)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


# --- Order status ---


@router.get("/v1/orders/{token}")
@limiter.limit("100/day")
def get_order_status(
    request: Request,
    response: Response,
    token: str,
    db: Session = Depends(get_db),
):
    """Check the status of an order (by access token)."""
    order = db.query(Order).filter(Order.access_token == token).first()
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
        "has_report": bool(order.report_path),
    }


# --- Report download ---


@router.get("/v1/orders/{token}/download")
@limiter.limit("50/day")
def download_report(
    request: Request,
    response: Response,
    token: str,
    db: Session = Depends(get_db),
):
    """Download the generated report for a paid order (by access token)."""
    order = db.query(Order).filter(Order.access_token == token).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != "paid":
        raise HTTPException(status_code=402, detail="Order has not been paid")

    if not order.report_path:
        raise HTTPException(status_code=404, detail="Report not yet generated")

    # Check if PDF is requested (via query param or Accept header)
    fmt = request.query_params.get("format", "pdf")
    suffix = "brief" if order.order_type == "brief" else "report"
    report_type = order.order_type

    # Try local file first — with path traversal protection
    report_file = (PROJECT_ROOT / order.report_path).resolve()
    if not report_file.is_relative_to(PROJECT_ROOT.resolve()):
        raise HTTPException(status_code=400, detail="Invalid report path")
    pdf_file = report_file.with_suffix(".pdf") if report_file.suffix == ".md" else None

    if fmt == "md" and report_file.exists():
        return FileResponse(
            path=str(report_file),
            filename=f"assay-{suffix}-{order.package_id}.md",
            media_type="text/markdown",
        )
    if fmt == "pdf" and pdf_file and pdf_file.exists():
        return FileResponse(
            path=str(pdf_file),
            filename=f"assay-{suffix}-{order.package_id}.pdf",
            media_type="application/pdf",
        )

    # Fall back to GCS if local file not available
    try:
        from assay.reports.storage import download_report as gcs_download
        content = gcs_download(order.package_id, report_type, fmt)
        if content:
            media = "application/pdf" if fmt == "pdf" else "text/markdown"
            ext = "pdf" if fmt == "pdf" else "md"
            return Response(
                content=content,
                media_type=media,
                headers={
                    "Content-Disposition": f'attachment; filename="assay-{suffix}-{order.package_id}.{ext}"',
                },
            )
    except Exception:
        logger.exception("GCS download failed for order %s", order.id)

    # Last resort: serve whatever local file exists (md fallback for pdf request)
    if report_file.exists():
        return FileResponse(
            path=str(report_file),
            filename=f"assay-{suffix}-{order.package_id}.md",
            media_type="text/markdown",
        )

    raise HTTPException(status_code=404, detail="Report file not found")
