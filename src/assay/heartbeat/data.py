"""Data pipeline checks — evaluation coverage, staleness, discovery freshness."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from assay.models import Package

from .health import HealthAlert


def check_data_pipeline(db: Session) -> list[HealthAlert]:
    """Run data pipeline health checks."""
    alerts: list[HealthAlert] = []
    now = datetime.now(timezone.utc)

    # Count packages by status
    total = db.query(func.count(Package.id)).scalar() or 0
    evaluated = (
        db.query(func.count(Package.id))
        .filter(Package.af_score.isnot(None))
        .scalar() or 0
    )
    unevaluated = total - evaluated

    # Alert if evaluation queue is very large
    if unevaluated > 5000:
        alerts.append(HealthAlert(
            level="warning",
            check="eval_queue_size",
            message=(
                f"Evaluation queue: {unevaluated:,} packages "
                f"({evaluated:,}/{total:,} evaluated)"
            ),
        ))

    # Check for stale evaluations (>90 days)
    stale_cutoff = now - timedelta(days=90)
    stale_count = (
        db.query(func.count(Package.id))
        .filter(
            Package.af_score.isnot(None),
            Package.last_evaluated < stale_cutoff,
        )
        .scalar() or 0
    )

    if stale_count > 0:
        pct = (stale_count / evaluated * 100) if evaluated > 0 else 0
        level = "warning" if pct > 25 else "info"
        alerts.append(HealthAlert(
            level=level,
            check="stale_evaluations",
            message=f"{stale_count:,} stale evaluations ({pct:.0f}% of {evaluated:,})",
        ))

    # Check if any evaluations happened recently (last 7 days)
    recent_cutoff = now - timedelta(days=7)
    recent_evals = (
        db.query(func.count(Package.id))
        .filter(
            Package.af_score.isnot(None),
            Package.last_evaluated >= recent_cutoff,
        )
        .scalar() or 0
    )

    if recent_evals == 0 and evaluated > 0:
        alerts.append(HealthAlert(
            level="warning",
            check="eval_velocity",
            message="No evaluations in the last 7 days",
        ))

    # Check evaluation coverage ratio
    if total > 0 and evaluated > 0:
        coverage = evaluated / total * 100
        if coverage < 30:
            alerts.append(HealthAlert(
                level="info",
                check="eval_coverage",
                message=f"Evaluation coverage: {coverage:.0f}% ({evaluated:,}/{total:,})",
            ))

    return alerts
