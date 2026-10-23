"""v2.6.1: the two LOW notes of the 2.6.0 re-cut security review (issue #275), and the dead `rel`.

Run: python3 dev/tests/test_paths_resolved_low_notes.py      (quick tier: plain code and a throwaway vault, no Chrome, no Claude)

- L1: paths._resolved keeps the name and resolves the folder only for EINVAL (the CPython 3.9.25 realpath race), and never when the
  last part is `.`, `..` or empty: a path that raised is never handed back un-normalised. Any other OSError is raised as before.
  The race is forced by a stand-in for Path.resolve; nothing here races anything.
- L2: tracker.safe_path refuses a NUL byte in its own words (it must still refuse). The tracker.py change is a guarded-file
  proposal, dev/proposals/261-low-notes/tracker-resolve-einval.diff; this test applies it to a throwaway vault's copy of tracker.py
  (or takes the copy as it is when the diff has already been applied).
- INFO: paths.py has one `def rel` (the older one, shadowed by the later, was dead).

All names are made up.
"""
import errno
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "system" / "scripts"))
import paths  # noqa: E402
from test_tracker import make_vault  # noqa: E402

DIFF = REPO / "dev" / "proposals" / "261-low-notes" / "tracker-resolve-einval.diff"
REAL_RESOLVE = pathlib.Path.resolve


def failing_resolve(names, err):
    """A Path.resolve that raises OSError(err) for a path whose last part is in `names`, and otherwise resolves for real."""
    def resolve(self, *a, **k):
        if self.name in names:
            raise OSError(err, "forced", str(self))
        return REAL_RESOLVE(self, *a, **k)
    return mock.patch.object(pathlib.Path, "resolve", resolve)


class ResolvedLowNotes(unittest.TestCase):
    def test_einval_on_an_ordinary_name_keeps_the_name(self):         # the 2.6.0 behaviour that the E1 flip test needs
        p = paths.ROOT / "inbox" / "linkfile"
        with failing_resolve({"linkfile"}, errno.EINVAL):
            self.assertEqual(paths._resolved(p), REAL_RESOLVE(paths.ROOT / "inbox") / "linkfile")
            self.assertEqual(paths.rel(p), "inbox/linkfile")

    def test_einval_on_dotdot_is_raised_never_returned_unnormalised(self):          # L1
        p = paths.ROOT / "inbox" / "x" / ".."
        with failing_resolve({".."}, errno.EINVAL):
            with self.assertRaises(OSError):
                paths._resolved(p)
            with self.assertRaises(OSError):
                paths.rel(p)

    def test_einval_on_dot_or_empty_name_is_raised(self):                           # L1: Path(".").name and Path("/").name are empty
        for p in (Path("."), Path("/")):
            with failing_resolve({""}, errno.EINVAL):
                with self.assertRaises(OSError):
                    paths._resolved(p)

    def test_another_oserror_is_raised_not_swallowed(self):                         # L1: only the EINVAL race is bridged
        for err in (errno.EACCES, errno.ELOOP, errno.ENAMETOOLONG, errno.EIO):
            with self.subTest(errno=errno.errorcode[err]), failing_resolve({"linkfile"}, err):
                with self.assertRaises(OSError) as cm:
                    paths._resolved(paths.ROOT / "inbox" / "linkfile")
                self.assertEqual(cm.exception.errno, err)

    def test_no_error_resolves_as_before(self):
        self.assertEqual(paths.rel(paths.ROOT / "inbox" / ".." / "inbox" / "a.txt"), "inbox/a.txt")

    def test_a_nul_byte_in_paths_stays_a_valueerror(self):                          # L2: paths.py is unchanged here; tracker.safe_path refuses it
        with self.assertRaises(ValueError):
            paths._resolved(str(paths.ROOT / "inbox" / "a\0b"))

    def test_paths_py_has_one_rel(self):                                            # INFO: the older `def rel` was dead
        src = (REPO / "system" / "scripts" / "paths.py").read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r"^def rel\(", src, re.M)), 1)


DRIVER = '''
import errno, sys
import paths, tracker
out = []
for rp in ("inbox/a\\0b", "inbox/\\0", "projects/ABC Example Programme/minutes/x\\0.docx"):
    try:
        tracker.safe_path(rp, "t")
        out.append("ACCEPTED")
    except tracker.Invalid as e:
        out.append(str(e))
orig = paths.rel
def raced(p):
    raise OSError(errno.EINVAL, "forced", str(p))
paths.rel = raced
try:
    tracker.safe_path("inbox/m.txt", "remove")
    out.append("ACCEPTED")
except tracker.Invalid as e:
    out.append(str(e))
paths.rel = orig
print("\\n".join(out))
'''


class TrackerNul(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vault = make_vault()
        cls.addClassCleanup(shutil.rmtree, cls.vault, True)
        t = cls.vault / "system" / "scripts" / "tracker.py"
        dry = subprocess.run(["patch", "-p1", "-N", "--dry-run", "-i", str(DIFF)], cwd=cls.vault, capture_output=True, text=True)
        if dry.returncode == 0:
            done = subprocess.run(["patch", "-p1", "-N", "-i", str(DIFF)], cwd=cls.vault, capture_output=True, text=True)
            assert done.returncode == 0, done.stdout + done.stderr
        else:    # not applying: fine only when the change is already in tracker.py (the diff then reverses cleanly)
            rev = subprocess.run(["patch", "-p1", "-R", "--dry-run", "-i", str(DIFF)], cwd=cls.vault, capture_output=True, text=True)
            assert rev.returncode == 0, "the diff neither applies nor is already applied:\n" + dry.stdout + dry.stderr
        assert "path contains a NUL character" in t.read_text(encoding="utf-8"), "the diff did not put the NUL check in tracker.py"
        (cls.vault / "system" / "scripts" / "drive_nul.py").write_text(DRIVER, encoding="utf-8")
        r = subprocess.run([sys.executable, str(cls.vault / "system" / "scripts" / "drive_nul.py")], cwd=tempfile.gettempdir(),
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        cls.lines = r.stdout.splitlines()
        assert t.exists()

    def test_a_nul_byte_is_refused_in_its_own_words(self):                          # L2
        for line in self.lines[:3]:
            self.assertEqual(line.split(":")[1].strip(), "path contains a NUL character", line)
            self.assertNotIn("outside the vault", line)

    def test_a_raced_resolve_is_still_refused_in_relative_words(self):              # the 2.6.0 behaviour, kept
        self.assertEqual(self.lines[3], "remove: inbox/m.txt changed while it was being checked (OSError)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
