// @ts-check
/* projects.js (BL-231 step 2b), moved from script/ by dev/tools/convert_area.py: 0029-projects-cockpit.js, 0054-generate-current-state-with-claude-bl-46.js, 0055-executive-current-state-bl-106.js, 0056-current-state-edited-in-place-bl-47.js, 0058-bl-162-sprint-rail.js, 0059-bl-207-sprint-insight.js, 0081-dashboard-pages-bl-87-to-bl-95.js, 0082-bl-190-sprint-links.js, 0083-after-bl-190-flow.js, 0124-insight-bl-51-bl-49-bl-54.js.
   Unchanged apart from `export`, `shared.` for the shared state (core/state.js) and the load-time steps, now in
   boot…() functions that src/main.js calls in today's order. */
import { howLink } from "./helpscreen.js";
import { openSpace } from "./components/reporting/ReportingSpace.jsx";
import { openDialog } from "./components/Dialog.jsx";
import { linkHtml } from "./core/linkText.js";
import { makePrepDialog } from "./components/dialogs/PageDialogs.jsx";
import { mountAiMenu } from "./components/AiSelect.jsx";
import { mountEditorBar, unmountEditorBar } from "./components/EditorBar.jsx";
import { attachSlash } from "./components/SlashMenu.jsx";
import { attachItemPick, insertHash } from "./components/ItemPicker.jsx";
import { chipClicked, itemChips, itemOf } from "./core/itemLink.js";
import { HEAD_SHIFT, runTool } from "./core/editorProfiles.js";
import { askClaude, openChat, questionLike, rbEnd, rbStart, runSearch, send, SRCH } from "./ask.js";
import { A, DEC, open, openOnly, overdue, P, pName, R, soon, SWEPT } from "./core/data.js";
import { $, $$, addHTML, esc, html, ibtn, ic, paintIcons, putHTML, raw, swapHTML, tipHide } from "./core/dom.js";
import { creaiteEditor, curDrop, ED_QUIET, edClaim, edOf, edValue } from "./core/editor.js";
import { closeCombobox } from "./components/Combobox.jsx";
import { closePicker, openPicker, pickerOpenFor } from "./components/Picker.jsx";
import { CALI, closeCal, DATE_HELP, formProject, onCmdEnter, WK, wkAsk } from "./core/fields.js";
import { countLink, go, navBlocked, navOf, navWrite, pkNewPending, pLink, seeAll, tabTitle } from "./core/nav.js";
import { cmdOK, cmOK, D, days, DDATE, fd, fdMd, health, ico, kindOf, MOD, mScroll, rel, S, store, TODAY, toIso, who } from "./core/page.js";
import { api, freeBackup, memPath, needVault, OLDSERVER, oneLine, reloadData, SERVED, SKEY, snack, stampFile, stampFull, viaServer, vq, writeSettings } from "./core/server.js";
import { shared } from "./core/state.js";
import { draftBtn, draftStat, draftWhyNot, DRRUN, GENFM, genFormDraft, genFormOptions, genReset, refineAsk, refineHtml, refineStatusHtml, versBarHtml } from "./drafts.js";
import { FOPEN } from "./files.js";
import { pdDrop } from "./help.js";
import { AGD, decAsked, decLate, decLateWords, decPending, decRank, decRevisit, dnBlock, dnDecisionHtml, dnList, dnOk, isSteering, prepReports, putHtml } from "./meetings.js";
import { mvBindScroll, mvCardHtml } from "./milestones.js";
import { bl185Row, htmlToMd, imgSrc, joinPanes, markSel, MD_IMG, mdHtml, openProject, openRecord, pkDrDrop, pkNewAsk, pkNewAskOff, pkNewKey, pkNewOffer, REC, saveCurrent, savePanel, splitPanes } from "./panel.js";
import { drawChips } from "./components/Chip.jsx";
import { mountPrepPopup } from "./components/prep/PrepPopup.jsx";
import { drawCockpitTabs } from "./notes.js";
import { mountPrepShape } from "./components/prep/PrepShape.jsx";
import { loadBrief, popupRev } from "./stores/prepPopup.js";
import { openProjectSettings } from "./stores/projectSettings.js";   /* #228 */
import { draftOn, pencil, SPARKI } from "./review.js";
import { nm, projArchive, renderSettings, row } from "./settings.js";
import { legBtn, pfResize, plur, portfolioTable, spark, tl } from "./today.js";
import { allBucket, boardMove, hit, isoAdd, PRIOS, rows } from "./work.js";
/* ======================= Projects + cockpit ======================= */
export function renderProjects(){ putHTML($("#projTbl"),raw(portfolioTable("pj"))); pfResize($("#projTbl")); if(!shared.LOADING&&!P.length) putHTML($("#projTbl"),html`<div class="empty">No projects yet. ${raw(howLink("projects"))} <button type="button" class="btn primary" data-setup="proj">Add a project</button> <span class="sub">or say “add project ABC …” to ask creaite</span></div>`); drawProjArchived(); }
/* #247: Show archived and Restore on the Projects page (they left Settings › People and projects): the same setting (showArchived:
   archived projects' items in Work, Today and the Excel export) and the same archive card (settings.js projArchive). */
export function projArchivedHtml(){ const L=(D.project_states||[]).filter(p=>p.state==="archived");
  return html`<div class="projarch"><label class="settick"><input type="checkbox" class="switch" id="projShowArch" ${S.showArchived?"checked":""}> Show archived projects</label>${S.showArchived?(L.length?html`<div class="tbl"><table class="mgr" id="projArchived" aria-label="Archived projects"><tbody>${L.map(p=>html`<tr><td>${p.name}</td><td class="sub">Archived</td><td class="mgract"><button type="button" class="mini" data-parch="restore" data-pcode="${p.code}" aria-label="Restore ${p.name}">Restore</button></td></tr>`)}</tbody></table></div>`:html`<p class="sub" id="projArchNone">No archived projects.</p>`):""}</div>`; }
export function drawProjArchived(){ const h=$("#projArchHost"); if(!h) return; putHTML(h,projArchivedHtml());
  const tick=$("#projShowArch"); if(tick) tick.onchange=async()=>{ const on=tick.checked; if(!await writeSettings({[SKEY.showArchived]:on})){ tick.checked=!on; return; } S.showArchived=on; await reloadData(); renderProjects(); };
  $$("#projArchived [data-parch]").forEach(b=>b.onclick=()=>projArchive(b.dataset.pcode,"restore",false)); }
export const DRAFTKIND={};                                   /* kind → feature; each kind's block adds its own */
/* BL-300: Top risks and issues: the text under each item is its latest update, falling back to the response (Alan,
   13-10-2026), cut at two lines (.rk-txt; #107, Alan 15-10-2026, was five); a cut one gets a quiet "More" and its full text as a tooltip, and the row
   opens the peek with all of it */
export const rkText=r=>String(r.upd||"").trim()||String(r.resp||"").trim()||"No response yet";
export function rkClamp(v){ if(!v) return;
  v.querySelectorAll(".rkrow .rk-txt").forEach(el=>{ if(!el.clientHeight) return;   /* hidden: measured when it shows */
    const row=el.closest(".rkrow"), cut=el.scrollHeight>el.clientHeight+1, more=row.querySelector(".rk-more");
    row.classList.toggle("clamped",cut);
    if(cut){ el.title=el.textContent; if(!more) addHTML(el,"afterend",html`<span class="rk-more" aria-hidden="true">More</span>`); }
    else { el.removeAttribute("title"); if(more) more.remove(); } }); }
/* #204: the project pages (Cockpit, Milestones) opened with no project chosen show this, not a blank page: a heading and the projects as links */
export function chooseProject(el,page){ if(!el) return; const name=page==="milestones"?"Milestones":"The project page";
  putHTML(el,P.length?html`<div class="wrapmax"><div class="choose"><h1 id="chooseH">Choose a project</h1><p class="sub">${name} shows one project. Pick the one to open.</p>
    <ul class="chooselist card" aria-labelledby="chooseH">${raw(P.map(p=>`<li><a href="#${page}=${esc(p.code)}" class="chooselink" data-choose="${page}" data-code="${esc(p.code)}"><span class="chname">${esc(p.name)}</span>${health(p.health)}</a></li>`).join(""))}</ul></div></div>`
    :html`<div class="wrapmax"><div class="choose"><h1 id="chooseH">Choose a project</h1><div class="empty card">No projects yet. Add one on the <a href="#projects" data-go="projects">Projects page</a>.</div></div></div>`); }
document.addEventListener("click",e=>{ const a=e.target.closest&&e.target.closest("[data-choose]"); if(a){ e.preventDefault(); go(a.dataset.choose==="milestones"?"milestones":"cockpit",a.dataset.code); return; } });
export function renderCockpit(code){ (()=>{ const p=P.find(x=>x.code===code); if(!p){ if(!code) chooseProject($("#v-cockpit"),"cockpit"); return; } queueMicrotask(mountCurEdit);   /* an open editor survives re-renders */
  const acts=A.filter(x=>x.p===code&&open(x)&&(overdue(x)||soon(x))).sort((a,b)=>(a.due||"9").localeCompare(b.due||"9"));
  const order=["Urgent","High","Medium","Low"];
  /* BL-15: top risks and issues, by priority */
  const risks=R.filter(r=>r.p===code&&r.st==="Open"&&(r.type==="Risk"||r.type==="Issue")).sort((a,b)=>order.indexOf(a.pr)-order.indexOf(b.pr)).slice(0,5);
  const dec=DEC.filter(d=>d.p===code&&d.st!=="Pending").sort((a,b)=>b.date.localeCompare(a.date)).slice(0,3);
  const dated=p.ms.filter(m=>m[1]);
  const all=dated.map(m=>m[1]).concat(TODAY).sort(); const t0=new Date(all[0]).getTime()-12*864e5, t1=new Date(all[all.length-1]).getTime()+12*864e5; const pos=d=>((new Date(d).getTime()-t0)/(t1-t0)*100).toFixed(1)+"%";
  const cv=R.filter(r=>r.p===code&&r.client&&!cmOK(r.cm)).length+A.filter(a=>a.p===code&&a.client&&!cmOK(a.cm)).length+DEC.filter(d=>d.p===code&&d.client&&!cmdOK(d.cmd)).length;
  /* BL-11: each milestone with forecast, baseline (when it moved) and progress from linked actions */
  const msList=p.ms.map(m=>`<div class="msrow${m[3]?" click":""}" ${m[3]?`data-ms="${m[3]}" tabindex="0" title="Edit milestone"`:""}>${ico("milestone")}<span class="msn">${esc(m[0])}${m[2]==="done"?' <span class="tag">Done</span>':""}</span><span class="${m[2]==="slip"?"late":""}">${m[1]?fd(m[1]):"No date"}</span>${m[4]&&m[1]&&m[4]!==m[1]?`<span class="sub">baseline ${fd(m[4])}</span>`:""}${m[5]!=null?`<span class="prog" title="${esc(m[12]||m[5]+"%")}"><i style="width:${m[5]}%"></i></span><span class="sub">${m[5]}%</span>`:""}</div>`).join("");
  /* BL-12: current state leads, with images */
  const paras=curReadHtml(p);
  const pi=P.findIndex(x=>x.code===code), nOpenA=A.filter(x=>x.p===code&&openOnly(x)).length, nOpenR=R.filter(r=>r.p===code&&r.st==="Open").length, nDec=DEC.filter(d=>d.p===code).length;
  putHTML($("#v-cockpit"),html`<div class="wrapmax"><nav class="crumb" aria-label="Breadcrumb"><a href="#" data-go="projects">Projects</a><span aria-hidden="true">›</span><span aria-current="page">${p.name}</span></nav>
   <div class="hhead"><div style="flex:1"><h1>${p.name}</h1><div class="sub">${(p.client||"Client not set")} · client reports ${((p.rhythm||"weekly").toLowerCase())}</div></div>
     <div class="pswitch"><button class="iconbtn" data-psw="-1" aria-label="Previous project" title="Previous project ( [ )" ${P.length<2?"disabled":""}>‹</button><select id="projSw" aria-label="Switch project">${P.map(x=>html`<option value="${x.code}" ${x.code===code?"selected":""}>${x.name}</option>`)}</select><button class="iconbtn" data-psw="1" aria-label="Next project" title="Next project ( ] )" ${P.length<2?"disabled":""}>›</button></div></div>
   <div id="cockTabs"></div>
   <div class="card curcard edt" style="margin-bottom:16px"><h2>Current state</h2><div class="genstatus" id="genStatus" hidden></div>${raw(pencil(`data-gen="${p.code}" aria-haspopup="dialog"${!viaServer()||shared.RUN||shared.GEN.run||DRRUN?' aria-disabled="true"':""}`,!viaServer()?"Generate needs the live server":shared.RUN||shared.GEN.run||DRRUN?"ask creaite is busy":"Generate current state",SPARKI,"second"))}${raw(pencil(`data-edcur="${p.code}"`,"Edit current state"))}<div id="curText" class="curtext">${raw(paras)}</div></div>
   <div class="cock"><div style="display:grid;gap:16px">
     <div class="card edt"><div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap"><span style="font-size:18px">${raw(health(p.health))}</span>${raw(spark(p))}${raw(legBtn())}<span class="sub">${p.reason}</span></div>${raw(pencil(`data-edproj="${p.code}"`,"Edit health and project details"))}
       <div class="evrow" style="margin-top:12px">${raw([["Overdue actions",A.filter(x=>x.p===code&&overdue(x)).length,1,"actions:overdue"],["No due date",undatedWork(code).length,0,""],["Urgent risks",R.filter(r=>r.p===code&&r.st==="Open"&&r.pr==="Urgent").length,1,"raid:urgentonly"],["Milestone slip",p.slip?p.slip+" days":"None",p.slip,""],["Due in "+S.dueSoon+" days",A.filter(x=>x.p===code&&soon(x)).length,0,"actions:soon",{st:["Open","Delayed"]}]].map(([l,v,b,nav,ex])=>`<div class="evbox${nav?" click":""}" ${nav?`data-nav="${esc(navOf(`${nav}:${code}`,ex))}" role="link" tabindex="0" title="Open in Work"`:""}><div class="v ${b&&v&&v!=="None"?"bad":""}">${v}</div><div class="l">${l}</div></div>`).join(""))}</div></div>
     ${raw(mvCardHtml(p))}
     <div class="card"><h2><a href="#" class="hlink" data-nav="actions:dueor:${raw(code)}">Actions due or overdue</a>${acts.length?html` <span class="sub">· ${acts.length}</span>`:""}</h2><div class="mini-list">${raw(acts.slice(0,S.listCap||10).map(x=>`<div data-open="actions:${x.id}" style="cursor:pointer"><span class="${overdue(x)?"late":""}" style="display:inline-block;width:110px">${rel(x.due)}</span>${ico("action")}${esc(x.t)} <span class="sub">— ${esc(who(x.o))}</span></div>`).join("")||'<div class="sub">Nothing due in the next '+S.dueSoon+' days.</div>')}</div>${acts.length>(S.listCap||10)?html`<a href="#" class="seeall" data-nav="actions:dueor:${raw(code)}">+${raw(acts.length-(S.listCap||10))} more — see all ›</a> `:""}${raw(seeAll(nOpenA,`${pName(code)} open action`,"actions:open:"+code))}</div>
     ${raw(undatedCard(code))}
   </div><div style="display:grid;gap:16px;align-content:start">
     <div class="card"><h2><a href="#" class="hlink" data-nav="raid:open:${raw(code)}">Top risks and issues</a></h2><div class="mini-list">${raw(risks.map(r=>`<div class="rkrow" data-open="raid:${r.id}" tabindex="0" style="cursor:pointer">${ico(r.type)}<span class="${r.pr==="Urgent"?"prio-urgent":"tag"}">${r.pr}</span> <span class="sub">${r.type}</span> ${esc(r.t)}<div class="sub rk-txt">${linkHtml(rkText(r))}</div></div>`).join("")||'<div class="sub">No open risks or issues.</div>')}</div>${raw(seeAll(nOpenR,`${pName(code)} open RAID item`,"raid:open:"+code))}</div>
     <div class="card"><h2><a href="#" class="hlink" data-nav="decisions:all:${raw(code)}">Recent decisions</a></h2><div class="mini-list">${raw(dec.map(d=>`<div data-open="decisions:${d.id}" style="cursor:pointer">${ico("decision")}${esc(d.t)}<div class="sub">${fd(d.date)} — ${esc(d.by)}</div></div>`).join("")||'<div class="sub">None yet.</div>')}</div>${raw(seeAll(nDec,`${pName(code)} decision`,"decisions:all:"+code))}</div>
     ${raw(depsCard(code))}
     ${cv?html`<div class="card"><h2>Client messaging</h2><div class="sub">${raw(cv)} client-visible item${cv===1?"":"s"} still need client messaging before the next client report.</div></div>`:""}
   </div></div>
   ${raw(flowCard(code))}
   <div class="cockfoot">${raw(ibtn("filetext","Reports",`data-reports="${p.code}"`,"bd"))}${raw(ibtn("folder","Browse files",`data-files="${p.code}"`,"bd"))}${raw(ibtn("gear","Project settings",`data-psettings="${p.code}"`,"bd"))}</div></div>`); })();
  drawCockpitTabs(code);   /* BL-301 B: Overview and Notes */
  csHead(code);   /* BL-274 */
  if(!(shared.CURED&&shared.CURED.code===code)) readClaims(code);   /* BL-162 */
  { const v=$("#v-cockpit"); if(v){
    const deps=R.filter(r=>r.p===code&&r.type==="Dependency"&&r.st==="Open"&&r.ms&&depWarn(r));
    v.querySelectorAll(".msrow[data-ms]").forEach(row=>{ const id=row.dataset.ms, b=deps.filter(d=>d.ms===id); if(!b.length) return; row.classList.add("atrisk");
      addHTML(row.querySelector(".msn"),"afterend",html`<span class="tag warn waiting" title="${b.map(d=>depWarn(d).text).join("\n")}">waiting on ${raw(b.map(d=>esc(d.id)).join(", "))}</span>`); }); } }   /* BL-87: dependencies */
  { const box=[...document.querySelectorAll("#v-cockpit .evrow .evbox")].find(b=>b.querySelector(".l")?.textContent==="No due date");
    if(box&&document.getElementById("undatedCard")){ box.classList.add("click"); box.setAttribute("data-undated",""); box.setAttribute("role","link"); box.tabIndex=0; box.title="Show them below"; } }   /* BL-190 */
  { const v=$("#v-cockpit"), ws=WARNS().filter(w=>w.p===code); decorateWarnings(v);
    const ev=v.querySelector(".evrow"); if(ev) addHTML(ev,"beforeend",html`<div class="evbox${ws.length?" click":""}" ${ws.length?html`data-wjump="1" role="link" tabindex="0" title="Show the early warnings"`:""}><div class="v ${ws.length?"bad":""}">${ws.length}</div><div class="l">Early warnings</div></div>`);
    const col=v.querySelector(".cock>div:last-child"); if(col&&ws.length) addHTML(col,"afterbegin",html`<div class="card" id="warnCard"><h2>Early warnings <span class="sub">· ${ws.length}</span></h2><div class="wlist">${ws.map(w=>html`<div ${raw(wOpen(w))} tabindex="0">${raw(wflag(w.k,w.id))}${w.k==="projects"?"":raw(esc(w.id)+" · ")}${wItem(w)}<span class="sub">${w.text}</span></div>`)}</div></div>`); }   /* BL-51 */
  tabTitle();
  { const v=$("#v-cockpit"), pend=decPending().filter(d=>d.p===code).sort(decRank), rev=decRevisit().filter(d=>d.p===code), col=v.querySelector(".cock>div:last-child");
    if(col&&(pend.length||rev.length)){
    const li=(d,m)=>`<div class="li" data-open="decisions:${d.id}" tabindex="0"><div class="t">${ico("decision")}${esc(d.t)}</div><div class="m">${m}</div></div>`;
    const dn=dnList(d=>d.p===code), rest=pend.filter(d=>!dn.includes(d));   /* BL-210: the dated ones that wait on someone are the shared rows */
    addHTML(col,"afterbegin",html`<div class="card" id="decCard"><h2>Decisions needed${pend.length?html` <span class="sub">· ${raw(countLink(`${plur(pend.length,"decision")} needed in ${pName(code)}`,pend.length,`decisions:pending:${code}`))}</span>`:""}</h2>${raw(dnBlock(dn,{inProject:true}))}${rest.length?html`<div class="mini-list">${raw(rest.map(d=>li(d,`${esc(d.id)} · ${decAsked(d)} · ${d.due?(decLate(d)?`needed by ${fd(d.due)}, <span class="late">${decLateWords(d)}</span>`:`needed by ${fd(d.due)}`):"no date needed by"}`)).join(""))}</div>`:pend.length?"":html`<p class="sub">None waiting.</p>`}${rev.length?html`<h3 class="sub" style="margin:12px 0 4px">To revisit</h3><div class="mini-list">${raw(rev.map(d=>li(d,`${esc(d.id)} · revisit date ${fd(d.revisit)} reached`)).join(""))}</div>`:""}</div>`); } }   /* BL-53 */
  { const h=document.querySelector(`#v-cockpit h2 a[data-nav="actions:dueor:${code}"]`), card=h&&h.closest(".card");
    if(card&&!card.querySelector("[data-allitems]")){ const n=[...A,...R,...DEC].filter(x=>x.p===code&&allBucket(x.st)==="Open").length;
    addHTML(card,"beforeend",html` <a href="#" class="seeall" data-allitems="1" data-nav="all:open:${raw(code)}" title="Actions, RAID items and decisions together">All items${n?html` (${raw(n)} open)`:""} ›</a>`); } }   /* BL-113 */
  rkClamp($("#v-cockpit"));   /* BL-300 */
  if(!shared.LOADING){ bl185Row();   /* BL-181 */
  $$("#v-cockpit [data-msjump]").forEach(b=>{ b.title="Open milestones: Movement"; b.setAttribute("aria-label",`Milestone slip ${b.querySelector(".v")?.textContent.trim()||""}, open milestones: Movement`); });
    mvBindScroll($("#v-cockpit")); paintIcons($("#mvCard"));   /* BL-245 */
    const h=[...$$("#v-cockpit .card>h2")].find(x=>x.textContent==="Client messaging"), card=h&&h.parentElement;
    if(card&&DRAFTKIND["client-bulk"]&&!card.querySelector("[data-drcmall]")&&draftOn("client")) addHTML(card,"beforeend",html`<div class="drstale">${raw(draftBtn("client-bulk","Draft all","Draft client wording for each of them, as proposals in Review (each approved on its own)",`data-drcmall="${esc(code)}"`))}<span class="drbst" role="status"></span></div>`); } }   /* BL-219 */
