"""The guarded-file check's marker rule, on a throwaway git repo (never the live history).
(1) a marked commit with an extra guarded edit fails; (2) an unmarked guarded edit fails; (3) the exact chain, marked, passes;
(4) a marked commit with no chain file fails; plus: a marked commit touching a guarded file the chain doesn't list fails.
Every case runs for the 2.6.1, the 2.6.2, the 2.6.3 and the 2.6.4 chain (own marker, chain file and pin); a group mixes 2.6.1 with 2.6.2, and one 2.6.2 with 2.6.3.
2.6.3 put system/scripts/draft_delivery.py on the guarded list: its cases are at the end."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guarded_chain  # noqa: E402
from guarded_chain import GUARDED, HistoryMissing, SPEC1, SPEC2, SPEC3, SPEC4, SPEC5, SPEC6, SPEC7, SPEC8, SPEC9, SPEC10, chain_digest, guarded_touched  # noqa: E402

TRK, UPD, REA = "system/scripts/tracker.py", "system/scripts/update.py", "system/scripts/reach.py"
LIVE, LEAK, EDIT, GOLD = "system/scripts/live_server.py", "system/scripts/client_leak.py", "system/scripts/edit_ai.py", "dev/tests/snapshots/golden.txt"
DRAFT = "system/scripts/draft_delivery.py"
DIFF_T, DIFF_U = "dev/proposals/x/tracker.diff", "dev/proposals/x/update.diff"


def run(d, *a, inp=None):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *a], cwd=d, check=True,
                          capture_output=True, text=True, input=inp).stdout


class Repo:
    def __init__(self, spec=SPEC1):
        self.spec = spec
        self.marker, self.cfile = spec[0], spec[1]
        self._t = tempfile.TemporaryDirectory()
        self.d = Path(self._t.name)
        run(self.d, "init", "-q", "-b", "main")
        self.write(TRK, "a\nb\nc\n")
        self.write(UPD, "u1\nu2\n")
        self.write(REA, "r1\nr2\n")
        self.write(LIVE, "l1\nl2\nl3\nl4\nl5\nl6\nl7\nl8\nl9\n")
        self.write(LEAK, "k1\nk2\n")
        self.write(EDIT, "e1\ne2\n")
        self.write(DRAFT, "d1\nd2\nd3\n")
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
            self.write(self.cfile, f"# chain\n{DIFF_T}\n{DIFF_U}\n")
        self.commit("add the chain files")
        self.pin = chain_digest(self.d, "HEAD", self.spec)
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
        self.write(self.cfile, "\n".join(names) + "\n")
        self.commit("add the chain files")
        self.pin = chain_digest(d, "HEAD", self.spec)
        for n in names:
            run(d, "apply", n)

    pin = "none"

    def touched(self, **kw):
        key = {SPEC1[0]: "pin", SPEC2[0]: "pin2", SPEC3[0]: "pin3", SPEC4[0]: "pin4", SPEC5[0]: "pin5", SPEC6[0]: "pin6", SPEC7[0]: "pin7", SPEC8[0]: "pin8",
               SPEC9[0]: "pin9", SPEC10[0]: "pin10"}[self.spec[0]]
        if "pin" in kw and key != "pin":
            kw[key] = kw.pop("pin")
        kw.setdefault(key, self.pin)
        return guarded_touched(self.d, "base", "HEAD", **kw)


class GuardedChain(unittest.TestCase):
    SPEC = SPEC1

    def setUp(self):
        self.r = Repo(self.SPEC)
        self.M = self.SPEC[0]
        self.addCleanup(self.r._t.cleanup)

    def test_unmarked_guarded_edit_fails(self):
        self.r.write(TRK, "a\nb\nc\nd\n")
        self.r.commit("Word writer tweak")
        self.assertEqual(self.r.touched(), [TRK])

    def test_exact_chain_marked_passes(self):
        self.r.chain()
        self.r.commit(self.M + " tracker and update")
        self.assertEqual(self.r.touched(), [])

    def test_chain_without_marker_fails(self):
        self.r.chain()
        self.r.commit("tracker and update")
        self.assertEqual(sorted(self.r.touched()), [TRK, UPD])

    def test_marked_commit_with_an_extra_guarded_edit_fails(self):
        self.r.chain()
        self.r.write(TRK, (self.r.d / TRK).read_text() + "extra\n")
        self.r.commit(self.M + " tracker and update")
        self.assertIn(TRK, self.r.touched())

    def test_marked_commit_touching_an_unlisted_guarded_file_fails(self):
        self.r.chain()
        self.r.write(REA, "r1\nr2\nr3\n")
        self.r.commit(self.M + " tracker and update")
        self.assertIn(REA, self.r.touched())

    def test_marked_commit_without_a_chain_file_fails(self):
        self.r.chain(with_file=False)
        self.r.commit(self.M + " tracker and update")
        self.assertEqual(sorted(self.r.touched()), [TRK, UPD])

    def test_a_marked_commit_does_not_excuse_a_later_unmarked_one(self):
        self.r.chain()
        self.r.commit(self.M + " tracker and update")
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
        self.r.commit(self.M + " many")
        self.assertEqual(self.r.touched(), [])

    def test_multi_chain_unmarked_fails(self):
        self.r.multi_chain()
        self.r.commit("many")
        self.assertEqual(sorted(self.r.touched()), [LIVE, TRK])

    def test_marked_commit_with_an_extra_live_server_edit_fails(self):
        self.r.multi_chain()
        self.r.write(LIVE, (self.r.d / LIVE).read_text() + "extra\n")
        self.r.commit(self.M + " many")
        self.assertIn(LIVE, self.r.touched())

    def test_an_unmarked_live_server_edit_fails(self):
        self.r.write(LIVE, "l1\nl2\nl3\nl4\nl5\nl6\nl7\nl8\nl9\nl10\n")
        self.r.commit("tweak")
        self.assertEqual(self.r.touched(), [LIVE])

    def test_an_unmarked_client_leak_edit_fails(self):
        self.r.write(LEAK, "k1\nk2\nk3\n")
        self.r.commit("tweak")
        self.assertEqual(self.r.touched(), [LEAK])

    def test_an_unmarked_edit_ai_edit_fails(self):
        self.r.write(EDIT, "e1\ne2\ne3\n")
        self.r.commit("tweak")
        self.assertEqual(self.r.touched(), [EDIT])

    def test_marked_commit_with_an_extra_edit_ai_edit_fails(self):
        self.r.chain()
        self.r.write(EDIT, "e1\ne2\ne3\n")
        self.r.commit(self.M + " tracker and update")
        self.assertIn(EDIT, self.r.touched())

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
        self.r.write(self.r.cfile, f"{DIFF_T}\n{DIFF_U}\ndev/proposals/x/evil.diff\n")
        self.r.commit(self.M + " tracker and update")
        self.assertIn(REA, self.r.touched())
        self.assertIn(REA, self.r.touched(pin=chain_digest(self.r.d, "HEAD", self.SPEC)))      # not even with the new list's own digest

    def test_forgery_b_an_empty_marked_commit_adds_the_diff_for_an_earlier_edit(self):
        self.r.write(TRK, "a\nB\nc\n")
        self.r.commit("sneaky unmarked edit")
        self.r.write(DIFF_T, subprocess.run(["git", "diff", "base", "HEAD", "--", TRK], cwd=self.r.d, capture_output=True, text=True).stdout)
        self.r.write(self.r.cfile, f"{DIFF_T}\n")
        self.r.commit(self.M + " nothing guarded in here")
        self.assertEqual(self.r.touched(pin=chain_digest(self.r.d, "HEAD", self.SPEC)), [TRK])

    def test_forgery_c_the_chain_is_there_and_the_edit_made_earlier_unmarked(self):
        self.r.chain()                                  # chain files committed, diffs applied in the work tree
        self.r.commit("the chain's edits, unmarked")
        run(self.r.d, "commit", "-q", "--allow-empty", "-m", self.M + " empty")
        self.assertEqual(sorted(self.r.touched()), [TRK, UPD])

    def test_a_chain_that_does_not_match_the_pin_fails(self):
        self.r.chain()
        self.r.commit(self.M + " tracker and update")
        self.assertEqual(sorted(self.r.touched(pin="0" * 64)), [TRK, UPD])

    def test_missing_base_gives_none_outside_ci(self):
        self.assertIsNone(guarded_touched(self.r.d, "origin/nope", "HEAD", ci=""))

    def test_missing_base_fails_in_ci(self):
        with self.assertRaises(HistoryMissing):
            guarded_touched(self.r.d, "origin/nope", "HEAD", ci="true")

    def test_the_live_pin_matches_the_live_chain_files(self):
        repo = Path(__file__).resolve().parents[2]
        name = self.SPEC[2]
        if chain_digest(repo, "HEAD", self.SPEC) is None and not getattr(guarded_chain, name):
            self.skipTest("this tree carries no chain list and no pin for it")
        self.assertEqual(chain_digest(repo, "HEAD", self.SPEC), getattr(guarded_chain, name),
                         f"the chain list or a listed diff changed: update {name} only with Alan's say (python3 dev/tests/guarded_chain.py)")



class GuardedChain2(GuardedChain):
    """The same cases for the 2.6.2 chain: its own marker, chain file and pin."""
    SPEC = SPEC2


class GuardedChain3(GuardedChain):
    """The same cases for the 2.6.3 chain: its own marker, chain file and pin."""
    SPEC = SPEC3


class GuardedChain4(GuardedChain):
    """The same cases for the 2.6.4 chain: its own marker, chain file and pin."""
    SPEC = SPEC4


class GuardedChain5(GuardedChain):
    """The same cases for the 2.6.7 chain: its own marker, chain file and pin."""
    SPEC = SPEC5


class GuardedChain6(GuardedChain):
    """The same cases for the 2.6.8 chain: its own marker, chain file and pin."""
    SPEC = SPEC6


class GuardedChain7(GuardedChain):
    """The same cases for the 2.6.9 chain: its own marker, chain file and pin."""
    SPEC = SPEC7


class GuardedChain8(GuardedChain):
    """The same cases for the second 2.6.9 chain (bundle rev 5): its own marker, chain file and pin."""
    SPEC = SPEC8


class ShippedPin8(unittest.TestCase):
    def test_the_shipped_pin_is_the_listed_chain(self):
        repo = Path(__file__).resolve().parents[2]
        listed = chain_digest(repo, "HEAD", SPEC8)
        self.assertIsNotNone(listed, "the 2.6.9b list is missing or empty")
        self.assertEqual(listed, guarded_chain.CHAIN8_SHA256)

    def test_the_markers_do_not_prefix_each_other(self):
        self.assertFalse(SPEC8[0].startswith(SPEC7[0]))
        self.assertFalse(SPEC7[0].startswith(SPEC8[0]))


class Chains7And8(unittest.TestCase):
    """A range holding the first 2.6.9 chain commit and then the bundle rev 5 commit, both on update.py (rev 5 builds on rev 4)."""

    def setUp(self):
        self.r = Repo(SPEC7)
        self.addCleanup(self.r._t.cleanup)

    def build(self, mark8=True, extra=False):
        r = self.r
        r.chain()                                       # chain 7: tracker.py a/B/c, update.py u1/U2
        pin7 = r.pin
        r.commit(SPEC7[0] + " tracker and update")
        r.write("dev/proposals/z/update.diff", r.diff_of(UPD, "u1\nU2\nu3\n"))
        r.write(SPEC8[1], "dev/proposals/z/update.diff\n")
        r.commit("add the 2.6.9b chain files")
        pin8 = chain_digest(r.d, "HEAD", SPEC8)
        run(r.d, "apply", "dev/proposals/z/update.diff")
        if extra:
            r.write(UPD, (r.d / UPD).read_text() + "extra\n")
        r.commit(SPEC8[0] + " update" if mark8 else "update")
        return pin7, pin8

    def test_both_marked_pass(self):
        p7, p8 = self.build()
        self.assertEqual(guarded_touched(self.r.d, "base", "HEAD", pin7=p7, pin8=p8), [])

    def test_the_second_unmarked_fails(self):
        p7, p8 = self.build(mark8=False)
        self.assertIn(UPD, guarded_touched(self.r.d, "base", "HEAD", pin7=p7, pin8=p8))

    def test_the_second_with_an_extra_edit_fails(self):
        p7, p8 = self.build(extra=True)
        self.assertIn(UPD, guarded_touched(self.r.d, "base", "HEAD", pin7=p7, pin8=p8))

    def test_a_wrong_second_pin_fails(self):
        p7, _ = self.build()
        self.assertIn(UPD, guarded_touched(self.r.d, "base", "HEAD", pin7=p7, pin8="0" * 64))

    def test_base_after_the_first_checks_the_second_alone(self):
        _, p8 = self.build()
        first = run(self.r.d, "log", "--format=%H", "--fixed-strings", "--grep", SPEC7[0]).strip()
        self.assertEqual(guarded_touched(self.r.d, first, "HEAD", pin8=p8), [])


class GuardedChain9(GuardedChain):
    """The same cases for the 2.6.10 chain: its own marker, chain file and pin."""
    SPEC = SPEC9


class ShippedPin9(unittest.TestCase):
    def test_the_shipped_pin_is_the_listed_chain(self):
        repo = Path(__file__).resolve().parents[2]
        listed = chain_digest(repo, "HEAD", SPEC9)
        self.assertIsNotNone(listed, "the 2.6.10 list is missing or empty")
        self.assertEqual(listed, guarded_chain.CHAIN9_SHA256)

    def test_no_marker_prefixes_another(self):
        """The 2.6.10 marker, the two 2.6.9 markers and a possible second 2.6.10 chain's marker: none starts with another."""
        marks = [SPEC7[0], SPEC8[0], SPEC9[0], "Guarded 2.6.10 chain (370 slice 3):"]
        for a in marks:
            for b in marks:
                if a != b:
                    self.assertFalse(a.startswith(b), (a, b))

    def test_base9_is_the_first_2610_base(self):
        self.assertEqual(guarded_chain.BASE9, "026528d9bdd64ee0039096a5425c7e3500db6106")


