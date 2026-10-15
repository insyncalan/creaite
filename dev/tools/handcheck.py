"""BL-341: run a release's hand checks unattended, in a fresh vault made from the release zip.

Usage (from the repository root):
  python3 dev/tools/handcheck.py v1.9.5 [--write] [--out DIR] [--only 1,2,13] [--keep] [--dirty] [--no-sheet]
  just -f dev/justfile handchecks v1.9.5

It does the hand-check Setup (dev/handchecks/<version>.md) by itself, in a throwaway folder:
  1. builds the release zip from this checkout (dev/tools/build_release.py; --dirty for uncommitted engine files);
  2. makes a new vault from it (system/scripts/update.py new-vault), with VIP alerts' automatic check slowed right down;
  3. loads the fictional demo portfolio (dev/tools/demo_data.py's load, called directly: its command line refuses outside
     the development repository, and this vault must not carry the .creaite-dev marker, or archiving never runs);
  4. fills the project and people registers for FAL, ORX, MER and TID (Rashid Al Suwaidi a VIP), and puts the old reports
     and minutes BL-03 needs in place;
  5. writes the stand-in Claude (dev/tests/test_run_chat.py's FAKE, answering the VIP check with nothing) and a calendar
     (a FAL Steering committee today and tomorrow, through sweep.py calendar);
  6. starts the live server on a free port with CREAITE_NOW pinned to today 09:30 and CREAITE_CLAUDE set to the stand-in.
Then it runs that release's checks module (dev/tests/handchecks/test_<v>.py, LiveBrowserCase-based, against that server),
writes the Results table with Pass or Fail and a short note into a copy of the hand-check file (--write: the file itself),
and makes the screenshot sheet for the judgement checks (sheet/index.html and a self-contained page per theme).

Everything it makes is under one run folder (--out, default a new temporary folder), printed at the end; screenshots never
go into the repository (it is public). It stops its server and Chrome by their own process groups (proc_guard), never
by name. Never Microsoft 365: Claude is the stand-in, and the VIP check is answered by it.

Development only; nothing at run time uses it. Not part of run_tests.py: one run takes a few minutes and builds a zip.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TOOLS = REPO / "dev" / "tools"
TESTS = REPO / "dev" / "tests"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TESTS))
sys.path.insert(0, str(TESTS / "handchecks"))
import proc_guard  # noqa: E402

NOW_TIME = "09:30"

# The stand-in's answer to the VIP check (its prompt starts with this): an empty list, so nothing is found and nothing fails
VIP_ANSWER = '''
if p.startswith("creaite VIP check"):
    out({"type": "result", "result": "[]", "session_id": "sess-vip"})
    sys.exit(0)
'''

PEOPLE = [  # full name, email, organisation, role, VIP: the demo's owners (fictional)
    ("Alan Carter", "alan.carter@example.com", "Example Consulting", "Programme manager", ""),
    ("Rashid Al Suwaidi", "rashid@northgate.example", "Northgate", "Sponsor", "client"),
    ("Lena Fischer", "lena.fischer@example.com", "Example Consulting", "Data lead", ""),
    ("Mei Tan", "mei.tan@orbitretail.example", "Orbit", "Test manager", ""),
    ("James Okafor", "james.okafor@orbitretail.example", "Orbit", "Sponsor", ""),
    ("Sara Khan", "sara.khan@example.com", "Example Consulting", "Delivery lead", ""),
    ("Dev Patel", "dev.patel@example.com", "Example Consulting", "Adoption lead", ""),
    ("Priya Nair", "priya.nair@meridian.example", "Meridian", "Sponsor", ""),
    ("Omar Haddad", "omar.haddad@example.com", "Example Consulting", "Cut-over lead", ""),
]
REGISTER = [  # code, name, aliases, stakeholders, domains, keywords
    ("FAL", "Falcon Data Platform", "Falcon, Northgate", "Rashid Al Suwaidi", "northgate.example", "Falcon, data platform"),
    ("ORX", "Orbit Customer App", "Orbit, Orbit Retail", "James Okafor", "orbitretail.example", "Orbit, customer app"),
    ("MER", "Meridian Contact Centre AI", "Meridian", "Priya Nair", "meridian.example", "Meridian, contact centre"),
    ("TID", "Tide Billing Migration", "Tide", "Omar Haddad", "", "Tide, billing"),
]


def log(msg):
    """One line of progress, with the time."""
    print(f"[handcheck {datetime.now():%H:%M:%S}] {msg}", flush=True)


def run(cmd, cwd, env=None, what=None):
    """Run a command; raise with its output if it fails."""
    r = subprocess.run([str(c) for c in cmd], cwd=cwd, env={**os.environ, **(env or {})}, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"{what or cmd[1]} failed ({r.returncode}):\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
    return r.stdout


def last_friday(today):
    """The Friday before `today` (a week back when today is a Friday)."""
    return today - timedelta(days=(today.weekday() - 4) % 7 or 7)


class Session:
    """One hand-check environment: the run folder, the zip, the vault and its live server."""

    def __init__(self, out=None, dirty=False, keep=False):
        self.dir = Path(out).resolve() if out else Path(tempfile.mkdtemp(prefix="creaite-hc-"))
        self.dir.mkdir(parents=True, exist_ok=True)
        self.dirty, self.keep = dirty, keep
        self.today = date.today()
        self.now = f"{self.today.isoformat()} {NOW_TIME}"
        self.zip = self.vault = self.proc = self.base = None
        self.fake = self.dir / "fake_claude.py"
        self.servers = []                      # every (proc, vault) this session started, stopped at close

    # ── Setup ────────────────────────────────────────────────────────────────

    def build_zip(self):
        """Setup step 2a: the release zip from this checkout."""
        out = self.dir / "zip"
        shutil.rmtree(out, ignore_errors=True)
        log("building the release zip")
        run([sys.executable, TOOLS / "build_release.py", "--out", out] + (["--dirty"] if self.dirty else []), REPO,
            what="build_release.py")
        self.zip = next(out.glob("creaite-*.zip"))
        return self.zip

    def write_fake(self):
        """Setup step 5: the stand-in Claude (test_run_chat's FAKE), answering the VIP check with an empty list."""
        from test_run_chat import FAKE
        text = FAKE.replace('out = lambda o: print(json.dumps(o), flush=True)\n',
                            'out = lambda o: print(json.dumps(o), flush=True)\n' + VIP_ANSWER.lstrip("\n"), 1)
        if text == FAKE:
            raise RuntimeError("test_run_chat.FAKE changed shape: the VIP answer couldn't be added")
        self.fake.write_text(text, encoding="utf-8")
        self.fake.chmod(0o755)

    def make_vault(self, name="vault"):
        """Setup steps 2 to 6 in a new vault called `name` in the run folder; returns its root."""
        if not self.zip:
            self.build_zip()
        if not self.fake.exists():
            self.write_fake()
        root = self.dir / name
        shutil.rmtree(root, ignore_errors=True)
        log(f"making the vault {root.name} from {self.zip.name}")
        run([sys.executable, "-I", REPO / "system/scripts/update.py", "new-vault", self.zip, root], REPO, what="update.py new-vault")
        if (root / ".creaite-dev").exists():
            raise RuntimeError("the new vault carries .creaite-dev; archiving would never run")
        cfg_path = root / "system/config/settings.json"
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        cfg.setdefault("vip", {})["check_minutes"] = 100000          # step 2: nothing calls out (the stand-in answers anyway)
        cfg_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        env = {"CREAITE_NOW": self.now}
        log("loading the demo portfolio")
        (root / "dev/tools").mkdir(parents=True, exist_ok=True)
        shutil.copy2(TOOLS / "demo_data.py", root / "dev/tools/demo_data.py")
        run([sys.executable, "-c", "import sys; sys.path.insert(0, 'dev/tools'); import demo_data; demo_data.load()"], root,
            env, what="demo_data load")
        self.write_registers(root)
        self.old_files(root)
        cal = root / "system/staging/hc-cal.json"     # the run wrapper passes only paths inside the vault (or home)
        meeting = {"id": "hc-1", "start": "10:00", "end": "11:00", "title": "FAL Steering committee",
                   "where": "Microsoft Teams Meeting", "teams": True, "private": False, "organiser": True}
        cal.write_text(json.dumps({"days": {self.today.isoformat(): [meeting],
                                            (self.today + timedelta(days=1)).isoformat(): [dict(meeting, id="hc-2")]}}))
        run([root / "system/scripts/run", "sweep.py", "calendar", cal], root, env, what="sweep.py calendar")
        cal.unlink()
        run([root / "system/scripts/run", "build_dashboard.py"], root, env, what="build_dashboard.py")
        return root

    @staticmethod
    def write_registers(root):
        """Setup step 3: FAL, ORX, MER and TID in the project register; their owners in the people register."""
        reg = root / "projects/_portfolio/project-register.md"
        text = reg.read_text(encoding="utf-8")
        rows = "".join(f"| {c} | {n} | {c} {n} | {a} | {s} | {d} |  | {k} |  |  |\n" for c, n, a, s, d, k in REGISTER)
        text = re.sub(r"^\|  \|  \|  \|  \|  \|  \|  \|  \|  \|  \|\n", rows, text, count=1, flags=re.M)
        reg.write_text(text, encoding="utf-8")
        ppl = root / "projects/_portfolio/people-register.md"
        text = ppl.read_text(encoding="utf-8")
        head = "|-----------|-------|---------|--------------|------|--------|-----|--------|\n"
        rows = "".join(f"| {n} | {e} | {n} ({o.split()[0]}) | {o} | {r} |  | {v} |  |\n" for n, e, o, r, v in PEOPLE)
        if head not in text:
            raise RuntimeError("the people register's table changed shape")
        ppl.write_text(text.replace(head, head + rows, 1), encoding="utf-8")

    def old_files(self, root):
        """Setup step 4: old reports and minutes for BL-03 (over 12 months back), and one recent report."""
        src = root / "system/templates/minutes-template.docx"
        fal, orx = root / "projects/FAL Falcon Data Platform", root / "projects/ORX Orbit Customer App"
        for f in (fal / "reports/2025-08-29 Falcon Data Platform weekly report.docx",
                  fal / "reports/2025-09-05 Falcon Data Platform client report.docx",
                  fal / "reports/2025-09-05 Falcon data notes.docx",
                  fal / "minutes/2025-09-02 FAL steering minutes.docx",
                  fal / "transcripts/2025-09-02 FAL steering transcript.docx",
                  root / "projects/_portfolio/minutes/2025-09-10 Portfolio review minutes.docx",
                  orx / f"reports/{last_friday(self.today).isoformat()} Orbit Customer App weekly report.docx"):
            f.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, f)

    def server_env(self, root, port):
        """The live server's environment: its port, the stand-in Claude, the pinned clock, and no app launches
        (CREAITE_NO_LAUNCH: /api/open reports the path instead of opening Word on the throwaway file)."""
        return {"CREAITE_PORT": str(port), "CREAITE_CLAUDE": str(self.fake), "CREAITE_NOW": self.now,
                "CREAITE_HC_VAULT": str(root), "CREAITE_NO_LAUNCH": "1"}

    def start_server(self, root):
        """Setup step 7: the live server on a free port; returns (process, base URL)."""
        from live_browser import free_port
        port = free_port()
        base = f"http://127.0.0.1:{port}"
        logf = open(self.dir / f"server-{root.name}.log", "ab")
        proc = proc_guard.spawn([sys.executable, str(root / "system/scripts/live_server.py")], cwd=root,
                                env={**os.environ, **self.server_env(root, port)}, stdout=logf, stderr=subprocess.STDOUT)
        logf.close()
        self.servers.append(proc)
        deadline = time.time() + 40
        while True:
            try:
                urllib.request.urlopen(base + "/health", timeout=1)
                break
            except OSError:
                if time.time() > deadline or proc.poll() is not None:
                    raise RuntimeError(f"the live server didn't answer; see {self.dir / f'server-{root.name}.log'}") from None
                time.sleep(0.2)
        log(f"live server for {root.name} at {base}")
        return proc, base

    def stop_server(self, proc):
        """Stop one server this session started, with every run it started (its own process group)."""
        if proc in self.servers:
            self.servers.remove(proc)
        proc_guard.stop(proc, grace=10)        # the server and every run it started: its own process group

    def open(self):
        """The shared vault and server the checks use."""
        self.vault = self.make_vault()
        self.proc, self.base = self.start_server(self.vault)
        self.export()
        return self

    def export(self):
        """Tell the checks module (in this process) where things are."""
        os.environ.update({"CREAITE_HC_DIR": str(self.dir), "CREAITE_HC_VAULT": str(self.vault), "CREAITE_HC_BASE": self.base,
                           "CREAITE_HC_NOW": self.now, "CREAITE_HC_ZIP": str(self.zip)})

    def close(self):
        """Stop every server this session started. The run folder stays (it holds the results and the sheet)."""
        for proc in list(self.servers):
            self.stop_server(proc)


