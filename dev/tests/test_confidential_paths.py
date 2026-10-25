"""#362 (Wanda's review, MEDIUM 1): a confidential meeting gets no project code on any path that matches calendar meetings.

Run: python3 dev/tests/test_confidential_paths.py   (no browser, no model)
One test per path, each with the title "[DEF] x" and sensitivity confidential (and the private one where it applies):
the set-aside lists, the Prep entry, the hub records, the next-day list and "Note for this meeting" (capture.meeting).
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system/scripts"))
import build_dashboard as bd  # noqa: E402
import capture  # noqa: E402
from test_dashboard import today  # noqa: E402

PROJECTS = [{"code": "ABC", "name": "Harbour Upgrade"}, {"code": "DEF", "name": "Orchard Rollout"}]
EV = {"id": "e1", "title": "[DEF] x", "start": "10:00", "end": "11:00", "sensitivity": "confidential"}


class ConfidentialPaths(unittest.TestCase):
    def test_set_aside_lists(self):
        m = {"key": "k", "day": "2026-10-20", "start": "10:00", "end": "11:00", "title": "[DEF] x", "p": "DEF", "private": False,
             "confidential": True}
        later, gone = bd._ir_aside_lists({"later": [m], "cleared": [m]}, [], [])
        self.assertIsNone(later[0]["p"])
        self.assertIsNone(gone[0]["p"])
        later, _ = bd._ir_aside_lists({"later": [dict(m, confidential=False)], "cleared": []}, [], [])
        self.assertEqual(later[0]["p"], "DEF")

    def test_prep_entry(self):
        """The Prep entry shows no project for a confidential meeting unless Alan chose it (a remembered series); a private or
        personal one has no brief at all."""
        ctx = {"projects": PROJECTS, "remembered": {}, "history": [], "items": None, "ms_names": {}, "vips": {}, "today": today()}
        _, rec = bd.prep_entry(EV, today(), ctx)
        self.assertEqual((rec["p"], rec["how"]), (None, "confidential"))
        _, chosen = bd.prep_entry(EV, today(), {**ctx, "remembered": {bd.series_of(EV["title"]): "DEF"}})
        self.assertEqual((chosen["p"], chosen["how"]), ("DEF", "remembered"))
        _, normal = bd.prep_entry({**EV, "sensitivity": "normal"}, today(), ctx)
        self.assertEqual(normal["p"], "DEF")
        self.assertIsNone(bd.prep_entry({**EV, "sensitivity": "private"}, today(), ctx))
        self.assertIsNone(bd.prep_entry({**EV, "sensitivity": "personal"}, today(), ctx))

    def test_hub_records(self):
        day = today().isoformat()
        for ev, want in ((EV, []), ({**EV, "sensitivity": "normal"}, ["DEF"])):
            hub = bd.meeting_hub({}, PROJECTS, today(), {"days": {day: [ev]}}, [], [], [], {})
            rec = next(r for r in hub.values() if r.get("title") == "[DEF] x")
            self.assertEqual(rec["p"], want)
        priv = bd.meeting_hub({}, PROJECTS, today(), {"days": {day: [{**EV, "sensitivity": "private"}]}}, [], [], [], {})
        self.assertFalse([r for r in priv.values() if r.get("title") == "[DEF] x"])

    def test_capture_meeting(self):
        day = today().isoformat()
        orig = bd.saved_calendar_days
        try:
            bd.saved_calendar_days = lambda: {day: [dict(EV, attendees=[{"name": "A B"}])]}
            r = capture.meeting(day, "10:00", "[DEF] x", PROJECTS)
            self.assertEqual((r["code"], r["how"], r["with"]), (None, "confidential", []))
            self.assertNotIn("DEF", json.dumps(r).replace("[DEF] x", ""))
            # #343: only a project Alan chose (a remembered series) counts for a confidential meeting; "No project" stays none
            ser = bd.series_of("[DEF] x")
            r = capture.meeting(day, "10:00", "[DEF] x", PROJECTS, {ser: "DEF"})
            self.assertEqual((r["code"], r["how"]), ("DEF", "remembered"))
            self.assertIsNone(capture.meeting(day, "10:00", "[DEF] x", PROJECTS, {ser: "_portfolio"})["code"])
            self.assertIsNone(capture.meeting(day, "10:00", "[DEF] x", PROJECTS, {})["code"])   # a guess from the title shows nothing
            bd.saved_calendar_days = lambda: {day: [dict(EV, sensitivity="normal")]}
            self.assertEqual(capture.meeting(day, "10:00", "[DEF] x", PROJECTS)["code"], "DEF")   # not confidential: still preselected
            bd.saved_calendar_days = lambda: {day: [dict(EV, sensitivity="private")]}
            self.assertIsNone(capture.meeting(day, "10:00", "[DEF] x", PROJECTS))
        finally:
            bd.saved_calendar_days = orig

    def test_next_day_list_source(self):
        src = Path(bd.__file__).read_text()
        self.assertIn('"p": ev_shown_p(ev)', src)
        self.assertIsNone(bd.ev_shown_p(EV))
        self.assertEqual(bd.ev_shown_p({**EV, "sensitivity": "normal", "p": "DEF"}), "DEF")

    def test_sensitivity_not_just_the_flag(self):
        """Every path reads invite_clean.sensitivity (fails closed), not only ev["private"] or the confidential flag."""
        src = (Path(bd.__file__)).read_text()
        self.assertNotIn('if ev.get("all_day") or ev.get("private"):', src)
        self.assertNotIn('if not ev or ev.get("private"):', Path(capture.__file__).read_text())


if __name__ == "__main__":
    unittest.main()
