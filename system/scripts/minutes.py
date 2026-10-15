"""creaite minutes helper — the deterministic parts of cx-minutes (standard library only).

Commands:
  transcript <file>        print a transcript (.vtt, .docx or .txt) as readable speaker turns
  key --date YYYY-MM-DD --title "<title>" [--transcript <file>] [--event-id <id>]
                           print the meeting key and whether system/processed.txt already has it
  filename --date YYYY-MM-DD --title "<title>"
                           print the file name stem: "YYYY-MM-DD Title" ([CODE] tags and unsafe characters removed)
  filedate <file>          the meeting date and title of a file, as JSON: from its name (creaite's `YYYY-MM-DD Title`, or Teams'
                           `Title-YYYYMMDD[_HHMMSS][UTC][-Meeting Transcript|Recording]`), else the file's own date ("how": "file";
                           stage then flags the items "date-from-file" for Review)
  new [CODE ...]           the files in each project's minutes and transcripts folders (never the others) that are not yet
                           in processed.txt, as JSON: what "process new minutes" works from
  baseline <CODE> --all | --keep-weeks N [--dry-run]
                           mark the project's existing meeting files as already processed, without extracting (setup of a
                           projects folder that already holds meetings): all of them, or only those older than N weeks so
                           the last N weeks are processed. One of the two must be said; never everything by default
  stage <meeting.json>     write the proposal for one meeting to system/staging/ and print its items table
  expected <CODE> [--title "<meeting title>"] [--date YYYY-MM-DD]
                           the open items of project CODE that this meeting is expected to discuss (BL-65), as JSON:
                           its open actions, and its open risks and issues with no response (and, apart, the open
                           RAID items that already have one). Read-only; cx-minutes calls it after matching the
                           project, then proposes updates for those the transcript discusses
  agenda <CODE> --date YYYY-MM-DD --title "<title>"
                           BL-209: the meeting's agenda points, as JSON {"source", "points"}: an agenda file in the project's
                           Agendas folder for that day (its list lines), else the questions on creaite's prep page for it.
                           Empty points: no agenda, so the Coverage step is skipped
  carry <on|off> --key "<meeting key>" --point "<agenda point>"
                           BL-209: carry a point that wasn't covered to the next meeting of the series (its Prep page lists it
                           as "Not covered last time"), or stop carrying it. Writes system/staging/carried.json only
  done-candidates <CODE> <transcript>
                           BL-218: the passages that may show one of project CODE's open items finished (its ID or most of its
                           words with a completion word), as JSON with a hint (Looks done, Maybe done, Not done), the line and
                           the speaker; plain code, for cx-minutes to judge before it proposes a closing update with "done"
  refresh <proposal>       re-extract: rebuild a meeting's proposed items from its (edited) draft minutes. Added,
                           removed and changed items follow the draft; decisions already made are kept where the
                           item still matches. Prints what changed.

meeting.json (written by cx-minutes):
  {"title": "...", "date": "YYYY-MM-DD", "event_id": null, "projects": ["ABC"],
   "draft": "system/staging/drafts/<stem>.docx", "transcript": "inbox/<file>",
   "items": [{"table": "actions", "section": "Actions", "values": {...}, "flags": []}, ...],
   "status_signals": ["..."],
   "coverage": [{"point": "<an agenda point, as `agenda` gave it>", "verdict": "Covered" | "Touched on" | "Not discussed"}]}
  coverage (BL-209) only when `agenda` found points; stage keeps the point's own words (never transcript text) as
  meeting.coverage and refuses a point that isn't on the agenda.
Item sources are set by stage: the minutes copy in the item's own project folder, plus the section.
A promise (BL-125 A) is {"table": "promises", "section": "<speaker, time>", "values": {"project", "promised_by",
  "promised_to", "description", "due_date"}}: something said in passing, so its source is the transcript copy (not the
  minutes), `raised` is the meeting date, and one said again becomes a mention of the open one (or an update if it has
  a new date). An update to an open promise may change status (Done, Dropped) and due_date; refresh leaves promises alone.
A closing update may carry "done" (BL-218): {"strength": "Looks done" | "Maybe done" | "Not done", "quote": "<the words>",
  "who": "<the speaker>", "reason": "…"}; stage marks it for Review with its evidence (a passage not said by the owner or Alan and
  not naming the owner is only Maybe done).
An item may instead update an open item of the meeting's project (BL-65), for something the meeting discussed:
   {"op": "update", "table": "actions" | "raid", "id": "ABC-A-003", "set": {"status": "Closed"},
    "why": "Sara said it was sent", "section": "Actions"}
  actions may change status, due_date and latest_update; RAID items status, response_action and due_date; never the
  owner, title or project (those stay with cx-edit and Review). Stage fills based_on from the item's updated_at, so an
  apply holds a conflict if the item changed after the proposal was made, and refuses (naming the item) an update to
  an item that is closed, in another project or not in the tracker. A new item that matches an open item of the same
  project becomes an update to it when it carries a changed due date, response or update, else only a mention.
A quick note (BL-54) is already filed where it belongs: give "note": "projects/<CODE> <Name>/minutes/YYYY-MM-DD Quick
note - <title>.md" instead of "draft" and "transcript". Nothing is copied or moved, no Word minutes are drafted, and
each item's source is the note plus the section.
"""
import argparse
import difflib
import hashlib
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
try:
    import log as debuglog  # BL-102: the debug log (not `log`: some scripts have a function of that name); optional
except ImportError:
    class debuglog:  # the helper is missing: every call does nothing and the script runs as before
        info = debug = warn = error = exception = staticmethod(lambda *a, **k: None)
        rule = staticmethod(lambda text, *a: "")
        main = staticmethod(lambda script, fn, *a: fn(*a))
import tracker  # noqa: E402  (fingerprint, transcript text)
import docx_tools  # noqa: E402
import extraction  # noqa: E402  (sprint-drafts-extraction: repeats, probably done, vague titles)

RAID_HEADING = "Risks, Issues, Assumptions & Dependencies"
RAID_TYPES = ("Risk", "Issue", "Assumption", "Dependency")
SECTIONS = {"actions": "Action Items", "decisions": "Decisions", "raid": RAID_HEADING, "promises": "Promises"}
RAISED_TABLES = ("actions", "raid", "promises")         # dated by `raised` (the meeting's date); decisions by `date`
ATTRIBUTION = r" — (?:proposed|raised|agreed|owner)\b"


def _section(lines, start, end):
    try:
        i = lines.index(start)
    except ValueError:
        return []
    out = []
    for line in lines[i + 1:]:
        if line == end:
            break
        if line.strip() and line.strip() != docx_tools.NONE:
            out.append(line.strip())
    return out


