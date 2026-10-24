"""End-to-end tests for the people register in the dashboard (BL-55) and the People view (BL-56).

Run: python3 dev/tests/test_people_dashboard.py   (needs Google Chrome; skipped otherwise)

Like test_dashboard_editing.py: a throwaway vault with fictional data and the real dashboard in headless Chrome, with
the file layer (VW) replaced by an in-memory fake. The page's own code makes the edits (the Settings › People card, the
owner picker, the new-person prompt, rename and merge); the test copies the proposals it wrote into the vault, applies
them with tracker.py, checks the register and the items, and undoes the apply.
"""
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from page_result import page_result  # noqa: E402
from test_dashboard import CHROME, populate  # noqa: E402
from test_tracker import REPO, Vault, action  # noqa: E402

sys.path.insert(0, str(REPO / "system" / "scripts"))
import propose  # noqa: E402

REGISTER = "projects/_portfolio/people-register.md"

SCRIPT = r"""
<script>
(async()=>{
  const FILES=JSON.parse(document.getElementById("seed").textContent), LOG=[];
  VW={ async read(p){ if(!(p in FILES)) throw new Error("not found: "+p); return FILES[p]; },
       async write(p,t){ FILES[p]=t; LOG.push(["write",p]); }, async remove(p){ delete FILES[p]; LOG.push(["remove",p]); },
       async exists(p){ return p in FILES; }, async append(p,t){ FILES[p]=(FILES[p]||"")+t; LOG.push(["append",p]); } };
  VSTATE="ok"; needVault=async()=>true;   /* the page's own vault check can finish late and reset the fake vault (slow CI) */
  const wait=ms=>new Promise(r=>setTimeout(r,ms)), el=id=>document.getElementById(id), set=(id,v)=>{ el(id).value=v; };
  // no live server here, so nothing applies the proposals; do what apply would do to the register, in order
  const seen=new Set(), settle=async()=>{ await wait(60); await VQ; await wait(60); await VQ;
    for(const [op,k] of LOG) if(op==="write"&&/-dashboard(-\d+)?\.json$/.test(k)&&!seen.has(k)){ seen.add(k); const d=JSON.parse(FILES[k]); ((d.file_changes||{}).file_ops||[]).forEach(o=>{ if(o.op==="write") FILES[o.path]=o.content; }); } };
  const fillDlg=async(f,save=true)=>{ for(const [k,v] of Object.entries(f)) set("pd_"+k,v); if(save) el("pdSave").click(); };
  const typeIn=(box,v)=>{ const inp=box.querySelector("input"); inp.value=v; inp.dispatchEvent(new Event("input",{bubbles:true})); return [...box.querySelectorAll(".copt")].map(o=>[o.dataset.t,o.dataset.n]); };
  const click=(box,sel)=>box.querySelector(sel).dispatchEvent(new MouseEvent("mousedown",{bubbles:true}));
  const out={errors:[]};
  window.addEventListener("unhandledrejection",e=>out.errors.push("unhandled: "+String(e.reason&&e.reason.stack||e.reason)));
  try{
    // 0. before anything changes: the page and propose.py read and write the same format, and match the same way
    out.parity={text:peopleText(FILES["projects/_portfolio/people-register.md"],[{name:"Ann Lee",email:"a@x.example",aliases:["Annie","AL"],org:"X",role:"Lead",hidden:true,extra:{}},{name:"Bo Li|Wu",email:"",aliases:[],org:"",role:"",hidden:false,extra:{}}]),
      resolve:Object.fromEntries(window.__inputs.map(t=>[t,(r=>[r.status,r.name,r.candidates])(resolvePerson(t))]))};
    needVault=async()=>true;      // the page's own vault check finishes late and would reset the fake's state
    // 0b. BL-56: the People view and a page per person (before anything above changes the data)
    go("people","work"); /* #248: With work is a tab of four now (Everyone is the default) */ out.peopleHash=location.hash; out.rail=document.querySelector(".rail button[data-v=people]").getAttribute("aria-current"); out.heading=document.querySelector("#v-people h1").textContent;
    const prow=()=>[...document.querySelectorAll("#peopleTbl tbody tr")].map(tr=>[...tr.cells].map(c=>c.textContent.replace(/\s+/g," ").trim()));
    out.peopleRows=prow();
    { const cs=e=>e&&getComputedStyle(e); const a=document.querySelector("#peopleTbl td.num a.cntl");   // #190: right-aligned counts, not drawn as links
      out.numStyle=[cs(document.querySelector("#peopleTbl thead th.num")).textAlign,cs(document.querySelector("#peopleTbl tbody td.num")).textAlign,a?cs(a).textDecorationLine:"none"]; }
    out.ptabs=[...document.querySelectorAll("#ptabs [data-ptab]")].map(b=>[b.textContent.replace(/\s+/g," ").trim(),b.getAttribute("aria-selected")]);   // BL-138
    document.querySelector('#ptabs [data-ptab="none"]').click(); out.noneRows=prow(); out.noneHash=location.hash; document.querySelector('#ptabs [data-ptab="work"]').click();
    document.querySelector("#peopleTbl th[data-psort=oa]").click(); out.byActions=prow().map(r=>r[0]);
    document.querySelector("#peopleTbl th[data-psort=name]").click(); out.byName=prow().map(r=>r[0]);
    document.querySelector('#peopleTbl a[data-person="Alan Carter"]').click(); out.myWork=[VIEW,location.hash];
    go("people"); document.querySelector('#peopleTbl a[data-person="Omar Ali"]').click(); await wait(20);
    const pp=()=>document.querySelector("#v-person");
    out.omar=[VIEW,location.hash,PERSON,pp().querySelector("h1").textContent.trim(),pp().querySelector(".sub").textContent.replace(/\s+/g," ").trim(),pp().querySelector(".ppcounts").textContent.replace(/\s+/g," ").trim(),[...pp().querySelectorAll("table.ptbl tr[data-row] td.title")].map(td=>{ const c=td.cloneNode(true); c.querySelectorAll(".x,.wflag").forEach(n=>n.remove()); return c.textContent.trim(); }),[...pp().querySelectorAll(".pph")].map(h=>h.textContent.replace(/\s+/g," ").trim()),pp().querySelector(".crumb").textContent.replace(/\s+/g," ").trim(),document.querySelector(".rail button[data-v=people]").getAttribute("aria-current")];
    out.noScores=!/%|score|rating|on.?time/i.test(pp().textContent);
    document.querySelector("#v-person tr[data-row] a.rowid").click(); await wait(20); out.openedItem=[!!CUR,CUR&&CUR.id]; closePanel();
    history.back(); await wait(100); out.back=[VIEW,location.hash]; history.forward(); await wait(100); out.forward=[VIEW,PERSON,location.hash];
    out.parse=[parseHash("#person=Omar%20Ali").arg,parseHash("#person=Nobody%20Here"),parseHash("#people").v];
    go("person","Jane Doe"); out.jane=[pp().textContent.includes("Go-live moves two weeks"),pp().textContent.includes("Nothing open."),[...pp().querySelectorAll(".card h2")].map(h=>h.textContent.replace(/\s+/g," ").trim())];
    D.leads={"Sara E":[["ABC","Testing"]]}; go("person","Sara Example"); out.leads=[...pp().querySelectorAll(".card h2")].map(h=>h.textContent.trim()); out.leadsItem=[...pp().querySelectorAll(".card")].find(c=>c.querySelector("h2").textContent.startsWith("Workstreams led")).textContent.replace(/\s+/g," ").trim(); D.leads={};
    go("person","S. Example"); out.unregistered=[pp().querySelector("h1").textContent.trim(),pp().querySelector("#ppEdit").getAttribute("aria-label")]   /* BL-161: the pencil, named */;
    go("person","Nobody Here"); out.nobody=pp().textContent.replace(/\s+/g," ").trim();
    // links both ways: from Work, the detail panel and Review; the palette
    clearAllFilters(); WT="actions"; applyView("open"); go("work"); const wl=document.querySelector('#v-work td[data-f=o] a[data-person="Sara Example"]'); out.workLink=!!wl; wl.click(); out.workLinkWent=[VIEW,PERSON];
    go("work"); openRecord("actions",A.find(a=>a.o==="Sara Example").id); document.querySelector('#panel [data-pkp="o"]').click(); const pl=[...document.querySelectorAll('.pkpop .pkopt')].find(o=>/page$/.test(o.textContent.trim())); out.panelLink=pl&&pl.textContent.trim().replace(/^Open (.*)'s page$/,"$1"); closePicker("owner",false); closePanel();   /* BL-176: the owner chip's list ends with the person's page */
    out.reviewLink=revDetail({kind:"actions",rec:{o:"Omar Ali",due:null,pr:"Medium"}}).includes('data-person="Omar Ali"');
    out.palette=[ckItems("omar").filter(i=>i.g==="People").map(i=>[i.l,i.h]),ckItems("people").some(i=>i.g==="Go to"&&i.l==="People")];
    go("today");
    // 1. the People page (#248; Settings › People's old address opens it) shows the register and everyone on items, with what's missing
    go("settings","people"); out.mgrView=[VIEW,location.hash];
    out.mgr=[...document.querySelectorAll("#plRows tr[data-pn]")].map(tr=>[tr.dataset.pn,tr.cells[0].textContent.replace(/\s+/g," ").trim(),tr.cells[1].textContent.trim(),((REG.find(p=>p.name===tr.dataset.pn)||{}).aliases||[]).join(", ")]);
    // 2. add a person with the new-person dialog (the owner prompt's, ownerFinal; Settings › People's Add went with it); the name is required
    let added=askPerson({}).then(res=>res&&res.person?regAddPerson(res.person):null); await wait(20); out.dlgOpen=el("personDlg").open; el("pdSave").click(); out.needName=el("pdErr").textContent;
    set("pd_name","Sara"); el("pdSave").click(); out.dupName=el("pdErr").textContent;
    await fillDlg({name:"Priya Nair",email:"priya@northgate.example",aliases:"Priya, PN",org:"Northgate",role:"Architect"}); await added; await settle();
    out.afterAdd=REG.map(p=>p.name); out.dlgClosed=!el("personDlg").open;
    // 3. edit them (the name is read-only here; renaming is its own action)
    go("person","Priya Nair"); el("ppEdit").click(); await wait(20);   /* her page's Edit details (Settings › People's Edit has gone) */ out.editName=[el("pd_name").value,el("pd_name").readOnly,el("pdTitle").textContent];
    await fillDlg({role:"Lead architect"}); await settle(); out.afterEdit=REG.find(p=>p.name==="Priya Nair").role;
    // 4. the owner picker (BL-179: a new item is the peek, so it is the owner chip's list): typing filters, a stranger is offered
    //    as typed, and using it asks for the person's details (ownerFinal)
    const peekNew=async(k,t)=>{ go("work"); openNew(k); const id=CUR.nid; await pkCommit(k,id,{p:"ABC"},"Project","",""); return id; };
    const commitTitle=async(k,id,t)=>{ await pkCommit(k,id,{t},"Title","",t); await settle(); };
    const chip=f=>document.querySelector(`#panel [data-pkp="${f}"]`), q=v=>{ const i=document.querySelector(".pkpop .pkq"); i.value=v; i.dispatchEvent(new Event("input",{bubbles:true})); return [...document.querySelectorAll(".pkpop .pkopt")].map(o=>(o.querySelector("span")||o).firstChild.textContent.trim()); };
    let nid=await peekNew("actions"); chip("o").click(); await wait(20);
    out.pickPartial=q("sar"); out.pickStranger=q("Zed Quill");
    let pr=pkOwner("actions",nid,"Zed Quill",true); closePicker("owner",false); await wait(30); out.newDlg=[el("personDlg").open,el("pd_name").value,el("pdMatch").hidden]; await fillDlg({email:"zed@quill.example"}); await pr; await settle();
    out.pickedNew=[CUR.draft.o,REG.some(p=>p.name==="Zed Quill")];
    // 5. saving with a typed name: a known alias maps silently ...
    await pkOwner("actions",nid,"sara e",true); await commitTitle("actions",nid,"Picker test"); out.mapped=[CUR.draft.o,el("personDlg").open]; closePanel();
    // ... a likely match asks first, and remembers the alias on "Yes" ...
    nid=await peekNew("actions");
    pr=pkOwner("actions",nid,"Sarah Example",true); await wait(30); out.likelyDlg=[el("personDlg").open,el("pdMatch").hidden,[...document.querySelectorAll("#pdMatch [data-use]")].map(b=>b.dataset.use),el("pdRemember").checked];
    document.querySelector("#pdMatch [data-use]").click(); await pr; await commitTitle("actions",nid,"Likely test"); out.likelySaved=[CUR.draft.o,REG.find(p=>p.name==="Sara Example").aliases.includes("Sarah Example")]; closePanel();
    // ... a stranger asks for details ...
    nid=await peekNew("actions");
    pr=pkOwner("actions",nid,"Dan Smith",true); await wait(30); out.strangerDlg=[el("personDlg").open,el("pdMatch").hidden,el("pd_name").value]; await fillDlg({org:"Elsewhere"}); await pr; await commitTitle("actions",nid,"Stranger test");
    out.strangerSaved=[CUR.draft.o,(REG.find(p=>p.name==="Dan Smith")||{}).org]; closePanel();
    // ... and cancelling the prompt changes nothing
    nid=await peekNew("actions");
    pr=pkOwner("actions",nid,"Eve Nobody",true); await wait(30); document.querySelector("#personForm [value=cancel]").click(); await pr; await settle();
    out.cancelled=[CUR.draft.o==="Eve Nobody",REG.some(p=>p.name==="Eve Nobody"),!!CUR]; closePanel();
    // 5b. a decision's "Made by" is the same picker
    nid=await peekNew("decisions"); await pkCommit("decisions",nid,{srcIn:"Steering"},"Source","","Steering");
    out.decisionByChip=!!chip("o"); await pkOwner("decisions",nid,"jane",true); await commitTitle("decisions",nid,"Use the new API"); out.decisionBy=CUR.draft.by; closePanel();
    // 6. Review: an owner the register doesn't know is flagged (never mapped)
    out.reviewFlag=[revDetail({kind:"actions",rec:{o:"Nobody Known",due:null,pr:"Medium"}}).includes("not in the people register"),revDetail({kind:"actions",rec:{o:"Omar Ali",due:null,pr:"Medium"}}).includes("not in the people register"),revDetail({kind:"actions",rec:{o:"omar",due:null,pr:"Medium"}}).includes("not in the people register")];
    // 7. rename and merge: items and the register change together
    await renamePerson("Omar Ali","Omar Aly"); await settle(); out.renamed=[REG.map(p=>p.name).includes("Omar Aly"),REG.map(p=>p.name).includes("Omar Ali"),A.filter(a=>a.o==="Omar Aly").length];
    await renamePerson("S. Example","Sara Example"); await settle();
    out.merged=[REG.map(p=>p.name).includes("S. Example"),REG.find(p=>p.name==="Sara Example").aliases.includes("S. Example"),A.filter(a=>a.o==="Sara Example").map(a=>a.id)];
    // 8. removing from the list hides a name from the picker; items keep it; Restore brings it back
    out.beforeHide=peopleAll().includes("Jane Doe"); await regSetHidden("Jane Doe",true); await settle(); out.hidden=[peopleAll().includes("Jane Doe"),REG.find(p=>p.name==="Jane Doe").hidden];
    await regSetHidden("Jane Doe",false); await settle(); out.restored=peopleAll().includes("Jane Doe");
    // 8b. a register the page can't read (the live server not letting it): edited from the text last known, never from the template
    const regBefore=FILES[REGD.path], _read=VW.read; VW.read=async p=>{ if(p===REGD.path) throw new Error("read isn't allowed"); return _read.call(VW,p); };
    await regAddAlias("Omar Aly","OA"); await settle(); VW.read=_read;
    const lastP=[...LOG].reverse().find(([op,k])=>op==="write"&&/-dashboard(-\d+)?\.json$/.test(k))[1], fop=JSON.parse(FILES[lastP]).file_changes.file_ops[0];
    out.unreadable=[fop.previous===regBefore,fop.content.includes("OA"),fop.content.includes("Priya Nair"),REG.find(p=>p.name==="Omar Aly").aliases];
    // 8c. two register edits made before the first is applied: the second is built on the first's result, so neither is lost
    const before8c=FILES[REGD.path], fresh=()=>[...LOG].filter(([op,k])=>op==="write"&&/-dashboard(-\d+)?\.json$/.test(k)&&!seen.has(k)).map(([o,k])=>JSON.parse(FILES[k]).file_changes.file_ops[0]);
    await regAddAlias("Jane Doe","JD1"); await wait(60); await VQ; await regAddAlias("Jane Doe","JD2"); await wait(60); await VQ;
    const chain=fresh(); out.chained=[chain.length,chain[0].previous===before8c,chain[1].previous===chain[0].content,chain[1].content.includes("JD1")&&chain[1].content.includes("JD2")];
    await settle(); out.afterChain=[REG.find(p=>p.name==="Jane Doe").aliases];
    // ... and once applied, the next edit starts from the file again
    await regAddAlias("Jane Doe","JD3"); await wait(60); await VQ; const third=fresh()[0]; out.afterApply=third.previous===FILES[REGD.path]; await settle();
    out.registerNow=FILES["projects/_portfolio/people-register.md"];
  }catch(e){ out.errors.push(String(e&&e.stack||e)); }
  out.files=FILES; out.log=LOG;
  const pre=document.createElement("pre"); pre.id="result"; pre.textContent=JSON.stringify(out); document.body.appendChild(pre);
})();
</script>
"""

