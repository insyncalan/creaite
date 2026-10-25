"""creaite capture (BL-301 C): the capture drawer's server side. A library for the live server: it has no command line, and it
writes a note file only through filechange.py (backed up, logged and undoable). Standard library only.

  guess(text)     which project a note is about, from the project register's signals, by the rules cx-minutes uses
                  (.claude/skills/cx-minutes/references/project-matching.md): {code, reason, candidates}. No guess (nothing
                  strong or medium, or signals for two projects) is code None: the note goes to Unfiled (the portfolio's notes
                  folder, `_Portfolio/08 Notes`).
  draft / drafts  the drawer's text as Alan types: one JSON file per drawer in system/staging/drafts/notes/ (capture-<id>.json),
                  removed once the note file is written.
  save            the note file, made from a template (notes.py) with the typed body, created through filechange.py in the
                  project's notes folder (or Unfiled's), named by its title; a taken name gets a number.
  recent          the newest notes across the projects and Unfiled, for the drawer's foot.
  meeting         what "Note for this meeting" fills in: the meeting's title, date, attendees and project, from the saved calendar.

Notes are internal and passive: nothing here extracts anything or reaches the tracker. Find updates (part E) does that, from the
note, when Alan asks.
"""
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
import notes  # noqa: E402

UNFILED = "_portfolio"                      # Unfiled notes live in the portfolio's notes folder
DRAFTS = paths.DRAFTS / "notes"
ID_RE = re.compile(r"[a-z0-9][a-z0-9-]{5,40}")
CODE_RE = re.compile(r"[A-Z][A-Z0-9]{2,6}")
TEXT_LIMIT = 100_000                        # characters in one note's body
TITLE_LIMIT = 120
RECENT = 5


# ── The register's signals ────────────────────────────────────────────────────

def _cells(line):
    """The cells of one Markdown table row."""
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _list(cell):
    """A register cell's comma- or semicolon-separated entries."""
    return [w.strip() for w in re.split(r"[,;]", cell or "") if w.strip()]


def _person(entry):
    """A stakeholder's name without its role: "Jane Doe (sponsor)" is "Jane Doe"."""
    return re.sub(r"\s*\(.*?\)\s*", " ", entry).strip()


def _row(code, row):
    """One Projects row of the register as {code, name, aliases, people, domains, channels, keywords, senders, exclude}."""
    def col(*names):
        """The cell under the first heading that starts with one of `names`."""
        return next((row[k] for k in row for n in names if k.startswith(n)), "")
    return {"code": code, "name": col("project name"),
            "aliases": _list(col("aliases")), "people": [_person(p) for p in _list(col("key stakeholders"))],
            "domains": [d.lower().lstrip("@") for d in _list(col("email domains"))],
            "channels": _list(col("teams channels")), "keywords": _list(col("keywords")),
            "senders": [x.lower() for x in _list(col("senders"))], "exclude": _list(col("exclude"))}


def _tables(text):
    """(section, {heading: cell}) for every row of every table in the register, under its `## ` section."""
    section, head = "", None
    for line in text.splitlines():
        if line.startswith("## "):
            section, head = line[3:].strip(), None
        elif line.startswith("|"):
            cells = _cells(line)
            if head is None:
                head = [c.lower() for c in cells]
            elif not set("".join(cells)) <= set("-: "):
                yield section, cells, dict(zip(head, cells))


def register():
    """{"projects": [project rows], "shared": {lower-case names}} from projects/_portfolio/project-register.md, by its column
    headings (an older register without Senders or Exclude works)."""
    try:
        text = paths.REGISTER.read_text(encoding="utf-8")
    except OSError:
        return {"projects": [], "shared": set()}
    out, shared = [], set()
    for section, cells, row in _tables(text):
        if section == "Projects" and CODE_RE.fullmatch(cells[0] or ""):
            out.append(_row(cells[0], row))
        elif section.startswith("Shared") and cells[0]:
            shared.add(_person(cells[0]).lower())
    return {"projects": out, "shared": shared}


