"""BL-168 (sprint-polish-2): Help's loop diagram reflows by the room it has. A real browser against the real live server.

Run: python3 dev/tests/test_help_loop.py   (needs Google Chrome; skipped otherwise)

Below about 900px of its own width the five steps stack (one column, the arrows turned down) rather than squeezing, and no
text in the diagram is under 12px, at any width. Since BL-173 ask creaite opens over the page, so the chat being open doesn't
reflow it; the generated guides carry the same rule.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_tracker import REPO  # noqa: E402

LOOP = """(()=>{ const f=document.querySelector('#helpPane .hp-flow'); const a=f.querySelector('.hp-arrow');
  const texts=[...f.closest('.hp-loop').querySelectorAll('*')].filter(e=>[...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim())&&e.getClientRects().length);
  const st=[...f.querySelectorAll(':scope>.hp-stage')].map(s=>Math.round(s.getBoundingClientRect().left));
  return {cols:getComputedStyle(f).gridTemplateColumns.split(' ').length, lefts:new Set(st).size, min:Math.min(...texts.map(e=>parseFloat(getComputedStyle(e).fontSize))),
    turned:a?getComputedStyle(a).transform!=='none':null, width:Math.round(f.getBoundingClientRect().width)}; })()"""


class HelpLoop(LiveBrowserCase):
    shared_server = True

    def loop(self, width, chat=False, frame=None):
        b = self.b
        b.resize(width, 900)
        b.eval("closeChat(); go('help','start')")
        b.wait("document.querySelector('#helpPane .hp-flow')")
        if frame:
            b.eval(f"document.querySelector('#helpPane .hp-loop').style.width='{frame}px'")
        if chat:
            b.eval("openChat()")
        b.pump(0.4)
        r = b.eval(LOOP)
        b.eval("document.querySelector('#helpPane .hp-loop').style.width=''; closeChat()")
        return r

    def test_wide_it_is_five_columns(self):
        r = self.loop(1400)
        self.assertEqual((r["cols"], r["lefts"]), (5, 5))
        self.assertGreaterEqual(r["min"], 12)

    def test_at_900_the_steps_stack_with_no_small_text(self):
        for chat in (False, True):
            r = self.loop(900, chat)
            self.assertEqual((r["cols"], r["lefts"]), (1, 1), chat)
            self.assertTrue(r["turned"])
            self.assertGreaterEqual(r["min"], 12)

    def test_at_1100_the_chat_changes_nothing(self):
        closed, opened = self.loop(1100), self.loop(1100, chat=True)
        self.assertEqual(opened, closed)                                              # BL-173: over the page, no reflow
        self.assertGreaterEqual(opened["min"], 12)

    def test_it_follows_its_own_width_not_the_window(self):
        r = self.loop(1400, frame=700)
        self.assertEqual(r["cols"], 1)
        self.assertGreaterEqual(r["min"], 12)

    def test_the_guides_carry_the_rule(self):
        for g in ("guide-first-day.html", "guide-how-to.html"):
            text = (REPO / "system/templates" / g).read_text(encoding="utf-8")
            self.assertIn("BL-168 (sprint-polish-2)", text, g)
            self.assertIn("@container (max-width:900px)", text, g)


if __name__ == "__main__":
    unittest.main()