INPUTS = ["Sara Example", "sara example", "Sara", "Sara E", "SE", "sara.example@client.com", "Sara.Example@Client.com",
          "sara.example@other.com", "Example", "S Example", "Sara Exampl", "Sarah Example", "Jan Doe", "Omar", "Omar Ali (Enable)",
          "AC", "Alan", "Alan Carter", "Bob", "Priya Nair", "PN", "Priya", "S. Example", "TBC", "J D", "Doe", "x@y.z"]


@unittest.skipUnless(CHROME.exists(), "Google Chrome not installed")
class PeopleDashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = v = Vault()
        populate(v)
        v.propose("people-seed", [action(1, description="Review the SOW", owner="S. Example"),
                                  action(2, description="Agree rota", owner="Omar Ali", project="DEF")])
        v.run("apply")
        cls.before = v.snapshot()
        v.run(script="build_dashboard.py")
        cls.reg0 = (v.root / REGISTER).read_text(encoding="utf-8")
        seed = {rel: (v.root / rel).read_text(encoding="utf-8") for rel in ("system/config/settings.json", REGISTER)}
        html = (v.root / "dashboard.html").read_text(encoding="utf-8")
        tag = '<script type="application/json" id="seed">' + json.dumps(seed).replace("</", "<\\/") + "</script>"
        inputs = "<script>window.__inputs=" + json.dumps(INPUTS) + ";</script>"
        harness = v.root / "harness.html"
        harness.write_text(html.replace("</body>", tag + inputs + SCRIPT + "</body>"), encoding="utf-8")
        # dev-test-steadiness: in real time, waiting for the result (a virtual-time budget ran out under load)
        cls.r = json.loads(page_result(harness.as_uri()))

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def test_no_script_errors(self):
        self.assertEqual(self.r["errors"], [])

    def test_the_people_page_lists_the_register_and_flags_gaps(self):
        # the Settings line: Settings › People is gone; its address opens the People page (#248), whose Everyone tab is the register
        # and everyone on items. "needs details" replaced "not in register" there (#248); aliases are on the record, not a column.
        self.assertEqual(self.r["mgrView"], ["people", "#people"])
        rows = {n: (label, email, aliases) for n, label, email, aliases in self.r["mgr"]}
        self.assertIn("Sara Example", rows)
        self.assertEqual(rows["Sara Example"][1], "sara.example@client.com")
        self.assertIn("Sara, Sara E", rows["Sara Example"][2])
        self.assertIn("needs details", rows["S. Example"][0])                       # on items, with no email, organisation or role
        self.assertIn("You (Alan Carter)", rows["Alan Carter"][0])

    def test_add_and_edit_through_the_dialog(self):
        r = self.r
        self.assertTrue(r["dlgOpen"])
        self.assertEqual(r["needName"], "A full name is required.")
        self.assertEqual(r["dupName"], "Sara is already in the register as Sara Example.")
        self.assertIn("Priya Nair", r["afterAdd"])
        self.assertTrue(r["dlgClosed"])
        self.assertEqual(r["editName"], ["Priya Nair", True, "Edit Priya Nair"])
        self.assertEqual(r["afterEdit"], "Lead architect")

    def test_owner_picker_offers_matches_and_new_people(self):
        """BL-179: on a new item the owner is the peek's chip; its list filters as you type and offers a stranger as a new person.
        (BL-187: the list suggests aliases, emails and likely matches as the old combo did; test_peek_fixes covers those.)"""
        r = self.r
        self.assertIn("Sara Example", r["pickPartial"])                                        # plain typing filters
        self.assertIn("New person “Zed Quill”…", r["pickStranger"])                           # BL-187: the old combo's wording
        self.assertEqual(r["newDlg"], [True, "Zed Quill", True])                              # details only: no match step
        self.assertEqual(r["pickedNew"], ["Zed Quill", True])

    def test_counts_right_aligned_one_zero_style(self):
        r = self.r
        self.assertEqual(r["numStyle"], ["right", "right", "none"])                          # #190
        for row in r["peopleRows"] + r["noneRows"]:
            self.assertNotIn("—", row[5:9])                                                   # a zero is 0, never a dash (#248: the counts follow Email and Projects)

    def test_saving_a_typed_owner(self):
        r = self.r
        self.assertEqual(r["mapped"], ["Sara Example", False])                                 # alias → full name, no prompt
        self.assertEqual(r["likelyDlg"], [True, False, ["Sara Example"], True])               # offered first, remember checked
        self.assertEqual(r["likelySaved"], ["Sara Example", True])
        self.assertEqual(r["strangerDlg"], [True, True, "Dan Smith"])                          # no matches: the details form
        self.assertEqual(r["strangerSaved"], ["Dan Smith", "Elsewhere"])
        self.assertEqual(r["cancelled"], [False, False, True])                                 # cancel: nothing saved
        self.assertTrue(r["decisionByChip"])
        self.assertEqual(r["decisionBy"], "Jane Doe")

    def test_people_view(self):
        r = self.r
        # #248 (People page v2) deliberately changed the view: four tabs, the register's columns (Name, Email, Organisation, Role,
        # Projects, Actions, RAID, Decisions, Overdue, then the row's buttons) on every tab, and "needs details" for a record
        # missing an email, organisation or role (there is no "not in register": a name on an item is in the register).
        self.assertEqual((r["peopleHash"], r["rail"], r["heading"]), ("#people/work", "page", "People"))
        rows = {x[0].replace(" needs details", ""): x[1:] for x in r["peopleRows"]}
        self.assertEqual(r["peopleRows"][0][0], "You (Alan Carter)")                           # Alan first on With work
        self.assertEqual(rows["Omar Ali"][:8], ["omar@def.example", "Enable", "Project manager", "Example Programme Digital Enablement", "2", "0", "0", "0"])   # Projects: every project he is on (ABC names him a stakeholder)
        self.assertEqual(rows["Sara Example"][1:8], ["Example Client Ltd", "Delivery lead", "Example Programme", "1", "0", "0", "0"])
        self.assertNotIn("Jane Doe", rows)                                                     # BL-138: a made decision alone is history
        none = {x[0].replace(" needs details", ""): x[1:] for x in r["noneRows"]}
        self.assertEqual(none["Jane Doe"][3:8], ["Example Programme", "0", "0", "0", "0"])      # on Nothing assigned: projects, nothing open
        self.assertEqual(r["noneHash"], "#people/none")
        self.assertEqual([t[1] for t in r["ptabs"]], ["false", "true", "false", "false"])
        self.assertEqual(r["ptabs"][1][0], f"With work {len(r['peopleRows'])}")
        self.assertEqual(r["ptabs"][2][0], f"Nothing assigned {len(r['noneRows'])}")
        self.assertEqual(rows["You (Alan Carter)"][7], "1")                                     # one overdue action
        self.assertIn("needs details", [x[0] for x in r["peopleRows"] if x[0].startswith("S. Example")][0])
        self.assertNotIn("not in register", " ".join(x[0] for x in r["peopleRows"] + r["noneRows"]))
        self.assertEqual(r["byActions"][1], "Omar Ali")                                        # sorted by open actions, most first
        self.assertEqual([n.replace(" needs details", "") for n in r["byName"]][1:],
                         ["Omar Ali", "S. Example", "Sara Example"])
        self.assertEqual(r["myWork"], ["work", "#work=actions&v=mine"])                   # Alan's own page is Work on the Mine view (BL-77)

    def test_person_page(self):
        r = self.r
        view, hash_, person, h1, sub, counts, items, groups, crumb, rail = r["omar"]
        self.assertEqual((view, hash_, person, h1), ("person", "#person=Omar%20Ali", "Omar Ali", "Omar Ali"))
        self.assertEqual(sub, "Enable · Project manager · omar@def.example")
        self.assertEqual(counts, "2 open actions0 open risks and issues0 overdueProjects Digital Enablement")
        self.assertEqual(items, ["Agree pilot success criteria", "Agree rota"])                # dated before undated
        self.assertEqual(groups, ["Digital Enablement"])
        self.assertEqual((crumb, rail), ("People›Omar Ali", "page"))
        self.assertTrue(r["noScores"])                                                          # counts only
        self.assertEqual(r["openedItem"], [True, "DEF-A-001"])
        self.assertEqual((r["back"], r["forward"]), (["people", "#people/work"], ["person", "Omar Ali", "#person=Omar%20Ali"]))   # #248: the tab is in the address
        self.assertEqual(r["parse"], ["Omar Ali", None, "people"])
        self.assertEqual(r["jane"], [True, True, ["Open work", "Closed in the last 14 days", "Decisions made · last 90 days"]])   # BL-56 phase 2
        self.assertEqual(r["leads"], ["Open work · 1", "Closed in the last 14 days", "Decisions made", "Workstreams led"])
        self.assertEqual(r["leadsItem"], "Workstreams ledExample Programme Testing")                          # the lead's alias maps to the person
        self.assertEqual(r["unregistered"], ["S. Example not in register", "Add details"])
        self.assertIn("Nobody called “Nobody Here” owns an item.", r["nobody"])

    def test_names_link_to_their_page(self):
        r = self.r
        self.assertTrue(r["workLink"])
        self.assertEqual(r["workLinkWent"], ["person", "Sara Example"])
        self.assertEqual(r["panelLink"], "Sara Example")
        self.assertTrue(r["reviewLink"])
        self.assertEqual(r["palette"], [[["Omar Ali", "Enable · Project manager"]], True])

    def test_workstream_leads_come_from_a_workstreams_table_when_there_is_one(self):
        v = Vault()
        try:
            populate(v)
            v.run(script="build_dashboard.py")
            self.assertEqual(self.data(v)["leads"], {})                                           # no workstreams yet: nothing
            mk = lambda n, p, name, lead, st="Active": {"n": n, "op": "new", "table": "workstreams", "decision": "approved",  # noqa: E731
                                                         "values": {"project": p, "name": name, "lead": lead, "status": st, "source": "t"}}
            v.propose("ws", [mk(1, "ABC", "Testing", "Sara E"), mk(2, "ABC", "Data", "Sara E", "Closed"),
                             mk(3, "DEF", "Pilot", "Omar Ali"), mk(4, "DEF", "Run", "")])       # BL-58: the real table
            v.run("apply")
            v.run(script="build_dashboard.py")
            self.assertEqual(self.data(v)["leads"], {"Sara E": [["ABC", "Testing"]], "Omar Ali": [["DEF", "Pilot"]]})
        finally:
            v.cleanup()

    @staticmethod
    def data(v):
        html = (v.root / "dashboard.html").read_text(encoding="utf-8")
        return json.loads(re.search(r'<script type="application/json" id="data">(.*?)</script>', html, re.S).group(1))

    def test_review_flags_unknown_owners(self):
        self.assertEqual(self.r["reviewFlag"], [True, False, False])

    def test_rename_merge_and_hide(self):
        r = self.r
        self.assertEqual(r["renamed"], [True, False, 2])
        self.assertEqual(r["merged"][:2], [False, True])
        self.assertEqual(len(r["merged"][2]), 2)                                               # her own and S. Example's (BL-179: the two made here are staged, not yet in the list)
        self.assertEqual(r["beforeHide"], True)
        self.assertEqual(r["hidden"], [False, True])
        self.assertTrue(r["restored"])

    def test_register_edits_made_before_the_first_applies_build_on_each_other(self):
        self.assertEqual(self.r["chained"], [2, True, True, True])
        self.assertEqual(self.r["afterChain"], [["Jane", "JD", "JD1", "JD2"]])
        self.assertTrue(self.r["afterApply"])

    def test_an_unreadable_register_is_edited_from_the_last_known_text(self):
        self.assertEqual(self.r["unreadable"], [True, True, True, ["Omar", "OA"]])

    def test_the_page_and_propose_py_agree(self):
        v = self.v
        for text in INPUTS:
            py = json.loads(v.run("people", "resolve", text, script="propose.py").stdout)
            js = self.r["parity"]["resolve"][text]
            self.assertEqual([py["status"], py["name"], py["candidates"]], js, text)
        self.assertEqual(self.r["parity"]["text"], propose.people_text(self.reg0, [
            {"name": "Ann Lee", "email": "a@x.example", "aliases": ["Annie", "AL"], "org": "X", "role": "Lead", "hidden": True,
             "extra": {}},
            {"name": "Bo Li|Wu", "email": "", "aliases": [], "org": "", "role": "", "hidden": False, "extra": {}}]))

    def test_proposals_apply_and_undo(self):
        v = self.v
        order = []
        for op, path in self.r["log"]:
            if op == "write" and re.search(r"-dashboard(-\d+)?\.json$", path) and path not in order:
                order.append(path)
        for i, path in enumerate(order, 1):                                                    # filename order = made order
            (v.root / f"system/staging/proposed-2026-10-07-{i:04d}-dashboard.json").write_text(
                self.r["files"][path], encoding="utf-8")
        v.run("apply")
        reg = propose.people_parse((v.root / REGISTER).read_text(encoding="utf-8"))
        by = {p["name"]: p for p in reg}
        self.assertEqual((by["Priya Nair"]["role"], by["Priya Nair"]["aliases"], by["Priya Nair"]["org"]),
                         ("Lead architect", ["Priya", "PN"], "Northgate"))
        # BL-179: "SE" was remembered by the Create form's combo (picking a suggested alias while typing); the peek's list has no such step
        self.assertIn("Sarah Example", by["Sara Example"]["aliases"])
        self.assertIn("S. Example", by["Sara Example"]["aliases"])                              # a merge keeps the old name
        self.assertIn("Omar Aly", by)
        self.assertEqual(by["Omar Aly"]["aliases"], ["Omar", "OA"])
        self.assertNotIn("Omar Ali", by)
        self.assertEqual(by["Dan Smith"]["org"], "Elsewhere")
        owners = {a["description"]: a["owner"] for a in v.rows("actions")}
        self.assertEqual(owners["Review the SOW"], "Sara Example")
        self.assertEqual(owners["Agree rota"], "Omar Aly")
        self.assertEqual(owners["Picker test"], "Sara Example")
        self.assertEqual(owners["Stranger test"], "Dan Smith")
        self.assertNotIn("Cancelled test", owners)
        self.assertEqual({d["decision"]: d["made_by"] for d in v.rows("decisions")}["Use the new API"], "Jane Doe")
        self.assertEqual((v.root / REGISTER).read_text(encoding="utf-8"), self.r["registerNow"])   # the page's file = the real one
        v.run("undo")
        data, files = v.snapshot()
        files.pop("harness.html", None)                                                          # the test's own page
        self.assertEqual((data, files), self.before)                                             # everything back exactly


