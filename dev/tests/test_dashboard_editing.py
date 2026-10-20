"""End-to-end tests for dashboard editing (Step 4b).

Run: python3 dev/tests/test_dashboard_editing.py   (needs Google Chrome; skipped otherwise)

Builds a throwaway vault with fictional data and the real dashboard, then loads it in headless Chrome with one
thing replaced: the file layer (VW), which normally uses Chrome's folder access and can't be driven
automatically. The fake keeps the vault's files in memory. The test then edits through the page's own code
(panel saves, Review decisions, undo, settings), copies what the page wrote back into the vault, and runs
tracker.py apply to check the changes reach the database.
"""
import json
import re
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from page_result import page_result  # noqa: E402
from test_dashboard import CHROME, populate  # noqa: E402
from test_tracker import ABC, Vault  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from split_dashboard import readable_page  # noqa: E402

SCRIPT = r"""
<script>
(async()=>{
  const FILES=JSON.parse(document.getElementById("seed").textContent), LOG=[];
  VW={ async read(p){ if(!(p in FILES)) throw new Error("not found: "+p); return FILES[p]; },
       async write(p,t){ FILES[p]=t; LOG.push(["write",p]); }, async remove(p){ delete FILES[p]; LOG.push(["remove",p]); },
       async exists(p){ return p in FILES; }, async append(p,t){ FILES[p]=(FILES[p]||"")+t; LOG.push(["append",p]); } };
  VSTATE="ok"; needVault=async()=>true;   /* the page's own vault check can finish late and reset the fake vault (slow CI) */
  const wait=ms=>new Promise(r=>setTimeout(r,ms)), set=(id,v)=>{ const el=document.getElementById(id); if(el.type==="checkbox") el.checked=v; else el.value=v; };
  const until=async(f,ms=15000)=>{ const t=Date.now(); while(!f()){ if(Date.now()-t>ms) return false; await wait(25); } return true; };   /* wait for the state, not a fixed time (steady under load) */
  const out={errors:[]};
  try{
    // 1. edit an existing action's owner and due date (BL-176: in the peek, each change is its own staged proposal)
    openRecord("actions","ABC-A-001"); await pkCommit("actions","ABC-A-001",{o:"Sara Example"},"Owner","",""); await pkCommit("actions","ABC-A-001",{due:"2026-11-20"},"Due date","",""); closePanel();
    // 1b. closing fills Closed as DD-MM-YYYY (BL-30), for an action and a RAID item, and saves
    for(const [k,arr] of [["actions",A],["raid",R]]){ const x=arr.find(i=>i.p==="ABC"&&i.id!=="ABC-A-001"&&OPENST(i.st)); openRecord(k,x.id);
      await pkSetStatus(k,x.id,"Closed"); PK.det[x.id]=true; drawPanel(); (out.closedFill=out.closedFill||[]).push(([...document.querySelectorAll("#pkDet .pk-drow")].find(r=>r.textContent.startsWith("Closed"))||{textContent:""}).textContent.replace(/^Closed/,"").split(" ·")[0].trim());
      (out.closedSaved=out.closedSaved||[]).push([x.st,x.closed]); closePanel(); }
    // 2. create a new action
    // BL-179: New is the peek; the title with a project stages one new proposal, later edits update it
    openNew("actions"); { const id=CUR.nid; await pkCommit("actions",id,{p:"ABC"},"Project","",""); await pkCommit("actions",id,{t:"Book the steering room"},"Action","",""); await pkCommit("actions",id,{o:"Omar Ali"},"Owner","",""); await pkCommit("actions",id,{due:"2026-10-15"},"Due date","",""); out.newStaged=PKS.filter(s=>s.isNew).length; } closePanel();
    // 3. create and immediately undo a RAID item (Undo in the message)
    openNew("raid"); { const id=CUR.nid; await pkCommit("raid",id,{p:"ABC"},"Project","",""); await pkCommit("raid",id,{t:"Temporary risk"},"Description","",""); } await pkUndoLast(); out.unstaged=[CUR&&CUR.mode,CUR&&CUR.staged]; CUR.draft.t=""; closePanel(); await VQ;   /* Undo last unstages it */
    // 4. health and current state
    openProject("ABC","health"); set("f_health","At risk"); set("f_reason","Data access still late"); await savePanel(false);
    go("cockpit","ABC"); startCurEdit("ABC"); const ce=document.getElementById("curEd"); ce.cxed.editor.commands.setContent("<p>Recovery plan agreed with the client.</p>");   /* BL-301 A: the one editor */
    ce.dispatchEvent(new Event("input",{bubbles:true})); await saveCurEdit(); await VQ;
    // 5. Review: approve a routine item, reject a new risk, try to approve the draft (must not write)
    const routine=REV.find(r=>r.kind==="actions"&&r.p), risk=REV.find(r=>r.kind==="raid"), draft=REV.find(r=>r.kind==="draft");
    // edit a proposal's owner and Save and approve: nothing else in it may change (regression: raised was blanked)
    openProposal(routine.n); await pkCommit(routine.kind,"rv"+routine.n,{o:"Omar Ali"},"Owner","",""); await pkPropSave(true); await VQ;   /* BL-177: the peek layout */
    await decide(risk.n,"rejected"); await decide(draft.n,"approved"); await VQ;
    out.draftSnack=document.getElementById("snackT").textContent;
    // 6. Work filters (BL-16) and column order (BL-17)
    const tick=(menu,v)=>{ document.getElementById(menu+"Btn").click(); const i=[...document.querySelectorAll(`#${menu}Menu input[type=checkbox]`)].find(x=>x.value===v); i.checked=true; i.dispatchEvent(new Event("change",{bubbles:true})); };
    // 5b. rich text Current state (BL-22): the editor writes Markdown; the page renders it (not saved here)
    // BL-47: the card itself becomes the editor; the side panel isn't used
    go("cockpit","ABC"); startCurEdit("ABC"); const ed=document.getElementById("curEd");
    ed.innerHTML="<div>Build is <b>late</b> and <i>risky</i>.</div><ul><li>Data access</li><li>UAT <b>prep</b></li></ul><ol><li>Escalate</li></ol>";
    ed.dispatchEvent(new Event("input",{bubbles:true})); out.md=htmlToMd(ed);
    out.inplace=[!!ed.closest(".curcard.editing"),document.getElementById("panel").classList.contains("on"),[...document.querySelectorAll(".inplace .rtebar [data-rc]")].length];
    ed.innerHTML="<h1>Next steps</h1><h2>Detail</h2><h3>Fine print</h3><blockquote>Hold the date</blockquote><p>Was <s>late</s>, see <a href=\"https://example.com/p\">the plan</a>.</p><ul><li>Data<ul><li>Masked extract</li></ul></li><li>UAT</li></ul>";
    out.mdNew=htmlToMd(ed);
    // unsaved changes: leaving asks first; Keep editing stays, Discard goes
    ed.dispatchEvent(new Event("input",{bubbles:true})); go("work"); out.guard=[VIEW,document.getElementById("discardBar").classList.contains("on")];
    document.querySelector('[data-dis="keep"]').click(); out.kept=[VIEW,!!document.getElementById("curEd")];
    go("work"); document.querySelector('[data-dis="go"]').click(); out.discarded=[VIEW,CURED];
    out.html=mdHtml("Para with **bold** and *it* and file_name.\n\n- one\n- two\n\n1. first");
    out.htmlNew=mdHtml("### Next\n\n> Quote\n\n- a\n  - b\n- c\n\nSee [x](https://e.com) and ~~old~~.");
    // BL-46: a generated draft lands in the in-place editor with its sources; nothing is saved
    { const realF=window.fetch; window.fetch=async(u,o)=>u==="/api/current/generate"?new Response(new Blob(['data: {"type":"step","label":"Reading minutes"}\n\n','data: {"type":"text","text":"Recovery is **on track** since 2026-10-05.\\n\\nSOURCES:\\n- minutes/2026-10-05 Steering.docx"}\n\n','data: {"type":"done"}\n\n']).stream(),{status:200,headers:{"Content-Type":"text/event-stream"}}):realF(u,o);
      await runGen({code:"ABC",from:"2026-09-29",to:TODAY,sources:["tracker"],note:""}); window.fetch=realF;
      out.gen=[htmlToMd(document.getElementById("curEd")),document.querySelector("#v-cockpit .gensrc")?.textContent||"",CURED&&CURED.dirty];
      document.querySelector("[data-cure=cancel]").click(); document.querySelector('[data-dis="go"]').click(); }
    // BL-42: Intake lists the files in the inbox (#232 C2: as rows of the one page; Select new and the Upload table went with the old Intake page)
    go("inbox"); out.inboxRows=(D.intake_review.meetings||[]).filter(m=>m.src==="upload").length; out.inboxHash=location.hash;
    // BL-62: Work filters behave
    { go("work"); loadTab("actions"); renderWork(); const a=A.find(x=>x.due); WQ=fd(a.due); out.f62search=rows().some(x=>x.id===a.id); WQ="";
      applyView("open"); PRIF.add("High"); syncView(); renderWork(); document.querySelector('#wtabs [data-t="raid"]').click(); out.f62raidClean=[...PRIF].length;
      document.querySelector('#wtabs [data-t="actions"]').click(); out.f62kept=[...PRIF];
      out.f62none=FDEFS.actions.find(d=>d[0]==="ws")[2]()[0];
      const c=A.find(x=>!CREAITE.open(x)&&x.due)||Object.assign(A[0],{}); out.f62closedDue=(()=>{ const was=[c.st,c.due]; c.st="Closed"; c.due=c.due||TODAY; const k=dueKey(c); [c.st,c.due]=was; return k; })();
      PRIF.clear(); FX.due.add("overdue"); syncView(); renderWork(); document.getElementById("clearF").click(); out.f62clear=[WVIEW,[...FX.due].length,[...PROJF].length];
      const f=FDEFS.decisions.find(d=>d[0]==="dt"); out.f62future=[f[5]({date:new Date(Date.now()+3*864e5).toISOString().slice(0,10)},new Set(["7"])),f[5]({date:TODAY},new Set(["7"]))]; }
    // command palette: Inbox, views, project actions, milestones and files are all reachable
    go("cockpit","ABC"); const ck=q=>ckItems(q).map(i=>`${i.g}|${i.l}`);
    out.ck=[ck("").filter(x=>x.startsWith("Go to|")),ck("overdue").filter(x=>x.startsWith("Views|")),ck("current state").filter(x=>x.startsWith("Actions|")),
      ck("uat start").filter(x=>x.startsWith("Milestones|")),ck("steering").filter(x=>x.startsWith("Files|")),ck("recording").filter(x=>x.startsWith("Intake|"))];
    // BL-44: the health panel opens on the right of the project page; #109: over the page (pover), against its right edge, not beside it
    go("cockpit","ABC"); openProject("ABC","health"); const pr=document.getElementById("panel").getBoundingClientRect(), vr=document.getElementById("v-cockpit").getBoundingClientRect();
    out.panelRight=[pr.right>=vr.right-2&&document.getElementById("panel").classList.contains("pover"), pr.top<=vr.top+2]; closePanel();
    // BL-52: health better than the evidence needs a new reason (checked here, not saved)
    openProject("ABC","health"); const hsel=document.getElementById("f_health"); hsel.value="On track"; hsel.dispatchEvent(new Event("change"));
    out.evidence=document.getElementById("hEvidence").textContent; set("f_reason",P.find(p=>p.code==="ABC").reason||"");
    await savePanel(false); out.evidenceBlock=document.getElementById("pErr").textContent;
    hsel.value="Off track"; hsel.dispatchEvent(new Event("change")); out.evidenceOk=document.getElementById("hEvidence").classList.contains("warn"); EDITING=false; closePanel();
    // 5b2. milestone picker shows names, keeps IDs as values (BL-27); nothing saved
    const linked=A.find(a=>a.ms==="ABC-M-001"); openRecord("actions",linked.id); PK.det[linked.id]=true; drawPanel(); document.querySelector('#pkDet [data-pkp="ms"]').click();   /* BL-176: Details' list */
    out.msOpts=[...document.querySelectorAll(".pkpop .pkopt")].map(o=>o.querySelector("span").textContent); out.msSel=(document.querySelector('.pkpop .pkopt[aria-selected="true"] span')||{}).textContent; closePicker("owner",false); closePanel();
    // 5b3. learn from a project choice (BL-28): the option names the signal and follows the chosen project
    const lr=REV.find(r=>r.kind==="actions"&&!r.done); lr.signals=[{kind:"keyword",value:"pilot",ok:false,owners:[]},{kind:"sender",value:"sam@client.com",ok:true,owners:[]}];
    openProposal(lr.n); await pkCommit("actions","rv"+lr.n,{p:"DEF"},"Project","","");   /* BL-177: the peek's Project, held in the proposal */
    out.learnTxt=(document.querySelector("#pkPropEnd .pk-learn span")||{}).textContent||""; closePanel(); delete lr.signals;
    // 5b4. reminders offer Run report now first; in the file version it needs the live server (BL-34)
    go("today"); const note=document.querySelector("#attnList .rem"); note.querySelector(".dots").click();
    out.remMenu=[...document.querySelectorAll("#remMenu [role=menuitem]")].map(b=>[b.textContent,b.getAttribute("aria-disabled")==="true",b.dataset.tip||""]); closeMenu();
    // 5b5. workstreams belong to their project (BL-57); in-memory items only, nothing saved here
    { const a1=A.find(a=>a.p==="ABC"), d1=A.find(a=>a.p==="DEF"), keep=[a1.ws,d1.ws]; a1.ws="Cut-over"; d1.ws="Cut-over";
      out.wsFor=[wsFor("ABC").includes("Cut-over"),wsFor("DEF").includes("Cut-over"),wsFor("ABC").some(w=>A.some(x=>x.p==="DEF"&&x.ws===w&&!A.some(y=>y.p==="ABC"&&y.ws===w)))];
      openRecord("actions",a1.id); PK.det[a1.id]=true; drawPanel(); document.querySelector('#pkDet [data-pkp="ws"]').click();   /* BL-176: Details' list, this project's only */
      out.wsList=[...document.querySelectorAll(".pkpop .pkopt span")].map(o=>o.textContent).filter(t=>t!=="None"&&!t.startsWith("Add ")).every(v=>wsFor("ABC").includes(v));
      const wq=document.querySelector(".pkpop .pkq"); wq.value="Brand new stream"; wq.dispatchEvent(new Event("input")); [...document.querySelectorAll(".pkpop .pkopt")].find(o=>o.textContent.startsWith("Add “")).click();
      out.wsAsk=[(document.querySelector(".pkws .pkws-h")||{}).textContent,(document.querySelector('.pkws [data-wsn="name"]')||{}).value]; closePicker("owner",false); closePanel();   /* BL-187: the new workstream's form */
      go("settings","people");
      out.wsMgr=[...document.querySelectorAll("#wsMgr tbody tr td:first-child")].map(td=>td.textContent.trim()).filter(t=>t.endsWith("Cut-over"));
      a1.ws=keep[0]; d1.ws=keep[1]; }
    // 5c. owner picker lists the project's own people first (BL-18 A; BL-179: the new item's owner chip); nothing saved
    openNew("actions"); await pkCommit("actions",CUR.nid,{p:"DEF"},"Project","",""); document.querySelector('#panel [data-pkp="o"]').click();
    out.defPeople=projPeople("DEF"); out.firstNames=[...document.querySelectorAll(".pkpop .pkopt")].slice(0,out.defPeople.length).map(o=>o.querySelector("span").firstChild.textContent.trim()); closePicker("owner",false); closePanel();
    // 5d. ask creaite autocomplete (BL-24)
    openChat(); const ci=document.getElementById("chIn"), type=v=>{ ci.value=v; ci.dispatchEvent(new Event("input",{bubbles:true})); },
      key=k=>ci.dispatchEvent(new KeyboardEvent("keydown",{key:k,bubbles:true,cancelable:true})), opts=()=>[...document.querySelectorAll("#acMenu .aco span")].map(x=>x.textContent);
    type("/"); out.acAll=opts().length; out.acGroups=document.querySelectorAll("#acMenu .cgrp").length;
    type("wee"); out.acWee=opts();
    type("client report "); out.acCodes=opts();
    type("mark ABC-A"); out.acMark=opts().slice(0,2);
    type("approve "); out.acApprove=opts().length===REV.filter(r=>!r.done).length;
    type("sweep mail"); key("ArrowDown"); key("ArrowDown"); key("Enter");   /* BL-199: nothing chosen until ↓; the 2nd is two presses */ out.acPicked=[ci.value,ci.value.slice(ci.selectionStart,ci.selectionEnd)];
    type("rev"); key("Escape"); out.acEsc=[document.getElementById("acMenu").hidden,document.getElementById("chat").classList.contains("on")];
    ci.value=""; closeChat();
    go("cockpit",P[0].code); out.pencils=[...document.querySelectorAll("#v-cockpit .card.edt .pencil")].map(b=>b.getAttribute("aria-label")); out.mvpencil=document.getElementById("mvPencil")?.getAttribute("aria-label");
    out.oldEdit=[...document.querySelectorAll("#v-cockpit button.mini")].some(b=>/^Edit/.test(b.textContent));
    go("today"); out.day={head:document.getElementById("dayHead").textContent,dots:document.querySelectorAll("#dayLine .dot").length,
      cols:[...document.querySelectorAll("#dayMeets .dm .tm")].map(e=>e.textContent),proj:!!document.querySelector('#dayMeets .dm [data-proj="ABC"]'),
      allDay:document.querySelector("#dayMeets .dayall").textContent,sections:document.querySelectorAll("#tBrief .tsec:not(.setupsec)").length};   /* BL-156: the set-up checklist is not one of the five */
    const cal0=D.calendar; D.calendar=null; renderToday(); out.dayNone=[document.querySelectorAll("#dayLine .dot").length,document.getElementById("dayMeets").textContent.includes("No calendar yet")&&document.getElementById("dayLine").hidden]; D.calendar=cal0; renderToday();
    go("work"); tick("proj","DEF");
    out.projRows=rows().map(x=>x.id); out.clearShown=!!document.getElementById("clearF");
    tick("proj","ABC"); out.twoLabel=document.getElementById("projBtn").textContent; out.twoRows=rows().filter(x=>x.p==="ABC").length;
    tick("pri","Urgent"); tick("pri","High"); out.priLabel=document.getElementById("priBtn").textContent;
    document.getElementById("projBtn").click(); document.querySelector('#projMenu [data-ma="clear"]').click(); tick("proj","DEF"); out.bothRows=rows().filter(x=>x.pr==="Urgent"||x.pr==="High").length===rows().length;
    document.getElementById("clearF").click(); out.afterClear=rows().length; out.clearHidden=WVIEW==="open";
    // BL-45: combinable filters, the applied row and count, menu counts, sorting, saved views, the address
    applyView("open"); renderWork(); tick("due","overdue"); out.f1open=WVIEW; tick("st","Delayed"); out.f1=[WVIEW,document.getElementById("wcount").textContent,[...document.querySelectorAll("#wapplied .fchip")].map(c=>c.textContent.replace("×","").trim())];
    document.getElementById("stBtn").click(); out.counts=[...document.querySelectorAll("#stMenu label")].map(l=>[l.textContent.replace(/\d+$/,""),l.querySelector("small").textContent,l.classList.contains("dim")]);
    applyView("overdue"); renderWork(); out.presetIsFilters=[[...FX.st].sort().join(),[...FX.due].join(),WVIEW];
    tick("own",ownerOpts()[0][0]); out.mineOverdue=[WVIEW,rows().every(x=>overdue(x))];
    document.querySelector('#workTbl th[data-col="t"]').click(); out.sortAsc=rows().map(x=>x.t); document.querySelector('#workTbl th[data-col="t"]').click(); out.sortDesc=rows().map(x=>x.t);
    out.sortHash=location.hash.includes("&s=t.desc"); document.querySelector('#workTbl th[data-col="t"]').click(); out.sortOff=!SORT[WT];
    out.parsedF=parseHash("#work=actions&st=Open,Delayed&due=overdue&o=Sara%20Example&s=due.asc");
    clearAllFilters(); renderWork(); tick("st","Cancelled"); document.getElementById("saveView").click(); document.getElementById("viewName").value="Stuck";
    document.getElementById("viewSave").click(); await VQ; await wait(50); out.saved=[WVIEW,[...document.querySelectorAll("#wviews .vchip")].map(b=>b.textContent.replace("×","").trim()).includes("Stuck"),JSON.stringify(SAVED.actions)]; applyView("open"); renderWork();
    document.getElementById("moreBtn").click(); out.more=[...document.querySelectorAll("#moreMenu .fplist .fsec2 ~ [data-fpk]")].map(x=>x.textContent); document.querySelector('#moreMenu [data-fpk="dr"]').click();
    const df=document.querySelector('#moreMenu [data-dr="from"]'); df.value="01-01-2099"; df.dispatchEvent(new Event("change",{bubbles:true})); out.dr=[DR.from,rows().length,[...document.querySelectorAll("#wapplied .fchip")].some(c=>c.textContent.startsWith("Due: 01-01-2099"))];
    document.getElementById("clearF").click(); applyView("open"); renderWork();
    const wq=document.getElementById("workQ"), srch=q=>{ wq.value=q; wq.dispatchEvent(new Event("input",{bubbles:true})); return rows().map(x=>x.id); };
    WT="actions"; WVIEW="open"; renderWork(); const sa=rows()[0];
    out.qId=srch(sa.id.toLowerCase()); out.qWords=srch(sa.t.split(" ").slice(0,2).reverse().join(" ")).includes(sa.id);
    out.qNone=[srch("zzqqxx").length,document.querySelector("#workTbl .empty").textContent.includes("zzqqxx"),!document.getElementById("clearF").hidden,location.hash.includes("&q=zzqqxx")];
    wq.dispatchEvent(new KeyboardEvent("keydown",{key:"Escape",bubbles:true,cancelable:true})); out.qEsc=[WQ,wq.value,rows().length>1];
    srch("zzqqxx"); document.getElementById("clearF").click(); out.qClear=[WQ,wq.value];
    out.qParse=parseHash("#work=actions&v=open&q=steering%20pack").q;
    moveCol("pr","t"); out.cols=[...document.querySelectorAll("#workTbl th")].map(th=>th.dataset.col);
    // 7. ask creaite reads a streamed answer and shows the confirmation card (canned stream; no server)
    const ev=o=>`data: ${JSON.stringify(o)}\n\n`;
    const body=[ev({type:"step",label:"Running tracker.py read actions"}),ev({type:"text",text:"Here's the plan for 2026-10-09."}),
      ev({type:"confirm",title:"Close ABC-A-001",body:"Stage a proposal closing it"}),ev({type:"done",session:"s-9"})].join("");
    const realFetch=window.fetch; window.fetch=async(u,o)=>{ if(u!=="/api/ask") return new Response('{"ok":true}',{headers:{"Content-Type":"application/json"}}); out.askBody=JSON.parse(o.body); return new Response(new Blob([body]).stream(),{status:200}); };
    D.token="t"; askLive("Close ABC-A-001",null); await until(()=>ASKSESSION==="s-9"&&document.querySelector("#chLog .confirm b")); window.fetch=realFetch;
    out.chat=[...document.querySelectorAll("#chLog .step, #chLog .msg")].map(e=>e.textContent);
    { const w=working(); out.quip=[w.querySelector(".quip").textContent.replace(/…$/,""),QUIPS]; w.remove(); }
    out.card=[...document.querySelectorAll("#chLog .confirm b")].map(b=>b.textContent); out.session=ASKSESSION;
    // 6b. ask creaite panel width (BL-35): ← widens by 20px and is remembered; double-click resets; capped at 70%
    openChat(); const grip=document.getElementById("chGrip"), cw=()=>document.getElementById("chat").getBoundingClientRect().width;
    setChatWidth(420,true); grip.dispatchEvent(new KeyboardEvent("keydown",{key:"ArrowLeft",bubbles:true,cancelable:true}));
    out.chatW=[cw(),store.get("creaite-chat-width",null),grip.getAttribute("aria-label")];
    setChatWidth(5000,true); out.chatMax=[cw(),Math.round(innerWidth*0.7)];
    grip.dispatchEvent(new MouseEvent("dblclick",{bubbles:true})); out.chatReset=[cw(),store.get("creaite-chat-width",null)]; closeChat();
    // 7a. Stop (BL-33): the Send button becomes Stop while a request runs; the button stops it; what's shown is kept
    window.fetch=async(u,o)=>{ if(u==="/api/ask/stop") return new Response(JSON.stringify({ok:false}),{headers:{"Content-Type":"application/json"}});
      const body=new ReadableStream({start(c){ c.enqueue(new TextEncoder().encode(ev({type:"text",text:"Partial answer"}))); o.signal.addEventListener("abort",()=>c.error(new DOMException("Aborted","AbortError"))); }});
      return new Response(body,{status:200}); };
    BUSY=false; openChat(); await wait(50); const pAsk=askLive("Slow question",null); await until(()=>document.getElementById("chSend").getAttribute("aria-label")==="Stop"&&[...document.querySelectorAll("#chLog .msg")].some(m=>m.textContent==="Partial answer")); out.stopBtn=document.getElementById("chSend").getAttribute("aria-label");
    document.getElementById("chSend").click(); await pAsk;   /* #130: the Stop button stops it; Esc never does (test_ask_reopen) */ await until(()=>document.getElementById("chSend").getAttribute("aria-label")==="Send"&&document.querySelector("#chLog .step.stopped")); window.fetch=realFetch;
    out.afterStop=[document.getElementById("chSend").getAttribute("aria-label"),[...document.querySelectorAll("#chLog .step.stopped")].length,
      [...document.querySelectorAll("#chLog .msg")].some(m=>m.textContent==="Partial answer"),document.getElementById("chat").classList.contains("on")];
    // 7a2. reattach (BL-37): earlier messages, the run's own question, then its replayed events; the run's
    // half-written entry in the chat file isn't shown twice; the run is acknowledged at the end
    out.acked=[];
    window.fetch=async(u,o)=>{ const b=o&&o.body?JSON.parse(o.body):{};
      if(u==="/api/chat") return new Response(JSON.stringify({ok:true,chat:"s-1",session:"s-1",messages:[{who:"you",text:"Earlier"},{who:"creaite",text:"Earlier answer",steps:[]},{who:"you",text:"Long job",run:"r-att-1"},{who:"creaite",text:"Half",steps:[],run:"r-att-1",running:true}]}),{headers:{"Content-Type":"application/json"}});
      if(u==="/api/ask/ack"){ out.acked.push(b.run); return new Response('{"ok":true}',{headers:{"Content-Type":"application/json"}}); }
      if(u==="/api/ask/attach") return new Response(new Blob([ev({type:"step",label:"Running report.py weekly-data ABC"}),ev({type:"text",text:"All done."}),ev({type:"done",session:"s-1",chat:"s-1",run:"r-att-1"})]).stream(),{status:200});
      return realFetch(u,o); };
    closeChat(); await attachRun({id:"r-att-1",chat:"s-1",message:"Long job",confirmed:false,done:false});
    await until(()=>RB.state==="done"&&out.acked.length&&!document.getElementById("askBtn").classList.contains("working")); window.fetch=realFetch;   /* the run's end, not a fixed 300 ms */
    out.attachLog=[...document.querySelectorAll("#chLog .step, #chLog .msg")].map(e=>[...e.childNodes].filter(n=>!(n.classList&&(n.classList.contains("msgedit")||n.classList.contains("msgcopy")))).map(n=>n.textContent).join(""));   /* BL-148: Copy and Edit buttons are not the text */
    out.attachEnd=[document.getElementById("askBtn").classList.contains("working"),RB.state==="done"&&!document.getElementById("runBadge").hidden,out.acked];
    rbDismiss();
    // 7b. New chat and History (BL-20), with the live server's answers stubbed
    newChat(); await wait(50); out.afterNew={session:ASKSESSION,chat:ASKCHAT,msgs:document.querySelectorAll("#chLog .msg.u").length};
    window.fetch=async(u,o)=>new Response(JSON.stringify(u==="/api/chats"?{ok:true,chats:[{chat:"s-9",title:"Close ABC-A-001",updated:"2026-10-05T09:30:00",count:2}]}
      :{ok:true,chat:"s-9",session:"s-12",messages:[{who:"you",text:"Close ABC-A-001"},{who:"creaite",text:"Done on 2026-10-09.",steps:["Running tracker.py apply"]}]}),{status:200,headers:{"Content-Type":"application/json"}});
    const logBefore=document.getElementById("chLog").children.length;
    await drawHistory(); out.hist=[...document.querySelectorAll("#chHistMenu [data-chat]")].map(b=>b.textContent);
    out.histKeepsChat=document.getElementById("chLog").children.length===logBefore&&document.getElementById("chHistMenu").classList.contains("on");
    /* dev-test-steadiness: wait for the reopened chat itself (its session and its reply), not a fixed 200 ms, before the stub goes */
    document.querySelector("#chHistMenu [data-chat]").click();
    await until(()=>ASKSESSION==="s-12"&&document.querySelector("#chLog .msg.a")); window.fetch=realFetch;
    out.histClosed=!document.getElementById("chHistMenu");   /* BL-316: the Menu block's menu, gone when closed */
    /* the Copy and Edit buttons the page adds a frame later are not the messages' text (BL-148, as attachLog above) */
    out.reopened={session:ASKSESSION,chat:ASKCHAT,log:[...document.querySelectorAll("#chLog .step, #chLog .msg")].map(e=>[...e.childNodes].filter(n=>!(n.classList&&(n.classList.contains("msgedit")||n.classList.contains("msgcopy")))).map(n=>n.textContent).join(""))};
    // 8. a setting (the page's own vault check finishes late and resets the fake's state; set it again)
    VSTATE="ok"; needVault=async()=>true;   /* the page's own vault check can finish late and reset the fake vault (slow CI) */
    // 8a. themes (BL-39, BL-142): every theme sets its palette attribute, creaite is the default; picking another theme sets it and saves it
    /* BL-320: Theme and Style are Essentials, drawn from the live server's catalogue (test_settings_calmer); this page has no server */
    const root=document.documentElement;
    out.themeDefault={palette:S.palette,attr:root.dataset.palette||null,
      options:THEMES.map(t=>t.id),
      ck:ckItems("theme:").map(i=>i.l).filter(l=>l.startsWith("Theme:"))};
    THEMES.push({id:"Test theme",swatch:["#000","#111","#222","#333"]});
    await setPalette("Test theme"); await VQ;
    out.themePicked={palette:S.palette,attr:root.dataset.palette||null,
      saved:JSON.parse(FILES["system/config/settings.json"]).dashboard.palette};
    S.palette="No such theme"; applyTheme(); out.themeUnknown=root.dataset.palette||null;
    out.themeOld=["creaite standard","Minimals","creaite teal"].map(n=>{ S.palette=n; applyTheme(); return root.dataset.palette; });   /* BL-142: the retired names open as creaite */
    S.palette="creaite"; applyTheme();
    await writeSettings({[SKEY.staleDays]:10});
    await VQ; await wait(50);
    // 9. navigation (BL-38): address, Back and Forward, links both ways, switcher, edit blocks leaving
    closeChat(); go("cockpit","ABC"); out.navH1=location.hash;
    document.querySelector('#v-cockpit [data-nav="raid:open:ABC"]').click(); out.navWork=[VIEW,WT,WVIEW,[...PROJF],location.hash,document.getElementById("workCrumb").textContent];
    const rid=rows()[0].id; openRecord("raid",rid); out.navItem=location.hash;
    history.back(); await wait(200); out.navBack=[VIEW,COCK,location.hash];
    history.forward(); await wait(200); out.navFwd=[VIEW,WT,CUR&&CUR.id,location.hash];
    openNew("raid"); document.getElementById("pkTitle").textContent="Half typed"; history.back(); await wait(200); out.navBlocked=[VIEW,!!CUR,location.hash.includes("item="+rid),!document.getElementById("pkAsk").hidden];   /* BL-179: a new item with a title asks Keep or Discard first */
    document.querySelector('#pkAsk [data-pkask="discard"]').click(); await wait(200);
    const da=A.find(a=>a.p==="DEF"); go("work"); openRecord("actions",da.id); document.querySelector('#pkId [data-proj]').click(); out.navPanel=[VIEW,COCK];
    switchProject(1); out.navSw=[COCK]; document.dispatchEvent(new KeyboardEvent("keydown",{key:"[",bubbles:true})); out.navSw.push(COCK);
    out.navSee=[...document.querySelectorAll("#v-cockpit .seeall")].map(a=>a.textContent);
    out.navParse=parseHash("#work=raid&v=open&p=ABC&from=ABC&item="+rid); out.rid=rid;
    // BL-48: the actions card is capped, shows the total, and links to the rest in Work
    const fake=[1,2].map(i=>({id:`ABC-A-90${i}`,p:"ABC",t:`Cap test ${i}`,o:S.me,pr:"Medium",due:TODAY,st:"Open",ws:"",src:"",raised:TODAY})); A.push(...fake);
    S.listCap=1; go("cockpit","ABC"); const h2=[...document.querySelectorAll("#v-cockpit .card h2")].find(h=>h.textContent.startsWith("Actions due or overdue"));
    const due=A.filter(x=>x.p==="ABC"&&CREAITE.open(x)&&(overdue(x)||soon(x))).length; out.cap=[due,h2.textContent,h2.parentNode.querySelectorAll(".mini-list > div[data-open]").length];
    const more=[...document.querySelectorAll("#v-cockpit .seeall")].find(a=>a.textContent.startsWith("+")); out.capMore=more?more.textContent:null;
    if(more) more.click(); out.capWork=[VIEW,[...FX.due].sort(),[...PROJF],rows().length===due]; S.listCap=10; fake.forEach(f=>A.splice(A.indexOf(f),1));
  }catch(e){ out.errors.push(String(e&&e.stack||e)); }
  out.files=FILES; out.log=LOG;
  const pre=document.createElement("pre"); pre.id="result"; pre.textContent=JSON.stringify(out); document.body.appendChild(pre);
})();
</script>
"""


