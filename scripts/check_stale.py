#!/usr/bin/env python3
"""Check for stale packages needing re-evaluation.

Queries the Assay API for packages that haven't been evaluated in >90 days
and prints a summary. Designed to be run as a cron job or GitHub Action.

Usage:
    python scripts/check_stale.py                     # Print stale summary
    python scripts/check_stale.py --json              # JSON output
    python scripts/check_stale.py --limit 10          # Limit results
    python scripts/check_stale.py --base-url http://localhost:8000  # Local dev
"""

import argparse
import json
import sys
import urllib.request


def fetch_queue(base_url: str, limit: int) -> dict:
    """Fetch the evaluation queue from the Assay API."""
    url = f"{base_url}/v1/queue?limit={limit}&include_stale=true"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def main():
    parser = argparse.ArgumentParser(description="Check for stale Assay evaluations")
    parser.add_argument(
        "--base-url",
        default="https://assay.tools",
        help="Base URL for the Assay API (default: https://assay.tools)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of packages to return (default: 50)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output raw JSON",
    )
    args = parser.parse_args()

    try:
        data = fetch_queue(args.base_url, args.limit)
    except Exception as e:
        print(f"Error fetching queue: {e}", file=sys.stderr)
        sys.exit(1)

    if args.json_output:
        print(json.dumps(data, indent=2))
        return

    queue = data.get("queue", [])
    if not queue:
        print("No packages need re-evaluation.")
        return

    unevaluated = [p for p in queue if p["status"] == "unevaluated"]
    needs_reeval = [p for p in queue if p["status"] == "needs_reevaluation"]
    stale = [p for p in needs_reeval if p.get("reason") == "stale"]
    incomplete = [p for p in needs_reeval if p.get("reason") == "missing_sub_components"]

    print(f"Evaluation Queue: {data['count']} packages")
    print(f"  Unevaluated: {len(unevaluated)}")
    print(f"  Stale (>90 days): {len(stale)}")
    print(f"  Missing sub-components: {len(incomplete)}")
    print()

    if stale:
        print("Stale packages (oldest first):")
        for p in stale[:20]:
            last = p.get("last_evaluated", "unknown")[:10] if p.get("last_evaluated") else "never"
            score = p.get("current_af_score", "?")
            print(f"  {p['id']:40s}  AF={score:<6}  last={last}")

    if incomplete:
        print("\nMissing sub-components:")
        for p in incomplete[:20]:
            score = p.get("current_af_score", "?")
            print(f"  {p['id']:40s}  AF={score}")


if __name__ == "__main__":
    main()
