"""Tests for #227: the Word writer matches the report as edited (dev/sprints/export-227-word-brief.md, acceptance checks 1 to 10).

Run: python3 dev/tests/test_word_export_227.py
Each test is named test_check_NN_... for the brief's check NN. They call creaite_doc.word_export on a fictional weekly document with the
pictures drawn by a stub (so no Chrome is needed), and read the .docx's XML. Two tests need other programs and skip, saying so, when
they are missing: Chrome (the real pictures) and LibreOffice (`soffice`: the file converted to a PDF, the text in order across pages).
A skipped test is not a pass.
"""
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
import zlib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "system" / "scripts"))
import creaite_doc  # noqa: E402
import docx_tools  # noqa: E402
import launch  # noqa: E402
import paths  # noqa: E402

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
ISO = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


def png(w, h, rgba=(30, 60, 200, 255)):
    """A solid PNG of the size asked for."""
    row = b"\x00" + bytes(rgba) * w

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(row * h)) + chunk(b"IEND", b""))


ITEMS = {
    "ABC-M-001": {"table": "milestones", "id": "ABC-M-001", "title": "Design sign-off", "baseline_date": "2026-09-28",
                  "forecast_date": "2026-09-28", "actual_date": "2026-09-25", "status": "Done", "percent_complete": 100},
    "ABC-M-002": {"table": "milestones", "id": "ABC-M-002", "title": "Go-live", "baseline_date": "2026-11-11",
                  "forecast_date": "2026-11-25", "status": "Planned", "percent_complete": 40},
    "ABC-M-003": {"table": "milestones", "id": "ABC-M-003", "title": "Leftout milestone", "baseline_date": "2026-12-01",
                  "forecast_date": "2026-12-01", "status": "Planned"},
    "ABC-M-004": {"table": "milestones", "id": "ABC-M-004", "title": "Confidential vendor exit", "baseline_date": "2026-12-15",
                  "forecast_date": "2026-12-15", "status": "Planned", "client_visible": 0},
    "ABC-M-005": {"table": "milestones", "id": "ABC-M-005", "title": "Zanzibar exit plan", "baseline_date": "2027-01-15",
                  "forecast_date": "2027-01-15", "status": "Planned"},       # no client_visible, as a saved client report's items
    "ABC-002": {"table": "raid", "id": "ABC-002", "title": "Vendor capacity", "response_action": "Book a second crew"},
    "ABC-A-005": {"table": "actions", "id": "ABC-A-005", "title": "Send the plan", "due_date": "2026-10-15"},
}


