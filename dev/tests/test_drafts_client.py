"""BL-225: draft client wording, in the peek and as Draft all on the project page.

Run: python3 dev/tests/test_drafts_client.py
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
from test_drafts_update import DraftCase  # noqa: E402


def make_client_visible(v, *ids):
    """Fixture only: client-visible items whose client messaging is still to write (the case the project page's card counts)."""
    con = sqlite3.connect(v.root / "system/tracker.db")
    try:
        for i in ids:
            table = "decisions" if "-D-" in i else "actions" if "-A-" in i else "raid"
            con.execute(f"UPDATE {table} SET client_visible = 1 WHERE id = ?", (i,))
        con.commit()
    finally:
        con.close()


class Client(DraftCase):
    @classmethod
    def load(cls, v):
        super().load(v)
        v.propose("conf", [{"n": 1, "op": "new", "table": "actions", "match": "strong", "flags": [], "decision": "approved",
                            "values": {"project": "ABC", "description": "Confidential: restructuring of the client team",
                                       "owner": "Alan Carter", "raised": "2026-10-01", "source": "Alan (cx-edit)"}}])
        v.run("apply")
        make_client_visible(v, "ABC-A-001", "ABC-003")

    def test_the_prompt_holds_only_the_items_own_text_and_the_check_flags_what_is_not_in_it(self):
        reply, events = self.draft({"kind": "client", "id": "ABC-A-001"})
        self.assertIsNone(reply, reply)
        p = drafts_fake.prompt(self.fake)
        self.assertIn("Escalate data access to the client CIO", p)
        for other in ("Jane Doe agreed", "Book UAT environment", "Test licences", "Example Programme", "minutes", "Steering"):
            self.assertNotIn(other, p.split("--- THE ITEM'S OWN TEXT ---")[1])
        d = next(e for e in events if e["type"] == "draft")
        self.assertTrue(d["text"].startswith("What it is: "))
        self.assertNotIn("REMOVED", d["text"])
        self.assertEqual(d["removed"], ["the name Jane Doe", "an internal code"])
        notes = " ".join(n["note"] for n in d["notes"])
        self.assertIn("14", notes)
        self.assertIn("Tom", notes)

    def test_a_confidential_item_is_refused(self):
        con = sqlite3.connect(self.v.root / "system/tracker.db")
        conf = con.execute("SELECT id FROM actions WHERE description LIKE 'Confidential%'").fetchone()[0]
        con.close()
        reply, _ = self.draft({"kind": "client", "id": conf})
        self.assertFalse(reply["ok"])
        self.assertIn("confidential", reply["message"])

    def test_draft_all_stages_proposals_none_of_them_approved_in_bulk(self):
        reply, events = self.draft({"kind": "client-bulk", "code": "ABC"})
        d = next(e for e in events if e["type"] == "draft")
        self.assertEqual(d["staged"], 2)
        (f,) = self.staged()
        data = json.loads(f.read_text())
        self.assertEqual(sorted(i["id"] for i in data["items"]), ["ABC-003", "ABC-A-001"])
        for it in data["items"]:
            self.assertEqual(list(it["changes"]), ["client_message"])
            self.assertEqual((it["decision"], it["drafted"]), ("pending", "client"))
        rows = self.b.eval("(async()=>{ await reloadData(); return REV.filter(r=>r.drafted).map(r=>[r.why,rvBulkOK(r)]); })()")
        self.assertEqual(rows, [["Client wording", False], ["Client wording", False]])
        con = sqlite3.connect(self.v.root / "system/tracker.db")
        self.assertEqual(con.execute("SELECT client_message FROM actions WHERE id='ABC-A-001'").fetchone()[0].count(": \n"), 2)  # unchanged
        con.close()
        f.unlink()

    def test_in_the_peek_the_card_lists_what_was_taken_out_and_use_fills_the_field(self):
        b = self.b
        b.eval("openRecord('actions','ABC-A-001')")
        b.wait("document.querySelector('#pkDet:not([hidden]) [data-draft=client]')")
        b.click("#pkDet [data-draft=client]")
        b.wait("document.querySelector('#pkAiDraftD .drcard')", 30)
        card = b.eval("document.querySelector('#pkAiDraftD .drcard').innerText")
        self.assertIn("Taken out: the name Jane Doe; an internal code", card)
        self.assertIn("Check before you use it", card)
        self.assertEqual(b.eval("PKS.length"), 0)
        b.click("#pkAiDraftD [data-drdo=use]")
        b.wait("(document.querySelector('#pkDet [data-pkf=cm]')||{}).textContent?.startsWith('What it is: Access')")
        self.assertEqual(b.eval("PKS.length"), 0)
        self.assertEqual(b.errors, [])

    def test_the_project_page_card_offers_draft_all(self):
        b = self.b
        b.eval("go('cockpit','ABC')")
        b.wait("document.querySelector('#v-cockpit [data-drcmall=ABC]')")


if __name__ == "__main__":
    unittest.main()
