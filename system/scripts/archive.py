"""creaite archiving (BL-10 and BL-03, v1.9.5; Alan's decisions, 14-10-2026). Standard library only.

Usage: system/scripts/run archive.py daily [--force]       the daily slot: archive old items once a day (see below)
       system/scripts/run archive.py items [--dry-run]     BL-10 now: archive the items due today (--dry-run lists them)
       system/scripts/run archive.py reports [--out <name>.json]
                                                           BL-03: print (or save in system/staging/drafts/) the spec that moves
                                                           the reports and minutes older than archive.reports_after_months into
                                                           each engagement's own 99 Archive; exit 1 when there is none
       system/scripts/run archive.py status [--json]       the last runs and what is due (read only; Settings › Health)

BL-10, items, automatic: once a day closed or cancelled actions and RAID items, and done or dropped promises, closed
archive.after_months.<kind> months ago or more (6 by default), are flagged archived (the BL-09 flag: still searchable, covered by
the backups, undoable). Decisions, milestones and any open item never are. It runs through tracker.py apply (one proposal,
source_run "archive", applied at once), so each flag is logged and undoable; an edit un-archives an item. It runs in the daily
slot: session start (session.py start, after the daily backup) and the live server's daily backup job (BL-323: after the
backup, the zip and Tidy up; a minute after start-up, then hourly), each once a day; never from an ask creaite run and never
in the development repository. The last run is kept in system/staging/archive-state.json (counts and IDs only) and shown in
Settings › Health.

BL-03, files, on a yes: weekly and client reports, minutes and Steerco one-pagers dated (by their file name) more than
archive.reports_after_months months ago (12) move into their engagement's own 99 Archive, keeping their place below it. Health shows
a line once a month while any are due ("Archive 14 reports and minutes older than 12 months"); its Fix it puts this command's spec
on the approval card, and Approve applies it through tracker.py apply (a `move` of kind "reports", the BL-09 guard exception: only
the apply moves into 99 Archive). Stored paths keep resolving (paths.resolve). Transcripts, agendas, documents and applied proposals
are never moved. BL-331: Files lists the archived ones with Move back, the exact reverse move ("reports_back"), which only the
live server puts on the approval card (archived_files, back_spec); never onto a file that is there.
Set CREAITE_NOW="YYYY-MM-DD HH:MM" to fix the clock (tests).
"""
import json
import os
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

STATE = paths.STAGING / "archive-state.json"
DATED = re.compile(r"^(\d{4}-\d{2}-\d{2}) ")
REPORT_DEFAULT_MONTHS = 12
# kind -> words its file name must hold (lower case), or None for any dated file. With the projects in the vault the weekly and
# client reports share one folder (reports/) with ad hoc documents, which are never archived.
NAMED = {"minutes": None, "weekly_reports": "weekly report", "client_reports": "client report", "steerco": "steerco one-pager"}


def today():
    """Today as a date (CREAITE_NOW fixes it in tests)."""
    import tracker
    return tracker.clock_day()


def shown(d):
    """YYYY-MM-DD as DD-MM-YYYY."""
    s = str(d or "")
    return f"{s[8:10]}-{s[5:7]}-{s[0:4]}" if len(s) >= 10 else s


def dev_repo():
    """Whether this is the development repository (.creaite-dev), where archiving never runs by itself."""
    return (paths.ROOT / ".creaite-dev").exists()


def ask_run():
    """True while an ask creaite run is in progress (the live server's guard record) or this is one of its tools: the daily run
    never starts from a chat. Fails closed: a guard folder that can't be read counts as a run."""
    if os.environ.get("CREAITE_HEADLESS_RUN") == "1":
        return True
    try:
        return (paths.GUARD / "run.json").exists()
    except OSError:
        return True


def state():
    """system/staging/archive-state.json as a dict ({} when there is none yet)."""
    try:
        d = json.loads(STATE.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):  # none yet, or unreadable: the next run writes it again
        return {}


