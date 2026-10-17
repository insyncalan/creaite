// @ts-check
/* intake.js (#179, Intake step 1): one queue, one decision per row, fewer buttons.
   Meetings that have ended and files Alan dropped are one list in Review's row shape (title, when, project, transcript state, age) in
   five groups: Ready, Upload files, Waiting, Later, Done recently. A ready row has three actions: Process, Not needed (asks for a reason)
   and Later; a waiting row has only Not needed. Process all ready (n) is the one bulk button. Process loads the transcript first (the
   old Load into inbox is that first step now), then runs the same processing as before, in the background: progress is on the row and
   ask creaite does not open by itself. Organiser and Where sit under Details. Keys: arrows move, Enter processes, N Not needed, H Later.
   The engine, /api/transcripts/* , /api/inbox/* and the clear route (/api/intake/clear) are unchanged.
   History: moved from script/ by dev/tools/convert_area.py (BL-231), rewritten for #179. */
import { openDialog } from "./components/Dialog.jsx";
import { openMenu } from "./components/Menu.jsx";
import { askLive, askStream, mdView, runAsk, setRunning } from "./ask.js";
import { P } from "./core/data.js";
import { $, $$, html, ibtn, ic, putHTML, raw } from "./core/dom.js";
import { addEl } from "./core/fields.js";
import { MSKEL } from "./core/motion.js";
import { anim, D, days, fd, fdText, store, TODAY } from "./core/page.js";
import { go } from "./core/nav.js";
import { api, OLDSERVER, oneLine, reloadData, snack, viaServer, writeSettings } from "./core/server.js";
import { shared } from "./core/state.js";
import { setRailCount } from "./stores/rail.js";
export const INSEL=new Set(); export let INRUN=[];
export const kb=n=>n>1048576?`${(n/1048576).toFixed(1)} MB`:`${Math.max(1,Math.round(n/1024))} KB`;
/* ======================= files you dropped ======================= */
/* BL-137: Upload files lists only files that were uploaded. A file Calendar import loaded is known by its recorded event ID (`f.event`),
   never by its name; it is a Details item on its meeting's row (Preview, Remove). */
export const uploadedFiles=()=>(D.inbox||[]).filter(f=>f.uploaded!==false&&!f.event);
export async function addInboxFiles(files){ if(!viaServer()){ snack("Adding files needs the live server"); return; } let added=0;
  for(const f of files){ const ext=(f.name.match(/\.[^.]+$/)||[""])[0].toLowerCase();
    if(![".vtt",".docx",".txt",".md",".pdf"].includes(ext)){ snack(`${f.name}: only .vtt, .docx, .txt, .md or .pdf`); continue; }
    if(f.size>25*1048576){ snack(`${f.name} is over 25 MB`); continue; }
    const data=await new Promise((res,rej)=>{ const fr=new FileReader(); fr.onload=()=>res(String(fr.result).split(",")[1]||""); fr.onerror=()=>rej(fr.error); fr.readAsDataURL(f); });
    const r=await api("/api/inbox/upload",{name:f.name,data}); if(!r.ok){ if(r.message===OLDSERVER){ snack(OLDSERVER); return; } snack(`${f.name}: ${oneLine(r.message)}`); continue; }
    added++; (D.inbox=D.inbox||[]).push({name:r.name,path:r.path,ext:ext.slice(1),size:f.size,date:TODAY,p:null,state:"new",uploaded:true}); }
  if(added){ snack(`${added} file${added===1?"":"s"} added to Intake`); await reloadData(); renderInbox(); } }
