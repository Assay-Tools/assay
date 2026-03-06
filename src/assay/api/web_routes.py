"""Web routes — server-rendered HTML pages for Assay."""

import math
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from assay.database import get_db
from assay.models import (
    Category,
    EmailSubscriber,
    Feedback,
    Order,
    Package,
    PackageAgentReadiness,
)

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
    # Stats — distinguish evaluated vs cataloged
    total_cataloged = db.query(func.count(Package.id)).scalar() or 0
    total_evaluated = (
        db.query(func.count(Package.id))
        .filter(Package.af_score.isnot(None))
        .scalar() or 0
    )
    total_categories = db.query(func.count(Category.slug)).scalar() or 0
    avg_af = db.query(func.avg(Package.af_score)).filter(Package.af_score.isnot(None)).scalar()

    stats = {
        "total_evaluated": total_evaluated,
        "total_cataloged": total_cataloged,
        "total_categories": total_categories,
        "avg_af_score": round(avg_af, 1) if avg_af is not None else None,
    }

    # Categories with counts, sorted by count desc
    categories = db.query(Category).all()
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

    # Search (escape LIKE wildcards in user input)
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

    stale_cutoff = datetime.now(timezone.utc) - timedelta(days=90)

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
            "stale_cutoff": stale_cutoff,
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

    # Compute staleness for template
    now = datetime.now(timezone.utc)
    is_stale = False
    days_since_eval = None
    if package.last_evaluated:
        last = package.last_evaluated
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        days_since_eval = (now - last).days
        is_stale = days_since_eval > 90

    return templates.TemplateResponse(
        "pages/package_detail.html",
        {
            "request": request,
            "package": package,
            "is_stale": is_stale,
            "days_since_eval": days_since_eval,
            "community_stats": _community_stats(db),
        },
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
            {
                "request": request, "category": None,
                "packages": [], "community_stats": _community_stats(db),
            },
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
        {
            "request": request, "category": category,
            "packages": packages, "community_stats": _community_stats(db),
        },
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


@router.get("/embed/compare", response_class=HTMLResponse)
def embed_compare(
    request: Request,
    ids: str = Query(..., description="Comma-separated package IDs"),
    db: Session = Depends(get_db),
):
    """Embeddable comparison widget for iframes."""
    id_list = [i.strip() for i in ids.split(",") if i.strip()][:10]
    if not id_list:
        return HTMLResponse("<p>No package IDs provided.</p>", status_code=400)

    packages = (
        db.query(Package)
        .options(joinedload(Package.category))
        .filter(Package.id.in_(id_list))
        .all()
    )
    pkg_map = {p.id: p for p in packages}
    packages = [pkg_map[pid] for pid in id_list if pid in pkg_map]

    return templates.TemplateResponse(
        "embeds/compare.html",
        {"request": request, "packages": packages},
    )


# ── Contribute ────────────────────────────────────────────────────────────────


@router.get("/contribute", response_class=HTMLResponse)
def contribute(
    request: Request,
    error: str = Query(None, description="OAuth error code"),
    db: Session = Depends(get_db),
):
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
            .join(
                PackageAgentReadiness, Package.id == PackageAgentReadiness.package_id, isouter=True,
            ).filter(
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
            "error": error,
        },
    )


# ── About ─────────────────────────────────────────────────────────────────────


@router.get("/about", response_class=HTMLResponse)
def about(request: Request, db: Session = Depends(get_db)):
    """About page with live stats."""
    total_cataloged = db.query(func.count(Package.id)).scalar() or 0
    total_evaluated = (
        db.query(func.count(Package.id))
        .filter(Package.af_score.isnot(None))
        .scalar() or 0
    )
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
        "total_evaluated": total_evaluated,
        "total_cataloged": total_cataloged,
        "total_categories": total_categories,
        "mcp_count": mcp_count,
        "avg_af_score": round(avg_af, 1) if avg_af is not None else None,
    }

    return templates.TemplateResponse(
        "pages/about.html",
        {"request": request, "stats": stats, "community_stats": _community_stats(db)},
    )


@router.get("/methodology", response_class=HTMLResponse)
def methodology(request: Request):
    """Scoring methodology deep-dive."""
    return templates.TemplateResponse(
        "pages/methodology.html",
        {"request": request},
    )


# ── llms.txt ───────────────────────────────────────────────────────────────

