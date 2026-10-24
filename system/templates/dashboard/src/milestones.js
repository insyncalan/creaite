// @ts-check
/* milestones.js (BL-231 step 2b), moved from script/ by dev/tools/convert_area.py: 0051-milestones-bl-23-proposals-like-every-ot.js, 0172-bl-250-a-sprint-milestone-ui.js, 0184-bl-174-sprint-milestones.js, 0185-bl-178-sprint-milestones.js, 0186-bl-186-sprint-milestones.js, 0187-bl-184-sprint-milestones.js, 0188-after-bl-184.js, 0189-bl-245-sprint-milestone-ui.js, 0190-after-bl-245.js, 0191-bl-274-sprint-ui-sweep.js, 0192-after-bl-274.js.
   Unchanged apart from `export`, `shared.` for the shared state (core/state.js) and the load-time steps, now in
   boot…() functions that src/main.js calls in today's order. */
import { actId } from "./activity.js";
import { step } from "./ask.js";
import { peekFrame } from "./components/Peek.jsx";
import { drawTabs } from "./components/Tabs.jsx";
import { A, P, peopleAll, pName, R } from "./core/data.js";
import { $, $$, addHTML, esc, html, ibtn, ic, ICONS, paintIcons, putHTML, raw } from "./core/dom.js";
import { autoGrow, DATE_HELP, onCmdEnter, srcHTML } from "./core/fields.js";
import { go, hashOf, navState, navWrite, parseHash, restoreNav } from "./core/nav.js";
import { D, DATE, fd, fdText, MOD, mScroll, reduced, S, TODAY, typeWord } from "./core/page.js";
import { needVault, reloadData, renderBadge, save, snack, viaServer, vq, writeProposal } from "./core/server.js";
import { shared } from "./core/state.js";
import { draftStat } from "./drafts.js";
import { helpPanelOpen } from "./helpscreen.js";
import { drFcDraw, drSame, pkHistory, PKMON, pkShort, PKTABS, readForm } from "./panel.js";
import { closePanel, depWarn, chooseProject, renderCockpit } from "./projects.js";
import { nm, ownerFinal, PKAPPLIED, sw } from "./settings.js";
import { sneakMvAttach } from "./sneak.js";
import { ceClose, ceCommit, ceRead, items } from "./work.js";
/* ======================= milestones (BL-23): proposals like every other edit ======================= */
export const MSI={name:0,date:1,state:2,id:3,base:4,prog:5,st:6,ord:7,fc:8,at:9};
export function msFind(id){ for(const p of P){ const m=p.ms.find(m=>m[3]===id); if(m) return {p,m}; } return {}; }
export const msLinked=id=>[...A.filter(a=>a.ms===id).map(a=>["actions",a]),...R.filter(r=>r.ms===id).map(r=>["raid",r])];
/* BL-231 step 2b: the final versions, folded in from after-bl-245 (0190), which replaced the panel's at load */
export function openMilestone(id){ const {p}=msFind(id); if(!p) return; mvOpenPage(p.code,"plan",id); }
export function openNewMilestone(code){ mvOpenPage(code,"plan",null,{add:true}); }
export function msNextId(code){ const p=P.find(x=>x.code===code); const n=Math.max(0,...p.ms.filter(m=>m[3]&&/-M-\d{3}$/.test(m[3])).map(m=>+m[3].slice(-3)))+1; return `${code}-M-${String(n).padStart(3,"0")}`; }
export function msState(m){ m[1]=m[8]||m[4]||""; m[2]=m[6]==="Done"?"done":((m[14]&&["Slipped","Overdue"].includes(m[14].st))||(m[4]&&m[8]&&m[8]>m[4]))?"slip":""; }   /* BL-186: Missed is retired */
export async function msPanelSave(){ const f=readForm(); $$("#pFields .bad").forEach(e=>e.classList.remove("bad")); const bad=(n,msg)=>{ $("#f_"+n)?.classList.add("bad"); $("#pErr").textContent=msg; };
  if(f.fc&&!DATE.test(f.fc)) return bad("fc","Not a date creaite knows. "+DATE_HELP);
  if(shared.CUR.mode==="rebase"){ if(!f.fc) return bad("fc","Choose the new baseline date."); if(!f.reason) return bad("reason","Give a reason for rebaselining; it's kept in the history."); if(!String(f.with||"").trim()) return bad("with","Say who agreed the new date; a rebaseline records a decision."); return msSave({base:f.fc,fc:f.fc},"rebase",f.reason,{agreed_with:String(f.with).split(",").map(x=>x.trim()).filter(Boolean),reason:f.reason,source:`${S.me} (dashboard), ${TODAY}`}); }   /* BL-186: a rebaseline records a decision */
  if(!f.name) return bad("name","Name the milestone."); if(f.ord&&!/^\d+$/.test(f.ord)) return bad("ord","Order is a whole number.");
  if(f.pc!==""&&f.pc!==undefined&&!(/^\d+$/.test(f.pc)&&+f.pc<=100)) return bad("pc","% complete is a whole number from 0 to 100.");
  if(shared.CUR.mode==="msnew") return msCreate(f);
  return msSave({name:f.name,desc:f.desc,fc:f.fc||null,st:f.st,ord:f.ord,pc:f.pc}, "edit"); }
export async function msSave(f,how,note,rebaseline){ const {p,m}=msFind(shared.CUR.id), id=shared.CUR.id, d=shared.CUR.draft, ch={};
  if(f.name!==undefined&&f.name!==m[0]) ch.name=f.name; if(f.desc!==undefined&&(f.desc.trim()||null)!==(m[13]||null)) ch.description=f.desc.trim()||null;
  if(f.fc!==undefined&&(f.fc||null)!==(m[8]||null)) ch.forecast_date=f.fc||null;
  if(f.base!==undefined&&f.base!==m[4]) ch.baseline_date=f.base; if(f.st!==undefined&&f.st!==m[6]) ch.status=f.st;
  if(f.ord!==undefined&&+f.ord!==+m[7]) ch.sort_order=+f.ord;
  if(f.pc!==undefined){ const pc=f.pc===""||f.pc===null?null:+f.pc; if(pc!==(m[10]??null)) ch.percent_complete=pc; }   /* BL-29: blank = calculated */
  if(ch.status==="Done"&&!(ch.forecast_date||m[8])) ch.forecast_date=TODAY;   /* Done: today, if it had no date */
  if(ch.status==="Done"&&(ch.percent_complete??m[10])!==100) ch.percent_complete=100;   /* and 100% */
  if(!Object.keys(ch).length){ closePanel(); return; }
  const before=[...m], item={op:"update",table:"milestones",id,changes:ch,based_on:d.at}; if(note) item.note=note; if(rebaseline) item.rebaseline=rebaseline;
  const label=how==="rebase"?`${id} rebaselined to ${fd(ch.baseline_date)}`:how==="done"?`${id} done`:`${id} ${Object.keys(ch).map(k=>({name:"name",description:"description",forecast_date:"forecast",status:"status",sort_order:"order",baseline_date:"baseline",percent_complete:"% complete"})[k]).join(", ")} updated`;
  closePanel(); await save(label,[item],null,()=>{ if("name" in ch) m[0]=ch.name; if("description" in ch) m[13]=ch.description||""; if("forecast_date" in ch) m[8]=ch.forecast_date; if("baseline_date" in ch) m[4]=ch.baseline_date; if("status" in ch) m[6]=ch.status; if("sort_order" in ch) m[7]=ch.sort_order; if("percent_complete" in ch){ m[10]=ch.percent_complete; m[5]=ch.percent_complete??m[11]; m[12]=ch.percent_complete==null?"":`${ch.percent_complete}%, set by ${S.me.split(" ")[0]} on ${fd(TODAY)}`; } msState(m); },()=>{ m.splice(0,m.length,...before); }); }
export async function msRemove(){ const {p,m}=msFind(shared.CUR.id), id=shared.CUR.id, links=msLinked(id), idx=p.ms.indexOf(m);
  const items=[{op:"update",table:"milestones",id,changes:{status:"Cancelled"},based_on:shared.CUR.draft.at},...links.map(([t,x])=>({op:"update",table:t,id:x.id,changes:{milestone:null},based_on:x.updated_at}))];
  closePanel(); await save(`${id} removed (Cancelled)${links.length?`; ${links.length} item${links.length===1?"":"s"} unlinked`:""}`,items,null,()=>{ p.ms.splice(p.ms.indexOf(m),1); links.forEach(([,x])=>x.ms=null); },()=>{ p.ms.splice(idx,0,m); links.forEach(([,x])=>x.ms=id); }); }
export async function msCreate(f){ const p=P.find(x=>x.code===shared.CUR.code), id=msNextId(p.code), source=`${S.me} (dashboard), ${TODAY}`;
  const pc=f.pc===""||f.pc===undefined?null:+f.pc;
  if(pc!==null&&(!/^\d+$/.test(f.pc)||pc>100)){ $("#pErr").textContent="% complete is a whole number from 0 to 100."; return; }
  const values={project:p.code,name:f.name,description:(f.desc||"").trim()||null,baseline_date:f.fc||null,forecast_date:f.fc||null,status:f.st,sort_order:+(f.ord||0),percent_complete:pc,source};
  const m=[f.name,"","",id,f.fc||null,pc,f.st,+(f.ord||0),f.fc||null,null,pc,null,pc==null?"":`${pc}%, set by ${S.me.split(" ")[0]} on ${fd(TODAY)}`,(f.desc||"").trim()]; msState(m);
  closePanel(); await save(`${id} created`,[{op:"new",table:"milestones",values}],null,()=>{ p.ms.push(m); p.ms.sort((a,b)=>(+a[7]||0)-(+b[7]||0)||String(a[1]).localeCompare(String(b[1]))); },()=>{ p.ms.splice(p.ms.indexOf(m),1); }); }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootMilestones0051(){
document.addEventListener("click",e=>{ const n=e.target.closest("[data-msnew]"); if(n){ openNewMilestone(n.dataset.msnew); return; } const r=e.target.closest("[data-ms]"); if(!r) return;
  if(r.tagName==="A"){ if((e.metaKey||e.ctrlKey||e.shiftKey)&&(r.getAttribute("href")||"#")!=="#") return; e.preventDefault(); }   /* BL-144: as [data-open] */
  openMilestone(r.dataset.ms); });
document.addEventListener("keydown",e=>{ if(e.key==="Enter"&&e.target.matches&&e.target.matches("[data-ms]")) openMilestone(e.target.dataset.ms); });
}
/* ===== BL-250 A (sprint-milestone-ui) ===== one history feed everywhere: the peek's feed (All, Activity, Updates, Source) read
   by shared helpers, so the milestone editor (#mvPeek) and the project panel (openProject: health and its reason) show their own
   history the same way. All three read ACT (build_dashboard.activity, which already holds every table's change_log lines and the
   Current state edits from file_activity) through pkHistory (BL-250 B: ACT plus D.activity_older, so early history and "created"
   survive a long log): no new data. feedLines maps an item's lines; feedTabItems (the Tabs building block's tabs, BL-316) and
   feedListHtml draw the tabs and the list. A milestone's feed: Activity is each field change, Updates the reason given with a
   change (the note in the same apply, as Movement reads it), Source its creation and its source line; internal only, so it is not
   shown in Client view. A project's: Activity is health, its reason and the other fields, Updates the Current state edits and
   the weekly updates rows, Source its creation. Parts B (the 2000-row cap) and C (links and labels) are another sprint's. */
export function feedLines(lines,typeOf,textOf){ return lines.map(a=>{ const ch=String(a.change||a.what||"");
  return {type:typeOf(ch,a),who:a.by,html:`<span class="chg">${esc(textOf?textOf(ch,a):ch)}</span>`,when:a.at,state:a.reverted||a.undone?"undone":PKAPPLIED.has(a.apply_id)?"applied":""}; }); }
/* function declarations (hoisted): the peek can be drawn before this block runs (BL-176's "if(CUR&&pkOn()) drawPanel()" on load) */
export function feedTabItems(tab,attr,sel){ return PKTABS.map(([v,l])=>({id:v,label:l,tabId:tab===v?sel:undefined,data:{[attr]:v}})); }
export function feedListHtml(items,tab){ const icn={act:"pencil",upd:"msg",src:"filetext"}, L=items.filter(e=>tab==="all"||e.type===tab);
  return L.length?L.map(e=>`<div class="pk-fe${e.state==="undone"?" undone":""}" data-t="${e.type}"><span class="pk-fi" aria-hidden="true">${ic(icn[e.type]||"pencil")}</span><div><b>${esc(e.who)}</b> ${e.html}${e.when?`<span class="when">· ${esc(fd(e.when))}</span>`:""}${e.state==="staged"?'<span class="pk-pill st">waiting</span>':e.state==="applied"?'<span class="pk-pill ap">saved</span>':e.state==="undone"?'<span class="pk-pill un">undone</span>':""}${e.note?`<div class="sub">${esc(e.note)}</div>`:""}</div></div>`).join(""):'<div class="sub">Nothing here yet.</div>'; }
/* the feed outside the peek: a section with its own tabs (data-fdtab), remembered per host ("ms", "proj") for the session. It draws
   every entry once; a tab only changes attributes (the section's data-tab, which CSS reads, and the tabs' selection), so the
   entries are never drawn again for a tab. The milestone feed is drawn again with its editor; the project panel's with the panel. */
export const FDTAB={};
export function feedBlock(host,items){ const tab=FDTAB[host]||"all", sel="fdTabSel-"+host, has=new Set(items.map(e=>e.type));
  const none=["act","upd","src"].filter(t=>!has.has(t)).map(t=>`<div class="sub fd-none" data-none="${t}">Nothing here yet.</div>`).join("");
  return `<section class="fd-hist" data-fdhost="${host}" data-tab="${tab}" aria-label="History"><div class="tabhost" data-fdtabs></div><div class="pk-feed" role="tabpanel" aria-labelledby="${sel}">${items.length?feedListHtml(items,"all"):""}${items.length?none:'<div class="sub">Nothing here yet.</div>'}</div></section>`; }
/* BL-316: a feed's tabs are the Tabs building block, drawn into the section's [data-fdtabs] once its HTML is in the page (mountFeedTabs) */
export function feedTabsDraw(s){ const host=s.dataset.fdhost, tab=FDTAB[host]||"all", box=s.querySelector(":scope>[data-fdtabs]"); if(!box) return;
  drawTabs(box,{items:feedTabItems(tab,"fdtab","fdTabSel-"+host),selected:tab,onSelect:v=>feedTab(s,v),label:"History",className:"pk-tabs",tabClass:"pk-tab",wrap:true}); }
export function mountFeedTabs(root){ if(root) root.querySelectorAll("section.fd-hist[data-fdhost]").forEach(feedTabsDraw); }
export function feedTab(s,v){ FDTAB[s.dataset.fdhost]=v; s.dataset.tab=v; feedTabsDraw(s); }
export function mvFeedItems(m){ const out=feedLines(pkHistory(m.id),ch=>/^created\b/.test(ch)?"src":/^note:/.test(ch)?"upd":"act",ch=>ch.replace(/^note: /,"reason: "));
  if(m.src) out.push({type:"src",who:"Source",html:`<div class="pk-src">${srcHTML(m.src)}</div>`,when:""});
  return out; }
