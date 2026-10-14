"""creaite debug log (BL-102): what creaite did and where it went wrong, kept for the last 7 days.

One plain-text file per day, system/logs/debug-YYYY-MM-DD.log, one line per entry:

    2026-10-09 14:32:05 INFO  tracker      apply 3 proposals
    2026-10-09 14:32:06 ERROR sweep        calendar read failed: TimeoutError: ...
        Traceback (most recent call last):          <- a traceback is indented continuation lines

Use (standard library only; no message text, notes, chats or client content: only short descriptions, IDs, paths and counts):

    import log
    log.info("sweep", "window 2026-10-02 to 2026-10-09, 41 searched")
    log.exception("tracker", "apply failed")                  # the message plus the current traceback
    with log.run("tracker.py", "apply"):                       # start, duration, exit status; an error with its traceback
        main()

Rules the helper keeps:
  - A write never raises. A read-only folder, a full disk or a bad setting leaves the script running.
  - Today and the six days before it are kept. The first entry of a new day deletes older files (no background job).
  - `logging.level` in settings.json: "info" (the default) or "debug"; warn and error are always written.
  - A day's file stops at `logging.max_mb` (5) with one line saying so.
  - Each entry is one append, so several processes can write at once without mixing lines.
Reading (for doctor.py, session.py and, in part 2, the dashboard): files(), tail(), entries(), errors_since(), repeated().
"""
import contextlib
import os
import re
import sys
import time
import traceback
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

LEVELS = {"debug": 10, "info": 20, "warn": 30, "error": 40}
LABELS = {10: "DEBUG", 20: "INFO ", 30: "WARN ", 40: "ERROR"}
DEFAULTS = {"level": "info", "max_mb": 5, "keep_days": 7, "repeat_window_hours": 24}   # BL-263: the window
MESSAGE_LIMIT = 500
TRACEBACK_LINES = 40
FULL_NOTICE = "log full for today: later entries are not kept"
FILE = re.compile(r"debug-(\d{4}-\d{2}-\d{2})\.log$")
ENTRY = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (DEBUG|INFO|WARN|ERROR)\s+(\S+)\s*(.*)$")
CONTROL = re.compile(r"[\x00-\x1f\x7f]+")
_cache = {"stamp": None, "value": dict(DEFAULTS)}


# ── Settings and the clock ─────────────────────────────────────────────────────

def settings() -> dict:
    """The `logging` block of settings.json with defaults filled in (cached until the file changes; never raises)."""
    try:
        stamp = paths.SETTINGS.stat().st_mtime_ns
        if _cache["stamp"] != stamp:
            block = paths.load_settings().get("logging") or {}
            value = dict(DEFAULTS)
            if str(block.get("level", "")).lower() in ("debug", "info"):
                value["level"] = str(block["level"]).lower()
            for key, low, high in (("max_mb", 0.001, 500), ("keep_days", 1, 90), ("repeat_window_hours", 1, 168)):
                try:
                    value[key] = min(max(float(block.get(key, DEFAULTS[key])), low), high)
                except (TypeError, ValueError):  # BL-228: a bad setting keeps its default
                    pass
            _cache.update(stamp=stamp, value=value)
        return _cache["value"]
    except Exception:
        return dict(DEFAULTS)


def now() -> datetime:
    """The local time; CREAITE_NOW ("YYYY-MM-DD HH:MM" or with :SS) fixes it for tests, as sweep.now() does."""
    fixed = os.environ.get("CREAITE_NOW")
    if fixed:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                return datetime.strptime(fixed, fmt)
            except ValueError:  # BL-228: try the next format; the real clock if none fits
                pass
    return datetime.now()


def path_for(day: date) -> Path:
    """The debug log file for a day: system/logs/debug-YYYY-MM-DD.log (BL-102)."""
    return paths.LOGS / f"debug-{day.isoformat()}.log"


# ── Writing ────────────────────────────────────────────────────────────────────

def clean(text, limit=MESSAGE_LIMIT) -> str:
    """One line: control characters (newlines too) become spaces, and a long text is cut."""
    t = CONTROL.sub(" ", str(text)).strip()
    return t if len(t) <= limit else t[:limit - 1] + "…"


