"""#119: Notes save by themselves about 2 s after you stop typing, with no draft step.
A real browser against the real live server over a throwaway vault.

Run: python3 dev/tests/test_notes_autosave_page.py   (needs Google Chrome; skipped otherwise)

Autosave (stores/notes.js):
  - the file is written about 2 s after the last key, not before; a further key moves it; no draft is ever posted, no "Draft kept";
  - nothing is sent when nothing changed; leaving, switching notes and a property toggle write at once; typing carries on undisturbed
    while a save is on its way;
  - every save of an editing session carries the same session id (also the keepalive save as the page goes), a new open or 5 minutes
    idle a new one; with the server half (filechange keeps one backup per session) the saves share ONE backup: those assertions
    run only when the tree has it; a title is saved at once but the file is renamed only when the title field is left;
  - the save line reads "Saved 14:02", "Editing", "Saving…", "Not saved" or "Changed outside creaite";
  - typing that could not be saved (no draft file keeps it) is never dropped silently: a note in that state is not closed or switched
    away from unless the text was copied or its loss confirmed; the banner offers Copy my text and a confirmed discard; the page asks
    before it is closed; an exit save counts as saved only when the server says so.
Not here (#136, later): focus mode, the scrim, the leave dialog and the closing rules.
"""
import json
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
import test_notes_tab_browser as notes_tab_browser  # noqa: E402  (its helpers; imported as a module so its own tests do not run here)

SPY = """(()=>{ window.__saves=[]; window.__drafts=0; window.__slow=0; window.__slowGet=0; window.__slowRename=0; window.__failRename=false; window.__fail=null; window.__rej=0;
  addEventListener('unhandledrejection',()=>{ window.__rej++; }); const f=window.fetch.bind(window);
  const later=(ms,u,o)=>new Promise(r=>setTimeout(r,ms)).then(()=>f(u,o));
  window.fetch=function(u,o){ const url=String(u), save=url.includes('/api/notes/save');
    if(url.includes('/api/notes/draft')) window.__drafts++;
    if(save){ try{ window.__saves.push({...JSON.parse(o.body),keepalive:!!(o&&o.keepalive)}); }catch(e){} }
    if(save&&window.__fail) return Promise.resolve(new Response(JSON.stringify(window.__fail),{status:200,headers:{'Content-Type':'application/json'}}));
    if(save&&window.__slow) return later(window.__slow,u,o);
    if(url.includes('/api/notes/get')&&window.__slowGet) return later(window.__slowGet,u,o);
    if(url.includes('/api/notes/rename')){ if(window.__failRename) return Promise.resolve(new Response(JSON.stringify({ok:true,renamed:true,from:'x',note:null}),{status:200,headers:{'Content-Type':'application/json'}})); if(window.__slowRename) return later(window.__slowRename,u,o); }
    return f(u,o); }; return true; })()"""
# (__failRename answers the rename with something the page cannot use, so its handling throws)
# the 2 s autosave timer never fires (every other timer does): a test of what writes at once then cannot be a race with the clock
NO_TIMER = """(()=>{ const st=window.setTimeout.bind(window); window.setTimeout=(fn,ms,...a)=>(ms===2000&&String(fn).includes('noteFlush'))?0:st(fn,ms,...a); return true; })()"""
CLIP = "(()=>{ window.__clip=null; Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async t=>{ window.__clip=t; }}}); return true; })()"