@unittest.skipUnless(CHROME.exists(), "Google Chrome not installed")
class DashboardEditingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = v = Vault()
        populate(v)
        sp = v.root / "system/config/settings.json"         # start from the default theme, whatever this repo has chosen
        s = json.loads(sp.read_text(encoding="utf-8"))
        s.setdefault("dashboard", {}).pop("palette", None)
        sp.write_text(json.dumps(s, indent=2), encoding="utf-8")
        today = date.today().isoformat()                    # Today's day view reads the sweep's calendar
        (v.root / "system/staging/calendar.json").write_text(json.dumps({"fetched": f"{today} 07:05", "days": {today: [
            {"start": "", "end": "", "all_day": True, "title": "Office closed", "where": "", "organiser": False},
            {"start": "10:00", "end": "11:00", "all_day": False, "title": "ABC steering", "where": "Teams", "organiser": True},
            {"start": "13:00", "end": "14:00", "all_day": False, "title": "Busy", "where": "", "organiser": False},
            {"start": "15:00", "end": "15:30", "all_day": False, "title": "Vendor call", "where": "", "organiser": False}]}}),
            encoding="utf-8")
        v.run(script="build_dashboard.py")
        seed = {}
        for rel in ["system/config/settings.json", f"{ABC}/CLAUDE.md"] + \
                [f"system/staging/{p.name}" for p in (v.root / "system/staging").glob("proposed-*.json")]:
            seed[rel] = (v.root / rel).read_text(encoding="utf-8")
        html = (v.root / "dashboard.html").read_text(encoding="utf-8")
        seed_tag = '<script type="application/json" id="seed">' + json.dumps(seed).replace("</", "<\\/") + "</script>"
        harness = v.root / "harness.html"
        harness.write_text(html.replace("</body>", seed_tag + SCRIPT + "</body>"), encoding="utf-8")
        # dev-test-steadiness: in real time, waiting for the result (a virtual-time budget ran out under load)
        cls.result = json.loads(page_result(harness.as_uri(), pin_clock=False))
        cls.new = {k: v for k, v in cls.result["files"].items() if re.search(r"-dashboard(-\d+)?\.json$", k)}

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def proposals(self):
        return [json.loads(t) for t in self.new.values()]

    def test_no_script_errors(self):
        self.assertEqual(self.result["errors"], [])

    def test_edits_written_as_approved_dashboard_proposals(self):
        props = self.proposals()
        self.assertTrue(all(p["source_run"] == "dashboard" for p in props))
        items = [i for p in props for i in p["items"]]
        self.assertTrue(all(i["decision"] == "approved" for i in items))
        upd = [i for i in items if i["op"] == "update" and i.get("id") == "ABC-A-001"]   # BL-176: each edit its own proposal
        self.assertEqual([u["changes"] for u in upd], [{"owner": "Sara Example"}, {"due_date": "2026-11-20"}])
        self.assertRegex(upd[0]["based_on"], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}$")   # exact, for conflicts
        self.assertNotIn("based_on", upd[1])                                   # a later one to the same item would conflict with the first
        new = next(i for i in items if i["op"] == "new" and i["table"] == "actions")
        self.assertEqual((new["values"]["description"], new["values"]["owner"], new["values"]["due_date"]),
                         ("Book the steering room", "Omar Ali", "2026-10-15"))
        self.assertTrue(new["values"]["source"].startswith("Alan Carter (dashboard), "))
        health = next(i for i in items if i["table"] == "projects")
        self.assertEqual(health["changes"], {"health": "At risk", "health_reason": "Data access still late"})

    def test_undo_removed_the_unapplied_proposal(self):
        descs = [i["values"].get("description") for p in self.proposals() for i in p["items"] if i["op"] == "new"]
        self.assertNotIn("Temporary risk", descs)
        self.assertEqual(self.result["unstaged"], ["new", None])                       # BL-179: the peek goes back to the unstaged draft
        self.assertEqual(self.result["newStaged"], 1)                                  # one proposal for the new action, whatever was edited
        self.assertIn("remove", [op for op, path in self.result["log"] if re.search(r"-dashboard(-\d+)?\.json$", path)])

    def test_current_state_is_a_file_change(self):
        fc = next(p["file_changes"] for p in self.proposals() if "file_changes" in p)
        op = fc["file_ops"][0]
        self.assertEqual((fc["file_changes_decision"], op["op"], op["path"]), ("approved", "write", f"{ABC}/CLAUDE.md"))
        self.assertIn("Recovery plan agreed with the client.", op["content"])
        self.assertIn("![Delivery plan](images/plan.png)", op["content"])        # images kept
        self.assertIn("**Client report rhythm:** fortnightly", op["content"])    # rest of the file untouched
        self.assertEqual(op["previous"], (self.v.root / ABC / "CLAUDE.md").read_text(encoding="utf-8"))

    def test_save_and_approve_changes_only_edited_fields(self):
        pending = json.loads(self.result["files"]["system/staging/proposed-pending.json"])
        original = json.loads((self.v.root / "system/staging/proposed-pending.json").read_text())
        before, after = original["items"][0]["values"], pending["items"][0]
        self.assertEqual(after["decision"], "approved")
        self.assertEqual(after["values"], {**before, "owner": "Omar Ali"})       # raised, source… untouched

    def test_review_decisions_and_draft_rule(self):
        pending = json.loads(self.result["files"]["system/staging/proposed-pending.json"])
        decided = {i["n"]: (i["decision"], i.get("decided_in")) for i in pending["items"]}
        self.assertIn(("approved", "dashboard"), decided.values())
        self.assertIn(("rejected", "dashboard"), decided.values())
        self.assertEqual(pending["meeting"]["minutes_decision"], "pending")     # drafts are approved in Claude Code
        self.assertIn("Approving a draft needs the live server", self.result["draftSnack"])   # BL-149: the command is the footnote

    def test_closing_fills_closed_date_in_shown_form(self):
        today = __import__("datetime").date.today()
        self.assertEqual(self.result["closedFill"], [today.strftime("%d-%m-%Y")] * 2)       # BL-30
        self.assertEqual(self.result["closedSaved"], [["Closed", today.isoformat()]] * 2)   # stored YYYY-MM-DD

    def test_reminder_run_report_now(self):
        menu = self.result["remMenu"]
        self.assertEqual(menu[0], ["Run report now", True, "Needs the live server"])
        self.assertEqual([m[0] for m in menu[1:]], ["Dismiss for this session", "Dismiss forever"])

    def test_workstreams_within_their_project(self):
        r = self.result
        self.assertEqual(r["wsFor"], [True, True, False])                       # BL-57: each project its own list
        self.assertTrue(r["wsList"])                                            # picker: this project's only
        self.assertEqual(r["wsAsk"], ["New workstream for Example Programme", "Brand new stream"])   # BL-187: added from the peek, with its details
        self.assertEqual(sorted(r["wsMgr"]), ["ABC Cut-over", "DEF Cut-over"])   # Settings: per project

    def test_learn_option_in_review(self):
        self.assertTrue(self.result["learnTxt"].startswith("Remember sam@client.com (sender) for Digital Enablement"))

    def test_milestone_picker_shows_names(self):
        self.assertEqual(self.result["msOpts"][0], "None")                     # BL-176: the peek's list shows names only
        self.assertIn("UAT start", self.result["msOpts"])
        self.assertEqual(self.result["msSel"], "UAT start")

    def test_pickers_list_project_people_first(self):
        r = self.result
        self.assertIn("Sam", r["defPeople"])                            # from the register's Key stakeholders
        self.assertEqual(r["firstNames"], r["defPeople"])

    def test_ask_autocomplete(self):
        r = self.result
        self.assertGreater(r["acAll"], 40)                               # "/" lists everything, grouped by skill
        self.assertGreaterEqual(r["acGroups"], 7)
        self.assertIn("weekly report", r["acWee"])
        self.assertEqual(r["acCodes"], ["client report ABC", "client report DEF"])
        self.assertTrue(all(x.startswith("mark ABC-A-") and x.endswith(" done") for x in r["acMark"]) and r["acMark"])
        self.assertTrue(r["acApprove"])
        self.assertEqual(r["acPicked"], ["sweep mail for ABC", "ABC"])   # 2nd suggestion; the code is selected to type over
        self.assertEqual(r["acEsc"], [True, True])                      # Esc closes the list, not the chat

    def test_current_state_edited_in_place(self):
        r = self.result
        self.assertEqual(r["inplace"][:2], [True, False])                 # BL-47: in the card, no side panel
        self.assertGreaterEqual(r["inplace"][2], 14)                      # the fuller toolbar
        self.assertEqual(r["mdNew"], "### Next steps\n\n#### Detail\n\n##### Fine print\n\n> Hold the date\n\nWas ~~late~~, see [the plan](https://example.com/p)."
                                     "\n\n- Data\n  - Masked extract\n- UAT")
        self.assertEqual(r["guard"], ["cockpit", True])                   # unsaved: Work waits
        self.assertEqual(r["kept"], ["cockpit", True])
        self.assertEqual(r["discarded"], ["work", None])
        self.assertEqual(r["htmlNew"], '<h3>Next</h3><blockquote>Quote</blockquote><ul><li>a<ul><li>b</li></ul></li><li>c</li></ul>'
                                       '<p>See <a href="https://e.com" target="_blank" rel="noopener noreferrer">x</a> and <s>old</s>.</p>')

    def test_generated_draft_in_the_editor(self):
        md, src, dirty = self.result["gen"]
        self.assertEqual(md, "Recovery is **on track** since 05-10-2026.")              # dates shown DD-MM-YYYY
        self.assertIn("2026-10-05 Steering.docx", src)
        self.assertTrue(dirty)                                                         # not saved until Alan saves

    def test_health_checked_against_evidence(self):
        r = self.result
        self.assertIn("On track, but the evidence suggests", r["evidence"])          # BL-52
        self.assertIn("Give a reason for rating it better", r["evidenceBlock"])
        self.assertFalse(r["evidenceOk"])                                           # worse or equal: no warning

    def test_inbox_view(self):
        self.assertGreaterEqual(self.result["inboxRows"], 1)
        self.assertEqual(self.result["inboxHash"], "#intake-review")   # #232-C: the one page's address; #intake and #inbox still open it (test_intake_review_wiring.py)

    def test_work_filters_fixed(self):
        r = self.result
        self.assertTrue(r["f62search"])                                        # BL-62: dates found as shown
        self.assertEqual(r["f62raidClean"], 0)                                 # nothing carries to another tab
        self.assertEqual(r["f62kept"], ["High"])                               # coming back keeps the tab's filters
        self.assertEqual(r["f62none"], ["", "No workstream"])
        self.assertEqual(r["f62closedDue"], "closed")                          # closed items aren't overdue or later
        self.assertEqual(r["f62clear"], ["open", 0, 0])                        # Clear all: back to All open, the first view
        self.assertEqual(r["f62future"], [False, True])                        # future decisions aren't "last 7 days"

    def test_command_palette_reaches_everything(self):
        go, views, acts, ms, files, inbox = self.result["ck"]
        self.assertIn("Go to|Intake", go)   # #232-C: one entry for the one page
        self.assertIn("Go to|Your commitments", go)
        self.assertIn("Views|Actions: Overdue", views)
        self.assertEqual(sorted(acts), ["Actions|Edit current state: ABC", "Actions|Generate current state: ABC"])
        self.assertTrue(ms and ms[0].startswith("Milestones|ABC-M-001"))
        self.assertTrue(files and inbox)

    def test_panels_open_on_the_right(self):
        self.assertEqual(self.result["panelRight"], [True, True])         # BL-44

    def test_rich_text_current_state(self):
        self.assertEqual(self.result["md"], "Build is **late** and *risky*.\n\n- Data access\n- UAT **prep**\n\n1. Escalate")
        self.assertEqual(self.result["html"], "<p>Para with <b>bold</b> and <i>it</i> and file_name.</p>"
                                              "<ul><li>one</li><li>two</li></ul><ol><li>first</li></ol>")

    def test_pencil_icons_on_editable_tiles(self):
        self.assertEqual(self.result["pencils"], ["Generate needs the live server", "Edit current state", "Edit health and project details"])  # BL-21, 23, 61; images are added in the editor (BL-63); BL-186: the milestone card's pencil opens its page
        self.assertEqual(self.result["mvpencil"], "Open milestones: Plan and Movement")
        self.assertFalse(self.result["oldEdit"])

    def test_combinable_filters_views_and_sorting(self):
        r = self.result
        self.assertEqual(r["f1open"], None)                                          # All open (Open only) + overdue: Custom
        self.assertEqual(r["f1"][0], "overdue")                                      # Open and Delayed + overdue IS the Overdue view
        self.assertRegex(r["f1"][1], r"^Showing \d+ of \d+$")
        self.assertIn("Due: Overdue", r["f1"][2])
        self.assertTrue(any(c[0].startswith("Open") for c in r["counts"]))         # counts in the Status menu
        self.assertEqual(r["presetIsFilters"], ["Delayed,Open", "overdue", "overdue"])   # a view is just filters
        self.assertEqual(r["mineOverdue"][0], None)                                  # Overdue + an owner: Custom
        self.assertTrue(r["mineOverdue"][1])
        self.assertEqual(r["sortAsc"], sorted(r["sortAsc"], key=str.lower))
        self.assertEqual(r["sortDesc"], sorted(r["sortDesc"], key=str.lower, reverse=True))
        self.assertTrue(r["sortHash"] and r["sortOff"])
        self.assertEqual(r["parsedF"]["fx"], {"st": ["Open", "Delayed"], "due": ["overdue"], "o": ["Sara Example"]})
        self.assertEqual(r["parsedF"]["sort"], {"col": "due", "dir": "asc"})
        self.assertEqual(r["saved"][:2], ["saved:Stuck", True])
        self.assertIn('"name":"Stuck","f":{"st":["Cancelled"]}', r["saved"][2])
        saved = json.loads(self.result["files"]["system/config/settings.json"])["work"]["saved_views"]["actions"]
        self.assertEqual(saved, [{"name": "Stuck", "f": {"st": ["Cancelled"]}, "lay": "list", "g": "due", "o": None,     # BL-103: a saved view keeps its layout and grouping
                                  "lg": "none", "sg": "none", "lsg": "none"}])                                            # BL-128, BL-129: its order, List grouping and sub-groups

    def test_more_filters(self):
        self.assertEqual(self.result["more"], ["Workstream", "Source", "Client-visible", "Stale", "Last updated", "Raised", "Milestone", "People I follow",
                                               "Due between", "Raised between", "Closed between"])   # + Filter (VIP: BL-99; the picker and its new fields: BL-130; Closed between: BL-190)
        self.assertEqual(self.result["dr"], ["2099-01-01", 0, True])

    def test_filters_and_column_order(self):
        r = self.result
        self.assertEqual(r["projRows"], ["DEF-A-001"])                 # project filter
        self.assertTrue(r["clearShown"])
        self.assertEqual(r["twoLabel"], "2 projects")                  # multi-select (BL-19)
        self.assertGreater(r["twoRows"], 0)
        self.assertEqual(r["priLabel"], "Urgent, High")
        self.assertTrue(r["bothRows"])                                 # project and priority combine
        self.assertTrue(r["afterClear"] >= 1 and r["clearHidden"])     # Clear all: back to the default view (BL-62)
        self.assertEqual(r["cols"][:2], ["pr", "t"])                    # Priority moved before the title

    def test_today_day_view(self):
        d = self.result["day"]
        self.assertTrue(d["head"].startswith("Three meetings, "))                     # all-day items aren't counted
        self.assertEqual(d["dots"], 3)
        self.assertEqual(d["cols"], ["10:00 – 11:00", "13:00 – 14:00", "15:00 – 15:30"])
        self.assertTrue(d["proj"])                                                   # "ABC steering" links to ABC
        self.assertIn("Office closed", d["allDay"])
        self.assertEqual(d["sections"], 8)    # BL-319: To decide, First thing (BL-295), Decisions needed (BL-210) and the brief's five (BL-72); You owe and Waiting on now sit inside Your commitments
        self.assertEqual(self.result["dayNone"], [0, True])                          # no calendar: one line, no timeline (BL-151)

    def test_work_search(self):
        r = self.result
        self.assertEqual(len(r["qId"]), 1)                              # by ID, any case
        self.assertTrue(r["qWords"])                                    # every word, any order
        self.assertEqual(r["qNone"], [0, True, True, True])             # empty message, Clear filters, in the address
        self.assertEqual(r["qEsc"], ["", "", True])                     # Esc clears
        self.assertEqual(r["qClear"], ["", ""])                         # Clear filters clears the search
        self.assertEqual(r["qParse"], "steering pack")

    def test_ask_creaite_stream_and_confirmation(self):
        r = self.result
        run = r["askBody"].pop("run")
        self.assertEqual(r["askBody"], {"message": "Close ABC-A-001", "session": None, "chat": None, "confirmed": None})
        self.assertRegex(run, r"^r-[a-z0-9]+-[a-z0-9]+$")                # BL-33: each request has a run ID
        self.assertIn("✓ 1 stepRunning tracker.py read actions", r["chat"])   # steps fold into one line that opens
        self.assertTrue(r["quip"][0] and r["quip"][0] in r["quip"][1])             # a rotating quip, not "Working…"
        self.assertIn("Here's the plan for 09-10-2026.", r["chat"])      # dates shown DD-MM-YYYY
        self.assertEqual(r["card"], ["Close ABC-A-001"])
        self.assertEqual(r["session"], "s-9")

    def test_chat_panel_resizable_and_remembered(self):
        r = self.result
        self.assertEqual(r["chatW"], [440, 440, "Resize ask creaite"])
        self.assertEqual(r["chatMax"][0], r["chatMax"][1])
        self.assertEqual(r["chatReset"], [420, 420])

    def test_reattach_to_a_running_request(self):
        r = self.result
        self.assertEqual(r["attachLog"], ["Earlier", "Earlier answer", "Long job", "✓ 1 stepRunning report.py weekly-data ABC",
                                          "All done."])                     # BL-37: no duplicate of the half entry
        self.assertEqual(r["attachEnd"], [False, True, ["r-att-1"]])         # indicator off, the finished badge (BL-139), acknowledged

    def test_stop_a_running_request(self):
        self.assertEqual(self.result["stopBtn"], "Stop")
        self.assertEqual(self.result["afterStop"], ["Send", 1, True, True])   # stopped, partial reply kept, chat open

    def test_new_chat_and_history(self):
        r = self.result
        self.assertEqual(r["afterNew"], {"session": None, "chat": None, "msgs": 0})   # BL-20: New chat starts afresh
        self.assertEqual(r["hist"], ["Close ABC-A-00105-10-2026 09:30 · 2 messages"])  # title, then the date line
        self.assertEqual((r["reopened"]["session"], r["reopened"]["chat"]), ("s-12", "s-9"))  # resumes its session
        self.assertTrue(r["histKeepsChat"] and r["histClosed"])          # BL-32: a dropdown over the current chat
        self.assertEqual(r["reopened"]["log"], ["Close ABC-A-001", "✓ 1 stepRunning tracker.py apply", "Done on 09-10-2026."])

    def test_navigation(self):
        r = self.result
        self.assertEqual(r["navH1"], "#cockpit=ABC")
        self.assertEqual(r["navWork"][:4], ["work", "raid", "open", ["ABC"]])          # project page → Work, filtered
        self.assertEqual(r["navWork"][4], "#work=raid&v=open&p=ABC&from=ABC")
        self.assertEqual(r["navWork"][5], "Projects›ABC›RAID")                          # breadcrumb
        self.assertEqual(r["navItem"], f"#work=raid&v=open&p=ABC&from=ABC&item={r['rid']}")  # item replaces the entry
        self.assertEqual(r["navBack"], ["cockpit", "ABC", "#cockpit=ABC"])               # Back: the project page
        self.assertEqual(r["navFwd"], ["work", "raid", r["rid"], r["navItem"]])        # Forward: Work with the item open
        self.assertEqual(r["navBlocked"], ["work", True, True, True])                   # a typed new item: Back asks first
        self.assertEqual(r["navPanel"], ["cockpit", "DEF"])                             # item → its project
        self.assertEqual(r["navSw"], ["ABC", "DEF"])                                    # ] wraps to ABC, [ back to DEF
        self.assertTrue(r["navSee"] and all(t.startswith("All ") for t in r["navSee"]))
        self.assertEqual({k: r["navParse"][k] for k in ("v", "wt", "wv", "p", "from")},
                         {"v": "work", "wt": "raid", "wv": "open", "p": ["ABC"], "from": "ABC"})
        self.assertEqual(r["navParse"]["item"], {"k": "raid", "id": r["rid"]})

    def test_project_page_actions_capped(self):
        due, head, shown = self.result["cap"]
        self.assertTrue(head.endswith(f"· {due}"))
        self.assertGreaterEqual(due, 2)
        if due > 1:
            self.assertEqual(shown, 1)
            self.assertEqual(self.result["capMore"], f"+{due - 1} more — see all ›")
            self.assertEqual(self.result["capWork"], ["work", ["overdue", "soon"], ["ABC"], True])

    def test_settings_written_with_backup_and_log(self):
        files = self.result["files"]
        self.assertEqual(json.loads(files["system/config/settings.json"])["review"]["stale_after_days"], 10)
        self.assertTrue(any(k.startswith("system/backups/settings-") for k in files))
        log = [json.loads(ln) for ln in files["system/config/settings-log.jsonl"].splitlines()]
        self.assertEqual((log[-1]["key"], log[-1]["old"], log[-1]["new"]), ("review.stale_after_days", 7, 10))

    def test_themes(self):
        r = self.result
        self.assertEqual(r["themeDefault"], {"palette": "creaite", "attr": "creaite", "options": ["Brightwater", "creaite", "Notion", "Linear", "Cursor", "Claude", "Apple", "Retro Arcade", "Thermo Scan"],
                                             "ck": ["Theme: Brightwater", "Theme: creaite", "Theme: Notion", "Theme: Linear", "Theme: Cursor",
                                                    "Theme: Claude", "Theme: Apple", "Theme: Retro Arcade",
                                                    "Theme: Thermo Scan"]})
        self.assertEqual(r["themePicked"], {"palette": "Test theme", "attr": "Test theme", "saved": "Test theme"})
        self.assertEqual(r["themeUnknown"], "creaite")          # an unknown name falls back to creaite
        self.assertEqual(r["themeOld"], ["creaite", "creaite", "creaite"])      # and so do the three retired names (BL-142)

    def test_apply_reaches_the_database_and_undo_reverses_it(self):
        v = self.v
        for path, text in self.result["files"].items():
            if path.startswith("system/staging/"):
                (v.root / path).write_text(text, encoding="utf-8")
        before = {t: v.rows(t) for t in ("actions", "projects")}
        out = v.run("apply").stdout
        self.assertIn("written", out)
        acts = {a["id"]: a for a in v.rows("actions")}
        self.assertEqual((acts["ABC-A-001"]["owner"], acts["ABC-A-001"]["due_date"]), ("Sara Example", "2026-11-20"))
        self.assertIn("Book the steering room", [a["description"] for a in acts.values()])
        abc = next(p for p in v.rows("projects") if p["code"] == "ABC")
        self.assertEqual((abc["health"], abc["health_reason"]), ("At risk", "Data access still late"))
        self.assertIn("Recovery plan agreed", (v.root / ABC / "CLAUDE.md").read_text(encoding="utf-8"))
        v.run("undo")
        # BL-176: ABC-A-001 had two proposals in this apply (each edit is its own); tracker.py's undo then puts updated_at back to
        # the middle stamp (BUILD › Sprint peek › Open), so the values are compared without it
        strip = lambda rows: [{k: x for k, x in r.items() if k != "updated_at"} for r in rows]  # noqa: E731
        self.assertEqual({t: strip(v.rows(t)) for t in ("actions", "projects")}, {t: strip(rows) for t, rows in before.items()})
        self.assertNotIn("Recovery plan agreed", (v.root / ABC / "CLAUDE.md").read_text(encoding="utf-8"))


