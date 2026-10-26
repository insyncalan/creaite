"""creaite paths — the single place where folder locations are defined.

Every script imports from here. Paths are relative to the vault root, which is
found from this file's own location, so creaite works wherever the folder is copied.
To reorganise folders, change this file (and the path table in CLAUDE.md), nothing else.
"""
from pathlib import Path
import errno
import json
import os
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[2]          # creaite/

# Bundled libraries first (no pip installs)
VENDOR = ROOT / "system" / "scripts" / "vendor"
if str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))

# Daily-use files (root)
DASHBOARD   = ROOT / "dashboard.html"
EXCEL_VIEW  = ROOT / "tracker-view.xlsx"
INBOX       = ROOT / "inbox"

# Projects. Where they live is the `locations` setting (BL-85): by default the vault's own projects/ folder; with
# `locations.projects_root` set, the engagement folders (and the portfolio folder) live there, e.g. in the company OneDrive.
# PROJECTS, PORTFOLIO, REGISTER, PORTFOLIO_MEMORY and PEOPLE_REGISTER are therefore worked out on each use (see __getattr__ below).
PROJECT_SUBFOLDERS = ("minutes", "transcripts", "documents", "reports", "notes")      # the default layout's subfolders (notes: BL-301)
EXTRACT_FROM = ("minutes", "transcripts")          # documents, reports and notes are never extracted

# System (engine; not edited by hand)
SYSTEM      = ROOT / "system"
DB          = SYSTEM / "tracker.db"
SCHEMA      = SYSTEM / "scripts" / "schema.sql"
PROCESSED   = SYSTEM / "processed.txt"
STAGING     = SYSTEM / "staging"
DAY_CLOSED  = STAGING / "day-closed.json"        # BL-206: the days closed with Close the day ({day: HH:MM}), written by the live server
CARRIED     = STAGING / "carried.json"           # BL-209: agenda points carried to the next meeting of a series (Coverage)
EVIDENCE    = STAGING / "evidence"               # BL-207: <code>-current.json, a saved Current state's sentence links (derived; rewritten on save)
APPLIED     = STAGING / "applied"
RUN_LOG     = STAGING / "run-log.txt"
HISTORY     = SYSTEM / "history"                   # dashboard snapshots
BACKUPS     = SYSTEM / "backups"                   # database backups
TEMPLATES   = SYSTEM / "templates"
SCHEDULES   = SYSTEM / "config" / "schedules.md"
SETTINGS    = SYSTEM / "config" / "settings.json"     # tunable values; see load_settings()
SETTINGS_LOG = SYSTEM / "config" / "settings-log.jsonl"
CLAUDE_SETTINGS = ROOT / ".claude" / "settings.json"      # Claude Code's permission rules for this vault (BL-75: changed only by permissions.py)
PERMISSIONS_LOG = SYSTEM / "config" / "permissions-log.jsonl"   # every rule added through permissions.py, and every undo
SWEEP_STATE = STAGING / "last-sweep.txt"            # time of last successful sweep
CALENDAR    = STAGING / "calendar.json"             # Alan's meetings, today and the week ahead (cx-sweep); Today's day view
MENTIONS    = STAGING / "mentions.jsonl"            # open items raised again in a later meeting or sweep (BL-51 early warnings)
INTAKE_CLEARED = STAGING / "intake-cleared.json"   # meetings set aside in Intake's Calendar import (BL-104 Clear day); never processed.txt
TRANSCRIPTS = STAGING / "transcripts.json"       # each meeting's transcript status from the sweep (BL-42 phase 3): never text, a passcode or a PIN
NOTES_SENT  = STAGING / "notes-sent.json"        # BL-301: what Find updates applied from each note (paragraph, fingerprint, IDs)
RUN_USAGE   = STAGING / "run-usage.jsonl"       # #197: one counts-only line per finished Claude run (usage_log.py appends; usage_report.py reads)
CONTEXT_SIZE = STAGING / "context-size.jsonl"    # #238: what every run loads, once a day (usage_log.py; counts only)
MINUTES_TEMPLATE = TEMPLATES / "minutes-template.docx"
WEEKLY_TEMPLATE  = TEMPLATES / "weekly-report-template.docx"
CLIENT_TEMPLATE  = TEMPLATES / "client-report-template.docx"
STEERCO_TEMPLATE  = TEMPLATES / "steerco-template.docx"             # BL-92
DRAFTS      = STAGING / "drafts"
BRANDING    = SYSTEM / "branding"                  # the firm's brand sources and the report logos: local only, kept out of git
REPORT_LOGOS = BRANDING / "logos"                  # v2.1.0 P3 (BL-335): firm.<ext>, <CODE>-client.<ext>, <CODE>-partner.<ext>
SEARCH_DIR  = SYSTEM / "search"                     # BL-07: the index's build stamp and each file's summary and tags (sidecars)
LOGS        = SYSTEM / "logs"                       # BL-102: the debug log, one file a day, the last 7 days (log.py)
GUARD       = SYSTEM / "guard"                      # BL-141: the ask creaite run in progress and its mark; written only by the live server
ASK_CHATS   = STAGING / "ask"                        # ask creaite chat history, one JSON file per chat
ASK_UPLOADS = STAGING / "uploads" / "ask"             # images attached to ask creaite messages (BL-100): kept with their chat, read only


# Releases and updates (BL-36). Vault-relative paths with forward slashes; a folder covers everything in it.
VERSION_FILE = ROOT / "VERSION"
RULES       = SYSTEM / "creaite-rules.md"            # creaite's rules, imported by the root CLAUDE.md; replaced by updates
RELEASES    = SYSTEM / "releases"                    # release zips: the installed one and every earlier one, kept
RELEASE_MANIFEST = "creaite-release.json"            # inside each release zip
ENGINE = ("VERSION", "system/creaite-rules.md", "system/scripts", "system/templates", ".claude/skills")  # replaced
ENGINE_MERGED = (".claude/settings.json", "system/config/settings.json")      # new keys and rules added, values kept
DATA = ("CLAUDE.md", "projects", "projects/_portfolio/people-register.md", "inbox", "system/tracker.db", "system/staging", "system/history", "system/backups",
        "system/releases", "system/search", "system/branding", "system/processed.txt", "system/config", ".claude/settings.local.json",
        "dashboard.html", "tracker-view.xlsx", ".creaite-dev")                 # never replaced or removed by an update


def load_settings() -> dict:
    """Read system/config/settings.json (the only place tunable values live)."""
    import json
    return json.loads(SETTINGS.read_text(encoding="utf-8"))


# ===== BL-266 (fix-backup-names) =====
def free_path(folder, stem: str, ext: str = "") -> Path:
    """folder/<stem><ext>, or <stem>-2<ext>, -3 and so on when that is taken: backups are named to the second, and two in one
    second must not overwrite the first."""
    p, n = Path(folder) / f"{stem}{ext}", 2
    while p.exists():
        p, n = Path(folder) / f"{stem}-{n}{ext}", n + 1
    return p
# ===== end BL-266 =====


def write_text_atomic(path, text: str) -> None:
    """Write text to path through a temporary file in the same folder, then os.replace: a reader sees the old file or the new
    one, never an empty or half-written one (Path.write_text truncates first). An existing file keeps its mode."""
    import secrets
    import threading
    path = Path(path)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.{secrets.token_hex(4)}.tmp")
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)      # the umask applies, as with open(…, "w")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        try:
            os.chmod(tmp, path.stat().st_mode & 0o7777)
        except FileNotFoundError:
            pass  # a new file: no old mode to keep
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


# ── Where the projects are (BL-85) ────────────────────────────────────────────
# Stored paths (the database's sources, proposals' file operations, links) are vault-relative with forward slashes. A path in a
# project folder is `projects/<engagement folder>/<path inside it>`; `projects/` is a logical prefix that `resolve` maps to the
# projects root, and `projects/_portfolio/` is always the portfolio folder, whatever it is called. So moving the root later is one
# setting change, and rows made before the setting existed keep working.

LOCATION_DEFAULTS = {"projects_root": "", "portfolio": "_Portfolio", "skeleton": "_Templates/_Skeleton",
                     "folders": {"transcripts": "02 Meetings/Transcripts", "minutes": "02 Meetings/Minutes",
                                 "weekly_reports": "04 Reporting/Weekly", "client_reports": "04 Reporting/Weekly",
                                 "adhoc_documents": "04 Reporting/Adhoc", "images": "04 Reporting/Content",
                                 "steerco": "04 Reporting/Steerco",       # BL-93, BL-87: listed in Files; creaite may file into it when asked
                                 "agendas": "02 Meetings/Agendas",                     # BL-98: meeting prep pages
                                 "notes": "08 Notes"},                                 # BL-301: Alan's notes, made on the first note
                     "never_index": ["99 Archive", "_Archive", "zz Archive", "_Templates", "99 System"],   # BL-112: 99 System: the backups;
                     # #252: the two old archive names are added, never removed, so a saved list from before still works
                     "offsite_backup": "_Portfolio/99 System/creaite backups",
                     "project_paths": {}}       # #385: {register folder name: "~/…"}, a project's own folder elsewhere
ARCHIVE = "99 Archive"             # #252 (Alan, 20-10-2026): archived projects (<projects root>/99 Archive/<folder>) and each
#                                    engagement's own archive folder: one name, so it sorts last beside 99 System. Every new move
#                                    goes here, nowhere else.
OLD_ARCHIVES = ("_Archive", "zz Archive")   # #252: the two earlier names. For one release they are still skipped (never
#                                    indexed or extracted), still resolved (a stored path under one still opens; a file in one can be
#                                    moved back or restored) and still shown. Nothing is renamed for Alan (no migration, no offer).
OLD_ARCHIVE = OLD_ARCHIVES[-1]     # "zz Archive": kept only so reach.py (guarded) imports until its #252 diff lands; then dropped
ALWAYS_NEVER_INDEX = (ARCHIVE, "_Archive", "_Templates", "99 System")   # skipped whatever the saved list says (BL-112, BL-09, #252)
DEFAULT_FOLDERS = {"minutes": "minutes", "transcripts": "transcripts", "weekly_reports": "reports", "client_reports": "reports",
                   "adhoc_documents": "reports", "images": "images", "documents": "documents", "steerco": "reports/Steerco",
                   "agendas": "agendas", "notes": "notes"}   # the default layout (Steerco its own folder so Files can label it;
