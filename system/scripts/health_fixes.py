"""creaite Health's Fix it (BL-320; Alan's guard decision, 14-10-2026): each fix runs exactly one known command, with nothing
from the page.

Used by the live server's dashboard-only routes (POST /api/health/fixes, POST /api/health/fix/<id>); it has no command line of
its own. Each fix is a fixed entry in FIXES: its words for Alan (what it will do, shown before he presses Fix it) and either the
one creaite script command it runs, or, for Microsoft 365, only the address of Claude's connector page (creaite can't sign in
for him and never tries). Nothing here touches Microsoft 365, a permission file or the record.

CHECK_FIXES maps a doctor check id (its function name in doctor.py, the `id` health.py reports for each problem) to its fix:
fix_for(check_id, detail) gives the fix's id, or None when the check has no fix or its detail isn't the problem the fix mends.
STANDALONE are the fixes no doctor check can see (Chrome's copy of the icon, Claude's connectors): Health offers them on their own.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

CONNECTOR_URL = "https://claude.ai/settings/connectors"
FIX_LOG = paths.STAGING / "health-fixes.jsonl"       # when each fix ran and whether it worked: ids and exit codes only

# id: what it is, the button, what it will do (shown first), and its one command (a creaite script and fixed words) or the page
FIXES = {
    "launcher": {"title": "Your launcher opens another vault", "button": "Fix it",
                 "does": "Make this vault's launcher again in ~/Applications, replacing the one that opens another vault.",
                 "command": ("launch.py", "make-launcher", "--replace")},
    "rosetta": {"title": "Python runs under Rosetta", "button": "Fix it",
                "does": "Make this vault's launchers again so they start creaite natively (arm64), not as an Intel program.",
                "command": ("launch.py", "make-launcher", "--if-present")},
    "icon": {"title": "Chrome's copy of the app shows an old icon", "button": "Fix it",
             "does": "Point the app's manifest at new icon addresses, so Chrome offers to update its copy of the icon.",
             "command": ("launch.py", "refresh-icon")},
    "m365": {"title": "Microsoft 365 isn't connected", "button": "Open connector settings",
             "does": "Open Claude's connector settings, where you reconnect Microsoft 365 yourself. creaite never signs in for you.",
             "url": CONNECTOR_URL},
    "offsite": {"title": "No copy of the backup in OneDrive yet", "button": "Make it now",
                "does": ("Make today's daily backup and its zip if they aren't there, then copy the newest zip to the OneDrive "
                         "backup folder."),
                "command": ("session.py", "backup")},
    # BL-09: a move, so it goes on the approval card: the command only prints the change; the live server puts it on the card
    # (Approve applies it through tracker.py apply, the one thing that may move a folder into or out of _Archive)
    "old_archive": {"title": "Folders still called zz Archive", "button": "Fix it",
                    "does": "Show the renames (each zz Archive folder becomes _Archive, in the same place) on the approval card; "
                            "nothing moves until you approve it there, and Undo moves them back.",
                    "command": ("propose.py", "old-archives"), "card": True},
    # BL-03: a move too, so the same: archive.py reports only prints the moves; Approve on the card applies them through tracker.py
    "archive_reports": {"title": "Archive old reports and minutes", "button": "Archive them",
                        "does": "Show the moves on the approval card: each report, minutes and Steerco one-pager older than the "
                                "period goes into its engagement's own _Archive, in the same place below it. Nothing moves until "
                                "you approve it there; links keep working, nothing is deleted, and Undo moves them back.",
                        "command": ("archive.py", "reports"), "card": True},
}

# doctor check id → (fix id, words in its detail that mean this fix mends it: any of them, or None for any detail)
CHECK_FIXES = {
    "launcher_vault": ("launcher", ("opens another vault",)),
    "python_version": ("rosetta", ("Rosetta",)),
    "offsite_backup": ("offsite", ("no copy yet", "days ago")),       # not "can't write to …": a copy can't mend that
    "old_archive_folders": ("old_archive", ("zz Archive",)),          # BL-09
    "archive_reports": ("archive_reports", ("Archive ",)),            # BL-03: the monthly line
}
STANDALONE = ("icon", "m365")


def fix_for(check_id, detail=""):
    """The fix's id for a doctor check id and its detail, or None."""
    hit = CHECK_FIXES.get(check_id)
    if not hit:
        return None
    fix, words = hit
    return fix if words is None or any(w in (detail or "") for w in words) else None


def describe(fix_id):
    """What Health shows before Fix it: the title, the button, what it will do, and the command it runs (or the page it opens)."""
    f = FIXES[fix_id]
    out = {"id": fix_id, "title": f["title"], "button": f["button"], "does": f["does"], "built": True}
    if "url" in f:
        out["url"] = f["url"]
    else:
        out["command"] = "system/scripts/run " + " ".join(f["command"])
    return out


def catalogue():
    """Every fix, described, and which doctor check each mends ({check id: fix id}) for Health's problems list."""
    return {"fixes": [describe(k) for k in FIXES], "checks": {k: v[0] for k, v in CHECK_FIXES.items()},
            "standalone": list(STANDALONE)}


def log(fix_id, ok, code=None):
    """One line per fix run: when, which, and whether it worked (never its output)."""
    try:
        FIX_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(FIX_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "fix": fix_id, "ok": bool(ok),
                                 "code": code}) + "\n")
    except OSError:  # the fix's own answer still reaches the page; the debug log below says it ran
        pass
    try:
        import log as debuglog
    except ImportError:  # BL-228: the debug log is optional
        return
    debuglog.info("health", f"fix {fix_id}: {'done' if ok else 'failed'}" + ("" if code is None else f" (exit {code})"))


def run_fix(fix_id, runner):
    """Run fix `fix_id` with `runner(script, *words)` → (exit code, output), the live server's own script runner.
    Returns the answer for the page: {ok, fix, message[, url]}. Raises KeyError for an unknown id."""
    f = FIXES[fix_id]
    if "url" in f:                                       # Microsoft 365: nothing runs; the page opens the address
        log(fix_id, True)
        return {"ok": True, "fix": fix_id, "url": f["url"],
                "message": "Opening Claude's connector settings: reconnect Microsoft 365 there, then check again."}
    code, out = runner(*f["command"])
    log(fix_id, code == 0, code)
    lines = [ln for ln in (out or "").splitlines() if ln.strip()]
    return {"ok": code == 0, "fix": fix_id, "message": lines[-1] if lines else ("Done." if code == 0 else "It didn't work.")}
