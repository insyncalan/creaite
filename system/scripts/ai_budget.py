"""Weekly budget for creaite's own AI runs (#334): how much of this week's budget the runs have used, and what to do about it.

Pure code: no file is written, no clock but the one passed in (CREAITE_NOW fixes it in tests), nothing here raises. It reads the
counts the usage monitor already keeps (system/staging/run-usage.jsonl: dollars and token counts per run, never any text) and the
`ai_budget` block of settings.json. The live server's run engine asks `gate()` before it starts a typed request; the Usage tab and
the ask panel draw `status()`. The buttons in the dashboard (Review, Apply, Undo) are not runs and are never asked: only
the kinds in BLOCKABLE can be held,
and a confirmed request (the answer to a question the last run asked) is never held, so a change in flight is never cut off.

The week runs from Monday 00:00 to the next Monday 00:00, local time (the usage file's own times). Dates shown are DD-MM-YYYY.
"""
import json
import math
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

UNITS = ("dollars", "tokens")
AT_LIMIT = ("confirm", "stop")
WARN_AT = 0.8                       # a plain warning from 80% of the week (the issue's figure)
BLOCKABLE = ("ask",)                # runs a person starts by typing; a sweep, the alert check and drafts are never held (README)
DEFAULTS = {"enabled": True, "unit": "dollars", "weekly_dollars": 50, "weekly_tokens": 50000000, "at_limit": "confirm"}
LIMITS = {"weekly_dollars": (1, 10000), "weekly_tokens": (100000, 10 ** 10)}
MAX_COUNT = 10 ** 12


def _now() -> datetime:
    fixed = os.environ.get("CREAITE_NOW")
    if fixed:
        try:
            return datetime.strptime(fixed, "%Y-%m-%d %H:%M")
        except ValueError:          # a bad test clock falls back to the real time
            pass
    return datetime.now()


def _num(v) -> float:
    """A count or dollar figure: only a real int or float counts (not a flag, a text or None); it must be finite and is held between
    0 and MAX_COUNT. Anything else counts nothing (a corrupt line is not spend)."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return 0.0
    try:
        x = float(v)
    except (OverflowError, ValueError):
        return 0.0
    if not math.isfinite(x):
        return 0.0
    return min(max(x, 0.0), float(MAX_COUNT))


def settings(raw=None) -> dict:
    """The budget's settings with every value checked: a missing, hand-edited or out-of-range value falls back to its default
    (an amount is held between its limits). `raw` is the settings.json block; None reads it."""
    if raw is None:
        try:
            got = paths.load_settings().get("ai_budget")
        except (OSError, ValueError, AttributeError):       # a missing or broken settings file: the defaults
            got = None
        raw = got if isinstance(got, dict) else {}
    out = dict(DEFAULTS)
    if isinstance(raw.get("enabled"), bool):
        out["enabled"] = raw["enabled"]
    if raw.get("unit") in UNITS:
        out["unit"] = raw["unit"]
    if raw.get("at_limit") in AT_LIMIT:
        out["at_limit"] = raw["at_limit"]
    for k, (lo, hi) in LIMITS.items():
        v = raw.get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v > 0:      # zero or below: the default
            out[k] = min(max(v, lo), hi)
    return out


def week_of(now=None) -> tuple:
    """(first day, last day, the Monday it starts again) of the week `now` falls in; the week starts on Monday."""
    d = (now or _now()).date()
    first = d - timedelta(days=d.weekday())
    return first, first + timedelta(days=6), first + timedelta(days=7)


def _row_day(row):
    """A usage line's day, or None when its `at` isn't the log's timestamp text (YYYY-MM-DDTHH:MM:SS, as usage_log writes it)."""
    try:
        at = row.get("at")
        if not isinstance(at, str):
            return None
        return date.fromisoformat(at[:10])
    except (AttributeError, ValueError):
        return None


