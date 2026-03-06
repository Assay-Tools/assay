"""Glama.ai registry discovery source — finds MCP servers from Glama.

Glama.ai has ~18,000+ MCP servers indexed. The site uses React Server Components
without a public JSON API, so we paginate through the HTML listing pages and
extract server data from embedded JSON-LD schema.org markup.
"""

from __future__ import annotations

import json
import re
import time

import httpx

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


def _slug_from_url(url: str) -> str:
    """Generate a slug from a Glama server detail URL like /mcp/servers/@org/name."""
    path = url.rstrip("/").split("/mcp/servers/")[-1] if "/mcp/servers/" in url else url
    return _slug_from_name(path)


class GlamaSource(DiscoverySource):
    """Discovers MCP servers from Glama.ai by scraping listing pages.

    Paginates through https://glama.ai/mcp/servers?page=N and extracts
    server entries from JSON-LD schema.org ItemList markup or from
    HTML link patterns.
    """

    BASE_URL = "https://glama.ai/mcp/servers"
    REQUEST_DELAY_SECONDS = 1.0

    @property
    def source_name(self) -> str:
        return "glama"

    def discover(self, limit: int = 500) -> list[DiscoveredPackage]:
        """Scrape Glama.ai listing pages for MCP servers."""
        results: list[DiscoveredPackage] = []
        seen_ids: set[str] = set()

        client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": "assay-discovery (https://assay.tools)"},
        )

        try:
            page = 1
            consecutive_empty = 0

            while len(results) < limit:
                print(f"  [glama] Fetching page {page} ...")

                try:
                    resp = client.get(self.BASE_URL, params={"page": page})
                    resp.raise_for_status()
                    html = resp.text
                except httpx.HTTPError as exc:
                    print(f"  [glama] HTTP error on page {page}: {exc}")
                    break

                page_packages = self._extract_from_jsonld(html, seen_ids)

                if not page_packages:
                    # Fall back to link extraction
                    page_packages = self._extract_from_links(html, seen_ids)

                if not page_packages:
                    consecutive_empty += 1
                    if consecutive_empty >= 2:
                        print("  [glama] No more results found, stopping.")
                        break
                else:
                    consecutive_empty = 0

                results.extend(page_packages)
                page += 1
                time.sleep(self.REQUEST_DELAY_SECONDS)

        finally:
            client.close()

        print(f"  [glama] Discovered {len(results)} packages.")
        return results[:limit]

    def _extract_from_jsonld(
        self, html: str, seen_ids: set[str]
    ) -> list[DiscoveredPackage]:
        """Extract server entries from JSON-LD schema.org markup."""
        packages: list[DiscoveredPackage] = []

        # Find all JSON-LD script blocks
        for match in re.finditer(
            r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
            html,
            re.DOTALL,
        ):
            try:
                data = json.loads(match.group(1))
            except (json.JSONDecodeError, ValueError):
                continue

            # Look for ItemList with SoftwareApplication entries
            items = []
            if isinstance(data, dict):
                if data.get("@type") == "ItemList":
                    items = data.get("itemListElement", [])
                elif data.get("@type") == "SearchResultsPage":
                    main_entity = data.get("mainEntity", {})
                    items = main_entity.get("itemListElement", [])

            for item in items:
                entry = item.get("item", item)
                if not isinstance(entry, dict):
                    continue

                name = entry.get("name", "")
                url = entry.get("url", "")
                if not name and not url:
                    continue

                pkg_id = _slug_from_url(url) if url else _slug_from_name(name)
                if not pkg_id or pkg_id in seen_ids:
                    continue
                seen_ids.add(pkg_id)

                packages.append(DiscoveredPackage(
                    id=pkg_id,
                    name=name or pkg_id,
                    repo_url=entry.get("codeRepository"),
                    homepage=url or None,
                    description=(entry.get("description") or "")[:500] or None,
                    topics=[],
                    stars=0,
                    package_type="mcp_server",
                    discovery_source="glama",
                ))

        return packages

    def _extract_from_links(
        self, html: str, seen_ids: set[str]
    ) -> list[DiscoveredPackage]:
        """Fall back to extracting server links from HTML."""
        packages: list[DiscoveredPackage] = []

        # Match links to individual server pages: /mcp/servers/@scope/name or /mcp/servers/name
        for match in re.finditer(
            r'href="(/mcp/servers/(@?[a-zA-Z0-9_-]+(/[a-zA-Z0-9_.-]+)?))"',
            html,
        ):
            path = match.group(2)
            if path in ("feeds", "new", "popular", "trending"):
                continue

            pkg_id = _slug_from_name(path)
            if not pkg_id or pkg_id in seen_ids:
                continue
            seen_ids.add(pkg_id)

            packages.append(DiscoveredPackage(
                id=pkg_id,
                name=path.split("/")[-1] if "/" in path else path,
                repo_url=None,
                homepage=f"https://glama.ai/mcp/servers/{path}",
                description=None,
                topics=[],
                stars=0,
                package_type="mcp_server",
                discovery_source="glama",
            ))

        return packages
