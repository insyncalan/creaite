"""Calendar import's Refresh (#265): the plain-code half of the calendar refresh as its own run kind.

Pressing Refresh in Intake's Calendar import (or Today's Refresh calendar) is Alan's go-ahead to read his Outlook calendar and
save it for Intake and Today, and nothing more. The live server (a guarded file: dev/proposals/calendar-refresh/) owns the route,
POST /api/calendar/refresh, and starts the run kind "calendar" under the guard hook's mode "calendar", which lets the run read the
calendar and run the sweep's calendar steps only (sweep.py calendar-window, calendar, transcripts todo, show and record). This
module is what the route and the page share, all plain code:

    precheck()          -> None, or why the refresh can't start (the development repository; the calendar source is off)
    build_prompt()      -> the run's message: fixed wording, nothing from the request or the page
    label()             -> the run's plain ask (BL-326)
    outcome(started)    -> {saved, meetings, days, transcripts}: what reached system/staging/calendar.json since `started`
    closure_line(res)   -> the run's one closure line
    closer()            -> the run's closer (live_server.Run(closer=…)): emits the "calendar" event, returns the closure
    stopped_line(run)   -> the closure line when Alan pressed Stop: whether the calendar was saved before he did (#265 review L3)
    lines()             -> the run's lines (live_server.Run(lines=…)): {"stopped": stopped_line}

The request is `{"run": "<id>"?}` and nothing else. The stream is the run engine's events, plus one "calendar" event before the
closure: {"type": "calendar", "saved": bool, "meetings": n, "days": n, "transcripts": bool}. Counts only, never a title or a body.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

KIND = "calendar"           # the run engine's kind, the usage monitor's kind and the guard hook's mode
MODE = "calendar"
USAGE_LABEL = "Calendar refresh"           # Activity › Usage (UsagePanel.jsx KIND)
LABEL = "Refresh the calendar"
SPEC = "system/staging/drafts/calendar.json"          # the sweep's own input file for `sweep.py calendar`
FACTS = "system/staging/drafts/transcripts.json"      # and for `sweep.py transcripts record`
COMMANDS = (                                          # the only commands the run is given (the hook's mode allows these alone)
    "system/scripts/run sweep.py calendar-window",
    f"system/scripts/run sweep.py calendar {SPEC}",
    "system/scripts/run sweep.py transcripts todo",
    f"system/scripts/run sweep.py transcripts record {FACTS}",
)


def precheck(settings=None, root=None):
    """None when a refresh may start, else why not, in plain words: never in the development repository (it would read real
    Microsoft 365 data), and not when the sweep's calendar source is off in Settings."""
    root = Path(root) if root else paths.ROOT
    if (root / ".creaite-dev").exists():
        return "The calendar isn't read in the development repository."
    s = paths.load_settings() if settings is None else settings
    sources = ((s or {}).get("sweep") or {}).get("sources") or {}
    if sources.get("calendar") is False:
        return "The calendar source is off in Settings (Sweep › Sources): turn it on to refresh the calendar."
    return None


def build_prompt():
    """The run's message: a fixed wording. Nothing in it comes from the request, the page or a file."""
    return ("Refresh Alan's Outlook calendar for Intake and Today: the cx-sweep skill's step 8 (Calendar) and step 8b "
            "(Transcripts) only, exactly as the skill says for \"refresh calendar\" on its own (they are in "
            ".claude/skills/cx-sweep/SKILL.md if you need to read them). Nothing else: no mail, no Teams, no proposals, "
            "no follow-alert check, no sweep lock and no done line. Run each command on its own, exactly as written here:\n"
            f"1. `{COMMANDS[0]}`: the window (from, to).\n"
            "2. outlook_calendar_search over that window; leave out meetings Alan declined and cancelled ones.\n"
            f"3. Write `{SPEC}` with the Write tool, in the skill's shape (times exactly as Microsoft 365 gives them), then "
            f"`{COMMANDS[1]}`.\n"
            f"4. `{COMMANDS[2]}`; for each meeting it lists, outlook_calendar_search and read_resource as step 8b says (never keep "
            f"a body, a passcode, a PIN or any transcript text); write `{FACTS}` with the Write tool, then `{COMMANDS[3]}`.\n"
            "If a step is refused or fails, say so in one plain line (\"The calendar was not saved: …\") and stop. Never quote "
            "an invite's text. End with the calendar command's one-line result.")


def label():
    """The plain ask the run shows (BL-326)."""
    return LABEL


def _since(p, started):
    """True when file `p` was written since `started` (seconds), allowing a second for the clock."""
    try:
        return p.stat().st_mtime >= started - 1
    except OSError:
        return False


def outcome(started):
    """What the run saved: whether system/staging/calendar.json was written since `started`, with its meetings and days
    (counts only), and whether the transcripts' statuses were recorded too."""
    saved = _since(paths.CALENDAR, started)
    meetings = days = 0
    if saved:
        try:
            held = json.loads(paths.CALENDAR.read_text(encoding="utf-8")).get("days") or {}
        except (OSError, ValueError, AttributeError):
            held, saved = {}, False
        if isinstance(held, dict):
            days = len(held)
            meetings = sum(len(v) for v in held.values() if isinstance(v, list))
    return {"saved": saved, "meetings": meetings, "days": days, "transcripts": _since(paths.TRANSCRIPTS, started)}


def closure_line(res):
    """The run's one closure line, from its outcome."""
    if not res.get("saved"):
        return "The calendar was not saved: Refresh again, or ask creaite why."
    n, d = res.get("meetings", 0), res.get("days", 0)
    line = f"Calendar saved: {n} meeting{'' if n == 1 else 's'} over {d} day{'' if d == 1 else 's'}."
    return line + ("" if res.get("transcripts") else " Transcripts weren't checked this time.")


def closer():
    """The run's closer (live_server.Run(closer=…)): emit the "calendar" event and return the closure."""
    def close(run):
        """Emit the run's outcome as the "calendar" event and return its closure line."""
        res = outcome(run.started)
        run.emit("calendar", **res)
        return {"ok": res["saved"], "line": closure_line(res), "href": "#inbox", "link": "Intake"}
    return close


STOPPED_SAVED = "Stopped after the calendar was saved: {n} meeting{s} over {d} day{ds}."
STOPPED_NOT_SAVED = "Stopped: the calendar was not saved. Press Refresh to start again."


def stopped_line(run):
    """#265 review L3: the closure line when Alan pressed Stop. The save is one atomic write, so it either finished before Stop
    or never began: say which (counts only), and emit the "calendar" event so the page reads the saved calendar again."""
    res = outcome(run.started)
    run.emit("calendar", **res)                   # the run engine catches a fault here and says the plain Stop line
    if not res["saved"]:
        return STOPPED_NOT_SAVED
    n, d = res["meetings"], res["days"]
    return STOPPED_SAVED.format(n=n, s="" if n == 1 else "s", d=d, ds="" if d == 1 else "s")


def lines():
    """The run's lines (live_server.Run(lines=…)): the Stop line is worked out when the run stops (stopped_line)."""
    return {"stopped": stopped_line}
