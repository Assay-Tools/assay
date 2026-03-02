"""Web routes — server-rendered HTML pages for Assay."""

import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from assay.database import get_db
from assay.models import Category, Package, PackageAgentReadiness

_templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(_templates_dir))

router = APIRouter(tags=["web"])

PER_PAGE = 20


def _community_stats(db: Session) -> dict:
    """Compute sitewide community stats for the footer banner."""
    stale_cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    total_evaluated = (
        db.query(func.count(Package.id))
        .filter(Package.af_score.isnot(None))
        .scalar() or 0
    )
    needs_eval = (
        db.query(func.count(Package.id))
        .filter(Package.af_score.is_(None))
        .scalar() or 0
    )
    stale_count = (
        db.query(func.count(Package.id))
        .filter(Package.af_score.isnot(None), Package.last_evaluated < stale_cutoff)
        .scalar() or 0
    )
    missing_sub = (
        db.query(func.count(Package.id))
        .join(PackageAgentReadiness, Package.id == PackageAgentReadiness.package_id, isouter=True)
        .filter(
            Package.af_score.isnot(None),
            or_(
                PackageAgentReadiness.tls_enforcement.is_(None),
                PackageAgentReadiness.package_id.is_(None),
            ),
        )
        .scalar() or 0
    )
    return {
        "total_evaluated": total_evaluated,
        "needs_eval": needs_eval,
        "needs_reeval": stale_count + missing_sub,
    }


# ── Landing page ──────────────────────────────────────────────────────────────


@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    """Landing page with stats and category grid."""
    # Stats
    total_packages = db.query(func.count(Package.id)).scalar() or 0
    total_categories = db.query(func.count(Category.slug)).scalar() or 0
    avg_af = db.query(func.avg(Package.af_score)).filter(Package.af_score.isnot(None)).scalar()

    stats = {
        "total_packages": total_packages,
        "total_categories": total_categories,
        "avg_af_score": round(avg_af, 1) if avg_af is not None else None,
    }

    # Categories with counts (eager load packages for count), sorted by count desc
    categories = (
        db.query(Category)
        .options(joinedload(Category.packages))
        .all()
    )
    categories.sort(key=lambda c: c.package_count, reverse=True)

    # Top rated packages for showcase
    top_packages = (
        db.query(Package)
        .options(joinedload(Package.category), joinedload(Package.interface))
        .filter(Package.af_score.isnot(None))
        .order_by(Package.af_score.desc())
        .limit(6)
        .all()
    )

    # Recently evaluated packages
    recent_packages = (
        db.query(Package)
        .options(joinedload(Package.category), joinedload(Package.interface))
        .filter(Package.af_score.isnot(None))
        .order_by(Package.created_at.desc())
        .limit(6)
        .all()
    )

    return templates.TemplateResponse(
        "pages/index.html",
        {
            "request": request,
            "stats": stats,
            "categories": categories,
            "top_packages": top_packages,
            "recent_packages": recent_packages,
            "community_stats": _community_stats(db),
        },
    )


# ── Packages browse ───────────────────────────────────────────────────────────


@router.get("/packages", response_class=HTMLResponse)
def packages_list(
    request: Request,
    q: str = Query(None, description="Search query"),
    category: str = Query(None, description="Category slug filter"),
    type: str = Query(None, description="Package type filter (mcp_server, skill)"),
    mcp: int = Query(None, description="MCP server filter (1=yes)"),
    free: int = Query(None, description="Free tier filter (1=yes)"),
    min_score: int = Query(0, ge=0, le=100, description="Minimum AF score"),
    page: int = Query(1, ge=1, description="Page number"),
    db: Session = Depends(get_db),
):
    """Browse and search packages with filters."""
    query = db.query(Package).options(
        joinedload(Package.category),
        joinedload(Package.interface),
        joinedload(Package.pricing),
    )

    # Package type filter
    if type:
        query = query.filter(Package.package_type == type)

    # Search
    if q:
        search_term = f"%{q}%"
        query = query.filter(
            or_(
                Package.name.ilike(search_term),
                Package.what_it_does.ilike(search_term),
                Package.tags.ilike(search_term),
            )
        )

    # Category filter
    if category:
        query = query.filter(Package.category_slug == category)

    # MCP filter
    if mcp:
        query = query.join(Package.interface).filter(
            Package.interface.has(has_mcp_server=True)
        )

    # Free tier filter
    if free:
        query = query.join(Package.pricing).filter(
            Package.pricing.has(free_tier_exists=True)
        )

    # Min score filter
    if min_score and min_score > 0:
        query = query.filter(Package.af_score >= min_score)

    # Count total before pagination
    total = query.count()
    total_pages = max(1, math.ceil(total / PER_PAGE))
    page = min(page, total_pages)

    # Order and paginate
    packages = (
        query.order_by(Package.af_score.desc().nulls_last(), Package.name)
        .offset((page - 1) * PER_PAGE)
        .limit(PER_PAGE)
        .all()
    )

    # Categories for filter sidebar
    categories = db.query(Category).order_by(Category.name).all()

    # Build pagination query string (without page param)
    qs_params = {}
    if q:
        qs_params["q"] = q
    if category:
        qs_params["category"] = category
    if type:
        qs_params["type"] = type
    if mcp:
        qs_params["mcp"] = "1"
    if free:
        qs_params["free"] = "1"
    if min_score:
        qs_params["min_score"] = str(min_score)
    pagination_qs = urlencode(qs_params)

    return templates.TemplateResponse(
        "pages/packages.html",
        {
            "request": request,
            "packages": packages,
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "per_page": PER_PAGE,
            "q": q,
            "categories": categories,
            "selected_category": category,
            "selected_type": type,
            "filter_mcp": bool(mcp),
            "filter_free": bool(free),
            "min_score": min_score,
            "pagination_qs": pagination_qs,
            "community_stats": _community_stats(db),
        },
    )


