"""BL-323: backups that look after themselves, all to OneDrive.

- The day's zip is made after the daily backup, complete against its manifest (each file's size and checksum, the creaite
  version), holds exactly what was agreed (the closed database backup, config, settings.local.json, CLAUDE.md, staging minus
  ask creaite's chats and images, the git bundle, the flow files, processed.txt) and nothing else; it appears in OneDrive (and
  in system/backups/) only once written: a temporary name, then a rename.
- If OneDrive can't be reached nothing stops; doctor warns from two days without a copy, and Health's offsite fix applies.
- Retention over a simulated 400 days of dated sample files keeps exactly the agreed set, locally and in OneDrive.
- Tidy up never removes a file it didn't write or the newest of a kind; it runs once a day, never in the development
  repository, and not when today's zip failed; Health and doctor show the last run.
- The weekly restore check catches a corrupt database, a missing file and a bad git bundle.
- A restore from the zip into a fresh vault gives a working vault (doctor: 0 failed), with the git history back.
- Undo of a file change whose backup Tidy up removed says so.

Run: python3 dev/tests/test_backups.py     (quick tier: no Chrome; needs git)
"""
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import zipfile
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_tracker import Vault  # noqa: E402

OFFSITE = "_Portfolio/99 System/creaite backups"
GIT = shutil.which("git")


def git(root, *args):
    """Run git in `root` with a fixed identity; returns stdout."""
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@example.com"}
    r = subprocess.run([GIT, "-C", str(root), *args], capture_output=True, text=True, env=env, timeout=120)
    if r.returncode:
        raise AssertionError(f"git {args}: {r.stderr}")
    return r.stdout


