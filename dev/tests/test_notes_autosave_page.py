"""#119 (page half): Notes save by themselves about 2 s after the last key, and focus mode closes by one path.
A real browser against the real live server over a throwaway vault.

Run: python3 dev/tests/test_notes_autosave_page.py   (needs Google Chrome; skipped otherwise)

Autosave (stores/notes.js):
  - the file is written about 2 s after the last key, not before; a further key moves it; no draft, no "Draft kept" or "Editing";
  - nothing is sent when nothing changed; leaving, switching notes and a property toggle write at once; typing carries on undisturbed
    while a save is on its way;
  - every save of an editing session carries the same session id (also the keepalive save as the page goes), a new open or 5 minutes
    idle a new one, and the server keeps ONE backup for the session; a title is saved at once but the file is renamed only when the
    title field is left;
  - the save line reads "Saved 14:02", "Saving…", "Not saved" or "Changed outside creaite".
Closing rules (focus mode, the same live element):
  - Esc, a click on the scrim and the leave icon do the same thing: flush, then close, with no question when it saved;
  - a save that fails or a file changed outside creaite keeps the note open with the three-button dialog (Keep editing, Copy my text
    then close, Save again) and the typing; Copy really copies; Save again retries; another note is not opened over unsaved text;
  - Esc closes the topmost overlay first (/ menu, [[ picker, AI bar and suggestion, a registered layer, the date pop-up, the tag box)
    and the next leaves; focus goes back to the control that opened focus mode, else the title.
"""
import json
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
import test_notes_tab_browser as notes_tab_browser  # noqa: E402  (its helpers; imported as a module so its own tests do not run here)

SPY = """(()=>{ window.__saves=[]; window.__slow=0; window.__fail=null; const f=window.fetch.bind(window);
  window.fetch=function(u,o){ const save=String(u).includes('/api/notes/save');
    if(save){ try{ window.__saves.push({...JSON.parse(o.body),keepalive:!!(o&&o.keepalive)}); }catch(e){} }
    if(save&&window.__fail) return Promise.resolve(new Response(JSON.stringify(window.__fail),{status:200,headers:{'Content-Type':'application/json'}}));
    if(save&&window.__slow) return new Promise(r=>setTimeout(r,window.__slow)).then(()=>f(u,o));
    return f(u,o); }; return true; })()"""
CLIP = "(()=>{ window.__clip=null; Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async t=>{ window.__clip=t; }}}); return true; })()"


