"""Run creaite's test files in parallel and report each one (development only).

Run: python3 dev/tools/run_tests.py [-j N] [--quick] [--changed [BASE]] [--deep] [--list] [--flaky] [--clean]
                                    [--repeat N [--stress N]] [--file-timeout S] [--rerun-max N] [--shard I/N] [name ...]
  name       only the test files whose name contains it (e.g. "people" runs test_people.py and test_people_dashboard.py)
  -j N       how many quick-tier files run at once (default: half the processor cores, at least 2)
  --quick    only the quick tier: the files that never start Chrome (BL-246)
  --changed  only the test files that can reach a file changed since BASE (default: main; the working tree and untracked
             files count). A file is reached when it names a changed script, directly or through a module it names. A change
             to the rules, a skill, the settings or VERSION runs everything; a change to documents runs nothing. It never replaces
             the full run before a merge. Quick by default: the tests that name
             the changed script or helper (forecast.py reaches 1 test file, sweep.py 29, tracker.py 127 of 129). It does not
             follow a script through the scripts that import it, so a change to a script the dashboard uses can still break
             a dashboard test it skips. --deep follows them all, which for an engine script is the whole suite.
  --list     print the test files that would run and stop (with or without --changed)
  --clean    stop orphaned test live servers and Chromes (parent gone, running over 15 minutes) and remove test folders
             over an hour old that nothing uses, then stop; every run does this first (BL-247)
  --update-snapshots [screen …]
             record the screen snapshots' goldens again (BL-254: all, or the screens named), then list which changed;
             say in the commit why each one changed
  --flaky    list the files that failed under load and passed alone (dev/tests/.flaky.jsonl), most often first, and stop
  --repeat N run each file N times side by side (-j at a time; Chrome files also under the machine-wide cap), with no
             re-run alone, and report each file's passes under load: the proof that a flaky file is steady
  --stress N with --repeat: N processes spin the processor meanwhile, so a fast laptop is as slow as a CI runner
  --file-timeout S
             stop a test file that runs longer than S seconds (default 900, or CREAITE_FILE_TIMEOUT; 0: never): it fails
             as TIMEOUT, and it and everything it started (its live servers, its Chromes) are stopped through its own
             process group, never by name. The slowest file takes about 290 s on a CI runner, so 900 s is three times that
  --shard I/N
             run only shard I of N (1 to N) of the files chosen by the other options (CI #89: the Linux jobs run three each).
             Every file is in exactly one shard. They are balanced greedily, slowest first, by the times in
             dev/tools/shard_times.txt (read from a real run; a file it doesn't list counts as 30 s), never by this machine's
             last run, so every machine, and every CI job, computes the same split. Print one with --list.
  --max-fail N
             once N files have failed, start no more (the ones running finish) and report: a machine where everything
             fails says so in minutes, not at the job's time limit (default 0: no limit; CI passes it)
  --rerun-max N
             re-run failures alone only when at most N files failed (default 15, or CREAITE_RERUN_MAX). More than that is
             not load: something is broken for the whole machine (the macOS runner's Chrome, say), and re-running a hundred
             files one at a time only holds the job open until its time limit

BL-246 (Alan, 11-10-2026): each file is in the quick tier or the Chrome tier, read from the file (dev/tools/run_support.py).
Chrome-tier files run under a machine-wide cap (about 3 at once, CREAITE_CHROME_CAP), shared by every worktree's and
session's runs through lock files in /tmp/creaite-chrome-slots; a run that dies or is stopped lets its slots go at once.
Each file runs with a private TMPDIR (/tmp/cr<pid>/<n>), removed when the file ends, pass or fail; the run's folder is
removed when the run ends or is stopped (Ctrl+C, SIGTERM), and a run killed outright is cleaned up by the next one.

Each test file builds its own throwaway vault, Chrome profile and server port, so files can run side by side.
The slowest files start first, so the run takes about as long as the slowest file. A file that fails is run once
more on its own when the others have finished (Alan's rule: a file that fails under load and passes alone counts as
passing; it is named as such). Exits 1 if any file still fails, printing the end of its output.

BL-172: each file runs with CREAITE_TEST_TAG set to its name, so the vaults it makes are called
`creaite-test-<name>-…`; any still there when the file ends are named in a warning line (not a failure), and then
removed with the file's folder (BL-246: the disk filled on 11-10-2026 with seven sprints' leftovers).
"""
import argparse
import ast
import functools
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time