def save_state(d):
    """Write the state whole (a .part file, then a rename)."""
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".json.part")
    tmp.write_text(json.dumps(d, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, STATE)


def note(level, msg):
    """One debug log line (counts and IDs only), when the log is there."""
    try:
        import log as debuglog
    except ImportError:  # BL-228: the debug log is optional
        return
    getattr(debuglog, level)("archive", msg)


# ===== BL-10: items =====
def run_items(force=False, dry=False):
    """Archive the items due today through tracker.py apply, once a day (force: again). Returns (exit code, the line to show)."""
    import tracker
    day = today()
    st = state()
    if not dry and not force and (st.get("items") or {}).get("day") == day.isoformat():
        return 0, "Archiving: already run today."
    con = tracker.connect()
    try:
        due = tracker.due_for_age_archive(con, day)
    finally:
        con.close()
    if dry:
        for t, i in due:
            print(f"{i} ({t})")
        return 0, f"{len(due)} item{'s' if len(due) != 1 else ''} would be archived today."
    apply_id = None
    if due:
        prop = paths.free_path(paths.STAGING, f"proposed-{datetime.now():%Y-%m-%d-%H%M%S}-archive", ".json")
        items = [{"n": n, "op": tracker.AGE_OP, "table": t, "id": i, "match": "strong", "flags": [], "decision": "approved"}
                 for n, (t, i) in enumerate(due, 1)]
        prop.write_text(json.dumps({"created": datetime.now().isoformat(timespec="seconds"), "source_run": tracker.AGE_SOURCE,
                                    "files": [], "items": items}, indent=2) + "\n", encoding="utf-8")
        code = tracker.cmd_apply([str(prop)])
        if code:
            prop.unlink(missing_ok=True)                 # nothing was written; nothing is left in Review
            note("warn", f"daily archiving stopped: the apply refused {len(due)} item(s)")
            return 1, "Archiving: the apply stopped, nothing was archived."
        apply_id = last_apply_of(prop.name)
    st["items"] = {"day": day.isoformat(), "archived": len(due), "apply_id": apply_id,
                   "at": datetime.now().strftime("%Y-%m-%d %H:%M")}
    save_state(st)
    note("info", f"daily archiving: {len(due)} item(s)" + (f", apply {apply_id}" if apply_id else ""))
    return 0, f"Archived {len(due)} item{'s' if len(due) != 1 else ''} closed long ago." if due else "Archiving: nothing to archive today."


def last_apply_of(name):
    """The apply that wrote proposal `name` (from applied/), or None."""
    for f in (paths.APPLIED / name, paths.STAGING / name):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):  # not in this folder: the other one
            continue
        ids = {i.get("applied") for i in data.get("items", []) if i.get("applied")}
        return max(ids) if ids else None
    return None


def daily(force=False):
    """The daily slot (session start, the live server's timer): BL-10's items once a day. Returns (exit code, line or None)."""
    if dev_repo() and not force:
        return 0, None
    if ask_run():
        return 0, None                                   # never from a chat: Alan's own session or the server's own timer
    if not paths.DB.exists():
        return 0, None
    try:
        return run_items()
    except Exception as e:  # noqa: BLE001  the daily slot never stops session start or the server
        note("error", f"daily archiving failed: {type(e).__name__}")
        return 1, f"Archiving didn't run: {type(e).__name__}: {e}"


# ===== BL-03: reports and minutes =====
def report_months(settings=None):
    """archive.reports_after_months (12); 0 or less turns BL-03 off."""
    try:
        s = settings if settings is not None else paths.load_settings()
        return int((s.get("archive") or {}).get("reports_after_months", REPORT_DEFAULT_MONTHS))
    except (OSError, ValueError, TypeError):
        return REPORT_DEFAULT_MONTHS


def due_reports(on=None):
    """[{code, kind, from, to}] of the files older than the period, by the date in their name, in each project folder in place
    and the portfolio's minutes (never an archived project, or a file whose place in 99 Archive is taken). A folder listing only."""
    import tracker
    months = report_months()
    if months <= 0:
        return []
    cutoff = tracker.months_before(on or today(), months).isoformat()
    out, seen, back = [], set(), moved_back()           # BL-331: a file Alan moved back is never offered again
    for code, base in paths.project_folders():
        kinds = ("minutes",) if code == "_portfolio" else paths.ARCHIVED_FILE_KINDS   # the portfolio: minutes only (Alan, 14-10-2026)
        for kind in kinds:
            sub = paths.folder_name(kind).strip("/")
            for f in due_in(base / sub, kind, cutoff):
                if f not in seen and paths.rel(f) not in back and not any((d / sub / f.name).exists() for d in paths.archive_dirs(base)):
                    seen.add(f)
                    out.append({"code": code, "kind": kind, "from": paths.rel(f),
                                "to": paths.rel(base / paths.ARCHIVE / sub / f.name)})
    return out


