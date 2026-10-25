"""#132 (G8 spike, 25-10-2026): a Claude key, token or host in the shell that started the live server must never reach a run.

Run: python3 dev/tests/test_v270_billing_env.py     (quick tier: no Chrome, no vault)

- paths.claude_billing_env names (never the values of) the settings that change how Claude is billed or where it connects.
- doctor says when its own environment holds one (a warning, never a failure, and never the value).
- GUARDED: live_server.run_env scrubs them from every run's environment (dev/proposals/132/01-live_server-scrub-env.patch).
- --bare turns the guard hook off: no launch, builder or script may use it, nor set CLAUDE_CODE_SIMPLE (a source-level check).
"""
import os
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "system" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import paths  # noqa: E402

CANARY = "sk-ant-canary-0000-TESTONLY"
LIVE = (SCRIPTS / "live_server.py").read_text()
SCRUBBED = "claude_billing_env" in LIVE


class Names(unittest.TestCase):
    def test_names_only_the_billing_settings(self):
        env = {"ANTHROPIC_API_KEY": CANARY, "ANTHROPIC_BASE_URL": "http://x", "CLAUDE_CODE_USE_BEDROCK": "1",
               "CLAUDE_CODE_OAUTH_TOKEN": CANARY, "PATH": "/usr/bin", "HOME": "/h", "CLAUDE_CONFIG_DIR": "/c"}
        self.assertEqual(paths.claude_billing_env(env), ["ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL", "CLAUDE_CODE_OAUTH_TOKEN",
                                                         "CLAUDE_CODE_USE_BEDROCK"])
        self.assertEqual(paths.claude_billing_env({"PATH": "/usr/bin"}), [])

    def test_doctor_warns_with_names_and_never_the_value(self):
        import doctor
        old = os.environ.get("ANTHROPIC_API_KEY")
        try:
            os.environ["ANTHROPIC_API_KEY"] = CANARY
            ok, detail = doctor.claude_billing_env()
            self.assertIsNone(ok)                                   # a warning
            self.assertIn("ANTHROPIC_API_KEY", detail)
            self.assertNotIn(CANARY, detail)
            os.environ.pop("ANTHROPIC_API_KEY")
            for k in paths.claude_billing_env():
                os.environ.pop(k, None)
            self.assertTrue(doctor.claude_billing_env()[0])
        finally:
            if old is None:
                os.environ.pop("ANTHROPIC_API_KEY", None)
            else:
                os.environ["ANTHROPIC_API_KEY"] = old


@unittest.skipUnless(SCRUBBED, "GUARDED: needs dev/proposals/132/01-live_server-scrub-env.patch (live_server.py is a guarded file)")
class Scrub(unittest.TestCase):
    def test_a_run_never_inherits_a_key_token_or_host(self):
        import live_server
        names = ["ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL", "CLAUDE_CODE_OAUTH_TOKEN",
                 "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_SIMPLE", "CLAUDE_CODE_API_KEY_HELPER_TTL_MS"]
        old = {k: os.environ.get(k) for k in names}
        try:
            for k in names:
                os.environ[k] = CANARY
            for kind in (None, "prep", "held"):
                env = live_server.run_env(kind)
                self.assertEqual([k for k in names if k in env], [], kind)
                self.assertNotIn(CANARY, " ".join(env.values()))
                self.assertIn("PATH", env)                           # the rest of the environment is kept
        finally:
            for k, v in old.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)


class NoBare(unittest.TestCase):
    """--bare skips hooks, so the guard would not run (G8 spike, section 3)."""

    def test_no_script_launches_claude_bare_or_in_simple_mode(self):
        hits = []
        for f in sorted(SCRIPTS.glob("*.py")):
            for n, line in enumerate(f.read_text().splitlines(), 1):
                if re.search(r"""["']--bare["']|--bare\s|CLAUDE_CODE_SIMPLE\s*["']?\]?\s*=""", line) and f.name != "paths.py":
                    hits.append(f"{f.name}:{n}")
        self.assertEqual(hits, [])

    def test_the_run_command_builders_exist_and_are_checked(self):
        # the three launch sites build their argument list in live_server.py; a rename must not hide them from the check above
        self.assertGreaterEqual(len(re.findall(r'"--output-format"', LIVE)), 2)


if __name__ == "__main__":
    unittest.main()
