"""BL-301 B (v20-notes-tab): the Notes tab in a real browser against the real live server.

Run: python3 dev/tests/test_notes_tab_browser.py   (needs Google Chrome; skipped otherwise)

Done when (BL-301 B, #119): a note is created, edited and autosaved (about 2 s after the last key; no draft step) through filechange.py (undoable) in the notes folder; the list
collapses and stays collapsed after a reload; links, backlinks and item chips work; the peek says which notes mention an item.
Also: the project page's tabs, keyboard and screen-reader names, and nothing scrolls sideways at 320 px.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

META = 4


class NotesTab(LiveBrowserCase):
    width, height = 1400, 1000

    def log(self):
        p = self.v.root / "system/config/files-log.jsonl"
        return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []

    def notes_dir(self):
        return next((self.v.root / "projects").glob("ABC */")) / "notes"

    def make(self, title, tpl="blank"):
        b = self.b
        b.eval("go('notes','ABC')")
        b.wait("!!document.getElementById('notesNew')")
        b.click("#notesNew")
        b.wait("document.getElementById('newNoteDlg').open")
        b.eval(f"(()=>{{ const i=document.getElementById('nnTitle'); i.value={json.dumps(title)}; i.dispatchEvent(new Event('input',{{bubbles:true}})); }})()")
        b.eval(f"document.querySelector('#newNoteDlg input[value=\"{tpl}\"]').click()")
        b.click("#nnMake")
        b.wait(f"noteCur.value&&noteCur.value.note.title==={json.dumps(title)}&&!!document.querySelector('.nbody.ProseMirror')", 15)

    def type_end(self, text):
        self.b.eval("document.querySelector('.nbody').cxed.focus('end')")
        self.b.wait("document.activeElement===document.querySelector('.nbody')", 5)
        self.b.type(text)

    def test_tabs_and_a_note_made_typed_and_saved_by_itself(self):
        b = self.b
        b.eval("go('cockpit','ABC')")
        b.wait("!!document.querySelector('#cockTabs [role=tab]')")
        tabs = b.eval("[...document.querySelectorAll('#cockTabs [role=tab]')].map(t=>[t.textContent,t.getAttribute('aria-selected')])")
        self.assertEqual(tabs, [["Overview", "true"], ["Notes", "false"]])
        b.click("#cockTabs [data-tab=notes]")
        b.wait("VIEW==='notes'&&location.hash.startsWith('#notes=ABC')")
        self.make("Data access", "stakeholder")
        self.assertEqual(b.eval("document.querySelector('.nbody').cxed.features"), "notes")
        self.assertTrue(b.eval("document.querySelector('.nbody').isContentEditable"))     # no Edit button
        f = self.notes_dir() / "Data access.md"
        self.assertTrue(f.is_file())
        self.assertIn("## Role and influence", f.read_text())
        n = len(self.log())
        self.type_end("Sara signs off security.")
        self.assertNotIn("Sara signs off", f.read_text())                                # not yet: the file follows about 2 s after the last key
        for _ in range(100):                                                              # then it is written by itself: no leaving, no draft step
            if "Sara signs off security." in f.read_text():
                break
            b.pump(0.1)
        self.assertIn("Sara signs off security.", f.read_text())
        b.wait("noteSave.value.state==='saved'", 10)
        for _ in range(50):                                                               # the log line follows the file by a moment
            edits = [e for e in self.log()[n:] if e.get("op") == "edit"]
            if edits:
                break
            b.pump(0.1)
        self.assertEqual(len(edits), 1)
        self.assertEqual(edits[0]["via"], "dashboard")
        self.assertIn("updated:", f.read_text())
        b.eval("go('today')")                                                             # leaving with nothing new writes nothing more
        b.pump(0.5)
        self.assertEqual(len([e for e in self.log()[n:] if e.get("op") == "edit"]), 1)

    def test_list_collapses_and_stays_collapsed(self):
        b = self.b
        self.make("First")
        self.assertEqual(b.eval("document.getElementById('notesCollapse').getAttribute('aria-expanded')"), "true")
        b.eval("document.body.focus()")
        b.key("\\", META)
        b.wait("document.getElementById('notesSplit').classList.contains('collapsed')")
        self.assertEqual(b.eval("document.getElementById('notesCollapse').getAttribute('aria-label')"), "Show the notes list")
        b.reload("typeof go==='function' && LIVE")
        b.wait("VIEW==='notes'&&!!document.getElementById('notesSplit')", 15)
        self.assertTrue(b.eval("document.getElementById('notesSplit').classList.contains('collapsed')"))
        b.click("#notesCollapse")
        b.wait("!document.getElementById('notesSplit').classList.contains('collapsed')")

    def test_pickers_chips_backlinks_and_the_peek(self):
        b = self.b
        item = b.eval("A.find(a=>a.p==='ABC').id")
        self.make("Target note")
        b.eval("go('cockpit','ABC')")
        self.make("Linking note")
        self.type_end("See [[Targ")
        b.wait("!!document.querySelector('#ntpick [role=option]')")
        self.assertEqual(b.eval("document.querySelector('.nbody').getAttribute('aria-activedescendant')"),
                         b.eval("document.querySelector('#ntpick [aria-selected=true]').id"))
        b.key("Enter")
        b.type(" and #" + item)                                                             # the whole ID: Enter picks an exact ID without an arrow (a prefix shared by several items does not)
        b.wait(f"!!document.querySelector('#ntpick [role=option]')&&document.querySelector('#ntpick').textContent.includes({json.dumps(item)})")
        b.key("Enter")
        b.wait(f"!!document.querySelector('.nbody .nchip[data-item={json.dumps(item)}]')")
        self.assertTrue(b.eval("!!document.querySelector('.nbody .wl:not(.missing)[data-wl=\"Target note\"]')"))
        b.eval("noteFlush()")
        b.wait("noteSave.value.state==='saved'", 15)
        text = (self.notes_dir() / "Linking note.md").read_text()
        self.assertIn("[[Target note]]", text)
        self.assertRegex(text, rf"\[{item} · (Action|Risk|Issue|Assumption|Dependency|Decision): [^\]]*\]\(creaite:item/{item}\)")      # #122 C: 'ID · Designation: title'; the address is unchanged
        self.assertIn(item, b.eval("document.querySelector('.nctx').textContent"))           # Linked work
        b.click(".nlist .ni:not(.on)")                                                       # open Target note
        b.wait("noteCur.value&&noteCur.value.note.title==='Target note'")
        b.wait("document.querySelector('.nctx').textContent.includes('Linking note')")       # Mentioned in
        b.eval(f"openRecord('actions',{json.dumps(item)})")
        b.wait("!!document.querySelector('#pkNotes .pk-notes')")
        self.assertIn("1 note mentions this", b.eval("document.querySelector('#pkNotes').textContent"))

    def test_narrow_screen_has_no_sideways_scroll(self):
        b = self.b
        self.make("Narrow")
        b.eval("closePanel&&closePanel(true)")
        b.resize(320, 800)
        b.wait("document.documentElement.clientWidth<=320")
        b.pump(0.3)
        self.assertLessEqual(b.eval("document.documentElement.scrollWidth-document.documentElement.clientWidth"), 0)


if __name__ == "__main__":
    unittest.main()
