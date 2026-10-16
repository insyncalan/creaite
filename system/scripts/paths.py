"""creaite paths — the single place where folder locations are defined.

Every script imports from here. Paths are relative to the vault root, which is
found from this file's own location, so creaite works wherever the folder is copied.
To reorganise folders, change this file (and the path table in CLAUDE.md), nothing else.
"""
from pathlib import Path
import json
import os
import re
import sys

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


def rel(p: Path) -> str:
    """Path as stored anywhere (database, proposals, links): relative to ROOT, forward slashes."""
    return Path(p).resolve().relative_to(ROOT).as_posix()


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
                     "never_index": ["_Archive", "_Templates", "99 System"],     # BL-112: 99 System holds the backup copies
                     "offsite_backup": "_Portfolio/99 System/creaite backups"}
ARCHIVE = "_Archive"               # BL-09: archived projects (<projects root>/_Archive/<folder>) and each engagement's own archive folder
OLD_ARCHIVE = "zz Archive"         # BL-09: the old name, still skipped for one release (Health offers to rename it)
ALWAYS_NEVER_INDEX = (ARCHIVE, "_Templates", "99 System")      # skipped whatever the saved list says (BL-112, BL-09)
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


def rel(p: Path) -> str:
    """Path as stored anywhere (database, proposals, links): relative to ROOT with forward slashes; a path in the projects
    root or the portfolio folder is stored under the logical prefix projects/ (BL-85)."""
    p = Path(p).resolve()
    if external():
        for base, prefix in ((portfolio_dir(), LOGICAL_PORTFOLIO), (projects_root(), LOGICAL)):
            try:
                return (Path(prefix) / p.relative_to(base.resolve())).as_posix()
            except ValueError:
                continue
    return p.relative_to(ROOT).as_posix()


def resolve(stored, archived=True) -> Path:
    """The inverse of rel: a stored path as a real path. Not checked for safety; tracker.safe_path does that. An archived project's
    path is mapped into _Archive (BL-09) unless `archived` is False (the apply's own folder moves)."""
    s = str(stored).replace("\\", "/")
    if Path(s).is_absolute():
        return Path(s)
    if external():
        if s == LOGICAL_PORTFOLIO or s.startswith(LOGICAL_PORTFOLIO + "/"):
            p = portfolio_dir() / s[len(LOGICAL_PORTFOLIO):].lstrip("/")
            return archived_file(portfolio_dir(), p.relative_to(portfolio_dir()).parts, p) if archived else p   # BL-03
        if s == LOGICAL or s.startswith(LOGICAL + "/"):
            p = projects_root() / s[len(LOGICAL):].lstrip("/")
            return archived_path(p) if archived else p
    return archived_path(ROOT / s) if archived and (s == LOGICAL or s.startswith(LOGICAL + "/")) else ROOT / s


# ===== BL-09: archived projects =====
# An archived project's folder is <projects root>/_Archive/<folder>. Stored paths never change (Alan, 14-10-2026): resolve maps
# projects/<folder>/… to _Archive/<folder>/… when <folder> is not in the projects root but is in _Archive, so every link still
# opens and a restore rewrites nothing. A move into or out of _Archive is made only by tracker.py apply (reach.archive_move_problem).

def archive_dir() -> Path:
    """<projects root>/_Archive: where archived projects' folders are (BL-09)."""
    return projects_root() / ARCHIVE


def archived_path(p: Path) -> Path:
    """p, or its place in _Archive when p is in an archived project's folder (that folder isn't in the projects root, but is in
    _Archive). Anything else is returned as it is."""
    root = projects_root()
    try:
        parts = Path(p).relative_to(root).parts
    except ValueError:
        return p
    if parts and parts[0] == portfolio_dir().name and (root / parts[0]) == portfolio_dir():
        return archived_file(root / parts[0], parts[1:], p)              # BL-03: portfolio minutes in _Portfolio/_Archive
    if not parts or parts[0] in (ARCHIVE, OLD_ARCHIVE) or parts[0].startswith((".", "_")):
        return p
    if (root / parts[0]).exists():
        return archived_file(root / parts[0], parts[1:], p)              # BL-03: a report or minutes moved into its own _Archive
    return root / ARCHIVE / Path(*parts) if (root / ARCHIVE / parts[0]).is_dir() else p