class Chains8And9(unittest.TestCase):
    """A range holding the 2.6.9b chain commit on update.py and then the 2.6.10 chain commit on reach.py."""

    def setUp(self):
        self.r = Repo(SPEC8)
        self.addCleanup(self.r._t.cleanup)

    def build(self, mark9=True, extra=False):
        r = self.r
        r.chain()                                       # chain 8: tracker.py a/B/c, update.py u1/U2
        pin8 = r.pin
        r.commit(SPEC8[0] + " tracker and update")
        r.write("dev/proposals/z/reach.diff", r.diff_of(REA, "r1\nR2\n"))
        r.write(SPEC9[1], "dev/proposals/z/reach.diff\n")
        r.commit("add the 2.6.10 chain files")
        pin9 = chain_digest(r.d, "HEAD", SPEC9)
        run(r.d, "apply", "dev/proposals/z/reach.diff")
        if extra:
            r.write(REA, (r.d / REA).read_text() + "extra\n")
        r.commit(SPEC9[0] + " reach" if mark9 else "reach")
        return pin8, pin9

    def test_both_marked_pass(self):
        p8, p9 = self.build()
        self.assertEqual(guarded_touched(self.r.d, "base", "HEAD", pin8=p8, pin9=p9), [])

    def test_the_second_unmarked_fails(self):
        p8, p9 = self.build(mark9=False)
        self.assertIn(REA, guarded_touched(self.r.d, "base", "HEAD", pin8=p8, pin9=p9))

    def test_the_second_with_an_extra_edit_fails(self):
        p8, p9 = self.build(extra=True)
        self.assertIn(REA, guarded_touched(self.r.d, "base", "HEAD", pin8=p8, pin9=p9))

    def test_a_wrong_2610_pin_fails(self):
        p8, _ = self.build()
        self.assertIn(REA, guarded_touched(self.r.d, "base", "HEAD", pin8=p8, pin9="0" * 64))

    def test_base_after_the_first_checks_the_second_alone(self):
        _, p9 = self.build()
        first = run(self.r.d, "log", "--format=%H", "--fixed-strings", "--grep", SPEC8[0]).strip()
        self.assertEqual(guarded_touched(self.r.d, first, "HEAD", pin9=p9), [])


