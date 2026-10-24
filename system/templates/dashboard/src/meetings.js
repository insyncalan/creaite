// @ts-check
/* meetings.js (BL-231 step 2b), moved from script/ by dev/tools/convert_area.py: 0084-prep-updates-bl-65.js, 0125-bl-126-sprint-prep-files.js, 0126-after-bl-126.js, 0143-decisions-and-schema-bl-53-sprint-5.js, 0144-bl-210-sprint-decisions-needed.js, 0145-steering-one-pager-bl-92-sprint-5.js, 0146-decisions-in-meeting-prep-bl-113.js, 0201-bl-223-sprint-drafts-writing.js, 0206-bl-209-sprint-insight.js.
   Unchanged apart from `export`, `shared.` for the shared state (core/state.js) and the load-time steps, now in
   boot…() functions that src/main.js calls in today's order. */
import { askLive, openChat, rbEnd, rbStart } from "./ask.js";
import { DEC, P, pName } from "./core/data.js";
import { $, $$, esc, html, ibtn, ic, putHTML, raw, writeDoc } from "./core/dom.js";
import { addEl, CALI, DATE_HELP } from "./core/fields.js";
import { go, openWork, pLink } from "./core/nav.js";
import { copied, D, days, DDATE, fd, isMe, MOD, nowStamp, S, store, TODAY, toIso } from "./core/page.js";
import { api, OLDSERVER, oneLine, reloadData, save, snack, viaServer, writeSettings } from "./core/server.js";
import { shared } from "./core/state.js";
import { DE_COLOURS, DE_FONT, draftAsk, DRAFTFEATURES, draftSrcHtml, draftStat, draftTextHtml, draftWhyNot, openDraftEmail } from "./drafts.js";
import { drawPanel, openRecord, REC } from "./panel.js";
import { DRAFTKIND, drawPrep, openPrep, prepKey, prepOf, prepTimed, WSIG } from "./projects.js";
import { draftOn } from "./review.js";
import { PERS, SA } from "./settings.js";
import { andList, capped, longDay, plur, projLink, renderToday, tib, tl, tLink } from "./today.js";
import { items, kOfId, recordFromBoard, rows } from "./work.js";
import { invitees } from "./components/prep/PrepHead.jsx";
import { prepNow, prepViewHref } from "./stores/prepPopup.js";
import { prepHref } from "./stores/prep.js";
/* ===== Prep updates (BL-65) ===== */
/* An update cx-minutes proposes to an open item (from what the meeting said) sits under the meeting's minutes like its new
   items, labelled "Update", with the item's ID and text and each changed field as before → after (revDetail), and what was
   said. One that closes the item is never covered by "Approve routine" or the minutes' group approve (review.py's
   individual_only marks it indiv), except a promise marked Done or Dropped without a probably-done guess (BL-125 A, decision 6). */

/* ===== BL-126 (sprint-prep-files) ===== */
/* Recent reports in the Prep popup: each project's latest weekly report, client report and steering one-pager, opened the way the
   Files page opens a file (data-openfile → /api/open). An online-only OneDrive file is shown as unavailable, never linked. */
export function prepReports(code,all,sec,pc){ const RP=(D.prep||{}).reports||{}, list=all?P.flatMap(p=>RP[p.code]||[]):(RP[code]||[]);
  return sec("Recent reports",list,x=>`<div>${pc(x)}${esc(x.kind)}${x.kind==="Client report"?' <span class="tag">for the client</span>':""} <span class="sub">${x.date?fd(x.date)+" · ":""}${x.online?`${esc(x.name)} — online-only, not available`:`<a href="#" data-openfile="${esc(x.path)}">${esc(x.name)}</a>`}</span></div>`,"No weekly report, client report or steering one-pager filed yet.",""); }
/* A saved prep page links its reports to #openfile=<projects/… path>: open that file once through /api/open (which checks the
   path again: the allowed folders, no .., it must exist) and clear the address. */
export function openFromAddress(){ const m=/^#openfile=(.*)$/.exec(location.hash); if(!m) return false;
  let p=""; try{ p=decodeURIComponent(m[1]); }catch(e){}
  try{ history.replaceState(null,"",location.pathname+location.search); }catch(e){}
  const no=()=>snack("Can't open that file");
  if(!/^(projects|inbox|system\/staging\/drafts)\/.+/.test(p)||p.split("/").includes("..")||!viaServer()){ no(); return true; }
  api("/api/open",{path:p}).then(r=>{ if(!r.ok) no(); }); return true; }
