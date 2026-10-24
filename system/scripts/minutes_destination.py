"""Where minutes are filed, and what to call them (#324, #326, #332). A library: no command line; live_server.py registers `routes`.

  POST /api/minutes/destination        {file}: where the minutes will be filed, per project: the project, the folder as a person reads
                                       it, the file name, whether it is taken (then the numbered name that will be used) and the
                                       transcript copy beside it. Read only.
  POST /api/minutes/destination/name   {file, code, name}: the minutes (and their transcript copy) filed under another name in that
                                       project. One name: no folder, the staged extension, the meeting's date first. Rewrites the
                                       one pending proposal (the copy, the source map and every item's source) and nothing else.
  POST /api/minutes/destination/where  {key | path}: where approved minutes sit now, in words (here, moved, or online-only).
  POST /api/minutes/destination/open   {key | path, what: file | folder}: open the minutes, or show them in Finder. Only a file
                                       found in a project's own minutes folder; the page never sends a place to open.

Approve settles a taken name by itself (`settle`, called by the minutes approve route): a second meeting with the same title and day
is filed as "Title (2)". tracker.py's rule stands: a file is never overwritten. Nothing here writes a project file; the copy is
still made by `tracker.py apply`, the one writer. No message holds a path or a proposal's name."""
import hashlib
import json
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

TITLE_MAX, NAME_MAX = 80, 150
DAY = re.compile(r"\d{4}-\d{2}-\d{2}")
RESERVED = re.compile(r"(?i)^(?:con|prn|aux|nul|com[0-9¹²³]|lpt[0-9¹²³]|conin\$|conout\$)(?:\..*)?$")
INVISIBLE = re.compile("[­᠎​-‏‪-‮⁠-⁤﻿]")
PROPOSAL = re.compile(r"proposed-[\w.-]+\.json")
MINUTES_EXTS = (".html", ".docx")


class DestinationError(ValueError):
    """A refusal in plain words (nothing was changed)."""


# ── Reading a proposal ───────────────────────────────────────────────────────

def _proposal(file):
    """(path, data) of one pending proposal that holds minutes to file. Raises DestinationError."""
    p = paths.STAGING / Path(str(file or "")).name
    if not PROPOSAL.fullmatch(p.name) or not p.is_file():
        raise DestinationError("Those minutes aren't pending any more.")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise DestinationError("Those minutes can't be read.") from None
    meeting = data.get("meeting") or {}
    if not meeting or meeting.get("applied") or meeting.get("note"):
        raise DestinationError("Those minutes have already been approved, or there are no minutes to file.")
    return p, data


def _copies(meeting, source):
    """The copy operations of one kind (`source`: "draft" or "transcript"), as file_ops indexes."""
    return [i for i, op in enumerate(meeting.get("file_ops") or []) if op.get("op") == "copy" and op.get("from") == source and op.get("to")]


def _code_of(to):
    """The project (or "_portfolio") whose minutes or transcripts folder holds this stored path, or None."""
    folder = str(to).rsplit("/", 1)[0]
    for code in [*paths.register_folders(), "_portfolio"]:
        try:
            if folder in (paths.rel(paths.folder(code, "minutes")), paths.rel(paths.folder(code, "transcripts"))):
                return code
        except (KeyError, OSError, ValueError):
            continue    # a project whose folder can't be worked out can't be this one
    return None


def _label(code):
    """A project as a person reads it (its name; never the code, BL-101)."""
    import tracker
    return "Portfolio" if code == "_portfolio" else tracker.project_label(code)


def folder_label(code, kind="minutes"):
    """'Example Programme › Minutes': the project and the folder's own name."""
    return f"{_label(code)} › {paths.folder_name(kind)}"


def _fold(rel):
    """A stored path as macOS compares names (case and normalisation ignored)."""
    return unicodedata.normalize("NFC", str(rel)).casefold()


