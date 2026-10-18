"""Shared fixture for test_client_leak and its split parts (module-level helpers and the base class; no tests here)."""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_reports as R  # noqa: E402  (its fixture: populate, ReportVault, NOW)
HEAD = "import sys, json; sys.path.insert(0, 'system/scripts')\nimport report_doc, creaite_doc, client_leak\n"
APPROVE_WEEK = """
d = report_doc.weekly_doc("ABC")
for s in d["sections"]:
    if s["id"] == "health":
        s["text"] = "UAT start slipped two weeks."
r = report_doc.save_draft(d)
p = report_doc.stage_weekly(r["path"])
"""
class Base(unittest.TestCase):
    def setUp(self):
        self.v = R.ReportVault()
        R.populate(self.v)

    def tearDown(self):
        self.v.cleanup()

    def py(self, code, ok=True):
        """Run Python in the vault on the fixed clock; returns the last line printed, read as JSON."""
        r = subprocess.run([sys.executable, "-c", HEAD + code], cwd=self.v.root, env={**os.environ, "CREAITE_NOW": R.NOW},
                           capture_output=True, text=True)
        if ok:
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        lines = r.stdout.strip().splitlines()
        return json.loads(lines[-1]) if ok else r

    def label(self, item_id, name="Sensitive"):
        self.v.propose(f"lab-{item_id}-{name.replace(' ', '')}", [
            {"n": 1, "op": "new", "table": "item_labels", "match": "strong", "flags": [], "decision": "approved",
             "values": {"item_id": item_id, "label": name, "reason": "kept from the client"}}])
        self.v.run("apply")

    def approve_week(self):
        self.py(APPROVE_WEEK + "print(json.dumps(p.name))")
        self.v.at("apply", script="tracker.py")

REGISTER = ("# People register\n\n## People\n\n| Full name | Email | Aliases | Organisation | Role | Hidden | VIP | Labels |\n"
            "|---|---|---|---|---|---|---|---|\n"
            "| Jane Doe | jane@example.com | Jane, JD | Example Client Ltd | Sponsor | | | |\n"
            "| Omar Ali | omar@example.com | Omar | Example Client Ltd | Tester | | | |\n"
            "| Mia Hale | mia@example.com | Mia | Example Partner | Adviser | | | |\n")
