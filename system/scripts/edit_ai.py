"""creaite AI on selected text (BL-301 D): the options, the prompt, and the plain-code check on every suggestion.

A suggestion is never a write. The page sends the selected text, the option and the project; plain code here builds the prompt
from those and from the project's name, people and open item IDs only (nothing else from the vault); the live server runs
Claude headless with no tools at all (`/api/edit/ai`, run kind "edit-ai"); the reply is parsed and checked here, and the page
shows it as a suggestion that changes nothing until Alan accepts it.

  python3 system/scripts/edit_ai.py context    JSON {option, text, code, place, instruction, document?} on stdin → {prompt,
                                               option, label, format} or {refused}
  python3 system/scripts/edit_ai.py result     JSON {request, context, reply} on stdin → {text, notes, option}
  python3 system/scripts/edit_ai.py options    each place's options, as JSON

The client place (#123) is the client sheet's: its facts are only the open items a client report may show (client_leak.item_problem
passes them: client-visible, not Sensitive, partner-only or excluded by a label, a milestone with client wording) and no people at
all; selected text that already holds something a client mustn't see is refused before anything goes to Claude; and a suggestion
that brings in an item a client may not see, internal wording (client_leak.text_findings), the tracker's internal health reason or
an internal-only marker (drafts.internal_findings), a person the text and the client-visible items don't name, or the word VIP comes
back with no text and a plain reason.

The place is the server's to decide, never the page's (#123, Jarvis): the client sheet sends the report it is editing as
`document` {kind, code, week_ending, client}; a request that names a document gets the client place whatever place it claims,
once plain code here has checked it is a client report of that project (bound_place). It fails closed: a request that claims the
client place without a document, or whose document isn't a client report, names another project, has a date or project creaite
doesn't know, or is saved but can't be read, is refused before anything goes to Claude. A request with no document keeps the
place it names (the weekly sheet, the minutes, Notes and the rest, as before).

The check (BL-106's plain-code check, as Make it executive's): every date, number, person's name and item ID the suggestion
loses or adds is a note under it. Notes, never blocks. Counts go to draft-stats.json under the feature "edit" (the page posts
/api/draft/stat): offered, used (accepted) and rejected (discarded); never text.
"""
import json
import re
import string
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
import status_checks  # noqa: E402

MAX_TEXT = 12000            # characters of selected text
MAX_INSTRUCTION = 400       # "Or say what you want…"
MAX_IDS, MAX_PEOPLE = 60, 40
OPEN = (("actions", "('Open','Delayed')"), ("raid", "('Open')"), ("decisions", "('Pending')"), ("milestones", "('Planned')"))
ID_RE = re.compile(r"\b[A-Z][A-Z0-9]{2,6}-(?:[A-Z]-)?\d{3}\b")
CODE_RE = re.compile(r"[A-Z][A-Z0-9]{2,6}")

