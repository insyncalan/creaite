"""BL-96, BL-141: ask creaite edits the permission files, each change on Alan's approval.

Run: python3 dev/tests/test_permission_file.py
Two halves. UnitTests drive permissions.py's begin_file_edit / finish_file_edit / recover / undo in a throwaway vault (kept: the
server still puts back deny entries a cut-short run left lifted). ServerTests run the real live server with a stand-in `claude`
(CREAITE_CLAUDE) that prepares the new file and asks filechange.py to make it, as ask creaite does since BL-141: the change waits
on the one card, and the server makes exactly what was shown, re-checked, or nothing.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import free_port  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_tracker import Vault  # noqa: E402

SETTINGS = ".claude/settings.json"
LOCAL = ".claude/settings.local.json"
CONFIG = "system/config/settings.json"
PROTECTED = ["Edit(.claude/settings.json)", "Edit(.claude/settings.local.json)"]       # the Write(...) pair was retired in v1.2.0


def read(v, rel):
    return json.loads((v.root / rel).read_text(encoding="utf-8"))


def deny(v):
    return read(v, SETTINGS)["permissions"]["deny"]


class UnitTests(unittest.TestCase):
    def setUp(self):
        self.v = Vault()

    def tearDown(self):
        self.v.cleanup()

    def py(self, code):
        src = f"import sys, json; sys.path.insert(0, {str(self.v.root / 'system/scripts')!r}); import permissions as P\n{code}"
        r = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True, cwd=tempfile.gettempdir())
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1]) if r.stdout.strip() else None

    def edit(self, path, change, why="Alan asked"):
        """begin, run `change` (python source that edits files like the confirmed run would) and finish, in one process."""
        return self.py(f"""st = P.begin_file_edit({path!r})
lifted_now = json.load(open(P.paths.CLAUDE_SETTINGS))['permissions']['deny']
{change}
ok, msg = P.finish_file_edit(st, {why!r})
print(json.dumps([ok, msg, st['lifted'], lifted_now]))""")

    def undo(self, ok=True):
        return self.v.run("undo", script="permissions.py", ok=ok)

    def test_only_that_files_denies_are_lifted_during_the_run_and_all_come_back(self):
        before = deny(self.v)
        ok, msg, lifted, during = self.edit(SETTINGS, "pass")
        self.assertEqual(lifted, ["Edit(.claude/settings.json)"])
        for d in lifted:
            self.assertNotIn(d, during)                                       # lifted for the run
        for d in before:
            if d not in lifted:
                self.assertIn(d, during)                                      # everything else stays denied, including the other files
        self.assertEqual((ok, msg), (True, "No change was made to .claude/settings.json."))
        self.assertEqual(deny(self.v), before)                                # all back, in the same order
        self.assertFalse((self.v.root / "system/staging/deny-lifted.json").exists())

    def test_a_narrow_rule_is_kept_logged_backed_up_and_undoable(self):
        orig = (self.v.root / SETTINGS).read_text()
        ok, msg, _, _ = self.edit(SETTINGS, """d = json.load(open(P.paths.CLAUDE_SETTINGS)); d['permissions']['allow'].append('Read(inbox/**)')
json.dump(d, open(P.paths.CLAUDE_SETTINGS, 'w'), indent=2)""")
        self.assertTrue(ok, msg)
        self.assertIn("Changed .claude/settings.json (change 1; the file before is system/backups/permfile-settings-", msg)
        now = read(self.v, SETTINGS)["permissions"]
        self.assertIn("Read(inbox/**)", now["allow"])
        for d in PROTECTED:
            self.assertIn(d, now["deny"])                                     # the safety entries are back after the edit
        entry = json.loads((self.v.root / "system/config/permissions-log.jsonl").read_text().splitlines()[-1])
        self.assertEqual((entry["op"], entry["file"], entry["why"], entry["via"]), ("file", "settings", "Alan asked", "dashboard"))
        self.assertIn(".claude/settings.json edited", self.v.run("list", script="permissions.py").stdout)
        self.undo()
        self.assertNotIn("Read(inbox/**)", read(self.v, SETTINGS)["permissions"]["allow"])
        for d in PROTECTED:
            self.assertIn(d, deny(self.v))
        self.assertEqual(sorted(json.loads(orig)["permissions"]["allow"]), sorted(read(self.v, SETTINGS)["permissions"]["allow"]))

    def test_a_rule_already_listed_is_not_listed_twice(self):
        rule = "Bash(python3 system/scripts/filechange.py *)"
        allow = read(self.v, SETTINGS)["permissions"]["allow"]
        self.assertEqual(allow.count(rule), 1)
        orig = (self.v.root / SETTINGS).read_text()
        add = lambda *rules: f"""d = json.load(open(P.paths.CLAUDE_SETTINGS)); d['permissions']['allow'].extend({list(rules)!r})
