"""#375 E1, slice S4: every reader of calendar.json goes through calendar_gateway and sees no more than its purpose allows.

Run: python3 dev/tests/test_calendar_readers_purpose.py      (quick tier: throwaway vaults, no Chrome, no Claude)

- day / meta readers (Today's day view, Intake, the day line, Close the day, transcript rows, draft attendees, the sweep's counts) get no body.
- body readers (draft agenda, prep page, the shared prep days) get at most 1,500 characters, whole lines; the Shape prompt holds at most
  600 characters of it.
- an unstamped row is filtered at read (the label rule), a stamped one is served as stored, and reading never writes the file.
All values are made up.
"""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_tracker import Vault  # noqa: E402

DAY = "2026-10-26"
LINES = "\n".join(f"Agenda line {i:03d} budget and plan for the quarter ahead" for i in range(120))     # about 6,000 characters
BODY = "BODYSENTINEL first line\n" + LINES + "\nPassword swordfish"
ROW = {"id": "r1", "start": "09:00", "end": "10:00", "title": "Budget review", "where": "Room 204", "organiser": "Pat Doe",
       "organiser_email": "pat.doe@brightwater.example", "sensitivity": "normal", "teams": True, "body": BODY,
       "attendees": [{"name": "Sam Lee", "email": "sam@brightwater.example", "type": "required", "response": "accepted"}],
       "attachments": ["plan.docx"]}
STAMPED = {**ROW, "id": "r2", "title": "Stamped review", "clean": 1, "body": "BODYSENTINEL kept as stored"}

DAY_READERS = {
    "today day view": "import build_dashboard as b\nprint(json.dumps(b.calendar([])))",
    "transcript rows": "import transcripts as t\nprint(json.dumps(t.calendar_rows()))",
    "draft attendees": f"import drafts as d\nprint(json.dumps(d._meeting_attendees('{DAY}', 'Budget review')))",
    "close the day": "import close_day as c\nprint(json.dumps(c.Lookup().meeting('r1')))",
    "intake rows": f"import build_dashboard as b, datetime\nprint(json.dumps(b.inbox_meetings({{}}, [], datetime.date.fromisoformat('{DAY}'))))",
}
META_READERS = {
    "sweep span": f"import sweep, datetime\nprint(sweep.calendar_span(datetime.date.fromisoformat('{DAY}')))",
    "sweep start": f"import sweep, datetime\nprint(sweep.calendar_fetch_from(datetime.date.fromisoformat('{DAY}')))",
    "sweep count": f"import sweep\nprint(sweep.saved_meetings_from('{DAY}'))",
    "refresh outcome": "import calendar_refresh as r, time\nprint(r.outcome(time.time() - 3600))",
    "dashboard fetched": "import build_dashboard as b\nprint(b.calendar_days({}, __import__('datetime').datetime(2026, 10, 26, 9, 0)).get('fetched'))",
}


def vault(test, rows=None):
    v = Vault()
    test.addCleanup(v.cleanup)
    cal = v.root / "system/staging/calendar.json"
    cal.parent.mkdir(parents=True, exist_ok=True)
    cal.write_text(json.dumps({"fetched": "2026-10-26 08:00", "to": "2026-10-30", "days": {DAY: rows or [ROW, STAMPED]}}), encoding="utf-8")
    return v, cal


def run(v, code):
    r = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts')\n" + code], cwd=v.root,
                       capture_output=True, text=True, env={**os.environ, "CREAITE_NO_LAUNCH": "1", "CREAITE_NOW": "2026-10-26T09:00:00"})
    return r


def ok(test, v, name, code):
    r = run(v, code)
    test.assertEqual(r.returncode, 0, f"{name}: {r.stderr[-400:]}")
    return r.stdout


