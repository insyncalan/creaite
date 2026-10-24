"""#339 part A: lighter runs. The two guarded patches (dev/proposals/339/*.diff) apply to live_server.py, and with them a typed
"refresh calendar" starts the small "calendar" kind and a sweep's --add-dir leaves out the home folder.

Run: python3 dev/tests/test_lighter_runs_339.py      (quick tier)
Structure checks read live_server.py as text. Tests that need the patches run on a throwaway copy with them applied (nothing in this
tree is touched) and are GUARDED skips once the tree has them (they then run on the tree itself).
"""
import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LIVE = REPO / "system/scripts/live_server.py"
DIFFS = sorted(p for p in (REPO / "dev/proposals/339").glob("*.diff") if p.name != "tests-pins.diff")
PINS = REPO / "dev/proposals/339/tests-pins.diff"
LANDED = "def panel_calendar" in LIVE.read_text(encoding="utf-8")


def patched_copy(test):
    """A throwaway live_server.py with the 339 diffs applied (or a plain copy once they have landed)."""
    d = Path(tempfile.mkdtemp(prefix="p339-"))
    test.addCleanup(shutil.rmtree, d, True)
    (d / "system/scripts").mkdir(parents=True)
    shutil.copy2(LIVE, d / "system/scripts/live_server.py")
    subprocess.run(["git", "init", "-q"], cwd=d, capture_output=True)
    if not LANDED:
        for f in DIFFS:
            r = subprocess.run(["git", "apply", str(f)], cwd=d, capture_output=True, text=True)
            test.assertEqual(r.returncode, 0, f"{f.name}: {r.stderr}")
    return d / "system/scripts/live_server.py"


class Structure(unittest.TestCase):
    """Pieces that need no guarded change."""

    def setUp(self):
        self.src = LIVE.read_text(encoding="utf-8")

    def test_sweep_and_calendar_kinds_exist(self):
        self.assertIn('KIND_ARGS["calendar"]', self.src)
        self.assertIn('KIND_ARGS["sweep"]', self.src)
        self.assertIn("def panel_sweep(", self.src)

    def test_calendar_kind_reads_no_project_file(self):
        self.assertRegex(self.src, r'policy == "calendar"[^\n]*\n\s+return \[\]')

    def test_calendar_words_are_in_the_sweep_recogniser(self):
        self.assertIn("refresh (?:the |my )?calendar", self.src)

    def test_the_page_side_change_is_in_the_source_and_the_built_page(self):
        js = (REPO / "system/templates/dashboard/src/ask.js").read_text(encoding="utf-8")
        self.assertIn("export const typedCalendar=", js)
        self.assertIn("typedCalendar(q,confirmed)", js)                                # drawn as a run creaite started (plain)
        self.assertIn("j.message&&!j.run?j.message", js)                              # the sweep-running sentence
        self.assertIn("plain&&res.status===400", js)                                  # the precheck's own reason
        self.assertIn("typedCalendar", (REPO / "system/templates/dashboard.html").read_text(encoding="utf-8"))

    def test_usage_report_lists_a_label_and_kind_per_run(self):
        sys.path.insert(0, str(REPO / "system/scripts"))
        import io
        import contextlib
        import usage_report
        import os
        d = Path(tempfile.mkdtemp(prefix="u339-"))
        self.addCleanup(shutil.rmtree, d, True)
        f = d / "u.jsonl"
        f.write_text('{"at":"2026-10-25T09:00:00","kind":"sweep","label":"chat","start_tokens":260000,"cost_usd":4.55}\n'
                     '{"at":"2026-10-25T10:00:00","kind":"ask","label":"chat","start_tokens":100,"cost_usd":0.1}\n', encoding="utf-8")
        os.environ["CREAITE_NOW"] = "2026-10-25 12:00"
        self.addCleanup(os.environ.pop, "CREAITE_NOW", None)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            usage_report.main(["--file", str(f), "--label", "chat", "--kind", "sweep"])
        self.assertIn("260000", out.getvalue())
        self.assertNotIn(" 100 ", out.getvalue())

    def test_patches_are_guarded_only_and_short(self):
        self.assertTrue(DIFFS)
        for f in [*DIFFS, PINS]:
            text = f.read_text(encoding="utf-8")
            only = {"system/scripts/live_server.py"} if f.name != "tests-pins.diff" else {
                "dev/tests/test_panel_sweep.py", "dev/tests/test_calendar_refresh.py", "dev/tests/test_ai_budget_gate_334.py"}
            self.assertEqual(set(re.findall(r"^diff --git a/(\S+)", text, re.M)), only)
            self.assertFalse([ln for ln in text.splitlines() if ln.startswith("+") and len(ln) > 141])


@unittest.skipIf(LANDED, "GUARDED: the patches have landed; Patched runs on the tree")
class PatchesApply(unittest.TestCase):
    def test_each_applies_alone_and_together(self):
        for f in DIFFS:
            d = Path(tempfile.mkdtemp(prefix="p339-"))
            self.addCleanup(shutil.rmtree, d, True)
            (d / "system/scripts").mkdir(parents=True)
            shutil.copy2(LIVE, d / "system/scripts/live_server.py")
            subprocess.run(["git", "init", "-q"], cwd=d, capture_output=True)
            r = subprocess.run(["git", "apply", "--check", str(f)], cwd=d, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"{f.name}: {r.stderr}")
        patched_copy(self)


