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


def run_js(path=JS, fix=None):
    r = subprocess.run(["node", "-e", SCRIPT % (json.dumps(Path(path).as_uri()), json.dumps(json.dumps(FIX if fix is None else fix)))], capture_output=True, text=True, timeout=60)
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
                                
                                ("full-width colon", '.normalize("NFK', '.concat("NFK'),
                                ("name over two lines", "(?:[^${SENT_NL}]*?(?:\\\\r\\\\n|[${SENT_NL}])[ \\\\t]*)?", ""),
                                ("bullet and ISO date", "\\\\d{4}\\\\s*-\\\\s*\\\\d{2}\\\\s*-\\\\s*\\\\d{2}", "\\\\d{9}")):
            got = self.mutant(old, new)
            self.assertFalse(got[SHAPES[shape]][0], shape)


class Generated(unittest.TestCase):
    def test_the_map_is_what_the_generator_writes(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "dev" / "tools"))
        import gen_linktext_confusables as g
        self.assertIsNone(g.stale())


LINES = ["17-10-2026: Chased Sara by email.", "17-10-2026: CHASED SARA BY EMAIL.", "17-10-2026: Emailed Tom by message asking.",
         "17-10-2026: EMAILED TOM BY MESSAGE.", "17-10-2026: Asked Chris by email.", "17-10-2026: ASKED CHRIS BY EMAIL.",
         "17-10-2026: chased sara by email.", "17-10-2026: emailed tom by message.", "17-10-2026: asked chris by email."]


def fuzz_cases():
    """(line) for every confusable of every letter the pattern needs, one at a time, plus seeded random combinations."""
    import random
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "dev" / "tools"))
    import gen_linktext_confusables as g
    tab = g.table()
    out = []
    for to, chars in tab.items():
        for ch in chars:
            for line in LINES:
                if to == "-":
                    out.append(line.replace("-", ch, 1))                     # the date's first hyphen
                else:
                    k = line.find(to, line.index(":"))
                    if k > 0:
                        out.append(line[:k] + ch + line[k + 1:])
    rnd = random.Random(368)
    for _ in range(300):
        line = rnd.choice(LINES)
        cs = list(line)
        for k in rnd.sample(range(line.index(":") + 1, len(line)), 4):
            if cs[k] in tab and tab[cs[k]]:
                cs[k] = rnd.choice(tab[cs[k]])
        out.append("".join(cs))
    return out


@unittest.skipUnless(shutil.which("node"), "needs Node")
class Fuzz(unittest.TestCase):
    cases = None

    @classmethod
    def setUpClass(cls):
        cls.cases = fuzz_cases()

    def test_every_confusable_reads_the_same_in_both(self):
        self.assertGreater(len(self.cases), 500)
        for t, (has, out) in zip(self.cases, run_js(fix=self.cases)):
            self.assertTrue(linktext.sent_has(t), repr(t))                 # Python recognises it (fail closed)
            self.assertEqual(has, True, repr(t))
            self.assertEqual(out, linktext.sent_strip(t), repr(t))

    def test_dropping_one_map_entry_fails_the_fuzz(self):
        src = JS.read_text()
        mp = (JS.parent / "sentConfusables.js").read_text()
        import re
        ran = 0
        for to in ("-", "A", "e", "S"):
            m = re.search(r'"%s": "((?:\\u[0-9a-f]{4})+)"' % re.escape(to), mp)
            if not m:
                continue
            first = m.group(1)[:6]
            tmpm, tmpj = JS.parent / "_mutant_368_map.js", JS.parent / "_mutant_368.js"
            tmpm.write_text(mp.replace(first, "", 1))
            tmpj.write_text(src.replace("./sentConfusables.js", "./_mutant_368_map.js"))
            try:
                got = run_js(tmpj, self.cases)
            finally:
                tmpm.unlink()
                tmpj.unlink()
            ran += 1
            self.assertTrue(any(not has for has, _ in got), "dropping %s's %s was not noticed" % (to, first))
        self.assertGreaterEqual(ran, 3)


if __name__ == "__main__":
    unittest.main()