class Purposes(unittest.TestCase):
    def test_day_and_meta_readers_get_no_body(self):
        v, _ = vault(self)
        for name, code in {**DAY_READERS, **META_READERS}.items():
            out = ok(self, v, name, code)
            self.assertNotIn("BODYSENTINEL", out, name)
            self.assertNotIn("Agenda line", out, name)
            self.assertNotIn('"body"', out, name)

    def test_day_readers_still_show_the_meeting(self):
        v, _ = vault(self)
        self.assertIn("Budget review", ok(self, v, "day view", DAY_READERS["today day view"]))
        self.assertIn("Sam Lee", ok(self, v, "attendees", DAY_READERS["draft attendees"]))
        self.assertIn("r1", ok(self, v, "transcripts", DAY_READERS["transcript rows"]))

    def test_meta_readers_count_and_date(self):
        v, _ = vault(self)
        self.assertEqual(ok(self, v, "count", META_READERS["sweep count"]).strip(), "2")
        self.assertIn("2026-10-26 08:00", ok(self, v, "fetched", META_READERS["dashboard fetched"]))
        self.assertIn("'meetings': 2", ok(self, v, "outcome", META_READERS["refresh outcome"]))

    def test_body_readers_stay_within_1500_characters(self):
        v, _ = vault(self)
        for name, code in {
                "agenda event": "import drafts as d\nprint(json.dumps(d.calendar_event({'eid': 'r1'})))",
                "prep page event": f"import prep_page as p\nprint(json.dumps(p._event('x|09:00|Budget review', '{DAY}')))",
                "shared prep days": f"import build_dashboard as b\nprint(json.dumps(b.saved_calendar_days()['{DAY}'][0]))"}.items():
            ev = json.loads(ok(self, v, name, code))
            body = ev.get("body") or ""
            self.assertTrue(body.startswith("BODYSENTINEL"), name)
            self.assertLessEqual(len(body), 1500, name)
            self.assertNotIn("swordfish", body.lower(), name)           # unstamped: filtered at read
            self.assertTrue(all(ln.startswith(("BODYSENTINEL", "Agenda line")) for ln in body.split("\n")), name)     # whole lines only

    def test_prep_panel_keeps_what_the_panel_needs_and_agenda_gets_no_attachments(self):
        v, _ = vault(self)
        shared = json.loads(ok(self, v, "shared", f"import build_dashboard as b\nprint(json.dumps(b.saved_calendar_days()['{DAY}'][0]))"))
        self.assertEqual(shared["attachments"], ["plan.docx"])
        self.assertIn("organiser_email", shared)
        agenda = json.loads(ok(self, v, "agenda", "import drafts as d\nprint(json.dumps(d.calendar_event({'eid': 'r1'})))"))
        self.assertNotIn("attachments", agenda)
        self.assertNotIn("organiser_email", agenda)

    def test_a_stamped_row_is_served_as_stored(self):
        v, _ = vault(self)
        ev = json.loads(ok(self, v, "stamped", "import drafts as d\nprint(json.dumps(d.calendar_event({'eid': 'r2'})))"))
        self.assertEqual(ev["body"], "BODYSENTINEL kept as stored")

    def test_the_shape_prompt_holds_at_most_600_characters_of_the_body(self):
        v, _ = vault(self)
        code = (f"import prep_page as p, prep_shape as s\nev = p._event('x|09:00|Budget review', '{DAY}')\n"
                "ctx = {'day': '" + DAY + "', 'meeting': {'body': ev['body']}, 'items': []}\n"
                "src = [x for x in s._context_sources(ctx, False, {}) if x['kind'] == 'invite'][0]\nprint(len(src['text']))")
        n = int(ok(self, v, "shape", code).strip())
        self.assertLessEqual(n, len("The invite says: ") + 600 + 3)

    def test_reading_never_writes_the_file(self):
        v, cal = vault(self)
        before, mtime = cal.read_bytes(), cal.stat().st_mtime_ns
        for name, code in {**DAY_READERS, **META_READERS}.items():
            ok(self, v, name, code)
        ok(self, v, "agenda", "import drafts as d\nprint(d.calendar_event({'eid': 'r1'}))")
        ok(self, v, "prep", f"import prep_page as p\nprint(p._event('x|09:00|Budget review', '{DAY}'))")
        self.assertEqual(cal.read_bytes(), before)
        self.assertEqual(cal.stat().st_mtime_ns, mtime)

    def test_a_private_event_gets_its_head_only_in_every_reader(self):
        priv = {**ROW, "id": "p1", "title": "Doctor", "sensitivity": "private", "private": True}
        v, _ = vault(self, [priv])
        ev = json.loads(ok(self, v, "agenda", "import drafts as d\nprint(json.dumps(d.calendar_event({'eid': 'p1'})))"))
        self.assertEqual(ev.get("title"), "Busy")
        for k in ("body", "attendees", "where", "organiser"):
            self.assertNotIn(k, ev)


if __name__ == "__main__":
    unittest.main()
