"""#339 part A: lighter runs. The two guarded patches (dev/proposals/339/*.diff) apply to live_server.py, and with them a typed
"refresh calendar" starts the small "calendar" kind and a sweep's --add-dir leaves out the home folder.

Run: python3 dev/tests/test_lighter_runs_339.py      (quick tier)
Structure checks read live_server.py as text. Tests that need the patches run on a throwaway copy with them applied (nothing in this
tree is touched) and are GUARDED skips once the tree has them (they then run on the tree itself).
"""
import contextlib
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
LIVE = REPO / "system/scripts/live_server.py"
DIFFS = sorted(p for p in (REPO / "dev/proposals/339").glob("*.diff") if p.name not in ("tests-pins.diff", "creaite-rules.diff"))
RULES = REPO / "dev/proposals/339/creaite-rules.diff"
PINS = REPO / "dev/proposals/339/tests-pins.diff"
PIN_FILES = ("test_panel_sweep", "test_calendar_refresh", "test_ai_budget_gate_334", "test_mail_check")
sys.path.insert(0, str(REPO / "system/scripts"))


def git_apply(d, diff, *flags):
    return subprocess.run(["git", "apply", *flags, str(diff)], cwd=d, capture_output=True, text=True)


def scratch(files):
    """A throwaway git repo holding copies of these repo files (paths relative to the repo root)."""
    d = Path(tempfile.mkdtemp(prefix="p339-"))
    for f in files:
        (d / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / f, d / f)
    subprocess.run(["git", "init", "-q"], cwd=d, capture_output=True)
    return d


def landed(diff, files):
    """Whether this diff is already in the tree (its reverse applies), decided per diff: a landing of only some of them is fine."""
    d = scratch(files)
    try:
        return git_apply(d, diff, "--reverse", "--check").returncode == 0
    finally:
        shutil.rmtree(d, True)


LIVE_REL = ["system/scripts/live_server.py"]
PIN_REL = [f"dev/tests/{n}.py" for n in PIN_FILES]
PENDING = [f for f in DIFFS if not landed(f, LIVE_REL)]          # the ones still to apply to a copy
PINS_LANDED = landed(PINS, PIN_REL)


def patched_source():
    """live_server.py's text with every not-yet-landed diff applied (applied to a throwaway copy; the tree is not touched)."""
    d = scratch(LIVE_REL)
    try:
        for f in PENDING:
            r = git_apply(d, f)
            assert r.returncode == 0, f"{f.name}: {r.stderr}"
        return (d / LIVE_REL[0]).read_text(encoding="utf-8")
    finally:
        shutil.rmtree(d, True)


SRC = patched_source()


def module(src=None):
    """The patched server as a module (the module itself runs from the real path, like test_ai_budget_gate_334's mutants)."""
    mod = types.ModuleType("live_server_339")
    mod.__file__ = str(LIVE)
    exec(compile(src or SRC, str(LIVE), "exec"), mod.__dict__)
    return mod


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

    def test_patches_are_guarded_only_and_short(self):
        self.assertTrue(DIFFS)
        for f in [*DIFFS, PINS, RULES]:
            text = f.read_text(encoding="utf-8")
            only = {"tests-pins.diff": {f"dev/tests/{n}.py" for n in PIN_FILES},
                    "creaite-rules.diff": {"system/creaite-rules.md"}}.get(f.name, {"system/scripts/live_server.py"})
            self.assertEqual(set(re.findall(r"^diff --git a/(\S+)", text, re.M)), only)
            if f is not RULES:                                                      # the rules file is written in long lines
                self.assertFalse([ln for ln in text.splitlines() if ln.startswith("+") and len(ln) > 141])


