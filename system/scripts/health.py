"""creaite Health (BL-320): what needs Alan, from doctor's checks, read only.

Settings › Health lists only the problems, one line each in plain words; everything fine folds into one count, and errors in the
debug log that have stopped are listed as stopped (BL-263). The checks are doctor.py's own, run in a child process with
--read-only (no test files are written) and --json; nothing here changes anything.

Each problem names the Fix it the page would offer. Where Alan's guard decision covers it (health_fixes.py, BL-320: the
launcher, Rosetta, the OneDrive copy) the fix is built: `fix.built` is True, with what it will do and its one command, and the
page runs it through POST /api/health/fix/<id>. Every other fix stays `built: False` with the manual step (`fix.how`). The
fixes no doctor check can see (Chrome's icon, Microsoft 365) are offered on their own (`standalone`). Library only; the live
server's /api/health uses it.

#242 (Alan, 19-10-2026): a problem Alan dismisses stops counting. settings.json's health.dismissed lists each one as {id,
detail_key, reason, date} (saved by the page's own settings save: a backup and a log line); `detail_key` is the check id and a
hash of the detail, so a problem whose detail changes (another file, another count) comes back by itself. A dismissed problem
is listed under `dismissed`, not `problems`. A problem in KEEP (engine integrity, data and privacy) or a crashed check can't be dismissed.
"""
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import health_fixes  # noqa: E402
import paths  # noqa: E402

DOCTOR = Path(__file__).resolve().parent / "doctor.py"
TIMEOUT = 90

# The Fix it each kind of problem would offer: (button, what it would run, why it waits for a guard decision, how to do it now).
FIXES = {
    "launcher": ("Fix it", "system/scripts/run launch.py make-launcher --replace", "runs a command that writes outside the vault "
                 "(~/Applications); launch.py is on no allow list", "Settings › Health › Diagnostics has the one step to type"),
    "migrate": ("Fix it", "system/scripts/run tracker.py migrate", "changes the record (a RECORD command, BL-267)",
                "Ask Claude to repair creaite"),
    "reinstall": ("Fix it", "system/scripts/run update.py install (the installed release again)", "replaces the engine",
                  "Settings › Health › creaite version › Reinstall, or ask Claude to update creaite"),
    "permissions": ("Review", "an edit to .claude/settings.json (permissions.py)", "changes a permission file",
                    "Ask Claude to set creaite up; it shows each rule before changing it"),
    "offsite": ("Make it now", "session.py backup: today's backup and zip, then the newest zip copied into the OneDrive folder",
                "writes outside the vault", "It is made after the next daily backup, at the first session of the day"),
    "setup": ("Open set-up", "the cx-setup skill", "runs set-up steps that change files", "Ask Claude to set creaite up"),
    "autostart": ("Turn it on", "nothing here: Settings › creaite and backups has the switch", "",
                  "Settings › creaite and backups › Start creaite when I sign in"),
    "manual": ("How to fix", "nothing: a step only you can take", "", ""),
}
# doctor check id -> (plain words for the line, the fix kind)
PLAIN = {
    "python_version": ("Python needs attention", "launcher"),
    "launcher_vault": ("Your creaite app opens a different copy of creaite", "launcher"),
    "fts5": ("This Python's SQLite can't search", "manual"),
    "vendored": ("A bundled library doesn't load", "reinstall"),
    "vendor_manifest": ("Bundled libraries don't match their manifest", "reinstall"),
    "database": ("The database needs repair", "migrate"),
    "writable": ("creaite can't write to its own folders", "manual"),
    "projects_root": ("The projects folder can't be reached", "manual"),
    "project_folders_present": ("Some project folders are missing", "manual"),
    "mapped_folders": ("Some folders creaite files into are missing or read-only", "manual"),
    "assistant_permissions": ("ask creaite's permissions are broader than creaite asks for", "permissions"),
    "assistant_guard": ("ask creaite's guard needs attention", "permissions"),
    "vault_not_synced": ("Your creaite folder is in a synced folder", "manual"),
    "online_only": ("Some project files are online-only", "manual"),
    "archive_reports": ("Old reports and minutes to archive", "manual"),     # BL-03: health_fixes builds its Fix it (the card)
    "archive_items": ("Archiving of old items", "manual"),                   # BL-10: information only (never a warning)
    "extraction_scope": ("Items were found in documents or reports", "manual"),
    "no_absolute_paths": ("A full file location was stored", "manual"),
    "config_files": ("A configuration file is missing", "setup"),
    "people_register": ("The people register needs attention", "setup"),
    "workstreams_moved": ("Old workstream lists to retire", "setup"),
    "search_index": ("The search index needs repair", "migrate"),
    "notes_folder_own": ("Notes share a folder with minutes, reports or other files; give notes a folder of their own "
                         "in Settings › Folders and OneDrive", "manual"),   # #124
    "offsite_backup": ("The OneDrive backup copy is missing or out of date", "offsite"),
    "backup_check": ("The weekly backup restore check found a problem", "manual"),       # BL-323
    "tidy_up": ("Tidy up of old backups", "manual"),                                      # BL-323 (always fine: information)
    "sweep_lock": ("A mail and Teams check looks stuck", "manual"),   # BL-328: health_fixes builds its Release
    "sweep_failed": ("A mail and Teams check didn't run", "manual"),   # #370: health_fixes builds its Check now
    "debug_log": ("Errors keep coming back", "manual"),
    "minutes_drafts": ("Minutes waiting in Review have lost their Word draft", "manual"),
    "new_vault": ("Set-up isn't finished", "setup"),
    "autostart": ("creaite won't start by itself after a restart", "autostart"),      # #300: a suggestion, dismissible
    "version": ("The version file is wrong", "reinstall"),
    "rules_imported": ("Your Claude instructions don't include creaite's rules", "setup"),
    "scripts_use_paths": ("A creaite file doesn't take its folder locations from one place", "reinstall"),
}

