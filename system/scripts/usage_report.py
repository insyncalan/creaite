"""Run usage report (#197), read only: per day and per kind, runs, tokens, start load, cost.

    system/scripts/run usage_report.py --days 7

Reads system/staging/run-usage.jsonl (written only by usage_log.py). CREAITE_NOW fixes today in tests.
"""
import argparse
import json
import os
import statistics
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402


def load(path=None) -> list:
    """The lines of the file; a broken line is skipped."""
    f = Path(path) if path else paths.RUN_USAGE
    rows = []
    if f.exists():
        for ln in f.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(ln)
                if isinstance(r, dict) and r.get("at"):
                    rows.append(r)
            except ValueError:      # a broken line is skipped
                continue
    return rows


def _today():
    """Today, or CREAITE_NOW's day in tests."""
    fixed = os.environ.get("CREAITE_NOW")
    if fixed:
        try:
            return datetime.strptime(fixed, "%Y-%m-%d %H:%M").date()
        except ValueError:      # a bad test clock falls back to the real day
            pass
    return datetime.now().date()


def summarise(rows, days=7, today=None) -> list:
    """One dict per (day, kind), newest day first."""
    today = today or _today()
    first = (today - timedelta(days=days - 1)).isoformat()
    groups = {}
    for r in rows:
        day = str(r["at"])[:10]
        if first <= day <= today.isoformat():
            groups.setdefault((day, r.get("kind", "")), []).append(r)
    out = []
    for (day, kind), g in groups.items():
        tokens = [r.get("input", 0) + r.get("output", 0) + r.get("cache_read", 0) + r.get("cache_create", 0) for r in g]
        inputs = sum(r.get("input", 0) + r.get("cache_read", 0) + r.get("cache_create", 0) for r in g)
        starts = [r.get("start_tokens", 0) for r in g]
        out.append({"day": day, "kind": kind, "runs": len(g), "tokens": sum(tokens), "avg_tokens": round(sum(tokens) / len(g)),
                    "start_min": min(starts), "start_median": round(statistics.median(starts)), "start_max": max(starts),
                    "cost_usd": round(sum(r.get("cost_usd", 0) for r in g), 4),
                    "start_share": round(sum(starts) / inputs, 2) if inputs else 0.0})
    out.sort(key=lambda s: s["kind"])
    out.sort(key=lambda s: s["day"], reverse=True)
    return out


def main(argv=None) -> int:
    """Print the report."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--file")
    a = ap.parse_args(argv)
    rows = summarise(load(a.file), a.days)
    if not rows:
        print("No runs recorded in that time.")
        return 0
    print(f"{'Day':<11}{'Kind':<10}{'Runs':>5}{'Tokens':>10}{'Avg':>9}{'Start min/med/max':>22}{'Start share':>12}{'Cost $':>9}")
    for s in rows:
        st = f"{s['start_min']}/{s['start_median']}/{s['start_max']}"
        print(f"{s['day']:<11}{s['kind']:<10}{s['runs']:>5}{s['tokens']:>10}{s['avg_tokens']:>9}{st:>22}"
              f"{s['start_share']:>11.0%}{s['cost_usd']:>9.4f}")
    n = sum(s["runs"] for s in rows)
    cost = sum(s["cost_usd"] for s in rows)
    med = statistics.median([s["start_median"] for s in rows for _ in range(s["runs"])])
    print(f"Total: {n} runs, ${cost:.2f}, start load about {round(med)} tokens a run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
