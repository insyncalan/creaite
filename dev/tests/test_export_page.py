"""#226: the server's side of the page export (system/scripts/export_page.py) and the plain fallback; no browser except the PDF test.

Run: python3 dev/tests/test_export_page.py
The posted page is never trusted: its markup is rebuilt through an allow-list, its style rules are checked, and it is compared with
the saved report (sections, rows, words that belong to hidden content, a client report's wording). Anything refused gives the plain
file, whose own tests are test_report_exports.py. Acceptance check 8 (client) and 12 (fallback) of the #226 brief are here too.
"""
import base64
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_report_exports import Base, SECTIONS, chrome_path  # noqa: E402

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


class LeakFix(Base):
    """p240-leakfix (Team Cap's review): the words and IDs of what a report leaves out must not survive in attributes, style rules,
    in other letter case, or with no version; a client file keeps only a short allow-list of attributes."""
    TRACKER = {"ABC-005": {"title": "Walrus budget cut", "description": "Walrus budget cut"}, "ABC-D-009": {"decision": "walrus"}}
    build = Server.build

    def client(self):
        approved = self.saved(pre="doc.update(state='approved', approved_at='2026-10-16 15:00:00')")
        secs = [s for s in SECTIONS if s["id"] in ("health", "summary", "risks")]     # risks holds the hidden row ABC-005
        return self.saved("client", sections=secs, pre=f"doc['based_on'] = {{'path': {approved!r}, 'version': 1}}",
                          audience="client", client="Harbour Board")

    @staticmethod
    def wrap(inner):
        return GOOD.replace("</section></div>", "</section>" + inner + "</div>", 1)

    def test_leak1_hidden_words_in_any_kept_attribute_are_refused_internal(self):
        path = self.saved()
        for attr in ('title="Walrus budget cut"', 'aria-label="Walrus budget cut"', 'data-note="Walrus budget cut"'):
            self.assertIn("leaves out", self.build(path, page(self.wrap(f"<p {attr}>x</p>")))[1], attr)
        for svg in ('<svg viewBox="0 0 9 9"><rect fill="red" data-x="Walrus budget cut"></rect></svg>',
                    '<img src="data:image/png;base64,iVBORw0KGgo=" alt="Walrus budget cut">'):
            self.assertIn("leaves out", self.build(path, page(self.wrap(svg)))[1], svg)

    def test_leak1_a_client_file_drops_every_attribute_off_the_list_and_still_reads_the_rest(self):
        path = self.client()
        out, why = self.build(path, page(self.wrap('<p title="Zanzibar" aria-label="Zanzibar" data-row="ABC-005" data-note="q">x</p>'
                                                   '<img alt="Zanzibar" src="data:image/png;base64,iVBORw0KGgo=">')))
        self.assertIsNone(why)
        for gone in ("title=", "aria-label", "data-row", "data-note", "alt=", "ABC-005", "Zanzibar"):
            self.assertNotIn(gone, out.split("</style>", 2)[-1], gone)
        self.assertIn('data-id="health"', out)
        self.assertIn("leaves out", self.build(path, page(self.wrap('<p class="Walrus budget cut">x</p>')))[1])
        self.assertIn("leaves out", self.build(path, page(self.wrap('<p style="content:\'Walrus budget cut\'">x</p>')))[1])

    def test_leak1_style_rules_with_a_hidden_word_in_content_are_refused(self):
        for path in (self.saved(date="2026-10-09"), self.client()):
            why = self.build(path, page(css='.a::after{content:"Walrus budget cut"}'))[1]
            self.assertIn("leaves out", why)

    def test_leak4_item_ids_never_reach_a_client_file_as_attributes(self):
        out, why = self.build(self.client(), page(self.wrap(
            '<table><tbody><tr data-row="ABC-005" data-ref="ABC-A-003"><td>x</td></tr></tbody></table>')))
        self.assertIsNone(why)
        self.assertNotRegex(out.split("</style>", 2)[-1], r"[A-Z0-9]{3,7}-(?:[A-Z]-)?\d+")

    def test_leak5_a_page_without_a_version_is_refused(self):
        pg = page()
        del pg["version"]
        path = self.saved()
        self.assertIn("version", self.build(path, pg)[1])
        pg["version"] = "x"
        self.assertIn("version", self.build(path, pg)[1])

    def test_leak6_words_are_matched_without_case(self):
        path = self.saved()
        for w in ("WALRUS BUDGET CUT", "walrus Budget cut", "Ｗalrus budget cut"):
            self.assertIn("leaves out", self.build(path, page(self.wrap(f"<p>{w}</p>")))[1], w)


