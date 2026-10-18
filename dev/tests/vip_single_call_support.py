"""Shared fixture for test_vip_single_call and its split parts (module-level helpers and the base class; no tests here)."""
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import unittest
import urllib.request
from contextlib import closing
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_live_server import free_port  # noqa: E402
from test_sweep_alerts import check_since, vip_file, vip_vault  # noqa: E402
from test_tracker import action  # noqa: E402
NOW = "2026-10-08 09:30"
OFF = "+04:00"
MIA = "Mia Hale <mia@client.example>"
SARA = "Sara Example <sara@brightwater.example>"
BEN = "Ben Ito <ben@brightwater.example>"
ALAN = "Alan Carter <alan@brightwater.example>"
SECRET = "SECRET MESSAGE TEXT"
REGISTER = """# People register

## People

| Full name | Email | Aliases | Organisation | Role | Hidden | VIP |
|---|---|---|---|---|---|---|
| Mia Hale | mia@client.example | Mia | Client | Sponsor | | client |
| Ben Ito | ben@brightwater.example | Ben | Brightwater | Director | | |
| Sara Example | sara@brightwater.example | Sara | Brightwater | Lead | | |
| Alan Carter | alan@brightwater.example | Alan | Brightwater | Programme manager | | |
"""
MAIL_ID = "AAQkADAwATM0MDAAMS1hYjI3LTJiOTQtMDACLTAwCgAQAN"
def thread(n=1, **extra):
    """A mail thread as the model returns it, in the laptop's zone."""
    subject = "Project Falcon revised plan" + (f" {n}" if n > 1 else "")
    return {"kind": "mail", "conversation": f"{MAIL_ID}{n}", "title": subject, "subject": subject, "from": MIA,
            "people": [MIA, SARA], "last": f"2026-10-08T09:00{OFF}", "last_from": "mia@client.example",
            "link": f"https://outlook.example/owa/?ItemID=t{n}", "sensitivity": "normal",
            "summary": "Mia asks for the revised plan.", "type": "action", "ask": "Send the revised plan", "due": "2026-10-12",
            "owners": ["Sara Example"], "items": [], "body": SECRET, **extra}

def py(v, code, **env):
    """Run code in the vault with sweep importable; returns stdout as JSON."""
    r = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts'); import sweep, paths\n" + code],
                       cwd=v.root, capture_output=True, text=True,
                       env={**os.environ, "CREAITE_NOW": NOW, "CREAITE_TZ_OFFSET": OFF, **env})
    if r.returncode:
        raise AssertionError(r.stdout + r.stderr)
    return json.loads(r.stdout)

def seed(v):
    """Project ABC with ABC-A-001 to 008 (003 closed), project XYZ with XYZ-A-001; Alan's identity."""
    cfg = v.root / "system/config/settings.json"
    d = json.loads(cfg.read_text())
    d["identity"] = {"name": "Alan Carter", "short_forms": ["Alan"], "own_domains": ["brightwater.example"]}
    cfg.write_text(json.dumps(d, indent=2))
    (v.root / "projects/_portfolio/people-register.md").write_text(REGISTER)
    rows = [action(i, description=f"Filler action {i}", owner="Ben Ito", due_date=f"2026-10-{10 + i}") for i in range(1, 7)]
    rows += [action(7, description="Send the revised plan to Mia", owner="Sara Example", due_date="2026-10-12"),
             action(8, description="Book the rehearsal room", owner="Ben Ito", due_date="2026-10-20")]
    v.propose("seed", rows)
    v.run("apply")
    with closing(sqlite3.connect(v.root / "system/tracker.db")) as con:
        con.execute("UPDATE actions SET status = 'Closed', closed = '2026-10-03' WHERE id = 'ABC-A-003'")
        con.execute("INSERT INTO projects (code, name) VALUES ('XYZ', 'Project Other')")
        con.execute("INSERT INTO actions (id, project, description, owner, raised, source) VALUES "
                    "('XYZ-A-001', 'XYZ', 'Send the revised plan', 'Sara Example', '2026-10-01', 'Email · test')")
        con.commit()

CLEAN = ("found, counts = sweep.vip_clean(json.loads(sys.argv[1]), '2026-10-08 09:00', sweep.local_zone(), "
         "sweep.vip_state()['alerts'], invites=json.loads(sys.argv[2]))\nprint(json.dumps([found, counts]))")
