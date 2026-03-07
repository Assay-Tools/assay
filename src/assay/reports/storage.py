"""Report storage on Google Cloud Storage.

Handles upload/download of generated reports (markdown + PDF) to a GCS bucket.
Reports are stored with a predictable key structure so they can be cached and
served across container redeploys.

Key structure:
  reports/{package_id}/{report_type}.md
  reports/{package_id}/{report_type}.pdf
"""

import json
import logging
import tempfile
from pathlib import Path

from google.cloud import storage
from google.oauth2 import service_account

from assay.config import settings

logger = logging.getLogger(__name__)

_client = None


def _get_client() -> storage.Client | None:
    """Lazy-init GCS client from service account key."""
    global _client
    if _client is not None:
        return _client

    if not settings.gcs_sa_key or not settings.gcs_bucket:
        logger.warning("GCS not configured (missing GCS_BUCKET or GCS_SA_KEY)")
        return None

    try:
        key_info = json.loads(settings.gcs_sa_key)
        credentials = service_account.Credentials.from_service_account_info(key_info)
        _client = storage.Client(credentials=credentials, project=key_info.get("project_id"))
        return _client
    except Exception:
        logger.exception("Failed to initialize GCS client")
        return None


def _bucket():
    client = _get_client()
    if not client:
        return None
    return client.bucket(settings.gcs_bucket)


def upload_report(package_id: str, report_type: str, md_path: Path, pdf_path: Path | None = None) -> bool:
    """Upload markdown and PDF report files to GCS.

    Args:
        package_id: Package identifier.
        report_type: "brief" or "report".
        md_path: Local path to the markdown file.
        pdf_path: Local path to the PDF file (optional but expected).

    Returns:
        True if upload succeeded, False otherwise.
    """
    bucket = _bucket()
    if not bucket:
        return False

    prefix = f"reports/{package_id}/{report_type}"

    try:
        md_blob = bucket.blob(f"{prefix}.md")
        md_blob.upload_from_filename(str(md_path), content_type="text/markdown")
        logger.info("Uploaded %s.md to GCS", prefix)

        if pdf_path and pdf_path.exists():
            pdf_blob = bucket.blob(f"{prefix}.pdf")
            pdf_blob.upload_from_filename(str(pdf_path), content_type="application/pdf")
            logger.info("Uploaded %s.pdf to GCS", prefix)

        return True
    except Exception:
        logger.exception("Failed to upload report %s to GCS", prefix)
        return False


def download_report(package_id: str, report_type: str, fmt: str = "pdf") -> bytes | None:
    """Download a report file from GCS.

    Args:
        package_id: Package identifier.
        report_type: "brief" or "report".
        fmt: "pdf" or "md".

    Returns:
        File contents as bytes, or None if not found.
    """
    bucket = _bucket()
    if not bucket:
        return None

    blob_name = f"reports/{package_id}/{report_type}.{fmt}"
    blob = bucket.blob(blob_name)

    try:
        if not blob.exists():
            return None
        return blob.download_as_bytes()
    except Exception:
        logger.exception("Failed to download %s from GCS", blob_name)
        return None


def report_exists(package_id: str, report_type: str) -> bool:
    """Check if both markdown and PDF exist in GCS for this report."""
    bucket = _bucket()
    if not bucket:
        return False

    prefix = f"reports/{package_id}/{report_type}"
    try:
        md_exists = bucket.blob(f"{prefix}.md").exists()
        pdf_exists = bucket.blob(f"{prefix}.pdf").exists()
        return md_exists and pdf_exists
    except Exception:
        return False
