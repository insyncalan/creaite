"""BL-320: Health's Fix it (fixed routes running fixed commands) and update.py's after-update steps.

Run: python3 dev/tests/test_health_fixes.py

Alan's guard decision (14-10-2026): each Fix it calls a fixed live-server route that runs exactly one known command, with no
arguments from the page, shows what it will do first and logs it; the Microsoft 365 reconnect only opens Claude's connector page.
Everything runs in a throwaway vault with a throwaway HOME (so ~/Applications is a temporary folder) and a fake OneDrive under
it; nothing here touches the real ~/Applications, a real OneDrive, Microsoft 365 or a LaunchAgent.
"""
import json
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
import zipfile
from contextlib import closing
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "system" / "scripts"))
from test_tracker import Vault  # noqa: E402
import health_fixes  # noqa: E402
import reach  # noqa: E402

OTHER_VAULT = "/tmp/some-other-creaite-vault"
OFFSITE = "_Portfolio/99 System/creaite backups"


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def fake_launcher(home, vault, name="creaite"):
    """An old-style launcher in <home>/Applications that opens `vault` (no Info.plist, no icon)."""
    app = home / "Applications" / f"{name}.app"
    exe = app / "Contents" / "MacOS" / "creaite"
    exe.parent.mkdir(parents=True)
    exe.write_text(f'#!/bin/bash\ncd "{vault}" && exec /bin/true\n', encoding="utf-8")
    exe.chmod(0o755)
    return app


class Catalogue(unittest.TestCase):
    """The fixes are a fixed list, mapped from doctor's check ids, and none touches Microsoft 365, permissions or the record."""

    def test_the_fixes_are_the_ones_alan_decided(self):
        self.assertEqual(set(health_fixes.FIXES), {"launcher", "rosetta", "icon", "m365", "offsite", "old_archive",
                                                      "archive_reports"})   # BL-09, BL-03
        commands = {k: f.get("command") for k, f in health_fixes.FIXES.items()}
        self.assertEqual(commands, {"launcher": ("launch.py", "make-launcher", "--replace"),
                                    "rosetta": ("launch.py", "make-launcher", "--if-present"),
                                    "icon": ("launch.py", "refresh-icon"), "m365": None,
                                    "offsite": ("session.py", "backup"),
                                    "old_archive": ("propose.py", "old-archives"),         # BL-09: prints the change for the card
                                    "archive_reports": ("archive.py", "reports")})         # BL-03: the same
        self.assertEqual(health_fixes.FIXES["m365"]["url"], "https://claude.ai/settings/connectors")

    def test_no_fix_runs_a_record_permission_or_microsoft_365_command(self):
        for fid, f in health_fixes.FIXES.items():
            if "command" not in f:
                continue
            if f.get("card"):                                 # BL-09: only prints a change, which waits on the approval card
                self.assertEqual(reach.command_kind(f["command"][0], list(f["command"][1:]))[0], "read")
                continue
            script, *words = f["command"]
            with self.subTest(fid):
                self.assertNotIn(script, ("tracker.py", "review.py", "propose.py", "permissions.py", "update.py", "excel_sync.py",
                                          "sweep.py", "filechange.py"))
                kind, _ = reach.command_kind(script, words)
                self.assertIn(kind, ("derived", "record") if script == "launch.py" else ("derived",))   # launch.py: never the panel's
                self.assertFalse(any(w.startswith("mcp__") for w in words))

    def test_the_fix_map_uses_healths_check_ids_and_their_details(self):
        fix = health_fixes.fix_for
        self.assertEqual(fix("launcher_vault", "~/Applications/creaite.app opens another vault (/x), not this one"), "launcher")
        self.assertIsNone(fix("launcher_vault", "no launcher"))
        self.assertEqual(fix("python_version", "3.12.1; running under Rosetta (as an Intel program): …"), "rosetta")
        self.assertEqual(fix("python_version", "/x/creaite.app is an old launcher that may run under Rosetta: make it again"),
                         "rosetta")
        self.assertIsNone(fix("python_version", "3.12.1"))
        self.assertEqual(fix("offsite_backup", "no copy yet in _Portfolio/99 System/creaite backups: it is made after …"), "offsite")
        self.assertEqual(fix("offsite_backup", "last copy 01-10-2026, 13 days ago: is OneDrive running?"), "offsite")
        self.assertIsNone(fix("offsite_backup", "can't write to _Portfolio/99 System/creaite backups"))
        for check in ("database", "search_index", "assistant_permissions", "assistant_guard", "vendored", "version", "new_vault"):
            self.assertIsNone(fix(check, "anything"), check)          # record, engine, permissions, set-up: never a Fix it
        cat = health_fixes.catalogue()
        self.assertEqual(cat["checks"], {"launcher_vault": "launcher", "python_version": "rosetta", "offsite_backup": "offsite",
                                         "old_archive_folders": "old_archive",                  # BL-09
                                         "archive_reports": "archive_reports"})                 # BL-03
        self.assertEqual(cat["standalone"], ["icon", "m365"])
        for d in cat["fixes"]:
            self.assertTrue(d["does"] and d["title"] and d["button"] and d["built"])
            self.assertTrue(("url" in d) != ("command" in d))
            if "command" in d:
                self.assertTrue(d["command"].startswith("system/scripts/run "))

    def test_ask_creaite_still_cannot_run_any_fix_command(self):
        """BL-141 unchanged: launch.py is never run by the panel; session.py backup is only what session start does already."""
        for f in health_fixes.FIXES.values():
            if "command" in f and f["command"][0] == "launch.py":
                for head in ("python3 system/scripts/", "system/scripts/run "):
                    self.assertIn("never does", reach.bash_problem(head + " ".join(f["command"])))
        self.assertEqual(reach.command_kind("session.py", ["backup"])[0], reach.command_kind("session.py", ["start"])[0])


