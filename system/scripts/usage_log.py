"""Run usage monitor (#197): one counts-only JSON line per finished Claude run, appended to system/staging/run-usage.jsonl.

#238 (v2.5.1) adds the second record, system/staging/context-size.jsonl: what every run loads before it starts, measured once a day
by the live server's daily job (daily(); never an ask creaite run, never the page). One row per always-loaded group and day:
{"date", "file", "bytes", "tokens"}. `file` is one of four fixed words (rules, claude_md, memory, skills), never a path or a name;
tokens are an estimate, bytes / 4. See measure(), append(), read(), changes() and daily() at the foot of this file.

Plain code. The live server calls record() when a run ends (result handler and the VIP call). Nothing else writes the file.
Never the text of anything: no prompt, reply, name, path or subject. Never written in the development repository (.creaite-dev).

Field names, checked on a real `claude -p ... --output-format stream-json --verbose` run (17-10-2026). The final event has
type "result" and, besides `result` (the reply text, never read here):
    total_cost_usd            float   dollars for the run
    duration_ms               int     wall time of the run (duration_api_ms: time in the API)
    num_turns                 int
    is_error, subtype, terminal_reason, stop_reason
    usage.input_tokens, usage.output_tokens,
    usage.cache_read_input_tokens, usage.cache_creation_input_tokens      (all ints)
    modelUsage                { "<model id>": {inputTokens, outputTokens, cacheReadInputTokens, cacheCreationInputTokens, costUSD, ...} }
The `--output-format json` reply (the VIP check) is the same object. The model name is on the system init event (`model`);
when that event was not kept, the first key of modelUsage is used.

A line: {"at", "kind", "label", "model", "seconds", "turns", "input", "output", "cache_read", "cache_create", "cost_usd",
"start_tokens", "stopped"}. start_tokens is the first assistant event's input plus cache tokens (what the run loaded before doing
anything); take it with start_tokens_of(first assistant event).

Calls the guarded hooks make:
    usage_log.start_tokens_of(assistant_event)            -> int, on the run's first assistant event
    usage_log.model_of(init_event)                        -> str, on the system init event
    usage_log.skills_of(assistant_event)                  -> list[str], on EVERY assistant event; the hook unions them in order
    usage_log.record(kind, result_event_or_None, label="", model="", seconds=0.0, start_tokens=0, stopped=False, skills=None)
    (skills: the names collected from the run; the line gets "skills": [...], empty when none. Only known skill names are kept,
    anything else typed becomes "other"; at most 20 entries a line: record() cleans them again)
A stopped or failed run passes result_event=None (or what it has) and still records. record() never raises.
"""
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

KINDS = ("ask", "sweep", "generate", "prep", "check", "load", "draft", "vip")


def _int(v) -> int:
    try:
        return max(0, int(v))
    except (TypeError, ValueError):
        return 0


def _now() -> datetime:
    fixed = os.environ.get("CREAITE_NOW")           # "YYYY-MM-DD HH:MM" fixes the clock in tests
    if fixed:
        try:
            return datetime.strptime(fixed, "%Y-%m-%d %H:%M")
        except ValueError:      # a bad test clock falls back to the real time
            pass
    return datetime.now()


def start_tokens_of(event) -> int:
    """Input plus cache tokens on an assistant event (message.usage): what the run loaded before doing anything."""
    try:
        u = (event.get("message") or event).get("usage") or {}
    except AttributeError:
        return 0
    return _int(u.get("input_tokens")) + _int(u.get("cache_read_input_tokens")) + _int(u.get("cache_creation_input_tokens"))


def model_of(event) -> str:
    """The model id on the system init event."""
    try:
        return str(event.get("model") or "")[:80]
    except AttributeError:
        return ""


# A skill name is kept only when it is one creaite knows: a folder in .claude/skills/, a plugin skill of a fixed list, or
# "<plugin>:<one of those>". Anything else the model typed (a sentence, a path, a person) becomes the literal "other".
OTHER = "other"
MAX_SKILLS = 20                     # names per line, "other" included; the rest are counted as "other" once
PLUGIN_SKILLS = ("docx", "pdf", "pptx", "xlsx")     # the Office skills creaite's rules name (document-skills plugin)
_PART = r"[a-z0-9][a-z0-9-]{0,39}"


