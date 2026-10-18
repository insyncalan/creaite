"""ask-hook-fix (15-10-2026): ask creaite's guard holds the never list for every form of a script argument, and never runs, part 2 of 3 (the fixture is in ask_bash_arg_forms_support.py).

Run: python3 dev/tests/test_ask_bash_arg_forms_held.py
"""
import shutil
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ask_bash_arg_forms_support import (  # noqa: E402
    HIDDEN,
    HookCase,
    MODES,
    T,
    shared_forms,
)


class HeldAndAskAgree(HookCase):
    def test_both_copies_refuse_the_shared_table(self):
        for name, cmd in shared_forms(self.root, self.home):
            for mode in ("held", "prep") + MODES:
                with self.subTest(form=name, mode=mode):
                    code, why = self.hook(mode, cmd)
                    self.assertEqual(code, 2, f"{mode}: {cmd!r}: {why}")
                    self.assertNotIn("FAKE-PRIVATE-KEY", why)


class HiddenWildcards(HookCase):
    def test_a_wildcard_reaching_a_hidden_folder_is_refused(self):
        self.refused_by(HIDDEN)

    def test_too_many_entries_is_refused(self):
        sys.path.insert(0, str(self.root / "system/scripts"))
        import reach
        many = self.root / "system/staging/drafts/many"
        many.mkdir(exist_ok=True)
        for i in range(reach.ASK_GLOB_LIMIT + 2):
            (many / f"{i}.vtt").write_text("")
        old = reach.paths.ROOT
        reach.paths.ROOT = self.root
        try:
            self.assertIn("too many files", reach.ask_never_reason(f"{T} system/staging/drafts/many/*.vtt") or "")
        finally:
            reach.paths.ROOT = old
            shutil.rmtree(many)


if __name__ == "__main__":
    unittest.main()
