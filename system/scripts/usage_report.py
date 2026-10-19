"""Run usage report (#197), read only: per day and per kind, runs, tokens, start load, cost.

    system/scripts/run usage_report.py --days 7
    system/scripts/run usage_report.py --json          the Usage tab's figures (#238), as page() gives them

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


# ===== #238 the Usage tab (Activity › Usage): page() gives the figures, counts only, from the lines above. =====
PAGE_DAYS = 14


def _tokens(r) -> int:
    """All the tokens of one run."""
    return sum(int(r.get(k) or 0) for k in ("input", "output", "cache_read", "cache_create"))


def _median(values):
    """The median of the non-zero values, rounded; None when there are none (a stopped run loads nothing)."""
    v = [x for x in values if x]
    return round(statistics.median(v)) if v else None


def _in(rows, first, last) -> list:
    """The rows whose day is in [first, last] (dates)."""
    a, b = first.isoformat(), last.isoformat()
    return [r for r in rows if a <= str(r["at"])[:10] <= b]


def _pct(now, before):
    """The change in per cent, rounded; None when there is nothing to compare with."""
    return round((now - before) * 100 / before) if before else None


def _week(rows) -> dict:
    """One week's card figures."""
    cost = round(sum(float(r.get("cost_usd") or 0) for r in rows), 4)
    return {"cost_usd": cost, "runs": len(rows), "start_median": _median([r.get("start_tokens", 0) for r in rows]),
            "avg_cost_usd": round(cost / len(rows), 4) if rows else 0.0}


def cards(rows, today) -> dict:
    """This week (the last 7 days) and the 7 before, with the change: per cent for cost, runs and the average run, tokens for
    the start load."""
    now = _week(_in(rows, today - timedelta(days=6), today))
    before = _week(_in(rows, today - timedelta(days=13), today - timedelta(days=7)))
    start = None if now["start_median"] is None or before["start_median"] is None else now["start_median"] - before["start_median"]
    return {"week": now, "previous": before, "change": {"cost_pct": _pct(now["cost_usd"], before["cost_usd"]),
                                                        "runs_pct": _pct(now["runs"], before["runs"]),
                                                        "start_tokens": start,
                                                        "avg_cost_pct": _pct(now["avg_cost_usd"], before["avg_cost_usd"])}}


def daily(rows, today, days=PAGE_DAYS) -> list:
    """One entry a day, oldest first: cost, runs and the median start load (None on a day with no runs)."""
    out = []
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        g = _in(rows, d, d)
        out.append({"day": d.isoformat(), "runs": len(g), "cost_usd": round(sum(float(r.get("cost_usd") or 0) for r in g), 4),
                    "start_median": _median([r.get("start_tokens", 0) for r in g])})
    return out


def kinds(rows) -> list:
    """Per kind of run: runs, average tokens, median start load, cost and share of the cost; the costliest first."""
    total = sum(float(r.get("cost_usd") or 0) for r in rows)
    groups = {}
    for r in rows:
        groups.setdefault(str(r.get("kind") or "ask"), []).append(r)
    out = []
    for k, g in groups.items():
        cost = sum(float(r.get("cost_usd") or 0) for r in g)
        out.append({"kind": k, "runs": len(g), "avg_tokens": round(sum(_tokens(r) for r in g) / len(g)),
                    "start_median": _median([r.get("start_tokens", 0) for r in g]), "cost_usd": round(cost, 4),
                    "share": round(cost / total, 4) if total else 0.0})
    out.sort(key=lambda x: (-x["cost_usd"], -x["runs"], x["kind"]))
    return out


def skills_page(all_rows, period_rows, today, skills_dir=None) -> list:
    """Per skill: runs and the cost of the runs that used it in the period, and the day it was last used (the whole file).
    A skill not used in the period is flagged never_in_period; days_since is None when it was never used at all."""
    cost = {}
    for r in period_rows:
        for name in r.get("skills") or []:
            cost[name] = cost.get(name, 0.0) + float(r.get("cost_usd") or 0)
    out = []
    for s in skills_table(all_rows, PAGE_DAYS, today, skills_dir):
        last = (today - timedelta(days=s["days_since"])).isoformat() if s["days_since"] is not None else None
        out.append({"skill": s["skill"], "runs": s["runs"], "cost_usd": round(cost.get(s["skill"], 0.0), 4), "last": last,
                    "days_since": s["days_since"], "never_in_period": s["runs"] == 0})
    out.sort(key=lambda x: (x["never_in_period"], -x["runs"], x["skill"]))
    return out


def page(rows=None, today=None, skills_dir=None) -> dict:
    """The Usage tab's figures over the last 14 days. Counts, dates and fixed words only: never a label, a model or any text."""
    every = load() if rows is None else rows
    today = today or _today()
    period = _in(every, today - timedelta(days=PAGE_DAYS - 1), today)
    return {"period": {"from": (today - timedelta(days=PAGE_DAYS - 1)).isoformat(), "to": today.isoformat(), "days": PAGE_DAYS},
            "empty": not every, "runs": len(period), "cards": cards(every, today), "daily": daily(every, today),
            "kinds": kinds(period), "skills": skills_page(every, period, today, skills_dir)}
# ===== end #238 =====


def main(argv=None) -> int:
    """Print the report."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--file")
    ap.add_argument("--json", action="store_true", help="the Usage tab's figures (#238)")
    a = ap.parse_args(argv)
    every = load(a.file)
    if a.json:
        print(json.dumps(page(every), indent=1))
        return 0
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
