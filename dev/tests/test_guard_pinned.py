"""BL-265: pin the guard files' decisions before they are split. reach.py, permissions.py and filechange.py decide what ask
creaite may touch (BL-141). Before any of their functions is split, every decision they make on a large table of inputs is
recorded here, and the split must leave every one of them byte for byte the same (dev/tests/pinned/guard/).

Two parts, both in a throwaway vault with a fake home folder (a stand-in .ssh key, .aws credentials, a keychain,
LaunchAgents, a shell start-up file, browser logins), so the home-folder rules are exercised for real and nothing touches
the real home folder:
- decisions: reach.classify (paths × operations, marked or not, a bulk count), reach.tier, reach.bash_problem,
  reach.hook_decision (tool calls in both modes), permissions.check_full (rules), permissions.settings_problem and
  validate_edit (edited settings files), permissions.preview_list (list edits);
- flows, end to end through the command lines: filechange.py create, edit, move, delete, a settings file, outside the
  vault, a never path, list and undo; permissions.py edit, list and undo; begin_file_edit and finish_file_edit (kept,
  refused and put back).

Run: python3 dev/tests/test_guard_pinned.py          (quick tier: no Chrome)
Record (only before the split, or for a change Alan has signed off): CREAITE_PIN_RECORD=1 python3 dev/tests/test_guard_pinned.py
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import ABC, Vault  # noqa: E402

PINNED = Path(__file__).resolve().parent / "pinned" / "guard"
RECORD = os.environ.get("CREAITE_PIN_RECORD") == "1"
TS = re.compile(r"\d{4}-\d\d-\d\d[ T]\d\d:\d\d(?::\d\d(?:\.\d+)?)?")
HOME_FILES = (".ssh/id_rsa", ".aws/credentials", "Library/Keychains/login.keychain-db", "Library/LaunchAgents/x.plist",
              ".zshrc", ".bash_profile", "Documents/notes.txt", "Library/Application Support/Google/Chrome/Default/Login Data",
              ".config/gh/hosts.yml", ".claude/settings.json")
VAULT_FILES = (f"{ABC}/notes.md", f"{ABC}/minutes/2026-10-01 Steering.docx", f"{ABC}/transcripts/2026-10-01 Steering.vtt",
               f"{ABC}/documents/SOW.docx", f"{ABC}/documents/plan.md", "inbox/forward.txt", "system/staging/drafts/new.md",
               ".git/config")

DECISIONS = r'''
import json, os, sys
sys.path.insert(0, "system/scripts")
import reach, permissions as P
H = os.path.expanduser("~")
ABC = %(abc)r
def short(x, n):
    """A key: the home and vault paths named first, then cut, so the key doesn't depend on how long those paths are."""
    x = str(x)
    for root, name in ((os.path.realpath(H), "<HOME>"), (H, "<HOME>"), (os.path.realpath(os.getcwd()), "<VAULT>"), (os.getcwd(), "<VAULT>")):
        x = x.replace(root, name)
    return x[:n]
paths = ["system/tracker.db", "system/scripts/tracker.py", "system/scripts/new.py", "system/creaite-rules.md", "VERSION",
         "CLAUDE.md", ".claude/settings.json", ".claude/settings.local.json", ".claude/skills/cx-edit/SKILL.md", ".mcp.json",
         "system/config/settings.json", "system/config/settings-log.jsonl", "system/staging/drafts/new.md",
         "system/staging/proposed-x.json", "system/staging/changes/r.json", "system/guard/run.json", "system/backups/x.db",
         "system/releases/creaite-1.0.0.zip", "dashboard.html", "tracker-view.xlsx", "inbox/forward.txt", ".git/config",
         ABC + "/CLAUDE.md", ABC + "/notes.md", ABC + "/new-note.md", ABC + "/minutes/2026-10-01 Steering.docx",
         ABC + "/transcripts/2026-10-01 Steering.vtt", ABC + "/documents/SOW.docx", ABC + "/documents/plan.md",
         "projects/_portfolio/PORTFOLIO.md", "projects/../system/tracker.db", "system/staging/../tracker.db",
         H + "/.ssh/id_rsa", H + "/.aws/credentials", H + "/Library/Keychains/login.keychain-db",
         H + "/Library/LaunchAgents/x.plist", H + "/.zshrc", H + "/.bash_profile", H + "/Documents/notes.txt",
         H + "/Library/Application Support/Google/Chrome/Default/Login Data", H + "/.config/gh/hosts.yml",
         H + "/.claude/settings.json", H + "/Documents/new.txt", "/etc/hosts", "/usr/bin/python3", "/System/Library/x",
         "/tmp/x.txt", "~/Documents/notes.txt"]