LLMS_TXT = """\
# Assay

> Assay is the quality layer for agentic software. It rates MCP servers, APIs, \
and SDKs across agent friendliness, security, and reliability — so agents and \
developers can choose the right tools.

Assay evaluates packages on three dimensions (each 0-100):
- **Agent Friendliness (AF)** — MCP quality, docs, error messages, auth simplicity, rate limits
- **Security** — TLS, auth strength, scope granularity, dependency hygiene, secret handling
- **Reliability** — uptime, version stability, breaking changes, error recovery

## API

- [Package list](/v1/packages): Browse and filter evaluated packages.
- [Package detail](/v1/packages/{package_id}): Full evaluation data for a single package.
- [Agent guide](/v1/packages/{id}/agent-guide): Agent-optimized view with scores.
- [Categories](/v1/categories): List all categories with package counts.
- [Category packages](/v1/categories/{slug}/packages): Packages in a category, by AF score.
- [Compare](/v1/compare?ids=a,b,c): Side-by-side comparison of up to 10 packages.
- [Stats](/v1/stats): Sitewide statistics and score distribution.
- [Evaluation queue](/v1/queue): Packages needing evaluation or re-evaluation.
- [Health](/v1/health): Health check endpoint.

## Website

- [Homepage](https://assay.tools/): Browse top-rated packages and categories.
- [All packages](https://assay.tools/packages): Search and filter the full directory.
- [Categories](https://assay.tools/categories): Browse by category.
- [Compare](https://assay.tools/compare): Side-by-side package comparison.
- [Contribute](https://assay.tools/contribute): See the evaluation queue and help rate packages.
- [Evaluation Guide](https://assay.tools/evaluate.md): Complete rubric and submission instructions for AI agents.
- [About](https://assay.tools/about): Scoring methodology and coverage stats.

## Optional

- [OpenAPI spec](/openapi.json): Full API schema in OpenAPI 3.1 format.
- [MCP server](https://github.com/Assay-Tools/assay): Assay's MCP server for agent integration.
"""

LLMS_FULL_TXT_EXTRA = """
## Scoring Details

### Agent Friendliness (AF) Sub-Components
| Component | Weight | What It Measures |
|-----------|--------|-----------------|
| MCP Server Quality | 25% | Existence, maturity, documentation of MCP server |
| Documentation Accuracy | 25% | API docs quality, examples, completeness |
| Error Message Quality | 20% | Structured errors with codes and recovery guidance |
| Auth Complexity | 15% | How easy to authenticate programmatically (100 = simple) |
| Rate Limit Clarity | 15% | Clear docs + response headers for rate limits |

### Security Sub-Components
| Component | Weight | What It Measures |
|-----------|--------|-----------------|
| TLS Enforcement | 25% | HTTPS required for all communication |
| Auth Strength | 25% | Mechanism strength (API keys, OAuth2, etc.) |
| Scope Granularity | 20% | Fine-grained permission controls |
| Dependency Hygiene | 15% | Clean dependencies, no known CVEs |
| Secret Handling | 15% | Credentials via env vars/vault, never in logs |

### Reliability Sub-Components
| Component | Weight | What It Measures |
|-----------|--------|-----------------|
| Uptime (Documented) | 30% | Published SLA, status page, uptime history |
| Version Stability | 25% | Stable releases, semver adherence |
| Breaking Changes | 25% | History of breaking changes, migration guides |
| Error Recovery | 20% | Retry guidance, idempotent operations |

### Score Thresholds
- 80+ Excellent (green)
- 60-79 Good (yellow)
- Below 60 Needs Work (red)

## API Usage Examples

Search for MCP servers with high AF scores:
```
GET /v1/packages?has_mcp=true&min_af_score=70&sort=af_score:desc
```

Get agent-optimized guide for a package:
```
GET /v1/packages/stripe/agent-guide
```

Compare alternatives:
```
GET /v1/compare?ids=resend,sendgrid,postmark
```

Filter by category:
```
GET /v1/packages?category=ai-ml&sort=af_score:desc
```

## Categories

The directory covers 16 categories: developer-tools, databases, ai-ml, communication, \
file-management, cloud-infrastructure, search, monitoring, productivity, security, \
finance, content-management, data-processing, social-media, agent-skills, and other.
"""


