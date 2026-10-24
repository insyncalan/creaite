"""Before and after start tokens (#338 N2), read only, counts only.

    python3 dev/tools/compare_start_tokens.py BEFORE.jsonl AFTER.jsonl
    python3 dev/tools/compare_start_tokens.py --file run-usage.jsonl --before 2026-10-01:2026-10-07 --after 2026-10-15:2026-10-21

Prints, per run kind, n, median and p90 start tokens for each window and the % change. A kind with fewer than MIN_N runs in either
window is marked "low n": read its change as a hint, not a result. Never any text: only kind and start_tokens are read.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
import start_tokens_report as st  # noqa: E402

MIN_N = 5


def read(path) -> list:
    """The lines of a jsonl file; a broken line is skipped."""
    rows = []
    for ln in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            r = json.loads(ln)
        except ValueError:      # a broken line is skipped
            continue
        if isinstance(r, dict):
            rows.append(r)
    return rows


def between(rows, first, last) -> list:
    """The lines whose day (YYYY-MM-DD) is from `first` to `last`, both included."""
    return [r for r in rows if first <= str(r.get("at", ""))[:10] <= last]


def _num(v) -> str:
    """A figure, or a dash."""
    return "-" if v is None else str(v)


def change_pct(before, after):
    """The % change from before to after (whole number), or None when either is missing or before is 0."""
    if not before or after is None:
        return None
    return round((after - before) / before * 100)


def compare(before_rows, after_rows) -> list:
    """One dict per kind seen in either window: before and after figures, the % change of median and p90, and whether n is low."""
    def by_kind(rows):
        """The whole-kind figures by kind name."""
        return {k["kind"]: k for k in st.summarise(rows) if k["resumed"] is None}
    b, a = by_kind(before_rows), by_kind(after_rows)
    empty = {"n": 0, "median": None, "p90": None}
    out = []
    for kind in sorted(set(b) | set(a)):
        x, y = b.get(kind, empty), a.get(kind, empty)
        out.append({"kind": kind, "before": x, "after": y, "median_change_pct": change_pct(x["median"], y["median"]),
                    "p90_change_pct": change_pct(x["p90"], y["p90"]), "low_n": min(x["n"], y["n"]) < MIN_N})
    return out


def table(rows) -> str:
    """A text table of compare()."""
    def pct(v):
        """A % change, or a dash."""
        return "-" if v is None else f"{v:+d}%"
    lines = [f"{'Kind':<12}{'n b/a':>9}{'Median b':>10}{'Median a':>10}{'Change':>8}{'p90 b':>9}{'p90 a':>9}{'Change':>8}  Note",
             ]
    for r in rows:
        b, a = r["before"], r["after"]
        f = _num
        lines.append(f"{r['kind'] or '(none)':<12}{str(b['n']) + '/' + str(a['n']):>9}{f(b['median']):>10}{f(a['median']):>10}"
                     f"{pct(r['median_change_pct']):>8}{f(b['p90']):>9}{f(a['p90']):>9}{pct(r['p90_change_pct']):>8}"
                     f"  {'low n (under ' + str(MIN_N) + ' runs): a hint only' if r['low_n'] else ''}")
    return "\n".join(lines)


def _span(text):
    """FIRST and LAST of a FIRST:LAST window."""
    first, _, last = text.partition(":")
    if not last:
        raise SystemExit(f"a window is FIRST:LAST (YYYY-MM-DD:YYYY-MM-DD), not {text!r}")
    return first, last


def main(argv=None) -> int:
    """Print the comparison."""
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*", help="BEFORE.jsonl AFTER.jsonl")
    ap.add_argument("--file", help="one jsonl file, with --before and --after")
    ap.add_argument("--before", help="FIRST:LAST days")
    ap.add_argument("--after", help="FIRST:LAST days")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if len(a.files) == 2:
        before, after = read(a.files[0]), read(a.files[1])
    elif a.file and a.before and a.after:
        every = read(a.file)
        before, after = between(every, *_span(a.before)), between(every, *_span(a.after))
    else:
        ap.error("give two files, or --file with --before and --after")
    rows = compare(before, after)
    print(json.dumps(rows, separators=(",", ":")) if a.json else table(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
