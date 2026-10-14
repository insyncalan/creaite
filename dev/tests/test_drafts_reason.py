"""BL-226: draft the reason for a health or forecast change, and the slip range in one sentence.

Run: python3 dev/tests/test_drafts_reason.py
The real live server in a throwaway vault; Claude is a stand-in (drafts_fake.py), so no model is called.
"""
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import drafts_fake  # noqa: E402
from test_dashboard import d  # noqa: E402
from test_drafts_update import DraftCase  # noqa: E402
import test_forecast  # noqa: E402  (its helpers, not its tests)


def shown(iso):
    return f"{iso[8:10]}-{iso[5:7]}-{iso[:4]}"


class SlipRangeSentence(unittest.TestCase):
    """The template's sentence uses forecast.py's own numbers (no model)."""

    def setUp(self):
        self.f = test_forecast.Forecast("ranges")
        self.f.setUp()
        self.addCleanup(self.f.tearDown)

    def test_the_sentence_matches_the_slip_range(self):
        for j in range(8):
            self.f.closed(j, slips=1, remaining=2 * j)              # remaining slips 0, 2, … 14: median 7, P80 11.2
        o = self.f.open_ms(slips=1)
        r = self.f.ranges()[o]
        self.assertTrue(r["ok"])
        self.assertEqual((r["med"], r["p80"]), (7, 11))
        self.assertEqual(r["explain"], f"Based on how 8 closed milestones finished after 1 slip, as this one has (median 7 days late), "
                                       f"likely {shown(r['lo'])} to {shown(r['hi'])} (thin evidence).")

    def test_no_range_means_no_sentence(self):
        o = self.f.open_ms(slips=0)
        r = self.f.ranges()[o]
        self.assertFalse(r["ok"])
        self.assertNotIn("explain", r)


class Reason(DraftCase):
    def health_reason(self):
        con = sqlite3.connect(self.v.root / "system/tracker.db")
        try:
            return con.execute("SELECT health, health_reason FROM projects WHERE code='ABC'").fetchone()
        finally:
            con.close()

    def test_health_the_facts_are_the_evidence_functions_and_use_fills_the_reason_unsaved(self):
        b = self.b
        before = self.health_reason()
        b.eval("go('cockpit','ABC'); openProject('ABC','health')")
        b.wait("document.querySelector('#hDraft [data-drhealth]')")
        facts = b.eval("healthFacts('ABC')")
        ev = b.eval("healthEvidence('ABC').reasons")
        self.assertTrue(ev)
        self.assertEqual([f.lower() for f in facts[:len(ev)]], [e.lower() for e in ev])
        b.eval("document.getElementById('f_health').value='At risk'; document.getElementById('f_health').dispatchEvent(new Event('change'))")
        b.click("#hDraft [data-drhealth]")
        b.wait("document.querySelector('#hDraft .drcard')", 30)
        p = drafts_fake.prompt(self.fake)
        self.assertIn("it is now At risk", p)
        for f in facts:
            self.assertIn(f, p)
        self.assertIn("--- HOUSE VOICE ---", p)
        b.click("#hDraft [data-drdo=use]")
        b.wait("document.getElementById('f_reason').value==='Two actions are overdue and UAT start has slipped.'")
        self.assertEqual(self.health_reason(), before)                    # nothing saved until Save
        self.assertEqual(b.errors, [])

    def test_health_with_no_evidence_asks_no_model(self):
        reply, _ = self.draft({"kind": "health", "code": "DEF", "to": "On track", "facts": []})
        self.assertTrue(reply["ok"])
        self.assertIn("Say why in your own words", reply["nothing"])

    def test_forecast_reason_comes_from_the_overdue_work_behind_the_milestone(self):
        reply, events = self.draft({"kind": "forecast", "id": "ABC-M-001", "fc": d(40)})
        self.assertIsNone(reply, reply)
        src = next(e for e in events if e["type"] == "sources")["sources"]
        self.assertTrue(any("Escalate data access to the client CIO" in s["text"] and "overdue" in s["text"].lower() for s in src), src)
        self.assertIn(f"to {shown(d(40))}", drafts_fake.prompt(self.fake))
        dr = next(e for e in events if e["type"] == "draft")
        self.assertEqual(dr["text"], "The data access escalation is overdue, so UAT start moves.")
        reply, _ = self.draft({"kind": "forecast", "id": "DEF-M-001", "fc": d(60)})
        self.assertIn("Nothing in the tracker explains the move", reply["nothing"])

    def test_forecast_in_the_milestone_editor(self):
        b = self.b
        b.eval("MVAUD='int'; mvOpenPage('ABC','plan')")   # BL-244 made Client the first-visit view; the editor rows are Internal
        b.wait("VIEW==='milestones'&&document.querySelector('#v-milestones .mv-prow[data-mvedit=\"ABC-M-001\"]')")
        b.click('#v-milestones .mv-prow[data-mvedit="ABC-M-001"]')
        b.wait("MV.peek==='ABC-M-001'&&!document.getElementById('mvPeek').hidden")
        b.eval(f"MV.pend={{id:'ABC-M-001',fc:'{d(40)}',why:''}}; mvEdDraw()")
        b.wait("document.querySelector('#mvFcDraft [data-drfc]')")
        b.click("#mvFcDraft [data-drfc]")
        b.wait("document.querySelector('#mvFcDraft .drcard')", 30)
        b.click("#mvFcDraft [data-drdo=use]")
        b.wait("document.getElementById('mvFcWhy').value.startsWith('The data access escalation')")
        self.assertEqual(b.eval("MV.pend.why"), "The data access escalation is overdue, so UAT start moves.")
        con = sqlite3.connect(self.v.root / "system/tracker.db")
        fc = con.execute("SELECT forecast_date FROM milestones WHERE id='ABC-M-001'").fetchone()[0]
        con.close()
        self.assertNotEqual(fc, d(40))                                    # Save forecast is still Alan's
        self.assertEqual(b.errors, [])


if __name__ == "__main__":
    unittest.main()