def area_of(area) -> str:
    """An area name made safe for one log column: letters, digits and _.- only, at most 20 characters."""
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(area).strip())[:20] or "creaite"


def _append(path: Path, text: str):
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, text.encode("utf-8"))               # one write per entry, so lines from two processes don't mix
    finally:
        os.close(fd)


def _emit(level: int, area, message, extra=()):
    try:
        cfg = settings()
        if level < 30 and level < LEVELS[cfg["level"]]:
            return
        t = now()
        path = path_for(t.date())
        fresh = not path.exists()
        path.parent.mkdir(parents=True, exist_ok=True)
        if fresh:
            prune(t.date())
        if path.exists() and path.stat().st_size >= cfg["max_mb"] * 1024 * 1024:
            if FULL_NOTICE not in _last_bytes(path):
                _append(path, f"{t:%Y-%m-%d %H:%M:%S} {LABELS[30]} log          {FULL_NOTICE}\n")
            return
        lines = [f"{t:%Y-%m-%d %H:%M:%S} {LABELS[level]} {area_of(area):<12} {clean(message)}"]
        lines += ["    " + clean(x, MESSAGE_LIMIT) for x in extra]
        _append(path, "\n".join(lines) + "\n")
    except Exception:  # BL-228: a log write never raises (the helper's rule)
        pass


def _last_bytes(path: Path, n=300) -> str:
    try:
        with open(path, "rb") as f:
            f.seek(max(0, path.stat().st_size - n))
            return f.read().decode("utf-8", "replace")
    except OSError:
        return ""


def debug(area, message):
    """Write a debug line to the debug log, if logging.level is debug (BL-102). Never raises."""
    _emit(10, area, message)


def info(area, message):
    """Write an info line to the debug log (BL-102). Never raises."""
    _emit(20, area, message)


def warn(area, message):
    """Write a warning line to the debug log (BL-102). Never raises."""
    _emit(30, area, message)


def error(area, message):
    """Write an error line to the debug log (BL-102). Never raises."""
    _emit(40, area, message)


def exception(area, message=""):
    """An error entry for the exception being handled, with its traceback as indented lines."""
    try:
        kind, value, tb = sys.exc_info()
        head = f"{message} — {kind.__name__}: {value}" if kind else str(message)
        lines = traceback.format_exception(kind, value, tb) if kind else []
        extra = [ln for chunk in lines for ln in chunk.rstrip("\n").splitlines()][-TRACEBACK_LINES:]
        _emit(40, area, head, extra)
    except Exception:  # BL-228: a log write never raises (the helper's rule)
        pass


@contextlib.contextmanager
def run(script, command=""):
    """Log a script run: its start, its duration and exit status, and an error with its traceback (which is re-raised)."""
    started = time.monotonic()
    area = Path(str(script)).stem
    info(area, f"start {clean(command, 200)}".strip())
    try:
        yield
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
        (info if code == 0 else warn)(area, f"exit {code} after {time.monotonic() - started:.1f}s")
        raise
    except KeyboardInterrupt:
        warn(area, f"interrupted after {time.monotonic() - started:.1f}s")
        raise
    except Exception:
        exception(area, f"failed after {time.monotonic() - started:.1f}s")
        raise
    else:
        info(area, f"done in {time.monotonic() - started:.1f}s")


SUBCOMMAND = re.compile(r"[a-z][a-z0-9_-]{0,30}$")
QUOTED = re.compile(r"'[^']*'|\"[^\"]*\"|“[^”]*”|‘[^’]*’")
ADDRESS = re.compile(r"\S+@\S+")


def rule(text, limit=160) -> str:
    """A validation or error message without the values in it: quoted text and addresses become … so what is left names the rule
    (\"owner 'Sara Khan' isn't in the register\" gives \"owner '…' isn't in the register\"). Used for item failures."""
    try:
        return clean(ADDRESS.sub("…", QUOTED.sub(lambda m: m.group(0)[0] + "…" + m.group(0)[-1], str(text))), limit)
    except Exception:
        return ""


