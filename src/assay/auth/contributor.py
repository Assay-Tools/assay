"""Contributor management — API key generation, lookup, trust tier logic."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from assay.models import Contributor


def generate_api_key() -> tuple[str, str]:
    """Generate a new API key.

    Returns (raw_key, key_hash) where raw_key is shown to the user once
    and key_hash (SHA-256) is stored in the database.
    """
    raw_key = secrets.token_hex(32)  # 64-char hex string
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    return raw_key, key_hash


def hash_api_key(raw_key: str) -> str:
    """Hash an API key for comparison."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


def find_contributor_by_api_key(db: Session, raw_key: str) -> Contributor | None:
    """Look up a contributor by their raw API key."""
    key_hash = hash_api_key(raw_key)
    return db.query(Contributor).filter(Contributor.api_key_hash == key_hash).first()


def find_contributor_by_github_id(db: Session, github_id: int) -> Contributor | None:
    """Look up an existing contributor by GitHub user ID."""
    return db.query(Contributor).filter(Contributor.github_id == github_id).first()


def create_contributor(
    db: Session,
    github_id: int,
    github_username: str,
    github_avatar_url: str | None = None,
    github_created_at: str | None = None,
    email: str | None = None,
) -> tuple[Contributor, str]:
    """Create a new contributor and generate their API key.

    Returns (contributor, raw_api_key). The raw key is only available at creation time.
    """
    raw_key, key_hash = generate_api_key()

    # Parse GitHub created_at if provided
    gh_created = None
    if github_created_at:
        try:
            gh_created = datetime.fromisoformat(github_created_at.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            pass

    contributor = Contributor(
        id=str(uuid.uuid4()),
        github_id=github_id,
        github_username=github_username,
        github_avatar_url=github_avatar_url,
        github_created_at=gh_created,
        email=email,
        api_key_hash=key_hash,
    )
    db.add(contributor)
    db.commit()
    db.refresh(contributor)

    return contributor, raw_key


def regenerate_api_key(db: Session, contributor: Contributor) -> str:
    """Regenerate an API key for an existing contributor.

    Returns the new raw key (shown once).
    """
    raw_key, key_hash = generate_api_key()
    contributor.api_key_hash = key_hash
    db.commit()
    return raw_key


def update_trust_tier(contributor: Contributor) -> str | None:
    """Check if contributor qualifies for tier promotion.

    Returns the new tier if promoted, None if unchanged.
    """
    old_tier = contributor.trust_tier

    if old_tier == "trusted":
        # Trusted is manually assigned, check for demotion only
        if contributor.rejected_count > 0:
            rejection_rate = contributor.rejected_count / max(contributor.submissions_count, 1)
            if rejection_rate >= 0.10:
                contributor.trust_tier = "established"
                return "established"
        return None

    if old_tier == "new":
        if (
            contributor.approved_count >= 10
            and contributor.submissions_count > 0
            and (contributor.rejected_count / contributor.submissions_count) < 0.20
        ):
            contributor.trust_tier = "established"
            return "established"

    # established -> trusted requires manual promotion (not automatic)

    return None


# Trust tier rate limits (submissions per day)
TIER_RATE_LIMITS = {
    "new": 5,
    "established": 20,
    "trusted": 50,
}


def get_rate_limit(contributor: Contributor) -> int:
    """Get the daily submission rate limit for a contributor."""
    return TIER_RATE_LIMITS.get(contributor.trust_tier, 5)