def _others(skip):
    """The destinations the pending proposals staged BEFORE this one will file at, folded: of two meetings with one name the
    earlier keeps it and the later is numbered, whichever is approved first, so a preview never says (2) for both."""
    out = set()
    for f in sorted(paths.STAGING.glob("proposed-*.json")):
        if f.name >= skip:
            continue
        try:
            m = json.loads(f.read_text(encoding="utf-8")).get("meeting") or {}
        except (OSError, ValueError):
            continue    # a proposal that can't be read has no destinations to keep clear of
        out.update(_fold(op["to"]) for op in m.get("file_ops") or [] if op.get("op") == "copy" and op.get("to"))
    return out


def _sha(real):
    """sha256 of a regular file, or None (a folder, a link, a missing file)."""
    try:
        if real.is_symlink() or not real.is_file():
            return None
        return hashlib.sha256(real.read_bytes()).hexdigest()
    except OSError:
        return None


def _taken(to, source_rel, others):
    """Whether a stored path is in the way: something there that is not the very file being filed (tracker.py files nothing then),
    or another pending proposal's destination. An online-only placeholder counts as there."""
    real = paths.resolve(to)
    if _fold(to) in others:
        return True
    if not (real.exists() or real.is_symlink()):
        return False
    mine, there = _sha(paths.resolve(source_rel)) if source_rel else None, _sha(real)
    return not (mine and there == mine)


def _numbered(to, source_rel, others):
    """The next free 'Name (2).ext' beside `to`."""
    head, _, name = to.rpartition("/")
    stem, ext = os.path.splitext(name)
    n, final = 2, to
    while _taken(final, source_rel, others) and n < 100:
        final, n = f"{head}/{stem} ({n}){ext}", n + 1
    return final


# ── The read ─────────────────────────────────────────────────────────────────

def view(file):
    """{ok, items: [{code, project, folder_label, name, ext, taken, numbered, will_be, transcript, local}]}: where each project's
    copy of the minutes will be filed, and under what name. `will_be` is the name used (the numbered one when taken)."""
    try:
        p, data = _proposal(file)
    except DestinationError as e:
        return {"ok": False, "message": str(e)}
    meeting, others = data["meeting"], _others(p.name)
    items = []
    for i in _copies(meeting, "draft"):
        to = meeting["file_ops"][i]["to"]
        code = _code_of(to)
        if not code:
            continue
        taken = _taken(to, meeting.get("draft"), others)
        on_disk = taken and (paths.resolve(to).exists() or paths.resolve(to).is_symlink())     # a FILED copy, not another pending one
        final = _numbered(to, meeting.get("draft"), others) if taken else to
        tr = _transcript_of(meeting, code, others)
        items.append({"code": code, "project": _label(code), "folder_label": folder_label(code), "name": Path(to).name,
                      "ext": Path(to).suffix.lower(), "taken": taken, "filed_copy": bool(on_disk),
                      "numbered": Path(final).name if taken else None,
                      "will_be": Path(final).name, "transcript": tr,
                      "local": not paths.is_online_only(paths.resolve(to)) if paths.resolve(to).exists() else True})
    return {"ok": True, "items": items, "multiple": len(items) > 1, "key": meeting.get("key") or None}


def _transcript_of(meeting, code, others):
    """The transcript copy in `code`'s transcripts folder: {name, will_be, folder_label}, or None (none is made)."""
    for i in _copies(meeting, "transcript"):
        to = meeting["file_ops"][i]["to"]
        if _code_of(to) == code:
            taken = _taken(to, meeting.get("transcript"), others)
            final = _numbered(to, meeting.get("transcript"), others) if taken else to
            return {"name": Path(to).name, "will_be": Path(final).name, "folder_label": folder_label(code, "transcripts")}
    return None


# ── Names ────────────────────────────────────────────────────────────────────

def _chars_problem(name):
    """Why a name holds a character that can't be in a file name, or None."""
    if any(ord(c) < 32 or ord(c) == 127 for c in name) or INVISIBLE.search(name):
        return "That name has a character a file name can't hold."
    if "/" in name or "\\" in name or ".." in name or name.startswith("."):
        return "A file name can't hold a folder, and can't start with a dot."
    if re.search(r'[<>:"|?*]', name) or RESERVED.match(name) or name != name.rstrip(". "):
        return 'A file name can\'t hold < > : " | ? * , end in a dot or a space, or be a name Windows reserves.'
    return None


