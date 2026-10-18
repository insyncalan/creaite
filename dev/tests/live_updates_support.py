"""Shared fixture for the BL-253 live-updates tests (test_live_updates.py, test_live_updates_events.py, test_live_updates_page.py): the stream reader, the server case and the page helpers."""
import http.client
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import free_port  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_tracker import Vault  # noqa: E402

WORDS = "Chase the confidential pricing letter"          # text that must never appear in an event
EVENT_KEYS = {"type", "seq", "parts", "v"}


class Stream:
    """One open /api/events stream read on a thread: each event with the time it arrived."""

    def __init__(self, port, token, host="127.0.0.1"):
        self.conn = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
        self.conn.request("GET", "/api/events", headers={"X-Creaite-Token": token, "Host": host})
        self.resp = self.conn.getresponse()
        self.events, self.raw, self.ended = [], b"", threading.Event()
        if self.resp.status == 200:
            threading.Thread(target=self.read, daemon=True).start()

    def read(self):
        fp = self.resp.fp
        try:
            while True:
                line = fp.readline()
                if not line:
                    break
                self.raw += line
                if line.startswith(b"data: "):
                    self.events.append((time.monotonic(), json.loads(line[6:])))
        except (OSError, ValueError):     # the test closed it
            pass
        self.ended.set()

    def wait_for(self, test, timeout=5.0):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            for at, e in list(self.events):
                if test(e):
                    return at, e
            time.sleep(0.02)
        return None, None

    def close(self):
        """Close as a page does when it goes: the socket is shut, whatever still holds it."""
        try:
            self.conn.sock and self.conn.sock.shutdown(socket.SHUT_RDWR)
        except OSError:      # already closed
            pass
        self.resp.close()
        self.conn.close()


def debug_logging(v):
    p = v.root / "system" / "config" / "settings.json"
    cfg = json.loads(p.read_text())
    cfg.setdefault("logging", {})["level"] = "debug"
    p.write_text(json.dumps(cfg, indent=2))


class ServerCase(unittest.TestCase):
    """The real live server in a throwaway vault, with the debug log at debug level."""

    def setUp(self):
        self.v = Vault()
        populate(self.v)
        debug_logging(self.v)
        self.v.run(script="build_dashboard.py")
        self.port = free_port()
        self.base = f"http://127.0.0.1:{self.port}"
        self.proc = subprocess.Popen([sys.executable, str(self.v.root / "system/scripts/live_server.py")],
                                     env={**os.environ, "CREAITE_PORT": str(self.port)},
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(self.stop)
        for _ in range(100):
            try:
                urllib.request.urlopen(self.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        html = urllib.request.urlopen(self.base + "/").read().decode()
        self.token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]
        self.streams = []

    def stop(self):
        for s in self.streams:
            s.close()
        if self.proc.poll() is None:            # our own server only, by its handle
            self.proc.terminate()
            self.proc.wait(timeout=10)
        self.v.cleanup()

    def open(self, **kw):
        s = Stream(self.port, kw.pop("token", self.token), **kw)
        self.streams.append(s)
        return s

    def log(self):
        f = self.v.root / "system" / "logs" / f"debug-{date.today():%Y-%m-%d}.log"
        return f.read_text(encoding="utf-8") if f.exists() else ""


def fetch_counter():
    """A page script that counts the page's requests by route, so a test can see what a change reloaded."""
    return """(()=>{ const f=window.fetch.bind(window); window.FETCHED={};
  window.fetch=function(u,o){ const k=String(typeof u==="string"?u:(u&&u.url)||"").split("?")[0]; FETCHED[k]=(FETCHED[k]||0)+1;
    if(window.REFUSE_EVENTS&&k==="/api/events") return Promise.resolve(new Response("{}",{status:503}));
    return f(u,o); }; })();"""


def today_log(v):
    f = v.root / "system" / "logs" / f"debug-{date.today():%Y-%m-%d}.log"
    return f.read_text(encoding="utf-8") if f.exists() else ""
