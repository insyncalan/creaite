// @ts-check
/* review.js (BL-231 step 2b), moved from script/ by dev/tools/convert_area.py: 0060-review.js, 0061-bl-133-sprint-work-views.js, 0063-after-bl-216.js, 0064-bl-133-stage-b-sprint-work-views.js, 0065-bl-221-sprint-drafts-extraction.js, 0066-bl-218-sprint-drafts-extraction.js, 0067-after-bl-218.js, 0193-bl-200-sprint-review-work.js, 0195-bl-197-sprint-review-work.js, 0209-bl-208-sprint-insight.js.
   Unchanged apart from `export`, `shared.` for the shared state (core/state.js) and the load-time steps, now in
   boot…() functions that src/main.js calls in today's order. */

import { openDialog } from "./components/Dialog.jsx";
import { linkHtml, linkWords } from "./core/linkText.js";


import { actHref } from "./activity.js";
import { A, DEC, open, peopleAll, pName, R, REV, wsFor } from "./core/data.js";
import { $, $$, esc, html, ic, ICONS, raw } from "./core/dom.js";

import { srcShort, weekendNote, wkLong } from "./core/fields.js";


import { go } from "./core/nav.js";
import { D, fd, fdText, isMe, nowStamp, OPENST, prio, S, TODAY, who } from "./core/page.js";
import { api, apply, applyNow, applySoon, conflictChoice, editProposal, needVault, oneLine, refreshAll, reloadData, reviewViaServer, snack, TRKRELOAD, undoApply, viaServer } from "./core/server.js";
import { shared } from "./core/state.js";
import { deBarred, deItems, deMe, draftStat, openDraftEmail, shRvHtml } from "./drafts.js";
import { kb } from "./core/intakeApi.js";
import { withdrawDecision } from "./meetings.js";
import { drSame, msChoices, nextId, NODRAFT_MSG, openProposal, openRecord, pkCid, pkDow, PKK, pkStatuses, pkWho, REC } from "./panel.js";
import { closePanel } from "./projects.js";
import { nm, PERS, personLink, row, unknownOwner } from "./settings.js";
import { pkAdd } from "./today.js";
import { irTick } from "./stores/intakeReview.js";
import { mountRejectMenu } from "./components/review/RejectMenu.jsx";
import { openMinutesRecord, trackApprove, trackApprovedWords, trackFailWords, trackPutBack } from "./stores/minutes.js";
import { approveProblems } from "./components/minutes/track.js";

import { contextMenuOpen, openContextMenu } from "./components/review/ContextMenu.jsx";
import { closePicker, openPicker, pickerOpenFor } from "./components/Picker.jsx";
import { rjAddGone, rjDropGone, rjGone, rjGuessFor, rjGuesses, rjOpenMenu, rjReasons, rjRecent, rjSetGone } from "./stores/rejects.js";
import { batchMove, BK_STATUS, bkWhat, boardAsk, boardMove, HL, hlOnly, items, kOfId, recordFromBoard, rows, thisFriday } from "./work.js";     /* RHL: the highlighted rows (BL-122); a row that may be ticked is ticked too, so the two are one selection */
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
export let decide = async function(n,v,written,g){
  const res=await (async()=>{ let r=REV.find(x=>x.n===n);
  if(v==="approved"&&r&&TRKRELOAD){ const k=[r.file,String(r.ref)]; await TRKRELOAD; r=REV.find(x=>x.file===k[0]&&String(x.ref)===k[1]); if(r) n=r.n; }   /* #275 round 3: Intake's row Approve and A (irApprove) wait for the Track reload too, then take the row as the data now has it */
  if(!r||r.done) return; if(v==="approved"&&r.kind==="draft"&&r.nodraft){ snack(NODRAFT_MSG); return; }   /* BL-260 point 4 (fix-minutes-approve): never approved; Reject still works */
  if(v==="approved"&&!r.p&&r.kind!=="files"){ snack("Choose a project first — open the item to set it"); openProposal(n); return; }
  if(viaServer()&&v==="approved"&&isRecordMin(r)) return approveTracked(r,g);   /* #275: the Track column, as the minutes view's Approve minutes */
  if(v==="approved"&&r.trk!=null){ snack(`${r.trk==="n"?"Crossed":"Kept in the minutes only"} in the minutes' Track column: tick it there to register it`); return; }   /* #275 */
  if(viaServer()&&v==="approved"&&r.kind==="draft") return reviewViaServer(r,"approved",[]);
  if(viaServer()&&v==="approved"&&(r.flags||[]).includes("conflict")) return conflictChoice(r);
  if(v==="approved"&&r.kind==="draft"){ snack(`Approving a draft needs the live server, which checks and cleans it first; or say “approve ${r.rec.t.replace(/^Minutes: /,"minutes for ").replace(/^Report: /,"report for ")}” in Claude Code`); return; }   /* BL-149 */
  if(v==="approved"&&(r.flags||[]).includes("conflict")){ snack("This conflicts with a newer change: Keep current or Use this one needs the live server; or say “keep” or “override” in Claude Code (review)"); return; }   /* BL-149 */
  if(!written){ if(!await needVault()) return; try{ await editProposal(r.file,data=>setDecision(data,r,v)); }catch(e){ snack("Not saved: "+e.message); return; } }
  if(viaServer()&&S.autoApply){ r.done=v; refreshAll(); applySoon(); return; }
  let undoRec=()=>{};
  apply(`#${n} ${v==="approved"?"approved":"rejected"}: ${r.rec.t}`,()=>{ r.done=v; if(v==="approved") undoRec=applyProposal(r); },
    async()=>{ delete r.done; undoRec(); try{ await editProposal(r.file,data=>setDecision(data,r,"pending")); }catch(e){ snack(viaServer()?"Already applied: undo it in Activity":"Already applied: use “undo last apply” in Claude Code"); } },"You, in Intake"); })();   /* BL-149 */
  return res; };   /* BL-225: stays on the row */