# page names these tests use: AUTOSAVE_MS noteFlushOnExit notesList noteDirty closeNote openNote noteGone noteUnsavedAtExit
class AutosavePage(LiveBrowserCase):
    width, height = 1400, 1000
    log, notes_dir, make, type_end = (notes_tab_browser.NotesTab.log, notes_tab_browser.NotesTab.notes_dir, notes_tab_browser.NotesTab.make,
                                      notes_tab_browser.NotesTab.type_end)

    def server_joins(self):
        """Whether this tree's filechange.py keeps one backup per editing session (the server half of #119)."""
        return "SESSION_IDLE" in (self.v.root / "system/scripts/filechange.py").read_text()

    def edits(self, since=0):
        return [e for e in self.log()[since:] if e.get("op") == "edit"]

    def wait_text(self, f, text, secs=10):
        """Seconds until `text` is in the file, counted from the call."""
        t0 = time.monotonic()
        while time.monotonic() - t0 < secs:
            if f.is_file() and text in f.read_text():
                return time.monotonic() - t0
            self.b.pump(0.05)
        self.fail(f"{text!r} never reached {f.name}: {f.read_text() if f.is_file() else 'no file'}")

    def line(self):
        return self.b.eval("document.getElementById('noteSave').textContent")

    def listing(self):
        return self.b.eval("notesList.value.map(n=>({path:n.path,title:n.title}))")

    def test_saves_two_seconds_after_the_last_key_and_not_before(self):
        b = self.b
        self.make("Timing")
        f = self.notes_dir() / "Timing.md"
        n = len(self.log())
        b.eval(SPY)
        self.type_end("first words")
        b.type(" and more")                                                           # one burst: the save follows its last key
        t_key = time.monotonic()
        self.assertNotIn("first words", f.read_text(), "straight after the last key: not yet")
        self.assertEqual(self.line(), "Editing")
        self.wait_text(f, "first words and more", 15)
        dt = time.monotonic() - t_key
        self.assertGreater(dt, 1.6, "about 2 s after the last key, never sooner (a slow machine only makes it later)")
        self.assertLess(dt, 8, "and not minutes later (a loose bound: only a stalled timer breaks it)")
        self.assertEqual(b.eval("AUTOSAVE_MS"), 2000, "the named constant is the 2 s the issue asks for")
        b.wait("noteSave.value.state==='saved'", 15)
        self.assertRegex(self.line(), r"^Saved \d\d:\d\d$")
        self.assertEqual(len(b.eval("window.__saves")), 1, "one save for the whole burst")
        for _ in range(40):
            if self.edits(n):
                break
            b.pump(0.1)
        self.assertEqual(len(self.edits(n)), 1)
        page = b.eval("document.body.innerText")
        for word in ("Draft kept", "Use my typing", "Keep the file"):
            self.assertNotIn(word, page)
        self.assertEqual(b.eval("window.__drafts"), 0, "no draft step: the page never posts a draft")

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
        b.eval(NO_TIMER)                                                              # the 2 s timer never fires: only these can have written
        self.type_end("typed in b")                                                   # leaving the page
        b.eval("go('today')")
        self.wait_text(fb, "typed in b", 10)
        b.eval("go('notes','ABC')")
        b.wait("noteCur.value&&!!document.querySelector('.nbody.ProseMirror')", 10)
        path_a = [x["path"] for x in self.listing() if x["title"] == "Leave A"][0]
        b.eval(f"openNote({json.dumps(path_a)})")
        b.wait("noteCur.value&&noteCur.value.note.title==='Leave A'&&!!document.querySelector('.nbody.ProseMirror')", 10)
        self.type_end("typed in a")                                                   # switching notes
        path_b = [x["path"] for x in self.listing() if x["title"] == "Leave B"][0]
        b.eval(f"openNote({json.dumps(path_b)})")
        self.wait_text(fa, "typed in a", 10)
        b.wait("noteCur.value&&noteCur.value.note.title==='Leave B'&&!!document.querySelector('.nbody.ProseMirror')", 10)
        self.type_end(" and pinned")                                                  # a property toggle
        b.eval("noteMeta({pinned:true},true)")
        self.wait_text(fb, "pinned: true", 10)
        self.assertIn("and pinned", fb.read_text())

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

    def test_one_session_id_for_the_saves_of_a_session_the_server_may_share_a_backup_on(self):
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
        if self.server_joins():
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
        if not self.server_joins():
            self.skipTest("the server half of #119 (filechange keeps one backup per session) is not in this tree")
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
        self.assertIn("Open the file's version", b.eval("document.querySelector('[data-nbanner=conflict] [data-ndiscard]').textContent"))
        self.assertNotIn("Draft kept", b.eval("document.body.innerText"))
        self.assertNotIn("kept as a draft", b.eval("document.querySelector('[data-nbanner=conflict]').textContent"), "no draft is kept: do not say so")

    def test_a_title_rename_does_not_remount_the_editor_or_lose_the_next_keys(self):
        b = self.b
        for i, delay in enumerate((0.1, 0.3, 0.8)):
            with self.subTest(delay=delay):
                title = f"Rename {i}"
                self.make(title)
                old, new = self.notes_dir() / f"{title}.md", self.notes_dir() / f"Renamed {i}.md"
                b.eval(SPY)
                b.eval("window.__slowRename=600")                                     # the rename round trip is wide: typing lands in it
                b.eval(f"(()=>{{ const i=document.getElementById('noteTitle'); i.focus(); i.value='Renamed {i}'; i.dispatchEvent(new Event('input',{{bubbles:true}})); return true; }})()")
                self.wait_text(old, f"title: Renamed {i}", 15)
                b.eval("window.__el=document.querySelector('.nbody'); window.__pm=window.__el.cxed.editor.view; true")
                b.click(".nbody")                                                     # leaving the title field renames the file
                b.pump(delay)
                b.type("typed after")

                def same():
                    return b.eval("document.querySelector('.nbody')===window.__el&&window.__el.cxed.editor.view===window.__pm&&document.activeElement===window.__el&&"
                                  "window.__el.textContent.includes('typed after')")
                self.assertTrue(same(), "right after typing")
                self.wait_text(new, "typed after", 20)
                self.assertTrue(same(), "after the rename and the save")
                b.pump(0.8)
                self.assertTrue(same(), "and a moment later")
                self.assertFalse(old.exists())

    def test_typing_while_another_note_is_opening_is_not_lost(self):
        b = self.b
        self.make("Get A")
        fa = self.notes_dir() / "Get A.md"
        self.make("Get B")
        path_a = [x["path"] for x in self.listing() if x["title"] == "Get A"][0]
        path_b = [x["path"] for x in self.listing() if x["title"] == "Get B"][0]
        b.eval(f"openNote({json.dumps(path_a)})")
        b.wait("noteCur.value&&noteCur.value.note.title==='Get A'&&!!document.querySelector('.nbody.ProseMirror')", 10)
        b.eval(SPY)
        b.eval("window.__slowGet=1500")
        b.eval(f"window.__r=undefined; openNote({json.dumps(path_b)}).then(v=>{{ window.__r=v; }}); true")
        b.pump(0.3)
        self.type_end("LATE words")                                                   # while B is still being fetched
        b.wait("window.__r!==undefined", 15)
        self.assertEqual(b.eval("window.__r"), False, "the switch is given up")
        self.assertEqual(b.eval("noteCur.value.note.title"), "Get A")
        self.assertIn("typed in this note", b.eval("notesMsg.value"))
        self.assertIn("LATE words", b.eval("document.querySelector('.nbody').textContent"))
        self.wait_text(fa, "LATE words", 15)                                          # and it is saved

    def test_typing_while_the_file_is_renamed_is_saved_before_the_flush_returns(self):
        b = self.b
        self.make("Slow rename")
        old, new = self.notes_dir() / "Slow rename.md", self.notes_dir() / "Quick rename.md"
        b.eval(SPY)
        b.eval("window.__slowRename=1500")
        b.eval("(()=>{ const i=document.getElementById('noteTitle'); i.value='Quick rename'; i.dispatchEvent(new Event('input',{bubbles:true})); return true; })()")
        b.eval("window.__fr=undefined; noteFlush(true).then(v=>{ window.__fr=v; }); true")
        self.wait_text(old, "title: Quick rename", 15)                               # saved; the rename is now in flight
        b.click(".nbody")
        b.type("during the rename")
        b.wait("window.__fr!==undefined", 20)
        self.assertEqual(b.eval("window.__fr"), True)
        self.assertEqual(b.eval("noteDirty()"), False, "true means everything typed is saved")
        self.assertIn("during the rename", new.read_text())

    def test_a_rename_that_fails_does_not_hang_later_saves(self):
        # What this pins is the `.catch` in settleRename: a rename whose handling throws is reported and later saves go on. The
        # try/finally blocks around `ses.busy` are defensive only: api() swallows network errors (server.js), so nothing reaches them.
        b = self.b
        self.make("Fails to rename")
        f = self.notes_dir() / "Fails to rename.md"
        b.eval(SPY)
        b.eval("window.__failRename=true")
        b.eval("(()=>{ const i=document.getElementById('noteTitle'); i.value='Other name'; i.dispatchEvent(new Event('input',{bubbles:true})); return true; })()")
        b.eval("window.__fr=undefined; noteFlush(true).then(v=>{ window.__fr=v; }); true")
        b.wait("window.__fr!==undefined", 15)
        self.type_end("still saves")
        self.wait_text(f, "still saves", 15)
        b.wait("noteSave.value.state==='saved'", 15)

    def test_a_late_save_result_does_not_touch_the_note_switched_to(self):
        b = self.b
        self.make("Late A")
        fa = self.notes_dir() / "Late A.md"
        self.make("Late B")
        path_a = [x["path"] for x in self.listing() if x["title"] == "Late A"][0]
        b.eval(f"openNote({json.dumps(path_a)})")
        b.wait("noteCur.value&&noteCur.value.note.title==='Late A'&&!!document.querySelector('.nbody.ProseMirror')", 10)
        b.eval(SPY)
        b.eval("window.__slow=1500")
        self.type_end("for a only")
        b.wait("noteSave.value.state==='saving'", 15)
        path_b = [x["path"] for x in self.listing() if x["title"] == "Late B"][0]
        b.eval(f"openNote({json.dumps(path_b)})")                                     # waits for A's save, then opens B
        b.wait("noteCur.value&&noteCur.value.note.title==='Late B'&&!!document.querySelector('.nbody.ProseMirror')", 15)
        self.assertIn("for a only", fa.read_text())
        self.assertNotIn("for a only", b.eval("document.querySelector('.nbody').textContent"))
        self.assertEqual(b.eval("noteSave.value.state"), "", "B shows no save state of A's")
        self.assertEqual(b.eval("noteDirty()"), False)

    def test_a_rename_then_a_save_goes_to_the_new_file_with_a_backup_of_its_own(self):
        b = self.b
        self.make("Before rename")
        n = len(self.log())
        old, new = self.notes_dir() / "Before rename.md", self.notes_dir() / "After rename.md"
        b.eval(SPY)
        self.type_end("one")
        self.wait_text(old, "one", 15)
        b.wait("noteSave.value.state==='saved'", 15)
        b.eval("(()=>{ const i=document.getElementById('noteTitle'); i.value='After rename'; i.dispatchEvent(new Event('input',{bubbles:true})); return true; })()")
        b.eval("noteFlush(true)")
        for _ in range(150):
            if new.is_file() and not old.exists():
                break
            b.pump(0.1)
        self.assertTrue(new.is_file())
        b.eval("document.querySelector('.nbody').cxed.focus('end')")
        b.type(" two")
        self.wait_text(new, "two", 15)
        saves = b.eval("window.__saves")
        self.assertTrue(saves[-1]["path"].endswith("After rename.md"), saves[-1]["path"])
        self.assertRegex(saves[-1]["session"], r"^[A-Za-z0-9-]{8,64}$")
        for _ in range(40):
            ed = self.edits(n)
            if ed and ed[-1]["path"].endswith("After rename.md"):
                break
            b.pump(0.1)
        ed = self.edits(n)
        self.assertTrue(ed[-1]["path"].endswith("After rename.md"))
        self.assertNotEqual(ed[-1]["backup"], ed[0]["backup"], "the renamed file's first save has a backup of its own")

    def test_closing_a_note_that_could_not_be_saved_keeps_it_unless_the_text_was_copied(self):
        b = self.b
        self.make("Closing")
        b.eval(SPY)
        b.eval(CLIP)
        b.eval("window.__fail={ok:false,message:'Not saved: nope.'}")
        self.type_end("keep this")
        b.wait("noteSave.value.state==='error'", 15)
        self.assertEqual(b.eval("closeNote()"), False)
        self.assertEqual(b.eval("noteCur.value.note.title"), "Closing", "still open")
        b.click("[data-ncopy]")                                                       # copied out: the typing is safe
        b.wait("window.__clip!==null", 5)
        self.assertIn("keep this", b.eval("window.__clip"))
        self.assertEqual(b.eval("closeNote()"), True)
        self.assertEqual(b.eval("noteCur.value"), None)

    def test_opening_the_same_note_while_it_is_fetched_keeps_the_typing(self):
        b = self.b
        self.make("Same again")
        f = self.notes_dir() / "Same again.md"
        path = b.eval("noteCur.value.path")
        b.eval(SPY)
        b.eval("window.__slowGet=1500")
        b.eval(f"window.__r=undefined; openNote({json.dumps(path)}).then(v=>{{ window.__r=v; }}); true")
        b.pump(0.3)
        self.type_end("typed meanwhile")                                              # while the same note is being fetched again
        b.wait("window.__r!==undefined", 15)
        self.assertEqual(b.eval("window.__r"), False, "the reopen is given up")
        self.assertIn("typed meanwhile", b.eval("document.querySelector('.nbody').textContent"))
        self.assertIn("typed in this note", b.eval("notesMsg.value"))
        self.wait_text(f, "typed meanwhile", 15)

    def test_an_exit_save_the_server_refuses_leaves_the_text_dirty(self):
        b = self.b
        self.make("Exit refused")
        b.eval(SPY)
        b.eval(NO_TIMER)
        b.eval("window.__fail={ok:false,message:'Not saved: nope.'}")
        self.type_end("not on disk")
        b.eval("noteFlushOnExit()")
        b.pump(1.0)
        self.assertEqual(len(b.eval("window.__saves")), 1, "the exit save was sent")
        self.assertEqual(b.eval("noteDirty()"), True, "refused: still dirty (nothing says it was saved)")

    def test_a_note_that_can_never_save_can_be_left_after_copying_or_discarding(self):
        b = self.b
        self.make("Stuck other")
        other = b.eval("noteCur.value.path")
        self.make("Stuck")
        f = self.notes_dir() / "Stuck.md"
        orig = f.read_text()
        b.eval(SPY)
        b.eval(CLIP)
        b.eval("window.__fail={ok:false,message:'Not saved: the disk said no.'}")
        self.type_end("irreplaceable")
        b.wait("noteSave.value.state==='error'", 15)
        self.assertEqual(b.eval(f"openNote({json.dumps(other)})"), False, "refused while the text is at risk")
        self.assertIn("stays open", b.eval("notesMsg.value"))
        b.click("[data-ncopy]")                                                       # a successful copy releases it
        b.wait("window.__clip!==null", 5)
        self.assertIn("irreplaceable", b.eval("window.__clip"))
        self.assertEqual(b.eval(f"openNote({json.dumps(other)})"), True)
        self.assertEqual(b.eval("noteCur.value.note.title"), "Stuck other")
        self.assertNotIn("irreplaceable", f.read_text())
        # a confirmed discard, from the banner: a question first, "Keep editing" keeps the text
        stuck = [x["path"] for x in self.listing() if x["title"] == "Stuck"][0]
        b.eval("window.__fail=null")
        b.eval(f"openNote({json.dumps(stuck)})")
        b.wait("noteCur.value&&noteCur.value.note.title==='Stuck'&&!!document.querySelector('.nbody.ProseMirror')", 10)
        b.eval("window.__fail={ok:false,message:'Not saved: the disk said no.'}")
        self.type_end("second text")
        b.wait("noteSave.value.state==='error'", 15)
        b.click("[data-ndiscard]")
        b.wait("!!document.querySelector('[data-ndiscardq]')", 5)
        self.assertIn("second text", b.eval("document.querySelector('.nbody').textContent"), "asking does not discard")
        b.click("[data-ndiscardno]")
        b.wait("!document.querySelector('[data-ndiscardq]')&&!!document.querySelector('[data-ndiscard]')", 5)
        self.assertIn("second text", b.eval("document.querySelector('.nbody').textContent"), "Keep editing keeps it")
        self.assertEqual(b.eval(f"openNote({json.dumps(other)})"), False, "still at risk")
        b.click("[data-ndiscard]")
        b.wait("!!document.querySelector('[data-ndiscardq]')", 5)
        b.eval("window.__fail=null")
        b.click("[data-ndiscardyes]")
        b.wait("noteSave.value.state===''&&!document.querySelector('[data-nbanner]')", 10)
        self.assertNotIn("second text", b.eval("document.querySelector('.nbody').textContent"), "the file's version is back")
        self.assertEqual(b.eval(f"openNote({json.dumps(other)})"), True)
        self.assertEqual(f.read_text(), orig)

    def test_a_conflict_offers_the_files_version_after_a_question(self):
        b = self.b
        self.make("Conflicting")
        f = self.notes_dir() / "Conflicting.md"
        orig = f.read_text()
        f.write_text(orig + "\nchanged elsewhere\n")
        self.type_end("my words")
        b.wait("noteSave.value.state==='conflict'", 15)
        self.assertEqual(b.eval("noteDirty()"), True)
        b.pump(2.6)                                                                   # nothing is retried over the other file
        self.assertNotIn("my words", f.read_text())
        b.click("[data-ndiscard]")
        b.wait("!!document.querySelector('[data-ndiscardq]')", 5)
        b.click("[data-ndiscardyes]")
        b.wait("noteSave.value.state===''", 10)
        text = b.eval("document.querySelector('.nbody').textContent")
        self.assertIn("changed elsewhere", text)
        self.assertNotIn("my words", text)
        self.assertEqual(b.eval("noteDirty()"), False)

    def test_a_note_moved_to_the_archive_is_forgotten_with_its_unsaved_typing(self):
        # #124's Delete note calls noteGone when the card is approved: the note's file has gone, so the editing state must not
        # keep it trapped in "Not saved", and nothing more is sent for it
        b = self.b
        self.make("Archived")
        path = b.eval("noteCur.value.path")
        b.eval(SPY)
        b.eval("window.__fail={ok:false,message:'Not saved: nope.'}")
        self.type_end("typed before it went")
        b.wait("noteSave.value.state==='error'", 15)
        self.assertEqual(b.eval("noteDirty()"), True)
        b.eval("window.__fail=null; window.__saves.length=0; true")
        b.eval(f"noteGone({json.dumps(path)})")
        b.pump(3.0)                                                                   # longer than the autosave and the retry
        self.assertEqual(b.eval("noteCur.value"), None)
        self.assertEqual(b.eval("noteDirty()"), False)
        self.assertEqual(b.eval("noteSave.value.state"), "")
        self.assertEqual(b.eval("window.__saves"), [], "nothing is sent for a note that has gone")
        self.assertEqual(b.eval("noteUnsavedAtExit()"), False, "and leaving the page is not stopped for it")


    def test_the_page_asks_before_closing_while_typing_could_not_be_saved(self):
        b = self.b
        self.make("Unload")
        b.eval(SPY)
        ask = "(()=>{ const e=new Event('beforeunload',{cancelable:true}); window.dispatchEvent(e); return e.defaultPrevented; })()"
        self.type_end("fine")
        b.wait("noteSave.value.state==='saved'", 15)
        self.assertFalse(b.eval(ask), "saved: leaving is not stopped")
        b.eval("window.__fail={ok:false,message:'Not saved: nope.'}")
        self.type_end(" more")
        b.wait("noteSave.value.state==='error'", 15)
        self.assertTrue(b.eval(ask), "typing that could not be saved: the browser asks")
        b.eval("window.__fail=null")
        b.eval("noteFlush()")
        b.wait("noteSave.value.state==='saved'", 15)
        self.assertFalse(b.eval(ask))

    def test_a_big_note_leaving_the_page_is_saved_without_a_keepalive_request(self):
        b = self.b
        self.make("Big")
        f = self.notes_dir() / "Big.md"
        b.eval(SPY)
        b.eval(NO_TIMER)
        self.type_end("start ")
        b.eval("document.querySelector('.nbody').cxed.editor.commands.insertContent('x'.repeat(100000))")
        b.wait("noteDirty()", 5)
        b.eval("noteFlushOnExit()")
        self.wait_text(f, "x" * 1000, 20)
        last = b.eval("window.__saves")[-1]
        self.assertFalse(last["keepalive"], "over about 60 KB a keepalive request would be refused")
        self.assertGreater(len(last["body"]), 100000)
        b.wait("!noteDirty()", 10)
        self.assertEqual(b.eval("window.__rej"), 0, "no unhandled rejection")


if __name__ == "__main__":
    unittest.main()