def parse_draft(path):
    """The items written in a set of minutes: action rows, decisions and typed RAID lines (tracked changes accepted)."""
    parts = docx_tools.read_parts(path)
    xml = next(raw.decode("utf-8") for info, raw in parts if info.filename == "word/document.xml")
    lines = docx_tools.story_text(docx_tools.accept_xml(xml)[0]).splitlines()
    actions = []
    for line in _section(lines, "Action Items", "Open Questions / Escalations"):
        cells = [c.strip() for c in line.split("|")]
        if len(cells) >= 3 and cells[0] != "Owner" and docx_tools.NONE not in cells[:2]:
            due = cells[2]
            if re.fullmatch(r"\d{2}-\d{2}-\d{4}", due):
                due = f"{due[6:]}-{due[3:5]}-{due[:2]}"
            elif due.lower() in ("", "not set"):
                due = None
            actions.append({"owner": cells[0] or "TBC", "text": cells[1], "due": due})
    decisions = [re.split(ATTRIBUTION, d, maxsplit=1)[0].strip()
                 for d in _section(lines, "Decisions", RAID_HEADING)]
    raid = []
    for line in _section(lines, RAID_HEADING, "Action Items"):
        text = re.split(ATTRIBUTION, line, maxsplit=1)[0].strip()
        m = re.match(r"(Risk|Issue|Assumption|Dependency)\s*[:—-]\s*(.+)$", text, re.I)
        raid.append({"type": m.group(1).capitalize() if m else None, "text": m.group(2).strip() if m else text})
    return {"actions": actions, "decisions": decisions, "raid": raid}


def similarity(a, b):
    """How alike two texts are (0 to 1), ignoring case, punctuation and spacing."""
    norm = lambda t: re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (t or "").lower())).strip()  # noqa: E731
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def match(drafted, staged, text_of, cutoff):
    """Pair draft entries with staged items by wording: [(draft entry or None, item or None)]."""
    pairs, used = [], set()
    for d in drafted:
        best = max(((similarity(text_of(d), item_text), i) for i, (item_text, _) in enumerate(staged) if i not in used),
                   default=(0, None))
        if best[1] is not None and best[0] >= cutoff:
            used.add(best[1])
            pairs.append((d, staged[best[1]][1]))
        else:
            pairs.append((d, None))
    pairs += [(None, item) for i, (_, item) in enumerate(staged) if i not in used]
    return pairs


def norm_title(title):
    """A meeting title for matching: lower case, [CODE] tags and punctuation removed, spaces squeezed."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", re.sub(r"\[[^\]]*\]", "", title.lower()))).strip()


def stem(day, title):
    """The file name stem for a meeting: 'YYYY-MM-DD Title', with [CODE] tags and unsafe characters removed."""
    clean = re.sub(r"\[[^\]]*\]", "", title)                 # [CODE] tags: the folder shows the project
    clean = re.sub(r'[\\/:*?"<>|\x00-\x1f]', " ", clean)      # characters not allowed in file names
    clean = re.sub(r"\s+", " ", clean).strip(" .")
    return f"{day} {clean}"


def transcript_text(path):
    """Speaker turns, consecutive lines by the same speaker merged."""
    p = paths.resolve(path)                      # a stored path (projects/… may be in the projects root, BL-85) or an absolute one
    if p.suffix.lower() == ".vtt":
        turns, in_note = [], False
        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line.startswith("NOTE"):            # a NOTE block (creaite's header from the event) runs to the next blank line
                in_note = True
                continue
            if not line:
                in_note = False
                continue
            if in_note or "-->" in line or line == "WEBVTT" or line.isdigit():
                continue
            m = re.match(r"<v ([^>]+)>(.*?)(?:</v>)?$", line)
            who, said = (m.group(1).strip(), m.group(2)) if m else (None, line)
            said = re.sub(r"<[^>]+>", "", said).strip()
            if turns and turns[-1][0] == who:
                turns[-1][1].append(said)
            else:
                turns.append((who, [said]))
        return "\n".join(f"{who}: {' '.join(s)}" if who else " ".join(s) for who, s in turns)
    if p.suffix.lower() == ".docx":
        return teams_docx_text(p)
    return tracker.text_of(p)


def teams_docx_text(p):
    """Teams' Word transcript export: '<id>Name 0:03Text' paragraphs → 'Name (0:03): text', same speaker merged."""
    import docx_tools
    xml = next(raw.decode("utf-8") for info, raw in docx_tools.read_parts(p) if info.filename == "word/document.xml")
    turns, header = [], []
    for line in docx_tools.story_text(xml).splitlines():
        line = re.sub(r"^\d{6,}", "", line.strip())               # Teams' internal speaker IDs
        m = re.match(r"^(.+?) (\d{1,2}:\d{2}(?::\d{2})?)(.*)$", line)
        if m and not re.fullmatch(r"[^\W\d_][\w'’.\- ]{1,60}", m.group(1).strip()):
            m = None                                                # e.g. the date header "September 30, 2026, 8:02AM"
        if not m:
            if line:
                (header if not turns else turns[-1][2]).append(line)
            continue
        who, at, said = m.group(1).strip(), m.group(2), m.group(3).strip()
        if turns and turns[-1][0] == who:
            turns[-1][2].append(said)
        else:
            turns.append((who, at, [said]))
    turns = split_web_format(turns)
    body = "\n".join(who if who.startswith("[") else f"{who} ({at}): {' '.join(x for x in s if x)}"
                     for who, at, s in turns)
    return "\n".join(header + ([body] if body else []))


# Teams' web/copy format: "AW Amy Wood 0 minutes 8 seconds0:08 Amy Wood 0 minutes 8 seconds Text…"
NAME = r"[A-Z][a-z][\w'’\-]*(?: [A-Z][a-z][\w'’\-]*){1,3}"
STAMP = r"(\d+) (minutes?|seconds?)(?: (\d+) seconds?)?(?:\d{1,2}:\d{2}(?::\d{2})?)?"


def split_web_format(turns):
    """Split turns containing web-format speaker markers into separate turns (same speaker merged)."""
    text_all = " ".join(" ".join(s) for _, _, s in turns)
    if not re.search(NAME + " " + STAMP, text_all):
        return turns
    # Speakers: those already known, plus names that follow Teams' initials ("AW Amy Wood 0 minutes…")
    known = {w for w, _, _ in turns}
    known |= {m.group(1) for m in re.finditer(r"\b[A-Z]{1,3} (" + NAME + ") " + STAMP, text_all)}
    # …and names Teams repeats straight after the timestamp ("Alan Carter 41 minutes 58 seconds41:58 Alan Carter …")
    known |= {m.group(1) for m in re.finditer(r"(" + NAME + r") \d+ (?:minutes?|seconds?)(?: \d+ seconds?)?"
                                              r"\d{1,2}:\d{2}(?::\d{2})? \1 ", text_all)}
    names = "|".join(re.escape(n) for n in sorted(known, key=len, reverse=True))
    marker = re.compile(r"(?:\b[A-Z]{1,3} )?(" + names + ") " + STAMP + r"\s?")
    out = []
    for who, at, said in turns:
        text = " ".join(said)
        marks = list(marker.finditer(text))
        if not marks:
            out.append((who, at, said))
            continue
        out.append((who, at, [text[:marks[0].start()].strip()]))
        out.append(("[Recording part 2]", "", []))
        for i, m in enumerate(marks):
            n1, unit, n2 = int(m.group(2)), m.group(3), int(m.group(4) or 0)
            mins, secs = (n1, n2) if unit.startswith("minute") else (0, n1)
            piece = text[m.end():marks[i + 1].start() if i + 1 < len(marks) else len(text)].strip()
            if out[-1][0] == m.group(1):
                out[-1][2].append(piece)
            else:
                out.append((m.group(1), f"{mins}:{secs:02d}", [piece]))
    return [t for t in out if t[0] == "[Recording part 2]" or any(x for x in t[2])]


def file_event_id(path):
    """The calendar event ID in the header of a transcript or chat that creaite loaded from Microsoft 365 (BL-42 phase 3)."""
    import transcripts
    return transcripts.file_event_id(path)


