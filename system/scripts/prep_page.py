"""creaite meeting prep page (BL-98 part 2): one self-contained HTML page for a meeting, saved in the project's Agendas
folder. Standard library only.

The live server gathers the context here, runs Claude headless with read-only tools to research it (reply: JSON), then
calls build, which renders the page and writes it. Claude never writes the file: the page is the server's own write. The
command line's build (cx-prep) saves through filechange.py instead (BL-271): backed up, logged, undoable, and on Alan's card
when it is sensitive.

Commands (cx-prep uses them from Claude Code):
  context "<meeting key>"              the meeting, its items ranked as the Prep brief ranks them, the project's latest
                                       reporting and what to research, as JSON
  build "<meeting key>" <reply.json>   render the page from Claude's reply and save it; prints the vault path
  latest                               {meeting key: the newest page's vault path}

A meeting key is the Prep brief's: "HH:MM|title" today, "YYYY-MM-DD|HH:MM|title" any later day the saved calendar holds
(BL-293: not only tomorrow; sweep.calendar_span). A past day, or one beyond the saved calendar, is refused with the reason.

Where it goes: <project>/<agendas folder>/YYYY-MM-DD Prep - <title>.html (locations.folders.agendas; the portfolio
folder's for a portfolio meeting). A name that is taken by a file creaite didn't write, or one Alan has edited, gets a
number; creaite's own unchanged page for the same meeting and day is replaced, after a copy to system/backups/files/.
Pages are kept for good. system/staging/prep-pages.json records what creaite wrote (path → sha256, key, day).
"""
import hashlib
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
import calendar_gateway  # noqa: E402  (#375 E1: the one read path for the saved calendar)
import docx_tools  # noqa: E402  (md_spans: the one reader of **bold**, _italic_, ~~strike~~ and `code`, shared with Word)

REGISTRY = paths.STAGING / "prep-pages.json"
FILE_BACKUPS = paths.BACKUPS / "files"
MAX_ITEMS = 25
MAIL_DAYS = 14
MARK = "creaite-prep-page"
DOC_TAG = ' <span class="tag">project document (internal)</span>'


def now():
    """The time now on creaite's clock (sweep.now; CREAITE_NOW fixes it for tests)."""
    import sweep
    return sweep.now()


