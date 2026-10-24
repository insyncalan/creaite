"""Shared helpers for the smoke264 probes (written against creaite 2.6.4; see README.md).

Every probe takes the zip under test, the earlier release's zip (the base) and a work folder:

    python3 -I probe_X.py NEW_ZIP BASE_ZIP WORK_DIR [--label 2.6.4] [--control] [--keep]

A probe builds a throwaway vault in its own run folder under WORK_DIR from the BASE zip with fictional demo data, installs
NEW_ZIP over it with the vault's own update.py (or, with --control, leaves the base alone so you can see the checks that
discriminate fail there), starts the vault's live server on a spare 127.0.0.1 port with a stand-in `claude` that only logs
a call, and (for the page probes) one headless Chrome. It stops only the processes it started and deletes its run folder.

Nothing here touches a live vault, Microsoft 365, git or the network. Standard library only; the smoke helpers it reuses
are in ../smoke (smoke_driver.py and lib/), which this folder does not copy.

Exit codes: 0 = every check passed (or --control finished), 1 = a check failed, 2 = harness problem (nothing was proved).
The version appears only in labels; no check hard-codes it.
"""
import argparse
import datetime
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
SMOKE = HERE.parent / "smoke"
sys.path.insert(0, str(SMOKE))
sys.path.insert(0, str(SMOKE / "lib"))
import smoke_driver as D  # noqa: E402
from cdp import Browser  # noqa: E402

RESULTS = []
ARGS = None


def rec(step, ok, note=""):
    """Record and print one check."""
    RESULTS.append((step, bool(ok), note))
    print(f"{'PASS' if ok else 'FAIL'} {step}: {note}", flush=True)


