"""creaite 2.6.6's hand checks that need no browser. 2.6.6 contains 2.6.5 (2.6.4b). The page behaviour of #341 and #358 is measured in
Chrome by the branches' own tests and the gate; this file checks the release is cut and that each change is in the tree.

   1  version     VERSION is 2.6.6, a version the tooling accepts
   2  notes       What's new has the 2.6.6 section above 2.6.5, mentioning #341, #358 and #362; the plain notes and the sheet exist
   3  guides      both guides carry 2.6.6 and no earlier 2.6 string
   4  guarded     no guarded file differs from the v2.6.4 release
   5  #341        the structure checks (no browser) pass
   6  #341        plain titles "Open risks and issues", "Progress over time", "Late milestones" are in the source
   7  #358        the mail check says "Looked in so far" and ends with a Found count, in the source
   8  #358        the mail check's own tests that need no browser pass
   9  #362        a title code beats a remembered series (test_title_code_wins)
  10  not in      amber (#341 item 17) is not claimed in What's new
  11  conf header  a confidential meeting's Prep header asks you to choose the project (test_confidential_persisted Header), the sheet has hand check 12 with "Not in 2.6.6" kept, and the notes' Good to know says it

Run (from the repository root):  python3 dev/tests/handchecks/test_v266.py
"""
import re
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SRC = REPO / "system/templates/dashboard/src"
GUARDED = ["system/creaite-rules.md", "system/scripts/tracker.py", "system/scripts/filechange.py", "system/scripts/reach.py",
           "system/scripts/permissions.py", "system/scripts/backup.py", "system/scripts/update.py", "system/scripts/live_server.py",
           "system/scripts/client_leak.py", "system/scripts/edit_ai.py", "system/scripts/draft_delivery.py", ".claude/settings.json"]
KIND = {n: "scriptable" for n in range(1, 12)}
LIVE_ONLY = {}


def read(p):
    return (REPO / p).read_text(encoding="utf-8")


def git(*a):
    return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True)


def run_test(rel, *names):
    return subprocess.run([sys.executable, str(REPO / rel), *names], cwd=REPO, capture_output=True, text=True)


class V266(unittest.TestCase):
    def test_c01_version(self):
        v = read("VERSION").strip()
        self.assertRegex(v, r"^\d+\.\d+\.\d+$")
        self.assertEqual(v, "2.6.6")

    def test_c02_notes(self):
        wn = read("system/templates/help/whats-new.md")
        heads = re.findall(r"^## creaite (\d+\.\d+\.\d+)\s*$", wn, re.M)
        self.assertEqual(heads[:2], ["2.6.6", "2.6.5"])
        sec = wn.split("## creaite 2.6.5\n")[0]
        for n in ("341", "358", "362"):
            self.assertIn(f"(#{n})", sec, f"What's new does not mention #{n}")
        self.assertTrue((REPO / "dev/release-notes/2.6.6-plain.md").exists())
        self.assertTrue((REPO / "dev/handchecks/v2.6.6.md").exists())

    def test_c03_guides(self):
        for g in ("guide-first-day.html", "guide-how-to.html"):
            t = read(f"system/templates/{g}")
            self.assertIn("creaite 2.6.6 ·", t)
            self.assertNotRegex(t, r"creaite 2\.6\.[0-5] ·")

    def test_c04_guarded_unchanged(self):
        if git("rev-parse", "-q", "--verify", "v2.6.4").returncode:
            self.skipTest("no v2.6.4 tag here")
        d = git("diff", "--name-only", "v2.6.4", "HEAD", "--", *GUARDED).stdout.split()
        self.assertEqual(d, [], f"guarded files changed since 2.6.4: {d}")

    def test_c05_341_structure(self):
        r = run_test("dev/tests/test_v265_341_structure.py")
        self.assertEqual(r.returncode, 0, r.stderr[-1500:])

    def test_c06_341_titles(self):
        t = "\n".join(f.read_text(encoding="utf-8") for f in sorted(SRC.rglob("*")) if f.suffix in (".js", ".jsx"))
        for w in ("Open risks and issues", "Progress over time", "Late milestones"):
            self.assertIn(w, t)

    def test_c07_358_wording(self):
        t = read("system/templates/dashboard/src/core/mailCheck.js")
        self.assertIn("Looked in so far", t)
        self.assertRegex(t, r"Found ")

    def test_c08_358_tests(self):
        r = run_test("dev/tests/test_mail_check.py", "Classifier", "CloseDayRows", "Pin", "LeakGate")   # the classes that start no browser
        self.assertEqual(r.returncode, 0, (r.stderr or r.stdout)[-1500:])

    def test_c09_362_title_code_wins(self):
        r = run_test("dev/tests/test_title_code_wins.py")
        self.assertEqual(r.returncode, 0, r.stderr[-1500:])

    def test_c10_not_in_scope(self):
        sec = read("system/templates/help/whats-new.md").split("## creaite 2.6.5\n")[0]
        self.assertNotRegex(sec, r"(?i)\bamber\b[^.]*\(#341\)")

    def test_c11_confidential_header(self):
        r = run_test("dev/tests/test_confidential_persisted.py", "Header")
        self.assertEqual(r.returncode, 0, (r.stderr or r.stdout)[-1500:])
        sheet = read("dev/handchecks/v2.6.6.md")
        self.assertRegex(sheet, r"(?m)^12\. \*\*A confidential meeting's Prep")
        for p in ("system/templates/help/whats-new.md", "dev/release-notes/2.6.6-plain.md"):
            sec = read(p).split("## creaite 2.6.5\n")[0]
            self.assertIn("### Good to know", sec)
            self.assertIn("For a confidential meeting you choose the project yourself", sec)
            self.assertNotIn("keeps its earlier wording", sec)


if __name__ == "__main__":
    unittest.main()