def clean_name(typed, ext, day):
    """(file name, None) for a typed name, or (None, why in plain words). One name ending in the staged extension, starting with the
    meeting's date, a title of at most 80 characters, nothing a file name can't hold on Windows or macOS."""
    name = " ".join(unicodedata.normalize("NFC", str(typed or "")).split())
    if name.lower().endswith(ext):
        name = name[: -len(ext)].rstrip()
    why = "Type a file name." if not name else _chars_problem(str(typed or "")) or _chars_problem(name)
    if why:
        return None, why
    if not name.startswith(day + " ") or not name[len(day) + 1:].strip():
        return None, "Keep the meeting's date at the start (YYYY-MM-DD, then a space and a title), so the minutes sort in order."
    if len(name[len(day) + 1:]) > TITLE_MAX or len(name) + len(ext) > NAME_MAX:
        return None, f"That name is too long: keep the title to {TITLE_MAX} characters."
    return name + ext, None


def _rewrite(data, old, new):
    """Every place a pending proposal names the filed path `old`, now `new`: the copy, the source map (key and value) and each
    item's source (which starts with the path)."""
    meeting = data["meeting"]
    for op in meeting.get("file_ops") or []:
        if op.get("op") == "copy" and op.get("to") == old:
            op["to"] = new
    if meeting.get("source_map"):
        meeting["source_map"] = {(new if k == old else k): (new if v == old else v) for k, v in meeting["source_map"].items()}
    for it in data.get("items") or []:
        for holder in (it.get("values") or {}, it):          # an update item keeps its source at the top (#355 M3), a new one in `values`
            _follow(holder, old, new)


def _follow(holder, old, new):
    """The holder's `source`, when it starts with the filed path `old`, now starts with `new`."""
    src = holder.get("source")
    if isinstance(src, str) and (src == old or src.startswith(old + " ")):
        holder["source"] = new + src[len(old):]


def _save(p, data):
    """Write the proposal back as the review code does (keeps what was first proposed)."""
    import review
    review.save(p, data)


def _transcript_follows(meeting, code, old, fixed, others):
    """(the transcript copy's path now, its path under the new minutes name) when it carried the minutes' stem, else (None, None).
    Raises DestinationError when that transcript name is taken."""
    t_old = next((o["to"] for o in (meeting["file_ops"][i] for i in _copies(meeting, "transcript")) if _code_of(o["to"]) == code), None)
    if not t_old or Path(t_old).stem != Path(old).stem:
        return t_old, None
    t_new = f"{t_old.rsplit('/', 1)[0]}/{Path(fixed).stem}{Path(t_old).suffix}"
    if _taken(t_new, meeting.get("transcript"), others):
        raise DestinationError(f"A transcript called {Path(t_new).name} is already in "
                               f"{folder_label(code, 'transcripts')}. Choose another name.")
    return t_old, t_new


def _rename_in(data, others, code, name):
    """Rename project `code`'s minutes (and the transcript copy that follows) in the loaded proposal `data`; the name used.
    Raises DestinationError, having changed nothing in `data`."""
    meeting = data["meeting"]
    idx = next((i for i in _copies(meeting, "draft") if _code_of(meeting["file_ops"][i]["to"]) == code), None)
    if idx is None:
        raise DestinationError("Those minutes aren't filed in that project.")
    old = meeting["file_ops"][idx]["to"]
    ext = Path(old).suffix.lower()
    if ext not in MINUTES_EXTS:
        raise DestinationError("Those minutes can't be renamed.")
    day = str(meeting.get("date") or "")
    if not DAY.fullmatch(day):
        raise DestinationError("Those minutes have no meeting date to start the name with.")
    fixed, why = clean_name(name, ext, day)
    if why:
        raise DestinationError(why)
    new = f"{old.rsplit('/', 1)[0]}/{fixed}"
    if new == old:
        return fixed
    if _taken(new, meeting.get("draft"), others):
        raise DestinationError(f"{fixed} is already in {folder_label(code)}. Choose another name.")
    t_old, t_new = _transcript_follows(meeting, code, old, fixed, others)
    _rewrite(data, old, new)
    if t_new:
        _rewrite(data, t_old, t_new)
    return fixed


