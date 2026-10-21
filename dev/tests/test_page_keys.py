"""#288 (2.6 line): one key per page, with no modifier: T Today, P Projects, W Work, I Intake, F Files, A Activity, S Settings,
R Reports, E People. Each goes the way the sidebar's button goes (nav go()). They are ignored while typing (core/keys.js typing())
and while a dialog or popup is open (core/keys.js popupOpen(): dialog[open], an open menu or list, the calendar, the ? panel, an
item being edited). The Work field picker (BL-130) moved from F to Shift+F. A real browser against the real live server; desktop
widths only (1400 and 900 px).

Run: python3 dev/tests/test_page_keys.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import intake_review_support as IR  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
KEYS = {"t": "today", "p": "projects", "w": "work", "i": "intake-review", "f": "files", "a": "activity", "s": "settings",
        "r": "reports", "e": "people"}
SIDEBAR = {"t": "today", "p": "projects", "w": "work", "i": "review", "f": "files", "a": "activity", "s": "settings",
           "r": "reports", "e": "people"}     # the sidebar button (data-v) each key stands for; Intake keeps the id "review" (#232)


class PageKeys(LiveBrowserCase):
    shared_server = True

    def neutral(self):
        """Help: a page no key goes to, with nothing focused and nothing open."""
        b = self.b
        b.eval("go('help')")
        b.wait("VIEW==='help'")
        b.eval("document.activeElement&&document.activeElement.blur()")
        return b

    def test_each_key_lands_on_its_page(self):
        for k, view in KEYS.items():
            with self.subTest(key=k):
                b = self.neutral()
                b.key(k)
                b.wait(f"VIEW==={view!r}", 5)
                self.assertFalse(b.eval("popupOpen()"), f"{view}: nothing should count as open once the page is drawn")

    def test_upper_case_without_shift_and_each_page_is_in_the_sidebar(self):
        b = self.neutral()
        b.eval("document.dispatchEvent(new KeyboardEvent('keydown',{key:'P',bubbles:true,cancelable:true}))")   # Caps Lock: P, no Shift
        b.wait("VIEW==='projects'", 5)
        ids = b.eval("RAIL_ITEMS.map(i=>i.id)")
        for k, rid in SIDEBAR.items():
            self.assertIn(rid, ids, f"{k}: its page is not a sidebar page")

    def test_t_on_today_stays_on_today(self):
        b = self.b
        b.eval("go('today')")
        b.wait("VIEW==='today'")
        b.eval("document.activeElement&&document.activeElement.blur()")
        b.key("t")
        b.pump(0.3)
        self.assertEqual(b.eval("VIEW"), "today")

    def test_ignored_while_typing(self):
        b = self.b
        b.eval("go('settings')")
        b.wait("VIEW==='settings' && !!document.getElementById('setq')")
        b.eval("document.getElementById('setq').focus()")
        b.key("p")
        b.pump(0.3)
        self.assertEqual(b.eval("VIEW"), "settings")
        self.assertEqual(b.eval("document.activeElement.id"), "setq")   # b.key sends no text: the box keeps the focus

    def test_ignored_while_a_dialog_or_popup_is_open(self):
        b = self.neutral()
        b.eval("(()=>{ const d=document.createElement('dialog'); d.id='t288'; document.body.append(d); d.show(); })()")
        self.assertTrue(b.eval("popupOpen()"))
        b.key("p")
        b.pump(0.3)
        self.assertEqual(b.eval("VIEW"), "help", "a dialog is open")
        b.eval("document.getElementById('t288').remove()")
        b.eval("go('work')")
        b.wait("VIEW==='work' && !!document.querySelector('#workTbl tbody tr')")
        b.eval("document.activeElement&&document.activeElement.blur()")
        b.key("d")                                                             # the Display menu (a popup)
        b.wait("popupOpen()", 5)
        b.eval("document.activeElement&&document.activeElement.blur()")
        b.key("p")
        b.pump(0.3)
        self.assertEqual(b.eval("VIEW"), "work", "the Display menu is open")
        b.key("Escape")
        b.eval("closeDisp(false); document.activeElement&&document.activeElement.blur()")
        b.wait("!popupOpen()", 5)
        b.key("?")                                                             # the ? panel
        b.wait("helpPanelOpen()", 5)
        b.eval("document.activeElement&&document.activeElement.blur()")
        b.key("p")
        b.pump(0.3)
        self.assertEqual(b.eval("VIEW"), "work", "the ? panel is open")

    def test_ignored_while_a_peek_or_ask_creaite_is_open(self):
        b = self.b
        b.eval("go('work')")
        b.wait("VIEW==='work' && !!document.querySelector('#workTbl tbody tr[data-row]')")
        b.eval("document.activeElement&&document.activeElement.blur()")
        b.key("j")
        b.key("Enter")                                                         # a peek, not editing
        b.wait("document.getElementById('panel').classList.contains('on')", 5)
        self.assertFalse(b.eval("EDITING"))
        b.eval("document.activeElement&&document.activeElement.blur()")
        b.key("p")
        b.pump(0.3)
        self.assertEqual(b.eval("VIEW"), "work", "a peek is open")
        b.key("Escape")
        b.wait("!document.getElementById('panel').classList.contains('on')", 5)
        b.eval("openChat()")
        b.wait("document.getElementById('chat').classList.contains('on')", 5)
        b.eval("document.activeElement&&document.activeElement.blur()")
        b.key("p")
        b.pump(0.3)
        self.assertEqual(b.eval("VIEW"), "work", "ask creaite is open")
        b.eval("closeChat()")

    def test_the_field_picker_is_shift_f_and_f_is_files(self):
        b = self.b
        b.eval("go('work')")
        b.wait("VIEW==='work' && !!document.querySelector('#workTbl tbody tr')")
        b.eval("document.activeElement&&document.activeElement.blur()")
        b.key("F", 8)
        b.wait("document.getElementById('moreMenu').classList.contains('on') && document.activeElement.id==='fpq'", 5)
        self.assertEqual(b.eval("VIEW"), "work")
        self.assertEqual(b.eval("document.getElementById('moreBtn').dataset.key"), "Shift+F")
        b.key("Escape")
        b.wait("!document.getElementById('moreMenu').classList.contains('on')", 5)
        b.eval("document.activeElement&&document.activeElement.blur()")
        b.key("f")
        b.wait("VIEW==='files'", 5)
        self.assertFalse(b.eval("document.getElementById('moreMenu')?.classList.contains('on')||false"))

    def test_help_lists_the_keys(self):
        md = (ROOT / "system/templates/help.md").read_text(encoding="utf-8")
        self.assertIn("| Shift + F | Work: the filter picker", md)
        self.assertNotIn("| F | Work: the filter picker", md)
        for line in ("| T | Today", "| P | Projects", "| W | Work", "| I | Intake", "| F | Files", "| A | Activity", "| S | Settings",
                     "| R | Reports", "| E | People"):
            self.assertIn(line, md)


class IntakeKeepsAR(LiveBrowserCase):
    """On Intake, A and R stay its approve and reject: pressed again after an approve (when the focus has left the row) they
    never leave the page. Approves change data, so this class has its own vault."""
    width, height = 1400, 1000

    @classmethod
    def load(cls, v):
        IR.load(v)

    def test_a_a_a_and_r_stay_on_intake(self):
        b = self.b
        IR.open_meeting(b)
        row = "#v-intake-review tr.irprop"
        ok = f"[...document.querySelectorAll('{row}')].find(t=>!!t.querySelector('[data-ira=approve]:not([disabled])'))"
        start = b.eval("REV.length")
        for i in range(3):                                                     # an approve applies at once: the row leaves REV
            b.wait(f"!!{ok}", 25)
            b.eval(f"{ok}.focus()")
            b.key("a")
            b.wait(f"REV.length==={start - i - 1}", 25)
            self.assertEqual(b.eval("VIEW"), "intake-review", "A left Intake")
            b.eval("document.activeElement&&document.activeElement.blur()")   # what Cap saw: the focus drops to the page
            b.key("a")
            b.pump(0.3)
            self.assertEqual(b.eval("VIEW"), "intake-review", "A with the focus on the page left Intake")
        b.key("r")
        b.pump(0.3)
        self.assertEqual(b.eval("VIEW"), "intake-review", "R left Intake")

if __name__ == "__main__":
    unittest.main()
