"""npm registry discovery source — finds MCP server packages on npm."""

from __future__ import annotations

import re
import time

import httpx

from .base import DiscoveredPackage, DiscoverySource


def _slug_from_npm(name: str) -> str:
    """Generate a package ID slug from an npm package name.

    Uses 'scope--package-name' format for scoped packages to avoid
    collisions (e.g., @anthropic/mcp-server -> anthropic--mcp-server).
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


class NpmSource(DiscoverySource):
    """Discovers MCP server packages from the npm registry."""

    SEARCH_QUERIES = [
        "mcp-server",
        "mcp server",
        "model-context-protocol",
        "@modelcontextprotocol",
        "keywords:mcp-server",
        "keywords:model-context-protocol",
        "@anthropic mcp",
        "fastmcp",
        "mcp-tool",
        "mcp plugin server",
    ]

    NPM_SEARCH = "https://registry.npmjs.org/-/v1/search"
    REQUEST_DELAY_SECONDS = 1.0

    @property
    def source_name(self) -> str:
        return "npm"

    def discover(self, limit: int = 500) -> list[DiscoveredPackage]:
        """Search npm for MCP server packages."""
        results: list[DiscoveredPackage] = []
        seen_ids: set[str] = set()
        client = httpx.Client(timeout=30.0)

        try:
            for query in self.SEARCH_QUERIES:
                if len(results) >= limit:
                    break
                self._run_query(
                    client, query, limit, results, seen_ids,
                )
        finally:
            client.close()

        print(f"  [npm] Discovered {len(results)} packages.")
        return results[:limit]

    def _run_query(
        self,
        client: httpx.Client,
        query: str,
        limit: int,
        results: list[DiscoveredPackage],
        seen_ids: set[str],
    ) -> None:
        offset = 0
        per_page = 250  # npm max

        while len(results) < limit:
            print(f"  [npm] Searching: q={query} offset={offset} ...")

            try:
                resp = client.get(
                    self.NPM_SEARCH,
                    params={
                        "text": query,
                        "size": per_page,
                        "from": offset,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPError as exc:
                print(f"  [npm] HTTP error: {exc}")
                break

            objects = data.get("objects", [])
            if not objects:
                break

            for obj in objects:
                if len(results) >= limit:
                    break

                pkg_data = obj.get("package", {})
                name = pkg_data.get("name", "")
                pkg_id = _slug_from_npm(name)

                if not pkg_id or pkg_id in seen_ids:
                    continue
                seen_ids.add(pkg_id)

                # Extract repo URL from links
                links = pkg_data.get("links", {})
                repo_url = links.get("repository") or links.get("homepage")

                pkg = DiscoveredPackage(
                    id=pkg_id,
                    name=name,
                    repo_url=repo_url,
                    homepage=links.get("homepage"),
                    description=(pkg_data.get("description") or "")[:500] or None,
                    topics=pkg_data.get("keywords", []),
                    stars=0,
                    last_active=pkg_data.get("date"),
                    package_type="mcp_server",
                    discovery_source="npm",
                )
                results.append(pkg)

            total = data.get("total", 0)
            offset += per_page
            if offset >= total or len(objects) < per_page:
                break

            time.sleep(self.REQUEST_DELAY_SECONDS)

        time.sleep(self.REQUEST_DELAY_SECONDS)
