"""The daily zip's git bundle (vault.bundle, BL-323) must not carry what the zip itself leaves out.

cx-setup's first commit is `git add -A` under the vault's .gitignore (system/templates/vault-gitignore). If that file lets
ask creaite's chats, their images or vip.json (BL-288) into a commit, `git bundle create --all` copies them into the zip and
its OneDrive copy. This builds a throwaway vault, makes cx-setup's first commit, plants the private files, bundles with
backup.make_bundle, clones the bundle and looks for the marker strings.

Run: python3 dev/tests/test_bundle_privacy.py     (quick tier; needs git)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
from test_tracker import Vault  # noqa: E402

GIT = shutil.which("git")
TEMPLATE = REPO / "system/templates/vault-gitignore"
ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com", "GIT_COMMITTER_NAME": "t",
       "GIT_COMMITTER_EMAIL": "t@example.com"}
CHAT, IMAGE, VIP, CAL, CONFIG, MEMORY = ("MARK-CHAT-7f3a", "MARK-IMAGE-2b9c", "MARK-VIP-51de", "MARK-CALENDAR-88a0",
                                         "MARK-CONFIG-04cc", "MARK-MEMORY-c1d2")
PRIVATE = {"system/staging/ask/chat-x.json": CHAT, "system/staging/uploads/ask/pic.png": IMAGE,
           "system/staging/vip.json": VIP, "system/staging/calendar.json": CAL,
           "system/staging/drafts/calendar-raw.json": CAL}


def git(root, *args):
    r = subprocess.run([GIT, "-C", str(root), *args], capture_output=True, text=True, env=ENV, timeout=120)
    if r.returncode:
        raise AssertionError(f"git {args}: {r.stderr}")
    return r.stdout


@unittest.skipUnless(GIT, "needs git")
class BundlePrivacy(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.root = self.v.root
        self.addCleanup(self.v.cleanup)

    def plant(self):
        for rel, mark in PRIVATE.items():
            f = self.root / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(f"{mark}\n")
        (self.root / "system/config").mkdir(parents=True, exist_ok=True)
        (self.root / "system/config/settings.json").write_text(f'{{"marker": "{CONFIG}"}}\n')
        (self.root / "projects/_portfolio").mkdir(parents=True, exist_ok=True)
        (self.root / "projects/_portfolio/PORTFOLIO.md").write_text(f"# Portfolio\n{MEMORY}\n")

    def bundle_text(self, template=None):
        """cx-setup step 1: git init, the template as .gitignore, `git add -A`, first commit. Then the bundle step."""
        shutil.copy(template or TEMPLATE, self.root / ".gitignore")
        self.plant()
        git(self.root, "init", "-q")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "first commit")
        dest = Path(tempfile.mkdtemp(prefix="creaite-bundle-")).resolve()
        self.addCleanup(shutil.rmtree, dest, ignore_errors=True)
        code = "import sys; sys.path.insert(0, 'system/scripts'); import backup; r = backup.make_bundle(sys.argv[1]); print(r)"
        r = subprocess.run([sys.executable, "-c", code, str(dest / "vault.bundle")], cwd=self.root, capture_output=True,
                           text=True, timeout=300)
        self.assertEqual(r.stdout.strip(), "None", r.stdout + r.stderr)
        subprocess.run([GIT, "clone", "-q", str(dest / "vault.bundle"), str(dest / "clone")], check=True, env=ENV,
                       capture_output=True)
        # every blob in every commit, not only the checked-out tree
        objs = git(dest / "clone", "rev-list", "--objects", "--all")
        names = {line.split(" ", 1)[1] for line in objs.splitlines() if " " in line}
        text = "\n".join(git(dest / "clone", "grep", "-I", "-e", "MARK-", "HEAD").splitlines())
        return names, text

    def test_bundle_holds_neither_chats_images_nor_vip(self):
        names, text = self.bundle_text()
        for rel in PRIVATE:
            self.assertNotIn(rel, names, f"{rel} is in the bundle")
        for mark in (CHAT, IMAGE, VIP, CAL):
            self.assertNotIn(mark, text)
        self.assertFalse([n for n in names if n.startswith("system/staging/")], "staging is in the bundle")

    def test_bundle_still_holds_memory_scripts_and_config(self):
        names, text = self.bundle_text()
        self.assertIn("projects/_portfolio/PORTFOLIO.md", names)
        self.assertIn("system/scripts/backup.py", names)
        self.assertIn("system/config/settings.json", names)
        self.assertIn(MEMORY, text)
        self.assertIn(CONFIG, text)

    def test_mutant_template_without_the_entries_leaks(self):
        weak = Path(tempfile.mkdtemp(prefix="creaite-gi-")) / "gitignore"
        self.addCleanup(shutil.rmtree, weak.parent, ignore_errors=True)
        lines = [ln for ln in TEMPLATE.read_text().splitlines() if not ln.strip().startswith("system/staging")]
        weak.write_text("\n".join(lines) + "\n")
        names, text = self.bundle_text(weak)
        tracked = git(self.root, "ls-files").splitlines()
        self.assertIn("system/staging/ask/chat-x.json", tracked)       # the template is what keeps it out of git
        if not patched():                                              # with the filtered bundle the zip is safe anyway
            self.assertIn("system/staging/ask/chat-x.json", names)
            self.assertIn(VIP, text)

    def test_template_lists_the_entries(self):
        entries = {ln.strip() for ln in TEMPLATE.read_text().splitlines()}
        for need in ("system/staging/", "system/logs/", "system/branding/", "system/tracker.db"):
            self.assertIn(need, entries)
        text = TEMPLATE.read_text()
        self.assertNotIn("system/config/", entries, "config is meant to stay in the history")
        self.assertIn("vip.json", text)       # the reason is written down


@unittest.skipUnless(GIT, "needs git")
class HealthNote(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.root = self.v.root
        self.addCleanup(self.v.cleanup)

    def test_doctor_shows_the_snapshot_note(self):
        r = vault_py(self.root, "import doctor; backup.save_state('verify', {'day': backup.today().isoformat(), 'ok': True, "
                                "'problems': [], 'checked': ['z.zip'], 'note': 'git history in the zip: one snapshot commit'}); "
                                "print(json.dumps(doctor.backup_check()))")
        self.assertIn("one snapshot commit", r.stdout, r.stdout + r.stderr)


def patched():
    """True when system/scripts/backup.py has the filtered bundle (dev/proposals/bundle/backup-bundle.diff applied)."""
    return "PRIVATE_PATHS" in (REPO / "system/scripts/backup.py").read_text(encoding="utf-8")


def rev5():
    """True when backup.py also has revision 5 (dev/proposals/bundle/backup-bundle-rev5.diff: no background gc, tolerant cleanup)."""
    return "gc.auto=0" in (REPO / "system/scripts/backup.py").read_text(encoding="utf-8")


def vault_py(root, code, *args, env=None):
    """Run Python inside the vault's scripts folder; returns the completed process."""
    return subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts'); import backup; " + code,
                           *args], cwd=root, capture_output=True, text=True, timeout=300,
                          env={**(env or ENV), "PYTHONDONTWRITEBYTECODE": "1"})


