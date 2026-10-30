# Mandatory Deterministic Application Demo

No ASR or speech-recognition setup is required.

## Suggested setup

Terminal 1:

```bash
python solution_server.py --port 8765
```

Terminal 2 (serve the browser files):

```bash
python -m http.server 8000 --directory client
```

Open `http://127.0.0.1:8000` in at least two browser tabs/windows.

Terminal 3, use long/demo mode so the 60-second recall view is meaningful:

```bash
python caption_source.py --duration 120
```

## Demonstrate

- provisional versus final captions are visually distinguishable;
- newer revisions replace older revisions of the same segment;
- `What did I miss?` defaults to 30 seconds and supports 15/30/60 seconds using local state under normal operation;
- one client temporarily disconnects, reconnects automatically, and recovers recent missed finalized captions without duplicate finals (steps below);
- a newly opened late client receives recent context and then continues with live updates.

## Reconnect and late-join steps

1. Keep both tabs connected until several captions are final. The live area
   should contain one row per segment, updated in place as revisions arrive.
2. In one tab's browser developer tools, set Network to **Offline**, then run
   `ws.close()` in that tab's console to close its existing WebSocket. Keep the
   page open; reloading would discard its local caption state.
3. Leave it offline for about five seconds while the other tab continues to
   receive captions. The disconnected tab retries once per second.
4. Set Network back to **Online**. The tab should reconnect automatically and
   merge missed finals into their segment positions. A provisional row that
   finalized during the disconnect should become final in the same row, and
   existing finals should not appear twice.
5. Click the recall buttons to check that recovered finals are available in
   local recall. Open a third tab while the source is still running to show
   recent finalized context arriving before continued live captions.

For protocol inspection, the WebSocket Messages panel shows `CLIENT_HELLO`
with the last finalized position on reconnect and a `HISTORY` response. New tabs
send `(0, 0)` and request up to 60 seconds of recent finals. Recovery is limited
to available finals inside that window.

The public T4 command in [PUBLIC_TESTS.md](PUBLIC_TESTS.md) exercises the Python
load clients and server. Use this browser demo and the JavaScript regression
tests as well to verify the browser implementation. Member 4 still needs to
make the server's initial HISTORY/live handoff atomic under concurrent updates.
