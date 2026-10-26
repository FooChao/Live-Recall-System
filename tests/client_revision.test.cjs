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
  const rows = [];
  const live = {
    appendChild(row) { rows.push(row); },
    get scrollHeight() { return rows.length; },
    scrollTop: 0,
  };
  const elements = { live, status: { textContent: "" }, recall: { textContent: "" } };
  const sockets = [];
  class FakeWebSocket {
    constructor() {
      this.listeners = {};
      sockets.push(this);
    }
    addEventListener(name, handler) { this.listeners[name] = handler; }
  }
  const context = vm.createContext({
    document: {
      getElementById(id) { return elements[id]; },
      createElement() {
        return {
          textContent: "",
          remove() { rows.splice(rows.indexOf(this), 1); },
        };
      },
      querySelectorAll() { return []; },
    },
    WebSocket: FakeWebSocket,
    console,
  });
  vm.runInContext(source, context);
  return {
    rows,
    context,
    send(fields) {
      sockets[0].listeners.message({ data: JSON.stringify({
        type: "CAPTION_UPDATE", session: "L1", segment: 1,
        revision: 1, source_ts: 1000, final: false, text: "TCP", ...fields,
      }) });
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

test("retention can remove both a row and its stored entry", () => {
  const client = createClient();
  client.send({ final: true });
  client.send({ segment: 2 });
  vm.runInContext("captions.get(1).row.remove(); captions.delete(1);", client.context);
  assert.equal(client.rows.length, 1);
  assert.equal(client.rows[0].id, "segment-2");
  assert.equal(vm.runInContext("captions.size", client.context), 1);
});
