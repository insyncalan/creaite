// @ts-check
/* intake.js (BL-231 step 2b), moved from script/ by dev/tools/convert_area.py: 0052-inbox-bl-42-phase-1-add-meeting-files-th.js, 0053-bl-137-sprint-final.js, 0134-meetings-in-the-inbox-bl-42-phase-2.js, 0135-bl-119-sprint-polish.js, 0136-transcripts-bl-42-phase-3-select-with-tr.js, 0137-clear-day-bl-104-set-meetings-aside-now.js.
   Unchanged apart from `export`, `shared.` for the shared state (core/state.js) and the load-time steps, now in
   boot…() functions that src/main.js calls in today's order. */
import { openDialog } from "./components/Dialog.jsx";
import { askLive, askStream, mdView, openChat, runAsk, setRunning } from "./ask.js";
import { P } from "./core/data.js";
import { $, $$, addHTML, html, ibtn, ic, putHTML, raw } from "./core/dom.js";
import { addEl } from "./core/fields.js";
import { MSKEL } from "./core/motion.js";
import { pLink } from "./core/nav.js";
import { anim, D, days, fd, fdText, TODAY } from "./core/page.js";
import { api, OLDSERVER, oneLine, reloadData, snack, viaServer, writeSettings } from "./core/server.js";
import { shared } from "./core/state.js";
import { setRailCount } from "./stores/rail.js";
import { cell } from "./work.js";
/* ======================= Inbox (BL-42 phase 1): add meeting files, then process them ======================= */
export const INSEL=new Set(); export let INRUN=[];
export const INSTATE={new:"New",draft:"Draft ready — in Review",processed:"Already processed",processing:"Processing…",chat:"Goes with its transcript"};
export const kb=n=>n>1048576?`${(n/1048576).toFixed(1)} MB`:`${Math.max(1,Math.round(n/1024))} KB`;
export function inboxBadge(){ const n=(D.inbox||[]).filter(f=>f.state==="new").length; setRailCount("inbox",n,`${n} new file${n===1?"":"s"} in Intake`); }   /* BL-70: Intake; ids and the inbox/ folder keep their names */
/* ===== BL-137 (sprint-final) =====
   Upload files lists only files that were uploaded. A file Calendar import loaded is known by its recorded event ID (`f.event`), never
   by its name; it is never listed there at any stage. Its state, Preview and Remove are on its meeting row. The Intake badge and the
   "waiting" counts still count a loaded transcript that has not been processed. */
export const uploadedFiles=()=>(D.inbox||[]).filter(f=>f.uploaded!==false&&!f.event);
export function renderInbox(){ const L=uploadedFiles(); [...INSEL].forEach(p=>{ if(!L.some(f=>f.path===p&&f.state==="new")) INSEL.delete(p); });
  putHTML($("#inboxTbl"),html`<thead><tr><th style="width:32px"></th><th>File</th><th>Type</th><th>Size</th><th>Added</th><th>Likely project</th><th>State</th><th></th></tr></thead><tbody>${L.length?L.map(f=>{ const st=INRUN.includes(f.path)?"processing":f.state;
    return html`<tr data-inf="${f.path}"><td><input type="checkbox" aria-label="Select ${f.name}" ${raw(INSEL.has(f.path)?"checked":"")} ${raw(st==="new"?"":"disabled")}></td><td class="title">${f.name}</td><td>${f.ext}</td><td>${kb(f.size)}</td><td style="white-space:nowrap">${fd(f.date)}</td><td>${f.p?raw(pLink(f.p)):html`<span class="sub">Not sure</span>`}</td><td><span class="tag ${st==="new"?"":"sub"}">${INSTATE[st]}</span>${st==="draft"&&html` <a href="#" data-go="review" class="sub">Open Review</a>`}</td><td style="white-space:nowrap;text-align:right">${raw(ibtn("eye","Preview",'data-inprev aria-haspopup="dialog"',"sm"))}${raw(ibtn("trash","Remove from Intake",`data-inrm ${st==="processing"?"disabled":""}`,"sm no"))}</td></tr>`; }):html`<tr><td colspan="8"><div class="empty minbox">No uploaded files waiting.</div></td></tr>`}</tbody>`);
  $("#inboxGo").disabled=!INSEL.size||!!shared.RUN; $("#inboxGo").title=shared.RUN?"ask creaite is busy; try again when it's finished":""; $("#inboxGo").textContent=INSEL.size?`Process ${INSEL.size} selected`:"Process selected"; inboxBadge(); renderMeetings(); }
