"""A Markdown picture line in a report can never pull a file from outside its own picture store into a Word file (v2.5.0 leak fix).

Run: python3 dev/tests/test_report_picture_paths.py

`![t](/abs/outside.png)` or `![t](../../outside.png)` in a health, text, table, timeline or Current state section of a client report
was resolved against the project folder and embedded in the client Word file. Now:
  - a client document reads only its own pictures (`_images/<name>`, creaite_doc.text_image);
  - an internal document also reads `images/<name>` from the project's own images folder, never through a symlink, `..`, an
    absolute path, a URL or a drive letter (paths.image_file; paths.resolve_image never leaves the project folder);
  - saving a client draft (/api/report/save, report_doc.save_draft) drops a picture line that names anything else.
Fictional data only.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_report_exports import ABC, ITEMS, Base  # noqa: E402
from test_word_export_227 import png  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
import docx_tools  # noqa: E402

OUT_SIZE, OWN_SIZE, LINK_SIZE = (77, 13), (31, 17), (59, 11)


def media_sizes(path):
    """The pixel sizes of every picture in a Word file."""
    with zipfile.ZipFile(path) as z:
        return [list(docx_tools.image_size(z.read(n))) for n in z.namelist() if n.startswith("word/media/")]


def bad_refs(outside):
    """Picture references that name a file outside the project's pictures."""
    up = "../" * 12 + str(outside).lstrip("/")
    return [str(outside), up, "../../../outside.png", "images/../../../outside.png", "file://" + str(outside),
            "C:/outside.png", "images\\..\\..\\outside.png"]


def sections_with(lines, current="Booked."):
    md = "\n".join(f"![leak]({r})" for r in lines)
    return [
        {"id": "health", "type": "health", "heading": "Health", "default_heading": "Health", "hidden": False,
         "text": f"Fine.\n\n{md}", "data": {"flag": "On track"}},
        {"id": "summary", "type": "text", "heading": "Summary", "default_heading": "Summary", "hidden": False, "text": f"Words.\n\n{md}"},
        {"id": "risks", "type": "table", "heading": "Risks", "default_heading": "Risks", "hidden": False, "text": f"Intro.\n\n{md}",
         "columns": [{"key": "id", "label": "ID"}], "rows": [{"ref": "ABC-002", "cells": {"id": "ABC-002"}, "shown": True}]},
        {"id": "milestones", "type": "timeline", "heading": "Milestones", "default_heading": "Milestones", "hidden": False,
         "text": f"Two.\n\n{md}", "data": {"milestones": ["ABC-M-001"]}},
        {"id": "current_state", "type": "panes", "heading": "Current state", "default_heading": "Current state", "hidden": False,
         "panes": [{"title": "Where", "text": f"{current}\n\n{md}"}]}]


class WordPictures(Base):
    def setUp(self):
        super().setUp()
        self.out = Path(tempfile.mkdtemp(prefix="pic-outside-"))
        self.addCleanup(shutil.rmtree, self.out, True)
        self.outside = self.out / "outside.png"
        self.outside.write_bytes(png(*OUT_SIZE))
        (self.v.root / "outside.png").write_bytes(png(*OUT_SIZE))           # the vault root, three levels up from the project
        self.images = self.v.root / ABC / "images"
        self.images.mkdir(parents=True, exist_ok=True)
        (self.images / "own.png").write_bytes(png(*OWN_SIZE))

    def word(self, audience, secs):
        kind = "weekly" if audience == "internal" else "client"
        r = self.py("from pathlib import Path\nimport paths\n"
                    f"doc = creaite_doc.new({kind!r}, 'ABC', 'Report', '2026-10-16', {secs!r}, items={ITEMS!r}, audience={audience!r})\n"
                    "o = Path(paths.DRAFTS) / 'pic.docx'\ncreaite_doc.word_export(doc, o)\nprint(json.dumps(str(o)))")
        return media_sizes(r)

    def test_a_client_word_file_never_carries_an_outside_picture(self):
        sizes = self.word("client", sections_with(bad_refs(self.outside) + ["images/own.png"]))
        self.assertNotIn(list(OUT_SIZE), sizes)
        self.assertNotIn(list(OWN_SIZE), sizes, "a client document reads only its own picture store")

    def test_an_internal_word_file_never_carries_an_outside_picture_but_keeps_its_own(self):
        sizes = self.word("internal", sections_with(bad_refs(self.outside), current="Booked.\n\n![Our site](images/own.png)"))
        self.assertNotIn(list(OUT_SIZE), sizes)
        self.assertIn(list(OWN_SIZE), sizes, "Current state's images/ picture is still embedded")

    def test_a_symlinked_picture_is_refused(self):
        (self.images / "link.png").symlink_to(self.out / "linked.png")
        (self.out / "linked.png").write_bytes(png(*LINK_SIZE))
        (self.images / "sub").symlink_to(self.out, target_is_directory=True)
        (self.images / "inner.png").symlink_to(self.images / "own.png")       # even a link to the project's own picture
        sizes = self.word("internal", sections_with(["images/link.png", "images/sub/linked.png", "images/sub/outside.png",
                                                     "images/inner.png"]))
        self.assertNotIn(list(LINK_SIZE), sizes)
        self.assertNotIn(list(OWN_SIZE), sizes)
        self.assertNotIn(list(OUT_SIZE), sizes)

    def word_kind(self, kind, audience, secs):
        r = self.py("from pathlib import Path\nimport paths\n"
                    f"doc = creaite_doc.new({kind!r}, 'ABC', 'Report', '2026-10-16', {secs!r}, items={ITEMS!r}, audience={audience!r})\n"
                    "o = Path(paths.DRAFTS) / 'pic.docx'\ncreaite_doc.word_export(doc, o)\nprint(json.dumps(str(o)))")
        return media_sizes(r)

    def test_a_client_kind_is_client_whatever_its_audience_says(self):
        """Review MEDIUM 1: a hand-written client draft marked audience internal still reads no project picture."""
        own = sections_with([], current="Booked.\n\n![Our site](images/own.png)")
        self.assertNotIn(list(OWN_SIZE), self.word_kind("client", "internal", own))
        self.assertIn(list(OWN_SIZE), self.word_kind("weekly", "internal", own))

    def test_a_hard_link_to_an_outside_file_is_refused(self):
        """Review LOW 1: a hard link in the images folder can name a file outside the project."""
        os.link(self.v.root / "outside.png", self.images / "hard.png")
        sizes = self.word("internal", sections_with(["images/hard.png"], current="![Our site](images/own.png)"))
        self.assertNotIn(list(OUT_SIZE), sizes)
        self.assertIn(list(OWN_SIZE), sizes)

    def test_a_mapped_images_folder_outside_the_project_is_refused(self):
        """Review LOW 2: locations.folders.images set to `../..` or an absolute path never reads outside the project."""
        r = self.py("import paths\nf = paths.project_dir('ABC')\npaths.external = lambda: True\nout = []\n"
                    f"for m in ('../..', {str(self.out)!r}, 'images'):\n"
                    "    paths.folder_name = lambda k, m=m: m\n"
                    "    out.append([bool(paths.image_file(f, 'images/outside.png')), bool(paths.image_file(f, 'images/own.png'))])\n"
                    "print(json.dumps(out))")
        self.assertEqual(r, [[False, False], [False, False], [False, True]])

    def test_a_picture_line_in_a_fenced_code_block_is_kept(self):
        """Review LOW 3: the save drop leaves fenced code as written; a picture line outside the fence still goes."""
        text = "```\n![a](/abs/one.png)\n```\n~~~md\n![b](../two.png)\n~~~\n![c](/abs/three.png)\nEnd."
        secs = [{"id": "summary", "type": "text", "heading": "S", "default_heading": "S", "hidden": False, "text": text}]
        r = self.py(f"doc = creaite_doc.new('client', 'ABC', 'R', '2026-10-16', {secs!r}, audience='client')\n"
                    "d, gone = creaite_doc.drop_outside_pictures(doc)\nprint(json.dumps([d['sections'][0]['text'], len(gone)]))")
        self.assertEqual(r, [text.replace("![c](/abs/three.png)\n", ""), 1])

    def test_resolve_image_never_leaves_the_project_folder(self):
        refs = bad_refs(self.outside) + ["images/own.png"]
        r = self.py("import paths\nf = paths.project_dir('ABC')\n"
                    f"print(json.dumps([[paths.resolve_image(f, r).is_file(), bool(paths.image_file(f, r))] for r in {refs!r}]))")
        self.assertEqual(r, [[False, False]] * (len(refs) - 1) + [[True, True]])


