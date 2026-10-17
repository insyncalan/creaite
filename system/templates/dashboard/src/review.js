// @ts-check
/* review.js (BL-231 step 2b), moved from script/ by dev/tools/convert_area.py: 0060-review.js, 0061-bl-133-sprint-work-views.js, 0063-after-bl-216.js, 0064-bl-133-stage-b-sprint-work-views.js, 0065-bl-221-sprint-drafts-extraction.js, 0066-bl-218-sprint-drafts-extraction.js, 0067-after-bl-218.js, 0193-bl-200-sprint-review-work.js, 0195-bl-197-sprint-review-work.js, 0209-bl-208-sprint-insight.js.
   Unchanged apart from `export`, `shared.` for the shared state (core/state.js) and the load-time steps, now in
   boot…() functions that src/main.js calls in today's order. */
import { openDialog } from "./components/Dialog.jsx";
import { linkHtml, linkWords } from "./core/linkText.js";
import { drawFilterBar } from "./components/FilterBar.jsx";

import { actHref } from "./activity.js";
import { A, DEC, open, P, peopleAll, pName, R, REV, SWEPT, wsFor } from "./core/data.js";
import { $, $$, addHTML, esc, html, ibtn, ic, ICONS, putHTML, raw } from "./core/dom.js";
import { linkAnchor } from "./core/linkUrl.js";
import { CALI, DATE_HELP, srcHTML, srcParse, srcShort, weekendNote, wkLong } from "./core/fields.js";
import { typing } from "./core/keys.js";
import { mDots, mRowGone, mSnapRows } from "./core/motion.js";
import { go } from "./core/nav.js";
import { D, DDATE, fd, fdText, isMe, MAC, nowStamp, OPENST, prio, reduced, revIco, S, store, TODAY, toIso, who } from "./core/page.js";
import { api, apply, applyNow, applySoon, conflictChoice, editProposal, hideSnack, needVault, oneLine, refreshAll, refreshItems, reloadData, renderBadge, reviewViaServer, snack, toDb, undoApply, viaServer } from "./core/server.js";
import { shared } from "./core/state.js";
import { deMe, draftStat, openDraftEmail, shRvHtml } from "./drafts.js";
import { kb } from "./intake.js";
import { withdrawDecision } from "./meetings.js";
import { drawPanel, drSame, learnable, learnSignal, msChoices, nextId, NODRAFT_MSG, openProposal, openRecord, pkDow, pkFollowRev, PKK, pkStatuses, pkWho, REC } from "./panel.js";
import { closePanel, pkOn } from "./projects.js";
import { nm, PERS, personLink, row, unknownOwner } from "./settings.js";
import { conflictHtml, isConflict, kindLabel, pkAdd, plur, revGroupTitle } from "./today.js";
import { mountRejectMenu } from "./components/review/RejectMenu.jsx";
import { closeMenu, menuOpenFor, openMenu } from "./components/Menu.jsx";
import { contextMenuOpen, openContextMenu, openContextMenuAt } from "./components/review/ContextMenu.jsx";
import { closePicker, openPicker, pickerOpenFor } from "./components/Picker.jsx";
import { rjAddGone, rjCloseMenu, rjDropGone, rjGone, rjGuesses, rjGuessFor, rjMenu, rjOpenMenu, rjReasons, rjRecent, rjSetGone } from "./stores/rejects.js";
import { batchMove, BK_STATUS, bkWhat, boardAsk, boardMove, cell, ceOpts, funnelTip, hit, HL, hlOnly, items, kOfId, msLabel, recordFromBoard, rows, rvfCount, rvOnly, rvPaint, rvPick, srcKind, thisFriday } from "./work.js";
/* ======================= Review ======================= */
shared.RSEL=0; export const CHK=new Set(), RHL=new Set();     /* RHL: the highlighted rows (BL-122); a row that may be ticked is ticked too, so the two are one selection */
export function applyProposal(r){ if(r.kind==="actions"){ const rec=Object.assign({id:nextId("actions",r.p),p:r.p,raised:TODAY,closed:null,src:r.src,upd_at:nowStamp()},r.rec); A.push(rec); return ()=>A.splice(A.indexOf(rec),1); }
  if(r.kind==="raid"){ const rec=Object.assign({id:nextId("raid",r.p),p:r.p,raised:TODAY,closed:null,src:r.src,upd_at:nowStamp()},r.rec); rec.pr=prio(rec.imp,rec.lik); R.push(rec); return ()=>R.splice(R.indexOf(rec),1); }
  if(r.kind==="decisions"){ const rec=Object.assign({id:nextId("decisions",r.p),p:r.p,src:r.src,upd_at:nowStamp()},r.rec); DEC.push(rec); return ()=>DEC.splice(DEC.indexOf(rec),1); }
  if(r.kind==="update"){ const x=REC("actions",r.rec.target)||REC("raid",r.rec.target); if(!x||r.rec.field!=="status") return ()=>{}; const b={...x}; x.st=r.rec.to; if(!OPENST(x.st)) x.closed=TODAY; return ()=>Object.assign(x,b); } return ()=>{}; }
export function setDecision(data,r,v){ const bf={meeting:"minutes_decision",report:"report_decision",file_changes:"file_changes_decision"}[r.ref];
  if(bf){ if(!data[r.ref]||data[r.ref].applied) throw new Error("already applied"); data[r.ref][bf]=v; data[r.ref].decided_in="dashboard"; return; }
  const it=(data.items||[]).find(i=>i.n===r.ref); if(!it||it.applied) throw new Error("already applied"); it.decision=v; it.decided_in="dashboard";
  const w=RVREASON.get(r.n);
    if(v==="rejected"&&w){ it.reject_reason=w.reason; if(w.dup) it.duplicate_of=w.dup; else delete it.duplicate_of; RVREASON.delete(r.n); } else if(v!=="rejected"){ delete it.reject_reason; delete it.duplicate_of; }
    if(it&&it.drafted&&(v==="approved"||v==="rejected")){ const f=Object.keys(it.changes||{})[0]; draftStat(it.drafted,v==="rejected"?"rejected":drSame((it.changes||{})[f],it.drafted_text)?"used":"edited"); }
    if(it&&it.suggested&&it.suggested.feature==="done"&&(v==="approved"||v==="rejected")) draftStat("done",v==="rejected"?"rejected":it.as_proposed?"edited":"used");   /* BL-218 */
    if(it&&it.suggested&&it.suggested.feature==="promise"&&(v==="approved"||v==="rejected")) draftStat("promise",v==="rejected"?"rejected":it.as_proposed?"edited":"used");   /* BL-342 Part 5 */
    if(it&&it.looks_like&&v==="rejected"&&it.duplicate_of===it.looks_like.id) draftStat("repeat","used");   /* BL-221: rejected as its duplicate */ }
export let decide = async function(n,v,written){ const tr=$(`#reviewBody tr[data-n="${n}"]`), was=REV.find(x=>x.n===n);
    const snap=tr&&shared.VIEW==="review"&&!reduced()?{g:{r:tr.getBoundingClientRect(),t:(tr.querySelector("td.title")||tr).textContent.trim()},rows:mSnapRows("#reviewBody tr[data-n]",e=>e.dataset.n)}:null;
    const before=was&&was.done;
  const res=await (async()=>{ const r=REV.find(x=>x.n===n); if(!r||r.done) return; if(v==="approved"&&r.kind==="draft"&&r.nodraft){ snack(NODRAFT_MSG); return; }   /* BL-260 point 4 (fix-minutes-approve): never approved; Reject still works */
  if(v==="approved"&&!r.p&&r.kind!=="files"){ snack("Choose a project first — open the item to set it"); openProposal(n); return; }
  if(viaServer()&&v==="approved"&&r.kind==="draft") return reviewViaServer(r,"approved",[]);
  if(viaServer()&&v==="approved"&&(r.flags||[]).includes("conflict")) return conflictChoice(r);
  if(v==="approved"&&r.kind==="draft"){ snack(`Approving a draft needs the live server, which checks and cleans it first; or say “approve ${r.rec.t.replace(/^Minutes: /,"minutes for ").replace(/^Report: /,"report for ")}” in Claude Code`); return; }   /* BL-149 */
  if(v==="approved"&&(r.flags||[]).includes("conflict")){ snack("This conflicts with a newer change: Keep current or Use this one needs the live server; or say “keep” or “override” in Claude Code (review)"); return; }   /* BL-149 */
  if(!written){ if(!await needVault()) return; try{ await editProposal(r.file,data=>setDecision(data,r,v)); }catch(e){ snack("Not saved: "+e.message); return; } }
  if(viaServer()&&S.autoApply){ CHK.delete(n); r.done=v; refreshAll(); applySoon(); return; }
  let undoRec=()=>{}; CHK.delete(n);
  apply(`#${n} ${v==="approved"?"approved":"rejected"}: ${r.rec.t}`,()=>{ r.done=v; if(v==="approved") undoRec=applyProposal(r); },
    async()=>{ delete r.done; undoRec(); try{ await editProposal(r.file,data=>setDecision(data,r,"pending")); }catch(e){ snack(viaServer()?"Already applied: undo it in Activity":"Already applied: use “undo last apply” in Claude Code"); } },"You, in Review"); })();   /* BL-149 */
  { const x=REV.find(y=>y.n===n); if(x&&x.done&&!RVINBATCH){ shared.RVSTATS[v]=(shared.RVSTATS[v]||0)+1; if(shared.VIEW==="review"&&!$("#panel").classList.contains("on")) rvAdvance(n); } }
  const now=REV.find(x=>x.n===n); if(snap&&now&&now.done&&!before) mRowGone(snap,n,v); return res; };
/* BL-25: what's needed to decide, on one line. Urgent red, High amber; missing owner or due date, and overdue, amber. */
export const WKRVF={actions:["due","due_date"],raid:["due","due_date"],decisions:["due","needed_by"]};   /* BL-180: declared before revDetail, which runs at load (Review) */
export const draftOn=f=>!(S.drafting&&S.drafting[f]===false);   /* AI drafts: declared before revDetail, which runs at load (Review) */
/* BL-290: the row's "Looks like" mark, only while Settings › General › AI drafts › Spot repeats is on (BL-133's reject reason keeps r.dup) */
export const rvDup=r=>draftOn("repeat")&&r.dup||null;
export function revDetail(r){ const x=r.rec, w=t=>`<span class="h-warn">${t}</span>`, pc=p=>p==="Urgent"?`<span class="h-bad">${p}</span>`:p==="High"?w(p):p,
    // @ts-expect-error TS2362: a Date minus a Date is the milliseconds between them (valueOf)
    dueTxt=d=>{ if(!d) return w("No due date"); const n=Math.round((new Date(d)-new Date(TODAY))/864e5); return n<0?w(`${fd(d)} · ${-n} day${n===-1?"":"s"} overdue`):`${fd(d)} · ${n===0?"today":`in ${n} day${n===1?"":"s"}`}`; },
    who=o=>!o||o==="TBC"?w("No owner"):unknownOwner(o)?w(`${personLink(o,o)} (not in the people register)`):personLink(o,o), ms=x.ms?`Milestone ${esc(((D.milestone_names||{})[x.ms]||[x.ms])[0])}`:"", parts=
    r.kind==="actions"?[who(x.o),dueTxt(x.due),pc(x.pr||"Medium"),esc(x.ws||""),ms]:
    r.kind==="raid"?[esc(x.type),who(x.o),x.imp&&x.lik?`${x.imp} × ${x.lik} → ${pc(prio(x.imp,x.lik))}`:w("Impact and likelihood not set"),x.resp?`Response: ${linkHtml(x.resp)}`:w("No response yet"),x.due?dueTxt(x.due):"",ms]:
    r.kind==="decisions"?[x.by?`Made by ${personLink(x.by,x.by)}`:w("Made by not recorded"),x.date?fd(x.date):""]:
    r.kind==="update"?(x.changes||[]).map(c=>`${esc(c.field)}: ${esc(fd(c.from==null||c.from===""?"—":linkWords(String(c.from))))} → ${esc(fd(c.to==null||c.to===""?"—":linkWords(String(c.to))))}`):
    r.kind==="draft"&&r.nodraft&&!r.done?[w("No Word draft was made for these minutes"),"Reject them and process the meeting again"]:[];   /* BL-260 */
  let h=(r.dn?dnHtml(r):"")+parts.filter(Boolean).join(" · ")+shRvHtml(r);
  if(r.kind==="update"&&r.rec&&r.rec.why) h=`${h} · <span class="sub">“${esc(r.rec.why)}”</span>`;   /* BL-65 */
  if(!shared.LOADING){ { const fdef=r&&WKRVF[r.kind], v=fdef&&r.rec?r.rec[fdef[0]]:null, n=weekendNote(v); if(n&&!r.done) h+=`<div class="wkrv"><span class="h-warn">${r.kind==="decisions"?"Needed":"Due"} on a ${esc(n.day)}</span> <button type="button" class="mini" data-wkrv="${r.n}" data-to="${n.prev}">${esc(wkLong(n.prev))}</button> <button type="button" class="mini" data-wkrv="${r.n}" data-to="${n.next}">${esc(wkLong(n.next))}</button></div>`; }   /* BL-180 */
  if(r&&r.drafted) h=`<span class="tag drrv">${ic("spark")}${r.drafted==="client"?"Drafted wording":"Drafted"}</span> ${h}`;
  if(!(!r||r.done||r.kind!=="raid"||String(r.rec.resp||"").trim()||(r.rec.type&&r.rec.type!=="Risk")||!draftOn("thinking"))) h=`${h} · <button type="button" class="linkbtn" data-drrisk="${r.n}">Draft a response</button>`; }   /* BL-225 */
  return h; }   /* BL-218: a probably-done update leads with its evidence; BL-260 */
/* BL-21: a discreet pencil, bottom-right of each editable tile */
export const pencil=(attrs,label,icon,cls)=>`<button class="pencil${cls?" "+cls:""}" ${attrs} title="${label}" aria-label="${label}"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icon||ICONS.pencil}</svg></button>`;
export const SPARKI='<path d="M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8z"/><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z"/>';   /* BL-61: "draft with AI" */
export const IMGI='<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="m21 17-5-5-9 8"/>';
/* BL-41: the items extracted from draft minutes sit under them (same proposal file), in each project the meeting
   covers; items from mail, Teams, cx-edit or the dashboard stay at project level */
export const isMin=r=>r&&r.kind==="draft"&&r.ref==="meeting";
export const kidsOf=(m,g)=>REV.filter(x=>x.file===m.file&&!["draft","files"].includes(x.kind)&&(g==="*"||(x.p||"?")===g));   /* "*": every project's (BL-133: grouped by source) */
export const routineKid=x=>!x.done&&!x.indiv&&x.p&&!(x.flags||[]).includes("conflict");
export const COLLAPSED=new Set();
/* BL-228 D: built with html`…`, returned as a string because the wrappers below (conflicts, Project) edit it as text */
export const rvMovable=r=>!!r&&!r.done&&(isMin(r)||["actions","raid","decisions"].includes(r.kind));   /* BL-186: declared before revRow, which runs at load (Review) */
export function revRow(r,idx,g,cls,head){ const minKids=isMin(r)&&head.kids.some(routineKid);
  let h=String(html`<tr class="click ${cls||""} ${idx===shared.RSEL?"sel":""}${RHL.has(r.n)?" hl":""}" aria-selected="${String(RHL.has(r.n))}" data-ri="${idx}" data-n="${r.n}" data-g="${g}"><td style="width:32px"><input type="checkbox" aria-label="${isMin(r)?"Select the routine items from these minutes":`Select ${r.rec.t??""}`}" ${raw(isMin(r)?(minKids&&head.kids.filter(routineKid).every(k=>CHK.has(k.n))?"checked":""):(RHL.has(r.n)?"checked":""))} ${raw(r.done||(isMin(r)&&!minKids)?"disabled":"")}></td><td class="title">${head&&head.kids.length?html`<button class="mini tog" data-act="t" aria-expanded="${String(!head.closed)}" title="${head.closed?"Show":"Hide"} its items">${raw(ic("chevdown","chev"))}${head.kids.length} item${head.kids.length===1?"":"s"}</button> `:""}${raw(revIco(r))}${r.rec.t??""}${r.edited?html` <span class="tag">· edited</span>`:""}${rvOutlier(r)?html` <span class="tag stale rvold">Oldest · ${rvAgeText(r)}</span>`:""}${rvDup(r)&&!r.done?raw(llTag(r)):""}${revDetail(r)?html`<div class="why rdet">${raw(revDetail(r))}</div>`:""}<div class="why">${kindLabel(r)??""} · ${r.why??""}${r.indiv?html` · <span class="indiv">approve individually</span>`:""}${raw(rjGuessHtml(r))}</div><div class="why">${fdText(srcShort(r.src))??""}${raw(rvSrcLink(r))}</div></td><td style="white-space:nowrap;text-align:right">${r.done?html`<span class="${r.done==="approved"?"h-ok":"h-bad"}" style="font-weight:500">${r.done==="approved"?"Approved":"Rejected"}</span>`:html`<span class="rvage${rvOutlier(r)?" old":""}">${rvAgeText(r)}</span> <span class="rowact">${isMin(r)&&viaServer()?raw(ibtn("refresh","Refresh items",'data-act="f"',"sm")):""}${raw(ibtn("pencil",r.kind==="draft"?(r.nodraft?"No Word draft":"Open draft"):"Edit",'data-act="e"',"sm","E"))}</span> ${head&&head.kids.some(routineKid)?html`<button class="mini ok" data-act="ga" title="Approves the routine items; minutes, new decisions and new risks stay for one-by-one approval">Approve all from these minutes</button> `:""}<button class="mini ok" data-act="a"${r.nodraft?html` disabled title="${NODRAFT_MSG}"`:""}>${raw(ic("check"))}Approve</button> ${raw(rvRejectOK(r)?ibtn("x","Reject, with a reason",'data-act="r" aria-haspopup="menu"',"sm no","R"):ibtn("x","Reject",'data-act="r"',"sm no","R"))}${["draft","files"].includes(r.kind)?"":raw(ibtn("chevdown","Reject with a reason",'data-act="rr" aria-haspopup="menu"',"sm no rvrr","Shift+R"))}`}</td></tr>`);
  if(isConflict(r)){
    const live=viaServer(), btns=`<button class="mini" data-act="ck" ${live?"":'disabled title="Needs the live server"'}>Keep current</button> <button class="mini ok" data-act="co" ${live?"":'disabled title="Needs the live server"'}>Use this one</button>`;
    h=h.replace(/<button class="mini ok" data-act="a">.*?<\/button>/,btns);   /* BL-160: the Approve button carries its icon */
    const i=h.indexOf('<div class="why">'); if(i>0) h=h.slice(0,i)+conflictHtml(r)+h.slice(i); }
  if(!shared.LOADING&&rvMovable(r)) h=h.replace('<span class="rowact">',`<span class="rowact"><button type="button" class="mini rvpj" data-act="pj" aria-haspopup="menu" title="${isMin(r)?"Move these minutes and their items to another project":"Move to another project"}">${ic("projects")}Project</button>`);
  return h; }
