"""#158 Phase B part 3: Help's What's new tab. The plain release notes are copied into system/templates/help/whats-new.md at release
(dev/tools/build_guides.py; the app never reads dev/ at run time). A dot on the tab and on Settings' Help button shows after an
update until the tab has been opened once for that version.

Run: python3 dev/tests/test_help_whatsnew.py   (the page tests need Google Chrome; skipped otherwise)
"""
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import TEST_PALETTES_JS, LiveBrowserCase  # noqa: E402
from test_tracker import REPO  # noqa: E402

sys.path.insert(0, str(REPO / "system" / "scripts"))
sys.path.insert(0, str(REPO / "dev" / "tools"))
import build_dashboard as bd  # noqa: E402
import build_guides as bg  # noqa: E402
import build_release as br  # noqa: E402
import update  # noqa: E402

VERSION = (REPO / "VERSION").read_text(encoding="utf-8").strip()
FILE = REPO / "system" / "templates" / "help" / "whats-new.md"


class Copy(unittest.TestCase):
    def test_the_copy_is_current_and_holds_the_installed_versions_notes(self):
        self.assertEqual(FILE.read_text(encoding="utf-8"), bg.whats_new_text(), "run python3 dev/tools/build_guides.py")
        if (REPO / "dev" / "release-notes" / f"{VERSION}.md").exists() or (REPO / "dev" / "release-notes" / f"{VERSION}-plain.md").exists():
            self.assertIn(f"\n## {VERSION}\n", FILE.read_text(encoding="utf-8"))

    def test_newest_first_and_only_shipped_versions(self):
        vs = [v["ver"] for v in bd.whats_new_parse()]
        self.assertEqual(vs, sorted(vs, key=bg._vkey, reverse=True))
        self.assertTrue(all(bg._vkey(v) <= bg._vkey(VERSION) for v in vs))
        self.assertGreaterEqual(len(vs), 1)

    def test_an_unreleased_version_without_notes_is_left_out_not_an_error(self):
        newer = f"{VERSION.split('.')[0]}.{int(VERSION.split('.')[1]) + 1}.0"
        text = bg.whats_new_text(newer)                                      # no notes file for it
        self.assertNotIn(f"## {newer}\n", text)
        self.assertEqual(text, bg.whats_new_text(VERSION))                   # Help shows the newest notes there are
        self.assertEqual(bd.whats_new_parse(""), [])                         # no file: no tab

    def test_a_plain_notes_file_is_preferred_to_the_full_one(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "9.9.9.md").write_text("# creaite 9.9.9\n\nTechnical.\n\n## Safer\n\n- sandbox\n", encoding="utf-8")
            (d / "9.9.9-plain.md").write_text("# creaite 9.9.9\n\nPlain words.\n\n## What is new\n\n- a thing\n", encoding="utf-8")
            old = bg.NOTES
            bg.NOTES = d
            try:
                text = bg.whats_new_text("9.9.9")
            finally:
                bg.NOTES = old
        self.assertIn("Plain words.", text)
        self.assertNotIn("Technical.", text)
        self.assertIn("### What is new", text)                                # a note's ## becomes ###, its title line is dropped
        self.assertNotIn("# creaite 9.9.9", text)

    def test_the_release_refuses_a_missing_copy_but_not_missing_notes(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "3.0.0.md").write_text("# creaite 3.0.0\n\nx\n", encoding="utf-8")
            wn = d / "whats-new.md"
            wn.write_text("## 2.9.0\nold\n", encoding="utf-8")
            with self.assertRaises(update.UpdateError):
                br.refuse_stale_whats_new("3.0.0", wn=wn, notes_dir=d)
            br.refuse_stale_whats_new("3.1.0", wn=wn, notes_dir=d)           # no notes for 3.1.0 yet: not refused
            wn.write_text("## 3.0.0\nx\n", encoding="utf-8")
            br.refuse_stale_whats_new("3.0.0", wn=wn, notes_dir=d)

    def test_the_tab_is_plain_html_newest_first(self):
        h = bd.help_sections()
        tab = [t for t in h["tabs"] if t["id"] == "whatsnew"][0]
        self.assertEqual(tab["title"], "What's new")
        vers = re.findall(r'<article class="hp-wn" id="wn-([\d.]+)"', tab["html"])
        self.assertEqual(vers, h["versions"])
        self.assertEqual(h["latest"], VERSION if VERSION in vers else vers[0])
        text = re.sub(r"<[^>]+>", " ", tab["html"])
        for token in ("**", "`", "[[", "](#", "{version}"):
            self.assertNotIn(token, text)