/* ===== end BL-126 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootMeetings0125(){
window.addEventListener("hashchange",()=>{ if(/^#openfile=/.test(location.hash)) openFromAddress(); });
}
/* BL-98 part 2: Prep page. Claude researches the meeting through the live server's run engine (read-only, progress and
   Stop, one run at a time); the server renders one self-contained HTML page from the reply and saves it in the
   project's Agendas folder, and it opens in a new tab. Open last prep page reopens creaite's newest one. */
shared.PREPRUN=null;
/* BL-287, BL-286: the newest prep page creaite saved for a meeting, and when: {path, when} or null. When comes from the day data
   (D.days, BL-293), else from this session's own save, else the date in the file's name. */
export const PREPSAVED={};
export function prepPageOf(e,day){ if(!e) return null; const key=prepKey(e,day), path=(SA().prep_pages||{})[key]; if(!path) return null;
  const dd=(((D.days||{}).days)||[]).find(x=>x.date===(day||TODAY)), mt=dd&&(dd.meetings||[]).find(x=>x.start===e.start&&x.title===e.title), pg=mt&&mt.prep;
  const named=/(\d{4}-\d{2}-\d{2}) Prep/.exec(path);
  return {path,key,when:pg&&pg.page===path&&pg.page_at_shown?pg.page_at_shown:PREPSAVED[key]||(named?fd(named[1]):"")}; }
export function prepPgStat(html){ putHtml($("#prepPgStat"),html||""); }
export function prepShow(w,html,path){ if(w&&!w.closed){ w.document.open(); writeDoc(w,raw(html)); w.document.close(); return; }
  const u=URL.createObjectURL(new Blob([html],{type:"text/html"})); prepPgStat(`<a href="${u}" target="_blank" rel="noopener">Open the prep page</a> · ${esc(path)}`); }
/* BL-286 D: `o.quiet` is Refresh research on the in-app prep page (#prep=…): no new tab; o.status(text) follows the run and
   o.done(result) gets the saved page, so the page reloads its view. */
export async function prepPage(given,o){ const was=shared.PREPRUN; o=o||{}; shared.RBOUT=""; if(!was&&viaServer()) rbStart("Making the prep page"); try{
  if(!viaServer()){ snack("The Prep page needs creaite to be running"); return; } if(shared.PREPRUN){ snack("A prep page is already being made"); return; }
  const asked=typeof given==="string"&&!!given;     /* BL-307: a meeting named by ask creaite, from its finished run's card */
  if(shared.BUSY&&!asked){ snack("ask creaite is busy; try again when it's finished"); return; }
  const key=asked?given:prepKey(shared.PREPEV,shared.PREPDAY);
  if(SA().agendas_shared&&!store.get("creaite-prep-shared-ok",false)){
    if(!confirm("The page is saved in the project's Agendas folder, in OneDrive, where other people may see it if the folder is shared. It's marked Internal. Save it there?")) return;
    store.set("creaite-prep-shared-ok",true); }
  const id=`p-${Date.now().toString(36)}-${Math.random().toString(36).slice(2,8)}`, ctl=new AbortController(); shared.PREPRUN={id,ctl};
  const w=o.quiet?null:window.open("","_blank");     /* opened now, while the click counts; filled when the page is ready */
  if(w) writeDoc(w,html`<!doctype html><title>Preparing…</title><p style="font:15px -apple-system,sans-serif;padding:24px">creaite is preparing the page; it opens here when it’s ready.</p>`);
  let steps=0, stopped=false, res, failed="";
  const show=()=>{ prepPgStat(`<span class="spin"></span> Researching${steps?` · ${steps} step${steps===1?"":"s"}`:""} <button class="mini" data-prepstop>Stop</button>`); if(o.status) o.status(`Researching${steps?` · ${steps} step${steps===1?"":"s"}`:""}`); }; show();
  const end=msg=>{ shared.RBOUT=/^Stopped/.test(msg||"")?"stopped":msg?"failed":""; shared.PREPRUN=null; prepPgStat(""); if(o.status) o.status(""); if(w&&!w.closed) w.close(); if(msg) snack(msg); };
  try{ res=await fetch("/api/prep/page",{method:"POST",signal:ctl.signal,headers:{"Content-Type":"application/json","X-Creaite-Token":D.token},body:JSON.stringify({key,run:id})}); }catch(e){ return end("creaite isn't reachable"); }
  if(!res.ok||!res.body||(res.headers.get("Content-Type")||"").includes("json")){ const j=await res.json().catch(()=>({})); return end(res.status===404&&j.message==="Not found"?OLDSERVER:oneLine(j.message)||"Couldn't start the prep page"); }
  const rd=res.body.getReader(), dec=new TextDecoder(); let buf="";
  for(;;){ let c; try{ c=await rd.read(); }catch(e){ stopped=true; break; } if(c.done) break; buf+=dec.decode(c.value,{stream:true}); let i;
    while((i=buf.indexOf("\n\n"))>=0){ const ch=buf.slice(0,i); buf=buf.slice(i+2); if(!ch.startsWith("data: ")) continue; let ev; try{ ev=JSON.parse(ch.slice(6)); }catch(e){ continue; }
      if(ev.type==="step"){ steps++; show(); } else if(ev.type==="stopped") stopped=true; else if(ev.type==="error") failed=ev.message; } }
  api("/api/ask/ack",{run:id}).catch(()=>{});   /* BL-326: this page saw the run end, so ask creaite doesn't draw it again on the next load */
  if(stopped) return end("Stopped; no page was written");
  if(failed) return end(failed);
  prepPgStat('<span class="spin"></span> Writing the page…'); if(o.status) o.status("Writing the page…");
  const r=await api("/api/prep/build",{run:id}); if(!r.ok) return end(r.message||"The page wasn't written");
  shared.PREPRUN=null; (SA().prep_pages||(SA().prep_pages={}))[key]=r.path; PREPSAVED[key]=`${fd(TODAY)} ${nowStamp().slice(11)}`; if(o.quiet){ if(o.status) o.status(""); if(o.done) o.done(r); } else prepShow(w,r.html,r.path);
  if(shared.VIEW==="today") renderToday();   /* BL-287, BL-293: the Open icon appears at once (the day band and the Week ahead) */
  if($("#prepDlg")&&$("#prepDlg").open&&prepKey(shared.PREPEV,shared.PREPDAY)===key) drawPrep(); snack(`Prep page saved: ${r.path}`); }
  finally{ rbEnd(shared.RBOUT||"done"); shared.RBOUT=""; } }
