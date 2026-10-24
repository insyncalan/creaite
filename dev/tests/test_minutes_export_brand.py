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
        self.assertIn("Shareable", page)
        self.assertNotIn("Internal", re.sub(r"<style>.*?</style>", "", page, flags=re.S))

    def test_word_html_and_pdf_use_the_same_tokens(self):
        import zipfile
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../system/scripts"))
        import creaite_doc
        z = zipfile.ZipFile(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../system/templates/minutes-template.docx"))
        xml = " ".join(z.read(n).decode("utf-8") for n in ("word/document.xml", "word/styles.xml"))
        page = self.html()
        for name, value in creaite_doc.BRAND.items():
            if name == "LINK":
                continue
            with self.subTest(token=name):
                self.assertTrue(re.search(value, xml, re.I), "Word template lacks " + value)
                self.assertTrue(re.search(value, page, re.I), "HTML lacks " + value)
        self.assertEqual(creaite_doc.BRAND["LINK"], "0563C1")
        self.assertIn("0563C1", xml)

    def test_the_sizes_and_margins_follow_the_word_template(self):
        # Word: 10pt body and table text (13.33px), tables 9350 of 9906 twips wide (94.4%), margins 1000 twips side / 900 top (17.6mm / 15.9mm)
        page = self.html()
        self.assertIn(".brand{font:13.33px", page)
        self.assertIn("font-size:13.33px;width:94.4%", page)
        self.assertIn("margin:15.9mm 17.6mm", page)

    def test_word_is_unchanged(self):
        self.approved("actions", "y")
        text = word_text(self.export(FILED, "docx"))
        self.assertIn(MARK, text)
        self.assertIn("Minutes of Meeting", text)


if __name__ == "__main__":
    unittest.main()