out = {"classify": {}, "tier": {}, "bash": {}, "hook": {}, "rules": {}, "settings_problem": {}, "validate_edit": {},
       "preview_list": {}, "outside": {}}
for p in paths:
    for op in reach.OPERATIONS:
        variants = [(False, 0)] if op == "read" else [(False, 0), (True, 0), (False, 11)]
        for marked, count in variants:
            out["classify"][f"{p} | {op} | marked={marked} | count={count}"] = list(reach.classify(p, op, marked, count))
perm_before = json.dumps({"permissions": {"allow": ["Read(**)"], "deny": []}})
perm_after = json.dumps({"permissions": {"allow": ["Read(**)", "Bash(python3 system/scripts/report.py *)"], "deny": []}})
for args in [(".claude/settings.json", "change", perm_before, perm_after, None),
             ("system/config/settings.json", "change", "{}", json.dumps({"sweep": {"due_from": "06:30"}}), None),
             ("system/config/settings.json", "change", "{}", perm_after, None),
             (ABC + "/notes.md", "change", "a", "b", None), (ABC + "/notes.md", "move", None, None, ".claude/settings.json"),
             (ABC + "/notes.md", "delete", None, None, None), (H + "/.claude/settings.json", "change", "{}", "{}", None)]:
    out["tier"][" | ".join(short(a, 60) for a in args)] = list(reach.tier(*args))
for c in ["python3 system/scripts/tracker.py read ABC", "python system/scripts/tracker.py read ABC",
          "python3 system/scripts/report.py weekly-data ABC --week-ending 2026-10-09",
          "python3 system/scripts/permissions.py check x", "python3 system/scripts/live_server.py",
          "python3 system/scripts/launch.py", "python3 system/scripts/nosuch.py", "python3 system/scripts/tracker.py read ABC; rm -rf x",
          "python3 system/scripts/tracker.py read ABC | head", "python3 system/scripts/tracker.py read $(whoami)",
          "python3 system/scripts/tracker.py read `id`", "python3 system/scripts/tracker.py read 'ABC $HOME'",
          "python3 system/scripts/tracker.py read \"ABC $HOME\"", "python3 system/scripts/tracker.py read 'unclosed",
          "python3 system/scripts/tracker.py read ABC > /tmp/x", "python3 system/scripts/tracker.py read ABC &",
          "python3 system/scripts/propose.py setting sweep.due_from 06:30", "python3 system/scripts/propose.py retire-settings",
          "python3 system/scripts/filechange.py edit system/config/settings.json --from x --why y",
          "system/scripts/run tracker.py read ABC", "rm -rf projects", "cat ~/.ssh/id_rsa", "ls", "",
          "python3 system/scripts/tracker.py read ABC\nrm x", "python3 system/scripts/tracker.py read ABC\\"]:
    out["bash"][c] = reach.bash_problem(c)