def sections(tmp):
    return [
        {"id": "header", "type": "header", "heading": "Weekly report", "hidden": False, "text": "",
         "data": {"label": "Weekly report · Internal",
                  "logos": [{"kind": "firm", "path": str(tmp / "firm.png")}, {"kind": "client", "path": str(tmp / "ABC-client.svg")}]}},
        {"id": "health", "type": "health", "heading": "Health", "hidden": False, "text": "The harbour migration slipped.",
         "data": {"flag": "Off track", "trend": [{"date": d, "flag": f}
                                                 for d, f in (("2026-09-11", "On track"), ("2026-09-18", "On track"),
                                                              ("2026-09-25", "At risk"), ("2026-10-02", "At risk"),
                                                              ("2026-10-09", "At risk"))],
                  "last_week": {"flag": "At risk", "date": "2026-10-09"}}},
        {"id": "glance", "type": "figures", "heading": "At a glance", "hidden": False,
         "figures": [{"key": "next_milestone", "label": "Next milestone", "value": "Go-live", "note": "25-11-2026", "shown": True},
                     {"key": "overdue", "label": "Overdue actions", "value": "3", "note": "", "shown": True},
                     {"key": "high_risks", "label": "High risks open", "value": "2", "note": "", "shown": True},
                     {"key": "decisions_needed", "label": "Decisions needed", "value": "0", "note": "", "shown": True},
                     {"key": "x", "label": "Hidden figure", "value": "zebrafigure", "shown": False}]},
        {"id": "summary", "type": "text", "heading": "Executive summary", "hidden": False, "text": ""},
        {"id": "asks", "type": "table", "heading": "What we need from people", "hidden": False,
         "columns": [{"key": "ask", "label": "Ask"}, {"key": "from", "label": "From"}], "rows": []},
        {"id": "milestones", "type": "timeline", "heading": "Milestones", "hidden": False, "text": "",
         "data": {"timeline": ["ABC-M-001", "ABC-M-002", "ABC-M-003", "ABC-M-004", "ABC-M-005"], "milestones": ["ABC-M-001", "ABC-M-002"]}},
        {"id": "this_week", "type": "text", "heading": "This week", "hidden": False,
         "text": "**Done:** the plan.\n\n- [ ] book room\n- [x] order kit\n- plain point\n\n"
                 "![Site photo](images/site.png)\n\n![Lost photo](images/lost.png)"},
        {"id": "risks", "type": "table", "heading": "Risks and issues", "hidden": False,
         "columns": [{"key": "id", "label": "ID"}, {"key": "risk", "label": "Risk or issue"},
                     {"key": "priority", "label": "Priority"}, {"key": "owner", "label": "Owner"}],
         "rows": [{"ref": "ABC-002", "shown": True, "cells": {"id": "ABC-002", "risk": "Risk: Vendor capacity", "priority": "Urgent",
                                                              "owner": "Sam Patel"}},
                  {"ref": "ABC-009", "shown": False, "cells": {"id": "ABC-009", "risk": "Secret quarry", "priority": "Low",
                                                               "owner": "Ola"}}]},
        {"id": "overdue", "type": "table", "heading": "Overdue actions", "hidden": False,
         "columns": [{"key": "id", "label": "ID"}, {"key": "action", "label": "Action"}, {"key": "owner", "label": "Owner"},
                     {"key": "due", "label": "Due"}],
         "rows": [{"ref": "ABC-A-005", "shown": True, "cells": {"id": "ABC-A-005", "action": "Send the plan", "owner": "Mia Hale",
                                                                "due": "15-10-2026"}}]},
        {"id": "secret", "type": "text", "heading": "Secret section", "hidden": True, "text": "walrus"},
        {"id": "current_state", "type": "panes", "heading": "Current state", "hidden": False,
         "panes": [{"title": "", "text": "Cutover rehearsal booked."}]},
    ]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="w227-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.drafts = self.tmp / "drafts"
        self.drafts.mkdir()
        old = paths.DRAFTS
        paths.DRAFTS = self.drafts
        self.addCleanup(setattr, paths, "DRAFTS", old)
        self.sizes = []
        self.real_pic = getattr(creaite_doc, "picture_png", None)

        # v2.5.0 leak fix: a picture is read only as `images/<name>` under the project's own folder (never an absolute path), so the
        # test's project folder is its temp folder
        real_dir = paths.project_dir
        paths.project_dir = lambda code, _t=self.tmp: _t
        self.addCleanup(setattr, paths, "project_dir", real_dir)
        # 2.5.1 M1 (v251-logofix): a header logo is drawn only from the project's own logo files (report_doc.logos: firm.<ext> and
        # <CODE>-client.<ext> in paths.REPORT_LOGOS, stored relative to the vault root), never from a path the document names; so the
        # test's vault root and logos folder are its temp folder, and the logos are written there under those names
        for name, value in (("ROOT", self.tmp.resolve()), ("REPORT_LOGOS", self.tmp)):
            self.addCleanup(setattr, paths, name, getattr(paths, name))
            setattr(paths, name, value)
        self.svgs = []
        # the tracker's client-safe milestones (M-004 and M-005 are not): the writer re-reads them and fails closed (LEAK 3)
        real_safe = creaite_doc.client_safe_ids
        creaite_doc.client_safe_ids = lambda code: {"ABC-M-001", "ABC-M-002", "ABC-M-003"}
        self.addCleanup(setattr, creaite_doc, "client_safe_ids", real_safe)

        def fake(svg, w, h, **kw):
            self.svgs.append(svg)
            self.sizes.append((w, h))
            return png(int(w), int(h))
        creaite_doc.picture_png = fake
        self.addCleanup(setattr, creaite_doc, "picture_png", self.real_pic)
        (self.tmp / "images").mkdir()
        (self.tmp / "images" / "site.png").write_bytes(png(40, 20, (0, 150, 0, 255)))
        (self.tmp / "firm.png").write_bytes(png(60, 20))
        (self.tmp / "ABC-client.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" width="80" height="30" viewBox="0 0 80 30">'
                                             '<rect width="80" height="30" fill="red"/></svg>')

    def doc(self, kind="weekly", **kw):
        d = creaite_doc.new(kind, "ABC", "Weekly report" if kind == "weekly" else "Client report", "2026-10-16",
                            sections(self.tmp), items=ITEMS, **kw)
        d["project_name"] = "Example Programme"
        return d

    def build(self, doc=None):
        doc = doc or self.doc()
        self.out = self.tmp / "out.docx"
        creaite_doc.word_export(doc, self.out)
        self.parts = {i.filename: raw for i, raw in docx_tools.read_parts(self.out)}
        self.xml = self.parts["word/document.xml"].decode("utf-8")
        self.root = ET.fromstring(self.xml)
        return doc

    def paras(self):
        """Body paragraphs (outside tables) as text."""
        body = self.root.find(W + "body")
        return ["".join(t.text or "" for t in p.iter(W + "t")) for p in body.findall(W + "p")]

    def tables(self):
        """Each table as rows of cell text."""
        return [[["".join(t.text or "" for t in c.iter(W + "t")) for c in r.findall(W + "tc")] for r in tb.findall(W + "tr")]
                for tb in self.root.iter(W + "tbl")]

    def alltext(self):
        return "\n".join(self.paras()) + "\n" + "\n".join(" | ".join(r) for t in self.tables() for r in t)

    def table_with(self, header):
        return next((t for t in self.tables() if header in t[0]), None)

    def drawings(self):
        return len(self.root.findall(".//" + W + "drawing"))