class PatchesApply(unittest.TestCase):
    def test_each_applies_alone_and_all_together(self):
        for f in PENDING:
            d = scratch(LIVE_REL)
            self.addCleanup(shutil.rmtree, d, True)
            r = git_apply(d, f, "--check")
            self.assertEqual(r.returncode, 0, f"{f.name}: {r.stderr}")
        self.assertTrue(SRC)

    @unittest.skipIf(PINS_LANDED, "GUARDED: the pin rewrites have landed")
    def test_the_pin_rewrites_apply_to_the_three_test_files(self):
        d = scratch(PIN_REL)
        self.addCleanup(shutil.rmtree, d, True)
        r = git_apply(d, PINS, "--check")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_the_rules_diff_applies_to_creaite_rules(self):
        d = scratch(["system/creaite-rules.md"])
        self.addCleanup(shutil.rmtree, d, True)
        if git_apply(d, RULES, "--reverse", "--check").returncode == 0:
            self.skipTest("GUARDED: the rules diff has landed")
        self.assertEqual(git_apply(d, RULES, "--check").returncode, 0)
        self.assertIn("typed \"refresh calendar\"", RULES.read_text(encoding="utf-8"))

    def test_the_recogniser_pin_stays(self):
        pin = (REPO / "dev/tests/test_panel_sweep.py").read_text(encoding="utf-8")
        self.assertIn('"sweep the UAT plan thread", "refresh calendar", "Refresh the calendar"', pin)