calls = [("Read", {"file_path": ABC + "/notes.md"}), ("Read", {"file_path": H + "/.ssh/id_rsa"}),
         ("Read", {"file_path": "/etc/hosts"}), ("Read", {"file_path": "system/tracker.db"}),
         ("Glob", {"pattern": "**/*.md", "path": H}), ("Glob", {"pattern": "*.md", "path": ABC}),
         ("Grep", {"pattern": "x", "path": H + "/Documents"}), ("LS", {"path": H}),
         ("Edit", {"file_path": "system/staging/drafts/new.md", "old_string": "a", "new_string": "b"}),
         ("Write", {"file_path": "system/staging/drafts/new.md", "content": "x"}),
         ("Write", {"file_path": "system/staging/proposed-x.json", "content": "x"}),
         ("Write", {"file_path": ABC + "/notes.md", "content": "x"}), ("Write", {"file_path": H + "/.zshrc", "content": "x"}),
         ("Edit", {"file_path": ".claude/settings.json", "old_string": "a", "new_string": "b"}),
         ("MultiEdit", {"file_path": "system/scripts/tracker.py", "edits": []}),
         ("NotebookEdit", {"notebook_path": ABC + "/x.ipynb"}),
         ("Bash", {"command": "python3 system/scripts/tracker.py read ABC"}), ("Bash", {"command": "rm -rf projects"}),
         ("Bash", {"command": "python3 system/scripts/report.py adhoc " + H + "/.ssh/id_rsa"}),
         ("WebFetch", {"url": "https://example.com"}), ("mcp__claude_ai_Microsoft_365__outlook_email_search", {"query": "x"})]
for mode in ("ask", "confirmed"):
    for tool, inp in calls:
        out["hook"][f"{mode} | {tool} | {short(json.dumps(inp, sort_keys=True), 140)}"] = list(reach.hook_decision(tool, inp, mode, ""))
# BL-301 (Alan, 15-10-2026, re-pinned deliberately): what a read marks under the server's table, with and without the notes
# exemption. Only a .md directly in a notes folder is exempt; its _images, a subfolder, transcripts and documents still mark.
import live_server
out["outside_table"] = {k: v for k, v in live_server.OUTSIDE_CONTENT.items() if k != "tools"}
for p in [ABC + "/notes/kickoff.md", ABC + "/notes/_images/a.png", ABC + "/notes/_images/a.md", ABC + "/notes/old/b.md",
          ABC + "/notes/c.txt", ABC + "/notes.md", ABC + "/transcripts/2026-10-01 Steering.vtt", ABC + "/documents/plan.md",
          ABC + "/documents/notes/d.md", "projects/_portfolio/notes/themes.md", "inbox/forward.txt", H + "/Documents/notes.txt"]:
    for exempt in (True, False):
        t = {**live_server.OUTSIDE_CONTENT, "notes_exempt": exempt}
        out["outside"][f"{short(p, 80)} | notes_exempt={exempt}"] = reach.outside_reason("Read", {"file_path": p}, t)
for r in ["Bash(python3 system/scripts/tracker.py *)", "Bash(python3 system/scripts/tracker.py:*)",
          "Bash(python3 system/scripts/report.py *)", "Bash(python3 system/scripts/permissions.py *)", "Bash(rm *)",
          "Bash(*)", "Bash", "Bash(python3 *)", "Bash(system/scripts/run tracker.py *)", "Edit(**)", "Edit(inbox/**)",
          "Write(system/scripts/x.py)", "Write(*)", "Read(**)", "WebFetch(domain:example.com)", "WebFetch", "WebSearch",
          "mcp__claude_ai_Microsoft_365__outlook_send_mail", "mcp__claude_ai_Microsoft_365__outlook_email_search",
          "mcp__claude_ai_Microsoft_365", "Bash(curl *)", "Bash(node build.js)", "Edit(.claude/settings.json)",
          "Bash(python3 system/scripts/tracker.py apply)", "Bash(git push *)", "Bash(sudo *)", ""]:
    try:
        out["rules"][r] = P.check_full(r)
    except Exception as e:
        out["rules"][r] = f"raised {type(e).__name__}: {e}"
