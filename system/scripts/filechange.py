"""creaite filechange — the only way ask creaite changes a file (BL-93, BL-96, BL-141). Standard library only.

ask creaite has no Edit, Write or open Bash for files: it prepares new content in system/staging/ and runs this script. What it
may touch is decided by reach.py (the vault, the projects folder and the home folder, minus the never list):
  ordinary   done at once: backed up first, logged (what, where, why; never contents), a line in the debug log, undoable
  sensitive  refused with "Needs approval" and the reason; in an ask creaite run the change is recorded as a request
             (system/staging/changes/), which the live server shows on its one card. Only Alan's Approve, through the server,
             makes it: the server calls perform() in its own process with a one-time approval. This command line has no way
             to pass one.
  never      refused, whatever is asked

Commands:
  check <path> [--edit]         would this create (or, with --edit, change) be done? JSON {ok, kind, reason, path, exists}; writes nothing
  create <path> --from <file> [--why "<reason>"]      a new file from <file> (inside system/staging/); never overwriting: a name
                                that is taken gets a number, "Name (2).docx"
  edit <path> --from <file> --why "<reason>"          replace an existing file's content with <file>'s
  move <path> <new path> --why "<reason>"             rename or move one existing file (never onto a file that is there)
  delete <path> --why "<reason>"                      delete one existing file (a copy is kept)
  undo [<n>]                    undo the latest change that hasn't been undone (or change <n>): a created file is removed, a changed
                                one put back, a moved one moved back, a deleted one restored. Refused when the file has been changed
                                since, so nothing Alan did is lost. Undoing an editing session's latest save (#119) puts back the
                                text from before the session and undoes its earlier saves with it
  list [--json] [--days N]      the changes made through this script

<path> is a stored path (projects/<folder>/…, mapped to the projects root), a vault path, ~/… or an absolute path. Every change is
saved first under system/backups/files/changes/<n>/ and logged in system/config/files-log.jsonl, with its tier (BL-194): ordinary
(made at once), sensitive or high (High-risk: a permission file or a permission rule), both made only on Alan's Approve.
"""
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
import reach  # noqa: E402

LOG = paths.SYSTEM / "config" / "files-log.jsonl"
CHANGES = paths.BACKUPS / "files" / "changes"
REQUESTS = paths.STAGING / "changes"          # sensitive changes asked for in a run: only asks; the server decides with Alan
STAGED = "system/staging/"
CHANGE_OPS = ("create", "edit", "move", "delete")
OP_KIND = {"create": "create", "edit": "change", "move": "move", "delete": "delete"}
NEEDS = 3                                       # exit code: needs approval
TIER_WORD = {"sensitive": "[Sensitive] ", "high": "[High-risk] "}   # BL-194: list shows the card's tier


def now():
    """The time now as YYYY-MM-DD HH:MM:SS, as the change log stores it."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def sha(p):
    """The SHA-256 of a file's bytes."""
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sha_bytes(b):
    """The SHA-256 of some bytes."""
    return hashlib.sha256(b).hexdigest()


def entries():
    """Every entry in system/config/files-log.jsonl, oldest first; a line that isn't JSON is skipped."""
    out = []
    if LOG.exists():
        for line in LOG.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    return out


def log(entry):
    """Append one entry to system/config/files-log.jsonl and a line to the debug log (what and where, never the contents)."""
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    reach._debug("info", f"{entry['op']} {entry['path']}{(' → ' + entry['to']) if entry.get('to') else ''} (change {entry['id']}"
                         f"{', approved' if entry.get('approved') else ''})")


def next_id(es=None):
    """The next change number: one more than the highest in the log (or in `es`)."""
    return max([e.get("id", 0) for e in (es if es is not None else entries())] + [0]) + 1


