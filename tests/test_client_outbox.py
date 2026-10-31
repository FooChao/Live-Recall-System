"""Run with: python3 -m unittest discover -s tests -p "test_client_outbox.py" -v"""

import asyncio
import unittest

from client_outbox import ClientOutbox, Outgoing


def update(segment, revision, final=False):
    return Outgoing(f"{segment}.{revision}", segment, final)


def history():
    return Outgoing("HISTORY", None, True)


class ClientOutboxTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.outbox = ClientOutbox()

    def queued(self):
        return [item.raw for item in self.outbox.pending]

    async def drain(self):
        sent = []
        while self.outbox.pending:
            sent.append((await self.outbox.get()).raw)
        return sent

    async def test_client_that_keeps_up_receives_every_revision(self):
        sent = []
        for item in [update(1, 1), update(1, 2), update(1, 3, final=True), update(2, 1)]:
            self.assertTrue(self.outbox.put(item, now=0))
            sent.append((await self.outbox.get()).raw)
        self.assertEqual(sent, ["1.1", "1.2", "1.3", "2.1"])
        self.assertEqual(self.outbox.coalesced, 0)

    async def test_newer_revision_replaces_queued_provisional(self):
        self.outbox.put(update(1, 1), now=0)
        self.outbox.put(update(1, 2), now=0)
        self.assertEqual(await self.drain(), ["1.2"])
        self.assertEqual(self.outbox.coalesced, 1)

    async def test_final_replaces_provisional_and_finals_are_kept(self):
        for item in [update(1, 1), update(1, 2, final=True),
                     update(2, 1), update(2, 2), update(2, 3, final=True),
                     update(3, 1)]:
            self.outbox.put(item, now=0)
        self.assertEqual(await self.drain(), ["1.2", "2.3", "3.1"])
        self.assertEqual(self.outbox.coalesced, 3)

    async def test_queued_final_survives_later_update_of_its_segment(self):
        self.outbox.put(update(1, 3, final=True), now=0)
        self.outbox.put(update(1, 4), now=0)
        self.assertEqual(await self.drain(), ["1.3", "1.4"])

    async def test_history_stays_first_and_is_never_coalesced(self):
        self.outbox.put(history(), now=0)
        self.outbox.put(update(5, 1), now=0)
        self.outbox.put(update(5, 2), now=0)
        self.assertEqual(await self.drain(), ["HISTORY", "5.2"])

    async def test_lagging_client_overflows_and_get_signals_close(self):
        self.assertTrue(self.outbox.put(update(1, 1, final=True), now=0))
        self.assertTrue(self.outbox.put(update(2, 1, final=True), now=15))
        self.assertFalse(self.outbox.put(update(3, 1, final=True), now=15.1))
        self.assertEqual(self.queued(), [])
        self.assertIsNone(await self.outbox.get())
        self.assertFalse(self.outbox.put(update(4, 1, final=True), now=15.2))

    async def test_pending_count_is_bounded(self):
        for segment in range(1, ClientOutbox.MAX_PENDING + 1):
            self.assertTrue(self.outbox.put(update(segment, 1, final=True), now=0))
        self.assertFalse(self.outbox.put(update(99, 1, final=True), now=0))
        self.assertIsNone(await self.outbox.get())

    async def test_get_waits_for_put(self):
        waiter = asyncio.create_task(self.outbox.get())
        await asyncio.sleep(0)
        self.assertFalse(waiter.done())
        self.outbox.put(update(1, 1), now=0)
        self.assertEqual((await waiter).raw, "1.1")


if __name__ == "__main__":
    unittest.main()