class GuardedChain10(GuardedChain):
    """The same cases for the second 2.6.10 chain (#370 slice 3): its own marker, chain file and pin."""
    SPEC = SPEC10


class ShippedPin10(unittest.TestCase):
    def test_the_shipped_pin_is_the_listed_chain(self):
        repo = Path(__file__).resolve().parents[2]
        listed = chain_digest(repo, "HEAD", SPEC10)
        self.assertIsNotNone(listed, "the second 2.6.10 list is missing or empty")
        self.assertEqual(listed, guarded_chain.CHAIN10_SHA256)

    def test_no_marker_prefixes_another(self):
        """The two 2.6.9 markers and the two 2.6.10 markers: none starts with another."""
        marks = [SPEC7[0], SPEC8[0], SPEC9[0], SPEC10[0]]
        self.assertEqual(SPEC10[0], "Guarded 2.6.10 chain (370 slice 3):")
        for a in marks:
            for b in marks:
                if a != b:
                    self.assertFalse(a.startswith(b), (a, b))

    def test_the_first_2610_marker_does_not_find_the_second_commit(self):
        """Discovery is subject.startswith(marker): the 370 commit is the second chain's only, never the first's."""
        subj = "Guarded 2.6.10 chain (370 slice 3): the run limits and refusal count, live_server.py only (rev 2)"
        self.assertTrue(subj.startswith(SPEC10[0]))
        self.assertFalse(any(subj.startswith(s[0]) for s in (SPEC1, SPEC2, SPEC3, SPEC4, SPEC5, SPEC6, SPEC7, SPEC8, SPEC9)))

    def test_base_is_the_second_2610_base(self):
        self.assertEqual(guarded_chain.BASE, guarded_chain.BASE10)


