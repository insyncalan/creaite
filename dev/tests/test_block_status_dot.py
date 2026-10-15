"""BL-256: StatusDot, the first Preact component (dev/COMPONENTS.md). It draws exactly the markup core/page.js's health()
writes, carries its word as well as its colour, escapes its text, and Today's portfolio table uses it.

Run: python3 dev/tests/test_block_status_dot.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

# Mount a StatusDot for health `h` through a placeholder, as Today does, and return the markup it leaves.
DRAW = ("(h=>{ const box=document.createElement('div'), ph=document.createElement('span'); ph.setAttribute('data-statusdot',h);"
        " box.appendChild(ph); mountStatusDots(box); return box.innerHTML; })")
# health()'s string as the browser parses it (the same DOM the old screen had), for comparison.
OLD = "(h=>{ const d=document.createElement('div'); d.innerHTML=health(h); return d.innerHTML; })"


class StatusDotBlock(LiveBrowserCase):
    shared_server = True        # it only reads

    def test_it_draws_what_health_draws_for_every_health(self):
        for h in ("On track", "At risk", "Off track", "", "Something else"):
            with self.subTest(health=h):
                self.assertEqual(self.b.eval(f"{DRAW}({json.dumps(h)})"), self.b.eval(f"{OLD}({json.dumps(h)})"))

    def test_it_carries_its_word_not_colour_alone(self):
        self.assertEqual(self.b.eval(f"(()=>{{ const d=document.createElement('div'); d.innerHTML={DRAW}('At risk'); return d.textContent; }})()"), "At risk")
        self.assertEqual(self.b.eval(f"(()=>{{ const d=document.createElement('div'); d.innerHTML={DRAW}(''); return d.textContent; }})()"), "Not set")

    def test_its_text_is_escaped(self):
        out = self.b.eval(f"{DRAW}('<b>x</b>')")
        self.assertIn("&lt;b&gt;x&lt;/b&gt;", out)
        self.assertNotIn("<b>", out)

    def test_a_plain_status_dot_carries_its_word(self):
        """BL-316: `status` draws a plain dot; its word is beside it (the dot hidden), in a named span, or its own name."""
        b = self.b
        out = b.eval("""(()=>{ const box=document.createElement('div'), r=p=>{ drawStatusDot(box,p); return box.innerHTML; };
          return [r({status:'ok',word:'Live <b>now</b>'}), r({status:'off',word:'Not running'}),
            r({status:'staged',wordId:'stX',live:true,word:'2 staged'}), r({status:'staged',cls:'pkdot',label:'Staged, not yet applied'})]; })()""")
        self.assertEqual(out[0], '<span class="dot" aria-hidden="true"></span>Live &lt;b&gt;now&lt;/b&gt;')
        self.assertEqual(out[1], '<span class="dot off" aria-hidden="true"></span>Not running')
        self.assertEqual(out[2], '<span class="dot" aria-hidden="true"></span><span id="stX" aria-live="polite">2 staged</span>')
        self.assertEqual(out[3], '<span class="pkdot" role="img" aria-label="Staged, not yet applied" data-tip="Staged, not yet applied"></span>')

    def test_the_page_s_status_dots_use_it(self):
        b = self.b
        self.assertEqual(b.eval("document.querySelector('#pkStage .dot').nextElementSibling.id"), "pkStN")
        self.assertEqual(b.eval("document.querySelector('#chSub .dot').getAttribute('aria-hidden')"), "true")
        self.assertTrue(b.eval("document.getElementById('chSub').textContent.length>10"))

    def test_today_s_portfolio_table_uses_it(self):
        b = self.b
        b.eval("go('today')")
        b.wait("document.querySelectorAll('#pfTbl .health').length>0")
        self.assertEqual(b.eval("document.querySelectorAll('#pfTbl [data-statusdot]').length"), 0, "every placeholder replaced")
        same = b.eval("[...document.querySelectorAll('#pfTbl .health')].every(e=>{ const w=e.textContent; "
                      f"return e.outerHTML==={OLD}(w==='Not set'?'':w); }})")
        self.assertTrue(same, "each marker is health()'s markup")


if __name__ == "__main__":
    unittest.main()
