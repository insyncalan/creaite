"""v2.1.0 P6 (BL-335): the weekly report view, in a real browser on the real live server (LiveBrowserCase; no Claude runs).

The sample portfolio's ABC project (a milestone slipping, an overdue action, two RAID items, a decision) is opened at
#reporting=ABC; its report is built by P3's /api/report/draft from the tracker.

- Every section of the mockup is there, in order: header with logos, health with its trend, At a glance, summary, milestones
  (timeline and list), asks, this week and next week, decisions, risks and issues, overdue actions, current state.
- The eye on a risk row leaves it out and Save keeps that in the draft; the milestone list's eye changes the list only.
- A figure's eye hides it and the layout remembers the glance order.
- Show as exported draws none of the editing controls.
- The logo route sends only the project's logo files; the header draws them.
- The address opens the same report again.

Run: python3 dev/tests/test_weekly_report_view.py      (Chrome tier; skipped without Chrome)
"""
import base64
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402

PX = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")
ORDER = ["header", "health", "glance", "summary", "milestones", "asks", "this_week", "next_week", "decisions", "risks", "overdue",
         "current_state"]


class WeeklyReportView(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        populate(v)
        logos = v.root / "system/branding/logos"
        logos.mkdir(parents=True, exist_ok=True)
        (logos / "firm.png").write_bytes(PX)
        (logos / "ABC-client.png").write_bytes(PX)

    def setUp(self):
        super().setUp()
        self.b.eval("go('weekly',{code:'ABC'})")
        self.b.wait("document.querySelector('#v-reporting section[data-id=current_state]')", 20)

    def ev(self, js):
        return self.b.eval(js)

    def test_every_section_is_there_in_order(self):
        ids = self.ev("[...document.querySelectorAll('#v-reporting .page>section[data-id]')].map(s=>s.dataset.id)")
        self.assertEqual(ids, ORDER)
        self.assertTrue(self.ev("!!document.querySelector('#v-reporting .wr-flag')"), "health flag")
        self.assertTrue(self.ev("!!document.querySelector('#v-reporting svg.wr-tl')"), "timeline")
        self.assertTrue(self.ev("document.querySelectorAll('#v-reporting .wr-stat').length>=4"), "figures")
        self.assertIn("#reporting=ABC", self.ev("location.hash"))

    def test_logos_drawn_from_the_project_files(self):
        self.b.wait("document.querySelectorAll('#v-reporting .wr-logo img').length==2", 10)
        self.ev("fetch('/api/report/logo',{method:'POST',headers:{'Content-Type':'application/json','X-Creaite-Token':D.token||''},"
                "body:JSON.stringify({code:'ABC',paths:['system/branding/logos/firm.png','CLAUDE.md','../x']})})"
                ".then(r=>r.json()).then(j=>{window.__logos=Object.keys(j.logos)})")
        self.b.wait("window.__logos", 10)
        self.assertEqual(self.ev("window.__logos"), ["system/branding/logos/firm.png"])

    def test_risk_eye_and_save(self):
        n = self.ev("document.querySelectorAll('#v-reporting [data-id=risks] tbody tr').length")
        self.assertGreaterEqual(n, 2)
        self.ev("document.querySelector('#v-reporting [data-id=risks] tbody tr .wr-eye').click()")
        self.b.wait("document.querySelector('#v-reporting [data-id=risks] tr.hidrow')", 5)
        self.assertIn("Showing", self.ev("document.querySelector('#v-reporting [data-id=risks] .wr-count').textContent"))
        self.ev("document.querySelector('#v-reporting .sheet-root').dispatchEvent(new KeyboardEvent('keydown',{key:'s',metaKey:true,bubbles:true,cancelable:true}))")
        self.b.wait("/Saved · version/.test(document.querySelector('#v-reporting .sheet-status').textContent)", 10)
        draft = next((self.v.root / "system/staging/drafts").glob("*Weekly report*.html"))
        text = draft.read_text(encoding="utf-8")
        data = json.loads(text.split('id="creaite-data">', 1)[1].split("</script>", 1)[0])
        risks = next(s for s in data["sections"] if s["id"] == "risks")
        self.assertTrue(any(r.get("shown") is False for r in risks["rows"]))

    def test_milestone_list_eye_changes_the_list_only(self):
        self.ev("document.querySelector('#v-reporting [data-id=milestones] .wr-link').click()")
        self.b.wait("document.querySelector('#v-reporting [data-id=milestones] table')", 5)
        before = self.ev("document.querySelectorAll('#v-reporting [data-id=milestones] svg.wr-tl circle').length")
        self.ev("document.querySelector('#v-reporting [data-id=milestones] tbody .wr-eye').click()")
        self.b.wait("document.querySelector('#v-reporting [data-id=milestones] tr.hidrow')", 5)
        self.assertEqual(self.ev("document.querySelectorAll('#v-reporting [data-id=milestones] svg.wr-tl circle').length"), before)

    def test_figure_eye_and_exported_view(self):
        self.ev("document.querySelector('#v-reporting .wr-stat .wr-seye').click()")
        self.b.wait("document.querySelector('#v-reporting .wr-stat.off')", 5)
        self.ev("document.querySelector('#v-reporting #hubExp').click()")
        self.b.wait("!document.querySelector('#v-reporting .wr-eye')", 5)
        self.assertFalse(self.ev("!!document.querySelector('#v-reporting .wr-stat.off')"))
        self.assertFalse(self.ev("!!document.querySelector('#v-reporting .wr-count')"))

    def test_figure_and_list_eyes_autosave(self):
        """Hand check 73: the figure's eye and the milestone list's eye go through the sheet, so autosave writes them."""
        self.ev("document.querySelector('#v-reporting .wr-stat .wr-seye').click()")
        self.b.wait("document.querySelector('#v-reporting .wr-stat.off')", 5)
        self.ev("document.querySelector('#v-reporting [data-id=milestones] .wr-link').click()")
        self.b.wait("document.querySelector('#v-reporting [data-id=milestones] table')", 5)
        self.ev("document.querySelector('#v-reporting [data-id=milestones] tbody .wr-eye').click()")
        self.b.wait("document.querySelector('#v-reporting [data-id=milestones] tr.hidrow')", 5)
        self.b.wait("/Saved · version/.test(document.querySelector('#v-reporting .sheet-status').textContent)", 10)
        draft = next((self.v.root / "system/staging/drafts").glob("*Weekly report*.html"))
        data = json.loads(draft.read_text(encoding="utf-8").split('id="creaite-data">', 1)[1].split("</script>", 1)[0])
        glance = next(s for s in data["sections"] if s["type"] == "figures")
        self.assertTrue(any(f.get("shown") is False for f in glance["figures"]), "the hidden figure is saved")
        ms = next(s for s in data["sections"] if s["id"] == "milestones")
        self.assertTrue(len(ms["data"]["milestones"]) < self.ev("document.querySelectorAll('#v-reporting [data-id=milestones] tbody tr').length"),
                        "the milestone left out of the list is saved")

    def test_click_words_edit_in_place(self):
        self.ev("document.querySelector('#v-reporting [data-id=summary] .wr-edit').click()")
        self.b.wait("document.querySelector('#v-reporting [data-id=summary] .sheet-rich.ProseMirror')", 5)

    def test_current_state_panes_use_the_one_editor(self):
        self.assertEqual(self.ev("document.querySelectorAll('#v-reporting [data-id=current_state] textarea').length"), 0)
        self.ev("document.querySelector('#v-reporting [data-id=current_state] .wr-edit').click()")
        self.b.wait("document.querySelector('#v-reporting [data-id=current_state] .sheet-rich.ProseMirror')", 5)


if __name__ == "__main__":
    unittest.main()
