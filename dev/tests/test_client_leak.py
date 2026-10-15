"""Tests for v2.1.0 P3's client leak check on the data (system/scripts/client_leak.py, report_doc.py; BL-336).

Run: python3 dev/tests/test_client_leak.py
Nothing that isn't client-visible, is Sensitive or is partner-only reaches a client report: not its items, rows, tags or milestone
list, not its file, not an approval. A client report is approved only after that week's internal report, and its facts then lock
to the approved week. test_reports' fixture and fixed clock (Friday 09-10-2026); the data is fictional.
"""
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


class ItemsNeverReachTheClient(Base):
    def test_client_report_holds_only_client_visible_items(self):
        doc = self.py("print(json.dumps(report_doc.client_doc('ABC')))")
        self.assertEqual(sorted(doc["items"]), ["ABC-006", "ABC-A-002", "ABC-D-007"])
        text = json.dumps(doc)
        for internal in ("ABC-005", "Vendor exits the market", "ABC-D-008", "Absorb the phase one overrun", "Confirm tester names"):
            self.assertNotIn(internal, text)
        self.assertNotIn("Test licences not ordered", text)                   # an item's internal wording never; its client wording only
        self.assertIn("Test licences are not yet ordered.", text)

    def test_a_sensitive_item_is_never_shown_even_when_client_visible(self):
        self.label("ABC-006")
        doc = self.py("print(json.dumps(report_doc.client_doc('ABC')))")
        self.assertNotIn("ABC-006", doc["items"])
        self.assertNotIn("ABC-006", json.dumps(doc["sections"]))
        got = self.py("d = report_doc.client_doc('ABC')\n"
                      "risks = next(s for s in d['sections'] if s['id'] == 'risks')\n"
                      "risks['rows'].append({'ref': 'ABC-006', 'shown': True, 'cells': {'type': 'Issue', 'risk': 'Licences'}})\n"
                      "d['items']['ABC-006'] = {'table': 'raid', 'id': 'ABC-006', 'title': 'Licences'}\n"
                      "safe, removed = client_leak.make_safe(d)\n"
                      "print(json.dumps({'found': client_leak.findings(d), 'removed': removed, 'safe': client_leak.findings(safe),"
                      " 'items': sorted(safe['items'])}))")
        self.assertIn("ABC-006 is Sensitive: never in a client report", got["found"])
        self.assertEqual(got["removed"], ["ABC-006 is Sensitive: never in a client report"])
        self.assertEqual(got["safe"], [])
        self.assertNotIn("ABC-006", got["items"])

    def test_a_partner_only_item_never_appears(self):
        self.v.propose("partner-label", [{"n": 1, "op": "new", "table": "labels", "match": "strong", "flags": [],
                                          "decision": "approved", "values": {"name": "Partner only", "colour": "grey"}}])
        self.v.run("apply")
        self.label("ABC-D-007", "Partner only")
        doc = self.py("print(json.dumps(report_doc.client_doc('ABC')))")
        self.assertNotIn("ABC-D-007", json.dumps(doc))
        got = self.py("print(json.dumps(client_leak.item_problem(client_leak.connect(), 'ABC-D-007')))")
        self.assertEqual(got, "ABC-D-007 is partner-only: never in a client report")

    def test_saving_a_client_report_drops_an_item_that_isnt_client_visible(self):
        got = self.py("d = report_doc.client_doc('ABC')\n"
                      "risks = next(s for s in d['sections'] if s['id'] == 'risks')\n"
                      "risks['rows'].append({'ref': 'ABC-005', 'shown': True, 'cells': {'type': 'Risk', 'risk': 'Vendor exits'}})\n"
                      "r = report_doc.save_draft(d)\n"
                      "back = creaite_doc.read(r['path'])\n"
                      "print(json.dumps({'removed': r['removed'], 'refs': sorted(client_leak.refs(back))}))")
        self.assertEqual(got["removed"], ["ABC-005 isn't client-visible"])
        self.assertNotIn("ABC-005", got["refs"])
        filed = (self.v.root / "system/staging/drafts/2026-10-09 Client report - Example Programme (Example Client Ltd).html")
        self.assertNotIn("Vendor exits", filed.read_text(encoding="utf-8"))

    def test_internal_wording_in_the_text_is_found(self):
        got = self.py("d = report_doc.client_doc('ABC')\n"
                      "s = next(s for s in d['sections'] if s['id'] == 'summary')\n"
                      "s['text'] = 'We will absorb the phase one overrun internally. Budget overrun on phase one is being absorbed.'\n"
                      "print(json.dumps(client_leak.findings(d)))")
        self.assertTrue(any(f.startswith("ABC-D-008 isn't client-visible but its wording appears") for f in got), got)
        self.assertTrue(any(f.startswith("memory line marked Client-safe: no appears") for f in got), got)

    def test_an_internal_report_is_never_checked_or_changed(self):
        got = self.py("d = report_doc.weekly_doc('ABC')\n"
                      "print(json.dumps({'f': client_leak.findings(d), 'same': client_leak.make_safe(d)[0] is d}))")
        self.assertEqual(got, {"f": [], "same": True})


