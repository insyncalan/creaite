"""#261 PROPOSAL tests: the remove of someone else's minutes holds the file open until the unlink, so a reused inode number can't
make a DIFFERENT file look like the staged one. They run against a patched scratch copy, like test_minutes_by_others_filing.

Run: python3 dev/tests/test_tracker_inode_hold.py

The gap (Linux ext4 and tmpfs, not APFS): `_remove_checked` read the staged inbox file through `_read_regular`, which closed it,
then `_unlink_same` moved the name aside and compared (st_dev, st_ino) with what was read. Once closed and unlinked, the inode is
free, and Linux gives its number straight to the next file made: a different file written at the name in between had the same
identity and was deleted. The fix (dev/proposals/261-inode-gap/tracker-inode.py.diff) keeps a descriptor of the file read open
until the unlink, so no other file can have its number.

`tracker.py` is guarded: the scratch vault gets a copy of it and the diff is applied there with `patch -p1` (or, once the diff is
in the repo, reversed for the defect test). The reuse is proved on any platform by a faithful fake of Linux's rule: os.stat of
the moved-aside name reports the staged file's inode number only while no descriptor in the process still holds that inode (the
only time POSIX lets the number be reused). A second test uses no fake at all: on Linux CI it is red without the fix.
"""
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_minutes_by_others_filing import FILE, INODE_DIFF, INODE_MARKER, Base  # noqa: E402

# A swap made in the backup hook (after the file is read and checked, before the move and the unlink): the staged file is
# unlinked and a different file written at its name, with NO descriptor kept by the swap (unlike HOLD in the E1 tests).
DRIVER = r"""
import sys, os
sys.path.insert(0, 'system/scripts')
from pathlib import Path
import tracker
NAME, FAKE = %(name)r, %(fake)r
state = {}
orig_stash = tracker.stash
def stash(*a, **k):
    p = Path('inbox') / NAME
    o = os.stat(p)
    state['id'] = (o.st_dev, o.st_ino)
    r = orig_stash(*a, **k)
    p.unlink()
    p.write_text("Somebody else's file\n")
    return r
tracker.stash = stash
def held(ident):
    for fd in range(1024):
        try:
            s = os.fstat(fd)
        except OSError:
            continue
        if (s.st_dev, s.st_ino) == ident:
            return True
    return False
real_stat = os.stat
def linux_stat(path, *a, **k):
    # Linux's rule: a freed inode number goes to the next file made; a number still held by an open descriptor never does
    s = real_stat(path, *a, **k)
    ident = state.get('id')
    if ident and str(path).startswith('.creaite-removing-') and s.st_dev == ident[0] and not held(ident):
        f = list(s)
        f[1] = ident[1]
        return os.stat_result(f)
    return s
if FAKE:
    os.stat = linux_stat
def leaked():
    # a descriptor still open on the staged file, now unlinked (no name left): the hold was not closed
    n = 0
    for fd in range(1024):
        try:
            s = os.fstat(fd)
        except OSError:
            continue
        n += (s.st_dev, s.st_ino) == state.get('id') and s.st_nlink == 0
    return n
print('RC', tracker.main(['apply']))
print('LEAKED', leaked())
"""


def _patch_inode(root, *flags):
    r = subprocess.run(["patch", "-p1", "-s", *flags, "-i", str(INODE_DIFF)], cwd=root, capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError(f"patch {' '.join(flags)} of {INODE_DIFF.name} failed in the scratch copy:\n{r.stdout}\n{r.stderr}")


class InodeBase(Base):
    HELD = True                                     # the #261 diff on (True) or off (False) in the scratch copy

    def setUp(self):
        super().setUp()                             # E1 on (PATCHED stays True)
        tracker = self.v.root / "system" / "scripts" / "tracker.py"
        has = INODE_MARKER in tracker.read_text(encoding="utf-8")
        if self.HELD and not has:
            _patch_inode(self.v.root)
        if not self.HELD and has:
            _patch_inode(self.v.root, "-R")

    def drive(self, fake):
        self.decide("approved", "approved")
        r = subprocess.run([sys.executable, "-c", DRIVER % {"name": Path(FILE).name, "fake": fake}], cwd=self.v.root,
                           capture_output=True, text=True, timeout=120)
        return r.stdout + r.stderr


class HeldOpen(InodeBase):
    def test_a_different_file_given_the_freed_inode_number_is_not_deleted(self):
        out = self.drive(fake=True)
        self.assertIn("RC 1", out)
        self.assertIn("a different file was put there; it is left alone", out)
        self.assertEqual((self.v.root / FILE).read_text(), "Somebody else's file\n")
        self.assertFalse(self.filed())                                  # rolled back
        self.assertEqual(self.v.rows("actions"), [])

    def test_with_the_real_file_system_a_different_file_is_not_deleted(self):
        """No fake: the platform's own inode numbers (red without the fix on Linux ext4 and tmpfs; APFS passes either way)."""
        out = self.drive(fake=False)
        self.assertIn("RC 1", out)
        self.assertEqual((self.v.root / FILE).read_text(), "Somebody else's file\n")

    def test_the_held_descriptor_is_closed_on_a_refusal(self):
        self.assertIn("LEAKED 0", self.drive(fake=True))

    def test_the_held_descriptor_is_closed_when_the_staged_file_is_removed(self):
        self.decide("approved", "approved")
        code = DRIVER.replace("    p.unlink()\n    p.write_text(\"Somebody else's file\\n\")\n", "")
        r = subprocess.run([sys.executable, "-c", code % {"name": Path(FILE).name, "fake": False}], cwd=self.v.root,
                           capture_output=True, text=True, timeout=120)
        out = r.stdout + r.stderr
        self.assertIn("RC 0", out)
        self.assertIn("LEAKED 0", out)
        self.assertFalse(self.inbox())
        self.assertTrue(self.filed())


class DefectWithoutHold(InodeBase):
    """Always without the #261 diff: with Linux's reuse (faked), the different file is deleted and the apply succeeds."""
    HELD = False

    def test_a_different_file_given_the_freed_inode_number_is_deleted(self):
        out = self.drive(fake=True)
        self.assertIn("RC 0", out)
        self.assertFalse((self.v.root / FILE).exists())


if __name__ == "__main__":
    unittest.main()