export async function addInboxFiles(files){ if(!viaServer()){ snack("Adding files needs the live server"); return; } let added=0;
  for(const f of files){ const ext=(f.name.match(/\.[^.]+$/)||[""])[0].toLowerCase();
    if(![".vtt",".docx",".txt",".md",".pdf"].includes(ext)){ snack(`${f.name}: only .vtt, .docx, .txt, .md or .pdf`); continue; }
    if(f.size>25*1048576){ snack(`${f.name} is over 25 MB`); continue; }
    const data=await new Promise((res,rej)=>{ const fr=new FileReader(); fr.onload=()=>res(String(fr.result).split(",")[1]||""); fr.onerror=()=>rej(fr.error); fr.readAsDataURL(f); });
    const r=await api("/api/inbox/upload",{name:f.name,data}); if(!r.ok){ if(r.message===OLDSERVER){ snack(OLDSERVER); return; } snack(`${f.name}: ${oneLine(r.message)}`); continue; }
    added++; (D.inbox=D.inbox||[]).push({name:r.name,path:r.path,ext:ext.slice(1),size:f.size,date:TODAY,p:null,state:"new",uploaded:true}); INSEL.add(r.path); }
  if(added){ snack(`${added} file${added===1?"":"s"} added to Intake`); await reloadData(); renderInbox(); } }
export async function processInbox(){ const paths=[...INSEL]; if(!paths.length||shared.RUN) return; if(!viaServer()){ snack("Processing needs the live server"); return; }
  INRUN=paths; INSEL.clear(); renderInbox(); openChat(); addEl("msg u",html`${`Process ${paths.length} file${paths.length===1?"":"s"} from Intake`}`);
  try{ await askLive(`process ${paths.join("; ")}`,`Process ${paths.length===1?paths[0]:paths.length+" Intake files"} into draft minutes and proposed items`); }
  finally{ INRUN=[]; await reloadData(); renderInbox(); } }
/* preview before processing; remove moves the file to backups (Undo puts it back) */
export async function previewInbox(path){ if(!viaServer()){ snack("Previewing needs the live server"); return; } const r=await api("/api/inbox/preview",{path});
  if(!r.ok){ snack(r.message===OLDSERVER?OLDSERVER:oneLine(r.message)); return; }
  if(r.open){ const o=await api("/api/open",{path}); snack(o.ok?"Opened in its own app":oneLine(o.message)); return; }
  $("#inPrevName").textContent=r.name; $("#inPrevText").textContent=r.text||"(empty)";
  { const md=/\.(md|markdown)$/i.test(r.name||path)&&!!r.text; $("#inPrevText").hidden=md; $("#inPrevMd").hidden=!md; putHTML($("#inPrevMd"),raw(md?mdView(r.text,{hBase:2}):"")); }   /* BL-196: a Markdown file is shown formatted */ $("#inPrevCut").hidden=!r.cut; $("#inPrev").dataset.path=path; openDialog("inPrev"); }
