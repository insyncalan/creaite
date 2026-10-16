"""#122 step C: work-item links in every rich editor (components/ItemPicker.jsx, core/itemLink.js), in a real browser against the
real live server.

Run: python3 dev/tests/test_item_links.py   (needs Google Chrome; skipped otherwise)

Done when:
- the `#` list shows 'ID · Designation: title' (the designation is the dashboard's own word for the kind) in Notes and in Current state,
  filtered by ID, designation or title, at the caret, with keys (arrows, Enter, Esc), and only the project's items;
- picking writes one link, `[ID · Designation: title](creaite:item/ID)`, drawn as a chip whose click opens the peek;
  an older link, whose words are only the ID, still resolves and opens the peek (its Markdown is not rewritten);
- Current state: the link is saved as that plain Markdown in the project's CLAUDE.md, the read view shows a link that opens the item,
  Word (docx_tools) shows the words only, and the text reloads and saves byte for byte;
- stray `#` lines and headings are unaffected; the plain profile has no list; the `/` menu's Work item row opens the list in both hosts.
"""
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
from live_browser import LiveBrowserCase  # noqa: E402

PICK = "document.querySelector('#ntpick')"
STATE = "### Top\n\nFirst paragraph.\n\n#### Middle\n\nSecond paragraph."
DESIGNATIONS = {"Action", "Risk", "Issue", "Assumption", "Dependency", "Decision"}