/* #229 gate: what a user acts on or must notice stays visible beside the one meta line (never part of it): the weekend note with its buttons (BL-180), the "Drafted" tag (BL-218), the no-Word-draft notice (BL-260) */
const RV_WK=/<div class="wkrv">.*?<\/div>/, RV_DR=/<span class="tag drrv">.*?<\/span> /, RV_ND=/<span class="h-warn">No Word draft was made for these minutes<\/span> · Reject them and process the meeting again/;
export const rvTipText=r=>{ const d=(revDetail(r)||"").replace(RV_WK,"").replace(RV_DR,"").replace(RV_ND,"").replace(/ · <button type="button" class="linkbtn" data-drrisk="[^"]*">[^<]*<\/button>/,""); const t=d.replace(/<[^>]+>/g,"").replace(/&amp;/g,"&").replace(/&lt;/g,"<").replace(/&gt;/g,">").replace(/&quot;/g,'"').replace(/&#0?39;/g,"'").replace(/\s+/g," ").trim();
  /* #271: the line truncates with an ellipsis, so the tip ends with its reason and full source */
  const tail=[r.why,fdText(srcShort(r.src))].map(x=>String(x??"").trim()).filter(x=>x&&x!=="—").join(" · ");
  return t?[t,tail].filter(Boolean).join(" · "):""; };     /* no detail: the row's own fallback tip */
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
export const SPARKI='<path d="M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8z"/><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z"/>';
/* BL-41: the items extracted from draft minutes sit under them (same proposal file), in each project the meeting
   covers; items from mail, Teams, cx-edit or the dashboard stay at project level */
export const isMin=r=>r&&r.kind==="draft"&&r.ref==="meeting";
/* #275: minutes kept as a record (the minutes view's) are approved by their Track column, exactly as the view's Approve
   minutes (stores/minutes.trackApprove, the one implementation): a tick registers a work item, a cross takes the line out of
   the minutes, neither keeps it in the minutes untracked. A ticked item worth a look (an owner who needs details, a possible
   duplicate) opens the minutes with the view's Before approving box. Undo puts the apply back and the minutes exactly as they
   were (openMinutesRecord settles them). Ported onto the Intake page's decide (v26-line merge). */
export const isRecordMin=r=>isMin(r)&&/\.html$/i.test(r.src||"");
export async function approveTracked(r,g){ const v=await openMinutesRecord({file:r.file});
  if(!v||!v.ok){ snack(oneLine((v&&v.message)||"")||"Couldn't open the minutes"); return; }
  /* under one project of minutes covering several, only that project's ticked items are registered; the others wait in Review */
  const mine=g&&g!=="*"&&(r.projects||[]).length>1?new Set(REV.filter(x=>x.file===r.file&&!["draft","files"].includes(x.kind)&&(x.p||"?")===g).map(x=>x.ref)):null;
  if(v.doc&&v.plan&&approveProblems(v.doc,v.plan.items,unknownOwner).some(p=>!mine||mine.has(p.n))){ go("minutes",{file:r.file,approve:true}); return; }
  const res=await trackApprove(v,mine?{mine:n=>mine.has(n)}:{});
  if(!res.ok){ snack(trackFailWords(res,"Approve")); await reloadData(); return; }
  snack(trackApprovedWords(res),res.apply_id?async()=>{ await undoApply(res.apply_id); await openMinutesRecord({file:r.file}); await reloadData(); }:null);
  await reloadData(); }
