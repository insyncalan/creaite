"""#121: links in plain text, wherever the text is shown, exported or searched (the Python side). Quick tier: no Chrome.

Run: python3 dev/tests/test_link_text.py

A link in a plain text field is kept as `[words](address)` (the dashboard's core/linkText.js writes it). Every place that shows or exports
that text reads it through system/scripts/linktext.py, so the raw characters never show:

| place                                  | how a link reads                                                                   | test                                |
|----------------------------------------|------------------------------------------------------------------------------------|-------------------------------------|
| Word reports, client reports, steerco  | a real hyperlink (the address is in the document's relationships)                  | WordHyperlinks                      |
| Word text preview, the draft checks    | "words (address)": the address is read like the words                              | WordHyperlinks, ClientChecks        |
| one-off Word tables (adhoc)            | "words (address)"                                                                  | Places.test_adhoc_and_facts         |
| HTML (the prep page)                   | an anchor, new tab, rel noopener noreferrer; print shows the address               | Places.test_prep_page               |
| the Excel export                       | the cell holds the words with a hyperlink on it ("words (address)" if several)     | Excel                               |
| the Excel import                       | the cell still saying what the export wrote is not a change; a hyperlink is not read | Excel                              |
| search                                 | the words are matched, the address never is                                        | Search                              |
| Review, Activity, status facts         | the words                                                                          | Places                              |
| (the dashboard's tables, peek, Draft email, Today: test_editor_links_plain.py)   |                                                                                    |                                     |
Every case is run with a hostile address: it is never a link, in any place.
"""
import json
import re
import sys
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import ABC, Vault, action  # noqa: E402

SCRIPTS = Path(__file__).resolve().parents[2] / "system" / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SCRIPTS / "vendor"))
import linktext  # noqa: E402
from openpyxl import load_workbook  # noqa: E402

GOOD = ["https://example.com/plan", "mailto:pmo@example.com"]
BAD = ["javascript:alert(1)", "JaVaScRiPt:alert(2)", "data:text/html,x", "file:///etc/passwd", "//evil.example/x", "vbscript:msgbox(1)",
       "https://user@evil.example/x", "ftp://example.com/x", "https://example.com/<script>", "https://exa%20mple.com", "relative/path",
       "https://example.com/&#106;avascript", "http://999.1.1.1/x", "https://[:::]/x", "https://example.com:70000/x"]
MATRIX = ("See [the plan](https://example.com/plan) and [mail us](mailto:pmo@example.com) then "
          + " ".join(f"[bad{i}]({a})" for i, a in enumerate(BAD)) + ".")


