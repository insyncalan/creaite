"""The client leak check (v2.1.0 P3; BL-336), on the data. Standard library only. A library: no command line.

Nothing that isn't client-visible, is Sensitive or is partner-only can reach a client report (or the minutes' distributed version,
BL-338). The check reads a creaite document's data (creaite_doc.py), never a Word file:
  - item_problem: why one item may not appear for a client, or None (the tracker as it is now, and the item's labels);
  - make_safe: a copy of a client document with every row, tag, milestone and item that fails dropped, and what was dropped;
  - findings: what is still wrong with a client document (items, internal wording found in its text, the tracker's internal health
    reason or an internal-only marker, and the name of someone who owns only items a client can't see), for approve and export:
    the gate at the end, whatever route or place the text came through (#123);
  - people: the names (and register aliases) of the owners of the items a client report may show, and of everyone else on the
    project's items: the names check edit_ai.client_problems and findings share (#123);
  - text_findings: the wording check on any text, moved here from review.client_findings (which still reads the Word flow's drafts
    through it until the Word drafts are retired).
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

SENSITIVE = "sensitive"
PARTNER_ONLY = {"partner only", "partner-only", "partner"}      # a label with one of these names keeps an item from every client
CLIENT_TABLES = ("actions", "raid", "decisions", "milestones")   # promises and workstreams never reach a client report
TEXT_OF = {"actions": "description", "raid": "description", "decisions": "decision", "milestones": "name"}
INTERNAL_WORDS = ("confidential", "restricted", "documents/")


def squash(t):
    """Text with its whitespace squeezed to single spaces."""
    return re.sub(r"\s+", " ", t or "").strip()


def connect():
    """The tracker database."""
    import tracker
    return tracker.connect()


def blocking_labels(con):
    """{label name in lower case: why} for every label that keeps an item out of a client report: Sensitive (never shown, whatever
    a warning card chose), any label that excludes (behaviour or default choice) and a partner-only label."""
    out = {SENSITIVE: "Sensitive"}
    try:
        for name, behaviour, choice in con.execute("SELECT name, behaviour, default_choice FROM labels"):
            low = (name or "").strip().lower()
            if low in PARTNER_ONLY:
                out[low] = "partner-only"
            elif low != SENSITIVE and (behaviour == "exclude" or choice == "exclude"):
                out[low] = f"labelled {name}"
    except Exception as e:  # noqa: BLE001  no labels table (an older vault): Sensitive still blocks, by name
        if "no such table" not in str(e):
            raise
    return out


def labels_of(con, item_id):
    """An item's label names."""
    try:
        return [r[0] for r in con.execute("SELECT label FROM item_labels WHERE item_id = ?", (item_id,))]
    except Exception as e:  # noqa: BLE001  no item_labels table (an older vault): no labels
        if "no such table" not in str(e):
            raise
        return []


def item_problem(con, ref, blocking=None):
    """Why the item `ref` may not appear in a client report, as a sentence, or None when it may."""
    import tracker
    table = tracker.item_table(ref)
    if table not in CLIENT_TABLES:
        return f"{ref} isn't an item a client report can show"
    row = con.execute(f"SELECT * FROM {table} WHERE id = ?", (ref,)).fetchone()
    if row is None:
        return f"{ref} isn't in the tracker"
    row = dict(row)
    if not int(row.get("client_visible") or 0):
        return f"{ref} isn't client-visible"
    if table == "milestones" and not tracker.client_milestones([row]):
        return f"{ref} has no client wording, or is cancelled"
    blocking = blocking_labels(con) if blocking is None else blocking
    for name in labels_of(con, ref):
        why = blocking.get(name.strip().lower())
        if why:
            return f"{ref} is {why}: never in a client report" if why != "Sensitive" else f"{ref} is Sensitive: never in a client report"
    return None


def refs(doc):
    """Every item reference a document holds: its items, table rows, source tags and milestone lists."""
    out = set((doc.get("items") or {}).keys())
    for s in doc.get("sections") or []:
        out |= {r.get("ref") for r in s.get("rows") or []}
        out |= {t.get("ref") for t in s.get("tags") or []}
        data = s.get("data") or {}
        out |= set(data.get("milestones") or []) | set(data.get("timeline") or [])
    return {r for r in out if r}


def _drop_section_refs(s, bad):
    """A section without its rows, tags and milestone references to the items in `bad`."""
    s = dict(s)
    if s.get("rows"):
        s["rows"] = [r for r in s["rows"] if r.get("ref") not in bad]
    if s.get("tags"):
        s["tags"] = [t for t in s["tags"] if t.get("ref") not in bad]
    if isinstance(s.get("data"), dict):
        s["data"] = {k: ([x for x in v if x not in bad] if k in ("milestones", "timeline") and isinstance(v, list) else v)
                     for k, v in s["data"].items()}
    return s


