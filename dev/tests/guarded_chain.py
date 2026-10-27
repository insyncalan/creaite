"""Which guarded scripts the commits in a range changed, with the approved guarded chains as the one allowed exception.

The convention (dev/proposals/GUARDED-2.6.1.md, GUARDED-2.6.2.md): each approved chain is applied as ONE commit whose subject starts with
exactly that chain's marker. That commit is allowed to change guarded scripts only if, with the diffs listed in the chain file (read from
that commit's PARENT) reverse-applied to the guarded files, every guarded file equals its parent's content. A marked commit with anything
extra, a missing or unreadable chain file, a pin mismatch, a listed diff that is missing or does not reverse, or a guarded file the
diffs don't explain, fails closed: its guarded files are reported as changed. Eight chains are known (2.6.1, 2.6.2, 2.6.3, 2.6.4, 2.6.7, 2.6.8, 2.6.9, then 2.6.9b, the bundle rev 5); a
range may hold any of them, in order. Plain code, no network."""
import hashlib
import os
import subprocess
import tempfile
from pathlib import Path

GUARDED = ("tracker.py", "filechange.py", "reach.py", "permissions.py", "backup.py", "update.py", "live_server.py", "client_leak.py", "edit_ai.py", "draft_delivery.py")
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
CHAIN2_SHA256 = "d6441d5568bc7680a2e7f051e6fe3e91f1d14af079220743edf9910e09637c8d"
# BASE_261 is the 2.6.0 release the 2.6.1 chain was checked from. BASE2 is the 2.6.1 release commit, published:
# the full sha of 5bf7da29 (Jarvis, 23-10-2026; main's merge commit 256fdcc2 changes no content). CHAIN2_SHA256 is the value
# `python3 dev/tests/guarded_chain.py` prints; change it only with the chain list.
BASE_261 = "9501f2cdc850618e2ae34419bf2c6cb1c0d94ba0"
BASE2 = "5bf7da29e22e9b5b9b5c6b494c357280df4e4c4b"
# The 2.6.3 chain (dev/proposals/draft-delivery-guarded/README.md): its own marker, list and pin. draft_delivery.py joined GUARDED with it
# (it holds the hook that checks the Outlook create-draft call; the 2.6.2 blocker was found there). BASE3 is the published 2.6.2 release
# commit, main's merge 39c1060a: draft_delivery.py was written in the 2.6.2 range by unmarked commits, so the check now starts from the
# release (BASE below) and a range from BASE2 would report the whole file as new. CHAIN3_SHA256 is the pin of the cut
# 2.6.3 chain list (dev/proposals/GUARDED-2.6.3.chain and the diffs it names). A pin that does not match the list matches nothing, so a
# marked 2.6.3 commit fails closed; change the pin only with the list, on Alan's say. `python3 dev/tests/guarded_chain.py` prints the value.
CHAIN3_MARKER = "Guarded 2.6.3 chain:"
CHAIN3_FILE = "dev/proposals/GUARDED-2.6.3.chain"
CHAIN3_SHA256 = "e0670db88b51a179f8cacc97018859ac374c35b7a4a035f7b498b6d6b3878d99"
BASE3 = "39c1060aaeffa0c47a03a3c8e0e48208d3cb9ed6"
# The 2.6.4 chain (its guarded diffs come from the v264-guarded branch: 345, 346 and the 334 live_server diff): its own marker, list and
# pin, the same way. BASE4 is the published 2.6.3 release commit (main e6389af8, tag v2.6.3), so the range now starts after the 2.6.3 chain
# and a range from BASE3 would carry the 2.6.3 chain commit, whose pin is no longer the one in force. The list file starts EMPTY and the pin
# empty: an empty list has no digest, so a marked 2.6.4 commit fails closed (its guarded files are reported as changed) until the list is
# cut and CHAIN4_SHA256 set with it, on Alan's say. `python3 dev/tests/guarded_chain.py` prints the value.
CHAIN4_MARKER = "Guarded 2.6.4 chain:"
CHAIN4_FILE = "dev/proposals/GUARDED-2.6.4.chain"
CHAIN4_SHA256 = "46c5fd81e62ef6d2b9b915db910277977652f879b84e4575b975fdc4824d84b3"
BASE4 = "e6389af8bd466dabd768b7f1a4fd170922fda255"
# The 2.6.7 chain (dev/proposals/GUARDED-2.6.7.chain: #347 words, #339 typed refresh, sweep without the home folder, the followed-people
# rule; all in live_server.py): its own marker, list and pin. BASE5 is the published 2.6.6 release commit (tag v2.6.6, main's merge
# 8e4e1f07); 2.6.6 changed no guarded file after 2.6.5 (5798101b), so the range is the same range as from 2.6.5. The range
# starts after the 2.6.4 chain. `python3 dev/tests/guarded_chain.py` prints the pin; change it only with the list, on Alan's say.
CHAIN5_MARKER = "Guarded 2.6.7 chain:"
CHAIN5_FILE = "dev/proposals/GUARDED-2.6.7.chain"
CHAIN5_SHA256 = "eb4403611bf69c3342be377d78726c0679c4bfea061e98b20522c3fc83a617b5"
BASE5 = "8e4e1f07c3deed9e6d1fded32ace8bba46d51200"
# The 2.6.8 chain (dev/proposals/GUARDED-2.6.8.chain: #365, #368, #369 v4, #369b; live_server.py, client_leak.py, backup.py): its own marker,
# list and pin. BASE6 is the published 2.6.7 release commit (82d27bb5), so the range starts after the 2.6.7 chain.
# `python3 dev/tests/guarded_chain.py` prints the pin; change it only with the list, on Alan's say.
CHAIN6_MARKER = "Guarded 2.6.8 chain:"
CHAIN6_FILE = "dev/proposals/GUARDED-2.6.8.chain"
CHAIN6_SHA256 = "09ee06f5d86436a1dd9b9da143150fd34055a85578b962ff86ca2bc3002213c6"
BASE6 = "82d27bb530280859dadf0c290175b32c1bba6744"
# The 2.6.9 chain (dev/proposals/GUARDED-2.6.9.chain: #382 and #371 in live_server.py, the backup bundle in backup.py): its own marker, list and pin.
# BASE7 is the published 2.6.8 release commit (tag v2.6.8, 286b03c1), so the range starts after the 2.6.8 chain.
# `python3 dev/tests/guarded_chain.py` prints the pin; change it only with the list, on Alan's say.
CHAIN7_MARKER = "Guarded 2.6.9 chain:"
CHAIN7_FILE = "dev/proposals/GUARDED-2.6.9.chain"
CHAIN7_SHA256 = "00ffb0b748ffe447e61e3202239862d2600a4461ed4d5509977eae4c1ee16f8b"
BASE7 = "286b03c11ddb3ec8c51e0d376af8ded168839e8a"
# The second 2.6.9 chain (dev/proposals/GUARDED-2.6.9b.chain: bundle rev 5, backup-bundle-rev5.diff, in backup.py), applied after the
# first: its own marker, list and pin. Its marker does not start with CHAIN7_MARKER, nor CHAIN7_MARKER with it. BASE8 is the commit
# just before its marked commit (v269-release 2a8b20f3: the first 2.6.9 chain applied, the rev 5 list committed), so a range from BASE8
# checks the second chain alone. BASE stays BASE7: the 2.6.9 release range holds both chains, peeled latest first.
# `python3 dev/tests/guarded_chain.py` prints the pin; change it only with the list, on Alan's say.
CHAIN8_MARKER = "Guarded 2.6.9 chain (bundle rev 5):"
CHAIN8_FILE = "dev/proposals/GUARDED-2.6.9b.chain"
CHAIN8_SHA256 = "3a755cdbe1d0d4cb8117010af8b52085f20438f80d2a606605d6fc20e8faa0d3"
BASE8 = "2a8b20f33c2ffa20cc71c061ff8ec60bc7a1c93f"
BASE = BASE7
SPEC1 = (CHAIN_MARKER, CHAIN_FILE, "CHAIN_SHA256")
SPEC2 = (CHAIN2_MARKER, CHAIN2_FILE, "CHAIN2_SHA256")
SPEC3 = (CHAIN3_MARKER, CHAIN3_FILE, "CHAIN3_SHA256")
SPEC4 = (CHAIN4_MARKER, CHAIN4_FILE, "CHAIN4_SHA256")
SPEC5 = (CHAIN5_MARKER, CHAIN5_FILE, "CHAIN5_SHA256")
SPEC6 = (CHAIN6_MARKER, CHAIN6_FILE, "CHAIN6_SHA256")
SPEC7 = (CHAIN7_MARKER, CHAIN7_FILE, "CHAIN7_SHA256")
SPEC8 = (CHAIN8_MARKER, CHAIN8_FILE, "CHAIN8_SHA256")


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


