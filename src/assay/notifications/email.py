"""Transactional email via Resend API.

Handles all outbound programmatic email: order confirmations, report delivery,
score-change notifications, newsletter subscription lifecycle.
Inbound/conversational email stays on Migadu.
"""

import logging

import resend

from assay.config import settings

logger = logging.getLogger(__name__)

FROM_ADDRESS = "Assay Tools <hello@assay.tools>"


def _ensure_resend():
    """Configure the Resend SDK. Returns True if configured, False otherwise."""
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not configured — email disabled")
        return False
    resend.api_key = settings.resend_api_key
    return True


def send_order_confirmation(
    to_email: str, order_id: int, package_id: str, order_type: str,
    access_token: str = "",
) -> bool:
    """Send immediate order confirmation after payment."""
    if not _ensure_resend():
        return False

    type_labels = {
        "report": "Full Evaluation Report",
        "brief": "Package Brief",
        "monitoring_subscription": "Package Monitoring",
    }
    amount_labels = {
        "report": "$99.00",
        "brief": "$3.00",
        "monitoring_subscription": "$3.00/mo",
    }
    type_label = type_labels.get(order_type, order_type)
    amount = amount_labels.get(order_type, "—")

    if order_type in ("report", "brief"):
        status_msg = (
            "Your report is being generated now. We'll email you the download link "
            "when it's ready — Full Evaluation Reports typically take 20-30 minutes, "
            "Package Briefs around 5 minutes."
        )
    else:
        status_msg = (
            "Your monitoring subscription is now active. You'll receive alerts "
            "when this package's scores change significantly."
        )

    text = f"""Thanks for your purchase!

Order #{order_id}
Product: {type_label}
Package: {package_id}
Amount: {amount}

{status_msg}

View your order: {settings.app_url}/orders/{access_token}/success

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

  <p style="color: #d1d5db; font-size: 14px; line-height: 1.6;">{status_msg}</p>

  <div style="text-align: center; margin: 28px 0;">
    <a href="{settings.app_url}/orders/{access_token}/success"
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

    try:
        resend.Emails.send({
            "from": FROM_ADDRESS,
            "to": [to_email],
            "reply_to": "hello@assay.tools",
            "subject": f"Order #{order_id} confirmed — {package_id}",
            "text": text,
            "html": html,
        })
        logger.info("Confirmation email sent for order %d to %s", order_id, to_email)
        return True
    except Exception:
        logger.exception("Failed to send confirmation email for order %d", order_id)
        return False


def send_report_ready(
    to_email: str, order_id: int, package_id: str, report_path: str | None = None,
    access_token: str = "",
) -> bool:
    """Send notification when report is ready, with PDF and markdown attached."""
    if not _ensure_resend():
        return False

    download_url = f"{settings.app_url}/orders/{access_token}/success"

    text = f"""Your Assay evaluation report for {package_id} is ready!

Both the PDF and markdown versions are attached to this email.

You can also download from: {download_url}

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

  <p style="color: #9ca3af; font-size: 14px;">Both the branded PDF and agent-friendly markdown are attached to this email.</p>

  <div style="text-align: center; margin: 28px 0;">
    <a href="{download_url}"
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

    # Build attachments list
    attachments = []
    if report_path:
        from assay.reports.delivery import PROJECT_ROOT
        md_path = PROJECT_ROOT / report_path
        pdf_path = md_path.with_suffix(".pdf")

        if md_path.exists():
            attachments.append({
                "filename": md_path.name,
                "content": list(md_path.read_bytes()),
            })
        if pdf_path.exists():
            attachments.append({
                "filename": pdf_path.name,
                "content": list(pdf_path.read_bytes()),
            })

    params: dict = {
        "from": FROM_ADDRESS,
        "to": [to_email],
        "reply_to": "hello@assay.tools",
        "subject": f"Your report is ready — {package_id}",
        "text": text,
        "html": html,
    }
    if attachments:
        params["attachments"] = attachments

    try:
        resend.Emails.send(params)
        logger.info("Report-ready email sent for order %d to %s", order_id, to_email)
        return True
    except Exception:
        logger.exception("Failed to send report-ready email for order %d", order_id)
        return False


