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

MENU = "document.querySelector('.slashmenu, #ntpick')"
NOTES_ROWS = ["text", "h1", "h2", "h3", "ul", "ol", "task", "quote", "codeblock", "table", "image", "item", "person", "note"]
CURRENT_ROWS = ["text", "h1", "h2", "h3", "ul", "ol", "quote", "image", "item"]
STATE = "### Top\n\nFirst paragraph.\n\n#### Middle\n\nSecond paragraph."
LONG = "\n\n".join(f"Paragraph {i} of a long note so that the editor scrolls." for i in range(1, 40))


class Slash(LiveBrowserCase):
    width, height = 1400, 1000

    def memory(self):
        return next((self.v.root / "projects").glob("ABC */CLAUDE.md"))

    def make_note(self, title="Slash test", body=None):
        b = self.b
        b.eval("go('notes','ABC')")
        b.wait("!!document.getElementById('notesNew')")
        b.click("#notesNew")
        b.wait("document.getElementById('newNoteDlg').open")
        b.eval(f"(()=>{{ const i=document.getElementById('nnTitle'); i.value={title!r}; i.dispatchEvent(new Event('input',{{bubbles:true}})); }})()")
        b.eval("document.querySelector('#newNoteDlg input[value=\"blank\"]').click()")
        b.click("#nnMake")
        b.wait("!!document.querySelector('.nbody.ProseMirror')", 15)
        if body:
            b.eval(f"document.querySelector('.nbody').cxed.editor.commands.setContent({body!r}, {{contentType:'markdown'}})")
        b.eval("document.querySelector('.nbody').cxed.focus('end')")
        b.wait("document.activeElement===document.querySelector('.nbody')", 5)

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
