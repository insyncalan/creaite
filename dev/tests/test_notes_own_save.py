"""#119 (Alan, 17-10-2026): Alan's own note save is not an ask creaite run's change.

Run: python3 dev/tests/test_notes_own_save.py

filechange.perform takes `own`, which only the live server's notes save route passes (the route builds the change itself and
never reads `own` from a request):
  - in a run that has already changed ten files, a note save waits for approval (as before); with `own` it is made, with no run
    tag in the log, so it is not counted against the run;
  - in a run marked by outside content, the same: `own` makes the note save at once;
  - `own` is honoured for an edit of a note and nothing else: not a create, not another file, never a settings file, and the
    never list still refuses;
  - the source: the notes save route passes own=True once; nothing in the live server reads `own` from a request; the default of
    perform's `own` is False.
"""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_tracker import ABC, Vault  # noqa: E402

NOTE = f"{ABC}/notes/Plan.md"
WHY = "a note saved in the Notes tab"


class OwnSave(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        for n in range(12):
            p = self.v.root / ABC / "notes" / f"N{n}.md"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("---\ntitle: N\n---\nbefore\n", encoding="utf-8")
        p = self.v.root / NOTE
        p.write_text("---\ntitle: Plan\n---\nbefore\n", encoding="utf-8")

    def tearDown(self):
        self.v.cleanup()

    def py(self, code):
        src = f"import sys, json; sys.path.insert(0, {str(self.v.root / 'system/scripts')!r})\nimport filechange, reach\n{code}"
        r = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True, cwd=tempfile.gettempdir())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def write_run(self, marked):
        guard = self.v.root / "system/guard"
        guard.mkdir(parents=True, exist_ok=True)
        (guard / "run.json").write_text(json.dumps({"run": "r-test", "mode": "chat", "marked": ["used outlook_email_search"]
                                                    if marked else []}), encoding="utf-8")

    def perform(self, path, data=b"after\n", op="edit", own=None, **extra):
        ch = {"op": op, "path": path, "data": data, "why": WHY, **extra}
        kw = ", via='dashboard'" + (f", own={own!r}" if own is not None else "")
        return self.py(f"print(json.dumps(filechange.perform({ch!r}{kw})))")

    def log(self):
        p = self.v.root / "system/config/files-log.jsonl"
        return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []

    def fill_run_with_ten_changes(self):
        """A run that has already changed ten files (by the run's own tag), so the eleventh is over the limit."""
        self.write_run(marked=False)
        for n in range(10):
            code, msg = self.py(f"print(json.dumps(filechange.perform({{'op': 'edit', 'path': {ABC + '/notes/N' + str(n) + '.md'!r}, "
                                f"'data': b'x\\n', 'why': {WHY!r}}}, via='cli', run='r-test')))")
            self.assertEqual(code, 0, msg)

    # ── the behaviour ──
    def test_the_eleventh_save_in_a_run_waits_unless_it_is_alans_own(self):
        self.fill_run_with_ten_changes()
        code, msg = self.perform(NOTE)
        self.assertEqual(code, 3, msg)
        self.assertIn("already changed", msg)
        code, msg = self.perform(NOTE, own=True)
        self.assertEqual(code, 0, msg)
        last = self.log()[-1]
        self.assertEqual(last["path"], NOTE)
        self.assertNotIn("run", last, "an own save carries no run tag, so it isn't counted against the run")

    def test_a_note_save_in_a_run_marked_by_outside_content_is_made_when_it_is_alans_own(self):
        self.write_run(marked=True)
        code, msg = self.perform(NOTE)
        self.assertEqual(code, 3, msg)
        code, msg = self.perform(NOTE, own=True)
        self.assertEqual(code, 0, msg)
        self.assertNotIn("run", self.log()[-1])

    def test_own_is_honoured_for_an_edit_of_a_note_and_nothing_else(self):
        self.write_run(marked=True)
        doc = f"{ABC}/documents/Plan.md"
        (self.v.root / doc).parent.mkdir(parents=True, exist_ok=True)
        (self.v.root / doc).write_text("x\n", encoding="utf-8")
        code, msg = self.perform(doc, own=True)
        self.assertEqual(code, 3, "another file is not a note: " + msg)
        code, msg = self.perform(f"{ABC}/notes/New.md", op="create", own=True)
        self.assertEqual(code, 3, "a create is not an edit: " + msg)
        code, msg = self.perform(".claude/settings.json", own=True)
        self.assertIn(code, (1, 3), "a settings file is never made by own: " + msg)
        code, msg = self.perform("system/scripts/reach.py", own=True)
        self.assertEqual(code, 1, "the never list still refuses: " + msg)

    def test_the_source_never_reads_own_from_a_request(self):
        live = (HERE.parent.parent / "system/scripts/live_server.py").read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r"own=True", live)), 1, "only the notes save route passes own=True")
        route = live[live.index("def notes_save_route"):]
        route = route[:route.index("\ndef ", 10)]
        self.assertIn("own=True", route)
        calls = re.findall(r"filechange\.perform\((?:[^()]|\([^()]*\)|\{[^{}]*\})*\)", live, re.S)
        self.assertTrue(calls)
        with_own = [c for c in calls if re.search(r"\bown\s*=", c)]
        self.assertEqual(len(with_own), 1, "only the notes save route passes own to filechange.perform")
        self.assertIn("own=True", with_own[0])
        self.assertNotIn('get("own")', route, "the route never reads own from the request")
        fc = (HERE.parent.parent / "system/scripts/filechange.py").read_text(encoding="utf-8")
        self.assertIn('def perform(ch, approval=None, via="cli", run=None, own=False):', fc)
        self.assertIn('return bool(own) and op == "edit" and paths.is_note(target)', fc)


if __name__ == "__main__":
    unittest.main()