import proc_guard
import run_support as support
import split_dashboard
import suite_queue
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

TESTS = Path(__file__).resolve().parents[1] / "tests"
TIMES = TESTS / ".durations"          # last run's time per file, so the slowest start first (git-ignored)
LAST_FAILED = TESTS / ".last-failed"  # the files that failed in their last run, one per line: they start first next time (git-ignored)
SHARD_TIMES = Path(__file__).resolve().parent / "shard_times.txt" # "test_x.py seconds" from a real CI run (committed), for --shard
SHARD_DEFAULT = 30                    # seconds assumed for a test file the times don't list
FLAKY = TESTS / ".flaky.jsonl"        # one line each time a file failed under load and passed alone (git-ignored)
REPO = TESTS.parents[1]
EVERYTHING = ("VERSION", "system/creaite-rules.md", ".claude/", "system/config/")   # a change here can reach any test
FILE_TIMEOUT = float(os.environ.get("CREAITE_FILE_TIMEOUT") or 900)   # seconds; 0 means no limit (see --file-timeout)
# A file that is slow by design gets a longer limit of its own here (--file-timeout 0 still means none). Empty since #89: the
# shared behaviour test (once about 1000 s waiting on a browser for every screen) is five files of about 230 s each, well inside
# the default limit.
SLOW_FILES = {}
RERUN_MAX = int(os.environ.get("CREAITE_RERUN_MAX") or 15)            # more failures than this are not re-run alone
TIMED_OUT = -1000                     # the exit code a file gets when it was stopped for running too long
CI = bool(os.environ.get("GITHUB_ACTIONS"))   # on a runner, print a failure's output as it happens (folded), not only at the end
BULK_COPIER = {"test_tracker"}        # its Vault copies every script; that is having them, not using them
TEMPLATE_USERS = ("build_dashboard", "docx_tools", "report", "prep_page", "live_server", "minutes")   # read system/templates/


# ===== #89 (CI shards) =====
def shard_arg(text):
    """'I/N' as (I, N) with 1 <= I <= N, or an argparse error."""
    m = re.fullmatch(r"(\d+)/(\d+)", text.strip())
    if not m or not 1 <= int(m.group(1)) <= int(m.group(2)):
        raise argparse.ArgumentTypeError(f"{text!r}: expected I/N with 1 <= I <= N (for example 2/3)")
    return int(m.group(1)), int(m.group(2))


def shard_weights():
    """{test file name: seconds} from dev/tools/shard_times.txt (empty when the file is missing)."""
    out = {}
    if SHARD_TIMES.exists():
        for ln in SHARD_TIMES.read_text(encoding="utf-8").splitlines():
            name, _, secs = ln.partition(" ")
            if name and secs.strip().isdigit():
                out[name] = int(secs)
    return out


def shard(files, index, count, weights=None):
    """The files of shard `index` (1-based) of `count`. Greedy, slowest first, each to the lightest shard so far; ties go
    to the lowest shard and the name, so the split depends only on the names and the weights. Every file is in exactly one
    shard, and the same file list gives the same split on every machine."""
    weights = shard_weights() if weights is None else weights
    load, mine = [0] * count, []
    for f in sorted(files, key=lambda f: (-weights.get(f.name, SHARD_DEFAULT), f.name)):
        k = load.index(min(load))
        load[k] += weights.get(f.name, SHARD_DEFAULT)
        if k == index - 1:
            mine.append(f)
    return sorted(mine, key=lambda f: f.name)


def apply_shard(files, spec):
    """`files` narrowed to shard `spec` ((I, N) or None for all), saying so."""
    if not spec:
        return files
    mine = shard(files, *spec)
    print(f"--shard {spec[0]}/{spec[1]}: {len(mine)} of {len(files)} test files.", flush=True)
    return mine


def last_failed():
    """The set of file names that failed in their last run."""
    return set(LAST_FAILED.read_text(encoding="utf-8").split()) if LAST_FAILED.exists() else set()


def remember_failed(ran, failed):
    """Keep the failed file names: those of the files just run replaced by `failed`, the others kept (a partial run
    doesn't forget a failure it didn't re-check)."""
    keep = (last_failed() - set(ran)) | set(failed)
    try:
        LAST_FAILED.write_text("".join(f"{n}\n" for n in sorted(keep)), encoding="utf-8")
    except OSError:
        pass                              # a read-only checkout loses only the ordering