def parse(doc, extra=None, argv=None):
    ap = argparse.ArgumentParser(description=doc, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("new_zip", help="the creaite release zip under test")
    ap.add_argument("base_zip", help="the earlier release the throwaway vault is built from (for 2.6.4: creaite-2.6.3.zip)")
    ap.add_argument("work_dir", help="folder for the run folder (created if missing; never inside a checkout or a live vault)")
    ap.add_argument("--label", help="version label for the output (default: the version in the zip's manifest)")
    ap.add_argument("--control", action="store_true", help="do not install the new zip: run the same checks on the base, "
                    "where the checks that target the fix are expected to FAIL (proves the check discriminates)")
    ap.add_argument("--keep", action="store_true", help="keep the run folder (vault, server log, screenshots)")
    if extra:
        extra(ap)
    a = ap.parse_args(argv)
    a.new_zip, a.base_zip, a.work_dir = Path(a.new_zip).expanduser(), Path(a.base_zip).expanduser(), Path(a.work_dir).expanduser()
    for p in (a.new_zip, a.base_zip):
        if not p.is_file():
            ap.error(f"{p} is not a file")
    if not a.label:
        a.label = D.zip_version(a.new_zip)
    a.base_label = D.zip_version(a.base_zip)
    global ARGS
    ARGS = a
    return a


def finish(a):
    """Print the summary and return the exit code."""
    bad = [r for r in RESULTS if not r[1]]
    print(f"\n{len(RESULTS) - len(bad)} of {len(RESULTS)} checks passed (zip label {a.label}, base {a.base_label}"
          f"{', CONTROL on the base' if a.control else ''}).")
    if a.control:
        print(f"CONTROL: {len(bad)} check(s) fail on the base, as expected where the fix is the point.")
        for s, _, _ in bad:
            print("  fails on base:", s)
        print("RESULT: CONTROL DONE")
        return 0
    for s, _, n in bad:
        print("  FAILED:", s, "--", n[:200])
    print("RESULT: PASS" if not bad else "RESULT: FAIL")
    return 1 if bad else 0


def run(main):
    """Run main(); a harness problem is exit 2, never a pass."""
    try:
        code = main()
    except D.Hard as e:
        print(f"HARNESS PROBLEM: {e}")
        code = 2
    except Exception as e:  # noqa: BLE001
        print(f"HARNESS PROBLEM: {type(e).__name__}: {e}")
        code = 2
    sys.exit(code)


# ---- fictional data ---------------------------------------------------------------------------------------------------

MAIL = ("Email · From: Priya Nair <priya.nair@northgate.example> · Subject: Data residency · Sent: 2026-10-20 09:00 "
        "· Link: https://outlook.example/owa/?ItemID=x")

FAKE = '''#!/usr/bin/env python3
import json, sys, os, time
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake_claude_calls.log"), "a").write(json.dumps({"argv_len": len(sys.argv), "t": time.time()}) + "\\n")
print(json.dumps({"type": "result", "result": "stand-in answer", "session_id": "smoke"}), flush=True)
'''


def ev(i, day, start, end, title, org, teams=True, n=4):
    return {"id": f"evt-{day[8:]}-{i:02d}", "start": start, "end": end, "title": title,
            "where": "Microsoft Teams Meeting" if teams else "", "all_day": False, "private": False, "teams": teams,
            "organiser": org, "organiser_email": "", "sensitivity": "normal", "recurrence": "", "body": "",
            "attendees": [{"name": f"Guest {k}", "email": "", "type": "required", "response": "accepted"} for k in range(n)],
            "attachments": []}


def calendar_days(today=None):
    """Three fictional days relative to the real today: the last weekday before today, today, the next weekday after today."""
    today = today or datetime.date.today()
    past = today - datetime.timedelta(days=1)
    while past.weekday() > 4:
        past -= datetime.timedelta(days=1)
    future = today + datetime.timedelta(days=1)
    while future.weekday() > 4:
        future += datetime.timedelta(days=1)
    return {"past": past, "today": today, "future": future}


def write_calendar(vault):
    """The week's meetings (system/staging/calendar.json), what the sweep found for them, and two processed meetings."""
    R, M, J = "Riley Stone", "Morgan Lee", "Jordan Park"
    d = calendar_days()
    sets = {
        "past": [("09:00", "09:30", "Weekly sync", R), ("09:45", "10:30", "Project kickoff", M),
                 ("13:00", "14:00", "Steering committee", R), ("14:30", "15:15", "Design review", J)],
        "today": [("08:30", "09:00", "Weekly sync", R), ("09:15", "10:00", "Project kickoff", M),
                  ("12:15", "12:45", "Steering committee", R), ("13:30", "14:15", "Design review", J),
                  ("19:00", "19:30", "Late huddle", M)],
        "future": [("09:00", "09:30", "Weekly sync", R), ("11:00", "12:00", "Steering committee", R)]}
    days = {d[k].isoformat(): [ev(i + 1, d[k].isoformat(), *m) for i, m in enumerate(sets[k])] for k in sets}
    (vault / "system/staging").mkdir(parents=True, exist_ok=True)
    stamp = f"{d['today'].isoformat()} 08:05"
    (vault / "system/staging/calendar.json").write_text(json.dumps(
        {"fetched": stamp, "to": (d["future"] + datetime.timedelta(days=1)).isoformat(), "days": days}, indent=1), encoding="utf-8")
    tx = {"checked": {}, "version": 1}
    for k in ("past", "today"):
        dd = d[k].isoformat()[8:]
        for i, st in {1: "available", 3: "available", 4: "not_transcribed"}.items():
            tx["checked"][f"evt-{dd}-{i:02d}"] = {"status": st, "checked": stamp}
    (vault / "system/staging/transcripts.json").write_text(json.dumps(tx, indent=1), encoding="utf-8")
    (vault / "system/processed.txt").write_text("".join(
        f"{d[k].isoformat()} | calendar:evt-{d[k].isoformat()[8:]}-02 | {d[k].isoformat()} Project kickoff.docx | 4\n"
        for k in ("past", "today")), encoding="utf-8")
    return d


# ---- one throwaway vault ----------------------------------------------------------------------------------------------

class V:
    """A throwaway vault: built from the base zip, the new zip installed over it unless --control, a calendar, a logging
    stand-in claude, optionally the live server and one headless Chrome."""

    def __init__(self, name, identity="Sam Reid", calendar=True, install=True):
        a = ARGS
        self.a = a
        ns = argparse.Namespace(work=str(a.work_dir), chain=True)
        a.work_dir.mkdir(parents=True, exist_ok=True)
        self.r = D.Run(ns)
        self.r.dir = a.work_dir.resolve() / f"{name}-{os.getpid()}"
        self.r.vault, self.r.tmp, self.r.agents = self.r.dir / "vault", self.r.dir / "tmp", self.r.dir / "agents"
        self.r.setup_dirs()
        (self.r.dir / "fake_claude.py").write_text(FAKE)
        os.chmod(self.r.dir / "fake_claude.py", 0o755)
        self.vault = self.r.vault
        self.name = name
        self.r.make_old_vault(a.base_zip)
        if install and not a.control:
            self.install_new()
        self.days = write_calendar(self.vault) if calendar else None
        cfgp = self.vault / "system/config/settings.json"
        cfg = json.loads(cfgp.read_text())
        if identity:
            cfg.setdefault("identity", {})["name"] = identity
        cfgp.write_text(json.dumps(cfg, indent=2) + "\n")
        self.b = None
        self.base = None
        self.token = None

    def install_new(self):
        """Install the zip under test over the base with the vault's own update.py (what a user does)."""
        return self.r.install(self.a.new_zip, D.zip_version(self.a.new_zip))

    def inspect_new(self):
        """update.py inspect of the zip under test (nothing is installed); returns the plan as a dict ({} if it failed)."""
        rel = self.vault / "system/releases"
        rel.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.a.new_zip, rel / self.a.new_zip.name)
        code, out = self.run("update.py", "inspect", f"system/releases/{self.a.new_zip.name}")
        return json.loads(out) if code == 0 and out.strip().startswith("{") else {}

    # settings and the database (scratch vault only)
    def settings(self):
        return json.loads((self.vault / "system/config/settings.json").read_text())

    def set_settings(self, fn):
        p = self.vault / "system/config/settings.json"
        c = json.loads(p.read_text())
        fn(c)
        p.write_text(json.dumps(c, indent=2) + "\n")

    def db(self, q, *args):
        con = sqlite3.connect(f"file:{self.vault / 'system/tracker.db'}?mode=ro", uri=True)
        try:
            return con.execute(q, args).fetchall()
        finally:
            con.close()

    def db_write(self, *statements):
        """Scratch-vault set-up only (never an assertion's evidence of a write)."""
        con = sqlite3.connect(self.vault / "system/tracker.db")
        try:
            for s in statements:
                con.execute(*s) if isinstance(s, tuple) else con.execute(s)
            con.commit()
        finally:
            con.close()

    def run(self, *a, check=False, timeout=300):
        return self.r.run_script(*a, check=check, timeout=timeout)

    def script_env(self):
        return {**os.environ, **self.r.env}

    # server and browser
    def start(self, width=1400, height=1000, browser=True):
        self.base, self.port = self.r.start_server()
        html = urllib.request.urlopen(self.base + "/").read().decode()
        self.token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]
        print(f"[{self.name}] live server pid {self.r.proc.pid} on {self.base}", flush=True)
        if browser:
            self.b = self.r.browser = Browser(width, height)
            print(f"[{self.name}] Chrome pid {self.b.proc.pid} (own process group)", flush=True)
            self.b.call("Emulation.setEmulatedMedia", features=[{"name": "prefers-color-scheme", "value": "light"},
                                                                  {"name": "prefers-reduced-motion", "value": "reduce"}])
            self.b.goto(self.base + "/")
            self.b.wait("typeof go==='function' && LIVE", 40)
            self.b.pump(1.0)
        return self

    def reload_page(self):
        self.b.reload()
        self.b.wait("typeof go==='function' && LIVE", 30)
        self.b.pump(1.5)

    def stop(self):
        try:
            return self.r.stop_server_and_browser()
        except Exception as e:  # noqa: BLE001
            return f"stop problem {e}"

    def cleanup(self, keep=False):
        return self.r.cleanup(keep)

    def close(self):
        """Stop what this probe started, then remove its run folder (unless --keep)."""
        print(self.stop(), flush=True)
        print(self.cleanup(self.a.keep), flush=True)

    # HTTP with the page's own token
    def post(self, path, body, token=True, timeout=60):
        h = {"Content-Type": "application/json"}
        if token:
            h["X-Creaite-Token"] = self.token
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), headers=h, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()

    def pj(self, path, body, **k):
        c, t = self.post(path, body, **k)
        try:
            return c, json.loads(t)
        except ValueError:
            return c, t

    def page_post(self, path, body):
        """The same POST, but made by the open page (adds the browser's own same-origin marks)."""
        return self.b.eval("fetch(%s,{method:'POST',headers:{'Content-Type':'application/json','X-Creaite-Token':%s},body:%s}).then(r=>r.text().then(t=>[r.status,t]))"
                           % (json.dumps(path), json.dumps(self.token), json.dumps(json.dumps(body))))

    def fingerprint(self, kind, obj):
        """The row fingerprint the page would send (build_dashboard.item_fp / block_fp), computed by the vault's own code."""
        code = "import sys,json; sys.path.insert(0,'system/scripts'); import build_dashboard as b; d=json.load(sys.stdin); print(b.%s(d))" % kind
        r = subprocess.run([sys.executable, "-c", code], input=json.dumps(obj), cwd=self.vault, capture_output=True, text=True,
                           env=self.script_env())
        return r.stdout.strip()

    # page helpers
    def stage(self, name, items, extra=None):
        p = self.vault / "system/staging" / f"proposed-{name}.json"
        d = {"created": "2026-10-20T09:00:00", "source_run": "cx-sweep", "files": [], "items": items}
        d.update(extra or {})
        p.write_text(json.dumps(d, indent=2))
        return p

    def reload_data(self):
        self.b.eval("window.RL=false; reloadData().then(()=>{window.RL=true})")
        self.b.wait("window.RL===true", 20)
        self.b.pump(1.0)

    def settings_search(self, q):
        self.b.eval("(()=>{const q=document.getElementById('setq'); q.value=%s; q.dispatchEvent(new Event('input',{bubbles:true}));})()" % json.dumps(q))
        self.b.pump(0.9)

    def view_text(self, view_id):
        return self.b.eval("document.getElementById(%s).innerText" % json.dumps(view_id))


def action(n, text, **extra):
    d = {"n": n, "op": "new", "table": "actions", "match": "strong", "flags": [], "decision": "pending",
         "values": {"project": "FAL", "description": text, "owner": "Lena Fischer", "due_date": "2026-11-09", "source": MAIL}}
    d.update(extra)
    return d