def _has(low, word):
    """Whether the lower-case text holds `word` as a whole word or phrase."""
    w = word.lower().strip()
    return len(w) > 2 and re.search(rf"(?<![a-z0-9]){re.escape(w)}(?![a-z0-9])", low) is not None


def _quoted(words):
    """Up to three words, quoted and joined: “a”, “b” and “c”."""
    words = list(dict.fromkeys(words))[:3]
    q = [f"“{w}”" for w in words]
    return q[0] if len(q) == 1 else ", ".join(q[:-1]) + " and " + q[-1]


def _people_signals(p, low, shared, first_names):
    """The stakeholders of project `p` the text names: a full name, or a first name only this project's stakeholders have."""
    out = []
    for n in p["people"]:
        if n.lower() in shared:
            continue
        first = n.split()[0] if " " in n else ""
        if _has(low, n):
            out.append(n)
        elif first and first_names.get(first.lower()) == {p["code"]} and _has(low, first):
            out.append(first)
    return out


def _signals(p, raw, low, shared, first_names):
    """(strong, medium, weak) signal words for project `p` in the text; None when a word in its Exclude column rules it out."""
    if any(_has(low, w) for w in p["exclude"]):
        return None
    strong = [p["code"]] if re.search(rf"(?<![A-Za-z0-9]){re.escape(p['code'])}(?![A-Za-z0-9])", raw) else []
    strong += [c for c in p["channels"] if _has(low, c)]
    medium = [p["name"]] if p["name"] and _has(low, p["name"]) else []
    medium += [a for a in p["aliases"] if a.lower() not in shared and _has(low, a)]
    medium += _people_signals(p, low, shared, first_names)
    medium += [x for x in p["senders"] if x in low]
    medium += [d for d in p["domains"] if re.search(rf"[@.]{re.escape(d)}(?![a-z0-9-])", low) or _has(low, d)]
    kws = [k for k in p["keywords"] if k.lower() not in shared and _has(low, k)]
    return (strong, medium + kws, []) if len(kws) >= 2 else (strong, medium, kws)


def _first_names(rows, shared):
    """{first name: {codes}} of the stakeholders listed with a full name (a first name alone is a signal only when it is one
    project's)."""
    out = {}
    for p in rows:
        for n in p["people"]:
            if n.lower() not in shared and " " in n:
                out.setdefault(n.split()[0].lower(), set()).add(p["code"])
    return out


def _verdict(found, weak, names):
    """The guess from the signals found: one project with strong or medium signals is it; two is a conflict; one keyword is not
    enough; none is nothing."""
    if len(found) == 1:
        (code, (strong, medium, _w)), = found.items()
        return {"code": code, "strength": "strong" if strong else "medium", "candidates": [code],
                "reason": f"guessed from {_quoted(strong + medium)}"}
    if found:
        codes = sorted(found)
        return {"code": None, "strength": "conflict", "candidates": codes,
                "reason": "could be " + " or ".join(names.get(c) or c for c in codes) + ": choose the project"}
    if weak:
        codes = sorted(weak)
        return {"code": None, "strength": "weak", "candidates": codes,
                "reason": f"only {_quoted([w for c in codes for w in weak[c]])} points to a project: not enough to guess"}
    return {"code": None, "strength": "none", "candidates": [], "reason": "nothing in the note names a project yet"}