class FixRoutes(unittest.TestCase):
    """The routes, through a real live server whose HOME is a throwaway folder and whose projects live in a fake OneDrive."""

    @classmethod
    def setUpClass(cls):
        cls.home = Path(tempfile.mkdtemp(prefix="creaite-home-")).resolve()
        cls.v = Vault()
        cls.v.run("init")
        cls.port = free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.env = {**os.environ, "HOME": str(cls.home), "CREAITE_PORT": str(cls.port)}
        cls.proc = subprocess.Popen([sys.executable, str(cls.v.root / "system/scripts/live_server.py")], env=cls.env,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                urllib.request.urlopen(cls.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        html = urllib.request.urlopen(cls.base + "/").read().decode()
        cls.token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.v.cleanup()
        shutil.rmtree(cls.home, ignore_errors=True)

    def setUp(self):
        shutil.rmtree(self.home / "Applications", ignore_errors=True)
        if (self.home / "Applications").is_file():
            (self.home / "Applications").unlink()

    def post(self, path, body=None, token=None, raw=None):
        data = raw if raw is not None else (b"" if body is None else json.dumps(body).encode())
        req = urllib.request.Request(self.base + path, data=data, method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": token or self.token})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            with e:
                return e.code, json.loads(e.read() or b"{}")

    def fix_log(self):
        f = self.v.root / "system/staging/health-fixes.jsonl"
        return [json.loads(ln) for ln in f.read_text().splitlines()] if f.exists() else []

    def manifest_icons(self):
        with urllib.request.urlopen(self.base + "/manifest.webmanifest") as r:
            return [i["src"] for i in json.loads(r.read())["icons"]]

    # ── the routes themselves ──
    def test_the_list_says_what_each_fix_does_before_it_runs(self):
        code, got = self.post("/api/health/fixes")
        self.assertEqual(code, 200)
        self.assertEqual([f["id"] for f in got["fixes"]], list(health_fixes.FIXES))
        self.assertEqual(got["checks"]["launcher_vault"], "launcher")

    def test_without_the_token_nothing_runs(self):
        before = len(self.fix_log())
        for path in ("/api/health/fixes", "/api/health/fix/icon", "/api/health/fix/m365"):
            self.assertEqual(self.post(path, token="wrong")[0], 403, path)
        self.assertEqual(len(self.fix_log()), before)

    def test_the_page_can_send_nothing_but_the_fix_id(self):
        before = len(self.fix_log())
        self.assertEqual(self.post("/api/health/fix/icon", {"command": "launch.py agent install"})[0], 400)
        self.assertEqual(self.post("/api/health/fix/icon", {"args": ["--replace"]})[0], 400)
        self.assertEqual(self.post("/api/health/fix/icon?x=1")[0], 400)
        self.assertEqual(self.post("/api/health/fix/agent")[0], 404)
        self.assertEqual(self.post("/api/health/fix/../launch")[0], 404)
        self.assertEqual(self.post("/api/health/fix/")[0], 404)
        self.assertEqual(len(self.fix_log()), before)

    def test_a_get_runs_nothing(self):
        before = len(self.fix_log())
        try:
            urllib.request.urlopen(self.base + "/api/health/fix/icon", timeout=10).read()
        except urllib.error.HTTPError as e:
            e.close()
        self.assertEqual(len(self.fix_log()), before)

    # ── each fix, working and with a forced fault ──
    def test_launcher_fix_replaces_a_launcher_that_opens_another_vault(self):
        app = fake_launcher(self.home, OTHER_VAULT)
        code, got = self.post("/api/health/fix/launcher", {})
        self.assertEqual(code, 200)
        self.assertTrue(got["ok"], got)
        text = (app / "Contents/MacOS/creaite").read_text()
        self.assertIn(f'cd "{self.v.root.resolve()}"', text)
        self.assertIn("arm64", (app / "Contents/Info.plist").read_text())
        self.assertEqual(self.fix_log()[-1]["fix"], "launcher")
        self.assertTrue(self.fix_log()[-1]["ok"])

    def test_launcher_fix_fault_is_reported(self):
        (self.home / "Applications").write_text("not a folder")          # forced fault: ~/Applications can't hold the app
        code, got = self.post("/api/health/fix/launcher")
        self.assertEqual(code, 200)
        self.assertFalse(got["ok"], got)
        self.assertTrue(got["message"])
        self.assertFalse(self.fix_log()[-1]["ok"])

    def test_rosetta_fix_remakes_only_this_vaults_launcher(self):
        mine = fake_launcher(self.home, self.v.root.resolve())
        code, got = self.post("/api/health/fix/rosetta")
        self.assertTrue(got["ok"], got)
        self.assertIn("LSArchitecturePriority", (mine / "Contents/Info.plist").read_text())   # natively, never Rosetta
        shutil.rmtree(mine)
        other = fake_launcher(self.home, OTHER_VAULT)                    # another vault's launcher is never touched
        code, got = self.post("/api/health/fix/rosetta")
        self.assertTrue(got["ok"], got)
        self.assertIn("no launcher for this vault", got["message"])
        self.assertIn(OTHER_VAULT, (other / "Contents/MacOS/creaite").read_text())
        self.assertFalse((other / "Contents/Info.plist").exists())

    def test_rosetta_fix_fault_is_reported(self):
        mine = fake_launcher(self.home, self.v.root.resolve())
        (mine / "Contents").chmod(0o500)                                  # forced fault: the old launcher can't be removed
        try:
            code, got = self.post("/api/health/fix/rosetta")
            self.assertFalse(got["ok"], got)
        finally:
            (mine / "Contents").chmod(0o755)

    def test_icon_fix_gives_the_manifest_new_icon_addresses(self):
        before = self.manifest_icons()
        self.assertTrue(all("?v=" in s for s in before))
        time.sleep(1.1)                                                   # the mark is in seconds
        code, got = self.post("/api/health/fix/icon")
        self.assertTrue(got["ok"], got)
        after = self.manifest_icons()
        self.assertNotEqual(before, after)
        self.assertEqual([s.split("?")[0] for s in before], [s.split("?")[0] for s in after])
        with urllib.request.urlopen(self.base + after[0]) as r:           # the new address still serves the icon
            self.assertEqual(r.headers.get_content_type(), "image/png")

    def test_icon_fix_fault_is_reported(self):
        stamp = self.v.root / "system/staging/app-icon.json"
        saved = stamp.read_bytes() if stamp.is_file() else None
        stamp.unlink(missing_ok=True)
        stamp.mkdir()                                                     # forced fault: the stamp can't be written
        try:
            code, got = self.post("/api/health/fix/icon")
            self.assertFalse(got["ok"], got)
        finally:
            stamp.rmdir()
            if saved is not None:
                stamp.write_bytes(saved)

    def test_m365_fix_only_opens_claudes_connector_page(self):
        code, got = self.post("/api/health/fix/m365")
        self.assertEqual(code, 200)
        self.assertEqual(got["url"], "https://claude.ai/settings/connectors")
        self.assertEqual(self.fix_log()[-1], {**self.fix_log()[-1], "fix": "m365", "ok": True, "code": None})

    def test_offsite_fix_with_the_projects_in_the_vault_has_nothing_to_copy(self):
        code, got = self.post("/api/health/fix/offsite")
        self.assertTrue(got["ok"], got)
        self.assertIn("no OneDrive copy to make", got["message"])

    # ── BL-09: the zz Archive rename goes on the approval card, and moves nothing before Approve ──
    def test_old_archive_fix_with_nothing_to_rename(self):
        code, got = self.post("/api/health/fix/old_archive")
        self.assertFalse(got["ok"], got)
        self.assertIn("nothing to rename", got["message"])

    def test_old_archive_fix_puts_the_renames_on_the_card_and_approve_makes_them(self):
        abc = next(d for d in (self.v.root / "projects").iterdir() if d.name.startswith("ABC "))
        old = abc / "zz Archive"
        (old / "sub").mkdir(parents=True)
        (old / "sub" / "a.md").write_text("a")
        self.addCleanup(shutil.rmtree, old, True)
        self.addCleanup(shutil.rmtree, abc / "_Archive", True)
        code, got = self.post("/api/health/fix/old_archive")
        self.assertTrue(got["ok"] and got["card"], got)
        self.assertTrue(old.is_dir())                                      # nothing moved yet
        _, pend = self.post("/api/edit/pending", {})
        card = pend["card"]
        self.assertTrue(card["valid"], card)
        self.assertIn(f"Move folder projects/{abc.name}/zz Archive/ → projects/{abc.name}/_Archive/", card["lines"])
        _, done = self.post("/api/edit/approve", {"card": card["card"]})
        self.assertTrue(done["ok"], done)
        self.assertFalse(old.exists())
        self.assertEqual((abc / "_Archive" / "sub" / "a.md").read_text(), "a")
        self.assertEqual(self.fix_log()[-1]["fix"], "old_archive")

    def test_a_fix_waits_for_a_running_job(self):
        """The fix runs under the same lock as Apply: while a job holds it, the fix says so and runs nothing."""
        # The lock is the server's own; the test can only hold it from inside, so check the route's code holds it.
        src = (REPO / "system/scripts/live_server.py").read_text()
        body = src[src.index("def health_fix_route"):src.index("def post_or_health")]
        self.assertIn("LOCK.acquire(blocking=False)", body)
        self.assertIn("LOCK.release()", body)


class OffsiteBackup(unittest.TestCase):
    """session.py backup (the offsite fix's command) in a vault whose projects live in a fake OneDrive under a fake HOME."""

    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="creaite-home-")).resolve()
        self.patched = mock.patch.dict(os.environ, {"HOME": str(self.home)})   # never the real home, for every child process
        self.patched.start()
        self.root = self.home / "OneDrive-Test" / "Engagements"
        (self.root / "_Portfolio").mkdir(parents=True)
        self.v = Vault()
        reg = self.v.root / "projects/_portfolio/project-register.md"
        shutil.copy(reg, self.root / "_Portfolio" / "project-register.md")
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text())
        data["locations"] = {**data.get("locations", {}), "projects_root": "~/OneDrive-Test/Engagements",
                             "portfolio": "_Portfolio", "offsite_backup": OFFSITE}
        cfg.write_text(json.dumps(data, indent=2))
        self.v.run("init")
        self.env = {**os.environ, "HOME": str(self.home)}

    def tearDown(self):
        self.v.cleanup()
        shutil.rmtree(self.home, ignore_errors=True)
        self.patched.stop()

    def backup(self):
        return subprocess.run([sys.executable, str(self.v.root / "system/scripts/session.py"), "backup"], env=self.env,
                              capture_output=True, text=True, timeout=60)

    def test_it_makes_todays_backup_and_the_onedrive_copy(self):
        r = self.backup()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("OneDrive copy made", r.stdout)
        copies = list((self.root / OFFSITE).glob("creaite-backup-*.zip"))         # BL-323: the day's closed zip
        self.assertEqual(len(copies), 1)
        with zipfile.ZipFile(copies[0]) as z, tempfile.TemporaryDirectory() as work:
            (Path(work) / "t.db").write_bytes(z.read("system/tracker.db"))
            with closing(sqlite3.connect(Path(work) / "t.db")) as con:
                self.assertTrue(con.execute("SELECT count(*) FROM sqlite_master").fetchone()[0])
        r = self.backup()                                                  # again: nothing new to copy
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("already holds the newest copy", r.stdout)

    def test_a_projects_folder_that_cant_be_reached_is_a_failure(self):
        shutil.rmtree(self.root)                                           # forced fault: OneDrive isn't there
        r = self.backup()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("wasn't made", r.stdout)

    def test_daily_backups_off_makes_nothing(self):
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text())
        data.setdefault("backups", {})["daily"] = False
        cfg.write_text(json.dumps(data, indent=2))
        r = self.backup()
        self.assertEqual(r.returncode, 1)
        self.assertFalse((self.root / OFFSITE).exists())