/** #122 B: the editor the key is in has its / menu open (SlashMenu sets aria-expanded on the text) @param {EventTarget|null} t */
const slashOn=t=>!!t&&/** @type {Element} */(t).getAttribute?.("aria-expanded")==="true";
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootProjects0029(){
document.addEventListener("keydown",e=>{ if(e.key==="Enter"&&e.target.matches&&e.target.matches(".rkrow[data-open]")) e.target.click(); });   /* BL-300 */
window.addEventListener("resize",()=>{ if(shared.VIEW==="cockpit") rkClamp($("#v-cockpit")); });
document.addEventListener("click",e=>{ const b=e.target.closest("[data-edcur]"); if(b){ startCurEdit(b.dataset.edcur); } const h=e.target.closest("[data-edproj]"); if(h) openProject(h.dataset.edproj,"health"); const f=e.target.closest("[data-files]"); if(f){ shared.FSEL={p:f.dataset.files,f:"All",sub:"",quick:"all"}; FOPEN.add(f.dataset.files); go("files"); } const rp=e.target.closest("[data-reports]"); if(rp){ openSpace(rp.dataset.reports); } const ps=e.target.closest("[data-psettings]"); if(ps){ e.preventDefault(); openProjectSettings(ps.dataset.psettings); } const a=e.target.closest("[data-ask]"); if(a){ openChat(); send(a.dataset.ask); } });
}
/* ======================= Generate current state with Claude (BL-46) ======================= */
export const GEN_SRC=[["tracker","Tracker changes and open items",1,"tracker"],["minutes","Minutes and transcripts",1,"minutes and transcripts"],["reports","Weekly and client reports",1,"reports"],["updates","Weekly updates",1,"weekly updates"],["swept","Mail and Teams items already swept",1,"swept mail and Teams"],["documents","Project documents (internal; off by default)",0,"project documents"]];   /* #110: the fourth is the short name for the Draw on line */
export const GEN_STARTERS=[["risks","Lead with risks"],["decisions","Lead with decisions needed"],["plain","Plain words, no jargon"]];   /* #110: a click appends the sentence to Steer it; keyed by id, never by the words */
export const GEN_FORMS=[["current","Current state"],["steering","Steering note"],["three","Three-line update"],["email","Email paragraph"],["teams","Teams message"]];   /* BL-227 */
export const GEN_AUDNOTE={internal:"Candid: the internal view of every item.",client:"Only items marked client-visible, in their client wording. Nothing else from the vault is used.",
  steering:"Internal wording for the steering committee, decisions and asks first; nothing confidential, restricted or marked Client-safe: no.",sponsor:"Internal wording for the sponsor, what is needed from them first; nothing confidential, restricted or marked Client-safe: no."};
export const GEN_AUD=[["internal","Internal"],["client","Client-safe"],["steering","Steering committee"],["sponsor","Sponsor"]], GEN_LEN=[["short","Short"],["standard","Standard"],["fuller","Fuller"]];   /* BL-106 */
/* #110: the four settings are quiet fields, each a button that opens the Picker block's list (↑ ↓ Home End, Enter, Esc, Tab); the buttons are
   drawn once in PageDialogs and only their words change, so a pick never loses the one you are on. Everything acts by data-gpick. */
const GEN_PICKS={days:()=>({label:"Period",value:shared.GEN.days,options:[...[7,14,30].map(n=>({v:n,label:`Last ${n} days`})),{v:"custom",label:"Dates…"}],
    set:v=>{ shared.GEN.days=v; $("#genCustom").hidden=v!=="custom"; if(v==="custom") $("#genFrom").focus(); }}),
  form:()=>{ const off=!draftOn("forms"), why=off?draftWhyNot("status-form"):""; return {label:"Form",value:shared.GEN.form,
    options:GEN_FORMS.map(([k,l])=>({v:k,label:l,...(why&&k!=="current"?{disabled:true,hint:why}:{})})),set:v=>{ shared.GEN.form=v; }}; },
  aud:()=>({label:"Audience",value:shared.GEN.aud,options:GEN_AUD.map(([k,l])=>({v:k,label:l})),set:v=>{ shared.GEN.aud=v; }}),
  len:()=>({label:"Length",value:shared.GEN.len,options:GEN_LEN.map(([k,l])=>({v:k,label:l})),set:v=>{ shared.GEN.len=v; }})};
export function genPick(btn){ if(btn.getAttribute("aria-disabled")==="true") return; if(pickerOpenFor(btn)){ closePicker("owner"); return; }
  const g=GEN_PICKS[btn.dataset.gpick]; if(!g) return; const c=g();
  openPicker(btn,{label:c.label,value:c.value,options:c.options,onPick:v=>{ c.set(v); genOptions(); }}); }
shared.GEN={code:null,days:S.genDays||7,aud:store.get("creaite-gen-aud","internal"),len:store.get("creaite-gen-len","standard"),form:store.get("creaite-gen-form","current"),run:null,ctl:null};
  
export function openGen(code){ (()=>{ if(shared.RUN||shared.GEN.run||DRRUN){ snack("ask creaite is busy; try again when it's finished"); return; } if(!viaServer()){ snack("Generate needs the live server"); return; } if(shared.RUN||shared.GEN.run||DRRUN){ snack("ask creaite is busy; try again when it's finished"); return; }
  if(shared.GEN.code!==code){ $("#genNote").value=""; $("#genFrom").value=""; $("#genTo").value=""; }   /* another project: no steer or dates from the last one */
  shared.GEN.code=code; $("#genWho").textContent=pName(code);
  genReset();   /* a dialog opened again starts as a new one: setup showing, no draft, Draw on folded */
  $("#genCustom").hidden=shared.GEN.days!=="custom";
  putHTML($("#genStart"),raw(GEN_STARTERS.map(([k,l])=>`<button type="button" class="genlink" data-gstart="${k}">${l}</button>`).join(" ")));
  putHTML($("#genSrc"),raw(GEN_SRC.map(([k,l,on])=>`<label><input type="checkbox" value="${k}" ${on?"checked":""}> ${l}</label>`).join("")));
  genSrcOpen(false); $("#genKbd").textContent=MOD+"↵";
  $("#genSweep").textContent=SWEPT&&SWEPT!=="never"?`Mail and Teams last swept ${fd(SWEPT)}; anything newer isn't in the vault yet.`:"Mail and Teams haven't been swept yet.";
  genOptions(); openDialog("genDlg"); })();
  const ttl=csTitle(code), h=ttl===CST_DEF?"Generate current state":`Generate: ${ttl}`; if(shared.GEN.form==="current") $("#genTitle").textContent=h; }   /* a remembered other form keeps its own "Write an …" title */   /* the dialog's title, which names it, names the status (BL-274) */
export function genStatus(html){ const el=$("#genStatus"); if(!el) return; el.hidden=!html; putHtml(el,html||""); }
export async function runGen(body,kind){ shared.RBOUT=""; rbStart(kind==="rewrite"?"Rewriting in the executive voice":"Drafting the current state"); try{
  const id=`g-${Date.now().toString(36)}-${Math.random().toString(36).slice(2,8)}`, ctl=new AbortController(); shared.GEN.run=id; shared.GEN.ctl=ctl;
  let said=[], steps=0, stopped=false, res;
  const show=()=>genStatus(`<span class="spin"></span> ${kind==="rewrite"?"Rewriting in the executive voice":"Drafting with Claude"}${steps?` · ${steps} step${steps===1?"":"s"}`:""} <button class="mini" data-genstop>Stop</button>`); show();
  try{ res=await fetch(kind==="rewrite"?"/api/current/rewrite":"/api/current/generate",{method:"POST",signal:ctl.signal,headers:{"Content-Type":"application/json","X-Creaite-Token":D.token},body:JSON.stringify({...body,run:id})}); }catch(e){ shared.GEN.run=null; genStatus(""); shared.RBOUT="failed"; snack("The live server isn't reachable"); return; }
  if(res.status===409||!res.ok||!res.body){ shared.GEN.run=null; genStatus(""); shared.RBOUT="failed"; const j=await res.json().catch(()=>({})); snack(res.status===404&&j.message==="Not found"?OLDSERVER:oneLine(j.message)||"Couldn't start the draft"); return; }
  if((res.headers.get("Content-Type")||"").includes("json")){ shared.GEN.run=null; genStatus(""); const j=await res.json(); snack(oneLine(j.message)||"Couldn't start the draft"); return; }
  const rd=res.body.getReader(), dec=new TextDecoder(); let buf="";
  for(;;){ let c; try{ c=await rd.read(); }catch(e){ stopped=true; break; } if(c.done) break; buf+=dec.decode(c.value,{stream:true}); let i;
    while((i=buf.indexOf("\n\n"))>=0){ const ch=buf.slice(0,i); buf=buf.slice(i+2); if(!ch.startsWith("data: ")) continue; let ev; try{ ev=JSON.parse(ch.slice(6)); }catch(e){ continue; }
      if(ev.type==="text") said.push(ev.text); else if(ev.type==="step"){ steps++; show(); } else if(ev.type==="stopped") stopped=true; else if(ev.type==="error"){ shared.RBOUT="failed"; snack(ev.message); } } }
  shared.GEN.run=null; genStatus(""); api("/api/ask/ack",{run:id}).catch(()=>{});   /* BL-326: seen here, so ask creaite doesn't draw it again */ if(stopped){ shared.RBOUT="stopped"; snack("Stopped; nothing changed"); return; }
  const text=said.join("\n\n"), [draft,src=""]=text.split(/^SOURCES:\s*$/m); if(!draft.trim()){ snack("No draft came back"); return; }
  if(kind==="rewrite"){ execResult(body.code,body.text,fdMd(draft.trim())); return; }
  genDraft(body.code,fdMd(draft.trim()),src.trim(),{audience:body.audience,length:body.length,from:body.from,to:body.to,note:body.note}); }
  finally{ rbEnd(shared.RBOUT||"done"); shared.RBOUT=""; } }
export function genDraft(code,md,sources,opts){ if(shared.VIEW!=="cockpit"||shared.COCK!==code) go("cockpit",code);
  if(!shared.CURED) startCurEdit(code); if(!shared.CURED) return; curLoad(1,md); shared.CURED.dirty=true; shared.CURED.sources=sources||"";
  shared.CURED.opts=opts||null; shared.CURED.notes=null; shared.CURED.facts=""; shared.CURED.rewrite=null; shared.CURED.claims=null; shared.CURED.ev={}; shared.CURED.vers=[{md}]; shared.CURED.at=0; shared.CURED.refineNote=""; mountCurEdit(); claimsInit("ed"); curCheck();   /* BL-207: the marks become claims */
  snack("Draft ready — edit it, then Save. Nothing is written until you do."); }
/* ===== #110 B: Steer it further under the unsaved Current state draft in the editor. The draft is the left pane; each refine writes
   a new version of it (drafts.js refineAsk: the same facts, the version shown and the change), with each sentence's fact marks put
   back so the sources and the no-source marks are worked out again for it. Versions live in the editor (CURED.vers) until it is
   closed; Save is still the only save. ===== */
export function curVersSync(){ const c=shared.CURED; if(!c) return; const n=(c.vers||[]).length, v=(c.vers||[])[c.at||0]||{};
  const el=$("#curVers"); if(el) putHtml(el,n>1?versBarHtml(c.at||0,n,"cver"):""); const m=$("#curRefineMsg"); if(m) putHtml(m,v.msg?`<div class="drnote" role="note">${esc(v.msg)}</div>`:""); }
/* a version's Markdown with each sentence's fact marks ({F3, F5}) put after it, from the draft's own sentences and sources */
export function refinedMd(res){ let md=String(res.text||""), pos=0; const ids=r=>((res.sources||[]).find(x=>x.ref===r)||{}).id;
  for(const s of res.sentences||[]){ const i=md.indexOf(s.text,pos); if(i<0) continue; pos=i+s.text.length;
    const f=[...new Set((s.refs||[]).map(ids).filter(x=>/^F\d+$/.test(String(x||""))))]; if(!f.length) continue;
    const mark=` {${f.join(", ")}}`; md=md.slice(0,pos)+mark+md.slice(pos); pos+=mark.length; }
  return md; }
/* the editor's words as they stand, with each sentence's fact marks put back: after a hand edit the editor's Markdown has none, and without them a restored
   version would be one claim with no source. A sentence with no source gets an empty mark ({}) so its edge is kept; one the text no longer matches goes unmarked. */
export function curSnap(c){ const root=$("#curEd"); if(!root) return null; const set=c.claims||{}; let md=stripMarks(edValue(root)), pos=0;
  for(const n of claimOrder(root)){ const cl=set[n]; if(!cl) continue; const t=claimText(root,n), i=md.indexOf(t,pos); if(i<0) continue; pos=i+t.length;
    const mark=(cl.ids||[]).length?` {${cl.ids.join(", ")}}`:" {}"; md=md.slice(0,pos)+mark+md.slice(pos); pos+=mark.length; }
  return {md}; }
function curShow(c,v){ curLoad(1,v.md); c.dirty=true; c.notes=null; c.claims=null; c.rewrite=null; mountCurEdit(); claimsInit("ed"); curCheck(); curVersSync(); }
function curStatus(c,h){ c.refineStatus=h; const el=$("#curRefineWork"); if(el) putHtml(el,refineStatusHtml(h)); }   /* kept in state: the editor can be drawn again while it is written */
export async function curRefine(){ const c=shared.CURED; if(!c||!c.opts||c.refining) return; const box=$("#curRefineNote"), ins=box?box.value.trim():"";
  if(!ins){ snack("Say what to change first, or pick one of the quick ones."); if(box) box.focus(); return; }
  const fromAt=c.at||0, snap=curSnap(c); if(!snap) return; c.vers=c.vers||[{}]; Object.assign(c.vers[fromAt],snap);   /* the words as they stand, edits and all */
  c.refining=true; c.refineStatus=""; $("#curRefineGo")?.setAttribute("aria-disabled","true");
  let res=null; try{ res=await refineAsk({body:{code:c.code,...c.opts},form:"current",text:stripMarks(snap.md).trim(),ins,fromV:fromAt+1,toV:c.vers.length+1,status:h=>curStatus(c,h)}); }
  finally{ c.refining=false; c.refineStatus=""; $("#curRefineGo")?.removeAttribute("aria-disabled"); }
  if(shared.CURED!==c) return;                                   /* closed while it was written */
  const late=curSnap(c); if(late) Object.assign(c.vers[fromAt],late);   /* whatever was typed while it was written stays in the version it was typed in */
  if(!res) return;                                               /* it failed: the editor is as it was */
  const v={md:fdMd(refinedMd(res)),msg:(res.length_notes||[]).join(" ")}; c.vers.push(v); c.at=c.vers.length-1; c.refineNote="";
  if(!c.edited){ c.edited=true; draftStat("forms","edited"); }   /* a refine is an edit of the same draft */
  curShow(c,v); }
export function curVersion(way){ const c=shared.CURED; if(!c||c.refining||!c.vers) return; const at=(c.at||0)+(way==="next"?1:-1); if(at<0||at>=c.vers.length) return;
  const snap=curSnap(c); if(snap) Object.assign(c.vers[c.at||0],snap); c.at=at; curShow(c,c.vers[at]); }
/* ===== end #110 B ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootProjects0054(){
if(!GEN_AUD.some(a=>a[0]===shared.GEN.aud)) shared.GEN.aud="internal";
if(!GEN_FORMS.some(a=>a[0]===shared.GEN.form)) shared.GEN.form="current";
if(!GEN_LEN.some(a=>a[0]===shared.GEN.len)) shared.GEN.len="standard";
$("#genDlg").addEventListener("click",e=>{ const b=e.target.closest("[data-gpick]"); if(b) genPick(b); });
$("#genDlg").addEventListener("keydown",e=>{ const b=e.target.closest&&e.target.closest("[data-gpick]"); if(b&&(e.key==="ArrowDown"||e.key==="ArrowUp")&&!pickerOpenFor(b)){ e.preventDefault(); genPick(b); } });
/* Steer it's starters append one sentence on a new line and never fill the box or send; the Draw on line opens its ticks */
$("#genDlg").addEventListener("click",e=>{ const st=e.target.closest("[data-gstart]"); if(st){ const x=GEN_STARTERS.find(a=>a[0]===st.dataset.gstart), t=$("#genNote"); if(!x) return;
    const v=t.value.replace(/\s+$/,""); t.value=(v?v+"\n":"")+x[1]+"."; t.dispatchEvent(new Event("input",{bubbles:true})); t.focus(); return; }
  if(e.target.closest("#genSrcBtn")) genSrcOpen($("#genSrcBtn").getAttribute("aria-expanded")!=="true");
  if(e.target.closest("#genChange")){ genReset(); $("#genDays").focus(); } });
$("#genSrc").addEventListener("change",()=>genSrcLine());
document.addEventListener("input",e=>{ if(e.target.id==="curRefineNote"&&shared.CURED) shared.CURED.refineNote=e.target.value; });   /* #110 B: what is typed survives the editor being drawn again */
/* ⌘↵ generates here (#101 has not built the shared dialog key yet; this is the one on this dialog) */
onCmdEnter("generate",t=>{ const d=$("#genDlg"); return !!d&&d.open&&(t===d||d.contains(t))&&!(t.closest&&t.closest("[data-refine]")); },()=>{ if(GENFM&&GENFM.vers&&GENFM.vers.length>1){ snack(`${MOD}↵ refines from here. Press Generate again to start over; it drops the versions.`); return; }   /* never regenerate over versions by a stray key */
  if(pickerOpenFor()){ closePicker("owner"); return; }   /* a menu open: ⌘↵ only closes it, so what is generated is what the strip shows */
  $("#genGo").click(); });
