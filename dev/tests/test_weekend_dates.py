"""BL-181 (sprint-peek-new): a weekend date on a work item always raises an alert, with the nearest working days offered.
The engine's note (tracker.weekend, propose.py's preview, review.py's list, the early warning) and, in a real browser, the
peek's date chips and typed box, the table's date cell, the bulk bar, the Board's prompt, Review and the calendars.

Run: python3 dev/tests/test_weekend_dates.py   (the browser part needs Google Chrome; skipped otherwise)
"""
import json
import subprocess
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
import tracker  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402
from test_tracker import Vault  # noqa: E402
from test_dashboard import populate  # noqa: E402

META = 4


def next_weekday(n):
    """The first date at least a week after today that is weekday n (Monday 0). A week out, so neither the date nor the
    Friday before it nor the Monday after it is ever a date populate() already gave ABC-A-002 (d(3)): on a Tuesday the
    Friday before the next Saturday was its due date, so choosing it changed nothing and saved nothing."""
    d = date.today() + timedelta(days=7)
    while d.weekday() != n:
        d += timedelta(days=1)
    return d


SAT, SUN, WED = next_weekday(5), next_weekday(6), next_weekday(2)
FRI_BEFORE = lambda d: d - timedelta(days=(d.weekday() - 4))          # noqa: E731  (the Friday before a Saturday or Sunday)
MON_AFTER = lambda d: d + timedelta(days=(7 - d.weekday()))           # noqa: E731
shown = lambda d: d.strftime("%d-%m-%Y")                               # noqa: E731


class EngineNote(unittest.TestCase):
    def test_saturday_and_sunday_are_noted_a_weekday_is_not(self):
        self.assertEqual(tracker.weekend("actions", {"due_date": SAT.isoformat()}, settings={}), [f"due on a Saturday ({shown(SAT)})"])
        self.assertEqual(tracker.weekend("raid", {"due_date": SUN.isoformat()}, settings={}), [f"due on a Sunday ({shown(SUN)})"])
        self.assertEqual(tracker.weekend("actions", {"due_date": WED.isoformat()}, settings={}), [])
        self.assertEqual(tracker.weekend("decisions", {"needed_by": SAT.isoformat()}, settings={}), [f"needed on a Saturday ({shown(SAT)})"])

    def test_dates_that_record_what_happened_and_milestones_are_never_noted(self):
        for v in ({"raised": SAT.isoformat()}, {"closed": SAT.isoformat()}, {"date": SAT.isoformat()}):
            self.assertEqual(tracker.weekend("actions", v, settings={}) + tracker.weekend("decisions", v, settings={}), [])
        self.assertEqual(tracker.weekend("milestones", {"forecast_date": SAT.isoformat()}, settings={}), [])

    def test_the_setting_changes_the_days(self):
        s = {"work": {"weekend_days": ["Friday", "Saturday"]}}
        fri = next_weekday(4)
        self.assertEqual(tracker.weekend("actions", {"due_date": fri.isoformat()}, settings=s), [f"due on a Friday ({shown(fri)})"])
        self.assertEqual(tracker.weekend("actions", {"due_date": SUN.isoformat()}, settings=s), [])

    def test_propose_prints_it_and_review_lists_it_and_neither_refuses(self):
        v = Vault()
        try:
            populate(v)
            spec = v.root / "system/staging/drafts/wk.json"
            spec.parent.mkdir(parents=True, exist_ok=True)
            spec.write_text(json.dumps({"source_run": "cx-edit", "items": [{"op": "new", "table": "actions", "values": {
                "project": "ABC", "description": "Weekend thing", "owner": "Alan Carter", "due_date": SAT.isoformat(), "raised": date.today().isoformat(),
                "status": "Open", "source": "Alan (cx-edit)"}}]}))
            out = v.run("stage", str(spec), script="propose.py").stdout
            self.assertIn(f"Note: due on a Saturday ({shown(SAT)}); a working day is usually meant", out)
            self.assertIn("Staged and approved", out)                                       # a note, never a refusal
            v.propose("wk-review", [{"n": 1, "op": "new", "table": "actions", "match": "strong", "flags": [], "decision": "pending",
                                     "values": {"project": "ABC", "description": "Review weekend", "owner": "Alan Carter",
                                                "due_date": SUN.isoformat(), "raised": date.today().isoformat(), "status": "Open",
                                                "source": "Alan (cx-edit)"}}])
            listed = v.run("list", script="review.py").stdout
            self.assertIn(f"due on a Sunday ({shown(SUN)})", listed)
            n = next(ln.split(" · ")[0].strip() for ln in listed.splitlines() if "Review weekend" in ln)
            v.run("approve", n, script="review.py")
            v.run("apply")
            self.assertTrue(any(r["description"] == "Review weekend" and r["due_date"] == SUN.isoformat() for r in v.rows("actions")))
        finally:
            v.cleanup()