# id: (the menu's name, what it does, the instruction Claude is given)
OPTIONS = {
    "rewrite": ("Rewrite clearly", "The same points, in plainer words",
                "Rewrite the text so it reads clearly: plain words, short sentences, the same points in the same order."),
    "shorter": ("Shorter", "About half the length; the facts kept",
                "Make the text shorter, about half its length. Keep every date, number, name and item ID that matters."),
    "longer": ("Longer", "Fuller sentences; adds no facts",
               "Make the text a little longer and fuller, so each point is explained. Add no facts: no new dates, numbers, "
               "names, items or claims that the text doesn't already hold."),
    "executive": ("Make it executive", "The executive voice: the position and what matters first",
                  "Rewrite the text in the executive voice below: bottom line first, quantified, names and dates, outcomes before "
                  "activities. Keep its facts and add none."),
    "spelling": ("Fix spelling and grammar", "British English; nothing else changed",
                 "Correct the spelling, grammar and punctuation only, in British English. Change nothing else: not the wording, "
                 "the order or the formatting."),
    "format": ("Format nicely", "Sub-headings, lists and bold where they help",
               "Format the text so it is easy to scan: short paragraphs, bulleted or numbered lists and sub-headings where they "
               "help, bold for the few key words. Keep the words themselves."),
    "checklist": ("Turn into a checklist", "One task a line, to tick off",
                  "Turn the text into a checklist: one task a line, each starting with a verb, written as Markdown task items "
                  "(\"- [ ] \"). Keep the owner and date with a task when the text gives them."),
    "summary": ("Summarise at the top", "A short summary first; the text kept below it",
                "Write a two- or three-sentence summary of the text, as a paragraph that starts with \"**Summary.**\", then a blank "
                "line, then the text exactly as it was."),
    "polish": ("Polish", "Spelling, grammar and a lighter touch on the wording; the facts and length kept",
               "Polish the text: correct spelling, grammar and punctuation in British English, and smooth awkward wording lightly. "
               "Keep its facts, its order, its length and its voice; add and remove nothing."),
    "formal": ("More formal", "A more formal tone for the email",
               "Rewrite the text in a more formal, professional tone. Keep its facts and its length."),
    "warmer": ("Warmer", "A warmer, friendlier tone for the email",
               "Rewrite the text in a warmer, friendlier tone, still professional. Keep its facts and its length."),
    "custom": ("Or say what you want…", "Your own instruction", ""),
}
# Each place chooses its options (BL-301 D). "plain": the peek's fields and Prep's boxes (plain text, so no formatting);
# "current": Current state (no checklists or tables, which the Word reports can't take); "notes": a note (everything);
# "email": the Draft email (More formal and Warmer added); "line": a one-line field, the peek's title (Alan, 14-10-2026: the
# suggestion stays one line, and Accept never breaks it).
PLACES = {
    "notes": ["rewrite", "shorter", "longer", "executive", "spelling", "format", "checklist", "summary", "custom"],
    "current": ["rewrite", "shorter", "longer", "executive", "spelling", "format", "summary", "custom"],
    "plain": ["rewrite", "shorter", "longer", "executive", "spelling", "custom"],
    "email": ["rewrite", "shorter", "longer", "formal", "warmer", "spelling", "custom"],
    "line": ["rewrite", "shorter", "executive", "spelling", "custom"],
    "report": ["shorter", "executive", "polish", "custom"],      # v2.1.0 P5: the A4 sheet (reports and minutes)
    "minutes": ["shorter", "executive", "polish", "custom"],
    "client": ["shorter", "executive", "polish", "custom"],      # #123: the client sheet (client-safe facts and reply check)
    "readonly": [],      # a sheet that can't be edited offers only Find the source, which is the page's own and runs no Claude
}
FORMATS = {"notes": "markdown", "current": "markdown", "plain": "plain", "email": "plain", "line": "line", "report": "markdown",
           "minutes": "markdown", "client": "markdown", "readonly": "plain"}
CLIENT_PLACES = {"client"}
CLIENT_RULE = ("This text is for the client. Use only what the text holds and the item IDs listed below; never add an internal "
               "health view or its reason, internal-only wording, or anyone's name the text doesn't already give.")
FORMAT_RULES = {
    "markdown": "The text is Markdown. Reply in Markdown, using only bold, italic, \"- \" bullets, numbered lists, \"### \" "
                "sub-headings, quotes, links{tasks}. Keep any link, image or HTML comment exactly as it is.",
    "plain": "The text is plain text, one paragraph a line. Reply in plain text: no Markdown, no bullets or symbols that weren't "
             "there, one paragraph a line.",
    "line": "The text is one line: a title. Reply with one line of plain text only: no line breaks, no Markdown, no bullets.",
}


def one_line(text):
    """A one-line field's suggestion: every line break and the spaces round it become one space."""
    return re.sub(r"\s*[\r\n]+\s*", " ", text or "").strip()


class Refused(Exception):
    """The request can't be suggested on (an unknown option or place, no text, too long)."""