export async function prepOpen(path){ if(!viaServer()){ snack("Opening a prep page needs creaite to be running"); return; } const w=window.open("","_blank");
  const r=await api("/api/prep/open",{path}); if(!r.ok){ if(w) w.close(); snack(r.message||"Couldn't open it"); return; } prepShow(w,r.html,r.path); }
export async function choosePrep(code){ const m=prepOf(shared.PREPEV); if(!m||!code) return; const map={...((D.prep||{}).series||{}),[m.series]:code};
  const kept=await writeSettings({"prep.series":map}); if(kept) D.prep.series=map;
  Object.values(D.prep.meetings).forEach(x=>{ if(x.series===m.series){ x.p=code; x.how=kept?"remembered":"chosen"; } }); drawPrep(); if(kept) snack("Remembered for this series"); }
   /* those handlers stop the click early */

/* BL-54's Quick capture form (FR-71) is replaced by the capture drawer (BL-301 C, components/notes/CaptureDrawer.jsx): ⌘⇧N,
   ⌘K "New note" and "note: …" in ask creaite save a note in the project's notes folder. Old quick notes stay in minutes/. */
 
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootMeetings0126(){
document.addEventListener("click",e=>{ if(e.target.closest("[data-preppage]")){ e.preventDefault(); prepPage(); return; }
  const o=e.target.closest("[data-prepopen]"); if(o){ e.preventDefault(); prepOpen(o.dataset.prepopen); return; }
  if(e.target.closest("[data-prepstop]")&&shared.PREPRUN){ api("/api/ask/stop",{run:shared.PREPRUN.id}).then(r=>{ if(!r.ok&&shared.PREPRUN) shared.PREPRUN.ctl.abort(); }); } });
document.addEventListener("click",e=>{ const b=e.target.closest("[data-prep]"); if(b) openPrep(prepTimed()[+b.dataset.prep],TODAY); });
document.addEventListener("click",e=>{ const g=e.target.closest("[data-prepgo]"); if(!g) return; e.preventDefault();   /* BL-287 */
  if(g.getAttribute("aria-disabled")==="true"){ snack("Opening a prep page needs creaite to be running"); return; } location.hash=prepViewHref(g.dataset.prepgo,g.dataset.prepgoday); });
/* #111: a later day's meeting (Week ahead) opens the Prep peek, then the prep page, through data-prepgo above (the old data-prepday popup is gone) */
document.addEventListener("click",e=>{ if(e.target.closest("#prepDlg [data-nav], #prepDlg [data-proj]")) $("#prepDlg").close(); },true);
}
/* ===== Decisions and schema (BL-53, sprint 5) ===== */
/* A decision can be Pending before it is made: it has a decision maker (who it is asked of), a needed-by date (`due` here) and no
   date until it is made; it keeps its D-number when it is made. The form, the Work list, Today, the project page, a person's
   page and the Draft email show it; the early warning and the revisit reminder come from build_dashboard.py. The lines above
   are extended by wrapping their functions, like the Insight section. */
