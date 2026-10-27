"""BL-253: live updates pushed, not polled, part 3 of 3 (closing ends, the page and the stale rules; the fixture is in live_updates_support.py).

Run: python3 dev/tests/test_live_updates_page.py
The server tests run the real live server in a throwaway vault; the page tests drive headless Chrome (skipped without it).
"""
import json
import sys
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_updates_support import (  # noqa: E402
    EVENT_KEYS,
    ServerCase,
    WORDS,
    fetch_counter,
)
from live_browser import LiveBrowserCase  # noqa: E402
from test_chat_and_sweep import short_health_check, stage_sweep  # noqa: E402
from test_dashboard import populate  # noqa: E402


class EventsRouteEnds(ServerCase):
    """The stream itself: security, timing, the parts named, no text, and clean ends."""

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
        self.b.eval("sessionStorage.setItem('creaite.staleReload','1'); "                    # the one reload is spent (#370)
                    "evClose(); D.token='a-token-from-before-a-restart'; pulseCheck(); 1")   # as after a restart
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
