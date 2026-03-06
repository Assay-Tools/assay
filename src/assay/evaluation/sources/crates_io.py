"""crates.io discovery source — finds MCP server crates on crates.io."""

from __future__ import annotations

import re
import time

import httpx

from .base import DiscoveredPackage, DiscoverySource


def _slug_from_crate(name: str) -> str:
    """Generate a package ID slug from a crate name.

    Crate names are globally unique on crates.io, so we use
    the name directly after sanitizing.
    """
    slug = re.sub(r"[^a-z0-9-]", "-", name.lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:255]


class CratesIoSource(DiscoverySource):
    """Discovers MCP server crates from crates.io."""

    SEARCH_QUERIES = [
        "mcp server",
        "mcp-server",
        "model-context-protocol",
        "mcp",
    ]

    CRATES_API = "https://crates.io/api/v1/crates"
    REQUEST_DELAY_SECONDS = 1.0
    USER_AGENT = "assay-discovery (https://assay.tools)"

    @property
    def source_name(self) -> str:
        return "crates_io"

    def discover(self, limit: int = 500) -> list[DiscoveredPackage]:
        """Search crates.io for MCP server crates."""
        results: list[DiscoveredPackage] = []
        seen_names: set[str] = set()
        client = httpx.Client(
            timeout=30.0,
            headers={"User-Agent": self.USER_AGENT},
        )

        try:
            for query in self.SEARCH_QUERIES:
                if len(results) >= limit:
                    break
                self._run_query(client, query, limit, results, seen_names)
        finally:
            client.close()

        print(f"  [crates_io] Discovered {len(results)} packages.")
        return results[:limit]

    def _run_query(
        self,
        client: httpx.Client,
        query: str,
        limit: int,
        results: list[DiscoveredPackage],
        seen_names: set[str],
    ) -> None:
        page = 1
        per_page = 100

        while len(results) < limit:
            print(f"  [crates_io] Searching: q={query} page={page} ...")

            try:
                resp = client.get(
                    self.CRATES_API,
                    params={
                        "q": query,
                        "per_page": per_page,
                        "page": page,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPError as exc:
                print(f"  [crates_io] HTTP error: {exc}")
                break

            crates = data.get("crates", [])
            if not crates:
                break

            for crate in crates:
                if len(results) >= limit:
                    break

                name = crate.get("name", "")
                if not name or name in seen_names:
                    continue
                seen_names.add(name)

                pkg_id = _slug_from_crate(name)
                if not pkg_id:
                    continue

                description = crate.get("description") or ""
                if len(description) > 500:
                    description = description[:500]

                keywords = crate.get("keywords", []) or []

                pkg = DiscoveredPackage(
                    id=pkg_id,
                    name=name,
                    repo_url=crate.get("repository"),
                    homepage=crate.get("homepage"),
                    description=description or None,
                    topics=keywords,
                    stars=0,
                    last_active=crate.get("updated_at"),
                    package_type="mcp_server",
                    discovery_source="crates_io",
                )
                results.append(pkg)

            total = data.get("meta", {}).get("total", 0)
            fetched = page * per_page
            if fetched >= total or len(crates) < per_page:
                break

            page += 1
            time.sleep(self.REQUEST_DELAY_SECONDS)

        time.sleep(self.REQUEST_DELAY_SECONDS)
