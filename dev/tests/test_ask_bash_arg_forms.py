"""ask-hook-fix (15-10-2026): ask creaite's guard holds the never list for every form of a script argument, and never runs, part 1 of 3 (the fixture is in ask_bash_arg_forms_support.py).

Run: python3 dev/tests/test_ask_bash_arg_forms.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ask_bash_arg_forms_support import (  # noqa: E402
    HookCase,
    MODES,
    NEVER,
    OVER_REFUSED,
    P,
    by,
    forms,
    handovers,
    lookalikes,
    WORDS,
)


class AskArgForms(HookCase):
    def test_every_form_is_refused(self):
        self.refused_by(forms(self.root, self.home))

    def test_the_two_reported_forms(self):
        """The two forms reported against ask mode: the wildcard one is refused as a pattern outside quotes (#174 F5, before the
        never list looks), the other with the secret named in the reason."""
        for mode in MODES:
            code, why = self.hook(mode, f"{P} ~/.ss?/id_rsa")
            self.assertEqual((code, by(why)), (2, WORDS), why)
        for cmd in (f"{P} --file=~/.ssh/id_rsa",):
            for mode in MODES:
                with self.subTest(cmd=cmd, mode=mode):
                    code, why = self.hook(mode, cmd)
                    self.assertEqual(code, 2, why)
                    self.assertIn("/.ssh", why)
                    self.assertIn("it holds secrets (keys, passwords, sign-ins)", why)

    def test_legitimate_lookalikes_pass(self):
        for cmd in lookalikes(self.root):
            for mode in MODES:
                with self.subTest(cmd=cmd, mode=mode):
                    code, why = self.hook(mode, cmd)
                    self.assertEqual(code, 0, f"{cmd!r} in {mode}: {why}")

    def test_the_narrow_over_refusal_is_known(self):
        for cmd in OVER_REFUSED:
            code, why = self.hook("ask", cmd)
            self.assertEqual((code, by(why)), (2, NEVER), why)
            self.assertIn("/tmp/x", why)


class Handover(HookCase):
    def test_wrap_and_hook_are_refused(self):
        self.refused_by(handovers(self.root))

    def test_the_wrapped_command_is_judged_on_its_own(self):
        """What wrap would have run: refused in a plain chat (BL-267), run in a confirmed one; unchanged."""
        code, why = self.hook("ask", "system/scripts/run tracker.py apply")
        self.assertEqual(code, 2)
        self.assertIn("changes the record", why)
        self.assertEqual(self.hook("confirmed", "system/scripts/run tracker.py apply")[0], 0)


if __name__ == "__main__":
    unittest.main()
