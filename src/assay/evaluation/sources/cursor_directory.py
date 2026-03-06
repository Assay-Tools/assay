"""Cursor Directory discovery source — finds MCP servers from cursor.directory."""

from __future__ import annotations

import json
import re
import time

import httpx

from .base import DiscoveredPackage, DiscoverySource


def _slug_from_github_url(url: str) -> str | None:
    """Extract 'owner--name' slug from a GitHub URL, or return None."""
    match = re.match(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", url)
    if match:
        owner, name = match.group(1), match.group(2)
        return f"{owner}--{name}".lower()
    return None


def _slug_from_name(name: str) -> str:
    """Generate a package ID slug from a display name."""
    slug = re.sub(r"[^a-z0-9-]", "-", name.lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:255]


class CursorDirectorySource(DiscoverySource):
    """Discovers MCP servers from the Cursor Directory.

    Tries the JSON API first, then falls back to scraping __NEXT_DATA__
    from the HTML page (standard Next.js pattern).
    """

    API_URL = "https://cursor.directory/api/mcp"
    PAGE_URL = "https://cursor.directory/mcp"
    REQUEST_DELAY_SECONDS = 1.0

    @property
    def source_name(self) -> str:
        return "cursor_directory"

    def discover(self, limit: int = 500) -> list[DiscoveredPackage]:
        """Fetch MCP servers from Cursor Directory."""
        results: list[DiscoveredPackage] = []
        seen_ids: set[str] = set()

        client = httpx.Client(timeout=30.0)

        try:
            servers = self._try_api(client) or self._try_html_fallback(client)

            if not servers:
                print("  [cursor_directory] No servers found from API or HTML fallback.")
                return []

            for server in servers:
                if len(results) >= limit:
                    break

                name = server.get("name", "")
                if not name:
                    continue

                # Build slug: prefer GitHub URL-based, fall back to name
                repo_url = server.get("url") or server.get("repo_url") or server.get("repository")
                slug = None
                if repo_url:
                    slug = _slug_from_github_url(repo_url)
                if not slug:
                    slug = _slug_from_name(name)

                if not slug or slug in seen_ids:
                    continue
                seen_ids.add(slug)

                # Build cursor.directory page URL
                server_slug = server.get("slug") or server.get("id") or ""
                homepage = f"https://cursor.directory/mcp/{server_slug}" if server_slug else self.PAGE_URL

                description = (server.get("description") or "")[:500] or None

                pkg = DiscoveredPackage(
                    id=slug,
                    name=name,
                    repo_url=repo_url,
                    homepage=homepage,
                    description=description,
                    topics=[],
                    stars=0,
                    package_type="mcp_server",
                    discovery_source="cursor_directory",
                )
                results.append(pkg)

        finally:
            client.close()

        print(f"  [cursor_directory] Discovered {len(results)} packages.")
        return results[:limit]

    def _try_api(self, client: httpx.Client) -> list[dict] | None:
        """Try fetching from the JSON API endpoint."""
        print("  [cursor_directory] Trying API endpoint ...")
        try:
            resp = client.get(self.API_URL)
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            print(f"  [cursor_directory] API not available: {exc}")
            return None

        # Handle both list and dict-wrapped responses
        if isinstance(data, list):
            servers = data
        elif isinstance(data, dict):
            servers = data.get("mcps") or data.get("servers") or data.get("data") or []
        else:
            return None

        if not servers:
            print("  [cursor_directory] API returned empty result.")
            return None

        print(f"  [cursor_directory] API returned {len(servers)} servers.")
        time.sleep(self.REQUEST_DELAY_SECONDS)
        return servers

    def _try_html_fallback(self, client: httpx.Client) -> list[dict] | None:
        """Fall back to extracting __NEXT_DATA__ JSON from the HTML page."""
        print("  [cursor_directory] Falling back to HTML scraping ...")
        try:
            resp = client.get(self.PAGE_URL)
            resp.raise_for_status()
            html = resp.text
        except httpx.HTTPError as exc:
            print(f"  [cursor_directory] HTML fetch failed: {exc}")
            return None

        # Extract __NEXT_DATA__ JSON from Next.js page
        pattern = r'<script\s+id="__NEXT_DATA__"\s+type="application/json">\s*({.*?})\s*</script>'
        match = re.search(pattern, html, re.DOTALL)
        if not match:
            print("  [cursor_directory] No __NEXT_DATA__ found in HTML.")
            return None

        try:
            next_data = json.loads(match.group(1))
        except json.JSONDecodeError as exc:
            print(f"  [cursor_directory] Failed to parse __NEXT_DATA__: {exc}")
            return None

        # Navigate the Next.js data structure to find server list
        page_props = next_data.get("props", {}).get("pageProps", {})
        servers = (
            page_props.get("mcps")
            or page_props.get("servers")
            or page_props.get("data")
            or []
        )

        if not servers:
            print("  [cursor_directory] No servers found in __NEXT_DATA__.")
            return None

        print(f"  [cursor_directory] HTML fallback found {len(servers)} servers.")
        time.sleep(self.REQUEST_DELAY_SECONDS)
        return servers
