"""Web routes — server-rendered HTML pages for Assay."""

import math
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from assay.database import get_db
from assay.models import Category, Package

templates = Jinja2Templates(directory="src/assay/templates")

router = APIRouter(tags=["web"])

PER_PAGE = 20


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

    # Categories with counts (eager load packages for count)
    categories = (
        db.query(Category)
        .options(joinedload(Category.packages))
        .order_by(Category.name)
        .all()
    )

    return templates.TemplateResponse(
        "pages/index.html",
        {"request": request, "stats": stats, "categories": categories},
    )


# ── Packages browse ───────────────────────────────────────────────────────────


@router.get("/packages", response_class=HTMLResponse)
def packages_list(
    request: Request,
    q: str = Query(None, description="Search query"),
    category: str = Query(None, description="Category slug filter"),
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
            "filter_mcp": bool(mcp),
            "filter_free": bool(free),
            "min_score": min_score,
            "pagination_qs": pagination_qs,
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
            {"request": request, "package": None},
            status_code=404,
        )

    return templates.TemplateResponse(
        "pages/package_detail.html",
        {"request": request, "package": package},
    )


# ── Categories ────────────────────────────────────────────────────────────────


@router.get("/categories", response_class=HTMLResponse)
def categories_list(request: Request, db: Session = Depends(get_db)):
    """Category directory."""
    categories = (
        db.query(Category)
        .options(joinedload(Category.packages))
        .order_by(Category.name)
        .all()
    )

    return templates.TemplateResponse(
        "pages/categories.html",
        {"request": request, "categories": categories},
    )


@router.get("/categories/{slug}", response_class=HTMLResponse)
def category_detail(request: Request, slug: str, db: Session = Depends(get_db)):
    """Packages in a category."""
    category = db.query(Category).filter(Category.slug == slug).first()

    if not category:
        return templates.TemplateResponse(
            "pages/category.html",
            {"request": request, "category": None, "packages": []},
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
        {"request": request, "category": category, "packages": packages},
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

    return templates.TemplateResponse(
        "pages/compare.html",
        {"request": request, "packages": packages, "ids_str": ids_str},
    )


# ── About ─────────────────────────────────────────────────────────────────────


@router.get("/about", response_class=HTMLResponse)
def about(request: Request):
    """About page."""
    return templates.TemplateResponse(
        "pages/about.html",
        {"request": request},
    )
