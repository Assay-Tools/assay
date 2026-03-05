"""Admin routes — bookkeeping, transaction export, and operational endpoints."""

import csv
import io
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from starlette.responses import Response, StreamingResponse

from assay.config import settings
from assay.database import get_db
from assay.models import Order

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin_key(request: Request):
    """Verify admin API key for protected endpoints."""
    api_key = request.headers.get("X-Api-Key", "")
    admin_keys = [
        k.strip() for k in (settings.admin_api_keys or "").split(",") if k.strip()
    ]
    if not admin_keys or api_key not in admin_keys:
        raise HTTPException(status_code=403, detail="Admin access required")


# --- Transaction export ---


@router.get("/transactions")
def list_transactions(
    request: Request,
    format: str = Query("json", pattern="^(json|csv)$"),
    status: str | None = None,
    db: Session = Depends(get_db),
    _auth=Depends(_require_admin_key),
):
    """Export all orders/transactions for bookkeeping.

    Supports JSON and CSV formats. Filterable by status.
    """
    query = db.query(Order).order_by(Order.created_at.desc())

    if status:
        query = query.filter(Order.status == status)

    orders = query.all()

    rows = []
    for o in orders:
        rows.append({
            "id": o.id,
            "package_id": o.package_id,
            "order_type": o.order_type,
            "status": o.status,
            "amount_cents": o.amount_cents,
            "currency": o.currency or "usd",
            "customer_email": o.customer_email or "",
            "stripe_session_id": o.stripe_session_id or "",
            "stripe_payment_intent": o.stripe_payment_intent or "",
            "stripe_subscription_id": o.stripe_subscription_id or "",
            "created_at": o.created_at.isoformat() if o.created_at else "",
            "paid_at": o.paid_at.isoformat() if o.paid_at else "",
        })

    if format == "csv":
        if not rows:
            return Response(content="", media_type="text/csv")

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": (
                    f"attachment; filename=assay-transactions-"
                    f"{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
                ),
            },
        )

    # Summary stats
    total_revenue = sum(r["amount_cents"] for r in rows if r["status"] == "paid")
    paid_count = sum(1 for r in rows if r["status"] == "paid")

    return {
        "summary": {
            "total_orders": len(rows),
            "paid_orders": paid_count,
            "total_revenue_cents": total_revenue,
            "total_revenue_usd": f"${total_revenue / 100:.2f}",
        },
        "transactions": rows,
    }


@router.get("/revenue")
def revenue_summary(
    request: Request,
    db: Session = Depends(get_db),
    _auth=Depends(_require_admin_key),
):
    """Quick revenue summary — total, by type, by month."""

    orders = db.query(Order).filter(Order.status == "paid").all()

    by_type = {}
    by_month = {}
    total = 0

    for o in orders:
        total += o.amount_cents or 0

        t = o.order_type or "unknown"
        by_type[t] = by_type.get(t, 0) + (o.amount_cents or 0)

        if o.paid_at:
            month_key = o.paid_at.strftime("%Y-%m")
            by_month[month_key] = by_month.get(month_key, 0) + (o.amount_cents or 0)

    return {
        "total_revenue_cents": total,
        "total_revenue_usd": f"${total / 100:.2f}",
        "paid_orders": len(orders),
        "by_type": {
            k: {"count": sum(1 for o in orders if o.order_type == k),
                "revenue_cents": v,
                "revenue_usd": f"${v / 100:.2f}"}
            for k, v in by_type.items()
        },
        "by_month": {
            k: f"${v / 100:.2f}" for k, v in sorted(by_month.items())
        },
    }
