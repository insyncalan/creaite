"""Guard (#178): no new unpinned clock read. The tests and the product follow CREAITE_NOW; this fails on a new read of the real clock.

Run: python3 dev/tests/test_clock_guard.py     (quick tier: no Chrome, no vault)

Three rules, each a count per file so a new read is caught and an old one cannot grow:

1. The date-sensitive test files (dev/tools/prerelease_dates.py DATE_SENSITIVE, which the pre-release run pins to a Friday and a
   Monday) have no read of the real day at all: `date.today()`, `datetime.now()`, `datetime.today()`, `datetime.utcnow()`. They use
   test_dashboard.today() / now(), which follow CREAITE_NOW. The few genuine real-clock uses are in ALLOWED, each with its reason.
2. Every other test file may not read the real day more often than LEGACY_TESTS says (it only goes down; a new test file starts at
   zero). Move a file to today() when you touch it, and lower its count.
3. The product's own clock reads (system/scripts, and `new Date()` / `Date.now()` in the dashboard source) may not grow past SCRIPTS
   and DASHBOARD_JS. A new date helper takes the file's existing now() that honours CREAITE_NOW, not a new read of the real clock.
   time.time() is counted in the scripts as well; its timers and lock ages are wall-clock on purpose and sit in the baseline.
"""
import os
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / "tools"))
from prerelease_dates import DATE_SENSITIVE  # noqa: E402

TEST_READ = re.compile(r"datetime\.(now|today|utcnow)\(|date\.today\(")
SCRIPT_READ = re.compile(r"datetime\.(now|today|utcnow)\(|date\.today\(|time\.time\(\)")
JS_READ = re.compile(r"new Date\(\)|Date\.now\(\)")

# Genuine real-clock uses in the date-sensitive test files: (file, text on the line, why it is the real clock on purpose).
ALLOWED = (
    ("test_dashboard.py", "else datetime.now()", "the helper itself: the real time when CREAITE_NOW is not set"),
    ("test_dashboard.py", "never date.today()", "the helper's docstring"),
    ("test_dashboard_data_pinned.py", "calendar:e10 |\", f\"{FIXED}",
     "tracker.py dates the processed.txt line with the real day (a guarded file); the test rewrites it to its fixed day"),
    ("test_debug_log_wiring.py", "datetime.now()",
     "the debug log's stamps are to the second and its server runs on the real clock (pin_clock = False): a frozen clock gives no new error"),
    ("test_run_chat.py", "TODAY = date.today().isoformat()",
     "live_server.py names the runs chat runs-<real day> (its run id ignores CREAITE_NOW; a guarded file)"),
    ("test_run_chat.py", "start_catchup(datetime.now())", "the stand-in harness is a subprocess on the real clock, like the server it drives"),
)

# Baselines: reads of the real clock today, per file. They only go down (#178). Not an approval of any one of them.
LEGACY_TESTS = {
    "test_archive_items_browser.py": 1, "test_bulk_edit.py": 3, "test_capture_drawer.py": 1, "test_cell_edit.py": 4,
    "test_chat_and_sweep.py": 6, "test_check_py39.py": 1, "test_current_state_live.py": 1, "test_dashboard_editing.py": 2,
    "test_decisions_dashboard.py": 1, "test_forecast.py": 1, "live_updates_support.py": 2,
    "test_milestone_states.py": 1, "test_new_item_peek.py": 1, "test_notes_175.py": 1, "test_notes_autosave_backups.py": 2, "test_notes_header.py": 2,
    "test_onedrive_projects.py": 1, "test_peek_fixes.py": 1, "test_plain_dates.py": 1, "test_review_triage.py": 1,
    "test_steerco_dashboard.py": 1, "test_transcripts.py": 1,
    "test_vip_confidential.py": 1, "test_vip_conversations.py": 1, "test_vip_screens.py": 3, "test_weekend_dates.py": 3,
    "test_work_all_items.py": 1, "test_work_filter_picker.py": 1, "test_work_grouping.py": 1, "test_work_item_peek.py": 1,
    "test_work_saved_views.py": 1, "test_workstreams.py": 2, "test_writer_pinned.py": 2, "work_board_case.py": 2,
}
SCRIPTS = {
    "archive.py": 3, "backup.py": 3, "build_dashboard.py": 5, "capture.py": 1, "creaite_doc.py": 3, "doctor.py": 2,
    "drafts.py": 7, "excel_sync.py": 5, "extraction.py": 1, "filechange.py": 3, "health.py": 1, "health_fixes.py": 1,
    "launch.py": 2, "live_server.py": 46, "log.py": 1, "minutes.py": 4, "notes.py": 3, "notes_find.py": 3, "permissions.py": 4,
    "propose.py": 7, "quality.py": 1, "reach.py": 3, "review.py": 5, "search.py": 1, "settings_catalogue.py": 2,
    "sneak_peek.py": 1, "status_checks.py": 1, "sweep.py": 3, "tracker.py": 7, "transcripts.py": 1, "update.py": 3, "usage_log.py": 1, "usage_report.py": 1,
}
DASHBOARD_JS = {
    "ask.js": 15, "components/notes/CaptureDrawer.jsx": 1, "components/notes/DeleteNote.jsx": 1,
    "components/peek/ChasePane.jsx": 2, "components/Menu.jsx": 2, "components/notes/NotesPage.jsx": 2, "components/report/weekly/weeklyDoc.js": 1, "core/data.js": 1, "core/dayroll.js": 1,
    "core/motion.js": 1, "core/page.js": 2, "core/server.js": 7, "drafts.js": 4, "files.js": 1, "help.js": 2, "core/intakeApi.js": 2,
    "meetings.js": 2, "milestones.js": 2, "panel.js": 6, "projects.js": 3, "review.js": 1, "settings.js": 5, "sneak.js": 3,
    "stores/aiEdit.js": 3, "stores/notes.js": 3, "stores/prepPopup.js": 3, "stores/settings.js": 1, "today.js": 3,
}


