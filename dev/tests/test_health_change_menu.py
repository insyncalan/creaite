"""#287: the weekly report's health Change menu (On track / At risk / Off track) is the section menu's popup.

Before: it was a Menu drawn inside the scaled report page, right-aligned to the 96 px indicator and 300 px wide, so it ran off
the left of the sheet (clipped under the side bar) and was scaled up with the page (45 px rows at 1440). Now it is opened with the
shared openMenu and the section menu's class ("rsmenu"), so it is a popup above the page, kept clear of the side bar, with
compact icon-and-word rows, and it takes whichever palette is on exactly as the section menu does.

Real Chrome on the real live server, desktop only (900 and 1440 px), in the Claude, Retro Arcade, Cursor and creaite palettes.
Run: python3 dev/tests/test_health_change_menu.py      (Chrome tier; skipped without Chrome)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_report_sheet as RS  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402

PALETTES = ("Claude", "Retro Arcade", "Cursor", "creaite")
WIDTHS = (900, 1440)
MENU = '.pophost [role=menu][aria-label="Health for this week"]'

REPORT = """((sel)=>{const m=document.querySelector(sel); if(!m) return null;
  const r=m.getBoundingClientRect(), c=getComputedStyle(m), rail=document.querySelector('.rail'), rr=rail?rail.getBoundingClientRect():{right:0},
    items=[...m.querySelectorAll('[role^=menuitem]')];
  return {l:r.left,t:r.top,r:r.right,b:r.bottom,w:r.width,iw:innerWidth,ih:innerHeight,rail:rr.right,cls:m.className,
    inScaled:!!m.closest('.sheet-a4'), outline:c.outlineStyle+' '+c.outlineWidth, shadow:c.boxShadow, border:c.borderTopWidth+' '+c.borderTopStyle,
    radius:c.borderTopLeftRadius, names:items.map(i=>i.textContent.trim()), h:items.map(i=>i.getBoundingClientRect().height),
    fs:items.map(i=>getComputedStyle(i).fontSize), icons:items.map(i=>!!i.querySelector('svg')),
    roles:items.map(i=>i.getAttribute('role')), current:items.map(i=>i.getAttribute('aria-checked')==='true'),
    hit:items.map(i=>{const b=i.getBoundingClientRect(), e=document.elementFromPoint(b.left+b.width/2,b.top+b.height/2); return !!e && m.contains(e)})}})"""


class HealthChangeMenu(LiveBrowserCase):
    shared_server = True
    load = RS.WeeklySheet.load

    def start(self, w, palette):
        self.b.resize(w, 900)
        self.b.reload("typeof go==='function' && LIVE")
        self.b.eval(f"document.documentElement.dataset.palette='{palette}'; document.documentElement.dataset.theme='light'")
        self.b.eval("go('reporting','ABC')")
        self.b.wait("document.querySelector('#v-reporting .wr-chg')", 20)
        self.b.pump(0.4)
        self.b.eval("document.querySelector('#v-reporting .wr-chg').scrollIntoView({block:'center'})")
        self.b.pump(0.2)

    def open_health(self):
        self.b.eval("document.querySelector('#v-reporting .wr-chg').click()")
        self.b.wait(f"!!document.querySelector({MENU!r})", 5)
        self.b.pump(0.3)                       # the popup's opening animation
        return self.b.eval(f"({REPORT})({MENU!r})")

    def section_menu(self):
        """The section menu's popup in the same palette: the look the health menu must share."""
        self.b.key("Escape")
        self.b.eval("document.querySelector('#v-reporting section[data-id=risks] .sheet-hbtn').click()")
        self.b.wait("!!document.querySelector('.pophost [role=menu]')", 5)
        self.b.pump(0.3)
        m = self.b.eval(f"({REPORT})('.pophost [role=menu]')")
        self.b.key("Escape")
        return m

    def test_a_compact_popup_inside_the_window_in_every_palette(self):
        for w in WIDTHS:
            for palette in PALETTES:
                with self.subTest(width=w, palette=palette):
                    self.start(w, palette)
                    m = self.open_health()
                    self.assertIsNotNone(m, "the health menu opens as a popup above the page")
                    self.assertFalse(m["inScaled"], "not inside the scaled report page")
                    self.assertIn("rsmenu", m["cls"].split(), "the section menu's class")
                    self.assertGreaterEqual(m["l"], m["rail"] - 0.5, "never under the side bar (not clipped at the left)")
                    self.assertGreaterEqual(m["t"], 0)
                    self.assertLessEqual(m["r"], m["iw"])
                    self.assertLessEqual(m["b"], m["ih"])
                    self.assertLess(m["w"], 220, "no wider than its words")
                    self.assertEqual([n.split("·")[0].strip() for n in m["names"]], ["On track", "At risk", "Off track"])
                    self.assertTrue(all(m["hit"]), "every option is visible and not covered")
                    self.assertTrue(all(28 <= h <= 34 for h in m["h"]), f"normal row height, got {m['h']}")
                    self.assertEqual(set(m["fs"]), {"13px"}, "normal text size")
                    self.assertTrue(all(m["icons"]), "a small icon before each word")
                    self.assertEqual(m["outline"].split()[0], "none", "no outline on the menu box")
                    self.assertEqual(set(m["roles"]), {"menuitemradio"}, "one of three: radio items")
                    self.assertEqual(sum(1 for c in m["current"] if c), 1, "the current health is aria-checked")
                    sec = self.section_menu()
                    for k in ("shadow", "border", "radius", "outline"):
                        self.assertEqual(m[k], sec[k], f"{k}: the same look as the section menu in {palette}")

    def test_picking_changes_the_health_and_keys_work(self):
        self.start(1440, "creaite")
        before = self.b.eval("document.querySelector('#v-reporting .wr-flag').textContent.trim()")
        m = self.open_health()
        want = next(n for n in ("On track", "At risk", "Off track") if n.upper() != before)
        self.assertIn(self.b.eval("document.activeElement.closest('[role=menu]')?.getAttribute('aria-label')||''"), "Health for this week",
                      "focus moves into the menu")
        self.b.eval(f"[...document.querySelectorAll('{MENU} [role=menuitemradio]')].find(b=>b.textContent.trim().startsWith({want!r})).click()")
        self.b.wait(f"!document.querySelector({MENU!r})", 5)
        self.b.wait(f"document.querySelector('#v-reporting .wr-flag').textContent.trim()==={want.upper()!r}", 5)
        self.assertEqual(self.b.eval("document.querySelector('#v-reporting .wr-chg').getAttribute('aria-expanded')"), "false")
        m = self.open_health()
        self.assertEqual([n.split("·")[0].strip() for n, c in zip(m["names"], m["current"]) if c], [want], "the new health is the checked one")
        self.b.key("Escape")
        self.b.wait(f"!document.querySelector({MENU!r})", 5)
        self.assertTrue(self.b.eval("document.activeElement===document.querySelector('#v-reporting .wr-chg')"), "Esc gives focus back")
        del m


if __name__ == "__main__":
    unittest.main()