class Chains9And10(unittest.TestCase):
    """A range holding the 2.6.10 chain commit on live_server.py and then the second 2.6.10 chain commit on the same file, as shipped."""

    def setUp(self):
        self.r = Repo(SPEC9)
        self.addCleanup(self.r._t.cleanup)

    def build(self, mark10=True, extra=False):
        r = self.r
        r.write("dev/proposals/y/live1.diff", r.diff_of(LIVE, "l1\nL2\nl3\nl4\nl5\nl6\nl7\nl8\nl9\n"))
        r.write(SPEC9[1], "dev/proposals/y/live1.diff\n")
        r.commit("add the 2.6.10 chain files")
        pin9 = chain_digest(r.d, "HEAD", SPEC9)
        run(r.d, "apply", "dev/proposals/y/live1.diff")
        r.commit(SPEC9[0] + " live_server")
        r.write("dev/proposals/z/live2.diff", r.diff_of(LIVE, "l1\nL2\nl3\nl4\nl5\nl6\nl7\nL8\nl9\n"))
        r.write(SPEC10[1], "dev/proposals/z/live2.diff\n")
        r.commit("add the second 2.6.10 chain files")
        pin10 = chain_digest(r.d, "HEAD", SPEC10)
        run(r.d, "apply", "dev/proposals/z/live2.diff")
        if extra:
            r.write(LIVE, (r.d / LIVE).read_text() + "extra\n")
        r.commit(SPEC10[0] + " live_server" if mark10 else "live_server")
        return pin9, pin10

    def test_both_marked_pass(self):
        p9, p10 = self.build()
        self.assertEqual(guarded_touched(self.r.d, "base", "HEAD", pin9=p9, pin10=p10), [])

    def test_the_second_unmarked_fails(self):
        p9, p10 = self.build(mark10=False)
        self.assertIn(LIVE, guarded_touched(self.r.d, "base", "HEAD", pin9=p9, pin10=p10))

    def test_the_second_with_an_extra_edit_fails(self):
        p9, p10 = self.build(extra=True)
        self.assertIn(LIVE, guarded_touched(self.r.d, "base", "HEAD", pin9=p9, pin10=p10))

    def test_a_wrong_second_pin_fails(self):
        p9, _ = self.build()
        self.assertIn(LIVE, guarded_touched(self.r.d, "base", "HEAD", pin9=p9, pin10="0" * 64))

    def test_a_wrong_first_pin_fails(self):
        _, p10 = self.build()
        self.assertIn(LIVE, guarded_touched(self.r.d, "base", "HEAD", pin9="0" * 64, pin10=p10))

    def test_base_after_the_first_checks_the_second_alone(self):
        _, p10 = self.build()
        first = run(self.r.d, "log", "--format=%H", "--fixed-strings", "--grep", SPEC9[0] + " live_server").strip()
        self.assertEqual(guarded_touched(self.r.d, first, "HEAD", pin10=p10), [])


