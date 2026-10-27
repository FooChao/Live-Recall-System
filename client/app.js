/*
 * LiveRecall browser client: live captions and revision replacement.
 *
 * Implemented behavior:
 *   - opens a WebSocket
 *   - sends CLIENT_HELLO
 *   - keeps one caption entry and one displayed row per segment
 *   - replaces a segment's text only when a newer revision is accepted
 *   - ignores stale/duplicate updates and protects finalized captions
 *   - displays whether an update is provisional/final
 *
 * Graded TODOs:
 *   - maintain >=60 s of finalized local state
 *   - implement 30 s default recall + 15/30/60 s views
 *   - automatic reconnect + correct resume state
 *   - HISTORY merge/deduplication
 *   - usable final UI
 */

const WS_URL = "ws://127.0.0.1:8765";
const statusEl = document.getElementById("status");
const liveEl = document.getElementById("live");
const recallEl = document.getElementById("recall");

// Caption state for the single L1 session used by this client.
// Key: segment number. Value: { caption: latest accepted message, row: its div }.
// Keeping the row reference lets us update it directly instead of searching the
// page. Keeping the complete message preserves source_ts for future recall.
// TODO: MEMBER 2 - Add time-based retention using caption.source_ts. Keep at
// least the previous 60 s of finalized captions and retain active provisional
// captions. When expiring an entry, remove BOTH its row (entry.row.remove()) and
// its Map entry (captions.delete(segment)); also run cleanup while input is idle.
const captions = new Map();
const LOCAL_RETENTION_SECONDS = 70;

let ws;

function numericClientId() {
  const key = "liverecall-client-id";
  let value = sessionStorage.getItem(key);
  if (!value) {
    value = String(Math.floor(100000 + Math.random() * 900000));
    sessionStorage.setItem(key, value);
  }
  return Number(value);
}

function removeExpiredCaptions(nowSeconds = Date.now() / 1000) {
  const cutoff = nowSeconds - LOCAL_RETENTION_SECONDS;

  for (const [segment, entry] of captions) {
    if (entry.caption.final && entry.caption.source_ts < cutoff) {
      entry.row.remove();
      captions.delete(segment);
    }
  }
}

function renderRecall(seconds = 30) {
  const nowSeconds = Date.now() / 1000;
  const cutoff = nowSeconds - seconds;

  removeExpiredCaptions(nowSeconds);

  // Does the regular check if the caption is final and within the requested range
  // Also sorts from oldest to newest
  const recentFinals = Array.from(captions.values())
    .map(entry => entry.caption)
    .filter(caption =>
      caption.final &&
      caption.source_ts >= cutoff
    )
    .sort((a, b) => a.segment - b.segment); // a comes first if a - b < 0

  recallEl.textContent = recentFinals.length > 0
    ? recentFinals.map(caption => caption.text).join("\n")
    : `No finalized captions available from the last ${seconds} seconds.`;
}

function applyCaptionUpdate(msg) {
  const existing = captions.get(msg.segment);

  // A final caption is complete and must never be overwritten. For an active
  // segment, accept only a strictly higher revision; equal revisions are
  // duplicates and lower revisions are stale. Rejected updates change nothing.
  if (existing &&
      (existing.caption.final || msg.revision <= existing.caption.revision)) {
    return;
  }

  let row;
  if (existing) {
    // Reuse the SAME div for every accepted revision of this segment.
    row = existing.row;
  } else {
    // Only the first update for a segment creates a new displayed line.
    // The supplied source sends segments in order, so new rows can be appended.
    row = document.createElement("div");
    row.id = `segment-${msg.segment}`;
    row.className = "naive-line";
    liveEl.appendChild(row);
  }

  const state = msg.final ? "FINAL" : "PROVISIONAL";
  // textContent displays caption text literally, including any HTML-like text.
  row.textContent = `[${state}] segment ${msg.segment} rev ${msg.revision}: ${msg.text}`;
  captions.set(msg.segment, { caption: msg, row });
  removeExpiredCaptions(); // Cleanup when there is an update
  // Updating an existing Map key keeps its original insertion position.
  liveEl.scrollTop = liveEl.scrollHeight;
}

function connect() {
  statusEl.textContent = "connecting";
  ws = new WebSocket(WS_URL);

  ws.addEventListener("open", () => {
    statusEl.textContent = "connected";
    ws.send(JSON.stringify({
      type: "CLIENT_HELLO",
      client_id: numericClientId(),
      session: "L1",
      // TODO MEMBER 3:
      // Resume from the latest accepted FINALIZED segment/revision.
      // Keep this position independently of the expiring captions Map.
      last_segment: 0,       
      last_revision: 0,
      history_seconds: 30
    }));
  });

  ws.addEventListener("message", (event) => {
    const msg = JSON.parse(event.data);
    if (msg.type === "CAPTION_UPDATE") {
      applyCaptionUpdate(msg);
    } else if (msg.type === "HISTORY") {
      console.log(`HISTORY with ${msg.items?.length ?? 0} item(s)`, msg);
      // TODO: merge history without stale/duplicate final captions.
      // TODO MEMBER 3:
      // Merge HISTORY items through the shared caption-acceptance logic.
      // Preserve final captions and reject stale/duplicate revisions.
      // Insert recovered captions in chronological display order.
    }
  });

  ws.addEventListener("close", () => {
    statusEl.textContent = "disconnected";
    // TODO: automatic reconnect after a short delay, using finalized resume state.
  });

  ws.addEventListener("error", () => {
    statusEl.textContent = "connection error";
  });
}

for (const button of document.querySelectorAll("button[data-seconds]")) {
  button.addEventListener("click", () => {
    const seconds = Number(button.dataset.seconds);
    //Render finalized captions from the last `seconds` using
    // the local captions Map. Keep 30 s as the default and support 15/30/60 s.
    // Normal recall uses local state; do not request history on every click.
    renderRecall(seconds)
  });
}

setInterval(removeExpiredCaptions, 1000); // Remove expired captions once per second
connect();
