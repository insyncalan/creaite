"""#226: the server's side of the page export (system/scripts/export_page.py) and the plain fallback; no browser except the PDF test.

Run: python3 dev/tests/test_export_page.py
The posted page is never trusted: its markup is rebuilt through an allow-list, its style rules are checked, and it is compared with
the saved report (sections, rows, words that belong to hidden content, a client report's wording). Anything refused gives the plain
file, whose own tests are test_report_exports.py. Acceptance check 8 (client) and 12 (fallback) of the #226 brief are here too.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_report_exports import Base, ITEMS, SECTIONS, chrome_path  # noqa: E402

GOOD = ('<div id="v-weekly" class="export-view"><div class="wrsheet"><div class="page"><section data-id="health"><h2>Health</h2>'
        '<p>The harbour migration slipped a week.</p></section><section data-id="summary"><h2>Executive summary</h2>'
        '<p>Progress on the lighthouse cutover.</p></section></div></div></div>')


def page(markup=GOOD, css=".page{color:#123}", version=1, palette="creaite"):
    return {"html": markup, "css": css, "palette": palette, "version": version}


class Server(Base):
    TRACKER = {"ABC-005": {"title": "Secret quarry", "description": "Secret quarry"},
               "ABC-D-009": {"decision": "walrus"}}

    def build(self, path, pg, kind="weekly"):
        """(file text or None, refusal or None) for the saved document at `path` and the posted page. The tracker lookup is the
        fixture's (the sample vault holds none of these items)."""
        return self.py(f"""
import export_page
export_page.item_lookup = {self.TRACKER!r}.get
doc = creaite_doc.read({path!r})
try:
    print(json.dumps([export_page.build(doc, {pg!r}, 'T'), None]))
except export_page.PageRefused as e:
    print(json.dumps([None, str(e)]))""")

    def test_a_good_page_is_kept_with_its_rules_and_the_light_print_frame(self):
        out, why = self.build(self.saved(), page())
        self.assertIsNone(why)
        self.assertIn('data-theme="light"', out)
        self.assertIn('data-palette="creaite"', out)
        self.assertIn(".page{color:#123}", out)
        self.assertRegex(out, r"@page\{size:A4")
        self.assertIn("print-color-adjust:exact", out)
        self.assertIn("<h2>Health</h2>", out)
        self.assertNotIn("creaite-data", out)

    def test_script_handlers_forms_frames_and_external_addresses_are_stripped(self):
        dirty = ('<div class="page"><section data-id="health" onclick="x()"><h2 onmouseover="y()">Health</h2>'
                 '<script>alert(1)</script><style>body{display:none}</style><iframe src="https://e.example/x"></iframe>'
                 '<button>Edit</button><input value="k"><a href="https://e.example/">link words</a>'
                 '<img src="https://e.example/p.png" alt="remote"><img src="data:image/png;base64,iVBORw0KGgo=" alt="own">'
                 '<p style="background:url(https://e.example/b.png)">a</p><p style="color:red">b</p>'
                 '<svg viewBox="0 0 10 10"><line x1="0" x2="5" onclick="z()" class="wr-tlline"></line><script>1</script></svg>'
                 '</section></div>')
        out, why = self.build(self.saved(), page(dirty))
        self.assertIsNone(why)
        for gone in ("<script", "onclick", "onmouseover", "<style>body", "<iframe", "<button", "<input", "href=", "e.example", "alert("):
            self.assertNotIn(gone, out.split("</style>", 2)[-1], gone)
        self.assertIn("link words", out)
        self.assertIn('alt="own"', out)
        self.assertNotIn("https://", out)
        self.assertIn('style="color:red"', out)
        self.assertIn('class="wr-tlline"', out)

    def test_style_rules_with_an_import_or_an_outside_address_are_refused(self):
        path = self.saved()
        for css in ("@import url(https://e.example/x.css);", ".a{background:url(https://e.example/x.png)}", ".a{width:expression(1)}",
                    "</style><script>1</script>"):
            self.assertIsNotNone(self.build(path, page(css=css))[1], css)
        self.assertIsNone(self.build(path, page(css=".a{background:url(data:image/png;base64,AAAA)} .b{scroll-behavior:auto}"))[1])

    def test_a_hidden_section_a_hidden_row_and_hidden_words_are_refused(self):
        path = self.saved()
        asks = GOOD.replace("</div></div></div>", '<section data-id="asks"><h2>What we need from people</h2></section></div></div></div>')
        self.assertIn("leaves out", self.build(path, page(asks))[1])
        leak = GOOD.replace("</section></div>", "</section><p>Secret <b>quarry</b></p></div>", 1)
        self.assertIn("leaves out", self.build(path, page(leak))[1], "hidden row words, even split by a mark")
        rows = GOOD.replace("</section></div>", '</section><section data-id="risks"><h2>Risks and issues</h2><table><tbody>'
                            "<tr><td>a</td></tr><tr><td>b</td></tr></tbody></table></section></div>", 1)
        self.assertIn("more rows", self.build(path, page(rows))[1], "the saved report shows one risk row")

    def test_words_the_shown_report_holds_too_are_not_taken_for_a_leak(self):
        secs = json.loads(json.dumps(SECTIONS))
        next(s for s in secs if s["id"] == "summary")["text"] = "Vendor capacity is the risk we watch."
        out, why = self.build(self.saved(sections=secs), page(GOOD.replace("</section></div>", "</section><p>Vendor capacity</p></div>", 1)))
        self.assertIsNone(why)

    def test_a_page_drawn_from_another_version_is_refused(self):
        self.assertIn("different version", self.build(self.saved(), page(version=7))[1])

    def test_nothing_or_nonsense_is_refused(self):
        path = self.saved()
        for bad in (None, {}, page(markup=""), page(css="")):
            self.assertIsNotNone(self.build(path, bad)[1], str(bad)[:40])
        self.assertEqual(self.py("import export_page\ntry:\n    export_page.clean_markup('x' * (export_page.MAX_HTML + 1))\nexcept export_page.PageRefused as e:\n    print(json.dumps(str(e)))"),
                         "the page was too large")

    def test_c08_a_client_report_page_is_checked_for_internal_wording_too(self):
        """Check 8: the client report's page goes through the same checks, plus the client wording check."""
        approved = self.saved(pre="doc.update(state='approved', approved_at='2026-10-16 15:00:00')")
        secs = [s for s in SECTIONS if s["id"] in ("health", "summary")]
        path = self.saved("client", sections=secs, pre=f"doc['based_on'] = {{'path': {approved!r}, 'version': 1}}",
                          audience="client", client="Harbour Board")
        ok = self.build(path, page())
        self.assertIsNone(ok[1], ok)
        bad = GOOD.replace("</section></div>", "</section><p>This one is restricted: internal only.</p></div>", 1)
        self.assertIn("client report must not show", self.build(path, page(bad))[1])


