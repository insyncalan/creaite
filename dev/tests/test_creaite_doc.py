"""Tests for v2.1.0 P1: creaite's document format (system/scripts/creaite_doc.py; dev/sprints/v210-contract.md).

Run: python3 dev/tests/test_creaite_doc.py
Each test builds a throwaway vault (test_tracker.Vault) and runs the real scripts there: round trip, versions and Undo, search.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import ABC, Vault  # noqa: E402

DOC = """
doc = creaite_doc.new("weekly", "ABC", "Weekly report", "2026-10-16", [
    {"id": "health", "type": "health", "heading": "Health", "default_heading": "Health", "hidden": False,
     "text": "**At risk:** the harbour migration slipped; budget < 5% over </script> fine", "data": {"flag": "At risk"}},
    {"id": "summary", "type": "text", "heading": "Executive summary", "default_heading": "Summary", "hidden": False,
     "text": "Progress on the lighthouse cutover.\\n\\n- first point\\n- second point",
     "tags": [{"ref": "ABC-A-003", "text": "tagword"}]},
    {"id": "risks", "type": "table", "heading": "Risks and issues", "default_heading": "Risks and issues", "hidden": False,
     "columns": [{"key": "id", "label": "ID"}, {"key": "title", "label": "Risk"}],
     "rows": [{"ref": "ABC-002", "cells": {"id": "ABC-002", "title": "Vendor capacity"}, "shown": True},
              {"ref": "ABC-005", "cells": {"id": "ABC-005", "title": "Secret quarry"}, "shown": False}]},
    {"id": "glance", "type": "figures", "heading": "At a glance", "default_heading": "At a glance", "hidden": False,
     "figures": [{"key": "overdue", "label": "Overdue actions", "value": "3", "shown": True},
                 {"key": "high", "label": "Hidden figure", "value": "zebrafigure", "shown": False}]},
    {"id": "asks", "type": "table", "heading": "What we need from people", "default_heading": "What we need from people",
     "hidden": True, "text": "Concealed walrus ask", "rows": [{"ref": "ABC-D-009", "cells": {"x": "walrus"}, "shown": True}]},
], items={"ABC-002": {"table": "raid", "title": "Vendor capacity"}, "ABC-005": {"table": "raid", "title": "Secret quarry"},
          "ABC-D-009": {"table": "decisions", "title": "walrus"}, "ABC-A-003": {"table": "actions", "title": "SOW"}})
