"""#269: what `minutes.py stage` accepts as a meeting spec, checked by plain code before anything is read. Standard library only.
A library: no command line. `minutes.py stage` calls it itself, so the check holds in every mode (a plain ask creaite chat, a
confirmed run, Intake's Process, Alan's own Terminal); the guard hook can call the same function before the command runs.

The spec is a `.json` directly in system/staging/drafts/, a JSON object. Every key stage reads that names, or makes, a path:
  "transcript"  a stored path (`inbox/<file>` directly, or a file in a project's or the portfolio's minutes or transcripts folder),
                a plain file (no link, no second hard link, not hidden), of a meeting file's type; a quick note goes as "note"
  "note"        a quick note (BL-54): a `.md` directly in a project's or the portfolio's minutes folder (never a BL-301 note)
  "draft"       a Word draft: a `.docx` directly in system/staging/drafts/, a plain file, not the draft of another meeting
                waiting in Review (a report's or another meeting's proposal)
  "date"        YYYY-MM-DD, a real date (it starts every file name stage makes)
  "projects"    a list of project codes (it picks the folders the files are filed in)
Each path is a string, relative to the vault (stored form), with no `..`, backslash, `~` or control character. Anything else
refused, in plain words. Nothing here writes."""
import json
import re
from datetime import date
from pathlib import Path

import paths

MEETING_TYPES = (".vtt", ".docx", ".txt", ".md", ".pdf")       # what Intake accepts (live_server.INBOX_TYPES)
CODE = re.compile(r"[A-Z][A-Z0-9]{2,6}")
BAD_CHARS = re.compile(r"[\\\x00-\x1f\x7f]")


def _real(p):
    """The real path of `p` (links followed), or None when it can't be worked out."""
    try:
        return Path(p).resolve()
    except (OSError, RuntimeError, ValueError):
        return None


def _within(real, folder):
    """True when `real` is `folder` itself or below it (both real paths)."""
    folder = _real(folder)
    return folder is not None and (real == folder or folder in real.parents)


def stored_problem(key, value):
    """Why `value` isn't a usable stored path for spec key `key`, or None."""
    if not isinstance(value, str):
        return f"\"{key}\" must be one path, as text (not a {type(value).__name__})"
    s = value.strip()
    if not s or s != value:
        return f"\"{key}\" must be a path with no spaces around it"
    if BAD_CHARS.search(s) or s.startswith(("/", "~")) or re.match(r"[A-Za-z]:", s):
        return f"\"{key}\" must be a path inside the vault, as stored (like inbox/<file>), never a full or home path"
    if ".." in s.split("/") or "." in s.split("/") or "" in s.split("/"):
        return f"\"{key}\" can't step out of its folder (no \"..\" or empty parts)"
    return None


def _plain_file_problem(key, given, real, must_exist=True):
    """Why the file at `given` (its real path `real`) isn't a plain file of its own, or None."""
    try:
        if Path(given).is_symlink():
            return f"\"{key}\" is a link; give the file itself"
        if not real.exists():
            return f"\"{key}\" not found: {paths.rel(real) if _within(real, paths.ROOT) else Path(given).name}" if must_exist else None
        st = real.stat()
        if not real.is_file():
            return f"\"{key}\" isn't a file"
        if st.st_nlink > 1:
            return f"\"{key}\" is linked from elsewhere (a second hard link); give a copy of its own"
    except OSError as e:
        return f"\"{key}\" can't be checked ({type(e).__name__})"
    if real.name.startswith((".", "~$")):
        return f"\"{key}\" is a hidden or temporary file"
    return None


def _meeting_folders(kinds):
    """The real folders of these kinds (minutes, transcripts) for every project and the portfolio (never _Archive)."""
    out = []
    for code, _ in paths.project_folders():
        for kind in kinds:
            try:
                f = _real(paths.folder(code, kind))
            except (LookupError, OSError):
                continue                                     # a project with no folder yet: nothing in it to stage
            if f is not None:
                out.append(f)
    return out


def _skipped(real, folder):
    """True when a part of `real` below `folder` is one creaite never reads (_Archive, _Templates, 99 System...)."""
    never = {n.lower() for n in paths.skipped_names()} | {n.lower() for n in paths.never_index()}
    return any(part.lower() in never or part.startswith(".") for part in real.relative_to(folder).parts[:-1])


def transcript_problem(value):
    """Why the spec's "transcript" can't be staged, or None: an Intake file, or one in a project's minutes or transcripts folder."""
    why = stored_problem("transcript", value)
    if why:
        return why
    given = paths.resolve(value, archived=False)
    real = _real(given)
    if real is None:
        return "\"transcript\" can't be checked"
    in_inbox = real.parent == _real(paths.INBOX)
    folder = next((f for f in _meeting_folders(paths.EXTRACT_FROM) if f in real.parents), None)
    if not in_inbox and (folder is None or _skipped(real, folder)):
        return ("\"transcript\" must be a file in inbox/ or in a project's minutes or transcripts folder; "
                "creaite doesn't stage a meeting from anywhere else")
    if real.suffix.lower() not in MEETING_TYPES:
        return f"\"transcript\" must be a meeting file ({', '.join(MEETING_TYPES)})"
    if not in_inbox and real.suffix.lower() == ".md" and re.match(r"(\d{4}-\d\d-\d\d )?Quick note - ", real.name):
        return "a quick note is staged as \"note\", not as a transcript"
    return _plain_file_problem("transcript", given, real)