class Patched(unittest.TestCase):
    """GUARDED: need the patches (applied to a throwaway copy while they are not in the tree)."""

    @classmethod
    def setUpClass(cls):
        d = Path(tempfile.mkdtemp(prefix="p339m-"))
        cls._d = d
        (d / "system/scripts").mkdir(parents=True)
        shutil.copy2(LIVE, d / "system/scripts/live_server.py")
        subprocess.run(["git", "init", "-q"], cwd=d, capture_output=True)
        if not LANDED:
            for f in DIFFS:
                subprocess.run(["git", "apply", str(f)], cwd=d, capture_output=True, check=True)
        cls.path = d / "system/scripts/live_server.py"
        cls.src = cls.path.read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._d, True)

    def fn(self):
        """panel_kind, run from the source text (panel_sweep's words and both functions; the module itself needs the whole server)."""
        a = self.src.index("PANEL_SWEEP_WORDS = re.compile(")
        b = self.src.index("PANEL_SWEEP_PROMPT = (")
        ns = {"re": re}
        exec(self.src[a:b], ns)
        return ns["panel_kind"], ns["panel_sweep"]

    def test_panel_kind_routes_only_and_panel_sweep_keeps_the_words(self):
        kind, sweep = self.fn()
        for ok in ("refresh calendar", "Refresh the calendar", "please refresh my calendar now.", "refresh my calendar please!"):
            self.assertEqual(kind(ok), "calendar", ok)
            self.assertTrue(sweep(ok), ok)                                   # the budget gate and the queue still exempt it
        for ok in ("sweep", "sweep mail for ABC", "check my mail", "sweep the UAT plan thread"):
            self.assertEqual(kind(ok), "sweep", ok)
        for no in ("refresh calendar and apply", "refresh calendar for ABC", "refreshing calendar", "x" * 130, "tell me about it"):
            self.assertIsNone(kind(no), no)
        self.assertIsNone(kind("refresh calendar", images=["a.png"]))
        self.assertIsNone(kind("refresh calendar", confirmed="Add action"))

    def test_ask_and_queue_route_calendar_to_its_run(self):
        self.assertIn("def calendar_run(run_id):", self.src)
        run = self.src[self.src.index("def calendar_run("):self.src.index("PANEL_SWEEP_PROMPT = (")]
        self.assertIn("None, None, None, kind=\"calendar\"", run)                  # no session, no chat: nothing carried or inherited
        self.assertIn("calendar_refresh.build_prompt()", run)                       # the fixed prompt, never the typed words
        self.assertIn("sweep_running()", run)
        self.assertIn("calendar_refresh.precheck()", run)
        self.assertIn('SWEEP_RUNNING_SAYS = "A mail check is running; try again when it ends."', self.src)
        ask = self.src[self.src.index("    def ask(self, req):"):self.src.index("sweep = panel_sweep(message")]
        self.assertIn("busy = current_run()", ask)                                  # a run going: the 409, before the route
        self.assertIn('panel_kind(message, images, req.get("confirmed")) == "calendar"', ask)
        self.assertIn("409 if said == SWEEP_RUNNING_SAYS else 400", ask)
        q = self.src[self.src.index("def queue_start("):self.src.index("def queue_after(")]
        self.assertIn('panel_kind(item["text"], images) == "calendar"', q)         # the second call site

    def test_budget_gate_still_reads_panel_sweep(self):
        gate = self.src[self.src.index("def budget_gate("):self.src.index("CARRY_TURNS")]
        self.assertIn("panel_sweep(req.get(\"message\")", gate)

    def test_calendar_is_a_known_kind(self):
        for needle in ('KIND_ARGS["calendar"]', '"calendar": "calendar"'):
            self.assertIn(needle, self.src)

    def test_sweep_run_dirs_leave_out_the_home_folder(self):
        self.assertIn('policy not in ("process", "reextract", "sweep")', self.src)

    def test_both_sweep_prompts_carry_the_followed_people_rule(self):
        for name in ("KIND_PROMPTS = {\"sweep\"", "PANEL_SWEEP_PROMPT = ("):
            start = self.src.index(name)
            block = self.src[start:self.src.index("\n# ", start)]
            self.assertIn("VIP_PRIVATE_RULE", block, name)

    def test_the_recogniser_pins_stay_and_the_rewritten_pins_apply(self):
        """panel_sweep keeps "refresh calendar", so the recogniser pin (test_panel_sweep) stays as it is; only the routing pins are
        rewritten on purpose, by dev/proposals/339/tests-pins.diff, which must apply to the three test files as they are now."""
        pin = (REPO / "dev/tests/test_panel_sweep.py").read_text(encoding="utf-8")
        self.assertIn('"sweep the UAT plan thread", "refresh calendar", "Refresh the calendar"', pin)
        d = Path(tempfile.mkdtemp(prefix="p339t-"))
        self.addCleanup(shutil.rmtree, d, True)
        (d / "dev/tests").mkdir(parents=True)
        for n in ("test_panel_sweep", "test_calendar_refresh", "test_ai_budget_gate_334"):
            shutil.copy2(REPO / f"dev/tests/{n}.py", d / f"dev/tests/{n}.py")
        subprocess.run(["git", "init", "-q"], cwd=d, capture_output=True)
        r = subprocess.run(["git", "apply", "--check", str(PINS)], cwd=d, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()