@router.get("/evaluate.md")
def evaluation_guide():
    """Portable evaluation guide for AI agents and human contributors."""
    guide_path = Path(__file__).parent.parent / "static" / "evaluate.md"
    return FileResponse(
        str(guide_path),
        media_type="text/markdown; charset=utf-8",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/llms.txt", response_class=PlainTextResponse)
def llms_txt():
    """Machine-readable site description for LLMs (llms.txt spec)."""
    return LLMS_TXT


@router.get("/llms-full.txt", response_class=PlainTextResponse)
def llms_full_txt():
    """Extended llms.txt with scoring methodology and API usage examples."""
    return LLMS_TXT + LLMS_FULL_TXT_EXTRA


# ── Order Success Page ────────────────────────────────────────────────────────


@router.get("/orders/{order_id}/success", response_class=HTMLResponse)
def order_success(request: Request, order_id: int, db: Session = Depends(get_db)):
    """Post-checkout success page showing order status and download link."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return templates.TemplateResponse("pages/order_success.html", {
            "request": request,
            "order": None,
            "error": "Order not found",
        })

    pkg = db.query(Package).filter(Package.id == order.package_id).first()

    return templates.TemplateResponse("pages/order_success.html", {
        "request": request,
        "order": order,
        "package": pkg,
        "error": None,
    })


# ── Admin / Data Freshness ────────────────────────────────────────────────────


@router.get("/admin/freshness", response_class=HTMLResponse)
def admin_freshness(request: Request, db: Session = Depends(get_db)):
    """Data freshness dashboard — evaluation coverage and staleness."""
    now = datetime.now(timezone.utc)

    # Overall counts
    total_cataloged = db.query(func.count(Package.id)).scalar() or 0
    total_evaluated = (
        db.query(func.count(Package.id))
        .filter(Package.af_score.isnot(None))
        .scalar() or 0
    )
    total_unevaluated = total_cataloged - total_evaluated

    # Staleness buckets (evaluated packages only)
    stale_30 = stale_60 = stale_90 = stale_180 = stale_older = never_dated = 0
    evaluated_pkgs = (
        db.query(Package.last_evaluated)
        .filter(Package.af_score.isnot(None))
        .all()
    )
    for (last_eval,) in evaluated_pkgs:
        if last_eval is None:
            never_dated += 1
            continue
        if last_eval.tzinfo is None:
            last_eval = last_eval.replace(tzinfo=timezone.utc)
        age_days = (now - last_eval).days
        if age_days <= 30:
            stale_30 += 1
        elif age_days <= 60:
            stale_60 += 1
        elif age_days <= 90:
            stale_90 += 1
        elif age_days <= 180:
            stale_180 += 1
        else:
            stale_older += 1

    staleness_buckets = [
        ("0-30 days", stale_30, "text-green-400"),
        ("31-60 days", stale_60, "text-green-400"),
        ("61-90 days", stale_90, "text-yellow-400"),
        ("91-180 days", stale_180, "text-orange-400"),
        ("180+ days", stale_older, "text-red-400"),
        ("No date", never_dated, "text-gray-500"),
    ]

    # Sub-component coverage (how many have full breakdowns)
    has_sub = (
        db.query(func.count(PackageAgentReadiness.package_id))
        .filter(PackageAgentReadiness.tls_enforcement.isnot(None))
        .scalar() or 0
    )
    missing_sub = total_evaluated - has_sub

    # Per-category freshness
    categories_raw = (
        db.query(
            Category.name,
            Category.slug,
            func.count(Package.id).label("total"),
            func.count(Package.af_score).label("evaluated"),
        )
        .join(Package, Package.category_slug == Category.slug, isouter=True)
        .group_by(Category.slug, Category.name)
        .order_by(Category.name)
        .all()
    )
    category_stats = []
    for name, slug, total, evaluated in categories_raw:
        pct = round(evaluated / total * 100) if total > 0 else 0
        category_stats.append({
            "name": name,
            "slug": slug,
            "total": total,
            "evaluated": evaluated,
            "pct": pct,
        })

    # Recently evaluated (last 10)
    recent = (
        db.query(Package.id, Package.name, Package.last_evaluated, Package.af_score)
        .filter(Package.af_score.isnot(None), Package.last_evaluated.isnot(None))
        .order_by(Package.last_evaluated.desc())
        .limit(10)
        .all()
    )

    return templates.TemplateResponse(
        "pages/admin_freshness.html",
        {
            "request": request,
            "total_cataloged": total_cataloged,
            "total_evaluated": total_evaluated,
            "total_unevaluated": total_unevaluated,
            "staleness_buckets": staleness_buckets,
            "has_sub_components": has_sub,
            "missing_sub_components": missing_sub,
            "category_stats": category_stats,
            "recent_evaluations": recent,
            "community_stats": _community_stats(db),
        },
    )


# ── Embeddable Score Badges ───────────────────────────────────────────────────


@router.get("/badge/{package_id}.svg")
def score_badge(package_id: str, db: Session = Depends(get_db)):
    """Shields.io-style SVG badge showing AF score for a package."""
    pkg = db.query(Package).filter(Package.id == package_id).first()
    if not pkg:
        svg = _badge_svg("assay", "not found", "#555", "#999")
        return Response(content=svg, media_type="image/svg+xml")

    if pkg.af_score is None:
        svg = _badge_svg("assay", "not evaluated", "#555", "#999")
    elif pkg.af_score >= 80:
        svg = _badge_svg(
            "assay", f"AF {pkg.af_score:.0f}", "#555", "#4c1",
        )
    elif pkg.af_score >= 60:
        svg = _badge_svg(
            "assay", f"AF {pkg.af_score:.0f}", "#555", "#dfb317",
        )
    else:
        svg = _badge_svg(
            "assay", f"AF {pkg.af_score:.0f}", "#555", "#e05d44",
        )

    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=3600"},
    )


def _badge_svg(
    label: str, value: str, label_color: str, value_color: str,
) -> str:
    """Generate a shields.io-style flat badge SVG."""
    label_width = len(label) * 7 + 10
    value_width = len(value) * 7 + 10
    total_width = label_width + value_width
    lx = label_width / 2
    vx = label_width + value_width / 2
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg"'
        f' width="{total_width}" height="20">\n'
        f'  <linearGradient id="b" x2="0" y2="100%">\n'
        f'    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>\n'
        f'    <stop offset="1" stop-opacity=".1"/>\n'
        f'  </linearGradient>\n'
        f'  <clipPath id="a">\n'
        f'    <rect width="{total_width}" height="20"'
        f' rx="3" fill="#fff"/>\n'
        f'  </clipPath>\n'
        f'  <g clip-path="url(#a)">\n'
        f'    <rect width="{label_width}" height="20"'
        f' fill="{label_color}"/>\n'
        f'    <rect x="{label_width}" width="{value_width}"'
        f' height="20" fill="{value_color}"/>\n'
        f'    <rect width="{total_width}" height="20"'
        f' fill="url(#b)"/>\n'
        f'  </g>\n'
        f'  <g fill="#fff" text-anchor="middle"'
        f' font-family="Verdana,Geneva,sans-serif"'
        f' font-size="11">\n'
        f'    <text x="{lx}" y="15"'
        f' fill="#010101" fill-opacity=".3">{label}</text>\n'
        f'    <text x="{lx}" y="14">{label}</text>\n'
        f'    <text x="{vx}" y="15"'
        f' fill="#010101" fill-opacity=".3">{value}</text>\n'
        f'    <text x="{vx}" y="14">{value}</text>\n'
        f'  </g>\n'
        f'</svg>'
    )


# ── RSS Feed ─────────────────────────────────────────────────────────────────


@router.get("/feed.xml")
def rss_feed(db: Session = Depends(get_db)):
    """RSS feed of recently evaluated packages."""
    packages = (
        db.query(Package)
        .filter(Package.af_score.isnot(None))
        .order_by(Package.last_evaluated.desc())
        .limit(50)
        .all()
    )

    items = []
    for pkg in packages:
        last_eval = ""
        if pkg.last_evaluated:
            last_eval = pkg.last_evaluated.strftime("%a, %d %b %Y %H:%M:%S +0000")
        desc = pkg.what_it_does or ""
        score_text = f"AF Score: {pkg.af_score:.0f}/100" if pkg.af_score else ""
        items.append(
            f"    <item>\n"
            f"      <title>{_xml_escape(pkg.name)} — {score_text}</title>\n"
            f"      <link>https://assay.tools/packages/{pkg.id}</link>\n"
            f"      <description>{_xml_escape(desc)}</description>\n"
            f"      <guid>https://assay.tools/packages/{pkg.id}</guid>\n"
            f"      <pubDate>{last_eval}</pubDate>\n"
            f"    </item>"
        )

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        "  <channel>\n"
        "    <title>Assay — Agent-Readiness Ratings</title>\n"
        "    <link>https://assay.tools</link>\n"
        "    <description>Recently evaluated MCP servers, APIs, and SDKs</description>\n"
        "    <language>en-us</language>\n"
        + "\n".join(items) + "\n"
        "  </channel>\n"
        "</rss>"
    )
    return Response(content=xml, media_type="application/rss+xml")


def _xml_escape(text: str) -> str:
    """Escape special XML characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# ── Developer Docs ───────────────────────────────────────────────────────────


@router.get("/developers", response_class=HTMLResponse)
def developers_page(request: Request):
    """Developer documentation page with API examples and MCP config."""
    return templates.TemplateResponse("pages/developers.html", {
        "request": request,
    })


@router.get("/terms", response_class=HTMLResponse)
def terms_page(request: Request):
    """Terms of Service."""
    return templates.TemplateResponse("pages/terms.html", {"request": request})


@router.get("/privacy", response_class=HTMLResponse)
def privacy_page(request: Request):
    """Privacy Policy."""
    return templates.TemplateResponse("pages/privacy.html", {"request": request})


@router.get("/methodology", response_class=HTMLResponse)
def methodology_page(request: Request):
    """Scoring methodology deep-dive."""
    return templates.TemplateResponse("pages/methodology.html", {
        "request": request,
    })


# ── Email Subscribe ─────────────────────────────────────────────────────────

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


@router.post("/subscribe")
def subscribe_email(
    email: str = Form(...),
    db: Session = Depends(get_db),
):
    """Subscribe an email to the Assay newsletter."""
    email = email.strip().lower()
    if not _EMAIL_RE.match(email) or len(email) > 255:
        return RedirectResponse("/?subscribed=invalid", status_code=303)

    existing = db.query(EmailSubscriber).filter_by(email=email).first()
    if existing:
        return RedirectResponse("/?subscribed=already", status_code=303)

    subscriber = EmailSubscriber(email=email)
    db.add(subscriber)
    db.commit()
    return RedirectResponse("/?subscribed=ok", status_code=303)


# ── Feedback ─────────────────────────────────────────────────────────────────

_FEEDBACK_TYPES = {"bug", "scoring", "feature", "general"}


@router.get("/feedback", response_class=HTMLResponse)
def feedback_page(request: Request):
    """Feedback submission page."""
    return templates.TemplateResponse("pages/feedback.html", {
        "request": request,
    })


@router.post("/feedback")
def submit_feedback(
    feedback_type: str = Form(...),
    message: str = Form(...),
    email: str = Form(""),
    db: Session = Depends(get_db),
):
    """Submit feedback."""
    message = message.strip()
    if not message or len(message) > 5000:
        return RedirectResponse("/feedback?submitted=invalid", status_code=303)

    if feedback_type not in _FEEDBACK_TYPES:
        feedback_type = "general"

    email_val = email.strip().lower() if email.strip() else None

    fb = Feedback(
        email=email_val,
        feedback_type=feedback_type,
        message=message[:5000],
    )
    db.add(fb)
    db.commit()
    return RedirectResponse("/feedback?submitted=ok", status_code=303)


# ── SEO ──────────────────────────────────────────────────────────────────────


ROBOTS_TXT = """\
User-agent: *
Allow: /

Sitemap: https://assay.tools/sitemap.xml
"""


@router.get("/robots.txt", response_class=PlainTextResponse)
def robots_txt():
    """Robots.txt for search engine crawlers."""
    return ROBOTS_TXT


@router.get("/sitemap.xml")
def sitemap_xml(db: Session = Depends(get_db)):
    """XML sitemap for search engine discovery."""
    base = "https://assay.tools"
    urls = []

    # Static pages
    for path, priority, freq in [
        ("/", "1.0", "daily"),
        ("/packages", "0.9", "daily"),
        ("/categories", "0.8", "weekly"),
        ("/compare", "0.6", "weekly"),
        ("/about", "0.5", "monthly"),
        ("/methodology", "0.6", "monthly"),
        ("/developers", "0.6", "monthly"),
        ("/contribute", "0.5", "monthly"),
        ("/feedback", "0.4", "monthly"),
        ("/terms", "0.3", "monthly"),
        ("/privacy", "0.3", "monthly"),
    ]:
        urls.append(
            f'  <url><loc>{base}{path}</loc>'
            f'<priority>{priority}</priority>'
            f'<changefreq>{freq}</changefreq></url>'
        )

    # Category pages
    categories = db.query(Category.slug).all()
    for (slug,) in categories:
        urls.append(
            f'  <url><loc>{base}/categories/{slug}</loc>'
            f'<priority>0.7</priority>'
            f'<changefreq>weekly</changefreq></url>'
        )

    # Package detail pages (evaluated only)
    packages = (
        db.query(Package.id, Package.last_evaluated)
        .filter(Package.af_score.isnot(None))
        .all()
    )
    for pkg_id, last_eval in packages:
        lastmod = ""
        if last_eval:
            lastmod = (
                f"<lastmod>{last_eval.strftime('%Y-%m-%d')}</lastmod>"
            )
        urls.append(
            f'  <url><loc>{base}/packages/{pkg_id}</loc>'
            f'{lastmod}'
            f'<priority>0.6</priority>'
            f'<changefreq>monthly</changefreq></url>'
        )

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>"
    )
    return Response(content=xml, media_type="application/xml")
