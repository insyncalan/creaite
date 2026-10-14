"""BL-129: group by in the List (collapsible headers, counts, a sub-group) and swimlanes on the Board, with the selection rules
(BL-122, BL-124) that grouping changes. A real browser against the real live server; counts are checked against Python.

Run: python3 dev/tests/test_work_grouping.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_decisions_board as DB  # noqa: E402
from test_work_board import BoardCase  # noqa: E402

TODAY = date.today().isoformat()
META = 4
SHIFT = 8
PNAME = {"ABC": "Example Programme", "DEF": "Digital Enablement"}


class ListGroups(BoardCase):
    shared_server = True

    def setUp(self):
        super().setUp()
        self.b.eval("localStorage.clear()")
        self.b.reload("typeof go==='function' && LIVE")

    def open_list(self, tab="actions", group="none", sub="none", view="open"):
        b = self.b
        b.eval("go('work')")
        b.wait("document.querySelector('#workTbl tbody tr')")
        if b.eval("WT") != tab:
            b.click(f'#wtabs button[data-t="{tab}"]')
            b.wait(f"WT==='{tab}'")
        if view:
            b.click(f'#wviews [data-wv="{view}"]')
        b.click('#wlay [data-lay="list"]')
        for sel, val in (("#wgrp", group), ("#wsub", sub)):
            b.eval(f"(()=>{{ const s=document.querySelector({sel!r}); s.value={val!r}; s.dispatchEvent(new Event('change',{{bubbles:true}})); }})()")
        b.pump(0.2)
        return b

    def heads(self, lvl=1):
        return self.b.eval(f"[...document.querySelectorAll('#workTbl tr.wgh.lv{lvl}')].map(r=>[r.querySelector('.wgn').textContent, r.querySelector('.sub').textContent])")

    def open_rows(self, tab):
        rows = self.v.rows(tab)
        if tab == "actions":
            return [r for r in rows if r["status"] == "Open"]                     # All open is Open only (Alan, 11-10-2026)
        if tab == "raid":
            return [r for r in rows if r["status"] == "Open"]
        return rows

    def late(self, tab, r):
        return r["status"] in (("Open", "Delayed") if tab == "actions" else ("Open",)) and bool(r["due_date"]) and r["due_date"] < TODAY

    def test_each_grouping_on_each_tab_has_the_right_counts(self):
        for tab, view, keys in (("actions", "open", ["project", "status", "priority", "owner", "due", "workstream", "milestone"]),
                                ("raid", "open", ["project", "status", "priority", "type", "owner", "due", "milestone"]),
                                ("decisions", "all", ["project", "status", "owner", "due"])):
            for g in keys:
                b = self.open_list(tab, g, view=view)
                heads = self.heads()
                self.assertTrue(heads, (tab, g))
                total = sum(int(sub.split(" ")[0]) for _, sub in heads)
                self.assertEqual(total, b.eval("rows().length"), (tab, g))              # every row is in exactly one group
                self.assertEqual(b.eval("document.querySelectorAll('#workTbl tr[data-row]').length"), total)
                if g in ("project", "priority", "status") and tab != "decisions":
                    field = {"project": "project", "priority": "priority", "status": "status"}[g]
                    rows = self.open_rows(tab)
                    if tab == "raid" and g == "priority":
                        continue                                                       # worked out from impact and likelihood
                    want = Counter((PNAME[r[field]] if g == "project" else r[field]) for r in rows)
                    got = {name: int(sub.split(" ")[0]) for name, sub in heads}
                    self.assertEqual(got, {k: v for k, v in want.items() if v} | {k: 0 for k in got if k not in want}, (tab, g))
                    if g == "project":                                                # the overdue count
                        for name, sub in heads:
                            late = sum(1 for r in rows if PNAME[r["project"]] == name and self.late(tab, r))
                            self.assertEqual(f"{late} overdue" in sub, bool(late), (tab, name, sub))
                            if late:
                                self.assertIn(f"{late} overdue", sub)
        # the order: Owner puts Me first and TBC last; Priority by rank
        b = self.open_list("actions", "owner")
        names = [h[0] for h in self.heads()]
        self.assertEqual((names[0], names[-1]), ("Me", "TBC"))
        b = self.open_list("actions", "priority")
        self.assertEqual([h[0] for h in self.heads()], ["Urgent", "High", "Medium", "Low"])

    def test_collapse_is_remembered_and_the_address_keeps_the_grouping(self):
        b = self.open_list("actions", "priority")
        b.click('#workTbl tr.wgh[data-gk="actions|priority|High"] .wgtog')
        b.wait("document.querySelector('#workTbl tr.wgh[data-gk=\"actions|priority|High\"]').classList.contains('coll')")
        self.assertFalse(b.eval("[...document.querySelectorAll('#workTbl tr[data-row]')].some(r=>A.find(a=>a.id===r.dataset.row).pr==='High')"))
        self.assertIn("&lg=priority", b.eval("location.hash"))
        b.reload("typeof go==='function' && LIVE")
        b.wait("document.querySelector('#workTbl tr.wgh')")
        self.assertTrue(b.eval("document.querySelector('#workTbl tr.wgh[data-gk=\"actions|priority|High\"]').classList.contains('coll')"))
        b.click('#workTbl tr.wgh[data-gk="actions|priority|High"] .wgtog')               # Enter on the button does the same (a button)
        b.wait("!document.querySelector('#workTbl tr.wgh[data-gk=\"actions|priority|High\"]').classList.contains('coll')")

    def test_a_shift_range_never_reaches_a_collapsed_group(self):
        b = self.open_list("actions", "priority")
        b.click('#workTbl tr.wgh[data-gk="actions|priority|High"] .wgtog')
        b.pump(0.2)
        urgent = b.eval("[...document.querySelectorAll('#workTbl tr[data-row][data-g1=\"actions|priority|Urgent\"]')].map(r=>r.dataset.row)")
        medium = b.eval("[...document.querySelectorAll('#workTbl tr[data-row][data-g1=\"actions|priority|Medium\"]')].map(r=>r.dataset.row)")
        b.click(f'#workTbl tr[data-row="{urgent[-1]}"] td.title')
        b.click(f'#workTbl tr[data-row="{medium[0]}"] td.title', modifiers=SHIFT)
        hl = b.eval("[...HL.keys()]")
        self.assertEqual(sorted(hl), sorted([urgent[-1], medium[0]]))
        self.assertFalse(b.eval("[...HL.keys()].some(id=>A.find(a=>a.id===id).pr==='High')"))
        # J and K step over the headers, onto rows only
        b.key("j")
        self.assertIn(b.eval("HLC"), medium)

    def test_collapsing_a_group_takes_its_rows_out_and_says_so(self):
        b = self.open_list("actions", "priority")
        urgent = b.eval("[...document.querySelectorAll('#workTbl tr[data-row][data-g1=\"actions|priority|Urgent\"]')].map(r=>r.dataset.row)")
        high = b.eval("[...document.querySelectorAll('#workTbl tr[data-row][data-g1=\"actions|priority|High\"]')].map(r=>r.dataset.row)")
        b.click(f'#workTbl tr[data-row="{urgent[0]}"] td.title')
        b.click(f'#workTbl tr[data-row="{high[0]}"] td.title', modifiers=META)
        b.click(f'#workTbl tr[data-row="{high[1]}"] td.title', modifiers=META)
        b.click('#workTbl tr.wgh[data-gk="actions|priority|High"] .wgtog')
        b.pump(0.3)
        self.assertEqual(b.eval("[...HL.keys()]"), [urgent[0]])
        self.assertIn("2 selected items left the selection", b.eval("document.getElementById('snackT').textContent"))

    def test_the_header_tick_and_select_all_matching(self):
        b = self.open_list("actions", "priority")
        b.click('#workTbl tr.wgh[data-gk="actions|priority|Urgent"] .wgtick')
        urgent = b.eval("[...document.querySelectorAll('#workTbl tr[data-row][data-g1=\"actions|priority|Urgent\"]')].map(r=>r.dataset.row)")
        self.assertEqual(sorted(b.eval("[...HL.keys()]")), sorted(urgent))
        self.assertTrue(b.eval("document.querySelector('#workTbl tr.wgh[data-gk=\"actions|priority|Urgent\"] .wgtick').checked"))
        b.click('#workTbl tr.wgh[data-gk="actions|priority|Low"] .wgtog')                  # collapse Low
        b.pump(0.2)
        total = b.eval("rows().length")
        low = b.eval("rows().filter(x=>x.pr==='Low').length")
        self.assertIn(f"Select all {total} matching", b.eval("document.getElementById('wbulk').textContent"))
        b.click("#wbulk [data-bq=all]")
        b.pump(0.2)
        self.assertEqual(b.eval("HL.size"), total, b.eval("[document.getElementById('wbulk').textContent, HLALL]"))
        self.assertIn(f"{total} selected ({low} in collapsed groups)", b.eval("document.querySelector('#wbulk .bkn').textContent"))
        b.click('#workTbl tr.wgh[data-gk="actions|priority|Medium"] .wgtog')               # still all: the explicit exception holds
        b.pump(0.2)
        self.assertEqual(b.eval("HL.size"), total)

    def test_a_sub_group_on_the_list(self):
        b = self.open_list("actions", "project", "priority")
        self.assertEqual([h[0] for h in self.heads()], ["Digital Enablement", "Example Programme"])
        subs = self.heads(2)
        self.assertTrue(subs)
        self.assertEqual(sum(int(s.split(" ")[0]) for _, s in subs), b.eval("rows().length"))
        self.assertIn("&sg=priority", b.eval("location.hash"))
        self.assertFalse(b.eval("[...document.querySelectorAll('#wsub option')].some(o=>o.value==='project')"))   # never the group itself

    def test_filters_search_and_saved_views_still_apply(self):
        b = self.open_list("actions", "owner")
        b.eval("(()=>{ const q=document.getElementById('workQ'); q.value='alpha'; q.dispatchEvent(new Event('input',{bubbles:true})); })()")
        b.pump(0.2)
        shown = b.eval("[...document.querySelectorAll('#workTbl tr[data-row]')].map(r=>r.dataset.row)")
        self.assertTrue(shown)
        self.assertTrue(b.eval("[...document.querySelectorAll('#workTbl tr[data-row]')].every(r=>/alpha/.test(A.find(a=>a.id===r.dataset.row).t))"))
        b.eval("(async()=>{ await saveView('By owner'); })()")
        b.wait("SAVED.actions.some(v=>v.name==='By owner')")
        self.assertEqual(b.eval("SAVED.actions.find(v=>v.name==='By owner').lg"), "owner")
        b.eval("(()=>{ const s=document.getElementById('wgrp'); s.value='none'; s.dispatchEvent(new Event('change',{bubbles:true})); })()")
        b.wait("!document.querySelector('#workTbl tr.wgh')")
        b.click('#wviews [data-wv="saved:By owner"]')
        b.wait("document.querySelector('#workTbl tr.wgh')")


class Swimlanes(BoardCase):
    width, height = 1500, 1800                     # a swimlane board is tall: room for a drag between lanes
    def setUp(self):
        super().setUp()
        self.b.eval("localStorage.clear()")
        self.b.reload("typeof go==='function' && LIVE")

    def sub(self, name):
        self.b.eval(f"(()=>{{ const s=document.getElementById('wsub'); s.value={name!r}; s.dispatchEvent(new Event('change',{{bubbles:true}})); }})()")
        self.b.wait("document.querySelector('#workBoard .blane')")

    def lanes(self):
        return self.b.eval("[...document.querySelectorAll('#workBoard .blane')].map(l=>l.dataset.lane)")

    def test_lanes_counts_and_collapse(self):
        b = self.open_board("actions", "due", view="open")
        self.sub("owner")
        lanes = self.lanes()
        self.assertEqual((lanes[0], lanes[-1]), ("@me", "TBC"))
        n = b.eval("[...document.querySelectorAll('#workBoard .blane > header h3')].reduce((a,h)=>a+ +h.textContent.split(' · ').pop(),0)")
        self.assertEqual(n, b.eval("rows().length"))
        self.assertIn("&sg=owner", b.eval("location.hash"))
        b.click('#workBoard .blane[data-lane="@me"] .bcoll')
        b.wait("document.querySelector('#workBoard .blane[data-lane=\"@me\"]').classList.contains('collapsed')")
        self.assertFalse(b.eval("!!document.querySelector('#workBoard .blane[data-lane=\"@me\"] .bcard')"))

    def test_a_cross_lane_and_column_move_states_both_and_saves_once(self):
        b = self.open_board("actions", "status", view="open")
        b.eval("(()=>{ const q=document.getElementById('workQ'); q.value='alpha'; q.dispatchEvent(new Event('input',{bubbles:true})); })()")   # a short board, all on screen
        self.sub("owner")
        card = b.eval("document.querySelector('#workBoard .blane[data-lane=\"@me\"] .bcol[data-col=Open] .bcard').dataset.row")
        files = len(list((self.v.root / "system/staging/applied").glob("*.json")))
        lanes = self.lanes()
        target = lanes[1]
        b.drag(self.card_sel(card), f'#workBoard .blane[data-lane="{target}"] .bcol[data-col="Delayed"] .bch')
        b.wait("document.getElementById('boardDlg').open")
        hint = b.eval("document.getElementById('bdHint').textContent")
        self.assertIn("Status → Delayed", hint)
        self.assertIn(f"owner → {target}", hint)
        b.click("#bdOk")
        self.wait_saved()
        row = self.action(card)
        self.assertEqual((row["status"], row["owner"]), ("Delayed", target))
        self.assertEqual(len(list((self.v.root / "system/staging/applied").glob("*.json"))), files + 1)     # one proposal
        b.click("#snackU")                                                                  # one Undo restores both
        b.wait("/Undone/.test(document.getElementById('snackT').textContent)", 15)
        row = self.action(card)
        self.assertEqual(row["status"], "Open")
        self.assertNotEqual(row["owner"], target)

    def test_move_to_offers_the_lane_as_a_second_step(self):
        b = self.open_board("actions", "due", view="open")
        self.sub("owner")
        card = b.eval("document.querySelector('#workBoard .blane[data-lane=\"@me\"] .bcard').dataset.row")
        b.click(self.card_sel(card) + " .bmv")
        b.wait("document.getElementById('bmenu')")
        lanes = b.eval("[...document.querySelectorAll('#bmenu [data-blto]')].map(x=>x.dataset.blto)")
        self.assertEqual(set(lanes), set(self.lanes()) - {"@me"})                           # every other lane, by keyboard too
        self.assertTrue(b.eval("document.getElementById('bmenu').contains(document.activeElement)"))
        b.click('#bmenu [data-blto="TBC"]')
        self.wait_saved()
        self.assertEqual(self.action(card)["owner"], "TBC")
        self.assertIn(card, b.eval("[...document.querySelectorAll('#workBoard .blane[data-lane=\"TBC\"] .bcard')].map(c=>c.dataset.row)"))

    def test_raid_lanes_by_project_refuse_a_project_change(self):
        b = self.open_board("raid", "owner", view="open")
        self.sub("project")
        card = b.eval("document.querySelector('#workBoard .blane[data-lane=\"ABC\"] .bcard').dataset.row")
        before = self.raid(card)
        b.eval(f"laneDrop({card!r}, boardKeyOf('raid','owner',R.find(x=>x.id==={card!r})), 'DEF')")
        b.pump(0.3)
        self.assertIn("project can't be changed", b.eval("document.getElementById('snackT').textContent"))
        self.assertEqual(self.raid(card), before)


class DecisionLanes(DB.BoardCase):
    width, height = 1500, 1800
    def test_a_lane_move_reassigns_who_is_asked_and_made_opens_the_peek(self):
        b = self.open_board("status")
        b.eval("(()=>{ const s=document.getElementById('wsub'); s.value='owner'; s.dispatchEvent(new Event('change',{bubbles:true})); })()")
        b.wait("document.querySelector('#workBoard .blane')")
        b.drag(self.card("ABC-D-007"), '#workBoard .blane[data-lane="Omar Ali"] .bcol[data-col="Pending"] .bch')
        self.wait_saved("ABC-D-007 moved to Omar Ali")
        self.assertEqual(self.row("ABC-D-007")["made_by"], "Omar Ali")
        b.drag(self.card("ABC-D-006"), '#workBoard .blane[data-lane="Omar Ali"] .bcol[data-col="Made"] .bch')     # column and lane
        # BL-176: Made opens the decision in the peek with Made and the lane's person staged
        b.wait("CUR && CUR.id==='ABC-D-006' && document.getElementById('panel').classList.contains('peek') && PKS.length===2", 15)
        self.assertEqual(b.eval("PKS[0].patch.st"), "Made")
        self.assertEqual(b.eval("curObj().st"), "Made")
        self.assertEqual(b.eval("PKS[1].patch.by"), "Omar Ali")
        self.assertEqual(b.eval("curObj().by"), "Omar Ali")
        self.assertEqual(self.row("ABC-D-006")["status"], "Pending")                       # nothing written until Apply


if __name__ == "__main__":
    unittest.main(verbosity=2)