def make_safe(doc, con=None):
    """(a copy of the document with every reference to an item a client may not see dropped, [why each was dropped]). An internal
    document is returned as it is."""
    if (doc.get("audience") or "internal") == "internal":
        return doc, []
    con = con or connect()
    blocking = blocking_labels(con)
    problems = {r: item_problem(con, r, blocking) for r in sorted(refs(doc))}
    bad = {r for r, why in problems.items() if why}
    if not bad:
        return doc, []
    out = dict(doc)
    out["sections"] = [_drop_section_refs(s, bad) for s in doc.get("sections") or []]
    out["items"] = {k: v for k, v in (doc.get("items") or {}).items() if k not in bad}
    return out, [problems[r] for r in sorted(bad)]


def _memory_findings(code, low):
    """Lines of the project's memory marked Client-safe: no that appear in the text."""
    found = []
    memory = paths.project_dir(code) / "CLAUDE.md"
    for line in (memory.read_text(encoding="utf-8").splitlines() if memory.exists() else []):
        if "Client-safe: no" in line:
            core = squash(re.sub(r"^\s*[-*]\s+", "", re.sub(r"[-*]?\s*\(?Client-safe: no\)?\.?", "", line))).lower()[:40]
            if len(core) >= 10 and core in squash(low):
                found.append(f"memory line marked Client-safe: no appears: “{line.strip()[:80]}”")
    return found


def _label_findings(con, code, text, low):
    """BL-94's floor: an item whose label excludes it from client output, found by its ID or its wording."""
    import tracker as t
    found = []
    for item_id, label in con.execute("SELECT il.item_id, il.label FROM item_labels il JOIN labels l ON l.name = il.label "
                                      "WHERE (l.behaviour = 'exclude' OR l.default_choice = 'exclude') AND il.item_id LIKE ?",
                                      (f"{code}-%",)):
        table = t.item_table(item_id)
        col = {"actions": "description", "raid": "description", "decisions": "decision"}.get(table)
        row = con.execute(f"SELECT {col}, client_message FROM {table} WHERE id = ?", (item_id,)).fetchone() if col else None
        wordings = [row[0]] + [ln.split(":", 1)[1] for ln in (row[1] or "").splitlines() if ":" in ln and table != "decisions"] \
            + ([row[1]] if row and table == "decisions" else []) if row else []      # its own words, and its client wording
        if re.search(rf"\b{re.escape(item_id)}\b", text):
            found.append(f"{item_id} is labelled {label} but its ID appears")
        else:
            hit = next((w for w in wordings if len((w or "").strip()) >= 15 and squash(w).lower() in squash(low)), None)
            if hit:
                found.append(f"{item_id} is labelled {label} but its wording appears: “{hit.strip()[:80]}”")
    return found


def text_findings(con, code, text):
    """Internal-only content in a client text: an item that isn't client-visible by its ID or wording, a memory line marked
    Client-safe: no, an item a label excludes, and the words confidential, restricted or documents/ (moved from
    review.client_findings; its messages unchanged)."""
    low = text.lower()
    found = []
    for table, col in (("raid", "description"), ("decisions", "decision"), ("actions", "description")):
        for row in con.execute(f"SELECT id, {col} FROM {table} WHERE project = ? AND client_visible = 0", (code,)):
            if re.search(rf"\b{re.escape(row[0])}\b", text):
                found.append(f"{row[0]} isn't client-visible but its ID appears")
            elif len(row[1] or "") >= 15 and squash(row[1]).lower() in squash(low):
                found.append(f"{row[0]} isn't client-visible but its wording appears: “{row[1][:80]}”")
    found += _memory_findings(code, low)
    try:                                                       # BL-94's floor
        found += _label_findings(con, code, text, low)
    except Exception as e:  # noqa: BLE001  BL-228: fails closed; skipped only when the tables aren't there
        import review
        found.extend(review.label_check_failure(con, e, code))
    for word in INTERNAL_WORDS:
        if word in low:
            found.append(f"contains “{word}”")
    return found


OWNER_TABLES = ("actions", "raid", "decisions", "milestones")


def person(owner):
    """An owner's name without its organisation: "Jane Doe (Example Client Ltd)" is "Jane Doe"."""
    return re.sub(r"\s*\([^)]*\)\s*$", "", owner or "").strip()


def named(text, people):
    """The people's names (or aliases) that the text holds, a name inside a longer one found counted once."""
    low = (text or "").lower()
    found = {p for p in people if p and len(p) > 2 and re.search(rf"\b{re.escape(p.lower())}\b", low)}
    return {p for p in found if not any(p != q and p.lower() in q.lower() for q in found)}   # "Sara" inside "Sara Khan"


def register_aliases():
    """{full name in lower case: [aliases]} from the people register (the same columns drafts.people_names reads); {} when it can't
    be read."""
    out = {}
    try:
        text = paths.PEOPLE_REGISTER.read_text(encoding="utf-8") if paths.PEOPLE_REGISTER.exists() else ""
    except OSError:
        return out
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and cells[0] and not set(cells[0]) <= set("-: ") and cells[0].lower() not in ("name", "full name"):
            out.setdefault(cells[0].lower(), []).extend(a.strip() for a in re.split(r"[;,]", cells[2]) if a.strip())
    return out


