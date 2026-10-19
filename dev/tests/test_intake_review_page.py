"""#232-0 (v2.5.0): Intake and Review on one page, the skeleton, in a real browser against the live server. The page opens at
#intake-review and from the sidebar's one entry; the old #review, #intake and #inbox addresses open it; the List, Board and
Two panes switch draws each view and is remembered in this browser; a meeting with proposals opens with one click and closes
with a second, its groups (Needs your decision, then Routine) hanging under it; Esc closes it; Later and Not needed start folded.
The row model and folding rules have their own tests (test_intake_review_model.py, test_intake_review_fold.py).

Run: python3 dev/tests/test_intake_review_page.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_dashboard  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402


class IntakeReviewPage(LiveBrowserCase):
    shared_server = True
    width, height = 1400, 1000

    @classmethod
    def load(cls, v):
        test_dashboard.populate(v)
        v.run(script="build_dashboard.py")

    def setUp(self):
        super().setUp()
        self.b.eval("try{ localStorage.removeItem('creaite-ir-view'); }catch(e){} irSetView('list'); go('today')")

    def model(self):
        """A fixed model on the page's own Review rows, so the open and close rules have something to open."""
        ns = self.b.eval("REV.filter(r=>!r.done).map(r=>r.n)")
        self.assertGreaterEqual(len(ns), 2, "the sample has fewer than two proposals")
        m = {"v": 1, "meetings": [
            {"id": "mA", "src": "calendar", "title": "Sample steering", "day": "2026-10-05", "start": "09:00", "p": None, "stage": "drafted",
             "state": "proposals", "age": 0, "stale": False, "groups": {"needs": ns[:1], "routine": ns[1:2]}},
            {"id": "mB", "src": "calendar", "title": "Sample sync", "day": "2026-10-05", "start": "15:00", "p": None, "stage": "arrived",
             "state": "ready", "age": 0, "stale": False, "groups": {"needs": [], "routine": []}}],
            "mail": {"needs": [], "routine": ns[2:3]}, "other": {"needs": [], "routine": []},
            "later": [{"key": "k1", "title": "Snoozed"}], "not_needed": [{"key": "k2", "title": "Chat", "reason": "Informal chat"}], "counts": {}}
        self.b.eval(f"D.intake_review={json.dumps(m)}; irOpen.value=null; irStage.value='all'; irFolded.value={{}}; go('intake-review')")
        self.b.wait("!!document.querySelector('#v-intake-review [data-irm=mA]')")

    def test_the_address_and_the_old_ones(self):
        b = self.b
        b.eval("go('intake-review')")
        self.assertEqual(b.eval("[VIEW, location.hash, document.querySelector('#irTitle').textContent]"),
                         ["intake-review", "#intake-review", "Intake and Review"])
        self.assertEqual(b.eval("['#review','#intake','#inbox','#intake-review'].map(h=>parseHash(h).v)"), ["intake-review"] * 4)
        b.eval("go('today'); location.hash='#review'")
        b.wait("VIEW==='intake-review'")
        self.assertFalse(b.eval("document.getElementById('v-intake-review').hidden"))

    def test_one_sidebar_entry(self):
        b = self.b
        self.assertEqual(b.eval("document.querySelectorAll('.rail [data-v=inbox]').length"), 0)
        b.eval("document.querySelector('.rail [data-v=review]').click()")
        b.wait("VIEW==='intake-review'")
        self.assertEqual(b.eval("document.querySelector('.rail [data-v=review]').getAttribute('aria-current')"), "page")
        self.assertIn("Intake and Review", b.eval("document.querySelector('.rail [data-v=review]').textContent"))

    def test_the_three_views_and_the_choice_is_remembered(self):
        b = self.b
        self.model()
        self.assertTrue(b.eval("!!document.querySelector('[data-irv=list]') && !!document.querySelector('.icpipe')"))
        for v, mark in (("board", "[data-irv=board] [data-ircol=drafted] [data-irm=mA]"), ("two", "[data-irv=two] [data-irdet]"), ("list", "[data-irv=list]")):
            b.eval(f"document.querySelector('[data-irview={v}]').click()")
            b.wait(f"!!document.querySelector({mark!r})")
            self.assertEqual(b.eval(f"document.querySelector('[data-irview={v}]').getAttribute('aria-pressed')"), "true")
        b.eval("document.querySelector('[data-irview=board]').click()")
        self.assertEqual(b.eval("JSON.parse(localStorage.getItem('creaite-ir-view'))"), "board")

    def test_one_click_opens_a_meeting_and_one_closes_it(self):
        b = self.b
        self.model()
        row = "document.querySelector('[data-irm=mA] td.title')"
        b.eval(f"{row}.click()")
        b.wait("document.querySelector('[data-irm=mA]').getAttribute('aria-expanded')==='true'")
        self.assertEqual(b.eval("[...document.querySelectorAll('#v-intake-review [data-irv=list] tbody tr.icsubhead')].slice(0,2).map(t=>t.dataset.irg)"),
                         ["needs", "routine"])
        self.assertIn("Sample steering · Needs your decision · 1", b.eval("document.querySelector('[data-irg=needs]').textContent"))
        b.eval("document.querySelector('[data-irm=mB] td.title').click()")              # nothing to check: it never opens, the first stays open
        self.assertEqual(b.eval("irOpen.value"), "mA")
        b.eval(f"{row}.click()")
        b.wait("document.querySelector('[data-irm=mA]').getAttribute('aria-expanded')==='false'")
        b.eval(f"{row}.click()")
        b.wait("irOpen.value==='mA'")
        b.eval("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))")
        b.wait("irOpen.value===null")

    def test_stage_filter_and_folded_sections(self):
        b = self.b
        self.model()
        b.eval("document.querySelector('.icpipe [data-irstage=arrived]').click()")
        b.wait("!document.querySelector('[data-irv=list] [data-irm=mA]')")
        b.eval("document.querySelector('.icpipe [data-irstage=arrived]').click()")
        b.wait("!!document.querySelector('[data-irv=list] [data-irm=mA]')")
        self.assertEqual(b.eval("[...document.querySelectorAll('[data-irfold]')].map(x=>x.getAttribute('aria-expanded'))"), ["false", "false"])
        b.eval("document.querySelector('[data-irfold=not_needed]').click()")
        b.wait("document.querySelector('[data-irsec=not_needed]').textContent.includes('Informal chat')")

    def test_empty(self):
        b = self.b
        b.eval("D.intake_review={v:1,meetings:[],mail:{needs:[],routine:[]},other:{needs:[],routine:[]},later:[],not_needed:[],counts:{}}; go('intake-review')")
        self.assertIn("Nothing here. Meetings appear when they end.", b.eval("document.getElementById('v-intake-review').textContent"))


if __name__ == "__main__":
    unittest.main()
