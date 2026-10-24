"""BL-134: Work's All items tab, in a real browser against the real live server.

Run: python3 dev/tests/test_work_all_items.py   (needs Google Chrome; skipped otherwise)

The merged read model (one row per action, RAID item and decision, with the shared fields, the three status buckets and the
default order) is checked against an oracle written in Python from the database the server reads.
"""
import sqlite3
import sys
import unittest
from contextlib import closing
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import work_data as W  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402
from test_decisions_dashboard import load as load_decisions  # noqa: E402

TODAY = date.today().isoformat()
TYPES = ["Action", "Decision", "Risk", "Issue", "Assumption", "Dependency"]
BUCKET = {"Open": "Open", "Delayed": "Open", "Pending": "Open", "Closed": "Closed", "Made": "Closed",
          "Cancelled": "Cancelled", "Withdrawn": "Cancelled"}


def load(v):
    """test_decisions_dashboard's data (pending, made, a revisit), the larger Work set, and one withdrawn decision."""
    load_decisions(v)
    W.load(v)
    with closing(sqlite3.connect(v.root / "system/tracker.db")) as con:
        con.execute("UPDATE decisions SET status='Withdrawn', date=NULL WHERE id=(SELECT id FROM decisions WHERE decision='Decision number 05')")
        con.commit()
    # BL-327: the server's first page is the last built dashboard.html while the records' version (change_log, applies) is
    # unchanged, and a direct edit doesn't move it; build the page again so it shows the edit
    v.run("build_dashboard.py", script="build_dashboard.py")


def expected(v):
    """{id: (k, type, owner, due, bucket, own status)} from the database."""
    out = {}
    for r in v.rows("actions"):
        out[r["id"]] = ("actions", "Action", r["owner"], r["due_date"], BUCKET[r["status"]], r["status"])
    for r in v.rows("raid"):
        out[r["id"]] = ("raid", r["type"], r["owner"], r["due_date"], BUCKET[r["status"]], r["status"])
    for r in v.rows("decisions"):
        due = r["date"] if r["status"] == "Made" else r["needed_by"]
        out[r["id"]] = ("decisions", "Decision", r["made_by"] or "", due or None, BUCKET[r["status"]], r["status"])
    return out


class AllItemsCase(LiveBrowserCase):
    width, height = 1500, 1000
    shared_server = True

    @classmethod
    def load(cls, v):
        load(v)

    def setUp(self):
        super().setUp()
        self.b.eval("localStorage.clear()")


class ReadModel(AllItemsCase):
    def page_rows(self):
        return self.b.eval("allRows().map(r=>[r.id,r.k,r.type,r.o,r.due||null,r.st,r.nst,r.pr])")

    def test_every_item_once_with_the_shared_fields(self):
        rows = self.page_rows()
        ids = [r[0] for r in rows]
        self.assertEqual(len(ids), len(set(ids)))                                      # IDs are unique across the three tables
        exp = expected(self.v)
        self.assertEqual(sorted(ids), sorted(exp))
        for id_, k, typ, owner, due, st, nst, pr in rows:
            self.assertEqual((k, typ, owner, due, st, nst), exp[id_], id_)
            self.assertIn(typ, TYPES)
            if k == "decisions":
                self.assertEqual(pr, "")                                                 # a decision has no priority
            else:
                self.assertIn(pr, ["Urgent", "High", "Medium", "Low"])
        self.assertEqual({r[1] for r in rows}, {"actions", "raid", "decisions"})
        self.assertEqual(set(TYPES), {r[2] for r in rows})

    def test_a_decisions_owner_and_due(self):
        dec = {r["id"]: r for r in self.v.rows("decisions")}
        rows = {r[0]: r for r in self.page_rows() if r[1] == "decisions"}
        pending = [i for i, r in dec.items() if r["status"] == "Pending" and r["needed_by"]]
        made = [i for i, r in dec.items() if r["status"] == "Made"]
        self.assertTrue(pending and made)
        for i in pending:                                                                # owner: who is asked; due: needed by
            self.assertEqual((rows[i][3], rows[i][4]), (dec[i]["made_by"], dec[i]["needed_by"]))
        for i in made:                                                                   # a made decision: its date
            self.assertEqual((rows[i][3], rows[i][4]), (dec[i]["made_by"] or "", dec[i]["date"]))

    def test_the_status_buckets(self):
        b = self.b
        b.eval("WT='all'; clearAllFilters(); WQ=''")
        exp = expected(self.v)
        for bucket in ("Open", "Closed", "Cancelled"):
            got = sorted(b.eval(f"(applyFilters({{st:['{bucket}']}}), items().filter(x=>passes(x)).map(x=>x.id))"))
            self.assertEqual(got, sorted(i for i, e in exp.items() if e[4] == bucket), bucket)
        self.assertEqual(b.eval("FDEFS.all.find(d=>d[0]==='st')[2]().map(o=>o[0])"), ["Open", "Closed", "Cancelled"])
        counts = b.eval("(clearAllFilters(), ['Open','Closed','Cancelled'].map(v=>countFor('st',v)))")
        self.assertEqual(counts, [sum(1 for e in exp.values() if e[4] == v) for v in ("Open", "Closed", "Cancelled")])
        natives = {e[5] for e in exp.values() if e[4] == "Open"}                        # each bucket holds its native words
        self.assertTrue({"Open", "Delayed", "Pending"} <= natives)
        self.assertIn("Withdrawn", {e[5] for e in exp.values() if e[4] == "Cancelled"})
        self.assertIn("Made", {e[5] for e in exp.values() if e[4] == "Closed"})
        self.assertEqual(sorted(b.eval("FDEFS.all.map(d=>d[0])")), sorted(["st", "due", "o", "p", "pr", "ty", "sl", "lu", "rd", "mi"]))   # #251: Milestone
        b.eval("WT='actions'")

    def test_the_default_order(self):
        order = self.b.eval("rows('all',allRows().slice(),null,DEFSORT.all).map(r=>[r.id,r.st,r.due||''])")
        late = [r for r in order if r[1] == "Open" and r[2] and r[2] < TODAY]
        self.assertTrue(late)
        self.assertEqual(order[:len(late)], late)                                        # overdue first
        rest = order[len(late):]
        dated = [r for r in rest if r[2]]
        self.assertEqual(rest[:len(dated)], dated)                                       # then by date, undated last
        self.assertEqual([r[2] for r in dated], sorted(r[2] for r in dated))
        self.assertTrue(all(not r[2] for r in rest[len(dated):]))
        late_dates = [r[2] for r in late]
        self.assertEqual(late_dates, sorted(late_dates))