class ItemLinks(LiveBrowserCase):
    width, height = 1400, 1000

    def memory(self):
        return next((self.v.root / "projects").glob("ABC */CLAUDE.md"))

    def section(self):
        text = self.memory().read_text(encoding="utf-8")
        return re.search(r"^## Current state[^\n]*\n(.*?)(?=^## |\Z)", text, re.M | re.S).group(1).strip("\n")

    def make_note(self, title):
        b = self.b
        b.eval("go('notes','ABC')")
        b.wait("!!document.getElementById('notesNew')")
        b.click("#notesNew")
        b.wait("document.getElementById('newNoteDlg').open")
        b.eval(f"(()=>{{ const i=document.getElementById('nnTitle'); i.value={title!r}; i.dispatchEvent(new Event('input',{{bubbles:true}})); }})()")
        b.eval("document.querySelector('#newNoteDlg input[value=\"blank\"]').click()")
        b.click("#nnMake")
        b.wait("!!document.querySelector('.nbody.ProseMirror')", 15)
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

    def rows(self):
        return self.b.eval("[...document.querySelectorAll('#ntpick [role=option]')].map(o=>o.textContent.trim())")

    def an_item(self, kind="actions"):
        """An ABC item of a kind and the text its link carries."""
        return self.b.eval(f"""(()=>{{ const x={'A' if kind == 'actions' else 'R'}.find(a=>a.p==='ABC'); return {{id:x.id, t:x.t}}; }})()""")

    # ---- the list -----------------------------------------------------------------------------------------------------

    def check_rows(self, root):
        b = self.b
        b.type("see #")
        b.wait("!!" + PICK, 5)
        rows = self.rows()
        self.assertTrue(rows)
        for r in rows:
            m = re.match(r"^(ABC-[A-Z0-9-]+) · (\w+): (.+)$", r)
            self.assertTrue(m, r)
            self.assertIn(m.group(2), DESIGNATIONS, r)
        self.assertEqual(self.b.eval("[...document.querySelectorAll('#ntpick [role=option]')].some(o=>!o.dataset.itemOpt.startsWith('ABC-'))"), False)
        # filtered by designation and by title
        first = rows[0]
        word = re.match(r"^\S+ · (\w+): (.+)$", first)
        b.type(word.group(1)[:4].lower())
        b.pump(0.1)
        self.assertTrue(all(word.group(1)[:4].lower() in r.lower() for r in self.rows()), self.rows())
        # geometry: at the caret
        g = b.eval(f"""(()=>{{ const v=document.querySelector({root!r}).cxed.editor.view, c=v.coordsAtPos(v.state.selection.from), m={PICK}.getBoundingClientRect();
          return {{cb:c.bottom, ct:c.top, mt:m.top, mb:m.bottom, pos:getComputedStyle({PICK}).position, right:m.right, vw:innerWidth}}; }})()""")
        self.assertEqual(g["pos"], "fixed")
        self.assertTrue(abs(g["mt"] - (g["cb"] + 4)) <= 4 or abs(g["mb"] - (g["ct"] - 4)) <= 4, g)
        self.assertLessEqual(g["right"], g["vw"])

    def test_notes_list_rows_are_id_designation_title(self):
        self.make_note("Rows")
        self.check_rows(".nbody")

    def test_current_state_list_rows_and_only_this_projects_items(self):
        self.open_current()
        self.check_rows("#curEd")

    def test_keys_arrows_enter_escape(self):
        b = self.b
        self.open_current()
        b.type("x #")
        b.wait("!!" + PICK, 5)
        self.assertEqual(b.eval("document.querySelector('#ntpick [aria-selected=true]').id"), "ntpick-0")
        b.key("ArrowDown")
        self.assertEqual(b.eval("document.querySelector('#ntpick [aria-selected=true]').id"), "ntpick-1")
        self.assertEqual(b.eval("curEd.getAttribute('aria-activedescendant')"), "ntpick-1")
        b.key("ArrowUp")
        b.key("Escape")
        b.wait(f"!{PICK}", 5)
        self.assertEqual(b.eval("curEd.textContent.endsWith('x #')"), True)
        self.assertTrue(b.eval("!!shared.CURED"))                                  # Esc closed the list, not the editor
        b.type("1")
        b.pump(0.1)
        self.assertFalse(b.eval("!!" + PICK))                                      # a dismissed "#" stays closed while it is typed on

    def test_no_match_closes_the_list_and_leaves_text_alone(self):
        b = self.b
        self.open_current()
        b.type("see #zzzzqq")
        b.pump(0.15)
        self.assertFalse(b.eval("!!" + PICK))
        self.assertTrue(b.eval("curEd.textContent.endsWith('see #zzzzqq')"))

    # ---- inserting ----------------------------------------------------------------------------------------------------

    def test_notes_insert_makes_one_chip_that_opens_the_peek_and_old_links_still_resolve(self):
        b = self.b
        item = self.an_item()
        self.make_note("Chip")
        b.type("old [" + item["id"] + "](creaite:item/" + item["id"] + ") and new ")
        b.eval(f"""(()=>{{ const e=document.querySelector('.nbody').cxed.editor; e.commands.setContent('Old [{item["id"]}](creaite:item/{item["id"]}) here', {{contentType:'markdown'}}); e.commands.focus('end'); }})()""")
        b.type(" and #" + item["id"][-3:])
        b.wait("!!" + PICK, 5)
        b.key("Enter")
        b.wait("document.querySelectorAll('.nbody .nchip').length===2", 5)
        md = b.eval("document.querySelector('.nbody').cxed.value()")
        self.assertIn(f"[{item['id']}](creaite:item/{item['id']})", md)                       # the old link, as it was
        self.assertRegex(md, rf"\[{re.escape(item['id'])} · (\w+): [^\]]+\]\(creaite:item/{re.escape(item['id'])}\)")
        # the whole text is one chip, and a click opens the peek (old chip first, then the new one)
        for i in (0, 1):
            b.eval("closePanel&&closePanel(true)")
            b.click(f".nbody p a:nth-of-type({i + 1})")
            b.wait("!!document.querySelector('#panel.on')", 5)
            self.assertIn(item["id"], b.eval("document.getElementById('panel').textContent"))

    def test_slash_item_finds_the_row_by_its_aliases_and_the_one_space_query(self):
        b = self.b
        self.open_current()
        b.type(" /")
        b.wait("!!document.querySelector('.slashmenu')", 5)
        for q in ("item", "work", "workitem", "issue", "action", "risk", "decision", "work item"):
            b.type(q)
            b.pump(0.1)
            self.assertTrue(b.eval("[...document.querySelectorAll('.slashmenu [data-slash]')].some(o=>o.dataset.slash==='item')"), q)
            for _ in q:
                b.key("Backspace")
        b.type("item")
        b.key("Enter")
        b.wait("!!" + PICK, 5)
        self.assertEqual(b.eval("curEd.textContent.endsWith('#')"), True)

    def test_command_enter_waits_while_the_item_list_is_open_in_current_state(self):
        b = self.b
        self.open_current()
        b.type(" see #")
        b.wait("!!" + PICK, 5)
        b.key("Enter", modifiers=4 if b.is_mac() else 2)
        b.pump(0.2)
        self.assertTrue(b.eval("!!shared.CURED"), "no save while the list is open")
        self.assertTrue(b.eval("!!" + PICK))
        b.key("Escape")
        b.wait(f"!{PICK}", 5)
        self.assertTrue(b.eval("!!shared.CURED"))                                  # Esc closed the list, not the editor

    def chip_text(self, root):
        return self.b.eval(f"document.querySelector({root!r}+' .nchip').textContent")

    def alt_click_case(self, root, ready):
        b = self.b
        item = self.an_item()
        ready(item)
        chip = f"{root} .nchip"
        b.wait(f"!!document.querySelector({chip!r})", 5)
        words = b.eval(f"document.querySelector({chip!r}).textContent")
        # Alt-click: the caret goes inside the chip's text and the peek stays shut
        b.eval("closePanel&&closePanel(true)")
        b.click(chip, modifiers=1)
        b.pump(0.3)
        self.assertFalse(b.eval("!!document.querySelector('#panel.on')"), "Alt-click must not open the peek")
        inside = b.eval(f"""(()=>{{ const c=document.querySelector({chip!r}), s=getSelection(); return !!(s.rangeCount && s.isCollapsed && c.contains(s.anchorNode)); }})()""")
        self.assertTrue(inside, "Alt-click puts the caret inside the chip")
        b.type("Z")                                                                # and typing there edits the chip's own words
        self.assertIn("Z", b.eval(f"document.querySelector({chip!r}).textContent"))
        self.assertNotEqual(b.eval(f"document.querySelector({chip!r}).textContent"), words)
        b.key("Backspace")
        b.pump(0.8)                                                                # past the double-click time, so it is a second click, not a double
        # a plain click opens the peek
        b.click(chip)
        b.wait("!!document.querySelector('#panel.on')", 5)
        self.assertIn(item["id"], b.eval("document.getElementById('panel').textContent"))
        return item

    def test_alt_click_edits_inside_a_chip_and_a_plain_click_opens_it_in_current_state(self):
        b = self.b
        self.open_current("### Top\n\nNothing yet.")

        def ready(item):
            b.eval(f"""(()=>{{ curEd.cxed.editor.commands.setContent('See [{item["id"]} · Action: {item["t"]}](creaite:item/{item["id"]}) now', {{contentType:'markdown'}}); }})()""")
        self.alt_click_case("#curEd", ready)
        # the plain click is the peek beside the text: the editor and its unsaved text stay, no discard question
        self.assertTrue(b.eval("!!shared.CURED && !document.getElementById('discardBar').classList.contains('on')"))
        self.assertTrue(b.eval("document.querySelector('#curEd .nchip')!==null"))

    def test_alt_click_edits_inside_a_chip_and_a_plain_click_opens_it_in_notes(self):
        b = self.b
        self.make_note("Alt chip")

        def ready(item):
            b.eval(f"""(()=>{{ const e=document.querySelector('.nbody').cxed.editor; e.commands.setContent('See [{item["id"]} · Action: {item["t"]}](creaite:item/{item["id"]}) now', {{contentType:'markdown'}}); }})()""")
        self.alt_click_case(".nbody", ready)

    def test_slash_work_item_row_opens_the_list_in_both_hosts(self):
        b = self.b
        self.make_note("Slash note")
        b.type("/work")
        b.key("Enter")
        b.wait("!!" + PICK, 5)
        self.assertEqual(b.eval("document.querySelector('.nbody').textContent"), "#")
        b.key("Escape")
        self.open_current()
        b.type(" /work")
        b.wait("!!document.querySelector('.slashmenu')", 5)
        b.key("Enter")
        b.wait("!!" + PICK, 5)
        self.assertEqual(b.eval("curEd.textContent.endsWith('#')"), True)

    def test_current_state_toolbar_has_the_item_button(self):
        b = self.b
        self.open_current()
        b.click('#curBar [data-nt="item"]') if b.eval("!!document.querySelector('#curBar [data-nt=item]')") else self.fail("no item button")
        b.wait("!!" + PICK, 5)

    # ---- Current state: storage, read view, Word -----------------------------------------------------------------------

    def test_current_state_round_trip_read_view_and_word(self):
        b = self.b
        item = self.an_item()
        self.open_current("### Top\n\nSee the plan.")
        b.type(" Depends on #" + item["id"][-3:])
        b.wait("!!" + PICK, 5)
        b.key("Enter")
        b.wait("document.querySelectorAll('#curEd .nchip').length===1", 5)
        md = b.eval("curEd.cxed.value()")
        link = re.search(r"\[(ABC-[A-Z0-9-]+ · \w+: [^\]]+)\]\(creaite:item/(ABC-[A-Z0-9-]+)\)", md)
        self.assertTrue(link, md)
        self.assertEqual(link.group(1).split(" · ")[0], link.group(2))
        # the chip is one box that opens the peek
        b.eval("closePanel&&closePanel(true)")
        b.click("#curEd .nchip")
        b.wait("!!document.querySelector('#panel.on')", 5)
        self.assertIn(link.group(2), b.eval("document.getElementById('panel').textContent"))
        self.assertTrue(b.eval("!!shared.CURED && !document.getElementById('discardBar').classList.contains('on')"))      # the unsaved text stays, no question asked
        b.eval("closePanel&&closePanel(true)")
        self.assertEqual(b.eval("curEd.cxed.value()"), md)
        b.click('[data-cure="save"]')
        b.wait("/saved and applied|Not saved/i.test(document.getElementById('snackT').textContent)", 15)
        saved = self.section()
        self.assertIn(link.group(0), saved)                                         # plain Markdown in the project's CLAUDE.md
        self.assertTrue(saved.startswith("### Top"))
        self.assertNotRegex(saved, r"(?m)^## ")
        # Word shows the words, not the address
        import docx_tools
        self.assertEqual(docx_tools.plain(link.group(0)), link.group(1))
        runs = docx_tools.md_runs(saved)
        self.assertIn(link.group(1), [r[0] for r in runs])
        self.assertTrue(all(r[4] is None for r in runs))
        # the read view shows a link that opens the item
        self.v.run(script="build_dashboard.py")
        b.reload("typeof go==='function' && LIVE")
        b.eval("go('cockpit','ABC')")
        b.wait("!!document.querySelector('#v-cockpit a.itemref')", 10)
        self.assertEqual(b.eval("document.querySelector('#v-cockpit a.itemref').textContent"), link.group(1))
        b.eval("document.querySelector('#v-cockpit a.itemref').click()")
        b.wait("!!document.querySelector('#panel.on')", 5)
        b.eval("closePanel&&closePanel(true)")
        # reload into the editor and save again: byte for byte
        b.click("#v-cockpit .curcard [data-edcur]")
        b.wait("!!(document.getElementById('curEd')&&document.getElementById('curEd').cxed)")
        self.assertEqual(b.eval("curEd.cxed.value()"), saved)
        b.eval("curEd.cxed.focus('end')")
        b.type("x")
        b.key("Backspace")
        self.assertEqual(b.eval("curEd.cxed.value()"), saved)

    def test_stray_hash_lines_and_headings_are_unaffected(self):
        b = self.b
        state = "### Heading\n\n#tag at the start\n\n#### Second\n\nplain # text"
        self.open_current(state)
        self.assertEqual(b.eval("curEd.cxed.value()"), state)
        self.assertFalse(b.eval("!!" + PICK))
        b.click('[data-cure="cancel"]')

    def test_plain_hosts_have_no_item_list(self):
        b = self.b
        b.eval("openRecord('actions'," + json.dumps(self.an_item()["id"]) + ")")
        b.wait("!!document.querySelector('#panel.on')", 5)
        b.eval("(()=>{ const e=[...document.querySelectorAll('#panel .ProseMirror')].find(x=>x.cxed); e.cxed.focus('end'); })()")
        b.type(" #")
        b.pump(0.2)
        self.assertFalse(b.eval("!!" + PICK))


    # ---- step C on the round-2 slash pattern: the `#` trigger and ordinary prose --------------------------------------------

    def hosts(self):
        """Each host in turn: (name, editor selector, how to read its text, how to open it)."""
        return (("notes", ".nbody", lambda: self.b.eval("document.querySelector('.nbody').textContent"), lambda: self.make_note("Prose")),
                ("current", "#curEd", lambda: self.b.eval("curEd.textContent"), lambda: self.open_current()))

    def test_prose_with_slashes_and_hashes_is_never_eaten_by_enter_in_both_hosts(self):
        b = self.b
        for name, sel, text, opener in self.hosts():
            opener()
            for prose in ("issue #12", "A / B", "1 / 2", "yes / no"):
                before = text()
                b.type(" " + prose + " ")
                b.pump(0.15)
                self.assertFalse(b.eval("!!document.querySelector('.slashmenu')"), (name, prose))
                self.assertFalse(b.eval("!!" + PICK), (name, prose, "a # then a space closes the list"))
                b.key("Enter")
                b.pump(0.15)
                self.assertIn(prose, text(), (name, prose))                         # Enter made a new line; the words stay as typed
                self.assertTrue(text().startswith(before), (name, prose))
            self.assertNotIn("creaite:item", b.eval(f"document.querySelector({sel!r}).cxed.value()"), name)

    def test_bare_hash_then_space_closes_the_list_and_leaves_text_alone(self):
        b = self.b
        for name, sel, text, opener in self.hosts():
            opener()
            b.type("see #")
            b.wait("!!" + PICK, 5)                                                  # the known stray-# behaviour: the list opens when an item matches
            b.type(" ")
            b.wait(f"!{PICK}", 5)
            self.assertIsNone(b.eval(f"document.querySelector({sel!r}).getAttribute('aria-controls')"), name)
            b.key("Enter")
            b.pump(0.15)
            self.assertIn("see # ", text().replace("\u00a0", " "), name)
            self.assertNotIn("creaite:item", b.eval(f"document.querySelector({sel!r}).cxed.value()"), name)

    def test_hash_after_text_opens_the_list_only_for_a_matching_item_and_escape_keeps_the_text(self):
        b = self.b
        item = self.an_item()
        suffix = item["id"].rsplit("-", 1)[1].lstrip("0") or "0"
        for name, sel, text, opener in self.hosts():
            opener()
            b.type("issue #zzqq9")                                                  # no item matches: no list, text kept
            b.pump(0.15)
            self.assertFalse(b.eval("!!" + PICK), name)
            for _ in "zzqq9":
                b.key("Backspace")
            b.type(suffix)                                                          # an item matches (ABC-A-012 for #12): the list opens
            b.wait("!!" + PICK, 5)
            self.assertEqual(b.eval(f"document.querySelector({sel!r}).getAttribute('aria-expanded')"), "true", name)
            b.key("Escape")                                                         # Esc closes the list and leaves the text as typed
            b.wait(f"!{PICK}", 5)
            self.assertTrue(text().endswith("issue #" + suffix), (name, text()))
            self.assertNotIn("creaite:item", b.eval(f"document.querySelector({sel!r}).cxed.value()"), name)

    def test_slash_work_item_ranking_with_multi_word_queries(self):
        b = self.b
        self.open_current()
        for q in ("item", "work item", "workitem", "work"):
            b.type(" /" + q)
            b.wait("!!document.querySelector('.slashmenu')", 5)
            first = b.eval("document.querySelector('.slashmenu [data-slash]').dataset.slash")
            self.assertEqual(first, "item", (q, first))                            # the Work item row leads the flat ranked list
            b.key("Escape")
            for _ in range(len(q) + 2):
                b.key("Backspace")

    def test_aria_expanded_is_true_during_the_item_list_after_the_slash_row_hands_over(self):
        b = self.b
        self.open_current()
        b.type(" /work")
        b.wait("!!document.querySelector('.slashmenu')", 5)
        self.assertEqual(b.eval("curEd.getAttribute('aria-expanded')"), "true")
        b.key("Enter")
        b.wait("!!" + PICK, 5)
        b.pump(0.2)
        self.assertEqual(b.eval("curEd.getAttribute('aria-expanded')"), "true")      # the picker's state came after the menu's close
        self.assertEqual(b.eval("curEd.getAttribute('aria-controls')"), "ntpick")
        self.assertEqual(b.eval("curEd.getAttribute('aria-haspopup')"), "listbox")
        self.assertFalse(b.eval("!!document.querySelector('.slashmenu')"))
        b.key("Enter", modifiers=4 if b.is_mac() else 2)                              # slashOn holds ⌘↵ back: no save while the list is open
        b.pump(0.2)
        self.assertTrue(b.eval("!!shared.CURED"))
        b.key("Escape")
        b.wait(f"!{PICK}", 5)
        self.assertTrue(b.eval("!!shared.CURED"))
        self.assertNotEqual(b.eval("curEd.getAttribute('aria-expanded')"), "true")


if __name__ == "__main__":
    unittest.main()
