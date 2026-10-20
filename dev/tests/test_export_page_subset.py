"""v2.5.0 page subset: a client report's posted export page is used only when its words are the saved, gated report's own.

The HTML and PDF export of a client report is the dashboard's own exported page (#226), posted with /api/report/export as `page`.
Before this fix the server checked that page only for item IDs, markers and the words of hidden rows: a page carrying another project's
hidden wording, the hidden owner's name or an internal section's text was written to the client's Reports folder. Now every section's
words must be made of that section's own shown strings (and the client view's fixed labels), the style rules may use only the dashboard
stylesheet's words, and a comment, a script or a foreign section refuses the page: the route then makes the plain file from the saved
report (`plain: true` with `plain_why`). Superseded by #239 step 3 (v2.5.2): a posted page is never used for a client report at all
(`page_ignored: true`); the file is client_snapshot.client_export's own render. The leak assertions are kept: none of the posted
words reach the file. Live routes, a throwaway vault, fictional data only.

Run: python3 dev/tests/test_export_page_subset.py        (the PDF cases need Chrome; skipped without it)
"""
import html
import re
import sqlite3
import sys
import unittest
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_report_export_save as S  # noqa: E402  (as a module: its own tests are not run again here)
from test_report_export_save import HAVE_CHROME  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))

WEEK = "2026-10-09"
FOREIGN = "Petra Quill will renegotiate the walrus supplier rebate quietly."
INTERNAL = "Walrus budget held back from the client for now."


def file_text(p):
    """The words of an exported file (a PDF's streams decompressed), lower case."""
    b = Path(p).read_bytes()
    if p.suffix == ".pdf":
        parts = [b]
        for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", b, re.S):
            try:
                parts.append(zlib.decompress(m.group(1)))
            except zlib.error:
                pass
        b = b"\n".join(parts)
        try:
            import pypdf
            b += "\n".join(pg.extract_text() or "" for pg in pypdf.PdfReader(str(p)).pages).encode()
        except Exception:
            pass
    return html.unescape(b.decode("utf-8", "ignore")).lower()


