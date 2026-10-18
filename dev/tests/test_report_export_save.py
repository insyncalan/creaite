"""#220: report exports are saved to disk first, say where, and ask what to do about a taken name.

Run: python3 dev/tests/test_report_export_save.py        (the PDF and the page tests need Chrome; skipped without it)

Brief: dev/sprints/export-220-save-brief.md. Each acceptance check maps to named tests:
  Check 1  (HTML, Word and PDF each leave a real file in the stated folder, right name)   test_check1_*
  Check 2  (the toast shows the folder link; Show in Finder and Open work)                  test_check2_*
  Check 3  (a taken name offers three choices; each does exactly what it says; Rename shows the whole name;
            Overwrite keeps a backup; Cancel writes nothing)                                test_check3_*
  Check 4  (a failed save, e.g. a read-only folder, says so)                                test_check4_*
  Check 5  (same for the internal and the client report and each format)                    test_check5_*
Live only: the Finder window and the real viewers (the tests set CREAITE_NO_LAUNCH).
"""
import json
import os
import re
import stat
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_reports import ABC, ReportRoutes  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
import launch  # noqa: E402

HAVE_CHROME = bool(launch.find_chrome())
PROJECT_REPORTS = "Example Programme › Reports"
WEEKLY_STEM = "2026-10-09 Weekly report - Example Programme"
PAGE_STEM = "2026-10-16 Weekly report - Example Programme"          # the page opens this week (the clock is pinned)
CLIENT_STEM = "2026-10-09 Client report - Example Programme (Example Client Ltd)"


def export_name(stem, fmt):
    return f"{stem}.{fmt}"                      # the plain name for all three formats (Alan, 18-10-2026)


