"""API route handlers for Assay."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from assay.database import get_db
from assay.models import Category, Package, PackageInterface, PackagePricing, PackageRequirements

from .schemas import (
    AgentGuideResponse,
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
    return HealthResponse()


# --- Packages ---


@router.get("/v1/packages", response_model=PackageListResponse, tags=["packages"])
def list_packages(
    category: str | None = Query(None, description="Filter by category slug"),
    has_mcp: bool | None = Query(None, description="Filter packages with MCP server"),
    free_tier: bool | None = Query(None, description="Filter packages with a free tier"),
    min_af_score: float | None = Query(None, ge=0, le=100, description="Minimum AF score"),
    compliance: str | None = Query(None, description="Required compliance (e.g. SOC2, HIPAA)"),
    sort: str = Query("af_score:desc", description="Sort field:direction (e.g. name:asc)"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(Package)
    q = _apply_eager(q)

    # Filters
    if category:
        q = q.filter(Package.category_slug == category)
    if has_mcp is not None:
        q = q.join(Package.interface).filter(PackageInterface.has_mcp_server == has_mcp)
    if free_tier is not None:
        q = q.join(Package.pricing).filter(PackagePricing.free_tier_exists == free_tier)
    if min_af_score is not None:
        q = q.filter(Package.af_score >= min_af_score)
    if compliance:
        # compliance stored as JSON array string — use LIKE for SQLite compat
        q = q.join(Package.requirements).filter(
            PackageRequirements.compliance.contains(compliance)
        )

    # Count before pagination
    total = q.count()

    # Sorting
    sort_field, _, sort_dir = sort.partition(":")
    sort_dir = sort_dir.lower() if sort_dir else "desc"
    column = getattr(Package, sort_field, None)
    if column is None:
        raise HTTPException(status_code=400, detail=f"Invalid sort field: {sort_field}")
    if sort_dir == "asc":
        q = q.order_by(column.asc())
    else:
        q = q.order_by(column.desc().nulls_last())

    packages = q.offset(offset).limit(limit).all()

    return PackageListResponse(
        packages=[p.to_dict() for p in packages],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/v1/packages/{package_id}", tags=["packages"])
def get_package(package_id: str, db: Session = Depends(get_db)):
    q = db.query(Package).filter(Package.id == package_id)
    q = _apply_eager(q)
    pkg = q.first()
    if not pkg:
        raise HTTPException(status_code=404, detail=f"Package '{package_id}' not found")
    return pkg.to_dict()


@router.get("/v1/packages/{package_id}/agent-guide", tags=["packages"])
def get_agent_guide(package_id: str, db: Session = Depends(get_db)):
    q = db.query(Package).filter(Package.id == package_id)
    q = _apply_eager(q)
    pkg = q.first()
    if not pkg:
        raise HTTPException(status_code=404, detail=f"Package '{package_id}' not found")
    return pkg.to_agent_guide()


# --- Categories ---


@router.get("/v1/categories", response_model=CategoryListResponse, tags=["categories"])
def list_categories(db: Session = Depends(get_db)):
    cats = db.query(Category).options(joinedload(Category.packages)).all()
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


@router.get("/v1/categories/{slug}/packages", response_model=CategoryPackagesResponse, tags=["categories"])
def get_category_packages(slug: str, db: Session = Depends(get_db)):
    cat = db.query(Category).options(joinedload(Category.packages)).filter(Category.slug == slug).first()
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


# --- Compare ---


@router.get("/v1/compare", response_model=CompareResponse, tags=["compare"])
def compare_packages(
    ids: str = Query(..., description="Comma-separated package IDs"),
    db: Session = Depends(get_db),
):
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
def get_evaluation_queue(
    limit: int = Query(50, ge=1, le=200),
    include_stale: bool = Query(True, description="Include packages needing re-evaluation"),
    db: Session = Depends(get_db),
):
    """Get packages needing evaluation — for community contributors."""
    # Unevaluated packages
    unevaluated = (
        db.query(Package)
        .filter(Package.af_score.is_(None))
        .order_by(Package.created_at.desc())
        .limit(limit)
        .all()
    )

    results = [
        {
            "id": p.id,
            "name": p.name,
            "repo_url": p.repo_url,
            "category": p.category_slug,
            "status": "needs_evaluation",
        }
        for p in unevaluated
    ]

    # Stale packages (evaluated > 90 days ago)
    if include_stale and len(results) < limit:
        stale_cutoff = datetime.now(timezone.utc) - timedelta(days=90)
        remaining = limit - len(results)
        stale = (
            db.query(Package)
            .filter(
                Package.af_score.isnot(None),
                Package.last_evaluated < stale_cutoff,
            )
            .order_by(Package.last_evaluated.asc())
            .limit(remaining)
            .all()
        )
        results.extend([
            {
                "id": p.id,
                "name": p.name,
                "repo_url": p.repo_url,
                "category": p.category_slug,
                "status": "needs_reevaluation",
                "last_evaluated": p.last_evaluated.isoformat() if p.last_evaluated else None,
                "current_af_score": p.af_score,
            }
            for p in stale
        ])

    return {"count": len(results), "queue": results}


# --- Stats ---


@router.get("/v1/stats", response_model=StatsResponse, tags=["stats"])
def get_stats(db: Session = Depends(get_db)):
    total_packages = db.query(func.count(Package.id)).scalar() or 0
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
