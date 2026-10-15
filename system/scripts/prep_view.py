"""creaite meeting prep, the page's content (BL-286 parts A and D). Standard library only.

  - typed(source): a source as a typed link (a vault file opens through /api/open; mail or Teams through its web link when the
    sweep kept one, plain text otherwise; a tracker item is its ID).
  - brief(key): the popup's data: the facts line since the last meeting, the series chip, and the organiser and invitees
    resolved to names through the people register.
  - dated_reporting(ctx), series(d, ctx, m): the context rail's latest reporting (always dated, with health) and the series timeline.
  - assemble(ctx, reply, focus, d, m): one model of the page, used by the in-app view and the Agendas file alike.
  - render_briefing(model): the Agendas HTML file in the Briefing layout (header, outline, centre, context rail).
  - store / load_content: the page's content (its context and Claude's reply) in system/staging/prep/, so the view shows it
    without running Claude again. regenerate(key): the Agendas file again, after the notes change (BL-98's rules kept).

The only writes are the server's own: system/staging/prep/*.json and the Agendas page (prep_page.save: never overwrites a file
creaite didn't write or one Alan edited; creaite's own is backed up first). Pages are Internal and never sent. Dates are
DD-MM-YYYY on screen; projects are named, never coded (BL-101).
"""
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
import prep_page  # noqa: E402
import prep_shape  # noqa: E402

CONTENT = paths.STAGING / "prep"
ID_RE = re.compile(r"[A-Z][A-Z0-9]{2,6}-(?:[A-Z]-)?\d{3}")
OPENABLE = re.compile(r"(projects|inbox|system/staging/drafts)/.+")
WEB = re.compile(r"https://[^\s<>\"']+")
ORDINAL = {1: "st", 2: "nd", 3: "rd"}
esc, shown = prep_page.esc, prep_page.shown


# ── typed sources ────────────────────────────────────────────────────────────

def _file_kind(path):
    ext = Path(path).suffix.lower().lstrip(".")
    return {"docx": "word", "doc": "word", "xlsx": "excel", "xls": "excel", "xlsm": "excel", "pdf": "pdf", "vtt": "transcript",
            "md": "text", "txt": "text", "html": "page"}.get(ext, "file")


def typed(src):
    """A source as a typed link: {type, label, …}. item: {id}; file: {path, kind} (opened through /api/open); mail or teams:
    {url} when the sweep kept an https link, else the label alone; tracker, invite, alan, carried or text: the label only."""
    s = re.sub(r"\s+", " ", str(src or "")).strip()
    if ID_RE.fullmatch(s):
        return {"type": "item", "id": s, "label": s}
    for kind, head in (("mail", "Email"), ("teams", "Teams")):
        if s.startswith(head):
            m = re.search(r"\s*·\s*Link:\s*(\S+)", s)
            out = {"type": kind, "label": prep_shape.short(s[:m.start()] if m else s, 200)}
            if m and WEB.fullmatch(m.group(1)):
                out["url"] = m.group(1)
            return out
    path = s.split(" — ")[0].strip()
    if OPENABLE.fullmatch(path) and ".." not in Path(path).parts:
        return {"type": "file", "kind": _file_kind(path), "path": path, "label": Path(path).name,
                **({"section": s.split(" — ", 1)[1][:80]} if " — " in s else {})}
    if s.lower().startswith("creaite tracker"):
        return {"type": "tracker", "label": s}
    return {"type": "text", "label": prep_shape.short(s, 200)}


# ── A: the facts line, the series chip, the people ──────────────────────────

def _plural(n, one, many=None):
    return f"{n} {one if n == 1 else (many or one + 's')}"


def since_counts(con, codes, since, day):
    """{decisions, risks, issues, overdue}: decisions made, risks and issues raised since `since`, and open actions that fell
    overdue between then and the meeting."""
    marks = ",".join("?" * len(codes))
    q = lambda sql, *a: con.execute(sql.format(m=marks), (*codes, *a)).fetchone()[0]   # noqa: E731
    return {"decisions": q("SELECT count(*) FROM decisions WHERE project IN ({m}) AND status = 'Made' AND date >= ? AND date <= ?",
                           since, day),
            "risks": q("SELECT count(*) FROM raid WHERE project IN ({m}) AND type = 'Risk' AND raised >= ?", since),
            "issues": q("SELECT count(*) FROM raid WHERE project IN ({m}) AND type = 'Issue' AND raised >= ?", since),
            "overdue": q("SELECT count(*) FROM actions WHERE project IN ({m}) AND status IN ('Open','Delayed') AND due_date >= ? "
                         "AND due_date < ?", since, day)}


