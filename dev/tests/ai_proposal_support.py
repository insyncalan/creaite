"""#132 round 1 proposal (dev/proposals/ai-models/round1): what its tests share. Not a test file itself.

The proposal's guarded changes are diff files, not applied to this branch. Each test builds a throwaway vault from this
branch (test_tracker.make_vault), applies the diffs it is about there with `git apply` (in order), and runs its checks in a
subprocess against that vault's scripts, so nothing here imports the patched files into the test process and nothing touches
this repository's own files.

CREAITE_PROPOSAL_UNPATCHED=1 builds the same vault without applying any diff: every test of the proposal must then fail
(that is how "each test fails when its hunk is reverted" is checked; see the README).
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import REPO, make_vault  # noqa: E402

ROUND1 = Path(os.environ.get("CREAITE_PROPOSAL_DIFFS") or REPO / "dev" / "proposals" / "ai-models" / "round1")   # the
#                         override is for the hunk-by-hunk check only (a folder of the same diffs with one hunk left out)
UNPATCHED = os.environ.get("CREAITE_PROPOSAL_UNPATCHED") == "1"


def diff_path(name):
    """The proposal's diff file by its short name (g1-key-store, …)."""
    return ROUND1 / f"{name}.diff"


def apply(root, names):
    """Apply the proposal's diffs, in order, to a vault's files (root holds system/scripts/…). Raises on any that won't apply."""
    for name in names:
        r = subprocess.run(["git", "apply", "--whitespace=nowarn", str(diff_path(name))], cwd=root, capture_output=True,
                           text=True)
        if r.returncode != 0:
            raise AssertionError(f"{name}.diff doesn't apply:\n{r.stderr}")


def vault(*names, patched=True):
    """A throwaway vault with the named diffs applied (none when patched is False, or under CREAITE_PROPOSAL_UNPATCHED=1)."""
    root = make_vault()
    if patched and not UNPATCHED:
        apply(root, names)
    return root


def fake_home():
    """A stand-in home folder holding the secrets the never list names (an SSH key, a keychain file): nothing real."""
    home = Path(tempfile.mkdtemp(prefix="creaite-home-"))
    for rel in (".ssh/id_rsa", "Library/Keychains/login.keychain-db", "Documents/notes.txt"):
        (home / rel).parent.mkdir(parents=True, exist_ok=True)
        (home / rel).write_text("stand-in, not a secret\n")
    return home


def run_py(root, code, env=None, timeout=120):
    """Run Python code in the vault (cwd = the vault, its system/scripts first on the path) and return what it printed last,
    as JSON."""
    prelude = "import sys, json, os\nsys.path.insert(0, 'system/scripts')\n"
    e = {k: v for k, v in os.environ.items() if k not in ("CREAITE_FAKE_PROVIDERS",)}
    e.update(env or {})
    r = subprocess.run([sys.executable, "-c", prelude + code], cwd=root, capture_output=True, text=True, env=e, timeout=timeout)
    if r.returncode != 0:
        raise AssertionError(f"the check failed in the vault:\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
    lines = [x for x in r.stdout.splitlines() if x.strip()]
    return json.loads(lines[-1]) if lines else None
