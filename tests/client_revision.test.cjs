// Run with: node --test tests/client_revision.test.cjs
// Exercise the real browser message handler with an in-memory DOM/WebSocket.
// No server, network connection, or additional packages are needed.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "../client/app.js"), "utf8");

function createClient() {
  let nowSeconds = 1000;
  const rows = [];
  const live = {
    insertBefore(row, next) {
      if (next !== null) assert.ok(rows.includes(next));
      rows.splice(next === null ? rows.length : rows.indexOf(next), 0, row);
    },
    get scrollHeight() { return rows.length; },
    scrollTop: 0,
  };
  const elements = { live, status: { textContent: "" }, recall: { textContent: "" } };
  const sockets = [];
  const retries = new Map();
  const intervals = [];
  const storage = new Map();
  const buttons = [15, 30, 60].map(seconds => ({
    dataset: { seconds: String(seconds) },
    addEventListener(name, handler) { this[name] = handler; },
  }));
  let nextTimerId = 1;
  class FakeWebSocket {
    constructor() {
      this.listeners = {};
      this.sent = [];
      sockets.push(this);
    }
    addEventListener(name, handler) { this.listeners[name] = handler; }
    send(raw) { this.sent.push(JSON.parse(raw)); }
    emit(name, event) { this.listeners[name](event); }
    close() { this.emit("close"); }
  }
  const context = vm.createContext({
    document: {
      getElementById(id) { return elements[id]; },
      createElement() {
        return {
          textContent: "",
          remove() {
            const index = rows.indexOf(this);
            if (index !== -1) rows.splice(index, 1);
          },
        };
      },
      querySelectorAll() { return buttons; },
    },
    WebSocket: FakeWebSocket,
    Date: class extends Date { static now() { return nowSeconds * 1000; } },
    sessionStorage: {
      getItem(key) { return storage.get(key) ?? null; },
      setItem(key, value) { storage.set(key, value); },
    },
    setInterval(callback) { intervals.push(callback); },
    setTimeout(callback, delay) {
      const id = nextTimerId++;
      retries.set(id, { callback, delay });
      return id;
    },
    console,
  });
  vm.runInContext(source, context);
  sockets[0].emit("open");
  return {
    rows,
    context,
    sockets,
    retries,
    elements,
    fireRetry() {
      const [id, timer] = retries.entries().next().value;
      retries.delete(id);
      timer.callback();
    },
    tick(seconds) {
      nowSeconds += seconds;
      for (const callback of intervals) callback();
    },
    recall(seconds) { buttons.find(button => Number(button.dataset.seconds) === seconds).click(); },
    receive(msg) {
      sockets.at(-1).emit("message", { data: JSON.stringify(msg) });
    },
    send(fields) {
      this.receive({
        type: "CAPTION_UPDATE", session: "L1", segment: 1,
        revision: 1, source_ts: 1000, final: false, text: "TCP", ...fields,
      });
    },
  };
}

test("newer revisions replace one row and preserve complete caption metadata", () => {
  const client = createClient();
  client.send({});
  const row = client.rows[0];
  assert.equal(row.id, "segment-1");
  assert.match(row.textContent, /\[PROVISIONAL\]/);
  client.send({ revision: 7, source_ts: 1001, text: "TCP uses acknowledgements.", final: true });
  assert.equal(client.rows.length, 1);
  assert.equal(client.rows[0], row);
  assert.equal(row.textContent, "[FINAL] segment 1 rev 7: TCP uses acknowledgements.");
  assert.equal(vm.runInContext("captions.get(1).caption.source_ts", client.context), 1001);
  assert.equal(vm.runInContext("captions.get(1).caption.session", client.context), "L1");
});

test("duplicate and stale revisions cannot change accepted state or its row", () => {
  const client = createClient();
  client.send({ revision: 4, text: "Current" });
  const displayed = client.rows[0].textContent;
  client.send({ revision: 4, text: "Duplicate" });
  client.send({ revision: 2, text: "Stale", final: true });
  assert.equal(client.rows.length, 1);
  assert.equal(client.rows[0].textContent, displayed);
  assert.equal(vm.runInContext("captions.get(1).caption.revision", client.context), 4);
  assert.equal(vm.runInContext("captions.get(1).caption.final", client.context), false);
});

