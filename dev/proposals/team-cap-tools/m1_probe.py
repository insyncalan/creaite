#!/usr/bin/env python3
"""M1 probe (fixed in 2.6.1): a malformed top-level `note` (or an item's `values` as a string) in a proposal must never roll back the apply.

Usage: python3 -I m1_probe.py <checkout>      (scratch vaults go under $TMPDIR, or the system temp folder)
Exit 0: every case applied (rc 0, a row written) and history_of didn't raise; 1 otherwise.
"""
import json
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path

REPO = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(REPO / "dev" / "tests"))
from test_tracker import Vault, action  # noqa: E402

CASES = [("control", {}), ("note-string", {"note": "a string"}), ("note-list", {"note": ["x"]}),
         ("note-number", {"note": 3}), ("note-path-list", {"note": {"path": ["x"]}})]
bad = 0
for name, extra in CASES:
    v = Vault()
    try:
        v.run("init")
        v.propose("m1", [action(1)], **extra)
        r = v.run("apply", ok=False)
        with closing(sqlite3.connect(v.root / "system/tracker.db")) as con:
            n = con.execute("SELECT count(*) FROM actions").fetchone()[0]
        h = subprocess.run([sys.executable, "-c", "import json, sys; sys.path.insert(0, 'system/scripts'); import item_history; "
                            "print(len(item_history.history_of('ABC-A-001')['events']))"],
                           cwd=v.root, capture_output=True, text=True)
        hist = h.stdout.strip() if h.returncode == 0 else "RAISED " + (h.stderr.strip().splitlines() or ["?"])[-1]
        ok = r.returncode == 0 and n == 1 and h.returncode == 0
        bad += not ok
        print(f"{name:16} apply rc {r.returncode}, actions {n}, history: {hist}  {'ok' if ok else 'FAIL'}")
    finally:
        v.cleanup()

# values as a string on an update, and a history read of an item applied from an old proposal (no item_events: derived route)
v = Vault()
try:
    v.run("init")
    v.propose("m1a", [action(1)])
    v.run("apply")
    v.propose("m1b", [{"n": 1, "op": "update", "table": "actions", "id": "ABC-A-001", "changes": {"status": "Delayed"},
                       "values": "x", "match": "strong", "flags": [], "decision": "approved"}])
    r = v.run("apply", ok=False)
    h = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, 'system/scripts'); import item_history, sqlite3, paths\n"
                        "con = sqlite3.connect(paths.DB); con.execute('DELETE FROM item_events') if con.execute(\"SELECT 1 FROM sqlite_master WHERE name='item_events'\").fetchone() else None; con.commit(); con.close()\n"
                        "print(len(item_history.history_of('ABC-A-001')['events']))"], cwd=v.root, capture_output=True, text=True)
    with closing(sqlite3.connect(v.root / "system/tracker.db")) as con:
        st = con.execute("SELECT status FROM actions").fetchone()[0]
    ok = r.returncode == 0 and st == "Delayed" and h.returncode == 0
    bad += not ok
    print(f"{'values-string':16} apply rc {r.returncode}, status {st}, derived history: "
          f"{h.stdout.strip() if h.returncode == 0 else 'RAISED ' + h.stderr.strip().splitlines()[-1]}  {'ok' if ok else 'FAIL'}")
finally:
    v.cleanup()
print("M1 FIXED" if not bad else f"M1 OPEN ({bad} failing)")
sys.exit(1 if bad else 0)