class Tab(AllItemsCase):
    shared_server = False                       # saved views write settings.json

    def open_all(self):
        b = self.b
        b.eval("go('work')")
        b.wait("document.querySelector('#workTbl tbody tr, #workTbl .empty')")
        b.click('#wtabs button[data-t="all"]')
        b.wait("WT==='all' && document.querySelector('#workTbl tbody tr[data-row]')")
        return b

    def ids(self):
        return self.b.eval("[...document.querySelectorAll('#workTbl tbody tr[data-row]')].map(r=>r.dataset.row)")

    def change(self, sel, value):
        self.b.eval(f"(()=>{{ const s=document.querySelector({sel!r}); s.value={value!r}; s.dispatchEvent(new Event('change',{{bubbles:true}})); }})()")
        self.b.pump(0.2)

    def test_the_tab_opens_on_all_open_as_a_read_only_list(self):
        b = self.open_all()
        self.assertEqual(b.eval("[...document.querySelectorAll('#wtabs button')].map(x=>x.textContent)"), ["Actions", "RAID", "Decisions", "All items"])
        self.assertEqual(b.eval("WVIEW"), "open")
        exp = expected(self.v)
        self.assertEqual(sorted(self.ids()), sorted(i for i, e in exp.items() if e[4] == "Open"))
        self.assertEqual(b.eval("[...document.querySelectorAll('#workTbl thead th')].map(t=>t.dataset.col)"), ["t", "type", "o", "due", "st"])
        self.assertTrue(b.eval("document.getElementById('wlay').hidden && document.getElementById('newBtn').hidden"))
        self.assertEqual(b.eval("document.querySelectorAll('#workTbl .cebtn, #workTbl td.ce').length"), 0)     # no cell editing
        self.assertEqual(b.eval("document.querySelector('#workTbl tr[data-row] td[data-f=st]').title"), "Edit it on the " + {"actions": "Actions", "raid": "RAID", "decisions": "Decisions"}[b.eval("document.querySelector('#workTbl tr[data-row]').dataset.k")] + " tab")
        st = b.eval("Object.fromEntries([...document.querySelectorAll('#workTbl tr[data-row]')].map(r=>[r.dataset.row,r.querySelector('td[data-f=st]').textContent]))")
        for id_, word in st.items():                                                  # each row keeps its own word
            self.assertEqual(word, exp[id_][5])
        self.assertIn("Pending", st.values())
        types = b.eval("[...document.querySelectorAll('#workTbl td[data-f=type] .typetag')].map(t=>t.textContent)")
        self.assertTrue(set(types) <= set(TYPES) and "Decision" in types and "Action" in types)
        self.assertIn("work=all", b.eval("location.hash"))
        self.assertIn("read-only", b.eval("document.getElementById('whintList').textContent"))

    def test_no_bulk_bar_and_no_board(self):
        b = self.open_all()
        rows = self.ids()
        b.click(f'#workTbl tr[data-row="{rows[0]}"] td[data-f=st]')
        b.click(f'#workTbl tr[data-row="{rows[1]}"] td[data-f=st]', modifiers=4)   # ⌘-click adds
        b.wait("HL.size===2")
        self.assertTrue(b.eval("document.getElementById('wbulk').hidden"))
        b.key("d")
        b.wait("document.getElementById('dispMenu').classList.contains('on')")
        self.assertFalse(b.eval("!!document.querySelector('#dispMenu [data-dlay]')"))   # no Layout in Display
        self.assertEqual(b.eval("[...document.querySelectorAll('#wgrp option')].map(o=>o.value)"), ["none", "project", "type", "owner", "due", "status", "priority"])
        self.assertIn("type", b.eval("[...document.querySelectorAll('#wbsort option')].map(o=>o.value)"))
        self.assertEqual(sorted(b.eval("[...document.querySelectorAll('#dispMenu [data-prop]')].map(i=>i.value)")),
                         sorted(["id", "t", "type", "o", "due", "pr", "st", "p", "ws", "src", "upd"]))
        b.eval("setLayout('all','board')")
        self.assertEqual(b.eval("layoutOf('all')"), "list")
        b.goto(self.base + "/#work=all&lay=board&g=due")                            # nor from an address
        b.wait("typeof go==='function' && LIVE && WT==='all'")
        self.assertTrue(b.eval("document.getElementById('workBoard').hidden && layoutOf('all')==='list'"))

    def test_a_row_opens_its_own_panel_for_each_type(self):
        b = self.open_all()
        b.eval("clearAllFilters(); workChanged()")
        b.wait("document.querySelectorAll('#workTbl tr[data-row]').length>100")
        seen = {}
        for k in ("actions", "raid", "decisions"):
            id_ = b.eval(f"document.querySelector('#workTbl tr[data-row][data-k={k}]').dataset.row")
            b.click(f'#workTbl tr[data-row="{id_}"] a.rowid')
            b.wait(f"CUR&&CUR.id==='{id_}'")
            seen[k] = b.eval("CUR.k")
            self.assertEqual(b.eval("WT"), "all")                                      # the tab stays
            b.key("Escape")
            b.eval("closePanel()")
        self.assertEqual(seen, {"actions": "actions", "raid": "raid", "decisions": "decisions"})
        dec = b.eval("document.querySelector('#workTbl tr[data-row][data-k=decisions]').dataset.row")   # a double-click too
        b.click(f'#workTbl tr[data-row="{dec}"] td[data-f=st]', count=2)
        b.wait(f"CUR&&CUR.id==='{dec}'&&CUR.k==='decisions'")

    def test_keyboard_path(self):
        b = self.open_all()
        b.eval("document.activeElement.blur()")
        b.key("j")
        first = self.ids()[0]
        b.wait(f"HL.has('{first}')")
        b.key("j")
        second = self.ids()[1]
        b.wait(f"HL.has('{second}')")
        b.key("Enter")
        b.wait(f"CUR&&CUR.id==='{second}'")
        self.assertEqual(b.eval("CUR.k"), expected(self.v)[second][0])

    def test_filters_grouping_and_the_empty_state(self):
        b = self.open_all()
        exp = expected(self.v)
        b.eval("applyFilters({st:['Open'],ty:['Decision','Issue']}); workChanged()")
        self.assertEqual(sorted(self.ids()), sorted(i for i, e in exp.items() if e[4] == "Open" and e[1] in ("Decision", "Issue")))
        self.assertIn("&ty=", b.eval("location.hash"))
        b.eval("setOf('ty').clear(); workChanged()")
        self.change("#wgrp", "type")
        labels = b.eval("[...document.querySelectorAll('#workTbl tr.wgh .wgn')].map(x=>x.textContent)")
        self.assertEqual(labels, [t for t in TYPES if any(e[4] == "Open" and e[1] == t for e in exp.values())])
        self.assertIn("item", b.eval("document.querySelector('#workTbl tr.wgh .sub').textContent"))
        self.change("#wgrp", "priority")
        self.assertIn("No priority", b.eval("[...document.querySelectorAll('#workTbl tr.wgh .wgn')].map(x=>x.textContent)"))
        self.change("#wgrp", "status")
        self.assertEqual(b.eval("[...document.querySelectorAll('#workTbl tr.wgh .wgn')].map(x=>x.textContent)"), ["Open"])   # #343: a group with nothing in it is not drawn (the Board keeps its columns)
        b.eval("applyFilters({st:['Open'],o:['Nobody At All']}); workChanged()")       # the empty state names the filters
        b.wait("document.querySelector('#workTbl .wempty')")
        self.assertIn("Nothing matches these 2 filters", b.eval("document.querySelector('#workTbl .wempty h2').textContent"))
        b.click('#workTbl [data-relax="all"]')
        b.wait("!document.querySelector('#workTbl .wempty')")
        self.assertEqual(len(self.ids()), len(exp))

    def test_presets_chase_and_a_saved_view(self):
        b = self.open_all()
        self.assertEqual(b.eval("allViews('all').map(v=>v.id)"), ["open", "mine", "soon", "chase", "overdue", "closed"])
        b.click('#wviews [data-wv="closed"]')
        b.wait("WVIEW==='closed'")
        exp = expected(self.v)
        self.assertEqual(sorted(self.ids()), sorted(i for i, e in exp.items() if e[4] != "Open"))
        b.click('#wviews [data-wv="mine"]')
        b.wait("WVIEW==='mine'")
        self.assertTrue(set(self.ids()) and all(exp[i][2] in ("Alan Carter", "Alan") for i in self.ids()))
        b.eval("applyFilters({st:['Open'],ty:['Risk']}); workChanged()")
        b.click("#saveView")
        b.click("#viewName")
        b.type("Open risks")
        b.click("#viewSave")
        b.wait("WVIEW==='saved:Open risks'", 5)
        import json
        saved = json.loads((self.v.root / "system/config/settings.json").read_text())["work"]["saved_views"]
        self.assertEqual([v["name"] for v in saved["all"]], ["Open risks"])
        self.assertEqual(saved["all"][0]["f"], {"st": ["Open"], "ty": ["Risk"]})
        b.reload("typeof go==='function' && LIVE")                                     # the address round-trips
        b.wait("WT==='all' && document.querySelector('#workTbl tbody tr[data-row]')")
        self.assertEqual(b.eval("WVIEW"), "saved:Open risks")
        self.assertTrue(all(exp[i][1] == "Risk" for i in self.ids()))
        b.click('#wtabs button[data-t="raid"]')                                         # Back returns to All items
        b.wait("WT==='raid'")
        self.assertNotIn("work=all", b.eval("location.hash"))
        b.click('#wtabs button[data-t="all"]')
        b.wait("WT==='all'")
        self.assertEqual(b.eval("WVIEW"), "saved:Open risks")                           # each tab keeps its own state

    def test_existing_addresses_are_unchanged(self):
        b = self.b
        for tab in ("actions", "raid", "decisions"):
            b.goto(self.base + f"/#work={tab}")
            b.wait(f"typeof go==='function' && LIVE && WT==='{tab}'")
            self.assertTrue(b.eval("!document.getElementById('wlay').hidden && !document.getElementById('newBtn').hidden"))
        b.goto(self.base + "/#work=nonsense")
        b.wait("typeof go==='function' && LIVE")
        self.assertEqual(b.eval("WT"), "actions")



