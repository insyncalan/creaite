"""BL-267: an unconfirmed ask creaite chat never changes the record. reach.SCRIPT_COMMANDS classifies every command of every
creaite script (read, derived, stage, guarded or record); the guard hook refuses a record command unless the run is a confirmed
request, and doctor counts the refusals.

- Every script with a command line is in the list, and every command its dispatcher accepts is classified (found by reading
  the dispatcher: `cmd == "…"`, `cmd in (…)`, `argv[:1] == ["…"]`, `add_parser("…")`), so a new one fails here until someone
  decides; and nothing classified is stale.
- In a plain chat the hook refuses every record command (directly and through the system/scripts/run wrapper) and lets the
  others through; in a confirmed run it lets them all through; --dry-run and --check make the commands that have them read
  only; an unknown command is refused (fails closed).
- A refusal is logged by name, and doctor's "Record changes refused in a plain chat" counts it.

Run: python3 dev/tests/test_record_commands.py     (quick tier: no Chrome)
"""
import ast
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "system" / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import reach  # noqa: E402
from test_tracker import Vault  # noqa: E402

SUB_DISPATCHERS = {"main_people": "people", "main_ws": "workstreams", "main_recode": None}   # second words; recode has none


def _is_cmd(n):
    if isinstance(n, ast.Name) and n.id == "cmd" or isinstance(n, ast.Attribute) and n.attr == "cmd":
        return True
    if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) and n.value.id == "argv":
        s = n.slice
        return isinstance(s, ast.Constant) and s.value == 0 or isinstance(s, ast.Slice) and s.lower is None and \
            isinstance(s.upper, ast.Constant) and s.upper.value == 1
    return False


def _strings(n):
    if isinstance(n, ast.Constant) and isinstance(n.value, str):
        return [n.value]
    if isinstance(n, (ast.Tuple, ast.List, ast.Set)):
        return [x for e in n.elts for x in _strings(e)]
    return []


def _words(fn):
    found = set()
    for n in ast.walk(fn):
        if isinstance(n, ast.Compare) and _is_cmd(n.left):
            for c in n.comparators:
                found.update(_strings(c))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "add_parser" and n.args:
            found.update(_strings(n.args[0]))
    return found


def dispatched():
    """{script: {command, …}} for every script in system/scripts/ with a command line, read from its dispatchers."""
    out = {}
    for f in sorted(SCRIPTS.glob("*.py")):
        text = f.read_text(encoding="utf-8")
        if '__name__ == "__main__"' not in text:
            continue
        names = set()
        for fn in ast.parse(text).body:
            if not isinstance(fn, ast.FunctionDef):
                continue
            if fn.name == "main" or fn.name.startswith("_main"):
                names |= _words(fn)
            elif fn.name.startswith("main_"):
                if fn.name not in SUB_DISPATCHERS:
                    names.add(f"<unmapped sub-dispatcher {fn.name}>")
                elif SUB_DISPATCHERS[fn.name]:
                    names |= {f"{SUB_DISPATCHERS[fn.name]} {w}" for w in _words(fn)}
        out[f.name] = names
    return out


def command(script, *words, wrapped=False):
    head = f"system/scripts/run {script}" if wrapped else f"python3 system/scripts/{script}"
    return " ".join([head, *words])


class Classified(unittest.TestCase):
    def test_every_script_and_command_is_classified(self):
        found = dispatched()
        self.assertEqual(sorted(set(found) - set(reach.SCRIPT_COMMANDS)), [],
                         "scripts with a command line that BL-267's list (reach.SCRIPT_COMMANDS) doesn't classify")
        missing = sorted(f"{s} {c}" for s, cmds in found.items() for c in cmds
                         if "" not in reach.SCRIPT_COMMANDS[s] and c not in reach.SCRIPT_COMMANDS[s])
        self.assertEqual(missing, [], "commands not classified in reach.SCRIPT_COMMANDS: decide read, derived, stage, guarded "
                                      "or record")

    def test_nothing_classified_is_stale(self):
        found = dispatched()
        stale = sorted(f"{s} {c}" for s, table in reach.SCRIPT_COMMANDS.items() for c in table
                       if s not in found or c and c not in found[s] and c.split()[0] not in found[s])
        self.assertEqual(stale, [])
        self.assertEqual({k for t in reach.SCRIPT_COMMANDS.values() for v in t.values()
                          for k in ([v[0]] if isinstance(v, tuple) else [v])} - {"read", "derived", "stage", "guarded", "record"},
                         set())

    def test_the_record_commands_are_the_ones_alan_named(self):
        """The commands that change the record, as decided for BL-267 (12-10-2026). A change here is a security decision."""
        record = sorted(f"{s} {c}".strip() for s, t in reach.SCRIPT_COMMANDS.items() for c, v in t.items()
                        if (v[0] if isinstance(v, tuple) else v) == "record")
        self.assertEqual(record, sorted([
            "tracker.py init", "tracker.py apply", "tracker.py undo", "tracker.py undo-changes", "tracker.py migrate",
            "review.py approve", "review.py reject", "review.py bulk", "review.py assign", "review.py edit",
            "review.py workstream", "review.py keep", "review.py override", "review.py merge", "review.py keep-new",
            "review.py retarget", "review.py unmerge",          # BL-297 (13-10-2026): classed as merge is
            "review.py unreject", "review.py rereason", "review.py approve-instead",   # BL-315 (v1.9.2): classed as reject is
            "propose.py stage", "propose.py recode", "propose.py setting", "propose.py learn", "propose.py register-columns",
            "propose.py people add", "propose.py people edit", "propose.py people rename", "propose.py people merge",
            "propose.py people map", "propose.py people migrate", "propose.py workstreams add",
            "propose.py workstreams retire-settings",
            "minutes.py baseline", "excel_sync.py import",
            "update.py install", "update.py undo", "update.py tidy", "update.py new-vault",
            "backup.py tidy", "backup.py restore",            # BL-323 (14-10-2026): removes old backups for good; restores the vault
            "permissions.py", "live_server.py", "launch.py"]))