class MetadataAndNames(Base):
    """v240-leak2 (c) and (d): a picture's own metadata (PNG text chunks, JPEG EXIF and comments) and its file name never reach a Word
    file; the picture's name in the file is neutral."""
    NEEDLE = b"Walrus budget cut"

    @staticmethod
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    def tagged_png(self, w, h):
        raw = png(w, h)
        extra = (self.chunk(b"tEXt", b"Comment\0" + self.NEEDLE) + self.chunk(b"iTXt", b"k\0\0\0\0\0" + self.NEEDLE)
                 + self.chunk(b"zTXt", b"k\0\0" + zlib.compress(self.NEEDLE)) + self.chunk(b"eXIf", b"Exif" + self.NEEDLE)
                 + self.chunk(b"tIME", b"\x07\xea\x0a\x12\0\0\0"))
        i = raw.index(b"IDAT") - 4
        return raw[:i] + extra + raw[i:]

    def test_word_export_strips_metadata_from_a_logo_and_a_text_section_picture(self):
        (self.tmp / "firm.png").write_bytes(self.tagged_png(60, 20))
        (self.tmp / "images" / "site.png").write_bytes(self.tagged_png(40, 20))
        for kind in ("weekly", "client"):
            self.build(self.doc(kind))
            media = [self.parts[n] for n in self.parts if n.startswith("word/media/")]
            self.assertTrue(media)
            for blob in media:
                self.assertNotIn(self.NEEDLE, blob, kind)
                self.assertNotIn(b"tEXt", blob, kind)
                self.assertNotIn(b"eXIf", blob, kind)
            self.assertIn(png(60, 20), media, f"{kind}: the picture itself is kept, as its pixels")

    def test_a_jpeg_loses_its_exif_and_comment_but_keeps_its_picture(self):
        def seg(marker, body):
            return bytes([0xFF, marker]) + struct.pack(">H", len(body) + 2) + body
        jpg = (b"\xff\xd8" + seg(0xE0, b"JFIF\0\x01\x01\0\0\x01\0\x01\0\0") + seg(0xE1, b"Exif\0\0" + self.NEEDLE)
               + seg(0xED, b"Photoshop 3.0\0" + self.NEEDLE) + seg(0xFE, self.NEEDLE)
               + seg(0xC0, b"\x08\x00\x14\x00\x28\x01\x01\x11\x00") + seg(0xDA, b"\x01\x01\x00\x00\x3f\x00") + b"\x12\x34\xff\xd9")
        out = docx_tools.strip_image_metadata(jpg)
        self.assertNotIn(self.NEEDLE, out)
        self.assertEqual(docx_tools.image_size(out), (40, 20))
        self.assertTrue(out.startswith(b"\xff\xd8") and out.endswith(b"\x12\x34\xff\xd9"))

    def test_the_picture_name_in_the_word_file_is_neutral_never_the_file_name(self):
        (self.tmp / "firm.png").write_bytes(png(60, 20))
        for kind in ("weekly", "client"):
            self.build(self.doc(kind))
            names = re.findall(r'<(?:wp:docPr|pic:cNvPr)[^>]*?name="([^"]*)"', self.xml) + re.findall(r'descr="([^"]*)"', self.xml)
            names = [n for n in names if n]
            self.assertTrue(names, kind)
            for n in names:
                self.assertRegex(n, r"^Picture \d+$", kind)
            self.assertNotIn("firm.png", self.xml)
            self.assertNotIn("site.png", self.xml)


