"""BL-222: suggest the thinking fields: a decision's reasoning and options considered, a risk's response with impact and likelihood,
and "Draft a response" for a new risk in Review.

Run: python3 dev/tests/test_drafts_thinking.py
The real live server in a throwaway vault; Claude is a stand-in (drafts_fake.py), so no model is called.
"""
import json
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import drafts_fake  # noqa: E402
from test_dashboard import d  # noqa: E402
from test_drafts_update import DraftCase  # noqa: E402

ABC = drafts_fake.ABC
NOTES = f"{ABC}/minutes/{d(-2)} Steering notes.md"


def item(n, table, **values):
    return {"n": n, "op": "new", "table": table, "values": values, "match": "strong", "flags": [], "decision": "approved"}


class Thinking(DraftCase):
    @classmethod
    def load(cls, v):
        super().load(v)
        (v.root / NOTES).write_text(
            "# Steering notes\n\nGo-live: we discussed whether go-live moves two weeks. Options were to keep the date and test on masked "
            "data, or to move go-live.\nData access is late, so the group agreed that go-live moves two weeks.\n\n"
            "Vendor: the vendor may exit the market next year; we need a second supplier lined up.\n")
        (v.root / f"{ABC}/minutes/{d(-2)} Confidential board.md").write_text("Board: the pricing secret for the merger.\n")
        v.propose("think", [
            item(1, "decisions", project="ABC", decision="Go-live moves two weeks after the steering", made_by="Jane Doe", date=d(-2),
                 source=f"{NOTES} — Decisions"),
            item(2, "raid", project="ABC", type="Risk", description="Vendor may exit the market next year", impact="Medium",
                 likelihood="Low", raised=d(-2), source=f"{NOTES} — Risks"),
            item(3, "raid", project="DEF", type="Risk", description="Supplier may exit the market", impact="High", likelihood="Low",
                 raised="2026-09-01", status="Closed", closed="2026-09-20", response_action="Lined up a second supplier with a short contract",
                 source="Alan (cx-edit)"),
            item(4, "decisions", project="ABC", decision="Pricing for the merger", made_by="Jane Doe", date=d(-2),
                 source=f"{ABC}/minutes/{d(-2)} Confidential board.md — Decisions"),
        ])
        v.run("apply")

    def ids(self):
        con = sqlite3.connect(self.v.root / "system/tracker.db")
        try:
            dec = con.execute("SELECT id FROM decisions WHERE decision LIKE 'Go-live moves two weeks after%'").fetchone()[0]
            risk = con.execute("SELECT id FROM raid WHERE description LIKE 'Vendor may exit%'").fetchone()[0]
            conf = con.execute("SELECT id FROM decisions WHERE decision = 'Pricing for the merger'").fetchone()[0]
            snap = con.execute("SELECT reasoning, options FROM decisions WHERE id = ?", (dec,)).fetchone()
            return dec, risk, conf, snap
        finally:
            con.close()

    def test_a_meeting_passage_gives_the_reasoning_and_the_options_with_sources(self):
        dec, _, _, before = self.ids()
        reply, events = self.draft({"kind": "thinking", "id": dec, "field": "reasoning"})
        self.assertIsNone(reply, reply)
        src = next(e for e in events if e["type"] == "sources")["sources"]
        self.assertTrue(any("group agreed that go-live moves" in s["text"] for s in src), src)
        p = drafts_fake.prompt(self.fake)
        self.assertTrue(p.startswith("Suggest the reasoning given"))
        self.assertIn("Never say who made the decision or when", p)
        dr = next(e for e in events if e["type"] == "draft")
        self.assertEqual(dr["text"], "Data access is late, so testing cannot finish in time. Nobody objected.")
        self.assertEqual(dr["unsourced"], 1)
        _, events = self.draft({"kind": "thinking", "id": dec, "field": "options"})
        dr = next(e for e in events if e["type"] == "draft")
        self.assertIn("Keep the date and test on masked data.", dr["text"])
        self.assertEqual(self.ids()[3], before)                                        # nothing saved

    def test_a_risk_draws_on_a_closed_risks_response_and_judges_impact_and_likelihood(self):
        _, risk, _, _ = self.ids()
        _, events = self.draft({"kind": "thinking", "id": risk, "field": "response_action"})
        src = next(e for e in events if e["type"] == "sources")["sources"]
        self.assertTrue(any("Lined up a second supplier" in s["text"] for s in src), src)
        dr = next(e for e in events if e["type"] == "draft")
        self.assertEqual(dr["impact"]["value"], "High")
        self.assertEqual(dr["likelihood"]["value"], "Medium")
        self.assertTrue(dr["text"].startswith("Escalate to the client CIO"))

    def test_a_confidential_source_is_skipped(self):
        _, _, conf, _ = self.ids()
        reply, _ = self.draft({"kind": "thinking", "id": conf, "field": "reasoning"})
        self.assertTrue(reply["ok"])
        self.assertIn("Nothing to suggest from", reply["nothing"])

    def test_made_and_maker_are_never_suggested(self):
        dec, _, _, _ = self.ids()
        reply, _ = self.draft({"kind": "thinking", "id": dec, "field": "made_by"})
        self.assertFalse(reply["ok"])

    def test_in_the_peek_impact_is_one_click_and_use_fills_the_response_unsaved(self):
        _, risk, _, _ = self.ids()
        b = self.b
        b.eval(f"openRecord('raid','{risk}')")
        b.wait("document.querySelector('#pkDescDr [data-draft=thinking][data-drf=resp]')")
        b.click("#pkDescDr [data-draft=thinking]")
        b.wait("document.querySelector('#pkAiDraft .drcard')", 30)
        self.assertIn("Suggested from", b.eval("document.querySelector('#pkAiDraft .drcard').innerText"))
        b.click("#pkAiDraft [data-drset='imp:High']")
        b.wait("PKS.length===1")
        self.assertEqual(b.eval("PKS[0].patch"), {"imp": "High"})
        b.click("#pkAiDraft [data-drdo=use]")
        b.wait("document.getElementById('pkDesc').textContent.startsWith('Escalate to the client CIO')")
        self.assertEqual(b.eval("PKS.length"), 1)                                      # the response isn't staged until the field is left
        b.eval("pkUndoLast()")
        b.wait("PKS.length===0")
        self.assertEqual(b.errors, [])

    def test_review_offers_draft_a_response_for_a_new_risk(self):
        b = self.b
        b.eval("go('review')")
        b.wait("document.querySelector('#reviewBody [data-drrisk]')")
        b.click("#reviewBody [data-drrisk]")
        b.wait("document.querySelector('#pkAiDraft .drcard')", 30)
        self.assertIn("Draft a response", b.eval("document.querySelector('#pkDescDr [data-drf=resp]').textContent"))
        b.click("#pkAiDraft [data-drdo=use]")
        b.wait("CUR&&CUR.mode==='proposal'&&document.getElementById('pkDesc').textContent.startsWith('Escalate')")
        b.eval("document.getElementById('pkDesc').blur()")
        b.wait("CUR.draft.resp&&CUR.draft.resp.startsWith('Escalate')")
        data = [json.loads(p.read_text()) for p in (self.v.root / "system/staging").glob("proposed-pending.json")]
        self.assertTrue(all(not (i.get("values") or {}).get("response_action") for x in data for i in x["items"]))   # held in the peek until Save


if __name__ == "__main__":
    unittest.main()