#                                                               agendas: BL-98; notes: BL-301)
LOGICAL = "projects"
LOGICAL_PORTFOLIO = "projects/_portfolio"

_cache = {}


def _cached(path: Path, load):
    """Parse a file again only when it has changed (a stale read is the worst a long-running server could do)."""
    try:
        key = path.stat().st_mtime_ns
    except OSError:
        return load(None)
    hit = _cache.get(path)
    if not hit or hit[0] != key:
        hit = _cache[path] = (key, load(path))
    return hit[1]


def locations() -> dict:
    """settings.json `locations`, each key filled from the defaults ({} values stay as the defaults say)."""
    def load(p):
        """The `locations` setting from one settings file, or {} when it is missing or unreadable."""
        try:
            return json.loads(p.read_text(encoding="utf-8")).get("locations") or {} if p else {}
        except (OSError, ValueError):
            return {}
    given = _cached(SETTINGS, load)
    out = {k: (dict(v) if isinstance(v, dict) else list(v) if isinstance(v, list) else v) for k, v in LOCATION_DEFAULTS.items()}
    for k, v in given.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k].update(v)
        else:
            out[k] = v
    return out


def external() -> bool:
    """True when the projects live outside the vault's projects/ folder (locations.projects_root is set)."""
    return bool(str(locations().get("projects_root") or "").strip())


def projects_root() -> Path:
    """Where the project folders live: the vault's projects/, or locations.projects_root (BL-85)."""
    root = str(locations().get("projects_root") or "").strip()
    if not root:
        return ROOT / "projects"
    p = Path(os.path.expanduser(root))               # stored with ~ so a new laptop with the same OneDrive works
    return p if p.is_absolute() else ROOT / p


def portfolio_dir() -> Path:
    """The portfolio folder: projects/_portfolio in the vault, else the projects folder's _Portfolio (BL-85)."""
    return projects_root() / str(locations().get("portfolio") or "_Portfolio") if external() else ROOT / "projects" / "_portfolio"


# ===== #385: a project's own folder, anywhere in the home folder =====
# locations.project_paths = {"<register folder name>": "~/…"}: that project's folder is there instead of <projects root>/<folder>.
# Honoured only when locations.projects_root is set (external()); the portfolio and the offsite backup stay under the projects
# root. Stored paths never change: projects/<folder>/… still names a mapped project's file, and resolve and rel map the first part
# after projects/ to the mapped folder (the longest match first). A value is stored with ~ (or relative to the projects root) and
# expanded on use. An archived mapped project is beside its own folder: <parent of the folder>/99 Archive/<folder>, stored as
# projects/99 Archive/<folder>/… exactly as an archived project in the projects root is. A mapped folder that isn't there (an
# unmounted drive, OneDrive not running) is never created: missing_project_paths lists it for Health.

def _loc_project_roots(loc) -> dict:
    """{folder name: real Path} from a `locations` value `loc`, failing closed (Cap's review of phase 1, MEDIUM 1): every entry
    project_mapping_problem refuses is left out (a value above the home folder, a key named 99 Archive, a symlink …), so no
    caller can take a bad one; the key is the register's own spelling. Archived projects' entries are included (resolve needs
    them); project_roots is the registered ones. dropped_project_paths lists what was left out."""
    return _loc_honoured(loc)[0]


def _raw_name_ok(name) -> bool:
    """A project_paths key that is well formed: a non-empty name with no slash, not . or .., no NUL byte."""
    return (isinstance(name, str) and bool(name.strip()) and "/" not in name and "\\" not in name
            and name not in (".", "..") and "\0" not in name)


def _raw_value_ok(value) -> bool:
    """A project_paths value that is well formed: non-empty text without a NUL byte (Cap's LOW 5: a NUL byte raises on every use)."""
    return isinstance(value, str) and bool(value.strip()) and "\0" not in value


def _loc_raw_roots(loc) -> dict:
    """{folder name: Path} from `loc` as written, unchecked: {} when it has no projects_root, and only the well-formed entries
    (a non-empty name without a slash, a non-empty text value). The path is expanded (~) and made absolute (a relative one is
    below that projects root), never resolved through symlinks and never checked on disk. Only _loc_honoured reads this."""
    loc = loc or {}
    m = loc.get("project_paths")
    if not str(loc.get("projects_root") or "").strip() or not isinstance(m, dict) or not m:
        return {}
    root = _loc_root(loc)
    out = {}
    for name, value in m.items():
        if not _raw_name_ok(name) or not _raw_value_ok(value):
            continue
        p = Path(os.path.expanduser(value.strip()))
        out[name] = p if p.is_absolute() else root / p
    return out


PROJECT_PATHS_SINCE = "2.6.10"  # #385: the first release that reads locations.project_paths; undoing an update to an older one
#                                warns (cx-setup, Settings › Undo update): its mapped projects drop out of view (no data lost)
_HONOURED = {}                 # #385: the checked map, by what it was checked against: (when, roots, dropped)
HONOURED_SECONDS = 2.0         # checked again at least this often (a folder swapped for a symlink is dropped within it)
_CHECKING = [False]            # a check that finds itself asked again (reach calling back) honours nothing meanwhile


def _loc_honoured(loc):
    """#385, fail closed on read (Cap's review, MEDIUM 2b): (roots, dropped) for `locations` value `loc`. roots is
    _loc_raw_roots(loc) without every entry project_mapping_problem refuses (a hand-edited settings.json, or a folder that has
    since become a symlink or moved inside another project's): such an entry is left out as if it weren't there, so nothing (reach,
    the guard hook, resolve) takes it as a project's folder. dropped is [{folder, path, why}] for Health. Checked again at least
    every HONOURED_SECONDS (a check takes milliseconds; resolve is called for every file)."""
    loc = loc or {}
    m = loc.get("project_paths")
    if not str(loc.get("projects_root") or "").strip() or not isinstance(m, dict) or not m:
        return {}, []
    key = json.dumps([loc.get("projects_root"), loc.get("portfolio"), loc.get("never_index"), m, os.path.expanduser("~")],
                     sort_keys=True, default=str)
    hit, now = _HONOURED.get(key), time.monotonic()
    if hit and now - hit[0] < HONOURED_SECONDS:
        return hit[1], hit[2]
    if _CHECKING[0]:
        return {}, []
    _CHECKING[0] = True
    try:
        raw, roots, dropped = _loc_raw_roots(loc), {}, []
        for name, value in m.items():
            why = project_mapping_problem(name, value, loc)
            if why is None and name in raw:      # Cap's LOW 5: kept under the register's spelling (case, Unicode form)
                roots[_register_spelling(name)] = raw[name]
            else:
                why = why or "it isn't a folder name with a path"
                dropped.append({"folder": str(name), "path": value if isinstance(value, str) else "",
                                "why": re.sub(r"^Not saved: ", "", why)})
    finally:
        _CHECKING[0] = False
    if len(_HONOURED) > 16:
        _HONOURED.clear()
    _HONOURED[key] = (now, roots, dropped)
    return roots, dropped


def _register_spelling(name) -> str:
    """The register's own spelling of folder name `name` (compared as macOS compares names), or `name` when it isn't there."""
    f = _fold(name)
    return next((v for v in register_folders().values() if _fold(v) == f), name)


def _mapping() -> dict:
    """#385: {folder name: real Path} of every honoured entry, archived projects' too: what resolve and rel map (an archived
    project's stored paths still open, in its archive slot). Never what reach takes: that is project_roots."""
    return _loc_honoured(locations())[0]


def _registered(name) -> bool:
    """Whether folder name `name` is a project in the register now (compared as macOS compares names)."""
    f = _fold(name)
    return any(_fold(v) == f for v in register_folders().values())


def project_roots() -> dict:
    """#385: {register folder name: real Path} for every project in the register mapped to its own folder (locations.project_paths),
    whether or not the folder is there now (callers check; nothing is ever created here). {} without a projects_root, or with no
    mapping. Fail closed: an entry project_mapping_problem refuses is never here (dropped_project_paths lists it), and nor is an
    archived project's (Cap's LOW 1: it isn't in the register, its old place is gone, and its archive slot is never in ask
    creaite's reach; resolve still maps its stored paths to the slot)."""
    return {k: p for k, p in _mapping().items() if _registered(k)}


def unreachable_own_folder(path):
    """#385 (Cap's review, MEDIUM 2): the saved place (with ~) of the project folder of its own that `path` would be inside when
    that folder isn't there now (OneDrive not running, a drive not connected), else None. A caller about to make folders for
    `path` stops instead: creaite never creates a project's own folder."""
    p = Path(os.path.abspath(str(path)))
    saved = project_paths()
    for k, r in project_roots().items():
        if (p == r or r in p.parents) and not r.is_dir():
            return saved.get(k) or str(r)
    return None


def dropped_project_paths() -> list:
    """#385: [{folder, path, why}] for every locations.project_paths entry left out because it breaks the rules on saving."""
    return list(_loc_honoured(locations())[1])


def project_paths() -> dict:
    """#385: locations.project_paths as saved ({folder name: the stored value, with ~}), only the entries project_roots honours."""
    return _saved_values(project_roots())


def _saved_values(roots) -> dict:
    """{key of `roots`: the value saved for it}, the saved key matched as macOS compares names (it may be spelled otherwise)."""
    m = locations().get("project_paths")
    m = m if isinstance(m, dict) else {}
    return {k: next((v for n, v in m.items() if _fold(n) == _fold(k)), "") for k in roots}