class Baseline(Base):
    def test_a_client_report_is_approved_only_after_the_internal_week(self):
        r = self.py("d = report_doc.client_doc('ABC')\nr = report_doc.save_draft(d)\nreport_doc.stage_client(r['path'])", ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Approve the internal weekly report for week ending 09-10-2026 first", r.stderr)
        self.assertEqual(list((self.v.root / "system/staging").glob("proposed-*client*.json")), [])

    def test_facts_lock_to_the_approved_week(self):
        self.approve_week()
        self.v.propose("later", [{"n": 1, "op": "update", "table": "raid", "id": "ABC-006", "match": "strong", "flags": [],
                                  "decision": "approved", "changes": {"client_visible": 0}}])
        self.v.at("apply", script="tracker.py")
        doc = self.py("print(json.dumps(report_doc.client_doc('ABC')))")
        self.assertEqual(doc["based_on"]["path"], f"{R.ABC}/reports/2026-10-09 Weekly report - Example Programme.html")
        self.assertTrue(doc["meta"]["locked"])
        self.assertEqual(doc["meta"]["facts_week"], "2026-10-09")
        # the facts are the approved week's, but the leak check reads the tracker as it is now: no longer client-visible, so out
        self.assertNotIn("ABC-006", doc["items"])
        self.assertIn("ABC-D-007", doc["items"])

    def test_approve_refuses_a_leak_and_files_a_clean_report(self):
        self.approve_week()
        r = self.py("d = report_doc.client_doc('ABC')\n"
                    "s = next(s for s in d['sections'] if s['id'] == 'summary')\n"
                    "s['text'] = 'Notes from documents/ for the client.'\n"
                    "r = report_doc.save_draft(d)\nreport_doc.stage_client(r['path'])", ok=False)
        self.assertIn("possible internal content", r.stderr)
        self.assertIn("contains “documents/”", r.stderr)
        self.py("d = creaite_doc.read('system/staging/drafts/2026-10-09 Client report - Example Programme (Example Client Ltd).html')\n"
                "s = next(s for s in d['sections'] if s['id'] == 'summary')\n"
                "s['text'] = 'Testing starts on plan.'\n"
                "r = report_doc.save_draft(d, d['version'])\n"
                "print(json.dumps(report_doc.stage_client(r['path']).name))")
        self.v.at("apply", script="tracker.py")
        filed = self.v.root / R.ABC / "reports/2026-10-09 Client report - Example Programme (Example Client Ltd).html"
        text = filed.read_text(encoding="utf-8")
        self.assertIn('"state": "approved"', text)
        for internal in ("ABC-005", "ABC-D-008", "Vendor exits the market", "client_facts"):
            self.assertNotIn(internal, text)


class P8ClientView(Base):
    """v2.1.0 P8: what the client view's Match internal, eyes, health reason and left-out check can and can't do to the data."""

    def test_internal_rows_copied_into_the_client_report_are_dropped_at_save(self):
        """Match internal copied wholesale (what a generic sheet would do) would put internal rows on the client's page: saving removes them."""
        self.label("ABC-006")
        got = self.py("d = report_doc.client_doc('ABC')\n"
                      "risks = next(s for s in d['sections'] if s['id'] == 'risks')\n"
                      "for ref, t in (('ABC-005', 'Vendor exits the market before go-live'), ('ABC-006', 'Test licences not ordered')):\n"
                      "    risks['rows'].append({'ref': ref, 'shown': True, 'cells': {'type': 'Risk', 'risk': t}})\n"
                      "    d['items'][ref] = {'table': 'raid', 'id': ref, 'title': t}\n"
                      "r = report_doc.save_draft(d)\n"
                      "text = open(str(__import__('paths').resolve(r['path']))).read()\n"
                      "print(json.dumps({'removed': r['removed'], 'leaked': [x for x in ('ABC-005', 'ABC-006', 'Vendor exits', 'Test licences not') if x in text]}))")
        self.assertEqual(sorted(got["removed"]), ["ABC-005 isn't client-visible", "ABC-006 is Sensitive: never in a client report"])
        self.assertEqual(got["leaked"], [])

    def test_the_left_out_check_never_offers_a_sensitive_or_unseen_item(self):
        self.label("ABC-006")
        got = self.py("import client_check\nd = report_doc.client_doc('ABC')\nc = client_check.check(d)\n"
                      "print(json.dumps({'items': {x['ref']: [x['kind'], x['why']] for x in c['left_out']['items']},"
                      " 'addable': [a['row']['ref'] for a in c['addable']]}))")
        self.assertEqual(got["items"]["ABC-006"], ["sensitive", "Sensitive: never in a client report"])
        self.assertEqual(got["items"]["ABC-005"], ["blocked", "not client-visible"])
        self.assertEqual(got["addable"], [])

    def test_a_row_hidden_by_its_eye_keeps_no_wording_in_the_file(self):
        got = self.py("d = report_doc.client_doc('ABC')\n"
                      "risks = next(s for s in d['sections'] if s['id'] == 'risks')\n"
                      "risks['rows'] = [{'ref': r['ref'], 'shown': False} for r in risks['rows']]\n"
                      "r = report_doc.save_draft(d)\n"
                      "text = open(str(__import__('paths').resolve(r['path']))).read()\n"
                      "print(json.dumps('Test licences are not yet ordered' in text.split('creaite-data')[0]))")
        self.assertFalse(got)

    def test_the_health_reason_is_in_the_data_but_never_on_the_exported_page(self):
        got = self.py("d = report_doc.client_doc('ABC')\n"
                      "d['meta']['health_diff'] = {'internal': 'At risk', 'client': 'On track', 'reason': 'INTERNAL-REASON-ZED'}\n"
                      "print(json.dumps({'page': 'INTERNAL-REASON-ZED' in creaite_doc.render(d, editing=False),"
                      " 'findings': client_leak.findings(d)}))")
        self.assertEqual(got, {"page": False, "findings": []})


class ReviewReadsTheData(Base):
    def test_client_findings_reads_a_creaite_draft_from_its_data(self):
        got = self.py("import review\n"
                      "d = report_doc.client_doc('ABC')\n"
                      "d['sections'][3]['text'] = 'Restricted: absorb the phase one overrun internally.'\n"
                      "d['items']['ABC-005'] = {'table': 'raid', 'id': 'ABC-005', 'title': 'x'}\n"
                      "p = 'system/staging/drafts/check.html'\n"
                      "open(p, 'w').write(creaite_doc.dumps(d))\n"
                      "print(json.dumps(review.client_findings({'draft': p, 'project': 'ABC'})))")
        self.assertIn("ABC-005 isn't client-visible", got)
        self.assertIn("contains “restricted”", got)
        self.assertTrue(any("ABC-D-008" in f for f in got), got)


if __name__ == "__main__":
    unittest.main()
