"""Intake's Process (#264): the plain-code half of Process as its own run kind.

Pressing Process in Intake is Alan's go-ahead to stage proposals for Review, and nothing more. The live server (a guarded file:
dev/proposals/intake-process/) owns the route, POST /api/intake/process, and starts the run kind "process" under the guard hook's
mode "process". This module is what the route and the page share, all plain code:

    validate_request(req)        -> (files, None) or (None, "why"): the request checked, every path an Intake file
    validate_paths(paths)        -> (paths, None) or (None, "why")
    build_prompt(files)          -> the run's message, fixed wording, the files one per line
    label(files)                 -> the run's plain ask (BL-326), never a path
    closer(files)                -> the run's closer: per file staged, needs you (with the run's question) or not staged
    outcome(files, started, said)-> the same, without a run (tests and the page's contract)

The request (a small, stable contract; #232's Intake page calls the same route):
    {"files": [{"path": "inbox/<name>", "project": "ABC"?}, ...], "run": "<id>"?}
    (a plain list of path strings is accepted too). At most MAX_FILES, each directly in inbox/, a regular file (no link, no
    second hard link, not hidden), one of TYPES, 1 byte to 25 MB, with a name of ordinary characters, not already waiting in
    Review. A project is a code in the tracker's projects table, or left out.
The stream: the run engine's events (step, closure, done...), plus one "intake" event before the closure:
    {"type": "intake", "files": [{"path", "state": "staged" | "needs" | "not_staged", "question"?}], "staged": n, "needs": n}

Never the text of a transcript: a question is the run's own short sentence about one of its files, one line, at most 300
characters, and only for a file the run was given.
"""
import json
import os
import re
import sqlite3
import stat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

KIND = "process"                 # the run engine's kind, the usage monitor's kind and the guard hook's mode
MODE = "process"
MAX_FILES = 20
TYPES = (".vtt", ".docx", ".txt", ".md", ".pdf")          # what Intake takes (live_server.INBOX_TYPES)
MAX_BYTES = 25 * 1024 * 1024
NAME_OK = re.compile(r"[\w .,()&'+-]{1,160}")             # the upload's own characters (live_server.inbox_upload), and no more
CODE_OK = re.compile(r"[A-Z][A-Z0-9]{2,6}")
QUESTION = re.compile(r"^QUESTION:\s*`?(inbox/[^`|\n]{1,200}?)`?\s*\|\s*(.+?)\s*$", re.M)
QUESTION_MAX = 300


def _why(path, reason):
    return f"{path}: {reason}"


def _waiting():
    """The Intake paths that already have a proposal waiting in Review (meeting.transcript, not applied)."""
    out = set()
    for p in sorted(paths.STAGING.glob("proposed-*.json")):
        try:
            m = json.loads(p.read_text(encoding="utf-8")).get("meeting") or {}
        except (OSError, ValueError):     # an unreadable proposal is Review's to show; it names no file here
            continue
        if isinstance(m, dict) and m.get("transcript") and not m.get("applied"):
            out.add(str(m["transcript"]))
    return out


def _name_problem(rel):
    """Why the path, as written, isn't an Intake file's (no file system access), or None."""
    if not isinstance(rel, str) or not rel:
        return "not a file path"
    if any(ord(c) < 32 or ord(c) == 127 for c in rel) or "\\" in rel:
        return _why(rel, "the path has characters a file in Intake never has")
    if not rel.startswith("inbox/"):
        return _why(rel, "only files in Intake (inbox/) can be processed here")
    name = rel[len("inbox/"):]
    if "/" in name or name in ("", ".", "..") or ".." in name.split("/"):
        return _why(rel, "only a file directly in Intake (inbox/) can be processed here")
    if name.startswith("."):
        return _why(rel, "a hidden file isn't an Intake file")
    if not NAME_OK.fullmatch(name):
        return _why(rel, "the file's name has characters Intake doesn't use: rename it, then add it again")
    if Path(name).suffix.lower() not in TYPES:
        return _why(rel, f"only {', '.join(TYPES)} files are processed")
    return None


