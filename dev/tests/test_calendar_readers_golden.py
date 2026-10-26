"""#375 E1 (2.6.9): every migrated calendar reader gives what it gave in 2.6.8, except where the difference is intended.

Run: python3 dev/tests/test_calendar_readers_golden.py       (quick tier: throwaway vaults, no Chrome, no Claude)

A fixture calendar (normal rows with attendees and addresses, organiser, attachments, a Teams link, recurrence, an all-day row, a
private and a confidential row, stamped and unstamped rows) is read by each migrated reader through the new path. The result is
compared with dev/tests/fixtures/readers_golden_268.json, the same readers run on the 2.6.8 release (origin/main a62fbb0a).
ALLOWED lists, per reader, the only differences that are intended (each with its reason); anything else, a lost field above all,
fails. Regenerate the golden (only from a 2.6.8 tree):  python3 test_calendar_readers_golden.py --generate <out.json>
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

GOLDEN = HERE / "fixtures" / "readers_golden_268.json"
DAY, EARLIER = "2026-10-26", "2026-10-23"
PEOPLE = [{"name": "Sam Lee", "email": "sam@harbourco.example", "type": "required", "response": "accepted"},
          {"name": "Ada Fox", "email": "ada@brightwater.example", "type": "optional", "response": "none", "registered": True}]
BODYTEXT = "Agenda\nBudget and plan\nLink https://example.com/join/abc123def456 now\nPassword: swordfish99"
REGISTER = """# Project register

## Projects

