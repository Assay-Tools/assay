"""GitHub search discovery source — finds MCP server repos via GitHub API."""

from __future__ import annotations

import re
import time

import httpx

from .base import DiscoveredPackage, DiscoverySource


def slug_from_repo(full_name: str) -> str:
    """Generate a package ID slug from a GitHub repo full name (owner/repo)."""
    repo_name = full_name.split("/")[-1]
    slug = re.sub(r"[^a-z0-9-]", "-", repo_name.lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:255]


class GitHubSource(DiscoverySource):
    """Discovers MCP server repositories from GitHub search."""

    SEARCH_QUERIES = [
        "topic:mcp-server",
        "mcp+server+in:name",
        "mcp-server+in:name",
    ]

    GITHUB_API = "https://api.github.com/search/repositories"
    REQUEST_DELAY_SECONDS = 7.0

    @property
    def source_name(self) -> str:
        return "github"

    def __init__(self):
        self.client = httpx.Client(
            headers={"Accept": "application/vnd.github+json"},
            timeout=30.0,
        )
        self._seen_urls: set[str] = set()
        self._results: list[DiscoveredPackage] = []

    def discover(self, limit: int = 500) -> list[DiscoveredPackage]:
        """Search GitHub for MCP server repos."""
        self._seen_urls.clear()
        self._results.clear()

        for query in self.SEARCH_QUERIES:
            if len(self._results) >= limit:
                break
            self._run_query(query, limit)

        self.client.close()
        return self._results[:limit]

    def _run_query(self, query: str, limit: int) -> None:
        page = 1
        per_page = min(100, limit)

        while len(self._results) < limit:
            url = f"{self.GITHUB_API}?q={query}&sort=stars&order=desc&per_page={per_page}&page={page}"
            print(f"  [github] Searching: q={query} page={page} ...")

            try:
                resp = self.client.get(url)
                if resp.status_code == 403:
                    retry_after = int(resp.headers.get("Retry-After", "60"))
                    print(f"  [github] Rate limited. Waiting {retry_after}s ...")
                    time.sleep(retry_after)
                    resp = self.client.get(url)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPError as exc:
                print(f"  [github] HTTP error: {exc}")
                break

            items = data.get("items", [])
            if not items:
                break

            for repo in items:
                html_url = repo.get("html_url", "")
                if html_url in self._seen_urls:
                    continue
                self._seen_urls.add(html_url)

                full_name = repo.get("full_name", "")
                pkg = DiscoveredPackage(
                    id=slug_from_repo(full_name),
                    name=repo.get("name", full_name.split("/")[-1]),
                    repo_url=html_url,
                    homepage=repo.get("homepage") or None,
                    description=(repo.get("description") or "")[:500] or None,
                    topics=repo.get("topics", []),
                    stars=repo.get("stargazers_count", 0),
                    last_active=repo.get("pushed_at"),
                    package_type="mcp_server",
                    discovery_source="github",
                )
                self._results.append(pkg)
                if len(self._results) >= limit:
                    break

            if len(items) < per_page or page >= 10:
                break

            page += 1
            print(f"  [github] Respecting rate limit, waiting {self.REQUEST_DELAY_SECONDS}s ...")
            time.sleep(self.REQUEST_DELAY_SECONDS)

        print(f"  [github] Respecting rate limit, waiting {self.REQUEST_DELAY_SECONDS}s ...")
        time.sleep(self.REQUEST_DELAY_SECONDS)
