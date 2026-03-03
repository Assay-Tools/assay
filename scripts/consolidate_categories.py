"""One-time migration: consolidate ~150 ad-hoc categories down to 16 canonical ones.

Usage:
    cd ~/git/assay
    uv run python scripts/consolidate_categories.py

What it does:
    1. Remaps all ad-hoc category slugs to canonical ones
    2. Runs _guess_category() on NULL-category packages
    3. Fixes canonical category names/descriptions from CATEGORIES dict
    4. Deletes orphaned Category rows (0 packages after reassignment)
    5. Prints before/after verification
"""

import sys
from pathlib import Path

# Ensure the project src is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from sqlalchemy import text

from assay.database import SessionLocal, init_db
from assay.evaluation.discovery import CATEGORIES, _guess_category
from assay.models import Category, Package

# Maps every known ad-hoc slug to a canonical slug.
# Built from DB audit of all 150 categories.
SLUG_MAP: dict[str, str] = {
    # --- AI & ML ---
    "ai": "ai-ml",
    "ai-ml": "ai-ml",
    "Ai Ml": "ai-ml",
    "machine-learning": "ai-ml",
    "llm": "ai-ml",
    "nlp": "ai-ml",
    "generative-ai": "ai-ml",

    # --- Databases ---
    "databases": "databases",
    "database": "databases",
    "Database": "databases",
    "vector-database": "databases",
    "vector-databases": "databases",

    # --- Communication ---
    "communication": "communication",
    "communications": "communication",
    "Communication": "communication",
    "email": "communication",
    "messaging": "communication",
    "notifications": "communication",

    # --- Developer Tools ---
    "developer-tools": "developer-tools",
    "devops": "developer-tools",
    "DevOps": "developer-tools",
    "dev-tools": "developer-tools",
    "development": "developer-tools",
    "testing": "developer-tools",
    "code-quality": "developer-tools",
    "version-control": "developer-tools",
    "documentation": "developer-tools",

    # --- Cloud Infrastructure ---
    "cloud-infrastructure": "cloud-infrastructure",
    "cloud": "cloud-infrastructure",
    "Cloud": "cloud-infrastructure",
    "infrastructure": "cloud-infrastructure",
    "Infrastructure": "cloud-infrastructure",
    "hosting": "cloud-infrastructure",
    "serverless": "cloud-infrastructure",

    # --- Data Processing ---
    "data-processing": "data-processing",
    "data": "data-processing",
    "Data": "data-processing",
    "analytics": "data-processing",
    "etl": "data-processing",
    "data-analytics": "data-processing",
    "data-integration": "data-processing",
    "data-visualization": "data-processing",

    # --- File Management ---
    "file-management": "file-management",
    "files": "file-management",
    "file-storage": "file-management",
    "media": "file-management",
    "storage": "file-management",

    # --- Search ---
    "search": "search",
    "web-scraping": "search",
    "web-search": "search",
    "browser": "search",
    "crawling": "search",

    # --- Monitoring ---
    "monitoring": "monitoring",
    "Monitoring": "monitoring",
    "observability": "monitoring",
    "Observability": "monitoring",
    "logging": "monitoring",
    "alerting": "monitoring",
    "apm": "monitoring",

    # --- Productivity ---
    "productivity": "productivity",
    "Productivity": "productivity",
    "project-management": "productivity",
    "task-management": "productivity",
    "crm": "productivity",
    "CRM": "productivity",
    "Crm": "productivity",
    "hr": "productivity",
    "hr-recruiting": "productivity",
    "hr-payroll": "productivity",
    "Hr": "productivity",
    "calendar": "productivity",
    "automation": "productivity",
    "workflow": "productivity",
    "collaboration": "productivity",

    # --- Security ---
    "security": "security",
    "Security": "security",
    "auth": "security",
    "authentication": "security",
    "identity": "security",
    "compliance": "security",

    # --- Finance ---
    "finance": "finance",
    "Finance": "finance",
    "payments": "finance",
    "billing": "finance",
    "accounting": "finance",
    "crypto": "finance",
    "fintech": "finance",

    # --- Content Management ---
    "content-management": "content-management",
    "cms": "content-management",
    "content": "content-management",
    "publishing": "content-management",

    # --- Social Media ---
    "social-media": "social-media",
    "social": "social-media",

    # --- Agent Skills ---
    "agent-skills": "agent-skills",

    # --- Other ---
    "other": "other",
    "Other": "other",
    "miscellaneous": "other",
    "uncategorized": "other",
    "general": "other",
    "utilities": "other",
    "utility": "other",
}