export let RVLASTN=null, RVLASTV=null, RVSHOWN=false;   /* BL-263: the cleared tick's memory of the last draw */
shared.MREVLEFT=false;   /* declared before renderReview, which runs at load */
export const MLV=store.get("creaite-lastviewed",{}), MLVAT={}, MNEWGONE=new Set();   /* declared before renderReview, which runs at load */
shared.RF=null;      /* {q:[n…], i, key} while the mode is on */
export const mFileAt=f=>{ const m=/(\d{4}-\d{2}-\d{2})[-T_ ]?(\d{2})(\d{2})/.exec(f||""); return m?`${m[1]} ${m[2]}:${m[3]}`:null; };   /* declared before renderReview, which runs at load */
shared.MNEWIO=null;   /* declared before renderReview, which runs at load */
export function renderReview(){ { const v=r=>(r.flags||[]).includes("vip")?0:1; REV.sort((a,b)=>v(a)-v(b)); }   /* BL-152: a followed person's proposals first, unlabelled (BL-288) */
 CHK.forEach(n=>RHL.add(n)); [...RHL].forEach(n=>{ const r=REV.find(x=>x.n===n); if(!r||r.done) RHL.delete(n); }); rvSyncChk(); if(!shared.LOADING) rjLoadGuesses();   /* BL-315 */
  rvRender(); renderBadge(); 
  REV.filter(r=>r.ws_suggest&&!r.done&&(r.flags||[]).includes("new-workstream")).forEach(r=>{ const cell=$(`#reviewBody tr[data-n="${r.n}"] td.title`); if(!cell||cell.querySelector(".wsq")) return;
    addHTML(cell,"beforeend",html`<div class="wsq">New workstream “${r.ws_suggest}” for ${(r.p||"?")}? <button class="mini" data-wsq="add" data-n="${r.n}">Add workstream</button><button class="mini" data-wsq="skip" data-n="${r.n}">Leave blank</button></div>`); });   /* BL-58 */
  if(!shared.LOADING){
    const n=REV.filter(r=>!r.done).length, d=$("#reviewBody .rvdone")||$("#v-review .rvdone");
    if(shared.MREVLEFT){ shared.MREVLEFT=false; RVLASTV=null; }   /* Review was left and opened again: an empty queue is just empty */
    if(RVLASTV!=="review"||n>0) RVSHOWN=false;
    if(d&&n===0&&shared.VIEW==="review"&&(RVSHOWN||RVLASTN>0&&RVLASTV==="review")&&!d.querySelector(".mclear")){ d.classList.add("mcleared"); if(RVSHOWN) d.classList.add("mstill"); RVSHOWN=true; addHTML(d,"afterbegin",html`<svg class="mclear" viewBox="0 0 44 44" aria-hidden="true"><circle cx="22" cy="22" r="20"/><path d="M13 22.5l6 6 12-13"/></svg>`); }
    RVLASTN=n; RVLASTV=shared.VIEW;
  mDots("review");
    REV.filter(x=>x.kind==="draft"&&x.ref==="meeting"&&!x.done&&(x.mt||(x.cov||[]).length)).forEach(x=>{ const el=document.querySelector(`#v-review [data-n="${x.n}"]`); if(!el||el.nextElementSibling&&el.nextElementSibling.classList.contains("mhcovrow")) return;
      const cov=(x.cov||[]), miss=cov.filter(c=>c.verdict!=="Covered").length;
      const body=html`${cov.length?html`<details class="mhcovrev"><summary>Coverage: ${miss?`${miss} of ${cov.length} agenda points not fully discussed`:`all ${cov.length} agenda points discussed`}</summary><ul class="mhcov">${cov.map(c=>html`<li><span class="tag ${c.verdict==="Covered"?"ok":c.verdict==="Not discussed"?"warn":""}">${c.verdict}</span> ${c.point}</li>`)}</ul></details>`:""}`;
      if(!String(body)) return; addHTML(el,"afterend",el.tagName==="TR"?html`<tr class="mhcovrow"><td></td><td colspan="20">${body}</td></tr>`:html`<div class="mhcovrow">${body}</div>`); });   /* BL-233 */
  const bar=$("#rvfilters"); if(bar&&!$("#rvFocusBtn")) addHTML(bar,"afterend",html`<button type="button" class="btn rvfocusbtn" id="rvFocusBtn" data-rvfocus="1" title="Decide one proposal at a time, with its source beside it">One at a time</button>`);
    if(shared.RF) rfDraw(); } }   /* BL-206 */   /* BL-133 (sprint-work-views): filters, grouping and order are in rvRender; grouped by project it draws as before */
export function toggleGroup(m,g,on){ const ks=kidsOf(m,g).filter(routineKid); if(on===undefined) on=!ks.every(k=>CHK.has(k.n)); ks.forEach(k=>on?CHK.add(k.n):CHK.delete(k.n)); renderReview(); }
export async function approveGroup(m,g){ RVINBATCH=true; try{ const kids=kidsOf(m,g), ks=kids.filter(routineKid), left=kids.filter(x=>!x.done&&!routineKid(x)).length;
  for(const k of ks){ CHK.delete(k.n); await decide(k.n,"approved"); }
  snack(`Approved ${ks.length} item${ks.length===1?"":"s"} from these minutes${left?` · ${left} still need approving one by one`:""}`); renderReview(); } finally{ RVINBATCH=false; } }
export async function rejectMinutes(m){ await decide(m.n,"rejected"); const pend=REV.filter(x=>x.file===m.file&&!["draft","files"].includes(x.kind)&&!x.done);
  if(pend.length) snack(`Minutes rejected. Its ${pend.length} item${pend.length===1?"":"s"} stay for review.`,async()=>{ for(const k of pend) await decide(k.n,"rejected"); renderReview(); },`Reject ${pend.length===1?"it":"them"} too`); }
   /* BL-198: the open peek follows the click. BL-122: a click highlights (repainted in place, so a double-click still lands on the row); a double-click opens */
/* BL-122: the buttons act on what is highlighted, and the bulk rule is unchanged: minutes, reports, health changes, new decisions, a decision
   recorded or withdrawn and new risks are `indiv` and are never in CHK, however they are selected; the message says how many were left out */
export function rvLeftOut(){ const n=[...RHL].filter(x=>{ const r=REV.find(y=>y.n===x); return r&&!r.done&&!CHK.has(x); }).length; return n?` ${n} highlighted ${n===1?"needs":"need"} individual approval and ${n===1?"was":"were"} left out.`:""; }
/* BL-133 (sprint-work-views): Approve, Reject and Approve all routine are the Review bar's and the preview's (rvApproveSelected, rvRejectSelected, rvRoutine) */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootReview0060(){
$("#reviewBody").addEventListener("click",e=>{ const tr=e.target.closest("tr[data-n]"); if(!tr) return; const n=+tr.dataset.n, g=tr.dataset.g; shared.RSEL=+tr.dataset.ri;
  const rr=REV.find(x=>x.n===n);
  if(isMin(rr)){ if(e.target.type==="checkbox"){ toggleGroup(rr,g,e.target.checked); return; } const a=e.target.closest("[data-act]");
    if(a&&a.dataset.act==="t"){ const key=rr.file+"|"+g; COLLAPSED.has(key)?COLLAPSED.delete(key):COLLAPSED.add(key); renderReview(); return; }
    if(a&&a.dataset.act==="ga"){ approveGroup(rr,g); return; } if(a&&a.dataset.act==="r"){ rejectMinutes(rr); return; } }
  if(e.target.type==="checkbox"){ e.target.checked?RHL.add(n):RHL.delete(n); shared.RVA=n; rvSyncChk(); renderReview(); return; }   /* BL-133: any proposed item can be selected (Reject may cover it); Approve still takes only what the bulk rule allows */
  if(e.target.closest("a")) return;                                                                   /* Open source and other links do their own job */
  const b=e.target.closest("[data-act]"); if(b){ if(b.dataset.act==="f"){ refreshItems(REV.find(x=>x.n===n)); return; } if(b.dataset.act==="a") decide(n,"approved"); else if(b.dataset.act==="r"){ const r=REV.find(x=>x.n===n); if(rvRejectOK(r)) rjMenuFor(rjWith(r),b); else decide(n,"rejected"); } else openProposal(n); return; }   /* BL-315: ✕ opens the reasons menu */ rvPick(e,n); rvPaint(); pkFollowRev(e,n); });
$("#reviewBody").addEventListener("dblclick",e=>{ const tr=e.target.closest("tr[data-n]"); if(!tr||e.target.closest("button,input,a,select")) return; const n=+tr.dataset.n; shared.RSEL=+tr.dataset.ri; rvOnly(n); openProposal(n); rvPaint(); });
$("#reviewBody").addEventListener("mousedown",e=>{ if(e.shiftKey&&e.target.closest("tr[data-n]")) e.preventDefault(); });
}
/* ===== BL-133 (sprint-work-views) =====
   Review as a triage queue. One selection (BL-122's highlight; the ticks follow it), a tick on each group, Select all N (every
   undecided row the filters show, Cmd/Ctrl+A too) and a bar: the count, what can be approved together and what can't (and why),
   Approve and Reject, and Set project, owner, due date, workstream and milestone on the selected proposals. The bulk rule is
   unchanged (rvBulkOK): minutes, reports, file changes, health changes, new decisions, a decision recorded or withdrawn, new risks,
   closing updates, conflicts and items with no project are never approved in bulk. Reject covers any proposed item except minutes,
   reports and file changes (one at a time, as before). Decisions are written one proposal file at a time and applied once
   (rvDecideMany), so a batch is one apply and one Undo; the result names what was left out, with Show them. Approve all routine
   acts on what the filters show and opens a preview first; so does any batch over 25. Filters (Kind, Needs, Source, Project, Age,
   each with is / is not), a search, Display (group by project, source or kind; order by age, kind or due date), the stale tag,
   Open source, auto-advance (review.auto_advance) and the empty-queue summary. Cmd/Ctrl+Z undoes the last decision or batch. */
export const RVF={k:new Set(),nd:new Set(),src:new Set(),p:new Set(),age:new Set()}, RVNEG=new Set(); export let RVQ="", RVG="project", RVO="", RVPK="k", RVLASTUNDO=null; shared.RVSTATS={approved:0,rejected:0,edited:0};
shared.RV_MAX=25;                                     /* a batch over this asks first (a let, so a test can lower it) */
export const rvBulkOK=r=>!!r&&!r.done&&!r.indiv&&!!r.p&&!["draft","files"].includes(r.kind)&&!(r.flags||[]).includes("conflict");
export const rvRejectOK=r=>!!r&&!r.done&&!["draft","files"].includes(r.kind);
export function rvSyncChk(){ CHK.clear(); RHL.forEach(n=>{ const r=REV.find(x=>x.n===n); if(rvBulkOK(r)) CHK.add(n); }); }
/* why an item can't be approved in bulk, in words */
export function rvWhyNot(r){ if(!r.p&&r.kind!=="files") return ["project","needs a project"]; if((r.flags||[]).includes("conflict")) return ["conflict","has a conflict to settle"];
  if(r.kind==="draft") return ["indiv",`${r.ref==="meeting"?"minutes are":"a report is"} approved on its own`]; if(r.kind==="files") return ["indiv","a file change is approved on its own"];
  return ["indiv",`${String(r.why||"this").toLowerCase()} is never approved in bulk`]; }
export const rvSrcKind=r=>r.kind==="draft"?(r.ref==="meeting"?"Minutes":"Report"):srcKind({src:r.src});
export const rvOwner=r=>r.kind==="decisions"?r.rec.by:r.rec.o;
export function rvNeeds(r){ const out=[]; if(!r.p&&r.kind!=="files") out.push("project"); if(["actions","raid"].includes(r.kind)){ const o=r.rec.o; if(!o||o==="TBC") out.push("owner"); else if(unknownOwner(o)) out.push("unknown"); }
  if(r.kind==="actions"&&!r.rec.due) out.push("due"); if(r.indiv) out.push("indiv"); if((r.flags||[]).includes("conflict")) out.push("conflict"); if(r.stale) out.push("stale"); return out; }
/** @type {[string, string, () => any[], (r: any, set: Set<any>) => boolean][]} each filter: key, label, its choices, and the test */
export const RVFIELDS=[["k","Kind",()=>[["actions","Action"],["raid","Risk or issue"],["decisions","Decision"],["update","Update"],["draft","Minutes or report"],["files","File change"]],(r,set)=>set.has(r.kind)],
  ["nd","Needs",()=>[["project","A project"],["owner","An owner"],["due","A due date"],["indiv","Individual approval"],["conflict","A conflict settled"],["unknown","An owner not in the register"],["stale",`Stale (over ${+S.staleDays||7} days)`]],(r,set)=>rvNeeds(r).some(v=>set.has(v))],
  ["src","Source",()=>["Minutes","Mail","Teams","Dashboard","cx-edit","Excel","Report","Other"].map(v=>[v,v]),(r,set)=>set.has(rvSrcKind(r))],
  ["p","Project",()=>[["?","Needs a project"],...P.map(p=>[p.code,p.name])],(r,set)=>(isMin(r)?(r.projects||[r.p]):[r.p]).some(p=>set.has(p||"?"))],
  ["age","Age",()=>[["1","Today or yesterday"],["7","This week"],["old",`Older than ${+S.staleDays||7} days`]],(r,set)=>[...set].some(v=>v==="old"?!!r.stale:(r.age||0)<=+v)]];
export const rvDef=k=>RVFIELDS.find(f=>f[0]===k);
export function rvQOK(r){ const w=RVQ.toLowerCase().split(/\s+/).filter(Boolean); if(!w.length) return true; const hay=[r.rec.t,r.src,r.why,r.p?pName(r.p):"",rvOwner(r)||"",kindLabel(r)].join(" ").toLowerCase(); return w.every(t=>hay.includes(t)); }
export function rvPasses(r,skip){ for(const [k,,,hit] of RVFIELDS){ if(k===skip) continue; const set=RVF[k]; if(set.size&&(RVNEG.has(k)?hit(r,set):!hit(r,set))) return false; } return skip==="q"||rvQOK(r); }
export const rvShown=()=>[...document.querySelectorAll("#reviewBody tr[data-n]")].map(t=>REV.find(r=>r.n===+t.dataset.n)).filter(Boolean);
export const rvMatching=()=>REV.filter(r=>!r.done&&rvPasses(r));          /* every undecided row the filters show, collapsed minutes included */
/* ── drawing ── */
export const RVKINDS={actions:"Actions",raid:"Risks and issues",decisions:"Decisions",update:"Updates",draft:"Minutes and reports",files:"File changes"};
export function rvBlocks(){ const out=rvBlocks0(); rjPlace(out); return out; }   /* BL-315: the rows rejected here, greyed, in their place */
export function rvBlocks0(){ const gk=new Set(rjGone.value.map(g=>g.rk)), ok=r=>!gk.has(rvKey(r))&&rvPasses(r), out=[];      /* [{key,title,blocks:[[{r,g,cls,head}]]}] */
  const minBlock=(m,g)=>{ const kids=kidsOf(m,g), vk=kids.filter(ok); if(!ok(m)&&!vk.length) return null; const closed=COLLAPSED.has(m.file+"|"+g); return [{r:m,g,cls:"mparent",head:{kids,closed}},...(closed?[]:vk.map(k=>({r:k,g,cls:"mchild"})))]; };
  if(RVG==="kind"){ Object.keys(RVKINDS).forEach(k=>{ const L=REV.filter(r=>r.kind===k&&ok(r)); if(L.length) out.push({key:k,title:esc(RVKINDS[k]),label:RVKINDS[k],blocks:L.map(r=>[isMin(r)?{r,g:"*",cls:"mparent",head:{kids:kidsOf(r,"*"),closed:true}}:{r,g:r.p||"?"}])}); }); return out; }   /* minutes: their items are listed under their own kinds */
  if(RVG==="source"){ [...new Set(REV.map(r=>r.file))].forEach(file=>{ const L=REV.filter(r=>r.file===file), used=new Set(), blocks=[];
      L.forEach(r=>{ if(isMin(r)){ kidsOf(r,"*").forEach(k=>used.add(k)); const b=minBlock(r,"*"); if(b) blocks.push(b); return; } if(!used.has(r)&&ok(r)) blocks.push([{r,g:"*"}]); });
      if(blocks.length) out.push({key:file,title:revGroupTitle(file,L),label:revGroupTitle(file,L).replace(/<[^>]+>/g,""),blocks}); }); return out; }
  const gs=[...new Set(REV.flatMap(r=>isMin(r)?(r.projects||[r.p]).map(p=>p||"?"):[r.p||"?"]))].sort((a,b)=>a==="?"?-1:b==="?"?1:0);
  gs.forEach(g=>{ const used=new Set(), blocks=[];
    REV.forEach(r=>{ if(isMin(r)){ if(!(r.projects||[r.p]).map(p=>p||"?").includes(g)) return; kidsOf(r,g).forEach(k=>used.add(k)); const b=minBlock(r,g); if(b) blocks.push(b); return; }
      if((r.p||"?")===g&&!used.has(r)&&ok(r)) blocks.push([{r,g}]); });
    if(blocks.length) out.push({key:g,title:g==="?"?"Needs a project":`<a href="#" class="hlink" data-proj="${g}">${esc(pName(g))}</a>`,label:g==="?"?"Needs a project":pName(g),blocks}); });
  return out; }