def options():
    """Each place's options, as the page lists them: {place: [{id, name, line}]}."""
    return {p: [{"id": o, "name": OPTIONS[o][0], "line": OPTIONS[o][1]} for o in ids] for p, ids in PLACES.items()}


def project_facts(code, client=False):
    """The project's name, its people (owners of its open items) and its open item IDs, nothing else (BL-301 D). For a client place
    (#123): only the open items client_leak.item_problem passes, and no people."""
    if not code or not CODE_RE.fullmatch(code) or not paths.DB.exists():
        return {"name": "", "people": [], "ids": []}
    import tracker
    people, ids, name = [], [], code
    try:
        name = tracker.project_label(code)
        con = tracker.connect()
        try:
            if client:
                return {"name": name if name != code else "", "people": [], "ids": client_ids(con, code)[:MAX_IDS]}
            for table, open_ in OPEN:
                cols = [r[1] for r in con.execute(f"PRAGMA table_info({table})")]
                owner = "owner" if "owner" in cols else "NULL"
                for i, o in con.execute(f"SELECT id, {owner} FROM {table} WHERE project = ? AND status IN {open_} ORDER BY id",
                                        (code,)):
                    ids.append(i)
                    if o and o != "TBC" and o not in people:
                        people.append(o)
        finally:
            con.close()
    except (Exception, SystemExit):  # noqa: BLE001  an unreadable database: what was read so far
        pass
    return {"name": name if name != code else "", "people": people[:MAX_PEOPLE], "ids": ids[:MAX_IDS]}


def client_ids(con, code):
    """The project's open item IDs a client report may show (client_leak.item_problem passes them)."""
    import client_leak
    blocking = client_leak.blocking_labels(con)
    out = []
    for table, open_ in OPEN:
        sql = f"SELECT id FROM {table} WHERE project = ? AND status IN {open_} AND client_visible = 1 ORDER BY id"
        for (i,) in con.execute(sql, (code,)):
            if not client_leak.item_problem(con, i, blocking):
                out.append(i)
    return out


# #123 review: a client reply's IDs and the word VIP are matched after normalising, so a look-alike, a zero-width character, a
# non-breaking hyphen, lower case or a missing space can't slip an item past the check (client_leak.text_findings matches IDs
# the same way since #127).
LOOK_ALIKE = str.maketrans({**{c: "-" for c in "\u2010\u2011\u2012\u2013\u2014\u2015\u2212\ufe58\ufe63\uff0d"},
                            **{c: "I" for c in "\u0399\u0406\u04c0\u01c0\u0131\u03b9\u0456"},
                            **{c: "V" for c in "\u0474\u0475\u03bd"}, **{c: "P" for c in "\u03a1\u0420\u03c1\u0440"},
                            # #127 review: the other Cyrillic and Greek letters that look Latin (a project code's "АВС")
                            **dict(zip("\u0410\u0412\u0415\u041a\u041c\u041d\u041e\u0421\u0422\u0425\u0430\u0435\u043e\u0441\u0445"
                                       "\u0391\u0392\u0395\u0396\u0397\u039a\u039c\u039d\u039f\u03a4\u03a5\u03a7\u03bf",
                                       "ABEKMHOCTXaeocxABEZHKMNOTYXo"))})
# Between the letters: up to two marks (dots, dashes, underscores; zero-width characters are already gone), each run allowed one
# space after it ("V. I. P."), but never a bare space ("Phase V IP telephony" isn't VIP; #123 review L).
_VIP_GAP = r"(?:[^\w\s]{1,2}\s?|_{1,2})?"
VIP_LOOSE = re.compile(rf"(?<![a-z0-9])v{_VIP_GAP}i{_VIP_GAP}p(?:{_VIP_GAP}s)?(?![a-z0-9])", re.I)
NO_PROJECT, UNCHECKED, REGISTER = "no project", "the check couldn't run", "the people register couldn't be read"


