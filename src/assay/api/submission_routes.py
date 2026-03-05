"""Evaluation submission API — authenticated write endpoint."""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy.orm import Session
from starlette.responses import Response

from assay.config import settings
from assay.database import get_db
from assay.evaluation.loader import load_evaluation
from assay.models import PendingEvaluation

from .rate_limit import limiter
from .schemas import (
    EvaluationSubmission,
    EvaluationSubmissionResponse,
    PendingEvaluationListResponse,
    PendingEvaluationResponse,
)

router = APIRouter(tags=["evaluations"])

# Rate limit: 20 submissions per day per IP
SUBMISSION_RATE_LIMIT = "20/day"


def _valid_api_keys() -> set[str]:
    """Parse configured API keys (read from env at call time for testability)."""
    import os

    raw = os.environ.get("SUBMISSION_API_KEYS", settings.submission_api_keys)
    if not raw:
        return set()
    return {k.strip() for k in raw.split(",") if k.strip()}


def _require_api_key(
    x_api_key: str = Header(..., description="Submission API key"),
) -> str:
    """Validate API key from X-Api-Key header. Returns the key."""
    keys = _valid_api_keys()
    if not keys:
        raise HTTPException(
            status_code=503,
            detail="Submission API is not configured (no API keys set)",
        )
    if x_api_key not in keys:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


# --- Submit evaluation ---


@router.post(
    "/v1/evaluations",
    response_model=EvaluationSubmissionResponse,
)
@limiter.limit(SUBMISSION_RATE_LIMIT)
def submit_evaluation(
    request: Request,
    response: Response,
    submission: EvaluationSubmission,
    api_key: str = Depends(_require_api_key),
    db: Session = Depends(get_db),
):
    """Submit a package evaluation.

    Requires a valid API key in the X-Api-Key header.
    Evaluations are queued for review before going live.
    """
    payload = submission.model_dump(mode="json")

    pending = PendingEvaluation(
        package_id=submission.id,
        submitted_by=api_key[:8] + "...",
        payload=json.dumps(payload),
    )
    db.add(pending)
    db.commit()

    return EvaluationSubmissionResponse(
        status="pending_review",
        package_id=submission.id,
        message=(
            f"Evaluation for '{submission.id}' queued for review "
            f"(pending #{pending.id})"
        ),
    )


# --- Admin: list pending evaluations ---


@router.get(
    "/v1/evaluations/pending",
    response_model=PendingEvaluationListResponse,
)
@limiter.limit("100/day")
def list_pending_evaluations(
    request: Request,
    response: Response,
    status: str = Query("pending", description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    api_key: str = Depends(_require_api_key),
    db: Session = Depends(get_db),
):
    """List pending evaluation submissions (admin)."""
    q = db.query(PendingEvaluation).filter(
        PendingEvaluation.status == status,
    )
    total = q.count()
    items = (
        q.order_by(PendingEvaluation.submitted_at.desc())
        .offset(offset).limit(limit).all()
    )

    return PendingEvaluationListResponse(
        evaluations=[
            PendingEvaluationResponse(
                id=e.id,
                package_id=e.package_id,
                submitted_at=e.submitted_at.isoformat(),
                submitted_by=e.submitted_by,
                status=e.status,
            )
            for e in items
        ],
        total=total,
    )


# --- Admin: approve/reject ---


@router.post("/v1/evaluations/{evaluation_id}/approve")
@limiter.limit("100/day")
def approve_evaluation(
    request: Request,
    response: Response,
    evaluation_id: int,
    api_key: str = Depends(_require_api_key),
    db: Session = Depends(get_db),
):
    """Approve a pending evaluation and load it into the database."""
    pending = db.query(PendingEvaluation).filter(
        PendingEvaluation.id == evaluation_id,
    ).first()
    if not pending:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    if pending.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Evaluation already {pending.status}",
        )

    # Load into the main database
    data = json.loads(pending.payload)
    try:
        pkg_id = load_evaluation(data, db)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Failed to load evaluation: {e}",
        )

    pending.status = "approved"
    pending.reviewed_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "status": "approved",
        "package_id": pkg_id,
        "message": f"Evaluation for '{pkg_id}' approved and loaded",
    }


@router.post("/v1/evaluations/{evaluation_id}/reject")
@limiter.limit("100/day")
def reject_evaluation(
    request: Request,
    response: Response,
    evaluation_id: int,
    reason: str = Query(None, description="Rejection reason"),
    api_key: str = Depends(_require_api_key),
    db: Session = Depends(get_db),
):
    """Reject a pending evaluation."""
    pending = db.query(PendingEvaluation).filter(
        PendingEvaluation.id == evaluation_id,
    ).first()
    if not pending:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    if pending.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Evaluation already {pending.status}",
        )

    pending.status = "rejected"
    pending.reviewed_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "status": "rejected",
        "package_id": pending.package_id,
        "message": f"Evaluation for '{pending.package_id}' rejected",
    }