export const decPending=()=>DEC.filter(d=>d.st==="Pending");
export const decLate=d=>d.st==="Pending"&&!!d.due&&d.due<TODAY;
// @ts-expect-error TS2362: true and false subtract as 1 and 0 (late decisions rank first)
export const decRank=(a,b)=>(decLate(b)-decLate(a))||(a.due||"9999").localeCompare(b.due||"9999")||a.id.localeCompare(b.id);
export const decRevisit=()=>DEC.filter(d=>d.st==="Made"&&/^\d{4}-\d{2}-\d{2}$/.test(d.revisit||"")&&d.revisit<=TODAY);
export const decShort=(t,n)=>t.length>n?t.slice(0,n-1)+"…":t;
export const decLateWords=d=>`${-days(d.due)} day${-days(d.due)===1?"":"s"} late`;
export const decAsked=d=>d.by?(isMe(d.by)?"asked of you":`from ${esc(d.by)}`):"no one asked yet";
export function decisionFields(x,projOpts){ const isNew=shared.CUR&&shared.CUR.mode==="new", others=DEC.filter(d=>d.p===x.p&&d.id!==x.id).map(d=>[d.id,`${d.id} · ${decShort(d.t,60)}`]);
  return [["t","Decision","area"],["p","Project","sel",projOpts],["st","Status","sel",isNew?["Pending","Made"]:["Pending","Made","Withdrawn"]],
    ["by","Decision maker (asked of, while pending)","owner"],["due","Needed by","date"],["date","Date made","date"],
    ...(isNew?[["srcIn","Source (where it was raised or decided)","area"]]:[]),
    ["#","Reasoning"],["why","Reasoning","area"],["opts","Options considered","area"],["revisit","Revisit (a date, or a trigger in words)","text"],
    ["replaces","Replaces",shared.EDITING?"sel":"dref",shared.EDITING?[["","None"],...others]:undefined],...(!shared.EDITING&&x.rby?[["rby","Replaced by","dref"]]:[]),
    ["#","Client messaging"],["client","Client-visible","check"],["cmd","Client messaging","cmd"]]; }
export function decisionCheck(f,orig,bad){ const st=f.st||(orig&&orig.st)||"Made";
  if(st==="Made"&&!(("date" in f)?f.date:orig&&orig.date)) return bad("date","A decision that is made needs the date it was made.");
  if(orig&&orig.st==="Made"&&st==="Pending") return bad("st","A decision that has been made can't go back to pending; record a new one that replaces it.");
  if(f.replaces&&orig&&f.replaces===orig.id) return bad("replaces","A decision can't replace itself.");
  return null; }
/* BL-176 (sprint-peek): Record the decision and Withdraw were the read view's buttons; in the peek, Status (or More › Mark as made) does both */
export async function withdrawDecision(x){ const before=x.st, id=x.id;
  if(await save(`${id} withdrawn`,[{op:"update",table:"decisions",id,changes:{status:"Withdrawn"},based_on:x.updated_at}],null,()=>{ x.st="Withdrawn"; x.upd_at=nowStamp(); },()=>{ x.st=before; })){ if(shared.CUR&&shared.CUR.id===id){ shared.CUR.pre=null; drawPanel(); } } }
   /* BL-190: through openWork, so no earlier filter is left and the list holds exactly the decisions counted */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootMeetings0143(){
/* Work › Decisions: a Needed by cell that says when it is late (BL-159: "Decision needed" is now Ask for a decision, in the New menu) */
/* Today › Needs attention: one line for the decisions waiting, with the first few linked */
document.addEventListener("click",e=>{ const a=e.target.closest("[data-decpending]"); if(!a) return; e.preventDefault(); openWork("","decisions","pending"); });
/* the project page: a Decisions needed card (and the decisions whose revisit date has come) */
/* a person's page: the decisions we're waiting on from them; Draft email then offers them too */
/* Settings › Early warnings: the pending-decision signal beside the others */
WSIG.push(["decision_overdue","Pending decision past its needed-by date","days","Late by at least (days)"]);
}
/* ===== BL-210 (sprint-decisions-needed) ===== Decisions needed: what waits on a named person, how long, and what slips.
   One list and one row, drawn on Today (a band ahead of Needs attention), on a project page (the Decisions needed card) and in
   a steering meeting's Prep. The list: pending decisions with a decision maker and a needed-by date; yours first (marked Yours,
   with Decide, which opens Record the decision), then by how late or how soon. Each row: the decision, the project, who it waits
   on, days waiting (since it entered the tracker, D.decisions[].since), when it is needed, and what slips if it stays open: the
   open items and milestones it blocks (links, D.decisions[].slips, and the milestone a blocked item belongs to); with no link
   recorded, nothing is said rather than a guess. Chase drafts an email to the decision maker on BL-224's builder (chase mode
   once it is late, the update request before), with only this decision ticked; nothing is sent. Internal; reads only. */
