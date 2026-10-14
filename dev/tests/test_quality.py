"""BL-233 (sprint-drafts-extraction): Quality, what you approve, edit and reject, read-only. Counts come from fixture proposals and a
fixture draft-stats.json; a group under 10 shows its counts and no rate; an edit from before BL-232 is "field unknown"; nothing in a
report or export reads it; Activity › Quality shows it.

Run: python3 dev/tests/test_quality.py
"""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_tracker import Vault  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
NOW = "2026-10-12 09:00"
MAIL = "Email · From: Jane Doe <jane.doe@client.com> · Subject: x · Sent: 2026-10-05 09:00 · Link: https://outlook.office365.com/x"
TEAMS = "Teams · Chat: ABC · From: Jane Doe · Sent: 2026-10-05 09:00 · Link: https://teams.microsoft.com/l/message/x"


def new(n, table="actions", decision="approved", **extra):
    values = {"project": "ABC", "description": f"Item {n}", "owner": "Sara Example", "source": extra.pop("source", "minutes — Actions")}
    values.update(extra.pop("values", {}))
    return {"n": n, "op": "new", "table": table, "values": values, "match": "strong", "flags": [], "decision": decision, **extra}


def fixtures(root):
    """Applied and pending proposals over the last four weeks, and the AI drafts' counts."""
    applied, staging = root / "system/staging/applied", root / "system/staging"
    minutes = [new(i) for i in range(1, 9)]                                                       # 8 approved as proposed
    minutes += [new(9, as_proposed={"project": "ABC", "description": "Item 9", "owner": "TBC", "source": "s"}),   # owner edited
                new(10, as_proposed={"project": "ABC", "description": "Item ten", "owner": "Sara Example", "source": "s"}),
                new(11, edited_in="review"),                                                   # before BL-232: field unknown
                new(12, decision="rejected", reject_reason="Duplicate"),
                new(13, decision="rejected", reject_reason="Sara's call, not ours"),             # Alan's words: counted as Other
                new(14, "raid", values={"type": "Risk"}), new(15, "decisions", values={"decision": "Go"})]
    (applied / "proposed-2026-10-05-0900.json").write_text(json.dumps({"created": "2026-10-05T09:00:00", "source_run": "cx-minutes",
                                                                       "items": minutes}))
    sweep = [new(1, source=MAIL), new(2, source=MAIL, decision="rejected", reject_reason="Not an action"), new(3, source=TEAMS)]
    (applied / "proposed-2026-10-06-0800-sweep.json").write_text(json.dumps({"created": "2026-10-06T08:00:00", "source_run": "cx-sweep",
                                                                             "items": sweep}))
    (staging / "proposed-2026-10-11-0800-sweep.json").write_text(json.dumps({"created": "2026-10-11T08:00:00", "source_run": "cx-sweep",
                                                                             "items": [new(1, source=MAIL, decision="pending")]}))
    (applied / "proposed-2026-08-01-0900.json").write_text(json.dumps({"created": "2026-08-01T09:00:00", "source_run": "cx-minutes",
                                                                       "items": [new(1)]}))   # outside both periods
    (staging / "draft-stats.json").write_text(json.dumps({"update": {"offered": 12, "used": 7, "edited": 3, "rejected": 2},
                                                          "sharpen": {"offered": 3, "used": 1, "edited": 1, "rejected": 1}}))


class Measure(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.cleanup)
        self.v.run("init")
        fixtures(self.v.root)

    def measure(self):
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts/quality.py"), "--json"], cwd=self.v.root,
                           env={**os.environ, "CREAITE_NOW": NOW}, capture_output=True, text=True, check=True)
        return json.loads(r.stdout)

    def test_counts_by_source_and_type_from_fixture_proposals(self):
        q = self.measure()
        src = {r["key"]: r for r in q["by_source"]}
        self.assertEqual(src["minutes"]["decided"], 15)
        self.assertEqual((src["minutes"]["approved"]["text"], src["minutes"]["edited"]["text"], src["minutes"]["rejected"]["text"]),
                         ("10 of 15 (67%)", "3 of 15 (20%)", "2 of 15 (13%)"))
        self.assertEqual((src["mail"]["decided"], src["mail"]["pending"], src["teams"]["decided"]), (2, 1, 1))
        types = {r["key"]: r["decided"] for r in q["by_type"]}
        self.assertEqual((types["action"], types["risk"], types["decision"]), (16, 1, 1))
        self.assertEqual({r["reason"]: r["n"] for r in q["reasons"]}, {"Duplicate": 1, "Other": 1, "Not an action": 1})
        self.assertNotIn("Sara", json.dumps(q))                                        # never about a person

    def test_a_group_under_ten_shows_its_count_and_no_rate(self):
        q = self.measure()
        mail = next(r for r in q["by_source"] if r["key"] == "mail")
        self.assertFalse(mail["rated"])
        self.assertEqual(mail["approved"]["text"], "1 of 2")                           # the count and its total, no percentage
        drafts = {r["feature"]: r for r in q["drafts"]}
        self.assertEqual(drafts["update"]["used"]["text"], "7 of 12 (58%)")
        self.assertEqual(drafts["sharpen"]["used"]["text"], "1 of 3")
        self.assertFalse(drafts["sharpen"]["rated"])

    def test_edits_show_the_fields_changed_and_pre_bl232_edits_as_field_unknown(self):
        q = self.measure()
        self.assertEqual({r["field"]: r["n"] for r in q["fields"]}, {"Owner": 1, "Title": 1})
        self.assertEqual(q["fields"][0]["of"], 3)
        self.assertEqual(q["unknown"], {"n": 1, "of": 3})

    def test_what_moved_needs_ten_in_both_periods(self):
        self.assertIn("Too few decided proposals to compare yet", self.measure()["moved"])

    def test_it_writes_nothing(self):
        before = self.v.snapshot()
        self.measure()
        self.assertEqual(self.v.snapshot(), before)


class NoReportReadsIt(unittest.TestCase):
    def test_no_report_one_pager_client_output_or_export_reads_it(self):
        for name in ("report.py", "excel_sync.py", "prep_page.py", "status_facts.py", "docx_tools.py"):
            text = (REPO / "system/scripts" / name).read_text(encoding="utf-8")
            self.assertNotIn("import quality", text, name)
            self.assertNotIn('"quality"', text, name)


class Page(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        populate(v)
        fixtures(v.root)
        v.run("rebuild", script="build_dashboard.py", ok=False)

    def test_activity_quality_shows_counts_out_of_totals(self):
        b = self.b
        b.eval("go('activity')")
        b.click("#actTabQ")
        b.wait("document.querySelectorAll('#qSrc tr').length>=2")
        text = b.eval("document.getElementById('actQuality').innerText")
        self.assertIn(" of ", text)
        self.assertIn("Not rated yet: 2 decided, rated from 10", text)
        self.assertIn("Draft the latest update", text)
        self.assertTrue(b.eval("document.getElementById('actTbl').offsetParent===null"))      # the change list is behind its tab
        b.click("#actTabCh")
        self.assertTrue(b.eval("document.getElementById('actQuality').hidden"))
        self.assertEqual(b.errors, [])


if __name__ == "__main__":
    unittest.main()