class SaveDropsPictureLines(unittest.TestCase):
    """The save route: a hand-written client draft can't carry a picture line naming an outside file."""

    @classmethod
    def setUpClass(cls):
        from test_reports import ReportRoutes
        ReportRoutes.setUpClass.__func__(cls)
        cls.out = Path(tempfile.mkdtemp(prefix="pic-route-"))
        (cls.out / "outside.png").write_bytes(png(*OUT_SIZE))

    @classmethod
    def tearDownClass(cls):
        from test_reports import ReportRoutes
        shutil.rmtree(cls.out, True)
        ReportRoutes.tearDownClass.__func__(cls)

    def post(self, path, body):
        from test_reports import ReportRoutes
        return ReportRoutes.post(self, path, body)

    def test_the_client_save_drops_an_outside_picture_line_and_the_word_file_has_none(self):
        week = "2026-10-09"
        w = self.post("/api/report/draft", {"kind": "weekly", "code": "ABC", "week_ending": week})
        next(s for s in w["doc"]["sections"] if s["id"] == "health")["text"] = "UAT start slipped two weeks."
        self.assertTrue(self.post("/api/report/save", {"doc": w["doc"], "base_version": w["version"]})["ok"])
        a = self.post("/api/report/approve", {"kind": "weekly", "code": "ABC", "week_ending": week, "force": True})
        self.assertTrue(a["ok"] or "awaiting review" in a["message"], a)
        r = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": week})
        self.assertTrue(r["ok"], r)
        doc = r["doc"]
        bad = bad_refs(self.out / "outside.png")
        md = "\n".join(f"![leak]({x})" for x in bad) + "\n![ours](_images/2026-10-09-own.png)"
        for s in doc["sections"]:
            if s.get("type") in ("health", "text", "table", "timeline"):
                s["text"] = f"Kept words.\n\n{md}"
            if s.get("type") == "panes":
                for p in s.get("panes") or []:
                    p["text"] = f"Kept words.\n\n{md}"
        s = self.post("/api/report/save", {"doc": doc, "base_version": r["version"]})
        self.assertTrue(s["ok"], s)
        back = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": week})
        text = json.dumps(back["doc"])
        self.assertIn("Kept words.", text)
        self.assertIn("_images/2026-10-09-own.png", text, "the document's own picture reference stays")
        for x in bad:
            self.assertNotIn(json.dumps(x)[1:-1], text, x)
        self.assertNotIn("outside.png", text)
        w = self.post("/api/report/export", {"kind": "client", "code": "ABC", "week_ending": week, "fmt": "docx", "on_clash": "number"})
        self.assertTrue(w["ok"], w)
        self.assertNotIn(list(OUT_SIZE), media_sizes(self.v.root / w["path"]))


if __name__ == "__main__":
    os.environ.setdefault("CREAITE_BROWSER_SLOTS", "4")
    unittest.main(verbosity=2)
