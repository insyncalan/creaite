"""#368: the page's sentStrip/sentHas (core/linkText.js) and Python's linktext.sent_strip/sent_has give the same answer on the same fixtures,
so a sent line the Python recognises cannot reach an email body built in the page. Mutants show the cases test each handling.

Run: python3 dev/tests/test_sent_parity_368.py     (quick tier: needs Node, no browser)
"""
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
import linktext  # noqa: E402
from test_sent_shapes_368 import SHAPES, NEGATIVES  # noqa: E402

JS = Path(__file__).resolve().parents[2] / "system" / "templates" / "dashboard" / "src" / "core" / "linkText.js"
EXTRA = ["<p>17-10-2026: Chased Sara by email.</p>", "Waiting\r\n17-10-2026: Chased Sara by email.\r\nNext",
         "<p>Waiting</p><p>17-10-2026: Chased Sara by email.</p>", "Keep this\n- 17-10-2026: Chased Sara by email.\nand this",
         "17-10-2026: Chased​ Sara by em​ail.", "1٧-10-2026: Chased Sara by email.", "", "plain text only"]
FIX = ["Keep this\n" + v + "\nand this" for v in SHAPES.values()] + list(SHAPES.values()) + NEGATIVES + EXTRA
SCRIPT = """import(%s).then(m=>{const f=JSON.parse(%s);console.log(JSON.stringify(f.map(t=>[m.sentHas(t),m.sentStrip(t)])));})"""


def run_js(path=JS):
    r = subprocess.run(["node", "-e", SCRIPT % (json.dumps(Path(path).as_uri()), json.dumps(json.dumps(FIX)))], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


@unittest.skipUnless(shutil.which("node"), "needs Node")
class Parity(unittest.TestCase):
    def test_same_answers(self):
        for t, (has, out) in zip(FIX, run_js()):
            self.assertEqual(has, linktext.sent_has(t), repr(t))
            self.assertEqual(out, linktext.sent_strip(t), repr(t))

    def test_shapes_recognised_and_negatives_not(self):
        got = dict(zip(FIX, run_js()))
        for v in SHAPES.values():
            self.assertTrue(got[v][0], v)
        for v in NEGATIVES:
            self.assertEqual(got[v], [False, v], v)

    def mutant(self, old, new):
        s = JS.read_text()
        self.assertIn(old, s, old)
        tmp = JS.parent / "_mutant_368.js"                   # beside the module, so its imports resolve; removed at once
        tmp.write_text(s.replace(old, new))
        try:
            return dict(zip(FIX, run_js(tmp)))
        finally:
            tmp.unlink()

    def test_mutants_are_caught(self):
        for shape, old, new in (("upper case BY", '"i").test(sentPlain', '"").test(sentPlain'),
                                ("non-breaking hyphens", "[\\u2010-\\u2015", "[\\u0001"),
                                ("full-width colon", '.normalize("NFK', '.concat("NFK'),
                                ("name over two lines", "(?:[^${SENT_NL}]*?(?:\\\\r\\\\n|[${SENT_NL}])[ \\\\t]*)?", ""),
                                ("bullet and ISO date", "\\\\d{4}\\\\s*-\\\\s*\\\\d{2}\\\\s*-\\\\s*\\\\d{2}", "\\\\d{9}")):
            got = self.mutant(old, new)
            self.assertFalse(got[SHAPES[shape]][0], shape)


if __name__ == "__main__":
    unittest.main()