class CreaiteTheme(unittest.TestCase):
    """creaite (was creaite teal, BL-142): the guides' palette and type, contrast in both modes, and Today's own tokens set too."""
    @classmethod
    def setUpClass(cls):
        import re
        css = readable_page()      # BL-231: the source; the bundle reprints the code
        blocks = re.findall(r':root\[data-palette="creaite"\](?::not\(\[data-theme="light"\]\)|\[data-theme="dark"\])?\{([^}]*)\}', css)
        cls.light, cls.sysdark, cls.dark = ({k: v.strip() for k, v in re.findall(r"--([a-z-]+):([^;]+);", b)} for b in blocks[:3])
        cls.css = css

    def test_guide_tokens_and_type(self):
        self.assertEqual((self.light["bg"], self.light["ink"], self.light["line"], self.light["accent"], self.light["accent-soft"]),
                         ("#F3F6F7", "#14212A", "#D7DFE3", "#0B6E7F", "#DCEFF2"))
        self.assertEqual((self.dark["bg"], self.dark["surface"], self.dark["accent"]), ("#0F1518", "#171E22", "#5FC4D6"))
        self.assertTrue(self.light["display"].startswith('"Schibsted Grotesk"') and self.light["font"].startswith('"Source Sans 3"'))
        self.assertIn('{id:"creaite",swatch:["#F3F6F7","#FFFFFF","#0B6E7F","#DCEFF2"]}', self.css)

    def test_today_follows_the_theme(self):
        days = ("day-page", "day-band", "day-ink", "day-muted", "day-rule", "day-sun", "day-past")
        for name, t in (("light", self.light), ("system dark", self.sysdark), ("dark", self.dark)):
            t = {**t, "day-ink": t["ink"], "day-muted": t["muted"], "day-rule": t["line"]}   # BL-325: aliases of --ink, --muted and --line, set once in the base
            self.assertTrue(all(k in t for k in days), f"{name}: Today's tokens not all set")
        self.assertEqual((self.light["day-page"], self.light["day-sun"], self.dark["day-sun"]), ("#F3F6F7", "#0B6E7F", "#5FC4D6"))
        self.assertEqual(self.sysdark, self.dark)                                    # the two dark blocks agree
        for name, t in (("light", self.light), ("dark", self.dark)):
            t = {**t, "day-ink": t["ink"], "day-muted": t["muted"]}                  # BL-325: aliases, set once in the base
            for fg in ("day-ink", "day-muted", "day-sun"):
                for g in ("day-page", "day-band"):
                    self.assertGreaterEqual(BrightwaterTheme.ratio(t[fg], t[g]), 4.5, f"{name}: --{fg} on --{g}")

    def test_contrast_in_both_modes(self):
        r = BrightwaterTheme.ratio
        for name, t in (("light", self.light), ("dark", self.dark)):
            for fg in ("ink", "muted", "accent", "bad", "warn", "ok"):
                for g in ("bg", "surface", "sunk", "accent-soft"):
                    self.assertGreaterEqual(r(t[fg], t[g]), 4.5, f"{name}: --{fg} on --{g}")
            self.assertGreaterEqual(r(t["accent-ink"], t["accent"]), 4.5, f"{name}: primary button")
            self.assertGreaterEqual(r(t["inverse-ink"], t["inverse"]), 4.5, f"{name}: snackbar")
            self.assertGreaterEqual(r(t["focus"], t["bg"]), 3, f"{name}: focus ring")