$("#genDlg").addEventListener("keydown",e=>{ if(e.key==="Enter"&&e.target.matches&&e.target.matches("#genFrom,#genTo")){ e.preventDefault(); $("#genGo").click(); } });   /* Enter in a date box generates, as the primary button; it never closes the dialog */
$("#genForm").addEventListener("submit",e=>{ if(e.submitter&&e.submitter.value!=="go") return; e.preventDefault(); if($("#genGo").getAttribute("aria-disabled")==="true") return;   /* a draft is being written */
  let from, to=TODAY; if(shared.GEN.days==="custom"){ const f=$("#genFrom").value.trim(), t=$("#genTo").value.trim(); if(!DDATE.test(f)||(t&&!DDATE.test(t))){ snack("Not a date creaite knows. "+DATE_HELP); return; } from=toIso(f); if(t) to=toIso(t); }
  else from=new Date(Date.now()-shared.GEN.days*864e5).toISOString().slice(0,10);
  const sources=[...$$("#genSrc input:checked")].map(i=>i.value); store.set("creaite-gen-aud",shared.GEN.aud); store.set("creaite-gen-len",shared.GEN.len); store.set("creaite-gen-form",shared.GEN.form);
  if(shared.GEN.form!=="current"){ genFormDraft({code:shared.GEN.code,from,to,note:$("#genNote").value.trim(),audience:shared.GEN.aud,length:shared.GEN.len}); return; }   /* BL-227: shown here, never saved */
  $("#genDlg").close();
  runGen({code:shared.GEN.code,from,to,sources,note:$("#genNote").value.trim(),audience:shared.GEN.aud,length:shared.GEN.len}); });
document.addEventListener("click",e=>{ const g=e.target.closest("[data-gen]"); if(g){ openGen(g.dataset.gen); return; }
  if(e.target.closest("[data-genstop]")&&shared.GEN.run){ api("/api/ask/stop",{run:shared.GEN.run}).then(r=>{ if(!r.ok&&shared.GEN.ctl) shared.GEN.ctl.abort(); }); } });
}
/* ===== Executive Current state (BL-106) ===== */
export function genOptions(){ genFormOptions(); genStrip(); genSrcLine(); }   /* the Form first: a remembered form that is switched off falls back to Current state */
/* #110: the words of the four fields (their value too, as data-v), the Draw on line and the fold's summary */
export function genStrip(){ const g=shared.GEN, set=(id,v,t)=>{ const b=$("#"+id); b.dataset.v=String(v); b.querySelector(".gv").textContent=t; };
  set("genDays",g.days,g.days==="custom"?"Dates…":`Last ${g.days} days`); set("genFormKind",g.form,(GEN_FORMS.find(x=>x[0]===g.form)||GEN_FORMS[0])[1]);
  set("genAud",g.aud,(GEN_AUD.find(x=>x[0]===g.aud)||GEN_AUD[0])[1]); set("genLen",g.len,(GEN_LEN.find(x=>x[0]===g.len)||GEN_LEN[1])[1]); }
export function genSrcOpen(on){ const b=$("#genSrcBtn"); b.setAttribute("aria-expanded",String(on)); $("#genSrc").hidden=!on; }
export function genSrcLine(){ const c=shared.GEN.aud==="client", off=shared.GEN.aud!=="internal"||shared.GEN.form!=="current";
  const on=[...$$("#genSrc input:checked")].map(i=>i.value), names=GEN_SRC.filter(x=>on.includes(x[0])).map(x=>x[3]);
  $$("#genSrc input").forEach(i=>{ i.disabled=off; }); $("#genSrc").classList.toggle("off",off); $("#genOff").hidden=!c;
  $("#genSrcSum").textContent=c?"Drawing on client-visible items":on.length?`Drawing on ${plur(on.length,"source")}`:"Drawing on no sources";
  $("#genSrcNames").textContent=c||!names.length?"":`· ${names.join(", ")}`; }
/* the fold's summary: Form, period, Audience, sources (#110 addendum) */
export function genSummary(){ const g=shared.GEN, f=$("#genFrom").value.trim(), t=$("#genTo").value.trim();
  const per=g.days==="custom"?`${f||"the start"} to ${t||"today"}`:`last ${g.days} days`, n=$$("#genSrc input:checked").length;
  return [(GEN_FORMS.find(x=>x[0]===g.form)||GEN_FORMS[0])[1],per,(GEN_AUD.find(x=>x[0]===g.aud)||GEN_AUD[0])[1],g.aud==="client"?"client-visible items":plur(n,"source")]; }
export const execOpts=()=>{ const o=(shared.CURED&&shared.CURED.opts)||{}; return {audience:o.audience||shared.GEN.aud,length:o.length||shared.GEN.len,...(o.from?{from:o.from}:{}),...(o.to?{to:o.to}:{})}; };
export function notesHtml(){ const h=(()=>{ const n=shared.CURED&&shared.CURED.notes; if(shared.CURED&&shared.CURED.checking) return '<span class="sub">Checking the wording…</span>';
  if(!n) return viaServer()?'<button class="mini" data-chk="1">Check the wording</button>':"";
  return (n.length?`<div class="sub">Notes on this draft (none of them stops you saving)</div><ul>${n.map(x=>`<li>${esc(x.note)}</li>`).join("")}</ul>`:'<span class="oknote">✓ Passes the checks.</span> ')+' <button class="mini" data-chk="1">Check again</button>'; })();
  return shared.CURED&&viaServer()&&!shared.CURED.checking?h+' <button type="button" class="mini" data-chksrc="" title="Find the sources of every sentence again, from today\'s facts">Check sources</button>':h; }
export function setNotes(){ const el=$("#genNotes"); if(el) putHTML(el,raw(notesHtml())); const f=$("#genFacts"); if(f&&shared.CURED){ f.hidden=!shared.CURED.facts; putHTML(f,html`<summary>Facts it was written from</summary>${raw(factsHtml(shared.CURED.facts))}`); } }
export function factsHtml(t){ return String(t||"").split(/\n(?=## )/).map(b=>{ const L=b.split("\n").filter(x=>x.trim()); if(!L.length) return ""; const head=L[0].startsWith("## ")?`<strong>${esc(L[0].slice(3))}</strong>`:"";
  return `<div class="factblk">${head}<ul>${L.slice(head?1:0).map(x=>`<li>${esc(x.replace(/^- /,""))}</li>`).join("")}</ul></div>`; }).join(""); }
export async function curCheck(text,original){ const cur=shared.CURED; if(!cur||!viaServer()) return; text=text??edValue($("#curEd")); if(!String(text).trim()){ cur.notes=[]; setNotes(); return; }
  const claims=cur.claims?claimsPayload("ed"):undefined;   /* BL-207 */
  const gen=cur.gen|0; cur.checking=true; curReady(false); setNotes(); const r=await api("/api/current/check",{code:cur.code,text,sources:cur.sources||"",original,claims,...execOpts()});
  if(shared.CURED!==cur||(cur.gen|0)!==gen) return;   /* closed, or another version loaded meanwhile (that one has its own check): this answer is for text no longer shown */
  cur.checking=false; if(r.ok){ cur.notes=r.notes; cur.facts=r.facts; if(r.evidence) claimsApply("ed",r.evidence,claims); } else { cur.notes=null; snack(oneLine(r.message)||"Couldn't check the draft"); }
  setNotes(); curReady(true); return r; }
export function rewriteHtml(){ const rw=shared.CURED&&shared.CURED.rewrite; if(!rw) return "";
  const notes=rw.notes?(rw.notes.length?`<ul class="rwnotes">${rw.notes.map(x=>`<li>${esc(x.note)}</li>`).join("")}</ul>`:'<div class="oknote">✓ Passes the checks and keeps your dates and numbers.</div>'):'<div class="sub">Checking…</div>';
  return `<div class="genrewrite" id="genRewrite" role="region" aria-label="Executive version"><div class="rwhead"><strong>Executive version</strong> <span class="sub">A draft. What is in the editor above is unchanged until you use this.</span></div>
    <div class="rwbody">${mdHtml(rw.md,(P.find(x=>x.code===shared.CURED.code)||{}).images)}</div>${notes}
    <div class="curacts"><span class="sp"></span><button class="btn" data-rw="discard">Discard</button><button class="btn primary" data-rw="use">Use this version</button></div></div>`; }
export function execRewrite(){ if(!shared.CURED) return; if(shared.RUN||shared.GEN.run){ snack("ask creaite is busy; try again when it's finished"); return; } if(!viaServer()){ snack("Make it executive needs the live server"); return; }
  const text=edValue($("#curEd")); if(!text.trim()){ snack("Write something first, or use Generate"); return; }
  runGen({code:shared.CURED.code,text,...execOpts()},"rewrite"); }
export function execResult(code,original,md){ if(!shared.CURED||shared.CURED.code!==code){ snack("The rewrite finished, but the editor was closed. Nothing was changed."); return; }
  shared.CURED.rewrite={md,original,notes:null}; mountCurEdit(); snack("Executive version ready. Use it or discard it; your text is unchanged.");
  const cur=shared.CURED, rw=cur.rewrite, claims=claimsPayload("rw"); api("/api/current/check",{code:cur.code,text:stripMarks(md),original,sources:"",claims,...execOpts()}).then(r=>{ if(shared.CURED!==cur||cur.rewrite!==rw) return;
    rw.notes=r.ok?r.notes:[]; if(r.ok) cur.facts=r.facts; setRewrite(); setNotes(); if(r.ok&&r.evidence) claimsApply("rw",r.evidence,claims); }); }
/* BL-301 D: Make it executive is now an option of AI ▾ beside Save (the whole Current state, with its facts and evidence, as
   before); the other options act on the whole pane the cursor was last in, and on a selection through the bar over it. */
export function curAiMenu(){ const el=$("#curAi"); if(!el||!shared.CURED) return;
  mountAiMenu(el,{place:"current",onExecutive:execRewrite,target:()=>{ const c=shared.CURED; const h=c&&(c.last===2?c.ed2:c.ed1); return h?{h,ai:{place:"current",project:()=>c.code}}:null; }}); }
export function setRewrite(){ const el=$("#genRewrite"); if(el) swapHTML(el,raw(rewriteHtml())); rwWrap(); evRefresh(); }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootProjects0055(){
document.addEventListener("click",e=>{ if(!shared.CURED) return;
  if(e.target.closest("[data-chk]")){ curCheck(); return; }
  const rw=e.target.closest("[data-rw]"); if(rw&&shared.CURED.rewrite){ const md=shared.CURED.rewrite.md; shared.CURED.rewrite=null;
    if(rw.dataset.rw==="use"){ curLoad(1,md); shared.CURED.dirty=true; shared.CURED.notes=null; shared.CURED.claims=null; mountCurEdit(); claimsInit("ed"); curCheck(); }
    else mountCurEdit(); } });
}
/* ======================= Current state, edited in place (BL-47) ======================= */
shared.CURED=null;   /* {code, orig (Markdown), src1, src2 (each pane's Markdown when its editor is made), ed1, ed2 (the panes' editors, BL-301 A: kept across re-renders), dirty} */
/* BL-301 A: each pane is the one editor (core/editor.js), loaded and saved as Markdown byte for byte; pictures are its image
   node, drawn as before (figure.cimg, an editable caption, ×). Paste keeps only what Current state supports (from Word,
   Outlook or a web page), and a pasted or dropped picture is added as before (BL-63). */
export const CUR_PROPS={
  transformPastedHTML:h=>mdHtml(htmlToMd(new DOMParser().parseFromString(h,"text/html").body)).replace(/<(\/?)h([345])>/g,(m,close,n)=>"<"+close+"h"+(n-HEAD_SHIFT)+">"),   /* #122: stored ### #### ##### are the editor's Heading 1 to 3 */
  handlePaste:(view,e)=>{ const pics=[...((e.clipboardData&&e.clipboardData.files)||[])].filter(f=>/^image\//.test(f.type)); if(!pics.length) return false;
    (async()=>{ for(const f of pics) await insertImage(f,view.dom); })(); return true; },
  handleClick:(view,pos,e)=>{ const id=chipClicked(e), hit=id&&itemOf(id); if(!hit) return false; curOpenItem(hit.k,id); return true; },   /* #122 C: an item link is a chip; a click opens it, Alt-click edits inside it */
  handleDrop:(view,e)=>{ const files=[...((e.dataTransfer&&e.dataTransfer.files)||[])]; if(!files.length) return false; e.preventDefault();
    const at=view.posAtCoords({left:e.clientX,top:e.clientY}); (async()=>{ for(const f of files) await insertImage(f,view.dom,at?at.pos:undefined); })(); return true; } };
/** #122 C: a chip in the editor opens its item in the peek beside the text; the editor and its unsaved changes stay (openRecord alone would ask to discard them) */
export function curOpenItem(k,id){ const c=shared.CURED; shared.CURED=null; try{ openRecord(k,id); } finally{ shared.CURED=c; } }
/** pane n's editor, made from its text (shared.CURED.srcN) or, made before, moved into the card just drawn */
export function curAttach(n){ const c=shared.CURED, slot=$(n===2?"#curEd2":"#curEd"), k=n===2?"ed2":"ed1"; if(!c||!slot) return;
  if(c[k]&&!c[k].editor.isDestroyed){ for(const a of ["aria-label","data-ph"]) c[k].el.setAttribute(a,slot.getAttribute(a)); slot.replaceWith(c[k].el); return; }
  const imgs=(P.find(x=>x.code===c.code)||{}).images;
  c[k]=creaiteEditor(slot,{features:"current",headShift:HEAD_SHIFT,extensions:[itemChips()],markdown:(n===2?c.src2:c.src1)||"",imageSrc:ref=>imgSrc(imgs,ref),editorProps:CUR_PROPS,
    ai:{place:"current",project:()=>(shared.CURED&&shared.CURED.code)||""}});   /* BL-301 D: AI on selected text */
  attachSlash(c[k],{profile:"current",host:{image:pickImage,item:()=>insertHash(c[k])}});   /* #122 B: the / menu (taken away with the editor) */
  attachItemPick(c[k],{code:()=>(shared.CURED&&shared.CURED.code)||""}); }   /* #122 C: the shared # list, this project's items (taken away with the editor) */
/** a new text for pane n (a draft, or the executive version): its editor is made again from it when the card is drawn */
export function curLoad(n,md){ const c=shared.CURED; if(!c) return; c.gen=(c.gen|0)+1; const k=n===2?"ed2":"ed1"; if(c[k]){ c[k].destroy(); c[k]=null; } if(n===2) c.src2=md; else c.src1=md; }
export function startCurEdit(code,pane){ if(shared.CURED||navBlocked()) return; const p=P.find(x=>x.code===code); if(!p) return; const [l,r]=splitPanes(p.current||"");
  if(pane===2) store.set("creaite-cur-collapsed",false);
  shared.CURED={code,orig:p.current||"",src1:l,src2:r,ed1:null,ed2:null,dirty:false,uploads:{},removed:new Set(),last:pane||1}; mountCurEdit();
  /* a reopened editor carries the saved links; only fresh or edited sentences go to the check */
  if(!shared.CURED) return; const ev=evSaved(code), root=$("#curEd"); if(!ev||!root) return;
    const set={}; claimsMatch(root,ev).forEach(({n,h})=>{ const e=ev[h]; set[n]={text:claimText(root,n),ids:[],how:(e.how==="none"||e.how==="kept")?"none":"saved",saved:e,touched:true,...(e.kept!=null?{kept:e.kept}:{})}; });
    if(Object.keys(set).length){ shared.CURED.claims=set; claimPaint("ed"); } }
/** a signal for tests and assistive tech, no visible change: #curEd carries data-ready once the editor is mounted, its version drawn and the wording check has landed
    (the check changes the height of the notes above the version bar), and data-draw="N" (counts up with each draw). Both are taken off while a draw or a check is under way. */
function curReady(on){ const e=$("#curEd"); if(!e) return; if(on) e.dataset.ready="1"; else e.removeAttribute("data-ready"); }
function curDrawn(){ const e=$("#curEd"); if(!e) return; shared.CURDRAW=(shared.CURDRAW|0)+1; e.dataset.draw=String(shared.CURDRAW); if(!shared.CURED.checking) curReady(true); }
export function mountCurEdit(){ curReady(false); (()=>{ const card=$("#v-cockpit .curcard"), box=card&&card.querySelector(".curtext"); if(!shared.CURED||!box||shared.COCK!==shared.CURED.code) return;
  card.classList.add("editing"); card.querySelectorAll(".pencil").forEach(b=>b.hidden=true);
  curBarOff();
  putHTML(box,html`<div class="rte inplace"><div id="curBar" class="curbar"></div>
    ${raw(curPanes(`<div class="rted" id="curEd" data-ph="Write here…" role="textbox" aria-multiline="true" aria-label="Current state, left pane" spellcheck="true"></div>`,`<div class="rted" id="curEd2" data-ph="Write here…" role="textbox" aria-multiline="true" aria-label="Current state, right pane" spellcheck="true"></div>`,"edit",!!splitPanes(shared.CURED.orig)[1]||!!String(shared.CURED.ed2?edValue(shared.CURED.ed2.el):shared.CURED.src2||"").trim()))}<input type="file" id="curImgFile" accept="image/png,image/jpeg" multiple hidden></div>
    <div class="gennotes" id="genNotes" aria-live="polite">${raw(notesHtml())}</div>${raw(rewriteHtml())}
    ${shared.CURED.opts&&viaServer()?raw(refineHtml("cur",{client:shared.CURED.opts.audience==="client",note:shared.CURED.refineNote||"",busy:shared.CURED.refining,status:shared.CURED.refineStatus,msg:((shared.CURED.vers||[])[shared.CURED.at||0]||{}).msg})):""}
    ${shared.CURED.sources?html`<details class="gensrc" open><summary>Drafted from</summary>${raw(mdHtml(shared.CURED.sources))}</details>`:""}
    <details class="gensrc" id="genFacts" ${shared.CURED.facts?"":"hidden"}><summary>Facts it was written from</summary>${raw(factsHtml(shared.CURED.facts))}</details>
    <div class="curacts"><span class="sub">⌘↵ saves · Esc cancels</span><span class="sp"></span><span id="curAi" class="curai"></span><button class="btn" data-cure="cancel">Cancel</button><button class="btn primary" data-cure="save">Save</button></div>`);
  curAttach(1); curAttach(2); curBar(); curAiMenu(); $$(".curpanes .rted").forEach(e=>{ paneBlank(e); }); shared.CURED.shown=new Set(figRefs($(".curpanes"))); (shared.CURED.last===2?$("#curEd2"):$("#curEd")).focus(); })();
  if(shared.CURED){ const t=csTitle(shared.CURED.code);
    $("#curEd")?.setAttribute("aria-label",`${t}, left pane`); $("#curEd2")?.setAttribute("aria-label",`${t}, right pane`); csHead(shared.CURED.code); }
  if(shared.CURED){ claimPaint("ed"); rwWrap(); evRefresh(); curVersSync(); curDrawn(); } }
export function endCurEdit(){ curBarOff(); evPanelClose(); curDrop(); DISCARD=null; $("#discardBar").classList.remove("on"); if(shared.VIEW==="cockpit") renderCockpit(shared.COCK); }
export const figRefs=ed=>[...ed.querySelectorAll("figure.cimg")].map(f=>f.dataset.ref).filter(r=>r&&!r.startsWith("new:"));
/* BL-76: an image taken out with its × stays out when saved; one that merely isn't in a drafted text is kept. (Only the × removes a
   picture: Backspace and Delete don't remove one, because its caption is editable.) */
export function noteRemoved(ed){ if(!shared.CURED) return; const now=new Set(figRefs(ed)); (shared.CURED.shown||[]).forEach(r=>{ if(!now.has(r)) shared.CURED.removed.add(r); }); shared.CURED.shown=now; }
export const imageRefs=md=>String(md||"").split("\n").map(l=>(l.match(MD_IMG)||[])[2]).filter(Boolean);
export async function saveCurEdit(){ const cur=shared.CURED, code=cur&&cur.code, payload=cur?evidencePayload():null, had=!!evSaved(code);
  await (async()=>{ if(shared.CURED&&shared.CURED.claims&&!shared.CURED.saving){ const root=$("#curEd");
    const wait=claimOrder(root).filter(n=>{ const c=shared.CURED.claims[n]; return c&&claimState(c)==="none"&&!c.touched; });
    if(wait.length){ evPanelOpen("ed",wait[0]); snack(wait.length===1?"One sentence has no source. Edit it, or keep it with a note, then Save.":`${wait.length} sentences have no source. Edit each one, or keep it with a note, then Save.`); return; } }
  if(!shared.CURED||shared.CURED.saving) return; const code=shared.CURED.code; let md=stripMarks(joinPanes(edValue($("#curEd")),edValue($("#curEd2"))));   /* BL-207: never a fact mark */   /* BL-89: one message, one save */
  if(md.trim()===String(shared.CURED.orig).trim()){ endCurEdit(); return; }
  /* BL-76: the editor stays open, with the text and pictures as they are, until the save has worked. Images staged for a save that
     didn't happen are taken away again. */
  shared.CURED.saving=true; const staged=[], cur=shared.CURED, giveUp=async msg=>{ for(const f of staged){ try{ await shared.VW.remove(f); }catch(e){} } if(msg) snack(msg); cur.saving=false; };
  /* BL-63: each new image is staged in system/staging/uploads/ and filed in the project's images/ with the text */
  const ups=shared.CURED.uploads||{}, ids=[...md.matchAll(/\]\(new:([a-z0-9]+)\)/g)].map(m=>m[1]).filter(id=>ups[id]), ops=[], added=[], notSaved=()=>$("#snack").classList.contains("on")?"":"Not saved: the live server isn't running and the vault isn't connected. Your text and pictures are still here.";
  if(ids.length){ if(!await needVault()){ await giveUp(notSaved()); return; } const dir=((D.image_dirs&&D.image_dirs[code])||`projects/${D.folders[code]}/images`)+"/", taken=new Set();   /* BL-85: the mapped images folder */
    for(const id of ids){ const u=ups[id], cap=(md.match(new RegExp(`!\\[([^\\]]*)\\]\\(new:${id}\\)`))||[])[1]||"", ext=u.file.type==="image/png"?"png":"jpg";
      const slug=((cap||u.file.name.replace(/\.[^.]+$/,"")).toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"").slice(0,40))||"image";
      let name=`${TODAY}-${slug}.${ext}`, i=2; try{ while(taken.has(name)||await shared.VW.exists(dir+name)) name=`${TODAY}-${slug}-${i++}.${ext}`; }catch(e){} taken.add(name);   /* no spaces: Markdown image links */
      const stagedPath=`system/staging/uploads/${stampFile()}-${id}.${ext}`;
      try{ await vq(()=>shared.VW.upload(stagedPath,u.file)); }catch(e){ await giveUp(`Not saved: ${e.message}. Your text and pictures are still here.`); return; }
      staged.push(stagedPath); ops.push({op:"copy",from:stagedPath,to:dir+name},{op:"remove",path:stagedPath}); md=md.replace(`](new:${id})`,`](images/${name})`); added.push({alt:cap,ref:`images/${name}`,src:u.src}); } }
  /* an image taken out with its × is dropped from the text; the file stays */
  const dropped=[...shared.CURED.removed].filter(r=>!md.includes(`](${r})`));
  const ok=await saveCurrent(code,md,ops,added,dropped);
  if(!ok){ await giveUp(notSaved()); return; }
  if(shared.CURED===cur) curDrop(); if(shared.VIEW==="cockpit") renderCockpit(shared.COCK); })();
    if(cur&&shared.CURED!==cur&&payload&&(Object.keys(payload).length||had)&&viaServer()){
      const w=await api("/api/current/evidence",{code,sentences:payload}); const p=P.find(x=>x.code===code); if(w.ok&&p){ p.ev=payload; if(shared.VIEW==="cockpit"&&shared.COCK===code) readClaims(code); } } }
