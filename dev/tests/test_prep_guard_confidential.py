"""#60 option (a) (Alan, 15-10-2026): a Prep page run never reads a confidential note, enforced in code.

Run: python3 dev/tests/test_prep_guard_confidential.py     (quick tier: no Chrome)

A throwaway vault with two notes in a project's notes folder, an ordinary one and one marked confidential. Covers:
- the guard hook in mode "prep" refuses a Read of the confidential note, a Grep, Glob or LS whose folder holds it, a creaite script
  given its path, its typed draft, the search index, a note that can't be read (fail closed), and a Bash call that tries to change
  its environment; the ordinary note, and a search where no note is confidential, are still let through;
- the same calls in ask creaite's modes (ask, confirmed) are let through exactly as before;
- search.py query and preview give the confidential note as its title and link only when CREAITE_RUN_KIND=prep, and are unchanged
  with no run kind (ask creaite) or another (a "generate" run);
- through the live server's own Run (a stand-in Claude, no model is called): a Prep page run is started with the hook in mode
  "prep" and CREAITE_RUN_KIND=prep, and its hook and search.py hold the note back; an ask creaite run keeps mode "ask" and no run
  kind, and a "generate" run still has no hook (the question for Alan, recorded in the report).
"""
import json
import os
import stat
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_tracker import ABC, Vault  # noqa: E402

TODAY = "2026-10-15"
OPEN_TEXT = "The vendor will confirm the licence count by Friday"
SECRET = "The restructure plan stays under wraps until the board meets in November"
OPEN_REL = f"{ABC}/notes/Vendor call.md"
SECRET_REL = f"{ABC}/notes/Board view.md"


def note(title, body, confidential):
    return (f"---\ntitle: {title}\ncreated: {TODAY}\nupdated: {TODAY}\ntags: []\npinned: false\n"
            f"confidential: {'true' if confidential else 'false'}\n---\n\n{body}\n")


def make(confidential=True):
    v = Vault()
    v.run("init")
    folder = v.root / ABC / "notes"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "Vendor call.md").write_text(note("Vendor call", OPEN_TEXT + ".", False), encoding="utf-8")
    (folder / "Board view.md").write_text(note("Board view", SECRET + ".", confidential), encoding="utf-8")
    return v


def hook(v, mode, tool, inp, env=None, held=False):
    """The guard hook as Claude Code runs it: exit code and its reason."""
    r = subprocess.run(["/bin/sh", "system/scripts/run", "reach.py", "hook", "--run", "r-test", "--mode", mode,
                        *(["--held", "1"] if held else [])], cwd=v.root,
                       input=json.dumps({"tool_name": tool, "tool_input": inp}), capture_output=True, text=True, timeout=60,
                       env={**os.environ, **(env or {})})
    return r.returncode, r.stderr.strip()


def search(v, *args, kind=None):
    env = {k: x for k, x in os.environ.items() if k != "CREAITE_RUN_KIND"}
    if kind:
        env["CREAITE_RUN_KIND"] = kind
    r = subprocess.run([sys.executable, "system/scripts/search.py", *args], cwd=v.root, capture_output=True, text=True,
                       timeout=120, env=env)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