def stored(p):
    """How a path is written in the log: projects/… or a vault path when it is in the vault or the projects root, ~/… in the home
    folder (portable: never an absolute home path), else the absolute path."""
    p = Path(os.path.realpath(p))
    for name, root in reach.roots():
        if name in ("vault", "projects") and reach.parts_under(p, root) is not None:
            return paths.rel(p)
    rel = reach.parts_under(p, reach.home())
    return "~/" + "/".join(rel) if rel is not None else str(p)


def resolve(stored_path):
    """A stored path (~/…, projects/…, a vault path or an absolute one) as a Path, before symlinks are resolved."""
    s = os.path.expanduser(str(stored_path))
    return Path(s) if Path(s).is_absolute() else paths.resolve(s)


def run_state():
    """(run id or None, marked, files this run has changed so far)."""
    data = reach.guard_run()
    if not data:
        return None, False, 0
    n = sum(1 for e in entries() if e.get("run") == data["run"] and e.get("op") in CHANGE_OPS)
    return data["run"], reach.is_marked(data), n


def verdict(op, path, to=None, own=False):
    """(kind, reason) for this change, from reach.classify, with the run's mark and count. `own` (#119, Alan 17-10-2026): the
    change is Alan's own note save from the dashboard, so no ask creaite run's mark or count applies to it."""
    _run, marked, count = (None, False, 0) if own else run_state()
    v = reach.classify(path, OP_KIND[op], marked=marked, count=count)
    if op == "move" and to is not None:
        v = reach.worst(v, reach.classify(to, "create", marked=marked, count=count))
    return v


def source_file(arg):
    """The --from file: inside system/staging/ of this vault, and a real file."""
    if not arg:
        raise SystemExit("creaite: --from <file in system/staging/> is required")
    p = Path(arg)
    p = Path(os.path.realpath(p if p.is_absolute() else paths.ROOT / p))
    if reach.parts_under(p, Path(os.path.realpath(paths.STAGING))) is None or not p.is_file():
        raise SystemExit("creaite: --from must be an existing file inside system/staging/")
    return p


def free_name(target):
    """`target`, or the first free "Name (2).ext", "Name (3).ext"… beside it: a create never overwrites."""
    final, n = target, 2
    while final.exists() or final.is_symlink():                  # never overwrite: a clash gets a number
        final = target.with_name(f"{target.stem} ({n}){target.suffix}")
        n += 1
    return final


def fingerprint(ch):
    """What an approval is bound to (BL-141): the operation, the real paths, the new content's hash and the target as it is now."""
    target = Path(os.path.realpath(resolve(ch["path"])))
    to = str(Path(os.path.realpath(resolve(ch["to"])))) if ch.get("to") else ""
    data = ch.get("data")
    before = sha(target) if target.is_file() else ""
    return sha_bytes(json.dumps([ch["op"], str(target).lower(), to.lower(), sha_bytes(data) if data is not None else "", before]).encode())


def check(path, edit=False):
    """The check command's answer for a create (or, with `edit`, a change) of `path`: {ok, kind, reason, path, exists}. Writes nothing."""
    p = resolve(path)
    kind, reason = verdict("edit" if edit else "create", path)
    out = {"ok": kind == "ordinary", "kind": kind, "reason": reason if kind != "sensitive" else f"needs approval: {reason}",
           "path": str(path), "exists": p.is_file()}
    if kind != "never":
        if edit and not p.is_file():
            out.update(ok=False, reason="there is no such file to change")
        if not edit and p.is_dir():
            out.update(ok=False, reason="that is a folder")
    return out


def record_request(ch, reason):
    """A sensitive change asked for in a run: kept for the server's card. Only an ask; never acted on without Alan's Approve."""
    run, _m, _n = run_state()
    if not run:
        return None
    REQUESTS.mkdir(parents=True, exist_ok=True)
    n = len(list(REQUESTS.glob(f"{run}-*.json"))) + 1
    req = {"run": run, "op": ch["op"], "path": stored(resolve(ch["path"])), "to": stored(resolve(ch["to"])) if ch.get("to") else None,
           "from": ch.get("from"), "why": ch.get("why", ""),
           "reason": reason, "at": now()}
    f = REQUESTS / f"{run}-{n:03d}.json"
    f.write_text(json.dumps(req, ensure_ascii=False), encoding="utf-8")
    return f