class CursorTheme(unittest.TestCase):
    """Cursor (2026-10-09), after dev/reference/themes/DESIGN-Cursor.md: the cream canvas and hairlines exactly in light, one orange, a derived dark set,
    contrast in both modes, Today's tokens set too."""
    @classmethod
    def setUpClass(cls):
        import re
        css = readable_page()      # BL-231: the source; the bundle reprints the code
        blocks = re.findall(r':root\[data-palette="Cursor"\](?::not\(\[data-theme="light"\]\)|\[data-theme="dark"\])?\{([^}]*)\}', css)
        cls.light, cls.sysdark, cls.dark = ({k: v.strip() for k, v in re.findall(r"--([a-z-]+):([^;]+);", b)} for b in blocks[:3])
        cls.css = css

    def test_design_tokens(self):
        t = self.light
        self.assertEqual((t["bg"], t["surface"], t["sunk"], t["ink"], t["muted"], t["line"], t["line-strong"], t["brand"], t["btn"]),
                         ("#F7F7F4", "#FFFFFF", "#EFEEE8", "#26251E", "#5A5852", "#E6E5E0", "#CFCDC4", "#F54E00", "#D04200"))
        self.assertNotEqual(t["bg"].upper(), "#FFFFFF")                              # the design: cream, never white
        self.assertEqual(self.dark["brand"], "#F54E00")                              # one orange in both modes
        self.assertEqual(t["shadow-card"], "none")                                   # hairline-only depth
        self.assertTrue(t["font"].startswith('"CursorGothic","Inter"'))
        self.assertIn("JetBrains Mono", t["mono"])
        self.assertIn('{id:"Cursor",swatch:["#F7F7F4","#FFFFFF","#F54E00","#FDEDE4"]}', self.css)
        self.assertEqual(self.sysdark, self.dark)                                    # the two dark blocks agree

    def test_today_follows_the_theme(self):
        days = ("day-page", "day-band", "day-ink", "day-muted", "day-rule", "day-sun", "day-past")
        for name, t in (("light", self.light), ("dark", self.dark)):
            t = {**t, "day-ink": t["ink"], "day-muted": t["muted"], "day-rule": t["line"]}   # BL-325: aliases of --ink, --muted and --line, set once in the base
            self.assertTrue(all(k in t for k in days), f"{name}: Today's tokens not all set")
            for fg in ("day-ink", "day-muted", "day-sun"):
                for g in ("day-page", "day-band"):
                    self.assertGreaterEqual(BrightwaterTheme.ratio(t[fg], t[g]), 4.5, f"{name}: --{fg} on --{g}")

    def test_contrast_in_both_modes(self):
        r = BrightwaterTheme.ratio
        for name, t in (("light", self.light), ("dark", self.dark)):
            for fg in ("ink", "muted", "faint", "accent", "bad", "warn", "ok"):
                for g in ("bg", "surface", "sunk", "accent-soft"):
                    self.assertGreaterEqual(r(t[fg], t[g]), 4.5, f"{name}: --{fg} on --{g}")
            self.assertGreaterEqual(r(t["accent-ink"], t["btn"]), 4.5, f"{name}: primary button text")
            self.assertGreaterEqual(r(t["accent-ink"], t["btn-hover"]), 4.5, f"{name}: primary button hover text")
            self.assertGreaterEqual(r(t["accent-ink"], t["accent"]), 4.5, f"{name}: accent fill")
            self.assertGreaterEqual(r(t["inverse-ink"], t["inverse"]), 4.5, f"{name}: snackbar")
            self.assertGreaterEqual(r(t["focus"], t["bg"]), 3, f"{name}: focus ring")
        self.assertLess(r("#FFFFFF", self.light["brand"]), 4.5)                      # why the button fill is the pressed orange, not the brand