class ShippedRange2610(unittest.TestCase):
    """The real 2.6.10 range: from the 2.6.9 release (tag v2.6.9, db5adb2a) and from BASE9 both 2.6.10 chains, from BASE10 (the default
    BASE) the second alone; every guarded change is a marked, pinned 2.6.10 chain."""

    def test_the_release_range_passes(self):
        repo = Path(__file__).resolve().parents[2]
        for base in ("db5adb2ac15f1787ec4f9b4aa89399af59e68afc", guarded_chain.BASE9, guarded_chain.BASE10):
            got = guarded_touched(repo, base, "HEAD", ci="")
            if got is None:
                self.skipTest("git history for the 2.6.10 range is not available")
            self.assertEqual(got, [], base)

    def test_the_default_range_passes(self):
        got = guarded_touched(Path(__file__).resolve().parents[2], ci="")
        if got is None:
            self.skipTest("git history for the 2.6.10 range is not available")
        self.assertEqual(got, [])


class ShippedRange269(unittest.TestCase):
    """The real 2.6.9 range: from the 2.6.8 release (BASE7) and from BASE8, every guarded change is a marked, pinned chain."""

    def test_the_release_range_passes(self):
        repo = Path(__file__).resolve().parents[2]
        for base in (guarded_chain.BASE7, guarded_chain.BASE8):
            got = guarded_touched(repo, base, "HEAD", ci="")
            if got is None:
                self.skipTest("git history for the 2.6.9 range is not available")
            self.assertEqual(got, [], base)


