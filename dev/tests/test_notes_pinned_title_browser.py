"""#222: a pinned note's card in the Notes list shows its title (not a blank), a long title ends in an ellipsis, also when confidential.

Run: python3 dev/tests/test_notes_pinned_title_browser.py   (needs Google Chrome; skipped otherwise), at 1400 px and 900 px.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_notes_tab_browser import NotesTab  # noqa: E402

LONG = "Alpha pinned " + "stakeholder alignment " * 6 + "end"
CLONG = "Bravo pinned " + "stakeholder alignment " * 6 + "end"


class NotesPinnedTitleBrowser(LiveBrowserCase):
    width, height = 1400, 1000
    notes_dir, make, type_end = NotesTab.notes_dir, NotesTab.make, NotesTab.type_end

    def made(self, title):
        b = self.b
        self.make(title)
        b.eval("noteFlush()")
        b.wait("noteSave.value.state==='saved'", 15)

    def flag(self, title, how):
        """Pin / mark confidential from the row's own menu."""
        b = self.b
        b.eval("document.querySelectorAll('.nlist .ni').forEach(x=>x.dataset.nt=x.querySelector('b').textContent.replace('\\u25c6 ',''))")
        b.click(f"[data-nt={json.dumps(title)}]", button="right")
        b.wait("!!document.querySelector('.pophost [role=menu]')", 10)
        b.eval(f"[...document.querySelectorAll('.pophost [role=menuitem]')].find(x=>x.textContent.startsWith({json.dumps(how)})).click()")
        key = "pinned" if how == "Pin" else "confidential"
        b.wait(f"notesList.value.find(n=>n.title==={json.dumps(title)}).{key}===true", 15)

    def card(self, title):
        return self.b.eval("""(()=>{const li=[...document.querySelectorAll('.nlist .ni')].find(x=>x.querySelector('b').textContent.includes(%s));
          const b=li.querySelector('b'), r=document.createRange(); r.selectNodeContents(b); const bb=b.getBoundingClientRect(), c=li.getBoundingClientRect();
          return {pin:!!li.querySelector('.pin,.npin'), pw:(li.querySelector('.pin,.npin')||{getBoundingClientRect(){return{width:0}}}).getBoundingClientRect().width, vis:r.getBoundingClientRect().left<bb.right-20, bw:bb.width, text:b.textContent, ell:getComputedStyle(b).textOverflow, ov:b.scrollWidth>b.clientWidth,
                  inside:bb.right<=c.right+0.5&&bb.left>=c.left-0.5, tw:r.getBoundingClientRect().width, small:li.querySelector('small').textContent}})()""" % json.dumps(title[:12]))

    def test_pinned_titles(self):
        self.made("Plain")
        self.made("Pinny")
        self.made("Secret")
        self.made(LONG)
        self.made(CLONG)
        self.flag("Pinny", "Pin")
        self.flag("Secret", "Pin")
        self.flag("Secret", "Mark confidential")
        self.flag(LONG, "Pin")
        self.flag(CLONG, "Pin")
        self.flag(CLONG, "Mark confidential")
        p = self.card("Plain")
        self.assertFalse(p["pin"])
        self.assertIn("Plain", p["text"])
        for t in ("Pinny", "Secret"):
            c = self.card(t)
            self.assertTrue(c["pin"], t)
            self.assertIn(t, c["text"])
            self.assertGreater(c["bw"], 20, (t, c))
            self.assertGreater(c["tw"], 20, (t, c))
            self.assertLess(c["pw"], 30, (t, c))                                             # the pin mark is a mark, not a 420 px panel (#222)
            self.assertTrue(c["vis"], (t, c))                                                # and the title starts inside the card
        self.assertIn("Confidential", self.card("Secret")["small"])
        for t in (LONG, CLONG):
            c = self.card(t)
            self.assertTrue(c["pin"])
            self.assertLess(c["pw"], 30, c)
            self.assertTrue(c["vis"], c)
            self.assertEqual(c["ell"], "ellipsis")
            self.assertTrue(c["ov"], c)
            self.assertTrue(c["inside"], c)
            self.assertGreater(c["bw"], 60, c)


class NotesPinnedTitleBrowser900(NotesPinnedTitleBrowser):
    width, height = 900, 900


if __name__ == "__main__":
    unittest.main()
