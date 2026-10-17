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


def skill_names(skills_dir=None) -> list:
    """The cx-* skill folders in .claude/skills/ (read only)."""
    d = Path(skills_dir) if skills_dir else paths.ROOT / ".claude" / "skills"
    return sorted(p.name for p in d.iterdir() if p.is_dir() and p.name.startswith("cx-")) if d.is_dir() else []


def skills_table(all_rows, days=7, today=None, skills_dir=None) -> list:
    """One dict per skill: runs in the last `days` days, runs ever, and days since it last ran (the whole file, not --days).
    A cx-* skill never seen has runs 0 and days_since None ("never run"). Old lines without "skills" count as none."""
    today = today or _today()
    first = (today - timedelta(days=days - 1)).isoformat()
    seen = {}
    for r in all_rows:
        day = str(r["at"])[:10]
        for name in r.get("skills") or []:
            s = seen.setdefault(name, {"runs": 0, "ever": 0, "last": ""})
            s["ever"] += 1
            s["last"] = max(s["last"], day)
            if first <= day <= today.isoformat():
                s["runs"] += 1
    for name in skill_names(skills_dir):
        seen.setdefault(name, {"runs": 0, "ever": 0, "last": ""})
    out = [{"skill": n, "runs": s["runs"], "ever": s["ever"],
            "days_since": (today - datetime.strptime(s["last"], "%Y-%m-%d").date()).days if s["last"] else None}
           for n, s in seen.items()]
    out.sort(key=lambda s: (s["days_since"] is None,s["days_since"] or 0, s["skill"]))
    return out


def print_skills(all_rows, days) -> None:
    """The skills section: runs in --days, and days since last run over the whole file."""
    print(f"\nSkills (runs in the last {days} days; days since last run uses the whole file)")
    print(f"{'Skill':<28}{'Runs':>6}{'Ever':>6}{'Days since':>12}")
    for s in skills_table(all_rows, days):
        since = "never run" if s["days_since"] is None else str(s["days_since"])
        print(f"{s['skill']:<28}{s['runs']:>6}{s['ever']:>6}{since:>12}")


def main(argv=None) -> int:
    """Print the report."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--file")
    a = ap.parse_args(argv)
    every = load(a.file)
    rows = summarise(every, a.days)
    if not rows:
        print("No runs recorded in that time.")
        print_skills(every, a.days)
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
    print_skills(every, a.days)
    return 0


if __name__ == "__main__":
    sys.exit(main())
