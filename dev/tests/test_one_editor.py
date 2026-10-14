"""BL-301 A: the one editor, in a real browser against the real live server. Each place that edits text in place uses it,
loads its text, edits it, saves it byte for byte by its own save path, and keeps its Undo and keys.

Run: python3 dev/tests/test_one_editor.py   (needs Google Chrome; skipped otherwise)

The places (dev/V20-ONE-EDITOR-NOTE.md lists them): Current state's two panes (Markdown), the peek's text fields and
Prep's notes and questions (plain text; Prep's own flows are in test_prep_view and test_prep_shape). The gate itself
(every Current state round-trips) is test_one_editor_gate.
"""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

META, SHIFT = 4, 8
MOD = META if sys.platform == "darwin" else 2      # the editor's Mod key: ⌘ on a Mac, Ctrl elsewhere (CI runs on Linux)
MARKER = "<!-- creaite: second pane -->"
# forms the old editor rewrote on every save (italic with stars, an entity, a nested numbered list, a bare link, a comment)
LEFT = ("Status is *provisional* and Q&A is &amp; done.\n\n1. Escalate\n  1. Sponsor first\n\n"
        "See https://example.com/plan for dates.\n\n<!-- kept out of sight -->\n\nLast line.")
RIGHT = "Alan's own notes."


class CurrentState(LiveBrowserCase):
    """Current state's panes: Markdown, saved by saveCurEdit → saveCurrent, as before."""

    width, height = 1280, 900

    def setUp(self):
        super().setUp()
        mem = self.memory()
        text = mem.read_text(encoding="utf-8")
        mem.write_text(re.sub(r"(## Current state\n).*?(?=\n## |\Z)", lambda m: m.group(1) + f"\n{LEFT}\n\n{MARKER}\n\n{RIGHT}\n",
                              text, flags=re.S), encoding="utf-8")
        self.v.run(script="build_dashboard.py")
        self.b.reload("typeof go==='function' && LIVE")

    def memory(self):
        return next((self.v.root / "projects").glob("ABC */CLAUDE.md"))

    def section(self):
        return re.search(r"## Current state\n(.*?)(?=\n## |\Z)", self.memory().read_text(encoding="utf-8"), re.S).group(1).strip()

    def open_editor(self):
        b = self.b
        b.eval("go('cockpit','ABC')")
        b.wait("document.querySelector('#v-cockpit .curcard [data-edcur]')")
        b.click("#v-cockpit .curcard [data-edcur]")
        b.wait("!!(document.getElementById('curEd')&&document.getElementById('curEd').cxed&&document.getElementById('curEd2')&&document.getElementById('curEd2').cxed)")
        return b.eval("P.find(x=>x.code==='ABC').current")

    def end(self, pane):
        """The cursor at the end of a pane (the editor focuses on the next frame)."""
        self.b.eval(f"{pane}.cxed.focus('end')")
        self.b.wait(f"document.activeElement==={pane}", 5)
        self.b.pump(0.1)

    def save(self):
        b = self.b
        b.eval("document.getElementById('snackT').textContent=''")
        b.key("Enter", META)
        b.wait("!document.getElementById('curEd')||/Not saved/.test(document.getElementById('snackT').textContent)", 15)
        b.wait("/saved and applied|Not saved/i.test(document.getElementById('snackT').textContent)", 15)
        return b.eval("document.getElementById('snackT').textContent")

    def test_each_pane_is_the_one_editor_named_for_screen_readers(self):
        self.open_editor()
        got = self.b.eval("""['curEd','curEd2'].map(id=>{ const e=document.getElementById(id);
          return [e.cxed.features, e.getAttribute('role'), e.getAttribute('aria-multiline'), e.getAttribute('aria-label'), e.isContentEditable]; })""")
        self.assertEqual([g[:3] for g in got], [["current", "textbox", "true"]] * 2)
        self.assertTrue(all(g[4] for g in got))
        self.assertRegex(got[0][3], r"left pane$")
        self.assertRegex(got[1][3], r"right pane$")
        self.assertEqual(self.b.eval("getComputedStyle(document.querySelector('#curEd [data-md-html]')).display"), "none")   # the comment, hidden

    def test_opening_and_saving_unchanged_writes_nothing(self):
        before = self.memory().read_bytes()
        self.open_editor()
        self.assertEqual(self.b.eval("joinPanes(edValue(curEd),edValue(curEd2))===P.find(x=>x.code==='ABC').current"), True)
        self.b.click('[data-cure="save"]')
        self.b.wait("!document.getElementById('curEd')", 5)
        self.assertEqual(self.memory().read_bytes(), before)

    def test_a_small_edit_saves_everything_else_byte_for_byte(self):
        shown = self.open_editor()
        self.end("curEd")
        self.b.type(" Added.")
        self.assertIn("saved and applied", self.save())
        self.assertEqual(self.section(), shown.replace("Last line.", "Last line. Added."))
        self.assertIn(MARKER, self.section())
        self.assertIn("<!-- kept out of sight -->", self.section())

    def test_undo_and_redo_are_the_editors_keys(self):
        shown = self.open_editor()
        b = self.b
        self.end("curEd")
        b.type(" Typed")
        self.assertIn("Last line. Typed", b.eval("edValue(curEd)"))
        b.key("z", MOD)
        self.assertEqual(b.eval("joinPanes(edValue(curEd),edValue(curEd2))"), shown)
        b.key("z", MOD | SHIFT)
        self.assertIn("Last line. Typed", b.eval("edValue(curEd)"))

    def test_bold_and_a_list_from_the_keys_and_the_toolbar(self):
        self.open_editor()
        b = self.b
        self.end("curEd2")
        b.key("Enter")
        b.type("Bold")
        b.eval("const e=curEd2.cxed.editor; const to=e.state.selection.from; e.commands.setTextSelection({from:to-4,to})")
        b.key("b", MOD)
        self.end("curEd2")
        b.key("Enter")
        b.key("b", MOD)                                     # bold off again for the next line
        b.type("Item")
        b.click('.inplace [data-rc="insertUnorderedList"]')
        self.assertIn("saved and applied", self.save())
        self.assertTrue(self.section().endswith(f"{MARKER}\n\n{RIGHT}\n\n**Bold**\n\n- Item"), self.section())

    def test_escape_asks_before_losing_an_edit(self):
        self.open_editor()
        b = self.b
        self.end("curEd")
        b.type(" Unsaved")
        b.key("Escape")
        b.wait("document.getElementById('discardBar').classList.contains('on')", 5)
        b.click('[data-dis="keep"]')
        self.assertIn("Unsaved", b.eval("edValue(curEd)"))

    def test_nothing_sideways_at_320_and_dark_and_reduced_motion(self):
        self.open_editor()
        b = self.b
        b.resize(320, 800)
        b.wait("document.documentElement.clientWidth<=320")
        self.assertLessEqual(b.eval("document.documentElement.scrollWidth"), b.eval("document.documentElement.clientWidth"))
        b.eval("document.documentElement.dataset.theme='dark'")
        same = b.eval("(()=>{ const e=getComputedStyle(curEd), c=getComputedStyle(document.querySelector('#v-cockpit .curcard')); return e.color===c.color; })()")
        self.assertTrue(same, "the editor's text takes the theme's colour")
        self.assertEqual(b.eval("getComputedStyle(curEd).transitionDuration"), "0s")


