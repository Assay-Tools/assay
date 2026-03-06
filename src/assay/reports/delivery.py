"""Report generation and delivery after Stripe payment confirmation."""

import logging
from pathlib import Path

from sqlalchemy.orm import Session

from assay.models import Order, Package

logger = logging.getLogger(__name__)


def _find_project_root() -> Path:
    """Find project root - works both in dev (source tree) and Docker (/app)."""
    # Docker: WORKDIR is /app, reports/ is copied there
    docker_root = Path("/app")
    if docker_root.exists() and (docker_root / "reports").exists():
        return docker_root
    # Dev: walk up from this file to find reports/
    candidate = Path(__file__).resolve()
    for _ in range(6):
        candidate = candidate.parent
        if (candidate / "reports" / "templates").exists():
            return candidate
    # Fallback: cwd
    return Path.cwd()


PROJECT_ROOT = _find_project_root()
REPORTS_DIR = PROJECT_ROOT / "reports" / "output" / "packages"


def generate_report_for_order(order: Order, db: Session) -> str | None:
    """Generate a report for a paid order.

    Supports both 'report' (Full Evaluation $99) and 'brief' (Package Brief $3).
    Returns the report file path (relative to project root) or None on failure.
    """
    if order.order_type not in ("report", "brief"):
        logger.warning("Order %d is not a report order (type=%s)", order.id, order.order_type)
        return None

    pkg = db.query(Package).filter(Package.id == order.package_id).first()
    if not pkg:
        logger.error("Package %s not found for order %d", order.package_id, order.id)
        return None

    try:
        import sys
        reports_script_dir = str(PROJECT_ROOT / "reports")
        if reports_script_dir not in sys.path:
            sys.path.insert(0, reports_script_dir)

        from generate_package_eval import generate_report

        from assay.config import settings
        base_url = settings.app_url.rstrip("/")

        report_type = order.order_type  # "report" or "brief"
        suffix = "-brief" if report_type == "brief" else ""
        filename = f"{order.package_id}{suffix}-order-{order.id}.md"

        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        output_path = REPORTS_DIR / filename

        generate_report(
            package_id=order.package_id,
            report_type=report_type,
            base_url=base_url,
            output_path=output_path,
            with_narratives=bool(settings.anthropic_api_key),
        )

        # Generate PDF from the markdown
        try:
            from assay.reports.pdf import markdown_to_pdf
            md_content = output_path.read_text()
            pdf_path = markdown_to_pdf(md_content, output_path)
            logger.info("PDF generated for order %d: %s", order.id, pdf_path)
        except Exception:
            logger.exception(
                "PDF generation failed for order %d (markdown still available)",
                order.id,
            )

        rel_path = f"reports/output/packages/{filename}"
        order.report_path = rel_path
        db.commit()

        logger.info("Report generated for order %d: %s", order.id, rel_path)
        return rel_path

    except SystemExit:
        logger.error("Report generator called sys.exit for order %d", order.id)
        return None
    except Exception:
        logger.exception("Failed to generate report for order %d", order.id)
        return None