class ShippedPin7(unittest.TestCase):
    def test_the_shipped_pin_is_the_listed_chain(self):
        repo = Path(__file__).resolve().parents[2]
        listed = chain_digest(repo, "HEAD", SPEC7)
        self.assertIsNotNone(listed, "the 2.6.9 list is missing or empty")
        self.assertEqual(listed, guarded_chain.CHAIN7_SHA256)


class ShippedPin6(unittest.TestCase):
    def test_the_shipped_pin_is_the_listed_chain(self):
        repo = Path(__file__).resolve().parents[2]
        listed = chain_digest(repo, "HEAD", SPEC6)
        self.assertIsNotNone(listed, "the 2.6.8 list is missing or empty")
        self.assertEqual(listed, guarded_chain.CHAIN6_SHA256)


class ShippedPin5(unittest.TestCase):
    def test_the_shipped_pin_is_the_listed_chain(self):
        repo = Path(__file__).resolve().parents[2]
        listed = chain_digest(repo, "HEAD", SPEC5)
        self.assertIsNotNone(listed, "the 2.6.7 list is missing or empty")
        self.assertEqual(listed, guarded_chain.CHAIN5_SHA256)


class EmptyChain4(unittest.TestCase):
    """2.6.4 starts with an empty chain list and no pin: it must fail closed, never pass a marked commit."""

    def test_the_empty_list_has_no_digest(self):
        r = Repo(SPEC4)
        self.addCleanup(r._t.cleanup)
        r.write(SPEC4[1], "# nothing yet\n")
        r.commit("an empty list")
        self.assertIsNone(chain_digest(r.d, "HEAD", SPEC4))

    def test_a_marked_commit_fails_closed_with_an_empty_list_and_pin(self):
        r = Repo(SPEC4)
        self.addCleanup(r._t.cleanup)
        r.write(SPEC4[1], "# nothing yet\n")
        r.commit("an empty list")
        r.write(TRK, "a\nB\nc\n")
        r.commit(SPEC4[0] + " tracker")
        self.assertEqual(guarded_touched(r.d, "base", "HEAD"), [TRK])
        self.assertEqual(guarded_touched(r.d, "base", "HEAD", pin4=""), [TRK])

    def test_the_shipped_pin_is_empty_until_the_list_is_cut(self):
        repo = Path(__file__).resolve().parents[2]
        listed = chain_digest(repo, "HEAD", SPEC4)
        if listed is None:
            self.assertEqual(guarded_chain.CHAIN4_SHA256, "", "a pin is set but the 2.6.4 list is empty or missing")
        else:
            self.assertEqual(listed, guarded_chain.CHAIN4_SHA256)