BACKUP_LINES = ("offsite_backup", "backup_check", "tidy_up")      # BL-323: shown under Backups when fine (the last copy, check, tidy)


ARCHIVING = ("archive_items", "archive_reports")      # BL-10, BL-03: their last runs are listed under Archiving when fine

# #242: what can never be dismissed, a failure or a warning: the engine's own integrity, and what protects your data and privacy
# (vault not synced, the assistant's permissions, backups, extraction scope); a check that crashed is never dismissable either
# (`crashed()`); every other problem may be dismissed
KEEP = ("python_version", "fts5", "vendored", "vendor_manifest", "database", "writable", "assistant_guard", "search_index",
        "version", "rules_imported", "scripts_use_paths",
        "vault_not_synced", "assistant_permissions", "backup_check", "offsite_backup", "extraction_scope")
KEEP_WHY = "This can't be dismissed: it protects your data, your privacy or creaite's own integrity."
CRASHED = re.compile(r"^[A-Za-z_.]*(Error|Exception):")        # an older doctor result without the `crashed` flag


def crashed(c):
    """True for a check that raised (doctor.check marks it; the detail's `TypeError: …` shape covers an older result)."""
    return bool(c.get("crashed")) or (c.get("status") == "fail" and bool(CRASHED.match(str(c.get("detail", "")))))


def problem_key(check_id, detail):
    """A dismissed problem's key: its check id and a short hash of its detail as shown (#242)."""
    return f"{check_id}:{hashlib.sha256(str(detail).encode('utf-8')).hexdigest()[:12]}"


def dismissed_entries(dismissed=None):
    """health.dismissed from settings.json (or `dismissed`), only the well-formed entries, by detail_key."""
    if dismissed is None:
        try:
            dismissed = (paths.load_settings().get("health") or {}).get("dismissed")
        except (OSError, ValueError):
            dismissed = None
    if not isinstance(dismissed, list):
        return {}
    return {d["detail_key"]: d for d in dismissed if isinstance(d, dict) and isinstance(d.get("detail_key"), str)}


def split_dismissed(problems, dismissed=None):
    """(problems still counted, dismissed problems with their reason and date): a problem that may not be dismissed stays."""
    entries, shown, gone = dismissed_entries(dismissed), [], []
    for p in problems:
        e = entries.get(p["key"]) if p["dismissable"] else None
        if e:
            gone.append({**p, "reason": str(e.get("reason") or ""), "date": str(e.get("date") or "")})
        else:
            shown.append(p)
    return shown, gone


def doctor_checks():
    """doctor.py --read-only --json, run in its own process: {checks: [{id, name, status, detail}], passed, failed}."""
    r = subprocess.run([sys.executable, str(DOCTOR), "--read-only", "--json"], cwd=paths.ROOT, capture_output=True, text=True,
                       timeout=TIMEOUT)
    for line in reversed(r.stdout.strip().splitlines()):
        if line.startswith("{"):
            return json.loads(line)
    raise RuntimeError("the health check gave no result" + (f": {r.stderr.strip().splitlines()[-1]}" if r.stderr.strip() else ""))


