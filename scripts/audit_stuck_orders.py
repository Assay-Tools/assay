#!/usr/bin/env python3
"""Audit stuck orders - find paid orders missing reports for >30min and attempt regeneration."""

import sys
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add parent dir to path to import assay modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from assay.database import SessionLocal
from assay.models import Order
from assay.reports.delivery import generate_report_for_order

def audit_stuck_orders() -> dict:
    """Find paid orders missing reports and attempt to regenerate them.

    Returns:
        dict with audit results including stuck orders and regeneration status
    """
    db: Session = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        audit_results = {
            "audit_timestamp": now.isoformat(),
            "stuck_orders": [],
            "summary": {
                "total_checked": 0,
                "total_stuck_30min": 0,
                "total_stuck_2h": 0,
                "regeneration_attempted": 0,
                "regeneration_succeeded": 0,
                "regeneration_failed": 0,
            }
        }

        # Query all paid orders (excluding monitoring_subscription type)
        paid_orders = (
            db.query(Order)
            .filter(
                Order.status == "paid",
                Order.order_type != "monitoring_subscription",
            )
            .all()
        )

        audit_results["summary"]["total_checked"] = len(paid_orders)

        for order in paid_orders:
            # Check if order has report_path (for report/brief orders, not monitoring subscriptions)
            if order.order_type in ("report", "brief"):
                if order.report_path is None:
                    # Calculate how long the order has been missing a report
                    if order.paid_at:
                        stuck_duration = now - order.paid_at
                    else:
                        stuck_duration = now - order.created_at

                    stuck_seconds = stuck_duration.total_seconds()
                    stuck_minutes = stuck_seconds / 60
                    stuck_hours = stuck_seconds / 3600

                    # Only report on orders stuck >30min
                    if stuck_minutes > 30:
                        order_info = {
                            "order_id": order.id,
                            "order_type": order.order_type,
                            "customer_email": order.customer_email,
                            "package_id": order.package_id,
                            "created_at": order.created_at.isoformat(),
                            "paid_at": order.paid_at.isoformat() if order.paid_at else None,
                            "stuck_duration_minutes": round(stuck_minutes, 2),
                            "stuck_duration_hours": round(stuck_hours, 2),
                            "regeneration_attempted": False,
                            "regeneration_status": None,
                            "regeneration_error": None,
                        }

                        # Determine if we should attempt regeneration (>30min but <2h) or escalate
                        if stuck_hours <= 2:
                            # Attempt regeneration
                            try:
                                report_path = generate_report_for_order(order, db)
                                if report_path:
                                    order_info["regeneration_attempted"] = True
                                    order_info["regeneration_status"] = "succeeded"
                                    audit_results["summary"]["regeneration_attempted"] += 1
                                    audit_results["summary"]["regeneration_succeeded"] += 1
                                    print(f"✓ Order {order.id}: Report regenerated - {report_path}")
                                else:
                                    order_info["regeneration_attempted"] = True
                                    order_info["regeneration_status"] = "failed"
                                    order_info["regeneration_error"] = "generate_report_for_order returned None"
                                    audit_results["summary"]["regeneration_attempted"] += 1
                                    audit_results["summary"]["regeneration_failed"] += 1
                                    print(f"✗ Order {order.id}: Report generation returned None")
                            except Exception as e:
                                order_info["regeneration_attempted"] = True
                                order_info["regeneration_status"] = "failed"
                                order_info["regeneration_error"] = str(e)
                                audit_results["summary"]["regeneration_attempted"] += 1
                                audit_results["summary"]["regeneration_failed"] += 1
                                print(f"✗ Order {order.id}: Regeneration failed - {e}")
                        else:
                            # Escalate: stuck >2h
                            order_info["regeneration_status"] = "escalated"
                            order_info["regeneration_error"] = "Order stuck >2 hours, requires human intervention"
                            audit_results["summary"]["total_stuck_2h"] += 1
                            print(f"⚠ Order {order.id}: ESCALATED - stuck {order_info['stuck_duration_hours']} hours")

                        audit_results["stuck_orders"].append(order_info)
                        audit_results["summary"]["total_stuck_30min"] += 1

        return audit_results

    finally:
        db.close()


def main():
    """Run audit and write results to artifact."""
    print("Starting stuck order audit...")

    results = audit_stuck_orders()

    # Write artifact
    artifact_dir = Path("/Users/aj/ai-data/projects/business-incubator/active/assay/artifacts/audit_stuck_orders/")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_file = artifact_dir / "stuck_order_report.json"

    with open(artifact_file, "w") as f:
        json.dump(results, f, indent=2)

    # Also write a human-readable markdown version
    markdown_file = artifact_dir / "stuck_order_report.md"
    write_markdown_report(results, markdown_file)

    print(f"\nAudit complete. Results written to:")
    print(f"  - {artifact_file}")
    print(f"  - {markdown_file}")
    print(f"\nSummary:")
    print(f"  Total orders checked: {results['summary']['total_checked']}")
    print(f"  Stuck >30min: {results['summary']['total_stuck_30min']}")
    print(f"  Stuck >2h (escalated): {results['summary']['total_stuck_2h']}")
    print(f"  Regeneration attempted: {results['summary']['regeneration_attempted']}")
    print(f"  Regeneration succeeded: {results['summary']['regeneration_succeeded']}")
    print(f"  Regeneration failed: {results['summary']['regeneration_failed']}")


def write_markdown_report(results: dict, output_file: Path):
    """Write a human-readable markdown report."""
    with open(output_file, "w") as f:
        f.write("# Stuck Order Audit Report\n\n")
        f.write(f"**Audit Timestamp**: {results['audit_timestamp']}\n\n")

        summary = results["summary"]
        f.write("## Summary\n\n")
        f.write(f"- **Total Orders Checked**: {summary['total_checked']}\n")
        f.write(f"- **Stuck >30min**: {summary['total_stuck_30min']}\n")
        f.write(f"- **Stuck >2h (Escalated)**: {summary['total_stuck_2h']}\n")
        f.write(f"- **Regeneration Attempted**: {summary['regeneration_attempted']}\n")
        f.write(f"- **Regeneration Succeeded**: {summary['regeneration_succeeded']}\n")
        f.write(f"- **Regeneration Failed**: {summary['regeneration_failed']}\n\n")

        if results["stuck_orders"]:
            f.write("## Stuck Orders\n\n")
            for order in results["stuck_orders"]:
                f.write(f"### Order {order['order_id']}\n\n")
                f.write(f"- **Type**: {order['order_type']}\n")
                f.write(f"- **Customer Email**: {order['customer_email']}\n")
                f.write(f"- **Package ID**: {order['package_id']}\n")
                f.write(f"- **Created**: {order['created_at']}\n")
                f.write(f"- **Paid At**: {order['paid_at']}\n")
                f.write(f"- **Stuck Duration**: {order['stuck_duration_hours']:.2f} hours ({order['stuck_duration_minutes']:.1f} minutes)\n")
                f.write(f"- **Regeneration Status**: {order['regeneration_status']}\n")
                if order['regeneration_error']:
                    f.write(f"- **Error**: {order['regeneration_error']}\n")
                f.write("\n")
        else:
            f.write("## Status\n\n")
            f.write("No stuck orders found. All paid report orders have report_path set.\n")


if __name__ == "__main__":
    main()
