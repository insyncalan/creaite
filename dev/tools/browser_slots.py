"""#89: a machine-wide limit on how many test processes drive Chrome at once (several agents or terminals on one laptop
otherwise start dozens of Chrome windows and every browser test times out).

This covers a test file run directly (`python3 dev/tests/test_x.py`) or by any other means; run_tests.py already holds a slot of
its own for each Chrome file it starts (run_support.take_slot, marked by CREAITE_CHROME_SLOT in the file's environment), and
then `hold()` does nothing. `hold()` takes one of N slots, each an exclusive flock on a file in the system temp folder
(`creaite-browser-slot-K.lock`; /tmp itself on a Mac or Linux, not the private TMPDIR run_tests gives a file),
for the rest of this process: the first Chrome start (dev/tools/cdp.py Browser) or browser test class (live_browser.py) calls
it, and the operating system lets the slot go when the process ends, even if it crashed. It waits (up to 20 minutes) for a
free slot, saying so, then fails loudly naming the slot files and the process that holds each.

CREAITE_BROWSER_SLOTS: the number of slots (default 2); 0 or "off" turns the limit off. In CI (CI or GITHUB_ACTIONS set) it is
off: a runner is one job's. CREAITE_BROWSER_WAIT: seconds to wait (default 1200).
"""
import atexit
import os
import sys
import tempfile
import time
from pathlib import Path

try:
    import fcntl
except ImportError:                # Windows: no flock; the limit is off there
    fcntl = None

DEFAULT_SLOTS = 2
DEFAULT_WAIT = 1200
_held = []                         # the Slot this process holds (kept so the lock lives until exit)


def slot_count(env=None):
    """How many slots: CREAITE_BROWSER_SLOTS, or 0 when the limit is off (a CI run, "off", 0, no flock)."""
    env = os.environ if env is None else env
    if fcntl is None or env.get("CI") or env.get("GITHUB_ACTIONS"):
        return 0
    raw = (env.get("CREAITE_BROWSER_SLOTS") or "").strip().lower()
    if raw in ("off", "0", "no", "false"):
        return 0
    try:
        return max(0, int(raw)) if raw else DEFAULT_SLOTS
    except ValueError:
        return DEFAULT_SLOTS


def slot_files(n, folder=None):
    """The n slot files (in `folder`, or /tmp)."""
    folder = Path(folder or ("/tmp" if os.name == "posix" else tempfile.gettempdir()))
    return [folder / f"creaite-browser-slot-{k}.lock" for k in range(1, n + 1)]


class Slot:
    """One held slot. release() lets it go early (a test); otherwise the process's end does."""

    def __init__(self, path, fh):
        """The slot file and its open, locked handle."""
        self.path, self.fh = path, fh

    def release(self):
        """Let the slot go (safe to call twice)."""
        if self.fh:
            try:
                fcntl.flock(self.fh, fcntl.LOCK_UN)
            finally:
                self.fh.close()
                self.fh = None


def _holder(path):
    try:
        return Path(path).read_text().strip() or "unknown"
    except OSError:
        return "unknown"


def acquire(n, wait=DEFAULT_WAIT, folder=None, poll=0.25):
    """A Slot out of n (an exclusive flock), waiting up to `wait` seconds; TimeoutError naming the files and holders if none frees."""
    files = slot_files(n, folder)
    start, told = time.time(), False
    while True:
        for p in files:
            fh = open(p, "a+")
            try:
                fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                fh.close()
                continue
            fh.seek(0)
            fh.truncate()
            fh.write(str(os.getpid()))
            fh.flush()
            return Slot(p, fh)
        if time.time() - start > wait:
            raise TimeoutError(f"No browser slot free after {wait:.0f}s: all {n} are held ("
                               + "; ".join(f"{p} by pid {_holder(p)}" for p in files)
                               + "). Other test runs on this machine are driving Chrome; wait, stop one, or set "
                                 "CREAITE_BROWSER_SLOTS (more slots, or off).")
        if not told and time.time() - start > 5:
            told = True
            print(f"Waiting for a browser slot ({n} on this machine; held by pid "
                  + ", ".join(_holder(p) for p in files) + ")...", file=sys.stderr, flush=True)
        time.sleep(poll)


def hold():
    """Take a slot for the rest of this process (once; a no-op when the limit is off or this process has one)."""
    if _held:
        return _held[0]
    if os.environ.get("CREAITE_CHROME_SLOT"):      # run_tests.py started this file and holds a slot for it
        return None
    n = slot_count()
    if not n:
        return None
    try:
        wait = float(os.environ.get("CREAITE_BROWSER_WAIT") or DEFAULT_WAIT)
    except ValueError:
        wait = DEFAULT_WAIT
    _held.append(acquire(n, wait))
    atexit.register(_held[0].release)           # a tidy close; a crash is the system's release
    return _held[0]
