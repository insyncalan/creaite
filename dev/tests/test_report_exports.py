"""Tests for v2.1.0 P2: the exports of a creaite document (creaite_doc.export; dev/sprints/v210-contract.md section 3).

Run: python3 dev/tests/test_report_exports.py
Every export is made from the data block, so HTML, Word and PDF have the same sections in the same order, and hidden sections,
rows and figures never reach any of them. The PDF tests print with Chrome (chrome_path), so this file is in the Chrome tier.
Each test builds a throwaway vault (test_tracker.Vault) with fictional data and runs the real scripts there.
"""
import json
import re
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import ABC, REPO, Vault  # noqa: E402

sys.path.insert(0, str(REPO / "system" / "scripts"))
import docx_tools  # noqa: E402
import launch  # noqa: E402

HIDDEN = ("Secret quarry", "walrus", "zebrafigure", "tagword", "Lantern ask")
SECTIONS = [
    {"id": "health", "type": "health", "heading": "Health", "default_heading": "Health", "hidden": False,
     "text": "The harbour migration slipped a week.", "data": {"flag": "At risk"}},
    {"id": "glance", "type": "figures", "heading": "At a glance", "default_heading": "At a glance", "hidden": False,
     "figures": [{"key": "overdue", "label": "Overdue actions", "value": "3", "note": "", "shown": True},
                 {"key": "high", "label": "Hidden figure", "value": "zebrafigure", "shown": False}]},
    {"id": "summary", "type": "text", "heading": "Executive summary", "default_heading": "Summary", "hidden": False,
     "text": "Progress on the lighthouse cutover.\n\n- first point\n- second point", "tags": [{"ref": "ABC-A-003", "text": "tagword"}]},
    {"id": "asks", "type": "table", "heading": "What we need from people", "default_heading": "What we need from people",
     "hidden": True, "text": "Lantern ask", "rows": [{"ref": "ABC-D-009", "cells": {"x": "walrus"}, "shown": True}]},
    {"id": "milestones", "type": "timeline", "heading": "Milestones", "default_heading": "Milestones", "hidden": False,
     "text": "Two milestones this quarter.", "data": {"milestones": ["ABC-M-001"]}},
    {"id": "risks", "type": "table", "heading": "Risks and issues", "default_heading": "Risks and issues", "hidden": False,
     "columns": [{"key": "id", "label": "ID"}, {"key": "title", "label": "Risk"}, {"key": "owner", "label": "Owner"}],
     "rows": [{"ref": "ABC-002", "cells": {"id": "ABC-002", "title": "Vendor capacity", "owner": "Sam Patel"}, "shown": True},
              {"ref": "ABC-005", "cells": {"id": "ABC-005", "title": "Secret quarry", "owner": "Ola Berg"}, "shown": False}]},
    {"id": "current_state", "type": "panes", "heading": "Current state", "default_heading": "Current state", "hidden": False,
     "panes": [{"title": "Where we are", "text": "Cutover rehearsal booked."}]},
]
ITEMS = {"ABC-002": {"table": "raid", "title": "Vendor capacity"}, "ABC-005": {"table": "raid", "title": "Secret quarry"},
         "ABC-D-009": {"table": "decisions", "title": "walrus"}, "ABC-M-001": {"table": "milestones", "title": "Go-live",
                                                                                "due_date": "2026-11-20"}}
SHOWN = [s["heading"] for s in SECTIONS if not s["hidden"]]


