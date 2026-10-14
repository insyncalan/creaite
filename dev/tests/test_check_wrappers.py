"""check.py's `wrappers` figure (BL-231 counts down to 0 from it) counts the dashboard's in-place function wrappers exactly,
the same as dev/tools/wrappers.py's inventory: `const a = f; f = function…` (or an arrow) for a function the page defines,
also with a comment or another declarator between; never a value swapped (`const was = LIVE; LIVE = on`), a temporary swap
put back later (`readForm = rf`), or a callback composed inside a function (`const d0 = doIt; doIt = () => …`).

Run: python3 dev/tests/test_check_wrappers.py     (quick tier: no Chrome)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import check  # noqa: E402

DEFS = "function go(v){} async function load(){} let evRoot=which=>which; let cfg=(a)=>a; function readForm(){} "


class Wrappers(unittest.TestCase):
    def count(self, js):
        return check.wrappers(DEFS + js)

    def test_a_wrapper_is_counted(self):
        for js in ("const g=go; go=function(v){ g(v); };",
                   "const l=load; load=async function(){ await l(); };",
                   "const e=evRoot; evRoot=w=>e(w);",
                   "const c=cfg; cfg=(a)=>c(a);",
                   "{ const g=go; go=(v)=>{ g(v); }; }"):
            with self.subTest(js):
                self.assertEqual(self.count(js), 1)

    def test_a_comment_or_another_declarator_between_still_counts(self):
        for js in ("const g=go;   /* why it is wrapped */\ngo=function(v){ g(v); };",
                   "const g=go; // why\ngo=function(v){ g(v); };",
                   "{ const s=new Set(), g=go; go=function(v){ g(v); }; }",
                   "{ const g=go, l=load; go=function(v){ g(v); }; }"):
            with self.subTest(js):
                self.assertEqual(self.count(js), 1)

    def test_what_isnt_a_wrapper_is_not_counted(self):
        for js in ("let LIVE=false; function setLive(on){ const was=LIVE; LIVE=on; }",          # a value swapped
                   "let CFG={}; function save(c){ const was=CFG; CFG=norm(c); }",              # a value swapped for a call's result
                   "async function close(){ const rf=readForm; readForm=()=>({}); try{ await x(); } finally{ readForm=rf; } }",
                   "save=async function(what,doIt){ const d0=doIt; doIt=()=>{ d0(); }; };",   # a callback, not a page function
                   "const g=go; if(g===go) go2();",                                            # captured, not reassigned
                   "const g=go; go==null;"):                                                   # a comparison, not an assignment
            with self.subTest(js):
                self.assertEqual(self.count(js), 0)

    def test_the_dashboard_figure_is_the_ratchet_figure(self):
        """The baseline holds the dashboard's count; check.py and the baseline agree on today's page."""
        import json
        base = json.loads((check.ROOT / "dev" / "check-baseline.json").read_text(encoding="utf-8"))
        self.assertLessEqual(check.wrappers(check.dashboard_js()), base["js"]["wrappers"])


if __name__ == "__main__":
    unittest.main()