# ── The Results table ────────────────────────────────────────────────────────

ROW = re.compile(r"^\| (\d+) \| ([^|]*) \| ([^|]*) \| \[[ x]\] \| \[[ x]\] \| ([^|]*)\|\s*$")


def fill_results(text, outcomes):
    """The hand-check file with its Results rows filled: [x] under Pass or Fail, and the note. A check with no Pass or Fail
    (judgement, live only, not automated yet) keeps both boxes empty and says why in the note."""
    out = []
    for line in text.splitlines(keepends=True):
        m = ROW.match(line)
        if m and int(m.group(1)) in outcomes:
            status, note = outcomes[int(m.group(1))]
            p, f = ("[x]", "[ ]") if status == "pass" else ("[ ]", "[x]") if status == "fail" else ("[ ]", "[ ]")
            note = " ".join(str(note).replace("|", "/").split())[:300]
            line = f"| {m.group(1)} | {m.group(2)} | {m.group(3)} | {p} | {f} | {note} |\n"
        out.append(line)
    return "".join(out)


class Collect(unittest.TextTestResult):
    """Each test's outcome, by check number (test_cNN_…)."""

    def __init__(self, *a, **k):
        """unittest's result, plus each check's outcome."""
        super().__init__(*a, **k)
        self.by_check = {}

    @staticmethod
    def check_of(test):
        """The check number in a test's name (test_cNN_…), or None."""
        m = re.match(r"test_c(\d+)_", getattr(test, "_testMethodName", ""))
        return int(m.group(1)) if m else None

    def _put(self, test, status, note):
        """Record one check's outcome."""
        n = self.check_of(test)
        if n is not None:
            self.by_check[n] = (status, note)

    def addSuccess(self, test):
        """Passed."""
        super().addSuccess(test)
        self._put(test, "pass", "")

    def addFailure(self, test, err):
        """Failed: the assertion's first line is the note."""
        super().addFailure(test, err)
        self._put(test, "fail", str(err[1]).strip().splitlines()[0] if str(err[1]).strip() else "failed")

    def addError(self, test, err):
        """An error in the check itself counts as Fail, with the error as the note."""
        super().addError(test, err)
        self._put(test, "fail", f"error: {err[0].__name__}: {str(err[1]).strip().splitlines()[0] if str(err[1]).strip() else ''}")

    def addSkip(self, test, reason):
        """Skipped (phase 2, or left out with --only)."""
        super().addSkip(test, reason)
        if reason != "not in --only":          # a check left out with --only keeps its row as it was
            self._put(test, "skip", reason)