export const RVORD={age:r=>-(r.age||0),kind:r=>Object.keys(RVKINDS).indexOf(r.kind),due:r=>r.rec.due||"9999"};
/* #177: age is quiet text on every row ("today", "1 day", "12 days"); the stale setting speaks only through one banner. All proposals older
   than it: "All 4 have waited more than 7 days. Oldest first?". Only some: a banner only for those older than twice the setting, and only those rows are marked. */
export const rvStaleDays=()=>+S.staleDays||7;
export const rvAgeText=r=>{ const d=Math.max(0,+r.age||0); return d===0?"today":d===1?"1 day":`${d} days`; };
export const rvOutlier=r=>!r.done&&!rvAllOld()&&(+r.age||0)>2*rvStaleDays();
export const rvAllOld=()=>{ const und=REV.filter(r=>!r.done); return und.length>0&&und.every(r=>r.stale); };
export function rvAgeBanner(und){ if(!und.length) return ""; const th=rvStaleDays(), on=RVO==="age", btn=html`<button type="button" class="btn${rvAllOld()?" primary":""}" id="rvOldest" aria-pressed="${String(on)}">${on?"Oldest first: on":"Oldest first"}</button>`;
  if(rvAllOld()) return html`<div class="rvagebanner" id="rvAgeBanner" role="status"><span><b>All ${und.length} have waited more than ${th} days.</b> Oldest first?</span>${btn}</div>`;
  const o=und.filter(rvOutlier); if(!o.length) return "";
  const mx=Math.max(...o.map(r=>+r.age||0));
  return html`<div class="rvagebanner" id="rvAgeBanner" role="status"><span><b>${o.length===1?`1 has waited ${mx} days.`:`${o.length} have waited more than ${2*th} days.`}</b></span>${btn}</div>`; }
export function rvRender(){ const und=REV.filter(r=>!r.done), shownN=und.filter(r=>rvPasses(r)).length;
  putHTML($("#rvSub"),html`Claude's proposals. ${und.length} waiting`);
  drawReviewFilters(); rvApplied(shownN,und.length); rvRoutineBtn(); putHTML($("#rvHint"),rvHintHtml());
  const G=rvBlocks(); if(RVO&&RVORD[RVO]) G.forEach(g=>g.blocks.sort((a,b)=>{ const x=RVORD[RVO](a[0].r), y=RVORD[RVO](b[0].r); return x<y?-1:x>y?1:0; }));
  let i=0; const anyLive=G.some(g=>g.blocks.some(b=>b.some(o=>!o.r.gone)));
  const groups=html`${G.map(g=>{ const rows=g.blocks.flat(), live=rows.filter(o=>!o.r.done&&!isMin(o.r)), n=rows.filter(o=>!o.r.done).length;
    const all=live.length&&live.every(o=>RHL.has(o.r.n));
    return html`<div class="rgroup"><h2><input type="checkbox" class="rgtick" data-rg="${g.key}" aria-label="Select the rows in ${g.label}" ${raw(all?"checked":"")} ${raw(live.length?"":"disabled")}> ${raw(g.title)} <span class="sub rgc">${n||!rows.some(o=>o.r.gone)?`${n} proposal${n===1?"":"s"}`:"rejected just now"}</span></h2></div><div class="tbl"><table><tbody>${rows.map(o=>raw(o.r.gone?rjGoneRow(o.r,o.g,o.cls):revRow(o.r,i++,o.g,o.cls,o.head)))}</tbody></table></div>`; })}`;   /* BL-315: a greyed row takes no cursor number */
  if(!und.length){ putHTML($("#reviewBody"),html`${rvEmptyHtml()}${G.length?groups:""}`); rvBar(); return; }
  putHTML($("#reviewBody"),anyLive?html`${rvAgeBanner(und)}${groups}`
    :html`<div class="empty"><div class="wempty"><h2>Nothing matches these filters</h2><div class="sub">${und.length} proposal${und.length===1?"":"s"} waiting outside them.</div><div class="wefoot"><button type="button" class="btn primary" id="rvClearF">Clear all filters</button></div></div></div>${groups}`);
  rvBar(); }
export const rvSrcLink=r=>{ if(r.nodraft&&r.tsrc) return ` · <a href="#" class="srclink" data-openfile="${esc(r.tsrc)}">Open source</a>`; /* BL-260: the transcript */ const o=srcParse(r.src); if(!o) return ""; if(o.type==="File") return ` · <a href="#" class="srclink" data-openfile="${esc(o.path)}">Open source</a>`; const a=o.Link?linkAnchor(o.Link,"Open source","srclink"):null; return a?` · ${a}`:""; };
export function rvHintHtml(){ return raw([["J","K","move"],["Shift","J","extend"],["Space","select"],["A","approve"],["R","reject with a reason"],["E","edit"],[MAC?"⌘":"Ctrl","Z","undo"]].map(a=>a.slice(0,-1).map(k=>`<span class="kbd">${k}</span>`).join(" ")+" "+a[a.length-1]).join(" · ")); }
export function rvEmptyHtml(){ const s=shared.RVSTATS, any=s.approved||s.rejected||s.edited;
  return html`<div class="empty rvdone"><h2>Nothing left to review</h2>${any?html`<div class="sub">This session: approved ${s.approved} · rejected ${s.rejected} · edited ${s.edited}</div>`:""}
    <div class="rvdacts">${RVLASTUNDO?html`<button type="button" class="btn" id="rvUndoLast">Undo the last batch</button>`:""}<button type="button" class="btn" data-go="activity">Open Activity</button><button type="button" class="btn" data-ask="sweep">Sweep now</button></div>
    <div class="sub" style="margin-top:14px">${SWEPT==="never"?"Mail and Teams have not been swept yet.":`The last sweep was ${fdText(SWEPT)}.`}${(D.inbox||[]).filter(f=>f.state==="new").length?` Intake has ${(D.inbox||[]).filter(f=>f.state==="new").length} new file${(D.inbox||[]).filter(f=>f.state==="new").length===1?"":"s"}.`:""}</div></div>`; }
/* ── filters: the FilterBar building block (BL-316), as Work's: Kind, Needs and Source each open their own list; the funnel's
   picker holds every field (Project and Age only there) ── */
export function rvBarProps(){ const und=REV.filter(r=>!r.done), main=new Set(["k","nd","src"]);
  const fields=RVFIELDS.map(([k,l,opts,hit])=>{ const set=RVF[k], on=!!set.size, neg=RVNEG.has(k), lab=v=>(opts().find(o=>o[0]===v)||[v,v])[1];
    return {id:k,label:l,main:main.has(k),section:main.has(k)?undefined:"More fields",menuId:`rvf-${k}`,data:{rvf:k},on,selected:set,not:neg,
      button:on?`${l}: ${neg?"not ":""}${set.size<=2?[...set].map(lab).join(", "):set.size+" chosen"}`:l,mark:on?`${neg?"not · ":""}set`:"",
      options:()=>opts().map(([v,ol])=>({value:v,label:ol,count:und.filter(r=>rvPasses(r,k)&&hit(r,new Set([v]))).length}))}; });
  return {fields,
    onSelect:(k,vals)=>{ RVF[k].clear(); vals.forEach(v=>RVF[k].add(v)); rvChanged(); },
    onNot:(k,n)=>{ n?RVNEG.add(k):RVNEG.delete(k); rvChanged(); },
    more:{id:"rvMore",menuId:"rvPick",label:funnelTip(rvfCount()),menuLabel:"Filter the proposals",count:rvfCount(),on:!!(RVF.p.size||RVF.age.size),
      field:RVPK,onField:k=>{ RVPK=k; drawReviewFilters(); },onOpen:()=>{ RVPK=RVF.p.size?"p":RVF.age.size?"age":"p"; },
      result:`Result: ${und.filter(r=>rvPasses(r)).length} of ${und.length} shown`,resultId:"rvResult",doneId:"rvPickDone"}}; }
export function drawReviewFilters(){ const h=$("#rvfilters"); if(h) drawFilterBar(h,rvBarProps()); }
export function rvApplied(shown,total){ const chips=RVFIELDS.filter(f=>RVF[f[0]].size).map(f=>{ const neg=RVNEG.has(f[0]), lab=v=>(f[2]().find(o=>o[0]===v)||[v,v])[1];
    return html`<span class="fchip${neg?" neg":""}">${f[1]}: ${neg?"not ":""}${[...RVF[f[0]]].map(lab).join(", ")}<button data-rvclr="${f[0]}" aria-label="Remove the ${f[1].toLowerCase()} filter">${raw(ic("x"))}</button></span>`; });
  if(RVQ.trim()) chips.push(html`<span class="fchip">Search: “${RVQ.trim()}”<button data-rvclr="q" aria-label="Clear the search">${raw(ic("x"))}</button></span>`);
  putHTML($("#rvapplied"),html`${chips.length?html`${chips}<button class="linkbtn" id="rvClearF">Clear all</button><span class="sp"></span><span class="sub" id="rvcount">Showing ${shown} of ${total}</span>`:""}`); }
export function rvRoutineBtn(){ const n=rvMatching().filter(rvBulkOK).length, b=$("#routineBtn"); putHTML(b,html`${raw(ic("checks"))}Approve routine <span class="sub">(${n})</span>`); b.disabled=!n; b.dataset.tip=(RVFIELDS.some(f=>RVF[f[0]].size)||RVQ.trim()?"Approves the routine proposals the filters show, after a preview.":"Approves every routine proposal, after a preview.")+" Minutes, new decisions and new risks stay for you."; }
export function rvChanged(){ renderReview(); }
/* ── Display: group and order ── */
export function rvDrawDisp(){ putHTML($("#rvDispMenu"),html`<h3><label for="rvGrp">Group by</label></h3><div class="dline"><select id="rvGrp">${[["project","Project"],["source","Source (each meeting or sweep)"],["kind","Kind"]].map(o=>html`<option value="${o[0]}" ${raw(o[0]===RVG?"selected":"")}>${o[1]}</option>`)}</select></div>
  <h3><label for="rvOrd">Order by</label></h3><div class="dline"><select id="rvOrd">${[["","As proposed"],["age","Oldest first"],["kind","Kind"],["due","Due date"]].map(o=>html`<option value="${o[0]}" ${raw(o[0]===RVO?"selected":"")}>${o[1]}</option>`)}</select></div>
  <div class="dfoot"><button type="button" class="linkbtn" id="rvDispReset">Reset</button><span class="sp"></span><button type="button" class="btn primary" id="rvDispDone">Done</button></div>`); }
export function rvDispClose(focus){ const m=$("#rvDispMenu"); m.classList.remove("on"); m.hidden=true; $("#rvDispBtn").setAttribute("aria-expanded","false"); if(focus) $("#rvDispBtn").focus(); }
/* ── the bar ── */
export function rvSel(){ return [...RHL].map(n=>REV.find(r=>r.n===n)).filter(r=>r&&!r.done); }
export const RVSETF=[["p","Project"],["o","Owner"],["due","Due date"],["ws","Workstream"],["ms","Milestone"]];
export function rvSetFields(L){ const items=L.filter(r=>["actions","raid","decisions"].includes(r.kind)), ar=L.every(r=>["actions","raid"].includes(r.kind)), ps=new Set(L.map(r=>r.p)), one=ps.size===1&&[...ps][0];
  const why=f=>!items.length||items.length<L.length?"Only proposed actions, risks, issues and decisions can be changed here":f!=="p"&&!ar?"Only proposed actions and RAID items have this":(f==="ws"||f==="ms")&&!one?"These are in different projects, or have none yet":"";
  return RVSETF.map(([f,l])=>{ const w=why(f); let opts=[];
    if(!w){ if(f==="p") opts=P.map(p=>[p.code,p.name]); else if(f==="o") opts=["TBC",...peopleAll()].map(x=>[x,x]); else if(f==="ws") opts=[["","None"],...wsFor(one).map(x=>[x,x])]; else if(f==="ms") opts=msChoices(one,""); }
    return [f,l,opts,w]; }); }
/* #114: the bar floats at the bottom edge of the window, centred in Review's column, while rows are selected. It is fixed, so it takes no
   room in the list (nothing moves when it appears); the page gets the bar's height as bottom padding so the last row scrolls clear of it. */
export function rvDock(){ const bar=$("#rvbar"), view=$("#v-review"); if(!bar||!view) return;
  if(bar.hidden){ view.classList.remove("rvfloat"); document.documentElement.style.removeProperty("--rvh"); rvWatch(false); return; }
  rvWatch(true); if(view.hidden) return;
  const r=view.getBoundingClientRect(), w=Math.min(view.clientWidth-48,1500);
  bar.style.setProperty("--rvw",`${w}px`); bar.style.setProperty("--rvl",`${Math.round(r.left+(view.clientWidth-w)/2)}px`);
  const h=`${bar.offsetHeight}px`; view.style.setProperty("--rvh",h); document.documentElement.style.setProperty("--rvh",h); view.classList.add("rvfloat"); }
/* Re-dock when Review's column changes size (the sidebar collapsing, the ask creaite panel opening) or the bar re-wraps; watched only while the bar is showing. */
let rvRO=null;
function rvWatch(on){ if(!on){ if(rvRO){ rvRO.disconnect(); rvRO=null; } return; }
  if(rvRO||typeof ResizeObserver==="undefined") return;
  rvRO=new ResizeObserver(()=>rvDock()); const bar=$("#rvbar"), view=$("#v-review"), shell=view&&view.parentElement; [view,shell,bar].forEach(el=>el&&rvRO.observe(el)); }
window.addEventListener("resize",rvDock);
export function rvBar(){ const bar=$("#rvbar"); if(!bar) return; const L=rvSel(); if(!L.length){ bar.hidden=true; rvDock(); $("#bulkApprove").disabled=$("#bulkReject").disabled=true; if(rjMenu.value&&rjMenu.value.anchor===$("#bulkReject")) rjCloseMenu(false); return; }
  const ok=L.filter(rvBulkOK), rej=L.filter(rvRejectOK), left=L.filter(r=>!rvBulkOK(r)), M=rvMatching();
  const groups={project:[],indiv:[],conflict:[]}; left.forEach(r=>groups[rvWhyNot(r)[0]].push(r));
  const part=(k,one,many)=>{ const g=groups[k]; return g.length?html`<span class="rvwhy" tabindex="0" title="${g.map(r=>`${r.rec.t}: ${rvWhyNot(r)[1]}`).join("\n")}">${g.length} ${g.length===1?one:many}</span>`:""; };
  bar.hidden=false; $("#rvCount").textContent=`${L.length} selected${M.length&&L.length<M.length?"":""}`;
  putHTML($("#rvSplit"),html`${[`${ok.length} can be approved together`,part("indiv","needs individual approval","need individual approval"),part("project","needs a project","need a project"),part("conflict","has a conflict","have conflicts")].filter(Boolean).map((x,i)=>i?html` · ${x}`:x)}`);
  const all=$("#rvAll"); all.hidden=L.length>=M.length; all.textContent=`Select all ${M.length}`; all.title="Every undecided proposal the filters show, in collapsed minutes too";
  putHTML($("#bulkApprove"),html`${raw(ic("check"))}Approve (${ok.length})`); $("#bulkApprove").disabled=!ok.length; putHTML($("#bulkReject"),html`${raw(ic("x"))}Reject with a reason <span class="kbd" aria-hidden="true">R</span>`); $("#bulkReject").disabled=!rej.length;   /* BL-315: one menu, for one row or many */
  $("#bulkReject").setAttribute("aria-label",`Reject ${rej.length===1?"1 proposal":rej.length+" proposals"} with a reason`); $("#bulkReject").title=rej.length<L.length?"Minutes, reports and file changes are rejected one at a time":"";
  putHTML($("#rvSet"),html`${rvSetFields(L).map(([f,label,opts,why])=>f==="due"?html`<span class="bkf"><label class="bklab" for="rvDate">${label}</label><span class="dwrap"><input type="text" id="rvDate" data-pick="1" data-date="1" placeholder="DD-MM-YYYY" autocomplete="off" ${raw(why?"disabled":"")} aria-label="Set the due date of ${L.length} proposals" title="${why}"><button type="button" class="dbtn" data-cal="rvDate" ${raw(why?"disabled":"")} aria-label="Choose date">${raw(CALI)}</button></span></span>`
    :html`<span class="bkf"><label class="bklab">${label}<select data-rvset="${f}" ${why?html`disabled aria-disabled="true"`:""} title="${why}"><option value="">Set…</option>${ceOpts(opts).map(o=>html`<option value="${o[0]}">${o[1]}</option>`)}</select></label></span>`)}`);  rvDock(); }
/* ── deciding several: one write per proposal file, one apply, one Undo ── */
export async function rvDecideMany(list,v){ list=list.filter(r=>r&&!r.done); if(!list.length) return {n:0}; if(!await needVault()) return {n:0};
  const byFile=new Map(); list.forEach(r=>{ if(!byFile.has(r.file)) byFile.set(r.file,[]); byFile.get(r.file).push(r); }); const done=[], failed=[];
  for(const [file,rs] of byFile){ try{ await editProposal(file,data=>rs.forEach(r=>setDecision(data,r,v))); done.push(...rs); }catch(e){ failed.push(...rs.map(r=>`#${r.n} (${e.message})`)); } }
  done.forEach(r=>{ CHK.delete(r.n); RHL.delete(r.n); }); shared.RVSTATS[v]=(shared.RVSTATS[v]||0)+done.length;
  const undoFiles=async()=>{ for(const [file,rs] of byFile){ const mine=rs.filter(r=>done.includes(r)); if(mine.length) try{ await editProposal(file,data=>mine.forEach(r=>setDecision(data,r,"pending"))); }catch(e){} } };
  if(viaServer()&&S.autoApply){ done.forEach(r=>r.done=v); refreshAll(); const res=await applyNow(); return {n:done.length,failed,undo:res.ok?()=>undoApply(res.apply_id):null,res}; }
  let undoRecs=[]; const what=`${done.length} proposal${done.length===1?"":"s"} ${v}`;
  apply(what,()=>{ done.forEach(r=>{ r.done=v; if(v==="approved") undoRecs.push(applyProposal(r)); }); },async()=>{ done.forEach(r=>delete r.done); undoRecs.forEach(u=>u()); undoRecs=[]; await undoFiles(); },"You, in Review");
  return {n:done.length,failed,undo:shared.UNDO}; }