class NewTheme:
    """BL-40a to BL-40d (sprint-polish-themes): what every theme added in 1.5.1 keeps. A subclass names the theme (THEME) and its
    design's own colours (design_tokens). Light, system dark and forced dark blocks; the two dark blocks agree; text 4.5:1 on every
    ground (faint included), the primary button (--btn under --btn-ink) and the accent fill, the snackbar, the count badge (--bad-ink
    on --bad), each health colour on its own soft ground, focus 3:1, white side panel in light (BL-80), Today's own tokens."""
    THEME = None

    @classmethod
    def setUpClass(cls):
        import re
        css = readable_page()      # BL-231: the source; the bundle reprints the code
        name = re.escape(cls.THEME)
        blocks = re.findall(r':root\[data-palette="' + name + r'"\](?::not\(\[data-theme="light"\]\)|\[data-theme="dark"\])?\{([^}]*)\}', css)
        cls.light, cls.sysdark, cls.dark = ({k: v.strip() for k, v in re.findall(r"--([a-z-]+):([^;]+);", b)} for b in blocks[:3])
        cls.css = css

    @staticmethod
    def hue_gap(a, b):
        import colorsys
        h = [colorsys.rgb_to_hsv(*(int(x.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)))[0] * 360 for x in (a, b)]
        d = abs(h[0] - h[1])
        return min(d, 360 - d)

    def test_three_blocks_and_a_listed_theme(self):
        self.assertEqual(self.sysdark, self.dark)                                    # the two dark blocks agree
        self.assertIn('{id:"%s",swatch:[' % self.THEME, self.css)
        self.assertEqual(self.light["surface"], "#FFFFFF")                          # BL-80: the side panel is white in light mode
        for t in (self.light, self.dark):
            self.assertFalse([k for k, v in t.items() if "url(" in v or "@import" in v])   # no external resources

    def test_today_follows_the_theme(self):
        days = ("day-page", "day-band", "day-ink", "day-muted", "day-rule", "day-sun", "day-past")
        for name, t in (("light", self.light), ("dark", self.dark)):
            t = {**t, "day-ink": t["ink"], "day-muted": t["muted"], "day-rule": t["line"]}   # BL-325: aliases of --ink, --muted and --line, set once in the base
            self.assertTrue(all(k in t for k in days), f"{name}: Today's tokens not all set")
            for fg in ("day-ink", "day-muted", "day-sun"):
                for g in ("day-page", "day-band"):
                    self.assertGreaterEqual(BrightwaterTheme.ratio(t[fg], t[g]), 4.5, f"{name}: --{fg} on --{g}")

    def test_contrast_in_both_modes(self):
        r = BrightwaterTheme.ratio
        for name, t in (("light", self.light), ("dark", self.dark)):
            for fg in ("ink", "muted", "faint", "accent", "bad", "warn", "ok"):
                for g in ("bg", "surface", "sunk", "accent-soft"):
                    self.assertGreaterEqual(r(t[fg], t[g]), 4.5, f"{name}: --{fg} on --{g}")
            for fg, g in (("btn-ink", "btn"), ("btn-ink", "btn-hover"), ("accent-ink", "accent"), ("inverse-ink", "inverse"), ("bad-ink", "bad"),
                          ("bad", "bad-soft"), ("warn", "warn-soft"), ("ok", "ok-soft"), ("ink", "warn-soft"), ("muted", "warn-soft"), ("accent", "surface")):
                self.assertGreaterEqual(r(t[fg], t[g]), 4.5, f"{name}: --{fg} on --{g}")
            self.assertGreaterEqual(r(t["focus"], t["bg"]), 3, f"{name}: focus ring")
            self.assertGreaterEqual(r(t["focus"], t["surface"]), 3, f"{name}: focus ring on a card")
            self.assertNotEqual(t["warn"].upper(), t["accent"].upper(), f"{name}: warn stays distinct from the accent")
            self.assertTrue(self.hue_gap(t["accent"], t["warn"]) >= 40 or r(t["accent"], t["warn"]) >= 1.5,
                            f"{name}: accent and warn are two colours (the Flow chart's open and closed bars, test_pages)")

    def test_design_tokens(self):
        for (mode, key), value in self.design_tokens().items():
            self.assertEqual((self.light if mode == "light" else self.dark)[key].upper(), value.upper(), f"{mode} --{key}")


