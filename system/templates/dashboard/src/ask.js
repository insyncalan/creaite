// @ts-check
/* ask.js (BL-231 step 2b), moved from script/ by dev/tools/convert_area.py: 0080-search-bl-07.js, 0085-ad-hoc-documents-and-permission-requests.js, 0086-bl-140-sprint-admin.js, 0087-bl-141-sprint-admin-what-ask-creaite-cha.js, 0088-bl-141-sprint-admin-the-one-card.js, 0089-bl-258-sprint-ask-flow.js, 0090-bl-194-sprint-ask-creaite-access-the-car.js, 0092-ask-creaite.js, 0093-bl-262-sprint-ask-flow.js, 0094-after-bl-262.js, 0095-bl-211-sprint-ui-audit.js, 0096-chat-and-sweep-markdown-in-the-chat-bl-1.js, 0097-bl-196-sprint-chat-text.js, 0098-bl-120-sprint-polish.js, 0100-chat-and-sweep-a-time-under-each-bubble.js, 0101-after-chat-and-sweep-times.js, 0102-bl-257-sprint-ask-flow.js, 0103-bl-262-sprint-ask-flow.js, 0104-after-bl-262.js, 0105-bl-139-sprint-final.js, 0106-after-bl-139.js, 0107-bl-259-sprint-ask-flow.js, 0108-after-bl-259.js, 0109-images-in-ask-creaite-bl-100.js, 0110-bl-201-sprint-chat-text.js, 0111-after-bl-201.js, 0112-bl-199-sprint-chat-text.js, 0113-after-bl-199.js, 0114-bl-145-fix-chat-box.js, 0117-after-bl-145.js, 0118-bl-148-sprint-ux.js, 0119-after-bl-148.js, 0120-command-palette.js, 0207-bl-205-sprint-insight.js, 0208-bl-206-sprint-insight.js.
   Unchanged apart from `export`, `shared.` for the shared state (core/state.js) and the load-time steps, now in
   boot…() functions that src/main.js calls in today's order. */
import { resumeDeleteNote } from "./components/notes/DeleteNote.jsx";
import { openDialog } from "./components/Dialog.jsx";
import { isNotePath, openNoteAt } from "./notes.js";
import { A, DEC, FILES, fpName, open, P, pName, R, REV } from "./core/data.js";
import { $, $$, addHTML, esc, html, ic, putHTML, raw, TIP, tipShow } from "./core/dom.js";
import { addEl, DATE_HELP, openPath, parseWhen, weekendNote } from "./core/fields.js";
import { recordsRefresh } from "./core/instant.js";
import { mWords } from "./core/motion.js";
import { go, navBlocked, parseHash, pLink, restoreNav } from "./core/nav.js";
import { anim, applyTheme, copied, D, days, fd, fdText, hk, ico, MOD, MTICK, nowStamp, OPENST, reduced, S, store, themeFade, themeOf, THEMES, TODAY, VAULT_PATH, who } from "./core/page.js";
import { api, needVault, OLDSERVER, oneLine, refreshAll, reloadData, save, SERVED, setLive, snack, viaServer, writeProposal, writeSettings, z2 } from "./core/server.js";
import { shared } from "./core/state.js";
import { ckChipsHtml, openDraftEmail } from "./drafts.js";
import { helpCk } from "./help.js";
import { MSEL, MTG, mtgCanPick, previewInbox, processMeetings, renderMeetings } from "./intake.js";
import { hubFor, hubLink, prepPage } from "./meetings.js";
import { openCapture } from "./components/notes/CaptureDrawer.jsx";
import { openMilestone, openNewMilestone } from "./milestones.js";
import { mdHtml, newItemOf, norm, openNew, openProject, openRecord, pkArr, pkCommit, pkPersist, pkStatuses, pkUndoLast, REC, validate } from "./panel.js";
import { openGen, openPrep, pickImage, prepOf, startCurEdit, vsAskSync } from "./projects.js";
import { railPopOpen } from "./rail.js";
import { decide } from "./review.js";
import { ownerFinal, peopleCk, PERS, renderSettings, resolvePerson, row, VIPD } from "./settings.js";
import { DC, longDay, pkAdd, plur, tl } from "./today.js";
import { allViews, applyView, items, itemsMove, loadTab, rows, saveTab } from "./work.js";
import { openCloseDay } from "./components/closeday/CloseDay.jsx";
import { closeMenu, menuOpenFor, openMenu } from "./components/Menu.jsx";
/* ===== Search (BL-07) ===== */
/* One search box finds anything in the vault. It runs through the live server (GET /api/search), which understands
   project codes, people, types and dates in the text and returns them as chips; the rest are the search terms.
   Results: Items (tracker rows, opened in their panel), Meetings (previewed here, scrolled to the match), Reports and
   Documents (opened with the system viewer). Results appear as you type, after a short pause. */
export const SRCH={skip:[],seq:0,timer:null,res:null,q:""};
export const SEARCHCFG=Object.assign({debounce_ms:150},D.search||{});
export const SKIND={action:"Action",risk:"Risk",issue:"Issue",assumption:"Assumption",dependency:"Dependency",decision:"Decision",milestone:"Milestone",minutes:"Minutes",transcript:"Transcript",report:"Report",document:"Document"};
export const SGROUP={items:"Items",meetings:"Meetings",reports:"Reports",documents:"Documents",notes:"Notes"};   /* BL-301 B: notes, their own group */
export const searchIco=k=>ico(k==="action"?"action":k==="decision"?"decision":k==="milestone"?"milestone":["risk","issue","assumption","dependency"].includes(k)?k[0].toUpperCase()+k.slice(1):"");
export async function searchFetch(q,skip){ const p=new URLSearchParams({q}); if(skip&&skip.length) p.set("skip",skip.join(","));
  const r=await fetch("/api/search?"+p,{headers:{"X-Creaite-Token":D.token||""}}); if(r.status===404) throw new Error(OLDSERVER); if(!r.ok) throw new Error((await r.json().catch(()=>({}))).message||"Search failed"); return await r.json(); }
export const vsProjects=p=>String(p||"").split(" ").filter(Boolean).map(c=>c==="_portfolio"?'<span class="pcode">Portfolio</span>':pLink(c)).join(" ");
/* the snippet is markup from search.py, which escapes the text and adds only <mark>, so it goes in with raw() */
export function vsRow(r,key){ const meta=[r.id&&html`${r.id}`,r.project&&raw(vsProjects(r.project)),r.date_shown&&html`${r.date_shown}`,r.meta&&html`${r.meta}`].filter(x=>x&&String(x)).map((x,i)=>i?html` · ${x}`:x);
  return html`<div class="vsr" data-vs="${key}" tabindex="0" role="link"><div class="vst">${raw(searchIco(r.kind))}<b>${r.title}</b> <span class="tag">${SKIND[r.kind]||r.kind}${r.group==="documents"?" · internal":""}</span></div><div class="vsm">${meta}</div><div class="vss">${raw(r.snippet||"")}</div></div>`; }
export function vsRender(){ const res=SRCH.res, box=$("#vsResults"); if(!res){ box.textContent=""; return; }
  putHTML($("#vsChips"),html`${res.chips.map((c,i)=>html`<span class="vschip" data-kind="${c.kind}">${c.label}<button type="button" data-vschip="${i}" aria-label="Remove ${c.label}">${raw(ic("x"))}</button></span>`)}`);
  const n=Object.values(res.totals).reduce((a,b)=>a+b,0);
  const groups=Object.keys(SGROUP).filter(g=>res.groups[g].length).map(g=>{ const L=res.groups[g], t=res.totals[g];
    return html`<h3 class="vsh">${SGROUP[g]} <span class="sub">· ${t>L.length?`${L.length} of ${t}`:t}</span></h3>${L.map((r,i)=>vsRow(r,g+":"+i))}`; });
  putHTML(box,groups.length?html`${groups}`:html`<div class="empty">Nothing found. Try fewer words, or remove a filter above.</div>`);   /* BL-88: the ask creaite button replaces the Ask row */
  $("#vsNote").textContent=n?`${n} result${n===1?"":"s"}${res.chips.length?" · filters understood from what you typed":""}`:""; }
export function vsClear(){ if(shared.ASKQ.done||!shared.ASKQ.run){ shared.ASKQ={run:null}; vsAnswerDraw(); } SRCH.skip=[]; SRCH.res=null; SRCH.q=""; $("#vsInput").value=""; $("#vsChips").textContent=""; $("#vsNote").textContent=""; $("#vsResults").textContent=""; vsShow(false); vsAskSync(); }
export function vsShow(on){ const f=$("#v-files .files"); if(f) f.hidden=on; $("#vsResults").hidden=!on; }
export let runSearch = async function(){ const q=$("#vsInput").value.trim(); SRCH.q=q; if(!q){ vsClear(); return; } vsShow(true);
  if(!viaServer()){ SRCH.res=null; $("#vsResults").textContent=""; putHTML($("#vsNote"),html`Live server needed: search runs through it. <button class="mini" data-copycmd>Copy the start command</button>`); $("#vsChips").textContent=""; return; }
  const seq=++SRCH.seq; $("#vsNote").textContent="Searching…";
  try{ const res=await searchFetch(q,SRCH.skip); if(seq!==SRCH.seq) return; SRCH.res=res; vsRender(); }catch(e){ if(seq===SRCH.seq){ $("#vsNote").textContent=oneLine(e.message); } } };
export function openResult(key){ const [g,i]=key.split(":"), r=SRCH.res&&SRCH.res.groups[g]&&SRCH.res.groups[g][+i]; if(r) openFound(r); }
/* where a result belongs: an item in its panel, a meeting in the preview, a report or document in the system viewer */
const SHOWARCH="Show archived projects (Settings › People and projects › Projects and register)";
export async function openFound(r){ const o=r.opens;
  if(o.type==="item"&&o.archived&&!S.showArchived){
    if(o.project_archived||!["actions","raid"].includes(o.table)){ snack(`Its project is archived: ${SHOWARCH} brings it back`); return; }   /* BL-09 */
    /* BL-10: archived for its age, in a live project: fetched past the views that hide it, and opened as any item (an edit un-archives it) */
    if(!REC(o.table,o.id)) await recordsRefresh([o.id],{aged:true});
    if(!REC(o.table,o.id)){ snack(`Archived for its age: ${SHOWARCH} shows it`); return; } }
  if(o.type==="item"){ if(o.table==="milestones"){ openMilestone(o.id); return; }   /* BL-186: the Milestones page, its editor open */ const k=o.table; shared.WT=k; go("work"); openRecord(k,o.id); return; }
  if(o.type==="preview"&&isNotePath(o.path)){ openNoteAt(o.path); return; }   /* BL-301 B: a note opens in its Notes tab */
  if(o.type==="preview") return searchPreview(o.path,o.q);
  openPath(o.path); }
export async function searchPreview(path,q){ if(!viaServer()){ snack("Previewing needs the live server"); return; }
  const r=await api("/api/search/preview",{path,q}); if(!r.ok){ snack(r.message===OLDSERVER?OLDSERVER:oneLine(r.message)); return; }
  if(r.empty){ openPath(path); return; }
  $("#spName").textContent=r.name; putHTML($("#spText"),raw(r.html)); $("#spCut").hidden=!r.cut; $("#searchPrev").dataset.path=path; openDialog("searchPrev");
  const m=$("#spText mark"); if(m) m.scrollIntoView({block:"center"}); }
export function openSearch(q){ go("files"); $("#vsInput").value=q; SRCH.skip=[]; runSearch(); $("#vsInput").focus(); }
/* ⌘K: a "Search the vault…" row from three characters, with the top five results under the jump list */
export const CKS={q:"",items:[],timer:null};
export function searchCkItems(){ const q=$("#cmdkIn").value.trim(); if(q.length<3) return []; const out=[{g:"Search",l:`Search the vault for “${q}”…`,h:"Files",fn:()=>openSearch(q)}];
  if(questionLike(q)) out.unshift({g:"Search",l:`ask creaite: “${q}”`,h:"An answer with sources",fn:()=>{ openSearch(q); askClaude(); }});
  if(CKS.q===q) CKS.items.forEach((r,i)=>out.push({g:"Search results",l:r.title,h:[SKIND[r.kind],r.date_shown].filter(Boolean).join(" · "),fn:()=>openFound(r)}));
  else if(viaServer()){ clearTimeout(CKS.timer); CKS.timer=setTimeout(async()=>{ try{ const res=await searchFetch(q); CKS.q=q; CKS.items=Object.keys(SGROUP).flatMap(g=>res.groups[g]).slice(0,5);
      if($("#cmdk").open&&$("#cmdkIn").value.trim()===q){ const was=shared.CKI; shared.CK=ckItems($("#cmdkIn").value); shared.CKI=Math.min(was,shared.CK.length-1); drawCk(); } }catch(e){} },SEARCHCFG.debounce_ms); }
  return out; }

/* ----- Ask (BL-07 part 2): a one-shot answer with a source for every point ----- */
/* The server gathers the best passages and tracker rows, then Claude answers read-only (kind "search" in the run engine:
   one run at a time, Stop, reattach). Citations like [file name › section] or [ABC-A-003] become links. Search answers
   aren't saved as chats; "Continue in ask creaite" makes one of this exchange. */
export const QWORDS=/^\s*(what|why|how|when|who|did|has|is)\b/i, questionLike=q=>/\?\s*$/.test(q)||QWORDS.test(q);
shared.ASKQ={run:null};
export const decodeHtml=s=>{ const t=document.createElement("textarea"); putHTML(t,raw(s)); return t.value; };
export const ITEMID=/^[A-Z][A-Z0-9]{2,6}-(?:[ADM]-)?\d{3}$/;
export const itemTable=id=>A.some(a=>a.id===id)?"actions":R.some(r=>r.id===id)?"raid":DEC.some(d=>d.id===id)?"decisions":P.some(p=>(p.ms||[]).some(m=>m[3]===id))?"milestones":null;
export function citeFind(name){ const n=name.trim().toLowerCase(), stem=x=>x.replace(/\.[^.]+$/,"").toLowerCase();
  const s=(shared.ASKQ.sources||[]).find(x=>x.kind!=="item"&&(x.name.toLowerCase()===n||(x.stem||"").toLowerCase()===n)); if(s) return s;
  const f=FILES.find(x=>x.n.toLowerCase()===n||stem(x.n)===n); return f?{name:f.n,path:f.path,kind:f.f==="notes"?"note":f.f==="reports"?"report":f.f==="documents"||f.f==="agendas"?"document":f.f==="transcripts"?"transcript":"minutes"}:null; }
/* [file › section], [ABC-A-003] and [a; b] in the answer's HTML become links when every part is a source we know */
export function vsCite(h){ return h.replace(/\[([^\[\]<>]{2,200})\]/g,(m,inner)=>{ const parts=decodeHtml(inner).split(/;\s*/).map(p=>{ const [file,...sec]=p.split("›").map(x=>x.trim());
      if(ITEMID.test(file)&&!sec.length&&itemTable(file)) return `<a href="#" class="cite" data-citeitem="${esc(file)}">${esc(file)}</a>`;
      const s=citeFind(file); return s?`<a href="#" class="cite" data-citefile="${esc(s.path)}" data-citekind="${esc(s.kind)}">${esc(p)}</a>`:null; });
    return parts.every(Boolean)?"["+parts.join("; ")+"]":m; }); }
export function vsAnswerDraw(){ const a=shared.ASKQ, box=$("#vsAnswer"); if(!a||!a.q){ box.hidden=true; vsAskSync(); return; } box.hidden=false;
  const running=!!a.run&&!a.done, text=a.said.join("\n\n").trim();
  putHTML(box,html`<div class="vsah"><b>Answer</b> <span class="sub">from your vault · “${a.q}”</span><span class="sp"></span>${running?html`<button class="mini" data-vsstop>Stop</button>`:raw('<button class="mini" data-vsdismiss aria-label="Close the answer">'+ic("x")+'</button>')}</div>
    ${running&&!text?html`<div class="vsab sub"><span class="spin"></span> Reading your files…${a.steps?html` ${a.steps} step${a.steps===1?"":"s"}`:""}</div>`:""}
    ${text?html`<div class="vsab">${raw(vsCite(mdHtml(text)))}</div>`:""}
    ${a.err?html`<div class="vsab" style="color:var(--bad)">${a.err}</div>`:""}${a.stopped?html`<div class="vsab sub">Stopped.</div>`:""}
    ${a.done&&text&&!a.stopped?html`<div class="vsaf"><button class="btn" data-vscontinue>Continue in ask creaite</button><span class="sub">Answers come from your files only; check the sources they cite.</span></div>`:""}`);
  vsAskSync(); }
export async function vsConsume(res,ctl){ const rd=res.body.getReader(), dec=new TextDecoder(); let buf="";
  for(;;){ let c; try{ c=await rd.read(); }catch(e){ if(ctl&&ctl.signal.aborted) shared.ASKQ.stopped=true; break; } if(c.done) break; buf+=dec.decode(c.value,{stream:true}); let i;
    while((i=buf.indexOf("\n\n"))>=0){ const ch=buf.slice(0,i); buf=buf.slice(i+2); if(!ch.startsWith("data: ")) continue; let ev; try{ ev=JSON.parse(ch.slice(6)); }catch(e){ continue; }
      if(ev.type==="sources"){ shared.ASKQ.sources=ev.sources; shared.ASKQ.q=ev.question||shared.ASKQ.q; } else if(ev.type==="text") shared.ASKQ.said.push(ev.text); else if(ev.type==="step") shared.ASKQ.steps=(shared.ASKQ.steps||0)+1;
      else if(ev.type==="stopped") shared.ASKQ.stopped=true; else if(ev.type==="error") shared.ASKQ.err=ev.message; else if(ev.type==="done") shared.ASKQ.session=ev.session;
      vsAnswerDraw(); } }
  shared.ASKQ.done=true; vsAnswerDraw(); const id=shared.ASKQ.run; if(id) api("/api/ask/ack",{run:id}); }
export async function askClaude(){ const q=$("#vsInput").value.trim(); if(q&&viaServer()) rbStart("Answering a question"); try{ if(!q) return;
  if(!viaServer()){ putHTML($("#vsNote"),html`Live server needed: Ask runs through it. <button class="mini" data-copycmd>Copy the start command</button>`); return; }
  if(shared.ASKQ.run&&!shared.ASKQ.done){ snack("An answer is already being written"); return; }
  const id=`q-${Date.now().toString(36)}-${Math.random().toString(36).slice(2,8)}`, ctl=new AbortController(); shared.ASKQ={run:id,ctl,q,said:[],sources:[],steps:0,done:false}; vsShow(true); vsAnswerDraw();
  let res; try{ res=await fetch("/api/search/ask",{method:"POST",signal:ctl.signal,headers:{"Content-Type":"application/json","X-Creaite-Token":D.token||""},body:JSON.stringify({q,skip:SRCH.skip,run:id})}); }
  catch(e){ shared.ASKQ={run:null}; vsAnswerDraw(); if(e.name!=="AbortError") snack("The live server isn't reachable"); return; }
  if(!res.ok||!res.body||(res.headers.get("Content-Type")||"").includes("json")){ const j=await res.json().catch(()=>({})); shared.ASKQ={run:null}; vsAnswerDraw(); snack(res.status===404?OLDSERVER:oneLine(j.message||"Couldn't start the answer")); return; }
  await vsConsume(res,ctl); }
  finally{ rbEnd(shared.ASKQ.stopped?"stopped":shared.ASKQ.err?"failed":"done"); } }
export async function reattachSearch(run){ if(shared.ASKQ.run&&!shared.ASKQ.done) return; const ctl=new AbortController(); shared.ASKQ={run:run.id,ctl,q:"",said:[],sources:[],steps:0,done:false}; go("files"); vsShow(true); vsAnswerDraw();
  let res; try{ res=await fetch("/api/ask/attach",{method:"POST",signal:ctl.signal,headers:{"Content-Type":"application/json","X-Creaite-Token":D.token||""},body:JSON.stringify({run:run.id})}); }catch(e){ return; }
  if(res.ok&&res.body) await vsConsume(res,ctl); }
