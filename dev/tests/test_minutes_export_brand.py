"""#303 (v2.6.1): the minutes' HTML and PDF export wear the Word minutes' branding (the template's wordmark, Charcoal and Signal Green,
Calibri, the title block) in one self-contained file; the Internal and Distributed markings stay right; the Word export is unchanged.
Run: python3 dev/tests/test_minutes_export_brand.py      (uses Chrome once, for the PDF)
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_export_internal_mark import MARK, InternalMark, pdf_text, word_text  # noqa: E402
from test_minutes_distributed_leak import FILED  # noqa: E402


class Brand(InternalMark):
    def html(self, version="internal"):
        self.approved("actions", "y")
        return self.export(FILED, "html", version).read_text(encoding="utf-8")

    def test_the_html_carries_the_brand_and_nothing_external(self):
        page = self.html()
        self.assertRegex(page, r'<img class="wordmark" src="data:image/png;base64,[A-Za-z0-9+/=]{1000,}"')
        for brand in ("#1e1f1e", "#91ff01", "#f8f8ff", "Calibri", "Minutes of Meeting", MARK):
            self.assertIn(brand, page)
        self.assertNotRegex(page, r"(?i)https?://|//cdn|@import|url\(\s*[\"']?(?!data:)|<link\b|<script\b|\bsrc=\"(?!data:)")

    def test_the_pdf_is_printed_from_the_branded_page(self):
        self.approved("actions", "y")
        text = pdf_text(self.export(FILED, "pdf"))
        self.assertIn("Minutes of Meeting", text)
        self.assertIn(MARK, text)

    def test_the_distributed_page_is_branded_and_not_internal(self):
        page = self.html("distributed")
        self.assertIn("Minutes of Meeting", page)
        self.assertIn("data:image/png;base64,", page)
        self.assertIn("Distributed", page)
        self.assertNotIn("Internal", re.sub(r"<style>.*?</style>", "", page, flags=re.S))

    def test_word_is_unchanged(self):
        self.approved("actions", "y")
        text = word_text(self.export(FILED, "docx"))
        self.assertIn(MARK, text)
        self.assertIn("Minutes of Meeting", text)


if __name__ == "__main__":
    unittest.main()
