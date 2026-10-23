"""#307 fix2: processed.txt lines that are not filed (rejected minutes) are not "Approved this week"; a filed .html record keeps its title."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "system" / "scripts"))
import build_dashboard as bd  # noqa: E402


class FiledRows(unittest.TestCase):
    def test_not_filed_is_skipped_and_html_titled(self):
        self.assertIsNone(bd._filed_row("2026-10-20 | fp:2026-10-20|steering | not filed | 0", {}))
        self.assertIsNone(bd._filed_row("2026-10-20 | fp:2026-10-20|lima | projects/Alpha/transcripts/2026-10-20 Lima.vtt | 0", {}))
        r = bd._filed_row("2026-10-20 | fp:2026-10-20|steering | projects/Alpha/minutes/2026-10-20 Budget review.html | 3", {})
        self.assertEqual((r["title"], r["path"]), ("Budget review", "projects/Alpha/minutes/2026-10-20 Budget review.html"))
        d = bd._filed_row("2026-10-20 | fp:2026-10-20|x | projects/Alpha/minutes/2026-10-20 Kick-off.docx | 1", {})
        self.assertEqual(d["title"], "Kick-off")


if __name__ == "__main__":
    unittest.main()
