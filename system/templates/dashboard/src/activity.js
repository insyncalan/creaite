// @ts-check
/* activity.js (BL-231 step 2b), moved from script/ by dev/tools/convert_area.py: 0070-activity.js, 0071-bl-164-sprint-rail.js, 0072-after-bl-164-js.js, 0205-bl-233-sprint-drafts-extraction.js.
   Unchanged apart from `export`, `shared.` for the shared state (core/state.js) and the load-time steps, now in
   boot…() functions that src/main.js calls in today's order. */
import { renderAskChanges } from "./ask.js";
import { A, DEC, P, pName, R } from "./core/data.js";
import { $, $$, addHTML, esc, html, ibtn, ic, ICONS, putHTML, raw } from "./core/dom.js";
import { parseWhen } from "./core/fields.js";
import { typing } from "./core/keys.js";
import { go, navWrite } from "./core/nav.js";
import { D, DATE, fd, KI, nowStamp } from "./core/page.js";
import { api, oneLine, refreshAll, reloadData, snack, undoApply, viaServer } from "./core/server.js";
import { shared } from "./core/state.js";
import { msFind } from "./milestones.js";
import { REC } from "./panel.js";
import { HL, hlClear, hlPick, hlToggle } from "./work.js";
import { mountRejectsList } from "./components/review/RejectsList.jsx";
import { rjApproveInstead, rjLoadRecent, rjReasonFor, rjUnreject } from "./review.js";
/* ======================= Activity ======================= */
/* BL-43: each line names the item: the ID (a link to it), its text cut to about 80 characters (full text on hover),
   then the change. Lines the dashboard adds before a reload are shown the same way, from the item's current text. */
export const ID_RE=/^([A-Z][A-Z0-9]{2,6}(?:-[AMD])?-\d{3}|[A-Z][A-Z0-9]{2,6})(?=[\s·:])/;
export function itemText(id){ const x=A.find(a=>a.id===id)||R.find(r=>r.id===id)||DEC.find(d=>d.id===id); if(x) return x.t;
  const m=(D.milestone_names||{})[id]; if(m) return m[0]; const p=P.find(p=>p.code===id); return p?p.name:""; }
/* BL-144: the link's own address, for Cmd-click or a middle click: an item opens in Work (#work=actions&p=ABC&item=ABC-A-003),
   a milestone on its project's page. A plain click opens the panel on Activity and never follows it. */
export function actHref(kind,id){ if(kind==="ms"){ const f=msFind(id); return f&&f.p?`#cockpit=${f.p.code}`:"#"; }
  const x=REC(kind,id); return x?`#work=${kind}${x.p?`&p=${x.p}`:""}&item=${id}`:"#"; }
export function actLine(a){ let id=a.id, text=a.item, change=a.change;
  if(!id){ const m=String(a.what).match(ID_RE); if(!m) return html`${String(a.what??"")}`; id=m[1]; text=itemText(id); change=a.what.slice(id.length).replace(/^[\s·:]+/,""); }
  if(!text) return html`${String(a.what??"")}`;
  const short=text.length>80?text.slice(0,79)+"…":text, kind=/-A-/.test(id)?"actions":/-D-/.test(id)?"decisions":/-M-/.test(id)?"ms":/-\d{3}$/.test(id)?"raid":/^[A-Z][A-Z0-9]{2,6}$/.test(id)?"proj":"";
  const ch=String(change??"");
  if(kind==="proj") return html`<a href="#" class="hlink" data-proj="${id}">${pName(id)}</a> — ${ch}`;     /* BL-101: a project is its name */
  const upd=id.match(/^(\d{4}-\d{2}-\d{2})\|([A-Z][A-Z0-9]{2,6})$/); if(upd) return html`<a href="#" class="hlink" data-proj="${upd[2]}">${pName(upd[2])}</a> · weekly update, week ending ${fd(upd[1])} — ${ch}`;
  const link=kind==="ms"?html`<a href="${actHref(kind,id)}" class="hlink" data-ms="${id}">${id}</a>`:kind&&itemText(id)?html`<a href="${actHref(kind,id)}" class="hlink" data-open="${kind}:${id}">${id}</a>`:String(id??"");
  return html`${link} · <span title="${text}">${short}</span> — ${ch}`; }
