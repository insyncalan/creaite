"""creaite Health (BL-320): what needs Alan, from doctor's checks, read only.

Settings › Health lists only the problems, one line each in plain words; everything fine folds into one count, and errors in the
debug log that have stopped are listed as stopped (BL-263). The checks are doctor.py's own, run in a child process with
--read-only (no test files are written) and --json; nothing here changes anything.

Each problem names the Fix it the page would offer. Where Alan's guard decision covers it (health_fixes.py, BL-320: the
launcher, Rosetta, the OneDrive copy) the fix is built: `fix.built` is True, with what it will do and its one command, and the
page runs it through POST /api/health/fix/<id>. Every other fix stays `built: False` with the manual step (`fix.how`). The
fixes no doctor check can see (Chrome's icon, Microsoft 365) are offered on their own (`standalone`). Library only; the live
server's /api/health uses it.
"""
import json
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
                 "(~/Applications); launch.py is on no allow list", "In Terminal: system/scripts/run launch.py make-launcher --replace"),
    "migrate": ("Fix it", "system/scripts/run tracker.py migrate", "changes the record (a RECORD command, BL-267)",
                "Say \"repair creaite\" in Claude Code, or run system/scripts/run tracker.py migrate"),
    "reinstall": ("Fix it", "system/scripts/run update.py install (the installed release again)", "replaces the engine",
                  "Settings › Health › creaite version › Reinstall, or say \"update creaite\""),
    "permissions": ("Review", "an edit to .claude/settings.json (permissions.py)", "changes a permission file",
                    "Say \"setup\" in Claude Code; it shows each rule before changing it"),
    "offsite": ("Make it now", "session.py backup: today's backup and zip, then the newest zip copied into the OneDrive folder",
                "writes outside the vault", "It is made after the next daily backup, at the first session of the day"),
    "setup": ("Open set-up", "the cx-setup skill", "runs set-up steps that change files", "Say \"setup\" in Claude Code"),
    "manual": ("How to fix", "nothing: a step only you can take", "", ""),
}
# doctor check id -> (plain words for the line, the fix kind)
PLAIN = {
    "python_version": ("Python needs attention", "launcher"),
    "launcher_vault": ("Your launcher opens another vault", "launcher"),
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
    "vault_not_synced": ("The vault is in a synced folder", "manual"),
    "online_only": ("Some project files are online-only", "manual"),
    "old_archive_folders": ("Folders still called zz Archive", "manual"),        # BL-09: health_fixes builds its Fix it
    "skeleton_archive": ("The project skeleton still holds zz Archive", "manual"),   # BL-09: Alan renames it in Finder
    "extraction_scope": ("Something was extracted from documents or reports", "manual"),
    "no_absolute_paths": ("A full path was stored", "manual"),
    "config_files": ("A configuration file is missing", "setup"),
    "people_register": ("The people register needs attention", "setup"),
    "workstreams_moved": ("Old workstream lists to retire", "setup"),
    "search_index": ("The search index needs repair", "migrate"),
    "offsite_backup": ("The OneDrive backup copy is missing or out of date", "offsite"),
    "backup_check": ("The weekly backup restore check found a problem", "manual"),       # BL-323
    "tidy_up": ("Tidy up of old backups", "manual"),                                      # BL-323 (always fine: information)
    "sweep_lock": ("A sweep lock is held with no sweep running", "manual"),   # BL-328: health_fixes builds its Release
    "debug_log": ("Errors keep coming back", "manual"),
    "minutes_drafts": ("Staged minutes have lost their Word draft", "manual"),
    "new_vault": ("Set-up isn't finished", "setup"),
    "version": ("The version file is wrong", "reinstall"),
    "rules_imported": ("CLAUDE.md doesn't import creaite's rules", "setup"),
    "scripts_use_paths": ("A script doesn't take its locations from paths.py", "reinstall"),
}

BACKUP_LINES = ("offsite_backup", "backup_check", "tidy_up")      # BL-323: shown under Backups when fine (the last copy, check, tidy)


def doctor_checks():
    """doctor.py --read-only --json, run in its own process: {checks: [{id, name, status, detail}], passed, failed}."""
    r = subprocess.run([sys.executable, str(DOCTOR), "--read-only", "--json"], cwd=paths.ROOT, capture_output=True, text=True,
                       timeout=TIMEOUT)
    for line in reversed(r.stdout.strip().splitlines()):
        if line.startswith("{"):
            return json.loads(line)
    raise RuntimeError("the health check gave no result" + (f": {r.stderr.strip().splitlines()[-1]}" if r.stderr.strip() else ""))


def home_short(text):
    """The home folder written as ~, so a line reads as it does in Finder."""
    return str(text).replace(str(Path.home()), "~")


def built_fix(fix_id, kind=""):
    """A built fix (health_fixes.describe), with the fields every fix has, so the page reads one shape."""
    d = health_fixes.describe(fix_id)
    return {**d, "kind": kind or fix_id, "would_run": d.get("command") or d.get("url", ""), "waits_for": "", "how": d["does"]}


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


def health(result=None):
    """{problems, fine, fine_names, stopped, checked}: doctor's warnings and failures in plain words, each with its fix; the
    rest counted. `result` is a doctor --json result (the tests pass one), else doctor runs now."""
    result = doctor_checks() if result is None else result
    problems, fine = [], []
    for c in result.get("checks") or []:
        if c.get("status") == "pass":
            fine.append(c.get("name", ""))
            continue
        title, kind = PLAIN.get(c.get("id"), (c.get("name", "A check"), "manual"))
        problems.append({"id": c.get("id"), "title": title, "check": c.get("name", ""), "severity": c.get("status"),
                         "detail": home_short(c.get("detail", "")), "fix": fix_for(kind, c.get("id"), c.get("detail", ""))})
    problems.sort(key=lambda p: p["severity"] != "fail")         # failures first, then warnings, each in doctor's order
    backups = [f"{c.get('name', '')}: {home_short(c.get('detail', ''))}" for c in result.get("checks") or []   # BL-323
               if c.get("id") in BACKUP_LINES and c.get("status") == "pass"]
    return {"problems": problems, "fine": len(fine), "fine_names": fine, "stopped": stopped_errors(), "backups": backups,
            "standalone": [built_fix(f) for f in health_fixes.STANDALONE],
            "read_only": bool(result.get("read_only")), "checked": datetime.now().strftime("%Y-%m-%d %H:%M")}
