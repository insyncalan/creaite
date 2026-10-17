"""#132 round 1, G3 (proposal, not applied): the model Alan chose for a kind of job, passed into every claude -p launch.

Run: python3 dev/tests/test_ai_proposal_g3_run_model.py

Two throwaway vaults from this branch: one as it is, one with g3-chosen-model.diff applied (ai_proposal_support). In each, a real
live_server.Run is built for every kind of run creaite starts, with subprocess.Popen replaced by a recorder, so the exact command,
working folder and environment are captured and nothing is started.

Done when:
- at the default settings every launch is byte for byte the unpatched one (command, cwd, the environment creaite adds, the run's
  events), kind by kind, and the launch tables (TOOLLESS_KINDS, NO_CONTEXT_ARGS, NO_CONTEXT_ENV, KIND_ARGS, KIND_TOOLS, KIND_DENIES,
  run_policy, launch_context) are equal: the guard hook (--settings), approvals, tools and folders don't move;
- a Claude model chosen for a kind of job adds `--model <alias>` to its runs (a tool-less kind's #126 Sonnet pin is replaced
  instead), and nothing else in the command changes;
- a choice that can't be used (an unknown id, a model not offered, a provider whose runs aren't built, a model that can't use
  tools for a job that needs them, an id that isn't one of the three aliases, a setting that can't be read) starts today's launch
  and says so in the run; --model is only ever given opus, sonnet or haiku.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ai_proposal_support as S  # noqa: E402

CAPTURE = r'''
import io, time, live_server as L, paths
choice = json.loads(%r)
if choice:
    p = paths.ROOT / "system" / "config" / "settings.json"
    cfg = json.loads(p.read_text())
    cfg.setdefault("ai", {}).setdefault("jobs", {}).update(choice)
    p.write_text(json.dumps(cfg))
seen = []
class Proc:
    def __init__(self, cmd, cwd=None, env=None, **kw):
        env = {k: v for k, v in (env or {}).items() if k.startswith(("CREAITE_", "CLAUDE_"))}
        env["CREAITE_SERVER_PID"] = "<PID>" if "CREAITE_SERVER_PID" in env else None    # this process's own number
        seen.append({"cmd": cmd, "cwd": str(cwd), "env": env})
        self.stdout, self.stderr, self.returncode, self.pid = io.StringIO(""), io.StringIO(""), 0, 0
    def wait(self, timeout=None): return 0
    def poll(self): return 0
    def kill(self): pass
    def terminate(self): pass
L.subprocess.Popen = Proc
CASES = [("ask", {}), ("ask-confirmed", {"confirmed": "Close ABC-A-001"}), ("typed-sweep", {"sweep": True}),
         ("search", {"kind": "search"}), ("prep", {"kind": "prep"}), ("generate", {"kind": "generate"}),
         ("check", {"kind": "check"}), ("load", {"kind": "load"}), ("alert-draft", {"kind": "generate", "only": L.ALERT_DRAFT_TOOLS}),
         ("edit-ai", {"kind": "edit-ai"}), ("shape-closed", {"kind": "shape-closed"}), ("notes-find", {"kind": "notes-find"}),
         ("close-day-sweep", {"kind": "sweep"})]
out = {}
for i, (name, kw) in enumerate(CASES):
    seen.clear()
    kw = dict(kw); confirmed = kw.pop("confirmed", None)
    r = L.Run(f"r-proposal{i:04d}", "Fictional request about ABC", None, None, confirmed, **kw)
    time.sleep(0.05)
    out[name] = dict(seen[0], events=[e for e in r.events if e.get("type") == "step"])   # not the ending of the recorder's empty stream
root = str(paths.ROOT)
text = json.dumps(out).replace(root, "<VAULT>")
import re
text = re.sub(r"creaite-toolless-[A-Za-z0-9_]+", "creaite-toolless-X", text)
text = re.sub(r"/(private/)?(var|tmp)/[^\"]*?creaite-toolless-X", "<NEUTRAL>", text)
print(text)
'''

TABLES = r'''
import live_server as L
res = {"TOOLLESS_KINDS": L.TOOLLESS_KINDS, "NO_CONTEXT_ARGS": L.NO_CONTEXT_ARGS, "NO_CONTEXT_ENV": L.NO_CONTEXT_ENV,
       "KIND_ARGS": L.KIND_ARGS, "KIND_TOOLS": L.KIND_TOOLS, "KIND_DENIES": L.KIND_DENIES, "GUARDED_KINDS": L.GUARDED_KINDS,
       "policy": {k: L.run_policy(k, None) for k in ("ask", "sweep", "search", "prep", "generate", "check", "load", "edit-ai",
                                                       "shape-closed", "notes-find")},
       "context": {k: [L.launch_context(k)[0], L.launch_context(k)[1]] for k in ("ask", "edit-ai", "shape-closed", "notes-find",
                                                                                  "generate")},
       "guard": [L.guard_mode("ask", None), L.guard_mode("ask", "x"), L.guard_mode("sweep", None)]}
print(json.dumps(res, default=str).replace(str(__import__("paths").ROOT), "<VAULT>"))
'''


class Launch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before_root = S.vault(patched=False)
        cls.after_root = S.vault("g3-chosen-model")
        cls.before = S.run_py(cls.before_root, CAPTURE % json.dumps({}))

    def capture(self, choice=None, root=None, env=None):
        return S.run_py(root or S.vault("g3-chosen-model"), CAPTURE % json.dumps(choice or {}), env=env)

    def test_default_launches_are_byte_for_byte_today(self):
        after = S.run_py(self.after_root, CAPTURE % json.dumps({}))
        self.assertEqual(sorted(after), sorted(self.before))
        for name in self.before:
            self.assertEqual(after[name], self.before[name], f"{name}: the launch changed at the default settings")
        self.assertTrue(any("--settings" in c["cmd"] for c in after.values()), "the guard hook is in the captured commands")
        self.assertEqual(after["edit-ai"]["cmd"][after["edit-ai"]["cmd"].index("--model") + 1], "sonnet", "#126's pin kept")

    def test_the_launch_tables_are_unchanged(self):
        self.assertEqual(S.run_py(self.after_root, TABLES), S.run_py(self.before_root, TABLES))

    def test_a_claude_choice_adds_only_the_model(self):
        after = self.capture({"tools": "claude:opus", "write": "claude:opus", "quick": "claude:opus"})
        for name, run in after.items():
            cmd, base = run["cmd"], self.before[name]["cmd"]
            self.assertEqual(run["cwd"], self.before[name]["cwd"], name)
            self.assertEqual(run["env"], self.before[name]["env"], name)
            self.assertEqual(run["events"], self.before[name]["events"], name)
            if "--model" in base:                                   # a tool-less kind: the pin is replaced, in place
                i = base.index("--model")
                self.assertEqual(cmd, base[:i + 1] + ["opus"] + base[i + 2:], name)
            else:                                                   # every other kind: --model opus is added once
                i = cmd.index("--model")
                self.assertEqual(cmd[i:i + 2], ["--model", "opus"], name)
                self.assertEqual(cmd[:i] + cmd[i + 2:], base, f"{name}: only --model opus was added")

    def test_one_kind_of_job_moves_only_its_own_runs(self):
        after = self.capture({"write": "claude:opus"})
        moved = sorted(n for n in after if after[n]["cmd"] != self.before[n]["cmd"])
        self.assertEqual(moved, ["alert-draft", "generate", "shape-closed"], "writing: Current state, drafts, Shape")

    def test_a_choice_that_cannot_be_used_starts_todays_launch_and_says_so(self):
        for bad in ("claude:--dangerously-skip-permissions", "claude:../../x", "openai:gpt-fake", "nosuch", "claude:opus5"):
            after = self.capture({"tools": bad})
            for name in ("ask", "prep", "search"):
                self.assertEqual(after[name]["cmd"], self.before[name]["cmd"], f"{bad} {name}")
                self.assertIn({"type": "step", "label": "The model chosen for this isn't available now, so this ran on the "
                                                        "recommended model."}, after[name]["events"], f"{bad} {name}")

    def test_run_model_fails_closed(self):
        root = S.vault("g3-chosen-model")
        out = S.run_py(root, r'''
import live_server as L, providers as pv, paths
res = {}
real_route, real_model = pv.route, pv.model
cfg = json.loads((paths.ROOT / "system/config/settings.json").read_text())
cfg.setdefault("ai", {}).setdefault("jobs", {})["tools"] = "claude:opus"
for name, model in (("not an alias", "claude:--dangerously-skip-permissions"), ("other provider", "openai:fake-small"),
                    ("no model", None)):
    pv.route = lambda job, settings, *a, m=model, **k: {"model": m, "wait": False, "ask": False, "why": ""}
    res[name] = L.run_model("ask", cfg)
pv.route = real_route
pv.model = lambda mid, settings, store=None: {"id": mid, "tools": False, "grade": 3, "provider": "claude", "label": "x"}
res["no tools for a tools job"] = L.run_model("ask", cfg)
pv.model = real_model
res["vip default"] = L.run_model("vip")
def broken():
    raise OSError("unreadable")
paths.load_settings = broken
res["unreadable"] = L.run_model("ask")
res["unknown kind"] = L.run_model("nosuch", cfg)
res["with_model"] = [L.with_model([], None), L.with_model(["--model", "sonnet"], "opus"), L.with_model(["-x"], "haiku"),
                     L.with_model(["--model"], "opus")]
res["aliases"] = list(L.CLAUDE_ALIASES)
print(json.dumps(res))''')
        self.assertEqual(out["not an alias"][0], None)
        self.assertIn("can't run this job", out["not an alias"][1])
        self.assertEqual(out["other provider"][0], None)
        self.assertIn("isn't used for this yet", out["other provider"][1])
        self.assertEqual(out["no model"][0], None)
        self.assertEqual(out["no tools for a tools job"][0], None)
        self.assertIn("can't run this job", out["no tools for a tools job"][1])
        self.assertEqual(out["unreadable"][0], None)
        self.assertIn("couldn't be read (OSError)", out["unreadable"][1])
        self.assertEqual(out["unknown kind"], [None, ""])
        self.assertEqual(out["vip default"], [None, ""])
        self.assertEqual(out["with_model"], [[], ["--model", "opus"], ["-x", "--model", "haiku"], ["--model", "--model", "opus"]])
        self.assertEqual(out["aliases"], ["opus", "sonnet", "haiku"])

    def test_the_vip_check_takes_the_same_model(self):
        src = (self.after_root / "system" / "scripts" / "live_server.py").read_text(encoding="utf-8")
        self.assertIn('"--disallowedTools", ",".join(vip_deny())] + with_model([], run_model("vip")[0])', src)
        self.assertEqual(src.count("run_model("), 3, "the run engine, the VIP check and the definition: every claude -p launch")
        self.assertEqual(src.count("claude_path(), \"-p\""), 2, "no other launch of claude to miss")


if __name__ == "__main__":
    unittest.main()