def send_score_change_alert(
    to_email: str,
    package_id: str,
    old_scores: dict,
    new_scores: dict,
) -> bool:
    """Send score change alert to monitoring subscribers."""
    if not _ensure_resend():
        return False

    def _fmt(label, old, new):
        if old is None or new is None:
            return ""
        delta = new - old
        arrow = "+" if delta > 0 else ""
        return f"{label}: {old:.0f} → {new:.0f} ({arrow}{delta:.0f})"

    changes = []
    for key, label in [("af", "Agent Friendliness"), ("security", "Security"), ("reliability", "Reliability")]:
        old_val = old_scores.get(key)
        new_val = new_scores.get(key)
        if old_val is not None and new_val is not None and old_val != new_val:
            changes.append(_fmt(label, old_val, new_val))

    if not changes:
        return False

    changes_text = "\n".join(changes)
    changes_html = "".join(
        f'<tr><td style="color: #d1d5db; padding: 6px 0; font-size: 14px;">{c}</td></tr>'
        for c in changes
    )

    pkg_url = f"{settings.app_url}/packages/{package_id}"

    text = f"""Score change detected for {package_id}

{changes_text}

View package: {pkg_url}

You're receiving this because you have an active monitoring subscription for this package.

— Assay Tools
https://assay.tools
"""

    html = f"""<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 560px; margin: 0 auto; padding: 24px; color: #e5e7eb; background: #111827;">
  <div style="border-bottom: 2px solid #6366f1; padding-bottom: 16px; margin-bottom: 24px;">
    <h1 style="font-size: 20px; color: #fff; margin: 0;">Assay Tools</h1>
  </div>

  <p style="color: #d1d5db; font-size: 16px;">Score change detected for <strong style="color: #fff;">{package_id}</strong></p>

  <div style="background: #1f2937; border: 1px solid #374151; border-radius: 12px; padding: 20px; margin: 20px 0;">
    <table style="width: 100%; border-collapse: collapse;">
      {changes_html}
    </table>
  </div>

  <div style="text-align: center; margin: 28px 0;">
    <a href="{pkg_url}"
       style="background: #6366f1; color: #fff; text-decoration: none; padding: 12px 28px; border-radius: 8px; font-size: 14px; font-weight: 500; display: inline-block;">
      View Package
    </a>
  </div>

  <p style="color: #6b7280; font-size: 12px; margin-top: 32px; border-top: 1px solid #1f2937; padding-top: 16px;">
    You're receiving this because you have an active monitoring subscription for this package.<br>
    Questions? Reply to this email.<br>
    <a href="https://assay.tools" style="color: #6366f1; text-decoration: none;">assay.tools</a>
  </p>
</body>
</html>"""

    try:
        resend.Emails.send({
            "from": FROM_ADDRESS,
            "to": [to_email],
            "reply_to": "hello@assay.tools",
            "subject": f"Score change — {package_id}",
            "text": text,
            "html": html,
        })
        logger.info("Score change alert sent for %s to %s", package_id, to_email)
        return True
    except Exception:
        logger.exception("Failed to send score change alert for %s to %s", package_id, to_email)
        return False


def send_subscription_confirmation(to_email: str, confirmation_token: str) -> bool:
    """Send double opt-in confirmation email for newsletter signup."""
    if not _ensure_resend():
        return False

    confirm_url = f"{settings.app_url}/confirm?token={confirmation_token}"

    text_body = f"""Thanks for subscribing to the Assay newsletter!

Please confirm your email address by visiting:
{confirm_url}

You'll get weekly updates on new evaluations, score changes, and ecosystem insights.

If you didn't sign up, just ignore this email.

— Assay Tools
https://assay.tools
"""

    html_body = f"""<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 560px; margin: 0 auto; padding: 24px; color: #e5e7eb; background: #111827;">
  <div style="border-bottom: 2px solid #6366f1; padding-bottom: 16px; margin-bottom: 24px;">
    <h1 style="font-size: 20px; color: #fff; margin: 0;">Assay Tools</h1>
  </div>

  <p style="color: #d1d5db; font-size: 16px;">Thanks for subscribing!</p>

  <p style="color: #9ca3af; font-size: 14px; line-height: 1.6;">
    Please confirm your email address to start receiving weekly updates on new evaluations,
    score changes, and ecosystem insights.
  </p>

  <div style="text-align: center; margin: 28px 0;">
    <a href="{confirm_url}"
       style="background: #6366f1; color: #fff; text-decoration: none; padding: 12px 28px; border-radius: 8px; font-size: 14px; font-weight: 500; display: inline-block;">
      Confirm Subscription
    </a>
  </div>

  <p style="color: #6b7280; font-size: 12px; margin-top: 32px; border-top: 1px solid #1f2937; padding-top: 16px;">
    If you didn't sign up, just ignore this email.<br>
    <a href="https://assay.tools" style="color: #6366f1; text-decoration: none;">assay.tools</a>
  </p>
</body>
</html>"""

    try:
        resend.Emails.send({
            "from": FROM_ADDRESS,
            "to": [to_email],
            "reply_to": "hello@assay.tools",
            "subject": "Confirm your Assay newsletter subscription",
            "text": text_body,
            "html": html_body,
        })
        logger.info("Confirmation email sent to %s", to_email)
        return True
    except Exception:
        logger.exception("Failed to send confirmation email to %s", to_email)
        return False


def send_newsletter(
    to_email: str, subject: str, html_content: str, text_content: str,
    unsubscribe_token: str,
) -> bool:
    """Send a newsletter issue to a single subscriber."""
    if not _ensure_resend():
        return False

    unsubscribe_url = f"{settings.app_url}/unsubscribe?token={unsubscribe_token}"

    # Inject unsubscribe footer into HTML
    footer = f"""
  <div style="text-align: center; margin-top: 32px; padding-top: 16px; border-top: 1px solid #1f2937;">
    <p style="color: #6b7280; font-size: 11px;">
      You're receiving this because you subscribed at assay.tools.<br>
      <a href="{unsubscribe_url}" style="color: #6366f1; text-decoration: none;">Unsubscribe</a>
    </p>
  </div>
</body>
</html>"""
    html_with_footer = html_content.replace("</body>\n</html>", footer)
    if html_with_footer == html_content:
        html_with_footer = html_content + footer

    text_with_footer = text_content + f"\n\n---\nUnsubscribe: {unsubscribe_url}\n"

    try:
        resend.Emails.send({
            "from": FROM_ADDRESS,
            "to": [to_email],
            "reply_to": "hello@assay.tools",
            "subject": subject,
            "text": text_with_footer,
            "html": html_with_footer,
            "headers": {
                "List-Unsubscribe": f"<{unsubscribe_url}>",
                "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
            },
        })
        return True
    except Exception:
        logger.exception("Failed to send newsletter to %s", to_email)
        return False