class WeekendInThePage(LiveBrowserCase):
    width, height = 1500, 1000

    @classmethod
    def load(cls, v):
        populate(v)
        v.propose("wk", [{"n": 1, "op": "new", "table": "actions", "match": "strong", "flags": [], "decision": "approved",
                          "values": {"project": "ABC", "description": "Due on a Saturday", "owner": "Alan Carter",
                                     "due_date": SAT.isoformat(), "source": "Alan (cx-edit)"}}])
        v.run("apply")
        v.propose("wk-pending", [{"n": 1, "op": "new", "table": "actions", "match": "strong", "flags": [], "decision": "pending",
                                  "values": {"project": "ABC", "description": "Proposed for a Sunday", "owner": "Alan Carter",
                                             "due_date": SUN.isoformat(), "source": "Alan (cx-edit)"}}])
        v.run(script="build_dashboard.py")

    def staged(self):
        return sorted(p for p in (self.v.root / "system/staging").glob("proposed-*-dashboard*.json"))

    def ask(self):
        return self.b.eval("WK.ask?WK.ask.box.textContent:''")

    def work(self):
        b = self.b
        b.eval("WT='actions'; go('work')")
        b.eval("HTMLSelectElement.prototype.showPicker=function(){}")
        b.wait("document.querySelector('#workTbl tr[data-row]')")
        b.click('#wlay [data-lay="list"]')
        b.eval("setOf('st').clear(); workChanged(); document.activeElement&&document.activeElement.blur()")
        b.pump(0.3)

    def peek_due(self, id_="ABC-A-002"):
        b = self.b
        self.work()
        b.eval(f"openRecord('actions',{id_!r})")
        b.wait(f"CUR&&CUR.id==={id_!r}")
        b.click('#pkProps [data-pkp="due"]')
        b.wait("document.querySelector('.pkpop .pkday')")

    def test_the_peek_marks_weekends_and_a_saturday_or_sunday_asks_with_friday_and_monday(self):
        b = self.b
        self.peek_due()
        sat_btn = f'.pkpop .pkday[data-d="{SAT.isoformat()}"]'
        if not b.eval(f"!!document.querySelector('{sat_btn}')"):
            b.click('.pkpop [data-m="1"]')
        self.assertTrue(b.eval(f"document.querySelector('{sat_btn}').classList.contains('wkend')"))
        self.assertTrue(b.eval(f"document.querySelector('{sat_btn}').getAttribute('aria-label').endsWith(', weekend')"))
        b.click(sat_btn)
        b.wait("!!WK.ask")
        self.assertIn(f"Saturday {shown(SAT)} is a weekend.", self.ask())
        self.assertIn(f"Friday {shown(FRI_BEFORE(SAT))}", self.ask())
        self.assertIn(f"Monday {shown(MON_AFTER(SAT))}", self.ask())
        self.assertEqual(b.eval("WK.ask.box.getAttribute('role')"), "status")
        self.assertEqual(self.staged(), [])                                                 # nothing saved before the choice
        b.click(f'[data-wkd="{FRI_BEFORE(SAT).isoformat()}"]')
        b.wait("PKS.length===1")
        self.assertEqual(b.eval("REC('actions','ABC-A-002').due"), FRI_BEFORE(SAT).isoformat())
        # Sunday, typed, then Keep this date: the weekend date is saved
        b.click('#pkProps [data-pkp="due"]')
        b.wait("document.querySelector('.pkpop .pkdt')")
        b.eval("document.querySelector('.pkpop .pkdt').focus(); document.querySelector('.pkpop .pkdt').select()")
        b.type(shown(SUN))
        b.wait("(document.querySelector('.pkpop .wkline')||{}).textContent")                 # said as it is typed
        self.assertIn("is a weekend", b.eval("document.querySelector('.pkpop .wkline').textContent"))
        b.key("Enter")
        b.wait("!!WK.ask")
        b.click('[data-wkd="keep"]')
        b.wait("PKS.length===2")
        self.assertEqual(b.eval("REC('actions','ABC-A-002').due"), SUN.isoformat())
        # a weekday raises nothing
        b.click('#pkProps [data-pkp="due"]')
        b.wait("document.querySelector('.pkpop .pkdt')")
        b.eval("document.querySelector('.pkpop .pkdt').focus(); document.querySelector('.pkpop .pkdt').select()")
        b.type(shown(WED))
        b.key("Enter")
        b.wait("PKS.length===3")
        self.assertEqual(self.ask(), "")
        self.assertEqual(b.errors, [])

    def test_monday_from_the_alert_and_a_new_item_too(self):
        b = self.b
        self.work()
        b.eval("PROJF.clear(); PROJF.add('ABC'); renderWork(); openNew('actions')")
        b.wait("CUR&&CUR.mode==='new'")
        b.eval(f"itemDatePicker(document.querySelector('#pkProps [data-pkp=\"due\"]'),{{value:'',due:true,label:'Due date',onPick:v=>pkCommit('actions',CUR.nid,{{due:v}},'Due date','','')}})")
        b.eval("document.querySelector('.pkpop .pkdt').focus()")
        b.type(shown(SAT))
        b.key("Enter")
        b.wait("!!WK.ask")
        b.click(f'[data-wkd="{MON_AFTER(SAT).isoformat()}"]')
        b.wait(f"CUR.draft.due==={MON_AFTER(SAT).isoformat()!r}")

    def test_the_made_date_never_alerts(self):
        b = self.b
        self.work()
        made = b.eval("DEC.find(d=>d.st==='Made').id")
        b.eval(f"openRecord('decisions',{made!r})")
        b.click('#pkProps [data-pkp="date"]')
        b.wait("document.querySelector('.pkpop .pkdt')")
        b.eval("document.querySelector('.pkpop .pkdt').focus(); document.querySelector('.pkpop .pkdt').select()")
        b.type(shown(SAT - timedelta(days=7)))
        b.key("Enter")
        b.wait("PKS.length===1")
        self.assertEqual(self.ask(), "")

    def test_the_date_cell_the_bulk_bar_and_the_board_prompt(self):
        b = self.b
        self.work()
        # the table's date cell
        b.click('#workTbl tr[data-row="ABC-A-002"] td[data-f="due"]')
        b.wait("document.getElementById('ceDate')")
        b.eval(f"document.getElementById('ceDate').value={shown(SAT)!r}")
        b.key("Enter")
        b.wait("!!WK.ask")
        self.assertIn("is a weekend", self.ask())
        b.eval("document.getElementById('snackT').textContent=''")
        b.click(f'[data-wkd="{MON_AFTER(SAT).isoformat()}"]')
        b.wait("document.getElementById('snackT').textContent!==''", 30)
        b.wait(f"REC('actions','ABC-A-002').due==={MON_AFTER(SAT).isoformat()!r}", 15)
        # the bulk bar
        b.pump(0.5)
        b.click('#workTbl tr[data-row="ABC-A-001"] td:last-child')
        b.click('#workTbl tr[data-row="ABC-A-002"] td:last-child', modifiers=META)
        b.wait("document.getElementById('bkDate')")
        b.eval(f"document.getElementById('bkDate').focus(); document.getElementById('bkDate').value={shown(SUN)!r}")
        b.key("Enter")
        b.wait("!!WK.ask")
        b.eval("document.getElementById('snackT').textContent=''")
        b.click('[data-wkd="keep"]')
        b.wait("document.getElementById('snackT').textContent!==''", 30)
        b.wait(f"REC('actions','ABC-A-001').due==={SUN.isoformat()!r}&&REC('actions','ABC-A-002').due==={SUN.isoformat()!r}", 15)
        # the Board's date prompt (inline in the dialog)
        b.eval("hlClear&&hlClear()")
        b.eval("window.__r=null; boardAsk({title:'Due date',date:TODAY}).then(v=>window.__r=v); 0")
        b.wait("document.getElementById('boardDlg').open")
        b.eval(f"document.getElementById('bdDate').value={shown(SAT)!r}")
        b.click("#bdOk")
        b.wait("!!WK.ask&&document.getElementById('boardDlg').contains(WK.ask.box)")
        b.click(f'#boardDlg [data-wkd="{FRI_BEFORE(SAT).isoformat()}"]')
        b.wait(f"window.__r==={FRI_BEFORE(SAT).isoformat()!r}")

    def test_review_notes_it_and_the_buttons_edit_the_proposal(self):
        b = self.b
        b.eval("go('intake-review')")                                             # #232 C2: the Intake page's row carries the note
        b.wait("document.querySelector('#v-intake-review [data-wkrv]')")
        self.assertIn("Due on a Sunday", b.eval("document.querySelector('#v-intake-review .wkrv').textContent"))
        b.click(f'#v-intake-review [data-wkrv][data-to="{MON_AFTER(SUN - timedelta(days=1)).isoformat()}"]')
        f = self.v.root / "system/staging/proposed-wk-pending.json"
        b.wait(f"REV.some(r=>r.rec&&r.rec.due==={MON_AFTER(SUN - timedelta(days=1)).isoformat()!r})")
        self.assertEqual(json.loads(f.read_text())["items"][0]["values"]["due_date"], MON_AFTER(SUN - timedelta(days=1)).isoformat())

    def test_the_early_warning_lists_it_and_can_be_switched_off(self):
        b = self.b
        rid = b.eval("A.find(a=>a.t==='Due on a Saturday').id")
        self.assertTrue(b.eval(f"warnsOf('actions',{rid!r}).some(w=>w.sig==='weekend')"))
        b.eval(f"WT='actions'; go('work'); openRecord('actions',{rid!r})")
        b.wait("document.querySelector('#pkWarn [data-wkwto]')")
        self.assertIn("a working day is usually meant", b.eval("document.getElementById('pkWarn').textContent"))
        self.assertTrue(b.eval("WSIG.some(s=>s[0]==='weekend')"))                          # listed with the others in Settings
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text())
        data.setdefault("warnings", {})["weekend"] = {"on": False}
        cfg.write_text(json.dumps(data))
        subprocess.run([sys.executable, str(self.v.root / "system/scripts/build_dashboard.py")], capture_output=True)
        b.reload()
        b.wait("typeof go==='function'")
        self.assertFalse(b.eval(f"WARNS().some(w=>w.sig==='weekend')"))

    def test_the_old_calendar_marks_weekends(self):
        b = self.b
        self.work()
        b.click('#workTbl tr[data-row="ABC-A-002"] td[data-f="due"]')
        b.wait("document.getElementById('ceDate')")
        b.click("#v-work td.editing .dbtn")
        b.wait("document.querySelector('.cal .cg button[data-v]')")
        marked = b.eval("[...document.querySelectorAll('.cal .cg button.wkend')].map(x=>new Date(x.dataset.v.split('-').reverse().join('-')+'T12:00:00').getDay())")
        self.assertTrue(marked)
        self.assertTrue(all(d in (0, 6) for d in marked))


if __name__ == "__main__":
    unittest.main()