# ── Package detail ────────────────────────────────────────────────────────────


@router.get("/packages/{package_id}", response_class=HTMLResponse)
def package_detail(request: Request, package_id: str, db: Session = Depends(get_db)):
    """Full package detail page."""
    package = (
        db.query(Package)
        .options(
            joinedload(Package.category),
            joinedload(Package.interface),
            joinedload(Package.auth),
            joinedload(Package.pricing),
            joinedload(Package.performance),
            joinedload(Package.requirements),
            joinedload(Package.agent_readiness),
        )
        .filter(Package.id == package_id)
        .first()
    )

    if not package:
        return templates.TemplateResponse(
            "pages/package_detail.html",
            {"request": request, "package": None, "community_stats": _community_stats(db)},
            status_code=404,
        )

    return templates.TemplateResponse(
        "pages/package_detail.html",
        {"request": request, "package": package, "community_stats": _community_stats(db)},
    )


# ── Categories ────────────────────────────────────────────────────────────────


@router.get("/categories", response_class=HTMLResponse)
def categories_list(request: Request, db: Session = Depends(get_db)):
    """Category directory."""
    categories = (
        db.query(Category)
        .options(joinedload(Category.packages).joinedload(Package.interface))
        .all()
    )
    categories.sort(key=lambda c: c.package_count, reverse=True)

    # Compute avg AF score and MCP count per category
    for cat in categories:
        scored = [p.af_score for p in cat.packages if p.af_score is not None]
        cat.avg_af_score = round(sum(scored) / len(scored), 0) if scored else None
        cat.mcp_count = sum(
            1 for p in cat.packages
            if p.interface and p.interface.has_mcp_server
        )

    return templates.TemplateResponse(
        "pages/categories.html",
        {"request": request, "categories": categories, "community_stats": _community_stats(db)},
    )


@router.get("/categories/{slug}", response_class=HTMLResponse)
def category_detail(request: Request, slug: str, db: Session = Depends(get_db)):
    """Packages in a category."""
    category = db.query(Category).filter(Category.slug == slug).first()

    if not category:
        return templates.TemplateResponse(
            "pages/category.html",
            {"request": request, "category": None, "packages": [], "community_stats": _community_stats(db)},
            status_code=404,
        )

    packages = (
        db.query(Package)
        .options(
            joinedload(Package.interface),
            joinedload(Package.pricing),
        )
        .filter(Package.category_slug == slug)
        .order_by(Package.af_score.desc().nulls_last(), Package.name)
        .all()
    )

    return templates.TemplateResponse(
        "pages/category.html",
        {"request": request, "category": category, "packages": packages, "community_stats": _community_stats(db)},
    )


# ── Compare ───────────────────────────────────────────────────────────────────


@router.get("/compare", response_class=HTMLResponse)
def compare_packages(
    request: Request,
    ids: str = Query(None, description="Comma-separated package IDs"),
    db: Session = Depends(get_db),
):
    """Side-by-side package comparison."""
    packages = []
    ids_str = ids

    if ids:
        id_list = [i.strip() for i in ids.split(",") if i.strip()]
        if id_list:
            packages = (
                db.query(Package)
                .options(
                    joinedload(Package.category),
                    joinedload(Package.interface),
                    joinedload(Package.auth),
                    joinedload(Package.pricing),
                    joinedload(Package.agent_readiness),
                )
                .filter(Package.id.in_(id_list))
                .all()
            )
            # Preserve requested order
            pkg_map = {p.id: p for p in packages}
            packages = [pkg_map[pid] for pid in id_list if pid in pkg_map]

    # All package IDs for the autocomplete/selector
    all_packages = (
        db.query(Package.id, Package.name, Package.af_score)
        .order_by(Package.name)
        .all()
    )

    return templates.TemplateResponse(
        "pages/compare.html",
        {
            "request": request,
            "packages": packages,
            "ids_str": ids_str,
            "all_packages": all_packages,
            "community_stats": _community_stats(db),
        },
    )


