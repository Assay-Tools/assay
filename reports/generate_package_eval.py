#!/usr/bin/env python3
"""Generate a Package Evaluation Report ($99 product).

Pulls data from the Assay API for a specific package, computes all metrics,
and populates the template at reports/templates/package-evaluation.md.

Usage:
    python reports/generate_package_eval.py claude-api
    python reports/generate_package_eval.py sendbird-mcp --base-url http://localhost:8000
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


DEFAULT_BASE_URL = "https://assay.tools"
TEMPLATE_PATH = Path(__file__).parent / "templates" / "package-evaluation.md"
OUTPUT_DIR = Path(__file__).parent / "output" / "packages"


def api_get(base_url: str, path: str, params: dict | None = None) -> dict | None:
    """Make a GET request to the Assay API. Returns None on 404."""
    url = f"{base_url}/v1{path}"
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
        url = f"{url}?{qs}"
    req = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        if e.code == 404:
            return None
        raise


def score_to_rating(score: float | None) -> str:
    """Convert a numeric score to a text rating."""
    if score is None:
        return "N/A"
    if score >= 80:
        return "Excellent"
    if score >= 60:
        return "Good"
    if score >= 40:
        return "Fair"
    return "Poor"


def fmt_score(score: float | None) -> str:
    """Format a score for display."""
    if score is None:
        return "—"
    return f"{score:.1f}"


def compute_report_data(base_url: str, package_id: str) -> dict:
    """Compute all template variables for a package evaluation report."""
    # --- Fetch package ---
    pkg = api_get(base_url, f"/packages/{package_id}")
    if not pkg:
        raise ValueError(f"Package '{package_id}' not found")

    ar = pkg.get("agent_readiness") or {}
    iface = pkg.get("interface") or {}
    auth = pkg.get("auth") or {}
    pricing = pkg.get("pricing") or {}
    perf = pkg.get("performance") or {}
    reqs = pkg.get("requirements") or {}

    af = pkg.get("af_score")
    sec = pkg.get("security_score")
    rel = pkg.get("reliability_score")

    # --- Fetch category peers for competitive positioning ---
    category = pkg.get("category", "")
    category_display = category
    peers = []
    if category:
        cat_data = api_get(base_url, f"/categories/{category}/packages")
        if cat_data:
            peers = cat_data.get("packages", [])
            cat_info = cat_data.get("category", {})
            if cat_info and cat_info.get("name"):
                category_display = cat_info["name"]

    # Fetch alternatives for comparison
    alternatives = pkg.get("alternatives") or []
    compare_ids = [package_id] + alternatives[:4]
    competitors = []
    if len(compare_ids) > 1:
        comp_data = api_get(base_url, "/compare", {"ids": ",".join(compare_ids)})
        if comp_data:
            competitors = comp_data.get("packages", [])

    # --- Category stats ---
    peer_scores = [p["af_score"] for p in peers if p.get("af_score") and p["id"] != package_id]
    cat_avg = sum(peer_scores) / len(peer_scores) if peer_scores else 0
    cat_rank = 1
    for p in peers:
        if p.get("af_score") and p["af_score"] > (af or 0) and p["id"] != package_id:
            cat_rank += 1

    # --- Interface table ---
    iface_rows = []
    if iface.get("has_rest_api"):
        iface_rows.append("| REST API | Yes |")
    if iface.get("has_graphql"):
        iface_rows.append("| GraphQL | Yes |")
    if iface.get("has_grpc"):
        iface_rows.append("| gRPC | Yes |")
    if iface.get("has_mcp_server"):
        url = iface.get("mcp_server_url") or "Available"
        iface_rows.append(f"| MCP Server | {url} |")
    if iface.get("has_sdk"):
        langs = ", ".join(iface.get("sdk_languages") or [])
        iface_rows.append(f"| SDK | {langs} |")
    if iface.get("webhooks"):
        iface_rows.append("| Webhooks | Yes |")
    if iface.get("openapi_spec_url"):
        iface_rows.append(f"| OpenAPI Spec | {iface['openapi_spec_url']} |")

    interface_table = "| Interface | Details |\n|-----------|--------|\n"
    interface_table += "\n".join(iface_rows) if iface_rows else "| — | No interface data available |"

    # --- Auth section ---
    auth_lines = []
    methods = auth.get("methods") or []
    if methods:
        auth_lines.append(f"**Methods**: {', '.join(methods)}")
    if auth.get("oauth"):
        auth_lines.append("**OAuth**: Yes")
    if auth.get("scopes"):
        auth_lines.append("**Scopes**: Supported")
    if auth.get("notes"):
        auth_lines.append(f"\n{auth['notes']}")
    auth_section = "\n".join(auth_lines) if auth_lines else "_No authentication data available._"

    # --- Pricing section ---
    pricing_lines = []
    if pricing.get("model"):
        pricing_lines.append(f"**Model**: {pricing['model']}")
    if pricing.get("free_tier_exists"):
        limits = pricing.get("free_tier_limits") or "Available"
        pricing_lines.append(f"**Free Tier**: {limits}")
    if pricing.get("paid_tiers"):
        pricing_lines.append(f"**Paid Tiers**: {pricing['paid_tiers']}")
    if pricing.get("requires_credit_card"):
        pricing_lines.append("**Requires Credit Card**: Yes")
    if pricing.get("notes"):
        pricing_lines.append(f"\n{pricing['notes']}")
    pricing_section = "\n".join(pricing_lines) if pricing_lines else "_No pricing data available._"

    # --- Performance section ---
    perf_lines = []
    if perf.get("latency_p50_ms"):
        perf_lines.append(f"**Latency (p50)**: {perf['latency_p50_ms']}ms")
    if perf.get("latency_p99_ms"):
        perf_lines.append(f"**Latency (p99)**: {perf['latency_p99_ms']}ms")
    if perf.get("uptime_sla_percent"):
        perf_lines.append(f"**Uptime SLA**: {perf['uptime_sla_percent']}%")
    if perf.get("rate_limits"):
        perf_lines.append(f"**Rate Limits**: {perf['rate_limits']}")
    perf_section = "\n".join(perf_lines) if perf_lines else "_No performance data available._"

    # --- Use cases ---
    use_cases = pkg.get("use_cases") or []
    use_cases_md = "\n".join(f"- {uc}" for uc in use_cases) if use_cases else "_Not specified._"

    not_for = pkg.get("not_for") or []
    not_for_md = "\n".join(f"- {nf}" for nf in not_for) if not_for else "_Not specified._"

    # --- Gotchas ---
    gotchas = ar.get("known_agent_gotchas") or []
    if gotchas:
        gotchas_md = "\n".join(f"- {g}" for g in gotchas)
    else:
        gotchas_md = "_No known gotchas documented._"

    # --- Competitive positioning ---
    comp_lines = []
    if competitors:
        comp_lines.append(f"### Category: {category_display}")
        comp_lines.append(f"**Rank**: #{cat_rank} of {len(peers) + 1} evaluated packages")
        comp_lines.append(f"**Category Average AF Score**: {cat_avg:.1f}")
        comp_lines.append("")
        comp_lines.append("### Head-to-Head Comparison")
        comp_lines.append("")
        comp_lines.append("| Package | AF Score | Security | Reliability |")
        comp_lines.append("|---------|----------|----------|-------------|")
        for c in competitors:
            marker = " **(this package)**" if c["id"] == package_id else ""
            comp_lines.append(
                f"| {c['name']}{marker} | {fmt_score(c.get('af_score'))} | "
                f"{fmt_score(c.get('security_score'))} | {fmt_score(c.get('reliability_score'))} |"
            )
    else:
        comp_lines.append(f"**Category Rank**: #{cat_rank} of {len(peers) + 1} in {category_display}")
        comp_lines.append(f"**Category Average**: {cat_avg:.1f}")

    # --- Improvement recommendations ---
    recs = _generate_recommendations(pkg, ar, cat_avg)

    # --- Roadmap ---
    roadmap = _generate_roadmap(pkg, ar, recs)

    # --- Security notes ---
    sec_notes = ar.get("security_notes") or ""
    sec_notes_md = f"> {sec_notes}" if sec_notes else ""

    # --- Narratives (placeholders for Claude to fill) ---
    score_narrative = (
        f"{{{{NARRATIVE: Summarize {pkg['name']}'s AF Score of {fmt_score(af)} in context. "
        f"Compare to category average of {cat_avg:.1f}. Highlight strongest and weakest dimensions.}}}}"
    )
    security_narrative = (
        f"{{{{NARRATIVE: Analyze {pkg['name']}'s security posture. "
        f"Note any sub-components below 80 as improvement areas.}}}}"
    )
    reliability_narrative = (
        f"{{{{NARRATIVE: Brief assessment of {pkg['name']}'s reliability profile.}}}}"
    )
    interface_narrative = (
        f"{{{{NARRATIVE: Brief note on {pkg['name']}'s integration options and what they mean for agent adoption.}}}}"
    )

    last_eval = pkg.get("last_evaluated") or "Unknown"
    if last_eval != "Unknown":
        try:
            dt = datetime.fromisoformat(last_eval.replace("Z", "+00:00"))
            last_eval = dt.strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            pass

    return {
        "package_name": pkg["name"],
        "what_it_does": pkg.get("what_it_does") or "_No description available._",
        "category_name": category_display,
        "homepage": pkg.get("homepage") or "—",
        "repo_url": pkg.get("repo_url") or "—",
        "package_type": pkg.get("package_type") or "—",
        "last_evaluated": last_eval,
        "report_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "year": str(datetime.now(timezone.utc).year),
        # AF Score dimensions
        "af_score": fmt_score(af),
        "af_rating": score_to_rating(af),
        "documentation_accuracy": fmt_score(ar.get("documentation_accuracy")),
        "documentation_rating": score_to_rating(ar.get("documentation_accuracy")),
        "error_message_quality": fmt_score(ar.get("error_message_quality")),
        "error_message_rating": score_to_rating(ar.get("error_message_quality")),
        "auth_complexity": fmt_score(ar.get("auth_complexity")),
        "auth_complexity_rating": score_to_rating(ar.get("auth_complexity")),
        "mcp_server_quality": fmt_score(ar.get("mcp_server_quality")),
        "mcp_quality_rating": score_to_rating(ar.get("mcp_server_quality")),
        "rate_limit_clarity": fmt_score(ar.get("rate_limit_clarity")),
        "rate_limit_rating": score_to_rating(ar.get("rate_limit_clarity")),
        # Top-level scores
        "security_score": fmt_score(sec),
        "security_rating": score_to_rating(sec),
        "reliability_score": fmt_score(rel),
        "reliability_rating": score_to_rating(rel),
        # Security sub-components
        "tls_enforcement": fmt_score(ar.get("tls_enforcement")),
        "tls_rating": score_to_rating(ar.get("tls_enforcement")),
        "auth_strength": fmt_score(ar.get("auth_strength")),
        "auth_strength_rating": score_to_rating(ar.get("auth_strength")),
        "scope_granularity": fmt_score(ar.get("scope_granularity")),
        "scope_rating": score_to_rating(ar.get("scope_granularity")),
        "secret_handling": fmt_score(ar.get("secret_handling")),
        "secret_rating": score_to_rating(ar.get("secret_handling")),
        "dependency_hygiene": fmt_score(ar.get("dependency_hygiene")),
        "dep_hygiene_rating": score_to_rating(ar.get("dependency_hygiene")),
        # Reliability sub-components
        "uptime_documented": fmt_score(ar.get("uptime_documented")),
        "uptime_rating": score_to_rating(ar.get("uptime_documented")),
        "version_stability": fmt_score(ar.get("version_stability")),
        "version_rating": score_to_rating(ar.get("version_stability")),
        "breaking_changes_history": fmt_score(ar.get("breaking_changes_history")),
        "breaking_changes_rating": score_to_rating(ar.get("breaking_changes_history")),
        "error_recovery": fmt_score(ar.get("error_recovery")),
        "error_recovery_rating": score_to_rating(ar.get("error_recovery")),
        # Sections
        "security_notes": sec_notes_md,
        "interface_table": interface_table,
        "auth_section": auth_section,
        "pricing_section": pricing_section,
        "performance_section": perf_section,
        "best_when": pkg.get("best_when") or "_Not specified._",
        "avoid_when": pkg.get("avoid_when") or "_Not specified._",
        "use_cases": use_cases_md,
        "not_for": not_for_md,
        "gotchas_section": gotchas_md,
        "error_message_notes": ar.get("error_message_notes") or "_No error handling notes available._",
        "competitive_section": "\n".join(comp_lines),
        "recommendations": "\n".join(recs),
        "roadmap": roadmap,
        # Narratives
        "score_summary_narrative": score_narrative,
        "security_narrative": security_narrative,
        "reliability_narrative": reliability_narrative,
        "interface_narrative": interface_narrative,
    }


def _cat_name(slug: str) -> str:
    """Convert category slug to display name."""
    return slug.replace("-", " ").title() if slug else "Uncategorized"


def _generate_recommendations(pkg: dict, ar: dict, cat_avg: float) -> list[str]:
    """Generate prioritized improvement recommendations based on scores."""
    recs = []
    af = pkg.get("af_score") or 0

    # Check each dimension for improvement opportunities
    dims = [
        ("Documentation Accuracy", ar.get("documentation_accuracy"), "documentation"),
        ("Error Message Quality", ar.get("error_message_quality"), "errors"),
        ("Auth Complexity", ar.get("auth_complexity"), "auth"),
        ("MCP Server Quality", ar.get("mcp_server_quality"), "mcp"),
        ("Rate Limit Clarity", ar.get("rate_limit_clarity"), "rate_limits"),
    ]

    sec_dims = [
        ("TLS Enforcement", ar.get("tls_enforcement")),
        ("Auth Strength", ar.get("auth_strength")),
        ("Scope Granularity", ar.get("scope_granularity")),
        ("Secret Handling", ar.get("secret_handling")),
        ("Dependency Hygiene", ar.get("dependency_hygiene")),
    ]

    # Sort by score ascending — worst dimensions first
    scored_dims = [(name, score, key) for name, score, key in dims if score is not None]
    scored_dims.sort(key=lambda x: x[1])

    priority = 1
    for name, score, key in scored_dims:
        if score < 60:
            recs.append(f"**P{priority} — {name} ({score:.0f}/100)**: "
                       f"{{{{RECOMMENDATION: Specific actionable improvement for {name.lower()} "
                       f"based on score of {score:.0f}.}}}}")
            priority += 1
        elif score < 80:
            recs.append(f"**P{priority} — {name} ({score:.0f}/100)**: "
                       f"{{{{RECOMMENDATION: Targeted improvement to reach Excellent tier for {name.lower()}.}}}}")
            priority += 1

    # Security recommendations
    scored_sec = [(name, score) for name, score in sec_dims if score is not None]
    scored_sec.sort(key=lambda x: x[1])
    for name, score in scored_sec:
        if score < 70:
            recs.append(f"**P{priority} — Security: {name} ({score:.0f}/100)**: "
                       f"{{{{RECOMMENDATION: Security improvement for {name.lower()}.}}}}")
            priority += 1

    if not recs:
        recs.append("This package scores well across all evaluated dimensions. "
                    "Maintain current quality levels and consider adding MCP server support "
                    "if not already present to maximize agent accessibility.")

    return recs


def _generate_roadmap(pkg: dict, ar: dict, recs: list[str]) -> str:
    """Generate an agent-readiness roadmap based on current scores."""
    af = pkg.get("af_score") or 0

    if af >= 85:
        phase = "**Current Status: Leader** — This package is among the top-rated in the ecosystem."
        next_step = "Focus on maintaining quality across releases and expanding integration options."
    elif af >= 70:
        phase = "**Current Status: Competitive** — This package performs above average but has clear room to improve."
        next_step = "Address the highest-priority recommendations above to break into the Excellent tier (80+)."
    elif af >= 55:
        phase = "**Current Status: Developing** — This package meets basic agent-friendliness criteria but needs investment."
        next_step = "Prioritize documentation accuracy and error message quality — these two dimensions have the highest impact on AF Score."
    else:
        phase = "**Current Status: Early Stage** — Significant work needed to make this package reliably agent-friendly."
        next_step = "Start with documentation: ensure docs match actual API behavior. Then add structured error responses with actionable messages."

    return f"""{phase}

