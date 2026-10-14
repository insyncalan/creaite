"""Tests for creating a new vault from a release zip (live vault readiness, v1.0.0).

Run: python3 dev/tests/test_new_vault.py
Builds a release zip from this repository's working files (--dirty), then creates throwaway vaults from it, both by
running the zip (python3 creaite-X.Y.Z.zip <folder>) and with update.py new-vault.
"""
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import REPO  # noqa: E402
from test_update import VERSION, build_release, remake  # noqa: E402

sys.path.insert(0, str(REPO / "system" / "scripts"))
import paths  # noqa: E402
import update  # noqa: E402


def keys(d, prefix=""):
    """Every key path in a settings dict; an empty dict in the defaults is a data map (e.g. prep.series)."""
    out = set()
    for k, v in d.items():
        out.add(prefix + k)
        if isinstance(v, dict) and v:
            out |= keys(v, prefix + k + ".")
    return out


class TestDefaults(unittest.TestCase):
    def test_defaults_cover_every_setting_and_carry_no_trial_values(self):
        repo = json.loads(paths.SETTINGS.read_text(encoding="utf-8"))
        defaults = json.loads((paths.TEMPLATES / "settings-defaults.json").read_text(encoding="utf-8"))
        data_maps = {k for k in keys(defaults) if isinstance(eval_path(defaults, k), dict) and not eval_path(defaults, k)}
        missing = {k for k in keys(repo) if k not in keys(defaults) and not any(k.startswith(m + ".") for m in data_maps)}
        self.assertEqual(missing, set(), "settings-defaults.json lacks keys the code uses")
        self.assertEqual((defaults["dashboard"]["palette"], defaults["dashboard"]["theme"]), ("creaite", "System"))
        self.assertEqual(defaults["identity"], {"name": "", "short_forms": [], "own_domains": []})
        self.assertEqual((defaults["reminders"]["dismissed_forever"], defaults["people"]["added"], defaults["prep"]["series"]),
                         ([], [], {}))


def eval_path(d, k):
    for part in k.split("."):
        d = d[part]
    return d


