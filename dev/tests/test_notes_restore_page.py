"""#175 (page half, Alan's answers 3 and 4): Activity's notes row is one editing session with a Restore button.
A real browser against the real live server over a throwaway vault (the server folds the session's saves into one row).

Run: python3 dev/tests/test_notes_restore_page.py   (needs Google Chrome; skipped otherwise)

  - a folded notes row reads "3 saves, 14:02 to 14:31" ("1 save, 14:02") and its button is "Restore 14:02", not "Undo";
  - Restore asks first (names the note and the time; Keep changes nothing), then puts the file back as it was when the session
    began and reopens the note: the editor shows the older text and the next autosave is NOT "Changed outside creaite";
  - with the note open and typing unsaved, the typing is saved first (the request order is save, then undo), then restored;
  - a note that is not the open one is restored and its row refreshed; the open note is left alone;
  - a failed restore says so and leaves the note as it was;
  - a row that is not a notes session keeps Undo, and so does a notes row without `saves` (from before the fold).
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
import test_notes_tab_browser as notes_tab_browser  # noqa: E402

SPY = """(()=>{ window.__req=[]; window.__failUndo=false; const f=window.fetch.bind(window);
  window.fetch=function(u,o){ const url=String(u); if(/api\\/(notes\\/save|changes\\/undo)/.test(url)) window.__req.push(url.split('/api/')[1]);
    if(window.__failUndo&&url.includes('/api/changes/undo')) return Promise.resolve(new Response(JSON.stringify({ok:false,message:'Not restored: the file has changed since.'}),{status:200,headers:{'Content-Type':'application/json'}}));
    return f(u,o); }; return true; })()"""
NO_TIMER = """(()=>{ const st=window.setTimeout.bind(window); window.setTimeout=(fn,ms,...a)=>(ms===2000&&String(fn).includes('noteFlush'))?0:st(fn,ms,...a); return true; })()"""
ROW = "[...document.querySelectorAll('#achgTbl tr[data-achg]')].find(r=>r.children[2].querySelector('b').textContent==='%s')"


class RestorePage(LiveBrowserCase):
    width, height = 1400, 1000
    log, notes_dir, make, type_end = (notes_tab_browser.NotesTab.log, notes_tab_browser.NotesTab.notes_dir, notes_tab_browser.NotesTab.make,
                                      notes_tab_browser.NotesTab.type_end)

    def saved(self, f, text):
        b = self.b
        self.type_end(text)
        for _ in range(300):
            if f.is_file() and text in f.read_text() and b.eval("noteSave.value.state") == "saved":
                return
            b.pump(0.05)
        self.fail(f"{text!r} not saved: {f.read_text()}")

    def session(self, title, words=("one", " two", " three")):
        self.make(title)
        f = self.notes_dir() / f"{title}.md"
        for w in words:
            self.saved(f, w)
        return f

    def activity(self):
        b = self.b
        b.eval("go('activity')")
        b.wait("!!document.querySelector('#achgTbl tr[data-achg]')", 10)

    def rows(self):
        return self.b.eval("[...document.querySelectorAll('#achgTbl tr[data-achg]')].map(r=>({path:r.children[2].querySelector('b').textContent,"
                           "text:r.children[2].textContent.trim(),btn:[...r.querySelectorAll('button')].map(x=>x.textContent.trim()).filter(t=>t!=='Show in Finder')}))")

    def row_of(self, title):
        return next(r for r in self.rows() if r["path"] == title)

    def times(self, title):
        r = self.b.eval("api('/api/changes/list',{})")
        c = next(c for c in r["changes"] if c["path"].endswith(f"/{title}.md"))
        return c["first_at"][11:16], c["at"][11:16], c["saves"]

    def ask(self, title):
        b = self.b
        b.eval(ROW % title + ".querySelector('[data-achgrestore]').click()")
        b.wait("!!document.querySelector('[data-achgask]')", 5)

    def click_restore(self, title):
        self.ask(title)
        self.b.eval("document.querySelector('[data-achgrestoreyes]').click()")

    def test_a_folded_row_reads_as_a_session_with_a_restore_button(self):
        self.session("Folded")
        self.activity()
        a, z, n = self.times("Folded")
        self.assertEqual(n, 3)
        r = self.row_of("Folded")
        self.assertIn(f"3 saves, {a}" + (f" to {z}" if z != a else ""), r["text"])
        self.assertEqual(r["btn"], [f"Restore {a}"])

    def test_one_save_reads_1_save(self):
        self.session("Single", words=("only",))
        self.activity()
        a, z, n = self.times("Single")
        self.assertEqual(n, 1)
        r = self.row_of("Single")
        self.assertIn(f"1 save, {a}", r["text"])
        self.assertNotIn(" to ", r["text"])

    def test_restore_asks_first_naming_the_note_and_the_time_and_keep_changes_nothing(self):
        b = self.b
        f = self.session("Ask")
        self.activity()
        a, _, _ = self.times("Ask")
        self.ask("Ask")
        q = b.eval("document.querySelector('[data-achgask]').textContent")
        self.assertIn("Ask", q)
        self.assertIn(a, q)
        self.assertIn("three", f.read_text(), "nothing is restored by the question")
        b.eval("document.querySelector('[data-achgrestoreno]').click()")
        self.assertEqual(self.row_of("Ask")["btn"], [f"Restore {a}"])
        self.assertIn("three", f.read_text())

    def test_restore_of_the_open_note_reopens_it_with_the_older_text_and_no_conflict(self):
        b = self.b
        f = self.session("Open")
        self.activity()
        self.click_restore("Open")
        b.wait("noteCur.value&&noteCur.value.path.endsWith('/Open.md')&&!noteCur.value.body.includes('three')", 10)
        text = f.read_text()
        self.assertNotIn("one", text)
        self.assertNotIn("three", text)
        b.eval("go('notes','ABC')")
        b.wait("!!document.querySelector('.nbody.ProseMirror')", 10)
        self.assertNotIn("one", b.eval("document.querySelector('.nbody').textContent"))
        self.saved(f, " after")
        self.assertEqual(b.eval("noteSave.value.state"), "saved")
        self.assertNotIn("Changed outside creaite", b.eval("document.getElementById('noteSave').textContent"))

    def test_unsaved_typing_in_the_open_note_is_saved_first_then_restored(self):
        b = self.b
        f = self.session("Dirty")
        b.eval(SPY)
        b.eval(NO_TIMER)
        self.activity()
        b.eval("noteMeta({tags:['restoretest']}); true")             # an unsaved change to the open note (the autosave timer never fires)
        self.assertEqual(b.eval("noteSave.value.state"), "typing")
        self.assertNotIn("restoretest", f.read_text())
        b.eval("window.__req.length=0; true")
        self.ask("Dirty")
        b.eval("document.querySelector('[data-achgrestoreyes]').click()")
        b.wait("window.__req.includes('changes/undo')", 10)
        order = b.eval("window.__req")
        self.assertIn("notes/save", order, "the pending change was saved before the restore")
        self.assertLess(order.index("notes/save"), order.index("changes/undo"))
        b.wait("noteCur.value&&!noteCur.value.body.includes('three')", 10)
        self.assertNotIn("three", f.read_text())
        self.assertNotEqual(b.eval("noteSave.value.state"), "conflict")

    def test_a_note_that_is_not_open_is_restored_and_the_open_one_is_left(self):
        b = self.b
        fa = self.session("Closed")
        fb = self.session("Current", words=("keep",))
        self.activity()
        self.click_restore("Closed")
        b.wait("/Undone/.test(document.getElementById('achgTbl').textContent)", 10)
        self.assertNotIn("three", fa.read_text())
        self.assertTrue(b.eval("noteCur.value.path.endsWith('/Current.md')"))
        self.assertIn("keep", fb.read_text())

    def test_a_failed_restore_says_so_and_leaves_the_note(self):
        b = self.b
        f = self.session("Fails")
        before = f.read_text()
        b.eval(SPY)
        self.activity()
        b.eval("window.__failUndo=true")
        self.click_restore("Fails")
        b.wait("document.body.textContent.includes('Not restored')", 10)
        self.assertEqual(f.read_text(), before)
        self.assertIn("three", b.eval("noteCur.value.body"))

    def test_other_rows_keep_undo(self):
        b = self.b
        self.session("Plain")
        self.activity()
        rows = [{"id": 900, "at": "2026-10-17 10:00:00", "op": "create", "path": "projects/x/y.txt", "why": "test", "tier": "ordinary"},
                {"id": 901, "at": "2026-10-17 10:05:00", "op": "edit", "path": "projects/ABC Example/notes/Old.md", "why": "test", "tier": "ordinary"}]
        b.eval("(()=>{ putHTML(document.getElementById('achgTbl'), askChangesHtml(" + json.dumps(rows) + ")); return true; })()")
        texts = b.eval("[...document.querySelectorAll('#achgTbl tr[data-achg]')].map(r=>[...r.querySelectorAll('button')].map(x=>x.textContent.trim()))")
        self.assertEqual(texts, [["Show in Finder", "Undo"], ["Show in Finder", "Undo"]])   # #374: the folder button comes first


if __name__ == "__main__":
    unittest.main()