# ===== end #89 =====


# ===== BL-172 (sprint-polish-2) =====
def tag(f):
    """The file's name without `test_`, as make_vault puts it in each vault's name."""
    return f.stem[len("test_"):] if f.stem.startswith("test_") else f.stem


# ===== end BL-172 =====


def changed_paths(base):
    """Files changed since `base` (committed, staged, edited) and untracked ones, as repo-relative paths."""
    def git(*args):
        """The lines git prints."""
        r = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f"git {' '.join(args)} failed: {r.stderr.strip()} (is {base!r} a branch or commit?)")
        return [x for x in r.stdout.splitlines() if x]
    mb = git("merge-base", "HEAD", base)
    return sorted(set(git("diff", "--name-only", mb[0] if mb else base)) | set(git("ls-files", "-o", "--exclude-standard")))


@functools.lru_cache(maxsize=None)
def module_paths():
    """{module name: file} over the scripts, tools and tests."""
    return {p.stem: p for pat in ("system/scripts/*.py", "dev/tools/*.py", "dev/tests/*.py") for p in REPO.glob(pat)}


@functools.lru_cache(maxsize=None)
def module_graph():
    """{module: set of modules it uses} over the scripts, tools and tests. A module is used when the file imports it
    or runs it by name (a string such as "tracker.py"); words in comments and messages don't count."""
    mods = module_paths()
    graph = {}
    for m, p in mods.items():
        used = set()
        for n in ast.walk(ast.parse(p.read_text(encoding="utf-8", errors="replace"))):
            if isinstance(n, ast.Import):
                used.update(a.name.split(".")[0] for a in n.names)
            elif isinstance(n, ast.ImportFrom) and n.module:
                used.add(n.module.split(".")[0])
            elif m not in BULK_COPIER and isinstance(n, ast.Constant) and isinstance(n.value, str) and ".py" in n.value:
                used.update(re.findall(r"([A-Za-z_]\w*)\.py\b", n.value))
        graph[m] = (used & set(mods)) - {m}
    return graph


def changed_roots(paths):
    """(the modules that changed, or None and the reason when the change can reach any test)."""
    roots = set()
    for p in paths:
        if any(p == e or p.startswith(e) for e in EVERYTHING) or "/vendor/" in p:
            return None, f"{p} can reach any test"
        if p.endswith(".py") and p.split("/")[0] in ("system", "dev") and "/" in p:
            roots.add(Path(p).stem)
        elif p == "system/scripts/schema.sql":
            roots.add("tracker")
        elif p.startswith("system/templates/"):
            roots.update(TEMPLATE_USERS)
        elif p.startswith("system/"):
            return None, f"{p} can reach any test"
        # documents, mockups, release notes and the like reach nothing
    return roots, ""


def reach(roots, deep=False):
    """The modules that use one of `roots`. Quick (the default): the modules that name a changed script, and anything that
    names a changed helper (a dev/tests module that isn't a test file, such as live_browser). Deep: through scripts too,
    which reaches every browser test, since each starts the live server and the live server imports every script."""
    graph = module_graph()
    reached = set(roots) | {"test_" + r for r in roots if "test_" + r in graph}          # test_<module> tests <module>
    todo = list(reached)
    helpers = {m for m, p in module_paths().items() if p.parent.name == "tests" and not m.startswith("test_")}
    while todo:
        cur = todo.pop()
        for m, used in graph.items():
            if cur in used and m not in reached:
                reached.add(m)
                if deep or m in helpers or cur in helpers or cur in roots and m.startswith("test_"):
                    todo.append(m)
    return reached


def select(files, base, deep=False):
    """(the test files that can reach what changed, why); the whole list when the change can reach any test."""
    paths = changed_paths(base)
    roots, reason = changed_roots(paths)
    if roots is None:
        return list(files), reason
    if not roots:
        return [], "nothing that a test reads has changed"
    reached = reach(roots, deep)
    plural = "s" if len(paths) != 1 else ""
    return [f for f in files if f.stem in reached], f"{len(paths)} changed file{plural} since {base}: {', '.join(sorted(roots))}"