def shipped_skills(skills_dir=None) -> set:
    """Folder names in .claude/skills/ (read only); empty when the folder can't be read."""
    d = Path(skills_dir) if skills_dir else paths.ROOT / ".claude" / "skills"
    try:
        return {p.name for p in d.iterdir() if p.is_dir()}
    except OSError:
        return set()


def plain_skill(name, known=None) -> str:
    """One raw skill name -> itself when known, otherwise "other". Never raises."""
    if not isinstance(name, str):
        return OTHER
    name = name.strip()
    known = shipped_skills() if known is None else known
    if name in known or name in PLUGIN_SKILLS:
        return name
    plugin, sep, skill = name.partition(":")
    if sep and re.fullmatch(_PART, plugin) and (skill in known or skill in PLUGIN_SKILLS):
        return name
    return OTHER


def clean_skills(names, skills_dir=None, known=None) -> list:
    """Raw names -> known names (deduped, in order), unknown ones as one "other", at most MAX_SKILLS entries in all.
    `known` (the folder names, from shipped_skills) saves reading the folder again when many lines are cleaned (#238)."""
    known = shipped_skills(skills_dir) if known is None else known
    kept, other = [], False
    for n in names or []:
        p = plain_skill(n, known)
        if p == OTHER:
            other = True
        elif p not in kept:
            kept.append(p)
    if len(kept) > MAX_SKILLS - (1 if other else 0):
        other = True
        kept = kept[:MAX_SKILLS - 1]
    return kept + [OTHER] if other else kept


def skills_of(event, skills_dir=None) -> list:
    """Skill names called in one assistant event: content items {"type":"tool_use","name":"Skill","input":{"skill":"<name>"}}
    (shape confirmed on a real run, 17-10-2026; "name" is the fallback, as live_server.describe_tool reads it). Only known names
    (see clean_skills); what the model typed otherwise is never kept. Deduped, in order; never raises."""
    raw = []
    try:
        for c in (event.get("message") or event).get("content") or []:
            if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("name") == "Skill":
                inp = c.get("input") or {}
                name = inp.get("skill")
                if not (isinstance(name, str) and name.strip()):
                    name = inp.get("name")
                if isinstance(name, str) and name.strip():
                    raw.append(name)
    except (AttributeError, TypeError):     # a malformed event has no skills
        return []
    return clean_skills(raw, skills_dir)


def line_for(kind, result=None, label="", model="", seconds=0.0, start_tokens=0, stopped=False, at=None, skills=None) -> dict:
    """The counts-only line. Reads only numbers (and the model id) from the result event."""
    r = result if isinstance(result, dict) else {}
    u = r.get("usage") if isinstance(r.get("usage"), dict) else {}
    if not model:
        mu = r.get("modelUsage")
        model = next(iter(mu), "") if isinstance(mu, dict) else ""
    try:
        cost = round(max(0.0, float(r.get("total_cost_usd") or 0)), 6)
    except (TypeError, ValueError):
        cost = 0.0
    secs = seconds or (_int(r.get("duration_ms")) / 1000.0)
    return {"at": (at or _now()).strftime("%Y-%m-%dT%H:%M:%S"),
            "kind": kind if kind in KINDS else "ask",
            "label": str(label or "")[:40],
            "model": str(model or "")[:80],
            "seconds": round(float(secs or 0), 1),
            "turns": _int(r.get("num_turns")),
            "input": _int(u.get("input_tokens")),
            "output": _int(u.get("output_tokens")),
            "cache_read": _int(u.get("cache_read_input_tokens")),
            "cache_create": _int(u.get("cache_creation_input_tokens")),
            "cost_usd": cost,
            "start_tokens": _int(start_tokens),
            "stopped": bool(stopped),
            "skills": clean_skills(s for s in (skills or []) if isinstance(s, str))}


