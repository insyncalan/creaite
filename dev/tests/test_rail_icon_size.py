"""#182: the left rail's icon size (Small, Medium, Large), chosen in Customise sidebar, in a real browser.

Run: python3 dev/tests/test_rail_icon_size.py   (needs Google Chrome; skipped otherwise)

dashboard.rail_icon_size is "small" (20px, what the rail has always had; the default), "medium" (24px) or "large"
(28px); the rail's widths do not change (188, 76, 56). Customise sidebar has an Icon size group of three buttons; Done saves it.
Checked at 1400px (expanded) and 900px (collapsed with labels), and in the three rail states. Dates pinned (CREAITE_NOW).
"""
import json
import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("CREAITE_NO_LAUNCH", "1")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

ICON = {"small": 20, "medium": 24, "large": 28}
CLIPPED = """[...document.querySelectorAll('.rail #railMain .rl, .rail #railMain .badge')].filter(e=>e.offsetParent
  && (e.scrollWidth>e.clientWidth+1 || e.getBoundingClientRect().right>document.querySelector('.rail').getBoundingClientRect().right+0.5)).map(e=>e.textContent)"""
RAIL_W = "Math.round(document.querySelector('.rail').getBoundingClientRect().width)"


class IconSizeBase(LiveBrowserCase):
    width, height = 1400, 900

    def setUp(self):
        super().setUp()
        self.b.resize(self.width, self.height)      # the page exactly this size: headless Chrome's page can be shorter than its window
                                                    # (Chrome for Testing 156 on Linux: 200 px), and the dialog checks below measure it

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": "2026-10-16 09:00"}

    def saved(self):
        return json.loads((self.v.root / "system/config/settings.json").read_text())["dashboard"].get("rail_icon_size")

    def icon(self):
        return self.b.eval("(r=>[Math.round(r.width),Math.round(r.height)])(document.querySelector('.rail [data-v=work] svg').getBoundingClientRect())")

    def rail_w(self):
        return self.b.eval(RAIL_W)

    def open_customise(self):
        self.b.click("#railMore")
        self.b.wait("!document.getElementById('railMoreMenu').hidden")
        self.b.click("#railCustBtn")
        self.b.wait("document.getElementById('railCust').open")

    def choose(self, size):
        self.open_customise()
        self.b.click(f'#railCust .rcsz[data-size="{size}"]')
        self.b.click("#railCustDone")
        self.b.wait("!document.getElementById('railCust').open")
        self.b.wait(f"railIconSize.value==='{size}'", 5)
        for _ in range(100):
            if self.saved() == size:
                return
            self.b.pump(0.05)
        self.fail("rail_icon_size never saved")


