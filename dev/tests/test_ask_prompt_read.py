"""BL-202: ask creaite's prompt tells it to look inside files with Read, Grep and Glob, never Bash, so a harmless lookup
isn't refused by the guard and shown to Alan as a warning. The line must not be dropped by a later edit."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
import live_server  # noqa: E402


class AskPromptReadsWithTools(unittest.TestCase):
    def test_the_prompt_names_read_grep_and_glob(self):
        p = live_server.ASK_PROMPT
        for tool in ("Read", "Grep", "Glob"):
            self.assertIn(tool, p)

    def test_the_prompt_forbids_bash_lookups(self):
        p = live_server.ASK_PROMPT
        self.assertIn("never Bash", p)
        for cmd in ("grep", "cat", "head", "tail", "sed", "awk"):
            self.assertIn(cmd, p)

    # ===== BL-252 (fix-search-read) =====
    def test_the_prompt_finds_items_with_search_not_grep(self):
        p = live_server.ASK_PROMPT
        self.assertIn("tracker.py read <table> --project CODE --search", p)
        self.assertIn("never grep the output", p)

    def test_the_prompt_retries_a_refused_read_without_asking(self):
        p = live_server.ASK_PROMPT
        self.assertIn("After a refused read-only command, retry it at once in the allowed form", p)
        self.assertIn("without asking Alan", p)
        self.assertIn("ask him only when the allowed form would change something", p)
    # ===== end BL-252 =====


if __name__ == "__main__":
    unittest.main()
