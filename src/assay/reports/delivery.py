"""Report generation and delivery after Stripe payment confirmation.

Includes a caching layer: reports are generated once per evaluation cycle
and served from cache for subsequent orders. When a package is re-evaluated,
the old report is archived and a fresh one generated on next purchase.

Cache invalidation triggers:
- Package re-evaluated (last_evaluated newer than report)
- Scores changed (af, security, or reliability)
"""

import logging
import shutil
from pathlib import Path

from sqlalchemy.orm import Session

from assay.models import Order, Package, ReportCache

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
ARCHIVE_DIR = PROJECT_ROOT / "reports" / "output" / "archive"


def _get_cached_report(
    package_id: str, report_type: str, pkg: Package, db: Session,
) -> ReportCache | None:
    """Check if a valid cached report exists for this package and type.

    A cached report is valid if:
    1. It's marked as current (not archived)
    2. The package hasn't been re-evaluated since the report was generated
    3. The scores haven't changed
    """
    cached = (
        db.query(ReportCache)
        .filter(
            ReportCache.package_id == package_id,
            ReportCache.report_type == report_type,
            ReportCache.is_current.is_(True),
        )
        .first()
    )
    if not cached:
        return None

    # Check if evaluation data has changed since report was generated
    if pkg.last_evaluated and cached.evaluation_date:
        if pkg.last_evaluated > cached.evaluation_date:
            logger.info(
                "Cache stale for %s/%s: evaluated %s > report %s",
                package_id, report_type, pkg.last_evaluated, cached.evaluation_date,
            )
            return None

    # Check if scores have drifted
    if (
        cached.af_score != pkg.af_score
        or cached.security_score != pkg.security_score
        or cached.reliability_score != pkg.reliability_score
    ):
        logger.info("Cache stale for %s/%s: scores changed", package_id, report_type)
        return None

    # Verify files exist (on disk or in GCS)
    md_file = PROJECT_ROOT / cached.md_path
    if not md_file.exists():
        # Check GCS before declaring missing
        try:
            from assay.reports.storage import report_exists
            if not report_exists(package_id, report_type):
                logger.warning(
                    "Cache entry for %s/%s but files missing locally and in GCS",
                    package_id, report_type,
                )
                return None
        except Exception:
            logger.warning(
                "Cache entry for %s/%s but file missing: %s", package_id, report_type, md_file,
            )
            return None

    return cached


def _archive_old_reports(package_id: str, report_type: str, db: Session) -> None:
    """Archive previous cached reports for this package/type.

    Old versions are preserved in GCS under archive/ prefix with timestamp,
    so they can be retrieved if needed.
    """
    old_entries = (
        db.query(ReportCache)
        .filter(
            ReportCache.package_id == package_id,
            ReportCache.report_type == report_type,
            ReportCache.is_current.is_(True),
        )
        .all()
    )
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    for entry in old_entries:
        entry.is_current = False

        # Archive to GCS with timestamp prefix for retrieval
        timestamp = entry.generated_at.strftime("%Y%m%d") if entry.generated_at else "unknown"
        try:
            from assay.reports.storage import archive_report
            archive_report(package_id, report_type, timestamp)
            logger.info("Archived %s/%s (version %s) to GCS", package_id, report_type, timestamp)
        except Exception:
            logger.exception("GCS archive failed for %s/%s", package_id, report_type)

        # Move local files to archive directory
        for rel_path in (entry.md_path, entry.pdf_path):
            if rel_path:
                src = PROJECT_ROOT / rel_path
                if src.exists():
                    dest = ARCHIVE_DIR / src.name
                    shutil.move(str(src), str(dest))
                    logger.info("Archived local %s -> %s", src.name, dest)
    if old_entries:
        db.flush()


def _copy_cached_to_order(cached: ReportCache, order: Order) -> str:
    """Return the canonical cache path for this order's report.

    No longer copies to order-specific filenames — all orders for the same
    package/type share the cached file.  The returned path matches the GCS
    structure so local lookup and GCS fallback use the same scheme.
    """
    return cached.md_path


def generate_report_for_order(order: Order, db: Session) -> str | None:
    """Generate a report for a paid order, using cache when possible.

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

    report_type = order.order_type

    # Check cache first
    cached = _get_cached_report(order.package_id, report_type, pkg, db)
    if cached:
        logger.info(
            "Serving cached %s report for %s (generated %s)",
            report_type, order.package_id, cached.generated_at,
        )
        rel_path = _copy_cached_to_order(cached, order)
        order.report_path = rel_path
        db.commit()
        return rel_path

    # No valid cache — generate fresh report
    try:
        import sys
        reports_script_dir = str(PROJECT_ROOT / "reports")
        if reports_script_dir not in sys.path:
            sys.path.insert(0, reports_script_dir)

        from generate_package_eval import generate_report

        from assay.config import settings
        base_url = settings.app_url.rstrip("/")

        # Generate to a canonical cache filename (not order-specific)
        suffix = "-brief" if report_type == "brief" else ""
        cache_filename = f"{order.package_id}{suffix}.md"
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        cache_path = REPORTS_DIR / cache_filename

        generate_report(
            package_id=order.package_id,
            report_type=report_type,
            base_url=base_url,
            output_path=cache_path,
            with_narratives=bool(settings.anthropic_api_key),
        )

        # Generate PDF from the markdown — required for delivery
        # Retry up to 3 attempts, then alert the operator
        pdf_rel = None
        last_error = None
        for attempt in range(1, 4):
            try:
                from assay.reports.pdf import markdown_to_pdf
                md_content = cache_path.read_text()
                pdf_result = markdown_to_pdf(md_content, cache_path)
                pdf_rel = f"reports/output/packages/{pdf_result.name}"
                logger.info(
                    "PDF generated for order %d (attempt %d): %s", order.id, attempt, pdf_result,
                )
                last_error = None
                break
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "PDF generation attempt %d/3 failed for order %d: %s",
                    attempt, order.id, exc,
                )

        if last_error:
            logger.error(
                "PDF generation failed after 3 attempts for order %d (continuing with markdown)",
                order.id,
            )

        # Upload to GCS for durable storage
        pdf_path = cache_path.with_suffix(".pdf") if pdf_rel else None
        try:
            from assay.reports.storage import upload_report
            upload_report(order.package_id, report_type, cache_path, pdf_path)
        except Exception:
            logger.exception("GCS upload failed for order %d (continuing with local)", order.id)

        # Archive any old cached reports for this package/type
        _archive_old_reports(order.package_id, report_type, db)

        # Create cache entry
        cache_entry = ReportCache(
            package_id=order.package_id,
            report_type=report_type,
            evaluation_date=pkg.last_evaluated,
            md_path=f"reports/output/packages/{cache_filename}",
            pdf_path=pdf_rel,
            af_score=pkg.af_score,
            security_score=pkg.security_score,
            reliability_score=pkg.reliability_score,
            is_current=True,
        )
        db.add(cache_entry)

        # Copy to order-specific files
        rel_path = _copy_cached_to_order(cache_entry, order)
        order.report_path = rel_path
        db.commit()

        logger.info("Report generated and cached for order %d: %s", order.id, rel_path)
        return rel_path

    except SystemExit:
        logger.error("Report generator called sys.exit for order %d", order.id)
        return None
    except Exception:
        logger.exception("Failed to generate report for order %d", order.id)
        return None