def meeting_key(day, title, transcript=None, event_id=None):
    """The key processed.txt records a meeting under: 'calendar:<event id>' when there is one (also read
    from a transcript file), else 'fp:<day>|<title>|<transcript hash>'.
    """
    if not event_id and transcript and Path(str(transcript)).suffix.lower() in (".vtt", ".txt"):
        event_id = file_event_id(transcript)              # a loaded transcript carries its meeting's event ID: never processed twice
    if event_id:
        return f"calendar:{event_id}"
    content = ""
    if transcript:
        p = paths.resolve(transcript)
        content = hashlib.sha256(p.read_bytes()).hexdigest()[:12] if p.exists() else ""
    return f"fp:{day}|{norm_title(title)}|{content}"


def processed_on(key):
    """The date processed.txt records for a meeting key, or None if it hasn't been processed."""
    if not paths.PROCESSED.exists():
        return None
    for line in paths.PROCESSED.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.split(" | ")]  # keys contain "|" without spaces
        if len(cells) >= 2 and cells[1] == key:
            return cells[0]
    return None


def open_duplicates(con, project, table, text):
    """Open items in the tracker with the same normalised description."""
    norm = re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", (text or "").lower())).strip()
    if table == "actions":
        rows = con.execute("SELECT id, description FROM actions WHERE project = ? AND status IN ('Open','Delayed')",
                           (project,))
    elif table in ("raid", "promises"):                 # BL-125 A: a promise said again is the open one, mentioned
        rows = con.execute(f"SELECT id, description FROM {table} WHERE project = ? AND status = 'Open'", (project,))
    else:
        rows = con.execute("SELECT id, decision FROM decisions WHERE project = ?", (project,))
    return [r[0] for r in rows if re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", r[1].lower())).strip() == norm]


def note_mention(item_ids, source, run, day):
    """Log that open items were raised again (a duplicate skipped at staging), for BL-51's early warnings.
    Append-only, one JSON line per item; never a tracker row."""
    paths.MENTIONS.parent.mkdir(parents=True, exist_ok=True)
    with open(paths.MENTIONS, "a", encoding="utf-8") as f:
        for item_id in item_ids:
            f.write(json.dumps({"at": day, "id": item_id, "run": run, "source": source}, ensure_ascii=False) + "\n")


# What a meeting may change on an open item (BL-65). Never the owner, title or project: those stay with cx-edit and Review.
UPDATE_FIELDS = {"actions": ("status", "due_date", "latest_update"), "raid": ("status", "response_action", "due_date"),
                 # BL-53: a meeting may make or withdraw a decision that was pending, and fill in what it states about it
                 "decisions": ("status", "date", "made_by", "needed_by", "reasoning", "options", "revisit"),
                 # BL-125 A: a promise kept (Done), dropped, or given a new date
                 "promises": ("status", "due_date")}
STILL_OPEN = {"actions": ("Open", "Delayed"), "raid": ("Open",), "decisions": ("Pending",), "promises": ("Open",)}


def update_changes(row, wanted, table):
    """The fields of wanted that would change the row (empty values and unchanged ones are dropped)."""
    return {f: wanted[f] for f in UPDATE_FIELDS[table]
            if wanted.get(f) not in (None, "") and wanted[f] != row.get(f)}


def made_on(table, changes, day):
    """BL-53: a pending decision the meeting makes is dated the day of the meeting, unless the spec gives a date."""
    if table == "decisions" and changes.get("status") == "Made" and not changes.get("date"):
        changes["date"] = day
    return changes


def check_update(rcon, table, item_id, wanted, folders):
    """(row, None) if an update to this item may be staged, else (None, why not). The message names the item."""
    if table not in UPDATE_FIELDS:
        return None, (f"{item_id or '(no id)'}: updates change actions, RAID items, pending decisions and open promises only, "
                      f"not {table}")
    row = tracker.fetch(rcon, table, item_id) if item_id else None
    if row is None:
        return None, f"{item_id or '(no id)'} isn't in the tracker"
    row = dict(row)
    if row["project"] not in folders:
        return None, f"{item_id} belongs to {row['project']}, which isn't one of this meeting's projects"
    if row["status"] not in STILL_OPEN[table]:
        return None, f"{item_id} is {row['status']}; only open items are updated"
    extra = sorted(set(wanted) - set(UPDATE_FIELDS[table]))
    if extra:
        return None, (f"{item_id}: {', '.join(extra)} can't be changed from minutes (a {table} update may change "
                      f"{', '.join(UPDATE_FIELDS[table])}); use cx-edit or Review")
    return row, None


def note_kinds(notes):
    """How many notes of each kind a staging run printed (for the debug log: kinds and counts, never the text of an item)."""
    kinds = {}
    for n in notes:
        k = ("other project" if n.startswith("skipped (") and not n.startswith(("skipped (rejected", "skipped (already"))
             else "rejected before" if n.startswith("skipped (rejected") else "already in the tracker" if n.startswith("skipped (already")
             else "staged as an update" if n.startswith("already in the tracker") else "update refused" if n.startswith("rejected update")
             else "no change" if n.startswith("no change") else "other")
        kinds[k] = kinds.get(k, 0) + 1
    return ", ".join(f"{k} {v}" for k, v in sorted(kinds.items()))


# ===== BL-209 (sprint-insight) ===== Coverage: was the agenda discussed?
VERDICTS = ("Covered", "Touched on", "Not discussed")


def _norm_point(t):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (t or "").lower())).strip()


def _list_lines(text):
    out = []
    for line in (text or "").splitlines():
        m = re.match(r"\s*(?:[-*•]|\d+[.)])\s+(.+)", line)
        if m:
            p = " ".join(m.group(1).replace("**", "").split()).strip()
            if 3 <= len(p) <= 300:
                out.append(p)
    return out


