"""check.py's JSDUP: a function declared twice in the dashboard's script fails the check, and (BL-231 step 2b) so does a
top-level name declared in two of its source files. JavaScript hoists the
last declaration over the others, so the first is lost without an error: on 12-10-2026 BL-253's `evOpen` and `evClose`
(the live event stream) silently replaced BL-207's evidence panel, and BL-210's `dnHtml` replaced BL-218's.

Run: python3 dev/tests/test_check_jsdup.py     (quick tier: no Chrome)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import check  # noqa: E402


class Duplicates(unittest.TestCase):
    def test_a_function_declared_twice_is_found_with_its_lines(self):
        js = "function a(){}\nfunction b(){}\nasync function a(){}\n"
        self.assertEqual(check.duplicate_functions(js), {"a": [1, 3]})

    def test_inner_functions_and_wrappers_are_not_duplicates(self):
        js = "function a(){ function inner(){} }\nfunction b(){ function inner(){} }\n{ const g=a; a=function(){ g(); }; }\n"
        self.assertEqual(check.duplicate_functions(js), {})

    def test_it_fails_the_check(self):
        problems = []
        check.js_metrics("function a(){}\nfunction a(){}\n", False, problems)
        self.assertEqual([p[2] for p in problems], ["JSDUP"])

    def test_the_dashboard_has_none(self):
        self.assertEqual(check.duplicate_functions(check.dashboard_js()), {})
        self.assertEqual(check.duplicate_names(check.dashboard_sources()), {})

    def test_an_exported_function_counts(self):
        self.assertEqual(check.duplicate_functions("export function a(){}\nexport async function a(){}\n"), {"a": [1, 2]})

    def test_a_name_declared_in_two_modules_is_found(self):
        """BL-231 step 2b: esbuild renames one of two modules' `a` and `export *` silently drops both from the page's
        names, so a name may be declared in one source file only (a module, or the pieces in script/)."""
        sources = {"src/one.js": "export const a=1;\nexport function b(){}\n",
                   "src/two.js": "export let a=2;\nconst c=3;\n",
                   "script/legacy.js": "function b(){}\nlet d;\n"}
        self.assertEqual(check.duplicate_names(sources), {"a": ["src/one.js", "src/two.js"],
                                                          "b": ["src/one.js", "script/legacy.js"]})
        problems = []
        check.js_metrics("x", False, problems, sources)
        self.assertEqual([p[2] for p in problems], ["JSDUP", "JSDUP"])


if __name__ == "__main__":
    unittest.main()
