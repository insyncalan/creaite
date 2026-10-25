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
         "17-10-2026: Chased​ Sara by em​ail.", "1٧-10-2026: Chased Sara by email.", "", "plain text only",
         # review M1: character references in HTML
         "<p>17-10-2026: Chased Sara by&#32;email.</p>", "<p>17-10-2026: Chased Sara by&#x20;email.</p>", "<p>17-10-2026&#58; Chased Sara by email.</p>",
         "<p>17-10-2026&colon; Chased Sara by&nbsp;email.</p>", "<p>17-10-2026: Chased Sara b&#121; &#101;mail.</p>", "<p>Fish &amp; chips &lt;b&gt;</p>",
         # re-review: invisible named references inside the date or a word, with a tag present
         "<p>17-10-2026&shy;: Chased Sara by email.</p>", "<p>17-10-2026&zwj;: Chased Sara by email.</p>", "<p>17-10-2026&NoBreak;: Chased Sara by email.</p>",
         "<p>17-10-2026: Chased Sara by em&ZeroWidthSpace;ail.</p>", "<p>17-10-2026: Cha&lrm;sed Sara by email.</p>", "<p>17-10-2026: Chased Sara &InvisibleTimes;by email.</p>",
         # review M2: the rest keeps its own characters
         "Caf\u00e9 r\u00e9sum\u00e9 \u0928\u092e\u0938\u094d\u0924\u0947 \u0391\u0392\u0393 \u041f\u0440\u0438\u0432\u0435\u0442\n17-10-2026: Chased Sara by email.\nCaf\u00e9 again",
         "Caf\u00e9 \u041f\u0440\u0438\u0432\u0435\u0442. 17-10-2026: Chased Sara by email.",
         "<p>Caf\u00e9 \u0928\u092e\u0938\u094d\u0924\u0947</p><p>17-10-2026: Chased Sara by email.</p>"]
FIX = ["Keep this\n" + v + "\nand this" for v in SHAPES.values()] + list(SHAPES.values()) + NEGATIVES + EXTRA
SCRIPT = """import(%s).then(m=>{const f=JSON.parse(require('fs').readFileSync(0,'utf8'));console.log(JSON.stringify(f.map(t=>[m.sentHas(t),m.sentStrip(t)])));})"""


def run_js(path=JS, fix=None):
    r = subprocess.run(["node", "-e", SCRIPT % json.dumps(Path(path).as_uri())], input=json.dumps(FIX if fix is None else fix), capture_output=True, text=True, timeout=60)
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

    def mutant(self, old, new, fix=None):
        s = JS.read_text()
        self.assertIn(old, s, old)
        tmp = JS.parent / "_mutant_368.js"                   # beside the module, so its imports resolve; removed at once
        tmp.write_text(s.replace(old, new))
        try:
            return dict(zip(FIX if fix is None else fix, run_js(tmp, fix)))
        finally:
            tmp.unlink()

    def test_mutants_are_caught(self):
        for shape, old, new in (("upper case BY", 'new RegExp(SENT_SRC, "i")', 'new RegExp(SENT_SRC, "")'),
                                ("full-width colon", '.normalize("NFK', '.concat("NFK'),
                                ("name over two lines", "const SENT_NAME_BREAK = `", "const SENT_NAME_BREAK = ``; const _unused = `"),
                                ("bullet and ISO date", "|\\\\d{4}", "|\\\\d{9}")):
            got = self.mutant(old, new)
            self.assertFalse(got[SHAPES[shape]][0], shape)

    def test_entity_mutant_is_caught(self):
        got = self.mutant("(_, s) => sentRef(s)", '(_, s) => "&" + s')
        for t in ("<p>17-10-2026: Chased Sara by&#32;email.</p>", "<p>17-10-2026&#58; Chased Sara by email.</p>"):
            self.assertFalse(got[t][0], t)

    def test_rest_of_the_field_keeps_its_characters(self):
        want = "Caf\u00e9 r\u00e9sum\u00e9 \u0928\u092e\u0938\u094d\u0924\u0947 \u0391\u0392\u0393 \u041f\u0440\u0438\u0432\u0435\u0442"
        t = want + "\n17-10-2026: Chased Sara by email.\nCaf\u00e9 again"
        self.assertEqual(linktext.sent_strip(t), want + "\nCaf\u00e9 again")
        self.assertEqual(dict(zip(FIX, run_js()))[t][1], want + "\nCaf\u00e9 again")
        got = self.mutant("const plain = sentPlain(text), { form, at } = sentMap(plain);", "const plain = sentMap(sentPlain(text)).form, { form, at } = sentMap(plain);")
        self.assertNotEqual(got[t][1], want + "\nCaf\u00e9 again", "rewriting the field in its normalised form must be seen")

    def test_numeric_references_decode_as_python_does(self):
        import hashlib
        import html
        parts = []
        for n in range(0x110000):
            parts.append(html.unescape("&#%d;" % n) + html.unescape("&#x%X;" % n) + (html.unescape("&#%d" % n) if n % 7 == 0 else ""))
        want = hashlib.sha256("\x01".join(parts).encode("utf-8")).hexdigest()
        script = """import(%s).then(m=>{const c=require('crypto');const p=[];for(let n=0;n<0x110000;n++){p.push(m.sentUnescape('&#'+n+';')+m.sentUnescape('&#x'+n.toString(16).toUpperCase()+';')+(n%%7===0?m.sentUnescape('&#'+n):''));}
console.log(c.createHash('sha256').update(Buffer.from(p.join('\\x01'),'utf8')).digest('hex'));})"""
        r = subprocess.run(["node", "-e", script % json.dumps(JS.as_uri())], capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr[-400:])
        self.assertEqual(r.stdout.strip(), want)

    def test_named_references_decode_as_python_does(self):
        import html
        import html.entities
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "dev" / "tools"))
        import gen_linktext_confusables as g
        named = g.entities()[0]
        self.assertGreater(len(named), 200)
        names = sorted(n for n in named if n.endswith(";"))
        texts = ["&%s" % n for n in names] + ["&%sx" % n[:-1] for n in names if n[:-1] in named]
        script = """import(%s).then(m=>{console.log(JSON.stringify(JSON.parse(require('fs').readFileSync(0,'utf8')).map(t=>m.sentUnescape(t))));})"""
        r = subprocess.run(["node", "-e", script % json.dumps(JS.as_uri())], input=json.dumps(texts), capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-400:])
        for t, got in zip(texts, json.loads(r.stdout)):
            self.assertEqual(got, html.unescape(t), t)