def chrome_path():
    """The Chrome the PDF export uses, or None (the PDF tests are then skipped)."""
    return launch.find_chrome()


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.v.run("init")

    def tearDown(self):
        self.v.cleanup()

    def py(self, code, env=None):
        """Run Python in the vault with creaite_doc imported; returns the last line of stdout as JSON."""
        import os
        r = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts'); import creaite_doc\n" + code],
                           cwd=self.v.root, capture_output=True, text=True, env={**os.environ, **(env or {})})
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def saved(self, kind="weekly", sections=SECTIONS, pre="", date="2026-10-16", **kw):
        """Save a document of `kind` (after running `pre` on it) and return its stored path."""
        args = ", ".join(f"{k}={v!r}" for k, v in kw.items())
        title = "Steering" if kind == "minutes" else "Weekly report" if kind == "weekly" else "Client report"
        r = self.py(f"doc = creaite_doc.new({kind!r}, 'ABC', {title!r}, {date!r}, {sections!r}, items={ITEMS!r}"
                    f"{', ' + args if args else ''})\n{pre}\n"
                    f"t = creaite_doc.target({kind!r}, 'ABC', {date!r}, name={title!r}, client={kw.get('client')!r})\n"
                    "print(json.dumps(creaite_doc.save(t, doc, 'Saved for a test')))")
        self.assertTrue(r["ok"], r)
        return r["path"]

    def export(self, path, fmt, env=None, **kw):
        """creaite_doc.export's answer."""
        args = "".join(f", {k}={v!r}" for k, v in kw.items())
        return self.py(f"print(json.dumps(creaite_doc.export({path!r}, {fmt!r}{args})))", env=env)

    def in_order(self, text, headings):
        """Assert every heading appears in `text`, in this order."""
        at = -1
        for h in headings:
            nxt = text.find(h, at + 1)
            self.assertGreater(nxt, at, f"{h!r} missing or out of order in:\n{text[:2000]}")
            at = nxt

    def word_text(self, path):
        """A Word file's body text, one line per paragraph."""
        raw = next(raw for info, raw in docx_tools.read_parts(self.v.root / path) if info.filename == "word/document.xml")
        return docx_tools.story_text(raw.decode("utf-8"))

    def hidden_absent(self, text):
        for gone in HIDDEN:
            self.assertNotIn(gone, text, gone)


class Html(Base):
    def test_the_page_without_its_data_with_the_sections_in_order(self):
        path = self.saved()
        r = self.export(path, "html")
        self.assertTrue(r["ok"], r)
        self.assertTrue(r["filed"])
        self.assertEqual(r["path"], f"{ABC}/reports/2026-10-16 Weekly report - Example Programme (2).html")   # the plain name is the filed report's own; the export is numbered
        page = (self.v.root / r["path"]).read_text(encoding="utf-8")
        self.assertNotIn("creaite-data", page)
        self.assertEqual(re.findall(r"<h2>(.*?)</h2>", page), SHOWN)
        self.hidden_absent(page)

    def test_an_unfiled_report_leaves_the_plain_name_for_the_filing(self):
        for kind, title in (("weekly", "Weekly report"), ("client", "Client report")):
            # v2.5.0 audience bypass: a client report is exported only after its internal week is approved, so it is based on one
            base = ("b = creaite_doc.new('weekly', 'ABC', 'Weekly report', '2026-10-16', [])\nb['state'] = 'approved'\n"
                    "rb = creaite_doc.save('system/staging/drafts/approved-base.html', b, 'Saved for a test')\n"
                    "doc['based_on'] = {'path': rb['path'], 'version': rb['version']}\n") if kind == "client" else ""
            r = self.py(f"doc = creaite_doc.new({kind!r}, 'ABC', {title!r}, '2026-10-16', {SECTIONS!r}, items={ITEMS!r})\n" + base +
                        "print(json.dumps(creaite_doc.save('system/staging/drafts/unfiled.html', doc, 'Saved for a test')))")
            self.assertTrue(r["ok"], r)
            out = self.export(r["path"], "html", out_dir=f"{ABC}/reports")
            self.assertTrue(out["ok"], out)
            self.assertRegex(out["path"], r"Example Programme\)? \(2\)\.html$", kind)
            self.assertNotIn("read only", out["path"])
            self.assertFalse((self.v.root / out["path"].replace(" (2).html", ".html")).exists(), "the filing name is left free")