/* a project's lines: its own, and each weekly updates row's (keyed week|code), from ACT and the older history, newest first */
export function projHistory(code){ const wk=new RegExp(`^\\d{4}-\\d{2}-\\d{2}\\|${code}$`), ids=new Set([code]);
  shared.ACT.forEach(a=>{ const i=actId(a); if(wk.test(i)) ids.add(i); }); Object.keys((D.activity_older||{}).items||{}).forEach(i=>{ if(wk.test(i)) ids.add(i); });
  return [...ids].flatMap(i=>pkHistory(i).map(a=>({...a,_id:i}))).sort((a,b)=>String(b.at||"").localeCompare(String(a.at||""))); }
export function projFeedItems(code){ const wk=new RegExp(`^(\\d{4}-\\d{2}-\\d{2})\\|${code}$`);
  return feedLines(projHistory(code),(ch,a)=>wk.test(a._id)||ch==="current state updated"?"upd":/^created\b/.test(ch)?"src":"act",
    (ch,a)=>{ const w=wk.exec(a._id); return w?`weekly update, week ending ${fd(w[1])}: ${ch==="created"?(a.item?pkShort(a.item,120):"created"):ch}`:ch; }); }
/* ===== end BL-250 A ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootMilestones0172(){
/* BL-316: the feeds' tabs take their own clicks and keys (the Tabs building block) */
}
/* ===== BL-174 (sprint-milestones) ===== a page opened before a live server restart says so. The server's token is new at every
   start, so its requests are refused with {stale:true}; any such refusal (an apply, a save, the pulse) shows a banner under the
   header with the server's words and a Reload button, instead of a bare "Not allowed". */
shared.STALE=false;   /* BL-269 (sprint-live-updates): once a reply says stale, the page asks the server nothing more until reloaded */
export function staleShow(msg){ shared.STALE=true; const b=$("#staleAlert"); if(!b) return; $("#staleMsg").textContent=msg||"creaite was restarted since this page was opened. Reload the page (Cmd+R) and try again.";
  if(b.hidden){ b.hidden=false; b.classList.add("on"); } }
/* ===== end BL-174 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootMilestones0184(){
{ const f0=window.fetch.bind(window); window.fetch=async function(u,o){
    /* BL-269: stale, every /api call (the presence, pulse, VIP and file timers, the stream's retry) is answered here, never sent */
    // @ts-expect-error TS2339: the page calls fetch with a string or a Request (a URL object has no .url and would not be matched)
    if(shared.STALE&&String(typeof u==="string"?u:(u&&u.url)||"").includes("/api/")) return new Response(JSON.stringify({ok:false,stale:true,message:$("#staleMsg").textContent}),{status:403,headers:{"Content-Type":"application/json"}});
    const r=await f0(u,o);
    // @ts-expect-error TS2339: as above
    try{ if(r.status===403&&String(typeof u==="string"?u:(u&&u.url)||"").includes("/api/")){ const j=await r.clone().json().catch(()=>null); if(j&&j.stale) staleShow(j.message); } }catch(e){}
    return r; }; }
document.addEventListener("click",e=>{ if(e.target.closest&&e.target.closest("#staleReload")) location.reload(); });
}
/* ===== BL-178 (sprint-milestones) ===== one Esc leaves Work's cell editor in every browser. showPicker() opened the platform's
   native list, which on Windows and Linux takes the first Esc (and Tab) itself, so leaving took two. The cell's list is now shown
   in the page (a listbox select, size>1, placed under the cell), so every key reaches the page: Esc closes the editor, Tab goes on
   to the next cell. Arrows, Home, End and typing move through the list without saving; Enter or a click saves; a click on the
   value already chosen closes it. The same on macOS. */
export function ceListPlace(){ if(!shared.CE) return; const td=shared.CE.td, sels=[...td.querySelectorAll("select.celist")]; if(!sels.length) return;
  const r=td.getBoundingClientRect(); let left=Math.max(8,r.left);
  sels.forEach(s=>{ s.style.minWidth=Math.max(sels.length>1?110:r.width,140)+"px"; const h=s.offsetHeight, w=s.offsetWidth;
    let top=r.top; if(top+h>innerHeight-8) top=Math.max(8,r.bottom-h);
    if(left+w>innerWidth-8) left=Math.max(8,innerWidth-8-w);
    s.style.top=top+"px"; s.style.left=left+"px"; left+=w+4; }); }
 
/* ===== end BL-178 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootMilestones0185(){
/* ceOpen: this version is now work.js's own (BL-231 step 2b) */
addEventListener("resize",()=>ceListPlace());
document.addEventListener("scroll",()=>ceListPlace(),true);
/* keys move the selection without saving; Enter saves; a click saves (change) or, on the value already chosen, closes */
document.addEventListener("keydown",e=>{ const s=e.target; if(!shared.CE||!s.matches||!s.matches("#workTbl select.celist")) return;
  if(e.key==="Enter"){ e.preventDefault(); e.stopPropagation(); const p=ceRead(); if(p) ceCommit(p); return; }
  if(e.key!=="Escape"&&e.key!=="Tab"&&!e.metaKey&&!e.ctrlKey) s.dataset.kb="1"; },true);
document.addEventListener("change",e=>{ const s=e.target; if(s.matches&&s.matches("#workTbl select.celist")&&s.dataset.kb==="1"){ delete s.dataset.kb; e.stopImmediatePropagation(); } },true);
document.addEventListener("mousedown",e=>{ const s=e.target.closest&&e.target.closest("#workTbl select.celist"); if(s) delete s.dataset.kb; },true);
document.addEventListener("click",e=>{ const s=e.target.closest&&e.target.closest("#workTbl select.celist"); if(!s||!shared.CE) return;
  setTimeout(()=>{ if(shared.CE&&shared.CE.td.contains(s)&&s.dataset.kb!=="1"&&!s.closest(".ceset")){ const td=shared.CE.td; ceClose(true); const b=td.querySelector(".cebtn"); b&&b.focus(); } },0); });
}
/* ===== BL-186 (sprint-milestones) ===== Milestones: Plan and Movement. The spec is dev/mockups/milestones-views-mockup.html (v6),
   and this is its logic on the real data: each milestone's index 14 (build_dashboard.milestone_detail: the state from tracker.py's
   one reading, the suggestion, owner, achieved date, client view, Original, history and log).
   - The Plan (mvPlan) is one component, drawn by the cockpit's Milestones card and by the page, so the two can't drift apart.
   - The page is a view like the others: #milestones=<CODE>&v=plan|movement[&ms=<ID>] (Back, Forward, a reload and a link keep the
     page, the view and the open milestone), the breadcrumb Projects › <Project name> › Milestones, the project switcher; the rail
     keeps Projects selected.
   - Internal view or Client view (AUD) is one choice for the card and the page, remembered in this browser (Client when nothing is
     stored: BL-244, "client view (default)"); it changes the milestone card and the page only. Movement is internal only:
     unavailable in Client view. BL-244: only the Internal view is marked (a bright border and an INTERNAL VIEW pill); the Client
     view is the cockpit's plain card.
   - The editor (#mvPeek) sits in the peek's place and size. Every change is saved on its own with Undo (save(): a dashboard
     proposal, applied at once with auto-apply). A click outside closes it, except a click on another milestone (it switches), the
     first click while a calendar or the people list is open (it closes only that), and a change waiting for its reason (it shakes
     and says so). Dates come from a calendar, never typed. Decide what to do stages proposals for Review. */
export const MVWORD={achieved:"Achieved",ontrack:"On track",atrisk:"At risk",slipped:"Slipped",overdue:"Overdue"};
export const MVCWORD={achieved:"Achieved",ontrack:"On track",atrisk:"At risk",slipped:"Expected later",overdue:"Late"};
export const MVRANK={achieved:0,ontrack:1,atrisk:2,slipped:3,overdue:4};
export const MVKEY={"Achieved":"achieved","On track":"ontrack","At risk":"atrisk","Slipped":"slipped","Overdue":"overdue"};
export const mvT=iso=>iso?Date.parse(iso.slice(0,10)+"T00:00:00Z"):NaN, mvDays=(a,b)=>Math.round((mvT(a)-mvT(b))/864e5);
export function mvPref(k,d){ try{ const v=localStorage.getItem(k); return v===null?d:v; }catch(e){ return d; } }
export function mvPrefSet(k,v){ try{ localStorage.setItem(k,v); }catch(e){} }
/* var, not let: the page's first render (before this block runs) reaches mvCardHtml, which waits for MVREADY */
export var MVVIEWKEY="creaite.cockpit.milestones.view", MVDETKEY="creaite.cockpit.milestones.details"; shared.MVREADY=false;
export var MVDET=mvPref(MVDETKEY,"1")!=="0"; shared.MSCODE=null; shared.MSNEXT=null; shared.MVAUD=mvPref(MVVIEWKEY,"cli")==="int"?"int":"cli";
shared.MV={view:"plan",sel:null,rb:null,adj:null,peek:null,add:null,flow:null,pend:null,scroll:{},after:null,cwPend:false};
export const mvCode=()=>shared.VIEW==="milestones"?shared.MSCODE:shared.COCK;
/* the suggestion, as tracker.suggested_state reads the dates (used while a change waits to be applied) */
export function mvSuggest(m){ if(m.status==="Done") return "achieved"; if(m.agr&&m.agr<TODAY) return "overdue"; if(m.agr&&m.fc&&m.fc>m.agr) return "slipped"; return "ontrack"; }
export function mvOf(p,m){ const x=m[14]||{}; return {id:m[3],arr:m,p:p.code,n:m[0],desc:m[13]||"",owner:x.owner||"",agr:x.agr||m[4]||"",fc:x.fc||m[8]||m[4]||"",orig:x.orig||x.agr||m[4]||"",
  actual:x.actual||"",state:MVKEY[x.st]||"ontrack",sug:MVKEY[x.sug]||"ontrack",manual:!!x.set,why:x.why||"",client:!!x.client,cw:x.cw||"",cvis:!!x.cvis,
  pct:x.pc??null,note:x.note||"",src:x.src||"",range:x.range||null,hist:x.hist||[],log:x.log||[],moves:x.moves||0,rb:x.rb||null,status:m[6]||"Planned",at:m[9],ord:+m[7]||0}; }
export function mvAll(code){ const p=P.find(x=>x.code===code); return p?p.ms.filter(m=>m[3]).map(m=>mvOf(p,m)):[]; }
export const mvGet=(code,id)=>mvAll(code).find(m=>m.id===id);
export const mvWhen=m=>m.state==="achieved"?(m.actual||m.fc||m.agr):(m.agr||m.fc);
export const mvMismatch=m=>m.state!=="achieved"&&MVRANK[m.state]<MVRANK[m.sug];
/* what each view shows: the client sees client-visible milestones with their wording only (the client report's filter, in
   tracker.client_milestones, given here as cvis); Movement and the internal view show every one */
export function mvVis(code,cli,move){ return mvAll(code).filter(m=>!cli||move||m.cvis); }
export function mvOpen(code,cli,move){ return mvVis(code,cli,move).filter(m=>m.state!=="achieved").sort((a,b)=>(a.agr||a.fc||"9").localeCompare(b.agr||b.fc||"9")); }
/* #286: a milestone marker on the Plan strip and the Movement list names its type first, "Milestone: …", on hover (data-tip) and to a screen reader */
const MSW=typeWord("milestone");
export function mvShape(st,sz){ sz=sz||16;
  const p={achieved:'<circle cx="8" cy="8" r="7" fill="var(--ok-soft)" stroke="var(--ok)" stroke-width="1.5"/><path d="M4.6 8.2l2.3 2.3 4.5-4.7" fill="none" stroke="var(--ok)" stroke-width="1.8"/>',
   ontrack:'<circle cx="8" cy="8" r="6" fill="var(--ok)"/>',
   atrisk:'<path d="M8 1.5 15 14H1z" fill="var(--warn-soft)" stroke="var(--warn)" stroke-width="1.5" stroke-linejoin="round"/><path d="M8 6v4M8 11.6v.2" stroke="var(--warn)" stroke-width="1.6"/>',
   slipped:'<path d="M8 1 15 8 8 15 1 8z" fill="var(--bad-soft)" stroke="var(--bad)" stroke-width="1.5" stroke-linejoin="round"/>',
   overdue:'<circle cx="8" cy="8" r="7" fill="var(--bad)"/><path d="M5.3 5.3l5.4 5.4M10.7 5.3l-5.4 5.4" stroke="var(--surface)" stroke-width="1.8"/>'}[st]||"";
  return `<svg width="${sz}" height="${sz}" viewBox="0 0 16 16" aria-hidden="true">${p}</svg>`; }
export const mvTag=(st,cli)=>`<span class="mv-st ${st}">${mvShape(st)}${(cli?MVCWORD:MVWORD)[st]}</span>`;
/* BL-244: only the internal view is marked; the client view has no pill, note or outline (the cockpit's plain card) */
export const mvPill=cli=>cli?"":`<span class="mv-pill int">${ic("eyeoff",{bare:true})} Internal view</span>`;
export const mvCardCls=cli=>cli?"mv-card card client":"mv-card internal";
export function mvPct(m){ return m.pct==null?'<div class="mv-lbl">Progress</div><div class="mv-pct">Not set</div>':`<div class="mv-lbl">Progress</div><div class="mv-pct"><b>${m.pct}% complete</b><div class="b" role="img" aria-label="${m.pct} percent complete"><i style="width:${m.pct}%"></i></div></div>`; }
export function mvRevised(m){ if(!m.orig||!m.agr||m.orig===m.agr) return ""; const rb=m.rb||{}; return `<div class="mv-hint">Revised from ${fd(m.orig)}${rb.date?`, agreed ${fd(rb.date)}`:""}${rb.decision?` (decision ${esc(rb.decision)})`:""}</div>`; }

/* ---- the plan line: every milestone on one line, names and dates placed so none overlap; achieved ones in green at the date
   achieved; a later forecast as a red dashed ring with its own dated label joined by a dashed line. It scrolls sideways. ---- */
export const MVPXD=8;
export function mvAxis(list,pad){ const ds=[TODAY]; list.forEach(m=>{ [mvWhen(m),m.state!=="achieved"&&m.fc>m.agr?m.fc:"",m.orig&&pad?m.orig:""].forEach(d=>{ if(d&&DATE.test(d)) ds.push(d); }); }); ds.sort();
  const a=new Date(mvT(ds[0])-14*864e5), b=new Date(mvT(ds[ds.length-1])+40*864e5);
  const A0=Date.UTC(a.getUTCFullYear(),a.getUTCMonth(),1), A1=Date.UTC(b.getUTCFullYear(),b.getUTCMonth()+1,1); const months=[];
  for(let y=a.getUTCFullYear(),mo=a.getUTCMonth();Date.UTC(y,mo,1)<A1;mo++){ if(mo>11){ mo=0; y++; } months.push(Date.UTC(y,mo,1)); }
  return {A0,A1,months}; }
