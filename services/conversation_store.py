"""
services/conversation_store.py — Per-user conversation memory.

Stores the last MAX_TURNS (user + assistant) message pairs per Telegram user ID.
Used by ai_service.py to inject sliding-window context into every API call.

Architecture:
  • Pure in-memory dict — zero dependencies, works in single-instance bots.
  • asyncio-safe: the CPython GIL and single-event-loop guarantee no races.
  • Swap _store for Redis with zero changes to callers when scaling out.
  • deque(maxlen=N) auto-evicts the oldest turn when the window is full.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Deque

MAX_TURNS: int = 5   # keep last 5 (user + assistant) pairs = 10 messages


@dataclass
class Turn:
    """One question-answer exchange."""
    user:        str
    assistant:   str
    timestamp:   datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Conversation:
    """Rolling conversation window for one user."""
    uid:   int
    turns: Deque[Turn] = field(default_factory=lambda: deque(maxlen=MAX_TURNS))

    # ── Mutation ──────────────────────────────────────────────────────────────

    def add(self, user_text: str, assistant_text: str) -> None:
        """Append a new turn; oldest is auto-evicted when at capacity."""
        self.turns.append(Turn(user=user_text, assistant=assistant_text))

    def clear(self) -> None:
        self.turns.clear()

    # ── Read ──────────────────────────────────────────────────────────────────

    def to_messages(self) -> list[dict]:
        """
        Flatten stored turns into OpenAI chat-completion message format.

        Returns a list like:
          [
            {"role": "user",      "content": "What's BTC doing?"},
            {"role": "assistant", "content": "BTC is consolidating…"},
            ...
          ]
        The caller prepends the system prompt before sending.
        """
        msgs: list[dict] = []
        for turn in self.turns:
            msgs.append({"role": "user",      "content": turn.user})
            msgs.append({"role": "assistant", "content": turn.assistant})
        return msgs

    @property
    def length(self) -> int:
        """Number of stored turns (0–MAX_TURNS)."""
        return len(self.turns)

    @property
    def is_empty(self) -> bool:
        return len(self.turns) == 0

    def summary_line(self) -> str:
        """One-liner for logging / debug."""
        return f"uid={self.uid} turns={self.length}/{MAX_TURNS}"


# ── Module-level store ────────────────────────────────────────────────────────

_store: dict[int, Conversation] = {}


def get_conversation(uid: int) -> Conversation:
    """Return (or lazily create) the Conversation for `uid`."""
    if uid not in _store:
        _store[uid] = Conversation(uid=uid)
    return _store[uid]


def clear_conversation(uid: int) -> None:
    """Wipe history for `uid`. Safe to call even if user has no history."""
    if uid in _store:
        _store[uid].clear()


def conversation_length(uid: int) -> int:
    """Return turn count for `uid`, or 0 if no history exists."""
    return _store[uid].length if uid in _store else 0


def has_conversation(uid: int) -> bool:
    """True if the user has at least one stored turn."""
    return uid in _store and not _store[uid].is_empty
