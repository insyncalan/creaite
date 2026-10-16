"""#116 F1 (17-10-2026): the guard's own wildcard expansion is bounded, and never holds back the checks that need none.

Run: python3 dev/tests/test_guard_glob_deadline.py     (quick tier: no Chrome)

The guard expands a wildcard to check what the shell (ask creaite) or a script (a run creaite starts itself) would find. Opening
some folders blocks in the kernel (macOS asks for consent before a program reads other apps' data under ~/Library), so
`minutes.py transcript '~/*/*/*/*/none.vtt'` held `ask_never_reason` and `held_never_reason` for minutes, past the hook's own
30 s timeout, and the checks that ran after the expansion (hand-over, validate, a held run's kind) never ran. Covers:
- a walk that blocks for 60 s is refused within the deadline, by the pure functions and by the guard's decision (`reach.decide`);
- a wildcard is never walked inside ~/Library (a fake home here), directly or through a symlink in the vault, nor outside the
  vault, the projects folder and the home folder: the walk is never started for those;
- a wildcard inside the vault still expands, and a match on the never list is still refused;
- the checks that need no expansion refuse before it starts: a record command, a `;`, a hand-over command, `tracker.py validate`
  with a wildcard, a held run's command that isn't a read.
No real folder outside the throwaway vault and fake home is ever listed: each test that could reach one replaces every walker
(the new one and the ones before it) with a recorder or a sleeper first.
"""
import glob
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_tracker import ABC, Vault  # noqa: E402

REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "system/scripts"))
import reach  # noqa: E402

T = "system/scripts/run minutes.py transcript"
SR = "system/scripts/run"
WALKERS = ("_glob_walk", "_ask_glob_dots")      # the shared walk, and ask mode's before #116 F1


class GlobCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        cls.v.run("init")
        cls.root = cls.v.root
        cls.home = Path(tempfile.mkdtemp(prefix="glob-deadline-home-")).resolve()
        (cls.home / ".ssh").mkdir()
        (cls.home / ".ssh/id_rsa").write_text("FAKE-PRIVATE-KEY-FOR-THE-TEST\n")
        gc = cls.home / "Library/Group Containers/app.example/data"
        gc.mkdir(parents=True)
        (gc / "none.vtt").write_text("WEBVTT\n")
        drafts = cls.root / "system/staging/drafts"
        drafts.mkdir(parents=True, exist_ok=True)
        os.symlink(cls.home / ".ssh", drafts / "keys")
        os.symlink(cls.home / "Library/Group Containers", drafts / "containers")
        (cls.root / ABC / "transcripts").mkdir(parents=True, exist_ok=True)
        (cls.root / ABC / "transcripts/2026-10-02 Weekly.vtt").write_text("WEBVTT\n")

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()
        shutil.rmtree(cls.home, ignore_errors=True)

    def setUp(self):
        self.saved = {"ROOT": reach.paths.ROOT, "HOME": os.environ.get("HOME"), "glob": glob.glob, "iglob": glob.iglob}
        self.saved.update({w: getattr(reach, w, None) for w in WALKERS})
        reach.paths.ROOT = self.root
        os.environ["HOME"] = str(self.home)

    def tearDown(self):
        reach.paths.ROOT = self.saved["ROOT"]
        os.environ["HOME"] = self.saved["HOME"]
        glob.glob, glob.iglob = self.saved["glob"], self.saved["iglob"]
        for w in WALKERS:
            if self.saved[w] is None:
                if hasattr(reach, w):
                    delattr(reach, w)
            else:
                setattr(reach, w, self.saved[w])

    def replace_walkers(self, fn):
        """Every walker the guard has used (the shared one, ask mode's, glob's) becomes fn; returns the list of calls."""
        calls = []

        def walker(*a, **k):
            calls.append(a[:1])
            return fn(*a, **k)
        for w in WALKERS:
            setattr(reach, w, walker)
        glob.glob = glob.iglob = walker
        return calls


class BlockingExpansion(GlobCase):
    def test_a_blocked_walk_is_refused_in_time(self):
        """A walk that blocks for 60 s (as an open under ~/Library/Group Containers did) is refused within the deadline."""
        self.replace_walkers(lambda *a, **k: (time.sleep(60), [])[1])
        cases = (("ask", reach.ask_never_reason, f"{T} '{ABC}/transcripts/*.vtt'"),
                 ("held", reach.held_never_reason, f"{T} '{ABC}/transcripts/*.vtt'"))
        for name, fn, cmd in cases:
            with self.subTest(check=name):
                start = time.monotonic()
                why = fn(cmd)
                self.assertLess(time.monotonic() - start, 10)
                self.assertIn("in time", why or "")

    def test_the_decision_is_refused_in_time(self):
        """The same through the guard's decision, as the hook calls it, in every mode."""
        self.replace_walkers(lambda *a, **k: (time.sleep(60), [])[1])
        for mode in ("ask", "confirmed", "sweep", "held", "prep"):
            with self.subTest(mode=mode):
                start = time.monotonic()
                ok, why = reach.decide("Bash", {"command": f"{T} '{ABC}/transcripts/*.vtt'"}, mode, "r-glob")
                self.assertLess(time.monotonic() - start, 10)
                self.assertFalse(ok)
                self.assertIn("in time", why)

    def test_the_deadline_is_short(self):
        self.assertLessEqual(reach.GLOB_SECONDS, 5)
        self.assertNotIn("reach-glob", [t.name for t in threading.enumerate() if not t.daemon])