export function rvSummary(verb,res,left){ const by={project:0,indiv:0,conflict:0}; left.forEach(r=>by[rvWhyNot(r)[0]]++);
  const parts=[by.project?`${by.project} need${by.project===1?"s":""} a project`:"",by.indiv?`${by.indiv} need${by.indiv===1?"s":""} individual approval`:"",by.conflict?`${by.conflict} ${by.conflict===1?"has a conflict":"have conflicts"}`:"",res.failed&&res.failed.length?`not saved: ${res.failed.join(", ")}`:""].filter(Boolean);
  const text=`${verb} ${res.n}${parts.length?" · "+parts.join(" · "):""}`; RVLASTUNDO=res.undo||null; shared.RVLEFT=left.map(r=>r.file+"|"+r.ref);
  putHTML($("#rvresult"),html`<span><b>${verb} ${res.n}</b>${parts.length?html` <span class="tag warn">partial</span>`:""}${parts.length?" · "+parts.join(" · "):""}</span>${left.length?html`<button type="button" class="linkbtn" id="rvShow">Show them</button>`:""}${res.undo?html`<button type="button" class="linkbtn" id="rvUndo">Undo</button>`:""}`);
  if(res.undo) snack(text,async()=>{ await res.undo(); $("#rvresult").textContent=""; }); else snack(text); }
shared.RVLEFT=[];
export async function rvApproveSelected(confirmed){ const L=rvSel(), ok=L.filter(rvBulkOK), left=L.filter(r=>!rvBulkOK(r)); if(!ok.length){ snack("None of these can be approved together"); return; }
  if(ok.length>shared.RV_MAX&&!confirmed){ rvPreview(ok,left,"Approve the selected",()=>rvApproveSelected(true)); return; }
  const res=await rvDecideMany(ok,"approved"); RHL.clear(); left.forEach(r=>RHL.add(r.n)); rvSyncChk(); renderReview(); rvSummary("Approved",res,left); }
export async function rvRejectSelected(){ const L=rvSel(), rej=L.filter(rvRejectOK), left=L.filter(r=>!rvRejectOK(r)); if(!rej.length) return;
  if(rej.length>shared.RV_MAX&&!await boardAsk({title:`Reject ${rej.length} proposals?`,hint:"Rejecting writes nothing to the tracker; Undo brings them back",clear:true,okText:`Reject ${rej.length}`})) return;
  const res=await rvDecideMany(rej,"rejected"); RHL.clear(); left.forEach(r=>RHL.add(r.n)); rvSyncChk(); renderReview(); rvSummary("Rejected",res,left.map(r=>({...r,why:"Minutes, a report or a file change, rejected on its own"}))); }
export function rvRoutine(){ const M=rvMatching(), ok=M.filter(rvBulkOK), left=M.filter(r=>!rvBulkOK(r)&&!isMin(r)&&r.kind!=="draft"); if(!ok.length){ snack("Nothing routine to approve"); return; }
  rvPreview(ok,M.filter(r=>!rvBulkOK(r)),"Approve all routine",async()=>{ const res=await rvDecideMany(ok,"approved"); renderReview(); rvSummary("Approved",res,left); }); }
/* the preview: counts by project and kind, the items, what is not included and why */
export function rvPreview(ok,left,title,go){ const dlg=$("#rvDlg"), filt=RVFIELDS.some(f=>RVF[f[0]].size)||RVQ.trim(), cnt=(L,f)=>{ const m=new Map(); L.forEach(r=>{ const k=f(r); m.set(k,(m.get(k)||0)+1); }); return [...m].map(([k,n])=>`${k} ${n}`).join(" · "); };
  const by={project:0,indiv:0,conflict:0}; left.forEach(r=>by[rvWhyNot(r)[0]]++);
  putHTML($("#rvDlgBody"),html`<h2 id="rvDlgTitle">Approve ${ok.length} routine proposal${ok.length===1?"":"s"}?</h2><div class="sub">${filt?"What the filters show.":"Every project, every kind."} Applied at once; Undo reverses the batch.</div>
    <div class="rvcnt"><div><b>${ok.length}</b>to approve</div><div><b>${cnt(ok,r=>pName(r.p))}</b>by project</div><div><b>${cnt(ok,r=>kindLabel(r))}</b>by kind</div></div>
    <div class="rvlst" role="list">${ok.map((r,i)=>html`<div role="listitem" ${i>=6?html`class="more" hidden`:""}><span>${r.rec.t??""}</span><span class="sub">${pName(r.p)??""}${rvOwner(r)?" · "+rvOwner(r):""}${r.rec.due?" · "+fd(r.rec.due):""}</span></div>`)}${ok.length>6?html`<div><span class="sub">+ ${ok.length-6} more</span><button type="button" class="linkbtn" id="rvDlgAll">Show all</button></div>`:""}</div>
    ${left.length?html`<div class="rvcnt warnc"><div><b>${left.length}</b>not included: ${[by.indiv?`${by.indiv} individual approval`:"",by.conflict?`${by.conflict} conflict${by.conflict===1?"":"s"}`:"",by.project?`${by.project} need${by.project===1?"s":""} a project`:""].filter(Boolean).join(" · ")}</div></div>`:""}`);
  $("#rvDlgOk").textContent=`Approve ${ok.length}`; let fired=false;
  $("#rvDlgOk").onclick=()=>{ if(fired) return; fired=true; dlg.close(); go(); }; $("#rvDlgCancel").onclick=()=>dlg.close();
  openDialog(dlg,{focus:"#rvDlgOk"}); }
/* ── mass change before approval: through editProposal, tagged edited, checked one by one, one Undo ── */
export function rvCheck(r,f,v){ if(f==="p") return P.some(p=>p.code===v)?"":"not a project";
  if(f==="o") return v==="TBC"||peopleAll().includes(v)?"":"not in the people register";
  if(f==="due"){ if(v&&v<TODAY) return "a due date can't be in the past"; return ""; }
  if(f==="ws") return !r.p?"needs a project first":v===""||wsFor(r.p).includes(v)?"":`not a workstream of ${pName(r.p)}`;
  if(f==="ms") return !r.p?"needs a project first":v===""||msChoices(r.p,"").some(m=>m[0]===v)?"":`not a milestone of ${pName(r.p)}`; return ""; }
export async function rvSet(f,v){ const L=rvSel().filter(r=>["actions","raid","decisions"].includes(r.kind)); if(!L.length||!await needVault()) return;
  const ok=[], left=[]; L.forEach(r=>{ const fld=f==="o"&&r.kind==="decisions"?"by":f, err=rvCheck(r,f,v); if(err) left.push(`#${r.n} ${r.rec.t.slice(0,40)} (${err})`); else if(String((f==="p"?r.p:r.rec[fld])??"")!==String(v??"")) ok.push({r,fld}); });
  if(!ok.length){ snack(left.length?`Nothing changed. Left out: ${left.join("; ")}`:"Nothing changed: they already have that"); return; }
  const before=ok.map(({r})=>({r,p:r.p,rec:{...r.rec},why:r.why,edited:r.edited})), byFile=new Map(); ok.forEach(o=>{ if(!byFile.has(o.r.file)) byFile.set(o.r.file,[]); byFile.get(o.r.file).push(o); });
  const prev={};
  try{ for(const [file,os] of byFile) await editProposal(file,data=>os.forEach(({r,fld})=>{ const it=(data.items||[]).find(i=>i.n===r.ref); if(!it||it.applied) throw new Error("already applied");
      prev[file+"|"+r.ref]={values:JSON.parse(JSON.stringify(it.values||{})),match:it.match,edited_in:it.edited_in,ap:"as_proposed" in it?it.as_proposed:undefined};   /* BL-232: Undo puts as_proposed back too */
      const vals=toDb(r.kind,{[fld]:v}); if(f==="p"){ const was=it.values&&it.values.project; it.values=Object.assign(it.values||{},{project:v}); it.match="strong"; if(it.values.milestone&&!String(it.values.milestone).startsWith(v+"-M-")) it.values.milestone=null;
        if(it.values.workstream&&!wsFor(v).some(w=>w.toLowerCase()===String(it.values.workstream).toLowerCase())) it.values.workstream=null; if(was&&was!==v){ if(it.moved_from===v) delete it.moved_from; else it.moved_from=it.moved_from||was; } }   /* BL-200: as review.py assign */
      else it.values=Object.assign(it.values||{},vals); it.edited_in="dashboard"; })); }catch(e){ snack("Not saved: "+e.message); return; }
  ok.forEach(({r,fld})=>{ if(f==="p"){ r.p=v; r.why="Project set in Review"; if(r.rec.ms&&!String(r.rec.ms).startsWith(v+"-M-")) r.rec.ms=null; if(r.rec.ws&&!wsFor(v).some(w=>w.toLowerCase()===String(r.rec.ws).toLowerCase())) r.rec.ws=""; } else r.rec[fld]=v; r.edited=true; }); shared.RVSTATS.edited+=ok.length;
  const undo=async()=>{ for(const [file,os] of byFile) try{ await editProposal(file,data=>os.forEach(({r})=>{ const it=(data.items||[]).find(i=>i.n===r.ref), p=prev[file+"|"+r.ref]; if(it&&p&&!it.applied){ it.values=p.values; it.match=p.match; if(p.edited_in===undefined) delete it.edited_in; else it.edited_in=p.edited_in; if(p.ap===undefined) delete it.as_proposed; else it.as_proposed=p.ap; /* BL-232 */ } })); }catch(e){}
    before.forEach(b=>{ b.r.p=b.p; b.r.rec=b.rec; b.r.why=b.why; b.r.edited=b.edited; }); renderReview(); };
  const lab={p:"Project",o:"Owner",due:"Due date",ws:"Workstream",ms:"Milestone",pr:"Priority",st:"Status",imp:"Impact",lik:"Likelihood"}[f], shown=f==="p"?pName(v):f==="due"?(v?fd(v):"none"):f==="ms"?(v?msLabel(v):"none"):(v||"none");
  renderReview(); snack(`${lab} set to ${shown} on ${ok.length} proposal${ok.length===1?"":"s"}${left.length?`. Left out: ${left.join("; ")}`:""}`,undo);
  if(f==="p") rvLearnCard(ok.map(o=>o.r),v); }
/* one learning card per bulk project choice: one signal per distinct sender (FR-14), never one per item */
export function rvLearnCard(L,code){ const by=new Map(); L.forEach(r=>{ const s=learnable(r); if(!s) return; const k=s.kind+"|"+s.value; if(!by.has(k)) by.set(k,{s,n:0}); by.get(k).n++; }); if(!by.size) return;
  putHTML($("#rvresult"),html`<div class="rvlearn"><b>Remember this?</b> ${[...by.values()].map(({s,n})=>html`<div>${s.kind==="domain"?"Mail from":s.kind==="sender"?"Mail from":"Items with"} <b>${s.value}</b> ${n>1?`(${n} of these ${L.length}) `:""}usually belong to ${pName(code)}. <button type="button" class="mini primary" data-rvlearn="${s.kind}|${s.value}" data-code="${code}">Remember</button></div>`)}<button type="button" class="mini" id="rvLearnNo">Not now</button></div>`); }
export function rvDate(){ const i=$("#rvDate"); if(!i) return; const v=i.value.trim(); let out=""; if(v){ const t=DDATE.test(v)?toIso(v):"", d=t?new Date(t+"T12:00:00"):null; if(!d||isNaN(d)||d.toISOString().slice(0,10)!==t){ snack(DDATE.test(v)?"That isn't a real date.":"Not a date creaite knows. "+DATE_HELP); return; } out=t; } rvSet("due",out); }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootReview0061(){
document.addEventListener("click",e=>{ if(!e.target.closest("#v-review")) return;
  const c=e.target.closest("[data-rvclr]"); if(c){ const k=c.dataset.rvclr; if(k==="q"){ RVQ=""; $("#rvQ").value=""; } else { RVF[k].clear(); RVNEG.delete(k); } rvChanged(); return; }
  if(e.target.id==="rvClearF"){ Object.values(RVF).forEach(s=>s.clear()); RVNEG.clear(); RVQ=""; $("#rvQ").value=""; rvChanged(); return; }
  });
$("#rvQ").addEventListener("input",e=>{ RVQ=e.target.value; rvChanged(); });
$("#rvQ").addEventListener("keydown",e=>{ if(e.key==="Escape"&&RVQ){ e.preventDefault(); e.stopPropagation(); RVQ=""; e.target.value=""; rvChanged(); } });
$("#rvDispBtn").addEventListener("click",e=>{ e.stopPropagation(); const m=$("#rvDispMenu"); if(m.classList.contains("on")){ rvDispClose(true); return; } rvDrawDisp(); m.hidden=false; m.classList.add("on"); $("#rvDispBtn").setAttribute("aria-expanded","true"); $("#rvGrp").focus(); });
document.addEventListener("click",e=>{ if(!e.target.closest("#rvOldest")) return; RVO=RVO==="age"?"":"age"; rvChanged(); $("#rvOldest")?.focus(); });
$("#rvDispMenu").addEventListener("click",e=>{ e.stopPropagation(); if(e.target.id==="rvDispDone") rvDispClose(true); if(e.target.id==="rvDispReset"){ RVG="project"; RVO=""; rvDrawDisp(); rvChanged(); } });
$("#rvDispMenu").addEventListener("change",e=>{ if(e.target.id==="rvGrp") RVG=e.target.value; if(e.target.id==="rvOrd") RVO=e.target.value; rvChanged(); });
$("#rvDispMenu").addEventListener("keydown",e=>{ if(e.key==="Escape"){ e.preventDefault(); e.stopPropagation(); rvDispClose(true); } });
document.addEventListener("click",e=>{ if(!e.target.closest(".rvdisp")&&$("#rvDispMenu").classList.contains("on")) rvDispClose(false); });
document.addEventListener("click",e=>{ if(e.target.id==="rvDlgAll"){ $$("#rvDlg .rvlst .more").forEach(x=>x.hidden=false); e.target.parentElement.remove(); } });
document.addEventListener("click",e=>{ const l=e.target.closest("[data-rvlearn]"); if(l){ const [kind,...v]=l.dataset.rvlearn.split("|"); learnSignal(l.dataset.code,kind,v.join("|")); l.closest("div").remove(); if(!$("#rvresult [data-rvlearn]")) $("#rvresult").textContent=""; return; }
  if(e.target.id==="rvLearnNo") $("#rvresult").textContent="";
  if(e.target.id==="rvShow"){ RHL.clear(); REV.filter(r=>shared.RVLEFT.includes(r.file+"|"+r.ref)).forEach(r=>RHL.add(r.n)); rvSyncChk(); renderReview(); $("#reviewBody tr.hl")?.scrollIntoView({block:"nearest"}); }
  if(e.target.id==="rvUndo"||e.target.id==="rvUndoLast"){ const u=RVLASTUNDO; RVLASTUNDO=null; $("#rvresult").textContent=""; if(u) u(); } });
document.addEventListener("change",e=>{ const s=e.target.closest&&e.target.closest("#rvbar select[data-rvset]"); if(!s||s.selectedIndex===0) return; rvSet(s.dataset.rvset,s.value); });
document.addEventListener("input",e=>{ if(e.target.id==="rvDate"&&!(e instanceof InputEvent)) rvDate(); });
document.addEventListener("keydown",e=>{ if(e.target.id==="rvDate"&&e.key==="Enter"){ e.preventDefault(); rvDate(); } });
$("#bulkApprove").onclick=()=>rvApproveSelected();
$("#bulkReject").onclick=()=>{ const L=rvSel().filter(rvRejectOK); if(L.length) rjMenuFor(L,$("#bulkReject")); };   /* BL-315 */
$("#routineBtn").onclick=()=>rvRoutine();
$("#rvClear").onclick=()=>{ RHL.clear(); CHK.clear(); renderReview(); };
$("#rvAll").onclick=()=>{ rvMatching().forEach(r=>RHL.add(r.n)); rvSyncChk(); renderReview(); };
/* a group's tick: its visible, undecided rows */
document.addEventListener("change",e=>{ const t=e.target.closest&&e.target.closest("#reviewBody .rgtick"); if(!t) return; const rows=[...t.closest(".rgroup").nextElementSibling.querySelectorAll("tr[data-n]")].map(tr=>REV.find(r=>r.n===+tr.dataset.n)).filter(r=>r&&!r.done&&!isMin(r));
  rows.forEach(r=>t.checked?RHL.add(r.n):RHL.delete(r.n)); rvSyncChk(); renderReview(); $(`#reviewBody .rgtick[data-rg="${CSS.escape(t.dataset.rg)}"]`)?.focus(); });
}
/* ── auto-advance: after a decision on a row, the cursor moves to the next undecided one ── */
export function rvAdvance(n){ if(S.rvAdvance===false) return; const trs=$$("#reviewBody tr[data-n]"), i=trs.findIndex(t=>+t.dataset.n===n); if(i<0) return;
  const nx=trs.slice(i+1).concat(trs.slice(0,i)).find(t=>{ const r=REV.find(x=>x.n===+t.dataset.n); return r&&!r.done; }); if(!nx) return;
  shared.RSEL=+nx.dataset.ri; RHL.clear(); rvSyncChk(); rvPaint(); nx.scrollIntoView({block:"nearest"}); }