class Behaviour(unittest.TestCase):
    """GUARDED: the patched server (a copy while the diffs are not in the tree), run with stand-ins for Run and the checks."""

    @classmethod
    def setUpClass(cls):
        cls.ls = module()

    class Reached(Exception):
        pass

    def handler(self):
        class H:
            sent = None
            numbered = staticmethod(lambda: False)

            def send(self, code, body):
                self.sent = (code, body)

            def follow(self, run, **kw):
                self.followed = run

        return H()

    def ask(self, req, sweep=False, why=None, busy=None):
        import calendar_refresh
        ls, h, runs = self.ls, self.handler(), []

        def run(*a, **kw):
            runs.append((a, kw))
            return mock.Mock(done=False)

        with mock.patch.object(ls, "Run", side_effect=run), mock.patch.object(ls, "current_run", return_value=busy), \
                mock.patch.object(ls, "sweep_running", return_value=sweep), mock.patch.object(ls, "budget_gate", return_value=None), \
                mock.patch.object(calendar_refresh, "precheck", return_value=why):
            ls.Handler.ask(h, dict({"message": "hello"}, **req))
        return h, runs

    def test_panel_kind_routes_only_and_panel_sweep_keeps_the_words(self):
        ls = self.ls
        for ok in ("refresh calendar", "Refresh the calendar", "please refresh my calendar now.", "refresh my calendar please!"):
            self.assertEqual(ls.panel_kind(ok), "calendar", ok)
            self.assertTrue(ls.panel_sweep(ok), ok)                          # the budget gate and the queue still exempt it
        for ok in ("sweep", "sweep mail for ABC", "check my mail", "sweep the UAT plan thread"):
            self.assertEqual(ls.panel_kind(ok), "sweep", ok)
        for no in ("refresh calendar and apply", "refresh calendar for ABC", "refreshing calendar", "x" * 130, "tell me about it"):
            self.assertIsNone(ls.panel_kind(no), no)
        self.assertIsNone(ls.panel_kind("refresh calendar", images=["a.png"]))
        self.assertIsNone(ls.panel_kind("refresh calendar", confirmed="Add action"))

    def test_a_typed_refresh_starts_the_calendar_run_with_its_fixed_prompt_and_no_chat(self):
        import calendar_refresh
        h, runs = self.ask({"message": "refresh calendar", "session": "s-1", "chat": "c-1", "kind": "ask"})
        self.assertEqual(len(runs), 1)
        a, kw = runs[0]
        self.assertEqual(kw["kind"], "calendar")
        self.assertEqual(a[1], calendar_refresh.build_prompt())               # never the typed words
        self.assertEqual(a[2:5], (None, None, None))                          # no session, no chat, no confirmation
        self.assertIsNotNone(getattr(h, "followed", None))

    def test_a_sweep_running_is_a_409_with_the_plain_sentence_and_no_run(self):
        h, runs = self.ask({"message": "refresh calendar"}, sweep=True)
        self.assertEqual(runs, [])
        self.assertEqual(h.sent[0], 409)
        self.assertEqual(h.sent[1]["message"], "A mail check is running; try again when it ends.")

    def test_a_precheck_failure_is_a_400_with_its_own_reason(self):
        h, runs = self.ask({"message": "refresh calendar"}, why="the calendar source is off")
        self.assertEqual(runs, [])
        self.assertEqual((h.sent[0], h.sent[1]["message"]), (400, "the calendar source is off"))

    def test_a_run_already_going_is_the_existing_409(self):
        h, runs = self.ask({"message": "refresh calendar"}, busy=mock.Mock(done=False, summary=lambda: {"id": "r-1"}))
        self.assertEqual(runs, [])
        self.assertEqual(h.sent[0], 409)

    def test_anything_more_is_a_plain_chat_or_sweep_not_the_calendar_run(self):
        for msg in ("refresh calendar and apply", "refresh calendar for ABC", "sweep"):
            h, runs = self.ask({"message": msg})
            self.assertEqual(len(runs), 1, msg)
            self.assertNotEqual(runs[0][1].get("kind"), "calendar", msg)

    def test_a_queued_refresh_starts_the_calendar_run_too(self):
        import calendar_refresh
        ls, runs = self.ls, []
        q = {"chat": "c-1", "items": [{"id": "1", "text": "refresh calendar", "images": []}], "held": False}
        with mock.patch.object(ls, "Run", side_effect=lambda *a, **kw: runs.append((a, kw)) or mock.Mock(summary=lambda: {})), \
                mock.patch.object(ls, "queue_save"), mock.patch.object(ls, "budget_gate", return_value=None), \
                mock.patch.object(ls, "sweep_running", return_value=False), mock.patch.object(ls, "ask_image_files", return_value=None), \
                mock.patch.object(calendar_refresh, "precheck", return_value=None):
            ls.queue_start(q, mock.Mock(done=True, kind="ask", chat="c-1", session="s"))
        self.assertEqual(runs[0][1]["kind"], "calendar")
        self.assertEqual(runs[0][0][1], calendar_refresh.build_prompt())

    def test_a_sweep_run_never_adds_the_home_folder_and_keeps_the_projects_root(self):
        ls = self.ls
        with mock.patch.object(ls, "extra_dirs", return_value=["/x/projects"]), \
                mock.patch.object(ls.reach, "home", return_value=Path("/x/home")):
            self.assertEqual(ls.run_dirs("sweep", True), ["/x/projects"])
            self.assertIn("/x/home", ls.run_dirs("ask", True))                # a plain chat is unchanged

    def test_both_sweep_prompts_end_with_the_followed_people_rule_text(self):
        ls = self.ls
        rule = ls.VIP_PRIVATE_RULE
        self.assertGreater(len(rule), 100)
        self.assertIn("never call or label a person a VIP", rule)
        for name, prompt in (("typed", ls.PANEL_SWEEP_PROMPT), ("close the day", ls.KIND_PROMPTS["sweep"])):
            self.assertTrue(prompt.endswith(rule), name)

    def test_the_budget_gate_still_reads_panel_sweep(self):
        gate = SRC[SRC.index("def budget_gate("):SRC.index("CARRY_TURNS")]
        self.assertIn('panel_sweep(req.get("message")', gate)

    def test_calendar_is_a_known_kind(self):
        for needle in ('KIND_ARGS["calendar"]', '"calendar": "calendar"'):
            self.assertIn(needle, SRC)

    def test_ask_and_queue_text_routes(self):
        ask = SRC[SRC.index("    def ask(self, req):"):SRC.index("sweep = panel_sweep(message")]
        self.assertIn('panel_kind(message, images, req.get("confirmed")) == "calendar"', ask)
        q = SRC[SRC.index("def queue_start("):SRC.index("def queue_after(")]
        self.assertIn('panel_kind(item["text"], images) == "calendar"', q)

    def test_usage_report_lists_a_label_and_kind_per_run(self):
        import usage_report
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


if __name__ == "__main__":
    unittest.main()