export const MVMN=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
export function mvStrip(list,cli){ const {A0,A1,months}=mvAxis(list,false), W=Math.round((A1-A0)/864e5*MVPXD), px=t=>(t-A0)/864e5*MVPXD, LH=42, base=62, levels=[], items=[]; let h='<div class="ax"></div>';
  months.forEach(t=>{ const d=new Date(t); h+=`<div class="mon" style="left:${px(t)}px">${MVMN[d.getUTCMonth()]}${d.getUTCMonth()===0||t===months[0]?" "+d.getUTCFullYear():""}</div>`; });
  list.forEach(m=>{ const w=mvWhen(m); if(!w) return; items.push({x:px(mvT(w)),m,g:false}); if(m.state!=="achieved"&&m.agr&&m.fc&&m.fc>m.agr) items.push({x:px(mvT(m.fc)),m,g:true}); });
  items.sort((a,b)=>a.x-b.x);
  items.forEach(it=>{ const m=it.m, st=m.state, ach=st==="achieved", x=it.x, text=it.g?150:Math.min(Math.max(m.n.length*6.4,76)+12,220), left=Math.min(Math.max(x-text/2,0),W-text); let lv=0;
    while(levels[lv]!==undefined&&left<levels[lv]+8) lv++; levels[lv]=left+text; const top=base+lv*LH, nm=m.n.length>26?m.n.slice(0,25)+"…":m.n;
    h+=`<div class="mv-lead" data-lv="${lv}" style="left:${x}px;top:56px;height:${top-56}px"></div>`;
    if(it.g){ const ax=px(mvT(m.agr));
      h+=`<div class="mv-gconn" style="left:${ax}px;width:${x-ax}px"></div><div class="mv-ghost" style="left:${x}px" role="img" aria-label="${MSW}: ${esc(m.n)} now expected ${fd(m.fc)}" data-tip="${MSW}: ${esc(m.n)} now expected ${fd(m.fc)}"></div>`;
      h+=`<button type="button" class="mv-lab gl" data-lv="${lv}" data-mvedit="${m.id}" style="left:${left}px;top:${top}px;width:${text}px" aria-label="${esc(m.n)} now expected ${fd(m.fc)}"><b>Expected ${fd(m.fc)}</b><span>${esc(m.n.length>20?m.n.slice(0,19)+"…":m.n)}</span></button>`; }
    else{ h+=`${(w=>`<button type="button" class="mv-mk ${st}" data-mvedit="${m.id}" style="left:${x}px" aria-label="${w}" data-tip="${w}">${mvShape(st,20)}</button>`)(`${MSW}: ${esc(m.n)}, ${(cli?MVCWORD:MVWORD)[st]}, ${ach?"achieved "+fd(m.actual||m.fc):"agreed "+fd(m.agr||m.fc)}`)}`;
      h+=`<button type="button" class="mv-lab${st==="overdue"?" late":""}${ach?" ok":""}" data-lv="${lv}" data-mvedit="${m.id}" tabindex="-1" style="left:${left}px;top:${top}px;width:${text}px" title="${esc(m.n)}"><b>${esc(nm)}</b><span>${fd(mvWhen(m))}</span></button>`; } });
  h+=`<div class="tday" style="left:${px(mvT(TODAY))}px;height:${base-6}px"><span>Today</span></div>`;
  const first=new Date(A0), last=new Date(A1-864e5);
  return {html:h,w:W,lv:Math.max(1,levels.length),h:base+Math.max(1,levels.length)*LH+4,range:`${MVMN[first.getUTCMonth()]} ${first.getUTCFullYear()} to ${MVMN[last.getUTCMonth()]} ${last.getUTCFullYear()}`,today:px(mvT(TODAY))}; }
export function mvPlan(code,cli,host){ const list=mvVis(code,cli,false).sort((a,b)=>(mvWhen(a)||"9").localeCompare(mvWhen(b)||"9")), s=mvStrip(list,cli);
  let h=`<div class="mv-stripbar">${ibtn("chevleft","Scroll the plan line left",'data-mvact="sl"',"mv-ib")}${ibtn("chevright","Scroll the plan line right",'data-mvact="sr"',"mv-ib")}<button type="button" class="mv-btn sm" data-mvact="st">Today</button><span class="mv-hint">${s.range}</span></div>
    <div class="mv-stripwrap" tabindex="0" data-mvscroll="${host}" data-today="${Math.round(s.today)}" aria-label="Milestone plan line, scrolls sideways"><div class="mv-strip" data-lvls="${s.lv}" style="width:${s.w}px;height:${s.h}px">${s.html}</div></div>
    <div class="mv-detog"><button type="button" data-mvact="det" aria-expanded="${MVDET}" aria-controls="mvRows-${host}"><svg viewBox="0 0 10 10" aria-hidden="true"><path d="M1 3l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>${MVDET?"Hide milestone details":"Show milestone details"}</button></div>
    <div class="mv-rows" id="mvRows-${host}"${MVDET?"":" hidden"}>`;
  list.forEach(m=>{ const st=m.state, moved=st!=="achieved"&&m.agr&&m.fc>m.agr, ach=st==="achieved";
    /* BL-90, kept from the old card: an open dependency with a date warning marks the milestone it blocks (internal only) */
    const blk=cli||ach?[]:R.filter(r=>r.p===code&&r.type==="Dependency"&&r.st==="Open"&&r.ms===m.id&&depWarn(r));
    h+=`<div class="mv-prow${blk.length?" atrisk":""}" role="button" tabindex="0" data-mvedit="${m.id}" aria-label="Edit ${esc(m.n)}"${m.desc?` title="${esc(m.desc)}"`:""}>
      <div><div class="nm">${esc(m.n)}${!m.cvis&&!cli?' <span class="mv-tag">Internal only</span>':""}${blk.length?` <span class="mv-tag warn waiting" title="${esc(blk.map(d=>depWarn(d).text).join("\n"))}">waiting on ${blk.map(d=>esc(d.id)).join(", ")}</span>`:""}</div>${cli&&m.cw?`<div class="mv-cw">${esc(m.cw)}</div>`:""}</div>
      <div><div class="mv-lbl">State</div>${mvTag(st,cli)}${!cli&&mvMismatch(m)?`<div class="mv-sugg">Dates suggest ${MVWORD[m.sug]}</div>`:""}</div>
      <div><div class="mv-lbl">${ach?"Achieved":"Agreed date"}</div><div class="dt"${ach?' style="color:var(--ok)"':""}>${ach?fd(m.actual||m.fc):(m.agr?fd(m.agr):"Not agreed yet")}</div>${ach&&m.agr?`<div class="mv-hint">Agreed ${fd(m.agr)}${m.actual===m.agr?" · on the agreed date":""}</div>`:""}${moved?`<div class="exp">Expected ${fd(m.fc)} (${mvDays(m.fc,m.agr)} days later)</div>`:""}${!cli?mvRevised(m):""}</div>
      <div>${mvPct(m)}</div></div>`; });
  return h+"</div>"; }
/* #301: the plan line is as tall as you drag its corner grip (the browser's own, like the Draft email preview's, #281): taller spreads the
   label rows apart, shorter scrolls; double-click the grip to go back. Remembered per browser, not per project. Mouse only. */
export const MVHKEY="creaite.mvStripH", MVHMIN=120;
export function mvFit(sw){ const st=sw.querySelector(".mv-strip"); if(!st) return; const n=+st.dataset.lvls||1, base=62, own=!!sw.style.height;
  const lh=own?Math.max(42,Math.min(72,Math.floor((sw.clientHeight-base-12)/n))):42, hh=base+n*lh+4;
  st.style.height=hh+"px";
  st.querySelectorAll("[data-lv]").forEach(e=>{ const top=base+(+e.dataset.lv)*lh; if(e.classList.contains("mv-lead")) e.style.height=(top-56)+"px"; else e.style.top=top+"px"; }); }
export function mvBindResize(sw){ if(sw.dataset.mvh) return; sw.dataset.mvh="1";
  const clamp=h=>Math.max(MVHMIN,Math.min(h,Math.round(innerHeight*0.85)));
  try{ const v=+localStorage.getItem(MVHKEY); if(v>=MVHMIN) sw.style.height=clamp(v)+"px"; }catch(e){}
  let last=sw.clientHeight;
  if(typeof ResizeObserver==="function") new ResizeObserver(()=>{ if(!sw.isConnected||sw.clientHeight<MVHMIN-8||sw.clientHeight===last) return; last=sw.clientHeight; if(sw.style.height){ mvFit(sw); try{ localStorage.setItem(MVHKEY,String(Math.round(sw.getBoundingClientRect().height))); }catch(e){} } }).observe(sw);
  sw.addEventListener("dblclick",e=>{ const r=sw.getBoundingClientRect(); if(e.clientX<r.right-22||e.clientY<r.bottom-22) return;   /* only on the grip in the bottom corner */
    sw.style.height=""; try{ localStorage.removeItem(MVHKEY); }catch(x){} mvFit(sw); });
  mvFit(sw); }
export function mvBindScroll(root){ (root||document).querySelectorAll("[data-mvscroll]").forEach(sw=>{ mvBindResize(sw); const k=sw.dataset.mvscroll; if(shared.MV.scroll[k]===undefined) shared.MV.scroll[k]=Math.max(0,(+sw.dataset.today||0)-sw.clientWidth/3);
  sw.scrollLeft=shared.MV.scroll[k]; sw.addEventListener("scroll",()=>{ shared.MV.scroll[k]=sw.scrollLeft; }); }); }

/* ---- the cockpit's card: the Plan only, never Movement ---- */
export function mvCardHtml(p){ if(!shared.MVREADY) return '<div class="mv-card card mv-compact" id="mvCard"></div>'; const cli=shared.MVAUD==="cli", code=p.code, any=mvAll(code).length;
  return `<div class="${mvCardCls(cli)} mv-compact" id="mvCard"><div class="mv-head"><h2>Milestones</h2>${mvPill(cli)}<span class="sp"></span>
    <button type="button" class="mv-ib" id="mvSwap" data-mvact="aud" aria-pressed="${cli}" aria-label="${cli?"Switch to internal view":"Switch to client view"}" data-tip="${cli?"Switch to internal view":"Switch to client view"}">${ic("swap",{bare:true})}</button>
    <button type="button" class="mv-ib" id="mvPencil" data-mvpage="${code}" aria-label="Open milestones: Plan and Movement" data-tip="Open milestones: Plan and Movement">${ic("pencil",{bare:true})}</button></div>
    ${any?mvPlan(code,cli,"card"):`<div class="mv-empty">No milestones yet. <button type="button" class="mv-btn sm" data-mvpage="${code}" data-mvadd="1">${ic("plus")}Add a milestone</button></div>`}</div>`; }

/* ---- the page: Milestones: Plan and Movement ---- */
export function mvAnswer(code,list,cli){ const done=mvVis(code,cli,false).length-list.length, late=list.filter(m=>m.state==="overdue"), end=list[list.length-1]; let a="";
  if(late.length) a+=`<b>${esc(late[0].n)}</b> is late: agreed ${fd(late[0].agr)}${late[0].fc>late[0].agr?`, now expected ${fd(late[0].fc)}`:""}. `;
  if(end&&end.agr&&(!late.length||end.id!==late[0].id)) a+=`<b>${esc(end.n)}</b> is agreed for ${fd(end.agr)}${end.fc>end.agr?` and now expected ${fd(end.fc)}`:""}. `;
  return a+`${done} achieved, ${list.length} to come.`; }
export function renderMilestones(){ const code=shared.MSCODE, p=P.find(x=>x.code===code), el=$("#v-milestones"); if(!el) return; if(!p){ if(!code) chooseProject(el,"milestones"); else el.textContent=""; return; }
  const cli=shared.MVAUD==="cli"; if(cli&&shared.MV.view==="move") shared.MV.view="plan";
  let h=`<div class="wrapmax"><nav class="crumb" aria-label="Breadcrumb"><a href="#" data-go="projects">Projects</a><span aria-hidden="true">›</span><a href="#" data-proj="${code}">${esc(p.name)}</a><span aria-hidden="true">›</span><span aria-current="page">Milestones</span></nav>
    <div class="mv-pageh"><h1>Milestones: Plan and Movement</h1><span class="sp"></span>
      <button type="button" class="mv-btn pri" id="mvAdd" data-mvadd="1">${ic("plus")}Add milestone</button></div>
    <div class="mv-ctl"><div class="mv-seg" role="group" aria-label="Milestone view"><button type="button" id="mvVPlan" data-mvview="plan" aria-pressed="${shared.MV.view==="plan"}">Plan</button><button type="button" id="mvVMove" data-mvview="move" aria-pressed="${shared.MV.view==="move"}"${cli?' aria-disabled="true" data-tip="Movement is internal only and is hidden in Client view"':""}>Movement <span class="mv-tag">Internal</span></button></div>
      <div class="mv-seg" role="group" aria-label="Audience"><button type="button" id="mvAInt" data-mvaud="int" aria-pressed="${!cli}">Internal view</button><button type="button" id="mvACli" data-mvaud="cli" aria-pressed="${cli}">Client view</button></div></div>`;
  if(shared.MV.view==="move") h+=`<div class="mv-card internal"><div class="mv-head"><h2>Movement</h2>${mvPill(false)}<span class="mv-tag warn">Internal only: never in client output</span></div>${mvMovement(code)}</div>`;
  else { const list=mvOpen(code,cli,false), any=mvAll(code).length;
    h+=`<div class="${mvCardCls(cli)}" id="mvPlanCard"><div class="mv-head"><h2>Plan</h2>${mvPill(cli)}</div>${cli?"":'<div class="mv-banner">Internal view includes internal-only milestones and a note where a state differs from what the dates suggest. Switch to Client view to see what a client sees.</div>'}
      ${any?`<p class="mv-answer">${mvAnswer(code,list,cli)}</p><p class="mv-cap">Every milestone sits on the line, achieved ones in green; a dashed ring shows where we now expect a later one. Scroll sideways for the whole line. Select a milestone to edit it.</p>${mvPlan(code,cli,"page")}`
        :`<div class="mv-empty">No milestones yet for ${esc(p.name)}. <button type="button" class="mv-btn sm" data-mvadd="1">${ic("plus")}Add milestone</button></div>`}</div>`; }
  putHTML(el,html`${raw(h)}</div>`); mvBindScroll(el); paintIcons(el); }

/* ---- Movement: the ladder of open milestones (original, agreed, forecast), the chart by reporting week, What changed, and
   Decide what to do ---- */
