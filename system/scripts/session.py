"""creaite session start — the CLAUDE.md session-start rule in one call (standard library only).

Usage: python3 system/scripts/session.py start [--json] [--force]
       python3 system/scripts/session.py backup      BL-320: Health's Fix it for the OneDrive copy: today's daily backup if it
                                                     isn't made yet with its zip, then the OneDrive copy of the newest zip

Does, in order (values from settings.json):
  1. daily backup: copies tracker.db to system/backups/tracker-YYYY-MM-DD.db once a day (backups.daily), then the day's
     closed zip, its OneDrive copy, Tidy up and the weekly restore check (backup.py, BL-323); then (BL-10) archives the
     items closed long ago, once a day, through tracker.py apply (archive.py daily; never from an ask creaite run);
  2. sweep: says whether the daily sweep is due (Claude then runs cx-sweep first);
  3. reminders: the weekly report and client reports due (minus any dismissed forever);
  4. status line: pending items by kind, drafts waiting, inbox files, last apply, and sweep failures in the run log;
  5. First thing (BL-295): what the last Close the day put first for this morning, still open.
In the development repo (.creaite-dev) it does nothing unless --force. Read-only on the database (the backup is a copy), apart
from the daily archiving, which writes only through tracker.py apply.
Set CREAITE_NOW="YYYY-MM-DD HH:MM" to fix the clock (tests).
"""
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
import sweep  # noqa: E402
import review  # noqa: E402
import build_dashboard  # noqa: E402


def backup_today(t, say=print):
    """Copy tracker.db to system/backups/tracker-YYYY-MM-DD.db if today's copy doesn't exist; then (BL-323) the day's closed
    zip, its copy in OneDrive, Tidy up once a day and the restore check once a week (backup.after_daily_backup)."""
    if not paths.load_settings().get("backups", {}).get("daily", True) or not paths.DB.exists():
        return None
    dest = paths.BACKUPS / f"tracker-{t:%Y-%m-%d}.db"
    made = None
    if not dest.exists():
        paths.BACKUPS.mkdir(parents=True, exist_ok=True)
        src = sqlite3.connect(f"file:{paths.DB}?mode=ro", uri=True)
        dst = sqlite3.connect(dest)
        with dst:
            src.backup(dst)
        src.close()
        dst.close()
        try:
            import log as debuglog  # BL-102: optional
            debuglog.info("session", f"daily backup made: {dest.name}")
        except ImportError:  # BL-228: the debug log is optional
            pass
        made = paths.rel(dest)
    import backup                                        # BL-323
    for line in backup.after_daily_backup(t.date()):
        say(line)
    return made


# ===== BL-320 (v192-fixit): Health's "make the OneDrive backup copy" =====
def backup_now():
    """Make today's daily backup if it isn't there yet, then the off-laptop copy of the newest daily backup (BL-85), and say
    which. Exit 1 when the copy couldn't be made. Works in the development repository too: its projects are sample data."""
    import tracker
    if tracker.offsite_dir() is None:
        print("The projects live in the vault, so there is no OneDrive copy to make.")
        return 0
    if not paths.DB.exists():
        print("There is no database yet, so there is nothing to back up.")
        return 1
    if not paths.load_settings().get("backups", {}).get("daily", True):
        print("Daily backups are off (backups.daily), so no copy was made: turn them on in Settings first.")
        return 1
    made = backup_today(sweep.now())                     # copies the newest one to OneDrive itself (saying if it failed)
    if made:
        print(f"Daily backup made: {made}")
    r = tracker.offsite_copy()                           # again, for the answer: copies only what isn't there yet
    if r["error"]:
        print(f"The OneDrive copy wasn't made: {r['error']}")
        return 1
    last = tracker.last_offsite_copy()
    if not last:
        print("There is no daily backup to copy yet.")
        return 1
    shown = f"{last[8:10]}-{last[5:7]}-{last[0:4]}"
    print(f"OneDrive copy made: the backup of {shown}." if r["copied"] or made
          else f"The OneDrive folder already holds the newest copy (the backup of {shown}).")
    return 0
# ===== end BL-320 =====


def archive_today():
    """BL-10: once a day, after the daily backup, archive the items closed long ago (archive.py daily: through tracker.py apply,
    never from an ask creaite run). The line to show, or None (already run today, or nothing to say)."""
    import archive
    code, line = archive.daily()
    return line if line and (code or not line.startswith("Archiving: already")) else None


def run_log_failures():
    """Sweep failures since the last successful sweep."""
    if not paths.RUN_LOG.exists():
        return []
    lines = paths.RUN_LOG.read_text(encoding="utf-8").splitlines()
    last_ok = max((i for i, ln in enumerate(lines) if "sweep ok" in ln), default=-1)
    return [ln for ln in lines[last_ok + 1:] if "FAILED" in ln]


def log_error_count():
    """Errors in the debug log in the last 24 hours (BL-102); 0 if the log can't be read."""
    try:
        import log
        return len(log.errors_since(24))
    except Exception:
        return 0


