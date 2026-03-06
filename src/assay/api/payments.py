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
            success_url=f"{settings.app_url}/orders/{order.id}/success",
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
            success_url=f"{settings.app_url}/orders/{order.id}/success",
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
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
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
        _send_confirmation_async(order.id, order.customer_email, order.package_id, order.order_type)

    # Generate report in background thread so webhook returns fast
    if order.order_type == "report":
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
            from assay.reports.delivery import generate_report_for_order
            report_path = generate_report_for_order(order, db)
            if report_path and order.customer_email:
                _send_report_ready_email(order.customer_email, order.id, order.package_id)
        except Exception:
            logger.exception("Background report generation failed for order %d", order_id)
        finally:
            db.close()

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


def _send_confirmation_async(order_id: int, email: str, package_id: str, order_type: str):
    """Send order confirmation email in background thread."""
    def _worker():
        try:
            _send_order_confirmation(email, order_id, package_id, order_type)
        except Exception:
            logger.exception("Failed to send confirmation email for order %d", order_id)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


def _smtp_send(smtp_user: str, smtp_pass: str, to_email: str, msg):
    """Send an email via SMTP. Uses Migadu (SMTP_SSL on port 465)."""
    import smtplib

    smtp_host = settings.smtp_host or "smtp.migadu.com"
    smtp_port = settings.smtp_port or 465

    with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, to_email, msg.as_string())


def _send_order_confirmation(to_email: str, order_id: int, package_id: str, order_type: str):
    """Send immediate order confirmation via SMTP."""
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    smtp_user = settings.smtp_user
    smtp_pass = settings.smtp_pass
    if not smtp_user or not smtp_pass:
        logger.warning("SMTP not configured — skipping confirmation email for order %d", order_id)
        return

    type_label = "Package Evaluation Report" if order_type == "report" else "Package Monitoring"
    amount = "$99.00" if order_type == "report" else "$3.00/mo"

    msg = MIMEMultipart("alternative")
    msg["From"] = f"Assay Tools <{smtp_user}>"
    msg["To"] = to_email
    msg["Subject"] = f"Order #{order_id} confirmed — {package_id}"

    text = f"""Thanks for your purchase!

Order #{order_id}
Product: {type_label}
Package: {package_id}
Amount: {amount}

{"Your evaluation report is being generated now. You'll receive another email with the download link shortly, typically within a minute or two." if order_type == "report" else "Your monitoring subscription is now active. You'll receive alerts when this package's scores change significantly."}

View your order: {settings.app_url}/orders/{order_id}/success

Questions? Reply to this email.

— Assay Tools
https://assay.tools
"""

    html = f"""<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 560px; margin: 0 auto; padding: 24px; color: #e5e7eb; background: #111827;">
  <div style="border-bottom: 2px solid #6366f1; padding-bottom: 16px; margin-bottom: 24px;">
    <h1 style="font-size: 20px; color: #fff; margin: 0;">Assay Tools</h1>
  </div>

  <p style="color: #9ca3af; margin-bottom: 24px;">Thanks for your purchase!</p>

  <div style="background: #1f2937; border: 1px solid #374151; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
    <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
      <tr><td style="color: #9ca3af; padding: 6px 0;">Order</td><td style="color: #fff; text-align: right; padding: 6px 0; font-family: monospace;">#{order_id}</td></tr>
      <tr><td style="color: #9ca3af; padding: 6px 0;">Product</td><td style="color: #fff; text-align: right; padding: 6px 0;">{type_label}</td></tr>
      <tr><td style="color: #9ca3af; padding: 6px 0;">Package</td><td style="color: #fff; text-align: right; padding: 6px 0;">{package_id}</td></tr>
      <tr style="border-top: 1px solid #374151;"><td style="color: #9ca3af; padding: 10px 0 6px;">Amount</td><td style="color: #fff; text-align: right; padding: 10px 0 6px; font-size: 18px; font-weight: 600;">{amount}</td></tr>
    </table>
  </div>

  <p style="color: #d1d5db; font-size: 14px; line-height: 1.6;">
    {"Your evaluation report is being generated now. You'll receive another email with the download link shortly — typically within a minute or two." if order_type == "report" else "Your monitoring subscription is now active. You'll receive alerts when this package's scores change significantly."}
  </p>

  <div style="text-align: center; margin: 28px 0;">
    <a href="{settings.app_url}/orders/{order_id}/success"
       style="background: #6366f1; color: #fff; text-decoration: none; padding: 12px 28px; border-radius: 8px; font-size: 14px; font-weight: 500; display: inline-block;">
      View Order
    </a>
  </div>

  <p style="color: #6b7280; font-size: 12px; margin-top: 32px; border-top: 1px solid #1f2937; padding-top: 16px;">
    Questions? Reply to this email.<br>
    <a href="https://assay.tools" style="color: #6366f1; text-decoration: none;">assay.tools</a>
  </p>
</body>
</html>"""

    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    _smtp_send(smtp_user, smtp_pass, to_email, msg)

    logger.info("Confirmation email sent for order %d to %s", order_id, to_email)


def _send_report_ready_email(to_email: str, order_id: int, package_id: str):
    """Send follow-up email when report is ready for download."""
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    smtp_user = settings.smtp_user
    smtp_pass = settings.smtp_pass
    if not smtp_user or not smtp_pass:
        logger.warning("SMTP not configured — skipping report-ready email for order %d", order_id)
        return

    download_url = f"{settings.app_url}/orders/{order_id}/success"

    msg = MIMEMultipart("alternative")
    msg["From"] = f"Assay Tools <{smtp_user}>"
    msg["To"] = to_email
    msg["Subject"] = f"Your report is ready — {package_id}"

    text = f"""Your Assay evaluation report for {package_id} is ready!

Download it here: {download_url}

— Assay Tools
https://assay.tools
"""

    html = f"""<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 560px; margin: 0 auto; padding: 24px; color: #e5e7eb; background: #111827;">
  <div style="border-bottom: 2px solid #6366f1; padding-bottom: 16px; margin-bottom: 24px;">
    <h1 style="font-size: 20px; color: #fff; margin: 0;">Assay Tools</h1>
  </div>

  <p style="color: #d1d5db; font-size: 16px;">Your evaluation report for <strong style="color: #fff;">{package_id}</strong> is ready!</p>

  <div style="text-align: center; margin: 28px 0;">
    <a href="{download_url}"
       style="background: #6366f1; color: #fff; text-decoration: none; padding: 12px 28px; border-radius: 8px; font-size: 14px; font-weight: 500; display: inline-block;">
      Download Report
    </a>
  </div>

  <p style="color: #6b7280; font-size: 12px; margin-top: 32px; border-top: 1px solid #1f2937; padding-top: 16px;">
    Questions? Reply to this email.<br>
    <a href="https://assay.tools" style="color: #6366f1; text-decoration: none;">assay.tools</a>
  </p>
</body>
</html>"""

    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    _smtp_send(smtp_user, smtp_pass, to_email, msg)

    logger.info("Report-ready email sent for order %d to %s", order_id, to_email)


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