def due_in(d, kind, cutoff):
    """The files directly in folder `d` of this kind dated on or before `cutoff` (YYYY-MM-DD), in name order."""
    if not d.is_dir() or d.is_symlink():
        return []
    out = []
    for f in sorted(d.iterdir()):
        m = DATED.match(f.name)
        if not m or not f.is_file() or f.is_symlink() or f.name.startswith((".", "~$")) or m.group(1) > cutoff:
            continue
        if NAMED[kind] is None or NAMED[kind] in f.name.lower():
            out.append(f)
    return out


def reports_spec(on=None):
    """The spec that moves every due file (a `move` of kind "reports" each), or None when there is none."""
    due = due_reports(on)
    if not due:
        return None
    n, months = len(due), report_months()
    return {"source_run": "archive", "items": [], "file_changes": {
        "title": f"Archive {n} report{'s' if n != 1 else ''} and minutes older than {months} months", "project": None,
        "archive": "reports", "file_ops": [{"op": "move", "from": x["from"], "to": x["to"]} for x in due]}}


def last_reports_archive(con):
    """{at, moved} of the latest apply (not undone) that archived reports, or None."""
    try:
        rows = con.execute("SELECT at, file_ops FROM applies WHERE undone_at IS NULL ORDER BY apply_id DESC").fetchall()
    except sqlite3.Error:
        return None
    for at, ops in rows:
        try:
            moved = sum(1 for r in json.loads(ops or "[]") if r.get("op") == "move" and r.get("kind") == "reports")
        except (ValueError, AttributeError):  # an apply's record in an older shape: not an archive of reports
            continue
        if moved:
            return {"at": at, "moved": moved}
    return None


def status(on=None):
    """What Health shows: the last item run, the last report archive, and how many reports and minutes are due this month."""
    day = on or today()
    items = state().get("items") or {}
    last = None
    if paths.DB.exists():
        con = sqlite3.connect(f"file:{paths.DB}?mode=ro", uri=True)
        try:
            last = last_reports_archive(con)
        finally:
            con.close()
    due = due_reports(day)
    this_month = bool(last and str(last["at"])[:7] == day.isoformat()[:7])
    return {"items": items, "reports": {"last": last, "due": len(due), "months": report_months(),
                                        "offer": bool(due) and not this_month}}


def items_line(st):
    """Health's line for the last daily run of BL-10."""
    it = st["items"]
    if not it:
        return "Archiving of old items hasn't run yet: it runs once a day."
    n = it.get("archived", 0)
    return (f"Archived {n} item{'s' if n != 1 else ''} on {shown(it.get('day'))}" if n
            else f"Nothing to archive on {shown(it.get('day'))}") + " (closed items, after their period)."


def reports_line(st):
    """Health's line for BL-03: the monthly offer ("Archive 14 reports and minutes older than 12 months"), or the last archive."""
    r = st["reports"]
    if r["offer"]:
        n = r["due"]
        return f"Archive {n} report{'s' if n != 1 else ''} and minutes older than {r['months']} months"
    if r["last"]:
        n = r["last"]["moved"]
        return f"Archived {n} report{'s' if n != 1 else ''} and minutes on {shown(r['last']['at'])}."
    return f"No reports or minutes older than {r['months']} months." if not r["due"] else \
        f"{r['due']} reports and minutes older than {r['months']} months: offered again next month."


# ===== BL-331: move one archived report back (Alan, 14-10-2026) =====
# Files lists what BL-03's archive moved into an engagement's (or the portfolio's) 99 Archive, marked Archived, each with Move back.
# Move back is the exact reverse of that move (a `move` of kind "reports_back": reach.archive_move_problem checks the reversed
# shape, and tracker.check_move that an archive moved that very file there). Only the live server puts it on the approval card,
# from the stored path the page names; tracker.py apply moves it and undo puts it back in 99 Archive. Never onto a file that is
# there: a taken place is refused. Once back, the apply's search refresh indexes it again.
BACK = "reports_back"


def archived_moves(con=None, kind="reports"):
    """{the archived file's stored path: its original stored path} for each file an apply (not undone) archived (kind "reports";
    #124: "notes", a deleted note) and no later apply (not undone) moved back, oldest first. Read from the applies table only.
    #252: keys follow an archive folder renamed by hand (paths.follow_stored)."""
    back = BACK if kind == "reports" else f"{kind}_back"
    own = con is None
    if own:
        if not paths.DB.exists():
            return {}
        con = sqlite3.connect(f"file:{paths.DB}?mode=ro", uri=True)
    try:
        rows = con.execute("SELECT file_ops FROM applies WHERE undone_at IS NULL ORDER BY apply_id").fetchall()
    except sqlite3.Error:  # a database from before applies kept file operations: nothing was archived
        rows = []
    finally:
        if own:
            con.close()
    out = {}
    for (ops,) in rows:
        try:
            recs = json.loads(ops or "[]")
        except ValueError:  # an apply's record in an older shape: no archive moves in it
            continue
        for r in recs if isinstance(recs, list) else []:
            if not isinstance(r, dict) or r.get("op") != "move":
                continue
            if r.get("kind") == kind:
                out[r.get("to")] = r.get("from")
            elif r.get("kind") == back:
                out.pop(r.get("from"), None)
    return _followed(out)


