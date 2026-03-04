#!/usr/bin/env python3
"""Generate the Quarterly State of Agentic Software report.

Pulls data from the Assay API, computes metrics, and populates the
template at reports/templates/quarterly-ecosystem.md.

Usage:
    python reports/generate_quarterly.py --quarter Q1 --year 2026
    python reports/generate_quarterly.py --quarter Q1 --year 2026 --base-url http://localhost:8000
"""

import argparse
import json
import sys
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError


DEFAULT_BASE_URL = "https://assay.tools"
TEMPLATE_PATH = Path(__file__).parent / "templates" / "quarterly-ecosystem.md"
OUTPUT_DIR = Path(__file__).parent / "output"


def api_get(base_url: str, path: str, params: dict | None = None) -> dict:
    """Make a GET request to the Assay API."""
    url = f"{base_url}/v1{path}"
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
        url = f"{url}?{qs}"
    req = Request(url, headers={"Accept": "application/json"})
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def fetch_all_packages(base_url: str, min_af_score: float = 0.01) -> list[dict]:
    """Fetch all evaluated packages via pagination."""
    packages = []
    offset = 0
    limit = 100
    while True:
        data = api_get(base_url, "/packages", {
            "min_af_score": min_af_score,
            "limit": limit,
            "offset": offset,
            "sort": "af_score:desc",
        })
        batch = data.get("packages", [])
        packages.extend(batch)
        if len(batch) < limit:
            break
        offset += limit
    return packages