class Word(Base):
    def test_the_firm_template_with_the_same_sections_in_the_same_order(self):
        r = self.export(self.saved(), "docx")
        self.assertTrue(r["ok"], r)
        text = self.word_text(r["path"])
        self.assertIn("Example Programme", text)
        self.in_order(text, SHOWN)
        for kept in ("Vendor capacity", "Sam Patel", "Overdue actions", "Go-live", "Cutover rehearsal booked", "first point"):
            self.assertIn(kept, text)
        self.hidden_absent(text)
        self.assertNotIn("{{", text)

    def test_a_reordered_document_exports_in_its_own_order(self):
        order = [SECTIONS[i] for i in (5, 2, 0, 1, 3, 4, 6)]
        r = self.export(self.saved(sections=order), "docx")
        self.assertTrue(r["ok"], r)
        self.in_order(self.word_text(r["path"]), [s["heading"] for s in order if not s["hidden"]])

    def test_minutes_fill_the_minutes_template(self):
        secs = [{"id": "summary", "type": "text", "heading": "Executive summary", "default_heading": "Executive summary",
                 "hidden": False, "text": "The steering agreed the plan."},
                {"id": "actions", "type": "table", "heading": "Action items", "default_heading": "Action items", "hidden": False,
                 "columns": [{"key": "owner", "label": "Owner"}, {"key": "text", "label": "Action"}],
                 "rows": [{"ref": "ABC-A-010", "cells": {"owner": "Sam Patel", "text": "Book the rehearsal"}, "shown": True}]}]
        r = self.export(self.saved("minutes", secs), "docx")
        self.assertTrue(r["ok"], r)
        self.assertTrue(r["path"].startswith(f"{ABC}/minutes/2026-10-16 Steering"), r)
        text = self.word_text(r["path"])
        self.in_order(text, ["Steering", "Executive summary", "Action items", "Book the rehearsal"])

    def test_a_pasted_control_character_still_gives_a_file_word_opens(self):
        """#127 round 6: a bell (\\x07) or U+FFFE pasted into a section or a table cell made document.xml invalid XML."""
        secs = json.loads(json.dumps(SECTIONS))
        next(s for s in secs if s["id"] == "summary")["text"] = "Progress on the\x07 lighthouse￾ cutover."
        next(s for s in secs if s["id"] == "risks")["rows"][0]["cells"]["title"] = "Vendor\x07 capacity"
        r = self.export(self.saved(sections=secs), "docx")
        self.assertTrue(r["ok"], r)
        ET.fromstring(next(raw for i, raw in docx_tools.read_parts(self.v.root / r["path"]) if i.filename == "word/document.xml"))
        self.assertIn("Progress on the lighthouse cutover.", self.word_text(r["path"]))