base = {"permissions": {"allow": ["Read(**)", "Bash(python3 system/scripts/tracker.py *)"],
                        "deny": ["Edit(.claude/settings.json)", "Write(.claude/settings.json)"]}}
def with_(**kw):
    d = json.loads(json.dumps(base)); d["permissions"].update(kw); return d
cases = {"unchanged": (base, base), "add a script": (base, with_(allow=base["permissions"]["allow"] + ["Bash(python3 system/scripts/report.py *)"])),
         "add Bash(*)": (base, with_(allow=base["permissions"]["allow"] + ["Bash(*)"])),
         "add a dangerous mode": (base, {**base, "permissions": {**base["permissions"], "defaultMode": "bypassPermissions"}}),
         "remove a safety deny": (base, with_(deny=[])), "add hooks": (base, {**base, "hooks": {"PreToolUse": []}}),
         "skip in a key": (base, {**base, "dangerouslySkipPermissions": True}),
         "an extra directory": (base, with_(additionalDirectories=["/"])),
         "not an object": (base, ["x"]), "env added": (base, {**base, "env": {"X": "1"}})}
for kind in ("claude", "config", "json", "mcp"):
    for name, (b, a) in cases.items():
        try:
            out["settings_problem"][f"{kind} | {name}"] = P.settings_problem(kind, b, a)
        except Exception as e:
            out["settings_problem"][f"{kind} | {name}"] = f"raised {type(e).__name__}: {e}"
for which in ("settings", "local", "config"):
    for name, (b, a) in cases.items():
        try:
            out["validate_edit"][f"{which} | {name}"] = P.validate_edit(which, b, a)
        except Exception as e:
            out["validate_edit"][f"{which} | {name}"] = f"raised {type(e).__name__}: {e}"
for spec in ["settings add allow Bash(python3 system/scripts/report.py *)", "settings add allow Bash(*)",
             "settings remove allow Read(**)", "settings remove deny Edit(.claude/settings.json)",
             "settings add deny Bash(rm *)", "local add allow Edit(inbox/**)", "settings add dir ~/Documents",
             "settings add dir /", "settings add allow Bash(python3 system/scripts/tracker.py *)",
             "settings add allow WebFetch(domain:example.com)", "local remove allow Nothing(x)"]:
    kind, f = P.parse_edit(spec)
    try:
        out["preview_list"][spec] = P.preview_list(f) if kind == "list" else f"not a list edit: {f}"
    except SystemExit as e:
        out["preview_list"][spec] = f"exit: {e}"
    except Exception as e:
        out["preview_list"][spec] = f"raised {type(e).__name__}: {e}"
print(json.dumps(out, sort_keys=True, ensure_ascii=False, default=str))
'''

FLOWS = r'''
import json, os, subprocess, sys
sys.path.insert(0, "system/scripts")
H = os.path.expanduser("~")
ABC = %(abc)r
steps = []
def run(*args, script="filechange.py"):
    r = subprocess.run([sys.executable, "system/scripts/" + script, *args], capture_output=True, text=True)
    err = r.stderr.strip()
    for root, name in ((os.path.realpath(H), "<HOME>"), (H, "<HOME>"), (os.path.realpath(os.getcwd()), "<VAULT>"), (os.getcwd(), "<VAULT>")):
        err = err.replace(root, name)                    # named before it is cut, so the cut doesn't depend on their length
    steps.append({"run": [script, *args], "exit": r.returncode, "out": r.stdout.strip(), "err": err[-400:]})
