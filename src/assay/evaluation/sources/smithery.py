"""Smithery.ai registry discovery source — finds MCP servers from Smithery."""

from __future__ import annotations

import re
import time

import httpx

from assay.config import settings

from .base import DiscoveredPackage, DiscoverySource


def _slug_from_name(name: str) -> str:
    """Generate a package ID slug from a Smithery server name.

    Includes scope to avoid collisions (e.g., '@scope/name' -> 'scope--name').
    """
    if "/" in name:
        scope, pkg = name.split("/", 1)
        scope = scope.lstrip("@")
        raw = f"{scope}--{pkg}"
    else:
        raw = name
    slug = re.sub(r"[^a-z0-9-]", "-", raw.lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:255]


class SmitherySource(DiscoverySource):
    """Discovers MCP servers from the Smithery.ai registry.

    Requires SMITHERY_TOKEN env var for authentication.
    If no token is set, discovery is skipped gracefully.
    """

    REGISTRY_API = "https://registry.smithery.ai/servers"
    REQUEST_DELAY_SECONDS = 1.0

    @property
    def source_name(self) -> str:
        return "smithery"

    def discover(self, limit: int = 500) -> list[DiscoveredPackage]:
        """Fetch MCP servers from Smithery registry."""
        token = getattr(settings, "smithery_token", "")
        if not token:
            print(
                "  [smithery] No SMITHERY_TOKEN set — skipping. "
                "Get a token at smithery.ai to enable."
            )
            return []

        results: list[DiscoveredPackage] = []
        seen_ids: set[str] = set()
        client = httpx.Client(
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
            timeout=30.0,
        )

        try:
            page = 1
            page_size = 100

            while len(results) < limit:
                print(f"  [smithery] Fetching page {page} ...")

                try:
                    resp = client.get(
                        self.REGISTRY_API,
                        params={
                            "pageSize": page_size,
                            "page": page,
                        },
                    )
                    if resp.status_code == 401:
                        print("  [smithery] Invalid token — skipping.")
                        break
                    resp.raise_for_status()
                    data = resp.json()
                except httpx.HTTPError as exc:
                    print(f"  [smithery] HTTP error: {exc}")
                    break

                servers = data.get("servers", data) if isinstance(data, dict) else data
                if not servers or not isinstance(servers, list):
                    break

                for server in servers:
                    if len(results) >= limit:
                        break

                    name = server.get("qualifiedName") or server.get("name", "")
                    pkg_id = _slug_from_name(name)
                    if not pkg_id or pkg_id in seen_ids:
                        continue
                    seen_ids.add(pkg_id)

                    # Extract repo URL if available
                    repo_url = server.get("repository") or server.get("homepage")

                    pkg = DiscoveredPackage(
                        id=pkg_id,
                        name=server.get("displayName") or name,
                        repo_url=repo_url,
                        homepage=server.get("homepage"),
                        description=(server.get("description") or "")[:500] or None,
                        topics=[],
                        stars=0,
                        last_active=server.get("updatedAt") or server.get("createdAt"),
                        package_type="mcp_server",
                        discovery_source="smithery",
                    )
                    results.append(pkg)

                if len(servers) < page_size:
                    break

                page += 1
                time.sleep(self.REQUEST_DELAY_SECONDS)

        finally:
            client.close()

        print(f"  [smithery] Discovered {len(results)} packages.")
        return results[:limit]