class ClaudeTheme(NewTheme, unittest.TestCase):
    """Claude (BL-40a), after dev/reference/themes/DESIGN-Claude.md: the cream canvas, warm ink and hairlines exactly in light, one coral,
    a derived dark set from the design's own dark surfaces."""
    THEME = "Claude"

    def design_tokens(self):
        return {("light", "bg"): "#FAF9F5", ("light", "ink"): "#141413", ("light", "muted"): "#6C6A64", ("light", "line"): "#E6DFD8",
                ("light", "brand"): "#CC785C", ("light", "btn"): "#A9583E", ("light", "inverse"): "#181715", ("dark", "bg"): "#181715",
                ("dark", "brand"): "#CC785C", ("dark", "ink"): "#FAF9F5", ("dark", "muted"): "#A09D96"}

    def test_why_coral_is_a_mark(self):
        r = BrightwaterTheme.ratio
        self.assertLess(r(self.light["brand"], self.light["bg"]), 4.5)                # coral on cream: not text
        self.assertLess(r("#FFFFFF", self.light["brand"]), 4.5)                       # nor under white text: the button is the pressed coral


class AppleTheme(NewTheme, unittest.TestCase):
    """Apple (BL-40b), after dev/reference/themes/DESIGN-Apple.md: parchment and white, near-black ink, one Action Blue, flat cards,
    a derived dark set from the design's own dark tiles and on-dark blue."""
    THEME = "Apple"

    def design_tokens(self):
        return {("light", "bg"): "#F5F5F7", ("light", "ink"): "#1D1D1F", ("light", "line"): "#E0E0E0", ("light", "accent"): "#0066CC",
                ("light", "btn"): "#0066CC", ("light", "focus"): "#0071E3", ("light", "shadow-card"): "none",
                ("dark", "surface"): "#1C1C1E", ("dark", "accent"): "#2997FF", ("dark", "ink"): "#F5F5F7"}

    def test_one_blue_and_a_pill_primary(self):
        self.assertIn(':root[data-palette="Apple"] .btn.primary{background:var(--btn);border-color:var(--btn);color:var(--btn-ink);border-radius:var(--r-pill)', self.css)
        self.assertLess(BrightwaterTheme.ratio("#7A7A7A", "#FFFFFF"), 4.5)           # why the design's muted grey is darkened
        self.assertNotRegex(self.css, r"@font-face[^}]*SF Pro")                       # never embedded: a system font


