"""creaite 2.6.7's hand checks that need no browser. 2.6.7 contains 2.6.6. The page behaviour of #328 is measured in Chrome by the
branch's own tests and the gate; this file checks the notes and the sheet, and that nothing guarded is claimed before it lands.

   1  notes      What's new has a 2.6.7 section above 2.6.6 mentioning #328; the plain notes and the sheet exist
   2  public     the public text names Matched, Likely, Not sure, Process all ready and the skipped list; no real names
   3  l4         the "Remember <domain>" offer is marked L4 in a comment in the notes file, not in the What's new text
   4  guarded    #347 and #339 are only inside a GUARDED comment, in the notes file and in What's new; both comments are closed
   5  sheet      the sheet has the Process all ready, confidential, single-row, chip and L4 checks, and marks the GUARDED ones
   6  tooling    dev/tools/whats_new.py finds the 2.6.7 section
   7  version    VERSION is a version the tooling accepts (the bump to 2.6.7 is the cut's job, not this file's)

Run (from the repository root):  python3 dev/tests/handchecks/test_v267.py
"""
import re
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def read(p):
    return (REPO / p).read_text(encoding="utf-8")


def sec(text, v="2.6.7", nxt="2.6.6"):
    return text.split(f"## creaite {v}\n", 1)[1].split(f"## creaite {nxt}\n", 1)[0]


def unguarded(t):
    return re.sub(r"<!--.*?-->", "", t, flags=re.S)


class V267(unittest.TestCase):
    def test_c01_notes(self):
        wn = read("system/templates/help/whats-new.md")
        heads = re.findall(r"^## creaite (\d+\.\d+\.\d+)\s*$", wn, re.M)
        self.assertEqual(heads[:2], ["2.6.7", "2.6.6"])
        self.assertIn("(#328)", sec(wn))
        self.assertTrue((REPO / "dev/release-notes/2.6.7-plain.md").exists())
        self.assertTrue((REPO / "dev/handchecks/v2.6.7.md").exists())

    def test_c02_public_text(self):
        for p in ("system/templates/help/whats-new.md", "dev/release-notes/2.6.7-plain.md"):
            t = unguarded(read(p).split("## creaite 2.6.6\n")[0])
            for w in ("Matched", "Likely", "Not sure", "Process all ready", "never named"):
                self.assertIn(w, t, f"{p} lacks {w!r}")
            self.assertIn("### Good to know", t)
            self.assertIn("Waiting to be saved", t)          # the two small fixes (hand checks 10 and 13 of 2.6.4)
            self.assertIn("we may need 5", t)
            self.assertNotRegex(t, r"(?i)\bL4\b|sign-off")
        r = subprocess.run([sys.executable, str(REPO / "dev/tests/test_no_real_names.py")], cwd=REPO, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, (r.stderr or r.stdout)[-1500:])

    def test_c03_l4_comment(self):
        t = read("dev/release-notes/2.6.7-plain.md")
        self.assertRegex(t, r"<!-- L4, pending Alan's sign-off")
        self.assertNotIn("L4", read("system/templates/help/whats-new.md"))
        self.assertIn("Remember <domain> for <project>?", read("dev/release-notes/2.6.7-plain.md"))

    def test_c04_guarded_only_in_comment(self):
        for p in ("system/templates/help/whats-new.md", "dev/release-notes/2.6.7-plain.md"):
            t = read(p).split("## creaite 2.6.6\n")[0]
            self.assertEqual(t.count("<!--"), t.count("-->"), f"{p}: an unclosed comment")
            self.assertIn("<!-- GUARDED: only if the 2.6.7 chain lands", t)
            for w in ("check my mail", "undo last save", "refresh calendar", "(#347)", "(#339)"):
                self.assertNotIn(w, unguarded(t), f"{p}: {w!r} is outside the GUARDED comment")
                self.assertIn(w, t)

    def test_c05_sheet(self):
        s = read("dev/handchecks/v2.6.7.md")
        for w in ("Process all ready", "confidential", "Single-row Process", "chip", "L4", "GUARDED", "Remember <domain>"):
            self.assertIn(w, s)
        self.assertGreaterEqual(len(re.findall(r"(?m)^\d+\. \*\*", s)), 10)

    def test_c06_tooling(self):
        sys.path.insert(0, str(REPO / "dev/tools"))
        sys.path.insert(0, str(REPO / "system/scripts"))
        import whats_new
        self.assertTrue(whats_new.has("2.6.7"))

    def test_c07_version(self):
        self.assertRegex(read("VERSION").strip(), r"^\d+\.\d+\.\d+$")


if __name__ == "__main__":
    unittest.main()
