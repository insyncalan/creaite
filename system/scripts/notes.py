"""creaite notes (BL-301): the note file format, the notes folder and the record of what Find updates applied. A library: it has
no command line and writes nothing to a project folder itself (a note is created and saved through filechange.py, backed up,
logged and undoable). Standard library only.

A note is one Markdown file, flat in the project's notes folder (`locations.folders.notes`, default `08 Notes`; `notes/` in the
default layout), named by its title (a taken name gets a number), with its pictures in `<notes folder>/_images/`. Portfolio notes
live in the portfolio folder's notes folder. The folder is made on the first note (and for every new project). A note starts with
a small front matter, so it reads cleanly in Finder and OneDrive without creaite:

    ---
    title: Stakeholder map
    created: 2026-10-13
    updated: 2026-10-13
    tags: [stakeholders, client]
    pinned: false
    confidential: false
    date: 2026-10-13          (a Working session note only: the meeting's date)
    with: [Mia Hale]     (a Working session note only: who it was with)
    ---

    The body, in Markdown.

Dates are stored YYYY-MM-DD. A key creaite doesn't know is kept as written, after the known ones. Notes are passive: never extracted,
never read by the sweep or an unattended run; search indexes them as kind `note` (tracker.py index), and a note marked confidential
is left out of what search gathers for Claude.

What Find updates applied (part E) is kept beside the note, never in it: system/staging/notes-sent.json, per note path the paragraph
number, a fingerprint of its text and the item IDs it became. Never the text itself.
"""
import hashlib
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

FIELDS = ("title", "created", "updated", "tags", "pinned", "confidential", "date", "with")
LISTS = ("tags", "with")
FLAGS = ("pinned", "confidential")
TEMPLATES = ("blank", "stakeholder", "lessons-learned", "working-session")
TEMPLATE_DIR = paths.TEMPLATES / "notes"
FENCE = "---"


# ── The format ────────────────────────────────────────────────────────────────

def _value(raw):
    """One front-matter value as written: a [list], true/false, or text (quotes taken off)."""
    v = raw.strip()
    if v.startswith("[") and v.endswith("]"):
        return [x.strip().strip("\"'") for x in v[1:-1].split(",") if x.strip().strip("\"'")]
    if v.lower() in ("true", "false"):
        return v.lower() == "true"
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


def parse(text):
    """(front matter as a dict, body) of a note's text. Text without front matter is all body, with an empty dict. A list key
    always comes back a list and a flag a bool, whatever was written."""
    text = text.lstrip("﻿")
    lines = text.split("\n")
    if not lines or lines[0].rstrip() != FENCE:
        return {}, text
    end = next((i for i in range(1, len(lines)) if lines[i].rstrip() == FENCE), None)
    if end is None:
        return {}, text
    meta = {}
    for ln in lines[1:end]:
        m = re.match(r"\s*([A-Za-z_][\w-]*)\s*:(.*)$", ln)
        if m:
            meta[m.group(1)] = _value(m.group(2))
    for k in LISTS:
        if k in meta and not isinstance(meta[k], list):
            meta[k] = [x.strip() for x in str(meta[k]).split(",") if x.strip()]
    for k in FLAGS:
        if k in meta and not isinstance(meta[k], bool):
            meta[k] = str(meta[k]).strip().lower() in ("yes", "y", "1", "true")
    body = "\n".join(lines[end + 1:])
    return meta, body[1:] if body.startswith("\n") else body


