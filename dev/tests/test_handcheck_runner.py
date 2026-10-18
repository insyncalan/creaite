"""#212: dev/tools/handcheck.py runs the hand checks of v2.2.0 to v2.4.0, and only the judgement and live-only checks are left manual.

No browser, no vault: it reads the sheets and the test modules as the runner does (dev/tools/handcheck_report.py).

Run: python3 dev/tests/test_handcheck_runner.py   (quick tier)
"""
import importlib
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "dev" / "tools"))
sys.path.insert(0, str(HERE / "handchecks"))
sys.path.insert(0, str(HERE))
import handcheck_report as hr  # noqa: E402

FIRST, LAST = "v2.2.0", "v2.4.0"
WANT = ["v2.2.0", "v2.3.0", "v2.3.1", "v2.3.2", "v2.3.3", "v2.3.4", "v2.4.0"]
KINDS = {"scriptable", "measurable", "judgement", "live only"}
STRUCK = {"v2.4.0": {28}}          # numbering kept, no test (Check this report, #170, is out of 2.4.0)


def module_path(v):
    return REPO / "dev" / "tests" / "handchecks" / f"{hr.module_name(v)}.py"


def attr(v, name):
    return getattr(importlib.import_module(hr.module_name(v)), name, None)


class Runner(unittest.TestCase):
    def test_every_release_from_v220_to_v240_has_a_module_and_a_sheet(self):
        avail = hr.releases()
        self.assertEqual([v for v in avail if hr.vkey(FIRST) <= hr.vkey(v) <= hr.vkey(LAST)], WANT)
        for v in WANT:
            with self.subTest(v):
                self.assertTrue(module_path(v).is_file())
                sheet, _ = hr.sheet_checks(v)
                self.assertTrue(sheet, f"{v}: no sheet checks found")
        for v in (FIRST, "v2.3.0", "v2.3.2", "v2.3.3", "v2.3.4", LAST):
            self.assertTrue((REPO / "dev/handchecks" / f"{v}.md").is_file(), f"dev/handchecks/{v}.md")

    def test_the_runner_lists_and_accepts_them(self):
        r = subprocess.run([sys.executable, str(REPO / "dev/tools/handcheck.py"), "all", "--list", "--from", FIRST, "--to", LAST],
                           capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for v in WANT:
            self.assertIn(f"{v}  {hr.module_name(v)}.py", r.stdout)
        self.assertEqual(r.stdout.count("coverage: every sheet check has a test or is tagged judgement or live only"), len(WANT), r.stdout)
        bad = subprocess.run([sys.executable, str(REPO / "dev/tools/handcheck.py"), "v2.9.9"], capture_output=True, text=True, timeout=60)
        self.assertEqual(bad.returncode, 2)
        self.assertIn("dev/tests/handchecks/test_v299.py", bad.stderr)

    def test_each_module_tags_its_kinds_and_only_judgement_and_live_only_are_manual(self):
        for v in WANT:
            with self.subTest(v):
                kind, live = attr(v, "KIND"), attr(v, "LIVE_ONLY")
                self.assertIsInstance(kind, dict, f"{module_path(v).name}: KIND")
                self.assertIsInstance(live, dict, f"{module_path(v).name}: LIVE_ONLY")
                self.assertLessEqual(set(kind.values()), KINDS, "unknown kind")
                tests = hr.scan_tests(module_path(v))
                sheet, _ = hr.sheet_checks(v)
                manual = {n for n, k in kind.items() if k == "judgement"} | set(live)
                for n in sheet:
                    if n in manual or n in STRUCK.get(v, ()):
                        continue
                    self.assertIn(n, tests, f"{v} check {n}: no test, and not tagged judgement or live only")
                    self.assertTrue(tests[n], f"{v} check {n}: its test is marked phase2 (skipped)")
                tags = hr.module_tags(importlib.import_module(hr.module_name(v)))
                self.assertEqual(set(tags), manual, "the tags the runner reads are the manual checks")
                gaps = hr.coverage(sheet, tests, tags)["gaps"]
                self.assertEqual([g for g in gaps if g not in STRUCK.get(v, ())], [], f"{v}: coverage gaps")

    def test_v240_has_one_method_per_check_and_none_are_phase2(self):
        tests = hr.scan_tests(module_path("v2.4.0"))
        sheet, _ = hr.sheet_checks("v2.4.0")
        self.assertEqual(sorted(set(sheet) - set(tests)), [])
        self.assertEqual(sorted(n for n, runs in tests.items() if not runs), [], "no check is marked phase2")


if __name__ == "__main__":
    unittest.main()
