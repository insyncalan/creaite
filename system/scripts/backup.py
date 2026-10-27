"""creaite backups that look after themselves (BL-323; Alan, 14-10-2026). Standard library only.

Usage: system/scripts/run backup.py list                     the daily zips, here and in OneDrive, newest first (read only)
       system/scripts/run backup.py show <zip or YYYY-MM-DD>  what a zip holds, checked against its manifest (read only)
       system/scripts/run backup.py check                    the restore check now (it also runs once a week by itself)
       system/scripts/run backup.py tidy [--dry-run]         Tidy up now (it also runs once a day by itself)
       system/scripts/run backup.py restore <zip or YYYY-MM-DD> [--claude-md] [--dry-run]
                                                             restore this vault from a daily zip (cx-setup, after Alan's yes)

Once a day, after the daily database backup (session.py), `after_daily_backup`:
  1. makes creaite-backup-YYYY-MM-DD.zip in system/backups/: the day's closed database backup (never the live file),
     system/config/, .claude/settings.local.json, the root CLAUDE.md, system/staging/ (never ask creaite's chats or their
     images, never vip.json), the vault's git history as one closed file (git bundle), system/history/flow-*.json, processed.txt and a
     manifest.json (each file's size and SHA-256, and the creaite version). It is written under a temporary name and renamed;
  2. copies the newest zip to the OneDrive folder (locations.offsite_backup), again under a temporary name then renamed, so
     OneDrive never syncs half a file. If OneDrive can't be reached nothing stops: the copy is made the next day it can be;
  3. Tidy up (once a day, never in the development repository, never when today's backup or zip failed, and never from a
     process an ask creaite run started (Alan, 14-10-2026): see `ask_run`): removes what the
     retention rules no longer keep, only files creaite wrote (matched by their exact name in their own folder) and never the
     newest of a kind. Logged as counts and sizes; system/backups/backup-state.json keeps the last run for Health;
  4. the restore check (once a week): the newest daily backup and the newest zip's database pass SQLite's integrity_check, the
     zip matches its manifest, and its git bundle verifies.

Retention (backups.* in settings.json; locally and in OneDrive): daily database backups and daily zips every day for
`daily_days` (30), then one a week (the Monday's: the week's earliest) for `weekly_days` (365), then one a month (the first:
the month's earliest) for good; a month's first is kept through the weekly year, or it couldn't be kept for good. Apply, undo,
revert, migrate and restore copies `copy_days` (14). Dashboard snapshots `snapshot_days` (30), then the month's first.
flow-*.json for good. Release zips: the installed one and `releases_kept` - 1 before it (newer ones are kept). Update backups:
the last `update_backups_kept` (3). File-change backups `file_change_days` (90). Applied proposals are all kept.
"""
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import zipfile
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

STATE = paths.BACKUPS / "backup-state.json"        # the last zip, Tidy up and restore check, for Health (never in the zip)
DAY = r"(\d{4}-\d{2}-\d{2})"
DAILY_DB = re.compile(rf"tracker-{DAY}\.db")
DAILY_ZIP = re.compile(rf"creaite-backup-{DAY}\.zip")
DB_COPY = re.compile(rf"tracker-{DAY}-\d{{6}}-(?:apply|undo|revert|migrate|restore)(?:-\d+)?\.db")
SNAPSHOT = re.compile(rf"dashboard-{DAY}\.html")
RELEASE = re.compile(r"creaite-(\d+)\.(\d+)\.(\d+)\.zip")
UPDATE_BACKUP = re.compile(r"update-\d{4}-\d{2}-\d{2}-\d{6}-\d+\.\d+\.\d+-to-\d+\.\d+\.\d+(?:-\d+)?")
CHANGE_DIR = re.compile(r"\d{4,}")
BUNDLE = "vault.bundle"
MANIFEST = "manifest.json"
DEFAULTS = {"daily_days": 30, "weekly_days": 365, "copy_days": 14, "snapshot_days": 30, "file_change_days": 90,
            "releases_kept": 3, "update_backups_kept": 3}
VERIFY_EVERY_DAYS = 7
LEFT_OUT = ("system/staging/ask/", "system/staging/uploads/ask/",   # ask creaite chats and images: can hold mail and Teams text
            "system/staging/vip.json",                                  # VIP is private to Alan (BL-288; Alan, 14-10-2026)
            "system/staging/drafts/calendar")                           # #369: the raw calendar reply (invite text, passcodes)
RESTORABLE = ("system/tracker.db", "system/config/", ".claude/settings.local.json", "CLAUDE.md", "system/staging/",
              "system/history/flow-", "system/processed.txt", BUNDLE, MANIFEST)


class BackupError(Exception):
    """A backup, check or restore that can't go ahead; the message says why, for Alan."""


# ── Settings, clock, state, log ────────────────────────────────────────────────

def settings():
    """backups.* retention values from settings.json, defaults filled in (whole days or counts, at least 1)."""
    try:
        block = paths.load_settings().get("backups") or {}
    except (OSError, ValueError):
        block = {}
    out = dict(DEFAULTS)
    for k in DEFAULTS:
        try:
            out[k] = max(1, int(block.get(k, DEFAULTS[k])))
        except (TypeError, ValueError):
            out[k] = DEFAULTS[k]           # a bad value keeps the agreed default
    return out


def today():
    """Today, or CREAITE_NOW's day in tests."""
    fixed = os.environ.get("CREAITE_NOW")
    return datetime.strptime(fixed[:10], "%Y-%m-%d").date() if fixed else date.today()


