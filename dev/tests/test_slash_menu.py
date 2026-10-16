"""#122 step B: the `/` menu at the caret and headings 1 to 3, in a real browser against the real live server
(components/SlashMenu.jsx, core/caretPlace.js, core/editorProfiles.js ED_SLASH).

Run: python3 dev/tests/test_slash_menu.py   (needs Google Chrome; skipped otherwise)

Done when (#118, #122, the engineering input on #117):
- the menu opens AT THE CARET in Notes (header present, scrolled editor) and in Current state: its top is the caret's bottom within a few
  px, at 1400 and 900; near the bottom of the window it flips above; it follows scroll and stays inside the window (the old menu dropped by
  the height of the note header and never flipped);
- the rows come from the profile table: Notes all groups, Current state no checklist or code, the plain profile no menu;
- typing narrows (name and description); arrows and Enter insert; Enter removes the "/query" and writes the right block; Esc closes and
  leaves the text; a click on a row inserts;
- Heading 1 to 3 write # ## ### in Notes and ### #### ##### in Current state (read back with value());
- it opens only at the start of a line or after a space, in a paragraph: not inside a word or an address, a code block or code, a link;
- a composition (IME) never opens it; screen-reader roles (listbox, group, option, aria-activedescendant);
- the [[ @ # lists in Notes are placed at the caret too.
"""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

META = 4
MENU = "document.querySelector('.slashmenu, #ntpick')"
NOTES_ROWS = ["text", "h1", "h2", "h3", "ul", "ol", "task", "quote", "codeblock", "table", "image", "item", "person", "note"]
CURRENT_ROWS = ["text", "h1", "h2", "h3", "ul", "ol", "quote", "image"]
STATE = "### Top\n\nFirst paragraph.\n\n#### Middle\n\nSecond paragraph."
LONG = "\n\n".join(f"Paragraph {i} of a long note so that the editor scrolls." for i in range(1, 40))


