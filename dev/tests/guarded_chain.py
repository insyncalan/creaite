"""Which guarded scripts the commits in a range changed, with the approved guarded chains as the one allowed exception.

The convention (dev/proposals/GUARDED-2.6.1.md, GUARDED-2.6.2.md): each approved chain is applied as ONE commit whose subject starts with
exactly that chain's marker. That commit is allowed to change guarded scripts only if, with the diffs listed in the chain file (read from
that commit's PARENT) reverse-applied to the guarded files, every guarded file equals its parent's content. A marked commit with anything
extra, a missing or unreadable chain file, a pin mismatch, a listed diff that is missing or does not reverse, or a guarded file the
diffs don't explain, fails closed: its guarded files are reported as changed. Two chains are known (2.6.1, then 2.6.2); a range may hold
either or both, in order. Plain code, no network."""
import hashlib
import os
import subprocess
import tempfile
from pathlib import Path

GUARDED = ("tracker.py", "filechange.py", "reach.py", "permissions.py", "backup.py", "update.py", "live_server.py", "client_leak.py", "edit_ai.py")
CHAIN_MARKER = "Guarded 2.6.1 chain:"
CHAIN_FILE = "dev/proposals/GUARDED-2.6.1.chain"
# The releases the check starts from are BASE_261 and BASE below, as commits (a branch name can move). Alan's say to change.
# Pin: sha256 over the ordered chain list and the bytes of every diff it names (see chain_digest). The chain is read from the marked
# commit's PARENT and must match this, so a commit cannot bring its own proof. Changing the chain means changing this, knowingly:
# `python3 dev/tests/guarded_chain.py` prints the current value.
CHAIN_SHA256 = "a598a48e87c29f40227e21f2233329bd816e0c5154c1037e12f96a9b14cb3c8f"

# The 2.6.2 chain (dev/proposals/GUARDED-2.6.2.md): its own marker, list and pin. Its range starts at BASE, the 2.6.1 release commit.
CHAIN2_MARKER = "Guarded 2.6.2 chain:"
CHAIN2_FILE = "dev/proposals/GUARDED-2.6.2.chain"
CHAIN2_SHA256 = "16038c62caa90dacfba846f97281fe628eff7e3339d8371aba998950a7215596"
# BASE_261 is the 2.6.0 release the 2.6.1 chain was checked from. BASE2 (also BASE, the default) is the 2.6.1 release commit, published:
# the full sha of 5bf7da29 (Jarvis, 23-10-2026; main's merge commit 256fdcc2 changes no content). CHAIN2_SHA256 is the value
# `python3 dev/tests/guarded_chain.py` prints; change it only with the chain list.
BASE_261 = "9501f2cdc850618e2ae34419bf2c6cb1c0d94ba0"
BASE2 = "5bf7da29e22e9b5b9b5c6b494c357280df4e4c4b"
BASE = BASE2
SPEC1 = (CHAIN_MARKER, CHAIN_FILE, "CHAIN_SHA256")
SPEC2 = (CHAIN2_MARKER, CHAIN2_FILE, "CHAIN2_SHA256")


class HistoryMissing(AssertionError):
    """In CI (CI=true) a missing base ref is a failure, not a skip."""


def _git(repo, *a, text=True, **kw):
    return subprocess.run(["git", *a], cwd=repo, capture_output=True, text=text, **kw)


def _is_guarded(f):
    return f.startswith("system/scripts/") and Path(f).name in GUARDED


def _blob(repo, ref, f):
    r = _git(repo, "show", f"{ref}:{f}", text=False)
    return r.stdout if r.returncode == 0 else None


def _diffs(repo, ref, chain_file):
    chain = _git(repo, "show", f"{ref}:{chain_file}")
    if chain.returncode != 0:
        return None
    return [l.strip() for l in chain.stdout.splitlines() if l.strip() and not l.lstrip().startswith("#")]


def chain_digest(repo, ref, spec=SPEC1):
    """sha256 over each listed diff's path and bytes, in the order of the chain file at `ref`; None if anything is missing."""
    diffs = _diffs(repo, ref, spec[1])
    if diffs is None:
        return None
    h = hashlib.sha256()
    for d in diffs:
        body = _blob(repo, ref, d)
        if body is None:
            return None
        h.update(d.encode() + b"\0" + body + b"\0")
    return h.hexdigest() if diffs else None