export async function removeInbox(path){ if(!viaServer()){ snack("Removing needs the live server"); return; } const f=(D.inbox||[]).find(x=>x.path===path), r=await api("/api/inbox/remove",{path});
  if(!r.ok){ snack(r.message===OLDSERVER?OLDSERVER:oneLine(r.message)); return; }
  INSEL.delete(path); D.inbox=(D.inbox||[]).filter(x=>x.path!==path); renderInbox();
  snack(`Removed ${f?f.name:path} from Intake (kept in backups)`,async()=>{ const b=await api("/api/inbox/restore",{kept:r.kept}); if(b.ok){ await reloadData(); renderInbox(); snack("Back in Intake"); } else snack(oneLine(b.message)); }); }
     /* BL-137: uploaded files only */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootIntake0053(){
$("#inboxPick").onclick=e=>{ e.stopPropagation(); $("#inboxFile").click(); };
$("#inboxFile").onchange=e=>{ addInboxFiles([...e.target.files]); e.target.value=""; };
$("#inboxDrop").addEventListener("dragover",e=>{ e.preventDefault(); e.currentTarget.classList.add("over"); });
$("#inboxDrop").addEventListener("dragleave",e=>e.currentTarget.classList.remove("over"));
$("#inboxDrop").addEventListener("drop",e=>{ e.preventDefault(); e.currentTarget.classList.remove("over"); addInboxFiles([...e.dataTransfer.files]); });
$("#inboxDrop").addEventListener("keydown",e=>{ if(e.key==="Enter"||e.key===" "){ e.preventDefault(); $("#inboxFile").click(); } });
$("#inboxTbl").addEventListener("click",e=>{ const tr=e.target.closest("tr[data-inf]"); if(!tr) return;
  if(e.target.closest("[data-inprev]")) previewInbox(tr.dataset.inf); else if(e.target.closest("[data-inrm]")) removeInbox(tr.dataset.inf); });
$("#inPrevOpen").onclick=async()=>{ const o=await api("/api/open",{path:$("#inPrev").dataset.path}); if(!o.ok) snack(oneLine(o.message)); };
$("#inboxTbl").addEventListener("change",e=>{ const tr=e.target.closest("tr[data-inf]"); if(!tr) return; e.target.checked?INSEL.add(tr.dataset.inf):INSEL.delete(tr.dataset.inf); renderInbox(); });
$("#inboxNew").onclick=()=>{ uploadedFiles().filter(f=>f.state==="new").forEach(f=>INSEL.add(f.path)); renderInbox(); };
$("#inboxGo").onclick=processInbox;
}
/* ===== Meetings in the Inbox (BL-42 phase 2) ===== */
/* This week's meetings from Alan's calendar (saved by cx-sweep), above the files: Teams or in person, organiser,
   likely project (changeable; remembered for the series, as meeting prep does) and whether each was processed (by its
   calendar event ID). Process selected (BL-119) loads each transcript and then sends the saved file to cx-minutes through the
   run engine, one meeting after another. The Transcript column is the sweep's lookup (phase 3). */
export const MTG=()=>(D.meetings&&D.meetings.rows)||[], MSEL=new Set(), MRUN={};
/* A meeting that hasn't ended can't have a transcript yet: greyed and not selectable until it ends (Alan, 2026-10-09).
   Worked out in the page, so a meeting becomes selectable on its own once its end time passes. */
export let nowHM = function(){ const n=new Date(); return `${String(n.getHours()).padStart(2,"0")}:${String(n.getMinutes()).padStart(2,"0")}`; };   /* a function, so tests can set the clock */
export const mtgLater=m=>m.day>TODAY||(m.day===TODAY&&(m.end||m.start||"")>nowHM());
export const mtgCanPick=m=>!!m.id&&!m.processed&&!m.draft&&!mtgLater(m)&&MRUN[m.id]!=="processing";
     /* BL-73: inside the Calendar import section */
export function mtgState(m){ const r=MRUN[m.id];
  if(mtgLater(m)) return html`<span class="sub">${m.day===TODAY&&m.start&&m.start<=nowHM()?"In progress: a transcript comes after it ends":"Not happened yet"}</span>`;
  if(r==="loading") return html`<span class="spin" aria-hidden="true"></span> Loading the transcript…`;     /* BL-119: Process selected loads first */
  if(r==="processing") return html`<span class="spin" aria-hidden="true"></span> Processing…`;
  if(m.processed) return html`<span class="tag">Already processed</span> <span class="sub">${fd(m.processed)}</span>`;
  if(m.draft||r==="draft") return html`<a href="#" data-go="review" class="hlink">Draft ready in Review</a>`;
  if(r&&r.startsWith("skipped:")) return html`<span class="tag">Skipped</span> <span class="sub">${r.slice(8)}</span>`;
  if(r&&r.startsWith("failed:")) return html`<span class="tag warn">Couldn't</span> <span class="sub">${r.slice(7)}</span>`;
  if(m.loaded) return html`<span class="tag">Loaded</span> <span class="sub">in the inbox, not processed yet</span>`;     /* BL-137: the file is not listed under Upload files */
  return html`<span class="sub">Not processed</span>`; }
/* BL-42 phase 3, BL-104: what the sweep found for each meeting. A transcript that exists and isn't processed stands out (tint, accent bar and a
   Transcript badge: words as well as colour); no transcript, not transcribed and no access are muted; processed ones are quiet. */
