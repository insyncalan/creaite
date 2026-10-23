#!/usr/bin/env python3
"""Upgrade smoke test 2.6.0 -> 2.6.1 candidate zip (driven by smoke-261.sh; extends smoke-260).

Extras over smoke-260: database migration checks (item_events, change_log unchanged, second migrate a no-op, backup before migrate),
the item-history route, six pages in Chrome (Today, Intake, Minutes, Work, Settings, Reporting), `update.py undo` byte-for-byte
engine comparison, a re-install after the undo, and a fresh new-vault from the zip.

Original smoke-260 text follows.

Steps (each recorded PASS / FAIL with a note; the run stops at the first hard failure but still cleans up):
  1  throwaway vault from the earlier release (2.5.4), with fictional demo data
  2  install the zip under test with `system/scripts/run update.py install` (inspect first), data counts unchanged
  3  `doctor.py`: no FAIL lines, exit 0
  4  `build_dashboard.py`: dashboard.html produced, fresh, carries the Intake and Minutes pages
  5  live server on a spare 127.0.0.1 port (throwaway settings value, stand-in Claude, never Microsoft 365), then one
     headless Chrome: the Intake page (#v-intake-review) and the Minutes page (#v-minutes, a staged fictional meeting)
     draw, with no console errors, no page exceptions and no failed (>= 400) requests
  6  stop ONLY the processes this run started (by process group of the PIDs it spawned) and remove the vault

Nothing here touches a live vault, ~/Library, /tmp or any synced folder; everything lives in one run folder under --work
(default: creaite-smoke-work in the system temp folder).
No git writes, no network except an optional `gh release download` of public release zips. Standard library only.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = Path(tempfile.gettempdir()) / "creaite-smoke-work"      # default --work (never inside the checkout)
LIB = HERE / "lib"
sys.path.insert(0, str(LIB))
import proc_guard  # noqa: E402  (copied from the creaite repo's dev/tools, unchanged)

GH_REPO = os.environ.get("CREAITE_GH_REPO", "")      # OWNER/REPO, needed only to download a release by tag; or pass a zip path
STEPS = []          # (number, name, status, note, seconds)
CTX = {}


def say(msg):
    print(f"[smoke {datetime.now():%H:%M:%S}] {msg}", flush=True)


class Hard(Exception):
    """A failure that ends the run (later steps depend on it)."""


def step(n, name):
    """Decorator: run the step, record PASS/FAIL, stop the run on Hard or any exception."""
    def wrap(fn):
        def run(*a, **k):
            t0 = time.time()
            say(f"step {n}: {name}")
            try:
                note = fn(*a, **k) or ""
                STEPS.append((n, name, "PASS", note, time.time() - t0))
                say(f"  PASS {note}")
            except Hard as e:
                STEPS.append((n, name, "FAIL", str(e), time.time() - t0))
                say(f"  FAIL {e}")
                raise
            except Exception as e:      # noqa: BLE001 - a crash in a step is a failure of the step
                STEPS.append((n, name, "FAIL", f"{type(e).__name__}: {e}", time.time() - t0))
                say(f"  FAIL {type(e).__name__}: {e}")
                raise Hard(str(e)) from e
        return run
    return wrap


def sh(cmd, cwd, env=None, check=True, timeout=300, what=None):
    """Run a command; returns (code, combined output). check=True raises Hard on a non-zero exit."""
    r = subprocess.run([str(c) for c in cmd], cwd=cwd, env={**os.environ, **(env or {})}, capture_output=True, text=True,
                       timeout=timeout)
    out = (r.stdout or "") + (r.stderr or "")
    if check and r.returncode:
        raise Hard(f"{what or ' '.join(map(str, cmd[:3]))} exited {r.returncode}: {out.strip()[-600:]}")
    return r.returncode, out


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_hashes(root):
    """{relative path: (sha256, mode)} of the engine files: system/scripts, system/templates, .claude/skills, VERSION, rules."""
    out = {}
    for base in ("system/scripts", "system/templates", ".claude/skills"):
        for p in sorted((root / base).rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
                out[str(p.relative_to(root))] = (sha256(p), oct(p.stat().st_mode & 0o777))
    for f in ("VERSION", "system/creaite-rules.md"):
        if (root / f).is_file():
            out[f] = (sha256(root / f), oct((root / f).stat().st_mode & 0o777))
    return out


def db_digest(db):
    """{table: (rows, sha256 of all rows by rowid)} for every table, read only; item_events included when there."""
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        out = {}
        for (t,) in con.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%' and name not like 'vault_search%' order by name"):
            h = hashlib.sha256()
            n = 0
            try:
                cur = con.execute(f'select * from "{t}" order by rowid')
            except sqlite3.OperationalError:
                cur = con.execute(f'select * from "{t}" order by 1')
            for row in cur:
                h.update(repr(row).encode())
                n += 1
            out[t] = (n, h.hexdigest()[:16])
        return out
    finally:
        con.close()


def zip_version(p):
    with zipfile.ZipFile(p) as z:
        return json.loads(z.read("creaite-release.json"))["version"]


# ── zips ─────────────────────────────────────────────────────────────────────

def gh_download(tag, dest_dir):
    if not GH_REPO:
        raise Hard("to download a tag, set CREAITE_GH_REPO=OWNER/REPO; or pass the zip path instead")
    dest_dir.mkdir(parents=True, exist_ok=True)
    code, out = sh(["gh", "release", "download", tag, "--repo", GH_REPO, "--pattern", "creaite-*.zip", "--dir", dest_dir,
                    "--clobber"], cwd=dest_dir, check=False, timeout=180)
    zips = sorted(dest_dir.glob("creaite-*.zip"))
    if code or not zips:
        raise Hard(f"couldn't download {tag} with gh ({out.strip()[-300:]}); pass the zip path instead")
    return zips[0]


def resolve_zip(arg, cache):
    """A path to a zip, or a release tag (v2.6.0 / 2.6.0) to download from GitHub."""
    p = Path(arg).expanduser()
    if p.is_file():
        return p.resolve()
    if re.fullmatch(r"v?\d+\.\d+\.\d+", arg):
        tag = arg if arg.startswith("v") else "v" + arg
        return gh_download(tag, cache / f"rel-{tag}")
    raise Hard(f"{arg} is neither a zip file nor a release tag like v2.6.0")


# ── the run ──────────────────────────────────────────────────────────────────

class Run:
    def __init__(self, a):
        self.a = a
        self.work = Path(a.work).resolve()
        self.dir = self.work / f"run-{datetime.now():%Y%m%d-%H%M%S}-{os.getpid()}"
        self.vault = self.dir / "vault"
        self.tmp = self.dir / "tmp"
        self.agents = self.dir / "agents"
        self.proc = None
        self.browser = None
        self.env = {}

    # safety: the run folder is ours alone, and the only thing ever removed
    def check_safe(self):
        real = self.dir.resolve()
        if str(real).startswith(str(Path.home().resolve() / "Library") + "/"):
            raise Hard(f"refusing to work under {real}")
        if (self.dir / ".creaite-dev").exists() or (self.vault / ".creaite-dev").exists():
            raise Hard("run folder carries .creaite-dev")

    def setup_dirs(self):
        self.dir.mkdir(parents=True)
        self.tmp.mkdir()
        self.agents.mkdir()
        (self.dir / ".smoke-run").write_text("created by smoke_driver.py; safe to delete\n")
        self.check_safe()
        # Everything that could reach outside the run folder is pointed inside it or switched off.
        self.env = {"TMPDIR": str(self.tmp), "CREAITE_AGENT_DIR": str(self.agents), "CREAITE_NO_LAUNCHCTL": "1",
                   "CREAITE_NO_LAUNCH": "1", "CREAITE_CLAUDE": str(self.write_fake()), "PYTHONDONTWRITEBYTECODE": "1"}
        for k in ("CREAITE_NOW", "CREAITE_PORT", "CREAITE_HC_VAULT", "CREAITE_BROWSER"):
            os.environ.pop(k, None)
        os.environ.update({"TMPDIR": str(self.tmp)})        # cdp.Browser's Chrome profile goes under the run folder

    def write_fake(self):
        """A stand-in for the `claude` command: answers every call with an empty result. The live server only ever calls it
        for the VIP check and for ask creaite; with this, nothing can reach Claude or Microsoft 365."""
        f = self.dir / "fake_claude.py"
        f.write_text('#!/usr/bin/env python3\nimport json, sys\n'
                     'print(json.dumps({"type": "result", "result": "[]", "session_id": "smoke"}), flush=True)\n')
        f.chmod(0o755)
        return f

    def run_script(self, *args, check=True, timeout=300):
        return sh([self.vault / "system/scripts/run", *args], self.vault, self.env, check=check, timeout=timeout,
                  what=f"run {args[0]}")

    # ── step 1 ──
    def make_old_vault(self, old_zip):
        code, out = sh([sys.executable, "-I", old_zip, self.vault], self.dir, self.env, what="new vault from the old zip",
                       timeout=300)
        if (self.vault / ".creaite-dev").exists():
            raise Hard("the new vault carries .creaite-dev")
        ver = (self.vault / "VERSION").read_text().strip()
        want = zip_version(old_zip)
        if ver != want:
            raise Hard(f"vault says {ver}, the zip says {want}")
        self.load_demo()
        counts = self.counts()
        if not counts["projects"]:
            raise Hard("demo data didn't load any project")
        CTX["before"] = counts
        CTX["engine_before"] = tree_hashes(self.vault)
        CTX["db_before"] = db_digest(self.vault / "system/tracker.db")
        CTX["tables_before"] = sorted(CTX["db_before"])
        return f"vault {ver} from {old_zip.name}; demo data: {counts}"

    def load_demo(self):
        """The repo's fictional demo portfolio (FAL, ORX, MER, TID), loaded through tracker.py apply like the repo's hand checks."""
        (self.vault / "dev/tools").mkdir(parents=True)
        shutil.copy2(LIB / "demo_data.py", self.vault / "dev/tools/demo_data.py")
        sh([sys.executable, "-c", "import sys; sys.path.insert(0, 'dev/tools'); import demo_data; demo_data.load()"],
           self.vault, self.env, what="demo_data load")
        shutil.rmtree(self.vault / "dev")           # a real vault has no dev/; leave none behind
        # the project register rows (so matching knows the codes), as the repo's hand checks write them
        reg = self.vault / "projects/_portfolio/project-register.md"
        text = reg.read_text(encoding="utf-8")
        text = re.sub(r"^\|  \|  \|  \|  \|  \|  \|  \|  \|  \|  \|\n",
                      "| FAL | Falcon Data Platform | FAL Falcon | Rashid Al Suwaidi | northgate.example |  |  | Falcon |  |  |\n",
                      text, count=1, flags=re.M)
        reg.write_text(text, encoding="utf-8")

    def counts(self):
        """Row counts from the record, read only."""
        con = sqlite3.connect(f"file:{self.vault / 'system/tracker.db'}?mode=ro", uri=True)
        try:
            return {t: con.execute(f"select count(*) from {t}").fetchone()[0]
                    for t in ("projects", "milestones", "actions", "raid", "decisions")}
        finally:
            con.close()

    # ── step 2 ──
    def install(self, new_zip, expect):
        rel = self.vault / "system/releases"
        rel.mkdir(parents=True, exist_ok=True)
        dest = rel / new_zip.name
        shutil.copy2(new_zip, dest)          # run refuses paths outside the vault and home: the vault's own releases folder
        if zip_version(dest) != expect:
            raise Hard(f"the zip says {zip_version(dest)}, expected {expect}")
        _, insp = self.run_script("update.py", "inspect", f"system/releases/{dest.name}")
        plan = json.loads(insp)
        _, out = self.run_script("update.py", "install", f"system/releases/{dest.name}", timeout=600)
        ver = (self.vault / "VERSION").read_text().strip()
        _, v = self.run_script("update.py", "version")
        if ver != expect or expect not in v:
            raise Hard(f"after install VERSION says {ver} / update.py says {v.strip()}; wanted {expect}")
        after = self.counts()
        if after != CTX["before"]:
            raise Hard(f"data changed over the update: {CTX['before']} -> {after}")
        first = out.strip().splitlines()[0] if out.strip() else ""
        return f"{plan['from']} -> {plan['to']}, {len(plan['replaced'])} replaced / {len(plan['added'])} added / {len(plan['removed'])} removed; {first}; data counts unchanged"

    # ── step 2b: the database migration ──
    def migration(self):
        db = self.vault / "system/tracker.db"
        now = db_digest(db)
        before = CTX["db_before"]
        notes = []
        has_events = "item_events" in now
        notes.append("item_events table " + ("PRESENT (" + str(now["item_events"][0]) + " rows)" if has_events
                                              else "ABSENT (no work-item-history table in this zip)"))
        new_tables = sorted(set(now) - set(before))
        gone = sorted(set(before) - set(now))
        notes.append(f"new tables: {new_tables or 'none'}; tables lost: {gone or 'none'}")
        if gone:
            raise Hard(f"tables lost over the update: {gone}")
        changed = [t for t in before if now.get(t) != before[t]]
        if "change_log" in changed:
            raise Hard(f"change_log changed over the update: {before['change_log']} -> {now['change_log']}")
        notes.append(f"change_log unchanged ({now['change_log'][0]} rows); tables whose rows changed: {changed or 'none'}")
        if changed:
            raise Hard(f"rows changed over the update in {changed}")
        # a backup of the database exists from before the migration, and equals the pre-update database
        ups = sorted((self.vault / "system/backups").glob("update-*"))
        if not ups or not (ups[-1] / "tracker.db").is_file():
            raise Hard("no update backup with tracker.db")
        bdig = db_digest(ups[-1] / "tracker.db")
        if bdig != before:
            raise Hard("the update backup's tracker.db isn't the pre-update database")
        notes.append(f"backup {ups[-1].name}/tracker.db = pre-update database ({len(bdig)} tables, identical rows); no item_events in it: {'item_events' not in bdig}")
        mig = sorted(p.name for p in (self.vault / "system/backups").glob("tracker-*migrate*"))
        notes.append(f"separate migrate backups: {mig or 'none (no table was rebuilt; the schema only added tables)'}")
        # second migrate does nothing
        _, out1 = self.run_script("tracker.py", "migrate")
        after1 = db_digest(db)
        _, out2 = self.run_script("tracker.py", "migrate")
        after2 = db_digest(db)
        if after1 != now or after2 != now:
            raise Hard("a second `tracker.py migrate` changed the database")
        if "up to date" not in out2.lower():
            raise Hard(f"second migrate didn't say the schema is up to date: {out2.strip()[:300]}")
        notes.append("second and third `tracker.py migrate`: 'Schema is up to date', rows identical")
        CTX["has_events"] = has_events
        CTX["db_after_install"] = now
        return "; ".join(notes)

    # ── step 3 ──
    def doctor(self):
        code, out = self.run_script("doctor.py", check=False)
        (self.dir / "doctor.txt").write_text(out)
        CTX["doctor_text"] = out
        m = re.search(r"(\d+) passed, (\d+) failed", out)
        fails = [ln for ln in out.splitlines() if ln.startswith("FAIL")]
        warns = [ln for ln in out.splitlines() if ln.startswith("WARN")]
        CTX["doctor_warns"] = warns
        if code or fails or not m or int(m.group(2)):
            raise Hard(f"doctor exit {code}: {m.group(0) if m else 'no summary'}; " + " | ".join(fails)[:500])
        return f"{m.group(0)}, exit 0, {len(warns)} WARN (expected on an empty first-setup vault): " + "; ".join(w[:70] for w in warns)

    # ── step 4 ──
    def dashboard(self):
        f = self.vault / "dashboard.html"
        start = time.time() - 1
        self.run_script("build_dashboard.py")
        if not f.is_file() or f.stat().st_size < 100_000:
            raise Hard("dashboard.html missing or tiny")
        if f.stat().st_mtime < start:
            raise Hard("dashboard.html wasn't rewritten by build_dashboard.py")
        text = f.read_text(encoding="utf-8", errors="replace")
        miss = [i for i in ('id="v-intake-review"', 'id="v-minutes"') if i not in text]
        if miss:
            raise Hard(f"dashboard.html lacks {miss}")
        return f"dashboard.html {f.stat().st_size // 1024} KiB, has the Intake and Minutes views"

    # ── step 5 ──
    def start_server(self):
        port = free_port()
        cfg_path = self.vault / "system/config/settings.json"
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        cfg.setdefault("live_mode", {})["port"] = port               # the throwaway settings value
        cfg.setdefault("vip", {})["check_minutes"] = 100000          # no automatic VIP check; the stand-in answers anyway
        cfg_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        log = open(self.dir / "server.log", "ab")
        self.proc = proc_guard.spawn([sys.executable, str(self.vault / "system/scripts/live_server.py")], cwd=self.vault,
                                     env={**os.environ, **self.env, "CREAITE_PORT": str(port)}, stdout=log,
                                     stderr=subprocess.STDOUT)
        log.close()
        CTX["server_pid"] = self.proc.pid
        base = f"http://127.0.0.1:{port}"
        end = time.time() + 60
        while True:
            try:
                urllib.request.urlopen(base + "/health", timeout=1)
                break
            except OSError:
                if time.time() > end or self.proc.poll() is not None:
                    tail = (self.dir / "server.log").read_text(errors="replace")[-600:]
                    raise Hard(f"live server didn't answer on {base}: {tail}")
                time.sleep(0.3)
        # it must be OUR process listening, on loopback only
        _, ls = sh(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-Fpn"], self.dir, check=False)
        pids = set(re.findall(r"^p(\d+)$", ls, re.M))
        names = re.findall(r"^n(.+)$", ls, re.M)
        if str(self.proc.pid) not in pids:
            raise Hard(f"port {port} is held by {pids}, not our server {self.proc.pid}")
        if any(not n.startswith("127.0.0.1:") for n in names):
            raise Hard(f"server listens beyond loopback: {names}")
        return base, port

    def stage_minutes(self):
        """Stage a fictional meeting as a minutes record with the vault's own minutes.py (as cx-minutes does); returns the
        proposal's file name. Dated on a past Tuesday to Thursday."""
        day = date.today() - timedelta(days=1)
        while day.weekday() not in (1, 2, 3):
            day -= timedelta(days=1)
        day = day.isoformat()
        title = "[FAL] Steering committee"
        turns = [(0, 1, "Alan Carter", "Morning all, first the SOW."), (0, 20, "Lena Fischer", "I'll send the revised plan next week."),
                 (1, 5, "Rashid Al Suwaidi", "We agreed the pilot stays on the lighthouse site."),
                 (2, 10, "Lena Fischer", "Data access is still late, that's the risk."),
                 (3, 0, "Sara Khan", "I'll book the UAT test environment by Friday.")]
        vtt = "WEBVTT\n\n" + "".join(f"00:{m:02d}:{s:02d}.000 --> 00:{m:02d}:{s + 5:02d}.000\n<v {w}>{t}</v>\n\n" for m, s, w, t in turns)
        (self.vault / "inbox").mkdir(exist_ok=True)
        (self.vault / "inbox" / f"{day} Steering committee.vtt").write_text(vtt, encoding="utf-8")
        p = {"project": "FAL"}
        spec = {"title": title, "date": day, "projects": ["FAL"], "transcript": f"inbox/{day} Steering committee.vtt",
                "coverage": [{"point": "Plan sign-off", "verdict": "Covered"}, {"point": "Training", "verdict": "Not discussed"}],
                "minutes": {"start": "10:00", "end": "11:00", "chat": False,
                            "attendees": "Rashid Al Suwaidi (Northgate); Alan Carter, Lena Fischer, Sara Khan",
                            "summary": [{"text": "The committee reviewed the plan and the pilot site.", "turn": 1}],
                            "updates": [{"heading": "Plan", "items": [{"text": "Lena is revising the plan.", "at": "00:00:21"}]},
                                        {"heading": "Pilot", "items": [{"text": "The pilot stays on the lighthouse site.", "at": "00:01:06"}]}],
                            "open_questions": [{"text": "Who owns the cut-over extract?", "turn": 4}]},
                "items": [{"table": "actions", "turn": 2, "due_words": "next week",
                           "values": {**p, "description": "Send the revised plan to the client", "owner": "Lena Fischer"}},
                          {"table": "actions", "turn": 5, "due_words": "next week",
                           "values": {**p, "description": "Book the UAT test environment", "owner": "Sara Khan"}},
                          {"table": "decisions", "at": "00:01:06",
                           "values": {**p, "decision": "The pilot stays on the lighthouse site", "made_by": "Rashid Al Suwaidi"}},
                          {"table": "raid", "turn": 4,
                           "values": {**p, "type": "Risk", "description": "Data access late, so the go-live slips"}}]}
        drafts = self.vault / "system/staging/drafts"
        drafts.mkdir(parents=True, exist_ok=True)
        (drafts / "meeting.json").write_text(json.dumps(spec), encoding="utf-8")
        before = {q.name for q in (self.vault / "system/staging").glob("proposed-*.json")}
        self.run_script("minutes.py", "stage", "system/staging/drafts/meeting.json")
        new = [q.name for q in (self.vault / "system/staging").glob("proposed-*.json") if q.name not in before]
        if not new:
            raise Hard("minutes.py stage produced no proposal")
        return new[0]

    def draws(self, b, shots, name, view, sel, js_ready, minimum_text=20):
        """Open a page with go(), wait for it, check it drew, screenshot."""
        b.eval(view)
        b.wait(js_ready, 30)
        b.pump(0.8)
        info = b.eval("(()=>{const e=document.querySelector(%s); if(!e) return null; const r=e.getBoundingClientRect();"
                      "return {children:e.querySelectorAll('*').length, h:Math.round(r.height), text:(e.innerText||'').trim().length,"
                      "hidden:e.hidden}})()" % json.dumps(sel))
        if not info or info["hidden"] or info["children"] < 5 or info["h"] < 100 or info["text"] < minimum_text:
            raise Hard(f"{name} page didn't draw: {info}")
        b.screenshot(str(shots / f"{name.lower()}.png"))
        return f"{name} drew ({info['children']} elements, {info['text']} chars)"

    def pages(self):
        base, port = self.start_server()
        CTX["base"] = base
        proposal = self.stage_minutes()
        sys.path.insert(0, str(LIB))
        from cdp import Browser                          # one headless Chrome, one tab, reused for all pages
        b = self.browser = Browser(1400, 1000)
        shots = self.dir / "shots"
        shots.mkdir()
        notes = []
        b.goto(base + "/")
        b.wait("typeof go==='function' && LIVE", 30)
        b.pump(0.5)
        html = urllib.request.urlopen(base + "/").read().decode("utf-8")
        token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]
        notes.append(self.draws(b, shots, "Today", "go('today')", "#v-today", "VIEW==='today' && !document.getElementById('v-today').hidden"))
        # the first-run question / start-at-sign-in (guarded 300 routes) is part of Today with the chain
        notes.append(self.draws(b, shots, "Intake", "irOpen.value=null; go('intake-review')", "#v-intake-review",
                                "VIEW==='intake-review' && !document.getElementById('v-intake-review').hidden"))
        b.eval(f"go('minutes',{{file:{json.dumps(proposal)}}})")
        b.wait("!document.getElementById('v-minutes').hidden && document.querySelector('#v-minutes tr.mi')", 30)
        b.pump(0.8)
        info = b.eval("(()=>{const e=document.getElementById('v-minutes'); const r=e.getBoundingClientRect();"
                      "return {rows:e.querySelectorAll('tr.mi').length, h:Math.round(r.height), text:(e.innerText||'').trim().length}})()")
        if info["rows"] < 1 or info["h"] < 100 or info["text"] < 50:
            raise Hard(f"Minutes page didn't draw: {info}")
        notes.append(f"Minutes drew ({info['rows']} item rows)")
        b.screenshot(str(shots / "minutes.png"))
        notes.append(self.draws(b, shots, "Work", "go('work')", "#v-work",
                                "VIEW==='work' && !!document.querySelector('#workTbl tbody tr[data-row]')"))
        rows = b.eval("document.querySelectorAll('#workTbl tbody tr[data-row]').length")
        notes.append(f"{rows} work rows")
        # open an item in the peek (Enter on a row), then the history route for that item
        b.eval("document.activeElement&&document.activeElement.blur()")
        item = b.eval("(document.querySelector('#workTbl tbody tr[data-row]')||{}).dataset && document.querySelector('#workTbl tbody tr[data-row]').dataset.row")
        b.key("ArrowDown")
        b.pump(0.3)
        b.key("Enter")
        b.pump(1.0)
        peek = b.eval("document.getElementById('panel') && document.getElementById('panel').classList.contains('on')")
        notes.append(f"peek {'opened' if peek else 'did not open'} on {item}")
        b.screenshot(str(shots / "work-peek.png"))
        ui = b.eval("!!(document.getElementById('panel')||{}).innerText && /history/i.test(document.getElementById('panel').innerText)")
        notes.append(f"peek text mentions history: {ui}")
        item_id = "FAL-A-001"
        con = sqlite3.connect(f"file:{self.vault / 'system/tracker.db'}?mode=ro", uri=True)
        try:
            row = con.execute("select id from actions order by id limit 1").fetchone()
            if row:
                item_id = row[0]
        finally:
            con.close()
        req = urllib.request.Request(base + "/api/item/history?id=" + item_id, headers={"X-Creaite-Token": token})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                hist = json.loads(r.read())
            ev = hist.get("events")
            notes.append(f"GET /api/item/history?id={item_id} -> 200, keys {sorted(hist)[:6]}, {len(ev) if ev is not None else '?'} events")
            CTX["history_route"] = "200"
        except urllib.error.HTTPError as e:
            notes.append(f"GET /api/item/history?id={item_id} -> HTTP {e.code} ({'route not in this zip' if e.code == 404 else 'ERROR'})")
            CTX["history_route"] = str(e.code)
            if e.code != 404:
                raise Hard(f"history route answered {e.code}")
        # Settings: the single-key switch and the avatar
        notes.append(self.draws(b, shots, "Settings", "go('settings')", "#v-settings",
                                "VIEW==='settings' && !!document.getElementById('setq')"))
        b.eval("(()=>{const q=document.getElementById('setq'); q.value='single-key'; q.dispatchEvent(new Event('input',{bubbles:true}));})()")
        b.pump(1.0)
        sk = b.eval("(()=>{const t=document.getElementById('v-settings').innerText; return /single-key/i.test(t)})()")
        has_def = b.eval("(()=>{try{return S&&S.singleKeys!==undefined}catch(e){return null}})()")
        notes.append(f"Settings finds 'single-key' text: {sk}; S.singleKeys={has_def}")
        b.screenshot(str(shots / "settings-singlekey.png"))
        if not sk:
            raise Hard("Settings has no Single-key shortcuts switch")
        b.eval("(()=>{const q=document.getElementById('setq'); q.value=''; q.dispatchEvent(new Event('input',{bubbles:true}));})()")
        av = b.eval("(()=>{const e=document.getElementById('railMore'); if(!e) return null; const r=e.getBoundingClientRect();"
                    "return {w:Math.round(r.width), h:Math.round(r.height), txt:(e.innerText||'').trim().slice(0,8), cls:e.className}})()")
        if not av or av["w"] < 10:
            raise Hard(f"avatar (#railMore) missing: {av}")
        b.click("#railMore")
        b.pump(0.5)
        menu = b.eval("!document.getElementById('railMoreMenu').hidden")
        b.screenshot(str(shots / "avatar-menu.png"))
        b.key("Escape")
        notes.append(f"avatar #railMore {av['w']}x{av['h']}, menu opens: {menu}")
        if not menu:
            raise Hard("avatar menu didn't open")
        notes.append(self.draws(b, shots, "Reports", "go('reports')", "#v-reports", "VIEW==='reports' && !document.getElementById('v-reports').hidden"))
        notes.append(self.draws(b, shots, "Reporting", "go('reporting','FAL')", "#v-reporting",
                                "VIEW==='reporting' && !document.getElementById('v-reporting').hidden"))
        b.pump(0.5)
        # no console errors, page exceptions or failed requests across all pages
        bad_req = []
        for ev in b.events:
            if ev.get("method") == "Network.responseReceived":
                r = ev["params"]["response"]
                if r["status"] >= 400 and not r["url"].endswith("favicon.ico"):
                    bad_req.append(f"{r['status']} {r['url']}")
        if not self.a.chain:        # the plain line: the guarded routes aren't in the zip, the page asks for them anyway
            missing = [x for x in bad_req if x.startswith("404 ") and "/api/autostart/" in x]
            bad_req = [x for x in bad_req if x not in missing]
            if missing:
                notes.append(f"NOTE plain line: {len(missing)} request(s) 404 for the guarded autostart route: {sorted(set(m.split('8/')[-1] if False else m.split('127.0.0.1:')[1].split('/',1)[1] for m in missing))}")
        if b.errors or bad_req:
            raise Hard(f"console/page errors: {[e[:200] for e in b.errors[:5]]}; failed requests: {bad_req[:5]}")
        notes.append("no console errors, exceptions or failed requests")
        CTX["page_notes"] = notes
        return f"server pid {CTX['server_pid']} on 127.0.0.1:{port}; " + "; ".join(notes)

    def stop_server_and_browser(self):
        notes = []
        if self.browser:
            self.browser.close()
            self.browser = None
            notes.append("Chrome closed")
        if self.proc:
            pid = self.proc.pid
            proc_guard.stop(self.proc, grace=10)
            if self.proc.poll() is None:
                raise Hard(f"live server pid {pid} did not stop")
            self.proc = None
            notes.append(f"live server pid {pid} stopped")
        return "; ".join(notes)

    # ── step 7: update.py undo, byte for byte ──
    def undo(self):
        stopped = self.stop_server_and_browser()
        vdb = self.vault / "system/tracker.db"
        mid_engine = tree_hashes(self.vault)
        mid_db = db_digest(vdb)
        _, out = self.run_script("update.py", "undo", check=False)
        ver = (self.vault / "VERSION").read_text().strip()
        if "Undone" not in out:
            raise Hard(f"undo said: {out.strip()[:400]}")
        after = tree_hashes(self.vault)
        before = CTX["engine_before"]
        diff = sorted(f for f in set(before) | set(after) if before.get(f) != after.get(f))
        if diff:
            raise Hard(f"{len(diff)} engine file(s) differ after undo: {diff[:8]}")
        adb = db_digest(vdb)
        dbd = sorted(t for t in set(adb) | set(CTX["db_before"]) if adb.get(t) != CTX["db_before"].get(t))
        tabs = sorted(adb) == CTX["tables_before"]
        if dbd:
            raise Hard(f"database differs from pre-update after undo in: {dbd}")
        changed_by_install = sorted(f for f in set(mid_engine) | set(before) if mid_engine.get(f) != before.get(f))
        return (f"{stopped}; undo output '{out.strip()[:90]}'; VERSION {ver}; {len(before)} engine files (scripts, templates, skills, VERSION, rules) "
                f"byte-identical with modes ({len(changed_by_install)} had changed by the install); database identical to pre-update "
                f"({len(adb)} tables, item_events gone: {'item_events' not in adb}; table set same: {tabs})")

    # ── step 8: install again after the undo ──
    def reinstall(self, new_zip, expect):
        dest = self.vault / "system/releases" / new_zip.name
        _, out = self.run_script("update.py", "install", f"system/releases/{dest.name}", timeout=600)
        ver = (self.vault / "VERSION").read_text().strip()
        if ver != expect:
            raise Hard(f"after re-install VERSION says {ver}")
        code, d = self.run_script("doctor.py", check=False)
        m = re.search(r"(\d+) passed, (\d+) failed", d)
        if code or not m or int(m.group(2)):
            raise Hard(f"doctor after re-install: {m.group(0) if m else d[-300:]}")
        has = "item_events" in db_digest(self.vault / "system/tracker.db")
        return f"installed {ver} again after the undo; doctor {m.group(0)}; item_events present: {has}"

    # ── step 9: a fresh vault from the zip ──
    def fresh(self, new_zip, expect):
        fv = self.dir / "fresh"
        env = {**self.env}
        code, out = sh([sys.executable, "-I", new_zip, fv], self.dir, env, what="new vault from the new zip", timeout=300)
        ver = (fv / "VERSION").read_text().strip()
        if ver != expect:
            raise Hard(f"fresh vault says {ver}")
        if (fv / ".creaite-dev").exists():
            raise Hard("fresh vault has .creaite-dev")
        c, d = sh([fv / "system/scripts/run", "doctor.py"], fv, env, check=False)
        m = re.search(r"(\d+) passed, (\d+) failed", d)
        fails = [ln for ln in d.splitlines() if ln.startswith("FAIL")]
        if not m or int(m.group(2)) or c:
            raise Hard(f"fresh vault doctor exit {c}: {m.group(0) if m else d[-300:]}; {fails}")
        dbf = fv / "system/tracker.db"
        tabs = sorted(db_digest(dbf)) if dbf.exists() else []
        c2, _ = sh([fv / "system/scripts/run", "build_dashboard.py"], fv, env, check=False)
        return (f"new vault from {new_zip.name} (python -I zip folder, non-interactive) VERSION {ver}; doctor {m.group(0)} exit {c}; "
                f"build_dashboard exit {c2}; item_events in fresh db: {'item_events' in tabs} ({len(tabs)} tables)")

    # ── step 6 ──
    def cleanup(self, keep):
        notes = []
        if self.browser:
            try:
                self.browser.close()                       # its own process group (Chrome and helpers)
                notes.append("Chrome closed")
            except Exception as e:                         # noqa: BLE001
                notes.append(f"Chrome close problem: {e}")
            self.browser = None
        if self.proc:
            pid = self.proc.pid
            proc_guard.stop(self.proc, grace=10)           # the server and the runs it started: its process group
            gone = self.proc.poll() is not None
            notes.append(f"live server pid {pid} stopped" if gone else f"live server pid {pid} DID NOT STOP")
            self.proc = None
            if not gone:
                raise Hard("; ".join(notes))
        if keep:
            notes.append(f"run folder kept: {self.dir}")
        elif self.dir.exists():
            if not (self.dir / ".smoke-run").exists():
                raise Hard(f"won't remove {self.dir}: no marker")
            shutil.rmtree(self.dir)
            notes.append("throwaway vault and run folder removed")
        return "; ".join(notes)


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("new", help="the zip under test (path), or a release tag such as v2.6.0 (downloaded with gh)")
    ap.add_argument("--old", default=str(WORK / "cache/rel-v2.6.0/creaite-2.6.0.zip"), help="the earlier release to start from: zip path or tag (default: cached published 2.6.0)")
    ap.add_argument("--expect", help="the version the new zip must be (default: whatever its manifest says)")
    ap.add_argument("--work", default=str(WORK), help="folder for the run folder and cache (default: creaite-smoke-work in the system temp folder)")
    ap.add_argument("--report", help="where to write the report (default: <work>/reports/smoke-<time>.md)")
    ap.add_argument("--chain", action="store_true", help="the zip carries the guarded chain: a 404 for a guarded route is then a failure")
    ap.add_argument("--keep", action="store_true", help="keep the run folder (vault, logs, screenshots)")
    a = ap.parse_args(argv)
    a.work = Path(a.work)
    (a.work / "reports").mkdir(parents=True, exist_ok=True)
    report = Path(a.report) if a.report else a.work / "reports" / f"smoke-{datetime.now():%Y%m%d-%H%M%S}.md"
    cache = a.work / "cache"
    r = Run(a)
    failed = False
    meta = {}
    try:
        new_zip = resolve_zip(a.new, cache)
        old_zip = resolve_zip(a.old, cache) if a.old.lower() not in ("none", "") else None
        expect = a.expect or zip_version(new_zip)
        meta = {"zip": str(new_zip), "sha256": sha256(new_zip), "version": expect,
                "old": f"{old_zip.name} ({zip_version(old_zip)})" if old_zip else "none (fresh vault only)"}
        say(f"zip {new_zip} ({meta['sha256'][:12]}), version {expect}; starting from {meta['old']}")
        r.setup_dirs()
        if old_zip:
            step(1, "throwaway vault from the earlier release, with demo data")(r.make_old_vault)(old_zip)
            step(2, f"update.py install of {new_zip.name}")(r.install)(new_zip, expect)
            step("2b", "database migration: item_events, change_log, backup, second migrate")(r.migration)()
        else:
            raise Hard("--old none isn't supported: the test is the upgrade")
        step(3, "doctor.py")(r.doctor)()
        step(4, "build_dashboard.py")(r.dashboard)()
        step(5, "live server + Chrome: Today, Intake, Minutes, Work, Settings, Reporting")(r.pages)()
        step(7, "update.py undo: engine and database byte-for-byte as 2.6.0")(r.undo)()
        step(8, "install again after the undo, doctor")(r.reinstall)(new_zip, expect)
        step(9, "fresh new-vault from the zip, doctor")(r.fresh)(new_zip, expect)
    except Hard:
        failed = True
    except Exception as e:      # noqa: BLE001
        failed = True
        STEPS.append((0, "setup", "FAIL", f"{type(e).__name__}: {e}", 0))
    finally:
        try:
            step("X", "stop own processes by PID, clean the throwaway vault")(r.cleanup)(a.keep or (failed and os.environ.get("SMOKE_KEEP_ON_FAIL")))
        except Hard:
            failed = True
        except Exception:   # noqa: BLE001
            failed = True
    lines = [f"# creaite {meta.get('version', '?')} upgrade smoke: {'FAIL' if failed else 'PASS'}",
             "", f"- When: {datetime.now():%d-%m-%Y %H:%M}", f"- Zip: {meta.get('zip', a.new)}",
             f"- SHA-256: {meta.get('sha256', '?')}", f"- Started from: {meta.get('old', '?')}", "",
             "| # | Step | Result | Seconds | Note |", "|---|------|--------|---------|------|"]
    for n, name, st, note, secs in STEPS:
        lines.append(f"| {n} | {name} | {st} | {secs:.0f} | {note.replace('|', '/')[:600]} |")
    if CTX.get("doctor_text"):
        lines += ["", "<details><summary>doctor.py output</summary>", "", "```", CTX["doctor_text"].strip(), "```", "</details>"]
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    say(f"report: {report}")
    say("RESULT: " + ("FAIL" if failed else "PASS"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
