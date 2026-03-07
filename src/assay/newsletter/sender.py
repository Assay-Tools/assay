"""Send newsletter issues to confirmed subscribers via Resend.

Handles batch sending with per-subscriber unsubscribe tokens,
and records the send in the newsletter_issues table.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from assay.models import EmailSubscriber, NewsletterIssue
from assay.notifications.email import send_newsletter

logger = logging.getLogger(__name__)


def get_active_subscribers(db: Session) -> list[EmailSubscriber]:
    """Return all confirmed, non-unsubscribed subscribers."""
    return (
        db.query(EmailSubscriber)
        .filter(
            EmailSubscriber.confirmed.is_(True),
            EmailSubscriber.unsubscribed_at.is_(None),
        )
        .all()
    )


def send_newsletter_issue(
    db: Session,
    subject: str,
    html_content: str,
    text_content: str,
    dry_run: bool = False,
) -> NewsletterIssue:
    """Send a newsletter to all active subscribers and record the issue.

    Args:
        db: Database session.
        subject: Email subject line.
        html_content: HTML body (unsubscribe footer added per-recipient).
        text_content: Plaintext body (unsubscribe footer added per-recipient).
        dry_run: If True, record the issue but don't actually send emails.

    Returns:
        The created NewsletterIssue record.
    """
    subscribers = get_active_subscribers(db)

    issue = NewsletterIssue(
        subject=subject,
        content_html=html_content,
        content_text=text_content,
        recipients_count=len(subscribers),
    )
    db.add(issue)
    db.flush()

    if dry_run:
        logger.info("Dry run: would send to %d subscribers", len(subscribers))
        db.commit()
        return issue

    sent = 0
    failed = 0
    for sub in subscribers:
        if not sub.unsubscribe_token:
            logger.warning("Subscriber %s has no unsubscribe token, skipping", sub.email)
            failed += 1
            continue

        ok = send_newsletter(
            to_email=sub.email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            unsubscribe_token=sub.unsubscribe_token,
        )
        if ok:
            sent += 1
        else:
            failed += 1

    issue.sent_at = datetime.now(timezone.utc)
    db.commit()

    logger.info(
        "Newsletter #%d sent: %d delivered, %d failed, %d total subscribers",
        issue.id, sent, failed, len(subscribers),
    )
    return issue