open("system/staging/drafts/body.md", "w").write("New text\n")
open("system/staging/drafts/settings.json", "w").write(open("system/config/settings.json").read().replace("07:00", "06:30"))
run("check", ABC + "/notes.md")
run("check", ABC + "/notes.md", "--edit")
run("create", ABC + "/fresh.md", "--from", "system/staging/drafts/body.md", "--why", "a new note")
run("edit", ABC + "/notes.md", "--from", "system/staging/drafts/body.md", "--why", "rewrite")
run("move", ABC + "/notes.md", ABC + "/notes-moved.md", "--why", "rename")
run("delete", ABC + "/fresh.md", "--why", "tidy")
run("edit", "system/config/settings.json", "--from", "system/staging/drafts/settings.json", "--why", "earlier sweep")
run("edit", ".claude/settings.json", "--from", "system/staging/drafts/body.md", "--why", "widen")
run("create", H + "/Documents/new.txt", "--from", "system/staging/drafts/body.md", "--why", "outside")
run("edit", H + "/.zshrc", "--from", "system/staging/drafts/body.md", "--why", "never")
run("edit", "system/tracker.db", "--from", "system/staging/drafts/body.md", "--why", "never")
run("list", "--json")
run("undo")
run("undo")
run("list", "--json")
run("edit", "settings add allow Bash(python3 system/scripts/report.py *)", "--why", "reports", script="permissions.py")
run("edit", "settings add allow Bash(*)", "--why", "everything", script="permissions.py")
run("edit", "local add allow Edit(inbox/**)", "--why", "inbox notes", script="permissions.py")
run("edit", "settings add allow WebFetch(domain:example.com)", "--why", "the client's site", script="permissions.py")
run("edit", "config set sweep.due_from \"06:30\"", "--why", "earlier sweep", script="permissions.py")
run("list", script="permissions.py")
run("undo", script="permissions.py")
run("undo", script="permissions.py")
run("list", script="permissions.py")
import permissions as P
fe = []
for path, new_text, why in [(".claude/settings.json", None, "no change"),
                            (".claude/settings.json", "ADD_REPORT", "add a script"),
                            (".claude/settings.json", "BASH_STAR", "add Bash(*)"),
                            (".claude/settings.json", "NOT_JSON", "broken file")]:
    try:
        st = P.begin_file_edit(path)
        p = os.path.join(os.getcwd(), path)
        d = json.load(open(p))
        if new_text == "ADD_REPORT":
            d["permissions"]["allow"].append("Bash(python3 system/scripts/report.py *)"); open(p, "w").write(json.dumps(d, indent=2))
        elif new_text == "BASH_STAR":
            d["permissions"]["allow"].append("Bash(*)"); open(p, "w").write(json.dumps(d, indent=2))
        elif new_text == "NOT_JSON":
            open(p, "w").write("{ not json")
        ok, msg = P.finish_file_edit(st, why)
        fe.append({"case": why, "ok": ok, "msg": msg, "allow_after": json.load(open(p))["permissions"].get("allow")})
    except Exception as e:
        fe.append({"case": why, "raised": f"{type(e).__name__}: {e}"})
