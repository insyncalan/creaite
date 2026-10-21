"""#228 part B in a real browser: one logo tile for each partner organisation, in the cog panel and in the report headers.

Run: python3 dev/tests/test_partner_logos_browser.py   (needs Google Chrome; skipped otherwise)

The partners are the project's `- **Partners:** Acme Labs; Beta Works` line (another part of #228 edits it). The cog panel shows
"Partner: <name>" tiles (add, change, remove, tick each); the report header shows one slot per ticked partner in line order. A project with
no Partners line keeps the one old "A partner" tile (test_client_report_panel.py, test_report_logo_slots.py).
"""
import re
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_reporting_hub as H  # noqa: E402
from test_tracker import ABC  # noqa: E402

SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="10"><rect width="20" height="10" fill="#06c"/></svg>'
HDR = "#v-reporting .wr-logos [data-hdr-logo='{k}']"
TILE = "#crPanel .cfglogo[data-kind='{k}']"


class PartnerTiles(H.Hub):
    PARTNERS = "Acme Labs; Beta Works"

    def setUp(self):
        super().setUp()
        self.logos = self.v.root / "system/branding/logos"
        self.logos.mkdir(parents=True, exist_ok=True)
        for f in self.logos.glob("*"):
            f.unlink()
        mem = self.v.root / ABC / "CLAUDE.md"
        self.mem = mem
        text = re.sub(r"- \*\*(Partners|Client report logos):\*\*[^\n]*\n", "", mem.read_text())
        mem.write_text(text + f"- **Partners:** {self.PARTNERS}\n")

    def svg(self, name, fill="#06c"):
        p = Path(self.v.root) / name
        p.write_text(SVG.replace("#06c", fill))
        return p

    def line(self, label):
        m = re.search(r"\*\*" + re.escape(label) + r":\*\*[ \t]*([^\n]*)", self.mem.read_text())
        return m.group(1).strip() if m else None

    def wait_line(self, want, label="Client report logos"):
        end = time.time() + 8
        while time.time() < end and self.line(label) != want:
            time.sleep(0.1)
        self.assertEqual(self.line(label), want)

    def open_panel(self):
        self.open_hub()
        self.b.eval("openClientReport('ABC')")
        self.b.wait("!!document.querySelector('#crPanel [data-kind]')")

    def hdr(self):
        return self.q("[...document.querySelectorAll('#v-reporting .wr-logos [data-hdr-logo]')].map(b=>b.dataset.hdrLogo)")

    # ----- the cog panel

    def test_the_panel_has_one_tile_per_partner_named_from_the_line(self):
        self.open_panel()
        self.assertEqual(self.q("[...document.querySelectorAll('#crPanel .cfglogo')].map(t=>t.dataset.kind)"),
                         ["firm", "client", "partner:acme-labs", "partner:beta-works"])
        self.assertEqual(self.q("[...document.querySelectorAll('#crPanel .cfglogo .cfgname')].map(t=>t.firstChild.textContent)"),
                         ["The firm", "The client", "Partner: Acme Labs", "Partner: Beta Works"])
        self.assertEqual(self.q("document.querySelector(\"[data-logo-add='partner:beta-works']\").getAttribute('aria-label')"),
                         "Add the Beta Works's logo")

    def test_a_partners_logo_is_added_changed_and_removed_on_its_own_tile(self):
        self.open_panel()
        self.b.set_files("[data-logo-file='partner:beta-works']", [self.svg("b.svg")])
        self.b.wait(f"!!document.querySelector(\"{TILE.format(k='partner:beta-works')} .mark img\")", 20)
        self.assertEqual(sorted(f.name for f in self.logos.glob("*")), ["ABC-partner-beta-works.svg"])
        self.assertFalse(self.q(f"!!document.querySelector(\"{TILE.format(k='partner:acme-labs')} .mark img\")"), "the other tile is untouched")
        self.b.set_files("[data-logo-file='partner:acme-labs']", [self.svg("a.svg", "#c00")])
        self.b.wait(f"!!document.querySelector(\"{TILE.format(k='partner:acme-labs')} .mark img\")", 20)
        self.assertEqual(sorted(f.name for f in self.logos.glob("*")), ["ABC-partner-acme-labs.svg", "ABC-partner-beta-works.svg"])
        self.assertEqual(self.q("document.querySelector(\"[data-logo-add='partner:beta-works']\").textContent"), "Change")
        self.b.click("[data-logo-remove='partner:beta-works']")
        self.b.click("[data-logo-remove-yes='partner:beta-works']")
        self.b.wait(f"!document.querySelector(\"{TILE.format(k='partner:beta-works')} .mark img\")", 20)
        self.assertEqual(sorted(f.name for f in self.logos.glob("*")), ["ABC-partner-acme-labs.svg"])

    def test_ticking_each_partner_writes_the_line_and_all_ticked_is_one_partner(self):
        self.open_panel()
        self.assertEqual(self.q("[...document.querySelectorAll('#crPanel [data-logo-tick]')].map(c=>c.checked)"), [True, True, True, True])
        self.b.click("[data-logo-tick='partner:beta-works']")
        self.wait_line("firm, client, partner:acme-labs")
        self.b.click("[data-logo-tick='partner:acme-labs']")
        self.wait_line("firm, client")
        self.b.click("[data-logo-tick='partner:acme-labs']")
        self.b.click("[data-logo-tick='partner:beta-works']")
        self.wait_line("firm, client, partner")

    def test_two_ticks_before_the_first_save_lands_keep_both(self):
        # v2.5.3 gate (CI run 39526296175): the second tick read the ticks as they were before the first save came back, and lost it
        self.open_panel()
        self.b.click("[data-logo-tick='partner:beta-works']")
        self.wait_line("firm, client, partner:acme-labs")
        self.b.click("[data-logo-tick='partner:acme-labs']")
        self.wait_line("firm, client")
        self.b.eval("document.querySelector(\"[data-logo-tick='partner:acme-labs']\").click(); "
                    "document.querySelector(\"[data-logo-tick='partner:beta-works']\").click(); 1")
        self.wait_line("firm, client, partner")

    def test_a_bare_partner_line_ticks_every_partner(self):
        self.mem.write_text(self.mem.read_text() + "- **Client report logos:** firm, partner\n")
        self.open_panel()
        self.assertEqual(self.q("[...document.querySelectorAll('#crPanel [data-logo-tick]')].map(c=>c.checked)"), [True, False, True, True])

    def test_an_added_partner_is_ticked_when_all_were(self):
        self.mem.write_text(self.mem.read_text() + "- **Client report logos:** firm, client, partner\n")
        self.mem.write_text(self.mem.read_text().replace("Acme Labs; Beta Works", "Acme Labs; Beta Works; Cora Ltd"))
        self.open_panel()
        self.assertEqual(self.q("[...document.querySelectorAll('#crPanel [data-logo-tick]')].map(c=>c.checked)"), [True, True, True, True, True])

    # ----- the report headers

    def test_the_header_has_a_slot_per_ticked_partner_in_line_order(self):
        self.open_hub()
        self.assertEqual(self.hdr(), ["firm", "client", "partner:acme-labs", "partner:beta-works"])
        self.assertEqual(self.q("document.querySelector(\"" + HDR.format(k="partner:beta-works") + "\").getAttribute('aria-label')"),
                         "Add Beta Works logo")
        self.q("setClientLogos('ABC', ['client', 'partner:beta-works'])")
        self.b.pump(0.5)
        self.open_hub()
        self.assertEqual(self.hdr(), ["firm", "client", "partner:beta-works"], "an unticked partner has no slot")

    def test_choosing_a_picture_in_a_partners_slot_saves_it_and_both_reports_show_it(self):
        self.open_hub()
        self.b.set_files("[data-hdr-logo-file='partner:acme-labs']", [self.svg("a.svg")])
        self.b.wait(f"!!document.querySelector(\"{HDR.format(k='partner:acme-labs')} img\")", 20)
        self.assertTrue((self.logos / "ABC-partner-acme-labs.svg").is_file())
        self.b.set_files("[data-hdr-logo-file='partner:beta-works']", [self.svg("b.svg", "#c00")])
        self.b.wait(f"!!document.querySelector(\"{HDR.format(k='partner:beta-works')} img\")", 20)
        self.b.click("#hubSeg [data-hv='client']")
        self.b.wait("document.querySelector('#v-reporting .page').dataset.audience==='client'", 20)
        self.assertEqual(self.q("document.querySelectorAll('#v-reporting .wr-logos img').length"), 2)
        self.assertEqual(self.hdr(), ["firm", "client", "partner:acme-labs", "partner:beta-works"])

    def test_show_as_exported_draws_each_ticked_partner_logo_and_no_text_for_a_partner(self):
        (self.logos / "ABC-partner-beta-works.svg").write_text(SVG)
        (self.logos / "ABC-partner-acme-labs.svg").write_text(SVG.replace("#06c", "#c00"))
        self.open_hub()
        self.q("setClientLogos('ABC', ['partner:acme-labs'])")
        self.b.pump(0.5)
        self.open_hub()
        self.b.click("#hubExp")
        self.b.pump(0.4)
        self.assertEqual(self.hdr(), [])
        self.assertEqual(self.q("document.querySelectorAll('#v-reporting .wr-logos img').length"), 1, "only the ticked partner's picture")
        header = self.q("document.querySelector('#v-reporting .wr-hd').innerText")
        self.assertNotIn("Beta Works", header)
        self.assertNotIn("Acme Labs", header, "a partner's name shows only as its picture")

    def test_the_old_partner_file_is_the_first_partners_tile_with_no_migration(self):
        (self.logos / "ABC-partner.svg").write_text(SVG)
        self.open_panel()
        self.b.wait(f"!!document.querySelector(\"{TILE.format(k='partner:acme-labs')} .mark img\")", 20)
        self.assertFalse(self.q(f"!!document.querySelector(\"{TILE.format(k='partner:beta-works')} .mark img\")"))
        self.assertEqual([f.name for f in self.logos.glob("*")], ["ABC-partner.svg"], "nothing renamed")


if __name__ == "__main__":
    unittest.main()