def status():
    """The status line's counts: pending, needs a project, conflicts, drafts, stale, possible matches, inbox
    files, the last apply and sweep failures in the run log.
    """
    rows = review.build_rows()
    counts = {"pending": sum(1 for r in rows if r["section"] != 0),
              "needs a project": sum(1 for r in rows if r["project"] == "Needs a project"),
              "conflicts": sum(1 for r in rows if r["section"] == 1),
              "drafts": len({(r["file"], r["ref"]) for r in rows if r["section"] == 0}),
              "stale": sum(1 for r in rows if r["stale"])}
    possible = 0
    for _, data in review.proposals():
        possible += sum(1 for i in data.get("items", []) if not i.get("applied") and i.get("decision") == "pending"
                        and i.get("match") == "possible")
    counts["possible matches"] = possible
    inbox = [f.name for f in paths.INBOX.iterdir() if f.is_file() and not f.name.startswith(".")] \
        if paths.INBOX.exists() else []
    last_apply = None
    if paths.DB.exists():
        con = sqlite3.connect(f"file:{paths.DB}?mode=ro", uri=True)
        last_apply = con.execute("SELECT max(at) FROM applies WHERE undone_at IS NULL").fetchone()[0]
        con.close()
    return {**counts, "inbox": inbox, "last_apply": (last_apply or "")[:16] or None, "failures": run_log_failures(),
            "log_errors": log_error_count()}


def first_thing(t):
    """BL-295 (Alan, 13-10-2026): what the last Close the day put on First thing tomorrow and is still open, as
    {day, day_shown, items: [{ref, type, t, p}]}, or None."""
    import close_day
    got = close_day.first_thing(t.date())
    items = [x for x in (got or {}).get("items") or [] if x.get("open")]
    return {"day": got["day"], "day_shown": got["day_shown"],
            "items": [{k: x.get(k) for k in ("ref", "type", "t", "p")} for x in items]} if items else None


def first_line(f):
    """The session-start line for First thing: up to five, each its type and words, then how many more."""
    if not f:
        return None
    n, show = len(f["items"]), f["items"][:5]
    words = "; ".join(f"{x['type']}: {x['t']}".rstrip(": ") for x in show)
    more = f"; and {n - len(show)} more" if n > len(show) else ""
    return f"First thing (from Close the day on {f['day_shown']}): {n} open — {words}{more}."


def print_backup(out):
    """The daily backup's line, its notes (BL-323), then the archiving line (BL-10)."""
    if out["backup"]:
        print(f"Daily backup: {out['backup']}")
    for line in out["backup_notes"]:
        print(line)
    if out["archive"]:
        print(out["archive"])


def print_notes(out):
    """The reminders, each with what to say, then First thing (BL-295)."""
    for r in out["reminders"]:
        print(f"{r['text']} — say {r['cmd']}")
    if out["first"]:
        print(first_line(out["first"]))


def reminders(t):
    """The weekly and client reports due at time `t` for each active project, minus those dismissed forever."""
    folders = {}
    import tracker
    con = tracker.connect()
    projects = []
    for code, name in con.execute("SELECT code, name FROM projects WHERE active = 1 ORDER BY code"):
        try:
            folders[code] = paths.project_dir(code)
        except LookupError:
            continue
        mem = build_dashboard.memory(folders[code])
        projects.append({"code": code, "name": name, "rhythm": mem["rhythm"], "client_report": mem["client_report"],
                         "client_reminder": mem["client_reminder"]})        # H3 (#221): none for a project with no client report
    files = build_dashboard.files(folders)
    return build_dashboard.reminders(paths.load_settings(), projects, files, t.date(), t)


def start(as_json=False, force=False):
    """The session-start rule in one call: daily backup, whether the sweep is due, reminders and the status line,
    printed or as JSON. Skipped in the development repository unless `force`.
    """
    if (paths.ROOT / ".creaite-dev").exists() and not force:
        print("Development repo (.creaite-dev): session-start rules skipped.")
        return 0
    t = sweep.now()
    notes = []                                           # BL-323: the zip, OneDrive copy, Tidy up and restore check lines
    out = {"backup": backup_today(t, notes.append), "backup_notes": notes, "archive": archive_today(), "sweep": sweep.due_info(),
           "reminders": reminders(t), "status": status(),
           "first": first_thing(t)}
    if as_json:
        print(json.dumps(out, indent=1))
        return 0
    print_backup(out)
    if out["sweep"]["due"]:
        print(f"Sweep due since {out['sweep']['due_from']}, running now… (run cx-sweep before anything else)")
    print_notes(out)
    s = out["status"]
    parts = [f"{s['pending']} pending" + (f" ({s['needs a project']} need a project, {s['conflicts']} conflicts, "
                                           f"{s['possible matches']} possible matches)" if s["pending"] else ""),
             f"{s['drafts']} draft{'s' if s['drafts'] != 1 else ''} awaiting review",
             f"{len(s['inbox'])} file{'s' if len(s['inbox']) != 1 else ''} waiting in Intake (inbox/)",
             f"last apply {build_dashboard.shown(s['last_apply']) if s['last_apply'] else 'never'}"]
    if s["stale"]:
        parts.append(f"{s['stale']} stale")
    if s["log_errors"]:
        parts.append(f"{s['log_errors']} error{'s' if s['log_errors'] != 1 else ''} in the last 24 hours ({paths.rel(paths.LOGS)}/)")
    print("Status: " + " · ".join(parts) + ".")
    for f in s["failures"]:
        print(f"Run log: {f}")
    return 0


def main(argv):
    """Run the start command in `argv` (--json, --force)."""
    if argv[:1] == ["start"]:
        return start("--json" in argv, "--force" in argv)
    if argv[:1] == ["backup"]:                             # BL-320
        return backup_now()
    print(__doc__)
    return 2


if __name__ == "__main__":
    try:
        import log as debuglog  # BL-102: the debug log (not `log`: some scripts have a function of that name); a script runs without it
    except ImportError:
        debuglog = None
    sys.exit(debuglog.main("session.py", main, sys.argv[1:]) if debuglog else main(sys.argv[1:]))