export const dnOk=d=>d.st==="Pending"&&!!d.by&&!!d.due;
// @ts-expect-error TS2362: true and false subtract as 1 and 0 (Alan's decisions sort first)
export const dnSort=(a,b)=>(isMe(b.by)-isMe(a.by))||a.due.localeCompare(b.due)||a.id.localeCompare(b.id);
export const dnList=f=>DEC.filter(d=>dnOk(d)&&(!f||f(d))).sort(dnSort);
export const dnShut=st=>/^(Closed|Cancelled|Made|Withdrawn|Done)$/.test(st||"");
/* what slips: the open items it blocks, then the milestones those belong to (a milestone it blocks itself is listed once) */
export function dnSlips(d){ const out=[], add=id=>{ if(!out.includes(id)) out.push(id); };
  (d.slips||[]).forEach(id=>{ const k=kOfId(id), x=k&&REC(k,id), m=(D.milestone_names||{})[id];
    if(x&&!dnShut(x.st)){ add(id); if(x.ms&&!dnShut(((D.milestone_names||{})[x.ms]||[])[1])) add(x.ms); } else if(m&&!dnShut(m[1])) add(id); else if(!k&&!m) add(id); });
  return out.map(id=>{ const k=kOfId(id), x=k&&REC(k,id), m=(D.milestone_names||{})[id];
    if(x) return `${esc(id)} ${esc(decShort(x.t,60))}${x.due?` (due ${dnDt(x.due)})`:""}`;
    return m?`the ${esc(m[0])} milestone${m[2]?` (${dnDt(m[2])})`:""}`:esc(id); }); }
export const dnDt=iso=>`<span class="dt">${fd(iso)}</span>`;   /* a date never breaks across lines */
export function dnWait(d){ if(!d.since) return ""; const n=-days(d.since); return n<=0?"raised today":`waiting ${plur(n,"day")}`; }
export function dnNeeded(d){ if(decLate(d)) return `needed by ${dnDt(d.due)}, <span class="late">${decLateWords(d)}</span>`;
  const n=days(d.due); return n===0?"needed today":n===1?"needed tomorrow":`needed by ${dnDt(d.due)}, in ${n} days`; }
/* one row: o.n numbers it as a Today line; o.inProject leaves the project out; o.extra is added at the end (Prep's reason) */
export function dnDecisionHtml(d,o={}){ const mine=isMe(d.by), slips=dnSlips(d), id=esc(d.id);
  const title=tLink(`data-open="decisions:${id}"`,esc(d.t));
  const body=[mine?'<span class="dnyours">Yours</span> asked of you':`from ${esc(d.by)}`,o.inProject?"":o.n?projLink(d.p):pLink(d.p),dnWait(d),dnNeeded(d)].filter(Boolean).join(" · ")
    +(slips.length?`<span class="dnslip">If it stays open: ${andList(slips)}</span>`:"")+(o.extra||"");
  if(o.n) return tl(o.n,title,body,`<span class="tacts dnacts">${mine?tib("flag","Record the decision",`Record the decision: ${d.t}`,`data-dndecide="${id}"`,true)
    :tib("chasemail","Draft email",`Draft email to ${d.by}: ${d.t}`,`data-dnchase="${id}" aria-haspopup="dialog"`,true)}${tib("external","Open",`Open ${d.id}`,`data-open="decisions:${id}"`)}</span>`,'class="dnrow"');   /* BL-319: Today's rows have icons */
  const acts=`<span class="dnacts">${mine?`<button type="button" class="mini" data-dndecide="${id}" aria-label="Decide ${id}">Decide</button>`:`<button type="button" class="mini" data-dnchase="${id}" aria-label="Draft email to ${esc(d.by)} for ${id}" data-tip="Draft an email to ${esc(d.by)}: nothing is sent">Draft email</button>`}<button type="button" class="mini" data-open="decisions:${id}" aria-label="Open ${id}">Open</button></span>`;
  return o.n?tl(o.n,title,body,acts,'class="dnrow"'):`<div class="dnrow"><div class="tb">${title}<p>${body}</p></div>${acts}</div>`; }
