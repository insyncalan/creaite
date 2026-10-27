"""#374 piece 2 (Alan 1c): Activity > What ask creaite changed shows a file's plain name and project, never its stored path,
and offers Show in Finder, which (FINDER_REVEAL on) posts the file's stored path to the existing /api/report/reveal.

Run: python3 dev/tests/test_activity_show_in_finder.py   (needs Google Chrome; skipped otherwise)

The list is a stand-in for /api/changes/list (fictional rows); /api/report/reveal is the real route with CREAITE_NO_LAUNCH, so nothing starts.
  - the Change cell holds the name (no extension) and "in <project name>", with no "projects/" anywhere in the row;
  - Show in Finder posts exactly {path: <the file's stored path>} to /api/report/reveal (never /api/open); a move posts the target file;
    the server answers (not launched) and no message is shown;
  - a file directly in inbox/ has the button; a settings file or one in the vault's root has none; a file that has gone is answered
    with "That file isn't there any more." (no path); a Deleted row has no button;
  - test_the_switch_is_pinned_on fails if FINDER_REVEAL is set back to false.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402


class ShowInFinder(LiveBrowserCase):
    shared_server = True

    @classmethod
    def server_env(cls):
        return {"CREAITE_NO_LAUNCH": "1"}

    def rows_for(self, folder):
        at = "2026-10-26 09:00:00"
        return [
            {"id": 1, "at": at, "op": "edit", "path": f"projects/{folder}/minutes/2026-10-20 Steering.docx", "tier": "ordinary", "why": "Alan asked"},
            {"id": 2, "at": at, "op": "move", "path": f"projects/{folder}/minutes/Old name.docx",
             "to": "projects/_portfolio/notes/New name.md", "tier": "sensitive", "why": "Alan asked"},
            {"id": 3, "at": at, "op": "create", "path": "inbox/Loose file.txt", "tier": "ordinary"},
            {"id": 4, "at": at, "op": "create", "path": "CLAUDE.md", "tier": "ordinary"},
            {"id": 5, "at": at, "op": "edit", "path": f"projects/{folder}/gone/Missing.docx", "tier": "ordinary"},
            {"id": 6, "at": at, "op": "delete", "path": f"projects/{folder}/minutes/Deleted.docx", "tier": "sensitive"},
            {"id": 7, "at": at, "op": "edit", "path": "system/config/settings.json", "tier": "sensitive"},
        ]

    def activity(self):
        b = self.b
        code = b.eval("Object.keys(D.folders)[0]")
        folder = b.eval("D.folders[%s]" % json.dumps(code))
        (self.v.root / "projects" / folder / "minutes").mkdir(parents=True, exist_ok=True)
        (self.v.root / "projects/_portfolio/notes").mkdir(parents=True, exist_ok=True)
        for rel in (f"projects/{folder}/minutes/2026-10-20 Steering.docx", "projects/_portfolio/notes/New name.md", "inbox/Loose file.txt"):
            (self.v.root / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.v.root / rel).write_text("fictional")
        b.eval("""(()=>{ window.__open=[]; window.__opened=[]; const f=window.fetch.bind(window); const rows=%s;
          window.fetch=function(u,o){ const url=String(u);
            if(url.includes('/api/changes/list')) return Promise.resolve(new Response(JSON.stringify({ok:true,changes:rows}),{status:200,headers:{'Content-Type':'application/json'}}));
            if(url.includes('/api/open')) window.__opened.push(o.body);
            if(url.includes('/api/report/reveal')) window.__open.push(JSON.parse(o.body));
            return f(u,o); }; return true; })()""" % json.dumps(self.rows_for(folder)))
        b.eval("go('activity')")
        b.wait("document.querySelectorAll('#achgTbl tr[data-achg]').length===7", 10)
        return code, folder, None

    def row(self, n):
        return self.b.eval("(()=>{ const r=document.querySelector('#achgTbl tr[data-achg=\"%d\"]'); return {text:r.children[2].textContent.replace(/\\s+/g,' ').trim(),"
                           "btn:[...r.querySelectorAll('button')].map(x=>x.textContent.trim())}; })()" % n)

    def test_name_and_project_are_shown_and_never_a_path(self):
        code, folder, _ = self.activity()
        pname = self.b.eval("pName(%s)" % json.dumps(code))
        r = self.row(1)
        self.assertIn("Changed 2026-10-20 Steering", r["text"])
        self.assertIn(f"in {pname}", r["text"])
        self.assertNotIn(".docx", r["text"])
        self.assertEqual(self.b.eval("document.querySelectorAll('#achgTbl code').length"), 0)
        self.assertNotIn("projects/", self.b.eval("document.getElementById('achgTbl').textContent"))
        self.assertIn("Show in Finder", r["btn"])

    def test_show_in_finder_posts_the_file_to_the_reveal_route(self):
        _, folder, _ = self.activity()
        self.before = self.b.eval("document.body.textContent.split(\"isn't there\").length-1")
        self.b.eval("document.querySelector('#achgTbl tr[data-achg=\"1\"] [data-achgshow]').click()")
        self.b.wait("window.__open.length===1", 5)
        self.assertEqual(self.b.eval("window.__open"), [{"path": f"projects/{folder}/minutes/2026-10-20 Steering.docx"}])
        self.b.pump(0.5)
        self.assertEqual(self.b.eval("window.__opened"), [], "/api/open is not used")
        self.assertEqual(self.b.eval("document.body.textContent.split(\"isn't there\").length-1"), self.before, "no message when it worked")
        self.assertFalse(self.b.eval("document.getElementById('snack').classList.contains('on')"))

    def test_a_move_shows_its_target_and_reveals_the_target_file(self):
        self.activity()
        r = self.row(2)
        self.assertIn("Moved Old name", r["text"])
        self.assertIn("→ New name in Portfolio", r["text"])
        self.assertEqual(r["btn"][0], "Show in Finder")
        self.b.eval("document.querySelector('#achgTbl tr[data-achg=\"2\"] [data-achgshow]').click()")
        self.b.wait("window.__open.length===1", 5)
        self.assertEqual(self.b.eval("window.__open"), [{"path": "projects/_portfolio/notes/New name.md"}])
        self.assertEqual(self.b.eval("window.__opened"), [])

    def test_the_button_follows_the_servers_allow_list(self):
        self.activity()
        self.assertIn("Show in Finder", self.row(3)["btn"], "inbox/<file>: the file itself is allowed")
        self.assertNotIn("Show in Finder", self.row(4)["btn"], "a file in the vault's root")
        self.assertIn("Intake", self.row(3)["text"])
        self.b.eval("document.querySelector('#achgTbl tr[data-achg=\"3\"] [data-achgshow]').click()")
        self.b.wait("window.__open.length===1", 5)
        self.assertEqual(self.b.eval("window.__open"), [{"path": "inbox/Loose file.txt"}])

    def test_a_settings_file_has_no_button(self):
        self.activity()
        self.assertNotIn("Show in Finder", self.row(7)["btn"])
        shown = self.b.eval("[...document.querySelectorAll('#achgTbl [data-achgshow]')].map(e=>JSON.parse(e.getAttribute('data-achgshow')).path)")
        self.assertEqual(len(shown), 4, shown)
        self.assertFalse([x for x in shown if x.startswith("system/") or x == "CLAUDE.md"], shown)

    def test_a_file_that_has_gone_is_answered_in_plain_words(self):
        self.activity()
        n = self.b.eval("document.body.textContent.split(\"can't open\").length-1")
        self.b.eval("document.querySelector('#achgTbl tr[data-achg=\"5\"] [data-achgshow]').click()")
        self.b.wait("window.__open.length===1", 5)
        # the snack element itself (the same words are also in the page's script, so the page text proves nothing)
        self.b.wait("(()=>{ const t=document.getElementById('snackT'), s=document.getElementById('snack'); return !!t&&!!s&&s.classList.contains('on')&&t.textContent.trim()===\"That file isn't there any more.\"; })()", 5)
        self.assertEqual(self.b.eval("document.getElementById('snackT').textContent.trim()"), "That file isn't there any more.")
        self.assertEqual(self.b.eval("document.body.textContent.split(\"can't open\").length-1"), n, "the server's message, with the path, is not shown")

    def test_the_switch_is_pinned_on(self):
        src = (Path(__file__).resolve().parents[2] / "system/templates/dashboard/src/core/finderReveal.js").read_text()
        self.assertIn("export const FINDER_REVEAL=true;", src)

    def test_a_deleted_row_offers_no_show_in_finder(self):
        self.activity()
        self.assertIn("Deleted Deleted", self.row(6)["text"])
        self.assertNotIn("Show in Finder", self.row(6)["btn"], "nothing is there to show")

    def test_no_raw_path_in_any_label_or_title_of_the_rows(self):
        self.activity()
        bad = self.b.eval("[...document.querySelectorAll('#achgTbl [aria-label],#achgTbl [title]')].map(e=>(e.getAttribute('aria-label')||'')+'|'+(e.getAttribute('title')||'')).filter(x=>/projects\\/|inbox\\/|system\\/|CLAUDE\\.md|\\.docx|\\.txt/.test(x))")
        self.assertEqual(bad, [])
        self.assertGreater(self.b.eval("document.querySelectorAll('#achgTbl [aria-label]').length"), 0, "the buttons are labelled")


if __name__ == "__main__":
    unittest.main()