def _file_problem(rel, name):
    """Why the file itself isn't a plain Intake file (lstat: a link is never followed), or None."""
    inbox = paths.INBOX
    try:
        if inbox.is_symlink() or not inbox.is_dir():
            return _why(rel, "Intake (inbox/) isn't a plain folder")
        st = os.lstat(inbox / name)
    except OSError:
        return _why(rel, "it isn't in Intake any more")
    if stat.S_ISLNK(st.st_mode):
        return _why(rel, "a link isn't an Intake file")
    if not stat.S_ISREG(st.st_mode):
        return _why(rel, "it isn't a plain file")
    if st.st_nlink > 1:
        return _why(rel, "it is linked from somewhere else, so it isn't only an Intake file")
    if not 0 < st.st_size <= MAX_BYTES:
        return _why(rel, "it is empty or over 25 MB")
    if os.path.realpath(inbox / name) != os.path.join(os.path.realpath(inbox), name):
        return _why(rel, "it isn't directly in Intake")
    return None


def check_path(rel):
    """None if `rel` is an Intake file Process may be given, else why not. Read only; never follows a link."""
    return _name_problem(rel) or _file_problem(rel, rel[len("inbox/"):])


def validate_paths(given):
    """(the paths, None) when every one is an Intake file Process may be given, else (None, why). One to MAX_FILES, no repeats,
    none already waiting in Review."""
    if not isinstance(given, list) or not given:
        return None, "Tick a file first."
    if len(given) > MAX_FILES:
        return None, f"Process takes at most {MAX_FILES} files at a time."
    if not all(isinstance(g, str) for g in given) or len(set(given)) != len(given):
        return None, "Each file once, as a path in Intake."
    for g in given:
        why = check_path(g)
        if why:
            return None, why
    waiting = _waiting()
    for g in given:
        if g in waiting:
            return None, _why(g, "its draft is already waiting in Review")
    return list(given), None


def project_codes():
    """The tracker's project codes, read only (an unreadable tracker gives none: a project is then refused, never guessed)."""
    try:
        con = sqlite3.connect(f"file:{paths.DB}?mode=ro", uri=True)
        try:
            return {r[0] for r in con.execute("SELECT code FROM projects")}
        finally:
            con.close()
    except sqlite3.Error:
        return set()


def _project_problem(f, codes):
    """(why the file's project is refused, or None; the codes, read once)."""
    project = f.get("project")
    if project in (None, ""):
        return None, codes
    if not isinstance(project, str) or not CODE_OK.fullmatch(project):
        return _why(f.get("path"), "that project code isn't valid"), codes
    codes = project_codes() if codes is None else codes
    return (None if project in codes else _why(f.get("path"), f"there is no project {project}")), codes


def validate_request(req, codes=None):
    """(files, None) or (None, why) for a POST /api/intake/process body: files is [{path, project}] (project may be None)."""
    if not isinstance(req, dict):
        return None, "Bad request."
    raw = req.get("files")
    if not isinstance(raw, list):
        return None, "Tick a file first."
    if len(raw) > MAX_FILES:
        return None, f"Process takes at most {MAX_FILES} files at a time."
    files = []
    for f in raw:
        f = {"path": f} if isinstance(f, str) else f
        if not isinstance(f, dict) or set(f) - {"path", "project"}:
            return None, "Each file is {path, project}."
        why, codes = _project_problem(f, codes)
        if why:
            return None, why
        files.append({"path": f.get("path"), "project": f.get("project") or None})
    ok, why = validate_paths([f["path"] for f in files])
    if why:
        return None, why
    return files, None