json.dump(d, open(P.paths.CLAUDE_SETTINGS, 'w'), indent=2)"""
        ok, msg, _, _ = self.edit(SETTINGS, add(rule))                         # only a repeat: a no-op that says so
        self.assertEqual((ok, msg), (True, f"No change was made to .claude/settings.json. {rule} is already listed."))
        self.assertEqual(read(self.v, SETTINGS)["permissions"]["allow"], allow)
        self.assertEqual(json.loads(orig), read(self.v, SETTINGS))
        ok, msg, _, _ = self.edit(SETTINGS, add(rule, "Read(inbox/**)", "Read(inbox/**)"))     # a new rule beside a repeat, and a new rule twice
        self.assertTrue(ok, msg)
        self.assertIn(f"Not listed twice: {rule}, Read(inbox/**).", msg)
        now = read(self.v, SETTINGS)["permissions"]["allow"]
        self.assertEqual((now.count(rule), now.count("Read(inbox/**)")), (1, 1))
        self.undo()
        self.assertEqual(read(self.v, SETTINGS)["permissions"]["allow"], allow)
        # a repeat that was already in the file is left as it was
        d = read(self.v, SETTINGS)
        d["permissions"]["allow"].append(rule)
        (self.v.root / SETTINGS).write_text(json.dumps(d, indent=2))
        ok, msg, _, _ = self.edit(SETTINGS, add("Read(inbox/**)"))
        self.assertTrue(ok, msg)
        self.assertEqual(read(self.v, SETTINGS)["permissions"]["allow"].count(rule), 2)

    def test_a_blanket_rule_a_skip_mode_or_a_removed_safety_entry_is_refused_and_the_file_put_back(self):
        orig = (self.v.root / SETTINGS).read_text()
        for change, why in (("d['permissions']['allow'].append('Write(*)')", "blanket"),
                            ("d['permissions']['allow'].append('Bash')", "blanket"),
                            ("d['permissions']['allow'].append('Edit(~/**)')", "blanket"),
                            ("d['permissions']['allow'].append('Write(~/Documents/**)')", "outside the vault"),
                            ("d['permissions']['allow'].append('Bash(node x.js)')", "creaite script"),
                            ("d['permissions']['defaultMode'] = 'bypassPermissions'", "skips permissions"),
                            ("d['permissions']['additionalDirectories'] = ['~']", "home folder"),
                            ("d['permissions']['deny'].remove('Bash(curl *)')", "keeps the panel out"),
                            ("d['permissions']['deny'].remove('WebFetch')", "keeps the panel out"),
                            ("d['permissions']['deny'].remove('Edit(system/tracker.db)')", "keeps the panel out")):
            ok, msg, _, _ = self.edit(SETTINGS, f"""d = json.load(open(P.paths.CLAUDE_SETTINGS)); {change}