/* #275 (Cap's M-c), on the Intake page's Approve routine (n) under minutes kept as a record (the old Review's Approve n routine,
   ported when Review retired): the Track column's crosses and neithers on the meeting's items first (trackApprove with approve
   false, the minutes view's changes), then the routine items, in one apply whose Undo also settles the minutes back, exactly as
   they were. The minutes, and an item approved one by one, still wait for their own Approve (the bulk rule). */
export async function approveRoutineTracked(m){ const v=await openMinutesRecord({file:m.file});
  if(!v||!v.ok){ snack(oneLine((v&&v.message)||"")||"Couldn't open the minutes"); return; }
  const item=x=>x.file===m.file&&!["draft","files"].includes(x.kind)&&!x.done, mine=new Set(REV.filter(item).map(x=>x.ref));
  const tr=await trackApprove(v,{only:n=>mine.has(n),approve:false}), made=tr.made;
  if(made) await reloadData();
  if(!tr.ok){ snack(trackFailWords(tr,"Approve routine")); return; }
  const ks=REV.filter(x=>item(x)&&rvBulkOK(x)), left=REV.filter(x=>item(x)&&!rvBulkOK(x)).length;
  let undo=null, out=[], got=ks.length;
  /* #275 round 3: an apply that stops puts the Track column's changes back too (trackPutBack), so the minutes are as they were */
  const putBack=async why=>{ const pb=made?await trackPutBack(v.path,tr.done||[]):{ok:true}; await reloadData();
    snack(`Approved 0 items from these minutes · ${why}${made?(pb.ok?" · the minutes are as they were":` · the minutes couldn't be put back (${pb.message||"try again"}): open them to check`):""}`); };
  if(ks.length){ const res=await rvDecideMany(ks,"approved"); undo=res.undo||null; out=trkLeftOut(res); got=res.n; if(res.stopped){ await putBack(out.join(" · ")); return; } }
  else if(made&&S.autoApply){ const res=await applyNow(); if(res.ok) undo=()=>undoApply(res.apply_id); else { await putBack(`apply stopped: ${oneLine(res.message)}`); return; } }
  const tail=made?` · ${made} line${made===1?"":"s"} taken out of the minutes or kept as lines only`:"";
  snack(`Approved ${got} item${got===1?"":"s"} from these minutes${tail}${left?` · ${left} still need approving one by one`:""}${out.length?" · "+out.join(" · "):""}`,
    undo?async()=>{ await undo(); await openMinutesRecord({file:m.file}); await reloadData(); }:null); }
export async function rejectMinutes(m){ await decide(m.n,"rejected"); const pend=REV.filter(x=>x.file===m.file&&!["draft","files"].includes(x.kind)&&!x.done);
  if(pend.length) snack(`Minutes rejected. Its ${pend.length} item${pend.length===1?"":"s"} stay for review.`,async()=>{ for(const k of pend) await decide(k.n,"rejected"); },`Reject ${pend.length===1?"it":"them"} too`); }                                     /* a batch over this asks first (a let, so a test can lower it) */
/* #232-B: the page's rule is the server's (review.hold_reason, carried on each row as `hold`; "" is routine, "invalid" is held back). A row without it (an edit made on the page) keeps the older test */
export const rvBulkOK=r=>!!r&&!r.done&&!(r.flags||[]).includes("invalid")&&("hold" in r?!r.hold:!r.indiv&&!!r.p&&!["draft","files"].includes(r.kind)&&!(r.flags||[]).includes("conflict"))&&r.trk==null;   /* #275: r.trk, crossed or neither in the minutes' Track column (build_dashboard, minutes_record.track_blocked) */
export const rvRejectOK=r=>!!r&&!r.done&&!["draft","files"].includes(r.kind);
/* why an item can't be approved in bulk, in words */
export function rvWhyNot(r){ if(!r.p&&r.kind!=="files") return ["project","needs a project"]; if((r.flags||[]).includes("conflict")) return ["conflict","has a conflict to settle"];
  if(r.trk!=null) return ["indiv",r.trk==="n"?"is crossed in the minutes' Track column":"is kept in the minutes only (Track: neither)"];   /* #275 */
  if(r.kind==="draft") return ["indiv",`${r.ref==="meeting"?"minutes are":"a report is"} approved on its own`]; if(r.kind==="files") return ["indiv","a file change is approved on its own"];
  return ["indiv",`${String(r.why||"this").toLowerCase()} is never approved in bulk`]; }
/* ── deciding several: one write per proposal file, one apply, one Undo ── */
/* #275 (Cap's re-review): an approval waits for a reload still bringing the Track choices (TRKRELOAD), then takes each row as the
   data now has it (REV's rows are replaced on a reload) and never one crossed or left with neither in the minutes (r.trk). Round 3:
   a row left out that way is returned (dropped) so the summary says why (trkLeftOut); an apply that stops puts the batch back to
   pending, so every row is on Intake again, and says so (stopped) rather than "Approved n" */
export async function rvDecideMany(list,v){ let dropped=[];
  if(v==="approved"){ if(TRKRELOAD) await TRKRELOAD; list=list.map(r=>r&&(REV.includes(r)?r:REV.find(x=>x.file===r.file&&String(x.ref)===String(r.ref))));
    dropped=list.filter(r=>r&&!r.done&&r.trk!=null); list=list.filter(r=>r&&r.trk==null); }
  list=list.filter(r=>r&&!r.done); if(!list.length) return {n:0,dropped}; if(!await needVault()) return {n:0,dropped};
  const byFile=new Map(); list.forEach(r=>{ if(!byFile.has(r.file)) byFile.set(r.file,[]); byFile.get(r.file).push(r); }); const done=[], failed=[];
  for(const [file,rs] of byFile){ try{ await editProposal(file,data=>rs.forEach(r=>setDecision(data,r,v))); done.push(...rs); }catch(e){ failed.push(...rs.map(r=>`#${r.n} (${e.message})`)); } }
  const undoFiles=async()=>{ for(const [file,rs] of byFile){ const mine=rs.filter(r=>done.includes(r)); if(mine.length) try{ await editProposal(file,data=>mine.forEach(r=>setDecision(data,r,"pending"))); }catch(e){} } };
  if(viaServer()&&S.autoApply){ done.forEach(r=>r.done=v); refreshAll(); const res=await applyNow();
    if(!res.ok){ await undoFiles(); done.forEach(r=>{ delete r.done; }); await reloadData(); return {n:0,failed,dropped,stopped:oneLine(res.message),res}; }
    return {n:done.length,failed,dropped,undo:()=>undoApply(res.apply_id),res}; }
  let undoRecs=[]; const what=`${done.length} proposal${done.length===1?"":"s"} ${v}`;
  apply(what,()=>{ done.forEach(r=>{ r.done=v; if(v==="approved") undoRecs.push(applyProposal(r)); }); },async()=>{ done.forEach(r=>delete r.done); undoRecs.forEach(u=>u()); undoRecs=[]; await undoFiles(); },"You, in Intake");
  return {n:done.length,failed,dropped,undo:shared.UNDO}; }
/* #275 round 3: what an rvDecideMany result left out, in words: an apply that stopped (all back on Intake) and the rows the Track
   reload left out (crossed, or kept in the minutes only) */
export function trkLeftOut(res){ const dr=(res&&res.dropped)||[], dn=dr.filter(r=>r.trk==="n").length, dk=dr.length-dn;
  return [res&&res.stopped?`apply stopped, all back on Intake: ${res.stopped}`:"",dn?`${dn} crossed in the minutes' Track column`:"",dk?`${dk} kept in the minutes only (Track: neither)`:""].filter(Boolean); }
export function rvSummary(verb,res,left){ const by={project:0,indiv:0,conflict:0}; left.forEach(r=>by[rvWhyNot(r)[0]]++);
  const parts=[...trkLeftOut({stopped:res.stopped}),by.project?`${by.project} need${by.project===1?"s":""} a project`:"",by.indiv?`${by.indiv} need${by.indiv===1?"s":""} individual approval`:"",by.conflict?`${by.conflict} ${by.conflict===1?"has a conflict":"have conflicts"}`:"",...trkLeftOut({dropped:res.dropped}),res.failed&&res.failed.length?`not saved: ${res.failed.join(", ")}`:""].filter(Boolean);
  const text=`${verb} ${res.n}${parts.length?" · "+parts.join(" · "):""}`;
  if(res.undo) snack(text,res.undo); else snack(text); }
/* a reload renumbers the proposals (review.py's order): the selection and the cursor follow them by file and item, not by number */
export const rvKey=r=>r.file+"|"+r.ref;
/* ===== end BL-133 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
/* ===== BL-133 stage B (sprint-work-views) =====
   Reject with a reason: the arrow beside Reject (a row's, and the bar's) or Shift+R opens Duplicate of <the possible duplicate>,
   Not mine to track, Not an action and Other; plain R still rejects at once. The reason (and the item a duplicate repeats) is
   written into the proposal (reject_reason, duplicate_of); the apply stores it in `rejected` and Activity shows it. A possible
   duplicate (build_dashboard.duplicate_hint: same project and type, open, token overlap ≥ review.duplicate_overlap) is tagged on
   the row and named in the panel, with Reject as duplicate. Nothing is merged and nothing is blocked beyond the fingerprint. */
export const RVREASON=new Map();
/* the panel names the possible duplicate */
/* ===== end BL-133 stage B ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
/* ===== BL-221 (sprint-drafts-extraction) ===== "Looks like": a proposal that repeats an item already in the tracker. Staging marks it
   (extraction.py: words, owner and workstream, plain code; the skill judges a close pair), and build_dashboard gives the row its `dup`:
   the item, where it is (same project, or another project's name), open or closed, and "Very likely" or "Possible", never a percentage.
   The row says "Looks like ORX-A-021 (same project, open) · Very likely"; the proposal's peek adds Compare (the two side by side, with
   the new source), Merge as an update (review.py merge through /api/review/repeat: any new date, latest update or response; nothing new
   rejects it as the duplicate), Keep as new (the mark goes) and Reject as a duplicate (BL-133's path, so the reason is recorded).
   Merge is offered only for an open item in the same project; across projects or onto a closed item it is Keep or Reject. */
export const llWhere=d=>`${d.same===false?pName(d.project):"same project"}, ${d.state||"open"}`;
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
    anchor=document.querySelector(`[data-rvrt="${r.n}"]`); if(!anchor) return; }
  openPicker(anchor,{role:"listbox",search:L.length>7,label:`Update which ${RTKINDS[r.kind]} instead`,options:L.map(c=>({v:c.id,label:`${c.id} · ${c.t}`,hint:rtHint(c)})),onPick:v=>rtGo(r,v)}); }
