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


def _blob(repo, ref, f):
    r = _git(repo, "show", f"{ref}:{f}", text=False)
    return r.stdout if r.returncode == 0 else None


def reversed_chain(repo, chain_sha, content_ref, files):
    """{file: bytes}: the `files` as they are at content_ref with the chain diffs (listed in chain_sha's own tree) reverse-applied,
    last diff first. None when the chain file or a listed diff is missing, a file is absent, or a diff doesn't reverse."""
    chain = _git(repo, "show", f"{chain_sha}:{CHAIN_FILE}")
    if chain.returncode != 0:
        return None
    diffs = [l.strip() for l in chain.stdout.splitlines() if l.strip() and not l.lstrip().startswith("#")]
    if not diffs:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for f in files:
            now = _blob(repo, content_ref, f)
            if now is None:
                return None
            (tmp / f).parent.mkdir(parents=True, exist_ok=True)
            (tmp / f).write_bytes(now)
        inc = [a for f in files for a in ("--include", f)]
        for d in reversed(diffs):
            body = _blob(repo, chain_sha, d)
            if body is None:
                return None
            r = subprocess.run(["git", "apply", "-R", "--unsafe-paths", "--directory", "", *inc, "-"], cwd=tmp, input=body, capture_output=True)
            if r.returncode != 0:
                return None
        return {f: (tmp / f).read_bytes() for f in files}


def chain_explains(repo, sha, files):
    """True when the chain diffs, reversed on commit `sha`'s `files`, give each file's parent content."""
    back = reversed_chain(repo, sha, sha, files)
    return back is not None and all(back[f] == _blob(repo, sha + "^", f) for f in files)


def guarded_touched(repo, base, head="HEAD"):
    """Guarded script paths whose content differs between base and head (the net change), except what the one approved chain
    commit explains: a commit in the range whose subject starts with CHAIN_MARKER and which passes chain_explains; the chain
    diffs reversed on head's files must then give base's content. None when git history for base isn't available."""
    d = _git(repo, "diff", "--name-only", base, head)
    if d.returncode != 0:
        return None
    net = [f for f in d.stdout.splitlines() if _is_guarded(f)]
    if not net:
        return []
    log = _git(repo, "log", "--no-merges", "--format=%H%x09%s", f"{base}..{head}")
    marked = [l.split("\t")[0] for l in log.stdout.splitlines() if l.split("\t", 1)[-1].startswith(CHAIN_MARKER)]
    if not marked:
        return net
    for sha in marked:                              # every marked commit must be exactly the chain
        own = [f for f in _git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "--root", sha).stdout.splitlines() if _is_guarded(f)]
        if own and not chain_explains(repo, sha, own):
            return net
    back = reversed_chain(repo, marked[0], head, net)
    if back is None:
        return net
    return [f for f in net if back[f] != _blob(repo, base, f)]