export function pickImage(){ const i=$("#curImgFile"); if(i) i.click(); }
/** BL-63: a picture added to a pane (`at`: the pane, or a node in it; `pos`: where it was dropped), as its own block after the
    block holding the cursor (or the drop point), else at the end; then its caption has the focus */
export async function insertImage(file,at,pos){ const ed=curPane(at), h=edOf(ed); if(!ed||!h||!shared.CURED) return;
  if(!/^image\/(png|jpeg)$/.test(file.type)){ snack(`${file.name} can't be added: only PNG or JPEG images`); return; }
  if(file.size>2*1024*1024){ snack(`${file.name} is over 2 MB: images can be 2 MB at most (keeps the dashboard small)`); return; }
  const src=await new Promise(res=>{ const fr=new FileReader(); fr.onload=()=>res(fr.result); fr.readAsDataURL(file); });
  const id=Date.now().toString(36)+Math.random().toString(36).slice(2,6); (shared.CURED.uploads=shared.CURED.uploads||{})[id]={file,src};
  const st=h.editor.state, end=st.doc.content.size, sel=getSelection(), inside=sel&&sel.rangeCount&&ed.contains(sel.anchorNode);
  const at0=typeof pos==="number"?pos:inside?st.selection.from:end, $p=st.doc.resolve(Math.min(at0,end)), after=$p.depth?$p.after(1):end;
  const nodes=[{type:"image",attrs:{src:`new:${id}`,alt:""}},...(after>=end?[{type:"paragraph"}]:[])];
  h.editor.chain().insertContentAt(after,nodes).run();
  const cap=ed.querySelector(`figure[data-ref="new:${id}"] figcaption`); if(cap) cap.focus(); }
export function cancelCurEdit(){ if(shared.CURED&&shared.CURED.dirty) askDiscard(()=>{}); else endCurEdit(); }
/* unsaved changes: leaving asks first (the dashboard never uses browser dialogs) */
export let DISCARD=null;
export function askDiscard(then){ DISCARD=then; $("#discardBar").classList.add("on"); $("#discardBar [data-dis=keep]").focus(); }
export const PKN={seq:0};   /* BL-179: declared before curGuard, which runs at load (navBlocked) and reads it */
export function curGuard(retry){ if(!PKN.force&&pkNewPending()){ pkNewAsk(retry); return true; } if(shared.CURED&&shared.CURED.dirty){ askDiscard(retry); return true; } if(shared.CURED) curDrop(); return false; }
/* #122 step A: the toolbar is the shared EditorBar (components/EditorBar.jsx, profile "current"): its buttons, keys, link form and
   ⌘⇧K / ⌘⇧X come from there. The bar acts on the pane the cursor is in. */
export function curBar(){ const el=$("#curBar"); if(!el) return;
  mountEditorBar(el,{profile:"current",legacyRc:true,handle:()=>edOf(curPane()),host:{image:pickImage,item:()=>{ const h=edOf(curPane()); if(h) insertHash(h); }}}); }
/** the bar is taken out of the page when the card is drawn again or editing ends (its listeners go with it) */
export function curBarOff(){ const el=$("#curBar"); if(el) unmountEditorBar(el); }
/* the pane the cursor is in, for the keys below */
export function rteCmd(cmd){ const h=edOf(curPane()); if(h) runTool(h,cmd); }
shared.DRH=null;                                          /* the health form's draft: {code, html, d, used} */
shared.HBACK=null;   /* #109: the pencil that opened the health form, to give focus back */
shared.PKDRC=null;   /* declared before closePanel, which runs at load */
export const PK={wide:false,key:null};   /* declared before closePanel, which runs at load */
export const pkOn=()=>$("#panel").classList.contains("on")&&$("#panel").classList.contains("peek");   /* declared before closePanel, which runs at load */
shared.PDBASE=null; shared.PDKEY=null; shared.PDOFFER=null; shared.PDT=null;   /* declared before closePanel, which runs at load */
export function closePanel(quiet){ if(shared.DRH){ if(shared.DRH.d) draftStat("reason","rejected"); shared.DRH=null; }   /* BL-222 */
  if(shared.PKDRC) pkDrDrop();   /* AI drafts */
  if($("#pkAsk")){ if(!PKN.force&&pkNewPending()){ pkNewAsk(null); return; }
    if(shared.CUR&&shared.CUR.mode==="new"&&!PKN.keep){ clearTimeout(shared.PKNT); pdDrop(pkNewKey()); }   /* empty, staged or discarded: nothing is kept */
    pkNewAskOff(); PKN.offer=null; pkNewOffer(""); }   /* BL-179: a new item in the peek (nothing to do while the page loads, before the peek is built) */
  PK.dirty=false; $("#panel").classList.remove("pkprop");   /* BL-250 A */
  const was=pkOn(), a=document.activeElement; if(a&&a!==document.body&&$("#panel").contains(a)) a.blur();   /* a text field commits as it closes, and no focus is left in a closed panel */   /* BL-166 */
  if(shared.EDITING&&shared.PDKEY) pdDrop(shared.PDKEY); shared.PDKEY=shared.PDBASE=shared.PDOFFER=null;   /* BL-169 */
  const wasItem=shared.CUR&&shared.CUR.mode==="record"; $("#panel").classList.remove("on","pwide","pover"); const back=shared.CUR&&shared.CUR.mode==="health"?shared.HBACK:null; shared.HBACK=null; shared.CUR=null; shared.EDITING=false; closeCal(); closeCombobox(); if(shared.SEL){ shared.SEL=null; markSel(); } if(wasItem&&!quiet) navWrite(false); 
  $("#panel").classList.remove("peek"); if(was){ PK.wide=false; PK.key=null; }
  { const o=document.activeElement; if(o&&o!==document.body&&!$("#panel").contains(o)&&o.closest("[data-open],tr[data-row],.bcard[data-row]")) o.blur(); }   /* #108: focus left on the panel the peek was opened from drew it highlighted (ring and row actions) after Esc, Close, a click outside or navigation: nothing stays highlighted */
  if(back&&back.isConnected) back.focus({preventScroll:true});   /* #109 */
  if(shared.PREPPEEK&&shared.PREPPEEK!=="swap") prepPeekEnd(); }   /* BL-286 E: the Prep popup comes back, modal, with focus on the item */
   /* looked up when clicked, so Close runs every later step (as Cancel and Esc do) */
/* BL-78: ⌘+Enter (Ctrl+Enter on Windows) runs the open form's own Save and closes the panel. A failed check or a question leaves it open
   with the message. Not in the read view, not from the chat, search or the Current state editor, not on key repeat or while a save runs. */
export async function saveAndClose(){ if(!shared.CUR||!shared.EDITING||shared.CUR.saving||!$("#panel").classList.contains("on")) return; const cur=shared.CUR; cur.saving=true;
  try{ await savePanel(false,true); } finally{ cur.saving=false; } }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootProjects0056(){
document.addEventListener("change",async e=>{ if(e.target.id!=="curImgFile") return; for(const f of [...e.target.files]) await insertImage(f); e.target.value=""; });
document.addEventListener("click",e=>{ const b=e.target.closest(".curpanes .cimgdel"); if(!b) return; e.preventDefault(); const ed=b.closest(".rted"), f=b.closest("figure"); if(f.cxRemove) f.cxRemove(); else f.remove(); noteRemoved($(".curpanes")); ed.focus(); });
document.addEventListener("input",e=>{ if(shared.CURED&&e.target.closest&&e.target.closest(".curpanes figcaption")) shared.CURED.dirty=true; });
document.addEventListener("keydown",e=>{ if(!(e.target.closest&&e.target.closest(".curpanes figcaption"))) return; const mod=e.metaKey||e.ctrlKey;   /* a caption is one line */
  if(e.key==="Escape"){ e.preventDefault(); e.stopPropagation(); cancelCurEdit(); }
  else if(e.key==="Enter"){ e.preventDefault(); if(mod) saveCurEdit(); else { const nx=e.target.closest("figure").nextElementSibling; if(nx){ const r=document.createRange(); r.selectNodeContents(nx); r.collapse(true); const s=getSelection(); s.removeAllRanges(); s.addRange(r); e.target.closest(".rted").focus(); } } } },true);
document.addEventListener("dragover",e=>{ if(e.target.closest&&e.target.closest(".curpanes .rted")&&[...e.dataTransfer.types].includes("Files")) e.preventDefault(); });
document.addEventListener("click",e=>{ const d=e.target.closest("[data-dis]"); if(!d) return; const then=DISCARD; $("#discardBar").classList.remove("on"); DISCARD=null;
  if(d.dataset.dis==="go"){ curDrop(); if(shared.VIEW==="cockpit") renderCockpit(shared.COCK); if(then) then(); } else $("#curEd")?.focus(); });
document.addEventListener("click",e=>{ const c=e.target.closest("[data-cure]"); if(c){ c.dataset.cure==="save"?saveCurEdit():cancelCurEdit(); } });
document.addEventListener("input",e=>{ if(shared.CURED&&e.target.classList&&e.target.classList.contains("rted")&&e.target.closest(".curpanes")){ shared.CURED.dirty=true; paneBlank(e.target); } });
document.addEventListener("focusin",e=>{ const ed=e.target.closest&&e.target.closest(".curpanes .rted"); if(ed&&shared.CURED) shared.CURED.last=ed.id==="curEd2"?2:1; });
document.addEventListener("keydown",e=>{
  if(!(e.target.classList&&e.target.classList.contains("rted")&&e.target.closest(".curpanes"))) return; const mod=e.metaKey||e.ctrlKey;   /* ⌘K stays the palette; ⌘⇧K and ⌘⇧X are the shared bar's (#122) */
  if(slashOn(e.target)&&(e.key==="Escape"||e.key==="Tab"||(mod&&e.key==="Enter"))) return;   /* #122 B: the / menu is open: Esc closes it, Tab inserts the row and ⌘↵ waits (components/SlashMenu.jsx), not cancel, indent or save */
  if(e.key==="Escape"){ e.preventDefault(); e.stopPropagation(); cancelCurEdit(); }
  else if(mod&&e.key==="Enter"){ e.preventDefault(); saveCurEdit(); }
  else if(e.key==="Tab"&&getSelection().anchorNode&&(getSelection().anchorNode.parentElement||{}).closest&&getSelection().anchorNode.parentElement.closest("li")){ e.preventDefault(); rteCmd(e.shiftKey?"outdent":"indent"); } },true);
/* a caption is one line of plain text (the editor itself pastes in the text: CUR_PROPS) */
document.addEventListener("paste",e=>{ if(e.target.closest&&e.target.closest(".curpanes figcaption")){ e.preventDefault(); document.execCommand("insertText",false,e.clipboardData.getData("text/plain").replace(/\s+/g," ")); } });
$("#pClose").onclick=()=>closePanel();
}
/* ===== BL-162 (sprint-rail) ===== the Current state card's title, renamed by clicking it. A label for the dashboard only, per project:
   "- **Current state title:** <words>" in the project's CLAUDE.md, beside the client-report rhythm; the "## Current state" section
   keeps its name, so the reports, Generate, Make it executive, search and the checks still find it. build_dashboard.memory() reads it
   as p.cstitle. Saved like setRhythm: needs the vault, a copy of the file in system/backups/files/, a line in settings-log.jsonl
   (current_state_title.<CODE>), and the snack offers Undo. An empty title or the default words remove the line. Without the live
   server's vault access, or while the Current state editor is open, the heading is plain text (one thing at a time). */