def is_dev():
    """True in the development repository (.creaite-dev)."""
    return (paths.ROOT / ".creaite-dev").exists()


# ===== BL-323 (Alan, 14-10-2026): a plain ask creaite chat never triggers a deletion =====
ASK_ENV = "CREAITE_HEADLESS_RUN"        # set by the live server on every headless Claude run it starts (inherited by its tools)


def ask_run():
    """True when this process belongs to, or runs beside, an ask creaite (headless) run: the live server's flag in the
    environment, or system/guard/run.json present (only the server writes it, at a run's start, and removes it at its end).
    Fails closed: if the guard folder can't be read, it counts as a run."""
    if os.environ.get(ASK_ENV):
        return True
    try:
        return (paths.GUARD / "run.json").exists()
    except OSError:
        return True
# ===== end BL-323 =====


def state():
    """system/backups/backup-state.json, or {}."""
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(key, value):
    """Record the last run of one step (zip, tidy, verify) in the state file."""
    data = state()
    data[key] = value
    try:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        tmp = STATE.with_name(STATE.name + ".part")
        tmp.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
        os.replace(tmp, STATE)
    except OSError:  # the step's own answer still reaches Alan; Health then says the step hasn't run
        pass


def note(level, message):
    """One debug-log line (counts, names and sizes only, never contents); the log is optional."""
    try:
        import log as debuglog
    except ImportError:  # BL-228: the debug log is optional
        return
    getattr(debuglog, level)("backup", message)


def sha(data):
    """SHA-256 of bytes."""
    return hashlib.sha256(data).hexdigest()


def mb(n):
    """Bytes as MB for a person."""
    return f"{n / 1_000_000:.0f} MB" if n >= 10_000_000 else f"{n / 1_000_000:.1f} MB"


def shown(day):
    """YYYY-MM-DD as DD-MM-YYYY."""
    return f"{day[8:10]}-{day[5:7]}-{day[0:4]}"


# ── Where the zips are ─────────────────────────────────────────────────────────

def offsite_dir():
    """The OneDrive backup folder (locations.offsite_backup inside the projects folder), or None when the projects live in the
    vault or the setting is empty."""
    sub = str(paths.locations().get("offsite_backup") or "").strip("/")
    return paths.projects_root() / sub if paths.external() and sub else None


def dated(folder, pattern):
    """{date: path} of the files in `folder` whose whole name matches `pattern` (group 1 the date); never a link or a folder."""
    out = {}
    if folder is None or not Path(folder).is_dir():
        return out
    for f in Path(folder).iterdir():
        m = pattern.fullmatch(f.name)
        if m and f.is_file() and not f.is_symlink():
            try:
                out[date.fromisoformat(m.group(1))] = f
            except ValueError:   # a name like 2026-13-40 isn't creaite's: left alone
                continue
    return out


def zip_name(day):
    """creaite-backup-YYYY-MM-DD.zip."""
    return f"creaite-backup-{day}.zip"


def list_zips():
    """Every daily zip here and in OneDrive, newest first: [{day, where, path, size}]."""
    out = []
    for where, folder in (("this laptop", paths.BACKUPS), ("OneDrive", offsite_dir())):
        for d, f in dated(folder, DAILY_ZIP).items():
            out.append({"day": d.isoformat(), "where": where, "path": str(f), "size": f.stat().st_size})
    return sorted(out, key=lambda z: (z["day"], z["where"] == "this laptop"), reverse=True)


def choices():
    """The zips Settings › Health offers to restore, newest first, one per name (the laptop's copy first): [{name, day, where,
    size, path}]. The live server accepts a restore only for a name in this list."""
    seen, out = set(), []
    for z in sorted(list_zips(), key=lambda z: (z["day"], z["where"] == "this laptop"), reverse=True):
        name = Path(z["path"]).name
        if name not in seen:
            seen.add(name)
            out.append({**z, "name": name})
    return out


def find_zip(name):
    """A zip by path, or the newest one for a YYYY-MM-DD (the laptop's first); raises BackupError."""
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", name or ""):
        hit = next((z for z in list_zips() if z["day"] == name), None)
        if not hit:
            raise BackupError(f"There is no backup of {shown(name)}: say \"list\" to see the ones there are.")
        return Path(hit["path"])
    p = Path(name).expanduser()
    p = p if p.is_absolute() else paths.ROOT / p
    if not p.is_file():
        raise BackupError(f"There is no such file: {name}")
    return p


# ── The daily zip ──────────────────────────────────────────────────────────────

def collect(day):
    """[(name in the zip, file)] for the day's zip: the closed database backup, never the live database."""
    db = paths.BACKUPS / f"tracker-{day}.db"
    if not db.is_file():
        raise BackupError(f"there is no daily backup of {shown(str(day))} to put in the zip")
    out = [("system/tracker.db", db)]
    for top in (paths.SYSTEM / "config", paths.STAGING):
        for f in sorted(top.rglob("*")) if top.is_dir() else []:
            arc = f.relative_to(paths.ROOT).as_posix()
            if f.is_file() and not f.is_symlink() and not arc.startswith(LEFT_OUT) and not wanted_out(f):
                out.append((arc, f))
    for f in (paths.ROOT / ".claude" / "settings.local.json", paths.ROOT / "CLAUDE.md", paths.PROCESSED):
        if f.is_file():
            out.append((f.relative_to(paths.ROOT).as_posix(), f))
    for f in sorted(paths.HISTORY.glob("flow-*.json")) if paths.HISTORY.is_dir() else []:
        out.append((f.relative_to(paths.ROOT).as_posix(), f))
    return out


