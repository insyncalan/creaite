"""H5 / #218: the free-text section of a weekly or client report: what the Python renderer and the Word writer do with it.

Run: python3 dev/tests/test_report_text_section.py

A text section is a section of type "freetext": a heading Alan names and a body of Markdown written by the Notes editor's own writer
(headings, bold, italic, strike, inline and block code, lists, checklists, quotes, links, tables, pictures). These tests cover
  - creaite_doc.render (the filed page and the HTML export): one test per content type, the leak of pasted HTML, the data block;
  - creaite_doc.word_export (the Word writer): one test per content type, read from the .docx's XML;
  - the client rule: a text section of the internal report is never in a client output unless it was matched or written there;
  - a LibreOffice docx -> PDF check that the text comes out in order (skipped, and says so, when soffice is missing).
Pictures are read only from `_images/<name>.png|jpg` in the reports folder (creaite_doc.images_dir), never from another path.
"""
import base64
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_word_export_227 import ITEMS, W, png  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "system" / "scripts"))
import creaite_doc  # noqa: E402
import docx_tools  # noqa: E402
import paths  # noqa: E402

ALL = """# Heading one

## Heading two

### Heading three

Plain words with **bold**, *italic*, ~~struck~~ and `inline_code()` plus a [link text](https://example.com/page?a=1) end.

- bullet one
- bullet two
  - nested bullet

1. first
2. second

- [ ] open task
- [x] done task

> A quoted line

```python
def tidy(x):
    return x  # kept as typed
```

| Name | Role |
|------|------|
| Mia Hale | Sponsor |
| Sam Patel | Lead |

![Site photo](_images/2026-10-18-site.png)
"""


def freetext(text=ALL, heading="Vendor notes", sid="free_1", **more):
    return {"id": sid, "type": "freetext", "heading": heading, "default_heading": "", "hidden": False, "text": text,
            "audience": "internal", **more}


def base_sections(*extra):
    return [
        {"id": "summary", "type": "text", "heading": "Executive summary", "hidden": False, "text": "Before the text section."},
        *extra,
        {"id": "this_week", "type": "text", "heading": "This week", "hidden": False, "text": "After the text section."},
    ]