export function mvMovement(code){ const list=mvOpen(code,false,true), behind=list.filter(m=>(m.agr&&m.fc>m.agr)||(m.agr&&m.agr<TODAY)), over=list.filter(m=>m.state==="overdue").length, end=list[list.length-1];
  if(!list.length) return `<p class="mv-answer">No open milestones: nothing has moved.</p>`;
  if(!list.some(m=>m.id===shared.MV.sel)) shared.MV.sel=(behind[0]||list[0]).id;
  let h=`<p class="mv-answer"><b>${behind.length} of ${list.length}</b> open milestone${list.length===1?" is":"s are"} behind ${list.length===1?"its":"their"} agreed date; ${over} overdue.${end&&end.agr?` ${esc(end.n)} is <b>${Math.max(0,mvDays(end.fc,end.agr))} days</b> behind the agreed date and <b>${Math.max(0,mvDays(end.fc,end.orig||end.agr))} days</b> behind the original.`:""}</p>`;
  const dated=list.filter(m=>m.agr||m.fc), {A0,A1,months}=mvAxis(dated,true), pos=t=>((t-A0)/(A1-A0)*100).toFixed(2)+"%";
  h+=`<div class="mv-box"><h3>Original, agreed and forecast</h3><p class="mv-cap">Open milestones. Select one to review how it moved and decide what to do.</p>
    <div class="mv-lh"><div>Milestone</div><div class="mv-hdrtrack">${months.map(t=>`<span style="left:${pos(t)}">${MVMN[new Date(t).getUTCMonth()]}</span>`).join("")}</div><div>Variance</div></div><div role="listbox" aria-label="Open milestones">`;
  list.forEach(m=>{ const st=m.state, vs=m.agr?mvDays(m.fc,m.agr):0, vo=m.orig?mvDays(m.fc,m.orig):0, rb=m.orig&&m.agr&&m.orig!==m.agr;
    const conn=m.agr&&m.fc>m.agr?`<div class="conn" style="left:${pos(mvT(m.agr))};width:calc(${pos(mvT(m.fc))} - ${pos(mvT(m.agr))})"></div>`:"";
    const aria=`${m.n}, ${MVWORD[st]}${vs>0?`, ${vs} days behind agreed`:""}, agreed ${fd(m.agr)||"not set"}, forecast ${fd(m.fc)||"not set"}`;
    h+=`<div class="mv-lrow" role="option" tabindex="0" data-mvsel="${m.id}" aria-selected="${m.id===shared.MV.sel}" aria-label="${esc(aria)}">
      <div><div class="nm">${esc(m.n)}</div><div class="sub">${mvTag(st)}${m.cvis?"":" · internal"}</div><div class="sub">Agreed ${fd(m.agr)||"not set"}${m.fc!==m.agr?` · forecast ${fd(m.fc)}`:""}</div></div>
      <div class="mv-track" aria-hidden="true">${months.map(t=>`<div class="tm" style="left:${pos(t)}"></div>`).join("")}<div class="td" style="left:${pos(mvT(TODAY))}"></div>${conn}${rb?`<div class="orig" style="left:${pos(mvT(m.orig))}" role="img" aria-label="${MSW}: original date ${fd(m.orig)}" data-tip="${MSW}: original date ${fd(m.orig)}"></div>`:""}${m.agr?`<div class="agr" style="left:${pos(mvT(m.agr))}"></div>`:""}${m.fc?`<div class="fc" style="left:${pos(mvT(m.fc))}" role="img" aria-label="${MSW}: ${MVWORD[st]}, forecast ${fd(m.fc)}" data-tip="${MSW}: ${MVWORD[st]}, forecast ${fd(m.fc)}">${mvShape(st,20)}</div>`:""}</div>
      <div class="mv-chips"><span class="v ${vs>0?"bad":"ok"}">${vs>0?"+"+vs+" d":"0 d"} <small>vs agreed</small></span>${rb?`<span class="v ${vo>0?"bad":"ok"}">${vo>0?"+":""}${vo} d <small>vs original</small></span>`:""}${m.moves?`<span class="mv-hint">Moved ${m.moves}×${rb?" · rebaselined":""}</span>`:'<span class="mv-hint">Not moved</span>'}</div></div>`; });
  h+=`</div><div class="mv-legend"><span><svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><rect x="3" y="3" width="8" height="8" transform="rotate(45 7 7)" fill="none" stroke="var(--faint)" stroke-width="2"/></svg>Original (if rebaselined)</span><span><svg width="6" height="16" aria-hidden="true"><rect width="3" height="16" x="1.5" fill="var(--ink)"/></svg>Agreed</span><span>Forecast, shaped by state</span><span><svg width="18" height="4" aria-hidden="true"><rect width="18" height="3" fill="var(--bad)" opacity=".55"/></svg>Distance past agreed</span><span><svg width="2" height="14" aria-hidden="true"><rect width="1" height="14" fill="var(--accent)"/></svg>Today</span></div></div>`;
  return h+mvDetail(code); }
export function mvTrend(m){ const H=m.hist.filter(r=>r[1]||r[2]); if(H.length<2) return '<p class="mv-hint">No movement recorded yet for this milestone: the chart starts once it has two reporting weeks.</p>';
  const W=520,Hh=210,L=56,R=26,T=14,B=30, vals=[]; H.forEach(r=>vals.push(mvT(r[1]),mvT(r[2]))); if(m.orig) vals.push(mvT(m.orig));
  const lo=Math.min(...vals)-4*864e5, hi=Math.max(...vals)+4*864e5, n=H.length, X=i=>L+i*(W-L-R)/(n-1), Y=t=>T+(hi-t)/(hi-lo)*(Hh-T-B), d5=t=>{ const x=new Date(t); return `${String(x.getUTCDate()).padStart(2,"0")}-${String(x.getUTCMonth()+1).padStart(2,"0")}`; };
  let s=`<svg class="mv-tr" viewBox="0 0 ${W} ${Hh}" width="100%" role="img" aria-label="Forecast and agreed date by reporting week for ${esc(m.n)}">`;
  for(let g=0;g<4;g++){ const t=lo+(hi-lo)*g/3, y=Y(t); s+=`<line x1="${L}" x2="${W-R}" y1="${y}" y2="${y}" stroke="var(--line)"/><text x="${L-6}" y="${y+4}" text-anchor="end">${d5(Math.round(t/864e5)*864e5)}</text>`; }
  const every=Math.max(1,Math.ceil(n/9)); H.forEach((r,i)=>{ if(i%every===0||i===n-1) s+=`<text x="${X(i)}" y="${Hh-10}" text-anchor="middle">${fd(r[0]).slice(0,5)}</text>`; });
  if(m.orig) s+=`<line x1="${L}" x2="${W-R}" y1="${Y(mvT(m.orig))}" y2="${Y(mvT(m.orig))}" stroke="var(--faint)" stroke-dasharray="2 4"/><text x="${W-R}" y="${Y(mvT(m.orig))-4}" text-anchor="end">original ${fd(m.orig).slice(0,5)}</text>`;
  let ap=""; H.forEach((r,i)=>{ ap+=i?`H${X(i)}V${Y(mvT(r[2]))}`:`M${X(i)} ${Y(mvT(r[2]))}`; });
  s+=`<path d="${ap}" fill="none" stroke="var(--ink)" stroke-width="2" stroke-dasharray="5 3"/><polyline fill="none" stroke="var(--bad)" stroke-width="2.5" points="${H.map((r,i)=>X(i)+","+Y(mvT(r[1]))).join(" ")}"/>`;
  H.forEach((r,i)=>{ const ch=i&&r[1]!==H[i-1][1]; s+=`<circle cx="${X(i)}" cy="${Y(mvT(r[1]))}" r="${ch?5:3}" fill="${ch?"var(--bad)":"var(--surface)"}" stroke="var(--bad)" stroke-width="2"><title>Week ending ${fd(r[0])}: forecast ${fd(r[1])}, agreed ${fd(r[2])}</title></circle>`; });
  return s+`</svg><div class="mv-legend" style="margin:2px 0 0"><span><svg width="22" height="4" aria-hidden="true"><rect width="22" height="3" fill="var(--bad)"/></svg>Forecast</span><span><svg width="22" height="4" aria-hidden="true"><rect width="22" height="2" fill="var(--ink)"/></svg>Agreed (steps on a rebaseline)</span><span>Across: reporting week ending</span></div>`; }
export function mvDetail(code){ const m=mvGet(code,shared.MV.sel); if(!m||m.state==="achieved") return '<div class="mv-box" style="margin-top:12px"><span class="mv-hint">Select an open milestone above to see how it moved.</span></div>';
  const st=m.state, vs=m.agr?mvDays(m.fc,m.agr):0, rb=m.orig&&m.agr&&m.orig!==m.agr; let h="";
  h+=`<div class="mv-box" style="margin-top:12px" id="mvDetail"><div class="mv-head" style="margin:0"><h2>${esc(m.n)}</h2><span class="mv-hint">${m.id}</span>${mvTag(st)}<span class="sp"></span><button type="button" class="mv-btn sm" data-mvedit="${m.id}">Edit milestone</button></div>
    <div class="mv-dchips"><span>Original <b>${fd(m.orig)||"not set"}</b></span><span>Agreed <b>${fd(m.agr)||"not set"}</b>${rb?" (rebaselined)":""}</span><span>Forecast <b>${fd(m.fc)||"not set"}</b></span><span>Moved <b>${m.moves}×</b></span><span>Progress <b>${m.pct==null?"not set":m.pct+"%"}</b></span><span>Owner <b>${esc(m.owner)||"not set"}</b></span></div>${mvRangeLine(m)}
    <div class="mv-grid2" style="margin-top:6px"><div><h3 style="margin:10px 0 4px;font-size:14px">Movement by reporting week</h3>${mvTrend(m)}</div><div><h3 style="margin:10px 0 2px;font-size:14px">What changed</h3>${m.log.length?`<ul class="mv-log">${m.log.map(l=>`<li class="${l.k}"><div class="w">${fd(l.d)}</div><div class="c">${esc(l.c)}</div><div class="w">${esc(fdText(l.w))}</div></li>`).join("")}</ul>`:'<p class="mv-hint">Nothing has changed since it was first agreed.</p>'}</div></div></div>`;
  h+=`<div class="mv-grid2"><div class="mv-box" id="mvDecide"><h3>Decide what to do</h3><p class="mv-cap">${vs>0||st==="overdue"?"Each choice is waiting in Review; nothing changes until you approve it there.":"No variance to decide on."}</p><div class="mv-adj">
    <button type="button" class="mv-btn" data-mvadj="hold">Hold: keep forecast, agreed date unchanged</button><button type="button" class="mv-btn pri" data-mvadj="rebase">Rebaseline</button><button type="button" class="mv-btn" data-mvadj="recover">Add recovery action</button><button type="button" class="mv-btn" data-mvadj="escalate">Escalate to steering</button></div>`;
  if(shared.MV.rb&&shared.MV.rb.id===m.id) h+=`<div class="mv-form" id="mvRbForm"><div class="mv-fld">New agreed date${mvDpBtn("mvRbDate",shared.MV.rb.date,"New agreed date",shared.MV.rb.date!==m.agr)}</div>
      <div class="mv-fld full">Agreed with<div class="mv-chiprow">${shared.MV.rb.with.length?shared.MV.rb.with.map(n=>`<span class="mv-chip">${esc(n)}${mvOrg(n)}<button type="button" data-mvrmw="${esc(n)}" aria-label="Remove ${esc(n)}">${ic("x",{bare:true})}</button></span>`).join(""):'<span class="mv-hint">Nobody chosen yet</span>'}<button type="button" class="mv-cb small" id="mvRbAdd" data-mvppl="rbwith" aria-haspopup="listbox" aria-expanded="false" aria-label="Add person">+ Add person</button></div></div>
      <label class="mv-fld full">Reason<input type="text" class="mv-in" id="mvRbWhy" value="${esc(shared.MV.rb.why||"")}" placeholder="Why the agreed date has to move"></label><div class="mv-err full" id="mvRbErr" role="alert"></div>
      <div class="full" style="display:flex;gap:8px"><button type="button" class="mv-btn pri" data-mvrb="ok" data-key="${MOD}↵" data-tip="Save rebaseline and decision">Save rebaseline and decision</button><button type="button" class="mv-btn" data-mvrb="no">Cancel</button></div></div>`;
  if(shared.MV.adj&&shared.MV.adj.id===m.id) h+=`<div class="mv-form" id="mvAdjForm"><label class="mv-fld full">${shared.MV.adj.k==="hold"?"Why hold? One line, for the decision record":shared.MV.adj.k==="recover"?"The recovery action":"What to ask the steering committee"}<input type="text" class="mv-in" id="mvAdjWhy" value="${esc(shared.MV.adj.text||"")}"></label><div class="mv-err full" id="mvAdjErr" role="alert"></div>
      <div class="full" style="display:flex;gap:8px"><button type="button" class="mv-btn pri" data-mvadjok="1" data-key="${MOD}↵">${shared.MV.adj.k==="hold"?"Save the hold":shared.MV.adj.k==="recover"?"Save the action":"Save the ask"}</button><button type="button" class="mv-btn" data-mvadjno="1">Cancel</button></div></div>`;
  h+=`</div><div class="mv-box"><h3>Internal note</h3><p class="mv-cap">Your own words. Never shown to the client.</p><textarea class="mv-in" id="mvNote" data-mvnote="${m.id}" rows="3" aria-label="Internal note" placeholder="What is going on, what you are waiting for">${esc(m.note)}</textarea><div class="mv-hint" style="margin-top:6px">Saves when you leave the box.</div></div></div>`;
  return h; }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootMilestones0186(){
Object.assign(ICONS,{eyeoff:'<path d="M17.9 17.9A10 10 0 0 1 12 19C5.5 19 2 12 2 12a17 17 0 0 1 4.1-5M9.9 5.2A9 9 0 0 1 12 5c6.5 0 10 7 10 7a17 17 0 0 1-2.2 3.2M3 3l18 18"/>',
  swap:'<path d="M7 7h12l-3-3M17 17H5l3 3"/>'});
}
/* ===== BL-184 (sprint-milestones) ===== the slip range (forecast.py): a likely date range from how your own milestones have
   slipped, shown only with enough history ("No range yet: n of 8…") and marked thin evidence while there is little. Internal only:
   it sits in Movement, never in the Plan or the Client view. */
export function mvRangeLine(m){ const r=m.range; if(!r) return "";
  const h=`<div class="mv-range${r.ok?" ok":""}" id="mvRange"><span class="mv-lbl">Slip range</span> ${r.ok?`<b>Likely ${fd(r.lo)} to ${fd(r.hi)}</b>${r.thin?' <span class="mv-tag warn">Thin evidence</span>':""}<span class="mv-hint"> from ${r.n} closed milestone${r.n===1?"":"s"} that slipped at least ${r.k} time${r.k===1?"":"s"}, as this one has</span>`:`<span class="mv-hint">No range yet: ${r.n} of ${r.need} closed milestones with history.</span>`}</div>`;
  return !h||!r.ok||!r.explain?h:h.replace(/<\/div>$/,`<div class="mv-hint mv-explain">${esc(r.explain)}</div></div>`); }