INVISIBLE_ROWS = ["<p>17-10-2026&shy;: Chased Sara by email.</p>", "<p>17-10-2026&zwj;: Chased Sara by email.</p>",
                  "<p>17-10-2026&NoBreak;: Chased Sara by email.</p>", "<p>17-10-2026: Chased Sara by em&ZeroWidthSpace;ail.</p>",
                  "<p>17-10-2026: Cha&lrm;sed Sara by email.</p>", "<p>17-10-2026: Chased Sara by&InvisibleTimes; email.</p>"]


@unittest.skipUnless(shutil.which("node"), "needs Node")
class InvisibleReferences(unittest.TestCase):
    def names(self):
        import html.entities
        import edit_ai
        return sorted(n for n, v in html.entities.html5.items() if n.endswith(";") and edit_ai.normal(v) == "")

    def test_every_invisible_name_is_in_the_page_table(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "dev" / "tools"))
        import gen_linktext_confusables as g
        names = self.names()
        self.assertGreater(len(names), 5)
        for n in ("shy;", "zwj;", "NoBreak;", "ZeroWidthSpace;", "lrm;", "InvisibleTimes;"):
            self.assertIn(n, names)
        self.assertEqual([n for n in names if n not in g.entities()[0]], [])

    def lines(self):
        import random
        rnd, out = random.Random(368), []
        base = "<p>17-10-2026: Chased Sara by email.</p>"
        for n in self.names():
            cut = rnd.randrange(len("<p>"), len(base) - len("</p>"))
            out.append(base[:cut] + "&" + n + base[cut:])
        return INVISIBLE_ROWS + out

    def test_both_sides_agree_and_recognise(self):
        lines = self.lines()
        for t, (has, out) in zip(lines, run_js(fix=lines)):
            self.assertTrue(linktext.sent_has(t), repr(t))
            self.assertEqual((has, out), (True, linktext.sent_strip(t)), repr(t))

    def test_dropping_an_invisible_name_is_caught(self):
        ent = JS.parent / "sentEntities.js"
        src = ent.read_text()
        self.assertIn('"shy;"', src)
        tmpe, tmpj = JS.parent / "_mutant_368_ent.js", JS.parent / "_mutant_368.js"
        tmpe.write_text(src.replace('"shy;"', '"shyX;"'))
        tmpj.write_text(JS.read_text().replace("./sentEntities.js", "./_mutant_368_ent.js"))
        try:
            got = dict(zip(INVISIBLE_ROWS, run_js(tmpj, INVISIBLE_ROWS)))
        finally:
            tmpe.unlink()
            tmpj.unlink()
        self.assertFalse(got[INVISIBLE_ROWS[0]][0])


class Timing(unittest.TestCase):
    """Review LOW 4: a long text is read in linear time (a time limit, both sides)."""
    BIG = ["17-10-2026: chased " * 55000, "17-10-2026: chased\n" * 55000, "x" * 1000000, " " * 1000000, "12 " * 330000,
           "17-10-2026: Asked " + "a" * 1000000]

    def test_python(self):
        import time
        for t in self.BIG:
            t0 = time.time()
            linktext.sent_has(t)
            linktext.sent_strip(t)
            self.assertLess(time.time() - t0, 6, repr(t[:30]))

    @unittest.skipUnless(shutil.which("node"), "needs Node")
    def test_js(self):
        import time
        t0 = time.time()
        script = """import(%s).then(m=>{const t=["17-10-2026: chased ".repeat(55000),"17-10-2026: chased\\n".repeat(55000),"x".repeat(1e6)," ".repeat(1e6),"12 ".repeat(330000),"17-10-2026: Asked "+"a".repeat(1e6)];for(const x of t){m.sentHas(x);m.sentStrip(x);}console.log('ok');})"""
        r = subprocess.run(["node", "-e", script % json.dumps(JS.as_uri())], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.stdout.strip(), "ok", r.stderr[-300:])
        self.assertLess(time.time() - t0, 30)

    @unittest.skipUnless(shutil.which("node"), "needs Node")
    def test_dropping_the_bound_is_caught(self):
        tmp = JS.parent / "_mutant_368.js"
        tmp.write_text(JS.read_text().replace("const SENT_SPAN = 400;", "const SENT_SPAN = 1000000000;"))
        script = """import(%s).then(m=>{m.sentHas("17-10-2026: chased ".repeat(55000));console.log('ok');})"""
        try:
            with self.assertRaises(subprocess.TimeoutExpired):
                subprocess.run(["node", "-e", script % json.dumps(tmp.as_uri())], capture_output=True, text=True, timeout=20)
        finally:
            tmp.unlink()

    def test_real_lines_still_match_inside_the_bound(self):
        self.assertTrue(linktext.sent_has("17-10-2026: Chased " + "N" * 300 + " by email."))
        self.assertTrue(linktext.sent_has("17-10-2026: Chased Sara\nExample by email."))


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