def wanted_out(f):
    """Working files that are never backed up: a half-written file, the Mac's folder notes, compiled Python."""
    return f.name == ".DS_Store" or f.name.endswith((".part", ".pyc")) or "__pycache__" in f.parts


PRIVATE_PATHS = ("system/staging", "system/logs", "system/branding")   # never in the zip's git history (BL-288, BL-323)
PRIVATE_SPECS = tuple(f":(icase){p}" for p in PRIVATE_PATHS)                # a volume that ignores case may hold System/Staging
EXCLUDE_SPECS = tuple(f":(exclude,icase){p}" for p in PRIVATE_PATHS)
SAFE_GIT = ("-c", "core.hooksPath=/dev/null", "-c", "core.excludesFile=/dev/null", "-c", "commit.gpgsign=false",
            "-c", "user.name=creaite", "-c", "user.email=creaite@localhost",
            "-c", "gc.auto=0", "-c", "maintenance.auto=false", "-c", "gc.autoDetach=false")
# SAFE_GIT: no user hook, global setting or background gc/maintenance runs on the snapshot repository
BUNDLE_NOTE = []                       # ["snapshot"] when the last bundle was the filtered snapshot (for the manifest)
SNAPSHOT_NOTE = "git history: a snapshot of the latest commit (earlier history held private files)"


def make_bundle(dest):
    """The vault's git history as one closed file at `dest`; None when made, else why not (no history is not a failure).
    Fails closed: any doubt gives no bundle, never an unfiltered one. Never changes the vault's repository (read only).
    If no commit ever held a private path the bundle is the whole history; otherwise it is one commit, a snapshot of HEAD
    without the private paths, built in a temporary repository, so old commits that hold chats or vip.json are not copied."""
    if not (paths.ROOT / ".git").exists():
        return "this vault has no git history"
    git = shutil.which("git")
    if not git:
        return "git isn't installed"
    try:
        return bundle_filtered(git, Path(dest))
    except (OSError, subprocess.SubprocessError) as e:
        Path(dest).unlink(missing_ok=True)
        return f"git bundle failed: {type(e).__name__}"


def git_env(index=None):
    """The caller's environment without any GIT_* variable (a GIT_DIR, GIT_INDEX_FILE or GIT_WORK_TREE exported by a hook or
    wrapper would point git at the vault's own repository and change it); only `index` (a temporary index file) is set."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    if index:
        env["GIT_INDEX_FILE"] = str(index)
    return env


def run_git(git, repo, *args, index=None, **kw):
    """Run git in `repo` with git_env(index); the CompletedProcess."""
    return subprocess.run([git, "-C", str(repo), *args], capture_output=True, timeout=300, env=git_env(index), **kw)


def bundle_filtered(git, dest):
    """The bundle at `dest` (whole history if clean, else a filtered snapshot); None when made, else why not."""
    root = paths.ROOT
    BUNDLE_NOTE.clear()
    seen = run_git(git, root, "rev-list", "--all", "--full-history", "-n", "1", "--", *PRIVATE_SPECS,
                   text=True)
    if seen.returncode:
        return "git bundle failed: couldn't check the history for private files"
    if not seen.stdout.strip():                                    # clean history: the whole of it, as before
        r = run_git(git, root, "bundle", "create", str(dest), "--all", text=True)
        return None if not r.returncode and dest.is_file() else fail(dest, r)
    branch = run_git(git, root, "symbolic-ref", "-q", "--short", "HEAD", text=True).stdout.strip()
    if not branch or run_git(git, root, "rev-parse", "-q", "--verify", "HEAD").returncode:
        return "git bundle failed: the history holds private files and has no branch to snapshot"
    work = tempfile.mkdtemp(prefix="creaite-bundle-")
    try:
        snap, idx = Path(work) / "snap", Path(work) / "index"
        snap.mkdir()
        read = run_git(git, root, "read-tree", "HEAD", index=idx)       # a temporary index: the vault's own is never touched
        listed = run_git(git, root, "ls-files", "-z", "--", ".", *EXCLUDE_SPECS, index=idx)
        if read.returncode or listed.returncode:
            return "git bundle failed: couldn't read the latest commit"
        out = run_git(git, root, "checkout-index", "-z", "--stdin", f"--prefix={snap}/", index=idx, input=listed.stdout)
        steps = [["init", "-q"], ["checkout", "-q", "-b", branch], ["add", "-A", "-f"],
                 ["commit", "-q", "-m", SNAPSHOT_NOTE], ["bundle", "create", str(dest), "HEAD", branch]]
        if out.returncode or any(run_git(git, snap, *SAFE_GIT, *st).returncode for st in steps) or not dest.is_file():
            dest.unlink(missing_ok=True)
            return "git bundle failed: couldn't build the filtered snapshot"
    finally:
        shutil.rmtree(work, ignore_errors=True)         # a temporary folder that won't delete never discards a good bundle
    BUNDLE_NOTE.append("snapshot")
    return None


def fail(dest, r):
    """Remove a half-made bundle; the reason from git's last line."""
    dest.unlink(missing_ok=True)
    last = (r.stderr.strip().splitlines() or ["no output"])[-1]
    return f"git bundle failed: {last[:200]}"


