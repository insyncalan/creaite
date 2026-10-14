"""Shared set-up for the tests that run the real live server and drive a real browser (BL-76, BL-77).

`LiveBrowserCase` starts the live server once per test class in a throwaway vault, and opens a fresh headless Chrome
(dev/tools/cdp.py) for every test. Override `load(v)` to put data in the vault. Skipped when Chrome isn't installed.
"""
import os
import re
import socket
import subprocess
import sys
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


def theme_names():
    """The dashboard's named themes, from its THEMES list, so theme checks follow new themes by themselves (BL-40, nine in 1.5.1)."""
    page = readable_page()     # BL-231: the source; the bundle reprints the code
    return tuple(re.findall(r'\{id:"([^"]+)"', re.search(r"const THEMES=\[(.*?)\];", page, re.S).group(1)))


def pin_page_clock(b, now):
    """Pin the page's clock to `now` ("YYYY-MM-DD HH:MM", as CREAITE_NOW pins the server's), from there on running, and
    reload the page under it. Date() and Date.now() read the pinned time; Date with arguments is unchanged."""
    from datetime import datetime
    t = datetime.strptime(now, "%Y-%m-%d %H:%M")
    b.call("Page.addScriptToEvaluateOnNewDocument", source="""(()=>{ const R=Date, off=new R(%d,%d,%d,%d,%d).getTime()-R.now();
  class D extends R{ constructor(...a){ if(a.length) super(...a); else super(R.now()+off); } static now(){ return R.now()+off; } }
  window.Date=D; })();""" % (t.year, t.month - 1, t.day, t.hour, t.minute))
    b.reload("typeof go==='function' && LIVE")


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@unittest.skipUnless(CHROME.exists(), "Google Chrome not installed")
class LiveBrowserCase(unittest.TestCase):
    shared_server = False      # True: one vault and server for the whole class (tests must not change data)
    width, height = 1400, 1000
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
        cls.proc = proc_guard.spawn([sys.executable, str(cls.v.root / "system/scripts/live_server.py")],   # BL-247
                                    env={**os.environ, "CREAITE_PORT": str(cls.port), **cls.server_env()},
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.time() + 30            # dev-test-steadiness: it gave up silently after 10 s; a loaded runner can need more
        while True:
            try:
                urllib.request.urlopen(cls.base + "/health", timeout=1)
                break
            except OSError:
                if time.time() > deadline or cls.proc.poll() is not None:
                    raise
                time.sleep(0.1)

    @classmethod
    def stop_server(cls):
        # BL-172 (sprint-polish-2): safe to call twice and after a start that failed half-way, so it can be a cleanup
        proc, cls.proc = getattr(cls, "proc", None), None
        proc_guard.stop(proc, grace=10)                # BL-247: the server and every run it started
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
