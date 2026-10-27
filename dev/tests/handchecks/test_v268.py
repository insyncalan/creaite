"""creaite 2.6.8's hand checks that need no browser. 2.6.8 contains 2.6.7. The invite scrub (#369) and the sent-line check (#368) are measured by
their own tests; this file checks the notes, the sheet, the guides and the version, and that no pending guarded item is claimed.

   1  notes     What's new has a 2.6.8 section above 2.6.7 naming #369 and #368; the plain notes and the sheet exist
   2  public    the public text names the over-removed titles and the limits; no real names, no GUARDED marker, no pending items claimed
   3  sheet     the sheet has ten checks and no 'Pending approvals' section (the guarded diffs are in the chain)
   4  tooling   dev/tools/whats_new.py finds the 2.6.8 section
   5  version   VERSION is 2.6.8 and both guides carry it

Run (from the repository root):  python3 dev/tests/handchecks/test_v268.py
"""
import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def read(p):
    return (REPO / p).read_text(encoding="utf-8")


def sec(t):
    return t.split("## creaite 2.6.8\n", 1)[1].split("## creaite 2.6.7\n", 1)[0]   # a later release's section above it is left out


def unguarded(t):
    return re.sub(r"<!--.*?-->", "", t, flags=re.S)


class V268(unittest.TestCase):
    def test_c01_notes(self):
        wn = read("system/templates/help/whats-new.md")
        heads = re.findall(r"^## creaite (\d+\.\d+\.\d+)\s*$", wn, re.M)
        self.assertEqual(heads[heads.index("2.6.8"):][:2], ["2.6.8", "2.6.7"])
        for n in ("#369", "#368"):
            self.assertIn(f"({n})", sec(wn))
        self.assertTrue((REPO / "dev/release-notes/2.6.8-plain.md").exists())
        self.assertTrue((REPO / "dev/handchecks/v2.6.8.md").exists())

    def test_c02_public_text(self):
        for p in ("system/templates/help/whats-new.md", "dev/release-notes/2.6.8-plain.md"):
            t = read(p)
            t = sec(t) if p.endswith("whats-new.md") else t
            self.assertEqual(t.count("<!--"), t.count("-->"))
            self.assertNotIn("GUARDED", t)
            for w in ("Pin the roadmap", "Secret Santa party", "the lines after them", "Meeting", "### Good to know", "look-alike"):
                self.assertIn(w, unguarded(t), f"{p} lacks {w!r}")
            self.assertNotRegex(unguarded(t), r"(?i)#358|amber|rescrub|client_leak")
        r = subprocess.run([sys.executable, str(REPO / "dev/tests/test_no_real_names.py")], cwd=REPO, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, (r.stderr or r.stdout)[-1500:])

    def test_c03_sheet(self):
        s = read("dev/handchecks/v2.6.8.md")
        self.assertEqual(len(re.findall(r"(?m)^\d+\. \*\*", s)), 10)
        self.assertNotIn("## Pending approvals", s)   # the guarded diffs are in the chain, nothing pends

    def test_c04_tooling(self):
        sys.path.insert(0, str(REPO / "dev/tools"))
        sys.path.insert(0, str(REPO / "system/scripts"))
        import whats_new
        self.assertTrue(whats_new.has("2.6.8"))

    def test_c05_version(self):
        self.assertGreaterEqual(tuple(map(int, read("VERSION").strip().split("."))), (2, 6, 8))   # 2.6.9 contains 2.6.8
        for g in ("guide-first-day.html", "guide-how-to.html"):
            t = read(f"system/templates/{g}")
            self.assertRegex(t, r"creaite 2\.6\.([89]|1\d) ·")   # 2.6.8 or later (test_v2610 pins 2.6.10)
            self.assertNotRegex(t, r"creaite 2\.6\.[0-7] ·")


if __name__ == "__main__":
    unittest.main()