export async function vsContinue(){ const a=shared.ASKQ; const r=await api("/api/search/continue",{q:a.q,answer:a.said.join("\n\n"),session:a.session}); if(!r.ok){ snack(oneLine(r.message)); return; }
  setChat(r.chat,r.session||null); $("#chLog").textContent=""; openChat(); }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootAsk0080(){
$("#vsInput").addEventListener("input",()=>{ if(!$("#vsInput").value.trim()) SRCH.skip=[]; clearTimeout(SRCH.timer); SRCH.timer=setTimeout(runSearch,SEARCHCFG.debounce_ms); });
$("#vsInput").addEventListener("keydown",e=>{ if(e.key==="Escape"&&($("#vsInput").value||SRCH.res)){ e.preventDefault(); e.stopPropagation(); vsClear(); } });
$("#vsChips").addEventListener("click",e=>{ const b=e.target.closest("[data-vschip]"); if(!b||!SRCH.res) return; const c=SRCH.res.chips[+b.dataset.vschip]; SRCH.skip.push(`${c.kind}:${c.value}`); runSearch(); });
$("#vsResults").addEventListener("click",e=>{ if(e.target.closest("[data-proj]")) return; const r=e.target.closest("[data-vs]"); if(r) openResult(r.dataset.vs); });
$("#vsResults").addEventListener("keydown",e=>{ if(e.key==="Enter"){ const r=e.target.closest("[data-vs]"); if(r){ e.preventDefault(); openResult(r.dataset.vs); } } });
$("#spOpen").onclick=async()=>{ const o=await api("/api/open",{path:$("#searchPrev").dataset.path}); if(!o.ok) snack(oneLine(o.message)); };
$("#vsAnswer").addEventListener("click",e=>{
  if(e.target.closest("[data-vsstop]")&&shared.ASKQ.run){ api("/api/ask/stop",{run:shared.ASKQ.run}).then(r=>{ if(!r.ok&&shared.ASKQ.ctl) shared.ASKQ.ctl.abort(); }); return; }
  if(e.target.closest("[data-vsdismiss]")){ shared.ASKQ={run:null}; vsAnswerDraw(); return; }
  if(e.target.closest("[data-vscontinue]")){ vsContinue(); return; }
  const f=e.target.closest("[data-citefile]"); if(f){ e.preventDefault(); if(["minutes","transcript"].includes(f.dataset.citekind)) searchPreview(f.dataset.citefile,shared.ASKQ.q); else openPath(f.dataset.citefile); return; }
  const it=e.target.closest("[data-citeitem]"); if(it){ e.preventDefault(); const id=it.dataset.citeitem, t=itemTable(id); if(t==="milestones"){ openMilestone(id); } else if(t){ shared.WT=t; go("work"); openRecord(t,id); } } });
$("#vsInput").addEventListener("keydown",e=>{ if(e.key==="Enter"&&questionLike($("#vsInput").value.trim())){ e.preventDefault(); askClaude(); } });
}
/* ===== Ad-hoc documents and permission requests (BL-75) ===== */
/* A headless run can only do what .claude/settings.json allows. When one narrow rule would let a request through, the run
   ends with "PERMISSION: <rule> | <why>" and the server sends a "permission" event (the rule already checked by
   permissions.py). The panel shows exactly that rule; Add the rule applies it through the server (backed up, logged,
   with Undo), and the request carries on in the same session. A rule creaite won't add is explained, not offered. */
/* BL-141: a rule ask creaite can be given is an item on the one approval card; this shows only what isn't added, and why. */
export async function permissionFlow(ev){ permissionInfo(ev); return false; }

/* ===== BL-140 (sprint-admin) ===== */
/* A rule that isn't added says the true reason. Already allowed is information, not a failure: nothing to add, so the refusal
   was about the command itself (what was refused is named), and Try again asks ask creaite to run the script on its own. Only a
   rule that is really out of bounds (it would run anything, or reach the database, the engine or the permissions) mentions
   editing .claude/settings.json yourself in Terminal. */
export function permissionInfoText(ev){ const asked=ev.asked&&ev.asked!==ev.rule?` (asked as ${ev.asked})`:"", shapes=(ev.refused||[]).filter(Boolean);
  if(ev.state==="allowed"||ev.covered) return `Nothing to add: ${ev.rule}${asked} is already allowed by ${ev.covered}. The request was refused for another reason`+(shapes.length?`: ${shapes.join("; ")}.`:".")+" ask creaite can run the script on its own instead.";
  if(ev.state==="out_of_bounds") return `ask creaite asked for ${ev.rule}${asked}, which creaite won't add: ${ev.reason}. If you do want it, edit .claude/settings.json yourself in Terminal.`;
  return `ask creaite asked for ${ev.rule}${asked}, which creaite won't add: ${ev.reason}.`; }
export function permissionInfo(ev){ const d=addEl("msg a info",html`${permissionInfoText(ev)}`);
  if(ev.state!=="allowed"&&!ev.covered) return;
  const a=document.createElement("div"); a.className="acts"; putHTML(a,html`<button class="btn" type="button">Try again</button>`); d.appendChild(a);
  a.querySelector("button").onclick=()=>{ if(shared.BUSY) return; putHTML(a,html`<span class='sub'>Trying again</span>`);
    send(`${ev.rule} is already allowed, so no rule is needed. Run the script on its own (python3 system/scripts/<name>.py …, with no cd, pipe, redirect or heredoc) and carry on with my last request.`); }; }
/* ===== end BL-140 ===== */

/* ===== BL-141 (sprint-admin): What ask creaite changed ===== */
/* Under Activity: every file ask creaite changed (and every change Alan approved on its card), today and the last seven days,
   newest first, each with Undo (filechange.py undo <n>, refused if the file has changed since). Read only otherwise. */
export const ACHG_OP={create:"Created",edit:"Changed",move:"Moved",delete:"Deleted"};
/* BL-194 (sprint-ask-creaite-access): each change's tier, as the card showed it (a word and an icon); older entries have none */
export function achgTier(t){ return t==="high"||t==="sensitive"?raw(chgTierTag(t==="high")):t==="ordinary"?html`<span class="tag">Ordinary</span>`:html`<span class="x">—</span>`; }
export function askChangesHtml(rows){ if(!rows.length) return html`<div class="empty">ask creaite hasn’t changed any files in the last seven days.</div>`;
  return html`<table><thead><tr><th>When</th><th>Tier</th><th>Change</th><th>Why</th><th></th></tr></thead><tbody>${rows.map(c=>html`<tr data-achg="${c.id}" data-tier="${c.tier||""}"><td style="white-space:nowrap">${fd(c.at.slice(0,10))} ${c.at.slice(11,16)}</td><td style="white-space:nowrap">${achgTier(c.tier)}</td><td>${ACHG_OP[c.op]||c.op} <code>${c.path}</code>${c.to?html` → <code>${c.to}</code>`:""}${c.approved?html` <span class="tag">approved on the card</span>`:""}</td><td>${c.why||""}</td><td style="text-align:right">${c.undone?html`<span class="x">Undone</span>`:html`<button class="mini" data-achgundo="${c.id}">Undo</button>`}</td></tr>`)}</tbody></table>`; }
export let ACHGFIRST=true;   /* the What ask creaite changed list (BL-141): rows rise in the first time, a row just undone flashes */
export async function renderAskChanges(){ const loading=shared.LOADING, was=new Set($$("#achgTbl tr[data-achg]").filter(t=>!t.querySelector("[data-achgundo]")).map(t=>t.dataset.achg));
  let box=$("#achg"); if(!box){ box=document.createElement("div"); box.id="achg"; putHTML(box,html`<h2 style="margin:22px 0 4px">What ask creaite changed</h2><p class="sub" style="margin:0 0 10px">Files ask creaite created, changed, moved or deleted, today and the last seven days. Each was backed up first.</p><div class="tbl" id="achgTbl"></div>`); $("#actTbl").after(box);
    box.addEventListener("click",async e=>{ const b=e.target.closest("[data-achgundo]"); if(!b) return; b.disabled=true; const r=await api("/api/changes/undo",{id:+b.dataset.achgundo}); snack(oneLine(r.message||(r.ok?"Undone":"Not undone"))); renderAskChanges(); }); }
  if(!viaServer()) putHTML($("#achgTbl"),html`<div class="empty">This list needs the live server.</div>`);
  else { const r=await api("/api/changes/list",{}); putHTML($("#achgTbl"),r.ok?askChangesHtml(r.changes||[]):html`<div class="empty">${oneLine(r.message||"Couldn't read the list.")}</div>`); }
  if(loading) return; if(reduced()) { ACHGFIRST=false; return; } const rows=$$("#achgTbl tr[data-achg]");
    if(ACHGFIRST&&rows.length){ ACHGFIRST=false; rows.slice(0,8).forEach((t,i)=>anim(t,[{opacity:0,transform:"translateY(4px)"},{opacity:1,transform:"none"}],{duration:320,delay:i*40})); }
    else if(!ACHGFIRST) rows.filter(t=>!t.querySelector("[data-achgundo]")&&!was.has(t.dataset.achg)).slice(0,12).forEach(t=>[...t.children].forEach(td=>{ td.classList.remove("mflash"); void td.offsetWidth; td.classList.add("mflash"); }));
    ACHGFIRST=false; return; }
/* ===== end BL-141 What ask creaite changed ===== */

/* ===== BL-141 (sprint-admin): the one card ===== */
/* Every sensitive change a request needs (a permission or settings file, outside the vault, a delete or move, another person's
   file, more than ten files, anything after reading outside content) is listed on ONE card: each with what it is, why it needs
   approval and the change itself (the lines before → after, or the file for a delete). Approve makes all of them, Decline none;
   the server holds the content shown and the one-time approvals, so the page only says yes or no. The card waits for Alan and
   comes back after a reload. The tags carry words, never colour alone. changesCardHtml is the card's whole markup (one small
   function, so sprint-motion can animate it). */
export function changesCardHtml(c){ const n=c.items.length, nh=c.items.filter(it=>it.tier==="high").length;   /* BL-194: the tiers */
  return `<div class="confirm chgcard" role="group" aria-label="Changes waiting for your approval" data-card="${esc(c.card)}"><b>${n} change${n===1?"":"s"} need${n===1?"s":""} your approval</b>`+
    `<span class="sub">Nothing has been changed yet. Approve makes ${n===1?"it":"all of them"}, Decline makes none. Each is backed up first and can be undone in Activity.</span>`+
    `${nh?`<span class="sub chgtiers">${nh===n?(n===1?"It is":"All are"):`${nh} ${nh===1?"is":"are"}`} High-risk: ${nh===1?"it changes":"they change"} what ask creaite is allowed to do. Read ${nh===1?"it":"them"} closely.</span>`:""}`+
    `<ol class="chglist">${c.items.map((it,i)=>{ const hi=it.tier==="high"; return `<li class="chgtier ${hi?"tier-high":"tier-sens"}" data-tier="${hi?"high":"sensitive"}" style="--i:${Math.min(i,7)}">${chgTierTag(hi)} <b>${esc(it.title)}</b><div class="sub">${esc(it.reason)}.${hi&&it.tier_reason?` High-risk because ${esc(it.tier_reason)}.`:""}${it.why?` Why: ${esc(it.why)}`:""}</div>`+
      `${(it.diff||[]).length?`<pre class="permdiff">${esc(it.diff.join("\n"))}</pre>`:it.summary?`<div class="sub">${esc(it.summary)}</div>`:""}${(it.files||[]).length?`<div class="sub">Deletes: ${it.files.map(f=>`<code>${esc(f)}</code>`).join(", ")}</div>`:""}${hi?chgRollback(it.id):""}</li>`; }).join("")}</ol>`+
    `${(c.refused||[]).length?`<div class="sub">Refused, whatever is approved: ${esc(c.refused.join("; "))}</div>`:""}`+
    `<div class="acts"><button class="btn" data-chg="no">Decline</button><button class="btn primary" data-chg="yes">Approve</button></div></div>`; }
export async function changesFlow(c){
  if(!c.card){ if((c.refused||[]).length) addEl("msg a info",html`${`Not changed, whatever is approved: ${c.refused.join("; ")}.`}`); return false; }
  if(document.querySelector(`#chLog [data-card="${CSS.escape(c.card)}"]`)) return false;
  const d=addEl("confirm-wrap",raw(changesCardHtml(c))); chatScroll();
  const yes=await new Promise(res=>d.querySelectorAll("[data-chg]").forEach(b=>b.onclick=()=>res(b.dataset.chg==="yes")));
  const acts=d.querySelector(".acts"); putHTML(acts,html`<span class='sub'>Working…</span>`);
  const r=await api(yes?"/api/changes/approve":"/api/changes/decline",{card:c.card});
  if(!yes){ putHTML(acts,html`<span class='sub'>Declined: nothing was changed</span>`); addEl("step stopped","Declined: nothing was changed"); return false; }
  putHTML(acts,html`<span class='sub'>${r.ok?html`${raw(MTICK)}Approved`:"Approved, with problems"}</span>`);   /* BL-136: the drawn tick only when it worked */
  chgRollbackNumbers(d,r.results);   /* BL-194: each High-risk item's way back names its own change */
  const lines=(r.results||[]).map(x=>`${x.ok?"✓":"✗"} ${oneLine(x.message)}`); addEl("msg a",html`${lines.length?lines.join("\n"):oneLine(r.message||"")}`);
  if(!(r.results||[]).some(x=>x.ok)) return false;
  snack(oneLine(r.message||"Changes made"),()=>go("activity"));
  const msg="The approved changes are made. Carry on with my last request."; addEl("msg u",html`${msg}`);
  shared.RUN={id:`r-${Date.now().toString(36)}-c`,ctl:new AbortController()}; setRunning(true);
  try{ await askStream("/api/ask",{message:msg,session:shared.ASKSESSION,chat:shared.ASKCHAT,run:shared.RUN.id},undefined,shared.RUN.ctl); } finally{ shared.RUN=null; setRunning(false); } return true; }
export async function pendingCard(){ if(!viaServer()) return; const r=await api("/api/changes/pending",{}); if(!r.ok||!r.card) return;
  if(r.card.chat&&r.card.chat!==shared.ASKCHAT){ setChat(r.card.chat,r.card.chat); await loadChat(r.card.chat,true); }
  openChat(); changesFlow(r.card); }
/* ===== end BL-141 the one card ===== */
/* ===== BL-258 (sprint-ask-flow) ===== a tracker change on one card. The run prepares the change; the server previews its own snapshot
   with propose.py preview and sends the lines, so the card shows exactly what will be written (each field before → after, the old
   value struck through on the danger band, the new one on the success band: the strike as well as the colour). Approve stages it and applies it at once (only this
   change: nothing else pending), Reject stages nothing, Stage for review (offered when another change to the same item waits in
   Review, or another job holds the tracker) leaves it in Review. Every item is listed; the approval is the server's, used once. The
   result names the item IDs, with Undo. BL-141's card for file changes is separate and unchanged. */
export function edLine(ln){ const m=/^(\s*)(.*)$/.exec(ln), ind=m[1].length>0, body=m[2], mid=/^(\S+) · (.*)$/.exec(body);
  const field=t=>{ const f=/^([^:]+): (.*?) → (.*)$/.exec(t); return f?`<span class="edf"><span class="ckf">${esc(f[1])}</span> <span class="eddel">${esc(f[2])}</span> → <span class="edadd">${esc(f[3])}</span></span>`:esc(t); };
  if(mid) return `<li><b>${esc(mid[1])}</b> ${mid[2].split("; ").map(field).join(" ")}</li>`;
  return `<li class="${ind?"edsub":""}">${ind?esc(body):`<b>${esc(body)}</b>`}</li>`; }
export function editCardHtml(c){ const n=c.lines.filter(l=>!/^\s/.test(l)).length;
  return `<div class="confirm edcard" role="group" aria-label="A change waiting for your approval" data-ecard="${esc(c.card)}"><b>${esc(c.title)}</b>`+
    `<span class="sub">Nothing has been written yet. ${c.valid?`Approve writes ${n===1?"this change":`all ${n} changes`} to the tracker at once; Reject discards ${n===1?"it":"them"}.`:"It has problems, so it can't be applied: ask creaite to fix it."}</span>`+
    `<ul class="edlines">${c.lines.map(edLine).join("")}</ul>`+
    `${(c.problems||[]).length?`<div class="sub edprob">${c.problems.map(esc).join("<br>")}</div>`:""}`+
    `${(c.clash||[]).length?`<div class="sub">${esc(c.clash.join(", "))} already ${c.clash.length===1?"has":"have"} a change waiting in Review, so this one can only be staged for review.</div>`:""}`+
    `<div class="acts"></div></div>`; }
export function edActs(acts,kinds){ const word={reject:"Reject",stage:"Stage for review",approve:"Approve"};
  acts.replaceChildren(...kinds.map(k=>{ const b=document.createElement("button"); b.type="button"; b.className="btn"+(k===kinds[kinds.length-1]&&k!=="reject"?" primary":""); b.dataset.ed=k; b.textContent=word[k]; return b; })); }
