"""#369 (2.6.8): the raw calendar reply (system/staging/drafts/calendar.json, invite text as Outlook gave it, passcodes included)
must not stay in staging after a refused or failed save, and so must not reach the daily backup zip or its OneDrive copy.

Run: python3 dev/tests/test_v268_calendar_draft_leak.py      (quick tier: throwaway vault, no Chrome, no Claude)

All names, codes and numbers are made up.
"""
import json
import subprocess
import sys
import unittest
import zipfile
from datetime import timedelta
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "system" / "scripts"))
from test_backups import Case, GIT  # noqa: E402
from test_dashboard import today  # noqa: E402

SECRET = "Zq7Passcode-4821"


class RawDraftLeak(Case):
    def setUp(self):
        super().setUp()
        self.draft = self.v.root / "system/staging/drafts/calendar.json"
        self.draft.parent.mkdir(parents=True, exist_ok=True)
        self.tomorrow = (today() + timedelta(days=1)).isoformat()

    def meeting(self, **kw):
        return {"id": "e1", "start": "09:00", "end": "09:30", "title": f"Review Passcode: {SECRET}", "where": f"Room 2 Passcode: {SECRET}",
                "body": f"Agenda: budget\nPasscode: {SECRET}", **kw}

    def write(self, spec):
        self.draft.write_text(json.dumps(spec))

    def staging_text(self):
        return "".join(f.read_text(errors="ignore") for f in (self.v.root / "system/staging").rglob("*") if f.is_file())

    def zips_text(self):
        out = ""
        for z in [*self.backups().glob("creaite-backup-*.zip"), *self.offsite().glob("creaite-backup-*.zip")]:
            with zipfile.ZipFile(z) as zf:
                out += "".join(zf.read(n).decode("utf-8", "ignore") for n in zf.namelist() if n != "vault.bundle")
        return out

    def calendar(self):
        return self.run_script("sweep.py", "calendar", str(self.draft), ok=False, now=self.today)

    def test_a_refused_reply_leaves_no_raw_draft_in_staging_or_the_backup(self):
        refusals = {"not a calendar": {"days": [self.meeting()]},
                    "too large": {"days": {self.tomorrow: [self.meeting(id=f"e{i}", start=f"{8 + i % 10:02d}:00")
                                                           for i in range(501)]}}}
        for name, spec in refusals.items():
            with self.subTest(name):
                self.write(spec)
                r = self.calendar()
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                self.assertFalse(self.draft.exists())
                self.assertNotIn(SECRET, self.staging_text())
        self.start(now=self.today)
        self.assertTrue(list(self.offsite().glob("creaite-backup-*.zip")))
        self.assertNotIn(SECRET, self.zips_text())

    def test_an_unreadable_reply_and_a_crash_also_remove_the_draft(self):
        self.draft.write_text("{ not json " + SECRET)
        self.assertEqual(self.calendar().returncode, 1)
        self.assertFalse(self.draft.exists())
        import sweep
        self.write({"days": {self.tomorrow: [self.meeting()]}})
        with mock.patch.object(sweep.paths, "DRAFTS", self.draft.parent), mock.patch.object(sweep, "calendar_days",
                                                                                           side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                sweep.calendar(str(self.draft))
        self.assertFalse(self.draft.exists())

    def test_a_leftover_draft_from_an_older_run_is_removed_when_the_calendar_commands_start(self):
        self.write({"days": {self.tomorrow: [self.meeting()]}})
        self.run_script("sweep.py", "calendar-window", now=self.today)
        self.assertFalse(self.draft.exists())
        other = self.draft.parent / "calendar-old.json"
        other.write_text(json.dumps({"days": {self.tomorrow: [self.meeting()]}}))
        self.write({"days": {self.tomorrow: [self.meeting(title="Budget review", body="Agenda")]}})
        r = self.calendar()                                  # the one passed is saved; any other is a leftover
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(other.exists())
        self.assertNotIn(SECRET, self.staging_text())

    def test_a_saved_reply_is_still_saved_clean_and_the_draft_removed(self):
        self.write({"days": {self.tomorrow: [self.meeting()]}})
        r = self.calendar()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(self.draft.exists())
        self.assertNotIn(SECRET, self.staging_text())


if __name__ == "__main__":
    unittest.main()
