"""BL-229 step 4: pin report.py's two largest builders before they are split. steerco_data (the steering one-pager's
facts) and current_context (what a Current state draft may draw on) run on test_steerco's fixture, with its fixed clock,
in each of their versions; their whole output is compared with the saved expectation in dev/tests/pinned/report/.

Run: python3 dev/tests/test_report_builders_pinned.py     (quick tier: no Chrome)
Record (only before the split, or for a reviewed change): CREAITE_PIN_RECORD=1 python3 dev/tests/test_report_builders_pinned.py
"""
import json
import os
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_reports as R  # noqa: E402  (its WeeklyTests and ClientTests fixtures; their tests don't run here)
import test_steerco as S  # noqa: E402  (its Base: the fixture and the fixed clock; none of its tests run here)

PINNED = Path(__file__).resolve().parent / "pinned" / "report"
RECORD = os.environ.get("CREAITE_PIN_RECORD") == "1"

STEERCO = {                                     # name: steerco-data arguments after the project code
    "steerco_internal": [],
    "steerco_client": ["--version", "client"],
    "steerco_since": ["--since", S.d(-10)],
    "steerco_dated": ["--date", S.d(3)],
    "steerco_client_including": ["--version", "client", "--include", "ABC-A-005,ABC-002"],
}
CONTEXT = {                                     # name: current-context arguments after the project code
    "context_internal": [],
    "context_client": ["--audience", "client"],
    "context_period": ["--from", S.d(-10), "--to", S.d(-1)],
    "context_short": ["--length", "short"],
    "context_tracker_only": ["--sources", "tracker"],
    "context_with_documents": ["--sources", "tracker,documents,swept"],
    "context_bad_length": ["--length", "epic"],
}


ADHOC = {                                       # name: adhoc-data arguments (one-off Word documents, BL-75)
    "adhoc_actions": ["actions"],
    "adhoc_actions_all": ["actions", "--status", "all"],
    "adhoc_actions_overdue": ["actions", "--overdue"],
    "adhoc_actions_by_owner": ["actions", "--group-by", "owner"],
    "adhoc_actions_columns": ["actions", "--columns", "id,description,owner", "--limit", "3"],
    "adhoc_raid_issues": ["raid", "--type", "Issue"],
    "adhoc_decisions": ["decisions"],
    "adhoc_milestones": ["milestones", "--status", "all"],
}


def vault_free(text, root):
    """The vault's path as <VAULT>, in both its forms (on macOS /var/… is also written /private/var/…)."""
    return text.replace(str(Path(root).resolve()), "<VAULT>").replace(str(root), "<VAULT>")


def pin(test, name, text):
    """Compare `text` with the saved expectation (or record it)."""
    f = PINNED / f"{name}.txt"
    if RECORD:
        PINNED.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")
    test.assertEqual(text, f.read_text(encoding="utf-8"), f"{name}: the builder's output changed")


class Pinned(S.Base):
    maxDiff = None

    def check(self, name, text):
        text = vault_free(text, self.v.root)
        f = PINNED / f"{name}.txt"
        if RECORD:
            PINNED.mkdir(parents=True, exist_ok=True)
            f.write_text(text, encoding="utf-8")
        self.assertEqual(text, f.read_text(encoding="utf-8"), f"{name}: the builder's output changed")

    def test_steerco_data(self):
        for name, args in STEERCO.items():
            with self.subTest(name):
                out = json.loads(self.script("report.py", "steerco-data", "ABC", *args).stdout)
                self.check(name, json.dumps(out, indent=1, sort_keys=True, ensure_ascii=False) + "\n")

    def test_adhoc_data(self):
        for name, args in ADHOC.items():
            with self.subTest(name):
                r = self.script("report.py", "adhoc-data", *args, ok=False)
                self.check(name, f"exit {r.returncode}\n{r.stdout}{r.stderr}")

    def test_current_context(self):
        for name, args in CONTEXT.items():
            with self.subTest(name):
                r = self.script("report.py", "current-context", "ABC", *args, ok=False)
                self.check(name, f"exit {r.returncode}\n{r.stdout}{r.stderr}")


class WeeklyPinned(unittest.TestCase):
    """weekly_data and weekly_stage on test_reports' weekly fixture (its clock fixed in ReportVault.at)."""
    maxDiff = None

    def setUp(self):
        R.WeeklyTests.setUp(self)

    def tearDown(self):
        self.v.cleanup()

    def out(self, *args):
        r = self.v.at(*args, script="report.py", ok=False)
        return vault_free(f"exit {r.returncode}\n{r.stdout}{r.stderr}", self.v.root)

    def test_weekly_data(self):
        pin(self, "weekly_data", self.out("weekly-data", "ABC"))
        pin(self, "weekly_data_earlier_week", self.out("weekly-data", "ABC", "--week-ending", "2026-10-02"))

    def test_weekly_stage(self):
        text = self.out("weekly-stage", R.WeeklyTests.spec(self))
        staged = sorted((self.v.root / "system/staging").glob("proposed-*.json"))
        for p in staged:
            data = json.loads(p.read_text(encoding="utf-8"))
            data.pop("created", None)                     # when it was staged
            text += f"\n== {p.name}\n" + json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False)
        text = re.sub(r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d+", "<TS>", text)   # based_on: rows' updated_at, the real clock
        pin(self, "weekly_stage", vault_free(text, self.v.root) + "\n")


class ClientPinned(unittest.TestCase):
    """client_data on test_reports' client fixture."""
    maxDiff = None

    def setUp(self):
        R.ClientTests.setUp(self)

    def tearDown(self):
        self.v.cleanup()

    def test_client_data(self):
        for name, args in {"client_data": [], "client_data_since": ["--since", "2026-09-20"]}.items():
            with self.subTest(name):
                r = self.v.at("client-data", "ABC", *args, script="report.py", ok=False)
                pin(self, name, vault_free(f"exit {r.returncode}\n{r.stdout}{r.stderr}", self.v.root))


if __name__ == "__main__":
    unittest.main()
