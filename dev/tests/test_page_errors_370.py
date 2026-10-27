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
out.review = f.topFrame("Error: Couldn't save\\nmia.hale@client.example:12:3\\n    at okFn (http://h/a.js:7:1)");
out.fname = f.topFrame("Error: x\\n    at Projects.Brightwater_Takeover (http://h/a.js:8:1)");
out.nomsgframe = f.topFrame("Error: Couldn't save\\nmia.hale@client.example:12:3");
out.ffmsg = f.topFrame("hale@client.example:12:3");
out.bound = [f.topFrame("Error\\n    at big (http://h/a.js:9999999:1)"), f.topFrame("Error\\n    at huge (http://h/a.js:10000000:1)\\n    at next (http://h/a.js:4:1)")];
out.rej = f.rejectionReport({ reason: { message: "boom", stack: "Error: boom\\n    at doIt (http://h/a.js:21:5)" } });
out.rejPlain = [f.rejectionReport({ reason: "text only" }), f.rejectionReport({ reason: null }), f.rejectionReport({})];
out.errRep = [f.errorReport({ message: "m", error: { stack: "Error: m\\n    at pick (http://h/a.js:3:4)" }, filename: "http://h/a.js", lineno: 9 }),
  f.errorReport({ message: "m2", error: null, filename: "a.js", lineno: 9 })];
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

    def test_the_review_example_gives_the_function_not_a_name_from_the_message(self):
        self.assertEqual(self.o["review"], {"source": "okFn", "line": 7})
        self.assertEqual(self.o["fname"], {"source": "Brightwater_Takeover", "line": 8})      # a function's own name is the frame, by design
        self.assertNotIn("hale", json.dumps(self.o["review"]))

    def test_a_v8_message_with_no_frame_gives_nothing_but_firefox_style_still_parses(self):
        self.assertIsNone(self.o["nomsgframe"])                                    # "Error: ..." and no "at" line: only a message
        self.assertEqual(self.o["ffmsg"], {"source": "hale", "line": 12})

    def test_the_line_number_has_an_upper_bound(self):
        self.assertEqual(self.o["bound"][0], {"source": "big", "line": 9999999})
        self.assertEqual(self.o["bound"][1], {"source": "next", "line": 4})        # 10000000 is not a line: the next frame is read

    def test_the_rejection_report_carries_the_frame_not_promise_and_zero(self):
        self.assertEqual(self.o["rej"], {"message": "boom", "source": "doIt", "line": 21})
        self.assertEqual(self.o["rejPlain"][0], {"message": "text only", "source": "promise", "line": 0})
        self.assertEqual(self.o["rejPlain"][1], {"message": None, "source": "promise", "line": 0})
        self.assertEqual(self.o["rejPlain"][2], {"source": "promise", "line": 0})        # no message: undefined, dropped by JSON

    def test_the_error_report_carries_the_frame_else_the_browsers_own_values(self):
        self.assertEqual(self.o["errRep"][0], {"message": "m", "source": "pick", "line": 3})
        self.assertEqual(self.o["errRep"][1], {"message": "m2", "source": "a.js", "line": 9})

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
                        and o["review"] == {"source": "okFn", "line": 7} and o["nomsgframe"] is None and o["bound"][1] == {"source": "next", "line": 4}
                        and o["rej"] == {"message": "boom", "source": "doIt", "line": 21}
                        and o["errRep"][0] == {"message": "m", "source": "pick", "line": 3}
                        and o["none"] == [None] * 7 and "http" not in json.dumps(o)
                        and re.fullmatch(r"[\w$]+", o["wild"]["source"]) is not None)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_each_mutant_is_caught(self):
        self.assertTrue(self._mutant('return {source:name||"anonymous",line};', 'return {source:t,line};'), "returns the raw frame text")
        self.assertTrue(self._mutant("if(typeof stack!==\"string\") return null;", "if(typeof stack!==\"string\") return {source:\"\",line:0};"), "no stack gives a frame")
        self.assertTrue(self._mutant(".replace(/[^\\w$]/g,\"\")", ""), "keeps odd characters")
        self.assertTrue(self._mutant("if(first>0) lines=lines.slice(first);", ""), "reads message lines as frames")
        self.assertTrue(self._mutant("else if(first<0&&", "else if(false&&"), "reads a frameless V8 message as a stack")
        self.assertTrue(self._mutant("||line>9999999", ""), "no upper bound on the line")
        self.assertTrue(self._mutant("const r=e&&e.reason, f=withFrame(r,\"promise\",0);\n  return {message:r&&r.message?r.message:r,source:f.source,line:f.line};",
                                     "const r=e&&e.reason, f=withFrame(r,\"promise\",0);\n  return {message:r&&r.message?r.message:r,source:\"promise\",line:0};"), "the rejection frame is computed and dropped")
        self.assertTrue(self._mutant("return {message:e&&e.message,source:f.source,line:f.line};", "return {message:e&&e.message,source:e&&e.filename,line:e&&e.lineno};"), "the error frame is computed and dropped")


class Wired(unittest.TestCase):
    def setUp(self):
        self.js = SERVER_JS.read_text(encoding="utf-8")

    def test_both_hooks_post_what_the_report_computed(self):
        self.assertRegex(self.js, r'import \{ errorReport, rejectionReport \} from "\./pageErrors\.js"')
        self.assertRegex(self.js, r'"error",e=>\{ const r=errorReport\(e\); diagHook\(r\.message,r\.source,r\.line\); \}\)')
        self.assertRegex(self.js, r'"unhandledrejection",e=>\{ const r=rejectionReport\(e\); diagHook\(r\.message,r\.source,r\.line\); \}\)')
        self.assertNotIn('"promise",0', self.js)           # the fallback lives in pageErrors.js, where it is tested

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
