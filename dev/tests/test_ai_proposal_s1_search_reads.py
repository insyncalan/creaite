"""#132 round 2, S1 (proposal, not applied): Search's answer may not read the never list's secrets and system folders.

Run: python3 dev/tests/test_ai_proposal_s1_search_reads.py

Round 1 (all but G1c) and all of round 2 are applied to a throwaway vault. Search's answer has no guard hook (#60, by design) and
is allowed Read, Grep and Glob, so nothing but Claude Code's own scoping stopped it reading ~/.ssh or the keychain's file. S1
adds the never list's read-barred places to its deny list as Read rules. Nothing else in any launch changes.

Done when:
- Search's deny list holds Read(<place>) and Read(<place>/**) for every never-list entry barred to reading (secrets below the
  home folder as ~/…, the operating system as //…), and nothing for the vault's own entries (those bar writing only);
- its allowed tools, its --tools and every other kind's lists are unchanged.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ai_proposal_support as S  # noqa: E402

LISTS = r'''
import live_server as L, reach
print(json.dumps({"denies": L.KIND_DENIES, "tools": L.KIND_TOOLS, "args": L.KIND_ARGS,
                  "search": L.run_policy("search", None), "never": [list(n[:3]) for n in reach.NEVER]}))'''


class SearchReads(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.after = S.run_py(S.vault2("s1-search-never-reads"), LISTS)
        cls.before = S.run_py(S.vault2("g10-fake-switch-and-tested-key"), LISTS)

    def test_the_never_reads_are_denied(self):
        deny = self.after["denies"]["search"]
        for want in ("Read(~/.ssh)", "Read(~/.ssh/**)", "Read(~/Library/Keychains/**)", "Read(~/.aws/**)",
                     "Read(~/.claude/.credentials.json)", "Read(//etc/**)", "Read(//System/**)", "Read(//Library/**)",
                     "Read(~/Library/Application Support/Google/Chrome/**)"):
            self.assertIn(want, deny)
        read_all = [n for n in self.after["never"] if n[2] == "all"]
        self.assertEqual(len([d for d in deny if d.startswith("Read(")]), 2 * len(read_all))
        self.assertFalse(any("system/" in d or "tracker.db" in d for d in deny if d.startswith("Read(")),
                         "the vault's own entries bar writing only: Search still reads the vault")

    def test_nothing_else_moves(self):
        added = [d for d in self.after["denies"]["search"] if d not in self.before["denies"]["search"]]
        self.assertEqual(self.after["denies"]["search"], self.before["denies"]["search"] + added)
        self.assertTrue(all(d.startswith("Read(") for d in added))
        for k in self.before["denies"]:
            if k != "search":
                self.assertEqual(self.after["denies"][k], self.before["denies"][k], k)
        self.assertEqual(self.after["tools"], self.before["tools"])
        self.assertEqual(self.after["args"], self.before["args"])
        self.assertEqual(self.after["search"][0], self.before["search"][0], "the allowed tools: Read, Grep, Glob")
        self.assertEqual(self.after["search"][0], ["Read", "Grep", "Glob"])


if __name__ == "__main__":
    unittest.main()
