"""Heartbeat orchestrator — runs all checks and reports results."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

from assay.database import SessionLocal

from .data import check_data_pipeline
from .feedback import check_feedback
from .health import HealthAlert, check_site_health


def run_heartbeat(
    base_url: str = "https://assay.tools",
    output_format: str = "text",
) -> list[HealthAlert]:
    """Run all heartbeat checks and return combined alerts."""
    all_alerts: list[HealthAlert] = []

    # Site health (no DB needed)
    print("Running site health checks ...")
    all_alerts.extend(check_site_health(base_url=base_url))

    # DB-dependent checks
    print("Running data pipeline checks ...")
    db = SessionLocal()
    try:
        all_alerts.extend(check_data_pipeline(db))
        all_alerts.extend(check_feedback(db))
    finally:
        db.close()

    # Sort by severity: critical > warning > info
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    all_alerts.sort(key=lambda a: severity_order.get(a.level, 3))

    # Output
    if output_format == "json":
        print(json.dumps([
            {
                "level": a.level,
                "check": a.check,
                "message": a.message,
                "timestamp": a.timestamp.isoformat(),
            }
            for a in all_alerts
        ], indent=2))
    else:
        _print_text_report(all_alerts)

    return all_alerts


def _print_text_report(alerts: list[HealthAlert]) -> None:
    """Print a human-readable heartbeat report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"\n{'=' * 60}")
    print(f"  Assay Heartbeat — {now}")
    print(f"{'=' * 60}")

    if not alerts:
        print("  All clear. No alerts.")
        print(f"{'=' * 60}\n")
        return

    criticals = [a for a in alerts if a.level == "critical"]
    warnings = [a for a in alerts if a.level == "warning"]
    infos = [a for a in alerts if a.level == "info"]

    if criticals:
        print(f"\n  CRITICAL ({len(criticals)}):")
        for a in criticals:
            print(f"    !! {a.message}")

    if warnings:
        print(f"\n  WARNINGS ({len(warnings)}):")
        for a in warnings:
            print(f"    !  {a.message}")

    if infos:
        print(f"\n  INFO ({len(infos)}):")
        for a in infos:
            print(f"       {a.message}")

    print(f"\n{'=' * 60}\n")

    # Exit code based on severity
    if criticals:
        sys.exit(2)
    elif warnings:
        sys.exit(1)


def main():
    """CLI entry point for heartbeat."""
    import argparse

    parser = argparse.ArgumentParser(description="Assay Heartbeat — business health checks")
    parser.add_argument(
        "--url", default="https://assay.tools",
        help="Base URL to check (default: https://assay.tools)",
    )
    parser.add_argument(
        "--format", choices=["text", "json"], default="text",
        help="Output format (default: text)",
    )
    args = parser.parse_args()

    run_heartbeat(base_url=args.url, output_format=args.format)


if __name__ == "__main__":
    main()
