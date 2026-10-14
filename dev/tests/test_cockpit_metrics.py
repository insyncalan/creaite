"""BL-185 (sprint-peek-new): the status cockpit refined. The metrics row under a project's status line: no "No due date" figure
(the No due date card stays), short date words ("Due 7d", "21d"), the shared warning icon beside the words of an alert metric,
and every metric one click target to its detail. A real browser against the real live server.

Run: python3 dev/tests/test_cockpit_metrics.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

ROW = "[...document.querySelectorAll('#v-cockpit .evrow .evbox')]"


class Metrics(LiveBrowserCase):
    shared_server = True

    def cockpit(self, code="ABC", slip=None):
        b = self.b
        if slip is not None:
            b.eval(f"P.find(p=>p.code==={code!r}).slip={slip}")
        b.eval(f"go('cockpit',{code!r})")
        b.wait("document.querySelector('#v-cockpit .evrow .evbox')")
        return b.eval(f"{ROW}.map(e=>({{l:e.querySelector('.l').textContent, v:e.querySelector('.v').textContent, bad:e.querySelector('.v').classList.contains('bad'), "
                      "icon:!!e.querySelector('.l svg[data-icn=\"alert\"]'), click:e.classList.contains('click'), role:e.getAttribute('role')}))")

    def test_four_core_metrics_short_labels_and_no_no_due_date(self):
        rows = self.cockpit(slip=21)
        labels = [r["l"] for r in rows]
        self.assertNotIn("No due date", labels)
        self.assertEqual(labels[:4], ["Overdue actions", "Urgent risks", "Milestone slip", f"Due {self.b.eval('S.dueSoon')}d"])
        self.assertEqual(rows[2]["v"], "21d")
        self.assertTrue(self.b.eval("!!document.getElementById('undatedCard')||P.find(p=>p.code==='ABC').undated.total===0"))   # FR-95's card is untouched

    def test_alert_metrics_carry_the_shared_icon_beside_their_words(self):
        rows = self.cockpit(slip=21)
        for r in rows:
            self.assertEqual(r["icon"], r["bad"], r)                       # an alert has the icon; a quiet metric has none
            self.assertTrue(r["l"].strip())                                # the words are always there
        self.assertTrue(any(r["icon"] for r in rows))
        self.assertNotIn("⚠", self.b.eval("document.querySelector('#v-cockpit .evrow').textContent"))   # never a typed glyph
        self.assertEqual(self.b.eval("document.querySelector('#v-cockpit .evrow svg[data-icn=\"alert\"]').getAttribute('aria-hidden')"), "true")

    def test_every_metric_with_a_detail_is_one_click_target(self):
        b = self.b
        rows = self.cockpit(slip=21)
        for r in rows:
            if r["l"] == "Early warnings" and r["v"] == "0":
                continue                                                   # nothing to show when there are none
            self.assertTrue(r["click"], r)
            self.assertEqual(r["role"], "link", r)
        b.eval(f"{ROW}.find(e=>e.querySelector('.l').textContent==='Milestone slip').querySelector('svg').dispatchEvent(new MouseEvent('click',{{bubbles:true}}))")
        b.wait("VIEW==='milestones'&&MV.view==='move'")                    # the icon is part of the target: BL-186, Milestone slip opens Movement
        self.cockpit(slip=0)
        b.click("#v-cockpit .evrow .evbox[data-nav^='raid:urgentonly'] .l")
        b.wait("VIEW==='work' && WT==='raid'")


if __name__ == "__main__":
    unittest.main()
