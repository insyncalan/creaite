"""#265 in real Chrome, on 2.6's one Intake page (#232): Refresh (the icon beside "Calendar read") reads the calendar through
its own route and the meetings appear, without ask creaite opening or a message in it. (2.5.3 drove the old Calendar import
section, retired in 2.6.0 C2.)

Run: python3 dev/tests/test_calendar_refresh_ui.py     (needs Google Chrome; skipped otherwise)
The real live server with test_calendar_refresh's stand-in Claude (it saves the calendar through the real sweep.py calendar).
The test is an expected failure until the guarded diffs in dev/proposals/calendar-refresh/ are applied.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_calendar_refresh import FAKE, needs_diff  # noqa: E402
from test_dashboard import populate  # noqa: E402


class CalendarRefreshPage(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        populate(v)
        fake = v.root / "fake_claude.py"
        fake.write_text(FAKE)
        fake.chmod(0o755)

    @classmethod
    def server_env(cls):
        return {"CREAITE_CLAUDE": str(cls.v.root / "fake_claude.py")}

    @needs_diff
    def test_refresh_reads_the_calendar_and_the_meetings_appear(self):
        self.b.eval("irSetView('list'); irStage.value='all'; go('intake-review')")
        self.b.wait("VIEW==='intake-review' && !!document.getElementById('icRef') && !document.getElementById('icRef').disabled")
        said = self.b.eval("document.querySelectorAll('#chLog .msg.u').length")
        self.b.click("#icRef")
        self.b.wait("D.intake_review.meetings.some(m=>m.title==='Pilot readiness review') && irRefreshing.value===false", timeout=90)
        self.b.wait("document.querySelector('[data-ircalread]').textContent.startsWith('Calendar read')")
        self.assertFalse(self.b.eval("document.getElementById('chat').classList.contains('on')"))   # the panel stayed shut
        self.assertEqual(self.b.eval("document.querySelectorAll('#chLog .msg.u').length"), said)   # nothing said in a chat
        self.assertIsNone(self.b.eval("RUN"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