def version():
    """The installed creaite version, or 0.0.0."""
    return paths.VERSION_FILE.read_text(encoding="utf-8").strip() if paths.VERSION_FILE.exists() else "0.0.0"


def make_zip(day, folder=None):
    """Write creaite-backup-<day>.zip into `folder` (system/backups/): under a temporary name, renamed once complete, so it
    never exists half-written. Returns its path; raises BackupError (nothing is left behind)."""
    folder = Path(folder or paths.BACKUPS)
    folder.mkdir(parents=True, exist_ok=True)
    dest, tmp = folder / zip_name(day), folder / f".{zip_name(day)}.part"
    files = []
    try:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z, tempfile.TemporaryDirectory(dir=folder) as work:
            for arc, f in collect(day):
                data = f.read_bytes()
                z.writestr(arc, data)
                files.append({"path": arc, "size": len(data), "sha256": sha(data)})
            bundle = Path(work) / BUNDLE
            why = make_bundle(bundle)
            if why is None:
                data = bundle.read_bytes()
                z.writestr(BUNDLE, data)
                files.append({"path": BUNDLE, "size": len(data), "sha256": sha(data)})
            manifest = {"creaite_backup": 1, "day": str(day), "made": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "version": version(), "files": files, "git": "bundle" if why is None else why}
            if why is None and BUNDLE_NOTE:
                manifest["git_note"] = SNAPSHOT_NOTE
            z.writestr(MANIFEST, json.dumps(manifest, indent=1) + "\n")
        os.replace(tmp, dest)
    except (OSError, sqlite3.Error, zipfile.BadZipFile, subprocess.SubprocessError, BackupError) as e:
        tmp.unlink(missing_ok=True)
        if isinstance(e, BackupError):
            raise
        raise BackupError(f"{type(e).__name__}: {e}") from e
    note("info", f"daily zip made: {dest.name}, {len(files)} files, {mb(dest.stat().st_size)}")
    return dest


def ensure_zip(day):
    """Today's zip, made if it isn't there yet: (path, made?)."""
    dest = paths.BACKUPS / zip_name(day)
    if dest.is_file():
        return dest, False
    return make_zip(day), True


def copy_offsite():
    """Copy the newest local daily zip into the OneDrive folder, under a temporary name then renamed; never the live database.
    {"copied": stored path or None, "error": text or None}. A failure never stops anything: the next day copies the newest."""
    out = {"copied": None, "error": None}
    dest_dir = offsite_dir()
    if dest_dir is None:
        return out
    try:
        zips = dated(paths.BACKUPS, DAILY_ZIP)
        if not zips:
            return out
        if not paths.projects_root().is_dir():
            out["error"] = "the projects folder isn't reachable (is OneDrive running?)"
            note("warn", "OneDrive backup copy not made: the projects folder isn't reachable")
            return out
        src = zips[max(zips)]
        dest = dest_dir / src.name
        if not (dest.exists() and dest.stat().st_size == src.stat().st_size):
            dest_dir.mkdir(parents=True, exist_ok=True)
            tmp = dest_dir / f".{src.name}.part"
            shutil.copyfile(src, tmp)
            os.replace(tmp, dest)
            out["copied"] = paths.rel(dest)
            note("info", f"OneDrive backup copy made: {dest.name}")
    except OSError as e:
        out["error"] = f"{type(e).__name__}: {e}"
        note("warn", f"OneDrive backup copy not made: {type(e).__name__}")
    return out


def last_offsite():
    """The date (YYYY-MM-DD) of the newest copy in the OneDrive folder, a daily zip or an older tracker-*.db copy, or None."""
    d = offsite_dir()
    days = list(dated(d, DAILY_ZIP)) + list(dated(d, DAILY_DB))
    return max(days).isoformat() if days else None


# ── Retention and Tidy up ─────────────────────────────────────────────────────

def keep_daily(days, on, s):
    """The dates kept of a daily series (database backups, zips): every day for daily_days, then the week's earliest (the
    Monday's) for weekly_days, and the month's earliest (the first) for good; the newest always."""
    days = sorted(set(days))
    week, month, keep = {}, {}, set(days[-1:])
    for d in days:
        week.setdefault(d.isocalendar()[:2], d)
        month.setdefault((d.year, d.month), d)
    for d in days:
        age = (on - d).days
        if age < s["daily_days"] or month[(d.year, d.month)] == d or age < s["weekly_days"] and week[d.isocalendar()[:2]] == d:
            keep.add(d)
    return keep


def keep_monthly(days, on, keep_days):
    """Dashboard snapshots: every day for keep_days, then the month's earliest; the newest always."""
    days = sorted(set(days))
    month = {}
    for d in days:
        month.setdefault((d.year, d.month), d)
    return {d for d in days if (on - d).days < keep_days or month[(d.year, d.month)] == d} | set(days[-1:])


def plan_daily(on, s):
    """[(kind, path)] the daily series no longer keep, here and in OneDrive."""
    out = []
    for kind, folder, pattern in (("daily database backup", paths.BACKUPS, DAILY_DB),
                                  ("daily zip", paths.BACKUPS, DAILY_ZIP),
                                  ("OneDrive zip", offsite_dir(), DAILY_ZIP),
                                  ("OneDrive database copy", offsite_dir(), DAILY_DB)):
        files = dated(folder, pattern)
        keep = keep_daily(files, on, s)
        out += [(kind, f) for d, f in files.items() if d not in keep]
    return out


