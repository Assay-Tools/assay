"""Glama.ai registry discovery source — finds MCP servers from Glama."""

from __future__ import annotations

import re
import time

import httpx

from assay.config import settings

from .base import DiscoveredPackage, DiscoverySource


def _slug_from_name(name: str) -> str:
    """Generate a package ID slug from a Glama server name.

    Uses namespace--name if namespaced (e.g., 'org/tool' -> 'org--tool'),
    otherwise just the name.
    """
    if "/" in name:
        namespace, pkg = name.split("/", 1)
        namespace = namespace.lstrip("@")
        raw = f"{namespace}--{pkg}"
    else:
        raw = name
    slug = re.sub(r"[^a-z0-9-]", "-", raw.lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:255]


class GlamaSource(DiscoverySource):
    """Discovers MCP servers from the Glama.ai registry.

    Uses the Glama public API. If GLAMA_TOKEN is set it will be sent
    as a Bearer token; otherwise requests are made unauthenticated.
    """

    REGISTRY_API = "https://glama.ai/api/mcp/servers"
    REQUEST_DELAY_SECONDS = 1.0

    @property
    def source_name(self) -> str:
        return "glama"

    def discover(self, limit: int = 500) -> list[DiscoveredPackage]:
        """Fetch MCP servers from Glama registry."""
        results: list[DiscoveredPackage] = []
        seen_ids: set[str] = set()

        headers: dict[str, str] = {"Accept": "application/json"}
        token = getattr(settings, "glama_token", "")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        client = httpx.Client(headers=headers, timeout=30.0)

        try:
            page = 1
            page_size = 100
            cursor: str | None = None

            while len(results) < limit:
                print(f"  [glama] Fetching page {page} ...")

                params: dict[str, str | int] = {"pageSize": page_size}
                # Support both page-based and cursor-based pagination
                if cursor:
                    params["cursor"] = cursor
                else:
                    params["page"] = page

                try:
                    resp = client.get(self.REGISTRY_API, params=params)
                    if resp.status_code == 401:
                        print("  [glama] Unauthorized — skipping.")
                        break
                    if resp.status_code == 403:
                        print("  [glama] Forbidden — token may be invalid, skipping.")
                        break
                    resp.raise_for_status()
                    data = resp.json()
                except httpx.HTTPError as exc:
                    print(f"  [glama] HTTP error: {exc}")
                    break

                # Handle various response shapes
                if isinstance(data, dict):
                    servers = (
                        data.get("servers")
                        or data.get("data")
                        or data.get("items")
                        or data.get("results")
                        or []
                    )
                    # Check for cursor-based pagination token
                    cursor = data.get("nextCursor") or data.get("cursor") or None
                elif isinstance(data, list):
                    servers = data
                    cursor = None
                else:
                    break

                if not servers or not isinstance(servers, list):
                    break

                for server in servers:
                    if len(results) >= limit:
                        break

                    name = (
                        server.get("qualifiedName")
                        or server.get("name")
                        or server.get("id")
                        or ""
                    )
                    if not name:
                        continue

                    pkg_id = _slug_from_name(name)
                    if not pkg_id or pkg_id in seen_ids:
                        continue
                    seen_ids.add(pkg_id)

                    # Extract repo URL if available
                    repo_url = (
                        server.get("repository")
                        or server.get("repositoryUrl")
                        or server.get("repo_url")
                    )

                    homepage = (
                        server.get("homepage")
                        or server.get("websiteUrl")
                        or server.get("url")
                    )

                    stars = server.get("stars") or server.get("stargazers_count") or 0

                    pkg = DiscoveredPackage(
                        id=pkg_id,
                        name=server.get("displayName") or server.get("title") or name,
                        repo_url=repo_url,
                        homepage=homepage,
                        description=(server.get("description") or "")[:500] or None,
                        topics=[],
                        stars=int(stars),
                        last_active=server.get("updatedAt") or server.get("createdAt"),
                        package_type="mcp_server",
                        discovery_source="glama",
                    )
                    results.append(pkg)

                # Stop if we got fewer results than requested (last page)
                if len(servers) < page_size:
                    break

                # If no cursor returned, fall back to page-based
                if not cursor:
                    page += 1

                time.sleep(self.REQUEST_DELAY_SECONDS)

        finally:
            client.close()

        print(f"  [glama] Discovered {len(results)} packages.")
        return results[:limit]