export const dnBlock=(L,o)=>L.length?`<div class="dnlist">${L.map(d=>dnDecisionHtml(d,o)).join("")}</div>`:"";
/* Today: the band, hidden when nothing waits */
export function renderDn(){ const L=dnList(), sec=$("#dnSec"); if(!sec) return; sec.hidden=!L.length; if(!L.length) return;
  const mine=L.filter(d=>isMe(d.by)).length, late=L.filter(decLate).length, c=capped(L.map((d,i)=>dnDecisionHtml(d,{n:i+1})),5,"dn");
  $("#nDn").textContent=[plur(L.length,"decision"),mine?`${mine} yours`:"",late?`${late} late`:""].filter(Boolean).join(" · ");
  putHtml($("#dnList"),c.html); putHtml($("#dnMore"),c.more); }
export function dnChase(id){ const d=REC("decisions",id); if(!d) return;
  if(!PERS().some(y=>y.name===d.by)){ snack(`${d.by} isn't on the People page, so there's no one to draft to`); return; }
  openDraftEmail(d.by,decLate(d)?"chase":"update",id); }
export function dnDecide(id){ const p=$("#prepDlg"); if(p&&p.open) p.close(); recordFromBoard(id); }
/* ===== end BL-210 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootMeetings0144(){
document.addEventListener("click",e=>{ const c=e.target.closest("[data-dnchase]"), k=e.target.closest("[data-dndecide]");
  if(c){ e.preventDefault(); dnChase(c.dataset.dnchase); } else if(k){ e.preventDefault(); dnDecide(k.dataset.dndecide); } });
}
/* ===== Steering one-pager (BL-92, sprint 5) ===== */
/* A meeting named like a steering committee ("SteerCo", "Steering"), matched to a project, gets a "Draft the one-pager" link in its
   Prep: pressing it asks creaite to draft it (the cx-steerco skill; confirmed in the chat panel, held for review as usual). Never
   scheduled and never sent. */
export const isSteering=t=>/steer/i.test(t||"");
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootMeetings0145(){
document.addEventListener("click",e=>{ if(e.target.closest("[data-steer]")){ const d=$("#prepDlg"); if(d&&d.open) d.close(); } },true);
}
/* ===== Decisions in meeting prep (BL-113) ===== */
/* The Prep brief also lists the project's decisions still needed (who is asked, by when) and the made decisions whose revisit
   date has come, after "Decisions since then", with the invite's reasons first. A portfolio meeting lists every project's. */

/* ===== BL-223 (sprint-drafts-writing) ===== Draft agenda: in the Prep popup (and from the meeting page), creaite builds a timed agenda
   in plain code from the Prep page's own selection (the decisions that need the meeting first, then overdue and Urgent work, then
   milestones due, then last time's uncovered points; at most six, timed from the meeting's length) and Claude words the invite text
   around it: a POAD (Purpose, Objectives, Approach, Deliverables) or the lighter write-up, each sentence with its sources. Copy gives
   rich text and plain text for pasting into the invite; Save to Agendas writes a Markdown file there by the server's own write (never
   overwriting; Internal unless marked for attendees). Nothing is sent and no invite is created or changed. A confidential meeting
   gives Claude its title and times only. */
export function putHtml(el,html){ if(el) putHTML(el,raw(html)); }        /* one place the writing drafts set HTML (BL-228 D) */
export let AGD=null;                                          /* the Prep popup's agenda: {key, html, d, style, attendees, saved} */
export const AGSTYLES=[["poad","POAD"],["lite","POAD lite"]];
export function agendaStyle(){ const v=store.get("creaite-agenda-style",S.agendaStyle||"poad"); return AGSTYLES.some(x=>x[0]===v)?v:"poad"; }
export function setAgendaStyle(v){ if(AGSTYLES.some(x=>x[0]===v)) store.set("creaite-agenda-style",v); }   /* BL-286 B: the last style used is remembered */
export const agendaInvited=()=>!!store.get("creaite-agenda-invited",false), setAgendaInvited=v=>store.set("creaite-agenda-invited",!!v);
/* "Include who's invited": the attendee list, by name (the people register's names when the live server has given them), as a last part */
export function agendaInvitedPart(){ if(!agendaInvited()) return null; const {m,brief}=prepNow(); if(m.invite&&m.invite.confidential) return null;
  const L=invitees(m,brief).map(p=>p.name); return L.length?{head:"Invited",text:L.join(", ")}:null; }