def plan_copies(on, s):
    """Apply, undo, revert, migrate and restore copies older than copy_days; never the newest."""
    found = sorted((f.name, f) for f in (paths.BACKUPS.iterdir() if paths.BACKUPS.is_dir() else [])
                   if DB_COPY.fullmatch(f.name) and f.is_file() and not f.is_symlink())
    out = []
    for name, f in found[:-1]:
        try:
            if (on - date.fromisoformat(DB_COPY.fullmatch(name).group(1))).days >= s["copy_days"]:
                out.append(("apply copy", f))
        except ValueError:   # not a real date: not creaite's
            continue
    return out


def plan_snapshots(on, s):
    """Dashboard snapshots no longer kept (flow-*.json are kept for good)."""
    files = dated(paths.HISTORY, SNAPSHOT)
    keep = keep_monthly(files, on, s["snapshot_days"])
    return [("dashboard snapshot", f) for d, f in files.items() if d not in keep]


def plan_releases(s):
    """Release zips older than the installed one's releases_kept - 1 predecessors; the installed and newer ones are kept."""
    try:
        installed = tuple(int(x) for x in version().split("."))
    except ValueError:
        return []
    found = sorted((tuple(int(x) for x in m.groups()), f) for f in (paths.RELEASES.iterdir() if paths.RELEASES.is_dir() else [])
                   for m in [RELEASE.fullmatch(f.name)] if m and f.is_file() and not f.is_symlink())
    older = [f for v, f in found if v < installed]
    if not found or not any(v == installed for v, _ in found):
        return []                     # without the installed release here, nothing is removed
    drop = older[:max(0, len(older) - (s["releases_kept"] - 1))]
    return [("release zip", f) for f in drop if f != found[-1][1]]


def plan_updates(s):
    """Update backups beyond the last update_backups_kept (only folders holding their update.json)."""
    found = sorted(d for d in (paths.BACKUPS.iterdir() if paths.BACKUPS.is_dir() else [])
                   if UPDATE_BACKUP.fullmatch(d.name) and d.is_dir() and not d.is_symlink() and (d / "update.json").is_file())
    return [("update backup", d) for d in found[:max(0, len(found) - s["update_backups_kept"])]]


def change_dates():
    """{change id: date} from the files log (system/config/files-log.jsonl)."""
    out = {}
    try:
        lines = (paths.SYSTEM / "config" / "files-log.jsonl").read_text(encoding="utf-8").splitlines()
    except OSError:
        return out
    for line in lines:
        try:
            e = json.loads(line)
            out.setdefault(int(e["id"]), date.fromisoformat(str(e["at"])[:10]))
        except (ValueError, KeyError, TypeError):   # a line that isn't a change: skipped
            continue
    return out


def plan_changes(on, s):
    """File-change backups (system/backups/files/changes/<n>/) older than file_change_days; never the newest."""
    folder = paths.BACKUPS / "files" / "changes"
    found = sorted((int(d.name), d) for d in (folder.iterdir() if folder.is_dir() else [])
                   if CHANGE_DIR.fullmatch(d.name) and d.is_dir() and not d.is_symlink())
    when = change_dates()
    out = []
    for n, d in found[:-1]:
        made = when.get(n) or datetime.fromtimestamp(d.stat().st_mtime).date()
        if (on - made).days >= s["file_change_days"]:
            out.append(("file-change backup", d))
    return out


def plan(on=None, s=None):
    """[(kind, path)] that Tidy up would remove today."""
    on, s = on or today(), s or settings()
    return plan_daily(on, s) + plan_copies(on, s) + plan_snapshots(on, s) + plan_releases(s) + plan_updates(s) + \
        plan_changes(on, s)


def size_of(p):
    """Bytes in a file or a folder."""
    if p.is_dir():
        return sum(f.stat().st_size for f in p.rglob("*") if f.is_file() and not f.is_symlink())
    return p.stat().st_size


def tidy(on=None, dry=False):
    """Remove what the retention rules no longer keep. {removed, bytes, kinds, dry}; refused in the development repository."""
    if is_dev():
        raise BackupError("Tidy up never runs in the development repository.")
    on = on or today()
    found = plan(on)
    kinds, total, removed = {}, 0, 0
    for kind, p in found:
        n = size_of(p)
        if not dry:
            try:
                shutil.rmtree(p) if p.is_dir() else p.unlink()
            except OSError:   # in use or gone: left for the next run, and not counted
                continue
        kinds[kind] = kinds.get(kind, 0) + 1
        total, removed = total + n, removed + 1
    out = {"day": on.isoformat(), "removed": removed, "bytes": total, "kinds": kinds, "dry": dry}
    if not dry:
        save_state("tidy", {k: out[k] for k in ("day", "removed", "bytes", "kinds")})
        note("info", f"tidy up: removed {removed} files, {mb(total)} ({', '.join(f'{k} {v}' for k, v in sorted(kinds.items())) or 'none'})")
    return out


# ── The restore check ─────────────────────────────────────────────────────────

def integrity(db):
    """None if SQLite's integrity_check says ok, else what it found."""
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            got = con.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            con.close()
    except sqlite3.Error as e:
        return f"{type(e).__name__}: {e}"
    return None if got == "ok" else str(got)[:200]


def read_manifest(z):
    """The zip's manifest.json, or raises BackupError."""
    try:
        return json.loads(z.read(MANIFEST).decode("utf-8"))
    except (KeyError, ValueError) as e:
        raise BackupError(f"it has no readable manifest ({type(e).__name__})") from e