# #127 round 4: characters Word shows as nothing that aren't format characters (Unicode category Cf, all dropped by unseen): the
# combining grapheme joiner, variation selectors, Mongolian free variation selectors, Khmer inherent vowels, Hangul fillers and the
# unassigned U+2065 among the invisible operators.
SHOWN_AS_NOTHING = frozenset([0x034F, 0x115F, 0x2065, 0x1160, 0x17B4, 0x17B5, 0x180B, 0x180C, 0x180D, 0x180F, 0x3164, 0xFFA0]
                             + list(range(0xFE00, 0xFE10)) + list(range(0xE0100, 0xE01F0)))


def unseen(text):
    """Text without the characters Word shows as nothing: every format character (category Cf: zero-width, direction marks and
    isolates, tags, the soft hyphen, the interlinear annotation marks) and SHOWN_AS_NOTHING (#127 round 4)."""
    import unicodedata
    t = text or ""
    if t.isascii():
        return t
    return "".join(c for c in t if ord(c) not in SHOWN_AS_NOTHING and unicodedata.category(c) != "Cf")


def normal(text):
    """Text as the client check matches it: NFKC, invisible characters gone (unseen, before and after NFKC, which can make a
    filler of a compatibility one), dashes and look-alike letters made plain."""
    import unicodedata
    t = unseen(unicodedata.normalize("NFKC", unseen(text))).translate(LOOK_ALIKE)
    return re.sub(r"\d", lambda m: str(unicodedata.decimal(m.group(), 0)), t)      # #127 review: any script's digits, as 0-9


def loose_ids(con, text):
    """Every item ID a text holds, however it is written: the strict form anywhere, and for each of the tracker's project codes,
    any case, with spaces, dots, dashes, underscores, slashes, colons or brackets for its hyphens ("ABC (A) 004"), or run on to a
    word before it ("seeABC-A-004"); with a letter part, the number may also drop its zeros ("ABC-A-4") or write them as O
    ("ABC-A-OO4"), always as a whole number ("ABC-A-40" is ABC-A-040, never ABC-A-004), and not one a slash, colon or dot continues
    ("ABC A 10/09"). A loose match counts only when the tracker holds that ID (#123 review L: "ABC 100 users" isn't ABC-100 when
    there is no ABC-100); it fails closed, so an ID the tracker can't be asked about counts."""
    t = normal(text)
    out = set(ID_RE.findall(t))
    up, sep = t.upper(), r"[\s_.\-/:()]*"
    for (c,) in con.execute("SELECT code FROM projects"):
        for m in re.finditer(rf"{re.escape(c)}{sep}(?:([A-NP-Z]){sep}([0-9O]{{1,3}})|([0-9O]{{3}}))(?![0-9O]|[/:.]\d)", up):
            num = (m.group(2) or m.group(3)).replace("O", "0").zfill(3)
            ref = f"{c}-{m.group(1)}-{num}" if m.group(1) else f"{c}-{num}"
            if ref not in out and in_tracker(con, ref):
                out.add(ref)
    return out


def in_tracker(con, ref):
    """Whether the tracker holds the item `ref`, in whichever table its form names (a form no table has isn't held); True when the
    tracker can't be asked (fails closed)."""
    import tracker
    table = tracker.item_table(ref)
    if not table:
        return False
    try:
        return con.execute(f"SELECT 1 FROM {table} WHERE id = ?", (ref,)).fetchone() is not None
    except Exception:  # noqa: BLE001  a table that can't be read: counted
        return True


