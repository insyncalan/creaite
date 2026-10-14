"""creaite reach — the one place that decides what ask creaite may touch (BL-141). Standard library only.

    classify(path, operation, marked=False, count=0) -> (kind, reason)

kind is "ordinary" (done at once, backed up, logged, undoable), "sensitive" (only on Alan's Approve, on the one card) or "never"
(refused whatever is asked). operation is read, create, change, move or delete. The path is expanded (~) and resolved first, so a
symlink or `..` is judged by where it really points; names are compared without regard to case (macOS is case-insensitive).
`marked` is True when the run has read outside content (mail, Teams, a web page, a transcript, a document); `count` is how many
files this request has already changed.

The reach is the vault, the projects root and the home folder. Outside it is never. Inside it, NEVER (one table, below) lists the
places that are refused: secrets and system areas for everything, and the database, the engine, creaite's own records and the
places that run code for any change. The database and the engine stay behind their own commands (tracker.py apply; an update).

Commands (read only):
  classify <path> <operation> [--marked] [--count N]    JSON {kind, reason}
  never                                                 the never list, one row a line
"""
import fnmatch
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

OPERATIONS = ("read", "create", "change", "move", "delete")
WRITES = ("create", "change", "move", "delete")
BULK = 10                     # more than this many files changed in one request is sensitive (Alan's default, 10-10-2026)

SECRET = "it holds secrets (keys, passwords, sign-ins)"
SYSTEM = "it is part of the operating system"
BEHIND = "the database, the engine and creaite's rules change only through their own commands (tracker.py apply; an update)"
RECORD = "it is creaite's own record or a generated file, written only by creaite's scripts"
RUNS_CODE = "it runs commands when you log in or open Terminal"

# The never list. (base, pattern, operations, reason): base is "home" (below the home folder), "vault" (below the vault) or "abs"
# (an absolute path); the pattern is matched one path part at a time (shell wildcards, case ignored) and covers everything below it.
# operations "all" bars reading too; "write" bars create, change, move and delete.
NEVER = (
    ("home", ".ssh", "all", SECRET), ("home", ".aws", "all", SECRET), ("home", ".gnupg", "all", SECRET),
    ("home", ".config/gcloud", "all", SECRET), ("home", ".config/gh", "all", SECRET), ("home", ".config/op", "all", SECRET),
    ("home", ".kube", "all", SECRET), ("home", ".docker", "all", SECRET), ("home", ".netrc", "all", SECRET),
    ("home", ".git-credentials", "all", SECRET), ("home", ".npmrc", "all", SECRET), ("home", ".pypirc", "all", SECRET),
    ("home", ".password-store", "all", SECRET), ("home", "Library/Keychains", "all", SECRET),
    ("home", "Library/Group Containers/*1password*", "all", SECRET), ("home", "Library/Application Support/1Password", "all", SECRET),
    ("home", "Library/Application Support/Bitwarden", "all", SECRET),
    ("home", "Library/Application Support/Google/Chrome", "all", SECRET), ("home", "Library/Application Support/Firefox", "all", SECRET),
    ("home", "Library/Application Support/Microsoft Edge", "all", SECRET),
    ("home", "Library/Application Support/BraveSoftware", "all", SECRET), ("home", "Library/Application Support/Arc", "all", SECRET),
    ("home", "Library/Safari", "all", SECRET), ("home", "Library/Containers/com.apple.Safari", "all", SECRET),
    ("home", "Library/Cookies", "all", SECRET), ("home", ".mozilla", "all", SECRET), ("home", ".config/google-chrome", "all", SECRET),
    ("home", ".claude.json", "all", SECRET), ("home", ".claude/.credentials.json", "all", SECRET),
    ("abs", "/System", "all", SYSTEM), ("abs", "/Library", "all", SYSTEM), ("abs", "/usr", "all", SYSTEM), ("abs", "/bin", "all", SYSTEM),
    ("abs", "/sbin", "all", SYSTEM), ("abs", "/etc", "all", SYSTEM), ("abs", "/private/etc", "all", SYSTEM), ("abs", "/opt", "all", SYSTEM),
    ("abs", "/Applications", "all", SYSTEM), ("abs", "/dev", "all", SYSTEM),
    ("vault", "system/tracker.db*", "write", BEHIND), ("vault", "system/scripts", "write", BEHIND),
    ("vault", "system/creaite-rules.md", "write", BEHIND), ("vault", "VERSION", "write", BEHIND), ("vault", "system/releases", "write", BEHIND),
    ("vault", "system/backups", "write", RECORD), ("vault", "system/logs", "write", RECORD), ("vault", "system/history", "write", RECORD),
    ("vault", "system/guard", "write", RECORD), ("vault", "system/config/files-log.jsonl", "write", RECORD),
    ("vault", "system/config/permissions-log.jsonl", "write", RECORD), ("vault", "system/config/settings-log.jsonl", "write", RECORD),
    ("vault", "system/processed.txt", "write", RECORD), ("vault", "system/staging/run-log.txt", "write", RECORD),
    ("vault", "system/staging/uploads/ask", "write", RECORD), ("vault", "system/staging/proposed-*", "write", RECORD),
    ("vault", "system/staging/applied", "write", RECORD), ("vault", "system/staging/ask", "write", RECORD),
    ("vault", "system/staging/*.json", "write", RECORD), ("vault", "system/staging/*.jsonl", "write", RECORD),
    ("vault", "system/staging/*.txt", "write", RECORD), ("vault", "dashboard.html", "write", RECORD),
    ("vault", "tracker-view.xlsx", "write", RECORD), ("vault", ".git", "write", RECORD), ("vault", ".creaite-dev", "write", RECORD),
    ("home", ".zshrc", "write", RUNS_CODE), ("home", ".zprofile", "write", RUNS_CODE), ("home", ".zshenv", "write", RUNS_CODE),
    ("home", ".zlogin", "write", RUNS_CODE), ("home", ".bashrc", "write", RUNS_CODE), ("home", ".bash_profile", "write", RUNS_CODE),
    ("home", ".bash_login", "write", RUNS_CODE), ("home", ".profile", "write", RUNS_CODE), ("home", ".config/fish", "write", RUNS_CODE),
    ("home", "Library/LaunchAgents", "write", RUNS_CODE), ("home", ".local/bin", "write", RUNS_CODE), ("home", "bin", "write", RUNS_CODE),
)

# Sensitive kind 1: what changes what ask creaite may do (permission and settings files, the registers, the memory files)
SETTINGS_FILES = ((("vault", ".claude"), "except skills"), (("vault", ".mcp.json"), ""), (("vault", "system/config"), ""),
                  (("vault", "system/templates/settings-defaults.json"), ""), (("vault", "CLAUDE.md"), ""), (("home", ".claude"), ""))
