"""#175 (page half): Notes undo and redo one change at a time, in the editor, in a real browser against the real live server.

Run: python3 dev/tests/test_notes_undo_browser.py   (needs Google Chrome; skipped otherwise)

Design r3 section 4 (dev/proposals/notes-175/design-r3.md). The editor's own history (⌘Z, ⌘⇧Z), made finer by the undo-steps extension
(core/undoSteps.js):
  - delete a line, then retype at once: ⌘Z takes back only the retype, a second brings the line back;
  - several undos go one change at a time and stop at the text the note opened with; redo puts them back in order, and typing
    after an undo clears redo;
  - an autosave never touches the editor (same view, history intact); an undo and a redo are saved like any edit, in the same
    session (same id, one backup);
  - switching notes and back keeps the history in the page when the file is unchanged, and drops it when it was changed outside
    creaite; a reload starts empty (nothing is kept in browser storage);
  - a paste, a picker choice and an AI replacement are one step each.
Each test fails with its piece taken out: 1 and 7 (paste, picker, AI) without that extension; 4 and 5 if a save rebuilds the editor;
6 without the in-memory history of closed notes. 2 and 3 pin the plain behaviour (pauses between bursts) that must not regress.
"""
import json
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
import test_notes_tab_browser as notes_tab_browser  # noqa: E402
from test_notes_autosave_page import SPY, NO_GUARD  # noqa: E402

META, SHIFT = 4, 8
MOD = META if sys.platform == "darwin" else 2      # the editor's Mod key: ⌘ on a Mac, Ctrl elsewhere (CI runs on Linux)
ED = "document.querySelector('.nbody').cxed.editor"
TEXT = ED + ".getText({blockSeparator:'|'})"


