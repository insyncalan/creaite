"""creaite search — find anything in the vault (BL-07). Read-only: it never writes to the tracker or to staging
(only `enrich set` writes, and only to system/search/). Standard library only.

Commands:
  parse "<text>"                       what the text means: the filter chips it contains and the words left to search
  query "<text>" [--project CODE] [--person NAME] [--kind TYPE] [--from YYYY-MM-DD] [--to YYYY-MM-DD]
                [--skip kind:value ...] [--no-parse]
                                       grouped results as JSON (Items, Meetings, Reports, Documents, Notes; 20 each)
  preview <path> ["<text>"]            a vault file's text with the words highlighted, as JSON (used by the page)
  context "<question>" [filters as in query] [--json]
                                       what Ask should read first (BL-07): the best passages from the index, each with its
                                       surrounding paragraph, and the matching tracker rows, within search.ask_budget_chars.
                                       Gathered here, without Claude; --json adds the list of sources for the page's links

Query understanding is plain code, not AI. Each recognised word becomes a chip the page can remove:
  projects   a project code from the tracker ("ABC", "ORX2C")
  people     a name, alias or email from the people register (BL-55), and Alan's own name and short forms
  types      risk, issue, assumption, dependency, action, decision, milestone, minutes, transcript, report, document, note
  dates      today, yesterday, this/last week, this/last month, since DD-MM-YYYY, in September [2026], a date

Enrichment (BL-07), done once when a meeting or report is processed, never per search:
  enrich set --path <vault path> [--path …] --summary "<two lines>" --tags "tag, tag, …"
                                       write the summary (two lines) and three to eight topic tags for a filed meeting or
                                       report to system/search/<sha256 of the path>.json; `index` folds them into the index
  enrich --missing [--json]            the indexed meetings and reports that have no summary yet (a copy of the same
                                       meeting in another project counts), newest first, for cx-setup's one-off backfill

Set CREAITE_NOW="YYYY-MM-DD HH:MM" to fix the clock (tests).
"""
import hashlib
import html
import json
import os
import re
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import linktext  # noqa: E402  (#121: a link in item text is matched by its words)
import notes  # noqa: E402  (BL-301: a note's text and its confidential mark)
import paths  # noqa: E402
import propose  # noqa: E402  (the people register's reader; read only)
import tracker  # noqa: E402

GROUP_CAP = 20
GROUPS = ("items", "meetings", "reports", "documents", "notes")       # notes: BL-301
STOPWORDS = set("""a an the of to and or is are was were be been do does did has have had what why how when who whom which
where about for with on in at by from it this that there their his her its we you i me my our any all""".split())
# what a typed type word means: (group, stored kind or None for the whole group)
TYPE_WORDS = {
    "risk": ("items", "Risk"), "risks": ("items", "Risk"), "issue": ("items", "Issue"), "issues": ("items", "Issue"),
    "assumption": ("items", "Assumption"), "assumptions": ("items", "Assumption"),
    "dependency": ("items", "Dependency"), "dependencies": ("items", "Dependency"),
    "action": ("items", "action"), "actions": ("items", "action"),
    "decision": ("items", "decision"), "decisions": ("items", "decision"),
    "milestone": ("items", "milestone"), "milestones": ("items", "milestone"),
    "minutes": ("meetings", "minutes"), "transcript": ("meetings", "transcripts"),
    "transcripts": ("meetings", "transcripts"),
    "report": ("reports", "report"), "reports": ("reports", "report"),
    "document": ("documents", "documents"), "documents": ("documents", "documents"), "doc": ("documents", "documents"),
    "docs": ("documents", "documents"),
    "note": ("notes", "note"), "notes": ("notes", "note"),                 # BL-301
}
TYPE_LABEL = {"Risk": "Risks", "Issue": "Issues", "Assumption": "Assumptions", "Dependency": "Dependencies",
              "action": "Actions", "decision": "Decisions", "milestone": "Milestones", "minutes": "Minutes",
              "transcripts": "Transcripts", "report": "Reports", "documents": "Documents",
              "note": "Notes"}
MONTHS = {m: i for i, names in enumerate(
    ["january jan", "february feb", "march mar", "april apr", "may", "june jun", "july jul", "august aug",
     "september sep sept", "october oct", "november nov", "december dec"], 1) for m in names.split()}


def today():
    """Today's date, or CREAITE_NOW's date in tests."""
    now = os.environ.get("CREAITE_NOW")
    return date.fromisoformat(now[:10]) if now else date.today()


def settings():
    """The search settings (debounce, Ask's reading budget, whether documents are included), with defaults."""
    return {"debounce_ms": 150, "ask_budget_chars": 40000, "include_documents": True,
            **(paths.load_settings().get("search") or {})}


# ── Query understanding ───────────────────────────────────────────────────────

