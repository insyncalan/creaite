"""#370 (C1): a page error names where it came from, as the top stack frame's function and line, and nothing else.

Run: python3 dev/tests/test_page_errors_370.py     (needs Node for the frame reader; skipped otherwise)

1. src/core/pageErrors.js under Node: V8 and Firefox-style stacks give function:line; no path, address or message text reaches the
   result; no usable stack gives null (the hook then does what it did before).
2. The page's hooks (src/core/server.js) take the frame for an error and for an unhandled rejection, and fall back to today's values.
3. Mutants: the reader returning the path, or the message, must fail.
"""
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MOD = REPO / "system/templates/dashboard/src/core/pageErrors.js"
SERVER_JS = REPO / "system/templates/dashboard/src/core/server.js"

SCRIPT = """
const f = await import(%s); const out = {};
const v8 = "SyntaxError: \\"[object Object]\\" is not valid JSON\\n    at JSON.parse (<anonymous>)\\n    at loadReview (https://127.0.0.1:8765/app/main.js?x=1:42:17)\\n    at async go (https://127.0.0.1:8765/app/main.js:9:3)";
out.v8 = f.topFrame(v8);
out.v8top = f.topFrame("Error: x\\n    at async reviewLoad (http://127.0.0.1:1/a.js:77:5)");
out.method = f.topFrame("Error: x\\n    at Object.save (http://127.0.0.1:1/a.js:5:1)");
out.anon = f.topFrame("Error: x\\n    at http://127.0.0.1:1/a.js:12:9");
out.ff = f.topFrame("loadReview@http://127.0.0.1:1/a.js:31:11\\ngo@http://127.0.0.1:1/a.js:2:2");
out.msgline = f.topFrame("Error: at secret (C:/Users/alan/Budget.docx:99:9)\\n    at okFn (http://h/a.js:7:1)");
out.none = [f.topFrame(""), f.topFrame(undefined), f.topFrame("Error: only a message"), f.topFrame(42), f.errorFrame("text"), f.errorFrame(null), f.errorFrame({})];
out.err = f.errorFrame({ stack: "Error: m\\n    at pick (http://h/a.js:3:4)" });
out.wild = f.topFrame("Error\\n    at we!rd<name> (http://h/a.js:3:4)");
process.stdout.write(JSON.stringify(out));
"""


def run_node(path=MOD):
    tmp = Path(tempfile.mkdtemp(prefix="pe370"))
    try:
        f = tmp / "pageErrors.mjs"
        f.write_text(Path(path).read_text(encoding="utf-8"), encoding="utf-8")
        r = subprocess.run(["node", "--input-type=module", "-e", SCRIPT % json.dumps(f.as_uri())], capture_output=True, text=True, timeout=60)
        if r.returncode:
            raise RuntimeError(r.stderr[-800:])
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@unittest.skipUnless(shutil.which("node"), "needs Node")
class Frame(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o = run_node()

    def test_the_top_frame_is_function_and_line(self):
        self.assertEqual(self.o["v8top"], {"source": "reviewLoad", "line": 77})
        self.assertEqual(self.o["ff"], {"source": "loadReview", "line": 31})
        self.assertEqual(self.o["method"], {"source": "save", "line": 5})
        self.assertEqual(self.o["anon"], {"source": "anonymous", "line": 12})
        self.assertEqual(self.o["err"], {"source": "pick", "line": 3})

    def test_a_native_frame_without_a_line_is_skipped_to_the_page_frame(self):
        self.assertEqual(self.o["v8"], {"source": "loadReview", "line": 42})

    def test_nothing_but_a_short_name_and_a_number_comes_out(self):
        for k in ("v8", "v8top", "ff", "method", "anon", "err", "wild", "msgline"):
            fr = self.o[k]
            self.assertEqual(sorted(fr), ["line", "source"], k)
            self.assertRegex(fr["source"], r"^[\w$]{1,60}$", k)
            self.assertIsInstance(fr["line"], int, k)
        blob = json.dumps(self.o)
        for bad in ("127.0.0.1", "http", "main.js", "valid JSON", "Budget", "alan", "secret", "Users"):
            self.assertNotIn(bad, blob)

    def test_no_usable_stack_gives_null(self):
        self.assertEqual(self.o["none"], [None] * 7)

    def test_a_message_line_that_looks_like_a_frame_is_not_taken(self):
        self.assertEqual(self.o["msgline"], {"source": "okFn", "line": 7})


@unittest.skipUnless(shutil.which("node"), "needs Node")
class Mutants(unittest.TestCase):
    def _mutant(self, old, new):
        src = MOD.read_text(encoding="utf-8")
        self.assertIn(old, src)
        tmp = Path(tempfile.mkdtemp(prefix="pe370m"))
        try:
            m = tmp / "m.js"
            m.write_text(src.replace(old, new, 1), encoding="utf-8")
            try:
                o = run_node(m)
            except RuntimeError:
                return True
            return not (o["v8"] == {"source": "loadReview", "line": 42} and o["msgline"] == {"source": "okFn", "line": 7}
                        and o["none"] == [None] * 7 and "http" not in json.dumps(o)
                        and re.fullmatch(r"[\w$]+", o["wild"]["source"]) is not None)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_each_mutant_is_caught(self):
        self.assertTrue(self._mutant('return {source:name||"anonymous",line};', 'return {source:t,line};'), "returns the raw frame text")
        self.assertTrue(self._mutant("if(typeof stack!==\"string\") return null;", "if(typeof stack!==\"string\") return {source:\"\",line:0};"), "no stack gives a frame")
        self.assertTrue(self._mutant(".replace(/[^\\w$]/g,\"\")", ""), "keeps odd characters")


class Wired(unittest.TestCase):
    def setUp(self):
        self.js = SERVER_JS.read_text(encoding="utf-8")

    def test_both_hooks_send_the_frame_with_today_s_values_as_the_fallback(self):
        self.assertRegex(self.js, r'import \{ errorFrame \} from "\./pageErrors\.js"')
        self.assertRegex(self.js, r'diagFrame=\(err,source,line\)=>\{ const f=errorFrame\(err\); return f\?\{source:f\.source,line:f\.line\}:\{source,line\}; \}')
        self.assertRegex(self.js, r'"unhandledrejection",e=>\{ const f=diagFrame\(e\.reason,"promise",0\);')
        self.assertRegex(self.js, r'"error",e=>\{ const f=diagFrame\(e\.error,e\.filename,e\.lineno\);')

    def test_the_message_sent_is_still_cut_to_what_the_server_takes(self):
        self.assertIn("message:String(message||\"\").slice(0,300)", self.js)
        self.assertIn("source:String(source||\"\").slice(0,300)", self.js)

    def test_the_candidate_parses_cannot_reject_the_page(self):
        for name in ("panel.js", "settings.js"):
            t = (REPO / "system/templates/dashboard/src" / name).read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"const data=JSON\.parse\(await shared\.VW\.read\(path\)\)", t), name)
            self.assertRegex(t, r"let data; try\{ data=JSON\.parse\(await shared\.VW\.read\(path\)\); \}catch\(e\)\{ return false; \}", name)


if __name__ == "__main__":
    unittest.main()
