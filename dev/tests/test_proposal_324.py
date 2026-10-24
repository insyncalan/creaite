"""The guarded proposal for #324, #326 and #332 (dev/proposals/324/live_server.diff) applies, forwards and back, to live_server.py as it
is now and with the 2.6.2 chain's live_server.py diffs applied first, in the chain's order (simulated on a throwaway copy of the file,
as dev/tests/guarded_chain.py simulates a chain commit; nothing in this tree is touched). It is skipped once the tree already has it
(the proposal has landed). It must not add a line over 140 characters, and it must touch only live_server.py.

Run: python3 dev/tests/test_proposal_324.py      (quick tier)
"""
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DIFF = REPO / "dev/proposals/324/live_server.diff"
LIVE = REPO / "system/scripts/live_server.py"
LANDED = "minutes_destination" in LIVE.read_text(encoding="utf-8")
CHAIN = REPO / "dev/proposals/GUARDED-2.6.2.chain"


def git(d, *a):
    return subprocess.run(["git", *a], cwd=d, capture_output=True, text=True)


class Proposal324(unittest.TestCase):
    def scratch(self, with_chain):
        d = Path(tempfile.mkdtemp(prefix="p324-"))
        self.addCleanup(shutil.rmtree, d, True)
        (d / "system/scripts").mkdir(parents=True)
        shutil.copy2(LIVE, d / "system/scripts/live_server.py")
        git(d, "init", "-q")
        if with_chain:
            for line in CHAIN.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "live_server" in line:
                    r = git(d, "apply", str(REPO / line))
                    self.assertEqual(r.returncode, 0, f"{line}: {r.stderr}")
        return d

    def test_only_live_server_and_short_lines(self):
        text = DIFF.read_text(encoding="utf-8")
        self.assertEqual(set(re.findall(r"^diff --git a/(\S+)", text, re.M)), {"system/scripts/live_server.py"})
        self.assertFalse([ln for ln in text.splitlines() if ln.startswith("+") and len(ln) > 141])

    @unittest.skipIf(LANDED, "the proposal has landed in this tree")
    def test_applies_forward_and_back_now_and_after_the_chain(self):
        for with_chain in (False, True):
            d = self.scratch(with_chain)
            f = d / "system/scripts/live_server.py"
            was = f.read_bytes()
            for args in (("apply", "--check"), ("apply",), ("apply", "-R", "--check"), ("apply", "-R")):
                r = git(d, *args, str(DIFF))
                self.assertEqual(r.returncode, 0, f"chain={with_chain} {args}: {r.stderr}")
            self.assertEqual(f.read_bytes(), was, "reversed: byte for byte as before")


if __name__ == "__main__":
    unittest.main()
