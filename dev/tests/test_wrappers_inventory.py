"""dev/tools/wrappers.py (BL-231 step 1): the inventory of in-place wrappers, on a small sample page and on the dashboard.

Run: python3 dev/tests/test_wrappers_inventory.py     (quick tier: no Chrome, no vault)
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import wrappers  # noqa: E402

SAMPLE = """<!doctype html>
<script type="application/json" id="data">{"go": "not code"}</script>
<script>
/* ===== core ===== */
function go(v){ return v; }
function draw(){ return 1; }
function swap(){ return 0; }
let LIVE=false;
const s1="go(", t1=`go ${"x"} go`, r1=/go\\(/g;   // go( in a comment
$("#a").onclick=go;
{ const g0=go; go=function(v){ return g0(v)+1; }; }
$("#b").addEventListener("click", go);
const opts={go:1, other:go};
function later(){ $("#c").onclick=go; return go(2); }
function param(go){ return go; }
const arrow=(go)=>go;
/* ===== more ===== */
{ const g1=go; /* a comment hides it from check.py */ go=async function(v){ return g1(v)*2; }; }
draw();
{ const seen=new Set(), d0=draw; draw=function(){ return d0()+seen.size; }; }
swap=function(){ return 9; };
{ const w0=swap; swap=x=>w0()+1; }
const was=LIVE; LIVE=true;
function tmp(){ const g=go; go=()=>0; try{ return g(1); } finally{ go=g; } }
</script>
"""


class SampleTests(unittest.TestCase):
    """The tool on a page small enough to check by hand."""

    @classmethod
    def setUpClass(cls):
        cls.inv = wrappers.inventory(SAMPLE, "sample.html", size=2)
        cls.chains = {c["name"]: c for c in cls.inv["chains"]}

    def test_chains_in_order(self):
        go = self.chains["go"]
        self.assertEqual([d["line"] for d in go["definitions"]], [5])
        self.assertEqual([(s["kind"], s["line"], s["alias"]) for s in go["steps"]],
                         [("wrapper", 11, "g0"), ("wrapper", 18, "g1")])
        self.assertTrue(go["steps"][1]["async"])
        self.assertEqual(go["steps"][1]["block"], "more")

    def test_early_references(self):
        early = [(e["line"], e["kind"], e["sees"]) for e in self.chains["go"]["early_references"]]
        # line 10 takes the original; 12 and 13 sit between the two wrappers. Strings, templates, regular expressions,
        # comments, object keys, function bodies and parameters (lines 9, 13's key, 14 to 16) are not uses at load.
        self.assertEqual(early, [(10, "reference", 0), (12, "reference", 1), (13, "reference", 1)])
        self.assertEqual([(e["line"], e["kind"]) for e in self.chains["draw"]["early_references"]], [(19, "call")])

    def test_second_declarator_and_comment(self):
        self.assertEqual([s["line"] for s in self.chains["draw"]["steps"]], [20])
        self.assertEqual(self.inv["summary"]["missed_by_check_py"], [])            # check.py sees both now (fix-wrapper-count)

    def test_replacement_starts_the_chain(self):
        self.assertEqual([s["kind"] for s in self.chains["swap"]["steps"]], ["replacement", "wrapper"])

    def test_not_wrappers(self):
        got = {(x["name"], x["reason"].split(",")[0]) for x in self.inv["not_wrappers"]}
        self.assertEqual(got, set())          # check.py no longer counts the LIVE swap or tmp's go swap (fix-wrapper-count)

    def test_counts_reconcile_with_check_py(self):
        s = self.inv["summary"]
        self.assertEqual(s["check_py_count"], s["wrappers"] - len(s["missed_by_check_py"]) + s["not_wrappers"])
        self.assertEqual((s["chains"], s["wrappers"], s["replacements"]), (3, 4, 1))

    def test_batches_put_go_last_and_alone(self):
        b = self.inv["batches"]
        self.assertEqual(b[-1]["chains"], ["go"])
        self.assertTrue(all(x["wrappers"] <= 2 for x in b))
        self.assertEqual(sorted(n for x in b for n in x["chains"]), ["draw", "go", "swap"])

    def test_unpaired_bracket_is_refused(self):
        with self.assertRaises(ValueError):
            wrappers.inventory("<script>function f(){ if(x){ }</script>")

    def test_cli_writes_json(self):
        with tempfile.TemporaryDirectory() as d:
            page, out = Path(d) / "p.html", Path(d) / "inv.json"
            page.write_text(SAMPLE, encoding="utf-8")
            self.assertEqual(wrappers.main(["--file", str(page), "--json", str(out), "--quiet"]), 0)
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["summary"]["wrappers"], 4)


class DashboardTests(unittest.TestCase):
    """The tool on today's dashboard: it reads the whole script, and its figures agree with check.py's."""

    def test_dashboard(self):
        """BL-231 phase 2 folded every wrapper: the tool reads the whole script and finds none, as check.py does."""
        inv = wrappers.inventory(wrappers.DASHBOARD.read_text(encoding="utf-8"))
        s = inv["summary"]
        self.assertEqual(s["wrappers"], 0)
        self.assertEqual(s["check_py_count"], s["wrappers"] - len(s["missed_by_check_py"]) + s["not_wrappers"])
        self.assertEqual((s["check_py_count"], s["chains"], s["replacements"]), (0, 0, 0))
        self.assertEqual(inv["batches"], [])


if __name__ == "__main__":
    unittest.main()