def _registry():
    try:
        return json.loads(REGISTRY.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def latest():
    """{meeting key: the newest page's vault path} for pages that are still there."""
    out = {}
    for rel, rec in sorted(_registry().items(), key=lambda kv: kv[1].get("at", "")):
        try:
            if paths.resolve(rel).is_file():
                out[rec.get("key", "")] = rel
        except (LookupError, ValueError, OSError):
            continue
    return out


def _event(key, day):
    try:
        days = calendar_gateway.read("prep_panel").get("days") or {}
    except (OSError, ValueError):
        return None
    start, title = key.split("|")[-2:]
    return next((e for e in days.get(day) or [] if e.get("start", "") == start and e.get("title") == title), None)


def decision_kind(x, day):
    """BL-113: what a decision is in this meeting's prep: one still needed, one whose revisit date has come, or one made since."""
    if x.get("st") == "Pending":
        return "Decision needed"
    if x.get("st") == "Made" and re.fullmatch(r"\d{4}-\d{2}-\d{2}", x.get("revisit") or "") and x["revisit"] <= day:
        return "Decision to revisit"
    return "Decision"


def decision_due(x, day):
    """The date that matters for it: needed by (pending), revisit date (to revisit), or the day it was made."""
    kind = decision_kind(x, day)
    return (x.get("due") if kind == "Decision needed" else x.get("revisit") if kind == "Decision to revisit" else x.get("date")) or ""


# ===== BL-126 (sprint-prep-files): only urgent, overdue and due-soon work is listed =====

def due_soon_days(settings=None):
    """Settings › Review › due soon (7 by default); the dashboard's soon() uses the same."""
    try:
        cfg = settings if isinstance(settings, dict) else paths.load_settings()
        return int((cfg.get("review") or {}).get("due_soon_days") or 7)
    except (TypeError, ValueError, OSError):
        return 7


def select_items(pool, day, soon):
    """(chosen, universe): the items worth a place on the page, in order, and how many open items there are in all.
    Listed: Urgent, overdue, or due within `soon` days of the meeting's day; a decision needed when it is due soon or overdue; a
    decision whose revisit date has come. Order: overdue (oldest first), then due soonest, then Urgent with no date."""
    from datetime import date as _date, timedelta
    limit = (_date.fromisoformat(day) + timedelta(days=soon)).isoformat()
    rank = {"Urgent": 0, "High": 1, "Medium": 2, "Low": 3}
    chosen, universe = [], 0
    for k, x in pool:
        if k == "decisions":
            kind = decision_kind(x, day)
            if kind == "Decision to revisit":
                universe += 1
                when = x.get("revisit") or ""
            elif kind == "Decision needed":
                universe += 1
                when = x.get("due") or ""
                if not when or when > limit:
                    continue
            else:
                continue                                     # made since the last meeting: the brief lists these, the page doesn't
            chosen.append((0 if kind == "Decision to revisit" or when < day else 1, when, 9, x["id"], k, x))
            continue
        universe += 1
        due = x.get("due") or ""
        urgent = x.get("pr") == "Urgent"
        if due and due < day:
            chosen.append((0, due, rank.get(x.get("pr"), 4), x["id"], k, x))
        elif due and (due <= limit or urgent):
            chosen.append((1, due, rank.get(x.get("pr"), 4), x["id"], k, x))
        elif urgent:
            chosen.append((2, "", 0, x["id"], k, x))
    chosen.sort(key=lambda c: c[:4])
    return [(c[4], c[5]) for c in chosen], universe


# ===== BL-229 (v1.7.0): context in gather and shape steps; the JSON is unchanged (test_prep_context_pinned.py) =====
_PINNED = []


def _collect():
    """The dashboard's data: the one `using` pinned (BL-286: one collect for a page's several parts), else a fresh collect."""
    import build_dashboard
    return _PINNED[-1] if _PINNED else build_dashboard.collect()


class using:
    """`with prep_page.using(d):` context() and the BL-286 helpers read this data instead of collecting it again."""

    def __init__(self, d):
        self.d = d

    def __enter__(self):
        _PINNED.append(self.d)
        return self.d

    def __exit__(self, *_):
        _PINNED.pop()
        return False


NO_PROJECT = "No project"          # #279: the saved value "_portfolio" as Alan reads it on a prep page


def _project_of(d, m):
    """(code, chosen) of a meeting's Prep brief record. #279: "No project" is the saved value "_portfolio", distinct from nothing
    chosen (""). A remembered code that is no project any more (unknown, removed, archived) counts as not chosen: the picker
    asks again, and the page still builds, in the all-projects view.
    #362 (persisted-paths proof, dev/proposals/362/PERSISTED-PATHS.md): everything that is written or sent for a meeting takes its
    project from here (context(): the page's Agendas folder, prep-pages.json, the stored content, the research prompt, Shape,
    the agenda and the one-pager drafts). A confidential meeting's project is therefore only ever one Alan chose (a remembered
    series, how "remembered"); a guess (matched, likely) stays on the screen and is not chosen, so the page is the all-projects
    view and files in the portfolio folder until he picks the project."""
    code = m.get("p") or ""
    if m.get("how") == "likely":                          # #328: a Likely guess is never a chosen project
        return "_portfolio", False
    if (m.get("invite") or {}).get("confidential") and m.get("how") != "remembered":
        return "_portfolio", False
    chosen = code == "_portfolio" or any(p["code"] == code for p in d.get("projects") or []) if code else False
    return (code, True) if chosen else ("_portfolio", False)


def context(key):
    """Everything the page and Claude's research need, or {"error": …}."""
    d = _collect()
    key = brief_key(key)
    m, problem = _meeting(d, key)
    if problem:
        return {"error": problem}
    code, chosen = _project_of(d, m)
    ev = _event(key, m["day"]) or {}
    allp = code == "_portfolio"
    items, universe = _prep_items(d, m, code, allp)
    codes = [p["code"] for p in d["projects"]] if allp else [code]
    title = ev.get("title") or key.split("|")[-1]
    return {"key": key, "day": m["day"], "project": code, "chosen": chosen, "series": m.get("series") or "",
            "project_name": NO_PROJECT if allp else
            next((p["name"] for p in d["projects"] if p["code"] == code), ""),
            "meeting": _prep_meeting(ev, title, m.get("invite") or {}),
            "carried": _carried(title, m["day"]),          # BL-209
            "since": m["since"], "last": m.get("last"), "items": items, "not_listed": max(0, universe - len(items)),
            "due_soon_days": due_soon_days(), "reporting": _prep_reporting(d, codes),
            "reports": [r for c in codes for r in ((d.get("prep") or {}).get("reports") or {}).get(c, [])],
            "research": {"minutes_and_transcripts": [f["path"] for f in _prep_recent(d, codes, allp, m["since"])],
                         "documents": _prep_documents(codes), "mail_and_teams_days": MAIL_DAYS, "codes": codes,
                         **_prep_notes(codes)},                    # BL-301: only the notes not marked confidential
            "port": int(__import__("os").environ.get("CREAITE_PORT") or
                        (paths.load_settings().get("live_mode") or {}).get("port", 8765))}   # as live_server.main picks it


# ===== BL-293 (sprint-today-days-server) ===== Prep on any day the saved calendar holds, not only today and tomorrow. Today's
# and tomorrow's Prep brief records come with the dashboard's data; a later day's is worked out when it is asked for
# (build_dashboard.prep_entry) and kept in that data, so the dashboard's own data and the Week ahead don't change.

def split_key(key):
    """(day YYYY-MM-DD, start, title) of a meeting key; an undated key is today's."""
    parts = str(key or "").split("|", 2)
    if len(parts) == 3 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", parts[0]):
        return parts[0], parts[1], parts[2]
    start, _, title = str(key or "").partition("|")
    return now().date().isoformat(), start, title


def brief_key(key):
    """The Prep brief's own form of a key: today's meeting undated ("HH:MM|title"), any other day dated."""
    day, start, title = split_key(key)
    return f"{start}|{title}" if day == now().date().isoformat() else f"{day}|{start}|{title}"


def day_problem(day):
    """None when a prep page may be made for a meeting on `day` (YYYY-MM-DD): today, or a later day the saved calendar holds.
    Otherwise why not, as Alan reads it."""
    import sweep
    if day < now().date().isoformat():
        return f"That meeting was on {shown(day)}, which has passed: prep is for today and the days ahead."
    span = sweep.calendar_span()
    if not span:
        return "There is no saved calendar yet; refresh the calendar."
    if day > span[1].isoformat():
        return f"{shown(day)} is beyond the saved calendar, which runs to {shown(span[1].isoformat())}; refresh the calendar."
    return None


def meeting_entry(d, key):
    """The Prep brief's record for a meeting key ({} when there is none): today's and tomorrow's from the dashboard data, a later
    day's worked out now from the saved calendar and kept in `d` for the next look-up."""
    prep = d.get("prep") if isinstance(d.get("prep"), dict) else {}
    meetings = prep.get("meetings") or {}
    for k in (key, brief_key(key)):
        if k in meetings:
            return meetings[k]
    day, start, title = split_key(key)
    if day_problem(day):
        return {}
    found = _entry_for(d, day, start, title)
    if found and isinstance(d.get("prep"), dict):
        d["prep"].setdefault("meetings", {})[brief_key(key)] = found
    return found or {}


def _entry_for(d, day, start, title):
    import build_dashboard
    from datetime import date as _date
    ev = next((e for e in build_dashboard.saved_calendar_days().get(day) or []
               if isinstance(e, dict) and e.get("start", "") == start and e.get("title") == title), None)
    if not ev:
        return None
    found = build_dashboard.prep_entry(ev, _date.fromisoformat(day), _entry_context(d))
    return found[1] if found else None


def _entry_context(d):
    """build_dashboard.prep_entry's ctx, from the collected dashboard data."""
    import build_dashboard
    return {"projects": d.get("projects") or [], "remembered": (d.get("prep") or {}).get("series") or {},
            "history": build_dashboard.past_meetings(d.get("files") or []),
            "items": (d.get("actions") or [], d.get("raid") or [], d.get("decisions") or []),
            "ms_names": {k: v[0] for k, v in (d.get("milestone_names") or {}).items()},
            "vips": build_dashboard.vip_kinds(), "today": now().date()}


def _meeting(d, key):
    """(the meeting's Prep brief record, None), or (None, why there is no prep for it)."""
    day = split_key(key)[0]
    problem = day_problem(day)
    if problem:
        return None, problem
    m = meeting_entry(d, key)
    if not m:
        return None, f"That meeting isn't in the saved calendar for {shown(day)} any more; refresh the calendar."
    return m, None          # #279: no project chosen yet still opens (the all-projects view, with a picker for the project)
# ===== end BL-293 =====


def _prep_items(d, m, code, allp):
    """The listed items (urgent, overdue, due soon; decisions needed or to revisit) and how many were in the running."""
    import build_dashboard
    inp = (lambda x: True) if allp else (lambda x: x["p"] == code)
    rank = m.get("rank") or {}
    ms = {k: v[0] for k, v in (d.get("milestone_names") or {}).items()}
    pool = [("actions", a) for a in d["actions"] if inp(a) and a["st"] in ("Open", "Delayed")] + \
           [("raid", r) for r in d["raid"] if inp(r) and r["st"] == "Open"] + \
           [("decisions", x) for x in d["decisions"] if inp(x) and build_dashboard.decision_for_prep(x, m["since"], m["day"])]   # BL-113
    chosen, universe = select_items(pool, m["day"], due_soon_days())
    items = [_prep_item(k, x, m["day"], ms, rank) for k, x in chosen[:MAX_ITEMS]]
    return items, universe


def _prep_item(k, x, day, ms, rank):
    decision = k == "decisions"
    return {"table": k, "id": x["id"], "p": x["p"], "text": x["t"],
            "type": decision_kind(x, day) if decision else x.get("type") or "Action",
            "owner": x.get("o") or x.get("by") or "", "due": decision_due(x, day) if decision else x.get("due") or x.get("date") or "",
            "priority": x.get("pr") or "", "status": x.get("st") or "", "workstream": x.get("ws") or "",
            "milestone": ms.get(x.get("ms")) or "", "why": ((rank.get(k) or {}).get(x["id"]) or [0, ""])[1]}


def _prep_reporting(d, codes):
    """Per project: health, its reason, the Current state, the latest weekly update and the latest weekly report."""
    import sqlite3
    reporting = []
    con = sqlite3.connect(f"file:{paths.DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    for c in codes:
        proj = next((p for p in d["projects"] if p["code"] == c), {})
        up = con.execute("SELECT week_ending, health, summary FROM updates WHERE project = ? ORDER BY week_ending DESC "
                         "LIMIT 1", (c,)).fetchone()
        weekly = sorted([f for f in d["files"] if f["p"] == c and f["f"] == "reports" and "weekly" in f["n"].lower()],
                        key=lambda f: (f.get("date") or "", f["n"]))
        reporting.append({"project": c, "name": proj.get("name", ""), "health": proj.get("health", ""),
                          "health_reason": proj.get("reason", ""), "current_state": (proj.get("current") or "")[:4000],
                          "update": dict(up) if up else None,
                          "weekly_report": {"name": weekly[-1]["n"], "path": weekly[-1]["path"], "date": weekly[-1].get("date")}
                          if weekly else None})
    con.close()
    return reporting


def _prep_recent(d, codes, allp, since):
    """The latest minutes and transcripts since the last meeting of the series, newest first (at most eight)."""
    return sorted([f for f in d["files"] if f["p"] in codes + (["_portfolio"] if allp else [])
                   and f["f"] in ("minutes", "transcripts") and (f.get("date") or "") >= since],
                  key=lambda f: f.get("date") or "", reverse=True)[:8]


def _prep_documents(codes):
    docs = []
    for c in codes:
        try:
            docs.append(paths.rel(paths.project_dir(c) / paths.folder_name("documents"))
                        if not paths.external() else paths.rel(paths.project_dir(c)))
        except (LookupError, ValueError):  # BL-228: a project without a documents folder has none to link
            pass
    return docs


def _prep_meeting(ev, title, invite):
    return {"title": title, "start": ev.get("start", ""), "end": ev.get("end", ""),
            "where": ev.get("where", ""), "organiser": invite.get("organiser"), "attendees": invite.get("attendees", []),
            "attachments": invite.get("attachments", []), "body": invite.get("body", ""),
            "confidential": bool(invite.get("confidential"))}
# ===== end BL-229 (context) =====


# ===== BL-301 (v20-confidential-prep) ===== A note marked confidential (front matter `confidential: true`, notes.is_confidential)
# is kept out of Prep, by plain code: it is never listed for the research and never named to Claude (a note's file name is its
# title), and anything in Claude's reply that cites one or quotes it (a finding, a question, an item's reason, the summary) is
# dropped before the page is built, stored or shown (hold_confidential; prep_view.assemble applies it again, so a note marked
# confidential later is dropped from a stored page too). The research run's read tools could still open the file by path: the
# prompt tells it not to, and what comes back is filtered.
QUOTE_WORDS = 8          # this many words in a row from a confidential note, found in the reply, counts as quoting it


def note_split(codes):
    """(ordinary notes, confidential notes) of these projects (or `_portfolio`), as vault paths, by name."""
    import notes
    ordinary, held = [], []
    for c in dict.fromkeys(codes):
        try:
            files = paths.note_files(c)
        except (LookupError, ValueError, OSError):  # a project without a folder has no notes
            continue
        for f in files:
            (held if notes.is_confidential(f) else ordinary).append(paths.rel(f))
    return ordinary, held


def _prep_notes(codes):
    """The research's notes: {"notes": [the ordinary notes' paths], "confidential_notes_left_out": n}, each key only when there
    is something to say (a project without notes keeps the context it always had). A confidential note is counted, never named."""
    ordinary, held = note_split(list(codes) + ["_portfolio"])
    return {**({"notes": ordinary} if ordinary else {}), **({"confidential_notes_left_out": len(held)} if held else {})}


def _words(text):
    return re.findall(r"[a-z0-9]+", str(text or "").lower())


def held_notes():
    """[{path, real, name, runs}] for every confidential note in the vault (every project and the portfolio): what a reply is
    checked against. `runs` are the note's QUOTE_WORDS-word runs, as joined words."""
    import notes
    try:
        codes = [c for c, _ in paths.project_folders()]
    except (LookupError, ValueError, OSError):
        codes = ["_portfolio"]
    out = []
    for rel in note_split(codes)[1]:
        real = paths.resolve(rel)
        w = _words(notes.read(real)[1])
        out.append({"path": rel.lower(), "real": str(real).lower(), "name": real.name.lower(),
                    "runs": {" ".join(w[i:i + QUOTE_WORDS]) for i in range(max(0, len(w) - QUOTE_WORDS + 1))}})
    return out


def _leaks(text, held, source=False):
    """Whether `text` points at a confidential note (as a source: its path, real path or file name) or quotes one."""
    if source:
        s = str(text or "").lower().replace("\\", "/")
        if any(h["path"] in s or h["real"] in s or h["name"] in s for h in held):
            return True
    w = _words(text)
    joined = {" ".join(w[i:i + QUOTE_WORDS]) for i in range(max(0, len(w) - QUOTE_WORDS + 1))}
    return any(joined & h["runs"] for h in held)


def hold_confidential(reply, held=None):
    """(Claude's reply with nothing from a confidential note, how many parts were dropped). A finding is dropped when its source
    is a confidential note or its text quotes one; so is a question, an item's reason or the summary that quotes one."""
    reply = reply if isinstance(reply, dict) else {}
    held = held_notes() if held is None else held
    if not held:
        return reply, 0
    out, dropped = dict(reply), 0
    if isinstance(reply.get("notes"), list):
        keep = [n for n in reply["notes"]
                if not (isinstance(n, dict) and (_leaks(n.get("source"), held, True) or _leaks(n.get("text"), held)))]
        dropped += len(reply["notes"]) - len(keep)
        out["notes"] = keep
    if isinstance(reply.get("questions"), list):
        keep = [q for q in reply["questions"] if not _leaks(q, held)]
        dropped += len(reply["questions"]) - len(keep)
        out["questions"] = keep
    if isinstance(reply.get("item_reasons"), dict):
        keep = {k: v for k, v in reply["item_reasons"].items() if not _leaks(v, held)}
        dropped += len(reply["item_reasons"]) - len(keep)
        out["item_reasons"] = keep
    if reply.get("about") and _leaks(reply["about"], held):
        out["about"], dropped = "", dropped + 1
    return out, dropped


NOTES_RULE = ("Notes: read only the notes listed under research \"notes\" (Alan's own notes, internal: label what comes from them). "
              "Never open, read, search or cite any other file in a notes folder: a note marked confidential is kept out of prep, "
              "and anything that cites or quotes one is removed from the page.")
# ===== end BL-301 (v20-confidential-prep) =====


PROMPT = """creaite prep page. Research one meeting for Alan and reply with ONLY a JSON object, nothing else.
Read-only: never write, send or change anything. Nothing you write is copied into the vault except the page itself.

The meeting and what creaite already knows (JSON):
{ctx}

Do this:
1. Read the invite body above and say in two or three plain sentences what the meeting is about ("about").
2. Look at the items listed (only Urgent, overdue and due-soon work is listed; "not_listed" says how many other open items
   there are, which are left out on purpose): for any whose relevance the invite implies in meaning but not in words (for example
   "go-live readiness" and a cut-over risk), give a short reason. Use only IDs from the list. Items of type "Decision
   needed" are still waiting for an answer (owner is who is asked, due is the date it is needed by) and "Decision to
   revisit" are decisions whose revisit date has come: where the meeting could settle one, say so in "questions".
3. Research, briefly, only what bears on the invite or the listed items: read the minutes and transcripts listed under
   research (`python3 system/scripts/docx_tools.py text <file>` for Word files, `minutes.py transcript` for .vtt),
   look in the documents folders listed, and search Microsoft 365 mail and Teams for the project over the last
   {days} days (read-only search tools only). Each finding is one line with its source (a file path, or "Email · From …
   · Subject … · Sent YYYY-MM-DD" or "Teams · Channel … · Sent …") and its date. Never quote long passages; never
   invent a finding. If Microsoft 365 isn't available, say so in "m365".
   {notes_rule}
4. Suggest up to five short questions or asks for the meeting.

Reply exactly in this shape:
{{"about": "…", "item_reasons": {{"<ID>": "why it matters for this meeting"}},
  "notes": [{{"text": "one-line finding", "source": "…", "date": "YYYY-MM-DD"}}],
  "questions": ["…"], "m365": "searched" | "unavailable: <why>"}}
"""


# ===== BL-209 (sprint-insight) ===== agenda points the series' last meeting didn't cover, carried by Alan from the meeting hub
def _carried(title, day):
    try:
        import minutes
        return [{"point": c["point"], "day": c.get("day", ""), "title": c.get("title", "")} for c in minutes.carried_for(title, day)]
    except Exception:  # noqa: BLE001  a help, never a blocker
        return []


def carried_html(ctx):
    """The page's "Not covered last time" section: the points carried over from the last meeting's minutes, or '' when there are none."""
    pts = ctx.get("carried") or []
    if not pts:
        return ""
    lis = "".join(f"<li>{esc(c['point'])} <span class=\"src\">{esc(c.get('title') or '')}, {esc(shown(c.get('day')))}</span></li>" for c in pts)
    return f"<details open><summary><h2>Not covered last time</h2></summary><ul>{lis}</ul></details>\n"


def prompt(ctx):
    """The research prompt for Claude: PROMPT filled with the meeting's context as JSON (cut at 60,000 characters) and the mail look-back
    in days."""
    slim = {k: v for k, v in ctx.items() if k not in ("port",)}
    return PROMPT.format(ctx=json.dumps(slim, ensure_ascii=False, indent=1)[:60000], days=MAIL_DAYS, notes_rule=NOTES_RULE)


def parse_reply(text):
    """Claude's JSON reply (the first {...} block in the text), or {} if there isn't one."""
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return {}
    try:
        out = json.loads(m.group(0))
    except ValueError:
        return {}
    return out if isinstance(out, dict) else {}


# ── the page ──────────────────────────────────────────────────────────────────

# v1.9.5 (UI audit, prep page drift): the status colours are the dashboard's (creaite theme, light and dark) and the type is
# its stacks (Source Sans 3 text, Schibsted Grotesk headings). The page embeds no font (one file, no url(): BL-98), so the
# named faces show where installed and the system font otherwise.
CSS = """
:root{--bg:#f6f7f8;--card:#fff;--ink:#16202a;--muted:#4d5c66;--line:#dde3e7;--accent:#0b6e7f;--warn:#8a5a00;--warnbg:#fbf0da;--ok:#2e6b3a;--bad:#b3261e;
  --font:"Source Sans 3","Segoe UI",system-ui,-apple-system,Arial,sans-serif;
  --display:"Schibsted Grotesk","Helvetica Neue",Arial,sans-serif}
@media (prefers-color-scheme:dark){:root{--bg:#0f1518;--card:#171e22;--ink:#e4eaed;--muted:#a2aeb5;--line:#2a343a;--accent:#5fc4d6;--warn:#f0c66b;--warnbg:#3a2c10;--ok:#9fd6a5;--bad:#f2b8b5}}
*{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 var(--font)}
main{max-width:860px;margin:0 auto;padding:24px 16px 48px} h1,h2,.rep h3{font-family:var(--display)}
h1{font-size:24px;line-height:1.25;margin:6px 0 4px} h2{font-size:17px;margin:0}
.internal{display:inline-block;font:700 11px/1 var(--font);letter-spacing:.08em;text-transform:uppercase;color:var(--warn);background:var(--warnbg);border:1px solid var(--warn);border-radius:4px;padding:4px 7px}
.meta{color:var(--muted);margin:0} .warn{background:var(--warnbg);color:var(--warn);border-radius:8px;padding:8px 12px;margin:12px 0}
details{background:var(--card);border:1px solid var(--line);border-radius:10px;margin:14px 0;padding:10px 14px} summary{cursor:pointer;list-style:none} summary::-webkit-details-marker{display:none}
summary h2::before{content:"▾ ";color:var(--muted)} details:not([open]) summary h2::before{content:"▸ "}
table{width:100%;border-collapse:collapse;margin-top:8px;font-size:14px} th,td{text-align:left;vertical-align:top;padding:6px 8px;border-top:1px solid var(--line)} th{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}
td.why{color:var(--accent)} a{color:var(--accent)} .empty{color:var(--muted);font-style:italic;margin:8px 0 0} ul{margin:8px 0 0;padding-left:20px} li{margin:4px 0}
.src{color:var(--muted);font-size:13px} .tag{font-size:11px;border:1px solid var(--line);border-radius:4px;padding:1px 5px;color:var(--muted)}
footer{color:var(--muted);font-size:12px;margin-top:24px}
blockquote{margin:8px 0;padding:0 0 0 12px;border-left:3px solid var(--line);color:var(--muted)} blockquote p{margin:0 0 6px}
.rep{max-width:70ch} .rep .proj{margin:14px 0 22px} .rep h3{font-size:16px;margin:0 0 6px;line-height:1.4} .rep h3.rh{margin-top:26px}
.rep p{margin:8px 0} .rep .headline{font-size:16px;line-height:1.55} .rep ul.points{margin:10px 0;padding-left:22px} .rep ul.points li{margin:9px 0;line-height:1.55}
.rep .upd{color:var(--ink)} .rep details.full,.rep details.more{background:none;border:0;border-top:1px solid var(--line);border-radius:0;padding:8px 0 0;margin:12px 0 0}
.rep details.full summary,.rep details.more summary{color:var(--accent);font-size:14px} .rep details.full summary::before,.rep details.more summary::before{content:"▸ "} .rep details[open] > summary::before{content:"▾ "}
.rep details ul,.rep details ol{margin:8px 0;padding-left:22px} .rep details li{margin:6px 0;line-height:1.5}
.health{display:inline-block;font:600 12px/1 var(--font);border:1px solid currentColor;border-radius:999px;padding:4px 8px;vertical-align:middle;margin-left:4px}
.health.ok{color:var(--ok)} .health.warnh{color:var(--warn)} .health.bad{color:var(--bad)}
ul.reps{list-style:none;padding:0;margin:6px 0 12px} ul.reps li{margin:6px 0} .rn{margin:10px 0 0}
@media print{body{background:#fff;color:#000;font-size:12px} main{max-width:none;padding:0} details{border:0;padding:0;margin:10px 0;page-break-inside:avoid} summary h2::before{content:""} a{color:#000;text-decoration:none} a.tlink::after{content:" (" attr(href) ")";font-size:.9em} .internal{border-color:#000;color:#000;background:none}}
"""


def esc(t):
    """Text escaped for HTML, quotes included; None becomes ''."""
    return html.escape(str(t if t is not None else ""), quote=True)


def shown(iso):
    """YYYY-MM-DD → DD-MM-YYYY (creaite shows dates that way)."""
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})(.*)$", str(iso or ""))
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}{m.group(4)}" if m else str(iso or "")


