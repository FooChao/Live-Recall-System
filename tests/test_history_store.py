"""Run with: python3 -m unittest discover -s tests -p "test_history_store.py" -v"""

import unittest

from history_store import HistoryStore


def caption(segment, source_ts, *, revision=3, final=True, session="L1"):
    return {
        "type": "CAPTION_UPDATE",
        "session": session,
        "segment": segment,
        "revision": revision,
        "source_ts": source_ts,
        "final": final,
        "text": f"Caption {segment}",
    }


class HistoryStoreTests(unittest.TestCase):
    def setUp(self):
        self.store = HistoryStore()
        self.now = 1000.0

    def add(self, segment, age, **kwargs):
        return self.store.can_add_final(
            caption(segment, self.now - age, **kwargs), now=self.now
        )

    def history(self, **kwargs):
        return self.store.get_history(session="L1", now=self.now, **kwargs)

    def test_provisional_is_not_history(self):
        self.assertFalse(self.add(1, 5, final=False))
        self.assertTrue(self.add(1, 4, final=True))
        self.assertEqual(len(self.history()), 1)

    def test_final_is_immutable_and_not_duplicated(self):
        self.assertTrue(self.add(1, 5))
        self.assertFalse(self.add(1, 5))
        self.assertFalse(self.add(1, 4, revision=2))
        self.assertFalse(self.add(1, 3, revision=4))
        self.assertEqual([item["revision"] for item in self.history()], [3])

    def test_recall_windows_and_boundary(self):
        for segment, age in enumerate([61, 60, 31, 30, 16, 15, 5], start=1):
            self.add(segment, age)
        for seconds, expected in [(15, [6, 7]), (30, [4, 5, 6, 7]),
                                  (60, [2, 3, 4, 5, 6, 7])]:
            with self.subTest(seconds=seconds):
                items = self.history(history_seconds=seconds)
                self.assertEqual([item["segment"] for item in items], expected)

    def test_resume_excludes_already_held_finals(self):
        for segment in [37, 38, 39, 40]:
            self.add(segment, 40 - segment)
        items = self.history(last_segment=38, last_revision=3)
        self.assertEqual([item["segment"] for item in items], [39, 40])

    def test_resume_compares_revision_for_same_segment(self):
        self.add(38, 2, revision=3)
        items = self.history(last_segment=38, last_revision=2)
        self.assertEqual([item["revision"] for item in items], [3])

    def test_new_client_receives_available_context(self):
        self.add(39, 5)
        self.add(40, 1)
        items = self.history(last_segment=0, last_revision=0)
        self.assertEqual([item["segment"] for item in items], [39, 40])

    def test_session_isolation(self):
        self.add(1, 5, session="L1")
        self.add(1, 5, session="L2")
        self.assertEqual([item["session"] for item in self.history()], ["L1"])

    def test_order_does_not_depend_on_insertion_order(self):
        for segment in [3, 1, 2]:
            self.add(segment, 4 - segment)
        self.assertEqual([item["segment"] for item in self.history()], [1, 2, 3])

    def test_expiry_and_rejection_of_expired_input(self):
        retention = self.store.retention_seconds

        self.assertFalse(self.add(1, retention + 1))
        self.assertTrue(self.add(2, retention))

        self.assertEqual(
            self.store.remove_expired(now=self.now + 1), 1
        )
        self.assertEqual(
            self.store.remove_expired(now=self.now + 1), 0
        )

    def test_add_and_query_both_remove_expired(self):
        self.assertTrue(
            self.add(1, self.store.retention_seconds - 1)
        )
        self.store.can_add_final(caption(2, 1002), now=1002)
        self.assertEqual(self.store.remove_expired(now=1002), 0)
        self.assertEqual(self.store.get_history(session="L1", now=1100), [])
        self.assertEqual(self.store.remove_expired(now=1100), 0)

    def test_storage_and_results_are_independent_copies(self):
        original = caption(1, 995)
        self.store.can_add_final(original, now=self.now)

        # Changing the input dictionary must not change stored fields.
        original["text"] = "changed input"

        returned = self.history()
        self.assertEqual(returned[0]["text"], "Caption 1")

        # Changing a returned dictionary must not change stored fields.
        returned[0]["text"] = "changed result"

        self.assertEqual(self.history()[0]["text"], "Caption 1")
        self.assertEqual(self.history()[0]["source_ts"], 995)

    def test_zero_window_and_invalid_configuration(self):
        self.add(1, 0)
        self.assertEqual(self.history(history_seconds=0), [])
        for seconds in [-1, 61, float("nan"), float("inf")]:
            with self.subTest(seconds=seconds), self.assertRaises(ValueError):
                self.history(history_seconds=seconds)
        for retention in [59, float("nan"), float("inf")]:
            with self.subTest(retention=retention), self.assertRaises(ValueError):
                HistoryStore(retention_seconds=retention)


if __name__ == "__main__":
    unittest.main()
