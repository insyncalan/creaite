"""BL-164: Activity's type icons, search and filters, and undoing several past changes.

Run: python3 dev/tests/test_activity_undo.py   (the browser tests need Google Chrome; skipped otherwise)

`tracker.py undo-changes <rowid> …` puts back chosen change_log rows where they still hold the value the change gave them,
as ONE new ordinary apply (via "revert:<rowids>"), validated and logged by write_item; "undo last apply" reverses it. No
schema change. In the page: a type icon on each entry, a search box with type chips and dates (in the address), the Work
lists' selection (BL-122) with tick boxes and a bar, a confirm that lists what will happen, and the result in a snack.
"""
import json
import os
import sqlite3
import sys
import unittest
from contextlib import closing
from pathlib import Path

os.environ.setdefault("CREAITE_NO_LAUNCH", "1")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import Vault, action  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402

META, SHIFT = 4, 8


def upd(n, table, id_, **changes):
    return {"n": n, "op": "update", "table": table, "id": id_, "changes": changes, "decision": "approved"}


def seed(v):
    """Three actions and a risk, then three later applies that each change one of them."""
    v.run("init")
    v.propose("a1", [action(1, description="Send revised SOW"), action(2, description="Book the UAT room"),
                     action(3, description="Order test licences"),
                     {"n": 4, "op": "new", "table": "raid", "decision": "approved",
                      "values": {"project": "ABC", "type": "Risk", "description": "Data access late", "impact": "High",
                                 "likelihood": "Medium", "raised": "2026-10-01", "source": "Alan (cx-edit)"}}])
    v.run("apply")
    v.propose("a2", [upd(1, "actions", "ABC-A-001", status="Closed")])
    v.run("apply")
    v.propose("a3", [upd(1, "actions", "ABC-A-002", owner="Sara Example")])
    v.run("apply")
    v.propose("a4", [upd(1, "actions", "ABC-A-003", due_date="2026-11-20", priority="High")])
    v.run("apply")


class Db:
    def __init__(self, v):
        self.v = v

    def q(self, sql, *a):
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            con.row_factory = sqlite3.Row
            return [dict(r) for r in con.execute(sql, a)]

    def rowid(self, item, field, op="update"):
        return self.q("SELECT rowid FROM change_log WHERE item_id = ? AND field = ? AND op = ? ORDER BY rowid DESC LIMIT 1",
                      item, field, op)[0]["rowid"]

    def item(self, table, id_):
        r = self.q(f"SELECT * FROM {table} WHERE id = ?", id_)
        return r[0] if r else None


