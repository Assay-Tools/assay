"""GitHub OAuth client — exchange code for token, fetch user profile."""

from __future__ import annotations

import logging

import httpx

from assay.config import settings

logger = logging.getLogger(__name__)

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"


def get_authorize_url(state: str | None = None) -> str:
    """Build the GitHub OAuth authorization URL."""
    params = {
        "client_id": settings.github_client_id,
        "scope": "read:user",
    }
    if state:
        params["state"] = state
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{GITHUB_AUTHORIZE_URL}?{qs}"


def exchange_code(code: str) -> str | None:
    """Exchange an authorization code for an access token.

    Returns the access token string, or None on failure.
    """
    resp = httpx.post(
        GITHUB_TOKEN_URL,
        data={
            "client_id": settings.github_client_id,
            "client_secret": settings.github_client_secret,
            "code": code,
        },
        headers={"Accept": "application/json"},
        timeout=15,
    )
    if resp.status_code != 200:
        logger.error("GitHub token exchange failed: %d %s", resp.status_code, resp.text)
        return None

    data = resp.json()
    token = data.get("access_token")
    if not token:
        logger.error("GitHub token exchange: no access_token in response: %s", data)
        return None

    return token


def fetch_user_profile(access_token: str) -> dict | None:
    """Fetch the authenticated user's GitHub profile.

    Returns a dict with: id, login, avatar_url, created_at, email.
    Returns None on failure.
    """
    resp = httpx.get(
        GITHUB_USER_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github.v3+json",
        },
        timeout=15,
    )
    if resp.status_code != 200:
        logger.error("GitHub user fetch failed: %d %s", resp.status_code, resp.text)
        return None

    data = resp.json()
    return {
        "id": data["id"],
        "login": data["login"],
        "avatar_url": data.get("avatar_url"),
        "created_at": data.get("created_at"),
        "email": data.get("email"),
    }