json.dump(d, open(P.paths.CLAUDE_SETTINGS, 'w'), indent=2)""")
            self.assertFalse(ok, change)
            self.assertIn(why, msg, change)
            self.assertIn(".claude/settings.json is as it was", msg)
            self.assertEqual(json.loads((self.v.root / SETTINGS).read_text()), json.loads(orig), change)
        self.assertEqual(self.v.run("list", "--json", script="permissions.py").stdout.count('"op": "file"'), 0)    # nothing was logged as kept

    def test_broken_json_or_a_deleted_file_is_put_back(self):
        orig = (self.v.root / SETTINGS).read_text()
        ok, msg, _, _ = self.edit(SETTINGS, "open(P.paths.CLAUDE_SETTINGS, 'w').write('{ nope')")
        self.assertFalse(ok)
        self.assertIn("no longer valid JSON", msg)
        self.assertEqual(json.loads((self.v.root / SETTINGS).read_text()), json.loads(orig))
        ok, msg, _, _ = self.edit(SETTINGS, "P.paths.CLAUDE_SETTINGS.unlink()")
        self.assertFalse(ok)
        self.assertIn("was deleted", msg)
        self.assertTrue((self.v.root / SETTINGS).exists())

    def test_the_local_file_is_created_and_the_settings_file_is_left_as_it_was(self):
        self.assertFalse((self.v.root / LOCAL).exists())
        before = (self.v.root / SETTINGS).read_text()
        ok, msg, lifted, during = self.edit(LOCAL, """json.dump({'permissions': {'allow': ['Read(inbox/**)']}}, open(P.paths.ROOT / '.claude/settings.local.json', 'w'))""")
        self.assertTrue(ok, msg)
        self.assertEqual(lifted, ["Edit(.claude/settings.local.json)"])
        self.assertEqual(read(self.v, LOCAL)["permissions"]["allow"], ["Read(inbox/**)"])
        self.assertEqual(json.loads((self.v.root / SETTINGS).read_text()), json.loads(before))      # the lifted entries are back
        self.undo()
        self.assertFalse((self.v.root / LOCAL).exists())                                            # there was none before

    def test_a_run_that_also_touches_the_settings_file_is_refused(self):
        orig = (self.v.root / SETTINGS).read_text()
        ok, msg, _, _ = self.edit(LOCAL, """json.dump({'permissions': {'allow': []}}, open(P.paths.ROOT / '.claude/settings.local.json', 'w'))
d = json.load(open(P.paths.CLAUDE_SETTINGS)); d['permissions']['allow'].append('Read(inbox/**)')
json.dump(d, open(P.paths.CLAUDE_SETTINGS, 'w'), indent=2)""")
        self.assertFalse(ok)
        self.assertIn("changed .claude/settings.json as well", msg)
        self.assertFalse((self.v.root / LOCAL).exists())
        for d in PROTECTED:
            self.assertIn(d, deny(self.v))                                                           # and the lift is undone either way

    def test_the_config_file_is_edited_with_no_deny_to_lift(self):
        cfg = self.v.root / CONFIG
        before = json.loads(cfg.read_text())
        ok, msg, lifted, _ = self.edit(CONFIG, """d = json.load(open(P.paths.SETTINGS)); d['sweep']['due_from'] = '06:15'
json.dump(d, open(P.paths.SETTINGS, 'w'), indent=2)""")
        self.assertTrue(ok, msg)
        self.assertEqual(lifted, [])
        self.assertEqual(json.loads(cfg.read_text())["sweep"]["due_from"], "06:15")
        self.undo()
        self.assertEqual(json.loads(cfg.read_text()), before)
        ok, msg, _, _ = self.edit(CONFIG, """d = json.load(open(P.paths.SETTINGS)); d['permissions'] = {'allow': ['Write(*)']}
json.dump(d, open(P.paths.SETTINGS, 'w'), indent=2)""")
        self.assertFalse(ok)
        self.assertEqual(json.loads(cfg.read_text()), before)

    def test_undo_leaves_a_file_alone_if_it_changed_since(self):
        self.edit(SETTINGS, """d = json.load(open(P.paths.CLAUDE_SETTINGS)); d['permissions']['allow'].append('Read(inbox/**)')
