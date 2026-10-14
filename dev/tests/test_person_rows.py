"""A person's page draws their open work with Work's own rows (BL-68), in headless Chrome.

Run: python3 dev/tests/test_person_rows.py   (needs Google Chrome; skipped otherwise)

A throwaway vault with fictional data; the dashboard's file layer is an in-memory fake, so the proposals the page writes
are read back from it. Covers: Work's rows grouped by project without an Owner column, Work's column choice, sorting by
a heading, a row's ID opening the item in the peek (BL-176), editing the due date in the peek staging a proposal, j and k, early-warning flags, "See all in Work"
filtered to the owner, handover (select, reassign, undo) and recent decisions as Decisions rows.
"""
import json
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_dashboard import CHROME, d, new, populate  # noqa: E402
from test_insight import chrome  # noqa: E402
from test_tracker import Vault, action  # noqa: E402

FAKE = """const FILES={}; VW={read:async p=>{ if(!(p in FILES)) throw new Error("not found: "+p); return FILES[p]; },
  write:async(p,t)=>{ FILES[p]=t; }, remove:async p=>{ delete FILES[p]; }, exists:async p=>p in FILES,
  append:async(p,t)=>{ FILES[p]=(FILES[p]||"")+t; }, upload:async()=>{} }; VSTATE="ok"; needVault=async()=>true;
  const wait=ms=>new Promise(r=>setTimeout(r,ms)), until=async(f,ms=3000)=>{ const t=Date.now(); while(!f()){ if(Date.now()-t>ms) throw new Error("timed out: "+f); await wait(10); } };
  const peek=()=>document.getElementById("panel").classList.contains("on")&&document.getElementById("panel").classList.contains("peek");"""

