"""Bounded per-client outbound queue with semantic coalescing."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass


@dataclass
class Outgoing:
    raw: str
    # None marks a message that is never coalesced (HISTORY).
    segment: int | None
    final: bool
    queued_at: float = 0.0


class ClientOutbox:
    """Messages accepted for one client but not yet written to its socket.

    The source handler only calls put(), which never awaits, so a slow reader
    delays nothing but its own outbox. Coalescing only happens while a message
    is still waiting here, i.e. when the client is not keeping up; a client that
    keeps up receives every revision.
    """

    # About 24 s of finals at the public source's rate (one per 0.75 s).
    # Coalescing leaves at most one provisional queued, so this caps memory per
    # client even if a burst outruns the lag check below.
    MAX_PENDING = 32
    # Well under the 60 s HISTORY window: a client dropped for lagging this far
    # can still recover every final it missed when it reconnects.
    MAX_LAG_SECONDS = 15.0

    def __init__(self) -> None:
        self.pending: deque[Outgoing] = deque()
        self.ready = asyncio.Event()
        self.overflowed = False
        self.coalesced = 0

    def put(self, item: Outgoing, now: float | None = None) -> bool:
        """Queue item; return False once the client is too far behind to keep.

        A queued provisional is obsolete as soon as any newer update of the same
        segment arrives, because the server only accepts newer revisions. Finals
        are never removed: they are the durable state the client must receive.
        """
        if self.overflowed:
            return False
        item.queued_at = time.time() if now is None else now

        if item.segment is not None:
            kept = deque(
                q for q in self.pending
                if q.final or q.segment != item.segment
            )
            self.coalesced += len(self.pending) - len(kept)
            self.pending = kept
        self.pending.append(item)

        if (len(self.pending) > self.MAX_PENDING
                or item.queued_at - self.pending[0].queued_at > self.MAX_LAG_SECONDS):
            # Queuing finals indefinitely would let memory and caption age grow
            # without bound. Dropping the client instead is safe because its
            # reconnect HISTORY resumes from the last final it actually holds.
            self.overflowed = True
            self.pending.clear()
        self.ready.set()
        return not self.overflowed

    async def get(self) -> Outgoing | None:
        """Wait for the next message; None means the client overflowed."""
        while not self.pending:
            if self.overflowed:
                return None
            self.ready.clear()
            await self.ready.wait()
        return self.pending.popleft()