def compute_report_data(base_url: str, quarter: str, year: str) -> dict:
    """Compute all template variables from API data."""
    # --- Core stats ---
    stats = api_get(base_url, "/stats")
    dist = stats["score_distribution"]

    total_evaluated = stats["total_evaluated"]
    excellent = dist["excellent"]
    good = dist["good"]
    fair = dist["fair"]
    poor = dist["poor"]

    scored_total = excellent + good + fair + poor
    pct = lambda n: round(n / scored_total * 100, 1) if scored_total else 0

    # --- All evaluated packages ---
    print("Fetching all evaluated packages...", file=sys.stderr)
    all_packages = fetch_all_packages(base_url)
    print(f"  Retrieved {len(all_packages)} packages", file=sys.stderr)

    top_af = all_packages[0]["af_score"] if all_packages else 0
    bottom_af = all_packages[-1]["af_score"] if all_packages else 0

    # --- Top 10 packages table ---
    top_10 = all_packages[:10]
    top_table_rows = []
    for i, pkg in enumerate(top_10, 1):
        sec = pkg.get("security_score")
        rel = pkg.get("reliability_score")
        sec_str = f"{sec:.1f}" if sec is not None else "—"
        rel_str = f"{rel:.1f}" if rel is not None else "—"
        top_table_rows.append(
            f"| {i} | {pkg['name']} | {pkg.get('category', '—')} | "
            f"{pkg['af_score']:.1f} | {sec_str} | {rel_str} |"
        )

    # --- Categories ---
    print("Fetching categories...", file=sys.stderr)
    cat_data = api_get(base_url, "/categories")
    categories = cat_data.get("categories", cat_data)

    # Filter to categories with packages, sort by package_count desc
    active_cats = [c for c in categories if c.get("package_count", 0) > 0]
    active_cats.sort(key=lambda c: c["package_count"], reverse=True)

    # Compute per-category stats from package data
    cat_packages = {}
    for pkg in all_packages:
        cat = pkg.get("category", "uncategorized")
        cat_packages.setdefault(cat, []).append(pkg)

    cat_table_rows = []
    cat_spotlights = []
    for cat_info in active_cats:
        slug = cat_info["slug"]
        name = cat_info["name"]
        total_in_cat = cat_info["package_count"]
        pkgs_in_cat = cat_packages.get(slug, [])
        evaluated = len(pkgs_in_cat)
        if evaluated == 0:
            continue
        scores = [p["af_score"] for p in pkgs_in_cat if p.get("af_score")]
        avg_score = sum(scores) / len(scores) if scores else 0
        top_score = max(scores) if scores else 0
        cat_table_rows.append(
            f"| {name} | {total_in_cat} | {evaluated} | "
            f"{avg_score:.1f} | {top_score:.1f} |"
        )

        # Spotlight for top 5 categories (skip "other" catch-all)
        if len(cat_spotlights) < 5 and evaluated >= 3 and slug != "other":
            # Deduplicate by name
            seen_names = set()
            top_3 = []
            for p in pkgs_in_cat:
                if p["name"] not in seen_names:
                    seen_names.add(p["name"])
                    top_3.append(p)
                if len(top_3) == 3:
                    break
            spotlight = f"#### {name}\n\n"
            spotlight += f"**{evaluated} packages evaluated** (out of {total_in_cat} tracked) — "
            spotlight += f"Average AF Score: {avg_score:.1f}\n\n"
            spotlight += "| Package | AF Score | Standout Quality |\n"
            spotlight += "|---------|----------|------------------|\n"
            for p in top_3:
                # Pick the strongest sub-dimension as standout
                standout = _best_dimension(p)
                spotlight += f"| {p['name']} | {p['af_score']:.1f} | {standout} |\n"
            spotlight += "\n*{{NARRATIVE: Brief insight on " + name + " category quality patterns.}}*\n"
            cat_spotlights.append(spotlight)

    # --- Security leaders ---
    # Filter to packages with real service interfaces (not local-only libraries)
    sec_candidates = [
        p for p in all_packages
        if p.get("security_score") is not None and _is_service(p)
    ]
    sec_sorted = sorted(sec_candidates, key=lambda p: p["security_score"], reverse=True)
    sec_leaders_rows = []
    sec_seen = set()
    for pkg in sec_sorted:
        if pkg["name"] in sec_seen:
            continue
        sec_seen.add(pkg["name"])
        if len(sec_leaders_rows) >= 10:
            break
        strengths = _security_strengths(pkg)
        sec_leaders_rows.append(
            f"| {pkg['name']} | {pkg.get('category', '—')} | "
            f"{pkg['security_score']:.1f} | {strengths} |"
        )

    # --- Common gotchas ---
    gotcha_counts: dict[str, int] = {}
    for pkg in all_packages:
        ar = pkg.get("agent_readiness", {})
        if ar and isinstance(ar, dict):
            gotchas = ar.get("known_agent_gotchas", [])
            if isinstance(gotchas, list):
                for g in gotchas:
                    if isinstance(g, str) and g.strip():
                        # Normalize similar gotchas
                        key = g.strip()[:80]
                        gotcha_counts[key] = gotcha_counts.get(key, 0) + 1

    top_gotchas = sorted(gotcha_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    gotcha_lines = []
    for gotcha, count in top_gotchas:
        gotcha_lines.append(f"- **{gotcha}** ({count} packages)")

    # --- Assemble template variables ---
    return {
        "quarter": quarter,
        "year": year,
        "total_packages": f"{stats['total_packages']:,}",
        "total_evaluated": f"{total_evaluated:,}",
        "total_categories": str(stats["total_categories"]),
        "avg_af_score": f"{stats['avg_af_score']:.1f}",
        "top_af_score": f"{top_af:.1f}",
        "bottom_af_score": f"{bottom_af:.1f}",
        "excellent_count": str(excellent),
        "excellent_pct": str(pct(excellent)),
        "good_count": str(good),
        "good_pct": str(pct(good)),
        "fair_count": str(fair),
        "fair_pct": str(pct(fair)),
        "poor_count": str(poor),
        "poor_pct": str(pct(poor)),
        "top_packages_table": "\n".join(top_table_rows),
        "category_table": "\n".join(cat_table_rows),
        "category_spotlights": "\n\n".join(cat_spotlights),
        "security_leaders_table": "\n".join(sec_leaders_rows),
        "common_gotchas": "\n".join(gotcha_lines) if gotcha_lines else "_No gotcha data available yet — this section will be populated as evaluations mature._",
        # Narrative sections — placeholders for Claude to fill in
        "executive_summary": "{{NARRATIVE: Write 2-3 paragraphs summarizing the Q1 2026 state of the agentic software ecosystem. Reference key numbers.}}",
        "score_distribution_insight": "{{NARRATIVE: One paragraph interpreting the score distribution — what does this tell us about ecosystem maturity?}}",
        "top_packages_insight": "{{NARRATIVE: Brief analysis of what the top-scoring packages have in common.}}",
        "category_insight": "{{NARRATIVE: Observations about category-level quality patterns.}}",
        "security_section": "{{NARRATIVE: 1-2 paragraphs on the overall security posture of the agentic software ecosystem.}}",
        "security_gaps": "{{NARRATIVE: Bullet list of the most common security weaknesses seen across evaluated packages.}}",
        "agent_readiness_patterns": "{{NARRATIVE: What patterns distinguish highly agent-friendly packages from mediocre ones?}}",
        "trends_section": "{{NARRATIVE: 2-3 paragraphs on emerging trends in the agentic software ecosystem for Q1 2026.}}",
    }


def _is_service(pkg: dict) -> bool:
    """Check if a package represents a networked service (not a local-only library)."""
    iface = pkg.get("interface") or {}
    if iface.get("has_rest_api") or iface.get("has_graphql") or iface.get("has_grpc"):
        return True
    if iface.get("has_mcp_server"):
        return True
    # Auth-only packages with just "none" are local libraries, not services
    auth = pkg.get("auth") or {}
    methods = auth.get("methods") or []
    if methods and set(methods) - {"none"}:
        return True
    return False


def _best_dimension(pkg: dict) -> str:
    """Return a human-readable label for the package's strongest quality."""
    ar = pkg.get("agent_readiness", {})
    if not ar or not isinstance(ar, dict):
        return "—"

    dims = {
        "MCP Quality": ar.get("mcp_server_quality"),
        "Documentation": ar.get("documentation_accuracy"),
        "Error Messages": ar.get("error_message_quality"),
        "Auth Simplicity": ar.get("auth_complexity"),
        "Security": pkg.get("security_score"),
    }
    scored = {k: v for k, v in dims.items() if v is not None}
    if not scored:
        return "—"
    best = max(scored, key=scored.get)
    return f"{best} ({scored[best]:.0f})"


def _security_strengths(pkg: dict) -> str:
    """Return a brief summary of security strengths."""
    ar = pkg.get("agent_readiness", {})
    if not ar or not isinstance(ar, dict):
        return "—"

    strengths = []
    if (v := ar.get("tls_enforcement")) and v >= 80:
        strengths.append("TLS")
    if (v := ar.get("auth_strength")) and v >= 80:
        strengths.append("Auth")
    if (v := ar.get("scope_granularity")) and v >= 80:
        strengths.append("Scoping")
    if (v := ar.get("secret_handling")) and v >= 80:
        strengths.append("Secrets")
    if (v := ar.get("dependency_hygiene")) and v >= 80:
        strengths.append("Deps")

    return ", ".join(strengths) if strengths else "Balanced"


def render_template(template: str, data: dict) -> str:
    """Simple mustache-style template rendering."""
    result = template
    for key, value in data.items():
        result = result.replace("{{" + key + "}}", str(value))
    return result


def main():
    parser = argparse.ArgumentParser(description="Generate Assay Quarterly Report")
    parser.add_argument("--quarter", required=True, help="Quarter label (e.g., Q1)")
    parser.add_argument("--year", required=True, help="Year (e.g., 2026)")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Assay API base URL")
    parser.add_argument("--output", help="Output file path (default: reports/output/QUARTER-YEAR.md)")
    args = parser.parse_args()

    # Load template
    if not TEMPLATE_PATH.exists():
        print(f"Template not found: {TEMPLATE_PATH}", file=sys.stderr)
        sys.exit(1)
    template = TEMPLATE_PATH.read_text()

    # Gather data
    print(f"Generating {args.quarter} {args.year} report from {args.base_url}...", file=sys.stderr)
    data = compute_report_data(args.base_url, args.quarter, args.year)

    # Render
    report = render_template(template, data)

    # Output
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.output) if args.output else OUTPUT_DIR / f"{args.quarter}-{args.year}.md"
    out_path.write_text(report)
    print(f"Report written to {out_path}", file=sys.stderr)

    # Show narrative placeholders that need filling
    import re
    narratives = re.findall(r"\{\{NARRATIVE:.*?\}\}", report)
    if narratives:
        print(f"\n{len(narratives)} narrative sections need writing:", file=sys.stderr)
        for n in narratives:
            print(f"  - {n[:80]}...", file=sys.stderr)


if __name__ == "__main__":
    main()
