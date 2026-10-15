"""creaite sweep helper — the deterministic parts of cx-sweep (standard library only).

Commands:
  due                      is the daily sweep due? (last success before today's sweep.due_from, and it's now after it)
  window [--days N]        the window to search: since the last successful sweep, or the first-run look-back, or N days
  lock | unlock            one sweep at a time (system/staging/sweep.lock; older than 30 minutes counts as stale). BL-328: the
                           lock records the live server's run (CREAITE_RUN_ID), so the server releases it when that run ends
  unlock --if-idle         release the lock only when no sweep holds it (Settings › Health's Release)
  stage <sweep.json>       write the proposal (source_run cx-sweep) and print its summary
  done --started "YYYY-MM-DD HH:MM" [--normal] [--summary "…"]
                           record success: last-sweep.txt (normal sweeps only) and one run-log line
  fail --message "…"       record a failure in the run log; last-sweep.txt is left alone so the next run covers the gap
  expected <CODE> [--date YYYY-MM-DD] [--subject "…"] [--text "…"]
                           BL-297: the project's open items a message may move forward (minutes.py expected's JSON, read only);
                           with a subject or text each carries `match` and the lists are best first; --date leaves out items
                           raised after the message. A message that moves one forward is staged as an update to it
  done-candidates <messages.json>
                           BL-218: the open items each message may show finished ({"messages": [{source, folder, from, to,
                           sent, text, attachments}]}), as JSON with a hint (Looks done, Maybe done, Not done) and reasons:
                           plain code, for cx-sweep to judge. Read-only; the input file is removed once read
  calendar <calendar.json> save Alan's meetings for the dashboard's Today day view and the Inbox's Meetings
                           (system/staging/calendar.json); days before the window start are dropped
  calendar-window          the days the calendar should cover, as JSON: from the start of settings.json
                           inbox.meetings_from ("monday" = Monday of this week, or a number of days back) to 7 days ahead
  transcripts todo|record <facts.json>|show
                           BL-42 phase 3: which meetings in the Calendar import window to look up for a transcript, and keep what
                           was found (system/staging/transcripts.json: a status for each, never any text); see transcripts.py
  vip addresses|record <found.json> [--found sweep|start-up|check]|seen <id…>|--all|list
                           VIPs (BL-99): the addresses to check, recording alerts in system/staging/vip.json (from a
                           VIP only; never ignored, never matched away), marking them seen, listing the unseen ones
  ignore <messages.json>   drop the messages the ignore rules (settings.json sweep.ignore, BL-97) match; prints
                           {"keep": [indices], "ignored": {rule name: count}} and adds the counts to the run's tally

sweep.json (written by cx-sweep):
  {"window": {"start": "...", "end": "..."}, "normal": true,
   "items": [{"table": "actions", "match": "strong|medium|possible", "values": {..., "source": "Email · From: … · Link: …"},
              "flags": []}, ...],
   "status_signals": [...], "attachments": {"to_inbox": [...], "to_file": [...]}}
  A promise (BL-125 A) is {"table": "promises", "values": {"project", "promised_by", "promised_to", "description",
  "due_date", "source"}}: raised the message's Sent day; one already open is a mention, not a second promise. A message
  showing an open promise kept, dropped or re-dated is {"op": "update", "table": "promises", "id": "ABC-P-004",
  "set": {"status": "Done"}, "why": "…", "source": "…"} (status Done or Dropped, due_date). Promises, new or updated,
  are staged only when settings promises.from_sweep is on (default off, Alan 13-10-2026); otherwise each is skipped
  and counted as "promises off".
calendar.json (written by cx-sweep from Outlook; saved with local 24-hour times. cx-sweep passes start and end as
Microsoft 365 gives them, an ISO date-time with its zone or {"dateTime", "timeZone"}, and this script converts them to
the laptop's time zone and files each meeting under its local date, BL-107; "HH:MM" already local is accepted too):
  {"days": {"YYYY-MM-DD": [{"id": "<event ID>", "start": "HH:MM", "end": "HH:MM", "title": "…", "where": "…",
                            "all_day": false, "private": false, "teams": true,
                            "organiser": true | "<organiser's display name>", "organiser_email": "…",
                            "sensitivity": "normal|personal|private|confidential", "recurrence": "weekly",
                            "body": "<the invite as plain text>", "attendees": [{"name", "email", "type":
                            "required|optional", "response": "accepted|tentative|declined|none"}],
                            "attachments": ["<file name>"]}, ...]}}
  BL-98: the invite's body (HTML removed, the Teams and Outlook joining boilerplate stripped, up to 20,000
  characters), attendees (each mapped to the people register's full name where it matches), the organiser's
  address, attachment names (never the files), the recurrence and the sensitivity are kept for meeting prep. Never
  kept: the join link, meeting ID, passcode or dial-in numbers. A confidential event keeps its title and times but
  no body or attendees. Events an ignore rule matches (BL-97), private ones included, are dropped before saving;
  with the private rule switched off (or from a VIP), a private meeting is saved as "Busy", with no details.
Set CREAITE_NOW="YYYY-MM-DD HH:MM" to fix the clock (tests).
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta
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
import tracker  # noqa: E402
import extraction  # noqa: E402  (sprint-drafts-extraction)

LOCK = paths.STAGING / "sweep.lock"
STALE = timedelta(minutes=30)


def now():
    """The time now to the minute, or CREAITE_NOW in tests."""
    fixed = os.environ.get("CREAITE_NOW")
    return datetime.strptime(fixed, "%Y-%m-%d %H:%M") if fixed else datetime.now().replace(second=0, microsecond=0)


def last_sweep():
    """When the last successful normal sweep ran (system/staging/last-sweep.txt), or None."""
    if not paths.SWEEP_STATE.exists():
        return None
    text = paths.SWEEP_STATE.read_text(encoding="utf-8").strip().splitlines()
    try:
        return datetime.strptime(text[0][:16], "%Y-%m-%d %H:%M") if text else None
    except ValueError:
        return None


def due_info():
    """Whether the daily sweep is due: the last success was before today's sweep.due_from and it is now after it.
    {due, now, due_from, last}.
    """
    s = paths.load_settings().get("sweep", {})
    t = now()
    h, m = map(int, s.get("due_from", "07:00").split(":"))
    due_from = t.replace(hour=h, minute=m)
    last = last_sweep()
    due = t >= due_from and (last is None or last < due_from)
    return {"due": due, "now": t.strftime("%Y-%m-%d %H:%M"), "due_from": due_from.strftime("%H:%M"),
            "last": last.strftime("%Y-%m-%d %H:%M") if last else None}


def window(days=None):
    """The window to search: the last `days` days, else since the last sweep, else the first-run look-back."""
    t, last = now(), last_sweep()
    s = paths.load_settings().get("sweep", {})
    if days:
        start, kind = t - timedelta(days=days), f"last {days} days"
    elif last:
        start, kind = last, "since the last sweep"
    else:
        start, kind = t - timedelta(days=s.get("first_run_lookback_days", 14)), "first run"
    debuglog.info("sweep", f"window {start:%Y-%m-%d %H:%M} to {t:%Y-%m-%d %H:%M} ({kind})")
    return {"start": start.strftime("%Y-%m-%d %H:%M"), "end": t.strftime("%Y-%m-%d %H:%M"), "kind": kind,
            "advances_timestamp": not days, "sources": s.get("sources", {}),
            "show_possible_matches": s.get("show_possible_matches", True),
            "ignore": [r for r in ignore_rules() if r.get("on", True)]}                 # BL-97: the rules in force


# ===== BL-328: the lock records the run that holds it, so it never outlives the sweep =====
# Line 1 is when it was taken (YYYY-MM-DD HH:MM), as before; then "run <id>" and "server <pid>" when the live server started
# the sweep (CREAITE_RUN_ID and CREAITE_SERVER_PID, set for each run). The server releases the lock when that run ends, however
# it ends, and on shutdown. A lock is held with no sweep running ("idle") when its run is no longer the run in progress
# (system/guard/run.json) or its server has stopped; a lock with no run (a sweep from Claude Code) is idle once it is stale.
def lock_info():
    """The sweep lock: {started (datetime), run, server (pid)}, or None when no sweep holds it."""
    try:
        lines = LOCK.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    info = {"started": None, "run": None, "server": None}
    try:
        info["started"] = datetime.strptime((lines[0] if lines else "").strip()[:16], "%Y-%m-%d %H:%M")
    except ValueError:
        try:
            info["started"] = datetime.fromtimestamp(LOCK.stat().st_mtime)
        except OSError:
            return None
    for line in lines[1:]:
        key, _, value = line.strip().partition(" ")
        if key == "run" and re.fullmatch(r"[A-Za-z0-9-]{6,64}", value):
            info["run"] = value
        elif key == "server" and value.isdigit():
            info["server"] = int(value)
    return info


def _alive(pid):
    """Whether a process with this pid is running."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except (PermissionError, OSError):           # someone else's process: it exists
        return True
    return True


def _run_in_progress():
    """The live server's run in progress (system/guard/run.json), or None."""
    try:
        import reach
        return (reach.guard_run() or {}).get("run")
    except Exception:  # noqa: BLE001  unreadable: no run known
        return None


def lock_state(info=None):
    """None (no lock), "running" (a sweep holds it) or "idle" (held with no sweep running: safe to release)."""
    info = lock_info() if info is None else info
    if not info:
        return None
    if info["run"]:
        if info["server"] and not _alive(info["server"]):
            return "idle"
        return "running" if _run_in_progress() == info["run"] else "idle"
    return "running" if now() - info["started"] < STALE else "idle"


def lock():
    """Take the sweep lock (system/staging/sweep.lock); refused while another sweep holds it (under 30 minutes old). A lock
    whose run has ended, or whose server has stopped, is replaced at once (BL-328)."""
    info = lock_info()
    run = os.environ.get("CREAITE_RUN_ID", "")
    run = run if re.fullmatch(r"[A-Za-z0-9-]{6,64}", run) else ""
    if info and not (run and info["run"] == run):          # the same run taking it again keeps it
        age = now() - info["started"]
        state = lock_state(info)
        if state == "running" and age < STALE:
            print(f"Another sweep started {int(age.total_seconds() // 60)} minutes ago; wait for it to finish.")
            debuglog.info("sweep", f"lock refused: another sweep started {int(age.total_seconds() // 60)} minutes ago")
            return 3
        if age >= STALE:
            print("A stale sweep lock was found (over 30 minutes old); continuing.")
            debuglog.warn("sweep", "a stale sweep lock (over 30 minutes old) was replaced")
        else:
            print("A sweep lock was left by a sweep that has ended; continuing.")
            debuglog.warn("sweep", f"a sweep lock left by run {info['run'] or '?'} (ended) was replaced")
    text = now().strftime("%Y-%m-%d %H:%M")
    if run:
        text += f"\nrun {run}"
        server = os.environ.get("CREAITE_SERVER_PID", "")
        if server.isdigit():
            text += f"\nserver {server}"
    LOCK.write_text(text + "\n", encoding="utf-8")
    print("Locked.")
    return 0


def unlock(if_idle=False):
    """Release the sweep lock; with if_idle (Health's Release), only when no sweep holds it."""
    if if_idle:
        state = lock_state()
        if state is None:
            print("No sweep lock is held.")
            return 0
        if state == "running":
            print("A sweep is running: its lock is released when it ends.")
            debuglog.info("sweep", "release refused: a sweep is running")
            return 3
        debuglog.info("sweep", f"an idle sweep lock was released (run {(lock_info() or {}).get('run') or 'none'})")
    LOCK.unlink(missing_ok=True)
    print("Unlocked.")
    return 0
# ===== end BL-328 =====


def log_line(text):
    """Append a timestamped line to the run log (system/staging/run-log.txt)."""
    paths.RUN_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(paths.RUN_LOG, "a", encoding="utf-8") as f:
        f.write(f"{now():%Y-%m-%d %H:%M} | {text}\n")


def link_of(source):
    """The link in a structured Email or Teams source, or None."""
    m = re.search(r"Link: (\S+)", source or "")
    return m.group(1) if m else None


