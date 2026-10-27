#!/usr/bin/env python3
"""
CS3103 Assignment 4 - LiveRecall server with caption revision checks.

Provides the required CLI, bounded revision-state checking and a basic WebSocket
broadcaster for caption_source.py -> server -> browser/load clients.

It DOES NOT implement the graded networking mechanisms:
  - recent-history recovery or late-join recovery
  - bounded per-client application queues
  - slow-client isolation
  - semantic coalescing / backpressure
  - constrained-bandwidth overload handling

Required evaluator command:
    python solution_server.py --port 8765

Teams should replace or substantially extend the implementation while keeping
this command-line interface and the protocol in the assignment specification.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

import websockets

from caption_state import CaptionRevisionState
from history_store import HistoryStore

# Naive global set of currently connected student clients.
# There is deliberately no per-client queue or recovery state here.
CLIENTS: set[Any] = set()

# One tracker for the server's single session, shared across source connections.
# Keeping it outside handle_source prevents a source reconnect from clearing the
# accepted revision position and allowing old captions to be broadcast again.
REVISION_STATE = CaptionRevisionState()

# Shared recent-final history across source connections.
# Keeping it outside handle_source preserves recovery context when
# the source disconnects and reconnects.
HISTORY = HistoryStore()


async def broadcast_naively(raw_message: str) -> None:
    """Send one message directly to every connected client.

    This is intentionally a naive baseline. The source handler waits for all
    sends to complete. Under pressure, this design may accumulate delay and is
    not the target architecture for the assignment.
    """
    if not CLIENTS:
        return

    snapshot = list(CLIENTS)
    results = await asyncio.gather(
        *(client.send(raw_message) for client in snapshot),
        return_exceptions=True,
    )
    for client, result in zip(snapshot, results):
        if isinstance(result, Exception):
            CLIENTS.discard(client)


async def handle_source(ws, hello: dict[str, Any]) -> None:
    session = hello.get("session")
    print(f"source connected: session={session}", flush=True)

    try:
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            # Valid JSON can also be a list, string or null; only objects can
            # contain caption fields. Ignore these other values without crashing.
            if not isinstance(msg, dict):
                continue

            msg_type = msg.get("type")
            if msg_type == "CAPTION_UPDATE":
                # First accept/save the revision, then broadcast it. Rejected
                # stale, duplicate, finalized-segment or mismatched-session
                # updates never reach clients. Forward the original message so
                # extra source fields remain intact; no valid provisional
                # revisions are intentionally suppressed in this baseline.
                if REVISION_STATE.accept(msg, session):
                    # Save accepted final=true messages to the
                    # bounded server history here, before awaiting broadcast.
                    # Retain enough finalized context for requests up to 60 s
                    # and expire older items even when no clients are connected.
                    if msg["final"]:
                        HISTORY.can_add_final(msg)

                    await broadcast_naively(raw)
            elif msg_type == "SOURCE_DONE":
                # Test-control message. The specification does not require it
                # to be forwarded to clients.
                print("source finished", flush=True)
            else:
                # Forward compatibility: ignore fields/messages this baseline
                # doesn't understand rather than crashing.
                continue
    finally:
        print("source disconnected", flush=True)


async def handle_client(ws, hello: dict[str, Any]) -> None:
    client_id = hello.get("client_id")

    # TODO MEMBER 4:
    # Make initial HISTORY delivery and live subscription one ordered handover.
    # Queue HISTORY first, then register the client without an intervening await.
    # Use one sender per client so live updates cannot overtake HISTORY.
    # Sending HISTORY before registration currently leaves a missed-update race.
    # Server gets history from its own history store and sends the requested HISTORY object to the client
    items = HISTORY.get_history(
        session=hello["session"],
        last_segment=hello.get("last_segment", 0),
        last_revision=hello.get("last_revision", 0),
        history_seconds=hello.get("history_seconds", 30),
    )

    await ws.send(json.dumps({
        "type": "HISTORY",
        "items": items,
    }))

    CLIENTS.add(ws)
    print(f"client connected: id={client_id}; clients={len(CLIENTS)}", flush=True)
    try:
        # Student clients normally don't send further messages after hello.
        # Keep the WebSocket open until the client disconnects.
        async for _ in ws:
            pass
    finally:
        CLIENTS.discard(ws)
        print(f"client disconnected: id={client_id}; clients={len(CLIENTS)}", flush=True)


async def handler(ws) -> None:
    try:
        raw = await asyncio.wait_for(ws.recv(), timeout=5)
        hello = json.loads(raw)
    except (asyncio.TimeoutError, json.JSONDecodeError):
        await ws.close(code=1008, reason="Expected a valid hello message")
        return

    msg_type = hello.get("type")
    if msg_type == "SOURCE_HELLO":
        await handle_source(ws, hello)
    elif msg_type == "CLIENT_HELLO":
        await handle_client(ws, hello)
    else:
        await ws.close(code=1008, reason="Expected SOURCE_HELLO or CLIENT_HELLO")


async def main_async(port: int) -> None:
    async with websockets.serve(
        handler,
        "0.0.0.0",
        port,
        max_size=2**20,
        ping_interval=20,
        ping_timeout=20,
    ):
        print(f"LiveRecall baseline listening on ws://0.0.0.0:{port}", flush=True)
        await asyncio.Future()

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    try:
        asyncio.run(main_async(args.port))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