{next_step}

{{{{NARRATIVE: 3-5 bullet roadmap of specific next steps for this package to improve its AF Score, ordered by expected impact.}}}}"""


def render_template(template: str, data: dict) -> str:
    """Simple mustache-style template rendering."""
    result = template
    for key, value in data.items():
        result = result.replace("{{" + key + "}}", str(value))
    return result


def main():
    parser = argparse.ArgumentParser(description="Generate Assay Package Evaluation Report")
    parser.add_argument("package_id", help="Package ID (e.g., claude-api, sendbird-mcp)")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Assay API base URL")
    parser.add_argument("--output", help="Output file path")
    args = parser.parse_args()

    # Load template
    if not TEMPLATE_PATH.exists():
        print(f"Template not found: {TEMPLATE_PATH}", file=sys.stderr)
        sys.exit(1)
    template = TEMPLATE_PATH.read_text()

    # Gather data
    print(f"Generating evaluation report for '{args.package_id}'...", file=sys.stderr)
    data = compute_report_data(args.base_url, args.package_id)

    # Render
    report = render_template(template, data)

    # Output
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.output) if args.output else OUTPUT_DIR / f"{args.package_id}.md"
    out_path.write_text(report)
    print(f"Report written to {out_path}", file=sys.stderr)

    # Show narrative placeholders
    import re
    narratives = re.findall(r"\{\{(?:NARRATIVE|RECOMMENDATION):.*?\}\}", report)
    if narratives:
        print(f"\n{len(narratives)} sections need narrative writing:", file=sys.stderr)
        for n in narratives:
            print(f"  - {n[:80]}...", file=sys.stderr)


if __name__ == "__main__":
    main()
