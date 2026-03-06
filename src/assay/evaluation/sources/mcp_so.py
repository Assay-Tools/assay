"""mcp.so discovery source — finds MCP servers from mcp.so marketplace."""

from __future__ import annotations

import json
import re
import time

import httpx

from .base import DiscoveredPackage, DiscoverySource


def _slug_from_name(name: str) -> str:
    """Generate a package ID slug from a server name.

    Includes namespace to avoid collisions (e.g. '@scope/name' -> 'scope--name').
    """
    if "/" in name:
        parts = name.split("/", 1)
        scope = parts[0].lstrip("@")
        raw = f"{scope}--{parts[1]}"
    else:
        raw = name
    slug = re.sub(r"[^a-z0-9-]", "-", raw.lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:255]


class MCPSoSource(DiscoverySource):
    """Discovers MCP servers from mcp.so marketplace.

    mcp.so is a Next.js site listing ~18K+ MCP servers.
    Tries JSON API first, then falls back to HTML scraping.
    No authentication required.
    """

    API_CANDIDATES = [
        "https://mcp.so/api/servers",
        "https://mcp.so/api/v1/servers",
        "https://mcp.so/api/search?q=",
        "https://mcp.so/api/servers?page=1&limit=100",
    ]
    HTML_URLS = [
        "https://mcp.so/servers",
        "https://mcp.so",
    ]
    REQUEST_DELAY_SECONDS = 1.0

    @property
    def source_name(self) -> str:
        return "mcp_so"

    def discover(self, limit: int = 500) -> list[DiscoveredPackage]:
        """Fetch MCP servers from mcp.so."""
        client = httpx.Client(timeout=30.0, follow_redirects=True)

        try:
            # Strategy 1: Try JSON API endpoints
            results = self._try_api(client, limit)
            if results:
                return results[:limit]

            # Strategy 2: Fall back to HTML scraping
            results = self._try_html_scraping(client, limit)
            if results:
                return results[:limit]

            print("  [mcp_so] No data found via API or HTML scraping.")
            return []

        finally:
            client.close()

    def _try_api(self, client: httpx.Client, limit: int) -> list[DiscoveredPackage]:
        """Try known API endpoints for JSON data."""
        for url in self.API_CANDIDATES:
            print(f"  [mcp_so] Trying API: {url} ...")
            try:
                resp = client.get(url)
                if resp.status_code == 404:
                    continue
                resp.raise_for_status()

                content_type = resp.headers.get("content-type", "")
                if "json" not in content_type and "text/html" in content_type:
                    # Got HTML back, not JSON — skip to scraping
                    continue

                data = resp.json()
                servers = self._extract_server_list(data)
                if servers:
                    print(f"  [mcp_so] API returned {len(servers)} entries.")
                    return self._parse_servers(servers, limit)
            except (httpx.HTTPError, json.JSONDecodeError) as exc:
                print(f"  [mcp_so] API {url} failed: {exc}")
                continue
            time.sleep(self.REQUEST_DELAY_SECONDS)

        print("  [mcp_so] No working API endpoint found.")
        return []

    def _try_html_scraping(self, client: httpx.Client, limit: int) -> list[DiscoveredPackage]:
        """Fall back to HTML scraping — look for embedded JSON data."""
        for url in self.HTML_URLS:
            print(f"  [mcp_so] Trying HTML scrape: {url} ...")
            try:
                resp = client.get(url)
                if resp.status_code >= 400:
                    continue
                html = resp.text

                # Try __NEXT_DATA__ (Next.js pages)
                servers = self._extract_next_data(html)
                if servers:
                    print(f"  [mcp_so] Extracted {len(servers)} servers from __NEXT_DATA__.")
                    return self._parse_servers(servers, limit)

                # Try React Server Components streaming data
                servers = self._extract_rsc_data(html)
                if servers:
                    print(f"  [mcp_so] Extracted {len(servers)} servers from RSC data.")
                    return self._parse_servers(servers, limit)

                # Try generic JSON blobs that look like server lists
                servers = self._extract_json_blobs(html)
                if servers:
                    print(f"  [mcp_so] Extracted {len(servers)} servers from embedded JSON.")
                    return self._parse_servers(servers, limit)

            except httpx.HTTPError as exc:
                print(f"  [mcp_so] HTML fetch {url} failed: {exc}")
                continue
            time.sleep(self.REQUEST_DELAY_SECONDS)

        print("  [mcp_so] HTML scraping found no server data.")
        return []

    def _extract_next_data(self, html: str) -> list[dict]:
        """Extract server data from __NEXT_DATA__ script tag."""
        match = re.search(
            r'<script\s+id="__NEXT_DATA__"\s+type="application/json">(.*?)</script>',
            html,
            re.DOTALL,
        )
        if not match:
            return []

        try:
            data = json.loads(match.group(1))
            # Navigate common Next.js data shapes
            props = data.get("props", {}).get("pageProps", {})
            for key in ("servers", "items", "tools", "data", "results", "list"):
                candidate = props.get(key)
                if isinstance(candidate, list) and len(candidate) > 0:
                    return candidate
            # Check nested structures
            for value in props.values():
                if isinstance(value, dict):
                    for key in ("servers", "items", "tools", "data", "results", "list"):
                        candidate = value.get(key)
                        if isinstance(candidate, list) and len(candidate) > 0:
                            return candidate
        except (json.JSONDecodeError, AttributeError):
            pass
        return []

    def _extract_rsc_data(self, html: str) -> list[dict]:
        """Extract server data from React Server Components streaming format.

        RSC responses embed JSON payloads in script tags or inline data.
        """
        servers: list[dict] = []

        # Look for self.__next_f.push style data (App Router RSC)
        for match in re.finditer(r'self\.__next_f\.push\(\[.*?,(.*?)\]\)', html, re.DOTALL):
            try:
                payload = match.group(1).strip().strip('"')
                # Unescape the JSON string
                payload = payload.replace('\\"', '"').replace("\\n", "\n")
                data = json.loads(payload)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and any(
                            k in item for k in ("name", "title", "github_url")
                        ):
                            servers.append(item)
                elif isinstance(data, dict):
                    for key in ("servers", "items", "data"):
                        if isinstance(data.get(key), list):
                            servers.extend(data[key])
            except (json.JSONDecodeError, TypeError, IndexError):
                continue

        return servers

    def _extract_json_blobs(self, html: str) -> list[dict]:
        """Look for JSON arrays that resemble server listings."""
        for match in re.finditer(r'\[(\{[^]]{100,})\]', html):
            try:
                candidate = json.loads("[" + match.group(1) + "]")
                if (
                    isinstance(candidate, list)
                    and len(candidate) > 2
                    and isinstance(candidate[0], dict)
                    and any(
                        k in candidate[0]
                        for k in ("name", "title", "qualifiedName", "github_url")
                    )
                ):
                    return candidate
            except json.JSONDecodeError:
                continue
        return []

    def _extract_server_list(self, data: object) -> list[dict]:
        """Extract a server list from various API response shapes."""
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("servers", "items", "data", "results", "hits", "list"):
                candidate = data.get(key)
                if isinstance(candidate, list):
                    return candidate
        return []

    def _parse_servers(self, servers: list[dict], limit: int) -> list[DiscoveredPackage]:
        """Convert raw server dicts into DiscoveredPackage objects."""
        results: list[DiscoveredPackage] = []
        seen_ids: set[str] = set()

        for server in servers:
            if len(results) >= limit:
                break

            name = (
                server.get("qualifiedName")
                or server.get("name")
                or server.get("title")
                or ""
            )
            if not name:
                continue

            pkg_id = _slug_from_name(name)
            if not pkg_id or pkg_id in seen_ids:
                continue
            seen_ids.add(pkg_id)

            repo_url = (
                server.get("github_url")
                or server.get("repository")
                or server.get("repo_url")
                or server.get("url")
            )
            # Only keep URLs that look like repos
            if repo_url and not any(
                host in repo_url for host in ("github.com", "gitlab.com", "bitbucket.org")
            ):
                homepage = repo_url
                repo_url = None
            else:
                homepage = server.get("homepage") or server.get("url")

            description = server.get("description") or ""
            if len(description) > 500:
                description = description[:500]

            tags = server.get("tags") or []
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]
            category = server.get("category")
            if category and category not in tags:
                tags.append(category)

            pkg = DiscoveredPackage(
                id=pkg_id,
                name=server.get("displayName") or server.get("title") or name,
                repo_url=repo_url,
                homepage=homepage,
                description=description or None,
                topics=tags,
                stars=server.get("stars", 0) or 0,
                last_active=(
                    server.get("updatedAt")
                    or server.get("updated_at")
                    or server.get("created_at")
                ),
                package_type="mcp_server",
                discovery_source="mcp_so",
            )
            results.append(pkg)

        print(f"  [mcp_so] Discovered {len(results)} packages.")
        return results