/* ===== BL-164 (sprint-rail) ===== Activity: a type icon on each entry, search and filters (in the address), and undo of several past
   changes. The icon comes from ic()'s set with the type's name as its tooltip and accessible name (never colour alone). The filters
   (ACTF: q, types, from, to) narrow ACT, the newest lines the builder returns; they live in the address (#activity&q=…&type=…) and
   survive opening an item and Back. Selection is the Work lists' (BL-122: HL with k "act", hlPick, hlToggle, hlClear); a line can be
   chosen when the builder gave it a rowid (tracker.py undo-changes could put it back). The latest apply keeps its exact Undo; a
   selection that is the whole latest apply uses it. Anything else goes through a confirm built from a dry run, then one new apply. */
export const ACTKINDS=[["action","Action","action"],["Risk","Risk","risk"],["Issue","Issue","issue"],["Assumption","Assumption","assumption"],["Dependency","Dependency","dependency"],
  ["decision","Decision","decision"],["milestone","Milestone","milestone"],["project","Project","projects"],["update","Weekly update","filetext"],["workstream","Workstream","work"],
  ["promise","Promise","handover"],["label","Label","label"],["setting","Setting","gear"],["file","File","folder"],["rejected","Rejected proposal","x"],["revert","Undo","undo"]];
export const actKindOf=k=>ACTKINDS.find(x=>x[0]===k);
export const actId=a=>a.id||(String(a.what||"").match(ID_RE)||[])[1]||"";
export function actKind(a){ if(a.kind) return a.kind; const id=actId(a);
  if(/-A-\d{3}$/.test(id)) return "action"; if(/-D-\d{3}$/.test(id)) return "decision"; if(/-M-\d{3}$/.test(id)) return "milestone";
  if(/^[A-Z][A-Z0-9]{2,6}-\d{3}$/.test(id)){ const r=R.find(x=>x.id===id); return (r&&r.type)||"Risk"; }
  if(/^\d{4}-\d{2}-\d{2}\|/.test(id)) return "update"; if(/^[A-Z][A-Z0-9]{2,6}$/.test(id)) return "project";
  return /^setting/i.test(String(a.what||""))?"setting":""; }
export const actIcon=a=>{ const k=actKindOf(actKind(a)); return k?html`<span class="acticon" role="img" aria-label="${k[1]}" data-tip="${k[1]}">${raw(ic(k[2]))}</span>`:""; };
shared.ACTF={};                                      /* {q, types:[], from, to}: what Activity is narrowed to */
export const actOn=()=>!!((shared.ACTF.q||"").trim()||(shared.ACTF.types||[]).length||shared.ACTF.from||shared.ACTF.to);
export const actProj=a=>{ const c=(actId(a).match(/^(?:\d{4}-\d{2}-\d{2}\|)?([A-Z][A-Z0-9]{2,6})/)||[])[1]; return c&&P.some(p=>p.code===c)?pName(c):""; };
export const actHay=a=>[actId(a),a.item,a.what,a.change,a.by,actProj(a),fd(a.at),a.at,(actKindOf(actKind(a))||[])[1]].join(" ").toLowerCase();
export function actMatch(a){ const q=(shared.ACTF.q||"").trim().toLowerCase(); if(q&&!q.split(/\s+/).every(w=>actHay(a).includes(w))) return false;
  if((shared.ACTF.types||[]).length&&!shared.ACTF.types.includes(actKind(a))) return false;
  const d=String(a.at||"").slice(0,10); if(shared.ACTF.from&&d<shared.ACTF.from) return false; if(shared.ACTF.to&&d>shared.ACTF.to) return false; return true; }
