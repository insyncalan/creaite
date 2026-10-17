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

    def test_a_file_changed_outside_with_the_same_text_has_no_history(self):
        """The text matches but the file does not (its front matter changed outside creaite): the stash's base is not the file's, so no history."""
        b = self.b
        self.make("Other base")
        self.make("Base check")
        f = self.notes_dir() / "Base check.md"
        self.burst("same")
        self.burst(" text")
        self.wait_text(f, "same text")
        b.wait("noteSave.value.state==='saved'", 10)
        path = b.eval("noteCur.value.path")
        other = b.eval("notesList.value.find(n=>n.title==='Other base').path")
        self.open_note(other)
        old = f.read_text()
        self.assertTrue(old.startswith("---\n"), old)
        f.write_text(old.replace("---\n", "---\nseen_elsewhere: yes\n", 1))
        self.open_note(path)
        self.assertEqual(self.text(), "same text", "the text the editor opens with is the same")
        self.assertFalse(b.eval(ED + ".can().undo()"), "a file changed outside creaite, even with the same text: no history")
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
        b.wait("%s==='see [[Zet'" % TEXT, 10)
        b.wait("(document.querySelector('#ntpick [role=option][aria-selected=true]')||{textContent:''}).textContent.includes('Zeta target')", 10)
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

    # ---- a block put in at the end is one undo: the editor's own follow-up changes (the trailing paragraph, the link scrub) are not steps ----
    def block_case(self, title, do, expect_text=None):
        """Type a line, pause, run `do` (JS), then one undo must give back exactly the document from before it, and a second the empty note."""
        b = self.b
        self.make(title)
        self.burst("hello")
        before = b.eval("JSON.stringify(" + ED + ".getJSON())")
        b.eval(do)
        b.pump(0.1)
        self.assertNotEqual(b.eval("JSON.stringify(" + ED + ".getJSON())"), before, "the block went in")
        self.undo()
        self.assertEqual(b.eval("JSON.stringify(" + ED + ".getJSON())"), before, "one undo removes the whole block, no stray paragraph left")
        self.undo()
        self.assertEqual(self.text(), "")

    def test_a_table_from_a_command_is_one_undo(self):
        self.block_case("Table cmd", ED + ".chain().focus('end').setMeta('cxStep',true).insertTable({rows:3,cols:3,withHeaderRow:true}).run()")

    def test_a_pasted_table_at_the_end_is_one_undo(self):
        self.block_case("Table paste", "(()=>{ const dt=new DataTransfer(); dt.setData('text/html','<table><tr><th>a</th><th>b</th></tr><tr><td>1</td><td>2</td></tr></table>'); "
                        "document.querySelector('.nbody').dispatchEvent(new ClipboardEvent('paste',{clipboardData:dt,bubbles:true,cancelable:true})); return true; })()")

    def test_a_template_or_ai_replacement_ending_in_a_block_is_one_undo(self):
        self.block_case("Block md", ED + ".chain().focus('end').setMeta('cxStep',true).insertContent('## Heading\\n\\n- a\\n- b\\n\\n| x | y |\\n|---|---|\\n| 1 | 2 |', {contentType:'markdown'}).run()")

    def test_a_link_the_guard_scrubs_is_one_undo(self):
        self.block_case("Link scrub", ED + ".chain().focus('end').setMeta('cxStep',true).insertContent([{type:'text',text:'bad link',marks:[{type:'link',attrs:{href:'javascript:alert(1)'}}]},"
                        "{type:'text',text:' tail'}]).run()")

    def test_a_slash_menu_table_is_one_undo(self):
        b = self.b
        self.make("Slash table")
        self.burst("hello")
        self.burst(" /table")
        b.wait("!!document.querySelector('.slashmenu [role=option], [role=listbox] [role=option]')", 10)
        b.key("ArrowDown")
        b.key("ArrowUp")
        b.key("Enter")
        b.wait("!!document.querySelector('.nbody table')", 10)
        self.undo()
        self.assertEqual(self.text(), "hello /table", "one undo takes the table and the deleted /table together")
        self.assertFalse(b.eval("!!document.querySelector('.nbody table')"))
        self.undo()
        self.assertEqual(self.text(), "hello")

    # ---- the history belongs to the note, whatever its title does or whatever happens to its file ----
    def test_a_rename_then_switching_away_and_back_keeps_the_history(self):
        b = self.b
        self.make("Other two")
        self.make("Rename keep")
        self.burst("first")
        self.burst(" second")
        b.eval("(()=>{ const t=document.getElementById('noteTitle'); t.focus(); t.value='Renamed keep'; t.dispatchEvent(new Event('input',{bubbles:true})); t.blur(); return true; })()")
        b.wait("noteCur.value.note.title==='Renamed keep'&&noteCur.value.path.endsWith('Renamed keep.md')", 15)
        b.wait("noteSave.value.state==='saved'", 15)
        self.switch_away_and_back("Other two")
        b.wait("noteCur.value.note.title==='Renamed keep'", 10)
        self.assertEqual(self.text(), "first second")
        self.focus_end()
        self.undo()
        self.assertEqual(self.text(), "first", "after a rename and a switch, Cmd+Z still undoes")

    def test_a_note_deleted_and_made_again_with_the_same_text_has_no_history(self):
        b = self.b
        self.make("Other three")
        self.make("Gone and back")
        f = self.notes_dir() / "Gone and back.md"
        self.burst("same")
        self.burst(" text")
        self.undo()
        self.wait_text(f, "same")
        b.wait("noteSave.value.state==='saved'", 10)
        path = b.eval("noteCur.value.path")
        other = b.eval("notesList.value.find(n=>n.title==='Other three').path")
        self.open_note(other)
        self.assertEqual(b.eval("noteGone(%s)" % json.dumps(path)), None)                # archived or deleted: the page forgets it
        self.open_note(path)
        self.assertEqual(self.text(), "same")
        self.assertFalse(b.eval(ED + ".can().undo()"), "a note of the same name does not inherit the old history")
        self.assertFalse(b.eval(ED + ".can().redo()"))

    def test_the_undone_steps_come_back_as_redo_after_switching(self):
        self.make("Other four")
        self.make("Two branches")
        self.burst("one")
        self.burst(" two")
        self.burst(" three")
        self.undo()
        self.undo()
        self.assertEqual(self.text(), "one")
        self.switch_away_and_back("Other four")
        self.focus_end()
        self.redo()
        self.assertEqual(self.text(), "one two", "the redo branch is the one that was undone, in order")
        self.redo()
        self.assertEqual(self.text(), "one two three")
        self.undo()
        self.undo()
        self.undo()
        self.assertEqual(self.text(), "")

    # ---- a slash row that puts nothing in leaves nothing pending ----
    def slash_row(self, text, row_wait="!!document.querySelector('.slashmenu [role=option]')"):
        b = self.b
        self.burst("hello")
        self.burst(text)
        b.wait(row_wait, 10)
        b.key("Enter")

    def paste_text(self, text):
        self.b.eval("(()=>{ const dt=new DataTransfer(); dt.setData('text/plain',%s); document.querySelector('.nbody').dispatchEvent(new ClipboardEvent('paste',{clipboardData:dt,bubbles:true,cancelable:true})); return true; })()" % json.dumps(text))
        self.b.pump(0.2)

    def test_a_cancelled_image_row_does_not_pull_a_later_paste_into_its_step(self):
        b = self.b
        self.make("Image cancel")
        self.slash_row(" /image")
        b.eval("document.querySelector('.nimgfile').dispatchEvent(new Event('cancel'))")          # the file picker was cancelled
        b.pump(1.5)
        self.assertEqual(self.text(), "hello ")
        self.focus_end()
        self.paste_text("PASTED")
        self.assertEqual(self.text(), "hello PASTED")
        self.undo()
        self.assertEqual(self.text(), "hello ", "one undo takes back only the paste")

    def test_a_cancelled_image_row_does_not_pull_a_later_insert_into_its_step(self):
        b = self.b
        self.make("Image cancel two")
        self.slash_row(" /image")
        b.eval("document.querySelector('.nimgfile').dispatchEvent(new Event('cancel'))")
        b.pump(0.3)
        b.eval("document.querySelector('.nbody').cxed.focus('end'); true")
        b.eval(ED + ".chain().focus('end').setMeta('cxStepJoin',true).insertTable({rows:2,cols:2}).run()")      # the toolbar's table, much later
        self.assertTrue(b.eval("!!document.querySelector('.nbody table')"))
        self.undo()
        self.assertFalse(b.eval("!!document.querySelector('.nbody table')"))
        self.assertEqual(self.text(), "hello ", "the deleted /image is a step of its own, not joined by a later insert")

    def test_a_cancelled_link_form_then_typing_is_a_step_of_its_own(self):
        b = self.b
        self.make("Link cancel")
        self.slash_row(" /link")
        b.wait("!!document.querySelector('.linkpop')", 10)
        b.key("Escape")                                                                # the form is cancelled; the cursor is back in the text
        b.wait("!document.querySelector('.linkpop')&&document.activeElement===document.querySelector('.nbody')", 5)
        b.type("X")
        self.assertEqual(self.text(), "hello X")
        self.undo()
        self.assertEqual(self.text(), "hello ", "the typing is its own step, not merged into the deletion of /link")

    def test_the_history_groups_equal_composition_ids_whatever_the_time_and_place(self):
        """The slash menu's join rests on this in prosemirror-history (test_notes_undo_shape pins the source; this runs it)."""
        b = self.b
        self.make("Composition")
        self.burst("hello")
        self.burst(" there")
        ev = "(()=>{const e=%s; const p=e.state.plugins.find(p=>/^history/.test(p.key)); return p.getState(e.state).done.eventCount; })()" % ED
        start = b.eval(ev)
        comp = "%s.state.plugins.find(p=>/^history/.test(p.key)).getState(%s.state).prevComposition" % (ED, ED)
        self.assertEqual(b.eval(comp), -1)
        self.assertEqual(b.eval("(()=>{const e=%s; e.view.dispatch(e.state.tr.insertText('A',1).setMeta('addToHistory',true)); return true; })()" % ED), True)
        self.assertEqual(b.eval(ev), start + 1, "far from the last change and without an id: its own step")
        self.assertEqual(b.eval("(()=>{const e=%s; e.view.dispatch(e.state.tr.insertText('B',e.state.doc.content.size-1).setMeta('composition',%s)); return true; })()" % (ED, comp)), True)
        self.assertEqual(b.eval(ev), start + 1, "the same composition id joins it, however far")
        self.assertEqual(b.eval(comp), -1, "a change with no id keeps the one it had")


if __name__ == "__main__":
    unittest.main()