def previously_proposed():
    """(link, normalised text) of items already proposed by earlier sweeps, applied or pending."""
    seen = set()
    for folder in (paths.STAGING, paths.APPLIED):
        for p in folder.glob("proposed-*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except ValueError:
                continue
            for i in data.get("items", []):
                v = i.get("values") or {}
                seen.add((link_of(v.get("source")), norm(v.get("description") or v.get("decision"))))
                if i.get("op") == "update":                                  # BL-113: a decision update from a message
                    seen.add((link_of(i.get("source")), norm(update_key(i.get("id"), i.get("changes")))))
    return seen


def norm(t):
    """Text for matching: lower case, letters, digits and single spaces only."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (t or "").lower())).strip()


def promises_from_sweep():
    """BL-125 A (Alan, 13-10-2026): whether the sweep may propose promises (new ones, and updates to open ones). Off by
    default (settings promises.from_sweep) until BL-233's quality data shows enough of them accepted unedited; promises
    from cx-minutes and those added by hand are unaffected."""
    return bool((paths.load_settings().get("promises") or {}).get("from_sweep", False))


def new_defaults(table, v, flags):
    """A new item's defaults and flags, in place: actions and RAID items raised today; an action with no owner or due date
    flagged; a decision needed (BL-113) undated, a decision made dated today; a promise (BL-125 A) raised the day its message
    was sent, and flagged when it has no due date (it can never be overdue)."""
    day = now().strftime("%Y-%m-%d")
    if table in ("actions", "raid"):
        v.setdefault("raised", day)
    if table == "promises":
        v.setdefault("raised", sent_day(v.get("source")) or day)
    if table == "actions" and v.get("owner", "TBC") == "TBC" and "no-owner" not in flags:
        flags.append("no-owner")
    if table in ("actions", "promises") and not v.get("due_date") and "no-due-date" not in flags:
        flags.append("no-due-date")
    if table == "decisions":                                           # a decision needed is Pending and has no date until it is made
        if (v.get("status") or "Made") == "Pending":
            v.pop("date", None)
        elif not v.get("date"):
            v["date"] = day


def stage(spec_file):
    """Write cx-sweep's items as a proposal (source_run cx-sweep) in system/staging/ and print its summary; drops what the
    ignore rules match (BL-97), flags VIP senders (BL-99), stages pending-decision updates (BL-113), deletes the input (BL-118)."""
    spec = json.loads(Path(spec_file).read_text(encoding="utf-8"))
    con = tracker.connect()
    rejected = {r[0] for r in con.execute("SELECT fingerprint FROM rejected")}
    open_items = {(r[0], norm(r[1])): r[2] for r in con.execute(     # (project, text) → ID (mentions, BL-51)
        "SELECT project, description, id FROM actions WHERE status IN ('Open','Delayed') UNION ALL "
        "SELECT project, description, id FROM raid WHERE status = 'Open' UNION ALL SELECT project, decision, id FROM decisions "
        "UNION ALL SELECT project, description, id FROM promises WHERE status = 'Open'")}           # BL-125 A: promise mentions too
    seen = previously_proposed()
    show_possible = paths.load_settings().get("sweep", {}).get("show_possible_matches", True)
    rules, vips, named = ignore_rules(), vip_addresses(), bool(spec.get("named"))    # BL-97 backstop
    items, notes, ignored, why = [], [], {}, {}
    updated = {}                                                        # BL-113: decision ID → its update item
    from_sweep = promises_from_sweep()                                  # BL-125 A: the sweep's promises are off by default
    for raw in spec.get("items", []):
        if raw.get("table") == "promises" and not from_sweep:          # new or updated, never staged while the setting is off
            notes.append("skipped (promises from the sweep are off: settings promises.from_sweep): "
                         + str((raw.get("values") or {}).get("description") or raw.get("id") or "a promise"))
            why["promises off"] = why.get("promises off", 0) + 1
            continue
        if raw.get("op") == "update":                                   # BL-113: a message makes or withdraws a pending decision
            decision_update(raw, con, items, notes, why, ignored, updated, rules, vips, named, seen)
            continue
        v = dict(raw.get("values") or {})
        table, text = raw.get("table"), v.get("description") or v.get("decision")
        match = raw.get("match", "strong")
        if match == "possible" and not show_possible:
            continue
        if not str(v.get("source", "")).startswith(("Email · ", "Teams · ")):
            notes.append(f"skipped (no structured Email/Teams source): {text}")
            why["no structured source"] = why.get("no structured source", 0) + 1
            continue
        rule = None if named else ignored_by(message_of_source(v["source"]), rules, vips)
        if rule:
            ignored[rule] = ignored.get(rule, 0) + 1
            notes.append(f"skipped (ignore rule “{rule}”): {text}")
            continue
        if summarised(v["source"], raw.get("conversation")):           # BL-334 C: on Today's card already, nothing newer
            notes.append(f"skipped (that conversation is summarised on Today; Create work item there): {text}")
            why["summarised on Today"] = why.get("summarised on Today", 0) + 1
            continue
        item = {"op": "new", "table": table, "values": v}
        if tracker.fingerprint(item) in rejected:
            notes.append(f"skipped (rejected before): {text}")
            why["rejected before"] = why.get("rejected before", 0) + 1
            continue
        if (v.get("project"), norm(text)) in open_items:
            notes.append(f"skipped (already in the tracker): {text}")
            why["already in the tracker"] = why.get("already in the tracker", 0) + 1
            if (link_of(v.get("source")), norm(text)) not in seen:     # a new message raising it again (BL-51)
                import minutes
                minutes.note_mention([open_items[(v.get("project"), norm(text))]],
                                     link_of(v.get("source")) or v.get("source"), "cx-sweep", now().strftime("%Y-%m-%d"))
            continue
        if (link_of(v.get("source")), norm(text)) in seen:
            notes.append(f"skipped (proposed before from the same message): {text}")
            why["already proposed"] = why.get("already proposed", 0) + 1
            continue
        flags = list(raw.get("flags") or [])
        if address_of(message_of_source(v["source"])["from"]) in vips and "vip" not in flags:
            flags.append("vip")                                        # BL-99: sorts first in Review
        new_defaults(table, v, flags)
        items.append({**item, "n": len(items) + 1, "match": match, "flags": flags, "decision": "pending"})
        import review as _review                          # BL-208: the fields cx-sweep guessed, and why
        if _review.clean_inferred(raw.get("inferred") if isinstance(raw, dict) else None):
            items[-1]["inferred"] = _review.clean_inferred(raw.get("inferred"))
        tracker.flag_workstream(con, items[-1])           # BL-58: the project's own workstreams only
    possible = sum(i["match"] == "possible" for i in items)
    out = None
    if items or spec.get("status_signals"):
        out = paths.STAGING / f"proposed-{now():%Y-%m-%d-%H%M}-sweep.json"
        n = 2
        while out.exists():
            out = paths.STAGING / f"proposed-{now():%Y-%m-%d-%H%M}-sweep-{n}.json"
            n += 1
        out.write_text(json.dumps({"created": now().strftime("%Y-%m-%dT%H:%M:00"), "source_run": "cx-sweep",
                                   "window": spec.get("window"), "files": [], "items": items,
                                   "status_signals": spec.get("status_signals", [])}, indent=2, ensure_ascii=False)
                       + "\n", encoding="utf-8")
        if items:
            extraction.after_stage(out, spec)                 # BL-221, BL-218, BL-220 (sprint-drafts-extraction), then validate
    att = spec.get("attachments") or {}
    skipped = {**why, **{f"ignore rule {r}": n for r, n in ignored.items()}}
    debuglog.info("sweep", f"stage: {len(spec.get('items', []))} proposed by the search, {len(items)} staged ({possible} possible)"
                  + (f" in {out.name}" if out else "") + f", {sum(skipped.values())} skipped"
                  + (f" ({', '.join(f'{k} {v}' for k, v in sorted(skipped.items()))})" if skipped else "")
                  + f", {len(att.get('to_inbox', []))} transcript(s) to Intake, {len(att.get('to_file', []))} document(s) to file")
    summary = (f"Sweep: {len(items)} item{'s' if len(items) != 1 else ''} ({possible} possible), "
               f"{len(att.get('to_inbox', []))} transcript(s) to Intake (inbox/), {len(att.get('to_file', []))} document(s) to file")
    print(summary + (f" — {paths.rel(out)}" if out else "") + (" — say review" if items else ""))
    for name in att.get("to_file", []):
        print(f"  To file in documents/: {name}")
    for note in notes:
        print("  Note: " + note)
    tally_ignored(ignored)
    paths.consume_draft(spec_file)                                      # BL-118: staged and checked, so the input has done its job
    return 0


# ===== Decisions needed (BL-113) =====
# A message can make (or withdraw) a decision that is still Pending: the spec item is {"op": "update", "table": "decisions",
# "id": "ABC-D-004", "set": {"status": "Made", ...}, "why": "…", "source": "<structured Email/Teams source>"} and is staged as an
# update to that decision, exactly as minutes.py stages one (minutes.UPDATE_FIELDS says what may change; a made decision is dated
# the message's Sent day unless the spec gives a date). Only pending decisions: other items are updated in Review or with cx-edit.

def update_key(item_id, changes):
    """The key that recognises an update already proposed: the item ID and its changes."""
    return f"{item_id} {json.dumps(changes or {}, sort_keys=True)}"


def sent_day(source):
    """The Sent: date (YYYY-MM-DD) in a structured source, or None."""
    m = re.search(r"Sent: (\d{4}-\d{2}-\d{2})", source or "")
    return m.group(1) if m else None


def decision_update(raw, con, items, notes, why, ignored, updated, rules, vips, named, seen):
    """Stage one update to a pending decision or an open promise, or say in notes why not (counted in why)."""
    import minutes
    table, item_id, source = raw.get("table"), str(raw.get("id") or ""), str(raw.get("source") or "")

    def skip(kind, note):
        """Note why the update was skipped, and count it under `kind`."""
        notes.append(note)
        why[kind] = why.get(kind, 0) + 1

    if table not in ("decisions", "promises"):                         # BL-125 A: a promise kept, dropped or re-dated too
        return skip("update refused", f"rejected update: {item_id or '(no id)'}: a sweep updates pending decisions and open promises "
                                       f"only, not {table}")
    if not source.startswith(("Email · ", "Teams · ")):
        return skip("no structured source", f"skipped (no structured Email/Teams source): update to {item_id}")
    rule = None if named else ignored_by(message_of_source(source), rules, vips)
    if rule:
        ignored[rule] = ignored.get(rule, 0) + 1
        notes.append(f"skipped (ignore rule “{rule}”): update to {item_id}")
        return
    wanted = dict(raw.get("set") or {})
    row, why_not = minutes.check_update(con, table, item_id, wanted, {r[0]: None for r in con.execute("SELECT code FROM projects")})
    if why_not:
        return skip("update refused", f"rejected update: {why_not}")
    day = sent_day(source) or now().strftime("%Y-%m-%d")
    changes = minutes.made_on(table, minutes.update_changes(row, wanted, table), day)
    if not changes:
        return skip("no change", f"no change to {item_id} (already as the message left it)")
    if (link_of(source), norm(update_key(item_id, changes))) in seen:
        return skip("already proposed", f"skipped (proposed before from the same message): update to {item_id}")
    minutes.note_mention([item_id], link_of(source) or source, "cx-sweep", day)       # discussed again: BL-51
    if item_id in updated:                                             # two messages on one decision in one sweep merge
        at = updated[item_id]
        at["changes"] = {**changes, **at["changes"]}
        at["why"] = " · ".join(x for x in (at.get("why"), raw.get("why")) if x)
        return
    item = {"op": "update", "table": table, "id": item_id, "changes": changes, "based_on": row["updated_at"], "why": raw.get("why") or "",
            "source": source, "n": len(items) + 1, "match": raw.get("match", "strong"), "flags": [], "decision": "pending"}
    items.append(item)
    updated[item_id] = item



# ===== BL-218 (sprint-drafts-extraction) ===== "Probably done" from mail and Teams. The skill runs `done-candidates` over the messages it
# read (plain code: extraction.done_candidates), judges the close matches, and puts an update in the spec for each it believes:
# {"op": "update", "table": "actions" | "raid", "id": "ABC-A-003", "source": "<structured Email/Teams source>",
#  "done": {"strength": "Looks done" | "Maybe done" | "Not done", "quote": "<the words that show it>", "who": "<sender>",
#           "at": "YYYY-MM-DD HH:MM", "folder": "Sent Items" | "Inbox" | "Teams", "reason": "…", "project": "ABC", "due_date": …}}
# Stage checks it (extraction.done_check: open, its own project, raised before, from the owner or Alan or naming the owner) and stages
# a closing update (status Closed; an action also gets a latest update quoting the evidence) or, for Not done, a re-dating one, with
# the evidence as `suggested`. A closing update is approved on its own (review.individual_only), never by Approve routine.
_decision_update_before_done = decision_update


def done_update(raw, con, items, notes, why, ignored, updated, rules, vips, named, seen):
    """Stage one "probably done" update from a message, or say in notes why not (counted in why)."""
    import minutes
    skip = skipper(notes, why)
    table, item_id, source = raw.get("table"), str(raw.get("id") or ""), str(raw.get("source") or "")
    refused = done_refusal(table, item_id, source)
    if refused:
        return skip(*refused)
    rule = None if named else ignored_by(message_of_source(source), rules, vips)
    if rule:
        ignored[rule] = ignored.get(rule, 0) + 1
        return notes.append(f"skipped (ignore rule “{rule}”): done update to {item_id}")
    codes = {r[0]: None for r in con.execute("SELECT code FROM projects")}
    row, why_not = minutes.check_update(con, table, item_id, {"status": "Closed"}, codes)
    if why_not:
        return skip("update refused", f"rejected update: {why_not}")
    return stage_done(raw, row, items, skip, seen)


def stage_done(raw, row, items, skip, seen):
    """The checked done update itself: the owner rule and strength (extraction.done_check), its changes and its evidence."""
    import minutes
    table, item_id, source, done = raw["table"], row["id"], str(raw.get("source") or ""), raw["done"]
    sender = done.get("who") or message_of_source(source)["from"]
    day = sent_day(source) or str(done.get("at") or "")[:10] or now().strftime("%Y-%m-%d")
    stamp = re.search(r"Sent: (\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2})?)", source)
    done = {**done, "at": done.get("at") or (stamp.group(1) if stamp else day), "who": re.sub(r"\s*<[^>]*>", "", sender).strip()}
    strength, refused = extraction.done_check(row, done, source, sender, extraction.people())
    if refused:
        return skip("update refused", f"rejected update: {refused}")
    done["strength"] = strength
    kind = "teams" if source.startswith("Teams") else "mail"
    changes = extraction.done_changes(table, done, kind)
    if not changes or (link_of(source), norm(update_key(item_id, changes))) in seen:
        return skip("already proposed", f"skipped (nothing to stage, or proposed before from the same message): done update to {item_id}")
    minutes.note_mention([item_id], link_of(source) or source, "cx-sweep", day)        # raised again: BL-51
    mark = extraction.done_mark(done, source, kind)
    items.append({"op": "update", "table": table, "id": item_id, "changes": changes, "based_on": row["updated_at"],
                  "why": f"{strength}: {extraction.evidence_line(mark['evidence'])}", "source": source, "n": len(items) + 1,
                  "match": "strong", "flags": [] if strength == "Looks done" else ["low-confidence"], "decision": "pending",
                  "suggested": mark})
    return None


def skipper(notes, why):
    """skip(kind, note): say why something wasn't staged, and count it by kind."""
    def skip(kind, note):
        """One skipped item: its note, counted."""
        notes.append(note)
        why[kind] = why.get(kind, 0) + 1
    return skip


def done_refusal(table, item_id, source):
    """(kind, note) when a done update can't be staged at all (the wrong table, no structured source), else None."""
    if table not in ("actions", "raid", "promises"):          # BL-125 A, decision 10: promises too (only while the sweep's are on)
        return "update refused", f"rejected update: {item_id or '(no id)'}: probably done is for actions, RAID items and promises"
    if not source.startswith(("Email · ", "Teams · ")):
        return "no structured source", f"skipped (no structured Email/Teams source): done update to {item_id}"
    if not extraction.switched_on("done"):
        return "switched off", f"skipped (probably done is off in Settings › General › AI drafts): done update to {item_id}"
    return None


def _decision_or_done(raw, *args):
    if isinstance(raw.get("done"), dict):
        return done_update(raw, *args)
    if raw.get("table") in PROGRESS:                                    # BL-297: a message moves an open item forward
        return progress_update(raw, *args)
    return _decision_update_before_done(raw, *args)


decision_update = _decision_or_done


def done_candidates_cmd(spec_file):
    """`done-candidates <messages.json>`: the open items each message may close, as JSON, for the skill to judge (plain code)."""
    try:
        msgs = json.loads(Path(spec_file).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"creaite: can't read {spec_file}: {type(e).__name__}")
        return 1
    con = tracker.connect()
    out = extraction.done_candidates(con, msgs.get("messages") if isinstance(msgs, dict) else msgs)
    con.close()
    print(json.dumps({"candidates": out}, ensure_ascii=False, indent=1))
    paths.consume_draft(spec_file, file=sys.stderr)                     # BL-118: read, so the input has done its job
    return 0
# ===== end BL-218 =====

HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def calendar_window(today=None):
    """(first day, last day) the saved calendar covers (BL-42): from inbox.meetings_from ("monday": Monday of this
    week; a number: that many days back) to 7 days ahead. `today` defaults to creaite's clock."""
    today = today or now().date()
    back = (paths.load_settings().get("inbox") or {}).get("meetings_from", "monday")
    try:
        start = today - timedelta(days=int(back))
    except (TypeError, ValueError):
        start = today - timedelta(days=today.weekday())
    return start, today + timedelta(days=7)


def calendar_span(today=None):
    """(first day, last day) the saved calendar holds now, as dates, or None without one (BL-293): calendar_window(), its last
    day cut to the fetch's own seven days ahead when the calendar was saved on an earlier day."""
    try:
        fetched = json.loads(paths.CALENDAR.read_text(encoding="utf-8")).get("fetched") or ""
    except (OSError, ValueError, AttributeError):
        return None
    first, last = calendar_window(today)
    try:
        last = min(last, datetime.strptime(str(fetched)[:10], "%Y-%m-%d").date() + timedelta(days=7))
    except ValueError:  # a calendar with no fetch date: the window as it is
        pass
    return first, last


# BL-107: Microsoft 365 gives calendar times in UTC (or with their own zone). The script, not Claude, converts them to
# the laptop's time zone, read each run (never stored, so it follows travel), and files each meeting under its local
# date. Accepted: "HH:MM" (already local, under the day given), an ISO date-time with a zone ("…Z", "…+04:00"; one with
# no zone is UTC, as Graph's are), or {"dateTime", "timeZone"} with an IANA or common Windows zone name.
WINDOWS_ZONES = {"utc": "UTC", "coordinated universal time": "UTC", "gmt standard time": "Europe/London",
                 "greenwich standard time": "Atlantic/Reykjavik", "arabian standard time": "Asia/Dubai",
                 "arab standard time": "Asia/Riyadh", "w. europe standard time": "Europe/Berlin",
                 "romance standard time": "Europe/Paris", "central european standard time": "Europe/Warsaw",
                 "central europe standard time": "Europe/Budapest", "e. europe standard time": "Europe/Bucharest",
                 "india standard time": "Asia/Kolkata", "singapore standard time": "Asia/Singapore",
                 "eastern standard time": "America/New_York", "central standard time": "America/Chicago",
                 "pacific standard time": "America/Los_Angeles", "aus eastern standard time": "Australia/Sydney"}


def _zone(name):
    from datetime import timezone
    n = str(name or "UTC").strip()
    if n.lower() in ("utc", "z", "etc/utc", "coordinated universal time"):
        return timezone.utc
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(WINDOWS_ZONES.get(n.lower(), n))
    except Exception:  # noqa: BLE001  an unknown zone (or no zone data on this machine)
        return None


def local_time(value, day):
    """(local YYYY-MM-DD, local HH:MM) of a calendar time, or None when it can't be read."""
    from datetime import timezone
    if isinstance(value, str) and HHMM.match(value.strip()):
        return day, value.strip()
    if isinstance(value, dict):
        raw, tz = str(value.get("dateTime") or ""), _zone(value.get("timeZone"))
    else:
        raw, tz = str(value or ""), timezone.utc
    if not raw or tz is None:
        return None
    raw = re.sub(r"(\.\d+)", lambda m: m.group(1)[:7], raw.strip()).replace("Z", "+00:00")   # Graph's 7-digit fractions
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    loc = dt.astimezone()                     # the laptop's own zone, now
    return loc.strftime("%Y-%m-%d"), loc.strftime("%H:%M")


def localise(spec_days, bad):
    """The spec's days with each timed meeting converted to local time and filed under its local start date. A
    meeting ending after local midnight ends at 23:59 that day; one that can't be read is named in bad."""
    out = {}
    for day, events in (spec_days or {}).items():
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(day)) or not isinstance(events, list):
            bad.append(str(day))
            continue
        for ev in events:
            if not isinstance(ev, dict):
                continue
            if ev.get("all_day"):
                out.setdefault(day, []).append(ev)
                continue
            s, e = local_time(ev.get("start"), day), local_time(ev.get("end"), day)
            if not s or not e:
                bad.append(f"{day} {ev.get('title', '')} (time not readable)".strip())
                continue
            end = e[1] if e[0] == s[0] else "23:59"
            out.setdefault(s[0], []).append({**ev, "start": s[1], "end": end})
    return out


