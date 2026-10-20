"""#256: the Work page reads the browser's saved layout (creaite-cols, creaite-colorder, creaite-colwidths, creaite-worklay and the
rest of that family) tolerantly. A tab missing from the saved value, a null, a wrong type, an unknown column or an empty list falls
back to that tab's default, with no error, and what is saved is never rewritten by loading (an update never resets saved layout).

Run: python3 dev/tests/test_work_saved_cols_tolerant.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import work_data as W  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402

DEFAULT = {"actions": ["t", "o", "due", "pr", "st"], "raid": ["t", "o", "due", "pr", "resp"],
           "decisions": ["t", "st", "by", "due", "date", "src"]}
TABS = ("actions", "raid", "decisions")
FAMILY = ["creaite-cols", "creaite-colorder", "creaite-colwidths", "creaite-worklay", "creaite-workgrp", "creaite-boardhide",
          "creaite-boardcoll", "creaite-listgrp", "creaite-worksub", "creaite-listcoll", "creaite-boardclosedall", "creaite-boardw"]

# each fixture: the raw strings saved under the keys, and the columns each tab is expected to show
FIXTURES = {
    "one tab only": ({"creaite-cols": '{"actions":["t","o","due"]}'},
                     {"actions": ["t", "o", "due"], "raid": DEFAULT["raid"], "decisions": DEFAULT["decisions"]}),
    "null, wrong type and empty": ({"creaite-cols": '{"actions":[],"raid":null,"decisions":"oops"}',
                                    "creaite-colorder": '{"actions":5,"raid":"o,t","decisions":null}'}, DEFAULT),
    "unknown columns": ({"creaite-cols": '{"actions":["zz","qq"],"raid":["t","nope","o"],"decisions":[7,null]}',
                         "creaite-colorder": '{"raid":["nope","o","t"]}'},
                        {"actions": DEFAULT["actions"], "raid": ["o", "t"], "decisions": DEFAULT["decisions"]}),
    "every key malformed": ({"creaite-cols": "null", "creaite-colorder": "null", "creaite-colwidths": "null",
                             "creaite-worklay": "null", "creaite-workgrp": "[1,2]", "creaite-boardhide": '"x"',
                             "creaite-boardcoll": "null", "creaite-listgrp": "7", "creaite-worksub": "null",
                             "creaite-listcoll": "null", "creaite-boardclosedall": '{"a":1}', "creaite-boardw": "null"},
                            DEFAULT),
    "a list where a map belongs": ({"creaite-cols": '["t","o"]', "creaite-colorder": '[["t"]]',
                                    "creaite-colwidths": '{"actions|t":"wide","actions|o":null}',
                                    "creaite-boardclosedall": "5"}, DEFAULT),
}


class SavedColsTolerant(LiveBrowserCase):
    width, height = 1500, 1000

    @classmethod
    def load(cls, v):
        populate(v)
        W.load(v)

    def boot_with(self, saved):
        b = self.b
        b.eval("localStorage.clear(); " + "".join(f"localStorage.setItem({k!r},{s!r});" for k, s in saved.items()))
        del b.errors[:]
        b.reload("typeof go==='function' && LIVE")
        return b

    def stored(self):
        return self.b.eval("(()=>{ const o={}; " + json.dumps(FAMILY) + ".forEach(k=>{ const v=localStorage.getItem(k); if(v!==null) o[k]=v; }); return o; })()")

    def shown(self, tab):
        b = self.b
        if tab != "actions":
            b.click(f'#wtabs button[data-t="{tab}"]')
        b.wait(f"WT==='{tab}' && document.querySelector('#workTbl thead th')")
        return b.eval("[...document.querySelectorAll('#workTbl thead th')].map(th=>th.dataset.col)")

    def walk(self, name, saved, want):
        b = self.boot_with(saved)
        b.eval("go('work')")
        b.wait("document.querySelector('#workTbl tbody tr, #workTbl .empty')")
        for tab in TABS:
            self.assertEqual(self.shown(tab), want[tab], f"{name}: {tab} columns")
            b.eval("openDisp()")
            b.wait("document.getElementById('dispMenu').classList.contains('on')")
            ticked = b.eval("[...document.querySelectorAll('#dispMenu [data-prop]:checked')].map(i=>i.value)")
            self.assertEqual(ticked, want[tab], f"{name}: {tab} Display properties")
            b.eval("closeDisp(false)")
        b.eval("go('people')")
        b.wait("document.querySelector('#v-people h1')")
        if b.eval("!!document.querySelector('#peopleTbl a[data-person]')"):
            b.eval("document.querySelector('#peopleTbl a[data-person]').click()")
            b.pump(0.5)
        b.eval("go('today')")
        b.pump(0.5)
        self.assertEqual(b.errors, [], f"{name}: no page errors")
        self.assertEqual(self.stored(), saved, f"{name}: what is saved is unchanged")

    def test_each_malformed_saved_layout_loads_every_tab(self):
        for name, (saved, want) in FIXTURES.items():
            with self.subTest(name):
                self.walk(name, saved, want)

    def test_a_change_on_a_missing_tab_saves_that_tab_alone(self):
        b = self.boot_with({"creaite-cols": '{"actions":["t","o","due"]}'})
        b.eval("go('work')")
        b.wait("document.querySelector('#workTbl tbody tr, #workTbl .empty')")
        self.shown("raid")
        b.eval("openDisp()")
        b.wait("document.getElementById('dispMenu').classList.contains('on')")
        b.click("#dispMenu #dprop-ws")
        b.wait("[...document.querySelectorAll('#workTbl thead th')].some(th=>th.dataset.col==='ws')")
        saved = json.loads(b.eval("localStorage.getItem('creaite-cols')"))
        self.assertEqual(saved["actions"], ["t", "o", "due"])            # the saved tab exactly as it was
        self.assertEqual(saved["raid"], DEFAULT["raid"] + ["ws"])       # the changed tab: its default plus the tick
        self.assertNotIn("decisions", saved)                            # an untouched missing tab is not written
        self.assertEqual(b.errors, [])


if __name__ == "__main__":
    unittest.main()
