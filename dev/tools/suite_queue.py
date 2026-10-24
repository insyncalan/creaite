"""A machine-wide queue for big test runs (dev speed): several agents or terminals each starting a full or sharded run on one
machine otherwise run side by side, every file runs several times slower, and nobody finishes sooner. This lets the runs take
turns, first come first served, like browser_slots does for Chrome.

`wait_turn()` is called by run_tests.py before a run of CREAITE_QUEUE_MIN_FILES files or more (default 60); smaller runs (a few
files, --changed) never wait. A run takes a ticket (a file in the system temp folder, `creaite-suite-queue/<time>-<pid>`) and
holds an exclusive flock on it until the process ends, so a crash frees its place at once. It may start when fewer than
CREAITE_SUITE_RUNS (default 1) live tickets are older than its own. It says where it stands while it waits.

Off in CI (CI or GITHUB_ACTIONS set: a runner is one job's), with CREAITE_SUITE_RUNS=0 or "off", and where there is no flock.
CREAITE_QUEUE_WAIT: seconds to wait (default 14400, four hours), then it fails loudly naming the runs ahead.
"""
import atexit
import os
import sys
import tempfile
import time
from pathlib import Path

try:
    import fcntl
except ImportError:                 # Windows: no flock; no queue there
    fcntl = None

DEFAULT_RUNS = 1
DEFAULT_WAIT = 14400
DEFAULT_MIN_FILES = 60
_ticket = []                        # this process's ticket (kept so the lock lives until exit)


def runs_allowed(env=None):
    """How many big runs may go at once: CREAITE_SUITE_RUNS, or 0 when the queue is off (CI, "off", 0, no flock)."""
    env = os.environ if env is None else env
    if fcntl is None or env.get("CI") or env.get("GITHUB_ACTIONS"):
        return 0
    raw = (env.get("CREAITE_SUITE_RUNS") or "").strip().lower()
    if raw in ("off", "0", "no", "false"):
        return 0
    try:
        return max(0, int(raw)) if raw else DEFAULT_RUNS
    except ValueError:
        return DEFAULT_RUNS


def min_files(env=None):
    """How many files make a run big enough to queue (CREAITE_QUEUE_MIN_FILES)."""
    env = os.environ if env is None else env
    try:
        return max(1, int(env.get("CREAITE_QUEUE_MIN_FILES") or DEFAULT_MIN_FILES))
    except ValueError:
        return DEFAULT_MIN_FILES


def queue_folder(folder=None):
    """The folder of tickets (/tmp on a Mac or Linux)."""
    base = Path(folder or ("/tmp" if os.name == "posix" else tempfile.gettempdir()))
    d = base / "creaite-suite-queue"
    d.mkdir(parents=True, exist_ok=True)
    return d


class Ticket:
    """One place in the queue: a file and its open, locked handle. release() gives it up early (a test)."""

    def __init__(self, path, fh):
        self.path, self.fh = path, fh

    def release(self):
        if self.fh:
            try:
                fcntl.flock(self.fh, fcntl.LOCK_UN)
            finally:
                self.fh.close()
                self.fh = None
            try:
                self.path.unlink()
            except OSError:
                pass


def _alive(path):
    """Whether the process that made a ticket still holds it (its flock can't be taken)."""
    try:
        fh = open(path, "a+")
    except OSError:
        return False
    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        fh.close()
        return True
    fcntl.flock(fh, fcntl.LOCK_UN)       # nobody holds it: a dead run's leftover
    fh.close()
    try:
        path.unlink()
    except OSError:
        pass
    return False


def ahead(folder, mine):
    """The live tickets older than `mine`, oldest first (dead ones are removed)."""
    older = [p for p in sorted(folder.glob("*-*")) if p.name < mine.name and p != mine]
    return [p for p in older if _alive(p)]


def take_ticket(folder=None):
    """Join the queue now (the order is the ticket's time, then pid)."""
    d = queue_folder(folder)
    path = d / f"{time.time_ns():020d}-{os.getpid()}"
    fh = open(path, "a+")
    fcntl.flock(fh, fcntl.LOCK_EX)
    fh.seek(0)
    fh.truncate()
    fh.write(f"{os.getpid()} {' '.join(sys.argv[:4])}")
    fh.flush()
    return Ticket(path, fh)


def wait_turn(n=None, wait=None, folder=None, poll=1.0, say=None):
    """Block until fewer than n live runs are ahead, then return the Ticket (held until the process ends). None if the queue is off."""
    n = runs_allowed() if n is None else n
    if not n:
        return None
    say = say or (lambda m: print(m, file=sys.stderr, flush=True))
    if wait is None:
        try:
            wait = float(os.environ.get("CREAITE_QUEUE_WAIT") or DEFAULT_WAIT)
        except ValueError:
            wait = DEFAULT_WAIT
    t = take_ticket(folder)
    start, last = time.time(), None
    while True:
        in_front = ahead(t.path.parent, t.path)
        if len(in_front) < n:
            if last is not None:
                say(f"Your turn: {time.time() - start:.0f}s in the queue.")
            _ticket.append(t)
            atexit.register(t.release)
            return t
        if len(in_front) != last:
            last = len(in_front)
            say(f"Waiting for a test-run turn: {last} run(s) ahead on this machine "
                f"(pids {', '.join(p.read_text().split()[0] for p in in_front if p.exists() and p.read_text().strip())}).")
        if time.time() - start > wait:
            t.release()
            raise TimeoutError(f"No turn after {wait:.0f}s: {len(in_front)} run(s) ahead. Stop one, or set CREAITE_SUITE_RUNS (more at once, or off).")
        time.sleep(poll)