class BothChains(unittest.TestCase):
    """A range holding the 2.6.1 chain commit and then the 2.6.2 chain commit (2.6.2 touches tracker.py again and reach.py)."""
    def setUp(self):
        self.r = Repo(SPEC1)
        self.addCleanup(self.r._t.cleanup)

    def build(self, mark2=True, unmarked_first=False):
        r = self.r
        r.chain()                                       # chain 1: tracker.py a/B/c, update.py u1/U2
        pin1 = r.pin
        if unmarked_first:
            r.commit("the 2.6.1 chain's edits, unmarked")
        else:
            r.commit(SPEC1[0] + " tracker and update")
        d2t = r.diff_of(TRK, "a\nB\nc\nd\n")         # chain 2 builds on chain 1's tracker.py
        d2r = r.diff_of(REA, "r1\nr2\nr3\n")
        r.write("dev/proposals/y/tracker.diff", d2t)
        r.write("dev/proposals/y/reach.diff", d2r)
        r.write(SPEC2[1], "dev/proposals/y/tracker.diff\ndev/proposals/y/reach.diff\n")
        r.commit("add the 2.6.2 chain files")
        r.pin2 = chain_digest(r.d, "HEAD", SPEC2)
        run(r.d, "apply", "dev/proposals/y/tracker.diff")
        run(r.d, "apply", "dev/proposals/y/reach.diff")
        return pin1

    def touched(self, pin1):
        return guarded_touched(self.r.d, "base", "HEAD", pin=pin1, pin2=self.r.pin2)

    def test_both_chains_marked_pass(self):
        p1 = self.build()
        self.r.commit(SPEC2[0] + " tracker and reach")
        self.assertEqual(self.touched(p1), [])

    def test_second_chain_unmarked_fails(self):
        p1 = self.build()
        self.r.commit("tracker and reach")
        self.assertIn(REA, self.touched(p1))

    def test_second_chain_with_an_extra_edit_fails(self):
        p1 = self.build()
        self.r.write(LIVE, (self.r.d / LIVE).read_text() + "extra\n")
        self.r.commit(SPEC2[0] + " tracker and reach")
        self.assertIn(LIVE, self.touched(p1))

    def test_first_chain_edits_unmarked_then_a_marked_second_chain_fails(self):
        p1 = self.build(unmarked_first=True)
        self.r.commit(SPEC2[0] + " tracker and reach")
        self.assertIn(UPD, self.touched(p1))

    def test_a_later_unmarked_edit_after_both_fails(self):
        p1 = self.build()
        self.r.commit(SPEC2[0] + " tracker and reach")
        self.r.write(TRK, (self.r.d / TRK).read_text() + "later\n")
        self.r.commit("later")
        self.assertIn(TRK, self.touched(p1))

    def test_base_after_the_first_chain_checks_the_second_alone(self):
        p1 = self.build()
        self.r.commit(SPEC2[0] + " tracker and reach")
        first = run(self.r.d, "log", "--format=%H", "--grep", SPEC1[0]).strip()
        self.assertEqual(guarded_touched(self.r.d, first, "HEAD", pin2=self.r.pin2), [])


DRAFT_DIFF = "dev/proposals/x/draft.diff"