class Case(unittest.TestCase):
    """A vault, optionally with its projects in a fake OneDrive under a fake HOME (never the real one)."""
    onedrive = True
    today = "2026-10-14 09:00"

    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="creaite-home-")).resolve()
        self.patched = mock.patch.dict(os.environ, {"HOME": str(self.home), "CREAITE_NOW": self.today})
        self.patched.start()
        self.v = Vault()
        self.root = self.home / "OneDrive-Test" / "Engagements"
        if self.onedrive:
            (self.root / "_Portfolio").mkdir(parents=True)
            shutil.copy(self.v.root / "projects/_portfolio/project-register.md", self.root / "_Portfolio" / "project-register.md")
            self.setting("locations", {**self.settings().get("locations", {}), "projects_root": "~/OneDrive-Test/Engagements",
                                       "portfolio": "_Portfolio", "offsite_backup": OFFSITE})
        self.v.run("init")

    def tearDown(self):
        self.v.cleanup()
        shutil.rmtree(self.home, ignore_errors=True)
        self.patched.stop()

    def settings(self):
        return json.loads((self.v.root / "system/config/settings.json").read_text())

    def setting(self, key, value):
        data = self.settings()
        data[key] = value
        (self.v.root / "system/config/settings.json").write_text(json.dumps(data, indent=2))

    def run_script(self, script, *args, ok=True, now=None):
        env = {**os.environ, **({"CREAITE_NOW": now} if now else {})}
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts" / script), *args], env=env, capture_output=True,
                           text=True, timeout=300, cwd=tempfile.gettempdir())
        if ok and r.returncode:
            raise AssertionError(f"{script} {args}: {r.stdout}\n{r.stderr}")
        return r

    def py(self, code, now=None):
        """Run Python inside the vault's scripts folder; returns the last line of output, parsed as JSON."""
        env = {**os.environ, **({"CREAITE_NOW": now} if now else {})}
        r = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts'); " + code],
                           cwd=self.v.root, env=env, capture_output=True, text=True, timeout=300)
        if r.returncode:
            raise AssertionError(r.stdout + r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def offsite(self):
        return self.root / OFFSITE

    def backups(self):
        return self.v.root / "system/backups"

    def start(self, now=None):
        return self.run_script("session.py", "start", "--force", now=now)

    def state(self):
        return json.loads((self.backups() / "backup-state.json").read_text())


@unittest.skipUnless(GIT, "needs git")
class DailyZip(Case):
    def populate(self):
        r = self.v.root
        (r / ".claude/settings.local.json").write_text('{"permissions": {"allow": []}}\n')
        (r / "system/staging/proposed-one.json").write_text('{"items": []}\n')
        (r / "system/staging/vip.json").write_text('{"alerts": []}\n')                # VIP is private to Alan (BL-288)
        (r / "system/staging/ask").mkdir(parents=True, exist_ok=True)
        (r / "system/staging/ask/chat-1.json").write_text('{"text": "mail text"}')
        (r / "system/staging/uploads/ask").mkdir(parents=True, exist_ok=True)
        (r / "system/staging/uploads/ask/img.png").write_bytes(b"png")
        (r / "system/history/flow-2026-10-13.json").write_text("{}")
        (r / "system/history/dashboard-2026-10-13.html").write_text("<html>")
        (r / "system/logs").mkdir(parents=True, exist_ok=True)
        (r / "system/logs/debug-2026-10-13.log").write_text("x")
        (r / "system/releases").mkdir(parents=True, exist_ok=True)
        (r / "system/releases/creaite-1.9.2.zip").write_bytes(b"zip")
        (r / "system/search").mkdir(parents=True, exist_ok=True)
        (r / "system/search/abc.json").write_text("{}")
        (r / "system/processed.txt").write_text("done: one\n")
        git(r, "init", "-q")
        git(r, "add", "CLAUDE.md")
        git(r, "commit", "-q", "-m", "first")

    def test_the_days_zip_is_complete_against_its_manifest_and_holds_exactly_the_agreed_files(self):
        self.populate()
        self.start()
        local = self.backups() / "creaite-backup-2026-10-14.zip"
        far = self.offsite() / "creaite-backup-2026-10-14.zip"
        self.assertTrue(local.is_file())
        self.assertEqual(far.read_bytes(), local.read_bytes())
        self.assertEqual(sorted(p.name for p in self.offsite().iterdir()), ["creaite-backup-2026-10-14.zip"])   # no .part left
        with zipfile.ZipFile(far) as z:
            names = set(z.namelist())
            manifest = json.loads(z.read("manifest.json"))
            for f in manifest["files"]:
                data = z.read(f["path"])
                self.assertEqual((len(data), hashlib.sha256(data).hexdigest()), (f["size"], f["sha256"]))
            self.assertEqual(z.read("system/tracker.db"), (self.backups() / "tracker-2026-10-14.db").read_bytes())  # the closed copy
        self.assertEqual(names - {"manifest.json"}, {f["path"] for f in manifest["files"]})
        self.assertEqual((manifest["day"], manifest["git"]), ("2026-10-14", "bundle"))
        self.assertIn("version", manifest)
        for wanted in ("system/tracker.db", "system/config/settings.json", ".claude/settings.local.json", "CLAUDE.md",
                       "system/staging/proposed-one.json", "vault.bundle", "system/history/flow-2026-10-13.json",
                       "system/processed.txt"):
            self.assertIn(wanted, names)
        for left_out in ("system/staging/ask/", "system/staging/uploads/ask/", "system/staging/vip.json", "system/history/dashboard-", "system/logs/",
                         "system/releases/", "system/search/", "system/scripts/", "system/backups/", ".git/"):
            self.assertFalse([n for n in names if n.startswith(left_out)], left_out)
        r = self.run_script("backup.py", "show", "2026-10-14")
        self.assertIn("Checks out", r.stdout)
        self.assertIn("OneDrive", self.run_script("backup.py", "list").stdout)

    def test_the_zip_and_the_onedrive_copy_appear_only_once_written(self):
        self.populate()
        self.run_script("session.py", "start", "--force")                     # the daily backup exists; now watch a remake
        (self.backups() / "creaite-backup-2026-10-14.zip").unlink()
        (self.offsite() / "creaite-backup-2026-10-14.zip").unlink()
        seen = self.py(
            "import os, shutil, zipfile, backup; seen = []; real_replace, real_copy, real_zip = os.replace, shutil.copyfile, zipfile.ZipFile\n"
            "def rep(a, b):\n"
            "    seen.append(['replace', os.path.basename(a), os.path.basename(b), os.path.exists(b)]); return real_replace(a, b)\n"
            "def cp(a, b):\n"
            "    seen.append(['copy', os.path.basename(b)]); return real_copy(a, b)\n"
            "os.replace, shutil.copyfile = rep, cp\n"
            "backup.make_zip('2026-10-14'); backup.copy_offsite(); print(json.dumps(seen))")
        self.assertEqual(seen, [["replace", ".creaite-backup-2026-10-14.zip.part", "creaite-backup-2026-10-14.zip", False],
                                ["copy", ".creaite-backup-2026-10-14.zip.part"],
                                ["replace", ".creaite-backup-2026-10-14.zip.part", "creaite-backup-2026-10-14.zip", False]])

    def test_onedrive_unreachable_stops_nothing_and_the_next_day_copies(self):
        away = self.root.parent / "Engagements-away"
        os.rename(self.root, away)
        try:
            r = self.start()
        finally:
            os.rename(away, self.root)
        self.assertIn("next day OneDrive can be reached", r.stdout)
        self.assertTrue((self.backups() / "creaite-backup-2026-10-14.zip").is_file())     # made locally all the same
        self.start(now="2026-10-15 09:00")
        self.assertTrue((self.offsite() / "creaite-backup-2026-10-15.zip").is_file())

    def test_doctor_warns_after_two_days_without_a_copy_and_offers_the_fix(self):
        self.start(now="2026-10-12 09:00")
        d = self.run_script("doctor.py", ok=False, now="2026-10-13 09:00").stdout
        self.assertIn("PASS  Off-laptop backup copy — last copy 12-10-2026", d)
        d = self.run_script("doctor.py", ok=False, now="2026-10-14 09:00").stdout
        self.assertIn("WARN  Off-laptop backup copy — last copy 12-10-2026, 2 days ago", d)
        line = next(x for x in d.splitlines() if "Off-laptop backup copy" in x)
        sys.path.insert(0, str(self.v.root / "system/scripts"))
        import health_fixes
        self.assertEqual(health_fixes.fix_for("offsite_backup", line), "offsite")


def ages(today, n):
    """The n days up to and including today, oldest first."""
    return [today - timedelta(days=k) for k in range(n - 1, -1, -1)]


class Retention(Case):
    today = "2026-10-05 09:00"            # 400 days back starts on 01-09-2025, the first of a month
    T = date(2026, 10, 5)

    def touch(self, p, data=b""):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return p

    def lay_out(self):
        b, h, o = self.backups(), self.v.root / "system/history", self.offsite()
        days = ages(self.T, 400)
        self.assertEqual(days[0], date(2025, 9, 1))
        for d in days:
            self.touch(b / f"tracker-{d}.db")
            self.touch(b / f"creaite-backup-{d}.zip")
            self.touch(o / f"creaite-backup-{d}.zip")
            self.touch(o / f"tracker-{d}.db")
            self.touch(b / f"tracker-{d}-120000-apply.db")
            self.touch(b / f"tracker-{d}-120000-apply-2.db")
            self.touch(h / f"dashboard-{d}.html")
            self.touch(h / f"flow-{d}.json")
        foreign = [b / "notes.txt", b / "tracker-2025-09-02.db.keep", b / "creaite-backup-2025-09-02 copy.zip",
                   b / "settings-2025-09-02-120000.json", b / "tracker-2025-09-02-120000-mine.db", h / "dashboard-old.html",
                   o / "my own notes.docx", o / "creaite-backup-2025-13-40.zip", self.v.root / "system/releases/installed.json",
                   self.v.root / "system/releases/creaite-1.0.0 copy.zip"]
        for f in foreign:
            self.touch(f)
        (self.v.root / "VERSION").write_text("1.9.3\n")
        for v in ("1.8.0", "1.9.0", "1.9.1", "1.9.2", "1.9.3", "2.0.0"):
            self.touch(self.v.root / f"system/releases/creaite-{v}.zip")
        for n in range(5):
            self.touch(b / f"update-2026-0{n + 1}-01-120000-1.{n}.0-to-1.{n + 1}.0" / "update.json", b"{}")
        self.touch(b / "update-2025-01-01-120000-0.9.0-to-1.0.0" / "notes.txt")        # no update.json: not creaite's backup
        log = []
        for n in range(1, 11):
            made = self.T - timedelta(days=30 * (10 - n) + 5)     # 275, 245, … 5 days ago
            self.touch(b / "files/changes" / f"{n:04d}" / "a.md")
            log.append(json.dumps({"id": n, "at": f"{made} 10:00:00", "op": "edit", "path": "x"}))
        (self.v.root / "system/config/files-log.jsonl").write_text("\n".join(log) + "\n")
        return foreign

    def expected_daily(self):
        return {d for d in ages(self.T, 400) if (self.T - d).days < 30 or d.day == 1 or (self.T - d).days < 365 and d.weekday() == 0}

    def dates_of(self, folder, prefix, suffix):
        out = set()
        for p in folder.iterdir():
            if p.name.startswith(prefix) and p.name.endswith(suffix) and len(p.name) == len(prefix) + 10 + len(suffix):
                try:
                    out.add(date.fromisoformat(p.name[len(prefix):len(prefix) + 10]))
                except ValueError:      # the foreign creaite-backup-2025-13-40.zip
                    continue
        return out

    def test_400_days_keep_exactly_the_agreed_set_and_never_a_foreign_file(self):
        foreign = self.lay_out()
        dry = self.run_script("backup.py", "tidy", "--dry-run").stdout
        self.assertIn("would remove", dry)
        self.assertEqual(len(list(self.backups().glob("tracker-????-??-??.db"))), 400)       # a dry run removes nothing
        out = self.run_script("backup.py", "tidy").stdout
        self.assertIn("removed", out)
        b, h, o = self.backups(), self.v.root / "system/history", self.offsite()
        want = self.expected_daily()
        self.assertEqual(self.dates_of(b, "tracker-", ".db"), want)
        self.assertEqual(self.dates_of(b, "creaite-backup-", ".zip"), want)
        self.assertEqual(self.dates_of(o, "creaite-backup-", ".zip"), want)
        self.assertEqual(self.dates_of(o, "tracker-", ".db"), want)
        copies = {p.name for p in b.glob("tracker-*-120000-apply*.db")}
        self.assertEqual(copies, {f"tracker-{d}-120000-apply{s}.db" for d in ages(self.T, 14) for s in ("", "-2")})
        self.assertEqual(self.dates_of(h, "dashboard-", ".html"),
                         {d for d in ages(self.T, 400) if (self.T - d).days < 30 or d.day == 1})
        self.assertEqual(len(list(h.glob("flow-*.json"))), 400)                                 # kept for good
        self.assertEqual(sorted(p.name for p in (self.v.root / "system/releases").glob("creaite-?.?.?.zip")),
                         ["creaite-1.9.1.zip", "creaite-1.9.2.zip", "creaite-1.9.3.zip", "creaite-2.0.0.zip"])
        self.assertEqual(sorted(p.name for p in b.glob("update-*")),
                         ["update-2025-01-01-120000-0.9.0-to-1.0.0", "update-2026-03-01-120000-1.2.0-to-1.3.0",
                          "update-2026-04-01-120000-1.3.0-to-1.4.0", "update-2026-05-01-120000-1.4.0-to-1.5.0"])
        self.assertEqual(sorted(p.name for p in (b / "files/changes").iterdir()), ["0008", "0009", "0010"])   # 65, 35, 5 days
        for f in foreign:
            self.assertTrue(f.exists(), f)
        st = self.state()["tidy"]
        self.assertEqual(st["day"], "2026-10-05")
        self.assertGreater(st["removed"], 1000)
        d = self.run_script("doctor.py", ok=False).stdout
        self.assertRegex(d, r"PASS  Tidy up of old backups — Tidy up, 05-10-2026: removed \d+ files")

    def test_never_the_newest_of_a_kind(self):
        b = self.backups()
        old = self.T - timedelta(days=500)
        for name in (f"tracker-{old}-120000-apply.db", f"tracker-{old}-130000-undo.db", f"creaite-backup-{old}.zip",
                     f"tracker-{old + timedelta(days=3)}.db"):
            self.touch(b / name)
        self.touch(self.v.root / f"system/history/dashboard-{old + timedelta(days=3)}.html")
        self.touch(b / "files/changes/0001/a.md")
        self.touch(b / "files/changes/0002/a.md")
        (self.v.root / "system/config/files-log.jsonl").write_text(
            "".join(json.dumps({"id": n, "at": f"{old} 10:00:00"}) + "\n" for n in (1, 2)))
        self.run_script("backup.py", "tidy")
        left = {p.name for p in b.iterdir()}
        self.assertNotIn(f"tracker-{old}-120000-apply.db", left)
        self.assertIn(f"tracker-{old}-130000-undo.db", left)                  # the newest copy stays, however old
        self.assertIn(f"creaite-backup-{old}.zip", left)
        self.assertIn(f"tracker-{old + timedelta(days=3)}.db", left)
        self.assertTrue((self.v.root / f"system/history/dashboard-{old + timedelta(days=3)}.html").exists())
        self.assertEqual(sorted(p.name for p in (b / "files/changes").iterdir()), ["0002"])

    def test_releases_are_left_alone_without_the_installed_one(self):
        (self.v.root / "VERSION").write_text("1.9.3\n")
        for v in ("1.0.0", "1.1.0", "1.2.0", "1.3.0"):
            self.touch(self.v.root / f"system/releases/creaite-{v}.zip")
        self.run_script("backup.py", "tidy")
        self.assertEqual(len(list((self.v.root / "system/releases").glob("*.zip"))), 4)

    def test_never_in_the_development_repository(self):
        self.touch(self.backups() / f"tracker-{self.T - timedelta(days=100)}-120000-apply.db")
        self.touch(self.backups() / f"tracker-{self.T}-120000-apply.db")
        (self.v.root / ".creaite-dev").write_text("")
        r = self.run_script("backup.py", "tidy", ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("development repository", r.stdout)
        self.assertEqual(len(list(self.backups().glob("tracker-*-apply.db"))), 2)


class Automatic(Case):
    """Tidy up runs by itself once a day after the backup and the zip, and not when the zip failed."""
    onedrive = False

    def old_copy(self):
        return self.backups() / "tracker-2026-06-01-120000-apply.db"

    def test_once_a_day_after_the_zip(self):
        self.old_copy().write_bytes(b"")
        (self.backups() / "tracker-2026-10-14-120000-apply.db").write_bytes(b"")
        self.start()
        self.assertFalse(self.old_copy().exists())
        self.assertEqual(self.state()["tidy"]["day"], "2026-10-14")
        self.assertEqual(self.state()["verify"]["ok"], True)

    def test_an_ask_creaite_run_never_triggers_a_deletion(self):
        """Alan, 14-10-2026: session start or session backup called from an ask creaite run (the live server's flag, or
        system/guard/run.json present) makes the backup and the zip but never runs Tidy up."""
        self.old_copy().write_bytes(b"")
        (self.backups() / "tracker-2026-10-14-120000-apply.db").write_bytes(b"")      # so the old copy isn't the newest
        env = {**os.environ, "CREAITE_HEADLESS_RUN": "1"}
        for cmd in (["start", "--force"], ["backup"]):
            r = subprocess.run([sys.executable, str(self.v.root / "system/scripts/session.py"), *cmd], env=env,
                               capture_output=True, text=True, timeout=120)
            self.assertIn(r.returncode, (0, 1), r.stderr)
        guard = self.v.root / "system/guard"
        guard.mkdir(parents=True, exist_ok=True)
        (guard / "run.json").write_text('{"run": "r1", "mode": "ask"}')               # the server's record of a run in progress
        self.start()
        self.assertTrue(self.old_copy().exists())                                    # nothing deleted
        self.assertTrue((self.backups() / "creaite-backup-2026-10-14.zip").is_file())  # the backup itself still made
        self.assertNotIn("tidy", self.state())
        (guard / "run.json").unlink()
        self.start()                                                                 # Alan's own session: Tidy up runs
        self.assertFalse(self.old_copy().exists())

    def test_not_when_todays_zip_failed(self):
        self.old_copy().write_bytes(b"")
        (self.backups() / "creaite-backup-2026-10-14.zip").mkdir(parents=True)   # forced fault: the zip can't be written
        r = self.start()
        self.assertIn("Daily backup zip not made", r.stdout)
        self.assertTrue(self.old_copy().exists())
        self.assertNotIn("tidy", self.state())


@unittest.skipUnless(GIT, "needs git")
class RestoreCheck(Case):
    onedrive = False

    def setUp(self):
        super().setUp()
        git(self.v.root, "init", "-q")
        git(self.v.root, "add", "CLAUDE.md")
        git(self.v.root, "commit", "-q", "-m", "first")
        self.start()
        self.zip = self.backups() / "creaite-backup-2026-10-14.zip"

    def rewrite(self, change):
        """Rewrite the zip through `change(files: dict) -> manifest edits`, keeping the manifest's checksums unless told."""
        with zipfile.ZipFile(self.zip) as z:
            files = {n: z.read(n) for n in z.namelist()}
        change(files)
        with zipfile.ZipFile(self.zip, "w") as z:
            for n, data in files.items():
                z.writestr(n, data)

    def check(self):
        r = self.run_script("backup.py", "check", ok=False)
        d = self.run_script("doctor.py", ok=False).stdout
        return r, d

    def test_a_good_backup_passes(self):
        r, d = self.check()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("PASS  Backup restore check — passed 14-10-2026", d)

    def test_a_corrupt_daily_backup(self):
        db = self.backups() / "tracker-2026-10-14.db"
        db.write_bytes(db.read_bytes()[:100] + b"\x00garbage" * 500)
        r, d = self.check()
        self.assertEqual(r.returncode, 1)
        self.assertIn("tracker-2026-10-14.db fails the integrity check", r.stdout)
        self.assertIn("WARN  Backup restore check", d)
        self.assertIn("backup.py check", d)                                        # says what to do

    def test_a_missing_file(self):
        self.rewrite(lambda f: f.pop("system/config/settings.json"))
        r, _ = self.check()
        self.assertIn("system/config/settings.json is listed in the manifest but missing", r.stdout)

    def test_a_corrupt_database_inside_the_zip(self):
        def spoil(f):
            bad = f["system/tracker.db"][:100] + b"\x00garbage" * 500
            m = json.loads(f["manifest.json"])
            for e in m["files"]:
                if e["path"] == "system/tracker.db":
                    e.update(size=len(bad), sha256=hashlib.sha256(bad).hexdigest())
            f["system/tracker.db"], f["manifest.json"] = bad, json.dumps(m).encode()
        self.rewrite(spoil)
        r, _ = self.check()
        self.assertIn("its database fails the integrity check", r.stdout)

    def test_a_bad_bundle(self):
        def spoil(f):
            good = f["vault.bundle"]
            bad = good[:len(good) - 30] + b"\x00" * 30          # the pack's end damaged
            m = json.loads(f["manifest.json"])
            for e in m["files"]:
                if e["path"] == "vault.bundle":
                    e.update(size=len(bad), sha256=hashlib.sha256(bad).hexdigest())
            f["vault.bundle"], f["manifest.json"] = bad, json.dumps(m).encode()
        self.rewrite(spoil)
        r, _ = self.check()
        self.assertIn("its git history can't be read", r.stdout)

    def test_a_changed_file(self):
        self.rewrite(lambda f: f.update({"CLAUDE.md": b"changed"}))
        r, _ = self.check()
        self.assertIn("CLAUDE.md doesn't match its checksum", r.stdout)


@unittest.skipUnless(GIT, "needs git")
class Restore(Case):
    onedrive = False

    def test_a_restore_into_a_fresh_vault_gives_a_working_vault(self):
        a = self.v.root
        self.setting("identity", {**self.settings().get("identity", {}), "name": "Restored Person"})
        (a / "system/staging/proposed-kept.json").write_text('{"items": []}\n')
        git(a, "init", "-q")
        git(a, "add", "CLAUDE.md")
        git(a, "commit", "-q", "-m", "the vault's history")
        self.start()
        zip_path = self.backups() / "creaite-backup-2026-10-14.zip"
        b = Vault()                                     # a fresh vault, as a release makes it: no database, no history
        try:
            (b.root / "CLAUDE.md").unlink()
            dry = b.run("restore", str(zip_path), "--dry-run", script="backup.py").stdout
            self.assertIn("database: replaces system/tracker.db", dry)
            self.assertFalse((b.root / "system/tracker.db").exists())             # a dry run changes nothing
            b.run("restore", str(zip_path), script="backup.py")
            with sqlite3.connect(b.root / "system/tracker.db") as con:
                self.assertEqual(con.execute("SELECT code FROM projects").fetchall(), [("ABC",)])
            s = json.loads((b.root / "system/config/settings.json").read_text())
            self.assertEqual(s["identity"]["name"], "Restored Person")
            self.assertIn("daily_days", s["backups"])                              # merged: this version's keys are there
            self.assertTrue((b.root / "system/staging/proposed-kept.json").is_file())
            self.assertEqual((b.root / "CLAUDE.md").read_bytes(), (a / "CLAUDE.md").read_bytes())
            self.assertIn("the vault's history", git(b.root, "log", "--oneline"))
            self.assertEqual(git(b.root, "status", "--porcelain", "CLAUDE.md"), "")  # the working files match the history
            d = b.run(script="doctor.py", ok=False).stdout
            self.assertIn(" 0 failed", d, d)
            # again, into a vault that has its own database and CLAUDE.md: both kept first, CLAUDE.md left alone
            (b.root / "CLAUDE.md").write_text("mine")
            out = b.run("restore", "2026-10-14", script="backup.py", ok=False)
            self.assertIn("no backup of 14-10-2026", out.stdout)                   # b has no zips of its own
            out = b.run("restore", str(zip_path), script="backup.py").stdout
            self.assertIn("your CLAUDE.md: kept as it is", out)
            self.assertEqual((b.root / "CLAUDE.md").read_text(), "mine")
            self.assertTrue(list((b.root / "system/backups").glob("tracker-*-restore.db")))
        finally:
            b.cleanup()

    def test_a_zip_with_a_path_outside_a_backup_is_refused(self):
        self.start()
        zip_path = self.backups() / "creaite-backup-2026-10-14.zip"
        with zipfile.ZipFile(zip_path, "a") as z:
            z.writestr("projects/ABC Example Programme/minutes/x.docx", b"x")
        r = self.run_script("backup.py", "restore", str(zip_path), ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("isn't something a creaite backup holds", r.stdout)

    def test_never_in_the_development_repository(self):
        self.start()
        (self.v.root / ".creaite-dev").write_text("")
        r = self.run_script("backup.py", "restore", "2026-10-14", ok=False)
        self.assertIn("never runs in the development repository", r.stdout)


class FileChangeUndo(Case):
    onedrive = False

    def test_undo_says_the_backup_has_gone(self):
        draft = self.v.root / "system/staging/drafts/note.md"
        draft.write_text("one")
        new = self.v.root / "system/staging/drafts/new.md"
        new.write_text("two")
        self.run_script("filechange.py", "edit", "system/staging/drafts/note.md", "--from", "system/staging/drafts/new.md",
                        "--why", "test")
        shutil.rmtree(self.backups() / "files/changes")
        r = self.run_script("filechange.py", "undo", ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("the backup of change 1 has gone", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
