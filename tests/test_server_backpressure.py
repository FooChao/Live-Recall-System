"""Run with: python3 -m unittest discover -s tests -p "test_server_backpressure.py" -v"""

import asyncio
import json
import unittest

import websockets

import solution_server
from caption_state import CaptionRevisionState
from history_store import HistoryStore

SEGMENTS = 200
# Large captions fill the stalled client's socket buffers within a second,
# which the public source would take minutes to do. Compression is disabled on
# the test connections, otherwise this repetitive text shrinks to a few bytes.
TEXT = "x" * 2000


def hello(client_id):
    return json.dumps({
        "type": "CLIENT_HELLO", "client_id": client_id, "session": "L1",
        "last_segment": 0, "last_revision": 0, "history_seconds": 30,
    })


class ServerBackpressureTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        solution_server.CLIENTS.clear()
        solution_server.REVISION_STATE = CaptionRevisionState()
        solution_server.HISTORY = HistoryStore()
        self.server = await websockets.serve(
            solution_server.handler, "127.0.0.1", 0,
            write_limit=solution_server.WRITE_LIMIT_BYTES,
        )
        port = self.server.sockets[0].getsockname()[1]
        self.uri = f"ws://127.0.0.1:{port}"

    async def asyncTearDown(self):
        self.server.close()
        await self.server.wait_closed()

    async def connect_client(self, client_id):
        ws = await websockets.connect(self.uri, compression=None)
        await ws.send(hello(client_id))
        while len(solution_server.CLIENTS) < client_id:
            await asyncio.sleep(0.01)
        return ws, list(solution_server.CLIENTS.values())[-1]

    async def run_source(self):
        async with websockets.connect(self.uri, compression=None) as source:
            await source.send(json.dumps({"type": "SOURCE_HELLO", "session": "L1"}))
            for segment in range(1, SEGMENTS + 1):
                for revision in (1, 2, 3):
                    await source.send(json.dumps({
                        "type": "CAPTION_UPDATE", "session": "L1",
                        "segment": segment, "revision": revision,
                        "source_ts": 0.0, "final": revision == 3, "text": TEXT,
                    }))
                    await asyncio.sleep(0.002)

    async def read_until_final(self, ws, segment):
        received = []
        while True:
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
            received.append(msg)
            if msg.get("final") and msg["segment"] == segment:
                return received

    async def test_stalled_client_is_coalesced_and_dropped_without_delaying_reader(self):
        stalled, stalled_outbox = await self.connect_client(1)
        reader, _ = await self.connect_client(2)

        reader_task = asyncio.create_task(self.read_until_final(reader, SEGMENTS))
        await self.run_source()
        received = await reader_task

        self.assertEqual(received[0], {"type": "HISTORY", "items": []})
        finals = [m["segment"] for m in received[1:] if m["final"]]
        self.assertEqual(finals, list(range(1, SEGMENTS + 1)))
        updates = [(m["segment"], m["revision"]) for m in received[1:]]
        self.assertEqual(updates, sorted(set(updates)))

        self.assertGreater(stalled_outbox.coalesced, 0)
        self.assertTrue(stalled_outbox.overflowed)
        with self.assertRaises(websockets.ConnectionClosed) as closed:
            while True:
                await asyncio.wait_for(stalled.recv(), timeout=5)
        self.assertEqual(closed.exception.rcvd.code, 1013)

        await reader.close()


if __name__ == "__main__":
    unittest.main()