def reversed_chain(repo, chain_sha, content_ref, files, pin=None, spec=SPEC1, start=None):
    """{file: bytes}: the `files` as they are at content_ref (or in `start`, a {file: bytes} already partly reversed) with the chain diffs
    (listed in chain_sha's tree, which must match the pin) reverse-applied, last diff first. None when the chain file or a listed diff
    is missing, a file is absent, or a diff doesn't reverse."""
    if chain_digest(repo, chain_sha, spec) != (pin or globals()[spec[2]]):
        return None
    diffs = _diffs(repo, chain_sha, spec[1])
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for f in files:
            now = start[f] if start is not None else _blob(repo, content_ref, f)
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


def chain_explains(repo, sha, files, pin=None, spec=SPEC1):
    """True when the pinned chain (read from sha's PARENT, never its own tree), reversed on commit `sha`'s `files`, gives each
    file's parent content."""
    back = reversed_chain(repo, sha + "^", sha, files, pin, spec)
    return back is not None and all(back[f] == _blob(repo, sha + "^", f) for f in files)


def _marked_chains(repo, base, head, pin, pin2):
    """(peel, carried): per chain, latest first, (spec, pin, marked commit, guarded files its marked commits changed), and the union of
    those files. (None, set()) when a marked commit is not exactly its chain."""
    log = _git(repo, "log", "--no-merges", "--format=%H%x09%s", f"{base}..{head}")
    subjects = [l.split("\t", 1) for l in log.stdout.splitlines()]
    peel, carried = [], set()
    for spec, p in ((SPEC2, pin2), (SPEC1, pin)):
        marked = [h for h, subj in subjects if subj.startswith(spec[0])]
        if not marked:
            continue
        own_all = set()
        for sha in marked:                          # every marked commit must be exactly its chain
            own = [f for f in _git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "--root", sha).stdout.splitlines() if _is_guarded(f)]
            if not chain_explains(repo, sha, own, p, spec):
                return None, set()
            own_all |= set(own)
        peel.append((spec, p, marked[0], sorted(own_all)))
        carried |= own_all
    return peel, carried


def _peel_back(repo, head, peel, cur):
    """Reverse each chain on its own files, latest first, updating cur in place. False when a chain does not reverse."""
    for spec, p, sha, own in peel:
        back = reversed_chain(repo, sha + "^", head, [f for f in own if f in cur], p, spec, start=cur)
        if back is None:
            return False
        cur.update(back)
    return True


def guarded_touched(repo, base=BASE, head="HEAD", pin=None, ci=None, pin2=None):
    """Guarded script paths whose content differs between base and head (the net change), except what the approved chain commits
    explain: for each chain (2.6.1, 2.6.2) a commit in the range whose subject starts with its marker and which passes chain_explains.
    Every net change must be carried by a marked commit, and the chains' diffs, reversed latest chain first, each only on the files its
    own marked commit changed, must give base's content. None when git history for base isn't available."""
    d = _git(repo, "diff", "--name-only", "--no-renames", base, head)
    if d.returncode != 0:
        if (os.environ.get("CI", "") if ci is None else ci).lower() in ("true", "1"):
            raise HistoryMissing(f"CI: git history for {base} is missing (use fetch-depth: 0): check 9 cannot run")
        return None
    net = [f for f in d.stdout.splitlines() if _is_guarded(f)]
    if not net:
        return []
    peel, carried = _marked_chains(repo, base, head, pin, pin2)
    if peel is None or not peel or not set(net) <= carried:     # a net change no marked commit made itself is somebody else's edit
        return net
    cur = {f: _blob(repo, head, f) for f in net}
    if any(v is None for v in cur.values()) or not _peel_back(repo, head, peel, cur):
        return net
    return [f for f in net if cur[f] != _blob(repo, base, f)]


if __name__ == "__main__":
    here = Path(__file__).resolve().parents[2]
    print("CHAIN_SHA256 ", chain_digest(here, "HEAD", SPEC1))
    print("CHAIN2_SHA256", chain_digest(here, "HEAD", SPEC2))