class Slash(LiveBrowserCase):
    width, height = 1400, 1000

    def memory(self):
        return next((self.v.root / "projects").glob("ABC */CLAUDE.md"))

    def make_note(self, title="Slash test", body=None, focus=True):
        b = self.b
        b.eval("go('notes','ABC')")
        b.wait("!!document.getElementById('notesNew')")
        b.click("#notesNew")
        b.wait("document.getElementById('newNoteDlg').open")
        b.eval(f"(()=>{{ const i=document.getElementById('nnTitle'); i.value={title!r}; i.dispatchEvent(new Event('input',{{bubbles:true}})); }})()")
        b.eval("document.querySelector('#newNoteDlg input[value=\"blank\"]').click()")
        b.click("#nnMake")
        b.wait("!!document.querySelector('.nbody.ProseMirror') && !document.getElementById('newNoteDlg').open", 15)          # the dialog has closed (it hands focus back to its opener as it does), so nothing takes focus from the editor later
        if body:
            b.eval(f"document.querySelector('.nbody').cxed.editor.commands.setContent({body!r}, {{contentType:'markdown'}})")
        if focus:
            b.wait("(()=>{ const e=document.querySelector('.nbody'); if(document.activeElement!==e) e.cxed.focus('end'); return document.activeElement===e; })()", 10)

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
        b.eval("curEd.cxed.focus('end')")
        b.wait("document.activeElement===curEd", 5)

    def geometry(self, root=".nbody"):
        """The caret's box, the menu's box and the note header's height, in window coordinates."""
        return self.b.eval(f"""(()=>{{ const el=document.querySelector({root!r}), v=el.cxed.editor.view, c=v.coordsAtPos(v.state.selection.from),
          m={MENU}, r=m&&m.getBoundingClientRect(), hd=document.querySelector('.nhead');
          return {{ caret:{{top:c.top,bottom:c.bottom,left:c.left}}, menu:r?{{top:r.top,bottom:r.bottom,left:r.left,right:r.right,height:r.height}}:null,
            side:m&&m.dataset.side, pos:m&&getComputedStyle(m).position, header:hd?hd.getBoundingClientRect().height:0, vh:innerHeight, vw:document.documentElement.clientWidth }}; }})()""")

    def mid(self, para=20):
        """The caret at the end of paragraph `para` of the long body, and that line scrolled to the middle of the window."""
        b = self.b
        b.eval(f"""(()=>{{ const e=document.querySelector('.nbody').cxed.editor; let n=0, at=1; e.state.doc.forEach((node,pos)=>{{ n++; if(n=={para}) at=pos+node.nodeSize-1; }});
          e.commands.focus(); e.commands.setTextSelection(at); }})()""")
        b.key("Enter")
        b.eval(f"({self.scroller()})(innerHeight/2)")
        b.pump(0.2)

    def open_menu(self, root=".nbody"):
        self.b.type("/")
        self.b.wait(f"!!{MENU}", 5)
        self.b.pump(0.15)
        return self.geometry(root)

    def rows(self):
        return self.b.eval("[...document.querySelectorAll('.slashmenu [role=option][data-slash]')].map(o=>o.dataset.slash)")

    def scroller(self):
        """Scroll whatever scrolls so the caret's bottom sits `to` px above the window's bottom."""
        return """(to)=>{ const v=document.querySelector('.nbody').cxed.editor.view; let n=v.dom.parentElement, hit=null;
          while(n&&n!==document.body){ const o=getComputedStyle(n).overflowY; if((o==='auto'||o==='scroll')&&n.scrollHeight>n.clientHeight){ hit=n; break; } n=n.parentElement; }
          const c=v.coordsAtPos(v.state.selection.from), d=c.bottom-(innerHeight-to);
          if(hit) hit.scrollTop+=d; else window.scrollBy(0,d); }"""

    # ---- the position bug and the fix ----------------------------------------------------------------------------------

    def check_at_caret(self, g, why):
        self.assertIsNotNone(g["menu"], why)
        self.assertGreater(g["header"], 20, "the note header is present")
        self.assertEqual(g["pos"], "fixed", why)
        self.assertLessEqual(abs(g["menu"]["top"] - (g["caret"]["bottom"] + 4)), 4, f"{why}: {g}")
        self.assertGreaterEqual(g["menu"]["left"], 0)
        self.assertLessEqual(g["menu"]["right"], g["vw"])

    def test_the_menu_opens_at_the_caret_in_notes_at_1400_and_900(self):
        b = self.b
        self.make_note("At the caret", LONG)
        for width in (1400, 900):
            b.resize(width, 1000)
            self.mid(20 + (width == 900))
            g = self.open_menu()
            self.check_at_caret(g, f"{width} middle of the note")
            b.key("Escape")
        # the middle of the note, in a list
        b.resize(1400, 1000)
        b.eval("document.querySelector('.nbody').cxed.editor.commands.setContent('Intro\\n\\n- one\\n- two\\n\\nOutro', {contentType:'markdown'})")
        b.eval("(()=>{ const e=document.querySelector('.nbody').cxed.editor; let p=0; e.state.doc.descendants((n,pos)=>{ if(n.isText&&n.text==='two') p=pos+3; }); e.commands.focus(); e.commands.setTextSelection(p); })()")
        b.key("Enter")
        b.pump(0.2)
        g = self.open_menu()
        self.check_at_caret(g, "inside a list")

    def test_it_flips_above_near_the_bottom_follows_scroll_and_stays_in_the_window(self):
        b = self.b
        b.resize(1400, 700)
        self.make_note("Flip", LONG)
        self.mid(20)
        b.type("/")
        b.wait(f"!!{MENU}", 5)
        b.eval(f"({self.scroller()})(60)")                 # the caret 60 px above the bottom of the window: no room below for 360 px
        b.pump(0.3)
        g = self.geometry()
        self.assertEqual(g["side"], "above", g)
        self.assertLessEqual(g["menu"]["bottom"], g["caret"]["top"] + 1, g)
        self.assertGreaterEqual(g["menu"]["top"], 0)
        self.assertLessEqual(g["menu"]["bottom"], g["vh"])
        # scroll the other way: back below the caret and still attached to it
        b.eval(f"({self.scroller()})(500)")
        b.pump(0.3)
        g = self.geometry()
        self.assertEqual(g["side"], "below", g)
        self.assertLessEqual(abs(g["menu"]["top"] - (g["caret"]["bottom"] + 4)), 4, g)
        # a short window: it takes the side with room and is cut to fit, never off the window
        b.resize(1400, 420)
        b.pump(0.3)
        g = self.geometry()
        self.assertGreaterEqual(g["menu"]["top"], 0, g)
        self.assertLessEqual(g["menu"]["bottom"], g["vh"], g)

    def test_the_menu_opens_at_the_caret_in_current_state(self):
        b = self.b
        for width in (1400, 900):
            b.resize(width, 1000)
            self.open_current()
            b.key("Enter")
            g = self.open_menu("#curEd")
            self.assertIsNotNone(g["menu"])
            self.assertEqual(g["pos"], "fixed")
            self.assertLessEqual(abs(g["menu"]["top"] - (g["caret"]["bottom"] + 4)), 4, g)
            b.key("Escape")

    def test_in_current_state_escape_closes_the_menu_and_does_not_cancel_the_edit_and_tab_does_not_indent(self):
        b = self.b
        self.open_current()
        b.key("Enter")
        b.type("/")
        b.wait(f"!!{MENU}", 5)
        b.key("Escape")
        b.wait(f"!{MENU}", 5)
        self.assertTrue(b.eval("!!shared.CURED && document.activeElement===curEd && !document.getElementById('discardBar').classList.contains('on')"))
        self.assertTrue(b.eval("curEd.textContent.endsWith('/')"))
        b.key("Backspace")
        b.type("- one")
        b.key("Enter")
        b.type("/bull")
        b.wait(f"!!{MENU}", 5)
        b.key("Tab")                                      # inserts the row (a bulleted list in a list item), not an indent
        b.wait(f"!{MENU}", 5)
        self.assertNotIn("/bull", b.eval("curEd.textContent"))
        self.assertTrue(b.eval("!!shared.CURED"))

    def test_the_square_bracket_at_and_hash_lists_are_placed_at_the_caret_too(self):
        b = self.b
        self.make_note("Lists at the caret", LONG)
        self.mid(20)
        b.type("See [[")
        b.wait("!!document.querySelector('#ntpick')", 5)
        b.pump(0.15)
        g = self.geometry()
        self.assertEqual(g["pos"], "fixed")
        self.assertLessEqual(abs(g["menu"]["top"] - (g["caret"]["bottom"] + 4)), 4, g)

    # ---- the rows ------------------------------------------------------------------------------------------------------

    def test_notes_offers_every_group_and_current_state_leaves_out_what_it_cannot_store(self):
        b = self.b
        self.make_note("Rows")
        self.open_menu()
        self.assertEqual(self.rows(), [r for r in NOTES_ROWS if r != "codeblock" or "codeBlock" in b.eval("Object.keys(document.querySelector('.nbody').cxed.editor.schema.nodes)")]
                         + [x for x in self.rows() if x.startswith("tpl:")])
        self.assertEqual(b.eval("[...document.querySelectorAll('.slashmenu [role=group]')].map(g=>g.getAttribute('aria-label'))"),
                         ["Text", "Lists", "Blocks", "Link"] + (["Templates"] if any(r.startswith("tpl:") for r in self.rows()) else []))
        self.assertNotIn("Sub-heading", b.eval("document.querySelector('.slashmenu').textContent"))
        self.open_current()
        b.key("Enter")
        self.open_menu("#curEd")
        self.assertEqual(self.rows(), CURRENT_ROWS)

    def test_the_profile_table_and_the_plain_profile_has_no_menu(self):
        b = self.b
        got = b.eval("""(()=>{ const f=(p,h)=>slashRows(p,h,null).map(r=>r.id); return { plain:f('plain',['table','image','item']), none:f('none',['image']),
          notes:f('notes',['item','person','note','table','image']), current:f('current',['image']), currentNoHost:f('current',[]), h:f('notes',[],null,'h') }; })()""")
        self.assertEqual(got["plain"], [])
        self.assertEqual(got["none"], [])
        self.assertEqual(got["current"], CURRENT_ROWS)
        self.assertEqual(got["currentNoHost"], [r for r in CURRENT_ROWS if r != "image"])
        self.assertNotIn("task", got["current"])
        b.eval("WT='actions'; go('work')")
        b.wait("document.querySelector('#workTbl tbody tr[data-row]')")
        id_ = b.eval("A.find(x=>x.p==='ABC').id")
        b.eval(f"openRecord('actions',{id_!r})")
        b.wait(f"CUR&&CUR.id==={id_!r}&&document.getElementById('panel').classList.contains('peek')")
        b.pump(0.3)
        b.click("#pkDesc")
        b.eval("pkDesc.cxed.editor.commands.selectAll()")
        b.type("/")
        b.pump(0.2)
        self.assertEqual(b.eval("document.querySelectorAll('.slashmenu,.slashroot').length"), 0)
        self.assertEqual(b.eval("pkDesc.textContent"), "/")

    def test_typing_narrows_by_name_and_description_and_no_match_is_said(self):
        b = self.b
        self.make_note("Filter")
        self.open_menu()
        b.type("head")
        b.pump(0.1)
        self.assertEqual(self.rows(), ["h1", "h2", "h3"])
        b.key("Backspace"); b.key("Backspace"); b.key("Backspace"); b.key("Backspace")
        b.type("h")
        self.assertTrue({"h1", "h2", "h3"} <= set(self.rows()))                   # "h" matches the headings
        b.key("Backspace")
        b.type("tick")                                                            # a description: "Tick things off"
        self.assertEqual(self.rows(), ["task"])
        b.type("zzz")
        b.pump(0.1)
        self.assertEqual(b.eval("document.querySelector('.slashmenu .none').textContent"), "No match")
        self.assertEqual(self.rows(), [])
        b.key("Enter")                                                            # nothing to insert: the menu closes, the text stays
        self.assertEqual(b.eval(f"!!{MENU}"), False)
        self.assertIn("/tickzzz", b.eval("document.querySelector('.nbody').textContent"))

    def test_rows_are_at_least_24px_and_the_menu_has_its_roles(self):
        b = self.b
        self.make_note("Roles")
        self.open_menu()
        self.assertEqual(b.eval("document.querySelector('.slashmenu').getAttribute('role')"), "listbox")
        self.assertEqual(b.eval("[...document.querySelectorAll('.slashmenu [role=option]')].filter(o=>o.getBoundingClientRect().height<24).length"), 0)
        self.assertGreaterEqual(b.eval("document.querySelectorAll('.slashmenu [role=group]').length"), 3)
        self.assertEqual(b.eval("document.querySelectorAll('.slashmenu [aria-selected=true]').length"), 1)
        active = b.eval("document.querySelector('.nbody .ProseMirror, .nbody.ProseMirror').getAttribute('aria-activedescendant')")
        self.assertEqual(active, b.eval("document.querySelector('.slashmenu [aria-selected=true]').id"))
        b.key("ArrowDown")
        b.pump(0.1)
        self.assertEqual(b.eval("document.querySelector('.nbody.ProseMirror, .nbody .ProseMirror').getAttribute('aria-activedescendant')"),
                         b.eval("document.querySelector('.slashmenu [aria-selected=true]').id"))
        self.assertEqual(b.eval("document.querySelector('.slashmenu [aria-selected=true]').dataset.slash"), "h1")
        b.key("Escape")
        self.assertFalse(b.eval("document.querySelector('.nbody.ProseMirror, .nbody .ProseMirror').hasAttribute('aria-activedescendant')"))

    # ---- inserting -------------------------------------------------------------------------------------------------------

    def test_enter_inserts_the_row_and_removes_the_typed_query(self):
        b = self.b
        self.make_note("Insert")
        b.type("/bull")
        b.wait(f"!!{MENU}", 5)
        b.key("Enter")
        b.wait(f"!{MENU}", 5)
        b.type("first")
        md = b.eval("document.querySelector('.nbody').cxed.value()")
        self.assertRegex(md, r"(?m)^[-*] first$")
        self.assertNotIn("/bull", md)
        b.key("Enter"); b.key("Enter")
        b.type("/quo")
        b.key("Enter")
        b.type("said")
        self.assertRegex(b.eval("document.querySelector('.nbody').cxed.value()"), r"(?m)^> said$")
        b.key("Enter"); b.key("Enter")
        b.type("/tick")
        b.key("Enter")
        b.type("do it")
        self.assertIn("- [ ] do it", b.eval("document.querySelector('.nbody').cxed.value()"))

    def test_a_click_on_a_row_inserts_it(self):
        b = self.b
        self.make_note("Click")
        b.type("/")
        b.wait(f"!!{MENU}", 5)
        b.click(".slashmenu [data-slash=h2]")
        b.wait(f"!{MENU}", 5)
        b.type("Clicked")
        self.assertRegex(b.eval("document.querySelector('.nbody').cxed.value()"), r"(?m)^## Clicked$")

    def test_a_host_row_hands_over_to_the_host_after_removing_the_query(self):
        b = self.b
        self.make_note("Host rows")
        b.type("/tabl")
        b.key("Enter")
        b.wait("!!document.querySelector('.nbody table')", 5)
        self.assertNotIn("/tabl", b.eval("document.querySelector('.nbody').textContent"))
        self.make_note("Host rows 2")
        b.type("/work")                                   # "Work item": types a # and the item picker takes over
        b.key("Enter")
        b.wait("!!document.querySelector('#ntpick')", 5)
        self.assertEqual(b.eval("document.querySelector('.nbody').textContent"), "#")

    def test_escape_closes_and_leaves_the_text_and_it_does_not_reopen_for_that_slash(self):
        b = self.b
        self.make_note("Escape")
        b.type("/he")
        b.wait(f"!!{MENU}", 5)
        b.key("Escape")
        b.wait(f"!{MENU}", 5)
        self.assertEqual(b.eval("document.querySelector('.nbody').textContent"), "/he")
        b.type("a")
        b.pump(0.2)
        self.assertEqual(b.eval(f"!!{MENU}"), False)
        self.assertEqual(b.eval("document.querySelector('.nbody').textContent"), "/hea")
        b.key("Enter")                                    # an ordinary Enter, not an insert
        b.type("again /")
        b.wait(f"!!{MENU}", 5)                            # a new slash opens it again

    def test_it_closes_when_the_caret_moves_away_or_focus_leaves(self):
        b = self.b
        self.make_note("Away", "Some text here")
        b.key("Enter")
        b.type("/")
        b.wait(f"!!{MENU}", 5)
        b.key("ArrowUp")                                  # the menu takes the arrows while open
        b.key("Escape")
        b.type("x")
        b.eval("document.querySelector('.nbody').cxed.editor.commands.setTextSelection(2)")
        b.pump(0.2)
        self.assertEqual(b.eval(f"!!{MENU}"), False)
        b.eval("document.querySelector('.nbody').cxed.focus('end')")
        b.key("Backspace"); b.key("Backspace")
        b.type("/")
        b.wait(f"!!{MENU}", 5)
        b.eval("document.activeElement.blur()")
        b.wait(f"!{MENU}", 5)

    # ---- where it must not open -----------------------------------------------------------------------------------------

    def test_not_inside_a_word_an_address_code_a_link_or_a_heading(self):
        b = self.b
        self.make_note("Not here")
        for text in ("and/or", "https://example.com/a", "1/2"):
            b.type(text)
            b.pump(0.2)
            self.assertEqual(b.eval(f"!!{MENU}"), False, text)
            b.key("Enter")
        b.type("go /")                                    # after a space it does
        b.wait(f"!!{MENU}", 5)
        b.key("Escape")
        b.key("Enter")
        b.click(".nbar [data-nt=code]")                   # inline code
        b.type("/")
        b.pump(0.2)
        self.assertEqual(b.eval(f"!!{MENU}"), False)
        b.click(".nbar [data-nt=code]")
        b.key("Enter")
        b.click(".nbar [data-nt=h2]")                     # a heading
        b.type("/")
        b.pump(0.2)
        self.assertEqual(b.eval(f"!!{MENU}"), False)
        if b.eval("!!document.querySelector('.nbody').cxed.editor.schema.nodes.codeBlock"):
            b.key("Enter"); b.key("Enter")
            b.eval("document.querySelector('.nbody').cxed.editor.chain().focus().setCodeBlock().run()")
            b.type("/")
            b.pump(0.2)
            self.assertEqual(b.eval(f"!!{MENU}"), False, "a code block")

    def test_a_composition_does_not_open_it_and_the_committed_text_does(self):
        b = self.b
        self.make_note("IME")
        b.call("Input.imeSetComposition", text="/", selectionStart=1, selectionEnd=1)
        b.pump(0.2)
        self.assertEqual(b.eval(f"!!{MENU}"), False)
        b.call("Input.insertText", text="/")
        b.pump(0.3)
        self.assertEqual(b.eval(f"!!{MENU}"), True, "a committed slash opens it")

    # ---- headings: the right stored level per host -----------------------------------------------------------------------

    def test_notes_headings_one_to_three_are_stored_as_one_to_three_hashes(self):
        b = self.b
        self.make_note("Hashes")
        for n in (1, 2, 3):
            b.type("/")
            b.wait(f"!!{MENU}", 5)
            b.click(f".slashmenu [data-slash=h{n}]")
            b.wait(f"!{MENU}", 5)
            b.type(f"Head {n}")
            b.key("Enter")
        md = b.eval("document.querySelector('.nbody').cxed.value()")
        for n in (1, 2, 3):
            self.assertRegex(md, rf"(?m)^{'#' * n} Head {n}$")
        self.assertNotIn("/", md)

    def test_current_state_headings_one_to_three_are_stored_as_three_to_five_hashes(self):
        b = self.b
        self.open_current()
        for n in (1, 2, 3):
            b.key("Enter"); b.key("Enter")
            b.type("/")
            b.wait(f"!!{MENU}", 5)
            b.click(f".slashmenu [data-slash=h{n}]")
            b.wait(f"!{MENU}", 5)
            b.type(f"Slash {n}")
        value = b.eval("edValue(curEd)")
        for n in (1, 2, 3):
            self.assertRegex(value, rf"(?m)^{'#' * (n + 2)} Slash {n}$")
        self.assertFalse(re.search(r"(?m)^#{1,2} ", value), "never a line that would end the section")
        self.assertNotIn("/", value.replace("</", ""))

    def test_current_state_menu_headings_leave_stray_hash_lines_byte_identical(self):
        """With the reversible mapping (headsIn/headsOut): a stored `# ` or `######` line is plain text, and the menu's headings go through
        the editor's commands so they are written ###, #### and ##### beside it; nothing stray is turned into a heading or lost."""
        b = self.b
        stray = "# Stray one\n\n###### Six hashes\n\n####### Seven"      # a `## ` line would end the section in the memory file itself
        self.open_current(f"{STATE}\n\n{stray}")
        before = b.eval("edValue(curEd)")
        for line in ("# Stray one", "###### Six hashes", "####### Seven"):
            self.assertIn(line, before.split("\n"), "untouched, an odd line is saved as it was")
        b.key("Enter"); b.key("Enter")
        for n in (1, 2, 3):
            b.type("/")
            b.wait(f"!!{MENU}", 5)
            b.click(f".slashmenu [data-slash=h{n}]")
            b.wait(f"!{MENU}", 5)
            b.type(f"Menu {n}")
            b.key("Enter")
        value = b.eval("edValue(curEd)")
        lines = value.split("\n")
        for line in ("# Stray one", "###### Six hashes", "####### Seven"):
            self.assertIn(line, lines, f"{line!r} stays byte for byte after the menu is used elsewhere")
        for n in (1, 2, 3):
            self.assertIn(f"{'#' * (n + 2)} Menu {n}", lines)
        self.assertEqual(b.eval("edValue(curEd).includes('\\u200b')"), False, "the escape never leaks into the saved text")
        self.assertEqual(b.eval("document.querySelectorAll('#curEd h1, #curEd h2, #curEd h3').length"), 5, "two from the state text, three from the menu")

    def test_notes_menu_headings_leave_a_stray_hash_line_alone_and_store_one_to_three(self):
        b = self.b
        self.make_note("Strays", "Intro paragraph")
        b.key("Enter")
        for n in (1, 2, 3):
            b.type("/")
            b.wait(f"!!{MENU}", 5)
            b.click(f".slashmenu [data-slash=h{n}]")
            b.wait(f"!{MENU}", 5)
            b.type(f"Note {n}")
            b.key("Enter")
        lines = b.eval("document.querySelector('.nbody').cxed.value()").split("\n")
        for n in (1, 2, 3):
            self.assertIn(f"{'#' * n} Note {n}", lines)

    def test_keyboard_markdown_shortcuts_still_make_headings(self):
        b = self.b
        self.make_note("Shortcuts")
        b.type("## Twice")
        self.assertRegex(b.eval("document.querySelector('.nbody').cxed.value()"), r"(?m)^## Twice$")

    # ---- review fixes (editor-122b3) ------------------------------------------------------------------------------------

    def test_m1_command_enter_waits_under_an_open_menu_in_current_state_and_saves_once_it_is_closed(self):
        b = self.b
        self.open_current()
        b.key("Enter")
        b.type("/he")
        b.wait(f"!!{MENU}", 5)
        b.key("Enter", META)                                       # held back: the document-level save handler stands back
        b.pump(0.6)
        self.assertTrue(b.eval("!!shared.CURED"), "still editing")
        self.assertTrue(b.eval(f"!!{MENU}"), "the menu is still open")
        self.assertNotIn("/he", self.memory().read_text(encoding="utf-8"), "nothing was saved")
        b.key("Escape")
        b.wait(f"!{MENU}", 5)
        b.key("Enter", META)                                       # with the menu closed it saves
        b.wait("!shared.CURED", 10)
        self.assertIn("/he", self.memory().read_text(encoding="utf-8"))

    def block(self, row, md_before, setup, typed, lead=""):
        """Open a Notes editor on md_before, caret at the end, run `setup` keys, choose `row`, type `typed`; the stored Markdown."""
        b = self.b
        self.make_note("Blocks", focus=False)           # focus is taken here, not waited for in make_note (under load focus can fall back to the New button)
        b.eval(f"document.querySelector('.nbody').cxed.editor.commands.setContent({md_before!r}, {{contentType:'markdown'}})")
        b.eval("""(()=>{ const e=document.querySelector('.nbody').cxed.editor; let at=1; e.state.doc.descendants((n,pos)=>{ if(n.isTextblock&&n.content.size) at=pos+n.nodeSize-1; }); e.commands.focus(); e.commands.setTextSelection(at); })()""")
        b.wait("document.activeElement===document.querySelector('.nbody')", 5)
        for k in setup:
            b.key(k)
        b.type(f"{lead}/{row}")
        b.wait(f"!!{MENU}", 5)
        b.key("Enter")
        b.wait(f"!{MENU}", 5)
        b.type(typed)
        return b.eval("document.querySelector('.nbody').cxed.value()").strip()

    def test_m2_a_list_row_inside_that_list_only_removes_the_query(self):
        md = self.block("bull", "- one\n- two", ["Enter"], "three")
        self.assertEqual(md, "- one\n- two\n- three", "one list, not split")
        md = self.block("bull", "- one\n- two", [], "x", lead=" ")          # in an item that has text: a toggle would lift "two" out of the list
        self.assertEqual(md, "- one\n- two x")

    def test_m2_a_quote_row_inside_a_quote_only_removes_the_query(self):
        md = self.block("quo", "> one", ["Enter"], "two")
        self.assertNotIn("\n\n\n", md)
        self.assertEqual(md.count("> one"), 1)
        self.assertRegex(md, r"(?s)^> one\n>\s*\n> two$", "still one quote")

    def test_m2_a_checklist_row_inside_a_checklist_only_removes_the_query(self):
        md = self.block("tick", "- [ ] one", ["Enter"], "two")
        self.assertEqual(md, "- [ ] one\n- [ ] two")
        md = self.block("tick", "- [ ] one\n- [ ] two", [], "x", lead=" ")
        self.assertEqual(md, "- [ ] one\n- [ ] two x")

    def test_m2_a_numbered_row_inside_a_bulleted_list_converts_the_list(self):
        md = self.block("num", "- one", ["Enter"], "two")
        self.assertRegex(md, r"(?m)^1\. ")
        self.assertNotRegex(md, r"(?m)^- ")
        self.assertIn("two", md)

    def test_m2_current_state_a_bulleted_row_in_a_nested_item_keeps_the_nesting(self):
        b = self.b
        self.open_current("- one\n  - two")
        before = b.eval("edValue(curEd)")
        self.assertEqual(before, "- one\n  - two")
        b.eval("""(()=>{ const e=curEd.cxed.editor; let at=1; e.state.doc.descendants((n,pos)=>{ if(n.isTextblock&&n.content.size) at=pos+n.nodeSize-1; }); e.commands.focus(); e.commands.setTextSelection(at); })()""")
        b.key("Enter")
        b.type("/bull")
        b.wait(f"!!{MENU}", 5)
        b.key("Enter")
        b.wait(f"!{MENU}", 5)
        b.type("three")
        self.assertEqual(b.eval("edValue(curEd)"), "- one\n  - two\n  - three", "unchanged apart from the item typed")

    def test_l3_short_names_and_aliases_find_the_row_and_one_space_is_allowed(self):
        b = self.b
        self.make_note("Aliases")
        self.open_menu()
        want = {"h1": ["h1"], "h2": ["h2"], "h3": ["h3"], "ul": ["ul"], "bullet": ["ul"], "todo": ["task"], "check": ["task"], "bq": ["quote"],
                "code": ["codeblock"], "table": ["table"], "img": ["image"], "heading 2": ["h2"], "bulleted list": ["ul"], "numbered list": ["ol"]}
        for q, rows in want.items():
            b.type(q)
            b.pump(0.1)
            self.assertEqual(self.rows()[:len(rows)], rows, q)
            if " " in q or q in ("h1", "h2", "h3"):
                self.assertEqual(self.rows(), rows, q)
            for _ in q:
                b.key("Backspace")
        b.type("ol")
        b.pump(0.1)
        self.assertEqual(self.rows()[0], "ol", "an alias ranks above a mere mention (Table, Stakeholder)")
        for _ in "ol":
            b.key("Backspace")
        b.type("num")
        self.assertEqual(self.rows()[0], "ol")
        for _ in "num":
            b.key("Backspace")
        b.type("h")
        r = self.rows()
        self.assertEqual(r[:3], ["h1", "h2", "h3"], "the headings first")
        self.assertGreater(len(r), 3, "then the other rows with an h in them (the mockup's rule)")
        for _ in "h":
            b.key("Backspace")
        b.type("heading 2")
        b.key("Enter")
        b.wait(f"!{MENU}", 5)
        b.type("Two")
        self.assertRegex(b.eval("document.querySelector('.nbody').cxed.value()"), r"(?m)^## Two$")

    def test_l3_a_phrase_that_names_no_row_closes_the_menu_and_stays_text(self):
        b = self.b
        self.make_note("Phrase")
        self.open_menu()
        b.type("zzz yyy")
        b.pump(0.2)
        self.assertEqual(b.eval(f"!!{MENU}"), False)
        self.assertIn("/zzz yyy", b.eval("document.querySelector('.nbody').textContent"))

    def test_l3_current_state_short_names_work_too(self):
        b = self.b
        self.open_current()
        b.key("Enter")
        b.type("/h2")
        b.wait(f"!!{MENU}", 5)
        self.assertEqual(self.rows(), ["h2"])
        b.key("Enter")
        b.type("Short")
        self.assertIn("#### Short", b.eval("edValue(curEd)").split("\n"))

    def test_l5_current_state_headings_inside_a_quote_are_shifted_and_stray_ones_stay_byte_identical(self):
        b = self.b
        self.open_current(f"{STATE}\n\n> ### Quoted\n\n> # Stray in a quote\n\n> > ##### Deep")
        value = b.eval("edValue(curEd)")
        lines = value.split("\n")
        for line in ("> ### Quoted", "> # Stray in a quote", "> > ##### Deep"):
            self.assertIn(line, lines, f"{line!r} saved as it was")
        self.assertEqual(b.eval("curEd.querySelectorAll('blockquote h1').length"), 1, "the shifted one is a heading in the editor")
        self.assertEqual(b.eval("curEd.querySelectorAll('blockquote blockquote h3').length"), 1)
        self.assertEqual(b.eval("edValue(curEd).includes('\\u200b')"), False)
        b.key("Enter"); b.key("Enter")
        b.type("/quo")
        b.key("Enter")
        b.type("/h2")
        b.wait(f"!!{MENU}", 5)
        b.key("Enter")
        b.type("In the quote")
        lines = b.eval("edValue(curEd)").split("\n")
        self.assertIn("> #### In the quote", lines, "stored shifted, never a line that would end the section")
        self.assertIn("> # Stray in a quote", lines)

    def test_l6_the_menu_follows_the_caret_after_a_resize_in_current_state(self):
        b = self.b
        self.open_current()
        b.key("Enter")
        self.open_menu("#curEd")
        for width in (900, 1400):
            b.resize(width, 1000)
            b.pump(0.8)
            g = self.geometry("#curEd")
            self.assertLessEqual(abs(g["menu"]["top"] - (g["caret"]["bottom"] + 4)), 4, f"{width}: {g}")
            self.assertLessEqual(abs(g["menu"]["left"] - g["caret"]["left"]), 14, f"{width}: {g}")   # anchored at the slash, a character before the caret

    def test_l6_the_menu_follows_the_caret_after_a_resize_in_notes(self):
        b = self.b
        self.make_note("Resize", LONG)
        self.mid(20)
        self.open_menu()
        b.resize(900, 1000)
        b.pump(0.8)
        g = self.geometry()
        self.assertLessEqual(abs(g["menu"]["top"] - (g["caret"]["bottom"] + 4)), 4, g)

    def test_l7_no_match_is_announced_and_the_aria_state_is_reset_on_close(self):
        b = self.b
        self.make_note("Aria")
        self.assertIsNone(b.eval("document.querySelector('.nbody').getAttribute('aria-expanded')"))
        self.open_menu()
        attrs = "(()=>{ const d=document.querySelector('.nbody'); return { exp:d.getAttribute('aria-expanded'), pop:d.getAttribute('aria-haspopup'), act:d.getAttribute('aria-activedescendant'), has:!!document.getElementById(d.getAttribute('aria-activedescendant')||'-') }; })()"
        got = b.eval(attrs)
        self.assertEqual((got["exp"], got["pop"], got["has"]), ("true", "listbox", True))
        b.type("zzz")
        b.pump(0.1)
        st = b.eval("(()=>{ const s=document.querySelector('.slashroot [role=status]'); return s&&{t:s.textContent,live:s.getAttribute('aria-live')}; })()")
        self.assertEqual(st, {"t": "No match", "live": "polite"})
        self.assertIsNone(b.eval("document.querySelector('.nbody').getAttribute('aria-activedescendant')"))
        b.key("Escape")
        b.wait(f"!{MENU}", 5)
        got = b.eval(attrs)
        self.assertEqual((got["exp"], got["pop"], got["act"]), ("false", None, None))

    # ---- the Notes tab as it was ----------------------------------------------------------------------------------------

    def test_the_old_slash_behaviours_still_work_on_an_empty_line(self):
        b = self.b
        self.make_note("Regression")
        b.type("Text first")
        b.key("Enter")
        b.type("/")
        b.wait(f"!!{MENU}", 5)
        b.type("check")
        b.key("Enter")
        b.type("item")
        md = b.eval("document.querySelector('.nbody').cxed.value()")
        self.assertIn("Text first", md)
        self.assertIn("- [ ] item", md)
        self.assertNotIn("/check", md)

    # ---- review fixes (editor-122b4) ------------------------------------------------------------------------------------

    def test_n1_prose_with_a_slash_and_spaces_stays_exactly_as_typed_when_enter_is_pressed(self):
        b = self.b
        for line in ("A / B", "1 / 2", "yes / no", "either / or"):
            self.make_note("Prose")
            b.type(line)
            b.pump(0.2)
            self.assertEqual(b.eval(f"!!{MENU}"), False, f"{line!r}: no menu open")
            b.key("Enter")
            b.pump(0.2)
            self.assertEqual(b.eval("document.querySelector('.nbody').cxed.value()").strip(), line, f"{line!r} is untouched by Enter")
            self.assertEqual(b.eval(f"!!{MENU}"), False)

    def test_n1_prose_with_a_slash_in_current_state_stays_as_typed(self):
        b = self.b
        self.open_current()
        b.key("Enter")
        b.type("yes / no")
        b.pump(0.2)
        self.assertEqual(b.eval(f"!!{MENU}"), False)
        b.key("Enter")
        b.pump(0.2)
        self.assertIn("yes / no", b.eval("edValue(curEd)").split("\n"))

    def test_n1_a_bare_slash_after_a_space_or_at_a_line_start_opens_all_rows_but_slash_space_does_not(self):
        b = self.b
        self.make_note("Bare")
        b.type("/")
        b.wait(f"!!{MENU}", 5)
        every = self.rows()
        self.assertEqual(every[:len(NOTES_ROWS)], NOTES_ROWS, "all rows at a line start")
        b.key("Escape")
        b.key("Backspace")
        b.type("word /")
        b.wait(f"!!{MENU}", 5)
        self.assertEqual(self.rows(), every, "all rows after a space")
        b.type(" ")
        b.pump(0.2)
        self.assertEqual(b.eval(f"!!{MENU}"), False, "slash then a space closes it")
        b.key("Enter")
        b.pump(0.2)
        self.assertEqual(b.eval("document.querySelector('.nbody').cxed.value()").strip(), "word /")
        b.type("/")
        b.wait(f"!!{MENU}", 5)
        self.assertEqual(self.rows(), every, "all rows at a line start again")

    def test_n1_heading_two_still_writes_a_heading_and_a_trailing_space_after_a_complete_word_closes_the_menu(self):
        b = self.b
        self.make_note("Trailing")
        b.type("/heading 2")
        b.wait(f"!!{MENU}", 5)
        b.key("Enter")
        b.wait(f"!{MENU}", 5)
        b.type("Two")
        self.assertRegex(b.eval("document.querySelector('.nbody').cxed.value()"), r"(?m)^## Two$")
        b.key("Enter")
        b.key("Enter")
        b.type("/h1 ")
        b.pump(0.3)
        self.assertEqual(b.eval(f"!!{MENU}"), False, "'/h1 ' closes the menu")
        b.key("Enter")
        b.pump(0.2)
        md = b.eval("document.querySelector('.nbody').cxed.value()")
        self.assertNotRegex(md, r"(?m)^# ", "Enter after '/h1 ' does not make a heading")
        self.assertIn("/h1", md)

    def test_n1_a_trailing_space_after_the_first_word_of_a_longer_row_name_keeps_the_menu(self):
        b = self.b
        self.make_note("Words")
        for q, row in (("heading ", "h1"), ("bulleted ", "ul"), ("numbered ", "ol")):
            b.type("/" + q)
            b.pump(0.2)
            self.assertEqual(b.eval(f"!!{MENU}"), True, q)
            self.assertIn(row, self.rows(), q)
            for _ in range(len(q) + 1):
                b.key("Backspace")

    def test_n2_a_list_row_in_a_nested_list_changes_that_nested_lists_type(self):
        md = self.block("bull", "- one\n  1. two", ["Enter"], "three")
        self.assertNotRegex(md, r"(?m)^\s+1\. ", "the nested numbered list is bulleted now")
        self.assertRegex(md, r"(?m)^\s+- three$")
        md = self.block("num", "1. one\n   - two", ["Enter"], "three")
        self.assertNotRegex(md, r"(?m)^\s+- ", "the nested bulleted list is numbered now")
        self.assertRegex(md, r"(?m)^\s+\d+\. three$")
        md = self.block("tick", "- [ ] one\n  - two", ["Enter"], "three")
        self.assertRegex(md, r"(?m)^\s+- \[ \] three$", "the nested list became a checklist")

    def test_n2_the_original_split_cases_stay_one_list_one_checklist_and_one_quote(self):
        md = self.block("bull", "- one\n  - two", ["Enter"], "three")
        self.assertEqual(md, "- one\n  - two\n  - three")
        md = self.block("tick", "- [ ] one\n  - [ ] two", ["Enter"], "three")
        self.assertEqual(md, "- [ ] one\n  - [ ] two\n  - [ ] three")
        md = self.block("quo", "> one", [], "x", lead=" ")
        self.assertEqual(md, "> one x")
        md = self.block("quo", "> one\n>\n> two\n>\n> three", ["ArrowUp", "End"], "x", lead=" ")
        self.assertEqual(md.count("> one"), 1)
        self.assertNotIn("\n\n\n", md)
        self.assertRegex(md, r"(?s)^> one\n>\s*\n> two x\n>\s*\n> three$", "no split: still one quote")

    def test_n3_quoted_headings_with_extra_indent_keep_their_level(self):
        b = self.b
        self.open_current(f"{STATE}\n\n>  ### Two spaces\n\n>\t### A tab\n\n>   ### Three spaces\n\n> >  ### Deep")
        self.assertEqual(b.eval("curEd.querySelectorAll('blockquote h1').length"), 4, "all four are Heading 1 in the editor")
        self.assertEqual(b.eval("curEd.querySelectorAll('blockquote h3').length"), 0)
        for want in ("Two spaces", "A tab", "Three spaces", "Deep"):
            line = next(l for l in b.eval("edValue(curEd)").split("\n") if l.endswith(want))
            self.assertEqual(line.lstrip(">\t "), f"### {want}", f"{want}: still level three when stored (was {line!r})")
        self.assertEqual(b.eval("edValue(curEd).includes('\\u200b')"), False)

    def test_n3_other_lines_are_not_changed_by_the_wider_quote_pattern(self):
        b = self.b
        self.open_current()
        b.eval("curEd.cxed.setValue(%r)" % "> \t### Space tab is code\n\n>     ### Five spaces is code\n\n> ### Plain")     # set directly: the page's own reading of the stored text would tidy the spaces
        self.assertEqual(b.eval("curEd.querySelectorAll('blockquote h1').length"), 1, "only the plain one is a heading")
        self.assertEqual(b.eval("curEd.querySelectorAll('blockquote pre').length"), 2)
        self.assertIn("### Space tab is code", b.eval("curEd.querySelectorAll('blockquote pre')[0].textContent"), "code shows what was stored")
        lines = b.eval("edValue(curEd)").split("\n")
        self.assertIn("> ### Plain", lines)
        self.assertIn("> \t### Space tab is code", lines)

    def test_n5_a_query_shows_a_flat_ranked_list_without_repeated_group_headers_and_the_groups_come_back(self):
        b = self.b
        self.make_note("Groups")
        b.type("/")
        b.wait(f"!!{MENU}", 5)
        heads = "[...document.querySelectorAll('.slashmenu .g')].map(g=>g.textContent)"
        self.assertEqual(b.eval(heads), ["Text", "Lists", "Blocks", "Link", "Templates"], "no query: the groups")
        self.assertEqual(b.eval("document.querySelectorAll('.slashmenu [role=group]').length"), 5)
        b.type("b")
        b.pump(0.2)
        heads_now = b.eval(heads)
        self.assertEqual(len(heads_now), len(set(heads_now)), f"no header repeats: {heads_now}")
        self.assertGreater(len(self.rows()), 2)
        self.assertEqual(b.eval("document.querySelectorAll('.slashmenu > [role=option]').length"), len(self.rows()), "the options are the listbox's own children, so the roles stay valid")
        self.assertEqual(b.eval("document.querySelectorAll('.slashmenu [role=group]').length"), 0)
        b.key("Backspace")
        b.pump(0.2)
        self.assertEqual(b.eval(heads), ["Text", "Lists", "Blocks", "Link", "Templates"], "the groups return with an empty query")

    def test_n6_a_multi_word_query_matches_when_each_word_starts_a_word_of_the_name(self):
        b = self.b
        self.make_note("Words")
        b.type("/")
        b.wait(f"!!{MENU}", 5)
        for q, first in (("head 2", "h2"), ("bull l", "ul"), ("num l", "ol"), ("head", "h1")):
            b.type(q)
            b.pump(0.2)
            self.assertTrue(self.rows(), f"{q}: rows (text now {b.eval('document.querySelector(\'.nbody\').cxed.value()')!r})")
            self.assertEqual(self.rows()[0], first, q)
            if " " in q:
                self.assertEqual(self.rows(), [first], f"{q}: only that row")
            for _ in q:
                b.key("Backspace")
        b.type("head 2")
        b.key("Enter")
        b.wait(f"!{MENU}", 5)
        b.type("Two")
        self.assertRegex(b.eval("document.querySelector('.nbody').cxed.value()"), r"(?m)^## Two$")

    # ---- review fixes (editor-122b5): H1 / M1 ---------------------------------------------------------------------------

    STUCK = ("RAG: Amber /Red", "yes /no", "ratio 1 /2", "and /or", "x, /x", "A /", "in/out /in", "w /o", "price /kg", "Q3 /Q4", "see /docs")

    def test_h1_a_word_stuck_to_a_slash_stays_exactly_as_typed_when_enter_is_pressed_in_notes(self):
        b = self.b
        for line in self.STUCK:
            self.make_note("Stuck")
            b.type(line)
            b.pump(0.2)
            b.key("Enter")
            b.pump(0.2)
            md = b.eval("document.querySelector('.nbody').cxed.value()")
            self.assertEqual(md.strip(), line, f"{line!r} keeps its text")
            self.assertEqual(b.eval(f"!!{MENU}"), False, f"{line!r}: the menu is closed")
            self.assertEqual(b.eval("document.querySelector('.nbody').cxed.editor.state.doc.childCount"), 2, f"{line!r}: Enter made a new line")

    def test_h1_a_word_stuck_to_a_slash_stays_as_typed_in_current_state(self):
        b = self.b
        self.open_current()
        for line in self.STUCK:
            b.key("Enter")
            b.type(line)
            b.pump(0.2)
            b.key("Enter")
            b.pump(0.2)
            self.assertEqual(b.eval(f"!!{MENU}"), False, f"{line!r}: the menu is closed")
            self.assertIn(line, b.eval("edValue(curEd)").split("\n"), f"{line!r} keeps its text")

    def test_h1_a_saved_note_with_a_stuck_slash_opens_no_menu_on_a_caret_move_and_enter_loses_nothing(self):
        b = self.b
        self.make_note("Saved", "RAG: Amber /Red", focus=False)
        b.eval("document.querySelector('.nbody').cxed.focus('end')")
        b.wait("document.activeElement===document.querySelector('.nbody')", 5)
        b.pump(0.3)
        self.assertEqual(b.eval(f"!!{MENU}"), False, "focusing at the end opens nothing")
        b.eval("document.querySelector('.nbody').cxed.editor.commands.setTextSelection(3)")
        b.eval("document.querySelector('.nbody').cxed.editor.commands.setTextSelection(15)")
        b.pump(0.3)
        self.assertEqual(b.eval(f"!!{MENU}"), False, "moving the caret opens nothing")
        b.key("ArrowRight"); b.key("End")
        b.key("Enter")
        b.pump(0.2)
        self.assertEqual(b.eval("document.querySelector('.nbody').cxed.value()").strip(), "RAG: Amber /Red")
        self.assertEqual(b.eval(f"!!{MENU}"), False)

    def test_h1_a_click_after_the_text_of_a_saved_note_then_enter_loses_nothing(self):
        b = self.b
        self.make_note("Clicked", "Status: Amber /Red", focus=False)
        b.eval("(()=>{ const e=document.querySelector('.nbody').cxed.editor, v=e.view, c=v.coordsAtPos(e.state.doc.content.size-1); window.__pt=[c.right+40, (c.top+c.bottom)/2]; })()")
        x, y = b.eval("window.__pt")
        for kind in ("mouseMoved", "mousePressed", "mouseReleased"):
            b.call("Input.dispatchMouseEvent", type=kind, x=x, y=y, button="left", clickCount=1)
        b.pump(0.3)
        self.assertEqual(b.eval(f"!!{MENU}"), False, "a click opens nothing")
        b.key("Enter")
        b.pump(0.2)
        self.assertEqual(b.eval("document.querySelector('.nbody').cxed.value()").strip(), "Status: Amber /Red")

    def test_m1_a_paste_with_a_slash_does_not_open_the_menu_in_notes_or_current_state(self):
        b = self.b
        paste = """(()=>{ const el=document.querySelector(%r), dt=new DataTransfer(); dt.setData('text/plain', 'see /h'); el.dispatchEvent(new ClipboardEvent('paste',{clipboardData:dt,bubbles:true,cancelable:true})); })()"""
        self.make_note("Paste")
        b.eval(paste % ".nbody")
        b.pump(0.3)
        self.assertIn("see /h", b.eval("document.querySelector('.nbody').cxed.value()"), "the paste landed")
        self.assertEqual(b.eval(f"!!{MENU}"), False, "Notes: a paste opens nothing")
        b.key("Enter")
        b.pump(0.2)
        self.assertEqual(b.eval("document.querySelector('.nbody').cxed.value()").strip(), "see /h")
        self.open_current()
        b.eval(paste % "#curEd")
        b.pump(0.3)
        self.assertIn("see /h", b.eval("edValue(curEd)"), "the paste landed")
        self.assertEqual(b.eval(f"!!{MENU}"), False, "Current state: a paste opens nothing")

    def test_h1_a_bare_slash_with_no_arrow_key_closes_on_enter_and_acts_as_a_new_line_but_an_arrow_then_enter_picks(self):
        b = self.b
        self.make_note("Bare enter")
        b.type("/")
        b.wait(f"!!{MENU}", 5)
        b.key("Enter")
        b.pump(0.2)
        self.assertEqual(b.eval(f"!!{MENU}"), False)
        self.assertEqual(b.eval("document.querySelector('.nbody').cxed.value()").strip(), "/")
        self.assertEqual(b.eval("document.querySelector('.nbody').cxed.editor.state.doc.childCount"), 2)
        self.make_note("Bare arrow")
        b.type("/")
        b.wait(f"!!{MENU}", 5)
        b.key("ArrowDown")
        b.key("Enter")
        b.wait(f"!{MENU}", 5)
        b.type("Big")
        self.assertRegex(b.eval("document.querySelector('.nbody').cxed.value()"), r"(?m)^# Big$", "the second row (Heading 1) after one arrow")

    def test_h1_a_weak_match_picks_only_after_an_arrow_key_and_a_sure_match_picks_at_once(self):
        b = self.b
        self.make_note("Weak")
        b.type("A /Red")
        b.wait(f"!!{MENU}", 5)
        self.assertEqual(self.rows()[0], "ol", "numbered matches 'red' in its name")
        b.key("ArrowDown"); b.key("ArrowUp")
        b.key("Enter")
        b.wait(f"!{MENU}", 5)
        self.assertRegex(b.eval("document.querySelector('.nbody').cxed.value()"), r"1\. ", "an arrow key makes the pick deliberate")
        self.make_note("Sure")
        b.type("/h1")
        b.wait(f"!!{MENU}", 5)
        b.key("Enter")
        b.wait(f"!{MENU}", 5)
        b.type("Top")
        self.assertRegex(b.eval("document.querySelector('.nbody').cxed.value()"), r"(?m)^# Top$")

    def test_a11y_the_live_region_goes_in_empty_and_then_says_how_many_options(self):
        b = self.b
        self.make_note("Live")
        b.eval("""(()=>{ window.__sr=[]; new MutationObserver(ms=>{ for(const m of ms) for(const n of m.addedNodes){ const e=n.nodeType===1&&(n.matches('.slashsr')?n:n.querySelector('.slashsr')); if(e) window.__sr.push(e.textContent); } }).observe(document.body,{childList:true,subtree:true}); })()""")
        b.type("/")
        b.wait(f"!!{MENU}", 5)
        b.wait("/^\\d+ options$/.test(document.querySelector('.slashsr').textContent)", 3)
        self.assertEqual(b.eval("window.__sr[0]"), "", "inserted empty")
        b.type("zzz")
        b.wait("document.querySelector('.slashsr').textContent==='No match'", 3)
        b.key("Escape")

    # ---- dark and forced colours -----------------------------------------------------------------------------------------

    def test_dark_and_forced_colours(self):
        b = self.b
        self.make_note("Colours")
        self.open_menu()
        b.eval("document.documentElement.dataset.theme='dark'")
        probe = "(()=>{ const m=document.querySelector('.slashmenu'), on=m.querySelector('.r.on'), off=m.querySelector('.r:not(.on)'); const c=e=>getComputedStyle(e); return { bg:c(m).backgroundColor, on:c(on).backgroundColor, off:c(off).backgroundColor, border:c(m).borderTopColor }; })()"
        got = b.eval(probe)
        self.assertNotEqual(got["on"], got["off"])
        self.assertNotEqual(got["bg"], "rgba(0, 0, 0, 0)")
        b.call("Emulation.setEmulatedMedia", features=[{"name": "forced-colors", "value": "active"}])
        b.pump(0.3)
        got = b.eval(probe)
        self.assertNotEqual(got["on"], got["off"], "the chosen row shows in forced colours")


if __name__ == "__main__":
    unittest.main()