/* ===== end BL-184 ===== */
/* ---- the date button and its calendar (weekends muted, keys: arrows by day and week, Page Up and Down by month, Esc) ---- */
export const MVDPH={}; export let MVCAL=null;
export function mvDpBtn(id,val,label,chg){ return `<button type="button" class="mv-dp${chg?" chg":""}" id="${id}" data-mvdp="${val||""}" aria-haspopup="dialog" aria-expanded="false" aria-label="${esc(label)}, ${val?fd(val):"not set"}"><span>${val?fd(val):"Choose a date"}</span>${ic("calendar",{bare:true})}</button>`; }
export function mvCalEl(){ let c=$("#mvCal"); if(!c){ addHTML(document.body,"beforeend",html`<div class="mv-cal" id="mvCal" hidden role="dialog" aria-label="Choose a date"></div>`); c=$("#mvCal"); } return c; }
export function mvCalOpen(btn,cb){ mvPopClose(false); const v=btn.dataset.mvdp||TODAY, d=new Date(mvT(v)); MVCAL={btn,cb,sel:btn.dataset.mvdp?mvT(v):null,focus:mvT(v),y:d.getUTCFullYear(),m:d.getUTCMonth()}; mvCalDraw(true); mvPlace(mvCalEl(),btn); btn.setAttribute("aria-expanded","true"); }
export function mvCalClose(refocus){ const c=$("#mvCal"); if(!c||c.hidden) return; c.hidden=true; MVCAL&&MVCAL.btn.setAttribute("aria-expanded","false"); if(refocus&&MVCAL&&MVCAL.btn.isConnected) MVCAL.btn.focus(); }
export function mvCalDraw(focus){ const c=mvCalEl(), {y,m}=MVCAL, first=Date.UTC(y,m,1), off=(new Date(first).getUTCDay()+6)%7, n=new Date(Date.UTC(y,m+1,0)).getUTCDate(), today=mvT(TODAY);
  let h=`<div class="mv-calh"><button type="button" data-mvcm="-1" aria-label="Previous month">${ic("chevleft",{bare:true})}</button><b aria-live="polite">${PKMON[m]} ${y}</b><button type="button" data-mvcm="1" aria-label="Next month">${ic("chevright",{bare:true})}</button></div><div class="mv-calg" role="grid">`;
  ["Mo","Tu","We","Th","Fr","Sa","Su"].forEach(w=>{ h+=`<div class="wd" aria-hidden="true">${w}</div>`; }); for(let i=0;i<off;i++) h+="<span></span>";
  for(let d=1;d<=n;d++){ const t=Date.UTC(y,m,d), wk=(off+d-1)%7>=5; h+=`<button type="button" data-mvt="${t}" tabindex="${t===MVCAL.focus?0:-1}" class="${wk?"wk ":""}${t===today?"td ":""}${t===MVCAL.sel?"sel":""}" aria-label="${d} ${PKMON[m]} ${y}${wk?", weekend":""}"${t===MVCAL.sel?' aria-pressed="true"':""}>${d}</button>`; }
  putHTML(c,html`${raw(h)}</div><div class="mv-calf"><span>Weekends are muted</span><button type="button" class="mv-btn sm" data-mvtoday="1">Today</button></div>`); c.hidden=false;
  if(focus){ const f=c.querySelector(`button[data-mvt="${MVCAL.focus}"]`)||c.querySelector("button[data-mvt]"); f&&f.focus(); } }
export function mvCalPick(t){ const cb=MVCAL.cb, btn=MVCAL.btn; mvCalClose(false); const d=new Date(+t), iso=`${d.getUTCFullYear()}-${String(d.getUTCMonth()+1).padStart(2,"0")}-${String(d.getUTCDate()).padStart(2,"0")}`; cb&&cb(iso); setTimeout(()=>{ const b=btn.id&&document.getElementById(btn.id); b&&b.focus(); },0); }
export function mvPlace(el,anchor){ const r=anchor.getBoundingClientRect(), w=el.offsetWidth, h=el.offsetHeight; let top=r.bottom+6, left=r.left;
  if(left+w>innerWidth-8) left=innerWidth-w-8; if(left<8) left=8; if(top+h>innerHeight-8) top=Math.max(8,r.top-h-6); el.style.top=top+"px"; el.style.left=left+"px"; }

/* ---- the people list: pick from the people list, or add a new person (a name and an organisation, through the register's
   own details dialog, as on actions) ---- */
export let MVPOP=null;
export function mvOrg(n){ const r=(typeof shared.REG!=="undefined"?shared.REG:[]).find(x=>x.name===n); return r&&r.org?` <small>${esc(r.org)}</small>`:""; }
export function mvPopEl(){ let c=$("#mvPop"); if(!c){ addHTML(document.body,"beforeend",html`<div class="mv-pop" id="mvPop" hidden></div>`); c=$("#mvPop"); } return c; }
export function mvPopClose(refocus=true){ const p=$("#mvPop"); if(!p||p.hidden) return; p.hidden=true; MVPOP&&MVPOP.btn.setAttribute("aria-expanded","false"); if(refocus&&MVPOP&&MVPOP.btn.isConnected) MVPOP.btn.focus(); }
export function mvPopItems(){ const q=MVPOP.q.trim().toLowerCase(), pool=peopleAll(), /** @type {any[]} */ L=pool.filter(n=>!q||n.toLowerCase().includes(q)||(mvOrg(n).toLowerCase().includes(q))).map(n=>({n}));
  if(q&&!pool.some(n=>n.toLowerCase()===q)) L.push({add:true,n:MVPOP.q.trim()}); return L; }
export function mvPopOpen(btn,cur,cb){ mvCalClose(false); MVPOP={btn,cur:cur||"",cb,q:"",idx:0}; mvPopDraw(); mvPlace(mvPopEl(),btn); btn.setAttribute("aria-expanded","true"); $("#mvPopQ")?.focus(); }
export function mvPopDraw(){ const p=mvPopEl(), L=mvPopItems();
  putHTML(p,html`<input type="text" class="mv-in" id="mvPopQ" placeholder="Search people, or type a new name" value="${MVPOP.q}" aria-label="Search people" autocomplete="off" role="combobox" aria-expanded="true" aria-controls="mvPopL" aria-autocomplete="list"${L.length?html` aria-activedescendant="mvPopO${raw(MVPOP.idx)}"`:""}><ul role="listbox" id="mvPopL" aria-label="People">${L.map((x,i)=>x.add?html`<li role="option" class="add" id="mvPopO${raw(i)}" data-mvpi="${raw(i)}" aria-selected="${String(i===MVPOP.idx)}">+ Add “${x.n}” as a new person</li>`:html`<li role="option" id="mvPopO${raw(i)}" data-mvpi="${raw(i)}" aria-selected="${String(i===MVPOP.idx)}"><span>${x.n}${x.n===MVPOP.cur?" ✓":""}</span>${raw(mvOrg(x.n))}</li>`)}</ul>`);
  p.hidden=false; }
export async function mvPopChoose(x){ if(!x) return; const cb=MVPOP.cb; mvPopClose(true);
  if(x.add){ const n=await ownerFinal(x.n); if(!n||n==="TBC") return; cb&&cb(n,true); return; } cb&&cb(x.n,false); }

/* ---- saving: each change is a dashboard proposal through save() (applied at once with auto-apply; Undo in the message) ---- */
export const MVSAVED=new Set();
/* changes queue (MVQ), so each is written after the one before has been applied and the page has its new updated_at */
shared.MVQ=Promise.resolve();
export function mvSave(m,ch,label,extra){ const run=shared.MVQ.then(()=>mvSave1(mvGet(m.p,m.id)||m,ch,label,extra)); shared.MVQ=run.catch(()=>{}); return run; }
export let MVSEC="";
export async function mvSave1(m,ch,label,extra){ const auto=viaServer()&&S.autoApply, item={op:"update",table:"milestones",id:m.id,changes:ch,...(extra||{})};
  if(!auto){ const sec=()=>new Date().toISOString().slice(0,19); if(sec()===MVSEC) await new Promise(r=>setTimeout(r,1000-new Date().getMilliseconds()+5)); MVSEC=sec(); }   /* held proposals apply in the order made: their names are by the second */
  if(auto||!MVSAVED.has(m.id)) item.based_on=m.at; MVSAVED.add(m.id);   /* a second unapplied change carries no based_on, as the peek's */
  const arr=m.arr, before=JSON.parse(JSON.stringify(arr));
  await save(label,[item],null,()=>mvPatch(arr,ch),()=>{ arr.splice(0,arr.length,...before); });
  mvRedraw(); }
export function mvPatch(arr,ch){ const /** @type {any} */ x=arr[14]=arr[14]||{}; if("name" in ch) arr[0]=ch.name; if("description" in ch) arr[13]=ch.description||"";
  if("forecast_date" in ch){ arr[8]=ch.forecast_date; x.fc=ch.forecast_date; } if("baseline_date" in ch){ arr[4]=ch.baseline_date; x.agr=ch.baseline_date; }
  if("status" in ch) arr[6]=ch.status; if("percent_complete" in ch){ arr[10]=ch.percent_complete; arr[5]=ch.percent_complete??arr[11]; x.pc=ch.percent_complete; }
  if("owner" in ch) x.owner=ch.owner||""; if("internal_note" in ch) x.note=ch.internal_note||""; if("actual_date" in ch) x.actual=ch.actual_date||""; if("client_visible" in ch) x.client=!!ch.client_visible;
  if("client_message" in ch) x.cw=ch.client_message||""; x.cvis=x.client&&String(x.cw||"").replace(/[^A-Za-z0-9]/g,"").length>=5;
  if("state" in ch){ x.set=!!ch.state; x.why=ch.state_reason||""; }
  const tmp={status:arr[6],agr:x.agr,fc:x.fc}; x.sug=MVWORD[mvSuggest(tmp)]; x.st=arr[6]==="Done"?"Achieved":x.set&&ch.state?ch.state:("state" in ch?x.sug:x.set?x.st:x.sug);
  if(arr[6]==="Done"){ x.st="Achieved"; x.set=false; } msState(arr); }

/* ---- the editor ---- */
/* the editor's frame: the Peek block's (BL-316), made once at the end of the page */
export const mvPeekFrame=()=>peekFrame("mvPeek",{label:"Edit milestone",cls:"mv-peek"});
export let MVJUST=false, MVOPENER=null;
export function mvEdOpen(id,from,o={}){ MVJUST=true; setTimeout(()=>{ MVJUST=false; },0); shared.MV.peek=id; shared.MV.add=o.add?mvDraftNew():null;   /* BL-245: every field at once */ shared.MV.flow=null; shared.MV.pend=null; shared.MV.cwPend=false;
  MVOPENER=from||document.activeElement; const p=mvPeekFrame(); p.classList.remove("enter"); void p.offsetWidth; if(!reduced()) p.classList.add("enter"); mvEdDraw(); $("#mvName")?.focus();
  if(shared.VIEW==="milestones") navWrite(false); }
export function mvEdClose(noFocus){ const was=shared.MV.peek!==null||shared.MV.add; shared.MV.peek=null; shared.MV.add=null; shared.MV.flow=null; shared.MV.pend=null; shared.MV.cwPend=false; mvCalClose(false); mvPopClose(false);
  const p=$("#mvPeek"); if(p) p.hidden=true; if(was&&shared.VIEW==="milestones") navWrite(false); if(!noFocus&&MVOPENER&&MVOPENER.isConnected) MVOPENER.focus(); }
export function mvStateExplain(m){ const st=m.state, sug=m.sug, sw=w=>`<b>${MVWORD[w]}</b>`, why=m.why?` (“${esc(m.why.replace(/\.$/,""))}”)`:"";
  if(st==="achieved") return `Achieved on ${fd(m.actual)||"a date not recorded"}. Pick another state to reopen it.`;
  const sugWhy=sug==="overdue"?`the agreed date (${fd(m.agr)}) has passed`:sug==="slipped"?`the forecast (${fd(m.fc)}) is later than the agreed date (${fd(m.agr)})`:"the forecast is not later than the agreed date";
  if(mvMismatch(m)) return `<b>You have set ${MVWORD[st]}</b>${why}. The dates suggest ${sw(sug)}: ${sugWhy}. <button type="button" class="mv-btn sm" data-mvpk="usesug">Use ${MVWORD[sug]}</button>`;
  if(m.manual&&st!==sug) return `<b>You have set ${MVWORD[st]}</b>${why}. The dates alone would say ${MVWORD[sug]}. <button type="button" class="mv-btn sm" data-mvpk="usesug">Use ${MVWORD[sug]}</button>`;
  return `${m.manual?"Set by you. ":"Following the dates. "}The dates say ${MVWORD[sug]}: ${sugWhy}.`; }
