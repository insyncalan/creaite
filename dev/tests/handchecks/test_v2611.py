"""creaite 2.6.11's hand checks that need no browser (sheet dev/handchecks/v2.6.11.md). 2.6.11 holds one change, #389 (a meeting
processed from a file leaves Intake's Arrived list), in ordinary code only (build_dashboard.py, minutes.py). No guarded file changes
and there is no guarded chain. All data is fictional; no browser, no network, no Claude.

The sheet holds only judgement and live-only checks (numbers 1 to 4, tagged below). The tests are numbered from 11 and cover the
rest.

  11  version    VERSION is 2.6.11
  12  notes      What's new has the 2.6.11 section above 2.6.10 naming #389; plain notes and sheet exist
  13  public     the notes carry no GUARDED marker or real names; whats_new.py finds the section
  14  guides     both guides carry 2.6.11 and no earlier 2.6 string; the first-day guide names the 2.6.11 zip
  15  guarded    no guarded file differs from the 2.6.10 release (tag v2.6.10, else main 6dc121ae)
  16  pins       guarded_chain.py and test_guarded_chain.py are as in 2.6.10, and test_guarded_chain passes
  20  #389       test_intake_processed_389 passes
  21  #389       minutes.by_others_keys exists and build_dashboard reads it (someone else's minutes never link, #232 E1)
  22  unchanged  the sibling Intake and calendar tests pass (one process at a time)
  25  claims     the 2.6.11 notes name #389 and no other item

Run (from the repository root):  python3 dev/tests/handchecks/test_v2611.py
"""
import re
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "system" / "scripts"))
sys.path.insert(0, str(REPO / "dev" / "tools"))

GUARDED = ["system/creaite-rules.md", "system/scripts/tracker.py", "system/scripts/filechange.py", "system/scripts/reach.py",
           "system/scripts/permissions.py", "system/scripts/backup.py", "system/scripts/update.py", "system/scripts/live_server.py",
           "system/scripts/client_leak.py", "system/scripts/edit_ai.py", "system/scripts/draft_delivery.py",
           "system/scripts/schema.sql", ".claude/settings.json", ".claude/settings.local.json"]
SCRIPTABLE = (11, 12, 13, 14, 15, 16, 20, 21, 22, 25)
KIND = {**{n: "scriptable" for n in SCRIPTABLE}, 1: "live-only", 2: "judgement", 3: "live-only", 4: "live-only"}
LIVE_ONLY = {
    1: "with Alan: drop in a transcript for a calendar meeting and process it; Intake shows one row (Drafted, then Done) in Chrome",
    2: "with Alan: two meetings with the same day and title; both stay as they were; does Intake read plainly (wording)",
    3: "with Alan: someone else's minutes for the meeting waiting in Review; the calendar row is not linked",
    4: "with Alan: Process from a meeting's own row, Not needed, and Review behave as in 2.6.10",
}
RELEASE_2610 = "6dc121aeb"   # main after the 2.6.10 merge (PR #51)
SIBLINGS = ("test_intake_review_model", "test_intake_process", "test_intake_process_minutes", "test_intake_process_round2",
            "test_calendar_refresh", "test_calendar_readers_golden")


def read(p):
    return (REPO / p).read_text(encoding="utf-8")


def git(*a):
    return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True)


def run_test(rel, *names):
    return subprocess.run([sys.executable, str(REPO / rel), *names], cwd=REPO, capture_output=True, text=True)


def baseline_ref():
    """The 2.6.10 release: the tag v2.6.10, else main's 2.6.10 merge; None when neither is here."""
    for ref in ("refs/tags/v2.6.10", RELEASE_2610):
        if git("rev-parse", "-q", "--verify", ref + "^{commit}").returncode == 0:
            return ref
    return None


def wn_section():
    wn = read("system/templates/help/whats-new.md")
    if "## creaite 2.6.11\n" not in wn:
        return None
    return wn.split("## creaite 2.6.11\n", 1)[1].split("## creaite 2.6.10\n", 1)[0]


def plain_notes():
    p = REPO / "dev/release-notes/2.6.11-plain.md"
    return p.read_text(encoding="utf-8") if p.exists() else None