def render(ctx, reply):
    """The page's HTML: one file, no external scripts, fonts or images; collapsible sections; a print style."""
    mt, port, code = ctx["meeting"], ctx.get("port", 8765), ctx["project"]
    reply = hold_confidential(reply)[0]                       # BL-301: a confidential note's findings never reach the page
    why_more = {k: str(v)[:200] for k, v in (reply.get("item_reasons") or {}).items() if isinstance(v, (str, int, float))}
    items = ctx["items"]                                      # BL-126: only what is urgent, overdue or due soon, in that order
    sources = []

    def link(i):
        """The dashboard address (on the live server) that opens this item."""
        return f"http://127.0.0.1:{port}/#work={i['table']}&p={i['p']}&item={i['id']}"

    rows = "".join(
        f"<tr><td><a href=\"{esc(link(i))}\">{esc(i['id'])}</a></td><td>{esc(i['text'])}<br><span class=\"src\">{esc(i['type'])}"
        f"{' · ' + esc(i['workstream']) if i['workstream'] else ''}{' · ' + esc(i['milestone']) if i['milestone'] else ''}</span></td>"
        f"<td>{esc(i['owner'])}</td><td>{esc(shown(i['due']))}</td><td>{esc(i['priority'])}</td>"
        f"<td class=\"why\">{esc('; '.join(x for x in (i['why'], why_more.get(i['id'], '')) if x))}</td></tr>" for i in items)
    soon = ctx.get("due_soon_days", 7)
    items_html = (f"<table><thead><tr><th>ID</th><th>Item</th><th>Owner</th><th>Due</th><th>Priority</th><th>Why it's relevant</th>"
                  f"</tr></thead><tbody>{rows}</tbody></table>") if items else \
        f'<p class="empty">Nothing is Urgent, overdue or due in the next {esc(soon)} days.</p>'
    n_other = int(ctx.get("not_listed") or 0)
    if n_other:
        work = f"http://127.0.0.1:{port}/#work=actions" + ("" if code == "_portfolio" else f"&p={esc(code)}")
        items_html += (f'<p class="src">{n_other} other open item{"s are" if n_other != 1 else " is"} not listed. '
                       f'<a href="{work}">Show {"them" if n_other != 1 else "it"} in Work</a>.</p>')
    allp = code == "_portfolio"
    reps_by = {}
    for r in ctx.get("reports") or []:
        reps_by.setdefault(r["p"], []).append(r)
    rep = []
    for r in ctx["reporting"]:
        wr = r.get("weekly_report")
        if wr:
            sources.append(f"{wr['path']}")
        rep.append(reporting_html(r, allp))
    rep_links = "".join(reports_html(c, reps_by.get(c, []), port, allp, ctx["reporting"]) for c in dict.fromkeys(r["project"] for r in ctx["reporting"]))
    if rep_links:
        rep.append(f'<h3 class="rh">Recent reports</h3>{rep_links}')
        sources.extend(r["path"] for rs in reps_by.values() for r in rs)
    notes = [n for n in reply.get("notes") or [] if isinstance(n, dict) and str(n.get("text") or "").strip()]
    notes_html = "".join(
        f"<li>{esc(str(n['text'])[:300])} <span class=\"src\">— {esc(str(n.get('source') or 'no source given')[:300])}"
        f"{', ' + esc(shown(n.get('date'))) if n.get('date') else ''}</span>"
        f"{DOC_TAG if 'documents' in str(n.get('source') or '').lower() else ''}</li>"
        for n in notes) or ""
    for n in notes:
        if n.get("source"):
            sources.append(str(n["source"])[:300])
    m365 = str(reply.get("m365") or "")
    qs = [q for q in reply.get("questions") or [] if isinstance(q, str) and q.strip()][:5]
    about = str(reply.get("about") or "").strip()
    who = ", ".join(a.get("name", "") for a in mt.get("attendees") or [])
    when = f"{'Today' if ctx['day'] == now().date().isoformat() else shown(ctx['day'])}, {mt['start']} – {mt['end']}"
    sources = list(dict.fromkeys(sources + ["creaite tracker (actions, risks and issues, decisions, updates)",
                                            f"Invite: {mt['title']} ({shown(ctx['day'])})"]))
    warn = '<p class="warn">Confidential meeting: only its title and times were kept, so the invite wasn\'t read.</p>' \
        if mt.get("confidential") else ""
    unavailable = "" if not m365 or m365.startswith("searched") else \
        f'<p class="warn">Microsoft 365 wasn\'t searched ({esc(m365[:200])}); this page is built from the vault only.</p>'
    return f"""<!doctype html>
<!-- {MARK} · Internal: Alan's meeting prep, not for the client. key={esc(ctx['key'])} day={esc(ctx['day'])} -->
<html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="{MARK}" content="{esc(ctx['key'])}"><title>Prep · {esc(mt['title'])}</title><style>{CSS}</style></head>
<body><main>
<span class="internal">Internal</span> <span class="src">Meeting prep for Alan · not for the client · never sent</span>
<h1>{esc(mt['title'])}</h1>
<p class="meta">{esc(when)}{' · ' + esc(mt['where']) if mt.get('where') else ''} · {esc(code if code != '_portfolio' else NO_PROJECT)} {esc(ctx['project_name'] if code != '_portfolio' else '')}</p>
{f'<p class="meta">With {esc(who)}</p>' if who else ''}{warn}{unavailable}
<details open><summary><h2>What this meeting is about</h2></summary>{f'<p>{esc(about)}</p>' if about else '<p class="empty">Nothing found.</p>'}</details>
{carried_html(ctx)}<details open><summary><h2>Work items</h2></summary>{items_html}</details>
<details open><summary><h2>Latest from the project reporting</h2></summary><div class="rep">{''.join(rep) or '<p class="empty">Nothing found.</p>'}</div></details>
<details open><summary><h2>Researched notes</h2></summary>{f'<ul>{notes_html}</ul>' if notes_html else '<p class="empty">Nothing found.</p>'}</details>
<details open><summary><h2>Questions and asks</h2></summary>{'<ul>' + ''.join(f'<li>{esc(q[:300])}</li>' for q in qs) + '</ul>' if qs else '<p class="empty">Nothing found.</p>'}</details>
<details><summary><h2>Sources</h2></summary><ul>{''.join(f'<li class="src">{esc(s)}</li>' for s in sources)}</ul></details>
<footer>Made by creaite on {esc(now().strftime('%d-%m-%Y %H:%M'))}. Internal: for Alan's preparation only. Items and report links open in the dashboard, which needs the live server to be running.</footer>
</main></body></html>
"""