class LinksIn(AllItemsCase):
    def test_the_project_page_link_opens_all_items_for_the_project(self):
        b = self.b
        b.eval("go('cockpit','ABC')")
        b.wait("document.querySelector('#v-cockpit [data-allitems]')")
        exp = expected(self.v)
        proj = {r["id"]: r["project"] for t in ("actions", "raid", "decisions") for r in self.v.rows(t)}
        want = sorted(i for i, e in exp.items() if e[4] == "Open" and proj[i] == "ABC")
        self.assertIn(f"({len(want)} open)", b.eval("document.querySelector('#v-cockpit [data-allitems]').textContent"))
        self.assertTrue(b.eval("!!document.querySelector('#v-cockpit [data-nav=\"actions:open:ABC\"]')"))   # the others stay
        b.click("#v-cockpit [data-allitems]")
        b.wait("VIEW==='work' && WT==='all' && document.querySelector('#workTbl tbody tr[data-row]')")
        self.assertEqual(sorted(b.eval("[...document.querySelectorAll('#workTbl tbody tr[data-row]')].map(r=>r.dataset.row)")), want)
        self.assertEqual(b.eval("[WVIEW,[...PROJF]]"), ["open", ["ABC"]])
        self.assertIn("All items", b.eval("document.getElementById('workCrumb').textContent"))
        self.assertIn("work=all", b.eval("location.hash"))


if __name__ == "__main__":
    unittest.main()