export async function rtGo(r,id){ const at={file:r.file,ref:r.ref};
  const res=await api("/api/review/retarget",{...at,id}); if(!res||!res.ok){ snack(oneLine(res&&res.message)||"Not changed"); return; }
  if(shared.CUR&&shared.CUR.mode==="proposal"&&shared.CUR.n===r.n) closePanel(); await reloadData();
  const dup=/duplicate/i.test(res.message||"");
  snack(dup?`Rejected as a duplicate of ${id}: it carried nothing new`:`Now an update to ${id}`,async()=>{ const back=await api("/api/review/retarget",{...at,undo:true});
    snack(back&&back.ok?"Back to a new item, as it was proposed":oneLine(back&&back.message)||"Not undone"); if(back&&back.ok) await reloadData(); }); }
/* ===== end BL-297 D ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
/* ===== BL-218 (sprint-drafts-extraction) ===== "Probably done": a closing update the sweep or the minutes staged because a sent mail, a
   reply, a Teams message or a meeting passage shows the item finished. Its row leads with the strength in a tag ("Looks done"; "Maybe
   done" says why; "Not done" re-dates it), then the evidence ("Mail 09-10-2026 15:02 by Sara Example: “attached the SOW”") beside the
   item's change, and the source opens as any row's does. Approve closes it; Reject with a reason (BL-133) records why, which the
   extraction reads next time. It is a closing update, so it is never covered by Approve routine (review.individual_only). */