def _marked_chains(repo, base, head, pin, pin2, pin3=None, pin4=None, pin5=None, pin6=None, pin7=None, pin8=None):
    """(peel, carried): per chain, latest first, (spec, pin, marked commit, guarded files its marked commits changed), and the union of
    those files. (None, set()) when a marked commit is not exactly its chain."""
    log = _git(repo, "log", "--no-merges", "--format=%H%x09%s", f"{base}..{head}")
    subjects = [l.split("\t", 1) for l in log.stdout.splitlines()]
    peel, carried = [], set()
    for spec, p in ((SPEC8, pin8), (SPEC7, pin7), (SPEC6, pin6), (SPEC5, pin5), (SPEC4, pin4), (SPEC3, pin3), (SPEC2, pin2), (SPEC1, pin)):
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


def guarded_touched(repo, base=BASE, head="HEAD", pin=None, ci=None, pin2=None, pin3=None, pin4=None, pin5=None, pin6=None, pin7=None,
                    pin8=None):
    """Guarded script paths whose content differs between base and head (the net change), except what the approved chain commits
    explain: for each chain (2.6.1, 2.6.2, 2.6.3, 2.6.4, 2.6.7, 2.6.8, 2.6.9, 2.6.9b) a commit in the range whose subject starts with its marker and which passes chain_explains.
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
    peel, carried = _marked_chains(repo, base, head, pin, pin2, pin3, pin4, pin5, pin6, pin7, pin8)
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
    print("CHAIN3_SHA256", chain_digest(here, "HEAD", SPEC3))
    print("CHAIN4_SHA256", chain_digest(here, "HEAD", SPEC4))
    print("CHAIN5_SHA256", chain_digest(here, "HEAD", SPEC5))
    print("CHAIN6_SHA256", chain_digest(here, "HEAD", SPEC6))
    print("CHAIN7_SHA256", chain_digest(here, "HEAD", SPEC7))
    print("CHAIN8_SHA256", chain_digest(here, "HEAD", SPEC8))
