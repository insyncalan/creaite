"""BL-301 A (dev/COMPONENTS.md §3, §6): the TextEditor building block, and the one editor under it (core/editor.js
`creaiteEditor`), on a small fixture. TextEditor is a box of plain text on the one editor: a named textbox, one paragraph a
line, its element's `value` reads and sets the text as a textarea's did, onInput on each change and onCommit when left,
Undo and Redo the editor's, Enter refused when it is one line, and its text is text, never markup. `creaiteEditor`
gives a text nobody changed back as it came, writes an edited one, and a value set by code is quiet (not an edit).

Run: python3 dev/tests/test_block_texteditor.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

META, SHIFT = 4, 8
TEXT = "First line <b>not bold</b>\n\n  *kept as typed*"

# Mount two TextEditors (many lines, and one line) on a fixture; record each onInput and onCommit.
MOUNT = """(t=>{ document.getElementById('teFix')?.remove(); const box=document.createElement('div'); box.id='teFix';
  document.body.prepend(box); const lab=document.createElement('span'); lab.id='teLab'; lab.textContent='Notes for the steering';
  const a=document.createElement('div'), b=document.createElement('div'); box.append(lab,a,b);
  window.TE={inp:[],com:[],inp1:[]};
  window.TEPROPS=v=>({id:'teMany',value:v,cls:'ppbox',rows:3,placeholder:'Your notes',labelledBy:'teLab',
    onInput:x=>TE.inp.push(x),onCommit:x=>TE.com.push(x)});
  mount(TextEditor,TEPROPS(t),a);
  mount(TextEditor,{id:'teOne',value:'One line',multiline:false,labelledBy:'teLab',onInput:x=>TE.inp1.push(x)},b);
  window.TEA=a; return true; })"""


class TextEditorBlock(LiveBrowserCase):
    shared_server = True        # it only reads

    def setUp(self):
        super().setUp()
        self.b.eval(f"{MOUNT}({json.dumps(TEXT)})")
        self.b.wait("!!document.querySelector('#teMany.ProseMirror') && !!document.querySelector('#teOne.ProseMirror')")

    def end_of(self, sel):
        self.b.eval(f"edOf(document.querySelector('{sel}')).focus('end')")
        self.b.wait(f"document.activeElement===document.querySelector('{sel}')")

    def test_it_is_a_named_textbox_on_the_one_editor(self):
        got = self.b.eval("(()=>{ const e=document.querySelector('#teMany'), o=document.querySelector('#teOne'); return [e.getAttribute('role'),"
                          " e.getAttribute('aria-multiline'), o.getAttribute('aria-multiline'), e.getAttribute('aria-labelledby'),"
                          " e.dataset.ph, e.isContentEditable, e.classList.contains('ppbox'), !!edOf(e), edOf(e).features]; })()")
        self.assertEqual(got, ["textbox", "true", "false", "teLab", "Your notes", True, True, True, "plain"])

    def test_its_text_is_text_one_paragraph_a_line_and_value_gives_it_back_as_given(self):
        got = self.b.eval("(()=>{ const e=document.querySelector('#teMany'); return [e.value, e.querySelectorAll('p').length,"
                          " !!e.querySelector('b,em,strong'), e.querySelector('p').textContent]; })()")
        self.assertEqual(got, [TEXT, 3, False, "First line <b>not bold</b>"])
        self.assertEqual(self.b.eval("TE.inp.length"), 0, "mounting is not an edit")

    def test_typing_fires_on_input_and_leaving_fires_on_commit(self):
        b = self.b
        self.end_of("#teMany")
        b.type("!")
        b.wait("TE.inp.length>0")
        self.assertEqual(b.eval("TE.inp[TE.inp.length-1]"), TEXT + "!")
        b.eval("document.querySelector('#teMany').blur()")
        b.wait("TE.com.length===1")
        self.assertEqual(b.eval("TE.com[0]"), TEXT + "!")

    def test_enter_makes_a_line_and_undo_and_redo_are_the_editor_s(self):
        b = self.b
        self.end_of("#teMany")
        b.key("Enter")
        b.type("x")
        b.wait("document.querySelector('#teMany').value.endsWith('\\nx')")
        b.key("z", META)
        b.wait(f"document.querySelector('#teMany').value==={json.dumps(TEXT)}")
        b.key("z", META | SHIFT)
        b.wait("document.querySelector('#teMany').value.endsWith('\\nx')")

    def test_a_one_line_box_refuses_enter_and_pastes_on_one_line(self):
        b = self.b
        self.end_of("#teOne")
        b.key("Enter")
        b.type("s")
        b.wait("TE.inp1.length>0")
        self.assertEqual(b.eval("document.querySelector('#teOne').value"), "One lines")
        self.assertEqual(b.eval("document.querySelectorAll('#teOne p').length"), 1)

    def test_setting_value_by_code_is_quiet_and_new_props_never_land_under_the_cursor(self):
        b = self.b
        b.eval("document.querySelector('#teMany').value='Set by code\\nTwo'")
        self.assertEqual(b.eval("[document.querySelector('#teMany').value, document.querySelectorAll('#teMany p').length, TE.inp.length]"),
                         ["Set by code\nTwo", 2, 0])
        b.eval("mount(TextEditor,TEPROPS('From the store'),TEA); true")       # not focused: the new value is shown
        b.wait("document.querySelector('#teMany').value==='From the store'")
        self.end_of("#teMany")
        b.eval("mount(TextEditor,TEPROPS('Regenerated'),TEA); true")          # focused: what is being typed stays
        b.pump(0.2)
        self.assertEqual(b.eval("document.querySelector('#teMany').value"), "From the store")


class OneEditor(LiveBrowserCase):
    """`creaiteEditor` itself, and its helpers (edOf, edValue, edSet), on an element of the fixture's own."""

    shared_server = True

    MK = """((md,o)=>{ document.getElementById('ceFix')?.remove(); const el=document.createElement('div'); el.id='ceFix'; el.dataset.k='x';
      el.setAttribute('aria-label','Current state'); document.body.prepend(el); window.CEI=0; el.addEventListener('input',()=>{ CEI++; });
      window.XED=creaiteEditor(el,{markdown:md,...(o||{})}); return true; })"""

    def test_it_mounts_on_the_element_given_and_keeps_its_names(self):
        self.b.eval(f"{self.MK}('Hello')")
        got = self.b.eval("(()=>{ const e=document.querySelector('#ceFix'); return [e.dataset.k, e.getAttribute('aria-label'),"
                          " e.classList.contains('ProseMirror'), edOf(e)===XED, edOf(e.firstElementChild)===XED]; })()")
        self.assertEqual(got, ["x", "Current state", True, True, True])

    def test_a_text_nobody_changed_is_given_back_as_it_came(self):
        md = "Status is *provisional* &amp; Q&A.\n\n1. One\n  1. Nested\n\nSee https://example.com.\n\n<!-- hidden -->\n"
        self.b.eval(f"{self.MK}({json.dumps(md)})")
        self.assertEqual(self.b.eval("[XED.value(), edValue(document.querySelector('#ceFix')), XED.touched(), CEI]"), [md, md, False, 0])

    def test_an_edit_fires_input_and_is_written_as_markdown(self):
        b = self.b
        b.eval(f"{self.MK}('Plain **bold** words')")
        b.eval("XED.focus('end')")
        b.wait("document.activeElement===document.querySelector('#ceFix')")
        b.type("!x")
        b.wait("CEI>0")
        self.assertTrue(b.eval("XED.touched()"))
        self.assertEqual(b.eval("XED.value()"), "Plain **bold** words!x")

    def test_set_value_is_quiet_and_destroy_lets_the_element_go(self):
        b = self.b
        b.eval(f"{self.MK}('Before')")
        b.eval("edSet(document.querySelector('#ceFix'),'After *this*')")
        self.assertEqual(b.eval("[XED.value(), XED.touched(), CEI, !!document.querySelector('#ceFix em')]"), ["After *this*", False, 0, True])
        b.eval("XED.destroy()")
        self.assertIsNone(b.eval("edOf(document.querySelector('#ceFix'))"))

    def test_plain_features_keep_markdown_as_text(self):
        b = self.b
        b.eval(f"{self.MK}(undefined,{{features:'plain',text:'1. not a list\\n**not bold**'}})")
        self.assertEqual(b.eval("[XED.value(), !!document.querySelector('#ceFix ol,#ceFix strong'), document.querySelectorAll('#ceFix p').length]"),
                         ["1. not a list\n**not bold**", False, 2])


if __name__ == "__main__":
    unittest.main()