HEALTH_ICON = {"On track": "✔", "At risk": "▲", "Off track": "✖"}       # the word and the icon always appear: never colour alone
HEALTH_CLASS = {"On track": "ok", "At risk": "warnh", "Off track": "bad"}


def task_glyph(text):
    """#134: a checklist item's "[ ]" / "[x]" (with text after it or on its own) as the box Word shows (☐ / ☑).
    docx_tools.TASK reads the same items; both apply it to bullets only (a numbered "1. [ ] a" is text in each)."""
    def box(m):
        """The glyph for a matched box, and the space after it when text followed."""
        return ("☑" if m.group(1) in "xX" else "☐") + (" " if m.group().strip() != m.group() else "")
    return re.sub(r"^\[([ xX])\](?:\s+|$)", box, text)


def md_line(line):
    """(kind, text) of one Current state line: "q" a quote line, "ul" or "ol" a list item (a checklist box drawn on a bullet), "head" a
    heading of any level, "text" anything else. #134"""
    for kind, pattern in (("q", r"\s*>\s?(.*)"), ("ul", r"\s*[-*•]\s+(.*)"), ("ol", r"\s*\d+[.)]\s+(.*)"), ("head", r"\s*#+\s*(.*)")):
        m = re.match(pattern, line)
        if m:
            text = m.group(1).strip()
            return kind, task_glyph(text) if kind == "ul" else text
    return "text", line.strip()