class TestNewVault(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.zip = build_release()
        cls.tmp = Path(tempfile.mkdtemp(prefix="creaite-newvault-"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)
        shutil.rmtree(cls.zip.parent, ignore_errors=True)

    def make(self, name, via_zip=True):
        target = self.tmp / name
        cmd = ([sys.executable, str(self.zip), str(target)] if via_zip else
               [sys.executable, str(REPO / "system/scripts/update.py"), "new-vault", str(self.zip), str(target)])
        r = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL)
        return target, r

    def test_zip_contents(self):
        with zipfile.ZipFile(self.zip) as z:
            names = set(z.namelist())
            settings = json.loads(z.read("system/config/settings.json"))
        self.assertIn(update.BOOTSTRAP, names)
        for need in ("VERSION", ".claude/settings.json", "system/templates/settings-defaults.json",
                     "system/templates/project-register-template.md", "system/templates/portfolio-template.md",
                     "system/templates/vault-gitignore", "system/templates/vault-CLAUDE-template.md"):
            self.assertIn(need, names)
        self.assertFalse([n for n in names if n.startswith(("dev/", "projects/", "inbox/", "system/branding/"))
                          or n in (".creaite-dev", "system/tracker.db", "CLAUDE.md")])
        self.assertEqual(settings["dashboard"]["palette"], "creaite")       # the defaults, not this repo's

    def test_run_the_zip(self):
        target, r = self.make("vault-a")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(f"Created a creaite {VERSION} vault", r.stdout)
        self.assertIn('say "setup"', r.stdout)
        self.assertIn("WARN  First setup", r.stdout)
        # nothing from development, no sample data
        for absent in ("dev", ".creaite-dev", "system/branding", "projects/ABC Example Programme", "__main__.py"):
            self.assertFalse((target / absent).exists(), absent)
        self.assertEqual(sorted(p.name for p in (target / "projects").iterdir()), ["_portfolio"])
        # starting files, empty registers
        reg = (target / "projects/_portfolio/project-register.md").read_text(encoding="utf-8")
        self.assertNotIn("Example Programme", reg)
        self.assertNotIn("| Example", (target / "projects/_portfolio/PORTFOLIO.md").read_text(encoding="utf-8"))
        self.assertIn("@system/creaite-rules.md", (target / "CLAUDE.md").read_text(encoding="utf-8"))
        self.assertIn("system/tracker.db", (target / ".gitignore").read_text(encoding="utf-8"))
        self.assertTrue((target / "system/processed.txt").read_text().startswith("# date processed"))
        # an empty database with every table
        con = sqlite3.connect(target / "system/tracker.db")
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({"projects", "actions", "raid", "decisions", "milestones", "workstreams", "vault_search"} <= tables)
        self.assertEqual(sum(con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                             for t in ("projects", "actions", "raid", "decisions", "workstreams")), 0)
        con.close()
        # clean settings, the release kept, doctor passes
        s = json.loads((target / "system/config/settings.json").read_text(encoding="utf-8"))
        self.assertEqual((s["dashboard"]["palette"], s["identity"]["name"]), ("creaite", ""))
        installed = json.loads((target / "system/releases/installed.json").read_text(encoding="utf-8"))
        self.assertEqual(installed["version"], VERSION)
        self.assertTrue((target / "system/releases" / self.zip.name).exists())
        self.assertTrue((target / "dashboard.html").exists())
        d = subprocess.run([sys.executable, str(target / "system/scripts/doctor.py")], cwd=target,
                           capture_output=True, text=True)
        self.assertEqual(d.returncode, 0, d.stdout)
        self.assertNotIn("FAIL", d.stdout)

    def test_new_vault_command_and_reinstall_keeps_data(self):
        target, r = self.make("vault-b", via_zip=False)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        note = target / "projects/_portfolio/minutes/2026-10-01 Mine.md"
        note.write_text("my notes", encoding="utf-8")
        (target / "CLAUDE.md").write_text("@system/creaite-rules.md\n\n- Role: Programme manager\n", encoding="utf-8")
        cfg = json.loads((target / "system/config/settings.json").read_text(encoding="utf-8"))
        cfg["identity"]["name"] = "Alan Carter"
        (target / "system/config/settings.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        r = subprocess.run([sys.executable, str(target / "system/scripts/update.py"), "install", str(self.zip),
                            "--reinstall"], cwd=target, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(note.read_text(encoding="utf-8"), "my notes")
        self.assertIn("Programme manager", (target / "CLAUDE.md").read_text(encoding="utf-8"))
        self.assertEqual(json.loads((target / "system/config/settings.json").read_text())["identity"]["name"],
                         "Alan Carter")

    def test_refusals(self):
        full = self.tmp / "full"
        full.mkdir()
        (full / "something.txt").write_text("x")
        _, r = self.make("full")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("isn't empty", r.stderr)
        self.assertEqual(sorted(p.name for p in full.iterdir()), ["something.txt"])     # untouched
        for synced in ("Library/CloudStorage/OneDrive-Company/creaite", "OneDrive - Company/creaite",
                       "Library/Mobile Documents/com~apple~CloudDocs/creaite"):
            with self.assertRaisesRegex(update.UpdateError, "synced folder"):
                update.vault_folder(self.tmp / synced)
        # a changed zip, and GitHub's "Source code (zip)"
        bad = self.tmp / "bad.zip"
        remake(self.zip, bad, corrupt="system/scripts/tracker.py")
        r = subprocess.run([sys.executable, str(REPO / "system/scripts/update.py"), "new-vault", str(bad),
                            str(self.tmp / "from-bad")], capture_output=True, text=True)
        self.assertIn("checksum", r.stderr)
        self.assertFalse((self.tmp / "from-bad").exists())
        source = self.tmp / "creaite-main.zip"
        with zipfile.ZipFile(source, "w") as z:
            z.writestr("creaite-main/README.md", "repo")
        r = subprocess.run([sys.executable, str(REPO / "system/scripts/update.py"), "new-vault", str(source),
                            str(self.tmp / "from-source")], capture_output=True, text=True)
        self.assertIn("Source code (zip)", r.stderr)

    def test_no_folder_and_no_terminal_asks_for_one(self):
        r = subprocess.run([sys.executable, str(self.zip)], capture_output=True, text=True, stdin=subprocess.DEVNULL)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("which folder", r.stderr)


class TestNewVaultProjectsFolder(unittest.TestCase):
    """BL-85 item 4: a vault is never in a synced folder, but its projects folder may be the company OneDrive."""

    @classmethod
    def setUpClass(cls):
        cls.zip = build_release()
        cls.home = Path(tempfile.mkdtemp(prefix="creaite-home-")).resolve()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.home, ignore_errors=True)
        shutil.rmtree(cls.zip.parent, ignore_errors=True)

    def make(self, vault, *extra):
        env = {**__import__("os").environ, "HOME": str(self.home)}
        return subprocess.run([sys.executable, str(self.zip), str(vault), *extra], capture_output=True, text=True,
                              stdin=subprocess.DEVNULL, env=env)

    def one_drive(self, name="OneDrive-TestCo"):
        d = self.home / "Library" / "CloudStorage" / name / "Documents" / "Engagements"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def test_a_company_onedrive_projects_folder_is_accepted_and_gets_its_portfolio_folder(self):
        root = self.one_drive()
        (root / "Example Programme").mkdir()
        vault = self.home / "creaite-a"
        r = self.make(vault, "--projects", str(root))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        s = json.loads((vault / "system/config/settings.json").read_text(encoding="utf-8"))
        self.assertEqual(s["locations"]["projects_root"], "~/Library/CloudStorage/OneDrive-TestCo/Documents/Engagements")   # home-relative
        for name in ("PORTFOLIO.md", "project-register.md", "people-register.md"):
            self.assertTrue((root / "_Portfolio" / name).is_file(), name)
        self.assertTrue((root / "_Portfolio" / "02 Meetings" / "Minutes").is_dir())
        self.assertTrue((root / "_Portfolio" / "02 Meetings" / "Transcripts").is_dir())
        self.assertFalse((vault / "projects").exists() and any((vault / "projects").iterdir()))     # nothing of the projects in the vault
        self.assertEqual(sorted(p.name for p in root.iterdir()), ["Example Programme", "_Portfolio"])  # and the engagement is untouched
        self.assertNotIn("FAIL", subprocess.run([sys.executable, str(vault / "system/scripts/doctor.py")], cwd=vault,
                                                capture_output=True, text=True, env={**__import__("os").environ, "HOME": str(self.home)}).stdout)

    def test_an_existing_portfolio_folder_keeps_its_own_files(self):
        root = self.one_drive("OneDrive-OtherCo")
        (root / "_Portfolio").mkdir()
        (root / "_Portfolio" / "PORTFOLIO.md").write_text("my own portfolio notes")
        vault = self.home / "creaite-b"
        self.assertEqual(self.make(vault, "--projects", str(root)).returncode, 0)
        self.assertEqual((root / "_Portfolio" / "PORTFOLIO.md").read_text(), "my own portfolio notes")
        self.assertTrue((root / "_Portfolio" / "project-register.md").is_file())                       # only what was missing

    def test_personal_cloud_storage_and_unreachable_folders_are_refused_and_nothing_is_left_behind(self):
        personal = self.one_drive("OneDrive-Personal")
        icloud = self.home / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "Engagements"
        icloud.mkdir(parents=True)
        for name, folder, why in (("p", personal, "personal OneDrive"), ("i", icloud, "personal or other sync service"),
                                  ("u", self.home / "Library/CloudStorage/OneDrive-Gone/Documents/Engagements", "isn't reachable")):
            vault = self.home / f"creaite-refused-{name}"
            r = self.make(vault, "--projects", str(folder))
            self.assertEqual(r.returncode, 1, (name, r.stdout))
            self.assertIn(why, r.stderr)
            self.assertFalse(vault.exists(), name)
            self.assertEqual(list(folder.iterdir()) if folder.exists() else [], [], name)

    def test_the_vault_itself_is_still_refused_in_a_synced_folder(self):
        root = self.one_drive("OneDrive-TestCo2")
        r = self.make(root.parent / "creaite-vault")
        self.assertEqual(r.returncode, 1)
        self.assertIn("synced folder", r.stderr)

    def test_a_plain_local_projects_folder_is_accepted(self):
        local = self.home / "work" / "engagements"
        local.mkdir(parents=True)
        vault = self.home / "creaite-c"
        self.assertEqual(self.make(vault, "--projects", str(local)).returncode, 0)
        self.assertTrue((local / "_Portfolio" / "project-register.md").is_file())

    def test_without_a_projects_folder_nothing_changes(self):
        vault = self.home / "creaite-d"
        self.assertEqual(self.make(vault).returncode, 0)
        s = json.loads((vault / "system/config/settings.json").read_text(encoding="utf-8"))
        self.assertEqual(s["locations"]["projects_root"], "")
        self.assertTrue((vault / "projects/_portfolio/project-register.md").is_file())


if __name__ == "__main__":
    unittest.main()