def _is_own(own, op, target):
    """#119: `own` counts only for an edit of a note (a create, another file or a settings file never)."""
    return bool(own) and op == "edit" and paths.is_note(target)


def _run_tag(run, own):
    """The run id the log line carries: none for Alan's own note save, else the given run or the one in progress."""
    return run if own else (run or run_state()[0])


def perform(ch, approval=None, via="cli", run=None, own=False):
    """Make one change: {op, path, to?, data?, from?, why}. Returns (code, message): 0 done, 1 refused, 3 needs approval. A
    sensitive change is made only with `approval`, a token the live server issued in this same process for exactly this change
    (reach.APPROVALS); a token from anywhere else, used, expired or for another change is refused. BL-265: the refusals, the
    verdict and the approval, the settings-file check, then one function per operation; every check in its old order."""
    op, why = ch["op"], re.sub(r"\s+", " ", ch.get("why") or "").strip()
    target = resolve(ch["path"]) if op in CHANGE_OPS else None
    refused = _refused(ch, op, why, target)
    if refused:
        return 1, refused
    # ===== #119 (Alan, 17-10-2026): `own`, honoured only for an edit of a note, by a route in the live server that builds the change
    # itself (never from a request body): Alan's typing is not an ask creaite run's change, so it carries no run tag and is not
    # counted against the run's limit. The never list, the settings-file check and the tiers are untouched. =====
    own = _is_own(own, op, target)
    kind, reason = verdict(op, ch["path"], ch.get("to"), own=own)
    if kind == "never":
        return 1, f"Not changed: {reason}."
    approved = False
    if kind == "sensitive":
        approved = bool(approval) and reach.APPROVALS.redeem(approval, fingerprint(ch))
        if not approved:
            return NEEDS, f"Needs approval: {reason}."
    before_bytes = target.read_bytes() if target.is_file() else b""
    problem = _settings_refused(ch, op, target, before_bytes)
    if problem:
        return 1, problem
    run = _run_tag(run, own)
    n_id = next_id()
    # ===== BL-194 (sprint-ask-creaite-access): the tier in the log (a label only; the decision above is unchanged) =====
    tier = "ordinary" if kind == "ordinary" else reach.tier(ch["path"], OP_KIND[op], before_bytes, ch.get("data"), to=ch.get("to"))[0]
    # ===== end BL-194 =====
    base = {"id": n_id, "at": now(), "why": why, "via": via, "tier": tier, **({"run": run} if run else {}),
            **({"approved": True} if approved else {})}
    if op == "create":
        return _do_create(ch, target, base, n_id)
    backup = _backup(ch, target, base, n_id, joinable=(op, kind, approved, run) == ("edit", "ordinary", False, None))
    do = {"edit": _do_edit, "move": _do_move, "delete": _do_delete}[op]
    return do(ch, target, base, n_id, backup, before_bytes)


# ===== #119: one backup per editing session =====
# A save may name its editing session ("<stored path>:<the page's session id>"). The session's first save is backed up and logged
# as always; a later save of the same session reuses that backup, so Undo of the latest save puts back the text as it was before
# the session. Only an ordinary edit (never one Alan approved on the card, a settings or permission file, or one made while an ask
# creaite run is in progress) of the same file, by the same route, under 5 minutes after the session's last save, with nothing else
# having changed the file since, joins a session. Anything else gets its own backup, as before. The log keeps a hash of the token.
SESSION_IDLE = 300                              # seconds without a save that end an editing session
SESSION_MAX = 1024                              # characters in a session token at most
# #175 (M2 of Team Cap's #119 review; cap kept, Alan 17-10-2026): a session also ends 30 minutes after its first save, so one
# Activity Restore (a file-level restore to the session's start; the editor's own Cmd+Z is the everyday undo) goes back at most
# about 30 minutes. The next save starts a new session with its own backup (the text as the last session left it), so Restore
# goes back one session at a time: the newer session first, then the older one.
SESSION_MAX_AGE = 1800                          # seconds from a session's first save after which the next save starts a new one