def md_blocks(md, _depth=0):
    """Current state (Markdown) as [("p", text) | ("q", text) | ("qb", [blocks]) | ("ul", [items]) | ("ol", [items])]. Pictures are
    dropped, links keep their text, a heading (any level) becomes a bold paragraph, a "> " run of lines one quote (#134: the sheet
    toolbar writes them), and a quote that holds a heading or a list is read again as blocks inside it (a "qb").
    Nothing else is understood."""
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", str(md or ""))
    t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)
    blocks, cur, items = [], None, []

    def flush():
        """End the block being built (a paragraph, a quote or a list) and add it to the blocks."""
        nonlocal cur, items
        if cur == "q":
            if _depth < 2 and any(md_line(x)[0] in ("ul", "ol", "head") for x in items):
                blocks.append(("qb", md_blocks("\n".join(items), _depth + 1)))
            elif any(items):
                blocks.append(("q", " ".join(x for x in items if x)))
        elif cur and items:
            blocks.append((cur, " ".join(items) if cur == "p" else items))
        cur, items = None, []

    for line in t.splitlines():
        kind, text = md_line(line)
        if not line.strip():
            flush()
        elif kind == "head":
            flush()
            blocks.append(("p", f"**{text.strip('*')}**"))
        elif kind == "text" and cur in ("ul", "ol") and line[:1].isspace():
            items[-1] += " " + text
        else:
            want = "p" if kind == "text" else kind
            if want != cur:
                flush()
                cur = want
            if text or cur in ("ul", "ol", "q"):          # an empty list item stays one (it can be continued on the next line)
                items.append(text)
    flush()
    return blocks