export function actTools(){ let box=$("#actTools"); if(!box) return; box.hidden=!shared.ACT.length;
  if(!$("#actQ")) putHTML(box,html`<div class="acttools"><label class="actsearch">${raw(ic("search"))}<input type="search" id="actQ" placeholder="Search Activity: ID, words, project, person, date" aria-label="Search Activity" autocomplete="off"><kbd aria-hidden="true">/</kbd></label>
      <span id="actCount" aria-live="polite"></span><button type="button" class="linkbtn" id="actClear" data-actclear hidden>Clear</button>
      <span class="actdates"><label for="actFrom">From</label><input type="text" id="actFrom" data-date="1" placeholder="DD-MM-YYYY" autocomplete="off"><label for="actTo">to</label><input type="text" id="actTo" data-date="1" placeholder="DD-MM-YYYY" autocomplete="off"></span>
      <div id="actTypes" role="group" aria-label="Show only these types"></div></div>`);
  const q=$("#actQ"); if(document.activeElement!==q&&q.value!==(shared.ACTF.q||"")) q.value=shared.ACTF.q||"";
  [["actFrom","from"],["actTo","to"]].forEach(([id,k])=>{ const el=$("#"+id); if(document.activeElement!==el) el.value=shared.ACTF[k]?fd(shared.ACTF[k]):""; });
  const have=new Set(shared.ACT.map(actKind)), types=shared.ACTF.types||[], foc=document.activeElement&&document.activeElement.dataset&&document.activeElement.dataset.acttype;
  putHTML($("#actTypes"),html`${ACTKINDS.filter(k=>have.has(k[0])||types.includes(k[0])).map(k=>html`<button type="button" class="vchip" data-acttype="${k[0]}" aria-pressed="${String(types.includes(k[0]))}">${raw(ic(k[2]))}${k[1]}</button>`)}`);
  if(foc) $(`#actTypes [data-acttype="${foc}"]`)?.focus(); }
export function actRow(a,i){ const rid=a.rowid&&!a.reverted&&!a.undone?`r${a.rowid}`:"";
  const end=a.reverted?html`<span class="x actundone" title="Put back by a later undo">undone</span>`:a.undo?raw(ibtn("undo","Undo this change",html`data-undoact="${i}"`,"sm"))
    :viaServer()&&a.apply_id&&a.apply_id===D.latest_apply&&!a.undone?raw(ibtn("undo","Undo this apply",html`data-undoapply="${a.apply_id}"`,"sm")):html`<span class="x" title="Only the latest apply can be undone here; tick older changes to undo them">Applied</span>`;
  return html`<tr${rid?html` data-row="${rid}"`:""}${a.reverted?html` class="undone"`:""}><td class="actck">${rid?html`<input type="checkbox" aria-label="Select: ${actId(a)} ${a.change||a.what||""}">`:""}</td><td class="actwhen" style="white-space:nowrap">${fd(a.at)}</td><td class="actchg">${actIcon(a)}${actLine(a)}</td><td class="x">${a.by}</td><td style="text-align:right">${end}</td></tr>`; }
