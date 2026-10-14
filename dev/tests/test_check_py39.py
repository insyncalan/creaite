"""check.py's PY39 rules: what Python 3.9 (creaite's floor, BL-242) lacks and the grammar check can't see.

Run: python3 dev/tests/test_check_py39.py     (quick tier: no Chrome, no vault)
"""
import ast
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import check  # noqa: E402

CAUGHT = {
    "write_text(newline=)": 'p.write_text("x", encoding="utf-8", newline="\\n")',     # transcripts.py before 88eaa65
    "zip(strict=)": "pairs = list(zip(a, b, strict=True))",
    "dataclass(slots=)": "@dataclass(slots=True)\nclass A:\n    x: int = 0",
    "int.bit_count": "n = (7).bit_count()",
    "contextlib.chdir": "import contextlib\nwith contextlib.chdir('x'):\n    pass",
    "datetime.UTC": "import datetime\nnow = datetime.datetime.now(datetime.UTC)",
    "from datetime import UTC": "from datetime import UTC",
    "itertools.pairwise": "import itertools\nfor a, b in itertools.pairwise(xs):\n    pass",
    "tomllib": "import tomllib",
    "anext": "async def f(it):\n    return await anext(it)",
    "X | None in a signature": "def f(x: int | None) -> str:\n    return ''",
    "X | None at module level": "LIMIT: int | None = None",
}
FINE = {
    "os.chdir": "import os\nos.chdir('x')",
    "write_text without newline": 'p.write_text("x", encoding="utf-8")',
    "zip without strict": "pairs = list(zip(a, b))",
    "X | None with the future import": "from __future__ import annotations\ndef f(x: int | None):\n    pass",
    "X | None on a local variable": "def f():\n    x: int | None = None\n    return x",
    "X | Y outside an annotation": "flags = a | b",
    "an f-string with the other quote": "x = f\"{d['k']}\"",
}
FSTRINGS = {                                   # only Python 3.12 accepts these; checked when check.py runs on 3.12+
    "a backslash in the expression": "x = f\"{(re.search(r'`(\\w+)`', y) or [None, ''])[1]}\"",   # check.py's own, 11-10-2026
    "the f-string's own quote": "x = f\"{d[\"k\"]}\"",
}


class Py39(unittest.TestCase):
    def found(self, src):
        return check.py39_api(src, ast.parse(src))

    def test_newer_library_and_language_are_caught(self):
        for name, src in CAUGHT.items():
            with self.subTest(name):
                self.assertTrue(self.found(src), f"{name} should be refused on Python 3.9")

    def test_what_39_has_is_left_alone(self):
        for name, src in FINE.items():
            with self.subTest(name):
                self.assertEqual(self.found(src), [], name)

    @unittest.skipIf(sys.version_info < (3, 12), "these don't parse before 3.12, where SYNTAX catches them")
    def test_312_fstrings_are_caught(self):
        for name, src in FSTRINGS.items():
            with self.subTest(name):
                self.assertTrue(self.found(src), name)


if __name__ == "__main__":
    unittest.main()