class Fallback(Base):
    """Check 12: with no page, or one that fails the check, the Python renderer still gives a file and says it is plain."""

    def test_no_page_gives_the_plain_file_and_says_so(self):
        r = self.export(self.saved(), "html", file_beside=False)
        self.assertTrue(r["ok"] and r["plain"], r)
        self.assertNotIn("plain_why", r)
        self.assertIn("<h2>Health</h2>", (self.v.root / r["path"]).read_text(encoding="utf-8"))

    def test_a_refused_page_gives_the_plain_file_and_the_reason(self):
        pg = page(GOOD.replace("</section></div>", '</section><section data-id="asks"><h2>walrus</h2></section></div>', 1))
        r = self.py(f"print(json.dumps(creaite_doc.export({self.saved()!r}, 'html', file_beside=False, page={pg!r})))")
        self.assertTrue(r["ok"] and r["plain"], r)
        self.assertIn("leaves out", r["plain_why"])
        self.assertNotIn("walrus", (self.v.root / r["path"]).read_text(encoding="utf-8"))

    def test_a_good_page_is_written_as_it_is_checked(self):
        pg = page()
        r = self.py(f"print(json.dumps(creaite_doc.export({self.saved()!r}, 'html', file_beside=False, page={pg!r})))")
        self.assertTrue(r["ok"], r)
        self.assertNotIn("plain", r)
        text = (self.v.root / r["path"]).read_text(encoding="utf-8")
        self.assertIn("The harbour migration slipped a week.", text)
        self.assertNotIn("<h2>Risks and issues</h2>", text)

    @unittest.skipUnless(chrome_path(), "Chrome isn't installed")
    def test_the_pdf_prints_the_same_page(self):
        import pypdf
        pg = page()
        r = self.py(f"print(json.dumps(creaite_doc.export({self.saved()!r}, 'pdf', file_beside=False, page={pg!r})))")
        self.assertTrue(r["ok"], r)
        self.assertNotIn("plain", r)
        text = "".join(p.extract_text() for p in pypdf.PdfReader(str(self.v.root / r["path"])).pages)
        self.assertIn("lighthouse cutover", text)
        self.assertNotIn("Risks and issues", text)

    def test_word_ignores_a_page(self):
        pg = page()
        r = self.py(f"print(json.dumps(creaite_doc.export({self.saved()!r}, 'docx', file_beside=False, page={pg!r})))")
        self.assertTrue(r["ok"], r)
        self.assertNotIn("plain", r)


if __name__ == "__main__":
    unittest.main()
