"""The guarded-file check's marker rule, on a throwaway git repo (never the live history).
(1) a marked commit with an extra guarded edit fails; (2) an unmarked guarded edit fails; (3) the exact chain, marked, passes;
(4) a marked commit with no chain file fails; plus: a marked commit touching a guarded file the chain doesn't list fails."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guarded_chain import CHAIN_FILE, CHAIN_MARKER, guarded_touched  # noqa: E402

TRK, UPD, REA = "system/scripts/tracker.py", "system/scripts/update.py", "system/scripts/reach.py"
DIFF_T, DIFF_U = "dev/proposals/x/tracker.diff", "dev/proposals/x/update.diff"


def run(d, *a, inp=None):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *a], cwd=d, check=True,
                          capture_output=True, text=True, input=inp).stdout


class Repo:
    def __init__(self):
        self._t = tempfile.TemporaryDirectory()
        self.d = Path(self._t.name)
        run(self.d, "init", "-q", "-b", "main")
        self.write(TRK, "a\nb\nc\n")
        self.write(UPD, "u1\nu2\n")
        self.write(REA, "r1\nr2\n")
        self.commit("base")
        run(self.d, "tag", "base")

    def write(self, f, text):
        (self.d / f).parent.mkdir(parents=True, exist_ok=True)
        (self.d / f).write_text(text)

    def commit(self, subject):
        run(self.d, "add", "-A")
        run(self.d, "commit", "-q", "-m", subject)

    def diff_of(self, f, text):
        """The diff that takes f to text, as the proposals are (a/ b/ paths), then f is put back."""
        old = (self.d / f).read_text()
        self.write(f, text)
        out = run(self.d, "diff", "--", f)
        self.write(f, old)
        return out

    def chain(self, with_file=True):
        dt, du = self.diff_of(TRK, "a\nB\nc\n"), self.diff_of(UPD, "u1\nU2\n")
        self.write(DIFF_T, dt)
        self.write(DIFF_U, du)
        if with_file:
            self.write(CHAIN_FILE, f"# chain\n{DIFF_T}\n{DIFF_U}\n")
        run(self.d, "apply", DIFF_T)
        run(self.d, "apply", DIFF_U)

    def touched(self):
        return guarded_touched(self.d, "base", "HEAD")


class GuardedChain(unittest.TestCase):
    def setUp(self):
        self.r = Repo()
        self.addCleanup(self.r._t.cleanup)

    def test_unmarked_guarded_edit_fails(self):
        self.r.write(TRK, "a\nb\nc\nd\n")
        self.r.commit("Word writer tweak")
        self.assertEqual(self.r.touched(), [TRK])

    def test_exact_chain_marked_passes(self):
        self.r.chain()
        self.r.commit(CHAIN_MARKER + " tracker and update")
        self.assertEqual(self.r.touched(), [])

    def test_chain_without_marker_fails(self):
        self.r.chain()
        self.r.commit("tracker and update")
        self.assertEqual(sorted(self.r.touched()), [TRK, UPD])

    def test_marked_commit_with_an_extra_guarded_edit_fails(self):
        self.r.chain()
        self.r.write(TRK, (self.r.d / TRK).read_text() + "extra\n")
        self.r.commit(CHAIN_MARKER + " tracker and update")
        self.assertIn(TRK, self.r.touched())

    def test_marked_commit_touching_an_unlisted_guarded_file_fails(self):
        self.r.chain()
        self.r.write(REA, "r1\nr2\nr3\n")
        self.r.commit(CHAIN_MARKER + " tracker and update")
        self.assertIn(REA, self.r.touched())

    def test_marked_commit_without_a_chain_file_fails(self):
        self.r.chain(with_file=False)
        self.r.commit(CHAIN_MARKER + " tracker and update")
        self.assertEqual(sorted(self.r.touched()), [TRK, UPD])

    def test_a_marked_commit_does_not_excuse_a_later_unmarked_one(self):
        self.r.chain()
        self.r.commit(CHAIN_MARKER + " tracker and update")
        self.r.write(UPD, "u1\nU2\nmore\n")
        self.r.commit("later")
        self.assertEqual(self.r.touched(), [UPD])

    def test_missing_base_gives_none(self):
        self.assertIsNone(guarded_touched(self.r.d, "origin/nope", "HEAD"))


if __name__ == "__main__":
    unittest.main()
