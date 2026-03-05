"""Feedback & support checks — recent feedback, subscribers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from assay.models import EmailSubscriber, Feedback

from .health import HealthAlert


def check_feedback(db: Session) -> list[HealthAlert]:
    """Check for feedback needing attention and subscriber growth."""
    alerts: list[HealthAlert] = []
    now = datetime.now(timezone.utc)

    # Count recent feedback (last 7 days)
    recent_cutoff = now - timedelta(days=7)
    recent_feedback = (
        db.query(func.count(Feedback.id))
        .filter(Feedback.submitted_at >= recent_cutoff)
        .scalar() or 0
    )

    # Total feedback
    total_feedback = db.query(func.count(Feedback.id)).scalar() or 0

    if recent_feedback > 0:
        alerts.append(HealthAlert(
            level="info",
            check="recent_feedback",
            message=(
                f"{recent_feedback} feedback in last 7 days ({total_feedback} total)"
            ),
        ))
    elif total_feedback > 0:
        alerts.append(HealthAlert(
            level="info",
            check="feedback_total",
            message=f"{total_feedback} total feedback submissions",
        ))

    # Subscriber count (informational)
    subscriber_count = db.query(func.count(EmailSubscriber.id)).scalar() or 0
    if subscriber_count > 0:
        alerts.append(HealthAlert(
            level="info",
            check="subscribers",
            message=f"{subscriber_count:,} email subscribers",
        ))

    return alerts