class NotesUndo(LiveBrowserCase):
    width, height = 1400, 1000
    log, notes_dir, make, type_end = (notes_tab_browser.NotesTab.log, notes_tab_browser.NotesTab.notes_dir, notes_tab_browser.NotesTab.make,
                                      notes_tab_browser.NotesTab.type_end)

    # ---- helpers ----
    def text(self):
        return self.b.eval(TEXT)

    def undo(self):
        self.b.key("z", MOD)

    def redo(self):
        self.b.key("z", MOD | SHIFT)

    def burst(self, text):
        """Type a burst, then pause past the history's 500 ms grouping, so it is a step of its own."""
        self.type_end(text)
        self.b.pump(0.7)

    def focus_end(self):
        self.b.eval("document.querySelector('.nbody').cxed.focus('end')")
        self.b.wait("document.activeElement===document.querySelector('.nbody')", 5)

    def wait_text(self, f, text, secs=10):
        t0 = time.monotonic()
        while time.monotonic() - t0 < secs:
            if f.is_file() and text in f.read_text():
                return
            self.b.pump(0.05)
        self.fail(f"{text!r} never reached {f.name}: {f.read_text() if f.is_file() else 'no file'}")

    def edits(self, since=0):
        return [e for e in self.log()[since:] if e.get("op") == "edit"]

    def open_note(self, path):
        b = self.b
        b.eval(f"openNote({json.dumps(path)})")
        b.wait(f"noteCur.value&&noteCur.value.path==={json.dumps(path)}&&!!document.querySelector('.nbody.ProseMirror')", 10)

    def switch_away_and_back(self, other_title):
        b = self.b
        path = b.eval("noteCur.value.path")
        other = b.eval(f"notesList.value.find(n=>n.title==={json.dumps(other_title)}).path")
        self.open_note(other)
        self.open_note(path)
        return path

    # ---- 1 to 3: the steps ----
    def test_delete_a_line_then_retype_at_once_is_two_steps(self):
        self.make("Retype")
        self.burst("First line")
        for _ in range(len("First line")):                                           # delete it, then retype at once (under 500 ms a key)
            self.b.key("Backspace")
        self.b.type("Second")
        self.assertEqual(self.text(), "Second")
        self.undo()
        self.assertEqual(self.text(), "", "one undo takes back only the retype")
        self.undo()
        self.assertEqual(self.text(), "First line", "a second brings the line back")

    def test_several_undos_go_one_change_at_a_time_and_stop_at_the_opened_text(self):
        self.make("Several", "stakeholder")
        opened = self.text()
        self.assertTrue(opened.strip(), "a template note opens with text")
        self.burst("alpha")
        self.burst(" beta")
        self.burst(" gamma")
        full = self.text()
        self.assertTrue(full.endswith("alpha beta gamma"))
        for want in ("alpha beta", "alpha"):
            self.undo()
            self.assertTrue(self.text().endswith(want), (self.text(), want))
        for _ in range(4):
            self.undo()
        self.assertEqual(self.text(), opened, "more undos stop at the opened text, never an empty note")

    def test_redo_puts_the_steps_back_in_order_and_typing_clears_it(self):
        self.make("Redo")
        self.burst("one")
        self.burst(" two")
        self.burst(" three")
        for _ in range(3):
            self.undo()
        self.assertEqual(self.text(), "")
        for want in ("one", "one two", "one two three"):
            self.redo()
            self.assertEqual(self.text(), want)
        self.undo()
        self.undo()
        self.assertTrue(self.b.eval(ED + ".can().redo()"))
        self.type_end("new")
        self.assertFalse(self.b.eval(ED + ".can().redo()"), "typing after an undo clears redo")

    # ---- 4 and 5: an autosave never resets the history ----
    def test_undo_and_redo_after_an_autosave_tick_in_the_same_session(self):
        b = self.b
        self.make("Autosave undo")
        f = self.notes_dir() / "Autosave undo.md"
        n = len(self.log())
        b.eval(SPY)
        b.eval("window.__view = " + ED + ".view; true")
        self.burst("kept")
        self.burst(" more")
        self.wait_text(f, "kept more")
        b.wait("noteSave.value.state==='saved'", 10)
        self.assertTrue(b.eval(ED + ".view===window.__view"), "a save does not rebuild the editor")
        self.assertTrue(b.eval(ED + ".can().undo()"), "the history survives the save")
        self.undo()
        self.assertEqual(self.text(), "kept")
        b.wait("noteSave.value.state==='typing'||noteSave.value.state==='saving'||noteSave.value.state==='saved'", 5)
        t0 = time.monotonic()
        while time.monotonic() - t0 < 10 and "more" in f.read_text():
            b.pump(0.1)
        self.assertNotIn("kept more", f.read_text(), "the undone text is autosaved")
        b.wait("noteSave.value.state==='saved'", 10)
        self.assertTrue(b.eval(ED + ".view===window.__view"))
        self.assertTrue(b.eval(ED + ".can().redo()"), "redo is still there after the autosave of the undo")
        self.redo()
        self.assertEqual(self.text(), "kept more")
        self.wait_text(f, "kept more")
        b.wait("noteSave.value.state==='saved'", 10)
        saves = b.eval("window.__saves")
        self.assertGreaterEqual(len(saves), 3)
        self.assertEqual(len({s["session"] for s in saves}), 1, "the undo and the redo are saved in the same session")
        for _ in range(40):
            if len(self.edits(n)) >= len(saves):
                break
            b.pump(0.1)
        self.assertEqual(len({e["backup"] for e in self.edits(n)}), 1, "one backup for the session")

    def test_redo_survives_a_title_rename_and_a_pinned_toggle(self):
        b = self.b
        self.make("Rename undo")
        b.eval("window.__view = " + ED + ".view; true")
        self.burst("one")
        self.burst(" two")
        self.undo()
        self.assertEqual(self.text(), "one")
        b.eval("(()=>{ const t=document.getElementById('noteTitle'); t.focus(); t.value='Renamed undo'; t.dispatchEvent(new Event('input',{bubbles:true})); t.blur(); return true; })()")
        b.wait("noteCur.value.note.title==='Renamed undo'", 15)
        b.eval("noteMeta({pinned:true},true)")
        b.wait("noteSave.value.state==='saved'", 15)
        b.pump(0.5)
        self.assertTrue(b.eval(ED + ".view===window.__view"), "a rename and a toggle keep the same editor")
        self.assertTrue(b.eval(ED + ".can().redo()"))
        self.focus_end()
        self.redo()
        self.assertEqual(self.text(), "one two")

    # ---- 6: reopen and reload ----
    def test_switching_notes_and_back_keeps_the_history_only_when_the_file_is_unchanged(self):
        b = self.b
        self.make("Other")
        self.make("Reopen")
        f = self.notes_dir() / "Reopen.md"
        self.burst("first")
        self.burst(" second")
        self.undo()
        self.assertEqual(self.text(), "first")
        self.switch_away_and_back("Other")
        self.wait_text(f, "first")
        self.assertEqual(self.text(), "first")
        self.assertTrue(b.eval(ED + ".can().redo()"), "the redo is kept too")
        self.focus_end()
        self.undo()
        self.assertEqual(self.text(), "", "after switching back, Cmd+Z undoes the last change")
        self.redo()
        self.assertEqual(self.text(), "first")
        b.wait("noteSave.value.state==='saved'||noteSave.value.state==='typing'", 10)
        # the file is changed outside creaite meanwhile: nothing to undo, and the text is the file's
        self.burst(" third")
        b.wait("noteSave.value.state==='saved'", 10)
        path = b.eval("noteCur.value.path")
        other = b.eval("notesList.value.find(n=>n.title==='Other').path")
        self.open_note(other)
        f.write_text(f.read_text().replace("first third", "first changed elsewhere"))
        self.open_note(path)
        self.assertIn("first changed elsewhere", self.text())
        self.assertFalse(b.eval(ED + ".can().undo()"), "a file changed outside creaite: no history")
        self.assertFalse(b.eval(ED + ".can().redo()"))

    def test_a_reload_starts_with_nothing_to_undo(self):
        b = self.b
        self.make("Reload")
        f = self.notes_dir() / "Reload.md"
        self.burst("kept")
        self.wait_text(f, "kept")
        b.wait("noteSave.value.state==='saved'", 10)
        self.assertTrue(b.eval(ED + ".can().undo()"))
        b.eval(NO_GUARD)
        b.reload("typeof go==='function' && LIVE")
        b.eval("go('notes','ABC')")
        b.wait("!!document.getElementById('notesNew')")
        path = [p for p in b.eval("notesList.value.map(n=>n.path)") if p.endswith("Reload.md")][0]
        self.open_note(path)
        self.assertIn("kept", self.text())
        self.assertFalse(b.eval(ED + ".can().undo()"), "a reload loses the history")
        self.assertEqual(b.eval("JSON.stringify([Object.keys(localStorage),Object.keys(sessionStorage)]).includes('kept')"), False)

    # ---- 7: paste, a picker choice and an AI replacement ----
    def test_paste_is_one_step(self):
        b = self.b
        self.make("Paste")
        self.type_end("typed")                                                        # no pause: a paste right after still starts its own step
        b.eval("(()=>{ const dt=new DataTransfer(); dt.setData('text/plain',' pasted text'); "
               "document.querySelector('.nbody .ProseMirror, .nbody.ProseMirror').dispatchEvent(new ClipboardEvent('paste',{clipboardData:dt,bubbles:true,cancelable:true})); return true; })()")
        self.assertEqual(self.text(), "typed pasted text")
        b.type("!")                                                                   # and what is typed after it is another
        self.undo()
        self.assertEqual(self.text(), "typed pasted text", "the typing after the paste is its own step")
        self.undo()
        self.assertEqual(self.text(), "typed", "one undo takes back the whole paste")
        self.undo()
        self.assertEqual(self.text(), "")

    def test_a_picker_choice_is_one_step(self):
        b = self.b
        self.make("Zeta target")
        b.eval("go('cockpit','ABC')")
        self.make("Picker")
        self.type_end("see [[Zet")
        b.wait("!!document.getElementById('ntpick')&&document.querySelectorAll('#ntpick [role=option]').length>0", 10)
        b.key("Enter")
        self.assertIn("[[Zeta target]]", self.text())
        self.undo()
        self.assertEqual(self.text(), "see [[Zet", "one undo takes back the chosen link, not the typing before it")
        self.undo()
        self.assertEqual(self.text(), "")

    def test_an_ai_replacement_is_one_step(self):
        b = self.b
        self.make("AI step")
        self.type_end("Sandbox access granted yesterday.")
        b.eval("(()=>{ const h=document.querySelector('.nbody').cxed; h.editor.commands.selectAll(); const ed=h.editor, r={from:1,to:ed.state.doc.content.size-1,text:'Sandbox access granted yesterday.',inline:true}; "
               "aiSug.value={status:'ready',h,range:r,text:'Clearly: Sandbox access granted yesterday.',notes:[],label:'Rewrite',ai:{place:'notes'}}; return true; })()")
        b.wait("!!document.querySelector('#aiLayer .aisug [data-aifirst]')", 5)
        b.click("#aiLayer .aisug [data-aifirst]")
        self.assertEqual(self.text(), "Clearly: Sandbox access granted yesterday.")
        self.undo()
        self.assertEqual(self.text(), "Sandbox access granted yesterday.", "one undo puts the whole text back")
        self.undo()
        self.assertEqual(self.text(), "")


if __name__ == "__main__":
    unittest.main()