test("final captions remain unchanged even if a higher revision arrives", () => {
  const client = createClient();
  client.send({ final: true, text: "Complete" });
  const displayed = client.rows[0].textContent;
  client.send({ revision: 2, text: "Must not replace final" });
  client.send({ revision: 3, final: true, text: "Another final" });
  assert.equal(client.rows.length, 1);
  assert.equal(client.rows[0].textContent, displayed);
  assert.equal(vm.runInContext("captions.get(1).caption.revision", client.context), 1);
});

test("segments have separate rows and revising one does not reorder them", () => {
  const client = createClient();
  client.send({});
  client.send({ segment: 2, text: "Second" });
  const [first, second] = client.rows;
  client.send({ revision: 2, text: "<b>Literal caption</b>" });
  assert.equal(client.rows.length, 2);
  assert.equal(client.rows[0], first);
  assert.equal(client.rows[1], second);
  assert.match(first.textContent, /<b>Literal caption<\/b>/);
  assert.match(second.textContent, /Second/);
  assert.equal(vm.runInContext("Array.from(captions.keys()).join(',')", client.context), "1,2");
});

test("idle retention removes expired finals but preserves provisionals and the resume position", () => {
  const client = createClient();
  client.send({ revision: 3, final: true });
  client.send({ segment: 2 });
  client.tick(70);
  assert.equal(client.rows.length, 2);
  client.tick(1);
  assert.equal(client.rows.length, 1);
  assert.equal(client.rows[0].id, "segment-2");
  assert.equal(vm.runInContext("captions.size", client.context), 1);
  client.sockets[0].close();
  client.fireRetry();
  client.sockets[1].emit("open");
  assert.equal(client.sockets[1].sent[0].last_segment, 1);
  assert.equal(client.sockets[1].sent[0].last_revision, 3);
});

function finalCaption(segment, changes = {}) {
  return {
    type: "CAPTION_UPDATE", session: "L1", segment, revision: 3,
    source_ts: 1000, final: true, text: `Caption ${segment}`, ...changes,
  };
}

test("a new client requests recent context without claiming any finalized state", () => {
  const client = createClient();
  const hello = client.sockets[0].sent[0];
  assert.equal(hello.type, "CLIENT_HELLO");
  assert.equal(hello.session, "L1");
  assert.ok(Number.isInteger(hello.client_id));
  assert.equal(hello.last_segment, 0);
  assert.equal(hello.last_revision, 0);
  assert.equal(hello.history_seconds, 60);
});

test("reconnect resumes from a final, never a newer provisional, and keeps the client ID", () => {
  const client = createClient();
  client.send({ segment: 38, revision: 3, final: true });
  client.send({ segment: 39, revision: 7 });
  client.sockets[0].close();
  assert.equal(client.sockets.length, 1);
  assert.equal(client.elements.status.textContent, "disconnected; retrying in 1 s");
  assert.equal(client.retries.values().next().value.delay, 1000);
  client.fireRetry();
  assert.equal(client.elements.status.textContent, "connecting");
  client.sockets[1].emit("open");
  const hello = client.sockets[1].sent[0];
  assert.equal(hello.client_id, client.sockets[0].sent[0].client_id);
  assert.equal(hello.last_segment, 38);
  assert.equal(hello.last_revision, 3);
  assert.equal(client.elements.status.textContent, "connected");
});

test("failed connections retry once per close, including failures before open", () => {
  const client = createClient();
  client.sockets[0].emit("error");
  client.sockets[0].close();
  client.sockets[0].close();
  assert.equal(client.retries.size, 1);
  client.fireRetry();
  client.sockets[1].emit("error");
  client.sockets[1].close();
  assert.equal(client.retries.size, 1);
  client.fireRetry();
  client.sockets[2].emit("open");
  assert.equal(client.sockets.length, 3);
  assert.equal(client.retries.size, 0);
  assert.equal(client.sockets[2].sent[0].last_segment, 0);

  // Delayed events from an earlier socket must not disturb the new connection.
  client.sockets[0].close();
  client.sockets[0].emit("error");
  client.sockets[0].emit("message", { data: JSON.stringify(finalCaption(99)) });
  assert.equal(client.retries.size, 0);
  assert.equal(client.elements.status.textContent, "connected");
  assert.equal(client.rows.length, 0);
});