export function dnHtml(r){ const d=r.dn, cls=d.strength==="Looks done"?"dn ok":d.strength==="Not done"?"dn warn":"dn";
  return `<span class="tag ${cls}">${esc(d.strength)}</span> <span class="dnev">${esc(d.ev)}</span>${d.reason?` <span class="sub">(${esc(d.reason)})</span>`:""}<br>`; }
/* ===== end BL-200 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
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
  const pa=t.closest("a[data-person]");   /* v2.3.0 #154: a linked name (not Alan's own, not in a field or the rail) gets the person menu; the row's own menu is the fallback */
  if(pa&&!t.closest("input,textarea,select,.rail,dialog,.cxmenu")&&!isMe(pa.dataset.person||"")&&pa.dataset.person){
    const row=pa.closest("[data-row]"), op=pa.closest("[data-open]"), id=row?row.dataset.row:op?String(op.dataset.open).split(":")[1]:pa.closest("#panel")&&shared.CUR&&shared.CUR.mode==="record"?pkCid():"";
    return {person:pa.dataset.person,only:id||"",el:pa}; }
  if(t.closest("input,textarea,select,[contenteditable=true],[contenteditable=plaintext-only],.rail,#panel,#chat,dialog,.cxmenu,.pkpop,td.editing")) return null;
  const a=t.closest("a[href]"); if(a&&!/^#/.test(a.getAttribute("href")||"")) return null;        /* a real link keeps the browser's menu */
  const row=t.closest("[data-row]"); if(row&&!row.closest("#actTbl")){ const id=row.dataset.row, inWork=!!row.closest("#workTbl,#workBoard"), k=row.dataset.k&&row.dataset.k!=="all"?row.dataset.k:inWork&&shared.WT!=="all"?shared.WT:kOfId(id);
    if(PKK.includes(k)&&REC(k,id)) return {k,id,el:row,row:inWork||!!row.closest("#v-person")}; }
  const o=t.closest("[data-open]"); if(o){ const [k,id]=String(o.dataset.open).split(":"); if(PKK.includes(k)&&REC(k,id)) return {k,id,el:o}; }
  return null; }
