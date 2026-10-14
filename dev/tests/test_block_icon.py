"""BL-256: the Icon and Chip building blocks (dev/COMPONENTS.md §3), first used by BL-286's prep page. Icon draws ic()'s
<svg> from element data, never raw HTML, and is hidden from screen readers; Chip is a span, or a named button when it acts,
and escapes its text.

Run: python3 dev/tests/test_block_icon.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

ICON = "(n=>{ const box=document.createElement('div'); mount(Icon,{name:n},box); return box.innerHTML; })"
OLD = "(n=>{ const d=document.createElement('div'); d.innerHTML=ic(n); return d.innerHTML; })"


class IconAndChipBlocks(LiveBrowserCase):
    shared_server = True        # it only reads

    def test_icon_draws_what_ic_draws(self):
        for n in ("calendar", "external", "mail", "chat", "spark", "filetext", "history", "work", "refresh"):
            with self.subTest(icon=n):
                self.assertEqual(self.b.eval(f"{ICON}({json.dumps(n)})"), self.b.eval(f"{OLD}({json.dumps(n)})"))

    def test_icon_is_hidden_and_an_unknown_one_is_empty(self):
        out = self.b.eval(f"{ICON}('nothing-by-this-name')")
        self.assertIn('aria-hidden="true"', out)
        self.assertNotIn("<path", out)

    def test_icon_keeps_only_plain_shapes(self):
        shapes = self.b.eval("(()=>{ ICONS.__t='<path d=\"M1 1\" onload=\"x()\"/><script>x()</script><circle cx=\"2\" cy=\"2\" r=\"1\"/>'; return iconShapes('__t'); })()")
        self.assertEqual(shapes, [["path", {"d": "M1 1"}], ["circle", {"cx": "2", "cy": "2", "r": "1"}]])

    def test_chip_static_and_as_a_button(self):
        b = self.b
        out = b.eval("(()=>{ const box=document.createElement('div'); mount(Chip,{name:'Project',children:'<i>Example</i>'},box); return box.innerHTML; })()")
        self.assertTrue(out.startswith('<span class="chip">'), out)
        self.assertIn("&lt;i&gt;Example&lt;/i&gt;", out)
        self.assertIn('<span class="vh">Project: </span>', out)                  # its name for a screen reader
        btn = b.eval("(()=>{ const box=document.createElement('div'); window.__hit=0; mount(Chip,{name:'Change project',icon:'calendar',onClick:()=>window.__hit++,children:'Example'},box); "
                     "document.body.append(box); const x=box.querySelector('button'); x.click(); return [x.type,x.getAttribute('aria-label'),x.dataset.tip,window.__hit,!!x.querySelector('svg[aria-hidden=true]')]; })()")
        self.assertEqual(btn, ["button", "Change project", "Change project", 1, True])


if __name__ == "__main__":
    unittest.main()
