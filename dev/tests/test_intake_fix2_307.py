"""#307 fix pass 2 (v2.6.1): the Intake peek never saves onto another item; the toast counts what the server saved; the plain words of
Moved minutes, "0 of N drafted" and a refused Add files name.

Run: python3 dev/tests/test_intake_fix2_307.py   (needs Google Chrome; skipped otherwise)
"""
import glob
import json
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import intake_review_support as S  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402

STALE = "That one was already approved or changed, so nothing was saved. The list has been refreshed."
BRAVO, CHARLIE = "Supplier may miss the November delivery", "Confirm data residency with legal"
SNACK = "(document.getElementById('snack')?document.getElementById('snack').innerText:'')"


class Fix2(LiveBrowserCase):
    shared_server = False
    width, height = 1400, 1000

    @classmethod
    def load(cls, v):
        S.load(v)

    def review_rows(self):
        return json.loads(self.v.run("list", "--json", script="review.py", cwd=self.v.root).stdout)

    def elsewhere(self, text):
        n = next(x["n"] for x in self.review_rows() if text in x["text"])
        self.v.run("approve", str(n), script="review.py", cwd=self.v.root)
        self.v.run("apply", cwd=self.v.root)

    def tracker_text(self):
        return json.dumps([self.v.rows(t) for t in ("actions", "raid")], default=str)

    def peek(self, text):
        b = self.b
        S.open_page(b)
        b.eval("openProposal((t=>REV.find(r=>JSON.stringify(r.rec).includes(t)).n)(%s))" % json.dumps(text))
        b.wait("document.getElementById('panel').classList.contains('on')")

    def refresh(self):
        self.b.eval("window.RF=false; reloadData().then(()=>{ window.RF=true; })")
        self.b.wait("window.RF===true")

    def snack(self):
        return self.b.eval(SNACK)

    def stale_case(self, button, how):
        b = self.b
        self.peek(BRAVO)
        if how == "approved":
            self.elsewhere(BRAVO)
        else:                                   # the same file rewritten under the same name and ref
            f = glob.glob(str(self.v.root / "system/staging/proposed-*sweep*.json"))[0]
            d = json.loads(Path(f).read_text())
            next(i for i in d["items"] if BRAVO in json.dumps(i))["values"]["description"] = BRAVO + " (rewritten)"
            Path(f).write_text(json.dumps(d, indent=2))
        self.refresh()
        before = self.tracker_text()
        b.eval("document.getElementById('%s').click()" % button)
        b.wait("/already approved or changed/.test(%s)" % SNACK, 20)
        self.assertEqual(self.snack().strip().split("\n")[0], STALE)
        time.sleep(1.5)
        self.assertEqual(before, self.tracker_text(), "nothing was saved")
        self.assertEqual(sum(1 for x in self.review_rows() if CHARLIE in x["text"]), 1, "the neighbour is still pending, untouched")

    # -- HIGH3
    def test_a_save_and_approve_after_the_item_was_approved_elsewhere_saves_nothing(self):
        self.stale_case("pkPSaveA", "approved")

    def test_b_plain_save_after_the_item_was_approved_elsewhere_saves_nothing(self):
        self.stale_case("pkPSave", "approved")

    def test_c_content_rewritten_under_the_same_name_saves_nothing(self):
        self.stale_case("pkPSaveA", "rewritten")

    def test_d_an_approve_elsewhere_of_another_item_still_lets_the_peek_save_its_own(self):
        b = self.b
        self.peek(BRAVO)
        self.elsewhere(CHARLIE)
        self.refresh()
        b.eval("document.getElementById('pkPSaveA').click()")
        for _ in range(80):
            if BRAVO in self.tracker_text():
                break
            time.sleep(0.25)
        self.assertIn(BRAVO, self.tracker_text())
        self.assertEqual(sum(1 for x in self.review_rows() if BRAVO in x["text"]), 0)

    # -- the toast counts what the server saved
    def test_e_three_clicks_on_one_row_say_saved_one_action(self):
        b = self.b
        S.open_page(b)
        b.eval("(()=>{ const t=[...document.querySelectorAll('#v-intake-review tr.irprop')].find(t=>t.textContent.includes(%s)); const x=t.querySelector('[data-ira=approve]'); x.click(); x.click(); x.click(); })()" % json.dumps(CHARLIE))
        b.wait("/Saved/.test(%s)" % SNACK, 30)
        self.assertEqual(self.snack().strip().split("\n")[0], "Saved 1 action")

    def test_f_saved_capped_follows_the_apply_line(self):
        b = self.b
        S.open_page(b)
        n = b.eval("(()=>{ const r=a=>({r:{kind:'actions'},v:a}); const L=[r('approved'),r('approved'),r('approved'),r('rejected')];"
                   " return [savedCapped(L,'Apply 4: written 1, filed 0, rejected 0, 0 still pending.').length, savedCapped(L,'Apply 4: written 2, filed 0, rejected 1').length, savedCapped(L,'something else').length]; })()")
        self.assertEqual(n, [1, 3, 4])

    # -- plain words
    def test_g_moved_minutes_is_exact(self):
        S.open_page(self.b)
        got = self.b.eval("[isMovedMinutes(\"That file isn't there.\"), isMovedMinutes('That proposal is no longer pending.'),"
                          " isMovedMinutes(\"draft: x.docx isn't there, so nothing is filed: approve it again\"),"
                          " isMovedMinutes(\"it isn't there or has no creaite-data block\"), isMovedMinutes('Nothing pending for it'), isMovedMinutes('')]")
        self.assertEqual(got, [True, True, False, False, False, False])

    def test_h_drafted_wording(self):
        S.open_page(self.b)
        got = self.b.eval("['0 of 1 waiting in Review; 1 couldn\\'t be read: process it again.', '2 of 2 waiting in Review', '1 of 3 waiting in Review; 2 couldn\\'t be read'].map(plainSay)")
        self.assertEqual(got[0], "Nothing was drafted. 1 couldn't be read: process it again.")
        self.assertEqual(got[1], "2 of 2 drafted, ready to check in Intake")
        self.assertTrue(got[2].startswith("1 of 3 drafted, ready to check in Intake"))

    def test_i_a_long_name_and_raw_errors_never_reach_the_note(self):
        b = self.b
        S.open_page(b)
        long = b.eval("(async()=>{ const r=await uploadInboxFile(new File(['x'],'L'.repeat(300)+'.vtt')); return r.fail; })()")
        self.assertIn("the file name is too long", long.lower())
        self.assertNotIn("OSError", long)
        for raw in ["OSError: [Errno 63] File name too long: '/Users/someone/vault/inbox/the file.vtt'", "Errno 28 no space", "Traceback (most recent call last)",
                    "failed at /private/var/x/inbox/a.vtt"]:
            why = b.eval("(async()=>{ const old=api; api=async()=>({ok:false,message:%s}); try{ const r=await uploadInboxFile(new File(['x'],'a.vtt')); return r.fail; } finally{ api=old; } })()" % json.dumps(raw))
            for bad in ("OSError", "Errno", "Traceback", "/Users", "/private"):
                self.assertNotIn(bad, why, raw)
        ok = b.eval("(async()=>{ const old=api; api=async()=>({ok:false,message:'creaite didn\\'t answer'}); try{ return (await uploadInboxFile(new File(['x'],'a.vtt'))).fail; } finally{ api=old; } })()")
        self.assertIn("creaite didn't answer", ok)


if __name__ == "__main__":
    unittest.main()