export const CST_DEF="Current state", CST_MAX=40;
export const csTitle=code=>{ const p=P.find(x=>x.code===code); return (p&&p.cstitle)||CST_DEF; };
export const csClean=v=>String(v||"").replace(/!?\[([^\]]*)\]\([^)]*\)/g,"$1").replace(/[*_`#>~|\\]/g,"").replace(/\s+/g," ").trim().slice(0,CST_MAX).trim();
export function csLine(text,title){ const re=/^[ \t]*(?:[-*][ \t]+)?\*\*Current state title:\*\*[^\n]*(?:\n|$)/m;
  if(title===CST_DEF) return text.replace(re,"");
  if(re.test(text)) return text.replace(/^([ \t]*(?:[-*][ \t]+)?)\*\*Current state title:\*\*[^\n]*/m,(m,pre)=>`${pre}**Current state title:** ${title}`);
  const rh=/^([ \t]*(?:[-*][ \t]+)?)\*\*Client report rhythm:\*\*[^\n]*$/m; if(rh.test(text)) return text.replace(rh,(m,pre)=>`${m}\n${pre}**Current state title:** ${title}`);
  if(/^## Current state/m.test(text)) return text.replace(/^## Current state/m,`- **Current state title:** ${title}\n\n## Current state`);
  return text.replace(/\s*$/,`\n\n- **Current state title:** ${title}\n`); }
export const csEditable=code=>viaServer()&&!(shared.CURED&&shared.CURED.code===code);
export function csHeadHtml(code){ const t=csTitle(code);
  return csEditable(code)?`<button type="button" class="cstbtn" data-cst="${esc(code)}" data-tip="Rename this title">${esc(t)}${ic("pencil","csp")}</button>`:esc(t); }
export function csHead(code){ const h=$("#v-cockpit .curcard>h2"); if(!h) return; h.classList.add("cshead"); h.id="csHead"; putHTML(h,raw(csHeadHtml(code)));
  const card=h.closest(".curcard"); if(card) card.setAttribute("aria-labelledby","csHead"); }
export function csStart(btn){ const code=btn.dataset.cst, h=btn.closest("h2"); if(!h||!csEditable(code)) return; tipHide();
  putHTML(h,html`<input type="text" class="cstin" maxlength="${raw(CST_MAX)}" aria-label="Title of this card" value="${csTitle(code)}" data-cstcode="${code}">`);
  const i=h.querySelector("input"); i.focus(); i.select(); let done=false;
  const end=async keep=>{ if(done) return; done=true; if(keep) await csSave(code,i.value); else { csHead(code); $("#v-cockpit .cstbtn")?.focus(); } };
  i.addEventListener("keydown",e=>{ if(e.key==="Enter"){ e.preventDefault(); e.stopPropagation(); end(true); } else if(e.key==="Escape"){ e.preventDefault(); e.stopPropagation(); end(false); } });
  i.addEventListener("blur",()=>end(true)); }
export async function csWrite(code,title){ let before="", wrote="";
  await vq(async()=>{ const path=memPath(code); before=await shared.VW.read(path); wrote=csLine(before,title); if(wrote===before) return;
    await shared.VW.write(await freeBackup(`system/backups/files/${code}-CLAUDE-`,".md"),before); await shared.VW.write(path,wrote); });
  return {before,wrote}; }
export async function csSave(code,raw){ const p=P.find(x=>x.code===code); if(!p) return; const old=p.cstitle||CST_DEF; let t=csClean(raw); if(!t||t.toLowerCase()===CST_DEF.toLowerCase()) t=CST_DEF;
  const back=()=>{ if(shared.VIEW==="cockpit"&&shared.COCK===code){ csHead(code); $("#v-cockpit .cstbtn")?.focus(); } };
  if(t===old){ back(); return; }
  if(!await needVault()){ back(); return; }
  try{ const {before,wrote}=await csWrite(code,t);
    await shared.VW.append("system/config/settings-log.jsonl",JSON.stringify({at:stampFull(),key:`current_state_title.${code}`,old,new:t})+"\n");
    p.cstitle=t; back();
    snack(t===CST_DEF?"Title back to “Current state”":`Title: ${t}`,()=>csUndo(code,old,t,before,wrote)); }
  catch(e){ snack("Not saved: "+e.message); back(); } }
export async function csUndo(code,old,now,before,wrote){ const p=P.find(x=>x.code===code); if(!await needVault()) return;
  try{ await vq(async()=>{ const path=memPath(code), cur=await shared.VW.read(path); await shared.VW.write(await freeBackup(`system/backups/files/${code}-CLAUDE-`,".md"),cur);
      await shared.VW.write(path,cur===wrote?before:csLine(cur,old));          /* the file as it was; or, if it changed since, only the line put back */
      await shared.VW.append("system/config/settings-log.jsonl",JSON.stringify({at:stampFull(),key:`current_state_title.${code}`,old:now,new:old})+"\n"); });
    if(p) p.cstitle=old; if(shared.VIEW==="cockpit"&&shared.COCK===code) csHead(code); snack("Title put back"); }
  catch(e){ snack("Not undone: "+e.message); } }
/* ===== end BL-162 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootProjects0058(){
document.addEventListener("click",e=>{ const b=e.target.closest("#v-cockpit .cstbtn"); if(b){ e.preventDefault(); csStart(b); } });
}
/* ===== BL-207 (sprint-insight) ===== evidence on hover. The executive Current state (Generate and Make it executive) comes back
   with each sentence ending in the facts it rests on ({F3, F7}, the facts sheet's IDs from status_facts.py). claimsWrap takes
   the marks out and wraps each sentence (a "claim") in spans; /api/current/check maps the IDs to rows and quotes (read from the
   files when asked, never stored); the panel shows them. A sentence with no source is marked as it arrives and Save waits until
   it is edited or kept with a note. A sentence edited by hand loses its mark until Check again re-checks it. Internal only:
   nothing here reaches the saved text, a report or the tracker. */
export const CLAIM_RE=/\s*\{\s*((?:F\d+\s*,?\s*)*)\}/;
export const stripMarks=md=>String(md||"").replace(new RegExp(CLAIM_RE.source,"g"),"").replace(/[ \t]+$/gm,"");
shared.EV=null;   /* the claim the panel shows: {which:"ed"|"rw", n} */
export function claimsWrap(root){ const out=[]; if(!root) return out; let n=0;
  for(const bl of root.querySelectorAll("p,li,blockquote")){ if(bl.closest("figure")) continue;
    const tw=document.createTreeWalker(bl,NodeFilter.SHOW_TEXT,{acceptNode:t=>t.parentElement.closest("p,li,blockquote,figure")===bl?1:2});
    const nodes=[]; while(tw.nextNode()) nodes.push(tw.currentNode);
    let pieces=[];
    const close=ids=>{ const text=pieces.map(t=>t.nodeValue).join("").replace(/\s+/g," ").trim();
      if(text&&(ids||(text.match(/[A-Za-z]{2,}/g)||[]).length>=3)){ n++;
        // @ts-expect-error TS2322: dataset stores the claim's number as a string
        pieces.forEach(t=>{ const sp=document.createElement("span"); sp.className="claim"; sp.dataset.c=n; t.parentNode.insertBefore(sp,t); sp.appendChild(t); });
        out.push({n,text,ids:ids||[]}); }
      pieces=[]; };
    for(let t of nodes){ let m;
      while(t&&(m=CLAIM_RE.exec(t.nodeValue))){ const before=t.nodeValue.slice(0,m.index), after=t.nodeValue.slice(m.index+m[0].length), ws=after.match(/^\s*/)[0];
        let nt=null; if(after.length>ws.length){ nt=document.createTextNode(after.slice(ws.length)); t.parentNode.insertBefore(nt,t.nextSibling); }
        if(ws) t.parentNode.insertBefore(document.createTextNode(ws),nt||t.nextSibling);
        if(before.trim()){ t.nodeValue=before; pieces.push(t); } else t.remove();
        close(m[1].match(/F\d+/g)||[]); t=nt; }
      if(t&&(t.nodeValue.trim()||pieces.length)) pieces.push(t); }
    close(null); }
  return out; }
export const evRoot=which=>which==="rd"?$("#curText .curpane[data-pane=\"1\"] .curin")||$("#curText"):which==="rw"?$("#genRewrite .rwbody"):$("#curEd");
export const claimSet=which=>which==="rd"?(shared.CURRD&&shared.CURRD.set):!shared.CURED?null:which==="rw"?(shared.CURED.rewrite&&shared.CURED.rewrite.claims):shared.CURED.claims;
export const claimSpans=(root,n)=>root?[...root.querySelectorAll(`.claim[data-c="${n}"]`)]:[];
export const claimText=(root,n)=>claimSpans(root,n).map(s=>s.textContent).join("").replace(/\s+/g," ").trim();
export const claimOrder=root=>root?[...new Set([...root.querySelectorAll(".claim[data-c]")].map(s=>+s.dataset.c))]:[];
export function claimState(c){ return c.how==="saved"&&!c.edited?"ok":c.edited?"edited":(c.how==="none"||(!c.how&&!c.ids.length))?(c.kept!=null?"kept":"none"):"ok"; }
export function claimTip(c){ if(c.how==="saved"&&!c.edited){ const n=(c.saved.facts||[]).reduce((a,f)=>a+(f.src||[]).length,0); return `Source: ${plur(n,"row")}`; }
  const st=claimState(c), ev=(shared.CURED&&shared.CURED.ev)||{};
  if(st==="edited") return "Edited by you: its source mark is off until you check again";
  if(st==="kept") return "Kept without a source"; if(st==="none") return "No source found for this sentence";
  if(!c.how) return "Source: checking…";
  const rows=c.ids.reduce((a,f)=>a+((ev[f]||{}).rows||[]).length+((ev[f]||{}).files||[]).length,0);
  return `Source: ${plur(rows,"row")}`; }
export function claimPaint(which){ const root=evRoot(which), set=claimSet(which); if(!root||!set) return; const edit=root.isContentEditable, seen=new Set();
  root.querySelectorAll(".claim[data-c]").forEach(s=>{ const c=set[s.dataset.c]; if(!c) return; const st=claimState(c), first=!seen.has(s.dataset.c); seen.add(s.dataset.c);
    s.classList.toggle("none",st==="none"); s.classList.toggle("kept",st==="kept"); s.classList.toggle("edited",st==="edited");
    if(first) s.dataset.first=""; else delete s.dataset.first;
    const tip=claimTip(c); s.title=tip+(st==="edited"?"":" · click to see"); s.setAttribute("aria-description",tip);
    if(!edit&&first){ s.tabIndex=0; s.setAttribute("role","button"); } }); }
export function claimsInit(which){ const root=evRoot(which); if(!root||!shared.CURED) return; const set={}, h=edOf(root);
  /* BL-301 A: in the editor the marks come out and the sentences become claim marks in one quiet step: the drafted text is
     wrapped as the read view wraps it, and the editor takes that back */
  const tpl=h?document.createElement("template"):null; if(tpl) putHTML(tpl,raw(h.editor.getHTML()));   /* a template: its pictures aren't fetched */
  claimsWrap(tpl?tpl.content:root).forEach(c=>{ set[c.n]={text:c.text,ids:c.ids,how:c.ids.length?"":"none"}; });
  if(tpl) h.editor.chain().setMeta(ED_QUIET,true).setMeta("addToHistory",false).setContent(tpl.innerHTML,{emitUpdate:false}).run();
  if(which==="rw"){ if(shared.CURED.rewrite) shared.CURED.rewrite.claims=shared.CURED.rewrite.claims||set; }
  else shared.CURED.claims=Object.keys(set).length?set:null;
  claimPaint(which); }
export function claimsPayload(which){ const root=evRoot(which), set=claimSet(which); if(!root||!set) return undefined;
  return claimOrder(root).filter(n=>set[n]).map(n=>({n,text:claimText(root,n),ids:set[n].ids||[],edited:!!set[n].edited}))
    .filter(c=>!(set[c.n]&&set[c.n].how==="saved"&&!set[c.n].edited)); }
export function claimsApply(which,ev,sent){ const set=claimSet(which), root=evRoot(which); if(!set||!ev||!shared.CURED) return;
  shared.CURED.ev={...(shared.CURED.ev||{}),...(ev.facts||{})};
  for(const c of ev.claims||[]){ const x=set[c.n]; if(!x) continue; const was=(sent||[]).find(s=>s.n===c.n);
    if(x.edited&&was&&was.text!==claimText(root,c.n)) continue;            /* typed again while it was being checked */
    x.ids=c.ids; x.how=c.how; if(x.edited){ x.edited=false; x.text=claimText(root,c.n); } }
  claimPaint(which); evRefresh(); }
export function claimTrack(){ const root=$("#curEd"); if(root&&shared.CURED&&shared.CURED.claims){ let changed=false;
  for(const [n,c] of Object.entries(shared.CURED.claims)){ if(c.edited) continue; if(claimText(root,n)!==c.text){ c.edited=true; c.touched=true; c.ids=[]; changed=true; } }
  if(changed){ claimPaint("ed"); evRefresh(); } }
  const set=shared.CURED&&shared.CURED.claims; if(set) Object.values(set).forEach(c=>{ if(c.edited&&c.saved){ c.saved=null; c.how=""; } }); }
/* The panel: in the peek's place, clear of the chat; Tab and ⇧Tab move between claims while it is open, Esc closes it. */
export function evEl(){ let p=$("#evPanel"); if(!p){ addHTML(document.body,"beforeend",html`<aside class="evpanel" id="evPanel" hidden role="complementary" aria-label="Source for this sentence"></aside>`); p=$("#evPanel"); } return p; }
export function evPanelOpen(which,n){ const root=evRoot(which), set=claimSet(which); if(!root||!set||!set[n]) return; shared.EV={which,n:+n};
  $$(".claim.cur").forEach(s=>s.classList.remove("cur")); claimSpans(root,n).forEach(s=>s.classList.add("cur")); evDraw(); }
export function evPanelClose(){ shared.EV=null; const p=$("#evPanel"); if(p) p.hidden=true; $$(".claim.cur").forEach(s=>s.classList.remove("cur")); }
export function evRefresh(){ if(shared.EV) evDraw(); }
export const EVWHAT={actions:"Action",raid:"RAID item",decisions:"Decision",milestones:"Milestone"};
export function evQuote(q){ return q&&q.text?`<blockquote class="evq">${esc(q.text)}</blockquote><div class="evqsrc">${esc(String(q.path).split("/").pop())}${q.line?`, line ${q.line}`:""}</div>`:""; }
export function evRowHtml(r){ const id=esc(r.id), link=r.kind==="milestones"?`<a href="#" class="hlink" data-ms="${id}">${id}</a>`:`<a href="#" class="hlink" data-open="${r.kind}:${id}">${id}</a>`;
  const due=r.due?(r.kind==="decisions"?"needed by ":r.kind==="milestones"?"forecast ":"due ")+fd(r.due):"";
  const bits=[EVWHAT[r.kind]||"",r.status,r.owner&&r.owner!=="TBC"?r.owner:"",due,r.closed?"closed "+fd(r.closed):""].filter(Boolean).join(" · ");
  return `<div class="evrow">${link} ${esc(r.title)}<div class="sub">${esc(bits)}</div>${r.quote&&r.quote.text?evQuote(r.quote):r.source?`<div class="evqsrc">Source: ${esc(r.source)}</div>`:""}</div>`; }
export function evDraw(){ const p=evEl(), root=evRoot(shared.EV.which), set=claimSet(shared.EV.which), c=set&&set[shared.EV.n];
  if(!c||!claimSpans(root,shared.EV.n).length){ evPanelClose(); return; }
  const st=claimState(c), ev=(shared.CURED&&shared.CURED.ev)||{}, order=claimOrder(root), i=order.indexOf(shared.EV.n);
  const block=claimSpans(root,shared.EV.n)[0].closest("p,li,blockquote"), inBlock=[...new Set([...block.querySelectorAll(".claim[data-c]")].filter(s=>s.closest("p,li,blockquote")===block).map(s=>s.dataset.c))];
  const good=inBlock.filter(k=>set[k]&&claimState(set[k])==="ok").length;
  const foot=good===inBlock.length?"Every claim in this paragraph has a source.":`${good} of ${plur(inBlock.length,"claim")} in this paragraph ${good===1?"has":"have"} a source.`;
  const waiting=order.filter(k=>set[k]&&claimState(set[k])==="none").length;
  const facts=c.ids.map(f=>{ const x=ev[f]; if(!x) return `<div class="evfact"><div class="evpart">${esc(f)}</div><div class="sub">Checking the source…</div></div>`;
    return `<div class="evfact"><div class="evpart">${esc(x.part)} · ${esc(f)}</div><div>${esc(x.text)}</div>${(x.rows||[]).map(evRowHtml).join("")}${(x.files||[]).map(q=>`<div class="evrow">${evQuote(q)||`<div class="evqsrc">${esc(String(q.path).split("/").pop())}</div>`}</div>`).join("")}</div>`; }).join("");
  const state=st==="none"?`<div class="evstate none" role="alert"><strong>No source found for this sentence.</strong> creaite couldn't tie it to the facts the draft was written from. Edit it, or keep it with a note.</div>
      <div class="evkeep"><input type="text" id="evNote" placeholder="Why it stays (optional)" aria-label="A note on why this sentence stays"><button type="button" class="btn" data-evkeep="one">Keep it</button>${waiting>1?`<button type="button" class="btn" data-evkeep="all">Keep all ${waiting}</button>`:""}</div>`
    : st==="kept"?`<div class="evstate">Kept without a source${c.kept?`: “${esc(c.kept)}”`:""}. <button type="button" class="mini" data-evkeep="undo">Undo</button></div>`
    : st==="edited"?`<div class="evstate">You edited this sentence, so its source mark is off until it is checked again. ${shared.EV.which==="ed"?'<button type="button" class="mini" data-chk="1">Check again</button>':""}</div>`
    : !c.how?`<div class="evstate sub">Checking the source…</div>`
    : c.how==="rechecked"?`<div class="evstate">Checked again after your edit: it matches ${plur(c.ids.length,"fact")} in the sheet.</div>`
    : `<div class="evstate">Rests on ${plur(c.ids.length,"fact")} from the facts sheet.</div>`;
  putHTML(p,html`<div class="evbar"><strong>Source</strong><span class="evint" title="Shown only here: never in a report, the saved text or a copy">Internal</span><span class="sp"></span><span class="sub" aria-live="polite">${raw(i+1)} of ${order.length}</span>${raw(ibtn("chevup","Previous claim",'data-evnav="-1"',"","⇧Tab"))}${raw(ibtn("chevdown","Next claim",'data-evnav="1"',"","Tab"))}${raw(ibtn("arrowright","Close",'data-evclose="1"',"","Esc"))}</div>
    <div class="evbody"><blockquote class="evsent">${claimText(root,shared.EV.n)}</blockquote>${raw(state)}${st==="edited"?"":raw(facts)}</div><div class="evfoot">${raw(foot)}</div>`);
  p.hidden=false;
  if(!shared.EV) return; { const set=claimSet(shared.EV.which), c=set&&set[shared.EV.n]; if(!c||!c.saved||c.edited) return;
    const body=$("#evPanel .evbody"); if(!body) return; const st=body.querySelector(".evstate"); body.querySelectorAll(".evfact").forEach(x=>x.remove());
    if(st&&claimState(c)==="ok") st.textContent=`Sourced when it was saved: ${plur((c.saved.facts||[]).length,"fact")} from the facts sheet.`;
    addHTML(body,"beforeend",raw(savedFactsHtml(c))); } }
export function evMove(d){ if(!shared.EV) return; const root=evRoot(shared.EV.which), order=claimOrder(root); if(!order.length) return; let i=order.indexOf(shared.EV.n)+d; i=(i+order.length)%order.length; const n=order[i];
  evPanelOpen(shared.EV.which,n); const sp=claimSpans(root,n)[0]; if(!sp) return; sp.scrollIntoView({block:"nearest"});
  if(shared.EV.which!=="ed") sp.focus({preventScroll:true}); else { const s=getSelection(), t=sp.firstChild||sp; try{ s.collapse(t,0); }catch(e){} } }
export function evKeep(mode){ if(!shared.EV) return; const set=claimSet(shared.EV.which); if(!set) return; const note=($("#evNote")||{}).value||"";
  if(mode==="undo"){ delete set[shared.EV.n].kept; }
  else (mode==="all"?Object.values(set).filter(c=>claimState(c)==="none"):[set[shared.EV.n]]).forEach(c=>{ c.kept=note.trim().slice(0,300); });
  claimPaint(shared.EV.which); evDraw(); if(mode!=="undo") snack(mode==="all"?"Kept without a source, with your note. Save when ready.":"Kept without a source. Save when ready."); }
export const evWhich=el=>el.closest("#genRewrite .rwbody")?"rw":el.closest("#curEd")?"ed":el.closest("#curText")?"rd":null;
export function rwWrap(){ const root=evRoot("rw"); if(!root||!shared.CURED||!shared.CURED.rewrite) return;
  if(!shared.CURED.rewrite.claims){ claimsInit("rw"); return; } claimsWrap(root); claimPaint("rw"); }
/* Save waits for every sentence creaite wrote without a source to be edited or kept (with a note); Alan's own edits never wait. */
/* BL-207, kept after Save (scrum master, 11-10-2026): the saved text stays plain Markdown; the sentence links go to
   system/staging/evidence/<code>-current.json (a sentence's hash to the facts and source IDs it rests on, rewritten on each
   save, through the live server). The read view and a reopened editor find the saved sentences by their hash; a sentence
   changed since has no link until Check sources re-checks it. */
shared.CURRD=null;   /* the read view's claims: {code, set:{n:{saved,how,kept}}, lost} */
export function claimHash(t){ t=String(t||"").replace(/\s+/g," ").trim().toLowerCase(); let a=0x811c9dc5, b=0x01000193^t.length;
  for(let i=0;i<t.length;i++){ const c=t.charCodeAt(i); a=Math.imul(a^c,0x01000193)>>>0; b=Math.imul(b^c,0x5bd1e995)>>>0; b^=b>>>13; }
  return (a>>>0).toString(16).padStart(8,"0")+(b>>>0).toString(16).padStart(8,"0"); }
/* Wrap the sentences of root whose hash is in ev (one sentence, or up to four in a row, as a claim was marked), from claim number n0. */
export function claimsMatch(root,ev,n0){ const found=[]; if(!root||!ev) return found; let n=n0||0; const ed=edOf(root), runs=[];   /* BL-301 A: in the editor, marks */
  for(const bl of root.querySelectorAll("p,li,blockquote")){ if(bl.closest("figure")) continue;
    const tw=document.createTreeWalker(bl,NodeFilter.SHOW_TEXT,{acceptNode:t=>t.parentElement.closest("p,li,blockquote,figure")===bl&&!t.parentElement.closest(".claim")?1:2});
    const /** @type {any[]} */ nodes=[]; while(tw.nextNode()) nodes.push(tw.currentNode); if(!nodes.length) continue;
    const full=nodes.map(t=>t.nodeValue).join(""), cuts=[0]; full.replace(/[.!?]["”’)]*\s+/g,(m,i)=>{ cuts.push(i+m.length); return m; }); cuts.push(full.length);
    const segs=[]; for(let i=0;i+1<cuts.length;i++) if(full.slice(cuts[i],cuts[i+1]).trim()) segs.push([cuts[i],cuts[i+1]]);
    const /** @type {[number, number, string][]} */ ranges=[]; for(let i=0;i<segs.length;){ let /** @type {[number, string]} */ hit=null; for(let j=Math.min(segs.length-1,i+3);j>=i;j--){ const h=claimHash(full.slice(segs[i][0],segs[j][1])); if(ev[h]){ hit=[j,h]; break; } }
      if(hit){ const s=segs[i][0]+full.slice(segs[i][0]).match(/^\s*/)[0].length, e=segs[hit[0]][1]-full.slice(0,segs[hit[0]][1]).match(/\s*$/)[0].length; ranges.push([s,e,hit[1]]); i=hit[0]+1; } else i++; }
    for(const [s,e,h] of ranges.reverse()){ n++; let pos=0; const /** @type {[any, number, number][]} */ mine=[];
      for(const t of nodes){ const a=pos, b=pos+t.nodeValue.length; pos=b; if(b<=s||a>=e) continue; mine.push([t,Math.max(s,a)-a,Math.min(e,b)-a]); }
      for(const [t,x,y] of mine){ if(ed){ runs.push([t,x,y,n]); continue; } let node=t; if(y<node.nodeValue.length) node.splitText(y); if(x>0) node=node.splitText(x);
        const sp=document.createElement("span"); sp.className="claim"; sp.dataset.c=n; node.parentNode.insertBefore(sp,node); sp.appendChild(node); }
      found.push({n,h}); } }
  if(ed) edClaim(root,runs);
  return found; }
export const evSaved=code=>(P.find(x=>x.code===code)||{}).ev||null;
export function readClaims(code){ shared.CURRD=null; const ev=evSaved(code), root=evRoot("rd"); if(!ev||!root) return; const set={}, hit=new Set();
  claimsMatch(root,ev).forEach(({n,h})=>{ const e=ev[h]; hit.add(h); set[n]={text:claimText(root,n),ids:[],how:(e.how==="none"||e.how==="kept")?"none":"saved",saved:e,...(e.kept!=null?{kept:e.kept}:{})}; });
  const lost=Object.keys(ev).filter(h=>!hit.has(h)&&(ev[h].facts||[]).length).length;
  shared.CURRD={code,set,lost}; claimPaint("rd");
  const card=$("#v-cockpit .curcard"); card?.querySelector(".evlost")?.remove();
  if(lost&&card) addHTML(card,"beforeend",html`<div class="evlost sub">${lost===1?"One sentence was":html`${raw(lost)} sentences were`} changed since ${lost===1?"it was":"they were"} sourced, so ${lost===1?"it has":"they have"} no source link until checked. <button type="button" class="mini" data-chksrc="${code}">Check sources</button></div>`); }
/* evRoot and claimSet learn the read view ("rd") */
/* the saved facts: rows from the page's own data, quotes from the live server when it is there */
export const SRCQ={};
export function savedFactsHtml(c){ return (c.saved.facts||[]).map((f,i)=>{ const key=claimHash(f.text+"|"+(f.src||[]).join(",")), got=SRCQ[key];
  if(!got&&viaServer()){ SRCQ[key]="…"; api("/api/current/sources",{src:f.src||[],text:f.text}).then(r=>{ SRCQ[key]=r.ok?r:{rows:null,files:[]}; evRefresh(); }); }
  const local=(f.src||[]).filter(s=>!s.startsWith("projects/")).map(id=>{ const k=/-A-\d{3}$/.test(id)?"actions":/-D-\d{3}$/.test(id)?"decisions":/-M-\d{3}$/.test(id)?"milestones":"raid", x=k==="milestones"?null:REC(k,id);
    return x?{id,kind:k,title:x.t,status:x.st,owner:x.o||x.by,due:x.due,closed:x.closed}:{id,kind:k,title:k==="milestones"?(((D.milestone_names||{})[id]||[])[0]||""):"",status:""}; });
  const rows=got&&got!=="…"&&got.rows?got.rows:local, files=got&&got!=="…"?got.files||[]:(f.src||[]).filter(s=>s.startsWith("projects/")).map(p=>({path:p,line:0,text:""}));
  return `<div class="evfact"><div class="evpart">${esc(f.part||"Fact")}</div><div>${esc(f.text)}</div>${rows.map(evRowHtml).join("")}${files.map(q=>`<div class="evrow">${evQuote(q)||`<div class="evqsrc">${esc(String(q.path).split("/").pop())}</div>`}</div>`).join("")}${!viaServer()&&(f.src||[]).length?'<div class="evqsrc">The quoted lines need the live server.</div>':""}</div>`; }).join(""); }
/* Check sources: every sentence in the editor without a link becomes a claim to re-check (plain code: the same dates, numbers
   and words as a fact), then the usual check runs. */
export function claimsAdopt(){ const root=$("#curEd"); if(!root||!shared.CURED) return 0; const set=shared.CURED.claims||(shared.CURED.claims={}); let n=Math.max(0,...Object.keys(set).map(Number)), added=0;
  const ed=edOf(root), runs=[], made=[];   /* BL-301 A: in the editor, marks */
  for(const bl of root.querySelectorAll("p,li,blockquote")){ if(bl.closest("figure")) continue;
    const tw=document.createTreeWalker(bl,NodeFilter.SHOW_TEXT,{acceptNode:t=>t.parentElement.closest("p,li,blockquote,figure")===bl&&!t.parentElement.closest(".claim")?1:2});
    const /** @type {any[]} */ nodes=[]; while(tw.nextNode()) nodes.push(tw.currentNode);
    for(const t of nodes){ const txt=t.nodeValue; if((txt.match(/[A-Za-z]{2,}/g)||[]).length<3) continue;
      const lead=txt.match(/^\s*/)[0].length, tail=txt.match(/\s*$/)[0].length; n++; added++; made.push(n);
      if(ed){ runs.push([t,lead,txt.length-tail,n]); continue; }
      let node=t; if(tail) node.splitText(txt.length-tail); if(lead) node=node.splitText(lead);
      // @ts-expect-error TS2322: dataset stores the claim's number as a string
      const sp=document.createElement("span"); sp.className="claim"; sp.dataset.c=n; node.parentNode.insertBefore(sp,node); sp.appendChild(node); } }
  if(ed) edClaim(root,runs);
  made.forEach(k=>{ set[k]={text:claimText(root,k),ids:[],how:"",edited:true,touched:true}; });
  claimPaint("ed"); return added; }
export async function checkSources(code){ if(!viaServer()){ snack("Check sources needs the live server"); return; }
  if(!shared.CURED){ startCurEdit(code); if(!shared.CURED) return; }
  Object.values(shared.CURED.claims||{}).forEach(c=>{ if(c.how==="saved"){ c.edited=true; c.saved=null; c.how=""; } });   /* re-find them all against today's facts */
  claimsAdopt(); claimPaint("ed"); await curCheck(); snack("Sources checked. A sentence creaite couldn't place is marked."); }
/* the read view draws its claims after each render */
/* on Save: the links of the sentences still sourced go to the evidence file */
export function evidencePayload(){ const root=$("#curEd"), set=shared.CURED&&shared.CURED.claims; if(!root||!set) return null; const ev=shared.CURED.ev||{}, out={};
  for(const n of claimOrder(root)){ const c=set[n]; if(!c||c.edited) continue; const text=claimText(root,n); if(!text) continue; const st=claimState(c);
    if(c.saved){ out[claimHash(text)]={...c.saved,...(c.kept!=null?{kept:c.kept,how:"kept"}:{})}; continue; }
    const facts=(c.ids||[]).map(f=>ev[f]).filter(Boolean).map(x=>({text:x.text,part:x.part,src:[...(x.rows||[]).map(r=>r.id),...(x.files||[]).map(q=>q.path)]}));
    if(facts.length) out[claimHash(text)]={facts,how:c.how==="rechecked"?"rechecked":"marked"}; else if(st==="kept") out[claimHash(text)]={facts:[],how:"kept",kept:c.kept||""}; }
  return out; }
/* ===== end BL-207 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootProjects0059(){
document.addEventListener("click",e=>{ const p=e.target.closest("#evPanel");
  if(p){ const nav=e.target.closest("[data-evnav]"); if(nav){ evMove(+nav.dataset.evnav); return; } if(e.target.closest("[data-evclose]")){ evPanelClose(); return; }
    const k=e.target.closest("[data-evkeep]"); if(k){ evKeep(k.dataset.evkeep); return; } return; }
  const sp=e.target.closest&&e.target.closest(".claim[data-c]"); if(!sp) return; const w=evWhich(sp); if(w) evPanelOpen(w,sp.dataset.c); });
document.addEventListener("focusin",e=>{ const sp=e.target.closest&&e.target.closest(".rwbody .claim[data-c],#curText .claim[data-c]"); if(sp&&!(shared.EV&&shared.EV.which===evWhich(sp)&&shared.EV.n===+sp.dataset.c)) evPanelOpen(evWhich(sp),sp.dataset.c); });
document.addEventListener("selectionchange",()=>{ if(!shared.EV||shared.EV.which!=="ed") return; const s=getSelection(); if(!s||!s.rangeCount) return; const n=s.anchorNode, el=n&&(n.nodeType===1?n:n.parentElement);
  const sp=el&&el.closest&&el.closest("#curEd .claim[data-c]"); if(sp&&+sp.dataset.c!==shared.EV.n) evPanelOpen("ed",sp.dataset.c); });
document.addEventListener("mouseover",e=>{ const sp=e.target.closest&&e.target.closest(".claim[data-c]"), root=sp&&sp.closest("#curEd,.rwbody,#curText");
  $$(".claim.hov").forEach(s=>{ if(!sp||s.dataset.c!==sp.dataset.c||!root.contains(s)) s.classList.remove("hov"); });
  if(sp&&root) claimSpans(root,sp.dataset.c).forEach(s=>s.classList.add("hov")); });
document.addEventListener("keydown",e=>{ if(!shared.EV||e.isComposing) return; const p=$("#evPanel"), root=evRoot(shared.EV.which);
  const inside=(p&&p.contains(e.target))||(root&&root.contains(e.target))||(shared.EV.which==="ed"&&e.target.id==="curEd");
  if(slashOn(e.target)&&(e.key==="Escape"||e.key==="Tab")) return;   /* #122 B: the / menu is open */
  if(e.key==="Escape"&&(inside||!document.querySelector("dialog[open]"))){ e.preventDefault(); e.stopImmediatePropagation(); evPanelClose(); return; }
  if(e.key==="Tab"&&inside&&!(e.target.id==="evNote")&&!e.metaKey&&!e.ctrlKey&&!e.altKey){ e.preventDefault(); e.stopImmediatePropagation(); evMove(e.shiftKey?-1:1); } },true);
document.addEventListener("input",e=>{ if(e.target.closest&&e.target.closest("#curEd")){ claimTrack(); if(shared.CURED&&shared.CURED.claims) claimPaint("ed"); } });   /* BL-301 A: a redrawn sentence is painted again */
setInterval(()=>{ if(shared.EV&&!(evRoot(shared.EV.which)||{}).isConnected) evPanelClose(); },800);
document.addEventListener("click",e=>{ const b=e.target.closest("[data-chksrc]"); if(!b) return; e.preventDefault(); checkSources(b.dataset.chksrc||(shared.CURED&&shared.CURED.code)); });
}
/* ===== Dashboard pages (BL-87 to BL-95) ===== */
/* BL-88: the ask creaite button beside the search bar. Dimmed with no text; available with text; highlighted, with a
   small ↵, when the text reads like a question (Enter then asks); "Answering…" with Stop while an answer is written. */