def record(kind, result=None, label="", model="", seconds=0.0, start_tokens=0, stopped=False, root=None, skills=None):
    """Append one line. Returns it, or None when nothing was written (development repository, or any failure)."""
    try:
        base = Path(root) if root else paths.ROOT
        if (base / ".creaite-dev").exists():
            return None
        line = line_for(kind, result, label, model, seconds, start_tokens, stopped, skills=skills)
        f = base / "system" / "staging" / "run-usage.jsonl" if root else paths.RUN_USAGE
        f.parent.mkdir(parents=True, exist_ok=True)
        with open(f, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(line, separators=(",", ":")) + "\n")
        return line
    except Exception:       # the monitor must never break a run
        return None


# ===== #238 (v2.5.1): what every run loads, measured once a day (system/staging/context-size.jsonl) =====
# Counts only: a row is {"date", "file", "bytes", "tokens"} and `file` is one of the four fixed words below. The content of a file
# is only counted, never read into a row; a project's name or a skill's name never reaches the record. Plain code, no clock but
# the one passed in (CREAITE_NOW in tests), nothing here raises into the live server.
CONTEXT_FILES = ("rules", "claude_md", "memory", "skills")       # the fixed words, in the order the page lists them
CONTEXT_KEYS = ("date", "file", "bytes", "tokens")
CONTEXT_DAYS = 30                                                 # the change shown beside each file
PORTFOLIO_FILES = ("PORTFOLIO.md", "project-register.md", "people-register.md")     # read every run (the rules' memory section)
_DAY = re.compile(r"\d{4}-\d{2}-\d{2}")


def estimate_tokens(n_bytes) -> int:
    """The token estimate for a size in bytes: bytes / 4, halves up. An estimate, not a count."""
    return (_int(n_bytes) + 2) // 4


def _size(path) -> int:
    try:
        return Path(path).stat().st_size
    except OSError:
        return 0


def _front_matter_size(path) -> int:
    """Bytes of a skill's front matter (its name and description, between the first two --- lines): what is loaded before the skill
    is called. 0 when the file can't be read or has none. The text is measured, never kept."""
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    if not text.startswith("---"):
        return 0
    end = text.find("\n---", 3)
    return len(text[:end + 4].encode("utf-8")) if end > 0 else 0


def _memory_files(vault: Path) -> list:
    """Each project's CLAUDE.md and the three portfolio files. The live vault goes through paths (a projects folder outside the vault,
    BL-85); any other root (a test's) is read from its own projects/ folder."""
    out = []
    if vault.resolve() == paths.ROOT.resolve():
        try:
            for _code, folder in paths.project_folders():
                out.append(Path(folder) / "CLAUDE.md")
            out += [paths.portfolio_dir() / n for n in PORTFOLIO_FILES]
            return out
        except Exception:       # a register that can't be read: fall through to the plain layout
            out = []
    base = vault / "projects"
    try:
        out = [d / "CLAUDE.md" for d in sorted(base.iterdir()) if d.is_dir() and not d.name.startswith("_")]
    except OSError:
        pass
    return out + [base / "_portfolio" / n for n in PORTFOLIO_FILES]


def measure(vault=None, today=None) -> list:
    """The four rows for today: rules (system/creaite-rules.md), claude_md (the root CLAUDE.md), memory (every project's CLAUDE.md
    and the portfolio's PORTFOLIO.md, project-register.md and people-register.md) and skills (the front matter of each skill)."""
    vault = Path(vault) if vault else paths.ROOT
    day = str(today or _now().strftime("%Y-%m-%d"))
    skills = vault / ".claude" / "skills"
    try:
        skill_files = sorted(skills.glob("*/SKILL.md"))
    except OSError:
        skill_files = []
    sizes = {"rules": _size(vault / "system" / "creaite-rules.md"),
             "claude_md": _size(vault / "CLAUDE.md"),
             "memory": sum(_size(f) for f in _memory_files(vault)),
             "skills": sum(_front_matter_size(f) for f in skill_files)}
    return [{"date": day, "file": f, "bytes": sizes[f], "tokens": estimate_tokens(sizes[f])} for f in CONTEXT_FILES]