class Checks(Base):
    def test_check_01_title_block_once_and_the_reports_logos(self):
        self.build()
        paras = self.paras()
        self.assertEqual([p for p in paras if p.strip().lower() == "weekly report"], ["Weekly Report"], paras[:10])
        self.assertIn("Example Programme", paras[:8])
        self.assertTrue(any(p.startswith("Week ending") for p in paras[:10]))
        media = [n for n in self.parts if n.startswith("word/media/")]
        self.assertIn(png(60, 20), [self.parts[n] for n in media], "the report's firm logo is in the file")
        self.assertFalse([n for n in self.parts if n.lower().endswith(".svg")], "an SVG logo becomes a PNG")
        self.assertTrue(any(abs(w / h - 80 / 30) < 0.1 for w, h in self.sizes), "the SVG logo was drawn to a PNG at its proportions")
        self.assertGreaterEqual(self.drawings(), 6)       # wordmark, 2 logos, health strip, timeline, site photo

    def test_check_02_health_one_label_reason_last_week_and_the_strip(self):
        self.build()
        text = self.alltext()
        self.assertEqual(len(re.findall(r"OFF TRACK", text, re.I)), 1, text[:800])
        self.assertIn("The harbour migration slipped.", text)
        self.assertIn("Last week: At risk (09-10)", text)
        at = self.xml.index("harbour migration")
        self.assertIn("<w:drawing", self.xml[at - 5000:at + 4000], "the six-week strip is a picture beside the health text")

    def test_check_03_at_a_glance_is_a_small_table_overdue_red(self):
        self.build()
        t = self.table_with("Overdue actions")
        self.assertIsNotNone(t, self.tables())
        self.assertEqual(len(t[0]), 4)
        self.assertEqual(t[1][1], "3")
        self.assertNotIn("Overdue actions:", "\n".join(self.paras()))
        self.assertNotIn("Hidden figure", self.alltext())
        self.assertRegex(self.xml, r'<w:color w:val="C0392B"/>(?:(?!</w:r>).)*<w:t[^>]*>3</w:t>')

    def test_check_04_milestones_picture_and_table(self):
        self.build()
        t = self.table_with("Milestone")
        self.assertEqual(t[0], ["Milestone", "Agreed", "Expected", "Progress", "State"])
        self.assertEqual(len(t), 3)
        golive = next(r for r in t[1:] if "Go-live" in r[0])
        self.assertEqual(golive[1:4], ["11-11-2026", "25-11-2026 (+14)", "40%"])
        done = next(r for r in t[1:] if "Design" in r[0])
        self.assertIn("achieved", done[2])
        self.assertIn("ACHIEVED", done[4])
        self.assertNotRegex(self.alltext(), ISO)
        self.assertNotIn("Leftout milestone", " ".join(" ".join(r) for r in t), "left out of the list")
        i = self.xml.index("Milestones")
        self.assertIn("<w:drawing", self.xml[i:i + 4000], "the timeline is a picture under its heading")

    def test_check_05_tables_full_columns_priority_late_and_empty_sentence(self):
        self.build()
        r = self.table_with("Response")
        self.assertEqual(r[0], ["ID", "Risk or issue", "Priority", "Owner", "Response"])
        self.assertEqual(r[1][2], "URGENT")
        self.assertEqual(r[1][4], "Book a second crew")
        self.assertEqual(self.table_with("Late")[1][-1], "1 day")
        self.assertIsNone(self.table_with("Ask"), "an empty table is the sentence, not a header-only table")
        self.assertIn("Nothing is needed from anyone this week.", self.paras())
        self.assertIn('w:fill="1E1F1E"', self.xml)      # the template's header style

    def test_check_06_text_kept_no_empty_heading_images_never_dropped(self):
        self.build()
        paras = self.paras()
        self.assertNotIn("Executive summary", [p.title() for p in paras] + paras, "an empty section has no heading")
        self.assertNotIn("EXECUTIVE SUMMARY", paras)
        text = "\n".join(paras)
        self.assertIn("book room", text)
        self.assertRegex(text, "☐\\s*book room")
        self.assertRegex(text, "☑\\s*order kit")
        self.assertIn("Cutover rehearsal booked.", text)
        self.assertNotIn("Where we are", text)
        self.assertRegex(self.xml, r"<w:b/>(?:(?!</w:r>).)*<w:t[^>]*>Done:")
        media = [self.parts[n] for n in self.parts if n.startswith("word/media/")]
        self.assertIn((self.tmp / "images" / "site.png").read_bytes(), media, "the placed picture is in the file")
        self.assertIn("lost.png", text, "a picture that can't be found is named, not dropped silently")

    def test_check_07_left_out_content_is_absent(self):
        self.build()
        text = self.alltext()
        for gone in ("walrus", "Secret", "zebrafigure", "Hidden figure", "Leftout", "quarry"):
            self.assertNotIn(gone, text)

    def test_check_08_client_report_same_writer(self):
        self.build(self.doc("client", audience="client", client="Harbour Board"))
        self.assertEqual([p for p in self.paras() if p.strip().lower() in ("status report", "client report", "weekly report")].__len__(), 1)
        self.assertIsNotNone(self.table_with("Late"))
        self.assertIsNotNone(self.table_with("Milestone"))
        self.assertNotIn("walrus", self.alltext())
        self.assertNotRegex(self.alltext(), ISO)

    def test_check_08b_a_milestone_that_is_not_client_safe_is_never_named_in_a_client_export(self):
        self.build(self.doc("client", audience="client", client="Harbour Board"))
        every = self.xml + " ".join(self.svgs) + " ".join(n + str(v) for n, v in self.parts.items() if n.endswith(".xml"))
        self.assertNotIn("Confidential vendor", every, "text, picture alt text or the picture's drawing")
        self.assertNotIn("ABC-M-004", every)
        self.assertTrue(any("Go-live" in v for v in self.svgs), "the client-safe milestones are still drawn")

    def test_leak3_a_milestone_with_no_client_visible_flag_is_not_drawn_in_a_client_export(self):
        """p240-leakfix LEAK 3: report_doc._client_item never stores client_visible; the saved items have none, so only the tracker's
        client-safe set may be drawn (picture and table), and a tracker that can't be read draws none."""
        self.build(self.doc("client", audience="client", client="Harbour Board"))
        every = self.xml + " ".join(self.svgs)
        self.assertNotIn("Zanzibar", every)
        self.assertTrue(any("Go-live" in v for v in self.svgs))
        creaite_doc.client_safe_ids = lambda code: set()
        self.svgs.clear()
        self.build(self.doc("client", audience="client", client="Harbour Board"))
        self.assertFalse(any("Go-live" in v for v in self.svgs), "fail closed")
        self.svgs.clear()
        self.build()
        self.assertTrue(any("Zanzibar" in v for v in self.svgs), "an internal export still draws it")

    def test_leak2_a_client_export_names_a_milestone_by_its_title_never_by_its_id(self):
        """p240-leakfix LEAK 2: no item ID anywhere in a client Word file (every XML part); the internal one keeps it."""
        secs = [x for x in sections(self.tmp) if x["type"] not in ("table",)]
        doc = creaite_doc.new("client", "ABC", "Client report", "2026-10-16", secs, items=ITEMS, audience="client",
                              client="Harbour Board")
        doc["project_name"] = "Example Programme"
        self.build(doc)
        ms = self.table_with("Milestone")
        self.assertIn("Design sign-off", [r[0] for r in ms])
        every = " ".join(self.svgs) + " ".join(v.decode("utf-8", "replace") for n, v in self.parts.items() if n.endswith((".xml", ".rels")))
        self.assertEqual(re.findall(r"[A-Z0-9]{3,7}-[A-Z]-\d+", every), [])
        self.build()
        self.assertIn("ABC-M-001 Design sign-off", [r[0] for r in self.table_with("Milestone")])

    def test_logo1_a_bad_logo_file_is_skipped_and_never_fails_the_export(self):
        """p240-leakfix LOGO 1: a bare PNG header (what the old save accepted) and a zero-height PNG used to fail every export."""
        (self.tmp / "firm.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        (self.tmp / "ABC-client.svg").write_bytes(b"not a picture")
        self.build()
        self.assertFalse([n for n in self.parts if n.startswith("word/media/") and self.parts[n][:8] == b"\x89PNG\r\n\x1a\n"
                          and len(self.parts[n]) == 8], "the bad file is not in the package")
        (self.tmp / "firm.png").write_bytes(png(60, 20)[:16] + struct.pack(">II", 60, 0) + png(60, 20)[24:])
        self.build()

    def test_logo7_current_behaviour_an_internal_weekly_export_carries_the_client_and_partner_logos(self):
        """LOGO 7 is Alan's question, not decided here. This documents what happens now: the weekly layout's logo choice
        (header section, data.logos) decides, and the fixture's choice (firm and client) puts both in an INTERNAL weekly file.
        If Alan says internal reports carry no client or partner logo, the change is one line in report_doc.py (the weekly layout's
        default logos / creaite_doc.Ctx.logos for audience 'internal') and this test then asserts the opposite."""
        self.build()
        media = [self.parts[n] for n in self.parts if n.startswith("word/media/")]
        self.assertIn(png(60, 20), media, "the firm logo")
        self.assertTrue(any(abs(w / h - 80 / 30) < 0.1 for w, h in self.sizes), "the client logo (an SVG drawn to a PNG)")

    def test_check_08c_a_client_timeline_draws_what_the_screen_does_a_left_out_one_stays_in_the_picture_not_the_table(self):
        self.build(self.doc("client", audience="client", client="Harbour Board"))
        self.assertTrue(any("Leftout milestone" in v for v in self.svgs))
        self.assertNotIn("Leftout", self.alltext(), "the list leaves it out")

    def test_check_08d_an_internal_export_draws_every_milestone(self):
        self.build()
        self.assertTrue(any("Leftout milestone" in v and "Confidential vendor exit" in v for v in self.svgs))
        self.assertNotIn("Leftout", self.alltext(), "but the list still leaves it out")

    def test_check_09_no_guarded_file_changed(self):
        # live_server.py is left out: Jarvis applied the approved per-route body caps to it in the v2.4.0 guarded commit (Alan, 18-10-2026);
        # the Word writer itself never touches a guarded file. reach.py is left out too: Jarvis applied the approved "ask creaite never
        # writes reports" refusal to it (commit 6249e5a4, Alan, 19-10-2026)
        guarded = ("tracker.py", "filechange.py", "permissions.py", "backup.py", "update.py")
        r = subprocess.run(["git", "diff", "--name-only", "origin/v234-final", "HEAD"], cwd=REPO, capture_output=True, text=True)
        if r.returncode != 0:
            self.skipTest("git history for origin/v234-final isn't available here: check 9 NOT run")
        touched = [f for f in r.stdout.split() if f.startswith("system/scripts/") and Path(f).name in guarded]
        self.assertEqual(touched, [])

    def test_check_10_package_is_sound_and_opens_without_repair(self):
        self.build()
        for name, raw in self.parts.items():
            if name.endswith((".xml", ".rels")):
                ET.fromstring(raw)
        rels = ET.fromstring(self.parts["word/_rels/document.xml.rels"])
        ids = {r.get("Id"): r.get("Target") for r in rels}
        used = set(re.findall(r'r:embed="([^"]+)"', self.xml))
        self.assertTrue(used <= set(ids), used - set(ids))
        for rid in used:
            self.assertIn("word/" + ids[rid], self.parts)
        self.assertIn('Extension="png"', self.parts["[Content_Types].xml"].decode())
        docpr = re.findall(r'<wp:docPr id="(\d+)"', self.xml)
        self.assertEqual(len(docpr), len(set(docpr)), "picture ids must be unique")
        self.assertNotIn("{{", self.xml)
        with zipfile.ZipFile(self.out) as z:
            self.assertIsNone(z.testzip())

    @unittest.skipUnless(shutil.which("soffice") or Path("/Applications/LibreOffice.app").exists(),
                         "LibreOffice (soffice) is not installed: the render-to-PDF check was NOT run")
    def test_check_10b_libreoffice_render_text_in_order(self):
        self.build()
        soffice = shutil.which("soffice") or "/Applications/LibreOffice.app/Contents/MacOS/soffice"
        subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(self.tmp), str(self.out)],
                       check=True, capture_output=True, timeout=180)
        from pypdf import PdfReader
        text = "\n".join(p.extract_text() for p in PdfReader(str(self.tmp / "out.pdf")).pages).upper()
        at = -1
        for h in ("EXAMPLE PROGRAMME", "HEALTH", "AT A GLANCE", "MILESTONES", "THIS WEEK", "RISKS AND ISSUES", "OVERDUE ACTIONS"):
            nxt = text.find(h, at + 1)
            self.assertGreater(nxt, at, f"{h} missing or out of order")
            at = nxt

    @unittest.skipUnless(launch.find_chrome(), "Chrome is not installed: the real-picture check was NOT run")
    def test_check_02_04_real_pictures_from_chrome(self):
        creaite_doc.picture_png = self.real_pic
        self.build()
        media = [raw for n, raw in self.parts.items() if n.startswith("word/media/")]
        self.assertGreaterEqual(len(media), 5)
        self.assertTrue(all(m[:8] == b"\x89PNG\r\n\x1a\n" for m in media))


if __name__ == "__main__":
    unittest.main(verbosity=2)