def mapped_project_paths() -> dict:
    """#385: as project_paths, archived projects' entries too (the settings entry is kept on archive: Health shows where each
    archived project is)."""
    return _saved_values(_mapping())


def _mapped_name(name, roots=None):
    """The mapping's own key for the folder name `name` (compared as macOS compares names), or None when it isn't mapped."""
    roots = project_roots() if roots is None else roots
    if not roots or not name:
        return None
    if name in roots:
        return name
    f = _fold(name)
    return next((k for k in roots if _fold(k) == f), None)


def archive_slot(name) -> Path:
    """#385: where the mapped project `name` is archived to: <parent of its folder>/99 Archive/<name> (Alan, 26-10-2026: beside
    the project, a rename on the same volume). None when `name` isn't mapped (its slot is <projects root>/99 Archive/<name>)."""
    roots = _mapping()
    k = _mapped_name(name, roots)
    return roots[k].parent / ARCHIVE / k if k else None


def _bases(roots=None) -> list:
    """(real folder, stored prefix) for every place a stored path is built on when the projects are outside the vault: the
    portfolio, each mapped project, each mapped project's archive slots (99 Archive and the old two), and the projects root; the
    longest real path first, so a file is stored under the most specific one."""
    roots = _mapping() if roots is None else roots
    out = [(portfolio_dir(), LOGICAL_PORTFOLIO), (projects_root(), LOGICAL)]
    for name, p in roots.items():
        out.append((p, f"{LOGICAL}/{name}"))
        out += [(p.parent / a / name, f"{LOGICAL}/{a}/{name}") for a in archive_names()]
    return sorted(((_resolved(b), pre) for b, pre in out), key=lambda x: -len(x[0].parts))


def base_of(path):
    """#385: the base (resolved) a real path lies under, the longest match first: a mapped project's folder, the portfolio folder
    or the projects root. An archive slot beside a mapped project is not a base (only tracker.py apply moves a folder there).
    None when the path is under none of them, or the projects are in the vault."""
    if not external():
        return None
    p = _resolved(path)
    bases = [projects_root(), portfolio_dir(), *project_roots().values()]
    for b in sorted((_resolved(b) for b in bases), key=lambda x: -len(x.parts)):
        if p == b or b in p.parents:
            return b
    return None


def parts_below_base(path):
    """#385: (base, the path's parts below it) for base_of(path), or None: what tracker.safe_path and reach need to check the
    skipped names (99 Archive, _Templates, 99 System) under every base, not only the projects root."""
    b = base_of(path)
    return None if b is None else (b, _resolved(path).parts[len(b.parts):])


def missing_project_paths() -> list:
    """#385: [{code, folder, path}] for every registered project mapped to a folder that isn't there (an unmounted drive, OneDrive
    not running, a folder moved by hand); `path` is the stored value (with ~). Nothing is created. An archived project is not in the
    register, so it is never listed."""
    roots, saved = project_roots(), project_paths()
    out = []
    for code, name in sorted(register_folders().items()):
        k = _mapped_name(name, roots)
        if k and not roots[k].is_dir():
            out.append({"code": code, "folder": k, "path": saved.get(k, "")})
    return out


def in_mapped_notes(c, name=None, archived=False) -> bool:
    """#385: whether real or written path `c` is in a mapped project's notes folder by name (NOTES_SHAPES relative to the
    project's own folder: <P>/<notes>, <P>/99 Archive/<notes>; archived: also the archive slot's <slot>/<notes> and
    <slot>/99 Archive/<notes>). For tracker's copy guard (the projects root's shapes stay in notes_shape)."""
    roots = _mapping()
    if not roots:
        return False
    name = [_fold(x) for x in Path(name or folder_name("notes")).parts if x not in ("", ".")]
    if not name:
        return False
    arch = _arch_names()
    c = [_fold(x) for x in Path(os.path.normpath(os.path.abspath(str(c)))).parts]
    for k, p in roots.items():
        places = [p] + ([p.parent / a / k for a in archive_names()] if archived else [])
        if any(_notes_below(c, b, name, arch) for b in places):
            return True
    return False


def _notes_below(c, b, name, arch) -> bool:
    """Whether folded parts `c` are below folder `b` (as written or real) in its notes folder `name` (folded parts), directly or
    in one of its archive folders `arch`."""
    for form in {os.path.normpath(os.path.abspath(b)), os.path.realpath(b)}:
        bp = [_fold(x) for x in Path(form).parts]
        if c[:len(bp)] != bp or len(c) == len(bp):
            continue                              # not below this form of the folder: try the other
        rest = c[len(bp):]
        if rest[:len(name)] == name or (rest and rest[0] in arch and rest[1:1 + len(name)] == name):
            return True
    return False


def mapped_notes_places(name, loc=None) -> list:
    """#385: the folders that are a mapped project's notes for notes folder `name` (notes_places' shapes, relative to each mapped
    folder and its archive slots), for the notes rename check."""
    out = []
    for k, p in _loc_project_roots(loc if loc is not None else locations()).items():
        for b in [p] + [p.parent / a / k for a in archive_names()]:
            out += [b / name] + [b / a / name for a in archive_names()]
    return out
# ===== end #385 (the mapping); its checks on save are project_paths_problem, below =====


def _resolved(p) -> Path:
    """Path(p).resolve(), the same on every Python: CPython 3.9.25's realpath raises OSError (EINVAL, with the full path) when a link
    at the last part is swapped for a file between its lstat and its readlink, where later versions keep that part as it is. So
    does this: the folder is resolved and the name kept (v2.6 gate: the E1 flip test on Python 3.9). v2.6.1 (security review L1):
    only for EINVAL, and never when the last part is `.`, `..` or empty, where keeping the name would hand back a path that was
    not normalised; any other OSError, and that case, is raised as before."""
    try:
        return Path(p).resolve()
    except OSError as e:
        name = Path(p).name
        if e.errno != errno.EINVAL or name in ("", ".", ".."):
            raise
        return Path(p).parent.resolve() / name


def rel(p: Path) -> str:
    """Path as stored anywhere (database, proposals, links): relative to ROOT with forward slashes; a path in the projects
    root or the portfolio folder is stored under the logical prefix projects/ (BL-85)."""
    p = _resolved(p)
    if external():
        roots = _mapping()
        bases = _bases(roots) if roots else ((portfolio_dir().resolve(), LOGICAL_PORTFOLIO), (projects_root().resolve(), LOGICAL))
        for base, prefix in bases:              # #385: a mapped project's folder (and its archive slot), the longest first
            try:
                return (Path(prefix) / p.relative_to(base)).as_posix()
            except ValueError:
                continue
    return p.relative_to(ROOT).as_posix()


def resolve(stored, archived=True) -> Path:
    """The inverse of rel: a stored path as a real path. Not checked for safety; tracker.safe_path does that. An archived project's
    path is mapped into 99 Archive (BL-09) unless `archived` is False (the apply's own folder moves). #252: a stored path that
    names an archive folder (an apply's record keeps the name it had) follows a folder renamed by hand: see follow_stored."""
    s = str(stored).replace("\\", "/")
    p = _resolve_raw(s, archived)
    if not _names_archive(s) or os.path.lexists(p):      # v2.6 review: no look at the disk for an ordinary path (the hot path)
        return p
    f = follow_stored(s)
    return _resolve_raw(f, archived) if f != s else p


def _names_archive(s) -> bool:
    """Whether a stored path (forward slashes) is one follow_stored could change: under projects/, with an archive folder part."""
    parts = s.split("/")
    return parts[0] == LOGICAL and any(i and is_archive_name(x) for i, x in enumerate(parts))


def _resolve_raw(stored, archived=True) -> Path:
    """resolve without following a renamed archive folder."""
    s = str(stored).replace("\\", "/")
    if Path(s).is_absolute():
        return Path(s)
    if external():
        if s == LOGICAL_PORTFOLIO or s.startswith(LOGICAL_PORTFOLIO + "/"):
            p = portfolio_dir() / s[len(LOGICAL_PORTFOLIO):].lstrip("/")
            return archived_file(portfolio_dir(), p.relative_to(portfolio_dir()).parts, p) if archived else p   # BL-03
        if s == LOGICAL or s.startswith(LOGICAL + "/"):
            mapped = _resolve_mapped(s, archived)       # #385: a project in a folder of its own
            if mapped is not None:
                return mapped
            p = projects_root() / s[len(LOGICAL):].lstrip("/")
            return archived_path(p) if archived else p
    return archived_path(ROOT / s) if archived and (s == LOGICAL or s.startswith(LOGICAL + "/")) else ROOT / s


def _resolve_mapped(s, archived=True):
    """#385: the real path of stored path `s` (under projects/) when it names a mapped project: projects/<folder>/… is in the
    folder's own place (or, archived, in its archive slot when the folder isn't there), and projects/<archive>/<folder>/… is in
    that slot. None for anything else (resolved as before)."""
    roots = _mapping()
    if not roots:
        return None
    parts = s.split("/")[1:]
    if not parts or not parts[0]:
        return None
    k = _mapped_name(parts[0], roots)
    if k:
        p = roots[k].joinpath(*parts[1:])
        return _archived_mapped(k, roots[k], parts[1:], p) if archived else p
    if is_archive_name(parts[0]) and len(parts) > 1:
        k = _mapped_name(parts[1], roots)
        if k:
            return roots[k].parent.joinpath(parts[0], k, *parts[2:])
    return None


def _archived_mapped(name, root, rest, p):
    """#385 (archived_path for a mapped project): p, a report or minutes in the project's own archive (BL-03) when the project is
    in place, or its place in the archive slot beside the folder (99 Archive, then the old two) when the project is archived."""
    if root.exists():
        return archived_file(root, tuple(rest), p)
    return next((d / name / Path(*rest) for d in archive_dirs(root.parent) if (d / name).is_dir()), p)


