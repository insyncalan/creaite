"""Tests for releases and updates (BL-36): dev/tools/build_release.py and system/scripts/update.py.

Run: python3 dev/tests/test_update.py
Builds a release zip from this repository's working files (--dirty), then installs it into throwaway vaults.
"""
import atexit
import base64
import json
import os
import re
import shutil
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_live_server import free_port  # noqa: E402
from test_tracker import REPO, Vault  # noqa: E402

sys.path.insert(0, str(REPO / "system" / "scripts"))
import paths  # noqa: E402
import update  # noqa: E402

VERSION = (REPO / "VERSION").read_text(encoding="utf-8").strip()
OWN_SKILL = ".claude/skills/my-own/SKILL.md"
OWN_CLAUDE = "@system/creaite-rules.md\n\n# Alan's own notes\n"


RELEASE_DIRS = []       # BL-172 (sprint-polish-2): this process's own release folders, removed when it ends
atexit.register(lambda: [shutil.rmtree(d, ignore_errors=True) for d in RELEASE_DIRS])


def build_release():
    out = Path(tempfile.mkdtemp(prefix="creaite-release-"))
    RELEASE_DIRS.append(out)
    r = subprocess.run([sys.executable, str(REPO / "dev" / "tools" / "build_release.py"), "--dirty", "--out", str(out),
                        "--tag", f"v{VERSION}"], capture_output=True, text=True)
    if r.returncode:
        raise AssertionError(r.stdout + r.stderr)
    return out / f"creaite-{VERSION}.zip"


def remake(src, dest, version=None, drop=(), add=None, corrupt=None, unlisted=None):
    """A copy of a release zip with changes, its manifest kept consistent unless corrupt or unlisted is given."""
    with zipfile.ZipFile(src) as z:
        content = {n: z.read(n) for n in z.namelist()}
    manifest = json.loads(content.pop(paths.RELEASE_MANIFEST))
    for n in drop:
        content.pop(n)
    content.update(add or {})
    if version:
        manifest["version"] = version
        content["VERSION"] = f"{version}\n".encode()
    manifest["files"] = {n: update.sha256(d) for n, d in content.items()}
    if corrupt:
        content[corrupt] = content[corrupt] + b"\n# changed"
    content.update(unlisted or {})
    with zipfile.ZipFile(dest, "w") as z:
        z.writestr(paths.RELEASE_MANIFEST, json.dumps(manifest))
        for n, d in content.items():
            z.writestr(n, d)
    return dest


class UpdateVault(Vault):
    """A throwaway vault at version 0.9.0 with a database, Alan's own CLAUDE.md, a changed setting and his own skill."""

    def __init__(self):
        super().__init__()
        (self.root / "VERSION").write_text("0.9.0\n", encoding="utf-8")
        self.run("init")
        (self.root / "CLAUDE.md").write_text(OWN_CLAUDE, encoding="utf-8")
        s = self.root / "system" / "config" / "settings.json"
        data = json.loads(s.read_text(encoding="utf-8"))
        data["sweep"]["due_from"] = "06:30"                  # Alan's value: kept
        self.dropped = next(k for k in data["dashboard"] if not k.startswith("_"))
        data["dashboard"].pop(self.dropped)                   # a "new" setting the release adds
        s.write_text(json.dumps(data, indent=2), encoding="utf-8")
        own = self.root / OWN_SKILL
        own.parent.mkdir(parents=True)
        own.write_text("Alan's own skill\n", encoding="utf-8")
        self.tmp = Path(tempfile.mkdtemp(prefix="creaite-zips-"))

    def cleanup(self):
        super().cleanup()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def update(self, *args, ok=True):
        return self.run(*args, script="update.py", ok=ok)

    def rows(self, sql):
        with closing(sqlite3.connect(self.root / "system" / "tracker.db")) as con:
            return con.execute(sql).fetchall()


class TestLists(unittest.TestCase):
    def test_engine_and_data_dont_overlap(self):
        for e in paths.ENGINE:
            self.assertFalse(update.under(e, paths.DATA), e)
            self.assertFalse(any(update.under(d, (e,)) for d in paths.DATA), e)
        for m in paths.ENGINE_MERGED:
            self.assertTrue(update.under(m, paths.DATA) or m.startswith(".claude/"), m)
        for never in ("CLAUDE.md", "system/tracker.db", "projects/ABC Example Programme/CLAUDE.md", "dev/BUILD.md",
                      "system/releases/creaite-1.0.0.zip", ".creaite-dev", "system/config/schedules.md"):
            self.assertFalse(update.is_engine(never), never)


class TestBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.zip = build_release()

    def test_zip_holds_the_engine_only(self):
        with zipfile.ZipFile(self.zip) as z:
            names = set(z.namelist())
            manifest = json.loads(z.read(paths.RELEASE_MANIFEST))
        self.assertEqual(manifest["version"], VERSION)
        for must in ("VERSION", "system/scripts/update.py", "system/scripts/tracker.py", "system/templates/dashboard.html",
                     "system/creaite-rules.md", "system/templates/vault-CLAUDE-template.md", ".claude/settings.json",
                     "system/config/settings.json",
                     # BL-275: the bundled pypdf, its dependency, their licences and the vendor manifest ship too
                     "system/scripts/vendor/pypdf/__init__.py", "system/scripts/vendor/typing_extensions.py",
                     "system/scripts/vendor/licenses/pypdf-6.19.0-LICENSE.txt",
                     "system/scripts/vendor/licenses/typing_extensions-4.15.0-LICENSE.txt",
                     "system/scripts/vendor/manifest.json"):
            self.assertIn(must, names)
        for name in names - {paths.RELEASE_MANIFEST, update.BOOTSTRAP}:      # the launcher: checked, never installed
            self.assertTrue(update.is_engine(name), name)
            self.assertNotIn("__pycache__", name)
            self.assertFalse(name.startswith("system/templates/dashboard/"), f"{name}: the dashboard's source is dev only")
        self.assertEqual(set(manifest["files"]), names - {paths.RELEASE_MANIFEST})

    def own_tmp(self):
        d = tempfile.mkdtemp(prefix="creaite-release-")
        self.addCleanup(shutil.rmtree, d, True)       # BL-172
        return d

    def test_tag_must_match_version(self):
        r = subprocess.run([sys.executable, str(REPO / "dev" / "tools" / "build_release.py"), "--dirty", "--tag",
                            "v0.0.1", "--out", self.own_tmp()], capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn("doesn't match VERSION", r.stderr)


class TestInstall(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.zip = build_release()

    def setUp(self):
        self.v = UpdateVault()
        self.addCleanup(self.v.cleanup)

    def test_install_replaces_engine_and_keeps_data(self):
        self.v.update("install", str(self.zip))
        root = self.v.root
        self.assertEqual((root / "VERSION").read_text().strip(), VERSION)
        self.assertEqual((root / "CLAUDE.md").read_text(), OWN_CLAUDE)
        settings = json.loads((root / "system" / "config" / "settings.json").read_text())
        self.assertEqual(settings["sweep"]["due_from"], "06:30")
        self.assertIn(self.v.dropped, settings["dashboard"])
        self.assertTrue((root / OWN_SKILL).exists())
        self.assertTrue((root / "system" / "releases" / self.zip.name).exists())
        self.assertEqual(json.loads((root / "system" / "releases" / "installed.json").read_text())["version"], VERSION)
        self.assertTrue(self.v.rows("SELECT code FROM projects"))
        log = (root / "system" / "config" / "settings-log.jsonl").read_text().splitlines()
        self.assertTrue(any(f"dashboard.{self.v.dropped}" in line for line in log))      # (other new settings, such as locations, are logged too)
        self.assertEqual(len(list((root / "system" / "backups").glob("update-*"))), 1)

    def test_retired_deny_rules_go_from_an_existing_vault_and_alans_own_rules_stay(self):
        """v1.2.0 retires Write(.claude/settings*.json) (Edit(...) already covers file edits): an update removes exactly those two
        from a vault that has them, keeps every other rule, including Alan's own, and shows the removal first."""
        cs = self.v.root / ".claude" / "settings.json"
        data = json.loads(cs.read_text())
        deny = data["permissions"]["deny"]
        for r in ("Write(.claude/settings.json)", "Write(.claude/settings.local.json)"):
            if r not in deny:
                deny.append(r)                                               # the vault as v1.1.0 left it
        deny.append("Bash(rm -rf *)")                                        # Alan's own, added by hand
        data["permissions"]["allow"].append("Read(~/Documents/notes/**)")    # and an allow rule of his
        cs.write_text(json.dumps(data, indent=2))
        shown = self.v.update("inspect", str(self.zip)).stdout
        self.assertIn("retired deny: Write(.claude/settings.json)", shown)
        self.v.update("install", str(self.zip))
        after = json.loads(cs.read_text())["permissions"]
        self.assertNotIn("Write(.claude/settings.json)", after["deny"])
        self.assertNotIn("Write(.claude/settings.local.json)", after["deny"])
        self.assertIn("Edit(.claude/settings.json)", after["deny"])         # the Edit rules stay
        self.assertIn("Edit(.claude/settings.local.json)", after["deny"])
        self.assertIn("Bash(rm -rf *)", after["deny"])                       # Alan's own rules are never removed
        self.assertIn("Read(~/Documents/notes/**)", after["allow"])
        self.assertNotIn("Write(.claude/settings.json)", json.loads((REPO / ".claude" / "settings.json").read_text())["permissions"]["deny"])

    def test_retiring_applies_only_to_rules_creaite_shipped(self):
        incoming = {"permissions": {"allow": [], "deny": ["Edit(.claude/settings.json)"]}}
        current = {"permissions": {"allow": [], "deny": ["Write(.claude/settings.json)", "Bash(my own rule)"]}}
        added = update.merge_permissions(current, incoming)
        self.assertEqual(current["permissions"]["deny"], ["Bash(my own rule)", "Edit(.claude/settings.json)"])
        self.assertEqual(added, ["retired deny: Write(.claude/settings.json)", "deny: Edit(.claude/settings.json)"])
        # a release that ships the rule again keeps it
        current = {"permissions": {"allow": [], "deny": ["Write(.claude/settings.json)"]}}
        incoming = {"permissions": {"allow": [], "deny": ["Write(.claude/settings.json)"]}}
        self.assertEqual(update.merge_permissions(current, incoming), [])
        self.assertEqual(current["permissions"]["deny"], ["Write(.claude/settings.json)"])

    def test_the_interim_rm_rules_go_but_only_those_exact_ones(self):
        """v1.3.0 (BL-118): the staging commands delete their own inputs, so the two exact-name rm rules added meanwhile are retired.
        A wider rm rule of Alan's own, or one for another file, stays."""
        incoming = {"permissions": {"allow": ["Bash(python3 system/scripts/sweep.py *)"], "deny": []}}
        current = {"permissions": {"allow": ["Bash(rm system/staging/drafts/sweep.json)", "Bash(rm system/staging/drafts/calendar.json)",
                                             "Bash(rm system/staging/drafts/mine.json)", "Bash(rm -f *)"], "deny": []}}
        added = update.merge_permissions(current, incoming)
        self.assertEqual(current["permissions"]["allow"],
                         ["Bash(rm system/staging/drafts/mine.json)", "Bash(rm -f *)", "Bash(python3 system/scripts/sweep.py *)"])
        self.assertIn("retired allow: Bash(rm system/staging/drafts/sweep.json)", added)
        self.assertIn("retired allow: Bash(rm system/staging/drafts/calendar.json)", added)
        self.assertEqual(update.merge_permissions(current, incoming), [])                                  # the second time round: nothing

    def test_inspect_changes_nothing(self):
        r = self.v.update("inspect", str(self.zip))
        p = json.loads(r.stdout)
        self.assertEqual((p["from"], p["to"]), ("0.9.0", VERSION))
        self.assertIn(f"dashboard.{self.v.dropped}", p["settings"]["system/config/settings.json"])
        self.assertIn(OWN_SKILL, p["left"])
        self.assertEqual((self.v.root / "VERSION").read_text().strip(), "0.9.0")

    def test_same_or_older_version_needs_reinstall(self):
        self.v.update("install", str(self.zip))
        r = self.v.update("install", str(self.zip), ok=False)
        self.assertIn("the version installed", r.stderr)
        self.v.update("install", str(self.zip), "--reinstall")

    def test_refuses_bad_zips(self):
        t = self.v.tmp
        cases = {
            "no manifest": (t / "source.zip", "Source code (zip)"),
            "outside the engine": (remake(self.zip, t / "a.zip", add={"projects/x.md": b"x"}), "outside the engine"),
            "unlisted": (remake(self.zip, t / "b.zip", unlisted={"system/scripts/extra.py": b"x"}), "not listed"),
            "checksum": (remake(self.zip, t / "c.zip", corrupt="system/scripts/tracker.py"), "checksum"),
            "CLAUDE.md": (remake(self.zip, t / "d.zip", add={"CLAUDE.md": b"x"}), "outside the engine"),
        }
        with zipfile.ZipFile(t / "source.zip", "w") as z:
            z.writestr("creaite-main/VERSION", "9.9.9")
        for label, (path, message) in cases.items():
            r = self.v.update("install", str(path), ok=False)
            self.assertEqual(r.returncode, 1, label)
            self.assertIn(message, r.stderr, label)
        self.assertEqual((self.v.root / "VERSION").read_text().strip(), "0.9.0")
        self.assertEqual((self.v.root / "CLAUDE.md").read_text(), OWN_CLAUDE)

    def test_refuses_the_development_repo(self):
        (self.v.root / ".creaite-dev").write_text("")
        r = self.v.update("install", str(self.zip), ok=False)
        self.assertIn("development repository", r.stderr)

    def test_failed_step_rolls_back(self):
        broken = remake(self.zip, self.v.tmp / "broken.zip", version="9.0.0",
                        add={"system/scripts/build_dashboard.py": b"raise SystemExit('broken build')\n"})
        before = (self.v.root / "system" / "scripts" / "build_dashboard.py").read_bytes()
        r = self.v.update("install", str(broken), ok=False)
        self.assertIn("has been restored", r.stderr)
        self.assertEqual((self.v.root / "VERSION").read_text().strip(), "0.9.0")
        self.assertEqual((self.v.root / "system" / "scripts" / "build_dashboard.py").read_bytes(), before)
        self.assertFalse((self.v.root / "system" / "releases" / "installed.json").exists())

    def test_removes_only_files_a_release_shipped(self):
        self.v.update("install", str(self.zip))
        gone = "system/templates/vendor/roboto-OFL.txt"
        nxt = remake(self.zip, self.v.tmp / "creaite-9.1.0.zip", version="9.1.0", drop=[gone])
        p = json.loads(self.v.update("inspect", str(nxt)).stdout)
        self.assertEqual(p["removed"], [gone])
        self.v.update("install", str(nxt))
        self.assertFalse((self.v.root / gone).exists())
        self.assertTrue((self.v.root / OWN_SKILL).exists())

    def test_older_vault_is_told_to_split_claude_md(self):
        (self.v.root / "system" / "creaite-rules.md").unlink()             # before the split: rules inline
        old = "# creaite\n\n## Non-negotiables\n\n- Local only.\n\n## About Alan\n\n- Programme manager.\n"
        (self.v.root / "CLAUDE.md").write_text(old, encoding="utf-8")
        r = self.v.update("install", str(self.zip))
        self.assertIn('say "setup"', r.stdout)
        self.assertTrue((self.v.root / "system" / "creaite-rules.md").exists())
        self.assertEqual((self.v.root / "CLAUDE.md").read_text(), old)

    def test_undo(self):
        self.v.update("install", str(self.zip))
        self.v.update("undo")
        self.assertEqual((self.v.root / "VERSION").read_text().strip(), "0.9.0")
        self.assertFalse((self.v.root / "system" / "releases" / "installed.json").exists())
        settings = json.loads((self.v.root / "system" / "config" / "settings.json").read_text())
        self.assertNotIn(self.v.dropped, settings["dashboard"])
        self.assertIn("no update to undo", self.v.update("undo", ok=False).stderr)

    def test_undo_keeps_a_changed_database_only_when_asked(self):
        self.v.update("install", str(self.zip))
        with closing(sqlite3.connect(self.v.root / "system" / "tracker.db")) as con, con:
            con.execute("UPDATE projects SET health_reason = 'changed after the update'")
        self.assertIn("--keep-database", self.v.update("undo", ok=False).stderr)
        self.v.update("undo", "--keep-database")
        self.assertEqual((self.v.root / "VERSION").read_text().strip(), "0.9.0")
        self.assertEqual(self.v.rows("SELECT DISTINCT health_reason FROM projects"), [("changed after the update",)])


class TestNewDefaultsKeepSavedValues(unittest.TestCase):
    """BL-320 (Alan, 14-10-2026): Close the day from 17:30 is the new default; Week ahead stays Urgent only. The release's
    settings.json is settings-defaults.json (build_release); an update only adds missing keys, so a saved value is kept."""
    DEFAULTS = (REPO / "system" / "templates" / "settings-defaults.json").read_text(encoding="utf-8")

    def merge(self, current):
        text, added = update.merged_changes("system/config/settings.json", json.dumps(current), self.DEFAULTS)
        return json.loads(text), added

    def test_the_defaults_are_the_accepted_mockups(self):
        d = json.loads(self.DEFAULTS)
        self.assertEqual(d["day"]["close_from"], "17:30")
        self.assertEqual(d["dashboard"]["week_ahead_priorities"], ["Urgent"])                  # Alan, 14-10-2026

    def test_an_existing_saved_value_is_never_overwritten(self):
        mine = {"day": {"close_from": None}, "dashboard": {"week_ahead_priorities": ["Urgent", "High"]}}
        after, added = self.merge(mine)
        self.assertIsNone(after["day"]["close_from"])                          # Alan's "off" stays off
        self.assertEqual(after["dashboard"]["week_ahead_priorities"], ["Urgent", "High"])        # his own list stays
        self.assertNotIn("day.close_from", added)
        self.assertNotIn("dashboard.week_ahead_priorities", added)
        after, _ = self.merge({"day": {"close_from": "18:15"}, "dashboard": {"week_ahead_priorities": []}})
        self.assertEqual((after["day"]["close_from"], after["dashboard"]["week_ahead_priorities"]), ("18:15", []))

    def test_a_vault_without_the_keys_gets_the_new_defaults(self):
        after, added = self.merge({"day": {"catchup_sweep": "offer"}, "dashboard": {}})
        self.assertEqual(after["day"]["close_from"], "17:30")
        self.assertEqual(after["day"]["catchup_sweep"], "offer")
        self.assertEqual(after["dashboard"]["week_ahead_priorities"], ["Urgent"])
        self.assertIn("day.close_from", added)
        self.assertIn("dashboard.week_ahead_priorities", added)


class TestLabelSettingRetired(unittest.TestCase):
    """BL-121: approving a draft needs no Word label, so an update removes documents.require_sensitivity_label (logged), and
    creaite's own note with it; anything else of Alan's in that section stays."""
    NOTE = "Approving a draft needs Word's sensitivity label (open, save, close in Word first)"

    @classmethod
    def setUpClass(cls):
        cls.zip = build_release()

    def setUp(self):
        self.v = UpdateVault()
        self.addCleanup(self.v.cleanup)
        self.cfg = self.v.root / "system" / "config" / "settings.json"

    def documents(self, section):
        data = json.loads(self.cfg.read_text(encoding="utf-8"))
        data["documents"] = section
        self.cfg.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def saved(self):
        return json.loads(self.cfg.read_text(encoding="utf-8"))

    def test_the_setting_goes_is_shown_first_logged_and_undone(self):
        self.documents({"require_sensitivity_label": True, "note": self.NOTE})
        p = json.loads(self.v.update("inspect", str(self.zip)).stdout)
        self.assertIn("without any Word sensitivity label", p["notes"])
        self.assertIn("retired setting: documents.require_sensitivity_label", p["settings"]["system/config/settings.json"])
        self.assertIn("documents", self.saved())                                       # inspect changed nothing
        self.v.update("install", str(self.zip))
        self.assertNotIn("documents", self.saved())
        log = [json.loads(ln) for ln in (self.v.root / "system/config/settings-log.jsonl").read_text().splitlines()]
        gone = next(r for r in log if r["key"] == "documents.require_sensitivity_label")
        self.assertEqual((gone["old"], gone["new"]), (True, None))
        self.assertTrue(gone["by"].startswith("update "))
        self.v.update("undo")
        self.assertEqual(self.saved()["documents"]["require_sensitivity_label"], True)

    def test_alans_own_keys_and_his_own_note_stay(self):
        self.documents({"require_sensitivity_label": False, "note": "mine", "other": 1})
        self.v.update("install", str(self.zip))
        self.assertEqual(self.saved()["documents"], {"note": "mine", "other": 1})

    def test_a_vault_without_the_section_and_a_second_run_change_nothing(self):
        data = self.saved()
        data.pop("documents", None)
        self.cfg.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self.v.update("install", str(self.zip))
        self.assertNotIn("documents", self.saved())
        before = self.cfg.read_text(encoding="utf-8")
        self.v.update("install", str(self.zip), "--reinstall")
        self.assertEqual(self.cfg.read_text(encoding="utf-8"), before)


class TestTidyAfterAnOlderInstaller(unittest.TestCase):
    """An update is run by the update.py already installed, so the new engine's migrations run through tracker.py migrate
    (update.py tidy), which every installer calls: retired rules and settings go, logged, once; never in the development repo."""
    NOTE = TestLabelSettingRetired.NOTE
    RM = ["Bash(rm system/staging/drafts/sweep.json)", "Bash(rm system/staging/drafts/calendar.json)"]

    def setUp(self):
        self.v = UpdateVault()
        self.addCleanup(self.v.cleanup)
        self.cfg = self.v.root / "system" / "config" / "settings.json"
        self.perms = self.v.root / ".claude" / "settings.json"
        data = json.loads(self.cfg.read_text(encoding="utf-8"))
        data["documents"] = {"require_sensitivity_label": True, "note": self.NOTE}
        data.setdefault("locations", {})["offsite_backup"] = "_Portfolio/creaite backups"
        self.cfg.write_text(json.dumps(data, indent=2), encoding="utf-8")
        perms = json.loads(self.perms.read_text(encoding="utf-8"))
        perms["permissions"]["allow"] += self.RM + ["Bash(python3 my-own.py)"]
        self.perms.write_text(json.dumps(perms, indent=2), encoding="utf-8")

    def test_migrate_retires_them_logged_once(self):
        out = self.v.run("migrate").stdout
        self.assertIn("Tidied after the update", out)
        data = json.loads(self.cfg.read_text(encoding="utf-8"))
        self.assertNotIn("documents", data)
        self.assertEqual(data["locations"]["offsite_backup"], update.NEW_BACKUP_DIR)
        allow = json.loads(self.perms.read_text(encoding="utf-8"))["permissions"]["allow"]
        self.assertFalse(set(self.RM) & set(allow))
        self.assertIn("Bash(python3 my-own.py)", allow)                                    # Alan's own rule stays
        log = [json.loads(ln) for ln in (self.v.root / "system/config/settings-log.jsonl").read_text().splitlines()]
        self.assertIn("documents.require_sensitivity_label", [r["key"] for r in log])
        before = (self.cfg.read_text(encoding="utf-8"), self.perms.read_text(encoding="utf-8"))
        self.assertNotIn("Tidied", self.v.run("migrate").stdout)                             # nothing the second time
        self.assertEqual((self.cfg.read_text(encoding="utf-8"), self.perms.read_text(encoding="utf-8")), before)
        self.assertIn("Nothing to tidy", self.v.update("tidy").stdout)

    def test_a_retired_theme_becomes_creaite_logged_once_and_other_values_stay(self):
        """BL-142: creaite standard, Minimals and creaite teal are gone; a saved one becomes creaite. Alan's other choice stays."""
        for old in ("creaite standard", "Minimals", "creaite teal"):
            data = json.loads(self.cfg.read_text(encoding="utf-8"))
            data["dashboard"]["palette"] = old
            self.cfg.write_text(json.dumps(data, indent=2), encoding="utf-8")
            self.v.run("migrate")
            self.assertEqual(json.loads(self.cfg.read_text(encoding="utf-8"))["dashboard"]["palette"], "creaite", old)
            log = [json.loads(ln) for ln in (self.v.root / "system/config/settings-log.jsonl").read_text().splitlines()]
            moved = [r for r in log if r["key"] == "dashboard.palette"][-1]
            self.assertEqual((moved["old"], moved["new"]), (old, "creaite"))
            self.assertTrue(moved["by"].startswith("update "))
        before = self.cfg.read_text(encoding="utf-8")
        self.assertNotIn("dashboard.palette", self.v.run("migrate").stdout)                     # nothing the second time
        self.assertEqual(self.cfg.read_text(encoding="utf-8"), before)
        for keep in ("Notion", "Brightwater", "Linear", "Cursor", "Claude", "Apple", "Retro Arcade", "Thermo Scan", "creaite", "my own"):
            data = json.loads(self.cfg.read_text(encoding="utf-8"))
            data["dashboard"]["palette"] = keep
            self.cfg.write_text(json.dumps(data, indent=2), encoding="utf-8")
            self.v.run("migrate")
            self.assertEqual(json.loads(self.cfg.read_text(encoding="utf-8"))["dashboard"]["palette"], keep)

    def test_an_update_shows_and_makes_the_same_change(self):
        zip_ = build_release()
        data = json.loads(self.cfg.read_text(encoding="utf-8"))
        data["dashboard"]["palette"] = "Minimals"
        self.cfg.write_text(json.dumps(data, indent=2), encoding="utf-8")
        p = json.loads(self.v.update("inspect", str(zip_)).stdout)
        self.assertIn("Minimals is retired", p["notes"])
        self.assertEqual(json.loads(self.cfg.read_text(encoding="utf-8"))["dashboard"]["palette"], "Minimals")   # inspect changes nothing
        self.v.update("install", str(zip_))
        self.assertEqual(json.loads(self.cfg.read_text(encoding="utf-8"))["dashboard"]["palette"], "creaite")

    def test_never_in_the_development_repository(self):
        (self.v.root / ".creaite-dev").write_text("", encoding="utf-8")
        before = (self.cfg.read_text(encoding="utf-8"), self.perms.read_text(encoding="utf-8"))
        self.v.run("migrate")
        self.assertEqual((self.cfg.read_text(encoding="utf-8"), self.perms.read_text(encoding="utf-8")), before)


class TestBackupFolderMigration(unittest.TestCase):
    """BL-112: a vault on the old backup folder moves to _Portfolio/99 System/creaite backups at the update; Alan's own value stays."""
    OLD, NEW = "_Portfolio/creaite backups", "_Portfolio/99 System/creaite backups"

    @classmethod
    def setUpClass(cls):
        cls.zip = build_release()

    def setUp(self):
        self.v = UpdateVault()
        self.addCleanup(self.v.cleanup)
        self.cfg = self.v.root / "system" / "config" / "settings.json"

    def locations(self, offsite=None, never=None):
        data = json.loads(self.cfg.read_text(encoding="utf-8"))
        data["locations"] = {"projects_root": "", "never_index": never if never is not None else ["_Archive", "_Templates"],
                             "offsite_backup": offsite or self.OLD}
        self.cfg.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def saved(self):
        return json.loads(self.cfg.read_text(encoding="utf-8"))["locations"]

    def test_the_old_default_moves_and_is_shown_first_logged_and_undone(self):
        self.locations(self.OLD + "/")                                                 # a trailing slash is still the old default
        p = json.loads(self.v.update("inspect", str(self.zip)).stdout)
        self.assertIn(self.NEW, p["notes"])
        self.assertIn("The old folder and its copies stay where they are", p["notes"])
        self.assertIn("99 System is added", p["notes"])
        self.assertEqual(self.saved()["offsite_backup"], self.OLD + "/")               # inspect changed nothing
        self.v.update("install", str(self.zip))
        loc = self.saved()
        self.assertEqual((loc["offsite_backup"], loc["never_index"]), (self.NEW, ["_Archive", "_Templates", "99 System"]))
        log = [json.loads(ln) for ln in (self.v.root / "system/config/settings-log.jsonl").read_text().splitlines()]
        moved = next(r for r in log if r["key"] == "locations.offsite_backup")
        self.assertEqual((moved["old"], moved["new"]), (self.OLD + "/", self.NEW))
        self.assertTrue(moved["by"].startswith("update "))
        self.assertEqual(next(r for r in log if r["key"] == "locations.never_index")["old"], ["_Archive", "_Templates"])
        self.v.update("undo")
        self.assertEqual(self.saved()["offsite_backup"], self.OLD + "/")
        self.assertEqual(self.saved()["never_index"], ["_Archive", "_Templates"])

    def test_a_custom_value_stays_and_99_system_is_still_added(self):
        self.locations("_Portfolio/My own backups")
        self.v.update("install", str(self.zip))
        loc = self.saved()
        self.assertEqual(loc["offsite_backup"], "_Portfolio/My own backups")
        self.assertIn("99 System", loc["never_index"])
        log = (self.v.root / "system/config/settings-log.jsonl").read_text()
        self.assertNotIn("locations.offsite_backup", log)

    def test_running_it_twice_changes_nothing(self):
        self.locations()
        self.v.update("install", str(self.zip))
        before = self.cfg.read_text(encoding="utf-8")
        self.v.update("install", str(self.zip), "--reinstall")
        self.assertEqual(self.cfg.read_text(encoding="utf-8"), before)
        self.assertEqual(self.saved()["never_index"].count("99 System"), 1)

    def test_a_vault_with_no_locations_block_ends_on_the_new_defaults(self):
        data = json.loads(self.cfg.read_text(encoding="utf-8"))
        data.pop("locations", None)
        self.cfg.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self.v.update("install", str(self.zip))
        loc = self.saved()
        self.assertEqual(loc["offsite_backup"], self.NEW)
        self.assertIn("99 System", loc["never_index"])


class TestLiveServer(unittest.TestCase):
    """The dashboard's Settings › creaite version, through the live server."""

    @classmethod
    def setUpClass(cls):
        cls.zip = build_release()
        cls.v = UpdateVault()
        cls.port = free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.proc = subprocess.Popen([sys.executable, str(cls.v.root / "system/scripts/live_server.py")],
                                    env={**os.environ, "CREAITE_PORT": str(cls.port)},
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            try:
                urllib.request.urlopen(cls.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        cls.token = cls.page_token()

    @classmethod
    def page_token(cls):
        html = urllib.request.urlopen(cls.base + "/").read().decode()
        return json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.v.cleanup()

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def test_upload_review_install_undo(self):
        status = self.post("/api/update/status", {})[1]
        self.assertEqual(status["installed"], "0.9.0")
        self.assertFalse(status["dev"])
        code, bad = self.post("/api/update/upload", {"name": "creaite-main.zip", "data": ""})
        self.assertEqual(code, 400)
        self.assertIn("Source code", bad["message"])
        data = base64.b64encode(self.zip.read_bytes()).decode()
        self.assertTrue(self.post("/api/update/upload", {"name": self.zip.name, "data": data})[1]["ok"])
        status = self.post("/api/update/status", {})[1]
        self.assertEqual(status["releases"], {"version": VERSION, "name": self.zip.name})
        plan = self.post("/api/update/inspect", {"source": "releases"})[1]
        self.assertEqual(plan["plan"]["to"], VERSION)
        self.assertEqual((self.v.root / "VERSION").read_text().strip(), "0.9.0")
        started, before = json.loads((self.v.root / "system/staging/live-server.json").read_text()), self.token
        done = self.post("/api/update/install", {"source": "releases"})[1]
        self.assertTrue(done["ok"], done["message"])
        self.assertEqual((self.v.root / "VERSION").read_text().strip(), VERSION)
        # BL-320: update.py reports its after-update steps and restarts this server in place (same pid), once it is free
        for label in ("Launcher: There's no launcher for this vault", "App icon: ", "Live server: The live server on port"):
            self.assertIn(label, done["message"])
        self.assertNotIn("Restart the live server", done["message"])
        for _ in range(100):
            try:
                again = json.loads((self.v.root / "system/staging/live-server.json").read_text())
                if self.page_token() != self.token:                             # a new run: a new token
                    break
            except (OSError, ValueError):
                pass
            time.sleep(0.2)
        type(self).token = self.page_token()
        self.assertNotEqual(self.token, before)
        self.assertEqual(self.post("/api/update/status", {})[1]["installed"], VERSION)
        self.assertEqual(again["pid"], started["pid"])
        self.assertEqual(self.post("/api/update/status", {})[1]["last"]["to"], VERSION)
        undone = self.post("/api/update/undo", {})[1]
        self.assertTrue(undone["ok"], undone["message"])
        self.assertEqual((self.v.root / "VERSION").read_text().strip(), "0.9.0")
        self.assertFalse(self.post("/api/update/inspect", {"source": "/etc"})[1]["ok"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
