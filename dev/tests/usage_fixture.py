"""Fixture for the Usage tab and usage_report --json (#238): fictional, counts only. Today is 2026-10-19 (CREAITE_NOW).

THIS_WEEK is 13 to 19 October, BEFORE the week before it (6 to 12 October). The expected figures, worked by hand:
  this week  4 runs  cost 6.50   median start 21000   average run cost 1.625  (rounds to 1.63)
  before     2 runs  cost 3.00   median start 20000   average run cost 1.50
  so cost +117 %, runs +100 %, start load +1000, average cost +8 %
"""
import json
from pathlib import Path

NOW = "2026-10-19 09:00"
TODAY = "2026-10-19"
POISON = "POISONED-TEXT: Jane Example wrote about the confidential merger and the secret price " * 4


def run(at, kind, cost, start, output=0, cache=None, skills=()):
    cache = start if cache is None else cache
    return {"at": at, "kind": kind, "label": "chat", "model": "claude-sonnet-5-5", "seconds": 5.0, "turns": 2, "input": 0,
            "output": output, "cache_read": cache, "cache_create": 0, "cost_usd": cost, "start_tokens": start, "stopped": False,
            "skills": list(skills)}


RUNS = [
    run("2026-10-19T08:00:00", "ask", 1.00, 20000, output=1000, cache=19000),                    # tokens 20000
    run("2026-10-19T09:00:00", "ask", 2.00, 22000, output=1000, cache=21000, skills=["cx-minutes"]),   # tokens 22000
    run("2026-10-17T10:00:00", "sweep", 3.00, 21000, output=4000, cache=21000, skills=["cx-sweep"]),   # tokens 25000
    run("2026-10-15T10:00:00", "vip", 0.50, 21000, output=0, cache=21000),                       # tokens 21000
    run("2026-10-08T10:00:00", "ask", 2.00, 20000, output=1000, cache=19000),                    # tokens 20000
    run("2026-10-10T10:00:00", "sweep", 1.00, 20000, output=1000, cache=20000, skills=["cx-sweep"]),  # tokens 21000
]

# Context change over 30 days: rules +3000 bytes (+750 tokens) since 2026-09-19; claude_md no change (baseline: its oldest row in the
# window, 2026-10-12); memory and skills have one row only, so no earlier measure.
CONTEXT = [
    # 30 days before today is 2026-09-19: the baseline is the latest row on or before it (50000), never the older 40000
    {"date": "2026-08-01", "file": "rules", "bytes": 40000, "tokens": 10000},
    {"date": "2026-09-19", "file": "rules", "bytes": 50000, "tokens": 12500},
    {"date": "2026-10-12", "file": "rules", "bytes": 51000, "tokens": 12750},
    {"date": "2026-10-19", "file": "rules", "bytes": 53000, "tokens": 13250},
    {"date": "2026-10-12", "file": "claude_md", "bytes": 700, "tokens": 175},
    {"date": "2026-10-19", "file": "claude_md", "bytes": 700, "tokens": 175},
    {"date": "2026-10-19", "file": "memory", "bytes": 5000, "tokens": 1250},
    {"date": "2026-10-19", "file": "skills", "bytes": 9000, "tokens": 2250},
]


def write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
