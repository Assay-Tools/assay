"""Assay MCP server implementation.

Exposes the Assay package directory as MCP tools so AI agents can
query package ratings, compare alternatives, and browse categories.
"""

import asyncio
import json

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from assay.database import SessionLocal, init_db
from assay.models.package import (
    Category,
    Package,
    PackageInterface,
    PackagePricing,
    ScoreSnapshot,
)

server = Server("assay")


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS = [
    types.Tool(
        name="find_packages",
        description=(
            "Search the Assay package directory by keyword, category, or filters. "
            "Use 'query' for text search across names, descriptions, and tags. "
            "Filter by category, MCP support, free tier, score thresholds, and package type. "
            "Results are sorted by the chosen dimension (default: AF score, highest first). "
            "Returns condensed agent-optimized records."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Text search across package name, description, and tags. "
                        "Example: 'email', 'payments', 'vector database'."
                    ),
                },
                "category": {
                    "type": "string",
                    "description": (
                        "Category slug to filter by. Use list_categories to see available slugs. "
                        "Examples: 'ai-ml', 'databases', 'communication', 'security'."
                    ),
                },
                "has_mcp": {
                    "type": "boolean",
                    "description": "If true, only return packages with an MCP server.",
                },
                "free_tier": {
                    "type": "boolean",
                    "description": "If true, only return packages that offer a free tier.",
                },
                "min_af_score": {
                    "type": "number",
                    "description": "Minimum agent-friendliness score (0-100).",
                },
                "min_security_score": {
                    "type": "number",
                    "description": "Minimum security score (0-100).",
                },
                "min_reliability_score": {
                    "type": "number",
                    "description": "Minimum reliability score (0-100).",
                },
                "package_type": {
                    "type": "string",
                    "description": "Filter by type: 'mcp_server', 'api', or 'skill'.",
                },
                "sort": {
                    "type": "string",
                    "description": (
                        "Sort dimension: 'af_score' (default), 'security_score', "
                        "'reliability_score', or 'name'."
                    ),
                    "default": "af_score",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results to return (default 10, max 50).",
                    "default": 10,
                },
                "offset": {
                    "type": "integer",
                    "description": "Number of results to skip for pagination (default 0).",
                    "default": 0,
                },
            },
            "additionalProperties": False,
        },
    ),
    types.Tool(
        name="get_package",
        description=(
            "Get the full detailed record for a single package by its ID. "
            "Includes interface, auth, pricing, performance, requirements, "
            "and agent-readiness details with known gotchas."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": "Package identifier (e.g. 'stripe-api', 'resend').",
                },
            },
            "required": ["id"],
            "additionalProperties": False,
        },
    ),
    types.Tool(
        name="compare_packages",
        description=(
            "Compare two or more packages side-by-side. Returns agent-optimized "
            "records for each package so you can evaluate trade-offs across "
            "AF score, security, reliability, pricing, and gotchas."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of package IDs to compare (2-5 packages).",
                    "minItems": 2,
                    "maxItems": 5,
                },
            },
            "required": ["ids"],
            "additionalProperties": False,
        },
    ),
    types.Tool(
        name="list_categories",
        description=(
            "List all available package categories with their descriptions "
            "and the number of evaluated packages in each. Use category slugs "
            "from this list when filtering with find_packages."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    ),
    types.Tool(
        name="get_score_history",
        description=(
            "Get score history for a package over time. Shows how AF, security, "
            "and reliability scores have changed across evaluations. Useful for "
            "determining if a package is improving or declining."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": "Package identifier.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max snapshots to return (default 20, max 100).",
                    "default": 20,
                },
            },
            "required": ["id"],
            "additionalProperties": False,
        },
    ),
    types.Tool(
        name="get_stats",
        description=(
            "Get sitewide statistics: total packages, evaluated count, "
            "score distribution, evaluation freshness, and category count. "
            "Useful for understanding Assay's coverage and data quality."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    ),
]


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return TOOLS


# ---------------------------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------------------------

def _eager_load_options():
    """Common eager-load options to avoid N+1 queries."""
    return [
        joinedload(Package.interface),
        joinedload(Package.auth),
        joinedload(Package.pricing),
        joinedload(Package.performance),
        joinedload(Package.requirements),
        joinedload(Package.agent_readiness),
        joinedload(Package.category),
    ]


SORTABLE_FIELDS = {"af_score", "security_score", "reliability_score", "name"}


