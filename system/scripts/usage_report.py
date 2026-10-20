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
    """The lines of the file; a broken line (or one with a bad byte) is skipped. Only the file's last 8 MB are read, and a file that
    isn't a regular file reads as empty (usage_log.read_lines)."""
    import usage_log
    f = Path(path) if path else paths.RUN_USAGE
    rows = []
    for ln in usage_log.read_lines(f):
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
            "days_since": max(0, (today - datetime.strptime(s["last"], "%Y-%m-%d").date()).days) if s["last"] else None}
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


# ===== #238 (v2.5.1): --json, the figures the Activity › Usage tab shows (and GET /api/usage serves) =====
# Counts only. A line's kind is one of usage_log.KINDS or "other"; a skill is a known name or "other" (usage_log.clean_skills); the
# label, model and any other field a line holds are never read. Tokens loaded at start are estimates the run reported; the context
# rows (usage_log.read) estimate bytes / 4. A run with no start load (a stopped one) is left out of the start-load medians.
JSON_DAYS = 14
WEEK = 7


def _median(values):
    return round(statistics.median(values)) if values else None


def _change_pct(now, before):
    return round((now - before) / before * 100) if before else None


def _cost_of(group) -> float:
    """The dollars of a group of lines; a line without a number counts nothing."""
    total = 0.0
    for r in group:
        try:
            total += max(0.0, float(r["cost_usd"] or 0))
        except (TypeError, ValueError):
            continue            # a cost that isn't a number is not counted
    return round(total, 4)


def _starts(group) -> list:
    """The start loads of a group of lines, leaving out a run that has none (a stopped one)."""
    return [r["start_tokens"] for r in group if r["start_tokens"]]


def _in_days(rows, today, first_back, last_back) -> list:
    """The lines from `first_back` to `last_back` days before today, both included."""
    a, b = (today - timedelta(days=first_back)).isoformat(), (today - timedelta(days=last_back)).isoformat()
    return [r for r in rows if a <= str(r["at"])[:10] <= b]


def _cards(rows, today) -> dict:
    """The four cards: the last seven days against the seven before."""
    def figs(g):
        """One week's cost, runs, median start load and average run cost."""
        cost = _cost_of(g)
        return {"cost": cost, "runs": len(g), "start": _median(_starts(g)), "avg_cost": round(cost / len(g), 4) if g else 0}
    n, b = figs(_in_days(rows, today, WEEK - 1, 0)), figs(_in_days(rows, today, 2 * WEEK - 1, WEEK))
    out = {k: {"now": n[k], "before": b[k], "change_pct": _change_pct(n[k], b[k])} for k in ("cost", "runs", "avg_cost")}
    out["start"] = {"now": n["start"], "before": b["start"],
                    "change": n["start"] - b["start"] if n["start"] is not None and b["start"] is not None else None}
    return out


def _valid_at(at) -> bool:
    """Whether a line's `at` starts with a real date in ASCII digits (YYYY-MM-DD, then anything or nothing)."""
    import usage_log
    day = str(at)[:10]
    return usage_log._DAY.fullmatch(day) is not None and usage_log._real_day(day)


def _clean_rows(rows, skills_dir) -> list:
    """The lines reduced to what the figures use: a real day, a kind from the fixed list (else "other"), bounded numbers (an odd one
    counts as 0) and known skill names. A line without a real date is dropped."""
    import usage_log
    known = usage_log.shipped_skills(skills_dir)           # once: the folder is not listed again for every line
    return [{"at": r["at"], "kind": r.get("kind") if r.get("kind") in usage_log.KINDS else "other",
             "cost_usd": usage_log._money(r.get("cost_usd", 0)), "start_tokens": usage_log._int(r.get("start_tokens", 0)),
             "tokens": sum(usage_log._int(r.get(k)) for k in ("input", "output", "cache_read", "cache_create")),
             "skills": usage_log.clean_skills([x for x in r.get("skills") or [] if isinstance(x, str)], known=known)}
            for r in rows if _valid_at(r["at"])]


def _by_day(window, today, days) -> list:
    """One entry a day, oldest first, empty days kept."""
    out = []
    for i in range(days):
        day = (today - timedelta(days=days - 1 - i)).isoformat()
        g = [r for r in window if str(r["at"])[:10] == day]
        out.append({"day": day, "runs": len(g), "cost_usd": _cost_of(g), "start_median": _median(_starts(g))})
    return out


def _by_kind(window) -> list:
    """One entry a kind, the dearest first, with its share of the cost."""
    total = _cost_of(window)
    out = []
    for kind in sorted({r["kind"] for r in window}):
        g = [r for r in window if r["kind"] == kind]
        out.append({"kind": kind, "runs": len(g), "avg_tokens": round(sum(r["tokens"] for r in g) / len(g)),
                    "start_median": _median(_starts(g)), "cost_usd": _cost_of(g),
                    "share_pct": round(_cost_of(g) / total * 100) if total else 0})
    out.sort(key=lambda k: (-k["cost_usd"], k["kind"]))
    return out


def _by_skill(clean, window, today, days, skills_dir) -> list:
    """Each skill's runs, cost and last use (cx-* skills never seen are listed); "other" is left out."""
    out = []
    for t in skills_table(clean, days, today, skills_dir):
        if t["skill"] != "other":
            out.append({"skill": t["skill"], "runs": t["runs"], "cost_usd": _cost_of([r for r in window if t["skill"] in r["skills"]]),
                        "days_since": t["days_since"],
                        "last": (today - timedelta(days=t["days_since"])).isoformat() if t["days_since"] is not None else None})
    return out


def report(rows, context_rows=None, days=JSON_DAYS, today=None, skills_dir=None) -> dict:
    """The Usage tab's figures as one dict: cards, by_day (oldest first, empty days kept), by_kind (by cost), skills and context."""
    import usage_log
    today = today or _today()
    clean = _clean_rows(rows, skills_dir)
    window = _in_days(clean, today, days - 1, 0)
    return {"as_of": today.isoformat(), "days": days, "empty": not window,
            "estimate": "tokens at start are what the run reported; context tokens are bytes / 4",
            "cards": _cards(clean, today), "by_day": _by_day(window, today, days), "by_kind": _by_kind(window),
            "skills": _by_skill(clean, window, today, days, skills_dir),
            "context": usage_log.changes(context_rows or [], today=today.isoformat())}


def json_report(days=JSON_DAYS, usage_file=None, context_file=None, skills_dir=None, reviews_root=None) -> dict:
    """report() over the two files in the vault's staging folder (or the paths given); a missing or broken file is empty.
    v2.5.3: with Alan's own review notes (usage_reviews.load: date, saw, decided only) and whether this process can save one."""
    import usage_log
    import usage_reviews
    out = report(load(usage_file), usage_log.read(context_file), days=days, skills_dir=skills_dir)
    out.update(reviews=usage_reviews.load(reviews_root), reviews_save=usage_reviews.REGISTERED)
    return out
# ===== end #238 =====


def main(argv=None) -> int:
    """Print the report."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int)
    ap.add_argument("--file")
    ap.add_argument("--json", action="store_true", help="print the Usage tab's figures as JSON (counts only; 14 days unless --days)")
    ap.add_argument("--context-file", help="with --json: the context-size record (default system/staging/context-size.jsonl)")
    a = ap.parse_args(argv)
    if a.json:
        print(json.dumps(json_report(a.days or JSON_DAYS, a.file, a.context_file), separators=(",", ":")))
        return 0
    a.days = a.days or 7
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