def failed_tests(out):
    """The test names a unittest run reports as FAIL or ERROR, in order (e.g. "Class.test_x")."""
    names = []
    for m in re.finditer(r"^(?:FAIL|ERROR): (\w+) \(([\w.]+)\)", out, re.M):
        where = m.group(2)                          # 3.11+: the whole ID; before: just the class
        full = where if where.endswith("." + m.group(1)) else f"{where}.{m.group(1)}"
        names.append(full[len("__main__."):] if full.startswith("__main__.") else full)
    return names


def result_line(name, code, secs, out, alone=False):
    """One file's result: OK or FAIL (TIMEOUT when it was stopped for running too long); a failure also names the tests
    that failed and its last error line, so a job cancelled before the end still says why its files failed."""
    took = f"{secs:.0f}s, alone" if alone else f"{secs:.0f}s"
    if code == 0:
        return f"OK    {name}  ({took})"
    line = f"FAIL  {name}  ({took}{', TIMEOUT' if code == TIMED_OUT else ''})"
    err = next((ln.strip() for ln in reversed(out.splitlines())
                if re.match(r"\s*(TIMEOUT:|\w*(Error|Exception)\b)", ln)), "")
    which = failed_tests(out)[:4]
    return line + (f"  {', '.join(which)}" if which else "") + (f" — {err[:200]}" if err else "")


def show_now(name, out):
    """On a CI runner, the end of a failed file's output at once, folded in the job's log (::group::)."""
    if CI:
        print(f"::group::{name} output (last 60 lines)\n" + "\n".join(out.splitlines()[-60:]) + "\n::endgroup::", flush=True)


def log_flaky(name, secs, out=""):
    """Remember a file that failed under load and passed alone, so the rule that counts it as passing stays visible, with
    which tests failed and the end of that output, so the flake can be diagnosed later."""
    with FLAKY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"file": name, "when": time.strftime("%Y-%m-%d %H:%M"), "alone_secs": round(secs),
                             "failed": failed_tests(out), "tail": out.splitlines()[-40:]}) + "\n")


def flaky_report():
    """Print the files that failed under load and passed alone, most often first."""
    if not FLAKY.exists():
        print("No file has failed under load and passed alone (nothing in .flaky.jsonl).")
        return
    rows = [json.loads(x) for x in FLAKY.read_text(encoding="utf-8").splitlines() if x.strip()]
    counts = {}
    for r in rows:
        c = counts.setdefault(r["file"], [0, r["when"]])
        c[0] += 1
        c[1] = max(c[1], r["when"])
    print(f"{len(rows)} failure(s) that passed alone, in {len(counts)} file(s):")
    for name, (n, last) in sorted(counts.items(), key=lambda kv: -kv[1][0]):
        print(f"  {n:3d}  {name}  (last {last})")
        latest = next((r for r in reversed(rows) if r["file"] == name and r.get("failed")), None)
        if latest:                                     # which tests, and the first error line (older entries have neither)
            err = next((ln.strip() for ln in latest.get("tail", []) if re.match(r"\s*\w*(Error|Exception)\b", ln)), "")
            print(f"        last failed: {', '.join(latest['failed'][:4])}" + (f" — {err[:140]}" if err else ""))