def reads(path, pattern):
    """(line number, line) for each line that reads the clock in code (a read after a # comment mark does not count)."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return [(n, line) for n, line in enumerate(lines, 1) if pattern.search(line.split("#")[0])]


class ClockGuard(unittest.TestCase):
    def test_the_date_sensitive_files_do_not_read_the_real_day(self):
        bad = []
        for name in DATE_SENSITIVE:
            for n, line in reads(HERE / name, TEST_READ):
                if not any(f == name and text in line for f, text, _why in ALLOWED):
                    bad.append(f"{name}:{n}: {line.strip()[:110]}")
        self.assertEqual(bad, [], "a real-clock read in a date-sensitive test: use test_dashboard.today() or now() (they follow "
                                  "CREAITE_NOW), or add the line to ALLOWED with its reason")

    def test_every_allowance_has_a_reason_and_still_matches_a_line(self):
        for name, text, why in ALLOWED:
            self.assertTrue(why.strip(), f"{name}: {text!r} has no reason")
            lines = (HERE / name).read_text(encoding="utf-8").splitlines()
            self.assertTrue(any(text in line for line in lines), f"ALLOWED has a stale entry: {name}: {text!r}")

    def test_every_listed_date_sensitive_file_exists(self):
        self.assertEqual([n for n in DATE_SENSITIVE if not (HERE / n).exists()], [])

    def test_other_test_files_do_not_read_the_real_day_more_than_before(self):
        grew = []
        for path in sorted(HERE.glob("*.py")):
            if path.name in DATE_SENSITIVE or path.name == Path(__file__).name:
                continue
            n = len(reads(path, TEST_READ))
            if n > LEGACY_TESTS.get(path.name, 0):
                grew.append(f"{path.name}: {n} reads, {LEGACY_TESTS.get(path.name, 0)} allowed")
        self.assertEqual(grew, [], "a new unpinned date read in a test: use test_dashboard.today() / now() (CREAITE_NOW)")

    def test_the_baseline_only_goes_down(self):
        stale = []
        for name, allowed in LEGACY_TESTS.items():
            n = len(reads(HERE / name, TEST_READ)) if (HERE / name).exists() else 0
            if n < allowed:
                stale.append(f"{name}: {allowed} listed, {n} read")
        self.assertEqual(stale, [], "a file reads the real day less than LEGACY_TESTS says: lower its count")

    def test_the_product_adds_no_new_clock_read(self):
        grew = []
        for path in sorted((REPO / "system" / "scripts").glob("*.py")):
            n = len(reads(path, SCRIPT_READ))
            if n > SCRIPTS.get(path.name, 0):
                grew.append(f"{path.name}: {n} reads, {SCRIPTS.get(path.name, 0)} allowed")
        self.assertEqual(grew, [], "a new real-clock read in a script: use the script's now() / today helper, which follows CREAITE_NOW")

    def test_the_dashboard_source_adds_no_new_clock_read(self):
        src = REPO / "system" / "templates" / "dashboard" / "src"
        grew = []
        for root, _dirs, files in os.walk(src):
            for name in sorted(files):
                path = Path(root) / name
                rel = path.relative_to(src).as_posix()
                n = len(JS_READ.findall(path.read_text(encoding="utf-8", errors="replace")))
                if n > DASHBOARD_JS.get(rel, 0):
                    grew.append(f"{rel}: {n} reads, {DASHBOARD_JS.get(rel, 0)} allowed")
        self.assertEqual(grew, [], "a new `new Date()` / `Date.now()` in the page: keep reads in the shared date helpers "
                                   "(the tests pin the page clock with page_clock_js)")


if __name__ == "__main__":
    unittest.main()
