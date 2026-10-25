"""creaite 2.6.5's (also called 2.6.4b) hand checks that need no browser. Release string: the tooling accepts only X.Y.Z (update.py VERSION_RE, doctor.py,
the zip name, the tag and What's new's headings), so 2.6.4b ships as VERSION 2.6.5 and is called 2.6.4b in the notes and file names.
The page behaviour (Intake first screen, Next job, People Display menu, the calm save, the design fixes) is measured in Chrome by the
branches' own tests (test_intake_first_screen_340, test_next_job_356, test_people_display, test_calm_save_357,
test_design_fixes_343_browser) and in the gate; this file checks the release is cut and that each change is in the tree.

   1  version     VERSION is a version the tooling accepts and is 2.6.5 or later (2.6.6 contains 2.6.5)
   2  notes       What's new has the 2.6.5 section above 2.6.4, mentioning every issue of the scope; the plain notes and the sheet exist
   3  guides      both guides carry 2.6.5 and no 2.6.4 string
   4  guarded     no guarded file differs from the v2.6.4 release and the 2.6.4 chain list is unchanged (2.6.4b has no chain of its own)
   5  #340        Intake: the waiting tail, the five-row limit and Show all are in the source
   6  #356        Next job: the clear Intake offers a next job and the Week ahead offers tomorrow
   7  #357        a bulk save says "Saved N changes" with one Undo
   8  #359        the focused ask creaite input has no turning gradient
   9  #360        People has a Display menu built from the shared pieces, key D
  10  #343        Files names a file's type Word, Transcript or Excel
  11  #355        minutes_destination follows an update item's top-level source (test_355_followups, no browser)
  12  not in      #341 and #362 are not claimed in What's new as done
  13  leak fix    a confidential meeting's project counts only when chosen (test_confidential_persisted, test_confidential_paths, test_confidential_end_to_end), hand check 10 is on the sheet, and What's new says it in plain words

Run (from the repository root):  python3 dev/tests/handchecks/test_v265.py
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


def read(p):
    return (REPO / p).read_text(encoding="utf-8")


def tree(sub):
    return "\n".join(f.read_text(encoding="utf-8") for f in sorted((SRC / sub).rglob("*")) if f.suffix in (".js", ".jsx"))


def git(*a):
    return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True)

KIND = {n: "scriptable" for n in range(1, 13)}
LIVE_ONLY = {}


class V265(unittest.TestCase):
    def test_c01_version(self):
        v = read("VERSION").strip()
        self.assertRegex(v, r"^\d+\.\d+\.\d+$")
        self.assertGreaterEqual(tuple(map(int, v.split("."))), (2, 6, 5))  # 2.6.6 contains 2.6.5; test_v266 pins its own string

    def test_c02_notes(self):
        wn = read("system/templates/help/whats-new.md")
        heads = re.findall(r"^## creaite (\d+\.\d+\.\d+)\s*$", wn, re.M)
        self.assertEqual(heads[heads.index("2.6.5"):][:2], ["2.6.5", "2.6.4"])
        sec = wn.split("## creaite 2.6.4\n")[0].split("## creaite 2.6.5\n")[1]
        for n in ("340", "343", "355", "356", "357", "359", "360"):
            self.assertIn(f"(#{n})", sec, f"What's new does not mention #{n}")
        self.assertTrue((REPO / "dev/release-notes/2.6.5-plain.md").exists())
        self.assertTrue((REPO / "dev/handchecks/v2.6.5.md").exists())

    def test_c03_guides(self):
        for g in ("guide-first-day.html", "guide-how-to.html"):
            t = read(f"system/templates/{g}")
            self.assertRegex(t, r"creaite 2\.6\.[5-9] ·")   # 2.6.5 or a later 2.6 (test_v266 pins 2.6.6)
            self.assertNotIn("2.6.4", t)

    def test_c04_guarded_unchanged(self):
        if git("rev-parse", "-q", "--verify", "v2.6.4").returncode:
            self.skipTest("no v2.6.4 tag here")
        d = git("diff", "--name-only", "v2.6.4", "HEAD", "--", *GUARDED).stdout.split()
        self.assertEqual(d, [], f"guarded files changed since 2.6.4: {d}")
        old = [x for x in git("show", "v2.6.4:dev/proposals/GUARDED-2.6.4.chain").stdout.splitlines() if x and not x.startswith("#")]
        new = [x for x in read("dev/proposals/GUARDED-2.6.4.chain").splitlines() if x and not x.startswith("#")]
        self.assertEqual(old, new, "the 2.6.4 chain list changed")
        self.assertFalse((REPO / "dev/proposals/GUARDED-2.6.4b.chain").exists())

    def test_c05_340_intake_first(self):
        t = tree("components/intakeReview") + tree("core") + tree("stores")
        self.assertIn("Waiting for the transcript", t)
        self.assertRegex(t, r"IR_MAIL_LIMIT|mail and Teams shows its first five")
        self.assertIn("Show all", t)

    def test_c06_356_next_job(self):
        t = tree("components") + tree("stores") + tree("core")
        self.assertRegex(t, r"(?i)next job")
        self.assertRegex(read("system/templates/dashboard/src/components/today/WeekAhead.jsx"), r"(?i)tomorrow")

    def test_c07_357_calm_save(self):
        t = read("system/templates/dashboard/src/components/Toast.jsx") + read("system/templates/dashboard/src/panel.js")
        self.assertRegex(t, r"Saved \$\{\w+\} change")
        self.assertIn("Undo", t)

    def test_c08_359_ask_focus(self):
        css = read("system/templates/dashboard/style.css")
        self.assertRegex(css, r"(?s)#askIn[^{}]*:focus[^{}]*\{[^}]*border-color|ask[^{}]*:focus[^{}]*\{[^}]*border-color")

    def test_c09_360_people_display(self):
        for f in ("core/displayMenu.js", "core/peopleDisplay.js", "stores/peopleDisplay.js", "components/people/PeopleDisplay.js"):
            self.assertTrue((SRC / f).exists(), f)
        self.assertRegex(read("system/templates/dashboard/src/core/keys.js"), r"""['"]d['"]|\bKeyD\b|key\s*===\s*['"]d['"]""")

    def test_c10_343_files_type(self):
        t = read("system/templates/dashboard/src/files.js")
        for w in ("Word", "Transcript", "Excel"):
            self.assertIn(w, t)

    def test_c11_355_followups(self):
        r = subprocess.run([sys.executable, str(REPO / "dev/tests/test_355_followups.py")], cwd=REPO, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr[-1500:])

    def test_c12_not_in_scope(self):
        sec = read("system/templates/help/whats-new.md").split("## creaite 2.6.4\n")[0].split("## creaite 2.6.5\n")[-1]
        self.assertNotRegex(sec, r"\(#(341|362)\)")

    def test_c13_confidential_leak_fix(self):
        for t in ("test_confidential_persisted", "test_confidential_paths", "test_confidential_end_to_end"):
            r = subprocess.run([sys.executable, str(REPO / f"dev/tests/{t}.py")], cwd=REPO, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, t + "\n" + r.stderr[-1500:])
        self.assertRegex(read("dev/handchecks/v2.6.5.md"), r"(?m)^10\. \*\*A confidential meeting")
        for p in ("system/templates/help/whats-new.md", "dev/release-notes/2.6.5-plain.md"):
            self.assertIn("no longer land in a project folder you didn't choose", read(p))


if __name__ == "__main__":
    unittest.main()
