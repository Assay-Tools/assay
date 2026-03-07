"""Evaluation Scheduler — strategic priority queue for package evaluations.

Single source of truth for "what to evaluate next", used by both the API
queue endpoint and the batch evaluator CLI.

Priority tiers (filled sequentially up to limit):
  1. Flagged for re-evaluation (status == "reevaluate")
  2. Never evaluated (af_score IS NULL)
  3. Stale (evaluated > 30 days ago, monthly freshness target)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from assay.models.package import Package

logger = logging.getLogger(__name__)

FRESHNESS_DAYS = 30


def get_evaluation_queue(
    db: Session,
    limit: int = 100,
    package_type: str | None = None,
    priority: str | None = None,
) -> list[dict]:
    """Return packages needing evaluation in priority order.

    Each item includes the Package object and a tier label.
    Returns list of dicts: {"package": Package, "tier": str, "reason": str}
    """
    results: list[dict] = []
    seen_ids: set[str] = set()

    def _base_query():
        q = db.query(Package)
        if package_type:
            q = q.filter(Package.package_type == package_type)
        if priority:
            q = q.filter(Package.priority == priority)
        return q

    # --- Tier 1: Flagged for re-evaluation ---
    if len(results) < limit:
        remaining = limit - len(results)
        flagged = (
            _base_query()
            .filter(Package.status == "reevaluate")
            .order_by(Package.priority.asc(), Package.last_evaluated.asc().nulls_first())
            .limit(remaining)
            .all()
        )
        for pkg in flagged:
            if pkg.id not in seen_ids:
                results.append({
                    "package": pkg, "tier": "flagged",
                    "reason": "flagged_for_reevaluation",
                })
                seen_ids.add(pkg.id)

    # --- Tier 2: Never evaluated ---
    if len(results) < limit:
        remaining = limit - len(results)
        unevaluated = (
            _base_query()
            .filter(Package.af_score.is_(None))
            .filter(Package.status != "reevaluate")  # already handled above
            .order_by(
                Package.priority.asc(),
                Package.stars.desc().nulls_last(),
                Package.created_at.desc(),
            )
            .limit(remaining)
            .all()
        )
        for pkg in unevaluated:
            if pkg.id not in seen_ids:
                results.append({"package": pkg, "tier": "unevaluated", "reason": "never_evaluated"})
                seen_ids.add(pkg.id)

    # --- Tier 3: Stale (>30 days since last evaluation) ---
    if len(results) < limit:
        remaining = limit - len(results)
        stale_cutoff = datetime.now(timezone.utc) - timedelta(days=FRESHNESS_DAYS)
        stale = (
            _base_query()
            .filter(
                Package.af_score.isnot(None),
                Package.status != "reevaluate",  # already handled
                Package.last_evaluated < stale_cutoff,
            )
            .order_by(Package.priority.asc(), Package.last_evaluated.asc())
            .limit(remaining)
            .all()
        )
        for pkg in stale:
            if pkg.id not in seen_ids:
                results.append({"package": pkg, "tier": "stale", "reason": "stale"})
                seen_ids.add(pkg.id)

    return results


def get_evaluation_stats(db: Session) -> dict:
    """Return counts per evaluation tier and freshness percentage."""
    stale_cutoff = datetime.now(timezone.utc) - timedelta(days=FRESHNESS_DAYS)

    total_packages = db.query(func.count(Package.id)).scalar() or 0

    total_flagged = (
        db.query(func.count(Package.id))
        .filter(Package.status == "reevaluate")
        .scalar() or 0
    )

    total_unevaluated = (
        db.query(func.count(Package.id))
        .filter(Package.af_score.is_(None))
        .scalar() or 0
    )

    total_evaluated = (
        db.query(func.count(Package.id))
        .filter(Package.af_score.isnot(None))
        .scalar() or 0
    )

    total_stale = (
        db.query(func.count(Package.id))
        .filter(
            Package.af_score.isnot(None),
            Package.last_evaluated < stale_cutoff,
        )
        .scalar() or 0
    )

    total_fresh = (
        db.query(func.count(Package.id))
        .filter(
            Package.af_score.isnot(None),
            Package.last_evaluated >= stale_cutoff,
        )
        .scalar() or 0
    )

    freshness_pct = round(total_fresh / total_evaluated * 100, 1) if total_evaluated > 0 else 0.0

    return {
        "total_packages": total_packages,
        "total_evaluated": total_evaluated,
        "total_flagged": total_flagged,
        "total_unevaluated": total_unevaluated,
        "total_stale": total_stale,
        "total_fresh": total_fresh,
        "evaluation_freshness_pct": freshness_pct,
        "freshness_target_days": FRESHNESS_DAYS,
    }