def _handle_find_packages(arguments: dict) -> str:
    query_text = arguments.get("query")
    category = arguments.get("category")
    has_mcp = arguments.get("has_mcp")
    free_tier = arguments.get("free_tier")
    min_af_score = arguments.get("min_af_score")
    min_security_score = arguments.get("min_security_score")
    min_reliability_score = arguments.get("min_reliability_score")
    package_type = arguments.get("package_type")
    sort_field = arguments.get("sort", "af_score")
    limit = min(arguments.get("limit", 10), 50)
    offset = max(arguments.get("offset", 0), 0)

    if sort_field not in SORTABLE_FIELDS:
        return json.dumps({
            "error": f"Invalid sort field: {sort_field}. "
            f"Allowed: {', '.join(sorted(SORTABLE_FIELDS))}",
        })

    with SessionLocal() as db:
        query = db.query(Package).options(*_eager_load_options())

        # Text search
        if query_text:
            search_term = f"%{query_text}%"
            query = query.filter(
                or_(
                    Package.name.ilike(search_term),
                    Package.what_it_does.ilike(search_term),
                    Package.tags.ilike(search_term),
                )
            )

        if category:
            query = query.filter(Package.category_slug == category)
        if has_mcp is True:
            query = query.join(PackageInterface).filter(
                PackageInterface.has_mcp_server.is_(True)
            )
        if free_tier is True:
            query = query.join(PackagePricing).filter(
                PackagePricing.free_tier_exists.is_(True)
            )
        if min_af_score is not None:
            query = query.filter(Package.af_score >= min_af_score)
        if min_security_score is not None:
            query = query.filter(Package.security_score >= min_security_score)
        if min_reliability_score is not None:
            query = query.filter(Package.reliability_score >= min_reliability_score)
        if package_type:
            query = query.filter(Package.package_type == package_type)

        # Count before pagination
        total = query.count()

        # Sort
        column = getattr(Package, sort_field)
        if sort_field == "name":
            query = query.order_by(column.asc())
        else:
            query = query.order_by(column.desc().nulls_last())

        packages = query.offset(offset).limit(limit).all()
        results = [pkg.to_agent_guide() for pkg in packages]

    return json.dumps({
        "count": len(results),
        "total": total,
        "offset": offset,
        "limit": limit,
        "packages": results,
    }, indent=2)


def _handle_get_package(arguments: dict) -> str:
    pkg_id = arguments.get("id")
    if not pkg_id:
        return json.dumps({"error": "Missing required parameter: id"})

    with SessionLocal() as db:
        pkg = (
            db.query(Package)
            .options(*_eager_load_options())
            .filter(Package.id == pkg_id)
            .first()
        )
        if not pkg:
            return json.dumps({"error": f"Package '{pkg_id}' not found"})

        return json.dumps(pkg.to_dict(), indent=2)


def _handle_compare_packages(arguments: dict) -> str:
    ids = arguments.get("ids", [])
    if len(ids) < 2:
        return json.dumps({"error": "Provide at least 2 package IDs to compare"})
    if len(ids) > 5:
        return json.dumps({"error": "Compare at most 5 packages at a time"})

    with SessionLocal() as db:
        packages = (
            db.query(Package)
            .options(*_eager_load_options())
            .filter(Package.id.in_(ids))
            .all()
        )

        found_ids = {pkg.id for pkg in packages}
        missing = [pid for pid in ids if pid not in found_ids]

        result = {
            "packages": [pkg.to_agent_guide() for pkg in packages],
        }
        if missing:
            result["not_found"] = missing

    return json.dumps(result, indent=2)


def _handle_list_categories(arguments: dict) -> str:
    with SessionLocal() as db:
        categories = (
            db.query(Category)
            .order_by(Category.name)
            .all()
        )
        results = [cat.to_dict() for cat in categories]

    return json.dumps({"count": len(results), "categories": results}, indent=2)


def _handle_get_score_history(arguments: dict) -> str:
    pkg_id = arguments.get("id")
    if not pkg_id:
        return json.dumps({"error": "Missing required parameter: id"})

    limit = min(arguments.get("limit", 20), 100)

    with SessionLocal() as db:
        pkg = db.query(Package).filter(Package.id == pkg_id).first()
        if not pkg:
            return json.dumps({"error": f"Package '{pkg_id}' not found"})

        snapshots = (
            db.query(ScoreSnapshot)
            .filter(ScoreSnapshot.package_id == pkg_id)
            .order_by(ScoreSnapshot.recorded_at.desc())
            .limit(limit)
            .all()
        )

        result = {
            "package_id": pkg_id,
            "package_name": pkg.name,
            "current_scores": {
                "af": pkg.af_score,
                "security": pkg.security_score,
                "reliability": pkg.reliability_score,
            },
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

    return json.dumps(result, indent=2)


def _handle_get_stats(arguments: dict) -> str:
    from sqlalchemy import func as sqlfunc

    with SessionLocal() as db:
        total = db.query(Package).count()
        evaluated = db.query(Package).filter(Package.af_score.isnot(None)).count()
        categories = db.query(Category).count()

        avg_af = db.query(sqlfunc.avg(Package.af_score)).scalar()

        # Score distribution
        excellent = db.query(Package).filter(Package.af_score >= 80).count()
        good = db.query(Package).filter(
            Package.af_score >= 60, Package.af_score < 80,
        ).count()
        fair = db.query(Package).filter(
            Package.af_score > 0, Package.af_score < 60,
        ).count()

    return json.dumps({
        "total_packages": total,
        "total_evaluated": evaluated,
        "total_categories": categories,
        "avg_af_score": round(avg_af, 1) if avg_af else None,
        "score_distribution": {
            "excellent_80_plus": excellent,
            "good_60_to_79": good,
            "below_60": fair,
            "unrated": total - evaluated,
        },
    }, indent=2)


_HANDLERS = {
    "find_packages": _handle_find_packages,
    "get_package": _handle_get_package,
    "compare_packages": _handle_compare_packages,
    "list_categories": _handle_list_categories,
    "get_score_history": _handle_get_score_history,
    "get_stats": _handle_get_stats,
}


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    handler = _HANDLERS.get(name)
    if not handler:
        return [
            types.TextContent(
                type="text",
                text=json.dumps({"error": f"Unknown tool: {name}"}),
            )
        ]

    try:
        # Run synchronous DB queries in a thread to keep the event loop free
        result = await asyncio.to_thread(handler, arguments)
    except Exception as e:
        result = json.dumps({"error": str(e)})

    return [types.TextContent(type="text", text=result)]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    """Run the Assay MCP server over stdio."""
    init_db()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
