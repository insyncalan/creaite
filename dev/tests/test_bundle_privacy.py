"""The daily zip's git bundle (vault.bundle, BL-323) must not carry what the zip itself leaves out.

cx-setup's first commit is `git add -A` under the vault's .gitignore (system/templates/vault-gitignore). If that file lets
ask creaite's chats, their images or vip.json (BL-288) into a commit, `git bundle create --all` copies them into the zip and
its OneDrive copy. This builds a throwaway vault, makes cx-setup's first commit, plants the private files, bundles with
backup.make_bundle, clones the bundle and looks for the marker strings.

Run: python3 dev/tests/test_bundle_privacy.py     (quick tier; needs git)
"""
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
        self.assertIn("system/staging/ask/chat-x.json", names)
        self.assertIn(VIP, text)

    def test_template_lists_the_entries(self):
        entries = {ln.strip() for ln in TEMPLATE.read_text().splitlines()}
        for need in ("system/staging/", "system/logs/", "system/branding/", "system/tracker.db"):
            self.assertIn(need, entries)
        text = TEMPLATE.read_text()
        self.assertNotIn("system/config/", entries, "config is meant to stay in the history")
        self.assertIn("vip.json", text)       # the reason is written down


if __name__ == "__main__":
    unittest.main()