def vocabulary():
    """What the parser can recognise: project codes (the tracker's), and people (the register's, then Alan's)."""
    codes = {}
    if paths.DB.is_file():
        con = tracker.connect()
        codes = {r["code"].lower(): r["code"] for r in con.execute("SELECT code FROM projects")}
        con.close()
    people = propose.people_parse(paths.PEOPLE_REGISTER.read_text(encoding="utf-8")) \
        if paths.PEOPLE_REGISTER.is_file() else []
    ident = (paths.load_settings().get("identity") or {})
    if ident.get("name") and not any(propose.person_key(p["name"]) == propose.person_key(ident["name"]) for p in people):
        people.append({"name": ident["name"], "email": "", "aliases": [a for a in ident.get("short_forms") or []],
                       "org": "", "role": "", "hidden": False, "extra": {}})
    forms = {}                       # the written form (as keyed) -> the person's name
    for p in people:
        for f in [p["name"], *p["aliases"]]:
            k = propose.person_key(f)
            if k:
                forms.setdefault(k, (p["name"], f, len(k) < 3))   # a two-letter alias only counts when written in capitals
        for addr in [e.strip() for e in str(p.get("email") or "").split(",") if e.strip()]:   # several addresses (BL-99)
            forms.setdefault(addr.lower(), (p["name"], addr, False))
    return {"codes": codes, "people": people, "forms": forms}


def month_range(y, m):
    """(first day, last day) of month `m` of year `y`."""
    first = date(y, m, 1)
    nxt = date(y + (m == 12), m % 12 + 1, 1)
    return first, nxt - timedelta(days=1)


def shown(d):
    """A date as Alan reads it: DD-MM-YYYY."""
    return tracker.shown(d.isoformat() if isinstance(d, date) else d)


def date_chip(tokens, i, now):
    """A date phrase at tokens[i]: (chip, tokens used) or None."""
    w = tokens[i].lower().strip(",.")
    nxt = tokens[i + 1].lower().strip(",.") if i + 1 < len(tokens) else ""
    after = tokens[i + 2].strip(",.") if i + 2 < len(tokens) else ""

    def make(label, frm, to, n):
        """(a date chip from `frm` to `to`, the number of words it used)."""
        return ({"kind": "date", "value": f"{frm or ''}..{to or ''}", "from": frm, "to": to,
                 "label": label, "words": " ".join(tokens[i:i + n])}, n)
    if w == "today":
        return make("Today", now.isoformat(), now.isoformat(), 1)
    if w == "yesterday":
        y = (now - timedelta(days=1)).isoformat()
        return make("Yesterday", y, y, 1)
    if w in ("last", "this") and nxt in ("week", "month"):
        if nxt == "week":
            mon = now - timedelta(days=now.weekday()) - (timedelta(days=7) if w == "last" else timedelta(0))
            a, b = mon, mon + timedelta(days=6)
        else:
            y, m = (now.year, now.month) if w == "this" else ((now.year - (now.month == 1)), (now.month - 2) % 12 + 1)
            a, b = month_range(y, m)
        return make(f"{w.capitalize()} {nxt} ({shown(a)} to {shown(b)})", a.isoformat(), b.isoformat(), 2)
    if w == "since" and nxt:
        d = parse_date(tokens[i + 1])
        if d:
            return make(f"Since {shown(d)}", d.isoformat(), None, 2)
    if w == "in" and nxt in MONTHS:
        m = MONTHS[nxt]
        year = int(after) if re.fullmatch(r"(19|20)\d\d", after) else None
        y = year or (now.year if m <= now.month else now.year - 1)
        a, b = month_range(y, m)
        return make(f"{nxt.capitalize() if nxt not in ('sep', 'sept') else 'September'} {y}", a.isoformat(), b.isoformat(),
                    3 if year else 2)
    d = parse_date(tokens[i])
    if d:
        return make(shown(d), d.isoformat(), d.isoformat(), 1)
    return None


def parse_date(text):
    """A date typed as DD-MM-YYYY (or with / or .) or YYYY-MM-DD, or None."""
    t = text.strip(",.")
    m = re.fullmatch(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})", t) or None
    try:
        if m:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", t)
        if m:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None
    return None


def parse_query(text, vocab=None, now=None, skip=()):
    """{terms, chips}. Each chip: {kind: project|person|type|date, value, label, words} (+ from/to for dates). A chip whose
    "kind:value" is in skip (the user removed it) is left out and its words dropped."""
    vocab = vocab or vocabulary()
    now = now or today()
    tokens = [t for t in re.findall(r'"[^"]+"|\S+', text)]
    chips, terms, used, i = [], [], set(), 0
    seen_date = False
    while i < len(tokens):
        raw = tokens[i]
        clean = raw.strip('?!,;:()')
        low = clean.lower()
        if raw.startswith('"'):
            terms.append(raw.strip('"'))
            i += 1
            continue
        got = None
        if not seen_date:
            got = date_chip([t.strip('?!;:()') for t in tokens], i, now)
            if got:
                seen_date = True
        if got:
            chip, n = got
            if f"date:{chip['value']}" not in skip:
                chips.append(chip)
            i += n
            continue
        # people: the longest run of words that is a name, alias or email
        person = None
        for n in range(min(4, len(tokens) - i), 0, -1):
            span = " ".join(t.strip('?!,;:()') for t in tokens[i:i + n])
            key = propose.person_key(span) if "@" not in span else span.lower()
            if key in vocab["forms"] and (not vocab["forms"][key][2] or span == span.upper()) \
                    and not any(c["kind"] == "person" and c["value"] == vocab["forms"][key][0] for c in chips):
                person = (vocab["forms"][key][0], n, span)
                break
        if person:
            if f"person:{person[0]}" not in skip:
                chips.append({"kind": "person", "value": person[0], "label": person[0], "words": person[2]})
            i += person[1]
            continue
        if low in vocab["codes"] and re.fullmatch(r"[A-Za-z][A-Za-z0-9]{2,6}", clean):
            code = vocab["codes"][low]
            if f"project:{code}" not in skip and not any(c["kind"] == "project" and c["value"] == code for c in chips):
                chips.append({"kind": "project", "value": code, "label": code, "words": clean})
            i += 1
            continue
        if low in TYPE_WORDS:
            group, kind = TYPE_WORDS[low]
            if f"type:{kind}" not in skip and not any(c["value"] == kind for c in chips):
                chips.append({"kind": "type", "value": kind, "group": group, "label": TYPE_LABEL[kind], "words": clean})
            i += 1
            continue
        terms.append(clean)
        i += 1
    terms = [t for t in terms if t]
    content = [t for t in terms if t.lower() not in STOPWORDS]
    return {"terms": content or terms, "chips": chips}


