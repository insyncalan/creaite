"""BL-256, BL-316 (dev/COMPONENTS.md §3): the Toast building block, the one message at the foot of the page. A polite status
region; 10 seconds with an action, 5 without (the times are props, so the fixture runs them short); held while the pointer is
over it or focus is inside it, and leaving starts the full time again; Esc hides it at once when you are on it, otherwise
only when nothing else is open; focus that was in it goes back where it came from; its action runs and hides it; its text is
escaped. And the page's own: snack(msg, undo, label) draws it as #snack. (The real 5 and 10 second timings, and ⌘Z in Work,
are test_snack_timing's.)

Run: python3 dev/tests/test_block_toast.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

MOUNT = """(()=>{ const old=document.getElementById('toastFix'); if(old){ mount(()=>null,{},old); old.remove(); }
  document.getElementById('tfLayer')?.remove(); window.scrollTo(0,0);
  const box=document.createElement('div'); box.id='toastFix'; document.body.prepend(box);
  const opener=document.createElement('button'); opener.id='tfOpener'; opener.textContent='Opener'; box.before(opener);
  window.TF={box, hits:0, hides:0, s:{open:false,text:'',action:'',run:0}};
  TF.draw=p=>{ Object.assign(TF.s,p); drawToast(box,{...TF.s,id:'tfx',textId:'tfxT',actionId:'tfxU',ms:700,actionMs:1400,
    layers:'#tfLayer',onAction:()=>{ TF.hits++; },onHide:()=>{ TF.hides++; TF.draw({open:false}); }}); };
  TF.show=(text,action)=>TF.draw({open:true,text,action:action||'',run:TF.s.run+1});
  TF.draw({}); return true; })()"""
ON = "document.getElementById('tfx').classList.contains('on')"
HELD = "document.getElementById('tfx').classList.contains('held')"


class ToastBlock(LiveBrowserCase):
    shared_server = True        # it only reads

    def setUp(self):
        super().setUp()
        self.b.call("Emulation.setFocusEmulationEnabled", enabled=True)
        self.b.eval(MOUNT)

    def on_for(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if not self.b.eval(ON):
                return False
            self.b.pump(0.05)
        return True

    def gone_within(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if not self.b.eval(ON):
                return True
            self.b.pump(0.05)
        return False

    def test_a_polite_status_region_whose_text_is_escaped(self):
        b = self.b
        b.eval("TF.show('<b>Saved</b> ABC-A-001','Undo')")
        got = b.eval("""(()=>{ const t=document.getElementById('tfx'); return [t.getAttribute('role'), t.getAttribute('aria-live'),
          t.className, document.getElementById('tfxT').textContent, !!t.querySelector('#tfxT b'),
          document.getElementById('tfxU').textContent, document.getElementById('tfxU').style.display]; })()""")
        self.assertEqual(got, ["status", "polite", "snack on mtimer", "<b>Saved</b> ABC-A-001", False, "Undo", ""])
        b.eval("TF.show('Checking…')")                                       # no action: no button, no bar
        self.assertEqual(b.eval("[document.getElementById('tfx').className, document.getElementById('tfxU').style.display]"),
                         ["snack on", "none"])

    def test_the_page_s_times_are_10_seconds_with_an_action_and_5_without(self):
        self.assertEqual(self.b.eval("[TOAST_ACTION_MS, TOAST_MS]"), [10000, 5000])

    def test_a_plain_message_goes_after_its_time_and_one_with_an_action_stays_longer(self):
        b = self.b
        t0 = time.monotonic()
        b.eval("TF.show('Plain')")
        self.assertTrue(self.on_for(0.5))
        self.assertTrue(self.gone_within(1.5))
        self.assertGreaterEqual(time.monotonic() - t0, 0.65)
        t0 = time.monotonic()
        b.eval("TF.show('With undo','Undo')")
        self.assertTrue(self.on_for(1.1))                                    # past the plain time
        self.assertTrue(self.gone_within(1.5))
        self.assertGreaterEqual(time.monotonic() - t0, 1.35)
        self.assertEqual(b.eval("TF.hits"), 0)                               # going by itself doesn't run the action

    def test_a_new_message_starts_the_time_again(self):
        b = self.b
        b.eval("TF.show('First')")
        b.pump(0.5)
        b.eval("TF.show('Second')")
        self.assertTrue(self.on_for(0.5))                                    # 1 second after the first: still on
        self.assertEqual(b.eval("document.getElementById('tfxT').textContent"), "Second")

    def test_the_pointer_over_it_holds_it_and_leaving_starts_the_full_time_again(self):
        b = self.b
        b.eval("TF.show('Saved','Undo')")
        r = b.eval("(()=>{ const r=document.getElementById('tfxT').getBoundingClientRect(); return [r.x+r.width/2, r.y+r.height/2]; })()")
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=r[0], y=r[1])
        b.wait(HELD)
        self.assertTrue(self.on_for(2.2))                                    # past its 1.4 seconds: held
        self.assertTrue(b.eval("document.getElementById('tfx').classList.contains('mtimer')"))   # the bar, paused
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=5, y=300)    # leave
        b.wait(f"!{HELD}")
        t_leave = time.monotonic()
        self.assertTrue(self.on_for(1.0))                                    # the full time again, not what was left
        self.assertTrue(self.gone_within(1.5))
        self.assertGreaterEqual(time.monotonic() - t_leave, 1.3)

    def test_focus_inside_holds_it_esc_hides_it_and_focus_goes_back(self):
        b = self.b
        b.eval("document.getElementById('tfOpener').focus(); TF.show('Saved','Undo')")
        b.eval("document.getElementById('tfxU').focus()")                    # as Tab reaching it would
        b.wait(HELD)
        self.assertTrue(self.on_for(2.0))
        b.key("Escape")
        b.wait(f"!{ON}")
        self.assertEqual(b.eval("TF.hits"), 0)                               # Esc hides; it doesn't run the action
        self.assertEqual(b.eval("document.activeElement.id"), "tfOpener")    # focus back where it came from
        self.assertFalse(b.eval(HELD))

    def test_esc_leaves_it_while_something_else_is_open_then_hides_it(self):
        b = self.b
        b.eval("document.body.focus(); const l=document.createElement('div'); l.id='tfLayer'; document.body.append(l); TF.show('Saved','Undo')")
        b.key("Escape")                                                      # the open layer's Esc, not the message's
        b.pump(0.1)
        self.assertTrue(b.eval(ON))
        b.eval("document.getElementById('tfLayer').remove()")
        b.key("Escape")                                                      # now there's nothing else: the message goes
        b.wait(f"!{ON}")

    def test_its_action_runs_once_and_hides_it_and_focus_goes_back(self):
        b = self.b
        b.eval("document.getElementById('tfOpener').focus(); TF.show('Moved to Done','Restore')")
        self.assertEqual(b.eval("document.getElementById('tfxU').textContent"), "Restore")
        b.eval("document.getElementById('tfxU').focus()")
        b.key("Enter")
        b.wait(f"!{ON}")
        self.assertEqual(b.eval("[TF.hits, TF.hides, document.activeElement.id]"), [1, 1, "tfOpener"])
        b.eval("TF.show('Again','Undo')")
        b.click("#tfxU")
        b.wait(f"!{ON}")
        self.assertEqual(b.eval("TF.hits"), 2)

    def test_the_page_s_snack_draws_it(self):
        """snack(msg, undo, label) stays the call: it draws the page's toast (#snack) at once, with its action's words."""
        b = self.b
        got = b.eval("""(()=>{ window.UNDID=0; snack('<i>Saved</i>',()=>{ UNDID++; },'Restore'); const s=document.getElementById('snack');
          return [s.className, s.getAttribute('role'), document.getElementById('snackT').textContent,
            document.getElementById('snackU').textContent, s.parentElement.id]; })()""")
        self.assertEqual(got, ["snack on mtimer", "status", "<i>Saved</i>", "Restore", "toastHost"])
        b.click("#snackU")
        b.wait("!document.getElementById('snack').classList.contains('on')")
        self.assertEqual(b.eval("UNDID"), 1)
        b.eval("snack('Plain')")
        self.assertEqual(b.eval("[document.getElementById('snack').className, document.getElementById('snackU').style.display]"),
                         ["snack on", "none"])
        b.eval("hideSnack()")
        self.assertFalse(b.eval("document.getElementById('snack').classList.contains('on')"))

    def test_over_a_modal_dialog_the_message_and_its_undo_can_be_reached(self):
        """BL-316: a modal dialog makes the page behind it inert; the page's toast is drawn inside the top modal while one is
        open (its Undo can be clicked and focused), and goes back where it was when the dialog closes."""
        b = self.b
        b.eval("""(()=>{ document.getElementById('tfDlg')?.remove(); const d=document.createElement('dialog'); d.id='tfDlg';
          d.innerHTML='<p>A modal</p><button id="tfIn">In it</button>'; document.body.appendChild(d); d.showModal();
          window.UNDID=0; snack('Moved',()=>{ UNDID++; }); return true; })()""")
        self.assertEqual(b.eval("document.getElementById('toastHost').parentElement.id"), "tfDlg")
        self.assertFalse(b.eval("document.getElementById('snackU').closest('[inert]')!==null"))
        b.click("#snackU")
        b.wait("UNDID===1")
        b.eval("document.getElementById('tfDlg').close()")
        b.wait("document.getElementById('toastHost').parentElement===document.body")
        b.eval("snack('Plain'); hideSnack(); document.getElementById('tfDlg').remove()")
        self.assertEqual(b.eval("document.getElementById('toastHost').parentElement.tagName"), "BODY")


if __name__ == "__main__":
    unittest.main(verbosity=2)