def session_key(ch, target):
    """The log's key for the save's editing session (16 hex of the token's hash), or None: no token, or one not for this file."""
    tok = ch.get("session")
    here = stored(target) + ":"
    if not isinstance(tok, str) or len(tok) > SESSION_MAX or not tok.startswith(here) or len(tok) == len(here):
        return None
    return sha_bytes(tok.encode("utf-8"))[:16]


def _backup(ch, target, base, n_id, joinable):
    """The earlier version of the file, kept first, always: called by perform after every check has passed, unchanged. A new copy
    in system/backups/files/changes/<n>/, unless (#119) the change is `joinable` (an ordinary edit, not approved on the card,
    outside any run), the file isn't a settings or permission file and the save names its editing session for this file: then the
    session's key goes in `base` (the log line), and a later save of that session reuses the session's one backup."""
    key = session_key(ch, target) if joinable and not is_settings_file(target) else None
    if key:
        base["session"] = key
        joined = session_backup(key, target, base["via"])
        if joined:
            return joined
    keep = CHANGES / f"{n_id:04d}"
    keep.mkdir(parents=True, exist_ok=True)
    backup = keep / target.name
    shutil.copy2(target, backup)                                   # the earlier version first, always
    return backup


def _same_session(last, key, here, via):
    """Whether the log entry `last` is an ordinary edit of `here` in session `key` by route `via`, outside any run, with a backup."""
    return bool(last) and last.get("op") == "edit" and last.get("path") == here and last.get("session") == key and \
        last.get("via") == via and last.get("tier") == "ordinary" and not last.get("approved") and not last.get("run") and \
        bool(last.get("backup"))


def _age(entry):
    """Seconds since a log entry's `at`, or None when it can't be read."""
    try:
        return (datetime.now() - datetime.strptime(str(entry.get("at")), "%Y-%m-%d %H:%M:%S")).total_seconds()
    except ValueError:
        return None


def _session_first(es, last):
    """#175: the session's first save: the log entry whose id is the number of the backup folder `last` shares (changes/<n>/),
    an edit of the same file in the same session with the same backup; None when it isn't in the log."""
    try:
        n = int(Path(str(last["backup"])).parent.name)
    except (KeyError, ValueError):
        return None
    return next((e for e in es if e.get("id") == n and e.get("op") == "edit" and e.get("path") == last.get("path") and
                 e.get("session") == last.get("session") and e.get("backup") == last.get("backup")), None)


def session_backup(key, target, via):
    """The backup of the editing session this save continues, or None. The last logged change to this file (as its path, or as
    where a move went) must be an ordinary edit of the same session by the same route, outside any run, under SESSION_IDLE seconds
    ago, its result still the file as it is now, and its backup still the earlier version it logged; and (#175) the session's
    first save must be in the log and under SESSION_MAX_AGE seconds ago."""
    here = stored(target)
    es = entries()
    last = next((e for e in reversed(es) if here in (e.get("path"), e.get("to"))), None)
    if not _same_session(last, key, here, via):
        return None
    age, first = _age(last), _session_first(es, last)
    started = _age(first) if first else None
    if age is None or started is None or not 0 <= age < SESSION_IDLE or not 0 <= started < SESSION_MAX_AGE:
        return None
    backup = paths.resolve(last["backup"])
    if sha(target) != last.get("after") or not backup.is_file() or sha(backup) != last.get("before"):
        return None
    return backup