export function cxShow(c,x,y){ const from=document.activeElement&&document.activeElement!==document.body?document.activeElement:c.el;
  if(c.person){ openContextMenu(cxPerson(c.person,c.only),x,y,{label:c.person,from}); return; }
  let ids=[[c.k,c.id]];
  if(c.row){ if(HL.has(c.id)&&HL.size>=2) ids=[...HL.keys()].map(id=>[kOfId(id),id]).filter(([k,id])=>k&&REC(k,id)); else { hlOnly(c.k,c.id); } }
  openContextMenu(ids.length>1?cxWorkMany(ids):cxWork(c.k,c.id),x,y,{label:ids.length>1?`${ids.length} items`:c.id,from}); }
/* v2.3.0 #154: the menu on a linked person's name. Draft email opens the person page's own popup (openDraftEmail), with the item the
   click came from as the starting selection (only) when the person has it among their emailable items; no email on record: it is
   greyed with the reason, and Add details (for a name not on the register and for a registered person with no address) opens the person's page at its details. No counts, no modes. */
export function cxPerson(name,only){ const x=PERS().find(y=>y.name===name), p=x&&x.p, email=(p&&p.email)||"", first=String(name).split(/\s+/)[0],
    starts=only&&x&&deItems(x).some(i=>i.id===only&&!deBarred(i))?only:undefined, /** @type {any[]} */ out=[];
  out.push({label:"Draft email",icon:"mail",hint:email?"":"No email on record: the draft is still made, with nothing in To",run:()=>openDraftEmail(name,"update",starts)},   /* #247: a person with no email still gets a draft (Alan, 19-10-2026) */
    {label:`Open ${first}'s page`,icon:"user",run:()=>go("person",name)});
  if(email) out.push({label:"Copy email address",icon:"copy",run:()=>cxCopy(email,"the email address")});
  if(!email) out.push({label:"Add details",icon:"pencil",run:()=>{ go("person",name); let n=0; const tick=()=>{ const b=$("#ppEdit"); if(b){ b.click(); return; } if(++n<30) requestAnimationFrame(tick); }; tick(); }});
  return out; }