export function vsAskSync(){ const q=$("#vsInput").value.trim(), a=shared.ASKQ&&shared.ASKQ.run&&!shared.ASKQ.done, btn=$("#vsAskBtn");
  const st=a?"answering":!q?"idle":questionLike(q)?"question":"ready"; btn.dataset.state=st; btn.setAttribute("aria-disabled",st==="idle"||st==="answering"?"true":"false");
  btn.querySelector(".asklab").textContent=a?"Answering…":"ask creaite"; $("#vsAskStop").hidden=!a; $("#vsHint").hidden=!!q; }
/* BL-90 part 1: dependencies, with no schema change. A RAID item of type Dependency whose milestone is set means "this milestone
   depends on it". Added here: the date warning (an early warning, signal "dependency", built in build_dashboard), a Dependencies
   card on the project page, an at-risk mark on a blocked milestone, a suggested milestone as one-click chips in the item's panel
   (never attached by itself; "None needed" is remembered until the text changes), and Work's "Unattached dependencies". */
export const depWarn=d=>WARNS().find(w=>w.k==="raid"&&w.id===d.id&&w.sig==="dependency");
export const msInfo=id=>{ const m=(D.milestone_names||{})[id]; return m?{name:m[0],date:m[2]}:{name:id,date:""}; };
export function depsCard(code){ const L=R.filter(r=>r.p===code&&r.type==="Dependency"&&r.st==="Open"); if(!L.length) return "";
  const by={}; L.forEach(d=>(by[d.ms||""]=by[d.ms||""]||[]).push(d));
  const groups=Object.keys(by).sort((a,b)=>!a?1:!b?-1:(msInfo(a).date||"9").localeCompare(msInfo(b).date||"9")), risk=L.filter(depWarn).length;
  const row=d=>{ const w=depWarn(d); return `<div class="deprow" data-open="raid:${d.id}" style="cursor:pointer"><span class="sub depid">${esc(d.id)}</span>${ico("Dependency")}<span class="dept">${esc(d.t)}</span><span class="sub">— ${esc(who(d.o))} · <span class="${d.due&&d.due<TODAY?"late":""}">${d.due?"due "+fd(d.due):"no due date"}</span></span>${w?`<div class="depwarn">${WICO.replace("<svg",'<svg width="13" height="13" style="flex:none;margin-top:2px"')}<span>${esc(w.text)}</span></div>`:""}</div>`; };
  return `<div class="card" id="depCard"><h2>Dependencies <span class="sub">· ${countLink(`${plur(L.length,"open dependency")} in ${pName(code)}`.replace("dependencys","dependencies"),L.length,`raid:open:${code}`,{st:["Open"],ty:["Dependency"]})}${risk?` · ${risk} at risk`:""}</span></h2>${groups.map(g=>`<div class="depg" data-g="${esc(g)}"><div class="depgh">${g?`${ico("milestone")}<a href="#" class="hlink" data-ms="${g}">${esc(msInfo(g).name)}</a> <span class="sub">${msInfo(g).date?"forecast "+fd(msInfo(g).date):""}</span>`:'Not attached <span class="tag">attach one to a milestone in its panel</span>'}</div>${by[g].map(row).join("")}</div>`).join("")}</div>`; }
export const depHash=t=>[...String(t||"")].reduce((a,c)=>(a*31+c.charCodeAt(0))|0,7);
export function depSuggest(code,due){ const p=P.find(x=>x.code===code); if(!p||!due) return [];
  return p.ms.filter(m=>m[3]&&m[6]==="Planned"&&(m[8]||m[4])&&(m[8]||m[4])>due).sort((a,b)=>(a[8]||a[4]).localeCompare(b[8]||b[4])).slice(0,3); }
/* BL-316: the suggestions are Chip building blocks (class chipbtn) in a group (#depSug), for the form here and the peek (pkDepDraw) */
export function depSugDraw(parent,L,attr){ const g=document.createElement("div"); g.id="depSug"; g.className="depchips"; g.setAttribute("role","group"); g.setAttribute("aria-label","Suggested milestones"); parent.append(g);
  drawChips(g,[...L.map(m=>({key:m[3],button:true,cls:"chipbtn",[`data-${attr}`]:m[3],children:`Attach to ${m[3]} (forecast ${fd(m[8]||m[4])})?`})),{key:"none",button:true,cls:"chipbtn quiet",[`data-${attr}none`]:"",children:"None needed"}]); }
export function depFormDraw(){ $("#depSug")?.remove(); if(!shared.EDITING||!shared.CUR||shared.CUR.k!=="raid"||!["record","new"].includes(shared.CUR.mode)) return;
  const typ=$("#f_type"), ms=$("#f_ms"); if(!typ||!ms||typ.value!=="Dependency"||ms.value) return;
  const code=$("#f_p")?.value||formProject(), dueTxt=$("#f_due")?.value||"", due=DDATE.test(dueTxt)?toIso(dueTxt):"", key=shared.CUR.id||"new";
  if((store.obj("creaite-dep-none")[key])===depHash($("#f_t")?.value)) return;
  const L=depSuggest(code,due); if(!L.length) return;
  depSugDraw(ms.closest("dd"),L,"depms"); }
/* BL-91: the Flow card, in inline SVG drawn to scale (a bar's height is its count times one scale per chart), in the theme's own
   colours: accent for opened, amber for closed, red for overdue and the oldest bucket. Every bar carries its number, and each
   chart a title, so colour is never the only signal. Counts only, never about a person. Data: D.flow[code] (build_dashboard.flow_data). */
export const FL={W:360,H:150,L:30,R:8,T:22,B:30};
export const flDay=iso=>{ const x=new Date(iso+"T00:00:00"), p=n=>String(n).padStart(2,"0"); x.setDate(x.getDate()+4-((x.getDay()+6)%7)); return `${x.getFullYear()}-${p(x.getMonth()+1)}-${p(x.getDate())}`; };   /* the week's Friday */
export let FLN=0;   /* closed bars are hatched as well as coloured, so opened and closed differ without relying on colour */
export function flBars(weeks,series,title,aria){ let LINKED=false; const pid="flh"+(FLN++), {W,H,L,R,T,B}=FL, pw=W-L-R, ph=H-T-B, n=weeks.length, gw=pw/n, bw=Math.min(18,gw*0.38), max=Math.max(1,...weeks.flatMap(w=>series.map(s=>w[s[0]]))), k=ph/max;
  let g=`<defs><pattern id="${pid}" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect class="fl-hp" width="1.6" height="4"/></pattern></defs><line class="fl-ax" x1="${L}" y1="${T+ph}" x2="${W-R}" y2="${T+ph}"/><text class="fl-m" x="${L-4}" y="${T+4}" text-anchor="end">${max}</text><text class="fl-m" x="${L-4}" y="${T+ph}" text-anchor="end">0</text>`;
  weeks.forEach((w,i)=>{ const cx=L+gw*i+gw/2, x0=cx-bw*series.length/2;
    series.forEach((s,j)=>{ const v=w[s[0]], h=v*k, ln=v&&s[4]?s[4](w,v):null; if(ln){ LINKED=true; g+=flkOpen(ln); }   /* BL-190: a bar that Work can list is a link */
      g+=`<rect class="${s[1]}" data-v="${v}" data-wk="${w.end}" x="${(x0+bw*j).toFixed(1)}" y="${(T+ph-h).toFixed(2)}" width="${(bw-1).toFixed(1)}" height="${h.toFixed(2)}"><title>Week of ${fd(w.start)}: ${v} ${s[2]}</title></rect>${s[3]&&v>0?`<rect class="fl-hatch" x="${(x0+bw*j).toFixed(1)}" y="${(T+ph-h).toFixed(2)}" width="${(bw-1).toFixed(1)}" height="${h.toFixed(2)}" fill="url(#${pid})" pointer-events="none"/>`:""}`;
      if(v>0) g+=`<text class="fl-t" x="${(x0+bw*j+(bw-1)/2).toFixed(1)}" y="${(T+ph-h-3).toFixed(1)}" text-anchor="middle">${v}</text>`; if(ln) g+="</g>"; });
    g+=`<text class="fl-m" x="${cx.toFixed(1)}" y="${T+ph+12}" text-anchor="middle">${fd(flDay(w.start)).slice(0,5)}</text>`; });
  const key=series.map((s,j)=>`<rect class="${s[1]}" x="${L+j*118}" y="3" width="9" height="9"/>${s[3]?`<rect class="fl-hatch" x="${L+j*118}" y="3" width="9" height="9" fill="url(#${pid})"/>`:""}<text class="fl-t" x="${L+j*118+13}" y="11">${s[2]}</text>`).join("");
  return `<figure class="flc"><figcaption>${title}</figcaption><svg viewBox="0 0 ${W} ${H}" role="${LINKED?"group":"img"}" aria-label="${esc(aria)}">${key}${g}</svg></figure>`; }
export function flHBars(rows,title,aria,cls){ const W=FL.W, lw=96, rh=26, H=rows.length*rh+8, max=Math.max(1,...rows.map(r=>r[1])), k=(W-lw-40)/max;
  const ln=rows.map(r=>r[1]&&r[2]?r[2]:null);   /* BL-190: a bucket that Work can list is a link (its words, bar and figure) */
  const g=rows.map((r,i)=>{ const y=4+i*rh, w=r[1]*k; return `${ln[i]?flkOpen(ln[i]):""}<text class="fl-t" x="0" y="${y+14}">${esc(r[0])}</text><rect class="${cls[i]}" data-v="${r[1]}" x="${lw}" y="${y+3}" width="${w.toFixed(2)}" height="16"><title>${esc(r[0])}: ${r[1]}</title></rect><text class="fl-t" x="${(lw+w+5).toFixed(1)}" y="${y+15}">${r[1]}</text>${ln[i]?"</g>":""}`; }).join("");
  return `<figure class="flc"><figcaption>${title}</figcaption><svg viewBox="0 0 ${W} ${H}" role="${ln.some(Boolean)?"group":"img"}" aria-label="${esc(aria)}">${g}</svg></figure>`; }