# ===== BL-09: archived projects =====
# An archived project's folder is <projects root>/99 Archive/<folder> (#252; _Archive and zz Archive until they are dropped). Stored
# paths never change (Alan, 14-10-2026): resolve maps projects/<folder>/… to 99 Archive/<folder>/… when <folder> is not in the
# projects root but is in an archive folder, so every link still opens and a restore rewrites nothing. A move into or out of an
# archive folder is made only by tracker.py apply (reach.archive_move_problem).

def _fold(x) -> str:
    import unicodedata
    return unicodedata.normalize("NFC", str(x)).casefold()


def archive_names() -> tuple:
    """#252: every name an archive folder may have: 99 Archive, then the two old ones (read and skipped for one release)."""
    return (ARCHIVE, *OLD_ARCHIVES)


def is_archive_name(name) -> bool:
    """#252: whether a folder called `name` is an archive folder, whole name only (never 99 Archivement or `99 Archive `), and
    ignoring case and Unicode form as macOS's file system does."""
    return _fold(name) in {_fold(n) for n in archive_names()}


def is_skipped(name) -> bool:
    """Whether a folder called `name` is one creaite never lists, indexes, reads or writes (skipped_names, compared as macOS
    compares names: `99 archive` is `99 Archive`)."""
    return _fold(name) in {_fold(n) for n in skipped_names()}


def archive_dir(name=None) -> Path:
    """<projects root>/99 Archive: where a project is archived to (BL-09, #252). Reading looks in archive_dirs as well. #385: for
    a project folder `name` mapped to a folder of its own, the 99 Archive beside that folder (archive_slot is the folder in it)."""
    slot = archive_slot(name) if name else None
    return slot.parent if slot is not None else projects_root() / ARCHIVE


def archive_dirs(base: Path) -> list:
    """#252: the archive folders that exist directly in `base` (a projects root or an engagement folder), 99 Archive first, then
    _Archive and zz Archive; when more than one is there all are read. Never a symlink. A folder listing only."""
    out = []
    for name in archive_names():
        d = Path(base) / name
        if d.is_dir() and not d.is_symlink() and not any(os.path.samefile(d, x) for x in out):   # one folder, two cases: once
            out.append(d)
    return out


def follow_stored(stored) -> str:
    """#252: the stored path `stored`, or, when nothing is at it and its archive folder's name (99 Archive, _Archive or zz Archive)
    has been renamed by hand (no migration: Alan renames his own), the same stored path with that part named as the folder that is
    there now (99 Archive tried first). An apply's record keeps the name the folder had when it was made, so a restore, Files'
    Archived list, Move back and Undo look the file up through this. Anything else is returned as it is."""
    s = str(stored).replace("\\", "/")
    parts = s.split("/")
    at = [i for i, x in enumerate(parts) if i and is_archive_name(x)]
    if parts[0] != LOGICAL or not at or len(at) > 2 or ".." in parts or os.path.lexists(_resolve_raw(s, False)):
        return s
    import itertools
    for names in itertools.product(archive_names(), repeat=len(at)):
        q = list(parts)
        for i, n in zip(at, names):
            q[i] = n
        cand = "/".join(q)
        if not _archive_symlink(cand, at) and os.path.lexists(_resolve_raw(cand, False)):
            return cand
    return s


def _archive_symlink(stored, at) -> bool:
    """#252: whether any archive folder part of the stored path (at: their positions) is a symlink, which is never followed
    (archive_dirs skips one too): a link to another engagement's archive must not list or move that engagement's files."""
    parts = stored.split("/")
    return any(_resolve_raw("/".join(parts[:i + 1]), False).is_symlink() for i in at)


def canonical_archive(stored):
    """#252: a stored path with each archive folder part (99 Archive, _Archive, zz Archive, any case) named 99 Archive, to tell
    whether two records mean the same file whichever name the archive folder had when each was made. Not a path to open."""
    return "/".join(ARCHIVE if i and is_archive_name(x) else x for i, x in enumerate(str(stored or "").split("/")))


def free_archive_path(base, sub: str, stem: str, ext: str = "") -> Path:
    """#252: <base>/99 Archive/<sub>/<stem><ext>, or <stem>-2<ext>, -3… until the name is free in 99 Archive and in every old
    archive folder beside it: a destination in 99 Archive that isn't there must not be followed (follow_stored) to a file of that
    name in _Archive or zz Archive, which would make a free move look like one onto an existing file."""
    dirs = [Path(base) / ARCHIVE] + [d for d in archive_dirs(base) if d != Path(base) / ARCHIVE]
    p, n = f"{stem}{ext}", 2
    while any(os.path.lexists(d / sub / p) for d in dirs):
        p, n = f"{stem}-{n}{ext}", n + 1
    return dirs[0] / sub / p


def archived_path(p: Path) -> Path:
    """p, or its place in an archive folder when p is in an archived project's folder (that folder isn't in the projects root, but is
    in 99 Archive, or in _Archive or zz Archive until they are dropped). Anything else is returned as it is."""
    for k, r in _mapping().items():              # #385: a mapped project's own folder, archived beside itself
        try:
            return _archived_mapped(k, r, Path(p).relative_to(r).parts, p)
        except ValueError:
            continue                              # not in this mapped project's folder: try the next one
    root = projects_root()
    try:
        parts = Path(p).relative_to(root).parts
    except ValueError:
        return p
    if parts and parts[0] == portfolio_dir().name and (root / parts[0]) == portfolio_dir():
        return archived_file(root / parts[0], parts[1:], p)              # BL-03: portfolio minutes in _Portfolio/99 Archive
    if not parts or is_archive_name(parts[0]) or parts[0].startswith((".", "_")):
        return p
    if (root / parts[0]).exists():
        return archived_file(root / parts[0], parts[1:], p)              # BL-03: a report or minutes moved into its own archive
    return next((d / Path(*parts) for d in archive_dirs(root) if (d / parts[0]).is_dir()), p)


def archived_file(base: Path, rest, p: Path) -> Path:
    """BL-03: p (base/rest, in a project folder that is in place), or, when p isn't there but base/99 Archive/rest is (or, #252,
    base/_Archive/rest or base/zz Archive/rest), that: a report, minutes or Steerco one-pager archived into the engagement's own
    archive folder keeps its stored path (Alan, 14-10-2026). #124: only those folders' files. A deleted note in
    <…>/99 Archive/<notes folder>/ is not mapped, so a new note may take its old name (its stored path is the notes folder's
    again), and the deleted one is reached only by Move back."""
    if not rest or is_archive_name(rest[0]) or os.path.lexists(p) or "/".join(rest[:-1]) not in archivable_folders():
        return p
    return next((m for m in (d / Path(*rest) for d in archive_dirs(base)) if m.is_file()), p)


ARCHIVED_FILE_KINDS = ("minutes", "weekly_reports", "client_reports", "steerco")    # BL-03: what moves into an engagement's 99 Archive


def archivable_folders() -> list:
    """BL-03: the folders, relative to an engagement (or project) folder, whose dated files move into its own 99 Archive after
    archive.reports_after_months: minutes, weekly and client reports and Steerco one-pagers (never transcripts, agendas or
    documents)."""
    return sorted({folder_name(k).strip("/") for k in ARCHIVED_FILE_KINDS})


# ===== end BL-09 =====


rel_project, resolve_project = rel, resolve         # the names the brief uses


def allowed_roots() -> list:
    """Where creaite may read and write project files: the vault and, if set, the projects root and (#385) each project mapped to a
    folder of its own (never its parent or its archive slot)."""
    if not external():
        return [ROOT.resolve()]
    return [ROOT.resolve(), projects_root().resolve()] + [p.resolve() for p in project_roots().values()]


def __getattr__(name):
    """PROJECTS and friends, worked out from the `locations` setting on each use (PEP 562)."""
    if name == "PROJECTS":
        return projects_root()
    if name == "PORTFOLIO":
        return portfolio_dir()
    if name == "REGISTER":
        return portfolio_dir() / "project-register.md"
    if name == "PORTFOLIO_MEMORY":
        return portfolio_dir() / "PORTFOLIO.md"
    if name == "PEOPLE_REGISTER":
        return portfolio_dir() / "people-register.md"        # BL-55: everyone who owns an item; read every run, edited through proposals
    raise AttributeError(f"module 'paths' has no attribute {name!r}")


def register_folders() -> dict:
    """{code: folder name} from the register's "Folder under projects/" column."""
    def load(p):
        """{code: folder} from one register file's table, or {} when it can't be read."""
        out = {}
        if not p:
            return out
        try:
            lines = p.read_text(encoding="utf-8").splitlines()
        except OSError:
            return out
        cols = None
        for ln in lines:
            if not ln.startswith("|"):
                if cols and out:
                    break
                continue
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if cols is None:
                if cells and cells[0] == "Code" and any(c.lower().startswith("folder") for c in cells):
                    cols = [i for i, c in enumerate(cells) if c.lower().startswith("folder")][0]
                continue
            if set("".join(cells)) <= set("-: "):
                continue
            if len(cells) > cols and re.fullmatch(r"[A-Z][A-Z0-9]{2,6}", cells[0]) and cells[cols]:
                out[cells[0]] = cells[cols]
        return out
    return _cached(REGISTER_PATH(), load)


def REGISTER_PATH() -> Path:
    """The project register: project-register.md in the portfolio folder."""
    return portfolio_dir() / "project-register.md"


def project_dir(code: str) -> Path:
    """The folder for a project code: the register's "Folder under projects/", else (the default layout) the one folder whose name
    starts with the code, e.g. 'ABC' -> projects/ABC Example Programme."""
    root = projects_root()
    named = register_folders().get(code)
    roots = project_roots()
    k = _mapped_name(named, roots)
    if k:
        return roots[k]                            # #385: its own folder, there or not (never created here)
    if named and (root / named).is_dir():
        return root / named
    if external():
        if named:
            return root / named                    # registered, not created yet (a new project's folder)
        raise LookupError(f"Project {code} has no folder in the register (Folder under projects/)")
    matches = [d for d in root.iterdir() if d.is_dir() and d.name.split(" ", 1)[0] == code]
    if len(matches) != 1:
        raise LookupError(f"Expected one folder for project {code} under projects/, found {len(matches)}")
    return matches[0]


