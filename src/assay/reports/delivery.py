"""Report generation and delivery after Stripe payment confirmation."""

import logging
from pathlib import Path

from sqlalchemy.orm import Session

from assay.models import Order, Package

logger = logging.getLogger(__name__)

# Reports stored relative to project root
REPORTS_DIR = Path(__file__).parent.parent.parent.parent / "reports" / "output" / "packages"
TEMPLATE_PATH = (
    Path(__file__).parent.parent.parent.parent / "reports" / "templates" / "package-evaluation.md"
)


def generate_report_for_order(order: Order, db: Session) -> str | None:
    """Generate a markdown report for a paid order.

    Returns the report file path (relative to project root) or None on failure.
    """
    if order.order_type != "report":
        logger.warning("Order %d is not a report order (type=%s)", order.id, order.order_type)
        return None

    pkg = db.query(Package).filter(Package.id == order.package_id).first()
    if not pkg:
        logger.error("Package %s not found for order %d", order.package_id, order.id)
        return None

    try:
        # Import the existing report generator
        import sys
        reports_script_dir = str(Path(__file__).parent.parent.parent.parent / "reports")
        if reports_script_dir not in sys.path:
            sys.path.insert(0, reports_script_dir)

        from generate_package_eval import compute_report_data, render_template

        # Generate report data via the API
        from assay.config import settings
        base_url = settings.app_url.rstrip("/")

        data = compute_report_data(base_url, order.package_id)

        # Load and render template
        if not TEMPLATE_PATH.exists():
            logger.error("Report template not found: %s", TEMPLATE_PATH)
            return None

        template = TEMPLATE_PATH.read_text()
        report_content = render_template(template, data)

        # Write report file — use order ID for uniqueness
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"{order.package_id}-order-{order.id}.md"
        report_path = REPORTS_DIR / filename
        report_path.write_text(report_content)

        # Store relative path on order
        rel_path = f"reports/output/packages/{filename}"
        order.report_path = rel_path
        db.commit()

        logger.info("Report generated for order %d: %s", order.id, rel_path)
        return rel_path

    except Exception:
        logger.exception("Failed to generate report for order %d", order.id)
        return None
