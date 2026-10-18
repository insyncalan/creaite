"""#200 (option 2): Today's "Sweep due since 07:00" banner with a Run sweep button. The build says whether the daily sweep is due
(sweep.due_info(): the last success before today's sweep.due_from, and now after it); the page shows a calm banner under the day band,
the button sends "sweep" to ask creaite as a typed sweep does, and the banner is hidden when the sweep isn't due, before 07:00, while a
run is going, and in the development repository; without the live server the button gives way to the restart hint. Real Chrome, the
real live server, a pinned clock and a fake last-sweep.txt.

Run: python3 dev/tests/test_sweep_banner.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

VISIBLE = "(()=>{const e=document.getElementById('sweepDue'); return !!e && !e.hidden && e.offsetParent!==null && getComputedStyle(e).display!=='none';})()"


class DueCase(LiveBrowserCase):
    NOW, LAST = "2026-10-09 08:00", "2026-10-08 07:30"
    shared_server = True

    @classmethod
    def load(cls, v):
        super().load(v)
        if cls.LAST:
            (v.root / "system/staging").mkdir(parents=True, exist_ok=True)
            (v.root / "system/staging/last-sweep.txt").write_text(cls.LAST + "\n", encoding="utf-8")

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": cls.NOW}

    def today(self):
        self.b.eval("go('today')")
        self.b.pump(0.3)


class SweepDue(DueCase):
    def test_banner_shows_with_the_button_and_the_build_field(self):
        b = self.b
        self.today()
        self.assertEqual(b.eval("D.sweep_due.due"), True)
        self.assertTrue(b.eval(VISIBLE))
        self.assertIn("Sweep due since 07:00", b.eval("document.getElementById('sweepDue').textContent"))
        self.assertEqual(b.eval("document.getElementById('sweepDue').getAttribute('role')"), "status")
        self.assertEqual(b.eval("document.getElementById('sweepRun').textContent"), "Run sweep")
        self.assertEqual(b.eval("document.getElementById('sweepDue').nextElementSibling.id"), "tBrief")      # between the day band and the sections
        self.assertTrue(b.eval("!!document.querySelector('#v-today > .dayband ~ #sweepDue')"))
        self.assertFalse(b.eval("!!document.querySelector('#sweepDue [data-dismiss],#sweepDue .x')"))   # not dismissible

    def test_the_button_sends_sweep_like_a_typed_one(self):
        b = self.b
        self.today()
        b.eval("send=((orig)=>function(t){ window.SENT=t; })(send)")
        b.click("#sweepRun")
        b.pump(0.2)
        self.assertEqual(b.eval("window.SENT"), "sweep")

    def test_the_button_is_reachable_and_works_from_the_keyboard(self):
        b = self.b
        self.today()
        b.eval("send=((orig)=>function(t){ window.SENT=t; })(send)")
        b.eval("document.getElementById('sweepRun').focus()")
        self.assertEqual(b.eval("document.activeElement.id"), "sweepRun")
        b.key("Enter")
        b.pump(0.2)
        self.assertEqual(b.eval("window.SENT"), "sweep")

    def test_hidden_while_a_run_is_going(self):
        b = self.b
        self.today()
        self.assertTrue(b.eval(VISIBLE))
        b.eval("rbStart('Running a sweep')")
        b.pump(0.2)
        self.assertFalse(b.eval(VISIBLE))

    def test_without_the_live_server_the_restart_hint_replaces_the_button(self):
        b = self.b
        self.today()
        b.eval("document.getElementById('liveAlert').classList.add('on')")    # what the page does when the server isn't reachable
        b.pump(0.1)
        self.assertFalse(b.eval("getComputedStyle(document.getElementById('sweepRun')).display!=='none'"))
        self.assertIn("Needs the live server", b.eval("document.querySelector('#sweepDue .sd-off').innerText"))

    def test_hidden_in_the_development_repository(self):
        b = self.b
        self.today()
        b.eval("D.dev=true; renderSweepDue()")
        self.assertFalse(b.eval(VISIBLE))


class SweepDueNarrow(SweepDue):
    width, height = 900, 900


class SweptToday(DueCase):
    LAST = "2026-10-09 07:10"

    def test_hidden_when_swept_since_seven(self):
        self.today()
        self.assertEqual(self.b.eval("D.sweep_due.due"), False)
        self.assertFalse(self.b.eval(VISIBLE))


class BeforeSeven(DueCase):
    NOW = "2026-10-09 06:30"

    def test_hidden_before_seven(self):
        self.today()
        self.assertEqual(self.b.eval("D.sweep_due.due"), False)
        self.assertFalse(self.b.eval(VISIBLE))


class NeverSwept(DueCase):
    LAST = ""

    def test_first_run_checklist_has_the_sweep_step_so_no_banner(self):
        self.today()
        self.assertEqual(self.b.eval("D.sweep_due.due"), True)
        self.assertFalse(self.b.eval(VISIBLE))


if __name__ == "__main__":
    unittest.main()