class RetroArcadeTheme(NewTheme, unittest.TestCase):
    """Retro Arcade (BL-40c), after dev/reference/themes/DESIGN-Retro-Arcade.md: black, white type, the pure arcade colours where they
    pass (yellow, lime, the blue as a fill, cyan as a border) and lighter ones where they don't; a derived light set."""
    THEME = "Retro Arcade"

    def design_tokens(self):
        return {("dark", "bg"): "#000000", ("dark", "ink"): "#FFFFFF", ("dark", "brand"): "#0000FF", ("dark", "btn"): "#0000FF",
                ("dark", "warn"): "#FFFF00", ("dark", "ok"): "#00FF00", ("dark", "line-strong"): "#00FFFF", ("dark", "focus"): "#FFFF00",
                ("light", "brand"): "#0000FF", ("light", "accent"): "#0000FF", ("light", "ink"): "#000000"}

    def test_the_pure_colours_that_fail_are_never_text(self):
        r, d = BrightwaterTheme.ratio, self.dark
        self.assertLess(r("#0000FF", d["bg"]), 4.5)                                 # electric blue on black: a fill, not text
        self.assertNotEqual(d["accent"], "#0000FF")
        self.assertLess(r("#FF0000", d["sunk"]), 4.5)                               # cherry red on the raised surface
        self.assertNotEqual(d["bad"], "#FF0000")
        self.assertGreaterEqual(r("#FFFF00", d["brand"]), 4.5)                      # the active page's yellow icon on its blue tile
        self.assertGreaterEqual(r("#FFFFFF", d["brand"]), 4.5)                      # and its white label


