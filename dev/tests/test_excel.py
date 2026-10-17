"""Tests for excel_sync.py (the Excel round-trip).

Run: python3 dev/tests/test_excel.py
Uses the same throwaway vault as test_tracker.py; the repository's own files are never touched.
"""
import json
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import ABC, Vault, action  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts" / "vendor"))
from openpyxl import load_workbook  # noqa: E402


class ExcelTests(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        self.v.propose("seed", [
            action(1, due_date="2026-10-09"),
            action(2, description="Book UAT environment"),
            {"n": 3, "op": "new", "table": "raid", "match": "strong", "flags": [], "decision": "approved",
             "values": {"project": "ABC", "type": "Risk", "description": "Data access delayed → MVP slips",
                        "impact": "High", "likelihood": "Medium", "raised": "2026-10-01",
                        "source": f"{ABC}/minutes/x.docx — Risks"}},
            {"n": 4, "op": "new", "table": "decisions", "match": "strong", "flags": [], "decision": "approved",
             "values": {"project": "ABC", "decision": "Go-live moves to 15 Nov", "date": "2026-10-01",
                        "source": f"{ABC}/minutes/x.docx — Decisions"}},
        ])
        self.v.run("apply")  # tracker.py exports the workbook after every apply
        self.xlsx = self.v.root / "tracker-view.xlsx"

    def tearDown(self):
        self.v.cleanup()

    def excel(self, *args, ok=True):
        return self.v.run(*args, script="excel_sync.py", ok=ok)

    def staged(self):
        files = sorted((self.v.root / "system/staging").glob("proposed-*-excel*.json"))
        return files[-1], json.loads(files[-1].read_text())

    def test_export_layout(self):
        self.assertTrue(self.xlsx.exists())
        wb = load_workbook(self.xlsx)
        self.assertEqual(wb.sheetnames, ["Review", "Projects", "Milestones", "Workstreams", "Actions", "RAID", "Decisions", "Promises", "Links", "Updates"])
        ws = wb["Actions"]
        header = [c.value for c in ws[1]]
        self.assertEqual(header[:3], ["ID", "Project", "Description"])
        due = ws.cell(row=2, column=header.index("Due") + 1)
        self.assertEqual(due.value.date(), date(2026, 10, 9))  # a real date…
        self.assertEqual(due.number_format, "dd-mm-yyyy")      # …shown DD-MM-YYYY
        rules = {str(dv.sqref): (dv.type, dv.formula1) for dv in ws.data_validations.dataValidation}
        self.assertIn(("custom", "FALSE"), rules.values())                                  # locked ID/source/updated
        self.assertIn(("list", '"Open,Delayed,Closed,Cancelled"'), rules.values())          # drop-down
        self.assertEqual(wb["RAID"].cell(row=2, column=11).value, "High")                    # priority as stored

    def test_round_trip_edit_add_delete(self):
        wb = load_workbook(self.xlsx)
        ws = wb["Actions"]
        h = [c.value for c in ws[1]]
        col = {name: h.index(name) + 1 for name in h}
        ws.cell(row=2, column=col["Owner"], value="Sara Example")           # edit a cell
        ws.cell(row=2, column=col["Due"], value=date(2026, 10, 16))          # and a date
        ws.delete_rows(3)                                                     # delete ABC-A-002
        ws.cell(row=3, column=col["Project"], value="ABC")                   # add a row
        ws.cell(row=3, column=col["Description"], value="Confirm hypercare scope")
        ws.cell(row=3, column=col["Due"], value="23-10-2026")                # typed as text, DD-MM-YYYY
        wb.save(self.xlsx)

        self.assertEqual(self.excel("changed", ok=False).returncode, 1)
        out = self.excel("import").stdout
        self.assertIn("1 new, 1 changed, 1 deleted (to confirm), 0 conflict(s), 0 invalid", out)
        self.assertEqual(self.excel("changed").returncode, 0)  # imported, so no longer "unimported"
        p, data = self.staged()
        self.assertEqual(data["source_run"], "excel-import")
        by_op = {i["op"]: i for i in data["items"]}
        self.assertEqual(by_op["update"]["changes"], {"owner": "Sara Example", "due_date": "2026-10-16"})
        self.assertEqual(by_op["new"]["values"]["due_date"], "2026-10-23")
        self.assertEqual(by_op["cancel"]["id"], "ABC-A-002")
        self.assertTrue(all(i["decision"] == "pending" for i in data["items"]))  # reviewed like any proposal

        for i in data["items"]:
            i["decision"] = "approved"
        p.write_text(json.dumps(data))
        self.assertIn("written 3", self.v.run("apply", str(p)).stdout)
        rows = {r["id"]: r for r in self.v.rows("actions")}
        self.assertEqual(rows["ABC-A-001"]["owner"], "Sara Example")
        self.assertEqual(rows["ABC-A-001"]["due_date"], "2026-10-16")
        self.assertEqual(rows["ABC-A-002"]["status"], "Cancelled")
        added = next(r for r in rows.values() if r["description"] == "Confirm hypercare scope")
        self.assertEqual(added["id"], "ABC-A-005")       # one number sequence per project: after the RAID item and the decision
        self.assertTrue(added["source"].startswith("Recorded by Alan in Excel"))
        # The apply re-exported the workbook with the new state
        ws = load_workbook(self.xlsx)["Actions"]
        self.assertEqual([r[0].value for r in ws.iter_rows(min_row=2, max_col=1) if r[0].value],
                         ["ABC-A-001", "ABC-A-002", "ABC-A-005"])

    def test_conflicting_edit_is_a_conflict(self):
        wb = load_workbook(self.xlsx)
        ws = wb["Actions"]
        ws.cell(row=2, column=[c.value for c in ws[1]].index("Owner") + 1, value="Sara Example")
        wb.save(self.xlsx)
        # Meanwhile the same action changes through another route
        self.v.propose("edit", [{"n": 1, "op": "update", "table": "actions", "id": "ABC-A-001",
                                 "changes": {"owner": "Omar Ali"}, "decision": "approved"}])
        out = self.v.run("apply", str(self.v.root / "system/staging/proposed-edit.json")).stdout
        self.assertIn("haven't been imported", out)  # export paused; workbook kept
        self.assertIn("conflict", self.excel("import").stdout)
        p, data = self.staged()
        item = data["items"][0]
        self.assertIn("conflict", item["flags"])
        item["decision"] = "approved"
        p.write_text(json.dumps(data))
        self.assertIn("held 1", self.v.run("apply", str(p)).stdout)
        self.assertEqual(self.v.rows("actions")[0]["owner"], "Omar Ali")  # not overwritten
        held = json.loads(p.read_text())["items"][0]
        self.assertEqual(held["current"]["owner"], "Omar Ali")             # both versions for review

    def test_export_refuses_unimported_edits(self):
        wb = load_workbook(self.xlsx)
        wb["Actions"].cell(row=2, column=3, value="Changed in Excel")
        wb.save(self.xlsx)
        before = self.xlsx.read_bytes()
        r = self.excel("export", ok=False)
        self.assertEqual(r.returncode, 3)
        self.assertEqual(self.xlsx.read_bytes(), before)
        self.excel("import")
        self.assertEqual(self.excel("export").returncode, 0)

    def test_export_refuses_while_open(self):
        (self.v.root / "~$tracker-view.xlsx").write_text("lock")
        self.assertIn("open in Excel", self.excel("export", ok=False).stdout)

    def test_review_sheet_decisions(self):
        p = self.v.propose("pending", [{**action(1, description="Send minutes"), "decision": "pending"},
                                       {**action(2, description="Chase legal"), "decision": "pending"},
                                       {**action(3, description="Tidy register"), "decision": "pending"}])
        self.excel("export")
        wb = load_workbook(self.xlsx)
        ws = wb["Review"]
        rows = {r[1].value: r for r in ws.iter_rows(min_row=2) if r[0].value == p.name}
        self.assertEqual(sorted(rows), [1, 2, 3])
        rows[1][9].value, rows[2][9].value = "Approve", "Reject"
        rows[3][9].value, rows[3][10].value = "Edit", "owner is Sara"
        wb.save(self.xlsx)
        out = self.excel("import").stdout
        self.assertIn("3 decision(s) recorded", out)
        items = json.loads(p.read_text())["items"]
        self.assertEqual([i["decision"] for i in items], ["approved", "rejected", "pending"])
        self.assertEqual(items[2]["review_note"], "Edit requested in Excel: owner is Sara")

    def test_locked_and_unknown_rows_ignored(self):
        wb = load_workbook(self.xlsx)
        ws = wb["Actions"]
        ws.cell(row=2, column=[c.value for c in ws[1]].index("Source") + 1, value="tampered")
        ws.cell(row=5, column=1, value="ABC-A-099")
        ws.cell(row=5, column=3, value="Made-up ID")
        wb.save(self.xlsx)
        out = self.excel("import").stdout
        self.assertIn("ABC-A-099 isn't in the last export", out)
        self.assertIn("No table edits to stage", out)

    def test_characters_a_workbook_cannot_hold_are_left_out(self):
        """#127 round 7: a C0 control character or U+FFFE/U+FFFF in a tracker row no longer stops the export after an apply
        (openpyxl's IllegalCharacterError left tracker-view.xlsx stale) or writes XML Excel must repair; tab and line breaks stay,
        and the character left out is no edit when the workbook is imported."""
        import re
        import zipfile
        self.v.propose("ctl", [action(5, description="Book\x07 the\x0bUAT\ufffe room\tnow\nplease"),
                               {"n": 6, "op": "new", "table": "decisions", "match": "strong", "flags": [], "decision": "approved",
                                "values": {"project": "ABC", "decision": "Go\x01 live\uffff in\x1f November", "date": "2026-10-02",
                                           "source": f"{ABC}/minutes/x.docx — Decisions"}}])
        out = self.v.run("apply")
        self.assertNotIn("IllegalCharacter", out.stdout + out.stderr)
        wb = load_workbook(self.xlsx)
        actions = [r[2].value for r in wb["Actions"].iter_rows(min_row=2) if r[0].value]
        decisions = [r[2].value for r in wb["Decisions"].iter_rows(min_row=2) if r[0].value]
        self.assertIn("Book the UAT room\tnow\nplease", actions)
        self.assertIn("Go live in November", decisions)
        bad = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]")
        with zipfile.ZipFile(self.xlsx) as z:
            for name in z.namelist():
                self.assertIsNone(bad.search(z.read(name).decode("utf-8", "surrogatepass")), name)
        self.assertEqual(self.excel("changed").returncode, 0)
        wb = load_workbook(self.xlsx)                  # one real edit: the rows the export cleaned are not edits
        h = [c.value for c in wb["Actions"][1]]
        wb["Actions"].cell(row=2, column=h.index("Owner") + 1, value="Sara Example")
        wb.save(self.xlsx)
        self.assertIn("0 new, 1 changed, 0 deleted", self.excel("import").stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