def md_inline(t):
    """Escaped text with **bold**, _italic_ and ~~strikethrough~~ kept, nested as they were written (#134; the same reading as Word's,
    docx_tools.md_spans), a `code` span as its words; every other mark is dropped."""
    out = []
    for text, bold, italic, strike, _, code in docx_tools.md_spans(str(t or "")):
        x = esc(text if code else re.sub(r"[*`]|(?<!\w)_|_(?!\w)", "", text))
        for on, tag in ((italic, "em"), (strike, "s"), (bold, "strong")):
            if on:
                x = f"<{tag}>{x}</{tag}>"
        out.append(x)
    return "".join(out)


def blocks_html(blocks):
    """HTML for md_blocks' blocks: paragraphs, quotes and lists, with **bold**, _italic_ and ~~strikethrough~~ kept."""
    return "".join(f"<p>{md_inline(b[1])}</p>" if b[0] == "p" else
                   f"<blockquote><p>{md_inline(b[1])}</p></blockquote>" if b[0] == "q" else
                   f"<blockquote>{blocks_html(b[1])}</blockquote>" if b[0] == "qb" else
                   f"<{b[0]}>{''.join(f'<li>{md_inline(x)}</li>' for x in b[1])}</{b[0]}>" for b in blocks)


def state_parts(md, n=5):
    """(headline, first n points, how many points there are) of a Current state. The headline is the first paragraph; the points are
    its list items, or, with no list, the paragraphs after it."""
    blocks = md_blocks(md)
    head = next((b[1] for b in blocks if b[0] == "p"), "")
    points = [x for b in blocks if b[0] in ("ul", "ol") for x in b[1]]
    if not points:
        points = [b[1] for b in blocks if b[0] in ("p", "q")][1:]
    return head, points[:n], len(points)


def _short(text, limit=240):
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    return t if len(t) <= limit else t[:limit].rsplit(" ", 1)[0] + "…"