def _followed(moves):
    """#252: the record keeps the archive folder's name as it was; after Alan renames the folder by hand a key is where it is now."""
    return {paths.follow_stored(k): v for k, v in moves.items() if k}


def moved_back(con=None):
    """The stored paths of the files moved back (a `move` of kind "reports_back" in an apply not undone): BL-03's monthly offer
    leaves them out for good (Alan, 14-10-2026). Read from the applies table only."""
    own = con is None
    if own:
        if not paths.DB.exists():
            return set()
        con = sqlite3.connect(f"file:{paths.DB}?mode=ro", uri=True)
    try:
        rows = con.execute("SELECT file_ops FROM applies WHERE undone_at IS NULL").fetchall()
    except sqlite3.Error:  # a database from before applies kept file operations: nothing was moved back
        rows = []
    finally:
        if own:
            con.close()
    out = set()
    for (ops,) in rows:
        try:
            recs = json.loads(ops or "[]")
        except ValueError:  # an apply's record in an older shape: no moves back in it
            continue
        out.update(r.get("to") for r in (recs if isinstance(recs, list) else [])
                   if isinstance(r, dict) and r.get("op") == "move" and r.get("kind") == BACK)
    return out


def _place(original):
    """(code, Files folder, sub) of an original stored path in a project or the portfolio that is in place, or None."""
    p = paths.resolve(original, archived=False)
    for code, base in paths.project_folders():
        try:
            rest = p.relative_to(base).parts
        except ValueError:  # not this project's folder: the next one
            continue
        sub = "/".join(rest[:-1])
        if sub == paths.folder_name("notes").strip("/") and original.lower().endswith(".md"):
            return code, "notes", ""                                     # #124: a deleted note
        if sub == paths.folder_name("minutes").strip("/"):
            return code, "minutes", ""
        if code != "_portfolio" and sub in paths.archivable_folders():
            return code, "reports", "Steerco" if sub == paths.folder_name("steerco").strip("/") else "Weekly"
    return None


def archived_files():
    """Files' archived list (BL-331): [{p, f, sub, n, type, date, kb, path, archived}] for each file BL-03 moved that is still in
    its 99 Archive. path is the stored path (it opens, through paths.resolve). Names, sizes and dates only; nothing is read."""
    out = []
    moved = {**archived_moves(), **archived_moves(kind=NOTE)}
    for at, original in moved.items():
        if not at or not original:
            continue
        f = paths.resolve(at, archived=False)
        place = _place(original)
        if place is None or f.is_symlink() or not f.is_file():
            continue
        code, kind, sub = place
        out.append({"p": code, "f": kind, "sub": sub, "n": f.name, "type": f.suffix.lstrip(".").lower(),
                    "date": paths.name_date(f.name)[0] or "", "kb": max(1, round(f.stat().st_size / 1024)),
                    "path": original, "at": at, "archived": True})                # #124: `at` is unique, `path` may not be
    return sorted(out, key=lambda x: (x["date"], x["n"]), reverse=True)


def _archived_hit(path):
    """(kind, archived path, original path) of the archived file `path` names: by its own place in 99 Archive first (unique), else by
    the stored path it came from (the first such, as before #124); (None, None, None) when the archive didn't move it."""
    first = (None, None, None)
    for k in ("reports", NOTE):
        moved = archived_moves(kind=k)
        if path in moved:
            return k, path, moved[path]
        hit = next((a for a, o in moved.items() if o == path), None)
        if hit and first[0] is None:
            first = (k, hit, path)
    return first