def client_problems(code, text, original=""):
    """What a client place's text holds that a client mustn't see, as short reasons ([] when it is client-safe): an item a client
    report may not show (however its ID is written), internal wording (client_leak.text_findings), the tracker's internal health
    reason or an internal-only marker the original didn't hold (drafts.internal_findings), a person neither the original nor the
    client-visible items (and their aliases) name, or the word VIP however it is written. Fails closed: no project is NO_PROJECT,
    a people register that can't be read is REGISTER (#127), and a tracker or a check that can't be read is UNCHECKED."""
    import client_leak
    import drafts
    import tracker
    if drafts.VIP_RE.search(text or "") or VIP_LOOSE.search(normal(text)):
        return ["something private"]
    if not code:
        return [NO_PROJECT]
    try:
        con = tracker.connect()
    except (Exception, SystemExit):  # noqa: BLE001
        return [UNCHECKED]
    try:
        text, original = client_leak.with_addresses(text), client_leak.with_addresses(original)   # #127: link addresses too
        blocking = client_leak.blocking_labels(con)
        found = [why for why in (client_leak.item_problem(con, i, blocking) for i in sorted(loose_ids(con, text))) if why]
        found += client_leak.text_findings(con, code, text or "")
        found += drafts.internal_findings(con, code, text or "", original)
        known = _register_names() + client_leak.project_owners(con, code)
        allowed = names(original, known) | client_leak.people(con, code, blocking)[0]
        found += [f"{n} isn't named in the text" for n in sorted(names(text, known) - allowed)]
    except client_leak.RegisterUnreadable:                # #127: fails closed, with its own message
        found = [REGISTER]
    except (Exception, SystemExit):  # noqa: BLE001  fails closed
        found = [UNCHECKED]
    finally:
        con.close()
    return found


def refusal(found, suggestion=False):
    """The plain message for a client place's problems: no project, a check that couldn't run, or something not client-safe."""
    if found == [NO_PROJECT]:
        return ("The suggestion was dropped: there's no project to check it against." if suggestion else
                "There's no project to check this text against, so nothing was sent to Claude.")
    if REGISTER in found:
        return ("The suggestion was dropped: the people register couldn't be read, so its names couldn't be checked. Fix it in "
                "Settings › People, then try again." if suggestion else
                "The people register couldn't be read, so the names couldn't be checked and nothing was sent to Claude. Fix it in "
                "Settings › People, then try again.")
    if UNCHECKED in found:
        return ("The suggestion was dropped: creaite couldn't check it against the tracker. Try again." if suggestion else
                "creaite couldn't check this text against the tracker, so nothing was sent to Claude. Try again.")
    return ("The suggestion was dropped: it held something that isn't client-safe. Try again." if suggestion else
            "This text already holds something that isn't client-safe. Fix it first; nothing was sent to Claude.")


DOC_KEYS = ("kind", "code", "week_ending", "client")
REPORT_AUDIENCE = {"client": "client", "weekly": "internal"}     # a report's kind gives its audience (report_doc.KINDS)


NOT_CLIENT = "That isn't a client report creaite can check, so nothing was sent to Claude."


def bound_place(req, code, claimed):
    """The place a request gets (#123): the client place for a request naming its client report (checked here, never trusted),
    else the place it claims. Refuses, failing closed, the client place without a document and any document that isn't a client
    report of this project that creaite can find and read."""
    if document_audience(req, code) is None:
        if claimed in CLIENT_PLACES:
            raise Refused("The client report wasn't named, so nothing was sent to Claude. Reload the page and try again.")
        return claimed
    return "client"


def document_audience(req, code, kinds=("client",)):
    """The audience ("client" or "internal") of the report a request names as `document` {kind, code, week_ending, client}, or
    None when it names none (#123; #127: the ✦ on a report section shares it). Plain code decides it from the report itself, never
    from what the page claims: the kind must be one of `kinds`, the project this one, and the report one creaite knows; when it is
    saved, its file must read as that kind, project and audience. Refuses anything else, failing closed."""
    d = req.get("document")
    if d is None or d == "" or d == {}:
        return None
    what = "client report" if tuple(kinds) == ("client",) else "report"
    if not isinstance(d, dict) or set(d) - set(DOC_KEYS) or any(not isinstance(d.get(k, ""), str) for k in DOC_KEYS) \
            or d.get("kind") not in kinds or d.get("kind") not in REPORT_AUDIENCE:
        raise Refused(f"That isn't a {what} creaite can check, so nothing was sent to Claude.")
    if not code or d.get("code") != code:
        raise Refused(f"The {what} and the project don't agree, so nothing was sent to Claude.")
    try:
        ok = _report_found(code, d)
    except (Exception, SystemExit):  # noqa: BLE001  fails closed: an unknown project or date, an unreadable file
        ok = False
    if not ok:
        raise Refused(f"That isn't a {what} creaite can check, so nothing was sent to Claude.")
    return REPORT_AUDIENCE[d["kind"]]