class WhereAWildcardIsWalked(GlobCase):
    def test_outside_reach_is_never_walked(self):
        """A wildcard whose fixed part is outside the vault, the projects folder and the home folder is refused unwalked."""
        calls = self.replace_walkers(lambda *a, **k: [])
        for cmd in (f"{T} '/*/*/*/*/*/x.vtt'", f"{T} '/Users/*/Library/*/x.vtt'", f"{T} '../../*/x.vtt'"):
            for name, fn in (("ask", reach.ask_never_reason), ("held", reach.held_never_reason)):
                with self.subTest(cmd=cmd, check=name):
                    self.assertIn("outside the vault, the projects folder and your home folder", fn(cmd) or "")
            for mode in ("ask", "held"):
                with self.subTest(cmd=cmd, mode=mode):
                    self.assertFalse(reach.decide("Bash", {"command": cmd}, mode, "r-glob")[0])
        self.assertEqual(calls, [])

    def test_the_expansion_itself_refuses_outside_reach(self):
        """_bounded_expand checks each wildcard's fixed part before it starts a walk (a second lock behind the literal check)."""
        calls = self.replace_walkers(lambda *a, **k: [])
        for pattern in ("/*/*/x.vtt", "/Users/*/x.vtt", str(self.home / "Library/*/x.vtt")):
            with self.subTest(pattern=pattern):
                with self.assertRaises(reach.GlobRefused):
                    reach._bounded_expand([pattern])
        self.assertEqual(calls, [])

    def test_the_arguments_as_written_are_checked_before_the_walk(self):
        """A secret named outright is refused at once, even when a wildcard beside it would block."""
        self.replace_walkers(lambda *a, **k: (time.sleep(60), [])[1])
        cmd = f"{T} ~/.ssh/id_rsa '{ABC}/transcripts/*.vtt'"
        for name, fn in (("ask", reach.ask_never_reason), ("held", reach.held_never_reason)):
            with self.subTest(check=name):
                start = time.monotonic()
                self.assertIn("holds secrets", fn(cmd) or "")
                self.assertLess(time.monotonic() - start, 1)

    def test_library_is_never_walked(self):
        """In the (fake) home folder, a wildcard that would look inside ~/Library is refused before it lists anything there."""
        for cmd in (f"{T} '~/*/*/*/*/none.vtt'", f"{T} '~/Library/*/*/*/none.vtt'",
                    f"{T} 'system/staging/drafts/containers/*/*/none.vtt'"):
            for name, fn in (("ask", reach.ask_never_reason), ("held", reach.held_never_reason)):
                with self.subTest(cmd=cmd, check=name):
                    why = fn(cmd) or ""
                    self.assertTrue("~/Library" in why or "secrets" in why, why)

    def test_the_library_rule_on_its_own(self):
        self.assertIn("~/Library", reach._glob_root_reason(self.home / "Library/Group Containers"))
        self.assertIn("~/Library", reach._glob_root_reason(self.root / "system/staging/drafts/containers"))
        self.assertIsNone(reach._glob_root_reason(self.home / "Documents"))
        self.assertIsNone(reach._glob_root_reason(self.root / ABC))


class InsideTheVault(GlobCase):
    def test_a_wildcard_in_the_vault_still_expands(self):
        weekly = str(self.root / ABC / "transcripts/2026-10-02 Weekly.vtt")
        cmd = f"{T} '{ABC}/transcripts/2026-10-0? Weekly.vtt'"
        self.assertIn(weekly, reach.ask_arg_paths(cmd))
        self.assertIn(weekly, reach.held_arg_paths(cmd))
        self.assertIsNone(reach.ask_never_reason(cmd))
        self.assertIsNone(reach.held_never_reason(cmd))
        for mode in ("ask", "confirmed", "sweep", "held", "prep"):
            with self.subTest(mode=mode):
                self.assertEqual(reach.decide("Bash", {"command": cmd}, mode, "r-glob"), (True, ""))

    def test_a_match_on_the_never_list_is_still_refused(self):
        """Through a symlink in the vault to the (fake) ~/.ssh: the walk follows it and the match is refused."""
        cmd = f"{T} 'system/staging/drafts/ke?s/id_rsa'"
        for name, fn in (("ask", reach.ask_never_reason), ("held", reach.held_never_reason)):
            with self.subTest(check=name):
                self.assertIn("holds secrets", fn(cmd) or "")


class CheapChecksFirst(GlobCase):
    def test_no_expansion_before_the_cheap_refusals(self):
        calls = self.replace_walkers(lambda *a, **k: [])
        rows = [
            ("ask", f"{SR} tracker.py apply 'x/*.json'"),                        # the record gate
            ("ask", f"{T} 'x/*.vtt'; ls"),                                        # a shell character
            ("ask", f"{SR} reach.py wrap minutes.py transcript '~/*/x.vtt'"),     # a hand-over command
            ("ask", f"{SR} tracker.py validate 'system/staging/proposed-*.json'"),   # validate with a wildcard
            ("confirmed", f"{SR} reach.py wrap minutes.py transcript '~/*/x.vtt'"),
            ("held", f"{SR} tracker.py apply 'x/*.json'"),
            ("held", f"{SR} build_dashboard.py '{ABC}/*'"),                       # not a read command
            ("held", f"{SR} tracker.py validate 'system/staging/proposed-*.json'"),
            ("prep", f"{SR} search.py enrich '{ABC}/*.vtt'"),                     # derived, not a read command
        ]
        for mode, cmd in rows:
            with self.subTest(mode=mode, cmd=cmd):
                calls.clear()
                ok, why = reach.decide("Bash", {"command": cmd}, mode, "r-glob")
                self.assertFalse(ok, cmd)
                self.assertEqual(calls, [], f"{cmd!r} expanded before it was refused ({why})")


if __name__ == "__main__":
    unittest.main()