def check_names(z, manifest):
    """Problems with the zip's names: one outside what a backup holds, a path that climbs out, a file missing or unlisted."""
    problems = []
    names = set(z.namelist())
    listed = {f["path"] for f in manifest.get("files") or []}
    for n in names:
        if n.startswith("/") or ".." in Path(n).parts or not n.startswith(RESTORABLE) or n.startswith(LEFT_OUT):
            problems.append(f"{n} isn't something a creaite backup holds")
    problems += [f"{n} is listed in the manifest but missing" for n in sorted(listed - names)]
    problems += [f"{n} is in the zip but not in the manifest" for n in sorted(names - listed - {MANIFEST})]
    return problems


def check_zip(path, deep=True):
    """(problems, manifest) for a daily zip: complete against its manifest (each file's size and checksum), and, when deep, its
    database passes integrity_check and its git bundle verifies."""
    try:
        with zipfile.ZipFile(path) as z:
            manifest = read_manifest(z)
            problems = check_names(z, manifest)
            names = set(z.namelist())
            for f in manifest.get("files") or []:
                if f["path"] in names:
                    data = z.read(f["path"])
                    if len(data) != f.get("size") or sha(data) != f.get("sha256"):
                        problems.append(f"{f['path']} doesn't match its checksum")
            if deep and not problems:
                problems += deep_checks(z, names)
    except (OSError, zipfile.BadZipFile, BackupError) as e:
        return [f"the zip can't be read: {e}"], {}
    return problems, manifest


def deep_checks(z, names):
    """The zip's database passes integrity_check; its git bundle (if any) verifies."""
    problems = []
    with tempfile.TemporaryDirectory() as work:
        if "system/tracker.db" not in names:
            problems.append("it holds no database")
        else:
            db = Path(work) / "tracker.db"
            db.write_bytes(z.read("system/tracker.db"))
            bad = integrity(db)
            if bad:
                problems.append(f"its database fails the integrity check: {bad}")
        if BUNDLE in names:
            b = Path(work) / BUNDLE
            b.write_bytes(z.read(BUNDLE))
            bad = verify_bundle(b, Path(work) / "repo")
            if bad:
                problems.append(f"its git history can't be read: {bad}")
    return problems


def verify_bundle(bundle, scratch):
    """None if `git bundle verify` reads the bundle and its pack unpacks (in an empty scratch repository), else why not."""
    git = shutil.which("git")
    if not git:
        return None                    # can't check without git: the zip's checksum still holds
    try:
        subprocess.run([git, "init", "-q", str(scratch)], capture_output=True, check=True, timeout=60, env=git_env())
        for step in ("verify", "unbundle"):            # unbundle indexes the pack, so a damaged one fails here
            r = subprocess.run([git, "-C", str(scratch), "bundle", step, str(bundle)], capture_output=True, text=True,
                               timeout=300, env=git_env())
            if r.returncode:
                return ((r.stderr.strip().splitlines() or [f"git bundle {step} failed"])[-1])[:200]
    except (OSError, subprocess.SubprocessError) as e:
        return f"{type(e).__name__}"
    return None


def newest_zip():
    """The newest daily zip: on the laptop, else in OneDrive; or None."""
    zips = list_zips()
    return Path(zips[0]["path"]) if zips else None


def verify(on=None):
    """The restore check: the newest daily backup and the newest zip. Saves {day, ok, problems, checked} for Health."""
    on = on or today()
    problems, checked, snapshot = [], [], False
    daily = dated(paths.BACKUPS, DAILY_DB)
    if daily:
        f = daily[max(daily)]
        checked.append(f.name)
        bad = integrity(f)
        if bad:
            problems.append(f"the daily backup {f.name} fails the integrity check: {bad}")
    z = newest_zip()
    if z:
        checked.append(z.name)
        bad, manifest = check_zip(z)
        problems += [f"{z.name}: {p}" for p in bad]
        snapshot = bool(manifest.get("git_note"))
    out = {"day": on.isoformat(), "ok": not problems, "problems": problems[:10], "checked": checked}
    if z and snapshot:
        out["note"] = "git history in the zip: one snapshot commit"        # Health shows it (doctor.backup_check)
    save_state("verify", out)
    note("info" if not problems else "warn", f"restore check: {'ok' if not problems else f'{len(problems)} problem(s)'}, "
                                             f"{len(checked)} checked")
    return out


def due(key, on, every_days):
    """True when the state's last `key` run is `every_days` or more before `on` (or never ran)."""
    last = (state().get(key) or {}).get("day")
    try:
        return not last or (on - date.fromisoformat(last)).days >= every_days
    except ValueError:
        return True


# ── Once a day ────────────────────────────────────────────────────────────────

def after_daily_backup(on=None):
    """The steps after the day's database backup (session.py): the zip, the OneDrive copy, Tidy up once a day, the restore
    check once a week. Returns the lines worth saying; never raises."""
    on, lines, ok = on or today(), [], True
    try:
        z, made = ensure_zip(on.isoformat())
        save_state("zip", {"day": on.isoformat(), "ok": True, "name": z.name})
    except BackupError as e:
        ok = False
        save_state("zip", {"day": on.isoformat(), "ok": False, "error": str(e)[:300]})
        note("warn", f"daily zip not made: {str(e)[:200]}")
        lines.append(f"Daily backup zip not made: {e}")
    r = copy_offsite()
    if r["error"]:
        lines.append(f"OneDrive backup copy not made: {r['error']}. It is made the next day OneDrive can be reached.")
    if ok and not is_dev() and not ask_run() and due("tidy", on, 1):        # never from an ask creaite run
        try:
            t = tidy(on)
            if t["removed"]:
                lines.append(f"Tidy up: removed {t['removed']} old backup files, {mb(t['bytes'])}.")
        except (BackupError, OSError) as e:
            note("warn", f"tidy up failed: {type(e).__name__}")
    if due("verify", on, VERIFY_EVERY_DAYS):
        v = verify(on)
        if not v["ok"]:
            lines.append("Restore check found a problem: " + "; ".join(v["problems"][:3]) + ". See Settings › Health.")
    return lines


