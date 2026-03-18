#!/usr/bin/env python3
"""
Revenue reconciliation: Compare Stripe charges against Assay database orders.
Matches payments (last 24-48 hours) between Stripe and the database.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import stripe
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Load environment
env_file = Path(__file__).parent.parent / ".secrets"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key] = value

DATABASE_URL = os.environ.get("DATABASE_URL")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in environment")
    sys.exit(1)
if not STRIPE_SECRET_KEY:
    print("ERROR: STRIPE_SECRET_KEY not found in environment")
    sys.exit(1)

stripe.api_key = STRIPE_SECRET_KEY


def get_db_session():
    """Create database session."""
    engine = create_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine)
    return Session()


def get_stripe_charges(hours=None):
    """Fetch all succeeded charges from Stripe (or last N hours if specified)."""
    charges = []
    try:
        # Pagination through Stripe API
        params = {"limit": 100}

        if hours:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
            cutoff_timestamp = int(cutoff.timestamp())
            params["created"] = {"gte": cutoff_timestamp}

        has_more = True
        starting_after = None

        while has_more:
            if starting_after:
                params["starting_after"] = starting_after

            response = stripe.Charge.list(**params)
            charges.extend(response.data)
            has_more = response.has_more
            if has_more and response.data:
                starting_after = response.data[-1].id

    except stripe.error.StripeError as e:
        print(f"ERROR fetching Stripe charges: {e}")
        return []

    return charges


def get_db_orders(hours=None):
    """Fetch paid orders from database (all time if hours=None, or last N hours)."""
    db = get_db_session()
    try:
        query_str = """
            SELECT
                id,
                access_token,
                package_id,
                order_type,
                status,
                stripe_session_id,
                stripe_payment_intent,
                stripe_subscription_id,
                stripe_customer_id,
                customer_email,
                amount_cents,
                currency,
                created_at,
                paid_at
            FROM orders
            WHERE status = 'paid'
        """

        params = {}
        if hours:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
            query_str += " AND paid_at >= :cutoff"
            params["cutoff"] = cutoff

        query_str += " ORDER BY paid_at DESC"

        query = text(query_str)
        result = db.execute(query, params)
        rows = result.fetchall()

        orders = []
        for row in rows:
            orders.append({
                "id": row[0],
                "access_token": row[1],
                "package_id": row[2],
                "order_type": row[3],
                "status": row[4],
                "stripe_session_id": row[5],
                "stripe_payment_intent": row[6],
                "stripe_subscription_id": row[7],
                "stripe_customer_id": row[8],
                "customer_email": row[9],
                "amount_cents": row[10],
                "currency": row[11],
                "created_at": row[12],
                "paid_at": row[13],
            })
        return orders
    finally:
        db.close()


def reconcile(hours=None):
    """Match Stripe charges to database orders."""
    print("=" * 80)
    print("ASSAY REVENUE RECONCILIATION")
    print("=" * 80)
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    period_str = f"Last {hours} hours" if hours else "All time"
    print(f"Lookback Period: {period_str}")
    print()

    # Fetch data
    if hours:
        print(f"Fetching Stripe charges (last {hours} hours)...")
    else:
        print("Fetching all Stripe charges...")
    stripe_charges = get_stripe_charges(hours=hours)
    print(f"  Found {len(stripe_charges)} succeeded charges")

    if hours:
        print(f"Fetching database orders (last {hours} hours, status=paid)...")
    else:
        print("Fetching all database orders (status=paid)...")
    db_orders = get_db_orders(hours=hours)
    print(f"  Found {len(db_orders)} paid orders")
    print()

    # Build lookup maps
    stripe_by_intent = {c.id: c for c in stripe_charges if c.id}
    stripe_by_customer_amount = {}
    for charge in stripe_charges:
        key = (charge.customer, charge.amount)
        if key not in stripe_by_customer_amount:
            stripe_by_customer_amount[key] = []
        stripe_by_customer_amount[key].append(charge)

    # Track matches and mismatches
    matched_orders = []
    unmatched_orders = []
    unmatched_charges = set(c.id for c in stripe_charges)
    missing_webhooks = []

    # Match orders to charges
    for order in db_orders:
        matched = False

        # Try exact match by payment intent
        if order["stripe_payment_intent"]:
            if order["stripe_payment_intent"] in stripe_by_intent:
                charge = stripe_by_intent[order["stripe_payment_intent"]]
                matched_orders.append({
                    "order_id": order["id"],
                    "package_id": order["package_id"],
                    "order_type": order["order_type"],
                    "amount_cents": order["amount_cents"],
                    "stripe_charge_id": charge.id,
                    "stripe_amount": charge.amount,
                    "match_method": "payment_intent",
                    "status": "matched",
                    "paid_at": order["paid_at"],
                })
                unmatched_charges.discard(charge.id)
                matched = True

        # Try match by customer + amount
        if not matched and order["stripe_customer_id"] and order["amount_cents"]:
            key = (order["stripe_customer_id"], order["amount_cents"])
            if key in stripe_by_customer_amount:
                # Pick the first charge matching this customer+amount
                # (could be ambiguous if multiple purchases same amount)
                charge = stripe_by_customer_amount[key][0]
                matched_orders.append({
                    "order_id": order["id"],
                    "package_id": order["package_id"],
                    "order_type": order["order_type"],
                    "amount_cents": order["amount_cents"],
                    "stripe_charge_id": charge.id,
                    "stripe_amount": charge.amount,
                    "match_method": "customer_amount",
                    "status": "matched",
                    "paid_at": order["paid_at"],
                })
                unmatched_charges.discard(charge.id)
                matched = True

        if not matched:
            # Check if we have a payment intent but it's not in Stripe
            if order["stripe_payment_intent"]:
                missing_webhooks.append({
                    "order_id": order["id"],
                    "package_id": order["package_id"],
                    "order_type": order["order_type"],
                    "amount_cents": order["amount_cents"],
                    "customer_email": order["customer_email"],
                    "stripe_payment_intent": order["stripe_payment_intent"],
                    "issue": "Payment intent recorded but not found in Stripe charges",
                })
            else:
                unmatched_orders.append({
                    "order_id": order["id"],
                    "package_id": order["package_id"],
                    "order_type": order["order_type"],
                    "amount_cents": order["amount_cents"],
                    "customer_email": order["customer_email"],
                    "issue": "No Stripe payment intent recorded",
                })

    # Unmatched Stripe charges (charges in Stripe but not in DB)
    unmatched_stripe_charges = []
    for charge_id in unmatched_charges:
        charge = stripe_by_intent[charge_id]
        unmatched_stripe_charges.append({
            "stripe_charge_id": charge.id,
            "stripe_amount": charge.amount,
            "stripe_customer": charge.customer,
            "stripe_description": charge.description,
            "stripe_payment_intent": charge.payment_intent,
            "issue": "Charge exists in Stripe but no matching order in database",
        })

    # Summary
    print("=" * 80)
    print("RECONCILIATION SUMMARY")
    print("=" * 80)
    total_matched = len(matched_orders)
    total_unmatched_orders = len(unmatched_orders)
    total_unmatched_charges = len(unmatched_stripe_charges)
    total_missing_webhooks = len(missing_webhooks)

    print(f"Matched Orders:              {total_matched}")
    print(f"Unmatched Database Orders:   {total_unmatched_orders}")
    print(f"Unmatched Stripe Charges:    {total_unmatched_charges}")
    print(f"Missing Webhook Deliveries:  {total_missing_webhooks}")
    print()

    # Calculate totals
    matched_total = sum(o["amount_cents"] for o in matched_orders)
    unmatched_stripe_total = sum(c["stripe_amount"] for c in unmatched_stripe_charges)
    missing_webhook_total = sum(o["amount_cents"] for o in missing_webhooks)
    unmatched_order_total = sum(o["amount_cents"] for o in unmatched_orders)

    print(f"Matched Revenue:             ${matched_total / 100:.2f}")
    print(f"Unmatched Stripe Revenue:    ${unmatched_stripe_total / 100:.2f}")
    print(f"Missing Webhook Revenue:     ${missing_webhook_total / 100:.2f}")
    print(f"Unmatched Order Revenue:     ${unmatched_order_total / 100:.2f}")
    print()

    # Detailed report
    print("=" * 80)
    print("DETAILED RESULTS")
    print("=" * 80)
    print()

    if total_matched > 0:
        print(f"MATCHED PAYMENTS ({total_matched}):")
        print("-" * 80)
        for match in sorted(matched_orders, key=lambda x: x["paid_at"], reverse=True):
            print(f"Order ID:       {match['order_id']}")
            print(f"  Package:      {match['package_id']}")
            print(f"  Type:         {match['order_type']}")
            print(f"  Amount:       ${match['amount_cents'] / 100:.2f}")
            print(f"  Match Method: {match['match_method']}")
            print(f"  Charge ID:    {match['stripe_charge_id']}")
            print(f"  Paid At:      {match['paid_at']}")
            print()

    if total_missing_webhooks > 0:
        print(f"MISSING WEBHOOK DELIVERIES ({total_missing_webhooks}):")
        print("-" * 80)
        print("These orders are marked paid but payment intent may not have webhook delivery.")
        for issue in missing_webhooks:
            print(f"Order ID:         {issue['order_id']}")
            print(f"  Package:        {issue['package_id']}")
            print(f"  Type:           {issue['order_type']}")
            print(f"  Amount:         ${issue['amount_cents'] / 100:.2f}")
            print(f"  Customer Email: {issue['customer_email']}")
            print(f"  Payment Intent: {issue['stripe_payment_intent']}")
            print(f"  Issue:          {issue['issue']}")
            print()

    if total_unmatched_orders > 0:
        print(f"UNMATCHED DATABASE ORDERS ({total_unmatched_orders}):")
        print("-" * 80)
        for order in unmatched_orders:
            print(f"Order ID:         {order['order_id']}")
            print(f"  Package:        {order['package_id']}")
            print(f"  Type:           {order['order_type']}")
            print(f"  Amount:         ${order['amount_cents'] / 100:.2f}")
            print(f"  Customer Email: {order['customer_email']}")
            print(f"  Issue:          {order['issue']}")
            print()

    if total_unmatched_charges > 0:
        print(f"UNMATCHED STRIPE CHARGES ({total_unmatched_charges}):")
        print("-" * 80)
        print("These charges exist in Stripe but have no matching order record.")
        for charge in unmatched_stripe_charges:
            print(f"Charge ID:        {charge['stripe_charge_id']}")
            print(f"  Amount:         ${charge['stripe_amount'] / 100:.2f}")
            print(f"  Customer ID:    {charge['stripe_customer']}")
            print(f"  Description:    {charge['stripe_description']}")
            print(f"  Payment Intent: {charge['stripe_payment_intent']}")
            print(f"  Issue:          {charge['issue']}")
            print()

    # Escalation check
    print("=" * 80)
    print("ESCALATION CHECK")
    print("=" * 80)
    if total_unmatched_charges > 0 or total_unmatched_orders > 0:
        print("WARNING: Mismatches detected. Review above for details.")
        print()
        if total_unmatched_charges > 0:
            print(f"  - {total_unmatched_charges} charge(s) in Stripe without DB record")
        if total_unmatched_orders > 0:
            print(f"  - {total_unmatched_orders} order(s) in DB without Stripe match")
        if total_missing_webhooks > 0:
            print(f"  - {total_missing_webhooks} order(s) missing webhook confirmation")
    else:
        print("OK: All charges and orders matched successfully.")
    print()

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "matched_orders": total_matched,
            "unmatched_orders": total_unmatched_orders,
            "unmatched_charges": total_unmatched_charges,
            "missing_webhooks": total_missing_webhooks,
            "matched_revenue_cents": matched_total,
            "unmatched_stripe_revenue_cents": unmatched_stripe_total,
            "missing_webhook_revenue_cents": missing_webhook_total,
            "unmatched_order_revenue_cents": unmatched_order_total,
        },
        "matched": matched_orders,
        "unmatched_orders": unmatched_orders,
        "unmatched_charges": unmatched_stripe_charges,
        "missing_webhooks": missing_webhooks,
    }


def generate_markdown_report(result):
    """Generate a markdown report from reconciliation results."""
    report = []
    report.append("# Assay Revenue Reconciliation Report")
    report.append("")
    report.append(f"**Generated**: {result['timestamp']}")
    report.append("")

    summary = result["summary"]
    report.append("## Summary")
    report.append("")
    report.append("| Metric | Count | Amount |")
    report.append("|--------|-------|--------|")
    report.append(f"| Matched Orders | {summary['matched_orders']} | ${summary['matched_revenue_cents'] / 100:.2f} |")
    report.append(f"| Unmatched Database Orders | {summary['unmatched_orders']} | ${summary['unmatched_order_revenue_cents'] / 100:.2f} |")
    report.append(f"| Unmatched Stripe Charges | {summary['unmatched_charges']} | ${summary['unmatched_stripe_revenue_cents'] / 100:.2f} |")
    report.append(f"| Missing Webhook Deliveries | {summary['missing_webhooks']} | ${summary['missing_webhook_revenue_cents'] / 100:.2f} |")
    report.append("")

    if summary["matched_orders"] > 0:
        report.append("## Matched Payments")
        report.append("")
        report.append("| Order ID | Package | Type | Amount | Match Method | Charge ID | Paid At |")
        report.append("|----------|---------|------|--------|--------------|-----------|---------|")
        for match in sorted(result["matched"], key=lambda x: x["paid_at"], reverse=True):
            report.append(
                f"| {match['order_id']} | {match['package_id']} | {match['order_type']} | "
                f"${match['amount_cents'] / 100:.2f} | {match['match_method']} | "
                f"{match['stripe_charge_id']} | {match['paid_at'].strftime('%Y-%m-%d %H:%M:%S UTC') if hasattr(match['paid_at'], 'strftime') else match['paid_at']} |"
            )
        report.append("")

    if summary["missing_webhooks"] > 0:
        report.append("## Missing Webhook Deliveries")
        report.append("")
        report.append("These orders are marked as paid in the database but may not have proper webhook confirmation from Stripe.")
        report.append("")
        for issue in result["missing_webhooks"]:
            report.append(f"### Order {issue['order_id']}")
            report.append("")
            report.append(f"- **Package**: {issue['package_id']}")
            report.append(f"- **Type**: {issue['order_type']}")
            report.append(f"- **Amount**: ${issue['amount_cents'] / 100:.2f}")
            report.append(f"- **Customer Email**: {issue['customer_email']}")
            report.append(f"- **Payment Intent**: {issue['stripe_payment_intent']}")
            report.append(f"- **Issue**: {issue['issue']}")
            report.append("")

    if summary["unmatched_orders"] > 0:
        report.append("## Unmatched Database Orders")
        report.append("")
        report.append("These orders exist in the database with paid status but have no matching Stripe charge.")
        report.append("")
        for order in result["unmatched_orders"]:
            report.append(f"### Order {order['order_id']}")
            report.append("")
            report.append(f"- **Package**: {order['package_id']}")
            report.append(f"- **Type**: {order['order_type']}")
            report.append(f"- **Amount**: ${order['amount_cents'] / 100:.2f}")
            report.append(f"- **Customer Email**: {order['customer_email']}")
            report.append(f"- **Issue**: {order['issue']}")
            report.append("")

    if summary["unmatched_charges"] > 0:
        report.append("## Unmatched Stripe Charges")
        report.append("")
        report.append("These charges exist in Stripe but have no matching order record in the database. This may indicate a webhook delivery failure.")
        report.append("")
        for charge in result["unmatched_charges"]:
            report.append(f"### Charge {charge['stripe_charge_id']}")
            report.append("")
            report.append(f"- **Amount**: ${charge['stripe_amount'] / 100:.2f}")
            report.append(f"- **Customer ID**: {charge['stripe_customer']}")
            report.append(f"- **Description**: {charge['stripe_description']}")
            report.append(f"- **Payment Intent**: {charge['stripe_payment_intent']}")
            report.append(f"- **Issue**: {charge['issue']}")
            report.append("")

    report.append("## Reconciliation Status")
    report.append("")
    if summary["unmatched_charges"] > 0 or summary["unmatched_orders"] > 0:
        report.append("⚠️  **ACTION REQUIRED** - Mismatches detected")
        report.append("")
        if summary["unmatched_charges"] > 0:
            report.append(f"- {summary['unmatched_charges']} charge(s) in Stripe without database record. **Action**: Check webhook logs for failed deliveries.")
        if summary["unmatched_orders"] > 0:
            report.append(f"- {summary['unmatched_orders']} order(s) in database without Stripe match. **Action**: Verify payment intent IDs or investigate failed payments.")
        if summary["missing_webhooks"] > 0:
            report.append(f"- {summary['missing_webhooks']} order(s) missing webhook confirmation. **Action**: Review webhook delivery logs.")
    else:
        report.append("✓ **OK** - All charges and orders matched successfully. No action required.")

    return "\n".join(report)


if __name__ == "__main__":
    # Determine lookback period from command line
    # Usage: python reconcile_revenue.py [hours] or python reconcile_revenue.py all
    hours = None  # Default: all time
    if len(sys.argv) > 1:
        if sys.argv[1].lower() == "all":
            hours = None
        else:
            try:
                hours = int(sys.argv[1])
            except ValueError:
                pass

    result = reconcile(hours=hours)

    # Generate markdown report
    report = generate_markdown_report(result)
    print("\n" + report)

    # Save report to file
    output_dir = Path("/Users/aj/ai-data/projects/business-incubator/active/assay/artifacts/reconcile_revenue")
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "reconciliation_report.md"

    with open(report_path, "w") as f:
        f.write(report)

    print(f"\n✓ Report saved to: {report_path}")
