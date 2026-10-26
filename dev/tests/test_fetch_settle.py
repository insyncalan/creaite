"""#250 slice A: the SweepFetch contract the guarded live server calls (observe / finish(answered) / fetch_text) and Cap's LOW findings.
Fictional data only. The calendar rule is stubbed (slice B owns the real one; its tests are test_transcript_hold).
Run: python3 dev/tests/test_fetch_settle.py"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_fetch_transcripts as F  # noqa: E402
from test_fetch_transcripts import DAY  # noqa: E402

OPEN = "lambda event, live, created: (False, 'normal')"


class Settle(F.Fetch):
    def setUp(self):
        super().setUp()
        self.set_on()

    def test_a_stopped_or_failed_run_writes_nothing_and_counts_left(self):
        self.assertEqual(self.obs(self.read(), answered=False), {"ev-1": "left"})
        self.assertEqual(self.counts, {"fetched": 0, "held": 0, "failed": 0, "left": 1, "error": 0})
        self.assertEqual(self.inbox(), [])
        self.assertEqual(self.said, "0 transcripts fetched, 1 left: Process to load it")
        self.assertEqual(self.obs(self.read()), {"ev-1": "fetched"})                     # Process-side state untouched: a later run fetches it

    def test_an_answered_run_fetches_and_says_so_once(self):
        self.assertEqual(self.obs(self.read()), {"ev-1": "fetched"})
        self.assertEqual(self.counts["fetched"], 1)
        self.assertEqual(self.said, "1 transcript fetched")
        self.tracker_untouched()                                                         # obs asserts a second finish() returns the same

    def test_the_switch_is_read_again_at_the_end_of_the_run(self):
        off = "import json as _j; _p = T.paths.load_settings; T.fetch_on = lambda settings=None: not getattr(T, '_ended', False)"
        out = self.obs(self.read(), setup=off + "\nOLD = T.SweepFetch.finish\nT.SweepFetch.finish = lambda self, a: (setattr(T, '_ended', True), OLD(self, a))[1]")
        self.assertNotIn("fetched", out.values())
        self.assertEqual(self.inbox(), [])

    def test_the_default_hold_fails_closed(self):
        out = self.obs(self.read(), hold="None", setup="import sys; sys.modules['transcript_hold'] = None")   # the rule can't be imported
        self.assertEqual(out, {"ev-1": "held"})
        self.assertEqual(self.inbox(), [])

    def test_a_hold_that_raises_or_answers_oddly_holds(self):
        for hook in ("lambda e, l, c: 1 / 0", "lambda e, l, c: None", "lambda e, l, c: 'held'", "lambda e, l, c: (None, 'x')"):
            with self.subTest(hook=hook):
                self.assertEqual(self.obs(self.read(), hold=hook), {"ev-1": "held"})
                self.assertEqual(self.inbox(), [])

    def test_the_hold_is_asked_for_each_transcript_and_any_hold_holds(self):
        two = F.transcript_result()
        two["transcripts"].append({**two["transcripts"][0], "createdDateTime": f"{DAY}T10:00:30Z"})
        hook = "lambda e, l, c: (c is not None and '10:00' in str(c), 'overlaps closed meeting')"
        self.assertEqual(self.obs(self.read("ev-1", two), hold=hook), {"ev-1": "held"})
        self.assertEqual(self.inbox(), [])

    def test_the_hold_gets_the_event_the_run_read_and_the_saved_row_and_no_title_reaches_the_line(self):
        seen = self.v.root / "seen.json"
        hook = f"lambda e, l, c: (open({str(seen)!r}, 'w').write(json.dumps([e, l, c])), (True, 'confidential'))[1]"
        self.assertEqual(self.obs(self.read(), hold=hook), {"ev-1": "held"})
        event, live, created = json.loads(seen.read_text())
        self.assertEqual((event["id"], event["day"], live["id"] if "id" in live else "ev-1"), ("ev-1", DAY, "ev-1"))
        self.assertTrue(created)
        self.assertEqual(self.said, "0 transcripts fetched, 1 held back: a confidential meeting at that time")
        self.assertNotIn("ABC", self.said)

    def test_low_a_bad_url_never_raises_and_still_holds(self):
        for bad in ("meeting-transcript:///a[b", "meeting-transcript://[::1/x", "meeting-transcript:///]"):
            self.assertIsInstance(T_key(bad), tuple)
        steps = self.read("ev-1", sensitivity="confidential")
        steps[0][1]["meetingTranscriptUrl"] = "meeting-transcript:///events/a[b"
        steps[1] = ("meeting-transcript:///events/a[b", steps[1][1], False)
        self.assertNotIn("fetched", self.obs(steps).values())
        self.assertEqual(self.inbox(), [])

    def test_low_an_at_sign_in_a_later_segment_does_not_merge_two_meetings(self):
        a, b = T_key("meeting-transcript:///events/x@1"), T_key("meeting-transcript:///events/x")
        self.assertNotEqual(a, b)
        self.assertEqual(T_key("meeting-transcript:///u:p@h/events/x"), T_key("meeting-transcript:///events/x"))   # user info still goes

    def test_low_one_read_that_cant_be_settled_doesnt_stop_the_others(self):
        steps = self.read("ev-1") + self.read("ev-2", F.result_at("15:05", subject="Weekly sync 12"))
        boom = ("orig = T.fetch_one\n"
                "T.fetch_one = lambda eid, *a, **k: (_ for _ in ()).throw(RuntimeError('x')) if eid == 'ev-1' else orig(eid, *a, **k)")
        out = self.obs(steps, boom)
        self.assertEqual(out["ev-2"], "fetched")
        self.assertEqual(out["ev-1"], "left")                                            # counted, not lost
        self.assertEqual(self.inbox(), [f"{DAY} Weekly sync 12.vtt"])

    def test_low_the_queue_is_capped(self):
        out = self.obs(self.read(), "T.QUEUE_MAX = 10")
        self.assertEqual(out, {"ev-1": "left"})
        self.assertEqual(self.inbox(), [])

    def test_low_no_partial_file_is_left_when_writing_fails(self):
        out = self.obs(self.read(), "T.tidy_vtt = lambda *a, **k: (_ for _ in ()).throw(ValueError('x'))")
        self.assertEqual(self.inbox(), [])
        self.assertNotEqual(out.get("ev-1"), "fetched")
        # a fault after the .vtt was opened (the chat) removes the .vtt as well
        out = self.obs(self.read(), "import io, builtins\n_o = builtins.open\n"
                       "def op(p, m='r', *a, **k):\n    f = _o(p, m, *a, **k)\n"
                       "    if m == 'x': f.write = lambda t: (_ for _ in ()).throw(OSError(28, 'full'))\n    return f\n"
                       "builtins.open = op")
        self.assertEqual(self.inbox(), [])
        self.assertEqual(out.get("ev-1"), "error")

    def test_the_write_never_overwrites(self):
        (self.v.root / "inbox").mkdir(exist_ok=True)
        (self.v.root / "inbox" / f"{DAY} ABC Steering.vtt").write_text("mine")
        self.obs(self.read())
        self.assertEqual((self.v.root / "inbox" / f"{DAY} ABC Steering.vtt").read_text(), "mine")
        self.assertEqual(len(self.inbox()), 2)

    def test_fetch_text_is_counts_only(self):
        import transcripts as T
        self.assertEqual(T.fetch_text({}), "")
        self.assertEqual(T.fetch_text({"fetched": 2, "held": 1, "left": 1}),
                         "2 transcripts fetched, 1 held back: a confidential meeting at that time, 1 left: Process to load it")
        self.assertIn("2 held back: confidential meetings", T.fetch_text({"held": 2}))


for _name in dir(F.Fetch):                      # the ported tests run in test_fetch_transcripts; only this file's own run here
    if _name.startswith("test_") and _name not in Settle.__dict__:
        setattr(Settle, _name, None)


def T_key(uri):
    import transcripts as T
    return T.meeting_key(uri)


if __name__ == "__main__":
    unittest.main()
