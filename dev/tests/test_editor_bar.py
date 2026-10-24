"""#122 step A: the shared editor foundation in a real browser against the real live server: the profiles, the one toolbar
(components/EditorBar.jsx, core/editorProfiles.js), the aligned checklist and Current state's heading levels.

Run: python3 dev/tests/test_editor_bar.py   (needs Google Chrome; skipped otherwise)

Done when (dev/sprints/one-editor.md, Alan's eight decisions on #122):
- the same toolbar shows the same buttons per profile: notes and current offer the same set minus what current leaves out
  (checklist, code, table, [[ @ #), the capture drawer shows the shared buttons, and the plain profile shows none;
- the checklist's box is centred on its first line (within 2 px) in the light and dark themes, at 900 and 1400 px, and is a
  24 px target;
- the bar works from the keyboard (one Tab stop, arrows, Home, End, Esc) and has a pressed state at the cursor;
- ⌘K stays the command palette (Shift or not, outside an editor); ⌘⇧K is the link form inside a rich editor;
- Current state writes its three heading levels as ###, #### and ##### and never as a line the section's reader would end on.
"""
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

META, SHIFT, CTRL = 4, 8, 2
# #122 final layout: Notes is one line of controls; Heading, List and Insert are hover menus whose items are listed beside them
NOTES = ["m-heading", "b", "i", "s", "code", "m-list", "quote", "link", "m-insert", "undo", "redo"]
NOTES_MENUS = {"m-heading": ["text", "h1", "h2", "h3", "clear"], "m-list": ["ul", "ol", "task", "indent", "outdent"],
               "m-insert": ["note", "person", "item", "table", "image"]}
NOTES_ALL = ["text", "h1", "h2", "h3", "b", "i", "s", "code", "ul", "ol", "task", "outdent", "indent", "quote", "link", "clear",
             "note", "person", "item", "table", "image", "undo", "redo"]      # everything the old 23 buttons did, bar Unlink (now the link form's Remove link)
CURRENT = ["h1", "h2", "h3", "b", "i", "s", "ul", "ol", "outdent", "indent", "quote", "image", "link", "unlink", "clear", "item", "undo", "redo"]
SHARED = ["h1", "h2", "h3", "b", "i", "s", "code", "ul", "ol", "task", "outdent", "indent", "quote", "link", "unlink", "clear", "undo", "redo"]      # the capture drawer: flat, no pickers yet
PROBE = ("### Delivery\n\nPlain **bold** and ~~struck~~ with [a link](https://example.com/plan) and [mail](mailto:pmo@example.com).\n\n"
         "- one\n  - nested\n- two\n\n1. first\n2. second\n\n#### Risks\n\n> a quote\n\n<!-- # inside a comment -->\n\n"
         "##### Detail\n\n# Stray level one\n\nLast line.")
MARKER = "<!-- creaite: second pane -->"
STATE = "### Top\n\nFirst paragraph.\n\n#### Middle\n\nSecond paragraph.\n\n##### Low\n\n- a bullet\n\nLast line."