class Hook(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = make()
        cls.secret, cls.open = str(cls.v.root / SECRET_REL), str(cls.v.root / OPEN_REL)

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def refused(self, tool, inp):
        for mode, held in (("prep", False), ("held", False), ("sweep", True)):   # #60: every run creaite starts itself
            code, why = hook(self.v, mode, tool, inp, held=held)
            self.assertEqual(code, 2, f"{mode} {tool} {inp}: {why}")
            self.assertIn("confidential", why)
        for mode in ("ask", "confirmed", "sweep"):          # ask creaite (a chat, a confirmed request, a typed sweep): as before
            self.assertEqual(hook(self.v, mode, tool, inp), (0, ""), f"{mode} {tool} {inp}")

    def allowed(self, tool, inp):
        for mode, held in (("prep", False), ("held", False), ("sweep", True)):
            self.assertEqual(hook(self.v, mode, tool, inp, held=held), (0, ""), f"{mode} {tool} {inp}")

    def test_1_read_of_the_confidential_note_by_its_path(self):
        self.refused("Read", {"file_path": self.secret})
        self.refused("Read", {"file_path": SECRET_REL})                       # its stored path
        self.allowed("Read", {"file_path": self.open})                        # the ordinary note is still readable

    def test_2_grep_glob_and_ls_that_would_reach_it(self):
        notes_dir = str(self.v.root / ABC / "notes")
        self.refused("Grep", {"pattern": "board", "path": notes_dir, "output_mode": "content"})
        self.refused("Grep", {"pattern": "board"})                            # the vault: it holds the notes folder
        self.refused("Grep", {"pattern": "board", "path": self.secret})      # the note itself
        self.refused("Glob", {"pattern": "*.md", "path": notes_dir})
        self.refused("Glob", {"pattern": "**/*.md", "path": str(self.v.root / ABC)})
        self.refused("Glob", {"pattern": notes_dir + "/*.md"})
        self.refused("LS", {"path": notes_dir})
        self.allowed("Grep", {"pattern": "board", "path": str(self.v.root / ABC / "minutes")})   # no note there

    def test_3_a_creaite_script_given_its_path(self):
        for cmd in (f"system/scripts/run search.py preview '{SECRET_REL}'", f"python3 system/scripts/search.py preview '{self.secret}'",
                    f"system/scripts/run docx_tools.py text '{SECRET_REL}'"):
            self.refused("Bash", {"command": cmd})
        self.allowed("Bash", {"command": f"system/scripts/run search.py preview '{OPEN_REL}'"})
        self.allowed("Bash", {"command": "system/scripts/run tracker.py read actions"})

    def test_4_the_places_that_keep_a_copy(self):
        draft = self.v.root / "system/staging/drafts/notes/0123456789abcdef.json"
        draft.parent.mkdir(parents=True, exist_ok=True)
        draft.write_text(json.dumps({"path": SECRET_REL, "body": SECRET, "changes": {}, "base": "", "at": TODAY}))
        try:
            self.refused("Read", {"file_path": str(draft)})
            self.refused("Read", {"file_path": str(self.v.root / "system/tracker.db")})          # the search index holds its text
            self.refused("Grep", {"pattern": "wraps", "path": str(self.v.root / "system/backups")})
        finally:
            draft.unlink()

    def test_5_fail_closed_a_note_that_cant_be_read(self):
        f = self.v.root / ABC / "notes" / "Locked.md"
        f.write_text(note("Locked", "Anything.", False), encoding="utf-8")
        f.chmod(0)
        try:
            if os.access(f, os.R_OK):
                self.skipTest("running as a user who can read anything")
            self.refused("Read", {"file_path": str(f)})
        finally:
            f.chmod(stat.S_IRUSR | stat.S_IWUSR)
            f.unlink()

    def test_6_its_environment_cant_be_changed(self):
        code, why = hook(self.v, "prep", "Bash", {"command": "CREAITE_RUN_KIND= system/scripts/run search.py query 'board'"})
        self.assertEqual(code, 2, why)
        code, why = hook(self.v, "prep", "Bash", {"command": "env -u CREAITE_RUN_KIND python3 system/scripts/search.py query board"})
        self.assertEqual(code, 2, why)


class NoConfidentialNote(unittest.TestCase):
    """With no note marked confidential, a Prep run may search the whole vault, as before."""

    def test_searches_are_let_through(self):
        v = make(confidential=False)
        try:
            for tool, inp in (("Grep", {"pattern": "board"}), ("Glob", {"pattern": "**/*.md"}),
                              ("Read", {"file_path": str(v.root / SECRET_REL)}),
                              ("Read", {"file_path": str(v.root / "system/tracker.db")})):
                self.assertEqual(hook(v, "prep", tool, inp), (0, ""), f"{tool} {inp}")
        finally:
            v.cleanup()


class Search(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = make()

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def notes_of(self, res):
        return {r["path"]: r for r in res["groups"]["notes"]}

    def test_1_query_leaves_it_out_entirely(self):
        search(self.v, "query", "board")                                     # the index built first, so "rebuilt" is the same
        plain = search(self.v, "query", "restructure")
        self.assertIn(SECRET_REL, self.notes_of(plain))
        self.assertIn("plan stays", json.dumps(plain), "ask creaite (no run kind) still gets it, as before")
        for kind in ("prep", "generate", "sweep"):
            held = search(self.v, "query", "restructure", kind=kind)
            self.assertEqual(held["groups"]["notes"], [], kind)
            self.assertEqual(held["totals"]["notes"], 0, kind)                # no match on its words
            self.assertNotIn("Board view", json.dumps(held), kind)            # no title
            self.assertNotIn("notes/Board", json.dumps(held), kind)           # no link
            self.assertNotIn("plan stays", json.dumps(held), kind)
        vendor = search(self.v, "query", "vendor")
        self.assertIn(OPEN_REL, self.notes_of(vendor))
        self.assertEqual(search(self.v, "query", "vendor", kind="prep"), vendor, "the ordinary note: unchanged")

    def test_2_preview_answers_as_for_a_file_not_indexed(self):
        plain = search(self.v, "preview", SECRET_REL, "board")
        self.assertIn("restructure", plain["html"], "ask creaite still gets the text")
        missing = search(self.v, "preview", f"{ABC}/notes/Nothing.md")
        for kind in ("prep", "generate"):
            self.assertEqual(search(self.v, "preview", SECRET_REL, "board", kind=kind), missing, kind)
        self.assertEqual(search(self.v, "preview", OPEN_REL, kind="prep"), search(self.v, "preview", OPEN_REL))

    def test_3_context_leaves_out_the_count_only_in_a_held_run(self):
        """#60 (Jarvis, 15-10-2026): a run creaite starts itself isn't told a confidential note matched; ask creaite and Search's
        answer (whose context the server builds without a run kind) still are."""
        def ctx(kind):
            r = subprocess.run([sys.executable, "system/scripts/search.py", "context", "restructure", "--json"], cwd=self.v.root,
                               capture_output=True, text=True, timeout=120,
                               env={**{k: x for k, x in os.environ.items() if k != "CREAITE_RUN_KIND"},
                                    **({"CREAITE_RUN_KIND": kind} if kind else {})})
            return json.loads(r.stdout)
        plain = ctx(None)
        self.assertIn("1 confidential note(s) also matched", plain["text"])
        for kind in ("prep", "generate", "sweep"):
            held = ctx(kind)
            self.assertNotIn("confidential note(s) also matched", held["text"], kind)
            self.assertNotIn("plan stays", held["text"], kind)
            self.assertEqual(held["text"], plain["text"].replace("(1 confidential note(s) also matched; their text is left out)",
                                                                 "(none found)"), kind)            # as if nothing matched

    def test_4_context_fails_closed_for_every_caller(self):
        v = make()
        try:
            locked = v.root / ABC / "notes" / "Locked.md"
            locked.write_text(note("Locked", "The budget freeze stays quiet for now.", False), encoding="utf-8")
            search(v, "query", "freeze")                                     # indexed while it could be read
            locked.chmod(0)
            if os.access(locked, os.R_OK):
                self.skipTest("running as a user who can read anything")
            try:
                for kind in (None, "prep"):                                   # ask creaite and a run creaite starts: held back
                    r = subprocess.run([sys.executable, "system/scripts/search.py", "context", "freeze", "--json"], cwd=v.root,
                                       capture_output=True, text=True, timeout=120,
                                       env={**{k: x for k, x in os.environ.items() if k != "CREAITE_RUN_KIND"},
                                            **({"CREAITE_RUN_KIND": kind} if kind else {})})
                    ctx = json.loads(r.stdout)
                    if kind is None:                                          # a held run isn't told (test_3)
                        self.assertIn("1 confidential note(s) also matched", ctx["text"])
                    self.assertNotIn("freeze stays", ctx["text"], kind)
                    self.assertNotIn("Locked.md", json.dumps(ctx["sources"]), kind)
            finally:
                locked.chmod(stat.S_IRUSR | stat.S_IWUSR)
        finally:
            v.cleanup()


FAKE = r'''#!/usr/bin/env python3
import json, os, re, subprocess, sys
args = sys.argv[1:]
rec = {"run_kind": os.environ.get("CREAITE_RUN_KIND"), "mode": None, "held": False, "hook": None}
if "--settings" in args:
    cmd = json.loads(args[args.index("--settings") + 1])["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    rec["mode"] = re.search(r"--mode (\S+)", cmd).group(1)
    rec["held"] = "--held 1" in cmd
    call = json.dumps({"tool_name": "Read", "tool_input": {"file_path": os.environ["SECRET_PATH"]}})
    rec["hook"] = subprocess.run(cmd, shell=True, input=call, capture_output=True, text=True).returncode
out = subprocess.run(["/bin/sh", "system/scripts/run", "search.py", "preview", os.environ["SECRET_REL"]], capture_output=True,
                     text=True).stdout
rec["sees_text"] = "restructure" in out
ctx = subprocess.run(["/bin/sh", "system/scripts/run", "search.py", "context", "restructure"], capture_output=True, text=True).stdout
rec["told_of_match"] = "confidential note(s) also matched" in ctx
open(__file__ + ".calls", "a", encoding="utf-8").write(json.dumps(rec) + "\n")
print(json.dumps({"type": "system", "subtype": "init", "session_id": "sess-g"}), flush=True)
print(json.dumps({"type": "result", "result": "{}", "session_id": "sess-g"}), flush=True)
'''

RUNS = r'''
import json, sys, time
sys.path.insert(0, "system/scripts")
import live_server as L
starts = [("ask", {}), ("confirmed", {"confirmed": "Close ABC-A-001"}), ("typed sweep", {"sweep": True}), ("prep", {"kind": "prep"}),
          ("generate", {"kind": "generate"}), ("search", {"kind": "search"}), ("sweep", {"kind": "sweep"}),
          ("narrow", {"kind": "generate", "only": L.ALERT_DRAFT_TOOLS}), ("notes-find", {"kind": "notes-find"}),
          ("edit-ai", {"kind": "edit-ai"})]
for name, kw in starts:
    confirmed = kw.pop("confirmed", None)
    r = L.Run("r-" + name.replace(" ", "-"), "sweep" if kw.get("sweep") else "Look at the notes.", None, None, confirmed, **kw)
    for _ in range(600):
        if r.done:
            break
        time.sleep(0.1)
held = {k: L.held_run(k, None, None, False, L.run_policy(k, None)[0])
        for k in ("check", "load", "shape-closed", "notes-find", "search", "ask")}
print(json.dumps(held))
'''


class ThroughTheRunEngine(unittest.TestCase):
    def test_runs_by_kind(self):
        v = make()
        try:
            fake = v.root / "fake_claude.py"
            fake.write_text(FAKE)
            fake.chmod(0o755)
            env = {**{k: x for k, x in os.environ.items() if k != "CREAITE_RUN_KIND"}, "CREAITE_CLAUDE": str(fake),
                   "SECRET_PATH": str(v.root / SECRET_REL), "SECRET_REL": SECRET_REL}
            r = subprocess.run([sys.executable, "-c", RUNS], cwd=v.root, env=env, capture_output=True, text=True, timeout=300)
            self.assertEqual(r.returncode, 0, r.stderr[-2000:])
            self.assertEqual(json.loads(r.stdout.strip().splitlines()[-1]),
                             {"check": True, "load": True, "shape-closed": False, "notes-find": False, "search": False,
                              "ask": False})
            calls = dict(zip(["ask", "confirmed", "typed sweep", "prep", "generate", "search", "sweep", "narrow", "notes-find",
                              "edit-ai"], [json.loads(x) for x in Path(str(fake) + ".calls").read_text().splitlines()]))
            mine = {"run_kind": None, "held": False, "hook": 0, "sees_text": True, "told_of_match": True}   # ask creaite: as before
            self.assertEqual(calls["ask"], {**mine, "mode": "ask"})
            self.assertEqual(calls["confirmed"], {**mine, "mode": "confirmed"})
            self.assertEqual(calls["typed sweep"], {**mine, "mode": "sweep"})
            # Search's answer is treated like ask creaite (Alan, 15-10-2026, #60): no hook, no run kind, search as for ask creaite
            self.assertEqual(calls["search"], {**mine, "mode": None, "hook": None})
            for kind in ("prep", "generate"):
                self.assertEqual(calls[kind], {"run_kind": kind, "mode": "held", "held": False, "hook": 2, "sees_text": False,
                                               "told_of_match": False})
            self.assertEqual(calls["sweep"], {"run_kind": "sweep", "mode": "sweep", "held": True, "hook": 2, "sees_text": False,
                                              "told_of_match": False})
            for name in ("narrow", "notes-find", "edit-ai"):                 # no file tools: no hook, as before
                self.assertEqual({k: calls[name][k] for k in ("run_kind", "mode", "hook")}, {"run_kind": None, "mode": None,
                                                                                              "hook": None}, name)
        finally:
            v.cleanup()


if __name__ == "__main__":
    unittest.main()
