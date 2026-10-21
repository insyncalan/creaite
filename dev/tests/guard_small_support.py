"""Shared set-up for the guard-small proposal tests (dev/proposals/guard-small/): a throwaway vault with a copy of the whole of
system/scripts/, the guarded files there with (or without) the proposal's diffs, and an optional mutation, so each test reads
the guard's decisions from the copy, never from the repository's own guarded files.

- GUARD_SMALL_UNPATCHED=1: the copy is left without the diffs (fail-first: the tests must go red).
- GUARD_SMALL_MUTATE=<name>: one mutation of the patched copy (each test file's MUTATIONS), to prove the tests notice it.
Once a diff is applied to the repository its marker is found there, the patch step is skipped and the unpatched copy is made
with `patch -R`, so the same tests go on guarding the real file.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_tracker import Vault  # noqa: E402

REPO = HERE.parents[1]
PROPOSALS = REPO / "dev" / "proposals" / "guard-small"
UNPATCHED = os.environ.get("GUARD_SMALL_UNPATCHED") == "1"
MUTATE = os.environ.get("GUARD_SMALL_MUTATE", "")

# diff -> (the file it changes, a line only the patched file has)
DIFFS = {
    "tracker-copy-source.diff": ("system/scripts/tracker.py", "class CopySource:"),
    "live-server-prompt.diff": ("system/scripts/live_server.py", "never an Edit or Write rule: files change through filechange.py"),
    "live-server-post-hook.diff": ("system/scripts/live_server.py", 'hooks["PostToolUse"]'),
    "reach-post-claim.diff": ("system/scripts/reach.py", "def post_tool"),
}


def _patch(root, diff, *flags):
    r = subprocess.run(["patch", "-p0", "-s", *flags, "-i", str(PROPOSALS / diff)], cwd=root, capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError(f"patch {diff} {' '.join(flags)} failed in the scratch copy:\n{r.stdout}\n{r.stderr}")


def scratch(diffs, mutations=None, patched=None):
    """A throwaway vault (Vault, initialised) with a copy of system/scripts/ and system/templates/, `diffs` applied (or taken off
    when GUARD_SMALL_UNPATCHED=1 or patched=False), and GUARD_SMALL_MUTATE's mutation from `mutations` made."""
    patched = (not UNPATCHED) if patched is None else patched
    v = Vault()
    v.run("init")
    shutil.copytree(REPO / "system" / "scripts", v.root / "system" / "scripts", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(REPO / "system" / "templates", v.root / "system" / "templates", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "dashboard"))
    for diff in diffs:
        rel, marker = DIFFS[diff]
        has = marker in (v.root / rel).read_text(encoding="utf-8")
        if patched and not has:
            _patch(v.root, diff)
        elif not patched and has:
            _patch(v.root, diff, "-R")
    if MUTATE and mutations and MUTATE in mutations and patched:
        rel, old, new = mutations[MUTATE][1:]
        f = v.root / rel
        text = f.read_text(encoding="utf-8")
        assert text.count(old) == 1, f"mutation {MUTATE}: {old!r} found {text.count(old)} times"
        f.write_text(text.replace(old, new), encoding="utf-8")
    return v


def in_vault(v, code, arg=None, timeout=300):
    """Run Python `code` in the vault (cwd and paths.ROOT are the vault there); its JSON output."""
    r = subprocess.run([sys.executable, "-c", "import json, sys; sys.path.insert(0, 'system/scripts')\n" + code],
                       input=json.dumps(arg), cwd=v.root, capture_output=True, text=True, timeout=timeout)
    if r.returncode:
        raise AssertionError(r.stdout + r.stderr)
    return json.loads(r.stdout.strip().splitlines()[-1])


def mutants_caught(test_file, mutations, tests):
    """For each mutation, run `tests` of `test_file` against the mutated copy; the names of the mutations that were NOT caught."""
    missed = []
    for name in mutations:
        env = dict(os.environ, GUARD_SMALL_MUTATE=name)
        env.pop("GUARD_SMALL_UNPATCHED", None)
        args = [sys.executable, str(test_file)] + [x for t in tests for x in ("-k", t)]
        r = subprocess.run(args, env=env, capture_output=True, text=True, timeout=1200)
        said = r.stdout + r.stderr
        if r.returncode == 0 or f"mutation {name}:" in said or "FAILED" not in said:   # a mutation not made is not a catch
            missed.append(name)
    return missed