/* the focused row for Shift+F10 and the context-menu key: the focused element's item, or the list's cursor row */
export function cxCursor(){ const a=document.activeElement; let c=a&&a!==document.body?cxTarget(a):null; if(c) return c;
  if(a&&a!==document.body&&a.closest&&a.closest("input,textarea,select,[contenteditable],.rail,#chat,dialog,#panel")) return null;
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
  const who=k==="decisions"?null:pkWho(x.o); if(who&&PERS().some(p=>p.name===who)) { out.push({label:"Draft email",icon:"mail",desc:"Asks for an update (update request)",run:()=>openDraftEmail(who)}); if(x.due&&x.due<TODAY&&OPENST(x.st)&&!deMe(who)) out.push({label:"Draft email",icon:"mail",desc:"Chases this overdue item (chase)",run:()=>openDraftEmail(who,"chase")}); }   /* BL-224 */
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
/* ===== end BL-208 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
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
/* the guesses, fetched once for each set of pending rows (core/server.js refreshAll asks for them while the Intake page is open) */
export async function rjLoadGuesses(){ if(!viaServer()) return; const sig=REV.filter(r=>!r.done).map(rjKey).join(","); if(sig===rjGuessFor.value) return; rjGuessFor.value=sig;
  const res=await api("/api/review/guesses",{}); if(!res.ok) return; if(Array.isArray(res.reasons)&&res.reasons.length) rjReasons.value=res.reasons;
  const /** @type {Record<string, any>} */ g={}; (res.guesses||[]).forEach(x=>{ g[`${x.file}#${x.ref}`]={reason:x.reason,why:x.why||"",of:x.of||null}; });
  if(JSON.stringify(g)===JSON.stringify(rjGuesses.value)) return; rjGuesses.value=g; }
const rjExpanded=(a,on)=>{ if(a&&a.getAttribute&&a.getAttribute("aria-haspopup")) a.setAttribute("aria-expanded",String(on)); };
/* the menu, to reject pending rows */
export function rjMenuFor(list,anchor,after,before){ list=list.filter(rvRejectOK); if(!list.length) return; rjExpanded(anchor,true);
  rjOpenMenu({rows:list.map(rjRow),anchor:anchor||null,mode:"reject",guesses:viaServer(),onPick:c=>{ if(before) before(); rjReject(list,c,after); },onClose:()=>rjExpanded(anchor,false),
    candidates:viaServer()?async()=>{ const r=list.find(x=>!rjDupOf(x))||list[0], res=await api("/api/review/candidates",{file:r.file,ref:r.ref}); return res.ok?res.items||[]:[]; }:undefined}); }
/* the menu, to change rejects' reason (a greyed row's chip or ▾, Activity's list) */
export function rjReasonFor(rows,anchor){ if(!rows.length) return; rjExpanded(anchor,true);
  rjOpenMenu({rows,anchor:anchor||null,mode:"reason",guesses:viaServer(),onPick:c=>rjRereason(rows,c),onClose:()=>rjExpanded(anchor,false),candidates:viaServer()?async()=>[]:undefined}); }   /* a reject is no longer pending: its Duplicate item is typed */
/* the batch's one message: the status line under the bar, and the message at the foot with Undo */
export function rjSay(text,undo){ snack(text,undo||null); }
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
    if(list.length===1) await decide(list[0].n,"rejected"); else { const res=await rvDecideMany(list,"rejected"); rvSummary("Rejected",res,[]); }
    rjAddGone(G.filter(g=>REV.some(r=>rvKey(r)===g.rk&&r.done==="rejected"))); if(after) after(); return; }
  const done=[], msgs=[];
  for(const {body,L} of rjBy(list,r=>c.guess?{guess:true}:{reason:c.reason||"",duplicate_of:dupOf(r)||""})){
    const res=await api("/api/review/reject",{rows:L.map(r=>({file:r.file,ref:r.ref})),...body});
    if(res.ok) (res.rejected||[]).forEach(x=>{ const r=L.find(y=>y.file===x.file&&String(y.ref)===String(x.ref)); if(r) done.push(r); }); else msgs.push(oneLine(res.message)); }
  if(!done.length){ snack("Not rejected: "+(msgs[0]||"nothing changed")); return; }
  const G=done.map(r=>rjGhost(r,why(r),dupOf(r)));
  done.forEach(r=>{ r.done="rejected"; });
  rjAddGone(G); irTick.value++;
  const ap=S.autoApply?await applyNow():(await reloadData(),null);
  const n=done.length, text=`Rejected ${n===1?"1":n} ${how}`+(ap&&!ap.ok?` · not applied: ${oneLine(ap.message)}`:"")+(msgs.length?` · not rejected: ${msgs[0]}`:"");
  rjSay(text,()=>rjUnreject(G));
  if(after) after(); }
async function rjRejected(rows,how,extra){ return api("/api/review/rejected",{rows:rows.map(r=>({file:r.file,ref:r.ref})),how,...(extra||{})}); }
const rjOff=what=>{ snack(`${what} needs the live server; or say “review” in Claude Code`); };
/* Undo a reject (pending or applied): back in Intake, waiting */
export async function rjUnreject(rows){ if(!viaServer()){ rjOff("Putting a reject back"); return; }
  const res=await rjRejected(rows,"undo"); if(!res.ok){ snack("Not undone: "+oneLine(res.message)); return; }
  const keys=rows.map(r=>r.key||rjKey(r)); rjDropGone(keys); await reloadData();
  if(shared.VIEW==="activity") rjLoadRecent();
  snack(`Back in Intake: ${keys.length}`); }
/* Change rejects' reason: one reason, each row's guess, or none; Undo puts each one's earlier reason back */
export async function rjRereason(rows,c,quiet){ if(!viaServer()){ rjOff("Changing a reason"); return; }
  const body=r=>{ if(c.guess){ const g=r.guess; return {reason:g?g.reason:"",duplicate_of:g&&g.reason==="Duplicate"&&g.of||""}; } return {reason:c.reason||"",duplicate_of:c.reason==="Duplicate"?c.dup||r.dup||"":""}; };
  const done=[], msgs=[];
  for(const {body:b,L} of rjBy(rows,body)){ const res=await rjRejected(L,"reason",b); if(res.ok){ (res.done||[]).forEach(d=>done.push({...d,now:b})); } else msgs.push(oneLine(res.message)); }
  if(!done.length){ snack("Not changed: "+(msgs[0]||"nothing changed")); return; }
  done.forEach(d=>rjSetGone([d.key],()=>({reason:d.now.reason||null,dup:d.now.duplicate_of||null})));
  if(S.autoApply) await applyNow(); else await reloadData(); if(shared.VIEW==="activity") rjLoadRecent();
  if(quiet) return;
  const to=c.guess?"their guesses":c.reason?c.reason+(c.reason==="Duplicate"&&(c.dup||rows.length===1&&rows[0].dup)?` of ${c.dup||rows[0].dup}`:""):"no reason";
  const back=done.map(d=>({...rjRef(d.key),key:d.key,was:d.was||{}}));
  rjSay(`Reason changed to ${to}`+(msgs.length?` · not changed: ${msgs[0]}`:""),async()=>{
    for(const {body:b,L} of rjBy(back,x=>({reason:x.was.reason||"",duplicate_of:x.was.duplicate_of||""}))) await rjRereason(L.map(x=>({...x,dup:b.duplicate_of||null})),{reason:b.reason||null,dup:b.duplicate_of||null},true);
    snack("Reason put back"); }); }