export let RVINBATCH=false;
/* a reload renumbers the proposals (review.py's order): the selection and the cursor follow them by file and item, not by number */
export const rvKey=r=>r.file+"|"+r.ref;
/* ===== end BL-133 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootReview0063(){
/* the keys: Shift+J/K extends, X is Space, Cmd/Ctrl+A selects all shown, Cmd/Ctrl+Z undoes the last decision or batch */
document.addEventListener("keydown",e=>{ if(shared.VIEW!=="review"||typing()||e.target.closest&&e.target.closest("dialog,.ddmenu")) return; const trs=$$("#reviewBody tr[data-n]");
  if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==="z"){ if(shared.UNDO){ e.preventDefault(); const u=shared.UNDO; shared.UNDO=null; hideSnack(); $("#rvresult").textContent=""; u(); } return; }
  if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==="a"){ e.preventDefault(); rvMatching().forEach(r=>RHL.add(r.n)); rvSyncChk(); renderReview(); return; }
  if(e.shiftKey&&!e.metaKey&&!e.ctrlKey&&(e.key==="J"||e.key==="K")&&trs.length){ e.preventDefault(); e.stopImmediatePropagation(); const cur=trs[shared.RSEL]?+trs[shared.RSEL].dataset.n:null; if(cur!=null&&shared.RVA==null) shared.RVA=cur;
    shared.RSEL=Math.max(0,Math.min(trs.length-1,shared.RSEL+(e.key==="J"?1:-1))); const order=trs.map(t=>+t.dataset.n), a=order.indexOf(shared.RVA), b=shared.RSEL; RHL.clear(); order.slice(Math.min(a<0?b:a,b),Math.max(a<0?b:a,b)+1).forEach(n=>RHL.add(n)); rvSyncChk(); rvPaint(); trs[shared.RSEL].scrollIntoView({block:"nearest"}); } },true);
document.addEventListener("click",e=>{ const b=e.target.closest("#reviewBody [data-act]"); if(!b) return; const n=+b.closest("tr[data-n]").dataset.n; if(b.dataset.act==="a"||b.dataset.act==="r") shared.RSEL=+b.closest("tr").dataset.ri; },true);
}
/* ===== BL-133 stage B (sprint-work-views) =====
   Reject with a reason: the arrow beside Reject (a row's, and the bar's) or Shift+R opens Duplicate of <the possible duplicate>,
   Not mine to track, Not an action and Other; plain R still rejects at once. The reason (and the item a duplicate repeats) is
   written into the proposal (reject_reason, duplicate_of); the apply stores it in `rejected` and Activity shows it. A possible
   duplicate (build_dashboard.duplicate_hint: same project and type, open, token overlap ≥ review.duplicate_overlap) is tagged on
   the row and named in the panel, with Reject as duplicate. Nothing is merged and nothing is blocked beyond the fingerprint. */
export const RVREASON=new Map();                         /* n → {reason, dup} for the next rejection written */
export const RVWHY=[["Not mine to track"],["Not an action"]];
/* the panel names the possible duplicate */
/* ===== end BL-133 stage B ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootReview0064(){
document.addEventListener("click",e=>{
  const b=e.target.closest("#reviewBody [data-act=rr]"); if(b){ e.stopPropagation(); const r=REV.find(x=>x.n===+b.closest("tr[data-n]").dataset.n); if(r&&!r.done){ shared.RSEL=+b.closest("tr").dataset.ri; rjMenuFor(rjWith(r),b); } return; }
  const d=e.target.closest("[data-rvdup]"); if(d){ e.stopPropagation(); const r=REV.find(x=>x.n===+d.dataset.rvdup); if(!r||r.done) return; closePanel(); rjReject([r],{reason:"Duplicate",dup:r.dup.id}); } },true);
/* Shift+R: the reason menu for the cursor row (or the selection, when there is one) */
document.addEventListener("keydown",e=>{ if(shared.VIEW!=="review"||typing()||e.metaKey||e.ctrlKey||!(e.shiftKey&&e.key==="R")||e.target.closest&&e.target.closest("dialog,[role=menu]")) return; e.preventDefault(); e.stopImmediatePropagation();
  rjKey315(); },true);
}
/* ===== BL-221 (sprint-drafts-extraction) ===== "Looks like": a proposal that repeats an item already in the tracker. Staging marks it
   (extraction.py: words, owner and workstream, plain code; the skill judges a close pair), and build_dashboard gives the row its `dup`:
   the item, where it is (same project, or another project's name), open or closed, and "Very likely" or "Possible", never a percentage.
   The row says "Looks like ORX-A-021 (same project, open) · Very likely"; the proposal's peek adds Compare (the two side by side, with
   the new source), Merge as an update (review.py merge through /api/review/repeat: any new date, latest update or response; nothing new
   rejects it as the duplicate), Keep as new (the mark goes) and Reject as a duplicate (BL-133's path, so the reason is recorded).
   Merge is offered only for an open item in the same project; across projects or onto a closed item it is Keep or Reject. */
export const llWhere=d=>`${d.same===false?pName(d.project):"same project"}, ${d.state||"open"}`;
export function llTag(r){ const d=r.dup; return ` <span class="tag stale dupt" title="${esc(d.t)}">Looks like ${esc(d.id)} (${esc(llWhere(d))}) · ${esc(d.strength||"Possible")}</span>`; }
export function llNoteHtml(r){ const d=r.dup, merge=d.staged&&d.same!==false&&d.state!=="closed";
  return `<div class="cmnote rvdupnote">Looks like <a href="#" data-open="${r.kind}:${esc(d.id)}">${esc(d.id)}</a> (${esc(llWhere(d))}) · ${esc(d.strength||"Possible")}: ${esc(d.t)}<div class="llacts"><button type="button" class="mini" data-rvll="cmp:${r.n}">Compare</button>${merge?`<button type="button" class="mini ok" data-rvll="merge:${r.n}">Merge as an update to ${esc(d.id)}</button>`:""}${d.staged?`<button type="button" class="mini" data-rvll="keep:${r.n}">Keep as new</button>`:""}<button type="button" class="mini no" data-rvdup="${r.n}">Reject as duplicate of ${esc(d.id)}</button></div></div>`; }
export const LLF=[["t","What"],["o","Owner"],["due","Due"],["ws","Workstream"],["st","Status"],["src","Source"]];
export function llCompare(r){ const d=r.dup, x=REC(r.kind,d.id)||{t:d.t}, dlg=$("#llDlg"), body=$("#llRows");
  $("#llNew").textContent=`Proposed (#${r.n})`; $("#llOld").textContent=`${d.id} (${llWhere(d)})`; body.replaceChildren();
  const mine={...r.rec,o:r.rec.o||r.rec.by,src:fdText(srcShort(r.src))}, theirs={...x,o:x.o||x.by,src:fdText(srcShort(x.src||""))};
  LLF.forEach(([f,lab])=>{ const a=mine[f], b=theirs[f]; if(!a&&!b) return; const tr=document.createElement("tr"), th=document.createElement("th"); th.scope="row"; th.textContent=lab; tr.append(th);
    [a,b].forEach(v=>{ const td=document.createElement("td"); td.textContent=f==="due"?(fd(v)||"—"):String(v||"—"); if(f!=="t"&&String(a||"")!==String(b||"")) td.className="lldiff"; tr.append(td); }); body.append(tr); });
  $("#llMerge").hidden=!(d.staged&&d.same!==false&&d.state!=="closed"); $("#llMerge").textContent=`Merge as an update to ${d.id}`; $("#llKeep").hidden=!d.staged; dlg.dataset.n=r.n; openDialog(dlg,{focus:"#llClose"}); }
export async function llAct(how,r){ if(!r||r.done) return; if(!viaServer()){ snack(`${how==="merge"?"Merging":"Keeping it as new"} needs the live server; or say “${how==="merge"?"merge":"keep-new"} ${r.n}” in Claude Code (review)`); return; }
  const res=await api("/api/review/repeat",{file:r.file,ref:r.ref,how}); snack(oneLine(res.message)||(res.ok?"Done":"Not changed")); if(res.ok){ closePanel(); await reloadData(); } }
/* ===== end BL-221 ===== */
/* ===== BL-297 D (v19-review-picker) ===== "Update an existing item instead": any pending new action, RAID item or decision with a
   project can be pointed at an open item of its project and kind, whether or not Looks like marked one. The proposal's peek has the
   button (beside the Looks like note, when there is one) and the row's right-click menu the same command. It asks the live server
   for the candidates (/api/review/candidates: review.py ranks them, the marked item first, then by BL-297 B's signals; strength in
   words, never a percentage) and opens the Picker block (openPicker: a listbox, search over seven, ↑ ↓ Home End, Enter, Esc back to the
   button). Choosing one retargets the proposal (/api/review/retarget: it becomes an update carrying its date and latest update or
   response, as Merge; with nothing new it is rejected as its duplicate). The message offers Undo (review.py unmerge, by file and
   item, so it works after either). Nothing reaches the tracker until the update is approved and applied. */
export const RTKINDS={actions:"action",raid:"risk or issue",decisions:"decision"};
export const rtOK=r=>!!r&&!r.done&&r.op==="new"&&!!r.p&&r.kind in RTKINDS;
export function rtNoteHtml(r){ if(!rtOK(r)) return "";
  return String(html`<div class="rtline"><button type="button" class="mini" data-rvrt="${r.n}" aria-haspopup="listbox" aria-expanded="false">${raw(ic("refresh"))}Update an existing item instead</button></div>`); }
/** what the picker says under each candidate: the strength and why, its owner and due date */
export function rtHint(c){ const s=c.strength?(c.why?`${c.strength}: ${c.why}`:c.strength):"";
  return [c.marked?"Looks like":"",s,c.owner||"",c.due?`Due ${fd(c.due)}`:""].filter(Boolean).join(" · "); }
export async function rtOpen(anchor,r){ if(!rtOK(r)) return;
  if(!viaServer()){ snack(`Updating an existing item instead needs the live server; or say “${r.n} is an update to <ID>” in Claude Code (review)`); return; }
  anchor.setAttribute("aria-busy","true"); const res=await api("/api/review/candidates",{file:r.file,ref:r.ref}); anchor.removeAttribute("aria-busy");
  if(!res||!res.ok){ snack(oneLine(res&&res.message)||"Couldn't list the items"); return; }
  const L=res.items||[]; if(!L.length){ snack(`No open ${RTKINDS[r.kind]} in ${pName(r.p)} for it to update`); return; }
  if(!anchor.isConnected){   /* the list or the peek was drawn again while the server answered: open on the new one, never silently not at all */
    const tr=document.querySelector(`#reviewBody tr[data-n="${r.n}"]`); anchor=document.querySelector(`[data-rvrt="${r.n}"]`)||(tr&&(tr.querySelector('[data-act="e"]')||tr)); if(!anchor) return; }
  openPicker(anchor,{role:"listbox",search:L.length>7,label:`Update which ${RTKINDS[r.kind]} instead`,options:L.map(c=>({v:c.id,label:`${c.id} · ${c.t}`,hint:rtHint(c)})),onPick:v=>rtGo(r,v)}); }
export async function rtGo(r,id){ const at={file:r.file,ref:r.ref};
  const res=await api("/api/review/retarget",{...at,id}); if(!res||!res.ok){ snack(oneLine(res&&res.message)||"Not changed"); return; }
  if(shared.CUR&&shared.CUR.mode==="proposal"&&shared.CUR.n===r.n) closePanel(); await reloadData();
  const dup=/duplicate/i.test(res.message||"");
  snack(dup?`Rejected as a duplicate of ${id}: it carried nothing new`:`Now an update to ${id}`,async()=>{ const back=await api("/api/review/retarget",{...at,undo:true});
    snack(back&&back.ok?"Back to a new item, as it was proposed":oneLine(back&&back.message)||"Not undone"); if(back&&back.ok) await reloadData(); }); }
/* ===== end BL-297 D ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootReview0065(){
document.addEventListener("click",e=>{ const b=e.target.closest&&e.target.closest("[data-rvrt]"); if(!b) return; e.preventDefault(); e.stopPropagation();
  const r=REV.find(x=>x.n===+b.dataset.rvrt); if(pickerOpenFor(b)){ closePicker(); return; } rtOpen(b,r); },true);   /* BL-297 D */
document.addEventListener("click",e=>{ const b=e.target.closest("[data-rvll]"); if(!b) return; e.preventDefault(); e.stopPropagation();
  const [how,n]=b.dataset.rvll.split(":"), r=REV.find(x=>x.n===+n); if(!r||!rvDup(r)) return; if(how==="cmp") llCompare(r); else llAct(how,r); },true);
$("#llDlg").addEventListener("click",e=>{ const dlg=$("#llDlg"), r=REV.find(x=>x.n===+dlg.dataset.n); if(e.target.id==="llClose") dlg.close();
  else if(e.target.id==="llMerge"){ dlg.close(); llAct("merge",r); } else if(e.target.id==="llKeep"){ dlg.close(); llAct("keep",r); } });
}
/* ===== BL-218 (sprint-drafts-extraction) ===== "Probably done": a closing update the sweep or the minutes staged because a sent mail, a
   reply, a Teams message or a meeting passage shows the item finished. Its row leads with the strength in a tag ("Looks done"; "Maybe
   done" says why; "Not done" re-dates it), then the evidence ("Mail 09-10-2026 15:02 by Sara Example: “attached the SOW”") beside the
   item's change, and the source opens as any row's does. Approve closes it; Reject with a reason (BL-133) records why, which the
   extraction reads next time. It is a closing update, so it is never covered by Approve routine (review.individual_only). */
export function dnHtml(r){ const d=r.dn, cls=d.strength==="Looks done"?"dn ok":d.strength==="Not done"?"dn warn":"dn";
  return `<span class="tag ${cls}">${esc(d.strength)}</span> <span class="dnev">${esc(d.ev)}</span>${d.reason?` <span class="sub">(${esc(d.reason)})</span>`:""}<br>`; }
/* ===== end BL-218 ===== */

/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootReview0067(){
document.addEventListener("click",e=>{ const a=e.target.closest("[data-appr]"); if(a){ e.stopPropagation(); decide(+a.dataset.appr,"approved"); return; } const o=e.target.closest("[data-revopen]"); if(o&&!e.target.closest("[data-appr]")){ go("review"); openProposal(+o.dataset.revopen); } });
}
/* ===== BL-200 (sprint-review-work) ===== change the project in Review: one pending item, or a whole set of minutes.
   A Project button on each proposed action, RAID item or decision (with Edit, beside Approve) opens a menu of the active projects;
   picking one moves the item through the live server (/api/review/assign, review.py assign: the old project's milestone and
   workstream are cleared, the match becomes strong, the item stays pending as Alan's edit). An update proposal names one tracker
   row, so it has no Project button. On the minutes entry, Project asks which project's items to move when the minutes span
   several, then where to, then shows the result before anything changes ("Move 9 items from Example Programme to DEF"); items
   already moved on their own are offered (move all, or leave those), and update items are named as staying. The minutes' filing
   follows (review.py rebuilds file_ops and projects); nothing moves on disk until the minutes are approved and applied. In the
   peek, a proposal's Project is a chip beside Owner and Due (held until Save, as its other fields are). Undo moves it back. */
export const rvActive=()=>P.filter(p=>p.active!==false);
/* BL-316: the project menus are the Menu block's (openMenu), opened from the row's Move button */
export function rvMoveTo(b,r){ openMenu(b,{label:"Move to project",id:"rvMoveTo",items:rvActive().map(p=>({id:p.code,name:p.name,icon:"projects",disabled:p.code===r.p,line:p.code===r.p?"Its project now":""})),onPick:v=>rvMoveItem(r,v)}); }
export async function rvMoveItem(r,code,quiet){ const was=r.p;
  if(!viaServer()){ if(!await needVault()) return false;   /* without the server: the same change, made in the proposal by the page */
    try{ await editProposal(r.file,data=>{ const it=(data.items||[]).find(i=>i.n===r.ref); if(!it||it.applied||it.op!=="new") throw new Error("that proposal can't be moved"); const /** @type {any} */ v=it.values=it.values||{};
      v.project=code; if(v.milestone&&!String(v.milestone).startsWith(code+"-M-")) v.milestone=null; if(v.workstream&&!wsFor(code).some(w=>w.toLowerCase()===String(v.workstream).toLowerCase())) v.workstream=null;
      it.match="strong"; if(it.moved_from===code) delete it.moved_from; else if(was&&was!==code) it.moved_from=it.moved_from||was; it.edited_in="review"; }); }
    catch(e){ snack("Not moved: "+e.message); return false; }
    r.p=code; r.edited=true; refreshAll();
    if(!quiet) snack(`Moved to ${pName(code)} — still waiting for review`,was&&was!==code?async()=>{ if(await rvMoveItem(r,was,true)) snack(`Moved back to ${pName(was)}`); }:null);   /* BL-316: Undo, as with the server */
    return true; }
  const keep=was||quiet?null:await rvItemState(r);   /* BL-316: an item with no project yet goes back to none, as it was */
  const res=await api("/api/review/assign",{file:r.file,ref:r.ref,code}); if(!res.ok){ snack(oneLine(res.message)||"Not moved"); return false; }
  await reloadData(); if(quiet) return true; const sig=learnable(r);
  if(!was&&!sig){ snack(`Moved to ${pName(code)} — still waiting for review`,keep?async()=>{ try{ await editProposal(r.file,data=>{ const it=(data.items||[]).find(i=>i.n===r.ref); if(!it||it.applied) throw new Error("it has been decided since");
      it.values={...(it.values||{}),...keep.values}; ["match","moved_from","edited_in"].forEach(f=>{ if(keep[f]===undefined) delete it[f]; else it[f]=keep[f]; }); }); }
    catch(e){ snack("Not moved back: "+e.message); return; } await reloadData(); snack("Moved back: no project yet"); }:null); return true; }
  if(sig) snack(`Moved to ${pName(code)} — still waiting for review`,()=>learnSignal(code,sig.kind,sig.value),`Remember ${sig.value}`);   /* BL-28: the signal is offered for the new project */
  else snack(`Moved to ${pName(code)} — still waiting for review`,was?async()=>{ const back=REV.find(x=>x.file===r.file&&x.ref===r.ref&&!x.done); if(back) await rvMoveItem(back,was,true); snack(`Moved back to ${pName(was)}`); }:null);
  return true; }
