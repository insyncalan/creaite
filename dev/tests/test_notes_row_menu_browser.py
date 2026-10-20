"""#194: right-click a note in the notes column for the same menu as the open note's ... menu, in a real browser, at 1400 px and 900 px.

Run: python3 dev/tests/test_notes_row_menu_browser.py   (needs Google Chrome; skipped otherwise)

  - a right-click on a row opens a menu with the same items, in the same order, as the ... button's, for THAT row's note, with the open
    note, its unsaved typing and its state untouched (Alan, 17-10-2026: it does not open the note);
  - the context-menu key and Shift+F10 on a focused row open it too; Esc closes it with focus back on the row;
  - Mark confidential, Pin and Delete note... from a row act on that row's note only; the confirm box names it; the open note's own row
    works as before;
  - a note changed elsewhere between the menu and the pick: Pin flips the CURRENT state (not the one the menu showed), and Delete note
    is refused with the edit-conflict message (the version is the one read when the confirm box opened);
  - focus returns to the row after Cancel and Esc, and to the next row (or the list) once Delete has moved it (#255: no card); one key press (keydown plus the native contextmenu) opens one menu.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_notes_tab_browser import NotesTab  # noqa: E402,F401  (its helpers; its own tests run in their own file)

ITEMS = "[...document.querySelectorAll('%s [role=menuitem]')].map(x=>x.textContent)"
KEYS = {"ContextMenu": "{key:'ContextMenu'}", "ShiftF10": "{key:'F10',shiftKey:true}"}


class NotesRowMenuBrowser(LiveBrowserCase):
    width, height = 1400, 1000
    notes_dir, make, type_end = NotesTab.notes_dir, NotesTab.make, NotesTab.type_end

    def two_notes(self):
        """Alpha and Beta exist and are saved; Beta is open with typing that is not saved yet."""
        b = self.b
        self.make("Alpha")
        b.eval("noteFlush()")
        b.wait("noteSave.value.state==='saved'", 15)
        self.make("Beta")
        b.eval("noteFlush()")
        b.wait("noteSave.value.state==='saved'", 15)
        self.tag_rows()
        self.type_end(" UNSAVED")
        self.assertIn("UNSAVED", b.eval("document.querySelector('.nbody').textContent"))
        self.assertEqual(b.eval("noteSave.value.state"), "typing")

    def row(self, title):
        return f"[data-notetitle={json.dumps(title)}]"

    def tag_rows(self):
        self.b.eval("document.querySelectorAll('.nlist .ni').forEach(x=>x.dataset.notetitle=x.querySelector('b').textContent.replace('\\u25c6 ',''))")

    def beta_untouched(self):
        b = self.b
        self.assertEqual(b.eval("noteCur.value.note.title"), "Beta")
        self.assertEqual(b.eval("document.getElementById('noteTitle').value"), "Beta")
        self.assertIn("UNSAVED", b.eval("document.querySelector('.nbody').textContent"))
        self.assertEqual(b.eval("noteSave.value.state"), "typing")                           # and nothing was flushed

    def menu_on(self, title):
        self.b.click(self.row(title), button="right")
        self.b.wait("!!document.querySelector('.pophost [role=menu]')", 10)

    def pick(self, word):
        self.b.eval(f"[...document.querySelectorAll('.pophost [role=menuitem]')].find(x=>x.textContent.startsWith({json.dumps(word)})).click()")

    def more_items(self):
        b = self.b
        b.click(".nmorewrap .nmore")
        b.wait("!!document.querySelector('.nmorewrap [role=menu]')")
        items = b.eval(ITEMS % ".nmorewrap")
        b.key("Escape")
        b.wait("!document.querySelector('.nmorewrap [role=menu]')")
        return items

    def test_right_click_a_row_leaves_the_open_note_alone_and_esc_returns_focus(self):
        b = self.b
        self.two_notes()
        self.menu_on("Alpha")
        self.beta_untouched()                                                                # nothing opened or switched
        row_items = b.eval(ITEMS % ".pophost")
        self.assertTrue(row_items[-1].startswith("Delete note…"), row_items)
        b.key("Escape")
        b.wait("!document.querySelector('.pophost [role=menu]')")
        b.pump(0.1)
        self.assertTrue(b.eval(f"document.activeElement===document.querySelector({json.dumps(self.row('Alpha'))})"))
        self.assertLessEqual(b.eval("document.documentElement.scrollWidth-document.documentElement.clientWidth"), 0)
        self.assertEqual(row_items[:2] + row_items[3:], (lambda m: m[:2] + m[3:])(self.more_items()))                                       # the same items, in the same order
        self.beta_untouched()

    def test_keyboard_opens_it_for_the_focused_row_and_esc_returns_focus(self):
        b = self.b
        self.two_notes()
        for name, init in KEYS.items():
            b.eval(f"document.querySelector({json.dumps(self.row('Alpha'))}).focus()")
            b.eval(f"document.activeElement.dispatchEvent(new KeyboardEvent('keydown',Object.assign({{bubbles:true,cancelable:true}},{init})))")
            b.wait("!!document.querySelector('.pophost [role=menu]')", 10)
            self.beta_untouched()
            self.assertEqual(b.eval("document.activeElement.getAttribute('role')"), "menuitem", name)
            b.key("Escape")
            b.wait("!document.querySelector('.pophost [role=menu]')")
            b.pump(0.1)
            self.assertTrue(b.eval(f"document.activeElement===document.querySelector({json.dumps(self.row('Alpha'))})"), name)

    def test_each_action_acts_on_the_row_note_not_the_open_one(self):
        b = self.b
        self.two_notes()
        alpha, beta = self.notes_dir() / "Alpha.md", self.notes_dir() / "Beta.md"
        self.menu_on("Alpha")
        self.pick("Mark confidential")
        b.wait("notesList.value.find(n=>n.title==='Alpha').confidential===true", 15)
        self.assertIn("confidential: true", alpha.read_text())
        self.assertNotIn("confidential: true", beta.read_text())
        self.beta_untouched()
        self.menu_on("Alpha")
        self.assertTrue(b.eval(ITEMS % ".pophost")[1].startswith("Not confidential"))        # the row menu knows Alpha's state
        self.pick("Pin")
        b.wait("notesList.value.find(n=>n.title==='Alpha').pinned===true", 15)
        self.assertIn("pinned: true", alpha.read_text())
        self.assertNotIn("pinned: true", beta.read_text())
        self.beta_untouched()
        self.tag_rows()
        self.menu_on("Alpha")
        self.pick("Delete note")
        b.wait("document.getElementById('noteDelDlg').open")
        self.assertEqual(b.eval("document.getElementById('ndelH').textContent"), "Delete “Alpha”?")
        self.assertEqual(b.eval("noteSave.value.state"), "typing")                           # the confirm box did not save the open note
        b.click("#ndelCancel")
        b.wait("!document.getElementById('noteDelDlg').open")
        self.beta_untouched()
        self.menu_on("Beta")                                                                 # the open note's own row: today's behaviour
        self.pick("Delete note")
        b.wait("document.getElementById('noteDelDlg').open")
        self.assertEqual(b.eval("document.getElementById('ndelH').textContent"), "Delete “Beta”?")


    def elsewhere(self, title, flag=None, body=None):
        """Another tab (or an autosave) changes the note's file on disk."""
        f = self.notes_dir() / f"{title}.md"
        t = f.read_text()
        if flag:
            self.assertIn(f"{flag}: false", t)
            t = t.replace(f"{flag}: false", f"{flag}: true", 1)
        if body:
            t = t.rstrip("\n") + "\n" + body + "\n"
        f.write_text(t)

    def on_row(self, title):
        self.b.pump(0.2)
        return self.b.eval(f"document.activeElement===document.querySelector({json.dumps(self.row(title))})")

    def test_a_flag_changed_elsewhere_is_flipped_from_the_current_state(self):
        b = self.b
        self.two_notes()
        alpha = self.notes_dir() / "Alpha.md"
        self.menu_on("Alpha")
        self.assertTrue(b.eval(ITEMS % ".pophost")[0].startswith("Pin"))                     # the menu was built on "not pinned"
        self.elsewhere("Alpha", flag="pinned")                                         # ... then another tab pinned it
        self.pick("Pin")
        for _ in range(100):
            if "pinned: true" not in alpha.read_text():
                break
            b.pump(0.1)
        self.assertNotIn("pinned: true", alpha.read_text())                                   # it flipped the current (pinned) state to unpinned
        self.beta_untouched()

    def test_delete_of_a_row_changed_elsewhere_after_the_box_opened_is_refused(self):
        b = self.b
        self.two_notes()
        alpha = self.notes_dir() / "Alpha.md"
        self.menu_on("Alpha")
        self.pick("Delete note")
        b.wait("document.getElementById('noteDelDlg').open")
        self.elsewhere("Alpha", body="Typed in another tab")
        b.click("#ndelGo")
        b.wait("!document.getElementById('noteDelDlg').open", 15)
        b.wait("document.querySelector('.snack')&&document.querySelector('.snack').textContent.includes('the note changed since you opened it')", 15)
        self.assertEqual(b.eval("document.querySelectorAll('#chLog .edcard').length"), 0)   # no card: nothing is moved
        self.assertTrue(alpha.is_file())
        self.assertIn("Typed in another tab", alpha.read_text())
        self.beta_untouched()

    def test_focus_returns_to_the_row_after_cancel_esc_and_delete(self):
        b = self.b
        self.two_notes()
        self.menu_on("Alpha")
        self.pick("Delete note")
        b.wait("document.getElementById('noteDelDlg').open")
        b.click("#ndelCancel")
        b.wait("!document.getElementById('noteDelDlg').open")
        self.assertTrue(self.on_row("Alpha"), "Cancel returns focus to the row")
        self.menu_on("Alpha")
        self.pick("Delete note")
        b.wait("document.getElementById('noteDelDlg').open")
        b.key("Escape")
        b.wait("!document.getElementById('noteDelDlg').open")
        self.assertTrue(self.on_row("Alpha"), "Esc returns focus to the row")
        self.menu_on("Alpha")
        self.pick("Delete note")
        b.wait("document.getElementById('noteDelDlg').open")
        b.click("#ndelGo")                                                                     # #255: moved at once, no card
        b.wait("!notesList.value.some(n=>n.title==='Alpha')", 20)
        self.assertEqual(b.eval("document.querySelectorAll('#chLog .edcard').length"), 0)
        b.pump(0.3)
        self.assertTrue(b.eval("document.activeElement.classList.contains('ni')||document.activeElement.id==='notesListBody'"),
                        b.eval("document.activeElement.tagName"))                              # the next row or the list, never lost to the page

    def test_one_key_press_opens_one_menu(self):
        b = self.b
        self.two_notes()
        b.eval(f"document.querySelector({json.dumps(self.row('Alpha'))}).focus()")
        b.eval("document.activeElement.dispatchEvent(new KeyboardEvent('keydown',{key:'ContextMenu',bubbles:true,cancelable:true}))")
        b.eval("document.activeElement.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true}))")   # the browser's own event for the same key
        b.wait("!!document.querySelector('.pophost [role=menu]')", 10)
        b.pump(0.2)
        self.assertEqual(b.eval("document.querySelectorAll('.pophost').length"), 1)
        self.assertEqual(b.eval("document.querySelectorAll('.pophost [role=menu]').length"), 1)
        b.key("Escape")
        b.wait("!document.querySelector('.pophost')")


class NotesRowMenuBrowser900(NotesRowMenuBrowser):
    width, height = 900, 900


if __name__ == "__main__":
    unittest.main()
