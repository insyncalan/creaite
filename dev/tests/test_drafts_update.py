"""BL-219: draft the latest update, for one action in the peek and for several at once (Work's bar, Today's stale line).

Run: python3 dev/tests/test_drafts_update.py
The real live server in a throwaway vault; Claude is a stand-in (drafts_fake.py) with a fixed reply, so no model is called.
"""
import json
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import drafts_fake  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402


class DraftCase(LiveBrowserCase):
    """A server with the stand-in Claude and the evidence fixture."""

    @classmethod
    def load(cls, v):
        drafts_fake.load(v)
        cls.fake = drafts_fake.install(v)

    @classmethod
    def server_env(cls):
        return {"CREAITE_CLAUDE": str(cls.fake)}

    def draft(self, body):
        """POST /api/draft from the page and read its stream: (JSON reply or None, the events)."""
        got = self.b.eval("""(async()=>{ const r=await fetch('/api/draft',{method:'POST',headers:{'Content-Type':'application/json','X-Creaite-Token':D.token},
            body:JSON.stringify(%s)}); const t=await r.text(); return {json:(r.headers.get('Content-Type')||'').includes('json'),t}; })()""" % json.dumps(body))
        if got["json"]:
            return json.loads(got["t"]), []
        events = [json.loads(ln[6:]) for ln in got["t"].splitlines() if ln.startswith("data: ")]
        run = next((e.get("run") for e in events if e.get("type") == "done"), None)
        if run:
            self.b.eval(f"api('/api/ask/ack',{{run:{json.dumps(run)}}})")
        return None, events

    def stats(self):
        p = self.v.root / "system/staging/draft-stats.json"
        return json.loads(p.read_text()) if p.exists() else {}

    def row(self, item_id):
        con = sqlite3.connect(self.v.root / "system/tracker.db")
        con.row_factory = sqlite3.Row
        try:
            return dict(con.execute("SELECT * FROM actions WHERE id = ?", (item_id,)).fetchone())
        finally:
            con.close()

    def staged(self):
        return sorted((self.v.root / "system/staging").glob("proposed-*-drafts.json"))


class OneItem(DraftCase):
    def test_an_item_with_evidence_drafts_a_sourced_line_and_marks_the_unsourced_one(self):
        before = self.row("ABC-A-001")
        reply, events = self.draft({"kind": "update", "id": "ABC-A-001"})
        self.assertIsNone(reply, reply)
        src = next(e for e in events if e["type"] == "sources")["sources"]
        texts = " | ".join(s["text"] for s in src)
        self.assertIn("raised again", texts)
        self.assertIn("Jane Doe agreed to raise data access", texts)
        d = next(e for e in events if e["type"] == "draft")
        self.assertTrue(d["ok"])
        self.assertEqual(d["sentences"][0]["refs"], ["S1"])
        self.assertFalse(d["sentences"][0]["unsourced"])
        self.assertTrue(d["sentences"][1]["unsourced"])
        self.assertEqual(d["unsourced"], 1)
        self.assertNotIn("[S1]", d["text"])
        self.assertEqual(self.row("ABC-A-001"), before)                    # nothing written
        self.assertEqual(self.stats()["update"]["offered"], 1)

    def test_a_confidential_source_is_never_read(self):
        self.draft({"kind": "update", "id": "ABC-A-001"})
        p = drafts_fake.prompt(self.fake)
        self.assertIn("Jane Doe agreed", p)
        self.assertNotIn("board secret", p)

    def test_no_evidence_drafts_nothing_and_asks_no_model(self):
        Path(str(self.fake) + ".prompt").unlink(missing_ok=True)
        reply, _ = self.draft({"kind": "update", "id": "ABC-A-002"})
        self.assertTrue(reply["ok"])
        self.assertTrue(reply["nothing"].startswith("Nothing new since 01-10-2026"), reply)
        self.assertEqual(drafts_fake.prompt(self.fake), "")

    def test_a_raid_item_or_a_closed_action_is_refused(self):
        reply, _ = self.draft({"kind": "update", "id": "ABC-003"})
        self.assertFalse(reply["ok"])
        self.assertIn("for actions", reply["message"])

    def test_switched_off_it_says_so(self):
        cfg = self.v.root / "system/config/settings.json"
        keep = cfg.read_text()
        data = json.loads(keep)
        data["drafting"] = {"update": False}
        cfg.write_text(json.dumps(data))
        try:
            reply, _ = self.draft({"kind": "update", "id": "ABC-A-001"})
            self.assertFalse(reply["ok"])
            self.assertTrue(reply["off"])
            self.assertIn("turned off", reply["message"])
        finally:
            cfg.write_text(keep)