class _EmailBase(unittest.TestCase):
    """Shared set-up for the Draft email tests (BL-83): headless Chrome with a fixed clock and fictional items."""

    TODAY = "2026-10-08"

    @classmethod
    def setUpClass(cls):
        from test_insight import chrome
        cls.chrome = staticmethod(chrome)
        cls.v = Vault()
        populate(cls.v)
        cls.v.run(script="build_dashboard.py")

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def probe(self, script):
        out, errors = self.chrome(self.v, script, name="email")
        self.assertEqual(errors, [])
        self.assertIsNotNone(out, "the page didn't finish")
        self.assertNotIn("error", out, out.get("error"))
        return out

    SETUP = """
      const IT=(k,id,p,t,due,pr,extra)=>({k,id,p,t,due,pr,...extra});
      const items=[IT("actions","ORX-A-004","ORX","Book the pilot room","2026-10-20","Medium"),
                   IT("actions","ORX-A-003","ORX","Send the SOW","2026-10-02","Urgent"),
                   IT("raid","ORX-001","ORX","Vendor may exit","2026-10-07","High",{type:"Risk",resp:"",upd:"Talking to two alternatives"}),
                   IT("actions","FAL-A-009","FAL","Confirm the data owner","2026-10-11","Low"),
                   IT("actions","FAL-A-010","FAL","Draft the rota",null,"Medium"),
                   IT("actions","ORX-A-005","ORX","Ready tomorrow","2026-10-09","Medium"),
                   IT("actions","ORX-A-006","ORX","Due today","2026-10-08","Medium")];
      const base={name:"Sara Example",email:"sara@client.example",items,today:"2026-10-08",dueSoon:7,names:{ORX:"Orchard pilot",FAL:"Falcon platform"},from:"Alan"};
      const at=(h,m)=>new Date(2026,9,8,h,m||0);
      const mk=o=>draftEmail({...base,now:at(9),...o});
      const parse=h=>new DOMParser().parseFromString(h,"text/html");
    """



