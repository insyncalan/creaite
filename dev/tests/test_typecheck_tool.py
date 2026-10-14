"""BL-231 step 3: dev/tools/typecheck.py reads tsc's output and says how to get Node.

Run: python3 dev/tests/test_typecheck_tool.py     (quick tier: no Chrome, no vault, no Node, no network)
"""
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import typecheck  # noqa: E402

OUTPUT = """scratch-split/dashboard.js(12,5): error TS2304: Cannot find name 'foo'.
scratch-split/dashboard.js(40,1): error TS2339: Property 'x' does not exist on type 'Window'.
scratch-split/dashboard.js(41,9): error TS2304: Cannot find name 'bar'.
  This line is a continuation and is not an error.
Found 3 errors in the same file, starting at: scratch-split/dashboard.js:12
"""
class Parsing(unittest.TestCase):
    def test_errors_are_read_with_their_codes(self):
        errors = typecheck.parse(OUTPUT)
        self.assertEqual([e[2] for e in errors], ["TS2304", "TS2339", "TS2304"])
        self.assertEqual(errors[0][:2], ("scratch-split/dashboard.js", 12))

    def test_summary_counts_by_code_most_frequent_first(self):
        lines = typecheck.summary(typecheck.parse(OUTPUT))
        self.assertEqual(lines[0], "typecheck: 3 type errors")
        self.assertEqual([ln.split() for ln in lines[1:]], [["TS2304", "2"], ["TS2339", "1"]])

    def test_clean_output_is_zero(self):
        self.assertEqual(typecheck.summary(typecheck.parse("")), ["typecheck: 0 type errors"])


class NoNode(unittest.TestCase):
    def test_npx_is_not_found_in_empty_folders(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(typecheck.find_npx(path=d, extra=()))

    def test_without_node_it_says_how_to_install_and_fails(self):
        buf = io.StringIO()
        with mock.patch.object(typecheck, "find_npx", return_value=None), redirect_stdout(buf):
            code = typecheck.main([])
        self.assertNotEqual(code, 0)
        self.assertIn("darwin-arm64.tar.gz", buf.getvalue())
        self.assertIn("SHASUMS256.txt", buf.getvalue())
        self.assertIn("development only", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