class ThermoScanTheme(NewTheme, unittest.TestCase):
    """Thermo Scan (BL-40d), after dev/reference/themes/DESIGN-Thermo-Scan.md: the navy ground, white type, golden yellow for calls to
    action, the thermal spectrum (cool blue, green, hot red) where it passes; a derived light set."""
    THEME = "Thermo Scan"

    def design_tokens(self):
        return {("dark", "bg"): "#050B26", ("dark", "ink"): "#FFFFFF", ("dark", "accent"): "#FFC800", ("dark", "btn"): "#FFC800",
                ("dark", "ok"): "#00FF00", ("dark", "focus"): "#FFC800", ("light", "btn"): "#FFC800", ("light", "ink"): "#050B26"}

    def test_the_pure_colours_that_fail_or_collide_are_moved(self):
        r, d = BrightwaterTheme.ratio, self.dark
        self.assertLess(r("#0000FF", d["bg"]), 3)                                   # cool blue on navy: decoration only
        self.assertNotIn("#0000FF", (d["accent"], d["ok"], d["warn"], d["bad"]))
        self.assertLess(r("#FF0000", d["sunk"]), 4.5)                               # hot red on a raised panel
        self.assertNotEqual(d["bad"], "#FF0000")
        self.assertNotEqual(d["warn"], d["accent"])                                 # the design's warning is its CTA yellow: moved to orange
        self.assertLess(r("#FFC800", self.light["surface"]), 4.5)                   # gold on white: a fill under navy, never text
        self.assertGreaterEqual(r(self.light["btn-ink"], self.light["btn"]), 4.5)


class BrightwaterTheme(unittest.TestCase):
    """The contrast helper the other theme tests share. Alan, 16-10-2026 (spend): Notion, Linear and Brightwater are no longer tested
    (their token and contrast tests are gone; the themes themselves stay in the product); theme tests run on creaite and Cursor."""
    @staticmethod
    def ratio(a, b):
        def lum(h):
            c = [int(h.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
            c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
            return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
        x, y = sorted((lum(a), lum(b)), reverse=True)
        return (x + 0.05) / (y + 0.05)


if __name__ == "__main__":
    unittest.main(verbosity=2)