export async function editFlow(c,o={}){
  if(!c.card){ addEl("msg a info",html`${`The change wasn't put on a card: ${c.refused}.`}`); return; }
  if(document.querySelector(`#chLog [data-ecard="${CSS.escape(c.card)}"]`)) return;
  const d=addEl("confirm-wrap",raw(editCardHtml(c))), acts=d.querySelector(".acts"); chatScroll();
  const later=c.stage===false?"approve":"stage";   /* #124: a note's move is never staged for review: Approve or Reject only */
  edActs(acts,!c.valid?["reject"]:(c.clash||[]).length?["reject",later]:["reject","approve"]);
  for(;;){ const how=await new Promise(res=>acts.querySelectorAll("[data-ed]").forEach(b=>b.onclick=()=>res(b.dataset.ed)));
    acts.textContent="Working…"; const r=await api(`/api/edit/${how}`,{card:c.card});
    if(r.ok){ acts.textContent=how==="approve"?"✓ Approved":how==="stage"?"Staged for review":"Rejected";
      if(how==="reject"){ addEl("step stopped","Rejected: nothing was staged or changed"); return; }
      const m=addEl("msg a",html`${r.message}${how==="approve"&&r.apply_id?html` <button class="mini" data-edundo="${String(r.apply_id)}">Undo</button>`:""}`);
      if(how==="approve") snack(oneLine(r.message)); await reloadData(); return m; }
    if(r.busy||(r.clash||[]).length){ addEl("msg a info",html`${r.message}`); edActs(acts,["reject",later]); continue; }
    if(r.stale){ addEl("msg a info",html`${oneLine(r.message)}`); if(o.onStale) o.onStale(r); edActs(acts,["reject"]); continue; }   /* #124: the card stays; nothing moved */
    acts.textContent="Not applied"; addEl("msg a info",html`${oneLine(r.message||"Not applied")}`); return; } }
export async function pendingEdit(){ if(!viaServer()) return; const r=await api("/api/edit/pending",{}); if(!r.ok||!r.card) return;
  if(r.card.chat&&r.card.chat!==shared.ASKCHAT){ setChat(r.card.chat,r.card.chat); await loadChat(r.card.chat,true); }
  openChat(); if(resumeDeleteNote(r.card)) return;   /* #124: a Delete note card this tab started is watched as the first time */
  editFlow(r.card); }
/* #124 Delete note: a card the server made for the page's own action (a note's move into _Archive), shown in ask creaite and
   answered there like any change card. Resolves to {apply} (the apply's number, for Undo) once Approve has applied it, else
   null (rejected, failed, or only staged for Review when another job was writing). */
export async function serverCardFlow(card,o={}){ openChat(); const m=await editFlow(card,o);
  const b=m&&m.querySelector?m.querySelector("[data-edundo]"):null; return b?{apply:+b.dataset.edundo||null}:null; }
/* ===== BL-314 (v191-ask-routing) ===== a field change asked in the chat runs through the dashboard's own action. The server checked
   each EDIT line against the tracker and sent the preview's before → after lines and, per item, the patch in the dashboard's own field
   names. Go ahead saves them exactly as the Work bulk bar does (itemsMove, batchMove's own save: each owner resolved against the
   register, the sidebar's checks, one proposal through /api/fs, applied at once through /api/apply when auto-apply is on, one Undo);
   Cancel does nothing. Nothing here is new to the server: the routes are the dashboard's, and nothing is written before Go ahead. */
export function fieldCardHtml(c){ const n=(c.items||[]).length;
  return `<div class="confirm edcard" role="group" aria-label="A change waiting for you" data-fcard="${esc(c.card)}"><b>${esc(c.title)}</b>`+
    `<span class="sub">Nothing has been written yet. ${c.valid?`Go ahead saves ${n===1?"it":`all ${n} items`} as an edit in the dashboard does${S.autoApply?", applied at once, with Undo":"; press Apply to write it"}.`:"It has problems, so it can't be saved: ask creaite to fix it, or edit the item yourself."}</span>`+
    `<ul class="edlines">${(c.lines||[]).map(edLine).join("")}</ul>`+
    `${(c.problems||[]).length?`<div class="sub edprob">${c.problems.map(esc).join("<br>")}</div>`:""}`+
    `${(c.notes||[]).length?`<div class="sub">${c.notes.map(esc).join("<br>")}</div>`:""}`+
    `<div class="acts"></div></div>`; }
export async function fieldFlow(c){
  if(document.querySelector(`#chLog [data-fcard="${CSS.escape(c.card)}"]`)) return;
  const d=addEl("confirm-wrap",raw(fieldCardHtml(c))), acts=d.querySelector(".acts"); chatScroll();
  const kinds=c.valid&&(c.items||[]).length?["cancel","go"]:["cancel"], word={cancel:"Cancel",go:"Go ahead"};
  acts.replaceChildren(...kinds.map(k=>{ const b=document.createElement("button"); b.type="button"; b.className="btn"+(k==="go"?" primary":""); b.dataset.fc=k; b.textContent=word[k]; return b; }));
  const how=await new Promise(res=>acts.querySelectorAll("[data-fc]").forEach(b=>b.onclick=()=>res(b.dataset.fc)));
  if(how!=="go"){ acts.textContent="Cancelled"; addEl("step stopped","Cancelled: nothing was changed"); return 0; }
  acts.textContent="Working…";
  const what=c.items.length===1?c.items[0].label:`${c.title}: {n} updated`;
  const r=await itemsMove(c.items.map(it=>({k:it.k,id:it.id,patch:{...it.patch}})),what,{wait:true});   /* the dashboard's own save */
  const done=r.done, left=[...r.left,...r.missing.map(id=>`${id} (not on this page: reload and ask again)`)];
  acts.textContent=done.length?"✓ Saved":"Not saved";
  if(done.length) addEl("msg a",html`${S.autoApply?"Applied":"Saved, waiting for Apply"}: ${done.join(", ")}.${S.autoApply&&D.latest_apply?html` <button class="mini" data-edundo="${String(D.latest_apply)}">Undo</button>`:""}`);
  if(left.length) addEl("msg a info",html`${`Left out: ${left.join("; ")}.`}`);
  else if(!done.length) addEl("msg a info","Not saved: nothing was changed (the message at the bottom of the screen says why).");
  return done.length; }
/* ===== end BL-314 ===== */
/* a card that holds the queue (BL-257) lets it go on once it is answered */
export async function queueResume(){ if(shared.RUN||!QUEUE.items.length) return; const r=await api("/api/ask/queue",{op:"resume"}); if(r.ok&&r.run) attachRun(r.run); else if(r.ok) queueDraw(r); }
/* ===== end BL-258 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootAsk0089(){
$("#chLog").addEventListener("click",async e=>{ const b=e.target.closest("[data-edundo]"); if(!b) return; b.disabled=true;
  const r=await api("/api/undo",{apply_id:+b.dataset.edundo||b.dataset.edundo}); snack(oneLine(r.message||(r.ok?"Undone":"Not undone"))); if(r.ok){ b.textContent="Undone"; await reloadData(); } else b.disabled=false; });
}
/* ===== BL-194 (sprint-ask-creaite-access): the card's tiers and the rollback line =====
   The server gives each change its tier (reach.tier: High-risk for a permission file or a change to a permission rule, else
   Sensitive); the page only shows it, with a word and an icon on the theme's warning or danger band. Under each High-risk change is
   the exact way back, with Copy; once approved, the command names that change's number. Approve and Decline are BL-141's, unchanged. */
export const CHG_UNDO="python3 system/scripts/filechange.py undo";
export function chgTierTag(hi){ return hi?`<span class="tag chghigh">${ic("shield",{bare:true,cls:"tiericon"})}High-risk</span>`:`<span class="tag chgsens">${ic("alert",{bare:true,cls:"tiericon"})}Sensitive</span>`; }
export function chgRollback(id){ return `<div class="chgback" data-chgback="${esc(id)}"><span>Way back: undo it from Activity › What ask creaite changed, or run</span> <code>${esc(CHG_UNDO)}</code> <button class="mini" data-chgcopy title="Copy the command">${ic("copy")}Copy</button></div>`; }
export function chgRollbackNumbers(d,results){ (results||[]).forEach(x=>{ const m=x.ok&&/\(change (\d+)/.exec(x.message||""); const code=m&&d.querySelector(`[data-chgback="${CSS.escape(x.id)}"] code`); if(code) code.textContent=`${CHG_UNDO} ${m[1]}`; }); }
/* ===== end BL-194 the card ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootAsk0090(){
$("#chLog").addEventListener("click",e=>{ const a=e.target.closest("[data-runhref]"); if(!a) return; e.preventDefault(); const href=a.dataset.runhref, st=parseHash(href);   /* BL-326: a closure's link goes to that place in creaite */
  if(!st){ snack("That isn't there any more"); return; } if(navBlocked()) return; try{ history.pushState(null,"",href); }catch(x){} restoreNav(st); });
$("#chLog").addEventListener("click",e=>{ const b=e.target.closest("[data-chgcopy]"); if(!b) return; const code=b.parentElement.querySelector("code");
  (navigator.clipboard?navigator.clipboard.writeText(code.textContent):Promise.reject()).then(()=>{ copied(b); snack("Copied"); },
    ()=>{ const sel=getSelection(), rg=document.createRange(); rg.selectNodeContents(code); sel.removeAllRanges(); sel.addRange(rg); snack("Couldn't copy: the command is selected, press ⌘C"); }); });
}
/* ======================= ask creaite ======================= */
export const sleep=ms=>new Promise(r=>setTimeout(r,ms)); shared.BUSY=false;
export const GREET="Hi Alan. I run your requests through Claude Code in the vault, so your skills and rules apply. Anything that writes asks you first.";
/* ===== BL-262 (sprint-ask-flow) ===== reopening shows the chat as it was: openChat never clears or redraws the log; an empty one
   is filled from the history in one step, or greeted at once (never typed out). SHOWN is the run whose events are on screen and
   the last event drawn (its sequence number), so a reattach asks only for what is newer. */
shared.SHOWN=null;
export function greet(){ addEl("msg a",html`${GREET}`); }
export function openChat(){ if(!$("#chat").classList.contains("on")){ const f=document.activeElement, ok=f&&f!==document.body&&!$("#chat").contains(f);   /* BL-211 */
      CHATFROM=ok?{el:f,key:chatFromKey(f)}:null; }
  $("#chat").classList.add("on"); rbDismiss(); if(CHFOLLOW||CHSAVED==null) chatScroll(); else $("#chLog").scrollTop=CHTOP=CHSAVED;   /* #148: where it was left */
  if(!$("#chLog").children.length&&!ATTACHED&&!shared.REATT){ if(shared.ASKCHAT&&viaServer()) loadChat(shared.ASKCHAT,true); else greet(); } setTimeout(()=>$("#chIn").focus(),40); }
/* ===== end BL-262 ===== */
/* BL-35: the panel's width is dragged from its left edge (← → by keyboard; double-click resets) and remembered in
   this browser — a screen preference, not a setting */
export const CHATW0=420, chatClamp=w=>Math.round(Math.max(360,Math.min(window.innerWidth*0.7,w)));
export function setChatWidth(w,save){ w=chatClamp(w); document.documentElement.style.setProperty("--chatw",w+"px"); $("#chGrip").setAttribute("aria-valuenow",w); if(save) store.set("creaite-chat-width",w); return w; }
export function closeChat(){ const wasOn=$("#chat").classList.contains("on"), inside=$("#chat").contains(document.activeElement);   /* BL-211 */
  if(wasOn) CHSAVED=$("#chLog").scrollTop;   /* #148: a hidden panel forgets its scroll position */
  $("#chat").classList.remove("on"); if($("#chat").contains(document.activeElement)) document.activeElement.blur();
    if(wasOn&&inside&&(!document.activeElement||document.activeElement===document.body)){ const t=chatReturnTarget(); if(t){ if(t.tabIndex<0&&!t.hasAttribute("tabindex")) t.setAttribute("tabindex","-1"); t.focus(); } }
    if(wasOn) CHATFROM=null; }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootAsk0094(){
setChatWidth(store.get("creaite-chat-width",CHATW0),false);
$("#chGrip").addEventListener("pointerdown",e=>{ e.preventDefault(); const g=e.currentTarget; g.setPointerCapture(e.pointerId); document.body.classList.add("chresizing");
  const move=ev=>setChatWidth(window.innerWidth-ev.clientX,false), up=ev=>{ g.releasePointerCapture(e.pointerId); document.body.classList.remove("chresizing"); g.removeEventListener("pointermove",move); g.removeEventListener("pointerup",up); setChatWidth(window.innerWidth-ev.clientX,true); };
  g.addEventListener("pointermove",move); g.addEventListener("pointerup",up); });
$("#chGrip").addEventListener("dblclick",()=>setChatWidth(CHATW0,true));
$("#chGrip").addEventListener("keydown",e=>{ const cur=parseInt(getComputedStyle(document.documentElement).getPropertyValue("--chatw"))||CHATW0;
  if(e.key==="ArrowLeft"||e.key==="ArrowRight"){ e.preventDefault(); setChatWidth(cur+(e.key==="ArrowLeft"?20:-20),true); } if(e.key==="Home"){ e.preventDefault(); setChatWidth(CHATW0,true); } });
window.addEventListener("resize",()=>setChatWidth(store.get("creaite-chat-width",CHATW0),false));
}
/* ===== BL-211 (sprint-ui-audit) ===== ask creaite gives focus back to where you were when it closes (Esc, the close button,
   ⌘J): the button, row or field that had focus when it opened (#askBtn when it was opened from there with the pointer). A row
   drawn again is found by its key; without an opener (or one gone or hidden) focus goes quietly to the page's .content
   (tabindex -1, no outline), else <body>; never the heading (BL-312). Focus is moved only when it was in the chat as it closed, so a click elsewhere on the page keeps its own focus. */
export let CHATFROM=null;
export function chatFromKey(el){ if(!el) return null; if(el.id) return {id:el.id}; for(const a of ["row","n","proj","person","ms","v"]) if(el.dataset&&el.dataset[a]!=null) return {a,v:el.dataset[a],tag:el.tagName}; return null; }
export const chatShown=el=>!!(el&&el.isConnected&&el.getClientRects().length&&!el.closest("[hidden],[inert]")&&getComputedStyle(el).visibility!=="hidden");
export function chatReturnTarget(){ const f=CHATFROM; let el=f&&f.el;
  if(!chatShown(el)&&f&&f.key){ const k=f.key; el=k.id?document.getElementById(k.id):document.querySelector(`${k.tag.toLowerCase()}[data-${k.a.replace(/[A-Z]/g,c=>"-"+c.toLowerCase())}="${CSS.escape(k.v)}"]`); }
  if(chatShown(el)) return el;
  const c=document.querySelector(".content"); return chatShown(c)?c:null; }   /* BL-312: no opener, quietly the page (never the h1); else <body> */
    /* a pointer click may not focus the button */
/* ===== end BL-211 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootAsk0095(){
  $("#askBtn").onclick=e=>{ openChat(); if(!CHATFROM) CHATFROM={el:$("#askBtn"),key:{id:"askBtn"}}; };
  $("#chatClose").onclick=()=>closeChat();
}
/* ===== Chat and sweep: markdown in the chat (BL-109) ===== */
/* chat-only names (chatMdInline, chatMdBlocks): the page's own mdInline/mdBlocks draw Current state, Help and the rest */
/* mdChat(text) returns HTML for one of creaite's replies. Every character is escaped first (esc), then blocks and inline
   forms are recognised on the escaped text, so nothing in a reply can become markup of its own. Links: https, http and
   mailto only. Used for creaite's replies (live and from History) and nowhere else: Alan's bubbles stay plain, and
   Current state keeps mdHtml. Placeholders (\u0001n\u0001) hold finished HTML while the rest is processed. */
export const MDC={ITEM:/\b[A-Z][A-Z0-9]{2,6}-(?:[ADM]-)?\d{3}\b/g, MAX:120000, URL:"((?:[^\\s()]|\\([^\\s()]*\\))+)",
  FENCE:/^ {0,3}(`{3,}|~{3,})[ \t]*([\w+#.-]*)[ \t]*$/, HEAD:/^ {0,3}(#{1,6})[ \t]+(.*?)(?:[ \t]+#+)?[ \t]*$/, HR:/^ {0,3}([-*_])(?:[ \t]*\1){2,}[ \t]*$/,
  QUOTE:/^ {0,3}&gt; ?/, LI:/^( *)([-*+]|\d{1,9}[.)])[ \t]+(.*)$/, SEP:/^\s*\|?\s*:?-+:?\s*(?:\|\s*:?-+:?\s*)*\|?\s*$/};
export const mdSafeUrl=u=>/^(?:https?:\/\/|mailto:)[^\s"<>]+$/i.test(u);
export let MDPATHS=null;
export const mdPaths=()=>{ if(!MDPATHS||MDPATHS.n!==FILES.length) MDPATHS={n:FILES.length,list:FILES.filter(f=>f.path).map(f=>({path:f.path,e:esc(f.path)})).sort((a,b)=>b.e.length-a.e.length)}; return MDPATHS.list; };
export const mdFileLink=(p,inner)=>`<a href="#" class="mdref" data-mdfile="${esc(p)}">${inner}</a>`, mdItemLink=id=>`<a href="#" class="mdref" data-mditem="${id}">${id}</a>`;
export function chatMdInline(s,st,noLinks){
  const keep=h=>{ st.push(h); return "\u0001"+(st.length-1)+"\u0001"; };
  s=s.replace(/(`{1,2})([^`\n]+?)\1(?!`)/g,(m,t,c)=>{ const p=mdPaths().find(f=>f.e===c.trim());
    return keep(p?mdFileLink(p.path,`<code>${c}</code>`):ITEMCODE(c)?`<a href="#" class="mdref" data-mditem="${c.trim()}"><code>${c.trim()}</code></a>`:`<code>${c}</code>`); });
  if(!noLinks){
    s=s.replace(new RegExp("!\\[([^\\]\\n]*)\\]\\("+MDC.URL+"\\)","g"),(m,alt)=>alt);   /* images are not drawn: the alt text shows */
    s=s.replace(new RegExp("\\[([^\\]\\n]+)\\]\\("+MDC.URL+"\\)","g"),(m,text,url)=>mdSafeUrl(url)?keep(`<a href="${url}" target="_blank" rel="noopener">${chatMdInline(text,st,true)}</a>`):m);
    if(/projects\/|inbox\//.test(s)) for(const f of mdPaths()) if(s.includes(f.e)) s=s.split(f.e).join(keep(mdFileLink(f.path,f.e)));
    s=s.replace(MDC.ITEM,id=>itemTable(id)?keep(mdItemLink(id)):id); }
  return s.replace(/\*\*(?=\S)([\s\S]*?\S)\*\*/g,"<strong>$1</strong>").replace(/(^|[^\w])__(?=\S)([\s\S]*?\S)__(?!\w)/g,"$1<strong>$2</strong>")
    .replace(/~~(?=\S)([\s\S]*?\S)~~/g,"<del>$1</del>")
    .replace(/(^|[^\w*\u0001])\*(?=[^\s*])([^*\n]*?[^\s*])\*(?!\*)/g,"$1<em>$2</em>").replace(/(^|[^\w])_(?=[^\s_])([^_\n]*?[^\s_])_(?!\w)/g,"$1<em>$2</em>"); }
export const ITEMCODE=c=>/^[A-Z][A-Z0-9]{2,6}-(?:[ADM]-)?\d{3}$/.test(c.trim())&&!!itemTable(c.trim());
export function chatMdBlocks(lines,st,depth){
  const out=[], n=lines.length, blank=l=>/^\s*$/.test(l), inl=t=>chatMdInline(t,st);
  const cells=l=>l.trim().replace(/^\|/,"").replace(/\|$/,"").split(/(?<!\\)\|/).map(c=>c.trim().replace(/\\\|/g,"|"));
  const tableAt=i=>i+1<n&&lines[i].includes("|")&&MDC.SEP.test(lines[i+1])&&lines[i+1].includes("-")&&cells(lines[i]).length===cells(lines[i+1]).length;
  const startsBlock=i=>MDC.FENCE.test(lines[i])||MDC.HEAD.test(lines[i])||MDC.HR.test(lines[i])||MDC.QUOTE.test(lines[i])||MDC.LI.test(lines[i])||tableAt(i);
  let i=0;
  while(i<n){ const l=lines[i];
    if(blank(l)){ i++; continue; }
    let m=MDC.FENCE.exec(l);
    if(m){ const mark=m[1], code=[]; i++;   /* an unfinished fence (a reply still arriving) is closed at the end for display */
      while(i<n&&!(lines[i].trim().startsWith(mark[0].repeat(mark.length))&&/^[`~]+\s*$/.test(lines[i].trim()))) code.push(lines[i++]);
      i++; out.push(`<div class="mdcode"><button type="button" class="mini mdcopy" data-mdcopy aria-label="Copy the code">Copy</button><pre><code>${code.join("\n")}</code></pre></div>`); continue; }
    m=MDC.HEAD.exec(l);
    if(m){ out.push(`<div class="mdh mdh${Math.min(m[1].length,3)}" role="heading" aria-level="${Math.min(6,m[1].length+(st.hb||0))}">${inl(m[2])}</div>`); i++; continue; }   /* BL-196: st.hb, under the page's own headings */
    if(tableAt(i)){ const head=cells(lines[i]), al=cells(lines[i+1]).map(c=>/^:-+:$/.test(c)?"c":/-:$/.test(c)?"r":""); i+=2; const rows=[];
      while(i<n&&!blank(lines[i])&&lines[i].includes("|")) rows.push(cells(lines[i++]));
      const td=(t,k,tag)=>`<${tag}${al[k]?` class="ta-${al[k]}"`:""}>${inl(t||"")}</${tag}>`;
      out.push(`<div class="mdtable"><table><thead><tr>${head.map((c,k)=>td(c,k,"th")).join("")}</tr></thead><tbody>${rows.map(r=>`<tr>${head.map((_,k)=>td(r[k],k,"td")).join("")}</tr>`).join("")}</tbody></table></div>`); continue; }
    if(MDC.HR.test(l)){ out.push("<hr>"); i++; continue; }
    if(MDC.QUOTE.test(l)){ const q=[]; while(i<n&&MDC.QUOTE.test(lines[i])) q.push(lines[i++].replace(MDC.QUOTE,""));
      out.push(`<blockquote>${depth<6?chatMdBlocks(q,st,depth+1):inl(q.join("\n")).replace(/\n/g,"<br>")}</blockquote>`); continue; }
    if(MDC.LI.test(l)){ const items=[]; let fence=null;
      while(i<n){ const x=lines[i], lm=fence?null:MDC.LI.exec(x);
        if(lm){ items.push({ind:lm[1].length,ord:/\d/.test(lm[2]),num:parseInt(lm[2]),off:lm[1].length+lm[2].length+1,lines:[lm[3]]}); i++; continue; }
        if(blank(x)){ let j=i; while(j<n&&blank(lines[j])) j++; if(items.length&&j<n&&(MDC.LI.test(lines[j])||/^ {2,}\S/.test(lines[j]))){ if(!MDC.LI.test(lines[j])) items[items.length-1].lines.push(""); i=j; continue; } break; }
        if(items.length&&/^ {2,}\S/.test(x)){ const it=items[items.length-1], t=x.slice(Math.min(it.off,x.length-x.trimStart().length));
          const fm=MDC.FENCE.exec(t); if(fence){ if(/^[`~]+\s*$/.test(t.trim())&&t.trim().startsWith(fence)) fence=null; } else if(fm) fence=fm[1][0].repeat(fm[1].length);
          it.lines.push(t); i++; continue; }
        break; }
      let pos=0;
      const body=it=>{ if(it.lines.length===1||depth>=6) return inl(it.lines.join("\n")).replace(/\n/g,"<br>"); const h=chatMdBlocks(it.lines,st,depth+1);
        return (h.match(/<p>/g)||[]).length===1&&/^<p>[\s\S]*<\/p>$/.test(h)?h.slice(3,-4):h; };
      const build=base=>{ const first=items[pos], tag=first.ord?"ol":"ul"; let h=`<${tag}${first.ord&&first.num!==1?` start="${first.num}"`:""}>`, open=false;
        while(pos<items.length){ const it=items[pos]; if(it.ind<base) break;
          if(it.ind>base&&open){ h+=build(it.ind); continue; }
          if(open) h+="</li>"; h+=`<li>${body(it)}`; open=true; pos++; }
        return h+(open?"</li>":"")+`</${tag}>`; };
      out.push(build(items[0].ind)); continue; }
    const para=[l]; i++; while(i<n&&!blank(lines[i])&&!startsBlock(i)) para.push(lines[i++]);
    out.push(`<p>${inl(para.join("\n")).replace(/\n/g,"<br>")}</p>`); }
  return out.join(""); }