class ResidualLeaks(Base):
    """Team Cap's re-review of p240-leakfix: four ways round the needle check that are closed here. The needle is a fictional hidden
    item's title, 'Walrus budget cut' (the client report hides ABC-005); a client file must never carry it."""

    TRACKER = LeakFix.TRACKER
    build = Server.build
    client = LeakFix.client
    wrap = staticmethod(LeakFix.wrap)

    def both(self):
        """(kind, stored path) of the internal and the client report; each is saved once per test (a second save of a filed report asks)."""
        if not hasattr(self, "_both"):
            self._both = (("internal", self.saved(date="2026-10-09")), ("client", self.client()))
        return self._both

    def test_a_css_content_written_with_escapes_or_split_strings_is_refused(self):
        for kind, path in self.both():
            for css in ('.a::after{content:"\\0057alrus budget cut"}', '.a::after{content:"Wal" "rus budget cut"}',
                        '.a::after{content:"Wal"/**/"rus bu" \'dget cut\'}', '.a::after{content:"\\57 alrus budget \\63 ut"}'):
                self.assertIn("leaves out", self.build(path, page(css=css))[1] or "", f"{kind}: {css}")
            self.assertIn("leaves out", self.build(path, page(self.wrap('<p style="content:\'\\0057alrus budget cut\'">x</p>')))[1] or "", kind)

    def test_a_picture_that_is_an_svg_data_address_is_read_for_the_needle(self):
        import base64
        for svg in ('<svg xmlns="http://www.w3.org/2000/svg"><title>Walrus budget cut</title></svg>',
                    '<svg xmlns="http://www.w3.org/2000/svg"><desc>Walrus budget cut</desc></svg>',
                    '<svg xmlns="http://www.w3.org/2000/svg"><text>Walrus budget cut</text></svg>',
                    '<svg xmlns="http://www.w3.org/2000/svg" data-n="Walrus budget cut"><rect/></svg>'):
            src = "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()
            for kind, path in self.both():
                self.assertIn("leaves out", self.build(path, page(self.wrap(f'<img src="{src}">')))[1] or "", f"{kind}: {svg}")
        ok = "data:image/svg+xml;base64," + base64.b64encode(b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="3" height="3"/></svg>').decode()
        self.assertIsNone(self.build(self.both()[1][1], page(self.wrap(f'<img src="{ok}">')))[1], "an SVG with nothing hidden in it is kept")

    def test_zero_width_characters_and_the_soft_hyphen_do_not_hide_a_word(self):
        for mark in ("​", "‌", "‍", "⁠", "﻿", "­"):
            word = f"Wal{mark}rus budget cut"
            for kind, path in self.both():
                self.assertIn("leaves out", self.build(path, page(self.wrap(f"<p>{word}</p>")))[1] or "", f"{kind}: {mark!r} in the text")
                self.assertIn("leaves out", self.build(path, page(css=f'.a::after{{content:"{word}"}}'))[1] or "", f"{kind}: {mark!r} in css")
            self.assertIn("leaves out", self.build(self.both()[0][1], page(self.wrap(f'<p title="{word}">x</p>')))[1] or "", f"{mark!r} in an attribute")

    def test_ids_joined_to_each_other_are_found_in_a_client_attribute(self):
        out, why = self.build(self.client(), page(self.wrap('<p class="ABC-A-001ABC-A-002">x</p><p class="a ABC-005,ABC-A-003">y</p>'
                                                            '<p class="xxABC-A-004yy">z</p>')))
        self.assertIsNone(why)
        tail = out.split("</style>", 2)[-1]
        for gone in ("ABC-A-001", "ABC-A-002", "ABC-005", "ABC-A-003", "ABC-A-004"):
            self.assertNotIn(gone, tail, gone)


class LeakPass2(Base):
    """v240-leak2 (Team Cap, 22:28 and 22:42): a CSS background picture, a wider set of invisible characters and a picture inside an
    SVG picture must not carry a hidden word into any file, and a client file takes no SVG picture in its styles at all."""

    TRACKER = LeakFix.TRACKER
    build = Server.build
    client = LeakFix.client
    wrap = staticmethod(LeakFix.wrap)
    SVG = '<svg xmlns="http://www.w3.org/2000/svg"><text>Walrus budget cut</text></svg>'

    both = ResidualLeaks.both

    def addresses(self):
        import base64
        from urllib.parse import quote
        return ["data:image/svg+xml;base64," + base64.b64encode(self.SVG.encode()).decode(),
                "data:image/svg+xml," + quote(self.SVG, safe=""),
                "data:image/svg+xml;utf8," + self.SVG.replace("<", "%3C").replace(">", "%3E").replace(" ", "%20")]

    def test_a_css_background_svg_is_refused_in_a_style_attribute_and_a_stylesheet(self):
        for addr in self.addresses():
            for quote_mark in ("", "'", '"'):
                url = f"url({quote_mark}{addr}{quote_mark})"
                for kind, path in self.both():
                    attr = '<p style="background:%s">x</p>' % url.replace('"', "&quot;")
                    out, why = self.build(path, page(LeakFix.wrap(attr)))
                    if kind == "internal":
                        self.assertIn("leaves out", why or "", f"{kind} style attribute: {url[:60]}")
                    else:
                        self.assertTrue(why or "walrus" not in (out or "").lower().replace("%20", " "), f"{kind} attr: {url[:60]}")
                        self.assertNotIn("svg+xml", (out or "").split("</style>", 2)[-1], kind)
                    out, why = self.build(path, page(css=f".page{{background:{url}}}"))
                    if kind == "internal":
                        self.assertIn("leaves out", why or "", f"{kind} stylesheet: {url[:60]}")
                    else:
                        self.assertIsNotNone(why, f"a client file takes no SVG address in its styles: {url[:60]}")

    def test_a_client_file_refuses_any_unreadable_or_odd_data_address_in_styles(self):
        path = self.client()
        for css in (".page{background:url(data:text/html;base64,PHA+)}", ".page{background:url(data:image/svg+xml;base64,@@@)}",
                    ".page{background:url(data:application/x;base64,AAAA)}"):
            self.assertIsNotNone(self.build(path, page(css=css))[1], css)
        self.assertIsNone(self.build(path, page(css=".page{background:url(data:image/png;base64,iVBORw0KGgo=)}"))[1])

    def test_an_internal_file_keeps_a_css_svg_with_nothing_hidden_in_it(self):
        import base64
        ok = "data:image/svg+xml;base64," + base64.b64encode(b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="3" height="3"/></svg>').decode()
        self.assertIsNone(self.build(self.both()[0][1], page(css=f".page{{background:url({ok})}}"))[1])

    def test_more_invisible_characters_do_not_hide_a_word(self):
        for mark in ("⁣", "͏", "︀", "᠎", "⁤", "‪", "\U000e0020", "؜"):
            word = f"Wal{mark}rus budget cut"
            for kind, path in self.both():
                self.assertIn("leaves out", self.build(path, page(self.wrap(f"<p>{word}</p>")))[1] or "", f"{kind}: {mark!r} text")
                self.assertIn("leaves out", self.build(path, page(css=f'.a::after{{content:"{word}"}}'))[1] or "", f"{kind}: {mark!r} css")
            self.assertIn("leaves out", self.build(self.both()[0][1], page(self.wrap(f'<p title="{word}">x</p>')))[1] or "", f"{mark!r} attr")

    def test_an_svg_picture_inside_an_svg_picture_is_not_kept(self):
        import base64
        from urllib.parse import quote
        inner = "data:image/svg+xml," + quote(self.SVG, safe="")
        outer = f'<svg xmlns="http://www.w3.org/2000/svg"><image href="{inner}"/></svg>'
        src = "data:image/svg+xml;base64," + base64.b64encode(outer.encode()).decode()
        for kind, path in self.both():
            out, why = self.build(path, page(self.wrap(f'<img src="{src}">')))
            self.assertTrue(why or "walrus" not in (out or "").lower(), kind)
            self.assertNotIn("image/svg", (out or "").split("</style>", 2)[-1], kind)


class PictureMetadata(LeakPass2):
    """v240-leak2 (c): a picture's own metadata (PNG text chunks) in the posted page is dropped from the file."""

    def tagged(self):
        import base64
        import struct
        import zlib
        raw = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGD4DwABBAEAwS2OUAAAAABJRU5ErkJggg==")
        kind, data = b"tEXt", b"Comment\0Walrus budget cut"
        chunk = struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        i = raw.index(b"IDAT") - 4
        return "data:image/png;base64," + base64.b64encode(raw[:i] + chunk + raw[i:]).decode()

    def test_a_png_in_an_img_loses_its_text_chunks_in_client_and_internal_files(self):
        for kind, path in self.both():
            out, why = self.build(path, page(self.wrap(f'<img src="{self.tagged()}">')))
            self.assertIsNone(why, f"{kind}: {why}")
            src = re.search(r'<img[^>]*src="data:image/png;base64,([^"]+)"', out.split("</style>", 2)[-1])
            self.assertIsNotNone(src, kind)
            blob = base64.b64decode(src.group(1))
            self.assertNotIn(b"Walrus", blob, kind)
            self.assertNotIn(b"tEXt", blob, kind)
            self.assertTrue(blob.startswith(b"\x89PNG") and b"IDAT" in blob, kind)

    def test_a_client_file_refuses_a_css_picture_that_still_carries_metadata(self):
        css = f".page{{background:url({self.tagged()})}}"
        self.assertIsNotNone(self.build(self.client(), page(css=css))[1])


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