export const ACTSHOW=300;
export function renderActivity(){ actTools(); [...HL].forEach(([id,k])=>{ if(k!=="act") HL.delete(id); });
  const LA=shared.ACT.map((a,i)=>[a,i]).filter(([a])=>actMatch(a)), on=actOn(), L=on?LA:LA.slice(0,ACTSHOW);   /* tidy-up (sprint-milestones): search looks through every line read; the list shows the newest 300 until then */
  $("#actCount").textContent=on?`${L.length} of ${shared.ACT.length}`:`${L.length} of ${shared.ACT.length}`; $("#actClear").hidden=!on;
  const what=[(shared.ACTF.q||"").trim()?`“${shared.ACTF.q.trim()}”`:"",(shared.ACTF.types||[]).map(t=>(actKindOf(t)||[,t])[1]).join(" or "),shared.ACTF.from?`from ${fd(shared.ACTF.from)}`:"",shared.ACTF.to?`to ${fd(shared.ACTF.to)}`:""].filter(Boolean).join(", ");
  putHTML($("#actTbl"),html`${L.length?html`<table><thead><tr><th class="actck"><span class="actvh">Select</span></th><th>When</th><th>Change</th><th>By</th><th></th></tr></thead><tbody>${L.map(([a,i])=>actRow(a,i))}</tbody></table>`
      :html`<div class="empty">Nothing matches ${what||"these filters"} in the changes shown here. <button type="button" class="btn" data-actclear>Clear</button></div>`}${!on&&LA.length>L.length&&html`<p class="sub" id="actMore" style="margin:10px 14px">The newest ${L.length} of ${LA.length} changes. Search or filter to look through all of them.</p>`}<p class="sub" id="actCap" ${raw(D.activity_capped?"":"hidden")} style="margin:10px 14px">These are the newest 2,000 changes (search and filters look at these). Older ones are kept in the tracker's change log.</p>`);
  const vis=new Set($$("#actTbl tr[data-row]").map(t=>t.dataset.row)); [...HL.keys()].forEach(id=>{ if(!vis.has(id)) HL.delete(id); }); if(shared.HLA!=null&&!vis.has(shared.HLA)) shared.HLA=null; if(shared.HLC!=null&&!vis.has(shared.HLC)) shared.HLC=null;
  actPaint(); renderAskChanges();
  if(!shared.LOADING&&!shared.ACT.length) putHTML($("#actTbl"),html`<div class="empty">Nothing has changed yet. What you approve, edit or apply shows here, newest first, with Undo. <a href="#" data-go="review">Open Review</a></div>`); }
export const actSel=()=>[...HL].filter(([,k])=>k==="act").map(([id])=>+id.slice(1));
export function actPaint(){ $$("#actTbl tr[data-row]").forEach(tr=>{ const on=HL.has(tr.dataset.row); tr.classList.toggle("hl",on); tr.classList.toggle("cur",tr.dataset.row===shared.HLC); const cb=tr.querySelector("input[type=checkbox]"); if(cb) cb.checked=on; });
  const n=actSel().length, bar=$("#actBar"); if(!bar) return; bar.hidden=!n;
  putHTML(bar,html`${n>0&&html`<span class="bkn" aria-live="polite">${n} selected:</span><button type="button" class="btn" id="actUndoSel" ${!viaServer()&&html`disabled title="Undoing needs the live server"`}>${raw(ic("undo"))}Undo ${n}</button><span class="sp"></span><button type="button" class="ib" data-actselclear aria-label="Clear the selection" data-tip="Clear the selection" data-key="Esc">${raw(ic("x"))}</button>`}`); }
export function actFilter(ch){ Object.assign(shared.ACTF,ch); renderActivity(); try{ navWrite(false); }catch(e){} }
   /* Shift-click picks a range, not text */
/* "/" searches Activity while it is open (elsewhere it is still ask creaite); Esc clears the selection before anything else */
export const actTyping=()=>typing()&&!document.activeElement.matches("input[type=checkbox]");   /* a tick box has the focus after a click: not typing */
/* the address: #activity&q=…&type=Risk,action&from=YYYY-MM-DD&to=… (also read with "?" after activity) */
/* undo several: the whole latest apply uses its exact undo; anything else is planned (a dry run), confirmed, then done as one apply */
export const ACT_ASK_AGAIN=25;
export async function actUndoSelected(){ const ids=actSel(); if(!ids.length) return; if(!viaServer()){ snack("Undoing needs the live server"); return; }
  const latest=D.latest_apply, whole=shared.ACT.filter(a=>a.rowid&&!a.reverted&&a.apply_id===latest).map(a=>a.rowid);
  if(latest&&whole.length&&ids.length===whole.length&&ids.every(r=>whole.includes(r))){ hlClear(); actPaint(); await undoApply(latest); return; }
  const plan=await api("/api/undo-changes",{rowids:ids,dry_run:true}); if(!plan.ok){ snack("Not undone: "+oneLine(plan.message)); return; }
  actConfirm(ids,plan); }
