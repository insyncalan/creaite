"""#328 (Team Cap's review, LOW to MEDIUM): behavioural test of build_dashboard.inbox_meetings, the rows Intake lists from the saved
calendar. A confidential meeting (the word in any case, the flag alone, or an odd value) is read through the sweep's fail-closed
invite_clean.sensitivity and keeps its title and times only: it carries confidential True, none of the matcher's extras
(level, reason, cands, offer), and nothing from its invite (attendees, domains, body). A normal meeting with the same title is
matched as before (p and how), so the test shows that the confidential reading is what changes the row.

Run: python3 dev/tests/test_inbox_confidential_row.py   (no browser, no model; the rows are built in a temp vault)
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_dashboard import populate  # noqa: E402
from test_tracker import Vault  # noqa: E402

DAY = "2026-10-21"
EXTRAS = ("level", "reason", "cands", "offer")                       # what a matched row's answer could add; a confidential row has none
INVITE = {"attendees": [{"name": "Sara Khan", "email": "sara@client.com"}, {"name": "Omar Ali", "email": "omar@client.com"}],
          "body": "Agenda: ABC go-live and the data access plan"}
TITLE = "[ABC] Weekly sync"


def event(eid, start, **more):
    return {"id": eid, "start": start, "end": start[:2] + ":45", "title": TITLE, "where": "Teams", "teams": True, "all_day": False,
            "private": False, "organiser": False, "sensitivity": "normal", **INVITE, **more}


CALENDAR = {"fetched": DAY + " 07:00", "days": {DAY: [
    event("n1", "09:00"),
    event("c1", "10:00", sensitivity="Confidential"),
    event("c2", "11:00", sensitivity="confidential"),
    event("c3", "12:00", confidential=True),                          # the flag alone, with the sensitivity normal
    event("c4", "13:00", sensitivity="secret-ish")]}}                 # an odd value fails closed


class InboxConfidentialRow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        populate(cls.v)                                               # ABC, with its register signals and client domain
        (cls.v.root / "system/staging/calendar.json").write_text(json.dumps(CALENDAR), encoding="utf-8")
        code = ("import json, sys\nfrom datetime import date\nimport build_dashboard as bd\n"
                "today = date(2026, 10, 21)\nprojects = [{'code': 'ABC', 'name': 'Example Programme'}]\n"
                "print(json.dumps(bd.inbox_meetings(bd.paths.load_settings(), projects, today)))")
        r = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, 'system/scripts')\n" + code], cwd=cls.v.root,
                           capture_output=True, text=True, check=True)
        cls.out = json.loads(r.stdout)
        cls.rows = {m["id"]: m for m in cls.out["rows"]}

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def test_all_five_meetings_are_listed(self):
        self.assertEqual(sorted(self.rows), ["c1", "c2", "c3", "c4", "n1"])

    def test_a_normal_meeting_is_matched_and_not_confidential(self):
        n = self.rows["n1"]
        self.assertEqual((n["p"], n["how"], n.get("confidential"), n["private"]), ("ABC", "matched", False, False))

    def test_each_confidential_spelling_is_a_confidential_row(self):
        for eid in ("c1", "c2", "c3", "c4"):
            with self.subTest(eid):
                c = self.rows[eid]
                self.assertTrue(c.get("confidential"))
                self.assertFalse(c["private"])
                self.assertEqual((c["title"], c["day"]), (TITLE, DAY))          # the title and times stay
                self.assertTrue(c["start"] and c["end"])

    def test_a_confidential_row_has_none_of_the_matchers_extras(self):
        for eid in ("c1", "c2", "c3", "c4"):
            with self.subTest(eid):
                self.assertEqual([k for k in EXTRAS if k in self.rows[eid]], [])

    def test_a_confidential_row_carries_nothing_from_its_invite(self):
        for eid in ("c1", "c2", "c3", "c4"):
            with self.subTest(eid):
                text = json.dumps(self.rows[eid])
                for secret in ("Sara", "Omar", "client.com", "data access", "attendees", "body"):
                    self.assertNotIn(secret, text)

    def test_the_same_title_differs_only_by_the_confidential_reading(self):
        """The normal row is matched; so the confidential flag, not the title, is what the page's hiding rests on."""
        n, c = self.rows["n1"], self.rows["c1"]
        self.assertEqual(n["title"], c["title"])
        self.assertTrue(n["p"] and not n["confidential"])
        self.assertTrue(c.get("confidential"))


if __name__ == "__main__":
    unittest.main(verbosity=1)
