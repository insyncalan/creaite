"""Every test vault holds every module its scripts import (lazy imports included). A missing module behind a try/except looks like
'unavailable' and lets a test pass without testing anything (the #250 hold tests did exactly that).

Run: python3 dev/tests/test_vault_modules_complete.py
"""
import importlib.util
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location("check_test_vault_modules", HERE.parents[1] / "dev" / "tools" / "check_test_vault_modules.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class VaultModules(unittest.TestCase):
    def test_audit_script_passes(self):
        self.assertEqual(audit.main.__module__, "check_test_vault_modules")
        argv, sys.argv = sys.argv, ["x", "--all"]
        try:
            self.assertEqual(audit.main(), 0)
        finally:
            sys.argv = argv

    def test_make_vault_copies_every_script(self):
        import test_tracker as T
        mods, g = audit.graph()
        self.assertEqual(audit.closure({m for m in mods}, g).keys() - mods, set())
        v = T.Vault()
        try:
            have = {p.stem for p in (v.root / "system" / "scripts").glob("*.py")}
            self.assertEqual(mods - have, set(), "the throwaway vault lacks scripts")
            need = audit.closure(have, g)
            self.assertEqual({d for d in need if d not in have}, set())
        finally:
            v.cleanup()

    def test_audit_detects_a_gap(self):
        mods, g = audit.graph()
        copied = mods - {"transcript_hold"}
        need = audit.closure(copied, g)
        self.assertIn("transcript_hold", {d for d in need if d not in copied}, "the audit must see a lazy import that is not copied")

    def test_lazy_guarded_modules_are_found(self):
        mods, g = audit.graph()
        self.assertEqual(g["transcripts"].get("transcript_hold"), "lazy")
        self.assertEqual(g["live_server"].get("ai_budget"), "lazy")


if __name__ == "__main__":
    unittest.main()