/* Approve instead: the reject undone and the item approved in one step; one approved only on its own goes back to Intake, opened */
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
  if(open.length){ const L=REV.filter(x=>open.includes(rjKey(x))&&!x.done); if(L.length){ if(shared.VIEW!=="intake-review") go("intake-review"); openProposal(L[0].n); } } }
/* Activity › What you rejected */
export async function rjLoadRecent(){ if(!viaServer()){ rjRecent.value={state:"off",items:[]}; return; } rjRecent.value={...rjRecent.value,state:"loading"};
  const res=await api("/api/review/rejects",{limit:50}); rjRecent.value=res.ok?{state:"ok",items:res.items||[]}:{state:"error",items:[],message:oneLine(res.message)}; }
/* ===== end BL-315 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
/* #232-C2: the listeners that outlive the old Review page. They serve the Intake page's rows and the peek, and Today (they were in bootReview0064, 0065, 0067 and 0315). */
export function bootProposalActions(){
mountRejectMenu();
document.addEventListener("click",e=>{
  const d=e.target.closest("[data-rvdup]"); if(d){ e.stopPropagation(); const r=REV.find(x=>x.n===+d.dataset.rvdup); if(!r||r.done) return; closePanel(); rjReject([r],{reason:"Duplicate",dup:r.dup.id}); } },true);   /* Reject as a duplicate, from the peek */
document.addEventListener("click",e=>{ const b=e.target.closest&&e.target.closest("[data-rvrt]"); if(!b) return; e.preventDefault(); e.stopPropagation();
  const r=REV.find(x=>x.n===+b.dataset.rvrt); if(pickerOpenFor(b)){ closePicker(); return; } rtOpen(b,r); },true);   /* BL-297 D */
document.addEventListener("click",e=>{ const b=e.target.closest("[data-rvll]"); if(!b) return; e.preventDefault(); e.stopPropagation();
  const [how,n]=b.dataset.rvll.split(":"), r=REV.find(x=>x.n===+n); if(!r||!rvDup(r)) return; if(how==="cmp") llCompare(r); else llAct(how,r); },true);
$("#llDlg").addEventListener("click",e=>{ const dlg=$("#llDlg"), r=REV.find(x=>x.n===+dlg.dataset.n); if(e.target.id==="llClose") dlg.close();
  else if(e.target.id==="llMerge"){ dlg.close(); llAct("merge",r); } else if(e.target.id==="llKeep"){ dlg.close(); llAct("keep",r); } });
document.addEventListener("click",e=>{ const a=e.target.closest("[data-appr]"); if(a){ e.stopPropagation(); decide(+a.dataset.appr,"approved"); return; } const o=e.target.closest("[data-revopen]"); if(o&&!e.target.closest("[data-appr]")){ go("intake-review"); openProposal(+o.dataset.revopen); } });
}
export function bootContextMenu(){
Object.assign(ICONS,{cxopen:'<path d="M14 4h6v6M10 14L20 4M19 13v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h6"/>'});
document.addEventListener("contextmenu",e=>{ if(performance.now()-CXKEYAT<400){ e.preventDefault(); return; }   /* the key opened it already */
  const kb=!e.clientX&&!e.clientY; let c=cxTarget(e.target); if(!c&&kb) c=cxCursor(); if(!c) return;
  e.preventDefault(); const r=c.el.getBoundingClientRect(); cxShow(c,kb?r.left+Math.min(48,r.width/3):e.clientX,kb?r.top+Math.min(r.height,28):e.clientY); });
window.addEventListener("keydown",e=>{ if(!(e.key==="ContextMenu"||(e.key==="F10"&&e.shiftKey))||contextMenuOpen()) return; const c=cxCursor(); if(!c) return;
  e.preventDefault(); e.stopPropagation(); CXKEYAT=performance.now(); const r=c.el.getBoundingClientRect(); c.el.scrollIntoView({block:"nearest"}); cxShow(c,r.left+Math.min(48,r.width/3),r.top+Math.min(r.height,28)); },true);
}
/* BL-231: decide is a seam (a test replaces it); the setter lets the page's own calls see the replacement */
export const reviewSeams = { decide: v => { decide = v; } };