class Tmp(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="h5-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.images = self.tmp / "_images"
        self.images.mkdir()
        self.photo = png(40, 20, (0, 150, 0, 255))
        (self.images / "2026-10-18-site.png").write_bytes(self.photo)
        old = creaite_doc.images_dir if hasattr(creaite_doc, "images_dir") else None
        creaite_doc.images_dir = lambda doc: self.images.parent
        self.addCleanup(lambda: old is None or setattr(creaite_doc, "images_dir", old))
        self.drafts = self.tmp / "drafts"
        self.drafts.mkdir()
        old_drafts = paths.DRAFTS
        paths.DRAFTS = self.drafts
        self.addCleanup(setattr, paths, "DRAFTS", old_drafts)
        self.pic = getattr(creaite_doc, "picture_png", None)
        creaite_doc.picture_png = lambda svg, w, h, **kw: png(int(w), int(h))
        self.addCleanup(setattr, creaite_doc, "picture_png", self.pic)

    def doc(self, *sections, kind="weekly", audience=None, **kw):
        d = creaite_doc.new(kind, "ABC", "Weekly report" if kind == "weekly" else "Client report", "2026-10-16",
                            list(sections) or base_sections(freetext()), items=ITEMS,
                            **({"audience": audience} if audience else {}), **kw)
        d["project_name"] = "Example Programme"
        return d

    def page(self, doc=None, editing=False):
        return creaite_doc.render(doc or self.doc(), editing=editing)


class HtmlRender(Tmp):
    """creaite_doc.render: the page and the HTML export."""

    def section(self, page):
        return re.search(r'<section data-id="free_1">(.*?)</section>', page, re.S).group(1)

    def test_heading_named_by_alan_and_body_headings_are_headings(self):
        s = self.section(self.page())
        self.assertIn("<h2>Vendor notes</h2>", s)
        for level, text in ((3, "Heading one"), (4, "Heading two"), (5, "Heading three")):
            self.assertRegex(s, rf"<h{level}>{text}</h{level}>", s[:600])

    def test_emphasis_strike_and_inline_code(self):
        s = self.section(self.page())
        self.assertIn("<strong>bold</strong>", s)
        self.assertIn("<em>italic</em>", s)
        self.assertIn("<s>struck</s>", s)
        self.assertIn("<code>inline_code()</code>", s)

    def test_link_keeps_its_url(self):
        s = self.section(self.page())
        self.assertIn('<a href="https://example.com/page?a=1">link text</a>', s.replace("&amp;", "&"))

    def test_unsafe_link_addresses_are_not_links(self):
        d = self.doc(*base_sections(freetext("[click](javascript:alert(1)) and [x](https://ok.example/a)")))
        s = self.section(self.page(d))
        self.assertEqual(s.count("<a "), 1, "only the https address is a link")
        self.assertNotIn('href="javascript', s)
        self.assertIn('href="https://ok.example/a"', s)

    def test_bullets_nested_and_numbered_lists(self):
        s = self.section(self.page())
        self.assertRegex(s, r"<ul>\s*<li>bullet one</li>\s*<li>bullet two\s*<ul>\s*<li>nested bullet</li>\s*</ul>\s*</li>\s*</ul>")
        self.assertRegex(s, r"<ol>\s*<li>first</li>\s*<li>second</li>\s*</ol>")

    def test_checklist_is_drawn_as_boxes(self):
        s = self.section(self.page())
        self.assertRegex(s, r"<li[^>]*>\s*(?:<span[^>]*>)?☐(?:</span>)?\s*open task")
        self.assertRegex(s, r"<li[^>]*>\s*(?:<span[^>]*>)?☑(?:</span>)?\s*done task")
        self.assertNotIn("[ ]", s)
        self.assertNotIn("[x]", s)

    def test_quote(self):
        self.assertRegex(self.section(self.page()), r"<blockquote>.*A quoted line.*</blockquote>")

    def test_code_block_is_pre_with_its_lines_kept(self):
        s = self.section(self.page())
        self.assertIn("<pre", s)
        self.assertIn("def tidy(x):\n    return x  # kept as typed", s)
        self.assertNotIn("```", s)

    def test_table_is_a_table(self):
        s = self.section(self.page())
        self.assertRegex(s, r"<table[^>]*>.*<th[^>]*>Name</th>.*<th[^>]*>Role</th>.*<td[^>]*>Mia Hale</td>.*<td[^>]*>Sponsor</td>", )
        self.assertNotIn("|---", s)
        self.assertEqual(len(re.findall(r"<tr>", s)), 3)

    def test_picture_is_embedded_as_a_data_uri(self):
        s = self.section(self.page())
        m = re.search(r'<img [^>]*src="data:image/png;base64,([^"]+)"[^>]*alt="Site photo"|<img [^>]*alt="Site photo"[^>]*src="data:image/png;base64,([^"]+)"', s)
        self.assertIsNotNone(m, s[-600:])
        self.assertEqual(base64.b64decode(m.group(1) or m.group(2)), self.photo)
        self.assertNotIn("_images/", s)

    def test_a_picture_outside_images_is_never_read(self):
        (self.tmp / "secret.png").write_bytes(png(8, 8))
        for ref in ("../secret.png", "/etc/passwd", "_images/../secret.png", "https://example.com/x.png", "_images/missing.png"):
            d = self.doc(*base_sections(freetext(f"![evil]({ref})")))
            s = self.section(self.page(d))
            self.assertNotIn("data:image", s, ref)
            self.assertNotIn(f'src="{ref}', s, ref)

    def test_pasted_html_is_escaped_never_passed_through(self):
        evil = '<script>alert(1)</script> <span style="color:red">x</span> <img src=x onerror=alert(2)>\n\n<div style="position:fixed">y</div>'
        s = self.section(self.page(self.doc(*base_sections(freetext(evil))))).replace('<div class="ft">', "", 1)
        for bad in ("<script", "<span", "<img", "<div", "<style"):
            self.assertNotIn(bad, s, bad)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", s)

    def test_filed_page_data_block_survives_a_closing_script_tag(self):
        text = "Before </script><script>alert(1)</script> after\n\n```html\n</script>\n```"
        d = self.doc(*base_sections(freetext(text)))
        page = self.page(d, editing=True)
        self.assertEqual(len(re.findall(r"</script>", page)), 1, "only the data block's own closing tag")
        self.assertEqual(creaite_doc.loads(page)["sections"][1]["text"], text)

    def test_empty_heading_leaves_out_the_h2_and_a_hidden_section_is_gone(self):
        s = self.section(self.page(self.doc(*base_sections(freetext("Just words.", heading="")))))
        self.assertNotIn("<h2>", s)
        self.assertIn("Just words.", s)
        d = self.doc(*base_sections(freetext("walrus words", hidden=True)))
        self.assertNotIn("walrus", self.page(d, editing=False), "left out of the export")
        filed = self.page(d, editing=True)
        self.assertNotIn("walrus", filed.split('<script type="application/json"')[0], "not drawn on the filed page")
        self.assertEqual(creaite_doc.loads(filed)["sections"][1]["text"], "walrus words",
                         "kept in the data so Show brings Alan's words back after a save (a text section can't be refilled)")

    def test_the_section_sits_where_it_was_put_and_moves(self):
        page = self.page()
        self.assertLess(page.index("Before the text section."), page.index("Vendor notes"))
        self.assertLess(page.index("Vendor notes"), page.index("After the text section."))
        d = self.doc(*base_sections(freetext()))
        d["sections"].insert(0, d["sections"].pop(1))
        page = self.page(d)
        self.assertLess(page.index("Vendor notes"), page.index("Before the text section."))

    def test_search_reads_the_section(self):
        words = creaite_doc.search_text(self.doc())
        self.assertIn("Vendor notes", words)
        self.assertIn("Mia Hale", words)
        self.assertIn("bullet two", words)


class WordWrite(Tmp):
    """creaite_doc.word_export: the .docx the section makes."""

    def build(self, doc=None):
        self.out = self.tmp / "out.docx"
        creaite_doc.word_export(doc or self.doc(), self.out)
        self.parts = {i.filename: raw for i, raw in docx_tools.read_parts(self.out)}
        self.xml = self.parts["word/document.xml"].decode("utf-8")
        self.root = ET.fromstring(self.xml)

    def paras(self):
        body = self.root.find(W + "body")
        return ["".join(t.text or "" for t in p.iter(W + "t")) for p in body.findall(W + "p")]

    def tables(self):
        return [[["".join(t.text or "" for t in c.iter(W + "t")) for c in r.findall(W + "tc")] for r in tb.findall(W + "tr")]
                for tb in self.root.iter(W + "tbl")]

    def para_xml(self, needle):
        return next(p for p in re.findall(r"<w:p[ >].*?</w:p>", self.xml, re.S) if needle in re.sub(r"<[^>]+>", "", p))

    def test_heading_named_by_alan_then_body_headings_in_bold(self):
        self.build()
        paras = self.paras()
        self.assertIn("Vendor notes", [p.strip() for p in paras])
        for text in ("Heading one", "Heading two", "Heading three"):
            self.assertIn(text, [p.strip() for p in paras])
            self.assertIn("<w:b/>", self.para_xml(text), text)
        self.assertGreater(paras.index("Heading two"), paras.index("Heading one"))

    def test_emphasis_runs(self):
        self.build()
        p = self.para_xml("Plain words")
        self.assertRegex(p, r"<w:b/>(?:(?!</w:r>).)*<w:t[^>]*>bold</w:t>")
        self.assertRegex(p, r"<w:i/>(?:(?!</w:r>).)*<w:t[^>]*>italic</w:t>")
        self.assertRegex(p, r"<w:strike/>(?:(?!</w:r>).)*<w:t[^>]*>struck</w:t>")

    def test_inline_code_is_monospace(self):
        self.build()
        p = self.para_xml("Plain words")
        self.assertRegex(p, r'<w:rFonts [^>]*w:ascii="(?:Courier New|Menlo|Consolas)"[^>]*/>(?:(?!</w:r>).)*<w:t[^>]*>inline_code\(\)</w:t>')

    def test_link_shows_its_url_in_the_text_or_is_a_hyperlink(self):
        self.build()
        shown = "\n".join(self.paras())
        rels = self.parts["word/_rels/document.xml.rels"].decode("utf-8")
        self.assertIn("link text", shown)
        self.assertTrue("https://example.com/page?a=1" in shown or "https://example.com/page?a=1" in rels.replace("&amp;", "&"),
                        "the address is in the text or in a real hyperlink relationship")

    def test_lists_nested_and_numbered(self):
        self.build()
        paras = [p.strip() for p in self.paras()]
        self.assertIn("• bullet one", paras)
        self.assertIn("• nested bullet", paras)
        self.assertIn("1. first", paras)
        self.assertIn("2. second", paras)
        self.assertRegex(self.para_xml("nested bullet"), r'<w:ind w:left="(?!360")\d+"')

    def test_checklist_boxes(self):
        self.build()
        paras = [p.strip() for p in self.paras()]
        self.assertIn("☐ open task", paras)
        self.assertIn("☑ done task", paras)

    def test_quote(self):
        self.build()
        self.assertIn("A quoted line", [p.strip() for p in self.paras()])
        self.assertRegex(self.para_xml("A quoted line"), r"<w:i/>")

    def test_code_block_is_monospace_lines_in_order(self):
        self.build()
        paras = self.paras()
        at = paras.index("def tidy(x):")
        self.assertEqual(paras[at + 1].strip(), "return x  # kept as typed")
        self.assertEqual(paras[at + 1], "    return x  # kept as typed", "indentation is kept")
        for line in ("def tidy(x):", "    return x  # kept as typed"):
            self.assertRegex(self.para_xml(line.strip()), r'w:ascii="(?:Courier New|Menlo|Consolas)"')
        self.assertNotIn("```", "\n".join(paras))

    def test_table_is_a_word_table(self):
        self.build()
        t = next((t for t in self.tables() if t[0] == ["Name", "Role"]), None)
        self.assertIsNotNone(t, self.tables())
        self.assertEqual(t[1:], [["Mia Hale", "Sponsor"], ["Sam Patel", "Lead"]])
        self.assertNotIn("|---", "\n".join(self.paras()))

    def test_picture_is_placed_from_its_file(self):
        self.build()
        media = [raw for n, raw in self.parts.items() if n.startswith("word/media/")]
        self.assertIn(self.photo, media)
        self.assertGreaterEqual(len(self.root.findall(".//" + W + "drawing")), 1)

    def test_a_picture_outside_images_is_named_not_read(self):
        (self.tmp / "secret.png").write_bytes(png(9, 9, (255, 0, 0, 255)))
        self.build(self.doc(*base_sections(freetext("![evil](../secret.png)\n\n![abs](/etc/hosts)"))))
        self.assertNotIn(png(9, 9, (255, 0, 0, 255)), self.parts.values())
        self.assertFalse([n for n in self.parts if n.startswith("word/media/") and self.parts[n] == png(9, 9, (255, 0, 0, 255))])

    def test_section_order_hidden_and_left_out(self):
        d = self.doc(*base_sections(freetext(), freetext("walrus", heading="Hidden bit", sid="free_2", hidden=True)))
        self.build(d)
        text = "\n".join(self.paras())
        self.assertLess(text.index("Before the text section."), text.index("Vendor notes"))
        self.assertLess(text.index("Vendor notes"), text.index("After the text section."))
        self.assertNotIn("walrus", text + self.xml)
        self.assertNotIn("Hidden bit", text)

    def test_braces_in_the_text_are_not_a_placeholder(self):
        self.build(self.doc(*base_sections(freetext("Use {{SUMMARY}} and {{X}} here.\n\n```\n{{CODE}}\n```\n\n| {{H}} |\n|---|\n| {{C}} |"))))
        text = "\n".join(self.paras()) + str(self.tables())
        self.assertIn("SUMMARY", text)
        self.assertIn("CODE", text)

    @unittest.skipUnless(shutil.which("soffice") or Path("/opt/homebrew/bin/soffice").exists()
                         or Path("/Applications/LibreOffice.app").exists(),
                         "LibreOffice (soffice) is not installed: the docx -> PDF text-order check was NOT run")
    def test_libreoffice_pdf_keeps_the_text_in_order(self):
        self.build()
        soffice = shutil.which("soffice") or next(p for p in ("/opt/homebrew/bin/soffice", "/Applications/LibreOffice.app/Contents/MacOS/soffice")
                                                  if Path(p).exists())
        subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(self.tmp), str(self.out)],
                       check=True, capture_output=True, timeout=240)
        from pypdf import PdfReader
        text = "\n".join(p.extract_text() for p in PdfReader(str(self.tmp / "out.pdf")).pages)
        flat = re.sub(r"\s+", " ", text).lower()        # the template sets section headings in capitals
        at = -1
        for needle in ("Before the text section.", "Vendor notes", "Heading one", "Heading two", "Heading three", "Plain words",
                       "bullet one", "nested bullet", "1. first", "2. second", "open task", "done task", "A quoted line",
                       "def tidy(x):", "return x # kept as typed", "Name", "Mia Hale", "Sam Patel", "After the text section."):
            nxt = flat.find(needle.lower(), at + 1)
            self.assertGreater(nxt, at, f"{needle!r} missing or out of order in the PDF text")
            at = nxt