STEPS = r"""
  const pp=()=>document.getElementById("v-person"), out={}, byT=t=>A.concat(R).find(x=>x.t===t);
  const txt=n=>{ const c=n.cloneNode(true); c.querySelectorAll(".x,.wflag").forEach(e=>e.remove()); return c.textContent.trim(); };
  const tables=()=>[...pp().querySelectorAll("table.ptbl")].map(t=>({t:t.dataset.t, group:(()=>{ let e=t.closest(".tbl").previousElementSibling; while(e&&!e.classList.contains("pph")) e=e.previousElementSibling; return e?e.textContent.replace(/\s+/g," ").trim():""; })(),
    heads:[...t.tHead.rows[0].cells].map(c=>c.textContent.replace(/[▲▼]/g,"").trim()), rows:[...t.tBodies[0].rows].map(r=>txt(r.querySelector("td.title")))}));
  const proposals=()=>Object.entries(FILES).filter(([k])=>/proposed-.*dashboard/.test(k)).map(([k,v])=>JSON.parse(v));
  go("person","Omar Ali"); await wait(30);
  // 1. Work's rows grouped by project; no Owner column
  out.groups=tables(); out.cards=[...pp().querySelectorAll(".card h2")].map(h=>h.textContent.replace(/\s+/g," ").trim());
  out.noOwner=!pp().querySelector('table.ptbl td[data-f="o"]');
  // 2. Work's column choice, order and widths apply (shared, remembered)
  const keep=[JSON.stringify(COLVIS),JSON.stringify(COLORD),JSON.stringify(RZ)];
  COLVIS.actions=["t","o","due","st","ws"]; COLORD.actions=["due","t"]; RZ["actions|due"]=150; renderPerson("Omar Ali");
  out.choice={heads:tables()[0].heads, width:pp().querySelector('table.ptbl[data-t=actions] th[data-col=due]').style.width};
  COLVIS=JSON.parse(keep[0]); COLORD=JSON.parse(keep[1]); RZ=JSON.parse(keep[2]); renderPerson("Omar Ali");
  // 3. sorting by a heading: asc, desc, then the default (overdue first, then by date)
  const abc=()=>tables().find(t=>t.t==="actions"&&/Example Programme/.test(t.group)).rows, th=()=>pp().querySelector('table.ptbl[data-t=actions] th[data-col=t]');
  out.sort=[abc()]; th().click(); out.sort.push(abc(), th().getAttribute("aria-sort")); th().click(); out.sort.push(abc()); th().click(); out.sort.push(abc());
  // 4. a row's ID opens the item in the peek; j and k step through the rows
  pp().querySelector("table.ptbl tr[data-row] a.rowid").click(); await until(()=>CUR&&peek());
  out.panel=[!!CUR, CUR&&CUR.k, CUR&&CUR.id, peek(), pp().querySelectorAll("tr.sel").length]; const first=CUR.id;
  document.activeElement&&document.activeElement.blur&&document.activeElement.blur();
  document.dispatchEvent(new KeyboardEvent("keydown",{key:"j",bubbles:true})); await until(()=>CUR&&CUR.id!==first&&peek()); out.j=[CUR.id, pp().querySelector("tr.sel").dataset.row];
  document.dispatchEvent(new KeyboardEvent("keydown",{key:"k",bubbles:true})); await until(()=>CUR&&CUR.id===first); out.k=CUR.id; closePanel();
  // 5. early-warning flags, as in Work
  const flagged=byT("Omar overdue ABC"); D.warnings=[{k:"actions",id:flagged.id,p:"ABC",sig:"stale",text:"No movement for 3 weeks"}]; renderPerson("Omar Ali");
  out.flag=[...pp().querySelectorAll("tr[data-row]")].filter(r=>r.querySelector(".wflag")).map(r=>r.dataset.row===flagged.id); D.warnings=[]; renderPerson("Omar Ali");
  // 6. double-click a due date: the peek opens on the item with the due date in focus; a new date is staged as a proposal
  const later=byT("Omar later ABC"); pp().querySelector(`tr[data-row="${later.id}"] td[data-f=due]`).dispatchEvent(new MouseEvent("dblclick",{bubbles:true}));
  await until(()=>CUR&&CUR.id===later.id&&peek());
  out.editing=[CUR.id===later.id&&peek(), document.activeElement&&document.activeElement.dataset.pkp];
  document.querySelector('#panel [data-pkp="due"]').click(); await until(()=>document.querySelector(".pkpop .pkdt"));
  const dt=document.querySelector(".pkpop .pkdt"); dt.value=__NEWDUE__; dt.dispatchEvent(new KeyboardEvent("keydown",{key:"Enter",bubbles:true}));
  await until(()=>PKS.length===1); await PKQ; await VQ;
  out.edit={due:later.due, view:VIEW, proposals:proposals().map(p=>p.items.map(i=>[i.table,i.op,i.id,i.changes]))}; closePanel();
  // 7. recent decisions are the Decisions table's row
  out.decisions=tables().filter(t=>t.t==="decisions");
  // 8. See all in Work: Work filtered to this owner
  pp().querySelector("[data-seeall=raid]").click(); await wait(20);
  out.seeAll=[VIEW, WT, [...OWN], [...FX.st], rows().map(x=>x.t), location.hash];
  go("person","Omar Ali"); pp().querySelector("[data-seeall=actions]").click(); await wait(20);
  out.seeAllActions=[VIEW, WT, [...OWN], rows().map(x=>x.t).sort()];
  // 9. hand over: tick rows, reassign, undo
  go("person","Omar Ali"); await wait(20); document.getElementById("ppHand").click(); await wait(20);
  out.hand=[pp().querySelectorAll("tr.handpick").length, pp().querySelectorAll("th.pickcol").length, pp().querySelectorAll("input.handbox").length];
  const picks=()=>pp().querySelectorAll("tr.handpick");
  picks()[0].click(); await wait(10); picks()[1].click(); await wait(10); out.picked=[...pp().querySelectorAll("input.handbox:checked")].length;
  pp().querySelector("table.ptbl th[data-col=t]").click(); await wait(10); out.pickedAfterClickingAHeading=[...pp().querySelectorAll("input.handbox:checked")].length;
  document.getElementById("handTo").value="Sara Example"; const before=[...HAND.picked].map(k=>k.split(":")[1]); document.getElementById("handGo").click(); await wait(150); await VQ;
  out.handed=before.map(id=>REC(id.includes("-A-")?"actions":"raid",id).o);
  await UNDO(); await VQ; out.undone=before.map(id=>REC(id.includes("-A-")?"actions":"raid",id).o);
  window.OUT=out;
"""


class PersonRowsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not CHROME.exists():
            raise unittest.SkipTest("Google Chrome not installed")
        cls.v = v = Vault()
        populate(v)
        v.propose("omar", [
            action(21, project="ABC", description="Omar overdue ABC", owner="Omar Ali", due_date=d(-4), priority="Urgent"),
            action(22, project="ABC", description="Omar later ABC", owner="Omar Ali", due_date=d(9)),
            new("raid", 23, project="DEF", type="Risk", description="Pilot slips", owner="Omar Ali", impact="High",
                likelihood="Medium", raised=d(-6), due_date=d(2), response_action="Add a buffer week",
                source="Alan (cx-edit)"),
            new("raid", 24, project="ABC", type="Issue", description="Vendor access blocked", owner="Omar Ali",
                impact="Medium", likelihood="High", raised=d(-3), source="Alan (cx-edit)"),
            new("decisions", 25, project="ABC", decision="Use the shared tenant", made_by="Omar Ali", date=d(-3),
                source="Alan (cx-edit)")])
        v.run("apply")
        v.run(script="build_dashboard.py")
        due = next(d(n) for n in range(20, 27) if date.fromisoformat(d(n)).weekday() < 5)   # a weekday: a weekend date asks first
        new_due = f"{due[8:]}-{due[5:7]}-{due[:4]}"
        cls.new_due = due
        cls.out, cls.errors = chrome(v, FAKE + STEPS.replace("__NEWDUE__", json.dumps(new_due)), name="person-rows")

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def test_no_script_errors(self):
        self.assertIsNotNone(self.out)
        self.assertNotIn("error", self.out)
        self.assertEqual(self.errors, [])

    def test_work_rows_grouped_by_project_without_an_owner_column(self):
        o = self.out
        g = [(t["group"], t["t"], t["heads"], t["rows"]) for t in o["groups"] if t["t"] != "decisions"]
        self.assertEqual([x[:2] for x in g], [("Example Programme", "actions"), ("Example Programme", "raid"),
                                              ("Digital Enablement", "actions"), ("Digital Enablement", "raid")])
        self.assertEqual(g[0][2], ["Action", "Due", "Priority", "Status"])             # Work's default columns, less Owner
        self.assertEqual(g[1][2], ["Risk or issue", "Due", "Priority", "Response"])
        self.assertEqual(g[0][3], ["Omar overdue ABC", "Omar later ABC"])              # overdue first, then by date
        self.assertEqual(g[1][3], ["Vendor access blocked"])
        self.assertEqual(g[3][3], ["Pilot slips"])
        self.assertTrue(o["noOwner"])
        self.assertEqual(o["cards"][0], "Open work · 5")

    def test_work_column_choice_order_and_width_apply(self):
        c = self.out["choice"]
        self.assertEqual(c["heads"], ["Due", "Action", "Status", "Workstream"])        # Owner left out, order as in Work
        self.assertEqual(c["width"], "150px")

    def test_sorting_by_a_heading(self):
        first, asc, aria, desc, default = self.out["sort"]
        self.assertEqual(first, ["Omar overdue ABC", "Omar later ABC"])
        self.assertEqual((asc, aria), (["Omar later ABC", "Omar overdue ABC"], "ascending"))
        self.assertEqual(desc, ["Omar overdue ABC", "Omar later ABC"])
        self.assertEqual(default, first)                                                # a third click returns to default

    def test_a_row_opens_the_peek_and_j_k_step(self):
        o = self.out
        self.assertEqual(o["panel"][:2], [True, "actions"])
        self.assertEqual(o["panel"][3:], [True, 1])
        self.assertEqual(o["j"][0], o["j"][1])
        self.assertNotEqual(o["j"][0], o["panel"][2])
        self.assertEqual(o["k"], o["panel"][2])

    def test_early_warning_flag_shows_on_the_row(self):
        self.assertEqual(sorted(self.out["flag"]), [True])

    def test_editing_the_due_date_in_the_peek_stages_a_proposal(self):
        e = self.out["edit"]
        self.assertEqual(self.out["editing"][0], True)                                 # the peek, on the double-clicked item
        self.assertEqual(self.out["editing"][1], "due")                                # with its due date in focus
        self.assertEqual(len(e["proposals"]), 1)
        (item,) = e["proposals"][0]
        self.assertEqual((item[0], item[1], item[3]), ("actions", "update", {"due_date": self.new_due}))
        self.assertEqual(e["due"], self.new_due)
        self.assertEqual(e["view"], "person")

    def test_recent_decisions_are_decisions_rows(self):
        (t,) = self.out["decisions"]
        self.assertEqual(t["heads"], ["Decision", "Status", "Made by", "Needed by", "Date", "Source"])     # Work's Decisions columns (BL-53 added two)
        self.assertEqual(t["rows"], ["Use the shared tenant"])

    def test_see_all_opens_work_filtered_to_the_owner(self):
        raid = self.out["seeAll"]
        self.assertEqual(raid[:4], ["work", "raid", ["Omar Ali"], ["Open"]])
        self.assertEqual(sorted(raid[4]), ["Pilot slips", "Vendor access blocked"])
        self.assertIn("o=Omar", raid[5])
        acts = self.out["seeAllActions"]
        self.assertEqual(acts[:3], ["work", "actions", ["Omar Ali"]])
        self.assertEqual(acts[3], sorted(["Agree pilot success criteria", "Omar later ABC", "Omar overdue ABC"]))

    def test_handover_selects_reassigns_and_undoes(self):
        o = self.out
        self.assertEqual(o["hand"], [5, 4, 5])                                         # a row and a tick box per item
        self.assertEqual(o["picked"], 2)
        self.assertEqual(o["pickedAfterClickingAHeading"], 2)                          # sorting keeps the selection
        self.assertEqual(o["handed"], ["Sara Example"] * 2)
        self.assertEqual(o["undone"], ["Omar Ali"] * 2)


if __name__ == "__main__":
    unittest.main()
