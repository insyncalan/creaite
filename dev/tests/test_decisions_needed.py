"""BL-210 (sprint-decisions-needed): Decisions needed, a band on Today, the same rows on a project page and in a steering Prep.

Run: python3 dev/tests/test_decisions_needed.py   (needs Google Chrome; skipped otherwise)

The clock is pinned (CREAITE_NOW for the live server and the build, pin_page_clock for the page) to test_decisions_dashboard's
Thursday, so "days waiting" and "days late" never depend on the real date. The data is that file's decisions plus one more
(Omar's, not yet late), an action ABC-D-006 blocks (in the UAT start milestone), and a steering meeting today.
"""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase, pin_page_clock  # noqa: E402
from test_decisions_dashboard import NOW, TODAY, d, dec, load  # noqa: E402
from test_tracker import ABC  # noqa: E402


def world(v):
    """test_decisions_dashboard's decisions (Sara's ABC-D-006, 3 days late; Alan's ABC-D-007, in 5 days; Omar's DEF one with
    no date), plus Omar's ABC decision due in 2 days with nothing linked, an action Sara's decision blocks, and a calendar."""
    load(v, TODAY)
    src = f"{ABC}/minutes/{d(-5)} Steering.docx — Decisions"
    v.propose("more", [dec(1, src, decision="Confirm the training dates", status="Pending", made_by="Omar Ali", needed_by=d(2)),
                       {"n": 2, "op": "new", "table": "actions", "match": "strong", "flags": [], "decision": "approved",
                        "values": {"project": "ABC", "description": "Book the pilot venue", "owner": "Alan Carter",
                                   "due_date": d(4), "milestone": "ABC-M-001", "source": src}}])
    v.run("apply")
    act = next(r["id"] for r in v.rows("actions") if r["description"] == "Book the pilot venue")
    v.propose("links", [{"n": 1, "op": "new", "table": "links", "match": "strong", "flags": [], "decision": "approved",
                         "values": {"from_item": "ABC-D-006", "to_item": act, "source": "Alan (cx-edit)"}}])
    v.run("apply")
    f = v.root / "system/staging/drafts/calendar.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"days": {TODAY.isoformat(): [
        {"id": "s1", "start": "14:00", "end": "15:00", "title": "ABC SteerCo"},
        {"id": "s2", "start": "16:00", "end": "16:30", "title": "ABC weekly sync"}]}}))
    env = {**os.environ, "CREAITE_NOW": NOW}
    subprocess.run([sys.executable, str(v.root / "system/scripts/sweep.py"), "calendar", str(f)], cwd=v.root, check=True, env=env,
                   capture_output=True)
    subprocess.run([sys.executable, str(v.root / "system/scripts/build_dashboard.py")], cwd=v.root, check=True, env=env,
                   capture_output=True)
    return act


class Base(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        cls.act = world(v)

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": NOW}

    def setUp(self):
        super().setUp()
        pin_page_clock(self.b, NOW)
        self.assertEqual(self.b.eval("TODAY"), TODAY.isoformat())

    def today(self):
        b = self.b
        b.eval("go('today'); renderToday();")
        b.wait("!document.getElementById('dnSec').hidden")
        return b

    def rows(self, sel="#dnList > li.dnrow"):
        return self.b.eval(f"[...document.querySelectorAll({json.dumps(sel)})].map(r=>[r.querySelector('a.t').dataset.open.split(':')[1],"
                           "r.textContent.replace(/\\s+/g,' ').trim(), [...r.querySelectorAll('.dnacts button')].map(x=>x.textContent.trim()||x.dataset.tip)])")   # BL-319: Today's are icons, read by their tooltip

    def staging(self):
        root = self.v.root / "system/staging"
        return sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() and "drafts" not in p.parts)

    def prep(self, title):
        b = self.today()
        b.wait("document.querySelector('#dayMeets .dm')")
        b.eval(f"openPrep(prepTimed().find(e=>e.title===({title!r})), TODAY)")
        b.wait("document.getElementById('prepDlg').open && document.getElementById('prepDecNeeded')")
        return b