def stored_folder(code: str, d=None) -> str:
    """#385: the folder name a project's stored paths use (projects/<this>/…): for a project in a folder of its own, the register's
    folder name (its real folder may be called anything); else the folder's own name. `d` is project_dir(code) when known."""
    k = _mapped_name(register_folders().get(code), project_roots())
    return k if k else (d if d is not None else project_dir(code)).name


def project_folders() -> list:
    """[(code, folder)] for every project, the portfolio folder last as '_portfolio'. With an outside projects root only registered
    projects (the folder holds other things), each in its own mapped folder when it has one (#385); in the default layout, every
    folder under projects/. A folder that isn't there is left out (a mapped one is listed by missing_project_paths)."""
    out = []
    if external():
        roots = project_roots()
        for code, name in sorted(register_folders().items()):
            k = _mapped_name(name, roots)
            d = roots[k] if k else projects_root() / name      # #385: a mapped one's own folder; one not there is in
            if d.is_dir():                                       # missing_project_paths (Health), never left out unsaid
                out.append((code, d))
    else:
        for d in sorted(x for x in projects_root().iterdir() if x.is_dir()):
            if d != portfolio_dir() and not is_skipped(d.name):          # BL-09: never 99 Archive (archived projects)
                out.append((d.name.split(" ", 1)[0], d))
    if portfolio_dir().is_dir():
        out.append(("_portfolio", portfolio_dir()))
    return out


def folder_name(kind: str) -> str:
    """The folder for a kind of file, relative to the engagement folder: transcripts, minutes, weekly_reports, client_reports,
    adhoc_documents, images, agendas, notes (documents has no folder of its own with an outside root: see document_files)."""
    return (locations()["folders"] if external() else DEFAULT_FOLDERS).get(kind) or DEFAULT_FOLDERS[kind]


def folder(code: str, kind: str) -> Path:
    """The real folder of one kind (minutes, transcripts, agendas, reports...) for a project or _portfolio (BL-85)."""
    return (portfolio_dir() if code == "_portfolio" else project_dir(code)) / folder_name(kind)


def resolve_image(project_folder: Path, ref: str) -> Path:
    """A Current-state image reference. In CLAUDE.md it is written `images/<name>` whichever folder holds the pictures; with an outside
    projects root the `images` folder is the mapped one (locations.folders.images), so references never contain spaces.
    v2.5.0 leak fix: a reference that is absolute, holds `..`, a backslash, a URL or a drive letter, or whose real path leaves the
    project folder, gives a path that does not exist (REFUSED_IMAGE), never the outside file."""
    ref = str(ref)
    refused = Path(project_folder) / REFUSED_IMAGE
    if not safe_image_ref(ref):
        return refused
    if external() and ref.startswith("images/"):
        f = Path(project_folder) / folder_name("images") / ref[len("images/"):]
    else:
        f = Path(project_folder) / ref
    try:
        if Path(project_folder).resolve() not in f.resolve().parents:
            return refused
    except (OSError, RuntimeError, ValueError):
        return refused
    return f


REFUSED_IMAGE = ".creaite-refused-image/none"      # what resolve_image gives for a reference it won't follow: never a real file


def safe_image_ref(ref) -> bool:
    """Whether a picture reference is a plain relative path: no absolute path, `..`, backslash, URL, drive letter or control character."""
    ref = str(ref or "")
    if not ref or ref.startswith(("/", "~")) or "\\" in ref or ":" in ref or any(ord(c) < 32 for c in ref):
        return False
    return all(p not in ("", ".", "..") for p in ref.split("/"))


def image_file(project_folder: Path, ref: str):
    """The real picture file an `images/<name>` reference names, or None: only a safe relative reference under `images/`, a regular
    file (never a symlink, nor reached through one, never a hard link) whose real path sits in the project's own images folder, itself
    inside the project folder (v2.5.0 leak fix)."""
    ref = str(ref or "")
    if not (ref.startswith("images/") and safe_image_ref(ref)):
        return None
    root = Path(project_folder) / (folder_name("images") if external() else "images")
    f = root / ref[len("images/"):]
    try:
        real_root = root.resolve()
        if Path(project_folder).resolve() not in real_root.parents:     # a mapped images folder outside the project (`../..`)
            return None
        if root.is_symlink() or not f.is_file() or f.stat().st_nlink > 1:     # a hard link may name an outside file
            return None
        p = f
        while p != root:                        # no symlink anywhere between the images folder and the file
            if p.is_symlink():
                return None
            p = p.parent
        if real_root not in f.resolve().parents:
            return None
    except (OSError, RuntimeError, ValueError):
        return None
    return f


def extract_dirs(code: str) -> list:
    """The only folders ever extracted from: minutes and transcripts."""
    return [folder(code, "minutes"), folder(code, "transcripts")]


def never_index() -> list:
    """The folder names creaite never lists, indexes, reads or writes: the saved `never_index` plus the reserved ones, so a list saved
    by an older release (or emptied by hand) never exposes 99 System, where the backup copies are (BL-112)."""
    saved = [str(n) for n in locations().get("never_index") or []]
    return saved + [n for n in ALWAYS_NEVER_INDEX if n not in saved]


def skipped_names() -> list:
    """never_index plus every old archive name (#252: _Archive and zz Archive, for one release): never listed, indexed, read or
    written, and never for reach.classify. zz Archive is left out of ask creaite's deny lists and permission patterns (Alan,
    14-10-2026), as before; 99 Archive and _Archive are in them."""
    names = never_index()
    return names + [n for n in OLD_ARCHIVES if n not in names]


def _excluded_dirs(code: str) -> list:
    base = portfolio_dir() if code == "_portfolio" else project_dir(code)
    kinds = ("minutes", "transcripts", "weekly_reports", "client_reports", "adhoc_documents", "images", "steerco", "agendas", "notes")
    skip = [folder(code, k) for k in kinds]   # BL-135: agendas are their own kind in Files; BL-301: so are notes
    return skip, [base / n for n in skipped_names()]


def document_roots(code: str) -> list:
    """Where a project's documents are: its documents/ folder, or with an outside root the whole engagement folder (minus the
    meeting and report folders, never_index and creaite's own images)."""
    base = portfolio_dir() if code == "_portfolio" else project_dir(code)
    return [base] if external() else [base / "documents"]


def is_online_only(p: Path) -> bool:
    """A OneDrive placeholder: a file whose content isn't on this device (macOS: a dataless file). Reading one would download it."""
    try:
        st = Path(p).stat()
    except OSError:
        return False
    if getattr(st, "st_flags", 0) & 0x40000000:                 # SF_DATALESS
        return True
    return st.st_size > 0 and getattr(st, "st_blocks", 1) == 0


def document_files(code: str, online: bool = False) -> list:
    """Every document of a project, in a fixed order. Online-only files are left out unless `online` (they are listed by doctor)."""
    base = portfolio_dir() if code == "_portfolio" else project_dir(code)
    ok = lambda f: online or not is_online_only(f)      # noqa: E731
    if not external():
        d = base / "documents"
        return [f for f in sorted(d.rglob("*")) if f.is_file() and not f.name.startswith((".", "~$")) and ok(f)] if d.is_dir() else []
    skip, never = _excluded_dirs(code)
    skip = [s.resolve() for s in skip + never]
    out = []
    for dirpath, dirnames, filenames in os.walk(base):
        here = Path(dirpath).resolve()
        dirnames[:] = sorted(n for n in dirnames if not n.startswith(".") and (here / n) not in skip
                             and not is_skipped(n))
        for n in sorted(filenames):
            f = Path(dirpath) / n
            if n.startswith((".", "~$")) or (here == base.resolve() and n in ("CLAUDE.md", "PORTFOLIO.md", "project-register.md", "people-register.md")):
                continue
            if ok(f):
                out.append(f)
    return out


# ===== BL-301 (v20-notes-server): notes, one Markdown file each, flat in the notes folder; pictures in its _images folder
NOTE_IMAGES = "_images"


def note_files(code: str, online: bool = False) -> list:
    """A project's (or _portfolio's) notes: the .md files directly in its notes folder, by name. The folder is made on the first
    note, so a project without one has none. Hidden and online-only files are left out (unless `online`)."""
    d = folder(code, "notes")
    if not d.is_dir():
        return []
    return [f for f in sorted(d.iterdir()) if f.is_file() and f.suffix.lower() == ".md" and not f.name.startswith((".", "~$"))
            and (online or not is_online_only(f))]


def is_note(p) -> bool:
    """Whether the real or stored path `p` is a note: a .md file directly in a project's or the portfolio's notes folder."""
    p = (resolve(p) if not Path(str(p)).is_absolute() else Path(p)).resolve()
    if p.suffix.lower() != ".md":
        return False
    area = project_area(p)
    if area is None:
        return False
    try:
        return p.parent == folder(area[0], "notes").resolve()
    except (LookupError, OSError):          # a project without a folder: no notes
        return False


NOT_NOTES = ("minutes", "transcripts", "weekly_reports", "client_reports", "adhoc_documents", "steerco", "agendas", "images")