export function mdChat(text,o){ text=String(text??"");
  if(text.length>MDC.MAX) return `<div class="mdraw">${esc(text)}</div>`;
  const /** @type {any} */ st=[], lines=esc(text.replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g,"").replace(/\r\n?/g,"\n")).split("\n");
  st.hb=(o&&o.hBase)||0; let h=chatMdBlocks(lines,st,0); for(let k=0;k<6&&/\u0001\d+\u0001/.test(h);k++) h=h.replace(/\u0001(\d+)\u0001/g,(m,x)=>st[x]); return h; }
export async function sayMd(t){ const d=addEl("msg a md",raw(mdChat(t))); chatScroll(); return d; }
export function mdClick(e){
  const c=e.target.closest("[data-mdcopy]"); if(c){ const code=c.parentElement.querySelector("code"); (navigator.clipboard?navigator.clipboard.writeText(code.textContent):Promise.reject()).then(()=>{ copied(c); snack("Copied"); },()=>snack("Couldn't copy")); return; }
  const f=e.target.closest("[data-mdfile]"); if(f){ e.preventDefault(); openPath(f.dataset.mdfile); return; }
  const it=e.target.closest("[data-mditem]"); if(it){ e.preventDefault(); const id=it.dataset.mditem, t=itemTable(id);
    if(t==="milestones"){ openMilestone(id); } else if(t){ shared.WT=t; go("work"); openRecord(t,id); } } }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootAsk0096(){
/* BL-196: the same clicks (a code block's Copy, a file, an item) in every formatted view (.mdv), not only the chat */
document.addEventListener("click",e=>{ if(e.target.closest(".mdv")&&!e.target.closest("#chLog")) mdClick(e); });
$("#chLog").addEventListener("click",e=>mdClick(e));
}
/* ===== BL-196 (sprint-chat-text) ===== formatted text, never raw markdown. One renderer: mdChat (BL-109) draws every view
   that shows markdown from a file or a run; mdView wraps it in .mdv, which shares the chat's styles and clicks. Every character
   is escaped first, so an HTML tag in the text is shown as text and never runs; links are https, http or mailto only and open
   with rel="noopener" in a new tab. hBase puts the text's headings under the page's own (a "#" in release notes is level 3 in
   a card whose title is an h2). A Copy beside such a view copies the original text, never the formatted one.
   Formatted: chat replies (BL-109), the release notes in Settings › creaite version › Review release, a confirmation card's
   text in the chat, and a Markdown file's preview in Intake's inbox. Current state, its sources and search answers keep mdHtml
   (the Current state editor round-trips its HTML through htmlToMd). Plain on purpose: see dev/BUILD.md, Sprint chat-text. */
export const mdView=(text,o)=>`<div class="mdv">${mdChat(text,o)}</div>`;
/* ===== end BL-196 ===== */
/* ===== end Chat and sweep (markdown) ===== */
/* ===== BL-120 (sprint-polish) =====
   The chat follows new content only while it is at (or within a few pixels of) the bottom. Once Alan scrolls up, nothing moves the
   view: new lines, steps, time stamps and the finished reply are added below, and a Jump to latest button appears. Scrolling back
   to the bottom, or the button, resumes following. Alan's own actions (sending, opening a chat, a new chat) go to the bottom.
   The state is kept from the scroll events, because content added below doesn't move the view.
   BL-311: only a move up stops following. A change in height that isn't a new line (the Edit button moving to the latest
   message, a step added to the fold, the working line, the panel resizing) used to leave the view a few pixels short and the
   browser's own scroll event then read that as Alan scrolling away, so the button showed while he was at the bottom. Now any
   change in the log or its size keeps the view at the bottom while following, and a scroll that didn't go up never stops it. */
export let CHFOLLOW=true, CHTOP=0, CHSAVED=null; export const CHNEAR=12;
export function chatPin(){ if(!CHFOLLOW) return; const l=$("#chLog"); l.scrollTop=l.scrollHeight; CHTOP=l.scrollTop; }
export const chatNear=()=>{ const l=$("#chLog"); return l.scrollHeight-l.scrollTop-l.clientHeight<=CHNEAR; };
export function chatScroll(force){ const l=$("#chLog"), b=$("#chJump");
  if(force||CHFOLLOW){ l.scrollTop=l.scrollHeight; CHTOP=l.scrollTop; CHFOLLOW=true; b.hidden=true; return; }
  b.textContent=(shared.RUN||shared.BUSY)?"↓ Latest · still working":"↓ New activity"; b.hidden=false; }
/* ===== end BL-120 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootAsk0098(){
$("#chLog").addEventListener("scroll",()=>{ const l=$("#chLog"), up=l.scrollTop<CHTOP-1; CHTOP=l.scrollTop;
  if(chatNear()){ CHFOLLOW=true; $("#chJump").hidden=true; } else if(up) CHFOLLOW=false; });
new MutationObserver(chatPin).observe($("#chLog"),{childList:true,subtree:true,characterData:true});   /* BL-311 */
if(window.ResizeObserver) new ResizeObserver(chatPin).observe($("#chLog"));
$("#chJump").onclick=()=>{ chatScroll(true); $("#chLog").focus({preventScroll:true}); };
}
/* ===== Chat and sweep: a time under each bubble and day dividers (BL-108) ===== */
export const localDay=off=>{ const d=new Date(); d.setDate(d.getDate()+(off||0)); return `${d.getFullYear()}-${z2(d.getMonth()+1)}-${z2(d.getDate())}`; };
export const nowIso=()=>{ const d=new Date(); return `${localDay(0)}T${z2(d.getHours())}:${z2(d.getMinutes())}:${z2(d.getSeconds())}`; };
export let CHSTARTED=null;   /* {chat, started}: a chat saved before the times existed gets its divider from this */
export function stampMsg(d,at){ if(!at||!d) return; const day=at.slice(0,10), hm=at.slice(11,16); d.dataset.day=day; if(d._time) d._time.remove();
  const t=document.createElement("time"); t.className="mtime "+(d.classList.contains("u")?"u":"a"); t.dateTime=at; t.title=`${fd(day)} ${at.slice(11,19)}`;
  t.textContent=day===localDay(0)?hm:`${fd(day).slice(0,5)} ${hm}`; d.after(t); d._time=t; dayDividers(); chatScroll(); }
export function dayDividers(){ const log=$("#chLog"); log.querySelectorAll(".mday").forEach(x=>x.remove());
  const msgs=[...log.children].filter(e=>e.classList.contains("msg")); if(!msgs.length) return;
  const seq=msgs.filter(e=>e.dataset.day).map(e=>({el:e,day:e.dataset.day})), head=!!CHSTARTED&&CHSTARTED.chat===shared.ASKCHAT&&!msgs[0].dataset.day;
  if(head) seq.unshift({el:log.firstElementChild,day:CHSTARTED.started.slice(0,10)});
  if(!seq.length||(!head&&new Set(seq.map(x=>x.day)).size<2)) return;   /* a divider only where a chat spans days (or the day of an older chat) */
  let prev=null; seq.forEach(x=>{ if(x.day===prev) return; prev=x.day; const m=document.createElement("div"); m.className="mday"; m.setAttribute("role","separator");
    m.textContent=x.day===localDay(0)?"Today":x.day===localDay(-1)?"Yesterday":fd(x.day); log.insertBefore(m,x.el); }); }
/* ===== end Chat and sweep (times) ===== */
export async function say(t,acts){ const d=addEl("msg a",""); for(let i=0;i<t.length;i+=4){ d.textContent=t.slice(0,i+4); await sleep(8); } if(acts){ const a=document.createElement("div"); a.className="acts"; putHTML(a,raw(acts)); d.appendChild(a); } chatScroll(); }
export async function step(l,ms=600){ const d=addEl("step",html`<span class="spin"></span>${l}`); await sleep(ms); putHTML(d,html`✓ ${l}`); }
export function confirmCard(title,body,ok,pre,md){ return new Promise(res=>{ const d=addEl("confirm",html`<b>${title}</b>${md?raw(mdView(body)):body}${pre?html`<pre class="permdiff">${pre}</pre>`:""}<div class="acts"><button class="btn">Cancel</button><button class="btn primary">${ok}</button></div>`); const [c,o]=d.querySelectorAll("button"); c.onclick=()=>{ putHTML(d.querySelector(".acts"),html`<span class='sub'>Cancelled</span>`); res(false); }; o.onclick=()=>{ putHTML(d.querySelector(".acts"),html`<span class='sub'>Confirmed</span>`); res(true); }; }); }
/* BL-330: the remembered chat is kept per vault, under a short fingerprint of the vault's path (never the path itself): two vaults
   served on the same address no longer ask for each other's chats. An older page's one shared key is read until this vault has its own. */
export const ASKVK=(()=>{ let h=5381; for(const c of String(VAULT_PATH)) h=(Math.imul(h,33)^c.charCodeAt(0))>>>0; return h.toString(36); })(), CHATK="creaite-ask-chat:"+ASKVK, SESSK="creaite-ask-session:"+ASKVK;
shared.ASKSESSION=store.get(SESSK,store.get("creaite-ask-session",null)); shared.ASKCHAT=store.get(CHATK,store.get("creaite-ask-chat",null));
/* BL-20: New chat and History. Chats are kept by the live server in system/staging/ask/ */
export function setChat(chat,session){ const was=shared.ASKCHAT; if(chat!==was&&$("#chIn").value&&was!==null) draftSave();
  shared.ASKCHAT=chat; shared.ASKSESSION=session; store.set(CHATK,chat); store.set(SESSK,session);
  if(chat!==was){ if(was===null&&$("#chIn").value) draftSave(); else draftRestore(); } }
export function newChat(){ if(shared.BUSY) return; setChat(null,null); $("#chLog").textContent=""; shared.SHOWN=null; greet(); $("#chIn").focus(); }   /* BL-262: greeted at once */
export async function loadChat(chat,quiet,skipRun){ const rec=await api("/api/chat",{chat}); if(rec.ok&&typeof skipRun==="function") skipRun=skipRun(rec); if(rec.ok&&skipRun) rec.messages=rec.messages.filter(m=>m.run!==skipRun);
  $("#chLog").textContent=""; shared.SHOWN=null;   /* BL-262: the whole history is drawn below in one step; it returns the record */
  if(!rec.ok){ if(rec.gone&&chat===shared.ASKCHAT) setChat(null,null);   /* BL-330: a chat that's gone is forgotten at once, so it isn't asked for again */
    if(quiet){ setChat(null,null); greet(); } else say(rec.message||"Couldn't open that chat."); return rec; }
  setChat(rec.chat,rec.session); CHSTARTED=rec.started?{chat:rec.chat,started:rec.started}:null;
  rec.messages.forEach((m,i)=>{ if(m.who==="you"){ const d=addEl("msg u",html`${m.text}${raw(imgThumbsHtml(m.images))}`,m.at||null); if(m.images&&m.images.length) fillThumbs(d); const r=rec.messages[i+1]; if(m.run&&r&&r.plain&&r.run===m.run) runAsk(d); } else { { let g=null; (m.steps||[]).forEach(l=>g=stepGroup(g,l)); } if(m.plain){ const b=runClosure({line:m.text,href:m.href,link:m.link}); if(m.done_at) stampMsg(b,m.done_at); } else if(m.text){ const b=addEl("msg a md",raw(mdChat(fdText(m.text)))); if(m.done_at) stampMsg(b,m.done_at); } if(m.stopped&&!m.plain) addEl("step stopped","Stopped");   /* BL-326: a run creaite started is kept as its closure line */ if(m.interrupted) addEl("step stopped","Interrupted: the live server stopped"); } }); dayDividers(); return rec; }
/* BL-32: History is a dropdown of the 10 most recent chats; the current chat stays on screen while choosing. BL-316: the Menu
   block's menu (openMenu), opened from #chHist; a slow list shows the skeleton first (motion 15) */
export function histClose(){ if(menuOpenFor($("#chHist"))) closeMenu(); }
export async function showHistory(e){ e&&e.stopPropagation(); if(menuOpenFor($("#chHist"))){ histClose(); return; } if(shared.BUSY) return; if(!viaServer()){ snack("History needs the live server"); return; } await drawHistory(); }
export const histOpen=(items,loading)=>openMenu($("#chHist"),{label:"History",id:"chHistMenu",cls:"chhist",align:"right",loading,items,onPick:c=>{ if(c!==shared.ASKCHAT) loadChat(c); }});
export async function drawHistory(){ let shown=false; const t=setTimeout(()=>{ shown=true; histOpen([],true); },150);
  try{ const res=await api("/api/chats"), L=(res.chats||[]).slice(0,10); if(shown&&!menuOpenFor($("#chHist"))) return;   /* closed while it loaded */
    histOpen([{id:"rc",note:"Recent chats"},...(L.length?L.map(c=>({id:c.chat,name:c.title||"Untitled",mark:c.chat===shared.ASKCHAT?"current":"",cls:c.chat===shared.ASKCHAT?"cur":undefined,
      line:`${fd(c.updated.slice(0,10))} ${c.updated.slice(11,16)} · ${c.count} message${c.count===1?"":"s"}`,data:{chat:c.chat}})):[{id:"none",note:"No earlier chats yet."}])],false); }
  finally{ clearTimeout(t); const M=$("#chHistMenu"); if(M) anim(M,[{opacity:.4,transform:"translateY(4px)"},{opacity:1,transform:"none"}],{duration:320}); } }

export async function handle(q){ const m=/^note:\s*([\s\S]+)/i.exec(q);   /* "note: …" in ask creaite */
  if(m){ if(!viaServer()){ await say("Saving a note needs the live server."); return; }   /* BL-301 C: saved as a note, the drawer's way (never the model) */
    const r=await api("/api/notes/capture/done",{code:"auto",body:m[1].trim(),template:"blank"});
    if(!r.ok){ await say(oneLine(r.message||"The note wasn't saved.")); return; }
    const un=r.code==="_portfolio"; await say(`Saved the note “${r.title}” in ${un?"Unfiled":pName(r.code)}${r.reason?(un?`: ${r.reason}`:` (${r.reason})`):""}. Find updates on the note turns it into tracker changes.`); return; }
  if(!viaServer()){ await say(SERVED?"The live server isn't running, so I can't run this here. Start it again, or copy the request into Claude Code.":"This is the file version of the dashboard. Open the live dashboard (start the live server), or copy the request into Claude Code.",`<button class="mini" id="cpy">Copy command</button>`); const c=$("#cpy"); if(c){ c.id=""; c.onclick=()=>{ navigator.clipboard?.writeText(q); snack("Copied"); }; } return; }
  await askLive(q,null); }
/* BL-33: a running request can be stopped (the Send button becomes Stop; Esc in the input). Read-only requests stop
   at once; a confirmed write stops once the step running now has finished. What's shown so far is kept. */
export let ATTACHED=null; shared.RUN=null;
export const SENDI=ic("arrowup"), STOPI=ic("stop");   /* BL-161 */
export function setRunning(on){ const b=$("#chSend"); putHTML(b,raw(on?STOPI:SENDI)); b.dataset.tip=on?"Stop":"Send"; b.dataset.key=on?"Esc":"Enter"; b.setAttribute("aria-label",on?"Stop":"Send"); b.classList.toggle("stop",on); if(TIP.el===b) tipShow(b,0); }   /* BL-161: one round button, the arrow or the stop square */
export async function stopAsk(){ if(!shared.RUN||shared.RUN.stopping) return; shared.RUN.stopping=true; const res=await api("/api/ask/stop",{run:shared.RUN.id});
  if(res.cleared){ queueDraw({items:[],held:false}); addEl("step stopped",`Stop cleared the queue: ${res.cleared} queued message${res.cleared===1?" was":"s were"} removed`); }   /* BL-257: and says so */
  if(!res.ok&&shared.RUN&&shared.RUN.ctl) shared.RUN.ctl.abort(); }   /* server unreachable or already finished: stop reading here */
export let askLive = async function(q,confirmed){ const id=`r-${Date.now().toString(36)}-${Math.random().toString(36).slice(2,8)}`, ctl=new AbortController(); shared.RUN={id,ctl}; setRunning(true);
  try{ await askStream("/api/ask",{message:q,session:shared.ASKSESSION,chat:shared.ASKCHAT,confirmed,run:id,images:SENDIMG.length?SENDIMG:undefined},confirmed,ctl); } finally{ shared.RUN=null; setRunning(false); } };
/* BL-37: runs belong to the live server. Closing the panel or the page doesn't stop one; on load the page reattaches
   (steps so far replayed, then live), the ask creaite button shows it's working, and a note says when it's done. */
export async function attachRun(run){ if(run&&run.kind==="search") return reattachSearch(run);   /* BL-07: a search answer */ if(shared.RUN||!run) return;   /* BL-326: a run creaite started (a draft, a Prep page, a check or load) is drawn plainly: its ask, steps and closure */ const ctl=new AbortController(); shared.RUN={id:run.id,ctl,attached:true}; setRunning(!run.done);
  ATTACHED=run.id; const after=await attachDraw(run);   /* BL-262 */
  try{ await askStream("/api/ask/attach",{run:run.id,after},run.confirmed,ctl,run.done,!!run.plain); } finally{ shared.RUN=null; setRunning(false); } }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootAsk0101(){
$("#chNew").onclick=newChat;
$("#chHist").onclick=showHistory;
}
/* ===== BL-257 (sprint-ask-flow) ===== messages sent while ask creaite is working are queued. The live server keeps the queue with
   the chat (system/staging/ask/queue/), so a reload or a closed panel keeps it, and starts the next one itself when a run ends; a
   run that ends with a question, a confirmation or a card holds the queue until Alan answers (or presses Run now). Shown under the
   log (never inside it, so the log is never redrawn), each marked Queued with Edit (back into the box, out of the queue) and
   Remove. Stop clears the queue and says so. Built with text, never markup. */
export let QUEUE={items:[],held:false};
export function queueDraw(q){ if(q) QUEUE={items:q.items||[],held:!!q.held}; const box=$("#chQueue"); if(!box) return; box.replaceChildren(); box.hidden=!QUEUE.items.length; if(!QUEUE.items.length) return;
  const head=document.createElement("div"); head.className="chqhead sub"; const n=QUEUE.items.length;
  head.textContent=shared.RUN?`${n} queued: ${n===1?"it runs":"they run in order"} when this request finishes`:QUEUE.held?`${n} queued: waiting for your answer above`:`${n} queued`; box.appendChild(head);
  if(!shared.RUN){ const go=document.createElement("button"); go.type="button"; go.className="mini"; go.dataset.qgo="1"; go.textContent="Run now"; head.appendChild(go); }
  QUEUE.items.forEach(it=>{ const row=document.createElement("div"); row.className="chqitem"; row.dataset.qid=it.id;
    const tag=document.createElement("span"); tag.className="tag"; tag.textContent="Queued"; const t=document.createElement("span"); t.className="chqtext"; t.textContent=it.text+((it.images||[]).length?` (${it.images.length} image${it.images.length===1?"":"s"})`:"");
    const ed=document.createElement("button"); ed.type="button"; ed.className="mini"; ed.dataset.qedit=it.id; ed.textContent="Edit";
    const rm=document.createElement("button"); rm.type="button"; rm.className="mini"; rm.dataset.qrm=it.id; rm.textContent="Remove"; rm.setAttribute("aria-label",`Remove the queued message: ${it.text.slice(0,60)}`);
    row.append(tag,t,ed,rm); box.appendChild(row); }); chatScroll(); }   /* the log is shorter now: keep the latest in view if Alan was there */
export async function queueLoad(){ if(!viaServer()) return; const r=await api("/api/ask/queue",{op:"list"}); if(r.ok) queueDraw(r); }
export async function queueAdd(text,imgs){ const r=await api("/api/ask/queue",{op:"add",message:text,images:imgs}); if(r.idle) return false;
  if(!r.ok){ snack(oneLine(r.message||"Couldn't queue it")); return true; } queueDraw(r); snack("Queued: it runs when this request finishes"); return true; }