"""


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.v.run("init")

    def tearDown(self):
        self.v.cleanup()

    def py(self, code, ok=True):
        """Run Python in the vault with creaite_doc imported; returns stdout."""
        r = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts'); "
                            "import creaite_doc\n" + code], cwd=self.v.root, capture_output=True, text=True)
        if ok:
            self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def js(self, code):
        """Run code that prints one JSON value; returns it."""
        return json.loads(self.py(code).strip().splitlines()[-1])


class RoundTrip(Base):
    def test_saved_file_reads_back_with_hidden_content_dropped_and_opens_alone(self):
        out = self.js(DOC + "t = creaite_doc.target('weekly', 'ABC', '2026-10-16')\n"
                            "r = creaite_doc.save(t, doc, 'Weekly report saved')\n"
                            "back = creaite_doc.read(t)\n"
                            "print(json.dumps({'r': r, 'back': back, 'clean': creaite_doc.clean(doc)}))")
        r, back = out["r"], out["back"]
        self.assertTrue(r["ok"], r)
        self.assertEqual((r["code"], r["version"]), (0, 1))
        self.assertEqual(r["path"], f"{ABC}/reports/2026-10-16 Weekly report - Example Programme.html")
        self.assertEqual(back["version"], 1)
        self.assertTrue(back["saved_at"])
        clean = {**out["clean"], "version": 1, "saved_at": back["saved_at"]}
        self.assertEqual(back, clean)
        self.assertEqual(back["sections"][4], {"id": "asks", "type": "table", "heading": "What we need from people",
                                               "default_heading": "What we need from people", "hidden": True})
        self.assertEqual(back["sections"][2]["rows"][1], {"ref": "ABC-005", "shown": False})
        self.assertEqual(sorted(back["items"]), ["ABC-002", "ABC-A-003"])        # only hidden rows or sections named the others
        self.assertIn("</script> fine", back["sections"][0]["text"])
        text = (self.v.root / r["path"]).read_text(encoding="utf-8")
        for gone in ("Secret quarry", "walrus", "zebrafigure", "tagword"):
            self.assertNotIn(gone, text.split('id="creaite-data"')[0], gone)    # never on the page
        for gone in ("Secret quarry", "walrus", "zebrafigure"):
            self.assertNotIn(gone, text, gone)                                    # nor in the file
        self.assertNotRegex(text, r"(?i)\b(?:src|href)\s*=|<link|@import|url\(|https?:")   # nothing loaded from anywhere
        self.assertEqual(text.count("<script"), 1)                               # the data block only
        self.assertIn("<title>Weekly report - Example Programme, 16-10-2026</title>", text)
        self.assertIn("Example Programme", text)
        self.assertNotIn(">ABC<", text)

    def test_html_export_has_no_data_block(self):
        page = self.js(DOC + "print(json.dumps(creaite_doc.render(doc, editing=False)))")
        self.assertNotIn("creaite-data", page)
        self.assertIn("Vendor capacity", page)

    def test_not_a_document_and_newer_schema_are_refused(self):
        out = self.js("from pathlib import Path\n"
                      "p = Path('system/staging/drafts/x.html'); p.write_text('<html>plain</html>')\n"
                      "msgs = []\n"
                      "for t in ('<html>plain</html>', '<script type=\"application/json\" id=\"creaite-data\">{bad</script>',\n"
                      "          '<script type=\"application/json\" id=\"creaite-data\">{\"format\": \"creaite-doc\", \"schema\": 9}</script>'):\n"
                      "    try:\n        creaite_doc.loads(t)\n    except creaite_doc.DocError as e:\n        msgs.append(str(e))\n"
                      "doc = creaite_doc.new('minutes', 'ABC', 'Steering', '2026-10-14')\n"
                      "r = creaite_doc.save('system/staging/drafts/x.html', doc, 'Minutes saved')\n"
                      "print(json.dumps({'msgs': msgs, 'r': r, 'is': creaite_doc.is_doc(p), 'kept': p.read_text()}))")
        self.assertEqual(len(out["msgs"]), 3)
        self.assertIn("isn't a creaite document", out["msgs"][0])
        self.assertIn("isn't valid JSON", out["msgs"][1])
        self.assertIn("newer creaite (schema 9)", out["msgs"][2])
        self.assertFalse(out["r"]["ok"])
        self.assertIn("never overwrites", out["r"]["message"])
        self.assertEqual(out["kept"], "<html>plain</html>")
        self.assertFalse(out["is"])

    def test_bad_shapes_are_refused(self):
        out = self.js("msgs = []\n"
                      "for args in (('memo', 'ABC', 'x', '2026-10-14'), ('weekly', 'ABC', 'x', '14-10-2026')):\n"
                      "    try:\n        creaite_doc.new(*args)\n    except creaite_doc.DocError as e:\n        msgs.append(str(e))\n"
                      "try:\n    creaite_doc.new('weekly', 'ABC', 'x', '2026-10-16', [{'id': 'a'}, {'id': 'a'}])\n"
                      "except creaite_doc.DocError as e:\n    msgs.append(str(e))\n"
                      "print(json.dumps(msgs))")
        self.assertEqual(len(out), 3)

    def test_file_names(self):
        out = self.js("print(json.dumps([creaite_doc.target('weekly', 'ABC', '2026-10-16'),\n"
                      "  creaite_doc.target('client', 'ABC', '2026-10-16', client='Northwind'),\n"
                      "  creaite_doc.target('minutes', 'ABC', '2026-10-14', 'ABC steering: weekly / review?'),\n"
                      "  creaite_doc.target('minutes', '_portfolio', '2026-10-14', 'Portfolio sync')]))")
        self.assertEqual(out, [f"{ABC}/reports/2026-10-16 Weekly report - Example Programme.html",
                               f"{ABC}/reports/2026-10-16 Client report - Example Programme (Northwind).html",
                               f"{ABC}/minutes/2026-10-14 ABC steering weekly review.html",
                               "projects/_portfolio/minutes/2026-10-14 Portfolio sync.html"])

    def test_report_file_keeps_docx_for_the_word_drafts(self):
        out = self.py("import report\nprint(report.report_file('2026-10-16', 'Weekly report', 'Example Programme'))\n"
                      "print(report.report_file('2026-10-16', 'Weekly report', 'Example Programme', ext='.html'))")
        self.assertEqual(out.split(), "2026-10-16 Weekly report - Example Programme.docx "
                                      "2026-10-16 Weekly report - Example Programme.html".split())


class Versions(Base):
    def test_each_save_is_a_version_kept_and_undoable(self):
        out = self.js(DOC + "t = 'system/staging/drafts/2026-10-16 Weekly report.html'\n"
                            "rs = []\n"
                            "for i in range(3):\n"
                            "    doc['sections'][1]['text'] = f'Edition {i + 1}'\n"
                            "    rs.append(creaite_doc.save(t, doc, f'save {i + 1}'))\n"
                            "vs = creaite_doc.versions(t)\n"
                            "older = creaite_doc.read_version(t, vs[1]['change'])\n"
                            "stale = creaite_doc.save(t, doc, 'stale', base_version=2)\n"
                            "u = creaite_doc.undo(t)\n"
                            "after = creaite_doc.read(t)\n"
                            "vs2 = creaite_doc.versions(t)\n"
                            "print(json.dumps({'rs': rs, 'vs': vs, 'older': older['sections'][1]['text'], 'stale': stale,\n"
                            "  'u': u, 'after': [after['version'], after['sections'][1]['text']], 'vs2': [v['version'] for v in vs2]}))")
        self.assertEqual([r["version"] for r in out["rs"]], [1, 2, 3])
        self.assertTrue(all(r["ok"] for r in out["rs"]))
        self.assertEqual([v["version"] for v in out["vs"]], [3, 2, 1])
        self.assertTrue(out["vs"][0]["current"])
        self.assertEqual(out["older"], "Edition 2")                    # what the third save replaced
        self.assertTrue(out["stale"]["conflict"])
        self.assertIn("now version 3", out["stale"]["message"])
        self.assertTrue(out["u"]["ok"], out["u"])
        self.assertEqual(out["u"]["version"], 2)
        self.assertEqual(out["after"], [2, "Edition 2"])
        self.assertEqual(out["vs2"], [2, 1])
        log = (self.v.root / "system/config/files-log.jsonl").read_text(encoding="utf-8")
        self.assertEqual(log.count('"op": "edit"'), 2)
        self.assertEqual(log.count('"op": "create"'), 1)
        self.assertEqual(list((self.v.root / "system/staging/drafts").glob("creaite-doc *")), [])    # no draft left behind

    def test_undo_of_the_first_save_removes_the_file(self):
        out = self.js(DOC + "t = creaite_doc.target('weekly', 'ABC', '2026-10-16')\n"
                            "creaite_doc.save(t, doc, 'first')\nu = creaite_doc.undo(t)\n"
                            "print(json.dumps([u, creaite_doc.versions(t), creaite_doc.undo(t)]))")
        self.assertTrue(out[0]["ok"])
        self.assertIsNone(out[0]["version"])
        self.assertEqual(out[1], [])
        self.assertFalse(out[2]["ok"])

    def test_saving_over_a_filed_report_needs_alans_approval(self):
        out = self.js(DOC + "import reach\nt = creaite_doc.target('weekly', 'ABC', '2026-10-16')\n"
                            "first = creaite_doc.save(t, doc, 'filed')\n"
                            "blocked = creaite_doc.save(t, doc, 'again')\n"
                            "approved = creaite_doc.save(t, doc, 'again', approver=reach.APPROVALS.issue, via='dashboard')\n"
                            "print(json.dumps([first, blocked, approved, creaite_doc.read(t)['version']]))")
        first, blocked, approved, now = out
        self.assertEqual(first["code"], 0)
        self.assertEqual(blocked["code"], 3)
        self.assertTrue(blocked["needs_approval"])
        self.assertEqual(approved["code"], 0, approved)
        self.assertEqual((approved["version"], now), (2, 2))


class Search(Base):
    def test_search_reads_each_shown_section_only(self):
        self.py(DOC + "creaite_doc.save(creaite_doc.target('weekly', 'ABC', '2026-10-16'), doc, 'filed')\n"
                      "print(creaite_doc.search_text(creaite_doc.target('weekly', 'ABC', '2026-10-16')))")
        self.assertIn("Indexed", self.v.run("index").stdout)
        path = f"{ABC}/reports/2026-10-16 Weekly report - Example Programme.html"

        def found(word):
            return path in [h["path"] for h in json.loads(self.v.run("query", word).stdout)]

        for word in ("lighthouse", "harbour", "Vendor capacity"):
            self.assertTrue(found(word), word)
        for word in ("walrus", "quarry", "zebrafigure", "tagword"):
            self.assertFalse(found(word), word)

    def test_sections_text_keeps_headings_in_page_order(self):
        out = self.js(DOC + "print(json.dumps(creaite_doc.sections_text(doc)))")
        self.assertEqual([s[0] for s in out], ["health", "summary", "risks", "glance"])
        self.assertIn("Vendor capacity", out[2][2])
        self.assertNotIn("Secret quarry", out[2][2])
        self.assertIn("Overdue actions 3", out[3][2])



class FixPass240(Base):
    """The 2.4.0 fix pass (H5): a big picture, empty sections in the plain page."""

    def test_a_picture_over_2_mb_is_left_out_with_a_plain_sentence_in_html_and_word(self):
        out = self.js("from pathlib import Path\nimport tempfile\n"
                      "root = Path(tempfile.mkdtemp()); (root / '_images').mkdir()\n"
                      "(root / '_images' / 'big.png').write_bytes(b'\\x89PNG\\r\\n\\x1a\\n' + b'0' * (3 * 1024 * 1024))\n"
                      "(root / '_images' / 'ok.png').write_bytes(b'\\x89PNG\\r\\n\\x1a\\n' + bytes(4) + b'IEND' + bytes(4))\n"
                      "creaite_doc.images_dir = lambda d: root\n"
                      "w = creaite_doc._Word({'project': 'ABC'}, root)\n"
                      "word = w.freetext({'text': '![chart](_images/big.png)'})\n"
                      "print(json.dumps({'big': creaite_doc._image_html({}, 'chart', '_images/big.png'),\n"
                      "                  'ok': creaite_doc._image_html({}, 'chart', '_images/ok.png')[:12], 'word': json.dumps(word)}))")
        self.assertIn("Picture too large to include", out["big"])
        self.assertNotIn("base64", out["big"])
        self.assertTrue(out["ok"].startswith("<figure>"), out["ok"])
        self.assertIn("Picture too large to include", out["word"])

    def test_a_picture_that_cannot_be_checked_is_left_out_with_a_plain_sentence_in_html_and_word(self):
        out = self.js("from pathlib import Path\nimport tempfile\n"
                      "root = Path(tempfile.mkdtemp()); (root / '_images').mkdir()\n"
                      "(root / '_images' / 'bad.jpg').write_bytes(b'\\xff\\xd8\\xff\\xfe\\x7f\\xffWalrus budget cut')\n"
                      "creaite_doc.images_dir = lambda d: root\n"
                      "w = creaite_doc._Word({'project': 'ABC'}, root)\n"
                      "word = w.freetext({'text': '![chart](_images/bad.jpg)'})\n"
                      "print(json.dumps({'html': creaite_doc._image_html({}, 'chart', '_images/bad.jpg'), 'word': json.dumps(word)}))")
        self.assertIn("Picture not included", out["html"])
        self.assertNotIn("base64", out["html"])
        self.assertIn("Picture not included", out["word"])

    def test_the_plain_page_leaves_out_a_section_with_nothing_in_it(self):
        page = self.js("doc = creaite_doc.new('weekly', 'ABC', 'Weekly report', '2026-10-16', [\n"
                       "  {'id': 'summary', 'type': 'text', 'heading': 'Summary', 'default_heading': 'Summary', 'hidden': False, 'text': ''},\n"
                       "  {'id': 'progress', 'type': 'text', 'heading': 'Progress', 'default_heading': 'Progress', 'hidden': False, 'text': '  '},\n"
                       "  {'id': 'current_state', 'type': 'panes', 'heading': 'Current state', 'default_heading': 'Current state', 'hidden': False, 'panes': []},\n"
                       "  {'id': 'next', 'type': 'text', 'heading': 'Next steps', 'default_heading': 'Next steps', 'hidden': False, 'text': 'Plan the cutover.'}])\n"
                       "print(json.dumps(creaite_doc.render(doc, editing=False)))")
        for gone in ("Summary", "Progress", "Current state"):
            self.assertNotIn(f"<h2>{gone}</h2>", page, gone)
        self.assertIn("<h2>Next steps</h2>", page)
        self.assertIn("Plan the cutover.", page)

    def test_the_weekly_picker_offers_every_decision_not_sixty(self):
        from test_tracker import ABC as FOLDER
        self.v.propose("many", [{"n": i, "op": "new", "table": "decisions", "match": "strong", "flags": [], "decision": "approved",
                                 "values": {"project": "ABC", "decision": f"Decision number {i}", "date": "2026-10-01",
                                            "source": f"{FOLDER}/minutes/x.docx - Decisions"}} for i in range(1, 71)])
        self.v.run("apply")
        n = self.js("import report_doc\nprint(json.dumps(len(report_doc._pick_weekly('ABC')['decisions'])))")
        self.assertEqual(n, 70)

    def test_a_project_code_with_a_trailing_newline_is_not_a_code(self):
        out = self.js("import report_doc\nprint(json.dumps([bool(report_doc.CODE.match('ABC')), bool(report_doc.CODE.match('ABC\\n'))]))")
        self.assertEqual(out, [True, False])


if __name__ == "__main__":
    unittest.main()
