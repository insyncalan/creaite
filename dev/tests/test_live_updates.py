"""BL-253: live updates pushed, not polled. GET /api/events streams `changed` with the parts that changed; the page reloads
only those parts, and the 30 s pulse is the fallback while the stream is down.

Run: python3 dev/tests/test_live_updates.py
The server tests run the real live server in a throwaway vault; the page tests drive headless Chrome (skipped without it).
"""
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
from live_browser import LiveBrowserCase, free_port  # noqa: E402
from test_chat_and_sweep import short_health_check, stage_sweep  # noqa: E402
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



class EventsRoute(ServerCase):
    """The stream itself: security, timing, the parts named, no text, and clean ends."""

    def test_the_token_and_host_are_checked_and_the_headers_set(self):
        self.assertEqual(self.open(token="wrong").resp.status, 403)
        self.assertEqual(self.open(host="evil.example").resp.status, 403)
        s = self.open()
        self.assertEqual(s.resp.status, 200)
        self.assertTrue(s.resp.getheader("Content-Type").startswith("text/event-stream"))
        self.assertEqual(s.resp.getheader("Cache-Control"), "no-store")
        for k, v in (("X-Frame-Options", "DENY"), ("X-Content-Type-Options", "nosniff"), ("Referrer-Policy", "no-referrer"),
                     ("Content-Security-Policy", "frame-ancestors 'none'")):
            self.assertEqual(s.resp.getheader(k), v)                       # BL-212's headers, as on every reply
        self.assertIsNone(s.resp.getheader("Access-Control-Allow-Origin"))
        _at, hello = s.wait_for(lambda e: e["type"] == "hello")
        self.assertTrue(hello and hello["v"])

    def test_a_change_on_disk_arrives_within_a_second_or_so_with_its_part_named(self):
        s = self.open()
        s.wait_for(lambda e: e["type"] == "hello")
        time.sleep(1.2)                                                     # the watcher has its first stamps
        started = time.monotonic()
        stage_sweep(self.v.root, WORDS)                                     # a sweep from Terminal: outside the server
        staged = time.monotonic()
        at, ev = s.wait_for(lambda e: e["type"] == "changed" and "review" in e["parts"])
        self.assertIsNotNone(ev, "no event for a staged sweep")
        self.assertLess(at - staged, 2.0)
        self.assertNotIn("tracker", ev["parts"])
        self.v.run("approve", "5", script="review.py")                       # the swept item (four were waiting)
        self.v.run("apply")
        at, ev = s.wait_for(lambda e: e["type"] == "changed" and "tracker" in e["parts"])
        self.assertIsNotNone(ev, "no event for an apply")
        self.assertLess(at - started, 30)
        seqs = [e["seq"] for _a, e in s.events if e["type"] == "changed"]
        self.assertEqual(seqs, sorted(set(seqs)))                           # numbered in order, as a run's events are

    def test_a_save_through_the_server_is_sent_at_once(self):
        s = self.open()
        s.wait_for(lambda e: e["type"] == "hello")
        time.sleep(1.2)
        body = json.dumps({"op": "write", "path": "system/config/settings.json",
                           "text": (self.v.root / "system/config/settings.json").read_text()[:-1] + "\n "}).encode()
        req = urllib.request.Request(self.base + "/api/fs", data=body, method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        sent = time.monotonic()
        urllib.request.urlopen(req, timeout=10).read()
        at, ev = s.wait_for(lambda e: e["type"] == "changed" and "settings" in e["parts"])
        self.assertIsNotNone(ev)
        self.assertLess(at - sent, 0.9)                                     # poked, not the next tick

    def test_inbox_and_vip_name_their_own_parts(self):
        s = self.open()
        s.wait_for(lambda e: e["type"] == "hello")
        time.sleep(1.2)
        (self.v.root / "inbox").mkdir(exist_ok=True)
        (self.v.root / "inbox" / "2026-10-09 Steering.vtt").write_text("WEBVTT\n\n" + WORDS)
        _at, ev = s.wait_for(lambda e: e["type"] == "changed" and "files" in e["parts"])
        self.assertEqual(ev and ev["parts"], ["files"])
        (self.v.root / "system/staging/vip.json").write_text(json.dumps({"alerts": [{"id": "x", "subject": WORDS}]}))
        _at, ev = s.wait_for(lambda e: e["type"] == "changed" and "vip" in e["parts"])
        self.assertEqual(ev and ev["parts"], ["vip"])

    def test_no_message_text_in_events(self):
        s = self.open()
        s.wait_for(lambda e: e["type"] == "hello")
        time.sleep(1.2)
        stage_sweep(self.v.root, WORDS)
        (self.v.root / "system/staging/vip.json").write_text(json.dumps({"alerts": [{"id": "y", "subject": WORDS}]}))
        s.wait_for(lambda e: e["type"] == "changed" and "vip" in e["parts"])
        s.wait_for(lambda e: e["type"] == "changed" and "review" in e["parts"])
        self.assertNotIn(WORDS.encode(), s.raw)
        self.assertNotIn(b"Chase", s.raw)
        for _at, e in s.events:
            self.assertLessEqual(set(e), EVENT_KEYS)
            self.assertTrue(set(e.get("parts", [])) <= {"tracker", "review", "calendar", "vip", "files", "settings"})
        self.assertNotIn(WORDS, self.log())                                 # nor in the debug log

    def test_a_dropped_page_frees_its_stream_and_stop_closes_the_rest(self):
        a = self.open()
        a.wait_for(lambda e: e["type"] == "hello")
        b = self.open()
        b.wait_for(lambda e: e["type"] == "hello")
        self.assertIn("events stream opened (2 open)", self.log())
        a.close()
        end = time.monotonic() + 5
        while "events stream closed (1 open)" not in self.log() and time.monotonic() < end:
            time.sleep(0.1)
        self.assertIn("events stream closed (1 open)", self.log())         # noticed without waiting for a ping
        req = urllib.request.Request(self.base + "/api/stop", data=b"{}", method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        self.assertTrue(json.loads(urllib.request.urlopen(req, timeout=10).read())["ok"])
        self.assertTrue(b.ended.wait(10), "the stream wasn't closed when the server stopped")
        self.proc.wait(timeout=10)


def fetch_counter():
    """A page script that counts the page's requests by route, so a test can see what a change reloaded."""
    return """(()=>{ const f=window.fetch.bind(window); window.FETCHED={};
  window.fetch=function(u,o){ const k=String(typeof u==="string"?u:(u&&u.url)||"").split("?")[0]; FETCHED[k]=(FETCHED[k]||0)+1;
    if(window.REFUSE_EVENTS&&k==="/api/events") return Promise.resolve(new Response("{}",{status:503}));
    return f(u,o); }; })();"""


class PageStream(LiveBrowserCase):
    """The page follows one stream and reloads only the part that changed (the pulse is at its 30 s default here)."""

    def setUp(self):
        super().setUp()
        self.b.call("Page.addScriptToEvaluateOnNewDocument", source=fetch_counter())
        self.b.reload("typeof go==='function' && LIVE && typeof EVS==='object' && EVS.up")

    def review_has(self, text):
        return f"REV.some(r=>(r.rec&&r.rec.t||'').includes({text!r}))"

    def test_one_stream_and_a_change_from_outside_shows_without_the_pulse(self):
        self.assertEqual(self.b.eval("EVS.opened"), 1)
        self.assertEqual(self.b.eval("FETCHED['/api/events']"), 1)
        self.b.wait("PULSE.v!=null")
        stage_sweep(self.v.root, "Pushed not polled")
        t = time.monotonic()
        self.b.wait(self.review_has("Pushed not polled"), timeout=10)
        self.assertLess(time.monotonic() - t, 6)                           # well inside the 30 s pulse
        self.assertEqual(self.b.eval("FETCHED['/api/events']"), 1)          # still the one stream

    def test_only_the_files_are_reloaded_for_a_new_inbox_file(self):
        self.b.wait("PULSE.v!=null")
        time.sleep(1.5)
        self.b.eval("FETCHED={}; 1")
        (self.v.root / "inbox").mkdir(exist_ok=True)
        (self.v.root / "inbox" / "2026-10-09 Workshop.vtt").write_text("WEBVTT\n\nhello")
        self.b.wait("(FETCHED['/api/files']||0)>0", timeout=10)
        time.sleep(1)
        self.assertEqual(self.b.eval("FETCHED['/api/data']||0"), 0)         # nothing else was reloaded
        self.b.wait("D.inbox.some(f=>(f.name||f.path||'').includes('Workshop'))", timeout=5)

    def test_leaving_the_page_closes_its_stream(self):
        self.assertTrue(self.b.eval("EVS.up"))
        self.b.eval("dispatchEvent(new PageTransitionEvent('pagehide')); 1")
        self.assertFalse(self.b.eval("EVS.up"))
        self.assertIsNone(self.b.eval("EVS.ctl"))
        time.sleep(1.5)
        self.assertEqual(self.b.eval("FETCHED['/api/events']"), 1)          # not reopened behind the page's back


class PulseFallback(LiveBrowserCase):
    """When the stream is refused, the pulse (every healthSecs) keeps the page fresh, as before BL-253."""

    @classmethod
    def load(cls, v):
        populate(v)
        short_health_check(v)

    def setUp(self):
        super().setUp()
        self.b.call("Page.addScriptToEvaluateOnNewDocument", source="window.REFUSE_EVENTS=true;" + fetch_counter())
        self.b.reload("typeof go==='function' && LIVE && typeof EVS==='object' && (FETCHED['/api/events']||0)>0")

    def test_the_pulse_takes_over_when_the_stream_is_refused(self):
        self.assertFalse(self.b.eval("EVS.up"))
        self.b.wait("PULSE.v!=null")
        stage_sweep(self.v.root, "Arrived by the pulse")
        self.b.wait("REV.some(r=>(r.rec&&r.rec.t||'').includes('Arrived by the pulse'))", timeout=15)
        self.assertGreater(self.b.eval("FETCHED['/api/pulse']||0"), 1)
        self.assertFalse(self.b.eval("EVS.up"))
        self.assertTrue(self.b.eval("document.getElementById('staleAlert').hidden"))   # refused is not stale


# ---------------------------------------------------------------- BL-269: a stale page stops asking, and is logged once
def today_log(v):
    f = v.root / "system" / "logs" / f"debug-{date.today():%Y-%m-%d}.log"
    return f.read_text(encoding="utf-8") if f.exists() else ""


class StaleLoggedOnce(ServerCase):
    """The server: a page's stale refusals are one info line, not a WARN per poll (BL-269)."""

    def test_one_line_for_a_page_and_its_repeats_at_debug(self):
        def pulse(token):
            req = urllib.request.Request(self.base + "/api/pulse", data=b"{}", method="POST",
                                         headers={"Content-Type": "application/json", "X-Creaite-Token": token})
            try:
                urllib.request.urlopen(req, timeout=10)
            except urllib.error.HTTPError as e:
                with e:
                    return e.code, json.loads(e.read())
        for _ in range(5):
            code, body = pulse("an-old-pages-token")
            self.assertEqual(code, 403)
            self.assertTrue(body["stale"])
        pulse("another-old-page")
        lines = [ln for ln in today_log(self.v).splitlines() if "/api/pulse 403" in ln]
        self.assertEqual(len(lines), 6)
        self.assertEqual(sum("told to reload" in ln for ln in lines), 2)             # one for each page
        self.assertFalse([ln for ln in lines if "WARN" in ln.upper().split("/API")[0]], lines)


class StalePageStops(LiveBrowserCase):
    """The page: after its first stale reply it sends nothing more to /api until reloaded."""

    @classmethod
    def load(cls, v):
        populate(v)
        short_health_check(v)

    def setUp(self):
        super().setUp()
        self.b.call("Page.addScriptToEvaluateOnNewDocument", source=fetch_counter())
        self.b.reload("typeof go==='function' && LIVE && typeof EVS==='object' && EVS.up")

    def test_no_more_api_calls_once_stale(self):
        self.b.eval("evClose(); D.token='a-token-from-before-a-restart'; pulseCheck(); 1")   # as after a restart
        self.b.wait("!document.getElementById('staleAlert').hidden", timeout=10)
        self.b.eval("FETCHED={}; 1")
        self.b.eval("evOpen(); pulseCheck(); vipPoll(); 1")
        time.sleep(11)                                                      # the 10 s presence timer, the 1 s pulse
        sent = self.b.eval("Object.keys(FETCHED).filter(k=>k.includes('/api/'))")
        self.assertEqual(sent, [])
        self.assertFalse(self.b.eval("EVS.up"))
        self.assertIn("restarted", self.b.eval("document.getElementById('staleAlert').innerText"))

if __name__ == "__main__":
    unittest.main()