class DraftEmailBuilderTests(_EmailBase):
    """BL-83 item 1: draftEmail() is a pure function."""

    def test_the_greeting_follows_the_time_and_uses_the_first_name(self):
        o = self.probe(self.SETUP + """
          const g=(h,m,x)=>parse(mk({now:at(h,m),...(x||{})}).html).querySelector("p").textContent;
          window.OUT={nine:g(9),noon_1:g(11,59),noon:g(12),late_1:g(17,59),six:g(18),one:g(13),seven:g(19),night:g(23,30),early:g(0,5),
            fallback:parse(mk({first:"",name:"Priya Nair"}).html).querySelector("p").textContent, given:parse(mk({first:"Pri"}).html).querySelector("p").textContent};""")
        self.assertEqual((o["nine"], o["early"]), ("Good morning, Sara,", "Good morning, Sara,"))
        self.assertEqual((o["noon_1"], o["noon"]), ("Good morning, Sara,", "Good afternoon, Sara,"))
        self.assertEqual((o["one"], o["late_1"]), ("Good afternoon, Sara,", "Good afternoon, Sara,"))
        self.assertEqual((o["six"], o["seven"], o["night"]), ("Good evening, Sara,",) * 3)
        self.assertEqual((o["fallback"], o["given"]), ("Good morning, Priya,", "Good morning, Pri,"))   # a given first name wins; else the first word

    def test_the_subject_for_one_project_several_and_a_single_item(self):
        o = self.probe(self.SETUP + """
          const orx=items.filter(i=>i.p==="ORX"), s=x=>mk(x).subject;
          window.OUT={several:s({}), one:s({items:orx}), single:s({items:[orx[1]]}), noOverdue:s({items:[orx[0],orx[3]]}), picked:s({picked:new Set(["actions:FAL-A-009","actions:FAL-A-010"])}), none:s({picked:new Set()})};""")
        self.assertEqual(o["several"], "FAL / ORX · Update request: 7 open items (2 overdue)")        # codes sorted, joined with " / "
        self.assertEqual(o["one"], "ORX · Update request: 5 open items (2 overdue)")
        self.assertEqual(o["single"], "ORX-A-003 · Update request")
        self.assertEqual(o["noOverdue"], "ORX · Update request: 2 open items")
        self.assertEqual(o["picked"], "FAL · Update request: 2 open items")                          # only what is ticked counts
        self.assertEqual(o["none"], "Update request")

    def test_each_block_has_the_code_and_name_and_the_items_are_ordered(self):
        o = self.probe(self.SETUP + """
          const d=parse(mk({}).html), heads=[...d.querySelectorAll("p b")].map(b=>b.parentElement.textContent), tables=[...d.querySelectorAll("table")];
          window.OUT={heads:heads.filter(h=>/Orchard|Falcon/.test(h)), tables:tables.length,
            order:tables.map(t=>[...t.querySelectorAll("tr")].slice(1).map(r=>r.cells[0].textContent)), headers:[...tables[0].querySelectorAll("th")].map(h=>h.textContent)};""")
        self.assertEqual(o["heads"], ["Falcon platform", "Orchard pilot"])                    # the project's name, never its code (BL-101)
        self.assertEqual(o["headers"], ["ID", "Item", "Due", "Priority"])
        self.assertEqual(o["order"][0], ["FAL-A-009", "FAL-A-010"])                                  # dated before undated
        self.assertEqual(o["order"][1], ["ORX-A-003", "ORX-001", "ORX-A-006", "ORX-A-005", "ORX-A-004"])   # overdue (oldest first), then soonest

    def test_overdue_due_soon_and_urgent_are_marked_in_words_and_colour(self):
        o = self.probe(self.SETUP + """
          const d=parse(mk({}).html), row=id=>[...d.querySelectorAll("tr")].find(r=>r.cells[0]&&r.cells[0].textContent===id), due=id=>row(id).cells[2], pr=id=>row(id).cells[3];
          const st=(el)=>({colour:el.style.color,bold:el.style.fontWeight==="bold"});
          const dueOf=id=>{ const c=due(id); return {text:c.textContent, ...st(c), span:!!c.querySelector("span")}; };   /* #183: the colour is on the cell, never a span */
          window.OUT={over:dueOf("ORX-A-003"), overRisk:dueOf("ORX-001"), today:dueOf("ORX-A-006"), tomorrow:dueOf("ORX-A-005"), inDays:dueOf("FAL-A-009"), later:dueOf("ORX-A-004"), none:dueOf("FAL-A-010"),
            urgent:pr("ORX-A-003").innerHTML, high:pr("ORX-001").textContent, colours:DE_COLOURS};""")
        self.assertEqual((o["over"]["text"], o["over"]["colour"], o["over"]["bold"]), ("02-10-2026" + "6 days overdue", "rgb(179, 38, 30)", True))
        self.assertFalse(any(o[k]["span"] for k in ("over", "overRisk", "today", "tomorrow", "inDays", "later", "none")))
        self.assertEqual(o["overRisk"]["text"], "07-10-20261 day overdue")                           # singular
        self.assertEqual((o["today"]["text"], o["tomorrow"]["text"], o["inDays"]["text"]), ("08-10-2026due today", "09-10-2026due tomorrow", "11-10-2026due in 3 days"))
        self.assertEqual((o["inDays"]["colour"], o["inDays"]["bold"]), ("rgb(138, 90, 0)", False))    # amber, in words as well
        self.assertEqual((o["later"]["text"], o["later"]["colour"]), ("20-10-2026", "rgb(30, 31, 30)"))   # nothing to say: the normal ink
        self.assertEqual(o["none"]["text"], "No date")
        self.assertIn("<b", o["urgent"])
        self.assertEqual(o["high"], "High")                                                          # only Urgent is bold

    def test_the_colour_pairs_meet_contrast_on_white(self):
        o = self.probe(self.SETUP + "window.OUT={c:DE_COLOURS};")
        c = o["c"]

        def lum(h):
            r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
            f = lambda v: v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4   # noqa: E731
            return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)

        def ratio(a, b):
            x, y = lum(a), lum(b)
            return (max(x, y) + 0.05) / (min(x, y) + 0.05)
        for name in ("red", "amber", "ink", "muted"):
            self.assertGreaterEqual(ratio(c[name], c["white"]), 4.5, name)
            self.assertGreaterEqual(ratio(c[name], c["head"]), 4.5, name + " on the header row")
        self.assertEqual((c["red"], c["amber"], c["ink"], c["head"], c["rule"]), ("#B3261E", "#8A5A00", "#1E1F1E", "#F1F3F4", "#D9D9E0"))

    def test_the_html_is_plain_enough_for_outlook(self):
        o = self.probe(self.SETUP + r"""
          const html=mk({includeUpdate:true,replyBy:"2026-10-16"}).html, d=parse(html), all=[...d.body.querySelectorAll("*")].filter(e=>e.tagName!=="TBODY");   /* the parser adds tbody; the email doesn't have it */
          window.OUT={n:all.length, noStyle:all.filter(e=>!e.getAttribute("style")&&e.tagName!=="BR").map(e=>e.tagName), classes:all.filter(e=>e.hasAttribute("class")||e.hasAttribute("id")).length,
            vars:/var\(|flex|grid|<img|<style|<link|<script|@font-face|class=/i.test(html), tags:[...new Set(all.map(e=>e.tagName))].sort(),
            font:all.filter(e=>!/Calibri,Arial,sans-serif/.test(e.getAttribute("style")||"")&&["P","TD","TH","DIV","TABLE"].includes(e.tagName)).length,
            table:[...d.querySelectorAll("table")].map(t=>[t.getAttribute("cellpadding"),t.getAttribute("cellspacing"),/border-collapse:collapse/.test(t.getAttribute("style")||"")]),
            cellRules:[...d.querySelectorAll("td,th")].every(c=>/border-bottom:1px solid #D9D9E0/i.test(c.getAttribute("style")||""))};""")
        self.assertGreater(o["n"], 30)
        self.assertEqual(o["noStyle"], [])                                                          # every element carries its own style
        self.assertEqual((o["classes"], o["vars"], o["font"]), (0, False, 0))                       # no classes, ids, variables, flexbox or images
        self.assertEqual(o["tags"], ["B", "BR", "DIV", "I", "P", "TABLE", "TD", "TH", "TR"])          # #183: what Outlook's create-draft takes; no span
        self.assertTrue(all(t == ["6", "0", True] for t in o["table"]))
        self.assertTrue(o["cellRules"])                                                             # a bottom border on every cell

    def test_raid_rows_show_type_and_response_and_the_latest_update_only_when_asked(self):
        o = self.probe(self.SETUP + """
          const a=mk({}), b=mk({includeUpdate:true});
          window.OUT={a:a.html, b:b.html, ta:a.text, tb:b.text};""")
        self.assertIn("Risk:", o["a"])
        self.assertIn("Response: none recorded yet", o["a"])
        self.assertNotIn("Talking to two alternatives", o["a"] + o["ta"])                           # off by default
        self.assertIn("Latest update: Talking to two alternatives", o["b"] + "")
        self.assertIn("Latest update: Talking to two alternatives", o["tb"])

    def test_the_reply_by_sentence_and_the_closing(self):
        o = self.probe(self.SETUP + """
          const a=mk({replyBy:"2026-10-16"}), b=mk({});
          window.OUT={a:parse(a.html).body.textContent, ta:a.text, b:parse(b.html).body.textContent, tb:b.text};""")
        self.assertIn("It would be helpful to hear back by Friday 16-10-2026.", o["a"])
        self.assertIn("It would be helpful to hear back by Friday 16-10-2026.", o["ta"])
        self.assertNotIn("hear back by", o["b"] + o["tb"])
        self.assertIn("Could you let me know where each one stands, and flag anything that's blocking you or that you need from me?", o["b"])
        self.assertTrue(o["b"].rstrip().endswith("Kind regards,Alan"))                              # the sign-off is Alan's first name

    def test_the_plain_text_is_the_same_email_with_the_table_as_aligned_lines(self):
        o = self.probe(self.SETUP + "const r=mk({}); window.OUT={t:r.text, to:r.to, n:r.items.length};")
        lines = o["t"].split("\n")
        self.assertEqual(lines[0], "Good morning, Sara,")
        self.assertIn("Falcon platform", lines)
        self.assertIn("Orchard pilot", lines)
        row = next(x for x in lines if "ORX-A-003" in x)
        self.assertEqual(row, "  ORX-A-003  Send the SOW  |  02-10-2026 (6 days overdue)  |  Urgent")
        self.assertEqual(o["t"].rstrip().split("\n")[-2:], ["Kind regards,", "Alan"])
        self.assertEqual((o["to"], o["n"]), ("sara@client.example", 7))


