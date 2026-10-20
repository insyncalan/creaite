"""#269 (scope addition): `search.py enrich set` never silently replaces a file's search summary. It writes a summary for a meeting or
report that has none yet; it replaces one only for a file a proposal waiting in Review files (the `to` of a copy or move, as cx-minutes
and the report skills enrich what they just staged), never for a client report, and never for a path that leads outside the vault
and the projects folder. Checked by search.py itself, so it holds in every mode. All paths are checked before any is written.

Run: python3 dev/tests/test_enrich_guard.py      (quick tier)
"""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import ABC, Vault  # noqa: E402

MINUTES = f"{ABC}/minutes/2026-10-05 Sync.docx"
WEEKLY = f"{ABC}/reports/2026-10-02 Weekly report - Example Programme.docx"
CLIENT = f"{ABC}/reports/2026-10-02 Client report - Example Programme.docx"
OK = ("--summary", "A new summary.", "--tags", "pilot, escalation, supplier")


class EnrichGuard(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        self.root = self.v.root
        self.outside = Path(tempfile.mkdtemp(prefix="creaite-outside-"))
        for rel in (MINUTES, WEEKLY, CLIENT):
            self.put(rel, "x")

    def tearDown(self):
        self.v.cleanup()
        shutil.rmtree(self.outside, ignore_errors=True)

    def put(self, rel, text, root=None):
        p = (root or self.root) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def sidecar(self, rel):
        return self.root / "system/search" / (hashlib.sha256(rel.encode()).hexdigest() + ".json")

    def summary(self, rel):
        f = self.sidecar(rel)
        return json.loads(f.read_text())["summary"] if f.exists() else None

    def enrich(self, *paths_, ok=True):
        args = [a for p in paths_ for a in ("--path", p)]
        r = subprocess.run([sys.executable, str(self.root / "system/scripts/search.py"), "enrich", "set", *args, *OK],
                           cwd=self.root, capture_output=True, text=True)
        self.assertEqual(r.returncode == 0, ok, r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        return r

    def seed(self, rel, text="The old summary."):
        """A summary written earlier (as the skills do once a file is processed)."""
        self.sidecar(rel).parent.mkdir(parents=True, exist_ok=True)
        self.sidecar(rel).write_text(json.dumps({"path": rel, "summary": text, "tags": ["a", "b", "c"]}))

    def stage(self, name, *to, kind="meeting"):
        block = {"title": "x", "file_ops": [{"op": "copy", "from": "draft", "to": t} for t in to]}
        self.v.propose(name, [], **{kind: block})

    # ── Written: a summary for a file that has none ──────────────────────────────
    def test_a_file_with_no_summary_gets_one(self):
        self.enrich(MINUTES, f"{ABC}/transcripts/2026-10-05 Sync.vtt")       # a copy not filed yet: cx-minutes enriches at stage
        self.assertEqual(self.summary(MINUTES), "A new summary.")

    def test_a_client_report_with_no_summary_gets_one(self):
        self.enrich(CLIENT)                                                  # cx-client-report, after Alan approves it
        self.assertEqual(self.summary(CLIENT), "A new summary.")

    # ── Replaced: only what a proposal waiting in Review files ──────────────────
    def test_an_existing_summary_is_not_silently_replaced(self):
        for rel in (MINUTES, WEEKLY, "projects/_portfolio/minutes/2026-10-05 Joint.docx"):
            with self.subTest(rel):
                self.seed(rel)
                r = self.enrich(rel, ok=False)
                self.assertIn("already has a summary", r.stderr)
                self.assertEqual(self.summary(rel), "The old summary.")

    def test_a_summary_is_replaced_for_a_file_a_staged_proposal_files(self):
        self.seed(MINUTES)
        self.seed(WEEKLY)
        self.stage("meeting", MINUTES)                                       # re-extract: the meeting staged again
        self.stage("weekly", WEEKLY, kind="report")                          # the weekly report redrafted
        self.enrich(MINUTES, WEEKLY)
        self.assertEqual((self.summary(MINUTES), self.summary(WEEKLY)), ("A new summary.", "A new summary."))

    def test_an_applied_proposal_doesnt_count(self):
        self.seed(MINUTES)
        applied = self.root / "system/staging/applied"
        applied.mkdir(parents=True, exist_ok=True)
        (applied / "proposed-old.json").write_text(json.dumps({"meeting": {"file_ops": [{"op": "copy", "to": MINUTES}]}}))
        self.enrich(MINUTES, ok=False)
        self.assertEqual(self.summary(MINUTES), "The old summary.")

    def test_a_proposal_that_only_names_the_file_doesnt_count(self):
        self.seed(MINUTES)
        self.v.propose("mention", [], meeting={"title": "x", "draft": MINUTES, "file_ops": [{"op": "remove", "path": MINUTES},
                                                                                           {"op": "link", "to": MINUTES}]})
        self.enrich(MINUTES, ok=False)

    def test_a_client_reports_summary_is_never_replaced(self):
        self.seed(CLIENT)
        self.stage("client", CLIENT, kind="report")
        r = self.enrich(CLIENT, ok=False)
        self.assertIn("client report", r.stderr)
        self.assertEqual(self.summary(CLIENT), "The old summary.")

    # ── Refused: outside, and nothing written when one path is refused ──────────
    def test_a_path_that_leads_outside_the_vault_is_refused(self):
        secret = self.put("Board.docx", "x", root=self.outside)
        link = self.root / ABC / "minutes/2026-10-06 Board.docx"
        link.symlink_to(secret)
        r = self.enrich(f"{ABC}/minutes/2026-10-06 Board.docx", ok=False)
        self.assertIn("outside", r.stderr)
        self.assertIsNone(self.summary(f"{ABC}/minutes/2026-10-06 Board.docx"))

    def test_one_refused_path_writes_none(self):
        self.seed(WEEKLY)
        self.enrich(MINUTES, WEEKLY, ok=False)
        self.assertIsNone(self.summary(MINUTES), "checked first, so nothing is half written")
        self.assertEqual(self.summary(WEEKLY), "The old summary.")


if __name__ == "__main__":
    unittest.main()