class Format(unittest.TestCase):
    def test_segments_words_and_addresses(self):
        segs = linktext.segments(MATRIX)
        self.assertEqual([(t, h) for t, h in segs if h], [("the plan", GOOD[0]), ("mail us", GOOD[1])])
        words = linktext.words(MATRIX)
        self.assertTrue(words.startswith("See the plan and mail us then [bad0](javascript:alert(1))"))
        for i, a in enumerate(BAD):
            self.assertIn(f"[bad{i}]({a})", words, "a refused address stays the literal text it is")
        self.assertEqual(linktext.with_address("x [w](https://example.com/a) [m](mailto:a@example.com)"), "x w (https://example.com/a) m (a@example.com)")
        self.assertEqual(linktext.addresses(MATRIX), GOOD)

    def test_html_is_escaped_and_only_a_good_address_is_an_anchor(self):
        h = linktext.html(MATRIX + " <b>&\"'")
        self.assertEqual(re.findall(r'<a class="tlink" href="([^"]*)" target="_blank" rel="noopener noreferrer">', h), GOOD)
        self.assertEqual(h.count("<a "), 2)
        self.assertNotIn("<b>", h)
        self.assertIn("&lt;b&gt;&amp;&quot;&#39;", h)
        for a in BAD:
            self.assertNotIn(f'href="{a}"', h)
        self.assertEqual(linktext.html("a [w](https://example.com/x?a=1&b=2)"),
                         'a <a class="tlink" href="https://example.com/x?a=1&amp;b=2" target="_blank" rel="noopener noreferrer">w</a>')

    def test_writing_and_reading_agree(self):
        for words, href in (("plan", "https://example.com/plan"), ("v[1] a\\b", "https://example.com/a_(b)"), ("x", "mailto:a@example.com"),
                            ("p", "https://example.com/a(b")):
            w = linktext.write(words, href)
            self.assertEqual(linktext.segments("<" + w + ">")[1][0], words)
            self.assertEqual(linktext.segments("<" + w + ">")[1][1], href if re.fullmatch(r"(?:[^()\s]|\([^()\s]*\))+", href) else href.replace("(", "%28"))
        self.assertIsNone(linktext.write("x", "javascript:alert(1)"))
        self.assertIsNone(linktext.write("", "https://example.com"))
        self.assertEqual(linktext.words("plain text, no link"), "plain text, no link")
        self.assertEqual((linktext.words(None), linktext.with_address(None), linktext.html(None)), ("", "", ""))

    def test_a_marker_in_the_address_is_found_by_the_checks_that_read_text(self):
        import drafts
        import status_facts
        text = "See [the plan](https://x.example/confidential-budget) for detail."
        self.assertTrue(drafts.secret(text), "the confidentiality check reads the address like the words")
        self.assertTrue(status_facts.SENSITIVE.search(text))
        self.assertIn("confidential", linktext.checkable(text))
        self.assertFalse(drafts.secret(linktext.words(text)), "(which is why no check may be run on the words alone)")