class Hook(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        cls.v.run("init")

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def decide(self, commands, mode):
        """{command: (allowed, reason)} from reach.hook_decision, run in the throwaway vault."""
        code = ("import json, sys; sys.path.insert(0, 'system/scripts'); import reach; "
                "print(json.dumps({c: reach.hook_decision('Bash', {'command': c}, sys.argv[1], 'r-1') "
                "for c in json.loads(sys.stdin.read())}))")
        import subprocess
        r = subprocess.run([sys.executable, "-c", code, mode], input=json.dumps(commands), cwd=self.v.root,
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    RECORD = [("tracker.py", "apply"), ("tracker.py", "undo"), ("tracker.py", "undo-changes", "3"), ("tracker.py", "migrate"),
              ("tracker.py", "init"), ("review.py", "approve", "1-3"), ("review.py", "reject", "2", "--reason=Duplicate"),
              ("review.py", "bulk", "ABC"), ("review.py", "assign", "4", "ABC"), ("review.py", "edit", "4", "owner=Sara"),
              ("review.py", "merge", "5"), ("review.py", "keep-new", "5"), ("review.py", "keep", "6"),
              ("propose.py", "stage", "system/staging/drafts/x.json"), ("propose.py", "recode", "ABC", "XYZ"),
              ("propose.py", "learn", "ABC", "sender", "a@b.com"), ("propose.py", "people", "add", "--name", "'Sara Khan'"),
              ("propose.py", "workstreams", "add", "ABC", "Data"), ("minutes.py", "baseline", "ABC", "--all"),
              ("excel_sync.py", "import"), ("update.py", "install", "system/releases/creaite-1.7.0.zip"),
              ("tracker.py", "frobnicate")]
    OTHERS = [("tracker.py", "read", "ABC"), ("tracker.py", "query", "--sql", "'SELECT 1'"), ("tracker.py", "validate",
              "system/staging/proposed-x.json"), ("tracker.py", "index"), ("tracker.py",), ("review.py", "pending"),
              ("review.py", "list", "--json"), ("review.py", "assign", "4", "ABC", "--dry-run"),
              ("propose.py", "preview", "system/staging/drafts/x.json"), ("propose.py", "fields", "actions"),
              ("propose.py", "recode", "ABC", "XYZ", "--dry-run"), ("propose.py", "learn", "ABC", "sender", "a@b.com", "--check"),
              ("propose.py", "people", "list"), ("propose.py", "workstreams", "list", "--project", "ABC"),
              ("minutes.py", "stage", "system/staging/drafts/m.json"), ("minutes.py", "baseline", "ABC", "--all", "--dry-run"),
              ("sweep.py", "stage", "system/staging/drafts/s.json"), ("report.py", "weekly-stage", "system/staging/drafts/w.json"),
              ("excel_sync.py", "export"), ("build_dashboard.py",), ("doctor.py",), ("session.py", "start"),
              ("filechange.py", "list"), ("search.py", "query", "vendor")]

    def test_a_plain_chat_is_refused_every_record_command(self):
        for wrapped in (False, True):
            got = self.decide([command(*c, wrapped=wrapped) for c in self.RECORD], "ask")
            for c, (ok, why) in got.items():
                with self.subTest(c):
                    self.assertFalse(ok, c)
                    self.assertIn("CONFIRM:", why)

    def test_a_plain_chat_may_still_read_stage_and_rebuild(self):
        got = self.decide([command(*c) for c in self.OTHERS], "ask")
        for c, (ok, why) in got.items():
            with self.subTest(c):
                self.assertTrue(ok, f"{c}: {why}")

    def test_a_confirmed_run_may_change_the_record(self):
        got = self.decide([command(*c) for c in self.RECORD[:-1] + self.OTHERS], "confirmed")
        for c, (ok, why) in got.items():
            with self.subTest(c):
                self.assertTrue(ok, f"{c}: {why}")

    def test_any_mode_but_confirmed_is_a_plain_chat(self):
        got = self.decide([command("tracker.py", "apply")], "")
        self.assertFalse(got[command("tracker.py", "apply")][0])

    def test_the_bash_checks_still_come_first(self):
        """A record command with shell characters is refused for its shape, as before BL-267, in either mode."""
        c = "python3 system/scripts/tracker.py apply | tail"
        for mode in ("ask", "confirmed"):
            ok, why = self.decide([c], mode)[c]
            self.assertFalse(ok)
            self.assertIn("shell characters", why)

    def test_a_refusal_is_logged_and_doctor_counts_it(self):
        own = Vault()                                      # its own vault: the class's has the other tests' refusals
        self.addCleanup(own.cleanup)
        own.run("init")
        self.v, shared = own, self.v
        self.addCleanup(setattr, self, "v", shared)
        self.decide([command("tracker.py", "apply"), command("tracker.py", "apply"), command("review.py", "approve", "1")], "ask")
        import subprocess
        r = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, 'system/scripts'); import doctor; "
                            "print(doctor.record_refusals()[1])"], cwd=self.v.root, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("2 × tracker.py apply", r.stdout)
        self.assertIn("1 × review.py approve", r.stdout)


if __name__ == "__main__":
    unittest.main()