class AfterUpdate(unittest.TestCase):
    """update.py's after-update steps: run in order, each reported; the first that fails stops them (and the install rolls back)."""

    def setUp(self):
        import update
        self.update = update

    def test_each_step_is_reported_in_order(self):
        calls = []

        def fake(*cmd):
            calls.append(cmd)
            return 0, f"line one\n{cmd[1]} done"
        with mock.patch.object(self.update, "run_script", fake):
            said = self.update.after_update()
        self.assertEqual(calls, [("launch.py", "make-launcher", "--if-present"), ("launch.py", "refresh-icon"),
                                 ("launch.py", "restart")])
        self.assertEqual(said, ["Launcher: make-launcher done", "App icon: refresh-icon done", "Live server: restart done"])

    def test_a_failed_step_raises_and_stops_the_rest(self):
        calls = []

        def fake(*cmd):
            calls.append(cmd)
            return (1, "couldn't write the stamp") if cmd[1] == "refresh-icon" else (0, "ok")
        with mock.patch.object(self.update, "run_script", fake):
            with self.assertRaises(self.update.UpdateError) as e:
                self.update.after_update()
        self.assertIn("App icon", str(e.exception))
        self.assertEqual(len(calls), 2)                                    # the restart never ran

    def test_restart_hint(self):
        self.assertEqual(self.update.restart_hint(["Live server: The live server on port 8765 restarts on the new version …"]), "")
        self.assertIn("Restart the live server", self.update.restart_hint(["Live server: The live server isn't running, so …"]))


class LaunchCommands(unittest.TestCase):
    """launch.py's new commands with nothing to do: no launcher, no server."""

    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="creaite-home-")).resolve()
        self.v = Vault()
        self.env = {**os.environ, "HOME": str(self.home)}

    def tearDown(self):
        self.v.cleanup()
        shutil.rmtree(self.home, ignore_errors=True)

    def launch(self, *args):
        return subprocess.run([sys.executable, str(self.v.root / "system/scripts/launch.py"), *args], env=self.env,
                              capture_output=True, text=True, timeout=60)

    def test_no_launcher_and_no_server_change_nothing(self):
        r = self.launch("make-launcher", "--if-present")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("no launcher for this vault", r.stdout)
        self.assertFalse((self.home / "Applications").exists())
        r = self.launch("restart")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("isn't running", r.stdout)

    def test_a_stale_server_file_is_never_signalled(self):
        """A pid left behind (here: this test's own process) isn't a live server answering for this vault: no signal is sent."""
        f = self.v.root / "system/staging/live-server.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({"pid": os.getpid(), "port": free_port()}))
        r = self.launch("restart")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("isn't running", r.stdout)


if __name__ == "__main__":
    unittest.main()