def main():
    init_db()
    db = SessionLocal()

    try:
        # --- Before stats ---
        cat_count_before = db.query(Category).count()
        print(f"=== Before: {cat_count_before} categories ===\n")

        all_cats = db.query(Category).all()
        for cat in sorted(all_cats, key=lambda c: c.slug):
            pkg_count = db.query(Package).filter(Package.category_slug == cat.slug).count()
            print(f"  {cat.slug:40s}  {cat.name:35s}  {pkg_count:>5} packages")

        # --- Step 1: Remap ad-hoc slugs ---
        print("\n--- Remapping ad-hoc slugs ---")
        remapped_total = 0

        # Get all distinct category slugs currently in packages
        distinct_slugs = [
            row[0] for row in db.query(Package.category_slug).distinct().all()
            if row[0] is not None
        ]

        for slug in distinct_slugs:
            canonical = SLUG_MAP.get(slug)
            if canonical is None:
                # Not in our map — try lowercase
                canonical = SLUG_MAP.get(slug.lower())
            if canonical is None:
                # Still unknown — count packages, assign to "other" if small
                count = db.query(Package).filter(Package.category_slug == slug).count()
                if count <= 5:
                    canonical = "other"
                else:
                    # Try guessing from the slug name itself
                    canonical = _guess_category(slug.replace("-", " "), [], slug)
                print(f"  Unmapped slug '{slug}' ({count} pkgs) → '{canonical}'")

            if canonical != slug:
                count = (
                    db.execute(
                        text("UPDATE packages SET category_slug = :canonical WHERE category_slug = :old"),
                        {"canonical": canonical, "old": slug},
                    ).rowcount
                )
                if count:
                    print(f"  Remapped: {slug} → {canonical} ({count} packages)")
                    remapped_total += count

        db.commit()
        print(f"\n  Total packages remapped: {remapped_total}")

        # --- Step 2: Assign NULL-category packages ---
        print("\n--- Assigning NULL-category packages ---")
        null_pkgs = db.query(Package).filter(Package.category_slug.is_(None)).all()
        print(f"  Found {len(null_pkgs)} packages with NULL category")

        assigned = 0
        for pkg in null_pkgs:
            tags = []
            if pkg.tags:
                import json
                try:
                    tags = json.loads(pkg.tags)
                except (json.JSONDecodeError, TypeError):
                    tags = []

            guessed = _guess_category(pkg.what_it_does, tags, pkg.name)
            pkg.category_slug = guessed
            assigned += 1

        db.commit()
        print(f"  Assigned category to {assigned} packages")

        # --- Step 3: Fix canonical category names ---
        print("\n--- Fixing canonical category names ---")
        for slug, meta in CATEGORIES.items():
            cat = db.query(Category).filter_by(slug=slug).first()
            if cat:
                if cat.name != meta["name"] or cat.description != meta.get("description"):
                    old_name = cat.name
                    cat.name = meta["name"]
                    cat.description = meta.get("description")
                    print(f"  Fixed: '{old_name}' → '{meta['name']}'")
            else:
                # Create missing canonical category
                cat = Category(slug=slug, name=meta["name"], description=meta.get("description"))
                db.add(cat)
                print(f"  Created: {slug} ({meta['name']})")

        db.commit()

        # --- Step 4: Delete orphaned categories ---
        print("\n--- Deleting orphaned categories ---")
        canonical_slugs = set(CATEGORIES.keys())
        all_cats = db.query(Category).all()
        deleted = 0
        for cat in all_cats:
            if cat.slug not in canonical_slugs:
                pkg_count = db.query(Package).filter(Package.category_slug == cat.slug).count()
                if pkg_count == 0:
                    db.delete(cat)
                    print(f"  Deleted orphan: {cat.slug}")
                    deleted += 1
                else:
                    print(f"  WARNING: non-canonical '{cat.slug}' still has {pkg_count} packages!")

        db.commit()
        print(f"  Deleted {deleted} orphaned categories")

        # --- After stats ---
        cat_count_after = db.query(Category).count()
        print(f"\n=== After: {cat_count_after} categories ===\n")

        remaining_cats = db.query(Category).all()
        for cat in sorted(remaining_cats, key=lambda c: c.slug):
            pkg_count = db.query(Package).filter(Package.category_slug == cat.slug).count()
            eval_count = (
                db.query(Package)
                .filter(Package.category_slug == cat.slug, Package.af_score.isnot(None))
                .count()
            )
            print(f"  {cat.slug:25s}  {cat.name:30s}  {pkg_count:>5} total  {eval_count:>5} evaluated")

        total_pkgs = db.query(Package).count()
        total_eval = db.query(Package).filter(Package.af_score.isnot(None)).count()
        null_cat = db.query(Package).filter(Package.category_slug.is_(None)).count()
        print(f"\n  Total packages: {total_pkgs}")
        print(f"  Total evaluated: {total_eval}")
        print(f"  NULL category: {null_cat}")
        print(f"  Categories: {cat_count_before} → {cat_count_after}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
