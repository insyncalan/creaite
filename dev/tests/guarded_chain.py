"""Which guarded scripts the commits in a range changed, with the approved guarded chain as the one allowed exception.

The convention (dev/proposals/GUARDED-2.6.1.md): the approved chain is applied as ONE commit whose subject starts with exactly
CHAIN_MARKER. That commit is allowed to change guarded scripts only if, with the diffs listed in dev/proposals/GUARDED-2.6.1.chain
(read from that commit's own tree) reverse-applied to the guarded files, every guarded file equals its parent's content. A marked
commit with anything extra, a missing or unreadable chain file, a listed diff that is missing or does not reverse, or a guarded file
the diffs don't explain, fails closed: its guarded files are reported as changed. Plain code, no network."""
import hashlib
import os
import subprocess
import tempfile
from pathlib import Path

GUARDED = ("tracker.py", "filechange.py", "reach.py", "permissions.py", "backup.py", "update.py", "live_server.py", "client_leak.py", "edit_ai.py")
CHAIN_MARKER = "Guarded 2.6.1 chain:"
CHAIN_FILE = "dev/proposals/GUARDED-2.6.1.chain"
# The release the check starts from, as a commit (a branch name can move). Alan's say to change.
BASE = "9501f2cdc850618e2ae34419bf2c6cb1c0d94ba0"
# Pin: sha256 over the ordered chain list and the bytes of every diff it names (see chain_digest). The chain is read from the marked
# commit's PARENT and must match this, so a commit cannot bring its own proof. Changing the chain means changing this, knowingly:
# `python3 dev/tests/guarded_chain.py` prints the current value.
CHAIN_SHA256 = "a598a48e87c29f40227e21f2233329bd816e0c5154c1037e12f96a9b14cb3c8f"


class HistoryMissing(AssertionError):
    """In CI (CI=true) a missing base ref is a failure, not a skip."""


def _git(repo, *a, text=True, **kw):
    return subprocess.run(["git", *a], cwd=repo, capture_output=True, text=text, **kw)


def _is_guarded(f):
    return f.startswith("system/scripts/") and Path(f).name in GUARDED


def _blob(repo, ref, f):
    r = _git(repo, "show", f"{ref}:{f}", text=False)
    return r.stdout if r.returncode == 0 else None


def chain_digest(repo, ref):
    """sha256 over each listed diff's path and bytes, in the order of the chain file at `ref`; None if anything is missing."""
    chain = _git(repo, "show", f"{ref}:{CHAIN_FILE}")
    if chain.returncode != 0:
        return None
    diffs = [l.strip() for l in chain.stdout.splitlines() if l.strip() and not l.lstrip().startswith("#")]
    h = hashlib.sha256()
    for d in diffs:
        body = _blob(repo, ref, d)
        if body is None:
            return None
        h.update(d.encode() + b"\0" + body + b"\0")
    return h.hexdigest() if diffs else None


def reversed_chain(repo, chain_sha, content_ref, files, pin=None):
    """{file: bytes}: the `files` as they are at content_ref with the chain diffs (listed in chain_sha's tree, which must match the pin) reverse-applied,
    last diff first. None when the chain file or a listed diff is missing, a file is absent, or a diff doesn't reverse."""
    if chain_digest(repo, chain_sha) != (pin or CHAIN_SHA256):
        return None
    chain = _git(repo, "show", f"{chain_sha}:{CHAIN_FILE}")
    diffs = [l.strip() for l in chain.stdout.splitlines() if l.strip() and not l.lstrip().startswith("#")]
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


def chain_explains(repo, sha, files, pin=None):
    """True when the pinned chain (read from sha's PARENT, never its own tree), reversed on commit `sha`'s `files`, gives each
    file's parent content."""
    back = reversed_chain(repo, sha + "^", sha, files, pin)
    return back is not None and all(back[f] == _blob(repo, sha + "^", f) for f in files)


def guarded_touched(repo, base=BASE, head="HEAD", pin=None, ci=None):
    """Guarded script paths whose content differs between base and head (the net change), except what the one approved chain
    commit explains: a commit in the range whose subject starts with CHAIN_MARKER and which passes chain_explains; the chain
    diffs reversed on head's files must then give base's content. None when git history for base isn't available."""
    d = _git(repo, "diff", "--name-only", "--no-renames", base, head)
    if d.returncode != 0:
        if (os.environ.get("CI", "") if ci is None else ci).lower() in ("true", "1"):
            raise HistoryMissing(f"CI: git history for {base} is missing (use fetch-depth: 0): check 9 cannot run")
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
        if not set(net) <= set(own) or not chain_explains(repo, sha, own, pin):   # it must itself carry every net change
            return net
    back = reversed_chain(repo, marked[0] + "^", head, net, pin)
    if back is None:
        return net
    return [f for f in net if back[f] != _blob(repo, base, f)]


if __name__ == "__main__":
    print(chain_digest(Path(__file__).resolve().parents[2], "HEAD"))
