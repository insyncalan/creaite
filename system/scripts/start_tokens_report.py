"""Start tokens per run kind (#339 A0), read only, counts only.

    system/scripts/run start_tokens_report.py --days 7 [--file PATH] [--json]

Reads system/staging/run-usage.jsonl (usage_report.load) and reports, per run kind, how many runs there were (n) and the median
and 90th percentile of start_tokens (what a run loaded before it did anything). Where a line carries a `resumed` field (a run that
continued an earlier session) each kind is also split into resumed and fresh. A run with no start load (a stopped one) is left out.
Never any text: only kind, `resumed` and numbers are read. CREAITE_NOW fixes today in tests.
"""
import argparse
import json
import math
import statistics
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402,F401  (every script takes its locations from paths.py)
import usage_report  # noqa: E402

# The 2.6.3 baseline from #339 (measured on the build before the lighter runs), for comparison only. Tokens and dollars.
BASELINE_ASK_START_MIN = 366_000        # an ask creaite start on 2.6.3 was 366k to 503k tokens (red line 500k)
BASELINE_ASK_START_MAX = 503_000
BASELINE_SWEEP_FLOOR_TOKENS = 60_000    # a sweep typed in the panel cannot go below about 60k tokens ...
BASELINE_SWEEP_FLOOR_USD = 1.50         # ... and $1.50: also the #339 target for a typed sweep
TARGET_PLAIN_ASK_START = 150_000        # #339 target for a plain ask (red line 500k, with part B)
RED_LINE_START = 500_000


def percentile(values, pct) -> int:
    """The nearest-rank percentile of a list of numbers (0 for an empty list)."""
    if not values:
        return 0
    s = sorted(values)
    return int(s[max(1, math.ceil(pct / 100 * len(s))) - 1])


def _starts(group) -> list:
    """The start loads of a group, whole numbers above 0; anything else (stopped run, text, a negative) is left out."""
    out = []
    for r in group:
        v = r.get("start_tokens")
        if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0:
            out.append(int(v))
    return out


def _figures(group) -> dict:
    """n, median and p90 of a group's start loads."""
    s = _starts(group)
    return {"n": len(s), "median": round(statistics.median(s)) if s else None, "p90": percentile(s, 90) if s else None}


def window(rows, days, today=None) -> list:
    """The lines from the last `days` days (today included) with a real date."""
    today = today or usage_report._today()
    first, last = (today - timedelta(days=days - 1)).isoformat(), today.isoformat()
    return [r for r in rows if first <= str(r.get("at", ""))[:10] <= last]


def summarise(rows) -> list:
    """One dict per kind (and per `resumed` value where any line of that kind has the field), kinds in name order.
    {"kind", "resumed": None | True | False, "n", "median", "p90"}; resumed None is the kind as a whole."""
    out = []
    for kind in sorted({str(r.get("kind", "")) for r in rows}):
        g = [r for r in rows if str(r.get("kind", "")) == kind]
        out.append(dict(kind=kind, resumed=None, **_figures(g)))
        if any("resumed" in r for r in g):
            for flag in (True, False):
                part = [r for r in g if "resumed" in r and bool(r["resumed"]) is flag]
                if part:
                    out.append(dict(kind=kind, resumed=flag, **_figures(part)))
    return out


def report(rows, days=7, today=None) -> dict:
    """The whole report as a dict: the window, the figures and the 2.6.3 baseline."""
    w = window(rows, days, today)
    return {"days": days, "runs": len(w), "kinds": summarise(w),
            "baseline_2_6_3": {"ask_start_range": [BASELINE_ASK_START_MIN, BASELINE_ASK_START_MAX],
                               "sweep_floor_tokens": BASELINE_SWEEP_FLOOR_TOKENS, "sweep_floor_usd": BASELINE_SWEEP_FLOOR_USD}}


def table(rep) -> str:
    """A short text table of a report()."""
    lines = [f"Start tokens per run kind, last {rep['days']} days ({rep['runs']} runs)",
             f"{'Kind':<12}{'Resumed':<9}{'n':>5}{'Median':>10}{'p90':>10}"]
    for k in rep["kinds"]:
        label = "all" if k["resumed"] is None else ("yes" if k["resumed"] else "no")
        med = "-" if k["median"] is None else str(k["median"])
        p90 = "-" if k["p90"] is None else str(k["p90"])
        lines.append(f"{k['kind'] or '(none)':<12}{label:<9}{k['n']:>5}{med:>10}{p90:>10}")
    b = rep["baseline_2_6_3"]
    lines.append(f"2.6.3 baseline: ask starts {b['ask_start_range'][0]} to {b['ask_start_range'][1]}; "
                 f"sweep floor {b['sweep_floor_tokens']} tokens, ${b['sweep_floor_usd']:.2f}.")
    return "\n".join(lines)


def main(argv=None) -> int:
    """Print the report."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--file")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    rep = report(usage_report.load(a.file), max(1, a.days))
    print(json.dumps(rep, separators=(",", ":")) if a.json else table(rep))
    return 0


if __name__ == "__main__":
    sys.exit(main())