# ── Restore ───────────────────────────────────────────────────────────────────

def restore_plan(names, claude_md=False, snapshot=False):
    """[(name in the zip, what restore does with it)] for Alan to see before he says yes."""
    out = []
    for n in sorted(names):
        if n == MANIFEST:
            continue
        if n == "system/tracker.db":
            what = "database: replaces system/tracker.db (the current one is backed up first)"
        elif n == "system/config/settings.json":
            what = "settings: the backup's values, with any setting this version added since"
        elif n == "CLAUDE.md":
            what = ("your CLAUDE.md: replaces it (the current one is kept)" if claude_md else
                    "your CLAUDE.md: only if this vault has none" if (paths.ROOT / "CLAUDE.md").exists() else "your CLAUDE.md")
        elif n == BUNDLE:
            what = ("git history: kept as it is (this vault has its own)" if (paths.ROOT / ".git").exists()
                    else "git history: one snapshot commit, restored from the bundle" if snapshot
                    else "git history: restored from the bundle")
        else:
            what = "restored (a file it replaces is kept first)"
        out.append((n, what))
    return out


def keep_copy(target, keep_dir):
    """Copy a file about to be replaced into keep_dir, under its vault path."""
    if target.is_file():
        dest = keep_dir / target.relative_to(paths.ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, dest)


def restore_db(data, stamp):
    """Put the zip's database in place through SQLite's backup, after a copy of the current one; then migrate it."""
    paths.BACKUPS.mkdir(parents=True, exist_ok=True)
    tmp = paths.BACKUPS / ".restore-tracker.db.part"
    tmp.write_bytes(data)
    try:
        bad = integrity(tmp)
        if bad:
            raise BackupError(f"the backup's database fails the integrity check: {bad}")
        if paths.DB.exists():
            copy_db(paths.DB, paths.free_path(paths.BACKUPS, f"tracker-{stamp}-restore", ".db"))
        copy_db(tmp, paths.DB)
    finally:
        tmp.unlink()
    r = subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "tracker.py"), "migrate"], cwd=paths.ROOT,
                       capture_output=True, text=True, timeout=300)
    return "database restored" + ("" if r.returncode == 0 else " (tracker.py migrate then failed: run it again)")


def copy_db(src, dest):
    """Copy a SQLite database with SQLite's backup, so the copy is consistent."""
    a, b = sqlite3.connect(str(src)), sqlite3.connect(str(dest))
    try:
        with b:
            a.backup(b)
    finally:
        a.close()
        b.close()