class Base(unittest.TestCase):
    def setUp(self):
        self.v = vip_vault()
        seed(self.v)

    def tearDown(self):
        self.v.cleanup()

    def clean(self, found, invites=False):
        r = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts'); import sweep\n" + CLEAN,
                            json.dumps(found), json.dumps(invites)], cwd=self.v.root, capture_output=True, text=True,
                           env={**os.environ, "CREAITE_NOW": NOW, "CREAITE_TZ_OFFSET": OFF})
        if r.returncode:
            raise AssertionError(r.stdout + r.stderr)
        return json.loads(r.stdout)

    def check(self, found, offered=None):
        """What the live server's check does with a reply: vip_clean, then vip_record with what was offered."""
        code = ("st = sweep.vip_state(); parts = sweep.vip_prompt_parts(st)\n"
                "found, counts = sweep.vip_clean(json.loads(sys.argv[1]), '2026-10-08 08:00', sweep.local_zone(), st['alerts'])\n"
                "offered = set(json.loads(sys.argv[2])) if sys.argv[2] != 'null' else parts['offered']\n"
                "checked = {'offered': offered, 'counts': counts}\n"
                "new = sweep.vip_record(found, 'check', checked=checked)\n"
                "print(json.dumps({'new': [a['id'] for a in new], 'counts': checked['counts']}))")
        r = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts'); import sweep\n" + code,
                            json.dumps(found), json.dumps(offered)], cwd=self.v.root, capture_output=True, text=True,
                           env={**os.environ, "CREAITE_NOW": NOW, "CREAITE_TZ_OFFSET": OFF})
        if r.returncode:
            raise AssertionError(r.stdout + r.stderr)
        return json.loads(r.stdout)

    def cards(self):
        return vip_file(self.v)["alerts"]

def owner_done(**extra):
    """Sara Example, the owner of ABC-A-007, says in the thread that she sent it."""
    return thread(**{"from": MIA, "last_from": "sara@brightwater.example",
                     "match": {"id": "ABC-A-007", "relation": "update", "why": "The plan was sent."},
                     "closes": {"id": "ABC-A-007", "evidence": "Sara says the revised plan went out"}, **extra})

MERGE = ("st = sweep.vip_state(); keep, drop = [next(a for a in st['alerts'] if a['id'] == x) for x in sys.argv[1:3]]\n"
         "sweep.card_merge(st, keep, drop); sweep.vip_save(st)\nprint(json.dumps(keep))")
TOOLS = ["mcp__claude_ai_Microsoft_365__outlook_email_search", "mcp__claude_ai_Microsoft_365__chat_message_search",
         "mcp__claude_ai_Microsoft_365__outlook_calendar_search", "mcp__claude_ai_Microsoft_365__read_resource"]
FAKE = r"""#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
here = Path(__file__).parent
n = len(list(here.glob("vip-call-*.json"))) + 1
(here / f"vip-call-{n}.json").write_text(json.dumps({"args": args, "headless": os.environ.get("CREAITE_HEADLESS_RUN")}))
if (here / "start-a-sweep").exists():
    (here / "system/staging/sweep.lock").write_text(os.environ["CREAITE_NOW"] + "\n")
replies = json.loads((here / "vip-replies.json").read_text())
found = replies[min(n, len(replies)) - 1]
print(json.dumps({"type": "result", "result": "Here they are: " + json.dumps(found), "total_cost_usd": 0.3027}))
"""
REPLY = [owner_done(), {**thread(2), "kind": "calendar"}, thread(3, subject="Accepted: Steering", title="Accepted: Steering"),
         thread(4, conversation="<DX1234567890ABCDEF@EXAMPLE.OUTLOOK.COM>"), thread(5, last="2026-10-08 09:00"),
         thread(6, **{"from": "Zed Other <zed@other.example>"})]
class ServerCheck:
    """The live server's own check, with a stand-in claude; check_minutes stays 30, so only the start-up check runs."""

    def start(self, reply, sweep=False):
        self.v = v = vip_vault()
        seed(v)
        check_since(v)
        (v.root / "vip-replies.json").write_text(json.dumps([reply]))
        if sweep:
            (v.root / "start-a-sweep").write_text("1")
        fake = v.root / "fake_claude.py"
        fake.write_text(FAKE)
        fake.chmod(0o755)
        self.port = free_port()
        self.base = f"http://127.0.0.1:{self.port}"
        self.proc = subprocess.Popen([sys.executable, str(v.root / "system/scripts/live_server.py")], cwd=v.root,
                                     env={**os.environ, "CREAITE_PORT": str(self.port), "CREAITE_CLAUDE": str(fake),
                                          "CREAITE_NOW": NOW, "CREAITE_TZ_OFFSET": OFF},
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                urllib.request.urlopen(self.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        html = urllib.request.urlopen(self.base + "/").read().decode()
        self.token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]

    def stop(self):
        self.proc.terminate()
        self.proc.wait(timeout=10)
        self.v.cleanup()

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())

    def calls(self):
        return [json.loads(f.read_text()) for f in sorted(self.v.root.glob("vip-call-*.json"))]

    def log(self):
        return "\n".join(f.read_text() for f in (self.v.root / "system/logs").glob("debug-*.log"))

    def wait(self, test, what):
        for _ in range(150):
            if test():
                return
            time.sleep(0.1)
        self.fail(f"never {what}")

TIMER = """import sys, json, time
sys.path.insert(0, 'system/scripts')
import live_server
sleeps = []
real_sleep = time.sleep
def nap(s):
    if s < 1:                          # a short poll inside the check (a thread, a subprocess wait) is not the timer's wait
        return real_sleep(s)
    sleeps.append(s)
    if len(sleeps) >= 2:
        raise KeyboardInterrupt        # not an Exception: it ends the loop after its second wait
time.sleep = nap
try:
    live_server.vip_timer()
except KeyboardInterrupt:
    pass
print("RESULT " + json.dumps({"sleeps": sleeps, "error": live_server.VIP_STATUS["last_error"]}))
"""
DEEP = "[" * 100000 + "]" * 100000