OFFICE = (".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".pdf", ".msg", ".eml", ".vtt", ".rtf", ".pages", ".numbers", ".key")
OTHERS_FOLDERS = ("transcripts", "minutes", "weekly_reports", "client_reports", "steerco", "adhoc_documents")


def home():
    """The home folder's real path: one of the places in reach (BL-141)."""
    return Path(os.path.expanduser("~")).resolve()


def real(path):
    """The real path: `~` expanded, a stored projects/… path mapped (paths.resolve), anything else relative to the vault, then
    symlinks and `..` resolved (a file that doesn't exist yet is resolved through its folder)."""
    s = os.path.expanduser(str(path).replace("\\", "/"))
    p = Path(s) if Path(s).is_absolute() else paths.resolve(s)
    return Path(os.path.realpath(p))


def parts_under(p, base):
    """p's parts below base, compared without case; None if p isn't base or below it."""
    a, b = [x.lower() for x in Path(p).parts], [x.lower() for x in Path(base).parts]
    return list(Path(p).parts[len(b):]) if a[:len(b)] == b else None


def roots():
    """(name, real path) of the places in reach: the vault, the projects root (when it is outside the vault) and the home folder."""
    out = [("vault", Path(os.path.realpath(paths.ROOT)))]
    if paths.external():
        out.append(("projects", Path(os.path.realpath(paths.projects_root()))))
    out.append(("home", home()))
    return out


def matches(rel_parts, pattern):
    """Whether a path's parts below its base match a never-list or settings-file pattern: part by part, shell wildcards, case ignored; a
    pattern naming a folder covers everything in it."""
    pat = [x for x in pattern.strip("/").split("/") if x]
    return len(rel_parts) >= len(pat) and all(fnmatch.fnmatchcase(r.lower(), q.lower()) for r, q in zip(rel_parts, pat))


def base_parts(p, base):
    """p's parts below a table row's base ("vault", "home", or "abs" for an absolute pattern); None when p isn't under it."""
    if base == "abs":
        return list(Path(p).parts[1:])
    root = Path(os.path.realpath(paths.ROOT)) if base == "vault" else home()
    return parts_under(p, root)


def never_reason(p, operation):
    """The never-list row that bars this operation on the real path p, as its reason; else None."""
    for base, pattern, ops, reason in NEVER:
        if ops == "write" and operation not in WRITES:
            continue
        rel = base_parts(p, base)
        if rel is not None and matches(rel, pattern):
            return reason
    return None


def in_reach(p):
    """The places in reach (vault, projects, home) that hold the real path p; empty when it is outside them all."""
    return [name for name, r in roots() if parts_under(p, r) is not None]


def project_kind(p):
    """(code, kind) when p is inside a project's transcripts, minutes or report folders; (code, None) elsewhere in a project; None
    outside the projects."""
    try:
        area = paths.project_area(p)
    except (OSError, LookupError, ValueError):
        return None
    if area is None:
        return None
    code = area[0]
    for kind in OTHERS_FOLDERS:
        try:
            f = Path(os.path.realpath(paths.folder(code, kind)))
        except (LookupError, KeyError, OSError):
            continue
        if parts_under(p, f) is not None:
            return code, kind
    return code, None


def settings_reason(p):
    """Why changing the real path p changes what ask creaite may do (a permission, settings or memory file, a register, a project's
    CLAUDE.md), or None. Such a change waits on Alan's card (BL-141)."""
    for (base, pattern), note in SETTINGS_FILES:
        rel = base_parts(p, base)
        if rel is None or not matches(rel, pattern):
            continue
        if note == "except skills" and len(rel) > 1 and rel[1].lower() == "skills":
            continue
        if base == "home" and parts_under(p, Path(os.path.realpath(paths.ROOT))) is not None:
            continue
        return "it changes what ask creaite may do (a permission, settings or memory file)"
    try:
        for f in (paths.REGISTER, paths.PEOPLE_REGISTER):
            if str(p).lower() == os.path.realpath(f).lower():
                return "it changes what ask creaite may do (a register)"
        area = paths.project_area(p)
        if area and len(area[1]) == 1 and area[1][0].lower() == "claude.md":
            return "it changes what ask creaite may do (a project's memory file)"
    # BL-228: a path outside every project is no register or memory file; the settings files above were checked
    except (OSError, LookupError, ValueError):
        pass
    return None


def classify(path, operation, marked=False, count=0):
    """("ordinary" | "sensitive" | "never", reason). See the module's description. BL-265: the never checks, then the
    reasons a change needs approval, each in the order it always had (dev/tests/test_guard_pinned.py)."""
    if operation not in OPERATIONS:
        raise ValueError(f"operation is one of {', '.join(OPERATIONS)}")
    try:
        p = real(path)
    except (OSError, ValueError, RuntimeError) as e:
        return "never", f"the path can't be worked out ({type(e).__name__})"
    where = in_reach(p)
    never = _never_verdict(p, operation, where)
    if never:
        return "never", never
    if operation == "read":
        return "ordinary", ""
    reasons = _approval_reasons(p, operation, where, marked, count)
    return ("sensitive", reasons[0]) if reasons else ("ordinary", "")


def _never_verdict(p, operation, where):
    """Why `p` is never touched for this operation, or None: out of reach, the never list, a .git folder, a folder creaite
    skips, an online-only OneDrive file."""
    if not where:
        return never_reason(p, "read") or "it is outside the vault, the projects folder and your home folder"
    why = never_reason(p, operation)
    if why:
        return why
    if operation in WRITES and any(x.lower() == ".git" for x in p.parts):
        return "it is inside a .git folder, whose hooks run commands"
    below = parts_under(p, Path(os.path.realpath(paths.projects_root())))          # _Archive, _Templates, 99 System (BL-93, BL-112)
    skipped = {n.lower() for n in paths.skipped_names()}
    hit = next((x for x in (below or ()) if x.lower() in skipped), None)
    if hit:
        return f"{hit} is never read or written by creaite"
    if operation in ("read", "change", "move", "delete") and p.is_file() and paths.is_online_only(p):
        return "it is an online-only OneDrive file (not on this device): creaite never downloads one"
    return None


def _approval_reasons(p, operation, where, marked, count):
    """Every reason a write needs Alan's approval, the first of which is shown."""
    reasons = []
    s = settings_reason(p)
    if s:
        reasons.append(s)
    if "vault" not in where and "projects" not in where:
        reasons.append("it is outside the vault and the projects folder")
    exists = p.exists()
    if operation in ("move", "delete") and exists:
        reasons.append("it deletes or moves a file that exists" if operation == "delete" else "it moves or renames a file that exists")
    if count >= BULK:
        reasons.append(f"this request has already changed {count} files (more than {BULK} need approval)")
    if exists and operation in ("change", "move", "delete"):
        reasons += _whose_file(p)
    if marked:
        staging = parts_under(p, Path(os.path.realpath(paths.STAGING)))
        if staging is None:
            reasons.append("this request has read outside content (mail, Teams, a transcript, a document or a web page)")
    return reasons


def _whose_file(p):
    """A reason when an existing file may be someone else's: a meeting record or report, a document, another user's."""
    area = project_kind(p)
    if area is not None and area[1]:
        return ["it is a meeting record or a report that may have been sent, or another person's words"]
    if area is not None and p.suffix.lower() in OFFICE:
        return ["it is a document that may be another person's (a client's or a shared file)"]
    try:
        if hasattr(os, "getuid") and p.stat().st_uid != os.getuid():
            return ["it is owned by another user"]
    except OSError:  # BL-228: a file that isn't there yet has no other owner
        pass
    return []


# ===== BL-09: the one exception for _Archive (agreed, Alan, 14-10-2026) =====
# _Archive stays on ask creaite's never list for reading and writing (classify above is unchanged: never). The only thing that may
# move a folder into or out of it is tracker.py apply running an approved archive, restore or rename of an old zz Archive folder:
# its `move` file operation asks archive_move_problem, and nothing else calls it. A model can't use it (filechange.py and the hook
# go through classify, which says never), and it covers only these whole-folder shapes, nothing inside a folder:
#   archive  <projects root>/<project folder>      -> <projects root>/_Archive/<same or numbered name>
#   restore  <projects root>/_Archive/<folder>     -> <projects root>/<same or numbered name>
#   rename   <projects root>[/<engagement>]/zz Archive -> the same folder's _Archive (Health's Fix it, BL-09)
ARCHIVE_MOVES = ("archive", "restore", "rename")


def _top_folder(name):
    """A project or engagement folder's own name: not hidden, not _-prefixed (_Archive, _Templates, _Portfolio), not skipped."""
    return not name.startswith((".", "_")) and name.lower() not in {x.lower() for x in paths.skipped_names()}


def _in_archive(parts):
    """parts are <_Archive>/<a project folder>."""
    return len(parts) == 2 and parts[0].lower() == paths.ARCHIVE.lower() and _top_folder(parts[1])


def _project_folder(parts):
    """parts are one project or engagement folder in the projects root."""
    return len(parts) == 1 and _top_folder(parts[0])


def _old_archive_rename(pa, pb):
    """pa is a zz Archive folder (in the root or one engagement) and pb the _Archive beside it."""
    same_place = len(pa) == len(pb) and len(pa) in (1, 2) and pa[:-1] == pb[:-1] and (len(pa) == 1 or _top_folder(pa[0]))
    return same_place and pa[-1].lower() == paths.OLD_ARCHIVE.lower() and pb[-1] == paths.ARCHIVE


def _move_shape(kind, pa, pb):
    """Whether the parts below the projects root (pa from, pb to) are the whole-folder move `kind`."""
    if kind == "archive":
        return _project_folder(pa) and _in_archive(pb)
    if kind == "restore":
        return _in_archive(pa) and _project_folder(pb)
    return _old_archive_rename(pa, pb)


def archive_move_problem(src, dst, kind):
    """None when moving the folder `src` to `dst` (stored paths, never mapped into _Archive) is the `kind` of move above; else why
    not. Neither end may be a symlink; the source must be a folder that exists and the destination must not exist."""
    if kind not in ARCHIVE_MOVES:
        return f"a folder move is an archive, a restore or a rename of an old archive folder (got {kind!r})"
    if any(".." in Path(str(x)).parts for x in (src, dst)):
        return "a path with .. in it"
    root = Path(os.path.realpath(paths.projects_root()))
    a, b = paths.resolve(src, archived=False), paths.resolve(dst, archived=False)
    if a.is_symlink() or b.is_symlink():
        return "a folder move never follows a symlink"
    pa = parts_under(Path(os.path.realpath(a)), root)
    pb = parts_under(Path(os.path.realpath(b.parent)) / b.name, root)
    if not pa or not pb:
        return "a folder move stays inside the projects folder"
    if not _move_shape(kind, pa, pb):
        return f"that isn't a whole-folder {kind} (projects folder and {paths.ARCHIVE} only)"
    if not a.is_dir():
        return f"{src} isn't a folder that exists"
    if b.exists():
        return f"{dst} already exists; a folder move never overwrites"
    return None
# ===== end BL-09 =====


def worst(*verdicts):
    """The strictest of several (kind, reason) verdicts: never over sensitive over ordinary."""
    order = {"never": 2, "sensitive": 1, "ordinary": 0}
    return max(verdicts, key=lambda v: order[v[0]])


# ===== BL-194 (sprint-ask-creaite-access): the risk tier of a change on the card =====
# Display and logging only: a tier never decides whether a change is made. classify() (and the never list, the guard hook, the
# one-time approvals and permissions.settings_problem) decide that, exactly as before. Every change on the card is "sensitive"
# (a yellow band) or "high" (High-risk, a red band): a permission file, or any change to a permission key in any JSON file.
PERMISSION_KEYS = ("allow", "deny", "ask", "additionalDirectories", "defaultMode", "hooks")
PERMISSION_FILES = (("vault", ".claude/settings.json"), ("vault", ".claude/settings.local.json"), ("vault", ".mcp.json"),
                    ("home", ".claude/settings.json"), ("home", ".claude/settings.local.json"))
TIERS = ("ordinary", "sensitive", "high")


def _json(text):
    """A dict from a file's text (bytes or str; empty is {}), or None when it isn't a JSON object."""
    if text is None:
        return {}
    try:
        s = text.decode("utf-8") if isinstance(text, (bytes, bytearray)) else str(text)
        if not s.strip():
            return {}
        d = json.loads(s)
    except (ValueError, UnicodeDecodeError):
        return None
    return d if isinstance(d, dict) else None


def _permission_values(d, where="", out=None):
    """Every permission key in d, at any depth (conservative: a nested `permissions` block counts too), as {dotted path: value}."""
    out = {} if out is None else out
    for k, v in d.items():
        here = f"{where}.{k}" if where else str(k)
        if k in PERMISSION_KEYS:
            out[here] = v
        elif isinstance(v, dict):
            _permission_values(v, here, out)
    return out


def _canon(v):
    return json.dumps(v, sort_keys=True, ensure_ascii=False)


def _label(v):
    return v if isinstance(v, str) else _canon(v)


def permission_change(old_text, new_text):
    """Whether new_text changes a permission rule compared with old_text: only the permission keys (allow, deny, ask,
    additionalDirectories, defaultMode, hooks) are compared, wherever they sit in the JSON. Returns
    {"changed": bool, "added": [...], "removed": [...], "keys": [...], "json": bool}: a rule added to or removed from a list
    ("permissions.allow: WebSearch"), and every key whose value changed in another way (defaultMode, hooks, a key added or
    dropped). Text that isn't a JSON object has no permission keys ("json": False, "changed": False); a permission file is
    High-risk by its path whatever its content (tier())."""
    old, new = _json(old_text), _json(new_text)
    if old is None or new is None:
        return {"changed": False, "added": [], "removed": [], "keys": [], "json": False}
    a, b = _permission_values(old), _permission_values(new)
    added, removed, keys = [], [], []
    for key in sorted(set(a) | set(b)):
        x, y = a.get(key), b.get(key)
        if key in a and key in b and _canon(x) == _canon(y):
            continue
        keys.append(key)
        if isinstance(x, (list, type(None))) and isinstance(y, (list, type(None))):
            xs, ys = x or [], y or []
            cx, cy = [_canon(v) for v in xs], [_canon(v) for v in ys]
            added += [f"{key}: {_label(v)}" for v, c in zip(ys, cy) if c not in cx]
            removed += [f"{key}: {_label(v)}" for v, c in zip(xs, cx) if c not in cy]
    return {"changed": bool(keys), "added": added, "removed": removed, "keys": keys, "json": True}


def is_permission_file(path):
    """True for ask creaite's permission files: .claude/settings.json and settings.local.json (the vault's and ~/.claude's) and the
    vault's .mcp.json (it starts servers)."""
    try:
        p = real(path)
    except (OSError, ValueError, RuntimeError):
        return False
    for base, pattern in PERMISSION_FILES:
        rel = base_parts(p, base)
        if rel is not None and [x.lower() for x in rel] == pattern.lower().split("/"):
            return True
    return False


def tier(path, operation, before=None, after=None, to=None):
    """("sensitive" | "high", reason) for a change shown on the card. High-risk: a permission file (path or destination), or new
    content that changes a permission key (permission_change) even where the path alone is Sensitive, such as
    system/config/settings.json. Everything else on the card is Sensitive. Never changes what is allowed."""
    pc = permission_change(before, after) if after is not None and operation in ("create", "change", "edit") else None
    what = ("; ".join(([f"adds {x}" for x in pc["added"]] + [f"removes {x}" for x in pc["removed"]])[:4])
            or "changes " + ", ".join(pc["keys"][:4])) if pc and pc["changed"] else ""
    if is_permission_file(path) or (to and is_permission_file(to)):
        return "high", f"it is one of ask creaite's permission files{f' ({what})' if what else ''}"
    if what:
        return "high", f"it changes a permission rule ({what})"
    return "sensitive", "it needs your approval"
# ===== end BL-194 =====


# ===== BL-141 (sprint-admin): one-time approvals, held in the live server's memory =====
class Approvals:
    """One-time approvals for sensitive changes. Only the live server issues them, after Alan's Approve, and only in its own process:
    nothing is written to a file, a prompt or an environment variable, so a model-run script (a separate process, with an empty
    table) can never redeem one. Each is bound to one change's fingerprint, lives at most MAX_LIFE seconds (or less, `until`),
    and is used once: any attempt to redeem it, right or wrong, uses it up."""
    MAX_LIFE = 30 * 60

    def __init__(self):
        import threading
        self._table, self._lock = {}, threading.Lock()

    def issue(self, fingerprint, until=None):
        """Issue a one-time approval bound to a change's fingerprint: a random token that lasts at most 30 minutes (or until `until`).
        Held only in the live server's memory (BL-141)."""
        import secrets
        import time
        token = secrets.token_hex(32)
        expires = time.time() + self.MAX_LIFE
        with self._lock:
            self._table[token] = (fingerprint, min(expires, until) if until else expires)
        return token

    def redeem(self, token, fingerprint):
        """Use a token once: True only if it was issued for this fingerprint and hasn't expired. The token is removed either way."""
        import hmac
        import time
        with self._lock:
            held = self._table.pop(str(token or ""), None)
        return bool(held) and hmac.compare_digest(held[0], fingerprint) and time.time() <= held[1]

    def clear(self):
        """Drop every approval not yet used; returns how many there were."""
        with self._lock:
            n = len(self._table)
            self._table.clear()
        return n

    def __len__(self):
        import time
        with self._lock:
            for t in [t for t, (_f, exp) in self._table.items() if exp < time.time()]:
                self._table.pop(t, None)
            return len(self._table)


APPROVALS = Approvals()


# ===== BL-141 part 2 (sprint-admin): the run's mark and the guard hook =====
# system/guard/ is on the never list: only the live server (and this hook, which is code the model can't change) writes it.
#   run.json              the ask creaite run in progress: {run, mode, started, outside: {tools, folders, outside_vault}, marked: [reasons]}
#   marked-sessions.json  the chat sessions that have read outside content (a resumed chat starts marked)
GUARD = paths.GUARD
RUN_FILE = GUARD / "run.json"
SESSIONS_FILE = GUARD / "marked-sessions.json"


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.part")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def guard_run():
    """The run in progress as the server wrote it, or None (no ask creaite run: a Terminal session)."""
    try:
        data = json.loads(RUN_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) and data.get("run") else None
    except (OSError, ValueError):
        return None


def marked_sessions():
    """The ask creaite chats that have read outside content (system/guard/marked-sessions.json); empty if none or unreadable."""
    try:
        data = json.loads(SESSIONS_FILE.read_text(encoding="utf-8"))
        return set(data) if isinstance(data, list) else set()
    except (OSError, ValueError):
        return set()


def start_run(run, mode, outside, session=None):
    """The server, as an ask creaite run starts: write the run (marked already if its chat was)."""
    marked = ["the chat had read outside content earlier"] if session and session in marked_sessions() else []
    _write_json(RUN_FILE, {"run": run, "mode": mode, "started": __import__("time").time(), "outside": outside, "marked": marked,
                           "session": session})


def mark(run, reason):
    """Mark the run as having read outside content. Never cleared by the model; only end_run removes the file."""
    data = guard_run()
    if not data or data.get("run") != run:
        return False
    if reason not in data["marked"]:
        data["marked"] = (data.get("marked") or []) + [reason]
        _write_json(RUN_FILE, data)
    return True


def end_run(run, session=None):
    """The server, as the run ends: remember a marked chat, then remove the run."""
    data = guard_run()
    if data and data.get("run") == run:
        if data.get("marked") and (session or data.get("session")):
            _write_json(SESSIONS_FILE, sorted(marked_sessions() | {session or data.get("session")}))
        RUN_FILE.unlink(missing_ok=True)


def is_marked(data=None):
    """Whether the run (the record given, else system/guard/run.json) has read outside content."""
    data = data if data is not None else guard_run()
    return bool(data and data.get("marked"))


def outside_reason(tool, inp, outside):
    """Why this tool call reads outside content, or None. `outside` is the run's table (OUTSIDE_CONTENT in live_server.py):
    {tools: [names], folders: [inbox, transcripts, documents], outside_vault: bool}."""
    tools = set((outside or {}).get("tools") or [])
    if tool in tools:
        return f"used {tool.rsplit('__', 1)[-1]}"
    if tool == "Grep" and (inp or {}).get("output_mode") == "content":     # a search whose folder holds the inbox or the projects
        try:
            where = real((inp or {}).get("path") or str(paths.ROOT))
            if any(parts_under(Path(os.path.realpath(f)), where) is not None for f in (paths.INBOX, paths.projects_root())):
                return "searched the text of files that include outside content"
        except (OSError, ValueError, RuntimeError):  # BL-228: an unresolvable search path; its paths are still checked below
            pass
    for p in tool_paths(tool, inp):
        why = folder_reason(p, outside)
        if why:
            return why
    return None


def folder_reason(path, outside):
    """Why reading this path is outside content under the run's table `outside` (inbox/, a transcript, a project document, a file outside
    the vault), or None."""
    try:
        p = real(path)
    except (OSError, ValueError, RuntimeError):
        return None
    folders = set((outside or {}).get("folders") or [])
    if "inbox" in folders and parts_under(p, Path(os.path.realpath(paths.INBOX))) is not None:
        return "read inbox/"
    pk = project_kind(p) if ("transcripts" in folders or "documents" in folders) else None
    if pk and pk[1] == "transcripts" and "transcripts" in folders:
        return "read a transcript"
    if pk and "documents" in folders:
        try:
            if any(parts_under(p, Path(os.path.realpath(r))) is not None for r in paths.document_roots(pk[0])) and pk[1] is None:
                return "read a project document"
        except (OSError, LookupError, ValueError):  # BL-228: a project without document roots; the outside-vault check below still runs
            pass
    if (outside or {}).get("outside_vault") and in_reach(p) == ["home"]:
        return "read a file outside the vault"
    return None


SHELL_OUT = set(";&|<>(){}\n\r")

# ===== BL-237 (sprint-portability): the interpreter wrapper =====
# system/scripts/run picks the newest Python 3.9 or later and runs one creaite script. A call through it has exactly the shape
# of `python3 system/scripts/<name>.py …`, so bash_problem applies every check to it unchanged; the wrapper itself (and wrap
# below, which it hands over to) refuses anything that isn't a script in system/scripts/ and any argument on the never list.
WRAPPER = "run"
WRAPPED = r"system/scripts/run ([a-z0-9_]+\.py)(?=\s|$)"
WRAP_NAME = r"[a-z0-9_]+\.py"


def wrap_problem(argv):
    """None if `system/scripts/run <argv…>` may start, else why not: the first word must be the bare name of a script in this
    folder, and no path-like argument may be on the never list (read), the same check the hook makes on a Bash call."""
    import re
    if not argv:
        return "needs a creaite script's name, e.g. system/scripts/run doctor.py"
    name = argv[0]
    if not re.fullmatch(WRAP_NAME, name):
        return "runs only a creaite script in system/scripts/, by its bare name: no -c, -m, path or other program"
    if not (Path(__file__).resolve().parent / name).is_file():
        return f"found no system/scripts/{name}"
    for a in argv[1:]:
        if ("/" in a or a.startswith(("~", "."))) and not a.startswith("-"):
            kind, why = classify(a, "read")
            if kind == "never":
                return f"won't pass {a}: {why}"
    return None


def wrap_main(argv):
    """`reach.py wrap <name>.py …`, run by system/scripts/run: check, then become `<this python> system/scripts/<name>.py …`.
    A refusal, or anything that goes wrong, exits 2 (a hook run through the wrapper fails closed)."""
    try:
        why = wrap_problem(argv)
    except Exception as e:  # noqa: BLE001  fail closed
        why = f"couldn't check the call ({type(e).__name__})"
    if why:
        _debug("warn", f"wrapper refused: {why}")
        sys.stderr.write(f"creaite: system/scripts/run {why}\n")
        return 2
    script = str(Path(__file__).resolve().parent / argv[0])
    try:
        sys.stdout.flush()
        os.execv(sys.executable, [sys.executable, script, *argv[1:]])
    except OSError as e:
        sys.stderr.write(f"creaite: system/scripts/run couldn't start {argv[0]} ({e})\n")
        return 2
# ===== end BL-237 =====


def bash_problem(command):
    """None if this is one creaite script run on its own, else why it is refused (BL-141: the panel has no open Bash). Parsing is
    strict: outside quotes no ; & | < > ( ) { } or new line; outside single quotes no $ or back-quote. BL-265: the script, then
    the scripts never run, then the shell characters, then the settings rule, as before."""
    cmd = (command or "").strip()
    m = __import__("re").match(r"python3? system/scripts/([a-z0-9_]+\.py)(?=\s|$)", cmd)
    # ===== BL-237 (sprint-portability): the wrapper is the same shape: exactly `system/scripts/run <name>.py …` =====
    if not m and (paths.ROOT / "system" / "scripts" / WRAPPER).is_file():
        m = __import__("re").match(WRAPPED, cmd)
    # ===== end BL-237 =====
    if not m:
        return ("ask creaite runs only creaite's own scripts, one at a time, exactly `python3 system/scripts/<name>.py …`; "
                "file changes go through filechange.py")
    return _script_refused(m.group(1)) or _shell_refused(cmd) or _settings_refused(m.group(1), cmd.split())


def _script_refused(script):
    if script == "permissions.py":
        return "permissions.py is never run by the panel"
    if script in ("live_server.py", "launch.py"):
        return f"{script} starts the live server or the app, which ask creaite never does"
    if not (paths.ROOT / "system" / "scripts" / script).is_file():
        return f"system/scripts/{script} doesn't exist"
    return None


def _shell_refused(cmd):
    """Why the command has shell characters the shell would act on, or None."""
    quote = None
    for i, ch in enumerate(cmd):
        if quote:
            if ch == quote and not (quote == '"' and cmd[i - 1] == "\\"):
                quote = None
            elif quote == '"' and ch in "$`":
                return "the command has $ or a back-quote, which the shell would expand: run the script on its own"
            continue
        if ch in "'\"":
            quote = ch
        elif ch in SHELL_OUT or ch in "$`" or ch == "\\":
            return ("the command has shell characters (; & | < > $ brackets, a back-quote or a new line): run the script on its own. "
                    "To keep a script's output, use its --out <name>.json (propose.py new-project and close-project) or read what it "
                    "printed and save it with the Write tool in system/staging/drafts/; never a redirect or /tmp")
    return "the command has an unclosed quote" if quote else None


def _settings_refused(script, words):
    if script == "propose.py" and len(words) > 2 and words[2] == "setting" or \
            script == "propose.py" and "retire-settings" in words:
        return ("settings are changed on the approval card: put the new settings.json in system/staging/drafts/ and run "
                "python3 system/scripts/filechange.py edit system/config/settings.json --from <that file> --why \"…\"")
    return None


# ===== BL-267: what each creaite script's commands do to the record =====
# One list. Every command of every creaite script is one of:
#   read     changes nothing;
#   derived  rebuilds or records what creaite derives (the dashboard, the Excel export, the search index, its run records);
#   stage    writes a pending proposal or a draft, which waits for Alan's approval in Review;
#   guarded  filechange.py, which makes its own decision on every change (BL-141: ordinary at once, sensitive on the card);
#   record   changes the record: writes the database, decides a proposal (approve, reject, edit, bulk, merge), stages items
#            already approved (propose.py's specs are approved when staged), or changes the registers, the engine or
#            what has been processed.
# In a run Alan hasn't confirmed (mode "ask"), the guard hook refuses every record command, whatever the permission rules
# allow (BL-267: a plain chat ran tracker.py apply unconfirmed). A (kind, flag) pair is that kind unless the flag is given, which
# makes it read only (--dry-run, --check). "a b" names a second word. A script with no commands has the one key "".
# dev/tests/test_record_commands.py fails until a new script or command is added here.
READ, DERIVED, STAGE, GUARDED, RECORD = "read", "derived", "stage", "guarded", "record"
SCRIPT_COMMANDS = {
    "tracker.py": {"read": READ, "validate": READ, "query": READ, "index": DERIVED,
                   "init": RECORD, "apply": RECORD, "undo": RECORD, "undo-changes": RECORD, "migrate": RECORD},
    "review.py": {"pending": READ, "list": READ, "approve": RECORD, "reject": RECORD, "bulk": RECORD,
                  "assign": (RECORD, "--dry-run"), "edit": RECORD, "workstream": RECORD, "keep": RECORD, "override": RECORD,
                  "merge": RECORD, "keep-new": RECORD,
                  "retarget": RECORD, "unmerge": RECORD, "candidates": READ,    # BL-297
                  "reasons": READ, "guesses": READ, "rejects": READ,            # BL-315
                  "unreject": RECORD, "rereason": RECORD, "approve-instead": RECORD},
    "propose.py": {"fields": READ, "preview": READ, "new-project": READ, "close-project": READ,
                   "stage": RECORD, "recode": (RECORD, "--dry-run"), "setting": RECORD, "learn": (RECORD, "--check"),
                   "register-columns": RECORD, "old-archives": READ, "archive": READ, "restore": READ,   # BL-09: print (or save) a spec
                   "people": READ, "people list": READ, "people resolve": READ, "people add": RECORD, "people edit": RECORD,
                   "people rename": RECORD, "people merge": RECORD, "people map": RECORD, "people migrate": RECORD,
                   "workstreams": READ, "workstreams list": READ, "workstreams suggest": READ, "workstreams add": RECORD,
                   "workstreams retire-settings": RECORD},
    "minutes.py": {"transcript": READ, "key": READ, "filename": READ, "filedate": READ, "new": READ, "expected": READ,
                   "agenda": READ, "done-candidates": READ, "stage": STAGE, "refresh": STAGE, "carry": STAGE,
                   "baseline": (RECORD, "--dry-run")},
    "sweep.py": {"due": READ, "window": READ, "expected": READ, "calendar-window": READ, "done-candidates": READ, "ignore": READ,
                 "lock": DERIVED, "unlock": DERIVED, "done": DERIVED, "fail": DERIVED, "calendar": DERIVED,
                 "transcripts": DERIVED, "vip": DERIVED, "stage": STAGE},
    "report.py": {"weekly-data": READ, "client-data": READ, "steerco-data": READ, "current-context": READ, "facts": READ,
                  "adhoc-data": READ, "adhoc": STAGE, "weekly-stage": STAGE, "client-stage": STAGE, "steerco-stage": STAGE},
    "excel_sync.py": {"changed": READ, "export": DERIVED, "import": RECORD},
    "docx_tools.py": {"text": READ, "status": READ, "fill": STAGE, "build-adhoc": STAGE, "clean": STAGE},
    "drafts.py": {"context": READ, "result": READ, "stats": READ, "features": READ, "stat": DERIVED},
    "filechange.py": {"check": READ, "list": READ, "create": GUARDED, "edit": GUARDED, "move": GUARDED, "delete": GUARDED,
                      "undo": GUARDED},
    "forecast.py": {"range": READ},
    "sneak_peek.py": {"read": READ},     # BL-322: reads one instruction on one item; writes nothing (its dry run is rolled back)
    "locations.py": {"check": READ, "inspect": READ, "portfolio-spec": READ, "tilde": READ},
    "prep_page.py": {"context": READ, "latest": READ, "build": GUARDED},   # BL-271: saved through filechange.py
    "search.py": {"parse": READ, "query": READ, "context": READ, "preview": READ, "enrich": DERIVED},
    "status_checks.py": {"check": READ, "sources": READ, "save-evidence": DERIVED},
    "status_facts.py": {"facts": READ},
    "status_prompt.py": {"rewrite-prompt": READ},
    "transcripts.py": {"todo": READ, "show": READ, "record": DERIVED},
    "update.py": {"version": READ, "find": READ, "inspect": READ, "fetch": STAGE,
                  "install": RECORD, "undo": RECORD, "tidy": RECORD, "new-vault": RECORD},
    "reach.py": {"classify": READ, "never": READ, "hook": READ, "wrap": READ},
    "session.py": {"start": DERIVED, "backup": DERIVED},     # BL-320: backup is the part of start that copies the daily backup
    "doctor.py": {"": READ},
    # BL-323: check records its result for Health (derived); tidy removes old backups for good and restore replaces the
    # database, settings and staging, so both are record commands (a plain chat may only look: --dry-run)
    "backup.py": {"list": READ, "show": READ, "check": DERIVED, "tidy": (RECORD, "--dry-run"), "restore": (RECORD, "--dry-run")},
    "quality.py": {"": READ},
    "build_dashboard.py": {"": DERIVED},
    "permissions.py": {"": RECORD},      # also never run by the panel (_script_refused)
    "live_server.py": {"": RECORD},      # also never run by the panel
    "launch.py": {"": RECORD},           # also never run by the panel
}


def command_kind(script, words):
    """(kind, the command as named) for `<script> <words…>`: one of the kinds above, or "unknown" for a script or command not in
    SCRIPT_COMMANDS (refused in a plain chat: it fails closed until someone decides). No command, or only options, is read
    only: the script prints its usage."""
    table = SCRIPT_COMMANDS.get(script)
    if table is None:
        return "unknown", script
    if "" in table:
        return table[""], script
    pos = [w for w in words if not w.startswith("-")]
    if not pos:
        return READ, script
    name = f"{pos[0]} {pos[1]}" if len(pos) > 1 and f"{pos[0]} {pos[1]}" in table else pos[0]
    kind = table.get(name, "unknown")
    if isinstance(kind, tuple):
        kind = READ if kind[1] in words else kind[0]
    return kind, f"{script} {name}"


def record_problem(command):
    """Why a plain chat may not run this creaite script command (BL-267), or None. Called only for a command bash_problem let
    through, and only when the run isn't confirmed."""
    words = bash_args(command)
    m = __import__("re").match(r"(?:python3? system/scripts/|system/scripts/run )([a-z0-9_]+\.py)", (command or "").strip())
    if not m:
        return None
    kind, name = command_kind(m.group(1), words)
    if kind == RECORD:
        _debug("warn", f"record command refused: {name}")
        return (f"{name} changes the record, and ask creaite runs it only for a request Alan has confirmed: say what you would "
                f"do and end your reply with CONFIRM: <short title> | <what will happen>")
    if kind == "unknown":
        _debug("warn", f"record command refused: {name} (not classified)")
        return (f"{name} isn't a command creaite knows the effect of, so a plain chat doesn't run it: check the script's usage, "
                f"or ask Alan to confirm it with a CONFIRM: line")
    return None
# ===== end BL-267 =====


# ===== BL-268 follow-up: what kind of command was refused, for the debug log =====
# A refusal logs the kind of command in a few words, never its text, paths or arguments (BL-102), so a refused step can be
# told apart at once: a common program by name (ls, cat, cd…), Python run another way, a program by its path, a creaite script
# by a full path (this vault's or another folder's), or another program.
KNOWN_PROGRAMS = {"ls", "cat", "head", "tail", "less", "cd", "pwd", "mv", "cp", "rm", "mkdir", "rmdir", "touch", "chmod", "echo",
                  "printf", "find", "grep", "rg", "sed", "awk", "sort", "uniq", "wc", "cut", "tr", "diff", "jq", "file", "stat",
                  "date", "env", "which", "test", "open", "osascript", "curl", "wget", "git", "gh", "node", "npm", "npx", "bash",
                  "sh", "zsh", "sqlite3", "xargs", "tee", "launchctl", "defaults", "security", "pbcopy", "pbpaste"}


def command_kind_words(command):
    """The kind of a Bash command that isn't one creaite script run on its own, in a few words: its program's name when it is
    a common one, otherwise what it is. Never the command's text, paths or arguments."""
    import re
    cmd = (command or "").strip()
    first = cmd.split()[0] if cmd else ""
    if not first:
        return "an empty command"
    script = _script_kind(cmd)
    if script:
        return script
    if first in ("python", "python3") or re.fullmatch(r"python3(\.\d+)?", first):
        return "python -c" if " -c " in f" {cmd} " else "python with another file" if len(cmd.split()) > 1 else "python"
    name = first.rsplit("/", 1)[-1]
    if "/" in first:
        return f"{name} by its path" if name in KNOWN_PROGRAMS else "a program by its path"
    return first if first in KNOWN_PROGRAMS else "another program"


def _script_kind(cmd):
    """A creaite script's kind: by its full path (this vault's or another folder's), or its name when it was run the usual way
    and refused for something else (the reason says what); None when the command names no creaite script that way."""
    import re
    script = re.search(r"(/[^\s'\"]*)?/?system/scripts/(?:run )?([a-z0-9_]+\.py)", cmd)
    if script and re.match(r"(python3? )?/", cmd):
        here = script.group(1) and os.path.realpath(script.group(1)) == os.path.realpath(paths.ROOT)
        return f"{script.group(2)} by its full path ({'this vault' if here else 'another folder'})"
    if script and re.match(r"(python3? system/scripts/|system/scripts/run )", cmd):
        return script.group(2)
    return None
# ===== end BL-268 follow-up =====


def bash_args(command):
    """A creaite script command's arguments after `python3 <script>`, shell-split; [] if it can't be split."""
    import shlex
    try:
        return shlex.split(command)[2:]
    except ValueError:
        return []


def tool_paths(tool, inp):
    """The paths a tool call names: a file tool's file, a search's folder, a creaite script's path-like arguments."""
    inp = inp or {}
    if tool in ("Read", "Edit", "Write", "MultiEdit", "NotebookEdit", "NotebookRead"):
        return [x for x in (inp.get("file_path") or inp.get("notebook_path"),) if x]
    if tool in ("Grep", "Glob", "LS"):
        out = [inp.get("path") or str(paths.ROOT)]
        pat = str(inp.get("pattern") or "") if tool == "Glob" else ""
        if pat.startswith(("/", "~")):
            out.append(pat.split("*", 1)[0] or "/")
        return out
    if tool == "Bash":
        return [a for a in bash_args(str(inp.get("command") or "")) if ("/" in a or a.startswith(("~", "."))) and not a.startswith("-")]
    return []


def never_inside(folder):
    """The first never-read place (secrets, the operating system) below this folder, or None."""
    try:
        root = real(folder)
    except (OSError, ValueError, RuntimeError):
        return str(folder)
    for base, pattern, ops, _why in NEVER:
        if ops != "all" or base == "vault":
            continue
        place = Path(pattern) if base == "abs" else home() / pattern.split("*")[0].rstrip("/")
        if parts_under(Path(os.path.realpath(place)), root) is not None:
            return ("~/" + pattern) if base == "home" else pattern
    return None


def direct_write_area(mode):
    """Where a direct Edit or Write may go (BL-141: everything else goes through filechange.py, with a backup and an undo)."""
    return paths.STAGING if mode == "confirmed" else paths.DRAFTS      # BL-295: the catch-up sweep ("sweep") as a plain chat


def hook_decision(tool, inp, mode, run):
    """(allow, reason) for one tool call in an ask creaite run. Marks the run first when the call reads outside content."""
    data = guard_run()
    if data and data.get("run") == run:
        why = outside_reason(tool, inp, data.get("outside"))
        if why:
            mark(run, why)
    for p in tool_paths(tool, inp):
        kind, why = classify(p, "read")
        if kind == "never":
            return False, f"{p}: {why}"
    if tool in ("Grep", "Glob", "LS"):                      # a search would go inside a never folder below it
        inside = never_inside((inp or {}).get("path") or str(paths.ROOT))
        if inside:
            return False, f"the search folder holds {inside}, which is never read: search a folder below it instead"
    if tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        p = (inp or {}).get("file_path") or (inp or {}).get("notebook_path") or ""
        rp = real(p)
        kind, why = classify(p, "change" if rp.exists() else "create")
        if kind == "never":
            return False, f"{p}: {why}"
        area = Path(os.path.realpath(direct_write_area(mode)))
        if parts_under(rp, area) is None:
            return False, (f"{p}: ask creaite changes files only through filechange.py (backed up, logged, undoable): prepare the "
                           f"new content in {paths.rel(area)}/ and run python3 system/scripts/filechange.py")
    if tool == "Bash":
        why = bash_refusal(str((inp or {}).get("command") or ""), mode)
        if why:
            return False, why
    return True, ""


def bash_refusal(command, mode):
    """Why a Bash call is refused, or None: its form (bash_problem), then, unless the run is confirmed, a record command
    (BL-267: the record changes only on a request Alan confirmed). BL-268: a script named by this vault's full path is read as
    the relative form first, so every check applies to it unchanged."""
    command = vault_relative(command)
    return bash_problem(command) or record_gate(command, mode)


# ===== BL-295 (sprint-close-day-server): the catch-up sweep from Close the day =====
# Close the day starts cx-sweep through the run engine as its own guarded mode, "sweep": a plain chat's rules (no record command,
# direct writes only in system/staging/drafts/), with the one step cx-sweep needs that a plain chat lacks: mapping the names in its
# own draft (`propose.py people map <a file in system/staging/drafts/>`), which changes nothing but that draft. Nothing else.
def record_gate(command, mode):
    """Why a record command is refused in this mode, or None: a confirmed run may; the catch-up sweep may map names in a draft."""
    if mode == "confirmed" or (mode == "sweep" and sweep_maps_draft(command)):
        return None
    return record_problem(command)


def sweep_maps_draft(command):
    """True for `propose.py people map <file directly in system/staging/drafts/>`, the catch-up sweep's one extra step."""
    import re
    m = re.fullmatch(r"(?:python3? system/scripts/|system/scripts/run )propose\.py people map (\S+)", (command or "").strip())
    if not m:
        return False
    target = real(m.group(1))
    return target.suffix == ".json" and target.parent == Path(os.path.realpath(paths.DRAFTS))
# ===== end BL-295 =====


def vault_relative(command):
    """`python3 <this vault>/system/scripts/x.py …` or `<this vault>/system/scripts/run x.py …` as the relative form the checks
    know (BL-268: a run that wrote a file by its full path then named the script the same way, and was refused). Only when the
    folder named is this vault's, by its real path (macOS's /var is /private/var); anything else is left as it is."""
    import re
    cmd = (command or "").strip()
    m = re.match(r"(python3? )?(/[^\s'\"]+?)/system/scripts/(?=\S)", cmd)
    if m and os.path.realpath(m.group(2)) == os.path.realpath(paths.ROOT):
        return (m.group(1) or "") + "system/scripts/" + cmd[m.end():]
    return cmd


def hook_main(argv):
    """`reach.py hook --run <id> --mode ask|confirmed`: Claude Code's PreToolUse hook for an ask creaite run. Reads the call as JSON
    on standard input; exit 0 lets it through to the permission rules, exit 2 refuses it (the reason goes back to Claude). Any
    error refuses: the guard fails closed."""
    try:
        opts = dict(zip(argv[0::2], argv[1::2]))
        call = json.loads(sys.stdin.read() or "{}")
        tool, inp = str(call.get("tool_name") or ""), call.get("tool_input") or {}
        ok, why = hook_decision(tool, inp, opts.get("--mode", "ask"), opts.get("--run", ""))
    except Exception as e:  # noqa: BLE001  fail closed
        ok, why = False, f"the guard couldn't check this call ({type(e).__name__})"
        tool = "?"
    if not ok:
        _debug("warn", f"refused {tool}{_refused_kind(tool, locals().get('inp'))}: {why}")   # BL-268 follow-up: the kind, never the text
        sys.stderr.write(f"creaite refused this: {why}\n")
        return 2
    return 0


def _refused_kind(tool, inp):
    """The kind of a refused Bash call in brackets, for the log line, or nothing; never raises, so the refusal (exit 2) stands."""
    try:
        return f" ({command_kind_words(str(inp.get('command') or ''))})" if tool == "Bash" and isinstance(inp, dict) else ""
    except Exception:  # noqa: BLE001  the log line is a help; the refusal must not depend on it
        return ""


def _debug(level, message):
    """A line in the debug log (paths and names only, never contents); nothing if the log isn't there."""
    try:
        import log as debuglog
        getattr(debuglog, level)("guard", debuglog.clean(message, 300))
    except Exception:  # noqa: BLE001  the log never stops a check
        pass


def main(argv):
    """The command line: hook and wrap (hook_main, wrap_main), classify <path> <operation> [--marked] [--count N] (prints the verdict as
    JSON) and never (prints the never list)."""
    if argv[:1] == ["hook"]:
        return hook_main(argv[1:])
    if argv[:1] == ["wrap"]:                                # BL-237: system/scripts/run hands over here
        return wrap_main(argv[1:])
    if argv[:1] == ["classify"] and len(argv) >= 3:
        count = int(argv[argv.index("--count") + 1]) if "--count" in argv else 0
        kind, reason = classify(argv[1], argv[2], marked="--marked" in argv, count=count)
        print(json.dumps({"kind": kind, "reason": reason}, ensure_ascii=False))
        return 0
    if argv[:1] == ["never"]:
        for base, pattern, ops, reason in NEVER:
            print(f"{ops:5}  {'~/' if base == 'home' else '' if base == 'abs' else '<vault>/'}{pattern}  — {reason}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
