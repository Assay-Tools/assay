"""API route handlers for Assay."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload
from starlette.responses import Response

from assay.database import get_db
from assay.models import (
    Category,
    Package,
    PackageAgentReadiness,
    PackageInterface,
    PackagePricing,
    PackageRequirements,
    ScoreSnapshot,
)

from .rate_limit import API_RATE_LIMIT, limiter
from .schemas import (
    CategoryItem,
    CategoryListResponse,
    CategoryPackagesResponse,
    CompareResponse,
    HealthResponse,
    PackageListResponse,
    ScoreDistribution,
    StatsResponse,
)

router = APIRouter()


# --- Eager-loading options reused across queries ---

_package_eager = [
    joinedload(Package.interface),
    joinedload(Package.auth),
    joinedload(Package.pricing),
    joinedload(Package.performance),
    joinedload(Package.requirements),
    joinedload(Package.agent_readiness),
    joinedload(Package.category),
]


def _apply_eager(q):
    for opt in _package_eager:
        q = q.options(opt)
    return q


# --- Health ---


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health():
    """Check API health and version."""
    return HealthResponse()


# --- Packages ---


@router.get("/v1/packages", response_model=PackageListResponse, tags=["packages"])
@limiter.limit(API_RATE_LIMIT)
def list_packages(
    request: Request,
    response: Response,
    category: str | None = Query(None, description="Filter by category slug"),
    has_mcp: bool | None = Query(None, description="Filter packages with MCP server"),
    free_tier: bool | None = Query(None, description="Filter packages with a free tier"),
    min_af_score: float | None = Query(None, ge=0, le=100, description="Minimum AF score"),
    min_security_score: float | None = Query(
        None, ge=0, le=100, description="Minimum security score",
    ),
    min_reliability_score: float | None = Query(
        None, ge=0, le=100, description="Minimum reliability score",
    ),
    compliance: str | None = Query(None, description="Required compliance (e.g. SOC2, HIPAA)"),
    type: str | None = Query(None, description="Filter by package type (mcp_server, skill)"),
    q: str | None = Query(
        None, description="Text search across name, description, and tags",
        alias="q",
    ),
    sort: str = Query("af_score:desc", description="Sort field:direction (e.g. name:asc)"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List and filter evaluated packages.

    Supports filtering by category, MCP availability, free tier,
    minimum AF score, compliance, package type, and text search.
    Results are paginated and sortable.
    """
    query = db.query(Package)
    query = _apply_eager(query)

    # Text search
    if q:
        escaped = q.replace("%", r"\%").replace("_", r"\_")
        search_term = f"%{escaped}%"
        query = query.filter(
            or_(
                Package.name.ilike(search_term),
                Package.what_it_does.ilike(search_term),
                Package.tags.ilike(search_term),
            )
        )

    # Filters
    if type:
        query = query.filter(Package.package_type == type)
    if category:
        query = query.filter(Package.category_slug == category)
    if has_mcp is not None:
        query = query.join(Package.interface).filter(
            PackageInterface.has_mcp_server == has_mcp,
        )
    if free_tier is not None:
        query = query.join(Package.pricing).filter(
            PackagePricing.free_tier_exists == free_tier,
        )
    if min_af_score is not None:
        query = query.filter(Package.af_score >= min_af_score)
    if min_security_score is not None:
        query = query.filter(Package.security_score >= min_security_score)
    if min_reliability_score is not None:
        query = query.filter(Package.reliability_score >= min_reliability_score)
    if compliance:
        # compliance stored as JSON array string — use LIKE for SQLite compat
        query = query.join(Package.requirements).filter(
            PackageRequirements.compliance.contains(compliance)
        )

    # Count before pagination
    total = query.count()

    # Sorting (whitelist to prevent attribute probing)
    SORTABLE_FIELDS = {
        "af_score", "security_score", "reliability_score",
        "name", "created_at", "last_evaluated",
    }
    sort_field, _, sort_dir = sort.partition(":")
    sort_dir = sort_dir.lower() if sort_dir else "desc"
    if sort_field not in SORTABLE_FIELDS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort field: {sort_field}. "
            f"Allowed: {', '.join(sorted(SORTABLE_FIELDS))}",
        )
    column = getattr(Package, sort_field)
    if sort_dir == "asc":
        query = query.order_by(column.asc())
    else:
        query = query.order_by(column.desc().nulls_last())

    packages = query.offset(offset).limit(limit).all()

    return PackageListResponse(
        packages=[p.to_dict() for p in packages],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/v1/packages/updated-since", tags=["packages"])
@limiter.limit(API_RATE_LIMIT)
def packages_updated_since(
    request: Request,
    response: Response,
    timestamp: str = Query(
        ..., description="ISO 8601 timestamp (e.g. 2026-03-01T00:00:00Z)",
    ),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Get packages updated since a given timestamp.

    Useful for syncing local caches or tracking new evaluations.
    Returns packages ordered by updated_at descending.
    """
    try:
        since = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid timestamp format. Use ISO 8601 (e.g. 2026-03-01T00:00:00Z)",
        )

    q = db.query(Package).filter(Package.updated_at >= since)
    q = _apply_eager(q)
    total = q.count()
    packages = (
        q.order_by(Package.updated_at.desc())
        .offset(offset).limit(limit).all()
    )

    return PackageListResponse(
        packages=[p.to_dict() for p in packages],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/v1/packages/{package_id}", tags=["packages"])
@limiter.limit(API_RATE_LIMIT)
def get_package(
    request: Request, response: Response, package_id: str, db: Session = Depends(get_db),
):
    """Get full evaluation data for a single package."""
    q = db.query(Package).filter(Package.id == package_id)
    q = _apply_eager(q)
    pkg = q.first()
    if not pkg:
        raise HTTPException(status_code=404, detail=f"Package '{package_id}' not found")
    return pkg.to_dict()


@router.get("/v1/packages/{package_id}/agent-guide", tags=["packages"])
@limiter.limit(API_RATE_LIMIT)
def get_agent_guide(
    request: Request, response: Response, package_id: str, db: Session = Depends(get_db),
):
    """Get agent-optimized guide with scores, gotchas, and auth info."""
    q = db.query(Package).filter(Package.id == package_id)
    q = _apply_eager(q)
    pkg = q.first()
    if not pkg:
        raise HTTPException(status_code=404, detail=f"Package '{package_id}' not found")
    return pkg.to_agent_guide()


@router.get("/v1/packages/{package_id}/score-history", tags=["packages"])
@limiter.limit(API_RATE_LIMIT)
def get_score_history(
    request: Request,
    response: Response,
    package_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Get historical score snapshots for a package."""
    pkg = db.query(Package).filter(Package.id == package_id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail=f"Package '{package_id}' not found")

    snapshots = (
        db.query(ScoreSnapshot)
        .filter(ScoreSnapshot.package_id == package_id)
        .order_by(ScoreSnapshot.recorded_at.desc())
        .limit(limit)
        .all()
    )

    return {
        "package_id": package_id,
        "snapshots": [
            {
                "af_score": s.af_score,
                "security_score": s.security_score,
                "reliability_score": s.reliability_score,
                "recorded_at": s.recorded_at.isoformat() if s.recorded_at else None,
            }
            for s in snapshots
        ],
    }


# --- Categories ---


@router.get("/v1/categories", response_model=CategoryListResponse, tags=["categories"])
@limiter.limit(API_RATE_LIMIT)
def list_categories(request: Request, response: Response, db: Session = Depends(get_db)):
    """List all categories with evaluated package counts."""
    cats = db.query(Category).all()
    return CategoryListResponse(
        categories=[
            CategoryItem(
                slug=c.slug,
                name=c.name,
                description=c.description,
                package_count=c.package_count,
            )
            for c in sorted(cats, key=lambda c: c.name)
        ]
    )


@router.get(
    "/v1/categories/{slug}/packages", response_model=CategoryPackagesResponse, tags=["categories"],
)
@limiter.limit(API_RATE_LIMIT)
def get_category_packages(
    request: Request, response: Response, slug: str, db: Session = Depends(get_db),
):
    """Get all packages in a category, ranked by AF score."""
    cat = db.query(Category).filter(Category.slug == slug).first()
    if not cat:
        raise HTTPException(status_code=404, detail=f"Category '{slug}' not found")

    # Reload packages with eager loading for full to_dict()
    q = db.query(Package).filter(Package.category_slug == slug)
    q = _apply_eager(q)
    packages = q.order_by(Package.af_score.desc().nulls_last()).all()

    return CategoryPackagesResponse(
        category=CategoryItem(
            slug=cat.slug,
            name=cat.name,
            description=cat.description,
            package_count=cat.package_count,
        ),
        packages=[p.to_dict() for p in packages],
    )


@router.get(
    "/v1/categories/{slug}/leaderboard", tags=["categories"],
)
@limiter.limit(API_RATE_LIMIT)
def get_category_leaderboard(
    request: Request,
    response: Response,
    slug: str,
    dimension: str = Query(
        "af_score",
        description="Score dimension to rank by (af_score, security_score, reliability_score)",
    ),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Top packages in a category ranked by a score dimension."""
    cat = db.query(Category).filter(Category.slug == slug).first()
    if not cat:
        raise HTTPException(
            status_code=404, detail=f"Category '{slug}' not found",
        )

    column = getattr(Package, dimension, None)
    if column is None or dimension not in (
        "af_score", "security_score", "reliability_score",
    ):
        raise HTTPException(
            status_code=400,
            detail="dimension must be af_score, security_score, or reliability_score",
        )

    q = db.query(Package).filter(
        Package.category_slug == slug,
        column.isnot(None),
    )
    q = _apply_eager(q)
    packages = q.order_by(column.desc()).limit(limit).all()

    return {
        "category": CategoryItem(
            slug=cat.slug,
            name=cat.name,
            description=cat.description,
            package_count=cat.package_count,
        ).model_dump(),
        "dimension": dimension,
        "packages": [p.to_dict() for p in packages],
    }


# --- Compare ---


@router.get("/v1/compare", response_model=CompareResponse, tags=["compare"])
@limiter.limit(API_RATE_LIMIT)
def compare_packages(
    request: Request,
    response: Response,
    ids: str = Query(..., description="Comma-separated package IDs"),
    db: Session = Depends(get_db),
):
    """Compare up to 10 packages side by side."""
    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    if not id_list:
        raise HTTPException(status_code=400, detail="No package IDs provided")
    if len(id_list) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 packages for comparison")

    q = db.query(Package).filter(Package.id.in_(id_list))
    q = _apply_eager(q)
    packages = q.all()

    # Report missing IDs
    found_ids = {p.id for p in packages}
    missing = [i for i in id_list if i not in found_ids]
    if missing:
        raise HTTPException(status_code=404, detail=f"Packages not found: {', '.join(missing)}")

    return CompareResponse(packages=[p.to_dict() for p in packages])


# --- Evaluation Queue ---


@router.get("/v1/queue", tags=["contribute"])
@limiter.limit(API_RATE_LIMIT)
def get_evaluation_queue(
    request: Request,
    response: Response,
    limit: int = Query(50, ge=1, le=200),
    include_stale: bool = Query(True, description="Include packages needing re-evaluation"),
    package_type: str | None = Query(
        None, description="Filter by package type (mcp_server, skill)",
    ),
    priority: str | None = Query(None, description="Filter by priority (high, low)"),
    db: Session = Depends(get_db),
):
    """Get packages needing evaluation — for community contributors.

    Ordered by priority (high first), then by created_at desc.
    """
    # Unevaluated packages — high priority first, then by created_at
    q = db.query(Package).filter(Package.af_score.is_(None))
    if package_type:
        q = q.filter(Package.package_type == package_type)
    if priority:
        q = q.filter(Package.priority == priority)

    unevaluated = (
        q.order_by(
            # high priority first (h < l alphabetically)
            Package.priority.asc(),
            Package.created_at.desc(),
        )
        .limit(limit)
        .all()
    )

    results = [
        {
            "id": p.id,
            "name": p.name,
            "repo_url": p.repo_url,
            "category": p.category_slug,
            "package_type": p.package_type,
            "priority": p.priority,
            "stars": p.stars,
            "status": "needs_evaluation",
        }
        for p in unevaluated
    ]

    if include_stale and len(results) < limit:
        # Packages with composite scores but missing security/reliability sub-components
        remaining = limit - len(results)
        iq = (
            db.query(Package)
            .join(
                PackageAgentReadiness, Package.id == PackageAgentReadiness.package_id, isouter=True,
            )
            .filter(
                Package.af_score.isnot(None),
                or_(
                    PackageAgentReadiness.tls_enforcement.is_(None),
                    PackageAgentReadiness.package_id.is_(None),
                ),
            )
        )
        if package_type:
            iq = iq.filter(Package.package_type == package_type)
        if priority:
            iq = iq.filter(Package.priority == priority)

        incomplete = (
            iq.order_by(Package.priority.asc(), Package.created_at.desc())
            .limit(remaining)
            .all()
        )
        results.extend([
            {
                "id": p.id,
                "name": p.name,
                "repo_url": p.repo_url,
                "category": p.category_slug,
                "package_type": p.package_type,
                "priority": p.priority,
                "stars": p.stars,
                "status": "needs_reevaluation",
                "reason": "missing_sub_components",
                "last_evaluated": p.last_evaluated.isoformat() if p.last_evaluated else None,
                "current_af_score": p.af_score,
            }
            for p in incomplete
        ])

    # Stale packages (evaluated > 90 days ago)
    if include_stale and len(results) < limit:
        stale_cutoff = datetime.now(timezone.utc) - timedelta(days=90)
        remaining = limit - len(results)
        sq = db.query(Package).filter(
            Package.af_score.isnot(None),
            Package.last_evaluated < stale_cutoff,
        )
        if package_type:
            sq = sq.filter(Package.package_type == package_type)
        if priority:
            sq = sq.filter(Package.priority == priority)

        stale = (
            sq.order_by(Package.priority.asc(), Package.last_evaluated.asc())
            .limit(remaining)
            .all()
        )
        results.extend([
            {
                "id": p.id,
                "name": p.name,
                "repo_url": p.repo_url,
                "category": p.category_slug,
                "package_type": p.package_type,
                "priority": p.priority,
                "stars": p.stars,
                "status": "needs_reevaluation",
                "reason": "stale",
                "last_evaluated": p.last_evaluated.isoformat() if p.last_evaluated else None,
                "current_af_score": p.af_score,
            }
            for p in stale
        ])

    return {"count": len(results), "queue": results}


# --- Stats ---


@router.get("/v1/stats", response_model=StatsResponse, tags=["stats"])
@limiter.limit(API_RATE_LIMIT)
def get_stats(request: Request, response: Response, db: Session = Depends(get_db)):
    """Get sitewide statistics and score distribution."""
    total_packages = db.query(func.count(Package.id)).scalar() or 0
    total_evaluated = (
        db.query(func.count(Package.id))
        .filter(Package.af_score.is_not(None))
        .scalar() or 0
    )
    total_categories = db.query(func.count(Category.slug)).scalar() or 0
    avg_af = db.query(func.avg(Package.af_score)).filter(Package.af_score.is_not(None)).scalar()

    # Score distribution (0-100 scale)
    excellent = db.query(func.count(Package.id)).filter(Package.af_score >= 80).scalar() or 0
    good = (
        db.query(func.count(Package.id))
        .filter(Package.af_score >= 60, Package.af_score < 80)
        .scalar()
        or 0
    )
    fair = (
        db.query(func.count(Package.id))
        .filter(Package.af_score >= 40, Package.af_score < 60)
        .scalar()
        or 0
    )
    poor = db.query(func.count(Package.id)).filter(Package.af_score < 40).scalar() or 0
    unrated = (
        db.query(func.count(Package.id)).filter(Package.af_score.is_(None)).scalar() or 0
    )

    return StatsResponse(
        total_packages=total_packages,
        total_evaluated=total_evaluated,
        total_categories=total_categories,
        avg_af_score=round(avg_af, 2) if avg_af is not None else None,
        score_distribution=ScoreDistribution(
            excellent=excellent,
            good=good,
            fair=fair,
            poor=poor,
            unrated=unrated,
        ),
    )