# ── Contribute ────────────────────────────────────────────────────────────────


@router.get("/contribute", response_class=HTMLResponse)
def contribute(request: Request, db: Session = Depends(get_db)):
    """Community contribution page with evaluation queue."""
    # Packages needing evaluation (status = discovered, no af_score)
    needs_eval_count = (
        db.query(func.count(Package.id))
        .filter(Package.af_score.is_(None))
        .scalar() or 0
    )

    # Packages needing re-evaluation (evaluated > 90 days ago OR missing security sub-components)
    stale_cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    stale_count = (
        db.query(func.count(Package.id))
        .filter(
            Package.af_score.isnot(None),
            Package.last_evaluated < stale_cutoff,
        )
        .scalar() or 0
    )
    missing_subcomponents_count = (
        db.query(func.count(Package.id))
        .join(PackageAgentReadiness, Package.id == PackageAgentReadiness.package_id, isouter=True)
        .filter(
            Package.af_score.isnot(None),
            or_(
                PackageAgentReadiness.tls_enforcement.is_(None),
                PackageAgentReadiness.package_id.is_(None),
            ),
        )
        .scalar() or 0
    )
    needs_reeval_count = stale_count + missing_subcomponents_count

    total_evaluated = (
        db.query(func.count(Package.id))
        .filter(Package.af_score.isnot(None))
        .scalar() or 0
    )

    queue_stats = {
        "needs_eval": needs_eval_count,
        "needs_reeval": needs_reeval_count,
        "needs_subcomponents": missing_subcomponents_count,
        "total_evaluated": total_evaluated,
    }

    # Queue: unevaluated first (high priority, then low), then stale, limited to 20
    queue_packages = (
        db.query(Package)
        .options(joinedload(Package.category))
        .filter(Package.af_score.is_(None))
        .order_by(Package.priority.asc(), Package.created_at.desc())
        .limit(20)
        .all()
    )

    # If fewer than 20 unevaluated, add packages missing security/reliability sub-components
    if len(queue_packages) < 20:
        remaining = 20 - len(queue_packages)
        incomplete_packages = (
            db.query(Package)
            .options(joinedload(Package.category))
            .join(PackageAgentReadiness, Package.id == PackageAgentReadiness.package_id, isouter=True)
            .filter(
                Package.af_score.isnot(None),
                or_(
                    PackageAgentReadiness.tls_enforcement.is_(None),
                    PackageAgentReadiness.package_id.is_(None),
                ),
            )
            .order_by(Package.priority.asc(), Package.created_at.desc())
            .limit(remaining)
            .all()
        )
        queue_packages.extend(incomplete_packages)

    # If still fewer than 20, add stale ones
    if len(queue_packages) < 20:
        remaining = 20 - len(queue_packages)
        stale_packages = (
            db.query(Package)
            .options(joinedload(Package.category))
            .filter(
                Package.af_score.isnot(None),
                Package.last_evaluated < stale_cutoff,
            )
            .order_by(Package.priority.asc(), Package.last_evaluated.asc())
            .limit(remaining)
            .all()
        )
        queue_packages.extend(stale_packages)

    return templates.TemplateResponse(
        "pages/contribute.html",
        {
            "request": request,
            "queue_stats": queue_stats,
            "queue_packages": queue_packages,
            "community_stats": _community_stats(db),
        },
    )


# ── About ─────────────────────────────────────────────────────────────────────


@router.get("/about", response_class=HTMLResponse)
def about(request: Request, db: Session = Depends(get_db)):
    """About page with live stats."""
    total_packages = db.query(func.count(Package.id)).scalar() or 0
    total_categories = db.query(func.count(Category.slug)).scalar() or 0
    mcp_count = (
        db.query(func.count(Package.id))
        .join(Package.interface)
        .filter(Package.interface.has(has_mcp_server=True))
        .scalar()
        or 0
    )
    avg_af = db.query(func.avg(Package.af_score)).filter(Package.af_score.isnot(None)).scalar()

    stats = {
        "total_packages": total_packages,
        "total_categories": total_categories,
        "mcp_count": mcp_count,
        "avg_af_score": round(avg_af, 1) if avg_af is not None else None,
    }

    return templates.TemplateResponse(
        "pages/about.html",
        {"request": request, "stats": stats, "community_stats": _community_stats(db)},
    )
