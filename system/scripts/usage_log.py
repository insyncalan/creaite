"""Run usage monitor (#197): one counts-only JSON line per finished Claude run, appended to system/staging/run-usage.jsonl.

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
    (skills: the names collected from the run; the line gets "skills": [...], empty when none)
A stopped or failed run passes result_event=None (or what it has) and still records. record() never raises.
"""
import json
import os
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


def skills_of(event) -> list:
    """Skill names called in one assistant event: content items {"type":"tool_use","name":"Skill","input":{"skill":"<name>"}}
    (shape confirmed on a real run, 17-10-2026). Names only, never the other arguments; deduped, in order; never raises."""
    out = []
    try:
        for c in (event.get("message") or event).get("content") or []:
            if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("name") == "Skill":
                name = (c.get("input") or {}).get("skill")
                if isinstance(name, str) and name.strip() and name.strip()[:60] not in out:
                    out.append(name.strip()[:60])
    except (AttributeError, TypeError):     # a malformed event has no skills
        return []
    return out


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
            "skills": list(dict.fromkeys(str(s)[:60] for s in (skills or []) if isinstance(s, str)))}


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
