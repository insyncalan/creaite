"""creaite meeting prep, shaping (BL-286 part C): Alan's focus and aim for one meeting, and what follows from it. Standard library only.

Plain code here; the model only words the notes (drafts.py kind "shape", through the live server's run engine, read-only).
  - suggestions(key): chips for the instruction box, from the invite's ranking, overdue items and what wasn't covered last time.
  - focus_filter(con, codes, focus, excluded): the work items and documents linked to the accepted focus, each with why, n of N.
  - shape_sources(con, ctx, instruction, reading): the numbered sources the shaping prompt cites ([S1]…).
  - merge(new, current, clear): Regenerate keeps the note sections Alan edited unless he clears them.
  - save(key, payload): Accept (and in-place edits) into system/staging/prep-focus.json, the server's own write.

A confidential meeting (the calendar kept only its title and times) is shaped from Alan's text and the tracker only: the invite,
its ranking, minutes, documents and carried points are never sources, and the run is given no tools.

prep-focus.json: {"version": 1, "meetings": {"<YYYY-MM-DD|HH:MM|title>": record}}; a record is
  {key, title, day, start, instruction, reading: {focus: [{id?, text}], aim, show: focus-only|focus-first},
   notes: {objective|talking_points|ask|carried_over: [line]}, drafted: {same, as creaite last drafted them},
   edited: [sections Alan changed], excluded: [item IDs or document paths ticked out], accepted_at, updated_at}
  where a line is {text, sources: [typed source]} (prep_view.typed). Nothing here reaches the tracker.
"""
import json
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

FOCUS = paths.STAGING / "prep-focus.json"
SECTIONS = ("objective", "talking_points", "ask", "carried_over")
HEADS = {"objective": "OBJECTIVE", "talking_points": "TALKING POINTS", "ask": "ASK", "carried_over": "CARRIED OVER"}
SHOW = ("focus-only", "focus-first")
ID_RE = re.compile(r"\b[A-Z][A-Z0-9]{2,6}-(?:[A-Z]-)?\d{3}\b")
MAX_SOURCES = 30
MAX_CHIPS = 6
LIMITS = {"instruction": 4000, "aim": 600, "line": 600, "lines": 12, "focus": 12, "excluded": 200, "questions": 12}


def now():
    """The time now on creaite's clock (sweep.now; CREAITE_NOW fixes it for tests)."""
    import sweep
    return sweep.now()


def canonical(key, day):
    """The meeting's stored ID: "YYYY-MM-DD|HH:MM|title", whichever form of the Prep brief's key is given."""
    parts = str(key or "").split("|")
    return key if len(parts) >= 3 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", parts[0]) else f"{day}|{key}"