json.dump(d, open(P.paths.CLAUDE_SETTINGS, 'w'), indent=2)""")
        d = read(self.v, SETTINGS)
        d["permissions"]["allow"].append("Read(system/search/**)")
        (self.v.root / SETTINGS).write_text(json.dumps(d))
        r = self.undo(ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Read(system/search/**)", read(self.v, SETTINGS)["permissions"]["allow"])

    def test_a_run_cut_short_is_recovered_and_the_database_and_engine_are_not_targets(self):
        self.py("P.begin_file_edit('.claude/settings.json')")
        self.assertNotIn("Edit(.claude/settings.json)", deny(self.v))                  # lifted, and the process is gone
        self.assertTrue((self.v.root / "system/staging/deny-lifted.json").exists())
        self.assertIn("Put the lifted", self.v.run("recover", script="permissions.py").stdout)
        for d in PROTECTED:
            self.assertIn(d, deny(self.v))
        self.assertIn("Nothing to recover", self.v.run("recover", script="permissions.py").stdout)
        for path in ("system/tracker.db", "system/scripts/tracker.py", "system/scripts/permissions.py", "system/scripts/paths.py", "../x", "CLAUDE.md"):
            r = subprocess.run([sys.executable, "-c", f"import sys; sys.path.insert(0, {str(self.v.root / 'system/scripts')!r}); import permissions as P; P.begin_file_edit({path!r})"],
                               capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0, path)
            self.assertIn("not a permission file", r.stderr)


FAKE = r'''#!/usr/bin/env python3
"""A stand-in `claude`: records the flags it was given and the settings.json it saw, then makes the edit tests script."""
import json, sys
from pathlib import Path
args = sys.argv[1:]
message = args[args.index("-p") + 1]
allowed = args[args.index("--allowedTools") + 1].split(",")
disallowed = args[args.index("--disallowedTools") + 1].split(",")
system = args[args.index("--append-system-prompt") + 1]
here = Path(__file__).resolve().parent
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": "sess-pf-1"})
text = "Done."
plan = json.loads((here / "fake_plan.json").read_text()) if (here / "fake_plan.json").exists() else {}
if "ask to edit" in message:
    import subprocess
    (here / "fake_seen.json").write_text(json.dumps({"allowed": allowed, "disallowed": disallowed, "prompt": system}))
    target = Path(plan["file"]) if plan["file"].startswith("/") else here / plan["file"]
    try:
        d = json.loads(target.read_text()) if target.is_file() else {}
    except (ValueError, UnicodeDecodeError):
        d = {}
    exec(plan["change"], {"d": d, "json": json})
    draft = here / "system/staging/drafts/permfile.json"
    draft.parent.mkdir(parents=True, exist_ok=True)
    draft.write_text(json.dumps(d, indent=2))
    if plan.get("mode") == "sleep":
        import time; time.sleep(30)
    r = subprocess.run([sys.executable, str(here / "system/scripts/filechange.py"), "edit" if target.exists() else "create", plan["file"], "--from",
                        "system/staging/drafts/permfile.json", "--why", plan["why"]], capture_output=True, text=True, cwd=here)
    text = "Waiting for your approval. " + r.stdout.strip()
out({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}})
out({"type": "result", "session_id": "sess-pf-1", "result": text})
'''


def events(resp):
    out = []
    for raw in resp:
        line = raw.decode().strip()
        if line.startswith("data: "):
            out.append(json.loads(line[6:]))
    return out


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = v = Vault()
        populate(v)
        fake = v.root / "fake_claude.py"
        fake.write_text(FAKE)
        fake.chmod(0o755)
        cls.plan = v.root / "fake_plan.json"
        cls.port = free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.env = {**os.environ, "CREAITE_PORT": str(cls.port), "CREAITE_CLAUDE": str(fake)}
        cls.start()
        cls.original = (v.root / SETTINGS).read_text()
        cls.config = (v.root / CONFIG).read_text()

    @classmethod
    def start(cls):
        cls.proc = subprocess.Popen([sys.executable, str(cls.v.root / "system/scripts/live_server.py")], env=cls.env,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            try:
                urllib.request.urlopen(cls.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        html = urllib.request.urlopen(cls.base + "/").read().decode()
        cls.token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.v.cleanup()

    def setUp(self):
        (self.v.root / SETTINGS).write_text(self.original)
        (self.v.root / CONFIG).write_text(self.config)
        (self.v.root / LOCAL).unlink(missing_ok=True)
        for f in ("system/config/permissions-log.jsonl", "system/config/settings-log.jsonl", "fake_seen.json", "fake_plan.json"):
            (self.v.root / f).unlink(missing_ok=True)

    def ask(self, message, **extra):
        req = urllib.request.Request(self.base + "/api/ask", data=json.dumps({"message": message, **extra}).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, events(r)
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def request(self, path, why, change, **plan):
        self.plan.write_text(json.dumps({"file": path, "why": why, "change": change, **plan}))
        status, ev = self.ask("ask to edit permissions")
        return next((e for e in ev if e["type"] == "changes"), None), ev

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        return json.loads(urllib.request.urlopen(req, timeout=60).read())

    def approve(self, card):
        return self.post("/api/changes/approve", {"card": card["card"]})

    def seen(self):
        return json.loads((self.v.root / "fake_seen.json").read_text())

    def test_a_run_asks_for_one_file_and_nothing_is_changed_by_asking(self):
        card, ev = self.request(SETTINGS, "Add Read(inbox/**) to allow", "d['permissions']['allow'].append('Read(inbox/**)')")
        self.assertEqual([(i["op"], i["path"], i["why"]) for i in card["items"]], [("edit", SETTINGS, "Add Read(inbox/**) to allow")])
        self.assertTrue(any(ln.startswith("+") and "Read(inbox/**)" in ln for ln in card["items"][0]["diff"]))
        self.assertEqual((self.v.root / SETTINGS).read_text(), self.original)

    def test_the_approved_change_is_made_exactly_and_the_safety_entries_stay(self):
        card, _ = self.request(SETTINGS, "Add Read(inbox/**) to allow", "d['permissions']['allow'].append('Read(inbox/**)')")
        seen = self.seen()
        self.assertIn("Edit(.claude/settings.json)", seen["disallowed"])                          # the run itself never could
        self.assertFalse([a for a in seen["allowed"] if ".claude" in a or "permissions.py" in a])
        self.assertIn("Edit(system/tracker.db)", seen["disallowed"])
        self.assertIn("Edit(system/scripts/**)", seen["disallowed"])                              # the engine stays out of reach
        r = self.approve(card)
        self.assertTrue(r["ok"], r)
        now = json.loads((self.v.root / SETTINGS).read_text())["permissions"]
        self.assertIn("Read(inbox/**)", now["allow"])
        for d in PROTECTED:
            self.assertIn(d, now["deny"])
        self.assertFalse((self.v.root / "system/staging/deny-lifted.json").exists())              # nothing is lifted any more

    def test_one_approval_one_change_and_the_page_cannot_name_a_file_nobody_asked_for(self):
        card, _ = self.request(SETTINGS, "x", "d['permissions']['allow'].append('Read(inbox/**)')")
        self.assertTrue(self.approve(card)["ok"])
        self.assertFalse(self.approve(card)["ok"])                                                # used up
        self.assertFalse(self.post("/api/changes/approve", {"card": "c-0000000000000000"})["ok"])
        status, body = self.ask("Go ahead: edit", confirmed="Edit", permfile=SETTINGS)            # the old permission-file run is gone
        self.assertEqual(status, 400)

    def test_the_database_the_engine_and_other_files_are_refused_at_the_card(self):
        for path in ("system/tracker.db", "system/scripts/tracker.py", "system/scripts/permissions.py"):
            (self.v.root / path).parent.mkdir(parents=True, exist_ok=True)
            if not (self.v.root / path).exists():
                (self.v.root / path).write_text("{}")
            card, ev = self.request(path, "x", "d['x'] = 1")
            self.assertIsNone(card, path)                                                         # never: not even asked
            self.assertIn("their own commands", " ".join(e.get("text", "") for e in ev), path)

    def test_a_blanket_rule_is_refused_whatever_is_approved_and_the_file_left_as_it_was(self):
        card, _ = self.request(SETTINGS, "Allow everything", "d['permissions']['allow'].append('Bash(sh -c *)')")
        self.assertIsNone(card["card"])
        self.assertTrue(any("interpreter or shell" in x for x in card["refused"]), card["refused"])
        self.assertEqual(json.loads((self.v.root / SETTINGS).read_text()), json.loads(self.original))

    def test_the_local_and_config_files_work_the_same_way(self):
        card, _ = self.request(LOCAL, "Add Read(inbox/**)", "d.setdefault('permissions', {}).setdefault('allow', []).append('Read(inbox/**)')")
        self.assertTrue(self.approve(card)["ok"])
        self.assertEqual(json.loads((self.v.root / LOCAL).read_text())["permissions"]["allow"], ["Read(inbox/**)"])
        self.assertEqual((self.v.root / SETTINGS).read_text(), self.original)                     # the settings file is untouched
        card, _ = self.request(CONFIG, "Sweep at 06:15", "d['sweep']['due_from'] = '06:15'")
        self.assertTrue(self.approve(card)["ok"])
        self.assertEqual(json.loads((self.v.root / CONFIG).read_text())["sweep"]["due_from"], "06:15")

    def test_undo_through_the_server_puts_the_file_back(self):
        card, _ = self.request(SETTINGS, "x", "d['permissions']['allow'].append('Read(inbox/**)')")
        self.approve(card)
        n = json.loads((self.v.root / "system/config/files-log.jsonl").read_text().splitlines()[-1])["id"]
        self.assertTrue(self.post("/api/changes/undo", {"id": n})["ok"])
        self.assertEqual((self.v.root / SETTINGS).read_text(), self.original)

    def test_stopping_the_run_shows_no_card_and_changes_nothing(self):
        self.plan.write_text(json.dumps({"file": SETTINGS, "why": "x", "change": "d['permissions']['allow'].append('Read(inbox/**)')", "mode": "sleep"}))
        import threading
        res = {}
        t = threading.Thread(target=lambda: res.update(ev=self.ask("ask to edit permissions", run="pf-stop-run1")[1]), daemon=True)
        t.start()
        for _ in range(60):
            if (self.v.root / "fake_seen.json").exists():
                break
            time.sleep(0.1)
        self.post("/api/ask/stop", {"run": "pf-stop-run1"})
        t.join(timeout=20)
        self.assertFalse([e for e in res.get("ev", []) if e["type"] == "changes"])
        self.assertEqual((self.v.root / SETTINGS).read_text(), self.original)
        self.assertFalse((self.v.root / "system/guard/run.json").exists())

    def test_a_server_stopped_mid_run_puts_the_denies_back_when_it_starts_again(self):
        subprocess.run([sys.executable, "-c", f"import sys; sys.path.insert(0, {str(self.v.root / 'system/scripts')!r}); import permissions as P; P.begin_file_edit('.claude/settings.json')"], check=True)
        self.assertNotIn("Edit(.claude/settings.json)", json.loads((self.v.root / SETTINGS).read_text())["permissions"]["deny"])
        self.proc.terminate()
        self.proc.wait(timeout=10)
        type(self).start()                                                                        # the server starts again
        deny_now = json.loads((self.v.root / SETTINGS).read_text())["permissions"]["deny"]
        for d in PROTECTED:
            self.assertIn(d, deny_now)
        self.assertFalse((self.v.root / "system/staging/deny-lifted.json").exists())

    def test_doctor_flags_a_leftover_lift(self):
        subprocess.run([sys.executable, "-c", f"import sys; sys.path.insert(0, {str(self.v.root / 'system/scripts')!r}); import permissions as P; P.begin_file_edit('.claude/settings.json')"], check=True)
        out = self.v.run(script="doctor.py", ok=False).stdout
        self.assertIn("deny entries", out)
        self.assertIn("permissions.py recover", out)
        self.v.run("recover", script="permissions.py")


if __name__ == "__main__":
    unittest.main()