def _report_found(code, d):
    """Whether the document names a report of its kind of this project creaite knows (report_server.target: the project is in the
    tracker and the date is one), and, when it is saved, whether it reads as that project's report of that kind and audience.
    Raises on anything it can't read."""
    import creaite_doc
    import report_doc
    import report_server
    ask = {"kind": d.get("kind"), "code": code, "week_ending": d.get("week_ending") or None, "client": d.get("client") or None}
    kind, dcode, fri, client = report_server.target(ask)
    state, path = report_doc.where(kind, dcode, fri, client)
    if not state:                                         # not saved yet: the draft route builds it from the tracker
        return True
    doc = creaite_doc.read(path)
    return isinstance(doc, dict) and doc.get("kind") == kind and (doc.get("audience") or "internal") == REPORT_AUDIENCE[kind] \
        and doc.get("project") == code


def request(req):
    """The request checked: (option, text, code, place, instruction) or Refused. The place is bound_place's."""
    code = str(req.get("code") or "")
    code = code if CODE_RE.fullmatch(code) else ""
    place = bound_place(req, code, str(req.get("place") or ""))
    option = str(req.get("option") or "")
    if place not in PLACES:
        raise Refused("Not a place creaite knows.")
    if option not in PLACES[place]:
        raise Refused("That option isn't offered here.")
    text = str(req.get("text") or "")
    if not text.strip():
        raise Refused("Select some text first.")
    if len(text) > MAX_TEXT:
        raise Refused(f"That's too much text for one suggestion; select under {MAX_TEXT // 1000}k characters.")
    instruction = " ".join(str(req.get("instruction") or "").split())
    if option == "custom" and not instruction:
        raise Refused("Say what you want done with the text.")
    if len(instruction) > MAX_INSTRUCTION:
        raise Refused(f"Keep the instruction under {MAX_INSTRUCTION} characters.")
    return option, text, code, place, instruction


def context(req):
    """{prompt, option, label, format} for one suggestion: the template filled from the request and the project's facts."""
    option, text, code, place, instruction = request(req)
    fmt = FORMATS[place]
    client = place in CLIENT_PLACES
    bad = client_problems(code, text, text) if client else []
    if bad:
        raise Refused(refusal(bad))
    facts = project_facts(code, client)
    task = OPTIONS[option][2] if option != "custom" else (
        "Do what Alan asks with the text, and only that. His instruction: " + instruction)
    if client:
        task += "\n\n" + CLIENT_RULE
    if option == "executive":
        import report
        task += "\n\nThe executive voice:\n" + report.style_guide()
    template = string.Template((paths.TEMPLATES / "drafts" / "edit-ai.md").read_text(encoding="utf-8"))
    prompt = template.substitute(
        task=task, format_rule=FORMAT_RULES[fmt].format(tasks=", \"- [ ] \" task items" if place == "notes" else ""),
        project=facts["name"] or "none given",
        people=", ".join(facts["people"]) or "none listed",
        ids=", ".join(facts["ids"]) or "none",
        text=text)
    return {"prompt": prompt, "option": option, "label": OPTIONS[option][0], "format": fmt, "place": place,
            "people": facts["people"], "original": text, "code": code}


def parse(reply):
    """The suggestion from the reply: what is between the markers, else the whole reply, trimmed."""
    m = re.search(r"<<<SUGGESTION\s*\n(.*?)\n?SUGGESTION>>>", reply or "", re.S)
    out = m.group(1) if m else (reply or "")
    return out.strip("\n").rstrip()


