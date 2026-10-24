"""BL-205: one ⌘K that does things, and shows the change first.

Run: python3 dev/tests/test_cmdk_change.py   (needs Google Chrome; skipped otherwise)
A throwaway vault (test_dashboard.populate: ABC slipping, DEF on track) and the real live server. Each verb's fixture phrase is read
into the right change; the preview shows before and after and what else it touches; two matching items or people ask; Esc stages
nothing; Enter stages one proposal (the peek's staging: never applied on the spot) with Undo; text that isn't a change still jumps or
searches; nothing deletes.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402


class CmdKChange(LiveBrowserCase):
    shared_server = False

    @classmethod
    def load(cls, v):
        populate(v)
        cfg = v.root / "system/config/settings.json"
        s = json.loads(cfg.read_text())
        s.setdefault("people", {"added": [], "hidden": []})["added"] = ["Sara Khan", "Omar Khan"]
        cfg.write_text(json.dumps(s, indent=2))
        v.run(script="build_dashboard.py")

    def staged(self):
        return sorted(p.name for p in (self.v.root / "system/staging").glob("proposed-*-dashboard.json"))

    def parse(self, q):
        return self.b.eval(f"(()=>{{ CKPICK={{}}; const c=ckParse({json.dumps(q)}); return c&&JSON.parse(JSON.stringify(c)); }})()")

    def palette(self, q):
        b = self.b
        b.eval("openCk()")
        b.wait("document.getElementById('cmdk').open")
        b.eval(f"(()=>{{ const i=document.getElementById('cmdkIn'); i.value={json.dumps(q)}; i.dispatchEvent(new Event('input')); }})()")
        b.pump(0.2)

    def test_each_verb_reads_its_phrase_into_the_right_change(self):
        b = self.b
        fri = b.eval("parseWhen('fri',TODAY,true)")
        c = self.parse("move ABC-A-002 to fri")
        self.assertEqual((c["verb"], c["k"], c["id"], c["patch"]), ("date", "actions", "ABC-A-002", {"due": fri}))
        c = self.parse("mark book UAT environment done")
        self.assertEqual((c["verb"], c["id"], c["patch"]), ("done", "ABC-A-002", {"st": "Closed"}))
        c = self.parse("Omar owns the UAT environment action")
        self.assertEqual((c["verb"], c["id"], c["patch"]), ("owner", "ABC-A-002", {"o": "Omar Ali"}))
        self.assertEqual(self.parse("make ABC-A-002 urgent")["patch"], {"pr": "Urgent"})
        self.assertEqual(self.parse("set ABC-A-002 status delayed")["patch"], {"st": "Delayed"})
        c = self.parse("add action for ABC: send the SOW, Sara Example, fri")
        self.assertEqual((c["verb"], c["k"], c["new"]["p"], c["new"]["t"], c["new"]["o"], c["new"]["due"]),
                         ("add", "actions", "ABC", "Send the SOW", "Sara Example", fri))
        self.assertEqual(self.parse("add risk for ABC: vendor exits the market")["new"]["type"], "Risk")
        self.assertEqual(self.parse("add decision for Example Programme: approve the budget")["k"], "decisions")
        base = b.eval("ckMs('ABC-M-001').due")
        c = self.parse("move uat start +2w")
        self.assertEqual((c["k"], c["id"], c["patch"]["fc"]), ("milestones", "ABC-M-001", b.eval(f"pkAdd('{base}',14)")))

    def test_the_preview_shows_before_and_after_and_what_else_it_touches(self):
        b = self.b
        self.palette("move uat start +2w")
        b.wait("!document.getElementById('ckPrev').hidden")
        self.assertEqual(b.eval("CK[0].g"), "Change")                       # a clearly read change comes first
        pv = b.eval("document.getElementById('ckPrev').innerText")
        self.assertIn("ABC-M-001 · UAT start", pv)
        self.assertIn("− ", pv)
        self.assertIn("+ ", pv)
        self.assertIn("open items tied to it", pv)
        self.assertIn("Slip against its baseline", pv)
        self.assertIn("Esc nothing changes", pv.replace("\n", " "))
        self.palette("make ABC-A-001 low")
        b.wait("/Urgent/.test(document.getElementById('ckPrev').innerText)")
        self.assertIn("Tied to the milestone UAT start", b.eval("document.getElementById('ckPrev').innerText"))

    def test_two_matching_people_or_items_ask_never_guess(self):
        b = self.b
        self.palette("Khan owns ABC-A-001")
        b.wait("CK[0] && CK[0].g==='Change · which one?'")
        self.assertEqual(sorted(b.eval("CK.filter(x=>x.g==='Change · which one?').map(x=>x.l)")), ["Omar Khan", "Sara Khan"])
        b.key("Enter")                                                        # picks the first
        b.wait("CK[0] && CK[0].g==='Change'")
        self.assertIn("Owner:", b.eval("CK[0].l"))
        self.assertTrue(b.eval("document.getElementById('cmdk').open"))       # still open: Enter again stages
        self.palette("mark UAT done")
        b.wait("CK[0] && CK[0].g==='Change · which one?'")
        self.assertGreaterEqual(b.eval("CK.filter(x=>x.g==='Change · which one?').length"), 2)

    def test_esc_stages_nothing_and_enter_stages_one_proposal_with_undo(self):
        b = self.b
        before = self.staged()
        # a week after the date it has, never "fri": ABC-A-002 is due in three days (populate), so on a Tuesday "fri" was the
        # date it already had, nothing changed and nothing was staged
        to = b.eval("(d=>`${d.slice(8,10)}-${d.slice(5,7)}-${d.slice(0,4)}`)(pkAdd(REC('actions','ABC-A-002').due,7))")
        self.palette(f"move ABC-A-002 to {to}")
        b.key("Escape")
        b.wait("!document.getElementById('cmdk').open")
        self.assertEqual(self.staged(), before)
        self.palette(f"move ABC-A-002 to {to}")
        b.eval("document.getElementById('snackT').textContent=''")
        b.key("Enter")
        b.wait("/Saved: /.test(document.getElementById('snackT').textContent)", 15)
        new = [n for n in self.staged() if n not in before]
        self.assertEqual(len(new), 1)
        data = json.loads((self.v.root / "system/staging" / new[0]).read_text())
        self.assertEqual([(i["op"], i["table"], i["id"], i["decision"]) for i in data["items"]], [("update", "actions", "ABC-A-002", "approved")])
        self.assertIn("due_date", data["items"][0]["changes"])
        self.assertNotEqual(next(a for a in self.v.rows("actions") if a["id"] == "ABC-A-002")["due_date"],
                            data["items"][0]["changes"]["due_date"])            # staged, not applied
        self.assertTrue(b.eval("!document.getElementById('pkStage').hidden"))  # the peek's pill: Undo last and Apply
        b.click("#snack button")                                              # Undo in the message
        b.wait(f"true", 1)
        for _ in range(50):
            if not [n for n in self.staged() if n not in before]:
                break
            b.pump(0.1)
        self.assertEqual(self.staged(), before)

    def test_cmd_enter_stages_and_opens_intake(self):
        b = self.b
        self.palette("add action for ABC: send the SOW, Sara Example")
        b.key("Enter", 4)
        b.wait("VIEW==='intake-review'", 15)
        self.assertEqual(len(self.staged()), 1)

    def test_text_that_is_not_a_change_still_jumps_and_searches_and_nothing_deletes(self):
        b = self.b
        self.assertIsNone(self.parse("Book UAT"))
        self.assertIsNone(self.parse("items due friday"))
        self.assertIsNone(self.parse("delete ABC-A-001"))
        self.palette("Book UAT")
        b.wait("CK.some(x=>x.g==='Items')")
        self.assertFalse(b.eval("CK.some(x=>x.g.startsWith('Change'))"))
        self.assertTrue(b.eval("document.getElementById('ckPrev').hidden"))
        self.palette("change the plan for ABC somehow")
        b.wait("CK[0] && CK[0].g==='Change'")
        self.assertIn("Give it to ask creaite", b.eval("CK[0].l"))
        self.assertEqual(b.errors, [])


if __name__ == "__main__":
    unittest.main()
