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
  - text_findings: the wording check on any text, moved here from review.client_findings; IDs found however written (#127);
  - plain_findings: findings' checks on a text with no sections: review.client_findings reads a Word draft through it (#127).
The names check fails closed: a people register that is missing or can't be read is a finding of its own (#127)."""
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


# #127 round 7: what the checks put between two forms of a text (as written, as shown, decoded) or two addresses. A newline, or
# any punctuation, can be read across ("…the rest is internal" then "Only _two_ …" reads "internal\nOnly" as the marker; "internal\n.\nonly"
# too), so the join is a word of its own that no name, ID, wording, health reason or marker holds: every pattern stops at it.
JOIN = "\nqqjoinqq\n"


def joined(*forms):
    """The forms of a text one after another, JOIN between them, each once and in order (empty ones left out)."""
    out = []
    for f in forms:
        if f and f not in out:
            out.append(f)
    return JOIN.join(out)


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
    """Lines of the project's memory marked Client-safe: no that appear in the text (`low`: as text_findings reads it)."""
    import edit_ai
    found = []
    memory = paths.project_dir(code) / "CLAUDE.md"
    for line in (memory.read_text(encoding="utf-8").splitlines() if memory.exists() else []):
        if "Client-safe: no" in line:
            core = re.sub(r"^\s*[-*]\s+", "", re.sub(r"[-*]?\s*\(?Client-safe: no\)?\.?", "", line))
            core = squash(edit_ai.normal(core)).lower()[:40]
            if len(core) >= 10 and core in squash(low):
                found.append(f"memory line marked Client-safe: no appears: “{line.strip()[:80]}”")
    return found


def _label_findings(con, code, text, low, ids):
    """BL-94's floor: an item whose label excludes it from client output, found by its ID (`ids`: the text's, however written) or
    its wording."""
    import edit_ai
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
        if item_id in ids:
            found.append(f"{item_id} is labelled {label} but its ID appears")
        else:
            hit = next((w for w in wordings if len((w or "").strip()) >= 15 and squash(edit_ai.normal(w)).lower() in squash(low)),
                       None)
            if hit:
                found.append(f"{item_id} is labelled {label} but its wording appears: “{hit.strip()[:80]}”")
    return found


def _link_findings(con, text):
    """({item IDs the text's work-item links name}, [findings for a work-item link creaite can't read, and for a creaite: link of
    a kind a client report may not hold])."""
    ids, unread = link_refs(con, text)
    return ids, [f"a link to a work item creaite can't read: “{a[:40]}”" for a in unread] + \
        [f"a creaite link a client can't open: “creaite:{k}”" for k in sorted(creaite_kinds(text) - LINK_KINDS)]


def text_findings(con, code, text, skip=()):
    """Internal-only content in a client text: an item that isn't client-visible by its ID or wording, a memory line marked
    Client-safe: no, an item a label excludes, and the words confidential, restricted or documents/ (moved from
    review.client_findings; its messages unchanged). #127: an ID is found however it is written (edit_ai.loose_ids: any case,
    look-alike characters, spaces or dots), and so is any other item the tracker holds that a client report can't show (a
    milestone or promise, or an item of another project); `skip`: items already found by the caller, not listed twice."""
    import edit_ai
    raw, text = text, with_decoded(as_shown(text))             # #127 round 4: %- or entity-encoded words are read too
    low = edit_ai.normal(text).lower()                         # (and invisible characters don't hide a word)
    ids, found = _link_findings(con, text)                     # #127: a work-item link's address counts as its ID
    ids |= edit_ai.loose_ids(con, text)
    seen = set(skip)
    for table, col in (("raid", "description"), ("decisions", "decision"), ("actions", "description")):
        for row in con.execute(f"SELECT id, {col} FROM {table} WHERE project = ? AND client_visible = 0", (code,)):
            if row[0] in ids:
                seen.add(row[0])
                found.append(f"{row[0]} isn't client-visible but its ID appears")
            elif len(row[1] or "") >= 15 and squash(edit_ai.normal(row[1])).lower() in squash(low):
                found.append(f"{row[0]} isn't client-visible but its wording appears: “{row[1][:80]}”")
    blocking = blocking_labels(con)
    for ref in sorted(ids - seen):                             # #127: milestones, promises and other projects' items
        if not edit_ai.in_tracker(con, ref):
            continue
        why = f"{ref} belongs to another project" if ref.split("-")[0] != code else item_problem(con, ref, blocking)
        if why:
            found.append(f"{why}, but its ID appears")
    found += _memory_findings(code, low)
    try:                                                       # BL-94's floor
        found += _label_findings(con, code, text, low, ids)
    except Exception as e:  # noqa: BLE001  BL-228: fails closed; skipped only when the tables aren't there
        import review
        found.extend(review.label_check_failure(con, e, code))
    for word in INTERNAL_WORDS:
        if word in low:
            found.append(f"contains “{word}”")
    return found + unreadable_findings(raw)


OWNER_TABLES = ("actions", "raid", "decisions", "milestones")


def person(owner):
    """An owner's name without its organisation: "Jane Doe (Example Client Ltd)" is "Jane Doe"."""
    return re.sub(r"\s*\([^)]*\)\s*$", "", owner or "").strip()


def _name_form(text, lower=True):
    """Text as a name is matched: as the ID check reads it (edit_ai.normal: NFKC, so a no-break space is a space; invisible
    characters gone), every run of whitespace (two spaces, a tab, a line break) one space, in lower case (#127 review), and its
    accents dropped ("Quentín" is "quentin"; #127 round 4; edit_ai.normal drops every combining mark since round 5), and a curly
    apostrophe straight ("O’Neill" is "o'neill", either way round; round 5). `lower=False` keeps its capitals, for the forms of a
    name that count only when written as one (name_pattern; round 6)."""
    import edit_ai
    t = re.sub(r"\s+", " ", edit_ai.normal(text or ""))
    return (t.lower() if lower else t).translate(APOSTROPHES)


APOSTROPHES = str.maketrans({c: "'" for c in "\u2019\u2018\u02bc\u2032"})


NAME_SEP = r"(?:[\s._\-+·'’*~`/|;\\]{1,4}|,)"   # between a name's words: spaces, a dot, dash, underscore, plus, emphasis
#                     # marks, (#127 round 5) a slash, bar, semicolon or backslash, and (round 6) a comma with no space ("Quentin,Marlow";
#                     # "Quentin, Marlow" is a list, read the same decoded or not)
JOIN_PART, JOIN_LEN = 3, 8                # #127 round 4: a name run together ("QuentinMarlow") only when each word has at least 3
#                                         # letters and the whole at least 8, so "Max Well" never matches "maxwell"


def _capitalised(word):
    """A pattern for one word of a name written as a name: its first letter a capital, the rest in any case ("Marlow", "MARLOW")."""
    return rf"(?-i:{re.escape(word[0].upper())})" + (rf"(?i:{re.escape(word[1:])})" if len(word) > 1 else "")


SCRIPT_END = 0x323B0                      # past the last letter Unicode 15 assigns (CJK Extension H); nothing beyond is a letter


def _class(test):
    """A character class (its inside, for [...]) of every character up to SCRIPT_END that `test` accepts, as ranges."""
    out, start, prev = [], None, None
    for cp in range(SCRIPT_END + 1):
        if cp < SCRIPT_END and test(chr(cp)):
            start, prev = (cp if start is None else start), cp
        elif start is not None:
            out.append(re.escape(chr(start)) + (f"-{re.escape(chr(prev))}" if prev > start else ""))
            start = None
    return "".join(out)


_INITIAL = []


def initial():
    """#127 round 7: the initial between a name's words, in any script: a capital letter (one whose upper case is itself and
    differs from its lower case: "Ł", "Б", not "a" or "ł"), or in a script with no case (Chinese, Arabic, Devanagari) a single
    letter followed by a dot or a space ("王 小 明"); then a dot or the separator after it. Built once, when a name is first
    matched (about 0.1 s)."""
    if not _INITIAL:
        upper = _class(lambda c: c.upper() == c != c.lower())
        caseless = _class(lambda c: c.isalpha() and c.upper() == c.lower())
        _INITIAL.append(rf"(?:(?-i:[{upper}])\.?|[{caseless}](?=[.\s])\.?)")
    return _INITIAL[0]


def name_pattern(name):
    """The pattern a name is found by (#127 round 4), matched against _name_form(text, lower=False): its words in order, in any
    case, with any run of separators between them (NAME_SEP), or, for a name whose words are all JOIN_PART letters or more and
    JOIN_LEN together, none ("QuentinMarlow", or the soft hyphen Word hides); a capital initial between its words ("Quentin J.
    Marlow"; never "a", so "Will a price cap" isn't Will Price; round 6); a two-word name also surname first after a comma
    ("Marlow, Quentin") or, when both words have JOIN_PART letters or more and both are written with a capital, without one
    ("Marlow Quentin", "MARLOW Quentin"; never "price will" or "Hill rose"; rounds 5 and 6). Always a whole word at each end, so
    a longer name ("Marlowe") is not this one. None for a name with nothing to match."""
    words = re.findall(r"[^\W_]+(?:['’][^\W_]+)*", _name_form(name))
    if not words:
        return None
    if len(words) == 1:
        return re.compile(rf"(?<![^\W_])(?i:{re.escape(words[0])})(?![^\W_])")
    joined = all(len(w) >= JOIN_PART for w in words) and sum(map(len, words)) >= JOIN_LEN
    sep = f"(?:{NAME_SEP}{initial()}(?={NAME_SEP}))?(?:{NAME_SEP}){'?' if joined else ''}"     # an initial may stand between
    forms = ["(?i:" + sep.join(map(re.escape, words)) + ")"]
    if len(words) == 2:
        forms.append(rf"(?i:{re.escape(words[1])}\s{{0,3}},\s{{0,3}}{re.escape(words[0])})")
        if min(map(len, words)) >= JOIN_PART:
            forms.append(rf"{_capitalised(words[1])}(?:{NAME_SEP}){_capitalised(words[0])}")
    return re.compile(r"(?<![^\W_])(?:" + "|".join(forms) + r")(?![^\W_])")


def _words_shown(text):
    """The text's words as Word shows them, Markdown's markers and link addresses gone (docx_tools.md_runs): "**Quentin** Marlow"
    and "[Quentin](https://…) Marlow" read "Quentin Marlow" (#127 round 4)."""
    if not re.search(r"[*_~`\[]", text or ""):
        return ""
    try:
        import docx_tools
        return "\n".join("".join(r[0] for r in docx_tools.md_runs(ln)) for ln in (text or "").splitlines())
    except Exception:  # noqa: BLE001  the text as written is still read
        return ""


EMPHASIS_MARKS = re.compile(r"[*_~`]")
SHOWN_PASSES = 12               # #127 round 7: plain until nothing changes, at most this many times (each pass is linear)
# #127 round 7: emphasis inside a word, as the HTML and PDF exports draw it ("inter*nal*-only", "ABC-A-0*0*4", "q~~uie~~t"): a run
# of * or of two or more ~ with no space on either side and a letter or digit on one. An underscore inside a word is not
# emphasis anywhere (snake_case stays as written).
INTRAWORD = re.compile(r"(?<=\w)(?:\*+|~{2,})(?=[^\s*~])|(?<=[^\s*~])(?:\*+|~{2,})(?=\w)")


def _plain_shown(t):
    """The text as Word shows it: docx_tools.plain and backticks dropped, again until nothing changes (SHOWN_PASSES at most)."""
    import docx_tools
    shown = t
    for _ in range(SHOWN_PASSES):
        nxt = "\n".join(docx_tools.plain(ln) for ln in shown.split("\n")).replace("`", "")
        if nxt == shown:
            break
        shown = nxt
    return shown


def as_shown(text):
    """The text, and when it holds an emphasis mark (* _ ~ `) also as the exports show it (#127 round 6): Markdown's emphasis,
    strike-through and link markers taken off as docx_tools.plain does, again until nothing changes (nested "**_x_**" too), and
    code backticks dropped, so "_ABC-A-004_", "internal _only_" or "the ~~quiet~~ audit" read as their words. Round 7: also with
    the emphasis marks inside a word dropped (INTRAWORD, as the HTML and PDF exports draw them), and each form after JOIN, so no
    pattern reads from one form into the next."""
    t = text or ""
    if not EMPHASIS_MARKS.search(t):
        return t
    try:
        inner = INTRAWORD.sub("", t)
        return joined(t, _plain_shown(t), inner, _plain_shown(inner))
    except Exception:  # noqa: BLE001  the text as written is still read
        return t


def named(text, people, every=False):
    """The people's names (or aliases) that the text holds, a name inside a longer one found counted once (with `every`, as the
    client gate asks, every one: "Quentin; Marlow" names both Quentin and Quentin Marlow; #127 round 6); whitespace, invisible
    characters, accents, separators between a name's words or none, surname first, and Markdown around its words don't hide it
    (_name_form, name_pattern, _words_shown)."""
    low = _names_text(text)
    found = set()
    for p in people:
        if p and len(p) > 2:
            pat = name_pattern(p)
            if pat is not None and pat.search(low):
                found.add(p)
    if every:
        return found
    return {p for p in found if not any(p != q and p.lower() in q.lower() for q in found)}   # "Sara" inside "Sara Khan"


def _names_text(text):
    """The text as names are matched in it: as written, as the exports show it (as_shown, emphasis inside a word too: "Quen*tin*
    Marlow") and as Word shows its words, JOIN between (round 7)."""
    return joined(_name_form(as_shown(text), lower=False), _name_form(_words_shown(text), lower=False))


def named_beyond(text, people, allowed):
    """#127 round 7: the people (names or aliases) the text names somewhere other than inside an allowed name: "Sam" in "Sam Patel
    will run it" is Sam Patel, allowed, not someone else whose alias is Sam; "Sam Patel and Sam" still names a Sam. Every name
    counts, as named(every=True) does, but only where it stands outside the span of an allowed name's match."""
    low = _names_text(text)
    spans = []
    for a in allowed:
        pat = name_pattern(a) if a and len(a) > 2 else None
        spans += [m.span() for m in pat.finditer(low)] if pat is not None else []
    out = set()
    for p in people:
        pat = name_pattern(p) if p and len(p) > 2 and p not in allowed else None
        if pat is not None and any(not any(a <= m.start() and m.end() <= b for a, b in spans) for m in pat.finditer(low)):
            out.add(p)
    return out


REGISTER_UNREAD = ("the people register couldn't be read, so the names couldn't be checked: fix it in Settings › People "
                   "(or say \"setup\"), then try again")


class RegisterUnreadable(Exception):
    """The people register is missing, can't be read or has no People table (#127: the names check fails closed)."""


def register_aliases():
    """{full name in lower case: [aliases]} from the people register (the same columns drafts.people_names reads). Raises
    RegisterUnreadable when the register is missing, can't be read or has no People table (#127: fails closed, never {})."""
    import propose
    out = {}
    try:
        text = paths.PEOPLE_REGISTER.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as e:
        raise RegisterUnreadable(REGISTER_UNREAD) from e
    if not propose.people_table(text.splitlines()):
        raise RegisterUnreadable(REGISTER_UNREAD)
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
    """The people a client text names who own only items a client report can't show (people's internal set); one finding saying
    so when the people register can't be read (#127: fails closed)."""
    try:
        _, internal = people(con, code, blocking)
    except RegisterUnreadable:
        return [REGISTER_UNREAD]
    return [f"{n} is named but owns only items a client report can't show" for n in sorted(named(text, internal, every=True))]


def doc_text(doc):
    """Everything of a document that reaches its file or an export, as text: every shown section's words and the items' values,
    and (#127) every link address its shown data holds (address_text), which the words alone (creaite_doc._plain) leave out; and
    (#127 review) the sections' and items' strings as stored (raw_text), so text that _plain deletes but Word shows (a link that
    Markdown doesn't read as one, a title, an image's words) is checked too."""
    import creaite_doc
    clean = creaite_doc.clean(doc)
    raw = raw_strings(clean)
    return creaite_doc.search_text(clean) + "\n" + json.dumps(clean.get("items") or {}, ensure_ascii=False) \
        + "\n" + raw_text(raw) + _addresses(raw)


def raw_strings(clean):
    """A cleaned document's sections' and items' strings as stored, one text."""
    return "\n".join(_strings(clean.get("sections") or []) + _strings(clean.get("items") or {}))


def _addresses(raw):
    """The raw strings' link addresses (address_text) and work-item link addresses, on lines of their own, or ""."""
    addresses = "\n".join([address_text(raw)] + [f"creaite:item/{a}" for a in item_links(raw)]).strip()   # (spaces in an ID too)
    return "\n" + addresses if addresses else ""


NOT_TEXT = ("ref", "milestones", "timeline")          # item references, checked as items (refs), not as words


def _strings(x):
    """Every string in a document's data (its sections: text, headings, cells, panes; or its items), as stored, but its item
    references (NOT_TEXT)."""
    if isinstance(x, str):
        return [x]
    if isinstance(x, dict):
        return [t for k, v in x.items() if k not in NOT_TEXT for t in _strings(v)]
    return [t for v in x for t in _strings(v)] if isinstance(x, list) else []


WEB_ADDRESS = re.compile(r"(?<![\w/%.-])(?:https?|mailto)[ \t]{0,5}:[^\s<>()\[\]\"']{0,2000}", re.I)


def raw_text(raw):
    """Stored strings as the checks read them: as they are, but an https or mailto address as plain words (as address_text reads
    it), so an external page's path is not read as one of creaite's own (documents/)."""
    return WEB_ADDRESS.sub(lambda m: re.sub(r"[^0-9A-Za-z]+", " ", m.group(0)), raw or "")


# #127: link addresses. The gate reads the ADDRESS of every link (inline, image, reference definition, <auto>, an HTML href, a bare
# https:, mailto: or creaite: one), fully %-decoded and entity-decoded (_decoded), because the words alone can say anything. Each
# address is added to the text the checks read twice over: as decoded (so a creaite: address keeps its shape) and as plain words
# ("mailto quentin marlow example com"), so the ID, names, wording and marker checks find what it holds. "Internal", kept narrow:
# an address that holds an item a client may not see (any project's, however written), the name or alias of someone who owns only
# such items, the tracker's health reason or an internal-only marker; and any creaite: link but a work item a client may see or a
# person (creaite:item, creaite:person; a note or anything else in creaite is Alan's own). An ordinary https or mailto address to
# anything else passes: there is no list of internal hosts.
ADDRESS = re.compile(
    r"\]\(\s{0,20}<?((?:https?|mailto):[^)\s]{0,2000}"                    # an inline link or image: a web address to where
    r"|[^()\s]{0,2000}(?:\([^()\s]{0,200}\)[^()\s]{0,2000})?)"                # Word's link ends (docx_tools.INLINE), quotes included
    r"|^[ \t]{0,3}\[[^\[\]\n]{1,300}\]:[ \t]{0,20}<?([^\s<>]{1,2000})"                       # a reference definition
    r"|href[ \t]{0,5}=[ \t]{0,5}[\"']([^\"'<>]{0,2000})"                                     # an HTML link
    r"|<([a-z][a-z0-9+.-]{1,30}:[^<>\s]{1,2000})>"                                            # an <auto> link
    r"|(?<![\w/%.-])((?:https?|mailto|creaite)[ \t]{0,5}(?::|%3a)[^\s<>()\[\]\"']{1,2000})",   # a bare address
    re.I | re.M)
CREAITE = re.compile(r"(?<![\w.%-])creaite\s{0,5}:[\s/\\]{0,8}([a-z]{1,20})(?=\s{0,5}[/\\?]\S)", re.I)   # a creaite: link's kind
SCHEME = re.compile(r"(?<![\w.%-])creaite\s{0,5}:", re.I)
LINK_KINDS = {"item", "items", "person"}          # creaite links a client report may hold (when what they name is client-safe)
ITEM_LINK = re.compile(r"(?<![\w.%-])creaite\s{0,5}:[\s/\\]{0,8}items?\s{0,5}(?:[/\\]|\?[a-z]{0,10}=)\s{0,5}"
                       r"([^\s)>\]\"'<]{0,200}(?:[ \t]+[A-Za-z0-9][^\s)>\]\"'<]{0,200}){0,2})", re.I)


LONG_TOKEN = 2000                                     # the longest address the gate reads; a longer one fails closed


def _decoded(text):
    """Text with %-encoding and HTML entities undone until it stops changing (at most DECODE_LEVELS times) and entities undone
    once more, then normalised as the ID check reads it (edit_ai.normal)."""
    import edit_ai
    import html
    t = text or ""
    for _ in range(DECODE_LEVELS):
        u = _decode_once(t)                           # #127 round 4: an entity-encoded % ("&#37;20") is undone too
        if u == t:
            break
        t = u
    return edit_ai.normal(html.unescape(t))


DECODE_LEVELS = 5
# a run of text that may hold a link address (a scheme's colon, a path's slash, a Markdown link, href, www.) or an encoded one
# (a %XX or an entity); #127 round 4: a relative address and a run of only %XX or only entities are covered (tested), a % or &
# that encodes nothing ("95%") isn't
LINKISH = re.compile(r"[:/\\]|%[0-9a-f]{2}|&#?\w{1,30};|\]\(|href|www\.", re.I)
ADDRESSY = re.compile(r"[a-z][a-z0-9+.-]{1,30}:|\]\(|href|www\.|/", re.I)       # a run that reads as an address, not only encoded
LONG_ADDRESS = (f"a link address too long to check (more than {LONG_TOKEN} characters): link to the page itself rather than a "
                "signed, tracked or prefilled address, then try again")
LONG_RUN = (f"text too long to check: more than {LONG_TOKEN} characters with no space, %- or entity-encoded, that may hide an "
            "address; break it up with spaces or write it plainly, then try again")
LINK_WRAP = re.compile(r"^(?:[^\]\s]{0,300}\]\(<?|[^\s]{0,10}href=[\"']?|<)|[)>\"'.,;:!?*_~|]{1,10}$", re.I)   # around an address
OVER_ENCODED = f"a link address encoded more than {DECODE_LEVELS} times, too many to check: write it plainly, then try again"


def _decode_once(t):
    """One round of decoding: %-encoding, then HTML entities."""
    import html
    from urllib.parse import unquote
    return html.unescape(unquote(t))


def overencoded(text):
    """Whether the text still changes when decoded (_decode_once) after DECODE_LEVELS rounds (_decoded stops there)."""
    t = text or ""
    for _ in range(DECODE_LEVELS + 1):
        u = _decode_once(t)
        if u == t:
            return False
        t = u
    return True


def unreadable_findings(text):
    """#127 review: what the gate can't read is a finding of its own (fails closed, like drop_item_links' LONG_TOKEN): a run of
    more than LONG_TOKEN characters with no space that may hold a link (Word shows its whole address; the gate decodes at most
    LONG_TOKEN of it), and an address still %-encoded after DECODE_LEVELS rounds."""
    out = []
    for m in re.finditer(r"\S+", text or ""):
        token = m.group(0)
        if len(token) <= LONG_TOKEN or not LINKISH.search(token):
            continue
        if len(LINK_WRAP.sub("", token)) > LONG_TOKEN:  # #127 round 4: a link's "[label](" and ")" aren't its address
            out.append(LONG_ADDRESS if ADDRESSY.search(token) else LONG_RUN)
    out = sorted(set(out))
    return out + ([OVER_ENCODED] if overencoded(text) else [])


SCHEME_GAP = re.compile(r"creaite\s{0,5}:\s{0,5}(?=/{0,2}\s{0,5}[a-z]{1,20}\s{0,5}[/\\?]\S)", re.I)   # any space, a no-break one too
# #127 round 4: what drop_item_links joins up before it reads a link: any space or slash between "creaite:" and the link's kind
# ("creaite:/ /item/", "creaite:\\note/"), and any space after a work-item link's slash ("creaite:item/ ABC-A-004", as ITEM_LINK
# reads it); prose such as "creaite: notes/ are kept" is left as it is
LINK_GAP = re.compile(r"creaite\s{0,5}:[\s/\\]{0,8}items?\s{0,5}[/\\]\s{1,5}(?=[A-Za-z0-9])"
                      r"|creaite\s{0,5}:[\s/\\]{0,8}(?=[a-z]{1,20}\s{0,5}[/\\?]\S)", re.I)


def link_addresses(text):
    """Every link address a text holds, decoded (see ADDRESS); a creaite: address split by spaces or a line break is joined first."""
    return [_decoded(next(g for g in m.groups() if g is not None)) for m in ADDRESS.finditer(SCHEME_GAP.sub("creaite:", text or ""))
            if any(g for g in m.groups())]


def address_text(text):
    """The text's link addresses as the checks read them: each as plain words, and a creaite: or relative address (a path in the
    vault, such as documents/…) also as decoded; an https or mailto address only as words, so an external page's path is not
    read as one of creaite's own."""
    out = []
    for a in link_addresses(text):
        if not re.match(r"(?:https?|mailto)\s{0,5}:", a, re.I):
            out.append(a)
        out.append(re.sub(r"[^0-9A-Za-z]+", " ", a).strip())
    return JOIN.join(out)                           # round 7: one address is never read into the next


def with_addresses(text):
    """A text with its link addresses added (address_text), and its %- or entity-encoded words (with_decoded): what a client check
    reads."""
    return with_decoded(joined(text or "", address_text(text)))


def _words_gap(m):
    """A run of punctuation in with_decoded's words form: the first of a sentence's punctuation (, ; . ! ? :) it holds then a space,
    as prose writes it, else a space (#127 round 6: "Quentin, Marlow" reads as it does undecoded, and "internal. Only" never as the
    marker's "internal . only")."""
    p = re.search(r"[,;.!?:]", m.group(0))
    return p.group(0) + " " if p else " "


def with_decoded(text):
    """#127 round 4: a text with, when it holds a % or an & that decoding changes, its decoded form added as plain words (_decoded:
    %-encoding undone to DECODE_LEVELS rounds, entities undone; a text encoded past that is unreadable_findings' finding). An
    encoded word outside any address a link pattern reads ("See Quentin%20Marlow.", an address a space or U+3000 breaks) is then
    found as written. #127 round 5: added twice. Once with its punctuation kept, its web addresses as words (raw_text, so an
    external page's path is never read as one of creaite's own, documents/): the marker is matched there, so "health%5Fdiff" is
    health_diff and "internal, only" stays two words apart. Once as words for the names and IDs, any other run of punctuation a
    space but one holding a sentence's punctuation (, ; . ! ? :) that punctuation and a space (_words_gap), so the marker can't be
    read across it."""
    t = text or ""
    if "%" not in t and "&" not in t:
        return t
    import edit_ai
    d = _decoded(t)
    if d == edit_ai.normal(t):
        return t
    kept = raw_text(d)
    words = re.sub(r"[\W_]+", _words_gap, d).strip()
    return joined(t, kept, words)                   # round 7: JOIN between, so nothing is read across two forms


def creaite_kinds(text):
    """The kinds of creaite: link a text holds ("item", "person", "note", …), in lower case."""
    return {m.group(1).lower() for m in CREAITE.finditer(_decoded(text))}


def item_links(text):
    """The address after creaite:item/ (or items/, //item/, item?id=, a backslash) of every work-item link in a text, decoded."""
    return [m.group(1) for m in ITEM_LINK.finditer(_decoded(text))]


def link_refs(con, text):
    """({item IDs the text's work-item links name}, [addresses with no ID creaite can read]): each address read as edit_ai.loose_ids
    reads a bare ID."""
    import edit_ai
    ids, unread = set(), []
    for a in item_links(text):
        got = edit_ai.loose_ids(con, a)
        ids |= got
        if not got:
            unread.append(a)
    return ids, unread


def _link_ok(con, code, span, blocking):
    """Whether a link (its whole Markdown or HTML, or a bare address) may stay in a client text: one that isn't a creaite: link,
    or a creaite: link whose every item, read from the whole link, is this project's and one a client report may show. A creaite:
    link that names no item (unreadable, or a person or a note) goes."""
    import edit_ai
    t = _decoded(span)
    if overencoded(span) and "creaite" in t.lower():      # #127 review: encoded past what the gate decodes: fails closed
        return False
    if not SCHEME.search(t):
        return True
    ids = edit_ai.loose_ids(con, t)
    return bool(ids) and all(i.split("-")[0] == code and not item_problem(con, i, blocking) for i in ids)


LINK_SPAN = re.compile(
    r"<a\s[^<>]{0,2000}>[^<]{0,2000}</a\s{0,5}>|<a\s[^<>]{0,2000}>"                                     # an HTML link
    r"|!?\[[^\[\]\n]{0,300}\]\(\s{0,20}(?:<[^<>\n]{0,2000}>|[^()\n]{0,2000}(?:\([^()\n]{0,200}\)[^()\n]{0,2000})?)"
    r"(?:\s{1,20}\"[^\"\n]{0,300}\")?\s{0,20}\)"                                                           # an inline link or image
    r"|^[ \t]{0,3}\[[^\[\]\n]{1,300}\]:[^\n]{0,2000}$"                                                     # a reference definition
    r"|!?\[[^\[\]\n]{0,300}\]\[[^\[\]\n]{0,300}\]"                                                          # a reference link
    r"|<[a-z][a-z0-9+.-]{1,30}:[^<>\s]{1,2000}>",                                                          # an <auto> link
    re.I | re.M)
REF_DEF = re.compile(r"^[ \t]{0,3}\[([^\[\]\n]{1,300})\]:[ \t]{0,20}([^\n]{0,2000})$", re.M)
LINKED = re.compile(r"creaite\s{0,5}:.", re.I | re.S)    # a word holding a creaite: scheme with something after it


def drop_item_links(code, text, con=None):
    """#127: a client text with every creaite: link that a client may not have taken out WHOLE, words and address: a link to an
    item a client report may not show (not client-visible, Sensitive, partner-only or excluded by a label, another project's) or
    one that names no item creaite can read (a person, a note), in any form (inline links and images, reference links and their
    definitions, HTML links, <auto> and bare addresses, %- or entity-encoded, split by spaces or a line break). A link to an item
    a client may see is kept as it is, words included; other links are left. Linear: every pattern is bounded, and a run of more
    than LONG_TOKEN characters with no space that mentions creaite is dropped (fails closed). report.current_context uses it on
    the Current state for the client audience (one helper, so a later filter can replace it)."""
    import edit_ai
    import html
    con = con or connect()
    blocking = blocking_labels(con)
    t = edit_ai.unseen(html.unescape(text or ""))         # #127 round 4: an invisible character hides no link
    t = LINK_GAP.sub(lambda m: re.sub(r"\s+", "", m.group(0)), t)
    bad = {m.group(1).strip().lower() for m in REF_DEF.finditer(t) if not _link_ok(con, code, m.group(2), blocking)}

    def keep(m):
        """The span as it is, or "" when it is a link a client may not have."""
        s = m.group(0)
        ref = re.fullmatch(r"!?\[[^\[\]\n]*\]\[([^\[\]\n]*)\]|[ \t]*\[([^\[\]\n]+)\]:.*", s, re.S)
        if ref:
            return "" if (ref.group(1) or ref.group(2) or "").strip().lower() in bad else s
        return s if _link_ok(con, code, s, blocking) else ""

    t = LINK_SPAN.sub(keep, t)

    def token(m):
        """A word as it is, or "" when it is (or may be: too long to read) a creaite: link a client may not have. A bare
        "creaite:" with nothing after it is prose (#127 review), not a link."""
        s = m.group(0)
        low = _decoded(s[:LONG_TOKEN + 1]).lower()
        if "creaite" not in low or (len(s) <= LONG_TOKEN and not LINKED.search(low) and not overencoded(s)):
            return s
        return "" if len(s) > LONG_TOKEN or not _link_ok(con, code, s, blocking) else s
    return re.sub(r"\S+", token, t)


def findings(doc, con=None):
    """What would leak if this client document were approved or exported: [sentence]; [] when it is safe. An internal document has
    none."""
    if (doc.get("audience") or "internal") == "internal":
        return []
    con = con or connect()
    blocking = blocking_labels(con)
    code, text = doc.get("project") or "", with_decoded(doc_text(doc))     # #127 round 4: encoded words read too
    bad = {r: why for r, why in ((r, item_problem(con, r, blocking)) for r in sorted(refs(doc))) if why}
    found = list(bad.values()) + text_findings(con, code, text, skip=bad)
    found += [f"it holds {why}" for why in internal_findings(con, code, doc)]             # #123: the gate at the end, any route
    import creaite_doc                                     # #127 review: an address too long or too encoded, as stored
    found += [f for f in unreadable_findings(raw_strings(creaite_doc.clean(doc))) if f not in found]
    return found + name_findings(con, code, text, blocking)


def marked(text):
    """Whether a text holds an internal-only marker (drafts.INTERNAL_MARK), read as the ID check reads text (edit_ai.normal: an
    invisible character or a look-alike dash hides none; #127 round 4)."""
    import drafts
    import edit_ai
    return bool(drafts.INTERNAL_MARK.search(edit_ai.normal(as_shown(text))))       # round 6: as the exports show it too


HEALTH_FLAG = re.compile(r"\s*(?:ON TRACK|AT RISK|OFF TRACK)\b")      # a Word report's health line starts with its flag, in capitals


def plain_findings(con, code, text):
    """#127: the gate at the end for a client text with no sections (a Word client report or client-safe steerco one-pager, read by
    review.client_findings): the same checks findings runs on a creaite document (items by ID, internal wording, the internal
    health reason or an internal-only marker, and the names). As M1 lets the health reason stand in the health section, it may
    stand in the report's own health line: the first line that starts with its health flag (report.py's HEALTH_LINE: "OFF TRACK
    …"), never a line that only shares the reason's words; anywhere else, or in a report with no health line, it is found. A
    marker is found anywhere."""
    import drafts
    lines = text.splitlines()
    shown = next((i for i, ln in enumerate(lines) if HEALTH_FLAG.match(ln)), None)
    text = with_addresses(text)       # #127: every link address in the text, decoded; round 4: its %- or entity-encoded words too
    found = drafts.internal_findings(con, code, with_addresses("\n".join(ln for i, ln in enumerate(lines) if i != shown)))
    if marked(text) and "an internal-only marker" not in found:
        found.append("an internal-only marker")
    return text_findings(con, code, text) + [f"it holds {why}" for why in found] + name_findings(con, code, text)


def _raw_split(clean, health_ids):
    """(the stored strings of everything but the health sections' words, of the health sections' words) of a cleaned document
    (#127 review: as raw_text and the addresses read them)."""
    sections = clean.get("sections") or []
    health = [s for s in sections if s.get("id") in health_ids]
    rest = _strings([s for s in sections if s.get("id") not in health_ids]) + [s.get("heading") or "" for s in health] \
        + _strings(clean.get("items") or {})
    return "\n".join(rest), "\n".join(_strings(health))


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
    raw, health_raw = _raw_split(clean, health_ids)
    rest = "\n\n".join([clean.get("title") or ""] + [f"{h}\n\n{t}" if i not in health_ids else h for i, h, t in shown]) \
        + "\n" + json.dumps(clean.get("items") or {}, ensure_ascii=False) + "\n" + raw_text(raw) + _addresses(raw)
    health += "\n" + raw_text(health_raw) + _addresses(health_raw)   # #127 review: the stored words and addresses too
    found = drafts.internal_findings(con, code, with_decoded(as_shown(rest)))   # round 4: encoded words; round 6: as shown
    health = with_decoded(health)
    if marked(health) and "an internal-only marker" not in found:
        found.append("an internal-only marker")
    return found
