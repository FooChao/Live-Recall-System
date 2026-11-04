/*
 * LiveRecall browser client: live captions, local recall, and recovery.
 *
 * Implemented behavior:
 *   - reconnects automatically and resumes from the latest finalized caption
 *   - merges recent HISTORY and live updates in segment order
 *   - keeps one caption entry and one displayed row per segment
 *   - replaces a segment's text only when a newer revision is accepted
 *   - ignores stale/duplicate updates and protects finalized captions
 *   - displays whether an update is provisional/final
 *   - keeps 70 s of finalized local state for 15/30/60 s recall
 */

const WS_URL = "ws://127.0.0.1:8765";
const SESSION = "L1";
const RECONNECT_DELAY_MS = 1000;
const statusEl = document.getElementById("status");
const liveEl = document.getElementById("live");
const recallEl = document.getElementById("recall");

// Caption state for the single L1 session used by this client.
// Key: segment number. Value: { caption: latest accepted message, row: its div }.
// Keeping the row reference lets us update it directly instead of searching the
// page. Keeping the complete message preserves source_ts for recall.
const captions = new Map();
const LOCAL_RETENTION_SECONDS = 70;

let ws;
let reconnectTimer = null;
// Keep the resume position after local caption expiry; provisionals never move it.
let lastFinalSegment = 0;
let lastFinalRevision = 0;

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

  // The transcript can repeat a sentence, so the segment number shows that a
  // repeated line is a separate caption rather than a duplicated final.
  recallEl.textContent = recentFinals.length > 0
    ? recentFinals.map(caption => `#${caption.segment} ${caption.text}`).join("\n")
    : `No finalized captions available from the last ${seconds} seconds.`;
}

function applyCaptionUpdate(msg) {
  if (!msg || msg.type !== "CAPTION_UPDATE" || msg.session !== SESSION ||
      !Number.isSafeInteger(msg.segment) || msg.segment <= 0 ||
      !Number.isSafeInteger(msg.revision) || msg.revision <= 0 ||
      typeof msg.final !== "boolean" || !Number.isFinite(msg.source_ts) ||
      typeof msg.text !== "string") {
    return;
  }

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
    // Recovered captions can arrive after newer live rows already exist.
    row = document.createElement("div");
    row.id = `segment-${msg.segment}`;
    let nextEntry;
    for (const entry of captions.values()) {
      if (entry.caption.segment > msg.segment &&
          (!nextEntry || entry.caption.segment < nextEntry.caption.segment)) {
        nextEntry = entry;
      }
    }
    liveEl.insertBefore(row, nextEntry ? nextEntry.row : null);
  }

  const state = msg.final ? "FINAL" : "PROVISIONAL";
  // textContent displays caption text literally, including any HTML-like text.
  row.textContent = `[${state}] segment ${msg.segment} rev ${msg.revision}: ${msg.text}`;
  row.className = msg.final ? "naive-line" : "naive-line provisional";
  captions.set(msg.segment, { caption: msg, row });
  if (msg.final && (msg.segment > lastFinalSegment ||
      (msg.segment === lastFinalSegment && msg.revision > lastFinalRevision))) {
    lastFinalSegment = msg.segment;
    lastFinalRevision = msg.revision;
  }
  removeExpiredCaptions(); // Cleanup when there is an update
  // Updating an existing Map key keeps its original insertion position.
  liveEl.scrollTop = liveEl.scrollHeight;
}

function connect() {
  statusEl.textContent = "connecting";
  const socket = new WebSocket(WS_URL);
  ws = socket;

  socket.addEventListener("open", () => {
    if (ws !== socket) return;
    statusEl.textContent = "connected";
    socket.send(JSON.stringify({
      type: "CLIENT_HELLO",
      client_id: numericClientId(),
      session: SESSION,
      last_segment: lastFinalSegment,
      last_revision: lastFinalRevision,
      history_seconds: 60
    }));
  });

  socket.addEventListener("message", (event) => {
    if (ws !== socket) return;
    let msg;
    try {
      msg = JSON.parse(event.data);
    } catch {
      return;
    }
    if (!msg || typeof msg !== "object") return;
    if (msg.type === "CAPTION_UPDATE") {
      applyCaptionUpdate(msg);
    } else if (msg.type === "HISTORY" && Array.isArray(msg.items)) {
      for (const item of msg.items) {
        if (item && item.final === true) applyCaptionUpdate(item);
      }
    }
  });

  socket.addEventListener("close", () => {
    if (ws !== socket || reconnectTimer !== null) return;
    statusEl.textContent = "disconnected; retrying in 1 s";
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      connect();
    }, RECONNECT_DELAY_MS);
  });

  socket.addEventListener("error", () => {
    if (ws !== socket) return;
    statusEl.textContent = "connection error";
    // WebSocket errors are followed by close, which schedules the retry.
  });
}

for (const button of document.querySelectorAll("button[data-seconds]")) {
  button.addEventListener("click", () => {
    const seconds = Number(button.dataset.seconds);
    //Render finalized captions from the last `seconds` using
    // the local captions Map. Keep 30 s as the default and support 15/30/60 s.
    // Normal recall uses local state; do not request history on every click.
    renderRecall(seconds);
  });
}

setInterval(removeExpiredCaptions, 1000); // Remove expired captions once per second
connect();