def command_of(argv) -> str:
    """What a script was asked to do, without what it was given: the sub-command and the flag names, never a value
    (a file name, a note or a path is a value). ["apply", "--dry-run", "--file=x.json"] gives "apply --dry-run --file"."""
    try:
        argv = [str(a) for a in argv]
        words = [argv[0]] if argv and SUBCOMMAND.match(argv[0]) else []
        words += [a.split("=", 1)[0] for a in argv if a.startswith("-") and SUBCOMMAND.match(a.split("=", 1)[0].lstrip("-"))]
        return clean(" ".join(words), 200)
    except Exception:
        return ""


def main(script, fn, *args) -> int:
    """Run a script's main under the log: `sys.exit(log.main("tracker.py", main, sys.argv[1:]))`.
    Logs the start, then one exit line with the code and the time taken (non-zero is a warning), and an error with its
    traceback (re-raised). Returns the exit code, so the script's own behaviour is unchanged."""
    started = time.monotonic()
    area = Path(str(script)).stem
    info(area, f"start {command_of(sys.argv[1:])}".strip())
    try:
        code = fn(*args)
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
        (info if code == 0 else warn)(area, f"exit {code} after {time.monotonic() - started:.1f}s")
        raise
    except KeyboardInterrupt:
        warn(area, f"interrupted after {time.monotonic() - started:.1f}s")
        raise
    except Exception:
        exception(area, f"failed after {time.monotonic() - started:.1f}s")
        raise
    code = code if isinstance(code, int) else 0
    (info if code == 0 else warn)(area, f"exit {code} after {time.monotonic() - started:.1f}s")
    return code


# ── Keeping only the last days ─────────────────────────────────────────────────

def files() -> list:
    """The log files, oldest first."""
    try:
        return sorted(p for p in paths.LOGS.iterdir() if p.is_file() and FILE.match(p.name))
    except OSError:
        return []


def prune(today: date = None) -> list:
    """Delete files dated before (today − keep_days + 1): today and the six days before it stay. Returns the names removed."""
    removed = []
    try:
        today = today or now().date()
        cutoff = today - timedelta(days=int(settings()["keep_days"]) - 1)
        for p in files():
            if date.fromisoformat(FILE.match(p.name).group(1)) < cutoff:
                try:
                    p.unlink()
                    removed.append(p.name)
                except OSError:  # BL-228: an old log that can't be deleted is tried again tomorrow
                    pass
    except Exception:  # BL-228: pruning is housekeeping inside a log write, which never raises
        pass
    return removed


# ── Reading ────────────────────────────────────────────────────────────────────

def tail(n=200) -> list:
    """The last n lines across the files, oldest first."""
    out = []
    try:
        for p in reversed(files()):
            out = p.read_text(encoding="utf-8", errors="replace").splitlines() + out
            if len(out) >= n:
                break
    except OSError:  # BL-228: an unreadable log reads as what was read so far
        pass
    return out[-n:]


def entries(since: datetime = None) -> list:
    """Parsed entries, oldest first: {at, level, area, message, detail}. Indented lines belong to the entry above."""
    out = []
    try:
        for p in files():
            for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                m = ENTRY.match(line)
                if m:
                    at = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
                    out.append({"at": at, "level": m.group(2), "area": m.group(3), "message": m.group(4), "detail": []})
                elif out and line.startswith("    "):
                    out[-1]["detail"].append(line[4:])
    except OSError:  # BL-228: an unreadable log reads as what was read so far
        pass
    return [e for e in out if since is None or e["at"] >= since]


def errors_since(hours=24) -> list:
    """The ERROR entries in the last `hours` hours."""
    return [e for e in entries(now() - timedelta(hours=hours)) if e["level"] == "ERROR"]


def repeated(days=7, minimum=3) -> list:
    """[(count, area, message)] for errors seen at least `minimum` times in the last `days` days, commonest first
    (numbers in a message are ignored, so "item 4 failed" and "item 9 failed" count together)."""
    seen = {}
    for e in entries(now() - timedelta(days=days)):
        if e["level"] == "ERROR":
            key = (e["area"], re.sub(r"\d+", "#", e["message"]))
            count, sample = seen.get(key, (0, e["message"]))
            seen[key] = (count + 1, sample)
    return sorted(((c, a, s) for (a, _), (c, s) in seen.items() if c >= minimum), reverse=True)