| Code | Project name | Aliases | Key stakeholders | Email domains | Teams channels | Keywords | Senders | Exclude |
|------|--------------|---------|------------------|---------------|----------------|----------|---------|---------|
| ABC | Harbour Upgrade |  |  | harbourco.example |  |  |  |  |
"""
def row(**kw):
    """A row as sweep.calendar_row writes it: the five base keys always there."""
    return {"start": "", "end": "", "all_day": False, "title": "Meeting", "where": "", "teams": False, "private": False,
            "organiser": False, **kw}


ROWS = {
    DAY: [
        row(id="r1", start="09:00", end="10:00", title="Weekly sync", where="Room 204", organiser="Pat Doe", teams=True,
            organiser_email="pat.doe@brightwater.example", sensitivity="normal", recurrence="weekly", body=BODYTEXT, attendees=PEOPLE,
            attachments=["plan.docx"]),
        row(id="r2", start="11:00", end="11:30", title="Stamped review", clean=1, organiser=True, sensitivity="normal",
            body="Kept as stored", attendees=PEOPLE[:1]),
        row(id="r3", all_day=True, title="Offsite", sensitivity="normal"),
        row(id="rP", start="12:00", end="13:00", title="Busy", private=True, teams=True),
        row(id="rC", start="14:00", end="15:00", title="Board pay", sensitivity="confidential"),
    ],
    EARLIER: [
        row(id="r4", start="10:00", end="11:00", title="Quay design", where="Teams", teams=True, sensitivity="normal",
            attendees=PEOPLE, body="Notes"),
    ],
}
SETUP = "import sys, json, datetime; sys.path.insert(0, 'system/scripts')\nD = datetime.date.fromisoformat('" + DAY + "')\n"
PROJ = "[{'code': 'ABC', 'name': 'Harbour Upgrade'}]"
READERS = {
    "build_dashboard.calendar": f"import build_dashboard as b\nout = b.calendar({PROJ})",
    "build_dashboard.saved_calendar_days": "import build_dashboard as b\nout = b.saved_calendar_days()",
    "build_dashboard.prep_match_ev": ("import build_dashboard as b\n"
                                      "out = {e['id']: b.prep_match_ev(e['title'], e, " + PROJ + ", {}) for d in b.saved_calendar_days().values() for e in d}"),
    "build_dashboard.inbox_meetings": f"import build_dashboard as b\nout = b.inbox_meetings({{}}, {PROJ}, D)",
    "build_dashboard.fetched": "import build_dashboard as b\nout = b.calendar_days({}, datetime.datetime(2026, 10, 26, 9, 0)).get('fetched')",
    "close_day.Lookup.meeting": "import close_day as c\nL = c.Lookup()\nout = {i: L.meeting(i) for i in ('r1', 'r2', 'rP', 'rC', 'r4')}",
    "transcripts.calendar_rows": "import transcripts as t\nout = t.calendar_rows()",
    "drafts.calendar_event": "import drafts as d\nout = {i: d.calendar_event({'eid': i}) for i in ('r1', 'r2', 'rP', 'rC', 'r4')}",
    "drafts.followup_facts": ("import drafts as d\n"
                              "out = {i: d.followup_facts({'eid': i, 'files': []})['attendees'] for i in ('r1', 'r2', 'rP', 'rC', 'r4')}"),
    "drafts._meeting_attendees": ("import drafts as d\n"
                                  "out = [d._meeting_attendees('" + DAY + "', 'Weekly sync'), d._meeting_attendees('" + EARLIER + "', 'Quay design'), "
                                  "d._meeting_attendees('" + DAY + "', 'Board pay')]"),
    "prep_page._event": ("import prep_page as p\n"
                         "out = {t: p._event('x|' + s + '|' + t, '" + DAY + "') for s, t in (('09:00', 'Weekly sync'), ('11:00', 'Stamped review'), "
                         "('12:00', 'Busy'), ('14:00', 'Board pay'))}"),
    "calendar_refresh.outcome": "import calendar_refresh as r, time\nout = r.outcome(time.time() - 3600)",
    "sweep.calendar_fetch_from": "import sweep\nout = str(sweep.calendar_fetch_from(D))",
    "sweep.calendar_span": "import sweep\nout = str(sweep.calendar_span(D))",
    "sweep.saved_meetings_from": "import sweep\nout = [sweep.saved_meetings_from('" + EARLIER + "'), sweep.saved_meetings_from('" + DAY + "')]",
}

# Intended differences, per reader: keys removed (at any depth) from both sides before comparing, with the reason. Everything else
# must be equal, so a field a reader used and lost fails here. Two normalisations apply to all: an empty list equals an absent key
# (no reader tells them apart), and the gateway forces "sensitivity": "private" on a private row (fails closed; invite_clean.sensitivity
# reads a private row either way). A private or confidential row is compared by its head fields: the gateway gives no place, Teams
# flag or organiser for it, whatever the purpose (every reader that wants them skips such a row first).
BODY = "body"
ALLOWED = {
    "build_dashboard.saved_calendar_days": {BODY: "filtered by the 2.6.9 composition D filter (checked on its own)",
                                            "registered": "no reader uses an attendee's registered flag"},
    "drafts.calendar_event": {BODY: "filtered by the 2.6.9 filter", "registered": "unused",
                              "attachments": "the draft reader never reads them (agenda purpose)",
                              "organiser_email": "the draft reader never reads it (agenda purpose)"},
    "prep_page._event": {BODY: "filtered by the 2.6.9 filter", "registered": "unused",
                         "email": "prep_page reads title, start, end and where; the invite's people come from the Prep entry",
                         "organiser_email": "not read by prep_page"},
    "transcripts.calendar_rows": {BODY: "day purpose carries none", "attachments": "not read (id, all_day, end, teams, private, title)",
                                  "email": "not read", "registered": "not read", "organiser_email": "not read"},
}


def norm(x, drop):
    if isinstance(x, dict):
        if x.get("private") is True or x.get("sensitivity") in ("private", "confidential"):      # head fields only (the gateway's rule)
            drop = drop | {"where", "teams", "organiser"}
        return {k: norm(v, drop) for k, v in x.items() if k not in drop and v != [] and not (k == "sensitivity" and v == "private")}
    if isinstance(x, list):
        return [norm(v, drop) for v in x]
    return x


def build_vault(test=None):
    v = Vault()
    if test:
        test.addCleanup(v.cleanup)
    cal = v.root / "system/staging/calendar.json"
    cal.parent.mkdir(parents=True, exist_ok=True)
    cal.write_text(json.dumps({"fetched": "2026-10-26 08:00", "to": "2026-10-30", "days": ROWS}), encoding="utf-8")
    (v.root / "projects/_portfolio/project-register.md").write_text(REGISTER, encoding="utf-8")
    return v


def run_all(v):
    out = {}
    for name, code in READERS.items():
        r = subprocess.run([sys.executable, "-c", SETUP + code + "\nprint(json.dumps(out, sort_keys=True, default=str))"], cwd=v.root,
                           capture_output=True, text=True, env={**os.environ, "CREAITE_NO_LAUNCH": "1", "CREAITE_NOW": "2026-10-26T09:00:00"})
        if r.returncode != 0:
            raise AssertionError(f"{name}: {r.stderr[-500:]}")
        out[name] = json.loads(r.stdout.strip().splitlines()[-1])
    return out


class Golden(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = build_vault()
        cls.new = run_all(cls.v)
        cls.old = json.loads(GOLDEN.read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def same(self, name):
        drop = set(ALLOWED.get(name, {}))
        self.maxDiff = None
        self.assertEqual(norm(self.new[name], drop), norm(self.old[name], drop), f"{name}: output differs from 2.6.8")

    def test_the_golden_covers_every_reader(self):
        self.assertEqual(set(self.old), set(READERS))

    def test_the_fixture_is_not_trivially_empty(self):
        self.assertTrue(self.old["drafts.followup_facts"]["r1"])
        self.assertEqual(self.old["build_dashboard.prep_match_ev"]["r1"][0], "ABC")        # the domain match the fixture is built to prove
        self.assertTrue(self.old["build_dashboard.inbox_meetings"]["rows"])


def _add(name):
    def t(self):
        self.same(name)
    t.__name__ = "test_" + name.replace(".", "_").replace("__", "_")
    return t


for _n in READERS:
    setattr(Golden, "test_same_" + _n.replace(".", "_").replace("__", "_"), _add(_n))


class Intended(unittest.TestCase):
    """The differences that are allowed are the intended ones, and nothing else crept in."""

    @classmethod
    def setUpClass(cls):
        cls.v = build_vault()
        cls.new = run_all(cls.v)

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def test_the_followup_keeps_the_attendees_addresses(self):
        got = self.new["drafts.followup_facts"]["r1"]
        self.assertIn({"name": "Sam Lee", "email": "sam@harbourco.example"}, got)

    def test_the_domain_match_survives(self):
        self.assertEqual(self.new["build_dashboard.prep_match_ev"]["r1"][0], "ABC")
        rows = {r["id"]: r for r in self.new["build_dashboard.inbox_meetings"]["rows"]}
        self.assertEqual(rows["r1"]["p"], "ABC")

    def test_a_private_or_confidential_event_gives_no_attendee_or_address(self):
        out = json.dumps([self.new["drafts.calendar_event"][i] for i in ("rP", "rC")] + [self.new["drafts.followup_facts"][i] for i in ("rP", "rC")])
        self.assertNotIn("@", out)
        self.assertNotIn("attendees", out)

    def test_the_day_views_carry_no_address(self):
        for name in ("build_dashboard.calendar", "transcripts.calendar_rows", "close_day.Lookup.meeting", "drafts._meeting_attendees"):
            self.assertNotIn("@", json.dumps(self.new[name]), name)

    def test_the_bodies_are_filtered(self):
        for name in ("build_dashboard.saved_calendar_days", "drafts.calendar_event", "prep_page._event"):
            blob = json.dumps(self.new[name])
            self.assertNotIn("swordfish99", blob, name)
            self.assertNotIn("abc123def456", blob, name)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--generate":
        vv = build_vault()
        try:
            Path(sys.argv[2]).write_text(json.dumps(run_all(vv), indent=1, sort_keys=True), encoding="utf-8")
        finally:
            vv.cleanup()
    else:
        unittest.main()