class Runner:
    """Runs test files, each in its own process group with a private TMPDIR; Chrome-tier files hold a machine-wide slot."""

    def __init__(self, timeout=FILE_TIMEOUT):
        self.timeout = timeout or None    # seconds a file may run before it is stopped (None: no limit)
        self.dir = support.RunDir()
        self.procs = set()
        self.lock = threading.Lock()

    def run(self, f, chrome=None):
        """Run one test file: (file, exit code, seconds, output, vaults it left behind)."""
        chrome = support.is_chrome(f) if chrome is None else chrome
        tmp = self.dir.for_file()
        slot = support.take_slot(say=lambda m: print(f"      {f.name} {m}", flush=True)) if chrome else None
        env = {**os.environ, "CREAITE_NO_LAUNCH": "1",           # BL-171: a test never starts Word or another app
               "CREAITE_TEST_TAG": tag(f),                         # BL-172: its vaults carry its name
               "TMPDIR": str(tmp), "TMP": str(tmp), "TEMP": str(tmp)}   # BL-246: everything it makes lands here
        if slot is not None:
            env["CREAITE_CHROME_SLOT"] = "1"                        # #89: it already holds a Chrome slot; browser_slots.hold() adds none
        t, p, out, timed_out = time.time(), None, [], False
        limit = self.timeout and max(self.timeout, SLOW_FILES.get(f.name, 0))      # None: no limit
        try:
            p = proc_guard.spawn([sys.executable, f.name], cwd=f.parent, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, env=env, pass_fds=() if slot is None else (slot,))   # BL-247: a watchdog too
            with self.lock:
                self.procs.add(p)
            reader = threading.Thread(target=lambda: out.append(p.stdout.read()), daemon=True)
            reader.start()
            try:
                p.wait(timeout=limit)  # the test itself, not its output: a leaked child may hold the pipe open
            except subprocess.TimeoutExpired:
                timed_out = True          # ci-macos-hang: a hung file fails here instead of holding the run to its time limit
                # SIGTERM to its group lets the test's own proc_guard stop the servers and Chromes it spawned (each in a
                # group of its own); after the grace, SIGKILL, and their watchdogs stop them when they see it go
                proc_guard.stop(p, grace=10)
            proc_guard.stop(p, grace=2)   # BL-247: whatever it started and left in its group (servers, Chromes) ends now
            reader.join(5)
            if timed_out:
                out.append(f"\nTIMEOUT: {f.name} ran over {limit:.0f}s (--file-timeout) and was stopped, with "
                           f"everything it started.\n")
        finally:
            with self.lock:
                self.procs.discard(p)
            if p is not None and p.returncode is None:
                proc_guard.stop(p, grace=2)
            support.give_slot(slot)
            left = support.RunDir.finish(tmp)
        code = TIMED_OUT if timed_out else p.returncode
        return f, code, time.time() - t, "".join(out), left

    def stop(self):
        """Kill every test still running, with what it started (its live server, its Chrome)."""
        with self.lock:
            procs = list(self.procs)
        for p in procs:
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except OSError:
                continue                  # already gone

    def close(self):
        """Remove the run's folder."""
        self.dir.close()


def rerun_alone(failed, runner, most=None):
    """Run each failed file once more on its own: a failure under load that passes alone counts (and is logged).
    More than `most` failures (--rerun-max) are not load, so none is run again.
    Returns (the files still failing, with their output; the files that passed alone)."""
    alone, still = [], []
    most = RERUN_MAX if most is None else most
    if len(failed) > most:
        print(f"\n{len(failed)} files failed, more than --rerun-max {most}: that is not load, so none is run again alone "
              f"(something is wrong for the whole machine; see the first failures below).", flush=True)
        return list(failed), []
    if failed:
        print(f"\nRunning {len(failed)} failed file{'s' if len(failed) != 1 else ''} again, one at a time…", flush=True)
    for name, out in failed:
        f, code, secs, out2, _ = runner.run(TESTS / name)
        print(result_line(name, code, secs, out2, alone=True), flush=True)
        if code == 0:
            alone.append((name, out))
            log_flaky(name, secs, out)
        else:
            still.append((name, out2))
    return still, alone


def slowest_first(files):
    """Sort `files` in place: the files that failed last time first, then slowest first by the last run's times (unknown
    files count as slow); return those times."""
    last = {}
    if TIMES.exists():
        for ln in TIMES.read_text(encoding="utf-8").splitlines():
            name, _, secs = ln.partition(" ")
            last[name] = float(secs or 0)
    bad = last_failed()
    files.sort(key=lambda f: (f.name not in bad, -last.get(f.name, 1e9)))
    return last


def execute(files, jobs, runner, max_fail=0):
    """Run the quick tier `jobs` at a time and the Chrome tier under the machine-wide cap, side by side. With `max_fail`
    (--max-fail), once that many files have failed no further file starts (those running finish), and the rest are named.
    Returns {file name: seconds}, [(failed file name, output)], [(file name, vaults left behind)]."""
    quick = [f for f in files if not support.is_chrome(f)]
    chrome = [f for f in files if support.is_chrome(f)]
    print(f"Running {len(files)} test file{'s' if len(files) != 1 else ''}: {len(quick)} quick ({jobs} at a time), "
          f"{len(chrome)} Chrome (at most {support.CHROME_CAP} on this machine, shared with other runs)…", flush=True)
    took, failed, leaks = {}, [], []
    qpool = ThreadPoolExecutor(max_workers=max(1, jobs))
    cpool = ThreadPoolExecutor(max_workers=max(1, min(jobs, support.CHROME_CAP)))
    try:
        futures = [qpool.submit(runner.run, f, False) for f in quick] + [cpool.submit(runner.run, f, True) for f in chrome]
        named = dict(zip(futures, quick + chrome))
        for fut in as_completed(futures):
            if fut.cancelled():
                continue
            f, code, secs, out, left = fut.result()
            took[f.name] = secs
            report(f.name, code, secs, out, left, leaks)
            if code:
                failed.append((f.name, out))
                if max_fail and len(failed) == max_fail:
                    stop_starting(futures, named, max_fail)
    finally:
        for pool in (qpool, cpool):
            pool.shutdown(wait=False, cancel_futures=True)
    return took, failed, leaks


