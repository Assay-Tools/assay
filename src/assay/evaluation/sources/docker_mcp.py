"""Docker Hub & Docker MCP Catalog discovery source — finds MCP server images."""

from __future__ import annotations

import re
import time

import httpx

from assay.config import settings

from .base import DiscoveredPackage, DiscoverySource


def _slug_from_docker(namespace: str, image: str) -> str:
    """Generate a package ID slug from a Docker image reference.

    Uses 'namespace--image-name' format (e.g., 'acme--mcp-server-sql').
    """
    raw = f"{namespace}--{image}" if namespace else image
    slug = re.sub(r"[^a-z0-9-]", "-", raw.lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:255]


class DockerMCPSource(DiscoverySource):
    """Discovers MCP server images from Docker Hub and the Docker MCP Catalog.

    Searches Docker Hub via the v2 search API and also fetches the curated
    Docker MCP Catalog from GitHub (docker/mcp-catalog).

    Uses DOCKER_HUB_TOKEN env var for authenticated requests if available,
    otherwise falls back to unauthenticated access (lower rate limits).
    """

    SEARCH_QUERIES = [
        "mcp+server",
        "mcp-server",
        "model-context-protocol",
    ]

    DOCKER_HUB_SEARCH = "https://hub.docker.com/v2/search/repositories/"
    MCP_CATALOG_URL = (
        "https://raw.githubusercontent.com/docker/mcp-catalog/main/catalog.json"
    )
    REQUEST_DELAY_SECONDS = 1.0

    @property
    def source_name(self) -> str:
        return "docker_mcp"

    def discover(self, limit: int = 500) -> list[DiscoveredPackage]:
        """Search Docker Hub and the MCP Catalog for MCP server images."""
        results: list[DiscoveredPackage] = []
        seen_ids: set[str] = set()

        headers: dict[str, str] = {"Accept": "application/json"}
        token = getattr(settings, "docker_hub_token", "")
        if token:
            headers["Authorization"] = f"Bearer {token}"
            print("  [docker_mcp] Using authenticated Docker Hub access.")
        else:
            print("  [docker_mcp] No DOCKER_HUB_TOKEN — using unauthenticated access.")

        client = httpx.Client(headers=headers, timeout=30.0)

        try:
            # --- Docker Hub search ---
            for query in self.SEARCH_QUERIES:
                if len(results) >= limit:
                    break
                self._search_docker_hub(client, query, limit, results, seen_ids)

            # --- Docker MCP Catalog ---
            if len(results) < limit:
                self._fetch_mcp_catalog(client, limit, results, seen_ids)
        finally:
            client.close()

        print(f"  [docker_mcp] Discovered {len(results)} packages.")
        return results[:limit]

    # ------------------------------------------------------------------
    # Docker Hub v2 search
    # ------------------------------------------------------------------

    def _search_docker_hub(
        self,
        client: httpx.Client,
        query: str,
        limit: int,
        results: list[DiscoveredPackage],
        seen_ids: set[str],
    ) -> None:
        page = 1
        page_size = 100

        while len(results) < limit:
            print(f"  [docker_mcp] Docker Hub search: q={query} page={page} ...")

            try:
                resp = client.get(
                    self.DOCKER_HUB_SEARCH,
                    params={
                        "query": query,
                        "page_size": page_size,
                        "page": page,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPError as exc:
                print(f"  [docker_mcp] HTTP error (Docker Hub): {exc}")
                break

            items = data.get("results", [])
            if not items:
                break

            for item in items:
                if len(results) >= limit:
                    break

                repo_name = item.get("repo_name", "")
                if "/" in repo_name:
                    namespace, image = repo_name.split("/", 1)
                else:
                    namespace = "library"
                    image = repo_name

                pkg_id = _slug_from_docker(namespace, image)
                if not pkg_id or pkg_id in seen_ids:
                    continue
                seen_ids.add(pkg_id)

                hub_url = f"https://hub.docker.com/r/{namespace}/{image}"

                pkg = DiscoveredPackage(
                    id=pkg_id,
                    name=image,
                    repo_url=hub_url,
                    homepage=hub_url,
                    description=(item.get("description") or "")[:500] or None,
                    topics=[],
                    stars=item.get("star_count", 0),
                    last_active=None,
                    package_type="mcp_server",
                    discovery_source="docker_mcp",
                )
                results.append(pkg)

            # Check for next page
            next_url = data.get("next")
            if not next_url or len(items) < page_size:
                break

            page += 1
            time.sleep(self.REQUEST_DELAY_SECONDS)

        time.sleep(self.REQUEST_DELAY_SECONDS)

    # ------------------------------------------------------------------
    # Docker MCP Catalog (GitHub)
    # ------------------------------------------------------------------

    def _fetch_mcp_catalog(
        self,
        client: httpx.Client,
        limit: int,
        results: list[DiscoveredPackage],
        seen_ids: set[str],
    ) -> None:
        print("  [docker_mcp] Fetching Docker MCP Catalog from GitHub ...")

        try:
            resp = client.get(self.MCP_CATALOG_URL)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            print(f"  [docker_mcp] HTTP error (MCP Catalog): {exc}")
            return

        # The catalog may be a list or a dict with a key holding the list.
        entries: list[dict] = []
        if isinstance(data, list):
            entries = data
        elif isinstance(data, dict):
            # Try common keys
            for key in ("servers", "catalog", "items", "images"):
                if isinstance(data.get(key), list):
                    entries = data[key]
                    break
            if not entries:
                # Fall back to values if dict of dicts
                entries = list(data.values()) if all(isinstance(v, dict) for v in data.values()) else []

        for entry in entries:
            if len(results) >= limit:
                break

            if not isinstance(entry, dict):
                continue

            # Extract image reference — catalog entries vary in shape
            image_ref = (
                entry.get("image")
                or entry.get("name")
                or entry.get("repo_name")
                or ""
            )
            if not image_ref:
                continue

            if "/" in image_ref:
                namespace, image = image_ref.split("/", 1)
            else:
                namespace = "library"
                image = image_ref

            # Strip any tag (e.g., "acme/mcp:latest" -> "acme/mcp")
            image = image.split(":")[0]

            pkg_id = _slug_from_docker(namespace, image)
            if not pkg_id or pkg_id in seen_ids:
                continue
            seen_ids.add(pkg_id)

            hub_url = f"https://hub.docker.com/r/{namespace}/{image}"
            repo_url = entry.get("repository") or entry.get("repo_url") or hub_url

            pkg = DiscoveredPackage(
                id=pkg_id,
                name=entry.get("display_name") or entry.get("title") or image,
                repo_url=repo_url,
                homepage=hub_url,
                description=(entry.get("description") or "")[:500] or None,
                topics=[],
                stars=entry.get("star_count", 0),
                last_active=entry.get("updated_at") or entry.get("created_at"),
                package_type="mcp_server",
                discovery_source="docker_mcp",
            )
            results.append(pkg)

        time.sleep(self.REQUEST_DELAY_SECONDS)