def archived_file(base: Path, rest, p: Path) -> Path:
    """BL-03: p (base/rest, in a project folder that is in place), or, when p isn't there but base/_Archive/rest is, that: a
    report, minutes or Steerco one-pager archived into the engagement's own _Archive keeps its stored path (Alan, 14-10-2026).
    #124: only those folders' files. A deleted note in <…>/_Archive/<notes folder>/ is not mapped, so a new note may take its old
    name (its stored path is the notes folder's again), and the deleted one is reached only by Move back."""
    if not rest or rest[0] in (ARCHIVE, OLD_ARCHIVE) or os.path.lexists(p):
        return p
    moved = base / ARCHIVE / Path(*rest)
    return moved if moved.is_file() and "/".join(rest[:-1]) in archivable_folders() else p


ARCHIVED_FILE_KINDS = ("minutes", "weekly_reports", "client_reports", "steerco")    # BL-03: what moves into an engagement's _Archive


def archivable_folders() -> list:
    """BL-03: the folders, relative to an engagement (or project) folder, whose dated files move into its own _Archive after
    archive.reports_after_months: minutes, weekly and client reports and Steerco one-pagers (never transcripts, agendas or
    documents)."""
    return sorted({folder_name(k).strip("/") for k in ARCHIVED_FILE_KINDS})


def old_archive_folders() -> list:
    """Folders still called zz Archive (BL-09): in the projects root itself and in each engagement or project folder (never in
    _Templates, _Portfolio or another _ folder, which creaite doesn't write in). A folder listing only; nothing inside is read."""
    root = projects_root()
    if not root.is_dir():
        return []
    out = [root / OLD_ARCHIVE] if (root / OLD_ARCHIVE).is_dir() else []
    for d in sorted(x for x in root.iterdir() if x.is_dir() and not x.name.startswith((".", "_")) and x.name not in skipped_names()):
        if (d / OLD_ARCHIVE).is_dir() and not (d / OLD_ARCHIVE).is_symlink():
            out.append(d / OLD_ARCHIVE)
    return out


def skeleton_old_archive() -> list:
    """The folders called zz Archive in the project skeleton (locations.skeleton, BL-09), relative to it: a listing of folder names
    only, as setup already reads the skeleton. creaite never writes in _Templates: Alan renames them in Finder."""
    sk = projects_root() / str(locations().get("skeleton") or "_Templates/_Skeleton")
    if not external() or not sk.is_dir():
        return []
    return sorted(d.relative_to(sk).as_posix() for d in sk.rglob("*") if d.is_dir() and d.name == OLD_ARCHIVE)
# ===== end BL-09 =====


rel_project, resolve_project = rel, resolve         # the names the brief uses


def allowed_roots() -> list:
    """Where creaite may read and write project files: the vault and, if set, the projects root."""
    return [ROOT.resolve()] + ([projects_root().resolve()] if external() else [])


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


def project_folders() -> list:
    """[(code, folder)] for every project, the portfolio folder last as '_portfolio'. With an outside projects root only registered
    projects (the folder holds other things); in the default layout, every folder under projects/."""
    out = []
    if external():
        for code, name in sorted(register_folders().items()):
            if (projects_root() / name).is_dir():
                out.append((code, projects_root() / name))
    else:
        for d in sorted(x for x in projects_root().iterdir() if x.is_dir()):
            if d != portfolio_dir() and d.name not in skipped_names():          # BL-09: never _Archive (archived projects)
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
    projects root the `images` folder is the mapped one (locations.folders.images), so references never contain spaces."""
    ref = str(ref)
    if external() and ref.startswith("images/"):
        return Path(project_folder) / folder_name("images") / ref[len("images/"):]
    return Path(project_folder) / ref


def extract_dirs(code: str) -> list:
    """The only folders ever extracted from: minutes and transcripts."""
    return [folder(code, "minutes"), folder(code, "transcripts")]


def never_index() -> list:
    """The folder names creaite never lists, indexes, reads or writes: the saved `never_index` plus the reserved ones, so a list saved
    by an older release (or emptied by hand) never exposes 99 System, where the backup copies are (BL-112)."""
    saved = [str(n) for n in locations().get("never_index") or []]
    return saved + [n for n in ALWAYS_NEVER_INDEX if n not in saved]


def skipped_names() -> list:
    """never_index plus the old archive name, zz Archive (BL-09): still never listed, indexed, read or written for one release,
    and never for reach.classify, but left out of ask creaite's deny lists and permission patterns (Alan, 14-10-2026: _Archive only)."""
    names = never_index()
    return names + ([OLD_ARCHIVE] if OLD_ARCHIVE not in names else [])


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
                             and n not in skipped_names())
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


