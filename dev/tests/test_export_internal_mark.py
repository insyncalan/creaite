"""v2.6.1: an internal export (Word, HTML, PDF) is visibly marked "Internal, not for distribution"; the distributed export says
Distributed and is not marked internal.
Run: python3 dev/tests/test_export_internal_mark.py      (quick tier: no Chrome)
"""
import os
import re
import sys
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_minutes_distributed_leak import DRAFT, FILED, Sensitive as _Base  # noqa: E402

MARK = "Internal, not for distribution"


def pdf_text(path):
    """A PDF's text, read with the bundled pypdf."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../system/scripts/vendor"))
    import pypdf
    return " ".join(p.extract_text() for p in pypdf.PdfReader(str(path)).pages)


def word_text(path):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")))


class InternalMark(_Base):
    def export(self, path, fmt, version="internal"):
        r = self.js("import minutes_record\n"
                    f"print(json.dumps(minutes_record.export({path!r}, {fmt!r}, False, {version!r})))")
        return self.v.root / r["path"]

    def test_a_draft_and_filed_internal_export_say_internal_in_word_html_and_pdf(self):
        for stage in ("draft", "filed"):
            if stage == "filed":
                self.approved("actions", "y")
            path = DRAFT if stage == "draft" else FILED
            with self.subTest(stage=stage):
                self.assertIn(MARK, word_text(self.export(path, "docx")), "Word")
                self.assertIn(MARK, self.export(path, "html").read_text(encoding="utf-8"), "HTML")
                self.assertIn(MARK, pdf_text(self.export(path, "pdf")), "PDF")

    def test_the_distributed_export_says_distributed_and_is_not_marked_internal(self):
        self.approved("actions", "y")
        for fmt in ("docx", "html", "pdf"):
            p = self.export(FILED, fmt, "distributed")
            text = word_text(p) if fmt == "docx" else p.read_text(encoding="utf-8") if fmt == "html" else pdf_text(p)
            with self.subTest(fmt=fmt):
                self.assertIn("Distributed", text)
                self.assertNotIn("Internal", text)


if __name__ == "__main__":
    unittest.main()