def reporting_html(r, compact):
    """One project's latest reporting: health (word and icon) and date, the headline, the first five points, the weekly update as a
    line or two, and the whole Current state behind a closed disclosure. A Portfolio meeting gets a compact block: the points go behind it."""
    up = r.get("update") or {}
    health = up.get("health") or r.get("health") or ""
    badge = (f'<span class="health {HEALTH_CLASS.get(health, "")}"><span aria-hidden="true">{HEALTH_ICON.get(health, "●")}</span> {esc(health)}</span>'
             if health else "")
    asof = ' <span class="src">as of %s</span>' % esc(shown(up["week_ending"])) if up.get("week_ending") else ""
    name = esc(r["name"] or r["project"])
    head, points, total = state_parts(r.get("current_state"))
    pts = f'<ul class="points">{"".join(f"<li>{md_inline(x)}</li>" for x in points)}</ul>' if points else ""
    summary = _short(up.get("summary") or r.get("health_reason"))
    wk = f" (week ending {esc(shown(up['week_ending']))})" if up.get("week_ending") else ""
    upd = f'<p class="upd"><strong>Weekly update</strong>{wk}: {esc(summary)}</p>' if summary else ""
    full = (f'<details class="full"><summary>Show the full current state</summary>{blocks_html(md_blocks(r["current_state"]))}'
            f'<p class="src">(Current state, project memory)</p></details>' if r.get("current_state") else "")
    if not (head or summary):
        return f'<section class="proj"><h3>{name} {badge}{asof}</h3><p class="empty">No reporting recorded yet.</p></section>'
    if compact:
        more = f'{pts}{upd}{full}'
        return (f'<section class="proj"><h3>{name} {badge}{asof}</h3>{f"<p class=headline>{md_inline(head)}</p>" if head else ""}'
                f'{f"<details class=more><summary>Points and weekly update</summary>{more}</details>" if more else ""}</section>')
    return (f'<section class="proj"><h3>{name} {badge}{asof}</h3>{f"<p class=headline>{md_inline(head)}</p>" if head else ""}'
            f'{pts}{upd}{full}</section>')


def reports_html(code, reports, port, compact, reporting):
    """The recent reports of one project as links the dashboard opens (the live server must be running)."""
    from urllib.parse import quote
    if not reports:
        return ""
    name = next((r["name"] or r["project"] for r in reporting if r["project"] == code), code)
    lis = []
    for r in reports:
        label = esc(r["kind"]) + (' <span class="tag">for the client</span>' if r["kind"] == "Client report" else "")
        when = f' <span class="src">{esc(shown(r["date"]))}</span>' if r.get("date") else ""
        file = (f'<span class="src">{esc(r["name"])} — unavailable: the file is online-only</span>' if r.get("online") else
                f'<a href="http://127.0.0.1:{port}/#openfile={esc(quote(r["path"], safe="/"))}">{esc(r["name"])}</a>')
        lis.append(f"<li>{label}{when} · {file}</li>")
    return (f'<p class="src rn">{esc(name)}</p>' if compact else "") + f'<ul class="reps">{"".join(lis)}</ul>'


def safe_name(title):
    """A meeting title made safe for a file name: no reserved characters, spaces collapsed, at most 80 characters ("Meeting" if empty)."""
    t = re.sub(r'[\\/:*?"<>|\x00-\x1f]', " ", str(title or "Meeting"))
    return re.sub(r"\s+", " ", t).strip(" .")[:80] or "Meeting"


def place(ctx):
    """(target, replaces) for the page: its name in the Agendas folder, and whether that is creaite's own unchanged page for
    the same name, which is replaced. A file creaite didn't write, or one changed since, gets a numbered name instead."""
    code = ctx["project"]
    try:
        folder = paths.folder("_portfolio" if code == "_portfolio" else code, "agendas")
    except LookupError as e:                    # #279: a project with no folder (removed or archived) is a reason, never a crash
        raise ValueError(f"There is no Agendas folder for that project: choose the meeting's project again ({e}).") from None
    stem = f"{ctx['day']} Prep - {safe_name(ctx['meeting']['title'])}"
    reg = _registry()
    target, n = folder / f"{stem}.html", 2
    while target.exists():
        rec = reg.get(paths.rel(target))
        if rec and rec.get("sha") == hashlib.sha256(target.read_bytes()).hexdigest() and _same_meeting(rec, ctx):
            return target, True
        target, n = folder / f"{stem} ({n}).html", n + 1
    return target, False


def _same_meeting(rec, ctx):
    """#279: whether creaite's page `rec` (prep-pages.json) is this meeting's own: another meeting with the same title on the
    same day (two general meetings, say) gets its own numbered page rather than replacing it. An old record with no key is."""
    if not rec.get("key"):
        return True
    return dated_key({"key": rec["key"], "day": rec.get("day")}) == dated_key(ctx)


def record(ctx, target, data):
    """Note in prep-pages.json that creaite wrote this page, as these bytes."""
    reg = _registry()
    reg[paths.rel(target)] = {"sha": hashlib.sha256(data).hexdigest(), "key": ctx["key"], "day": ctx["day"],
                              "at": now().strftime("%Y-%m-%d %H:%M")}
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(json.dumps(reg, indent=1, ensure_ascii=False), encoding="utf-8")


def save(ctx, page):
    """Write the page into the Agendas folder; returns its vault path. The live server's own write: never overwrites a file
    creaite didn't write (or one changed since): that gets a numbered name. creaite's own unchanged page is replaced, with a
    backup."""
    target, replaces = place(ctx)
    gone = paths.unreachable_own_folder(target)          # #385: never create a project's own folder that isn't there
    if gone:
        raise ValueError(f"The project's folder ({gone}) can't be reached, so the page isn't saved. Is OneDrive running?")
    target.parent.mkdir(parents=True, exist_ok=True)
    if replaces:
        FILE_BACKUPS.mkdir(parents=True, exist_ok=True)
        keep = paths.free_path(FILE_BACKUPS, f"{now():%Y-%m-%d-%H%M%S} {target.stem}", target.suffix)   # BL-266
        keep.write_bytes(target.read_bytes())
    data = page.encode("utf-8")
    tmp = target.with_suffix(".tmp")
    tmp.write_bytes(data)
    tmp.replace(target)
    record(ctx, target, data)
    return paths.rel(target)


# ===== BL-223 (sprint-drafts-writing) ===== an agenda Alan chose to keep: a Markdown file in the Agendas folder, by the
# server's own write (never the model's). It never overwrites anything: a name that is taken gets a number. Its list lines are the
# agenda's points, so cx-minutes' Coverage (minutes.py agenda) reads it for that meeting.
AGENDA_LOG = paths.STAGING / "agendas.json"