/** a pending item's project fields as its proposal holds them, for Undo (null when it can't be read) */
export async function rvItemState(r){ try{ const data=JSON.parse(await shared.VW.read("system/staging/"+r.file)), it=(data.items||[]).find(i=>i.n===r.ref); if(!it) return null;
  const v=it.values||{}; return {values:{project:v.project??null,milestone:v.milestone??null,workstream:v.workstream??null},match:it.match,moved_from:it.moved_from,edited_in:it.edited_in}; }catch(e){ return null; } }
export function rvMoveMinutes(b,r,g){ if(!viaServer()){ snack(`Moving minutes needs the live server, which refiles them; or say “minutes ${r.n} is DEF” in Claude Code`); return; }
  const projs=(r.projects||[r.p]).filter(Boolean);
  const to=frm=>openMenu(b,{label:`Move ${pName(frm)}'s items to`,id:"rvMoveTo",items:rvActive().filter(p=>p.code!==frm).map(p=>({id:p.code,name:p.name,icon:"projects",line:projs.includes(p.code)?"These minutes are filed here too":""})),onPick:v=>rvMovePreview(b,r,frm,v)});
  // @ts-expect-error TS2362: true and false subtract as 1 and 0 (this item's project first)
  if(projs.length>1){ const order=[...projs].sort((x,y)=>(y===g)-(x===g)); openMenu(b,{label:"These minutes span several projects: move which project's items?",id:"rvMoveTo",items:order.map(c=>({id:c,name:pName(c),icon:"projects",line:`${plur(kidsOf(r,c).filter(k=>!k.done).length,"item")}, and its copy of the minutes`})),onPick:v=>setTimeout(()=>to(v),0)}); }
  else to(projs[0]); }
/* BL-316: the preview is Review's confirmation dialog (#rvDlg, the Dialog block), as a large approval's is */
export async function rvMovePreview(b,r,frm,code,moved="leave"){ const res=await api("/api/review/assign",{file:r.file,ref:r.ref,code,from:frm,moved,dry_run:true});
  if(!res.ok||!res.preview){ snack(oneLine(res.message)||"Can't move these minutes"); return; } const pv=res.preview, dlg=$("#rvDlg");
  putHTML($("#rvDlgBody"),html`<h2 id="rvDlgTitle" class="rvmv-h">${pv.headline}</h2>
    <p class="sub">The minutes and transcript will be filed in ${pName(code)}'s folders when the minutes are approved. Nothing changes in the tracker until then.</p>
    ${pv.alone?html`<fieldset class="rvmv-ch"><legend>${pv.alone} item${pv.alone===1?" was":"s were"} moved on ${pv.alone===1?"its":"their"} own before</legend><label><input type="radio" name="rvmvA" value="leave" ${raw(moved!=="all"?"checked":"")}> Leave ${pv.alone===1?"it":"those"} where ${pv.alone===1?"it is":"they are"}</label><label><input type="radio" name="rvmvA" value="all" ${raw(moved==="all"?"checked":"")}> Move all</label></fieldset>`:""}
    ${(pv.updates||[]).length?html`<p class="sub">${pv.updates.join(", ")} ${pv.updates.length===1?"is an update":"are updates"} to ${pv.updates.length===1?"an item":"items"} already in the tracker, so ${pv.updates.length===1?"it stays":"they stay"} with ${pName(frm)}.</p>`:""}`);
  dlg.classList.add("rvmvdlg"); $("#rvDlgOk").textContent="Move"; $("#rvDlgBody").onchange=e=>{ if(e.target.name==="rvmvA") rvMovePreview(b,r,frm,code,e.target.value); };
  dlg.addEventListener("close",()=>{ dlg.classList.remove("rvmvdlg"); $("#rvDlgBody").onchange=null; },{once:true});
  let fired=false; $("#rvDlgCancel").onclick=()=>dlg.close();
  $("#rvDlgOk").onclick=async()=>{ if(fired) return; fired=true; dlg.close(); const out=await api("/api/review/assign",{file:r.file,ref:r.ref,code,from:frm,moved});
    if(!out.ok){ snack(oneLine(out.message)||"Not moved"); return; } await reloadData();
    const undo=pv.projects.includes(code)?null:async()=>{ const m=REV.find(x=>x.file===r.file&&x.ref==="meeting"&&!x.done); if(!m) return;
      const back=await api("/api/review/assign",{file:r.file,ref:"meeting",code:frm,from:code,moved:"all"}); snack(back.ok?`Moved back to ${pName(frm)}`:oneLine(back.message)||"Not moved back"); await reloadData(); };
    snack(`${pv.headline.replace(/^Move/,"Moved")} — the minutes go with them`,undo); };
  openDialog(dlg,{focus:"#rvDlgOk"}); }
/* ===== end BL-200 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootReview0193(){
document.addEventListener("click",e=>{ const b=e.target.closest&&e.target.closest('#reviewBody [data-act="pj"]'); if(!b) return; e.stopPropagation(); e.preventDefault();
  const tr=b.closest("tr[data-n]"), r=REV.find(x=>x.n===+tr.dataset.n); if(!rvMovable(r)) return; shared.RSEL=+tr.dataset.ri;
  if(menuOpenFor(b)){ closeMenu(); return; } isMin(r)?rvMoveMinutes(b,r,tr.dataset.g):rvMoveTo(b,r); },true);
/* the peek: a proposal's Project sits beside Owner and Due */
if(shared.CUR&&pkOn()) drawPanel();
}
/* ===== BL-197 (sprint-review-work) ===== right-click a work item for a menu of its common actions. One component (components/review/ContextMenu.jsx since BL-316: a menu
   with submenus, a real menu, the icon set beside each word, never colour alone) and per-kind action lists (cxWork for actions,
   RAID items and decisions; cxReview for Review's proposals), wired to the save paths that exist: one item through boardMove (the
   cell editor's save: the same checks, one proposal, Undo in the message, a line in Activity); several through batchMove (BL-124's
   bar: what can't take the change is left out and named); a decision through recordFromBoard and withdrawDecision; a proposal
   through rvSet (Review's own edit path: kept as Alan's edit, still pending, nothing in the tracker until apply), decide, and
   Review's own Approve and Reject for the highlighted rows, whose bulk rule is unchanged (minutes, new decisions and new risks are
   never approved together). Nothing deletes. Where: a row or card on Work (every tab, All items too), Mine, a person's page and
   the project page's tables, and any item link (data-open: Today, Activity, the project page's cards). Several highlighted rows:
   the menu says how many and offers only what applies to all of them (different kinds: Copy IDs only). Shift+F10 or the
   context-menu key opens it on the cursor row; arrows, Enter, Esc; submenus open to the side that fits the window (BL-175). Outside
   items, text fields and real links, the browser's own menu appears. */
export let CXKEYAT=-1e9;   /* BL-316: the menu itself is components/review/ContextMenu.jsx (the Menu block's MenuPanel) */
/* ---- what was right-clicked ---- */
export function cxTarget(t){ if(!t||!t.closest) return null;
  if(t.closest("input,textarea,select,[contenteditable=true],[contenteditable=plaintext-only],.rail,#panel,#chat,dialog,.cxmenu,.pkpop,td.editing")) return null;
  const a=t.closest("a[href]"); if(a&&!/^#/.test(a.getAttribute("href")||"")) return null;        /* a real link keeps the browser's menu */
  const tr=t.closest("#reviewBody tr[data-n]"); if(tr){ const r=REV.find(x=>x.n===+tr.dataset.n); return r&&!r.done?{rev:r,el:tr}:null; }
  const gt=t.closest("#reviewBody tr[data-gone]"); if(gt){ const g=rjGone.value.find(x=>x.key===gt.dataset.gone); return g?{gone:g,el:gt}:null; }   /* BL-315: a row rejected here */
  const row=t.closest("[data-row]"); if(row&&!row.closest("#actTbl")){ const id=row.dataset.row, inWork=!!row.closest("#workTbl,#workBoard"), k=row.dataset.k&&row.dataset.k!=="all"?row.dataset.k:inWork&&shared.WT!=="all"?shared.WT:kOfId(id);
    if(PKK.includes(k)&&REC(k,id)) return {k,id,el:row,row:inWork||!!row.closest("#v-person")}; }
  const o=t.closest("[data-open]"); if(o){ const [k,id]=String(o.dataset.open).split(":"); if(PKK.includes(k)&&REC(k,id)) return {k,id,el:o}; }
  return null; }
export function cxShow(c,x,y){ const from=document.activeElement&&document.activeElement!==document.body?document.activeElement:c.el;
  if(c.gone){ openContextMenu(cxGone(c.gone,c.el),x,y,{label:"Rejected proposal",from}); return; }   /* BL-315 */
  if(c.rev){ const n=c.rev.n; if(!(RHL.has(n)&&RHL.size>=2)){ rvOnly(n); shared.RSEL=+c.el.dataset.ri; rvPaint(); } else { shared.RSEL=+c.el.dataset.ri; rvPaint(); }
    const L=RHL.size>=2?rvSel():[c.rev]; openContextMenu(L.length>1?cxReviewMany(L):cxReview(c.rev,c.el),x,y,{label:L.length>1?`${L.length} proposals`:"Proposal",from}); return; }
  let ids=[[c.k,c.id]];
  if(c.row){ if(HL.has(c.id)&&HL.size>=2) ids=[...HL.keys()].map(id=>[kOfId(id),id]).filter(([k,id])=>k&&REC(k,id)); else { hlOnly(c.k,c.id); } }
  openContextMenu(ids.length>1?cxWorkMany(ids):cxWork(c.k,c.id),x,y,{label:ids.length>1?`${ids.length} items`:c.id,from}); }
/* the focused row for Shift+F10 and the context-menu key: the focused element's item, or the list's cursor row */
export function cxCursor(){ const a=document.activeElement; let c=a&&a!==document.body?cxTarget(a):null; if(c) return c;
  if(a&&a!==document.body&&a.closest&&a.closest("input,textarea,select,[contenteditable],.rail,#chat,dialog,#panel")) return null;
  if(shared.VIEW==="review"){ const tr=$$("#reviewBody tr[data-n]")[shared.RSEL]; return tr?cxTarget(tr.querySelector("td.title")||tr):null; }
  const id=shared.HLC??shared.SEL; if(!id||!["work","mine","person"].includes(shared.VIEW)) return null; const el=$$("#workTbl [data-row],#workBoard .bcard[data-row],#v-person table.ptbl tr[data-row]").find(e=>e.dataset.row===id);
  return el?cxTarget(el.querySelector("td.title")||el):null; }
/* ---- shared pieces ---- */
export const cxCopy=(text,what)=>{ const done=()=>snack(`Copied ${what}`); if(navigator.clipboard) navigator.clipboard.writeText(text).then(done,()=>prompt("Copy:",text)); else prompt("Copy:",text); };
export const cxLink=id=>location.origin+location.pathname+actHref(kOfId(id),id);
/** @param {any} cur @param {(v: any) => any} set @param {{clear?: boolean, label?: string, hint?: string}} [o] */
export function cxDates(cur,set,{clear=true,label="Due date",hint}={}){ const nm=pkAdd(TODAY,7-pkDow(TODAY)), wk=iso=>{ const w=weekendNote(iso); return w?w.text:""; };
  const at=(lab,iso)=>({label:lab,icon:"calendar",hint:[fd(iso),wk(iso)].filter(Boolean).join(" · "),checked:cur===iso,run:()=>set(iso)});
  return [at("Today",TODAY),at("Tomorrow",pkAdd(TODAY,1)),at("Friday",thisFriday()),at("Next week",nm),
    {label:"Pick a date…",icon:"calendar",run:async()=>{ const d=await boardAsk({title:label,hint:hint||"",date:cur||thisFriday()}); if(d) set(d); }},
    ...(clear&&cur?[{sep:true},{label:"Clear",icon:"x",run:()=>set(null)}]:[])]; }
export function cxPeople(cur,set,me=true){ const L=peopleAll(); return [...L.map(n=>({label:n,icon:"user",hint:isMe(n)?"Me":"",checked:n===cur,run:()=>set(n)})),{label:"Unassigned (TBC)",icon:"user",checked:!cur||cur==="TBC",run:()=>set("TBC")}]; }
export const cxList=(vals,cur,set,icon)=>vals.map(v=>Array.isArray(v)?v:[v,v]).map(([v,l])=>({label:l,icon,checked:String(cur??"")===String(v??""),run:()=>set(v)}));
/* ---- one action, RAID item or decision ---- */
export function cxWork(k,id){ const x=REC(k,id), one=(patch,label)=>boardMove(k,id,patch,label), /** @type {any[]} */ out=[{label:"Open",icon:"cxopen",run:()=>openRecord(k,id)}];
  if(k==="decisions"){ const pend=x.st==="Pending";
    out.push({label:"Record the decision",icon:"check",disabled:!pend,hint:pend?"":"Already "+x.st.toLowerCase(),run:()=>recordFromBoard(id)},
      {label:"Withdraw",icon:"x",disabled:x.st==="Withdrawn",run:async()=>{ if(await boardAsk({title:`Withdraw ${id}?`,hint:x.t,clear:true,okText:"Withdraw"})) await withdrawDecision(x); }},
      {sep:true},{label:"Needed by",icon:"calendar",disabled:!pend,sub:()=>cxDates(x.due,v=>one({due:v}),{label:`Needed by, for ${id}`,hint:x.t})},
      {label:"Decision maker",icon:"user",search:true,disabled:x.st==="Withdrawn",sub:()=>cxPeople(x.by,v=>one({by:v}))}); }
  else { const op=OPENST(x.st);
    out.push(op?{label:"Close",icon:"check",run:()=>one({st:"Closed"})}:{label:"Reopen",icon:"undo",run:()=>one({st:"Open"})},
      {sep:true},{label:"Status",icon:"flag",sub:()=>pkStatuses(k).map(s=>({label:s,icon:null,checked:x.st===s,run:()=>one({st:s})}))},
      {label:"Owner",icon:"user",search:true,sub:()=>cxPeople(x.o,v=>one({o:v}))},
      {label:"Due",icon:"calendar",sub:()=>cxDates(x.due,v=>one({due:v}),{label:`Due date for ${id}`,hint:x.t})},
      ...(k==="actions"?[{label:"Priority",icon:"alert",sub:()=>cxList(["Urgent","High","Medium","Low"],x.pr,v=>one({pr:v}))}]
        :[{label:"Impact",icon:"alert",sub:()=>cxList(["High","Medium","Low"],x.imp,v=>one({imp:v}))},{label:"Likelihood",icon:"alert",sub:()=>cxList(["High","Medium","Low"],x.lik,v=>one({lik:v}))}]),
      {label:"Workstream",icon:"layers",sub:()=>cxList([...wsFor(x.p),["","None"]],x.ws||"",v=>one({ws:v}),"layers")},
      {label:"Milestone",icon:"flag",sub:()=>cxList(msChoices(x.p,x.ms),x.ms||"",v=>one({ms:v}),"flag")}); }
  out.push({sep:true},{label:"Copy ID",icon:"copy",run:()=>cxCopy(id,id)},{label:"Copy link",icon:"link",run:()=>cxCopy(cxLink(id),`the link to ${id}`)});
  const who=k==="decisions"?null:pkWho(x.o); if(who&&PERS().some(p=>p.name===who)) { out.push({label:`Draft email to ${who}`,icon:"mail",run:()=>openDraftEmail(who)}); if(x.due&&x.due<TODAY&&OPENST(x.st)&&!deMe(who)) out.push({label:`Chase ${who}`,icon:"mail",run:()=>openDraftEmail(who,"chase")}); }   /* BL-224 */
  return out; }
/* ---- several highlighted: what applies to all of them ---- */
export function cxWorkMany(ids){ const ks=new Set(ids.map(i=>i[0])), k=ids[0][0], xs=ids.map(([kk,id])=>REC(kk,id)), n=ids.length, all=ids.map(i=>i[1]);
  const /** @type {any[]} */ out=[{head:`${n} items`}], many=(f,v)=>batchMove(k,all,{[f]:v},bkWhat(f,v));
  if(ks.size>1) out.push({label:"Change them on their own tabs",icon:null,disabled:true,hint:"These items are of different kinds"});
  else if(k==="decisions") out.push({label:"Decision maker",icon:"user",search:true,sub:()=>cxPeople(null,v=>many("by",v))});
  else { const proj=new Set(xs.map(x=>x.p)), p=proj.size===1?[...proj][0]:null, why=p?"":"These items are in different projects";
    out.push({label:"Close",icon:"check",disabled:!xs.some(x=>OPENST(x.st)),run:()=>many("st","Closed")},{label:"Reopen",icon:"undo",disabled:!xs.some(x=>!OPENST(x.st)),run:()=>many("st","Open")},{sep:true},
      {label:"Status",icon:"flag",sub:()=>BK_STATUS[k].map(s=>({label:s,run:()=>many("st",s)}))},
      {label:"Owner",icon:"user",search:true,sub:()=>cxPeople(null,v=>many("o",v))},
      {label:"Due",icon:"calendar",sub:()=>cxDates(null,v=>many("due",v),{clear:false,label:`Due date for ${n} items`})},
      ...(k==="actions"?[{label:"Priority",icon:"alert",sub:()=>cxList(["Urgent","High","Medium","Low"],null,v=>many("pr",v))}]
        :[{label:"Impact",icon:"alert",sub:()=>cxList(["High","Medium","Low"],null,v=>many("imp",v))},{label:"Likelihood",icon:"alert",sub:()=>cxList(["High","Medium","Low"],null,v=>many("lik",v))}]),
      {label:"Workstream",icon:"layers",disabled:!p,hint:why,sub:()=>cxList([...wsFor(p),["","None"]],null,v=>many("ws",v),"layers")},
      {label:"Milestone",icon:"flag",disabled:!p,hint:why,sub:()=>cxList(msChoices(p,""),null,v=>many("ms",v),"flag")}); }
  out.push({sep:true},{label:"Copy IDs",icon:"copy",run:()=>cxCopy(all.join(", "),`${n} IDs`)});
  return out; }
/* ---- Review: a proposal (or several), changed before it is approved ---- */
export const cxPk=r=>["actions","raid","decisions"].includes(r.kind);
export function cxReviewFields(L,set){ const ar=L.every(r=>["actions","raid"].includes(r.kind)), ps=new Set(L.map(r=>r.p)), p=ps.size===1?[...ps][0]:null, one=L.length===1?L[0]:null, k=L[0].kind, same=L.every(r=>r.kind===k), x=one?one.rec:{};
  const /** @type {any[]} */ out=[{label:"Project",icon:"projects",sub:()=>rvActive().map(q=>({label:q.name,icon:"projects",checked:one&&one.p===q.code,run:()=>one?rvMoveItem(one,q.code):set("p",q.code)}))},
    {label:k==="decisions"&&same?"Decision maker":"Owner",icon:"user",search:true,sub:()=>cxPeople(one?(k==="decisions"?x.by:x.o):null,v=>set("o",v))}];
  if(ar) out.push({label:"Due",icon:"calendar",sub:()=>cxDates(one?x.due:null,v=>set("due",v||""),{clear:!!one,label:one?"Due date":"Due date for "+L.length+" proposals"})});
  if(same&&k==="actions") out.push({label:"Priority",icon:"alert",sub:()=>cxList(["Urgent","High","Medium","Low"],one?x.pr:null,v=>set("pr",v))});
  if(same&&k==="raid") out.push({label:"Impact",icon:"alert",sub:()=>cxList(["High","Medium","Low"],one?x.imp:null,v=>set("imp",v))},{label:"Likelihood",icon:"alert",sub:()=>cxList(["High","Medium","Low"],one?x.lik:null,v=>set("lik",v))});
  if(ar){ const why=p?"":"These are in different projects, or have none yet";
    out.push({label:"Workstream",icon:"layers",disabled:!p,hint:why,sub:()=>cxList([...wsFor(p),["","None"]],one?x.ws||"":null,v=>set("ws",v),"layers")},
      {label:"Milestone",icon:"flag",disabled:!p,hint:why,sub:()=>cxList(msChoices(p,""),one?x.ms||"":null,v=>set("ms",v),"flag")}); }
  if(same&&k!=="decisions") out.push({label:"Status",icon:"flag",sub:()=>pkStatuses(k).map(s=>({label:s,checked:one&&x.st===s,run:()=>set("st",s)}))});
  return out; }
export function cxReview(r,tr){ const /** @type {any[]} */ out=[{label:"Approve",icon:"check",disabled:!!r.nodraft,hint:r.nodraft?NODRAFT_MSG:"",run:()=>decide(r.n,"approved")},   /* BL-260 point 4 */
    rvRejectOK(r)?{label:"Reject with a reason…",icon:"x",run:()=>rjMenuFor(rjWith(r),tr.querySelector("[data-act=rr]")||tr)}:{label:"Reject",icon:"x",run:()=>isMin(r)?rejectMinutes(r):decide(r.n,"rejected")},{sep:true},
    {label:r.kind==="draft"?(r.nodraft?"No Word draft":"Open the draft"):"Open",icon:"cxopen",disabled:r.kind==="files",run:()=>openProposal(r.n)}];
  if(isMin(r)) out.push({label:"Project",icon:"projects",hint:"Move these minutes and their items",run:()=>rvMoveMinutes(tr.querySelector('[data-act="pj"]')||tr,r,tr.dataset.g)});
  if(rtOK(r)) out.push({label:"Update an existing item instead…",icon:"refresh",run:()=>rtOpen(tr.querySelector('[data-act="e"]')||tr,r)});   /* BL-297 D */
  if(cxPk(r)) out.push({sep:true},...cxReviewFields([r],(f,v)=>rvSet(f,v)));
  return out; }
export function cxReviewMany(L){ const ok=L.filter(rvBulkOK), rej=L.filter(rvRejectOK), /** @type {any[]} */ out=[{head:`${L.length} proposals`},
    {label:`Approve ${ok.length}`,icon:"check",disabled:!ok.length,hint:ok.length<L.length?`${L.length-ok.length} need${L.length-ok.length===1?"s":""} individual approval or a project`:"",run:()=>rvApproveSelected()},
    {label:`Reject ${rej.length} with a reason…`,icon:"x",disabled:!rej.length,run:()=>rjMenuFor(rej,$("#bulkReject"))}];   /* BL-315 */
  if(L.every(cxPk)) out.push({sep:true},...cxReviewFields(L,(f,v)=>rvSet(f,v)));
  else out.push({label:"Change them one by one",icon:null,disabled:true,hint:"Minutes, reports, file changes and updates have no fields here"});
  return out; }
/* ===== end BL-197 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootReview0195(){
Object.assign(ICONS,{cxopen:'<path d="M14 4h6v6M10 14L20 4M19 13v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h6"/>'});
document.addEventListener("contextmenu",e=>{ if(performance.now()-CXKEYAT<400){ e.preventDefault(); return; }   /* the key opened it already */
  const kb=!e.clientX&&!e.clientY; let c=cxTarget(e.target); if(!c&&kb) c=cxCursor(); if(!c) return;
  e.preventDefault(); const r=c.el.getBoundingClientRect(); cxShow(c,kb?r.left+Math.min(48,r.width/3):e.clientX,kb?r.top+Math.min(r.height,28):e.clientY); });