class Bars(LiveBrowserCase):
    width, height = 1400, 1000

    def mod(self):
        return META if self.b.is_mac() else CTRL

    def memory(self):
        return next((self.v.root / "projects").glob("ABC */CLAUDE.md"))

    def ids(self, sel):
        return self.b.eval(f"[...document.querySelectorAll({sel!r})].map(b=>b.dataset.nt)")

    def pick(self, menu, cmd):
        """Open a bar menu with the pointer and click one item (what a person does)."""
        b = self.b
        b.click(f".nbar [data-nt={menu}]")
        b.wait(f"!!document.querySelector('.nbar [role=menu] [data-cmd={cmd}]')", 5)
        b.click(f".nbar [role=menu] [data-cmd={cmd}]")
        b.wait("!document.querySelector('.nbar [role=menu]')", 5)

    def make_note(self, title="Bar test"):
        b = self.b
        b.eval("go('notes','ABC')")
        b.wait("!!document.getElementById('notesNew')")
        b.click_until("#notesNew", "document.getElementById('newNoteDlg').open")          # #152: a click lost to a redraw is pressed again
        b.eval(f"(()=>{{ const i=document.getElementById('nnTitle'); i.value={title!r}; i.dispatchEvent(new Event('input',{{bubbles:true}})); }})()")
        b.eval("document.querySelector('#newNoteDlg input[value=\"blank\"]').click()")
        b.click("#nnMake")
        b.wait("!!document.querySelector('.nbody.ProseMirror')", 15)
        b.eval("document.querySelector('.nbody').cxed.focus('end')")
        b.wait("document.activeElement===document.querySelector('.nbody')", 5)
        b.frames(3)                                                  # the editor gives itself focus a frame later: let that land first (#152)

    def open_current(self, state=STATE):
        b = self.b
        mem = self.memory()
        text = mem.read_text(encoding="utf-8")
        mem.write_text(re.sub(r"(## Current state\n).*?(?=\n## |\Z)", lambda m: m.group(1) + f"\n{state}\n", text, flags=re.S), encoding="utf-8")
        self.v.run(script="build_dashboard.py")
        b.reload("typeof go==='function' && LIVE")
        b.eval("go('cockpit','ABC')")
        b.wait("document.querySelector('#v-cockpit .curcard [data-edcur]')")
        b.click("#v-cockpit .curcard [data-edcur]")
        b.wait("!!(document.getElementById('curEd')&&document.getElementById('curEd').cxed)")

    # ---- the profiles --------------------------------------------------------------------------------------------------

    def test_the_profile_table_says_what_each_profile_shows(self):
        b = self.b
        got = b.eval("(()=>{ const f=(p,h)=>profileTools(p,h).filter(t=>t!=='|').map(t=>t.id); "
                     "return { notes:f('notes',['note','person','item','table','image']), notesBare:f('notes',[]), current:f('current',['image','item']), "
                     "plain:f('plain',['image']), email:f('email',['image']), none:f('none',[]), capture:f('capture',[]), textsection:f('textsection',['image','table']), textsectionBare:f('textsection',[]), names:Object.keys(ED_PROFILES) }; })()")
        self.assertEqual(got["notes"], NOTES)
        self.assertEqual(got["notesBare"], ["m-heading", "b", "i", "s", "code", "m-list", "quote", "link", "undo", "redo"])      # no Insert menu without a host
        self.assertEqual(got["capture"], SHARED)
        self.assertEqual(got["current"], CURRENT)
        self.assertEqual(got["plain"], [])            # decision 2: plain fields keep plain text, no toolbar
        self.assertEqual(got["email"], [])            # #133: Draft email's preview is the editor's Email feature set, with no toolbar
        self.assertEqual(got["none"], [])
        self.assertEqual(sorted(got["names"]), ["capture", "current", "email", "none", "notes", "plain", "sheet", "textsection"])
        # #218: a report text section has Notes' bar, its Insert menu only for the pickers its host offers (Table and Picture here, never note, person or item)
        self.assertEqual(got["textsection"], NOTES)
        self.assertEqual(got["textsectionBare"], [t for t in NOTES if t != "m-insert"])
        self.assertEqual(sorted(set(NOTES_ALL) - {"unlink"} - set(CURRENT)), sorted(["text", "task", "code", "note", "person", "table"]))

    def test_notes_current_and_the_capture_drawer_draw_their_profile(self):
        b = self.b
        self.make_note()
        self.assertEqual(self.ids(".nbar [data-nt]"), NOTES)
        self.assertEqual(b.eval("document.querySelectorAll('.nbar').length"), 1)
        self.assertEqual(b.eval("document.querySelectorAll('.nbar [data-nt=unlink]').length"), 0)         # Unlink is the link form's Remove link
        self.assertEqual(b.eval("document.querySelector('.nbar').getAttribute('role')"), "toolbar")
        b.eval("openCapture()")
        b.wait("!document.getElementById('capDrawer').hidden && !!document.querySelector('#capBody.ProseMirror')", 10)
        self.assertEqual(self.ids(".capbar [data-nt]"), SHARED)
        b.eval("closeCapture()")
        self.open_current()
        self.assertEqual(self.ids(".inplace .rtebar [data-nt]"), CURRENT)
        self.assertEqual(b.eval("[...document.querySelectorAll('.inplace .rtebar [data-rc]')].length"), len(CURRENT) - 4)   # the old data-rc names stay (not h1 h2 h3, nor the work-item button, #122 C)

    def test_plain_hosts_have_no_toolbar_and_keep_plain_text(self):
        b = self.b
        b.eval("WT='actions'; go('work')")
        b.wait("document.querySelector('#workTbl tbody tr[data-row]')")
        id_ = b.eval("A.find(x=>x.p==='ABC').id")
        b.eval(f"openRecord('actions',{id_!r})")
        b.wait(f"CUR&&CUR.id==={id_!r}&&document.getElementById('panel').classList.contains('peek')")
        b.pump(0.3)
        self.assertEqual(b.eval("document.querySelectorAll('#panel .rtebar').length"), 0)
        b.click("#pkDesc")
        b.eval("pkDesc.cxed.editor.commands.selectAll()")
        b.type("# not a heading")
        b.key("Enter")
        b.type("- [ ] nor a checklist")
        self.assertEqual(b.eval("pkDesc.textContent"), "# not a heading\n- [ ] nor a checklist")
        self.assertEqual(b.eval("pkDesc.querySelectorAll('h1,ul,li,input').length"), 0)

    # ---- the buttons ---------------------------------------------------------------------------------------------------

    def test_headings_one_to_three_in_notes_are_written_with_one_to_three_hashes(self):
        b = self.b
        self.make_note("Headings")
        for n in (1, 2, 3):
            b.type(f"Head {n}")
            self.pick("m-heading", f"h{n}")
            b.eval("document.querySelector('.nbody').cxed.focus('end')")
            b.key("Enter")
            b.key("Enter")                  # a heading ends with Enter; a second makes sure the next line is a paragraph
        md = b.eval("document.querySelector('.nbody').cxed.value()")
        for n in (1, 2, 3):
            self.assertRegex(md, rf"(?m)^{'#' * n} Head {n}$")

    def test_pressed_state_follows_the_cursor(self):
        b = self.b
        self.make_note("Pressed")
        b.type("plain")
        self.assertEqual(b.eval("document.querySelector('.nbar [data-nt=b]').getAttribute('aria-pressed')"), "false")
        b.key("b", self.mod())
        b.type("bold")
        b.wait("document.querySelector('.nbar [data-nt=b]').getAttribute('aria-pressed')==='true'", 5)
        self.pick("m-list", "ul")
        b.click(".nbar [data-nt=m-list]")
        b.wait("!!document.querySelector('.nbar [role=menu] [data-cmd=ul]')", 5)
        self.assertEqual(b.eval("document.querySelector('.nbar [data-cmd=ul]').getAttribute('aria-checked')"), "true")
        self.assertIsNone(b.eval("document.querySelector('.nbar [data-cmd=indent]').getAttribute('aria-disabled')"))
        b.key("Escape")

    def test_keyboard_flow_roving_tabindex_arrows_home_end_and_escape(self):
        b = self.b
        self.make_note("Keys")
        self.assertEqual(b.eval("[...document.querySelectorAll('.nbar button[data-nt]')].filter(x=>x.tabIndex===0).length"), 1)
        b.eval("document.querySelector('.nbar button[tabindex=\"0\"]').focus()")
        self.assertEqual(b.eval("document.activeElement.dataset.nt"), "m-heading")
        b.key("ArrowRight")
        b.wait("document.activeElement.dataset.nt==='b'", 5)
        b.key("End")
        b.wait(f"document.activeElement.dataset.nt==={NOTES[-1]!r}", 5)
        b.key("ArrowRight")                                              # wraps, as Menu does
        b.wait("document.activeElement.dataset.nt==='m-heading'", 5)
        b.key("ArrowLeft")
        b.wait(f"document.activeElement.dataset.nt==={NOTES[-1]!r}", 5)
        b.key("Home")
        b.wait("document.activeElement.dataset.nt==='m-heading'", 5)
        self.assertEqual(b.eval("[...document.querySelectorAll('.nbar button[data-nt]')].filter(x=>x.tabIndex===0).map(x=>x.dataset.nt)"), ["m-heading"])
        b.key("Escape")
        b.wait("document.activeElement===document.querySelector('.nbody')", 5)
        # Enter on a focused button runs it (a click with no mouse) and the cursor goes back to the text
        b.eval("document.querySelector('.nbar [data-nt=quote]').focus()")
        b.key("Enter")
        b.wait("document.querySelector('.nbody blockquote')", 5)

    def test_shortcut_hints_are_announced_the_tab_stop_follows_a_click_and_composing_is_left_alone(self):
        b = self.b
        self.make_note("Small")
        keys = b.eval("Object.fromEntries([...document.querySelectorAll('.nbar button[data-nt]')].filter(x=>x.hasAttribute('aria-keyshortcuts')).map(x=>[x.dataset.nt,x.getAttribute('aria-keyshortcuts')]))")
        self.assertEqual(keys["b"], "Meta+B Control+B")
        self.assertEqual(keys["s"], "Meta+Shift+X Control+Shift+X")
        self.assertEqual(keys["link"], "Meta+Shift+K Control+Shift+K")
        self.assertEqual(b.eval("document.querySelector('.nbar [data-nt=m-heading]').getAttribute('aria-keyshortcuts')"), None)
        b.type("word")
        b.click(".nbar [data-nt=i]")
        stops = "[...document.querySelectorAll('.nbar button[data-nt]')].filter(x=>x.tabIndex===0).map(x=>x.dataset.nt)"
        b.wait(f"{stops}.length===1", 5)                                 # the stop moves on the next render (#152: two stops for a moment on macOS CI)
        self.assertEqual(b.eval(stops), ["i"])
        # a key pressed while an input method is composing is not ⌘⇧K / ⌘⇧X
        b.eval("document.querySelector('.nbody').cxed.focus('end')")
        b.wait("document.activeElement===document.querySelector('.nbody')", 5)
        mac = "true" if b.is_mac() else "false"
        b.eval("""document.activeElement.dispatchEvent(new KeyboardEvent('keydown',{key:'k',metaKey:%s,ctrlKey:%s,shiftKey:true,isComposing:true,bubbles:true,cancelable:true}))""" % (mac, "false" if b.is_mac() else "true"))
        b.pump(0.2)
        self.assertFalse(b.eval("!!document.querySelector('.linkpop')"))
        b.eval("(()=>{ const d=document.getElementById('cmdk'); if(d.open) d.close(); })()")        # (the palette's own key handler is not ours)
        b.eval("document.querySelector('.nbody').cxed.focus('end')")
        b.wait("document.activeElement===document.querySelector('.nbody')", 5)
        b.eval("""document.activeElement.dispatchEvent(new KeyboardEvent('keydown',{key:'k',metaKey:%s,ctrlKey:%s,shiftKey:true,bubbles:true,cancelable:true}))""" % (mac, "false" if b.is_mac() else "true"))
        b.wait("!!document.querySelector('.linkpop')", 5)       # and the same key not composing does open it

    def test_targets_are_24px_and_the_bar_names_every_button(self):
        b = self.b
        self.make_note("Targets")
        small = b.eval("[...document.querySelectorAll('.nbar button[data-nt]')].filter(x=>{ const r=x.getBoundingClientRect(); return r.width<24||r.height<24; }).map(x=>x.dataset.nt)")
        self.assertEqual(small, [])
        self.assertEqual(b.eval("[...document.querySelectorAll('.nbar button[data-nt]')].filter(x=>!x.getAttribute('aria-label')).length"), 0)

    def test_a_wrapping_bar_wraps_by_group_so_no_divider_ends_a_line(self):
        b = self.b
        probe = """(sel=>{ const bar=document.querySelector(sel), out=[]; for(const sep of bar.querySelectorAll('.rtesep')){
          const next=sep.parentElement.querySelector('button'), prev=sep.parentElement.previousElementSibling.querySelector('button:last-of-type');
          out.push({ sep:sep.getBoundingClientRect().top, next:next.getBoundingClientRect().top, hh:sep.getBoundingClientRect().height }); }
          const tops=new Set([...bar.querySelectorAll('button[data-nt]')].map(x=>Math.round(x.getBoundingClientRect().top)));
          return { seps:out, lines:tops.size, small:[...bar.querySelectorAll('button[data-nt]')].filter(x=>{ const r=x.getBoundingClientRect(); return r.width<24||r.height<24; }).length }; })(%s)"""
        self.make_note("Wrap")
        b.eval("openCapture()")
        b.wait("!document.getElementById('capDrawer').hidden && !!document.querySelector('.capbar [data-nt]')", 10)
        for width in (1400, 900):
            b.resize(width, 1000)
            b.pump(0.3)
            for sel in (".nbar", ".capbar"):
                got = b.eval(probe % json.dumps(sel))
                self.assertGreaterEqual(len(got["seps"]), 3, got)
                for sep in got["seps"]:
                    self.assertAlmostEqual(sep["sep"], sep["next"], delta=5, msg=f"{width} {sel}: a divider is on the line of the button after it ({got})")
                    self.assertGreater(sep["hh"], 8, got)
                self.assertEqual(got["small"], 0)               # targets are not shrunk to make it fit
        self.assertEqual(self.b.eval(probe % json.dumps(".nbar"))["small"], 0)

    # ---- the keys ------------------------------------------------------------------------------------------------------

    def test_cmd_k_stays_the_palette_and_cmd_shift_k_is_the_link_in_an_editor(self):
        b = self.b
        mod = self.mod()
        palette = "document.getElementById('cmdk').open"
        b.key("k", mod)
        b.wait(palette, 5)
        b.key("Escape")
        b.wait(f"!({palette})", 5)
        b.key("k", mod | SHIFT)                                          # the palette ignores Shift outside an editor
        b.wait(palette, 5)
        b.key("Escape")
        b.wait(f"!({palette})", 5)
        self.make_note("Link")
        b.type("see the plan")
        b.eval("(()=>{ const e=document.querySelector('.nbody').cxed.editor; const to=e.state.selection.from; e.commands.setTextSelection({from:to-8,to}); })()")
        b.key("k", mod | SHIFT)
        b.wait("!!document.querySelector('.linkpop')", 5)
        self.assertFalse(b.eval(palette))
        b.type("https://example.com/plan")
        b.key("Enter")
        b.wait("!document.querySelector('.linkpop')", 5)
        md = b.eval("document.querySelector('.nbody').cxed.value()")
        self.assertIn("see [the plan](https://example.com/plan)", md)
        b.key("k", mod)                                                  # ⌘K in an editor is still the palette
        b.wait(palette, 5)
        b.key("Escape")

    def test_the_link_form_refuses_other_schemes(self):
        b = self.b
        mod = self.mod()
        self.make_note("Scheme")
        b.type("bad link")
        b.key("a", mod)
        b.click(".nbar [data-nt=link]")
        b.wait("!!document.querySelector('.linkpop')", 5)
        b.type("javascript:alert(1)")
        b.key("Enter")
        self.assertNotIn("javascript", b.eval("document.querySelector('.nbody').cxed.value()"))

    # ---- the checklist -------------------------------------------------------------------------------------------------

    def align(self):
        return self.b.eval("""(()=>{ const out=[]; for(const li of document.querySelectorAll('.nbody ul[data-type=taskList] li')){
          const box=li.querySelector('label input').getBoundingClientRect(), p=li.querySelector('div p'), r=document.createRange(); r.selectNodeContents(p.firstChild);
          const t=r.getClientRects()[0]; const lab=li.querySelector('label'), lc=getComputedStyle(lab), pc=getComputedStyle(p);
          out.push({ box:(box.top+box.bottom)/2, text:(t.top+t.bottom)/2, w:box.width, h:box.height, checked:li.dataset.checked,
            lines:Math.round(p.getBoundingClientRect().height/parseFloat(pc.lineHeight)), label:lab.getBoundingClientRect().height, line:parseFloat(pc.lineHeight),
            labelFlex:lc.display+'/'+lc.alignItems }); } return out; })()""")

    def checklist_note(self):
        self.make_note("Checks")
        long = "A long item that is written so that it wraps onto a second line and then a third line for the box to stay on the first. " * 2
        self.b.eval(f"document.querySelector('.nbody').cxed.editor.commands.setContent({('- [ ] Short item' + chr(10) + '- [x] Done item' + chr(10) + '- [ ] ' + long)!r}, {{contentType:'markdown'}})")
        self.b.wait("document.querySelectorAll('.nbody ul[data-type=taskList] li').length===3", 5)

    def test_the_checkbox_is_centred_on_the_first_line_light_dark_900_and_1400(self):
        b = self.b
        self.checklist_note()
        for width in (1400, 900):
            b.resize(width, 1000)
            for theme in ("light", "dark"):
                b.eval(f"document.documentElement.dataset.theme={theme!r}")
                b.pump(0.2)
                rows = self.align()
                self.assertEqual(len(rows), 3)
                for r in rows:
                    self.assertLessEqual(abs(r["box"] - r["text"]), 1, f"{width} {theme}: {r}")     # the box's centre is the first line's centre
                    self.assertAlmostEqual(r["label"], r["line"], delta=1, msg=f"the label is one line tall: {r}")   # the label rule itself
                    self.assertEqual(r["labelFlex"], "flex/center", r)
                    self.assertGreaterEqual(r["w"], 24, r)             # the click target stays 24 px
                    self.assertGreaterEqual(r["h"], 24, r)
                self.assertGreaterEqual(rows[2]["lines"], 3, rows[2])     # the long item wraps: the box stays on its first line

    def test_the_checkbox_is_still_a_24px_target_in_forced_colours(self):
        b = self.b
        self.checklist_note()
        b.call("Emulation.setEmulatedMedia", features=[{"name": "forced-colors", "value": "active"}])
        b.pump(0.3)
        for r in self.align():
            self.assertGreaterEqual(r["w"], 24, r)
            self.assertGreaterEqual(r["h"], 24, r)
            self.assertLessEqual(abs(r["box"] - r["text"]), 1, r)

    def test_a_checkbox_toggles_and_the_checklist_is_in_notes_only(self):
        b = self.b
        self.checklist_note()
        b.click(".nbody ul[data-type=taskList] li:first-child label input")
        self.assertIn("- [x] Short item", b.eval("document.querySelector('.nbody').cxed.value()"))
        self.open_current()
        self.assertEqual(b.eval("document.querySelectorAll('#curEd ul[data-type=taskList]').length"), 0)
        self.assertIsNone(b.eval("document.querySelector('.inplace .rtebar [data-nt=task]')"))

    # ---- forced colours and dark -----------------------------------------------------------------------------------------

    def test_pressed_and_disabled_are_visible_in_dark_and_forced_colours(self):
        b = self.b
        self.make_note("Colours")
        b.type("x")
        b.click(".nbar [data-nt=b]")
        b.click(".nbar [data-nt=m-list]")                                  # outside a list, Indent is greyed
        b.wait("!!document.querySelector('.nbar [data-cmd=indent]')", 5)
        probe = ("(()=>{ const s=n=>{ const e=document.querySelector('.nbar [data-nt='+n+'],.nbar [data-cmd='+n+']'), c=getComputedStyle(e); "
                 "return [c.backgroundColor,c.color,c.opacity]; }; return { on:s('b'), off:s('i'), dis:s('indent') }; })()")
        b.eval("document.documentElement.dataset.theme='dark'")
        got = b.eval(probe)
        self.assertNotEqual(got["on"][0], got["off"][0])                  # pressed shows in dark
        self.assertNotEqual(got["dis"][2], "1")                           # disabled is dimmed
        b.call("Emulation.setEmulatedMedia", features=[{"name": "forced-colors", "value": "active"}])
        b.pump(0.3)
        got = b.eval(probe)
        self.assertNotEqual(got["on"][0], got["off"][0], "pressed shows in forced colours")
        self.assertEqual(got["dis"][2], "1")                              # forced colours dims with GrayText instead
        self.assertNotEqual(got["dis"][1], got["off"][1])

    # ---- Current state: heading levels -----------------------------------------------------------------------------------

    def section(self):
        return re.search(r"## Current state\n(.*?)(?=\n## |\Z)", self.memory().read_text(encoding="utf-8"), re.S).group(1).strip()

    def save(self):
        b = self.b
        b.eval("document.getElementById('snackT').textContent=''")
        b.key("Enter", self.mod())
        b.wait("/— saved|Not saved/i.test(document.getElementById('snackT').textContent)", 20)
        return b.eval("document.getElementById('snackT').textContent")

    def test_current_state_stored_headings_open_as_heading_one_to_three_and_save_back_the_same(self):
        b = self.b
        self.open_current()
        self.assertEqual(b.eval("[...document.querySelectorAll('#curEd h1,#curEd h2,#curEd h3')].map(h=>h.tagName+':'+h.textContent)"),
                         ["H1:Top", "H2:Middle", "H3:Low"])
        self.assertEqual(b.eval("edValue(curEd)"), STATE)                  # untouched: as it came
        b.eval("curEd.cxed.focus('end')")
        b.wait("document.activeElement===curEd", 5)
        b.type(" More.")                                                   # touched: the exact writer, shifted back out
        self.assertEqual(b.eval("edValue(curEd)"), STATE.replace("Last line.", "Last line. More."))
        # the toolbar's three levels write ###, #### and #####
        b.key("Enter")
        b.key("Enter")
        for n in (1, 2, 3):
            b.type(f"New {n}")
            b.click(f".inplace .rtebar [data-nt=h{n}]")
            b.key("Enter")
            b.key("Enter")
        value = b.eval("edValue(curEd)")
        for n in (1, 2, 3):
            self.assertRegex(value, rf"(?m)^{'#' * (n + 2)} New {n}$")
        self.assertFalse(re.search(r"(?m)^#{1,2} ", value), "no heading level that would end the section")
        self.assertIn("— saved", self.save())
        sec = self.section()
        self.assertFalse(re.search(r"(?m)^#{1,2} ", sec), sec)
        for line in ("### Top", "#### Middle", "##### Low", "### New 1", "#### New 2", "##### New 3"):
            self.assertIn(line, sec)
        # the rest of the file is where it was: the section did not swallow or lose the next one
        text = self.memory().read_text(encoding="utf-8")
        self.assertGreater(len(re.findall(r"(?m)^## ", text)), 1)

    def test_the_read_view_draws_the_three_levels_as_the_python_readers_do(self):
        self.assertEqual(self.b.eval("mdHtml('### A\\n\\n#### B\\n\\n##### C\\n\\ntext')"), "<h3>A</h3><h4>B</h4><h5>C</h5><p>text</p>")

    def test_a_pasted_heading_lands_as_the_matching_level(self):
        b = self.b
        self.open_current()
        b.eval("curEd.cxed.focus('end')")
        b.wait("document.activeElement===curEd", 5)
        b.key("Enter")
        b.eval("""(()=>{ const dt=new DataTransfer(); dt.setData('text/html','<h1>Pasted one</h1><h2>Pasted two</h2><h3>Pasted three</h3>');
          curEd.dispatchEvent(new ClipboardEvent('paste',{clipboardData:dt,bubbles:true,cancelable:true})); })()""")
        b.wait("edValue(curEd).includes('Pasted three')", 5)
        v = b.eval("edValue(curEd)")
        for n, w in ((3, "one"), (4, "two"), (5, "three")):
            self.assertIn(f"{'#' * n} Pasted {w}", v)

    # ---- the review's findings (editor-122a2): a reversible mapping and no level above three -----------------------------

    def test_the_mapping_is_reversible_and_leaves_other_hash_lines_as_text(self):
        b = self.b
        text = PROBE.replace("<!-- # inside a comment -->", "<!--\n# inside a comment\n-->")      # the page's reader joins a comment; the mapping must not care
        typed = "# a\n\n## b\n\n### c\n\n#### d\n\n##### e\n\n###### f"
        maps = b.eval(f"(()=>{{ const t={json.dumps(text)}; return {{ in:headsIn(t,2), back:headsOut(headsIn(t,2),2), typed:headsOut({json.dumps(typed)},2) }}; }})()")
        self.assertEqual(maps["back"], text)                                    # in then out: the same bytes
        self.assertIn("\n\u200b# Stray level one\n", maps["in"])                # a stray level one is kept as text, with its #
        self.assertTrue(maps["in"].startswith("# Delivery\n"))                  # ### is the editor's first level
        self.assertIn("\n<!--\n# inside a comment\n-->\n", maps["in"])         # a comment is left alone
        self.assertEqual(maps["typed"].split("\n\n"), ["### a", "#### b", "##### c", "##### d", "##### e", "##### f"])   # above 3 clamps
        # escapes nest: a line that already starts with the zero-width space comes back as it was
        odd = "\u200b# x\n\n## y\n\n###### z\n\n```\n# code\n```"
        self.assertEqual(b.eval(f"headsOut(headsIn({json.dumps(odd)},2),2)"), odd)

    def test_current_state_with_a_stray_level_one_saves_byte_for_byte_after_an_edit_elsewhere(self):
        b = self.b
        self.open_current(PROBE)
        self.assertEqual(b.eval("[...document.querySelectorAll('#curEd h1,#curEd h2,#curEd h3')].map(h=>h.tagName+':'+h.textContent)"),
                         ["H1:Delivery", "H2:Risks", "H3:Detail"])
        self.assertIn("# Stray level one", b.eval("curEd.textContent"))          # shown as text, not as a heading
        self.assertEqual(b.eval("edValue(curEd)"), PROBE)                          # untouched
        b.eval("curEd.cxed.focus('end')")
        b.wait("document.activeElement===curEd", 5)
        b.type("x")
        b.key("Backspace")
        self.assertEqual(b.eval("curEd.cxed.touched()"), True)                   # the exact writer ran
        self.assertEqual(b.eval("edValue(curEd)"), PROBE)                          # and gave every byte back, the stray line too

    def test_current_state_has_no_heading_level_above_three(self):
        b = self.b
        self.open_current()
        b.eval("curEd.cxed.focus('end')")
        b.wait("document.activeElement===curEd", 5)
        for hashes in ("####", "#####", "######"):
            b.key("Enter")
            b.type(f"{hashes} Typed {len(hashes)}")
            b.pump(0.1)
        self.assertEqual(b.eval("document.querySelectorAll('#curEd h4,#curEd h5,#curEd h6').length"), 0)
        value = b.eval("edValue(curEd)")
        self.assertFalse(re.search(r"(?m)^#{6} ", value), value)
        self.assertEqual(len(re.findall(r"(?m)^####[^#]", value)), 1, value)      # only Middle: nothing typed is stored as Heading 2
        self.assertIn("#### Typed 4", b.eval("curEd.textContent"))               # typed hashes past three stay text
        # whatever level the editor did produce (a paste, a command) is clamped on the way out
        self.assertEqual(b.eval("headsOut('#### x\\n\\n###### y',2)"), "##### x\n\n##### y")


if __name__ == "__main__":
    unittest.main()