def guess(text, active=None):
    """Which project a note is about: {code, reason, candidates, strength}. Strong signals (the code as a whole token or [CODE],
    a Teams channel) and medium ones (the project's name, an alias or client name, a stakeholder listed under that project only,
    a sender or a client domain, two or more keywords) assign the note; one keyword alone doesn't; a word in a project's Exclude
    column rules it out; Shared names are never a signal; signals for two projects are a conflict. `active` limits it to those
    codes (the active projects). No guess: code None, and the reason says why."""
    reg = register()
    rows = [p for p in reg["projects"] if active is None or p["code"] in active]
    raw = text or ""
    for name in sorted(reg["shared"], key=len, reverse=True):      # a Shared name is never a signal, nor a word inside it
        raw = re.sub(rf"(?<![A-Za-z0-9]){re.escape(name)}(?![A-Za-z0-9])", " ", raw, flags=re.I)
    first_names = _first_names(rows, reg["shared"])
    found, weak = {}, {}
    for p in sorted(rows, key=lambda r: -len(r["code"])):          # longer codes first: [ORX] never matches [ORX2C]
        sig = _signals(p, raw, raw.lower(), reg["shared"], first_names)
        if sig and (sig[0] or sig[1]):
            found[p["code"]] = sig
        elif sig and sig[2]:
            weak[p["code"]] = sig[2]
    return _verdict(found, weak, {p["code"]: p["name"] for p in rows})


# ── Drafts, as Alan types ─────────────────────────────────────────────────────

def _draft_file(did):
    """The draft file of drawer `did`; raises ValueError for an id that isn't one."""
    if not ID_RE.fullmatch(str(did or "")):
        raise ValueError("Not a draft id.")
    return DRAFTS / f"capture-{did}.json"


def _code(req):
    """The request's project code (Unfiled when none); raises ValueError for one that isn't a code."""
    code = str(req.get("code") or "")
    if code and code != UNFILED and not CODE_RE.fullmatch(code):
        raise ValueError("Not a project code.")
    return code or UNFILED


def _day(req):
    """The request's date (YYYY-MM-DD, or ""); raises ValueError otherwise."""
    day = str(req.get("date") or "")
    if day and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        raise ValueError("The date must be YYYY-MM-DD.")
    return day


def clean(req):
    """The drawer's fields from a request, checked: {code, title, body, template, date, with, confidential}. `confidential` is the
    drawer's switch (off unless set): true only for a real true. Raises ValueError with a reason Alan can read."""
    body = str(req.get("body") or "").replace("\r\n", "\n")
    if len(body) > TEXT_LIMIT:
        raise ValueError("A note can be 100,000 characters at most.")
    template = str(req.get("template") or "blank")
    if template not in notes.TEMPLATES:
        raise ValueError("Not a note template.")
    people = [re.sub(r"\s+", " ", str(p)).strip()[:80] for p in (req.get("with") or []) if str(p).strip()][:40]
    return {"code": _code(req), "title": re.sub(r"\s+", " ", str(req.get("title") or "")).strip()[:TITLE_LIMIT], "body": body,
            "template": template, "date": _day(req), "with": people, "confidential": req.get("confidential") is True}


def draft(did, fields, at=None):
    """Keep the drawer's text as a draft (written whole, through a temporary file). Returns the time it was kept, HH:MM."""
    f = _draft_file(did)
    f.parent.mkdir(parents=True, exist_ok=True)
    stamp = at or datetime.now().strftime("%Y-%m-%d %H:%M")
    tmp = f.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"id": did, "at": stamp, **fields}, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, f)
    return stamp


def drafts():
    """The drafts kept and not yet saved as notes, newest first: [{id, title, code, at, body, template, date, with}]."""
    out = []
    for f in DRAFTS.glob("capture-*.json") if DRAFTS.is_dir() else []:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):       # a draft half-written or gone while listed: skipped this time
            continue
        if isinstance(d, dict) and ID_RE.fullmatch(str(d.get("id") or "")) and \
                f"{d.get('body') or ''}{d.get('title') or ''}".strip():
            out.append(d)
    return sorted(out, key=lambda d: str(d.get("at") or ""), reverse=True)


def discard(did):
    """Remove a draft (Discard, or once its note is written)."""
    _draft_file(did).unlink(missing_ok=True)


# ── The note file ─────────────────────────────────────────────────────────────

def title_of(fields):
    """The note's title: as typed, else the body's first words (without Markdown), else 'Untitled note'."""
    if fields["title"]:
        return fields["title"]
    first = next((ln for ln in fields["body"].splitlines() if ln.strip()), "")
    words = re.sub(r"[#*_`>\[\]]+", " ", first).split()[:8]
    return " ".join(words).strip(" .:-")[:60] or "Untitled note"


