"""Collect weekly newsletter data from the Assay database.

Gathers: new packages, biggest score movers, newly evaluated packages,
category stats, and ecosystem totals for the past 7 days.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from assay.models import Category, Package, ScoreSnapshot

logger = logging.getLogger(__name__)


def _aware(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware (SQLite returns naive)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@dataclass
class ScoreChange:
    """A package whose scores changed significantly."""

    package_id: str
    name: str
    category: str | None
    old_af: float | None
    new_af: float | None
    af_delta: float
    old_security: float | None
    new_security: float | None
    security_delta: float
    old_reliability: float | None
    new_reliability: float | None
    reliability_delta: float


@dataclass
class NewPackage:
    """A package discovered this week."""

    package_id: str
    name: str
    category: str | None
    package_type: str
    stars: int | None


@dataclass
class NewlyEvaluated:
    """A package that received its first evaluation this week."""

    package_id: str
    name: str
    category: str | None
    af_score: float | None
    security_score: float | None
    reliability_score: float | None


@dataclass
class CategoryStat:
    """Per-category summary."""

    slug: str
    name: str
    total_evaluated: int
    new_this_week: int


@dataclass
class WeeklyDigest:
    """All data for a weekly newsletter issue."""

    week_start: datetime
    week_end: datetime
    new_packages: list[NewPackage] = field(default_factory=list)
    score_movers: list[ScoreChange] = field(default_factory=list)
    newly_evaluated: list[NewlyEvaluated] = field(default_factory=list)
    category_stats: list[CategoryStat] = field(default_factory=list)
    total_packages: int = 0
    total_evaluated: int = 0
    total_categories: int = 0
    freshness_pct: float = 0.0


def collect_weekly_data(db: Session, as_of: datetime | None = None) -> WeeklyDigest:
    """Collect all data needed for the weekly newsletter.

    Args:
        db: Database session.
        as_of: End of the reporting period (defaults to now).

    Returns:
        WeeklyDigest with all newsletter data populated.
    """
    now = as_of or datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    digest = WeeklyDigest(week_start=week_ago, week_end=now)

    # -- New packages discovered this week --
    new_pkgs = (
        db.query(Package)
        .filter(Package.created_at >= week_ago)
        .order_by(Package.stars.desc().nullslast(), Package.created_at.desc())
        .limit(20)
        .all()
    )
    digest.new_packages = [
        NewPackage(
            package_id=p.id,
            name=p.name,
            category=p.category_slug,
            package_type=p.package_type,
            stars=p.stars,
        )
        for p in new_pkgs
    ]

    # -- Newly evaluated (first scores this week) --
    # Use a subquery to find packages whose earliest snapshot is within this week
    first_snap_sub = (
        db.query(
            ScoreSnapshot.package_id,
            func.min(ScoreSnapshot.recorded_at).label("first_recorded"),
        )
        .group_by(ScoreSnapshot.package_id)
        .subquery()
    )
    newly_eval = (
        db.query(Package)
        .join(first_snap_sub, Package.id == first_snap_sub.c.package_id)
        .filter(
            first_snap_sub.c.first_recorded >= week_ago,
            Package.af_score.isnot(None),
        )
        .order_by(Package.af_score.desc())
        .limit(15)
        .all()
    )
    digest.newly_evaluated = [
        NewlyEvaluated(
            package_id=p.id,
            name=p.name,
            category=p.category_slug,
            af_score=p.af_score,
            security_score=p.security_score,
            reliability_score=p.reliability_score,
        )
        for p in newly_eval
    ]

    # -- Biggest score movers --
    # Find packages with 2+ snapshots where at least one is this week.
    # Use window functions to get latest and previous scores efficiently.
    from sqlalchemy import text as sa_text
    movers_query = sa_text("""
        WITH ranked AS (
            SELECT
                package_id,
                af_score,
                security_score,
                reliability_score,
                recorded_at,
                ROW_NUMBER() OVER (PARTITION BY package_id ORDER BY recorded_at DESC) as rn
            FROM score_snapshots
        ),
        latest AS (
            SELECT * FROM ranked WHERE rn = 1
        ),
        previous AS (
            SELECT * FROM ranked WHERE rn = 2
        )
        SELECT
            l.package_id,
            p.af_score as old_af, l.af_score as new_af,
            p.security_score as old_security, l.security_score as new_security,
            p.reliability_score as old_reliability, l.reliability_score as new_reliability
        FROM latest l
        JOIN previous p ON l.package_id = p.package_id
        WHERE l.recorded_at >= :week_ago
        ORDER BY (
            ABS(COALESCE(l.af_score, 0) - COALESCE(p.af_score, 0)) +
            ABS(COALESCE(l.security_score, 0) - COALESCE(p.security_score, 0)) +
            ABS(COALESCE(l.reliability_score, 0) - COALESCE(p.reliability_score, 0))
        ) DESC
        LIMIT 20
    """)
    mover_rows = db.execute(movers_query, {"week_ago": week_ago}).fetchall()
    for row in mover_rows:
        pkg_id = row[0]
        old_af, new_af = row[1], row[2]
        old_sec, new_sec = row[3], row[4]
        old_rel, new_rel = row[5], row[6]

        af_delta = (new_af or 0) - (old_af or 0)
        sec_delta = (new_sec or 0) - (old_sec or 0)
        rel_delta = (new_rel or 0) - (old_rel or 0)

        total_delta = abs(af_delta) + abs(sec_delta) + abs(rel_delta)
        if total_delta < 3:
            continue

        pkg = db.get(Package, pkg_id)
        if not pkg:
            continue

        digest.score_movers.append(
            ScoreChange(
                package_id=pkg_id,
                name=pkg.name,
                category=pkg.category_slug,
                old_af=old_af,
                new_af=new_af,
                af_delta=af_delta,
                old_security=old_sec,
                new_security=new_sec,
                security_delta=sec_delta,
                old_reliability=old_rel,
                new_reliability=new_rel,
                reliability_delta=rel_delta,
            )
        )

    digest.score_movers.sort(
        key=lambda x: abs(x.af_delta) + abs(x.security_delta) + abs(x.reliability_delta),
        reverse=True,
    )
    digest.score_movers = digest.score_movers[:10]

    # -- Category stats --
    categories = db.query(Category).all()
    for cat in categories:
        evaluated_count = (
            db.query(func.count(Package.id))
            .filter(Package.category_slug == cat.slug, Package.af_score.isnot(None))
            .scalar()
        )
        new_count = (
            db.query(func.count(Package.id))
            .filter(Package.category_slug == cat.slug, Package.created_at >= week_ago)
            .scalar()
        )
        digest.category_stats.append(
            CategoryStat(
                slug=cat.slug,
                name=cat.name,
                total_evaluated=evaluated_count or 0,
                new_this_week=new_count or 0,
            )
        )
    digest.category_stats.sort(key=lambda x: x.total_evaluated, reverse=True)

    # -- Ecosystem totals --
    digest.total_packages = db.query(func.count(Package.id)).scalar() or 0
    digest.total_evaluated = (
        db.query(func.count(Package.id))
        .filter(Package.af_score.isnot(None))
        .scalar() or 0
    )
    digest.total_categories = len([c for c in digest.category_stats if c.total_evaluated > 0])

    # Freshness: % evaluated within 30 days
    fresh_count = (
        db.query(func.count(Package.id))
        .filter(Package.af_score.isnot(None), Package.last_evaluated >= thirty_days_ago)
        .scalar() or 0
    )
    if digest.total_evaluated > 0:
        digest.freshness_pct = round(100 * fresh_count / digest.total_evaluated, 1)

    logger.info(
        "Newsletter data collected: %d new packages, %d movers, %d newly evaluated",
        len(digest.new_packages),
        len(digest.score_movers),
        len(digest.newly_evaluated),
    )
    return digest
