"""creaite AI on selected text (BL-301 D): the options, the prompt, and the plain-code check on every suggestion.

A suggestion is never a write. The page sends the selected text, the option and the project; plain code here builds the prompt
from those and from the project's name, people and open item IDs only (nothing else from the vault); the live server runs
Claude headless with no tools at all (`/api/edit/ai`, run kind "edit-ai"); the reply is parsed and checked here, and the page
shows it as a suggestion that changes nothing until Alan accepts it.

  python3 system/scripts/edit_ai.py context    JSON {option, text, code, place, instruction} on stdin → {prompt, option, label,
                                               format} or {refused}
  python3 system/scripts/edit_ai.py result     JSON {request, context, reply} on stdin → {text, notes, option}
  python3 system/scripts/edit_ai.py options    each place's options, as JSON

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
    "format": ("Add headings and bold", "Sub-headings, lists and bold where they help",
               "Format the text so it is easy to scan: short paragraphs, bulleted or numbered lists and sub-headings where they "
               "help, bold for the few key words. Keep the words themselves."),
    "checklist": ("Pull out the tasks", "Finds the tasks and writes one a line to tick off",
                  "Turn the text into a checklist: one task a line, each starting with a verb, written as Markdown task items "
                  "(\"- [ ] \"). Keep the owner and date with a task when the text gives them."),
    "summary": ("Summarise at the top", "A short summary first; the text kept below it",
                "Write a two- or three-sentence summary of the text, as a paragraph that starts with \"**Summary.**\", then a blank "
                "line, then the text exactly as it was."),
    "polish": ("Polish", "Spelling, grammar and a lighter touch on the wording; the facts and length kept",
               "Polish the text: correct spelling, grammar and punctuation in British English, and smooth awkward wording lightly. "
               "Keep its facts, its order, its length and its voice; add and remove nothing."),
    "notes": ("Format notes", "Rough notes sorted under headings, with bullets; every point kept",
              "Format these rough notes: sort them under short headings with bullets beneath. Keep every point and every date, "
              "number, name and item ID; add nothing and drop nothing. If the text already has headings (a Working session "
              "note's template), keep those headings and file the points under them."),
    "formal": ("More formal", "A more formal tone for the email",
               "Rewrite the text in a more formal, professional tone. Keep its facts and its length."),
    "warmer": ("Warmer", "A warmer, friendlier tone for the email",
               "Rewrite the text in a warmer, friendlier tone, still professional. Keep its facts and its length."),
    "custom": ("Or say what you want…", "Your own instruction", ""),
}
# Each place chooses its options (BL-301 D). "plain": the peek's fields and Prep's boxes (plain text, so no formatting);
# "current": Current state (no checklists or tables, which the Word reports can't take); "notes": a note (everything);
# "email": the Draft email (More formal and Warmer added); "line": a one-line field, the peek's title (Alan, 14-10-2026: the
# suggestion stays one line, and Accept never breaks it). #117: there is no separate spelling option (every option but Ask… also
# corrects spelling, grammar and punctuation, see context()), and "notes" (Format notes) leads where blocks exist: notes and current.
# v2.1.0 switches on the bar for notes and current only (the page's place table, AI_PLACE_TABLE); email, plain and line are listed so
# that v2.2.0 is a switch. "report", "minutes" and "readonly" are the A4 sheet's (v2.1.0 P5), kept exactly as shipped (SHEET_PLACES).
# The client sheet's `client` place (#123) is added here, in FORMATS and in FORMAT_RULES.
PLACES = {
    "notes": ["notes", "rewrite", "shorter", "longer", "executive", "format", "checklist", "summary", "custom"],
    "current": ["notes", "rewrite", "shorter", "longer", "executive", "format", "summary", "custom"],
    "plain": ["rewrite", "shorter", "executive", "custom"],
    "email": ["rewrite", "shorter", "longer", "formal", "warmer", "custom"],
    "line": ["rewrite", "shorter", "executive", "custom"],
    "report": ["shorter", "executive", "polish", "custom"],      # v2.1.0 P5: the A4 sheet (reports and minutes)
    "minutes": ["shorter", "executive", "polish", "custom"],
    "readonly": [],      # a sheet that can't be edited offers only Find the source, which is the page's own and runs no Claude
}
FORMATS = {"notes": "markdown", "current": "markdown", "plain": "plain", "email": "plain", "line": "line", "report": "markdown",
           "minutes": "markdown", "readonly": "plain"}
# The A4 sheet's places (v2.1.0 P5/P6/P8; the client report's sheet is "report"): their option sets, format rules and prompts stay
# exactly as v2.1.0 shipped them. #117 adds nothing here: no spelling sentence (Polish already does that), no new option, and the
# shipped Markdown rule, word for word. A client-safe change to these places is its own item (#123's `client` place), never #117's.
SHEET_PLACES = ("report", "minutes", "readonly")
SPELLING = " Also correct any spelling, grammar and punctuation, in British English."
# The Markdown rule, per place (#117). The heading levels the place may write: a note stores `#` to `###`; Current state is stored
# SHIFTED by two (`###` to `#####`), because a `## ` line ends its `## Current state` section (build_dashboard.py, report.py read to
# the next `## `). The text Claude is given is in the stored levels, so it is told the stored ones; result() also re-levels a stray
# `#` or `##` line for Current state, and the page does too (core/editor.js headsSafe) before anything is written.
_MARKDOWN = ("The text is Markdown. Reply in Markdown, using only bold, italic, \"- \" bullets, numbered lists, {heads} "
             "headings{note}, quotes, links{tasks}. Keep any link, image or HTML comment exactly as it is.")
_PLAIN = ("The text is plain text, one paragraph a line. Reply in plain text: no Markdown, no bullets or symbols that weren't "
          "there, one paragraph a line.")
_LINE = "The text is one line: a title. Reply with one line of plain text only: no line breaks, no Markdown, no bullets."
# v2.1.0's Markdown rule for the sheet, unchanged (no task items: the sheet's reports can't take them)
_SHEET_MARKDOWN = ("The text is Markdown. Reply in Markdown, using only bold, italic, \"- \" bullets, numbered lists, \"### \" "
                   "sub-headings, quotes, links. Keep any link, image or HTML comment exactly as it is.")
FORMAT_RULES = {
    "notes": _MARKDOWN.format(heads="\"# \", \"## \" and \"### \"", note="", tasks=", \"- [ ] \" task items"),
    "current": _MARKDOWN.format(heads="\"### \", \"#### \" and \"##### \"",
                                note=" (never \"# \" or \"## \": a \"## \" line would end this section)", tasks=""),
    "plain": _PLAIN,
    "email": _PLAIN,
    "line": _LINE,
    "report": _SHEET_MARKDOWN,
    "minutes": _SHEET_MARKDOWN,
    "readonly": _PLAIN,
}
# how far a place's stored heading levels are shifted from the editor's 1 to 3 (Current state's are written `###` to `#####`)
HEAD_SHIFT = {"current": 2}
FENCE_RE = re.compile(r"^\s*(```|~~~)")


def relevel(text, place):
    """A place that stores its headings shifted never gets a heading above its lowest level: Current state's `#` and `##` lines
    become `###` and `####` (outside fenced code), so no `## ` line can end the `## Current state` section (#117)."""
    shift = HEAD_SHIFT.get(place)
    if not shift:
        return text
    out, fence = [], False
    for line in (text or "").split("\n"):
        if FENCE_RE.match(line):
            fence = not fence
        m = None if fence else re.match(r"^((?:> {0,4}|>\t)*)(#{1,6})([ \t].*|)$", line)
        if m and len(m.group(2)) <= shift:
            line = m.group(1) + "#" * (len(m.group(2)) + shift) + m.group(3)
        out.append(line)
    return "\n".join(out)


def one_line(text):
    """A one-line field's suggestion: every line break and the spaces round it become one space."""
    return re.sub(r"\s*[\r\n]+\s*", " ", text or "").strip()


class Refused(Exception):
    """The request can't be suggested on (an unknown option or place, no text, too long)."""


def options():
    """Each place's options, as the page lists them: {place: [{id, name, line}]}."""
    return {p: [{"id": o, "name": OPTIONS[o][0], "line": OPTIONS[o][1]} for o in ids] for p, ids in PLACES.items()}


def project_facts(code):
    """The project's name, its people (owners of its open items) and its open item IDs, nothing else (BL-301 D)."""
    if not code or not CODE_RE.fullmatch(code) or not paths.DB.exists():
        return {"name": "", "people": [], "ids": []}
    import tracker
    people, ids, name = [], [], code
    try:
        name = tracker.project_label(code)
        con = tracker.connect()
        try:
            for table, open_ in (("actions", "('Open','Delayed')"), ("raid", "('Open')"), ("decisions", "('Pending')"),
                                 ("milestones", "('Planned')")):
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


def _needs_blocks(option, text):
    """Format notes is offered for a multi-block selection only: two or more non-empty lines."""
    if option == "notes" and sum(1 for ln in text.splitlines() if ln.strip()) < 2:
        raise Refused("Format notes needs two or more paragraphs.")


def request(req):
    """The request checked: (option, text, code, place, instruction) or Refused."""
    place = str(req.get("place") or "")
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
    _needs_blocks(option, text)
    instruction = " ".join(str(req.get("instruction") or "").split())
    if option == "custom" and not instruction:
        raise Refused("Say what you want done with the text.")
    if len(instruction) > MAX_INSTRUCTION:
        raise Refused(f"Keep the instruction under {MAX_INSTRUCTION} characters.")
    code = str(req.get("code") or "")
    return option, text, code if CODE_RE.fullmatch(code) else "", place, instruction


def context(req):
    """{prompt, option, label, format} for one suggestion: the template filled from the request and the project's facts."""
    option, text, code, place, instruction = request(req)
    fmt = FORMATS[place]
    facts = project_facts(code)
    task = OPTIONS[option][2] if option != "custom" else (
        "Do what Alan asks with the text, and only that. His instruction: " + instruction)
    if option != "custom" and place not in SHEET_PLACES:    # every reshape also fixes spelling and grammar (the page says so);
        task += SPELLING                                    # the sheet's prompts stay as v2.1.0 shipped them
    if option == "executive":
        import report
        task += "\n\nThe executive voice:\n" + report.style_guide()
    template = string.Template((paths.TEMPLATES / "drafts" / "edit-ai.md").read_text(encoding="utf-8"))
    prompt = template.substitute(
        task=task, format_rule=FORMAT_RULES[place],
        project=facts["name"] or "none given",
        people=", ".join(facts["people"]) or "none listed",
        ids=", ".join(facts["ids"]) or "none",
        text=text)
    return {"prompt": prompt, "option": option, "label": OPTIONS[option][0], "format": fmt, "place": place,
            "people": facts["people"], "original": text}


def parse(reply):
    """The suggestion from the reply: what is between the markers, else the whole reply, trimmed."""
    m = re.search(r"<<<SUGGESTION\s*\n(.*?)\n?SUGGESTION>>>", reply or "", re.S)
    out = m.group(1) if m else (reply or "")
    return out.strip("\n").rstrip()


def names(text, people):
    """The people's names (or aliases) that the text holds, a name inside a longer one found counted once."""
    low = (text or "").lower()
    found = {p for p in people if p and len(p) > 2 and re.search(rf"\b{re.escape(p.lower())}\b", low)}
    return {p for p in found if not any(p != q and p.lower() in q.lower() for q in found)}   # "Sara" inside "Sara Khan"


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
    text = relevel(text, ctx.get("place"))                 # Current state never gets a `# ` or `## ` line (it would end the section)
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