def notes_folder_clash(folders=None) -> list:
    """#124, #128: the kinds whose folder is the notes folder, inside it or around it (case and NFC ignored, "" and "." parts left
    out), as "kind (folder)"; [] when notes have a folder of their own. folders: a locations.folders mapping to check (default:
    the one in use). doctor flags a clash; propose.py setting and the page's settings save refuse one."""
    import unicodedata
    from pathlib import PurePosixPath

    given = None if folders is None else {**LOCATION_DEFAULTS["folders"], **folders}     # as locations() fills a saved one

    def name(kind):
        """The kind's folder as mapped."""
        return folder_name(kind) if given is None else str(given.get(kind) or DEFAULT_FOLDERS[kind])

    def norm(kind):
        """The kind's folder inside the engagement, folded, without empty or "." parts."""
        n = unicodedata.normalize("NFC", name(kind)).casefold().replace("\\", "/")
        return PurePosixPath(*[x for x in n.split("/") if x not in ("", ".")])
    n = norm("notes")
    return [f"{k} ({name(k)})" for k in NOT_NOTES if norm(k) == n or n in norm(k).parents or norm(k) in n.parents]


# #128: where an engagement's notes can be, below the projects folder: <eng>/<notes>, and (archived) <eng>/99 Archive/<notes>,
# 99 Archive/<eng>/<notes>, 99 Archive/<eng>/99 Archive/<notes> ("*" an engagement, "A" 99 Archive, _Archive or zz Archive).
# tracker's copy guard
# matches these shapes (notes_shape) and the rename check lists them (notes_places): one list, so the two never disagree.
NOTES_SHAPES = (("*",), ("*", "A"), ("A", "*"), ("A", "*", "A"))
NOT_A_NOTE = (".DS_Store", "Icon\r")             # Finder's own files (and ._* AppleDouble) are never notes


def _arch_names() -> set:
    return {_fold(n) for n in archive_names()}        # #252: 99 Archive, _Archive and zz Archive


def _exempt(parts, loc=None) -> bool:
    """#128 D2: folded `parts` below the projects folder are in _Templates or in the skeleton itself (its exact path, never
    the rest of its top folder): never an engagement's notes."""
    skel = str((loc if loc is not None else locations()).get("skeleton") or "_Templates/_Skeleton")
    sk = [_fold(x) for x in skel.replace("\\", "/").split("/") if x not in ("", ".")]
    return bool(parts) and (parts[0] == "_templates" or (bool(sk) and parts[:len(sk)] == sk))


def notes_shape(parts, name, archived=True, loc=None) -> bool:
    """#128: whether `parts` (folded, below the projects folder) are inside a notes folder named `name` (folded parts) in one
    of NOTES_SHAPES (only the first unless `archived`)."""
    arch = _arch_names()
    for shape in NOTES_SHAPES if archived else NOTES_SHAPES[:1]:
        head = parts[:len(shape)]
        if len(head) == len(shape) and all((x in arch) if s == "A" else (x not in arch) for s, x in zip(shape, head)) \
                and not _exempt(parts, loc) and parts[len(shape):len(shape) + len(name)] == name:
            return True
    return False


def notes_places(root, name, loc=None) -> list:
    """#128: every folder below `root` that NOTES_SHAPES give for notes folder `name` (a path inside each engagement)."""
    arch = _arch_names()
    out = []
    for shape in NOTES_SHAPES:
        here = [Path(root)]
        for s in shape:
            nxt = []
            for d in here:
                try:
                    kids = [k for k in d.iterdir() if k.is_dir()]
                except OSError:                   # gone or unreadable: nothing there to guard
                    continue
                nxt += [k for k in kids if ((_fold(k.name) in arch) if s == "A" else (_fold(k.name) not in arch))]
            here = nxt
        out += [d / name for d in here if not _exempt([_fold(x) for x in (d / name).relative_to(root).parts], loc)]
    return out


def _holds_files(d) -> bool:
    """A folder with a file or a symlink anywhere below it (never followed), Finder's own files apart; a symlink itself counts."""
    if os.path.islink(d):
        return True
    for _, dirs, files in os.walk(d, followlinks=False):
        if any(os.path.islink(os.path.join(_, x)) for x in dirs):
            return True
        if any(f not in NOT_A_NOTE and not f.startswith("._") for f in files):
            return True
    return False


def _loc_root(loc) -> Path:
    root = str((loc or {}).get("projects_root") or "").strip()
    if not root:
        return ROOT / "projects"
    p = Path(os.path.expanduser(root))
    return p if p.is_absolute() else ROOT / p


def _loc_notes(loc) -> str:
    """#128 D1: the notes folder's name in effect for `locations` value `loc`: `notes` in the vault's own layout (no
    projects_root), else the mapped one (paths.folder_name's rule)."""
    if not str((loc or {}).get("projects_root") or "").strip():
        return DEFAULT_FOLDERS["notes"]
    folders = (loc or {}).get("folders")
    return str({**LOCATION_DEFAULTS["folders"], **(folders if isinstance(folders, dict) else {})}.get("notes")
               or DEFAULT_FOLDERS["notes"])


def notes_rename_problem(old, new):
    """#128 F1: why `locations` mapping `new` can't replace `old` (both whole `locations` values): the notes folder's name
    changes while a folder under the old name holds files, under the old root or the new one (notes_places: every engagement,
    registered or not, the portfolio, their 99 Archive and archived engagements), so those notes would lose the apply's guard.
    D1: the name compared is the one in effect (the vault's own layout uses `notes`), and a new projects folder that holds the
    old one or sits inside it counts too (the notes would be at another depth); a move to an unrelated folder is saved. The
    way to rename: move the folders in Finder first, then change the setting."""
    a, b = _loc_notes(old), _loc_notes(new)
    ro, rn = os.path.realpath(_loc_root(old)), os.path.realpath(_loc_root(new))
    nested = ro != rn and (rn.startswith(ro.rstrip(os.sep) + os.sep) or ro.startswith(rn.rstrip(os.sep) + os.sep))
    if _fold(a.strip("/")) == _fold(b.strip("/")) and not nested:
        return None
    why = f"move the notes folders to “{b}” first" if not nested else "the new projects folder holds the old one or sits " \
        "inside it, so the notes would lose their guard: move the notes out first"
    for root in dict.fromkeys([_loc_root(old), _loc_root(new)]):
        bases = notes_places(root, a, old) + notes_places(root, a, new)
        pf = root / str((new or {}).get("portfolio") or "_Portfolio")
        bases += [pf / a, *(pf / n / a for n in archive_names()), ROOT / "projects" / "_portfolio" / a]
        bases += mapped_notes_places(a, old) + mapped_notes_places(a, new)      # #385: a mapped project's own notes
        for d in dict.fromkeys(bases):
            if os.path.lexists(d) and _holds_files(d):
                return f"Not saved: notes are still in “{a}” ({d.parent.name}): {why}, then change the setting."
    return None


def _engagement_top(top, new) -> bool:
    """#128 L1, D2: folder `top` (below the projects folder) is 99 Archive, the portfolio, a registered engagement, or any
    folder but _Templates that holds a notes folder (an engagement not in the register)."""
    engagements = {_fold(x) for x in register_folders().values()} | {_fold(new.get("portfolio") or "_Portfolio")}
    if _fold(top) in _arch_names() | engagements:
        return True
    d, name = _loc_root(new) / top, _loc_notes(new)
    return _fold(top) != "_templates" and any((d / x / name).is_dir() for x in ("", *archive_names()))


def skeleton_problem(old, new):
    """#128 L1: why `new`'s locations.skeleton can't be saved (a changed one that is empty, ".", has "..", is in 99 Archive, or is
    an engagement's or the portfolio's folder: its notes would lose the by-name guard), or None."""
    if "skeleton" not in (new or {}) or (new or {}).get("skeleton") == (old or {}).get("skeleton"):
        return None                               # left as it was (or the default)
    s = str(new.get("skeleton") or "")
    parts = [x for x in s.replace("\\", "/").split("/") if x not in ("", ".")]
    if not parts or ".." in parts or _engagement_top(parts[0], new):
        return (f"Not saved: locations.skeleton “{s}” isn't a template folder of its own "
                "(never “.”, 99 Archive, an engagement or the portfolio).")
    return None


def locations_change_problem(old, new):
    """#128: why `locations` value `new` can't replace `old` (the page's settings save and propose.py setting), or None: the
    notes folder would share a folder with another kind, a renamed notes folder would leave notes unguarded, or the skeleton
    isn't a template folder of its own."""
    if not isinstance(new, dict) or not isinstance(new.get("folders", {}), dict):          # D3, D4
        return "Not saved: locations and locations.folders must be objects."
    nf, of = new.get("folders"), old.get("folders")
    clash = notes_folder_clash(nf if isinstance(nf, dict) else {}) if nf != of else []
    if clash:
        return f"Not saved: the notes folder would also be the {', '.join(clash)} folder or hold it: give notes a folder of their own."
    return skeleton_problem(old, new) or project_paths_problem(old, new) or notes_rename_problem(old, new)


# ===== #385: checks on saving locations.project_paths =====
def project_path_stored(value) -> str:
    """#385: how a project's folder is stored: its real path (symlinks followed when it is there) written with ~ for the home
    folder; a relative value (below the projects root) is kept as it is."""
    v = str(value or "").strip().replace("\\", "/")
    p = Path(os.path.expanduser(v))
    if not v or not p.is_absolute():
        return v.rstrip("/")
    real = Path(os.path.realpath(p))
    home = Path(os.path.realpath(os.path.expanduser("~")))
    try:
        return "~/" + real.relative_to(home).as_posix()
    except ValueError:
        return real.as_posix()


def _below_or_same(a: str, b: str) -> bool:
    """Whether folded real path `a` is `b` or inside it."""
    return a == b or a.startswith(b.rstrip("/") + "/")