# cmd_undo's other kinds of change (BL-265, added before the split): a permission file edited by a run, a removed rule,
# a setting changed since, and permissions.py itself replaced
st = P.begin_file_edit(".claude/settings.json")
p = os.path.join(os.getcwd(), ".claude/settings.json")
d = json.load(open(p)); d["permissions"]["allow"].append("Edit(inbox/notes/**)"); open(p, "w").write(json.dumps(d, indent=2))
ok, msg = P.finish_file_edit(st, "inbox notes folder")
fe.append({"case": "a new Edit rule kept", "ok": ok, "msg": msg})
run("undo", script="permissions.py")
st = P.begin_file_edit(".claude/settings.json")
d = json.load(open(p)); d["permissions"]["allow"].append("Edit(inbox/more/**)"); open(p, "w").write(json.dumps(d, indent=2))
ok, msg = P.finish_file_edit(st, "another folder")
fe.append({"case": "edited, then changed again by hand", "ok": ok, "msg": msg})
d = json.load(open(p)); d["permissions"]["allow"].append("Edit(inbox/hand/**)"); open(p, "w").write(json.dumps(d, indent=2))
run("undo", script="permissions.py")
run("edit", "local add allow Edit(inbox/x/**)", "--why", "x", script="permissions.py")
run("edit", "local remove allow Edit(inbox/x/**)", "--why", "not needed", script="permissions.py")
run("undo", script="permissions.py")
run("edit", "config set sweep.due_from \"05:30\"", "--why", "earliest", script="permissions.py")
cfg = json.load(open("system/config/settings.json")); cfg["sweep"]["due_from"] = "05:45"
open("system/config/settings.json", "w").write(json.dumps(cfg, indent=2))
run("undo", script="permissions.py")
src = open("system/scripts/permissions.py").read()
open("system/staging/drafts/permissions.py", "w").write(src + "\n# a harmless line\n")
run("edit", "script system/staging/drafts/permissions.py", "--why", "a script change", script="permissions.py")
run("undo", script="permissions.py")
run("list", script="permissions.py")
# filechange.perform with approvals, as the live server makes them: issued in this process, bound to one change, used once
# (BL-265, added before the split); then cmd_undo's refusals when a file changed after creaite's change
import filechange as F, reach
ap = []
def act(ch, token=None):
    code, msg = F.perform(ch, approval=token, via="dashboard")
    ap.append({"change": {k: (v if k != "data" else "<data>") for k, v in ch.items()}, "token": token is not None, "code": code, "msg": msg})
def token(ch):
    return reach.APPROVALS.issue(F.fingerprint(ch))
open(ABC + "/keep.md", "w").write("keep\n")
mv = {"op": "move", "path": ABC + "/keep.md", "to": ABC + "/archive/keep.md", "why": "file it"}
act(mv)                                                  # no token: needs approval
other = token({"op": "delete", "path": ABC + "/keep.md", "why": "x"})
act(mv, other)                                           # a token for another change
act(mv, "not-a-real-token")
t = token(mv); act(mv, t)                                # approved: moved
act({"op": "move", "path": ABC + "/archive/keep.md", "to": ABC + "/keep.md", "why": "back"}, t)   # the same token again: used up
run("undo")                                              # the move put back
dl = {"op": "delete", "path": ABC + "/keep.md", "why": "tidy"}
act(dl, token(dl))
run("undo")                                              # restored
cfg = open("system/config/settings.json", "rb").read()
good = {"op": "edit", "path": "system/config/settings.json", "data": cfg.replace(b"07:00", b"06:15"), "why": "earlier"}
act(good, token(good))
bad = {"op": "edit", "path": "system/config/settings.json", "why": "permissions",
       "data": cfg.replace(b"{", b'{"permissions": {"allow": ["Bash(*)"]}, ', 1)}
act(bad, token(bad))                                     # refused whatever is approved
act({"op": "delete", "path": ".claude/settings.json", "why": "x"}, token({"op": "delete", "path": ".claude/settings.json", "why": "x"}))
act({"op": "rename", "path": ABC + "/keep.md", "why": "x"})
act({"op": "edit", "path": ABC + "/keep.md", "why": "", "data": b"x"})
act({"op": "edit", "path": ABC + "/missing.md", "why": "x", "data": b"x"})
act({"op": "delete", "path": ABC + "/missing.md", "why": "x"})
act({"op": "create", "path": ABC + "/documents", "data": b"x"})
open(ABC + "/a.md", "w").write("a\n"); open(ABC + "/b.md", "w").write("b\n")
mv2 = {"op": "move", "path": ABC + "/a.md", "to": ABC + "/b.md", "why": "x"}
act(mv2, token(mv2))                                     # never overwrites
run("create", ABC + "/made.md", "--from", "system/staging/drafts/body.md", "--why", "made")
open(ABC + "/made.md", "a").write("changed by hand\n")
run("undo")                                              # created, then changed: left alone
run("edit", ABC + "/a.md", "--from", "system/staging/drafts/body.md", "--why", "rewrite")
open(ABC + "/a.md", "a").write("changed by hand\n")
run("undo")                                              # edited, then changed: left alone
mv3 = {"op": "move", "path": ABC + "/a.md", "to": ABC + "/c.md", "why": "rename"}
act(mv3, token(mv3))
open(ABC + "/a.md", "w").write("taken\n")
run("undo")                                              # moved, and the old name is taken: left alone
dl2 = {"op": "delete", "path": ABC + "/b.md", "why": "tidy"}
act(dl2, token(dl2))
open(ABC + "/b.md", "w").write("back again\n")
run("undo")                                              # deleted, and it exists again: left alone
run("undo", "1")                                         # a change by its number
files = sorted(os.path.relpath(os.path.join(d, f)) for d, _, fs in os.walk(ABC) for f in fs)
log = [json.loads(l) for l in open("system/config/files-log.jsonl")] if os.path.exists("system/config/files-log.jsonl") else []
requests = sorted(os.listdir("system/staging/changes")) if os.path.isdir("system/staging/changes") else []
print(json.dumps({"steps": steps, "finish_file_edit": fe, "approved": ap, "project_files": files, "files_log": log,
                  "requests": requests, "home_documents": sorted(os.listdir(os.path.join(H, "Documents"))),
                  "zshrc": open(os.path.join(H, ".zshrc")).read()}, sort_keys=True, ensure_ascii=False, default=str))
