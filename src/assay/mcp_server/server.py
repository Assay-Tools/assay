"""Assay MCP server implementation.

Exposes the Assay package directory as MCP tools so AI agents can
query package ratings, compare alternatives, and browse categories.
"""

import asyncio
import json

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server
from sqlalchemy.orm import joinedload

from assay.database import SessionLocal, init_db
from assay.models.package import Category, Package, PackageInterface, PackagePricing

server = Server("assay")


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS = [
    types.Tool(
        name="find_packages",
        description=(
            "Search the Assay package directory. Filter by category, MCP support, "
            "free tier availability, and minimum agent-friendliness score. "
            "Returns condensed agent-optimized records."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Category slug to filter by (e.g. 'email', 'database').",
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
                "limit": {
                    "type": "integer",
                    "description": "Max results to return (default 10, max 50).",
                    "default": 10,
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
            "and agent-readiness details."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": "Package identifier (e.g. 'resend', 'stripe').",
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
            "records for each package so you can evaluate trade-offs."
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
            "and the number of packages in each."
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


def _handle_find_packages(arguments: dict) -> str:
    category = arguments.get("category")
    has_mcp = arguments.get("has_mcp")
    free_tier = arguments.get("free_tier")
    min_af_score = arguments.get("min_af_score")
    limit = min(arguments.get("limit", 10), 50)

    with SessionLocal() as db:
        query = db.query(Package).options(*_eager_load_options())

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

        # Order by af_score descending (best first), nulls last
        query = query.order_by(Package.af_score.desc().nulls_last())
        packages = query.limit(limit).all()

        results = [pkg.to_agent_guide() for pkg in packages]

    return json.dumps({"count": len(results), "packages": results}, indent=2)


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


_HANDLERS = {
    "find_packages": _handle_find_packages,
    "get_package": _handle_get_package,
    "compare_packages": _handle_compare_packages,
    "list_categories": _handle_list_categories,
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
