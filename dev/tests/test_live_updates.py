"""BL-253: live updates pushed, not polled, part 1 of 3 (the stream route, first half; the fixture is in live_updates_support.py).

Run: python3 dev/tests/test_live_updates.py
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
    ServerCase,
    WORDS,
)
from test_chat_and_sweep import stage_sweep  # noqa: E402


class EventsRouteSecurity(ServerCase):
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
        body = json.dumps({"op": "write", "path": "system/config/settings.json",       # #128: still a settings object (the
                           "text": (self.v.root / "system/config/settings.json").read_text() + "\n"}).encode()   # page's own)
        req = urllib.request.Request(self.base + "/api/fs", data=body, method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        sent = time.monotonic()
        urllib.request.urlopen(req, timeout=10).read()
        at, ev = s.wait_for(lambda e: e["type"] == "changed" and "settings" in e["parts"])
        self.assertIsNotNone(ev)
        self.assertLess(at - sent, 0.9)                                     # poked, not the next tick


if __name__ == "__main__":
    unittest.main()
