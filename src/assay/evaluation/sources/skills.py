"""Skills discovery sources — awesome lists and OpenClaw ecosystem."""

from __future__ import annotations

import re
import time

import httpx

from .base import DiscoveredPackage, DiscoverySource


def _slug_from_url(url: str) -> str:
    """Generate a package ID slug from a URL."""
    # Extract owner/repo from GitHub URL
    match = re.search(r"github\.com/([^/]+/[^/]+)", url)
    if match:
        repo_part = match.group(1).split("/")[-1]
    else:
        repo_part = url.rstrip("/").split("/")[-1]
    slug = re.sub(r"[^a-z0-9-]", "-", repo_part.lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:255]


class GitHubAwesomeListSource(DiscoverySource):
    """Discovers skills from GitHub awesome-list style repos.

    Crawls README files from curated repos that list agent skills,
    extracting GitHub links as skill packages.
    """

    # Curated repos that list agent skills
    AWESOME_REPOS = [
        "anthropics/skills",
        "anthropics/claude-code-skills",
        "punkpeye/awesome-mcp-servers",
    ]

    @property
    def source_name(self) -> str:
        return "github_awesome"

    def discover(self, limit: int = 500) -> list[DiscoveredPackage]:
        results: list[DiscoveredPackage] = []
        seen_ids: set[str] = set()
        client = httpx.Client(
            headers={"Accept": "application/vnd.github.raw+json"},
            timeout=30.0,
        )

        try:
            for repo in self.AWESOME_REPOS:
                if len(results) >= limit:
                    break

                print(f"  [github_awesome] Crawling {repo} ...")
                readme_url = f"https://api.github.com/repos/{repo}/readme"

                try:
                    resp = client.get(readme_url)
                    if resp.status_code == 404:
                        print(f"  [github_awesome] {repo} not found, skipping.")
                        continue
                    resp.raise_for_status()
                    content = resp.text
                except httpx.HTTPError as exc:
                    print(f"  [github_awesome] Error fetching {repo}: {exc}")
                    continue

                # Extract GitHub links from markdown
                links = re.findall(
                    r"\[([^\]]+)\]\((https://github\.com/[^/]+/[^/)]+)\)",
                    content,
                )

                for name, url in links:
                    if len(results) >= limit:
                        break

                    pkg_id = _slug_from_url(url)
                    if pkg_id in seen_ids or not pkg_id:
                        continue
                    seen_ids.add(pkg_id)

                    # Determine package_type based on source repo
                    is_skill = "skill" in repo.lower()
                    pkg_type = "skill" if is_skill else "mcp_server"

                    pkg = DiscoveredPackage(
                        id=pkg_id,
                        name=name.strip(),
                        repo_url=url,
                        homepage=None,
                        description=None,
                        topics=[],
                        stars=0,
                        last_active=None,
                        package_type=pkg_type,
                        discovery_source="github_awesome",
                    )
                    results.append(pkg)

                time.sleep(2.0)  # Be polite between repos

        finally:
            client.close()

        print(f"  [github_awesome] Discovered {len(results)} packages.")
        return results


class OpenClawSource(DiscoverySource):
    """Discovers agent skills from the OpenClaw ecosystem.

    Searches GitHub for repos tagged with openclaw or agent-skill topics.
    """

    SEARCH_QUERIES = [
        "topic:agent-skill",
        "topic:claude-skill",
        "topic:openclaw",
        "agent+skill+in:name",
    ]

    GITHUB_API = "https://api.github.com/search/repositories"
    REQUEST_DELAY_SECONDS = 7.0

    @property
    def source_name(self) -> str:
        return "openclaw"

    def discover(self, limit: int = 500) -> list[DiscoveredPackage]:
        results: list[DiscoveredPackage] = []
        seen_urls: set[str] = set()
        client = httpx.Client(
            headers={"Accept": "application/vnd.github+json"},
            timeout=30.0,
        )

        try:
            for query in self.SEARCH_QUERIES:
                if len(results) >= limit:
                    break

                print(f"  [openclaw] Searching: q={query} ...")

                try:
                    resp = client.get(
                        self.GITHUB_API,
                        params={
                            "q": query,
                            "sort": "stars",
                            "order": "desc",
                            "per_page": min(100, limit - len(results)),
                        },
                    )
                    if resp.status_code == 403:
                        retry_after = int(resp.headers.get("Retry-After", "60"))
                        print(f"  [openclaw] Rate limited. Waiting {retry_after}s ...")
                        time.sleep(retry_after)
                        resp = client.get(
                            self.GITHUB_API,
                            params={"q": query, "sort": "stars", "order": "desc", "per_page": 100},
                        )
                    resp.raise_for_status()
                    data = resp.json()
                except httpx.HTTPError as exc:
                    print(f"  [openclaw] HTTP error: {exc}")
                    continue

                for repo in data.get("items", []):
                    if len(results) >= limit:
                        break

                    html_url = repo.get("html_url", "")
                    if html_url in seen_urls:
                        continue
                    seen_urls.add(html_url)

                    full_name = repo.get("full_name", "")
                    repo_name = full_name.split("/")[-1]
                    slug = re.sub(r"[^a-z0-9-]", "-", repo_name.lower())
                    slug = re.sub(r"-+", "-", slug).strip("-")[:255]

                    pkg = DiscoveredPackage(
                        id=slug,
                        name=repo.get("name", repo_name),
                        repo_url=html_url,
                        homepage=repo.get("homepage") or None,
                        description=(repo.get("description") or "")[:500] or None,
                        topics=repo.get("topics", []),
                        stars=repo.get("stargazers_count", 0),
                        last_active=repo.get("pushed_at"),
                        package_type="skill",
                        discovery_source="openclaw",
                    )
                    results.append(pkg)

                print(f"  [openclaw] Waiting {self.REQUEST_DELAY_SECONDS}s ...")
                time.sleep(self.REQUEST_DELAY_SECONDS)

        finally:
            client.close()

        print(f"  [openclaw] Discovered {len(results)} skills.")
        return results
