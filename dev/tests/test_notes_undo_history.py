"""#175: in the Notes editor Cmd/Ctrl+Z undoes only the LAST user-led change, as in any editor; autosave never resets the history.
A real browser against the real live server over a throwaway vault.

Run: python3 dev/tests/test_notes_undo_history.py   (needs Google Chrome; skipped otherwise)

  1. type A, B, C as three lines, delete B, retype B2 (an autosave between the steps): each Cmd+Z takes back exactly one step, in order,
     and Cmd+Shift+Z puts them back one at a time;
  2. the same with focus mode entered and left between the steps;
  3. through a save that returns "changed outside creaite" and the dialog's Keep editing: the history is intact;
  4. a title edit (and the rename it causes) keeps the history; switching to another note and back opens the editor afresh: the text is
     kept whole and the undo history of the re-opened note is empty (a fresh editor), which can never lose text;
  5. the toolbar's Undo and Redo buttons use the same history as Cmd+Z and Cmd+Shift+Z, one action per press.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
import test_notes_tab_browser as notes_tab_browser  # noqa: E402

PARAS = "[...document.querySelectorAll('.nbody.ProseMirror > p')].map(p=>p.textContent)"
SELECT_B = ("(()=>{ const p=[...document.querySelectorAll('.nbody.ProseMirror > p')].find(p=>p.textContent==='B'); const r=document.createRange();"
            " r.selectNodeContents(p); const s=getSelection(); s.removeAllRanges(); s.addRange(r); return true; })()")


class UndoHistory(LiveBrowserCase):
    width, height = 1400, 1000
    log, notes_dir, make, type_end = (notes_tab_browser.NotesTab.log, notes_tab_browser.NotesTab.notes_dir, notes_tab_browser.NotesTab.make,
                                      notes_tab_browser.NotesTab.type_end)

    @property
    def mod(self):
        return 4 if self.b.is_mac() else 2

    def paras(self):
        return self.b.eval(PARAS)

    def settle(self, autosave=False):
        """A pause past the history's 500 ms grouping, so each step is its own undo step; optionally wait until the file is written."""
        b = self.b
        if autosave:
            b.wait("noteSave.value.state==='saved'", 15)
        b.pump(0.8)

    def steps(self, hooks=None):
        """Type A, B, C as lines, delete B, retype B2; returns the paragraph lists after each step. `hooks[i]` runs after step i."""
        b, snaps, hooks = self.b, [], hooks or {}
        self.type_end("")
        snaps.append(self.paras())
        plan = [lambda: b.type("A"), lambda: b.key("Enter"), lambda: b.type("B"), lambda: b.key("Enter"), lambda: b.type("C"),
                lambda: (b.eval(SELECT_B), b.key("Delete")), lambda: b.type("B2")]
        autosave = {4, 5, 6}
        for i, act in enumerate(plan):
            act()
            self.settle(autosave=i in autosave)
            if i in hooks:
                hooks[i]()
            snaps.append(self.paras())
        return snaps

    def undo_all(self, snaps):
        b, m = self.b, self.mod
        for k in range(len(snaps) - 2, -1, -1):                                       # Cmd+Z: one step back each time
            b.key("z", m)
            b.pump(0.3)
            self.assertEqual(self.paras(), snaps[k], f"undo to step {k}")
        for k in range(1, len(snaps)):                                                # Cmd+Shift+Z: one step forward each time
            b.key("z", m | 8)
            b.pump(0.3)
            self.assertEqual(self.paras(), snaps[k], f"redo to step {k}")

    def test_1_undo_steps_back_one_action_at_a_time_across_autosaves(self):
        self.make("Undo one")
        snaps = self.steps()
        self.assertEqual(snaps[-1][:3], ["A", "B2", "C"], "the steps built what they should")
        self.assertIn("B2", (self.notes_dir() / "Undo one.md").read_text())
        self.assertNotEqual(snaps[-1], snaps[-2], "the steps differ")
        self.undo_all(snaps)

    def test_2_the_same_with_focus_mode_entered_and_left_between_the_steps(self):
        self.make("Undo focus")
        b, m = self.b, self.mod

        def toggle():
            b.key("F", m | 8)
            b.pump(0.6)
        snaps = self.steps({1: toggle, 3: toggle, 5: toggle, 6: toggle})
        self.assertIn("B2", (self.notes_dir() / "Undo focus.md").read_text())
        b.eval("document.querySelector('.nbody').cxed.focus('end')")
        self.undo_all(snaps)

    def test_3_through_a_changed_outside_conflict_and_keep_editing(self):
        self.make("Undo conflict")
        b, m = self.b, self.mod
        f = self.notes_dir() / "Undo conflict.md"
        b.click("#noteExpand")
        b.wait("noteFocus.value&&document.activeElement===document.querySelector('.nbody')", 5)
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=700, y=500)           # the pointer leaves the expand icon: no hover tip takes the first Esc
        b.pump(0.4)
        snaps = self.steps()
        f.write_text(f.read_text() + "\nsomeone else\n")
        b.type("!")
        b.wait("noteSave.value.state==='conflict'", 15)
        snaps.append(self.paras())
        b.key("Escape")
        b.wait("document.getElementById('noteLeaveDlg').open", 8)
        b.click("[data-nlkeep]")
        b.wait("!document.getElementById('noteLeaveDlg').open", 5)
        self.assertEqual(b.eval("noteFocus.value"), True, "Keep editing: the note stays open")
        b.eval("document.querySelector('.nbody').cxed.focus('end')")
        self.assertEqual(self.paras(), snaps[-1], "the typing is still there")
        self.undo_all(snaps)

    def test_4_title_edit_keeps_history_and_switching_notes_opens_a_fresh_editor_without_losing_text(self):
        self.make("Other note")
        other = self.b.eval("noteCur.value.path")
        self.make("Undo title")
        b, m = self.b, self.mod
        snaps = self.steps()
        b.eval("document.getElementById('noteTitle').focus()")
        b.eval("(()=>{ const i=document.getElementById('noteTitle'); i.select(); return true; })()")
        b.type("Undo title two")
        b.key("Tab")
        b.wait("noteSave.value.state==='saved'", 15)
        b.pump(1.0)
        self.assertEqual(self.paras(), snaps[-1], "a title edit and its rename leave the text alone")
        b.eval("document.querySelector('.nbody').cxed.focus('end')")
        b.key("z", m)
        b.pump(0.3)
        self.assertEqual(self.paras(), snaps[-2], "Cmd+Z after a title edit and rename still steps back one action")
        b.key("z", m | 8)
        b.pump(0.3)
        self.assertEqual(self.paras(), snaps[-1])
        # switch to another note and back: the editor is opened afresh, from the saved file
        mine = b.eval("noteCur.value.path")
        b.eval(f"openNote({other!r})")
        b.wait(f"noteCur.value&&noteCur.value.path==={other!r}&&!!document.querySelector('.nbody.ProseMirror')", 10)
        b.eval(f"openNote({mine!r})")
        b.wait(f"noteCur.value&&noteCur.value.path==={mine!r}&&!!document.querySelector('.nbody.ProseMirror')", 10)
        b.pump(0.5)
        self.assertEqual(self.paras(), snaps[-1], "back on the note: the whole text is there")
        b.eval("document.querySelector('.nbody').cxed.focus('end')")
        b.key("z", m)
        b.pump(0.3)
        self.assertEqual(self.paras(), snaps[-1], "a re-opened note starts a fresh history: Cmd+Z has nothing to undo, and removes nothing")

    def test_5_the_undo_button_does_what_cmd_z_does(self):
        """The toolbar has Undo and Redo buttons (editorProfiles.js: c.undo()); they use the same history, one action per press."""
        self.make("Undo button")
        b = self.b
        snaps = self.steps()
        b.eval("document.querySelector('.nbody').cxed.focus('end')")
        names = b.eval("[...document.querySelectorAll('.ndoc button')].map(x=>x.getAttribute('aria-label')||x.dataset.tip||'')")
        un = next(i for i, n in enumerate(names) if n.lower().startswith("undo"))
        rd = next(i for i, n in enumerate(names) if n.lower().startswith("redo"))
        pick = lambda i: f"[...document.querySelectorAll('.ndoc button')][{i}].click()"
        for k in range(len(snaps) - 2, len(snaps) - 5, -1):
            b.eval(pick(un))
            b.pump(0.3)
            self.assertEqual(self.paras(), snaps[k], f"Undo button to step {k}")
        b.key("z", self.mod)                                                          # the keyboard carries on from where the button left off
        b.pump(0.3)
        self.assertEqual(self.paras(), snaps[len(snaps) - 5])
        b.eval(pick(rd))
        b.pump(0.3)
        self.assertEqual(self.paras(), snaps[len(snaps) - 4], "Redo button")


if __name__ == "__main__":
    unittest.main()