def session_saves(todo, last):
    """#119: the earlier saves, not yet undone, of the editing session whose latest save is `last` (they share its one backup),
    undone with it; [] for any other change."""
    if last["op"] != "edit" or not last.get("session"):
        return []
    return [e["id"] for e in todo if e["id"] < last["id"] and e.get("op") == "edit" and e.get("session") == last["session"]
            and e.get("backup") == last.get("backup") and e.get("path") == last["path"]]
# ===== end #119 =====


# ===== #175 (L1 of Team Cap's #119 review): the Notes tab's old typed drafts, cleared once they can't be used =====
# Since #119 the Notes tab keeps no draft: it writes the note itself. Drafts it kept before (system/staging/drafts/notes/<16 hex of
# the note's path>.json, and a <…>.json.tmp left by an interrupted write) are no longer read or removed by anything, yet they go into
# the daily zip and make reach.confidential_places hold back the search index and the backups. The live server calls this at
# start-up: each such file is moved into ONE backup folder, system/backups/files/changes/<n>/, with one line in the files log (op
# "cleanup": not a change Activity lists or Restore touches; Tidy up removes the folder after backups.file_change_days, 90). Only
# those names, only regular files directly in that folder: never the Capture drawer's capture-*.json, never a symlink, a subfolder
# or anything else. A draft reach.confidential_places counts as a confidential note's typed copy is left where it is, never moved
# and never deleted (Alan, 17-10-2026: moving it into the backups would let a held run read it once no note is confidential).
# Nothing to do: nothing is written.
NOTE_DRAFT = re.compile(r"[0-9a-f]{16}\.json(\.tmp)?")


def retire_note_drafts(folder=None):
    """Move the Notes tab's old drafts (NOTE_DRAFT names except leftover .json.tmp files, which always stay where they are, regular
    files directly in `folder`, default notes.DRAFT_DIR), other than a confidential note's, into one backup folder and log it once. Returns how many were moved."""
    import notes
    d = Path(folder) if folder else notes.DRAFT_DIR
    found = [f for f in (d.iterdir() if d.is_dir() and not d.is_symlink() else [])
             if NOTE_DRAFT.fullmatch(f.name) and not f.name.endswith(".tmp") and f.is_file() and not f.is_symlink()]
    held = set(reach.confidential_places()) if found else set()   # a leftover .tmp is never moved: confidential_places reads only *.json
    found = sorted(f for f in found if Path(os.path.realpath(f)) not in held)
    if not found:
        return 0
    n_id = next_id()
    keep = CHANGES / f"{n_id:04d}"
    keep.mkdir(parents=True, exist_ok=True)
    for f in found:
        shutil.copy2(f, keep / f.name)                              # the copy first, always
        f.unlink()
    log({"id": n_id, "at": now(), "op": "cleanup", "path": paths.rel(d), "files": [f.name for f in found],
         "backup": paths.rel(keep), "via": "server", "tier": "ordinary",
         "why": "#175: the Notes tab's old typed drafts, no longer used since #119"})
    return len(found)
# ===== end #175 =====


def _refused(ch, op, why, target):
    """Why the change can't be made at all, before its verdict, or None."""
    if op not in CHANGE_OPS:
        return f"Not changed: {op} isn't a change filechange makes."
    if op != "create" and (not why or len(why) > 300):
        return "Not changed: say why, in up to 300 characters (--why)."
    if op == "create":
        if target.is_dir():
            return "Not created: that is a folder."
    elif not target.is_file():
        return "Not changed: there is no such file." if op == "edit" else f"Not {'moved' if op == 'move' else 'deleted'}: there is no such file."
    if op == "move" and resolve(ch["to"]).exists():
        return f"Not moved: {ch['to']} already exists, and creaite never overwrites."
    return None


def _settings_refused(ch, op, target, before_bytes):
    """A permission or settings file is only ever changed, and its new content is checked first, whatever is approved."""
    if is_settings_file(target) or (op == "move" and is_settings_file(resolve(ch["to"]))):
        if op in ("move", "delete"):
            return "Not changed: a permission or settings file is changed, never deleted or moved (its safety entries would go)."
        problem = settings_check(target, ch["data"], before_bytes)
        if problem:
            return f"Not changed: {problem}. The file is as it was."
    return None