export function actPlanLine(d){ const val=v=>v==null||v===""?"—":DATE.test(String(v).slice(0,10))?fd(String(v)):String(v), f=String(d.field||"").replace(/_/g," ");
  if(d.why) return `<li class="skip"><b>${esc(d.id||"#"+d.rowid)}</b> · ${esc(f)} · skipped: ${esc(d.why)}</li>`;
  if(d.change==="removed") return `<li><b>${esc(d.id)}</b> · removed (that change created it)</li>`;
  if(d.change==="put back") return `<li><b>${esc(d.id)}</b> · put back</li>`;
  const t=itemText(d.id); return `<li><b>${esc(d.id)}</b>${t?` <span class="sub">${esc(t.length>60?t.slice(0,59)+"…":t)}</span>`:""} · ${esc(f)} ${esc(val(d.from))} → ${esc(val(d.to))}</li>`; }
export function actConfirm(ids,plan){ let dlg=$("#actDlg"); if(!dlg){ addHTML(document.body,"beforeend",html`<dialog id="actDlg" aria-labelledby="actDlgH"></dialog>`); dlg=$("#actDlg"); }
  const done=plan.done||[], skipped=plan.skipped||[], n=done.length; let asked=false;
  putHTML(dlg,html`<h2 id="actDlgH" style="margin:0 0 6px">${n?html`Undo ${raw(n)} change${n===1?"":"s"}?`:"Nothing here can be undone"}</h2>
    <p class="sub" id="actDlgAsk" style="margin:0 0 10px">${n?"Each goes back to what it was before, only where it still holds the value that change gave it. It is one new apply, so you can undo it too.":html`Each of these has changed since, or can't be put back here.`}</p>
    <ul class="actplan">${raw(done.map(actPlanLine).join(""))}${raw(skipped.map(actPlanLine).join(""))}</ul>
    <div class="curacts"><span class="sp"></span><button type="button" class="btn" id="actDlgCancel">${n?"Cancel":"Close"}</button>${n?html`<button type="button" class="btn primary" id="actDlgGo">Undo ${raw(n)}</button>`:""}</div>`);
  $("#actDlgCancel").onclick=()=>dlg.close();
  if(n) $("#actDlgGo").onclick=async()=>{ if(n>ACT_ASK_AGAIN&&!asked){ asked=true; $("#actDlgAsk").textContent=`This undoes ${n} changes at once. Are you sure? (It can itself be undone.)`; $("#actDlgGo").textContent=`Yes, undo ${n}`; $("#actDlgGo").focus(); return; }
    const go=$("#actDlgGo"); go.disabled=true; const r=await api("/api/undo-changes",{rowids:ids}); dlg.close(); hlClear(); await reloadData(); actPaint();
    snack(r.ok?oneLine(r.message):"Not undone: "+oneLine(r.message),r.ok&&r.apply_id?()=>undoApply(r.apply_id):null); };
  dlg.showModal(); ($("#actDlgGo")||$("#actDlgCancel")).focus(); }
/* ===== end BL-164 (JS) ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootActivity0071(){
Object.assign(ICONS,{action:KI.action,risk:KI.Risk,issue:KI.Issue,assumption:KI.Assumption,dependency:KI.Dependency,decision:KI.decision,milestone:KI.milestone,
  label:'<path d="M20.6 13.4 13.4 20.6a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8z"/><circle cx="7.5" cy="7.5" r="1.2"/>'});
document.addEventListener("input",e=>{ if(e.target.id==="actQ") actFilter({q:e.target.value}); });
document.addEventListener("change",e=>{ const t=e.target; if(t.id!=="actFrom"&&t.id!=="actTo") return; const v=t.value.trim(), iso=v?parseWhen(v):"";
  if(v&&!iso) return; actFilter({[t.id==="actFrom"?"from":"to"]:iso||""}); });
document.addEventListener("click",e=>{ const t=e.target;
  const ty=t.closest&&t.closest("#actTypes [data-acttype]"); if(ty){ const k=ty.dataset.acttype, L=[...(shared.ACTF.types||[])]; actFilter({types:L.includes(k)?L.filter(x=>x!==k):[...L,k]}); return; }
  if(t.closest&&t.closest("[data-actclear]")){ e.preventDefault(); shared.ACTF={}; renderActivity(); try{ navWrite(false); }catch(x){} $("#actQ")?.focus(); return; }
  if(t.closest&&t.closest("[data-actselclear]")){ hlClear(); actPaint(); return; }
  if(t.closest&&t.closest("#actUndoSel")){ actUndoSelected(); return; } });
$("#actTbl").addEventListener("click",e=>{ const tr=e.target.closest("tr[data-row]"); if(!tr) return;
  if(e.target.matches("input[type=checkbox]")){ hlToggle("act",tr.dataset.row); actPaint(); return; }
  if(e.target.closest("a,button,input,select,textarea,label,[data-proj],[role=link]")) return;   /* a link or a button does its own job */
  hlPick(e,"act",tr.dataset.row); actPaint(); });
$("#actTbl").addEventListener("mousedown",e=>{ if(e.shiftKey&&e.target.closest("tr[data-row]")) e.preventDefault(); });
document.addEventListener("keydown",e=>{ if(shared.VIEW!=="activity") return;
  if(e.key==="/"&&!e.metaKey&&!e.ctrlKey&&!e.altKey&&!actTyping()&&!document.querySelector("dialog[open]")&&!$("#chat").classList.contains("on")){ e.preventDefault(); e.stopImmediatePropagation(); $("#actQ")?.focus(); $("#actQ")?.select(); return; }
  if(e.key==="Escape"&&actSel().length&&!document.querySelector("dialog[open]")&&!$("#panel").classList.contains("on")&&!actTyping()){ e.preventDefault(); e.stopImmediatePropagation(); hlClear(); actPaint(); } },true);
}

/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootActivity0072(){
$("#actTbl").addEventListener("click",e=>{ const u=e.target.closest("[data-undoapply]"); if(u){ undoApply(+u.dataset.undoapply); return; } const b=e.target.closest("[data-undoact]"); if(!b) return; const a=shared.ACT[+b.dataset.undoact]; a.undo(); shared.ACT.splice(+b.dataset.undoact,1); shared.ACT.unshift({at:nowStamp(),what:`Undone: ${a.what}`,by:"You, in Activity"}); refreshAll(); snack("Change reversed"); });
}
/* ===== BL-233 (sprint-drafts-extraction) ===== Activity › Quality. What you approve, edit and reject, by source (minutes, sweep mail,
   sweep Teams, dashboard) and by type, the reasons given, the fields edits change most (BL-232's as_proposed; an edit from before it is
   "field unknown"), and each AI-draft feature's use (draft-stats.json). quality.py works it out, read-only, when the page is built
   (D.quality). Every figure is a count out of its total ("11 of 192"), never a bare percentage, and a group under 10 shows its counts
   with "not rated yet". Extraction and drafts only, never a person; internal; no report or export reads it. Built with DOM nodes. */
export function qCell(tr,text,cls){ const td=document.createElement("td"); td.textContent=text; if(cls) td.className=cls; tr.append(td); return td; }
export function qRow(body,head,cells,note){ const tr=document.createElement("tr"), th=document.createElement("th"); th.scope="row"; th.textContent=head;
  if(note){ const s=document.createElement("span"); s.className="qnr"; s.textContent=note; th.append(s); } tr.append(th); cells.forEach(c=>qCell(tr,c)); body.append(tr); }
export function qEmpty(body,cols,text){ const tr=document.createElement("tr"), td=document.createElement("td"); td.colSpan=cols; td.className="empty"; td.textContent=text; tr.append(td); body.replaceChildren(tr); }
export const qNR=(r,n,w="decided")=>r?"":n?`Not rated yet: ${n} ${w}, rated from ${(D.quality||{}).min||10}`:`Not ${w} yet`;
export function qGroups(id,L){ const body=$(id); body.replaceChildren(); if(!L.length){ qEmpty(body,5,"Nothing proposed in this period."); return; }
  L.forEach(r=>qRow(body,r.label,[r.approved.text,r.edited.text,r.rejected.text,String(r.pending)],qNR(r.rated,r.decided))); }
export function renderQuality(){ const q=D.quality||{}; if(q.error){ $("#qPeriod").textContent=`Quality couldn't be counted (${q.error}).`; return; }
  const p=q.period||{}; $("#qPeriod").textContent=p.from?`The last ${p.weeks} weeks: ${fd(p.from)} to ${fd(p.to)}, by the day each proposal was made.`:"";
  $("#qMoved").textContent=q.moved||""; qGroups("#qSrc",q.by_source||[]); qGroups("#qType",q.by_type||[]);
  const why=$("#qWhy"); why.replaceChildren(); (q.reasons||[]).forEach(r=>qRow(why,r.reason,[r.text])); if(!(q.reasons||[]).length) qEmpty(why,2,"No rejections in this period.");
  const dup=q.duplicates||{}; $("#qDup").textContent=dup.of?`The tracker recorded ${dup.text} rejections in this period as a duplicate of an existing item.`:"";
  const fl=$("#qFields"); fl.replaceChildren(); const lab=q.source_labels||{};
  (q.fields||[]).forEach(r=>qRow(fl,r.field,[r.text,Object.entries(r.by_source||{}).map(([k,n])=>`${lab[k]||k} ${n}`).join(" · ")])); if(!(q.fields||[]).length) qEmpty(fl,3,"No edits with a known field in this period.");
  const u=q.unknown||{}; $("#qUnknown").textContent=u.n?`${u.n} of ${u.of} edited proposals were edited before creaite kept what was first proposed: field unknown.`:"";
  const dr=$("#qDrafts"); dr.replaceChildren(); (q.drafts||[]).forEach(r=>qRow(dr,r.label,r.offered?[String(r.offered),r.used.text,r.edited.text,r.rejected.text]:["0","—","—","—"],qNR(r.rated,r.offered,"offered"))); }
export function actTab(q){ $("#v-activity").classList.toggle("q",q); $("#actQuality").hidden=!q; $("#actTabQ").setAttribute("aria-selected",String(q)); $("#actTabCh").setAttribute("aria-selected",String(!q));
  $("#actTabQ").tabIndex=q?0:-1; $("#actTabCh").tabIndex=q?-1:0; if(q){ renderQuality(); rjLoadRecent(); } }   /* BL-315: What you rejected, fresh each time */
 
/* ===== end BL-233 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootActivity0205(){
/* BL-315: Activity › Quality › What you rejected: the chip changes the reason, Approve instead, Undo (review.js does each) */
mountRejectsList($("#qRejects"),{onReason:(r,el)=>rjReasonFor([{key:r.key,file:r.file,ref:r.ref,t:r.text||"",reason:r.reason||"",dup:r.duplicate_of||null,guess:null}],el),
  onApprove:r=>rjApproveInstead([r]),onUndo:r=>rjUnreject([r]),name:pName,when:at=>`${fd(String(at).slice(0,10))}${String(at).length>15?" "+String(at).slice(11,16):""}`});
$("#actTabQ").addEventListener("click",()=>actTab(true));
$("#actTabCh").addEventListener("click",()=>actTab(false));
$(".acttabs").addEventListener("keydown",e=>{ if(e.key!=="ArrowRight"&&e.key!=="ArrowLeft") return; e.preventDefault(); const q=!$("#v-activity").classList.contains("q"); actTab(q); (q?$("#actTabQ"):$("#actTabCh")).focus(); });
}