class DecisionsNeeded(Base):
    shared_server = True            # nothing here changes the tracker or staging

    def test_the_data_says_since_when_and_what_it_blocks(self):
        got = {x["id"]: x for x in self.b.eval("DEC")}
        self.assertEqual((got["ABC-D-006"]["since"], got["ABC-D-006"]["slips"]), (d(-5), [self.act]))   # the minutes' date, earlier than the apply
        self.assertEqual(got["ABC-D-009"]["slips"], [])
        self.assertNotIn("since", got["ABC-D-008"])                                                     # made: not on the list

    def test_the_band_comes_first_yours_first_then_by_how_late_or_soon(self):
        b = self.today()
        order = b.eval("[...document.querySelectorAll('#tBrief > section')].map(s=>s.id||s.getAttribute('aria-labelledby'))")
        self.assertEqual(order.index("dnSec") + 1, order.index("attnSec"))                                # just ahead of Needs attention
        rows = self.rows()
        self.assertEqual([r[0] for r in rows], ["ABC-D-007", "ABC-D-006", "ABC-D-009"])                  # yours, late, soon; DEF's undated one left out
        self.assertEqual(b.eval("document.getElementById('nDn').textContent"), "3 decisions · 1 yours · 1 late")
        mine, sara, omar = rows
        self.assertIn("Yours", mine[1])
        self.assertEqual(mine[2], ["Record the decision", "Open"])                                      # BL-319: icons, named
        self.assertEqual((sara[2], omar[2]), (["Draft a chase", "Open"], ["Draft a chase", "Open"]))
        self.assertIn("from Sara Example", sara[1])
        self.assertIn("Example Programme", sara[1])                                                      # the project by name
        self.assertNotIn("ABC ·", sara[1])
        self.assertIn("waiting 5 days", sara[1])
        self.assertIn(f"needed by {d(-3)[8:10]}-{d(-3)[5:7]}-{d(-3)[:4]}, 3 days late", sara[1])
        self.assertIn(f"If it stays open: {self.act} Book the pilot venue", sara[1])
        self.assertIn("the UAT start milestone", sara[1])                                               # the milestone the action belongs to
        self.assertIn("needed by", omar[1])
        self.assertIn("in 2 days", omar[1])
        self.assertNotIn("If it stays open", omar[1])                                                   # no link: no consequence, not a guess
        self.assertEqual(b.errors, [])

    def test_with_nothing_waiting_the_band_is_hidden(self):
        b = self.today()
        b.eval("window.KEEP=DEC.map(d=>d.by); DEC.forEach(d=>{ d.by=''; }); renderToday();")
        try:
            self.assertTrue(b.eval("document.getElementById('dnSec').hidden"))
        finally:
            b.eval("DEC.forEach((d,i)=>{ d.by=KEEP[i]; }); renderToday();")

    def test_open_opens_the_decision(self):
        b = self.today()
        b.click('#dnList li.dnrow .dnacts [data-open="decisions:ABC-D-006"]')
        b.wait("CUR&&CUR.id==='ABC-D-006'")

    def test_chase_drafts_only_and_nothing_leaves_the_laptop(self):
        b = self.today()
        before = self.staging()
        b.eval("window.SENTURLS=[]; const f0=window.fetch; window.fetch=(u,...a)=>{ SENTURLS.push(String(u)); return f0(u,...a); };")
        b.click('#dnList [data-dnchase="ABC-D-006"]')                                                    # late: BL-224's chase mode
        b.wait("document.getElementById('deDlg')&&document.getElementById('deDlg').open")
        self.assertEqual(b.eval("[DE.mode, DE.name, DE.only]"), ["chase", "Sara Example", "ABC-D-006"])
        self.assertTrue(b.eval("[...DE.picked].every(k=>k==='decisions:ABC-D-006')"))                   # nothing else starts ticked
        self.assertTrue(b.eval("DE.items.some(i=>i.id==='ABC-D-006')"))
        self.assertIn("Nothing is sent", b.eval("document.querySelector('#deDlg .prephead').textContent"))
        self.assertNotIn("0 overdue", b.eval("document.getElementById('deSubj').value"))                # Sara is outside: nothing ticked yet
        b.eval("document.getElementById('deDlg').close()")
        b.click('#dnList [data-dnchase="ABC-D-009"]')                                                    # not yet late: the update request
        b.wait("document.getElementById('deDlg').open")
        self.assertEqual(b.eval("[DE.mode, DE.name, DE.only]"), ["update", "Omar Ali", "ABC-D-009"])
        self.assertTrue(b.eval("DE.items.length>1 && [...DE.picked].every(k=>k==='decisions:ABC-D-009')"))   # his other items offered, unticked
        b.eval("document.getElementById('deDlg').close()")
        self.assertEqual(b.eval("SENTURLS.filter(u=>!/\\/api\\/(pulse|health|events|version|diagnostics)/.test(u))"), [])   # no save, no chase record
        self.assertEqual(self.staging(), before)
        self.assertFalse((self.v.root / "system/staging/chases.json").exists())

    def test_the_project_page_uses_the_same_rows(self):
        b = self.b
        b.eval("go('cockpit','ABC')")
        b.wait("document.getElementById('decCard')")
        self.assertEqual([r[0] for r in self.rows("#decCard .dnlist > .dnrow")], ["ABC-D-007", "ABC-D-006", "ABC-D-009"])
        self.assertNotIn("Example Programme", self.rows("#decCard .dnlist > .dnrow")[1][1])           # its own page: no project
        b.eval("go('cockpit','DEF')")
        b.wait("document.getElementById('decCard')&&/Approve the pilot budget/.test(document.getElementById('decCard').textContent)")
        self.assertEqual(b.eval("document.querySelectorAll('#decCard .dnrow').length"), 0)              # undated: the plain line
        self.assertIn("no date needed by", b.eval("document.getElementById('decCard').textContent"))

    def test_a_steering_prep_lists_the_same_rows_and_another_meeting_does_not(self):
        b = self.prep("ABC SteerCo")
        rows = self.rows("#prepDecNeeded .dnrow")
        self.assertEqual([r[0] for r in rows], ["ABC-D-007", "ABC-D-006", "ABC-D-009"])
        self.assertIn("If it stays open", rows[1][1])
        b.eval("document.getElementById('prepDlg').close()")
        b = self.prep("ABC weekly sync")
        self.assertEqual(b.eval("document.querySelectorAll('#prepDecNeeded .dnrow').length"), 0)       # BL-113's lines, unchanged
        b.eval("document.getElementById('prepDlg').close()")


class Deciding(Base):
    """Decide stages Made in the peek, which saves a staged change: a fresh vault and server for each test."""

    def test_decide_opens_record_the_decision_with_made_staged(self):
        b = self.today()
        b.click('#dnList [data-dndecide="ABC-D-007"]')
        b.wait("CUR&&CUR.id==='ABC-D-007'&&document.getElementById('panel').classList.contains('on')")
        b.wait("PKS.some(s=>s.id==='ABC-D-007')")
        self.assertEqual(self.row_status("ABC-D-007"), "Pending")                                      # staged, not applied

    def test_decide_in_a_steering_prep_closes_the_prep_first(self):
        b = self.prep("ABC SteerCo")
        b.click('#prepDecNeeded [data-dndecide="ABC-D-007"]')
        b.wait("!document.getElementById('prepDlg').open && CUR && CUR.id==='ABC-D-007'")

    def row_status(self, id_):
        return next(r["status"] for r in self.v.rows("decisions") if r["id"] == id_)


if __name__ == "__main__":
    unittest.main()
