"""creaite slip range (BL-184): a likely date range for an open milestone, from how your own milestones have slipped. Read only.

Run: python3 system/scripts/forecast.py range [CODE] [--json]

Plain code works everything out from the tracker's history (change_log, through tracker.milestone_events, which skips undone
applies); the model computes nothing. Internal only: no client report, client-safe one-pager or client view reads it.

- A milestone's slips are the times its forecast moved later (forecast_date updates). They are measured against the first agreed
  date, so a rebaseline (a change to the agreed date) is not a slip in itself.
- A milestone is closed when its status changed to Done; it was finished on its achieved date (actual_date), else that day.
- For an open milestone with k slips so far, the reference class is every closed milestone with at least k slips. For each, the
  remaining slip is how far it finished after its forecast as it stood after its k-th slip (after none: its first forecast).
  The range is today's forecast plus the 50th and the 80th percentile of those remaining slips.
- The range is shown only when at least MIN_CLASS (8) closed milestones are in the class; otherwise "No range yet: n of 8 closed
  milestones with history". While fewer than THIN_PROJECTS (5) projects have closed milestones, it is labelled thin evidence.
"""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402,F401  (locations come from paths.py, as in every script)
import tracker  # noqa: E402

MIN_CLASS = 8
THIN_PROJECTS = 5


def percentile(values, p):
    """Linear interpolation between the closest ranks (p from 0 to 100)."""
    v = sorted(values)
    if not v:
        return None
    i = (len(v) - 1) * p / 100
    lo, hi = int(i), min(int(i) + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (i - lo)


def history(con):
    """{id: {project, status, first_forecast, slips: [forecast after each slip], closed: date or None, forecast}} from change_log."""
    rows = {r["id"]: dict(r) for r in con.execute("SELECT * FROM milestones")}
    out = {}
    for mid, events in tracker.milestone_events(con, list(rows)).items():
        m = rows.get(mid)
        if not m:
            continue
        first, slips, done = None, [], None
        for e in events:
            if e["field"] == "forecast_date" and e["new"]:
                if first is None and (e["op"] == "insert" or not e["old"]):
                    first = e["new"]
                elif e["old"] and e["new"] > e["old"]:
                    slips.append(e["new"])
                if first is None:
                    first = e["old"] or e["new"]
            elif e["field"] == "status" and e["new"] == "Done":
                done = e["at"][:10]
            elif e["field"] == "status" and e["old"] == "Done":
                done = None
        if first is None:
            first = m["forecast_date"] or m["baseline_date"]
        closed = None
        if m["status"] == "Done":
            closed = m.get("actual_date") or done
        out[mid] = {"project": m["project"], "status": m["status"], "first": first, "slips": slips, "closed": closed,
                    "forecast": m["forecast_date"] or m["baseline_date"]}
    return out


def days(a, b):
    """Days from date `b` to date `a` (both YYYY-MM-DD); negative when `a` is earlier."""
    return (date.fromisoformat(a) - date.fromisoformat(b)).days


def ranges(con, ids=None):
    """{id: {...}} for open milestones (Planned, with a forecast): ok, lo, hi (YYYY-MM-DD), n (closed milestones in the class),
    need, k (slips so far), thin, text (as the page shows it)."""
    h = history(con)
    closed = {i: x for i, x in h.items() if x["closed"] and x["first"]}
    projects = {x["project"] for x in closed.values()}
    thin = len(projects) < THIN_PROJECTS
    out = {}
    for mid, x in h.items():
        if ids is not None and mid not in ids:
            continue
        if x["status"] != "Planned" or not x["forecast"]:
            continue
        k = len(x["slips"])
        remaining = []
        for c in closed.values():
            if len(c["slips"]) >= k:
                base = c["slips"][k - 1] if k else c["first"]
                remaining.append(days(c["closed"], base))
        n = len(remaining)
        r = {"k": k, "n": n, "need": MIN_CLASS, "thin": thin, "ok": n >= MIN_CLASS, "lo": None, "hi": None}
        if r["ok"]:
            fc = date.fromisoformat(x["forecast"])
            r["lo"] = (fc + timedelta(days=round(percentile(remaining, 50)))).isoformat()
            r["hi"] = (fc + timedelta(days=round(percentile(remaining, 80)))).isoformat()
            r["med"], r["p80"] = round(percentile(remaining, 50)), round(percentile(remaining, 80))      # BL-226 (sprint-drafts-fields)
            r["explain"] = explain(r)
            r["text"] = f"Likely {tracker.shown(r['lo'])} to {tracker.shown(r['hi'])}" + (
                f" (thin evidence: {n} closed milestone{'s' if n != 1 else ''} with at least {k} slip{'s' if k != 1 else ''}, "
                f"from {len(projects)} project{'s' if len(projects) != 1 else ''})" if thin else "")
        else:
            r["text"] = f"No range yet: {n} of {MIN_CLASS} closed milestones with history"
        out[mid] = r
    return out


# ===== BL-226 (sprint-drafts-fields) ===== the slip range in one sentence, worked out by a template from the same numbers (no model):
# "Based on how 8 closed milestones slipped after 1 slip, as this one has (median 9 days), likely 04-12-2026 to 18-12-2026."
def explain(r):
    """One sentence explaining a milestone's slip range `r`, or '' when there is no range."""
    if not r.get("ok"):
        return ""
    after = f" after {r['k']} slip{'s' if r['k'] != 1 else ''}, as this one has" if r["k"] else ""
    days_ = f"median {r['med']} day{'s' if abs(r['med']) != 1 else ''} late" if r["med"] > 0 else \
        f"median {abs(r['med'])} day{'s' if abs(r['med']) != 1 else ''} early" if r["med"] < 0 else "median on time"
    return (f"Based on how {r['n']} closed milestones finished{after} ({days_}), likely {tracker.shown(r['lo'])} to "
            f"{tracker.shown(r['hi'])}" + (" (thin evidence)" if r.get("thin") else "") + ".")
# ===== end BL-226 =====


def main(argv):
    """The range command: print the slip range for each open milestone (one project with CODE), or JSON with --json."""
    if not argv or argv[0] != "range":
        print(__doc__)
        return 2
    args = argv[1:]
    as_json = "--json" in args
    code = next((a for a in args if not a.startswith("--")), None)
    con = tracker.connect()
    got = ranges(con)
    if code:
        got = {i: r for i, r in got.items() if i.startswith(code + "-M-")}
    if as_json:
        print(json.dumps(got, indent=1))
    else:
        names = {r["id"]: r["name"] for r in con.execute("SELECT id, name FROM milestones")}
        for i, r in sorted(got.items()):
            print(f"{i} {names.get(i, '')}: {r['text']}")
        if not got:
            print("No open milestones with a forecast.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
