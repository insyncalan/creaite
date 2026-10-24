"""2.6.4 (line-reach): ai_budget.py and start_tokens_report.py are classified READ in reach.SCRIPT_COMMANDS, and only that.
dev/proposals/line-reach/reach.diff is put on a copy of reach.py when this tree lacks it, so the test is the same either way.
Mutant: either one classified as record turns the test red.

Run: python3 dev/tests/test_reach_line_entries.py
"""
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIFF = ROOT / "dev/proposals/line-reach/reach.diff"
SRC = ROOT / "system/scripts/reach.py"
SCRIPTS = ("ai_budget.py", "start_tokens_report.py")


def load(mutate=None):
    """reach.py as the chain leaves it, as a module of its own (the diff put on a copy when the tree lacks it)."""
    d = Path(tempfile.mkdtemp(prefix="creaite-reach-"))
    f = d / "system/scripts/reach.py"
    f.parent.mkdir(parents=True)
    shutil.copy(SRC, f)
    sys.path.insert(0, str(ROOT / "system/scripts"))
    if '"ai_budget.py"' not in f.read_text():
        subprocess.run(["git", "apply", str(DIFF)], cwd=d, check=True)
    if mutate:
        t = f.read_text()
        old = f'"{mutate}": {{"": READ}}'
        assert old in t, mutate
        f.write_text(t.replace(old, f'"{mutate}": {{"": RECORD}}', 1))
    spec = importlib.util.spec_from_file_location("reach_line_copy", f)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    shutil.rmtree(d, ignore_errors=True)
    return mod


def read_only(mod):
    return all(mod.SCRIPT_COMMANDS.get(s) == {"": mod.READ} for s in SCRIPTS)


class Entries(unittest.TestCase):
    def test_both_are_read_and_nothing_else(self):
        mod = load()
        for s in SCRIPTS:
            self.assertEqual(mod.SCRIPT_COMMANDS[s], {"": "read"}, s)
            for kind in (mod.STAGE, mod.GUARDED, mod.RECORD, mod.DERIVED):
                self.assertNotIn(kind, mod.SCRIPT_COMMANDS[s].values(), s)

    def test_mutant_either_one_as_record_goes_red(self):
        for s in SCRIPTS:
            self.assertFalse(read_only(load(mutate=s)), s)


if __name__ == "__main__":
    unittest.main(verbosity=1)