def _do_create(ch, target, base, n_id):
    final = free_name(target)
    made = [stored(d) for d in reversed([p for p in final.parents if not p.exists()])]
    final.parent.mkdir(parents=True, exist_ok=True)
    tmp = final.with_name(f".{final.name}.part")
    tmp.write_bytes(ch["data"])
    os.replace(tmp, final)
    log({**base, "op": "create", "path": stored(final), "after": sha(final), "made_dirs": made})
    return 0, f"Created {stored(final)} (change {n_id})."


def _do_edit(ch, target, base, n_id, backup, before_bytes):
    tmp = target.with_name(f".{target.name}.part")
    tmp.write_bytes(ch["data"])
    os.replace(tmp, target)
    recheck = settings_check(target, target.read_bytes(), before_bytes) if is_settings_file(target) else None
    if recheck:                                                # re-read and re-checked: put back if it fails
        shutil.copy2(backup, target)
        return 1, f"Not changed: {recheck}. The file is as it was."
    if is_settings_file(target):
        with open(paths.SETTINGS_LOG, "a", encoding="utf-8") as f:     # the settings log, as every settings change has
            f.write(json.dumps({"at": now(), "key": f"file:{stored(target)}", "old": None, "new": "changed"}, ensure_ascii=False) + "\n")
    log({**base, "op": "edit", "path": stored(target), "backup": paths.rel(backup), "before": sha(backup), "after": sha(target)})
    return 0, (f"Changed {stored(target)} (change {n_id}; the earlier version is {paths.rel(backup)}). "
               "Undo it with: python3 system/scripts/filechange.py undo")


def _do_move(ch, target, base, n_id, backup, before_bytes):
    dst = resolve(ch["to"])
    made = [stored(d) for d in reversed([p for p in dst.parents if not p.exists()])]
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(target), str(dst))
    log({**base, "op": "move", "path": stored(target), "to": stored(dst), "backup": paths.rel(backup), "after": sha(dst), "made_dirs": made})
    return 0, f"Moved {stored(target)} to {stored(dst)} (change {n_id}). Undo it with: python3 system/scripts/filechange.py undo"


def _do_delete(ch, target, base, n_id, backup, before_bytes):
    target.unlink()
    log({**base, "op": "delete", "path": stored(target), "backup": paths.rel(backup), "before": sha(backup)})
    return 0, (f"Deleted {stored(target)} (change {n_id}; a copy is {paths.rel(backup)}). "
               "Undo it with: python3 system/scripts/filechange.py undo")


# ── permission and settings files: checked before and re-checked after writing, whatever is approved (BL-141) ──
def settings_kind(target):
    """"claude", "config", "json" or "mcp" for a permission or settings file; None for anything else."""
    p = Path(os.path.realpath(target))
    vault = Path(os.path.realpath(paths.ROOT))
    for base in (vault, reach.home()):
        rel = reach.parts_under(p, base)
        if rel is None:
            continue
        low = [x.lower() for x in rel]
        if low in ([".claude", "settings.json"], [".claude", "settings.local.json"]):
            return "claude"
        if base == vault and low == [".mcp.json"]:
            return "mcp"
        if base == vault and low == ["system", "config", "settings.json"]:
            return "config"
        if base == vault and p.suffix.lower() == ".json" and (low[:2] == ["system", "config"] or low == ["system", "templates", "settings-defaults.json"]):
            return "json"
    return None


def is_settings_file(target):
    """Whether the target is a permission or settings file, whose new content is checked before and after writing (settings_check)."""
    return settings_kind(target) is not None


