"""Evaluation submission API — authenticated write endpoint."""

import hmac
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy.orm import Session
from starlette.responses import Response

from assay.auth.contributor import (
    find_contributor_by_api_key,
    get_rate_limit,
    update_trust_tier,
)
from assay.config import settings
from assay.database import get_db
from assay.evaluation.loader import load_evaluation
from assay.models import Contributor, PendingEvaluation
from assay.security.prompt_injection import scan_submission

from .rate_limit import limiter
from .schemas import (
    EvaluationSubmission,
    EvaluationSubmissionResponse,
    PendingEvaluationListResponse,
    PendingEvaluationResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["evaluations"])

# Fallback IP-based rate limit (applies when contributor lookup fails)
SUBMISSION_RATE_LIMIT = "20/day"


def _parse_keys(env_var: str, fallback: str) -> set[str]:
    """Parse comma-separated API keys from env (read at call time for testability)."""
    import os

    raw = os.environ.get(env_var, fallback)
    if not raw:
        return set()
    return {k.strip() for k in raw.split(",") if k.strip()}


def _submission_keys() -> set[str]:
    return _parse_keys("SUBMISSION_API_KEYS", settings.submission_api_keys)


def _admin_keys() -> set[str]:
    """Admin keys. No fallback — admin keys must be explicitly configured."""
    return _parse_keys("ADMIN_API_KEYS", settings.admin_api_keys)


def _resolve_submitter(
    x_api_key: str = Header(..., description="Submission API key"),
    db: Session = Depends(get_db),
) -> tuple[str, Contributor | None]:
    """Resolve API key to either a contributor or a legacy env-var key.

    Returns (display_name, contributor_or_none).
    - For DB-backed keys: ("github_username", contributor_object)
    - For legacy env-var keys: ("admin:xxxx...", None)
    - Raises 401 if key is invalid.
    """
    # First, try DB-backed contributor lookup
    contributor = find_contributor_by_api_key(db, x_api_key)
    if contributor:
        return contributor.github_username, contributor

    # Fall back to legacy env-var keys (constant-time comparison)
    keys = _submission_keys()
    if keys and any(hmac.compare_digest(x_api_key, k) for k in keys):
        return f"admin:{x_api_key[:8]}...", None

    raise HTTPException(status_code=401, detail="Invalid API key")


def _require_admin_key(
    x_api_key: str = Header(..., description="Admin API key"),
    db: Session = Depends(get_db),
) -> str:
    """Validate API key for admin operations (approve/reject/list).

    Accepts: env-var admin keys OR contributor keys with is_admin=True.
    """
    # Check env-var admin keys (constant-time comparison)
    keys = _admin_keys()
    if keys and any(hmac.compare_digest(x_api_key, k) for k in keys):
        return x_api_key

    # Check DB-backed contributor with admin flag
    contributor = find_contributor_by_api_key(db, x_api_key)
    if contributor and contributor.is_admin:
        return x_api_key

    raise HTTPException(status_code=403, detail="Admin access required")


# --- Plausibility validation ---


def _validate_plausibility(submission: EvaluationSubmission) -> str | None:
    """Check submission for obvious spam/bot signals.

    Returns an error message if implausible, None if OK.
    """
    scores = []

    if submission.af_score_components:
        afc = submission.af_score_components
        scores.extend([
            afc.integration_quality, afc.api_doc_score, afc.error_handling_score,
            afc.auth_complexity_score, afc.rate_limit_clarity_score,
        ])

    if submission.security_score_components:
        sec = submission.security_score_components
        scores.extend([
            sec.tls_enforcement, sec.auth_strength, sec.scope_granularity,
            sec.dependency_hygiene, sec.secret_handling,
        ])

    if submission.reliability_score_components:
        rel = submission.reliability_score_components
        scores.extend([
            rel.uptime_documented, rel.version_stability,
            rel.breaking_changes_history, rel.error_recovery,
        ])

    if not scores:
        return None  # No score components provided, skip validation

    # All scores identical (bot/spam signal)
    if len(set(scores)) == 1 and len(scores) >= 5:
        return "All sub-component scores are identical — this looks like automated spam"

    # All scores exactly 0 or exactly 100
    if all(s == 0 for s in scores):
        return "All scores are 0 — at least some components should have non-zero values"
    if all(s == 100 for s in scores):
        return "All scores are 100 — a perfect score across all dimensions is implausible"

    return None