def _written(v):
    """One front-matter value as it is written."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(str(x).replace(",", " ").strip() for x in v if str(x).strip()) + "]"
    text = str(v if v is not None else "").replace("\n", " ").strip()
    return f'"{text}"' if text[:1] in "[\"'" or text.lower() in ("true", "false") else text


def render(meta, body):
    """A note's text from its front matter and body: the known keys in their order, then any others as given, then a blank line and
    the body. parse(render(meta, body)) gives them back."""
    keys = [k for k in FIELDS if k in meta] + [k for k in meta if k not in FIELDS]
    head = [FENCE] + [f"{k}: {_written(meta[k])}" for k in keys] + [FENCE]
    return "\n".join(head) + "\n\n" + body


def touched(meta, today=None):
    """The front matter with `updated` set to today (and `created`, if it had none): what a save writes."""
    day = (today or date.today()).isoformat()
    out = dict(meta)
    out.setdefault("created", day)
    out["updated"] = day
    return out


def read(p):
    """(front matter, body) of the note file `p`; ({}, "") when it can't be read."""
    try:
        return parse(Path(p).read_text(encoding="utf-8", errors="ignore"))
    except OSError:
        return {}, ""


def is_confidential(p):
    """Whether the note file `p` is marked confidential (BL-301: kept out of Prep pages and of what search gathers for Claude)."""
    return bool(read(p)[0].get("confidential"))


def held(p):
    """#60 option (a) (Alan, 15-10-2026): whether a Prep run must treat the note file `p` as confidential. Fail closed: marked
    confidential, online only (reading it would download it) or unreadable all count; only a note read and not marked is ordinary."""
    try:
        if paths.is_online_only(Path(p)):
            return True
        return bool(parse(Path(p).read_text(encoding="utf-8", errors="ignore"))[0].get("confidential"))
    except Exception:  # noqa: BLE001  fail closed
        return True


def index_text(p):
    """A note's text for the search index: its title and tags, then the body (the rest of the front matter left out)."""
    meta, body = read(p)
    head = [str(meta.get("title") or Path(p).stem)]
    if meta.get("tags"):
        head.append(", ".join(meta["tags"]))
    if meta.get("with"):
        head.append(", ".join(meta["with"]))
    return "\n".join(head) + "\n" + body


def index_date(p):
    """The date search files a note under: its meeting date (a Working session), else when it was last updated, else created,
    else a date in its name; '' when none."""
    meta = read(p)[0]
    for k in ("date", "updated", "created"):
        v = str(meta.get(k) or "")
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
            return v
    return paths.name_date(Path(p).name)[0] or ""


# ── The folder and new notes ──────────────────────────────────────────────────

def folder(code):
    """The notes folder of a project (or `_portfolio`), whether or not it has been made yet."""
    return paths.folder(code, "notes")


def images(code):
    """Where a project's note pictures go: `_images` in its notes folder (made with the first picture)."""
    return folder(code) / paths.NOTE_IMAGES


def file_name(title):
    """A note's file stem from its title: characters a file name can't hold (in Finder, OneDrive or Windows) become spaces, and a
    leading dot is dropped. 'Untitled note' when nothing is left."""
    stem = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', " ", str(title or ""))
    stem = re.sub(r"\s+", " ", stem).strip().lstrip(".").strip()[:120].rstrip()
    return stem or "Untitled note"


def new_path(code, title):
    """Where a new note with this title goes: `<notes folder>/<title>.md`, a taken name getting a number. Makes nothing."""
    return paths.free_path(folder(code), file_name(title), ".md")


def template(name, title, today=None, when=None, people=()):
    """A new note's text from one of the four templates (blank, stakeholder, lessons-learned, working-session): the template's body
    under fresh front matter. A Working session note also gets the meeting's date (`when`, default today) and who it was with."""
    if name not in TEMPLATES:
        raise ValueError(f"a note template is one of {', '.join(TEMPLATES)}")
    meta, body = parse((TEMPLATE_DIR / f"{name}.md").read_text(encoding="utf-8"))
    day = (today or date.today()).isoformat()
    meta.update({"title": str(title).strip() or "Untitled note", "created": day, "updated": day})
    meta.setdefault("tags", [])
    meta.setdefault("pinned", False)
    meta.setdefault("confidential", False)
    if name == "working-session":
        meta["date"] = when or day
        meta["with"] = [str(p).strip() for p in people if str(p).strip()]
    return render(meta, body)


# ── Paragraphs and what Find updates applied (notes-sent.json) ────────────────

LIST_ITEM = re.compile(r"(?:[-*+]|\d{1,3}[.)])\s")      # BL-301 E: a top-level list item ("- ", "* ", "1. ", "- [ ] ")