# ── Searching ─────────────────────────────────────────────────────────────────

def like(term):
    """A SQL LIKE pattern matching `term` anywhere, with its wildcards escaped."""
    return "%" + term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def mark(text, terms, width=None):
    """HTML-escaped text with the search words in <mark>; with width, a window around the first match."""
    text = re.sub(r"\s+", " ", text or "").strip()
    pat = re.compile("|".join(re.escape(t) for t in sorted({t for t in terms if t}, key=len, reverse=True)), re.I) \
        if any(terms) else None
    if width and len(text) > width:
        m = pat.search(text) if pat else None
        start = max(0, (m.start() if m else 0) - width // 4)
        text = ("…" if start else "") + text[start:start + width] + ("…" if start + width < len(text) else "")
    if not pat:
        return html.escape(text)
    out, pos = [], 0
    for m in pat.finditer(text):
        out += [html.escape(text[pos:m.start()]), "<mark>", html.escape(m.group(0)), "</mark>"]
        pos = m.end()
    return "".join(out) + html.escape(text[pos:])


def owner_forms(vocab, name):
    """The lower-case forms a person's name is matched by: the name and their aliases of 3 letters or more (BL-55)."""
    p = next((p for p in vocab["people"] if p["name"] == name), None)
    forms = {name.lower()}
    if p:
        forms |= {a.lower() for a in p["aliases"] if len(a) >= 3}
    return sorted(forms)


def words_match(row, cols, terms, any_term):
    """True unless the row only matched through a link's address (#121): when a searched column holds `[words](address)`, the terms are
    checked again against the words alone. A row with no link in it matched on the SQL already and is kept as it is."""
    if not terms or not any(isinstance(row.get(c), str) and "](" in row[c] and linktext.has_link(row[c]) for c in cols):
        return True
    hay = [linktext.words(str(row.get(c) or "")).lower() for c in cols]
    found = [any(t.lower() in h for h in hay) for t in terms]
    return any(found) if any_term else all(found)


def item_rows(con, vocab, terms, flt, any_term=False):
    """Tracker items matching the words and filters, with plain SQL LIKE beside the index (nothing is copied into it)."""
    kinds = flt["kinds"]
    out = []
    specs = [("actions", "action", ["id", "description", "owner", "workstream", "latest_update"], "owner", "raised",
              "description"),
             ("raid", None, ["id", "description", "response_action", "owner", "workstream"], "owner", "raised", "description"),
             ("decisions", "decision", ["id", "decision", "made_by"], "made_by", "date", "decision"),
             ("milestones", "milestone", ["id", "name", "description"], None, "COALESCE(forecast_date, baseline_date)", "name")]
    for table, kind, cols, who, dcol, text in specs:
        if kinds is not None and not (kind in kinds or (table == "raid" and kinds & {"Risk", "Issue", "Assumption",
                                                                                      "Dependency"})):
            continue
        where, args = [], []
        likes = ["(" + " OR ".join(f"{c} LIKE ? ESCAPE '\\'" for c in cols) + ")" for _ in terms]
        if likes:
            where.append("(" + (" OR " if any_term else " AND ").join(likes) + ")")
            args += [like(t) for t in terms for _ in cols]
        if flt["project"]:
            where.append(f"project IN ({','.join('?' * len(flt['project']))})")
            args += flt["project"]
        if table == "raid" and kinds is not None and kinds & {"Risk", "Issue", "Assumption", "Dependency"}:
            want = sorted(kinds & {"Risk", "Issue", "Assumption", "Dependency"})
            where.append(f"type IN ({','.join('?' * len(want))})")
            args += want
        if flt["person"] and who:
            forms = [f for n in flt["person"] for f in owner_forms(vocab, n)]
            where.append("(" + " OR ".join([f"lower({who}) = ?"] * len(forms) +
                                           [f"lower({who}) LIKE ?"] * len(forms)) + ")")
            args += forms + [f"{f} (%" for f in forms]
        elif flt["person"]:
            continue                                # milestones have no owner
        if flt["from"]:
            where.append(f"{dcol} >= ?")
            args.append(flt["from"])
        if flt["to"]:
            where.append(f"{dcol} <= ?")
            args.append(flt["to"])
        sql = f"SELECT *, {dcol} AS _date FROM {table}" + (" WHERE " + " AND ".join(where) if where else "")
        found = (dict(r) for r in con.execute(sql + f" ORDER BY _date DESC, id LIMIT 400", args))
        out.extend((table, row, text) for row in found if words_match(row, cols, terms, any_term))   # #121: a link's address is never matched
    return out


def archived_projects(con):
    """BL-10: the codes of archived projects (empty on a database from before BL-09), so search can tell an archived
    project's item from one archived for its age."""
    try:
        return {r[0] for r in con.execute("SELECT code FROM main.projects WHERE archived = 1")}
    except sqlite3.Error:
        return set()


def item_opens(table, r, gone):
    """Where a tracker row's result opens: its table and ID, and whether it is archived, and by its project (BL-10)."""
    out = {"type": "item", "table": table, "id": r["id"]}
    if r.get("archived"):
        out["archived"] = True
        if r["project"] in gone:
            out["project_archived"] = True
    return out


def item_result(table, r, text, terms, gone=frozenset()):
    """One tracker row as a search result: its ID, kind, text, details and link. `gone`: the archived projects' codes; an
    archived item of one of them opens with project_archived (BL-10), one archived for its age without."""
    kind = {"actions": "action", "decisions": "decision", "milestones": "milestone"}.get(table) or (r.get("type") or "Risk").lower()
    meta = []
    if table == "actions":
        meta = [r["status"], r["owner"], f"due {tracker.shown(r['due_date'])}" if r["due_date"] else ""]
    elif table == "raid":
        meta = [r["type"], r["status"], r["owner"]]
    elif table == "decisions":
        meta = [f"made by {r['made_by']}" if r["made_by"] else ""]
    else:
        meta = [r["status"], f"forecast {tracker.shown(r['forecast_date'] or r['baseline_date'])}"]
    if r.get("archived"):                      # BL-09: an archived project's items are still found, marked Archived
        meta.append("Archived")
    opens = item_opens(table, r, gone)
    return {"group": "items", "kind": kind, "id": r["id"], "title": r[text], "snippet": mark(r[text], terms, 220),
            "archived": bool(r.get("archived")),
            "project": r["project"], "date": r["_date"] or "", "date_shown": tracker.shown(r["_date"]) if r["_date"] else "",
            "meta": " · ".join(x for x in meta if x), "opens": opens}


def fts_match(terms, vocab, person_names, any_term=False):
    """MATCH text for the words (the last as a prefix), and for any chosen person's name or alias."""
    parts = []
    if terms and any_term:
        parts.append(" OR ".join(tracker.fts_terms(t, prefix=True) for t in terms))
    elif terms:
        parts.append(tracker.fts_terms(" ".join(terms), prefix=True))
    if person_names:
        names = []
        for n in person_names:
            names += [n] + [a for a in next((p["aliases"] for p in vocab["people"] if p["name"] == n), []) if len(a) >= 3]
        parts.append("(" + " OR ".join('"' + x.replace('"', '""') + '"' for x in dict.fromkeys(names)) + ")")
    return " AND ".join(f"({p})" if len(parts) > 1 else p for p in parts)


FILE_GROUP = {"minutes": "meetings", "transcripts": "meetings", "report": "reports", "documents": "documents", "note": "notes"}
FILE_KIND = {"minutes": "minutes", "transcripts": "transcript", "report": "report", "documents": "document", "note": "note"}


def file_results(con, vocab, terms, flt, opts, any_term=False):
    """Meetings, reports, documents and notes from the full-text index matching the words and filters, grouped.
    `any_term` matches any word instead of every word.
    """
    want_groups = flt["groups"]
    where, args = [], []
    match = fts_match(terms, vocab, flt["person"], any_term)
    if match:
        where.append("vault_search MATCH ?")
        args.append(match)
    if flt["project"]:
        where.append("(" + " OR ".join("(' ' || project || ' ') LIKE ?" for _ in flt["project"]) + ")")
        args += [f"% {c} %" for c in flt["project"]]
    if flt["from"]:
        where.append("date >= ?")
        args.append(flt["from"])
    if flt["to"]:
        where.append("date <= ?")
        args.append(flt["to"])
    kinds = flt["file_kinds"]
    if kinds is not None:
        where.append(f"kind IN ({','.join('?' * len(kinds))})")
        args += sorted(kinds)
    if not opts["include_documents"]:
        where.append("kind != 'documents'")
    snip = "snippet(vault_search, 4, char(2), char(3), '…', 24)" if match else "substr(content, 1, 300)"
    sql = (f"SELECT path, project, kind, date, {snip} AS snip FROM vault_search" +
           (" WHERE " + " AND ".join(where) if where else "") +
           (" ORDER BY rank" if match else " ORDER BY date DESC") + " LIMIT 400")
    out = {"meetings": [], "reports": [], "documents": [], "notes": []}
    for r in con.execute(sql, args):
        group = FILE_GROUP.get(r["kind"])
        if group is None:                                 # a kind a later release indexes: left out until this one knows it
            continue
        if want_groups is not None and group not in want_groups:
            continue
        out[group].append(file_result(r, group, terms, match))
    return out


def file_result(r, group, terms, match):
    """One indexed file as a search result: its title, snippet (or, with no words to match, its summary), project, date and how it
    opens (meetings and notes in the preview, the rest in their own app)."""
    name = Path(r["path"]).stem
    text = (r["snip"] or "").replace(f"{name}\n", "", 1)
    if not match:                                   # no words to match: the summary says more than the first lines
        note = tracker.read_sidecar(r["path"])
        text = " ".join(note["summary"].splitlines()) if note and note.get("summary") else text
    body = html.escape(re.sub(r"\s+", " ", text)).replace("\x02", "<mark>").replace("\x03", "</mark>")
    return {"group": group, "kind": FILE_KIND[r["kind"]], "title": name, "snippet": body, "project": r["project"],
            "path": r["path"], "date": r["date"], "date_shown": tracker.shown(r["date"]) if r["date"] else "",
            "opens": {"type": "preview" if group in ("meetings", "notes") else "file", "path": r["path"], "q": " ".join(terms)}}


def understand(text, project=(), person=(), kind=(), frm=None, to=None, skip=(), parse=True, now=None, vocab=None):
    """The text and explicit filters as (terms, chips, flt): what to look for and how to narrow it."""
    vocab = vocab or vocabulary()
    parsed = parse_query(text, vocab, now, skip) if parse else {"terms": [t for t in re.findall(r'"[^"]+"|\S+', text)],
                                                                 "chips": []}
    chips = parsed["chips"]
    have = {(c["kind"], c["value"]) for c in chips}
    for code in project:
        if ("project", code) not in have and f"project:{code}" not in skip:
            chips.append({"kind": "project", "value": code, "label": code, "words": ""})
    for name in person:
        if ("person", name) not in have and f"person:{name}" not in skip:
            chips.append({"kind": "person", "value": name, "label": name, "words": ""})
    for k in kind:
        k = TYPE_WORDS.get(k.lower(), (None, k))[1]
        if k in TYPE_LABEL and ("type", k) not in have and f"type:{k}" not in skip:
            group = next(g for g, kk in TYPE_WORDS.values() if kk == k)
            chips.append({"kind": "type", "value": k, "group": group, "label": TYPE_LABEL[k], "words": ""})
    d = next((c for c in chips if c["kind"] == "date"), None)
    if (frm or to) and not d:
        label = f"{shown(frm)} to {shown(to)}" if frm and to else f"Since {shown(frm)}" if frm else f"Until {shown(to)}"
        chips.append({"kind": "date", "value": f"{frm or ''}..{to or ''}", "from": frm, "to": to, "label": label, "words": ""})
        d = chips[-1]
    types = [c for c in chips if c["kind"] == "type"]
    flt = {"project": [c["value"] for c in chips if c["kind"] == "project"],
           "person": [c["value"] for c in chips if c["kind"] == "person"],
           "from": d["from"] if d else None, "to": d["to"] if d else None,
           "kinds": {c["value"] for c in types} if types else None,
           "groups": {c["group"] for c in types} if types else None}
    flt["file_kinds"] = {c["value"] for c in types if c["group"] != "items"} if types else None
    return parsed["terms"], chips, flt


def search(text, project=(), person=(), kind=(), frm=None, to=None, skip=(), parse=True, refresh=True, now=None, hold=False):
    """Grouped results for the text and filters: {terms, chips, groups, totals, rebuilt}. Explicit filters (project,
    person, kind, from, to) are added as chips of their own. #60: `hold` leaves confidential notes out entirely."""
    vocab = vocabulary()
    terms, chips, flt = understand(text, project, person, kind, frm, to, skip, parse, now, vocab)
    out = {"q": text, "terms": terms, "chips": chips, "groups": {g: [] for g in GROUPS}, "totals": {g: 0 for g in GROUPS},
           "rebuilt": False}
    if not terms and not chips:
        return out
    opts = settings()
    if not paths.DB.is_file():
        return out
    con = tracker.connect()
    try:
        if refresh and tracker.index_state()[0]:
            tracker.build_index()
            out["rebuilt"] = True
        found = {g: [] for g in GROUPS}
        if flt["groups"] is None or "items" in flt["groups"]:
            gone = archived_projects(con)
            found["items"] = [item_result(t, r, x, terms, gone) for t, r, x in item_rows(con, vocab, terms, flt)]
            ids = [t.lower() for t in terms]
            found["items"].sort(key=lambda r: (r["id"].lower() not in ids,))      # an exact ID first; then newest (stable)
        if flt["groups"] is None or flt["groups"] - {"items"}:
            for g, rows in file_results(con, vocab, terms, flt, opts).items():
                found[g] = held_out(rows, hold)                                  # #60
    finally:
        con.close()
    for g in GROUPS:
        out["totals"][g] = len(found[g])
        out["groups"][g] = found[g][:GROUP_CAP]
    return out


# ── Preview ───────────────────────────────────────────────────────────────────

PREVIEW_LIMIT = 300_000


def indexed(rel):
    """The path, if it is a file the index covers (the page may preview nothing else)."""
    p = paths.resolve(rel).resolve()
    ok = {f.resolve() for f, _, _ in tracker.index_files()}
    return p if p in ok else None


def indexed_text(p):
    """The text of an indexed file as search shows it: a note's (BL-301) without its front matter, else tracker.text_of's."""
    return notes.index_text(p) if paths.is_note(p) else tracker.text_of(p)


def preview(rel, q=""):
    """A vault file's text with the search words highlighted, as a dict for the page (cut at PREVIEW_LIMIT)."""
    p = indexed(rel)
    if not p:
        return {"ok": False, "message": "That file isn't in the search index."}
    text = indexed_text(p)
    if not text.strip():
        return {"ok": True, "name": p.name, "html": "", "cut": False, "empty": True, "open": True}
    cut = len(text) > PREVIEW_LIMIT
    terms = [t.strip('?!,;:()"') for t in re.findall(r'"[^"]+"|\S+', q)]
    terms = [t for t in terms if t and t.lower() not in STOPWORDS]
    return {"ok": True, "name": p.name, "cut": cut, "empty": False, "open": False,
            "html": "".join(f"<p>{mark(line, terms)}</p>" for line in text[:PREVIEW_LIMIT].split("\n") if line.strip())}


# ===== #60 (Alan, 15-10-2026): a run creaite starts itself never sees a confidential note =====
# The live server starts every run of its own that may read files (Prep, Shape the meeting, Current state, the AI drafts,
# a transcript check or load, Close the day's sweep) with CREAITE_RUN_KIND=<its kind> (live_server.run_env), never ask
# creaite or Search's answer, and the guard hook lets a Bash call through only as one creaite script on its own, so the run
# can't change it. There,
# query leaves a confidential note out entirely (no title, link or match on its words: notes.held, fail closed) and preview answers
# as for a file the index doesn't hold. Everyone else's results are unchanged. (Option (a)'s title and link replaced: #60 follow-ups.)


def held_run():
    """Whether this command runs inside a run creaite started itself (set by the live server, never by the run or ask creaite)."""
    return bool(os.environ.get("CREAITE_RUN_KIND"))


def held_note(rel):
    """Whether the stored path `rel` is a note such a run must not see (marked confidential, or unreadable)."""
    p = paths.resolve(rel)
    return paths.is_note(p) and notes.held(p)


def held_out(rows, hold=True):
    """Search results without the confidential notes when `hold` (#60: no title, no link, no match on their words); else as given."""
    return [r for r in rows if not (hold and r["kind"] == "note" and held_note(r["path"]))]


def preview_for_run(rel, q=""):
    """The command line's preview: in a run creaite started, a confidential note answers as a file the index doesn't hold."""
    if held_run() and indexed(rel) and held_note(rel):
        return {"ok": False, "message": "That file isn't in the search index."}
    return preview(rel, q)
# ===== end #60 =====


# ── Ask: what Claude reads first (BL-07) ───────────────────────────────────────

HEADINGS = {"executive summary", "updates", "decisions", "action items", "open questions", "escalations",
            "open questions / escalations", "risks, issues, assumptions & dependencies", "risks and issues", "next steps",
            "summary", "attendees", "agenda", "progress", "help needed"}


def paragraphs(text):
    """The text as paragraphs (blank-line separated, else line by line), each with the heading it sits under."""
    lines = [ln.rstrip() for ln in text.splitlines()]
    blank_separated = any(not ln.strip() for ln in lines)
    out, heading, buf = [], "", []

    def flush():
        """Close the paragraph being gathered."""
        if buf:
            out.append((heading, " ".join(buf).strip()))
            buf.clear()
    for ln in lines:
        h = ln.strip().lstrip("#").strip().rstrip(":")
        if ln.strip() and (ln.lstrip().startswith("#") or h.lower() in HEADINGS):
            flush()
            heading = h
            continue
        if not ln.strip() or not blank_separated:
            flush()
            if ln.strip():
                buf.append(ln.strip())
                flush()
        else:
            buf.append(ln.strip())
    flush()
    return out


def score(par, terms):
    """How many of the search terms a paragraph contains (matched on their stems)."""
    low = par.lower()
    return sum(1 for t in terms if t.lower()[:max(4, len(t) - 2)] in low)


def best_passages(text, terms, room, per_file=2):
    """Up to per_file best paragraphs, each with its neighbours, as [(heading, text)], within room characters."""
    pars = paragraphs(text)
    if not pars:
        return []
    ranked = sorted(range(len(pars)), key=lambda i: (-score(pars[i][1], terms), i))
    out, used = [], 0
    for i in ranked[:per_file]:
        if terms and score(pars[i][1], terms) == 0 and out:
            break
        lo, hi = max(0, i - 1), min(len(pars), i + 2)
        chunk = "\n".join(p[1] for p in pars[lo:hi])
        if used + len(chunk) > room:
            chunk = chunk[:max(0, room - used)]
        if not chunk:
            break
        out.append((pars[i][0], chunk))
        used += len(chunk)
    return out


def item_line(table, r):
    """One tracker row as a plain line for Ask's context: kind, status, owner, date and text."""
    if table == "actions":
        bits = ["Action", r["status"], f"owner {r['owner']}", f"due {tracker.shown(r['due_date'])}" if r["due_date"] else "no due date"]
        what = r["description"]
    elif table == "raid":
        bits = [r["type"], r["status"], f"owner {r['owner']}", f"priority {r['priority']}" if r["priority"] else ""]
        reply = f" — response: {linktext.words(r['response_action'])}" if r["response_action"] else " — no response yet"
        what = r["description"] + reply
    elif table == "decisions":
        bits = ["Decision", f"made by {r['made_by']}" if r["made_by"] else "", f"on {tracker.shown(r['date'])}" if r["date"] else ""]
        what = r["decision"]
    else:
        bits = ["Milestone", r["status"], f"forecast {tracker.shown(r['forecast_date'] or r['baseline_date'])}"]
        what = r["name"]
    return f"{r['id']} ({r['project']}) — {', '.join(b for b in bits if b)}: {what}"


def file_passages(files, terms):
    """([(result, passages)] for the best 14 files, [confidential notes left out]). BL-301: a note marked confidential is never
    read here, so its text doesn't reach Claude; it is only counted."""
    ordered = [r for g in ("meetings", "reports", "documents", "notes") for r in files[g]]
    held = [r for r in ordered if r["kind"] == "note" and notes.held(paths.resolve(r["path"]))]   # #60: fail closed
    out = []
    for r in [r for r in ordered if r not in held][:14]:
        f = paths.resolve(r["path"])
        out.append((r, best_passages(indexed_text(f), terms, 2400) if f.is_file() else []))
    return out, held


def context(text, project=(), person=(), kind=(), frm=None, to=None, skip=(), now=None, budget=None):
    """Everything Ask should start from, as {text, sources}: the question and filters, the best passages (each with the
    paragraph around the match and its file and section), and the matching tracker rows. Gathered by plain code; the
    size is kept within the budget by dropping the lowest-ranked passages. Documents are labelled internal."""
    vocab = vocabulary()
    terms, chips, flt = understand(text, project, person, kind, frm, to, skip, True, now, vocab)
    opts = settings()
    budget = int(budget or opts["ask_budget_chars"])
    head = [f"Question: {text.strip()}", f"Today is {shown(now or today())}.",
            "Filters understood: " + ("; ".join(c["label"] for c in chips) if chips else "none"),
            "Words searched for: " + (", ".join(terms) if terms else "none")]
    sources, passages, rows, held = [], [], [], []
    if paths.DB.is_file():
        con = tracker.connect()
        try:
            if tracker.index_state()[0]:
                tracker.build_index()
            if flt["groups"] is None or "items" in flt["groups"]:
                rows = item_rows(con, vocab, terms, flt, any_term=True)[:40]
            if flt["groups"] is None or flt["groups"] - {"items"}:
                files = file_results(con, vocab, terms, flt, opts, any_term=True)
                passages, held = file_passages(files, terms)
        finally:
            con.close()
    body, used = [], sum(len(h) for h in head)
    items_block = [item_line(t, r) for t, r, _ in rows]
    items_text = "\n".join(items_block)
    room = max(0, budget - used - min(len(items_text), budget // 4) - 400)
    for n, (r, pars) in enumerate(passages, 1):
        name = Path(r["path"]).name
        label = {"minutes": "Meeting minutes", "transcript": "Meeting transcript", "report": "Report",
                 "document": "Document (internal)", "note": "Note (internal)"}[r["kind"]]
        for heading, chunk in pars:
            block = f"[{name}{' › ' + heading if heading else ''}] — {label}, {r['date_shown'] or 'undated'}, " \
                    f"{r['project'] or 'no project'}\n{chunk}"
            if room - len(block) < 0:
                break
            body.append(block)
            room -= len(block)
            if not any(s["path"] == r["path"] for s in sources):
                sources.append({"name": name, "stem": Path(r["path"]).stem, "path": r["path"], "kind": r["kind"]})
        else:
            continue
        break
    if held and not held_run():                 # #60 (Jarvis, 15-10-2026): a run creaite starts itself isn't told one matched
        body.append(f"({len(held)} confidential note(s) also matched; their text is left out)")
    out = head + ["", "## Passages from meetings, reports, documents and notes"] + (body or ["(none found)"]) + \
        ["", "## Tracker items"] + ([items_text[:max(0, budget - sum(len(x) for x in head + body) - 200)]] if items_block else ["(none found)"])
    for t, r, _ in rows:
        sources.append({"name": r["id"], "path": "", "kind": "item", "table": t, "project": r["project"]})
    return {"text": "\n".join(out), "sources": sources, "chips": chips, "terms": terms}


# ── Enrichment (BL-07) ─────────────────────────────────────────────────────────

ENRICH_FOLDERS = ("minutes", "transcripts", "reports")


def enrich_check(path):
    """The vault path of a filed meeting or report that may be enriched; exits if it isn't one (BL-07, BL-85)."""
    p = Path(path)
    msg = f"creaite search: {path} isn't a minutes, transcript or report path under projects/<project>/"
    if p.is_absolute() or ".." in p.parts or len(p.parts) < 4 or p.parts[0] != "projects":
        sys.exit(msg)
    if not paths.external():
        if p.parts[2] not in ENRICH_FOLDERS:
            sys.exit(msg)
    else:                                       # BL-85: the folders are the mapped ones; the file must be one the index covers as such
        target = paths.resolve(p.as_posix()).resolve()
        if target not in {f.resolve() for f, kind, _ in tracker.index_files() if kind in ENRICH_FOLDERS}:
            sys.exit(msg)
    return p.as_posix()


def enrich_set(rels, summary, tags):
    """Write one sidecar per path (the same text for every copy of a meeting). Returns the sidecar files written."""
    lines = [ln.strip() for ln in str(summary).strip().splitlines() if ln.strip()]
    if not 1 <= len(lines) <= 2 or any(len(ln) > 300 for ln in lines):
        sys.exit("creaite search: the summary is one or two lines of at most 300 characters each")
    tag_list = [re.sub(r"\s+", " ", t).strip().lower() for t in re.split(r"[,;\n]", tags) if t.strip()]
    tag_list = list(dict.fromkeys(tag_list))
    if not 3 <= len(tag_list) <= 8:
        sys.exit(f"creaite search: give three to eight topic tags (got {len(tag_list)})")
    paths.SEARCH_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for rel in rels:
        rel = enrich_check(rel)
        f = tracker.sidecar_path(rel)
        f.write_text(json.dumps({"path": rel, "summary": "\n".join(lines), "tags": tag_list}, ensure_ascii=False, indent=1),
                     encoding="utf-8")
        out.append(f)
    return out


def enrich_missing():
    """Indexed meetings and reports with no sidecar for any of their copies, newest first."""
    groups = {}
    for f, folder, code in tracker.index_files():
        if folder not in ENRICH_FOLDERS:
            continue
        key = hashlib.sha256(f.read_bytes()).hexdigest() if folder != "reports" else paths.rel(f)
        g = groups.setdefault(key, {"path": paths.rel(f), "paths": [], "folder": folder, "projects": [],
                                    "date": paths.file_date(f)[0] if folder != "reports" else (paths.name_date(f.name)[0] or "")})
        g["paths"].append(paths.rel(f))
        if code not in g["projects"]:
            g["projects"].append(code)
    out = [g for g in groups.values() if not any(tracker.read_sidecar(p) for p in g["paths"])]
    return sorted(out, key=lambda g: (g["date"], g["path"]), reverse=True)


# ── Command line ──────────────────────────────────────────────────────────────

def main(argv):
    """Run the search command in `argv` (see the module docstring)."""
    if not argv:
        print(__doc__)
        return 2
    cmd, args = argv[0], argv[1:]
    if cmd == "parse" and len(args) == 1:
        print(json.dumps(parse_query(args[0]), ensure_ascii=False, indent=2))
        return 0
    if cmd == "query" and args:
        multi = {"--project": [], "--person": [], "--kind": [], "--skip": []}
        single, i = {}, 1
        while i < len(args):
            if args[i] == "--no-parse":
                single["parse"] = False
                i += 1
            elif args[i] in multi and i + 1 < len(args):
                multi[args[i]].append(args[i + 1])
                i += 2
            elif args[i] in ("--from", "--to") and i + 1 < len(args):
                single[args[i][2:]] = args[i + 1]
                i += 2
            else:
                sys.exit(f"creaite search: unexpected {args[i]}")
        res = search(args[0], multi["--project"], multi["--person"], multi["--kind"], single.get("from"), single.get("to"),
                     multi["--skip"], single.get("parse", True), hold=held_run())     # #60
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    if cmd == "enrich":
        if args[:1] == ["--missing"]:
            miss = enrich_missing()
            if "--json" in args:
                print(json.dumps(miss, ensure_ascii=False, indent=2))
            else:
                print("\n".join(f"{g['date'] or 'undated'}  {g['path']}" + (f"  (also {len(g['paths']) - 1} other cop{'y' if len(g['paths']) == 2 else 'ies'})"
                                                                         if len(g["paths"]) > 1 else "") for g in miss)
                      or "Every indexed meeting and report has a summary.")
            return 0
        if args[:1] == ["set"]:
            rels, summary, tags, i = [], None, None, 1
            while i + 1 < len(args):
                if args[i] == "--path":
                    rels.append(args[i + 1])
                elif args[i] == "--summary":
                    summary = args[i + 1]
                elif args[i] == "--tags":
                    tags = args[i + 1]
                else:
                    sys.exit(f"creaite search: unexpected {args[i]}")
                i += 2
            if not rels or summary is None or tags is None:
                sys.exit("creaite search: enrich set needs --path, --summary and --tags")
            written = enrich_set(rels, summary, tags)
            print(f"Wrote {len(written)} summary file(s) in {paths.rel(paths.SEARCH_DIR)}/. The index picks them up at its next rebuild.")
            return 0
        print(__doc__)
        return 2
    if cmd == "context" and args:
        multi, single, i, as_json = {"--project": [], "--person": [], "--kind": [], "--skip": []}, {}, 1, False
        while i < len(args):
            if args[i] == "--json":
                as_json = True
                i += 1
            elif args[i] in multi and i + 1 < len(args):
                multi[args[i]].append(args[i + 1])
                i += 2
            elif args[i] in ("--from", "--to") and i + 1 < len(args):
                single[args[i][2:]] = args[i + 1]
                i += 2
            else:
                sys.exit(f"creaite search: unexpected {args[i]}")
        res = context(args[0], multi["--project"], multi["--person"], multi["--kind"], single.get("from"), single.get("to"),
                      multi["--skip"])
        print(json.dumps(res, ensure_ascii=False) if as_json else res["text"])
        return 0
    if cmd == "preview" and args:
        print(json.dumps(preview_for_run(args[0], args[1] if len(args) > 1 else ""), ensure_ascii=False))   # #60
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    try:
        import log as debuglog  # BL-102: the debug log (not `log`: some scripts have a function of that name); a script runs without it
    except ImportError:
        debuglog = None
    sys.exit(debuglog.main("search.py", main, sys.argv[1:]) if debuglog else main(sys.argv[1:]))