class V2611(unittest.TestCase):
    def run_all(self, *files):
        """Each test file in turn (one process at a time); a missing file is a failure (it pins the behaviour)."""
        for f in files:
            rel = f"dev/tests/{f}.py"
            with self.subTest(f):
                self.assertTrue((REPO / rel).exists(), f"{rel} is missing")
                r = run_test(rel)
                self.assertEqual(r.returncode, 0, f"{rel} failed:\n" + (r.stderr or r.stdout)[-1500:])

    # ---- the release shape --------------------------------------------------------------------------------------------------
    def test_c11_version(self):
        self.assertEqual(read("VERSION").strip(), "2.6.11")

    def test_c12_notes(self):
        wn = read("system/templates/help/whats-new.md")
        heads = re.findall(r"^## creaite (\d+\.\d+\.\d+)\s*$", wn, re.M)
        self.assertEqual(heads[:2], ["2.6.11", "2.6.10"])
        self.assertIn("(#389)", wn_section())
        self.assertIn("### Intake", wn_section())
        self.assertIsNotNone(plain_notes(), "dev/release-notes/2.6.11-plain.md is missing")
        sheet = read("dev/handchecks/v2.6.11.md")
        self.assertGreaterEqual(len(re.findall(r"(?m)^\d+\. \*\*", sheet)), 4)
        self.assertIn("Not in 2.6.11", sheet)

    def test_c13_public_text(self):
        for t in (wn_section(), plain_notes()):
            self.assertEqual(t.count("<!--"), t.count("-->"))
            self.assertNotIn("GUARDED", t)
            self.assertNotRegex(t, r"(?m)^\W*ask creaite", "a line never starts with ask creaite")
        import whats_new
        self.assertTrue(whats_new.has("2.6.11"))
        r = run_test("dev/tests/test_no_real_names.py")
        self.assertEqual(r.returncode, 0, (r.stderr or r.stdout)[-1500:])

    def test_c14_guides(self):
        for g in ("guide-first-day.html", "guide-how-to.html"):
            t = read(f"system/templates/{g}")
            self.assertIn("creaite 2.6.11 ·", t)
            self.assertNotRegex(t, r"creaite 2\.6\.(\d|10) ·")
            self.assertNotRegex(t, r"creaite-2\.6\.(\d|10)\.zip")
        self.assertIn("creaite-2.6.11.zip", read("system/templates/guide-first-day.html"))

    # ---- guarded files and pins ---------------------------------------------------------------------------------------------
    def test_c15_guarded_equal_2610(self):
        ref = baseline_ref()
        if ref is None:
            self.skipTest("neither the tag v2.6.10 nor main's 2.6.10 merge (6dc121ae) is here")
        d = git("diff", "--name-only", ref, "--", *GUARDED).stdout.split()
        self.assertEqual(d, [], f"guarded files differ from 2.6.10: {d} (2.6.11 has no guarded chain)")

    def test_c16_pins_unchanged(self):
        ref = baseline_ref()
        if ref is None:
            self.skipTest("neither the tag v2.6.10 nor main's 2.6.10 merge (6dc121ae) is here")
        d = git("diff", "--name-only", ref, "--", "dev/tests/guarded_chain.py", "dev/tests/test_guarded_chain.py").stdout.split()
        self.assertEqual(d, [], f"the chain pins changed since 2.6.10: {d}")
        self.run_all("test_guarded_chain")

    # ---- #389 -----------------------------------------------------------------------------------------------------------------
    def test_c20_processed_from_a_file(self):
        self.run_all("test_intake_processed_389")

    def test_c21_others_never_link(self):
        import minutes
        self.assertTrue(callable(getattr(minutes, "by_others_keys", None)), "minutes.by_others_keys is missing (#232 E1)")
        self.assertIn("minutes.by_others_keys()", read("system/scripts/build_dashboard.py"))

    def test_c22_siblings(self):
        self.run_all(*SIBLINGS)

    def test_c25_notes_claim_only_389(self):
        for name, t in (("What's new 2.6.11", wn_section()), ("2.6.11-plain.md", plain_notes())):
            with self.subTest(name):
                self.assertEqual(sorted(set(re.findall(r"\(#(\d+)\)", t))), ["389"], f"{name} names an item other than #389")


if __name__ == "__main__":
    unittest.main()
