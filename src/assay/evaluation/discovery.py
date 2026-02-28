"""Discovery Agent — finds MCP server packages from public sources."""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone

import httpx

from assay.database import SessionLocal, init_db
from assay.models import Category, Package

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
    "other": {
        "name": "Other",
        "description": "Uncategorized packages",
        "keywords": [],
    },
}


def _slug_from_repo(full_name: str) -> str:
    """Generate a package ID slug from a GitHub repo full name (owner/repo)."""
    # Use just the repo name, not the owner
    repo_name = full_name.split("/")[-1]
    # Lowercase, keep alphanumerics and hyphens
    slug = re.sub(r"[^a-z0-9-]", "-", repo_name.lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:255]


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


class DiscoveryAgent:
    """Discovers MCP server repositories from GitHub and creates stub Package records."""

    SEARCH_QUERIES = [
        "topic:mcp-server",
        "mcp+server+in:name",
        "mcp-server+in:name",
    ]

    GITHUB_API = "https://api.github.com/search/repositories"
    # Unauthenticated GitHub search: 10 requests/minute
    REQUEST_DELAY_SECONDS = 7.0

    def __init__(self, limit: int = 250):
        self.limit = limit
        self.client = httpx.Client(
            headers={"Accept": "application/vnd.github+json"},
            timeout=30.0,
        )
        # Track repos by URL to deduplicate across queries
        self._seen_urls: set[str] = set()
        self._repos: list[dict] = []

    def search_github(self) -> list[dict]:
        """Run all search queries against GitHub and return deduplicated repo list."""
        for query in self.SEARCH_QUERIES:
            if len(self._repos) >= self.limit:
                break
            self._run_query(query)
        return self._repos[: self.limit]

    def _run_query(self, query: str) -> None:
        """Execute a single GitHub search query, paginating as needed."""
        page = 1
        per_page = min(100, self.limit)

        while len(self._repos) < self.limit:
            url = f"{self.GITHUB_API}?q={query}&sort=stars&order=desc&per_page={per_page}&page={page}"
            print(f"  Searching: q={query} page={page} ...")

            try:
                resp = self.client.get(url)
                if resp.status_code == 403:
                    # Rate limited — wait and retry once
                    retry_after = int(resp.headers.get("Retry-After", "60"))
                    print(f"  Rate limited. Waiting {retry_after}s ...")
                    time.sleep(retry_after)
                    resp = self.client.get(url)

                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPError as exc:
                print(f"  HTTP error: {exc}")
                break

            items = data.get("items", [])
            if not items:
                break

            for repo in items:
                html_url = repo.get("html_url", "")
                if html_url in self._seen_urls:
                    continue
                self._seen_urls.add(html_url)
                self._repos.append(repo)
                if len(self._repos) >= self.limit:
                    break

            # GitHub search only returns up to 1000 results (10 pages of 100)
            if len(items) < per_page or page >= 10:
                break

            page += 1
            print(f"  Respecting rate limit, waiting {self.REQUEST_DELAY_SECONDS}s ...")
            time.sleep(self.REQUEST_DELAY_SECONDS)

        # Delay between different queries
        print(f"  Respecting rate limit, waiting {self.REQUEST_DELAY_SECONDS}s ...")
        time.sleep(self.REQUEST_DELAY_SECONDS)

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

    def insert_packages(self, repos: list[dict], db) -> int:
        """Create stub Package records. Returns count of newly inserted packages."""
        existing_ids = {p.id for p in db.query(Package.id).all()}
        inserted = 0

        for repo in repos:
            full_name = repo.get("full_name", "")
            pkg_id = _slug_from_repo(full_name)

            if pkg_id in existing_ids:
                print(f"  SKIP (exists): {pkg_id}")
                continue

            description = repo.get("description") or ""
            topics = repo.get("topics", [])
            stars = repo.get("stargazers_count", 0)
            language = repo.get("language") or ""
            html_url = repo.get("html_url", "")

            category_slug = _guess_category(description, topics, full_name)

            pkg = Package(
                id=pkg_id,
                name=repo.get("name", pkg_id),
                repo_url=html_url,
                homepage=repo.get("homepage") or None,
                category_slug=category_slug,
                what_it_does=description[:500] if description else None,
                tags=json.dumps(topics) if topics else None,
                status="discovered",
            )
            db.add(pkg)
            existing_ids.add(pkg_id)
            inserted += 1
            print(
                f"  ADD: {pkg_id:50s}  stars={stars:>6}  lang={language:>12}  "
                f"cat={category_slug}"
            )

        db.commit()
        return inserted

    def run(self) -> None:
        """Full discovery pipeline: search, deduplicate, insert."""
        print(f"=== Assay Discovery Agent ===")
        print(f"Target: up to {self.limit} packages\n")

        # 1. Initialize database
        print("[1/4] Initializing database ...")
        init_db()

        # 2. Seed categories
        print("[2/4] Seeding categories ...")
        db = SessionLocal()
        try:
            self.seed_categories(db)

            # 3. Search GitHub
            print(f"\n[3/4] Searching GitHub ...")
            repos = self.search_github()
            print(f"  Found {len(repos)} unique repositories.\n")

            # 4. Insert packages
            print(f"[4/4] Inserting package stubs ...")
            inserted = self.insert_packages(repos, db)

            # Summary
            total = db.query(Package).count()
            print(f"\n=== Done ===")
            print(f"  New packages inserted: {inserted}")
            print(f"  Total packages in DB:  {total}")

        finally:
            db.close()
            self.client.close()


def main():
    parser = argparse.ArgumentParser(description="Assay Discovery Agent — find MCP server packages")
    parser.add_argument(
        "--limit",
        type=int,
        default=250,
        help="Maximum number of packages to discover (default: 250)",
    )
    args = parser.parse_args()

    agent = DiscoveryAgent(limit=args.limit)
    agent.run()


if __name__ == "__main__":
    main()
