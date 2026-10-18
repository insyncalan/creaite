"""#132 round 1, G1c (proposal, not applied): the never list in the runs creaite starts itself (guard modes "prep" and "held").

Run: python3 dev/tests/test_ai_proposal_g1c_held_never.py

Found while checking G1: ask creaite's hook refuses the never list (secrets, the operating system) first, but a Prep page run and
the other runs creaite starts itself (Current state, AI drafts, Shape, a transcript check or load: mode "held") go through
reach.prep_decision, which checks only confidential notes and Bash's form. So the hook lets such a run read ~/.ssh, the keychain
file or /etc, and hand a creaite script a secret's path; the pinned decisions record it (test_guard_pinned). The keychain's file
is encrypted, so reading it gives no key, but the never list exists so that these places are never read at all.

g1c-never-list-held-runs.diff is applied to a throwaway vault (ai_proposal_support). Done when, in modes prep and held:
- every never place is refused (a Read, a search folder with one below it, a creaite script given one), as for ask creaite;
- ordinary reads in the vault are still let through, and a confidential note is still refused for its own reason.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ai_proposal_support as S  # noqa: E402
from test_tracker import ABC  # noqa: E402


class HeldModes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = S.vault("g1c-never-list-held-runs")
        cls.home = S.fake_home()
        notes = cls.root / ABC / "notes"
        notes.mkdir(parents=True, exist_ok=True)
        (notes / "Closed.md").write_text("---\ntitle: Closed\nconfidential: true\n---\n\nKept back.\n")
        (notes / "Open.md").write_text("---\ntitle: Open\nconfidential: false\n---\n\nOrdinary.\n")

    def decide(self, calls):
        return S.run_py(self.root, r'''
import reach
out = {}
for mode in ("prep", "held"):
    for tool, inp in json.loads(%r):
        out[f"{mode} | {tool} | {json.dumps(inp)}"] = list(reach.decide(tool, inp, mode, ""))
print(json.dumps(out))''' % json.dumps(calls), env={"HOME": str(self.home)})

    def test_never_places_are_refused(self):
        h = str(self.home)
        out = self.decide([["Read", {"file_path": f"{h}/Library/Keychains/login.keychain-db"}],
                           ["Read", {"file_path": f"{h}/.ssh/id_rsa"}], ["Read", {"file_path": "/etc/hosts"}],
                           ["Grep", {"pattern": "x", "path": f"{h}/Library"}], ["Glob", {"pattern": "**/*", "path": h}],
                           ["LS", {"path": h}], ["Glob", {"pattern": f"{h}/.ssh/*"}],
                           ["Bash", {"command": f"system/scripts/run search.py preview {h}/Library/Keychains/login.keychain-db"}],
                           ["Bash", {"command": f"python3 system/scripts/docx_tools.py text {h}/.ssh/id_rsa"}]])
        self.assertEqual(len(out), 18)
        for k, (ok, why) in out.items():
            self.assertFalse(ok, k)
            self.assertTrue("secrets" in why or "operating system" in why or "never read" in why, f"{k}: {why}")

    def test_ordinary_reads_still_pass_and_a_confidential_note_keeps_its_reason(self):
        out = self.decide([["Read", {"file_path": f"{ABC}/CLAUDE.md"}], ["Grep", {"pattern": "x", "path": f"{ABC}/minutes"}],
                           ["Read", {"file_path": f"{ABC}/notes/Open.md"}], ["Read", {"file_path": f"{ABC}/notes/Closed.md"}],
                           ["Bash", {"command": "system/scripts/run tracker.py read ABC"}]])
        for mode in ("prep", "held"):
            self.assertEqual(out[f'{mode} | Read | {{"file_path": "{ABC}/CLAUDE.md"}}'], [True, ""])
            self.assertEqual(out[f'{mode} | Grep | {{"pattern": "x", "path": "{ABC}/minutes"}}'], [True, ""])
            self.assertEqual(out[f'{mode} | Read | {{"file_path": "{ABC}/notes/Open.md"}}'], [True, ""])
            self.assertEqual(out[f'{mode} | Bash | {{"command": "system/scripts/run tracker.py read ABC"}}'], [True, ""])
            closed = out[f'{mode} | Read | {{"file_path": "{ABC}/notes/Closed.md"}}']
            self.assertFalse(closed[0])
            self.assertIn("confidential", closed[1])


if __name__ == "__main__":
    unittest.main()
