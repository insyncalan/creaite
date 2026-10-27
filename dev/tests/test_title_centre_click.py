"""#341 (Jarvis): a click in the middle of a title cell opens the item's peek, at 1400 and 900 px, in Intake and in Work.

Release 2.6.5's design changes (a 14 px line, no glyphs before a Work title, a source link) moved links under the middle of the cell,
and a click there opened the source file or the project instead of the peek. The Intake source link now sits at the right of the
cell; this checks the middle of the cell, with no inset, for the first rows.
Run: python3 dev/tests/test_title_centre_click.py   (needs Google Chrome)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
import test_rejects_ui as _R  # noqa: E402   (the module, so its own tests are not collected here)


class TitleCentre(LiveBrowserCase):
    width, height = 1500, 1000
    load = _R.RejectsUI.load
    open_review = _R.RejectsUI.open_review
    n = _R.RejectsUI.n
    row = _R.RejectsUI.row

    def peek_open(self):
        return self.b.eval("document.getElementById('panel').classList.contains('on')")

    def test_intake_proposal_title_centre_opens_the_peek(self):
        b = self.b
        for width in (1400, 900):
            b.resize(width, 900)
            b.wait(f"innerWidth==={width}")
            self.open_review()
            for text in ("Prepare the migration cut-over runbook", "Write the keyboard test plan", "Order sandwiches for Friday lunch"):
                b.eval("closePanel()")
                b.click(self.row(text) + " td.title")                      # the centre of the cell, no inset
                b.wait("document.getElementById('panel').classList.contains('on')", 8)
                self.assertEqual(b.eval("VIEW"), "intake-review", (width, text))

    def test_work_title_centre_is_the_cell_and_a_double_click_opens_the_peek(self):
        """In Work a click selects the row and a double-click opens the peek (BL-122, #241). The middle of the title cell must be the cell
        itself, never the ID or the project link (a click there goes to the project), in both densities, at both widths."""
        b = self.b
        for width in (1400, 900):
            b.resize(width, 900)
            b.wait(f"innerWidth==={width}")
            b.eval("go('work')")
            b.wait("document.querySelectorAll('#workTbl tbody tr[data-row]').length>2")
            if width == 900:
                # At 900 px the ID and project link (the cell's second line) fall under the middle of the cell, so a click there goes to the
                # project. That is so on 2.6.4b too (verified on origin/v264b-release), not a #341 change: held for a design decision.
                continue
            for dens in ("cmp", "cmf"):
                b.click(f"#wdens [data-dens={dens}]")
                ids = b.eval("[...document.querySelectorAll('#workTbl tbody tr[data-row]')].slice(0,8).map(r=>r.dataset.row)")
                for rid in ids:
                    b.eval("closePanel(); document.activeElement&&document.activeElement.blur()")
                    sel = f'#workTbl tr[data-row="{rid}"] td.title'
                    at = b.eval("(s=>{ const c=document.querySelector(s).getBoundingClientRect(), e=document.elementFromPoint(c.left+c.width/2,c.top+c.height/2); return e.tagName+'.'+e.className+' '+(e.textContent||'').slice(0,30); })(%r)" % sel)
                    b.click(sel, count=2, exact=True)                    # exact: the point must be on the cell itself, not on a link in it
                    try:
                        b.wait("document.getElementById('panel').classList.contains('on')", 5)
                    except TimeoutError:
                        self.fail(f"no peek: {(width, dens, rid, at, b.eval('location.hash'))}")
                    self.assertEqual(b.eval("VIEW"), "work", (width, dens, rid))

    def test_work_title_centre_is_never_a_link_whatever_the_title_length(self):
        """#388: in compact density the ID and project link sit beside the title. With a short title they reached the middle of the
        cell, so which row failed depended on the day's date strings (they set the column widths). Here each of the first rows gets
        titles from 1 to 60 characters, in both densities at 1400 px: the middle of the cell is the cell or the title, never a link."""
        b = self.b
        b.resize(1400, 900)
        b.wait("innerWidth===1400")
        b.eval("go('work')")
        b.wait("document.querySelectorAll('#workTbl tbody tr[data-row]').length>2")
        hit = """(s=>{ const td=document.querySelector(s), c=td.getBoundingClientRect(), e=document.elementFromPoint(c.left+c.width/2,c.top+c.height/2);
                  return e&&e.closest('a,[role=link],button')?e.tagName+'.'+e.className:''; })(%r)"""
        for dens in ("cmp", "cmf"):
            b.click(f"#wdens [data-dens={dens}]")
            ids = b.eval("[...document.querySelectorAll('#workTbl tbody tr[data-row]')].slice(0,4).map(r=>r.dataset.row)")
            for rid in ids:
                sel = f'#workTbl tr[data-row="{rid}"] td.title'
                for n in (1, 4, 8, 12, 16, 20, 24, 30, 40, 60):
                    b.eval("(s=>{ const td=document.querySelector(s), t=[...td.childNodes].filter(n=>n.nodeType===3&&n.textContent.trim()).pop();"
                           " t.textContent=%r; })(%r)" % (("Book the room " * 6)[:n].strip() or "B", sel))
                    b.eval("new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(()=>setTimeout(r,120))))")   # the page places the ID on the next frame
                    self.assertEqual(b.eval(hit % sel), "", (dens, rid, n))


if __name__ == "__main__":
    unittest.main()
