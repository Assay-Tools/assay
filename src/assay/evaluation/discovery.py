"""Discovery Agent — orchestrates multiple discovery sources to find packages."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from assay.database import SessionLocal, init_db
from assay.models import Category, Package

from .sources import (
    CratesIoSource,
    CursorDirectorySource,
    DiscoveredPackage,
    DiscoverySource,
    DockerMCPSource,
    GitHubAwesomeListSource,
    GitHubSource,
    GlamaSource,
    MCPRegistrySource,
    MCPRunSource,
    MCPSoSource,
    NpmSource,
    OpenClawSource,
    PyPISource,
    SmitherySource,
)

# Pre-defined categories with display names and keyword hints for matching.
CATEGORIES: dict[str, dict[str, str | list[str]]] = {
    "developer-tools": {
        "name": "Developer Tools",
        "description": "IDEs, code editors, CI/CD, version control, debugging",
        "keywords": ["git", "github", "gitlab", "code", "ide", "ci", "cd", "lint", "debug",
                     "vscode", "editor", "devtool", "build", "deploy", "docker", "kubernetes",
                     "terraform", "npm", "pip", "cargo", "cli", "terminal", "shell"],
    },
    "databases": {
        "name": "Databases",
        "description": "SQL, NoSQL, vector databases, caching",
        "keywords": ["database", "sql", "postgres", "mysql", "sqlite", "mongo", "redis",
                     "supabase", "firebase", "dynamo", "cassandra", "neo4j", "vector",
                     "pinecone", "weaviate", "qdrant", "chroma", "db"],
    },
    "ai-ml": {
        "name": "AI & Machine Learning",
        "description": "LLMs, embeddings, training, inference",
        "keywords": ["ai", "ml", "llm", "openai", "anthropic", "gpt", "claude", "embedding",
                     "model", "inference", "training", "huggingface", "ollama", "langchain",
                     "rag", "agent", "chatbot", "copilot", "gemini"],
    },
    "communication": {
        "name": "Communication",
        "description": "Email, messaging, notifications, chat",
        "keywords": ["email", "smtp", "slack", "discord", "teams", "telegram", "twilio",
                     "sendgrid", "resend", "notification", "sms", "chat", "webhook",
                     "messaging", "mail"],
    },
    "file-management": {
        "name": "File Management",
        "description": "File storage, conversion, processing",
        "keywords": ["file", "storage", "s3", "blob", "upload", "download", "filesystem",
                     "pdf", "csv", "excel", "image", "video", "audio", "media", "drive",
                     "dropbox", "gdrive"],
    },
    "cloud-infrastructure": {
        "name": "Cloud Infrastructure",
        "description": "AWS, GCP, Azure, serverless, hosting",
        "keywords": ["aws", "gcp", "azure", "cloud", "serverless", "lambda", "ec2",
                     "cloudflare", "vercel", "netlify", "heroku", "infrastructure", "iac",
                     "pulumi"],
    },
    "search": {
        "name": "Search",
        "description": "Web search, semantic search, indexing",
        "keywords": ["search", "elasticsearch", "algolia", "typesense", "meilisearch",
                     "crawl", "scrape", "index", "brave", "google", "bing", "web-search",
                     "browser", "puppeteer", "playwright"],
    },
    "monitoring": {
        "name": "Monitoring",
        "description": "Logging, metrics, alerting, observability",
        "keywords": ["monitor", "log", "metric", "alert", "observability", "datadog",
                     "grafana", "prometheus", "sentry", "newrelic", "apm", "trace",
                     "uptime", "healthcheck"],
    },
    "productivity": {
        "name": "Productivity",
        "description": "Task management, calendars, notes, automation",
        "keywords": ["todo", "task", "project", "calendar", "notion", "obsidian", "note",
                     "jira", "linear", "asana", "trello", "airtable", "spreadsheet",
                     "automation", "zapier", "workflow", "schedule"],
    },
    "security": {
        "name": "Security",
        "description": "Auth, secrets, scanning, compliance",
        "keywords": ["security", "auth", "oauth", "jwt", "secret", "vault", "encrypt",
                     "scan", "vulnerability", "compliance", "firewall", "waf", "sso",
                     "identity", "password"],
    },
    "finance": {
        "name": "Finance",
        "description": "Payments, accounting, crypto, trading",
        "keywords": ["payment", "stripe", "paypal", "invoice", "accounting", "crypto",
                     "bitcoin", "ethereum", "trading", "finance", "bank", "wallet",
                     "currency", "stock"],
    },
    "content-management": {
        "name": "Content Management",
        "description": "CMS, headless content, markdown, publishing",
        "keywords": ["cms", "content", "wordpress", "sanity", "strapi", "markdown",
                     "blog", "publish", "headless", "contentful", "ghost", "wiki",
                     "documentation"],
    },
    "data-processing": {
        "name": "Data Processing",
        "description": "ETL, pipelines, transformation, analytics",
        "keywords": ["data", "etl", "pipeline", "transform", "analytics", "bigquery",
                     "snowflake", "dbt", "airflow", "spark", "kafka", "stream",
                     "batch", "warehouse"],
    },
    "social-media": {
        "name": "Social Media",
        "description": "Twitter/X, LinkedIn, Instagram, posting",
        "keywords": ["twitter", "tweet", "linkedin", "instagram", "facebook", "social",
                     "post", "feed", "reddit", "youtube", "tiktok", "mastodon",
                     "bluesky"],
    },
    "agent-skills": {
        "name": "Agent Skills",
        "description": "Claude Code skills, agent capabilities, prompt templates",
        "keywords": ["skill", "claude-code", "agent-skill", "openclaw", "prompt",
                     "workflow", "automation", "slash-command", "capability", "tool",
                     "extension", "plugin"],
    },
    "other": {
        "name": "Other",
        "description": "Uncategorized packages",
        "keywords": [],
    },
}

# Map source name strings to source classes
SOURCE_CLASSES: dict[str, type[DiscoverySource]] = {
    "github": GitHubSource,
    "mcp_registry": MCPRegistrySource,
    "skills": GitHubAwesomeListSource,
    "openclaw": OpenClawSource,
    "npm": NpmSource,
    "pypi": PyPISource,
    "smithery": SmitherySource,
    "glama": GlamaSource,
    "cursor_directory": CursorDirectorySource,
    "docker_mcp": DockerMCPSource,
    "mcp_run": MCPRunSource,
    "mcp_so": MCPSoSource,
    "crates_io": CratesIoSource,
}


def _guess_category(description: str | None, topics: list[str], name: str) -> str:
    """Assign a best-guess category based on repo description, topics, and name."""
    text = " ".join([
        (description or "").lower(),
        " ".join(topics),
        name.lower(),
    ])

    best_slug = "other"
    best_score = 0

    for slug, meta in CATEGORIES.items():
        if slug == "other":
            continue
        score = sum(1 for kw in meta["keywords"] if kw in text)
        if score > best_score:
            best_score = score
            best_slug = slug

    return best_slug


def _compute_priority(pkg: DiscoveredPackage) -> str:
    """Compute priority tier based on quality signals.

    Signals: stars, recent activity, multi-source presence.
    high: stars >= 50, or recently active (last 90 days) with stars >= 10
    medium: stars >= 10, or recently active
    low: everything else
    """
    stars = pkg.stars
    # Check recency (last_active within 90 days)
    recent = False
    if pkg.last_active:
        try:
            from datetime import datetime, timezone
            active_date = datetime.fromisoformat(
                pkg.last_active.replace("Z", "+00:00"),
            )
            days_old = (datetime.now(timezone.utc) - active_date).days
            recent = days_old <= 90
        except (ValueError, TypeError):
            pass

    if stars >= 50:
        return "high"
    if stars >= 10 and recent:
        return "high"
    if stars >= 10 or recent:
        return "medium"
    return "low"


def _normalize_name(slug: str) -> str | None:
    """Normalize a package slug for dedup — strips common prefixes like 'mcp-server-'."""
    name = slug.lower().strip("-")
    for prefix in ("mcp-server-", "mcp-", "server-", "modelcontextprotocol-"):
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    name = name.strip("-")
    return name if name else None


def _normalize_repo_url(url: str | None) -> str | None:
    """Normalize a repo URL for deduplication (lowercase, strip trailing slashes and .git)."""
    if not url:
        return None
    url = url.lower().rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    return url


logger = logging.getLogger(__name__)

LOG_DIR = Path(__file__).parent.parent.parent.parent / "logs" / "discovery"


def _log_discovery_run(
    sources: list[str],
    discovered: int,
    inserted: int,
    total_db: int,
) -> None:
    """Append a JSON line to the discovery run log."""
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_file = LOG_DIR / "runs.jsonl"
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sources": sources,
            "discovered": discovered,
            "inserted": inserted,
            "duplicates_skipped": discovered - inserted,
            "total_db": total_db,
        }
        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError as exc:
        logger.warning("Could not write discovery log: %s", exc)


class DiscoveryAgent:
    """Orchestrates multiple discovery sources to find and insert packages."""

    def __init__(
        self,
        limit: int = 50000,
        sources: list[DiscoverySource] | None = None,
        package_type_filter: str | None = None,
    ):
        self.limit = limit
        self.sources = sources or [cls() for cls in SOURCE_CLASSES.values()]
        self.package_type_filter = package_type_filter

    def seed_categories(self, db) -> None:
        """Create Category records if they don't already exist."""
        existing = {c.slug for c in db.query(Category).all()}
        created = 0
        for slug, meta in CATEGORIES.items():
            if slug not in existing:
                cat = Category(
                    slug=slug,
                    name=meta["name"],
                    description=meta["description"],
                )
                db.add(cat)
                created += 1
        if created:
            db.commit()
            print(f"  Seeded {created} categories.")
        else:
            print("  Categories already exist.")

    def discover_all(self) -> list[DiscoveredPackage]:
        """Run all sources and return deduplicated results.

        Each source gets its own per-source limit (total limit / num sources,
        with a generous minimum) so early sources don't starve later ones.
        Final dedup happens after all sources have run.
        """
        all_packages: list[DiscoveredPackage] = []
        seen_repo_urls: set[str] = set()
        seen_ids: set[str] = set()
        seen_normalized_names: set[str] = set()

        # Give each source its own limit instead of sharing a shrinking remainder.
        # Use a generous per-source limit — dedup handles overlap.
        per_source_limit = max(self.limit // max(len(self.sources), 1), 5000)

        for source in self.sources:
            print(f"\n--- Source: {source.source_name} (limit={per_source_limit}) ---")
            try:
                discovered = source.discover(limit=per_source_limit)
            except Exception as exc:
                print(f"  ERROR: {source.source_name} failed: {exc}")
                continue

            added = 0
            for pkg in discovered:
                # Apply package_type filter if set
                if self.package_type_filter and self.package_type_filter != "all":
                    if pkg.package_type != self.package_type_filter:
                        continue

                # Deduplicate by normalized repo_url (primary)
                norm_url = _normalize_repo_url(pkg.repo_url)
                if norm_url and norm_url in seen_repo_urls:
                    continue

                # Deduplicate by package id (secondary)
                if pkg.id in seen_ids:
                    continue

                # Deduplicate by normalized name (tertiary) — catches
                # "mcp-server-foo" vs "foo" from different sources
                norm_name = _normalize_name(pkg.id)
                if norm_name and norm_name in seen_normalized_names:
                    continue

                if norm_url:
                    seen_repo_urls.add(norm_url)
                seen_ids.add(pkg.id)
                if norm_name:
                    seen_normalized_names.add(norm_name)
                all_packages.append(pkg)
                added += 1

            print(f"  Added {added} unique packages from {source.source_name}.")

        print(f"\n  Total unique packages across all sources: {len(all_packages)}")
        return all_packages[:self.limit]

    def insert_packages(self, packages: list[DiscoveredPackage], db) -> int:
        """Create stub Package records. Returns count of newly inserted packages.

        For existing packages found via a new source, merges the source into
        the discovery_source list and enriches empty metadata fields.
        """
        existing_ids = {p.id for p in db.query(Package.id).all()}
        # Also collect legacy_ids so new-format slugs don't duplicate old packages
        legacy_ids = {
            p.legacy_id for p in db.query(Package.legacy_id).filter(
                Package.legacy_id.isnot(None)
            ).all()
        }
        # Map normalized repo_url -> package id for URL-based dedup + merge
        url_to_id: dict[str, str] = {}
        for row in db.query(Package.id, Package.repo_url).filter(
            Package.repo_url.isnot(None)
        ).all():
            norm = _normalize_repo_url(row.repo_url)
            if norm:
                url_to_id[norm] = row.id

        inserted = 0
        merged = 0

        for pkg in packages:
            norm_url = _normalize_repo_url(pkg.repo_url)

            # Check if this package already exists (by id, legacy_id, or repo_url)
            existing_pkg_id = None
            if pkg.id in existing_ids:
                existing_pkg_id = pkg.id
            elif pkg.id in legacy_ids:
                existing_pkg_id = pkg.id  # will be caught by id match below
            elif norm_url and norm_url in url_to_id:
                existing_pkg_id = url_to_id[norm_url]

            if existing_pkg_id:
                # Merge: add source to discovery_source list + enrich empty fields
                self._merge_existing(db, existing_pkg_id, pkg)
                merged += 1
                continue

            category_slug = _guess_category(pkg.description, pkg.topics, pkg.name)
            priority = _compute_priority(pkg)

            db_pkg = Package(
                id=pkg.id,
                name=pkg.name,
                repo_url=pkg.repo_url,
                homepage=pkg.homepage,
                category_slug=category_slug,
                what_it_does=pkg.description,
                tags=json.dumps(pkg.topics) if pkg.topics else None,
                package_type=pkg.package_type,
                discovery_source=json.dumps([pkg.discovery_source]),
                priority=priority,
                stars=pkg.stars,
                status="discovered",
            )
            db.add(db_pkg)
            existing_ids.add(pkg.id)
            if norm_url:
                url_to_id[norm_url] = pkg.id
            inserted += 1
            print(
                f"  ADD: {pkg.id:50s}  stars={pkg.stars:>6}  type={pkg.package_type:>12}  "
                f"src={pkg.discovery_source:>15}  pri={priority}  cat={category_slug}"
            )

        db.commit()
        if merged:
            print(f"  Merged source info into {merged} existing packages.")
        return inserted

    @staticmethod
    def _merge_existing(db, pkg_id: str, pkg: DiscoveredPackage) -> None:
        """Merge new discovery data into an existing package record."""
        existing = db.get(Package, pkg_id)
        if not existing:
            return

        # Add source to discovery_source list if not already present
        sources = existing.discovery_sources_list
        if pkg.discovery_source not in sources:
            sources.append(pkg.discovery_source)
            existing.discovery_source = json.dumps(sources)

        # Enrich empty fields with data from the new source
        if not existing.repo_url and pkg.repo_url:
            existing.repo_url = pkg.repo_url
        if not existing.homepage and pkg.homepage:
            existing.homepage = pkg.homepage
        if not existing.what_it_does and pkg.description:
            existing.what_it_does = pkg.description
        if not existing.tags and pkg.topics:
            existing.tags = json.dumps(pkg.topics)
        # Upgrade stars if new source has higher count
        if pkg.stars and (not existing.stars or pkg.stars > existing.stars):
            existing.stars = pkg.stars

    def run(self) -> None:
        """Full discovery pipeline: search all sources, deduplicate, insert."""
        print("=== Assay Discovery Agent ===")
        print(f"Target: up to {self.limit} packages")
        print(f"Sources: {', '.join(s.source_name for s in self.sources)}")
        if self.package_type_filter:
            print(f"Type filter: {self.package_type_filter}")

        # 1. Initialize database
        print("\n[1/4] Initializing database ...")
        init_db()

        # 2. Seed categories
        print("[2/4] Seeding categories ...")
        db = SessionLocal()
        try:
            self.seed_categories(db)

            # 3. Discover from all sources
            print("\n[3/4] Running discovery sources ...")
            packages = self.discover_all()
            print(f"\n  Total unique packages discovered: {len(packages)}")

            # 4. Insert packages
            print("\n[4/4] Inserting package stubs ...")
            inserted = self.insert_packages(packages, db)

            # Summary
            total = db.query(Package).count()
            print("\n=== Done ===")
            print(f"  New packages inserted: {inserted}")
            print(f"  Total packages in DB:  {total}")

            # Log discovery run
            _log_discovery_run(
                sources=[s.source_name for s in self.sources],
                discovered=len(packages),
                inserted=inserted,
                total_db=total,
            )

        finally:
            db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Assay Discovery Agent — find packages from multiple sources",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50000,
        help="Maximum number of packages to discover (default: 50000)",
    )
    parser.add_argument(
        "--source",
        choices=list(SOURCE_CLASSES.keys()) + ["all"],
        default="all",
        help="Discovery source to use (default: all)",
    )
    parser.add_argument(
        "--type",
        choices=["mcp_server", "skill", "all"],
        default="all",
        dest="package_type",
        help="Package type to discover (default: all)",
    )
    args = parser.parse_args()

    # Build source list
    if args.source == "all":
        sources = [cls() for cls in SOURCE_CLASSES.values()]
    elif args.source == "skills":
        # "skills" is a shorthand for both awesome-list and openclaw sources
        sources = [GitHubAwesomeListSource(), OpenClawSource()]
    else:
        source_cls = SOURCE_CLASSES.get(args.source)
        if source_cls:
            sources = [source_cls()]
        else:
            print(f"Unknown source: {args.source}")
            return

    type_filter = args.package_type if args.package_type != "all" else None

    agent = DiscoveryAgent(limit=args.limit, sources=sources, package_type_filter=type_filter)
    agent.run()


if __name__ == "__main__":
    main()
