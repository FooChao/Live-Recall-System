"""bounded finalized-caption history"""

from __future__ import annotations

import math
import time
from typing import Any

class HistoryStore:
    """Keep one final per (session, segment) inside a recent time window.
    The 'now' arguments are for tests
    Expiry runs on every add/query, or explicitly through remove_expired().
    """

    def __init__(self, retention_seconds: float = 70.0) -> None:
        # History must be at least 60 seconds (Added some buffer)
        if not math.isfinite(retention_seconds) or retention_seconds < 60:
            raise ValueError("retention_seconds must be finite and at least 60")
        self.retention_seconds = retention_seconds
        # Dictionary where key = (session, segment), and value = caption object
        self.finals: dict[tuple[str, int], dict[str, Any]] = {}

    def remove_expired(self, now: float | None = None) -> int:
        """Remove expired finals; return the number removed (for testing)."""
        current_time = time.time() if now is None else now
        cutoff = current_time - self.retention_seconds
        expired = [
            key for key, caption in self.finals.items()
            if caption["source_ts"] < cutoff
        ]
        for key in expired:
            del self.finals[key]
        return len(expired)

    def can_add_final(self, caption: dict[str, Any], now: float | None = None) -> bool:
        """Store a recent final once; return whether it was newly stored.

        Ignore provisionals, expired finals, and repeats of an already-final
        segment. A final is immutable even if a later input claims a higher
        revision. Preserve source timestamps and extra protocol fields.
        """
        current_time = time.time() if now is None else now
        self.remove_expired(now=current_time)
        # Reject caption if provisional
        if caption.get("final") is not True:
            return False
        # Reject if caption expired
        if caption["source_ts"] < current_time - self.retention_seconds:
            return False
        key = (caption["session"], caption["segment"])
        # Check if the segment already has a final
        if key in self.finals:
            return False
        self.finals[key] = caption.copy()
        return True

    def get_history(self, session: str, last_segment: int = 0, last_revision: int = 0, history_seconds: float = 30, now: float | None = None) -> list[dict[str, Any]]:
        """Return recent finals after the client's finalized resume position.
        A new client uses (0, 0). A zero-second request returns no items.
        """
        if not math.isfinite(history_seconds) or not 0 <= history_seconds <= 60:
            raise ValueError("history_seconds must be between 0 and 60")
        current_time = time.time() if now is None else now
        # Remove expired finals again
        self.remove_expired(now=current_time)
        if history_seconds == 0:
            return []
        cutoff = current_time - history_seconds
        resume_position = (last_segment, last_revision)

        # Include final caption item if it is part of the same session AND 
        # its time must be higher than the cutoff (part of the requested history) AND
        # it is newer than the resume position
        items = [
            caption for caption in self.finals.values()
            if caption["session"] == session
            and caption["source_ts"] >= cutoff
            and (caption["segment"], caption["revision"]) > resume_position
        ]
        # Sort by segment number so that oldest comes first
        items.sort(key=lambda caption: caption["segment"])
        return [caption.copy() for caption in items]