class DraftDelivery(unittest.TestCase):
    """2.6.3: draft_delivery.py (the Outlook draft hook) is guarded. A plain edit fails; an edit inside the marked chain commit passes."""
    SPEC = SPEC3

    def setUp(self):
        self.r = Repo(self.SPEC)
        self.addCleanup(self.r._t.cleanup)

    def anchor_chain(self):
        r = self.r
        r.write(DRAFT_DIFF, r.diff_of(DRAFT, "d1\nd2 guarded\nd3\n"))
        r.write(r.cfile, DRAFT_DIFF + "\n")
        r.commit("add the chain files")
        r.pin = chain_digest(r.d, "HEAD", self.SPEC)
        run(r.d, "apply", DRAFT_DIFF)

    def touched(self):
        return guarded_touched(self.r.d, "base", "HEAD", pin3=self.r.pin)

    def test_it_is_on_the_guarded_list(self):
        self.assertIn("draft_delivery.py", GUARDED)

    def test_a_plain_edit_fails(self):
        self.r.write(DRAFT, "d1\nd2\nd3\nd4\n")
        self.r.commit("tweak the hook")
        self.assertEqual(guarded_touched(self.r.d, "base", "HEAD"), [DRAFT])

    def test_a_new_file_added_outside_a_chain_fails(self):
        run(self.r.d, "rm", "-q", DRAFT)
        self.r.commit("remove it")
        self.assertEqual(guarded_touched(self.r.d, "base", "HEAD"), [DRAFT])

    def test_the_edit_inside_the_marked_chain_commit_passes(self):
        self.anchor_chain()
        self.r.commit(SPEC3[0] + " draft_delivery anchor")
        self.assertEqual(self.touched(), [])

    def test_the_same_edit_unmarked_fails(self):
        self.anchor_chain()
        self.r.commit("draft_delivery anchor")
        self.assertEqual(self.touched(), [DRAFT])

    def test_an_extra_edit_in_the_marked_commit_fails(self):
        self.anchor_chain()
        self.r.write(DRAFT, (self.r.d / DRAFT).read_text() + "sneaky\n")
        self.r.commit(SPEC3[0] + " draft_delivery anchor")
        self.assertEqual(self.touched(), [DRAFT])

    def test_a_later_plain_edit_after_the_chain_fails(self):
        self.anchor_chain()
        self.r.commit(SPEC3[0] + " draft_delivery anchor")
        self.r.write(DRAFT, (self.r.d / DRAFT).read_text() + "later\n")
        self.r.commit("later")
        self.assertEqual(self.touched(), [DRAFT])

    def test_the_2_6_2_marker_does_not_excuse_it(self):
        self.anchor_chain()
        self.r.commit(SPEC2[0] + " draft_delivery anchor")
        self.assertEqual(guarded_touched(self.r.d, "base", "HEAD", pin2=self.r.pin), [DRAFT])

    def test_an_empty_pin_fails_closed(self):
        self.anchor_chain()
        self.r.commit(SPEC3[0] + " draft_delivery anchor")
        self.assertEqual(guarded_touched(self.r.d, "base", "HEAD"), [DRAFT])


class Chains2And3(unittest.TestCase):
    """A range holding the 2.6.2 chain commit and then the 2.6.3 chain commit (tracker.py in 2.6.2, draft_delivery.py in 2.6.3)."""

    def setUp(self):
        self.r = Repo(SPEC2)
        self.addCleanup(self.r._t.cleanup)

    def build(self, mark3=True):
        r = self.r
        r.chain()
        pin2 = r.pin
        r.commit(SPEC2[0] + " tracker and update")
        r.write(DRAFT_DIFF, r.diff_of(DRAFT, "d1\nd2 guarded\nd3\n"))
        r.write(SPEC3[1], DRAFT_DIFF + "\n")
        r.commit("add the 2.6.3 chain files")
        pin3 = chain_digest(r.d, "HEAD", SPEC3)
        run(r.d, "apply", DRAFT_DIFF)
        r.commit(SPEC3[0] + " draft_delivery" if mark3 else "draft_delivery")
        return pin2, pin3

    def test_both_marked_pass(self):
        p2, p3 = self.build()
        self.assertEqual(guarded_touched(self.r.d, "base", "HEAD", pin2=p2, pin3=p3), [])

    def test_the_third_unmarked_fails(self):
        p2, p3 = self.build(mark3=False)
        self.assertIn(DRAFT, guarded_touched(self.r.d, "base", "HEAD", pin2=p2, pin3=p3))     # an unexplained net change reports them all

    def test_base_after_the_second_checks_the_third_alone(self):
        p2, p3 = self.build()
        second = run(self.r.d, "log", "--format=%H", "--grep", SPEC2[0]).strip()
        self.assertEqual(guarded_touched(self.r.d, second, "HEAD", pin3=p3), [])


if __name__ == "__main__":
    unittest.main()
