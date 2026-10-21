"""#124, #255: Delete note in a real browser against the real live server, at 1400 px and 900 px.

Run: python3 dev/tests/test_notes_delete_browser.py   (needs Google Chrome; skipped otherwise)

  - "Delete note…" is last in the note's … menu, in red; it opens the confirm box naming the note, Cancel focused;
  - Cancel (and Esc) closes it and nothing is asked for: no card, the note stays;
  - #255: Delete note moves it into the archive folder (99 Archive today, 99 Archive after #252) at once, with no card (Chrome's own call passes the server's page check): the note
    closes, the list drops it, a toast says "Moved … to the archive", and the toast's Undo brings it back into the list;
  - nothing scrolls sideways at 900 px with the box open;
  - #255: a note saved in another window after it was opened here is not deleted: a plain message, the note stays;
  - #255: Files › Archived's Move back of a deleted note works at once, with Undo; the toast after Undo says what happened
    (back, or back under another name: L3, Jarvis 16-10-2026);
  - Files › Archived: two deleted notes of one name are two rows keyed by their own place in the archive folder (Move back, Open), and Open
    of a deleted note opens that file, never the Notes tab (M2).
Each runs at 1400 px and again at 900 px.
"""
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_notes_tab_browser import NotesTab  # noqa: E402,F401  (its helpers; its own tests run in their own file)

SHOTS = Path.home() / "dev.env/team-stark-shots/notes-124"
WS = "Working session"


