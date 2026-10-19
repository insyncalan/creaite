"""#241 E: no update may undo anyone's Work layout. A browser holding every saved Work key (the list's column widths, order and
visibility, the layout, the board and list groupings, the sub-groups, hidden empty columns, collapsed board columns and list
groups, the Closed column's window) and saved views in settings loads the new build over that old localStorage, reloads, and
every key comes back exactly as it was; the page shows what they say. A list column resized by drag, by the keyboard
separator and put back by double-click keeps its width, order and visibility across a reload, and a collapsed board column
stays collapsed. A real browser against the real live server.

Run: python3 dev/tests/test_work_layout_survives.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import work_data as W  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402

READY = "typeof go==='function' && LIVE"

# every Work key a browser can hold today, each with a value a person could have chosen
FIXTURE = {
    "creaite-colwidths": {"actions|o": 220, "actions|due": 150, "raid|o": 180},
    "creaite-colorder": {"actions": ["t", "due", "o", "pr", "st", "ws"]},
    "creaite-cols": {"actions": ["t", "o", "due", "pr", "st", "ws"], "raid": ["t", "o", "due", "pr", "resp"],
                     "decisions": ["t", "st", "by", "due", "date", "src"]},
    "creaite-worklay": {"actions": "list", "raid": "board", "decisions": "list"},
    "creaite-workgrp": {"actions": "status", "raid": "owner"},
    "creaite-listgrp": {"actions": "none", "decisions": "owner"},
    "creaite-worksub": {"decisions|list": "project", "raid|board": "none"},
    "creaite-boardhide": {"actions": True},
    "creaite-boardcoll": {"raid|owner|TBC": True},
    "creaite-boardclosedall": ["raid"],
    "creaite-listcoll": {"decisions|owner|@me": True},
    "creaite-boardw": {"raid|owner": {"@me": 320}},
}
SAVED_VIEWS = {"actions": [{"name": "My layout", "f": {"st": ["Open"]}, "lay": "list", "g": "due", "o": {"col": "due", "dir": "asc"},
                            "lg": "none", "sg": "none", "lsg": "none"}]}
KEYS_JS = json.dumps(sorted(FIXTURE))


class LayoutSurvives(LiveBrowserCase):
    width, height = 1500, 1000

    @classmethod
    def load(cls, v):
        populate(v)
        W.load(v)
        f = v.root / "system/config/settings.json"
        cfg = json.loads(f.read_text(encoding="utf-8"))
        cfg.setdefault("work", {})["saved_views"] = SAVED_VIEWS
        f.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
        v.run("build_dashboard.py", script="build_dashboard.py")

    def setUp(self):
        super().setUp()
        self.b.eval("localStorage.clear()")

    # ── helpers ──
    def put_fixture(self):
        b = self.b
        for k, val in FIXTURE.items():
            b.eval(f"localStorage.setItem({k!r}, {json.dumps(json.dumps(val))})")
        b.reload(READY)

    def stored(self):
        """Every Work key as stored, parsed (None when missing), plus any creaite- key that wasn't in the fixture."""
        return self.b.eval(f"""(()=>{{ const out={{}}; {KEYS_JS}.forEach(k=>{{ const v=localStorage.getItem(k); out[k]=v===null?null:JSON.parse(v); }}); return out; }})()""")

    def extra_keys(self):
        return self.b.eval(f"Object.keys(localStorage).filter(k=>/^creaite-(col|work|board|list)/.test(k)&&!{KEYS_JS}.includes(k))")

    def tab(self, t):
        b = self.b
        if b.eval("WT") != t:
            b.click(f'#wtabs button[data-t="{t}"]')
            b.wait(f"WT==='{t}'")
        b.wait("document.querySelector('#workTbl tbody tr, #workTbl .empty, #workBoard .bcol, #workBoard .empty')")

    def heads(self):
        return self.b.eval("[...document.querySelectorAll('#workTbl thead th[data-col]')].map(t=>t.dataset.col)")

    def th_width(self, col):
        return round(self.b.eval(f"document.querySelector('#workTbl thead th[data-col=\"{col}\"]').getBoundingClientRect().width"))

    def visit_everything(self):
        """Open every tab in the layout it has, as a person would after an update, and check the page shows the saved layout."""
        b = self.b
        b.eval("go('work')")
        self.tab("actions")
        self.assertEqual(b.eval("layoutOf('actions')"), "list")
        self.assertEqual(self.heads(), ["t", "due", "o", "pr", "st", "ws"])          # order and visibility
        self.assertEqual(self.th_width("o"), 220)                                    # widths
        self.assertEqual(self.th_width("due"), 150)
        self.assertEqual(b.eval("document.querySelectorAll('#workTbl tr.wgh').length"), 0)   # "no grouping" stays a choice
        self.tab("raid")
        self.assertEqual(b.eval("layoutOf('raid')"), "board")
        self.assertEqual(b.eval("groupOf('raid')"), "owner")
        self.assertTrue(b.eval("document.querySelector('#workBoard .bcol[data-col=\"TBC\"]').classList.contains('collapsed')"))
        self.assertEqual(round(b.eval("document.querySelector('#workBoard .bcol[data-col=\"@me\"]').getBoundingClientRect().width")), 320)
        self.assertTrue(b.eval("BCLALL.has('raid')"))
        self.tab("decisions")
        self.assertEqual(b.eval("listGroupOf('decisions')"), "owner")
        self.assertEqual(b.eval("subOf('decisions','list')"), "project")
        self.assertTrue(b.eval("document.querySelector('#workTbl tr.wgh[data-gk=\"decisions|owner|@me\"]').classList.contains('coll')"))
        self.tab("actions")
        b.click('#wviews [data-wv="saved:My layout"]')
        b.wait("WVIEW==='saved:My layout'")
        self.assertEqual(b.eval("listGroupOf('actions')"), "none")

    def saved_views(self):
        return json.loads((self.v.root / "system/config/settings.json").read_text())["work"]["saved_views"]

    # ── tests ──
    def test_every_saved_key_survives_the_new_build_and_a_reload(self):
        self.put_fixture()
        self.assertEqual(self.stored(), FIXTURE)
        self.visit_everything()
        self.assertEqual(self.stored(), FIXTURE)                                     # loading the new build rewrote nothing
        self.b.reload(READY)
        self.visit_everything()
        self.b.reload(READY)
        self.assertEqual(self.stored(), FIXTURE)                                     # and a reload after it neither
        self.assertEqual(self.extra_keys(), [])                                       # nothing added unasked
        self.assertEqual(self.saved_views(), SAVED_VIEWS)

    def test_a_list_column_resize_survives_a_reload_with_its_order_and_visibility(self):
        b = self.b
        self.put_fixture()
        b.eval("go('work')")
        self.tab("actions")
        rz = '#workTbl thead th[data-col="pr"] .colrz'
        w0 = self.th_width("pr")
        pos = b.box(rz)
        for kind, x in (("mouseMoved", pos["x"]), ("mousePressed", pos["x"]), ("mouseMoved", pos["x"] + 30), ("mouseMoved", pos["x"] + 60),
                        ("mouseReleased", pos["x"] + 60)):
            b.call("Input.dispatchMouseEvent", type=kind, x=x, y=pos["y"], button="left", clickCount=1)
        b.pump(0.2)
        self.assertEqual(self.th_width("pr"), w0 + 60)
        b.eval(f"document.querySelector({rz!r}).focus()")
        b.key("ArrowRight")                                                            # the keyboard separator: 16 px a step
        b.pump(0.1)
        self.assertEqual(self.th_width("pr"), w0 + 76)
        self.assertEqual(b.eval("JSON.parse(localStorage.getItem('creaite-colwidths'))['actions|pr']"), w0 + 76)
        b.reload(READY)
        b.eval("go('work')")
        self.tab("actions")
        self.assertEqual(self.th_width("pr"), w0 + 76)                                # the width,
        self.assertEqual(self.heads(), ["t", "due", "o", "pr", "st", "ws"])          # the order and the visibility survive
        self.assertEqual(self.th_width("o"), 220)                                    # and the other widths are untouched
        b.eval(f"document.querySelector({rz!r}).dispatchEvent(new MouseEvent('dblclick',{{bubbles:true}}))")
        b.pump(0.1)
        self.assertNotIn("actions|pr", b.eval("JSON.parse(localStorage.getItem('creaite-colwidths'))"))
        b.reload(READY)
        b.eval("go('work')")
        self.tab("actions")
        self.assertEqual(self.th_width("pr"), w0)                                     # put back, and stays put back
        self.assertEqual(self.th_width("o"), 220)

    def test_a_board_column_collapse_survives_a_reload(self):
        b = self.b
        self.put_fixture()
        b.eval("go('work')")
        self.tab("raid")
        b.click('#workBoard .bcol[data-col="@me"] [data-bcoll]')
        b.wait("document.querySelector('#workBoard .bcol[data-col=\"@me\"]').classList.contains('collapsed')")
        b.reload(READY)
        b.eval("go('work')")
        self.tab("raid")
        self.assertTrue(b.eval("document.querySelector('#workBoard .bcol[data-col=\"@me\"]').classList.contains('collapsed')"))
        self.assertTrue(b.eval("document.querySelector('#workBoard .bcol[data-col=\"TBC\"]').classList.contains('collapsed')"))
        self.assertEqual(b.eval("JSON.parse(localStorage.getItem('creaite-boardcoll'))"), {"raid|owner|TBC": True, "raid|owner|@me": True})


if __name__ == "__main__":
    unittest.main()