@unittest.skipUnless(GIT and patched(), "needs git and the filtered bundle (dev/proposals/bundle/backup-bundle.diff)")
class ExistingVault(unittest.TestCase):
    """A vault whose OLD history holds a chat and vip.json (made before the gitignore knew them)."""

    def setUp(self):
        self.v = Vault()
        self.root = self.v.root
        self.addCleanup(self.v.cleanup)
        self.work = Path(tempfile.mkdtemp(prefix="creaite-bundle-")).resolve()
        self.addCleanup(shutil.rmtree, self.work, ignore_errors=True)
        (self.root / "projects/_portfolio").mkdir(parents=True, exist_ok=True)
        (self.root / "projects/_portfolio/PORTFOLIO.md").write_text(f"# Portfolio\n{MEMORY}\n")
        git(self.root, "init", "-q")

    def old_history(self, untrack=True):
        for rel in ("system/staging/ask/chat-x.json", "system/staging/vip.json"):
            f = self.root / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(f"{CHAT if 'chat' in rel else VIP}\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "old first commit")
        if not untrack:                                                 # an old vault that never ran the untrack step
            return
        shutil.copy(TEMPLATE, self.root / ".gitignore")                 # later: ignored and untracked
        git(self.root, "rm", "-r", "-q", "--cached", "system/staging")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "stop tracking staging")

    def state(self):
        return (git(self.root, "rev-parse", "HEAD"), git(self.root, "for-each-ref"), git(self.root, "status", "--porcelain"),
                (self.root / ".git/index").read_bytes())

    def bundle(self):
        dest = self.work / "vault.bundle"
        r = vault_py(self.root, "r = backup.make_bundle(sys.argv[1]); print(json.dumps(r))", str(dest))
        self.assertEqual(r.returncode, 0, r.stderr)
        return dest, json.loads(r.stdout.strip().splitlines()[-1])

    def everything(self, dest):
        clone = self.work / "clone"
        subprocess.run([GIT, "clone", "-q", str(dest), str(clone)], check=True, env=ENV, capture_output=True)
        text = ""
        for line in git(clone, "rev-list", "--objects", "--all").splitlines():
            sha = line.split(" ", 1)[0]
            if git(clone, "cat-file", "-t", sha).strip() in ("blob", "commit"):
                text += subprocess.run([GIT, "-C", str(clone), "cat-file", "-p", sha], capture_output=True).stdout.decode("utf-8", "replace")
        return clone, text

    def test_old_history_is_not_bundled_and_the_repo_is_untouched(self):
        self.old_history()
        before = self.state()
        dest, why = self.bundle()
        self.assertIsNone(why)
        self.assertEqual(self.state(), before, "make_bundle changed the vault's repository")
        clone, text = self.everything(dest)
        for mark in (CHAT, VIP):
            self.assertNotIn(mark, text)
        self.assertIn(MEMORY, text)
        self.assertEqual(git(clone, "rev-list", "--count", "--all").strip(), "1")      # a snapshot

    def test_private_file_reachable_only_through_a_merge_is_found(self):
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "base")
        trunk = git(self.root, "symbolic-ref", "--short", "HEAD").strip()
        git(self.root, "checkout", "-q", "-b", "side")
        self.old_history(untrack=False)                                  # the chat and vip.json, on `side` only
        git(self.root, "checkout", "-q", trunk)
        git(self.root, "merge", "-q", "--no-ff", "-s", "ours", "side", "-m", "merge, ours")
        git(self.root, "branch", "-q", "-D", "side")
        self.assertNotIn("system/staging/vip.json", git(self.root, "ls-tree", "-r", "--name-only", "HEAD"))
        dest, why = self.bundle()
        self.assertIsNone(why)
        text = self.everything(dest)[1]
        for mark in (CHAT, VIP):
            self.assertNotIn(mark, text)

    def test_upper_case_private_path_is_found(self):
        f = self.work / "c.json"
        f.write_text(f"{CHAT}\n")
        sha = git(self.root, "hash-object", "-w", str(f)).strip()
        git(self.root, "update-index", "--add", "--cacheinfo", f"100644,{sha},System/Staging/ask/c.json")
        keep = self.root / "projects/_portfolio/PORTFOLIO.md"
        keep.parent.mkdir(parents=True, exist_ok=True)
        keep.write_text(f"{MEMORY}\n")
        git(self.root, "add", "projects")
        git(self.root, "commit", "-q", "-m", "linux commit")
        git(self.root, "rm", "-q", "--cached", "System/Staging/ask/c.json")
        git(self.root, "commit", "-q", "-m", "removed")
        dest, why = self.bundle()
        self.assertIsNone(why)
        self.assertNotIn(CHAT, self.everything(dest)[1])

    def test_head_tracking_upper_case_private_path_is_filtered(self):
        f = self.work / "c.json"
        f.write_text(f"{CHAT}\n")
        sha = git(self.root, "hash-object", "-w", str(f)).strip()
        git(self.root, "update-index", "--add", "--cacheinfo", f"100644,{sha},System/Staging/ask/c.json")
        (self.root / "keep.txt").write_text(f"{MEMORY}\n")
        git(self.root, "add", "keep.txt")
        git(self.root, "commit", "-q", "-m", "x")
        dest, why = self.bundle()
        self.assertIsNone(why)
        clone, text = self.everything(dest)
        self.assertNotIn(CHAT, text)
        self.assertIn(MEMORY, text)

    def test_snapshot_keeps_export_ignored_and_tracked_ignored_files_and_runs_no_hook(self):
        (self.root / ".gitattributes").write_text("notes/export.txt export-ignore\n")
        (self.root / "notes").mkdir()
        (self.root / "notes/export.txt").write_text("EXPORTED\n")
        (self.root / ".gitignore").write_text("kept-but-ignored.txt\n")
        (self.root / "kept-but-ignored.txt").write_text("IGNORED-BUT-TRACKED\n")
        self.old_history(untrack=False)
        git(self.root, "add", "-f", "-A")
        git(self.root, "commit", "-q", "-m", "more")
        hooks, marker = self.work / "hooks", self.work / "hook-ran"
        hooks.mkdir()
        (hooks / "pre-commit").write_text(f"#!/bin/sh\ntouch {marker}\n")
        (hooks / "pre-commit").chmod(0o755)
        home = self.work / "home"                                      # the user's real global config: ~/.gitconfig
        home.mkdir()
        (home / ".gitconfig").write_text(f"[core]\n\thooksPath = {hooks}\n\texcludesFile = {self.work}/ignore\n")
        (self.work / "ignore").write_text("*.txt\n")
        dest = self.work / "vault.bundle"
        r = vault_py(self.root, "print(json.dumps(backup.make_bundle(sys.argv[1])))", str(dest),
                     env={**ENV, "HOME": str(home)})
        self.assertEqual(json.loads(r.stdout.strip().splitlines()[-1]), None, r.stderr)
        self.assertFalse(marker.exists(), "the user's commit hook ran on the snapshot")
        clone = self.everything(dest)[0]
        names = git(clone, "ls-files").splitlines()
        self.assertIn("notes/export.txt", names)
        self.assertIn("kept-but-ignored.txt", names)
        self.assertIn(".gitattributes", names)

    def test_exported_git_variables_cannot_reach_the_real_repository(self):
        self.old_history(untrack=False)
        gd = self.root / ".git"
        cases = {"GIT_INDEX_FILE": {"GIT_INDEX_FILE": str(gd / "index")},
                 "GIT_DIR": {"GIT_DIR": str(gd)},
                 "GIT_DIR+GIT_WORK_TREE": {"GIT_DIR": str(gd), "GIT_WORK_TREE": str(self.root)},
                 "GIT_OBJECT_DIRECTORY": {"GIT_OBJECT_DIRECTORY": str(gd / "objects")}}
        for name, extra in cases.items():
            with self.subTest(name):
                status = git(self.root, "status", "--porcelain")           # refreshes the index first
                before = ((gd / "index").read_bytes(), (gd / "config").read_bytes(), (gd / "HEAD").read_bytes(),
                          git(self.root, "for-each-ref"), status)
                dest = self.work / f"{name}.bundle"
                r = vault_py(self.root, "print(json.dumps(backup.make_bundle(sys.argv[1])))", str(dest),
                             env={**ENV, **extra})
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertIsNone(json.loads(r.stdout.strip().splitlines()[-1]), r.stdout)
                idx, cfg, head = (gd / "index").read_bytes(), (gd / "config").read_bytes(), (gd / "HEAD").read_bytes()
                after = (idx, cfg, head, git(self.root, "for-each-ref"), git(self.root, "status", "--porcelain"))
                self.assertEqual(after, before, f"{name} changed the vault's repository")

    def many_files_vault(self, n=1500):
        """A vault of n tiny tracked files (as many loose objects) plus a private file, so git's own `gc --auto` would start."""
        d = self.root / "many"
        d.mkdir()
        for i in range(n):
            (d / f"f{i}.txt").write_text(f"{i}\n")
        for i in range(12):                                              # incompressible, so a repack takes a while
            (d / f"big{i}.bin").write_bytes(os.urandom(1_000_000))
        (self.root / "system/staging/ask").mkdir(parents=True)
        (self.root / "system/staging/ask/chat-x.json").write_text(f"{CHAT}\n")
        git(self.root, "add", "-f", "-A")
        git(self.root, "commit", "-q", "-m", "many")

    @unittest.skipUnless(rev5(), "needs revision 5 (backup-bundle-rev5.diff)")
    def test_snapshot_survives_background_gc(self):
        """The CI failure: the temp repository's detached `gc --auto` was still writing when its folder was deleted
        ("Directory not empty"), so the day had no bundle. A global gc.auto=1 makes it start every time."""
        self.many_files_vault()
        home = self.work / "home"
        home.mkdir()
        (home / ".gitconfig").write_text("[gc]\n\tauto = 1\n[maintenance]\n\tstrategy = gc\n")
        dest, tmp = self.work / "vault.bundle", self.work / "tmp"
        tmp.mkdir()
        r = vault_py(self.root, "print(json.dumps(backup.make_bundle(sys.argv[1])))", str(dest),
                     env={**ENV, "HOME": str(home), "TMPDIR": str(tmp)})
        self.assertIsNone(json.loads(r.stdout.strip().splitlines()[-1]), r.stdout + r.stderr)
        self.assertEqual(list(tmp.iterdir()), [], "the temporary folder was left behind (a background gc was still writing)")
        clone, text = self.everything(dest)
        self.assertNotIn(CHAT, text)
        self.assertEqual(git(clone, "rev-list", "--count", "--all").strip(), "1")

    @unittest.skipUnless(rev5(), "needs revision 5 (backup-bundle-rev5.diff)")
    def test_a_folder_that_will_not_delete_does_not_discard_the_bundle(self):
        self.old_history(untrack=False)
        dest = self.work / "vault.bundle"
        code = ("import shutil; real = shutil.rmtree\n"
                "def boom(path, *a, **k):\n"
                "    if 'creaite-bundle-' in str(path):\n"
                "        if k.get('ignore_errors'): return\n"
                "        raise OSError(39, 'Directory not empty')\n"
                "    return real(path, *a, **k)\n"
                "backup.shutil.rmtree = boom\n"
                "print(json.dumps(backup.make_bundle(sys.argv[1])))")
        r = vault_py(self.root, code, str(dest))
        self.assertIsNone(json.loads(r.stdout.strip().splitlines()[-1]), r.stdout + r.stderr)
        self.assertTrue(dest.is_file())

    def fresh_vault(self):
        fresh = Path(tempfile.mkdtemp(prefix="creaite-fresh-")).resolve()
        self.addCleanup(shutil.rmtree, fresh, ignore_errors=True)
        (fresh / "system/scripts").mkdir(parents=True)
        for f in (self.root / "system/scripts").glob("*.py"):
            shutil.copy(f, fresh / "system/scripts" / f.name)
        return fresh

    def repo_state(self):
        gd = self.root / ".git"
        status = git(self.root, "status", "--porcelain")
        objs = sorted(str(f.relative_to(gd)) for f in (gd / "objects").rglob("*") if f.is_file())
        return ((gd / "index").read_bytes(), (gd / "config").read_bytes(), (gd / "HEAD").read_bytes(),
                git(self.root, "for-each-ref"), status, objs)

    def test_verify_and_restore_ignore_exported_git_variables(self):
        gd = self.root / ".git"
        cases = {"GIT_INDEX_FILE": {"GIT_INDEX_FILE": str(gd / "index")}, "GIT_DIR": {"GIT_DIR": str(gd)},
                 "GIT_DIR+GIT_WORK_TREE": {"GIT_DIR": str(gd), "GIT_WORK_TREE": str(self.root)},
                 "GIT_OBJECT_DIRECTORY": {"GIT_OBJECT_DIRECTORY": str(gd / "objects")}}
        shutil.copy(TEMPLATE, self.root / ".gitignore")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "one")
        (self.root / "projects/_portfolio/PORTFOLIO.md").write_text("# Portfolio\nchanged\n")
        git(self.root, "commit", "-q", "-am", "two")
        full, _ = self.bundle()                                          # a clean history: the whole of it (2 commits)
        full = full.rename(self.work / "full.bundle")
        (self.root / "system/staging/ask").mkdir(parents=True)
        (self.root / "system/staging/ask/chat-x.json").write_text(f"{CHAT}\n")
        git(self.root, "add", "-f", "-A")
        git(self.root, "commit", "-q", "-m", "chat")
        snap, _ = self.bundle()                                          # a snapshot (1 commit)
        self.assertEqual(git(self.everything(snap)[0], "rev-list", "--count", "--all").strip(), "1")
        for kind, bundle, commits in (("snapshot", snap, "1"), ("full", full, "2")):
            for name, extra in cases.items():
                with self.subTest(f"{kind} {name}"):
                    fresh = self.fresh_vault()
                    before = self.repo_state()
                    r = vault_py(fresh, "print(backup.restore_git(open(sys.argv[1], 'rb').read())); "
                                        "print(backup.verify_bundle(sys.argv[1], sys.argv[2]))", str(bundle),
                                 str(self.work / f"scratch-{kind}-{name}"), env={**ENV, **extra})
                    self.assertIn("git history restored", r.stdout, r.stdout + r.stderr)
                    self.assertEqual(r.stdout.strip().splitlines()[-1], "None")
                    self.assertEqual(self.repo_state(), before, "the vault's own repository changed")
                    self.assertTrue((fresh / ".git").is_dir(), "the restored vault has no .git of its own")
                    self.assertEqual(git(fresh, "rev-list", "--count", "HEAD").strip(), commits)

    def test_a_moved_private_file_stays_in_the_snapshot(self):
        """Known limit of a path filter (README, NOTES): a private file renamed to another path is not recognised."""
        self.old_history(untrack=False)
        git(self.root, "mv", "system/staging/vip.json", "notes-vip.json")
        git(self.root, "commit", "-q", "-m", "moved")
        dest, why = self.bundle()
        self.assertIn(VIP, self.everything(dest)[1])

    def test_head_still_tracking_private_files_is_filtered(self):
        self.old_history(untrack=False)
        dest, why = self.bundle()
        self.assertIsNone(why)
        text = self.everything(dest)[1]
        for mark in (CHAT, VIP):
            self.assertNotIn(mark, text)

    def test_clean_history_keeps_every_commit(self):
        shutil.copy(TEMPLATE, self.root / ".gitignore")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "one")
        (self.root / "projects/_portfolio/PORTFOLIO.md").write_text("# Portfolio\nchanged\n")
        git(self.root, "commit", "-q", "-am", "two")
        dest, why = self.bundle()
        self.assertIsNone(why)
        self.assertEqual(git(self.everything(dest)[0], "rev-list", "--count", "--all").strip(), "2")

    def test_restore_reads_the_snapshot(self):
        self.old_history()
        dest, _ = self.bundle()
        fresh = Path(tempfile.mkdtemp(prefix="creaite-fresh-")).resolve()
        self.addCleanup(shutil.rmtree, fresh, ignore_errors=True)
        (fresh / "system/scripts").mkdir(parents=True)
        for f in (self.root / "system/scripts").glob("*.py"):
            shutil.copy(f, fresh / "system/scripts" / f.name)
        r = vault_py(fresh, "print(backup.restore_git(open(sys.argv[1], 'rb').read())); "
                            "print(backup.verify_bundle(sys.argv[1], sys.argv[2]))", str(dest), str(self.work / "scratch"))
        self.assertIn("git history restored", r.stdout, r.stdout + r.stderr)
        self.assertEqual(r.stdout.strip().splitlines()[-1], "None")                  # the weekly check reads it
        self.assertIn("projects/_portfolio/PORTFOLIO.md", git(fresh, "ls-tree", "-r", "--name-only", "HEAD"))
        self.assertTrue(git(fresh, "symbolic-ref", "HEAD").strip().startswith("refs/heads/"))

    def test_failure_leaves_no_bundle_and_the_manifest_says_so(self):
        self.old_history()
        day = "2026-10-14"
        self.v.run("init")
        (self.root / "system/backups").mkdir(parents=True, exist_ok=True)
        shutil.copy(self.root / "system/tracker.db", self.root / f"system/backups/tracker-{day}.db")
        code = ("backup.run_git = lambda *a, **k: __import__('subprocess').CompletedProcess(a, 1, b'', 'boom'); "
                "import zipfile; p = backup.make_zip(sys.argv[1]); z = zipfile.ZipFile(p); "
                "print(json.dumps({'names': z.namelist(), 'manifest': json.loads(z.read('manifest.json'))}))")
        r = vault_py(self.root, code, day)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertNotIn("vault.bundle", out["names"])
        self.assertIn("git bundle failed", out["manifest"]["git"])

    def test_git_missing_gives_no_bundle(self):
        self.old_history()
        r = vault_py(self.root, "backup.shutil.which = lambda n: None; print(json.dumps(backup.make_bundle(sys.argv[1])))",
                     str(self.work / "x.bundle"))
        self.assertEqual(json.loads(r.stdout.strip().splitlines()[-1]), "git isn't installed")
        self.assertFalse((self.work / "x.bundle").exists())


if __name__ == "__main__":
    unittest.main()
