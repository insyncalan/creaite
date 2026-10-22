"""Which guarded scripts the commits in a range changed, with the approved guarded chain as the one allowed exception.

The convention (dev/proposals/GUARDED-2.6.1.md): the approved chain is applied as ONE commit whose subject starts with exactly
CHAIN_MARKER. That commit is allowed to change guarded scripts only if, with the diffs listed in dev/proposals/GUARDED-2.6.1.chain
(read from that commit's own tree) reverse-applied to the guarded files, every guarded file equals its parent's content. A marked
commit with anything extra, a missing or unreadable chain file, a listed diff that is missing or does not reverse, or a guarded file
the diffs don't explain, fails closed: its guarded files are reported as changed. Plain code, no network."""
import subprocess
import tempfile
from pathlib import Path

GUARDED = ("tracker.py", "filechange.py", "reach.py", "permissions.py", "backup.py", "update.py")
CHAIN_MARKER = "Guarded 2.6.1 chain:"
CHAIN_FILE = "dev/proposals/GUARDED-2.6.1.chain"


def _git(repo, *a, text=True, **kw):
    return subprocess.run(["git", *a], cwd=repo, capture_output=True, text=text, **kw)


def _is_guarded(f):
    return f.startswith("system/scripts/") and Path(f).name in GUARDED


def chain_explains(repo, sha, files):
    """True when reverse-applying the listed chain diffs to the guarded `files` of commit `sha` gives each file's parent content."""
    chain = _git(repo, "show", f"{sha}:{CHAIN_FILE}")
    if chain.returncode != 0:
        return False
    diffs = [l.strip() for l in chain.stdout.splitlines() if l.strip() and not l.lstrip().startswith("#")]
    if not diffs:
        return False
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        parents = {}
        for f in files:
            now = _git(repo, "show", f"{sha}:{f}", text=False)
            before = _git(repo, "show", f"{sha}^:{f}", text=False)
            if now.returncode != 0 or before.returncode != 0:        # added or deleted: not an explained change
                return False
            (tmp / f).parent.mkdir(parents=True, exist_ok=True)
            (tmp / f).write_bytes(now.stdout)
            parents[f] = before.stdout
        inc = [a for f in files for a in ("--include", f)]
        for d in reversed(diffs):
            body = _git(repo, "show", f"{sha}:{d}", text=False)
            if body.returncode != 0:
                return False
            r = subprocess.run(["git", "apply", "-R", "--unsafe-paths", "--directory", "", *inc, "-"], cwd=tmp, input=body.stdout,
                               capture_output=True)
            if r.returncode != 0:
                return False
        return all((tmp / f).read_bytes() == parents[f] for f in files)


def guarded_touched(repo, base, head="HEAD"):
    """Guarded script paths changed by the commits in base..head, commit by commit (merge commits themselves skipped, the commits
    they bring in are not). None when git history for base isn't available (the caller skips)."""
    r = _git(repo, "log", "--no-merges", "--format=%H", f"{base}..{head}")
    if r.returncode != 0:
        return None
    touched = []
    for sha in r.stdout.split():
        files = [f for f in _git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "--root", sha).stdout.splitlines() if _is_guarded(f)]
        if not files:
            continue
        subject = _git(repo, "log", "-1", "--format=%s", sha).stdout.strip()
        if subject.startswith(CHAIN_MARKER) and chain_explains(repo, sha, files):
            continue
        touched += files
    return touched