export const TXLABEL={available:"Transcript available",not_transcribed:"Not transcribed",none:"No transcript",no_access:"No access"};
export const mtgHasTx=m=>m.transcript==="available"&&!m.processed&&!m.draft;
export const mtgLoadable=m=>!!m.id&&!m.processed&&!m.draft&&!m.loaded&&!mtgLater(m)&&MRUN[m.id]!=="processing"&&(m.transcript==="available"||(!m.transcript&&m.teams));
export const mtgCheckable=m=>!!m.id&&m.teams&&!mtgLater(m)&&!m.processed&&m.transcript!=="none";
export let MTGSHOW="all"; export const mtgShown=m=>MTGSHOW!=="tx"||mtgHasTx(m);
export function mtgTx(m,i){ const r=MRUN[m.id], spin=html`<span class="spin" aria-hidden="true"></span> `;
  if(r==="checking") return html`${spin}Checking…`; if(r==="loading") return html`${spin}Loading…`;
  const label=m.transcript?TXLABEL[m.transcript]:mtgLater(m)?"":"Not checked yet";
  const chk=mtgCheckable(m)?html` <button type="button" class="linkbtn mtgchk" data-chk="${i}" ${raw(viaServer()?"":"disabled")} title="${viaServer()?"Look it up again":"Needs the live server"}">${m.transcript?"Check again":"Check"}</button>`:"";
  const loadedAct=m.loaded?html` <button type="button" class="linkbtn" data-mprev="${i}">Preview</button>${!(m.processed||m.draft||r==="processing")&&html` <button type="button" class="linkbtn" data-mrm="${i}">Remove</button>`}`:"";     /* BL-137 */
  const state=m.loaded?html`<span class="tag">Loaded</span> <span class="sub">in the inbox</span>${loadedAct}`:m.transcript==="available"?html`<span class="mtgyes">${label}</span>`:html`<span class="sub">${label}</span>`;
  return html`${state}${chk}<div class="sub mtgwhen">${m.transcript_checked?`checked ${fdText(m.transcript_checked)}`:""}</div>`; }