def merged_settings(data):
    """The backup's settings.json with any key this version's settings has that it lacks (the update's merge rule: values kept)."""
    restored = json.loads(data.decode("utf-8"))
    for src in (paths.SETTINGS, paths.TEMPLATES / "settings-defaults.json"):
        try:
            current = json.loads(src.read_text(encoding="utf-8"))
        except (OSError, ValueError):   # no current settings here (a fresh folder): the defaults file follows
            continue
        current.pop("_about", None)
        import update
        update.merge_new(restored, current)
    return (json.dumps(restored, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def restore_git(data):
    """The git history from the bundle, into a vault that has none (the working files are never touched)."""
    if (paths.ROOT / ".git").exists():
        return "git history: this vault has its own, kept"
    git = shutil.which("git")
    if not git:
        return "git history: not restored (git isn't installed)"
    with tempfile.TemporaryDirectory() as work:
        b = Path(work) / BUNDLE
        b.write_bytes(data)
        heads = subprocess.run([git, "bundle", "list-heads", str(b)], capture_output=True, text=True, timeout=120,
                               env=git_env()).stdout
        head = next((ln.split()[0] for ln in heads.splitlines() if ln.endswith(" HEAD")), None)
        run = [[git, "-C", str(paths.ROOT), "init", "-q"],
               [git, "-C", str(paths.ROOT), "fetch", "-q", "--update-head-ok", str(b), "+refs/heads/*:refs/heads/*",
                "+refs/tags/*:refs/tags/*"]]
        for cmd in run:
            if subprocess.run(cmd, capture_output=True, timeout=300, env=git_env()).returncode:
                return "git history: not restored (git couldn't read the bundle)"
        branch = branch_of(git, heads, head)
        if branch:
            subprocess.run([git, "-C", str(paths.ROOT), "symbolic-ref", "HEAD", branch], capture_output=True, timeout=60,
                           env=git_env())
            subprocess.run([git, "-C", str(paths.ROOT), "reset", "-q"], capture_output=True, timeout=120, env=git_env())
    return "git history restored"


def branch_of(git, heads, head):
    """The branch the bundle's HEAD points at (refs/heads/…), or None."""
    for ln in heads.splitlines():
        parts = ln.split()
        if len(parts) == 2 and parts[0] == head and parts[1].startswith("refs/heads/"):
            return parts[1]
    return None


def restore(name, claude_md=False, dry=False):
    """Restore this vault from a daily zip: the database (after a copy of the current one), the configuration files (settings
    merged), staging, the flow files, processed.txt, CLAUDE.md (only if missing, or with claude_md) and the git history (only
    into a vault without one). Every file it replaces is kept first in system/backups/restore-<time>/. Never a project file."""
    if is_dev():
        raise BackupError("Restore never runs in the development repository: use git there.")
    path = find_zip(name)
    problems, manifest = check_zip(path)
    if problems:
        raise BackupError(f"{path.name} can't be restored: " + "; ".join(problems[:5]))
    with zipfile.ZipFile(path) as z:
        steps = restore_plan(z.namelist(), claude_md, bool(manifest.get("git_note")))
        if dry:
            return {"zip": path.name, "day": manifest.get("day"), "version": manifest.get("version"), "plan": steps, "dry": True}
        done = apply_restore(z, steps, claude_md)
    note("info", f"restored from {path.name}: {len(done)} steps")
    return {"zip": path.name, "day": manifest.get("day"), "version": manifest.get("version"), "done": done, "dry": False}


def apply_restore(z, steps, claude_md):
    """Write each restorable file from the open zip; returns what was done."""
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    keep_dir = paths.free_path(paths.BACKUPS, f"restore-{stamp}")
    done, files = [], 0
    for n, _ in steps:
        data = z.read(n)
        if n == "system/tracker.db":
            done.append(restore_db(data, stamp))
            continue
        if n == BUNDLE:
            done.append(restore_git(data))
            continue
        target = paths.ROOT / n
        if n == "CLAUDE.md" and target.exists() and not claude_md:
            done.append("your CLAUDE.md: kept as it is")
            continue
        if n == "system/config/settings.json":
            data = merged_settings(data)
        if target.is_file() and target.read_bytes() == data:
            continue
        keep_copy(target, keep_dir)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        files += 1
    done.append(f"{files} files restored" + (f"; the ones replaced are in {paths.rel(keep_dir)}" if keep_dir.exists() else ""))
    return done


# ── Command line ──────────────────────────────────────────────────────────────

def cmd_list():
    """Print the daily zips, newest first."""
    zips = list_zips()
    if not zips:
        print("There are no daily backup zips yet: one is made at the first session of each day.")
        return 0
    for z in zips:
        print(f"{shown(z['day'])}  {mb(z['size']):>8}  {z['where']}  {Path(z['path']).name}")
    return 0


def cmd_show(name):
    """Print what a zip holds and whether it checks out."""
    path = find_zip(name)
    problems, manifest = check_zip(path)
    print(f"{path.name}: the backup of {shown(manifest.get('day', '????-??-??'))}, creaite {manifest.get('version', '?')}, "
          f"{len(manifest.get('files') or [])} files.")
    for n, what in restore_plan([f["path"] for f in manifest.get("files") or []], snapshot=bool(manifest.get("git_note"))):
        print(f"  {n} — {what}")
    if manifest.get("git") not in (None, "bundle"):
        print(f"  (no git history: {manifest['git']})")
    if manifest.get("git_note"):
        print(f"  ({manifest['git_note']})")
    print("Checks out: complete against its manifest, database and git history readable." if not problems
          else "Problems: " + "; ".join(problems))
    return 0 if not problems else 1


def cmd_check():
    """Run the restore check now and say what it found."""
    v = verify()
    if not v["checked"]:
        print("There is nothing to check yet: the first daily backup is made at the first session of the day.")
    elif v["ok"]:
        print(f"Restore check passed: {', '.join(v['checked'])}.")
    else:
        print("Restore check found problems: " + "; ".join(v["problems"]))
    return 0 if v["ok"] else 1


def cmd_tidy(dry):
    """Run Tidy up now (or show what it would remove)."""
    t = tidy(dry=dry)
    kinds = ", ".join(f"{v} {k}{'s' if v != 1 else ''}" for k, v in sorted(t["kinds"].items())) or "nothing"
    print(f"Tidy up{' would remove' if dry else ' removed'} {t['removed']} files, {mb(t['bytes'])}: {kinds}.")
    return 0


def cmd_restore(name, claude_md, dry):
    """Restore from a zip, or show the plan."""
    r = restore(name, claude_md, dry)
    print(f"{r['zip']}: the backup of {shown(r['day'] or '????-??-??')}, creaite {r['version']}.")
    for line in ([f"  {n} — {w}" for n, w in r["plan"]] if dry else [f"  {d}" for d in r["done"]]):
        print(line)
    if not dry:
        print("Restored. Run system/scripts/run doctor.py, then rebuild the dashboard (system/scripts/run build_dashboard.py).")
    return 0


def main(argv):
    """The command line (see the docstring)."""
    cmd = argv[0] if argv else ""
    words = [a for a in argv[1:] if not a.startswith("--")]
    try:
        if cmd == "list":
            return cmd_list()
        if cmd == "show" and words:
            return cmd_show(words[0])
        if cmd == "check":
            return cmd_check()
        if cmd == "tidy":
            return cmd_tidy("--dry-run" in argv)
        if cmd == "restore" and words:
            return cmd_restore(words[0], "--claude-md" in argv, "--dry-run" in argv)
    except BackupError as e:
        print(str(e))
        return 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    try:
        import log as debuglog  # BL-102: the debug log; a script runs without it
    except ImportError:
        debuglog = None
    sys.exit(debuglog.main("backup.py", main, sys.argv[1:]) if debuglog else main(sys.argv[1:]))