class Filing(Base):
    def test_beside_never_overwrites_and_off_leaves_only_the_draft(self):
        path = self.saved()
        one, two = self.export(path, "docx"), self.export(path, "docx")
        self.assertEqual(one["path"], path[:-5] + ".docx")
        self.assertEqual(two["path"], path[:-5] + " (2).docx")
        self.assertIsNone(one["draft"])
        self.assertEqual(list((self.v.root / "system/staging/drafts").iterdir()), [])     # filed: no draft or fill input left
        ET.fromstring(next(raw for i, raw in docx_tools.read_parts(self.v.root / one["path"]) if i.filename == "word/document.xml"))
        off = self.export(path, "html", file_beside=False, open_after=False)
        self.assertEqual((off["ok"], off["filed"], off["open_after"]), (True, False, False))
        self.assertTrue(off["path"].startswith("system/staging/drafts/"), off)
        self.assertTrue((self.v.root / off["path"]).is_file())
        log = [json.loads(x) for x in (self.v.root / "system/config/files-log.jsonl").read_text().splitlines()]
        self.assertEqual([e["path"] for e in log if e["op"] == "create" and not e["path"].endswith(".html")], [one["path"], two["path"]])

    def test_an_html_export_never_stands_in_for_the_draft(self):
        """Check 74: a filed report exported as HTML, not filed beside, must not leave a plain page at the draft's own path (where
        "Edit again" looks first)."""
        path = self.saved()
        own = "system/staging/drafts/" + path.rsplit("/", 1)[1]
        off = self.export(path, "html", file_beside=False)
        self.assertTrue(off["ok"], off)
        self.assertNotEqual(off["path"], own)
        self.assertFalse((self.v.root / own).exists(), "the export took the draft's path")
        self.assertTrue((self.v.root / off["path"]).is_file())
        self.assertEqual(self.py(f"print(json.dumps(creaite_doc.read({path!r})['kind']))"), "weekly")

    def test_exports_are_always_filed_beside_for_reports_and_by_default_for_minutes(self):
        got = self.py("print(json.dumps([creaite_doc.file_beside_default(k) for k in ('weekly', 'client', 'minutes')]))")
        self.assertEqual(got, [True, True, True])

    def test_the_saved_settings_win_and_an_unknown_kind_is_refused(self):
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text(encoding="utf-8")) if cfg.is_file() else {}
        data["reports"] = {"file_exports_beside": False, "file_minutes_exports_beside": False}
        cfg.parent.mkdir(parents=True, exist_ok=True)
        cfg.write_text(json.dumps(data), encoding="utf-8")
        got = self.py("print(json.dumps([creaite_doc.file_beside_default(k) for k in ('weekly', 'client', 'minutes')]))")
        self.assertEqual(got, [True, True, False], 'the old reports key is ignored; only minutes follow a setting')
        self.assertEqual(self.py("try:\n    creaite_doc.file_beside_default('memo')\nexcept ValueError:\n    print('true')"), True)

    def test_a_client_view_waits_for_the_approved_internal_report(self):
        draft = self.saved(date="2026-10-09")
        approved = self.saved(pre="doc.update(state='approved', approved_at='2026-10-16 15:00:00')")
        waiting = self.saved("client", date="2026-10-09", pre=f"doc['based_on'] = {{'path': {draft!r}, 'version': 1}}",
                             audience="client", client="Harbour Board")
        r = self.export(waiting, "docx")
        self.assertFalse(r["ok"])
        self.assertEqual(r["message"], "A client report is exported only after the internal report is approved.")
        ready = self.saved("client", pre=f"doc['based_on'] = {{'path': {approved!r}, 'version': 1}}", audience="client",
                           client="Harbour Board")
        r = self.export(ready, "docx")
        self.assertTrue(r["ok"], r)
        self.assertTrue(r["path"].startswith(f"{ABC}/reports/2026-10-16 Client report - Example Programme (Harbour Board)"), r)
        # v2.5.0: a client report's client is the project's own (its memory's Client line; this vault's names none), whatever the
        # document says
        self.in_order(self.word_text(r["path"]), ["Example Programme", "Client · Draft", "Health", "Executive summary"])
        self.assertNotIn("Harbour Board", self.word_text(r["path"]))

    def test_an_unknown_format_and_a_missing_file_say_why(self):
        self.assertIn("HTML, Word or PDF", self.export(self.saved(), "odt")["message"])
        self.assertEqual(self.export("projects/nowhere.html", "html")["message"], "That file isn't there.")

    def test_no_chrome_fails_with_a_clear_message_and_files_nothing(self):
        path = self.saved()
        r = self.export(path, "pdf", env={"CREAITE_BROWSER": "/nonexistent/chrome"})
        self.assertFalse(r["ok"])
        self.assertIn("Chrome wasn't found", r["message"])
        self.assertFalse((self.v.root / (path[:-5] + ".pdf")).exists())
        self.assertEqual(list((self.v.root / "system/staging/drafts").glob("*.html")), [])


@unittest.skipUnless(chrome_path(), "Chrome isn't installed")
class Pdf(Base):
    def test_the_same_sections_in_the_same_order_as_html_and_word(self):
        import pypdf
        path = self.saved()
        r = self.export(path, "pdf")
        self.assertTrue(r["ok"], r)
        text = "\n".join(p.extract_text() for p in pypdf.PdfReader(str(self.v.root / r["path"])).pages)
        self.in_order(text, SHOWN)
        self.assertIn("Vendor capacity", text)
        self.hidden_absent(text)
        html = self.export(path, "html")
        word = self.export(path, "docx")
        page = (self.v.root / html["path"]).read_text(encoding="utf-8")
        self.assertEqual(re.findall(r"<h2>(.*?)</h2>", page), SHOWN)
        self.in_order(self.word_text(word["path"]), SHOWN)


if __name__ == "__main__":
    unittest.main()
