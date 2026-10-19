"""#233 part a: click the logo's place in the report header to add or change the logo (Alan's Round 8 requirement).

In the header of both reports (edit mode only): each logo slot that is ON for the report and has no file shows a dashed
"Add <firm|client|partner> logo" tile; a filled logo is a button "Change <name> logo". Both open the same chooser flow as the cog
panel (stores/reportingSettings.js uploadClientLogo), the logo shows at once in both reports, the firm's asks first, and nothing
shows in "Show as exported" or for a slot that is turned off.

Run: python3 dev/tests/test_report_logo_slots.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_reporting_hub as H  # noqa: E402
from live_browser import TEST_PALETTES  # noqa: E402

SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="10"><rect width="20" height="10" fill="#06c"/></svg>'
TILE = "#v-reporting .wr-logos [data-hdr-logo={k}]"


class LogoSlots(H.Hub):
    def setUp(self):
        super().setUp()
        logos = self.v.root / "system/branding/logos"
        logos.mkdir(parents=True, exist_ok=True)
        for f in logos.glob("*"):
            f.unlink()
        self.b.reload("typeof go==='function' && LIVE")                      # the shared server keeps the last test's ticks: all three on
        self.q("setClientLogos('ABC', ['firm', 'client', 'partner'])")
        self.b.pump(0.6)

    def svg(self, name):
        p = Path(self.v.root) / name
        p.write_text(SVG)
        return p

    def tiles(self):
        return self.q("[...document.querySelectorAll('#v-reporting .wr-logos [data-hdr-logo]')].map(b=>b.dataset.hdrLogo)")

    def has_img(self, k):
        return self.q(f"!!document.querySelector('#v-reporting .wr-logos [data-hdr-logo={k}] img')")

    def test_a_dashed_add_tile_shows_for_each_slot_that_is_on_and_has_no_file(self):
        self.open_hub()
        self.assertEqual(self.tiles(), ["firm", "client", "partner"])
        for k in ("firm", "client", "partner"):
            sel = TILE.format(k=k)
            self.assertEqual(self.q(f"document.querySelector('{sel}').getAttribute('aria-label')"), f"Add {k} logo")
            self.assertIn(f"Add {k} logo", self.q(f"document.querySelector('{sel}').innerText"))
            self.assertEqual(self.q(f"getComputedStyle(document.querySelector('{sel}')).borderTopStyle"), "dashed")

    def test_a_slot_that_is_off_shows_nothing(self):
        self.open_hub()
        self.q("setClientLogos('ABC', ['client'])")
        self.b.pump(0.5)
        self.open_hub()
        self.assertEqual(self.tiles(), ["firm", "client"], "the partner slot is turned off in the cog panel")

    def test_nothing_shows_in_show_as_exported(self):
        self.open_hub()
        self.assertEqual(len(self.tiles()), 3)
        self.b.click("#hubExp")
        self.b.pump(0.3)
        self.assertEqual(self.tiles(), [])
        self.assertEqual(self.q("document.querySelectorAll('#v-reporting .wr-logos .wr-logo-add').length"), 0)

    def test_choosing_a_picture_saves_it_and_both_reports_show_it_at_once(self):
        self.open_hub()
        self.b.set_files("[data-hdr-logo-file=client]", [self.svg("client.svg")])
        self.b.wait(f"!!document.querySelector('{TILE.format(k='client')} img')", 20)
        self.assertTrue((self.v.root / "system/branding/logos/ABC-client.svg").is_file())
        self.assertEqual(self.q(f"document.querySelector('{TILE.format(k='client')}').getAttribute('aria-label')"), "Change client logo")
        self.b.click("#hubSeg [data-hv='client']")
        self.b.wait("document.querySelector('#v-reporting .page').dataset.audience==='client'", 20)
        self.assertTrue(self.has_img("client"), "the client report shows it too, without a reload")
        self.b.click("#hubSeg [data-hv='side']")
        self.b.wait("document.querySelectorAll('#v-reporting .page').length==2", 20)
        self.assertEqual(self.q("document.querySelectorAll('#v-reporting .wr-logos [data-hdr-logo=client] img').length"), 2)

    def test_change_replaces_the_file(self):
        self.open_hub()
        self.b.set_files("[data-hdr-logo-file=partner]", [self.svg("p1.svg")])
        self.b.wait(f"!!document.querySelector('{TILE.format(k='partner')} img')", 20)
        before = self.q(f"document.querySelector('{TILE.format(k='partner')} img').src")
        other = Path(self.v.root) / "p2.svg"
        other.write_text(SVG.replace("#06c", "#c00"))
        self.b.set_files("[data-hdr-logo-file=partner]", [other])
        self.b.wait(f"document.querySelector('{TILE.format(k='partner')} img').src!=={before!r}", 20)
        self.assertEqual(len(list((self.v.root / "system/branding/logos").glob("ABC-partner*"))), 1)

    def test_replacing_the_firm_logo_asks_first_and_adding_one_does_not(self):
        self.open_hub()
        self.q("window.__clicks=0; HTMLInputElement.prototype.click=function(){ window.__clicks++; }")
        self.b.click(TILE.format(k="firm"))
        self.assertEqual(self.q("window.__clicks"), 1, "no logo yet: nothing to replace, the chooser opens at once")
        self.b.set_files("[data-hdr-logo-file=firm]", [self.svg("firm.svg")])
        self.b.wait(f"!!document.querySelector('{TILE.format(k='firm')} img')", 20)
        self.b.click(TILE.format(k="firm"))
        self.assertEqual(self.q("window.__clicks"), 1, "the chooser waits for the answer")
        self.assertIn("used by all projects", self.q("document.querySelector('#v-reporting .wr-logo-ask').innerText"))
        self.b.click("[data-hdr-logo-no=firm]")
        self.assertEqual(self.q("!!document.querySelector('#v-reporting .wr-logo-ask')"), False)
        self.assertEqual(self.q("window.__clicks"), 1)
        self.b.click(TILE.format(k="firm"))
        self.b.click("[data-hdr-logo-yes=firm]")
        self.assertEqual(self.q("window.__clicks"), 2)

    def test_keyboard_enter_opens_the_chooser_and_escape_cancels_the_firm_question(self):
        self.open_hub()
        self.b.set_files("[data-hdr-logo-file=firm]", [self.svg("firm.svg")])
        self.b.wait(f"!!document.querySelector('{TILE.format(k='firm')} img')", 20)
        self.q("window.__clicks=0; HTMLInputElement.prototype.click=function(){ window.__clicks++; }")
        self.q(f"document.querySelector('{TILE.format(k='client')}').focus()")
        self.b.key("Enter")
        self.assertEqual(self.q("window.__clicks"), 1)
        self.q(f"document.querySelector('{TILE.format(k='firm')}').focus()")
        self.b.key("Enter")
        self.b.wait("!!document.querySelector('#v-reporting .wr-logo-ask')")
        self.b.key("Escape")
        self.b.pump(0.2)
        self.assertEqual(self.q("!!document.querySelector('#v-reporting .wr-logo-ask')"), False)
        self.assertEqual(self.q("document.activeElement && document.activeElement.dataset.hdrLogo"), "firm", "focus returns to the logo")
        self.assertEqual(self.q("window.__clicks"), 1)

    def test_tiles_are_readable_in_light_and_dark_and_both_palettes(self):
        self.open_hub()
        for palette in TEST_PALETTES:
            for theme in ("light", "dark"):
                self.q(f"document.documentElement.dataset.palette={palette!r}; document.documentElement.dataset.theme={theme!r}")
                self.b.pump(0.1)
                r = self.q(f"(()=>{{const e=document.querySelector('{TILE.format(k='client')}'),r=e.getBoundingClientRect();return [r.width,r.height]}})()")
                self.assertGreater(r[0], 40, (palette, theme))
                self.assertGreaterEqual(r[1], 24, (palette, theme))
                self.assertEqual(self.q("(()=>{const e=document.querySelector('.wr-logo-add'),c=getComputedStyle(e);return c.color!==c.backgroundColor})()"), True)


if __name__ == "__main__":
    unittest.main()
