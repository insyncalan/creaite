"""BL-247: every live server and headless Chrome a test starts ends when its test ends, however it ends (development only;
standard library only).

`spawn(cmd, …)` starts a process in its own process group (`start_new_session`) and a watchdog beside it. `stop(p)` ends
the whole group: SIGTERM, then SIGKILL after a grace period. Four ways out, all covered:
- **Normally or on a failure:** the test's tearDown or addCleanup calls `stop` (live_browser, cdp.Browser.close).
- **On exit:** `atexit` stops anything still running when the test process ends.
- **On Ctrl+C or Stop (SIGTERM, SIGINT, SIGHUP):** a handler stops everything, then lets the signal end the process.
- **When the test process dies outright (SIGKILL, a crash):** the watchdog, a tiny separate process, sees its parent go
  and stops the group itself. Chrome's helpers and the live server can't notice that on their own.

run_tests.py starts each test file through `spawn` too, so a runner killed mid-run takes its tests down, and they take
their servers and Chromes down. Windows has no process groups or these signals: there `spawn` is a plain Popen.
"""
import atexit
import os
import signal
import subprocess
import sys
import threading

POSIX = os.name == "posix"
GRACE = 5                                 # seconds between SIGTERM and SIGKILL
_LIVE = set()
_LOCK = threading.Lock()

WATCHDOG = r"""
import os, signal, sys, time
parent, group, grace = int(sys.argv[1]), int(sys.argv[2]), float(sys.argv[3])
def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
def group_alive():
    try:
        os.killpg(group, 0)
        return True
    except OSError:
        return False
while group_alive():
    if not alive(parent) or os.getppid() == 1:
        try:
            os.killpg(group, signal.SIGTERM)
        except OSError:
            break
        end = time.time() + grace
        while time.time() < end and group_alive():
            time.sleep(0.1)
        try:
            os.killpg(group, signal.SIGKILL)
        except OSError:
            pass
        break
    time.sleep(0.5)
"""


def spawn(cmd, watch=True, **kw):
    """Popen `cmd` in its own process group, remembered so it is stopped on exit or on a stop signal, and (with `watch`)
    with a watchdog that ends the group if this process dies without stopping it."""
    if not POSIX:
        return subprocess.Popen(cmd, **kw)
    _install()
    p = subprocess.Popen(cmd, start_new_session=True, **kw)
    with _LOCK:
        _LIVE.add(p)
    if watch:
        subprocess.Popen([sys.executable, "-c", WATCHDOG, str(os.getpid()), str(p.pid), str(GRACE)],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True, close_fds=True)
    return p


def stop(p, grace=GRACE):
    """End `p` and everything in its process group: SIGTERM, then SIGKILL after `grace` seconds. Safe to call twice."""
    if p is None:
        return
    with _LOCK:
        _LIVE.discard(p)
    if not POSIX:
        p.terminate()
        _wait_or(p, grace, p.kill)
        return
    _signal_group(p.pid, signal.SIGTERM)
    _wait_or(p, grace, lambda: _signal_group(p.pid, signal.SIGKILL))
    _signal_group(p.pid, signal.SIGKILL)  # helpers the leader didn't take with it (Chrome's renderers, a server's runs)


def _wait_or(p, grace, then):
    try:
        p.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        then()
        try:
            p.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            pass                          # unkillable for now; the watchdog and --clean are the backstops


def _signal_group(pgid, sig):
    try:
        os.killpg(pgid, sig)
    except OSError:
        pass                              # the group has gone already


def stop_all():
    """Stop every process started with `spawn` that is still running."""
    with _LOCK:
        live = list(_LIVE)
    for p in live:
        stop(p, grace=2)


_INSTALLED = []


def _install():
    """Once per process: stop everything at exit and on SIGTERM, SIGINT or SIGHUP, then let the signal do what it did."""
    if _INSTALLED:
        return
    _INSTALLED.append(True)
    atexit.register(stop_all)
    if threading.current_thread() is not threading.main_thread():
        return                            # signal handlers can only be set from the main thread; atexit still applies
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        before = signal.getsignal(sig)

        def handler(signum, frame, before=before):
            """Stop what we started, then do what the signal did before (default: end the process)."""
            stop_all()
            if callable(before):
                before(signum, frame)
            elif before == signal.SIG_IGN:
                return
            else:
                signal.signal(signum, signal.SIG_DFL)
                os.kill(os.getpid(), signum)
        signal.signal(sig, handler)