class ExportSave(unittest.TestCase):
    """The route, on a live server in a throwaway vault (the same harness as test_reports.ReportRoutes)."""
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
                f.unlink()                      # exports and filed reports of an earlier test

    def weekly(self):
        """A saved weekly draft (the export needs one)."""
        r = self.post("/api/report/draft", {"kind": "weekly", "code": "ABC", "week_ending": "2026-10-09"})
        self.assertTrue(r["ok"], r)
        self.section(r["doc"], "health")["text"] = "UAT start slipped two weeks."          # an approval needs the reason
        s = self.post("/api/report/save", {"doc": r["doc"], "base_version": r["version"]})
        self.assertTrue(s["ok"], s)

    def client(self):
        """A saved client draft whose internal week is approved."""
        self.weekly()
        a = self.post("/api/report/approve", {"kind": "weekly", "code": "ABC", "week_ending": "2026-10-09", "force": True})
        self.assertTrue(a["ok"] or "awaiting review" in a["message"], a)
        r = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": "2026-10-09"})
        self.assertTrue(r["ok"], r)
        s = self.post("/api/report/save", {"doc": r["doc"], "base_version": r["version"]})
        self.assertTrue(s["ok"], s)

    def export(self, fmt, kind="weekly", **more):
        return self.post("/api/report/export", {"kind": kind, "code": "ABC", "week_ending": "2026-10-09", "fmt": fmt, **more})

    def drafts_left(self):
        return [p.name for p in (self.v.root / "system/staging/drafts").glob("*") if re.search(r"\.(docx|pdf)$|\(read only\)", p.name)]

    # ── Check 1 and 5: every format, both reports, lands in Reports with the right name ────────────────────────────────
    def formats(self):
        return ["html", "docx"] + (["pdf"] if HAVE_CHROME else [])

    def test_check1_each_format_of_the_weekly_report_is_saved_in_reports(self):
        self.weekly()
        for fmt in self.formats():
            r = self.export(fmt)
            name = export_name(WEEKLY_STEM, fmt)
            self.assertTrue(r["ok"] and r["saved"], r)
            self.assertEqual((r["name"], r["path"], r["folder"]), (name, f"{ABC}/reports/{name}", f"{ABC}/reports"), r)
            self.assertTrue((self.reports / name).stat().st_size > 0, fmt)
            self.assertEqual(r["folder_label"], PROJECT_REPORTS)
            self.assertNotIn("launched", r)                                    # opening is a separate choice
        self.assertEqual(self.drafts_left(), [])                               # nothing half-made is left behind

    def test_check5_each_format_of_the_client_report_is_saved_in_reports(self):
        self.client()
        for fmt in self.formats():
            r = self.export(fmt, "client")
            name = export_name(CLIENT_STEM, fmt)
            self.assertTrue(r["ok"] and r["saved"], r)
            self.assertEqual((r["name"], r["folder_label"]), (name, PROJECT_REPORTS), r)
            self.assertTrue((self.reports / name).is_file(), fmt)
            self.assertIn("left_out", r)                                       # the client check still runs and answers

    # ── Check 2: the answer carries what the toast needs; Show in Finder ───────────────────────────────────────────────
    def test_check2_the_answer_names_the_folder_and_show_in_finder_accepts_it(self):
        self.weekly()
        r = self.export("docx")
        self.assertEqual(r["message"], f"Saved {export_name(WEEKLY_STEM, 'docx')} in {PROJECT_REPORTS}.")
        for target in (r["path"], r["folder"]):
            shown = self.post("/api/report/reveal", {"path": target})
            self.assertEqual((shown["ok"], shown["launched"]), (True, False), shown)       # CREAITE_NO_LAUNCH: nothing opens
        for bad in ("CLAUDE.md", "projects/../CLAUDE.md", f"{ABC}/reports/none.docx"):
            self.assertFalse(self.post("/api/report/reveal", {"path": bad})["ok"], bad)
        log = [json.loads(x) for x in (self.v.root / "system/config/files-log.jsonl").read_text().splitlines()]
        self.assertTrue(any(e["op"] == "create" and e["path"] == r["path"] for e in log))   # logged, so undoable

    # ── Check 3: a taken name ──────────────────────────────────────────────────────────────────────────────────────────
    def test_check3_a_taken_name_asks_and_writes_nothing(self):
        self.weekly()
        first = self.export("docx")
        before = {p.name: p.read_bytes() for p in self.reports.glob("*")}
        again = self.export("docx")
        self.assertEqual((again["ok"], again.get("clash"), again["name"]), (False, True, first["name"]), again)
        self.assertEqual(again["numbered"], export_name(WEEKLY_STEM, "docx").replace(".docx", " (2).docx"))
        self.assertEqual(again["folder_label"], PROJECT_REPORTS)
        self.assertEqual({p.name: p.read_bytes() for p in self.reports.glob("*")}, before)   # Cancel and the question write nothing
        self.assertEqual(self.drafts_left(), [])

    def test_check3_add_a_number(self):
        self.weekly()
        self.export("docx")
        r = self.export("docx", on_clash="number")
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["name"], WEEKLY_STEM + " (2).docx")
        self.assertTrue((self.reports / (WEEKLY_STEM + ".docx")).is_file())
        self.assertEqual(self.export("docx", on_clash="number")["name"], WEEKLY_STEM + " (3).docx")

    def test_check3_rename_it(self):
        self.weekly()
        self.export("docx")
        r = self.export("docx", on_clash="rename", new_name="Weekly for the board")
        self.assertEqual((r["ok"], r["name"]), (True, "Weekly for the board.docx"), r)        # the extension is kept
        self.assertTrue((self.reports / "Weekly for the board.docx").is_file())
        taken = self.export("docx", on_clash="rename", new_name="Weekly for the board.docx")  # a taken new name asks again
        self.assertEqual((taken["ok"], taken.get("clash")), (False, True), taken)
        for bad in ("", "a/b", "../x", ".hidden"):
            self.assertFalse(self.export("docx", on_clash="rename", new_name=bad)["ok"], bad)
        self.assertEqual(sorted(p.name for p in self.reports.glob("*.docx")), sorted(["Weekly for the board.docx", WEEKLY_STEM + ".docx"]))

    def test_check3_overwrite_keeps_a_backup(self):
        self.weekly()
        self.export("docx")
        target = self.reports / (WEEKLY_STEM + ".docx")
        target.write_bytes(b"EARLIER FILE")
        r = self.export("docx", on_clash="overwrite")
        self.assertEqual((r["ok"], r["replaced"], r["name"]), (True, True, WEEKLY_STEM + ".docx"), r)
        self.assertNotEqual(target.read_bytes(), b"EARLIER FILE")
        self.assertTrue(r["message"].startswith("Replaced "), r["message"])
        backups = [p for p in (self.v.root / "system/backups/files").rglob("*") if p.is_file() and p.read_bytes() == b"EARLIER FILE"]
        self.assertTrue(backups, "the earlier file is backed up first")
        self.assertEqual(sorted(p.name for p in self.reports.glob("*.docx")), [WEEKLY_STEM + ".docx"])   # nothing else was added

    def test_check3_html_after_the_report_is_filed_asks_and_overwrite_is_undoable(self):
        self.weekly()
        a = self.post("/api/report/approve", {"kind": "weekly", "code": "ABC", "week_ending": "2026-10-09"})
        self.assertTrue(a["ok"], a)
        filed = self.reports / (WEEKLY_STEM + ".html")
        original = filed.read_bytes()
        asked = self.export("html")                                              # the plain name is the filed report's name
        self.assertEqual((asked["ok"], asked.get("clash"), asked["name"]), (False, True, WEEKLY_STEM + ".html"), asked)
        self.assertEqual(filed.read_bytes(), original)                           # nothing was written before the choice
        self.assertEqual(self.drafts_left(), [])
        r = self.export("html", on_clash="overwrite")
        self.assertEqual((r["ok"], r["replaced"]), (True, True), r)
        self.assertNotEqual(filed.read_bytes(), original)
        self.assertTrue([p for p in (self.v.root / "system/backups/files").rglob("*") if p.is_file() and p.read_bytes() == original],
                        "the filed report is backed up first")
        import subprocess
        undo = subprocess.run([sys.executable, "system/scripts/filechange.py", "undo"], cwd=self.v.root, capture_output=True, text=True)
        self.assertEqual(undo.returncode, 0, undo.stdout + undo.stderr)
        self.assertEqual(filed.read_bytes(), original)                           # Undo puts the filed report back

    # ── Check 4: a failed save ─────────────────────────────────────────────────────────────────────────────────────────
    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root can write to a read-only folder")
    def test_check4_a_read_only_folder_says_so_and_writes_nothing(self):
        self.weekly()
        self.reports.chmod(stat.S_IRUSR | stat.S_IXUSR)
        try:
            r = self.export("docx")
        finally:
            self.reports.chmod(stat.S_IRWXU)
        self.assertFalse(r["ok"], r)
        self.assertEqual(r.get("saved"), False)
        self.assertIn("Not saved", r["message"])
        self.assertIn("Nothing was written", r["message"])
        self.assertNotIn("Not exported", r["message"])
        self.assertEqual([p.name for p in self.reports.glob("*") if p.suffix == ".docx" or p.name.startswith(".")], [])
        self.assertEqual(self.drafts_left(), [])


