"""v2.1.0 P6 (BL-335): the weekly report view, in a real browser on the real live server (LiveBrowserCase; no Claude runs).

The sample portfolio's ABC project (a milestone slipping, an overdue action, two RAID items, a decision) is opened at
#weekly=ABC; its report is built by P3's /api/report/draft from the tracker.

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
        self.b.wait("document.querySelector('#v-weekly section[data-id=current_state]')", 20)

    def ev(self, js):
        return self.b.eval(js)

    def test_every_section_is_there_in_order(self):
        ids = self.ev("[...document.querySelectorAll('#v-weekly .page>section[data-id]')].map(s=>s.dataset.id)")
        self.assertEqual(ids, ORDER)
        self.assertTrue(self.ev("!!document.querySelector('#v-weekly .wr-flag')"), "health flag")
        self.assertTrue(self.ev("!!document.querySelector('#v-weekly svg.wr-tl')"), "timeline")
        self.assertTrue(self.ev("document.querySelectorAll('#v-weekly .wr-stat').length>=4"), "figures")
        self.assertIn("#weekly=ABC", self.ev("location.hash"))

    def test_logos_drawn_from_the_project_files(self):
        self.b.wait("document.querySelectorAll('#v-weekly .wr-logo img').length==2", 10)
        self.ev("fetch('/api/report/logo',{method:'POST',headers:{'Content-Type':'application/json','X-Creaite-Token':D.token||''},"
                "body:JSON.stringify({code:'ABC',paths:['system/branding/logos/firm.png','CLAUDE.md','../x']})})"
                ".then(r=>r.json()).then(j=>{window.__logos=Object.keys(j.logos)})")
        self.b.wait("window.__logos", 10)
        self.assertEqual(self.ev("window.__logos"), ["system/branding/logos/firm.png"])

    def test_risk_eye_and_save(self):
        n = self.ev("document.querySelectorAll('#v-weekly [data-id=risks] tbody tr').length")
        self.assertGreaterEqual(n, 2)
        self.ev("document.querySelector('#v-weekly [data-id=risks] tbody tr .wr-eye').click()")
        self.b.wait("document.querySelector('#v-weekly [data-id=risks] tr.hidrow')", 5)
        self.assertIn("Showing", self.ev("document.querySelector('#v-weekly [data-id=risks] .wr-count').textContent"))
        self.ev("[...document.querySelectorAll('#v-weekly .sheet-bar button')].find(b=>b.textContent==='Save').click()")
        self.b.wait("/Saved · version/.test(document.querySelector('#v-weekly .sheet-bar [role=status]').textContent)", 10)
        draft = next((self.v.root / "system/staging/drafts").glob("*Weekly report*.html"))
        text = draft.read_text(encoding="utf-8")
        data = json.loads(text.split('id="creaite-data">', 1)[1].split("</script>", 1)[0])
        risks = next(s for s in data["sections"] if s["id"] == "risks")
        self.assertTrue(any(r.get("shown") is False for r in risks["rows"]))

    def test_milestone_list_eye_changes_the_list_only(self):
        self.ev("document.querySelector('#v-weekly [data-id=milestones] .wr-link').click()")
        self.b.wait("document.querySelector('#v-weekly [data-id=milestones] table')", 5)
        before = self.ev("document.querySelectorAll('#v-weekly [data-id=milestones] circle').length")
        self.ev("document.querySelector('#v-weekly [data-id=milestones] tbody .wr-eye').click()")
        self.b.wait("document.querySelector('#v-weekly [data-id=milestones] tr.hidrow')", 5)
        self.assertEqual(self.ev("document.querySelectorAll('#v-weekly [data-id=milestones] circle').length"), before)

    def test_figure_eye_and_exported_view(self):
        self.ev("document.querySelector('#v-weekly .wr-stat .wr-seye').click()")
        self.b.wait("document.querySelector('#v-weekly .wr-stat.off')", 5)
        self.ev("[...document.querySelectorAll('#v-weekly .sheet-bar button')].find(b=>b.textContent==='Show as exported').click()")
        self.b.wait("!document.querySelector('#v-weekly .wr-eye')", 5)
        self.assertFalse(self.ev("!!document.querySelector('#v-weekly .wr-stat.off')"))
        self.assertFalse(self.ev("!!document.querySelector('#v-weekly .wr-count')"))

    def test_click_words_edit_in_place(self):
        self.ev("document.querySelector('#v-weekly [data-id=summary] .wr-edit').click()")
        self.b.wait("document.querySelector('#v-weekly [data-id=summary] textarea')", 5)
        self.ev("(()=>{const t=document.querySelector('#v-weekly [data-id=summary] textarea'); t.value='A new line.'; t.dispatchEvent(new Event('input',{bubbles:true}));})()")
        self.b.wait("document.querySelector('#v-weekly [data-id=summary] textarea').value==='A new line.'", 5)


if __name__ == "__main__":
    unittest.main()