def back_spec(path):
    """(spec, None) that moves an archived file back, or (None, why not). `path` is the archived file's own stored path (Files'
    `at`, #124: unique, where two deleted notes may share one first name), or, as before, the stored path it came from."""
    import reach
    path = str(path or "")
    if not path.startswith("projects/") or ".." in Path(path).parts:
        return None, "that isn't a stored project path"
    kind, at, original = _archived_hit(paths.follow_stored(path))     # #252: a folder renamed by hand
    if not at:
        return None, "that file isn't one the archive moved, so it can't be moved back"
    src, dst = paths.resolve(at, archived=False), paths.resolve(original, archived=False)
    if src.is_symlink() or not src.is_file():
        return None, f"{src.name} isn't in its archive folder any more"
    name = dst.name
    if os.path.lexists(dst):
        if kind != NOTE or not reach.NOTES_BACK_RENAMES:
            return None, f"{dst.name} is already in its place: nothing is overwritten (rename or move that file first)"
        dst = paths.free_path(dst.parent, dst.stem, dst.suffix)     # #124: a new note took the name: back as <name>-2.md
        original = paths.rel(dst)
    place = _place(original)
    title = f"Move back {name}" + (f" as {dst.name} (a note has its name)" if dst.name != name else "")
    return {"source_run": "archive", "items": [], "file_changes": {
        "title": title, "project": place[0] if place and place[0] != "_portfolio" else None,
        "archive": BACK if kind == "reports" else NOTE_BACK, "file_ops": [{"op": "move", "from": at, "to": original}]}}, None
# ===== end BL-331 =====


# ===== #124: Delete note (Alan, 15-10-2026) =====
# A note is never deleted for good: Delete note moves its file into its own engagement's (or the portfolio's) 99 Archive, keeping
# its place below it (<…>/99 Archive/<notes folder>/<note>.md; a name taken there gets -2, -3…). It is a `move` of kind "notes",
# the BL-09 guard exception: reach.archive_move_problem checks the shape, and only tracker.py apply moves it, from the live
# server's own approval card (propose.py stages it only from the server's snapshot in system/guard/), after Alan's confirm box in
# the Notes tab. Files › Archived lists it with Move back (the exact reverse, "notes_back", back_spec above); undo puts it back.
# Its pictures stay in _images (the note's links to them work again once it is back). Nothing is read from the note but its
# front-matter title, for the card; its text goes nowhere.
NOTE, NOTE_BACK = "notes", "notes_back"


def note_delete_spec(rel):
    """(spec, None) that moves the note at stored path `rel` into its own folder's 99 Archive, or (None, why not)."""
    import notes
    hit = notes.note_of(rel)
    if not hit or hit[1].is_symlink() or not hit[1].is_file():
        return None, "that isn't a note that is there"
    code, p = hit
    base = paths.portfolio_dir() if code == "_portfolio" else paths.project_dir(code)
    dest = paths.free_path(base / paths.ARCHIVE / paths.folder_name("notes").strip("/"), p.stem, p.suffix)
    title = str(notes.read(p)[0].get("title") or p.stem).replace("\n", " ").strip()[:160]
    return {"source_run": "notes", "items": [], "file_changes": {
        "title": f"Delete note \u201c{title}\u201d (move it to the archive)", "project": None if code == "_portfolio" else code,
        "archive": NOTE, "file_ops": [{"op": "move", "from": paths.rel(p), "to": paths.rel(dest)}]}}, None
# ===== end #124 =====


def main(argv):
    """Run the command in `argv` (see the module's description)."""
    cmd = argv[0] if argv else ""
    if cmd == "daily":
        code, line = daily("--force" in argv)
        if line:
            print(line)
        return code
    if cmd == "items":
        if dev_repo() and "--dry-run" not in argv:
            print("Development repository (.creaite-dev): archiving is not run here (use --dry-run).")
            return 1
        code, line = run_items(force=True, dry="--dry-run" in argv)
        print(line)
        return code
    if cmd == "reports":
        spec = reports_spec()
        if not spec:
            print(f"No reports or minutes older than {report_months()} months: nothing to archive.", file=sys.stderr)
            return 1
        out = argv[argv.index("--out") + 1] if "--out" in argv and argv.index("--out") + 1 < len(argv) else None
        import propose
        return propose.emit_spec(spec, out)
    if cmd == "status":
        st = status()
        if "--json" in argv:
            print(json.dumps({**st, "items_line": items_line(st), "reports_line": reports_line(st)}))
        else:
            print(items_line(st))
            print(reports_line(st))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    try:
        import log as debuglog  # BL-102: the debug log (not `log`: some scripts have a function of that name); a script runs without it
    except ImportError:
        debuglog = None
    sys.exit(debuglog.main("archive.py", main, sys.argv[1:]) if debuglog else main(sys.argv[1:]))