class DraftEmailPopupTests(_EmailBase):
    """BL-83 item 2: the popup, the safeguard for outside addresses, the reply-by picker and copying (a stubbed clipboard)."""

    PREP = r"""
      S.ownDomains=["brightwater.example"]; S.me="Alan Carter";
      const WRITES=[]; VW={read:async()=>"",write:async(...a)=>WRITES.push(["write",...a]),remove:async(...a)=>WRITES.push(["remove",...a]),exists:async()=>false,append:async(...a)=>WRITES.push(["append",...a]),upload:async()=>WRITES.push(["upload"])};
      const realApi=api; api=async(...a)=>{ WRITES.push(["api",...a]); return {ok:true}; };
      const mkA=(id,t,due,client,extra)=>({id,p:"ABC",t,ws:"",o:"Sara Example",pr:"Medium",due,st:"Open",raised:"2026-09-01",closed:null,upd:"",client:!!client,cm:"",src:"ABC Example Programme/minutes/2026-10-01 Steering.docx",...extra});
      A.length=0; R.length=0;
      A.push(mkA("ABC-A-101","Send the revised SOW","2026-10-02",true,{pr:"Urgent",upd:"Waiting on legal"}), mkA("ABC-A-102","Internal budget note",TODAY,false), mkA("ABC-A-103","Client workshop booked","2099-01-01",true),
             mkA("ABC-A-104","Confidential pricing review","2099-01-02",true,{upd:"Marked CONFIDENTIAL by legal"}), mkA("ABC-A-105","From a plan","2099-01-03",true,{src:"ABC Example Programme/documents/Plans/2026-09-01 Plan.md"}));
      R.push({id:"ABC-001",p:"ABC",type:"Issue",t:"Test licences not ordered",ws:"",o:"Sara Example",resp:"",due:null,imp:"Medium",lik:"High",pr:"High",st:"Open",raised:"2026-09-01",client:false,cm:"",src:"x",upd:""});
      REG.length=0; REG.push({name:"Sara Example",email:"sara@brightwater.example",aliases:[],org:"",role:"",extra:{}});
      const who=()=>({picked:[...DE.picked].sort(),outside:DE.outside,tags:[...document.querySelectorAll("#deInc .tag")].length,items:[...document.querySelectorAll("#deInc label.it")].map(l=>l.querySelector("span").textContent.split(" · ")[0])});
      const text=()=>document.getElementById("dePrev").innerText;
    """

    def test_the_popup_is_built_in_the_order_the_backlog_gives(self):
        o = self.probe(self.PREP + """
          openDraftEmail("Sara Example"); const d=document.getElementById("deDlg"), body=document.getElementById("deBody");
          const order=[...body.querySelectorAll("#deTo,#deSubj,#deInc,#deUpd,#deReply,#dePrev,#deCopyHtml,#deCopyText,#deDone")].map(e=>e.id);
          window.OUT={open:d.open, title:document.getElementById("deTitle").textContent, order, to:document.getElementById("deTo").textContent, copyTo:!!document.getElementById("deCopyTo"),
            subj:document.getElementById("deSubj").value, editable:document.getElementById("dePrev").isContentEditable, ro:document.getElementById("deReply").readOnly, who:who(),
            white:getComputedStyle(document.getElementById("dePrev")).backgroundColor, sent:/Nothing is sent/.test(d.textContent), preview:text().slice(0,40)};""")
        self.assertEqual((o["open"], o["title"]), (True, "Draft email: Sara Example"))
        self.assertEqual(o["order"], ["deTo", "deSubj", "deInc", "deUpd", "deReply", "dePrev", "deCopyHtml", "deCopyText", "deDone"])
        self.assertEqual((o["to"], o["copyTo"]), ("sara@brightwater.example", True))
        self.assertTrue(o["editable"] and o["ro"])                                                   # the preview edits in place; the date is a read-only picker
        self.assertEqual(o["white"], "rgb(255, 255, 255)")
        self.assertTrue(o["sent"])
        self.assertRegex(o["subj"], r"^ABC · Update request: 4 open items \(1 overdue\)$")           # the confidential and documents items are left out

    def test_an_own_domain_has_everything_ticked_an_outside_address_only_client_visible_items(self):
        o = self.probe(self.PREP + """
          openDraftEmail("Sara Example"); const own=who(); document.getElementById("deDlg").close();
          REG[0].email="sara@client.example"; openDraftEmail("Sara Example"); const outside=who(), noteOut=document.querySelector("#deBody .denote").textContent; 
          const first=document.querySelector('#deInc input[data-deit="actions:ABC-A-102"]'); first.click(); const ticked=who().picked, subj=document.getElementById("deSubj").value, internalNow=text().includes("Internal budget note"); document.getElementById("deDlg").close();
          REG[0].email=""; openDraftEmail("Sara Example"); const none=who(), noteNone=document.querySelector("#deBody .denote").textContent; document.getElementById("deDlg").close();
          S.ownDomains=["client.example"]; REG[0].email="SARA@Client.Example"; openDraftEmail("Sara Example"); const caps=who();
          window.OUT={own,outside,noteOut,ticked,subj,internalNow,none,noteNone,caps};""")
        every = ["actions:ABC-A-101", "actions:ABC-A-102", "actions:ABC-A-103", "raid:ABC-001"]
        self.assertEqual((o["own"]["picked"], o["own"]["outside"], o["own"]["tags"]), (every, False, 0))
        self.assertEqual((o["outside"]["picked"], o["outside"]["outside"]), (["actions:ABC-A-101", "actions:ABC-A-103"], True))   # not client-visible: unticked
        self.assertEqual(o["outside"]["tags"], 2)                                                    # and tagged "internal"
        self.assertIn("outside your own domains", o["noteOut"])
        self.assertEqual(o["ticked"], ["actions:ABC-A-101", "actions:ABC-A-102", "actions:ABC-A-103"])   # ticking one adds it
        self.assertTrue(o["internalNow"])
        self.assertIn("3 open items", o["subj"])
        self.assertEqual(o["none"]["picked"], ["actions:ABC-A-101", "actions:ABC-A-103"])               # no address: treated as outside
        self.assertIn("no email address on record", o["noteNone"].lower())
        self.assertEqual(o["caps"]["picked"], every)                                                  # the domain match ignores case

    def test_confidential_items_documents_sources_and_updates_never_appear_unless_ticked(self):
        o = self.probe(self.PREP + """
          openDraftEmail("Sara Example"); const html=document.getElementById("dePrev").innerHTML, plain=text(), left=[...document.querySelectorAll("#deBody .denote")].map(n=>n.textContent).join(" ");
          document.getElementById("deUpd").click(); const withUpd=text();
          window.OUT={html,plain,left,withUpd,ids:who().items};""")
        for gone in ("Confidential pricing review", "From a plan", "ABC-A-104", "ABC-A-105", "Steering.docx", "documents/", "Plans"):
            self.assertNotIn(gone, o["html"] + o["plain"], gone)
        self.assertEqual(o["ids"], ["ABC-A-101", "ABC-A-102", "ABC-A-103", "ABC-001"])               # not even offered
        self.assertIn("2 items left out", o["left"])
        self.assertNotIn("Waiting on legal", o["plain"])                                             # the latest update is off by default
        self.assertIn("Waiting on legal", o["withUpd"])                                              # and on when ticked

    def test_the_reply_by_picker_refuses_the_past_and_adds_the_sentence(self):
        o = self.probe(self.PREP + """
          openDraftEmail("Sara Example"); document.querySelector('[data-cal="deReply"]').click(); const cal=document.querySelector("#deDlg .cal");
          const days=[...cal.querySelectorAll(".cg button")], past=days.filter(b=>toIso(b.getAttribute("aria-label"))<TODAY), fut=days.filter(b=>toIso(b.getAttribute("aria-label"))>=TODAY);
          const state={inDialog:!!cal, past:past.length, pastOff:past.every(b=>b.disabled), futOn:fut.every(b=>!b.disabled), todayBtn:[...cal.querySelectorAll(".cf button")].map(b=>b.dataset.v)};
          const pick=fut[fut.length-1]; pick.click(); const val=document.getElementById("deReply").value, iso=toIso(val), sentence=text();
          document.querySelector('[data-cal="deReply"]').click(); [...document.querySelectorAll("#deDlg .cal .cf button")].find(b=>b.dataset.v==="").click();
          window.OUT={state,val,iso,hasSentence:sentence.includes("It would be helpful to hear back by"), dated:sentence.includes(val), cleared:document.getElementById("deReply").value, gone:!text().includes("hear back by"), today:TODAY};""")
        s = o["state"]
        self.assertTrue(s["inDialog"])                                                                # the popup opens inside the dialog, so it can be used
        self.assertTrue(s["pastOff"] and s["futOn"])
        self.assertEqual(s["todayBtn"][0], f"{o['today'][8:]}-{o['today'][5:7]}-{o['today'][:4]}")      # Today is the first choice
        self.assertGreaterEqual(o["iso"], o["today"])
        self.assertTrue(o["hasSentence"] and o["dated"])                                              # with a DD-MM-YYYY date
        self.assertEqual((o["cleared"], o["gone"]), ("", True))

    def test_the_calendars_earliest_day_option_works_beside_the_latest(self):
        o = self.probe("""
          document.body.insertAdjacentHTML("beforeend",'<span class="dwrap"><input id="tmin" type="text" readonly data-pick data-min="2099-05-10" data-max="2099-05-20" value="15-05-2099"><button type="button" class="dbtn" data-cal="tmin">c</button></span>');
          document.querySelector('[data-cal="tmin"]').click(); const cal=document.querySelector(".cal"), on=[...cal.querySelectorAll(".cg button")].filter(b=>!b.disabled).map(b=>b.textContent);
          cal.querySelector('.cg button[tabindex="0"]').dispatchEvent(new KeyboardEvent("keydown",{key:"PageUp",bubbles:true})); const afterPgUp=[...document.querySelectorAll(".cal .cg button")].filter(b=>!b.disabled).length;
          window.OUT={on, afterPgUp, today:[...cal.querySelectorAll(".cf button")][0].dataset.v};""")
        self.assertEqual(o["on"], [str(n) for n in range(10, 21)])                                    # only the 10th to the 20th
        self.assertGreater(o["afterPgUp"], 0)                                                         # a month back is clamped into range

    def test_copy_email_puts_html_and_plain_text_together_and_takes_the_edits(self):
        o = self.probe(self.PREP + """
          const clip=[]; let seen=null; const till=async f=>{ for(let i=0;i<400&&!f();i++) await new Promise(r=>setTimeout(r,25)); };   /* wait for the copy, not a fixed time (steady under load) */
           Object.defineProperty(navigator,"clipboard",{configurable:true,value:{ write:async items=>{ const it=items[0]; seen={types:[...it.types||Object.keys(it.__t)]}; clip.push([await it.__t["text/html"].text(),await it.__t["text/plain"].text()]); }, writeText:async t=>clip.push(["",t]) }});
          window.ClipboardItem=function(map){ this.__t=map; this.types=Object.keys(map); };
          openDraftEmail("Sara Example"); const prev=document.getElementById("dePrev"); prev.querySelector("p").textContent="Hi Sara, quick one before our call,"; prev.dispatchEvent(new Event("input",{bubbles:true}));
          document.getElementById("deCopyHtml").click(); await till(()=>clip.length); const rich=clip.pop(), msg=document.getElementById("deMsg").textContent, label=document.getElementById("deCopyHtml").textContent;
          document.getElementById("deCopyText").click(); await till(()=>clip.length); const plain=clip.pop();
          document.getElementById("deCopySubj").click(); await till(()=>clip.length); const subj=clip.pop(); document.getElementById("deCopyTo").click(); await till(()=>clip.length); const to=clip.pop();
          window.OUT={types:seen&&seen.types, htmlHas:rich[0].includes("Hi Sara, quick one before our call,"), htmlTable:rich[0].includes("<table"), textHas:rich[1].includes("Hi Sara, quick one before our call,"),
            plainHas:plain[1].includes("Hi Sara, quick one"), msg, label, subj:subj[1], to:to[1], writes:WRITES.length};""")
        self.assertEqual(sorted(o["types"]), ["text/html", "text/plain"])                              # both formats, together
        self.assertTrue(o["htmlHas"] and o["htmlTable"] and o["textHas"])                              # what is on screen, edits included
        self.assertTrue(o["plainHas"])
        self.assertIn("Copied", o["msg"])
        self.assertEqual(o["label"], "Copied")                                                         # BL-136: a drawn tick (an svg) and "Copied"
        self.assertEqual((o["subj"], o["to"]), ("ABC · Update request: 4 open items (1 overdue)", "sara@brightwater.example"))
        self.assertEqual(o["writes"], 0)                                                               # nothing is written by opening or copying

    def test_a_refused_clipboard_selects_the_preview_and_says_so(self):
        o = self.probe(self.PREP + """
          Object.defineProperty(navigator,"clipboard",{configurable:true,value:{ write:async()=>{ throw new Error("NotAllowedError"); }, writeText:async()=>{ throw new Error("NotAllowedError"); } }});
          window.ClipboardItem=function(m){ this.m=m; };
          openDraftEmail("Sara Example"); document.getElementById("deCopyHtml").click(); await new Promise(r=>setTimeout(r,60));
          const sel=getSelection(), a=document.getElementById("deMsg").textContent, selected=sel.toString().length>50&&document.getElementById("dePrev").contains(sel.anchorNode);
          document.getElementById("deCopySubj").click(); await new Promise(r=>setTimeout(r,60));
          window.OUT={a,selected,subjSelected:document.activeElement.id, msg:document.getElementById("deMsg").textContent, mod:MOD};
          Object.defineProperty(navigator,"clipboard",{configurable:true,value:undefined}); document.getElementById("deCopyText").click(); await new Promise(r=>setTimeout(r,60)); window.OUT.none=document.getElementById("deMsg").textContent;""")
        self.assertIn(f"press {o['mod']}C to copy", o["a"])
        self.assertTrue(o["selected"])                                                                 # the preview is selected for the copy
        self.assertEqual(o["subjSelected"], "deSubj")
        self.assertIn("press", o["msg"])
        self.assertIn("press", o["none"])                                                              # and with no clipboard at all

    def test_changing_an_option_after_editing_asks_before_it_redraws(self):
        o = self.probe(self.PREP + """
          openDraftEmail("Sara Example"); const prev=document.getElementById("dePrev"); prev.querySelector("p").textContent="My own words,"; prev.dispatchEvent(new Event("input",{bubbles:true}));
          document.getElementById("deUpd").click(); const kept=text().includes("My own words,"), note=!document.getElementById("deNote").hidden;
          document.getElementById("deRedraw").click(); window.OUT={kept,note,after:text().includes("My own words,"), upd:text().includes("Waiting on legal")};""")
        self.assertTrue(o["kept"] and o["note"])                                                       # the edits are kept until he says
        self.assertFalse(o["after"])
        self.assertTrue(o["upd"])

    def test_the_page_is_given_the_own_domains_from_settings(self):
        import json as _json
        settings = _json.loads((self.v.root / "system/config/settings.json").read_text())
        want = [d.lower() for d in settings["identity"].get("own_domains", [])]
        o = self.probe("window.OUT={d:D.settings.ownDomains, s:S.ownDomains};")
        self.assertEqual((o["d"], o["s"]), (want, want))
        self.assertTrue(want)                                                                          # the safeguard needs at least one

    def test_the_person_page_has_draft_email_and_no_prep_1_1_and_the_button_opens_the_popup(self):
        o = self.probe(self.PREP + """
          go("person","Sara Example"); const row=()=>[...document.querySelectorAll("#v-person .hhead button, #v-person button.btn, #v-person button.ib")].map(b=>(b.textContent.trim()||b.getAttribute("aria-label")||"").trim()).filter(Boolean);   /* BL-161: Edit details is the pencil, named */
          const withItems={row:row(), disabled:document.getElementById("ppEmail").disabled, pp1:!!document.getElementById("pp1"), note:!!document.getElementById("ppEmailNote")};
          document.getElementById("ppEmail").click(); const opened=document.getElementById("deDlg")&&document.getElementById("deDlg").open; document.getElementById("deDlg").close();
          A.length=0; R.length=0; go("person","Jane Doe"); go("person","Sara Example");
          const none={disabled:document.getElementById("ppEmail").disabled, note:(document.getElementById("ppEmailNote")||{}).textContent, hand:!!document.getElementById("ppHand"), row:row()};
          document.getElementById("ppEmail").click(); const dlgAfter=document.getElementById("deDlg").open;
          window.OUT={withItems,opened,none,dlgAfter,text:document.getElementById("v-person").innerText};""")
        w = o["withItems"]
        self.assertIn("Draft email", w["row"])
        self.assertLess(w["row"].index("Draft email"), w["row"].index("Hand over…"))                   # in Prep 1:1's old place, beside Hand over
        self.assertLess(w["row"].index("Hand over…"), w["row"].index("Edit details"))
        self.assertEqual((w["disabled"], w["pp1"], w["note"]), (False, False, False))
        self.assertNotIn("Prep 1:1", o["text"])
        self.assertTrue(o["opened"])
        n = o["none"]
        self.assertEqual((n["disabled"], n["hand"]), (True, False))                                    # nothing open: the button is off
        self.assertEqual(n["note"], "Nothing open for Sara Example, so no email is needed.")
        self.assertFalse(o["dlgAfter"])                                                                # and does nothing

    def test_nothing_open_says_so_and_opens_nothing(self):
        o = self.probe(self.PREP + """
          A.length=0; R.length=0; openDraftEmail("Sara Example"); window.OUT={dlg:!!document.getElementById("deDlg"), snack:document.getElementById("snackT").textContent};""")
        self.assertFalse(o["dlg"])
        self.assertEqual(o["snack"], "Nothing open for Sara Example, so no email is needed")



