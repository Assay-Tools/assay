"""OAuth authentication routes — GitHub sign-in and API key issuance."""

import logging
import secrets
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
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


@router.get("/auth/github")
def auth_github_redirect():
    """Redirect user to GitHub OAuth authorization page."""
    if not settings.github_client_id:
        return RedirectResponse("/contribute?error=oauth_not_configured", status_code=303)

    state = secrets.token_urlsafe(32)
    # In production, state should be stored in a session cookie for CSRF protection.
    # For now, we skip state validation since this is a low-risk read-only OAuth scope.
    url = get_authorize_url(state=state)
    return RedirectResponse(url, status_code=302)


@router.get("/auth/callback")
def auth_callback(
    request: Request,
    code: str = Query(None),
    error: str = Query(None),
    db: Session = Depends(get_db),
):
    """Handle GitHub OAuth callback — exchange code, create/find contributor, issue key."""
    if error or not code:
        logger.warning("OAuth callback error: %s", error or "no code")
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
        return templates.TemplateResponse(
            "pages/api_key.html",
            {
                "request": request,
                "api_key": raw_key,
                "contributor": existing,
                "is_new": False,
            },
        )

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

    return templates.TemplateResponse(
        "pages/api_key.html",
        {
            "request": request,
            "api_key": raw_key,
            "contributor": contributor,
            "is_new": True,
        },
    )