class PeekText(LiveBrowserCase):
    """The peek's text fields: plain text, staged on leaving the field, as before."""

    def open_action(self):
        b = self.b
        b.eval("WT='actions'; go('work')")
        b.wait("document.querySelector('#workTbl tbody tr[data-row]')")
        id_ = b.eval("A.find(x=>x.p==='ABC').id")
        b.eval(f"openRecord('actions',{id_!r})")
        b.wait(f"CUR&&CUR.id==={id_!r}&&document.getElementById('panel').classList.contains('peek')")
        b.pump(0.3)
        return id_

    def test_every_text_field_is_the_one_editor_as_plain_text(self):
        self.open_action()
        got = self.b.eval("[...document.querySelectorAll('#panel .pked[data-pkf]')].filter(e=>!e.hidden).map(e=>[e.id||e.dataset.pkf,e.cxed&&e.cxed.features,e.getAttribute('role')])")
        self.assertTrue(got)
        self.assertTrue(all(g[1] == "plain" and g[2] == "textbox" for g in got), got)

    def test_the_latest_update_is_staged_as_typed_and_undo_works_in_the_field(self):
        id_ = self.open_action()
        b = self.b
        b.click("#pkDesc")
        b.eval("pkDesc.cxed.editor.commands.selectAll()")
        b.type("First line")
        b.key("Enter")
        b.type("Second & <third>")
        self.assertEqual(b.eval("pkDesc.textContent"), "First line\nSecond & <third>")
        b.key("z", MOD)
        self.assertNotEqual(b.eval("pkDesc.textContent"), "First line\nSecond & <third>")
        b.key("z", MOD | SHIFT)
        b.eval("pkDesc.blur()")
        b.wait(f"(A.find(x=>x.id==={id_!r})||{{}}).upd==='First line\\nSecond & <third>'||PKS.some(s=>JSON.stringify(s).includes('Second & <third>'))", 10)

    def test_enter_ends_the_title_and_escape_puts_it_back(self):
        self.open_action()
        b = self.b
        before = b.eval("pkTitle.textContent")
        b.click("#pkTitle")
        b.type(" more")
        b.key("Escape")
        self.assertEqual(b.eval("pkTitle.textContent"), before)
        b.click("#pkTitle")
        b.key("Enter")
        self.assertNotEqual(b.eval("document.activeElement.id"), "pkTitle")
        self.assertEqual(b.eval("pkTitle.textContent.includes('\\n')"), False)


if __name__ == "__main__":
    unittest.main()