export function flMix(mix,title,link){ const W=FL.W, tot=Object.values(mix).reduce((a,b)=>a+b,0), cls={Urgent:"fl-pU",High:"fl-pH",Medium:"fl-pM",Low:"fl-pL"}, bw=W-8; let x=4;
  const segs=tot?Object.entries(mix).filter(([,v])=>v).map(([p,v])=>{ const w=v/tot*bw, ln=link?link(p,v):null, r=`${ln?flkOpen(ln):""}<rect class="${cls[p]}" data-v="${v}" x="${x.toFixed(1)}" y="6" width="${w.toFixed(2)}" height="22"><title>${p}: ${v}</title></rect>${w>=16?`<text class="fl-t fl-on" x="${(x+w/2).toFixed(1)}" y="21" text-anchor="middle">${v}</text>`:""}${ln?"</g>":""}`; x+=w; return r; }).join(""):`<text class="fl-m" x="4" y="22">No open risks or issues</text>`;   /* BL-190: each segment is a link */
  const key=Object.entries(mix).map(([p,v],i)=>`<rect class="${cls[p]}" x="${4+i*88}" y="38" width="9" height="9"/><text class="fl-t" x="${4+i*88+13}" y="46">${p} ${v}</text>`).join("");
  return `<figure class="flc"><figcaption>${title}</figcaption><svg viewBox="0 0 ${W} 54" role="${tot&&link?"group":"img"}" aria-label="Open risks and issues by priority: ${Object.entries(mix).map(([p,v])=>p+" "+v).join(", ")}">${segs}${key}</svg></figure>`; }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootProjects0081(){
$("#vsInput").addEventListener("input",vsAskSync);
$("#vsInput").addEventListener("keydown",e=>{ if(e.key==="Enter"&&!questionLike($("#vsInput").value.trim())&&$("#vsInput").value.trim()){ e.preventDefault(); clearTimeout(SRCH.timer); runSearch(); } });
$("#vsAskBtn").addEventListener("click",()=>{ const st=$("#vsAskBtn").dataset.state; if(st==="idle"){ $("#vsInput").focus(); return; } if(st==="answering") return; askClaude(); });
$("#vsAskStop").addEventListener("click",()=>{ if(shared.ASKQ.run) api("/api/ask/stop",{run:shared.ASKQ.run}).then(r=>{ if(!r.ok&&shared.ASKQ.ctl) shared.ASKQ.ctl.abort(); }); });
vsAskSync();
$("#pFields").addEventListener("input",e=>{ if(["f_due","f_type","f_p","f_t"].includes(e.target.id)) depFormDraw(); });
$("#pFields").addEventListener("change",e=>{ if(["f_due","f_type","f_p","f_ms"].includes(e.target.id)) depFormDraw(); });
$("#pFields").addEventListener("click",e=>{ const a=e.target.closest("[data-depms]"), n=e.target.closest("[data-depnone]"); if(a){ const ms=$("#f_ms"); ms.value=a.dataset.depms; ms.dispatchEvent(new Event("change",{bubbles:true})); depFormDraw(); }
  else if(n){ const d=store.obj("creaite-dep-none"); d[shared.CUR.id||"new"]=depHash($("#f_t")?.value); store.set("creaite-dep-none",d); depFormDraw(); } });
}
/* ===== BL-190 (sprint-links) ===== the Flow card's figures open Work: a week's opened bars (Raised between that week, any status),
   its closed bars (Closed, Closed between that week), an ageing bucket (All items, open actions and RAID items raised in that span)
   and a priority segment (open risks and issues of that priority). Each is linked only when the page's own data gives the same
   count as the chart (the chart is worked out when the page is built), so the number always equals the rows Work lists. The
   overdue-by-week bars stay plain: they are rebuilt from the history of due dates, which no Work filter can reproduce. */
export const flkOpen=ln=>`<g class="flk" role="link" tabindex="0" data-nav="${esc(ln.nav)}" data-n="${ln.n}" aria-label="${esc(ln.label)}, open in Work">`;
export const inSpan=(day,from,to)=>!!day&&(!from||day.slice(0,10)>=from)&&(!to||day.slice(0,10)<=to);
export function flLinks(code){ const nm=pName(code), RI=["Risk","Issue"], wk=w=>`in the week of ${fd(w.start)}`;
  const guard=(n,v,ln)=>n===v?{...ln,n:v}:null;
  return {
    aOpen:(w,v)=>guard(A.filter(x=>x.p===code&&inSpan(x.raised,w.start,w.end)).length,v,{nav:navOf(`actions:open:${code}`,{st:[],rr:[w.start,w.end]}),label:`${plur(v,"action")} opened in ${nm} ${wk(w)}`}),
    aClose:(w,v)=>guard(A.filter(x=>x.p===code&&x.st==="Closed"&&inSpan(x.closed,w.start,w.end)).length,v,{nav:navOf(`actions:closed:${code}`,{st:["Closed"],cr:[w.start,w.end]}),label:`${plur(v,"action")} closed in ${nm} ${wk(w)}`}),
    rOpen:(w,v)=>guard(R.filter(x=>x.p===code&&RI.includes(x.type)&&inSpan(x.raised,w.start,w.end)).length,v,{nav:navOf(`raid:open:${code}`,{st:[],ty:RI,rr:[w.start,w.end]}),label:`${v} risk${v===1?" or issue":"s and issues"} opened in ${nm} ${wk(w)}`}),
    rClose:(w,v)=>guard(R.filter(x=>x.p===code&&RI.includes(x.type)&&x.st==="Closed"&&inSpan(x.closed,w.start,w.end)).length,v,{nav:navOf(`raid:closed:${code}`,{st:["Closed"],ty:RI,cr:[w.start,w.end]}),label:`${v} risk${v===1?" or issue":"s and issues"} closed in ${nm} ${wk(w)}`}),
    age:(lab,v)=>{ const m=/^(\d+) to (\d+) days$/.exec(lab), o=/^Over (\d+) days$/.exec(lab); if(!m&&!o) return null;
      const from=m?isoAdd(TODAY,-m[2]):"", to=isoAdd(TODAY,-(m?+m[1]:+o[1]+1));
      return guard([...A,...R].filter(x=>x.p===code&&open(x)&&x.raised&&inSpan(x.raised,from,to)).length,v,{nav:navOf(`all:open:${code}`,{st:["Open"],ty:["Action","Risk","Issue","Assumption","Dependency"],rr:[from,to]}),label:`${plur(v,"open item")} in ${nm} open ${lab.toLowerCase()}`}); },
    mix:(p,v)=>guard(R.filter(x=>x.p===code&&x.st==="Open"&&RI.includes(x.type)&&x.pr===p).length,v,{nav:navOf(`raid:open:${code}`,{st:["Open"],ty:RI,pr:[p]}),label:`${v} open ${p} risk${v===1?" or issue":"s and issues"} in ${nm}`}) }; }
/* ===== end BL-190 (Flow) ===== */
export function flowCard(code){ const f=(D.flow||{})[code]; if(!f) return ""; const w=f.weeks, a=f.ageing, rk=f.risks, ms=f.milestones, od=f.overdue, L=flLinks(code);   /* BL-190: L */
  const dir=od.now<od.last_week?"down":od.now>od.last_week?"up":"level";
  return `<div class="card flowcard" id="flowCard"><h2>Flow <span class="sub">· last ${f.period} weeks · counts only</span></h2><p class="flsum" id="flowSummary">This week: ${esc(f.summary)}.</p>
   <div class="flgrid">${flBars(w,[["a_opened","fl-op","opened",false,L.aOpen],["a_closed","fl-cl","closed",true,L.aClose]],"Actions opened and closed, by week",`Actions opened and closed in each of the last ${f.period} weeks`)}
    ${flBars(w,[["r_opened","fl-op","opened",false,L.rOpen],["r_closed","fl-cl","closed",true,L.rClose]],"Risks and issues opened and closed, by week",`Risks and issues opened and closed in each of the last ${f.period} weeks`)}
    ${flBars(w,[["overdue","fl-od","overdue"]],`Overdue at the end of each week: ${od.now} now, ${dir==="level"?"level with":dir==="down"?"down from":"up from"} ${od.last_week} last week`,`Overdue items at the end of each of the last ${f.period} weeks`)}
    ${flHBars(a.labels.map((l,i)=>[l,a.buckets[i],a.buckets[i]?L.age(l,a.buckets[i]):null]),`How long the ${a.open} open item${a.open===1?" has":"s have"} been open`,`Open items by how long they have been open: ${a.labels.map((l,i)=>l+" "+a.buckets[i]).join(", ")}`,["fl-a0","fl-a1","fl-a2","fl-a3"])}
    ${flMix(rk.mix,"Open risks and issues by priority",L.mix)}</div>
   <div class="flfoot"><div><b>Oldest open</b>${a.oldest.length?a.oldest.map(o=>`<div class="mini-list"><div data-open="${o.k}:${o.id}" style="cursor:pointer">${ico(o.k==="actions"?"action":"Risk")}<span class="sub">${esc(o.id)}</span> ${esc(o.t)} <span class="sub">— ${o.days} day${o.days===1?"":"s"}</span></div></div>`).join(""):'<div class="sub">Nothing open.</div>'}</div>
    <div><b>Risks and issues</b><div class="sub">${rk.opened} opened, ${rk.closed} closed${rk.cancelled?`, ${rk.cancelled} cancelled`:""} in ${f.period} weeks</div><b style="margin-top:8px;display:block">Milestone movement</b>${ms.moves?`<div class="sub">${ms.moves} forecast move${ms.moves===1?"":"s"} in ${f.period} weeks, ${Math.abs(ms.days)} day${Math.abs(ms.days)===1?"":"s"} ${ms.days>=0?"later":"earlier"} in all</div>`+ms.by.map(m=>`<div class="sub">${esc(m.name)}: ${m.moves} move${m.moves===1?"":"s"}, ${Math.abs(m.days)} day${Math.abs(m.days)===1?"":"s"} ${m.days>=0?"later":"earlier"}</div>`).join(""):'<div class="sub">No forecast has moved.</div>'}</div></div></div>`; }
/* BL-95: open work with no due date always shows on the project page, to push for a date. Every open or delayed action, and every
   open risk or issue (an assumption or a dependency only if it has a response action to date); never a decision, closed or
   cancelled item. Raised within dashboard.undated_grace_days (3) shows dimmer, marked new. Mirrors build_dashboard.undated_counts. */
export const undatedWork=code=>[...A.filter(x=>x.p===code&&open(x)&&!x.due).map(x=>["actions",x]),...R.filter(r=>r.p===code&&r.st==="Open"&&!r.due&&(r.type==="Risk"||r.type==="Issue"||r.resp)).map(r=>["raid",r])];
export const isNewUndated=x=>!!x.raised&&-days(x.raised)<=(S.undatedGrace??3);
export function undatedCard(code){ const L=undatedWork(code); if(!L.length) return "";
  const na=L.filter(([k])=>k==="actions").length, nr=L.length-na, pri=x=>PRIOS.indexOf(x.pr)<0?9:PRIOS.indexOf(x.pr);
  // @ts-expect-error TS2362: true and false subtract as 1 and 0 (undated new items sort first)
  L.sort((a,b)=>(isNewUndated(a[1])-isNewUndated(b[1]))||(pri(a[1])-pri(b[1]))||a[1].id.localeCompare(b[1].id));
  return `<div class="card" id="undatedCard"><h2>No due date <span class="sub">· ${L.length}</span></h2>
    <div class="mini-list">${L.map(([k,x])=>`<div class="undrow${isNewUndated(x)?" dim":""}" data-open="${k}:${x.id}" style="cursor:pointer"><span class="sub undid">${esc(x.id)}</span>${ico(k==="actions"?"action":kindOf("raid",x))}<span class="undt">${esc(x.t)}${isNewUndated(x)?' <span class="tag">new</span>':""}</span><span class="sub">— ${esc(who(x.o))}${x.pr?" · "+esc(x.pr):""}</span><span class="dwrap undset"><input type="text" id="und-${esc(x.id)}" data-pick="1" data-date="1" data-und="${k}:${x.id}" placeholder="Set date" autocomplete="off" aria-label="Set the due date of ${esc(x.id)}" title="Set the due date of ${esc(x.id)} here: type DD-MM-YYYY or choose from the calendar"><button type="button" class="dbtn" data-cal="und-${esc(x.id)}" aria-label="Choose the due date of ${esc(x.id)}">${CALI}</button></span></div>`).join("")}</div>
    ${na?seeAll(na,`${pName(code)} undated action`,"actions:undated:"+code)+" ":""}${nr?seeAll(nr,`${pName(code)} undated RAID item`,"raid:undated:"+code):""}</div>`; }
/* the evidence row's "No due date" figure counts actions and RAID items together, so it can't open one Work list: it shows the card, whose two
   "All n … without a date" links open each list with exactly that many */
/* The date is set on the row, as a Work cell is (BL-123): picking from the calendar, or typing it and pressing Enter or leaving the field, saves it
   through the same checks (`boardMove`: one proposal, Undo in the message) and the item leaves this card. No side panel. */
export async function undCommit(inp,picked){   /* picked: the working day chosen instead of a weekend, so it isn't asked about again */
  if(!picked){ const v=inp.value.trim(), t=DDATE.test(v)?toIso(v):""; if(t&&!WK.ok&&!inp.dataset.busy&&wkAsk(t,inp,d=>{ inp.value=fd(d); return undCommit(inp,true); })) return; }
  if(inp.dataset.busy) return; const v=inp.value.trim(); if(v==="") return;
  const t=DDATE.test(v)?toIso(v):"", d=t?new Date(t+"T12:00:00"):null;
  if(!d||isNaN(d)||d.toISOString().slice(0,10)!==t){ snack(DDATE.test(v)?"That isn't a real date.":"Not a date creaite knows. "+DATE_HELP); return; }
  const [k,id]=inp.dataset.und.split(":"); inp.dataset.busy="1"; try{ await boardMove(k,id,{due:t}); } finally{ delete inp.dataset.busy; } }
   /* the calendar fires a plain input event; typing fires an InputEvent */
/* BL-89: Current state in two resizable panes. One message: the left pane then the right, stored in the one section with the
   pane marker between them (a text without it is the left pane). The divider's position is a view setting of this browser,
   shared across projects (default 62%, never under 25% for either pane); double-click resets it; a button folds the right pane
   into a thin strip (it stays part of the message, and the strip shows when it holds text). Under 760px the panes stack. */
export const SPLIT0=62, SPLITMIN=25;
export const paneSplit=()=>Math.min(100-SPLITMIN,Math.max(SPLITMIN,+store.get("creaite-cur-split",SPLIT0)||SPLIT0));
export function curPanes(left,right,mode,hasRight){ const solo=/\bsolo\b/.test(mode), c=!solo&&!!store.get("creaite-cur-collapsed",false), sp=paneSplit();
  /* ===== BL-117 (sprint-polish) ===== nothing on the right: the same frame, the right column empty (no divider, fold button or dot), so the text keeps its width */
  if(solo) return `<div class="curpanes ${mode}" style="--split:${sp}"><div class="curpane" data-pane="1">${left}</div><span class="curgap" aria-hidden="true"></span><div class="curpane" data-pane="2" aria-hidden="true"></div></div>`;
  return `<div class="curpanes ${mode}${c?" collapsed":""}" style="--split:${sp}"><div class="curpane" data-pane="1">${left}</div>
    <div class="curdiv" role="separator" aria-orientation="vertical" tabindex="0" aria-label="Resize the two panes" aria-valuemin="${SPLITMIN}" aria-valuemax="${100-SPLITMIN}" aria-valuenow="${Math.round(sp)}"><button type="button" class="curcollapse" aria-expanded="${!c}" aria-label="${c?"Show the right pane":"Fold the right pane"}" title="${c?"Show the right pane":"Fold the right pane"}">${c?"‹":"›"}</button></div>
    <div class="curpane" data-pane="2">${right}<span class="curdot${hasRight?" has":""}" title="This pane holds text" aria-label="The right pane holds text">●</span></div></div>`; }
export function curReadHtml(p){ const [l,r]=splitPanes(p.current||""), L=mdHtml(l,p.images), R=mdHtml(r,p.images);
  if(!r) return curPanes(`<div class="curin">${L||'<p class="sub">No current state yet.</p>'}</div>`,"","read solo",false);     /* BL-116, BL-117 (sprint-polish) */
  return curPanes(`<div class="curin">${L}</div>`,`<div class="curin">${R}</div>`,"read",true); }
export const paneOf=n=>n&&(n.nodeType===1?n:n.parentNode)&&(n.nodeType===1?n:n.parentNode).closest?(n.nodeType===1?n:n.parentNode).closest(".curpanes .rted"):null;
export function curPane(at){ const a=paneOf(at); if(a) return a; const sel=getSelection(), b=sel&&sel.rangeCount?paneOf(sel.anchorNode):null; if(b) return b; return $(shared.CURED&&shared.CURED.last===2?"#curEd2":"#curEd"); }
export const paneBlank=ed=>ed.classList.toggle("blank",!ed.textContent.trim()&&!ed.querySelector("figure"));
export function setSplit(box,pct,keep){ pct=Math.round(Math.min(100-SPLITMIN,Math.max(SPLITMIN,pct))*10)/10; box.style.setProperty("--split",pct); const d=box.querySelector(".curdiv"); if(d) d.setAttribute("aria-valuenow",Math.round(pct)); if(keep) store.set("creaite-cur-split",pct); return pct; }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootProjects0083(){
document.addEventListener("click",e=>{ if(e.target.closest("[data-undated]")){ e.preventDefault(); mScroll(document.getElementById("undatedCard"),{block:"center"}); } });
document.addEventListener("keydown",e=>{ if(e.key==="Enter"&&e.target.matches&&e.target.matches("[data-undated]")) e.target.click(); });
document.addEventListener("input",e=>{ if(e.target.matches&&e.target.matches("input[data-und]")&&!(e instanceof InputEvent)) undCommit(e.target); });
document.addEventListener("change",e=>{ if(e.target.matches&&e.target.matches("input[data-und]")) undCommit(e.target); });
document.addEventListener("keydown",e=>{ if(e.key==="Enter"&&e.target.matches&&e.target.matches("input[data-und]")){ e.preventDefault(); e.stopPropagation(); undCommit(e.target); } },true);
$("#v-cockpit").addEventListener("pointerdown",e=>{ const dv=e.target.closest(".curdiv"); if(!dv||e.target.closest(".curcollapse")) return; const box=dv.closest(".curpanes"); if(box.classList.contains("collapsed")) return;
  e.preventDefault(); dv.setPointerCapture(e.pointerId); box.classList.add("dragging"); let pct=paneSplit();
  const mv=ev=>{ const r=box.getBoundingClientRect(); pct=setSplit(box,(ev.clientX-r.left)/r.width*100,false); };
  const up=()=>{ dv.removeEventListener("pointermove",mv); dv.removeEventListener("pointerup",up); box.classList.remove("dragging"); store.set("creaite-cur-split",pct); };
  dv.addEventListener("pointermove",mv); dv.addEventListener("pointerup",up); });
$("#v-cockpit").addEventListener("dblclick",e=>{ const dv=e.target.closest(".curdiv"); if(dv&&!e.target.closest(".curcollapse")){ store.set("creaite-cur-split",SPLIT0); setSplit(dv.closest(".curpanes"),SPLIT0,false); } });
$("#v-cockpit").addEventListener("keydown",e=>{ const dv=e.target.closest&&e.target.closest(".curdiv"); if(!dv||e.target.closest(".curcollapse")) return; const box=dv.closest(".curpanes"), now=+dv.getAttribute("aria-valuenow");
  const to=e.key==="ArrowLeft"?now-2:e.key==="ArrowRight"?now+2:e.key==="Home"?SPLITMIN:e.key==="End"?100-SPLITMIN:null; if(to===null) return; e.preventDefault(); setSplit(box,to,true); });
$("#v-cockpit").addEventListener("click",e=>{ const b=e.target.closest(".curcollapse"); if(!b) return; const box=b.closest(".curpanes"), c=box.classList.toggle("collapsed"); store.set("creaite-cur-collapsed",c);
  b.setAttribute("aria-expanded",!c); b.textContent=c?"‹":"›"; b.title=b.ariaLabel=c?"Show the right pane":"Fold the right pane"; });
}
/* ===== Insight (BL-51, BL-49, BL-54) ===== */
/* The views below are extended by wrapping their render functions, so the lines above stay as they were.
   BL-51 early warnings: worked out at build time (build_dashboard.py early_warnings), never stored. Shown as a flag
   on the item (reasons on hover), in the detail panel, on the project page (a card and the evidence row) and in the
   portfolio evidence. Settings › Early warnings switches each signal off and sets its threshold. */
