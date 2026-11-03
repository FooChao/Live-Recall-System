#!/usr/bin/env python3
"""
CS3103 Assignment 4 - LiveRecall server with caption revision checks.

Provides the required CLI, bounded revision-state checking, bounded recovery
history and per-client delivery for caption_source.py -> server -> clients.

Each client has a bounded outbox drained by its own sender task, so a slow
reader never stalls the source or other clients. Under backpressure the outbox
drops obsolete provisional revisions and keeps every final; a client that falls
too far behind is disconnected and recovers through HISTORY on reconnect.

Required evaluator command:
    python solution_server.py --port 8765

Teams should replace or substantially extend the implementation while keeping
this command-line interface and the protocol in the assignment specification.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import socket
from typing import Any

import websockets

from caption_state import CaptionRevisionState
from client_outbox import ClientOutbox, Outgoing
from history_store import HistoryStore

# Connected student clients, each with the messages still waiting to be sent.
CLIENTS: dict[Any, ClientOutbox] = {}

# Bytes buffered below the outbox can no longer be coalesced, so keep those
# buffers small: a backed-up client's backlog then waits in its outbox, where
# obsolete provisionals are dropped. Even a 16 KiB kernel buffer (doubled by
# Linux) holds over 150 caption messages, far more than in-flight traffic needs.
CLIENT_SNDBUF_BYTES = 16 * 1024
WRITE_LIMIT_BYTES = 4 * 1024

# One tracker for the server's single session, shared across source connections.
# Keeping it outside handle_source prevents a source reconnect from clearing the
# accepted revision position and allowing old captions to be broadcast again.
REVISION_STATE = CaptionRevisionState()

# Shared recent-final history across source connections.
# Keeping it outside handle_source preserves recovery context when
# the source disconnects and reconnects.
HISTORY = HistoryStore()


def broadcast(raw_message: str, msg: dict[str, Any]) -> None:
    """Queue one accepted caption for every client without awaiting any socket.

    Because nothing here awaits, the source handler keeps reading at the
    source's pace however slowly individual clients drain their outboxes.
    """
    for outbox in CLIENTS.values():
        outbox.put(Outgoing(raw_message, msg["segment"], msg["final"]))


async def send_loop(ws, outbox: ClientOutbox, client_id: Any) -> None:
    """Write one client's outbox to its socket in order; the only awaiting sender."""
    try:
        while (item := await outbox.get()) is not None:
            await ws.send(item.raw)
    except websockets.ConnectionClosed:
        return
    print(f"client overflowed: id={client_id}; closing for HISTORY recovery", flush=True)
    await ws.close(code=1013, reason="Too far behind; reconnect to resume")


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
                # extra source fields remain intact. Provisionals are only
                # suppressed later, per client, by that client's outbox.
                if session is not None and REVISION_STATE.accept(msg, session):
                    # Save accepted final=true messages to the
                    # bounded server history here, before broadcasting.
                    # Retain enough finalized context for requests up to 60 s
                    # and expire older items even when no clients are connected.
                    if msg["final"]:
                        HISTORY.can_add_final(msg)

                    broadcast(raw, msg)
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

    # HISTORY is queued and the client registered with no await in between, so
    # every final is either in this HISTORY snapshot or broadcast to the outbox
    # afterwards: none can fall into a gap, and live updates cannot overtake it.
    items = HISTORY.get_history(
        session=hello["session"],
        last_segment=hello.get("last_segment", 0),
        last_revision=hello.get("last_revision", 0),
        history_seconds=hello.get("history_seconds", 30),
    )
    ws.transport.get_extra_info("socket").setsockopt(
        socket.SOL_SOCKET, socket.SO_SNDBUF, CLIENT_SNDBUF_BYTES
    )
    outbox = ClientOutbox()
    outbox.put(Outgoing(json.dumps({"type": "HISTORY", "items": items}), None, True))
    CLIENTS[ws] = outbox
    sender = asyncio.create_task(send_loop(ws, outbox, client_id))

    print(f"client connected: id={client_id}; clients={len(CLIENTS)}", flush=True)
    try:
        # Student clients normally don't send further messages after hello.
        # Keep the WebSocket open until the client disconnects.
        async for _ in ws:
            pass
    except websockets.ConnectionClosed:
        # Abnormal closes, including our own 1013 overflow close, still just
        # mean the client is gone; it recovers through HISTORY on reconnect.
        pass
    finally:
        del CLIENTS[ws]
        sender.cancel()
        print(
            f"client disconnected: id={client_id}; clients={len(CLIENTS)}; "
            f"coalesced={outbox.coalesced}",
            flush=True,
        )


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
        write_limit=WRITE_LIMIT_BYTES,
    ):
        print(f"LiveRecall listening on ws://0.0.0.0:{port}", flush=True)
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