test("late-join history is ordered before live captions and is available to local recall", () => {
  const client = createClient();
  client.send({ segment: 4, text: "Live provisional" });
  client.receive({ type: "HISTORY", items: [finalCaption(3), finalCaption(1), finalCaption(2)] });
  assert.deepEqual(client.rows.map(row => row.id), ["segment-1", "segment-2", "segment-3", "segment-4"]);
  client.recall(30);
  assert.equal(client.elements.recall.textContent, "Caption 1\nCaption 2\nCaption 3");
  assert.equal(client.sockets[0].sent.length, 1);
});

test("recovered finals replace missed provisionals and merge without duplicate or stale rows", () => {
  const client = createClient();
  client.send({ segment: 38, revision: 3, final: true, text: "Original final" });
  client.send({ segment: 39, revision: 2 });
  const recoveredRow = client.rows[1];
  client.sockets[0].close();
  client.fireRetry();
  client.sockets[1].emit("open");
  const history = { type: "HISTORY", items: [
    finalCaption(38, { revision: 9, text: "Cannot change a final" }),
    finalCaption(39, { revision: 1, text: "Stale" }),
    finalCaption(39), finalCaption(40),
  ] };
  client.receive(history);
  client.receive(history);
  client.send({ segment: 40, revision: 3, final: true, text: "Duplicate" });
  assert.equal(client.rows.length, 3);
  assert.equal(client.rows[1], recoveredRow);
  assert.match(client.rows[0].textContent, /Original final$/);
  assert.match(client.rows[1].textContent, /\[FINAL\].*Caption 39$/);
  assert.match(client.rows[2].textContent, /Caption 40$/);

  // Older history and provisionals cannot move the next resume position backwards or forwards.
  client.receive({ type: "HISTORY", items: [finalCaption(37)] });
  client.send({ segment: 41, revision: 10 });
  client.sockets[1].close();
  client.fireRetry();
  client.sockets[2].emit("open");
  assert.equal(client.sockets[2].sent[0].last_segment, 40);
  assert.equal(client.sockets[2].sent[0].last_revision, 3);
});

test("empty history allows live updates and a later final to advance resume state", () => {
  const client = createClient();
  client.receive({ type: "HISTORY", items: [] });
  client.send({ segment: 1, revision: 8 });
  client.send({ segment: 1, revision: 10, final: true });
  assert.equal(client.rows.length, 1);
  client.sockets[0].close();
  client.fireRetry();
  client.sockets[1].emit("open");
  assert.equal(client.sockets[1].sent[0].last_segment, 1);
  assert.equal(client.sockets[1].sent[0].last_revision, 10);
});

test("malformed messages and nonfinal or foreign-session history cannot poison recovery", () => {
  const client = createClient();
  client.sockets[0].emit("message", { data: "invalid JSON" });
  for (const message of [null, [], "caption", { type: "HISTORY", items: {} }]) {
    client.receive(message);
  }
  client.receive({ type: "HISTORY", items: [null,
    finalCaption(100, { session: "L2" }), finalCaption(100, { final: false }),
    finalCaption(100, { revision: "3" }), finalCaption(100, { segment: -1 }),
    finalCaption(100, { source_ts: null }), finalCaption(100, { text: null }),
    finalCaption(100, { type: "OTHER" }),
  ] });
  client.send({ segment: 100, final: "true" });
  client.send({ segment: 100, session: "L2", final: true });
  assert.equal(client.rows.length, 0);
  client.receive({ type: "HISTORY", items: [finalCaption(1)] });
  assert.equal(client.rows.length, 1);
  client.sockets[0].close();
  client.fireRetry();
  client.sockets[1].emit("open");
  assert.equal(client.sockets[1].sent[0].last_segment, 1);
});

test("15/30/60 second recall includes recovered finals at the boundary without network requests", () => {
  const client = createClient();
  client.receive({ type: "HISTORY", items: [
    finalCaption(1, { source_ts: 939 }), finalCaption(2, { source_ts: 940 }),
    finalCaption(3, { source_ts: 970 }), finalCaption(4, { source_ts: 985 }),
  ] });
  for (const [seconds, expected] of [
    [15, "Caption 4"], [30, "Caption 3\nCaption 4"], [60, "Caption 2\nCaption 3\nCaption 4"],
  ]) {
    client.recall(seconds);
    assert.equal(client.elements.recall.textContent, expected);
  }
  assert.equal(client.sockets[0].sent.length, 1);
});