def _clean_row(r):
    """One row with only the four keys and valid values, or None. Anything else a line held is dropped here, so text can't pass through."""
    if not isinstance(r, dict) or r.get("file") not in CONTEXT_FILES:
        return None
    day = r.get("date")
    b, t = r.get("bytes"), r.get("tokens")
    if not (isinstance(day, str) and _DAY.fullmatch(day)):
        return None
    if not all(isinstance(x, int) and not isinstance(x, bool) and x >= 0 for x in (b, t)):
        return None
    return {"date": day, "file": r["file"], "bytes": b, "tokens": t}


def read(path=None) -> list:
    """The rows of the file, cleaned (see _clean_row). A missing file is empty; a line that isn't JSON, or isn't a valid row, is skipped."""
    f = Path(path) if path else paths.CONTEXT_SIZE
    rows = []
    try:
        lines = f.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return rows
    for ln in lines:
        try:
            row = _clean_row(json.loads(ln))
        except ValueError:
            continue
        if row:
            rows.append(row)
    return rows


def append(rows, root=None) -> int:
    """Append the rows not already recorded for their day and file; returns how many were written. Nothing is written in the
    development repository (.creaite-dev) or on any failure. Rows are cleaned first: only the four keys, only the fixed words."""
    try:
        base = Path(root) if root else paths.ROOT
        if (base / ".creaite-dev").exists():
            return 0
        f = base / "system" / "staging" / "context-size.jsonl" if root else paths.CONTEXT_SIZE
        have = {(r["date"], r["file"]) for r in read(f)}
        new = []
        for r in rows or []:
            c = _clean_row(r)
            if c and (c["date"], c["file"]) not in have:
                have.add((c["date"], c["file"]))
                new.append(c)
        if not new:
            return 0
        f.parent.mkdir(parents=True, exist_ok=True)
        with open(f, "a", encoding="utf-8") as fh:
            fh.write("".join(json.dumps(c, separators=(",", ":")) + "\n" for c in new))
        return len(new)
    except Exception:       # the monitor must never break the daily job
        return 0


def daily(root=None, today=None) -> list:
    """The live server's daily job: measure now and append, once a day. Returns the rows written (empty when today's are there already,
    in the development repository, not a vault, or on any failure). Never raises."""
    try:
        base = Path(root) if root else paths.ROOT
        if not ((base / "system" / "creaite-rules.md").exists() or (base / "CLAUDE.md").exists()):
            return []           # not a vault (a folder that has gone): four zeros would read as a trim
        rows = measure(base, today)
        return rows if append(rows, root=root) else []
    except Exception:
        return []


def changes(rows, today=None, days=CONTEXT_DAYS) -> list:
    """For each file with a row: its latest figures and the change over `days`. The baseline is the latest row on or before
    `days` days ago, else the oldest row inside the window; with no earlier row the change and `since` are None."""
    from datetime import date, timedelta
    t = str(today or _now().strftime("%Y-%m-%d"))
    cut = (date.fromisoformat(t) - timedelta(days=days)).isoformat()
    out = []
    for f in CONTEXT_FILES:
        mine = sorted((r for r in rows or [] if r.get("file") == f), key=lambda r: r["date"])
        mine = [r for r in mine if r["date"] <= t]
        if not mine:
            continue
        now, earlier = mine[-1], mine[:-1]
        old = [r for r in earlier if r["date"] <= cut]
        base = old[-1] if old else (earlier[0] if earlier else None)
        out.append({"file": f, "date": now["date"], "bytes": now["bytes"], "tokens": now["tokens"],
                    "since": base["date"] if base else None,
                    "change_bytes": now["bytes"] - base["bytes"] if base else None,
                    "change_tokens": now["tokens"] - base["tokens"] if base else None})
    return out
# ===== end #238 =====
