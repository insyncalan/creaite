"""Pre-release date check (#178): the date-sensitive test files, run pinned to a Friday, pinned to a Monday and unpinned.

Run: python3 dev/tools/prerelease_dates.py [--list] [--jobs N] [--pins friday,monday,real]

Why: a test that builds its fixtures from the real day passes on the day it was written and fails on another weekday (a Saturday
run once hid "said by Friday" checks, a Friday pin and a Monday pin each failed 18 and 22 files). The release gate runs this
once, from the release branch. It runs `dev/tools/run_tests.py` on DATE_SENSITIVE three times, with `CREAITE_NOW` set to
Friday 16-10-2026 09:30, to Monday 12-10-2026 09:30 and not set at all, and fails (exit 1) when any run has a failing file, or
when the three runs do not fail the same files (a file that passes unpinned and fails pinned is the case it exists for).

The page's clock follows `CREAITE_NOW` too (live_browser.LiveBrowserCase and test_insight.chrome pin it), so the page and the data
agree. Test-only: no product code is read or changed. Not in CI: `.github` is untouched; the release steps run this by hand.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUN_TESTS = REPO / "dev" / "tools" / "run_tests.py"

PINS = {"friday": "2026-10-16 09:30", "monday": "2026-10-12 09:30", "real": ""}

# The files that build fixtures from the day (the #178 sweep). A new test that reads the day through test_dashboard.today()
# belongs here. Full file names, so `run_tests.py` does not match a longer name by substring.
DATE_SENSITIVE = (
    "test_ask_prep_offer.py", "test_count_links.py", "test_dashboard_data_pinned.py", "test_debug_log_wiring.py",
    "test_dashboard.py", "test_drafts_email.py", "test_decisions_prep.py", "test_drafts_agenda.py", "test_insight.py",
    "test_meetings.py", "test_prep_reimagined.py", "test_prep_page_content.py", "test_prep_view.py", "test_promises_page.py",
    "test_run_chat.py", "test_sweep_alerts.py", "test_today_brief.py", "test_work_filters_live.py", "test_milestone_ui.py",
    "test_minutes_editor.py", "test_pages.py", "test_people_dashboard.py", "test_settings_page.py", "test_close_day_card.py",
)


def failed_files(output):
    """The test files `run_tests.py` reports as failed, taking a re-run alone ("alone") over the run under load."""
    state = {}
    for line in output.splitlines():
        m = re.match(r"(OK|FAIL|TIMEOUT)\s+(test_\w+\.py)\s+\((\d+)s(, alone)?\)", line)
        if m:
            state[m.group(2)] = m.group(1) != "OK"
    return sorted(name for name, bad in state.items() if bad)


def run_pin(label, stamp, jobs):
    """Run DATE_SENSITIVE under one pin ("" for none) and return the files that failed."""
    env = {k: v for k, v in os.environ.items() if k != "CREAITE_NOW"}
    if stamp:
        env["CREAITE_NOW"] = stamp
    print(f"== {label}: {'CREAITE_NOW=' + stamp if stamp else 'CREAITE_NOW not set'}", flush=True)
    r = subprocess.run([sys.executable, str(RUN_TESTS), "-j", str(jobs), *DATE_SENSITIVE], cwd=REPO, env=env,
                       capture_output=True, text=True)
    bad = failed_files(r.stdout)
    if r.returncode and not bad:
        bad = ["(run_tests.py exited %d without naming a file)" % r.returncode]
    print(f"   {'failed: ' + ', '.join(bad) if bad else 'all passed'}", flush=True)
    return bad


def main(argv):
    """Run every pin, compare them, print the verdict; 0 when all passed alike, else 1."""
    if "--list" in argv:
        print("\n".join(DATE_SENSITIVE))
        return 0
    jobs = int(argv[argv.index("--jobs") + 1]) if "--jobs" in argv else 4
    chosen = argv[argv.index("--pins") + 1].split(",") if "--pins" in argv else list(PINS)
    results = {label: run_pin(label, PINS[label], jobs) for label in chosen}
    problems = [f"{label}: {', '.join(bad)}" for label, bad in results.items() if bad]
    if len({tuple(v) for v in results.values()}) > 1:
        problems.append("the runs differ: " + "; ".join(f"{k} fails {len(v)}" for k, v in results.items()))
    if problems:
        print("PRE-RELEASE DATE CHECK FAILED\n  " + "\n  ".join(problems))
        return 1
    print("pre-release date check: the same result pinned to a Friday, a Monday and unpinned")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
