"""Shared set-up for the tests that run the real live server and drive a real browser (BL-76, BL-77).

`LiveBrowserCase` starts the live server once per test class in a throwaway vault, and opens a fresh headless Chrome
(dev/tools/cdp.py) for every test. Override `load(v)` to put data in the vault. Skipped when Chrome isn't installed.
"""
import os
import re
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import proc_guard  # noqa: E402
from test_dashboard import CHROME, populate  # noqa: E402
from test_tracker import Vault  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from split_dashboard import readable_page  # noqa: E402


# Alan, 16-10-2026 (spend): theme checks run on the creaite and Cursor palettes only, light and dark. Every loop over the
# palettes in the tests uses this one list; the product's themes (and test_help's counts) are untouched.
TEST_PALETTES = ("creaite", "Cursor")
TEST_PALETTES_JS = "[" + ",".join('"%s"' % p for p in TEST_PALETTES) + "]"


def theme_names():
    """The dashboard's named themes, from its THEMES list, so theme checks follow new themes by themselves (BL-40, nine in 1.5.1)."""
    page = readable_page()     # BL-231: the source; the bundle reprints the code
    return tuple(re.findall(r'\{id:"([^"]+)"', re.search(r"const THEMES=\[(.*?)\];", page, re.S).group(1)))


def pin_page_clock(b, now):
    """Pin the page's clock to `now` ("YYYY-MM-DD HH:MM", as CREAITE_NOW pins the server's), from there on running, and
    reload the page under it. Date() and Date.now() read the pinned time; Date with arguments is unchanged."""
    from test_dashboard import page_clock_js
    b.call("Page.addScriptToEvaluateOnNewDocument", source=page_clock_js(now))
    b.reload("typeof go==='function' && LIVE")


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@unittest.skipUnless(CHROME.exists(), "Google Chrome not installed")
class LiveBrowserCase(unittest.TestCase):
    shared_server = False      # True: one vault and server for the whole class (tests must not change data)
    width, height = 1400, 1000
    pin_clock = True           # #178: under CREAITE_NOW the page's clock is pinned too (a class whose server runs on the real clock sets False)
    reduced_motion = True      # BL-136: the page loads with the system's reduced motion on (a motion test sets False)

    @classmethod
    def load(cls, v):
        populate(v)

    @classmethod
    def server_env(cls):
        """Extra environment for the live server (a stand-in `claude`, a fixed clock…)."""
        return {}

    @classmethod
    def start_server(cls):
        cls.v = Vault()
        cls.load(cls.v)
        cls.port = free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        # ci-macos-hang: the server's output goes to a file outside the vault (not DEVNULL), and PYTHONFAULTHANDLER lets a
        # SIGABRT print where every thread is, so a server that never answers says why instead of failing silently
        fd, cls.server_log = tempfile.mkstemp(prefix="creaite-server-", suffix=".log")
        with os.fdopen(fd, "wb") as log:
            cls.proc = proc_guard.spawn([sys.executable, str(cls.v.root / "system/scripts/live_server.py")],   # BL-247
                                        env={**os.environ, "CREAITE_PORT": str(cls.port), "PYTHONFAULTHANDLER": "1",
                                             **cls.server_env()}, stdout=log, stderr=log)
        started = time.time()
        deadline = started + 30                # dev-test-steadiness: it gave up silently after 10 s; a loaded runner can need more
        while True:
            try:
                urllib.request.urlopen(cls.base + "/health", timeout=1)
                break
            except OSError as e:
                if time.time() > deadline or cls.proc.poll() is not None:
                    raise RuntimeError(cls.server_trouble(e, time.time() - started)) from e
                time.sleep(0.1)

    @classmethod
    def server_trouble(cls, err, secs):
        """Why the server never answered /health: whether it is still running, and the end of its output (with every
        thread's stack when it was still running: SIGABRT and PYTHONFAULTHANDLER)."""
        running = cls.proc.poll() is None
        if running:
            try:
                os.kill(cls.proc.pid, signal.SIGABRT)
                cls.proc.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                pass
        try:
            lines = Path(cls.server_log).read_text(encoding="utf-8", errors="replace").splitlines()
            tail = [ln for ln in lines if not ln.lstrip().startswith("Binary file")][-60:]   # 3.14 adds the C stack too
        except OSError:
            tail = []
        state = "still running, not answering" if running else f"exited with {cls.proc.returncode}"
        return (f"The live server on port {cls.port} didn't answer /health after {secs:.0f}s ({state}; last error: {err}). "
                "Its output:\n" + ("\n".join(tail) or "(none)"))

    @classmethod
    def stop_server(cls):
        # BL-172 (sprint-polish-2): safe to call twice and after a start that failed half-way, so it can be a cleanup
        proc, cls.proc = getattr(cls, "proc", None), None
        proc_guard.stop(proc, grace=10)                # BL-247: the server and every run it started
        log, cls.server_log = getattr(cls, "server_log", None), None
        if log:
            Path(log).unlink(missing_ok=True)
        v, cls.v = getattr(cls, "v", None), None
        if v:
            v.cleanup()

    @classmethod
    def setUpClass(cls):
        if cls.shared_server:
            cls.addClassCleanup(cls.stop_server)      # BL-172: runs even when setUpClass fails after the vault is made
            cls.start_server()

    @classmethod
    def tearDownClass(cls):
        if cls.shared_server:
            cls.stop_server()

    def setUp(self):
        from cdp import Browser
        if not self.shared_server:
            self.addCleanup(self.stop_server)         # BL-172: a setUp that fails (here or in a subclass) still removes its vault
            self.start_server()
        self.addCleanup(self._close_browser)
        for attempt in (1, 2):                 # a headless Chrome that dies as it starts (seen under heavy load) is started once more
            self.b = Browser(self.width, self.height, reduced_motion=self.reduced_motion)
            try:
                self.b.goto(self.base + "/")
                self.b.wait("typeof go==='function' && LIVE")
                if self.pin_clock and os.environ.get("CREAITE_NOW"):   # #178: a pinned run pins the page too, so page and data agree
                    pin_page_clock(self.b, os.environ["CREAITE_NOW"])
                break
            except ConnectionError:
                self.b.close()
                if attempt == 2:
                    raise

    def _close_browser(self):
        b, self.b = getattr(self, "b", None), None
        if b:
            b.close()

    def tearDown(self):
        self._close_browser()
        if not self.shared_server:
            self.stop_server()