/** Process the files in INSEL, in the background: the row shows it, the ask creaite panel is left as it was */
export async function processInbox(){ const paths=[...INSEL]; if(!paths.length||shared.RUN) return; if(!viaServer()){ snack("Processing needs the live server"); return; }
  INRUN=paths; INSEL.clear(); renderInbox(); addEl("msg u",html`${`Process ${paths.length} file${paths.length===1?"":"s"} from Intake`}`);
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
/* ======================= meetings ======================= */
export const MTG=()=>(D.meetings&&D.meetings.rows)||[], MSEL=new Set(), MRUN={};
/* A meeting that hasn't ended can't have a transcript yet, so it isn't in the queue until it ends (Alan, 2026-10-09). Worked out in the
   page, so a meeting joins the queue on its own once its end time passes. */
export let nowHM = function(){ const n=new Date(); return `${String(n.getHours()).padStart(2,"0")}:${String(n.getMinutes()).padStart(2,"0")}`; };   /* a function, so tests can set the clock */
export const mtgLater=m=>m.day>TODAY||(m.day===TODAY&&(m.end||m.start||"")>nowHM());
export const mtgCanPick=m=>!!m.id&&!m.processed&&!m.draft&&!mtgLater(m)&&MRUN[m.id]!=="processing";
export const TXLABEL={available:"Transcript available",not_transcribed:"Not transcribed",none:"No transcript",no_access:"No access"};
export const mtgHasTx=m=>m.transcript==="available"&&!m.processed&&!m.draft;
export const mtgCheckable=m=>!!m.id&&m.teams&&!mtgLater(m)&&!m.processed&&m.transcript!=="none";
export const TXWHY={none:"No transcript for this meeting",not_transcribed:"Not transcribed yet",no_access:"No access to the transcript"};
export const mtgSkip=m=>m.loaded?"":TXWHY[m.transcript]||(!m.transcript&&!m.teams?"Not a Teams meeting, so there is no transcript to load":"");
/** a stable key for a meeting: the one Clear day and the saved Later list use */
export const rowKey=m=>m.key||m.id||`${m.day}|${m.start}|${m.title}`;
export const mtgBusy=()=>!!shared.RUN||(typeof shared.BUSY!=="undefined"&&shared.BUSY);
/* ----- Later: set aside in this browser (like other per-person view settings), not the cleared record. It comes back to Ready by
   itself when a transcript arrives for a meeting that had none when it was set aside, or with "Back to Ready" ----- */
const LATERK="creaite-intake-later", REASONK="creaite-intake-reasons";
export const laterGet=()=>/** @type {Record<string,string>} */(store.get(LATERK,{}));
const laterSet=/** @param {Record<string,string>} v */v=>store.set(LATERK,v);
export function setLater(k,st){ const L=laterGet(); L[k]=st||""; laterSet(L); }
export function unLater(k){ const L=laterGet(); delete L[k]; laterSet(L); }
const isLater=/** @param {string} k @param {any} m */(k,m)=>{ const L=laterGet(); if(!(k in L)) return false;
  if(m&&m.transcript==="available"&&L[k]!=="available"){ unLater(k); return false; } return true; };
/* ----- the queue: every meeting that has ended and every file you dropped, in its group ----- */
/** @typedef {{kind:"m"|"f", k:string, m?:any, f?:any, i?:number, title:string, day:string}} IRow */
export function intakeRows(){ const g=/** @type {{ready:IRow[],files:IRow[],waiting:IRow[],later:IRow[],done:IRow[]}} */({ready:[],files:[],waiting:[],later:[],done:[]});
  MTG().forEach((m,i)=>{ if(mtgLater(m)) return; const r=MRUN[m.id], k=rowKey(m), it=/** @type {IRow} */({kind:"m",k,m,i,title:m.title,day:m.day});
    if(m.processed||m.draft||r==="draft"){ g.done.push(it); return; }
    if(r==="loading"||r==="processing"||r==="checking"){ g.ready.push(it); return; }
    if(isLater(k,m)){ g.later.push(it); return; }
    (!m.private&&!!m.id&&(m.transcript==="available"||!!m.loaded)?g.ready:g.waiting).push(it); });
  uploadedFiles().forEach(f=>{ const it=/** @type {IRow} */({kind:"f",k:f.path,f,title:f.name,day:f.date});
    if(f.state==="draft"||f.state==="processed"){ g.done.push(it); return; }
    if(INRUN.includes(f.path)){ g.files.push(it); return; }
    if(f.state==="new"&&isLater(f.path,null)) g.later.push(it); else g.files.push(it); });
  g.done.sort((a,b)=>String(b.day).localeCompare(String(a.day)));
  return g; }
const running=/** @param {IRow} r */r=>r.kind==="m"?["loading","processing","checking"].includes(MRUN[r.m.id]):INRUN.includes(r.f.path);
/** what Process all ready covers, and what the badge and Today count: ready meetings plus files, not those already running */
export function readyList(){ const g=intakeRows(); return [...g.ready,...g.files].filter(r=>!running(r)&&(r.kind==="m"||r.f.state==="new")); }
export const readyCount=()=>readyList().length;
export function inboxBadge(){ const n=readyCount(); setRailCount("inbox",n,`${n} ready in Intake`); }   /* BL-70: Intake; ids and the inbox/ folder keep their names */
/* ----- the rows ----- */
const ageDays=/** @param {string} d */d=>d?Math.max(0,-days(d.slice(0,10))):0;
const ageText=/** @param {number} n */n=>n<=0?"today":n===1?"1 day":`${n} days`;
export const INDET=new Set(); export let INCUR="";
const org=m=>m.organiser===true?"You":m.organiser?m.organiser:"Not known";
const projSel=(m,i)=>html`<select class="mtgp" data-mi="${i}" aria-label="Project for ${m.title}"><option value="" ${raw(!m.p?"selected":"")}>Not sure</option>${P.map(p=>html`<option value="${p.code}" ${raw(m.p===p.code?"selected":"")}>${p.name}</option>`)}<option value="_portfolio" ${raw(m.p==="_portfolio"?"selected":"")}>Portfolio</option></select>`;
const MTGI=ic("video",{size:14,w:2});   /* BL-158 */
const dis=on=>raw(on?"disabled":"");
function rowState(r){ if(r.kind==="f"){ const f=r.f; if(INRUN.includes(f.path)) return html`<span class="spin" aria-hidden="true"></span> Processing…`;
    if(f.state==="draft") return html`Draft ready in Review`; if(f.state==="processed") return html`Already processed`; return ""; }
  const m=r.m, x=MRUN[m.id];
  if(x==="checking") return html`<span class="spin" aria-hidden="true"></span> Checking the transcript…`;
  if(x==="loading") return html`<span class="spin" aria-hidden="true"></span> Loading the transcript…`;
  if(x==="processing") return html`<span class="spin" aria-hidden="true"></span> Processing…`;
  if(m.processed) return html`Already processed ${fd(m.processed)}`;
  if(m.draft||x==="draft") return html`Draft ready in Review`;
  if(x&&x.startsWith("skipped:")) return html`<span class="tag">Skipped</span> ${x.slice(8)}`;
  if(x&&x.startsWith("failed:")) return html`<span class="tag warn">Couldn't</span> ${x.slice(7)}`;
  return ""; }
function rowChip(r,grp){ if(grp==="done") return ""; if(r.kind==="f") return html`<span class="inchip">Uploaded file</span>`;
  const m=r.m; if(grp==="waiting") return html`<span class="inchip warn">Waiting for transcript</span> <span class="sub">${m.private?"Private":!m.id?"Refresh to pick this meeting":m.transcript?TXLABEL[m.transcript]:m.teams?"Not checked yet":"Not a Teams meeting"}</span>`;
  return html`<span class="inchip">Transcript ready</span>`; }
function details(r){ if(!INDET.has(r.k)) return "";
  if(r.kind==="f"){ const f=r.f, st=INRUN.includes(f.path); return html`<div class="indet"><span>${String(f.ext||"").toUpperCase()} · ${kb(f.size)} · added ${fd(f.date)}</span>${raw(ibtn("eye","Preview",'data-inprev aria-haspopup="dialog"',"sm"))}${raw(ibtn("trash","Remove from Intake",`data-inrm ${st?"disabled":""}`,"sm no"))}</div>`; }
  const m=r.m, i=r.i, loadedAct=m.loaded?html` <button type="button" class="linkbtn" data-mprev="${i}">Preview transcript</button>${!(m.processed||m.draft||MRUN[m.id]==="processing")&&html` <button type="button" class="linkbtn" data-mrm="${i}">Remove transcript</button>`}`:"";
  const chk=mtgCheckable(m)?html` <button type="button" class="linkbtn mtgchk" data-chk="${i}" ${dis(!viaServer())}>${m.transcript?"Check again":"Check"}</button>`:"";
  return html`<div class="indet"><span>Organiser: ${org(m)}</span><span>Where: ${m.teams?html`<span class="mtgteams">${raw(MTGI)} Teams</span>`:"In person"}</span>${m.transcript_checked?html`<span class="sub">checked ${fdText(m.transcript_checked)}</span>`:""}${loadedAct}${chk}</div>`; }
function rowActs(r,grp){ const live=viaServer(), busy=mtgBusy(), k=r.k, run=running(r);
  if(grp==="done") return (r.kind==="m"?(r.m.draft||MRUN[r.m.id]==="draft"):r.f.state==="draft")?html`<button type="button" class="btn" data-ia="review">Open Review</button>`:"";
  if(run) return html`<button type="button" class="btn" disabled>Processing</button>`;
  const not=html`<button type="button" class="btn" data-ia="not" aria-haspopup="menu" aria-expanded="false" ${dis(!live||(r.kind==="m"&&MRUN[r.m.id]==="processing"))}>Not needed</button>`;
  if(grp==="waiting") return not;
  if(grp==="later") return html`<button type="button" class="btn" data-ia="unlater">Back to Ready</button>${not}`;
  return html`<button type="button" class="btn primary" data-ia="process" ${dis(!live||busy)}>Process</button>${not}<button type="button" class="btn" data-ia="later">Later</button>`; }
function rowHTML(r,grp){ const m=r.m, f=r.f, day=r.kind==="m"?m.day:f.date, n=ageDays(day), old=n>=3&&grp!=="done", run=running(r), st=rowState(r);
  const when=r.kind==="m"?html`${new Date(day).toLocaleDateString("en-GB",{weekday:"short"})} ${fd(day)}, ${m.start}–${m.end}`:html`Dropped ${fd(day)}`;
  const proj=r.kind==="m"?(m.private?html`<span class="sub">Private</span>`:projSel(m,r.i)):(f.p?html`${(P.find(p=>p.code===f.p)||{name:f.p}).name}`:html`<span class="sub">Not sure</span>`);
  const attr=r.kind==="m"?html`data-mid="${m.id||""}" data-mi="${r.i}"`:html`data-inf="${f.path}"`;
  return html`<div class="inrow${r.k===INCUR?" sel":""}${run?" run":""}${grp==="done"?" done":""}" role="listitem" data-ik="${r.k}" data-g="${grp}" ${attr}><div class="inmain"><div class="int">${r.title}</div><div class="inm"><span>${when}</span><span>${proj}</span>${rowChip(r,grp)}<button type="button" class="btn quiet indtb" data-ia="det" aria-expanded="${String(INDET.has(r.k))}">Details</button></div></div><div class="inact"><span class="inage${old?" old":""}">${ageText(n)}</span>${rowActs(r,grp)}</div>${st?html`<div class="instate" role="status">${st}</div>`:""}${run?html`<div class="inprog" aria-hidden="true"><i></i></div>`:""}${details(r)}</div>`; }
const inGrpHead=(name,count)=>html`<div class="ingrp"><h2>${name}</h2><span class="sub">${count}</span></div>`;
function dropzone(){ return html`<div class="dropzone indrop" id="inboxDrop" tabindex="0" role="button" aria-label="Add files to Intake"><button class="linkbtn" id="inboxPick" type="button">Choose files</button> or drop them here, anywhere on this page. <span class="sub">.vtt, .docx, .txt, .md or .pdf, up to 25 MB each. Each becomes a row with a project to confirm.</span></div>`; }
/* ----- Cleared (BL-104) and the reason Not needed recorded ----- */
export const MCLR={open:false};
const reasonsGet=()=>/** @type {Record<string,string>} */(store.get(REASONK,{}));
export function clrList(){ const C=(D.meetings||{}).cleared||[]; if(!C.length){ MCLR.open=false; return ""; }
  const days=[...new Set(C.map(m=>m.day))], why=reasonsGet();
  return html`<div class="mtgcleared"><button class="clrlink" data-clr="toggle" aria-expanded="${String(MCLR.open)}">Cleared (${C.length})</button>${MCLR.open&&html`<div class="mtgclrlist">${days.map(d=>html`<div class="clrday"><span>${new Date(d).toLocaleDateString("en-GB",{weekday:"long"})} ${fd(d)}</span><span class="sp"></span><button class="btn mtgclr" data-clr="restoreday" data-day="${d}">Restore day</button></div>${C.filter(m=>m.day===d).map(m=>html`<div class="clrrow"><span class="sub" style="white-space:nowrap">${m.start}–${m.end}</span><span>${m.title}</span>${why[m.key]&&html`<span class="sub">${why[m.key]}</span>`}<span class="sp"></span><button class="btn mtgclr" data-clr="restore" data-key="${m.key}" aria-label="Restore ${m.title}">Restore</button></div>`)}`)}</div>`}</div>`; }
/* ----- the page ----- */
export function renderInbox(){ const mt=D.meetings||{}, g=intakeRows(), live=viaServer(), busy=mtgBusy(), n=readyCount();
  [...MSEL].forEach(id=>{ const m=MTG().find(x=>x.id===id); if(!m||!mtgCanPick(m)) MSEL.delete(id); });
  const all=[...g.ready,...g.files,...g.waiting,...g.later,...g.done]; if(!all.some(r=>r.k===INCUR)) INCUR=(readyList()[0]||all[0]||{k:""}).k;
  $("#mtgRead").textContent=mt.fetched?`Calendar read ${fdText(mt.fetched)}`:"";
  $("#inSub").textContent=`Meetings that have ended and files you dropped. ${n} ready.`;
  const go_=$("#inAll"); go_.textContent=`Process all ready (${n})`; go_.disabled=!n||busy||!live; go_.classList.toggle("off",go_.disabled);
  $("#mtgRefresh").disabled=busy||!live;
  const section=(name,lst,grp)=>lst.length?html`${inGrpHead(name,grp==="done"?String(lst.length):grp==="later"?`${lst.length} set aside`:grp==="waiting"?`${lst.length} no transcript yet`:`${lst.length} with a transcript`)}<div role="list">${lst.map(r=>rowHTML(r,grp))}</div>`:"";
  const nothing=!all.length;
  const empty=!mt.fetched?html`<div class="empty">No calendar yet: it comes in with the sweep. Refresh reads it now.</div>`
    :nothing?html`<div class="empty">Nothing here yet. Meetings appear when they end, and transcripts as they arrive.</div>`
    :!g.ready.length?html`<div class="empty">Nothing ready. A meeting appears here when its transcript arrives.</div>`:"";
  const upN=g.files.length;
  putHTML($("#mtgBody"),html`${section("Ready",g.ready,"ready")}${empty}<div class="ingrp"><h2>Upload files</h2><span class="sub">${upN?`${upN} waiting`:"drop transcripts or minutes anywhere on this page"}</span></div>${dropzone()}<div role="list">${g.files.map(r=>rowHTML(r,"files"))}</div>${section("Waiting",g.waiting,"waiting")}${section("Later",g.later,"later")}${section("Done recently",g.done,"done")}${clrList()}`);
  inboxBadge(); }
export const renderMeetings=renderInbox;
/* ======================= Process: load the transcript, then process, in the background ======================= */
export async function processMeetings(){ const L=MTG().filter(m=>MSEL.has(m.id)); if(!L.length) return;
  if(!viaServer()){ snack("Processing needs the live server"); return; } if(mtgBusy()){ snack("ask creaite is busy; try again when it's finished"); return; }
  MSEL.clear(); const PL=L.length>1?`Processing ${L.length} meetings`:`Processing “${L[0].title}”`;     /* BL-139: what the badge says */
  for(const m of L){ const why=mtgSkip(m); if(why){ MRUN[m.id]="skipped:"+why; renderInbox(); continue; }
    const when=`${fd(m.day)} at ${m.start}`; let now=m;
    if(!m.loaded){ MRUN[m.id]="loading"; renderInbox(); runAsk(addEl("msg u",html`${`Load the transcript of “${m.title}” (${when})`}`));
      shared.RUNLABEL=PL; try{ await jobLive("/api/transcripts/load",{id:m.id}); }catch(e){} delete MRUN[m.id]; await reloadData(); now=MTG().find(x=>x.id===m.id);
      if(!now||!now.loaded){ MRUN[m.id]="skipped:"+(TXWHY[now&&now.transcript]||"No transcript could be loaded"); renderInbox(); continue; } }
    MRUN[m.id]="processing"; renderInbox(); addEl("msg u",html`${`Process the meeting “${m.title}” (${when})`}`); const before=$$("#chLog .msg.a").length;
    shared.RUNLABEL=PL; try{ await askLive(`process ${now.loaded}`,`Process “${m.title}” (${when}) into draft minutes and proposed items`); }catch(e){} await reloadData();
    const after=MTG().find(x=>x.id===m.id), said=[...$$("#chLog .msg.a")].slice(before).map(e=>e.textContent.trim()).filter(Boolean).pop()||"";
    MRUN[m.id]=after&&(after.draft||after.processed)?"draft":`failed:${oneLine(said).split(/(?<=[.!?])\s/)[0].slice(0,140)||"no draft came back"}`; renderInbox(); } }
/** one row */
export async function processRow(r){ if(r.kind==="m"){ MSEL.clear(); MSEL.add(r.m.id); await processMeetings(); } else { INSEL.clear(); INSEL.add(r.f.path); await processInbox(); } }
/** the one bulk button: every ready meeting, then every file, one run after another */
export async function processAllReady(){ const L=readyList(); if(!L.length) return; if(!viaServer()){ snack("Processing needs the live server"); return; } if(mtgBusy()){ snack("ask creaite is busy; try again when it's finished"); return; }
  const ms=L.filter(r=>r.kind==="m"), fs=L.filter(r=>r.kind==="f");
  MSEL.clear(); ms.forEach(r=>MSEL.add(r.m.id)); INSEL.clear(); fs.forEach(r=>INSEL.add(r.f.path));
  if(ms.length) await processMeetings(); if(fs.length) await processInbox(); }
export async function refreshCalendar(){ const body=$("#mtgBody"); let /** @type {any} */ sk=null; const t=setTimeout(()=>{ if(body){ sk=putHTML(document.createElement("div"),MSKEL).firstChild; body.before(sk); } },150);   /* BL-263 */
  try{ if(!viaServer()){ snack("Refreshing needs the live server"); return; } if(mtgBusy()){ snack("ask creaite is busy; try again when it's finished"); return; }
  $("#mtgRead").textContent="Refreshing…"; addEl("msg u","Refresh calendar");
  try{ await askLive("refresh calendar","Refresh the calendar for Intake and Today"); }catch(e){} await reloadData(); renderInbox(); }
  finally{ clearTimeout(t); if(sk){ sk.remove(); anim($("#mtgBody"),[{opacity:0,transform:"translateY(4px)"},{opacity:1,transform:"none"}],{duration:320}); } } }
export async function mtgProject(i,code){ const m=MTG()[i]; if(!m) return; const was=m.p; m.p=code||null; m.how=code?"remembered":"unsure";
  if(m.private||!code){ renderInbox(); return; }             /* a private "Busy" has no series to remember */
  const map={...((D.prep||{}).series||{}),[m.series]:code};
  if(await writeSettings({"prep.series":map})){ /** @type {any} */(D.prep=D.prep||{}).series=map; MTG().forEach(x=>{ if(x.series===m.series&&!x.private){ x.p=code; x.how="remembered"; } });
    Object.values((D.prep||{}).meetings||{}).forEach(x=>{ if(x.series===m.series){ x.p=code; x.how="remembered"; } }); snack("Remembered for this meeting series"); }
  else m.p=was; renderInbox(); }
/* a transcript job (a check or a load) goes through the run engine like a question, but isn't a chat; the server writes the status and the files */
export let jobLive = async function(url,body){ if(!shared.RUNLABEL) shared.RUNLABEL=/load/.test(url)?"Loading a transcript":"Checking a transcript"; const id=`r-${Date.now().toString(36)}-${Math.random().toString(36).slice(2,8)}`, ctl=new AbortController(); shared.RUN={id,ctl}; setRunning(true);
  try{ await askStream(url,{...body,run:id},true,ctl,undefined,true); } finally{ shared.RUN=null; setRunning(false); } };   /* BL-326: drawn plainly (steps and the closure) */
export async function checkMeeting(m){ if(!viaServer()){ snack("Checking needs the live server"); return; } if(mtgBusy()){ snack("ask creaite is busy; try again when it's finished"); return; }
  MRUN[m.id]="checking"; renderInbox(); runAsk(addEl("msg u",html`${`Check the transcript of “${m.title}” (${fd(m.day)} at ${m.start})`}`));
  try{ await jobLive("/api/transcripts/check",{id:m.id}); }catch(e){} delete MRUN[m.id]; await reloadData(); renderInbox(); }
/* BL-137: a loaded transcript and its chat are previewed and removed from the meeting's row (Remove only before it is processed; one Undo) */
export async function removeLoaded(m){ if(!viaServer()){ snack("Removing needs the live server"); return; } const files=(D.inbox||[]).filter(f=>f.event===m.id), kept=[];
  for(const f of files){ const r=await api("/api/inbox/remove",{path:f.path}); if(!r.ok){ snack(r.message===OLDSERVER?OLDSERVER:oneLine(r.message)); break; } kept.push(r.kept); }
  if(!kept.length) return; await reloadData(); renderInbox();
  snack(`Removed the loaded transcript of “${m.title}” (kept in backups)`,async()=>{ for(const k of kept) await api("/api/inbox/restore",{kept:k}); await reloadData(); renderInbox(); snack("Back in Intake"); }); }
/* ======================= Not needed: the reason, then Clear (BL-104) =======================
   Cleared is not processed: nothing is written to processed.txt or the tracker. The live server saves the set-aside in
   system/staging/intake-cleared.json and is unchanged (#179 uses the brief's fallback): the reason is kept in this browser and shown
   in the Cleared list, and on the row's `skipped:<reason>` state until the page reloads. */
export const NOT_REASONS=["Informal chat","No decisions","Duplicate of another meeting","Other"];
export const clrKeys=ms=>ms.map(m=>({key:m.key,day:m.day,start:m.start,title:m.title}));
export async function mtgClear(ms,reason){ ms=ms.filter(m=>MRUN[m.id]!=="processing"); if(!ms.length) return;
  if(!viaServer()){ snack("Clearing needs the live server"); return; }
  const r=await api("/api/intake/clear",{op:"clear",items:clrKeys(ms)});
  if(!r.ok){ snack(oneLine(r.message||"Couldn't set those meetings aside")); renderInbox(); return; }
  const keys=ms.map(m=>m.key), W=reasonsGet(); if(reason) keys.forEach(k=>{ W[k]=reason; }); store.set(REASONK,W);
  await reloadData(); renderInbox();
  snack(`Not needed${reason?`: ${reason}`:""} (${ms.length} meeting${ms.length===1?"":"s"})`,()=>mtgRestore({op:"restore",keys})); }
export async function mtgRestore(body){ const r=await api("/api/intake/clear",body);
  if(!r.ok){ snack(oneLine(r.message||"Couldn't restore")); return; } await reloadData(); renderInbox(); snack(`Restored ${r.count} meeting${r.count===1?"":"s"}`); }
/** the reason menu for a row's Not needed; picking one sets it aside */
export function notNeededMenu(r,anchor){ if(!viaServer()) return;
  openMenu(anchor,{label:"Not needed because",id:"inNotMenu",items:[{id:"hd",head:"Not needed because"},...NOT_REASONS.map(x=>({id:x,name:x}))],
    onPick:async why=>{ if(r.kind==="m") await mtgClear([r.m],why); else { await removeInbox(r.f.path); } } }); }
/* ======================= keys: as in Review (arrows or J K move, Enter does the main thing, N and H as the buttons) ======================= */
const cursorRows=()=>$$("#mtgBody [data-ik]").filter(el=>el.dataset.g!=="done");
function setCursor(k){ INCUR=k; $$("#mtgBody .inrow").forEach(el=>el.classList.toggle("sel",el.dataset.ik===k)); const el=$$("#mtgBody .inrow").find(x=>x.dataset.ik===k); if(el) el.scrollIntoView({block:"nearest"}); }
const rowOf=k=>{ const g=intakeRows(); return [...g.ready,...g.files,...g.waiting,...g.later].find(r=>r.k===k); };
/** called from core/keys.js while Intake is open; true when the key was used */
export function intakeKey(/** @type {KeyboardEvent} */ e){ if(shared.VIEW!=="inbox"||e.shiftKey||e.metaKey||e.ctrlKey||e.altKey) return false;
  const t=/** @type {HTMLElement} */(e.target); if(t&&t.closest&&t.closest("[role=menu],dialog,.ddmenu")) return false;
  const els=cursorRows(); if(!els.length) return false; const keys=els.map(x=>x.dataset.ik), i=Math.max(0,keys.indexOf(INCUR));
  if(e.key==="ArrowDown"||e.key==="j"){ e.preventDefault(); setCursor(keys[Math.min(i+1,keys.length-1)]); return true; }
  if(e.key==="ArrowUp"||e.key==="k"){ e.preventDefault(); setCursor(keys[Math.max(i-1,0)]); return true; }
  const r=rowOf(keys[i]); if(!r) return false; const grp=els[i].dataset.g, ready=grp==="ready"||grp==="files";
  if(e.key==="Enter"){ if(t&&t.closest&&t.closest("button,a,input,select,textarea")) return false; if(!ready||running(r)||!viaServer()||mtgBusy()) return false; e.preventDefault(); processRow(r); return true; }
  if(e.key==="n"||e.key==="N"){ if(running(r)) return false; e.preventDefault(); const b=/** @type {HTMLElement|null} */(els[i].querySelector('[data-ia="not"]')); if(b&&!(/** @type {HTMLButtonElement} */(b)).disabled) notNeededMenu(r,b); return true; }
  if(e.key==="h"||e.key==="H"){ if(!ready||running(r)) return false; e.preventDefault(); setLater(r.k,r.kind==="m"?r.m.transcript:""); renderInbox(); return true; }
  return false; }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootIntake(){
const V=$("#v-inbox");
$("#inAll").onclick=processAllReady;
$("#mtgRefresh").onclick=refreshCalendar;
$("#inboxFile").onchange=e=>{ addInboxFiles([...e.target.files]); e.target.value=""; };
$("#inPrevOpen").onclick=async()=>{ const o=await api("/api/open",{path:$("#inPrev").dataset.path}); if(!o.ok) snack(oneLine(o.message)); };
/* a drop works anywhere on the page */
const dropOn=on=>V.classList.toggle("dragover",on);
V.addEventListener("dragover",e=>{ if([...(e.dataTransfer?.types||[])].includes("Files")){ e.preventDefault(); dropOn(true); } });
V.addEventListener("dragleave",e=>{ if(!e.relatedTarget||!V.contains(/** @type {Node} */(e.relatedTarget))) dropOn(false); });
V.addEventListener("drop",e=>{ dropOn(false); const f=[...(e.dataTransfer?.files||[])]; if(f.length){ e.preventDefault(); addInboxFiles(f); } });
V.addEventListener("keydown",e=>{ if(e.target.id==="inboxDrop"&&(e.key==="Enter"||e.key===" ")){ e.preventDefault(); $("#inboxFile").click(); } });
V.addEventListener("change",e=>{ const el=/** @type {HTMLSelectElement} */(e.target); if(el.matches&&el.matches(".mtgp")) mtgProject(+el.dataset.mi,el.value); });
V.addEventListener("click",e=>{ const t=/** @type {HTMLElement} */(e.target);
  if(t.closest("#inboxPick")){ e.stopPropagation(); $("#inboxFile").click(); return; }
  const rowEl=t.closest(".inrow"), el=rowEl&&/** @type {HTMLElement} */(rowEl);
  const pv=t.closest("[data-mprev]"), rm=t.closest("[data-mrm]"); if(pv||rm){ const m=MTG()[+/** @type {HTMLElement} */(pv||rm).dataset[pv?"mprev":"mrm"]]; if(m&&m.loaded) pv?previewInbox(m.loaded):removeLoaded(m); return; }
  const ck=/** @type {HTMLButtonElement|null} */(t.closest("[data-chk]")); if(ck&&!ck.disabled){ const m=MTG()[+ck.dataset.chk]; if(m) checkMeeting(m); return; }
  if(el&&t.closest("[data-inprev]")){ previewInbox(el.dataset.inf); return; } if(el&&t.closest("[data-inrm]")){ removeInbox(el.dataset.inf); return; }
  const cl=/** @type {HTMLElement|null} */(t.closest("[data-clr]")); if(cl&&!(/** @type {HTMLButtonElement} */(cl)).disabled){ const k=cl.dataset.clr;
    if(k==="toggle"){ MCLR.open=!MCLR.open; renderInbox(); } else if(k==="restore") mtgRestore({op:"restore",keys:[cl.dataset.key]}); else if(k==="restoreday") mtgRestore({op:"restore_day",day:cl.dataset.day}); return; }
  const a=/** @type {HTMLButtonElement|null} */(t.closest("[data-ia]")); if(!a||!el||a.disabled) return;
  const r=rowOf(el.dataset.ik)||intakeRows().done.find(x=>x.k===el.dataset.ik); if(!r) return; INCUR=r.k; const act=a.dataset.ia;
  if(act==="process") processRow(r); else if(act==="not") notNeededMenu(r,a);
  else if(act==="later"){ setLater(r.k,r.kind==="m"?r.m.transcript:""); renderInbox(); }
  else if(act==="unlater"){ unLater(r.k); renderInbox(); }
  else if(act==="det"){ INDET.has(r.k)?INDET.delete(r.k):INDET.add(r.k); renderInbox(); }
  else if(act==="review") go("review"); });
/* the clock moves on: a meeting joins the queue when it ends */
setInterval(()=>{ if(shared.VIEW==="inbox"&&!document.activeElement?.matches?.(".mtgp")) renderInbox(); },60000);
}
export const intakeSeams = { jobLive: v => { jobLive = v; }, nowHM: v => { nowHM = v; } };