def outcomes_for(mod, result):
    """Pass, Fail or a note for every check the module knows, from the run and the module's registry."""
    notes = getattr(mod, "NOTES", {})
    out = {}
    for n, (status, note) in result.by_check.items():
        kind = mod.KIND.get(n, "")
        if status == "pass" and kind == "judgement":
            status, note = "judgement", "judgement: on the screenshot sheet"
        extra = notes.get(n, "")
        note = "; ".join(x for x in (note, extra) if x)
        out[n] = (status, f"auto ({kind}): {note}" if status in ("pass", "fail") else note)
    for n, why in getattr(mod, "LIVE_ONLY", {}).items():
        if isinstance(n, int):
            out[n] = ("live", f"live only: {why}")
    return out


def check_texts(text):
    """{number: the check's text} from the hand-check file's Checks section (for the sheet)."""
    body = text.split("## Checks", 1)[-1].split("\n## ", 1)[0]
    return {int(m.group(1)): m.group(2).strip() for m in re.finditer(r"^(\d+)\. (.+)$", body, re.M)}


def main(argv):
    """Set up, run the checks, fill the Results table and make the sheet. Exit 1 if any check failed."""
    ap = argparse.ArgumentParser(description="Run a release's hand checks unattended (BL-341).")
    ap.add_argument("version", help="e.g. v1.9.5")
    ap.add_argument("--out", help="the run folder (default: a new temporary folder)")
    ap.add_argument("--write", action="store_true", help="fill the Results table in dev/handchecks/<version>.md itself")
    ap.add_argument("--only", help="comma-separated check numbers to run")
    ap.add_argument("--keep", action="store_true", help="leave the server running until Enter is pressed")
    ap.add_argument("--dirty", action="store_true", help="build the zip from uncommitted engine files too")
    ap.add_argument("--no-sheet", action="store_true", help="skip the screenshot sheet")
    a = ap.parse_args(argv)
    v = a.version if a.version.startswith("v") else "v" + a.version
    md = REPO / "dev/handchecks" / f"{v}.md"
    modname = "test_v" + v[1:].replace(".", "")
    if not md.exists() or not (TESTS / "handchecks" / f"{modname}.py").exists():
        print(f"No hand checks for {v}: need {md.relative_to(REPO)} and dev/tests/handchecks/{modname}.py", file=sys.stderr)
        return 2
    version = (REPO / "VERSION").read_text().strip()
    if version != v[1:]:
        log(f"note: VERSION says {version}, not {v[1:]} (Setup step 1 expects the release's own version)")
    s = Session(a.out, a.dirty, a.keep)
    os.environ["CREAITE_HC_SHEET"] = "0" if a.no_sheet else "1"
    if a.only:
        os.environ["CREAITE_HC_ONLY"] = a.only
    t0 = time.time()
    try:
        s.open()
        import importlib
        mod = importlib.import_module(modname)
        suite = unittest.defaultTestLoader.loadTestsFromModule(mod)
        runner = unittest.TextTestRunner(stream=sys.stdout, verbosity=2, resultclass=Collect)
        result = runner.run(suite)
        outcomes = outcomes_for(mod, result)
        if a.keep:
            input(f"Server still running at {s.base} (vault {s.vault}). Press Enter to stop it… ")
    finally:
        s.close()
    filled = fill_results(md.read_text(encoding="utf-8"), outcomes)
    dest = md if a.write else s.dir / md.name
    dest.write_text(filled, encoding="utf-8")
    sheet = None
    if not a.no_sheet:
        import sheet as sheetmod
        sheet = sheetmod.write(s.dir, title=f"creaite {v[1:]} hand checks: the judgement sheet",
                               checks=check_texts(md.read_text(encoding="utf-8")))
    counts = {}
    for st, _ in outcomes.values():
        counts[st] = counts.get(st, 0) + 1
    log(f"done in {time.time() - t0:.0f} s: " + ", ".join(f"{k} {n}" for k, n in sorted(counts.items())))
    log(f"Results: {dest}")
    if sheet:
        log(f"Screenshot sheet: {sheet}")
    log(f"Run folder: {s.dir}")
    return 0 if not any(st == "fail" for st, _ in outcomes.values()) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
