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

def paragraphs(body):
    """[(n, text)] for a note's body: blocks separated by blank lines, numbered from 1 in order (a source's `#p<n>`)."""
    out, buf = [], []
    for ln in body.split("\n") + [""]:
        if ln.strip():
            buf.append(ln)
        elif buf:
            out.append((len(out) + 1, "\n".join(buf)))
            buf = []
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


def record_sent(rel, entries, at):
    """Add what one Find updates apply sent from the note at stored path `rel`: `entries` is [(paragraph number, paragraph text,
    [item IDs])]; only the number, the text's fingerprint and the IDs are kept, with `at` (YYYY-MM-DD HH:MM). Written whole, through
    a temporary file. Returns the note's records."""
    data = _sent_all()
    rows = data.setdefault(rel, [])
    for n, text, ids in entries:
        rows.append({"p": int(n), "fp": fingerprint(text), "ids": [str(i) for i in ids], "at": str(at)})
    paths.NOTES_SENT.parent.mkdir(parents=True, exist_ok=True)
    tmp = paths.NOTES_SENT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"version": 1, "notes": data}, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, paths.NOTES_SENT)
    return rows


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
