"""BL-253: live updates pushed, not polled, part 2 of 3 (the stream route, second half; the fixture is in live_updates_support.py).

Run: python3 dev/tests/test_live_updates_events.py
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
    today_log,
)


class EventsRouteParts(ServerCase):
    """The stream itself: security, timing, the parts named, no text, and clean ends."""

    def test_a_refused_settings_save_writes_nothing_and_sends_no_event(self):
        """#128: a settings save the server refuses (here: not a settings object) leaves settings.json as it was and sends no
        'settings' event; the same save made valid is written and sent at once."""
        s = self.open()
        s.wait_for(lambda e: e["type"] == "hello")
        time.sleep(1.2)
        f = self.v.root / "system/config/settings.json"
        before = f.read_text()

        def save(text):
            body = json.dumps({"op": "write", "path": "system/config/settings.json", "text": text}).encode()
            req = urllib.request.Request(self.base + "/api/fs", data=body, method="POST",
                                         headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
            return json.loads(urllib.request.urlopen(req, timeout=10).read())
        got = save(before[:-1])                                             # the closing brace cut off
        self.assertFalse(got["ok"], got)
        self.assertIn("settings must be a JSON object", got["message"])
        self.assertEqual(f.read_text(), before)
        at, ev = s.wait_for(lambda e: e["type"] == "changed" and "settings" in e["parts"], timeout=2.5)
        self.assertIsNone(ev, "a refused save sent a settings event")
        self.assertEqual(save(before + "\n"), {"ok": True})
        at, ev = s.wait_for(lambda e: e["type"] == "changed" and "settings" in e["parts"])
        self.assertIsNotNone(ev)
        self.assertEqual(f.read_text(), before + "\n")

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
        # the server writes a request's log line once the reply has gone (log_request, in the handler's finally), so the last
        # line can follow the reply; under load it hadn't been written when the log was read (5 != 6). Wait for it.
        end = time.time() + 10
        while True:
            lines = [ln for ln in today_log(self.v).splitlines() if "/api/pulse 403" in ln]
            if len(lines) >= 6 or time.time() > end:
                break
            time.sleep(0.05)
        self.assertEqual(len(lines), 6)
        self.assertEqual(sum("told to reload" in ln for ln in lines), 2)             # one for each page
        self.assertFalse([ln for ln in lines if "WARN" in ln.upper().split("/API")[0]], lines)


if __name__ == "__main__":
    unittest.main()