def names(text, people):
    """The people's names (or aliases) that the text holds, a name inside a longer one found counted once (client_leak.named)."""
    import client_leak
    return client_leak.named(text, people)


def check(original, suggestion, people=()):
    """BL-106's plain-code check on a suggestion: the dates, numbers, names and item IDs it loses or adds, as [{id, note}]."""
    notes = []
    for x in status_checks.kept(ID_RE.sub(" ", original or ""), ID_RE.sub(" ", suggestion or "")):
        notes.append({"id": x["id"], "note": x["note"].replace("The rewrite", "The suggestion").replace("the rewrite",
                                                                                                         "the suggestion")})
    before, after = set(ID_RE.findall(original or "")), set(ID_RE.findall(suggestion or ""))
    if before - after:
        notes.append({"id": "ids-lost", "note": f"It leaves out {', '.join(sorted(before - after)[:5])}."})
    if after - before:
        notes.append({"id": "ids-added", "note": f"It adds {', '.join(sorted(after - before)[:5])}, which your text didn't have: "
                                                 "check it."})
    register = list(people) + _register_names()
    nb, na = names(original, register), names(suggestion, register)
    if nb - na:
        notes.append({"id": "names-lost", "note": f"It leaves out {', '.join(sorted(nb - na)[:3])}."})
    caps = _caps(suggestion) - _caps(original) - {w for n in na for w in n.split()}
    added = (na - nb) | caps
    if added:
        notes.append({"id": "names-added", "note": f"It adds {', '.join(sorted(added)[:4])}, which your text didn't have: check it."})
    return notes


def _register_names():
    """Every name and alias in the people register (drafts.people_names), or none when it can't be read."""
    try:
        import drafts
        return drafts.people_names()
    except Exception:  # noqa: BLE001  the register is optional
        return []


def _caps(text):
    """Capitalised words that aren't a sentence's first word or a common one: names a suggestion may have made up."""
    out = set()
    for sent in re.split(r"(?<=[.!?:])\s+|\n+", text or ""):
        line = re.sub(r"^[-•*#>\s\[\]x]*", "", sent.strip())
        for m in re.finditer(r"\b[A-Z][a-z]{2,}\b", line):
            if m.start() > 0 and m.group() not in status_checks.COMMON_CAPS and m.group() not in ("Summary",):
                out.add(m.group())
    return out


def result(body):
    """{text, notes, option} from {request, context, reply}: the parsed suggestion and its check."""
    ctx = body.get("context") or {}
    text = parse(str(body.get("reply") or ""))
    if ctx.get("format") == "line":                       # a title stays one line, whatever came back
        text = one_line(text)
    if not text.strip():
        return {"text": "", "notes": [], "message": "No suggestion came back."}
    bad = client_problems(ctx.get("code") or "", text, ctx.get("original") or "") if ctx.get("place") in CLIENT_PLACES else []
    if bad:
        return {"text": "", "notes": [], "option": ctx.get("option"), "format": ctx.get("format"), "message": refusal(bad, True)}
    return {"text": text, "notes": check(ctx.get("original") or "", text, ctx.get("people") or []), "option": ctx.get("option"),
            "format": ctx.get("format")}


def main(argv):
    """The context, result and options commands (see the module's docstring)."""
    cmd = argv[0] if argv else ""
    if cmd == "options":
        print(json.dumps(options()))
        return 0
    if cmd not in ("context", "result"):
        print(__doc__)
        return 2
    try:
        body = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        print(json.dumps({"refused": "The request couldn't be read."}))
        return 0
    if not isinstance(body, dict):
        body = {}
    if cmd == "result":
        print(json.dumps(result(body), ensure_ascii=False))
        return 0
    try:
        print(json.dumps(context(body), ensure_ascii=False))
    except Refused as e:
        print(json.dumps({"refused": str(e)}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