export const WARNS=()=>D.warnings||[], warnsOf=(k,id)=>WARNS().filter(w=>w.k===k&&w.id===id);
export const WICO=ic("bolt",{bare:true,w:2});   /* BL-158 */
export function wflag(k,id){ const w=warnsOf(k,id); if(!w.length) return ""; const why=w.map(x=>x.text);
  return `<span class="wflag" title="${esc(why.join("\n"))}" role="img" aria-label="Early warning: ${esc(why.join("; "))}">${WICO}</span>`; }
export const wOpen=w=>w.k==="milestones"?`data-ms="${w.id}"`:w.k==="projects"?`data-person="${esc(w.who||"")}"`:`data-open="${w.k}:${w.id}"`;   /* projects: the key-person signal (BL-56) */
export const wItem=w=>{ if(w.k==="projects") return `${pName(w.id)}: key person`; const x=w.k==="actions"?A.find(a=>a.id===w.id):w.k==="raid"?R.find(r=>r.id===w.id):w.k==="decisions"?DEC.find(d=>d.id===w.id):null; return x?x.t:((D.milestone_names||{})[w.id]||[w.id])[0]; };
export function decorateWarnings(root){ if(!root) return;
  root.querySelectorAll("[data-open]").forEach(el=>{ if(el.closest(".wlist")||el.querySelector(".wflag")) return; const [k,id]=el.dataset.open.split(":"); const f=wflag(k,id); if(f) addHTML((el.querySelector(".t")||el),"afterbegin",raw(f)); });
  root.querySelectorAll(".msrow[data-ms] .msn").forEach(el=>{ if(!el.querySelector(".wflag")) addHTML(el,"afterbegin",raw(wflag("milestones",el.closest("[data-ms]").dataset.ms))); }); }
/* Settings › Early warnings: each signal on or off, with its threshold (settings.json `warnings`) */
export const WSIG=[["redated","Action re-dated again and again","times","Re-dated at least (times)"],["repeat_risk","Risk raised repeatedly, no response","mentions","Raised in at least (meetings or sweeps)"],
  ["milestone_slip","Milestone slipping week after week","weeks","Forecast later this many weeks running"],["long_open","Action open far longer than usual","factor","Longer than the project's usual by (times)"],
  ["key_person","One person owns most of a project's open items","share","More than (% of the project's open items)"],
  ["dependency","Dependency due after what it blocks, or overdue near it","near_days","Overdue counts when the milestone is within (days)"]];   /* BL-56, BL-90 */
export const WSIG_MORE={long_open:["min_days","…and open at least (days)",14],key_person:["min_items","…with at least (open items)",6]};   /* a second threshold, under its signal */
export function warnSectionHtml(){ const W=D.warn_settings||{};
  return `${WSIG.map(([k,l,t,tl])=>row(l,`<input type="checkbox" class="switch" data-wk="${k}.on" ${(W[k]||{}).on!==false?"checked":""} aria-label="${esc(l)}">`)+((W[k]||{}).on!==false&&t?row(tl,`<input type="number" data-wk="${k}.${t}" value="${(W[k]||{})[t]??""}" min="1" step="${t==="factor"?"0.5":"1"}" style="width:80px" aria-label="${esc(tl)}">`):"")+((W[k]||{}).on!==false&&WSIG_MORE[k]?row(WSIG_MORE[k][1],`<input type="number" data-wk="${k}.${WSIG_MORE[k][0]}" value="${(W[k]||{})[WSIG_MORE[k][0]]??WSIG_MORE[k][2]}" min="1" style="width:80px" aria-label="${esc(WSIG_MORE[k][1])}">`):"")).join("")}<small class="sub">Flags are worked out when the dashboard is built; they're never stored.</small>`; }

/* BL-49 meeting prep: a Prep link on each of today's meetings opens a short brief for its project: open actions
   (overdue first), risks and issues with no response, decisions since the last meeting in the same series (else 7
   days) and early warnings; each line opens its item. The match comes from build_dashboard.prep (title and the
   register's signals). An unsure meeting asks for its project, and the choice is kept per series (settings.json
   prep.series). A portfolio meeting gets a cross-project brief. */
export const PREPN=8; shared.PREPEV=null; shared.PREPDAY=null;
export const prepTimed=()=>(((D.calendar||{}).days||{})[TODAY]||[]).filter(e=>!e.all_day), prepKey=(e,day)=>day&&day!==TODAY?`${day}|${e.start}|${e.title}`:`${e.start}|${e.title}`, prepOf=(e,day)=>e&&((D.prep||{}).meetings||{})[prepKey(e,day===undefined?shared.PREPDAY:day)];
export function prepDlg(){ let d=$("#prepDlg"); if(d) return d;
  /* BL-286 A: the header and toolbar (#prepTop) and the facts line and invite (#prepLead) are Preact components; the agenda card
     (#prepAgenda), the Prep page run's status (#prepPgStat) and the lists (#prepBody) are drawn by the code below */
  d=makePrepDialog(); mountPrepPopup($("#prepTop"),$("#prepLead")); mountPrepShape($("#prepShape"));   /* BL-286 C: Shape the meeting */
  d.addEventListener("click",e=>{   /* a click on the scrim is the Dialog's: it closes when nothing is typed */
    const o=e.target.closest("[data-open]"), inner=e.target.closest("button,input,select,a:not([data-open])");
    if(o&&prepPeekable(o)&&!(inner&&o.contains(inner))){ e.preventDefault(); e.stopPropagation(); prepPeek(o); return; }   /* BL-286 E: the full peek, over the popup */
    if(e.target.closest("#prepClose")||e.target.closest("[data-open],[data-ms],[data-nav],[data-proj]")) d.close(); });
  d.addEventListener("keydown",e=>{ if(e.key==="Enter"&&e.target.matches&&e.target.matches("[data-open]")&&prepPeekable(e.target)){ e.preventDefault(); e.stopPropagation(); prepPeek(e.target); } });
  d.addEventListener("close",()=>{ if(d.open||shared.PREPPEEK==="swap") return;   /* "close" comes as a task: after a swap the dialog is open again */ if(shared.PREPPEEK){ shared.PREPPEEK=null; shared.PKSRC=null; d.classList.remove("pknm"); if(pkOn()) closePanel(); } $("#prepScrim")?.remove(); });
  return d; }
export function openPrep(e,day){ shared.PREPEV=e; shared.PREPDAY=day||TODAY; const d=prepDlg(); loadBrief(prepKey(e,shared.PREPDAY)); drawPrep(); openDialog(d); $("#prepScroll").scrollTop=0; }
/* ===== BL-286 E: the full Work peek over the Prep popup =====
   The popup is a modal dialog in the top layer, so a peek (#panel, with its pickers and the staged pill) can't sit above it.
   While an item is open the dialog becomes non-modal, over a scrim of its own, and the peek opens above it; ↑ ↓ step through
   the popup's items. Closing the peek makes the dialog modal again, with focus back on the item's line. */
export const prepPeekable=el=>{ const [k,id]=String(el.dataset.open||"").split(":"); return ["actions","raid","decisions"].includes(k)&&!!REC(k,id); };
/* the popup's items: the brief's, or the shaping panel's while a meeting is being shaped (BL-286 C) */
export const prepPeekRoot=()=>{ const d=$("#prepDlg"); return d&&d.classList.contains("shaping")?"#prepShape":"#prepBody"; };
export function prepPeekList(){ return $$(`${prepPeekRoot()} [data-open]`).filter(prepPeekable).map(el=>{ const [k,id]=el.dataset.open.split(":"); return {k,id}; }).filter((o,i,L)=>L.findIndex(x=>x.id===o.id)===i); }
export function prepPeekMark(){ const id=shared.CUR&&shared.CUR.id; $$(`${prepPeekRoot()} [data-open]`).forEach(el=>el.classList.toggle("sel",!!id&&el.dataset.open.split(":")[1]===id)); }
export function prepPeek(el){ const d=$("#prepDlg"), [k,id]=el.dataset.open.split(":"); if(!d||!d.open) return;
  if(!shared.PREPPEEK){ shared.PREPPEEK="swap"; d.close(); d.classList.add("pknm"); openDialog(d,{modal:false,focus:false}); shared.PREPPEEK={el:el.dataset.open};
    if(!$("#prepScrim")){ addHTML(document.body,"beforeend",html`<div id="prepScrim" aria-hidden="true"></div>`); $("#prepScrim").addEventListener("click",()=>closePanel()); } }
  else shared.PREPPEEK.el=el.dataset.open;
  shared.PKSRC={order:prepPeekList,step:o=>{ openRecord(o.k,o.id); if(shared.PREPPEEK) shared.PREPPEEK.el=`${o.k}:${o.id}`; prepPeekMark(); }};
  openRecord(k,id); prepPeekMark(); if(!pkOn()) prepPeekEnd(); }
export function prepPeekEnd(){ const d=$("#prepDlg"), was=shared.PREPPEEK; if(!was) return; shared.PKSRC=null; $("#prepScrim")?.remove();
  if(!d||!d.open){ shared.PREPPEEK=null; return; }
  shared.PREPPEEK="swap"; d.close(); d.classList.remove("pknm"); openDialog(d,{focus:false}); shared.PREPPEEK=null; drawPrep();
  const back=was.el&&$$(`${prepPeekRoot()} [data-open]`).find(x=>x.dataset.open===was.el); if(back) back.focus(); }
export function drawPrep(){ popupRev.value++; { const key=prepKey(shared.PREPEV,shared.PREPDAY); putHtml($("#prepAgenda"),AGD&&AGD.key===key?AGD.html:""); }   /* BL-286: the header, toolbar and facts line redraw too */
  (()=>{ const m=prepOf(shared.PREPEV)||{}, code=m.p, all=code==="_portfolio";
  const pick=code?"":'<div class="wnote">Not sure which project this meeting is for. Choose one from the project chip above, and creaite remembers it for this series.</div>';
  if(!code){ putHtml($("#prepBody"),pick); return; }
  const inP=x=>all||x.p===code, pc=x=>all?pLink(x.p)+" ":"";
  // @ts-expect-error TS2362: true and false subtract as 1 and 0 (overdue actions sort first)
  const acts=A.filter(x=>inP(x)&&(all?overdue(x)||soon(x):openOnly(x))).sort((a,b)=>(overdue(b)-overdue(a))||(a.due||"9").localeCompare(b.due||"9"));
  const risks=R.filter(r=>inP(r)&&r.st==="Open"&&(r.type==="Risk"||r.type==="Issue")&&!String(r.resp||"").trim()).sort((a,b)=>PRIOS.indexOf(a.pr)-PRIOS.indexOf(b.pr));
  const decs=DEC.filter(x=>inP(x)&&x.date>=m.since&&x.date<=TODAY).sort((a,b)=>b.date.localeCompare(a.date)), ws=WARNS().filter(w=>inP(w));
  /* BL-98: what the invite makes relevant moves to the top of each list, with why; the rest follow in the usual order */
  const rk=(k,id)=>((m.rank||{})[k]||{})[id], up=(k,list,id=x=>x.id)=>[...list.filter(x=>rk(k,id(x))).sort((a,b)=>rk(k,id(b))[0]-rk(k,id(a))[0]),...list.filter(x=>!rk(k,id(x)))];
  const why=(k,id)=>{ const r=rk(k,id); return r?`<span class="prepwhy">${esc(r[1])}</span>`:""; };
  const sec=(h,list,line,empty,nav,cnt)=>`<section class="prepsec"><h3>${h} <span class="sub">· ${cnt?countLink(cnt[0],list.length,cnt[1],cnt[2]):list.length}</span></h3>${list.length?`<div class="wlist">${list.slice(0,PREPN).map(line).join("")}</div>${list.length>PREPN&&nav?`<a href="#" class="seeall" data-nav="${nav}">+${list.length-PREPN} more — see all ›</a>`:""}`:`<div class="sub">${empty}</div>`}</section>`;
  const idc=x=>`<span class="idc">${esc(x.id)}</span>`;   /* BL-286: each line shows its ID, as in Work */
  putHtml($("#prepBody"),pick+'<div class="prepgrid">'
    +sec(all?"Overdue and due-soon actions":"Open actions",up("actions",acts),x=>`<div data-open="actions:${x.id}" tabindex="0">${wflag("actions",x.id)}${pc(x)}${idc(x)}${esc(x.t)}<span class="sub ${overdue(x)?"late":""}">${rel(x.due)} · ${esc(who(x.o))}</span>${why("actions",x.id)}</div>`,all?"Nothing overdue or due soon.":"No open actions.",all?"":`actions:open:${code}`,all?[`${plur(acts.length,"action")} overdue or due soon`,"actions:open:",{st:["Open","Delayed"],due:["overdue","soon"]}]:[`${plur(acts.length,"open action")} in ${pName(code)}`,`actions:open:${code}`])
    +sec("Risks and issues with no response",up("raid",risks),r=>`<div data-open="raid:${r.id}" tabindex="0">${wflag("raid",r.id)}${pc(r)}${idc(r)}${ico(r.type)}${esc(r.t)}<span class="sub">${esc(r.pr||"")} ${esc(r.type)} · ${esc(who(r.o))}</span>${why("raid",r.id)}</div>`,"Every open risk and issue has a response.",all?"":navOf(`raid:nomit:${code}`,{ty:["Risk","Issue"]}),risks.length===R.filter(r=>inP(r)&&r.st==="Open"&&(r.type==="Risk"||r.type==="Issue")&&!r.resp).length?[`${risks.length} risk${risks.length===1?" or issue":"s and issues"} with no response${all?"":" in "+pName(code)}`,`raid:nomit:${all?"":code}`,{ty:["Risk","Issue"]}]:null)
    +sec("Decisions since then",up("decisions",decs),x=>`<div data-open="decisions:${x.id}" tabindex="0">${pc(x)}${idc(x)}${ico("decision")}${esc(x.t)}<span class="sub">${fd(x.date)}${x.by?" · "+esc(x.by):""}</span>${why("decisions",x.id)}</div>`,"No decisions since then.",all?"":`decisions:all:${code}`)
    +(ws.length?sec("Early warnings",[...ws.filter(w=>rk(w.k,w.id)),...ws.filter(w=>!rk(w.k,w.id))],w=>`<div ${wOpen(w)} tabindex="0">${wflag(w.k,w.id)}${pc(w)}${w.k==="projects"?"":esc(w.id)+" · "}${esc(wItem(w))}<span class="sub">${esc(w.text)}</span>${why(w.k,w.id)}</div>`,"",""):"")
    +prepReports(code,all,sec,pc)+'</div>'); })();
  { const m=prepOf(shared.PREPEV)||{}, code=m.p, body=$("#prepBody");
    if(body&&code&&code!=="_portfolio"&&isSteering(shared.PREPEV&&shared.PREPEV.title)&&!body.querySelector(".steerlink")){
    const bar=`<p class="steerlink sub">Steering committee: <button class="mini" data-ask="steerco one-pager ${code}" data-steer="1" aria-label="Draft the one-pager" data-tip="Draft the steering one-pager with ask creaite">${ic("filetext")}One-pager</button> <button class="mini" data-ask="steerco one-pager ${code} client-safe" data-steer="1" aria-label="Draft the client-safe one-pager" data-tip="Draft the client-safe one-pager with ask creaite">${ic("filetext")}Client-safe one-pager</button> <span>(a Word draft for you to review; nothing is sent${viaServer()?"":"; needs the live server"})</span></p>`;
    addHTML(body,"afterbegin",raw(bar)); } }   /* BL-92 */
  { const m=prepOf(shared.PREPEV)||{}, code=m.p, body=$("#prepBody"); if(body&&code&&!body.querySelector("#prepDecs")){
    const all=code==="_portfolio", inP=x=>all||x.p===code, pc=x=>all?pLink(x.p)+" ":"", rk=id=>((m.rank||{}).decisions||{})[id];
    const up=list=>[...list.filter(x=>rk(x.id)).sort((a,b)=>rk(b.id)[0]-rk(a.id)[0]),...list.filter(x=>!rk(x.id))];
    const why=id=>rk(id)?`<span class="prepwhy">${esc(rk(id)[1])}</span>`:"";
    const steer=isSteering(shared.PREPEV&&shared.PREPEV.title), others=decPending().filter(inP).filter(d=>!steer||!dnOk(d)).sort(decRank);   /* BL-210: a steering meeting leads with the shared rows, in their order */
    const pend=steer?[...dnList(inP),...up(others)]:up(others), rev=up(decRevisit().filter(inP));
    const sec=(id,h,list,line,empty,nav,cnt)=>`<section class="prepsec" id="${id}"><h3>${h} <span class="sub">· ${cnt?countLink(cnt[0],list.length,cnt[1],cnt[2]):list.length}</span></h3>${list.length?`<div class="wlist">${list.slice(0,PREPN).map(line).join("")}</div>${list.length>PREPN&&nav&&!all?`<a href="#" class="seeall" data-nav="${nav}">+${list.length-PREPN} more — see all ›</a>`:""}`:`<div class="sub">${empty}</div>`}</section>`;
    const html=`<div id="prepDecs">`
      +sec("prepDecNeeded","Decisions needed",pend,d=>steer&&dnOk(d)?dnDecisionHtml(d,{inProject:!all,extra:why(d.id)}):`<div data-open="decisions:${d.id}" tabindex="0">${pc(d)}<span class="idc">${esc(d.id)}</span>${ico("decision")}${esc(d.t)}<span class="sub">${decAsked(d)} · ${d.due?(decLate(d)?`needed by ${fd(d.due)}, <span class="late">${decLateWords(d)}</span>`:`needed by ${fd(d.due)}`):"no date needed by"}</span>${why(d.id)}</div>`,"No decision is waiting.",`decisions:pending:${code}`,[`${plur(pend.length,"decision")} needed${all?"":" in "+pName(code)}`,`decisions:pending:${all?"":code}`])
      +(rev.length?sec("prepDecRevisit","Decisions to revisit",rev,d=>`<div data-open="decisions:${d.id}" tabindex="0">${pc(d)}${ico("decision")}${esc(d.t)}<span class="sub">revisit date ${fd(d.revisit)} reached${d.by?" · "+esc(d.by):""}</span>${why(d.id)}</div>`,"",`decisions:all:${code}`):"")+`</div>`;
    const at=[...body.querySelectorAll(".prepsec")].find(s=>/^Decisions since/.test((s.querySelector("h3")||{}).textContent||""));
    if(at) addHTML(at,"afterend",raw(html)); else addHTML(body,"beforeend",raw(html)); } }   /* BL-113 */
  if(shared.PREPPEEK) prepPeekMark(); }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootProjects0124(){
document.addEventListener("click",e=>{ if(e.target.closest("[data-wjump]")) mScroll($("#warnCard"),{block:"start"}); });
document.addEventListener("keydown",e=>{ if(e.key==="Enter"&&e.target.matches&&e.target.matches(".wlist [data-open]")) e.target.click(); });
$("#settingsBody").addEventListener("change",async e=>{ const el=e.target.closest("[data-wk]"); if(!el) return; e.stopPropagation();
  const [sig,key]=el.dataset.wk.split("."), v=el.type==="checkbox"?el.checked:Number(el.value);
  if(el.type==="number"&&!(v>0)){ snack("Use a number above 0"); renderSettings(); return; }
  if(!await writeSettings({[`warnings.${sig}.${key}`]:v})){ renderSettings(); return; }
  ((D.warn_settings=D.warn_settings||{})[sig]=D.warn_settings[sig]||{})[key]=v; renderSettings();
  if(SERVED){ await reloadData(); snack("Saved; early warnings updated"); } else snack("Saved to settings.json; the flags update at the next rebuild"); },true);
}
