"""#307 paths 16, 17, 18 (v2.6.1): a row on Intake is its proposal file plus its item ref, never its place in the current list.
The list renumbers when something changes outside the page (Claude Code's approve, a second tab, a sweep, auto-apply); the open page
must then approve the item it showed, or say plainly that it was already approved or changed and save nothing.

Run: python3 dev/tests/test_intake_stale_rows_307.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import intake_review_support as S  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402

STALE = "That one was already approved or changed, so nothing was saved. The list has been refreshed."


class Stale307(LiveBrowserCase):
    shared_server = False          # each test changes the record
    width, height = 1400, 1000

    @classmethod
    def load(cls, v):
        S.load(v)

    # -- helpers
    def review_rows(self):
        r = self.v.run("list", "--json", script="review.py", cwd=self.v.root)
        return json.loads(r.stdout)

    def num(self, text):
        """review.py's number for the pending item whose title holds `text`."""
        return next(x["n"] for x in self.review_rows() if text in x["text"])

    def elsewhere(self, *texts):
        """What Claude Code does: approve these by number with review.py, then apply (the list renumbers behind the page)."""
        for t in texts:
            self.v.run("approve", str(self.num(t)), script="review.py", cwd=self.v.root)
        self.v.run("apply", cwd=self.v.root)

    def descriptions(self):
        return sorted(a["description"] for a in self.v.rows("actions"))

    def open_mail(self):
        S.open_page(self.b)

    def hold(self, title, button="approve"):
        """Keep the row's button as the page drew it (the stale DOM a person clicks)."""
        self.b.eval("window.HBTN=([...document.querySelectorAll('#v-intake-review tr.irprop')].find(t=>t.textContent.includes(%s))||{querySelector(){return null}}).querySelector('[data-ira=%s]'); !!window.HBTN" % (json.dumps(title), button))
        self.assertTrue(self.b.eval("!!window.HBTN"), f"no {button} button on the row {title!r}")

    def renumbered(self, title):
        """Quick-refresh the page's list from the server (as an event does); returns REV's number for `title` afterwards."""
        self.b.eval("window.REFRESHED=false; refreshRecords(['ABC-A-001']).then(()=>{ window.REFRESHED=true; })")
        self.b.wait("window.REFRESHED===true")
        return self.b.eval("(t=>(REV.find(r=>JSON.stringify(r.rec).includes(t))||{}).n)(%s)" % json.dumps(title))

    def message(self):
        return self.b.eval("document.getElementById('snack')?document.getElementById('snack').innerText:''")

    # -- 16 and 17
    def test_c16_a_renumbered_list_approves_the_item_the_row_showed(self):
        b = self.b
        self.open_mail()
        self.hold("Confirm data residency with legal")
        n0 = b.eval("(t=>REV.find(r=>JSON.stringify(r.rec).includes(t)).n)('Confirm data residency with legal')")
        self.elsewhere("Chase legal on the SOW", "Vendor exits the market")          # two earlier proposals leave the list: every later number moves
        after = self.renumbered("Confirm data residency with legal")
        self.assertNotEqual(after, n0, "the list should have renumbered")
        base = self.descriptions()
        b.eval("window.HBTN.click()")
        b.wait("document.getElementById('snack') && /Applied|Approved|saved/i.test(document.getElementById('snack').innerText) || false", 30)
        b.wait("true")
        for _ in range(60):
            if "Confirm data residency with legal" in self.descriptions():
                break
            b.eval("0")
            import time
            time.sleep(0.25)
        self.assertEqual(sorted(base + ["Confirm data residency with legal"]), self.descriptions(),
                         "the row's own item is approved, and nothing else")

    def test_c17_a_row_approved_elsewhere_is_refused_and_nothing_else_is_approved(self):
        b = self.b
        self.open_mail()
        self.hold("Confirm data residency with legal")
        self.elsewhere("Confirm data residency with legal")
        base = self.descriptions()
        self.renumbered("Share the pilot plan")
        b.eval("window.HBTN.click()")
        b.wait("document.getElementById('snack') && document.getElementById('snack').innerText.includes('already approved or changed')", 20)
        self.assertEqual(self.message().strip().split("\n")[0], STALE)
        self.assertEqual(base, self.descriptions(), "nothing else was approved")
        self.assertEqual(sum(1 for x in self.review_rows() if "Confirm data residency" in x["text"]), 0)

    def test_c17b_a_stale_reject_is_refused_too(self):
        b = self.b
        self.open_mail()
        self.hold("Confirm data residency with legal", "reject")
        self.elsewhere("Confirm data residency with legal")
        self.renumbered("Share the pilot plan")
        pending = len(self.review_rows())
        b.eval("window.HBTN.click()")
        b.wait("document.getElementById('snack') && document.getElementById('snack').innerText.includes('already approved or changed')", 20)
        self.assertEqual(pending, len(self.review_rows()), "no other item was rejected")

    # -- 18
    def routine_button(self, title):
        """Keep the Approve routine button of the group whose rows include `title`."""
        self.b.eval("""((t)=>{ window.HBTN=[...document.querySelectorAll('#v-intake-review [data-ira=routine]')].find(btn=>{ let tr=btn.closest('tr').nextElementSibling;
          while(tr&&!tr.classList.contains('icsubhead')){ if(tr.textContent.includes(t)) return true; tr=tr.nextElementSibling; } return false; }); })(%s)""" % json.dumps(title))
        self.assertTrue(self.b.eval("!!window.HBTN"))

    def routine_ns(self):
        return self.b.eval("irModel().mail.routine.map(n=>JSON.stringify(REV.find(r=>r.n===n).rec.t))")

    def test_c18_approve_routine_after_the_routine_was_approved_elsewhere_saves_nothing(self):
        b = self.b
        self.open_mail()
        titles = [json.loads(t) for t in self.routine_ns()]
        self.assertTrue(titles, "the fixture's mail section has routine rows")
        self.routine_button(titles[0])
        self.elsewhere(*titles)
        base = self.descriptions()
        self.renumbered(titles[0])
        b.eval("window.HBTN.click()")
        b.wait("document.getElementById('snack') && document.getElementById('snack').innerText.includes('already approved or changed')", 30)
        self.assertEqual(base, self.descriptions())
        self.assertNotIn("lines taken out", self.message())

    def test_c18b_approve_routine_leaves_the_changed_ones_for_you_and_says_how_many(self):
        b = self.b
        self.open_mail()
        titles = [json.loads(t) for t in self.routine_ns()]
        if len(titles) < 2:
            self.skipTest("needs two routine rows")
        self.routine_button(titles[0])
        self.elsewhere(titles[0])
        self.renumbered(titles[1])
        b.eval("window.HBTN.click()")
        b.wait("document.getElementById('snack') && document.getElementById('snack').innerText.includes('changed since you looked, left for you')", 30)
        self.assertIn("1 changed since you looked, left for you", self.message())
        self.assertEqual(sorted([titles[0]] + titles[1:]), [d for d in self.descriptions() if d in titles])

    # -- a second tab
    def test_c19_a_second_tab_approves_and_the_first_tab_refuses_the_same_row(self):
        from cdp import Browser
        b = self.b
        self.open_mail()
        self.hold("Confirm data residency with legal")
        b2 = Browser(self.width, self.height)
        self.addCleanup(b2.close)
        b2.goto(self.base + "/")
        b2.wait("typeof go==='function' && LIVE")
        b2.eval("go('intake-review')")
        b2.wait("!!document.querySelector('#v-intake-review [data-irsec=mail]')")
        b2.eval("[...document.querySelectorAll('#v-intake-review tr.irprop')].find(t=>t.textContent.includes('Confirm data residency with legal')).querySelector('[data-ira=approve]').click()")
        import time
        for _ in range(80):
            if "Confirm data residency with legal" in self.descriptions():
                break
            time.sleep(0.25)
        self.assertIn("Confirm data residency with legal", self.descriptions())
        base = self.descriptions()
        b.eval("window.HBTN.click()")
        b.wait("document.getElementById('snack') && document.getElementById('snack').innerText.includes('already approved or changed')", 20)
        self.assertEqual(base, self.descriptions())

    # -- the identity check itself
    def test_c20_a_model_number_resolves_to_its_file_and_ref_not_its_place(self):
        b = self.b
        self.open_mail()
        r = b.eval("""(()=>{ const n=irModel().mail.needs.concat(irModel().mail.routine)[0]; const was=REV.find(x=>x.n===n);
          const key=was.file+'|'+was.ref, wasN=was.n; REV.forEach(x=>{ x.n=x.n+100; });          /* the list renumbered behind the page */
          const now=revForModelN(n); return [key, now?now.file+'|'+now.ref:null, now?now.n:null, wasN, irRow(n)===now]; })()""")
        self.assertEqual(r[0], r[1])
        self.assertEqual(r[2], r[3] + 100)
        self.assertTrue(r[4])

    def test_c21_a_number_whose_item_has_gone_resolves_to_nothing(self):
        b = self.b
        self.open_mail()
        self.assertTrue(b.eval("""(()=>{ const n=irModel().mail.needs.concat(irModel().mail.routine)[0]; const was=REV.find(x=>x.n===n);
          REV.splice(REV.indexOf(was),1); REV.forEach(x=>{ if(x.n>n) x.n--; }); return irRow(n)===null; })()"""))

    def test_c22_a_decision_made_the_other_way_elsewhere_is_not_flipped(self):
        b = self.b
        self.open_mail()
        r = b.eval("""(()=>{ const r=REV.find(x=>x.kind==='actions'); const data={items:[{n:r.ref,decision:'rejected'}]};
          try{ setDecision(data,r,'approved'); return 'flipped'; }catch(e){ return e.message; } })()""")
        self.assertIn("already changed", r)

    def test_c23_an_edit_retargets_only_the_edited_row_not_an_identical_one_in_the_file(self):
        """Cap (2.6.2): two identical items in one file share a fingerprint; editing one must not move the other's snapshot."""
        b = self.b
        self.open_mail()
        r = b.eval("""(()=>{ SNAP.model=D.intake_review; SNAP.keys=new Map([[1,{key:'f.json|1',fp:'x',cfp:'OLD'}],[2,{key:'f.json|2',fp:'x',cfp:'OLD'}],
          [3,{key:'g.json|1',fp:'x',cfp:'OLD'}]]);
          snapFollowEdit('f.json','1','OLD','NEW'); return [1,2,3].map(n=>SNAP.keys.get(n).cfp); })()""")
        self.assertEqual(r, ["NEW", "OLD", "OLD"])


if __name__ == "__main__":
    unittest.main()
