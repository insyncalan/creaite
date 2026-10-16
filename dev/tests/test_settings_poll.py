"""#96: opening Settings asks the live server once for each thing, not three times.

A page that opened on Settings (after an update restarts the server, the browser reloads onto the page it was on) read
/api/diagnostics three times, /api/update/status twice and /api/setup/status twice inside 50 ms: each Settings card reads its
own status when it is drawn, the start-up read of the diagnostics did the same, and then redrew every card, which read them all
again. The reads are now shared while one is in flight (and for two seconds after), and a press of Refresh, an install or a
new error still reads afresh.

Run: python3 dev/tests/test_settings_poll.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

COUNT = """(()=>{ window.__calls=[]; const f=window.fetch; window.fetch=function(u){ try{ window.__calls.push(String(u)); }catch(e){} return f.apply(this,arguments); }; })()"""
READS = ("/api/diagnostics", "/api/update/status", "/api/setup/status", "/api/health")


class SettingsReads(LiveBrowserCase):
    shared_server = True        # these only read

    def counts(self):
        calls = self.b.eval("__calls.slice()")
        return {k: sum(1 for c in calls if c == k) for k in READS}

    def open_settings_fresh(self):
        """Reload the page onto Settings, as a restart does, counting every fetch from the first script."""
        b = self.b
        b.eval("go('settings','system')")
        address = b.eval("location.hash")
        b.call("Page.addScriptToEvaluateOnNewDocument", source=COUNT)
        b.goto(self.base + "/" + address)
        b.reload("typeof go==='function' && LIVE")
        b.wait("VIEW==='settings' && !!document.querySelector('#settingsBody [data-sec]')")
        b.wait("!!document.getElementById('diagCard') && !!document.getElementById('suCard') && !!document.querySelector('#updCard .sub, #updCard .row, #updCard [class*=row]')", timeout=15)

    def test_opening_settings_reads_each_status_once(self):
        self.open_settings_fresh()
        time.sleep(5)                                     # the reload of the data that follows a first paint, and the rest
        n = self.counts()
        self.assertEqual(n["/api/diagnostics"], 1, n)
        self.assertEqual(n["/api/update/status"], 1, n)
        self.assertEqual(n["/api/setup/status"], 1, n)
        self.assertLessEqual(n["/api/health"], 1, n)       # the doctor behind it runs once, and only here

    def test_nothing_polls_while_the_page_sits_on_settings(self):
        self.open_settings_fresh()
        time.sleep(4)
        before = self.counts()
        time.sleep(12)
        self.assertEqual(self.counts(), before)

    def test_refresh_still_reads_afresh(self):
        self.open_settings_fresh()
        time.sleep(3)                                     # past the shared window
        before = self.counts()["/api/diagnostics"]
        self.b.click("#diagRefresh")
        self.b.wait(f"__calls.filter(c=>c==='/api/diagnostics').length>{before}")
        self.assertEqual(self.counts()["/api/diagnostics"], before + 1)


if __name__ == "__main__":
    unittest.main()
