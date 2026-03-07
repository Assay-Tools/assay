"""Assay CLI — query the Assay API from the command line.

Usage:
    assay check <package>          Show scores for a package
    assay compare <a> <b> [<c>]    Compare packages side by side
    assay stale [--days N]         List packages needing re-evaluation
"""

import argparse
import json
import sys

import httpx

DEFAULT_BASE_URL = "https://assay.tools"


def _client(base_url: str) -> httpx.Client:
    return httpx.Client(base_url=base_url, timeout=15, follow_redirects=True)


def _score_bar(score: float | None, width: int = 20) -> str:
    """Render a simple ASCII bar for a score."""
    if score is None:
        return "N/A"
    filled = round(score / 100 * width)
    bar = "#" * filled + "-" * (width - filled)
    return f"[{bar}] {score:.0f}/100"


def cmd_check(args):
    """Show scores and details for a single package."""
    with _client(args.base_url) as client:
        resp = client.get(f"/v1/packages/{args.package}")
        if resp.status_code == 404:
            print(f"Package '{args.package}' not found.")
            sys.exit(1)
        resp.raise_for_status()
        pkg = resp.json()

    print(f"\n  {pkg['name']}  ({pkg['id']})")
    if pkg.get("what_it_does"):
        print(f"  {pkg['what_it_does']}")
    print()

    print(f"  AF Score:          {_score_bar(pkg.get('af_score'))}")
    print(f"  Security:          {_score_bar(pkg.get('security_score'))}")
    print(f"  Reliability:       {_score_bar(pkg.get('reliability_score'))}")
    print()

    if pkg.get("category"):
        cat = pkg["category"]
        if isinstance(cat, dict):
            print(f"  Category:          {cat.get('name', 'Unknown')}")
        else:
            print(f"  Category:          {cat}")

    if pkg.get("last_evaluated"):
        print(f"  Last evaluated:    {pkg['last_evaluated'][:10]}")
    if pkg.get("version_evaluated"):
        print(f"  Version evaluated: {pkg['version_evaluated']}")

    # Interface
    iface = pkg.get("interface")
    if iface:
        caps = []
        if iface.get("has_rest_api"):
            caps.append("REST")
        if iface.get("has_graphql"):
            caps.append("GraphQL")
        if iface.get("has_mcp_server"):
            caps.append("MCP")
        if iface.get("has_sdk"):
            langs = iface.get("sdk_languages", [])
            if isinstance(langs, str):
                try:
                    langs = json.loads(langs)
                except (json.JSONDecodeError, TypeError):
                    langs = []
            caps.append(f"SDK ({', '.join(langs)})" if langs else "SDK")
        if caps:
            print(f"  Interface:         {', '.join(caps)}")

    # Agent readiness highlights
    ar = pkg.get("agent_readiness")
    if ar:
        gotchas = ar.get("known_agent_gotchas")
        if gotchas:
            if isinstance(gotchas, str):
                try:
                    gotchas = json.loads(gotchas)
                except (json.JSONDecodeError, TypeError):
                    gotchas = []
            if gotchas:
                print("\n  Gotchas:")
                for g in gotchas:
                    print(f"    - {g}")

    if pkg.get("best_when"):
        print(f"\n  Best when:         {pkg['best_when']}")
    if pkg.get("avoid_when"):
        print(f"  Avoid when:        {pkg['avoid_when']}")

    print()

    if args.json:
        print(json.dumps(pkg, indent=2))


def cmd_compare(args):
    """Compare packages side by side."""
    ids = ",".join(args.packages)
    with _client(args.base_url) as client:
        resp = client.get(f"/v1/compare?ids={ids}")
        if resp.status_code == 404:
            print(f"Error: {resp.json().get('detail', 'Packages not found')}")
            sys.exit(1)
        resp.raise_for_status()
        data = resp.json()

    packages = data.get("packages", [])
    if not packages:
        print("No packages found.")
        sys.exit(1)

    if args.json:
        print(json.dumps(data, indent=2))
        return

    # Table header
    name_width = max(len(p.get("name", p["id"])) for p in packages) + 2
    header = f"  {'Package':<{name_width}} {'AF':>6} {'Security':>10} {'Reliability':>13}"
    print(f"\n{header}")
    print("  " + "-" * (len(header) - 2))

    for pkg in sorted(packages, key=lambda p: p.get("af_score") or 0, reverse=True):
        name = pkg.get("name", pkg["id"])
        af = f"{pkg['af_score']:.0f}" if pkg.get("af_score") is not None else "N/A"
        sec = f"{pkg['security_score']:.0f}" if pkg.get("security_score") is not None else "N/A"
        rel = (
            f"{pkg['reliability_score']:.0f}"
            if pkg.get("reliability_score") is not None
            else "N/A"
        )
        print(f"  {name:<{name_width}} {af:>6} {sec:>10} {rel:>13}")

    print()


def cmd_stale(args):
    """List packages needing re-evaluation."""
    with _client(args.base_url) as client:
        resp = client.get(
            "/v1/queue",
            params={"limit": args.limit, "include_stale": True},
        )
        resp.raise_for_status()
        data = resp.json()

    queue = data.get("queue", [])

    if args.json:
        print(json.dumps(data, indent=2))
        return

    if not queue:
        print("\n  No packages in the evaluation queue.\n")
        return

    # Group by status
    needs_eval = [p for p in queue if p["status"] == "needs_evaluation"]
    needs_reeval = [p for p in queue if p["status"] == "needs_reevaluation"]

    if needs_eval:
        print(f"\n  Needs evaluation ({len(needs_eval)}):")
        for p in needs_eval:
            priority = f" [{p['priority']}]" if p.get("priority") else ""
            stars = f" ({p['stars']} stars)" if p.get("stars") else ""
            print(f"    {p['id']}{priority}{stars}")

    if needs_reeval:
        print(f"\n  Needs re-evaluation ({len(needs_reeval)}):")
        for p in needs_reeval:
            reason = p.get("reason", "unknown")
            last = p.get("last_evaluated", "")[:10] if p.get("last_evaluated") else "never"
            af = f"AF:{p['current_af_score']:.0f}" if p.get("current_af_score") else ""
            print(f"    {p['id']}  (reason: {reason}, last: {last}) {af}")

    print(f"\n  Total: {data.get('count', len(queue))} packages\n")