def _fingerprints(data):
    """{item number as text: the item's fingerprint} as the file now stands (#346): a new name changes each item's source, so the
    open Review page needs the new ones to go on deciding those items. Numbers and hex digits only."""
    import build_dashboard
    items = [it for it in data.get("items") or [] if isinstance(it, dict) and isinstance(it.get("n"), int)]
    return {str(it["n"]): build_dashboard.item_fp(it) for it in items}


def set_names(file, names):
    """File the minutes under {code: name}: {ok, names: {code: name}, fps, message}. All or none: every name is checked and applied to
    the loaded proposal, which is written once at the end, so a refusal on any project changes nothing."""
    try:
        p, data = _proposal(file)
        others, used = _others(p.name), {}
        for code, name in (names or {}).items():
            used[code] = _rename_in(data, others, str(code), name)
        _save(p, data)
        fps = _fingerprints(json.loads(p.read_text(encoding="utf-8")))       # as written, whatever the save added
    except DestinationError as e:
        return {"ok": False, "message": str(e)}
    return {"ok": True, "names": used, "fps": fps, "message": ""}


def set_name(file, code, name):
    """File one project's minutes under `name`: {ok, name, message} (set_names for one project)."""
    r = set_names(file, {code: name})
    return {"ok": True, "name": r["names"][code], "message": ""} if r["ok"] else r


def settle(file):
    """Number every taken destination of a pending proposal, so Approve never stops on a name already used (#332): the minutes copy
    and the transcript copy each take the next free 'Name (2)'. Returns [{code, name, was}] for what changed; [] when nothing was
    taken or the proposal can't be read (approve then says why). Call under the server's lock, before approving."""
    try:
        p, data = _proposal(file)
    except DestinationError:
        return []
    meeting, others, moved = data["meeting"], _others(p.name), []
    for source in ("draft", "transcript"):
        for i in _copies(meeting, source):
            to = meeting["file_ops"][i]["to"]
            if _code_of(to) and _taken(to, meeting.get(source), others):
                new = _numbered(to, meeting.get(source), others)
                if new != to:
                    _rewrite(data, to, new)
                    moved.append({"code": _code_of(to), "name": Path(new).name, "was": Path(to).name, "kind": source})
    if moved:
        _save(p, data)
    return moved


# ── Where approved minutes sit (#326) ────────────────────────────────────────

def _sane(rel):
    """Whether a stored path is a plausible one: no NUL or control character, at most 400 characters, each part at most 200 (a longer
    one makes the disk raise ENAMETOOLONG on older Pythons, and the error would carry the real folder)."""
    return len(rel) <= 400 and not any(ord(c) < 32 for c in rel) and all(len(x) <= 200 for x in rel.split("/"))


def _filed_in(key, path):
    """The stored path of filed minutes: from a stored path given, else the last processed.txt line for the meeting key. None if none."""
    rel = str(path or "")
    if _sane(rel) and re.fullmatch(r"projects/.+", rel) and ".." not in Path(rel).parts and rel.lower().endswith(MINUTES_EXTS):
        return rel
    if not key:
        return None
    try:
        lines = paths.PROCESSED.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        cells = [c.strip() for c in line.split(" | ")]
        if len(cells) >= 3 and cells[1] == str(key):
            names = [f.strip() for f in cells[2].split(";") if f.strip()]
            return next((f for f in names if f.lower().endswith(MINUTES_EXTS)), None)
    return None


NOT_FOUND = {"ok": False, "state": "moved", "message": "These minutes aren't in a project's Minutes folder that creaite knows."}


def where(key=None, path=None):
    """{ok, state: here | moved | online, code, project, folder_label, name, message}: approved minutes found in a project's own
    minutes folder, in words. `moved` covers a file or folder that is no longer there. No path is ever in the answer; a path the disk
    refuses is answered as not found."""
    try:
        return _where(_filed_in(key, path))
    except (OSError, ValueError):
        return dict(NOT_FOUND)


