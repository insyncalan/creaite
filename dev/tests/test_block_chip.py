"""BL-256 (dev/COMPONENTS.md §3): the Chip building block, as the Prep popup (BL-286) and Today's day band (BL-293) use it.
Static it is a <span class="chip"> whose name (when given) is read before its value; with onClick, or `button` for a page-wide
handler, it is a <button> named in full, with the tooltip, that runs on a click and on Enter. Its tones are classes; its text
is escaped. (The two branches' tests, joined on release-190.)

Run: python3 dev/tests/test_block_chip.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

MOUNT = """(()=>{ document.getElementById('chipFix')?.remove(); const box=document.createElement('div'); box.id='chipFix';
  document.body.prepend(box); const a=document.createElement('div'), b=document.createElement('div'); box.append(a,b);
  window.__hits=0;
  mount(Chip,{icon:'calendar',name:'When',children:'<b>13-10-2026</b>'},a);
  mount(Chip,{name:'Add ABC-A-001 to the text',tip:'overdue since 01-10-2026',cls:'shsug',onClick:()=>{ window.__hits++; },children:'+ ABC-A-001'},b);
  return true; })()"""


class ChipBlock(LiveBrowserCase):
    shared_server = True        # it only reads

    def setUp(self):
        super().setUp()
        self.b.eval(MOUNT)

    def test_a_static_chip_names_its_value_and_escapes_its_text(self):
        b = self.b
        got = b.eval("(()=>{ const c=document.querySelector('#chipFix span.chip'); return [c.tagName, c.textContent, !!c.querySelector('b'), !!c.querySelector('svg.i'), c.querySelector('.vh').textContent]; })()")
        self.assertEqual(got[0], "SPAN")
        self.assertEqual(got[1], "When: <b>13-10-2026</b>")                         # escaped, not markup
        self.assertFalse(got[2])
        self.assertTrue(got[3])
        self.assertEqual(got[4], "When: ")

    def test_a_button_chip_is_named_has_its_tooltip_and_runs_on_click_and_enter(self):
        b = self.b
        sel = "#chipFix button.chip"
        got = b.eval(f"(()=>{{ const c=document.querySelector('{sel}'); return [c.type, c.getAttribute('aria-label'), c.dataset.tip, c.className]; }})()")
        self.assertEqual(got, ["button", "Add ABC-A-001 to the text", "overdue since 01-10-2026", "chip shsug"])
        b.click(sel)
        b.wait("window.__hits===1")
        b.eval(f"document.querySelector('{sel}').focus()")
        b.key("Enter")
        b.wait("window.__hits===2")


DRAW = """(p=>{ const box=document.createElement('div'); window.CHIPHIT=0; if(p.click){ delete p.click; p.onClick=()=>{ CHIPHIT++; }; }
  drawChip(box,{...p}); window.CHIPBOX=box; return box.innerHTML; })"""


class ChipBlockTones(LiveBrowserCase):
    shared_server = True

    def test_a_statement_is_a_span_with_its_tone(self):
        self.assertEqual(self.b.eval(f"{DRAW}({{tone:'ok',children:'Minutes made'}})"), '<span class="chip ok">Minutes made</span>')

    def test_an_action_is_a_named_button_with_its_tooltip(self):
        b = self.b
        html = b.eval(f"{DRAW}({{tone:'cta plan',name:'Prepare for ABC steering',tip:'Worth preparing for',click:true,children:'Prepare'}})")
        self.assertEqual(html, '<button type="button" class="chip cta plan" aria-label="Prepare for ABC steering" '
                               'data-tip="Worth preparing for">Prepare</button>')
        b.eval("CHIPBOX.querySelector('button').click()")
        self.assertEqual(b.eval("CHIPHIT"), 1)

    def test_a_button_without_a_handler_for_a_page_wide_one(self):
        self.assertEqual(self.b.eval(f"{DRAW}({{tone:'cta',button:true,'data-prep':'0',children:'Prep'}})"),
                         '<button type="button" class="chip cta" data-prep="0">Prep</button>')

    def test_its_text_is_escaped(self):
        html = self.b.eval(f"{DRAW}({{tone:'mute',children:'<i>x</i>'}})")
        self.assertIn("&lt;i&gt;x&lt;/i&gt;", html)


if __name__ == "__main__":
    unittest.main()