export function mvEdDraw(){ const p=mvPeekFrame(), code=mvCode(), pn=pName(code);
  if(shared.MV.add){ mvAddDraw(p,pn); drFcDraw(); return; }   /* BL-245 */
  const m=mvGet(code,shared.MV.peek); if(!m){ mvEdClose(true); drFcDraw(); return; }
  const st=m.state, ach=st==="achieved", F=shared.MV.flow&&shared.MV.flow.id===m.id?shared.MV.flow:null, PD=shared.MV.pend&&shared.MV.pend.id===m.id?shared.MV.pend:null;
  const keep=document.activeElement&&p.contains(document.activeElement)?document.activeElement.id:null;
  let h=`<div class="mv-pkbar"><span class="id">${m.id} · ${esc(pn)}</span><span class="sp"></span><span class="mv-hint">Each change saves on its own, with Undo</span>${ibtn("x","Close",'data-mvpk="close"',"mv-ib")}</div><div class="mv-pkbody">`;
  h+=`<input class="mv-ttl" id="mvName" type="text" value="${esc(m.n)}" aria-label="Milestone name">`;
  h+=`<div class="mv-dchips"><span>${mvTag(st)}</span><span>${ach?`Achieved <b>${fd(m.actual)||"—"}</b>`:`Agreed <b>${fd(m.agr)||"not set"}</b>`}</span>${ach?"":`<span>Forecast <b>${fd(m.fc)||"not set"}</b></span>`}<span>Progress <b>${m.pct==null?"not set":m.pct+"%"}</b></span></div>`;
  h+=`<div class="mv-pksec"><h4>State</h4><div class="mv-stopts" role="radiogroup" aria-label="State">${["ontrack","atrisk","slipped","overdue","achieved"].map(s=>`<button type="button" class="mv-so" role="radio" aria-checked="${st===s}" data-mvstate="${s}">${mvShape(s)}${MVWORD[s]}</button>`).join("")}</div><div class="mv-explain${mvMismatch(m)?" warn":""}">${mvStateExplain(m)}</div>`;
  if(F){ if(F.to==="achieved") h+=`<div class="mv-inl"><div class="mv-fld">Achieved on${mvDpBtn("mvFlDate",F.date,"Achieved on",F.date!==TODAY)}</div><button type="button" class="mv-btn pri" data-mvpk="flok" data-key="${MOD}↵">Confirm achieved</button><button type="button" class="mv-btn" data-mvpk="flno">Cancel</button><div class="mv-err" id="mvFlErr" role="alert"></div></div>`;
    else { const need=MVRANK[F.to]<MVRANK[mvSugOf(m)]; h+=`<div class="mv-inl"><label class="mv-fld">Why ${MVWORD[F.to]}?${need?"":" (optional)"}<input type="text" class="mv-in" id="mvFlWhy" value="${esc(F.why||"")}" placeholder="One line, for the log"></label><button type="button" class="mv-btn pri" data-mvpk="flok" data-key="${MOD}↵">Set ${MVWORD[F.to]}</button><button type="button" class="mv-btn" data-mvpk="flno">Cancel</button><div class="mv-err" id="mvFlErr" role="alert"></div></div>`; } }
  h+="</div>";
  if(ach) h+=`<div class="mv-pksec"><h4>Dates</h4><div class="mv-row2"><div class="mv-fld">Achieved on${mvDpBtn("mvAch",m.actual,"Achieved on")}</div><div class="mv-fld">Agreed<b style="font-size:15px;color:var(--ink)">${fd(m.agr)||"not set"}</b></div></div></div>`;
  else h+=`<div class="mv-pksec"><h4>Dates</h4><div class="mv-row2"><div class="mv-fld">Agreed (the baseline)${m.agr?`<div style="display:flex;gap:8px;align-items:center"><b style="font-size:15px;color:var(--ink);white-space:nowrap">${fd(m.agr)}</b><button type="button" class="mv-btn sm" data-mvpk="rebase">Rebaseline…</button></div><span class="mv-hint">Original ${fd(m.orig)||fd(m.agr)}</span>`:mvDpBtn("mvAgr","","Set the agreed date")}</div>
      <div class="mv-fld">Forecast${mvDpBtn("mvFc",PD?PD.fc:m.fc,"Forecast",!!PD)}</div></div>
      ${PD?`<div class="mv-inl"><label class="mv-fld">Why is the forecast moving to ${fd(PD.fc)}?<input type="text" class="mv-in" id="mvFcWhy" value="${esc(PD.why||"")}" placeholder="One line, for the movement log"></label><button type="button" class="mv-btn pri" data-mvpk="fcok" data-key="${MOD}↵" data-tip="Save forecast">Save forecast</button><button type="button" class="mv-btn" data-mvpk="fcno">Cancel</button></div>`:""}<div class="mv-err" id="mvDtErr" role="alert"></div></div>`;
  h+=`<div class="mv-pksec"><h4>Progress</h4><div class="mv-rng"><input type="range" id="mvRng" min="0" max="100" step="5" value="${m.pct||0}" aria-label="Percent complete"><input type="number" class="mv-in" id="mvNum" min="0" max="100" value="${m.pct==null?"":m.pct}" aria-label="Percent complete number" placeholder="%"></div><span class="mv-hint">Set by hand. Not calculated from actions.</span></div>`;
  h+=`<div class="mv-pksec"><h4>Description</h4><label class="mv-fld">Scope and needs<textarea class="mv-in" id="mvDesc" rows="3" placeholder="What the milestone covers and what it needs">${esc(m.desc)}</textarea></label>
    <div class="mv-fld" style="margin-top:10px">Owner<button type="button" class="mv-cb" id="mvOwner" data-mvppl="owner" aria-haspopup="listbox" aria-expanded="false" aria-label="Owner, ${esc(m.owner||"not set")}"><span>${m.owner?esc(m.owner)+mvOrg(m.owner):'<span class="mv-hint">Choose the owner</span>'}</span>${ic("chevdown",{bare:true})}</button><span class="mv-hint">From the people list, or add a new person.</span></div></div>`;
  const cwOn=m.client||shared.MV.cwPend;
  h+=`<div class="mv-pksec"><h4>Client view</h4><div class="mv-swrow"><button type="button" class="mv-sw" id="mvCli" role="switch" aria-checked="${cwOn}" aria-label="Visible to client"></button><span>Visible to client</span></div>
    <label class="mv-fld">Client wording<textarea class="mv-in" id="mvCw" rows="2" ${cwOn?"":"disabled"} placeholder="Plain wording a client can read">${esc(m.cw)}</textarea></label>${shared.MV.cwPend?'<div class="mv-err" role="alert">Write the client wording: it is saved with the switch, as a client-visible milestone needs it.</div>':m.client&&!m.cvis?'<div class="mv-err">Client wording is needed before this appears in a client report.</div>':'<span class="mv-hint">Off by default. Only visible milestones appear in client output.</span>'}</div>`;
  /* BL-250 A: its history, internal only */
  h+=`<div class="mv-pksec"><h4>History</h4>${shared.MVAUD==="cli"?'<span class="mv-hint" id="mvHistHid">History is internal: switch to Internal view to see it.</span>':feedBlock("ms",mvFeedItems(m))}</div>`;
  h+=`<div class="mv-pksec"><button type="button" class="mv-btn danger" data-mvpk="cancel">Cancel this milestone</button> <span class="mv-hint">Keeps its history; hides it from every view.</span></div></div>`;
  putHTML(p,raw(h)); mountFeedTabs(p); p.hidden=false; sneakMvAttach(p); paintIcons(p); const d=$("#mvDesc"); if(d&&typeof autoGrow==="function") autoGrow(d);   /* BL-322: Sneak peek's sparkle, foot line and box */
  if(keep&&document.getElementById(keep)) document.getElementById(keep).focus(); 
  drFcDraw(); }
export function mvShake(){ const p=$("#mvPeek"); if(!p) return; p.classList.remove("shake"); void p.offsetWidth; if(!reduced()) p.classList.add("shake"); snack("Finish or cancel the pending change first."); }
export function mvRedraw(){ if(shared.VIEW==="milestones") renderMilestones(); if(shared.VIEW==="cockpit"&&shared.COCK) renderCockpit(shared.COCK); if(shared.MV.peek||shared.MV.add) mvEdDraw(); }
/* what the dates would say with the milestone open (for an achieved one, as if it were reopened) */
export const mvSugOf=m=>m.state==="achieved"?mvSuggest({status:"Planned",agr:m.agr,fc:m.fc}):m.sug;
export async function mvSetState(m,to){ shared.MV.flow=null;
  if(to===m.state&&!(to===m.sug&&m.manual)){ mvEdDraw(); return; }
  if(to==="achieved"){ shared.MV.flow={id:m.id,to,date:TODAY}; mvEdDraw(); return; }
  if(to===mvSugOf(m)){ return mvSave(m,m.state==="achieved"?{status:"Planned",state:null}:{state:null},`${m.id} ${m.state==="achieved"?"reopened; its state":"state"} follows the dates (${MVWORD[to]})`); }
  shared.MV.flow={id:m.id,to,why:""}; mvEdDraw(); $("#mvFlWhy")?.focus(); }
export async function mvAct(k){ if(shared.DRF&&shared.DRF.used&&k==="fcok"&&($("#mvFcWhy")?.value||"").trim()){ draftStat("reason",drSame($("#mvFcWhy").value,shared.DRF.used)?"used":"edited"); shared.DRF=null; }
    else if(shared.DRF&&k==="fcno"){ if(shared.DRF.d) draftStat("reason","rejected"); shared.DRF=null; }
  const code=mvCode(), m=shared.MV.peek?mvGet(code,shared.MV.peek):null;
  if(k==="close") return mvEdClose();
  if(!m) return;
  if(k==="flno"){ shared.MV.flow=null; return mvEdDraw(); }
  if(k==="flok"){ const F=shared.MV.flow; if(!F) return;
    if(F.to==="achieved"){ if(F.date>TODAY){ $("#mvFlErr").textContent="The achieved date can't be after today."; return; } const d=m.agr?mvDays(F.date,m.agr):0; shared.MV.flow=null;
      return mvSave(m,{status:"Done",state:"Achieved",actual_date:F.date,percent_complete:100},`${m.n} marked achieved on ${fd(F.date)}${m.agr?d===0?" (the agreed date)":d>0?` (${d} days after agreed)`:` (${-d} days early)`:""}`); }
    const why=($("#mvFlWhy")?.value||"").trim(), sug=mvSugOf(m), need=MVRANK[F.to]<MVRANK[sug];
    if(need&&!why){ $("#mvFlErr").textContent=`${MVWORD[F.to]} is better than the dates suggest (${MVWORD[sug]}): say why, in one line.`; $("#mvFlWhy").focus(); return; }
    shared.MV.flow=null; const ch={state:MVWORD[F.to],state_reason:why||null}; if(m.state==="achieved"){ ch.status="Planned"; }
    return mvSave(m,ch,`${m.id} state set to ${MVWORD[F.to]}`); }
  if(k==="usesug") return mvSave(m,{state:null},`${m.id} state follows the dates (${MVWORD[m.sug]})`);
  if(k==="fcno"){ shared.MV.pend=null; return mvEdDraw(); }
  if(k==="fcok"){ const r=($("#mvFcWhy")?.value||"").trim(); if(!r){ $("#mvDtErr").textContent="Say why the forecast is moving."; $("#mvFcWhy").focus(); return; }
    const v=shared.MV.pend.fc, dd=mvDays(v,m.fc); shared.MV.pend=null; return mvSave(m,{forecast_date:v},`${m.id} forecast moved to ${fd(v)} (${dd>0?"+":""}${dd} days)`,{note:r}); }
  if(k==="rebase"){ mvEdClose(true); let msg=""; if(shared.MVAUD==="cli"){ shared.MVAUD="int"; mvPrefSet(MVVIEWKEY,"int"); msg="Switched to Internal view: Movement is internal only."; }
    shared.MV.sel=m.id; shared.MV.rb={id:m.id,date:m.fc>m.agr?m.fc:m.agr,why:"",with:[]}; shared.MV.adj=null; mvOpenPage(code,"move"); if(msg) snack(msg);
    requestAnimationFrame(()=>{ const f=$("#mvRbForm"); if(f){ mScroll(f,{block:"center"}); $("#mvRbWhy")?.focus(); } }); return; }
  if(k==="cancel"){ const arr=m.arr, p=P.find(x=>x.code===code), idx=p.ms.indexOf(arr), links=msLinked(m.id);
    const items=[{op:"update",table:"milestones",id:m.id,changes:{status:"Cancelled"},based_on:m.at},...links.map(([t,x])=>({op:"update",table:t,id:x.id,changes:{milestone:null},based_on:x.updated_at}))];
    mvEdClose(true); await save(`${m.n} cancelled${links.length?`; ${links.length} item${links.length===1?"":"s"} unlinked`:""}`,items,null,()=>{ p.ms.splice(p.ms.indexOf(arr),1); links.forEach(([,x])=>x.ms=null); },()=>{ p.ms.splice(idx,0,arr); links.forEach(([,x])=>x.ms=m.id); }); mvRedraw(); } }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootMilestones0188(){
document.addEventListener("keydown",e=>{ const c=$("#mvCal"); if(!c||c.hidden||!c.contains(e.target)) return; const k=e.key, step={ArrowLeft:-1,ArrowRight:1,ArrowUp:-7,ArrowDown:7}[k];
  if(k==="Escape"){ e.preventDefault(); e.stopPropagation(); mvCalClose(true); return; }
  if(step!==undefined){ e.preventDefault(); MVCAL.focus+=step*864e5; const d=new Date(MVCAL.focus); MVCAL.y=d.getUTCFullYear(); MVCAL.m=d.getUTCMonth(); mvCalDraw(true); return; }
  if(k==="PageUp"||k==="PageDown"){ e.preventDefault(); const d=new Date(MVCAL.focus), t=Date.UTC(d.getUTCFullYear(),d.getUTCMonth()+(k==="PageUp"?-1:1),d.getUTCDate()), d2=new Date(t); MVCAL.focus=t; MVCAL.y=d2.getUTCFullYear(); MVCAL.m=d2.getUTCMonth(); mvCalDraw(true); }
  if(k==="Tab"){ mvCalClose(false); } },true);
document.addEventListener("input",e=>{ if(e.target.id!=="mvPopQ") return; MVPOP.q=e.target.value; MVPOP.idx=0; const pos=e.target.selectionStart; mvPopDraw(); const q=$("#mvPopQ"); q.focus(); q.setSelectionRange(pos,pos); });
document.addEventListener("keydown",e=>{ const p=$("#mvPop"); if(!p||p.hidden||!p.contains(e.target)) return; const n=mvPopItems().length;
  if(e.key==="ArrowDown"){ e.preventDefault(); MVPOP.idx=(MVPOP.idx+1)%n; mvPopDraw(); $("#mvPopQ").focus(); }
  else if(e.key==="ArrowUp"){ e.preventDefault(); MVPOP.idx=(MVPOP.idx-1+n)%n; mvPopDraw(); $("#mvPopQ").focus(); }
  else if(e.key==="Enter"){ e.preventDefault(); mvPopChoose(mvPopItems()[MVPOP.idx]); }
  else if(e.key==="Escape"){ e.preventDefault(); e.stopPropagation(); mvPopClose(true); } else if(e.key==="Tab"){ mvPopClose(false); } },true);
}
/* ===== BL-245 (sprint-milestone-ui) ===== Add milestone in one step. Add milestone (the page's button, the card's empty-state
   button, ⌘K) opens the editor with every field ready at once: the name, state, agreed and forecast dates, progress (slider and
   %), description, owner and client view. Nothing is saved until Create milestone (or Enter in the name): then one new proposal
   carries every field, through save() as before (so tracker.py's rules check it, and the message has Undo), and the editor
   becomes the saved milestone's, where each change saves on its own as before. The rules are the editor's: a state better than
   the dates suggest needs a one-line reason, Achieved needs a date that isn't after today, and Visible to client needs the
   client wording. A click outside with something entered shakes instead of closing (Esc or Cancel discards the draft). */
export const mvDraftNew=()=>({name:"",st:null,why:"",agr:"",fc:"",ach:TODAY,pct:null,desc:"",owner:"",client:false,cw:""});
export const mvAddDirty=()=>{ const A=shared.MV.add; if(!A) return false; mvAddSync(); return !!(A.name.trim()||A.st||A.agr||A.fc||A.pct!=null||A.desc.trim()||A.owner||A.client||A.cw.trim()); };
/* what the dates say for the draft, as tracker.suggested_state would read them once saved (as an open milestone) */
export const mvAddSug=A=>mvSuggest({status:"Planned",agr:A.agr,fc:A.fc||A.agr});
/* the typed fields are read from the page, so a value set without an input event (a paste, a script) is never missed */
export function mvAddSync(){ const A=shared.MV.add, v=id=>{ const e=document.getElementById(id); return e?e.value:null; }; if(!A) return;
  const n=v("mvName"), d=v("mvDesc"), c=v("mvCw"), w=v("mvAWhy"), p=v("mvNum"); if(n!==null) A.name=n; if(d!==null) A.desc=d; if(c!==null) A.cw=c; if(w!==null) A.why=w;
  if(p!==null) A.pct=p===""?null:+p; }
