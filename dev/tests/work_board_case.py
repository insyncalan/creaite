"""The Work board tests' shared set-up: a vault with about 60 actions and 30 RAID items, and the helpers that read the page.

Not a test file. test_work_board.py (layout) and test_work_board_moves.py (drags) both build on it, so the two halves run side by side.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import work_data as W  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402

TODAY = date.today()


def iso(n):
    return (TODAY + timedelta(days=n)).isoformat()

def wd(n):
    """BL-181: n days on, moved to the next working day, so a test's date never raises the weekend alert."""
    d = date.today() + timedelta(days=n)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d.isoformat()



def week_sunday(day):
    return day + timedelta(days=6 - day.weekday())


def due_column(r, is_open):
    """Overdue, This week, Next week, Later, No date (or Closed) for a row: the oracle for the Due grouping."""
    if not is_open:
        return "Closed"
    if not r["due_date"]:
        return "No date"
    due = date.fromisoformat(r["due_date"])
    if due < TODAY:
        return "Overdue"
    sun = week_sunday(TODAY)
    return "This week" if due <= sun else "Next week" if due <= sun + timedelta(days=7) else "Later"

class BoardCase(LiveBrowserCase):
    """A vault with about 60 actions and 30 RAID items; every test gets a fresh server so moves can be written freely."""
    width, height = 1640, 1000      # BL-319: the 212px sidebar; the board keeps the 1428px it had beside the 72px rail

    @classmethod
    def load(cls, v):
        populate(v)
        W.load(v)

    # ── driving the page ──
    def open_board(self, tab="actions", group=None, view=None):
        b = self.b
        b.eval("go('work')")
        b.wait("document.querySelector('#workTbl tbody tr, #workTbl .empty, #workBoard .bcol, #workBoard .empty, #workBoard .bpick')")
        if tab != "actions":
            b.click(f'#wtabs button[data-t="{tab}"]')
            b.wait(f"WT==='{tab}'")
        if view:
            b.click(f'#wviews [data-wv="{view}"]')
        b.click('#wlay [data-lay="board"]')
        b.wait("!document.getElementById('workBoard').hidden && document.querySelector('#workBoard .bcol, #workBoard .empty, #workBoard .bpick')")
        if group:
            self.group(group)
        return b

    def group(self, name):
        self.b.eval(f"(()=>{{ const s=document.getElementById('wgrp'); s.value={name!r}; s.dispatchEvent(new Event('change',{{bubbles:true}})); }})()")
        self.b.wait(f"groupOf(WT)==={name!r}")

    def columns(self):
        """{column label: [card IDs]} in page order."""
        return self.b.eval("""Object.fromEntries([...document.querySelectorAll('#workBoard .bcol')].map(c=>[c.querySelector('h3').textContent.replace(/ · \\d+$/,''),
          [...c.querySelectorAll('.bcard')].map(k=>k.dataset.row)]))""")

    def headers(self):
        return self.b.eval("[...document.querySelectorAll('#workBoard .bcol h3')].map(h=>h.textContent)")

    def card_in(self, col, pred=None):
        cols = self.columns()
        return cols[col][0] if not pred else next(i for i in cols[col] if pred(i))

    def card_sel(self, id_):
        return f'#workBoard .bcard[data-row="{id_}"]'

    def col_sel(self, label):
        return f'#workBoard .bcol[data-col="{label}"]'

    def action(self, id_):
        return next(r for r in self.v.rows("actions") if r["id"] == id_)

    def raid(self, id_):
        return next(r for r in self.v.rows("raid") if r["id"] == id_)

    def wait_saved(self, moved=None):
        """The snackbar says the move was — saved (and, with `moved`, that it is about this move: an earlier message may still be up)."""
        self.b.wait(f"/— saved/.test(document.getElementById('snackT').textContent) && document.getElementById('snackT').textContent.includes({(moved or '')!r})", 15)

    def dialog_open(self):
        return self.b.eval("document.getElementById('boardDlg').open")


def W_initials(name):
    if not name or name == "TBC":
        return "?"
    parts = name.split()
    return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()
