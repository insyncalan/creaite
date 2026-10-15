"""#124: Delete note in a real browser against the real live server, at 1400 px and 900 px.

Run: python3 dev/tests/test_notes_delete_browser.py   (needs Google Chrome; skipped otherwise)

  - "Delete note…" is last in the note's … menu, in red; it opens the confirm box naming the note, Cancel focused;
  - Cancel (and Esc) closes it and nothing is asked for: no card, the note stays;
  - Delete note puts exactly one card up in ask creaite (the move into the archive, the file named); Reject leaves the note;
  - doing it again and Approve moves it into _Archive: the note closes, the list drops it, a toast says "Moved … to the archive";
  - the toast's Undo brings it back into the list;
  - nothing scrolls sideways at 900 px with the box open.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_notes_tab_browser import NotesTab  # noqa: E402,F401  (its helpers; its own tests run in their own file)

SHOTS = Path.home() / "dev.env/team-stark-shots/notes-124"
WS = "Working session"


class NotesDeleteBrowser(LiveBrowserCase):
    width, height = 1400, 1000
    log, notes_dir, make = NotesTab.log, NotesTab.notes_dir, NotesTab.make

    def shot(self, name):
        try:
            SHOTS.mkdir(parents=True, exist_ok=True)
            self.b.screenshot(str(SHOTS / f"{name}-{self.b.eval('innerWidth')}.png"))
        except OSError:  # a shot is for people only; the test doesn't depend on it
            pass

    def archived(self):
        return next((self.v.root / "projects").glob("ABC */")) / "_Archive" / "notes" / f"{WS}.md"

    def open_box(self):
        b = self.b
        b.click(".nmorewrap .nmore")
        b.wait("!!document.querySelector('.nmorewrap [role=menu] .bad')")
        self.shot("menu")
        items = b.eval("[...document.querySelectorAll('.nmorewrap [role=menuitem]')].map(x=>x.textContent)")
        self.assertTrue(items[-1].startswith("Delete note…"), items)
        self.assertNotEqual(b.eval("getComputedStyle(document.querySelector('.nmorewrap .bad b')).color"),
                            b.eval("getComputedStyle(document.querySelector('.nmorewrap [role=menuitem] b')).color"))
        b.click(".nmorewrap [role=menu] .bad")
        b.wait("document.getElementById('noteDelDlg').open")

    def card(self):
        return self.b.eval("[...document.querySelectorAll('#chLog .edcard')].map(c=>c.querySelector('b').textContent)")

    def flow(self):
        b = self.b
        self.make(WS)
        b.eval("noteFlush()")
        b.wait("noteSave.value.state==='saved'", 15)
        f = self.notes_dir() / f"{WS}.md"
        self.open_box()
        self.shot("confirm")
        self.assertEqual(b.eval("document.getElementById('ndelH').textContent"), f"Delete “{WS}”?")
        self.assertIn("Restore it any time from Files › Archived", b.eval("document.getElementById('ndelP').textContent"))
        self.assertIn("shows the link as missing", b.eval("document.getElementById('ndelP').textContent"))
        self.assertEqual(b.eval("document.activeElement.id"), "ndelCancel")             # Cancel by default
        self.assertLessEqual(b.eval("document.documentElement.scrollWidth-document.documentElement.clientWidth"), 0)
        b.click("#ndelCancel")
        b.wait("!document.getElementById('noteDelDlg').open")
        self.assertEqual(self.card(), [])                                                  # Cancel: nothing asked for
        self.open_box()
        b.key("Escape")
        b.wait("!document.getElementById('noteDelDlg').open")
        self.assertEqual(self.card(), [])
        self.assertTrue(f.is_file())
        self.open_box()
        b.click("#ndelGo")                                                                  # 1: Delete note, then the card
        b.wait("document.querySelector('#chLog .edcard [data-ed=\"approve\"]')", 15)
        self.assertEqual(self.card(), [f"Delete note “{WS}” (move it to the archive)"])
        self.assertIn("_Archive/notes/Working session.md", b.eval("document.querySelector('#chLog .edcard').textContent"))
        self.shot("card")
        b.click("#chLog .edcard [data-ed=\"reject\"]")                                       # Reject: left where it is
        b.wait("document.querySelector('#chLog .edcard .acts').textContent.includes('Rejected')", 15)
        self.assertTrue(f.is_file())
        self.assertFalse(self.archived().exists())
        b.click("#chatClose")                                                               # ask creaite sits over the page
        b.wait("!document.getElementById('chat').classList.contains('on')")
        b.eval("go('notes','ABC')")
        b.wait(f"noteCur.value&&noteCur.value.note.title==={json.dumps(WS)}", 15)
        self.open_box()
        b.click("#ndelGo")
        b.wait("[...document.querySelectorAll('#chLog .edcard [data-ed=\"approve\"]')].length===1", 15)
        self.assertEqual(len(self.card()), 2)                                                # the rejected one, and this one
        b.click("#chLog .edcard:last-of-type [data-ed=\"approve\"]")
        b.wait("!noteCur.value||noteCur.value.note.title!=='Working session'", 20)
        b.wait("document.querySelector('.snack') && document.querySelector('.snack').textContent.includes('to the archive')", 10)
        self.assertFalse(f.exists())
        self.assertTrue(self.archived().is_file())
        self.assertNotIn(WS, b.eval("[...document.querySelectorAll('.nlist .ni b')].map(x=>x.textContent)"))
        self.shot("moved")
        b.eval("[...document.querySelectorAll('.snack button')].find(x=>/Undo/.test(x.textContent)).click()")
        for _ in range(150):
            if f.is_file():
                break
            b.pump(0.1)
        self.assertTrue(f.is_file())                                                       # Undo: back in its notes folder
        b.wait(f"[...document.querySelectorAll('.nlist .ni b')].some(x=>x.textContent==={json.dumps(WS)})", 15)

    def test_delete_note_confirm_then_card_then_undo(self):
        self.flow()

    def test_at_900(self):
        self.b.resize(900, 1000)
        self.b.wait("innerWidth===900")
        self.flow()


del NotesTab

if __name__ == "__main__":
    unittest.main()
