"""Run creaite's test files in parallel and report each one (development only).

Run: python3 dev/tools/run_tests.py [-j N] [--quick] [--changed [BASE]] [--deep] [--list] [--flaky] [--clean]
                                    [--repeat N [--stress N]] [name ...]
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
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

TESTS = Path(__file__).resolve().parents[1] / "tests"
TIMES = TESTS / ".durations"          # last run's time per file, so the slowest start first (git-ignored)
FLAKY = TESTS / ".flaky.jsonl"        # one line each time a file failed under load and passed alone (git-ignored)
REPO = TESTS.parents[1]
EVERYTHING = ("VERSION", "system/creaite-rules.md", ".claude/", "system/config/")   # a change here can reach any test
BULK_COPIER = {"test_tracker"}        # its Vault copies every script; that is having them, not using them
TEMPLATE_USERS = ("build_dashboard", "docx_tools", "report", "prep_page", "live_server", "minutes")   # read system/templates/


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

    def __init__(self):
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
        t, p, out = time.time(), None, []
        try:
            p = proc_guard.spawn([sys.executable, f.name], cwd=f.parent, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, env=env, pass_fds=() if slot is None else (slot,))   # BL-247: a watchdog too
            with self.lock:
                self.procs.add(p)
            reader = threading.Thread(target=lambda: out.append(p.stdout.read()), daemon=True)
            reader.start()
            p.wait()                      # the test itself, not its output: a leaked child may hold the pipe open
            proc_guard.stop(p, grace=2)   # BL-247: whatever it started and left in its group (servers, Chromes) ends now
            reader.join(5)
        finally:
            with self.lock:
                self.procs.discard(p)
            if p is not None and p.returncode is None:
                proc_guard.stop(p, grace=2)
            support.give_slot(slot)
            left = support.RunDir.finish(tmp)
        return f, p.returncode, time.time() - t, "".join(out), left

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


def rerun_alone(failed, runner):
    """Run each failed file once more on its own: a failure under load that passes alone counts (and is logged).
    Returns (the files still failing, with their output; the files that passed alone)."""
    alone, still = [], []
    if failed:
        print(f"\nRunning {len(failed)} failed file{'s' if len(failed) != 1 else ''} again, one at a time…", flush=True)
    for name, out in failed:
        f, code, secs, out2, _ = runner.run(TESTS / name)
        print(f"{'OK  ' if code == 0 else 'FAIL'}  {name}  ({secs:.0f}s, alone)", flush=True)
        if code == 0:
            alone.append((name, out))
            log_flaky(name, secs, out)
        else:
            still.append((name, out2))
    return still, alone


def slowest_first(files):
    """Sort `files` in place, slowest first by the last run's times (unknown files count as slow); return those times."""
    last = {}
    if TIMES.exists():
        for ln in TIMES.read_text(encoding="utf-8").splitlines():
            name, _, secs = ln.partition(" ")
            last[name] = float(secs or 0)
    files.sort(key=lambda f: -last.get(f.name, 1e9))
    return last


def execute(files, jobs, runner):
    """Run the quick tier `jobs` at a time and the Chrome tier under the machine-wide cap, side by side.
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
        for fut in as_completed(futures):
            f, code, secs, out, left = fut.result()
            took[f.name] = secs
            print(f"{'OK  ' if code == 0 else 'FAIL'}  {f.name}  ({secs:.0f}s)", flush=True)
            if left:
                leaks.append((f.name, left))
                print(f"WARN  {f.name} left {left} vault{'s' if left != 1 else ''} behind (removed with its folder)", flush=True)
            if code:
                failed.append((f.name, out))
    finally:
        for pool in (qpool, cpool):
            pool.shutdown(wait=False, cancel_futures=True)
    return took, failed, leaks


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
    if not files:
        print("No test files to run." if a.changed else "No test files match.")
        return 0 if a.changed else 1
    if a.list:
        print("\n".join(f"{f.name}{'  (Chrome)' if support.is_chrome(f) else ''}" for f in files))
        return 0
    return run_all(files, a.j, a.repeat, a.stress)


def repeat_line(f, code, secs, out):
    """One copy's result: OK or FAIL, and for a failure the tests that failed and its last error line."""
    line = f"{'OK  ' if code == 0 else 'FAIL'}  {f.name}  ({secs:.0f}s)"
    if code:
        err = next((ln.strip() for ln in reversed(out.splitlines()) if re.match(r"\s*\w*(Error|Exception)\b", ln)), "")
        line += f"  {', '.join(failed_tests(out)[:4])}" + (f" — {err[:200]}" if err else "")
    return line


def repeat(files, n, jobs, stress=0):
    """Run each of `files` `n` times, `jobs` at a time (Chrome files also under the machine-wide cap), interleaved so each
    copy runs beside the others; no re-run alone. `stress` processes spin the processor meanwhile, so a fast laptop is as
    slow as a shared CI runner. Prints each copy's result, then the passes per file."""
    runner, start, results = Runner(), time.time(), {f.name: [] for f in files}
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


def run_all(files, jobs, copies=0, stress=0):
    """Run `files`, re-run failures alone, report; always remove the run's temporary folders, even when stopped.
    With `copies` (--repeat), run that many copies of each under load instead, and report each file's passes."""
    support.clean()                       # BL-247: orphans and stale folders from earlier runs, before this one adds load
    signal.signal(signal.SIGTERM, stop_on_sigterm)
    if copies:
        return repeat(files, copies, jobs, stress)
    stale = split_dashboard.stale()       # BL-231 step 2a: the tests read the built page; never rebuilt behind your back
    if stale:
        print(f"Warning: {stale}. The tests run against the page as it is, and test_dashboard_split fails.", flush=True)
    last = slowest_first(files)
    start, runner = time.time(), Runner()
    try:
        took, failed, leaks = execute(files, jobs, runner)
        TIMES.write_text("".join(f"{k} {v:.1f}\n" for k, v in sorted({**last, **took}.items())), encoding="utf-8")
        failed, alone = rerun_alone(failed, runner)
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
    print(f"\n{len(files) - len(failed)} passed, {len(failed)} failed, in {time.time() - start:.0f}s.")
    if leaks:
        print("Vaults left behind (now removed): " + ", ".join(f"{n} by {name}" for name, n in leaks) + ".")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