/* ===== end BL-257 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootAsk0102(){
$("#chQueue").addEventListener("click",async e=>{ const rm=e.target.closest("[data-qrm]"), ed=e.target.closest("[data-qedit]"), go=e.target.closest("[data-qgo]");
  if(rm){ const r=await api("/api/ask/queue",{op:"remove",id:rm.dataset.qrm}); if(r.ok) queueDraw(r); return; }
  if(ed){ const it=QUEUE.items.find(x=>x.id===ed.dataset.qedit); const r=await api("/api/ask/queue",{op:"remove",id:ed.dataset.qedit}); if(!r.ok||!it) return; queueDraw(r);
    const inp=$("#chIn"); inp.value=it.text; inp.dispatchEvent(new Event("input",{bubbles:true})); inp.focus(); return; }
  if(go){ const r=await api("/api/ask/queue",{op:"resume"}); if(r.ok&&r.run) attachRun(r.run); else if(r.message) snack(oneLine(r.message)); } });
}
/* ===== BL-262 (sprint-ask-flow) ===== what a reattach draws before it follows the run, and the event to follow it from:
   - the run already on screen: nothing (the log is never cleared), from the last event drawn;
   - else the chat's history, in one step, with the run's part as far as the history reaches (the server says how far: `seq`);
   - a run the history doesn't have yet: Alan's message, from the start. */
export async function attachDraw(run){ if(shared.SHOWN&&shared.SHOWN.run===run.id&&$("#chLog").children.length) return shared.SHOWN.seq;
  if(run.chat&&run.chat===shared.ASKCHAT&&$("#chLog").children.length){ const d=addEl("msg u",html`${run.message}${raw(imgThumbsHtml(run.images))}`,run.started||undefined); if((run.images||[]).length) fillThumbs(d); if(run.plain) runAsk(d); shared.SHOWN={run:run.id,seq:0}; return 0; }   /* BL-257: the next queued message, in the chat on screen */
  let after=0, has=false;
  if(run.chat){ setChat(run.chat,shared.ASKSESSION); const rec=await loadChat(run.chat,true,r=>r.seq&&run.id in r.seq?null:run.id);   /* a history that doesn't say how far it reaches: the run is followed from the start */
    has=!!(rec&&rec.ok&&rec.messages.some(m=>m.run===run.id)); if(has) after=rec.seq[run.id]||0; }
  else { $("#chLog").textContent=""; }
  if(!has){ const d=addEl("msg u",html`${run.message}`,run.started||undefined); if(run.plain) runAsk(d); }
  shared.SHOWN={run:run.id,seq:after}; return after; }
/* ===== end BL-262 ===== */
export async function reattach(){ if(!viaServer()) return; queueLoad(); shared.REATT=true; let r; try{ r=await api("/api/ask/running"); } finally{ shared.REATT=false; }   /* #148: openChat leaves the first draw of the log to this */
  if(r.ok&&r.run) attachRun(r.run); else { if(shared.ASKCHAT&&!$("#chLog").children.length&&!ATTACHED) await loadChat(shared.ASKCHAT,true);   /* #148: the saved chat is drawn before the panel is opened, so opening it shows it whole at once */ pendingCard(); pendingEdit(); } }   /* BL-257: the queue comes back too; BL-258: a change card too */   /* BL-141: a card still waiting comes back */
/* ===== BL-139 (sprint-final) =====
   A small badge fixed at the bottom right shows that ask creaite is working and, afterwards, that it has finished. It follows
   every run the run engine makes: a chat message, Process selected, a transcript check or load, a sweep or calendar refresh, a
   report or one-off document (all through askStream), Generate and Make it executive (runGen), the Prep page and a search answer.
   Running: the spark pulses (not under reduced motion), "ask creaite is working…", what is running where known, and the time it has
   taken. Finished: a tick and "ask creaite has finished", with how long it took; it stays until it is dismissed (×), the chat is
   opened or the next run starts, so a run that ended while you were away is still flagged. Stopped and failed say so in words.
   Hidden while the chat panel is open (the chat shows the run); back if the panel is closed during the run. While the tab is
   hidden, a finished run puts a mark in the page title until the tab is seen. role="status", polite; the clock is aria-hidden so
   it is not read out every second. The top-bar dot stays. */
export const RB={state:"",t0:0,label:"",took:"",timer:null}, RBMARK="✓ ask creaite finished · ";
shared.RBMARKED=false; shared.RUNLABEL=""; shared.RBOUT="";
export const rbClock=ms=>{ const s=Math.max(0,Math.round(ms/1000)); return `${Math.floor(s/60)}:${String(s%60).padStart(2,"0")}`; };
export const RBWORDS={running:"ask creaite is working…",done:"ask creaite has finished",stopped:"ask creaite was stopped",failed:"ask creaite stopped with a problem"}, RBICON={done:"✓",stopped:"■",failed:"!"};
export let rbDraw = function(){ const el=$("#runBadge"); if(!el) return; if(!RB.state){ el.hidden=true; return; }
  const s=RB.state; el.hidden=false; el.className=`runbadge ${s}`; el.dataset.state=s;
  $("#rbI").textContent=RBICON[s]||""; $("#rbT").textContent=RBWORDS[s];
  $("#rbL").textContent=s==="running"?RB.label:RB.took?`${s==="done"?"took":"after"} ${RB.took}`:"";
  $("#rbE").hidden=s!=="running"; $("#rbX").hidden=s==="running"; rbTick(); };
export function rbTick(){ if(RB.state==="running") $("#rbE").textContent=rbClock(Date.now()-RB.t0); }
export function rbGuess(q){ q=String(q||""); return /weekly report/i.test(q)?"Drafting the weekly report":/client report/i.test(q)?"Drafting the client report":/steerco|one-pager/i.test(q)?"Drafting the one-pager":
  /refresh calendar/i.test(q)?"Refreshing the calendar":/^sweep/i.test(q)?"Sweeping mail and Teams":/prep/i.test(q)?"Making the prep page":/^process/i.test(q)?"Processing a meeting":""; }
export function rbUnmark(){ if(shared.RBMARKED){ shared.RBMARKED=false; if(document.title.startsWith(RBMARK)) document.title=document.title.slice(RBMARK.length); } }
export function rbStart(label){ if(RB.state==="running"){ if(label) RB.label=label; rbDraw(); return; }       /* a confirmed follow-up of the same run keeps its clock */
  rbUnmark(); Object.assign(RB,{state:"running",t0:Date.now(),label:label||shared.RUNLABEL||"",took:""}); shared.RUNLABEL=""; clearInterval(RB.timer); RB.timer=setInterval(rbTick,1000); rbDraw(); }
export function rbStop(){ clearInterval(RB.timer); RB.timer=null; }
export function rbEnd(state){ if(RB.state!=="running") return; rbStop(); RB.took=rbClock(Date.now()-RB.t0);
  if($("#chat").classList.contains("on")){ RB.state=""; rbDraw(); return; }                                   /* the chat showed it happen */
  RB.state=state||"done"; rbDraw();
  if(document.hidden){ if(!shared.RBMARKED){ shared.RBMARKED=true; document.title=RBMARK+document.title; }
    if(VIPD().notify===true&&"Notification" in window&&Notification.permission==="granted"){ try{ const n=new Notification(RBWORDS[RB.state],{body:RB.took?`${RB.state==="done"?"took":"after"} ${RB.took}`:"",tag:"creaite-run"}); n.onclick=()=>{ window.focus(); openChat(); n.close(); }; }catch(e){} } } }
export function rbCancel(){ if(RB.state==="running"){ rbStop(); RB.state=""; rbDraw(); } }
export function rbDismiss(){ if(RB.state&&RB.state!=="running"){ RB.state=""; rbDraw(); } rbUnmark(); }
export function askWorking(on){ $("#askBtn").classList.toggle("working",on); }
export function askFinished(o){ rbEnd(o||"done"); }
 
/* the other runs: Generate and Make it executive, the Prep page and a search answer wrap their own functions */
/* ===== end BL-139 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootAsk0105(){
document.addEventListener("visibilitychange",()=>{ if(!document.hidden) rbUnmark(); });
$("#rbMain").onclick=()=>openChat();
$("#rbX").onclick=()=>{ rbDismiss(); };
}
/* While ask creaite works: a rotating bit of office humour instead of "Working…" (like Claude's own "Clauding…"),
   and the technical steps folded into one "✓ 5 steps" line that opens to show them. */
export const QUIPS=["Percolating coffee","Getting my steps in","Waiting for the conference call to start","You're on mute","Circling back",
  "Touching base","Taking this offline","Aligning stakeholders","Socialising the deck","Putting it in the parking lot",
  "Boiling a small ocean","Moving the needle","Picking the low-hanging fruit","Running it up the flagpole","Booking a meeting about the meeting",
  "Waiting for the projector to connect","Hunting for a free meeting room","Reply-all-ing, carefully","Turning amber back to green",
  "Herding stakeholders","Adding an action to the action log","Queueing for the kettle","Looking for the HDMI dongle","Can everyone see my screen?",
  "Rescheduling the reschedule","Doing a deep dive","Taking it to the steering committee","Double-clicking on that","Going round the room",
  "Adding it to the backlog","Chasing sign-off","Checking the RACI","Re-baselining the plan","Syncing on the sync","Grabbing five minutes",
  "Reading the pre-read","Finding a whiteboard pen that works","Raising a ticket with IT","Wordsmithing the slide","Ideating",
  "Leveraging the synergies","Updating the RAG status","Waiting for the lift","Joining from my phone","Finding the meeting link",
  "Sorry, you go","Just finishing another call","Pinging the stakeholders","Bringing the deck to life","Locking in the agenda",
  /* BL-259 (sprint-ask-flow): 100 more, in the same voice (office life, harmless, no names, no brands) */
  "Finding the action log","Unmuting","Sharing the wrong screen","Sharing the right screen","Waiting for the room to empty",
  "Collecting the printouts","Refilling the stapler","Looking for a working pen","Fixing the wobbly chair","Warming up the projector",
  "Asking who has the clicker","Moving the stand-up to Tuesday","Waiting for quorum","Taking the minutes","Agreeing the next steps",
  "Parking that for now","Coming back to that","Noting the dependency","Updating the tracker","Colour-coding the spreadsheet",
  "Merging two spreadsheets","Finding the latest version","Renaming it final_final","Checking the shared drive","Clearing the inbox",
  "Flagging it for later","Drafting a polite nudge","Softening the wording","Adding a gentle reminder","Writing the out-of-office",
  "Booking the next check-in","Finding a slot that suits everyone","Declining a clashing invite","Accepting tentatively",
  "Waiting for the calendar to load","Moving my lunch","Reheating my coffee","Finding the good mugs","Wiping the whiteboard",
  "Taking a photo of the whiteboard","Drawing a box and an arrow","Adding another arrow","Labelling the swimlanes",
  "Sorting the sticky notes","Grouping the sticky notes","Voting with dots","Timeboxing it","Setting a five-minute timer",
  "Running slightly over","Going round once more","Asking any other business","Thanking everyone for their time","Sending the follow-up",
  "Attaching the slides","Forgetting the attachment","Tidying the agenda","Numbering the actions","Assigning an owner",
  "Agreeing a due date","Nudging the due date","Checking the dependencies","Raising a risk","Scoring the risk","Mitigating the risk",
  "Closing the issue","Logging a decision","Recording who agreed","Printing double-sided","Unjamming the printer",
  "Finding the meeting room key","Adjusting the air conditioning","Opening a window","Charging my laptop","Finding a free socket",
  "Restarting for updates","Reconnecting to the Wi-Fi","Dialling in","Spelling my name for the call","Waiting in the lobby",
  "Admitting everyone from the lobby","Turning my camera on","Blurring my background","Checking I'm not on mute","Saying hello to the room",
  "Asking for a quick show of hands","Reading the room","Summarising the discussion","Playing it back","Checking for questions",
  "Writing it in plain English","Cutting it to one page","Making the font smaller","Aligning the boxes","Fixing the bullet points",
  "Choosing a better chart","Labelling the axes","Checking the numbers add up","Double-checking the dates","Converting the time zones",
  "Proofreading"];
/* ===== BL-259 (sprint-ask-flow) ===== each quip stays for a random 5 to 10 seconds (chosen again for each one), drawn from a shuffled
   deck so none comes back until the rest have been shown; a new working line keeps the quip already showing until its time is up
   (so never one shown for under 5 seconds). The working line is unchanged otherwise: italic, aria-hidden, "Working" for readers. */
export const QUIPMIN=5000, QUIPMAX=10000; shared.QDECK=[]; shared.QNOW={text:"",i:-1,until:0};
export function quipDeal(){ if(!shared.QDECK.length){ shared.QDECK=QUIPS.map((_,i)=>i); for(let i=shared.QDECK.length-1;i>0;i--){ const j=Math.floor(Math.random()*(i+1)); [shared.QDECK[i],shared.QDECK[j]]=[shared.QDECK[j],shared.QDECK[i]]; }
    if(shared.QDECK.length>1&&shared.QDECK[shared.QDECK.length-1]===shared.QNOW.i) [shared.QDECK[0],shared.QDECK[shared.QDECK.length-1]]=[shared.QDECK[shared.QDECK.length-1],shared.QDECK[0]]; }   /* never the same twice running */
  return shared.QDECK.pop(); }
export function quipNow(){ const now=Date.now(); if(!shared.QNOW.text||now>=shared.QNOW.until){ const i=quipDeal(); shared.QNOW={text:QUIPS[i]+"…",i,until:now+QUIPMIN+Math.random()*(QUIPMAX-QUIPMIN)}; } return shared.QNOW.text; }
export function quip(el){ const q=el&&el.querySelector(".quip"); if(!q) return; const t=quipNow(); if(q.textContent!==t) q.textContent=t; }
export function working(){ const d=addEl("step working",html`<span class="spin mdots"><i></i><i></i><i></i></span><span class="quip" aria-hidden="true"></span><span class="vh">Working</span>`); quip(d); return d; }
   /* looks twice a second; a quip changes only when its time is up */
/* ===== end BL-259 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootAsk0107(){
setInterval(()=>$$("#chLog .step.working").forEach(quip),500);
}
export function stepGroup(g,label){ if(!g||!g.isConnected) g=addEl("step steps",html`<details><summary>✓ <span class="n"></span></summary><ul></ul></details>`);
  const ul=g.querySelector("ul"), li=document.createElement("li"); li.textContent=label; ul.appendChild(li);
  const n=ul.children.length; g.querySelector(".n").textContent=`${n} step${n===1?"":"s"}`; return g; }
/* ===== BL-326 (v1.9.5) ===== a run creaite started itself (a Prep page, Generate, an AI draft, a meeting's check or load, the
   catch-up sweep) shows three things: its ask (one plain line, drawn as Alan's message), its activity (the working line and
   "✓ n steps", in plain words) and its closure (one line with the outcome and a link, or what went wrong and what to do). Never
   its prompt, JSON, HTML or a tool's raw output: askStream draws only these events for such a run (the cards stay cards). */
export const PLAINEV=["step","closure","changes","editcard","fieldcard","done"];
/* #36: its ask is drawn as Alan's message but isn't one he typed, so it never offers Edit (BL-148), which would send it as a chat */
export function runAsk(d){ if(d) d.classList.add("runask"); return d; }
export function runClosure(c){ const href=/^#[\w=%.|:&-]*$/.test(String(c.href||""))?String(c.href):"";
  return addEl("msg a runend"+(c.ok===false?" info":""),html`${String(c.line||"")}${href?html` · <a href="${href}" class="hlink" data-runhref="${href}">${c.link||"Open"}</a>`:""}`); }
/* ===== end BL-326 ===== */
export async function askStream(url,body,confirmed,ctl,ended,plain){ let res, outcome="done"; const live=!ended; askWorking(live); if(live) rbStart(shared.RUNLABEL||rbGuess(body&&body.message));     /* BL-139; BL-262: a finished run (ended) shows no working line */
  try{ res=await fetch(url,{method:"POST",signal:ctl.signal,headers:{"Content-Type":"application/json","X-Creaite-Token":D.token,"X-Creaite-Seq":"1"},body:JSON.stringify(body)}); }   /* BL-262: numbered events */
  catch(e){ askWorking(false); if(e.name==="AbortError"){ rbEnd("stopped"); addEl("step stopped","Stopped"); retryOffer("stopped",body); return; } rbEnd("failed"); setLive(false); await say("The live server stopped."); retryOffer("failed",body); return; }   /* BL-148: Try again */
  if(res.status===409){ askWorking(false); rbCancel(); const j=await res.json().catch(()=>({})); await say("ask creaite is still working on the last request. Stop it, or wait until it finishes."); if(j.run&&!shared.RUN) attachRun(j.run); return; }
  if(!res.ok||!res.body){ askWorking(false); rbEnd("failed"); await say("ask creaite couldn't start: check the live server window."); retryOffer("failed",body); return; }
  const work=()=>live?working():document.createElement("div");   /* BL-262 */ let next=null;
  const rd=res.body.getReader(), dec=new TextDecoder(), t0=performance.now(); let buf="", conf=null, perm=null, chg=null, ecard=null, fcard=null, prep=null, runId=body.run, replies=[], grp=null, spin=work();
  for(;;){ let chunk; try{ chunk=await rd.read(); }catch(e){ spin.remove(); askWorking(false); rbEnd(shared.RUN&&shared.RUN.stopping?"stopped":"failed"); if(shared.RUN&&shared.RUN.stopping) addEl("step stopped","Stopped"); retryOffer(shared.RUN&&shared.RUN.stopping?"stopped":"failed",body); return; } const {value,done}=chunk; if(done) break; buf+=dec.decode(value,{stream:true}); let i; const replayed=url==="/api/ask/attach"&&performance.now()-t0<150;   /* #148: the backlog an attach opens with (the server sends it as soon as the stream opens), is drawn as it was: no words fading in */
    while((i=buf.indexOf("\n\n"))>=0){ const chunk=buf.slice(0,i); buf=buf.slice(i+2); if(!chunk.startsWith("data: ")) continue; let ev; try{ ev=JSON.parse(chunk.slice(6)); }catch(e){ continue; }
      if(ev.seq&&runId) shared.SHOWN={run:runId,seq:ev.seq};   /* BL-262: the last event drawn */
      if(plain&&!PLAINEV.includes(ev.type)){ if(ev.type==="stopped") outcome="stopped"; else if(ev.type==="error") outcome="failed"; continue; }   /* BL-326: a run creaite started shows its steps and its closure, never its prompt, reply or raw output */
      if(ev.type==="closure"){ spin.remove(); grp=null; outcome=ev.ok?"done":ev.stopped?"stopped":"failed"; replies.push(runClosure(ev)); spin=work(); }
      else if(ev.type==="step"){ spin.remove(); grp=stepGroup(grp,ev.label); spin=work(); }
      else if(ev.type==="text"){ spin.remove(); grp=null; { const d=await sayMd(fdText(ev.text)); replies.push(live&&!replayed?mWords(d):d); }   /* BL-136: a live reply's words fade in; #148: not a finished run replayed (ended: live is false) nor the backlog an attach opens with (replayed) */ claimsNote(ev.checked); spin=work(); }
      else if(ev.type==="cant"){ spin.remove(); grp=null; cantCard(ev); spin=work(); }   /* BL-314: the plain "I can't", with where it can be done */
      else if(ev.type==="confirm") conf=ev;
      else if(ev.type==="permission") perm=ev;      /* BL-140: a rule that isn't added, and why */
      else if(ev.type==="changes") chg=ev;          /* BL-141: the one card */
      else if(ev.type==="editcard") ecard=ev;       /* BL-258: a tracker change on one card */
      else if(ev.type==="fieldcard") fcard=ev;      /* BL-314: a field change, through the dashboard's own action */
      else if(ev.type==="applied"){ spin.remove(); grp=null; addEl(ev.ok?"msg a":"msg a info",html`${ev.message}${ev.ok&&ev.apply_id?html` <button class="mini" data-edundo="${String(ev.apply_id)}">Undo</button>`:""}`); if(ev.ok) snack(oneLine(ev.message)); spin=work(); }   /* BL-306: a confirmed change, applied once */
      else if(ev.type==="prep") prep=ev;            /* BL-307: the live server's Prep page, offered on its own card */
      else if(ev.type==="denied"){ spin.remove(); refusedSteps(ev); spin=work(); }   /* BL-201: plain words, the command in a fold-out */
      else if(ev.type==="error"){ spin.remove(); outcome="failed"; await say(ev.message); }
      else if(ev.type==="stopped"){ spin.remove(); outcome="stopped"; conf=null; spin=addEl("step stopped",ev.timed_out?"Stopped: nobody was watching for too long":ev.after_step?"Stopped after the current step finished":"Stopped"); }
      else if(ev.type==="done"){ runId=ev.run||runId; next=ev.next||null;   /* BL-257: the queued message the server started */ setChat(ev.chat||shared.ASKCHAT,ev.session||shared.ASKSESSION); replies.forEach(b=>stampMsg(b,ev.done_at||nowIso())); replies=[]; } } }
  replies.forEach(b=>stampMsg(b,nowIso()));   /* a reply that ended without a done event (stopped, cut off) is finished now */
  if(!spin.classList.contains("stopped")) spin.remove();
  askWorking(false); setRunning(false); if(runId) api("/api/ask/ack",{run:runId}); ATTACHED=null; askFinished(outcome); retryOffer(outcome,body);   /* BL-148 */
  if(next){ setTimeout(()=>attachRun(next),0); return; } queueLoad();   /* BL-257: follow the next queued message once this run's caller has let go */
  if(perm) permissionFlow(perm);
  if(chg&&await changesFlow(chg)) return;
  if(ecard) await editFlow(ecard);   /* BL-258 */
  if(fcard) await fieldFlow(fcard);   /* BL-314 */
  if(conf&&await confirmCard(conf.title,conf.body,"Go ahead",null,true)){ addEl("msg u",html`${"Go ahead: "+conf.title}`); shared.RUN.id=`${shared.RUN.id}-w`; shared.RUN.ctl=new AbortController(); setRunning(true);
    await askStream("/api/ask",{message:`Go ahead: ${conf.title}`,session:shared.ASKSESSION,chat:shared.ASKCHAT,confirmed:conf.title,run:shared.RUN.id},conf.title,shared.RUN.ctl); return; }
  if(prep&&await confirmCard("Prep page",html`Research ${prep.title}${prep.project?html` (${prep.project})`:""} and save a page in the project's Agendas folder. The live server writes it, marked Internal.`,"Go ahead")){ addEl("msg u",html`${"Go ahead: Prep page"}`); await prepPage(prep.key); }   /* BL-307: the Prep page route (BL-98), never the chat */
  if(chg||ecard||fcard||conf||prep) setTimeout(queueResume,0);   /* BL-257: answered, so a held queue goes on */
  if(confirmed) await reloadData(); }