def used(rows, now=None, unit="dollars") -> float:
    """This week's use: the dollars (cost_usd), or the tokens (input, output and both cache counts), of the lines that fall in the
    week. A line without a real date, or from another week, counts nothing; so does a number that isn't one."""
    first, _, nxt = week_of(now)
    total = 0.0
    for r in rows or ():
        day = _row_day(r)
        if day is None or not first <= day < nxt:
            continue
        if unit == "tokens":
            total += sum(_num(r.get(k)) for k in ("input", "output", "cache_read", "cache_create"))
        else:
            total += _num(r.get("cost_usd"))
    return total


def _show(unit, v) -> str:
    return f"${v:,.2f}" if unit == "dollars" else f"{round(v):,} tokens"


def _dmy(d) -> str:
    return d.strftime("%d-%m-%Y")


def status(rows=None, cfg=None, now=None) -> dict:
    """The week's figures, counts and dates only: {enabled, unit, limit, used, percent, state, at_limit, week_start, week_end,
    resets, line, counted}. state is off, ok, warn (from 80%) or over (from 100%). `rows` None reads the usage file; a missing or
    unreadable file counts as nothing used (counted False), so a fault never holds a run. Dates are YYYY-MM-DD; `line` is the
    words for a person."""
    cfg = cfg or settings()
    now = now or _now()
    first, last, nxt = week_of(now)
    unit = cfg["unit"]
    limit = cfg["weekly_tokens"] if unit == "tokens" else cfg["weekly_dollars"]
    counted = True
    if rows is None:
        try:
            import usage_report
            rows = usage_report.load()
        except Exception:           # nothing is held because the file could not be read
            rows, counted = [], False
    spent = used(rows, now, unit)
    pct = round(spent / limit * 100, 1) if limit else 0.0
    state = "off" if not cfg["enabled"] else "over" if spent >= limit else "warn" if spent >= limit * WARN_AT else "ok"
    line = f"{_show(unit, spent)} of {_show(unit, limit)} used this week; the week ends on {_dmy(last)}."
    return {"enabled": cfg["enabled"], "unit": unit, "limit": limit, "used": round(spent, 4), "percent": pct, "state": state,
            "at_limit": cfg["at_limit"], "week_start": first.isoformat(), "week_end": last.isoformat(), "resets": nxt.isoformat(),
            "counted": counted, "line": line}


def warning(st) -> str:
    """The plain line to show beside the ask box from 80%, or "" below it (or when the budget is off)."""
    if st.get("state") == "warn":
        return f"Heads-up: {st['line']} At the limit creaite will {'ask first' if st['at_limit'] == 'confirm' else 'stop new requests'}."
    if st.get("state") == "over":
        return f"Over this week's AI budget: {st['line']}"
    return ""


def gate(kind, st=None, confirmed=None, over_budget=False):
    """Whether a run of `kind` may start now. None: go ahead. Otherwise {"ok": False, "budget": {...}, "message": words}, where
    budget.can_continue says whether Alan may start it anyway (confirm mode: he just did, with over_budget True, which is his own
    click on the page). Only a run in BLOCKABLE is ever held, never a confirmed request, and never when the budget is off or its
    count could not be read."""
    if kind not in BLOCKABLE or confirmed:
        return None
    try:
        st = st if st is not None else status()
        if st["state"] != "over" or not st["counted"]:
            return None
        can = st["at_limit"] == "confirm"
        if can and over_budget is True:
            return None
        resets = date.fromisoformat(st["resets"])
    except Exception:               # a fault in the count never holds a run
        return None
    base = (f"This week's AI budget is used up ({st['line'].split(' used')[0]}). It starts again on Monday {_dmy(resets)}. "
            "The buttons in the dashboard still work.")
    msg = base + (" Run this request anyway?" if can else " Raise the budget in Settings, Advanced, creaite and ask creaite, to run more.")
    brief = {k: st[k] for k in ("unit", "limit", "used", "percent", "state", "at_limit", "resets")}
    return {"ok": False, "budget": dict(brief, can_continue=can), "message": msg}


def main(argv=None) -> int:
    """Print this week's figures as JSON (counts and dates only)."""
    print(json.dumps(status(), separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