def calendar(spec_file):
    """Keep the day view's, the Inbox's and meeting prep's meetings: event ID, times, title, place, Teams or not, the
    organiser, and the invite's details for prep (BL-98, see invite_details). Ignored events (BL-97: private ones,
    ToDo invites…) are dropped and counted; a private meeting the rules let through becomes "Busy" (ID and Teams
    kept, nothing else). Days before the window start are dropped."""
    try:
        spec = json.loads(Path(spec_file).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"Can't read {spec_file}: {e}")
        debuglog.warn("sweep", f"calendar: the spec could not be read ({type(e).__name__})")
        return 1
    days, bad, ignored = {}, [], {}
    rules, vips = ignore_rules(), vip_addresses()                  # BL-97: ignored events are never saved
    start_day = calendar_window()[0].isoformat()
    for day, events in sorted(localise(spec.get("days"), bad).items()):     # BL-107: local times, local dates
        if day < start_day:              # before the window (BL-42): not kept
            continue
        kept = []
        for ev in events:
            rule = ignored_by(message_of_event(ev), rules, vips)
            if rule:
                ignored[rule] = ignored.get(rule, 0) + 1
                continue
            all_day = bool(ev.get("all_day"))
            start, end = str(ev.get("start") or ""), str(ev.get("end") or "")
            if not all_day and not (HHMM.match(start) and HHMM.match(end) and end > start):
                bad.append(f"{day} {start}-{end} {ev.get('title', '')}".strip())
                continue
            sens = str(ev.get("sensitivity") or "").lower()
            private = bool(ev.get("private")) or sens in ("private", "personal")
            org = ev.get("organiser")
            org = (str(org).strip()[:80] or False) if isinstance(org, str) else bool(org)   # True: Alan; else a name
            row = {"start": "" if all_day else start, "end": "" if all_day else end, "all_day": all_day,
                   "title": "Busy" if private else str(ev.get("title") or "Meeting")[:140],
                   "where": "" if private else str(ev.get("where") or "")[:80],
                   "teams": bool(ev.get("teams")), "private": private,
                   "organiser": False if private else org}
            if not private:
                row.update(invite_details(ev, confidential=sens == "confidential"))     # BL-98
            if str(ev.get("id") or "").strip():              # the calendar event ID (BL-42): processed state, picking
                row = {"id": str(ev["id"]).strip()[:512], **row}
            kept.append(row)
        days[day] = sorted(kept, key=lambda e: (not e["all_day"], e["start"]))
    paths.CALENDAR.write_text(json.dumps({"fetched": now().strftime("%Y-%m-%d %H:%M"), "days": days}, indent=1,
                                         ensure_ascii=False), encoding="utf-8")
    n = sum(len(v) for v in days.values())
    debuglog.info("sweep", f"calendar saved: {n} meeting(s) over {len(days)} day(s) in {datetime.now().astimezone():%Z (%z)}, "
                  f"{len(bad)} with times that could not be read, {sum(ignored.values())} ignored")
    print(f"Calendar saved: {n} meeting{'s' if n != 1 else ''} over {len(days)} day{'s' if len(days) != 1 else ''}."
          + (f" Skipped (bad times): {'; '.join(bad)}." if bad else "")
          + (f" {ignored_text(ignored)}." if ignored else ""))
    tally_ignored(ignored)
    paths.consume_draft(spec_file)                                      # BL-118: the calendar is saved
    return 0


# ===== Sweep and alerts (BL-97, BL-99, BL-98) =====
# BL-97 ignore rules (settings.json sweep.ignore). Each rule: name; where (a list of mail, teams, calendar); field
# (subject: a mail's subject or an event's title; sender: an address; channel: a Teams channel or chat); how (begins,
# contains, equals; for a sender also address or domain; "begins" looks past RE:, FW: and [CODE] tags); text; on. One built-in rule, {"builtin": "private"}, drops
# anything marked private or personal; it can be switched off, not deleted. Matching ignores case. A VIP sender
# (BL-99) is never ignored, and a thread or meeting Alan names isn't either. Only counts are kept, never content.

IGNORE_DEFAULTS = [
    {"name": "Anything marked private", "builtin": "private", "where": ["mail", "teams", "calendar"], "on": True},
    {"name": "ToDo invites", "where": ["mail", "calendar"], "field": "subject", "how": "begins", "text": "todo", "on": True},
    {"name": "humancapital", "where": ["mail"], "field": "sender", "how": "address",
     "text": "hr@brightwater.example", "on": True},
    {"name": "Info: entries", "where": ["calendar"], "field": "subject", "how": "begins", "text": "info:", "on": True},
    {"name": "FYI: entries", "where": ["calendar"], "field": "subject", "how": "begins", "text": "fyi:", "on": True},
]
IGNORE_FIELDS = {"subject": ("begins", "contains", "equals"), "sender": ("address", "domain", "begins", "contains", "equals"),
                 "channel": ("begins", "contains", "equals")}
TALLY = paths.STAGING / "sweep-ignored.json"


def ignore_rules():
    """The ignore rules (settings.json sweep.ignore, or the shipped three when the key is missing). The private rule
    is always there: a settings list that lost it gets it back, switched off."""
    rules = (paths.load_settings().get("sweep") or {}).get("ignore")
    rules = [dict(r) for r in rules if isinstance(r, dict)] if isinstance(rules, list) else [dict(r) for r in IGNORE_DEFAULTS]
    if not any(r.get("builtin") == "private" for r in rules):
        rules.insert(0, {**IGNORE_DEFAULTS[0], "on": False})
    return rules


def vip_addresses():
    """{address: full name} of the VIPs (BL-99): every address of each person the people register marks VIP."""
    if not vip_settings().get("enabled", True):
        return {}
    import propose
    return {a: v["name"] for v in propose.vip_people() for a in v["emails"]}


def address_of(text):
    """The address in "Name <a@b.c>" (or the text itself when it is an address), lower case; else ""."""
    m = re.search(r"<([^<>@\s]+@[^<>\s]+)>", text or "") or re.search(r"([^\s<>@]+@[^\s<>]+)", text or "")
    return m.group(1).strip().lower() if m else ""


def message_of_source(source):
    """A proposal source (Email · From: … · Subject: … / Teams · Channel: … · From: …) as an ignore-check message."""
    parts = {k.strip(): v.strip() for k, _, v in (p.partition(":") for p in str(source).split(" · ")[1:]) if v}
    kind = "teams" if str(source).startswith("Teams · ") else "mail"
    return {"kind": kind, "from": parts.get("From", ""), "subject": parts.get("Subject", ""),
            "channel": parts.get("Channel") or parts.get("Chat") or ""}


def message_of_event(ev):
    """A calendar event as an ignore-check message: its title, organiser address and sensitivity."""
    return {"kind": "calendar", "subject": ev.get("title") or "", "from": ev.get("organiser_email") or "",
            "private": bool(ev.get("private")) or str(ev.get("sensitivity") or "").lower() in ("private", "personal")}


def rule_matches(rule, msg):
    """Whether one ignore rule (BL-97) matches a message: by sender, subject or body, contains or exact, or the
    built-in private rule.
    """
    if not rule.get("on", True) or msg.get("kind") not in (rule.get("where") or ["mail", "teams", "calendar"]):
        return False
    if rule.get("builtin") == "private":
        return bool(msg.get("private")) or str(msg.get("sensitivity") or "").lower() in ("private", "personal")
    want = str(rule.get("text") or "").strip().lower()
    if not want:
        return False
    field, how = rule.get("field", "subject"), rule.get("how", "contains")
    if field == "sender":
        addr = address_of(msg.get("from")) or str(msg.get("from") or "").strip().lower()
        if how == "address":
            return addr == want
        if how == "domain":
            dom = want.lstrip("@")
            return addr.endswith("@" + dom) or addr.endswith("." + dom)
        have = addr
    else:
        have = " ".join(str(msg.get("subject" if field == "subject" else "channel") or "").lower().split())
    if how == "begins":          # a subject also "begins" after RE:, FW: and [CODE] tags ("RE: [ABC] ToDo …")
        bare = re.sub(r"^(?:(?:re|fw|fwd|aw|wg)\s*:\s*|\[[^\]]*\]\s*)+", "", have)
        return have.startswith(want) or bare.startswith(want)
    return have == want if how == "equals" else want in have


def ignored_by(msg, rules=None, vips=None):
    """The name of the first rule that drops msg ({kind, subject, from, channel, private|sensitivity}), or None.
    A VIP sender (BL-99) is never ignored, whatever the rule."""
    if address_of(msg.get("from")) in (vip_addresses() if vips is None else vips):
        return None
    return next((r.get("name") or "Unnamed rule" for r in (ignore_rules() if rules is None else rules)
                 if rule_matches(r, msg)), None)


def ignored_text(counts):
    """"Ignored 14: ToDo invites 9, humancapital 3, Anything marked private 2"."""
    return f"Ignored {sum(counts.values())}: " + ", ".join(f"{k} {n}" for k, n in sorted(counts.items(), key=lambda x: -x[1]))