class PageSubset(unittest.TestCase):
    """Client report pages posted to the live export route (ExportSave's harness, without running its own tests again)."""
    setUpClass = classmethod(S.ExportSave.setUpClass.__func__)
    tearDownClass = classmethod(S.ExportSave.tearDownClass.__func__)
    post = S.ExportSave.post
    section = S.ExportSave.section
    reports = S.ExportSave.reports
    setUp = S.ExportSave.setUp

    def db(self):
        c = sqlite3.connect(self.v.root / "system/tracker.db")
        c.row_factory = sqlite3.Row
        return c

    def seed(self):
        """Another project's hidden action, and an ABC action the client report leaves out (its owner's name is the needle)."""
        con = self.db()
        if not con.execute("SELECT 1 FROM projects WHERE code='DEF'").fetchone():
            p = dict(con.execute("SELECT * FROM projects WHERE code='ABC'").fetchone())
            p.update(code="DEF", name="Digital Enablement")
            con.execute(f"INSERT INTO projects ({','.join(p)}) VALUES ({','.join('?' * len(p))})", list(p.values()))
        base = dict(con.execute("SELECT * FROM actions WHERE project='ABC' LIMIT 1").fetchone())
        r = dict(base, id="DEF-A-090", project="DEF", description="Renegotiate the walrus supplier rebate quietly",
                 owner="Petra Quill", client_visible=0)
        con.execute(f"INSERT OR REPLACE INTO actions ({','.join(r)}) VALUES ({','.join('?' * len(r))})", list(r.values()))
        h = dict(base, id="ABC-A-091", description="Hold the vendor penalty back", owner="Orla Brightwell", client_visible=0)
        con.execute(f"INSERT OR REPLACE INTO actions ({','.join(h)}) VALUES ({','.join('?' * len(h))})", list(h.values()))
        con.commit()
        con.close()

    def approved_client(self):
        """A clean, approved ABC client report: (its saved document, the shown sections)."""
        import creaite_doc
        self.seed()
        r = self.post("/api/report/draft", {"kind": "weekly", "code": "ABC", "week_ending": WEEK})
        self.assertTrue(r["ok"], r)
        self.section(r["doc"], "health")["text"] = "UAT start slipped two weeks."
        self.section(r["doc"], "summary")["text"] = INTERNAL
        self.assertTrue(self.post("/api/report/save", {"doc": r["doc"], "base_version": r["version"]})["ok"])
        a = self.post("/api/report/approve", {"kind": "weekly", "code": "ABC", "week_ending": WEEK, "force": True})
        self.assertTrue(a["ok"] or "awaiting review" in a["message"], a)
        r = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": WEEK})
        self.assertTrue(r["ok"], r)
        self.assertTrue(self.post("/api/report/save", {"doc": r["doc"], "base_version": r["version"]})["ok"])
        a = self.post("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True})
        self.assertTrue(a["ok"], a)
        doc = creaite_doc.read(self.v.root / a["path"])
        shown = [s for s in creaite_doc.clean(doc)["sections"] if not s.get("hidden")]
        text = str(creaite_doc.clean(doc)).lower()
        for needle in ("petra quill", "walrus", "orla brightwell"):
            self.assertNotIn(needle, text, "the saved client report must not hold the needle (else the test proves nothing)")
        return doc, shown

    def page(self, doc, body, sid=None, css=".page{color:#123}", version=None):
        sid = sid or self.first
        m = f'<div class="export-view"><div class="page"><section data-id="{sid}">{body}</section></div></div>'
        return {"html": m, "css": css, "palette": "creaite", "version": int(doc.get("version") or 0) if version is None else version}

    def export_page(self, fmt, page):
        return self.post("/api/report/export", {"kind": "client", "code": "ABC", "week_ending": WEEK, "fmt": fmt,
                                                "on_clash": "number", "page": page})

    def formats(self):
        return ["html"] + (["pdf"] if HAVE_CHROME else [])

    def assert_refused(self, label, page, needles, fmt):
        r = self.export_page(fmt, page)
        self.assertTrue(r.get("ok"), (label, fmt, r))
        self.assertTrue(r.get("page_ignored"), (label, fmt, "the posted page must never be used for a client report", r))
        got = file_text(self.v.root / r["path"])
        for n in needles:
            self.assertNotIn(n.lower(), got, (label, fmt, n))

    def test_a_page_with_words_the_saved_report_does_not_hold_is_refused(self):
        doc, shown = self.approved_client()
        self.first = shown[0]["id"]
        other = next(s["id"] for s in shown if s["id"] != self.first)
        cases = [
            ("another project's hidden wording", self.page(doc, f"<p>{FOREIGN}</p>"), ["Petra Quill", "walrus"]),
            ("the hidden owner's name", self.page(doc, "<p>Orla Brightwell leads this.</p>"), ["Orla Brightwell"]),
            ("an internal section's text", self.page(doc, f"<p>{INTERNAL}</p>"), ["walrus budget"]),
            ("arbitrary text", self.page(doc, "<p>Zanzibar quokka ledger.</p>"), ["quokka"]),
            ("text in an attribute", self.page(doc, '<p class="Petra Quill" data-type="walrus" style="--petra:quill">x</p>'),
             ["petra", "walrus", "quill"]),
            ("text in the style rules", self.page(doc, "<p></p>", css='.page::after{content:"Petra Quill walrus"}'),
             ["petra quill", "walrus"]),
            ("text in an HTML comment", self.page(doc, f"<p></p><!-- {FOREIGN} -->"), ["petra quill"]),
            ("a script", self.page(doc, f"<p></p><script>var x='{FOREIGN}'</script>"), ["petra quill", "<script"]),
            ("a second section with a foreign id",
             self.page(doc, f'</section><section data-id="zz_foreign"><p>{FOREIGN}</p>'), ["petra quill"]),
            ("another section's words under this section's id",
             self.page(doc, "<p>Orla Brightwell</p>", sid=other), ["orla brightwell"]),
            ("a version mismatch", self.page(doc, "<p></p>", version=int(doc.get("version") or 0) + 1), []),
        ]
        for fmt in self.formats():
            for label, page, needles in cases:
                with self.subTest(label=label, fmt=fmt):
                    self.assert_refused(label, page, needles, fmt)

    def test_control_even_the_page_the_dashboard_posts_is_not_used_the_server_renders(self):
        """v2.5.2 (#239 step 3): a page made of the saved report's own words is not used either: the file is the server's render of
        the checked snapshot (styled, never `plain`), and a class from the posted page never reaches it."""
        doc, shown = self.approved_client()
        self.first = shown[0]["id"]
        sec = next((s for s in shown if s["id"] == "risks"), None) or next(s for s in shown if s.get("type") == "table")
        page = {"html": f'<div id="v-clientreport" class="export-view"><div class="page"><section data-id="{sec["id"]}">'
                        f'<h2 class="wr-unknown">{html.escape(sec["heading"])}</h2></section></div></div>',
                "css": ".page{color:#123}.wr-posted td{padding:4px}", "palette": "creaite", "version": int(doc.get("version") or 0)}
        for fmt in self.formats():
            r = self.export_page(fmt, page)
            self.assertTrue(r.get("ok"), r)
            self.assertTrue(r.get("page_ignored"), (fmt, r))
            self.assertFalse(r.get("plain"), (fmt, r))
            if fmt == "html":
                text = (self.v.root / r["path"]).read_text(encoding="utf-8")
                self.assertNotIn("wr-unknown", text, "nothing from the posted page")
                self.assertNotIn(".wr-posted", text, "nothing from the posted style rules")


if __name__ == "__main__":
    unittest.main(verbosity=2)
