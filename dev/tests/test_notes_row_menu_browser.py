"""#194: right-click a note in the notes column for the same menu as the open note's ... menu, in a real browser, at 1400 px and 900 px.

Run: python3 dev/tests/test_notes_row_menu_browser.py   (needs Google Chrome; skipped otherwise)

  - a right-click on a row opens that note and a menu with the same items, in the same order, as the ... button's;
  - the context-menu key and Shift+F10 on a focused row open it too; Esc closes it with focus back on the row;
  - Mark confidential from the row menu is written to the note's file; the ... menu then says "Not confidential";
  - Delete note... from the row menu opens the same confirm box.
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
    notes_dir, make = NotesTab.notes_dir, NotesTab.make

    def two_notes(self):
        b = self.b
        self.make("Alpha")
        b.eval("noteFlush()")
        b.wait("noteSave.value.state==='saved'", 15)
        self.make("Beta")
        b.eval("noteFlush()")
        b.wait("noteSave.value.state==='saved'", 15)

    def row(self, title):
        return f"[data-notetitle={json.dumps(title)}]"

    def tag_rows(self):
        self.b.eval("document.querySelectorAll('.nlist .ni').forEach(x=>x.dataset.notetitle=x.querySelector('b').textContent.replace('\\u25c6 ',''))")

    def more_items(self):
        b = self.b
        b.click(".nmorewrap .nmore")
        b.wait("!!document.querySelector('.nmorewrap [role=menu]')")
        items = b.eval(ITEMS % ".nmorewrap")
        b.key("Escape")
        b.wait("!document.querySelector('.nmorewrap [role=menu]')")
        return items

    def test_right_click_opens_the_same_menu_and_esc_returns_focus(self):
        b = self.b
        self.two_notes()
        self.tag_rows()
        b.click(self.row("Alpha"), button="right")
        b.wait("noteCur.value&&noteCur.value.note.title==='Alpha'&&!!document.querySelector('.pophost [role=menu]')", 10)
        row_items = b.eval(ITEMS % ".pophost")
        self.assertTrue(row_items[-1].startswith("Delete note…"), row_items)
        b.key("Escape")
        b.wait("!document.querySelector('.pophost [role=menu]')")
        b.pump(0.1)
        self.assertEqual(b.eval("document.activeElement.querySelector('b')&&document.activeElement.querySelector('b').textContent"), "Alpha")
        self.assertLessEqual(b.eval("document.documentElement.scrollWidth-document.documentElement.clientWidth"), 0)
        self.assertEqual(row_items, self.more_items())                                       # the same items, in the same order

    def test_keyboard_opens_it_and_esc_returns_focus(self):
        b = self.b
        self.two_notes()
        self.tag_rows()
        for name, init in KEYS.items():
            b.eval(f"document.querySelector({json.dumps(self.row('Alpha'))}).focus()")
            b.eval(f"document.activeElement.dispatchEvent(new KeyboardEvent('keydown',Object.assign({{bubbles:true,cancelable:true}},{init})))")
            b.wait("!!document.querySelector('.pophost [role=menu]')", 10)
            self.assertEqual(b.eval("noteCur.value.note.title"), "Alpha", name)
            self.assertEqual(b.eval("document.activeElement.getAttribute('role')"), "menuitem", name)
            b.key("Escape")
            b.wait("!document.querySelector('.pophost [role=menu]')")
            b.pump(0.1)
            self.assertTrue(b.eval(f"document.activeElement===document.querySelector({json.dumps(self.row('Alpha'))})"), name)

    def test_picks_act_on_the_row_note(self):
        b = self.b
        self.two_notes()
        self.tag_rows()
        b.click(self.row("Alpha"), button="right")
        b.wait("!!document.querySelector('.pophost [role=menu]')", 10)
        b.eval("[...document.querySelectorAll('.pophost [role=menuitem]')].find(x=>x.textContent.startsWith('Mark confidential')).click()")
        b.wait("noteSave.value.state==='saved'&&noteCur.value.meta.confidential===true", 15)
        self.assertIn("confidential: true", (self.notes_dir() / "Alpha.md").read_text())
        self.assertNotIn("confidential: true", (self.notes_dir() / "Beta.md").read_text())
        self.assertTrue(self.more_items()[1].startswith("Not confidential"))
        b.click(self.row("Alpha"), button="right")
        b.wait("!!document.querySelector('.pophost [role=menu]')", 10)
        b.eval("[...document.querySelectorAll('.pophost [role=menuitem]')].find(x=>x.textContent.startsWith('Delete note')).click()")
        b.wait("document.getElementById('noteDelDlg').open")
        self.assertEqual(b.eval("document.getElementById('ndelH').textContent"), "Delete “Alpha”?")


class NotesRowMenuBrowser900(NotesRowMenuBrowser):
    width, height = 900, 900


if __name__ == "__main__":
    unittest.main()
