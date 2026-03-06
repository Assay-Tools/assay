"""MCP Registry discovery source — official registry at registry.modelcontextprotocol.io."""

from __future__ import annotations

import re
import time

import httpx

from .base import DiscoveredPackage, DiscoverySource


def _slug_from_name(name: str) -> str:
    """Generate a package ID slug from a registry server name.

    Includes namespace to avoid collisions (e.g. 'ai.foo/bar' -> 'ai-foo--bar').
    """
    if "/" in name:
        parts = name.split("/", 1)
        raw = f"{parts[0]}--{parts[1]}"
    else:
        raw = name
    slug = re.sub(r"[^a-z0-9-]", "-", raw.lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:255]


class MCPRegistrySource(DiscoverySource):
    """Discovers MCP servers from the official MCP Registry."""

    API_BASE = "https://registry.modelcontextprotocol.io/v0.1/servers"
    PAGE_SIZE = 96
    REQUEST_DELAY_SECONDS = 1.0  # Registry is generous, light delay

    @property
    def source_name(self) -> str:
        return "mcp_registry"

    def discover(self, limit: int = 500) -> list[DiscoveredPackage]:
        """Fetch servers from MCP Registry with cursor-based pagination."""
        results: list[DiscoveredPackage] = []
        cursor: str | None = None
        seen_ids: set[str] = set()

        client = httpx.Client(timeout=30.0)

        try:
            while len(results) < limit:
                params: dict[str, str | int] = {
                    "limit": min(self.PAGE_SIZE, limit - len(results)),
                    "version": "latest",
                }
                if cursor:
                    params["cursor"] = cursor

                print(f"  [mcp_registry] Fetching page (cursor={cursor or 'start'}) ...")

                try:
                    resp = client.get(self.API_BASE, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                except httpx.HTTPError as exc:
                    print(f"  [mcp_registry] HTTP error: {exc}")
                    break

                servers = data.get("servers", [])
                if not servers:
                    break

                for entry in servers:
                    server = entry.get("server", entry)
                    name = server.get("name", "")
                    pkg_id = _slug_from_name(name)

                    if pkg_id in seen_ids or not pkg_id:
                        continue
                    seen_ids.add(pkg_id)

                    # Extract repo URL from repository field
                    repo_info = server.get("repository", {})
                    repo_url = repo_info.get("url") if isinstance(repo_info, dict) else None

                    pkg = DiscoveredPackage(
                        id=pkg_id,
                        name=server.get("title") or name.split("/")[-1] if "/" in name else name,
                        repo_url=repo_url,
                        homepage=server.get("websiteUrl"),
                        description=server.get("description"),
                        topics=[],
                        stars=0,  # Registry doesn't provide star counts
                        last_active=None,
                        package_type="mcp_server",
                        discovery_source="mcp_registry",
                    )
                    results.append(pkg)

                    if len(results) >= limit:
                        break

                # Pagination
                metadata = data.get("metadata", {})
                next_cursor = metadata.get("nextCursor")
                if not next_cursor or next_cursor == cursor:
                    break
                cursor = next_cursor

                time.sleep(self.REQUEST_DELAY_SECONDS)

        finally:
            client.close()

        print(f"  [mcp_registry] Discovered {len(results)} servers.")
        return results
