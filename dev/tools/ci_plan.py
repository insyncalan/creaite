"""CI plan: how many shards each Linux job set gets so a run uses exactly the plan's concurrent-job limit (dev speed).

GitHub's Free plan allows 20 jobs at once (Pro 40, Team 60). A run that uses fewer leaves capacity idle; one that uses more queues.
The tests workflow's `plan` job runs this and feeds the result to its matrix:

    python3 dev/tools/ci_plan.py [--macos] [--limit N]      prints the matrix as JSON; with GITHUB_OUTPUT set, also writes `matrix=…`

Python 3.14 runs every test file in the 3.14 shards; Python 3.9 (the floor) runs the quick tier in QUICK_SHARDS shards; macOS (3.14,
MAC_SHARDS shards) is added only when the run asks for it. The 3.14 shards get what is left: limit - QUICK_SHARDS - (MAC_SHARDS if
macos). The `plan` job itself finishes before the shards start and `Tests passed` starts after they end, so neither counts.
"""
import argparse
import json
import os
import sys

LIMIT = 20            # the Free plan's concurrent jobs (set CREAITE_CI_LIMIT or --limit for another plan)
QUICK_SHARDS = 3      # Python 3.9, the quick tier
MAC_SHARDS = 3        # macOS, when asked for


def shards_314(macos, limit=LIMIT):
    """How many Python 3.14 shards fill the limit."""
    return max(1, limit - QUICK_SHARDS - (MAC_SHARDS if macos else 0))


def matrix(macos, limit=LIMIT):
    """The strategy.matrix object: one entry per job."""
    n = shards_314(macos, limit)
    inc = [{"python": "3.14", "shard": i, "shards": n, "scope": ""} for i in range(1, n + 1)]
    inc += [{"python": "3.9", "shard": i, "shards": QUICK_SHARDS, "scope": "--quick"} for i in range(1, QUICK_SHARDS + 1)]
    return {"include": inc}


def main(argv):
    """Print the job matrix (or its size) for the CI workflow."""
    ap = argparse.ArgumentParser(prog="ci_plan.py")
    ap.add_argument("--macos", action="store_true", help="the run also starts the macOS job (3 shards)")
    ap.add_argument("--limit", type=int, default=int(os.environ.get("CREAITE_CI_LIMIT") or LIMIT))
    a = ap.parse_args(argv)
    m = matrix(a.macos, a.limit)
    text = json.dumps(m, separators=(",", ":"))
    print(text)
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"matrix={text}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
