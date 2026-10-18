"""H5 / #218: the text section through the live server's report routes, and its picture home.

Run: python3 dev/tests/test_report_text_section_routes.py

On a live server in a throwaway vault (the harness of test_reports.ReportRoutes):
  - POST /api/report/image   a PNG or JPEG (2 MB at most) is filed in the project's Reports folder under `_images/` (filechange.py);
  - POST /api/report/images  the pictures of a text section as data addresses, for the editor to draw (read only);
  - a weekly draft with a text section saves, is kept in the file, exports to HTML and Word with its content and its picture;
  - a client report: a new client draft has none of the internal report's text sections, one written there is exported, one
    marked internal that got in is left out of every export.
"""
import base64
import re
import sys
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_report_text_section import ALL, freetext, png  # noqa: E402
from test_reports import ABC, ReportRoutes  # noqa: E402

WEEK = "2026-10-09"


def b64(raw):
    return base64.b64encode(raw).decode("ascii")


class TextSectionRoutes(unittest.TestCase):
    setUpClass = classmethod(ReportRoutes.setUpClass.__func__)
    tearDownClass = classmethod(ReportRoutes.tearDownClass.__func__)
    post = ReportRoutes.post
    section = ReportRoutes.section

    @property
    def reports(self):
        return self.v.root / ABC / "reports"

    def setUp(self):
        self.reports.mkdir(parents=True, exist_ok=True)
        for f in self.reports.glob("*"):
            if f.is_file():
                f.unlink()

    def upload(self, raw, name="site.png", code="ABC"):
        return self.post("/api/report/image", {"code": code, "name": name, "data": b64(raw)})

    def draft_with(self, *text_sections, week=WEEK):
        r = self.post("/api/report/draft", {"kind": "weekly", "code": "ABC", "week_ending": week})
        self.assertTrue(r["ok"], r)
        doc = r["doc"]
        self.section(doc, "health")["text"] = "UAT start slipped two weeks."
        at = next(i for i, s in enumerate(doc["sections"]) if s["id"] == "summary") + 1
        doc["sections"][at:at] = list(text_sections)
        doc["layout"]["order"] = [s["id"] for s in doc["sections"]]
        s = self.post("/api/report/save", {"doc": doc, "base_version": r["version"]})
        self.assertTrue(s["ok"], s)
        return doc

    # ── the picture's home ──
    def test_a_picture_is_filed_under_images_in_the_reports_folder(self):
        raw = png(30, 12)
        r = self.upload(raw, "Site photo.png")
        self.assertTrue(r["ok"], r)
        self.assertRegex(r["ref"], r"^_images/\d{4}-\d{2}-\d{2}-site-photo\.png$")
        self.assertEqual((self.reports / r["ref"]).read_bytes(), raw)

    def test_the_same_name_twice_gets_a_number_and_nothing_is_overwritten(self):
        a, b = self.upload(png(5, 5, (1, 2, 3, 255)), "x.png"), self.upload(png(6, 6, (4, 5, 6, 255)), "x.png")
        self.assertNotEqual(a["ref"], b["ref"])
        self.assertEqual((self.reports / a["ref"]).read_bytes(), png(5, 5, (1, 2, 3, 255)))

    def test_only_png_or_jpeg_up_to_two_megabytes(self):
        self.assertFalse(self.upload(b"GIF89a....")["ok"])
        self.assertFalse(self.upload(b"<svg xmlns='http://www.w3.org/2000/svg'/>", "x.svg")["ok"])
        big = self.upload(b"\x89PNG\r\n\x1a\n" + b"0" * (2 * 1024 * 1024 + 1))
        self.assertFalse(big["ok"], big)
        self.assertIn("2 MB", big["message"])
        self.assertTrue(self.upload(b"\xff\xd8\xff\xe0" + b"0" * 64, "j.jpg")["ok"])

    def test_a_bad_project_or_bad_data_is_refused(self):
        self.assertFalse(self.upload(png(4, 4), code="NOPE")["ok"])
        self.assertFalse(self.post("/api/report/image", {"code": "ABC", "name": "x.png", "data": "not base64!!"})["ok"])

    def test_pictures_are_read_back_by_reference_and_only_that_shape(self):
        raw = png(7, 7)
        ref = self.upload(raw)["ref"]
        r = self.post("/api/report/images", {"code": "ABC", "refs": [ref, "../x.png", "/etc/hosts", "_images/missing.png", "_images/../../x.png"]})
        self.assertTrue(r["ok"], r)
        self.assertEqual(list(r["images"]), [ref])
        self.assertEqual(base64.b64decode(r["images"][ref].split(",", 1)[1]), raw)

    # ── saving and exporting ──
    def test_a_text_section_is_saved_with_the_report_and_comes_back_unchanged(self):
        ref = self.upload(png(40, 20, (0, 150, 0, 255)))["ref"]
        text = ALL.replace("_images/2026-10-18-site.png", ref) + "\nBefore </script> after\n"
        self.draft_with(freetext(text), week="2026-09-25")
        back = self.post("/api/report/draft", {"kind": "weekly", "code": "ABC", "week_ending": "2026-09-25"})
        self.assertEqual(back["where"], "draft")
        s = self.section(back["doc"], "free_1")
        self.assertEqual((s["type"], s["heading"], s["text"]), ("freetext", "Vendor notes", text))
        order = [x["id"] for x in back["doc"]["sections"]]
        self.assertEqual(order[order.index("summary") + 1], "free_1")

    def test_html_and_word_exports_carry_the_text_and_the_picture(self):
        ref = self.upload(png(40, 20, (0, 150, 0, 255)))["ref"]
        self.draft_with(freetext(ALL.replace("_images/2026-10-18-site.png", ref)), week="2026-10-02")
        h = self.post("/api/report/export", {"kind": "weekly", "code": "ABC", "week_ending": "2026-10-02", "fmt": "html", "on_clash": "number"})
        self.assertTrue(h["ok"], h)
        page = (self.v.root / h["path"]).read_text(encoding="utf-8")
        self.assertIn("<h2>Vendor notes</h2>", page)
        self.assertIn("data:image/png;base64,", page)
        self.assertRegex(page, r"<table[^>]*>.*Mia Hale")
        self.assertNotIn('id="creaite-data"', page, "the HTML export has no data block")
        w = self.post("/api/report/export", {"kind": "weekly", "code": "ABC", "week_ending": "2026-10-02", "fmt": "docx", "on_clash": "number"})
        self.assertTrue(w["ok"], w)
        with zipfile.ZipFile(self.v.root / w["path"]) as z:
            xml = z.read("word/document.xml").decode("utf-8")
            self.assertTrue([n for n in z.namelist() if n.startswith("word/media/")])
        text = re.sub(r"<[^>]+>", " ", xml)
        for needle in ("Vendor notes", "Heading one", "def tidy(x):", "Mia Hale", "open task"):
            self.assertIn(needle, text)

    # ── the client rule ──
    def approve_internal(self, week):
        a = self.post("/api/report/approve", {"kind": "weekly", "code": "ABC", "week_ending": week, "force": True})
        self.assertTrue(a["ok"] or "awaiting review" in a["message"], a)

    def test_a_new_client_draft_has_none_of_the_internal_text_sections(self):
        self.draft_with(freetext("INTERNAL-ONLY walrus", heading="Internal musings"), week="2026-09-18")
        self.approve_internal("2026-09-18")
        r = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": "2026-09-18"})
        self.assertTrue(r["ok"], r)
        self.assertFalse([s for s in r["doc"]["sections"] if s["type"] == "freetext"])
        self.assertNotIn("walrus", str(r["doc"]))

    def test_a_text_section_written_in_the_client_report_is_exported_and_an_internal_one_is_not(self):
        self.draft_with(week="2026-09-11")
        self.approve_internal("2026-09-11")
        r = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": "2026-09-11"})
        doc = r["doc"]
        mine = freetext("Hello client, written for you.", heading="A note for you", sid="free_9", audience="client")
        slipped = freetext("INTERNAL-ONLY walrus", heading="Internal musings", sid="free_8", audience="internal")
        doc["sections"] += [mine, slipped]
        doc["layout"]["order"] = [s["id"] for s in doc["sections"]]
        s = self.post("/api/report/save", {"doc": doc, "base_version": r["version"]})
        self.assertTrue(s["ok"], s)
        e = self.post("/api/report/export", {"kind": "client", "code": "ABC", "week_ending": "2026-09-11", "fmt": "html", "on_clash": "number"})
        self.assertTrue(e["ok"], e)
        page = (self.v.root / e["path"]).read_text(encoding="utf-8")
        self.assertIn("Hello client, written for you.", page)
        self.assertNotIn("walrus", page)
        self.assertNotIn("Internal musings", page)


if __name__ == "__main__":
    unittest.main(verbosity=2)