def save_agenda(key, draft, attendees=False):
    """Write the drafted agenda (drafts.agenda_file_text) for the meeting `key`; returns its vault path, or raises ValueError."""
    import drafts
    ctx = context(key)
    if ctx.get("error"):
        raise ValueError(ctx["error"])
    folder = paths.folder("_portfolio" if ctx["project"] == "_portfolio" else ctx["project"], "agendas")
    gone = paths.unreachable_own_folder(folder)          # #385: never create a project's own folder that isn't there
    if gone:
        raise ValueError(f"The project's folder ({gone}) can't be reached, so the agenda isn't saved. Is OneDrive running?")
    folder.mkdir(parents=True, exist_ok=True)
    stem = f"{ctx['day']} Agenda - {safe_name(ctx['meeting']['title'])}"
    target, n = folder / f"{stem}.md", 2
    while target.exists():
        target, n = folder / f"{stem} ({n}).md", n + 1
    draft = {**draft, "meeting": {"title": ctx["meeting"]["title"], "day": ctx["day"], "start": ctx["meeting"].get("start", ""),
                                  "end": ctx["meeting"].get("end", "")}}
    target.write_text(drafts.agenda_file_text(draft, attendees), encoding="utf-8")
    try:
        log = json.loads(AGENDA_LOG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        log = {}
    log[paths.rel(target)] = {"key": key, "day": ctx["day"], "for_attendees": bool(attendees), "at": now().strftime("%Y-%m-%d %H:%M")}
    AGENDA_LOG.write_text(json.dumps(log, indent=1, ensure_ascii=False), encoding="utf-8")
    return paths.rel(target)
# ===== end BL-223 =====


def save_through_filechange(ctx, page):
    """BL-271: the command line's write (cx-prep, and ask creaite running it). The page is put in system/staging/drafts/ and
    filechange.py makes the change, so it is backed up, logged and undoable, and waits on Alan's card when it is sensitive (a
    run that has read outside content). (exit code, message): 0 saved, 3 on the card, 1 refused."""
    import filechange
    target, replaces = place(ctx)
    paths.DRAFTS.mkdir(parents=True, exist_ok=True)
    draft = paths.free_path(paths.DRAFTS, f"prep-page {ctx['day']}", ".html")
    data = page.encode("utf-8")
    draft.write_bytes(data)
    via = "ask" if filechange.run_state()[0] else "cli"
    ch = {"op": "edit" if replaces else "create", "path": paths.rel(target), "data": data, "from": paths.rel(draft),
          "why": f"Prep page for {ctx['meeting']['title']}"}
    code, msg = filechange.perform(ch, None, via)
    if code == filechange.NEEDS:
        recorded = filechange.record_request(ch, msg[len("Needs approval: "):].rstrip("."))
        msg += (" It is on the card for Alan to approve or decline; nothing was changed." if recorded else
                " From Terminal, nothing was changed.")
        return code, msg                                    # the draft stays: the card shows it
    draft.unlink()
    if code == 0:
        record(ctx, target, data)
    return code, msg


def build(key, reply_text, ctx=None):
    """(vault path, html) of the page built from Claude's reply; raises ValueError with a reason Alan can read."""
    ctx = ctx or context(key)
    if ctx.get("error"):
        raise ValueError(ctx["error"])
    import prep_view
    reply = parse_reply(reply_text) if isinstance(reply_text, str) else reply_text or {}
    reply = hold_confidential(reply)[0]                       # BL-301: nothing from a confidential note is built or stored
    page = prep_view.page_for(ctx, reply)                     # BL-286: the Briefing layout, with the accepted focus
    rel = save(ctx, page)
    prep_view.store(ctx, reply, rel)                          # BL-286: the content, so the in-app page needs no new run
    return rel, page


# ===== BL-326 (v1.9.5): what ask creaite shows for a Prep page run: the ask, then the closure (never the prompt or the reply) =====
def long_day(iso):
    """YYYY-MM-DD → "Thursday 15th October" (the year only when it isn't this year), as the Today page writes a day."""
    import build_dashboard
    from datetime import date
    try:
        d = date.fromisoformat(str(iso or "")[:10])
    except ValueError:
        return str(iso or "")
    year = "" if d.year == now().year else f" {d.year}"
    return f"{build_dashboard.DAYS[d.weekday()]} {build_dashboard.ordinal(d.day)} {d.strftime('%B')}{year}"


def ask_line(ctx):
    """The one plain line ask creaite shows for the run, as if Alan had typed it: "Prep page for <meeting>, <day> <time>"."""
    m = ctx.get("meeting") or {}
    title = " ".join(str(m.get("title") or "the meeting").split())[:160]
    when = " ".join(x for x in (long_day(ctx.get("day")), str(m.get("start") or "")) if x)
    return f"Prep page for {title}, {when}" if when else f"Prep page for {title}"


def dated_key(ctx):
    """The meeting's key with its day ("YYYY-MM-DD|HH:MM|title"), for the in-app prep page's address."""
    key = str(ctx.get("key") or "")
    return key if re.match(r"\d{4}-\d{2}-\d{2}\|", key) else f"{ctx.get('day')}|{key}"


def closure(ctx, rel):
    """The closure line for a saved page and the link to it: "Saved the prep page in <project> › <folders>", Open."""
    from urllib.parse import quote
    parts = str(rel or "").split("/")
    folders = parts[2:-1] if len(parts) > 3 and parts[0] == "projects" else []
    first = "the portfolio" if ctx.get("project") == "_portfolio" else ctx.get("project_name") or "the project"   # #279
    where = " › ".join([first] + folders)
    return {"ok": True, "line": f"Saved the prep page in {where}", "href": "#prep=" + quote(dated_key(ctx), safe=""),
            "link": "Open"}
# ===== end BL-326 =====


def main(argv):
    """The command line: context prints the meeting's context as JSON; build renders the page from Claude's reply and saves it through
    filechange.py (BL-271), then deletes the reply file (BL-118); latest prints the newest pages."""
    if len(argv) >= 2 and argv[0] == "context":
        print(json.dumps(context(argv[1]), ensure_ascii=False, indent=1))
        return 0
    if len(argv) >= 3 and argv[0] == "build":
        try:
            ctx = context(argv[1])
            if ctx.get("error"):
                raise ValueError(ctx["error"])
            import prep_view
            reply = hold_confidential(parse_reply(Path(argv[2]).read_text(encoding="utf-8")))[0]   # BL-301
            page = prep_view.page_for(ctx, reply)                                  # BL-286: the Briefing layout
        except (OSError, ValueError) as e:
            print(f"Not built: {e}")
            return 1
        code, msg = save_through_filechange(ctx, page)                           # BL-271: never a direct write
        if code == 0:
            prep_view.store(ctx, reply, latest().get(ctx["key"]))                    # BL-286: the content
        print(f"Prep page: {msg}")
        if code != 1:
            paths.consume_draft(argv[2])                                          # BL-118: built, so the reply file has done its job
        return code
    if argv[:1] == ["latest"]:
        print(json.dumps(latest(), ensure_ascii=False))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    try:
        import log as debuglog  # BL-102: the debug log (not `log`: some scripts have a function of that name); a script runs without it
    except ImportError:
        debuglog = None
    sys.exit(debuglog.main("prep_page.py", main, sys.argv[1:]) if debuglog else main(sys.argv[1:]))
