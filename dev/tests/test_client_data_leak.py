"""v2.6.1: report.py client-data never gives the model a Sensitive or otherwise blocked item's words, even when it is client-visible,
and its excluded list holds an ID, kind and priority only (never the description).
Run: python3 dev/tests/test_client_data_leak.py      (quick tier: no Chrome)
Uses test_reports' fictional ABC world; the items are labelled through the tracker's own item_labels table in a throwaway vault.
"""
import json
import os
import sqlite3
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_reports import ReportVault, populate  # noqa: E402


class ClientDataLeak(unittest.TestCase):
    def setUp(self):
        self.v = ReportVault()
        populate(self.v)

    def tearDown(self):
        self.v.cleanup()

    def label(self, *ids, name="Sensitive"):
        con = sqlite3.connect(self.v.root / "system/tracker.db")
        try:
            con.execute("INSERT OR IGNORE INTO labels (name, builtin) VALUES (?, 1)", (name,))
            for i in ids:
                con.execute("INSERT INTO item_labels (item_id, label) VALUES (?, ?)", (i, name))
            con.commit()
        finally:
            con.close()

    def data(self):
        r = self.v.at("client-data", "ABC", "--since", "2026-10-01", script="report.py")
        return json.loads(r.stdout), r.stdout

    def test_a_sensitive_client_visible_item_is_in_no_list(self):
        d0, _ = self.data()
        self.assertEqual(([a["id"] for a in d0["client_actions"]], [a["id"] for a in d0["our_commitments"]],
                          [x["id"] for x in d0["decisions"]], [r["id"] for r in d0["risks"]]),
                         (["ABC-A-002"], ["ABC-A-003"], ["ABC-D-007"], ["ABC-006"]), "before: all four are shown")
        self.label("ABC-A-002", "ABC-A-003", "ABC-D-007", "ABC-006")
        d, raw = self.data()
        self.assertEqual((d["client_actions"], d["our_commitments"], d["decisions"], d["risks"]), ([], [], [], []))
        for i in ("ABC-A-002", "ABC-A-003", "ABC-D-007", "ABC-006"):
            self.assertNotIn(i, raw, f"{i}: not even its ID, nothing of it in the facts")
        self.assertFalse([n for n in d["needs_client_messaging"] if any(i in n for i in ("ABC-A-002", "ABC-D-007", "ABC-006"))])

    def test_a_partner_only_or_excluding_label_blocks_the_same_way(self):
        self.label("ABC-006", name="Partner only")
        d, _ = self.data()
        self.assertNotIn("ABC-006", [r["id"] for r in d["risks"]])

    def test_the_excluded_list_has_no_wording_and_a_sensitive_one_is_not_listed(self):
        d, raw = self.data()
        self.assertEqual(d["excluded_high_risks"], ["ABC-005 Risk (Urgent)"])
        self.assertNotIn("Vendor exits the market", raw, "the description of a non-client-visible risk never reaches the model")
        self.label("ABC-005")
        self.assertEqual(self.data()[0]["excluded_high_risks"], [])


if __name__ == "__main__":
    unittest.main()