def note_problem(value):
    """Why the spec's "note" (a quick note, BL-54) can't be staged, or None: a .md directly in a minutes folder."""
    why = stored_problem("note", value)
    if why:
        return why
    given = paths.resolve(value, archived=False)
    real = _real(given)
    if real is None or real.suffix.lower() != ".md" or real.parent not in _meeting_folders(("minutes",)):
        return ("\"note\" must be a quick note: a .md file directly in a project's minutes folder (a note in a notes folder "
                "goes through Find updates, not minutes)")
    return _plain_file_problem("note", given, real, must_exist=False)          # not found: stage says so in its own words


def _pending_refs(rel_path):
    """The pending proposals (system/staging/proposed-*.json) that name `rel_path` anywhere."""
    out = []
    for p in sorted(paths.STAGING.glob("proposed-*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue                                         # unreadable: tracker.py validate reports it, not this check
        if _names(data, rel_path):
            out.append((p.name, data))
    return out


def _names(node, s):
    """True when the JSON value `node` holds the string `s` anywhere."""
    if isinstance(node, str):
        return node == s
    if isinstance(node, dict):
        return any(_names(v, s) for v in node.values())
    if isinstance(node, list):
        return any(_names(v, s) for v in node)
    return False


def _same_meeting(data, spec):
    """True when a pending proposal is this same meeting (same date and title): staging it again after fixing the spec."""
    m = (data or {}).get("meeting") or {}
    return bool(m) and m.get("date") == spec.get("date") and m.get("title") == spec.get("title")


def draft_problem(value, spec):
    """Why the spec's Word "draft" can't be staged, or None: a .docx directly in system/staging/drafts/, not another meeting's."""
    why = stored_problem("draft", value)
    if why:
        return why
    given = paths.resolve(value, archived=False)
    real = _real(given)
    if real is None or real.suffix.lower() != ".docx" or real.parent != _real(paths.DRAFTS):
        return ("\"draft\" must be the Word minutes drafted for this meeting: a .docx directly in system/staging/drafts/ "
                "(it is filed on approval); a Word file from anywhere else is never filed as minutes")
    why = _plain_file_problem("draft", given, real, must_exist=False)      # not found: stage says what to run first
    if why or not real.exists():
        return why
    other = [n for n, d in _pending_refs(paths.rel(real)) if not _same_meeting(d, spec)]
    if other:
        return f"\"draft\" is already waiting in Review with {other[0]}: it belongs to that proposal, not to this meeting"
    return None


def fields_problem(spec):
    """Why the spec's date or projects can't make file names and folders, or None."""
    try:
        if not isinstance(spec.get("date"), str) or date.fromisoformat(spec["date"]).isoformat() != spec["date"]:
            raise ValueError
    except ValueError:
        return "\"date\" must be the meeting's date as YYYY-MM-DD"
    if not isinstance(spec.get("title"), str):
        return "\"title\" must be the meeting's title, as text"
    projects = spec.get("projects", [])
    if not isinstance(projects, list) or any(not isinstance(c, str) or not (c == "_portfolio" or CODE.fullmatch(c))
                                             for c in projects):
        return "\"projects\" must be a list of project codes (like ABC)"
    return None


def spec_file_problem(spec_path, root=None):
    """Why `spec_path` isn't a meeting spec stage may read, or None: a .json directly in system/staging/drafts/, a plain file."""
    if not isinstance(spec_path, str) or not spec_path or BAD_CHARS.search(spec_path):
        return "give one meeting spec: a .json file in system/staging/drafts/"
    given = Path(spec_path)
    if not given.is_absolute():
        given = Path(root or Path.cwd()) / given
    real = _real(given)
    if real is None or real.suffix.lower() != ".json" or real.parent != _real(paths.DRAFTS):
        return "the meeting spec must be a .json file directly in system/staging/drafts/"
    return _plain_file_problem("spec", given, real)


def validate_spec(spec_path, root=None):
    """#269: None when `minutes.py stage <spec_path>` may go on, else a plain refusal (one sentence, no file text). `root` is the
    folder a relative `spec_path` is read from (the command's working folder; the guard hook passes the vault)."""
    why = spec_file_problem(spec_path, root)
    if why:
        return why
    given = Path(spec_path) if Path(spec_path).is_absolute() else Path(root or Path.cwd()) / spec_path
    try:
        spec = json.loads(given.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "the meeting spec can't be read as JSON"
    return spec_problem(spec)


def spec_problem(spec):
    """Why this spec (already read) can't be staged, or None: its fields, then every path it names."""
    if not isinstance(spec, dict):
        return "the meeting spec must be a JSON object"
    why = fields_problem(spec)
    if why:
        return why
    for key, check in (("transcript", transcript_problem), ("note", note_problem)):
        if spec.get(key) not in (None, ""):
            why = check(spec[key])
            if why:
                return why
    if spec.get("draft") not in (None, ""):
        return draft_problem(spec["draft"], spec)
    return None