def report(name, code, secs, out, left, leaks):
    """Print one file's result (and, on a CI runner, a failure's output at once); note the vaults it left behind."""
    print(result_line(name, code, secs, out), flush=True)
    if code:
        show_now(name, out)
    if left:
        leaks.append((name, left))
        print(f"WARN  {name} left {left} vault{'s' if left != 1 else ''} behind (removed with its folder)", flush=True)


def stop_starting(futures, named, max_fail):
    """--max-fail reached: cancel every file not yet started (those running finish) and name them."""
    skipped = [named[x].name for x in futures if x.cancel()]
    print(f"\n{max_fail} files have failed (--max-fail {max_fail}): no further file starts. Not run: "
          f"{len(skipped)} ({', '.join(skipped[:10])}{', …' if len(skipped) > 10 else ''}).\n", flush=True)


def stop_on_sigterm(_signum, _frame):
    """SIGTERM (a stopped task, a closed terminal) ends the run the way Ctrl+C does, so it cleans up."""
    raise KeyboardInterrupt


def update_snapshots(screens):
    """BL-254: record the goldens again (all, or the screens named) and say which changed. Deliberate: the commit says why."""
    os.environ["CREAITE_UPDATE_SNAPSHOTS"] = "1"
    os.environ["CREAITE_SNAPSHOT_ONLY"] = ",".join(screens)
    runner = Runner()
    try:
        _, code, secs, out, _ = runner.run(TESTS / "test_snapshots.py", chrome=True)
    finally:
        runner.close()
    if code:
        print(out[-3000:])
        return code
    changed = subprocess.run(["git", "status", "--short", "--", str(TESTS / "snapshots")], cwd=REPO,
                             capture_output=True, text=True).stdout.strip()
    print(f"Snapshots recorded in {secs:.0f}s." + (f" Changed or new:\n{changed}" if changed else " None changed."))
    return 0


def one_off(a):
    """--flaky, --clean or --update-snapshots: a command of its own, not a test run."""
    if a.flaky:
        flaky_report()
        return 0
    if a.clean:
        if support.clean() == (0, 0):
            print("Nothing to clean up.")
        return 0
    return update_snapshots(a.names)