export function mvAddDraw(p,pn){ const A=shared.MV.add, sug=mvAddSug(A), st=A.st||sug, keep=document.activeElement&&p.contains(document.activeElement)?document.activeElement.id:null;
  const need=!!A.st&&A.st!=="achieved"&&MVRANK[A.st]<MVRANK[sug];
  let h=`<div class="mv-pkbar"><span class="id">New milestone · ${esc(pn)}</span><span class="sp"></span><span class="mv-hint">Saved when you press Create milestone</span>${ibtn("x","Close",'data-mvpk="close"',"mv-ib")}</div><div class="mv-pkbody">`;
  h+=`<input class="mv-ttl" id="mvName" type="text" value="${esc(A.name)}" placeholder="Name the milestone" aria-label="Milestone name"><div class="mv-err" id="mvAddErr" role="alert"></div>`;
  h+=`<div class="mv-pksec"><h4>State</h4><div class="mv-stopts" role="radiogroup" aria-label="State">${["ontrack","atrisk","slipped","overdue","achieved"].map(s=>`<button type="button" class="mv-so" role="radio" aria-checked="${st===s}" data-mvstate="${s}">${mvShape(s)}${MVWORD[s]}</button>`).join("")}</div>`;
  h+=`<div class="mv-explain${need?" warn":""}">${A.st==="achieved"?"Achieved: say when.":A.st?`<b>You have set ${MVWORD[A.st]}</b>. The dates suggest <b>${MVWORD[sug]}</b>.`:A.agr||A.fc?`Following the dates: they say <b>${MVWORD[sug]}</b>.`:"Following the dates: <b>On track</b> until the dates say otherwise."}</div>`;
  if(A.st==="achieved") h+=`<div class="mv-inl"><div class="mv-fld">Achieved on${mvDpBtn("mvAAch",A.ach,"Achieved on")}</div></div>`;
  else if(A.st) h+=`<div class="mv-inl"><label class="mv-fld">Why ${MVWORD[A.st]}?${need?"":" (optional)"}<input type="text" class="mv-in" id="mvAWhy" value="${esc(A.why)}" placeholder="One line, for the log"></label></div>`;
  h+=`</div><div class="mv-pksec"><h4>Dates</h4><div class="mv-row2"><div class="mv-fld">Agreed (the baseline)${mvDpBtn("mvAgr",A.agr,"Agreed date")}</div><div class="mv-fld">Forecast${mvDpBtn("mvFc",A.fc,"Forecast")}</div></div></div>`;
  h+=`<div class="mv-pksec"><h4>Progress</h4><div class="mv-rng"><input type="range" id="mvRng" min="0" max="100" step="5" value="${A.pct||0}" aria-label="Percent complete"><input type="number" class="mv-in" id="mvNum" min="0" max="100" value="${A.pct==null?"":A.pct}" aria-label="Percent complete number" placeholder="%"></div><span class="mv-hint">Set by hand. Not calculated from actions.</span></div>`;
  h+=`<div class="mv-pksec"><h4>Description</h4><label class="mv-fld">Scope and needs<textarea class="mv-in" id="mvDesc" rows="3" placeholder="What the milestone covers and what it needs">${esc(A.desc)}</textarea></label>
    <div class="mv-fld" style="margin-top:10px">Owner<button type="button" class="mv-cb" id="mvOwner" data-mvppl="aowner" aria-haspopup="listbox" aria-expanded="false" aria-label="Owner, ${esc(A.owner||"not set")}"><span>${A.owner?esc(A.owner)+mvOrg(A.owner):'<span class="mv-hint">Choose the owner</span>'}</span>${ic("chevdown",{bare:true})}</button><span class="mv-hint">From the people list, or add a new person.</span></div></div>`;
  h+=`<div class="mv-pksec"><h4>Client view</h4><div class="mv-swrow"><button type="button" class="mv-sw" id="mvCli" role="switch" aria-checked="${A.client}" aria-label="Visible to client"></button><span>Visible to client</span></div>
    <label class="mv-fld">Client wording<textarea class="mv-in" id="mvCw" rows="2" ${A.client?"":"disabled"} placeholder="Plain wording a client can read">${esc(A.cw)}</textarea></label><span class="mv-hint">${A.client?"Needed: it is what a client reads.":"Off by default. Only visible milestones appear in client output."}</span></div>`;
  h+=`<div class="mv-pksec mv-afoot"><button type="button" class="mv-btn pri" id="mvACreate" data-mvpk="acreate" data-key="${MOD}↵" data-tip="Create milestone">${ic("plus")}Create milestone</button><button type="button" class="mv-btn" data-mvpk="close">Cancel</button><div class="mv-err" id="mvACreateErr" role="alert"></div></div></div>`;
  putHTML(p,raw(h)); p.hidden=false; paintIcons(p); const d=$("#mvDesc"); if(d&&typeof autoGrow==="function") autoGrow(d);
  if(keep&&document.getElementById(keep)) document.getElementById(keep).focus(); }
export function mvAddState(s){ const A=shared.MV.add; mvAddSync(); A.st=s===mvAddSug(A)&&s!=="achieved"?null:s; if(!A.st||A.st==="achieved") A.why=""; mvEdDraw();
  if(A.st&&A.st!=="achieved") $("#mvAWhy")?.focus(); else $(`#mvPeek [data-mvstate="${s}"]`)?.focus(); }
export function mvAddDate(id,v){ const A=shared.MV.add; mvAddSync();
  if(id==="mvAAch"){ if(v>TODAY){ snack("The achieved date can't be after today."); return; } A.ach=v; }
  else if(id==="mvAgr"){ A.agr=v; if(!A.fc) A.fc=v; }
  else if(id==="mvFc") A.fc=v;
  /* a state set by hand that now matches the dates simply follows them */
  if(A.st&&A.st!=="achieved"&&A.st===mvAddSug(A)){ A.st=null; A.why=""; }
  mvEdDraw(); }
export function mvAddErr(id,msg,focus){ const e=$("#"+id); if(e) e.textContent=msg; if(focus) $("#"+focus)?.focus(); return false; }
export async function mvAddCommit(){ const A=shared.MV.add; if(!A) return; mvAddSync(); const code=mvCode(), p=P.find(x=>x.code===code), name=A.name.trim(); if(!p) return;
  ["mvAddErr","mvACreateErr"].forEach(i=>{ const e=$("#"+i); if(e) e.textContent=""; });
  if(!name) return mvAddErr("mvAddErr","Name the milestone.","mvName");
  const sug=mvAddSug(A), why=A.why.trim(), ach=A.st==="achieved";
  if(A.st&&!ach&&MVRANK[A.st]<MVRANK[sug]&&!why) return mvAddErr("mvACreateErr",`${MVWORD[A.st]} is better than the dates suggest (${MVWORD[sug]}): say why, in one line.`,"mvAWhy");
  if(ach&&A.ach>TODAY) return mvAddErr("mvACreateErr","The achieved date can't be after today.");
  if(A.pct!=null&&(!Number.isInteger(A.pct)||A.pct<0||A.pct>100)) return mvAddErr("mvACreateErr","Progress is a whole number from 0 to 100.","mvNum");
  if(A.client&&A.cw.replace(/[^A-Za-z0-9]/g,"").length<5) return mvAddErr("mvACreateErr","Write the client wording: a milestone visible to the client needs it.","mvCw");
  const known=new Set(p.ms.map(m=>m[3])), id=msNextId(code), ord=Math.max(0,...p.ms.filter(m=>m[3]).map(m=>+m[7]||0))+1, source=`${S.me} (dashboard), ${TODAY}`;
  const ch={name,status:ach?"Done":"Planned"};
  if(A.agr) ch.baseline_date=A.agr; if(A.fc||A.agr) ch.forecast_date=A.fc||A.agr;
  if(A.pct!=null||ach) ch.percent_complete=A.pct!=null?A.pct:100;
  if(A.desc.trim()) ch.description=A.desc.trim(); if(A.owner) ch.owner=A.owner;
  if(ach){ ch.state="Achieved"; ch.actual_date=A.ach; } else if(A.st){ ch.state=MVWORD[A.st]; ch.state_reason=why||null; }
  if(A.client){ ch.client_visible=1; ch.client_message=A.cw.trim(); }
  const arr=[name,"","",id,null,null,"Planned",ord,null,null,null,null,"","",{st:"On track",sug:"On track",set:false,why:"",owner:"",actual:"",client:false,cw:"",cword:"On track",cvis:false,src:source,orig:A.agr||"",agr:"",fc:"",pc:null,moves:0,rb:null,hist:[],log:[]}];
  /* not saved (no vault, or the proposal couldn't be written): the draft stays, as it was */
  shared.MV.add=null; if(await save(`${id} created`,[{op:"new",table:"milestones",values:{project:code,...ch,sort_order:ord,source}}],null,()=>{ mvPatch(arr,ch); p.ms.push(arr); },()=>{ const i=p.ms.indexOf(arr); if(i>=0) p.ms.splice(i,1); })===false){ shared.MV.add=A; mvEdDraw(); return; }
  const made=(P.find(x=>x.code===code)||p).ms.find(m=>m[3]&&!known.has(m[3])&&m[0]===name)||p.ms.find(m=>m[3]===id);
  shared.MV.peek=made?made[3]:null; mvRedraw(); if(shared.MV.peek) $("#mvName")?.blur(); }
/* ===== end BL-245 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootMilestones0189(){
document.addEventListener("input",e=>{ if(!shared.MV.add) return; const t=e.target, A=shared.MV.add;
  if(t.id==="mvName") A.name=t.value; else if(t.id==="mvDesc") A.desc=t.value; else if(t.id==="mvCw") A.cw=t.value; else if(t.id==="mvAWhy") A.why=t.value;
  else if(t.id==="mvRng"||t.id==="mvNum") A.pct=t.value===""?null:+t.value; });
document.addEventListener("keydown",e=>{ if(shared.MV.add&&e.key==="Enter"&&e.target.id==="mvAWhy"){ e.preventDefault(); mvAddCommit(); } });
}

/* ---- opening the page and the editor ---- */
export function mvOpenPage(code,view,id,o={}){ if(!P.some(p=>p.code===code)) return false; if(view) shared.MV.view=view; if(shared.MVAUD==="cli"&&shared.MV.view==="move") shared.MV.view="plan";
  shared.MV.after=id||o.add?{id,add:!!o.add}:null;
  if(shared.VIEW==="milestones"&&shared.MSCODE===code){ renderMilestones(); navWrite(false); mvAfter(); return true; }
  const r=go("milestones",code); return r; }
export function mvAfter(){ const a=shared.MV.after; shared.MV.after=null; if(!a) return; setTimeout(()=>{ if(a.add) mvEdOpen(null,$("#mvAdd"),{add:true}); else if(a.id&&mvGet(shared.MSCODE,a.id)) mvEdOpen(a.id,null); },0); }
/* the view in the address: #milestones=<CODE>&v=plan|movement[&ms=<ID>] */
/* the code changes as the new entry is written (go's last navWrite), so the entry being left keeps its own */
/* a refresh (after an apply, the files' pulse, a sweep) redraws the page and the editor only when their milestones changed, so a
   click is never lost to a redraw under the pointer */
export const mvSig=()=>{ const p=P.find(x=>x.code===mvCode()); return JSON.stringify([shared.MSCODE,shared.MV.view,shared.MVAUD,shared.MV.sel,p?p.ms:null]); };
/* the cockpit's slip metric and the Projects table's Slip open Movement (Internal view, with a word if the card was in Client view) */
export function mvSlipOpen(code){ let msg=""; if(shared.MVAUD==="cli"){ shared.MVAUD="int"; mvPrefSet(MVVIEWKEY,"int"); msg="Switched to Internal view: Movement is internal only."; } mvOpenPage(code,"move"); if(msg) snack(msg); }
export function mvDatePicked(id,v){ const code=mvCode(), m=shared.MV.peek?mvGet(code,shared.MV.peek):null;
  if(shared.MV.add&&["mvAAch","mvAgr","mvFc"].includes(id)) return mvAddDate(id,v);   /* BL-245 */
  if(id==="mvRbDate"&&shared.MV.rb){ shared.MV.rb.why=$("#mvRbWhy")?.value||shared.MV.rb.why; shared.MV.rb.date=v; renderMilestones(); return; }
  if(!m) return;
  if(id==="mvFlDate"&&shared.MV.flow){ shared.MV.flow.date=v; mvEdDraw(); return; }
  if(id==="mvAch"){ if(v>TODAY){ snack("The achieved date can't be after today."); return; } if(v!==m.actual) mvSave(m,{actual_date:v},`${m.id} achieved date set to ${fd(v)}`); return; }
  if(id==="mvAgr"){ const ch={baseline_date:v}; if(!m.fc) ch.forecast_date=v; mvSave(m,ch,`${m.id} agreed for ${fd(v)}`); return; }
  if(id==="mvFc"){ shared.MV.pend=v===m.fc?null:{id:m.id,fc:v,why:""}; mvEdDraw(); $("#mvFcWhy")?.focus(); } }