def tally_ignored(counts):
    """Add this step's counts to the run's tally (system/staging/sweep-ignored.json), read by done."""
    if not counts:
        return
    try:
        have = json.loads(TALLY.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        have = {}
    for k, n in counts.items():
        have[k] = have.get(k, 0) + n
    TALLY.parent.mkdir(parents=True, exist_ok=True)
    TALLY.write_text(json.dumps(have, ensure_ascii=False), encoding="utf-8")


def take_tally():
    """The ignore counts gathered during this sweep (BL-97), cleared once read."""
    try:
        counts = json.loads(TALLY.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        counts = {}
    TALLY.unlink(missing_ok=True)
    return counts


def ignore_cmd(spec_file):
    """messages.json: {"named": false, "messages": [{kind, subject, from, channel, private|sensitivity}]} (or the
    list alone). Prints the indices to keep and the counts by rule."""
    try:
        spec = json.loads(Path(spec_file).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"Can't read {spec_file}: {e}")
        return 1
    msgs = spec if isinstance(spec, list) else spec.get("messages") or []
    named = isinstance(spec, dict) and bool(spec.get("named"))
    rules, vips = ignore_rules(), vip_addresses()
    keep, counts = [], {}
    for i, m in enumerate(msgs):
        rule = None if named else ignored_by(m, rules, vips)
        if rule:
            counts[rule] = counts.get(rule, 0) + 1
        else:
            keep.append(i)
    tally_ignored(counts)
    print(json.dumps({"keep": keep, "ignored": counts}, ensure_ascii=False))
    paths.consume_draft(spec_file, file=sys.stderr)                     # BL-118: the answer is printed; stdout stays the JSON alone
    return 0


# BL-98: what the saved calendar keeps of an invite for meeting prep. The body becomes plain text with the joining
# boilerplate (Teams and Outlook join links, meeting ID, passcode, dial-in numbers) taken out; those act as a key to
# the meeting and are no use for prep.
BODY_MAX = 20000
JOIN_LINE = re.compile(
    r"(microsoft teams (meeting|need help)|join (the meeting|on your computer|with a video conferencing|by phone|"
    r"conference)|click here to join|meeting id\b|passcode|password:|dial[- ]in|phone conference id|find a local number|"
    r"reset dial[- ]in pin|conference id|tel:|teams\.microsoft\.com|teams\.live\.com|aka\.ms/|meet\.google\.com|"
    r"zoom\.us/|webex\.com|for organi[sz]ers: meeting options|learn more( about teams)?\s*(\||$)|meeting options|"
    r"^\s*\+\d[\d ,#()-]{7,}|^\s*_{8,}\s*$|^\s*\.{3,}\s*$|system reference|"
    r"this meeting is being recorded|join microsoft teams meeting)", re.I)


def invite_text(body):
    """An invite body as plain text: HTML removed, the joining boilerplate stripped, blank runs collapsed."""
    import html as htmllib
    t = str(body or "")
    if re.search(r"<(html|body|div|p|br|span|table|a)\b", t, re.I):
        t = re.sub(r"(?is)<(script|style|head)\b.*?</\1>", " ", t)
        t = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|h\d)>", "\n", t)
        t = re.sub(r"(?i)<li\b[^>]*>", "\n- ", t)
        t = re.sub(r"<[^>]+>", " ", t)
        t = htmllib.unescape(t)
    t = t.replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in t.split("\n")]
    lines = [re.sub(r"https?://\S*(teams\.microsoft|teams\.live|zoom\.us|webex|meet\.google)\S*", "", ln) for ln in lines
             if not JOIN_LINE.search(ln)]
    out = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    return out[:BODY_MAX]


def invite_details(ev, confidential=False):
    """The invite fields meeting prep uses (BL-98). A confidential event keeps none of the body or attendees."""
    out = {"sensitivity": "confidential" if confidential else str(ev.get("sensitivity") or "normal").lower()[:20]}
    addr = address_of(ev.get("organiser_email"))
    if addr:
        out["organiser_email"] = addr
    if ev.get("recurrence"):
        out["recurrence"] = str(ev["recurrence"])[:40]
    if confidential:
        return out
    body = invite_text(ev.get("body"))
    if body:
        out["body"] = body
    try:
        import propose
        people, others = propose.people_pool()
    except Exception:  # noqa: BLE001  mapping names is a nicety
        people, others = [], []
    attendees = []
    for a in ev.get("attendees") or []:
        a = {"name": a} if isinstance(a, str) else a if isinstance(a, dict) else {}
        raw = str(a.get("name") or a.get("email") or "").strip()
        email = address_of(a.get("email") or raw)
        name = re.sub(r"\s*<[^>]*>\s*", "", raw).strip() or email
        if not name:
            continue
        res = None
        for probe in (email, name):
            if probe and people:
                r = propose.resolve_person(probe, people, others)
                if r["status"] in ("known", "alias", "email"):
                    res = r["name"]
                    break
        attendees.append({"name": (res or name)[:80], "email": email[:120], **({"registered": True} if res else {}),
                          "type": "optional" if str(a.get("type") or "").lower().startswith("opt") else "required",
                          "response": str(a.get("response") or "none").lower()[:12]})
    if attendees:
        out["attendees"] = attendees[:80]
    files = [str(f.get("name") if isinstance(f, dict) else f).strip()[:160] for f in ev.get("attachments") or []]
    if [f for f in files if f]:
        out["attachments"] = [f for f in files if f][:40]
    return out


# BL-99 VIPs. Anything sent by a VIP (mail, Teams, a calendar invite or update) is recorded as an alert in
# system/staging/vip.json: who, what, when, the link, the matched project (else none), Claude's gist of up to 140
# characters and a private or confidential marker. No message text is kept. An alert stays until Alan marks it seen;
# the same message is never alerted twice. The sweep, the session start and the live server's timer all record here.

VIP_FILE = paths.STAGING / "vip.json"
GIST = 140


def vip_settings():
    """The VIP alert settings (BL-99), with defaults: enabled, check_minutes, notify."""
    return {"enabled": True, "check_minutes": 30, "notify": True, **(paths.load_settings().get("vip") or {})}


