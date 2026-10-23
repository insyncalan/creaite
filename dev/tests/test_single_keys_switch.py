"""#298 (2.6.1; WCAG 2.1.4): Settings › Essentials › Look and help › Single-key shortcuts (help.single_keys, on by default). Off, no
letter or symbol key pressed on its own does anything: not the page keys (T P W I F A S R E), not Work's row keys (J K O S P T C V D),
not N, / or ?, not Intake's row keys; the hints for them go. Esc, Enter, Space, the arrows and keys held with Cmd or Ctrl still work,
and a letter still types in a field. The switch is read live (no reload). A real browser against the real live server; desktop
widths only.

Run: python3 dev/tests/test_single_keys_switch.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SET = "setSynced({'help.single_keys':%s})"


class SingleKeysSwitch(LiveBrowserCase):
    shared_server = True

    def setUp(self):
        super().setUp()
        self.b.eval(SET % "true")

    def tearDown(self):
        self.b.eval(SET % "true")
        super().tearDown()

    def work(self):
        b = self.b
        b.eval("go('work')")
        b.wait("VIEW==='work' && !!document.querySelector('#workTbl tbody tr[data-row]')")
        b.eval("document.activeElement&&document.activeElement.blur()")
        return b

    def test_the_setting_is_defined_and_in_the_catalogue(self):
        d = json.loads((ROOT / "system/templates/settings-defaults.json").read_text(encoding="utf-8"))
        self.assertIs(d["help"]["single_keys"], True)
        self.assertIn("help.single_keys", (ROOT / "system/scripts/settings_catalogue.py").read_text(encoding="utf-8"))

    def test_on_everything_works_as_before(self):
        b = self.work()
        self.assertTrue(b.eval("singleKeysOn()"))
        self.assertEqual(b.eval("document.documentElement.dataset.singleKeys"), "on")
        b.key("j")
        b.wait("HLC!=null", 5)
        b.key("p")                                                  # P with no peek: Projects
        b.wait("VIEW==='projects'", 5)

    def test_off_no_page_key_acts(self):
        b = self.b
        b.eval(SET % "false")
        b.eval("go('help')")
        b.wait("VIEW==='help'")
        b.eval("document.activeElement&&document.activeElement.blur()")
        for k in "tpwifasre":
            b.key(k)
            b.pump(0.15)
            self.assertEqual(b.eval("VIEW"), "help", f"{k} must do nothing")
        b.key("n")
        b.key("?")
        b.key("/")
        b.pump(0.5)                                                  # / waits a third of a second for a second /
        self.assertFalse(b.eval("!!document.querySelector('#capDrawer.on')"))
        self.assertFalse(b.eval("helpPanelOpen()"))
        self.assertFalse(b.eval("document.getElementById('chat').classList.contains('on')"))
        b.eval("document.dispatchEvent(new KeyboardEvent('keydown',{key:'P',bubbles:true,cancelable:true}))")
        self.assertEqual(b.eval("VIEW"), "help")

    def test_off_no_work_key_acts_but_the_arrows_and_enter_do(self):
        b = self.work()
        b.eval(SET % "false")
        self.assertEqual(b.eval("document.documentElement.dataset.singleKeys"), "off")
        for k in "jkospctvdn":
            b.key(k)
            b.pump(0.15)
        self.assertIsNone(b.eval("HLC"), "no letter moves the cursor")
        self.assertFalse(b.eval("document.getElementById('panel').classList.contains('on')"))
        self.assertFalse(b.eval("!!document.querySelector('#dispMenu.on, #dispMenu:not([hidden])') && popupOpen()"))
        self.assertFalse(b.eval("!!document.querySelector('#capDrawer.on')"))
        b.eval("document.dispatchEvent(new KeyboardEvent('keydown',{key:'F',shiftKey:true,bubbles:true,cancelable:true}))")
        self.assertFalse(b.eval("popupOpen()"), "Shift+F does nothing")
        b.key("ArrowDown")
        b.wait("HLC!=null", 5)                                      # the arrows still move the cursor
        b.key("Enter")
        b.wait("document.getElementById('panel').classList.contains('on')", 5)   # and Enter opens it
        b.key("Escape")
        b.wait("!document.getElementById('panel').classList.contains('on')", 5)

    def test_off_a_letter_still_types_in_a_field_and_modifier_keys_work(self):
        b = self.b
        b.eval(SET % "false")
        b.eval("go('settings')")
        b.wait("VIEW==='settings' && !!document.getElementById('setq')")
        b.eval("document.getElementById('setq').focus()")
        self.assertFalse(b.eval("singleKeyBlocked({key:'p',target:document.activeElement,isComposing:false})"), "a field gets its letters")
        b.eval("document.activeElement.blur()")
        b.eval("document.dispatchEvent(new KeyboardEvent('keydown',{key:'j',metaKey:true,bubbles:true,cancelable:true}))")
        b.wait("document.getElementById('chat').classList.contains('on')", 5)   # Cmd+J is still ask creaite
        b.eval("closeChat()")

    def test_off_the_hints_go_and_back_again_live(self):
        b = self.work()
        self.assertIn("J", b.eval("workHint('list')"))
        b.eval(SET % "false")
        hint = b.eval("workHint('list')")
        for k in (">J<", ">K<", ">O<", ">S<", ">C<", ">V<", ">D<", "Shift+F"):
            self.assertNotIn(k, hint)
        self.assertIn("Esc", hint)
        self.assertIn("Space", hint)
        self.assertEqual(b.eval("getComputedStyle(document.getElementById('hFoot')).display"), "none")
        b.eval(SET % "true")
        self.assertIn(">J<", b.eval("workHint('list')"))
        b.key("j")
        b.wait("HLC!=null", 5)


if __name__ == "__main__":
    unittest.main()