def project_mapping_problem(name, value, loc) -> str:
    """#385: why project folder `name` can't be mapped to `value` (as saved) in `locations` value `loc` (whose project_paths
    holds every mapping, this one included), or None. Refused: no projects folder set; a name that isn't one folder; a path with
    `..`, not written with ~ (or relative to the projects folder), outside the home folder or the home folder itself, inside the
    creaite folder (or holding it), in ~/Library outside ~/Library/CloudStorage, in a hidden folder (~/.config …: Cap's Full
    review, MEDIUM 1), on or holding a place creaite never touches, under (or named) 99 Archive, _Templates or 99 System, a
    symlink, holding the projects folder, inside or holding the portfolio or another registered project's folder in the projects folder, or the same as, inside or holding another mapped project's
    folder. A folder inside the projects folder under another name is fine (Jarvis, 26-10-2026: Alan's "either"). Names compare
    as macOS compares them (case and Unicode form ignored)."""
    loc = loc or {}
    label = f"Not saved: the folder for “{name}”"
    if not str(loc.get("projects_root") or "").strip():
        return "Not saved: a project's own folder needs the projects folder set first (Settings › Folders and OneDrive)."
    why = _mapping_name_problem(name, loc) or _mapping_shape_problem(value, label)
    if why:
        return why
    root = _loc_root(loc)
    real = _mapping_real(value.strip().replace("\\", "/"), root)
    if real is None:
        return f"{label} goes through a shortcut (a symlink): give its real location instead."
    why = _mapping_place_problem(real, root)
    if why:
        return f"{label} {why}"
    why = _inside_other_project(_fold(real), name, loc, root)        # Jarvis, 26-10-2026: elsewhere in the projects folder is fine
    if why:
        return f"{label} {why}"
    why = _never_place(Path(real))
    if why:
        return f"{label} is a place creaite never touches ({why})."
    below_home = Path(real).relative_to(os.path.realpath(os.path.expanduser("~"))).parts
    hidden = next((x for x in below_home if x.startswith(".")), None)
    if hidden:                                   # Cap's MEDIUM 1: ~/.config/git, ~/.ipython/…/startup run things on their own
        return (f"{label} is in (or is) {hidden}, a hidden folder: those hold settings and things that run on their own, "
                "never a project.")
    parts = [_fold(x) for x in below_home]
    if len(parts) == 1 or parts == ["library", "cloudstorage"]:      # Cap's LOW 4: its archive would be ~/99 Archive
        return (f"{label} is directly in your home or Library folder: put it inside a folder there, since its archive goes "
                "beside it (99 Archive in the same folder).")
    return _mapping_overlap_problem(_fold(real), name, loc, root, label)


def _mapping_name_problem(name, loc):
    """#385: why `name` isn't a project folder name a mapping may have, or None."""
    if not isinstance(name, str) or not name.strip() or "/" in name or "\\" in name or name in (".", "..") or "\0" in name \
            or name.startswith((".", "_")) or is_skipped(name) \
            or _fold(name) == _fold(str(loc.get("portfolio") or "_Portfolio")):
        return f"Not saved: “{name}” isn't a project's folder name (one folder, as the project register names it)."
    m = loc.get("project_paths") if isinstance(loc.get("project_paths"), dict) else {}
    if sum(1 for k in m if isinstance(k, str) and _fold(k) == _fold(name)) > 1:     # Cap's LOW 4: macOS has one folder for both
        return f"Not saved: “{name}” is in the list twice, spelled another way (case or accents): keep one entry."
    return None


def _mapping_shape_problem(value, label):
    """#385: why the saved text `value` isn't written as a project's folder may be (empty, `..`, not with ~ or relative), or None."""
    if not isinstance(value, str) or not value.strip():
        return f"{label} is empty: remove the entry instead."
    v = value.strip().replace("\\", "/")
    if ".." in v.split("/"):
        return f"{label} has “..” in it: give the folder itself."
    if "\0" in v:                                   # Cap's LOW 5: a hand edit; never a path
        return f"{label} has a character no folder name can have: give the folder itself."
    if v.rstrip("/") == "~":
        return f"{label} must be inside your home folder (and not the home folder itself)."
    if v.startswith("/") or (len(v) > 1 and v[1] == ":") or (v.startswith("~") and not v.startswith("~/")):
        return f"{label} must be written with ~ for your home folder (~/…), so it works on a new laptop."
    return None


def _mapping_real(v, root):
    """#385: the real path of mapping value `v` (with ~, or relative to the projects folder `root`), or None when a part below
    where it starts is a symlink (a link can be pointed somewhere else later)."""
    start = Path(os.path.expanduser("~")) if v.startswith("~") else root
    rest = Path(os.path.expanduser(v)).relative_to(start).parts if v.startswith("~") else Path(v).parts
    here = start
    for part in rest:
        here = here / part
        if os.path.islink(here):
            return None
    return os.path.realpath(here)


def _mapping_place_problem(real, root):
    """#385: why the real folder `real` is no place for a project (outside home, ~/Library outside CloudStorage, a skipped name,
    the creaite folder, holding the projects folder `root`), as the end of a sentence, or None."""
    home = os.path.realpath(os.path.expanduser("~"))
    f = _fold(real)
    if not f.startswith(_fold(home).rstrip("/") + "/"):
        return "must be inside your home folder (and not the home folder itself)."
    parts = [_fold(x) for x in Path(real).relative_to(home).parts]
    if parts[0] == "library" and parts[1:2] != ["cloudstorage"]:
        return "is in your Library folder: only ~/Library/CloudStorage (OneDrive) may hold a project."
    hit = next((x for x in Path(real).relative_to(home).parts if is_skipped(x)), None)
    if hit:
        return f"is in (or is) {hit}, which creaite never reads or writes."
    vault = _fold(os.path.realpath(ROOT))
    if _below_or_same(f, vault) or _below_or_same(vault, f):
        return "is inside the creaite folder, or holds it: a project lives outside creaite's own folder."
    if _below_or_same(_fold(os.path.realpath(root)), f):
        return "holds the projects folder: give the project's own folder."
    return None


def _mapping_overlap_problem(f, name, loc, root, label):
    """#385: why folded real path `f` is the same as, inside or holding another mapped project's folder, or None."""
    for other, ov in ((loc.get("project_paths") or {}).items() if isinstance(loc.get("project_paths"), dict) else []):
        if other == name or _mapping_shape_problem(ov, ""):
            continue                              # this one, or a malformed entry (refused on its own, never a place)
        op = Path(os.path.expanduser(ov.strip()))
        o = _fold(os.path.realpath(op if op.is_absolute() else root / op))
        if not o.startswith(_fold(os.path.realpath(os.path.expanduser("~"))).rstrip("/") + "/"):
            continue                              # outside the home folder: refused on its own, never a place to overlap
        if o == f:
            return f"{label} is the same folder as “{other}”'s: each project needs a folder of its own."
        if _below_or_same(f, o) or _below_or_same(o, f):
            return f"{label} is inside “{other}”'s folder, or holds it: each project needs a folder of its own."
    return None


def _inside_other_project(f, name, loc, root):
    """#385: why folded real path `f` (the folder for `name`) is, is inside, or holds the portfolio folder or another registered
    project's own folder in the projects folder `root` (one mapped elsewhere is checked by its own place), or None."""
    pf = _fold(os.path.realpath(root / str(loc.get("portfolio") or "_Portfolio")))
    if _below_or_same(f, pf) or _below_or_same(pf, f):
        return "is inside the portfolio folder, or holds it: a project needs a folder of its own."
    mapped = {k: None for k in (loc.get("project_paths") if isinstance(loc.get("project_paths"), dict) else {})}
    for other in register_folders().values():
        if _fold(other) == _fold(name) or _mapped_name(other, mapped):
            continue                                  # this project, or one mapped elsewhere
        o = _fold(os.path.realpath(root / other))
        if _below_or_same(f, o) or _below_or_same(o, f):
            return f"is inside {other}'s folder, or holds it: each project needs a folder of its own."
    return None


def _never_place(real: Path):
    """#385: why the real folder `real` is, or holds, a place on reach's never list (secrets, the operating system, what runs
    commands), or None. reach.py is read only here."""
    try:
        import reach
    except ImportError:                           # a script run without the scripts folder on its path: the other checks hold
        return None
    for op in ("read", "create"):
        why = reach.never_reason(real, op)
        if why:
            return why
    home = reach.home()
    f = _fold(real)
    for base, pattern, _ops, reason in reach.NEVER:
        if base != "home":
            continue
        lit = []
        for x in pattern.split("/"):
            if any(c in x for c in "*?["):
                break
            lit.append(x)
        if lit and _below_or_same(_fold(home.joinpath(*lit)), f):
            return reason
    return None


def project_paths_problem(old, new):
    """#385: why `locations` value `new` can't replace `old` because of locations.project_paths (each entry checked by
    project_mapping_problem, only when the map or the projects folder changes), or None."""
    m = (new or {}).get("project_paths", {})
    if m in ({}, None):
        return None
    if not isinstance(m, dict):
        return "Not saved: locations.project_paths must be an object ({\"<project folder>\": \"~/…\"})."
    old = old or {}
    if all(new.get(k) == old.get(k) for k in ("project_paths", "projects_root", "portfolio")):
        return None
    was = old.get("project_paths") if isinstance(old.get("project_paths"), dict) else {}
    for name, value in m.items():
        why = project_mapping_problem(name, value, new)
        if why:
            return why
        if was.get(name) != value and not _registered(name):    # Cap's LOW 6: only a project in the register gets a new place
            return (f"Not saved: “{name}” isn't a project in the register: only a registered project (not an archived one) "
                    "can be given a folder of its own.")
    return None
# ===== end #385 checks =====


# ===== end BL-301 =====


REPORT_LABELS = (("steerco", "Steerco"), ("weekly_reports", "Weekly"), ("client_reports", "Weekly"), ("adhoc_documents", "Adhoc"))


def report_files(code: str, online: bool = False) -> list:
    """[(file, label)] for a project's report folders (BL-87), the label saying which one: Steerco, Weekly (weekly and client
    reports are filed together) or Adhoc. Steerco is read, never written to. When ad hoc documents share the weekly folder (the
    default layout keeps all reports in reports/), a file named ad hoc is Adhoc; reports/Steerco is the Steerco folder there."""
    out, taken = [], set()
    shared = folder(code, "adhoc_documents").resolve() == folder(code, "weekly_reports").resolve()
    for kind, label in REPORT_LABELS:
        d = folder(code, kind)
        if not d.is_dir():
            continue
        for f in sorted(d.rglob("*")):
            if not f.is_file() or f.name.startswith((".", "~$")) or f.resolve() in taken or not (online or not is_online_only(f)):
                continue
            if f.name.endswith(".client.json"):           # v2.5.1 (#239): a client report's checked snapshot, creaite's own record
                continue
            taken.add(f.resolve())
            out.append((f, "Adhoc" if label == "Weekly" and shared and re.search(r"ad[ _-]?hoc", f.name, re.I) else label))
    return out


