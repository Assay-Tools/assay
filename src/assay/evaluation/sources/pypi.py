"""PyPI discovery source — finds MCP server packages on PyPI."""

from __future__ import annotations

import re
import time

import httpx

from .base import DiscoveredPackage, DiscoverySource


def _slug_from_pypi(name: str) -> str:
    """Generate a package ID slug from a PyPI package name."""
    slug = re.sub(r"[^a-z0-9-]", "-", name.lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:255]


class PyPISource(DiscoverySource):
    """Discovers MCP server packages from PyPI search.

    Uses the PyPI JSON API and XMLRPC search (via simple API)
    since PyPI deprecated the search endpoint. We search for
    packages with 'mcp' in the name via the simple index.
    """

    # PyPI doesn't have a search API anymore, so we search via
    # the JSON API for known package name patterns
    SEARCH_PREFIXES = [
        "mcp-server-",
        "mcp-",
        "modelcontextprotocol-",
        "fastmcp-",
        "mcp-tool-",
        "pymcp-",
        "llm-mcp-",
    ]

    PYPI_JSON = "https://pypi.org/pypi"
    PYPI_SIMPLE = "https://pypi.org/simple/"
    REQUEST_DELAY_SECONDS = 0.5

    @property
    def source_name(self) -> str:
        return "pypi"

    def discover(self, limit: int = 500) -> list[DiscoveredPackage]:
        """Search PyPI for MCP server packages.

        Strategy: Fetch the simple index (list of all package names),
        filter for MCP-related names, then fetch metadata for each.
        """
        results: list[DiscoveredPackage] = []
        seen_ids: set[str] = set()
        client = httpx.Client(timeout=60.0)

        try:
            # Fetch simple index to find MCP-related package names
            print("  [pypi] Fetching package index ...")
            try:
                resp = client.get(
                    self.PYPI_SIMPLE,
                    headers={"Accept": "application/vnd.pypi.simple.v1+json"},
                )
                resp.raise_for_status()
                data = resp.json()
                projects = data.get("projects", [])
            except httpx.HTTPError as exc:
                print(f"  [pypi] Error fetching index: {exc}")
                return results

            # Filter for MCP-related package names
            mcp_names = []
            for project in projects:
                name = project.get("name", "")
                name_lower = name.lower()
                if any(name_lower.startswith(p) for p in self.SEARCH_PREFIXES):
                    mcp_names.append(name)
                elif "mcp" in name_lower and "server" in name_lower:
                    mcp_names.append(name)
                elif name_lower.startswith("fastmcp"):
                    mcp_names.append(name)

            print(f"  [pypi] Found {len(mcp_names)} MCP-related packages.")

            # Fetch metadata only for packages not already in the DB
            skipped = 0
            for name in mcp_names:
                if len(results) >= limit:
                    break

                pkg_id = _slug_from_pypi(name)
                if pkg_id in seen_ids:
                    continue
                seen_ids.add(pkg_id)

                # Skip metadata fetch for packages already in DB (by ID or normalized name)
                if pkg_id in self.known_ids:
                    skipped += 1
                    continue
                norm = re.sub(r"^(mcp-server-|mcp-|server-|modelcontextprotocol-)", "", pkg_id).strip("-")
                if norm and norm in self.known_normalized_names:
                    skipped += 1
                    continue

                try:
                    resp = client.get(f"{self.PYPI_JSON}/{name}/json")
                    if resp.status_code == 404:
                        continue
                    resp.raise_for_status()
                    info = resp.json().get("info", {})
                except httpx.HTTPError:
                    continue

                # Post-filter: verify description mentions MCP for
                # packages that matched only by loose name patterns
                summary = (info.get("summary") or "").lower()
                desc_long = (info.get("description") or "").lower()[:2000]
                name_lower = name.lower()
                is_prefix_match = any(name_lower.startswith(p) for p in self.SEARCH_PREFIXES)
                if not is_prefix_match and "mcp" not in name_lower:
                    # Loose match — require description confirmation
                    if "mcp" not in summary and "model context protocol" not in desc_long:
                        continue

                # Extract repo URL from project URLs
                project_urls = info.get("project_urls") or {}
                repo_url = (
                    project_urls.get("Repository")
                    or project_urls.get("Source")
                    or project_urls.get("GitHub")
                    or project_urls.get("Source Code")
                    or project_urls.get("Homepage")
                )

                pkg = DiscoveredPackage(
                    id=pkg_id,
                    name=name,
                    repo_url=repo_url,
                    homepage=info.get("home_page") or info.get("project_url"),
                    description=(info.get("summary") or "")[:500] or None,
                    topics=info.get("keywords", "").split(",") if info.get("keywords") else [],
                    stars=0,
                    last_active=None,
                    package_type="mcp_server",
                    discovery_source="pypi",
                )
                results.append(pkg)

                time.sleep(self.REQUEST_DELAY_SECONDS)

            if skipped:
                print(f"  [pypi] Skipped {skipped} packages already in DB.")

        finally:
            client.close()

        print(f"  [pypi] Discovered {len(results)} packages.")
        return results[:limit]