/* ===== Images in ask creaite (BL-100) ===== */
/* Paste (⌘V / Ctrl+V), drop or attach up to 4 PNG or JPEG images. Each is shrunk here (longest side about 1600px, under the
   2 MB limit), uploaded to system/staging/uploads/ask/ and shown as a thumbnail above the box with × to remove. The message
   carries their IDs; the server tells Claude Code to read them. They are for discussion only, and go with their chat. */
export const IMG_MAX=4, IMG_SIDE=1600, IMG_BYTES=1900*1024; shared.PIMG=[]; shared.IMGURL={};
export function imgFlash(t){ snack(t); }
export function shrinkImage(file){ return new Promise((res,rej)=>{ const u=URL.createObjectURL(file), im=new Image();
  im.onload=()=>{ URL.revokeObjectURL(u); let w=im.naturalWidth, h=im.naturalHeight, k=Math.min(1,IMG_SIDE/Math.max(w,h)); w=Math.max(1,Math.round(w*k)); h=Math.max(1,Math.round(h*k));
    for(let side=0;side<6;side++){ const c=document.createElement("canvas"); c.width=w; c.height=h; const x=c.getContext("2d"); x.fillStyle="#fff"; x.fillRect(0,0,w,h); x.drawImage(im,0,0,w,h);
      const png=file.type==="image/png"&&side===0, q=[.9,.8,.7,.6,.5,.4][side], url=png?c.toDataURL("image/png"):c.toDataURL("image/jpeg",q), b64=url.split(",")[1];
      if(b64.length*3/4<=IMG_BYTES||(w<200&&h<200)) return res({data:b64,url,type:url.slice(5,url.indexOf(";"))});
      if(png){ side=-1; file={type:"image/jpeg"}; continue; } w=Math.max(1,Math.round(w*.85)); h=Math.max(1,Math.round(h*.85)); }
    rej(new Error("too big")); };
  im.onerror=()=>{ URL.revokeObjectURL(u); rej(new Error("not an image")); }; im.src=u; }); }
export function drawThumbs(){ const T=$("#chThumbs"); T.hidden=!shared.PIMG.length; putHTML(T,html`${shared.PIMG.map((p,i)=>html`<div class="chthumb${p.id?"":" up"}" data-i="${i}" style="background-image:url('${p.url}')" title="Click to enlarge"><button class="x" type="button" data-rm="${i}" aria-label="Remove image">${raw(ic("x"))}</button></div>`)}`); }
export async function addImages(files){ if(!viaServer()){ imgFlash("Images need the live server"); return; }
  for(const f of files){ if(shared.PIMG.length>=IMG_MAX){ imgFlash(`Up to ${IMG_MAX} images on a message`); break; }
    if(f.type!=="image/png"&&f.type!=="image/jpeg"){ imgFlash("Only PNG or JPEG images"); continue; }
    let s; try{ s=await shrinkImage(f); }catch(e){ imgFlash("Couldn't read that image"); continue; }
    const p={url:s.url,id:null,name:f.name||"image"}; shared.PIMG.push(p); drawThumbs();   /* BL-148: the name is kept with the draft */
    const r=await api("/api/ask/image",{data:s.data}); if(!r.ok){ shared.PIMG.splice(shared.PIMG.indexOf(p),1); drawThumbs(); imgFlash(oneLine(r.message)); continue; }
    p.id=r.id; shared.IMGURL[r.id]=s.url; drawThumbs(); } }
export function imgView(url){ let B=$("#imgBig"); if(!B){ B=document.createElement("div"); B.id="imgBig"; putHTML(B,html`<img alt='Attached image'>`); B.onclick=()=>B.classList.remove("on"); document.body.appendChild(B); }
  B.firstChild.src=url; B.classList.add("on"); }
export function imgThumbsHtml(ids){ return ids&&ids.length?`<div class="mthumbs">${ids.map(i=>`<div class="chthumb" data-img="${esc(i)}" style="${shared.IMGURL[i]?`background-image:url('${shared.IMGURL[i]}')`:""}" title="Click to enlarge"></div>`).join("")}</div>`:""; }
export async function fillThumbs(root){ for(const t of root.querySelectorAll("[data-img]")){ const i=t.dataset.img; if(!shared.IMGURL[i]){ const r=await api("/api/ask/image/get",{id:i}); if(r.ok) shared.IMGURL[i]=`data:${r.type};base64,${r.data}`; else t.title="This image is gone"; }
  if(shared.IMGURL[i]) t.style.backgroundImage=`url('${shared.IMGURL[i]}')`; } }
 
export const imgFiles=dt=>dt?[...dt.files].filter(f=>f.type.startsWith("image/")):[];
export let SENDIMG=[];
export let send = function(text){ const sent=(async text=>{ text=(text??$("#chIn").value).trim(); const imgs=shared.PIMG.filter(p=>p.id).map(p=>p.id); if(shared.RUN&&(text||imgs.length)&&viaServer()&&await sendQueued(text,imgs)) return; if(shared.BUSY||(!text&&!imgs.length)) return; if(shared.PIMG.some(p=>!p.id)){ imgFlash("Wait for the image to finish uploading"); return; }
  if(!text) text=imgs.length>1?"Please look at these images.":"Please look at this image."; shared.BUSY=true; $("#chIn").value=""; acClose(); SENDIMG=imgs; shared.PIMG=[]; drawThumbs();
  const d=addEl("msg u",html`${text}${raw(imgThumbsHtml(imgs))}`); fillThumbs(d); try{ await handle(text); } finally{ shared.BUSY=false; SENDIMG=[]; } })(text);
  if(text==null&&!$("#chIn").value){ clearTimeout(DRAFTT); draftClear(); CHREC.i=-1; } return sent; };   /* the draft is cleared once a typed message has gone */
/* BL-257: sent while a run works: queued with the server (true), or false when the run has just ended (sent as usual) */
export async function sendQueued(text,imgs){ if(shared.PIMG.some(p=>!p.id)){ imgFlash("Wait for the image to finish uploading"); return true; }
  const t=text||(imgs.length>1?"Please look at these images.":"Please look at this image.");
  if(!(await queueAdd(t,imgs))){ for(let i=0;shared.BUSY&&i<20;i++) await sleep(100);   /* it ended meanwhile: sent as usual once it has let go */
    if(shared.BUSY){ snack("Answer the card above first, then send this"); return true; } return false; }   /* a card waiting for Alan: his text stays in the box */
  $("#chIn").value=""; acClose(); shared.PIMG=[]; drawThumbs(); $("#chIn").dispatchEvent(new Event("input",{bubbles:true})); return true; }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootAsk0109(){
document.addEventListener("click",e=>{ const t=e.target.closest("[data-img]"); if(t&&shared.IMGURL[t.dataset.img]){ imgView(shared.IMGURL[t.dataset.img]); } });
$("#chThumbs").addEventListener("click",async e=>{ const rm=e.target.closest("[data-rm]"), th=e.target.closest(".chthumb"); if(rm){ const p=shared.PIMG[+rm.dataset.rm]; shared.PIMG.splice(+rm.dataset.rm,1); drawThumbs(); if(p&&p.id) api("/api/ask/image/remove",{id:p.id}); return; } if(th&&shared.PIMG[+th.dataset.i]) imgView(shared.PIMG[+th.dataset.i].url); });
$("#chAttach").onclick=()=>$("#chFile").click();
$("#chFile").onchange=e=>{ addImages([...e.target.files]); e.target.value=""; };
$("#chIn").addEventListener("paste",e=>{ const f=imgFiles(e.clipboardData); if(f.length){ e.preventDefault(); addImages(f); } });
$("#chat").addEventListener("dragover",e=>{ if([...(e.dataTransfer?.types||[])].includes("Files")){ e.preventDefault(); $("#chat").classList.add("drop"); } });
$("#chat").addEventListener("dragleave",e=>{ if(!e.relatedTarget||!$("#chat").contains(e.relatedTarget)) $("#chat").classList.remove("drop"); });
$("#chat").addEventListener("drop",e=>{ $("#chat").classList.remove("drop"); const f=imgFiles(e.dataTransfer); if(f.length){ e.preventDefault(); addImages(f); } });
}
/* ===== BL-201 (sprint-chat-text) ===== a refused command in plain words. The server (refusal_view in live_server.py) gives one
   sentence per refusal: what was tried, why not, and what ask creaite does instead; the raw command is under "Show the command"
   for troubleshooting, never in the line. ⚠ only for a refusal the run didn't recover from (no later step succeeded). An older
   server's event (no `plain`) still shows its tools and shapes. Display only: the guard and what it refuses are unchanged. */
export function refusedSteps(ev){ const pl=ev.plain||[], seen=new Set();
  if(!pl.length){ addEl("step refused stop",html`⚠ Refused: ${(ev.tools||[]).join("; ")}${(ev.shapes||[]).length?` (${ev.shapes.join("; ")})`:""}`); return; }
  pl.forEach(r=>{ if(seen.has(r.line+"|"+r.raw)) return; seen.add(r.line+"|"+r.raw);
    addEl("step refused"+(r.recovered?"":" stop"),html`<div class="rfline">${r.recovered?"":html`<span class="rfwarn" aria-label="Stopped here">⚠</span>`}<span>${r.line}</span></div><details class="rfraw"><summary>Show the command</summary><code>${r.raw||""}</code></details>`); }); }
/* ===== end BL-201 ===== */
/* ===== BL-314 (v1.9.1) ===== the server checks every work-item ID in a reply against the tracker before it is shown (claims.py):
   the text arrives already flagged or corrected, and `checked` lists what changed, said here in one quiet line. A "cant" event
   is the plain "I can't" for something the panel can never do (a Microsoft 365 action, the live server): one sentence and a
   button to where it can be done, in place of a Go ahead that would only be refused. Display only: the guard is unchanged. */
export function claimsNote(found){ if(!found||!found.length) return; const n=k=>found.filter(f=>f.kind===k).length, t=n("title"), o=n("owner"), m=n("missing");
  const parts=[t?`${t} title${t===1?"":"s"} didn't match`:"",o?`${o} owner${o===1?"":"s"} corrected`:"",m?`${m} ID${m===1?"":"s"} not in the tracker`:""].filter(Boolean);
  addEl("step checked",html`<span>Checked against the tracker: ${parts.join(", ")}.</span>`); }
export function cantCard(ev){ const g=ev.go;
  addEl("msg a cant",html`<p>${ev.line}</p>${g&&g.label?html`<button class="mini" data-cango="${JSON.stringify(g)}">${g.label}</button>`:""}`); }
export function cantGo(g){ if(!g) return; if(g.email){ if(PERS().some(p=>p.name===g.email)){ openDraftEmail(g.email,g.mode||"update"); return; } go("people"); return; } if(g.page) go(g.page,g.arg); }
document.addEventListener("click",e=>{ const b=e.target.closest("[data-cango]"); if(!b) return; e.preventDefault(); let g=null; try{ g=JSON.parse(b.dataset.cango); }catch(x){ return; } cantGo(g); });
/* ===== end BL-314 ===== */
/* BL-24: suggestions as Alan types — skills' trigger phrases and CLAUDE.md commands (gathered at build), project
   codes, open item IDs and review numbers. ↑ ↓ move, Enter or Tab picks, Esc closes; "/" lists everything. */
/* ===== BL-199 (sprint-chat-text) ===== no suggestion is chosen until the arrow keys choose one (AC.i is -1: nothing
   highlighted, no aria-activedescendant). Enter with none chosen sends what was typed; ↓ chooses the first, ↑ the last;
   Enter with one chosen fills the box with it (never sends). Tab with none chosen completes the first (it never sends).
   A click still picks; Esc closes. The same for every list acItems builds. */
shared.AC={items:[],i:-1};
export function acItems(v){ const t=v.replace(/^\s+/,""), C=D.commands||[]; let m;
  if((m=t.match(/^(client report|weekly report|review|sweep mail for|close project)\s+(\S*)$/i))) return P.filter(p=>p.code.startsWith(m[2].toUpperCase())).map(p=>({t:`${m[1]} ${p.code}`,s:p.name}));
  if((m=t.match(/^mark\s+(\S*)$/i))) return [...A.filter(open).map(x=>[x,"done"]),...R.filter(r=>r.st==="Open").map(x=>[x,"closed"])].filter(([x])=>x.id.startsWith(m[1].toUpperCase())).slice(0,30).map(([x,w])=>({t:`mark ${x.id} ${w}`,s:x.t}));
  if((m=t.match(/^(approve|reject)\s+(\d*)$/i))) return REV.filter(r=>!r.done&&String(r.n).startsWith(m[2])).map(r=>({t:`${m[1].toLowerCase()} ${r.n}`,s:r.rec.t}));
  if(t==="/") return C.map(c=>({t:c.t,s:c.s,g:c.s}));
  if(t.length<2) return [];
  const words=t.toLowerCase().split(/\s+/).filter(Boolean);
  return C.filter(c=>{ const cw=c.t.toLowerCase().split(/[\s…]+/); return c.t.toLowerCase()!==t.toLowerCase()&&words.every(w=>cw.some(x=>x.startsWith(w))); }).slice(0,8).map(c=>({t:c.t,s:c.s})); }
export function acDraw(){ const M=$("#acMenu"); if(!shared.AC.items.length){ M.hidden=true; $("#chIn").removeAttribute("aria-activedescendant"); return; } let g=null;
  putHTML(M,html`<div class="achint" aria-hidden="true">${shared.AC.i<0?"Enter sends what you typed · ↓ ↑ choose a suggestion":"Enter puts this suggestion in the box · Esc closes"}</div>${shared.AC.items.map((it,i)=>{ const h=it.g&&it.g!==g?html`<div class="cgrp">${it.g}</div>`:""; g=it.g; return html`${h}<div class="aco ${i===shared.AC.i?"act":""}" id="aco${i}" role="option" aria-selected="${String(i===shared.AC.i)}" data-aci="${i}"><span>${it.t??""}</span>${it.g?"":html`<small>${it.s||""}</small>`}</div>`; })}`);
  M.hidden=false; if(shared.AC.i<0){ $("#chIn").removeAttribute("aria-activedescendant"); M.scrollTop=0; return; }   /* BL-199 */
  $("#chIn").setAttribute("aria-activedescendant","aco"+shared.AC.i); $("#aco"+shared.AC.i)?.scrollIntoView({block:"nearest"}); }
export function acUpdate(){ shared.AC.items=acItems($("#chIn").value); shared.AC.i=-1; acDraw(); }   /* BL-199: nothing chosen */
export function acClose(){ shared.AC.items=[]; acDraw(); }
export function acPick(i){ const it=shared.AC.items[i]; if(!it) return; const inp=$("#chIn"); let v=it.t, sel=null;
  if(v.endsWith("…")) v=v.slice(0,-1).replace(/\s*$/," ");
  else { const m=v.match(/<[^>]+>|\bABC(?:-[A-Z])?(?:-\d{3})?\b|\b\d{2}-\d{2}-\d{4}\b/); if(m) sel=[m.index,m.index+m[0].length]; }
  inp.value=v; acClose(); inp.focus(); if(sel) inp.setSelectionRange(...sel); else inp.setSelectionRange(v.length,v.length); }
export function acKey(e){ if(!shared.AC.items.length) return false;
  if(e.key==="ArrowDown"||e.key==="ArrowUp"){ e.preventDefault(); const n=shared.AC.items.length, dn=e.key==="ArrowDown";   /* BL-199 */
    shared.AC.i=shared.AC.i<0?(dn?0:n-1):(shared.AC.i+(dn?1:-1)+n)%n; acDraw(); return true; }
  if(e.key==="Enter"){ if(shared.AC.i<0){ acClose(); return false; } e.preventDefault(); acPick(shared.AC.i); return true; }   /* BL-199: none chosen, Enter sends the typed text */
  if(e.key==="Tab"&&!e.shiftKey){ e.preventDefault(); acPick(shared.AC.i<0?0:shared.AC.i); return true; }
  if(e.key==="Escape"){ e.preventDefault(); e.stopPropagation(); acClose(); return true; } return false; }
/* ===== end BL-199 ===== */
 
    /* BL-257: during a run, Enter queues it */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootAsk0113(){
$("#chIn").addEventListener("input",acUpdate);
$("#chIn").addEventListener("blur",()=>setTimeout(acClose,120));
$("#acMenu").addEventListener("mousedown",e=>{ const o=e.target.closest("[data-aci]"); if(o){ e.preventDefault(); acPick(+o.dataset.aci); } });
$("#chSend").onclick=()=>shared.RUN?stopAsk():send();
$("#chIn").addEventListener("keydown",e=>{ if(acKey(e)) return; if(e.key==="Escape"&&shared.RUN){ e.preventDefault(); e.stopPropagation(); stopAsk(); return; } if(e.key==="Enter"&&!e.shiftKey){ e.preventDefault(); send(); } });
}
/* ===== BL-145 (fix-chat-box) ===== the message box grows with what is typed. chFit() sets #chIn's height from its content,
   between one row and about half the panel's height (never more than half the window), and scrolls inside beyond that with the
   cursor kept in view. It runs on input (typing, Shift+Enter, paste, delete), whenever code sets the value (send, a suggestion
   picked, a new chat), when the panel opens or changes size (its width changes the wrapping), and on a theme or font change. */

/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootAsk0117(){
$("#chQuick").onclick=e=>{ const b=e.target.closest("[data-q]"); if(b) send(b.dataset.q); };
}
/* ===== BL-148 (sprint-ux) ===== the conveniences a chat should have.
   (1) Copy on every reply: a small button in the reply's corner, shown on hover and on focus, copies the reply as plain text.
   (2) ↑ in an empty box recalls the last message sent in this chat; ↑ again goes further back, ↓ forward (and back to empty).
   (3) Edit on Alan's last message puts it back in the box; sending it continues the chat (no branching). Never on the ask of a
       run creaite started (BL-326, #36): Alan didn't type it.
   (4) Try again after a stopped or failed run sends the same message again.
   (5) The unsent draft (its text and the names of attached images) is kept per chat in this browser and comes back after a
       reload; it is cleared on send. It never reaches the server. Enter sends and Shift+Enter makes a new line, as before (BL-145). */