export function agendaDraw(){ if(AGD&&shared.PREPEV&&AGD.key===prepKey(shared.PREPEV,shared.PREPDAY)) putHtml($("#prepAgenda"),AGD.html); }
export const agWhen=p=>p.at?`${p.at}`:"";
/* the copy: Outlook-safe inline styles (as Draft email), and the same as plain text */
export function agendaCopy(d){ const C=DE_COLOURS, e=esc, p=(inner,x="")=>`<p style="${DE_FONT}color:${C.ink};margin:0 0 10px 0;${x}">${inner}</p>`;
  const parts=(d.parts||[]).map(x=>p(`${x.head?`<b style="font-weight:bold;">${e(x.head)}</b><br>`:""}${e(x.text)}`)).join("");
  const td=(t,x="")=>`<td style="${DE_FONT}color:${C.ink};border-bottom:1px solid ${C.rule};padding:4px 8px;vertical-align:top;${x}">${t}</td>`;
  const rows=(d.agenda||[]).map(a=>`<tr>${td(e(agWhen(a)),"white-space:nowrap;")}${td(e(a.point))}${td(`${a.minutes} min`,"white-space:nowrap;")}</tr>`).join("");
  const html=`<div style="${DE_FONT}color:${C.ink};background:${C.white};">${parts}${rows?`${p('<b style="font-weight:bold;">Agenda</b>',"margin-bottom:4px;")}<table cellpadding="4" cellspacing="0" border="0" style="border-collapse:collapse;${DE_FONT}color:${C.ink};">${rows}</table>`:""}</div>`;
  const text=[...(d.parts||[]).flatMap(x=>[x.head,x.text,""].filter((v,i)=>i>0||v)),...((d.agenda||[]).length?["Agenda",...d.agenda.map(a=>`${agWhen(a)?agWhen(a)+"  ":""}${a.point} (${a.minutes} min)`)]:[])].join("\n").trim();
  return {html,text}; }
export function agendaCardHtml(d){ const loose=d.unsourced||0, conf=d.confidential?'<div class="agnote">Confidential meeting: Claude saw only its title and times.</div>':"";
  const parts=(d.parts||[]).map(x=>`${x.head?`<h4>${esc(x.head)}</h4>`:""}${draftTextHtml({sources:d.sources,sentences:x.sentences,text:x.text})}`).join("");
  const list=(d.agenda||[]).length?`<ol class="aglist" aria-label="Agenda">${d.agenda.map(a=>`<li><span class="agt">${esc(agWhen(a))}</span><span>${esc(a.point)}</span><span class="agm">${a.minutes} min</span></li>`).join("")}</ol>`:'<div class="agnote">No agenda points: nothing is due, overdue or waiting on a decision.</div>';
  return `<div class="drcard" role="region" aria-label="Draft agenda" tabindex="-1"><div class="drhead">${ic("spark")}<b>Draft agenda</b><span class="sub">A suggestion: copy it into the invite. Nothing is sent and no invite is changed.</span></div>
    <div class="agparts">${parts}</div>${loose?`<div class="drnote">${loose} sentence${loose===1?" has":"s have"} no source: check ${loose===1?"it":"them"} before you use it.</div>`:""}${list}${conf}${draftSrcHtml(d,false,"Drafted from")}
    <label class="agnote"><input type="checkbox" data-agatt ${AGD&&AGD.attendees?"checked":""}> Save it for attendees (otherwise it is saved marked Internal)</label>
    <div class="drfoot"><span class="sp"></span><button type="button" class="btn" data-agdo="discard">Discard</button><button type="button" class="btn" data-agdo="save" ${viaServer()?"":"disabled"} data-tip="Save it as a file in the project's Agendas folder">Save to Agendas</button><button type="button" class="btn" data-agdo="plain">Copy as plain text</button><button type="button" class="btn primary" data-agdo="copy">Copy</button></div><div class="sub" id="agMsg" role="status"></div></div>`; }
export async function draftAgenda(){ const why=draftWhyNot("agenda"); if(why){ snack(why); return; } if(!shared.PREPEV) return;
  const key=prepKey(shared.PREPEV,shared.PREPDAY), style=agendaStyle(), mine={key,html:"",style,attendees:false}; AGD=mine;
  const res=await draftAsk({kind:"agenda",key,style},{label:"Drafting the agenda",status:h=>{ if(AGD===mine){ mine.html=h?`<div class="drstatus" role="status">${h}</div>`:""; agendaDraw(); } }});
  if(AGD!==mine){ if(res.ok&&!res.nothing) draftStat("agenda","rejected"); return; }
  if(res.nothing){ mine.html=`<div class="drnone" role="status">${ic("spark")}<span>${esc(res.nothing)}</span></div>`; agendaDraw(); return; }
  if(!res.ok){ AGD=null; agendaDraw(); putHtml($("#prepAgenda"),""); snack(res.message||"No draft came back"); return; }
  { const inv=agendaInvitedPart(); if(inv) res.parts=[...(res.parts||[]),inv]; }
  mine.d=res; mine.html=agendaCardHtml(res); agendaDraw(); $("#prepAgenda .drcard")?.focus?.(); }