def agenda_points(code, day, title):
    """{"source": vault path or None, "points": [...]}: an agenda file in the project's Agendas folder named for the day (a
    .md, .txt or .docx whose name shares a word with the title, or the only one that day), else the questions on creaite's
    prep page for the meeting (prep-pages.json). Read only."""
    words = set(_norm_point(title).split()) - {"meeting", "the", "and", "with", "weekly", "call"}
    try:
        folder = paths.folder(code, "agendas")
    except (LookupError, ValueError):
        folder = None
    if folder and folder.is_dir():
        same_day = [f for f in sorted(folder.iterdir()) if f.is_file() and f.name.startswith(day) and f.suffix.lower() in (".md", ".txt", ".docx")]
        named = [f for f in same_day if words & set(_norm_point(f.stem[10:]).split())]
        pick = named[0] if named else (same_day[0] if len(same_day) == 1 else None)
        if pick:
            try:
                text = transcript_text(pick) if pick.suffix.lower() == ".docx" else pick.read_text(encoding="utf-8", errors="replace")
            except Exception:  # noqa: BLE001  an unreadable agenda: treated as none
                text = ""
            if pick.suffix.lower() == ".docx":
                text = "\n".join(f"- {ln}" for ln in text.splitlines() if ln.strip())
            pts = _list_lines(text)
            if pts:
                return {"source": paths.rel(pick), "points": list(dict.fromkeys(pts))[:30]}
    try:
        reg = json.loads((paths.STAGING / "prep-pages.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        reg = {}
    for rel, rec in sorted(reg.items(), key=lambda kv: kv[1].get("at", ""), reverse=True):
        if rec.get("day") == day and str(rec.get("key", "")).endswith("|" + title):
            try:
                html = paths.resolve(rel).read_text(encoding="utf-8")
            except (OSError, LookupError, ValueError):
                continue
            m = re.search(r"Questions and asks</h2></summary>(.*?)</details>", html, re.S)
            pts = [re.sub(r"<[^>]+>", "", x).strip() for x in re.findall(r"<li>(.*?)</li>", m.group(1), re.S)] if m else []
            import html as _html
            pts = [_html.unescape(x) for x in pts if x]
            if pts:
                return {"source": rel, "points": pts[:30]}
    return {"source": None, "points": []}


def coverage_of(spec, codes, day, title):
    """(coverage, agenda source, notes): the spec's verdicts kept only for points on the agenda, in its words."""
    raw = spec.get("coverage")
    if not raw:
        return None, None, []
    found = {"source": None, "points": []}
    for code in codes:
        found = agenda_points(code, day, title)
        if found["points"]:
            break
    if not found["points"]:
        return None, None, ["coverage left out: this meeting has no agenda or prep page"]
    known = {_norm_point(p): p for p in found["points"]}
    out, notes = [], []
    for c in raw if isinstance(raw, list) else []:
        point, verdict = (c or {}).get("point"), (c or {}).get("verdict")
        if verdict not in VERDICTS:
            notes.append(f"coverage: \"{str(point)[:60]}\" has no verdict Covered, Touched on or Not discussed; left out")
            continue
        if _norm_point(point) not in known:
            notes.append(f"coverage: \"{str(point)[:60]}\" isn't on the agenda; left out")
            continue
        out.append({"point": known[_norm_point(point)], "verdict": verdict})
    return out, found["source"], notes


def carried_load():
    """The agenda points carried to the next meeting of a series (system/staging/carried.json, BL-209)."""
    try:
        data = json.loads(paths.CARRIED.read_text(encoding="utf-8"))
        return [c for c in data.get("points") or [] if isinstance(c, dict) and c.get("point")]
    except (OSError, ValueError, AttributeError):
        return []


def carry(on, key, point):
    """Carry one agenda point to the series' next meeting, or stop. The meeting and point come from a staged or applied proposal's
    meeting.coverage, so nothing new is extracted. Returns a message."""
    meeting = None
    for p in list(paths.STAGING.glob("proposed-*.json")) + (list(paths.APPLIED.glob("*.json")) if paths.APPLIED.is_dir() else []):
        try:
            m = json.loads(p.read_text(encoding="utf-8")).get("meeting") or {}
        except (OSError, ValueError):
            continue
        if m.get("key") == key:
            meeting = m
            break
    if not meeting:
        raise ValueError("That meeting isn't in creaite's records.")
    hit = next((c for c in meeting.get("coverage") or [] if _norm_point(c.get("point")) == _norm_point(point)), None)
    if not hit:
        raise ValueError("That point isn't in the meeting's coverage.")
    import build_dashboard
    series = build_dashboard.series_of(meeting.get("title") or "")
    keep = [c for c in carried_load() if not (c.get("key") == key and _norm_point(c.get("point")) == _norm_point(point))]
    if on:
        keep.append({"series": series, "point": hit["point"], "key": key, "day": meeting.get("date") or "",
                     "title": meeting.get("title") or "", "projects": meeting.get("projects") or [], "carried": _today().isoformat()})
    paths.CARRIED.parent.mkdir(parents=True, exist_ok=True)
    tmp = paths.CARRIED.with_suffix(".tmp")
    tmp.write_text(json.dumps({"points": keep}, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(paths.CARRIED)
    return f"Carried to the next {meeting.get('title') or 'meeting'}." if on else "No longer carried."


def carried_for(title, day):
    """The points carried to a meeting: those of its series from an earlier day, within 60 days."""
    import build_dashboard
    series = build_dashboard.series_of(title)
    first = (date.fromisoformat(day) - timedelta(days=60)).isoformat()
    return [c for c in carried_load() if c.get("series") == series and first <= (c.get("day") or "") < day]


# ===== BL-260 (fix-minutes-draft) =====
def stage_refused(spec):
    """True (and says why) when a quick note can't be staged: it goes alone and must exist."""
    note = spec.get("note")
    if note and (spec.get("draft") or spec.get("transcript")):
        print("A quick note is staged on its own: give \"note\" without \"draft\" or \"transcript\".")
        debuglog.warn("minutes", "stage refused: a quick note was given with a draft or a transcript")
        return True
    if note and not paths.resolve(note).is_file():
        print(f"Quick note not found: {note}")
        debuglog.warn("minutes", "stage refused: the quick note file was not found")
        return True
    return False


def draft_refused(spec):
    """True (and says why) when a transcript comes without its draft Word minutes, or the named draft doesn't exist:
    otherwise Review shows a minutes row with nothing to open. Only a quick note has no draft."""
    if spec.get("transcript") and not spec.get("draft"):
        print("No draft minutes: run step 3 (docx_tools.py fill) first, then stage again. Nothing staged.")
        debuglog.warn("minutes", "stage refused: a transcript was given with no draft minutes")
        return True
    if spec.get("draft") and not paths.resolve(spec["draft"]).is_file():
        print(f"Draft minutes not found: {spec['draft']}. Run step 3 (docx_tools.py fill) first, then stage again. "
              "Nothing staged.")
        debuglog.warn("minutes", "stage refused: the draft minutes file was not found")
        return True
    return False
# ===== end BL-260 =====


def stage_gate(spec):
    """The refusals, in order (BL-229: out of cmd_stage): (exit code, or None to go on; the meeting key)."""
    day, title = spec["date"], spec["title"]
    if stage_refused(spec):       # BL-260: the quick note checks, moved out of here
        return 1, None
    key = meeting_key(day, title, spec.get("note") or spec.get("transcript"), spec.get("event_id"))
    done = processed_on(key)
    if done:
        print(f"Already processed on {tracker.shown(done)}: {title}. Nothing staged.")
        debuglog.info("minutes", f"stage skipped: the meeting ({key.split(':')[0]} key, {day}) was already processed on {done}")
        return 3, key
    if draft_refused(spec):       # BL-260: never minutes without their Word draft
        return 1, key
    if not spec.get("projects"):
        print("No project matched: leave the file in inbox/ and flag it as Project? with the candidates.")
        debuglog.info("minutes", f"stage skipped: no project matched ({key.split(':')[0]} key, {day})")
        return 1, key
    return None, key


def stage_ops(spec, projects, name):
    """Where the draft and the transcript go for each project, as file operations done on approval: (folders, ops,
    source_map, tcopies)."""
    ext = Path(spec["transcript"]).suffix if spec.get("transcript") else None
    folders, ops, source_map, tcopies = {}, [], {}, {}
    tpath = paths.resolve(spec["transcript"]).resolve() if spec.get("transcript") else None
    in_place = lambda code: bool(tpath) and paths.folder(code, "transcripts").resolve() in (tpath.parent, *tpath.parents)   # noqa: E731
    for code in projects:
        mdir, tdir = paths.rel(paths.folder(code, "minutes")), paths.rel(paths.folder(code, "transcripts"))   # BL-85: the mapped folders
        folders[code] = (mdir, tdir)
        minutes_copy = f"{mdir}/{name}.docx"
        if spec.get("draft"):
            ops.append({"op": "copy", "from": "draft", "to": minutes_copy})
        if spec.get("transcript"):
            if in_place(code):                 # Alan's own file, already in the project's transcripts folder: never copied, moved or renamed
                tcopies[code] = spec["transcript"]
            else:
                tcopies[code] = f"{tdir}/{name}{ext}"
                ops.append({"op": "copy", "from": "transcript", "to": tcopies[code]})
            source_map[minutes_copy] = tcopies[code]
    if spec.get("transcript") and not any(in_place(code) for code in projects):
        ops.append({"op": "remove", "path": spec["transcript"]})
    if spec.get("draft"):
        ops.append({"op": "remove", "path": spec["draft"]})
    return folders, ops, source_map, tcopies


class Staging:
    """The items one meeting stages (BL-229: out of cmd_stage): new items, updates to open items, and notes on what was
    skipped."""

    def __init__(self, spec, key, name, folders, tcopies):
        self.spec, self.key, self.name, self.folders, self.tcopies = spec, key, name, folders, tcopies
        self.day, self.title, self.note = spec["date"], spec["title"], spec.get("note")
        self.ext = Path(spec["transcript"]).suffix if spec.get("transcript") else None
        self.date_from_file = bool(spec.get("transcript")) and paths.file_date(spec["transcript"])[1] == "file"   # a dateless name (BL-85)
        self.con = tracker.connect()
        self.rcon = tracker.connect()          # rows by name, for the open items an update touches
        self.con.row_factory = None
        self.rejected = {r[0] for r in self.con.execute("SELECT fingerprint FROM rejected")}
        self.items, self.notes, self.updated = [], [], {}

    def mention(self, ids):
        """Log open items raised again (BL-51). BL-301 E: Find updates' staging collects them instead and logs them only for the
        rows Alan applies or saves."""
        note_mention(ids, self.key, "cx-minutes", self.day)

    def source_for(self, project, section, table):
        """Where an item came from: the note, the filed minutes, or the filed transcript, and the section. A promise cites the
        transcript when there is one: it was said in passing, so it isn't in the minutes (BL-125 A)."""
        cite_minutes = self.spec.get("draft") and not (table == "promises" and self.ext)
        where = self.note or (f"{self.folders[project][0]}/{self.name}.docx" if cite_minutes else
                              self.tcopies.get(project) or f"{self.folders[project][1]}/{self.name}{self.ext}")
        return f"{where} — {section or SECTIONS.get(table, RAID_HEADING)}"

    def stage_update(self, table, row, changes, why, source):
        """One update item for an open item; two for the same item in one meeting are merged."""
        if row["id"] in self.updated:
            at = self.updated[row["id"]]
            at["changes"] = {**changes, **at["changes"]}
            at["why"] = " · ".join(x for x in (at.get("why"), why) if x)
            return
        item = {"op": "update", "table": table, "id": row["id"], "changes": changes, "based_on": row["updated_at"],
                "why": why or "", "source": source, "n": len(self.items) + 1, "match": "strong", "flags": [],
                "decision": "pending"}
        self.items.append(item)
        self.updated[row["id"]] = item

    def take(self, raw):
        """One item from the spec: an update to an open item, or a new one."""
        if raw.get("op") == "update":                                       # BL-65: something the meeting discussed
            self.take_update(raw)
        else:
            self.take_new(raw)

    def take_update(self, raw):
        """An update the meeting discussed (BL-65), checked against the open item."""
        table, item_id = raw.get("table"), str(raw.get("id") or "")
        wanted = dict(raw.get("set") or {})
        row, why_not = check_update(self.rcon, table, item_id, wanted, self.folders)
        if why_not:
            self.notes.append(f"rejected update: {why_not}")
            return
        self.mention([item_id])                                          # discussed again: BL-51
        changes = made_on(table, update_changes(row, wanted, table), self.day)
        if not changes:
            self.notes.append(f"no change to {item_id} (already as the meeting left it); logged as discussed")
            return
        self.stage_update(table, row, changes, raw.get("why"),
                          raw.get("source") or self.source_for(row["project"], raw.get("section") or "Updates", table))

    def new_values(self, raw, table):
        """The new item's values with the meeting's defaults and its source."""
        values = dict(raw.get("values") or {})
        if table == "decisions":                      # BL-53: a decision needed is Pending and has no date until it is made
            values["status"] = values.get("status") or "Made"
            if values["status"] == "Pending":
                values.pop("date", None)
            else:
                values.setdefault("date", self.day)
        else:
            values.setdefault("raised" if table in RAISED_TABLES else "date", self.day)
        values["source"] = self.source_for(values["project"], raw.get("section"), table)
        return values

    def take_new(self, raw):
        """A new item, unless it is for another project, was rejected before, or is already open."""
        table = raw.get("table")
        project = (raw.get("values") or {}).get("project")
        if project not in self.folders:
            self.notes.append(f"skipped ({project}): not one of this meeting's projects — {dict(raw.get('values') or {})}")
            return
        values = self.new_values(raw, table)
        item = {"op": "new", "table": table, "values": values}
        if tracker.fingerprint(item) in self.rejected:
            self.notes.append(f"skipped (rejected before): {values.get('description') or values.get('decision')}")
            return
        dupes = open_duplicates(self.con, project, table, values.get("description") or values.get("decision"))
        if dupes:
            self.as_duplicate(table, values, dupes)
            return
        self.items.append({**item, "n": len(self.items) + 1, "match": raw.get("match", "strong"),
                           "flags": self.flags(raw, table, values), "decision": "pending"})
        import review as _review                          # BL-208: the fields cx-minutes guessed, and why
        if _review.clean_inferred(raw.get("inferred")):
            self.items[-1]["inferred"] = _review.clean_inferred(raw.get("inferred"))
        tracker.flag_workstream(self.con, self.items[-1])           # BL-58: the project's own workstreams only

    def as_duplicate(self, table, values, dupes):
        """An item already open: what changed goes to the first as an update, never a second item (BL-65)."""
        text = values.get("description") or values.get("decision")
        self.mention(dupes)                                       # raised again: BL-51
        row = dict(tracker.fetch(self.rcon, table, dupes[0])) if table in UPDATE_FIELDS else None
        if row and table == "decisions" and row["status"] != "Pending":
            row = None                                   # only a pending decision is made by a later meeting
        changes = made_on(table, update_changes(row, values, table), self.day) if row else {}
        if changes:
            self.stage_update(table, row, changes, f"Raised again in {self.title}", values["source"])
            self.notes.append(f"already in the tracker as {dupes[0]}, so staged as an update to it "
                              f"({', '.join(changes)}): {text}")
        else:
            self.notes.append(f"skipped (already in the tracker as {', '.join(dupes)}): {text}")

    def flags(self, raw, table, values):
        """The item's flags, with no owner, no due date and a dateless transcript added."""
        flags = list(raw.get("flags") or [])
        if table == "actions" and values.get("owner", "TBC") == "TBC" and "no-owner" not in flags:
            flags.append("no-owner")
        if table in ("actions", "promises") and not values.get("due_date") and "no-due-date" not in flags:
            flags.append("no-due-date")                   # BL-125 A: a promise with no date is never overdue
        if self.date_from_file and "date-from-file" not in flags:
            flags.append("date-from-file")                # BL-85: the transcript's name has no date; Review shows it
        return flags


def stage_proposal(spec, key, projects, ops, source_map, staging):
    """The proposal cx-minutes stages for one meeting (BL-229: out of cmd_stage)."""
    day, title = spec["date"], spec["title"]
    coverage, agenda_src, cov_notes = coverage_of(spec, projects, day, title)       # BL-209: the agenda's points only
    staging.notes += cov_notes
    proposal = {
        "created": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "source_run": "cx-minutes",
        "files": [f for f in (spec.get("draft"), spec.get("transcript")) if f],
        "meeting": {"key": key, "title": title, "date": day, "projects": projects,
                    "draft": spec.get("draft"), "transcript": spec.get("transcript"),
                    "minutes_decision": "pending", "file_ops": ops, "source_map": source_map,
                    **({"date_from_file": True} if staging.date_from_file else {}),
                    **({"coverage": coverage, "agenda": agenda_src} if coverage else {})},
        "items": staging.items,
        "status_signals": spec.get("status_signals", []),
    }
    if spec.get("note"):     # BL-54: no minutes to approve and no files to move; the block only records the note as processed
        proposal["meeting"].update(note=spec["note"], kind="quick note", minutes_decision="approved")
    return proposal


def write_proposal(proposal):
    """Write it to staging under a name not yet taken; return its path."""
    out = paths.STAGING / f"proposed-{datetime.now():%Y-%m-%d-%H%M}.json"
    n = 2
    while out.exists():
        out = paths.STAGING / f"proposed-{datetime.now():%Y-%m-%d-%H%M}-{n}.json"
        n += 1
    out.write_text(json.dumps(proposal, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def log_staged(out, spec, key, projects, staging):
    """One debug log line: what was staged, by kind, and the notes' kinds."""
    by_table = {}
    for it in staging.items:
        k = f"{it['table']}{' updates' if it['op'] == 'update' else ''}"
        by_table[k] = by_table.get(k, 0) + 1
    notes = staging.notes
    debuglog.info("minutes", f"staged {out.name}: {key.split(':')[0]} key, {spec['date']}, projects {', '.join(projects)}, "
                  f"{len(staging.items)} item(s) ({', '.join(f'{k} {v}' for k, v in sorted(by_table.items())) or 'none'})"
                  + (f", notes: {note_kinds(notes)}" if notes else "") + (", quick note" if spec.get("note") else "")
                  + (", draft + transcript copied on approval" if spec.get("draft") and spec.get("transcript") else ""))


def print_staged(out, spec, projects, proposal, notes):
    """What was staged, one line an item, as the file holds it."""
    print(f"Staged {paths.rel(out)} — {spec['title']}, {tracker.shown(spec['date'])} · "
          f"{', '.join(tracker.project_label(c) for c in projects)}")
    if spec.get("draft"):
        print(f"Draft minutes: {spec['draft']}")
    print("# · Project · Type · Description · Owner · Due · Flags")
    data = json.loads(out.read_text(encoding="utf-8"))
    for it in data["items"]:
        if it["op"] == "update":
            shown = "; ".join(f"{f} → {tracker.shown(c) if f in tracker.DATE_FIELDS else c}" for f, c in it["changes"].items())
            print(f"{it['n']} · {it['id'].split('-')[0]} · Update · {it['id']}: {shown}"
                  f"{' (' + it['why'] + ')' if it.get('why') else ''} · · · {', '.join(it.get('flags', []))}")
            continue
        v = it["values"]
        kind = v.get("type") or {"actions": "Action", "decisions": "Decision", "promises": "Promise"}.get(it["table"], it["table"])
        print(f"{it['n']} · {v['project']} · {kind} · {v.get('description') or v.get('decision')} · "
              f"{tracker.who_of(v)} · {tracker.shown(v.get('due_date')) or ''} · {', '.join(it.get('flags', []))}")
    for s in proposal["status_signals"]:
        print(f"Status signal: {s}")
    for note in notes:
        print("Note: " + note)


def cmd_stage(spec_file):
    """Write the proposal for one meeting (from cx-minutes' meeting.json) to system/staging/ and print its items.

    Returns 1 when the extraction checks find a problem (BL-218, BL-220, BL-221); otherwise the spec file is
    deleted once staged (BL-118).
    """
    spec = json.loads(Path(spec_file).read_text(encoding="utf-8"))
    refused, key = stage_gate(spec)
    if refused is not None:
        return refused
    projects = spec["projects"]
    name = stem(spec["date"], spec["title"])
    folders, ops, source_map, tcopies = stage_ops(spec, projects, name)
    staging = Staging(spec, key, name, folders, tcopies)
    for raw in spec.get("items", []):
        staging.take(raw)
    proposal = stage_proposal(spec, key, projects, ops, source_map, staging)
    out = write_proposal(proposal)
    check = extraction.after_stage(out, spec) if staging.items else 0     # BL-221, BL-218, BL-220 (sprint-drafts-extraction)
    log_staged(out, spec, key, projects, staging)
    print_staged(out, spec, projects, proposal, staging.notes)
    if not check:
        paths.consume_draft(spec_file)                      # BL-118: staged and checked, so the spec has done its job
    return 1 if check else 0


def follows_draft(i):
    """Whether refresh rebuilds this staged item from the draft: a new, unapplied action, decision made or RAID item. A
    decision needed (BL-53) and a promise (BL-125 A) aren't in the Word draft, so refresh leaves them alone."""
    return (i.get("op") == "new" and not i.get("applied") and i.get("table") != "promises"
            and not (i.get("table") == "decisions" and (i.get("values") or {}).get("status") == "Pending"))


def cmd_refresh(arg):
    """Re-extract: make a meeting's unapplied items follow its edited draft."""
    prop = tracker.resolve_proposal(arg)
    data = json.loads(prop.read_text(encoding="utf-8"))
    meeting = data.get("meeting") or {}
    draft = meeting.get("draft")
    if not draft or not paths.resolve(draft).is_file():
        print("No draft minutes to refresh from (already filed, or no draft in this proposal).")
        return 1
    if docx_tools.is_open(paths.resolve(draft)):
        print(f"{Path(draft).name} is open in Word. Save and close it, then refresh.")
        debuglog.info("minutes", f"refresh paused: {Path(draft).name} is open in Word")
        return 3
    parsed = parse_draft(paths.resolve(draft))
    items = data.get("items", [])
    live = [i for i in items if follows_draft(i)]
    projects = meeting.get("projects") or []
    project = projects[0] if projects else None
    minutes_copy = next((op["to"] for op in meeting.get("file_ops", []) if op.get("op") == "copy" and op.get("from") == "draft"
                         and project and op["to"].startswith(paths.rel(paths.project_dir(project)))), None)
    source = lambda table: f"{minutes_copy or draft} — {SECTIONS[table]}"  # noqa: E731
    next_n = max([i.get("n", 0) for i in items] + [0]) + 1
    added, removed, updated, unchanged, keep = [], [], [], 0, [i for i in items if i not in live]

    def new_item(table, values, flags):
        """A new pending proposal item for an item added in the draft."""
        nonlocal next_n
        values = {"project": project, **values, "source": source(table)}
        values.setdefault("raised" if table in ("actions", "raid") else "date", meeting.get("date"))
        if len(projects) > 1:
            flags = flags + ["low-confidence"]
        item = {"n": next_n, "op": "new", "table": table, "values": {k: v for k, v in values.items() if v is not None},
                "match": "strong" if project else "unresolved", "flags": flags, "decision": "pending",
                "edited_in": "refresh"}
        next_n += 1
        return item

    def owner_value(staged, drafted):
        """Keep the staged owner when it names the same person as the draft; otherwise the draft's."""
        strip = lambda o: re.sub(r"\s*\([^)]*\)$", "", o or "TBC")  # noqa: E731
        return staged if staged and strip(staged) == strip(drafted) else drafted

    groups = (
        ("actions", parsed["actions"], lambda d: d["text"], 0.75, "description"),
        ("decisions", [{"text": t} for t in parsed["decisions"]], lambda d: d["text"], 0.6, "decision"),
        ("raid", parsed["raid"], lambda d: d["text"], 0.6, "description"),
    )
    for table, drafted, text_of, cutoff, field in groups:
        staged = [(i["values"].get(field, ""), i) for i in live if i["table"] == table]
        for d, item in match(drafted, staged, text_of, cutoff):
            if item is None:
                values = {field: d["text"]}
                flags = []
                if table == "actions":
                    values.update(owner=d["owner"], due_date=d["due"])
                    flags = (["no-owner"] if d["owner"] == "TBC" else []) + ([] if d["due"] else ["no-due-date"])
                if table == "raid":
                    values["type"] = d["type"] or "Risk"
                    flags = [] if d["type"] else ["low-confidence"]
                added.append(new_item(table, values, flags))
                continue
            if d is None:
                removed.append(item)
                continue
            v, before = item["values"], dict(item["values"])
            v[field] = d["text"]
            if table == "actions":
                v["owner"] = owner_value(v.get("owner"), d["owner"])
                if d["due"]:
                    v["due_date"] = d["due"]
                else:
                    v.pop("due_date", None)
            if table == "raid" and d["type"]:
                v["type"] = d["type"]
            if v != before:
                item["edited_in"] = "refresh"
                updated.append((item, before))
            else:
                unchanged += 1
            keep.append(item)
    data["items"] = sorted(keep + added, key=lambda i: i.get("n", 0))
    tracker.stamp_as_proposed(prop, data)           # ===== BL-232 (fix-as-proposed): the first edit keeps what was proposed =====
    prop.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tracker.cmd_validate(str(prop))
    label = lambda i: i["values"].get("description") or i["values"].get("decision")  # noqa: E731
    print(f"Refreshed from {Path(draft).name}: {len(added)} added, {len(removed)} removed, {len(updated)} updated, "
          f"{unchanged} unchanged.")
    debuglog.info("minutes", f"refreshed {prop.name} from {Path(draft).name}: {len(added)} added, {len(removed)} removed, "
                  f"{len(updated)} updated, {unchanged} unchanged")
    for i in added:
        print(f"  + {i['table']}: {label(i)}")
    for i in removed:
        print(f"  − {i['table']}: {label(i)}" + (f" (was {i['decision']})" if i.get("decision") != "pending" else ""))
    for i, before in updated:
        changes = ", ".join(f"{k}: {before.get(k) or '—'} → {i['values'].get(k) or '—'}" for k in i["values"]
                            if i["values"].get(k) != before.get(k))
        print(f"  ~ {i['table']}: {changes}")
    return 0


# ── Expected items (BL-65) ────────────────────────────────────────────────────

def _today():
    import os
    now = os.environ.get("CREAITE_NOW")           # tests fix the clock
    return date.fromisoformat(now[:10]) if now else date.today()


def open_promises(con, code):
    """A project's open promises, soonest due first (BL-125 A): a meeting may say one was kept, dropped or re-dated."""
    cols = ("id", "description", "promised_by", "promised_to", "due_date", "status", "updated_at")
    return [{c: r[c] for c in cols} for r in con.execute(
        "SELECT * FROM promises WHERE project = ? AND status = 'Open' ORDER BY COALESCE(due_date, '9999'), id", (code,))]


def expected_items(code, title="", day=None):
    """What a meeting of project `code` is expected to discuss: its open actions, and its open risks and issues with
    no response, plus the meeting's series (the same logic as meeting prep) and when that series last met."""
    import build_dashboard as bd           # the brief's own matching: series_of, prep_match, prep.series
    con = tracker.connect()
    project = con.execute("SELECT code, name FROM projects WHERE code = ?", (code,)).fetchone()
    if not project:
        raise SystemExit(f"creaite: {code} isn't a project in the tracker")
    projects = [dict(r) for r in con.execute("SELECT code, name FROM projects WHERE active = 1 ORDER BY code")]
    day = day or _today()
    remembered = (paths.load_settings().get("prep") or {}).get("series") or {}
    series = bd.series_of(title)
    matched, how = bd.prep_match(title, projects, remembered) if title else (None, "no title")
    history = []
    for pcode, _ in paths.project_folders():
        for folder in ("minutes", "transcripts"):
            d = paths.folder(pcode, folder)
            history += [{"n": f.name, "f": folder} for f in d.glob("*") if f.is_file()] if d.is_dir() else []
    last = max((d for d, s in bd.past_meetings(history) if series and s == series and d < day.isoformat()), default=None)
    pick = lambda r, cols: {c: r[c] for c in cols}      # noqa: E731
    acts = [pick(r, ("id", "description", "owner", "workstream", "priority", "due_date", "status", "latest_update", "updated_at"))
            for r in con.execute("SELECT * FROM actions WHERE project = ? AND status IN ('Open','Delayed') "
                                 "ORDER BY COALESCE(due_date, '9999'), id", (code,))]
    raid_cols = ("id", "type", "description", "owner", "priority", "due_date", "status", "response_action", "updated_at")
    risks = [pick(r, raid_cols) for r in con.execute(
        "SELECT * FROM raid WHERE project = ? AND status = 'Open' AND type IN ('Risk','Issue') AND "
        "COALESCE(trim(response_action), '') = '' ORDER BY id", (code,))]
    answered = [pick(r, raid_cols) for r in con.execute(
        "SELECT * FROM raid WHERE project = ? AND status = 'Open' AND NOT (type IN ('Risk','Issue') AND "
        "COALESCE(trim(response_action), '') = '') ORDER BY id", (code,))]
    pending = [pick(r, ("id", "decision", "made_by", "needed_by", "status", "reasoning", "options", "revisit", "updated_at"))
               for r in con.execute("SELECT * FROM decisions WHERE project = ? AND status = 'Pending' "
                                    "ORDER BY COALESCE(needed_by, '9999'), id", (code,))]
    promises = open_promises(con, code)                                                                    # BL-125 A
    return {"project": code, "name": project["name"], "meeting": title, "date": day.isoformat(), "series": series,
            "series_project": {"p": matched, "how": how}, "last_meeting": last,
            "since": last or (day - timedelta(days=7)).isoformat(),
            "actions": acts, "risks_and_issues_without_response": risks,
            "other_open_raid": answered, "decisions_needed": pending, "open_promises": promises,
            "how_to_use": "Propose an update (op: update) only for an item the transcript actually discusses, citing it; "
                          "leave the rest alone; never propose one of these again as a new item."}


def processed_meeting(day, title):
    """Is a meeting of this date and title already in processed.txt? (the content part of its key is ignored: a minutes copy and
    its transcript differ in content but are one meeting)"""
    if not paths.PROCESSED.exists():
        return False
    needle = f"fp:{day}|{norm_title(title)}|"
    return any(needle in line for line in paths.PROCESSED.read_text(encoding="utf-8").splitlines() if not line.startswith("#"))


def meeting_files(code):
    """[{path, date, title, how}] for every file in a project's minutes and transcripts folders (never the other folders), oldest
    first. The date is in the name (creaite's or Teams'), else the file's own date. Online-only files are left out."""
    out = []
    for d in paths.extract_dirs(code):
        for f in sorted(d.glob("*")) if d.is_dir() else []:
            if f.is_file() and not f.name.startswith((".", "~$")) and not paths.is_online_only(f):
                day, title, how = paths.name_date(f.name)
                if not day:
                    day, how = paths.file_date(f)
                out.append({"project": code, "path": paths.rel(f), "date": day, "title": re.sub(r"^Quick note - ", "", title), "how": how})
    return sorted(out, key=lambda r: (r["date"], r["path"]))


def cmd_new(codes):
    """The extractable files not yet processed, as JSON: the list cx-minutes works from for \"process new minutes\"."""
    out = []
    for code in codes or [c for c, _ in paths.project_folders()]:
        out += [{**r, "key": meeting_key(r["date"], r["title"], r["path"])} for r in meeting_files(code)
                if not processed_meeting(r["date"], r["title"])]
    print(json.dumps(out, indent=2, ensure_ascii=False))
    away = [f for c, k, f in paths.online_only_files() if k in ("minutes", "transcripts") and (not codes or c in codes)]
    if away:                                         # never read: it would download them
        print(f"Skipped {len(away)} online-only file(s) (not on this device): " + ", ".join(f.name for f in away[:5])
              + (" …" if len(away) > 5 else "") + ". Set the folder to Always keep on this device.", file=sys.stderr)
    return 0


def cmd_baseline(code, all_existing, keep_weeks, dry_run):
    """Mark a project's existing meeting files as already processed, without extracting anything (BL-85, first setup of a projects
    folder that already holds meetings). Either every unprocessed file (--all), or those older than N weeks (--keep-weeks N: the last
    N weeks stay to be processed). One of them must be said: never everything silently."""
    today = _today()
    cutoff = (today - timedelta(weeks=keep_weeks)).isoformat() if keep_weeks is not None else None
    todo = [r for r in meeting_files(code) if not processed_meeting(r["date"], r["title"])]
    mark = [r for r in todo if cutoff is None or r["date"] < cutoff]
    if not dry_run and mark:
        paths.PROCESSED.parent.mkdir(parents=True, exist_ok=True)
        with paths.PROCESSED.open("a", encoding="utf-8") as f:
            for r in mark:
                key = meeting_key(r["date"], r["title"], r["path"])
                f.write(f"{today.isoformat()} | {key} | baseline: existing {r['path']}, not extracted\n")
    print(json.dumps({"project": code, "existing": len(todo), "marked_processed": len(mark), "left_to_process": len(todo) - len(mark),
                      "cutoff": cutoff, "dry_run": dry_run}))
    return 0


def main(argv):
    """Run the minutes command in `argv` (see the module docstring)."""
    if not argv:
        print(__doc__)
        return 2
    cmd = argv[0]
    if cmd == "transcript" and len(argv) == 2:
        print(transcript_text(argv[1]))
        return 0
    if cmd in ("key", "filename"):
        ap = argparse.ArgumentParser(prog=f"minutes.py {cmd}")
        ap.add_argument("--date", required=True)
        ap.add_argument("--title", required=True)
        ap.add_argument("--transcript")
        ap.add_argument("--event-id")
        a = ap.parse_args(argv[1:])
        date.fromisoformat(a.date)
        if cmd == "filename":
            print(stem(a.date, a.title))
            return 0
        key = meeting_key(a.date, a.title, a.transcript, a.event_id)
        done = processed_on(key)
        print(json.dumps({"key": key, "processed_on": done}))
        return 0
    if cmd == "filedate" and len(argv) == 2:
        day, title, how = paths.name_date(Path(argv[1]).name)
        if not day:
            day, how = paths.file_date(paths.resolve(argv[1]) if not Path(argv[1]).is_absolute() else argv[1])
        print(json.dumps({"date": day, "title": title, "how": how, "from_name": how in ("creaite", "teams"),
                          "event_id": file_event_id(argv[1])}))       # set for a transcript or chat loaded from the calendar (BL-42 phase 3)
        return 0
    if cmd == "new":
        return cmd_new(argv[1:])
    if cmd == "baseline":
        ap = argparse.ArgumentParser(prog="minutes.py baseline")
        ap.add_argument("code")
        ap.add_argument("--all", action="store_true", dest="all_existing")
        ap.add_argument("--keep-weeks", type=int)
        ap.add_argument("--dry-run", action="store_true")
        a = ap.parse_args(argv[1:])
        if a.all_existing == (a.keep_weeks is not None):
            print("Say which: --all (mark every existing meeting file as processed) or --keep-weeks N (process the last N weeks).")
            return 2
        return cmd_baseline(a.code, a.all_existing, a.keep_weeks, a.dry_run)
    if cmd == "stage" and len(argv) == 2:
        return cmd_stage(argv[1])
    if cmd == "agenda" and len(argv) >= 2:                  # BL-209
        a = argparse.ArgumentParser(prog="minutes.py agenda")
        a.add_argument("code")
        a.add_argument("--date", required=True)
        a.add_argument("--title", required=True)
        o = a.parse_args(argv[1:])
        print(json.dumps(agenda_points(o.code, o.date, o.title), ensure_ascii=False, indent=1))
        return 0
    if cmd == "carry" and len(argv) >= 2 and argv[1] in ("on", "off"):
        a = argparse.ArgumentParser(prog="minutes.py carry")
        a.add_argument("--key", required=True)
        a.add_argument("--point", required=True)
        o = a.parse_args(argv[2:])
        try:
            print(carry(argv[1] == "on", o.key, o.point))
        except ValueError as e:
            print(e)
            return 2
        return 0
    if cmd == "refresh" and len(argv) == 2:
        return cmd_refresh(argv[1])
    if cmd == "expected":
        ap = argparse.ArgumentParser(prog="minutes.py expected")
        ap.add_argument("code")
        ap.add_argument("--title", default="")
        ap.add_argument("--date")
        a = ap.parse_args(argv[1:])
        print(json.dumps(expected_items(a.code, a.title, date.fromisoformat(a.date) if a.date else None),
                         indent=2, ensure_ascii=False))
        return 0
    print(__doc__)
    return 2


REBUILD_AFTER = ("stage", "refresh")      # BL-110: these change what the dashboard shows, so the dashboard is rebuilt



# ===== BL-218 (sprint-drafts-extraction) ===== "Probably done" in a meeting: minutes.py done-candidates <CODE> <transcript> lists the
# passages that may show one of the project's open items finished (plain code: extraction.passage_candidates), for cx-minutes to judge
# before it proposes a closing update with a `done` block. Read-only.
def done_candidates_cmd(code, transcript):
    """The open items of project CODE that the transcript may show finished, as JSON."""
    try:
        text = transcript_text(transcript)
    except OSError as e:
        print(f"creaite: can't read {transcript}: {type(e).__name__}")
        return 1
    con = tracker.connect()
    out = extraction.passage_candidates(con, code.upper(), text)
    con.close()
    print(json.dumps({"candidates": out}, ensure_ascii=False, indent=1))
    return 0


_main_before_done = main


def _main_with_done(argv):
    if len(argv) == 3 and argv[0] == "done-candidates":
        return done_candidates_cmd(argv[1], argv[2])
    return _main_before_done(argv)


main = _main_with_done
# ===== end BL-218 =====

if __name__ == "__main__":
    code = debuglog.main("minutes.py", main, sys.argv[1:])
    if code == 0 and sys.argv[1:2] and sys.argv[1] in REBUILD_AFTER:
        import build_dashboard
        build_dashboard.rebuild()
    sys.exit(code)