def paragraphs(body):
    """[(n, text)] for a note's body: blocks separated by blank lines, numbered from 1 in order (a source's `#p<n>`). BL-301 E: in a
    list, each top-level item is its own line (its indented sub-items and continuation lines stay with it), because Find updates
    marks, and sends, a note line by line, and a tight list has no blank lines between its items."""
    out, buf = [], []

    def flush():
        """End the line being gathered."""
        if buf:
            out.append((len(out) + 1, "\n".join(buf)))
            buf.clear()

    for ln in body.split("\n") + [""]:
        if not ln.strip():
            flush()
        elif buf and LIST_ITEM.match(ln) and LIST_ITEM.match(buf[0]):
            flush()                                        # the next item of the same list
            buf.append(ln)
        else:
            buf.append(ln)
    return out


def fingerprint(text):
    """A paragraph's fingerprint: the first 16 hex characters of the SHA-256 of its text with the spacing evened out. Says whether
    a line changed, never what it says."""
    return hashlib.sha256(re.sub(r"\s+", " ", text).strip().encode("utf-8")).hexdigest()[:16]


def _sent_all():
    """notes-sent.json as {note path: [{p, fp, ids, at}]}; {} when it is missing or unreadable."""
    try:
        data = json.loads(paths.NOTES_SENT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data.get("notes") if isinstance(data, dict) and isinstance(data.get("notes"), dict) else {}


def sent(rel):
    """What Find updates applied from the note at stored path `rel`: [{p, fp, ids, at}], oldest first."""
    return list(_sent_all().get(rel) or [])


def record_sent(rel, entries, at, apply_id=None):
    """Add what one Find updates apply sent from the note at stored path `rel`: `entries` is [(paragraph number, paragraph text,
    [item IDs])]; only the number, the text's fingerprint and the IDs are kept, with `at` (YYYY-MM-DD HH:MM) and, when it was
    applied, the apply's number (`apply`, so an Undo can take it back: forget_sent). Written whole, through a temporary file.
    Returns the note's records."""
    data = _sent_all()
    rows = data.setdefault(rel, [])
    for n, text, ids in entries:
        rows.append({"p": int(n), "fp": fingerprint(text), "ids": [str(i) for i in ids], "at": str(at),
                     **({"apply": int(apply_id)} if apply_id is not None else {})})
    _write_sent(data)
    return rows


def _write_sent(data):
    """notes-sent.json written whole, through a temporary file."""
    paths.NOTES_SENT.parent.mkdir(parents=True, exist_ok=True)
    tmp = paths.NOTES_SENT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"version": 1, "notes": data}, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, paths.NOTES_SENT)


def forget_sent(rel, apply_id):
    """BL-301 E: after an Undo of apply `apply_id`, the note's lines that apply sent count as new again. Returns how many records
    went."""
    data = _sent_all()
    rows = data.get(rel) or []
    keep = [r for r in rows if r.get("apply") != int(apply_id)]
    if len(keep) == len(rows):
        return 0
    if keep:
        data[rel] = keep
    else:
        data.pop(rel, None)
    _write_sent(data)
    return len(rows) - len(keep)


def unsent(rel, body):
    """[(n, text)] of the note's paragraphs that Find updates has not sent yet: new or changed lines (matched by fingerprint, so a
    paragraph moved up or down still counts as sent)."""
    done = {r.get("fp") for r in sent(rel)}
    return [(n, t) for n, t in paragraphs(body) if fingerprint(t) not in done]


def sent_ids(rel, body):
    """{paragraph number: [item IDs]} for the paragraphs of the note's current body that became items: the margin ticks."""
    by_fp = {}
    for r in sent(rel):
        ids = by_fp.setdefault(r.get("fp"), [])
        ids.extend(x for x in dict.fromkeys(r.get("ids") or []) if x not in ids)
    return {n: by_fp[fingerprint(t)] for n, t in paragraphs(body) if fingerprint(t) in by_fp}