/* Decide what to do: each choice is staged for Review (a pending proposal), nothing changes until it is approved there */
export async function mvStage(items,what){ if(!await needVault()) return; let name;
  try{ name=await writeProposal(items.map(i=>({...i,decision:"pending"}))); }catch(e){ snack("Not saved: "+e.message); return; }
  await reloadData(); renderBadge();
  snack(`${what} Waiting in Review: nothing changes until you approve it there.`,async()=>{ try{ await vq(async()=>{ const pth="system/staging/"+name; if(await shared.VW.exists(pth)) await shared.VW.remove(pth); }); await reloadData(); snack("Taken back"); }catch(e){ snack("Already decided: undo it in Activity"); } }); }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootMilestones0190(){
document.addEventListener("click",e=>{ const j=e.target.closest&&e.target.closest("[data-msjump],[data-cockjump$='|milestones']"); if(!j) return; e.preventDefault(); e.stopImmediatePropagation();
  mvSlipOpen(j.dataset.cockjump?j.dataset.cockjump.split("|")[0]:shared.COCK); },true);
/* one delegated listener for the card, the page, Movement and the editor */
document.addEventListener("click",e=>{ const t=e.target; if(!t.closest) return;
  const pg=t.closest("[data-mvpage]"); if(pg){ e.preventDefault(); mvOpenPage(pg.dataset.mvpage,"plan",null,{add:!!pg.dataset.mvadd}); return; }
  const ad=t.closest("[data-mvadd]"); if(ad&&shared.VIEW==="milestones"){ e.preventDefault(); mvEdOpen(null,ad,{add:true}); return; }
  const a=t.closest("[data-mvact]"); if(a){ const k=a.dataset.mvact, root=a.closest(".mv-card")||document, sw=root.querySelector("[data-mvscroll]");
    if(k==="aud"){ shared.MVAUD=shared.MVAUD==="cli"?"int":"cli"; mvPrefSet(MVVIEWKEY,shared.MVAUD); mvRedraw(); requestAnimationFrame(()=>$("#mvSwap")?.focus()); return; }
    if(k==="det"){ MVDET=!MVDET; mvPrefSet(MVDETKEY,MVDET?"1":"0"); mvRedraw(); return; }
    if(sw&&k==="sl") sw.scrollBy({left:-320,behavior:reduced()?"instant":"smooth"}); if(sw&&k==="sr") sw.scrollBy({left:320,behavior:reduced()?"instant":"smooth"});
    if(sw&&k==="st") sw.scrollTo({left:Math.max(0,(+sw.dataset.today||0)-sw.clientWidth/3),behavior:reduced()?"instant":"smooth"}); return; }
  const ed=t.closest("[data-mvedit]"); if(ed){ e.preventDefault(); if((shared.MV.peek&&(shared.MV.flow||shared.MV.pend)&&ed.dataset.mvedit!==shared.MV.peek)||(shared.MV.add&&mvAddDirty())){ mvShake(); return; } mvEdOpen(ed.dataset.mvedit,ed); return; }
  const vw=t.closest("[data-mvview]"); if(vw){ if(vw.dataset.mvview==="move"&&shared.MVAUD==="cli"){ snack("Movement is internal only and is hidden in Client view."); return; } shared.MV.view=vw.dataset.mvview; renderMilestones(); navWrite(true); return; }
  const au=t.closest("[data-mvaud]"); if(au){ shared.MVAUD=au.dataset.mvaud; mvPrefSet(MVVIEWKEY,shared.MVAUD); if(shared.MVAUD==="cli"&&shared.MV.view==="move"){ shared.MV.view="plan"; navWrite(false); } renderMilestones(); $(shared.MVAUD==="cli"?"#mvACli":"#mvAInt")?.focus(); return; }
  const se=t.closest("[data-mvsel]"); if(se){ shared.MV.sel=se.dataset.mvsel; shared.MV.rb=null; shared.MV.adj=null; renderMilestones(); $(`[data-mvsel="${shared.MV.sel}"]`)?.focus(); return; }
  const dp=t.closest("[data-mvdp]"); if(dp){ e.preventDefault(); mvCalOpen(dp,v=>mvDatePicked(dp.id,v)); return; }
  const c=$("#mvCal"); if(c&&!c.hidden&&c.contains(t)){ const cm=t.closest("[data-mvcm]"); if(cm){ MVCAL.m+=+cm.dataset.mvcm; if(MVCAL.m<0){ MVCAL.m=11; MVCAL.y--; } if(MVCAL.m>11){ MVCAL.m=0; MVCAL.y++; } MVCAL.focus=Date.UTC(MVCAL.y,MVCAL.m,1); mvCalDraw(false); return; }
    const dd=t.closest("button[data-mvt]"); if(dd){ mvCalPick(dd.dataset.mvt); return; } if(t.closest("[data-mvtoday]")){ mvCalPick(mvT(TODAY)); return; } return; }
  const pp=t.closest("[data-mvppl]"); if(pp){ e.preventDefault(); const code=mvCode(), m=shared.MV.peek?mvGet(code,shared.MV.peek):null;
    if(pp.dataset.mvppl==="aowner"&&shared.MV.add){ mvAddSync(); mvPopOpen(pp,shared.MV.add.owner,n=>{ if(shared.MV.add){ shared.MV.add.owner=n; mvEdDraw(); $("#mvOwner")?.focus(); } }); }   /* BL-245 */
    else if(pp.dataset.mvppl==="owner"&&m) mvPopOpen(pp,m.owner,(n,added)=>{ if(n!==m.owner||added) mvSave(m,{owner:n},added?`${n} added to the people list and set as owner`:`${m.id} owner set to ${n}`); });
    else if(pp.dataset.mvppl==="rbwith") mvPopOpen(pp,"",n=>{ shared.MV.rb.why=$("#mvRbWhy")?.value||shared.MV.rb.why; if(!shared.MV.rb.with.includes(n)) shared.MV.rb.with.push(n); renderMilestones(); $("#mvRbAdd")?.focus(); });
    return; }
  const pi=t.closest("[data-mvpi]"); if(pi&&$("#mvPop")?.contains(pi)){ mvPopChoose(mvPopItems()[+pi.dataset.mvpi]); return; }
  const st=t.closest("[data-mvstate]"); if(st&&shared.MV.add){ mvAddState(st.dataset.mvstate); return; }   /* BL-245 */
  if(st){ const m=mvGet(mvCode(),shared.MV.peek); if(m) mvSetState(m,st.dataset.mvstate); return; }
  const pk=t.closest("[data-mvpk]"); if(pk){ if(pk.dataset.mvpk==="acreate"){ mvAddCommit(); return; } mvAct(pk.dataset.mvpk); return; }
  if(t.closest("#mvCli")&&shared.MV.add){ mvAddSync(); shared.MV.add.client=!shared.MV.add.client; mvEdDraw(); if(shared.MV.add.client) $("#mvCw")?.focus(); return; }   /* BL-245 */
  if(t.closest("#mvCli")){ const m=mvGet(mvCode(),shared.MV.peek); if(!m) return;
    if(m.client) return mvSave(m,{client_visible:0},`${m.id} hidden from the client`);
    if(String(m.cw||"").replace(/[^A-Za-z0-9]/g,"").length>=5) return mvSave(m,{client_visible:1},`${m.id} visible to the client`);
    shared.MV.cwPend=!shared.MV.cwPend; mvEdDraw(); if(shared.MV.cwPend) $("#mvCw")?.focus(); return; }
  const rm=t.closest("[data-mvrmw]"); if(rm){ shared.MV.rb.why=$("#mvRbWhy")?.value||shared.MV.rb.why; shared.MV.rb.with=shared.MV.rb.with.filter(n=>n!==rm.dataset.mvrmw); renderMilestones(); return; }
  const rb=t.closest("[data-mvrb]"); if(rb){ if(rb.dataset.mvrb==="no"){ shared.MV.rb=null; renderMilestones(); return; } mvRebaseline(); return; }
  const aj=t.closest("[data-mvadj]"); if(aj){ const k=aj.dataset.mvadj, m=mvGet(shared.MSCODE,shared.MV.sel); if(!m) return; shared.MV.rb=null; shared.MV.adj=null;
    if(k==="rebase"){ shared.MV.rb={id:m.id,date:m.fc>m.agr?m.fc:m.agr,why:"",with:[]}; renderMilestones(); $("#mvRbWhy")?.focus(); return; }
    shared.MV.adj={id:m.id,k,text:k==="recover"?`Recover ${m.n}: `:k==="escalate"?`${m.n} is ${Math.max(0,mvDays(m.fc,m.agr))} days behind the agreed date: hold, recover or rebaseline?`:""}; renderMilestones(); const i=$("#mvAdjWhy"); if(i){ i.focus(); i.setSelectionRange(i.value.length,i.value.length); } return; }
  if(t.closest("[data-mvadjno]")){ shared.MV.adj=null; renderMilestones(); return; }
  if(t.closest("[data-mvadjok]")){ mvAdjust(); return; } });
document.addEventListener("keydown",e=>{ const t=e.target; if(!t.matches) return;
  if((e.key==="Enter"||e.key===" ")&&t.matches(".mv-prow[data-mvedit],.mv-lrow[data-mvsel]")){ e.preventDefault(); t.click(); return; }
  if(e.key==="Enter"&&t.id==="mvName"){ e.preventDefault(); if(shared.MV.add) mvAddCommit(); else t.blur(); return; }
  if(e.key==="Enter"&&["mvFlWhy","mvFcWhy","mvRbWhy","mvAdjWhy"].includes(t.id)){ e.preventDefault(); ({mvFlWhy:()=>mvAct("flok"),mvFcWhy:()=>mvAct("fcok"),mvRbWhy:mvRebaseline,mvAdjWhy:mvAdjust})[t.id](); return; }
  if(e.key==="Escape"&&(shared.MV.peek||shared.MV.add)&&!helpPanelOpen()&&!($("#mvCal")&&!$("#mvCal").hidden)&&!($("#mvPop")&&!$("#mvPop").hidden)&&!document.querySelector("#personDlg[open]")){
    if(shared.MV.flow||shared.MV.pend){ e.preventDefault(); shared.MV.flow=null; shared.MV.pend=null; mvEdDraw(); return; }
    if(t.matches("#mvPeek input[type=text],#mvPeek textarea")&&t.value!==t.defaultValue){ t.value=t.defaultValue; }
    e.preventDefault(); mvEdClose(); } });
document.addEventListener("change",e=>{ const t=e.target, code=mvCode(), m=shared.MV.peek?mvGet(code,shared.MV.peek):null;
  if(t.id==="mvNote"){ const n=mvGet(shared.MSCODE,t.dataset.mvnote); if(n&&t.value.trim()!==n.note) mvSave(n,{internal_note:t.value.trim()||null},`${n.id} internal note saved`); return; }
  if(!m) return;
  if(t.id==="mvName"){ const v=t.value.trim(); if(!v){ t.value=m.n; snack("A milestone needs a name."); return; } if(v!==m.n) mvSave(m,{name:v},`${m.id} renamed to ${v}`); }
  else if(t.id==="mvDesc"){ const v=t.value.trim(); if(v!==m.desc) mvSave(m,{description:v||null},`${m.id} description updated`); }
  else if(t.id==="mvRng"||t.id==="mvNum"){ if(t.value==="") return; const v=+t.value;
    if(!Number.isInteger(v)||v<0||v>100){ t.value=m.pct??""; snack("Progress is a whole number from 0 to 100."); return; } if(v!==m.pct) mvSave(m,{percent_complete:v},`${m.id} progress set to ${v}%`); }
  else if(t.id==="mvCw"){ const v=t.value.trim(), ok=v.replace(/[^A-Za-z0-9]/g,"").length>=5;
    if(shared.MV.cwPend){ if(!ok){ snack("The client wording needs a few words."); return; } shared.MV.cwPend=false; return mvSave(m,{client_visible:1,client_message:v},`${m.id} visible to the client`); }
    if(m.client&&!ok){ t.value=m.cw; snack("A client-visible milestone needs its client wording: hide it from the client first."); return; }
    if(v!==m.cw) mvSave(m,{client_message:v||null},`${m.id} client wording saved`); } });
document.addEventListener("input",e=>{ if(e.target.id==="mvFlWhy"&&shared.MV.flow) shared.MV.flow.why=e.target.value; if(e.target.id==="mvFcWhy"&&shared.MV.pend) shared.MV.pend.why=e.target.value;
  if(e.target.id==="mvAdjWhy"&&shared.MV.adj) shared.MV.adj.text=e.target.value; if(e.target.id==="mvRbWhy"&&shared.MV.rb) shared.MV.rb.why=e.target.value;
  if((e.target.id==="mvDesc"||e.target.id==="mvNote")&&typeof autoGrow==="function") autoGrow(e.target); if(e.target.id==="mvRng") $("#mvNum").value=e.target.value; });
}
/* ===== BL-274 (sprint-ui-sweep) ===== ⌘↵ in the milestone editor (#mvPeek) saves what is pending and closes it: a new milestone
   is created (Create milestone's checks); a state or forecast change waiting for its reason is saved, or its reason field is
   focused with the message; a typed field (name, description, progress, client wording) is committed; then it closes. With
   nothing pending it closes. In Movement, ⌘↵ in the rebaseline or decide form stages it, as its button does. */
export async function mvSaveAndClose(){ if(!shared.MV.peek&&!shared.MV.add) return;
  if(shared.MV.add){ await mvAddCommit(); if(shared.MV.add) return; mvEdClose(); return; }   /* a failed check leaves it open, its field focused */
  if(shared.MV.flow){ await mvAct("flok"); if(shared.MV.flow) return; }
  if(shared.MV.pend){ await mvAct("fcok"); if(shared.MV.pend) return; }
  const a=document.activeElement; if(a&&a.matches&&a.matches("#mvPeek input[type=text],#mvPeek input[type=number],#mvPeek textarea")) a.blur();   /* commits it */
  if(shared.MV.cwPend){ snack("Write the client wording: a milestone visible to the client needs it."); $("#mvCw")?.focus(); return; }
  mvEdClose(); }
/* ===== end BL-274 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootMilestones0191(){
onCmdEnter("milestone",t=>!!(shared.MV.peek||shared.MV.add)&&!!(t===document.body||(t.closest&&t.closest("#mvPeek,#mvCal,#mvPop"))),()=>mvSaveAndClose());
onCmdEnter("rebaseline",t=>!!shared.MV.rb&&!!(t.closest&&t.closest("#mvRbForm")),()=>mvRebaseline());
onCmdEnter("decide",t=>!!shared.MV.adj&&!!(t.closest&&t.closest("#mvAdjForm")),()=>mvAdjust());
}
export async function mvRebaseline(){ const code=shared.MSCODE, m=mvGet(code,shared.MV.sel), R=shared.MV.rb, err=$("#mvRbErr"); if(!m||!R) return; R.why=($("#mvRbWhy")?.value||"").trim();
  if(!R.date){ err.textContent="Choose the new agreed date."; return; } if(R.date===m.agr){ err.textContent="That is the agreed date already: choose the new one."; return; }
  if(!R.with.length){ err.textContent="Choose who agreed it."; $("#mvRbAdd")?.focus(); return; } if(!R.why){ err.textContent="Say why the agreed date moves."; $("#mvRbWhy").focus(); return; }
  const ch={baseline_date:R.date}; if(!m.fc||m.fc<R.date) ch.forecast_date=R.date;
  const item={op:"update",table:"milestones",id:m.id,changes:ch,based_on:m.at,rebaseline:{agreed_with:R.with.slice(),reason:R.why,source:`${S.me} (dashboard, Milestones › Movement), ${TODAY}`}};
  shared.MV.rb=null; await mvStage([item],`${m.n} rebaselined to ${fd(R.date)}, with a decision record.`); renderMilestones(); }
export async function mvAdjust(){ const code=shared.MSCODE, m=mvGet(code,shared.MV.sel), A2=shared.MV.adj, err=$("#mvAdjErr"); if(!m||!A2) return; const text=($("#mvAdjWhy")?.value||"").trim();
  if(!text||text===`Recover ${m.n}:`){ err.textContent=A2.k==="hold"?"Say why, in one line.":"Say what it is, in one line."; $("#mvAdjWhy").focus(); return; }
  const src=`${S.me} (dashboard, Milestones › Movement), ${TODAY}`; let items, what;
  if(A2.k==="hold"){ items=[{op:"new",table:"decisions",values:{project:code,decision:`Hold ${m.n}: keep the forecast ${fd(m.fc)}; the agreed date ${fd(m.agr)} is unchanged`,made_by:S.me,date:TODAY,status:"Made",reasoning:text,source:src}}]; what=`Hold on ${m.n}.`; }
  else if(A2.k==="recover"){ items=[{op:"new",table:"actions",values:{project:code,description:text,owner:"TBC",priority:"High",raised:TODAY,milestone:m.id,source:src}}]; what=`A recovery action for ${m.n}; its owner and date are yours to set in Review.`; }
  else { items=[{op:"new",table:"decisions",values:{project:code,decision:text,status:"Pending",source:src}}]; what=`An ask for the steering committee about ${m.n}.`; }
  shared.MV.adj=null; await mvStage(items,what); renderMilestones(); }
/* a click outside the editor closes it: not the click that opened it, not another milestone (it switches), not the first click while
   a calendar or the people list is open (it closes only that), and not while a change waits for its reason (it shakes) */
export let MVPOPWAS=false;
/* ===== end BL-186 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootMilestones0192(){
document.addEventListener("mousedown",e=>{ const c=$("#mvCal"), p=$("#mvPop"); MVPOPWAS=!!((c&&!c.hidden)||(p&&!p.hidden));
  if(c&&!c.hidden&&!c.contains(e.target)&&!e.target.closest("[data-mvdp]")) mvCalClose(false);
  if(p&&!p.hidden&&!p.contains(e.target)&&!e.target.closest("[data-mvppl]")) mvPopClose(false); },true);
document.addEventListener("click",e=>{ if(!(shared.MV.peek||shared.MV.add)||MVJUST) return; const P2=(e.composedPath&&e.composedPath())||[];
  if(P2.some(n=>n&&n.nodeType===1&&(n.id==="mvPeek"||n.id==="mvCal"||n.id==="mvPop"||n.id==="snack"||n.id==="chat"||n.id==="askBtn"||n.id==="personDlg"||n.id==="tip"||(n.dataset&&(n.dataset.mvedit||n.dataset.mvadd||n.dataset.mvpage))))) return;
  if(MVPOPWAS){ MVPOPWAS=false; return; }
  if(shared.MV.flow||shared.MV.pend){ mvShake(); return; }
  if(shared.MV.add&&mvAddDirty()){ mvShake(); return; }   /* BL-245: Esc or Cancel discards the draft */
  mvEdClose(true); });
/* ready: draw what the first render left, and open an address that names the page (#milestones=…) */
shared.MVREADY=true;
if(/^#milestones(=|&|$)/.test(shared.HASH0||"")){ const st=parseHash(shared.HASH0); if(st){ restoreNav(st); shared.NAVSTATE=navState(); try{ history.replaceState(shared.NAVSTATE,"",hashOf(shared.NAVSTATE)); }catch(e){} } }
else if(shared.VIEW==="cockpit"&&shared.COCK) renderCockpit(shared.COCK);
}