export function renderMeetings(){ const mt=D.meetings||{}, L=MTG(); [...MSEL].forEach(id=>{ const m=L.find(x=>x.id===id); if(!m||!mtgCanPick(m)) MSEL.delete(id); });
  $("#mtgRead").textContent=mt.fetched?`Calendar read ${fdText(mt.fetched)}`:"";
  const busy=!!shared.RUN||(typeof shared.BUSY!=="undefined"&&shared.BUSY);
  $("#mtgGo").disabled=!MSEL.size||busy||!viaServer(); $("#mtgGo").textContent=MSEL.size?`Process ${MSEL.size} selected`:"Process selected";
  $("#mtgGo").title=!viaServer()?"Needs the live server":busy?"ask creaite is busy; try again when it's finished":"";
  const ld=L.filter(m=>MSEL.has(m.id)&&mtgLoadable(m)).length, offTx=!ld||busy||!viaServer(), why=!viaServer()?"Needs the live server":busy?"ask creaite is busy; try again when it's finished":ld?"":"Tick meetings that have a transcript";
  $("#mtgLoad").disabled=offTx; $("#mtgLoad").title=why;
  $("#mtgLoad").textContent=ld?`Load ${ld} into inbox`:"Load into inbox";
  $("#mtgTx").disabled=!L.some(m=>mtgHasTx(m)&&mtgCanPick(m));
  $("#mtgRefresh").disabled=busy||!viaServer(); $("#mtgRefresh").title=!viaServer()?"Needs the live server":"";
  if(!mt.fetched){ putHTML($("#mtgBody"),html`<div class="empty">No calendar yet: it comes in with the sweep. Refresh reads it now.</div>`); $("#mtgNew").disabled=true; return; }
  if(!L.length){ putHTML($("#mtgBody"),html`<div class="empty">${(mt.cleared||[]).length?`Every meeting since ${fd(mt.from)} is cleared.`:`No meetings since ${fd(mt.from)}.`}</div>${clrList()}`); $("#mtgNew").disabled=true; return; }
  $("#mtgNew").disabled=!L.some(m=>mtgCanPick(m)&&!m.private);
  const shown=mtgShown, nTx=L.filter(mtgHasTx).length;
  putHTML($("#mtgChips"),html`<button type="button" class="vchip" data-show="all" aria-pressed="${String(MTGSHOW!=="tx")}">All</button><button type="button" class="vchip" data-show="tx" aria-pressed="${String(MTGSHOW==="tx")}">With transcripts · ${nTx}</button>`);
  const days=[...new Set(L.filter(shown).map(m=>m.day))], org=m=>m.organiser===true?"You":m.organiser?m.organiser:html`<span class="sub">—</span>`;
  const sel=on=>raw(on?"selected":""), off=on=>raw(on?"disabled":"");
  const projSel=(m,i)=>html`<select class="mtgp" data-mi="${i}" aria-label="Project for ${m.title}"><option value="" ${sel(!m.p)}>Not sure</option>${P.map(p=>html`<option value="${p.code}" ${sel(m.p===p.code)}>${p.name}</option>`)}<option value="_portfolio" ${sel(m.p==="_portfolio")}>Portfolio</option></select>`;
  const noIds=L.some(m=>!m.id);
  putHTML($("#mtgBody"),html`${clrConfirm()}<div class="tbl"><table class="mtgtbl"><thead><tr><th style="width:32px"></th><th>Time</th><th>Meeting</th><th>Where</th><th>Organiser</th><th>Project</th><th>State</th><th>Transcript</th><th style="width:30px"></th></tr></thead><tbody>${days.map(d=>html`<tr class="mtgday"><td colspan="9"><div class="mtgdayh"><span>${new Date(d).toLocaleDateString("en-GB",{weekday:"long"})} ${fd(d)}</span><span class="sp"></span><button class="btn mtgclr" data-clr="day" data-day="${d}" ${off(clrOff())} title="${clrOff()?"Needs the live server":"Set this day's meetings aside"}">Clear day · ${L.filter(m=>m.day===d&&shown(m)).length}</button></div></td></tr>${L.map((m,i)=>[m,i]).filter(([m])=>m.day===d&&shown(m)).map(([m,i])=>html`<tr data-mid="${m.id||""}" class="${m.private?"mtgpriv":""}${mtgLater(m)?" mtglater":""}${mtgHasTx(m)?" mtgtx":""}${m.transcript&&m.transcript!=="available"&&!m.processed?" mtgmute":""}${m.processed?" mtgdone":""}" ${mtgLater(m)&&html`title="Not happened yet: no transcript until it has ended"`}><td><input type="checkbox" data-mi="${i}" aria-label="Select ${m.title}" ${raw(MSEL.has(m.id)?"checked":"")} ${off(!mtgCanPick(m))} ${!m.id&&html`title="Refresh the calendar to pick this meeting"`}></td><td style="white-space:nowrap">${m.start}–${m.end}</td><td class="title">${mtgHasTx(m)&&html`<span class="txbadge">Transcript</span> `}${m.title}${m.private?html` <span class="sub">private</span>`:""}</td><td>${m.teams?html`<span class="mtgteams" title="Teams meeting">${raw(MTGI)} Teams</span>`:html`<span class="sub">In person</span>`}</td><td>${org(m)}</td><td>${projSel(m,i)}</td><td>${mtgState(m)}</td><td>${mtgTx(m,i)}</td><td><button class="mtgx" data-clr="one" data-mi="${i}" ${off(clrOff())} aria-label="Clear ${m.title}" title="Clear this meeting">${raw(ic("x"))}</button></td></tr>`)}`)}</tbody></table></div>${noIds&&html`<p class="sub" style="margin:8px 0 0">Some meetings were saved before the calendar kept IDs: Refresh to pick them.</p>`}${clrList()}`);
}
export const MTGI=ic("video",{size:14,w:2});   /* BL-158 */
export const mtgBusy=()=>!!shared.RUN||(typeof shared.BUSY!=="undefined"&&shared.BUSY);
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootIntake0134(){
putHTML($("#isecCalBody"),html`<div class="mtgsec" id="mtgSec"><div class="mtghead"><span class="sub" id="mtgRead"></span><span class="sp"></span><button class="btn" id="mtgRefresh">Refresh</button><button class="btn" id="mtgNew">Select new</button><button class="btn" id="mtgTx">Select with transcripts</button><button class="btn" id="mtgLoad" disabled>Load into inbox</button><button class="btn primary" id="mtgGo" disabled>Process selected</button></div><div class="mtgchips" id="mtgChips" role="group" aria-label="Show"></div><div id="mtgBody"></div></div>`);
}
/* ===== BL-119 (sprint-polish) =====
   Process n selected is the one button for processing. For each ticked meeting, in turn: load its transcript and meeting chat as Load
   into inbox does (written by the server, with the calendar event ID), then run cx-minutes on the saved file. A row that has no
   transcript to load (No transcript, Not transcribed, No access, or not a Teams meeting) is skipped with the reason on its row, and
   the others carry on. A meeting already loaded is processed from its file. Claude never searches Teams for a missing transcript. */
export const TXWHY={none:"No transcript for this meeting",not_transcribed:"Not transcribed yet",no_access:"No access to the transcript"};
export const mtgSkip=m=>m.loaded?"":TXWHY[m.transcript]||(!m.transcript&&!m.teams?"Not a Teams meeting, so there is no transcript to load":"");
export async function processMeetings(){ const L=MTG().filter(m=>MSEL.has(m.id)); if(!L.length) return;
  if(!viaServer()){ snack("Processing needs the live server"); return; } if(mtgBusy()){ snack("ask creaite is busy; try again when it's finished"); return; }
  MSEL.clear(); let chat=false; const PL=L.length>1?`Processing ${L.length} meetings`:`Processing “${L[0].title}”`;     /* BL-139: what the badge says */
  for(const m of L){ const why=mtgSkip(m); if(why){ MRUN[m.id]="skipped:"+why; renderMeetings(); continue; }
    if(!chat){ openChat(); chat=true; } const when=`${fd(m.day)} at ${m.start}`; let now=m;
    if(!m.loaded){ MRUN[m.id]="loading"; renderMeetings(); runAsk(addEl("msg u",html`${`Load the transcript of “${m.title}” (${when})`}`));
      shared.RUNLABEL=PL; try{ await jobLive("/api/transcripts/load",{id:m.id}); }catch(e){} delete MRUN[m.id]; await reloadData(); now=MTG().find(x=>x.id===m.id);
      if(!now||!now.loaded){ MRUN[m.id]="skipped:"+(TXWHY[now&&now.transcript]||"No transcript could be loaded"); renderMeetings(); continue; } }
    MRUN[m.id]="processing"; renderMeetings(); addEl("msg u",html`${`Process the meeting “${m.title}” (${when})`}`); const before=$$("#chLog .msg.a").length;
    shared.RUNLABEL=PL; try{ await askLive(`process ${now.loaded}`,`Process “${m.title}” (${when}) into draft minutes and proposed items`); }catch(e){} await reloadData();
    const after=MTG().find(x=>x.id===m.id), said=[...$$("#chLog .msg.a")].slice(before).map(e=>e.textContent.trim()).filter(Boolean).pop()||"";
    MRUN[m.id]=after&&(after.draft||after.processed)?"draft":`failed:${oneLine(said).split(/(?<=[.!?])\s/)[0].slice(0,140)||"no draft came back"}`; renderMeetings(); } }
export async function refreshCalendar(){ const body=$("#mtgBody"); let /** @type {any} */ sk=null; const t=setTimeout(()=>{ if(body){ sk=putHTML(document.createElement("div"),MSKEL).firstChild; body.before(sk); } },150);   /* BL-263 */
  try{ if(!viaServer()){ snack("Refreshing needs the live server"); return; } if(mtgBusy()){ snack("ask creaite is busy; try again when it's finished"); return; }
  $("#mtgRead").textContent="Refreshing…"; openChat(); addEl("msg u","Refresh calendar");
  try{ await askLive("refresh calendar","Refresh the calendar for Intake and Today"); }catch(e){} await reloadData(); renderMeetings(); }
  finally{ clearTimeout(t); if(sk){ sk.remove(); anim($("#mtgBody"),[{opacity:0,transform:"translateY(4px)"},{opacity:1,transform:"none"}],{duration:320}); } } }
export async function mtgProject(i,code){ const m=MTG()[i]; if(!m) return; const was=m.p; m.p=code||null; m.how=code?"remembered":"unsure";
  if(m.private||!code){ renderMeetings(); return; }             /* a private "Busy" has no series to remember */
  const map={...((D.prep||{}).series||{}),[m.series]:code};
  if(await writeSettings({"prep.series":map})){ /** @type {any} */(D.prep=D.prep||{}).series=map; MTG().forEach(x=>{ if(x.series===m.series&&!x.private){ x.p=code; x.how="remembered"; } });
    Object.values((D.prep||{}).meetings||{}).forEach(x=>{ if(x.series===m.series){ x.p=code; x.how="remembered"; } }); snack("Remembered for this meeting series"); }
  else m.p=was; renderMeetings(); }
   /* a meeting becomes selectable once it ends */
 
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootIntake0135(){
$("#mtgSec").addEventListener("change",e=>{ const el=e.target; if(el.matches(".mtgp")){ mtgProject(+el.dataset.mi,el.value); return; }
  if(el.type==="checkbox"&&el.dataset.mi!=null){ const m=MTG()[+el.dataset.mi]; if(!m||!m.id) return; el.checked?MSEL.add(m.id):MSEL.delete(m.id); renderMeetings(); } });
$("#mtgNew").onclick=()=>{ MTG().filter(m=>mtgCanPick(m)&&!m.private).forEach(m=>MSEL.add(m.id)); renderMeetings(); };
setInterval(()=>{ if(shared.VIEW==="inbox"&&!document.activeElement?.matches?.(".mtgp")) renderMeetings(); },60000);
$("#mtgGo").onclick=processMeetings;
$("#mtgRefresh").onclick=refreshCalendar;
}
/* ===== Transcripts (BL-42 phase 3): Select with transcripts, Load into inbox, Load and process, Check again ===== */
/* a transcript job (a check or a load) goes through the run engine like a question, but isn't a chat; the server writes the status and the files */
export let jobLive = async function(url,body){ if(!shared.RUNLABEL) shared.RUNLABEL=/load/.test(url)?"Loading a transcript":"Checking a transcript"; const id=`r-${Date.now().toString(36)}-${Math.random().toString(36).slice(2,8)}`, ctl=new AbortController(); shared.RUN={id,ctl}; setRunning(true);
  try{ await askStream(url,{...body,run:id},true,ctl,undefined,true); } finally{ shared.RUN=null; setRunning(false); } };   /* BL-326: drawn plainly (steps and the closure) */
export async function checkMeeting(m){ if(!viaServer()){ snack("Checking needs the live server"); return; } if(mtgBusy()){ snack("ask creaite is busy; try again when it's finished"); return; }
  MRUN[m.id]="checking"; renderMeetings(); openChat(); runAsk(addEl("msg u",html`${`Check the transcript of “${m.title}” (${fd(m.day)} at ${m.start})`}`));
  try{ await jobLive("/api/transcripts/check",{id:m.id}); }catch(e){} delete MRUN[m.id]; await reloadData(); renderMeetings(); }
export async function loadMeetings(){ const L=MTG().filter(m=>MSEL.has(m.id)&&mtgLoadable(m)); if(!L.length) return;
  if(!viaServer()){ snack("Loading needs the live server"); return; } if(mtgBusy()){ snack("ask creaite is busy; try again when it's finished"); return; }
  MSEL.clear(); openChat();
  for(const m of L){ const when=`${fd(m.day)} at ${m.start}`; MRUN[m.id]="loading"; renderMeetings();
    runAsk(addEl("msg u",html`${`Load the transcript of “${m.title}” (${when})`}`));
    try{ await jobLive("/api/transcripts/load",{id:m.id}); }catch(e){} delete MRUN[m.id]; await reloadData();
    renderMeetings(); } }
/* BL-137: a loaded transcript and its chat are previewed and removed from the meeting's row (Remove only before it is processed; one Undo) */
export async function removeLoaded(m){ if(!viaServer()){ snack("Removing needs the live server"); return; } const files=(D.inbox||[]).filter(f=>f.event===m.id), kept=[];
  for(const f of files){ const r=await api("/api/inbox/remove",{path:f.path}); if(!r.ok){ snack(r.message===OLDSERVER?OLDSERVER:oneLine(r.message)); break; } kept.push(r.kept); }
  if(!kept.length) return; await reloadData(); renderInbox(); renderMeetings();
  snack(`Removed the loaded transcript of “${m.title}” (kept in backups)`,async()=>{ for(const k of kept) await api("/api/inbox/restore",{kept:k}); await reloadData(); renderInbox(); renderMeetings(); snack("Back in the inbox"); }); }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootIntake0136(){
$("#mtgTx").onclick=()=>{ MTG().filter(m=>mtgHasTx(m)&&mtgCanPick(m)).forEach(m=>MSEL.add(m.id)); renderMeetings(); };
$("#mtgChips").onclick=e=>{ const b=e.target.closest("[data-show]"); if(b){ MTGSHOW=b.dataset.show; renderMeetings(); } };
$("#mtgLoad").onclick=loadMeetings;
$("#mtgSec").addEventListener("click",e=>{ const pv=e.target.closest("[data-mprev]"), rm=e.target.closest("[data-mrm]"); if(pv||rm){ const m=MTG()[+(pv||rm).dataset[pv?"mprev":"mrm"]]; if(m&&m.loaded) pv?previewInbox(m.loaded):removeLoaded(m); return; }
  const b=e.target.closest("[data-chk]"); if(b&&!b.disabled){ const m=MTG()[+b.dataset.chk]; if(m) checkMeeting(m); } });
}
/* ===== Clear day (BL-104): set meetings aside, now and in every later intake. Cleared is not processed: nothing is written
   to processed.txt or the tracker. Saved by the live server in system/staging/intake-cleared.json. ===== */
export const MCLR={ask:null,open:false};
export const clrOff=()=>!viaServer();
export const clrKeys=ms=>ms.map(m=>({key:m.key,day:m.day,start:m.start,title:m.title}));
export const clrUnproc=m=>m.transcript==="available"&&!m.processed&&!m.draft;       /* the sweep's check (BL-42 phase 3) says a transcript exists */
export function clrConfirm(){ if(!MCLR.ask) return ""; const n=MTG().filter(m=>MCLR.ask.includes(m.key)&&clrUnproc(m)).length;
  return html`<div class="mtgconfirm" role="alert"><span>${n} of these ${n===1?"has a transcript":"have transcripts"} you haven't processed. Clear anyway?</span><span class="sp"></span><button class="btn primary" data-clr="yes">Clear anyway</button><button class="btn" data-clr="no">Cancel</button></div>`; }
export function clrList(){ const C=(D.meetings||{}).cleared||[]; if(!C.length){ MCLR.open=false; return ""; }
  const days=[...new Set(C.map(m=>m.day))];
  return html`<div class="mtgcleared"><button class="clrlink" data-clr="toggle" aria-expanded="${String(MCLR.open)}">Cleared (${C.length})</button>${MCLR.open&&html`<div class="mtgclrlist">${days.map(d=>html`<div class="clrday"><span>${new Date(d).toLocaleDateString("en-GB",{weekday:"long"})} ${fd(d)}</span><span class="sp"></span><button class="btn mtgclr" data-clr="restoreday" data-day="${d}">Restore day</button></div>${C.filter(m=>m.day===d).map(m=>html`<div class="clrrow"><span class="sub" style="white-space:nowrap">${m.start}–${m.end}</span><span>${m.title}</span><span class="sp"></span><button class="btn mtgclr" data-clr="restore" data-key="${m.key}" aria-label="Restore ${m.title}">Restore</button></div>`)}`)}</div>`}</div>`; }
export async function mtgClear(ms,force){ ms=ms.filter(m=>MRUN[m.id]!=="processing"); if(!ms.length) return;
  if(!viaServer()){ snack("Clearing needs the live server"); return; }
  if(!force&&ms.some(clrUnproc)){ MCLR.ask=ms.map(m=>m.key); renderMeetings(); return; }
  MCLR.ask=null; const r=await api("/api/intake/clear",{op:"clear",items:clrKeys(ms)});
  if(!r.ok){ snack(oneLine(r.message||"Couldn't clear those meetings")); renderMeetings(); return; }
  const keys=ms.map(m=>m.key); await reloadData(); renderMeetings();
  snack(`Cleared ${ms.length} meeting${ms.length===1?"":"s"}`,()=>mtgRestore({op:"restore",keys})); }
export async function mtgRestore(body){ const r=await api("/api/intake/clear",body);
  if(!r.ok){ snack(oneLine(r.message||"Couldn't restore")); return; } await reloadData(); renderMeetings(); snack(`Restored ${r.count} meeting${r.count===1?"":"s"}`); }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootIntake0137(){
$("#mtgSec").addEventListener("click",e=>{ const b=e.target.closest("[data-clr]"); if(!b||b.disabled) return; const k=b.dataset.clr, L=MTG();
  if(k==="day") mtgClear(L.filter(m=>m.day===b.dataset.day&&mtgShown(m)));        /* only what is listed */
  else if(k==="one"){ const m=L[+b.dataset.mi]; if(m) mtgClear([m]); }
  else if(k==="yes") mtgClear(L.filter(m=>(MCLR.ask||[]).includes(m.key)),true);
  else if(k==="no"){ MCLR.ask=null; renderMeetings(); }
  else if(k==="toggle"){ MCLR.open=!MCLR.open; renderMeetings(); }
  else if(k==="restore") mtgRestore({op:"restore",keys:[b.dataset.key]});
  else if(k==="restoreday") mtgRestore({op:"restore_day",day:b.dataset.day}); });
}
export const intakeSeams = { jobLive: v => { jobLive = v; }, nowHM: v => { nowHM = v; } };