def _where(rel):
    """where() for the stored path `_filed_in` gave (read once, so what is checked is what is opened)."""
    code = _code_of(rel) if rel and _sane(rel) else None
    if not rel or not code or paths.rel(paths.folder(code, "minutes")) != rel.rsplit("/", 1)[0]:
        return dict(NOT_FOUND)
    real, name, label = paths.resolve(rel), Path(rel).name, folder_label(code)
    base = {"code": code, "project": _label(code), "folder_label": label, "name": name}
    if real.is_symlink() or not real.is_file():           # a folder named like a file is not the minutes
        if paths.resolve(rel.rsplit("/", 1)[0]).is_dir():
            return {"ok": True, "state": "moved", **base, "folder_only": True,
                    "message": f"{name} isn't in {label} now: it may have been moved or renamed. The folder can still be opened."}
        return {"ok": False, "state": "moved", **base, "message": f"The {label} folder isn't there now: it may have been moved or renamed."}
    if paths.is_online_only(real):
        return {"ok": True, "state": "online", **base,
                "message": f"{name} is online-only in OneDrive, so it isn't on this laptop. Set the Minutes folder to "
                           "Always keep on this device, or download it from OneDrive."}
    return {"ok": True, "state": "here", **base, "message": ""}


def _show(real):
    """Show a file in Finder, or open a folder. Nothing opens under CREAITE_NO_LAUNCH (the tests); True when something was started."""
    if os.environ.get("CREAITE_NO_LAUNCH"):
        return False
    if sys.platform == "darwin":
        subprocess.Popen(["open", "-R", str(real)] if real.is_file() else ["open", str(real)])
    elif os.name == "nt":
        subprocess.Popen(["explorer", "/select,", str(real)] if real.is_file() else ["explorer", str(real)])
    else:
        subprocess.Popen(["xdg-open", str(real.parent if real.is_file() else real)])
    return True


def _open_file(real):
    """Open a file in its default app (nothing under CREAITE_NO_LAUNCH)."""
    if os.environ.get("CREAITE_NO_LAUNCH"):
        return False
    subprocess.Popen(["open", str(real)] if sys.platform == "darwin" else ["xdg-open", str(real)])
    return True


def open_where(key=None, path=None, what="folder"):
    """Open approved minutes (`what` "file") or show them (`what` "folder": the file in Finder, else the folder). The same words as
    `where` when it can't."""
    try:
        rel = _filed_in(key, path)                  # read once: the path checked is the path opened
        w = _where(rel)
        if not w.get("ok"):
            return {**w, "launched": False}
        return _opened(w, rel, what)
    except (OSError, ValueError):
        return {**NOT_FOUND, "launched": False}


def _opened(w, rel, what):
    """open_where's last step, on a path `where` found."""
    real = paths.resolve(rel)
    if what == "file":
        if w["state"] != "here":
            return {**w, "ok": False, "launched": False}
        return {**w, "launched": _open_file(real)}
    if w["state"] == "moved":                       # the file has gone; its folder is shown, and the answer says so
        return {**w, "launched": _show(real.parent)}
    return {**w, "launched": _show(real)}


# ── Routes ───────────────────────────────────────────────────────────────────

def routes(lock):
    """The routes for live_server's table, given its lock (each answers 200 with {ok, ...}; never a path or a proposal's name)."""
    def read(handler, req):
        """POST /api/minutes/destination {file}: where the minutes will be filed (read only)."""
        return handler.send(200, view(req.get("file")))

    def name(handler, req):
        """POST /api/minutes/destination/name {file, code, name}: file the minutes under another name."""
        with lock:
            if isinstance(req.get("names"), dict):          # all projects at once: all or none
                return handler.send(200, set_names(req.get("file"), req["names"]))
            return handler.send(200, set_name(req.get("file"), str(req.get("code") or ""), req.get("name")))

    def at(handler, req):
        """POST /api/minutes/destination/where {key | path}: where approved minutes sit now (read only)."""
        return handler.send(200, where(req.get("key"), req.get("path")))

    def open_(handler, req):
        """POST /api/minutes/destination/open {key | path, what}: open the minutes, or show them in Finder."""
        return handler.send(200, open_where(req.get("key"), req.get("path"), "file" if req.get("what") == "file" else "folder"))

    return {"/api/minutes/destination": read, "/api/minutes/destination/name": name,
            "/api/minutes/destination/where": at, "/api/minutes/destination/open": open_}