def cmd_newsletter(args):
    """Newsletter pipeline: collect data, or send a ready newsletter."""
    from assay.database import SessionLocal, init_db

    init_db()
    db = SessionLocal()

    try:
        if args.action == "collect":
            _newsletter_collect(db)
        elif args.action == "send":
            _newsletter_send(db, args.dry_run)
        else:
            print(f"Unknown action: {args.action}")
            sys.exit(1)
    finally:
        db.close()


def _newsletter_collect(db):
    """Collect weekly data and save prompt for Claude Code session."""
    from assay.newsletter.collector import collect_weekly_data
    from assay.newsletter.writer import generate_subject, save_digest_for_session

    print("Collecting weekly data...")
    digest = collect_weekly_data(db)
    print(
        f"  {len(digest.new_packages)} new packages, "
        f"{len(digest.score_movers)} movers, "
        f"{len(digest.newly_evaluated)} newly evaluated"
    )

    subject = generate_subject(digest)
    print(f"  Subject: {subject}")

    prompt_path = save_digest_for_session(digest)
    print(f"  Data + prompt saved to: {prompt_path.parent}")
    print("  Claude Code session will write the newsletter content.")


def _newsletter_send(db, dry_run: bool = False):
    """Send the most recent ready newsletter to subscribers."""
    from assay.newsletter.sender import get_active_subscribers, send_newsletter_issue
    from assay.newsletter.writer import NEWSLETTER_DIR

    ready_dir = NEWSLETTER_DIR / "ready"
    if not ready_dir.exists():
        print("No ready newsletters found. Run the newsletter session first.")
        sys.exit(1)

    # Find most recent newsletter
    meta_files = sorted(ready_dir.glob("newsletter-*.json"), reverse=True)
    if not meta_files:
        print("No ready newsletters found.")
        sys.exit(1)

    import json
    meta_path = meta_files[0]
    meta = json.loads(meta_path.read_text())
    date_str = meta["date"]
    subject = meta["subject"]

    html_path = ready_dir / f"newsletter-{date_str}.html"
    text_path = ready_dir / f"newsletter-{date_str}.txt"

    if not html_path.exists() or not text_path.exists():
        print(f"Missing content files for {date_str}")
        sys.exit(1)

    html_content = html_path.read_text()
    text_content = text_path.read_text()

    print(f"Newsletter: {subject}")
    print(f"  HTML: {len(html_content)} chars, Text: {len(text_content)} chars")

    subscribers = get_active_subscribers(db)
    print(f"  {len(subscribers)} confirmed subscribers")

    if not subscribers:
        print("  No confirmed subscribers. Saving issue without sending.")

    issue = send_newsletter_issue(
        db, subject, html_content, text_content, dry_run=dry_run,
    )
    print(f"  Issue #{issue.id}: {issue.recipients_count} recipients")
    if dry_run:
        print("  (dry run — no emails were actually sent)")

    # Archive the sent newsletter
    sent_dir = NEWSLETTER_DIR / "sent"
    sent_dir.mkdir(parents=True, exist_ok=True)
    for f in ready_dir.glob(f"newsletter-{date_str}.*"):
        f.rename(sent_dir / f.name)
    print(f"  Archived to {sent_dir}")


def main():
    parser = argparse.ArgumentParser(
        prog="assay",
        description="Assay CLI — query package quality scores",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Assay API base URL (default: {DEFAULT_BASE_URL})",
    )

    subparsers = parser.add_subparsers(dest="command")

    # check
    check_p = subparsers.add_parser("check", help="Show scores for a package")
    check_p.add_argument("package", help="Package ID (e.g., stripe)")
    check_p.add_argument("--json", action="store_true", help="Output raw JSON")

    # compare
    compare_p = subparsers.add_parser("compare", help="Compare packages")
    compare_p.add_argument("packages", nargs="+", help="Package IDs to compare")
    compare_p.add_argument("--json", action="store_true", help="Output raw JSON")

    # stale
    stale_p = subparsers.add_parser(
        "stale", help="List packages needing evaluation",
    )
    stale_p.add_argument(
        "--days", type=int, default=90, help="Days threshold (default: 90)",
    )
    stale_p.add_argument(
        "--limit", type=int, default=50, help="Max results (default: 50)",
    )
    stale_p.add_argument("--json", action="store_true", help="Output raw JSON")

    # newsletter
    news_p = subparsers.add_parser(
        "newsletter", help="Newsletter pipeline (collect data or send)",
    )
    news_p.add_argument(
        "action",
        choices=["collect", "send"],
        help="collect: gather data + save prompt, send: deliver ready newsletter",
    )
    news_p.add_argument(
        "--dry-run", action="store_true",
        help="Record the issue but don't actually send emails",
    )

    args = parser.parse_args()

    if args.command == "check":
        cmd_check(args)
    elif args.command == "compare":
        cmd_compare(args)
    elif args.command == "stale":
        cmd_stale(args)
    elif args.command == "newsletter":
        cmd_newsletter(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