class WordHyperlinks(unittest.TestCase):
    """Word: a link in a value is a real hyperlink, the text preview and the draft checks show its address."""

    def setUp(self):
        self.v = Vault()
        self.v.run("init")

    def tearDown(self):
        self.v.cleanup()

    def fill(self, text):
        drafts = self.v.root / "system/staging/drafts"
        tpl = drafts / "tpl.docx"
        doc = ('<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
               '<w:p><w:r><w:rPr><w:b/><w:sz w:val="20"/></w:rPr><w:t>{{X}}</w:t></w:r></w:p></w:body></w:document>')
        rels = '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>'
        with zipfile.ZipFile(tpl, "w") as z:
            z.writestr("word/document.xml", doc)
            z.writestr("word/_rels/document.xml.rels", rels)
            z.writestr("[Content_Types].xml", "<Types/>")
        values = drafts / "values.json"
        values.write_text(json.dumps({"X": text}), encoding="utf-8")
        out = drafts / "out.docx"
        self.v.run("fill", str(tpl), str(values), str(out), script="docx_tools.py", cwd=self.v.root)
        with zipfile.ZipFile(out) as z:
            return out, z.read("word/document.xml").decode("utf-8"), z.read("word/_rels/document.xml.rels").decode("utf-8")

    def test_a_good_link_is_a_real_hyperlink_and_a_hostile_one_is_text(self):
        out, doc, rels = self.fill(MATRIX)
        self.assertEqual(doc.count("<w:hyperlink "), 2)
        for a in GOOD:
            self.assertRegex(rels, re.escape(f'Target="{a}" TargetMode="External"'))
        self.assertEqual(len(re.findall(r"<Relationship ", rels)), 2, "only the two good addresses were related")
        for a in BAD:
            self.assertNotIn(f'Target="{a}"', rels)
        self.assertIn("[bad0](javascript:alert(1))", re.sub(r"<[^>]+>", "", doc), "a hostile address is the literal text")
        self.assertRegex(doc, r'<w:color w:val="0563C1"/>')
        self.assertIn("xmlns:r=", doc[:600])
        self.assertNotRegex(doc, "[\x01\x02\x03]")
        text = self.v.run("text", str(out), script="docx_tools.py").stdout
        self.assertIn("See the plan (https://example.com/plan) and mail us (pmo@example.com) then [bad0](javascript:alert(1))", text)
        self.assertNotIn("[the plan]", text)
        import review
        lines = review.draft_lines(out)
        self.assertIn("(https://example.com/plan)", " ".join(lines), "the draft checks read the address as they read the words")

    def test_an_ampersand_in_an_address_is_escaped_in_the_relationship(self):
        out, doc, rels = self.fill("Go [here](https://example.com/a?b=1&c=2) now")
        self.assertIn('Target="https://example.com/a?b=1&amp;c=2"', rels)
        self.assertIn("https://example.com/a?b=1&c=2", self.v.run("text", str(out), script="docx_tools.py").stdout)

    def parse_ok(self, doc, label):
        """The document.xml parses, and every hyperlink sits directly inside one paragraph."""
        import xml.etree.ElementTree as ET
        try:
            root = ET.fromstring(doc.encode("utf-8"))
        except ET.ParseError as e:
            self.fail(f"{label}: document.xml is not well-formed: {e}")
        W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        for para in root.iter(W + "p"):
            for child in para:
                self.assertIn(child.tag, {W + t for t in ("r", "pPr", "hyperlink", "bookmarkStart", "bookmarkEnd", "proofErr", "ins", "del",
                                                        "sdt", "smartTag", "fldSimple", "commentRangeStart", "commentRangeEnd")}, label)
        self.assertEqual(len(list(root.iter(W + "hyperlink"))), len([h for p in root.iter(W + "p") for h in p.findall(W + "hyperlink")]),
                         f"{label}: a hyperlink sits outside its paragraph")
        return root

    def test_a_link_leaves_the_document_well_formed_beside_a_styled_paragraph(self):
        """The #121 run pattern must stop at its own run: a bold 'Title' paragraph before the placeholder used to be swallowed."""
        drafts = self.v.root / "system/staging/drafts"
        tpl = drafts / "tpl2.docx"
        doc = ('<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
               '<w:p><w:r><w:rPr><w:b/></w:rPr><w:t>Title</w:t></w:r></w:p>'
               '<w:p><w:r><w:rPr><w:sz w:val="20"/></w:rPr><w:t>{{X}}</w:t></w:r></w:p></w:body></w:document>')
        with zipfile.ZipFile(tpl, "w") as z:
            z.writestr("word/document.xml", doc)
            z.writestr("word/_rels/document.xml.rels", '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>')
            z.writestr("[Content_Types].xml", "<Types/>")
        (drafts / "v2.json").write_text(json.dumps({"X": "see [plan](https://a.example/p) now"}), encoding="utf-8")
        out = drafts / "out2.docx"
        self.v.run("fill", str(tpl), str(drafts / "v2.json"), str(out), script="docx_tools.py", cwd=self.v.root)
        with zipfile.ZipFile(out) as z:
            d = z.read("word/document.xml").decode("utf-8")
        self.parse_ok(d, "synthetic")
        text = re.sub(r"<[^>]+>", "", d)
        self.assertEqual((text.count("Title"), text.count("see "), text.count("plan"), text.count(" now")), (1, 1, 1, 1))

    def test_every_real_template_stays_well_formed_with_a_link_in_each_placeholder(self):
        tpls = Path(__file__).resolve().parents[2] / "system" / "templates"
        drafts = self.v.root / "system/staging/drafts"
        for t in sorted(tpls.glob("*-template.docx")):
            if t.name.startswith("vault"):
                continue
            with zipfile.ZipFile(t) as z:
                src = z.read("word/document.xml").decode("utf-8")
            names = sorted(set(re.findall(r"\{\{([A-Z][A-Z0-9_]*)\}\}", re.sub(r"<[^>]+>", "", src))))
            names = [n for n in names if not n.startswith("STYLE_")]
            self.assertTrue(names, t.name)
            for n in names:
                # one placeholder at a time holds a link, the rest are plain: every placeholder is tried
                values = {k: f"plain{j}" for j, k in enumerate(names)}
                values[n] = "see [plan](https://a.example/p) now"
                (drafts / "tv.json").write_text(json.dumps(values), encoding="utf-8")
                out = drafts / "tout.docx"
                r = self.v.run("fill", str(t), str(drafts / "tv.json"), str(out), script="docx_tools.py", cwd=self.v.root, ok=False)
                if r.returncode != 0:
                    continue                                   # a placeholder the filler refuses a plain string for is not this test's
                with zipfile.ZipFile(out) as z:
                    d = z.read("word/document.xml").decode("utf-8")
                self.parse_ok(d, f"{t.name} {n}")
                text = re.sub(r"<[^>]+>", "", d)
                plain_src = re.sub(r"<[^>]+>", "", src)
                self.assertEqual(text.count("plan"), len(re.findall(r"\{\{" + n + r"\}\}", plain_src)),
                                 f"{t.name} {n}: the link text appears once per placeholder")

    def test_a_one_off_document_paragraph_shows_the_words_and_address_never_raw(self):
        import docx_tools
        para = '<w:p><w:r><w:rPr><w:b/></w:rPr><w:t>x</w:t></w:r></w:p>'
        out = docx_tools.put_text(para, "Read [the plan](https://example.com/plan) now")
        self.assertIn("Read the plan (https://example.com/plan) now", out)
        self.assertNotIn("](", out)
        self.parse_ok('<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>' + out + '</w:body></w:document>', "put_text")

    def test_text_with_no_link_is_filled_as_it_always_was(self):
        out, doc, rels = self.fill("Plain & simple [not a link] (really)")
        self.assertNotIn("<w:hyperlink", doc)
        self.assertIn("Plain &amp; simple [not a link] (really)", doc)
        self.assertEqual(rels.count("<Relationship "), 0)