# ===== BL-301 B (v20-notes-tab): what the Notes tab reads =====
# The Notes tab (the dashboard, through the live server's /api/notes/* routes) lists a project's notes from their front matter and
# the references in their bodies (no text), opens one, and writes the file through filechange.py as Alan types (backed up once per
# editing session, logged, undoable; #119). Nothing here writes a project file. DRAFT_DIR holds the capture drawer's drafts
# (capture.py); the Notes tab keeps none since #119, and reach.py still treats any left there as a note's typed copy.

WIKI_LINK = re.compile(r"\[\[([^\[\]\n|]{1,160})(?:\|[^\[\]\n]*)?\]\]")
ITEM_LINK = re.compile(r"\]\(creaite:item/([A-Za-z0-9-]{3,30})\)")
ITEM_ID = re.compile(r"(?<![A-Za-z0-9/-])([A-Z][A-Z0-9]{2,6}-[A-Z]-\d{2,4})(?![A-Za-z0-9-])")
PERSON_LINK = re.compile(r"@\[([^\[\]\n]{1,80})\]\(creaite:person/[^)\s]*\)")
KIND_WORDS = (("working-session", "Working session"), ("stakeholder", "Stakeholder"), ("lessons", "Lessons learned"))
DRAFT_DIR = paths.DRAFTS / "notes"


def kind_of(meta):
    """The note's kind as the list shows it ("Stakeholder", "Lessons learned", "Working session"), from its front matter; ''."""
    if meta.get("date") or meta.get("with"):
        return "Working session"
    tags = [str(t).lower() for t in meta.get("tags") or []]
    for key, word in KIND_WORDS:
        if any(t == key or t.startswith(key) for t in tags):
            return word
    return ""


def refs(body):
    """{links, items, people} the body points at: the titles in [[…]], the item IDs (chips and plain IDs) and the people (@[…])."""
    def once(xs):
        """Each value once, in order, stripped."""
        return list(dict.fromkeys(x.strip() for x in xs if x.strip()))
    return {"links": once(WIKI_LINK.findall(body)), "items": once(ITEM_LINK.findall(body) + ITEM_ID.findall(body)),
            "people": once(PERSON_LINK.findall(body))}


def text_sha(text):
    """What a save checks the file against: the SHA-256 of the note's text as it was opened (16 hex characters)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def summary(p, code=None):
    """One note as the list and the dashboard's data hold it: where it is, its front matter and what it points at. Never its text."""
    p = Path(p)
    text = p.read_text(encoding="utf-8", errors="ignore")
    meta, body = parse(text)
    from datetime import datetime
    mod = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    out = {"path": paths.rel(p), "file": p.name, "title": str(meta.get("title") or p.stem), "created": str(meta.get("created") or ""),
           "updated": str(meta.get("updated") or ""), "tags": list(meta.get("tags") or []), "pinned": bool(meta.get("pinned")),
           "confidential": bool(meta.get("confidential")), "date": str(meta.get("date") or ""), "with": list(meta.get("with") or []),
           "kind": kind_of(meta), "mod": mod, **refs(body)}
    if code:
        out["p"] = code
    return out


def listing(code):
    """[summary] of a project's (or `_portfolio`'s) notes: pinned first, then the most recently changed."""
    out = []
    for f in paths.note_files(code):
        try:
            out.append(summary(f, code))
        except OSError:  # a note that went while the list was read is simply not listed
            continue
    return sorted(out, key=lambda n: (not n["pinned"], -_stamp(n)))


def _stamp(n):
    """A sortable number for when a note last changed: its file's time, else its `updated` date."""
    t = n.get("mod") or n.get("updated") or ""
    return int(re.sub(r"\D", "", t)[:12].ljust(12, "0") or 0)


def note_of(rel):
    """(code, real path) when the stored path `rel` is a note directly in a notes folder; else None."""
    s = str(rel or "")
    if not s or ".." in Path(s).parts or not s.lower().endswith(".md"):
        return None
    p = paths.resolve(s)
    if not paths.is_note(p):
        return None
    area = paths.project_area(p)
    return (area[0], p) if area else None