window.addEventListener("keydown",e=>{ if(!(e.key==="ContextMenu"||(e.key==="F10"&&e.shiftKey))||contextMenuOpen()) return; const c=cxCursor(); if(!c) return;
  e.preventDefault(); e.stopPropagation(); CXKEYAT=performance.now(); const r=c.el.getBoundingClientRect(); c.el.scrollIntoView({block:"nearest"}); cxShow(c,r.left+Math.min(48,r.width/3),r.top+Math.min(r.height,28)); },true);
}
/* ===== BL-208 (sprint-insight) ===== Review one proposal at a time: a focus mode inside Review, from its toolbar. The list stays; the
   card shows one proposal with its fields (a guessed one underlined with a dashed line and its reason), the source beside it (the
   source note stands in for the transcript line until BL-60's positions exist), a Project control (BL-200) and A Approve, R Reject
   (with a reason, BL-133), E Edit, J Skip, K Previous. The queue (review.focus_queue, built into D.review_focus) is what needs Alan,
   guessed fields first, then a spot-check of the routine items at review.spot_check_rate; the routine rest is approved together, by
   the list's own rule (rvBulkOK: never minutes, new decisions or new risks). Approving here is decide(): the same as in the list.
   Where you stopped is kept per batch. */
export const rfKey=()=>[...new Set(REV.filter(r=>!r.done).map(r=>r.file))].sort().join("|");
export function rfQueue(){ const F=D.review_focus||{queue:[],spot:[]}, live=n=>{ const r=REV.find(x=>x.n===n); return r&&!r.done; };
  const q=F.queue.filter(live), extra=REV.filter(r=>!r.done&&!rvBulkOK(r)&&!q.includes(r.n)).map(r=>r.n);   /* anything new since the build */
  return [...q.filter(n=>!F.spot.includes(n)),...extra,...q.filter(n=>F.spot.includes(n))]; }
export const rfRoutine=()=>REV.filter(r=>!r.done&&rvBulkOK(r)&&!(r.inferred||[]).length&&!rfQueue().includes(r.n));
export function rfOpen(){ if(!REV.some(r=>!r.done)){ snack("Nothing waits in Review"); return; } const key=rfKey(); let i=0; try{ const s=JSON.parse(localStorage.getItem("creaite-rvfocus")||"{}"); if(s.key===key) i=s.i||0; }catch(e){}
  shared.RF={key,i}; rfDraw(); }
export function rfSave(){ if(!shared.RF) return; try{ localStorage.setItem("creaite-rvfocus",JSON.stringify({key:shared.RF.key,i:shared.RF.i})); }catch(e){} }
export function rfClose(){ shared.RF=null; $("#rvFocus")?.remove(); $("#reviewBody")?.removeAttribute("hidden"); renderReview(); }
export const RFF={o:"Owner",by:"Decision maker",due:"Due",pr:"Priority",st:"Status",ws:"Workstream",type:"Type",imp:"Impact",lik:"Likelihood",resp:"Response",date:"Date",t:"Title"};
export function rfFields(r){ const x=r.rec||{}, inf=Object.fromEntries((r.inferred||[]).map(i=>[i.field,i.why])), show=(f,v)=>{ const why=inf[f]||inf[{o:"owner",by:"made_by",due:"due_date",pr:"priority",imp:"impact",lik:"likelihood",resp:"response_action",t:"description"}[f]];
    return `<div class="rfrow${why?" guess":""}"><span class="rfk">${RFF[f]||f}</span><span class="rfv"${why?` title="${esc(why)}"`:""}>${esc(["due","date"].includes(f)?fd(v):String(v))}</span>${why?`<span class="rfwhy">Guessed: ${esc(why)}</span>`:""}</div>`; };
  const keys=r.kind==="actions"?["o","due","pr","ws"]:r.kind==="raid"?["type","o","imp","lik","resp","due"]:r.kind==="decisions"?["by","st","date"]:[];
  if(r.kind==="update") return (x.changes||[]).map(c=>`<div class="rfrow"><span class="rfk">${esc(c.field)}</span><span class="rfv">− ${esc(fd(String(c.from??"—")))} &nbsp; + ${esc(fd(String(c.to??"—")))}</span></div>`).join("");
  return keys.filter(f=>x[f]!=null&&x[f]!=="").map(f=>show(f,x[f])).join("")+keys.filter(f=>(x[f]==null||x[f]==="")&&f!=="ws").map(f=>`<div class="rfrow missing"><span class="rfk">${RFF[f]}</span><span class="rfv sub">Not set</span></div>`).join(""); }
export function rfDraw(){ if(!shared.RF) return; const q=rfQueue(); if(shared.RF.i>=q.length) shared.RF.i=Math.max(0,q.length-1); shared.RF.q=q; rfSave();
  const el=(()=>{ let e=$("#rvFocus"); $("#reviewBody").setAttribute("hidden",""); if(!e){ addHTML($("#reviewBody"),"beforebegin",html`<section id="rvFocus" class="rvfocus" aria-label="One proposal at a time" tabindex="-1"></section>`); e=$("#rvFocus"); } return e; })();
  const rt=rfRoutine(), spot=(D.review_focus||{}).spot||[];
  if(!q.length){ putHTML(el,html`<div class="rfhead"><strong>Nothing left that needs you</strong><span class="sp"></span><button type="button" class="btn" data-rf="close">Back to the list</button></div>${rt.length?html`<p>${raw(plur(rt.length,"routine item"))} can be approved together. <button type="button" class="btn primary" data-rf="routine">Approve the routine items</button></p>`:html`<p class="sub">Review is clear.</p>`}`); el.focus(); return; }
  const r=REV.find(x=>x.n===q[shared.RF.i]), isSpot=spot.includes(r.n), x=r.rec||{}, kind=r.kind==="draft"?(r.ref==="meeting"?"Minutes":"Report"):r.kind==="update"?"Update":{actions:"Action",raid:x.type||"RAID item",decisions:"Decision",files:"File change"}[r.kind]||r.kind;
  const need=q.length-spot.filter(n=>q.includes(n)).length;
  putHTML(el,html`<div class="rfhead"><strong>${raw(shared.RF.i+1)} of ${q.length}</strong><span class="sub">${raw(plur(need,"proposal"))} need${need===1?"s":""} you${spot.length?html`, then ${raw(plur(spot.filter(n=>q.includes(n)).length,"spot-check"))}`:""}${rt.length?html` · ${raw(plur(rt.length,"routine item"))} approved together at the end`:""}</span><span class="sp"></span><button type="button" class="btn" data-rf="close" title="Back to the list (Esc)">List</button></div>
    <div class="rfcard"><div class="rfmain">
      <div class="rfmeta">${isSpot?html`<span class="tag warn">Spot-check: a routine item, shown so you can check the extraction</span> `:""}<span class="tag">${kind}</span> ${(r.inferred||[]).length?html`<span class="tag warn">${raw(plur(r.inferred.length,"guessed field"))}</span>`:""}
        ${["actions","raid","decisions"].includes(r.kind)?html`<button type="button" class="mini rfproj" data-rf="proj" aria-haspopup="menu">Project: ${(r.p?pName(r.p):"Choose…")}</button>`:r.p?pName(r.p):""}</div>
      <h2 class="rftitle">${(x.t||"")}</h2>${raw(rfFields(r))}
      ${(r.flags||[]).length?html`<div class="sub">Flags: ${((r.flags||[]).join(", "))}</div>`:""}
      ${r.kind==="draft"&&(r.cov||[]).length?html`<div class="sub">Coverage: ${raw(r.cov.filter(c=>c.verdict!=="Covered").length)} of ${r.cov.length} agenda points not fully discussed</div>`:""}
    </div><aside class="rfsrc" aria-label="Where it came from"><h3>Source</h3>${r.src?raw(srcHTML(r.src)):html`<span class="sub">No source recorded</span>`}<p class="sub">The source note stands in for the transcript line until creaite records where in the file it was said.</p></aside></div>
    <div class="rfacts"><button type="button" class="btn primary" data-rf="a"><kbd>A</kbd> Approve</button><button type="button" class="btn" data-rf="r"><kbd>R</kbd> Reject</button><button type="button" class="btn" data-rf="e"><kbd>E</kbd> Edit</button><button type="button" class="btn" data-rf="j"><kbd>J</kbd> Skip</button><button type="button" class="btn" data-rf="k" ${shared.RF.i?"":"disabled"}><kbd>K</kbd> Previous</button></div>`);
  el.focus({preventScroll:true}); }
export async function rfAct(a,btn){ if(!shared.RF) return; const r=REV.find(x=>x.n===shared.RF.q[shared.RF.i]);
  if(a==="close"){ rfClose(); return; }
  if(a==="routine"){ const ok=rfRoutine(); if(!ok.length) return; const res=await rvDecideMany(ok,"approved"); rvSummary("Approved",res,[]); rfDraw(); return; }
  if(!r) return;
  if(a==="j"){ shared.RF.i=Math.min(shared.RF.i+1,shared.RF.q.length); if(shared.RF.i>=shared.RF.q.length) shared.RF.i=shared.RF.q.length-1; rfDraw(); return; }
  if(a==="k"){ shared.RF.i=Math.max(0,shared.RF.i-1); rfDraw(); return; }
  if(a==="e"){ openProposal(r.n); return; }
  if(a==="a"){ await decide(r.n,"approved"); rfDraw(); return; }
  if(a==="r"){ if(isMin(r)){ await rejectMinutes(r); rfDraw(); return; } rvOnly(r.n); if(rvRejectOK(r)) rjMenuFor([r],btn||$('#rvFocus [data-rf="r"]'),()=>rfDraw()); else { await decide(r.n,"rejected"); rfDraw(); } return; }
  if(a==="proj"){ const b=btn||$('#rvFocus [data-rf="proj"]'); openContextMenuAt(b,rvActive().map(p=>({label:p.name,icon:"projects",checked:r.p===p.code,run:async()=>{ await rvMoveItem(r,p.code); rfDraw(); }})),{label:"Project"}); } }
/* ===== end BL-208 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootReview0209(){
document.addEventListener("click",e=>{ const b=e.target.closest("[data-rf]"); if(b&&b.closest("#rvFocus")){ rfAct(b.dataset.rf,b); return; } if(e.target.closest("[data-rvfocus]")) rfOpen(); });
window.addEventListener("keydown",e=>{ if(!shared.RF||shared.VIEW!=="review"||e.metaKey||e.ctrlKey||e.altKey||e.isComposing) return; const t=e.target; if(t.closest&&t.closest("input,textarea,select,[contenteditable=true],dialog,.cxmenu,[role=menu],#panel,#chat")) return;
  const k=e.key.toLowerCase(); if(e.key==="Escape"){ e.preventDefault(); e.stopImmediatePropagation(); rfClose(); return; }
  if(["a","r","e","j","k"].includes(k)){ e.preventDefault(); e.stopImmediatePropagation(); rfAct(k); } },true);
}
/* ===== BL-315 (v1.9.2) ===== Rejects, in real life: Team 1's screen piece on Team 2's server (dev/V192-REJECT-REASONS-NOTE.md).
   One reasons menu (components/review/RejectMenu.jsx, its state in stores/rejects.js) for one row or many: the Review bar's Reject
   with a reason and R, a row's ✕ and ▾, Shift+R, the row's menu (right-click, Shift+F10), the peek's Reject and One at a time's R.
   The seven reasons on 1 to 7, Use each guess (G) and No reason (0). creaite's guess shows on each row in grey ("guess: Chatter"),
   from /api/review/guesses; Use each guess rejects each row with its own. Duplicate records the item a guess or a "Looks like"
   names, or asks for it (the look-alikes, an ID typed, or none). Rejects go through /api/review/reject (review.py: the spelling,
   rejected_at, the guesses), then apply as any decision does. One message for the batch, with Undo: every row back in Review.
   A rejected row stays, greyed, with its reason as a chip ("Rejected · Chatter") until Review is left: the chip or its ▾ reopens
   the menu to change the reason; Approve instead undoes the reject and approves it in one step (/api/review/rejected); an item
   approved only on its own (minutes, a new decision, a new risk…) goes back to Review and its proposal opens: nothing is ever
   approved in bulk that the bulk rule keeps back, and nothing is approved without Alan's click. Each change has its Undo.
   Activity › Quality › What you rejected lists recent rejects with the same chip, Approve instead and Undo. Without the live
   server a reject still takes its reason (written into the proposal, as BL-133 did); guesses, changing a reason and Approve
   instead need the server. */
export const rjKey=r=>`${r.file}#${r.ref}`;
export const rjGuessOf=r=>rjGuesses.value[rjKey(r)]||null;
export const rjDupOf=r=>{ if(rvDup(r)) return r.dup.id; const g=rjGuessOf(r); return g&&g.reason==="Duplicate"&&g.of||null; };
export const rjRow=r=>({key:rjKey(r),file:r.file,ref:r.ref,t:r.rec&&r.rec.t||"",guess:r.gone?r.guess:rjGuessOf(r),dup:r.gone?r.dup:rjDupOf(r),reason:r.gone?r.reason||"":undefined});
/* a row's ✕ or ▾ acts on the selection when the row is in it (as Work's bar does), otherwise on the row */
export const rjWith=r=>RHL.has(r.n)&&RHL.size>1?rvSel().filter(rvRejectOK):[r];
const rjShort=t=>{ t=String(t||""); return t.length>60?t.slice(0,59)+"…":t; };
export function rjGuessHtml(r){ const g=!r.done&&rvRejectOK(r)?rjGuessOf(r):null; if(!g) return "";
  return String(html` · <span class="rvguess" title="creaite's guess at why you'd reject it${g.why?`: ${g.why}`:""}">guess: ${g.reason}${g.of?` (${g.why||g.of})`:""}</span>`); }