def settings_check(target, new_bytes, before_bytes):
    """Why writing new_bytes over a permission or settings file is refused whatever is approved (permissions.settings_problem), or
    None. Run on the new content before writing, and again on the file as written."""
    kind = settings_kind(target)
    if kind is None:
        return None
    import permissions
    if kind == "mcp":
        return permissions.settings_problem("mcp", {}, {})
    try:
        before = json.loads(before_bytes.decode("utf-8")) if before_bytes else {}
    except (ValueError, UnicodeDecodeError):
        before = {}
    try:
        after = json.loads(new_bytes.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return "the new file isn't valid JSON"
    return permissions.settings_problem(kind, before if isinstance(before, dict) else {}, after)


def cli_change(op, path, why, via, src=None, to=None):
    """Make one change from the command line through perform, with no approval. A sensitive one is recorded as a request for the live
    server's card (BL-141). Prints the outcome; returns the exit code (3: needs approval)."""
    ch = {"op": op, "path": path, "why": why, **({"to": to} if to else {})}
    if src is not None:
        f = source_file(src)
        ch.update(data=f.read_bytes(), **{"from": paths.rel(f)})
    code, msg = perform(ch, None, via)
    if code == NEEDS:
        recorded = record_request(ch, msg[len("Needs approval: "):].rstrip("."))
        msg += (" It is on the card for Alan to approve or decline; nothing was changed." if recorded else
                " ask creaite shows such a change on a card for approval; from Terminal, make it yourself.")
    print(msg)
    return code


def cmd_undo(which):
    """Undo the latest change (or the one numbered `which`), if nothing has changed the file since. BL-265: one function per
    kind of change, each saying what it did or why it left the file alone."""
    es = entries()
    undone = {e.get("undoes") for e in es if e.get("op") == "undo"}
    todo = [e for e in es if e.get("op") in CHANGE_OPS and e["id"] not in undone]
    last = next((e for e in reversed(todo) if which is None or e["id"] == which), None)
    if not last:
        print("Nothing to undo.")
        return 0
    p = resolve(last["path"])
    undo = {"create": _undo_create, "move": _undo_move, "delete": _undo_delete}.get(last["op"], _undo_edit)
    note, refusal = undo(last, p)
    if refusal:
        print(refusal)
        return 1
    n = next_id(es)
    # #119: undoing an editing session's latest save puts back the text from before the session, so its earlier saves (the same
    # session, sharing its one backup) are undone with it
    whole = session_saves(todo, last)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        for i, undoes in enumerate([last["id"]] + whole):
            f.write(json.dumps({"id": n + i, "at": now(), "op": "undo", "undoes": undoes, "path": last["path"]}, ensure_ascii=False) + "\n")
    reach._debug("info", f"undo of change {last['id']}: {last['path']} {note}" + (f" (and {len(whole)} earlier saves)" if whole else ""))
    print(f"{last['path']} {note} (change {last['id']} undone" +
          (f", with the earlier saves of its editing session: {', '.join(str(i) for i in whole)}" if whole else "") + ").")
    return 0


def _remove_made_dirs(last):
    for d in reversed(last.get("made_dirs") or []):
        dp = resolve(d)
        if dp.is_dir() and not any(dp.iterdir()):
            dp.rmdir()


def _undo_create(last, p):
    """(what was done, None) or (None, why it was left alone)."""
    if not p.exists():
        return "was already gone", None
    if sha(p) != last["after"]:
        return None, f"Not undone: {last['path']} has been changed since creaite made it, so it is left alone."
    p.unlink()
    _remove_made_dirs(last)
    return "removed", None


def _undo_move(last, p):
    dst, src = resolve(last["to"]), p
    if not dst.exists() or sha(dst) != last["after"] or src.exists():
        return None, f"Not undone: {last['to']} has been changed since, or {last['path']} is taken, so both are left alone."
    src.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(dst), str(src))
    _remove_made_dirs(last)
    return "put back", None


