"""BL-231: split_dashboard.py's split is a move, not a rewrite (joining the pieces gives back the same bytes), and the
committed dashboard.html is the page its source in system/templates/dashboard/ builds: since step 2b, the shell, the CSS
and the app script bundled from src/ by the pinned esbuild (dev/tools/build_dashboard_js.py). The build is reproducible,
and a stale page is caught.

Run: python3 dev/tests/test_dashboard_split.py     (quick tier: no Chrome, no vault; writes only to a temp dir)
"""
import io
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import build_dashboard_js as bj  # noqa: E402
import convert_area  # noqa: E402
import split_dashboard as sd  # noqa: E402

REAL = sd.PAGE

SCRIPT = (
    "/* ===== first ===== */ at the very start\n"
    "const a = '</scr' + 'ipt>';  \n"
    "const b = \"<\\/script>\";\t\n"
    "  /* ===== indented, never cuts ===== */\n"
    "/* ===== Outer (BL-1) ===== */\n"
    "outer();\n"
    "/* ===== Inner (BL-2) ===== */\n"
    "inner();\n"
    "/* ===== end BL-2 ===== */\n"
    "outerAgain();\n"
    "/* ===== end BL-1 ===== */\n"
    "\n"
    "/* ======================= section ======================= */\n"
    "last(); /* ===== mid-line, never cuts ===== */"
)
PAGE = ('<!doctype html>\n<script type="application/json" id="data"><style>not css</style></script>\n'
        "<style>\n:root{--a:1}   \n</style>\n<body></body>\n<script>" + SCRIPT + "</script>\n</html>")


class Split(unittest.TestCase):
    def roundtrip(self, html):
        """Split `html` into a temp dir, join it from there, and return (pieces, the joined text)."""
        pieces = sd.split(html)
        self.assertEqual(sd.join(pieces), html)
        with tempfile.TemporaryDirectory() as tmp:
            sd.write_pieces(pieces, Path(tmp))
            return pieces, sd.join(sd.read_pieces(Path(tmp)))

    def test_real_dashboard_joins_byte_for_byte(self):
        original = REAL.read_bytes()
        pieces, joined = self.roundtrip(original.decode("utf-8"))
        self.assertEqual(joined.encode("utf-8"), original)
        self.assertEqual(len(pieces["script"]), 1, "the bundle has no block markers (esbuild drops comments): one piece")
        self.assertIn(":root", pieces["css"])
        self.assertIn(sd.CSS_SLOT, pieces["shell"])
        self.assertIn(sd.SCRIPT_SLOT, pieces["shell"])
        self.assertIn('type="application/json"', pieces["shell"], "the data block stays in the shell")

    def test_synthetic_page_cuts(self):
        pieces, joined = self.roundtrip(PAGE)
        self.assertEqual(joined, PAGE)
        self.assertEqual(pieces["css"], "\n:root{--a:1}   \n")
        self.assertNotIn("not css", pieces["css"], "a <style> inside the JSON block is not the CSS")
        names = [n for n, _ in pieces["script"]]
        self.assertEqual(names, ["0001-first.js", "0002-outer-bl-1.js", "0003-inner-bl-2.js", "0004-after-bl-2.js",
                                 "0005-section.js"])
        text = dict(pieces["script"])
        self.assertTrue(text["0001-first.js"].endswith("  /* ===== indented, never cuts ===== */\n"))
        self.assertTrue(text["0003-inner-bl-2.js"].endswith("/* ===== end BL-2 ===== */\n"))
        self.assertTrue(text["0004-after-bl-2.js"].startswith("outerAgain();"))
        self.assertTrue(text["0004-after-bl-2.js"].endswith("/* ===== end BL-1 ===== */\n\n"),
                        "blank lines after an end marker stay with the block")
        self.assertTrue(text["0005-section.js"].endswith("never cuts ===== */"), "no newline is added at the end")

    def test_crlf_and_no_trailing_newline(self):
        html = PAGE.replace("\n", "\r\n").rstrip("\n").rstrip("\r")
        self.assertFalse(html.endswith("\n"))
        pieces, joined = self.roundtrip(html)
        self.assertEqual(joined.encode("utf-8"), html.encode("utf-8"))
        self.assertTrue(all(t.endswith("\r\n") for _, t in pieces["script"][:-1]), "cuts fall after the whole CRLF")

    def test_text_before_the_first_marker_is_its_own_piece(self):
        html = PAGE.replace("<script>/*", "<script>\n// preamble\n/*")
        pieces, joined = self.roundtrip(html)
        self.assertEqual(joined, html)
        self.assertEqual(pieces["script"][0], ("0001-start.js", "\n// preamble\n"))

    def test_a_page_holding_a_slot_is_refused(self):
        with self.assertRaises(ValueError):
            sd.split(PAGE.replace(":root", sd.CSS_SLOT))

    def test_cli_split_join_and_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            page, out = Path(tmp) / "page.html", Path(tmp) / "split"
            page.write_bytes(PAGE.replace("\n", "\r\n").encode("utf-8"))
            with redirect_stdout(io.StringIO()):
                self.assertEqual(sd.main(["split", "--file", str(page), "--out", str(out)]), 0)
                self.assertEqual(sd.main(["join", "--dir", str(out)]), 0)
                self.assertEqual(sd.main(["check", "--file", str(page)]), 0)
            self.assertEqual((out / "dashboard.html").read_bytes(), page.read_bytes())
            self.assertTrue((out / "manifest.json").is_file())