def text_of(fields, title, today=None):
    """The note file's text: the template's front matter (a Working session's date and attendees too, and `confidential: true` when
    the drawer's switch is on, as notes.py records it) over the typed body."""
    meta, _body = notes.parse(notes.template(fields["template"], title, today=today, when=fields["date"] or None,
                                             people=fields["with"]))
    meta["confidential"] = bool(fields.get("confidential"))
    return notes.render(meta, fields["body"].rstrip("\n") + "\n")


def save(fields, via="dashboard"):
    """Write the note through filechange.py: a new file in the project's (or Unfiled's) notes folder, named by its title, a taken
    name getting a number. (code, message, stored path or None): 0 saved; 3 needs approval (an ask creaite run has read outside
    content, so a change waits: the draft is kept); 1 refused."""
    import filechange
    title = title_of(fields)
    try:
        target = notes.folder(fields["code"]) / f"{notes.file_name(title)}.md"
    except LookupError:                       # a code with no project folder
        return 1, "That project has no folder.", None
    data = text_of(fields, title).encode("utf-8")
    ch = {"op": "create", "path": str(target), "data": data, "why": f"Note captured: {title}"}
    code, msg = filechange.perform(ch, None, via)
    if code:
        return code, msg, None
    m = re.match(r"Created (.+) \(change \d+\)\.$", msg)
    return 0, msg, m.group(1) if m else None


# ── Recent notes and the meeting's details ────────────────────────────────────

def recent(codes, limit=RECENT):
    """The newest notes across `codes` and Unfiled: [{path, title, code, at}], by when the file last changed."""
    out = []
    for code in list(codes) + [UNFILED]:
        try:
            files = paths.note_files(code)
        except LookupError:                   # a project with no folder has no notes
            continue
        for f in files:
            try:
                st = f.stat()
            except OSError:                   # gone while listed
                continue
            meta = notes.read(f)[0]
            out.append({"path": paths.rel(f), "title": str(meta.get("title") or f.stem), "code": code,
                        "at": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"), "_m": st.st_mtime})
    out.sort(key=lambda r: r["_m"], reverse=True)
    return [{k: v for k, v in r.items() if k != "_m"} for r in out[:limit]]


def _attendees(ev, me):
    """The meeting's attendees by name, without Alan; none for a confidential meeting (the calendar keeps nothing more)."""
    if (ev.get("sensitivity") or "") == "confidential":
        return []
    mine, people = (me or "").strip().lower(), []
    for a in ev.get("attendees") or []:
        n = (a.get("name") if isinstance(a, dict) else str(a or "")).strip()
        if n and n.lower() != mine and n not in people:
            people.append(n)
    return people


def meeting(day, start, title, projects, remembered=None, me=""):
    """What "Note for this meeting" fills in from the saved calendar: {title, date, with, code, how}, or None when the meeting
    isn't there or is private. A confidential meeting gives only its title and date."""
    import build_dashboard
    evs = build_dashboard.saved_calendar_days().get(day) or []
    ev = next((e for e in evs if e.get("title") == title and (not start or e.get("start") == start)), None)
    sens = build_dashboard.invite_clean.sensitivity(ev) if ev else "private"
    if sens == "private":
        return None
    if sens == "confidential":                           # #362: title and date only; no people
        # A confidential meeting's project counts only when Alan chose it (a remembered series, prep_page._project_of's rule);
        # a guess from the title shows nothing selected (#343 M1). The drawer then does not guess either.
        code, how = build_dashboard.prep_match(title, projects, remembered or {})
        chosen = how == "remembered" and code and code != "_portfolio"
        return {"title": title, "date": day, "with": [], "code": code if chosen else None,
                "how": "remembered" if chosen else "confidential"}
    code, how = build_dashboard.prep_match(title, projects, remembered or {})
    return {"title": title, "date": day, "with": _attendees(ev, me), "code": code or None, "how": how}