export const CPYI=ic("copy",{size:13,w:2});   /* BL-158 */
export const msgText=d=>[...d.childNodes].filter(n=>n.nodeType===3).map(n=>n.data).join("");            /* Alan's message as typed (not its images or buttons) */
export function msgPlain(d){ d.classList.add("copying"); const t=d.innerText.replace(/\n{3,}/g,"\n\n").trim(); d.classList.remove("copying"); return t; }
export let CHDECOR=false;
export function chDecorate(){ CHDECOR=false; const log=$("#chLog"); if(!log) return;
  log.querySelectorAll(".msg.a").forEach(d=>{ if(!d.querySelector(":scope>.msgcopy")&&d.textContent.trim()) addHTML(d,"beforeend",html`<button type="button" class="msgcopy" data-msgcopy title="Copy the reply" aria-label="Copy the reply">${raw(CPYI)}</button>`); });
  log.querySelectorAll(".msg.u.runask>.msgedit").forEach(b=>b.remove());   /* #36: a run creaite started has no Edit */
  const us=[...log.querySelectorAll(".msg.u:not(.runask)")], last=us[us.length-1];
  us.forEach(d=>{ const b=d.querySelector(":scope>.msgedit"); if(d!==last&&b) b.remove(); });
  if(last&&!last.querySelector(":scope>.msgedit")&&msgText(last).trim()) addHTML(last,"beforeend",html`<button type="button" class="msgedit" data-msgedit title="Edit and send again" aria-label="Edit and send again">Edit</button>`); }
export function chPut(t){ const el=$("#chIn"); el.value=t; el.focus(); el.setSelectionRange(t.length,t.length); draftSave(); }
/* (2) recall: the messages Alan sent in the chat on screen, newest last */
export const CHREC={i:-1,shown:null};
/* (4) a stopped or failed run offers to send the same message again */
export function retryOffer(outcome,body){ const q=body&&body.message; if(outcome==="done"||!q) return;
  $$("#chLog .retry").forEach(x=>x.remove());
  const d=addEl("step retry",html`<button type="button" class="mini" data-retry>Try again</button> <span class="sub">sends “${q.length>60?q.slice(0,57)+"…":q}” again</span>`); d._q=q; }
/* (5) the draft, per chat, in this browser only */
export const DRAFTK="creaite-ask-drafts", draftKey=()=>shared.ASKCHAT||"new";
export function draftSave(){ const all=store.get(DRAFTK,{}), t=$("#chIn").value, imgs=shared.PIMG.map(p=>p.name).filter(Boolean);
  if(t.trim()||imgs.length) all[draftKey()]={text:t,images:imgs,at:Date.now()}; else delete all[draftKey()];
  const keep=Object.entries(all).sort((a,b)=>b[1].at-a[1].at).slice(0,10); store.set(DRAFTK,Object.fromEntries(keep)); }
export function draftRestore(){ const el=$("#chIn"), d=store.get(DRAFTK,{})[draftKey()]; if(!d||el.value) return;
  if(d.text) el.value=d.text; if(d.images&&d.images.length) $("#chDraftNote").textContent=`Before the reload you had attached ${d.images.join(", ")}: attach ${d.images.length===1?"it":"them"} again to send.`; }
export function draftClear(){ const all=store.get(DRAFTK,{}); delete all[draftKey()]; delete all.new; store.set(DRAFTK,all); $("#chDraftNote").textContent=""; }
export let DRAFTT=null; 
/* ===== end BL-148 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootAsk0118(){
new MutationObserver(()=>{ if(!CHDECOR){ CHDECOR=true; requestAnimationFrame(chDecorate); } }).observe($("#chLog"),{childList:true,subtree:true,characterData:true});
$("#chLog").addEventListener("click",e=>{
  const c=e.target.closest("[data-msgcopy]"); if(c){ const t=msgPlain(c.closest(".msg")); (navigator.clipboard?navigator.clipboard.writeText(t):Promise.reject()).then(()=>{ copied(c); snack("Copied"); },()=>snack("Couldn't copy")); return; }
  const ed=e.target.closest("[data-msgedit]"); if(ed){ if(shared.RUN||shared.BUSY){ snack("Wait for ask creaite to finish, or stop it"); return; } chPut(msgText(ed.closest(".msg"))); return; }
  const r=e.target.closest("[data-retry]"); if(r){ if(shared.RUN||shared.BUSY) return; const q=r.closest(".retry")._q; r.closest(".retry").remove(); send(q); } });
$("#chIn").addEventListener("keydown",e=>{ if(e.defaultPrevented||e.altKey||e.metaKey||e.ctrlKey||e.shiftKey||(e.key!=="ArrowUp"&&e.key!=="ArrowDown")) return;
  if(shared.AC.items.length&&!$("#acMenu").hidden) return;                                              /* the suggestions use the arrows */
  const el=e.target, sent=[...$("#chLog").querySelectorAll(".msg.u")].map(msgText).filter(t=>t.trim());
  const recalling=CHREC.i>=0&&el.value===CHREC.shown; if(!sent.length||(el.value!==""&&!recalling)) return;
  if(e.key==="ArrowUp"){ if(recalling&&el.selectionStart>0&&el.value.lastIndexOf("\n",el.selectionStart-1)>=0) return;   /* inside a long recalled message, ↑ moves the cursor */
    CHREC.i=recalling?Math.min(CHREC.i+1,sent.length-1):0; }
  else { if(!recalling) return; if(el.value.indexOf("\n",el.selectionEnd)>=0) return; CHREC.i--; }
  e.preventDefault();
  if(CHREC.i<0){ CHREC.shown=null; el.value=""; return; }
  const t=sent[sent.length-1-CHREC.i]; CHREC.shown=t; el.value=t; el.setSelectionRange(t.length,t.length); });
$("#chIn").addEventListener("input",()=>{ CHREC.i=-1; CHREC.shown=null; });
$("#chIn").addEventListener("input",()=>{ clearTimeout(DRAFTT); DRAFTT=setTimeout(draftSave,250); });
addEventListener("pagehide",()=>{ if($("#chIn").value) draftSave(); });
addHTML($("#chThumbs"),"afterend",html`<div class="chdraft sub" id="chDraftNote" aria-live="polite"></div>`);
draftRestore();
}

/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootAsk0119(){
document.addEventListener("click",e=>{ const g=e.target.closest("[data-gowork]"); if(g){ shared.WT="actions"; applyView(g.dataset.gowork); go("work"); } });
}
/* ======================= command palette ======================= */
shared.CK=[]; shared.CKI=0;
export function ckItems(q){ let out=(q=>{ q=q.toLowerCase(); const out=[]; const add=(g,l,h,fn,kw)=>{ if(!q||(l+" "+h+" "+(kw||"")).toLowerCase().includes(q)) out.push({g,l,h,fn}); };   /* kw: words that find it without showing (a project's code) */
  const nNew=(D.inbox||[]).filter(f=>f.state==="new").length;
  [["today","Today",""],["inbox","Intake",nNew?`${nNew} new`:""],["projects","Projects",""],["work","Work",""],["people","People",""],["mine","Your commitments",""],["review","Review",""],["files","Files",""],["activity","Activity",""],["settings","Settings",""],["help","Help",""]].forEach(([v,l,h])=>add("Go to",l,h,()=>go(v)));
  /* Work's views, built-in and saved, straight from anywhere */
  [["actions","Actions"],["raid","RAID"],["decisions","Decisions"]].forEach(([t,tl])=>allViews(t).forEach(v=>add("Views",`${tl}: ${v.label}`,v.builtin?"":"saved view",()=>{ if(navBlocked()) return; saveTab(); loadTab(t); applyView(v.id); go("work"); })));
  P.forEach(p=>add("Projects",p.name,p.health,()=>go("cockpit",p.code),p.code)); peopleCk(add);
  add("Actions","New action","",()=>{ shared.WT="actions"; go("work"); openNew("actions"); }); add("Actions","New RAID item","",()=>{ shared.WT="raid"; go("work"); openNew("raid"); }); add("Actions","New decision","",()=>{ shared.WT="decisions"; go("work"); openNew("decisions"); });
  add("Actions","Add files to Intake","",()=>{ go("inbox"); $("#inboxFile").click(); });
  if(nNew) add("Actions","Process new Intake files",`${nNew} new`,()=>{ go("inbox"); $("#inboxNew").click(); });
  if(shared.VIEW==="cockpit"&&shared.COCK){ const c=shared.COCK;   /* the project page you're on */
    add("Actions",`Generate current state: ${c}`,"",()=>openGen(c)); add("Actions",`Edit current state: ${c}`,"",()=>startCurEdit(c));
    add("Actions",`Add milestone: ${c}`,"",()=>openNewMilestone(c)); add("Actions",`Add image: ${c}`,"",()=>{ go("cockpit",c); startCurEdit(c); pickImage(); }); add("Actions",`Edit health: ${c}`,"",()=>openProject(c,"health")); }
  add("Actions","ask creaite","/",openChat); add("Actions","Switch light or dark","",()=>$("#themeBtn").click());
  THEMES.forEach(t=>add("Actions",`Theme: ${t.id}`,themeOf(S.palette)===t?"current":"",()=>setPalette(t.id)));
  add("Actions","Customise the rail","right-click the rail",()=>railPopOpen());   /* BL-191: the rail's control has no button of its own now */
  if(q.length>1){ P.forEach(p=>(p.ms||[]).filter(m=>m[3]).forEach(m=>add("Milestones",`${m[3]} · ${m[0]}`,m[1]?fd(m[1]):"",()=>openMilestone(m[3]))));
    (D.inbox||[]).forEach(f=>add("Intake",f.name,"preview",()=>{ go("inbox"); previewInbox(f.path); }));
    FILES.filter(f=>f.p!=="inbox").forEach(f=>add("Files",f.n,[fpName(f.p),f.f,f.sub].filter(Boolean).join(" › "),()=>openPath(f.path),f.p)); }   /* BL-101: the name shown, the code still finds it */
  if(q.length>1){ A.forEach(a=>add("Items",`${a.id} · ${a.t}`,who(a.o),()=>{ shared.WT="actions"; go("work"); openRecord("actions",a.id); })); R.forEach(r=>add("Items",`${r.id} · ${r.t}`,r.pr,()=>{ shared.WT="raid"; go("work"); openRecord("raid",r.id); })); DEC.forEach(d=>add("Items",`${d.id} · ${d.t}`,fd(d.date),()=>{ shared.WT="decisions"; go("work"); openRecord("decisions",d.id); })); }
  const hk=helpCk(q), hfirst=/^(help|how)/.test(q.trim());   /* BL-84: "help" and "how do I…" list the tasks first */
  return [...(hfirst?hk:[]),...out.slice(0,60),...(hfirst?[]:hk),...searchCkItems()]; })(q);
  if(!q||"new note quick capture".includes(q.toLowerCase())) out.splice(out.findIndex(x=>x.g==="Actions")+1||out.length,0,{g:"Actions",l:"New note",h:"⌘⇧N",fn:()=>openCapture()});   /* BL-126; BL-301 C: the capture drawer */
  MTG().filter(m=>mtgCanPick(m)).forEach(m=>{ const l=`Intake: process meeting ${m.title}`;
    if(!q||l.toLowerCase().includes(q.toLowerCase())) out.push({g:"Actions",l,h:fd(m.day),fn:()=>{ go("inbox"); MSEL.clear(); MSEL.add(m.id); renderMeetings(); processMeetings(); }}); });   /* BL-42 phase 3 */
  { const c=ckParse(q); if(c){ const pre=[], ql=String(q||"").trim().toLowerCase();
    if(!(c.ask&&(ql.split(/\s+/).length<3||out.some(x=>String(x.l).toLowerCase().startsWith(ql))))){   /* "New action" is the palette's own entry, not a request */
    if(c.pick) c.pick.forEach(x=>{ const isP=c.what==="person"; pre.push({g:"Change · which one?",l:isP?x:`${x.id} · ${x.t}`,h:isP?"person":pName(x.p),change:c,fn:()=>{ if(isP){ shared.CKPICK.owner=x; shared.CKPICK.ofor=c.phrase; } else { shared.CKPICK.target={k:x.k,id:x.id}; shared.CKPICK.for=c.phrase; } ckRefresh(); },keep:true}); });
    else if(c.ask) pre.push({g:"Change",l:`Give it to ask creaite: “${q.trim()}”`,h:"ask creaite",change:c,fn:()=>ckAsk(q.trim())});
    else pre.push({g:"Change",l:ckSummary(c),h:"↵ stages",change:c,fn:()=>ckStage(c),stage:true});
    out=[...pre,...out]; } } }   /* BL-209 */
  if(!q||"close the day evening end".includes(q.toLowerCase())||/^close( the)? day/i.test(q)) out.splice(!q?Math.max(0,out.findIndex(x=>x.g==="Actions")):0,0,{g:"Actions",l:"Close the day",h:"Today",fn:()=>{ go("today"); openClose(); }});   /* BL-205 */
  return out; }
export function drawCk(){ let g="",h=""; shared.CK.forEach((it,i)=>{ if(it.g!==g){ g=it.g; h+=`<div class="grp">${g}</div>`; } h+=`<button data-i="${i}" aria-selected="${i===shared.CKI}">${esc(it.l)}<small>${esc(it.h)}</small></button>`; }); putHTML($("#cmdkList"),h?raw(h):html`<div class="grp">No matches.</div>`); $("#cmdkList [aria-selected=true]")?.scrollIntoView({block:"nearest"});
  { const pv=$("#ckPrev");
    const it=shared.CK[shared.CKI]; pv.hidden=!(it&&it.change); putHTML(pv,it&&it.change?raw(ckPreview(it.change)):""); $("#cmdkList").querySelectorAll("button").forEach((b,i)=>{ if(shared.CK[i]&&shared.CK[i].g.startsWith("Change")) b.classList.add("ckchg"); }); } }
export function openCk(){ shared.CKPICK={}; $("#cmdkIn").value=""; shared.CK=ckItems(""); shared.CKI=0; drawCk(); openDialog("cmdk",{focus:"#cmdkIn"}); }
export function runCk(i){ const it=shared.CK[i]; if(!it) return; if(it.keep){ it.fn(); return; } $("#cmdk").close(); it.fn(); }
 
export async function setPalette(id){ if(S.palette===id) return; if(!await writeSettings({"dashboard.palette":id})) return; S.palette=id; themeFade(); applyTheme(); if(document.querySelector("#settingsBody [data-k=palette]")) renderSettings(); snack(`Theme: ${id}`); }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootAsk0120(){
$("#searchBtn").onclick=()=>openCk();
$("#searchBtn").onkeydown=e=>{ if(e.key==="Enter") openCk(); };
$("#cmdkIn").addEventListener("input",()=>{ shared.CK=ckItems($("#cmdkIn").value); shared.CKI=0; drawCk(); });
$("#cmdkIn").addEventListener("keydown",e=>{ if(e.key==="ArrowDown"){ e.preventDefault(); shared.CKI=Math.min(shared.CKI+1,shared.CK.length-1); drawCk(); } else if(e.key==="ArrowUp"){ e.preventDefault(); shared.CKI=Math.max(shared.CKI-1,0); drawCk(); } else if(e.key==="Enter"){ e.preventDefault(); runCk(shared.CKI); } });
$("#cmdkList").onclick=e=>{ const b=e.target.closest("[data-i]"); if(b) runCk(+b.dataset.i); };
$("#themeBtn").onclick=()=>{ const dark=document.documentElement.dataset.theme?document.documentElement.dataset.theme==="dark":matchMedia("(prefers-color-scheme: dark)").matches; S.theme=dark?"Light":"Dark"; themeFade(); applyTheme(); writeSettings({"dashboard.theme":S.theme}); };
}
/* ===== BL-205 (sprint-insight) ===== one ⌘K that does things. Plain code reads a change in words ("move ORX-A-021 to fri", "mark
   the sign-off action done", "Omar owns the SOW action", "add action for FAL: send the SOW, Sara, Friday") over parseWhen (BL-147),
   the people register and the item and milestone names; the palette shows it first, marked Change, with each field before → after
   and what else it touches, and Enter stages it: one proposal through the peek's staging (pkCommit, or the new item's route), never
   applied on the spot, so BL-189's rule holds and the pill offers Undo last and Apply. ⌘Enter stages and opens Review. Two matching
   items or people ask with a short pick list; text it can't read as a change still jumps and searches, and a request that looks
   like a change is offered to ask creaite. Nothing deletes. The verbs: move or set a date, mark done or closed, set the owner, set
   the priority or status, add an action, risk or decision. */
export const CKVERB=/^(move|push|pull|bring|set|mark|close|complete|finish|reopen|assign|give|make|change|update|add|new|log|raise|record|reschedule|delay)\b|\b(owns|is done|is closed|due)\b/i;
shared.CKPICK={};            /* what the pick list chose: {target: [k,id] | ms id, owner: name} for the text it was chosen for */
export const ckWords=t=>String(t||"").toLowerCase().replace(/[^a-z0-9\s-]/g," ").split(/\s+/).filter(w=>w.length>2&&!["the","for","and","action","risk","item","decision","milestone","task","this","that","with","from"].includes(w));
export const ckKind=id=>/-A-\d{3}$/.test(id)?"actions":/-D-\d{3}$/.test(id)?"decisions":/-M-\d{3}$/.test(id)?"milestones":/^[A-Z][A-Z0-9]{2,6}-\d{3}$/.test(id)?"raid":null;
export function ckMilestones(){ const out=[]; P.forEach(p=>(p.ms||[]).forEach(m=>{ if(m[3]) out.push({id:m[3],p:p.code,t:m[0],due:m[8]||m[1]||"",base:m[4]||"",done:m[2]==="done"}); })); return out; }
export const ckMs=id=>ckMilestones().find(m=>m.id===id);
/* the item a phrase names: an ID, or the open items (and milestones) whose title shares the most words, in the project it names */
export function ckTarget(phrase,{ms=true,kinds=["actions","raid","decisions"]}={}){ const raw=String(phrase||"").trim(); if(!raw) return {none:true};
  const idm=raw.toUpperCase().match(/\b[A-Z][A-Z0-9]{2,6}-(?:[AD]-|M-)?\d{3}\b/); if(idm){ const id=idm[0], k=ckKind(id);
    if(k==="milestones") return ckMs(id)?{k,id}:{none:true,why:`${id} isn't a milestone creaite knows`}; return k&&REC(k,id)?{k,id}:{none:true,why:`${id} isn't in the tracker`}; }
  if(shared.CKPICK.target&&shared.CKPICK.for===raw) return shared.CKPICK.target;
  const words=ckWords(raw), proj=P.find(p=>words.includes(p.code.toLowerCase())||p.name.toLowerCase().split(/\s+/).some(w=>w.length>3&&words.includes(w)));
  const pw=proj?new Set([proj.code.toLowerCase(),...proj.name.toLowerCase().split(/\s+/)]):new Set(), want=words.filter(w=>!pw.has(w));
  if(!want.length) return {none:true,why:proj?`Which item in ${proj.name}?`:""};
  const pool=[...kinds.flatMap(k=>pkArr(k).filter(x=>(k==="decisions"?x.st==="Pending":OPENST(x.st)||x.st==="Open")&&(!proj||x.p===proj.code)).map(x=>({k,id:x.id,t:x.t,p:x.p}))),
    ...(ms?ckMilestones().filter(m=>!m.done&&(!proj||m.p===proj.code)).map(m=>({k:"milestones",id:m.id,t:m.t,p:m.p})):[])];
  const score=x=>{ const tw=ckWords(x.t); return want.filter(w=>tw.some(t=>t===w||(w.length>3&&t.startsWith(w))||(t.length>3&&w.startsWith(t)))).length; };
  const sc=pool.map(x=>[score(x),x]).filter(s=>s[0]>0).sort((a,b)=>b[0]-a[0]); if(!sc.length) return {none:true,why:"No open item matches those words"};
  const top=sc.filter(s=>s[0]===sc[0][0]).map(s=>s[1]); return top.length===1?{k:top[0].k,id:top[0].id}:{pick:top.slice(0,6),phrase:raw}; }
