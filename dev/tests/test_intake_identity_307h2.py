"""#307 h2 (HIGH2): every Intake action checks the item's CONTENT on the server side of the write, not only its file and number.
The engine renumbers items inside a proposal file (sweep.py) and a file name can be written again, so the page names a row by file,
ref and a content fingerprint, finds the item in the freshly read file by that, and writes with expect_text (/api/fs).

Scenarios (a real vault, a real server, real Chrome): Bravo/Charlie renumbered inside one file; a file deleted and written again under
the same name (Delta/Echo); a write that loses a race; the routine button; Approve many; the peek's Save and approve; a double click.
Run: python3 dev/tests/test_intake_identity_307h2.py   (needs Google Chrome; skipped otherwise)"""
import json
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import intake_review_support as S  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402
from test_tracker import action  # noqa: E402

STALE = "already approved or changed"
MAILX = S.MAIL


def item(n, text, owner="Sara Example"):
    return S.pending({**action(n, description=text, owner=owner, due_date="2026-11-09", source=MAILX), "match": "strong"})


class Identity307(LiveBrowserCase):
    shared_server = False
    width, height = 1400, 1000
    NAME = "2026-10-09-1000-identity"

    @classmethod
    def load(cls, v):
        S.load(v)

    def stage(self, items):
        p = self.v.propose(self.NAME, items)
        d = json.loads(p.read_text())
        d["source_run"] = "cx-sweep"
        p.write_text(json.dumps(d, indent=2))
        return p

    def rewrite(self, items, delete_first=False):
        """What the engine or a new sweep does behind the open page: the same file name, other items or other numbers."""
        p = self.v.root / "system" / "staging" / f"proposed-{self.NAME}.json"
        d = json.loads(p.read_text())
        if delete_first:
            p.unlink()
            time.sleep(0.2)
        d["items"] = items
        p.write_text(json.dumps(d, indent=2))

    def open_page(self):
        self.b.eval("window.RELOADED=false; reloadData().then(()=>{ window.RELOADED=true; })")
        self.b.wait("window.RELOADED===true", 30)
        S.open_page(self.b)

    def hold(self, title, button="approve"):
        self.b.eval("window.HBTN=([...document.querySelectorAll('#v-intake-review tr.irprop')].find(t=>t.textContent.includes(%s))||{querySelector(){return null}}).querySelector('[data-ira=%s]'); !!window.HBTN" % (json.dumps(title), button))
        self.assertTrue(self.b.eval("!!window.HBTN"), f"no {button} button on {title!r}")

    def refresh(self):
        self.b.eval("window.REFRESHED=false; refreshRecords(['ABC-A-001']).then(()=>{ window.REFRESHED=true; })")
        self.b.wait("window.REFRESHED===true")

    def descs(self):
        return sorted(a["description"] for a in self.v.rows("actions"))

    def staged_decisions(self):
        out = {}
        for f in (self.v.root / "system" / "staging").glob("proposed-*.json"):
            for i in json.loads(f.read_text()).get("items", []):
                out.setdefault(f.name, {})[(i.get("values") or {}).get("description")] = i.get("decision")
        return out

    def settle(self, want=None, secs=14):
        """Wait until the tracker holds `want` (a description) or the page said it was stale, then a moment more."""
        end = time.time() + secs
        while time.time() < end:
            if want and want in self.descs():
                break
            if STALE in (self.b.eval("document.getElementById('snack')?document.getElementById('snack').innerText:''") or ""):
                break
            time.sleep(0.25)
        time.sleep(1.0)

    def snack(self):
        return self.b.eval("document.getElementById('snack')?document.getElementById('snack').innerText:''")

    def decided(self, text):
        """True when the item with this description is approved in staging or in the tracker."""
        if text in self.descs():
            return True
        return any(d.get(text) == "approved" for d in self.staged_decisions().values())

    # -- HIGH2 a: the file is renumbered in place
    def test_i1_bravo_row_after_a_renumber_in_the_file_saves_bravo_never_charlie(self):
        self.stage([item(1, "Alpha anchor"), item(2, "Bravo anchor"), item(3, "Charlie anchor")])
        self.open_page()
        self.hold("Bravo anchor")
        self.rewrite([item(1, "Bravo anchor"), item(2, "Charlie anchor")])             # Alpha was taken out; every later number moved
        self.b.eval("window.HBTN.click()")
        self.settle("Bravo anchor")
        self.assertTrue(self.decided("Bravo anchor"), "the row's own item is approved")
        self.assertFalse(self.decided("Charlie anchor"), "and no other item")

    def test_i1b_the_same_after_the_page_refreshed_its_list(self):
        self.stage([item(1, "Alpha anchor"), item(2, "Bravo anchor"), item(3, "Charlie anchor")])
        self.open_page()
        self.hold("Bravo anchor")
        self.rewrite([item(1, "Bravo anchor"), item(2, "Charlie anchor")])
        self.refresh()
        self.hold("Bravo anchor")                       # the page is drawn again: the row called Bravo is Bravo
        self.b.eval("window.HBTN.click()")
        self.settle("Bravo anchor")
        self.assertTrue(self.decided("Bravo anchor"))
        self.assertFalse(self.decided("Charlie anchor"))

    def test_i1c_reject_after_a_renumber_rejects_the_row_item_only(self):
        self.stage([item(1, "Alpha anchor"), item(2, "Bravo anchor"), item(3, "Charlie anchor")])
        self.open_page()
        self.hold("Bravo anchor", "reject")
        self.rewrite([item(1, "Bravo anchor"), item(2, "Charlie anchor")])
        self.b.eval("window.HBTN.click()")
        time.sleep(2.5)
        self.b.eval("(()=>{ const m=document.querySelector('#rjMenu button, .rjmenu button, [data-rjreason]'); if(m) m.click(); })()")
        time.sleep(2.0)
        d = {k: v for x in self.staged_decisions().values() for k, v in x.items()}
        self.assertNotEqual(d.get("Charlie anchor"), "rejected", "Charlie is never rejected for Bravo's row")

    # -- HIGH2 b: the file is deleted and written again under the same name
    def test_i2_delta_row_after_the_file_was_written_again_saves_nothing(self):
        self.stage([item(1, "Delta anchor")])
        self.open_page()
        self.hold("Delta anchor")
        self.rewrite([item(1, "Echo anchor")], delete_first=True)
        self.b.eval("window.HBTN.click()")
        self.settle("Delta anchor")
        self.assertIn(STALE, self.snack())
        self.assertFalse(self.decided("Echo anchor"), "Echo is never approved for Delta's row")
        self.assertFalse(self.decided("Delta anchor"))

    def test_i2b_the_same_after_a_refresh(self):
        self.stage([item(1, "Delta anchor")])
        self.open_page()
        self.hold("Delta anchor")
        self.rewrite([item(1, "Echo anchor")], delete_first=True)
        self.refresh()
        self.b.eval("window.HBTN.click()")
        self.settle("Delta anchor")
        self.assertFalse(self.decided("Echo anchor"))

    # -- the write loses a race: the file changes between the page's read and its write (a second tab, an apply, a sweep)
    def test_i3_a_file_that_changes_between_the_read_and_the_write_is_never_written_over(self):
        p = self.stage([item(1, "Alpha anchor"), item(2, "Bravo anchor")])
        self.open_page()
        self.hold("Bravo anchor")
        newer = json.loads(p.read_text())
        newer["items"].append(item(3, "Late anchor"))
        self.b.eval("""window.RACED=false; (()=>{ const rd=shared.VW.read; shared.VW.read=async function(path){ const t=await rd.apply(this,arguments);
          if(!window.RACED && /proposed-2026-10-09-1000-identity/.test(path)){ window.RACED=true; await api('/api/fs',{op:'write',path,text:%s}); } return t; }; })()""" % json.dumps(json.dumps(newer, indent=2)))
        self.b.eval("window.HBTN.click()")
        self.settle("Bravo anchor")
        self.assertIn(STALE, self.snack())
        self.assertFalse(self.decided("Bravo anchor"))
        self.assertIn("Late anchor", json.dumps(self.staged_decisions()), "the newer file was not written over")

    def test_i3b_a_second_tab_approved_it_first(self):
        from cdp import Browser
        self.stage([item(1, "Alpha anchor"), item(2, "Bravo anchor")])
        self.open_page()
        self.hold("Bravo anchor")
        b2 = Browser(self.width, self.height)
        self.addCleanup(b2.close)
        b2.goto(self.base + "/")
        b2.wait("typeof go==='function' && LIVE")
        b2.eval("go('intake-review')")
        b2.wait("!!document.querySelector('#v-intake-review [data-irsec=mail]')")
        b2.eval("[...document.querySelectorAll('#v-intake-review tr.irprop')].find(t=>t.textContent.includes('Bravo anchor')).querySelector('[data-ira=approve]').click()")
        self.settle("Bravo anchor")
        n = self.descs().count("Bravo anchor")
        self.b.eval("window.HBTN.click()")
        self.settle(None, 6)
        self.assertEqual(n, self.descs().count("Bravo anchor"), "not saved twice")

    # -- the routine buttons and Approve many
    def test_i4_routine_after_a_renumber_approves_only_the_rows_still_there(self):
        self.stage([item(1, "Alpha anchor"), item(2, "Bravo anchor"), item(3, "Charlie anchor")])
        self.open_page()
        self.b.eval("""((t)=>{ window.HBTN=[...document.querySelectorAll('#v-intake-review [data-ira=routine]')].find(btn=>{ let tr=btn.closest('tr').nextElementSibling;
          while(tr&&!tr.classList.contains('icsubhead')){ if(tr.textContent.includes(t)) return true; tr=tr.nextElementSibling; } return false; }); })('Bravo anchor')""")
        self.assertTrue(self.b.eval("!!window.HBTN"))
        self.rewrite([item(1, "Bravo anchor"), item(2, "Charlie anchor")])
        self.b.eval("window.HBTN.click()")
        self.settle("Bravo anchor")
        self.assertTrue(self.decided("Bravo anchor"))
        self.assertTrue(self.decided("Charlie anchor"))
        self.assertFalse(self.decided("Alpha anchor"), "the item that left the file is not approved")

    def test_i5_approve_many_with_stale_rows_approves_the_items_they_showed(self):
        self.stage([item(1, "Alpha anchor"), item(2, "Bravo anchor"), item(3, "Charlie anchor")])
        self.open_page()
        self.b.eval("window.OLDROWS=REV.filter(r=>/Bravo anchor/.test(JSON.stringify(r.rec))).map(r=>r)")
        self.rewrite([item(1, "Bravo anchor"), item(2, "Charlie anchor")])
        self.b.eval("rvDecideMany(window.OLDROWS,'approved')")
        self.settle("Bravo anchor")
        self.assertTrue(self.decided("Bravo anchor"))
        self.assertFalse(self.decided("Charlie anchor"))

    def test_i5b_approve_many_when_the_item_is_gone_saves_nothing(self):
        self.stage([item(1, "Delta anchor")])
        self.open_page()
        self.b.eval("window.OLDROWS=REV.filter(r=>/Delta anchor/.test(JSON.stringify(r.rec))).map(r=>r)")
        self.rewrite([item(1, "Echo anchor")], delete_first=True)
        self.b.eval("rvDecideMany(window.OLDROWS,'approved')")
        self.settle("Delta anchor", 6)
        self.assertFalse(self.decided("Echo anchor"))
        self.assertFalse(self.decided("Delta anchor"))

    # -- the peek's Save and approve
    def peek(self, title):
        self.b.eval("(t=>{ const r=REV.find(x=>JSON.stringify(x.rec).includes(t)); openProposal(r.n); })(%s)" % json.dumps(title))
        self.b.wait("shared.CUR&&shared.CUR.mode==='proposal'")

    def test_i6_save_and_approve_after_a_renumber_saves_bravo_and_leaves_charlie_alone(self):
        self.stage([item(1, "Alpha anchor"), item(2, "Bravo anchor"), item(3, "Charlie anchor")])
        self.open_page()
        self.peek("Bravo anchor")
        self.rewrite([item(1, "Bravo anchor"), item(2, "Charlie anchor")])
        self.refresh()
        self.b.eval("pkPropSave(true)")
        self.settle("Bravo anchor")
        self.assertTrue(self.decided("Bravo anchor"))
        self.assertFalse(self.decided("Charlie anchor"), "Charlie is not approved")
        mine = self.staged_decisions().get(f"proposed-{self.NAME}.json", {})
        left = [i["values"]["description"] for i in json.loads((self.v.root / "system" / "staging" / f"proposed-{self.NAME}.json").read_text())["items"]] if mine else []
        self.assertLessEqual(left.count("Bravo anchor"), 1, "Bravo is not written over Charlie in the file")
        self.assertEqual(self.descs().count("Bravo anchor"), 1)
        self.assertTrue("Charlie anchor" in left or "Charlie anchor" in self.descs(), "Charlie's proposal is intact")

    def test_i6b_save_and_approve_on_a_file_written_again_says_so_and_saves_nothing(self):
        self.stage([item(1, "Delta anchor")])
        self.open_page()
        self.peek("Delta anchor")
        self.rewrite([item(1, "Echo anchor")], delete_first=True)
        self.b.eval("pkPropSave(true)")
        self.settle("Delta anchor", 6)
        self.assertFalse(self.decided("Echo anchor"))
        self.assertFalse(self.decided("Delta anchor"))
        self.assertIn(STALE, self.snack())

    # -- a double click
    def test_i7_a_double_click_saves_one_item_once(self):
        self.stage([item(1, "Alpha anchor"), item(2, "Bravo anchor")])
        self.open_page()
        self.hold("Bravo anchor")
        self.b.eval("window.HBTN.click(); window.HBTN.click()")
        self.settle("Bravo anchor")
        time.sleep(2)
        self.assertEqual(1, self.descs().count("Bravo anchor"))
        self.assertFalse(self.decided("Alpha anchor"))


if __name__ == "__main__":
    unittest.main()
