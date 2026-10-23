"""2.6.2 (#314): the page sends the row's fingerprint as `expect` on /api/review, and works against a server that ignores it.

Real headless Chrome on the real live server of this tree (with or without the route's guarded diff: an unknown field is harmless, and
a match goes through either way). The mismatch words review.py says are recognised by the page (REVIEW_CHANGED).
Run: python3 dev/tests/test_review_expect_page.py      (needs Google Chrome)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402
import test_minutes_editor as me  # noqa: E402


class PageSendsExpect(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        populate(v)
        cls.proposal = me.stage_meeting(v)

    def test_the_call_carries_the_fingerprint_and_the_decision_still_goes_through(self):
        b = self.b
        b.eval(f"go('minutes',{{file:{json.dumps(self.proposal)}}})")
        b.wait("document.querySelector('#v-minutes tr.mi')", 15)
        b.eval("window.SENT=[]; const f=window.fetch; window.fetch=function(u,o){ if(/\\/api\\/review$/.test(String(u))) window.SENT.push(JSON.parse(o.body)); return f.apply(this,arguments); }")
        row = b.eval(f"REV.find(r=>r.kind==='draft'&&r.file==={json.dumps(self.proposal)})")
        self.assertTrue(row and len(row.get("fp", "")) == 12, row)
        b.eval(f"window.RES=null; reviewViaServer(REV.find(r=>r.kind==='draft'&&r.file==={json.dumps(self.proposal)}),'approved',['as-staged']).then(()=>{{window.RES=1}})")
        b.wait("window.RES===1", 30)
        sent = b.eval("window.SENT")
        self.assertEqual(len(sent), 1, sent)
        self.assertEqual(sent[0]["expect"], row["fp"])
        self.assertEqual(sent[0]["decision"], "approved")
        self.b.pump(0.5)
        self.assertIn("Approved", self.b.eval("(document.getElementById('toastHost')||{innerText:''}).innerText"), "the decision went through")

    def test_file_without_transcript_carries_the_fingerprint_and_a_changed_item_is_not_filed(self):
        """Cap's note 1: File without transcript (stores/minutes.js) sent file + ref only. It now sends the row's fingerprint, and the
        server's "has changed since you looked at it" is told to the person as the stale-row words, with nothing filed."""
        b = self.b
        b.eval(f"go('minutes',{{file:{json.dumps(self.proposal)}}})")
        b.wait("document.querySelector('#v-minutes tr.mi')", 15)
        row = b.eval(f"REV.find(r=>r.kind==='draft'&&r.file==={json.dumps(self.proposal)})")
        b.eval("window.SENT=[]; const f=window.fetch; window.fetch=function(u,o){ if(/\\/api\\/review$/.test(String(u))){ window.SENT.push(JSON.parse(o.body)); "
               "return Promise.resolve(new Response(JSON.stringify({ok:false,message:'1: not recorded — that item has changed since you looked at it, so nothing was changed. Look at the list again.'}),{status:200})); } return f.apply(this,arguments); }")
        b.eval(f"window.RES=null; fileWithoutTranscript({json.dumps(self.proposal)}).then(x=>{{window.RES=x}})")
        b.wait("!!window.RES", 30)
        sent = b.eval("window.SENT")
        self.assertEqual(len(sent), 1, sent)
        self.assertEqual(sent[0]["expect"], row["fp"])
        self.assertIn("without-transcript", sent[0]["modes"])
        res = b.eval("window.RES")
        self.assertFalse(res["ok"])
        self.assertTrue(res.get("stale"))
        self.assertEqual(res["message"], b.eval("STALE_ROW_MSG"))

    def test_the_mismatch_words_are_recognised(self):
        self.assertTrue(self.b.eval("REVIEW_CHANGED.test('2: not recorded — that item has changed since you looked at it, so nothing was changed. Look at the list again.')"))
        self.assertFalse(self.b.eval("REVIEW_CHANGED.test('3: already approved')"))


if __name__ == "__main__":
    unittest.main(verbosity=1)