def _validate_evidence_consistency(submission: EvaluationSubmission) -> list[str]:
    """Validate that scores fall within bands implied by evidence checkpoints.

    Only applies to rubric_version 2.0+ submissions with evidence.
    Returns a list of error messages (empty if all valid).
    """
    if submission.rubric_version < "2.0" or not submission.evidence:
        return []

    from assay.evaluation.rubric import ALL_RUBRICS, validate_score_against_evidence

    errors = []

    # Build a map of sub-component ID -> score from the submission
    score_map: dict[str, float] = {}
    if submission.af_score_components:
        afc = submission.af_score_components
        score_map.update({
            "integration_quality": afc.integration_quality,
            "api_doc_score": afc.api_doc_score,
            "error_handling_score": afc.error_handling_score,
            "auth_complexity_score": afc.auth_complexity_score,
            "rate_limit_clarity_score": afc.rate_limit_clarity_score,
        })
    if submission.security_score_components:
        sec = submission.security_score_components
        score_map.update({
            "tls_enforcement": sec.tls_enforcement,
            "auth_strength": sec.auth_strength,
            "scope_granularity": sec.scope_granularity,
            "dependency_hygiene": sec.dependency_hygiene,
            "secret_handling": sec.secret_handling,
        })
    if submission.reliability_score_components:
        rel = submission.reliability_score_components
        score_map.update({
            "uptime_documented": rel.uptime_documented,
            "version_stability": rel.version_stability,
            "breaking_changes_history": rel.breaking_changes_history,
            "error_recovery": rel.error_recovery,
        })

    # Check each sub-component that has both a score and evidence
    evidence = submission.evidence
    for sub_id, rubric in ALL_RUBRICS.items():
        score = score_map.get(sub_id)
        sub_evidence = getattr(evidence, sub_id, None)
        if score is not None and sub_evidence is not None:
            error = validate_score_against_evidence(
                rubric, score, sub_evidence.checkpoints,
            )
            if error:
                errors.append(error)

    return errors


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
    submitter: tuple[str, Contributor | None] = Depends(_resolve_submitter),
    db: Session = Depends(get_db),
):
    """Submit a package evaluation.

    Requires a valid API key in the X-Api-Key header.
    Evaluations are queued for review before going live.
    Trusted contributors' submissions are auto-approved.
    """
    display_name, contributor = submitter

    # Per-contributor rate limit check (beyond the IP-based slowapi limit)
    if contributor:
        daily_limit = get_rate_limit(contributor)
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = (
            db.query(PendingEvaluation)
            .filter(
                PendingEvaluation.submitted_by == contributor.github_username,
                PendingEvaluation.submitted_at >= today_start,
            )
            .count()
        )
        if today_count >= daily_limit:
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Daily submission limit reached"
                    f" ({daily_limit}/day for {contributor.trust_tier} tier)"
                ),
            )

    # Plausibility validation
    plausibility_error = _validate_plausibility(submission)
    if plausibility_error:
        raise HTTPException(status_code=422, detail=plausibility_error)

    # Prompt injection scan on free-text fields
    text_fields = {
        "what_it_does": submission.what_it_does,
        "best_when": submission.best_when,
        "avoid_when": submission.avoid_when,
    }
    if submission.agent_readiness:
        text_fields["error_message_notes"] = submission.agent_readiness.error_message_notes
        text_fields["idempotency_notes"] = submission.agent_readiness.idempotency_notes
    if submission.auth:
        text_fields["auth_notes"] = submission.auth.notes
    if submission.pricing:
        text_fields["pricing_notes"] = submission.pricing.notes
    if submission.security_score_components:
        text_fields["security_notes"] = submission.security_score_components.security_notes

    # Also scan list-type fields
    list_fields = {}
    if submission.use_cases:
        list_fields["use_cases"] = " ".join(submission.use_cases)
    if submission.not_for:
        list_fields["not_for"] = " ".join(submission.not_for)
    if submission.alternatives:
        list_fields["alternatives"] = " ".join(submission.alternatives)
    if submission.tags:
        list_fields["tags"] = " ".join(submission.tags)
    if submission.agent_readiness and submission.agent_readiness.known_agent_gotchas:
        list_fields["known_agent_gotchas"] = " ".join(
            submission.agent_readiness.known_agent_gotchas,
        )

    injection_findings = scan_submission({**text_fields, **list_fields})
    if injection_findings:
        field_names = sorted({f["field"] for f in injection_findings})
        logger.warning(
            "Prompt injection detected in submission %s by %s: fields=%s",
            submission.id, display_name, field_names,
        )
        raise HTTPException(
            status_code=422,
            detail=(
                f"Submission rejected: suspicious content detected in "
                f"field(s) {', '.join(field_names)}. "
                f"Text fields must not contain LLM prompt manipulation attempts."
            ),
        )

    # Evidence consistency validation (rubric v2+ only)
    if submission.rubric_version >= "2.0" and not submission.evidence:
        raise HTTPException(
            status_code=422,
            detail=(
                "Rubric version 2.0+ requires evidence checkpoints."
                " Include an 'evidence' object."
            ),
        )
    evidence_errors = _validate_evidence_consistency(submission)
    if evidence_errors:
        raise HTTPException(
            status_code=422,
            detail=f"Score-evidence inconsistency: {'; '.join(evidence_errors)}",
        )

    payload = submission.model_dump(mode="json")

    # Determine if this should be auto-approved
    auto_approve = contributor and contributor.trust_tier == "trusted"

    pending = PendingEvaluation(
        package_id=submission.id,
        submitted_by=display_name,
        payload=json.dumps(payload),
        status="approved" if auto_approve else "pending",
    )
    db.add(pending)

    # Update contributor stats
    if contributor:
        contributor.submissions_count += 1
        contributor.last_submission_at = datetime.now(timezone.utc)

    db.flush()

    # Auto-approve: load directly into the main database
    if auto_approve:
        try:
            load_evaluation(payload, db)
            pending.reviewed_at = datetime.now(timezone.utc)
            if contributor:
                contributor.approved_count += 1
                update_trust_tier(contributor)
        except Exception:
            logger.exception(
                "Auto-approve failed for %s by %s", submission.id, display_name,
            )
            # Revert to pending review on failure
            pending.status = "pending"

    db.commit()

    status = "accepted" if auto_approve and pending.status == "approved" else "pending_review"
    return EvaluationSubmissionResponse(
        status=status,
        package_id=submission.id,
        message=(
            f"Evaluation for '{submission.id}'"
            f" {'accepted and loaded' if status == 'accepted' else 'queued for review'}"
            f" (#{pending.id})"
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
    api_key: str = Depends(_require_admin_key),
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
    api_key: str = Depends(_require_admin_key),
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
    except Exception:
        logger.exception(
            "Failed to load evaluation %d for package %s",
            evaluation_id, pending.package_id,
        )
        raise HTTPException(
            status_code=422,
            detail="Failed to load evaluation. Check server logs for details.",
        )

    pending.status = "approved"
    pending.reviewed_at = datetime.now(timezone.utc)

    # Update contributor stats if submitted by a known contributor
    if pending.submitted_by:
        contributor = (
            db.query(Contributor)
            .filter(Contributor.github_username == pending.submitted_by)
            .first()
        )
        if contributor:
            contributor.approved_count += 1
            update_trust_tier(contributor)

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
    api_key: str = Depends(_require_admin_key),
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

    # Update contributor stats if submitted by a known contributor
    if pending.submitted_by:
        contributor = (
            db.query(Contributor)
            .filter(Contributor.github_username == pending.submitted_by)
            .first()
        )
        if contributor:
            contributor.rejected_count += 1
            update_trust_tier(contributor)

    db.commit()

    return {
        "status": "rejected",
        "package_id": pending.package_id,
        "message": f"Evaluation for '{pending.package_id}' rejected",
    }
