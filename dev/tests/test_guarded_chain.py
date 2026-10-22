"""The guarded-file check's marker rule, on a throwaway git repo (never the live history).
(1) a marked commit with an extra guarded edit fails; (2) an unmarked guarded edit fails; (3) the exact chain, marked, passes;
(4) a marked commit with no chain file fails; plus: a marked commit touching a guarded file the chain doesn't list fails."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guarded_chain  # noqa: E402
from guarded_chain import CHAIN_FILE, CHAIN_MARKER, HistoryMissing, chain_digest, guarded_touched  # noqa: E402

TRK, UPD, REA = "system/scripts/tracker.py", "system/scripts/update.py", "system/scripts/reach.py"
LIVE, LEAK, GOLD = "system/scripts/live_server.py", "system/scripts/client_leak.py", "dev/tests/snapshots/golden.txt"
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
        self.write(LIVE, "l1\nl2\nl3\nl4\nl5\nl6\nl7\nl8\nl9\n")
        self.write(LEAK, "k1\nk2\n")
        self.write(GOLD, "g1\ng2\n")
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
        """Commit the chain (diffs and list) as an ordinary earlier commit, then apply the diffs, uncommitted: the next commit is the chain commit."""
        dt, du = self.diff_of(TRK, "a\nB\nc\n"), self.diff_of(UPD, "u1\nU2\n")
        self.write(DIFF_T, dt)
        self.write(DIFF_U, du)
        if with_file:
            self.write(CHAIN_FILE, f"# chain\n{DIFF_T}\n{DIFF_U}\n")
        self.commit("add the chain files")
        self.pin = chain_digest(self.d, "HEAD")
        run(self.d, "apply", DIFF_T)
        run(self.d, "apply", DIFF_U)

    def multi_chain(self):
        """A bigger chain: three diffs to live_server.py (different places), one to tracker.py, one to a non-guarded golden file."""
        d = self.d
        steps = [(LIVE, "l1\nL2\nl3\nl4\nl5\nl6\nl7\nl8\nl9\n"), (TRK, "a\nB\nc\n"),
                 (LIVE, "l1\nL2\nl3\nl4\nl5\nl6\nl7\nl8\nL9\n"), (GOLD, "g1\nG2\n"),
                 (LIVE, "l1\nL2\nl3\nl4\nL5\nl6\nl7\nl8\nL9\n")]
        names = []
        for i, (f, text) in enumerate(steps):
            name = f"dev/proposals/x/d{i}.diff"
            self.write(name, self.diff_of(f, text))
            self.write(f, text)                        # later diffs build on earlier ones (staged, so each diff is one step)
            run(d, "add", f)
            names.append(name)
        run(d, "reset", "-q")
        for f in (LIVE, TRK, GOLD):
            run(d, "checkout", "--", f)
        self.write(CHAIN_FILE, "\n".join(names) + "\n")
        self.commit("add the chain files")
        self.pin = chain_digest(d, "HEAD")
        for n in names:
            run(d, "apply", n)

    pin = "none"

    def touched(self, **kw):
        kw.setdefault("pin", self.pin)
        return guarded_touched(self.d, "base", "HEAD", **kw)


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
        self.assertIn(UPD, self.r.touched())

    def test_an_unmarked_edit_that_is_reverted_nets_to_nothing(self):
        self.r.write(TRK, "a\nb\nc\nd\n")
        self.r.commit("tweak")
        self.r.write(TRK, "a\nb\nc\n")
        self.r.commit("put back")
        self.assertEqual(self.r.touched(), [])

    def test_multi_diff_chain_with_live_server_and_a_non_guarded_diff_passes(self):
        self.r.multi_chain()
        self.r.commit(CHAIN_MARKER + " many")
        self.assertEqual(self.r.touched(), [])

    def test_multi_chain_unmarked_fails(self):
        self.r.multi_chain()
        self.r.commit("many")
        self.assertEqual(sorted(self.r.touched()), [LIVE, TRK])

    def test_marked_commit_with_an_extra_live_server_edit_fails(self):
        self.r.multi_chain()
        self.r.write(LIVE, (self.r.d / LIVE).read_text() + "extra\n")
        self.r.commit(CHAIN_MARKER + " many")
        self.assertIn(LIVE, self.r.touched())

    def test_an_unmarked_live_server_edit_fails(self):
        self.r.write(LIVE, "l1\nl2\nl3\nl4\nl5\nl6\nl7\nl8\nl9\nl10\n")
        self.r.commit("tweak")
        self.assertEqual(self.r.touched(), [LIVE])

    def test_an_unmarked_client_leak_edit_fails(self):
        self.r.write(LEAK, "k1\nk2\nk3\n")
        self.r.commit("tweak")
        self.assertEqual(self.r.touched(), [LEAK])

    def test_a_golden_only_change_is_not_guarded(self):
        self.r.write(GOLD, "g1\nother\n")
        self.r.commit("golden")
        self.assertEqual(self.r.touched(), [])

    def test_forgery_a_a_marked_commit_adds_its_own_diff_and_lists_it(self):
        self.r.chain()
        self.r.write(REA, "r1\nr2\nevil\n")
        evil = self.r.diff_of(REA, "r1\nr2\nevil\n")
        run(self.r.d, "checkout", "--", REA)
        self.r.write(REA, "r1\nr2\nevil\n")
        self.r.write("dev/proposals/x/evil.diff", evil)
        self.r.write(CHAIN_FILE, f"{DIFF_T}\n{DIFF_U}\ndev/proposals/x/evil.diff\n")
        self.r.commit(CHAIN_MARKER + " tracker and update")
        self.assertIn(REA, self.r.touched())
        self.assertIn(REA, self.r.touched(pin=chain_digest(self.r.d, "HEAD")))      # not even with the new list's own digest

    def test_forgery_b_an_empty_marked_commit_adds_the_diff_for_an_earlier_edit(self):
        self.r.write(TRK, "a\nB\nc\n")
        self.r.commit("sneaky unmarked edit")
        self.r.write(DIFF_T, subprocess.run(["git", "diff", "base", "HEAD", "--", TRK], cwd=self.r.d, capture_output=True, text=True).stdout)
        self.r.write(CHAIN_FILE, f"{DIFF_T}\n")
        self.r.commit(CHAIN_MARKER + " nothing guarded in here")
        self.assertEqual(self.r.touched(pin=chain_digest(self.r.d, "HEAD")), [TRK])

    def test_forgery_c_the_chain_is_there_and_the_edit_made_earlier_unmarked(self):
        self.r.chain()                                  # chain files committed, diffs applied in the work tree
        self.r.commit("the chain's edits, unmarked")
        run(self.r.d, "commit", "-q", "--allow-empty", "-m", CHAIN_MARKER + " empty")
        self.assertEqual(sorted(self.r.touched()), [TRK, UPD])

    def test_a_chain_that_does_not_match_the_pin_fails(self):
        self.r.chain()
        self.r.commit(CHAIN_MARKER + " tracker and update")
        self.assertEqual(sorted(self.r.touched(pin="0" * 64)), [TRK, UPD])

    def test_missing_base_gives_none_outside_ci(self):
        self.assertIsNone(guarded_touched(self.r.d, "origin/nope", "HEAD", ci=""))

    def test_missing_base_fails_in_ci(self):
        with self.assertRaises(HistoryMissing):
            guarded_touched(self.r.d, "origin/nope", "HEAD", ci="true")

    def test_the_live_pin_matches_the_live_chain_files(self):
        repo = Path(__file__).resolve().parents[2]
        self.assertEqual(chain_digest(repo, "HEAD"), guarded_chain.CHAIN_SHA256,
                         "the chain list or a listed diff changed: update CHAIN_SHA256 only with Alan's say (python3 dev/tests/guarded_chain.py)")


if __name__ == "__main__":
    unittest.main()