def vip_state():
    """The VIP alerts and last check time from system/staging/vip.json (BL-99)."""
    try:
        st = json.loads(VIP_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        st = {}
    return {"last_check": st.get("last_check"), "alerts": [a for a in st.get("alerts") or [] if isinstance(a, dict)],
            **({"held": st["held"]} if isinstance(st.get("held"), dict) and st["held"] else {})}


def vip_save(st):
    """Write the VIP alerts to system/staging/vip.json, atomically (BL-99)."""
    VIP_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = VIP_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(VIP_FILE)


def vip_id(m):
    """A short stable ID for a VIP message, from its link, else its sender, subject and time."""
    import hashlib
    key = m.get("link") or "|".join(str(m.get(k) or "") for k in ("from", "subject", "sent"))
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def vip_project(m):
    """The project a VIP message names: the one it was given, else a code, name, alias or keyword in its subject."""
    if m.get("project"):
        return str(m["project"])
    try:
        import build_dashboard
        con = tracker.connect()
        projects = [{"code": r[0], "name": r[1]} for r in con.execute("SELECT code, name FROM projects WHERE active = 1")]
        hits = build_dashboard.project_hits(m.get("subject") or "", projects)
    except Exception:  # noqa: BLE001  a project is a nicety; the alert matters
        return None
    return hits.pop() if len(hits) == 1 else None


def vip_record(found, how="sweep"):
    """Record what the check or the sweep found. Each entry is a conversation (BL-334: {"conversation", "kind", "title",
    "people", "from", "last", "link", "sensitivity", "attachments", "summary", "items"}; conv_record) or, as before, one
    message ({kind, from, subject, sent, link, gist, sensitivity, project}). Only a conversation or a message from a followed
    address is kept; ignore rules don't apply. Returns the new or updated alerts."""
    vips = vip_addresses()
    st = vip_state()
    have = {a["id"] for a in st["alerts"]}
    held = st.setdefault("held", {}) if how in ("check", "start-up") else None
    new = []
    for m in found if isinstance(found, list) else []:
        if not isinstance(m, dict):
            continue
        is_conv = bool(m.get("conversation")) or "summary" in m or "items" in m
        got = conv_record(st, m, vips, how, held) if is_conv else msg_record(st, m, vips, how, have)
        if got:
            new.append(got)
    dirty = st.pop("_dirty", False)                                  # BL-342: a key learned or two cards merged
    if how in ("check", "start-up") or new or dirty:
        if how in ("check", "start-up") and not st.get("held"):
            st["last_check"] = now().strftime("%Y-%m-%d %H:%M")     # BL-334: not past a conversation still being waited for
        if not st.get("held"):
            st.pop("held", None)
        vip_save(st)
    return new


def msg_record(st, m, vips, how, have):
    """One message as its own alert (BL-99, the shape before BL-334), or None when it isn't from a followed address or is
    alerted already."""
    addr = address_of(m.get("from"))
    if addr not in vips:
        return None
    aid = vip_id(m)
    if aid in have:
        return None
    alert = {"id": aid, "who": vips[addr], "address": addr, "kind": m.get("kind") or "mail",
             "subject": " ".join(str(m.get("subject") or "(no subject)").split())[:200],
             "sent": str(m.get("sent") or "")[:16], "link": str(m.get("link") or "")[:1000] or None,
             "p": vip_project(m), "gist": " ".join(str(m.get("gist") or "").split())[:GIST], "marker": marker_of(m),
             **({"confidential": True} if marker_of(m) == "confidential" else {}),
             "found": how, "at": now().strftime("%Y-%m-%d %H:%M"), "seen": None}
    st["alerts"].append(alert)
    have.add(aid)
    return alert


def marker_of(m):
    """"private", "confidential" or None, from a message's or conversation's sensitivity."""
    sens = str(m.get("sensitivity") or "").lower()
    return "private" if sens in ("private", "personal") else "confidential" if sens == "confidential" else None

# ===== BL-334: alerts read the conversation, not the message =====
# The unit is the conversation (a Teams chat ID or a mail conversation ID): one card per conversation, updated in place when
# it carries on ("updated HH:MM"). The check reads everyone's messages, the title, the people and the attachment names, and
# returns Claude's own summary (at most about 300 characters) and the candidate items (actions with an owner and due date
# where stated, decisions and risks). Greetings and chatter give no candidates: the card is one quiet line. A conversation
# whose last message is under 15 minutes old is waited for, at most 15 minutes. The project is matched from the title first,
# then the people, the attachment names and the content, against the register's signals. No message text is kept: the
# summary and the candidates are Claude's words. Nothing reaches Review unless Alan asks: Create work item stages one
# candidate; Dismiss stages nothing. The sweep skips a conversation already summarised unless newer messages came after it.

SUMMARY = 300
QUIET_WAIT = 15                                         # minutes: wait for a conversation to go quiet, at most this long
CAND_TYPES = ("action", "decision", "risk")


def conv_key(m):
    """The alert ID of a conversation: from its kind and conversation ID (else its link, else its title and people)."""
    import hashlib
    cid = str(m.get("conversation") or m.get("link") or "|".join([str(m.get("title") or "")] + sorted(map(str, m.get("people") or []))))
    return hashlib.sha1(f"conv:{m.get('kind') or 'teams'}:{cid}".encode("utf-8")).hexdigest()[:12]


def _clean(text, limit):
    """One line, at most limit characters, without the word that labels a followed person (BL-288)."""
    t = re.sub(r"\s*[(\[]?\s*\bVIPs?\b\s*[)\]]?\s*", " ", " ".join(str(text or "").split()), flags=re.I).strip()
    return t[:limit]


def _when(text):
    """A "YYYY-MM-DD HH:MM" time from text, or ""."""
    m = re.match(r"(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2})", str(text or ""))
    return f"{m.group(1)} {m.group(2)}" if m else ""


def _person(text):
    """A participant as its name only (never the address)."""
    t = str(text or "").strip()
    return (t.split("<")[0].strip() or address_of(t)) if "<" in t else t


def conv_title(m, people):
    """The card's title: the chat's or thread's own title, never a generic "Group chat"; without one, the people in it."""
    t = _clean(m.get("title") or m.get("subject"), 200)
    if t and not re.fullmatch(r"(group )?chat|teams chat|meeting chat|\(no subject\)|no subject", t, re.I):
        return t
    return ", ".join(people[:4]) + (f" and {len(people) - 4} more" if len(people) > 4 else "") if people else "Conversation"


def conv_project(m, title, people_raw, attachments, summary, cands):
    """The project a conversation is about (BL-334 point 6): the title first, then the people (a register sender, an email
    domain or a key stakeholder), then the attachment names, then the content; one match only, else None."""
    try:
        import build_dashboard
        con = tracker.connect()
        projects = [{"code": r[0], "name": r[1]} for r in con.execute("SELECT code, name FROM projects WHERE active = 1")]
    except Exception:  # noqa: BLE001  a project is a nicety; the alert matters
        return None
    codes = {p["code"] for p in projects}
    text = " ".join([summary] + [c["text"] for c in cands])
    for hits in (lambda: build_dashboard.project_hits(title, projects), lambda: people_hits(people_raw),
                 lambda: build_dashboard.project_hits(" · ".join(attachments), projects),
                 lambda: build_dashboard.project_hits(text, projects)):
        found = one_hit(hits(), codes)
        if found:
            return found
    given = str(m.get("project") or "")
    return given if given in codes else None


def one_hit(hits, codes):
    """The one active project among hits, else None (none, or more than one)."""
    hits = {h for h in hits if h in codes}
    return hits.pop() if len(hits) == 1 else None


def people_hits(people):
    """Codes whose register signals name one of the people: a sender address, an email domain or a key stakeholder."""
    own = {str(d).lower() for d in (paths.load_settings().get("identity") or {}).get("own_domains") or []}
    addrs = {address_of(p) for p in people} - {""}
    names = {_person(p).lower() for p in people} - {""}
    return {cells[0] for cells in register_rows() if row_names(cells, addrs, names, own)}


def register_rows():
    """The register's Projects rows with a code, as lists of cells."""
    text = paths.REGISTER.read_text(encoding="utf-8") if paths.REGISTER.exists() else ""
    section = ""
    for line in text.splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.startswith("|") else []
        if section == "Projects" and len(cells) >= 9 and re.fullmatch(r"[A-Z][A-Z0-9]{2,6}", cells[0]):
            yield cells


def row_names(cells, addrs, names, own):
    """Whether a register row's senders, email domains (not Alan's own) or key stakeholders name one of the people."""
    split = lambda c: {x.strip().lower() for x in c.split(",") if x.strip()}        # noqa: E731
    domains = {d.lstrip("@") for d in split(cells[5])} - own
    stake = {re.sub(r"\s*\(.*?\)", "", x).strip() for x in split(cells[4])}
    return bool(addrs & split(cells[8]) or any(a.split("@")[-1] in domains for a in addrs) or names & stake)

def conv_candidates(items):
    """The candidate items, cleaned: [{n, type, text, owner, due}] (at most eight; Claude's words, never quoted text)."""
    out = []
    for it in items if isinstance(items, list) else []:
        if not isinstance(it, dict):
            continue
        typ = str(it.get("type") or "action").lower()
        text = _clean(it.get("text") or it.get("title") or it.get("description"), 200)
        if typ not in CAND_TYPES or not text:
            continue
        out.append({"type": typ, "text": text, "owner": _clean(it.get("owner"), 80) or None,
                    "due": real_date(it.get("due") or it.get("due_date"))})
        if len(out) == 8:
            break
    return out


def conv_record(st, m, vips, how, held):
    """Record or update one conversation's alert in st (BL-334). Returns the alert when it was added or changed, else None.
    held: the conversations being waited for (a check or start-up only), {key: when first waited}; None for the sweep."""
    people_raw = [str(p) for p in ([m.get("from")] + list(m.get("people") or [])) if p]
    followed = followed_in(people_raw, vips)
    if not followed:
        return None
    key, last, keys = conv_key(m), conv_last(m), conv_keys(m)
    if held is not None and still_talking(held, key, last):
        return None
    a = card_find(st, key, keys)                                       # BL-342: any key the thread has been seen under
    replied = _when(m.get("replied"))                                  # the stage 1 shape: Alan's newer message in the thread
    if a is not None:
        card_learn(st, a, keys)
        if (a.get("last") or "") >= last:
            return card_unchanged(st, a, replied)
    else:
        a = card_new(st, m, vips, how, key, keys)
    a.pop("confidential", None)                                        # set again below while it is still confidential
    a.update(conv_content(m, conv_people(people_raw, vips), people_raw))
    vip_match(a, m, st["alerts"])                                      # BL-342 part 2: New, Update or Chase against open work
    conv_finish(a, last, m.get("link"))
    if replied and replied >= last:
        replied_set(a, replied)                                        # he answered after the last message
    return a


def card_new(st, m, vips, how, key, keys):
    """A new card for a thread, added to st (BL-342: open, with the keys it was first seen under)."""
    followed = followed_in([str(p) for p in ([m.get("from")] + list(m.get("people") or [])) if p], vips)
    a = {"id": key, "conv": str(m.get("conversation") or "")[:300] or None, "kind": m.get("kind") or "teams",
         "who": vips[followed], "address": followed, "found": how, "at": now().strftime("%Y-%m-%d %H:%M"),
         "seen": None, "candidates": [], "state": "open", "keys": []}
    st["alerts"].append(a)
    card_learn(st, a, keys)
    return a


def card_unchanged(st, a, replied):
    """A thread with nothing newer: the card stays as it is, unless Alan answered it since (then it closes as replied;
    returns the card) """
    if replied and (a.get("state") or "open") == "open" and replied >= (a.get("last") or ""):
        st["_dirty"] = True
        return replied_set(a, replied)
    return None


def conv_last(m):
    """When a conversation's last message was sent ("YYYY-MM-DD HH:MM"), else now."""
    return _when(m.get("last") or m.get("sent")) or now().strftime("%Y-%m-%d %H:%M")


def followed_in(people_raw, vips):
    """The first followed address among a conversation's people, else ""."""
    return next((a for a in (address_of(p) for p in people_raw) if a in vips), "")


def conv_finish(a, last, link):
    """Merge the candidates, set the quiet flag and the times; a card seen before comes back when there is something new.
    BL-342: a card Alan answered (replied) is open again, a handled one comes back when the new message asks something of him."""
    a["candidates"] = conv_merge(a.get("candidates") or [], a.pop("_cands"))
    fresh = any(not (c.get("made") or c.get("dismissed")) for c in a["candidates"])
    private = a["marker"] == "private"                                 # a confidential one is a card like any other
    asks = bool(a.get("ask")) and a.get("type") in ("action", "decision", "risk")
    a.update({"quiet": not private and not fresh and not a.get("ask"), "sent": last, "last": last,
              "updated": now().strftime("%Y-%m-%d %H:%M"), "link": str(link or a.get("link") or "")[:1000] or None})
    if a.get("seen") and (fresh or private or asks):
        a["seen"] = None                                               # carried on with something new: back on Today
    if not a.get("seen"):
        a["state"] = "open"
        a.pop("replied_at", None)
        a.pop("handled_at", None)
    return a


def still_talking(held, key, last):
    """Point 5: True while a conversation's last message is under 15 minutes old and it hasn't been waited for 15 minutes
    (it is then held); False once it may be recorded."""
    stamp = now().strftime("%Y-%m-%d %H:%M")
    mins = lambda t: (now() - datetime.strptime(t, "%Y-%m-%d %H:%M")).total_seconds() / 60     # noqa: E731
    try:
        age = mins(last)
    except ValueError:
        age = QUIET_WAIT
    since = held.get(key) or stamp
    if age < QUIET_WAIT and mins(since) < QUIET_WAIT:
        held[key] = since
        return True
    held.pop(key, None)
    return False


def conv_people(people_raw, vips):
    """The people in a conversation by name (a followed address as the register names it), each once."""
    people, seen = [], set()
    for p in people_raw:
        n = vips.get(address_of(p)) or _person(p)
        if n and n.lower() not in seen:
            seen.add(n.lower())
            people.append(n)
    return people


def conv_content(m, people, people_raw):
    """What a conversation's card shows: its title, people, attachment names, project, summary and marker, and its
    candidates under "_cands". A private one keeps only a neutral line, the people as its title and no project or
    candidates. A confidential one (Alan, 15-10-2026, plan #17) keeps Claude's own summary and candidates like any other,
    marked "confidential": true: internal only, so no attachment names, and anything made from it is never client-visible
    and carries the Sensitive label (vip_make); it never reaches a client report."""
    marker = marker_of(m)
    attachments = [_clean(x, 120) for x in (m.get("attachments") or []) if str(x or "").strip()][:20]
    if marker == "private":
        title = ", ".join(people[:4]) or "Conversation"
        return {"subject": title, "title": title, "people": people[:12], "attachments": [], "p": None,
                "summary": f"{marker} conversation", "gist": f"{marker} conversation", "marker": marker, "_cands": [],
                "type": None, "ask": "", "due": None, "owners": []}
    closed = marker == "confidential"
    if closed:
        attachments = []
    summary, cands = _clean(m.get("summary") or m.get("gist"), SUMMARY), conv_candidates(m.get("items"))
    if closed and re.fullmatch(r"(private|confidential)( conversation)?", summary, re.I):
        summary = ""                                                    # an older reply's placeholder is not a summary
    title = conv_title(m, people)
    return {"subject": title, "title": title, "people": people[:12], "attachments": attachments,
            "p": conv_project(m, title, people_raw, attachments, summary, cands), "summary": summary,
            "gist": summary[:GIST], "marker": marker, **({"confidential": True} if closed else {}), "_cands": cands,
            **card_fields(m, cands)}


def conv_merge(old, cands):
    """The new candidates, numbered, keeping each one's made or dismissed state; earlier ones already made or dismissed
    stay so (they are not offered twice)."""
    by = {norm(c["text"]): c for c in old}
    merged = []
    for c in cands:
        prev = by.pop(norm(c["text"]), None) or {}
        merged.append({**c, **{k: prev[k] for k in ("made", "dismissed") if prev.get(k)}})
    merged += [c for c in by.values() if c.get("made") or c.get("dismissed")]
    for i, c in enumerate(merged, 1):
        c["n"] = i
    return merged

def vip_open(a):
    """Whether an alert still waits for Alan: not seen, not a quiet line, and (BL-342) not one he has already answered."""
    return not a.get("seen") and not a.get("quiet") and a.get("state") != "replied"


def cand_settled(a):
    """Mark a conversation seen once every candidate is made or dismissed (a private one has none: Dismiss settles it)."""
    c = a.get("candidates") or []
    if c and all(x.get("made") or x.get("dismissed") for x in c) and not a.get("seen"):
        a["seen"] = now().strftime("%Y-%m-%d %H:%M")


def summarised(source, conversation=None):
    """BL-334 C: the alert that has already summarised the conversation an item comes from, with nothing newer since
    (the item's Sent time is not after the summary's last message), else None. Matched by the conversation ID, else the
    link, else the kind and the thread's own title."""
    msg = message_of_source(source)
    title = re.sub(r"^((re|fw|fwd|aw)\s*:\s*|\[ext\]\s*)+", "", msg["subject"] or msg["channel"] or "", flags=re.I)
    ref = {"conv": conversation, "link": link_of(source), "title": title.strip().lower(), "kind": msg["kind"]}
    sent = _when((re.search(r"Sent: ([0-9: T-]+)", source or "") or [None, ""])[1]) or ""
    for a in vip_state()["alerts"]:
        if "summary" in a and same_conv(a, ref) and (not sent or sent <= (a.get("last") or "")):
            return a
    return None


def same_conv(a, ref):
    """Whether an alert is the conversation ref names: its conversation ID, its link, or its kind and own title."""
    if ref["conv"] and a.get("conv") == ref["conv"]:
        return True
    if ref["link"] and a.get("link") == ref["link"]:
        return True
    return bool(ref["title"]) and a.get("kind") == ref["kind"] and str(a.get("title") or "").strip().lower() == ref["title"]

# ===== end BL-334 =====

# ===== BL-342 (Part 1): a thread's card =====
# One card per thread, built around what Alan must do: a type (action, decision, fyi or risk), a due date, owners and one line
# of what is asked of him (`ask`). The card keeps every key the thread has been seen under (`conv`, `keys`): a thread matches a
# card on any of them, and two cards later found to share one are merged (newest summary kept, Handled kept if either was
# handled). `state` is open, handled (Alan pressed Handled; `handled_at`) or replied (his own message after the last one
# shows in the thread; `replied_at`; a later message from someone else opens it again). Log on the matched item stages one
# `update` proposal of its own for Review (vip_log). Claude's words and references only, never message text (BL-99), and
# never the word that labels a followed person (BL-288).

CARD_TYPES = ("action", "decision", "fyi", "risk")
KEYS_KEPT = 12


def real_date(x):
    """x as a YYYY-MM-DD date when it is a real one, else None (a due date that isn't a date is dropped)."""
    t = str(x or "").strip()[:10]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", t):
        return None
    try:
        datetime.strptime(t, "%Y-%m-%d")
    except ValueError:                                              # 2026-02-30 and the like: not a date
        return None
    return t


def card_owners(raw):
    """The people named to act: full names, each once, at most six; "you" when the ask is of Alan."""
    parts = re.split(r"\s*[;,]\s*|\s+and\s+", raw) if isinstance(raw, str) else raw if isinstance(raw, list) else []
    me, out = my_name().lower(), []
    for p in parts:
        n = _clean(p, 80)
        if n.lower() in ("you", "me") or (me and n.lower() == me):
            n = "you"
        if n and n.lower() not in {x.lower() for x in out}:
            out.append(n)
    return out[:6]


def card_fields(m, cands):
    """A thread's type, ask, due date and owners from what Claude returned. Without a type, the first candidate's, else fyi
    (a quiet thread: nothing for Alan)."""
    typ = str(m.get("type") or "").strip().lower()
    typ = "fyi" if typ in ("file", "fyi / file") else typ
    if typ not in CARD_TYPES:
        typ = cands[0]["type"] if cands else "fyi"
    return {"type": typ, "ask": _clean(m.get("ask"), 140), "due": real_date(m.get("due")),
            "owners": card_owners(m.get("owners"))}


def norm_subject(text):
    """A mail subject without Re:, Fw:, bracketed tags, case or extra spaces."""
    t = " ".join(str(text or "").split())
    while True:
        u = re.sub(r"^((re|fw|fwd|aw)\s*:\s*|\[[^\]]*\]\s*)+", "", t, flags=re.I)
        if u == t:
            break
        t = u
    return t.strip().lower()


def conv_keys(m):
    """Every key a found thread can be known by: its conversation ID, its link, and (mail) a local key from the normalised
    subject and the sorted participant addresses."""
    import hashlib
    keys = []
    if m.get("conversation"):
        keys.append("id:" + str(m["conversation"])[:300])
    if m.get("link"):
        keys.append("link:" + str(m["link"])[:1000])
    subject = norm_subject(m.get("subject") or m.get("title"))
    if (m.get("kind") or "teams") == "mail" and subject:
        people = sorted({address_of(p) or str(p).strip().lower() for p in [m.get("from")] + list(m.get("people") or []) if p})
        keys.append("loc:" + hashlib.sha1((subject + "|" + ",".join(people)).encode("utf-8")).hexdigest()[:16])
    return keys


def card_keys(a):
    """The keys a card is known by: those it stored, and (an older card) its conversation ID and link."""
    return set(a.get("keys") or []) | ({"id:" + a["conv"]} if a.get("conv") else set()) | \
        ({"link:" + a["link"]} if a.get("link") else set())


def card_find(st, key, keys):
    """The card a found thread belongs to: its alert ID or any shared key. Two or more are merged into the first."""
    hits = [x for x in st["alerts"] if x.get("id") == key or same_thread(card_keys(x), set(keys))]
    for extra in hits[1:]:
        card_merge(st, hits[0], extra)
    return hits[0] if hits else None


def same_thread(have, keys):
    """Whether a card's keys and a found thread's keys name one thread: they share a key, and the two conversation IDs
    (when both are known) agree (two chats that share a link are still two)."""
    ids_a, ids_b = {k for k in have if k.startswith("id:")}, {k for k in keys if k.startswith("id:")}
    if ids_a and ids_b and not ids_a & ids_b:
        return False
    return bool(have & keys)


def card_learn(st, a, keys):
    """Add the keys a thread was seen under to its card (and its conversation ID, once known)."""
    have = list(a.get("keys") or [])
    new = [k for k in keys if k not in have]
    if new or "keys" not in a:
        a["keys"] = (have + new)[-KEYS_KEPT:]
        st["_dirty"] = True
    ident = next((k[3:] for k in keys if k.startswith("id:")), "")
    if ident and not a.get("conv"):
        a["conv"] = ident
        st["_dirty"] = True


def card_merge(st, keep, drop):
    """Fold the card `drop` into `keep` (two cards for one thread): the newer one's summary and fields, the keys of both,
    the candidates of both with their made or dismissed state, and Handled when either was handled. `drop` goes."""
    newer, older = (drop, keep) if (drop.get("last") or "") > (keep.get("last") or "") else (keep, drop)
    for f in ("title", "subject", "summary", "gist", "people", "attachments", "p", "marker", "type", "ask", "due", "owners",
              "link", "sent", "last", "updated", "quiet", "who", "address"):
        if f in newer:
            keep[f] = newer[f]
    keep.pop("confidential", None)
    if newer.get("confidential"):
        keep["confidential"] = True
    keep["keys"] = list(dict.fromkeys((keep.get("keys") or []) + (drop.get("keys") or [])))[-KEYS_KEPT:]
    keep["conv"] = keep.get("conv") or drop.get("conv")
    keep["candidates"] = conv_merge(older.get("candidates") or [], newer.get("candidates") or [])
    merge_marks(keep, drop)
    merge_state(keep, drop, newer)
    st["alerts"].remove(drop)
    st["_dirty"] = True


def merge_marks(keep, drop):
    """What a card remembers of its work: made stays, and logged stays when both cards are matched to the same item."""
    if drop.get("made") and not keep.get("made"):
        keep["made"] = drop["made"]
    dm, km = drop.get("match") or {}, keep.get("match") or {}
    if dm.get("logged") and km and not km.get("logged") and dm.get("id") == km.get("id"):
        km["logged"] = dm["logged"]


def merge_state(keep, drop, newer):
    """The merged card's state: handled when either was; seen when both were; otherwise open (or replied, as the newer was)."""
    handled = [x for x in (keep, drop) if x.get("state") == "handled"]
    if handled:
        keep.update({"state": "handled", "handled_at": handled[0].get("handled_at"), "seen": handled[0].get("seen")})
    elif keep.get("seen") and drop.get("seen"):
        keep["seen"] = max(keep["seen"], drop["seen"])
    else:
        keep["seen"] = None
        keep["state"] = newer.get("state") or "open"
        if keep["state"] == "replied":
            keep["replied_at"] = newer.get("replied_at")


def replied_set(a, when):
    """Close a card as replied (Alan answered in the thread at `when`). A handled or dismissed card stays as it is."""
    if a.get("seen") or a.get("state") == "handled":
        return a
    a["state"], a["replied_at"] = "replied", when
    return a


def vip_replied(aid, when=None):
    """Close the card aid as replied at `when` (default now); only when that is not before its last message. Returns True
    when the card changed."""
    st = vip_state()
    a = next((x for x in st["alerts"] if x.get("id") == aid), None)
    when = _when(when) or now().strftime("%Y-%m-%d %H:%M")
    if a is None or a.get("state") == "replied" or when < (a.get("last") or "") or replied_set(a, when).get("state") != "replied":
        return False
    vip_save(st)
    return True


def vip_handled(ids=None):
    """Handled (BL-342): the same effect as Dismiss (out of Needs attention, kept in vip.json, Undo puts it back), recorded
    as `handled` with a time. Returns the IDs settled."""
    st, done, at = vip_state(), [], now().strftime("%Y-%m-%d %H:%M")
    for a in st["alerts"]:
        if not a.get("seen") and (ids is None or a["id"] in ids):
            a.update({"seen": at, "state": "handled", "handled_at": at})
            done.append(a["id"])
    if done:
        vip_save(st)
    return done


def vip_sort(alerts, today=None):
    """Overdue cards first (oldest due date first), then by due date, then by last message, newest first."""
    today = today or now().strftime("%Y-%m-%d")
    by_last = sorted(alerts, key=lambda a: a.get("last") or a.get("sent") or "", reverse=True)
    return sorted(by_last, key=lambda a: (0 if a.get("due") and a["due"] < today else 1, a.get("due") or "9999-12-31"))


def logged_state(logged, item_id=None):
    """Where a logged update is: "staged" (pending in Review), "decided" (decided there, not applied yet), "applied" or "gone"."""
    name = str((logged or {}).get("proposal") or "")
    if not re.fullmatch(r"proposed-[\w.-]+\.json", name):
        return "gone"
    for d, state in ((paths.STAGING, None), (paths.APPLIED, "applied")):
        try:
            data = json.loads((d / name).read_text(encoding="utf-8"))
        except (OSError, ValueError):                              # not in this folder (or unreadable): look in the other
            continue
        item = next((i for i in data.get("items") or [] if i.get("op") == "update" and i.get("id") == item_id), None)
        if item is None:
            return "gone"
        return state or ("staged" if item.get("decision") == "pending" else "decided")
    return "gone"


def log_target(a):
    """(the matched action's ID, its row) for a card that may be logged; raises ValueError with a reason to show."""
    if a.get("marker") == "private":
        raise ValueError("Nothing to log for a private conversation.")
    item_id = str((a.get("match") or {}).get("id") or "") if isinstance(a.get("match"), dict) else ""
    if not item_id:
        raise ValueError("No matched item to log it on.")
    if "-A-" not in item_id:
        raise ValueError("Log is for actions; open the item and add the update there.")
    row = tracker.fetch(tracker.connect(), "actions", item_id)
    if row is None or row["status"] not in ("Open", "Delayed"):
        raise ValueError("That item isn't open any more.")
    return item_id, row


def vip_log(aid):
    """Log a matched thread on its item (BL-342, decision b): a thin wrapper over vip_update_stage (Part 2), which stages the one
    pending `update` of the action for Review. Adds this wrapper's refusals (private thread, no matched item, not an action, not
    open) and the card's state: clicking again stages nothing new. Returns {"proposal", "id", "line", "lines", "added", "state",
    "already", "logged"}; raises LookupError (no such card) or ValueError with a reason to show. Hold VIP_WRITE around it."""
    a = vip_find(aid)
    if a is None:
        raise LookupError("That thread isn't on Today any more.")
    item_id, _row = log_target(a)
    was = (a.get("match") or {}).get("logged")
    if isinstance(was, dict) and logged_state(was, item_id) != "gone":
        return {"proposal": was.get("proposal"), "id": item_id, "state": logged_state(was, item_id), "already": True,
                "added": False, "logged": {**was, "state": logged_state(was, item_id)}}
    got = vip_update_stage(aid)
    logged = {**(vip_find(aid).get("match") or {}).get("logged", {}), "state": "staged"}
    return {**got, "state": "staged", "already": False, "logged": logged}

# ===== end BL-342 =====



def vip_seen(ids=None):
    """Mark alerts seen (all of them when ids is None). Returns how many changed."""
    st, n = vip_state(), 0
    for a in st["alerts"]:
        if not a.get("seen") and (ids is None or a["id"] in ids):
            a["seen"] = now().strftime("%Y-%m-%d %H:%M")
            n += 1
    if n:
        vip_save(st)
    return n


# ===== BL-296 (sprint-vip-p2-server): Dismiss, Undo and Create work item on a followed person's message =====
# Dismiss is Seen under a plainer name (the alert stays in vip.json, out of Needs attention and the count); Undo puts it back.
# Create work item fills the new-item form from what the alert holds (references only, never message text, BL-99), stages
# the item as the dashboard's own approved proposal (nothing is applied here), dismisses the alert and records on it
# `made`: {"proposal", "n", "id", "at"}, with the ID once an apply has written it. Nothing returned names how a sender is
# followed (BL-288).

MADE_TYPES = {"action": ("actions", None), "risk": ("raid", "Risk"), "issue": ("raid", "Issue"),
              "decision": ("decisions", None)}
MADE_FIELDS = {"actions": ("description", "owner", "due_date", "priority", "workstream", "latest_update", "milestone"),
               "raid": ("description", "owner", "due_date", "impact", "likelihood", "response_action", "workstream",
                        "milestone"),
               "decisions": ("decision", "made_by", "needed_by", "options", "reasoning", "status")}
LONG_FIELDS = ("options", "reasoning", "latest_update", "response_action")
# A work item made from a confidential conversation (Alan, 15-10-2026, plan #17): internal only. It is never client-visible
# (whatever the form sent) and carries the built-in Sensitive label, which keeps it out of a client report or a client-safe
# one-pager unless Alan himself makes it client-visible and includes it.
CONFIDENTIAL_MADE = {"client_visible": 0, "labels": ["Sensitive"], "label_reason": "Made from a confidential message"}


def vip_find(aid):
    """The alert with this ID (any state), or None."""
    return next((a for a in vip_state()["alerts"] if a.get("id") == aid), None)


def vip_dismiss(ids=None, cand=None):
    """Dismiss alerts (all of them when ids is None): out of Needs attention, kept in vip.json. Returns the IDs dismissed.
    BL-334: with cand, only that candidate item of the one conversation named (nothing is staged); the conversation goes
    once all of its candidates are made or dismissed."""
    if cand is not None:
        return cand_dismiss(ids or set(), cand, True)
    st, done = vip_state(), []
    for a in st["alerts"]:
        if not a.get("seen") and (ids is None or a["id"] in ids):
            a["seen"] = now().strftime("%Y-%m-%d %H:%M")
            done.append(a["id"])
    if done:
        vip_save(st)
    return done


def cand_of(a, cand):
    """Candidate number cand on an alert's card, or None."""
    return next((x for x in (a or {}).get("candidates") or [] if x.get("n") == cand), None)


def cand_dismiss(ids, cand, on):
    """BL-334: dismiss (on) or put back one candidate item of the conversations named (a made one whose proposal has gone is
    forgotten, as vip_undismiss does for a message). Nothing is staged. Returns the IDs."""
    st, done = vip_state(), []
    for a in st["alerts"]:
        c = cand_of(a, cand) if a["id"] in ids else None
        if c and on and not (c.get("dismissed") or c.get("made")):
            c["dismissed"] = now().strftime("%Y-%m-%d %H:%M")
            cand_settled(a)
            done.append(a["id"])
        elif c and not on and (c.get("dismissed") or (isinstance(c.get("made"), dict) and made_state(c["made"]) == "gone")):
            c.pop("dismissed", None)
            if isinstance(c.get("made"), dict) and made_state(c["made"]) == "gone":
                c.pop("made")                                          # its proposal was removed before an apply (Undo)
            a["seen"] = None
            done.append(a["id"])
    if done:
        vip_save(st)
    return done


def vip_undismiss(ids, cand=None):
    """Undo a Dismiss: the alerts come back to Needs attention. A made item whose proposal has gone (removed before an
    apply) is forgotten with it. Returns the IDs restored. BL-334: with cand, that candidate item comes back."""
    if cand is not None:
        return cand_dismiss(ids, cand, False)
    st, done = vip_state(), []
    for a in st["alerts"]:
        if a["id"] in ids and a.get("seen"):
            a["seen"] = None
            if a.get("state") == "handled":
                a["state"] = "open"                                    # BL-342: Handled undone
                a.pop("handled_at", None)
            if isinstance(a.get("made"), dict) and made_state(a["made"]) == "gone":
                a.pop("made")
            done.append(a["id"])
    if done:
        vip_save(st)
    return done


def alert_source(a):
    """The alert as an item's source, in the sweep's own format (the tracker conventions), with the message's link."""
    who = f"{a.get('who') or ''} <{a['address']}>" if a.get("address") else str(a.get("who") or "")
    link = f" · Link: {a['link']}" if a.get("link") else ""
    sent, subject = a.get("sent") or "", a.get("subject") or ""
    if a.get("kind") == "teams":
        return f"Teams · Chat: {subject} · From: {a.get('who') or ''} · Sent: {sent}{link}"
    if a.get("kind") == "calendar":
        return f"Calendar · From: {who} · Subject: {subject} · Sent: {sent}{link}"
    return f"Email · From: {who} · Subject: {subject} · Sent: {sent}{link}"


def active_projects():
    """{code: name} of the active projects."""
    try:
        con = tracker.connect()
        return {c: n for c, n in con.execute("SELECT code, name FROM projects WHERE active = 1")}
    except Exception:  # noqa: BLE001  no database yet: no projects
        return {}


def my_name():
    """Alan's full name, from settings identity (the owner of what he makes)."""
    return str((paths.load_settings().get("identity") or {}).get("name") or "").strip()


def made_state(made):
    """Where a made item is: "applied" (its ID filled in), "staged", or "gone" (its proposal was removed unapplied)."""
    if made.get("id"):
        return "applied"
    name = str(made.get("proposal") or "")
    if not re.fullmatch(r"proposed-[\w.-]+\.json", name):
        return "gone"
    for d in (paths.STAGING, paths.APPLIED):
        try:
            data = json.loads((d / name).read_text(encoding="utf-8"))
        except (OSError, ValueError):  # not in this folder (or unreadable): look in the other
            continue
        item = next((i for i in data.get("items") or [] if i.get("n") == made.get("n")), None)
        if item and item.get("result_id"):
            made["id"] = item["result_id"]
            return "applied"
        return "staged"
    return "gone"


def vip_made_refresh():
    """Fill in the ID of each made item an apply has written since; saves only when one changed. Returns the state."""
    st, changed = vip_state(), False
    for a in st["alerts"]:
        for m in [a.get("made")] + [c.get("made") for c in a.get("candidates") or []]:     # BL-334: each candidate's too
            if isinstance(m, dict) and not m.get("id"):
                made_state(m)
                changed = changed or bool(m.get("id"))
    if changed:
        vip_save(st)
    return st


def made_view(made):
    """A made item as a route returns it: the proposal, the ID once applied, and where it is."""
    if not isinstance(made, dict):
        return None
    m = dict(made)
    m["state"] = made_state(m)
    return m


def vip_prefill(aid, kind=None, cand=None):
    """The new-item form's values for an alert, from its references only: the type, the project (code and name; none when
    the alert has no active project), the subject as the description, Alan as owner, no due date, raised on the sent date,
    the source in the sweep's format and the link. Raises LookupError for an unknown alert, ValueError for a wrong type."""
    a, c = prefill_target(aid, cand)
    kind = kind or (c or {}).get("type") or "action"                    # BL-334: a candidate's own type unless one is chosen
    if kind not in MADE_TYPES:
        raise ValueError("Make an action, a risk, an issue or a decision.")
    table, rtype = MADE_TYPES[kind]
    projects = active_projects()
    code = a.get("p") if a.get("p") in projects else None
    v = prefill_values(table, rtype, a, c or {})
    sent = str(a.get("sent") or "")[:10]
    return {"id": aid, "type": kind, "table": table, "project": code, "project_name": projects.get(code) if code else None,
            "needs_project": code is None, "values": v,
            "raised": sent if re.fullmatch(r"\d{4}-\d{2}-\d{2}", sent) else None,
            "source": alert_source(a), "link": a.get("link"), "who": a.get("who"), "sent": a.get("sent"),
            "kind": a.get("kind") or "mail", "marker": a.get("marker"),
            "made": made_view((c or a).get("made")), **({"cand": cand} if c else {})}


def prefill_target(aid, cand):
    """(alert, candidate or None) for a prefill; raises LookupError when either has gone."""
    a = vip_find(aid)
    if a is None:
        raise LookupError("That message isn't in Needs attention any more.")
    c = cand_of(a, cand) if cand is not None else None
    if cand is not None and c is None:
        raise LookupError("That item isn't on the card any more.")
    return a, c


def prefill_values(table, rtype, a, c):
    """The form's first values: a candidate's words, owner and due date (BL-334), else the subject with Alan as owner."""
    head, owner, due = c.get("text") or a.get("subject") or "", c.get("owner") or my_name() or None, c.get("due")
    if table == "decisions":
        return {"decision": head, "made_by": owner, "needed_by": due}
    return {"description": head, "owner": owner, "due_date": due, **({"type": rtype} if rtype else {})}


def made_values(pre, values):
    """The new item's values: the form's (known fields only) over the prefill's; the raised date and source as prefilled."""
    values = values if isinstance(values, dict) else {}
    v = {k: x for k, x in pre["values"].items() if x not in (None, "")}
    for k in MADE_FIELDS[pre["table"]]:
        if k not in values:
            continue
        x = values[k]
        if x in (None, ""):
            v.pop(k, None)
        elif isinstance(x, str):
            v[k] = (x.strip() if k in LONG_FIELDS else " ".join(x.split()))[:2000]
        elif isinstance(x, (int, float)) and not isinstance(x, bool):
            v[k] = x
    v["project"] = str(values.get("project") or pre.get("project") or "").strip()
    made_day(pre, v)
    v["source"] = pre["source"]
    return v


def made_day(pre, v):
    """The made item's day: an action's or RAID item's raised date; a made decision's date (BL-334 found it: a decision has
    no raised date), the day the message was sent."""
    day = pre.get("raised") or now().strftime("%Y-%m-%d")
    if pre["table"] != "decisions":
        v["raised"] = day
    elif (v.get("status") or "Made") != "Pending":
        v.setdefault("date", day)


def vip_make(aid, kind=None, values=None, cand=None):
    """Stage a work item made from an alert as a pending proposal for Review (proposed-…-dashboard.json; BL-334: "Create work
    item stages that item as a proposal for Review", check 45; nothing is applied here or by the page's Save), dismiss the
    alert and record the proposal on it. Returns {"proposal", "n", "table", "values"}; raises
    LookupError, or ValueError with a reason to show (no project, no description, a field that fails validation)."""
    import propose
    pre = vip_prefill(aid, kind, cand)
    if cand is not None and pre.get("made"):
        raise ValueError("That item is already made.")
    v = made_values(pre, values)
    if pre.get("marker") == "confidential":
        v.update(CONFIDENTIAL_MADE)                                     # never client-visible; the Sensitive label carried
    if v["project"] not in active_projects():
        raise ValueError("Choose a project for it first.")
    head = "decision" if pre["table"] == "decisions" else "description"
    if not str(v.get(head) or "").strip():
        raise ValueError("Give it a description.")
    spec = {"created": now().strftime("%Y-%m-%dT%H:%M:%S"), "source_run": "dashboard", "files": [],
            "items": [{"n": 1, "op": "new", "table": pre["table"], "values": v, "match": "strong", "flags": [],
                       "decision": "pending", "edited_in": "dashboard"}]}
    propose.complete(spec)
    propose.people_check_spec(spec)                                     # BL-55: a registered name as the register has it
    bad = [why for k, why in propose.check(spec).values() if k == "invalid"]
    if bad:
        raise ValueError(f"Not staged: {bad[0]}")
    stamp, out, n = now().strftime("%Y-%m-%d-%H%M%S"), None, 1
    while out is None or out.exists() or (paths.APPLIED / out.name).exists():    # never a name already used
        out = paths.STAGING / f"proposed-{stamp}-dashboard{f'-{n}' if n > 1 else ''}.json"
        n += 1
    paths.STAGING.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    mark_made(aid, cand, {"proposal": out.name, "n": 1, "id": None, "at": now().strftime("%Y-%m-%d %H:%M")})
    return {"proposal": out.name, "n": 1, "table": pre["table"], "values": spec["items"][0]["values"]}


def mark_made(aid, cand, made):
    """Record a made item on its alert (dismissing it), or on its one candidate (BL-334: the card goes once all are settled)."""
    st = vip_state()
    for a in st["alerts"]:
        c = cand_of(a, cand) if a["id"] == aid and cand is not None else None
        if c:
            c["made"] = made
            cand_settled(a)
        elif a["id"] == aid and cand is None:
            a["seen"] = a.get("seen") or now().strftime("%Y-%m-%d %H:%M")
            a["made"] = made
    vip_save(st)
# ===== end BL-296 =====


def vip_cmd(a):
    """Run the vip command (BL-99): print the addresses to check, record alerts in system/staging/vip.json
    (references and a gist, never message text), mark them seen or list the unseen ones.
    """
    if a.what == "addresses":
        st = vip_state()
        print(json.dumps({"enabled": vip_settings().get("enabled", True), "addresses": vip_addresses(),
                          "since": st["last_check"] or last_sweep() and last_sweep().strftime("%Y-%m-%d %H:%M")},
                         ensure_ascii=False))
        return 0
    if a.what == "list":
        print(json.dumps([x for x in vip_state()["alerts"] if not x.get("seen")], ensure_ascii=False))
        return 0
    if a.what == "seen":
        n = vip_seen(None if a.all else set(a.args))
        print(f"Marked {n} VIP alert{'s' if n != 1 else ''} seen.")
        return 0
    if not a.args:
        print("Give the found messages' JSON file.")
        return 2
    try:
        found = json.loads(Path(a.args[0]).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"Can't read {a.args[0]}: {e}")
        return 1
    new = vip_record(found.get("messages") if isinstance(found, dict) else found, a.found)
    print(f"VIP: {len(new)} new alert{'s' if len(new) != 1 else ''}" +
          "".join(f"\n  {x['who']}: {x['subject']} ({x['sent']}){' · ' + x['marker'] if x['marker'] else ''}"
                  for x in new))
    paths.consume_draft(a.args[0])                                      # BL-118: recorded
    return 0


def main(argv):
    """Run the sweep command in `argv` (see the module docstring)."""
    ap = argparse.ArgumentParser(prog="sweep.py")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("due")
    w = sub.add_parser("window")
    w.add_argument("--days", type=int)
    sub.add_parser("lock")
    ul = sub.add_parser("unlock")
    ul.add_argument("--if-idle", action="store_true")              # BL-328: Health's Release
    st = sub.add_parser("stage")
    st.add_argument("spec")
    d = sub.add_parser("done")
    d.add_argument("--started", required=True)
    d.add_argument("--normal", action="store_true")
    d.add_argument("--summary", default="")
    f = sub.add_parser("fail")
    f.add_argument("--message", required=True)
    sub.add_parser("calendar-window")
    c = sub.add_parser("calendar")
    c.add_argument("spec")
    ig = sub.add_parser("ignore")
    ig.add_argument("spec")
    tr = sub.add_parser("transcripts")
    tr.add_argument("what", choices=["todo", "record", "show"])
    tr.add_argument("args", nargs="*")
    vp = sub.add_parser("vip")
    vp.add_argument("what", choices=["addresses", "record", "seen", "list"])
    vp.add_argument("args", nargs="*")
    vp.add_argument("--found", default="sweep", choices=["sweep", "start-up", "check"])
    vp.add_argument("--all", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "due":
        print(json.dumps(due_info()))
        return 0
    if a.cmd == "window":
        print(json.dumps(window(a.days)))
        return 0
    if a.cmd == "lock":
        return lock()
    if a.cmd == "unlock":
        return unlock(a.if_idle)
    if a.cmd == "stage":
        return stage(a.spec)
    if a.cmd == "done":
        if a.normal:
            paths.SWEEP_STATE.write_text(a.started[:16] + "\n", encoding="utf-8")
        counts = take_tally()                                   # BL-97: what the ignore rules dropped, counts only
        summary = "; ".join(x for x in (a.summary, ignored_text(counts) if counts else "") if x)
        log_line(f"sweep ok{' (normal)' if a.normal else ''}{' | ' + summary if summary else ''}")
        debuglog.info("sweep", f"done{' (normal)' if a.normal else ''}: {debuglog.rule(summary, 200) or 'no summary'}")
        print("Recorded." + (f" Last sweep: {tracker.shown(a.started[:16])}." if a.normal else "")
              + (f" {ignored_text(counts)}." if counts else ""))
        return 0
    if a.cmd == "calendar":
        return calendar(a.spec)
    if a.cmd == "calendar-window":
        first, last = calendar_window()
        print(json.dumps({"from": first.isoformat(), "to": last.isoformat()}))
        return 0
    if a.cmd == "ignore":
        return ignore_cmd(a.spec)
    if a.cmd == "vip":
        return vip_cmd(a)
    if a.cmd == "transcripts":
        import transcripts
        return transcripts.main([a.what, *a.args])
    if a.cmd == "fail":
        take_tally()
        log_line(f"sweep FAILED | {a.message}")
        debuglog.error("sweep", f"sweep failed: {debuglog.rule(a.message, 200)}")
        print("Failure recorded; the next sweep will cover the gap.")
        return 0
    ap.print_help()
    return 2


REBUILD_AFTER = ("stage", "calendar", "done", "fail")      # BL-110: these change what the dashboard shows, so the dashboard is rebuilt



# ===== BL-218 (sprint-drafts-extraction) ===== the command for "probably done": sweep.py done-candidates <messages.json>
_main_before_done = main


def _main_with_done(argv):
    if len(argv) == 2 and argv[0] == "done-candidates":
        return done_candidates_cmd(argv[1])
    return _main_before_done(argv)


main = _main_with_done
# ===== end BL-218 =====

# ===== BL-297 (sprint-smart-updates) ===== Smarter updates from mail and Teams.
# `expected <CODE> [--date YYYY-MM-DD] [--subject "…"] [--text "…"]`: the project's open actions, RAID items and pending decisions, the
# same JSON as minutes.py expected (BL-65), read only. With a subject or text, each item carries `match` {score, strength, why} from
# extraction.rank_open and each list is sorted best first; with --date, items raised after that day are left out.
# A message that moves an open item forward (rebooked, re-dated, progressed, blocked, waiting on someone) is staged as an update to it:
# {"op": "update", "table": "actions" | "raid", "id": "ABC-A-007", "set": {"latest_update": "DD-MM-YYYY: …", "due_date": "YYYY-MM-DD"},
#  "why": "<the few words>", "source": "<structured Email/Teams source>"}. An action may change latest_update and due_date, a RAID item
# due_date and response_action; never the status (closing is "probably done", BL-218), owner, title or project.
PROGRESS = {"actions": ("latest_update", "due_date"), "raid": ("due_date", "response_action")}


def progress_update(raw, con, items, notes, why, ignored, updated, rules, vips, named, seen):
    """Stage one update that moves an open action or RAID item forward, or say in notes why not (counted in why)."""
    import minutes
    skip = skipper(notes, why)
    table, item_id, source = raw.get("table"), str(raw.get("id") or ""), str(raw.get("source") or "")
    if not source.startswith(("Email · ", "Teams · ")):
        return skip("no structured source", f"skipped (no structured Email/Teams source): update to {item_id}")
    rule = None if named else ignored_by(message_of_source(source), rules, vips)
    if rule:
        ignored[rule] = ignored.get(rule, 0) + 1
        return notes.append(f"skipped (ignore rule “{rule}”): update to {item_id}")
    wanted = dict(raw.get("set") or {})
    extra = sorted(set(wanted) - set(PROGRESS[table]))
    if extra:
        return skip("update refused", f"rejected update: {item_id}: a message may change {', '.join(PROGRESS[table])} only, "
                                      f"not {', '.join(extra)}")
    row, why_not = minutes.check_update(con, table, item_id, wanted, {r[0]: None for r in con.execute("SELECT code FROM projects")})
    if why_not:
        return skip("update refused", f"rejected update: {why_not}")
    return stage_progress(raw, row, items, skip, seen, updated)


def stage_progress(raw, row, items, skip, seen, updated):
    """The checked update itself: what changes, once per message, two from one sweep merged."""
    import minutes
    table, item_id, source = raw["table"], row["id"], str(raw.get("source") or "")
    changes = minutes.update_changes(row, dict(raw.get("set") or {}), table)
    if not changes:
        return skip("no change", f"no change to {item_id} (already as the message left it)")
    if (link_of(source), norm(update_key(item_id, changes))) in seen:
        return skip("already proposed", f"skipped (proposed before from the same message): update to {item_id}")
    minutes.note_mention([item_id], link_of(source) or source, "cx-sweep", sent_day(source) or now().strftime("%Y-%m-%d"))
    if item_id in updated:
        at = updated[item_id]
        at["changes"] = {**changes, **at["changes"]}
        at["why"] = " · ".join(x for x in (at.get("why"), raw.get("why")) if x)
        return None
    item = {"op": "update", "table": table, "id": item_id, "changes": changes, "based_on": row["updated_at"], "why": raw.get("why") or "",
            "source": source, "n": len(items) + 1, "match": raw.get("match", "strong"), "flags": [], "decision": "pending"}
    items.append(item)
    updated[item_id] = item
    return None


def expected(code, day=None, subject="", text=""):
    """The open items a message for project `code` may move forward (minutes.py expected's JSON), best matches first when the
    message's subject or words are given."""
    import minutes
    out = minutes.expected_items(code, "", datetime.strptime(day, "%Y-%m-%d").date() if day else None)
    out["how_to_use"] = ("A message that moves one of these forward (rebooked, re-dated, progressed, blocked, waiting on someone) becomes "
                         "an update to it (op: update), never a new item; leave the rest alone.")
    if not (subject or text) and not day:
        return out
    con = tracker.connect()
    try:
        ranked = extraction.rank_open(con, code, text or subject, subject, day)
    finally:
        con.close()
    for key in ("actions", "risks_and_issues_without_response", "other_open_raid", "decisions_needed"):
        out[key] = rank_list(out[key], ranked, bool(subject or text))
    return out


def rank_list(rows, ranked, scored):
    """One expected list: items raised after the message left out, and, when scored, each with its match, best first."""
    kept = [r for r in rows if r["id"] in ranked]
    if not scored:
        return kept
    for r in kept:
        r["match"] = ranked[r["id"]]
    return sorted(kept, key=lambda r: -r["match"]["score"])


def expected_cmd(argv):
    """`sweep.py expected <CODE> [--date] [--subject] [--text]`: print the expected items as JSON."""
    ap = argparse.ArgumentParser(prog="sweep.py expected")
    ap.add_argument("code")
    ap.add_argument("--date")
    ap.add_argument("--subject", default="")
    ap.add_argument("--text", default="")
    a = ap.parse_args(argv)
    print(json.dumps(expected(a.code.upper(), a.date, a.subject, a.text), indent=2, ensure_ascii=False))
    return 0


_main_before_expected = main


def _main_with_expected(argv):
    if argv[:1] == ["expected"]:
        return expected_cmd(argv[1:])
    return _main_before_expected(argv)


main = _main_with_expected
# ===== end BL-297 =====

# ===== BL-342 part 2: match a thread to open work =====
# A card says New, Update or Chase against the project's open actions, or nothing when no project was matched. Plain code
# builds the short candidate list (vip_open_items) and validates what the model suggests (vip_match); the tracker is only
# ever read (a read-only connection). A card's "match" is {"id", "relation": "new"|"update"|"chase", "why", "t", "count"
# (cards on the same item), "logged" ({"proposal", "at"} once a line was staged; the one place a card records it)}. Updates are staged by vip_update_stage as
# a pending proposal for Review (one op: update on latest_update; several threads for one item add a line to the same one).
MATCH_RELATIONS = ("new", "update", "chase")
MATCH_ITEMS = 15
MATCH_WHY = 140
NEUTRAL_LINE = "Discussed in a confidential thread, {day}"


def vip_ro():
    """A read-only connection to the tracker (rows by column name): the match never writes it."""
    import sqlite3
    con = sqlite3.connect(f"file:{paths.DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def _thread_text(thread):
    """The words a thread offers for matching: its title, summary and candidate texts (Claude's own words)."""
    return " ".join([str(thread.get("title") or thread.get("subject") or ""), str(thread.get("summary") or "")] +
                    [str(c.get("text") or "") for c in thread.get("items") or [] if isinstance(c, dict)])


def _open_actions(con, project):
    """{id: row} of a project's open actions (Open or Delayed)."""
    return {r["id"]: dict(r) for r in con.execute(
        "SELECT id, project, description, owner, due_date, status, latest_update, updated_at FROM actions "
        "WHERE project = ? AND status IN ('Open', 'Delayed')", (project,))}


def _owner_in(thread, owner, register):
    """Whether an item's owner is one of the thread's people (by name, alias or address)."""
    people = " ".join(str(p) for p in (thread.get("people") or []) + (thread.get("people_raw") or []))
    return bool(extraction.known_owner(owner)) and extraction.is_person(people, owner, register)


def vip_open_items(project, thread):
    """The candidate open work for a thread (Part 2): the project's open actions, best match first, at most 15, each
    {id, table, t, owner, due, named, owner_in_thread}. thread: {title, summary, items, people}. Ranked by an ID the thread
    names, then extraction.py's signals (title words, owner, timeframe), then an owner who is in the thread, then due soon.
    No project, no database or nothing open: an empty list."""
    if not project:
        return []
    try:
        con = vip_ro()
        rows, text = _open_actions(con, project), _thread_text(thread)
        if not rows:
            return []
        scores = extraction.rank_open(con, project, text, str(thread.get("title") or thread.get("subject") or ""),
                                      _when(thread.get("last"))[:10] or None)
        register = extraction.people()
    except Exception:  # noqa: BLE001  matching is a nicety; the card matters
        return []
    named = set(extraction.ITEM_ID.findall(text))
    out = []
    for r in rows.values():
        mine = r["id"] in named
        inside = _owner_in(thread, r["owner"], register)
        score = 2.0 if mine else (scores.get(r["id"]) or {}).get("score", 0.0) + (0.2 if inside else 0.0)
        out.append((-score, r["due_date"] or "9999-99-99", r["id"],
                    {"id": r["id"], "table": "actions", "t": r["description"], "owner": r["owner"], "due": r["due_date"],
                     "named": mine, "owner_in_thread": inside}))
    return [x[3] for x in sorted(out, key=lambda x: x[:3])[:MATCH_ITEMS]]


def _alan_wrote(who):
    """Whether the sender a thread's last message names is Alan (his name or a short form from settings, or the Sent folder)."""
    return bool(str(who or "").strip()) and extraction.is_alan(str(who), "")


def _match_thread(a, found):
    """What vip_match compares: the card's own words and the people in the thread."""
    return {**found, "title": a.get("title"), "summary": a.get("summary"), "people": a.get("people"),
            "people_raw": [str(p) for p in [found.get("from")] + list(found.get("people") or []) if p],
            "items": [{"text": c.get("text")} for c in a.get("_cands") or a.get("candidates") or []]}


def _suggested(found, rows, thread):
    """(relation, id, why) the model suggested; with no suggestion, an open ID the thread names gives Update, else New."""
    raw = found.get("match") if isinstance(found.get("match"), dict) else None
    if raw is None:
        named = [i for i in extraction.ITEM_ID.findall(_thread_text(thread)) if i in rows]
        return ("update", named[0], f"The thread names {named[0]}.") if named else ("new", "", "")
    rel, item_id = str(raw.get("relation") or "").strip().lower(), str(raw.get("id") or "").strip().upper()
    return (rel if rel in MATCH_RELATIONS else "update" if item_id else "new"), item_id, _clean(raw.get("why"), MATCH_WHY)


def _checked_match(rel, item_id, why, rows, thread, found):
    """The match code accepts: an unknown, closed or other project's ID is New; Chase needs the item's owner in the thread (not
    Alan) and the thread's last message to be Alan's, else it is Update."""
    if rel == "new" or item_id not in rows:
        return {"id": None, "relation": "new", "why": (why if rel == "new" else "") or "Nothing open matches."}
    row = rows[item_id]
    if rel == "chase" and not (_owner_in(thread, row["owner"], extraction.people()) and not _alan_wrote(row["owner"])
                               and _alan_wrote(found.get("last_from"))):
        rel = "update"
    return {"id": item_id, "relation": rel, "why": why or "The thread moves it forward.", "t": _clean(row["description"], 200)}


def vip_match(a, found, alerts=None):
    """Set a card's "match" from the model's suggestion in `found`, validated by code (Part 2). The model suggests
    {"id", "relation", "why"}; the code keeps it only when the ID is an open action of the card's project (else New), and
    accepts Chase only when the item's owner is in the thread, isn't Alan, and the thread's last message (found["last_from"])
    is Alan's (else Update). A private card gets no match; a card with no project gets New and says so. alerts: every card, so
    the count of cards on one item is refreshed on all of them. Returns the match (or None)."""
    old = a.pop("match", None) or {}
    if a.get("marker") == "private":
        return None
    if not a.get("p"):
        a["match"] = {"id": None, "relation": "new", "why": "No project matched, so nothing to match against."}
        return a["match"]
    try:
        rows = _open_actions(vip_ro(), a["p"])
    except Exception:  # noqa: BLE001  matching is a nicety; the card matters
        rows = {}
    thread = _match_thread(a, found)
    a["match"] = _checked_match(*_suggested(found, rows, thread), rows, thread, found)
    if old.get("logged") and old.get("id") == a["match"].get("id"):
        a["match"]["logged"] = old["logged"]                            # still the same item: still logged on it
    if alerts is not None:
        vip_match_counts(alerts)
    return a["match"]


def vip_match_counts(alerts):
    """Set "count" on every card's match: how many open cards (not Handled or Replied) sit on the same item."""
    by = {}
    for x in alerts:
        m = x.get("match") or {}
        if m.get("id") and x.get("state", "open") == "open":
            by[m["id"]] = by.get(m["id"], 0) + 1
    for x in alerts:
        m = x.get("match")
        if m and m.get("id"):
            m["count"] = by.get(m["id"], 1)
    return by


def _day_shown(day):
    """YYYY-MM-DD as DD-MM-YYYY."""
    y, mo, d = (str(day or "")[:10].split("-") + ["", "", ""])[:3]
    return f"{d}-{mo}-{y}" if y else ""


def vip_update_line(a):
    """The line a card adds to an item's latest update: Claude's own summary line, the date and where it came from, never
    message text; a confidential thread gets only the neutral line."""
    day = _day_shown(a.get("last") or now().strftime("%Y-%m-%d"))
    if a.get("marker") == "confidential" or a.get("confidential"):
        return NEUTRAL_LINE.format(day=day)
    how = "Teams chat" if a.get("kind") == "teams" else "mail thread"
    say = _clean(a.get("summary") or a.get("gist"), 200).rstrip(". ")
    return f"{day}: {say} (from a {how})" if say else f"{day}: discussed in a {how}"


def _pending_for(item_id):
    """(path, spec, item) of the pending thread-update proposal for an item, else None."""
    for f in sorted(paths.STAGING.glob("proposed-*-dashboard*.json")):
        try:
            spec = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue                                                    # an unreadable proposal isn't ours to match
        for it in spec.get("items") or []:
            if (it.get("op") == "update" and it.get("id") == item_id and it.get("decision") == "pending"
                    and (it.get("suggested") or {}).get("feature") == "thread"):
                return f, spec, it
    return None


def _thread_source(a):
    """The thread as an update's source. A confidential card gives only "Email thread · link" or "Teams chat · link", never the
    subject or title."""
    if not (a.get("marker") == "confidential" or a.get("confidential")):
        return alert_source(a)
    return f"{'Teams chat' if a.get('kind') == 'teams' else 'Email thread'} · Link: {a.get('link') or ''}".rstrip(" :")


def _set_lines(item):
    """latest_update = the item's existing text, then each thread's line (Review shows a replacement, and approving it would
    otherwise lose the old text)."""
    sg = item["suggested"]
    item["changes"]["latest_update"] = "\n".join(([sg["base"]] if sg.get("base") else []) + sg["lines"])


def _new_update_spec(a, m, row, line, source, confidential):
    """A fresh pending proposal for an item's update: one op: update on latest_update (the item's existing text first, then the
    thread's line), based_on the row's updated_at; suggested.threads lists the card ids already in it."""
    import propose
    sg = {"feature": "thread", "threads": [a["id"]], "lines": [line], "base": row.get("latest_update") or ""}
    spec = {"created": now().strftime("%Y-%m-%dT%H:%M:%S"), "source_run": "dashboard", "files": [],
            "items": [{"n": 1, "op": "update", "table": "actions", "id": m["id"], "changes": {},
                       "why": "Logged from a confidential thread" if confidential
                       else f"Logged from a thread: {a.get('title') or 'conversation'}"[:200],
                       "source": source, "suggested": sg, "match": "strong", "flags": [],
                       "decision": "pending", "edited_in": "dashboard"}]}
    _set_lines(spec["items"][0])
    propose.complete(spec)
    spec["items"][0]["based_on"] = row["updated_at"]
    bad = [why for k, why in propose.check(spec).values() if k == "invalid"]
    if bad:
        raise ValueError(f"Not staged: {bad[0]}")
    return spec


def _free_name():
    """A proposal file name not used yet (staging or applied)."""
    stamp, out, n = now().strftime("%Y-%m-%d-%H%M%S"), None, 1
    while out is None or out.exists() or (paths.APPLIED / out.name).exists():
        out = paths.STAGING / f"proposed-{stamp}-dashboard{f'-{n}' if n > 1 else ''}.json"
        n += 1
    return out


def _add_line(item, a, line, source):
    """Add a thread's line and source to a pending update; False when this card is already in it. Keyed on the card's stable id
    (the hash of kind and conversation), not on the newest message's link, so a thread with a new message adds nothing. When
    Part 1's `keys` land, any of the card's keys should count here too."""
    sg = item["suggested"]
    ids = {a["id"], *(a.get("keys") or [])}
    if ids & set(sg.get("threads") or []):
        return False
    sg["threads"] = list(sg.get("threads") or []) + [a["id"]]
    sg["lines"] = list(sg.get("lines") or []) + [line]
    item["source"] = f"{item.get('source') or ''} ; {source}"
    _set_lines(item)
    return True


def vip_update_stage(aid):
    """Stage the update a matched card offers (Part 2; Part 1's Log click calls it): one pending proposal for Review with one
    op: update on the item's latest_update (its existing text kept, the thread's line after it), based_on its updated_at, the
    thread as source, checked by propose.check as vip_make's is. A second thread for the same item adds its line to that pending
    proposal (never a second file); the same card again adds nothing. Returns {"proposal", "id", "line", "lines", "added"};
    raises LookupError (no such card), ValueError with a reason to show (no match, item no longer open, fails validation).
    Records {"proposal", "at"} as match["logged"]. Locking: this reads and writes vip.json like mark_made, which has no lock of
    its own; the live server's route must hold VIP_WRITE around the call (Part 3's vip_lock keeps that pattern)."""
    st = vip_state()
    a = next((x for x in st["alerts"] if x.get("id") == aid), None)
    if a is None:
        raise LookupError("No such alert.")
    m = a.get("match") or {}
    if not m.get("id"):
        raise ValueError("This thread has no matched item to log on.")
    try:
        row = _open_actions(vip_ro(), a.get("p")).get(m["id"])
    except Exception:  # noqa: BLE001  no database: the item can't be checked
        row = None
    if row is None:
        raise ValueError(f"{m['id']} is no longer open.")
    confidential = a.get("marker") == "confidential" or bool(a.get("confidential"))
    line, source = vip_update_line(a), _thread_source(a)
    found = _pending_for(m["id"])
    if found:
        out, spec, item = found
        added = _add_line(item, a, line, source)
    else:
        spec, out, added = _new_update_spec(a, m, row, line, source, confidential), _free_name(), True
        item = spec["items"][0]
    if added:
        paths.STAGING.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    m["logged"] = {"proposal": out.name, "at": now().strftime("%Y-%m-%d %H:%M")}
    vip_save(st)
    return {"proposal": out.name, "id": m["id"], "line": line, "lines": item["suggested"]["lines"], "added": added}
# ===== end BL-342 part 2 =====


if __name__ == "__main__":
    code = debuglog.main("sweep.py", main, sys.argv[1:])
    if code == 0 and sys.argv[1:2] and sys.argv[1] in REBUILD_AFTER:
        import build_dashboard
        build_dashboard.rebuild()
    sys.exit(code)
