"""BL-150, as changed by BL-173 (sprint-polish-2): ask creaite opens over the page. With the chat open at 1400px and 1100px the
main area keeps its width and its first row its position (nothing reflows, and the Work filter bar doesn't fold for it); a
dragged chat width doesn't move the page. BL-176 (sprint-peek): an item opens in the peek, over the page too: the page never
makes room for it, it keeps clear of the chat, and the chat opening and closing leaves it as it was. Below 1100px the chat is a
layer, as before.
A real browser against the real live server.

Run: python3 dev/tests/test_panel_room.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

GEOM = """(()=>{ const r=s=>{ const e=document.querySelector(s); if(!e) return null; const b=e.getBoundingClientRect(); return [Math.round(b.left),Math.round(b.top),Math.round(b.width),Math.round(b.height)]; };
  return JSON.stringify({content:r('.content'), shell:r('.shell'), row:r('#workTbl tbody tr[data-row]')||r('#v-'+VIEW+' .tbl'), panel:r('#panel'),
    folds:document.querySelectorAll('#wfilters .wfold').length}); })()"""
SEEN = """(()=>{ const s=document.getElementById('pkMore'), r=s.getBoundingClientRect(), c=$('#chat').getBoundingClientRect();
  const hit=document.elementFromPoint(r.left+r.width/2, r.top+r.height/2); return r.right<=c.left+1 && !!hit && s.contains(hit); })()"""   # BL-176: the peek's last toolbar button, not under the chat


class PanelRoom(LiveBrowserCase):
    shared_server = True

    def geom(self):
        return json.loads(self.b.eval(GEOM))

    def settle(self, s=0.4):
        self.b.pump(s)

    def reset(self, width):
        b = self.b
        b.resize(width, 900)
        b.eval("closeChat(); if(CUR){ EDITING=false; closePanel(true); } setChatWidth(420,false)")
        self.settle(0.3)

    # ===== BL-173 (sprint-polish-2) =====
    def test_the_chat_alone_moves_nothing_at_1400_and_1100(self):
        for width in (1400, 1100):
            for view in ("work", "inbox", "review"):
                self.reset(width)
                self.b.eval(f"go({view!r})")
                self.settle()
                closed = self.geom()
                self.b.eval("openChat()")
                self.settle()
                opened = self.geom()
                self.assertEqual((opened["content"], opened["row"], opened["shell"]), (closed["content"], closed["row"], closed["shell"]), (view, width))
                self.assertEqual(opened["folds"], closed["folds"], (view, width))                  # the filter bar doesn't fold for it
                self.assertAlmostEqual(self.b.eval("$('#chat').getBoundingClientRect().left"), self.b.eval("document.documentElement.clientWidth") - 420, delta=2)   # clientWidth: Linux draws a scrollbar
                self.assertNotEqual(self.b.eval("getComputedStyle($('#chat')).boxShadow"), "none")  # a layer, with its shadow
        self.reset(1400)

    def test_a_dragged_width_moves_only_the_chat(self):
        self.reset(1400)
        self.b.eval("go('work')")
        self.settle()
        closed = self.geom()
        self.b.eval("openChat(); setChatWidth(640,false)")
        self.settle()
        self.assertAlmostEqual(self.b.eval("$('#chat').getBoundingClientRect().left"), self.b.eval("document.documentElement.clientWidth") - 640, delta=2)
        self.assertEqual(self.geom()["content"], closed["content"])
        self.reset(1400)

    # ===== BL-176 (sprint-peek) ===== the item panel is now the peek: over the page, never making room (it replaced the BL-80 and
    # BL-150 behaviour that BL-173 kept for the item panel)
    def test_with_the_peek_open_the_page_is_as_with_nothing_open(self):
        """At 1400, 1100 and 1000, with the chat closed and open: the page's area, shell, first row and folded filters are what they
        are with no item open; the peek is at least 520px wide; beside the chat it ends at the chat's left edge where there is room,
        and where there isn't (1000px), its content keeps clear of the chat and its toolbar's last button still takes a click."""
        b = self.b
        for width in (1400, 1100, 1000):
            for chat in (False, True):
                self.reset(width)
                b.eval("go('work')" + ("; openChat()" if chat else ""))
                self.settle(0.5)
                base = self.geom()
                b.eval("openRecord('actions',A[0].id)")
                self.settle(0.8)
                now = self.geom()
                self.assertEqual((now["content"], now["shell"], now["row"][:2], now["folds"]), (base["content"], base["shell"], base["row"][:2], base["folds"]), (width, chat))
                self.assertAlmostEqual(now["row"][2], base["row"][2], delta=1, msg=(width, chat))  # the open row's own mark may round a pixel
                self.assertGreaterEqual(now["panel"][2], 520, (width, chat))
                if chat:
                    edge = b.eval("$('#chat').getBoundingClientRect().left")
                    if width >= 1100:
                        self.assertLessEqual(now["panel"][0] + now["panel"][2], edge + 1, width)
                    self.assertLessEqual(b.eval("$('#pkTitle').getBoundingClientRect().right"), edge + 1, (width, "content"))
                    self.assertTrue(b.eval(SEEN), (width, chat))
                else:
                    self.assertAlmostEqual(now["panel"][0] + now["panel"][2], b.eval("document.documentElement.clientWidth"), delta=2)
        self.reset(1400)

    def test_opening_the_chat_beside_an_open_peek_and_closing_it_again(self):
        b = self.b
        self.reset(1100)
        b.eval("go('work'); openRecord('actions',A[0].id)")
        self.settle(0.8)
        alone = self.geom()
        b.eval("openChat()")
        self.settle(0.6)
        self.assertTrue(b.eval(SEEN))
        self.assertTrue(b.eval("$('#panel').classList.contains('on')"))                    # the chat opening leaves it open
        b.eval("closeChat()")
        self.settle(0.6)
        self.assertEqual(self.geom(), alone)                                                # and closing it leaves it as it was
        self.reset(1400)
    # ===== end BL-176 =====

    def test_below_1100_it_stays_a_layer(self):
        b = self.b
        b.resize(1000, 900)
        b.eval("go('work'); openChat()")
        b.pump(0.3)
        self.assertAlmostEqual(b.eval("document.querySelector('.shell').getBoundingClientRect().right"), 1000, delta=2)
        b.eval("closeChat()")
        b.resize(1400, 900)

    def test_the_work_filter_bar_folds_for_a_narrow_window_not_the_chat_or_the_peek(self):
        b = self.b
        self.reset(1400)
        b.eval("go('work')")
        b.pump(0.4)
        self.assertEqual(b.eval("document.querySelectorAll('#wfilters .wfold').length"), 0)      # room for all: nothing folded
        b.eval("openChat()")
        b.pump(0.4)
        self.assertEqual(b.eval("document.querySelectorAll('#wfilters .wfold').length"), 0)      # BL-173: the chat alone folds nothing
        self.assertTrue(b.eval("""(()=>{ const bar=$('#v-work .toolbar'), t=bar.firstElementChild.offsetTop;
          return [...bar.children].filter(c=>c.offsetParent&&c.offsetHeight>8).every(c=>c.offsetTop<=t+8); })()"""))   # still one row
        b.eval("openRecord('actions',A[0].id)")                                                 # BL-176: nor does the peek, over the page
        b.pump(0.6)
        self.assertEqual(b.eval("document.querySelectorAll('#wfilters .wfold').length"), 0)
        b.resize(900, 900)                                                                       # a narrow window still folds, as before
        b.eval("closePanel(); wfFit()")
        b.pump(0.6)
        self.assertGreater(b.eval("document.querySelectorAll('#wfilters .wfold').length"), 0)
        self.assertTrue(b.eval("!document.querySelector('#wfilters .dd.wfold .fbtn.on')"))      # a set filter never folds
        b.eval("$('#moreBtn').click()")
        b.pump(0.3)
        self.assertIn("Priority", b.eval("$('#moreMenu').textContent"))                           # it is in the funnel
        self.reset(1400)


if __name__ == "__main__":
    unittest.main()