def autostart_check():
    """#300: a doctor-shaped warning while creaite wouldn't start by itself after a restart, else None. Only on macOS, never in the
    development repository (no login agent there), and never when the state can't be read. Dismissible like any other problem."""
    try:
        import launch
        st = launch.agent_state()
    except Exception:  # noqa: BLE001  a suggestion never breaks Health
        return None
    if not st.get("supported") or st.get("on"):
        return None
    return {"id": "autostart", "name": "Start when you sign in", "status": "warn",
            "detail": "creaite isn't set to start when you sign in, so after a restart it stays closed until you open it"}


def home_short(text):
    """The home folder written as ~, so a line reads as it does in Finder."""
    return str(text).replace(str(Path.home()), "~")


def built_fix(fix_id, kind=""):
    """A built fix (health_fixes.describe), with the fields every fix has, so the page reads one shape."""
    d = health_fixes.describe(fix_id)
    would_run = d.get("command") or d.get("url") or d.get("call", "")
    return {**d, "kind": kind or fix_id, "would_run": would_run, "waits_for": "", "how": d["does"]}


def fix_for(kind, problem_id=None, detail=""):
    """The Fix it a problem offers: built when health_fixes has one for this check and detail (BL-320, Alan's guard decision),
    otherwise not built, with the manual step meanwhile."""
    fix_id = health_fixes.fix_for(problem_id, detail) if problem_id else None
    if fix_id:
        return built_fix(fix_id, kind)
    button, would_run, why, how = FIXES[kind]
    return {"kind": kind, "button": button, "would_run": would_run, "waits_for": why, "how": how, "built": False}


def stopped_errors():
    """Errors that kept coming back and have now stopped (BL-263): area, count, first and last times, the short message."""
    try:
        import log
        groups = log.repeats(days=int(log.settings()["keep_days"]))
    except Exception:  # noqa: BLE001  the log is optional: Health still shows doctor's checks without it
        return []
    return [{"area": g["area"], "count": g["count"], "span": log.span(g), "message": home_short(log.short(g["message"]))}
            for g in groups if not g["live"]]


def problem(c):
    """One doctor warning or failure as Health lists it: plain words, its fix, its key and whether it may be dismissed."""
    title, kind = PLAIN.get(c.get("id"), (c.get("name", "A check"), "manual"))
    if c.get("id") == "archive_reports" and str(c.get("detail", "")).startswith("Archive "):
        title = str(c["detail"]).split(":")[0]               # BL-03: "Archive 14 reports and minutes older than 12 months"
    detail, keep = home_short(c.get("detail", "")), c.get("id") in KEEP or crashed(c)
    return {"id": c.get("id"), "title": title, "check": c.get("name", ""), "severity": c.get("status"), "detail": detail,
            "fix": fix_for(kind, c.get("id"), c.get("detail", "")), "key": problem_key(c.get("id"), detail),
            "dismissable": not keep, "keep_why": KEEP_WHY if keep else ""}


def health(result=None, dismissed=None):
    """{problems, dismissed, fine, fine_names, stopped, checked}: doctor's warnings and failures in plain words, each with its
    fix; the rest counted. `result` is a doctor --json result (the tests pass one), else doctor runs now; `dismissed` is a
    health.dismissed list (the tests pass one), else settings.json's (#242)."""
    result = doctor_checks() if result is None else result
    problems, fine = [], []
    extra = autostart_check()
    for c in [*(result.get("checks") or []), *([extra] if extra else [])]:
        if c.get("status") == "pass":
            fine.append(c.get("name", ""))
            continue
        problems.append(problem(c))
    problems.sort(key=lambda p: p["severity"] != "fail")         # failures first, then warnings, each in doctor's order
    problems, gone = split_dismissed(problems, dismissed)
    archiving = [home_short(c.get("detail", "")) for c in result.get("checks") or []      # BL-10, BL-03: the last runs
                 if c.get("id") in ARCHIVING and c.get("status") == "pass" and c.get("detail")]
    backups = [f"{c.get('name', '')}: {home_short(c.get('detail', ''))}" for c in result.get("checks") or []   # BL-323
               if c.get("id") in BACKUP_LINES and c.get("status") == "pass"]
    return {"problems": problems, "dismissed": gone, "fine": len(fine), "fine_names": fine, "stopped": stopped_errors(),
            "archiving": archiving, "backups": backups,
            "standalone": [built_fix(f) for f in health_fixes.STANDALONE],
            "read_only": bool(result.get("read_only")), "checked": datetime.now().strftime("%Y-%m-%d %H:%M")}