def build_prompt(files):
    """The run's message: a fixed wording with the files one per line (each a validated Intake path)."""
    lines = [f"- `{f['path']}`" + (f" (project {f['project']}, as set in Intake)" if f.get("project") else "") for f in files]
    return ("Process these Intake files with the cx-minutes skill, one after another, exactly as the skill says for "
            "\"process <file>\":\n" + "\n".join(lines) + "\n"
            "Read each file (and a transcript's \" - chat.txt\" beside it, if there is one), draft the minutes and stage the "
            "meeting with `system/scripts/run minutes.py stage <spec in system/staging/drafts/>`, the spec's \"transcript\" "
            "being that file's path exactly as listed. Stage nothing else and touch no other file. If you can't finish a file "
            "without Alan (its project isn't clear, it isn't a meeting, it was processed before), stage nothing for it and end "
            "your reply with one line for that file: QUESTION: <its path as listed> | <one short question for Alan>. "
            "Never quote the file's text.")


def label(files):
    """The plain ask the run shows (BL-326): never a path or a file's name."""
    n = len(files)
    return "Process 1 Intake file" if n == 1 else f"Process {n} Intake files"


def questions(said, given):
    """{path: question} from the run's reply lines `QUESTION: <path> | <text>`, only for a file the run was given; one line, at
    most QUESTION_MAX characters, control characters out."""
    out = {}
    for m in QUESTION.finditer("\n".join(str(s) for s in (said or []))):
        path, text = m.group(1).strip(), " ".join(m.group(2).split())
        text = "".join(c for c in text if ord(c) >= 32 and ord(c) != 127)[:QUESTION_MAX].strip()
        if path in given and text and path not in out:
            out[path] = text
    return out


def staged_paths(started):
    """The Intake paths with a proposal staged since `started` (seconds), not applied: what the run put in Review."""
    out = set()
    for p in sorted(paths.STAGING.glob("proposed-*.json")):
        try:
            if p.stat().st_mtime < started - 1:
                continue
            m = json.loads(p.read_text(encoding="utf-8")).get("meeting") or {}
        except (OSError, ValueError):     # a proposal that can't be read isn't counted as staged: the row says so
            continue
        if isinstance(m, dict) and m.get("transcript") and not m.get("applied"):
            out.add(str(m["transcript"]))
    return out


def outcome(files, started, said):
    """Per file: "staged" (in Review now), "needs" (the run asked Alan something about it) or "not_staged"; and the counts."""
    given = [f["path"] for f in files]
    done, asked = staged_paths(started), questions(said, set(given))
    rows = []
    for p in given:
        if p in done:
            rows.append({"path": p, "state": "staged"})
        elif p in asked:
            rows.append({"path": p, "state": "needs", "question": asked[p]})
        else:
            rows.append({"path": p, "state": "not_staged"})
    staged = sum(r["state"] == "staged" for r in rows)
    needs = sum(r["state"] == "needs" for r in rows)
    return {"files": rows, "staged": staged, "needs": needs}


def closure_line(res):
    """The run's one closure line, from its outcome."""
    n, s, q = len(res["files"]), res["staged"], res["needs"]
    if s == n:
        return f"{'The file is' if n == 1 else f'All {n} files are'} staged: the drafts are waiting in Review."
    parts = [f"{s} of {n} staged for Review"]
    if q:
        parts.append(f"{q} need{'s' if q == 1 else ''} you (see Intake)")
    if n - s - q:
        parts.append(f"{n - s - q} not staged")
    return "; ".join(parts) + "."


def closer(files):
    """The run's closer (live_server.Run(closer=…)): emits the "intake" event, returns the closure."""
    def close(run):
        """Emit the run's outcome as the "intake" event and return its closure line."""
        res = outcome(files, run.started, getattr(run, "said", []))
        run.emit("intake", **res)
        return {"ok": res["staged"] > 0 or res["needs"] > 0, "line": closure_line(res), "href": "#review", "link": "Review"}
    return close