class WhatsNewPage(LiveBrowserCase):
    shared_server = True

    def test_the_tab_the_dot_and_the_address(self):
        b = self.b
        b.eval("try{ localStorage.removeItem('creaite-help-whatsnew-seen'); }catch(e){}")
        b.reload("typeof go==='function' && LIVE")
        b.eval("go('settings')")
        self.assertTrue(b.eval("getComputedStyle(document.querySelector('#v-settings [data-go=help]'),'::after').content!=='none'"))   # the dot on Settings' button
        b.eval("go('help','start')")
        tabs = b.eval("[...document.querySelectorAll('#helpTabs [role=tab]')].map(t=>t.textContent)")
        self.assertEqual(tabs[-1], "What's new")
        dot = "getComputedStyle(document.querySelector('#helpTabs [data-help=whatsnew]'),'::after').content!=='none'"
        self.assertTrue(b.eval(dot))
        b.click("#helpTabs [data-help=whatsnew]")
        b.pump(0.2)
        self.assertEqual(b.eval("location.hash"), "#help-whatsnew")
        arts = b.eval("[...document.querySelectorAll('#helpPane .hp-wn')].map(a=>a.dataset.ver)")
        self.assertEqual(arts, sorted(arts, key=lambda v: [int(x) for x in v.split('.')], reverse=True))
        self.assertFalse(b.eval(dot))                                         # opened once: the dot clears ...
        self.assertFalse(b.eval("document.body.classList.contains('wn-new')"))
        b.reload("typeof go==='function' && LIVE")                            # ... and stays cleared
        b.eval("go('help','start')")
        self.assertFalse(b.eval(dot))
        b.eval("localStorage.setItem('creaite-help-whatsnew-seen', JSON.stringify('0.0.1'))")   # an older version seen: it shows again
        b.reload("typeof go==='function' && LIVE")
        b.eval("go('help','start')")
        self.assertTrue(b.eval(dot))
        old = arts[-1]
        r = b.eval(f"(()=>{{ go('help','whatsnew-{old}'); return [HELPARG, location.hash]; }})()")
        self.assertEqual(r, [f"whatsnew-{old}", f"#help-whatsnew-{old}"])
        self.assertEqual(b.eval(f"parseHash('#help-whatsnew-{old}').arg"), f"whatsnew-{old}")

    def test_search_finds_the_notes(self):
        b = self.b
        b.eval("go('help','start'); document.querySelector('#helpS').focus()")
        b.type("minutes beside their transcript")
        b.pump(0.3)
        groups = b.eval("[...document.querySelectorAll('#helpRes .hs-g h2')].map(h=>h.firstChild.textContent.trim())")
        self.assertIn("What's new", groups)

    def test_desktop_and_900_both_palettes_and_modes(self):
        b = self.b
        for width in (1400, 900):
            b.resize(width, 900)
            b.eval("go('help','whatsnew')")
            r = b.eval("""(()=>{ const lum=c=>{ const [r,g,b]=c.match(/[\\d.]+/g).slice(0,3).map(Number).map(v=>{ v/=255; return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4); }); return 0.2126*r+0.7152*g+0.0722*b; };
              const ratio=(a,b)=>{ const x=lum(a), y=lum(b); return (Math.max(x,y)+0.05)/(Math.min(x,y)+0.05); };
              const bgOf=el=>{ for(let e=el;e;e=e.parentElement){ const c=getComputedStyle(e).backgroundColor; if(!/rgba\\(0, 0, 0, 0\\)|transparent/.test(c)) return c; } return 'rgb(255,255,255)'; };
              const res={}; for(const pal of %s) for(const mode of ['Light','Dark']){ S.palette=pal; S.theme=mode; applyTheme();
                for(const s of ['.hp-wn h2','.hp-wn h3','.hp-wn p','.hp-wn li','.hp-hero .hp-eyebrow','.hp-lede']){ const el=document.querySelector('#helpPane '+s); res[pal+'|'+mode+'|'+s]=el?ratio(getComputedStyle(el).color,bgOf(el)):-1; } }
              return {res, side:document.documentElement.scrollWidth<=innerWidth+1}; })()""" % TEST_PALETTES_JS)
            self.assertTrue(r["side"], width)
            self.assertEqual({k: v for k, v in r["res"].items() if v < 4.5}, {}, width)


if __name__ == "__main__":
    unittest.main()