/* the guesses, fetched once for each set of pending rows */
export async function rjLoadGuesses(){ if(!viaServer()) return; const sig=REV.filter(r=>!r.done).map(rjKey).join(","); if(sig===rjGuessFor.value) return; rjGuessFor.value=sig;
  const res=await api("/api/review/guesses",{}); if(!res.ok) return; if(Array.isArray(res.reasons)&&res.reasons.length) rjReasons.value=res.reasons;
  const /** @type {Record<string, any>} */ g={}; (res.guesses||[]).forEach(x=>{ g[`${x.file}#${x.ref}`]={reason:x.reason,why:x.why||"",of:x.of||null}; });
  if(JSON.stringify(g)===JSON.stringify(rjGuesses.value)) return; rjGuesses.value=g; if(shared.VIEW==="review"&&!shared.RF) renderReview(); }
const rjExpanded=(a,on)=>{ if(a&&a.getAttribute&&a.getAttribute("aria-haspopup")) a.setAttribute("aria-expanded",String(on)); };
/* the menu, to reject pending rows */
export function rjMenuFor(list,anchor,after,before){ list=list.filter(rvRejectOK); if(!list.length) return; rjExpanded(anchor,true);
  rjOpenMenu({rows:list.map(rjRow),anchor:anchor||null,mode:"reject",guesses:viaServer(),onPick:c=>{ if(before) before(); rjReject(list,c,after); },onClose:()=>rjExpanded(anchor,false),
    candidates:viaServer()?async()=>{ const r=list.find(x=>!rjDupOf(x))||list[0], res=await api("/api/review/candidates",{file:r.file,ref:r.ref}); return res.ok?res.items||[]:[]; }:undefined}); }
/* the menu, to change rejects' reason (a greyed row's chip or ▾, Activity's list) */
export function rjReasonFor(rows,anchor){ if(!rows.length) return; rjExpanded(anchor,true);
  rjOpenMenu({rows,anchor:anchor||null,mode:"reason",guesses:viaServer(),onPick:c=>rjRereason(rows,c),onClose:()=>rjExpanded(anchor,false),candidates:viaServer()?async()=>[]:undefined}); }   /* a reject is no longer pending: its Duplicate item is typed */
/* the batch's one message: the status line under the bar, and the message at the foot with Undo */
export function rjSay(text,undo){ RVLASTUNDO=undo||null; const el=$("#rvresult");
  if(el) putHTML(el,html`<span><b>${text}</b></span>${undo?html`<button type="button" class="linkbtn" id="rvUndo">Undo</button>`:""}`); snack(text,undo||null); }
const rjGhost=(r,reason,dup)=>({...r,rec:{...r.rec},gone:true,key:rjKey(r),rk:rvKey(r),done:"rejected",n:null,reason:reason||null,dup:dup||null,guess:rjGuessOf(r),at:Date.now(),server:viaServer()});
const rjBy=(rows,body)=>{ const m=new Map(); rows.forEach(r=>{ const b=body(r), k=JSON.stringify(b); if(!m.has(k)) m.set(k,{body:b,L:[]}); m.get(k).L.push(r); }); return [...m.values()]; };
const rjRef=k=>{ const i=k.lastIndexOf("#"), ref=k.slice(i+1); return {file:k.slice(0,i),ref:/^\d+$/.test(ref)?+ref:ref}; };
export async function rjReject(list,c,after){ list=list.filter(r=>rvRejectOK(r)); if(!list.length) return;
  if(list.length>shared.RV_MAX&&!await boardAsk({title:`Reject ${list.length} proposals?`,hint:"Rejecting writes nothing to the tracker; Undo brings them back",clear:true,okText:`Reject ${list.length}`})) return;
  const why=r=>{ if(!c.guess) return c.reason||null; const g=rjGuessOf(r); return g?g.reason:null; };
  const dupOf=r=>{ if(c.guess){ const g=rjGuessOf(r); return g&&g.reason==="Duplicate"&&g.of||null; } return c.reason==="Duplicate"?rjDupOf(r)||c.dup||null:null; };
  const how=c.guess?"with their guesses":c.reason?`as ${c.reason}`:"without a reason";
  if(!viaServer()){                               /* the page writes the proposal itself, with the reason (BL-133's way) */
    list.forEach(r=>{ const w=why(r); if(w) RVREASON.set(r.n,{reason:w,dup:dupOf(r)}); else RVREASON.delete(r.n); }); const G=list.map(r=>rjGhost(r,why(r),dupOf(r)));
    if(list.length===1) await decide(list[0].n,"rejected"); else { const res=await rvDecideMany(list,"rejected"); RHL.clear(); rvSyncChk(); rvSummary("Rejected",res,[]); }
    rjAddGone(G.filter(g=>REV.some(r=>rvKey(r)===g.rk&&r.done==="rejected"))); renderReview(); if(after) after(); return; }
  const done=[], msgs=[];
  for(const {body,L} of rjBy(list,r=>c.guess?{guess:true}:{reason:c.reason||"",duplicate_of:dupOf(r)||""})){
    const res=await api("/api/review/reject",{rows:L.map(r=>({file:r.file,ref:r.ref})),...body});
    if(res.ok) (res.rejected||[]).forEach(x=>{ const r=L.find(y=>y.file===x.file&&String(y.ref)===String(x.ref)); if(r) done.push(r); }); else msgs.push(oneLine(res.message)); }
  if(!done.length){ snack("Not rejected: "+(msgs[0]||"nothing changed")); return; }
  const at=shared.VIEW==="review"?$$("#reviewBody tr[data-n]").findIndex(t=>done.some(r=>+t.dataset.n===r.n)):-1;
  const G=done.map(r=>rjGhost(r,why(r),dupOf(r)));
  done.forEach(r=>{ r.done="rejected"; RHL.delete(r.n); CHK.delete(r.n); }); shared.RVSTATS.rejected=(shared.RVSTATS.rejected||0)+done.length;
  rjAddGone(G); renderReview(); if(at>=0&&S.rvAdvance!==false){ shared.RSEL=Math.max(0,Math.min(at,$$("#reviewBody tr[data-n]").length-1)); rvPaint(); }   /* the cursor moves on */
  const ap=S.autoApply?await applyNow():(await reloadData(),null);
  const n=done.length, text=`Rejected ${n===1?"1":n} ${how}`+(ap&&!ap.ok?` · not applied: ${oneLine(ap.message)}`:"")+(msgs.length?` · not rejected: ${msgs[0]}`:"");
  rjSay(text,()=>rjUnreject(G));
  if(shared.VIEW==="review"&&(!document.activeElement||document.activeElement===document.body)) $(`#reviewBody tr[data-gone="${CSS.escape(G[0].key)}"] [data-rjchip]`)?.focus({preventScroll:true});   /* focus stays near: the reject's chip */
  if(after) after(); }
async function rjRejected(rows,how,extra){ return api("/api/review/rejected",{rows:rows.map(r=>({file:r.file,ref:r.ref})),how,...(extra||{})}); }
const rjOff=what=>{ snack(`${what} needs the live server; or say “review” in Claude Code`); };
/* Undo a reject (pending or applied): back in Review, waiting, highlighted */
export async function rjUnreject(rows){ if(!viaServer()){ rjOff("Putting a reject back"); return; }
  const res=await rjRejected(rows,"undo"); if(!res.ok){ snack("Not undone: "+oneLine(res.message)); return; }
  const keys=rows.map(r=>r.key||rjKey(r)); rjDropGone(keys); await reloadData();
  if(shared.VIEW==="review"){ RHL.clear(); REV.filter(r=>keys.includes(rjKey(r))&&!r.done).forEach(r=>RHL.add(r.n)); rvSyncChk(); renderReview(); }
  if(shared.VIEW==="activity") rjLoadRecent();
  const el=$("#rvresult"); if(el) el.textContent=""; RVLASTUNDO=null; snack(`Back in Review: ${keys.length}`); }
/* Change rejects' reason: one reason, each row's guess, or none; Undo puts each one's earlier reason back */
export async function rjRereason(rows,c,quiet){ if(!viaServer()){ rjOff("Changing a reason"); return; }
  const body=r=>{ if(c.guess){ const g=r.guess; return {reason:g?g.reason:"",duplicate_of:g&&g.reason==="Duplicate"&&g.of||""}; } return {reason:c.reason||"",duplicate_of:c.reason==="Duplicate"?c.dup||r.dup||"":""}; };
  const done=[], msgs=[];
  for(const {body:b,L} of rjBy(rows,body)){ const res=await rjRejected(L,"reason",b); if(res.ok){ (res.done||[]).forEach(d=>done.push({...d,now:b})); } else msgs.push(oneLine(res.message)); }
  if(!done.length){ snack("Not changed: "+(msgs[0]||"nothing changed")); return; }
  done.forEach(d=>rjSetGone([d.key],()=>({reason:d.now.reason||null,dup:d.now.duplicate_of||null})));
  if(S.autoApply) await applyNow(); else await reloadData(); if(shared.VIEW==="review") renderReview(); if(shared.VIEW==="activity") rjLoadRecent();
  if(quiet) return;
  const to=c.guess?"their guesses":c.reason?c.reason+(c.reason==="Duplicate"&&(c.dup||rows.length===1&&rows[0].dup)?` of ${c.dup||rows[0].dup}`:""):"no reason";
  const back=done.map(d=>({...rjRef(d.key),key:d.key,was:d.was||{}}));
  rjSay(`Reason changed to ${to}`+(msgs.length?` · not changed: ${msgs[0]}`:""),async()=>{
    for(const {body:b,L} of rjBy(back,x=>({reason:x.was.reason||"",duplicate_of:x.was.duplicate_of||""}))) await rjRereason(L.map(x=>({...x,dup:b.duplicate_of||null})),{reason:b.reason||null,dup:b.duplicate_of||null},true);
    snack("Reason put back"); }); }
/* Approve instead: the reject undone and the item approved in one step; one approved only on its own goes back to Review, opened */
export async function rjApproveInstead(rows){ if(!viaServer()){ rjOff("Approve instead"); return; }
  const res=await rjRejected(rows,"approve"); if(!res.ok){ snack("Not approved: "+oneLine(res.message)); return; }
  const was=res.done||[], open=res.open||[], keys=rows.map(r=>r.key||rjKey(r)), ghosts=rjGone.value.filter(g=>keys.includes(g.key)); rjDropGone(keys);
  const ap=S.autoApply&&was.length?await applyNow():(await reloadData(),null);
  if(shared.VIEW==="activity") rjLoadRecent();
  const n=was.length, text=[n?`Approved instead: ${n}`:"",open.length?`${open.length} need${open.length===1?"s":""} approving on ${open.length===1?"its":"their"} own`:"",ap&&!ap.ok?`not applied: ${oneLine(ap.message)}`:""].filter(Boolean).join(" · ");
  const undo=n?async()=>{ const back=was.map(d=>({...rjRef(d.key),key:d.key,was:d.was||{}}));
    if(ap&&ap.ok&&ap.apply_id){ const u=await api("/api/undo",{apply_id:ap.apply_id}); if(!u.ok){ snack("Not undone: "+oneLine(u.message)); return; } await reloadData();
      for(const {body:b,L} of rjBy(back,x=>({reason:x.was.reason||"",duplicate_of:x.was.duplicate_of||""}))) await api("/api/review/reject",{rows:L.map(x=>({file:x.file,ref:x.ref})),...b}); }
    else { for(const x of back){ try{ await editProposal(x.file,data=>{ const it=(data.items||[]).find(i=>i.n===x.ref); if(!it||it.applied) throw new Error("already applied"); it.decision="rejected"; it.decided_in="dashboard";
        if(x.was.reason) it.reject_reason=x.was.reason; else delete it.reject_reason; if(x.was.duplicate_of) it.duplicate_of=x.was.duplicate_of; else delete it.duplicate_of; }); }catch(e){ snack("Not rejected again: "+e.message); } } }
    rjAddGone(ghosts.filter(g=>back.some(x=>x.key===g.key))); if(S.autoApply) await applyNow(); else await reloadData(); if(shared.VIEW==="activity") rjLoadRecent(); snack(`Rejected again: ${back.length}`); }:null;
  rjSay(text||"Nothing changed",undo);
  if(open.length){ const L=REV.filter(x=>open.includes(rjKey(x))&&!x.done); if(L.length){ if(shared.VIEW!=="review") go("review"); RHL.clear(); L.forEach(x=>RHL.add(x.n)); rvSyncChk(); renderReview(); openProposal(L[0].n); } } }
/* a greyed row: its text, its chip, Approve instead and ▾. It takes no cursor number and can't be selected */
export function rjGoneRow(g,grp,cls){ const chip=`Rejected · ${g.reason||"No reason"}${g.dup?` (${g.dup})`:""}`;
  return String(html`<tr class="rvgone ${cls||""}" data-gone="${g.key}" data-g="${grp}"><td style="width:32px"></td><td class="title"><span class="rvgt">${raw(revIco(g))}${g.rec.t??""}</span><div class="why">${kindLabel(g)??""} · ${fdText(srcShort(g.src))??""}</div></td><td style="white-space:nowrap;text-align:right"><button type="button" class="tag bad rjchip" data-rjchip="${g.key}" aria-haspopup="menu" aria-expanded="false" aria-label="${chip}: change the reason" data-tip="Change the reason">${chip}</button> <button type="button" class="mini ok" data-rjok="${g.key}" aria-label="Approve instead: ${g.rec.t??""}">${raw(ic("check"))}Approve instead</button> ${raw(ibtn("chevdown","Change the reason",`data-rjrr="${esc(g.key)}" aria-haspopup="menu" aria-expanded="false"`,"sm no rvrr"))}</td></tr>`); }
/* the greyed rows go where they were: under their minutes, or among their group's rows in proposal order */
export function rjPlace(out){ const L=rjGone.value.filter(g=>rvPasses(g)); if(!L.length) return;
  const cmp=(a,b)=>a.file<b.file?-1:a.file>b.file?1:(+a.ref||0)-(+b.ref||0);
  L.forEach(g=>{ const key=RVG==="kind"?g.kind:RVG==="source"?g.file:(g.p||"?"); let grp=out.find(x=>x.key===key);
    if(!grp){ const title=RVG==="kind"?esc(RVKINDS[g.kind]||g.kind):RVG==="source"?revGroupTitle(g.file,[]):key==="?"?"Needs a project":`<a href="#" class="hlink" data-proj="${esc(key)}">${esc(pName(key))}</a>`;
      grp={key,title,label:title.replace(/<[^>]+>/g,""),blocks:[]}; out.push(grp); }
    const gg=RVG==="project"?key:"*", mb=grp.blocks.find(b=>b[0].cls==="mparent"&&b[0].r.file===g.file&&!(b[0].head&&b[0].head.closed));
    if(mb){ let i=mb.findIndex((o,j)=>j>0&&cmp(g,o.r)<0); if(i<0) i=mb.length; mb.splice(i,0,{r:g,g:gg,cls:"mchild"}); return; }
    let i=grp.blocks.findIndex(b=>b[0].cls!=="mparent"&&cmp(g,b[0].r)<0); if(i<0) i=grp.blocks.length; grp.blocks.splice(i,0,[{r:g,g:gg}]); }); }
/* a greyed row's menu (right-click, Shift+F10 on its chip) */
export function cxGone(g,tr){ return [{head:"Rejected proposal"},{label:"Change the reason…",icon:"x",run:()=>rjReasonFor([rjRow(g)],tr.querySelector("[data-rjchip]")||tr)},
  {label:"Approve instead",icon:"check",run:()=>rjApproveInstead([g])},{label:"Put back in Review",icon:"undo",run:()=>rjUnreject([g])}]; }
/* R (and Shift+R): the highlighted rows, or the cursor row; minutes, reports and file changes are rejected as before */
export function rjKey315(){ const L=rvSel().filter(rvRejectOK); if(L.length){ rjMenuFor(L,$("#rvbar")&&!$("#rvbar").hidden?$("#bulkReject"):null); return; }
  const tr=$$("#reviewBody tr[data-n]")[shared.RSEL], r=tr&&REV.find(x=>x.n===+tr.dataset.n); if(!r||r.done) return;
  if(rvRejectOK(r)) rjMenuFor([r],tr.querySelector("[data-act=rr]")||tr); else if(isMin(r)) rejectMinutes(r); else decide(r.n,"rejected"); }
/* Activity › What you rejected */
export async function rjLoadRecent(){ if(!viaServer()){ rjRecent.value={state:"off",items:[]}; return; } rjRecent.value={...rjRecent.value,state:"loading"};
  const res=await api("/api/review/rejects",{limit:50}); rjRecent.value=res.ok?{state:"ok",items:res.items||[]}:{state:"error",items:[],message:oneLine(res.message)}; }
/* ===== end BL-315 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootReview0315(){
mountRejectMenu();
document.addEventListener("click",e=>{ const t=e.target; if(!t.closest) return; const b=t.closest("#reviewBody [data-rjchip],#reviewBody [data-rjrr],#reviewBody [data-rjok]"); if(!b) return; e.preventDefault(); e.stopPropagation();
  const key=b.dataset.rjchip||b.dataset.rjrr||b.dataset.rjok, g=rjGone.value.find(x=>x.key===key); if(!g) return;
  if(b.dataset.rjok) rjApproveInstead([g]); else rjReasonFor([rjRow(g)],b); },true);
}
/* BL-231: decide is a seam (a test replaces it); the setter lets the page's own calls see the replacement */
export const reviewSeams = { decide: v => { decide = v; } };
