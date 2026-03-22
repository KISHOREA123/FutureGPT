"""
services/digest_store.py — Per-user daily digest subscription store.

Stores:
  • Whether a user has opted in to daily digest
  • Their preferred delivery time (hour in UTC, 0-23)
  • Whether they've completed onboarding
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone

MAX_DIGEST_HOUR = 23


@dataclass
class UserProfile:
    uid:                int
    digest_enabled:     bool     = False
    digest_hour:        int      = 8          # 8 AM UTC default
    onboarding_done:    bool     = False
    joined_at:          datetime = field(default_factory=lambda: datetime.now(timezone.utc))


_profiles: dict[int, UserProfile] = {}


def get_profile(uid: int) -> UserProfile:
    if uid not in _profiles:
        _profiles[uid] = UserProfile(uid=uid)
    return _profiles[uid]


def set_digest(uid: int, enabled: bool, hour: int = 8) -> UserProfile:
    p = get_profile(uid)
    p.digest_enabled = enabled
    p.digest_hour    = max(0, min(MAX_DIGEST_HOUR, hour))
    return p


def mark_onboarding_done(uid: int) -> None:
    get_profile(uid).onboarding_done = True


def is_onboarding_done(uid: int) -> bool:
    return get_profile(uid).onboarding_done


def get_digest_subscribers() -> list[UserProfile]:
    """Return all users with digest enabled."""
    return [p for p in _profiles.values() if p.digest_enabled]