'''


def normalise(text, v, home):
    for root in (Path(v.root).resolve(), Path(v.root), Path(home).resolve(), Path(home)):
        text = text.replace(str(root), "<HOME>" if "home" in str(root).rsplit("/", 1)[-1] else "<VAULT>")
    text = re.sub(r"\d{4}-\d\d-\d\d-\d{6}(?:-\d+(?=\.(?:json|py|md|db)\b))?", "<STAMP>", text)   # backup file names
    # (settings-YYYY-MM-DD-HHMMSS); BL-266: a second backup in the same second takes -2, -3…, which depends on timing
    text = TS.sub("<TS>", text)
    text = re.sub(r"\b[0-9a-f]{12,64}\b", "<HEX>", text)                    # hashes, fingerprints and backup names
    return text


class Pinned(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        self.home = Path(tempfile.mkdtemp(prefix="creaite-guard-home-"))
        for f in HOME_FILES:
            (self.home / f).parent.mkdir(parents=True, exist_ok=True)
            (self.home / f).write_text("stand-in\n", encoding="utf-8")
        for f in VAULT_FILES:
            (self.v.root / f).parent.mkdir(parents=True, exist_ok=True)
            (self.v.root / f).write_text("sample\n", encoding="utf-8")

    def tearDown(self):
        self.v.cleanup()
        import shutil
        shutil.rmtree(self.home, ignore_errors=True)

    def run_in_vault(self, code):
        env = {**os.environ, "HOME": str(self.home), "CREAITE_NO_LAUNCH": "1"}
        r = subprocess.run([sys.executable, "-c", code % {"abc": ABC}], cwd=self.v.root, env=env, capture_output=True,
                           text=True, timeout=300)
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        data = json.loads(r.stdout.strip().splitlines()[-1])
        text = normalise(json.dumps(data, ensure_ascii=False), self.v, self.home)
        # sorted after the paths are named: sorting the real paths would order the keys by where the temp folder is
        return json.dumps(json.loads(text), indent=1, sort_keys=True, ensure_ascii=False) + "\n"

    def check(self, name, got):
        f = PINNED / f"{name}.json"
        if RECORD:
            PINNED.mkdir(parents=True, exist_ok=True)
            f.write_text(got, encoding="utf-8")
        self.assertEqual(got, f.read_text(encoding="utf-8"), f"{name}: a guard decision changed")

    def test_decisions(self):
        self.check("decisions", self.run_in_vault(DECISIONS))

    def test_flows(self):
        self.check("flows", self.run_in_vault(FLOWS))


if __name__ == "__main__":
    unittest.main()