class Several(DraftCase):
    def test_the_bulk_path_stages_pending_proposals_and_saves_nothing_in_place(self):
        before = [self.row(i) for i in ("ABC-A-001", "ABC-A-002")]
        reply, events = self.draft({"kind": "update-bulk", "ids": ["ABC-A-001", "ABC-A-002"]})
        d = next(e for e in events if e["type"] == "draft")
        self.assertEqual(d["staged"], 1)
        self.assertTrue(any("ABC-A-002" in s and "nothing new" in s for s in d["skipped"]))
        files = self.staged()
        self.assertEqual(len(files), 1)
        data = json.loads(files[0].read_text())
        self.assertEqual(data["source_run"], "drafts")
        (it,) = data["items"]
        self.assertEqual((it["op"], it["table"], it["id"], it["decision"]), ("update", "actions", "ABC-A-001", "pending"))
        self.assertEqual(list(it["changes"]), ["latest_update"])
        self.assertEqual(it["changes"]["latest_update"], "Raised again at the weekly sync.")
        self.assertEqual(it["based_on"], before[0]["updated_at"])
        self.assertEqual((it["drafted"], it["drafted_text"]), ("update", "Raised again at the weekly sync."))
        self.assertTrue(it["why"].startswith("Drafted from"))
        self.assertEqual([self.row(i) for i in ("ABC-A-001", "ABC-A-002")], before)
        r = self.b.eval("(async()=>{ await reloadData(); return REV.filter(r=>r.drafted).map(r=>({n:r.n,indiv:r.indiv,why:r.why,src:r.draft_src.length})); })()")
        self.assertEqual(len(r), 1)
        self.assertTrue(r[0]["indiv"])
        self.assertEqual(r[0]["why"], "Drafted update")
        # approving it in Review counts it as used; it is not covered by Approve routine
        self.assertFalse(self.b.eval(f"rvBulkOK(REV.find(r=>r.n==={r[0]['n']}))"))
        files[0].unlink()


class InThePage(DraftCase):
    def open_item(self, item_id):
        b = self.b
        b.eval(f"openRecord('actions','{item_id}')")
        b.wait("document.querySelector('#pkDescDr [data-draft=update]')")

    def test_draft_shows_a_card_and_use_puts_it_in_the_field_unsaved_until_leaving(self):
        b = self.b
        self.open_item("ABC-A-001")
        self.assertEqual(b.eval("document.querySelector('#pkDescDr [data-draft]').textContent"), "Draft")
        b.click("#pkDescDr [data-draft=update]")
        b.wait("document.querySelector('#pkAiDraft .drcard')", 30)
        card = b.eval("document.querySelector('#pkAiDraft .drcard').innerText")
        self.assertIn("Jane Doe agreed", card)
        self.assertIn("no source", card)
        self.assertIn("Drafted from", card)
        self.assertEqual(b.eval("document.getElementById('pkDesc').textContent"), "")
        self.assertEqual(b.eval("PKS.length"), 0)
        b.click("#pkAiDraft [data-drdo=use]")
        b.wait("document.getElementById('pkDesc').textContent.includes('Jane Doe agreed')")
        self.assertEqual(b.eval("PKS.length"), 0)                               # in the field, not staged
        self.assertTrue(b.eval("document.activeElement.id==='pkDesc'"))
        b.eval("document.getElementById('pkDesc').blur()")
        b.wait("PKS.length===1", 15)
        self.assertEqual(b.eval("PKS[0].patch.upd"), "Jane Doe agreed to raise data access with the CIO. Escalation is on track.")
        for _ in range(100):
            if self.stats().get("update", {}).get("used"):
                break
            b.pump(0.05)
        self.assertEqual(self.stats()["update"]["used"], 1)
        b.eval("pkUndoLast()")
        b.wait("PKS.length===0")
        self.assertEqual(b.errors, [])

    def test_discard_drops_the_draft_and_counts_it(self):
        b = self.b
        self.open_item("ABC-A-001")
        b.click("#pkDescDr [data-draft=update]")
        b.wait("document.querySelector('#pkAiDraft .drcard')", 30)
        b.click("#pkAiDraft [data-drdo=discard]")
        b.wait("!document.querySelector('#pkAiDraft .drcard')")
        for _ in range(100):
            if self.stats().get("update", {}).get("rejected"):
                break
            b.pump(0.05)
        self.assertGreaterEqual(self.stats()["update"]["rejected"], 1)
        self.assertEqual(b.eval("PKS.length"), 0)

    def test_nothing_new_is_said_in_place(self):
        b = self.b
        self.open_item("ABC-A-002")
        b.click("#pkDescDr [data-draft=update]")
        b.wait("document.querySelector('#pkAiDraft .drnone')", 30)
        self.assertIn("Nothing new since", b.eval("document.querySelector('#pkAiDraft .drnone').textContent"))

    def test_the_bar_offers_draft_updates_and_today_has_no_stale_line(self):      # #352: Today's stale-updates line is gone; the Work bar keeps the draft
        b = self.b
        b.wait("PULSE.reloads===0 && !PULSE.busy && !EVS.timer", 30)       # BL-327: the page's own data reload would redraw the bar away
        b.eval("go('work'); WT='actions'; renderWork()")
        b.wait("document.querySelector('#workTbl tr[data-row]')")
        b.eval("HL.clear(); ['ABC-A-001','ABC-A-002'].forEach(i=>HL.set(i,'actions')); hlPaint(); hlBar()")
        b.wait("document.querySelector('#wbulk [data-drbulk]')")
        self.assertIn("Draft updates", b.eval("document.querySelector('#wbulk [data-drbulk]').textContent"))
        b.click("#wbulk [data-drbulk]")
        b.wait("REV.some(r=>r.drafted)", 30)
        b.wait("document.getElementById('snackT').textContent.includes('in Intake')", 30)
        self.assertIn("in Intake", b.eval("document.getElementById('snackT').textContent"))
        b.eval("HL.clear(); hlPaint(); hlBar(); A.forEach(x=>x.upd_at='2026-01-01'); go('today'); renderToday()")
        b.wait("document.querySelector('#v-today')")
        b.pump(0.8)
        self.assertFalse(b.eval("!!document.getElementById('drStale') || /had no update for/.test(document.getElementById('v-today').textContent)"))     # #352
        b.eval("go('intake-review')")                                              # #232 C2: the drafted rows carry their tag on the Intake page
        b.wait("document.querySelector('#v-intake-review tr.irprop .drrv')")
        for f in self.staged():
            f.unlink()


if __name__ == "__main__":
    unittest.main()