# ===== BL-263 (fix-doctor-errors) =====
# Repeated errors with their first and last times, and whether each is still happening: one seen within the last
# `logging.repeat_window_hours` (24) is live and warns; an older one has stopped and is listed as information. Messages are the
# logged ones (IDs, paths and counts only, BL-102), shortened at a word boundary so a path is never cut in the middle.
def short(text, limit=120) -> str:
    """The text, or its words up to `limit` characters and "…": cut only at a space, so a path stays whole."""
    t = str(text)
    if len(t) <= limit:
        return t
    cut = t.rfind(" ", 0, limit)
    return t if cut <= 0 else t[:cut].rstrip(" ,;:—-") + " …"


def repeats(days=7, minimum=3, window_hours=None) -> list:
    """[{count, area, message, first, last, live}] for errors seen at least `minimum` times in the last `days` days, grouped as
    repeated() groups them; live ones first, then the most recent. `live` is a last time within the window."""
    window = float(settings()["repeat_window_hours"] if window_hours is None else window_hours)
    since = now() - timedelta(hours=window)
    seen = {}
    for e in entries(now() - timedelta(days=days)):
        if e["level"] == "ERROR":
            key = (e["area"], re.sub(r"\d+", "#", e["message"]))
            g = seen.setdefault(key, {"count": 0, "area": e["area"], "message": e["message"], "first": e["at"], "last": e["at"]})
            g["count"] += 1
            g["last"] = e["at"]
    out = [dict(g, live=g["last"] >= since) for g in seen.values() if g["count"] >= minimum]
    return sorted(out, key=lambda g: (g["live"], g["last"]), reverse=True)


def span(g) -> str:
    """"09-10 21:20 to 10-10 17:02", or one time when the first and last are the same minute."""
    a, b = g["first"].strftime("%d-%m %H:%M"), g["last"].strftime("%d-%m %H:%M")
    return a if a == b else f"{a} to {b}"
# ===== end BL-263 =====


# ===== BL-252 (fix-small-17): refused commands by shape =====
# live_server.py logs each command the guard refused as "<run> refused: <shape>" (BL-140: refused_shape, the shape only). These
# counts show whether ask creaite's instruction (no pipe, no redirect, no cd … &&) is holding: a rise means it isn't. Only the
# fixed words below ever come out, never what was logged after "refused:", so no command text can reach a count (BL-102).
REFUSED = re.compile(r"^\S+ refused: (.*)$")
REFUSAL_SHAPES = (("a pipe", "a pipe"), ("a redirect", "a redirect"), ("a cd … && prefix", "cd … &&"),
                  ("more than one command", "more than one command"), ("a heredoc", "a heredoc"),
                  ("a substitution", "a substitution"), ("not run as python3", "not run as python3 system/scripts/…"),
                  ("isn't a creaite script", "not a creaite script"), ("no rule covers", "a subcommand no rule covers"),
                  (" was refused", "another tool"))


def refusals(days=7) -> list:
    """[(shape, count)] for the commands ask creaite's guard refused in the last `days` days, in REFUSAL_SHAPES order, nonzero
    only. One refusal can count under several shapes (a pipe and a redirect)."""
    counts = {}
    for e in entries(now() - timedelta(days=days)):
        m = REFUSED.match(e["message"]) if e["area"] == "run" else None
        if not m:
            continue
        hit = [label for word, label in REFUSAL_SHAPES if word in m.group(1)] or ["other"]
        for label in hit:
            counts[label] = counts.get(label, 0) + 1
    order = [label for _, label in REFUSAL_SHAPES] + ["other"]
    return [(label, counts[label]) for label in order if counts.get(label)]


def refusals_line(days=7) -> str:
    """The counts in one line, such as "3 × a pipe, 1 × a redirect", or "none"."""
    found = refusals(days)
    return ", ".join(f"{n} × {label}" for label, n in found) if found else "none"
# ===== end BL-252 =====