class ClientRule(Tmp):
    """A text section of the internal report is internal: not in a client output unless matched or written there."""

    def client(self, *sections):
        return self.doc(*sections, kind="client", audience="client", client="Example Client Ltd")

    def test_an_unmatched_internal_text_section_is_not_in_the_client_page_html_or_word(self):
        secret = freetext("INTERNAL-ONLY walrus words", heading="Internal musings", audience="internal")
        d = self.client(*base_sections(secret))
        for editing in (True, False):
            page = self.page(d, editing=editing)
            self.assertNotIn("walrus", page)
            self.assertNotIn("Internal musings", page)
        self.out = self.tmp / "client.docx"
        creaite_doc.word_export(d, self.out)
        xml = next(raw for i, raw in docx_tools.read_parts(self.out) if i.filename == "word/document.xml").decode("utf-8")
        self.assertNotIn("walrus", xml)
        self.assertNotIn("Internal musings", xml)
        self.assertNotIn("walrus", creaite_doc.search_text(d))

    def test_clean_drops_it_for_every_export_path(self):
        d = self.client(*base_sections(freetext("walrus", audience="internal")))
        self.assertNotIn("walrus", json.dumps(creaite_doc.clean(d)))

    def test_a_section_written_or_matched_in_the_client_report_is_shown(self):
        mine = freetext("Written for the client.", heading="A note for you", audience="client")
        d = self.client(*base_sections(mine))
        self.assertIn("Written for the client.", self.page(d))
        self.assertIn("A note for you", self.page(d))

    def test_the_internal_report_shows_its_own_text_section(self):
        self.assertIn("Vendor notes", self.page(self.doc()))

    def test_the_client_leak_gate_reads_a_text_sections_words_and_pictures(self):
        import client_leak
        d = self.client(*base_sections(freetext("See ABC-A-005 and the table:\n\n| a |\n|---|\n| ABC-002 |", audience="client")))
        text = client_leak.doc_text(d)
        self.assertIn("ABC-002", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