class IconSize(IconSizeBase):
    def test_the_section_is_there_and_small_is_the_default(self):
        b = self.b
        self.assertEqual(self.icon(), [20, 20])                                                # nothing changes for anyone who does not choose
        self.assertEqual(self.rail_w(), 188)
        self.open_customise()
        self.assertEqual(b.eval("[...document.querySelectorAll('#railCust .rcsz')].map(x=>[x.dataset.size,x.getAttribute('aria-pressed')])"),
                         [["small", "true"], ["medium", "false"], ["large", "false"]])
        self.assertEqual(b.eval("document.getElementById('railCustSizeH').textContent"), "Icon size")
        self.assertEqual(b.eval("document.querySelector('#railCust .rcszs').closest('[role=group]').getAttribute('aria-labelledby')"), "railCustSizeH")

    def test_each_size_sets_the_icon_box_persists_and_clips_nothing(self):
        b = self.b
        for size in ("medium", "large", "small"):
            self.choose(size)
            n = ICON[size]
            self.assertEqual(self.icon(), [n, n], size)
            self.assertEqual(self.rail_w(), 188)                                               # the width is unchanged
            self.assertEqual(b.eval(CLIPPED), [], size)                                        # no name or count clipped
            b.reload(wait_for="typeof go==='function' && LIVE")
            self.assertEqual(self.icon(), [n, n], size)                                        # kept across a reload
            self.assertEqual(self.saved(), size)
            b.click("#railTog")                                                                # collapsed with labels
            b.wait(f"{RAIL_W}===76", 5)
            self.assertEqual(self.icon(), [n, n], size)
            self.assertEqual(b.eval(CLIPPED), [], size)
            ic = b.eval("document.querySelector('.rail [data-v=work] svg').getBoundingClientRect().bottom")
            rl = b.eval("document.querySelector('.rail [data-v=work] .rl').getBoundingClientRect().top")
            self.assertGreaterEqual(rl, ic - 1, size)                                          # the label stays under the icon
            b.eval("railSetLabels(false)")                                                     # icons only
            b.wait(f"{RAIL_W}===56", 5)
            self.assertEqual(self.icon(), [n, n], size)
            b.eval("railSetLabels(true)")
            b.click("#railTog")
            b.wait(f"{RAIL_W}===188", 5)

    def test_cancel_and_esc_leave_it_and_esc_returns_focus_outside_the_dialog(self):
        b = self.b
        self.open_customise()
        b.click('#railCust .rcsz[data-size="large"]')
        self.assertEqual(b.eval("document.querySelector('#railCust .rcsz[data-size=large]').getAttribute('aria-pressed')"), "true")
        self.assertEqual(self.icon(), [20, 20])                                                # nothing changes until Done
        b.click("#railCustCancel")
        b.wait("!document.getElementById('railCust').open")
        self.assertEqual(self.icon(), [20, 20])
        self.assertIn(self.saved(), (None, "small"))                                         # never changed: still the default
        self.open_customise()
        self.assertEqual(b.eval("document.querySelector('#railCust .rcsz[data-size=small]').getAttribute('aria-pressed')"), "true")   # starts from the saved one
        b.click('#railCust .rcsz[data-size="medium"]')
        b.key("Escape")
        b.wait("!document.getElementById('railCust').open")
        self.assertEqual(self.icon(), [20, 20])
        self.assertFalse(b.eval("document.getElementById('railCust').contains(document.activeElement)"))

    def test_reset_puts_back_small(self):
        b = self.b
        self.choose("large")
        self.open_customise()
        b.click("#railCustReset")
        self.assertEqual(b.eval("document.querySelector('#railCust .rcsz[data-size=small]').getAttribute('aria-pressed')"), "true")
        b.click("#railCustDone")
        b.wait("!document.getElementById('railCust').open")
        self.assertEqual(self.icon(), [20, 20])

    ADV = """(()=>{const r=[...document.querySelectorAll('#settingsBody .srow,#settingsBody .igrow,#settingsBody .row')].find(x=>/Icon size/.test(x.textContent)); return r&&r.querySelector('select')})()"""

    def adv_value(self):
        self.b.wait(f"!!{self.ADV}", 8)
        return self.b.eval(f"{self.ADV}.value")

    def set_stored(self, value):
        p = self.v.root / "system/config/settings.json"
        js = json.loads(p.read_text())
        if value is None:
            js["dashboard"].pop("rail_icon_size", None)
        else:
            js["dashboard"]["rail_icon_size"] = value
        p.write_text(json.dumps(js, indent=2) + "\n")

    def test_settings_advanced_and_customise_stay_in_step_without_a_reload(self):
        b = self.b
        b.eval("location.hash='#settings/look'")
        self.assertEqual(self.adv_value(), "small")
        self.assertEqual(b.eval(f"[...{self.ADV}.options].map(o=>o.textContent)"), ["Small", "Medium", "Large"])
        b.eval(f"(s=>{{s.value='large'; s.dispatchEvent(new Event('change',{{bubbles:true}}))}})({self.ADV})")   # Advanced -> rail and dialog
        b.wait("railIconSize.value==='large'", 5)
        self.assertEqual(self.icon(), [28, 28])
        self.open_customise()
        self.assertEqual(b.eval("document.querySelector('#railCust .rcsz[data-size=large]').getAttribute('aria-pressed')"), "true")
        b.click('#railCust .rcsz[data-size="medium"]')                                        # dialog -> Advanced
        b.click("#railCustDone")
        b.wait("!document.getElementById('railCust').open")
        b.wait(f"{self.ADV}.value==='medium'", 8)
        self.assertEqual(self.icon(), [24, 24])

    def test_a_missing_or_unknown_stored_value_is_small_everywhere(self):
        b = self.b
        for value in (None, "huge"):
            self.set_stored(value)
            b.reload(wait_for="typeof go==='function' && LIVE")
            self.assertEqual(self.icon(), [20, 20], value)
            b.eval("location.hash='#settings/look'")
            self.assertEqual(self.adv_value(), "small", value)                                # Small, not blank
            self.open_customise()
            self.assertEqual(b.eval("document.querySelector('#railCust .rcsz[data-size=small]').getAttribute('aria-pressed')"), "true", value)
            b.click("#railCustCancel")
            b.wait("!document.getElementById('railCust').open")


class IconSize900(IconSizeBase):
    width, height = 900, 800

    def test_the_section_is_there_and_small_is_the_default(self):
        self.assertEqual(self.icon(), [20, 20])
        self.assertEqual(self.rail_w(), 76)                                                    # 900px: collapsed with labels
        self.open_customise()
        self.assertEqual(self.b.eval("document.querySelectorAll('#railCust .rcsz').length"), 3)
        self.assertTrue(self.b.eval("(r=>r.bottom<=innerHeight&&r.right<=innerWidth)(document.querySelector('#railCustDone').getBoundingClientRect())"))

    def test_each_size_sets_the_icon_box_persists_and_clips_nothing(self):
        b = self.b
        for size in ("large", "medium", "small"):
            self.choose(size)
            n = ICON[size]
            self.assertEqual(self.icon(), [n, n], size)
            self.assertEqual(self.rail_w(), 76)
            self.assertEqual(b.eval(CLIPPED), [], size)
            b.reload(wait_for="typeof go==='function' && LIVE")
            self.assertEqual(self.icon(), [n, n], size)


if __name__ == "__main__":
    unittest.main()
