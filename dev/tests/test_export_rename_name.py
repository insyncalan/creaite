"""v2.5.0: a name typed for an export (on_clash "rename", new_name) never claims a report's filing name, and is never a reserved name.

Before this fix a weekly (internal) export could be renamed to "2026-10-16 Client report - … (Example Client Ltd).html" and sit in the
Reports folder looking like the client's filed report; Windows' reserved device names (CON, NUL, COM1…) were taken too. Now a typed
name that reads as a weekly or client filing name is refused unless it is this report's own filing name (which then asks, as before),
and a reserved device name or a character Windows forbids is refused. Live routes, a throwaway vault, fictional data only.

Run: python3 dev/tests/test_export_rename_name.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_report_export_save as S  # noqa: E402  (as a module: its own tests are not run again here)
from test_report_export_save import CLIENT_STEM, WEEKLY_STEM  # noqa: E402


class RenameName(unittest.TestCase):
    """The rename choice of the export route (ExportSave's harness, without running its own tests again)."""
    setUpClass = classmethod(S.ExportSave.setUpClass.__func__)
    tearDownClass = classmethod(S.ExportSave.tearDownClass.__func__)
    post = S.ExportSave.post
    section = S.ExportSave.section
    reports = S.ExportSave.reports
    setUp = S.ExportSave.setUp
    weekly = S.ExportSave.weekly
    client = S.ExportSave.client
    export = S.ExportSave.export

    def files(self):
        return sorted(p.name for p in self.reports.glob("*") if p.is_file())

    def test_a_weekly_export_is_never_renamed_to_a_client_filing_name(self):
        self.weekly()
        before = self.files()
        for fmt in ("html", "docx"):
            for typed in (f"2026-10-16 Client report - Example Programme (Example Client Ltd).{fmt}",
                          "2026-10-09 Client report - Example Programme (Example Client Ltd)",
                          "2026-10-09 client REPORT - Example Programme",
                          "2026-10-09  Client​ report - Example Programme",
                          "２０２６-10-09 Client report - Example Programme",
                          "2026_10_09_Client_report_Example",
                          "Client report - Example Programme (Example Client Ltd)",
                          "2026-10-02 Weekly report - Example Programme",           # another week's weekly filing name
                          f"2026-10-09 Weekly report - Another Programme.{fmt}"):    # another report's filing name
                with self.subTest(fmt=fmt, typed=typed):
                    r = self.export(fmt, on_clash="rename", new_name=typed)
                    self.assertFalse(r.get("ok") or r.get("saved"), r)
        self.assertEqual(self.files(), before, "nothing was written")

    def test_a_client_export_is_never_renamed_to_another_filing_name(self):
        self.client()
        before = self.files()
        for typed in ("2026-10-16 Client report - Example Programme (Example Client Ltd)", f"{WEEKLY_STEM}.docx"):
            with self.subTest(typed=typed):
                r = self.export("docx", "client", on_clash="rename", new_name=typed)
                self.assertFalse(r.get("ok") or r.get("saved"), r)
        self.assertEqual(self.files(), before)

    def test_reserved_and_forbidden_names_are_refused(self):
        self.weekly()
        before = self.files()
        for typed in ("CON", "con.docx", "NUL", "nul.txt", "PRN", "AUX", "COM1", "lpt9", "COM¹", "CONIN$", "a<b", "a>b", 'a"b',
                      "a|b", "a?b", "a*b", "a:b", "CON .docx", "nul.tar.gz"):
            with self.subTest(typed=typed):
                r = self.export("docx", on_clash="rename", new_name=typed)
                self.assertFalse(r.get("ok") or r.get("saved"), r)
        self.assertEqual(self.files(), before)

    def test_control_ordinary_names_and_the_reports_own_name_still_work(self):
        self.weekly()
        r = self.export("docx", on_clash="rename", new_name="Board copy")
        self.assertEqual((r["ok"], r["name"]), (True, "Board copy.docx"), r)
        r = self.export("docx", on_clash="rename", new_name="Console notes")            # starts like CON, is not CON
        self.assertEqual((r["ok"], r["name"]), (True, "Console notes.docx"), r)
        r = self.export("docx", on_clash="rename", new_name=f"{WEEKLY_STEM} (2)")         # its own filing name, numbered
        self.assertEqual((r["ok"], r["name"]), (True, f"{WEEKLY_STEM} (2).docx"), r)
        own = self.export("html", on_clash="rename", new_name=WEEKLY_STEM + ".HTML")   # its own reserved filing name: asks, as before
        self.assertEqual((own["ok"], own.get("reserved")), (False, True), own)
        self.client()
        r = self.export("docx", "client", on_clash="rename", new_name=f"{CLIENT_STEM} (2)")
        self.assertEqual((r["ok"], r["name"]), (True, f"{CLIENT_STEM} (2).docx"), r)


if __name__ == "__main__":
    unittest.main(verbosity=2)
