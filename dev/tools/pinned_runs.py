"""Run the date-sensitive test files pinned to fixed days and print a pass/fail table (#178; development only).

Run: python3 dev/tools/pinned_runs.py [-t SECONDS] [--pins fri,mon,real] [name ...]
  name       only the files whose name contains it (default: the whole LIST below)
  --pins     which clocks to run each file under (default fri,mon,real):
               fri   CREAITE_NOW=2026-10-16 09:30 (Friday: the weekly-report day)
               mon   CREAITE_NOW=2026-10-12 09:30 (Monday: the week's first day)
               real  CREAITE_NOW unset
  -t         per-run limit in seconds (default 240); a run over it is reported as TIMEOUT

Files run one at a time (the machine is shared). Not part of run_tests.py's default run. The tests build their dates
through test_dashboard.today()/d()/now(), which follow CREAITE_NOW; a failure here is a fixture reading the real date.
"""
import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PINS = {"fri": "2026-10-16 09:30", "mon": "2026-10-12 09:30", "real": ""}

# The one list: the test files whose fixtures follow the day (#178).
LIST = [
    "ask_prep_offer", "count_links", "dashboard_data_pinned", "debug_log_wiring", "dashboard", "drafts_email",
    "decisions_prep", "drafts_agenda", "insight", "meetings", "prep_reimagined", "prep_page_content", "prep_view",
    "promises_page", "run_chat", "sweep_alerts", "today_brief", "work_filters_live",
    "milestone_ui", "minutes_editor", "pages", "people_dashboard",
]


def run(name, pin, limit):
    env = {k: v for k, v in os.environ.items() if k != "CREAITE_NOW"}
    if pin:
        env["CREAITE_NOW"] = pin
    t = time.time()
    p = subprocess.Popen([sys.executable, str(ROOT / "dev/tests" / f"test_{name}.py")], cwd=ROOT, env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
    try:
        out, _ = p.communicate(timeout=limit)
        res = "pass" if p.returncode == 0 else "FAIL"
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        out, _ = p.communicate()
        res = "TIMEOUT"
    return res, int(time.time() - t), out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*")
    ap.add_argument("--pins", default="fri,mon,real")
    ap.add_argument("-t", type=int, default=240)
    a = ap.parse_args()
    pins = a.pins.split(",")
    names = [n for n in LIST if not a.names or any(x in n for x in a.names)]
    print("%-26s" % "file" + "".join("%-14s" % p for p in pins), flush=True)
    bad = 0
    for n in names:
        cells = []
        for p in pins:
            res, secs, out = run(n, PINS[p], a.t)
            bad += res != "pass"
            cells.append("%-14s" % ("%s %ds" % (res, secs)))
            if res != "pass":
                lines = out.strip().splitlines()
                heads = [x for x in lines if x.startswith(("FAIL:", "ERROR:"))][:6]
                tail = "\n".join(heads + lines[-3:])
                sys.stderr.write("--- %s [%s]\n%s\n" % (n, p, tail))
        print("%-26s" % n + "".join(cells), flush=True)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