def ro():
    """A read-only connection to the tracker, rows as sqlite3.Row: shaping never writes to it."""
    con = sqlite3.connect(f"file:{paths.DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def shown(iso):
    """YYYY-MM-DD → DD-MM-YYYY."""
    s = str(iso or "")
    return f"{s[8:10]}-{s[5:7]}-{s[:4]}" if re.match(r"\d{4}-\d{2}-\d{2}", s) else s


def short(text, n=160):
    """Text on one line, cut to n characters with an ellipsis."""
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    return t if len(t) <= n else t[:n - 1] + "…"


# ── suggestion chips ─────────────────────────────────────────────────────────

def _chip(kind, item_id, label, why, insert):
    return {"kind": kind, "id": item_id, "label": label, "why": why, "insert": insert}


def _ranked(rank, texts):
    """Chips for the three items the invite ranks highest."""
    rows = sorted(((sc[0], i, sc[1]) for ids in (rank or {}).values() for i, sc in ids.items()), key=lambda r: (-r[0], r[1]))
    out = []
    for _, item_id, why in rows[:3]:
        text = texts.get(item_id) or ""
        out.append(_chip("invite", item_id, f"{item_id} · {short(text, 40)}" if text else item_id, why, f"{item_id} ({short(text, 60)})"))
    return out


def _overdue(ctx, seen):
    """Chips for the listed work that is overdue at the meeting (decisions have their own chips: none)."""
    return [_chip("overdue", i["id"], f"{i['id']} · {short(i['text'], 40)}", f"overdue since {shown(i['due'])}",
                  f"{i['id']} ({short(i['text'], 60)})")
            for i in ctx.get("items") or [] if i["id"] not in seen and i.get("due") and i["due"] < ctx["day"]
            and i["table"] != "decisions"]


def suggestions(ctx, rank=None, texts=None):
    """Chips for the instruction box: the items the invite ranks highest, overdue items and what wasn't covered last time. A
    chip's `insert` is the text it adds. A confidential meeting has no invite ranking and no carried points."""
    confidential = bool((ctx.get("meeting") or {}).get("confidential"))
    texts = {**(texts or {}), **{i["id"]: i["text"] for i in ctx.get("items") or []}}
    out = [] if confidential else _ranked(rank, texts)
    out += _overdue(ctx, {c["id"] for c in out})
    if not confidential:
        out += [_chip("carried", None, short(c["point"], 48), f"not covered on {shown(c.get('day'))}",
                      f"carried over: {short(c['point'], 80)}") for c in ctx.get("carried") or []]
    return out[:MAX_CHIPS]


def milestone_chips(con, ctx):
    """Chips for the open milestones due within the due-soon window of the meeting ("Pilot go-live 06-11-2026")."""
    import drafts
    codes = (ctx.get("research") or {}).get("codes") or [ctx.get("project")]
    out = []
    for mid, name, due in drafts.milestones_due(con, codes, ctx["day"], max(30, ctx.get("due_soon_days") or 7)):
        out.append(_chip("milestone", mid, f"{short(name, 36)} {shown(due)}", "milestone due", f"{mid} ({name}, {shown(due)})"))
    return out


def chips(key):
    """{ok, chips, confidential} for a meeting key, or {ok: False, message}: the instruction box's suggestions."""
    import prep_page
    d = prep_page._collect()
    with prep_page.using(d):
        ctx = prep_page.context(key)
    if ctx.get("error"):
        return {"ok": False, "message": ctx["error"]}
    m = prep_page.meeting_entry(d, key)
    texts = {x["id"]: x.get("t") or "" for k in ("actions", "raid", "decisions") for x in d.get(k) or []}
    con = ro()
    try:
        out = (suggestions(ctx, m.get("rank"), texts) + milestone_chips(con, ctx))[:MAX_CHIPS]
    finally:
        con.close()
    return {"ok": True, "chips": out, "confidential": bool(ctx["meeting"].get("confidential"))}


# ── the focus filter ─────────────────────────────────────────────────────────

ITEM_SQL = {
    "actions": "SELECT id, project, description AS text, owner, due_date AS due, status, workstream, milestone, source FROM actions",
    "raid": "SELECT id, project, description AS text, owner, due_date AS due, status, workstream, milestone, source, type FROM raid",
    "decisions": "SELECT id, project, decision AS text, made_by AS owner, needed_by AS due, status, NULL AS workstream, "
                 "NULL AS milestone, source FROM decisions",
}
OPEN = {"actions": ("Open", "Delayed"), "raid": ("Open",), "decisions": ("Pending",)}


def source_key(src):
    """(kind, key, words) that groups items cited in the same place: a file (minutes, transcript), a mail thread (its subject
    without Re:/Fw:) or a Teams chat or channel. None for anything else."""
    s = str(src or "")
    if s.startswith("Email"):
        m = re.search(r"Subject:\s*(.*?)\s*(?:·|$)", s)
        subj = re.sub(r"^(?:(?:re|fw|fwd)\s*:\s*)+", "", (m.group(1) if m else "").strip(), flags=re.I)
        return ("mail", subj.lower(), f"the same mail thread ({short(subj, 60)})") if subj else None
    if s.startswith("Teams"):
        m = re.search(r"(Channel|Chat):\s*(.*?)\s*(?:·|$)", s)
        return ("teams", m.group(2).lower(), f"the same Teams {m.group(1).lower()} ({short(m.group(2), 60)})") if m else None
    head = s.split(" — ")[0].strip()
    if "/" in head:
        day, title, _ = paths.name_date(Path(head).name)
        what = "minutes" if "/minutes/" in head else "transcript" if "/transcripts/" in head else "file"
        return ("file", head, f"the same {what} ({title or Path(head).stem}{', ' + shown(day) if day else ''})")
    return None


def _rows(con, codes):
    """Every item of the projects, as dicts with their table."""
    out = []
    marks = ",".join("?" * len(codes))
    for table, sql in ITEM_SQL.items():
        for r in con.execute(f"{sql} WHERE project IN ({marks})", codes):
            out.append({**dict(r), "table": table})
    return out


def _milestone_names(con, codes):
    marks = ",".join("?" * len(codes))
    return {r[0]: r[1] for r in con.execute(f"SELECT id, name FROM milestones WHERE project IN ({marks})", codes)}


def _links(con, ids):
    """[(other, how)] for each focus ID: the links table, both ways."""
    out = {}
    for i in ids:
        for r in con.execute("SELECT from_item, to_item FROM links WHERE from_item = ? OR to_item = ?", (i, i)):
            other, how = (r[1], f"blocked by {i}") if r[0] == i else (r[0], f"blocks {i}")
            out.setdefault(other, []).append(how)
    return out


def _why(x, focus_rows, linked, ms_names):
    """The reasons an item is linked to the focus, strongest first."""
    why = list(linked.get(x["id"], []))
    for f in focus_rows:
        if x.get("workstream") and x["workstream"] == f.get("workstream") and x["project"] == f["project"]:
            why.append(f"same workstream ({x['workstream']}) as {f['id']}")
        ms = x.get("milestone")
        if ms and (ms == f.get("milestone") or ms == f["id"]):
            why.append(f"same milestone ({ms_names.get(ms, ms)}) as {f['id']}")
        sk, fk = source_key(x.get("source")), source_key(f.get("source"))
        if sk and fk and sk[:2] == fk[:2]:
            why.append(f"cited in {sk[2]} as {f['id']}")
    return list(dict.fromkeys(why))


def _universe(rows, focus_ids):
    """The open items (and the focus items whatever their status): the ones the filter looks through."""
    return [x for x in rows if x["id"] in focus_ids or x["status"] in OPEN[x["table"]]]


def _item_out(x, why, in_focus, excluded):
    return {"id": x["id"], "table": x["table"], "p": x["project"], "text": x["text"], "owner": x.get("owner") or "",
            "due": x.get("due") or "", "status": x.get("status") or "", "type": x.get("type") or
            {"actions": "Action", "decisions": "Decision"}.get(x["table"], ""), "why": why,
            "in_focus": in_focus, "excluded": excluded}


def focus_filter(con, codes, focus_ids, excluded=(), confidential=False):
    """{items, documents, n, N, docs_n, docs_N}: the work items and documents linked to the focus. An item is in when it is a
    focus item, is linked to one (the links table), shares its workstream or milestone, or is cited in the same minutes, mail
    or Teams thread. A document is in when a focus item cites it or was raised again in it, or its name shares the focus's words.
    Each says why; an excluded one (ticked out) stays listed and isn't counted. A confidential meeting lists no documents."""
    codes = [c for c in codes if c and c != "_portfolio"] or list(codes)
    rows = _rows(con, codes)
    focus_ids = [i for i in focus_ids if i]
    focus_rows = [x for x in rows if x["id"] in focus_ids]
    milestones = [i for i in focus_ids if re.fullmatch(r"[A-Z][A-Z0-9]{2,6}-M-\d{3}", i)]
    focus_rows += [{"id": m, "project": codes[0], "milestone": m, "source": ""} for m in milestones]
    linked, ms_names = _links(con, focus_ids), _milestone_names(con, codes)
    items = []
    universe = _universe(rows, set(focus_ids))
    for x in universe:
        why = ["in focus"] if x["id"] in focus_ids else _why(x, focus_rows, linked, ms_names)
        if why:
            items.append(_item_out(x, why, x["id"] in focus_ids, x["id"] in excluded))
    items.sort(key=lambda i: (not i["in_focus"], i["due"] or "9999", i["id"]))
    docs = [] if confidential else _documents(codes, focus_rows, excluded)[0]
    # "n of N": N is only the items listed (Alan, 13-10-2026), n those not ticked out; the same for documents
    return {"items": items, "documents": docs, "n": sum(1 for i in items if not i["excluded"]), "N": len(items),
            "docs_n": sum(1 for d in docs if not d["excluded"]), "docs_N": len(docs)}


def _cited_docs(focus_rows):
    """{path: [why]}: the meeting files the focus items come from, or were raised again in."""
    found = {}
    for f in focus_rows:
        sk = source_key(f.get("source"))
        if sk and sk[0] == "file":
            found.setdefault(sk[1], []).append(f"{f['id']} comes from it")
    for m in _mentions({f["id"] for f in focus_rows}):
        head = str(m.get("source") or "").split(" — ")[0]
        if "/" in head:
            found.setdefault(head, []).append(f"{m['id']} was raised again in it")
    return found


def _project_files(code):
    """A project's documents and meeting files; [] when it has no folders."""
    try:
        return paths.document_files(code) + [p for d in paths.extract_dirs(code) if d.is_dir() for p in sorted(d.iterdir())]
    except (LookupError, ValueError, OSError):  # a project without folders has no documents
        return []


def _documents(codes, focus_rows, excluded):
    """(documents linked to the focus, how many documents and meeting files the projects hold)."""
    found = _cited_docs(focus_rows)
    words = set().union(*[_words(f.get("text")) for f in focus_rows]) if focus_rows else set()
    total = 0
    for c in codes:
        files = _project_files(c)
        total += len(files)
        for p in files:
            shared = words & _words(paths.name_date(p.name)[1] or p.stem)
            if len(shared) >= 2 or (shared and len(words) <= 2):
                found.setdefault(paths.rel(p), []).append("its name shares " + ", ".join(f"“{w}”" for w in sorted(shared)[:2]))
    docs = [{"path": k, "name": Path(k).name, "why": list(dict.fromkeys(v)), "excluded": k in excluded} for k, v in found.items()]
    return sorted(docs, key=lambda d: d["path"]), max(total, len(docs))


STOP = set("the a an and or of to for in on at by with from is are was were be it this that as into not no will can our we "
           "you they their its about over under than then".split())


def _words(text):
    return {w for w in re.findall(r"[a-z][a-z0-9]+", str(text or "").lower()) if len(w) > 3 and w not in STOP}


def _mentions(ids):
    """mentions.jsonl lines for these IDs (an open item raised again in a later meeting or sweep)."""
    out = []
    try:
        lines = paths.MENTIONS.read_text(encoding="utf-8").splitlines() if paths.MENTIONS.exists() else []
    except OSError:
        lines = []
    for ln in lines:
        try:
            m = json.loads(ln)
        except ValueError:  # a damaged line is skipped; the others still count
            continue
        if m.get("id") in ids:
            out.append(m)
    return out


def focus_ids(reading, instruction=""):
    """The item IDs in a reading's focus (else those named in the instruction), in order, without repeats."""
    ids = [f.get("id") for f in (reading or {}).get("focus") or [] if isinstance(f, dict) and f.get("id")]
    return list(dict.fromkeys(ids or ID_RE.findall(instruction or "")))


def filter_for(key):
    """{ok, filter} for a meeting: focus_filter on its accepted focus (prep-focus.json), or {ok: False, message}."""
    import prep_page
    ctx = prep_page.context(key)
    if ctx.get("error"):
        return {"ok": False, "message": ctx["error"]}
    rec = get(canonical(key, ctx["day"])) or {}
    con = ro()
    try:
        f = focus_filter(con, (ctx.get("research") or {}).get("codes") or [ctx["project"]],
                         focus_ids(rec.get("reading"), rec.get("instruction")), set(rec.get("excluded") or []),
                         bool(ctx["meeting"].get("confidential")))
    finally:
        con.close()
    return {"ok": True, "filter": f, "show": ((rec.get("reading") or {}).get("show")) or "focus-first"}


# ── the shaping prompt's sources ─────────────────────────────────────────────

def _src(kind, text, link=None, item_id=None):
    return {"id": item_id or "", "kind": kind, "text": short(text, 400), "link": link or {"type": "text", "label": short(text, 120)}}


def _item_line(i, day):
    late = " (overdue)" if i.get("due") and i["due"] < day and i["table"] != "decisions" else ""
    bits = [i.get("type") or "", i.get("owner") or "", f"due {shown(i['due'])}{late}" if i.get("due") else "", i.get("status") or ""]
    return f"{i['id']}: {i['text']} ({', '.join(b for b in bits if b)})"


def _context_sources(ctx, conf, rank):
    """The invite (unless confidential), the listed items (the ones the invite ranks first) and the carried points."""
    day, out = ctx["day"], []
    body = (ctx.get("meeting") or {}).get("body") or ""
    if body and not conf:
        out.append(_src("invite", f"The invite says: {short(body, 600)}", {"type": "invite", "label": "The invite"}))
    ranked = set() if conf else {i for ids in (rank or {}).values() for i in ids}
    for i in sorted(ctx.get("items") or [], key=lambda x: x["id"] not in ranked):
        why = f" The invite: {i['why']}." if i.get("why") and not conf else ""
        out.append(_src("item", _item_line(i, day) + why, {"type": "item", "id": i["id"], "label": i["id"]}, i["id"]))
    return out + ([] if conf else _carried_sources(ctx))


def _carried_sources(ctx):
    """What wasn't covered last time, one source each."""
    return [_src("carried", f"Not covered at {c.get('title') or 'the last meeting'} on {shown(c.get('day'))}: {c['point']}",
                 {"type": "carried", "label": f"Minutes {shown(c.get('day'))}"}) for c in ctx.get("carried") or []]


def _focus_sources(con, ctx, conf, instruction, reading, have):
    """The items and documents linked to the focus named in the reading (or the instruction), not already listed."""
    import prep_view
    f = focus_filter(con, (ctx.get("research") or {}).get("codes") or [ctx["project"]], focus_ids(reading, instruction),
                     confidential=conf)
    out = [_src("item", f"{_item_line(i, ctx['day'])}; linked to the focus: {'; '.join(i['why'][:2])}",
                {"type": "item", "id": i["id"], "label": i["id"]}, i["id"]) for i in f["items"] if i["id"] not in have]
    out += [_src("document", f"Document {d['path']}: {'; '.join(d['why'][:2])}", prep_view.typed(d["path"])) for d in f["documents"][:6]]
    return out


def shape_sources(con, ctx, instruction, reading=None, rank=None):
    """The shaping prompt's sources, each {id, kind, text, link}: Alan's instruction, then (unless confidential) the invite, the
    items it ranks, the listed (urgent, overdue, due-soon) items, what wasn't covered last time, the items and documents linked
    to the focus, milestones due and the latest minutes. A confidential meeting: the instruction and tracker items only."""
    import prep_view
    conf = bool((ctx.get("meeting") or {}).get("confidential"))
    out = [_src("instruction", f"Alan's instruction: {instruction}", {"type": "alan", "label": "Your instruction"})]
    out += _context_sources(ctx, conf, rank)
    out += _focus_sources(con, ctx, conf, instruction, reading, {s["id"] for s in out if s["id"]})
    out += [_src("milestone", f"Milestone {c['insert']}", {"type": "item", "id": c["id"], "label": c["id"]}, c["id"])
            for c in milestone_chips(con, ctx)]
    research = [] if conf else ((ctx.get("research") or {}).get("minutes_and_transcripts") or [])[:3]
    out += [_src("file", f"Meeting record {p}", prep_view.typed(p)) for p in research]
    return out[:MAX_SOURCES]


# ── the stored focus ─────────────────────────────────────────────────────────

def load():
    """prep-focus.json's meetings, {} when there are none or it can't be read."""
    try:
        data = json.loads(FOCUS.read_text(encoding="utf-8"))
        return data.get("meetings") or {} if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def get(mid):
    """One meeting's stored focus record, or None."""
    return load().get(mid)


def _write(meetings):
    FOCUS.parent.mkdir(parents=True, exist_ok=True)
    tmp = FOCUS.with_suffix(".tmp")
    tmp.write_text(json.dumps({"version": 1, "meetings": meetings}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(FOCUS)


def _clean_line(x):
    """A note line as stored: its text (cut) and its typed sources (known keys only)."""
    if isinstance(x, str):
        x = {"text": x}
    if not isinstance(x, dict) or not str(x.get("text") or "").strip():
        return None
    keep = ("type", "label", "id", "path", "url")
    srcs = [{k: str(s[k])[:400] for k in keep if s.get(k)} for s in x.get("sources") or [] if isinstance(s, dict)][:6]
    return {"text": str(x["text"]).strip()[:LIMITS["line"]], "sources": srcs}


def clean_notes(notes):
    """Notes as stored: the four sections only, each a list of at most 12 lines."""
    notes = notes if isinstance(notes, dict) else {}
    out = {}
    for s in SECTIONS:
        lines = notes.get(s) if isinstance(notes.get(s), list) else []
        out[s] = [ln for ln in (_clean_line(x) for x in lines[:LIMITS["lines"]]) if ln]
    return out


def clean_reading(reading):
    """A reading as stored: focus entries ({id?, text}), the aim and what to show."""
    r = reading if isinstance(reading, dict) else {}
    focus = []
    for f in (r.get("focus") or [])[:LIMITS["focus"]]:
        f = {"text": f} if isinstance(f, str) else f if isinstance(f, dict) else {}
        text, fid = str(f.get("text") or "").strip()[:200], str(f.get("id") or "")
        if text or ID_RE.fullmatch(fid):
            focus.append({**({"id": fid} if ID_RE.fullmatch(fid) else {}), "text": text or fid})
    show = r.get("show") if r.get("show") in SHOW else "focus-first"
    return {"focus": focus, "aim": str(r.get("aim") or "").strip()[:LIMITS["aim"]], "show": show}


def _text_of(lines):
    return "\n".join(re.sub(r"\s+", " ", ln.get("text") or "").strip() for ln in lines or [])


def edited_sections(notes, drafted):
    """The sections whose text Alan changed from creaite's last draft."""
    return [s for s in SECTIONS if _text_of((notes or {}).get(s)) != _text_of((drafted or {}).get(s))]


def merge(new, current=None, clear=False):
    """(notes, kept): a regenerated draft merged with what Alan has. A section he edited keeps his text unless he clears it
    (clear: True for every section, or a list of sections); the others take the new draft."""
    current = current or {}
    edited = set(current.get("edited") or edited_sections(current.get("notes"), current.get("drafted"))) \
        if current.get("notes") else set()
    if clear is True:
        edited = set()
    elif isinstance(clear, list):
        edited -= set(clear)
    notes = {s: (current["notes"].get(s) or []) if s in edited else (new or {}).get(s) or [] for s in SECTIONS}
    return notes, sorted(edited, key=SECTIONS.index)


def _apply(rec, payload):
    """Copy what the payload gives (instruction, reading, drafted, notes, excluded) into the record, cleaned."""
    cleaners = {"instruction": lambda v: str(v or "")[:LIMITS["instruction"]], "reading": clean_reading, "drafted": clean_notes,
                "notes": clean_notes,
                "excluded": lambda v: [str(x)[:300] for x in (v or [])[:LIMITS["excluded"]] if isinstance(x, str)]}
    for k, fn in cleaners.items():
        if k in payload:
            rec[k] = fn(payload.get(k))
    if "questions" in payload:          # BL-286 D: Alan's questions and asks, edited on the prep page; null gives back the research's
        if payload["questions"] is None:
            rec.pop("questions", None)
        else:
            rec["questions"] = clean_questions(payload["questions"])
    return rec


def clean_questions(v):
    """Alan's questions and asks: plain text, one each, blank ones dropped (at most 12, 600 characters each)."""
    out = [re.sub(r"\s+", " ", x).strip()[:LIMITS["line"]] for x in (v if isinstance(v, list) else []) if isinstance(x, str)]
    return [x for x in out if x][:LIMITS["questions"]]


def save(key, day, payload, meeting=None):
    """Store a meeting's focus (Accept, or an edit in place). The edited sections are worked out against creaite's draft.
    Returns (record, event): event is "used" or "edited" on Accept (for draft-stats.json), else None."""
    mid = canonical(key, day)
    meetings = load()
    rec = dict(meetings.get(mid) or {})
    m = meeting or {}
    rec.update({"key": key, "title": m.get("title") or rec.get("title") or mid.split("|")[-1], "day": day,
                "start": m.get("start") or rec.get("start") or mid.split("|")[1]})
    _apply(rec, payload)
    rec["edited"] = (edited_sections(rec.get("notes"), rec.get("drafted")) if rec.get("drafted")
                     else list(SECTIONS) if rec.get("notes") else [])   # questions saved before any shaping mark no section
    rec["updated_at"] = now().strftime("%Y-%m-%d %H:%M")
    event = None
    if payload.get("accept"):
        rec["accepted_at"] = rec["updated_at"]
        event = "edited" if rec["edited"] else "used"
    meetings[mid] = rec
    _write(meetings)
    return rec, event


def forget(key, day):
    """Remove a meeting's stored focus (Clear on the page). True when there was one."""
    meetings = load()
    hit = meetings.pop(canonical(key, day), None)
    if hit is not None:
        _write(meetings)
    return hit is not None


# ── the shaping reply: its reading, its notes, and the checks ────────────────
# The reply (system/templates/drafts/shape.md) is plain text under fixed headings: FOCUS, AIM and SHOW (the reading), then
# OBJECTIVE, TALKING POINTS, ASK and CARRIED OVER (the notes), one "- " line each, every line ending with its [S…] tags.

HEADING = re.compile(r"^\s*(?:#+\s*)?\**([A-Z][A-Z ]{1,28}?)\**\s*:\s*(.*)$")
READING_HEADS = ("FOCUS", "AIM", "SHOW")
NOTE_HEADS = {v: k for k, v in HEADS.items()}
TAGS = re.compile(r"\s*\[(S\d+(?:\s*,\s*S\d+)*)\]")
NONE_LINE = re.compile(r"^\(?(none|nothing|n/a)\)?\.?$", re.I)


def split_reply(reply):
    """({heading: [lines]}, stray lines, unknown headings): the reply's text under each heading, in order."""
    parts, stray, unknown, cur = {}, [], [], None
    for raw in (reply or "").splitlines():
        m = HEADING.match(raw)
        if m and not raw.lstrip().startswith(("-", "*", "•")):
            cur = m.group(1).strip()
            if cur not in READING_HEADS + tuple(NOTE_HEADS) + ("READING", "NOTES", "SOURCES"):
                unknown.append(cur)
            parts.setdefault(cur, [])
            if m.group(2).strip():
                parts[cur].append(m.group(2).strip())
        elif raw.strip():
            (parts[cur] if cur else stray).append(raw.strip())
    return parts, stray, unknown


def _note_line(raw, by_ref):
    """One note line: its text without tags and bullet, its sources, and which tags didn't name a real source."""
    text = re.sub(r"^\s*[-*•]\s*", "", raw)
    refs = [r.strip() for m in TAGS.finditer(text) for r in m.group(1).split(",")]
    text = TAGS.sub("", text).strip()
    good = [r for r in dict.fromkeys(refs) if r in by_ref]
    return {"text": text, "refs": good, "bad": [r for r in refs if r not in by_ref],
            "sources": [by_ref[r]["link"] for r in good]}


def parse_reading(parts, known_ids):
    """(reading, checks): FOCUS split on ';' (IDs kept), AIM, SHOW (focus-only or focus-first)."""
    checks = []
    focus = []
    for bit in re.split(r"\s*;\s*", " ".join(parts.get("FOCUS") or [])):
        bit = TAGS.sub("", bit).strip(" .")
        if bit:
            ids = ID_RE.findall(bit)
            focus.append({**({"id": ids[0]} if ids else {}), "text": bit})
            checks += [_check("error", "Focus", f"{i} isn't in your project record.") for i in ids if i not in known_ids]
    aim = TAGS.sub("", " ".join(parts.get("AIM") or [])).strip()
    show_raw = " ".join(parts.get("SHOW") or []).strip().lower()
    show = "focus-only" if "only" in show_raw else "focus-first" if "first" in show_raw else None
    if not focus:
        checks.append(_check("error", "Focus", "The reply doesn't say what it read as the focus."))
    if not aim:
        checks.append(_check("error", "Aim", "The reply doesn't say what it read as the aim."))
    if not show:
        checks.append(_check("warn", "Show", "The reply doesn't say focus only or focus first; focus first is used."))
    return {"focus": focus, "aim": aim, "show": show or "focus-first"}, checks


def _check(level, section, note):
    return {"level": level, "section": section, "note": note}


def parse_notes(parts, sources):
    """(notes, checks): each note section's lines with their sources. A line with no real source is an error; so is a missing
    Objective. Ask and Talking points missing are warnings; Carried over may be empty."""
    by_ref = {s["ref"]: s for s in sources}
    notes, checks = {}, []
    for head, sec in NOTE_HEADS.items():
        lines = [ln for ln in parts.get(head) or [] if not NONE_LINE.match(re.sub(r"^\s*[-*•]\s*", "", ln))]
        got = [_note_line(ln, by_ref) for ln in lines]
        name = head.capitalize()
        for n, ln in enumerate(got, 1):
            if ln["bad"]:
                checks.append(_check("error", name, f"Line {n} cites {', '.join(ln['bad'])}, which isn't a source."))
            elif not ln["refs"]:
                checks.append(_check("error", name, f"Line {n} cites no source."))
        notes[sec] = [{"text": ln["text"], "sources": ln["sources"], "refs": ln["refs"]} for ln in got if ln["text"]]
        if head not in parts and sec != "carried_over":
            checks.append(_check("error" if sec == "objective" else "warn", name, f"The reply has no {name} section."))
    if not notes["objective"] and "OBJECTIVE" in parts:
        checks.append(_check("error", "Objective", "The Objective is empty."))
    return notes, checks


def parse(reply, sources, known_ids, current=None, clear=False):
    """The shaping reply, parsed and checked: {reading, drafted, notes (merged with Alan's edits), kept, checks, ok}. A heading
    the format doesn't have, or text outside the headings, is reported and left out."""
    parts, stray, unknown = split_reply(reply)
    reading, checks = parse_reading(parts, set(known_ids))
    drafted, more = parse_notes(parts, sources)
    checks += more
    checks += [_check("error", h.capitalize(), f"{h.capitalize()} isn't a section of the notes; its lines are left out.")
               for h in unknown]
    if stray:
        checks.append(_check("warn", "", f"{len(stray)} line{'s' if len(stray) != 1 else ''} outside the sections, left out."))
    notes, kept = merge(drafted, current, clear)
    return {"reading": reading, "drafted": drafted, "notes": notes, "kept": kept, "checks": checks,
            "ok": not any(c["level"] == "error" for c in checks)}
