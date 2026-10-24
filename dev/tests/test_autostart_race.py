"""#300 race: the autostart status answers late (after load, after the user has opened something). It must update only the
#asQ card: not Today as a whole, not the setup list, and never an open panel.

Run: python3 dev/tests/test_autostart_race.py   (needs Google Chrome; skipped otherwise)

The status route is stubbed with a promise the test releases by hand, so the order is deterministic (on Linux the real route says
"Only on a Mac", which is why CI never saw the race).
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_decisions_needed import Base  # noqa: E402

HOLD = r"""
window.__asr = {release: null, calls: 0};
const real = window.fetch.bind(window);
window.fetch = (u, o) => {
  if (!String(u).startsWith('/api/autostart/status')) return real(u, o);
  window.__asr.calls++;
  return new Promise(res => { window.__asr.release = () => res(new Response(JSON.stringify(
    {ok: true, supported: true, dev: false, installed: false, loaded: false, on: false, folder: '/Users/example/creaite'}),
    {status: 200, headers: {'Content-Type': 'application/json'}})); });
};
"""


class LateStatus(Base):
    def held(self):
        b = self.today()
        b.eval("try{localStorage.removeItem('creaite-autostart-asked')}catch(e){}")
        b.eval(HOLD)
        b.eval("AS.status=null; void asRefresh(); 0")           # the late answer is now in flight
        b.wait("window.__asr.calls>=1 && !!window.__asr.release")
        if not b.eval("!!document.querySelector('#setupList')"):
            self.skipTest("the sample vault has finished set-up, so the checklist is not up")
        return b

    def test_a_late_status_leaves_an_open_panel_alone(self):
        b = self.held()
        b.click('#dnList [data-dndecide="ABC-D-007"]')
        b.wait("CUR&&CUR.id==='ABC-D-007'&&document.getElementById('panel').classList.contains('on')")
        b.eval("window.__asr.release()")
        b.wait("!!document.querySelector('#asQ')", 10)                           # the card appears
        b.pump(0.5)
        self.assertTrue(b.eval("CUR&&CUR.id==='ABC-D-007'&&document.getElementById('panel').classList.contains('on')"))

    def test_a_late_status_does_not_redraw_the_setup_list_or_today(self):
        b = self.held()
        b.eval("document.querySelector('#setupList').dataset.mark='kept'; document.querySelector('#setupList h2').dataset.mark='kept'; "
               "document.querySelector('#dnList').dataset.mark='kept'")
        b.eval("window.__asr.release()")
        b.wait("!!document.querySelector('#asQ')", 10)
        b.pump(0.3)
        self.assertEqual(b.eval("document.querySelector('#setupList h2').dataset.mark"), "kept")     # same nodes: nothing rewritten
        self.assertEqual(b.eval("document.querySelector('#dnList').dataset.mark"), "kept")

    def test_a_click_in_the_setup_list_is_not_lost_when_the_status_arrives(self):
        b = self.held()
        b.eval("window.__asr.release()")
        b.eval("window.__clicked=0; document.querySelector('#setupList [data-setopen=\"setup\"]').addEventListener('click',()=>{window.__clicked++})")
        b.click('#setupList [data-setopen="setup"]')
        b.pump(0.5)
        self.assertEqual(b.eval("window.__clicked"), 1)
        self.assertTrue(b.eval("!!document.querySelector('#asQ')"))

    def test_the_question_card_does_not_move_when_the_status_arrives(self):
        """The card's slot is reserved before the status answers, so its place and height are the same after (no sleeps: the
        status is held by hand). Fails if the card only appears late."""
        b = self.held()
        if not b.eval("/Mac/i.test(String(navigator.platform||navigator.userAgent))"):
            self.skipTest("the slot is reserved on a Mac only")
        box = "(()=>{const e=document.querySelector('#asQ'),l=document.querySelector('#setupList');"\
              "if(!e)return null;const r=e.getBoundingClientRect(),q=l.getBoundingClientRect();return [r.top,r.height,q.height,document.querySelector('#dnList').getBoundingClientRect().top]})()"
        # The real status may already have answered, so put the page back into its boot state (no status yet) and draw Today's list
        # as the first paint does; the held status is then still in flight.
        b.eval("(()=>{const e=document.querySelector('#asQ'); if(e) e.remove(); AS.status=null; AS.done=false; renderSetup(); 0})()")
        first = b.eval(box)
        self.assertIsNotNone(first, "no slot before the status answers")
        b.eval("window.__asr.release()")
        b.wait("!!document.querySelector('#asQ') && !document.querySelector('#asQ').dataset.slot", 10)
        b.frames(2)
        self.assertEqual(b.eval(box), first)


if __name__ == "__main__":
    unittest.main()