def project_files(code: str, online: bool = False, documents: bool = True) -> list:
    """[(file, kind, sub)] for one project: minutes, transcripts, agendas (BL-135: their own kind, `sub` the folder path below Agendas),
    notes (BL-301: their own kind, the note files only: the pictures in _images are not listed),
    reports (Steerco, weekly, client and ad hoc folders) and documents, wherever the `locations` setting puts them. `sub` is a report's folder label (Steerco, Weekly, Adhoc: BL-87) or a
    document's folder path below its root, joined with " › ". `documents=False` leaves documents out and doesn't walk them
    (the Files page's default: the bulk of a large OneDrive); search indexing still reads them."""
    base = portfolio_dir() if code == "_portfolio" else project_dir(code)
    out, seen = [], set()

    def add(d, kind):
        """Add the files under `d` as `kind`, once per folder, skipping hidden, lock and online-only files."""
        if d.is_dir() and d.resolve() not in seen:
            seen.add(d.resolve())
            out.extend((f, kind, "") for f in sorted(d.rglob("*"))
                       if f.is_file() and not f.name.startswith((".", "~$")) and (online or not is_online_only(f)))
    add(folder(code, "minutes"), "minutes")
    add(folder(code, "transcripts"), "transcripts")
    # ===== BL-135 (sprint-prep-files): Agendas are their own kind, listed whether or not documents are, and kept out of the documents walk
    ag = folder(code, "agendas")
    if ag.is_dir() and ag.resolve() not in seen:
        seen.add(ag.resolve())
        out.extend((f, "agendas", " › ".join(f.relative_to(ag).parts[:-1])) for f in sorted(ag.rglob("*"))
                   if f.is_file() and not f.name.startswith((".", "~$")) and (online or not is_online_only(f)))
    nd = folder(code, "notes")
    if nd.is_dir() and nd.resolve() not in seen:          # BL-301: notes are their own kind, never documents
        seen.add(nd.resolve())
        out.extend((f, "notes", "") for f in note_files(code, online))
    out.extend((f, "reports", label) for f, label in report_files(code, online))
    if documents:
        root = base if external() else base / "documents"
        for f in document_files(code, online):
            parts = f.relative_to(root).parts
            out.append((f, "documents", " › ".join(parts[:-1])))
    return out


# ── Dates in file names (BL-85) ────────────────────────────────────────────────
# creaite names what it files `YYYY-MM-DD Title`; Teams names its own `Title-YYYYMMDD_HHMMSS-Meeting Transcript.docx`, `Title-YYYYMMDD.docx`
# (and sometimes has no date at all). The meeting date comes from the name, else from the file's own date (flagged in Review).

_CREAITE_NAME = re.compile(r"(\d{4})-(\d{2})-(\d{2}) (.+)")
_TEAMS_NAME = re.compile(r"(.+)-(\d{4})(\d{2})(\d{2})(?:_\d{6})?(?:UTC)?(?:-(?:Meeting )?(?:Transcript|Recording))?", re.I)


def _valid(y, m, d):
    from datetime import date
    try:
        return date(int(y), int(m), int(d)).isoformat()
    except ValueError:
        return None


def name_date(name: str):
    """(YYYY-MM-DD, title, how) read from a file name, or (None, title, None) when it has no date. how: "creaite" or "teams"."""
    stem = Path(name).stem if Path(name).suffix and len(Path(name).suffix) <= 6 else Path(name).name
    m = _CREAITE_NAME.fullmatch(stem)
    if m and _valid(*m.group(1, 2, 3)):
        return _valid(*m.group(1, 2, 3)), m.group(4).strip(), "creaite"
    m = _TEAMS_NAME.fullmatch(stem)
    if m and _valid(*m.group(2, 3, 4)):
        return _valid(*m.group(2, 3, 4)), m.group(1).strip(), "teams"
    return None, re.sub(r"[-_ ]*(Meeting )?(Transcript|Recording)$", "", stem, flags=re.I).strip(), None


def file_date(path) -> tuple:
    """(YYYY-MM-DD, how): the date in the file's name, else the file's own date (how "file"; "" if it can't be read)."""
    day, _, how = name_date(Path(path).name)
    if day:
        return day, how
    try:
        from datetime import datetime
        return datetime.fromtimestamp(Path(path).stat().st_mtime).strftime("%Y-%m-%d"), "file"
    except OSError:
        return "", "file"


def online_only_files() -> list:
    """[(code, kind, file)] for every project file that is a OneDrive placeholder (its content isn't on this device). creaite never
    reads these (reading one would download it): indexing and extraction skip them, and doctor lists them."""
    out = []
    for code, _ in project_folders():
        out += [(code, kind, f) for f, kind, _ in project_files(code, online=True) if is_online_only(f)]
    return out


# ── What may be read and written in the project folders (BL-93) ────────────────
# Reading: every document of a project (never an online-only file, never 99 Archive or _Templates). Writing: creaite may create files
# in any folder of a project when producing something Alan asked for and approved, and change an existing one only when Alan asks, shown
# and confirmed, a copy kept first (filechange.py). Everything is inside a project folder or the vault: never outside, never _Templates
# or 99 Archive, never a hidden file.

def project_area(path):
    """(code, path below its folder) when `path` (a stored path or a real one) is inside a project's folder or the portfolio folder;
    else None. Nothing is checked about the file itself."""
    p = (resolve(path) if not Path(str(path)).is_absolute() else Path(path)).resolve()
    for code, folder in project_folders():
        f = folder.resolve()
        if p == f or f in p.parents:
            return code, p.relative_to(f).parts
    return None


def project_path_problem(path, write=False):
    """None if `path` may be read (or created in, when `write`); else a plain reason."""
    if ".." in Path(str(path)).parts:
        return "a path with .. in it"
    area = project_area(path)
    if area is None:
        return "it isn't inside a project folder (or the portfolio folder)"
    code, parts = area
    hit = next((part for part in parts if is_skipped(part)), None)
    if hit:
        return f"{hit} is never read or written by creaite"
    if write and any(part.startswith(".") for part in parts):
        return "creaite never writes a hidden file"
    return None



def consume_draft(spec_file, file=None) -> str:
    """BL-118: delete the draft input a staging command has finished with, so nothing piles up in system/staging/drafts/ (where draft
    minutes also live). Call it only after the output is written and checked. Deletes only the exact .json file passed in, and
    only when it sits directly in the drafts folder once the path is resolved (so `..` and symlinks can't reach anything else);
    a symlink itself is left alone. Prints one line (to `file`, stdout unless a command's output is data) and returns the name, or
    returns '' when nothing was removed."""
    try:
        given = Path(spec_file)
        real = given.resolve()
        if given.is_symlink() or real.suffix.lower() != ".json" or real.parent != DRAFTS.resolve() or not real.is_file():
            return ""
        given.unlink()
    except OSError:
        return ""
    print(f"Removed draft input: {real.name}", file=file or sys.stdout)
    return real.name


def tool_pattern(sub: str) -> str:
    """The Claude Code permission pattern for `sub`, a path below the logical projects/ prefix (BL-93): relative to the vault
    when the projects are in it; `~/…` (kept home-relative, like the setting) or `//abs/…` when they are in a projects root."""
    sub = sub.lstrip("/")
    if not external():
        return f"projects/{sub}"
    roots = project_roots()
    head, _, rest = sub.partition("/")
    k = _mapped_name(head, roots)
    if k:                                            # #385: a mapped project's own folder, written with ~ like the setting
        return _pattern_of(roots[k]) + (f"/{rest}" if rest else "")
    portfolio = str(locations().get("portfolio") or "_Portfolio")
    if sub == "_portfolio" or sub.startswith("_portfolio/"):
        sub = portfolio + sub[len("_portfolio"):]
    root = str(locations().get("projects_root")).strip().rstrip("/")
    if root.startswith("~"):
        return f"{root}/{sub}"
    if Path(root).is_absolute():
        return f"/{root}/{sub}"                      # Claude Code writes an absolute path as //abs/path
    return f"{root}/{sub}"


def _pattern_of(p) -> str:
    """#385: a real folder as a permission pattern's start: `~/…` below the home folder, else `//abs/…`."""
    home = Path(os.path.expanduser("~"))
    p = Path(os.path.normpath(str(p)))
    for h in dict.fromkeys([home, home.resolve()]):
        try:
            return "~/" + p.relative_to(h).as_posix()
        except ValueError:
            continue                              # not below this form of the home folder: try the other
    return "/" + p.as_posix()


def tool_patterns(sub: str) -> list:
    """#385: tool_pattern(sub), plus, for a pattern that applies inside every engagement (`**/99 Archive/**`, the never_index
    ones), the same pattern under each mapped project's own folder, which is outside the projects root. Phase 3: the live
    server's deny list uses this so a mapped project's 99 Archive is denied too."""
    out = [tool_pattern(sub)]
    s = sub.lstrip("/")
    if external() and s.startswith("**/"):
        out += [f"{_pattern_of(p)}/{s}" for p in project_roots().values()]
    return out


def never_index_patterns():
    """Permission patterns (below the projects root) for the folders creaite never reads or writes: 99 Archive, _Archive,
    _Templates, 99 System (zz Archive is guarded by reach.classify but not named here, as before: Alan, 14-10-2026)."""
    return [f"**/{n}/**" for n in never_index() if n != OLD_ARCHIVES[-1]]      # BL-09, #252