def _backup_gone(last):
    """BL-323: Tidy up removes file-change backups after backups.file_change_days (90); the files log keeps the line."""
    if last.get("backup") and not paths.resolve(last["backup"]).exists():
        return (f"Not undone: the backup of change {last['id']} has gone (file-change backups are kept for 90 days, "
                f"backups.file_change_days). The files log keeps the line.")
    return None


def _undo_delete(last, p):
    if _backup_gone(last):
        return None, _backup_gone(last)
    if p.exists():
        return None, f"Not undone: {last['path']} exists again, so it is left alone. The copy is {last['backup']}."
    p.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(paths.resolve(last["backup"]), p)
    return "restored", None


def _undo_edit(last, p):
    if _backup_gone(last) and p.exists() and sha(p) == last.get("after"):
        return None, _backup_gone(last)
    if not p.exists() or sha(p) != last["after"]:
        return None, f"Not undone: {last['path']} has been changed since, so it is left alone. The earlier version is {last['backup']}."
    shutil.copy2(paths.resolve(last["backup"]), p)
    return "put back", None


def changes(days=None):
    """The changes made through this script (newest last), each with `undone`; only the last `days` days when given."""
    es = entries()
    undone = {e.get("undoes") for e in es if e.get("op") == "undo"}
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d") if days else ""
    return [{**e, "undone": e["id"] in undone} for e in es if e.get("op") in CHANGE_OPS and e.get("at", "") >= since]


def cmd_list(as_json, days=None):
    """The list command: the changes made through this script (the last `days` days, if given), in order, or as JSON. Writes nothing."""
    shown = changes(days)
    if as_json:
        print(json.dumps(shown, indent=2, ensure_ascii=False))
        return 0
    for e in shown:
        print(f"{e['at']}  #{e['id']} {'(undone) ' if e['undone'] else ''}{TIER_WORD.get(e.get('tier'), '')}{e['op']} {e['path']}{(' → ' + e['to']) if e.get('to') else ''} — {e.get('why') or ''}")
    if not shown:
        print("No files have been changed through filechange.py.")
    return 0


def main(argv):
    """The command line: check, create, edit, move, delete, undo, list (see the module's description). BL-265: the options
    parsed once, then the command."""
    if not argv:
        print(__doc__)
        return 2
    cmd, args = argv[0], argv[1:]
    opts, pos, why, via = _cli_options(args)
    if cmd == "check" and pos:
        print(json.dumps(check(pos[0], edit="--edit" in args), ensure_ascii=False))
        return 0
    if cmd in ("create", "edit") and pos:
        return cli_change(cmd, pos[0], why, via, src=opts.get("--from"))
    if cmd == "move" and len(pos) == 2:
        return cli_change("move", pos[0], why, via, to=pos[1])
    if cmd == "delete" and pos:
        return cli_change("delete", pos[0], why, via)
    if cmd == "undo":
        return cmd_undo(int(pos[0]) if pos else None)
    if cmd == "list":
        return cmd_list("--json" in args, int(opts["--days"]) if str(opts.get("--days", "")).isdigit() else None)
    print(__doc__)
    return 2


def _cli_options(args):
    """(options, positional arguments, why, via). A change made while an ask creaite run is in progress is the run's."""
    opts = {a: args[i + 1] for i, a in enumerate(args[:-1]) if a.startswith("--") and a not in ("--edit", "--json")}
    pos = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or not args[i - 1].startswith("--") or args[i - 1] in ("--edit", "--json"))]
    why = re.sub(r"\s+", " ", opts.get("--why") or "").strip()
    via = opts.get("--via", "cli") if opts.get("--via") in ("cli", "dashboard", "ask") else "cli"
    if run_state()[0]:
        via = "ask"
    return opts, pos, why, via


if __name__ == "__main__":
    try:
        import log as debuglog  # BL-102: the debug log (not `log`: some scripts have a function of that name); a script runs without it
    except ImportError:
        debuglog = None
    sys.exit(debuglog.main("filechange.py", main, sys.argv[1:]) if debuglog else main(sys.argv[1:]))