export async function agendaCopyDo(rich,btn){ const c=agendaCopy(AGD.d);
  try{ if(!navigator.clipboard) throw new Error("no clipboard");
    if(rich){ if(typeof ClipboardItem==="undefined"||!navigator.clipboard.write) throw new Error("no rich clipboard"); await navigator.clipboard.write([new ClipboardItem({"text/html":new Blob([c.html],{type:"text/html"}),"text/plain":new Blob([c.text],{type:"text/plain"})})]); }
    else await navigator.clipboard.writeText(c.text);
    copied(btn); $("#agMsg").textContent=rich?"Copied: paste it into the invite":"Copied as plain text"; }
  catch(err){ $("#agMsg").textContent=`Your browser blocked copying: select the text and press ${MOD}C`; return; }
  if(!AGD.used){ AGD.used=true; draftStat("agenda","used"); } }
export async function agendaSave(btn){ if(!viaServer()){ snack("Saving needs creaite to be running"); return; } const d=AGD.d; btn.disabled=true;
  const r=await api("/api/agenda/save",{key:AGD.key,parts:(d.parts||[]).map(x=>({head:x.head,text:x.text})),agenda:d.agenda||[],attendees:!!AGD.attendees}); btn.disabled=false;
  if(!r.ok){ snack(oneLine(r.message)||"The agenda wasn't saved"); return; }
  $("#agMsg").textContent=`Saved: ${r.path}`; snack(`Agenda saved in the Agendas folder${AGD.attendees?" (for attendees)":" (Internal)"}`); if(!AGD.used){ AGD.used=true; draftStat("agenda","used"); } }
/* ===== end BL-223 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootMeetings0201(){
DRAFTFEATURES.push(["agenda","Draft the agenda and invite text","From the Prep page: the invite text (POAD or a lighter write-up) and a timed agenda, to copy"]);
Object.assign(DRAFTKIND,{agenda:"agenda"});
document.addEventListener("click",e=>{   /* Draft agenda itself is a menu now (PrepToolbar, BL-286 B) */
  const a=e.target.closest("[data-agdo]"); if(!a||!AGD||!AGD.d) return; e.preventDefault();
  if(a.dataset.agdo==="discard"){ if(!AGD.used) draftStat("agenda","rejected"); AGD=null; putHtml($("#prepAgenda"),""); $("[data-agenda]")?.focus(); return; }
  if(a.dataset.agdo==="save"){ agendaSave(a); return; }
  agendaCopyDo(a.dataset.agdo==="copy",a); });
document.addEventListener("change",e=>{ if(e.target.matches&&e.target.matches("[data-agatt]")&&AGD){ AGD.attendees=e.target.checked; AGD.html=agendaCardHtml(AGD.d); } });
}
/* ===== v2.1.0 P10 (BL-339) ===== the meeting hub is retired. An old #meeting=<token> link (and a bookmark) is read from the
   token index the page still carries (D.hub, build_dashboard.meeting_hub) and sent to the meeting's Prep before it, and to its
   minutes (#minutes=<stored path>, the minutes view) after it. Nothing here draws a page. */
export function meetingRoute(token){ const m=(D.hub||{})[token]; if(!m||!m.day) return null;
  const now=new Date();
  const clockNow=String(now.getHours()).padStart(2,"0")+":"+String(now.getMinutes()).padStart(2,"0");
  const over=m.day<TODAY||(m.day===TODAY&&!!(m.end||m.start)&&(m.end||m.start)<=clockNow);
  const minFile=(m.filed||[]).find(f=>String(f).toLowerCase().endsWith(".html"));
  if(over&&minFile) return "#minutes="+encodeURIComponent(minFile);
  if(over&&(m.counts||{}).pending) return "#review";   /* the minutes are drafted and waiting: Review is where they open */
  const ev=(((D.calendar||{}).days||{})[m.day]||[]).find(e=>e.start===m.start&&e.title===m.title);
  return ev?prepHref(prepKey(ev,m.day),m.day):null; }
/* the retired page's address for the meeting a file belongs to (its minutes, copies or quick note), or null */
export function meetingOfFile(path){ const found=Object.entries(D.hub||{}).find(([,m])=>(m.files||[]).includes(path)); return found?found[0]:null; }
/* ===== end P10 ===== */
