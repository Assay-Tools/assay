"""OAuth authentication routes — GitHub sign-in and API key issuance."""

import hashlib
import hmac
import logging
import secrets
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from assay.auth.contributor import (
    create_contributor,
    find_contributor_by_github_id,
    regenerate_api_key,
)
from assay.auth.github import exchange_code, fetch_user_profile, get_authorize_url
from assay.config import settings
from assay.database import get_db

logger = logging.getLogger(__name__)

_templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(_templates_dir))

router = APIRouter(tags=["auth"])

# CSRF state cookie name and signing key derivation
_STATE_COOKIE = "oauth_state"


def _sign_state(state: str) -> str:
    """Sign the OAuth state token using the app's secret key."""
    key = (settings.github_client_secret or "fallback-key").encode()
    return hmac.new(key, state.encode(), hashlib.sha256).hexdigest()


@router.get("/auth/github")
def auth_github_redirect():
    """Redirect user to GitHub OAuth authorization page."""
    if not settings.github_client_id:
        return RedirectResponse("/contribute?error=oauth_not_configured", status_code=303)

    state = secrets.token_urlsafe(32)
    url = get_authorize_url(state=state)
    response = RedirectResponse(url, status_code=302)
    # Store signed state in HttpOnly cookie for CSRF validation on callback
    signed = _sign_state(state)
    response.set_cookie(
        _STATE_COOKIE,
        f"{state}:{signed}",
        max_age=600,  # 10 minutes
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return response


@router.get("/auth/callback")
def auth_callback(
    request: Request,
    code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
    db: Session = Depends(get_db),
):
    """Handle GitHub OAuth callback — exchange code, create/find contributor, issue key."""
    if error or not code:
        logger.warning("OAuth callback error: %s", error or "no code")
        return RedirectResponse("/contribute?error=oauth_denied", status_code=303)

    # Validate CSRF state
    cookie_val = request.cookies.get(_STATE_COOKIE, "")
    if ":" not in cookie_val or not state:
        logger.warning("OAuth callback: missing state cookie or state param")
        return RedirectResponse("/contribute?error=oauth_denied", status_code=303)
    cookie_state, cookie_sig = cookie_val.rsplit(":", 1)
    expected_sig = _sign_state(cookie_state)
    if not hmac.compare_digest(cookie_sig, expected_sig) or not hmac.compare_digest(
        cookie_state, state
    ):
        logger.warning("OAuth callback: state mismatch (CSRF)")
        return RedirectResponse("/contribute?error=oauth_denied", status_code=303)

    if not settings.github_client_id or not settings.github_client_secret:
        return RedirectResponse("/contribute?error=oauth_not_configured", status_code=303)

    # Exchange code for access token
    access_token = exchange_code(code)
    if not access_token:
        return RedirectResponse("/contribute?error=oauth_failed", status_code=303)

    # Fetch GitHub profile
    profile = fetch_user_profile(access_token)
    if not profile:
        return RedirectResponse("/contribute?error=oauth_failed", status_code=303)

    # We do NOT store the access token — just use it once for profile fetch
    github_id = profile["id"]
    github_username = profile["login"]

    # Check if contributor already exists
    existing = find_contributor_by_github_id(db, github_id)
    if existing:
        # Existing contributor — regenerate their API key
        raw_key = regenerate_api_key(db, existing)
        resp = templates.TemplateResponse(
            "pages/api_key.html",
            {
                "request": request,
                "api_key": raw_key,
                "contributor": existing,
                "is_new": False,
            },
        )
        resp.delete_cookie(_STATE_COOKIE)
        resp.headers["Cache-Control"] = "no-store"
        return resp

    # New contributor
    contributor, raw_key = create_contributor(
        db,
        github_id=github_id,
        github_username=github_username,
        github_avatar_url=profile.get("avatar_url"),
        github_created_at=profile.get("created_at"),
        email=profile.get("email"),
    )
    logger.info("New contributor registered: %s (GitHub #%d)", github_username, github_id)

    resp = templates.TemplateResponse(
        "pages/api_key.html",
        {
            "request": request,
            "api_key": raw_key,
            "contributor": contributor,
            "is_new": True,
        },
    )
    resp.delete_cookie(_STATE_COOKIE)
    resp.headers["Cache-Control"] = "no-store"
    return resp