# #128: where an engagement's notes can be, below the projects folder: <eng>/<notes>, and (archived) <eng>/_Archive/<notes>,
# _Archive/<eng>/<notes>, _Archive/<eng>/_Archive/<notes> ("*" an engagement, "A" _Archive or zz Archive). tracker's copy guard
# matches these shapes (notes_shape) and the rename check lists them (notes_places): one list, so the two never disagree.
NOTES_SHAPES = (("*",), ("*", "A"), ("A", "*"), ("A", "*", "A"))
NOT_A_NOTE = (".DS_Store", "Icon\r")             # Finder's own files (and ._* AppleDouble) are never notes


def _fold(x) -> str:
    import unicodedata
    return unicodedata.normalize("NFC", str(x)).casefold()


def _arch_names() -> set:
    return {_fold(ARCHIVE), _fold(OLD_ARCHIVE)}


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
    registered or not, the portfolio, their _Archive and archived engagements), so those notes would lose the apply's guard.
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
        bases += [pf / a, pf / ARCHIVE / a, ROOT / "projects" / "_portfolio" / a]
        for d in dict.fromkeys(bases):
            if os.path.lexists(d) and _holds_files(d):
                return f"Not saved: notes are still in “{a}” ({d.parent.name}): {why}, then change the setting."
    return None


def _engagement_top(top, new) -> bool:
    """#128 L1, D2: folder `top` (below the projects folder) is _Archive, the portfolio, a registered engagement, or any
    folder but _Templates that holds a notes folder (an engagement not in the register)."""
    engagements = {_fold(x) for x in register_folders().values()} | {_fold(new.get("portfolio") or "_Portfolio")}
    if _fold(top) in _arch_names() | engagements:
        return True
    d, name = _loc_root(new) / top, _loc_notes(new)
    return _fold(top) != "_templates" and any((d / x / name).is_dir() for x in ("", ARCHIVE, OLD_ARCHIVE))


def skeleton_problem(old, new):
    """#128 L1: why `new`'s locations.skeleton can't be saved (a changed one that is empty, ".", has "..", is in _Archive, or is
    an engagement's or the portfolio's folder: its notes would lose the by-name guard), or None."""
    if "skeleton" not in (new or {}) or (new or {}).get("skeleton") == (old or {}).get("skeleton"):
        return None                               # left as it was (or the default)
    s = str(new.get("skeleton") or "")
    parts = [x for x in s.replace("\\", "/").split("/") if x not in ("", ".")]
    if not parts or ".." in parts or _engagement_top(parts[0], new):
        return f"Not saved: locations.skeleton “{s}” isn't a template folder of its own (never “.”, _Archive, an engagement or the portfolio)."
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
    return skeleton_problem(old, new) or notes_rename_problem(old, new)


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
# Reading: every document of a project (never an online-only file, never _Archive or _Templates). Writing: creaite may create files
# in any folder of a project when producing something Alan asked for and approved, and change an existing one only when Alan asks, shown
# and confirmed, a copy kept first (filechange.py). Everything is inside a project folder or the vault: never outside, never _Templates
# or _Archive, never a hidden file.

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
    skipped = set(skipped_names())
    if any(part in skipped for part in parts):
        return f"{next(p for p in parts if p in skipped)} is never read or written by creaite"
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
    portfolio = str(locations().get("portfolio") or "_Portfolio")
    if sub == "_portfolio" or sub.startswith("_portfolio/"):
        sub = portfolio + sub[len("_portfolio"):]
    root = str(locations().get("projects_root")).strip().rstrip("/")
    if root.startswith("~"):
        return f"{root}/{sub}"
    if Path(root).is_absolute():
        return f"/{root}/{sub}"                      # Claude Code writes an absolute path as //abs/path
    return f"{root}/{sub}"


def never_index_patterns():
    """Permission patterns (below the projects root) for the folders creaite never reads or writes: _Archive, _Templates, 99 System."""
    return [f"**/{n}/**" for n in never_index() if n != OLD_ARCHIVE]      # BL-09: _Archive only (Alan, 14-10-2026)