# ── The page: the dialog, the choices and the toast, in real Chrome ────────────────────────────────────────────────────
class ExportSavePage(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        populate(v)

    @classmethod
    def server_env(cls):
        return {"CREAITE_NO_LAUNCH": "1"}

    def setUp(self):
        super().setUp()
        self.reports = self.v.root / ABC / "reports"
        self.b.eval("go('weekly',{code:'ABC'})")
        self.b.wait("document.querySelector('#v-weekly section[data-id=current_state]')", 20)
        self.b.eval("window.__calls=[];const f=window.fetch;window.fetch=function(u,o){window.__calls.push([String(u),o&&o.body||'']);return f.apply(this,arguments)}")

    def export(self, label):
        self.b.eval("document.querySelector('[data-wrexport]').click()")
        self.b.wait("document.querySelector('[role=menu]')", 5)
        self.b.eval(f"[...document.querySelectorAll('[role=menu] [role=menuitem]')].find(b=>b.textContent.includes({label!r})).click()")

    def exported_files(self):
        return sorted(p.name for p in self.reports.glob("*.html"))

    def test_check2_the_toast_names_the_folder_with_show_in_finder_and_open(self):
        self.export("HTML")
        self.b.wait("document.querySelector('[data-export-saved]')", 30)
        text = self.b.eval("document.querySelector('[data-export-saved]').textContent")
        name = export_name(PAGE_STEM, "html")
        self.assertIn(f"Saved {name} in {PROJECT_REPORTS}", text)
        self.assertEqual(self.b.eval("document.querySelector('[data-export-saved] a[data-export-folder]').textContent"), PROJECT_REPORTS)
        self.assertEqual(self.b.eval("[...document.querySelectorAll('[data-export-saved] button')].map(b=>b.textContent)"),
                         ["Show in Finder", "Open"])
        self.assertTrue((self.reports / name).is_file())
        self.b.eval("document.querySelector('[data-export-saved] a[data-export-folder]').click()")
        self.b.eval("[...document.querySelectorAll('[data-export-saved] button')].find(b=>b.textContent==='Show in Finder').click()")
        self.b.eval("[...document.querySelectorAll('[data-export-saved] button')].find(b=>b.textContent==='Open').click()")
        self.b.wait("window.__calls.filter(c=>/api\\/open|report\\/reveal/.test(c[0])).length>=3", 10)
        calls = self.b.eval("window.__calls.filter(c=>/api\\/open|report\\/reveal/.test(c[0]))")
        self.assertIn(f"{ABC}/reports", calls[0][1])                       # the link opens the folder
        self.assertIn("report/reveal", calls[1][0])
        self.assertIn(name, calls[1][1])
        self.assertIn("api/open", calls[2][0])
        self.assertIn(name, calls[2][1])

    def test_check3_a_taken_name_offers_the_three_choices_and_cancel_writes_nothing(self):
        self.export("HTML")
        self.b.wait("document.querySelector('[data-export-saved]')", 30)
        self.export("HTML")
        self.b.wait("document.querySelector('#exportClashDlg[open]')", 30)
        name = export_name(PAGE_STEM, "html")
        self.assertIn(name, self.b.eval("document.querySelector('#exportClashDlg').textContent"))
        self.assertEqual(self.b.eval("[...document.querySelectorAll('#exportClashDlg input[name=clash]')].map(i=>i.value)"),
                         ["number", "rename", "overwrite"])
        self.assertEqual(self.b.eval("document.querySelector('#exportClashDlg input[name=clash]:checked').value"), "number")
        self.assertIn(PAGE_STEM + " (2).html", self.b.eval("document.querySelector('#exportClashDlg').textContent"))
        field = self.b.eval("(()=>{const i=document.querySelector('#exportClashRename');return {v:i.value,w:i.getBoundingClientRect().width,"
                            "dw:document.querySelector('#exportClashDlg .mnap, #exportClashDlg').getBoundingClientRect().width,"
                            "full:i.scrollWidth<=i.clientWidth+1}})()")
        self.assertEqual(field["v"], name)                                  # the whole name, prefilled
        self.assertTrue(field["full"], "the field shows the whole name")
        self.assertGreater(field["w"], field["dw"] * 0.6)                   # the full width of the dialog
        before = self.exported_files()
        self.b.eval("document.querySelector('#exportClashNo').click()")
        self.b.wait("!document.querySelector('#exportClashDlg[open]')", 5)
        self.assertEqual(self.exported_files(), before)
        self.assertFalse(self.b.eval("window.__calls.some(c=>/on_clash/.test(c[1]))"))

    def test_check3_each_choice_does_what_it_says(self):
        name = export_name(PAGE_STEM, "html")
        self.export("HTML")
        self.b.wait("document.querySelector('[data-export-saved]')", 30)

        def again(choice, typed=None):
            self.export("HTML")
            self.b.wait("document.querySelector('#exportClashDlg[open]')", 30)
            self.b.eval(f"document.querySelector('#exportClashDlg input[value={choice}]').click()")
            if typed:
                self.b.eval(f"(()=>{{const i=document.querySelector('#exportClashRename');i.value={typed!r};"
                            "i.dispatchEvent(new Event('input',{bubbles:true}))})()")
            self.b.eval("document.querySelector('#exportClashGo').click()")
            self.b.wait("!document.querySelector('#exportClashDlg[open]')", 10)
        again("number")
        self.b.wait("/\\(2\\)\\.html in/.test(document.querySelector('[data-export-saved]').textContent)", 10)
        again("rename", "Board copy.html")
        self.b.wait("/Board copy\\.html in/.test(document.querySelector('[data-export-saved]').textContent)", 10)
        (self.reports / name).write_text("EARLIER FILE")
        again("overwrite")
        self.b.wait("/^Replaced/.test(document.querySelector('[data-export-saved]').textContent)", 10)
        self.assertTrue((self.reports / name.replace(".html", " (2).html")).is_file())
        self.assertTrue((self.reports / "Board copy.html").is_file())
        self.assertNotEqual((self.reports / name).read_text(), "EARLIER FILE")

    def test_check4_a_failed_save_is_said_on_the_page(self):
        self.b.eval("(()=>{const g=window.fetch;window.fetch=function(u,o){return String(u).includes('report/export')?Promise.resolve(new Response("
                    "JSON.stringify({ok:false,saved:false,message:'Not saved: the Example Programme \u203a Reports folder can\\'t be written to "
                    "(Permission denied). Nothing was written.'}),{status:200})):g.call(window,u,o)}})()")
        self.export("Word")
        self.b.wait("document.querySelector('[data-export-failed]')", 30)
        self.assertIn("Nothing was written", self.b.eval("document.querySelector('[data-export-failed]').textContent"))
        self.assertNotIn("Not exported", self.b.eval("document.body.innerText"))


if __name__ == "__main__":
    unittest.main()