class Source(unittest.TestCase):
    """dashboard.html is built from system/templates/dashboard/ (step 2a), its script from ES modules (step 2b)."""

    def test_committed_page_is_up_to_date(self):
        self.assertEqual(sd.built(), REAL.read_bytes(), f"dashboard.html is stale; rebuild it with: {sd.REBUILD}")
        self.assertEqual(sd.stale(), "")

    def test_the_build_is_reproducible_wherever_the_source_is(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "elsewhere" / "dashboard"
            shutil.copytree(sd.SRC, src)
            shutil.copytree(sd.SRC.parent / "vendor" / "preact", src.parent / "vendor" / "preact")   # BL-256: beside it, as in templates/
            shutil.copytree(sd.SRC.parent / "vendor" / "tiptap", src.parent / "vendor" / "tiptap")   # BL-301 A: and the one editor's
            self.assertEqual(sd.built(src), REAL.read_bytes(), "the same source built in another folder gives other bytes")
        self.assertEqual(sd.built(), sd.built(), "two builds of the same source differ")

    def test_the_script_is_the_bundle_alone(self):
        script = bj.script()
        self.assertTrue(script.startswith(f"var {bj.GLOBAL_NAME} = (() => {{"), "the bundle is one IIFE")
        self.assertEqual(script.count(f"var {bj.GLOBAL_NAME} = "), 1)
        self.assertTrue(script.rstrip().endswith("})();"), "nothing follows it (script/ and its prologue are gone)")
        self.assertFalse((sd.SRC / "script").exists())
        self.assertIn(script, sd.built().decode("utf-8"))

    def test_every_module_imports_what_it_uses(self):
        """Another module's name used without an import would be a ReferenceError: nothing puts the modules' names in
        the page's scope any more (only the ones on window on purpose, core/globals.js)."""
        for path in bj.module_files():
            js = path.read_text(encoding="utf-8")
            need = set()
            for line in bj.imports_for(path):
                need |= set(bj.WORD.findall(line.split("{", 1)[1].split("}", 1)[0]))
            self.assertEqual(need - bj.imported(js), set(),
                             f"{path.name} uses another module's names without importing them: "
                             f"{bj.REBUILD_IMPORTS} {path.relative_to(sd.REPO)}")

    def test_no_module_reads_another_s_value_before_it_runs(self):
        """esbuild runs the modules in the order their imports reach them, not today's; a module that read another's
        `const` while loading, before that one ran, would get undefined."""
        self.assertEqual(bj.load_order_problems(), [])
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "dashboard"
            shutil.copytree(sd.SRC, src)
            order = bj.eval_order(src)
            texts = bj.analysis_sources(src)                    # BL-256: a component's JSX as calls, for the lexer
            order = [m for m in order if m in texts]            # the vendored library isn't the page's own source
            exports = {m: bj.top_level(texts[m], exported=True) for m in order}
            early, name = next((m, n) for i, m in enumerate(order) for n in sorted(bj.imported(texts[m]))
                               if any(exports[o].get(n, "function") != "function" for o in order[i + 1:]))
            f = src / "src" / early
            f.write_text(f.read_text(encoding="utf-8") + f"\nexport const TOO_EARLY = {name};\n", encoding="utf-8")
            self.assertEqual(len(bj.load_order_problems(src)), 1, "the check finds a read made too early")

    def test_the_load_time_steps_run_from_main_in_today_s_order(self):
        """Each boot…() a module exports is called once, by main.js, after publish(); the start-up is among them."""
        main = (sd.SRC / "src" / "main.js").read_text(encoding="utf-8")
        boots = sorted(n for p in bj.module_files() for n in bj.top_level(p.read_text(encoding="utf-8"), exported=True)
                       if n.startswith("boot"))
        tail = main.split("publish(page);", 1)[1]
        self.assertTrue(boots)
        for n in boots:
            self.assertEqual(tail.count(f"\n{n}();"), 1, f"{n} is called once, after publish()")
        calls = [ln for ln in tail.split("\n") if ln.startswith("boot")]
        nums = [ln[-7:-3] for ln in calls if ln[-7:-3].isdigit()]
        self.assertEqual(nums, sorted(nums), "the areas' steps in their pieces' order (today's)")
        self.assertIn("\nshared.LOADING=false;\n", tail, "the start-up (piece 0151) is there")

    def test_the_globals_tests_list_is_complete(self):
        """Every page name a test uses is listed (an extra one is harmless: publish() skips names no module exports,
        so converting an area never has to edit the list)."""
        missing = set(bj.test_names()) - set(bj.globals_json()["names"]["tests"])
        self.assertEqual(missing, set(), "src/core/globals.json's `tests` list is missing names a test uses: "
                                         "python3 dev/tools/build_dashboard_js.py globals")

    def test_stale_page_names_the_rebuild_and_build_fixes_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, page = Path(tmp) / "dashboard", Path(tmp) / "dashboard.html"
            shutil.copytree(sd.SRC, src)
            page.write_bytes(sd.built(src))
            self.assertEqual(sd.stale(src, page), "")
            edits = [(src / "style.css", "/* edited */\n", b"/* edited */"),
                     (src / "src" / "core" / "dom.js", "export const editedInTest = 1;\n", b"editedInTest"),
                     (src / "src" / "files.js", "export const editedInFiles = 2;\n", b"editedInFiles")]
            for f, add, mark in edits:
                f.write_bytes(f.read_bytes() + add.encode())
                self.assertIn(sd.REBUILD, sd.stale(src, page), f.name)
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(sd.cmd_build(src, page), 0)
                self.assertIn(mark, page.read_bytes(), f"build writes the edited {f.name} into the page")
                self.assertEqual(sd.stale(src, page), "")

    def test_convert_area_moves_pieces_into_a_module(self):
        """dev/tools/convert_area.py (the recipe in dev/archive/notes/v1.8.0/V18-MODULES-PLAN.md), on a copy: a made-up area's two pieces
        (every real area is converted), one with a load-time step, a shared `let` and a seam, one with neither."""
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "dashboard"
            shutil.copytree(sd.SRC, src)
            (src / "script").mkdir(exist_ok=True)
            one, two = src / "script" / "9998-made-up.js", src / "script" / "9999-made-up-too.js"
            one.write_text('/* ===== Made up ===== */\nlet FSEL={p:"All"}, MADEUP=1;\nfunction send(t){ return t+FSEL.p; }\n'
                           'document.addEventListener("click",()=>{ FSEL={p:"x"}; });\n', encoding="utf-8")
            two.write_text('/* ===== Made up too ===== */\nfunction madeUpToo(){ return FSEL; }\n', encoding="utf-8")
            main = src / "src" / "main.js"
            main.write_text(main.read_text(encoding="utf-8").replace("publish(page);", '// export * from "./madeup.js";\n\npublish(page);'),
                            encoding="utf-8")
            p = convert_area.plan("madeup", ["9998", "9999"], src)
            self.assertEqual(p["notes"], [])
            self.assertTrue(convert_area.write(p, src))
            module = (src / "src" / "madeup.js").read_text(encoding="utf-8")
            self.assertIn("export let MADEUP=1; shared.FSEL={", module, "a `let` another area uses becomes shared state")
            self.assertIn("return shared.FSEL; }", module)
            self.assertIn('import { shared } from "./core/state.js";', module)
            self.assertIn("export let send = function(t){", module, "a seam is a `let`")
            self.assertIn("export const madeupSeams = { send: v => { send = v; } };", module, "with its setter")
            self.assertIn("export function bootMadeup9998(){", module)
            self.assertTrue(one.read_text(encoding="utf-8").endswith("\nbootMadeup9998();\n"), "the stub calls it")
            self.assertFalse(two.exists(), "a piece with no load-time steps is deleted")
            self.assertIn('\nexport * from "./madeup.js";\n', main.read_text(encoding="utf-8"))

    def test_a_module_esbuild_refuses_fails_the_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "dashboard"
            shutil.copytree(sd.SRC, src)
            (src / "src" / "main.js").write_text('import { nothing } from "./core/no-such-module.js";\n', encoding="utf-8")
            with self.assertRaises(bj.BuildError):
                sd.built(src)


if __name__ == "__main__":
    unittest.main()