class Seeded(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        self.two = "Plan [one](https://example.com/one) and [two](https://example.com/two)."
        self.one = "Read [the plan](https://example.com/plan) now."
        self.v.propose("seed", [
            action(1, latest_update=self.one),
            action(2, description="Book UAT environment", latest_update=self.two),
            action(3, description="Third", latest_update=MATRIX),
            {"n": 4, "op": "new", "table": "raid", "match": "strong", "flags": [], "decision": "approved",
             "values": {"project": "ABC", "type": "Risk", "description": "Data access delayed", "impact": "High", "likelihood": "Medium",
                        "raised": "2026-10-01", "response_action": self.one, "source": f"{ABC}/minutes/x.docx — Risks"}},
            {"n": 5, "op": "new", "table": "decisions", "match": "strong", "flags": [], "decision": "approved",
             "values": {"project": "ABC", "decision": "Go-live moves", "date": "2026-10-01", "reasoning": self.one, "options": self.two,
                        "source": f"{ABC}/minutes/x.docx — Decisions"}},
        ])
        self.v.run("apply")
        self.xlsx = self.v.root / "tracker-view.xlsx"

    def tearDown(self):
        self.v.cleanup()


class Excel(Seeded):
    def cell(self, wb, sheet, row, label):
        ws = wb[sheet]
        h = [c.value for c in ws[1]]
        return ws.cell(row=row, column=h.index(label) + 1)

    def test_a_cell_holds_the_words_with_a_hyperlink_and_several_links_read_words_and_address(self):
        wb = load_workbook(self.xlsx)
        c = self.cell(wb, "Actions", 2, "Latest update")
        self.assertEqual(c.value, "Read the plan now.")
        self.assertEqual(c.hyperlink.target if c.hyperlink and c.hyperlink.target else c.hyperlink.location, "https://example.com/plan")
        c2 = self.cell(wb, "Actions", 3, "Latest update")
        self.assertEqual(c2.value, "Plan one (https://example.com/one) and two (https://example.com/two).")
        self.assertIsNone(c2.hyperlink, "one cell cannot carry two links")
        c3 = self.cell(wb, "Actions", 4, "Latest update")                # the matrix: two good links, so words and addresses, and every hostile one literal
        self.assertIsNone(c3.hyperlink)
        self.assertTrue(c3.value.startswith("See the plan (https://example.com/plan) and mail us (pmo@example.com) then [bad0](javascript:alert(1))"))
        self.assertNotIn("[the plan]", c3.value)
        self.assertEqual(self.cell(wb, "RAID", 2, "Response action").value, "Read the plan now.")
        self.assertEqual(self.cell(wb, "Decisions", 2, "Reasoning").value, "Read the plan now.")
        self.assertTrue(self.cell(wb, "Decisions", 2, "Options").value.startswith("Plan one (https://example.com/one)"))

    def test_the_import_does_not_read_the_words_or_a_hyperlink_as_a_change(self):
        r = self.v.run("changed", script="excel_sync.py", ok=False)
        self.assertEqual(r.returncode, 0, "a fresh export has no edits")
        wb = load_workbook(self.xlsx)
        ws = wb["Actions"]
        h = [c.value for c in ws[1]]
        ws.cell(row=2, column=h.index("Owner") + 1, value="Sara Example")      # one real edit; the link cells are saved as the export wrote them
        wb.save(self.xlsx)
        self.v.run("import", script="excel_sync.py")
        staged = sorted((self.v.root / "system/staging").glob("proposed-*-excel*.json"))[-1]
        items = json.loads(staged.read_text())["items"]
        self.assertEqual([(i["id"], sorted(i["changes"])) for i in items], [("ABC-A-001", ["owner"])],
                         "the link cells were not read as changes (the words are what the export wrote)")

    def test_an_edited_link_cell_is_said_to_lose_its_address(self):
        wb = load_workbook(self.xlsx)
        ws = wb["Actions"]
        h = [c.value for c in ws[1]]
        ws.cell(row=2, column=h.index("Latest update") + 1, value="Read the new plan now.")
        wb.save(self.xlsx)
        out = self.v.run("import", script="excel_sync.py").stdout
        self.assertIn("ABC-A-001", out)
        self.assertIn("Latest update cell was edited", out)
        self.assertIn("https://example.com/plan", out, "the address that goes is named")

    def test_the_weekly_data_gives_the_model_the_words_of_a_response(self):
        data = json.loads(self.v.run("weekly-data", "ABC", script="report.py").stdout)
        resp = [r["response"] for r in data["top_risks"] if r["text"] == "Data access delayed"]
        self.assertEqual(resp, ["Read the plan now."], "not the raw [words](address)")

    def test_an_edited_link_cell_is_staged_as_the_words_typed(self):
        wb = load_workbook(self.xlsx)
        ws = wb["Actions"]
        h = [c.value for c in ws[1]]
        ws.cell(row=2, column=h.index("Latest update") + 1, value="Read the new plan now.")
        wb.save(self.xlsx)
        self.v.run("import", script="excel_sync.py")
        staged = sorted((self.v.root / "system/staging").glob("proposed-*-excel*.json"))[-1]
        items = json.loads(staged.read_text())["items"]
        self.assertEqual(items[0]["changes"], {"latest_update": "Read the new plan now."})


class Search(Seeded):
    def hits(self, q):
        r = self.v.run("query", q, "--no-parse", script="search.py")
        return sorted(i["id"] for i in json.loads(r.stdout)["groups"]["items"])

    def test_the_words_are_matched_and_the_address_never_is(self):
        self.assertIn("ABC-A-001", self.hits("plan"), "a word of the link matches")
        self.assertEqual([i for i in self.hits("example") if i in ("ABC-A-001", "ABC-A-002")], [],
                         "a word that is only in an address matches nothing")
        self.assertEqual([i for i in self.hits("https") if i in ("ABC-A-001", "ABC-A-002")], [])
        self.assertIn("ABC-A-003", self.hits("example"), "but a hostile address is literal text, and literal text is searched")
        self.assertIn("ABC-A-003", self.hits("plan"))
        self.assertIn("ABC-A-001", self.hits("read"), "the plain words of the same text still match")


class SearchEdge(Seeded):
    def test_a_phrase_spanning_a_links_edge_matches_on_the_words(self):
        r = self.v.run("query", "\"plan now\"", script="search.py")
        ids = sorted(i["id"] for i in json.loads(r.stdout)["groups"]["items"])
        self.assertIn("ABC-A-001", ids, "'the plan' + ' now' is 'plan now' in the displayed words")
        r = self.v.run("query", "plan example", "--no-parse", script="search.py")
        ids = sorted(i["id"] for i in json.loads(r.stdout)["groups"]["items"])
        self.assertNotIn("ABC-A-001", ids, "the address still never matches")


class Places(Seeded):
    def test_review_activity_facts_and_adhoc_show_the_words(self):
        import build_dashboard
        import report
        import review
        import status_facts
        d = review.describe({"op": "update", "table": "actions", "id": "ABC-A-001", "changes": {"latest_update": MATRIX}})
        self.assertIn("latest_update → See the plan and mail us then [bad0](javascript:alert(1))", d[1])
        self.assertNotIn("[the plan]", d[1])
        act = build_dashboard._act_change({"field": "latest_update", "op": "update", "old_value": self.one, "new_value": self.two}, "actions", {})
        self.assertEqual(act, "latest update: Read the plan now. → Plan one and two.")
        self.assertEqual(status_facts.sent(self.one), "Read the plan now.")
        cell = report._adhoc_cell({"latest_update": self.one}, "latest_update", "actions", {}, "2026-10-16")
        self.assertEqual(cell, "Read the plan (https://example.com/plan) now.")

    def test_prep_page(self):
        import prep_view
        h = prep_view._line_html({"text": MATRIX, "sources": []}, 8765)
        self.assertEqual(re.findall(r'<a class="tlink" href="([^"]*)" target="_blank" rel="noopener noreferrer">', h), GOOD)
        self.assertNotIn("[the plan]", h)
        self.assertIn("[bad0](javascript:alert(1))", h)
        import prep_page
        css = Path(prep_page.__file__).read_text()
        self.assertIn('a.tlink::after{content:" (" attr(href) ")"', css, "printed, the address shows")

    def test_the_python_check_is_never_looser_than_the_dashboards(self):
        """The same cases as test_editor_links.py; the dashboard's side is compared in test_editor_links_plain.py (it needs Chrome)."""
        for a in ("https://example.com", "http://example.com/a?b=1&c=2#d", "https://example.com:8443/x", "https://sub.example.co.uk/a_(b)",
                  "https://[2001:db8::1]/x", "mailto:pmo@example.com", "MAILTO:pmo@example.com?subject=Plan%20review", "mailto:pmo@example.com?subject=Hi&body=Hello%20there", "https://xn--caf-dma.example/", "HTTPS://Example.com/Path"):
            self.assertIsNotNone(linktext.valid_address(a), a)
        for a in ["javascript:alert(1)", "JAVASCRIPT:alert(1)", "jav\tascript:alert(1)", "java&#x09;script:alert(1)", " javascript:alert(1)",
                  "​https://example.com", "data:text/html,x", "file:///etc/passwd", "blob:https://example.com/x", "about:blank", "ftp://example.com/x",
                  "tel:+441234567890", "creaite:item/ABC-A-001", "//evil.example/x", "\\\\evil.example\\x", "/relative", "example.com", "https://", "https:///x",
                  "https://user:pw@example.com", "https://bank.example@evil.example/", "https://exa mple.com", "https://example.com/\"x", "https://example.com/<x>",
                  "https://example.com/`x`", "mailto:pmo@example.com?bcc=x@evil.example", "mailto:pmo@example.com?subject=Hi&cc=x@evil.example", "mailto:pmo@example.com?to=x@evil.example",
    "mailto:a%40evil.example%2Cb@good.example%zz", "mailto:a%40evil.example%2Cb@good.example", "mailto:pmo@example.com?%62cc=x@evil.example",
    "mailto:pmo@example.com?subject=%zz", "mailto:pmo@example.com#frag", "https://\u0430pple.com", "https://\u00e9_!$&'()*+,;=.com/", "https://caf\u00e9.example/",
    "mailto:", "mailto:nobody", "mailto:a@example.com,b@example.com", "mailto:a@b@example.com", "", None, 5,
                  "x" * 3000, "https://example.com/" + "x" * 2100]:
            self.assertIsNone(linktext.valid_address(a), a)


if __name__ == "__main__":
    unittest.main()