# The archive folder's name, as paths.py has it (99 Archive today, 99 Archive after #252), read without importing paths here.
ARCHIVE = re.search(r'^ARCHIVE = "([^"]+)"', (Path(__file__).resolve().parent.parent.parent / "system/scripts/paths.py")
                    .read_text(encoding="utf-8"), re.M).group(1)

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
        return next((self.v.root / "projects").glob("ABC */")) / ARCHIVE / "notes" / f"{WS}.md"

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

    def on_more(self):
        self.b.pump(0.2)
        return self.b.eval("document.activeElement===document.querySelector('.nmorewrap .nmore')")

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
        self.assertTrue(self.on_more(), "Cancel returns focus to the … button")
        self.open_box()
        b.key("Escape")
        b.wait("!document.getElementById('noteDelDlg').open")
        self.assertTrue(self.on_more(), "Esc returns focus to the … button")
        self.assertEqual(self.card(), [])
        self.assertTrue(f.is_file())
        self.open_box()
        self.assertIn("It moves as soon as you press Delete note", b.eval("document.querySelector('#noteDelDlg .sub').textContent"))
        b.click("#ndelGo")                                                                  # #255: Delete note, and it moves
        b.wait("!noteCur.value||noteCur.value.note.title!=='Working session'", 20)
        self.assertEqual(self.card(), [])                                                  # no card, ever
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

    def real_lines(self):
        """The lines tracker._reverse_move really writes, for names with ' as ', quotes and colons: [(name, case, lines)]."""
        import subprocess
        names = ["Plan as built", 'Say "as is": a note', "Notes as a as b"]
        code = ("import sys, json, pathlib; sys.path.insert(0, 'system/scripts')\nimport paths, reach, tracker\n"
                f"notes = pathlib.Path({str(self.notes_dir())!r}); arch = notes.parent / {ARCHIVE!r} / 'notes'; arch.mkdir(parents=True, exist_ok=True)\n"
                f"out = []\nfor n in {names!r}:\n"
                "    def run(on):\n        reach.NOTES_BACK_RENAMES = on; rep = []\n"
                "        tracker._reverse_move({'from': paths.rel(notes / (n + '.md')), 'to': paths.rel(arch / (n + '.md')), 'kind': 'notes'}, rep)\n"
                "        return rep\n"
                "    (arch / (n + '.md')).write_text('x'); (notes / (n + '.md')).write_text('y')\n"
                "    out.append([n, 'renamed', run(True), (notes / (n + '-2.md')).is_file()])\n"
                "    (notes / (n + '-2.md')).unlink(); (notes / (n + '.md')).write_text('y'); (arch / (n + '.md')).write_text('x')\n"
                "    out.append([n, 'taken', run(False), None])\n"
                "    (notes / (n + '.md')).unlink(); (arch / (n + '.md')).unlink()\n"
                "    out.append([n, 'missing', run(True), None])\n"
                "print(json.dumps(out))")
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=self.v.root)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def words(self):
        b = self.b
        self.assertEqual(b.eval("[undoWords({ok:true,moves:[]},'A'), undoWords({ok:true,moves:['odd line']},'A'), undoWords({ok:false,message:'No'},'A')]"),
                         ["“A” is back in its notes folder", "Undo did not restore the note: see Files › Archived", "No"])
        for name, case, lines, made in self.real_lines():
            got = b.eval(f"undoWords({{ok:true,moves:{json.dumps(lines)}}},{json.dumps(name)})")
            want = {"renamed": f"Restored “{name}” as {name}-2.md: a note has its old name",
                    "taken": "Not restored: a note with that name exists",
                    "missing": "Not restored: the archived note is no longer there"}[case]
            self.assertEqual(got, want, (name, case, lines))
            if case == "renamed":
                self.assertTrue(made, lines)

    def changed_elsewhere(self, title):
        """#255: another window saves the note after this one opened it: Delete note moves nothing and says why."""
        b = self.b
        self.make(title)
        b.eval("noteFlush()")
        b.wait("noteSave.value.state==='saved'", 15)
        f = self.notes_dir() / f"{title}.md"
        rel = b.eval("noteCur.value.path")
        other = self.post_api("/api/notes/get", {"path": rel})                               # window 2
        s = self.post_api("/api/notes/save", {"path": rel, "body": "Window two's typing.\n", "base": other["base"]})
        self.assertTrue(s["ok"], s)
        self.open_box()
        b.click("#ndelGo")
        b.wait("document.querySelector('.snack') && document.querySelector('.snack').textContent.includes('Not deleted')", 15)
        self.assertIn("changed since you opened it", b.eval("document.querySelector('.snack').textContent"))
        self.assertTrue(f.is_file())
        self.assertIn("Window two's typing.", f.read_text())
        self.assertEqual(self.card(), [])

    def moved_back(self, title):
        """#255: Files › Archived's Move back of a deleted note: at once, no card, with Undo."""
        b = self.b
        r = self.post_api("/api/notes/new", {"code": "ABC", "template": "blank", "title": title})
        d = self.post_api("/api/notes/delete/now", {"path": r["note"]["path"], "base": r["base"]})     # Chrome's own call
        self.assertTrue(d["ok"], d)
        f = self.notes_dir() / f"{title}.md"
        self.assertFalse(f.exists())
        b.eval("go('files')")
        b.wait("!!document.getElementById('filesTbl')", 15)
        b.eval("refreshFiles(true)")
        b.wait(f"(D.files_archived||[]).some(f=>f.n==={json.dumps(title + '.md')})", 20)
        b.eval("document.querySelector('#fquick [data-q=\"archived\"]').click()")
        sel = f"#filesTbl [data-moveback$={json.dumps('/' + title + '.md')}]"
        b.wait(f"!!document.querySelector({json.dumps(sel)})", 15)
        self.assertEqual(b.eval(f"document.querySelector({json.dumps(sel)}).dataset.mbkind"), "notes")
        b.eval(f"document.querySelector({json.dumps(sel)}).click()")
        for _ in range(150):
            if f.is_file():
                break
            b.pump(0.1)
        self.assertTrue(f.is_file())                                                        # back at once
        b.wait("document.querySelector('.snack') && document.querySelector('.snack').textContent.includes('back to its notes folder')", 10)
        self.assertEqual(self.card(), [])
        b.eval("[...document.querySelectorAll('.snack button')].find(x=>/Undo/.test(x.textContent)).click()")
        for _ in range(150):
            if not f.exists():
                break
            b.pump(0.1)
        self.assertFalse(f.exists())                                                         # Undo: archived again
        self.words()

    def archived_rows(self, title):
        b = self.b
        for word in ("one", "two"):
            r = self.post_api("/api/notes/new", {"code": "ABC", "template": "blank", "title": title})
            d = self.post_api("/api/notes/delete/now", {"path": r["note"]["path"], "base": r["base"]})    # #255: no card
            self.assertTrue(d["ok"], (word, d))
        b.eval("go('files')")
        b.wait("!!document.getElementById('filesTbl')", 15)
        b.eval("refreshFiles(true)")
        b.wait(f"(D.files_archived||[]).filter(f=>f.n.startsWith({json.dumps(title)})).length===2", 20)
        rows = b.eval(f"D.files_archived.filter(f=>f.n.startsWith({json.dumps(title)})).map(f=>[f.path,f.at])")
        self.assertEqual(len({r[0] for r in rows}), 1)                                        # one first name …
        self.assertEqual(len({r[1] for r in rows}), 2)                                        # … two places, two keys
        self.assertFalse(b.eval(f"isNotePath({json.dumps(rows[0][1])})"))                      # Open: the file, not the Notes tab
        self.assertTrue(b.eval(f"isNotePath({json.dumps(rows[0][0])})"))

    def post_api(self, path, body):
        return json.loads(self.b.eval(f"(async()=>JSON.stringify(await api({json.dumps(path)},{json.dumps(body)})))()"))

    def test_delete_note_confirm_then_moved_then_undo(self):
        self.flow()

    def test_at_900(self):
        self.b.resize(900, 1000)
        self.b.wait("innerWidth===900")
        self.flow()

    def test_changed_in_another_window_is_not_deleted(self):
        self.changed_elsewhere("Elsewhere at 1400")

    def test_changed_in_another_window_is_not_deleted_at_900(self):
        self.b.resize(900, 1000)
        self.b.wait("innerWidth===900")
        self.changed_elsewhere("Elsewhere at 900")

    def test_move_back_at_once_with_undo(self):
        self.moved_back("Back at 1400")

    def test_move_back_at_once_with_undo_at_900(self):
        self.b.resize(900, 1000)
        self.b.wait("innerWidth===900")
        self.moved_back("Back at 900")

    def test_archived_rows_keyed_by_their_place(self):
        self.archived_rows("Same at 1400")

    def test_archived_rows_keyed_by_their_place_at_900(self):
        self.b.resize(900, 1000)
        self.b.wait("innerWidth===900")
        self.archived_rows("Same at 900")


del NotesTab

if __name__ == "__main__":
    unittest.main()