# ── BL-138: the People page's two tabs, in a real browser against the real live server ──

from live_browser import LiveBrowserCase  # noqa: E402


class PeopleTabsTests(LiveBrowserCase):
    """test_decisions_dashboard's data: Sara asked for a late decision (and owns an open action), Alan asked for one, Omar asked
    for one (and owns an open action), Jane made one; plus Lee Closed, who owns only a closed action and isn't in the register."""
    width, height = 1400, 1000

    @classmethod
    def load(cls, v):
        from test_decisions_dashboard import load as load_decisions, d
        load_decisions(v)
        v.propose("closed-only", [action(1, description="Old task", owner="Lee Closed", status="Closed", closed=d(-2)),
                                  action(2, project="DEF", description="Ask about rota", owner="Priya Waits")])
        v.run("apply")

    def setUp(self):
        super().setUp()
        self.b.eval("localStorage.clear()")

    def tab(self, t):
        b = self.b
        b.click(f'#ptabs [data-ptab="{t}"]')
        b.wait(f"PTAB==='{t}'")

    def rows(self):
        return self.b.eval("[...document.querySelectorAll('#peopleTbl tbody tr')].map(tr=>[...tr.cells].map(c=>c.textContent.replace(/\\s+/g,' ').trim()))")

    def names(self):
        return [r[0].replace(" needs details", "").replace("You (Alan Carter)", "Alan Carter") for r in self.rows()]

    def open_people(self):
        b = self.b
        b.eval("go('people','work')")          # #248: With work is one of four tabs (Everyone is the default)
        b.wait("document.querySelector('#ptabs [data-ptab]')")
        return b

    def test_who_is_on_each_tab_with_counts(self):
        b = self.open_people()
        self.assertEqual(b.eval("PTAB"), "work")
        work = {r[0]: r[1:] for r in self.rows()}
        self.assertEqual(self.rows()[0][0], "You (Alan Carter)")                                   # You first
        self.assertEqual(work["Sara Example"][4:8], ["1", "0", "1", "0"])                          # open action, a decision waiting (Overdue stays actions and RAID)
        self.assertEqual(work["Omar Ali"][4:7], ["1", "0", "1"])
        self.assertIn("Priya Waits needs details", work)                                         # an open action alone counts (#248: needs details, not "not in register")
        self.assertNotIn("Jane Doe", self.names())                                                # a made decision alone does not
        self.assertNotIn("Lee Closed", self.names())
        heads = b.eval("[...document.querySelectorAll('#peopleTbl thead th')].map(t=>t.textContent.replace(/[▲▼]/g,'').trim())")
        self.assertEqual(heads, ["Name", "Email", "Organisation", "Role", "Projects", "Actions", "Risks and issues", "Decisions", "Overdue", "Actions on the person"])   # #248: the register's columns
        n_work = len(self.rows())
        self.tab("none")
        none = {r[0].replace(" needs details", ""): r[1:] for r in self.rows()}
        self.assertEqual(none["Jane Doe"][4:8], ["0", "0", "0", "0"])                             # nothing open (#248: one set of columns; no Closed items)
        self.assertEqual(none["Lee Closed"][3], "Example Programme")
        self.assertTrue(set(self.names()).isdisjoint(set(work) | {"Alan Carter"}))               # nobody on both
        tabs = b.eval("[...document.querySelectorAll('#ptabs [data-ptab]')].map(x=>x.textContent.replace(/\\s+/g,' ').trim())")
        self.assertEqual(tabs[1:3], [f"With work {n_work}", f"Nothing assigned {len(self.rows())}"])
        self.assertTrue(tabs[0].startswith("Everyone ") and tabs[3].startswith("Needs attention "), tabs)
        self.assertFalse(b.eval("/%|score|rating|on.?time/i.test(document.getElementById('v-people').textContent)"))

    def test_hidden_people_are_on_neither(self):
        b = self.open_people()
        b.eval("REG.forEach(p=>{ if(p.name==='Omar Ali'||p.name==='Jane Doe') p.hidden=true; }); renderPeople()")
        names = self.names()
        self.tab("none")
        names += self.names()
        self.assertNotIn("Omar Ali", names)
        self.assertNotIn("Jane Doe", names)

    def test_a_count_link_shows_a_focus_outline_when_reached_by_tab(self):
        """#190: the count links lose their dotted underline in the People table; focus must still be visible (a computed outline)."""
        b = self.open_people()
        b.eval("document.querySelector('#ptabs [data-ptab=\"work\"]').focus()")
        for _ in range(40):
            b.key("Tab")
            if b.eval("!!document.activeElement.matches('#peopleTbl a.cntl')"):
                break
        self.assertTrue(b.eval("document.activeElement.matches('#peopleTbl a.cntl')"), b.eval("document.activeElement.outerHTML.slice(0,120)"))
        o = b.eval("(()=>{ const c=getComputedStyle(document.activeElement); return [c.outlineStyle, parseFloat(c.outlineWidth), document.activeElement.matches(':focus-visible')]; })()")
        self.assertNotEqual(o[0], "none", o)
        self.assertGreater(o[1], 0, o)
        self.assertTrue(o[2], o)

    def test_the_person_page_counts_read_zero_not_a_dash(self):
        b = self.open_people()
        b.eval("go('person','Priya Waits')")
        b.wait("VIEW==='person'&&document.querySelector('.ppcounts')")
        t = b.eval("[...document.querySelectorAll('.ppcounts > *')].map(x=>x.textContent.replace(/\\s+/g,' ').trim())")
        self.assertTrue(any(x.startswith("0 ") for x in t), t)                                # she owns no risks: 0
        self.assertFalse(any("—" in x or x.startswith("-") for x in t), t)

    def test_sorting_each_tab_and_the_tab_survives_reload_and_the_address(self):
        b = self.open_people()
        b.click('#peopleTbl th[data-psort="name"]')
        self.assertEqual(self.names()[0], "Alan Carter")                                          # You stay first
        rest = self.names()[1:]
        self.assertEqual(rest, sorted(rest))
        self.tab("none")
        self.assertEqual(b.eval("location.hash"), "#people/none")
        b.click('#peopleTbl th[data-psort="name"]')                                               # this tab's own sort: name, now reversed
        self.assertEqual(self.names(), sorted(self.names(), reverse=True))
        b.reload("typeof go==='function' && LIVE")
        b.wait("VIEW==='people' && PTAB==='none' && document.querySelector('#peopleTbl tbody tr')")
        b.eval("go('today')")
        b.click('.rail button[data-v="people"]')                                                   # the rail returns to the tab last used
        b.wait("VIEW==='people'")
        self.assertEqual(b.eval("[PTAB,location.hash]"), ["none", "#people/none"])
        b.goto(self.base + "/#people")                                                             # a plain link: Everyone (#248; was With work)
        b.wait("typeof go==='function' && LIVE && VIEW==='people'")
        self.assertEqual(b.eval("PTAB"), "all")
        b.eval("history.back()")
        b.wait("PTAB==='none'")
        b.key("Tab")
        b.eval("document.querySelector('#ptabs [data-ptab=\"none\"]').focus()")
        b.key("ArrowLeft")                                                                          # arrows move between the tabs
        b.wait("PTAB==='work'")

    def test_closing_someones_last_item_moves_them(self):
        b = self.open_people()
        self.assertIn("Priya Waits", self.names())
        id_ = b.eval("A.find(a=>a.o==='Priya Waits').id")
        self.assertTrue(b.eval(f"boardMove('actions','{id_}',{{st:'Closed'}},'closed')"))
        b.eval("renderPeople()")
        self.assertNotIn("Priya Waits", self.names())
        self.tab("none")
        self.assertIn("Priya Waits", self.names())


if __name__ == "__main__":
    unittest.main()
