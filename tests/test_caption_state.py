"""Run from the project folder: python -m unittest discover -s tests -v.

These tests exercise revision state only; no server or network is started.
"""

import unittest

from caption_state import CaptionRevisionState


def caption(**changes):
    message = {
        "type": "CAPTION_UPDATE", "session": "L1", "segment": 1,
        "revision": 1, "source_ts": 1000.0, "final": False, "text": "TCP",
    }
    message.update(changes)
    return message


class CaptionRevisionTests(unittest.TestCase):
    def test_all_increasing_revisions_are_accepted_including_final(self):
        state = CaptionRevisionState()
        # Revisions need not be consecutive, and there need not be three of them.
        for revision, final in [(1, False), (2, False), (7, False), (10, True)]:
            with self.subTest(revision=revision):
                self.assertTrue(state.accept(caption(revision=revision, final=final), "L1"))
        self.assertEqual(state.latest_caption["revision"], 10)
        self.assertTrue(state.latest_caption["final"])

    def test_duplicate_and_stale_updates_leave_state_unchanged(self):
        state = CaptionRevisionState()
        original = caption(revision=4)
        self.assertTrue(state.accept(original, "L1"))
        for update in [caption(revision=4, text="duplicate"), caption(revision=2, final=True)]:
            self.assertFalse(state.accept(update, "L1"))
            self.assertEqual(state.latest_caption, original)

    def test_final_cannot_be_overwritten_even_by_higher_revision(self):
        state = CaptionRevisionState()
        original = caption(revision=2, final=True)
        self.assertTrue(state.accept(original, "L1"))
        for revision, final in [(1, False), (2, True), (3, False), (4, True)]:
            self.assertFalse(state.accept(caption(revision=revision, final=final), "L1"))
            self.assertEqual(state.latest_caption, original)

    def test_new_segment_has_its_own_revision_counter(self):
        state = CaptionRevisionState()
        self.assertTrue(state.accept(caption(revision=20, final=True), "L1"))
        self.assertTrue(state.accept(caption(segment=2, revision=1), "L1"))
        self.assertFalse(state.accept(caption(segment=1, revision=21, final=True), "L1"))
        self.assertEqual(state.latest_caption["segment"], 2)

    def test_malformed_comparison_fields_do_not_poison_state(self):
        state = CaptionRevisionState()
        invalid = [
            {"segment": 0}, {"segment": -1}, {"segment": True}, {"segment": "1"},
            {"revision": 0}, {"revision": -1}, {"revision": True}, {"revision": "1"},
            {"final": "false"}, {"final": 1}, {"final": None}, {"type": "SOURCE_DONE"},
        ]
        for fields in invalid:
            with self.subTest(fields=fields):
                self.assertFalse(state.accept(caption(**fields), "L1"))
                self.assertIsNone(state.latest_caption)
        self.assertTrue(state.accept(caption(), "L1"))

    def test_session_must_match_hello_and_existing_stream(self):
        state = CaptionRevisionState()
        self.assertFalse(state.accept(caption(session="L2"), "L1"))
        self.assertFalse(state.accept(caption(session=None), None))
        self.assertTrue(state.accept(caption(), "L1"))
        self.assertFalse(state.accept(caption(session="L2", segment=2), "L2"))
        self.assertEqual(state.latest_caption["session"], "L1")

    def test_preserves_metadata_and_does_not_keep_the_callers_dictionary(self):
        state = CaptionRevisionState()
        update = caption(source_ts=1234.5, phase="normal")
        self.assertTrue(state.accept(update, "L1"))
        self.assertEqual(state.latest_caption, update)
        self.assertIsNot(state.latest_caption, update)
        update["revision"] = 999
        self.assertEqual(state.latest_caption["revision"], 1)

    def test_old_final_is_rejected_even_after_many_later_segments(self):
        state = CaptionRevisionState()
        for segment in range(1, 10001):
            self.assertTrue(state.accept(caption(segment=segment, final=True), "L1"))
        self.assertEqual(state.latest_caption["segment"], 10000)
        self.assertFalse(state.accept(caption(segment=1, revision=999, final=True), "L1"))
        self.assertEqual(state.latest_caption["segment"], 10000)


if __name__ == "__main__":
    unittest.main()