# page names these tests use: noteFocusClose noteEscape noteFocusOpen noteFlushOnExit notesList noteLeave noteText
class AutosavePage(LiveBrowserCase):
    width, height = 1400, 1000
    log, notes_dir, make, type_end = (notes_tab_browser.NotesTab.log, notes_tab_browser.NotesTab.notes_dir, notes_tab_browser.NotesTab.make,
                                      notes_tab_browser.NotesTab.type_end)

    # ---- helpers ----
    def edits(self, since=0):
        return [e for e in self.log()[since:] if e.get("op") == "edit"]

    def wait_text(self, f, text, secs=10):
        t0 = time.monotonic()
        while time.monotonic() - t0 < secs:
            if f.is_file() and text in f.read_text():
                return time.monotonic() - t0
            self.b.pump(0.05)
        self.fail(f"{text!r} never reached {f.name}: {f.read_text() if f.is_file() else 'no file'}")

    def line(self):
        return self.b.eval("document.getElementById('noteSave').textContent")

    def focus_on(self):
        b = self.b
        b.click("#noteExpand")
        b.wait("noteFocus.value&&!!document.querySelector('.ndoc.nfocus')&&document.activeElement===document.querySelector('.nbody')", 5)

    def trigger(self, how):
        b = self.b
        if how == "esc":
            b.key("Escape")
        elif how == "scrim":
            b.eval("document.querySelector('[data-nscrim]').click()")
        else:
            b.click("#noteExpand")

    def dialog_open(self):
        return self.b.eval("document.getElementById('noteLeaveDlg').open")

    # ---- autosave ----
    def test_saves_two_seconds_after_the_last_key_and_not_before(self):
        b = self.b
        self.make("Timing")
        f = self.notes_dir() / "Timing.md"
        n = len(self.log())
        b.eval(SPY)
        self.type_end("first words")
        b.pump(1.0)
        self.assertNotIn("first words", f.read_text(), "1 s after the last key: not yet")
        self.assertEqual(self.line(), "Saving…")
        self.type_end(" and more")                                                    # a further key moves the save
        dt = self.wait_text(f, "first words and more", 8)
        self.assertGreater(dt, 1.5, "about 2 s after the last key")
        b.wait("noteSave.value.state==='saved'", 10)
        self.assertRegex(self.line(), r"^Saved \d\d:\d\d$")
        self.assertEqual(len(b.eval("window.__saves")), 1, "one save for the whole burst")
        for _ in range(40):
            if self.edits(n):
                break
            b.pump(0.1)
        self.assertEqual(len(self.edits(n)), 1)
        page = b.eval("document.body.innerText")
        for word in ("Draft kept", "Editing", "Use my typing", "Keep the file"):
            self.assertNotIn(word, page)

    def test_nothing_is_sent_when_nothing_changed(self):
        b = self.b
        self.make("Quiet")
        n = len(self.log())
        b.eval(SPY)
        b.click(".nbody")
        b.pump(3.0)
        b.eval("noteFlush()")
        b.pump(0.4)
        self.assertEqual(b.eval("window.__saves"), [])
        self.assertEqual(self.edits(n), [])
        self.type_end("one thing")
        b.wait("noteSave.value.state==='saved'", 10)
        b.eval("noteFlush()")
        b.pump(3.0)
        self.assertEqual(len(b.eval("window.__saves")), 1, "saved text is not sent again")

    def test_leaving_switching_and_a_toggle_write_at_once(self):
        b = self.b
        self.make("Leave A")
        fa = self.notes_dir() / "Leave A.md"
        self.make("Leave B")
        fb = self.notes_dir() / "Leave B.md"
        b.eval(SPY)
        self.type_end("typed in b")                                                   # leaving the page
        b.eval("go('today')")
        self.assertLess(self.wait_text(fb, "typed in b", 4), 1.7, "written by leaving, not by the 2 s timer")
        b.eval("go('notes','ABC')")
        b.wait("noteCur.value&&!!document.querySelector('.nbody.ProseMirror')", 10)
        b.eval(f"openNote({json.dumps([x['path'] for x in self.listing() if x['title'] == 'Leave A'][0])})")
        b.wait("noteCur.value&&noteCur.value.note.title==='Leave A'&&!!document.querySelector('.nbody.ProseMirror')", 10)
        self.type_end("typed in a")                                                   # switching notes
        path_b = [x["path"] for x in self.listing() if x["title"] == "Leave B"][0]
        b.eval(f"openNote({json.dumps(path_b)})")
        self.assertLess(self.wait_text(fa, "typed in a", 4), 1.7, "written by switching, not by the timer")
        b.wait("noteCur.value&&noteCur.value.note.title==='Leave B'&&!!document.querySelector('.nbody.ProseMirror')", 10)
        self.type_end(" and pinned")                                                  # a property toggle
        b.eval("noteMeta({pinned:true},true)")
        self.assertLess(self.wait_text(fb, "pinned: true", 4), 1.7, "written by the toggle, not by the timer")
        self.assertIn("and pinned", fb.read_text())

    def listing(self):
        return self.b.eval("notesList.value.map(n=>({path:n.path,title:n.title}))")

    def test_typing_carries_on_while_a_save_is_on_its_way(self):
        b = self.b
        self.make("Overlap")
        f = self.notes_dir() / "Overlap.md"
        b.eval(SPY)
        b.eval("window.__slow=1500")
        self.type_end("alpha")
        b.wait("noteSave.value.state==='saving'", 8)
        b.type("beta")                                                                # typed while the first save is out
        self.assertEqual(b.eval("document.activeElement===document.querySelector('.nbody')"), True)
        b.wait("noteSave.value.state!=='saving'", 8)
        self.assertIn("alphabeta", b.eval("document.querySelector('.nbody').textContent"), "the save's answer does not touch the text")
        self.assertEqual(b.eval("document.activeElement===document.querySelector('.nbody')"), True)
        self.wait_text(f, "alphabeta", 10)
        b.wait("noteSave.value.state==='saved'", 10)
        saves = b.eval("window.__saves")
        self.assertEqual(len(saves), 2)
        self.assertIn("alpha", saves[0]["body"])
        self.assertNotIn("beta", saves[0]["body"])
        self.assertIn("alphabeta", saves[1]["body"])

    def test_one_session_id_for_the_saves_of_a_session_and_one_backup(self):
        b = self.b
        self.make("Sessions")
        f = self.notes_dir() / "Sessions.md"
        n = len(self.log())
        b.eval(SPY)
        for word in ("one", " two", " three"):
            self.type_end(word)
            self.wait_text(f, word, 8)
            b.wait("noteSave.value.state==='saved'", 8)
        saves = b.eval("window.__saves")
        self.assertEqual(len(saves), 3)
        sid = saves[0]["session"]
        self.assertRegex(sid, r"^[A-Za-z0-9-]{8,64}$")
        self.assertEqual({s["session"] for s in saves}, {sid}, "N saves in a session: one id")
        for _ in range(40):
            if len(self.edits(n)) == 3:
                break
            b.pump(0.1)
        ed = self.edits(n)
        self.assertEqual(len(ed), 3)
        self.assertEqual(len({e["backup"] for e in ed}), 1, "one backup for the session")
        b.eval("document.querySelector('.nbody').cxed.focus('end')")                  # the keepalive save as the page goes carries it too
        b.type(" four")
        b.eval("noteFlushOnExit()")
        keep = b.eval("window.__saves")[-1]
        self.assertTrue(keep["keepalive"])
        self.assertEqual(keep["session"], sid)
        self.wait_text(f, "four", 8)
        # a new open is a new session
        path = b.eval("noteCur.value.path")
        b.eval("go('today')")
        b.eval("go('notes','ABC')")
        b.wait("noteCur.value&&!!document.querySelector('.nbody.ProseMirror')", 10)
        b.eval(f"openNote({json.dumps(path)})")
        b.wait("noteCur.value&&noteCur.value.path===" + json.dumps(path) + "&&!!document.querySelector('.nbody.ProseMirror')", 10)
        self.type_end(" five")
        self.wait_text(f, "five", 8)
        b.wait("noteSave.value.state==='saved'", 8)
        reopened = b.eval("window.__saves")[-1]["session"]
        self.assertNotEqual(reopened, sid, "a new open: a new session id")
        # five minutes without a save: a new id again
        b.eval("(()=>{ const o=Date.now; window.__skew=0; Date.now=()=>o.call(Date)+window.__skew; window.__skew=6*60*1000; return true; })()")
        self.type_end(" six")
        self.wait_text(f, "six", 8)
        self.assertNotEqual(b.eval("window.__saves")[-1]["session"], reopened, "5 minutes idle: a new session id")

    def test_a_new_session_is_a_new_backup(self):
        b = self.b
        self.make("Backups")
        f = self.notes_dir() / "Backups.md"
        n = len(self.log())
        path = b.eval("noteCur.value.path")
        self.type_end("first session a")
        self.wait_text(f, "first session a", 8)
        b.wait("noteSave.value.state==='saved'", 8)
        self.type_end(" b")
        self.wait_text(f, "session a b", 8)
        b.eval("go('today')")
        b.eval("go('notes','ABC')")
        b.wait("noteCur.value&&!!document.querySelector('.nbody.ProseMirror')", 10)
        b.eval(f"openNote({json.dumps(path)})")
        b.wait("noteCur.value&&noteCur.value.path===" + json.dumps(path) + "&&!!document.querySelector('.nbody.ProseMirror')", 10)
        self.type_end(" second session")
        self.wait_text(f, "second session", 8)
        for _ in range(40):
            if len(self.edits(n)) == 3:
                break
            b.pump(0.1)
        ed = self.edits(n)
        self.assertEqual(len(ed), 3)
        self.assertEqual(ed[0]["backup"], ed[1]["backup"])
        self.assertNotEqual(ed[1]["backup"], ed[2]["backup"])

    def test_a_title_is_saved_at_once_but_the_file_is_renamed_when_the_field_is_left(self):
        b = self.b
        self.make("Old title")
        old, new = self.notes_dir() / "Old title.md", self.notes_dir() / "New title.md"
        b.eval("(()=>{ const i=document.getElementById('noteTitle'); i.focus(); i.value='New title'; i.dispatchEvent(new Event('input',{bubbles:true})); return true; })()")
        self.wait_text(old, "title: New title", 8)
        b.wait("noteSave.value.state==='saved'", 8)
        b.pump(0.5)
        self.assertTrue(old.is_file() and not new.exists(), "autosaving the title does not rename the file each time")
        b.eval("document.getElementById('noteTitle').blur()")
        for _ in range(80):
            if new.is_file() and not old.exists():
                break
            b.pump(0.1)
        self.assertTrue(new.is_file() and not old.exists(), "leaving the title field renames it")

    def test_the_save_line_says_saved_not_saved_or_changed_outside(self):
        b = self.b
        self.make("Wording")
        f = self.notes_dir() / "Wording.md"
        orig = f.read_text()
        b.eval(SPY)
        self.type_end("fine")
        b.wait("noteSave.value.state==='saved'", 10)
        self.assertRegex(self.line(), r"^Saved \d\d:\d\d$")
        b.eval("window.__fail={ok:false,message:'Not saved: nope.'}")                 # a save that fails
        self.type_end(" more")
        b.wait("noteSave.value.state==='error'", 10)
        self.assertEqual(self.line(), "Not saved")
        self.assertIn("nope", b.eval("document.querySelector('[data-nbanner=error]').textContent"))
        self.assertTrue(b.eval("!!document.querySelector('[data-nbanner] [data-ncopy]')"))
        b.eval("window.__fail=null")
        f.write_text(orig + "\nsomeone else\n")                                       # a file changed outside creaite
        self.type_end(" again")
        b.wait("noteSave.value.state==='conflict'", 10)
        self.assertEqual(self.line(), "Changed outside creaite")
        self.assertIn("changed outside creaite", b.eval("document.querySelector('[data-nbanner=conflict]').textContent"))
        self.assertNotIn("Draft kept", b.eval("document.body.innerText"))

    # ---- closing rules ----
    def test_esc_the_scrim_and_the_leave_icon_save_then_close_with_no_question(self):
        b = self.b
        for how in ("esc", "scrim", "icon"):
            with self.subTest(how=how):
                title = f"Close by {how}"
                self.make(title)
                f = self.notes_dir() / f"{title}.md"
                self.focus_on()
                self.assertEqual(b.eval("document.querySelector('.ndoc').getAttribute('role')"), "dialog")
                self.assertEqual(b.eval("document.querySelector('.ndoc').getAttribute('aria-modal')"), "true")
                self.type_end(f"typed for {how}")
                t0 = time.monotonic()
                self.trigger(how)
                b.wait("!noteFocus.value", 8)
                self.assertFalse(self.dialog_open(), "saved: no prompt")
                self.assertLess(time.monotonic() - t0, 1.7, "flushed by closing, not by the 2 s timer")
                self.assertIn(f"typed for {how}", f.read_text())
                self.assertEqual(b.eval("noteSave.value.state"), "saved")
                self.assertEqual(b.eval("document.activeElement.id"), "noteExpand", "focus is back on the control that opened it")
                self.assertEqual(b.eval("document.querySelector('.ndoc').classList.contains('nfocus')"), False)

    def failing(self, title, how):
        """A note in focus mode whose file changed outside creaite, with text typed after; the close is tried by `how`."""
        b = self.b
        self.make(title)
        f = self.notes_dir() / f"{title}.md"
        orig = f.read_text()
        b.eval(SPY)
        b.eval(CLIP)
        self.focus_on()
        f.write_text(orig + "\nchanged elsewhere\n")
        self.type_end("my unsaved words")
        self.trigger(how)
        b.wait("document.getElementById('noteLeaveDlg').open", 8)
        return f, orig

    def test_a_failing_save_keeps_the_note_and_asks_with_three_buttons(self):
        b = self.b
        for how in ("esc", "scrim", "icon"):
            with self.subTest(how=how):
                f, orig = self.failing(f"Conflict {how}", how)
                self.assertEqual(b.eval("noteFocus.value"), True, "the note stays open")
                self.assertEqual(b.eval("[...document.querySelectorAll('#noteLeaveDlg .nlfoot button')].map(x=>[x.textContent,x.hasAttribute('data-nlkeep'),x.hasAttribute('data-nlcopy'),x.hasAttribute('data-nlretry')])"),
                                 [["Keep editing", True, False, False], ["Copy my text then close", False, True, False], ["Save again", False, False, True]])
                self.assertEqual(b.eval("document.getElementById('noteLeaveDlg').getAttribute('aria-labelledby')"), "noteLeaveH")
                self.assertIn("changed outside creaite", b.eval("document.getElementById('noteLeaveP').textContent"))
                self.assertIn("my unsaved words", b.eval("document.querySelector('.nbody').textContent"), "the typing is kept")
                self.assertNotIn("my unsaved words", f.read_text())
                self.assertEqual(b.eval("document.activeElement.hasAttribute('data-nlkeep')"), True)
                b.reload("typeof go==='function' && LIVE")                            # (the page goes with its unsaved note; the next case starts clean)

    def test_keep_editing_and_esc_in_the_dialog_go_back_to_the_note(self):
        b = self.b
        self.failing("Keep going", "esc")
        b.click("[data-nlkeep]")
        b.wait("!document.getElementById('noteLeaveDlg').open", 5)
        self.assertEqual(b.eval("noteFocus.value"), True)
        b.wait("document.activeElement===document.querySelector('.nbody')", 5)
        self.assertIn("my unsaved words", b.eval("document.querySelector('.nbody').textContent"))
        b.key("Escape")                                                               # tries again, asks again
        b.wait("document.getElementById('noteLeaveDlg').open", 8)
        b.key("Escape")                                                               # a modal dialog takes Esc itself: Keep editing
        b.wait("!document.getElementById('noteLeaveDlg').open", 5)
        self.assertEqual(b.eval("noteFocus.value"), True, "Esc in the dialog does not leave focus mode")
        self.assertIn("my unsaved words", b.eval("document.querySelector('.nbody').textContent"))

    def test_copy_my_text_then_close_really_copies(self):
        b = self.b
        self.failing("Copy out", "scrim")
        b.click("[data-nlcopy]")
        b.wait("!noteFocus.value", 8)
        self.assertIn("my unsaved words", b.eval("window.__clip"))
        self.assertFalse(self.dialog_open())
        self.assertEqual(b.eval("document.activeElement.id"), "noteExpand")
        self.assertIn("my unsaved words", b.eval("document.querySelector('.nbody').textContent"), "closing drops nothing: the note still holds it")

    def test_save_again_retries_and_closes_when_it_works(self):
        b = self.b
        f, orig = self.failing("Retry", "icon")
        b.eval("window.__saves.length=0")
        b.click("[data-nlretry]")                                                     # still changed outside: asks again
        b.wait("window.__saves.length>=1&&document.getElementById('noteLeaveDlg').open&&noteSave.value.state==='conflict'", 8)
        self.assertEqual(b.eval("noteFocus.value"), True)
        f.write_text(orig)                                                            # put the file back as it was opened
        b.click("[data-nlretry]")
        b.wait("!noteFocus.value", 8)
        self.assertFalse(self.dialog_open())
        self.assertIn("my unsaved words", f.read_text())
        self.assertEqual(b.eval("noteSave.value.state"), "saved")

    def test_a_save_that_errors_asks_too_and_another_note_is_not_opened_over_unsaved_text(self):
        b = self.b
        self.make("Other")
        other = b.eval("noteCur.value.path")
        self.make("Erroring")
        f = self.notes_dir() / "Erroring.md"
        b.eval(SPY)
        b.eval("window.__fail={ok:false,message:'Not saved: the disk said no.'}")
        self.focus_on()
        self.type_end("held text")
        b.key("Escape")
        b.wait("document.getElementById('noteLeaveDlg').open", 8)
        self.assertIn("the disk said no", b.eval("document.getElementById('noteLeaveP').textContent"))
        b.click("[data-nlkeep]")
        b.wait("!document.getElementById('noteLeaveDlg').open", 5)
        b.click("#noteExpand")                                                        # leave: asks again
        b.wait("document.getElementById('noteLeaveDlg').open", 8)
        b.click("[data-nlkeep]")
        b.wait("!document.getElementById('noteLeaveDlg').open", 5)
        b.eval("window.__fail=null")
        self.assertEqual(b.eval("noteFocus.value"), True)
        b.eval("window.__fail={ok:false,message:'Not saved: still no.'}")
        self.assertEqual(b.eval(f"openNote({json.dumps(other)})"), False)
        self.assertEqual(b.eval("noteCur.value.note.title"), "Erroring", "not opened over unsaved text")
        self.assertIn("stays open", b.eval("notesMsg.value"))
        self.assertIn("held text", b.eval("document.querySelector('.nbody').textContent"))
        self.assertNotIn("held text", f.read_text())
        b.eval("window.__fail=null")
        b.click("#noteExpand")                                                        # works now: closes with no question
        b.wait("!noteFocus.value", 8)
        self.assertIn("held text", f.read_text())

    # ---- Esc layers, focus, the live element ----
    def test_esc_closes_the_topmost_overlay_first_then_leaves_focus_mode(self):
        b = self.b
        self.make("Layers")
        self.focus_on()
        self.type_end("hello world")

        def one_esc_closes(open_js, closed_js):
            b.wait(open_js, 5)
            b.key("Escape")
            b.wait(closed_js, 5)
            self.assertEqual(b.eval("noteFocus.value"), True, "the first Esc closed the overlay only")
            self.assertFalse(self.dialog_open())

        def second_esc_leaves():
            b.key("Escape")
            b.wait("!noteFocus.value", 8)
            self.assertFalse(self.dialog_open())
            self.focus_on()

        b.key("Enter")                                                                # the / menu
        b.type("/")
        one_esc_closes("!!document.querySelector('#ntpick [role=option]')", "!document.querySelector('#ntpick')")
        second_esc_leaves()
        b.type("[[Lay")                                                               # the [[ picker
        one_esc_closes("!!document.querySelector('#ntpick')", "!document.querySelector('#ntpick')")
        second_esc_leaves()
        b.eval("document.querySelector('.nbody').cxed.editor.commands.setContent('hello world')")    # the picker's text goes
        b.eval("document.querySelector('.nbody').cxed.editor.commands.selectAll()")  # the AI bar over a selection
        one_esc_closes("!!document.querySelector('.aibar')", "!document.querySelector('.aibar')")
        second_esc_leaves()
        b.eval("document.querySelector('.nbody').cxed.editor.commands.selectAll()")  # the bar with its menu open: menu, then bar, then leave
        b.wait("!!document.querySelector('.aibar')", 5)
        b.key("/", 1)
        b.wait("!!document.querySelector('.aibar [role=menu]')", 5)
        b.key("Escape")
        b.wait("!document.querySelector('.aibar [role=menu]')", 5)
        self.assertEqual(b.eval("!!document.querySelector('.aibar')&&noteFocus.value"), True)
        one_esc_closes("!!document.querySelector('.aibar')", "!document.querySelector('.aibar')")
        second_esc_leaves()
        # the AI suggestion, with the cursor in the text and with focus in the card
        b.eval("""(()=>{ const h=document.querySelector('.nbody').cxed; aiSug.value={h,ai:{place:'notes'},option:'x',label:'Tighten',status:'ready',text:'Hi',notes:[],
          range:{from:1,to:3,text:'he'},top:140,left:200}; return true; })()""")
        b.wait("!!document.querySelector('.aisug')", 5)
        b.eval("document.querySelector('.nbody').cxed.focus()")
        one_esc_closes("!!document.querySelector('.aisug')", "!document.querySelector('.aisug')")
        second_esc_leaves()
        b.eval("""(()=>{ const h=document.querySelector('.nbody').cxed; aiSug.value={h,ai:{place:'notes'},option:'x',label:'Tighten',status:'ready',text:'Hi',notes:[],
          range:{from:1,to:3,text:'he'},top:140,left:200}; return true; })()""")
        b.wait("document.activeElement&&document.activeElement.hasAttribute('data-aifirst')", 5)
        one_esc_closes("!!document.querySelector('.aisug')", "!document.querySelector('.aisug')")
        second_esc_leaves()
        # a layer a later part registers (the link popover): consumed first
        b.eval("window.__pop=true; noteEscLayers.unshift(()=>{ if(!window.__pop) return false; window.__pop=false; return true; }); true")
        b.key("Escape")
        b.pump(0.3)
        self.assertEqual(b.eval("noteFocus.value&&window.__pop===false"), True)
        second_esc_leaves()
        b.eval("noteEscLayers.shift(); true")
        self.assertEqual(b.eval("noteEscape()"), False, "nothing open: Esc has no overlay to close")

    def test_esc_in_the_tag_box_and_the_date_pop_up_closes_only_that(self):
        b = self.b
        self.make("Header layers", "working-session")
        self.focus_on()
        b.click(".nhead .addl")
        b.wait("!!document.querySelector('.nhead .addin')", 5)
        b.key("Escape")
        b.wait("!document.querySelector('.nhead .addin')", 5)
        self.assertEqual(b.eval("noteFocus.value"), True)
        b.click(".nhead .ndbtn")
        b.wait("!!document.querySelector('.nhead .dpop')", 5)
        b.key("Escape")
        b.wait("!document.querySelector('.nhead .dpop')", 5)
        self.assertEqual(b.eval("noteFocus.value"), True)
        self.assertEqual(b.eval("!!document.activeElement.closest('.nhead')"), True, "focus stays in the header")
        b.key("Escape")
        b.wait("!noteFocus.value", 8)

    def test_focus_goes_back_to_the_title_when_nothing_opened_it_and_the_note_is_the_same_element(self):
        b = self.b
        self.make("Same element")
        self.type_end("before ")
        b.eval("window.__el=document.querySelector('.nbody'); window.__pm=window.__el.cxed.editor.view; document.activeElement.blur(); true")
        b.eval("noteFocusOpen()")                                                     # opened from code, nothing focused
        b.wait("noteFocus.value&&document.activeElement===document.querySelector('.nbody')", 5)
        self.assertEqual(b.eval("document.querySelector('.nbody')===window.__el&&window.__el.cxed.editor.view===window.__pm"), True,
                         "the same live element, not a copy")
        b.type("while lifted")
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('.ndoc')).position"), "fixed")
        self.assertLessEqual(b.eval("document.querySelector('.ndoc').getBoundingClientRect().width"), 1041)
        b.key("Escape")
        b.wait("!noteFocus.value", 8)
        b.wait("document.activeElement&&document.activeElement.id==='noteTitle'", 5)
        self.assertEqual(b.eval("document.querySelector('.nbody')===window.__el"), True)
        self.assertIn("before while lifted", b.eval("document.querySelector('.nbody').textContent"))
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('.ndoc')).position"), "relative")

    def test_at_900_px_the_lifted_note_is_96_percent_wide(self):
        b = self.b
        self.make("Narrow focus")
        b.eval("closePanel&&closePanel(true)")
        b.resize(900, 800)
        b.wait("document.documentElement.clientWidth<=900")
        self.focus_on()
        w = b.eval("document.querySelector('.ndoc.nfocus').getBoundingClientRect().width")
        self.assertGreater(w, 0.94 * 900)
        self.assertLess(w, 0.975 * 900)
        self.assertLessEqual(b.eval("document.documentElement.scrollWidth-document.documentElement.clientWidth"), 0)
        b.key("Escape")
        b.wait("!noteFocus.value", 8)


if __name__ == "__main__":
    unittest.main()
