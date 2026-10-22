"""#277: Match internal's check route (POST /api/report/match-check) is sent a client document whose project code is not a string
(a list, a number, an object: P22's seed 2 made a list). It must answer a refusal Alan can read, never a fault (HTTP 500): the
document is refused where it is read (creaite_doc.check), so nothing reaches the tracker query with a code it can't bind. A
document with a string code is checked as before. Fictional data only.

Run: python3 dev/tests/test_match_check_project_code.py
"""
import copy
import json
import sys
import unittest
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_client_audience as A  # noqa: E402  (its harness: a live server in a throwaway vault)

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
import creaite_doc  # noqa: E402


class MatchCheckProjectCode(unittest.TestCase):
    """test_client_audience's harness (a live server in a throwaway vault), without its own tests."""
    setUpClass = classmethod(A.S.ExportSave.setUpClass.__func__)
    tearDownClass = classmethod(A.S.ExportSave.tearDownClass.__func__)
    post, reports, setUp, client = A.S.ExportSave.post, A.S.ExportSave.reports, A.S.ExportSave.setUp, A.S.ExportSave.client
    weekly, section = A.S.ExportSave.weekly, A.S.ExportSave.section
    fresh, draft_file = A.Audience.fresh, A.Audience.draft_file

    def match_check(self, docs):
        """The route's (HTTP status, answer); a fault answers its status too, not an exception."""
        try:
            return 200, self.post("/api/report/match-check", {"docs": docs})
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            try:
                return e.code, json.loads(body)
            except ValueError:
                return e.code, {"raw": body}

    def test_a_project_code_that_is_not_a_string_is_refused_not_a_fault(self):
        d = self.fresh()["doc"]
        for bad in (["ABC"], ["ABC", "DEF"], 7, {"code": "ABC"}, True):
            with self.subTest(project=bad):
                sent = copy.deepcopy(d)
                sent["project"] = bad
                status, r = self.match_check([sent])
                self.assertEqual(status, 200, r)
                self.assertFalse(r.get("ok"), r)
                self.assertTrue(r.get("message"), r)
                self.assertNotIn("findings", r)

    def test_a_string_project_code_is_still_checked(self):
        d = self.fresh()["doc"]
        status, r = self.match_check([d])
        self.assertEqual(status, 200, r)
        self.assertTrue(r.get("ok"), r)
        self.assertEqual(len(r["findings"]), 1, r)

    def test_check_refuses_a_non_string_code_and_keeps_a_missing_one(self):
        base = creaite_doc.new("client", "ABC", "Client report", "2026-10-09")
        creaite_doc.check(base)                                   # a string code: fine
        for bad in (["ABC"], 7, {"a": 1}, False):
            with self.subTest(project=bad), self.assertRaises(creaite_doc.DocError):
                creaite_doc.check({**base, "project": bad})
        for ok in (None, ""):                                     # no code at all: not this check's refusal
            creaite_doc.check({**base, "project": ok})


if __name__ == "__main__":
    unittest.main(verbosity=2)