def main(argv):
    ap = argparse.ArgumentParser(prog="run_tests.py")
    ap.add_argument("-j", type=int, default=max(2, (os.cpu_count() or 4) // 2))
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--changed", nargs="?", const="main", metavar="BASE")
    ap.add_argument("--deep", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--flaky", action="store_true")
    ap.add_argument("--clean", action="store_true")
    ap.add_argument("--update-snapshots", action="store_true")
    ap.add_argument("--repeat", type=int, default=0, metavar="N")
    ap.add_argument("--stress", type=int, default=0, metavar="N")
    ap.add_argument("--file-timeout", type=float, default=FILE_TIMEOUT, metavar="S")
    ap.add_argument("--rerun-max", type=int, default=RERUN_MAX, metavar="N")
    ap.add_argument("--shard", type=shard_arg, metavar="I/N")
    ap.add_argument("--max-fail", type=int, default=0, metavar="N")
    ap.add_argument("names", nargs="*")
    a = ap.parse_args(argv)
    if a.flaky or a.clean or a.update_snapshots:
        return one_off(a)
    files = [f for f in sorted(TESTS.glob("test_*.py")) if not a.names or any(n in f.name for n in a.names)]
    if a.quick:
        files = [f for f in files if not support.is_chrome(f)]
    if a.changed:
        files, why = select(files, a.changed, a.deep)
        print(f"--changed: {len(files)} of the test files ({why}).", flush=True)
    files = apply_shard(files, a.shard)
    if not files:
        print("No test files to run." if a.changed else "No test files match.")
        return 0 if a.changed else 1
    if a.list:
        print("\n".join(f"{f.name}{'  (Chrome)' if support.is_chrome(f) else ''}" for f in files))
        return 0
    if len(files) >= suite_queue.min_files():            # a big run takes its turn beside other agents' big runs (CI: off)
        suite_queue.wait_turn()
    return run_all(files, a.j, a.repeat, a.stress, timeout=a.file_timeout, rerun_max=a.rerun_max, max_fail=a.max_fail)


def repeat_line(f, code, secs, out):
    """One copy's result: OK or FAIL, and for a failure the tests that failed and its last error line."""
    return result_line(f.name, code, secs, out)


def repeat(files, n, jobs, stress=0, timeout=FILE_TIMEOUT):
    """Run each of `files` `n` times, `jobs` at a time (Chrome files also under the machine-wide cap), interleaved so each
    copy runs beside the others; no re-run alone. `stress` processes spin the processor meanwhile, so a fast laptop is as
    slow as a shared CI runner. Prints each copy's result, then the passes per file."""
    runner, start, results = Runner(timeout), time.time(), {f.name: [] for f in files}
    pool = ThreadPoolExecutor(max_workers=max(1, jobs))
    burners = [subprocess.Popen([sys.executable, "-c", "while True: pass"]) for _ in range(max(0, stress))]
    spin = f", {stress} processes spinning" if stress else ""
    print(f"Running {len(files)} file(s) {n} times each, {jobs} at a time, no re-run alone{spin}…", flush=True)
    try:
        for fut in as_completed([pool.submit(runner.run, f) for _ in range(n) for f in files]):
            f, code, secs, out, _ = fut.result()
            results[f.name].append(code == 0)
            print(repeat_line(f, code, secs, out), flush=True)
    except KeyboardInterrupt:
        print("\nStopped.", flush=True)
        return 130
    finally:
        for b in burners:
            b.kill()
        pool.shutdown(wait=False, cancel_futures=True)
        runner.stop()
        runner.close()
    print(f"\nUnder load ({jobs} at a time{spin}, {time.time() - start:.0f}s):")
    for name, oks in results.items():
        print(f"  {sum(oks)}/{len(oks)}  {name}")
    return 0 if all(all(v) for v in results.values()) else 1


def run_all(files, jobs, copies=0, stress=0, timeout=FILE_TIMEOUT, rerun_max=None, max_fail=0):
    """Run `files`, re-run failures alone, report; always remove the run's temporary folders, even when stopped.
    With `copies` (--repeat), run that many copies of each under load instead, and report each file's passes."""
    support.clean()                       # BL-247: orphans and stale folders from earlier runs, before this one adds load
    signal.signal(signal.SIGTERM, stop_on_sigterm)
    if copies:
        return repeat(files, copies, jobs, stress, timeout)
    stale = split_dashboard.stale()       # BL-231 step 2a: the tests read the built page; never rebuilt behind your back
    if stale:
        print(f"Warning: {stale}. The tests run against the page as it is, and test_dashboard_split fails.", flush=True)
    last = slowest_first(files)
    start, runner = time.time(), Runner(timeout)
    try:
        took, failed, leaks = execute(files, jobs, runner, max_fail)
        TIMES.write_text("".join(f"{k} {v:.1f}\n" for k, v in sorted({**last, **took}.items())), encoding="utf-8")
        remember_failed([f.name for f in files], [n for n, _ in failed])
        failed, alone = rerun_alone(failed, runner, rerun_max)
    except KeyboardInterrupt:
        runner.stop()
        print("\nStopped. The tests still running were ended and their temporary folders removed.", flush=True)
        return 130
    finally:
        runner.stop()
        runner.close()
    for name, out in alone:
        which = failed_tests(out)
        print(f"Passed alone after failing under load: {name}" + (f" ({', '.join(which[:4])} failed)" if which else "")
              + " (logged; python3 dev/tools/run_tests.py --flaky)")
    for name, out in failed:
        print(f"\n===== {name} =====\n" + "\n".join(out.splitlines()[-80:]))
    not_run = len(files) - len(took)
    print(f"\n{len(took) - len(failed)} passed, {len(failed)} failed" + (f", {not_run} not run (--max-fail)" if not_run else "")
          + f", in {time.time() - start:.0f}s.")
    if leaks:
        print("Vaults left behind (now removed): " + ", ".join(f"{n} by {name}" for name, n in leaks) + ".")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
