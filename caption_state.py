"""Bounded revision checking for the mandatory single-session caption source."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CaptionRevisionState:
    # This is revision state, NOT a recovery-history store. The required source
    # sends increasing segment numbers and completes each segment before starting
    # the next. Consequently, we only need the latest accepted caption: every
    # smaller segment number is already behind our accepted stream position.
    # Memory does not grow with the number of completed segments.
    # TODO: MEMBER 2 - Add a separate bounded store for finalized recovery
    # history. latest_caption is replaced on each accepted update, so it cannot
    # serve as the recent transcript needed for HISTORY responses.
    latest_caption: dict[str, Any] | None = None

    def accept(self, msg: dict[str, Any], source_session: str) -> bool:
        """Decide whether the server should accept and broadcast this update.

        Return True and save a copy of msg when the field/session checks pass
        AND one of these conditions holds:
          1. No caption has been accepted yet (the first update).
          2. The segment number is higher than the latest accepted segment.
          3. It is the same segment, the stored caption is not final, and the
             incoming revision is strictly higher than the stored revision.

        Return False without changing latest_caption when:
          - type is not CAPTION_UPDATE, source_session is not a nonempty string,
            or the message session differs from the source's hello session;
          - segment/revision is not a positive integer, or final is not a bool;
          - the session differs from the already accepted stream's session;
          - the segment number is lower than the latest accepted segment;
          - it is the same segment and the stored caption is already final;
          - it is the same segment and the revision is equal (duplicate) or
            lower (stale).

        handle_source() broadcasts only when this function returns True.
        There are no await points between checking and saving the state.
        The saved message includes source_ts and extra fields for a future,
        separate history component; this function does not keep a transcript.
        """
        segment = msg.get("segment")
        revision = msg.get("revision")
        final = msg.get("final")

        # Validate the fields used in comparisons. In Python, bool is a subclass
        # of int, so exact type checks stop True from becoming segment/revision 1.
        if (msg.get("type") != "CAPTION_UPDATE"
                or not isinstance(source_session, str) or not source_session
                or msg.get("session") != source_session
                or type(segment) is not int or segment <= 0
                or type(revision) is not int or revision <= 0
                or type(final) is not bool):
            # Return False: a field/session check failed; keep existing state.
            return False

        previous = self.latest_caption
        if previous is not None:
            # The mandatory server has one session. Do not mix another session's
            # updates into its revision state or broadcast stream.
            if source_session != previous["session"]:
                # Return False: this update belongs to a different stream.
                return False

            if segment < previous["segment"]:
                # Return False: this segment is behind the accepted stream
                # position, even if it claims a very large revision number.
                return False

            if segment == previous["segment"]:
                # Finals are immutable, even if a later message claims a higher
                # revision. For unfinished captions, only higher revisions win.
                if previous["final"] or revision <= previous["revision"]:
                    # Return False: the segment is complete, or this revision
                    # does not improve the currently stored provisional caption.
                    return False

        # A newer segment has its own revision counter; do not compare its
        # revision with the preceding segment's revision. No fixed revision
        # count is assumed. Copy the message so caller edits cannot alter state.
        self.latest_caption = msg.copy()
        # Return True: state is now saved and the caller may broadcast msg.
        return True
