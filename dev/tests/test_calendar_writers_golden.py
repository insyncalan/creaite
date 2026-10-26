"""#375 E1 S4 (2.6.9): the three calendar WRITERS save what they saved in 2.6.8, except where the difference is intended.

Run: python3 dev/tests/test_calendar_writers_golden.py       (quick tier: throwaway vaults, no Chrome, no Claude)

Writers: sweep.calendar (a save: sweep.calendar_row, and keep_held_past_days for the past days already held), and
sweep.rescrub_calendar (_clean_calendar_file). A fixture sweep reply (normal, stamped-by-nobody rows with attendees and addresses,
organiser, attachments, Teams, recurrence, an all-day row, a private and a confidential row, an ignored row, a repeated ID, a bad time)
and a held calendar (past days: unstamped rows with a join link and a passcode, a junk key, a stamped row, a private row) are written by
each writer, and the file is compared key by key with dev/tests/fixtures/writers_golden_268.json, the same run on the 2.6.8 release.
Allowed differences, and only these: the `clean` stamps (top level and rows), the body (filtered: every line left must be a line the
2.6.8 file held, and no join link or passcode is in it), and keys outside ROW_KEYS on a saved row (junk the filter removes).
Regenerate the golden (only from a 2.6.8 tree):  python3 test_calendar_writers_golden.py --generate <out.json>
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

GOLDEN = HERE / "fixtures" / "writers_golden_268.json"
NOW = "2026-10-28 10:00"               # a Wednesday: the window starts Monday 26th, so the 26th and 27th are past days inside it
BODY = "Agenda\nBudget and plan\nLink https://example.com/join/abc123def456 now\nPassword: swordfish99\nKeep this line"
PEOPLE = [{"name": "Sam Lee", "email": "sam@harbourco.example", "type": "required", "response": "accepted"},
          {"name": "Ada Fox", "email": "ada@brightwater.example", "type": "optional", "response": "none"}]


def ev(**kw):
    return {"title": "Meeting", "start": "09:00", "end": "10:00", **kw}


SPEC = {"days": {
    "2026-10-27": [ev(id="past-from-reply", title="Reply for a past day", start="09:00", end="09:30")],      # the held 27th wins
    "2026-10-28": [
        ev(id="n1", title="Weekly sync", where="Room 204", teams=True, organiser="Pat Doe", organiser_email="Pat Doe <pat.doe@brightwater.example>",
           recurrence="weekly", body=BODY, attendees=PEOPLE, attachments=[{"name": "plan.docx"}, "notes.txt"]),
        ev(id="n2", title="Mine", start="11:00", end="11:30", organiser=True, body="Plain"),
        ev(id="n1", title="Repeated ID", start="12:00", end="12:30"),
        ev(id="p1", title="Dentist", start="13:00", end="14:00", sensitivity="private", where="Clinic", teams=True, body=BODY, attendees=PEOPLE),
        ev(id="c1", title="Board pay", start="14:00", end="15:00", sensitivity="confidential", where="HR", teams=True, organiser="Pat Doe",
           body=BODY, attendees=PEOPLE, attachments=["pay.xlsx"], recurrence="monthly"),
        ev(id="t1", title="ToDo: tidy desk", start="15:00", end="15:15"),
        ev(id="b1", title="Bad times", start="16:30", end="16:00"),
        ev(id="a1", title="Offsite", all_day=True, where="Harbour Hotel"),
    ],
    "2026-10-29": [ev(id="n3", title="Quay design", where="Teams", teams=True, organiser="Ada Fox", body="Notes", attendees=PEOPLE[:1])],
}}
HELD_ROWS = {
    "2026-10-26": [
        {"id": "h1", "start": "09:00", "end": "10:00", "all_day": False, "title": "Held review", "where": "Room 1", "teams": True, "private": False,
         "organiser": "Pat Doe", "sensitivity": "normal", "organiser_email": "pat.doe@brightwater.example", "recurrence": "weekly",
         "body": BODY, "attendees": PEOPLE, "attachments": ["plan.docx"], "description": "junk key"},
        {"id": "h2", "start": "11:00", "end": "11:30", "all_day": False, "title": "Held private", "where": "", "teams": True, "private": True,
         "organiser": False},
        {"id": "h3", "start": "14:00", "end": "15:00", "all_day": False, "title": "Held confidential", "where": "", "teams": False, "private": False,
         "organiser": False, "sensitivity": "confidential"},
    ],
    "2026-10-27": [
        {"id": "h4", "start": "10:00", "end": "11:00", "all_day": False, "title": "Held all-hands", "where": "Teams", "teams": True, "private": False,
         "organiser": True, "sensitivity": "normal", "body": "Kept as stored", "attendees": PEOPLE[:1], "attachments": ["deck.pptx"]},
        {"id": "h5", "start": "", "end": "", "all_day": True, "title": "Held offsite", "where": "Harbour Hotel", "teams": False, "private": False,
         "organiser": False, "sensitivity": "normal"},
    ],
    "2026-10-28": [
        {"id": "h6", "start": "08:00", "end": "08:30", "all_day": False, "title": "Held today", "where": "", "teams": False, "private": False,
         "organiser": False, "sensitivity": "normal", "body": BODY},
    ],
}
SAVED = {"fetched": "2026-10-27 08:00", "to": "2026-10-30", "days": HELD_ROWS}
SCENARIOS = ("sweep_save", "rescrub")
SAVED_KEYS = {"id", "start", "end", "all_day", "title", "where", "teams", "private", "organiser", "sensitivity", "organiser_email", "recurrence",
              "body", "attendees", "attachments", "clean"}


def build_vault(test=None):
    v = Vault()
    if test:
        test.addCleanup(v.cleanup)
    cal = v.root / "system/staging/calendar.json"
    cal.parent.mkdir(parents=True, exist_ok=True)
    cal.write_text(json.dumps(SAVED), encoding="utf-8")
    return v


def run(v, code):
    env = {**os.environ, "CREAITE_NO_LAUNCH": "1", "CREAITE_NOW": NOW}
    r = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, 'system/scripts')\n" + code], cwd=v.root, capture_output=True, text=True,
                       env=env)
    if r.returncode != 0:
        raise AssertionError(r.stderr[-800:])
    return json.loads((v.root / "system/staging/calendar.json").read_text(encoding="utf-8"))


def run_all():
    out = {}
    v = build_vault()
    try:
        spec = v.root / "system/staging/drafts/calendar-fixture.json"
        spec.parent.mkdir(parents=True, exist_ok=True)
        spec.write_text(json.dumps(SPEC), encoding="utf-8")
        out["sweep_save"] = run(v, "import sweep\nsweep.calendar('system/staging/drafts/calendar-fixture.json')")
    finally:
        v.cleanup()
    v = build_vault()
    try:
        out["rescrub"] = run(v, "import sweep\nsweep.rescrub_calendar()")
    finally:
        v.cleanup()
    return out


def norm(x, drop):
    """Without the stamps and the keys in `drop`; without empty lists (a filter that leaves nothing leaves no key)."""
    if isinstance(x, dict):
        return {k: norm(v, drop) for k, v in x.items() if k not in drop and v != []}
    if isinstance(x, list):
        return [norm(v, drop) for v in x]
    return x


def rows(cal):
    return {(d, r.get("id") or r.get("title")): r for d, rs in (cal.get("days") or {}).items() for r in rs}


class Writers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.new = run_all()
        cls.old = json.loads(GOLDEN.read_text(encoding="utf-8"))

    def test_the_golden_covers_every_writer(self):
        self.assertEqual(set(self.old), set(SCENARIOS))
        self.assertTrue(rows(self.old["sweep_save"]) and rows(self.old["rescrub"]))

    def _compare(self, name):
        old, new = self.old[name], self.new[name]
        self.assertEqual({k: v for k, v in new.items() if k not in ("clean", "days")}, {k: v for k, v in old.items() if k not in ("clean", "days")},
                         f"{name}: fetched/to differ")
        self.assertEqual(sorted(map(str, rows(new))), sorted(map(str, rows(old))), f"{name}: the saved meetings differ")
        self.assertEqual(list(new["days"]), list(old["days"]), f"{name}: the days or their order differ")
        for key, o in rows(old).items():
            n = rows(new)[key]
            drop = {"clean", "body"}
            self.assertEqual(norm({k: v for k, v in n.items() if k in SAVED_KEYS}, drop), norm({k: v for k, v in o.items() if k in SAVED_KEYS}, drop),
                             f"{name} {key}: a field changed or was lost")
            # the body: filtered, so every line left is a line 2.6.8 held, and nothing to join or unlock a meeting
            nb, ob = str(n.get("body") or ""), str(o.get("body") or "")
            for line in nb.splitlines():
                self.assertIn(line, ob.splitlines(), f"{name} {key}: a body line that 2.6.8 did not hold")
            self.assertNotIn("swordfish99", nb)
            self.assertNotIn("abc123def456", nb)
            if ob and not any(x in ob for x in ("swordfish99", "abc123def456")):
                self.assertEqual(nb, ob, f"{name} {key}: a clean body changed")

    def test_the_sweep_save_matches_2_6_8(self):
        self._compare("sweep_save")

    def test_the_rescrub_matches_2_6_8(self):
        self._compare("rescrub")

    def test_the_new_files_are_stamped_and_no_row_is_without_a_stamp(self):
        for name in SCENARIOS:
            self.assertTrue(self.new[name].get("clean"))
            for r in rows(self.new[name]).values():
                self.assertTrue(r.get("clean"), f"{name}: a row without a stamp")

    def test_no_row_keeps_a_key_outside_the_saved_keys(self):
        keys = SAVED_KEYS
        for name in SCENARIOS:
            for r in rows(self.new[name]).values():
                self.assertFalse(set(r) - keys, f"{name}: {set(r) - keys}")

    def test_private_and_confidential_rows_keep_nothing_but_their_head(self):
        for name in SCENARIOS:
            for (d, k), r in rows(self.new[name]).items():
                if r.get("private") or r.get("sensitivity") == "confidential":
                    for gone in ("attendees", "attachments", "body", "organiser_email", "recurrence"):
                        self.assertNotIn(gone, r, f"{name} {k}")
                    self.assertFalse(r.get("where") if r.get("private") else False)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--generate":
        Path(sys.argv[2]).write_text(json.dumps(run_all(), indent=1, sort_keys=True), encoding="utf-8")
    else:
        unittest.main()