def facts_text(counts, since, has_last, first):
    """'Since the last meeting (29-09-2026): 3 decisions, 1 new risk, 2 actions now overdue. 2 items the invite points to are
    shown first.'"""
    parts = [_plural(counts["decisions"], "decision")] if counts["decisions"] else []
    parts += [f"{counts['risks']} new risk{'s' if counts['risks'] != 1 else ''}"] if counts["risks"] else []
    parts += [f"{counts['issues']} new issue{'s' if counts['issues'] != 1 else ''}"] if counts["issues"] else []
    parts += [f"{_plural(counts['overdue'], 'action')} now overdue"] if counts["overdue"] else []
    head = f"Since the last meeting ({shown(since)})" if has_last else f"No earlier meeting on record; since {shown(since)}"
    text = f"{head}: {', '.join(parts) if parts else 'nothing new'}."
    if first:
        text += f" {_plural(first, 'item')} the invite points to {'is' if first == 1 else 'are'} shown first."
    return text


def ordinal(n):
    """1st, 2nd, 3rd, 4th… 11th, 12th, 13th, 21st."""
    return f"{n}{'th' if 10 <= n % 100 <= 20 else ORDINAL.get(n % 10, 'th')}"


def cadence(recurrence, days):
    """'Every week', 'Every 2 weeks', 'Every month'… from the invite's recurrence, else the usual gap between meetings; '' unsure."""
    r = str(recurrence or "").lower()
    word = {"daily": "Every day", "weekly": "Every week", "fortnightly": "Every 2 weeks", "biweekly": "Every 2 weeks",
            "monthly": "Every month"}
    for k, v in word.items():
        if k in r:
            return v
    m = re.search(r"every (\d+) weeks?", r)
    if m:
        return f"Every {m.group(1)} weeks" if m.group(1) != "1" else "Every week"
    from datetime import date
    gaps = sorted((date.fromisoformat(b) - date.fromisoformat(a)).days for a, b in zip(days, days[1:]))
    if not gaps:
        return ""
    g = gaps[len(gaps) // 2]
    return next((label for lo, hi, label in ((6, 8, "Every week"), (13, 15, "Every 2 weeks"), (20, 22, "Every 3 weeks"),
                                             (27, 35, "Every month")) if lo <= g <= hi), "")


def series_chip(s, recurrence):
    """{text, cadence, nth, last}: 'Every 2 weeks · 6th meeting · last 29-09-2026' (parts it can't tell are left out)."""
    past = sorted(x["day"] for x in s["meetings"] if not x.get("this"))
    every = cadence(recurrence, past)
    nth = len(past) + 1
    last = past[-1] if past else None
    bits = [every] if every else []
    bits += [f"{ordinal(nth)} meeting"] + ([f"last {shown(last)}"] if last else [])
    return {"text": " · ".join(bits), "cadence": every, "nth": nth, "last": last}


def _initials(name):
    words = [w for w in re.split(r"[\s.@_-]+", name) if w and w[0].isalpha()]
    return "".join(w[0].upper() for w in words[:2]) or "?"


def _person(raw, people, others, registered=False):
    """{name, initials, registered}: a name or address resolved through the people register. An address it doesn't know is
    shown as its own words (never the raw address), marked unregistered."""
    import propose
    raw = str(raw or "").strip()
    hit = propose.resolve_person(raw, people, others) if people and not registered else {"status": "known" if registered else ""}
    if hit.get("status") in ("known", "alias", "email"):
        name, known = hit.get("name") or raw, True
    elif "@" in raw:
        name, known = " ".join(w.capitalize() for w in re.split(r"[._-]+", raw.split("@")[0]) if w), False
    else:
        name, known = raw, False
    return {"name": name, "initials": _initials(name), "registered": known}


def _register():
    """(register people plus Alan, other names on items) for resolving; empty when the register can't be read."""
    import propose
    try:
        return propose.people_pool()
    except Exception:  # noqa: BLE001  names stay as the calendar gave them when the register can't be read
        return [], []


def _organiser(org, email, reg, others):
    """The organiser as a person: Alan himself (True), a name, or the address resolved; None when the invite gives none."""
    if org is True:
        me = (paths.load_settings().get("identity") or {}).get("name") or "You"
        return {"name": me, "initials": _initials(me), "registered": True, "you": True}
    raw = org if isinstance(org, str) and org else email
    return _person(raw, reg, others) if raw else None


def people(meeting, ev=None):
    """{organiser, invitees, count, confidential}: the invite's organiser and invitees as names (people register, BL-55). A
    confidential meeting kept no attendees, and says so."""
    reg, others = _register()
    meeting = meeting or {}
    organiser = _organiser(meeting.get("organiser"), (ev or {}).get("organiser_email"), reg, others)
    inv = [_person(a.get("name") or a.get("email"), reg, others) for a in meeting.get("attendees") or []
           if isinstance(a, dict) and (a.get("name") or a.get("email"))]
    return {"organiser": organiser, "invitees": inv, "count": len(inv), "confidential": bool(meeting.get("confidential"))}


def brief(key):
    """{ok, facts, series, people} for the Prep popup (BL-286 A), or {ok: False, message}."""
    d = prep_page._collect()
    with prep_page.using(d):
        ctx = prep_page.context(key)
    if ctx.get("error"):
        return {"ok": False, "message": ctx["error"]}
    m = prep_page.meeting_entry(d, key)
    s = series(d, ctx, m)
    return {"ok": True, "facts": facts(ctx, m), "series": series_chip(s, (m.get("invite") or {}).get("recurrence")),
            "people": people(ctx["meeting"], prep_page._event(key, ctx["day"]))}


def facts(ctx, m):
    """The facts line's numbers and words, for the popup and the page."""
    codes = (ctx.get("research") or {}).get("codes") or [ctx["project"]]
    since, has_last = (m.get("last") or ctx.get("since") or ctx["day"]), bool(m.get("last") or ctx.get("last"))
    first = 0 if ctx["meeting"].get("confidential") else sum(len(v) for v in (m.get("rank") or {}).values())
    con = prep_shape.ro()
    try:
        counts = since_counts(con, codes, since, ctx["day"])
    finally:
        con.close()
    return {**counts, "since": since, "has_last": has_last, "invite_first": first,
            "text": facts_text(counts, since, has_last, first)}


# ── D: dated reporting, the series ───────────────────────────────────────────

def _report_link(r):
    return {"kind": r["kind"], "date": r.get("date") or "", "date_shown": shown(r.get("date")), "name": r["name"],
            "online": bool(r.get("online")), **({} if r.get("online") else {"link": typed(r["path"])})}


def dated_reporting(ctx):
    """Per project: 'Weekly report · week ending DD-MM-YYYY · ▲ At risk', the headline, three points, and the latest weekly and
    client reports with their dates."""
    out = []
    for r in ctx.get("reporting") or []:
        up = r.get("update") or {}
        health = up.get("health") or r.get("health") or ""
        icon = prep_page.HEALTH_ICON.get(health, "●")
        line = (f"Weekly report · week ending {shown(up['week_ending'])}" if up.get("week_ending") else "No weekly report yet") + \
            (f" · {icon} {health}" if health else "")
        head, points, _ = prep_page.state_parts(r.get("current_state"), 3)
        reps = [x for x in ctx.get("reports") or [] if x.get("p") == r["project"]]
        latest = [next((x for x in reps if x["kind"] == k), None) for k in ("Weekly report", "Client report")]
        out.append({"project": r["project"], "name": r.get("name") or r["project"], "line": line, "health": health, "icon": icon,
                    "week_ending": up.get("week_ending"), "headline": head, "points": points,
                    "summary": prep_shape.short(up.get("summary") or r.get("health_reason"), 240),
                    "reports": [_report_link(x) for x in latest if x]})
    return out


def _series_days(d, name, day):
    """{day: {files, minutes}} of the earlier meetings of a series: filed minutes and transcripts, and processed.txt."""
    import build_dashboard as bd
    out = {}
    for f in d.get("files") or []:
        if f.get("f") not in ("minutes", "transcripts"):
            continue
        fd, title, _ = paths.name_date(f["n"])
        fd = f.get("date") or fd
        if not fd or fd >= day or bd.series_of(re.sub(r"^Quick note - ", "", title or "")) != name:
            continue
        rec = out.setdefault(fd, {"files": [], "minutes": None})
        rec["files"].append(f["path"])
        if f["f"] == "minutes" and not rec["minutes"]:
            rec["minutes"] = f["path"]
    for fd, ser in bd.past_meetings([]):
        if ser == name and fd < day:
            out.setdefault(fd, {"files": [], "minutes": None})
    return out


def raised_from(con, files):
    """{actions, decisions, raid}: the items whose source is one of these meeting files."""
    out = {}
    for table in ("actions", "decisions", "raid"):
        n = 0
        for p in files:
            n += con.execute(f"SELECT count(*) FROM {table} WHERE substr(source, 1, ?) = ?", (len(p), p)).fetchone()[0]
        out[table] = n
    return out


def not_covered(name, day):
    """The agenda points of that meeting that weren't covered: carried to the next (carried.json) or marked Not discussed in its
    minutes' Coverage (staged or applied proposals)."""
    import build_dashboard as bd
    import minutes
    pts = {minutes._norm_point(c["point"]) for c in minutes.carried_load() if c.get("series") == name and c.get("day") == day}
    for _, data in bd._hub_proposals():
        m = data["meeting"]
        if m.get("date") == day and bd.series_of(m.get("title") or "") == name:
            pts |= {minutes._norm_point(c.get("point")) for c in m.get("coverage") or [] if c.get("verdict") == "Not discussed"}
    return len(pts - {""})


def _prep_pages(name):
    """{day: the newest prep page creaite wrote for a meeting of the series}."""
    import build_dashboard as bd
    out = {}
    for rel, rec in sorted(prep_page._registry().items(), key=lambda kv: kv[1].get("at", "")):
        if bd.series_of(str(rec.get("key") or "").split("|")[-1]) == name:
            out[rec.get("day") or ""] = rel
    return out


def series(d, ctx, m, limit=8):
    """{series, meetings}: this meeting and the earlier ones of its series, newest first, each with its counts (actions,
    decisions and RAID items raised, points not covered) and links to its minutes and prep page."""
    import build_dashboard as bd
    name = m.get("series") or bd.series_of(ctx["meeting"]["title"])
    pages = _prep_pages(name)
    rows = [{"day": ctx["day"], "day_shown": shown(ctx["day"]), "this": True, "prep": pages.get(ctx["day"])}]
    con = prep_shape.ro()
    try:
        for day, rec in sorted(_series_days(d, name, ctx["day"]).items(), reverse=True)[:limit - 1]:
            rows.append({"day": day, "day_shown": shown(day), "this": False, "raised": raised_from(con, rec["files"]),
                         "not_covered": not_covered(name, day), "minutes": typed(rec["minutes"]) if rec["minutes"] else None,
                         "files": rec["files"], "prep": pages.get(day)})
    finally:
        con.close()
    return {"series": name, "meetings": rows}


# ── the page's one model ─────────────────────────────────────────────────────

def _work(ctx, reply, flt, show):
    """The work items table: the focus's items (only them, or them first) when a focus is accepted, else the listed items."""
    more = {k: str(v)[:200] for k, v in (reply.get("item_reasons") or {}).items() if isinstance(v, (str, int, float))}
    listed = [{**i, "why": [w for w in (i.get("why"), more.get(i["id"])) if w], "in_focus": False} for i in ctx.get("items") or []]
    if not flt:
        return {"mode": "all", "rows": listed, "not_listed": int(ctx.get("not_listed") or 0)}
    focus = [i for i in flt["items"] if not i["excluded"]]
    have = {i["id"] for i in focus}
    rows = focus if show == "focus-only" else focus + [i for i in listed if i["id"] not in have]
    return {"mode": show, "rows": rows, "n": flt["n"], "N": flt["N"], "docs_n": flt["docs_n"], "docs_N": flt["docs_N"],
            "documents": flt["documents"], "not_listed": int(ctx.get("not_listed") or 0)}


def _notes(reply):
    out = []
    for n in reply.get("notes") or []:
        if isinstance(n, dict) and str(n.get("text") or "").strip():
            out.append({"text": str(n["text"])[:300], "date": n.get("date") or "", "date_shown": shown(n.get("date")),
                        "source": typed(str(n.get("source") or "")[:300]) if n.get("source") else None,
                        "source_text": str(n.get("source") or "no source given")[:300]})
    return out


def _found_sources(model):
    """Every source the page cites, in order, repeats included."""
    lines = [ln for s in ((model.get("focus") or {}).get("notes") or {}).values() for ln in s]
    found = [n["source"] for n in model["notes"] if n.get("source")] + [s for ln in lines for s in ln.get("sources") or []]
    found += [r["link"] for p in model["reporting"] for r in p["reports"] if r.get("link")]
    found.append({"type": "tracker", "label": "creaite tracker (actions, risks and issues, decisions, updates)"})
    if not model["meeting"]["confidential"]:
        found.append({"type": "invite", "label": f"Invite: {model['meeting']['title']} ({shown(model['meeting']['day'])})"})
    return found


def _all_sources(model):
    """The page's sources as typed links, each once."""
    seen, out = set(), []
    for s in _found_sources(model):
        k = (s.get("type"), s.get("path") or s.get("url") or s.get("id") or s.get("label"))
        if k not in seen:
            seen.add(k)
            out.append(s)
    return out


def _meeting(ctx):
    mt = ctx["meeting"]
    allp = ctx["project"] == "_portfolio"
    return {"title": mt["title"], "day": ctx["day"], "day_shown": shown(ctx["day"]), "start": mt.get("start", ""),
            "end": mt.get("end", ""), "where": mt.get("where", ""), "confidential": bool(mt.get("confidential")),
            "project": ctx["project"], "project_name": "Portfolio" if allp else ctx.get("project_name") or "",
            "body": "" if mt.get("confidential") else mt.get("body", "")}


def _filter(ctx, focus):
    """The focus filter for an accepted focus, or None when there is none."""
    if not focus or not (focus.get("reading") or focus.get("instruction")):
        return None
    con = prep_shape.ro()
    try:
        return prep_shape.focus_filter(con, (ctx.get("research") or {}).get("codes") or [ctx["project"]],
                                       prep_shape.focus_ids(focus.get("reading"), focus.get("instruction")),
                                       set(focus.get("excluded") or []), bool(ctx["meeting"].get("confidential")))
    finally:
        con.close()


def _questions(reply, focus=None):
    """Alan's edited questions and asks (prep-focus.json, BL-286 D) when he has some, else the research's."""
    if "questions" in (focus or {}):
        return list(focus["questions"])
    return [q[:300] for q in reply.get("questions") or [] if isinstance(q, str) and q.strip()][:5]


def assemble(ctx, reply, focus=None, d=None, m=None):
    """The page's model: the meeting, the accepted focus and its filter, the work items, Claude's notes and questions, dated
    reporting, the series and every source as a typed link. The in-app view and the Agendas file are both made from it."""
    reply, m = prep_page.hold_confidential(reply or {})[0], m or {}      # BL-301: never a confidential note's finding or words
    show = ((focus or {}).get("reading") or {}).get("show") or "focus-first"
    model = {"id": prep_shape.canonical(ctx["key"], ctx["day"]), "key": ctx["key"], "internal": True, "meeting": _meeting(ctx),
             "port": ctx.get("port", 8765), "focus": focus, "work": _work(ctx, reply, _filter(ctx, focus), show),
             "about": str(reply.get("about") or "").strip(), "notes": _notes(reply), "m365": str(reply.get("m365") or ""),
             "questions": _questions(reply, focus), "questions_edited": "questions" in (focus or {}),
             "carried": ctx.get("carried") or [], "reporting": dated_reporting(ctx),
             "reporting_raw": ctx.get("reporting") or [], "reports": ctx.get("reports") or []}
    model["series"] = series(d, ctx, m) if d is not None else {"series": "", "meetings": []}
    model["sources"] = _all_sources(model)
    model["outline"] = ["Focus and notes", "Work items", "Researched notes", "Questions and asks", "Latest reporting", "Sources",
                        "This series"]
    return model


# ── the stored content ───────────────────────────────────────────────────────

def content_path(mid):
    """system/staging/prep/<YYYY-MM-DD HHMM> <hash>.json for a meeting ID (the title's hash: any title is a safe name)."""
    day, start = (mid.split("|") + ["", ""])[:2]
    return CONTENT / f"{day} {start.replace(':', '')} {hashlib.sha256(mid.encode('utf-8')).hexdigest()[:12]}.json"


def store(ctx, reply, page=None):
    """Keep a page's content (its context and Claude's reply), beside prep-pages.json: the server's own write."""
    mid = prep_shape.canonical(ctx["key"], ctx["day"])
    rec = {"id": mid, "key": ctx["key"], "day": ctx["day"], "title": ctx["meeting"]["title"], "project": ctx["project"],
           "built_at": prep_page.now().strftime("%Y-%m-%d %H:%M"), "page": page, "context": ctx, "reply": reply or {}}
    CONTENT.mkdir(parents=True, exist_ok=True)
    target = content_path(mid)
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(target)
    return rec


def load_content(mid):
    """A meeting's stored content, or None."""
    try:
        rec = json.loads(content_path(mid).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return rec if rec.get("id") == mid else None


def page_for(ctx, reply, d=None):
    """The Agendas HTML for a context and reply, with the meeting's accepted focus (the Briefing layout)."""
    d = d if d is not None else _data()
    m = prep_page.meeting_entry(d, ctx["key"]) if d else {}
    focus = prep_shape.get(prep_shape.canonical(ctx["key"], ctx["day"]))
    return render_briefing(assemble(ctx, reply, focus, d, m))


def _data():
    try:
        return prep_page._collect()
    except (OSError, sqlite3.Error, ValueError):   # without the dashboard data the page has no series, never no page
        return {}


def _resolve(key):
    """(ctx, reply, stored, d): the live context when the meeting is still in the calendar, else the stored one."""
    d = _data()
    with prep_page.using(d):
        ctx = prep_page.context(key)
    if ctx.get("error"):
        mid = key if len(key.split("|")) >= 3 else prep_shape.canonical(key, prep_page.now().date().isoformat())
        stored = load_content(mid)
        return (stored["context"], stored["reply"], stored, d) if stored else (ctx, {}, None, d)
    stored = load_content(prep_shape.canonical(key, ctx["day"]))
    return ctx, (stored or {}).get("reply") or {}, stored, d


def view(key):
    """{ok, model, stored, saved, live} for the in-app prep page (Meetings › Prep), or {ok: False, message}. Claude is never run."""
    ctx, reply, stored, d = _resolve(key)
    if ctx.get("error"):
        return {"ok": False, "message": ctx["error"]}
    m = prep_page.meeting_entry(d, key)
    focus = prep_shape.get(prep_shape.canonical(ctx["key"], ctx["day"]))
    model = assemble(ctx, reply, focus, d, m)
    model["brief"] = {"series": series_chip(model["series"], (m.get("invite") or {}).get("recurrence")),
                      "people": people(ctx["meeting"], prep_page._event(ctx["key"], ctx["day"]))}
    saved = None
    if stored and stored.get("page"):
        saved = {"path": stored["page"], "at": stored.get("built_at"), "at_shown": shown(stored.get("built_at"))}
    return {"ok": True, "model": model, "stored": bool(stored), "saved": saved, "live": bool(m)}


def regenerate(key, day):
    """Render the Agendas file again from the stored content and the current focus; returns its vault path, or None when no
    page was built yet. BL-98's rules: creaite's own unchanged page is replaced after a backup; one Alan edited gets a number."""
    stored = load_content(prep_shape.canonical(key, day))
    if not stored or not stored.get("page"):
        return None
    ctx, d = stored["context"], _data()
    rel = prep_page.save(ctx, page_for(ctx, stored["reply"], d))
    stored["page"], stored["built_at"] = rel, prep_page.now().strftime("%Y-%m-%d %H:%M")
    target = content_path(stored["id"])
    target.write_text(json.dumps(stored, indent=1, ensure_ascii=False), encoding="utf-8")
    return rel


# ── the Agendas file: the Briefing layout ────────────────────────────────────

BRIEF_CSS = """
.top{max-width:1280px;margin:0 auto;padding:24px 16px 8px} .chips{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0 0}
.chip{font-size:12px;border:1px solid var(--line);border-radius:999px;padding:3px 9px;color:var(--muted);background:var(--card)}
.brief{display:grid;grid-template-columns:190px minmax(0,1fr) 300px;gap:20px;max-width:1280px;margin:0 auto;padding:0 16px 48px}
.brief main{max-width:none;margin:0;padding:0} .outline{position:sticky;top:12px;align-self:start;font-size:14px}
.outline a{display:block;padding:3px 0;text-decoration:none}
.outline h3{font-size:12px;color:var(--muted);text-transform:uppercase;margin:16px 0 4px}
.rail details{margin:0 0 14px} .band{border-left:4px solid var(--accent)} .band h3{font-size:14px;margin:12px 0 4px}
.tl{list-style:none;padding:0}
.tl li{border-left:2px solid var(--line);padding:0 0 10px 10px;margin:0} .tl li.this{border-color:var(--accent)}
td.why ul{margin:0;padding-left:16px} .open{font-size:12px}
@media (max-width:1000px){.brief{grid-template-columns:minmax(0,1fr)} .outline{position:static}}
@media print{.brief{display:block} .outline{display:none}}
"""


def item_href(item_id, port):
    """The dashboard address that opens a tracker item in Work (its table from the ID's letter, its project from the prefix)."""
    m = re.fullmatch(r"([A-Z][A-Z0-9]{2,6})-(?:([A-Z])-)?\d{3}", item_id)
    table = {"A": "actions", "D": "decisions", "M": "milestones", "P": "promises"}.get(m.group(2) or "", "raid") if m else "actions"
    return f"http://127.0.0.1:{port}/#work={table}&p={m.group(1) if m else ''}&item={item_id}"


def _src_html(s, port):
    """One typed source as HTML: a file opens in the dashboard (#openfile), mail or Teams by its web link, an item in Work."""
    from urllib.parse import quote
    label = esc(s.get("label"))
    if s.get("type") == "file" and s.get("path"):
        return f'<a href="http://127.0.0.1:{port}/#openfile={esc(quote(s["path"], safe="/"))}">{label}</a>'
    if s.get("url"):
        return f'{label} <a class="open" href="{esc(s["url"])}">open ↗</a>'
    if s.get("type") == "item" and s.get("id"):
        return f'<a href="{esc(item_href(s["id"], port))}">{label}</a>'
    return label


def _head_html(mo):
    mt = mo["meeting"]
    when = f"{mt['day_shown']}, {mt['start']} – {mt['end']}"
    chips = [mt["project_name"]] + [((mo.get("brief") or {}).get("series") or {}).get("text") or ""]
    warn = ('<p class="warn">Confidential meeting: only its title and times were kept, so the invite wasn\'t read.</p>'
            if mt["confidential"] else "")
    m365 = mo.get("m365") or ""
    if m365 and not m365.startswith("searched"):
        warn += f'<p class="warn">Microsoft 365 wasn\'t searched ({esc(m365[:200])}); this page is built from the vault only.</p>'
    return (f'<header class="top"><span class="internal">Internal</span> <span class="src">Meeting prep for Alan · not for the '
            f'client · never sent</span><h1>{esc(mt["title"])}</h1><p class="meta">{esc(when)}'
            f'{" · " + esc(mt["where"]) if mt["where"] else ""}</p><div class="chips">'
            + "".join(f'<span class="chip">{esc(c)}</span>' for c in chips if c) + f"</div>{warn}</header>")


def _outline_html(mo):
    ids = ["focus", "work", "notes", "questions", "reporting", "sources", "series"]
    days = "".join(f'<a href="#series">{esc(x["day_shown"])}</a>' for x in mo["series"]["meetings"] if not x.get("this"))
    return ('<nav class="outline">' + "".join(f'<a href="#{i}">{esc(t)}</a>' for i, t in zip(ids, mo["outline"]))
            + (f"<h3>This series</h3>{days}" if days else "") + "</nav>")


def _line_html(ln, port):
    srcs = " · ".join(_src_html(s, port) for s in ln.get("sources") or [])
    return f"<li>{esc(ln['text'])}{f' <span class=src>— {srcs}</span>' if srcs else ''}</li>"


def _reading_html(reading):
    focus = "; ".join(x.get("text") or x.get("id") or "" for x in reading.get("focus") or [])
    return ((f"<p><strong>Focus:</strong> {esc(focus)}</p>" if focus else "")
            + (f"<p><strong>Aim:</strong> {esc(reading.get('aim'))}</p>" if reading.get("aim") else ""))


def _focus_html(mo, port):
    f = mo.get("focus") or {}
    reading, notes = f.get("reading") or {}, f.get("notes") or {}
    if not (reading or notes):
        return ""
    parts = [_reading_html(reading)]
    for sec in prep_shape.SECTIONS:
        if notes.get(sec):
            parts.append(f"<h3>{esc(prep_shape.HEADS[sec].capitalize())}</h3><ul>"
                         + "".join(_line_html(ln, port) for ln in notes[sec]) + "</ul>")
    stamp = f'<p class="src">Your notes, accepted {esc(shown(f.get("accepted_at")))}</p>' if f.get("accepted_at") else ""
    return f'<details open id="focus" class="band"><summary><h2>Focus and notes</h2></summary>{"".join(parts)}{stamp}</details>\n'


def _row_html(i, port):
    link = f"http://127.0.0.1:{port}/#work={i['table']}&p={i['p']}&item={i['id']}"
    why = i.get("why") or []
    why = why if isinstance(why, list) else [why]
    return (f'<tr><td><a href="{esc(link)}">{esc(i["id"])}</a></td><td>{esc(i["text"])}<br><span class="src">'
            f'{esc(i.get("type") or "")}</span></td><td>{esc(i.get("owner") or "")}</td><td>{esc(shown(i.get("due")))}</td>'
            f'<td class="why">{esc("; ".join(w for w in why if w))}</td></tr>')


def _work_html(mo, port):
    w, code = mo["work"], mo["meeting"]["project"]
    rows = "".join(_row_html(i, port) for i in w["rows"])
    title = f"Work items in focus · {w['n']} of {w['N']}" if w["mode"] != "all" else "Work items"
    body = (f"<table><thead><tr><th>ID</th><th>Item</th><th>Owner</th><th>Due</th><th>Why it's here</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>") if rows else '<p class="empty">Nothing is Urgent, overdue or due soon.</p>'
    n = w["not_listed"]
    if n and w["mode"] == "all":
        work = f"http://127.0.0.1:{port}/#work=actions" + ("" if code == "_portfolio" else f"&p={esc(code)}")
        body += (f'<p class="src">{n} other open item{"s are" if n != 1 else " is"} not listed. '
                 f'<a href="{work}">Show {"them" if n != 1 else "it"} in Work</a>.</p>')
    if w.get("documents"):
        docs = "".join(f'<li>{_src_html(typed(d["path"]), port)} <span class="src">{esc("; ".join(d["why"]))}</span></li>'
                       for d in w["documents"] if not d["excluded"])
        body += f"<h3>Documents in focus · {w['docs_n']} of {w['docs_N']}</h3><ul>{docs}</ul>"
    return f'<details open id="work"><summary><h2>{esc(title)}</h2></summary>{body}</details>\n'


def _notes_html(mo, port):
    lis = []
    for n in mo["notes"]:
        src = esc(n["source_text"]) + (f' {_src_html(n["source"], port)}' if n.get("source") and n["source"].get("type") == "file"
                                       else f' <a class="open" href="{esc(n["source"]["url"])}">open ↗</a>'
                                       if (n.get("source") or {}).get("url") else "")
        doc = prep_page.DOC_TAG if "documents" in n["source_text"].lower() else ""
        lis.append(f'<li>{esc(n["text"])} <span class="src">— {src}{", " + esc(n["date_shown"]) if n["date"] else ""}</span>{doc}</li>')
    body = f"<ul>{''.join(lis)}</ul>" if lis else '<p class="empty">Nothing found.</p>'
    qs = ("<ul>" + "".join(f"<li>{esc(q)}</li>" for q in mo["questions"]) + "</ul>") if mo["questions"] else \
        '<p class="empty">Nothing found.</p>'
    about = f"<p>{esc(mo['about'])}</p>" if mo["about"] else '<p class="empty">Nothing found.</p>'
    return (f'<details open><summary><h2>What this meeting is about</h2></summary>{about}</details>\n'
            f'{prep_page.carried_html({"carried": mo["carried"]})}'
            f'<details open id="notes"><summary><h2>Researched notes</h2></summary>{body}</details>\n'
            f'<details open id="questions"><summary><h2>Questions and asks</h2></summary>{qs}</details>\n')


def _reporting_html(mo, port):
    allp = mo["meeting"]["project"] == "_portfolio"
    parts = []
    for r, raw in zip(mo["reporting"], mo["reporting_raw"]):
        reps = "".join(f'<li>{esc(x["kind"])} · {esc(x["date_shown"])} · '
                       + (f'{esc(x["name"])} — unavailable: the file is online-only' if x["online"] else _src_html(x["link"], port))
                       + "</li>" for x in r["reports"])
        parts.append(f'<p class="meta"><strong>{esc(r["line"])}</strong></p>{prep_page.reporting_html(raw, allp)}'
                     + (f'<ul class="reps">{reps}</ul>' if reps else ""))
    body = "".join(parts) or '<p class="empty">Nothing found.</p>'
    return f'<details open id="reporting"><summary><h2>Latest reporting</h2></summary><div class="rep">{body}</div></details>\n'


def _series_html(mo, port):
    lis = []
    for x in mo["series"]["meetings"]:
        if x.get("this"):
            lis.append(f'<li class="this"><strong>{esc(x["day_shown"])}</strong> · this meeting</li>')
            continue
        r = x.get("raised") or {}
        counts = (f'{r.get("actions", 0)} actions, {r.get("decisions", 0)} decisions raised · {x.get("not_covered", 0)} not covered')
        links = [_src_html(x["minutes"], port)] if x.get("minutes") else []
        links += [_src_html(typed(x["prep"]), port).replace(">" + esc(Path(x["prep"]).name) + "<", ">prep page<")] if x.get("prep") else []
        lis.append(f'<li><strong>{esc(x["day_shown"])}</strong> · {esc(counts)}<br>{" · ".join(links)}</li>')
    return f'<details open id="series"><summary><h2>This series</h2></summary><ul class="tl">{"".join(lis)}</ul></details>\n'


def _sources_html(mo, port):
    lis = "".join(f'<li class="src">{_src_html(s, port)}</li>' for s in mo["sources"])
    return f'<details open id="sources"><summary><h2>Sources</h2></summary><ul>{lis}</ul></details>\n'


def render_briefing(mo):
    """The Agendas file in the Briefing layout: one self-contained, Internal HTML file (no scripts, fonts or images), with a
    header, an outline, the centre (focus, work items, notes, questions) and the context rail (reporting, series, sources)."""
    port = mo.get("port", 8765)
    return f"""<!doctype html>
<!-- {prep_page.MARK} · Internal: Alan's meeting prep, not for the client. key={esc(mo['key'])} day={esc(mo['meeting']['day'])} -->
<html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="{prep_page.MARK}" content="{esc(mo['key'])}"><title>Prep · {esc(mo['meeting']['title'])}</title>
<style>{prep_page.CSS}{BRIEF_CSS}</style></head>
<body>{_head_html(mo)}
<div class="brief">{_outline_html(mo)}
<main>{_focus_html(mo, port)}{_work_html(mo, port)}{_notes_html(mo, port)}</main>
<aside class="rail">{_reporting_html(mo, port)}{_series_html(mo, port)}{_sources_html(mo, port)}</aside>
</div>
<footer class="top">Made by creaite on {esc(prep_page.now().strftime('%d-%m-%Y %H:%M'))}. Internal: for Alan's preparation only. Items and
report links open in the dashboard, which needs the live server to be running.</footer>
</body></html>
"""