def project_owners(con, code):
    """Every owner named on the project's items, open or not, without their organisation."""
    out = set()
    for table in OWNER_TABLES:
        cols = [r[1] for r in con.execute(f"PRAGMA table_info({table})")]
        if "owner" in cols:
            out |= {person(o) for (o,) in con.execute(f"SELECT DISTINCT owner FROM {table} WHERE project = ?", (code,))
                    if o and o != "TBC"}
    return sorted(out)


OPEN_STATUS = {"actions": ("Open", "Delayed"), "raid": ("Open",), "decisions": ("Pending",), "milestones": ("Planned",)}


def _owners(con, code, blocking):
    """Yield (owner without organisation, whether a client report may show the item, whether it is open) for each of the project's
    items with an owner."""
    for table in OWNER_TABLES:
        cols = [r[1] for r in con.execute(f"PRAGMA table_info({table})")]
        if "owner" not in cols:
            continue
        for i, o, st in con.execute(f"SELECT id, owner, status FROM {table} WHERE project = ?", (code,)):
            if o and o != "TBC":
                yield person(o), not item_problem(con, i, blocking), st in OPEN_STATUS.get(table, ())


def _tokens(names):
    """Every word of the names, in lower case: "Jane Doe" gives "jane" and "doe"."""
    return {w for n in names for w in re.findall(r"[\w'-]+", n.lower())}


def people(con, code, blocking=None):
    """(client, internal): the names and register aliases of the owners of the project's items a client report may show (any
    status), and of the owners of its OPEN items a client report can't show who own none of those (#123 review M3: someone whose
    only internal items are closed is neither). Alan's own name and short forms are left out (he is named in his client reports),
    and so is an alias that is ambiguous (M2): one that is, or is a word of, a client-visible owner's name or alias, or Alan's; an
    internal-only owner's full name is always kept."""
    blocking = blocking_labels(con) if blocking is None else blocking
    shown, other = set(), set()
    for name, may_show, is_open in _owners(con, code, blocking):
        if may_show:
            shown.add(name)
        elif is_open:
            other.add(name)
    aliases = register_aliases()
    client = shown | {a for n in shown for a in aliases.get(n.lower(), [])}
    keep = {x.lower() for x in client | alans_names()}
    shared = keep | _tokens(client | alans_names())
    full = {n for n in other - shown if n.lower() not in keep}
    internal = full | {a for n in full for a in aliases.get(n.lower(), []) if a.lower() not in shared}
    return client, internal


def alans_names():
    """Alan's own name and short forms (settings identity), or none when the settings can't be read."""
    try:
        ident = paths.load_settings().get("identity") or {}
        return {ident.get("name") or ""} | set(ident.get("short_forms") or [])
    except Exception:  # noqa: BLE001  no settings: nobody is left out
        return set()


def name_findings(con, code, text, blocking=None):
    """The people a client text names who own only items a client report can't show (people's internal set)."""
    _, internal = people(con, code, blocking)
    return [f"{n} is named but owns only items a client report can't show" for n in sorted(named(text, internal))]


def doc_text(doc):
    """Everything of a document that reaches its file or an export, as text: every shown section's words and the items' values."""
    import creaite_doc
    clean = creaite_doc.clean(doc)
    return creaite_doc.search_text(clean) + "\n" + json.dumps(clean.get("items") or {}, ensure_ascii=False)


def findings(doc, con=None):
    """What would leak if this client document were approved or exported: [sentence]; [] when it is safe. An internal document has
    none."""
    if (doc.get("audience") or "internal") == "internal":
        return []
    con = con or connect()
    blocking = blocking_labels(con)
    code, text = doc.get("project") or "", doc_text(doc)
    found = [why for why in (item_problem(con, r, blocking) for r in sorted(refs(doc))) if why]
    found += text_findings(con, code, text)
    found += [f"it holds {why}" for why in internal_findings(con, code, doc)]             # #123: the gate at the end, any route
    return found + name_findings(con, code, text, blocking)


def internal_findings(con, code, doc):
    """drafts.internal_findings on a client document (#123 review M1). A client report shows internal health, so the tracker's
    health reason may stand in the document's own shown health section (Match internal copies it there): it is checked on
    everything else the document holds. An internal-only marker is found anywhere, the health section included."""
    import creaite_doc
    import drafts
    shown = creaite_doc.sections_text(doc)
    health_ids = {s.get("id") for s in doc.get("sections") or [] if s.get("type") == "health"}
    health = "\n\n".join(t for i, _h, t in shown if i in health_ids)
    clean = creaite_doc.clean(doc)
    rest = "\n\n".join([clean.get("title") or ""] + [f"{h}\n\n{t}" if i not in health_ids else h for i, h, t in shown]) \
        + "\n" + json.dumps(clean.get("items") or {}, ensure_ascii=False)
    found = drafts.internal_findings(con, code, rest)
    if drafts.INTERNAL_MARK.search(health) and "an internal-only marker" not in found:
        found.append("an internal-only marker")
    return found