EDITABLE = ("title", "tags", "pinned", "confidential", "date", "with")


def clean_changes(changes):
    """The front-matter changes a save may make, kept to known keys, types and sizes."""
    out = {}
    for k, v in (changes or {}).items():
        if k not in EDITABLE:
            continue
        if k in FLAGS:
            out[k] = bool(v)
        elif k in LISTS:
            vals = v if isinstance(v, list) else str(v or "").split(",")
            out[k] = [str(x).replace(",", " ").strip()[:60] for x in vals if str(x).strip()][:20]
        elif k == "date":
            if v and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(v)):
                continue
            out[k] = str(v or "")
        else:
            out[k] = re.sub(r"\s+", " ", str(v or "")).strip()[:160]
    return out


def saved_text(text, body=None, changes=None, today=None):
    """The note's new text from its current `text`: the body (None keeps it) and the front-matter changes, stamped `updated`. None
    when nothing would change (so an unchanged note isn't written)."""
    meta, old = parse(text)
    new = dict(meta)
    for k, v in clean_changes(changes).items():
        if k == "date" and not v:
            new.pop("date", None)
        else:
            new[k] = v
    if not new.get("title"):
        new["title"] = meta.get("title") or "Untitled note"
    body = old if body is None else str(body)
    if new == meta and body == old:
        return None
    return render(touched(new, today), body)
# ===== end BL-301 B =====


# ===== BL-301 B gaps (v20-notes-gaps): pictures, a renamed title renames the file, links to a renamed note =====
# Pictures go in the notes folder's `_images/` and are written `![caption](_images/<name>)` (a path beside the note, so the
# Markdown reads in Finder and OneDrive). A note whose title changes is renamed to match (a move through filechange.py), and
# the `[[…]]` links to it in other notes are changed to the new title. Nothing here writes a file: the live server does, through
# filechange.py.

IMAGE_REF = re.compile(r"!\[[^\]\n]*\]\((_images/[A-Za-z0-9][A-Za-z0-9._-]{0,120}\.(?:png|jpe?g))\)", re.I)
WIKI_PARTS = re.compile(r"\[\[([^\[\]\n|]{1,160})(\|[^\[\]\n]*)?\]\]")


def image_refs(body):
    """The `_images/…` pictures a note's body shows, each once, in order."""
    return list(dict.fromkeys(IMAGE_REF.findall(body or "")))


def image_name(label, ext, today=None):
    """A new picture's file name: `YYYY-MM-DD-<words>.<ext>`, no spaces (a Markdown image link can't hold one)."""
    slug = re.sub(r"[^a-z0-9]+", "-", str(label or "").lower()).strip("-")[:40].strip("-") or "image"
    return f"{(today or date.today()).isoformat()}-{slug}.{ext}"


def name_fits(p, title):
    """Whether the note file `p` is already named by `title` (or by it with the number a taken name gets)."""
    want, stem = file_name(title), Path(p).stem
    return stem == want or bool(re.fullmatch(re.escape(want) + r"(?:-\d+| \(\d+\))", stem)) or stem.lower() == want.lower()


def link_safe(title):
    """Whether a title can stand in a [[…]] link (no brackets, bar or line break)."""
    return bool(title) and not re.search(r"[\[\]|\n]", title)


def relinked(text, old_names, new_title):
    """The note's text with each [[old]] (or [[old|shown]]) link to a renamed note pointing at `new_title`; the front matter is left
    as it is. `old_names` are matched without regard to case. None when no link changes."""
    olds = {str(o).strip().lower() for o in old_names if str(o).strip()}
    _meta, body = parse(text)
    head = text[:len(text) - len(body)]

    def swap(m):
        """One link, pointed at the new title when it named the old one."""
        return f"[[{new_title}{m.group(2) or ''}]]" if m.group(1).strip().lower() in olds else m.group(0)
    new_body = WIKI_PARTS.sub(swap, body)
    return None if new_body == body else head + new_body
# ===== end BL-301 B gaps =====
