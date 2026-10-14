"""BL-256 (dev/COMPONENTS.md §3): the IconButton building block, first used by BL-319's Today rows. It draws ibtn's markup
(<button class="ib">), names what it does in the tooltip (data-tip) and to a screen reader (aria-label, or `name` when the row's
words are added), runs on a click and on Enter, and, blocked by `why`, stays focusable with aria-disabled and the reason as its
tooltip, calling onBlocked instead. Its data-* attributes are there for page-wide handlers.

Run: python3 dev/tests/test_block_icon_button.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

DRAW = """(p=>{ const box=document.createElement('div'); document.body.prepend(box); window.IBHIT=0; window.IBBLOCK=0;
  drawIconButton(box,{...p,onClick:()=>{ IBHIT++; },onBlocked:()=>{ IBBLOCK++; }}); window.IBBOX=box; return true; })"""


class IconButtonBlock(LiveBrowserCase):
    shared_server = True

    def test_named_with_its_tooltip_and_runs_on_click_and_enter(self):
        b = self.b
        b.eval(f"{DRAW}({{icon:'check',label:'Approve and save',name:'Approve and save: <b>Plan</b>',primary:true,data:{{tdact:'approve'}}}})")
        o = b.eval("""(()=>{ const x=IBBOX.querySelector('button'); return [x.type,x.className,x.getAttribute('aria-label'),x.dataset.tip,x.dataset.tdact,
          !!x.querySelector('svg.i[aria-hidden=true]'),x.hasAttribute('aria-disabled'),x.querySelector('b')===null]; })()""")
        self.assertEqual(o, ["button", "ib sm pri", "Approve and save: <b>Plan</b>", "Approve and save", "approve", True, False, True])   # escaped
        b.eval("IBBOX.querySelector('button').click()")
        self.assertEqual(b.eval("IBHIT"), 1)
        b.eval("IBBOX.querySelector('button').focus()")
        b.key("Enter")
        b.wait("IBHIT===2")

    def test_blocked_says_why_and_never_runs(self):
        b = self.b
        b.eval(f"{DRAW}({{icon:'play',label:'Process the transcript',why:'Needs the live server',haspopup:'menu'}})")
        o = b.eval("""(()=>{ const x=IBBOX.querySelector('button'); x.click(); return [x.getAttribute('aria-disabled'),x.dataset.tip,x.getAttribute('aria-label'),x.disabled,x.getAttribute('aria-haspopup'),IBHIT,IBBLOCK]; })()""")
        self.assertEqual(o, ["true", "Needs the live server", "Process the transcript", False, "menu", 0, 1])


if __name__ == "__main__":
    unittest.main()