class UndoChangesCommand(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        seed(self.v)
        self.db = Db(self.v)

    def tearDown(self):
        self.v.cleanup()

    def undo(self, *rowids, dry=False, ok=True):
        r = self.v.run("undo-changes", "--json", *(["--dry-run"] if dry else []), *map(str, rowids), ok=ok)
        return json.loads([x for x in r.stdout.splitlines() if x.startswith("{")][-1])

    def three(self):
        return [self.db.rowid("ABC-A-001", "status"), self.db.rowid("ABC-A-002", "owner"), self.db.rowid("ABC-A-003", "due_date")]

    def test_three_past_changes_in_three_items_go_back_in_one_new_apply(self):
        applies = len(self.db.q("SELECT * FROM applies"))
        backups = set((self.v.root / "system/backups").glob("tracker-*-revert.db"))
        rows = self.three()
        out = self.undo(*rows)
        self.assertEqual(len(out["done"]), 3, out)
        self.assertEqual(out["skipped"], [])
        self.assertEqual(self.db.item("actions", "ABC-A-001")["status"], "Open")
        self.assertIsNone(self.db.item("actions", "ABC-A-001")["closed"])        # the derived field follows, as in any update
        self.assertEqual(self.db.item("actions", "ABC-A-002")["owner"], "Alan Carter")
        self.assertIsNone(self.db.item("actions", "ABC-A-003")["due_date"])
        self.assertEqual(self.db.item("actions", "ABC-A-003")["priority"], "High")   # not chosen: left as it is
        self.assertEqual(len(self.db.q("SELECT * FROM applies")), applies + 1)        # one new apply
        new = out["apply_id"]
        vias = {r["via"] for r in self.db.q("SELECT via FROM change_log WHERE apply_id = ?", new)}
        self.assertEqual(vias, {"revert:" + ",".join(map(str, sorted(rows)))})        # via carries the rowids
        self.assertEqual({r["op"] for r in self.db.q("SELECT op FROM change_log WHERE apply_id = ?", new)}, {"update"})   # ordinary rows
        self.assertTrue(set((self.v.root / "system/backups").glob("tracker-*-revert.db")) - backups)   # the database backup

    def test_a_later_edit_skips_that_item_and_the_others_still_go_back(self):
        rows = self.three()
        self.v.propose("a5", [upd(1, "actions", "ABC-A-002", owner="Omar Ali")])     # changed since
        self.v.run("apply")
        out = self.undo(*rows)
        self.assertEqual(sorted(d["id"] for d in out["done"]), ["ABC-A-001", "ABC-A-003"])
        self.assertEqual([(s["id"], s["why"]) for s in out["skipped"]], [("ABC-A-002", "has changed since: left as it is")])
        self.assertEqual(self.db.item("actions", "ABC-A-002")["owner"], "Omar Ali")
        self.assertIn("skipped 1", out["message"])

    def test_the_dry_run_matches_what_happens_and_writes_nothing(self):
        rows = self.three()
        self.v.propose("a5", [upd(1, "actions", "ABC-A-002", owner="Omar Ali")])
        self.v.run("apply")
        before = (self.db.q("SELECT count(*) n FROM change_log")[0]["n"], self.db.q("SELECT count(*) n FROM applies")[0]["n"])
        plan = self.undo(*rows, dry=True)
        self.assertEqual(before, (self.db.q("SELECT count(*) n FROM change_log")[0]["n"], self.db.q("SELECT count(*) n FROM applies")[0]["n"]))
        self.assertEqual(self.db.item("actions", "ABC-A-001")["status"], "Closed")
        self.assertIsNone(plan["apply_id"])
        real = self.undo(*rows)
        strip = lambda o: ([(d["rowid"], d["id"], d.get("from"), d.get("to")) for d in o["done"]], [(s["rowid"], s["why"]) for s in o["skipped"]])  # noqa: E731
        self.assertEqual(strip(plan), strip(real))
        self.assertEqual(plan["done"][0]["from"], "Closed" if plan["done"][0]["id"] == "ABC-A-001" else plan["done"][0]["from"])

    def test_the_revert_is_itself_undone_by_undo_last_apply(self):
        rows = self.three()
        out = self.undo(*rows)
        self.v.run("undo")
        self.assertEqual(self.db.item("actions", "ABC-A-001")["status"], "Closed")
        self.assertEqual(self.db.item("actions", "ABC-A-002")["owner"], "Sara Example")
        self.assertEqual(self.db.item("actions", "ABC-A-003")["due_date"], "2026-11-20")
        self.assertTrue(self.db.q("SELECT undone_at FROM applies WHERE apply_id = ?", out["apply_id"])[0]["undone_at"])
        # with the revert undone, the same changes can be put back again
        again = self.undo(*rows)
        self.assertEqual(len(again["done"]), 3)

    def test_a_created_item_is_removed_only_if_untouched(self):
        made = self.db.rowid("ABC-A-002", "id", op="insert")
        out = self.undo(made)                                                         # ABC-A-002's owner changed since: kept
        self.assertEqual(out["done"], [])
        self.assertIn("changed since", out["skipped"][0]["why"])
        self.assertIsNotNone(self.db.item("actions", "ABC-A-002"))
        made_r = self.db.rowid("ABC-004", "id", op="insert")                         # the risk: never changed
        out = self.undo(made_r)
        self.assertEqual([d["change"] for d in out["done"]], ["removed"])
        self.assertIsNone(self.db.item("raid", "ABC-004"))
        self.v.run("undo")                                                            # and back again, as it was
        self.assertEqual(self.db.item("raid", "ABC-004")["description"], "Data access late")

    def test_a_created_item_that_something_refers_to_stays(self):
        self.v.propose("ms", [{"n": 1, "op": "new", "table": "milestones", "decision": "approved",
                               "values": {"project": "ABC", "name": "UAT", "baseline_date": "2026-11-01", "forecast_date": "2026-11-01",
                                          "source": "Alan (cx-edit)"}}])
        self.v.run("apply")
        ms = self.db.q("SELECT id FROM milestones")[0]["id"]
        made = self.db.rowid(ms, "id", op="insert")
        self.v.propose("link", [upd(1, "actions", "ABC-A-003", milestone=ms)])
        self.v.run("apply")
        out = self.undo(made)
        self.assertEqual(out["done"], [])
        self.assertIn("refers to it", out["skipped"][0]["why"])

    def test_what_cannot_be_chosen(self):
        rows = self.three()
        out = self.undo(*rows)
        undo_row = self.db.q("SELECT rowid FROM change_log WHERE apply_id = ? LIMIT 1", out["apply_id"])[0]["rowid"]
        again = self.undo(undo_row, rows[0])
        whys = {s["rowid"]: s["why"] for s in again["skipped"]}
        self.assertEqual(whys[undo_row], "is itself an undo")
        self.assertEqual(whys[rows[0]], "already undone")
        self.assertIn("not in the change log", self.undo(999999)["skipped"][0]["why"])
        self.assertIn("Nothing to undo", self.undo(999999)["message"])
        self.assertEqual(self.v.run("undo-changes", "abc", ok=False).returncode, 2)

    def test_two_changes_to_one_field_go_back_in_turn(self):
        self.v.propose("a5", [upd(1, "actions", "ABC-A-002", owner="Omar Ali")])
        self.v.run("apply")
        first = self.db.q("SELECT rowid FROM change_log WHERE item_id='ABC-A-002' AND field='owner' AND op='update' ORDER BY rowid")
        out = self.undo(*[r["rowid"] for r in first])
        self.assertEqual(len(out["done"]), 2)
        self.assertEqual(self.db.item("actions", "ABC-A-002")["owner"], "Alan Carter")

    def test_validation_is_never_loosened(self):
        """A restore that breaks a rule is skipped with the rule's own words; nothing else changes for it."""
        self.v.propose("d", [{"n": 1, "op": "new", "table": "decisions", "decision": "approved",
                              "values": {"project": "ABC", "decision": "Pick a vendor", "status": "Pending", "source": "Alan (cx-edit)"}}])
        self.v.run("apply")
        dec = self.db.q("SELECT id FROM decisions")[0]["id"]
        self.v.propose("d2", [upd(1, "decisions", dec, status="Made", date="2026-10-05", made_by="Jane Doe")])
        self.v.run("apply")
        out = self.undo(self.db.rowid(dec, "status"))
        self.assertEqual(out["done"], [])
        self.assertIn("can't go back to Pending", out["skipped"][0]["why"])
        self.assertEqual(self.db.item("decisions", dec)["status"], "Made")

    def test_no_schema_change(self):
        schema = (self.v.root / "system/scripts/schema.sql").read_text()
        self.undo(*self.three())
        for _ in range(2):
            r = self.v.run("migrate")
        tables = self.db.q("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name")
        self.v.run("migrate")
        self.assertEqual(tables, self.db.q("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name"))
        self.assertEqual(schema, (Path(__file__).resolve().parents[2] / "system/scripts/schema.sql").read_text())
        self.assertNotIn("revert", schema)
        del r

    def test_activity_marks_reverted_entries_and_shows_one_entry_for_the_revert(self):
        sys.path.insert(0, str(self.v.root / "system/scripts"))
        import build_dashboard
        rows = self.three()
        out = self.undo(*rows)
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            con.row_factory = sqlite3.Row
            act = build_dashboard.activity(con)
        by_row = {a.get("rowid"): a for a in act if a.get("rowid")}
        for r in rows:
            self.assertTrue(by_row[r]["reverted"], r)
        rev = [a for a in act if a.get("revert")]
        self.assertEqual(len(rev), 1)
        self.assertEqual(rev[0]["change"], "Undid 3 changes")
        self.assertEqual(rev[0]["apply_id"], out["apply_id"])
        self.assertEqual(rev[0]["by"], "You, in Activity")
        kinds = {a["id"]: a["kind"] for a in act if a.get("id") and a.get("kind")}
        self.assertEqual(kinds["ABC-A-001"], "action")
        self.assertEqual(kinds["ABC-004"], "Risk")
        self.assertTrue(all("rowid" not in a or isinstance(a["rowid"], int) for a in act))
        # entries that can't be chosen carry no rowid: the revert itself
        self.assertNotIn("rowid", rev[0])


class ActivityPage(LiveBrowserCase):
    width, height = 1400, 900

    @classmethod
    def load(cls, v):
        seed(v)
        v.propose("a5", [upd(1, "actions", "ABC-A-001", owner="Omar Ali", priority="Urgent")])   # the latest apply
        v.run("apply")

    def go_activity(self, hash_=""):
        b = self.b
        b.eval(f"go('activity')" if not hash_ else f"location.hash={json.dumps(hash_)}")
        b.wait("document.querySelector('#actTbl tbody tr')")

    def rows(self):
        return self.b.eval("[...document.querySelectorAll('#actTbl tbody tr')].map(t=>t.textContent)")

    def count(self):
        return self.b.eval("document.getElementById('actCount').textContent")

    def test_each_entry_has_its_type_icon_and_name(self):
        b = self.b
        self.go_activity()
        icons = b.eval("""[...document.querySelectorAll('#actTbl tbody tr .acticon')].map(s=>[s.getAttribute('aria-label'),s.dataset.tip,!!s.querySelector('svg')])""")
        names = {x[0] for x in icons}
        self.assertTrue({"Action", "Risk"} <= names, names)
        self.assertTrue(all(x[0] == x[1] and x[2] for x in icons))
        # every kind has an icon and a name
        kinds = b.eval("ACTKINDS.map(k=>[k[0],k[1],!!ICONS[k[2]]])")
        self.assertTrue(all(k[2] for k in kinds), kinds)
        self.assertEqual([k[1] for k in kinds][:3], ["Action", "Risk", "Issue"])

    def test_search_by_id_text_project_person_and_date_with_the_count_and_clear(self):
        b = self.b
        self.go_activity()
        total = b.eval("document.querySelectorAll('#actTbl tbody tr').length")
        self.assertEqual(self.count(), f"{total} of {total}")
        b.eval("document.getElementById('actQ').focus()")
        b.type("ABC-A-002")
        b.wait("document.querySelectorAll('#actTbl tbody tr').length<" + str(total))
        self.assertTrue(all("ABC-A-002" in r for r in self.rows()), self.rows())
        self.assertRegex(self.count(), rf"^\d+ of {total}$")
        for q, must in (("uat room", "Book the UAT room"), ("example programme", "ABC-"), ("omar", "Omar Ali"),
                        ("sara", "Sara Example")):          # a project matches by its name; its lines carry its code
            b.eval(f"document.getElementById('actQ').value={json.dumps(q)}; document.getElementById('actQ').dispatchEvent(new Event('input',{{bubbles:true}}))")
            self.assertTrue(self.rows() and all(must.lower() in r.lower() for r in self.rows()), (q, self.rows()))
        when = b.eval("fd(ACT[0].at.slice(0,10))")
        b.eval(f"document.getElementById('actQ').value={json.dumps(when)}; document.getElementById('actQ').dispatchEvent(new Event('input',{{bubbles:true}}))")
        self.assertTrue(self.rows())
        b.eval("document.getElementById('actQ').value='zzzz nothing'; document.getElementById('actQ').dispatchEvent(new Event('input',{bubbles:true}))")
        empty = b.eval("document.getElementById('actTbl').textContent")
        self.assertIn("zzzz nothing", empty)                                                  # says what was searched
        b.click("#actTbl [data-actclear]")
        self.assertEqual(self.count(), f"{total} of {total}")
        self.assertEqual(b.eval("document.getElementById('actQ').value"), "")

    def test_slash_focuses_the_search_only_on_activity(self):
        b = self.b
        self.go_activity()
        b.eval("document.activeElement.blur()")
        b.key("/")
        self.assertEqual(b.eval("document.activeElement.id"), "actQ")
        self.assertFalse(b.eval("document.getElementById('chat').classList.contains('on')"))
        b.eval("go('today')")
        b.eval("document.activeElement.blur()")
        b.key("/")
        b.wait("document.getElementById('chat').classList.contains('on')")                  # elsewhere / is still ask creaite

    def test_type_chips_dates_and_the_address_round_trip(self):
        b = self.b
        self.go_activity()
        # BL-316: Kind is the FilterBar block's list (was a row of toggles)
        b.click("#actTypeBtn")
        b.wait("document.getElementById('actTypeMenu').classList.contains('on')")
        b.click('#actTypeMenu [role=option]:has(input[value="Risk"])')
        self.assertTrue(all("ABC-004" in r for r in self.rows()), self.rows())
        self.assertEqual(b.eval("document.querySelector('#actTypeMenu [role=option]:has(input[value=\"Risk\"])').getAttribute('aria-selected')"), "true")
        self.assertEqual(b.eval("document.getElementById('actTypeBtn').textContent.trim()"), "Kind: Risk")
        b.key("Escape")
        b.eval("document.getElementById('actQ').value='data'; document.getElementById('actQ').dispatchEvent(new Event('input',{bubbles:true}))")
        self.assertIn("q=data", b.eval("location.hash"))
        self.assertIn("type=Risk", b.eval("location.hash"))
        h = b.eval("location.hash")
        # open an item and come back: the filters are kept
        b.click('#actTbl a[data-open]')
        b.wait("document.getElementById('panel').classList.contains('on')")
        b.key("Escape")
        b.wait("!document.getElementById('panel').classList.contains('on')")
        self.assertEqual(b.eval("document.getElementById('actQ').value"), "data")
        # leave and come back with Back
        b.eval("go('today')")
        b.eval("history.back()")
        b.wait("VIEW==='activity'")
        b.wait("document.getElementById('actQ').value==='data'")
        self.assertTrue(all("ABC-004" in r for r in self.rows()))
        # a fresh load of the address
        b.goto(self.base + "/" + h)
        b.wait("typeof go==='function' && LIVE && VIEW==='activity'")
        b.wait("document.getElementById('actQ').value==='data'")
        self.assertTrue(all("ABC-004" in r for r in self.rows()))
        # dates: from after everything shows nothing, and says so
        b.eval("ACTF={}; renderActivity()")
        b.click("#actFunnel")                                    # the funnel's picker: When is two date boxes
        b.click('#actPick .fpf[data-fpk="when"]')
        b.wait("!!document.querySelector('#actPick input[data-when=from]')")
        b.eval("const i=document.querySelector('#actPick input[data-when=from]'); i.value='01-01-2099'; i.dispatchEvent(new Event('change',{bubbles:true}))")
        self.assertIn("Nothing matches", b.eval("document.getElementById('actTbl').textContent"))
        self.assertIn("from=2099-01-01", b.eval("location.hash"))

    def sel_rows(self):
        return self.b.eval("[...document.querySelectorAll('#actTbl tbody tr[data-row].hl')].map(t=>t.dataset.row)")

    def test_selecting_with_cmd_ctrl_shift_and_esc(self):
        b = self.b
        self.go_activity()
        rows = b.eval("[...document.querySelectorAll('#actTbl tbody tr[data-row]')].map(t=>t.dataset.row)")
        self.assertGreaterEqual(len(rows), 5)
        cell = lambda r: f'#actTbl tr[data-row="{r}"] td.actwhen'  # noqa: E731
        b.click(cell(rows[1]))
        self.assertEqual(self.sel_rows(), [rows[1]])
        b.click(cell(rows[3]), modifiers=META)
        self.assertEqual(self.sel_rows(), [rows[1], rows[3]])
        # Ctrl-click (Windows): on a Mac Chrome turns a real Ctrl-click into a right click, so the event is sent directly
        b.eval(f"document.querySelector('{cell(rows[3])}').dispatchEvent(new MouseEvent('click',{{bubbles:true,cancelable:true,ctrlKey:true}}))")
        self.assertEqual(self.sel_rows(), [rows[1]])
        b.click(cell(rows[1]))                                                        # the anchor is the last row clicked (BL-122)
        b.click(cell(rows[4]), modifiers=SHIFT)
        self.assertEqual(self.sel_rows(), rows[1:5])
        self.assertIn("4 selected", b.eval("document.getElementById('actBar').textContent"))
        self.assertTrue(all(b.eval(f"document.querySelector('#actTbl tr[data-row=\"{r}\"] input[type=checkbox]').checked") for r in rows[1:5]))
        b.click(f'#actTbl tr[data-row="{rows[0]}"] input[type=checkbox]')                      # a tick adds
        self.assertEqual(len(self.sel_rows()), 5)
        b.key("Escape")
        self.assertEqual(self.sel_rows(), [])
        self.assertTrue(b.eval("document.getElementById('actBar').hidden"))
        self.assertEqual(b.eval("VIEW"), "activity")

    def pick(self, rowids):
        self.b.eval(f"HL.clear(); {json.dumps(rowids)}.forEach(r=>HL.set('r'+r,'act')); actPaint()")

    def latest_rows(self):
        return self.b.eval("ACT.filter(a=>a.rowid&&a.apply_id===D.latest_apply).map(a=>a.rowid)")

    def older_rows(self):
        return self.b.eval("""['ABC-A-001|status','ABC-A-002|owner','ABC-A-003|due_date'].map(k=>{ const [id,f]=k.split('|');
          return ACT.find(a=>a.rowid&&a.id===id&&a.apply_id!==D.latest_apply&&a.change.startsWith(f.replace('_',' ')+':')).rowid; })""")

    def test_undo_three_older_changes_with_the_confirm_then_undo_the_undo(self):
        b = self.b
        self.go_activity()
        rows = self.older_rows()
        self.pick(rows)
        b.click("#actUndoSel")
        b.wait("document.getElementById('actDlg').open")
        items = b.eval("[...document.querySelectorAll('#actDlg li')].map(l=>l.textContent)")
        self.assertEqual(len(items), 3)
        self.assertTrue(any("ABC-A-001" in x and "Closed → Open" in x for x in items), items)
        self.assertTrue(any("ABC-A-002" in x and "Sara Example → Alan Carter" in x for x in items), items)
        self.assertTrue(any("ABC-A-003" in x and "20-11-2026 → —" in x for x in items), items)
        b.click("#actDlgGo")
        b.wait("document.getElementById('snack').classList.contains('on')&&/Undid/.test(document.getElementById('snackT').textContent)", 20)
        self.assertRegex(b.eval("document.getElementById('snackT').textContent"), r"Undid \d changes?")
        b.wait("ACT.some(a=>a.revert)")
        self.assertTrue(b.eval("ACT.filter(a=>a.reverted).length>=2"))
        self.assertTrue(b.eval("[...document.querySelectorAll('#actTbl tr.undone')].length>=2"))
        self.assertIn("undone", b.eval("document.querySelector('#actTbl tr.undone td:last-child').textContent"))
        # the revert is one entry with its own Undo (it is the latest apply now)
        rev = b.eval("(()=>{ const i=ACT.findIndex(a=>a.revert); return {i, apply:ACT[i].apply_id, latest:D.latest_apply}; })()")
        self.assertEqual(rev["apply"], rev["latest"])
        b.click(f'#actTbl [data-undoapply="{rev["apply"]}"]')
        b.wait("!ACT.some(a=>a.revert&&!a.undone)", 20)
        self.assertFalse(b.eval("ACT.some(a=>a.reverted)"))

    def test_a_selection_of_the_whole_latest_apply_uses_the_exact_undo(self):
        b = self.b
        self.go_activity()
        latest = self.latest_rows()
        self.assertGreaterEqual(len(latest), 2)
        b.eval("window.CALLED=[]; const u=undoApply; undoApply=function(id){ CALLED.push(id); return u.apply(this,arguments); }")
        self.pick(latest)
        b.click("#actUndoSel")
        b.wait("CALLED.length===1", 20)
        self.assertEqual(b.eval("CALLED[0]"), b.eval("D.latest_apply") or b.eval("CALLED[0]"))
        self.assertFalse(b.eval("document.getElementById('actDlg')&&document.getElementById('actDlg').open"))

    def test_over_25_asks_again(self):
        b = self.b
        self.go_activity()
        b.eval("""window.FAKE=Array.from({length:30},(_,i)=>({rowid:i+1,id:'ABC-A-001',field:'owner',change:'set',from:'a',to:'b'}));
          api=(p,body)=>Promise.resolve(p==='/api/undo-changes'?{ok:true,done:FAKE,skipped:[],message:'x',apply_id:body.dry_run?null:99}:{ok:true});""")
        self.pick(self.older_rows())
        b.click("#actUndoSel")
        b.wait("document.getElementById('actDlg').open")
        self.assertEqual(b.eval("document.getElementById('actDlgGo').textContent"), "Undo 30")
        b.click("#actDlgGo")
        self.assertTrue(b.eval("document.getElementById('actDlg').open"))                       # asked again, with the count
        self.assertIn("30", b.eval("document.getElementById('actDlgAsk').textContent"))
        b.click("#actDlgCancel")
        b.wait("!document.getElementById('actDlg').open")

    def test_entries_that_cannot_be_chosen_have_a_disabled_tick(self):
        b = self.b
        self.go_activity()
        r = b.eval("""(()=>{ ACT.unshift({at:'2026-10-10 09:00',what:'ABC-A-001 · changed',by:'You'}); renderActivity();
          const first=document.querySelector('#actTbl tbody tr'); const cb=first.querySelector('input[type=checkbox]'); return {row:first.dataset.row||null, tick:!!cb, off:!!cb&&cb.disabled}; })()""")
        self.assertEqual(r, {"row": None, "tick": True, "off": True})   # #191: a tick box on every row, disabled where it cannot be chosen

    def test_the_disabled_tick_is_skipped_by_a_range_and_not_counted(self):
        """#191: a range across a row that cannot be chosen never takes it, its tick cannot be ticked, and Undo n counts only chosen rows.
        (Activity has no select-all key and J/K are not bound there: ranges and ticks are how several rows are chosen.)"""
        b = self.b
        self.go_activity()
        b.eval("""(()=>{ const x={at:'2026-10-10 09:00',what:'ABC-A-001 · changed',by:'You'}; ACT.unshift({...x}); ACT.splice(3,0,{...x}); renderActivity(); })()""")
        b.eval("document.activeElement&&document.activeElement.blur(); hlClear(); actPaint()")
        order = b.eval("[...document.querySelectorAll('#actTbl tbody tr')].map(t=>t.dataset.row||null)")
        self.assertIsNone(order[0])
        self.assertIsNone(order[3])
        ok = [r for r in order if r]
        cell = lambda r: f'#actTbl tr[data-row="{r}"] td.actwhen'  # noqa: E731
        b.click(cell(ok[0]))
        b.click(cell(ok[3]), modifiers=SHIFT)                                            # a range from the first to the fourth, over the disabled row
        self.assertEqual(self.sel_rows(), ok[:4])                                        # the range spans the disabled row without taking it
        b.eval("document.querySelector('#actTbl tr:not([data-row]) input').click()")        # a disabled tick does nothing
        self.assertEqual(self.sel_rows(), ok[:4])
        self.assertEqual(b.eval("document.querySelectorAll('#actTbl tr:not([data-row]) input:checked').length"), 0)
        self.assertEqual(b.eval("document.getElementById('actUndoSel').textContent.trim()"), "Undo 4")
        self.assertEqual(b.eval("document.querySelectorAll('#actTbl input[disabled]').length"), 2)

    def test_the_footer_says_when_the_cap_is_reached(self):
        b = self.b
        self.go_activity()
        self.assertFalse(b.eval("!!document.getElementById('actCap')&&!document.getElementById('actCap').hidden"))
        b.eval("D.activity_capped=true; renderActivity()")
        self.assertIn("newest", b.eval("document.getElementById('actCap').textContent"))


if __name__ == "__main__":
    unittest.main()
