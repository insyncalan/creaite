"""What every Claude run loads before it starts (#238): the size of the always-loaded files, measured once a day.

Plain code, like usage_log.py. The live server's daily job calls daily_line() (one line in backup_daily_job, after the backup
steps: never from an ask creaite run, never in the development repository); the page only reads. Each day appends one line per
group to system/staging/context-size.jsonl:

    {"date": "YYYY-MM-DD", "file": "<group>", "bytes": int, "tokens": int, "files": int}

`file` is one of GROUPS, a fixed word, never a path or a folder name (a project folder may carry a client's name). tokens is
an estimate, bytes / 4. Counts only: no text of any file is ever kept; the skills' front matter is read only to count it.
table() gives the page each group now, with its change over 30 days. CREAITE_NOW fixes today in tests.
"""
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

GROUPS = ("rules", "claude_md", "memory", "skills")
FILE_NAME = "context-size.jsonl"
WINDOW = 30
PORTFOLIO_FILES = ("PORTFOLIO.md", "project-register.md", "people-register.md")


def _today() -> date:
    """Today, or CREAITE_NOW's day in tests."""
    fixed = os.environ.get("CREAITE_NOW")
    if fixed:
        try:
            return datetime.strptime(fixed, "%Y-%m-%d %H:%M").date()
        except ValueError:      # a bad test clock falls back to the real day
            pass
    return datetime.now().date()


def tokens(n: int) -> int:
    """The estimate the page shows: bytes / 4."""
    return round(max(0, int(n)) / 4)


def _memory_files(root):
    """Every project's CLAUDE.md and the portfolio's memory and registers (through paths, or the default layout under root)."""
    if root is None:
        try:
            folders = paths.project_folders()
        except (OSError, LookupError, ValueError):      # no projects folder: nothing to count
            folders = []
    else:
        base = Path(root) / "projects"
        folders = [(d.name.split(" ", 1)[0], d) for d in sorted(base.iterdir()) if d.is_dir() and d.name != "_Archive"] \
            if base.is_dir() else []
    out = []
    for code, d in folders:
        names = PORTFOLIO_FILES if code == "_portfolio" or d.name == "_portfolio" else ("CLAUDE.md",)
        out += [Path(d) / n for n in names]
    return out


def front_matter_bytes(f: Path) -> int:
    """The bytes of a SKILL.md's front matter (its name and description, what Claude Code loads); 0 when it has none."""
    try:
        text = f.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return 0
    if not text.startswith("---"):
        return 0
    end = text.find("\n---", 3)
    return len(text[:end + 4].encode("utf-8")) if end > 0 else 0


def _size(f: Path) -> int:
    """A file's size, 0 when it isn't there."""
    try:
        return f.stat().st_size if f.is_file() else 0
    except OSError:
        return 0


def measure(root=None) -> list:
    """[{file, bytes, tokens, files}] for each group, now. Reads sizes only (and the skills' front matter to count it)."""
    base = Path(root) if root is not None else paths.ROOT
    skills = base / ".claude" / "skills"
    skill_files = sorted(skills.glob("*/SKILL.md")) if skills.is_dir() else []
    sizes = {"rules": [_size(base / "system" / "creaite-rules.md")],
             "claude_md": [_size(base / "CLAUDE.md")],
             "memory": [s for s in (_size(f) for f in _memory_files(root)) if s],
             "skills": [s for s in (front_matter_bytes(f) for f in skill_files) if s]}
    return [{"file": g, "bytes": sum(sizes[g]), "tokens": tokens(sum(sizes[g])), "files": len([s for s in sizes[g] if s])}
            for g in GROUPS]


def _file(root):
    """The record's path."""
    return (Path(root) / "system" / "staging" / FILE_NAME) if root is not None else paths.STAGING / FILE_NAME


def load(root=None, path=None) -> list:
    """The record's lines (only known groups and whole numbers); a broken line is skipped."""
    f = Path(path) if path else _file(root)
    rows = []
    try:
        lines = f.read_text(encoding="utf-8").splitlines() if f.is_file() else []
    except OSError:
        lines = []
    for ln in lines:
        try:
            r = json.loads(ln)
        except ValueError:      # a broken line is skipped
            continue
        if isinstance(r, dict) and r.get("file") in GROUPS and isinstance(r.get("bytes"), int) and isinstance(r.get("date"), str):
            rows.append(r)
    return rows


def record_daily(root=None, today=None):
    """Append today's lines once a day. Returns them, or None when nothing was written (development repository, already
    measured today, or any failure). Never raises."""
    try:
        base = Path(root) if root is not None else paths.ROOT
        if (base / ".creaite-dev").exists():
            return None
        day = (today or _today()).isoformat()
        if any(r["date"] == day for r in load(root)):
            return None
        lines = [{"date": day, "file": m["file"], "bytes": m["bytes"], "tokens": m["tokens"], "files": m["files"]}
                 for m in measure(root)]
        f = _file(root)
        f.parent.mkdir(parents=True, exist_ok=True)
        with open(f, "a", encoding="utf-8") as fh:
            fh.write("".join(json.dumps(x, separators=(",", ":")) + "\n" for x in lines))
        return lines
    except Exception:       # the monitor must never break the daily job
        return None


def daily_line(root=None):
    """For the live server's daily job: a short line when today's sizes were recorded, else None."""
    lines = record_daily(root)
    if not lines:
        return None
    return "context size recorded: about " + format(sum(x["tokens"] for x in lines), ",") + " tokens"


def change(series, now_bytes, today, window=WINDOW):
    """(change in bytes over the window, the date it last changed) for one group's records [(date, bytes)], oldest first.
    The baseline is the last record on or before the window's start, else the oldest one; (None, None) with no record."""
    if not series:
        return None, None
    start = (today - timedelta(days=window)).isoformat()
    before = [s for s in series if s[0] <= start]
    base = before[-1] if before else series[0]
    seq = [s for s in series if s[0] >= base[0]] + [(today.isoformat(), now_bytes)]
    changed_on = None
    for prev, cur in zip(seq, seq[1:]):
        if cur[1] != prev[1]:
            changed_on = cur[0]
    return now_bytes - base[1], changed_on


def table(root=None, today=None, path=None) -> list:
    """The page's rows: each group now, with its change over 30 days from the record. Read only."""
    today = today or _today()
    hist = sorted(load(root, path), key=lambda r: r["date"])
    out = []
    for m in measure(root):
        series = [(r["date"], r["bytes"]) for r in hist if r["file"] == m["file"]]
        delta, on = change(series, m["bytes"], today)
        out.append({**m, "change_bytes": delta, "changed_on": on})
    return out


if __name__ == "__main__":
    print(json.dumps(table(), indent=1))
