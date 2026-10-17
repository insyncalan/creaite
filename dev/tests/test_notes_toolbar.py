"""#122 the Notes toolbar, Alan's final layout (16-10-2026): ONE line at 900 and 1400 px, grouped into hover menus.

Run: python3 dev/tests/test_notes_toolbar.py   (needs Google Chrome; skipped otherwise)

Done when:
- every one of the 23 old Notes buttons is still reachable (table-driven: where it lives now, and its effect read back from the
  editor's text); Unlink is the link form's Remove link;
- Heading (Text, Heading 1-3, Clear formatting), List (Bulleted, Numbered, Checklist, Indent, Outdent) and Insert ([[ @ #, Table,
  Image) are menus; B I S code, Quote, Link, Undo and Redo are visible;
- a menu opens on hover and folds about 220 ms after the pointer leaves; click, Enter or Down open it with focus inside; arrows
  move, Esc closes with focus back on its button; the bar is one Tab stop with roving arrows; the menu buttons carry
  aria-haspopup="menu" and aria-expanded; Tab and Shift+Tab indent and outdent in a list;
- the bar is one line (every control on one row) at 900 and 1400 px; the Current state and capture drawer bars keep their controls.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
import test_editor_bar as eb  # noqa: E402  (its helpers are borrowed; its own tests run in their own file)
from test_editor_bar import NOTES, SHARED, CURRENT  # noqa: E402

# (the old button, where it lives now: "visible" or the menu, the command id)
OLD_23 = [
    ("h1", "m-heading", "h1"), ("h2", "m-heading", "h2"), ("h3", "m-heading", "h3"),
    ("b", None, "b"), ("i", None, "i"), ("s", None, "s"), ("code", None, "code"),
    ("ul", "m-list", "ul"), ("ol", "m-list", "ol"), ("task", "m-list", "task"),
    ("outdent", "m-list", "outdent"), ("indent", "m-list", "indent"), ("quote", None, "quote"),
    ("link", None, "link"), ("unlink", "link form", "remove"), ("clear", "m-heading", "clear"),
    ("note", "m-insert", "note"), ("person", "m-insert", "person"), ("item", "m-insert", "item"),
    ("table", "m-insert", "table"), ("image", "m-insert", "image"), ("undo", None, "undo"), ("redo", None, "redo"),
]
EFFECT = {   # command: (the text before, then what the text has to match after; the selection is the whole text unless noted)
    "h1": ("x", r"(?m)^# x$"), "h2": ("x", r"(?m)^## x$"), "h3": ("x", r"(?m)^### x$"),
    "b": ("word", r"\*\*word\*\*"), "i": ("word", r"(\*|_)word\1"), "s": ("word", r"~~word~~"), "code": ("word", r"`word`"),
    "ul": ("x", r"(?m)^[-*] x$"), "ol": ("x", r"(?m)^1\. x$"), "task": ("x", r"(?m)^[-*] \[ \] x$"),
    "quote": ("x", r"(?m)^> x$"), "clear": ("**word** x", r"^word x$"),
    "text": ("## x", r"(?m)^x$"),
}


class Toolbar(LiveBrowserCase):
    width, height = 1400, 1000
    mod, memory, ids, pick, make_note, open_current = (eb.Bars.mod, eb.Bars.memory, eb.Bars.ids, eb.Bars.pick, eb.Bars.make_note, eb.Bars.open_current)

    def value(self):
        return self.b.eval("document.querySelector('.nbody').cxed.value()")

    def reset(self, text):
        b = self.b
        b.eval(f"document.querySelector('.nbody').cxed.setValue({text!r})")
        b.eval("document.querySelector('.nbody').cxed.focus('end')")
        b.wait("document.activeElement===document.querySelector('.nbody')", 5)
        b.eval("""(()=>{ const e=document.querySelector('.nbody').cxed.editor; let p=1; e.state.doc.descendants((n,pos)=>{ if(n.isTextblock&&n.content.size) p=pos+n.nodeSize-1; });
          e.commands.setTextSelection(p); })()""")                    # the caret in the last line's text (focus('end') can land after a list)
        b.pump(0.1)

    def select_all(self):
        self.b.eval("document.querySelector('.nbody').cxed.editor.commands.selectAll()")

    def point(self, x, y):
        self.b.call("Input.dispatchMouseEvent", type="mouseMoved", x=x, y=y, button="none")

    def hover(self, sel):
        p = self.b.box(sel)
        self.point(p["x"], p["y"])

    def away(self):
        self.point(5, 900)

    def expanded(self, menu):
        return self.b.eval(f"document.querySelector('.nbar [data-nt={menu}]').getAttribute('aria-expanded')")

    def cmd(self, menu, cmd):
        """Click `cmd` the way a person does: through its menu, or straight on the bar."""
        b = self.b
        if menu is None:
            b.click(f".nbar [data-nt={cmd}]")
        else:
            self.pick(menu, cmd)

    # ---- nothing is lost ------------------------------------------------------------------------------------------------

    def test_all_23_old_buttons_have_a_home_and_the_bar_has_nothing_else(self):
        b = self.b
        self.make_note("Table")
        self.assertEqual(len(OLD_23), 23)
        self.assertEqual(self.ids(".nbar [data-nt]"), NOTES)
        visible = {c for _, w, c in OLD_23 if w is None}
        self.assertEqual({t for t in NOTES if not t.startswith("m-")} - visible, set())
        for menu in ("m-heading", "m-list", "m-insert"):
            b.click(f".nbar [data-nt={menu}]")
            b.wait("!!document.querySelector('.nbar [role=menu] [role^=menuitem]')", 5)
            got = b.eval("[...document.querySelectorAll('.nbar [role=menu] [data-cmd]')].map(x=>x.dataset.cmd)")
            want = [c for _, w, c in OLD_23 if w == menu]
            self.assertEqual(sorted(g for g in got if g != "text"), sorted(want), menu)
            b.key("Escape")
            b.wait("!document.querySelector('.nbar [role=menu]')", 5)
        self.assertEqual(b.eval("document.querySelector('.nbar [data-nt=link]').getAttribute('aria-label')"), "Add or edit a link (⌘⇧K)")

    def test_each_old_command_still_does_its_job_from_where_it_lives(self):
        self.make_note("Effects")
        for old, where, cmd in OLD_23:
            if cmd not in EFFECT:
                continue
            before, rx = EFFECT[cmd]
            with self.subTest(old=old, where=where):
                self.reset(before)
                if cmd in ("b", "i", "s", "code", "clear"):
                    self.select_all()
                self.cmd(where, cmd)
                self.assertRegex(self.value().strip(), rx)

    def test_indent_outdent_undo_redo_and_tab(self):
        b = self.b
        self.make_note("Lists")
        self.reset("- a\n- b")
        self.cmd("m-list", "indent")
        self.assertRegex(self.value(), r"(?m)^  [-*] b$")
        self.cmd("m-list", "outdent")
        self.assertRegex(self.value(), r"(?m)^[-*] b$")
        b.key("Tab")                                           # Tab and Shift+Tab do the same in a list
        b.wait("/^ {2,}[-*] b$/m.test(document.querySelector('.nbody').cxed.value())", 5)
        b.key("Tab", 8)
        b.wait("/^[-*] b$/m.test(document.querySelector('.nbody').cxed.value())", 5)
        self.reset("")
        b.type("abc")
        b.pump(0.3)
        b.click(".nbar [data-nt=undo]")
        b.wait("!document.querySelector('.nbody').cxed.value().includes('abc')", 5)
        b.click(".nbar [data-nt=redo]")
        b.wait("document.querySelector('.nbody').cxed.value().includes('abc')", 5)

    def test_indent_and_outdent_grey_out_outside_a_list(self):
        b = self.b
        self.make_note("Grey")
        self.reset("plain")
        b.click(".nbar [data-nt=m-list]")
        b.wait("!!document.querySelector('.nbar [data-cmd=indent]')", 5)
        for c in ("indent", "outdent"):
            self.assertEqual(b.eval(f"document.querySelector('.nbar [data-cmd={c}]').getAttribute('aria-disabled')"), "true")
        b.key("Escape")

    def test_link_and_its_remove_link(self):
        b = self.b
        self.make_note("Links")
        self.reset("see plan")
        self.select_all()
        b.click(".nbar [data-nt=link]")
        b.wait("!document.querySelector('.nbar .rtelink').hidden", 5)
        self.assertEqual(b.eval("!!document.querySelector('.nbar [data-rl=remove]')"), False)       # nothing to remove yet
        b.type("https://example.com/plan")
        b.key("Enter")
        b.wait("document.querySelector('.nbar .rtelink').hidden", 5)
        self.assertIn("[see plan](https://example.com/plan)", self.value())
        b.click(".nbar [data-nt=link]")                          # the cursor is in the link: the same button edits it, and removes it
        b.wait("!document.querySelector('.nbar .rtelink').hidden", 5)
        b.wait("!!document.querySelector('.nbar [data-rl=remove]')", 5)
        b.click(".nbar [data-rl=remove]")
        b.wait("!document.querySelector('.nbody').cxed.value().includes('](')", 5)
        self.assertIn("see plan", self.value())
        self.assertEqual(b.eval("document.querySelectorAll('.nbar [data-nt=unlink]').length"), 0)

    def test_inserts_hand_over_to_the_host(self):
        b = self.b
        self.make_note("Inserts")
        for cmd, ch in (("note", "[["), ("person", "@"), ("item", "#")):
            self.reset("")
            self.cmd("m-insert", cmd)
            b.wait(f"document.querySelector('.nbody').cxed.value().includes({ch!r})", 5)
            b.wait("!!document.querySelector('#ntpick')", 5)           # the host's own picker opens
            b.key("Escape")
            b.wait("!document.querySelector('#ntpick')", 5)
        self.reset("")
        self.cmd("m-insert", "table")
        b.wait("!!document.querySelector('.nbody table')", 5)
        b.eval("window.__img=0; document.querySelector('.nimgfile').addEventListener('click', e => { window.__img++; e.preventDefault(); }, true)")
        self.cmd("m-insert", "image")
        b.wait("window.__img===1", 5)

    # ---- the menus: hover, keys, names --------------------------------------------------------------------------------------

    def test_a_menu_opens_on_hover_and_folds_after_the_pointer_leaves(self):
        b = self.b
        self.make_note("Hover")
        self.assertEqual(self.expanded("m-list"), "false")
        self.hover(".nbar [data-nt=m-list]")
        b.wait("document.querySelector('.nbar [data-nt=m-list]').getAttribute('aria-expanded')==='true'", 5)
        self.assertTrue(b.eval("!!document.querySelector('.nbar [role=menu]')"))
        self.assertEqual(b.eval("document.activeElement===document.querySelector('.nbody')"), True)       # opened by hover: focus stays in the text
        self.hover(".nbar [role=menu] [data-cmd=ol]")             # moving onto the menu keeps it open
        b.pump(0.5)
        self.assertEqual(self.expanded("m-list"), "true")
        self.hover(".nbar [data-nt=m-heading]")                   # pointing at another folds this one and opens that
        b.wait("document.querySelector('.nbar [data-nt=m-heading]').getAttribute('aria-expanded')==='true'", 5)
        self.assertEqual(self.expanded("m-list"), "false")
        self.away()
        b.pump(0.05)
        self.assertEqual(self.expanded("m-heading"), "true")      # not at once: it waits about 220 ms
        b.wait("document.querySelector('.nbar [data-nt=m-heading]').getAttribute('aria-expanded')==='false'", 3)

    def test_a_click_on_an_open_menus_button_shuts_it_and_one_menu_is_open_at_a_time(self):
        b = self.b
        self.make_note("Toggle")
        self.hover(".nbar [data-nt=m-list]")                      # opened by the pointer ...
        b.wait("document.querySelector('.nbar [data-nt=m-list]').getAttribute('aria-expanded')==='true'", 5)
        b.eval("document.querySelector('.nbar [data-nt=m-heading]').focus()")      # ... the keyboard opening Heading closes it
        b.key("ArrowDown")
        b.wait("document.querySelector('.nbar [data-nt=m-heading]').getAttribute('aria-expanded')==='true'", 5)
        b.wait("document.querySelector('.nbar [data-nt=m-list]').getAttribute('aria-expanded')==='false'", 5)
        self.assertEqual(b.eval("document.querySelectorAll('.nbar [role=menu]').length"), 1)
        b.key("Escape")                                           # Esc still returns focus to the button
        b.wait("document.activeElement===document.querySelector('.nbar [data-nt=m-heading]')", 5)
        self.assertEqual(self.expanded("m-heading"), "false")
        b.eval("document.querySelector('.nbar [data-nt=m-heading]').focus()")      # Heading open by the keyboard ...
        b.key("ArrowDown")
        b.wait("document.querySelector('.nbar [data-nt=m-heading]').getAttribute('aria-expanded')==='true'", 5)
        self.away()
        self.hover(".nbar [data-nt=m-list]")                      # ... pointing at List closes it
        b.wait("document.querySelector('.nbar [data-nt=m-list]').getAttribute('aria-expanded')==='true'", 5)
        self.assertEqual(self.expanded("m-heading"), "false")
        self.assertEqual(b.eval("document.querySelectorAll('.nbar [role=menu]').length"), 1)
        b.pump(0.5)
        b.click(".nbar [data-nt=m-list]")                         # #143: a click on a hover-opened menu keeps it and moves focus in ...
        b.wait("document.activeElement.getAttribute('role') && document.activeElement.getAttribute('role').startsWith('menuitem')", 5)
        self.assertEqual(self.expanded("m-list"), "true")
        b.click(".nbar [data-nt=m-list]")                         # ... and the next click on the open menu's button shuts it
        b.wait("document.querySelector('.nbar [data-nt=m-list]').getAttribute('aria-expanded')==='false'", 5)

    def test_keyboard_opens_with_down_or_enter_and_esc_returns_focus(self):
        b = self.b
        self.make_note("Keys")
        self.reset("x")
        for key in ("ArrowDown", "Enter", " "):
            b.eval("document.querySelector('.nbar [data-nt=m-heading]').focus()")
            b.key(key)
            b.wait("document.querySelector('.nbar [data-nt=m-heading]').getAttribute('aria-expanded')==='true'", 5)
            b.wait("document.activeElement.getAttribute('role') && document.activeElement.getAttribute('role').startsWith('menuitem')", 5)
            self.assertEqual(b.eval("document.activeElement.dataset.cmd"), "text")
            b.key("ArrowDown")
            b.wait("document.activeElement.dataset.cmd==='h1'", 5)
            b.key("End")
            b.wait("document.activeElement.dataset.cmd==='clear'", 5)
            b.key("ArrowUp")
            b.wait("document.activeElement.dataset.cmd==='h3'", 5)
            b.key("Escape")
            b.wait("document.activeElement===document.querySelector('.nbar [data-nt=m-heading]')", 5)
            self.assertEqual(self.expanded("m-heading"), "false")
        b.eval("document.querySelector('.nbar [data-nt=m-heading]').focus()")      # Enter on an item runs it
        b.key("ArrowDown")
        b.wait("document.activeElement.dataset.cmd==='text'", 5)
        b.key("ArrowDown")
        b.key("ArrowDown")
        b.wait("document.activeElement.dataset.cmd==='h2'", 5)
        b.key("Enter")
        b.wait("/^## x$/m.test(document.querySelector('.nbody').cxed.value())", 5)
        self.assertEqual(self.expanded("m-heading"), "false")

    # ---- a keyboard-opened menu's fold must not outlive the menu (review of 46863145: a stale fold took focus out of the note) ----

    def open_heading_by_keyboard(self):
        b = self.b
        b.eval("document.querySelector('.nbar [data-nt=m-heading]').focus()")
        b.key("ArrowDown")
        b.wait("document.querySelector('.nbar [data-nt=m-heading]').getAttribute('aria-expanded')==='true'", 5)
        b.wait("document.activeElement.getAttribute('role') && document.activeElement.getAttribute('role').startsWith('menuitem')", 5)

    def back_in_the_note_then_hover_list_and_type(self, keep):
        """Click back into the note, type, point at List (the pointer opens a menu), type again: nothing may take focus."""
        b = self.b
        b.eval("document.querySelector('.nbody').cxed.focus('end')")
        b.wait("document.activeElement===document.querySelector('.nbody')", 5)
        b.type("abc")
        self.hover(".nbar [data-nt=m-list]")
        b.wait("document.querySelector('.nbar [data-nt=m-list]').getAttribute('aria-expanded')==='true'", 5)
        b.pump(0.4)
        self.assertEqual(b.eval("document.activeElement===document.querySelector('.nbody')"), True, "the stale fold took focus out of the note")
        b.type("def")
        self.assertRegex(self.value(), keep)
        self.away()

    def test_a_closed_keyboard_menu_leaves_no_fold_behind_after_esc(self):
        b = self.b
        self.make_note("Stale esc")
        self.reset("x")
        self.open_heading_by_keyboard()
        b.key("Escape")
        b.wait("document.activeElement===document.querySelector('.nbar [data-nt=m-heading]')", 5)
        self.assertEqual(self.expanded("m-heading"), "false")
        self.back_in_the_note_then_hover_list_and_type(r"xabcdef")

    def test_a_closed_keyboard_menu_leaves_no_fold_behind_after_a_pick(self):
        b = self.b
        self.make_note("Stale pick")
        self.reset("x")
        self.open_heading_by_keyboard()
        b.key("ArrowDown")
        b.key("ArrowDown")
        b.wait("document.activeElement.dataset.cmd==='h2'", 5)
        b.key("Enter")
        b.wait("/^## x$/m.test(document.querySelector('.nbody').cxed.value())", 5)
        self.assertEqual(self.expanded("m-heading"), "false")
        self.back_in_the_note_then_hover_list_and_type(r"(?s)## x.*abcdef")

    def test_esc_puts_focus_on_the_opener_before_the_list_goes_so_the_bar_stays(self):
        b = self.b
        self.make_note("Esc first")
        self.reset("x")
        self.open_heading_by_keyboard()
        b.eval("""(()=>{ window.__seen=[]; const bar=document.querySelector('.nbar'), btn=document.querySelector('.nbar [data-nt=m-heading]');
          window.__obs=new MutationObserver(()=>{ window.__seen.push([!!document.querySelector('.nbar [role=menu]'), document.activeElement===btn, !!document.querySelector('.nbar')&&document.querySelector('.nbar').offsetParent!==null]); });
          window.__obs.observe(bar,{childList:true,subtree:true,attributes:true}); })()""")
        b.key("Escape")
        b.wait("document.activeElement===document.querySelector('.nbar [data-nt=m-heading]')", 5)
        b.pump(0.3)
        # whenever the list was gone, the opener already had focus and the bar was still shown
        bad = b.eval("window.__seen.filter(r=>!r[0] && (!r[1] || !r[2])).length")
        self.assertEqual(bad, 0, "the list went before focus was back on the opener")
        self.assertEqual(b.eval("document.querySelector('.nbar').offsetParent!==null"), True)

    def test_a_keyboard_opened_menu_folds_when_the_pointer_opens_another(self):
        b = self.b
        self.make_note("Fold")
        self.reset("x")
        self.open_heading_by_keyboard()
        self.hover(".nbar [data-nt=m-list]")
        b.wait("document.querySelector('.nbar [data-nt=m-list]').getAttribute('aria-expanded')==='true'", 5)
        self.assertEqual(self.expanded("m-heading"), "false")
        self.assertEqual(b.eval("document.querySelectorAll('.nbar [role=menu]').length"), 1)
        self.assertEqual(b.eval("document.activeElement===document.querySelector('.nbar [data-nt=m-heading]')"), True)    # folded: focus is on its opener, not lost
        self.away()

    def test_enter_and_click_opened_menus_fold_too_when_the_pointer_opens_another(self):
        b = self.b
        self.make_note("Fold more")
        self.reset("x")
        b.eval("document.querySelector('.nbar [data-nt=m-list]').focus()")          # Enter opens List, focus inside
        b.key("Enter")
        b.wait("document.activeElement.getAttribute('role') && document.activeElement.getAttribute('role').startsWith('menuitem')", 5)
        self.hover(".nbar [data-nt=m-heading]")
        b.wait("document.querySelector('.nbar [data-nt=m-heading]').getAttribute('aria-expanded')==='true'", 5)
        self.assertEqual(self.expanded("m-list"), "false")
        self.assertEqual(b.eval("document.querySelectorAll('.nbar [role=menu]').length"), 1)
        self.away()
        b.wait("document.querySelectorAll('.nbar [role=menu]').length===0", 5)
        b.click(".nbar [data-nt=m-list]")                                           # a click opens List with focus inside
        b.wait("document.activeElement.getAttribute('role') && document.activeElement.getAttribute('role').startsWith('menuitem')", 5)
        self.hover(".nbar [data-nt=m-heading]")
        b.wait("document.querySelector('.nbar [data-nt=m-heading]').getAttribute('aria-expanded')==='true'", 5)
        self.assertEqual(self.expanded("m-list"), "false")
        self.assertEqual(b.eval("document.querySelectorAll('.nbar [role=menu]').length"), 1)
        self.away()
        b.wait("document.querySelectorAll('.nbar [role=menu]').length===0", 5)
        self.hover(".nbar [data-nt=m-list]")                                        # hover List, Down moves in ...
        b.wait("document.querySelector('.nbar [data-nt=m-list]').getAttribute('aria-expanded')==='true'", 5)
        b.eval("document.querySelector('.nbar [data-nt=m-list]').focus()")
        b.key("ArrowDown")
        b.wait("document.activeElement.getAttribute('role') && document.activeElement.getAttribute('role').startsWith('menuitem')", 5)
        self.hover(".nbar [data-nt=m-heading]")                                     # ... then the pointer opens Heading
        b.wait("document.querySelector('.nbar [data-nt=m-heading]').getAttribute('aria-expanded')==='true'", 5)
        self.assertEqual(self.expanded("m-list"), "false")
        self.assertEqual(b.eval("document.querySelectorAll('.nbar [role=menu]').length"), 1)

    def test_a_click_on_a_hover_opened_menu_takes_it_so_the_pointer_opening_another_folds_it(self):
        b = self.b
        self.make_note("Click claims")
        self.reset("x")
        self.hover(".nbar [data-nt=m-list]")                                        # the pointer opens List ...
        b.wait("document.querySelector('.nbar [data-nt=m-list]').getAttribute('aria-expanded')==='true'", 5)
        b.pump(0.5)
        b.click(".nbar [data-nt=m-list]")                                           # ... a click moves in (the keyboard has it now) ...
        b.wait("document.activeElement.getAttribute('role') && document.activeElement.getAttribute('role').startsWith('menuitem')", 5)
        self.assertEqual(self.expanded("m-list"), "true")
        self.hover(".nbar [data-nt=m-heading]")                                     # ... so the pointer opening Heading folds it
        b.wait("document.querySelector('.nbar [data-nt=m-heading]').getAttribute('aria-expanded')==='true'", 5)
        self.assertEqual(self.expanded("m-list"), "false")
        self.assertEqual(b.eval("document.querySelectorAll('.nbar [role=menu]').length"), 1)

    def test_a_fold_does_not_pull_focus_back_when_focus_has_already_moved_elsewhere(self):
        b = self.b
        self.make_note("No theft")
        self.reset("x")
        b.click(".nbar [data-nt=m-list]")                                           # List open, focus inside it
        b.wait("document.activeElement.getAttribute('role') && document.activeElement.getAttribute('role').startsWith('menuitem')", 5)
        b.eval("document.querySelector('.nbody').cxed.focus('end')")                # focus into the note without a pointerdown or Tab
        b.wait("document.activeElement===document.querySelector('.nbody')", 5)
        b.type("abc")
        self.hover(".nbar [data-nt=m-heading]")                                     # the pointer opens Heading: List folds
        b.wait("document.querySelector('.nbar [data-nt=m-heading]').getAttribute('aria-expanded')==='true'", 5)
        b.pump(0.4)
        self.assertEqual(self.expanded("m-list"), "false")
        self.assertEqual(b.eval("document.activeElement===document.querySelector('.nbody')"), True, "the fold took focus out of the note")
        b.type("def")
        self.assertRegex(self.value(), r"xabcdef")
        self.away()

    def test_esc_then_down_in_the_same_tick_keeps_the_new_fold(self):
        b = self.b
        self.make_note("Same tick")
        self.reset("x")
        b.eval("""(async()=>{ const bt=document.querySelector('.nbar [data-nt=m-heading]'), key=k=>new KeyboardEvent('keydown',{key:k,bubbles:true,cancelable:true});
          bt.focus(); bt.dispatchEvent(key('ArrowDown')); await new Promise(r=>setTimeout(r,300));      // open by key, focus inside
          document.activeElement.dispatchEvent(key('Escape'));                                          // Esc ...
          for(let i=0;i<4;i++) await Promise.resolve();                                                 // (the close has rendered, its effect has not run)
          bt.dispatchEvent(key('ArrowDown'));                                                           // ... and Down at once
          await new Promise(r=>setTimeout(r,300)); })()""")
        self.assertEqual(self.expanded("m-heading"), "true")
        self.hover(".nbar [data-nt=m-list]")                                        # the pointer opens List: Heading, still the keyboard's, folds
        b.wait("document.querySelector('.nbar [data-nt=m-list]').getAttribute('aria-expanded')==='true'", 5)
        self.assertEqual(self.expanded("m-heading"), "false")
        self.assertEqual(b.eval("document.querySelectorAll('.nbar [role=menu]').length"), 1)
        self.away()

    def test_the_bar_is_one_tab_stop_and_the_menus_are_named(self):
        b = self.b
        self.make_note("Stop")
        self.assertEqual(b.eval("[...document.querySelectorAll('.nbar button[data-nt]')].filter(x=>x.tabIndex===0).length"), 1)
        for m in ("m-heading", "m-list", "m-insert"):
            self.assertEqual(b.eval(f"document.querySelector('.nbar [data-nt={m}]').getAttribute('aria-haspopup')"), "menu")
            self.assertEqual(self.expanded(m), "false")
        self.assertEqual(b.eval("document.querySelector('.nbar').getAttribute('role')"), "toolbar")
        self.assertEqual(b.eval("document.querySelector('.nbody').hasAttribute('aria-haspopup')"), False)          # on the buttons, not the editor
        b.eval("document.querySelector('.nbar button[tabindex=\"0\"]').focus()")
        for expect in ("b", "i", "s", "code", "m-list"):
            b.key("ArrowRight")
            b.wait(f"document.activeElement.dataset.nt==={expect!r}", 5)
        b.key("ArrowDown")
        b.wait("document.querySelector('.nbar [role=menu]')", 5)
        self.assertEqual(b.eval("document.querySelector('.nbar [role=menu]').getAttribute('aria-label')"), "List")
        self.assertEqual(b.eval("[...document.querySelectorAll('.nbar [role=menu] [role^=menuitem]')].map(x=>x.getAttribute('role'))"),
                         ["menuitemradio"] * 3 + ["menuitem"] * 2)
        b.key("Escape")
        b.wait("document.activeElement.dataset.nt==='m-list'", 5)
        self.assertEqual(b.eval("[...document.querySelectorAll('.nbar button[data-nt]')].filter(x=>x.tabIndex===0).map(x=>x.dataset.nt)"), ["m-list"])
        self.assertEqual(b.eval("[...document.querySelectorAll('.nbar button[data-nt]')].filter(x=>{ const r=x.getBoundingClientRect(); return r.width<24||r.height<24; }).length"), 0)

    def test_the_state_at_the_cursor_is_ticked_in_the_menus(self):
        b = self.b
        self.make_note("Ticks")
        self.reset("## x")
        b.click(".nbar [data-nt=m-heading]")
        b.wait("!!document.querySelector('.nbar [data-cmd=h2]')", 5)
        got = b.eval("Object.fromEntries([...document.querySelectorAll('.nbar [role=menuitemradio]')].map(x=>[x.dataset.cmd,x.getAttribute('aria-checked')]))")
        self.assertEqual(got, {"text": "false", "h1": "false", "h2": "true", "h3": "false"})
        b.key("Escape")

    # ---- one line ---------------------------------------------------------------------------------------------------------

    def test_the_bar_is_one_line_at_900_and_1400_and_the_other_bars_keep_their_controls(self):
        b = self.b
        self.make_note("One line")
        probe = """(sel=>{ const bar=document.querySelector(sel), r=bar.getBoundingClientRect();
          const tops=new Set([...bar.querySelectorAll('button[data-nt]')].map(x=>Math.round(x.getBoundingClientRect().top)));
          return { lines:tops.size, h:Math.round(r.height), over:bar.scrollWidth>bar.clientWidth+1,
                   inside:[...bar.querySelectorAll('button[data-nt]')].every(x=>x.getBoundingClientRect().right<=r.right+1) }; })(%s)"""
        for width in (1400, 900):
            b.resize(width, 1000)
            b.pump(0.3)
            got = b.eval(probe % '".nbar"')
            self.assertEqual(got["lines"], 1, f"{width}: {got}")
            self.assertFalse(got["over"], got)
            self.assertTrue(got["inside"], got)
            self.assertLess(got["h"], 50, got)
        b.resize(1400, 1000)
        b.eval("openCapture()")
        b.wait("!document.getElementById('capDrawer').hidden && !!document.querySelector('.capbar [data-nt]')", 10)
        self.assertEqual(self.ids(".capbar [data-nt]"), SHARED)
        b.eval("closeCapture()")
        self.open_current()
        self.assertEqual(self.ids(".inplace .rtebar [data-nt]"), CURRENT)
        self.assertEqual(b.eval("document.querySelectorAll('.inplace .rtebar [aria-haspopup]').length"), 0)


if __name__ == "__main__":
    unittest.main()
