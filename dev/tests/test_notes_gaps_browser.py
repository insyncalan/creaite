"""BL-301 B gaps (v20-notes-gaps): the Notes tab's three gaps in a real browser against the real live server.

Run: python3 dev/tests/test_notes_gaps_browser.py   (needs Google Chrome; skipped otherwise)

  - the toolbar's Image button adds a picture: filed at once in the notes folder's _images/, shown as creaite's figure, and
    written `![caption](_images/…)` when the note saves;
  - changing a note's title renames its file when the note saves, the address names the new file, and a [[link]] to it in
    another note follows;
  - a Working session note's date and attendees are edited in its header after it is made (a wrong date says so and isn't
    saved).
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_notes_tab_browser import NotesTab  # noqa: E402,F401  (its helpers; its own tests run in their own file)

PICK = """(async()=>{ const c=document.createElement('canvas'); c.width=8; c.height=8; c.getContext('2d').fillRect(0,0,8,8);
  const blob=await new Promise(r=>c.toBlob(r,'image/png')); const dt=new DataTransfer(); dt.items.add(new File([blob],'Org chart.png',{type:'image/png'}));
  const i=document.querySelector('.ned .nimgfile'); i.files=dt.files; i.dispatchEvent(new Event('change',{bubbles:true})); return true; })()"""


class NotesGapsBrowser(LiveBrowserCase):
    width, height = 1400, 1000
    log, notes_dir, make, type_end = NotesTab.log, NotesTab.notes_dir, NotesTab.make, NotesTab.type_end

    def saved(self, f, text):
        for _ in range(150):
            if f.is_file() and text in f.read_text():
                return True
            self.b.pump(0.1)
        return False

    def test_image_button_files_a_picture_in_images(self):
        b = self.b
        self.make("With a picture")
        self.assertTrue(b.eval("!!document.querySelector('.nbar [data-nt=image]')"))
        self.assertEqual(b.eval("document.querySelector('.nbar [data-nt=image]').getAttribute('aria-label')"),
                         "Add a picture here (PNG or JPEG, up to 2 MB)")
        b.eval(PICK)
        b.wait("!!document.querySelector('.nbody figure.cimg img[src^=\"data:image/png\"]')", 15)
        pics = list((self.notes_dir() / "_images").glob("*-org-chart.png"))
        self.assertEqual(len(pics), 1, "filed at once in _images/")
        b.eval("noteFlush()")
        f = self.notes_dir() / "With a picture.md"
        self.assertTrue(self.saved(f, f"](_images/{pics[0].name})"), f.read_text())
        b.eval("go('today')")
        b.eval("go('notes','ABC')")
        b.wait("noteCur.value&&noteCur.value.note.title==='With a picture'&&!!document.querySelector('.nbody figure.cimg img[src^=\"data:image/png\"]')", 15)

    def test_renamed_title_renames_the_file_and_links_follow(self):
        b = self.b
        self.make("Old name")
        b.eval("go('cockpit','ABC')")
        self.make("Points at it")
        self.type_end("See [[Old name]] today.")
        b.eval("noteFlush()")
        b.wait("noteSave.value.state==='saved'", 15)
        b.click(".nlist .ni:not(.on)")
        b.wait("noteCur.value&&noteCur.value.note.title==='Old name'")
        b.eval("(()=>{ const i=document.getElementById('noteTitle'); i.value='New name'; i.dispatchEvent(new Event('input',{bubbles:true})); })()")
        b.eval("noteFlush()")
        b.wait("noteCur.value&&noteCur.value.note.file==='New name.md'", 15)
        self.assertTrue((self.notes_dir() / "New name.md").is_file())
        self.assertFalse((self.notes_dir() / "Old name.md").exists())
        b.wait("location.hash.includes('New%20name.md')", 5)
        self.assertIn("[[New name]]", (self.notes_dir() / "Points at it.md").read_text())
        self.assertIn("Renamed the file to New name.md", b.eval("document.querySelector('.nmsg').textContent"))
        moves = [e for e in self.log() if e.get("op") == "move"]
        self.assertEqual([m["via"] for m in moves], ["dashboard"])

    def test_working_session_date_and_with_edited_in_the_header(self):
        b = self.b
        self.make("Workshop", "working-session")
        b.wait("!!document.getElementById('noteWsDate')")
        set_ = "(id,v)=>{ const i=document.getElementById(id); i.value=v; i.dispatchEvent(new Event('input',{bubbles:true})); i.dispatchEvent(new Event('change',{bubbles:true})); }"
        b.eval(f"({set_})('noteWsDate','sometime soon')")
        b.wait("document.getElementById('noteDateRead')&&document.getElementById('noteDateRead').classList.contains('bad')")
        self.assertEqual(b.eval("document.getElementById('noteWsDate').getAttribute('aria-invalid')"), "true")
        b.eval(f"({set_})('noteWsDate','01-10-2026')")
        b.eval("document.getElementById('noteWsDate').dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}))")
        b.eval(f"({set_})('noteWsWith','Omar Ali, Lena Park')")
        b.wait("!document.getElementById('noteDatePop')")
        b.eval("noteFlush()")
        f = self.notes_dir() / "Workshop.md"
        self.assertTrue(self.saved(f, "date: 2026-10-01"), f.read_text())
        self.assertIn("with: [Omar Ali, Lena Park]", f.read_text())


del NotesTab

if __name__ == "__main__":
    unittest.main()