/* a person: a known name, alias or email; two likely ones ask */
export function ckPerson(text){ const raw=String(text||"").trim(); if(!raw) return {none:true}; if(/^(me|myself|i)$/i.test(raw)) return {name:S.me};
  if(shared.CKPICK.owner&&shared.CKPICK.ofor===raw) return {name:shared.CKPICK.owner};
  const r=resolvePerson(raw); if(r.name) return {name:r.name}; if(r.candidates.length>1) return {pick:r.candidates,phrase:raw}; if(r.candidates.length===1) return {name:r.candidates[0]};
  return {name:raw,unknown:true}; }
// @ts-expect-error TS2362: a Date minus a Date is the milliseconds between them (valueOf)
export const ckDate=(text,base)=>{ const t=String(text||"").trim().replace(/^(to|on|by|for|until)\s+/i,""); if(/^[+-]\s*\d/.test(t)&&base){ const n=t.replace(/\s+/g,"").replace(/^-/,"-"), neg=n.startsWith("-"); const iso=parseWhen(neg?n.slice(1).replace(/^/,"+"):n,base); if(!iso) return null; if(!neg) return iso; const d=(new Date(iso+"T12:00:00")-new Date(base+"T12:00:00"))/864e5; return pkAdd(base,-d); } return parseWhen(t,TODAY,true); };
export const ckPri=t=>{ const m=String(t||"").toLowerCase().match(/\b(urgent|high|medium|low)\b/); return m?m[1][0].toUpperCase()+m[1].slice(1):null; };
/* text → {verb, target, patch, …} | {pick…} | {ask: why} | null (not a change) */
export function ckParse(q){ const c=ckParse1(q); return c&&c.ask&&!CKSTART.test(String(q||"").trim())?null:c; }   /* "items due fri" is a search, not a change */
export const CKSTART=/^(move|push|pull|bring|set|mark|close|complete|finish|reopen|assign|give|make|change|update|add|new|log|raise|record|reschedule|delay)\b/i;
export function ckParse1(q){ const s=String(q||"").trim().replace(/\s+/g," "); if(s.length<6||!CKVERB.test(s)||/^close (the )?day$/i.test(s)) return null; let m;
  const one=(phrase,fn,o)=>{ const t=ckTarget(phrase,o); if(t.pick) return {pick:t.pick,phrase:t.phrase,what:"item"}; if(t.none) return {ask:t.why||"creaite couldn't tell which item"}; return fn(t); };
  /* add an action, risk or decision */
  if((m=s.match(/^(?:add|new|log|raise|record)\s+(?:an?\s+)?(action|risk|issue|decision)\s+(?:for|on|in|to)\s+([^:]+?)\s*:\s*(.+)$/i))){ const kind=m[1].toLowerCase(), pw=m[2].trim().toLowerCase();
    const proj=P.find(p=>p.code.toLowerCase()===pw||p.name.toLowerCase()===pw||p.name.toLowerCase().startsWith(pw)||pw.split(/\s+/).includes(p.code.toLowerCase())); if(!proj) return {ask:`creaite doesn't know a project called “${m[2].trim()}”`};
    const parts=m[3].split(/\s*,\s*/), text=parts.shift().trim(); let owner=null, due=null;
    parts.forEach(x=>{ const d=ckDate(x); if(d&&!due) due=d; else if(!owner) owner=x; });
    const k=kind==="action"?"actions":kind==="decision"?"decisions":"raid", f={p:proj.code,t:text[0].toUpperCase()+text.slice(1)};
    if(owner){ const r=ckPerson(owner); if(r.pick) return {pick:r.pick,phrase:r.phrase,what:"person"}; f[k==="decisions"?"by":"o"]=r.name; }
    if(k==="actions"){ f.o=f.o||"TBC"; f.st="Open"; f.pr=S.defPriority||"Medium"; if(due) f.due=due; }
    if(k==="raid"){ f.type=kind==="issue"?"Issue":"Risk"; f.o=f.o||"TBC"; f.st="Open"; f.imp="Medium"; f.lik="Medium"; if(due) f.due=due; }
    if(k==="decisions"){ f.st="Pending"; f.by=f.by||""; if(due) f.due=due; f.srcIn="Typed in ⌘K"; }
    return {verb:"add",k,new:f,label:`New ${kind}`}; }
  /* mark done / close / reopen */
  if((m=s.match(/^(?:mark|set)\s+(.+?)\s+(?:as\s+)?(done|closed|complete|completed|finished)$/i))||(m=s.match(/^(?:close|complete|finish)\s+(.+)$/i))||(m=s.match(/^(.+?)\s+is\s+(done|closed|complete|finished)$/i)))
    return one(m[1],t=>t.k==="milestones"?{ask:"Mark a milestone done from its editor (Projects › the milestone)"}:t.k==="decisions"?{ask:"A decision is recorded as made, not done: use Record the decision"}:{verb:"done",...t,patch:{st:"Closed"},label:"Closed"},{ms:false,kinds:["actions","raid"]});
  if((m=s.match(/^reopen\s+(.+)$/i))) return one(m[1],t=>({verb:"status",...t,patch:{st:"Open"},label:"Reopened"}),{ms:false,kinds:["actions","raid"]});
  /* the owner */
  if((m=s.match(/^(.+?)\s+owns\s+(.+)$/i))||(m=s.match(/^(?:assign|give)\s+(.+?)\s+to\s+(.+)$/i))&&(m=[m[0],m[2],m[1]])||(m=s.match(/^(?:set|change)\s+(?:the\s+)?owner\s+(?:of\s+)?(.+?)\s+to\s+(.+)$/i))&&(m=[m[0],m[2],m[1]])){
    const who=m[1], what=m[2]; const r=ckPerson(who); if(r.pick) return {pick:r.pick,phrase:r.phrase,what:"person"};
    return one(what,t=>t.k==="milestones"?{ask:"A milestone's owner is set in its editor"}:{verb:"owner",...t,patch:{[t.k==="decisions"?"by":"o"]:r.name},label:t.k==="decisions"?"Decision maker":"Owner",unknown:r.unknown},{ms:false}); }
  /* the priority */
  if((m=s.match(/^(?:set|change|make)\s+(.+?)\s+(?:priority\s+)?(?:to\s+)?(urgent|high|medium|low)(?:\s+priority)?$/i))||(m=s.match(/^(.+?)\s+priority\s+(?:to\s+)?(urgent|high|medium|low)$/i)))
    return one(m[1].replace(/\s+priority$/i,""),t=>t.k!=="actions"?{ask:t.k==="raid"?"A RAID item's priority comes from its impact and likelihood: set those in the item":"Only actions have a priority"}:{verb:"priority",...t,patch:{pr:ckPri(m[2])},label:"Priority"},{ms:false,kinds:["actions","raid"]});
  /* the status */
  if((m=s.match(/^(?:set|change)\s+(.+?)\s+status\s+(?:to\s+)?([a-z]+)$/i))||(m=s.match(/^(.+?)\s+status\s+(?:to\s+)?([a-z]+)$/i))){ const st=m[2][0].toUpperCase()+m[2].slice(1).toLowerCase();
    return one(m[1],t=>t.k==="milestones"?{ask:"A milestone's state is set in its editor"}:pkStatuses(t.k).includes(st)?(t.k==="decisions"&&st!=="Pending"?{ask:"Record or withdraw a decision from its peek or the right-click menu"}:{verb:"status",...t,patch:{st},label:"Status"}):{ask:`${st} isn't a status for this item: ${pkStatuses(t.k).join(", ")}`},{ms:false}); }
  /* a date: move, push, set … due */
  if((m=s.match(/^(?:move|push|pull|bring|reschedule|delay)\s+(.+?)\s+((?:to|by|until|on)\s+.+|[+-]\s*\d+\s*[a-z]*)$/i))||(m=s.match(/^(?:set\s+)?(.+?)\s+(?:due|due date|needed by|forecast)\s+(?:to\s+|on\s+|by\s+)?(.+)$/i))){
    const what=m[1].replace(/\s+(?:due|due date)$/i,""), when=m[2];
    return one(what,t=>{ const cur=t.k==="milestones"?ckMs(t.id).due:REC(t.k,t.id).due; const iso=ckDate(when,cur||TODAY); if(!iso) return {ask:`“${when}” isn't a date creaite knows. ${DATE_HELP}`};
      if(t.k==="milestones") return {verb:"date",...t,patch:{fc:iso},label:"Forecast"};
      if(t.k==="decisions"&&REC(t.k,t.id).st!=="Pending") return {ask:"Only a pending decision has a needed-by date"};
      return {verb:"date",...t,patch:{due:iso},label:t.k==="decisions"?"Needed by":"Due date"}; }); }
  return {ask:"creaite couldn't read that as a change"}; }
/* ---- the preview ---- */
export const CKFN={o:"Owner",by:"Decision maker",due:"Due",fc:"Forecast",st:"Status",pr:"Priority",t:"Title",p:"Project",type:"Type",imp:"Impact",lik:"Likelihood"};
export const ckShow=(f,v)=>v==null||v===""?"—":["due","fc"].includes(f)?fd(v):f==="p"?pName(v):String(v);
export function ckTouches(c){ const out=[], x=c.k==="milestones"?ckMs(c.id):c.new?null:REC(c.k,c.id), p=c.new?c.new.p:x&&x.p;
  if(c.k==="milestones"&&x){ const tied=[...A.filter(a=>a.ms===c.id&&OPENST(a.st)).map(a=>a.id),...R.filter(r=>r.ms===c.id&&r.st==="Open").map(r=>r.id)];
    if(tied.length) out.push(`${plur(tied.length,"open item")} tied to it: ${tied.slice(0,5).join(", ")}${tied.length>5?"…":""}`);
    const late=[...A,...R].filter(i=>i.ms===c.id&&OPENST(i.st)&&i.due&&c.patch.fc&&i.due>c.patch.fc); if(late.length) out.push(`${plur(late.length,"item")} would then be due after it: ${late.map(i=>i.id).join(", ")}`);
    // @ts-expect-error TS2362: a Date minus a Date is the milliseconds between them (valueOf)
    if(x.base){ const was=Math.round((new Date(x.due+"T12:00:00")-new Date(x.base+"T12:00:00"))/864e5), now=Math.round((new Date(c.patch.fc+"T12:00:00")-new Date(x.base+"T12:00:00"))/864e5);
      out.push(`Slip against its baseline (${fd(x.base)}): ${was>0?"+":""}${was} → ${now>0?"+":""}${now} days`); } }
  else if(x){ if(x.ms){ const m=ckMs(x.ms); if(m){ const d=c.patch.due||x.due; out.push(`Tied to the milestone ${m.t} (forecast ${fd(m.due)})${d&&m.due&&d>m.due?": the new date is after it":""}`); } }
    const deps=R.filter(r=>r.type==="Dependency"&&r.st==="Open"&&x.ms&&r.ms===x.ms&&r.id!==c.id); if(deps.length) out.push(`Dependencies on the same milestone: ${deps.map(r=>r.id).join(", ")}`);
    if(c.patch.st==="Closed"&&x.client) out.push("It is client-visible: the next client report will show it closed"); }
  if(c.patch&&c.patch.due){ const w=weekendNote(c.patch.due); if(w) out.push(w.text); }
  if(c.patch&&c.patch.fc){ const w=weekendNote(c.patch.fc); if(w) out.push(w.text); }
  const days=(D.calendar||{}).days||{}, next=Object.keys(days).filter(d=>d>=TODAY).sort().flatMap(d=>(days[d]||[]).filter(e=>!e.all_day&&e.p===p&&(d>TODAY||e.start>=new Date().toTimeString().slice(0,5))).map(e=>[d,e]))[0];
  if(next) out.push(`Next meeting for ${pName(p)}: ${next[1].title}, ${longDay(next[0])} ${next[1].start}`);
  if(c.unknown) out.push(`“${c.patch.o||c.patch.by}” isn't in the people register: creaite asks before staging`);
  return out; }
export function ckPreview(c){ if(c.ask) return `<div class="ckpv"><div class="ckpvh">${ic("alert")} ${esc(c.ask)}</div><div class="sub">Press Enter to ask creaite to do it instead, or Esc.</div></div>`;
  if(c.pick) return `<div class="ckpv"><div class="ckpvh">Which ${c.what==="person"?"person":"one"} do you mean?</div><div class="sub">Pick one from the list, then press Enter to stage.</div></div>`;
  let title, rows;
  if(c.new){ title=`New ${c.k==="actions"?"action":c.k==="decisions"?"decision":(c.new.type||"risk").toLowerCase()} in ${pName(c.new.p)}`; rows=Object.entries(c.new).filter(([f])=>CKFN[f]&&f!=="p").map(([f,v])=>`<div class="ckln add"><span class="ckf">${CKFN[f]}</span><span class="ckb" aria-label="Added">+ ${esc(ckShow(f,v))}</span></div>`).join("")+ckChipsHtml(c); }
  else { const x=c.k==="milestones"?ckMs(c.id):REC(c.k,c.id); title=`${c.id} · ${x.t}`;
    rows=Object.entries(c.patch).map(([f,v])=>{ const was=c.k==="milestones"?(f==="fc"?x.due:""):x[f]; return `<div class="ckln"><span class="ckf">${CKFN[f]||f}</span><span class="ckdel" aria-label="Before">− ${esc(ckShow(f,was))}</span><span class="ckadd" aria-label="After">+ ${esc(ckShow(f,v))}</span></div>`; }).join(""); }
  const t=ckTouches(c);
  return `<div class="ckpv" aria-live="polite"><div class="ckpvh">${esc(title)}</div>${rows}${t.length?`<div class="cktch"><div class="sub">What else it touches</div><ul>${t.map(x=>`<li>${esc(x)}</li>`).join("")}</ul></div>`:'<div class="sub cktch">Nothing else is tied to it.</div>'}<div class="sub ckkeys"><kbd>↵</kbd> stage · <kbd>${MOD}↵</kbd> stage and open Review · <kbd>Esc</kbd> nothing changes</div></div>`; }
export function ckSummary(c){ if(c.new) return `Add: ${c.new.t}`; const x=c.k==="milestones"?ckMs(c.id):REC(c.k,c.id), f=Object.keys(c.patch)[0];
  return `${c.label}: ${c.id} ${x?"· "+x.t:""} → ${ckShow(f,c.patch[f])}`; }
/* ---- staging: the peek's path, never applied here ---- */
export async function ckStage(c,thenReview){ if(c.ask){ ckAsk($("#cmdkIn").value); return; } if(c.pick) return;
  let ok=false;
  if(c.new){ ok=await ckStageNew(c); }
  else if(c.k==="milestones"){ ok=await ckStageMs(c); }
  else { const k=c.k, x=REC(k,c.id), f={...c.patch}, f0=Object.keys(c.patch)[0];                 /* boardMove's checks, then the peek's staging */
    for(const n of ["o","by"]) if(n in f&&f[n]&&f[n]!=="TBC"){ const o=await ownerFinal(f[n]); if(o===null) return; f[n]=o; }
    if("st" in f&&k!=="decisions") f.closed=x.closed||null; if(k==="raid"){ if(!("imp" in f)) f.imp=x.imp; if(!("lik" in f)) f.lik=x.lik; }
    norm(k,f); const v={...f}; if("closed" in v) v.raised=x.raised; delete v.imp; delete v.lik; delete v.pr; if(k==="actions"&&"pr" in c.patch) v.pr=f.pr;
    const err=validate(k,v,false,x); if(err){ snack(oneLine(err)); return; }
    ok=await pkCommit(k,c.id,f,c.label,String(x[f0]??""),String(f[f0]??"")); }
  if(!ok) return;
  snack(`Staged: ${ckSummary(c)}. Nothing reaches the tracker until you apply`,()=>pkUndoLast());
  if(thenReview) go("review"); }
export async function ckStageNew(c){ const k=c.k, f={...c.new}; if(f.o&&f.o!=="TBC"){ const o=await ownerFinal(f.o); if(o===null) return false; f.o=o; } if(f.by){ const o=await ownerFinal(f.by); if(o===null) return false; f.by=o; }
  const err=validate(k,f,true,null); if(err){ snack(oneLine(err)); return false; } norm(k,f); const {values}=newItemOf(k,f); if(!await needVault()) return false;
  const meta={k,id:"nw"+Date.now().toString(36),patch:{},prev:{},label:"Created",from:"",to:f.t,at:nowStamp(),note:"⌘K",type:"act",isNew:true,title:f.t,p:f.p,known:pkArr(k).map(r=>r.id),ms:Date.now()};
  let name; try{ name=await writeProposal([{op:"new",table:k,values}],{peek:meta}); }catch(e){ snack("Not staged: "+e.message); return false; }
  shared.PKS.push({name,...meta}); pkPersist(); refreshAll(); return true; }
export async function ckStageMs(c){ const m=ckMs(c.id); if(!m||!await needVault()) return false; const changes={forecast_date:c.patch.fc};
  const meta={k:"milestones",id:c.id,patch:{},prev:{},label:"Forecast",from:m.due||"",to:c.patch.fc,at:nowStamp(),note:"⌘K",type:"act",ms:Date.now()};
  let name; try{ name=await writeProposal([{op:"update",table:"milestones",id:c.id,changes}],{peek:meta}); }catch(e){ snack("Not staged: "+e.message); return false; }
  shared.PKS.push({name,...meta}); pkPersist(); refreshAll(); return true; }
export function ckAsk(text){ $("#cmdk").open&&$("#cmdk").close(); openChat(); setTimeout(()=>{ const t=$("#chIn"); if(t){ t.value=text; t.dispatchEvent(new Event("input",{bubbles:true})); t.focus(); } },60); }
/* ---- into the palette: a change first, marked Change; a pick list asks; the jump list under it ---- */
export function ckRefresh(){ const i=$("#cmdkIn"); shared.CK=ckItems(i.value); shared.CKI=0; drawCk(); i.focus(); }
/* ===== end BL-205 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootAsk0207(){
$("#cmdkIn").addEventListener("keydown",e=>{ if(e.key==="Enter"&&(e.metaKey||e.ctrlKey)){ const it=shared.CK[shared.CKI]; if(it&&it.stage){ e.preventDefault(); e.stopImmediatePropagation(); $("#cmdk").close(); ckStage(it.change,true); } } },true);
}
/* ===== BL-206 (sprint-insight) ===== Close the day: the morning brief's evening counterpart. A one-minute card (Today's Close the day
   button, or ⌘K) with what moved today, what you promised today, what is still open, tomorrow's meetings (the next working day) and
   their prep pages, and on a Friday the weekly report line. Closing records only that the day was closed (system/staging/
   day-closed.json, by the live server); tomorrow's brief says so. Nothing reaches the tracker, nothing is sent. The nudge
   (day.close_from, 17:30 by default; empty is off) is a quiet line on Today, never a pop-up. */
/* BL-270 (sprint-ui-sweep): Close the day is a round door icon at the bottom right of Today's band. Its name and tooltip say what the
   old line said; the nudge (day.close_from) is a dot on it, never a pop-up; once closed it is in the accent colour. */
export function dcText(){ const d=DC(), now=new Date().toTimeString().slice(0,5), y=pkAdd(d.today||TODAY,-1);
  if(d.closed) return {t:`Day closed at ${d.closed} · look at the day again`,nudge:false,closed:true};
  const last=d.last?` · last closed ${d.last.day===y?"yesterday":longDay(d.last.day)} at ${d.last.at}`:"";
  if(d.from&&now>=d.from) return {t:`It's after ${d.from}: close the day when you're ready${last}`,nudge:true,closed:false};
  return {t:`Close the day${last}`,nudge:false,closed:false}; }
export function dcIcon(){ const b=$("#dayClose"); if(!b) return; const x=dcText();
  b.setAttribute("aria-label",x.t); b.dataset.tip=x.t; b.classList.toggle("closed",x.closed); b.classList.toggle("nudge",x.nudge);
  if(!b.firstChild) putHTML(b,html`${raw(ic("door"))}<span class="dcdot" aria-hidden="true"></span>`); }
/* BL-295: the card itself is components/closeday/CloseDay.jsx, a guided shutdown in four steps (it replaces BL-206's one card) */
export function openClose(){ openCloseDay(); }
/* ===== end BL-206 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootAsk0208(){
document.addEventListener("click",e=>{ if(e.target.closest("[data-dclose]")) openClose(); });
}
/* BL-231: test seams. A test replaces these through window.rbDraw, window.runSearch and window.send (core/globals.js puts the
   setters on window), so the page's own calls see the replacement. */
export const askSeams = { askLive: v => { askLive = v; }, rbDraw: v => { rbDraw = v; }, runSearch: v => { runSearch = v; }, send: v => { send = v; } };
