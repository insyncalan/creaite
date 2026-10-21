// @ts-check
/* drafts.js (BL-231 step 2b), moved from script/ by dev/tools/convert_area.py: 0128-draft-email-bl-83.js, 0129-bl-224-sprint-drafts-writing.js, 0160-bl-157-sprint-ux.js, 0196-ai-drafts-the-scaffold-sprint-drafts-fie.js, 0202-bl-227-sprint-drafts-writing.js, 0203-bl-224-sprint-drafts-writing.js, 0204-bl-220-sprint-drafts-extraction.js.
   Unchanged apart from `export`, `shared.` for the shared state (core/state.js) and the load-time steps, now in
   boot…() functions that src/main.js calls in today's order. */
import { openDialog } from "./components/Dialog.jsx";
import { closePicker } from "./components/Picker.jsx";
import { linkSegments, linkWithAddress, sentStrip } from "./core/linkText.js";
import { linkUrl } from "./core/linkUrl.js";
import { makeDraftEmailDialog } from "./components/dialogs/PageDialogs.jsx";
import { drawCk, rbEnd, rbStart } from "./ask.js";
import { drawChips } from "./components/Chip.jsx";
import { A, open, P, pName, soon, wsFor } from "./core/data.js";
import { $, $$, addHTML, esc, html, ic, ICONS, putHTML, raw } from "./core/dom.js";
import { creaiteEditor, edEmailHtml } from "./core/editor.js";
import { CALI, CMDENTER, closeCal, onCmdEnter, parseWhen } from "./core/fields.js";
import { copied, D, DDATE, fd, MOD, S, store, TODAY, toIso } from "./core/page.js";
import { api, OLDSERVER, oneLine, snack, status, viaServer, writeSettings } from "./core/server.js";
import { shared } from "./core/state.js";
import { putHtml } from "./meetings.js";
import { curObj, mdHtml, msChoices, openProposal, pkCid, pkCommit, PKDRAW, PKDRBODY, PKDRBTN, PKDREXTRA, PKDRTITLE, PKFL, pkLabel, pkNewTitle, pkRev, pkUndoLast, REC } from "./panel.js";
import { curRefine, curVersion, DRAFTKIND, GEN_AUD, GEN_AUDNOTE, GEN_FORMS, genSummary } from "./projects.js";
import { draftOn, SPARKI } from "./review.js";
import { PERS, personPool, renderPerson, row, SA, SETSECTIONS } from "./settings.js";
import { plur } from "./today.js";
import { hit, items, rows } from "./work.js";
/* ===== Draft email (BL-83) ===== */
/* The email to a person asking where their open items stand. A pure builder: it reads nothing from the page, so it is tested on its own.
   It writes for Outlook's Word engine: every element has its own inline style, a table with cellpadding and a bottom border on each cell,
   Calibri then Arial, no classes, variables, flexbox or images. The email is always drawn on white, whichever theme is on. Colour is never
   the only signal: the words say overdue and due soon too. */
export const DE_COLOURS={red:"#B3261E",amber:"#8A5A00",ink:"#1E1F1E",muted:"#5C5D60",head:"#F1F3F4",rule:"#D9D9E0",white:"#FFFFFF",askBg:"#F7F3E3",askRule:"#C9A227"};   /* askBg, askRule: BL-298's "What I need from you" line */
export const DE_FONT="font-family:Calibri,Arial,sans-serif;font-size:11pt;";
export const DE_OPEN="I hope you're well. I'm pulling together where things stand on the items below and would be grateful for a brief update on each when you have a moment.";
export const DE_ASK="Could you let me know where each one stands, and flag anything that's blocking you or that you need from me?";
export const DE_THANKS="Thank you very much for your help.";
export const DE_DECIDE="Where an item is a decision we need from you, could you let me know what you have decided?";   /* BL-53 */
export const deIsoDays=(a,b)=>Math.round((Date.UTC(+a.slice(0,4),+a.slice(5,7)-1,+a.slice(8,10))-Date.UTC(+b.slice(0,4),+b.slice(5,7)-1,+b.slice(8,10)))/864e5);
export const deGreeting=(now,first)=>`Good ${now.getHours()<12?"morning":now.getHours()<18?"afternoon":"evening"}${first?", "+first:""},`;
/* what to say about a due date, relative to today: {words, level: "over" | "soon" | ""} */
export function deDue(due,today,soon){ if(!due) return {date:"No date",words:"",level:""}; const n=deIsoDays(due,today), date=fd(due);
  if(n<0) return {date,words:`${-n} day${n===-1?"":"s"} overdue`,level:"over"};
  if(n<=soon) return {date,words:n===0?"due today":n===1?"due tomorrow":`due in ${n} days`,level:"soon"};
  return {date,words:"",level:""}; }
export const deRank=(x,today)=>{ const d=x.due; return [d?(d<today?0:1):2,d||"9999",x.id]; };
export const deSort=(a,b,today)=>{ const x=deRank(a,today), y=deRank(b,today); return x[0]-y[0]||x[1].localeCompare(y[1])||x[2].localeCompare(y[2]); };
export function deSubject(items,today){ if(!items.length) return "Update request"; const codes=[...new Set(items.map(i=>i.p))].sort();
  if(items.length===1) return `${items[0].id} · Update request`;
  const over=items.filter(i=>i.due&&i.due<today).length; return `${codes.join(" / ")} · Update request: ${items.length} open items${over?` (${over} overdue)`:""}`; }
/* ===== BL-224 (sprint-drafts-writing) ===== one email component, three modes. draftEmail stays a pure builder with no model call:
   mode "update" (BL-83's update request, unchanged), "followup" (after a meeting: the minutes' own summary paragraph, the decisions and
   the actions grouped by owner, the lead recipient's first) and "chase" (overdue items, the tone stepping up with how often they have
   been chased, from system/staging/chases.json). The row, the table and the plain-text lines are shared by every mode. */
export const deTd=(inner,extra="")=>`<td style="${DE_FONT}color:${DE_COLOURS.ink};border-bottom:1px solid ${DE_COLOURS.rule};padding:6px 8px;vertical-align:top;${extra}">${inner}</td>`;
export const deTh=(t,w)=>`<th align="left" style="${DE_FONT}color:${DE_COLOURS.ink};background:${DE_COLOURS.head};border-bottom:1px solid ${DE_COLOURS.rule};padding:6px 8px;text-align:left;font-weight:bold;${w?`width:${w};`:""}">${t}</th>`;
export const deP=(inner,extra="")=>`<p style="${DE_FONT}color:${DE_COLOURS.ink};margin:0 0 12px 0;${extra}">${inner}</p>`;
export const deHead=t=>`<p style="${DE_FONT}color:${DE_COLOURS.ink};margin:16px 0 6px 0;"><b style="font-weight:bold;">${esc(t)}</b></p>`;
export const deTimes=n=>n===1?"once":n===2?"twice":`${n} times`;
export const deChasedWords=c=>`Chased ${fd(c.last)}, ${deTimes(c.n)}`;
export const deReplyBy=r=>r?` It would be helpful to hear back by ${new Date(r+"T12:00:00").toLocaleDateString("en-GB",{weekday:"long"})} ${fd(r)}.`:"";
/** #121: plain text with links as the email's HTML: the words escaped, a link as an anchor with its colour written in (a mail program drops classes). The rich copy keeps the
    link; the plain copy (deTextRows) shows "words (address)". Only an address core/linkUrl.js accepts is ever an anchor. @param {unknown} t */
export const deLinks=t=>linkSegments(t).map(x=>x.href?`<a href="${esc(linkUrl(x.href))}" target="_blank" rel="noopener noreferrer" style="color:${DE_COLOURS.link||"#0b5cad"};text-decoration:underline;">${esc(x.t)}</a>`:esc(x.t)).join("");
export function deRowHtml(i,o){ const C=DE_COLOURS, e=esc, d=deDue(i.due,o.today,o.dueSoon??7), colour=d.level==="over"?C.red:d.level==="soon"?C.amber:C.ink, strong=d.level==="over"?"font-weight:bold;":"";
  const what=i.k==="raid"?`<b style="font-weight:bold;">${e(i.type||"Risk")}:</b> ${e(i.t)}<br><span style="color:${C.muted};">Response: ${sentStrip(i.resp).trim()?deLinks(sentStrip(i.resp).trim()):"none recorded yet"}</span>`:i.k==="decisions"?`<b style="font-weight:bold;">Decision needed:</b> ${e(i.t)}`:e(i.t);
  const upd=o.includeUpdate&&sentStrip(i.upd).trim()?`<br><span style="color:${C.muted};">Latest update: ${deLinks(sentStrip(i.upd))}</span>`:"";
  const ch=o.chased&&o.chased[i.id]?`<br><span style="color:${C.muted};">${e(deChasedWords(o.chased[i.id]))}</span>`:"";
  return `<tr style="vertical-align:top;">${deTd(e(i.noid?"":i.id),"white-space:nowrap;")}${deTd(what+upd+ch)}${deTd(`<span style="color:${colour};${strong}">${e(d.date)}</span>${d.words?`<br><span style="color:${colour};${strong}">${e(d.words)}</span>`:""}`,"white-space:nowrap;")}${deTd(i.pr==="Urgent"?`<b style="font-weight:bold;">Urgent</b>`:e(i.pr||""),"white-space:nowrap;")}</tr>`; }
export function deTableHtml(list,o){ return `<table cellpadding="6" cellspacing="0" border="0" style="border-collapse:collapse;width:100%;${DE_FONT}color:${DE_COLOURS.ink};"><tr style="vertical-align:top;">${deTh("ID","9%")}${deTh("Item")}${deTh("Due","18%")}${deTh("Priority","10%")}</tr>${list.map(i=>deRowHtml(i,o)).join("")}</table>`; }
export function deTextRows(list,o){ const w=Math.max(...list.map(i=>(i.noid?"":i.id).length)), out=[], pad="".padEnd(w);
  list.forEach(i=>{ const d=deDue(i.due,o.today,o.dueSoon??7); out.push(`  ${(i.noid?"":i.id).padEnd(w)}  ${i.k==="raid"?`${i.type||"Risk"}: `:i.k==="decisions"?"Decision needed: ":""}${i.t}  |  ${d.date}${d.words?` (${d.words})`:""}  |  ${i.pr||""}`);
    if(i.k==="raid") out.push(`  ${pad}  Response: ${linkWithAddress(sentStrip(i.resp).trim())||"none recorded yet"}`);
    if(o.includeUpdate&&sentStrip(i.upd).trim()) out.push(`  ${pad}  Latest update: ${linkWithAddress(sentStrip(i.upd))}`);
    if(o.chased&&o.chased[i.id]) out.push(`  ${pad}  ${deChasedWords(o.chased[i.id])}`); });
  return out; }
export const dePicked=o=>o.items.filter(i=>!o.picked||o.picked.has(i.k+":"+i.id));
export const deByProject=(items,c,today)=>items.filter(i=>i.p===c).sort((a,b)=>deSort(a,b,today));
export const deClose=o=>[deP(`Kind regards,<br>${esc(o.from||"")}`,"margin-bottom:0;"),["","Kind regards,",o.from||""]];
/* o: {mode, name, first, email, items:[{k,id,p,t,due,pr,type,resp,upd}], picked:Set of "k:id" (all when absent), includeUpdate, replyBy (YYYY-MM-DD),
       now:Date, today:"YYYY-MM-DD", dueSoon, names:{code:name}, from:"Alan", cover (the opening paragraph, BL-224's Polish)} → {to, subject, html, text, items}
   followup adds {title, day, attendees:[{name,email}], lead, summary}; chase adds {chased:{id:{n,last}}} */
export function draftEmail(o){ if(o.mode==="followup") return deFollowup(o); if(o.mode==="chase") return deChase(o);
  const e=esc, today=o.today, first=o.first||String(o.name||"").split(/\s+/)[0]||"";
  const items=dePicked(o), codes=[...new Set(items.map(i=>i.p))].sort(), reply=deReplyBy(o.replyBy), open=o.cover||DE_OPEN, ask=`${DE_ASK}${items.some(i=>i.k==="decisions")?" "+DE_DECIDE:""}${reply} ${DE_THANKS}`;
  const blocks=codes.map(c=>deHead((o.names||{})[c]||c)+deTableHtml(deByProject(items,c,today),o)).join(""), [endH,endT]=deClose(o);
  const html=`<div style="${DE_FONT}color:${DE_COLOURS.ink};background:${DE_COLOURS.white};">${deP(e(deGreeting(o.now,first)))}${deP(e(open))}${blocks}${deP(e(ask),"margin-top:16px;")}${endH}</div>`;
  const lines=[deGreeting(o.now,first),"",open,""];   /* the same email as plain text: the table as aligned lines */
  codes.forEach(c=>lines.push(((o.names||{})[c]||c).trim(),...deTextRows(deByProject(items,c,today),o),""));
  lines.push(ask,...endT);
  return {to:o.email||"",subject:deSubject(items,today),html,text:lines.join("\n"),items}; }
/* Chase: the tone steps up with the most often chased of the items picked: a first reminder, a second, then a firmer one */
export const DE_CHASE=[{subj:"Reminder",open:"A quick reminder about the items below, which are now past their due dates.",ask:"Could you let me know where each one stands, and when I can expect it?"},
  {subj:"Second reminder",open:"I'm following up on my earlier note{last} about the items below, which are still overdue.",ask:"Could you let me have an update on each, and a date for anything still open?"},
  {subj:"Overdue, reply needed",open:"These items are now well overdue and are holding up other work; I have chased them {n}{since}.",ask:"Please reply with a firm date for each, or tell me what is blocking it so that we can resolve it together."}];
export function deChaseLevel(items,chased){ const c=items.map(i=>(chased||{})[i.id]).filter(Boolean), n=Math.max(0,...c.map(x=>x.n)), last=c.map(x=>x.last).sort().pop()||"";
  return {level:Math.min(n,2),n,last}; }
export function deChase(o){ const e=esc, today=o.today, first=o.first||String(o.name||"").split(/\s+/)[0]||"", items=dePicked(o), codes=[...new Set(items.map(i=>i.p))].sort();
  const lv=deChaseLevel(items,o.chased), t=DE_CHASE[lv.level], open=o.cover||t.open.replace("{last}",lv.last?` of ${fd(lv.last)}`:"").replace("{n}",deTimes(lv.n)).replace("{since}",lv.last?`, most recently on ${fd(lv.last)}`:"");
  const ask=`${t.ask}${deReplyBy(o.replyBy)} ${DE_THANKS}`, [endH,endT]=deClose(o);
  const blocks=codes.map(c=>deHead((o.names||{})[c]||c)+deTableHtml(deByProject(items,c,today),o)).join("");
  const html=`<div style="${DE_FONT}color:${DE_COLOURS.ink};background:${DE_COLOURS.white};">${deP(e(deGreeting(o.now,first)))}${deP(e(open))}${blocks}${deP(e(ask),"margin-top:16px;")}${endH}</div>`;
  const lines=[deGreeting(o.now,first),"",open,""]; codes.forEach(c=>lines.push(((o.names||{})[c]||c).trim(),...deTextRows(deByProject(items,c,today),o),"")); lines.push(ask,...endT);
  const subject=!items.length?t.subj:items.length===1?`${items[0].id} · ${t.subj}`:`${codes.join(" / ")} · ${t.subj}: ${items.length} overdue items`;   /* nothing ticked yet: no "0 overdue items" */
  return {to:o.email||"",subject,html,text:lines.join("\n"),items,level:lv.level}; }
/* Follow-up: the actions grouped by owner, the lead recipient's own first, then the other attendees', then the rest */
export function deOwners(acts,o){ const names=[o.lead,...(o.attendees||[]).map(a=>a.name)].filter(Boolean), all=[...new Set(acts.map(i=>i.o||"No owner"))];
  return [...names.filter(n=>all.includes(n)).filter((n,i,a)=>a.indexOf(n)===i),...all.filter(n=>!names.includes(n)).sort()]; }
export const DE_INTERNAL="Internal: not for distribution.";
export function deFollowup(o){ const e=esc, today=o.today, items=dePicked(o), acts=items.filter(i=>i.k==="actions"), decs=items.filter(i=>i.k==="decisions"), codes=[...new Set(items.map(i=>i.p).concat(o.codes||[]))].sort();
  const att=o.attendees||[], first=att.length===1?String(att[0].name).split(/\s+/)[0]:"all";
  const when=o.day?` on ${new Date(o.day+"T12:00:00").toLocaleDateString("en-GB",{weekday:"long"})} ${fd(o.day)}`:"";
  const open=o.cover||`Thank you for your time at the ${o.title||"meeting"}${when}. Here is a short summary, the decisions we made and the actions we agreed.`;
  const ask=`Please let me know if I have missed or misrecorded anything.${deReplyBy(o.replyBy)} ${DE_THANKS}`, [endH,endT]=deClose(o), owners=deOwners(acts,o), mine=n=>acts.filter(i=>(i.o||"No owner")===n).sort((a,b)=>deSort(a,b,today));
  const html=`<div style="${DE_FONT}color:${DE_COLOURS.ink};background:${DE_COLOURS.white};">${o.internal?deP(`<b style="font-weight:bold;">${DE_INTERNAL}</b>`):""}${deP(e(deGreeting(o.now,first)))}${deP(e(open))}`
    +(o.summary?deHead("Summary")+deP(e(o.summary)):"")+(decs.length?deHead("Decisions")+decs.map(d=>deP(`• ${e(d.t)}${d.by?` <span style="color:${DE_COLOURS.muted};">(${e(d.by)})</span>`:""}`,"margin:0 0 4px 0;")).join(""):"")
    +(acts.length?deHead("Actions")+owners.map(n=>deP(`<b style="font-weight:bold;">${e(n)}</b>`,"margin:10px 0 4px 0;")+deTableHtml(mine(n),o)).join(""):"")+`${deP(e(ask),"margin-top:16px;")}${endH}</div>`;
  const lines=[...(o.internal?[DE_INTERNAL,""]:[]),deGreeting(o.now,first),"",open,""];
  if(o.summary) lines.push("Summary",o.summary,"");
  if(decs.length) lines.push("Decisions",...decs.map(d=>`  • ${d.t}${d.by?` (${d.by})`:""}`),"");
  if(acts.length){ lines.push("Actions"); owners.forEach(n=>lines.push(n,...deTextRows(mine(n),o),"")); }
  lines.push(ask,...endT);
  return {to:att.map(a=>a.email).filter(Boolean).join("; "),subject:`${o.internal?"[Internal] ":""}${codes.join(" / ")}${codes.length?" · ":""}${o.title||"Meeting"}: follow-up and actions`,html,text:lines.join("\n"),items}; }
/* The popup. Opening, copying and changing it write nothing; the only record is "I sent it" in Chase (system/staging/chases.json,
   item IDs, the date and the mode, through the live server). Nothing is sent and no Outlook draft is made. */
shared.DE=null;   /* {mode, name, email, items, picked:Set, includeUpdate, replyBy, edited, subjEdited, outside, cover, polish; followup: token, title, day, attendees, lead, summary, note} */
export const deHost=addr=>String(addr||"").split("@")[1]?.trim().toLowerCase()||"";
export const deOutside=email=>{ const h=deHost(email); return !h||!(S.ownDomains||[]).includes(h); };   /* no address on record counts as outside */
export const deOutsideAll=L=>!L.length||L.some(a=>deOutside(a.email));                                    /* follow-up: one outside address is enough */
/* items marked confidential or restricted, or from a project's documents/, are never offered */
export const deBarred=i=>/\b(confidential|restricted)\b/i.test([i.t,i.resp,i.upd,i.src,i.cm].join(" "))||/(^|\/)documents\//i.test(String(i.src||""));
export const deItem=(k,i)=>({k,id:i.id,p:i.p,t:i.t,due:i.due||null,pr:i.pr,type:i.type,resp:i.resp,upd:i.upd,client:!!i.client,src:i.src,cm:i.cm,o:i.o||i.by||"",by:i.by||""});
export function deItems(x){ return [...x.oa.map(a=>deItem("actions",a)),...x.or.map(r=>deItem("raid",r)),...(x.D||[]).filter(d=>d.st==="Pending").map(d=>deItem("decisions",d))]; }   /* BL-53: decisions we need from them */
export const deOverdue=i=>!!i.due&&i.due<TODAY;
/* the default tick set: all of them for an address on an own domain; for anyone else only what is client-visible */
export const deDefaults=(items,outside)=>new Set(items.filter(i=>!outside||i.client).map(i=>i.k+":"+i.id));
export const deMe=n=>String(n||"").trim().toLowerCase()===String(S.me||"").trim().toLowerCase();
export function deDlgEl(){ let d=$("#deDlg"); if(d) return d;
  d=makeDraftEmailDialog(); d.addEventListener("click",e=>{ if(e.target.closest("#deClose")) d.close(); });   /* a click on the scrim is the Dialog's: it closes when nothing is typed */ d.addEventListener("close",()=>{ if(d.open) return; closeCal(); dePrevDrop(); if(shared.DE&&shared.DE.polish) draftStat("email","rejected"); shared.DE=null; }); return d; }   /* the close event is queued: a popup opened again meanwhile keeps its email */
export function deShow(title){ const d=deDlgEl(); $("#deTitle").textContent=title; drawDraftEmail(true); openDialog(d); }
/* from a person's page: an update request, or a chase of their overdue items */
/* only (BL-210, Decisions needed): one item's ID; it alone starts ticked (if the outside-address rule allows), the rest are offered unticked */
export function openDraftEmail(name,mode="update",only){ shared.SENTVIA=""; (()=>{ const x=PERS().find(y=>y.name===name); if(!x) return;
  const all=deItems(x), ok=all.filter(i=>!deBarred(i)), email=(x.p&&x.p.email)||"", chase=ok.filter(deOverdue);
  if(!ok.length){ snack(`Nothing open for ${name}, so no email is needed`); return; }
  if(mode==="chase"&&(!chase.length||deMe(name)||(only&&!chase.some(i=>i.id===only)))) mode="update";   /* BL-342 N3: a thread's Chase on an item not past its date opens the update email */
  const items=mode==="chase"?chase:ok, outside=deOutside(email), picked=deDefaults(items,outside);
  if(only&&!items.some(i=>i.id===only)){ snack(ok.some(i=>i.id===only)?`${only} isn't past its date yet, so it isn't in a chase`:`${only} is marked confidential or restricted, so it can't go in an email`); return; }
  if(only) [...picked].forEach(k=>{ if(!k.endsWith(":"+only)) picked.delete(k); });
  shared.DE={mode,name,email,items,left:all.length-ok.length,picked,includeUpdate:false,replyBy:"",edited:false,subjEdited:false,outside,canChase:!!chase.length&&!deMe(name),cover:"",polish:null,only};
  deShow(`Draft email: ${name}`); })();
 }   /* BL-288: the note about a followed person is dropped (Alan) */
/* from a meeting's page (and Review): the follow-up, with what the meeting produced that is in the tracker */
export function openFollowup(t){ const m=(D.hub||{})[t]; if(!m){ snack("That meeting isn't in creaite's records any more"); return; }
  const all=(m.items||[]).filter(x=>x.id&&(x.k==="actions"||x.k==="decisions")).map(x=>REC(x.k,x.id)&&deItem(x.k,REC(x.k,x.id))).filter(Boolean), ok=all.filter(i=>!deBarred(i));
  if(!ok.length){ snack("The meeting has no actions or decisions in the tracker yet: approve and apply them first"); return; }
  shared.DE={mode:"followup",token:t,title:m.title,day:m.day,codes:m.p||[],items:ok,left:all.length-ok.length,attendees:[],lead:"",summary:"",note:viaServer()?"Reading the attendees and the minutes' summary…":"The attendees and the minutes' summary need the live server.",
    picked:new Set(),includeUpdate:false,replyBy:"",edited:false,subjEdited:false,outside:true,cover:"",polish:null};
  shared.DE.picked=deDefaults(ok,true); deShow(`Follow-up: ${m.title}`); if(viaServer()) deFollowFacts(shared.DE,m); }
/* v2.1.0 P7: from the minutes view's Export menu, for the version shown ("internal" or "distributed"). The server builds the content
   (minutes_record.followup_facts: the distributed version through distributed_of, so no Internal only, Sensitive, partner-only or
   excluded content reaches the draft); the Internal version is marked Internal. The same popup, builder and Polish as the meeting's. */
export async function openMinutesFollowup(path,version){ const r=await api("/api/minutes/followup",{path,version});
  if(!r||!r.ok){ snack(oneLine((r&&r.message)||"")||"Couldn't read the minutes for the email"); return; }
  const all=(r.items||[]).map(x=>({...x,p:(r.codes||[])[0]||"",due:x.due||null,pr:"",client:version==="distributed",noid:/^@/.test(x.id),by:x.by||"",o:x.o||x.by||""})), ok=all.filter(i=>!deBarred(i));
  if(!ok.length){ snack(version==="distributed"?"The distributed version has no actions or decisions to put in an email":"The minutes have no actions or decisions to put in an email"); return; }
  const outside=version==="distributed"?deOutsideAll(r.attendees||[]):false;
  const de={mode:"followup",token:"",title:r.title,day:r.day,codes:r.codes||[],items:ok,left:all.length-ok.length,attendees:r.attendees||[],lead:"",summary:r.summary||"",
    note:version==="distributed"?`From the Distributed version${r.left_out?`: ${r.left_out} withheld item${r.left_out===1?"":"s"} and every Internal only line left out`:": Internal only lines are left out"}.`:"From the Internal version: the email is marked Internal.",
    picked:new Set(),includeUpdate:false,replyBy:"",edited:false,subjEdited:false,outside:false,cover:"",polish:null,internal:version!=="distributed",version};
  shared.DE=de; const owners=new Set(ok.map(i=>i.o)); de.lead=(de.attendees.find(a=>owners.has(a.name))||{}).name||""; de.picked=new Set(ok.map(i=>i.k+":"+i.id));
  deShow(`${version==="distributed"?"Distributed":"Internal"} follow-up: ${r.title}`); }
export async function deFollowFacts(de,m){ const r=await api("/api/email/followup",{key:m.key,eid:m.eid||"",day:m.day,start:m.start,title:m.title,files:[...(m.files||[]),...(m.draft?[m.draft]:[])]});
  if(shared.DE!==de) return; if(!r.ok){ de.note=oneLine(r.message)||"Couldn't read the attendees and the summary"; drawDraftEmail(true); return; }
  de.attendees=r.attendees||[]; de.summary=r.summary||""; de.note=r.note||""; de.outside=deOutsideAll(de.attendees);
  const owners=new Set(de.items.map(i=>i.o)); de.lead=(de.attendees.find(a=>owners.has(a.name))||{}).name||""; de.picked=deDefaults(de.items,de.outside); drawDraftEmail(true); }
export function deBuild(){ return draftEmail({mode:shared.DE.mode,name:shared.DE.name,email:shared.DE.email,items:shared.DE.items,picked:shared.DE.picked,includeUpdate:shared.DE.includeUpdate,replyBy:shared.DE.replyBy,now:new Date(),today:TODAY,dueSoon:S.dueSoon,
  names:Object.fromEntries(P.map(p=>[p.code,p.name])),from:String(S.me||"").split(/\s+/)[0],cover:shared.DE.cover,chased:SA().chases||{},
  title:shared.DE.title,day:shared.DE.day,codes:shared.DE.codes,attendees:shared.DE.attendees,lead:shared.DE.lead,summary:shared.DE.summary,internal:!!shared.DE.internal}); }
/* the parts of the popup that differ by mode */
export function deModesHtml(){ if(shared.DE.mode==="followup") return "";
  return `<div class="demodes" role="group" aria-label="Kind of email"><button type="button" class="vchip" data-demode="update" aria-pressed="${shared.DE.mode==="update"}">Update request</button><button type="button" class="vchip" data-demode="chase" aria-pressed="${shared.DE.mode==="chase"}" ${shared.DE.canChase?"":'disabled data-tip="Nothing of theirs is overdue"'}>Chase overdue items</button></div>`; }
export function deToHtml(){ if(shared.DE.mode!=="followup") return `<span id="deTo">${shared.DE.email?esc(shared.DE.email):'<span class="sub">No email recorded</span>'}</span>${shared.DE.email?'<button class="mini" id="deCopyTo">Copy</button>':""}`;
  const L=shared.DE.attendees; return `<span id="deTo">${L.length?L.map(a=>`${esc(a.name)}${a.email?` &lt;${esc(a.email)}&gt;`:' <span class="sub">(no address)</span>'}`).join("; "):'<span class="sub">No attendees on record</span>'}</span>${L.some(a=>a.email)?'<button class="mini" id="deCopyTo">Copy</button>':""}`; }
export const deChaseText=lv=>`${["A first reminder","A second reminder","A firmer reminder"][lv.level]}${lv.n?`: chased ${fd(lv.last)}, ${deTimes(lv.n)}`:": not chased before"}. Press I sent it after you send it, so the next one knows.`;
export function deChaseLine(){ const el=$("#deChase"); if(!el) return; const pk=shared.DE.items.filter(i=>shared.DE.picked.has(i.k+":"+i.id)); el.textContent=deChaseText(deChaseLevel(pk.length?pk:shared.DE.items,SA().chases)); }
export function deExtraHtml(){ if(shared.DE.mode==="chase"){ const pk=shared.DE.items.filter(i=>shared.DE.picked.has(i.k+":"+i.id)), lv=deChaseLevel(pk.length?pk:shared.DE.items,SA().chases);
    return `<div class="dechase" id="deChase">${esc(deChaseText(lv))}</div>`; }
  if(shared.DE.mode!=="followup") return "";
  const owners=[...new Set(shared.DE.items.filter(i=>i.k==="actions").map(i=>i.o).filter(Boolean))];
  return `${shared.DE.note?`<div class="denote">${esc(shared.DE.note)}</div>`:""}${owners.length?`<div class="deopts"><label>Lead with <select id="deLead"><option value="">Attendees in order</option>${owners.map(n=>`<option ${shared.DE.lead===n?"selected":""}>${esc(n)}</option>`).join("")}</select></label></div>`:""}`; }
/* BL-290: with Polish off the row stays, greyed: the tone chips disabled and the Polish button saying why (draftBtn) */
export function dePolishHtml(){ const tone=shared.DE.tone||"neutral", off=!draftOn("email");
  return `<div class="detone${off?" off":""}"><span class="sub">Polish the wording of the opening paragraph:</span>${["warm","neutral","firm"].map(t=>`<button type="button" class="vchip" data-detone="${t}" aria-pressed="${tone===t}"${off?" disabled":""}>${t[0].toUpperCase()+t.slice(1)}</button>`).join("")}${draftBtn("polish","Polish","Reword the opening paragraph only, in this tone; the table, subject and addresses are never touched",'data-depolish="1"')}</div><div id="dePolish" class="depolish">${shared.DE.polish?shared.DE.polish.html:""}</div>`; }
/* redraw the whole popup (first: build it) or just the preview and subject */
export function drawDraftEmail(first){ const em=deBuild(), codes=[...new Set(shared.DE.items.map(i=>i.p))].sort();
  if(first){ dePrevDrop(); const row=i=>{ const w=deDue(i.due,TODAY,S.dueSoon), c=(SA().chases||{})[i.id]; return `<label class="it"><input type="checkbox" data-deit="${i.k}:${esc(i.id)}" ${shared.DE.picked.has(i.k+":"+i.id)?"checked":""}><span>${i.noid?"":esc(i.id)+" · "}${esc(i.t.length>70?i.t.slice(0,69)+"…":i.t)}</span>${shared.DE.outside&&!i.client?'<span class="tag">internal</span>':""}${i.kept?'<span class="tag" data-tip="A line in the minutes only: no work item is made">minutes only</span>':""}<span class="sub">${esc(w.date)}${w.words?" · "+w.words:""}${shared.DE.mode==="chase"&&c?" · "+esc(deChasedWords(c)):""}</span></label>`; };
    const outsideNote=shared.DE.mode==="followup"?(shared.DE.attendees.length?"An attendee's address is outside your own domains":"There are no attendee addresses on record"):shared.DE.email?"This address is outside your own domains":"There's no email address on record";
    putHtml($("#deBody"),`${deModesHtml()}<div class="derow"><label>To</label>${deToHtml()}</div>
      <div class="derow"><label for="deSubj">Subject</label><input type="text" id="deSubj"><button class="mini" id="deCopySubj">Copy</button></div>
      ${shared.DE.outside?`<div class="denote">${outsideNote}, so items that aren't client-visible are unticked and marked internal. Tick any you want to include.${deAiSafe()?" AI suggestions on this email use client-visible items only, and one that brings in anything internal is dropped.":""}</div>`:""}
      ${shared.DE.left?`<div class="denote">${shared.DE.left} item${shared.DE.left===1?"":"s"} left out: marked confidential or restricted, or from a project's documents.</div>`:""}${deExtraHtml()}
      <div class="deinc" id="deInc">${codes.map(c=>`<div class="pph">${esc(pName(c))}</div>${shared.DE.items.filter(i=>i.p===c).sort((a,b)=>deSort(a,b,TODAY)).map(row).join("")}`).join("")}</div>
      <div class="deopts">${shared.DE.mode==="followup"?"":'<label><input type="checkbox" id="deUpd"> Include latest update</label>'}<label>Please reply by <span class="dwrap"><input id="deReply" type="text" readonly data-pick data-min="today" size="10" aria-label="Reply by"><button type="button" class="dbtn" data-cal="deReply" aria-label="Choose a reply-by date">${CALI}</button></span></label></div>
      ${dePolishHtml()}<div id="deNote" class="denote" hidden></div>
      <div id="dePrev" contenteditable="true" role="textbox" aria-multiline="true" aria-label="The email, editable"></div>
      <div class="deacts"><button class="btn primary" id="deCopyHtml">Copy email</button><button class="btn" id="deCopyText">Copy as plain text</button>${shared.DE.mode==="chase"||shared.DE.mode==="update"?`<button class="btn" id="deSent" ${viaServer()?"":"disabled"} data-tip="Log that you sent it: a dated Latest update on each ticked item (the items, names and dates only, never the email)">I sent it</button>`:""}<span class="sp"></span><span class="sub" id="deMsg" aria-live="polite"></span><button class="btn" id="deDone">Close</button></div>`);
    $("#deDone").onclick=()=>$("#deDlg").close(); if(shared.DE.includeUpdate&&$("#deUpd")) $("#deUpd").checked=true; if(shared.DE.replyBy) $("#deReply").value=fd(shared.DE.replyBy); }
  dePrevPut(em.html); shared.DE.edited=false; $("#deNote").hidden=true; if(!shared.DE.subjEdited) $("#deSubj").value=em.subject; }
/* ===== #133 ===== the preview is a host of the shared editor (core/editor.js, features "email"): the same selection bar as the other editors
   (Improve: Rewrite, Shorter, Longer; Tone: More formal, Warmer; Ask…), on text inside one paragraph or cell, so the table and the colours
   are never reshaped. The builder (draftEmail) stays the source (BL-83): the preview shows what it built, `shared.DE.built` is that HTML,
   and what is copied is that HTML until the email is edited, then the editor's document in the same wrapper (deHtml). */
/* #186: the AI bar for an outside recipient. The server decides who the email goes to from its addresses (edit_ai.email_outside: the own
   domains, every address, failing closed), then gives Claude the client-visible items only and drops a suggestion that brings in anything
   internal. The page only asks whether this server does that (/api/edit/ai/caps, until it says yes); until then the bar stays off for an
   outside recipient (#133's interim) and no addresses are sent, so an older server is never asked for something it can't check. The page's
   own `outside` only shows or hides the bar: it is never sent. */
let DE_AI_SAFE=false, deAiAsking=null, deAiNoUntil=0;
const DE_AI_NO_MS=60000;   /* a no (an older server's 404, or an error) is kept a minute, so a redraw doesn't ask again each time */
/** Whether this server decides the email's audience itself (kept once it says yes; a no is asked again after a minute). */
export const deAiSafe=()=>DE_AI_SAFE;
/** Ask the server, once at a time. @returns {Promise<boolean>|null} */
export function deAiCheck(){ if(DE_AI_SAFE||deAiAsking||!viaServer()||Date.now()<deAiNoUntil) return deAiAsking;
  const q=Promise.resolve().then(()=>api("/api/edit/ai/caps",{})).then(r=>(DE_AI_SAFE=!!(r&&r.ok&&r.email_audience==="recipients")),()=>false)
    .then(ok=>{ if(!ok) deAiNoUntil=Date.now()+DE_AI_NO_MS; return ok; });
  deAiAsking=q; q.then(()=>{ if(deAiAsking===q) deAiAsking=null; }); return q; }
/** The addresses the email goes to, as the server judges them: the person's, or every attendee's ("" for anyone with none on record). */
export const deRecipients=()=>{ const d=shared.DE; if(!d) return [""]; return d.mode==="followup"?(d.attendees||[]).map(a=>String(a.email||"")):[String(d.email||"")]; };
/** Put the builder's HTML in the preview: a new editor on first use, else quietly into the one there (not an edit). @param {string} html */
export function dePrevPut(html){ const el=$("#dePrev"); if(!el) return; shared.DE.built=html;
  /* The bar is on for an internal recipient, and for an outside one once the server has said it decides the audience (#186): `enabled`
     is read each time a selection would show the sparkle, so the editor is never rebuilt when the answer comes (a rebuild would take
     the focus and the caret away while you type). With that yes the request carries the addresses (read when you ask, so a follow-up's
     attendees loaded later count); without it none are sent. */
  if(!deAiSafe()) deAiCheck();
  if(el.cxed&&!el.cxed.editor.isDestroyed){ el.cxed.setValue(html); return; }
  creaiteEditor(el,{ features:"email", html, ai:{ place:"email", project:()=>{ const d=shared.DE; return (d&&((d.items&&d.items[0]&&d.items[0].p)||(d.codes&&d.codes[0])))||""; },
    enabled:()=>!!shared.DE&&(!shared.DE.outside||deAiSafe()), recipients:()=>deAiSafe()?deRecipients():null } }); }
/** End the preview's editor (the popup is redrawn or closed), and with it the selection bar over it. */
export function dePrevDrop(){ const el=$("#dePrev"); if(el&&el.cxed) el.cxed.destroy(); }
/** The HTML Copy email puts on the clipboard. An unedited email is the builder's HTML as the browser holds it (what the preview's own
    innerHTML always was: a table with its body, attributes as the parser writes them), byte for byte; an edited one is the editor's document
    inside the builder's wrapper, each cell's lone paragraph unwrapped and every inline style kept. */
export function deHtml(){ const el=$("#dePrev");
  if(shared.DE.edited&&el&&el.cxed&&!el.cxed.editor.isDestroyed) return `<div style="${DE_FONT}color:${DE_COLOURS.ink};background:${DE_COLOURS.white};">${edEmailHtml(el.cxed.editor)}</div>`;
  const t=document.createElement("div"); putHtml(t,shared.DE.built||""); return t.innerHTML; }
/* ===== end #133 ===== */
/* an option changed: redraw the email, unless the person has edited it, in which case ask first (their edits would be lost) */
export function deOptionsChanged(){ if(!shared.DE.edited){ const em=deBuild(); dePrevPut(em.html); if(!shared.DE.subjEdited) $("#deSubj").value=em.subject; return; }
  const n=$("#deNote"); n.hidden=false; putHtml(n,'You\'ve edited the email, so it hasn\'t changed with your last choice. <button class="mini" id="deRedraw">Redraw it (your edits are lost)</button>'); }
export function deSay(btn,msg,ok){ $("#deMsg").textContent=msg; if(ok&&btn) copied(btn); }   /* BL-136: the drawn tick and "Copied" */
/* when the browser refuses the clipboard, select what to copy and say so, never fail silently */
export function deSelect(id){ const el=$("#"+id); if(!el) return; if(el.select){ el.focus(); el.select(); } else { el.focus(); const r=document.createRange(); r.selectNodeContents(el); const g=getSelection(); g.removeAllRanges(); g.addRange(r); } }
export async function deCopyText(text,btn,selectId){ try{ if(!navigator.clipboard||!navigator.clipboard.writeText) throw new Error("no clipboard"); await navigator.clipboard.writeText(text); deSay(btn,"Copied",true); }
  catch(err){ deSelect(selectId); deSay(null,`Your browser blocked copying: press ${MOD}C to copy`); } }
/* what is on screen is what is copied: the preview's own HTML (with any edits) and its text, together, so Outlook pastes the table and the colours */
export async function deCopyEmail(withHtml,btn){ const prev=$("#dePrev"), html=deHtml(), text=shared.DE.edited?prev.innerText:deBuild().text;
  try{ if(!navigator.clipboard) throw new Error("no clipboard");
    if(withHtml){ if(typeof ClipboardItem==="undefined"||!navigator.clipboard.write) throw new Error("no rich clipboard"); await navigator.clipboard.write([new ClipboardItem({"text/html":new Blob([html],{type:"text/html"}),"text/plain":new Blob([text],{type:"text/plain"})})]); }
    else await navigator.clipboard.writeText(text);
    shared.SENTVIA=withHtml?"email":"message";   /* only once the copy has gone through */
    deSay(btn,withHtml?"Copied: paste it into Outlook":"Copied as plain text",true); }
  catch(err){ deSelect("dePrev"); deSay(null,`Your browser blocked copying: press ${MOD}C to copy`); } }
/* ===== v2.3.0 #153 ===== "I sent it" logs the work. In the pane and in this popup it records the chase (chases.json: item IDs, the date and
   the mode, as before) and stages a dated Latest update on each item through the peek's own staging (pkCommit: a proposal already
   approved, source_run dashboard, applied with the others), with one Undo for the batch. A decision's text is its Reasoning, a
   risk's its Response (pkUpdLabel). Never the email's text, only who, when, how and the reply-by date. */
export const sentKindOf=id=>["actions","raid","decisions"].find(k=>REC(k,id));
export const SENT_FIELD={actions:"upd",raid:"resp",decisions:"why"};
/** how Alan sent it: "email" after Copy email / Copy for Outlook, "message" after Copy as text; email when neither. */
export const sentVia=()=>shared.SENTVIA==="message"?"message":"email";
/** The dated line for one item. mode: chase (others' item), update (asking for an update), help (Alan's own item), decision.
    n is the reminder number once recorded; confidential items get the short form (who and how, no detail).
    @param {{today?:string,name:string,via?:string,mode:string,n?:number,replyBy?:string,need?:string,confidential?:boolean}} o */
export function sentLine(o){ const d=fd(o.today||TODAY), via=o.via==="message"?"message":"email", whom=o.name||"them", by=o.replyBy?`; reply asked for by ${fd(o.replyBy)}`:"";
  if(o.confidential) return `${d}: ${o.mode==="update"?"Emailed":"Chased"} ${whom} by ${via}.`;
  if(o.mode==="update") return `${d}: Emailed ${whom} by ${via} asking for an update.`;
  if(o.mode==="help"){ const need=String(o.need||"").replace(/\s+/g," ").replace(/\s+done\.?$/i,"").replace(/\.$/,"").trim().slice(0,80); return `${d}: Asked ${whom} by ${via} for ${need||"help"}.`; }
  if(o.mode==="decision") return `${d}: Asked ${whom} for a decision by ${via}${by}.`;
  return `${d}: Chased ${whom} by ${via}${o.n?` (reminder ${o.n})`:""}${by}.`; }
/** Stage the line on each item (queued in order, each to its own item by ID, so reordering or unticking changes nothing) and offer
    one Undo for the batch. Returns how many were staged.
    @param {{k:string,id:string,need?:string}[]} entries @param {{name:string,mode:string,replyBy?:string,via?:string,chases?:any,sendId?:string,failed?:string[]}} o */
export async function sentLog(entries,o){ let ok=0; const mine=[];   /* the staged entries this press made: Undo removes exactly these */ const via=o.via||sentVia(), ch=o.chases||SA().chases||{}, st=o.sendId?sendState(o.sendId):null, failed=o.failed||[];
  for(const e of entries){ if(st&&st.done.has(e.id)) continue;   /* logged by an earlier press of this same send: never twice */
    const x=REC(e.k,e.id), f=SENT_FIELD[e.k]; if(!x||!f){ failed.push(e.id); continue; }
    const conf=deBarred(deItem(e.k,x)), line=sentLine({name:o.name,via,mode:o.mode,n:(ch[e.id]||{}).n,replyBy:o.replyBy,need:e.need,confidential:conf});
    const was=String(x[f]||"").trim();
    const before=new Set(shared.PKS);
    let good=false; try{ good=await pkCommit(e.k,e.id,{[f]:was?line+"\n"+was:line},"Latest update",was?"…":"none",line,{logNote:"Draft email: I sent it"}); }catch(err){ good=false; }
    if(good){ ok++; if(st) st.done.add(e.id); mine.push(...shared.PKS.filter(s=>!before.has(s)&&s.k===e.k&&s.id===e.id)); } else failed.push(e.id); }
  const bad=failed.length?` Couldn't log ${failed.join(", ")}: press I sent it again to log just those.`:"";
  if(!ok){ if(bad) snack(bad.trim()); return 0; }
  snack((ok===1?"Logged.":`Logged on ${plur(ok,"item")}.`)+bad,async()=>{ for(const s of mine.slice().reverse()) await pkUndoLast(s); });   /* the toast's own Undo button */
  return ok; }
/** One send (one popup, one pane) remembers which items it has recorded and logged, so a retry after a failure repeats only what is missing. */
export function sendState(id){ if(!shared.SENT) shared.SENT={}; if(!shared.SENT[id]) shared.SENT[id]={rec:new Set(),done:new Set()}; return shared.SENT[id]; }
/* "I sent it" in the popup, update and chase modes: one record, then a Latest update on each ticked item */
export async function deSent(btn){ if(!viaServer()){ snack("Recording a chase needs the live server"); return; }
  const picked=shared.DE.items.filter(i=>shared.DE.picked.has(i.k+":"+i.id)); if(!picked.length){ snack("Tick the items you sent it about"); return; }
  if(btn.disabled) return;
  const ids=picked.map(i=>i.id), mode=shared.DE.mode==="update"?"update":"chase", name=shared.DE.name, replyBy=shared.DE.replyBy;
  if(!shared.DE.sendId) shared.DE.sendId="de"+Date.now()+Math.random().toString(36).slice(2,6);
  const sid=shared.DE.sendId, st=sendState(sid), fresh=ids.filter(i=>!st.rec.has(i));
  btn.disabled=true;
  if(fresh.length){ const r=await api("/api/chases",{ids:fresh,mode});
    if(!r.ok){ btn.disabled=false; snack(oneLine(r.message)||"Not recorded"); return; }
    fresh.forEach(i=>st.rec.add(i)); SA().chases=r.chases||{}; }
  const chases=SA().chases||{}, failed=[];
  let n=0; try{ n=await sentLog(picked.map(i=>({k:i.k,id:i.id})),{name,mode,replyBy,chases,sendId:sid,failed}); }
  catch(err){ btn.disabled=false; snack("The update couldn't be logged: press I sent it to try again"); return; }
  if(failed.length){ btn.disabled=false; return; }   /* the popup stays so the missing ones can be retried; sentLog said which */
  if(shared.DE&&shared.DE.name===name&&$("#deDlg")?.open) $("#deDlg").close();
  if(!n&&!st.done.size) snack(`Recorded on ${plur(ids.length,"item")}`);
  if(shared.VIEW==="person"&&shared.PERSON) renderPerson(shared.PERSON); }
/* Polish the wording: the model rewords the opening paragraph only (the table, subject and addresses never go to it); its version is
   shown beside the original, and Use this puts it in the email */
export function deCover(){ const b=draftEmail({...deBuildArgs(),cover:""}); return (b.text.split("\n")[2]||"").trim(); }
export const deBuildArgs=()=>({mode:shared.DE.mode,name:shared.DE.name,email:shared.DE.email,items:shared.DE.items,picked:shared.DE.picked,includeUpdate:shared.DE.includeUpdate,replyBy:shared.DE.replyBy,now:new Date(),today:TODAY,dueSoon:S.dueSoon,
  names:{},from:"",chased:SA().chases||{},title:shared.DE.title,day:shared.DE.day,codes:shared.DE.codes,attendees:shared.DE.attendees,lead:shared.DE.lead,summary:shared.DE.summary});
/* One Polish run for the Draft email and the Draft email pane (BL-298): the kind's switch first (draftWhyNot; {ok:false, why} when
   it is off, with no run), then draftAsk. kind "polish" rewords the opening only; "polish-help" (Alan's own item in the pane) also
   suggests To get … done and What I need from you. */
export async function polishAsk(body,o={}){ const why=draftWhyNot(body.kind); if(why) return {ok:false,why:true,message:why};
  return draftAsk(body,{label:"Polishing the wording",...o}); }
/* The pane's Tone (First, Second, Firmer) as Polish's tone: a first reminder warm, a second neutral, a firmer one firm. */
export const POLISH_TONES=["warm","neutral","firm"];
export async function dePolish(){ const why=draftWhyNot("polish"); if(why){ snack(why); return; }
  const de=shared.DE, text=de.cover||deCover(), tone=de.tone||"neutral", host=()=>$("#dePolish");
  const res=await polishAsk({kind:"polish",text,tone},{status:h=>{ if(shared.DE===de) putHtml(host(),h?`<div class="drstatus" role="status">${h}</div>`:""); }});
  if(shared.DE!==de){ if(res.ok&&!res.nothing) draftStat("email","rejected"); return; }
  if(!res.ok||res.nothing){ putHtml(host(),""); snack(res.nothing||res.message||"No draft came back"); return; }
  de.polish={d:res,html:`<div class="drcard" role="region" aria-label="Polished wording"><div class="drhead">${ic("spark")}<b>Polished, ${esc(tone)}</b><span class="sub">The table, subject and addresses are unchanged.</span></div><div class="sub">Yours</div><div class="drtext">${esc(text)}</div><div class="sub" style="margin-top:6px">Polished</div>${draftTextHtml(res)}<div class="drfoot"><span class="sp"></span><button type="button" class="btn" data-depo="discard">Keep mine</button><button type="button" class="btn primary" data-depo="use">Use this</button></div></div>`};
  putHtml(host(),de.polish.html); }
export function dePolishDo(what){ const p=shared.DE.polish; shared.DE.polish=null; putHtml($("#dePolish"),"");
  if(what!=="use"){ draftStat("email","rejected"); return; }
  draftStat("email","used"); shared.DE.cover=p.d.text; deOptionsChanged(); }
/* the person page says when an item was last chased */
export function chaseNote(x){ const c=SA().chases||{}, L=[...x.oa,...x.or].filter(i=>c[i.id]); if(!L.length) return "";
  return `<span class="sub" id="ppChased">${L.slice(0,3).map(i=>`${esc(i.id)} ${esc(deChasedWords(c[i.id]).toLowerCase())}`).join("; ")}${L.length>3?` and ${L.length-3} more`:""}</span>`; }
/* ===== end BL-224 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootDrafts0129(){
document.addEventListener("input",e=>{ if(!shared.DE) return; if(e.target.id==="dePrev") shared.DE.edited=true; else if(e.target.id==="deSubj") shared.DE.subjEdited=true;
  else if(e.target.id==="deReply"){ shared.DE.replyBy=DDATE.test(e.target.value)?toIso(e.target.value):""; deOptionsChanged(); } });
document.addEventListener("change",e=>{ if(!shared.DE) return; const t=e.target;
  if(t.dataset&&t.dataset.deit){ t.checked?shared.DE.picked.add(t.dataset.deit):shared.DE.picked.delete(t.dataset.deit); if(shared.DE.mode==="chase") deChaseLine(); deOptionsChanged(); }
  else if(t.id==="deUpd"){ shared.DE.includeUpdate=t.checked; deOptionsChanged(); }
  else if(t.id==="deLead"){ shared.DE.lead=t.value; deOptionsChanged(); } });
document.addEventListener("click",e=>{ if(!shared.DE) return; const t=e.target;
  if(t.closest("#deRedraw")){ shared.DE.subjEdited=false; const em=deBuild(); dePrevPut(em.html); shared.DE.edited=false; $("#deSubj").value=em.subject; $("#deNote").hidden=true; return; }
  const md=t.closest("[data-demode]"); if(md&&!md.disabled&&md.dataset.demode!==shared.DE.mode){ openDraftEmail(shared.DE.name,md.dataset.demode,shared.DE.only); return; }
  const tn=t.closest("[data-detone]"); if(tn){ shared.DE.tone=tn.dataset.detone; $$("[data-detone]").forEach(x=>x.setAttribute("aria-pressed",x===tn)); return; }
  if(t.closest("[data-depolish]")){ dePolish(); return; }
  const pu=t.closest("[data-depo]"); if(pu&&shared.DE.polish){ dePolishDo(pu.dataset.depo); return; }
  if(t.closest("#deSent")){ deSent(t.closest("#deSent")); return; }
  if(t.closest("#deCopyTo")) deCopyText(shared.DE.mode==="followup"?shared.DE.attendees.map(a=>a.email).filter(Boolean).join("; "):shared.DE.email,$("#deCopyTo"),"deTo");
  else if(t.closest("#deCopySubj")) deCopyText($("#deSubj").value,$("#deCopySubj"),"deSubj");
  else if(t.closest("#deCopyHtml")) deCopyEmail(true,$("#deCopyHtml"));
  else if(t.closest("#deCopyText")) deCopyEmail(false,$("#deCopyText")); });
document.addEventListener("click",e=>{ const b=e.target.closest("[data-defollow]"); if(b){ e.preventDefault(); e.stopPropagation(); openFollowup(b.dataset.defollow); } },true);
}
/* ===== BL-157 (sprint-ux) ===== fixes from the one-off UX sweep (each under an hour; the rest are BL-165 onwards):
   an empty Activity and an empty Projects page say what to do next (baseline check 6), and Quick capture's unsent note was kept
   in this browser (check 3; the capture drawer, BL-301 C, keeps its drafts on the server now). */
/* ===== end BL-157 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootDrafts0160(){
}
/* ===== AI drafts: the scaffold (sprint-drafts-fields; used by drafts-extraction and drafts-writing) =====
   A draft is a suggestion, never a write: it lands in an unsaved field, a pending proposal or a dialog, and nothing is saved, applied
   or sent without Alan. Plain code on the server (drafts.py) chooses the facts and their sources; the model only words them, through
   the run engine (POST /api/draft, kind "generate": one run at a time, progress and Stop). The pieces, for each draft kind:
   - DRAFTFEATURES: the switches (settings.json `drafting.<feature>`, on when missing), listed in Settings › Advanced › AI drafts.
   - DRAFTKIND: kind → feature (the server's DRAFT_KINDS and drafts.py's @kind name the same kinds).
   - draftBtn(kind, word, tip, attrs): the one Draft button (the spark icon and a word, BL-158). Off or with no live server it is
     greyed (aria-disabled) and its tooltip says why; a click then says so too (draftWhyNot).
   - draftAsk(body, {label, status, url?, onStep?, onSources?}): runs the draft (url: another streamed route, BL-286's /api/prep/shape) and resolves to {ok, text, sentences, sources, …} (the "draft" event),
     {ok:true, nothing:"Nothing new since …"} (no model call), {stopped} or {message}. status(html) shows progress and Stop.
   - draftCardHtml(d, {title, use, extra, from}): the card: the text with each sentence's sources (a sentence with no source is marked
     "no source"), "Drafted from n sources" (Generate's .gensrc mark) with each source and Open for a file, Discard and Use.
   - draftStat(feature, event): counts used, edited and rejected in system/staging/draft-stats.json (offered is counted by the
     server when a draft comes back). Counts only. */
export const DRAFTFEATURES=[["update","Draft the latest update","An action's latest update from what happened since the last one, and Draft updates for actions with no recent update"],
  ["client","Draft client wording","Plain client messaging from the item's own text, with what was taken out"],
  ["thinking","Suggest the thinking fields","A decision's options and reasoning; a risk's response, impact and likelihood"],
  ["reason","Draft the reason for a health or forecast change","One sentence from the evidence creaite already holds"],
  ["repeat","Spot repeats of existing items","Marks a proposal that looks like an item already in the tracker; Merge, Keep or Reject in Review"],   /* BL-221 (sprint-drafts-extraction) */
  ["done","Spot items that are probably done","The sweep and the minutes propose closing an open item when a sent mail, reply or meeting shows it finished"],   /* BL-218 */
  ["sharpen","Sharpen a vague action","A clear, verb-first title for a vague action, beside the original; you pick one"]];   /* BL-220 */
export let DRRUN=null;
export function draftWhyNot(kind){ const f=DRAFTKIND[kind]||kind, name=(DRAFTFEATURES.find(x=>x[0]===f)||[])[1]||"Drafting";
  return !draftOn(f)?`${name} is off in Settings › Advanced › AI drafts`:!viaServer()?`${name} needs the live server`:DRRUN?"A draft is being written; wait for it or stop it":""; }
export function draftBtn(kind,word,tip,attrs=""){ const why=draftWhyNot(kind);
  return `<button type="button" class="drbtn" data-draft="${kind}" ${attrs} aria-label="${esc(word)}" data-tip="${esc(why||tip)}"${why?' aria-disabled="true"':""}>${ic("spark")}<span>${esc(word)}</span></button>`; }
export function draftStat(feature,event,n=1){ if(feature&&viaServer()) api("/api/draft/stat",{feature,event,n}).catch(()=>{}); }
export async function draftAsk(body,o={}){ const status=o.status||(()=>{});
  if(DRRUN) return {ok:false,message:"A draft is already being written"};
  if(shared.RUN||shared.GEN.run||shared.BUSY||shared.PREPRUN) return {ok:false,message:"ask creaite is busy; try again when it's finished"};
  if(!viaServer()) return {ok:false,message:"Drafting needs the live server"};
  const id=`d-${Date.now().toString(36)}-${Math.random().toString(36).slice(2,8)}`, ctl=new AbortController(); DRRUN={id,ctl};
  let steps=0, res, started=false; const out={said:[]};
  const show=()=>status(`<span class="spin" aria-hidden="true"></span><span>${esc(o.label||"Drafting with Claude")}${steps?` · ${steps} step${steps===1?"":"s"}`:""}</span><button type="button" class="mini" data-drstop>Stop</button>`);
  shared.RBOUT=""; show();
  try{
    try{ res=await fetch(o.url||"/api/draft",{method:"POST",signal:ctl.signal,headers:{"Content-Type":"application/json","X-Creaite-Token":D.token},body:JSON.stringify({...body,run:id})}); }   /* o.url: BL-296's /api/alerts/draft */
    catch(e){ return {ok:false,message:"The live server isn't reachable"}; }
    if(!res.ok||!res.body||(res.headers.get("Content-Type")||"").includes("json")){ const j=await res.json().catch(()=>({}));
      return {ok:!!j.ok&&!!j.nothing,nothing:j.nothing||"",off:!!j.off,confidential:!!j.confidential,message:res.status===404&&j.message==="Not found"?OLDSERVER:oneLine(j.message||"")||"The draft couldn't be started"}; }
    started=true; rbStart(o.label||"Drafting with Claude");
    const rd=res.body.getReader(), dec=new TextDecoder(); let buf="";
    for(;;){ let c; try{ c=await rd.read(); }catch(e){ out.stopped=true; break; } if(c.done) break; buf+=dec.decode(c.value,{stream:true}); let i;
      while((i=buf.indexOf("\n\n"))>=0){ const ch=buf.slice(0,i); buf=buf.slice(i+2); if(!ch.startsWith("data: ")) continue; let ev; try{ ev=JSON.parse(ch.slice(6)); }catch(e){ continue; }
        if(ev.type==="step"){ steps++; show(); if(o.onStep) o.onStep(steps); } else if(ev.type==="stopped") out.stopped=true; else if(ev.type==="error") out.message=ev.message;
        else if(ev.type==="sources"){ out.sources=ev.sources; if(o.onSources) o.onSources(ev); } else if(ev.type==="text"&&ev.text) out.said.push(ev.text);
        else if(ev.type==="draft"){ const {type,...d}=ev; Object.assign(out,d,{got:true}); } } }
    api("/api/ask/ack",{run:id}).catch(()=>{});
    if(out.stopped){ shared.RBOUT="stopped"; return {ok:false,stopped:true,message:"Stopped; nothing changed"}; }
    if(out.got&&out.nothing){ shared.RBOUT="done"; return {ok:true,nothing:String(out.nothing)}; }   /* #272: the reply had nothing to suggest: no text, so no field is filled */
    if(!out.got||(!out.text&&!out.items&&!out.prefill&&!(out.health&&out.reason))){ shared.RBOUT="failed"; return {ok:false,message:out.message||"No draft came back",length_notes:out.length_notes||[]}; }
    out.ok=true; return out;
  } finally{ DRRUN=null; status(""); if(started) rbEnd(shared.RBOUT||"done"); shared.RBOUT=""; } }
export function draftTextHtml(d){ const src=d.sources||[], S2=d.sentences||[];
  if(!S2.length) return `<div class="drtext">${esc(d.text||"")}</div>`;
  return `<div class="drtext">${S2.map(s=>s.unsourced?`<mark class="drloose">${esc(s.text)}</mark><span class="drtag" role="note">no source</span>`
    :`<span>${esc(s.text)}</span>${s.refs.map(r=>`<sup class="drref" data-tip="${esc((src.find(x=>x.ref===r)||{}).text||r)}">${esc(r)}</sup>`).join("")}`).join(" ")}</div>`; }
export function draftSrcHtml(d,open,word){ const L=d.sources||[]; if(!L.length) return "";
  return `<details class="gensrc drsrc"${open?" open":""}><summary>${esc(word||"Drafted from")} ${L.length} source${L.length===1?"":"s"}</summary><ol class="drsl">${L.map(s=>`<li><b>${esc(s.ref)}</b> ${esc(s.text)}${s.path?` <a href="#" class="hlink" data-dropen="${esc(s.path)}">Open</a>`:""}</li>`).join("")}</ol></details>`; }
export function draftCardHtml(d,o={}){ const loose=d.unsourced||0;
  return `<div class="drcard" role="region" aria-label="${esc(o.title||"Draft")}"><div class="drhead">${ic("spark")}<b>${esc(o.title||"Draft")}</b><span class="sub">A suggestion. Nothing is saved until you use it and save it.</span></div>
    ${draftTextHtml(d)}${loose?`<div class="drnote">${loose} sentence${loose===1?" has":"s have"} no source: check ${loose===1?"it":"them"} before you use the draft.</div>`:""}
    ${o.extra||""}${draftSrcHtml(d,false,o.from)}
    <div class="drfoot"><span class="sp"></span><button type="button" class="btn" data-drdo="discard">Discard</button><button type="button" class="btn primary" data-drdo="use">${esc(o.use||"Use this")}</button></div></div>`; }
export async function drStatsLoad(){ if(!viaServer()) return; const r=await api("/api/drafts",{}); const el=$("#drStats"); if(!el||!r.ok) return;
  const st=r.stats||{}, rows=DRAFTFEATURES.map(([f,l])=>{ const c=st[f]||{}; return c.offered?`<tr><td>${esc(l)}</td><td>${c.offered} offered · ${c.used||0} used · ${c.edited||0} edited · ${c.rejected||0} rejected</td></tr>`:""; }).join("");
  putHTML(el,rows?html`<table><caption class="vh">How each kind of draft has been used</caption>${raw(rows)}</table>`:html`No drafts offered yet.`); }
/* ===== end AI drafts: the scaffold ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootDrafts0196(){
Object.assign(ICONS,{spark:ICONS.spark||SPARKI});
document.addEventListener("click",e=>{ if(e.target.closest("[data-drstop]")&&DRRUN){ api("/api/ask/stop",{run:DRRUN.id}).then(r=>{ if(!r.ok&&DRRUN) DRRUN.ctl.abort(); }); } });
document.addEventListener("click",async e=>{ const a=e.target.closest("[data-dropen]"); if(!a) return; e.preventDefault();
  if(!viaServer()){ snack("Opening a file needs the live server"); return; } const r=await api("/api/open",{path:a.dataset.dropen}); if(!r.ok) snack(oneLine(r.message)||"Couldn't open it"); });
/* Settings › Advanced › AI drafts: a switch per feature, and what Alan has done with each kind of draft (from draft-stats.json) */
SETSECTIONS.splice(SETSECTIONS.findIndex(s=>s.id==="appearance")+1,0,{id:"drafts",cat:"general",title:"AI drafts",
  kw:"ai drafts draft suggest model claude latest update stale client wording messaging reasoning options response impact likelihood health forecast reason counts used rejected",
  render:()=>`<p class="sub" style="margin:0 0 4px">A draft is a suggestion, never a save: it fills a field, a proposal in Review or a box for you to edit. creaite picks the facts; Claude only words them. Each needs the live server.</p>`
    +DRAFTFEATURES.map(([f,l,h])=>row(l,`<input type="checkbox" class="switch" data-drsw="${f}" ${draftOn(f)?"checked":""} aria-label="${esc(l)}">`,h)).join("")
    +`<div class="drstats" id="drStats">${viaServer()?"":"How often each kind of draft is used shows here while the live server runs."}</div>`,
  after:()=>drStatsLoad()});
$("#settingsBody").addEventListener("change",async e=>{ const el=e.target.closest&&e.target.closest("[data-drsw]"); if(!el) return; const f=el.dataset.drsw, v=el.checked;
  if(!await writeSettings({["drafting."+f]:v})){ el.checked=!v; return; } S.drafting={...(S.drafting||{}),[f]:v}; });
}
/* ===== BL-227 (sprint-drafts-writing) ===== one set of facts, many forms. Generate's Form: Current state (as before: into the editor,
   saved only by Save) or a Steering note, a Three-line update, an Email paragraph or a Teams message, for an audience (Internal,
   Client-safe, Steering committee, Sponsor). The other forms are written from the same ranked facts sheet on the run engine (the
   draft kind "status-form", which /api/current/generate also takes as `form`), shown in the dialog with each sentence's sources and
   a length check, and copied: never saved. */
export let GENFM=null;                                         /* the form drafted in the Generate dialog: {d, form, used} */
export const GEN_FIXEDLEN={three:"Three lines, at most 60 words",email:"One paragraph, at most 120 words",teams:"At most 50 words"};
/* BL-290: with Forms off the other forms are greyed (aria-disabled, saying why) and a remembered one falls back to Current state */
export function genFormOptions(){ const off=!draftOn("forms"); if(off&&shared.GEN.form!=="current") shared.GEN.form="current";
  const cur=shared.GEN.form==="current", why=off?draftWhyNot("status-form"):"", fx=GEN_FIXEDLEN[shared.GEN.form]||"", len=$("#genLen");
  /* #110: one hint line under the strip follows the Form and the Audience (was a note under each) */
  $("#genHint").textContent=`${cur?`Into the editor, for you to edit and save.${why?` The other forms: ${why[0].toLowerCase()+why.slice(1)}.`:""}`:"Shown here to copy; never saved."} ${GEN_AUDNOTE[shared.GEN.aud]||""}`.trim();
  if(fx) len.setAttribute("aria-disabled","true"); else len.removeAttribute("aria-disabled"); len.title=fx;   /* Length dims for a form that fixes it, with the reason on hover */
  const h=$("#genDlg h2"); if(h) h.textContent=cur?"Generate current state":`Write ${/^[aeiou]/i.test(GEN_FORMS.find(x=>x[0]===shared.GEN.form)[1])?"an":"a"} ${GEN_FORMS.find(x=>x[0]===shared.GEN.form)[1].toLowerCase().replace(/^teams/,"Teams")}`;
  genFooter(); if(!GENFM||GENFM.form!==shared.GEN.form) putHtml($("#genOut"),""); }
/* #110: after a draft starts the setup folds to one summary line with Change settings; the footer is then Close and a plain Generate again
   (Copy on the card is the one primary). The DOM is the state: the summary line shows while it is folded. */
export const genFolded=()=>!$("#genSum").hidden;
function genFooter(){ const fold=genFolded(), cur=shared.GEN.form==="current";
  $("#genGoT").textContent=fold?"Generate again":cur?"Generate":"Write it"; $("#genGo").classList.toggle("primary",!fold); $("#genCancel").textContent=fold?"Close":"Cancel"; }
export function genFold(){ const [form,...rest]=genSummary(), el=$("#genSumTxt"), b=document.createElement("b"); b.textContent=form;
  el.replaceChildren(b,document.createTextNode(` · ${rest.join(" · ")}`)); $("#genSum").hidden=false;
  if($("#genSetup").contains(document.activeElement)) $("#genChange").focus();      /* focus never drops to the page behind the dialog when the setup folds */
  $("#genSetup").hidden=true; genFooter(); }
/* back to a new dialog: setup showing, no draft (an unused one counts as rejected), Draw on folded, not busy. Change settings, Discard, closing and opening do this */
export function genReset(){ GENSEQ++;                      /* a draft still being written belongs to the dialog as it was: it is stopped and its result is never shown */
  if(GENCALL&&DRRUN){ const r=DRRUN; api("/api/ask/stop",{run:r.id}).then(x=>{ if(!x.ok) r.ctl.abort(); }); }
  if(GENFM&&!GENFM.used) draftStat("forms","rejected"); GENFM=null; putHtml($("#genOut"),""); refineUnmount();   /* every version goes with the draft */
  $("#genSetup").hidden=false; $("#genSum").hidden=true; genBusy(false); genFooter(); }
function genBusy(on){ if(on) $("#genGo").setAttribute("aria-disabled","true"); else $("#genGo").removeAttribute("aria-disabled"); }
export function genFormCard(d,v){ const name=(GEN_FORMS.find(x=>x[0]===d.form)||[])[1]||"Status", aud=(GEN_AUD.find(x=>x[0]===d.audience)||[])[1]||"", loose=d.unsourced||0;
  return `<div class="drcard" role="region" aria-label="${esc(name)}" tabindex="-1"><div class="drhead">${ic("spark")}<b>${esc(name)}</b><span class="sub">${esc(aud)} · not saved: copy it where you need it</span>${v&&v.n>1?versBarHtml(v.at,v.n,"gver"):""}</div>
    ${genFormText(d)}${loose?`<div class="drnote">${loose} sentence${loose===1?" has":"s have"} no source: check ${loose===1?"it":"them"} before you use it.</div>`:""}
    ${(d.length_notes||[]).length?`<div class="drnote" role="note">${d.length_notes.map(esc).join(" ")}</div>`:`<div class="drnote">${d.words} words.</div>`}${draftSrcHtml(d,false,"Written from")}
    <div class="drfoot"><span class="sp"></span><button type="button" class="btn" data-gfdo="discard">Discard</button><button type="button" class="btn" data-gfdo="plain">Copy as plain text</button>${d.form==="teams"?"":'<button type="button" class="btn primary" data-gfdo="rich">Copy</button>'}</div><div class="sub" id="gfMsg" role="status"></div></div>`; }
/* the form's text with each sentence's sources, its **bold** and "- " bullets shown as they will read; a line per sentence where the
   form is made of lines (the steering note, the three-line update) */
export function genFormText(d){ const src=d.sources||[], lines=d.form==="steering"||d.form==="three", fmt=t=>esc(t.replace(/^[-*]\s+/,"• ")).replace(/\*\*(.+?)\*\*/g,"<b>$1</b>");
  const one=x=>x.unsourced?`<mark class="drloose">${fmt(x.text)}</mark><span class="drtag" role="note">no source</span>`:`<span>${fmt(x.text)}</span>${x.refs.map(r=>`<sup class="drref" data-tip="${esc((src.find(y=>y.ref===r)||{}).text||r)}">${esc(r)}</sup>`).join("")}`;
  return `<div class="drtext">${(d.sentences||[]).map(one).join(lines?"<br>":" ")}</div>`; }
let GENSEQ=0, GENCALL=false;                                   /* which dialog session a draft belongs to; a form draft is being written */
export async function genFormDraft(body){ const out=$("#genOut"), why=draftWhyNot("status-form"); if(why){ snack(why); return; }
  if(GENFM&&!GENFM.used) draftStat("forms","rejected"); GENFM=null; refineUnmount(); const form=shared.GEN.form, mine=++GENSEQ;   /* a new draft: the old one's refine box and versions go */
  genFold(); genBusy(true);                                  /* #110: the setup folds to its summary while it is written; Generate again waits */
  let res; GENCALL=true; try{ res=await draftAsk({kind:"status-form",...body,form},{label:"Writing it from the facts",status:h=>{ if(mine===GENSEQ) putHtml(out,h?`<div class="drstatus" role="status">${h}</div>`:""); }}); }
  finally{ GENCALL=false; if(mine===GENSEQ) genBusy(false); }
  if(mine!==GENSEQ){ if(res.ok&&!res.nothing) draftStat("forms","rejected"); return; }   /* the dialog was closed, reset or opened again meanwhile: this draft is not its own, and was never used */
  if(res.nothing){ putHtml(out,`<div class="drnone" role="status">${ic("spark")}<span>${esc(res.nothing)}</span></div>`); return; }
  if(!res.ok){ putHtml(out,""); genReset(); snack(res.message||"No draft came back"); return; }   /* a failure gives the setup back */
  GENFM={d:res,form,used:false,edited:false,body:{...body},vers:[res],at:0}; putHtml(out,genFormCard(res,{at:0,n:1})); refineMount(body.audience==="client"); out.querySelector(".drcard")?.focus?.(); }
export async function genFormCopy(rich,btn){ const d=GENFM.d, html=d.form==="steering"?mdHtml(d.text):d.text.split(/\n+/).map(x=>`<p>${esc(x)}</p>`).join("");
  try{ if(!navigator.clipboard) throw new Error("no clipboard");
    if(rich){ if(typeof ClipboardItem==="undefined"||!navigator.clipboard.write) throw new Error("no rich clipboard"); await navigator.clipboard.write([new ClipboardItem({"text/html":new Blob([html],{type:"text/html"}),"text/plain":new Blob([d.text],{type:"text/plain"})})]); }
    else await navigator.clipboard.writeText(d.text);
    copied(btn); $("#gfMsg").textContent="Copied"; }
  catch(err){ $("#gfMsg").textContent=`Your browser blocked copying: select the text and press ${MOD}C`; return; }
  if(!GENFM.used){ GENFM.used=true; draftStat("forms","used"); } }
/* ===== #110 B: Steer it further. Under a form's result in the Generate dialog, and under the unsaved Current state draft in the cockpit
   editor (projects.js curRefine): a box, four starters that append a sentence, Refine (⌘↵). A refine is the draft kind "status-form"
   asked again on the run engine with the previous version (`text`) and the change (`note`): the facts are worked out again for the same
   period and audience, so a version draws on exactly what the first did, and the server keeps only sourced sentences for any audience
   but Internal. Each is a new version; Back and On move between them; Discard, closing and Change settings drop them all. Nothing is
   saved or sent by a refine; the editor's Save is the only save. ===== */
export const REFINE_TEXT_MAX=1500, REFINE_NOTE_MAX=500, REFINE_INS_MAX=300;      /* what /api/draft takes for `text` and `note`; the change itself, leaving room for the first steer */
export const REFINE_STARTERS=[["shorter","Shorter","Make it shorter."],["plainer","Plainer words","Use plainer words."],["decision","Lead with the decision","Lead with the decision."],["risks","Add the risks","Add the risks."]];
export function refineNote(ins,steer){ ins=String(ins||"").replace(/\s+/g," ").trim().slice(0,300); const first=String(steer||"").replace(/\s+/g," ").trim(), room=REFINE_NOTE_MAX-ins.length-27;
  return first&&room>20?`${ins} (The first steer was: ${first.slice(0,room)})`:ins; }
export function versBarHtml(at,n,attr){ return `<span class="vers" role="group" aria-label="Versions">Version ${at+1} of ${n}${at>0?` · <button type="button" class="genlink" data-${attr}="back">Back to version ${at}</button>`:""}${at<n-1?` · <button type="button" class="genlink" data-${attr}="next">On to version ${at+2}</button>`:""}</span>`; }
export const refineStatusHtml=h=>h?`<div class="drstatus" role="status">${h}</div>`:"";
const REFINE_NOT_CLIENT="Steer it further is not available for a Client-safe draft yet.";      /* the server refuses it too (drafts.py REFINE_NOT_CLIENT) */
export function refineHtml(scope,o={}){ const cur=scope==="cur";
  if(o.client) return `<div class="genref" id="${scope}Refine" data-refine-off="${scope}"><div class="drnote" role="note">${esc(REFINE_NOT_CLIENT)}</div></div>`;
  return `<div class="genref" id="${scope}Refine" data-refine="${scope}"><label for="${scope}RefineNote">Steer it further <span class="sub">Each change makes a new version. ${cur?"Nothing is saved until you press Save.":"Nothing is saved or sent."}</span></label>
    <textarea id="${scope}RefineNote" rows="2" placeholder="For example: shorter, lead with the decision, leave out the overdue actions">${esc(o.note||"")}</textarea>
    <div class="genrow"><span class="sub">Try:</span><span class="genstarts">${REFINE_STARTERS.map(([k,l])=>`<button type="button" class="genlink" data-rstart="${k}">${esc(l)}</button>`).join(" ")}</span><span class="sp"></span>${cur?'<span id="curVers"></span>':""}<button type="button" class="btn" id="${scope}RefineGo" data-refinego="${scope}"${o.busy?' aria-disabled="true"':""}>Refine<span class="kbd" aria-hidden="true">${MOD}↵</span></button></div>
    <div id="${scope}RefineWork" aria-live="polite">${refineStatusHtml(o.status)}</div><div id="${scope}RefineMsg">${o.msg?`<div class="drnote" role="note">${esc(o.msg)}</div>`:""}</div></div>`; }
/* one refine on the run engine: the new version's draft, or null (the reason shown) */
export async function refineAsk(o){ const why=draftWhyNot("status-form"); if(why){ snack(why); return null; }
  const ins=String(o.ins||"").replace(/\s+/g," ").trim();
  if(ins.length>REFINE_INS_MAX){ snack(`A change can be ${REFINE_INS_MAX} characters at most; yours is ${ins.length}. Shorten it.`); return null; }
  if(o.text.length>REFINE_TEXT_MAX){ snack(`This draft is over ${REFINE_TEXT_MAX} characters, more than a refine can take. Shorten it first.`); return null; }
  const b=o.body, res=await draftAsk({kind:"status-form",code:b.code,from:b.from,to:b.to,audience:b.audience,length:b.length,form:o.form,text:o.text,note:refineNote(ins,b.note)},
    {label:`Refining version ${o.fromV} into version ${o.toV}…`,status:o.status});
  if(res.nothing){ snack(res.nothing); return null; }
  if(!res.ok){ const n=(res.length_notes||[]).join(" "); snack(n?`${n} No new version was made.`:res.message||"No new version came back"); return null; }   /* the server's count of what it left out, when there is one */
  return res; }
export function refineMount(client){ const h=$("#genRefineHost"); if(!h) return; putHTML(h,raw(refineHtml("gen",{client:!!client}))); h.hidden=false; }
export function refineUnmount(){ const h=$("#genRefineHost"); if(!h) return; putHTML(h,raw("")); h.hidden=true; }
let GENREF=false;                                              /* a refine is being written in the dialog */
export async function genRefine(){ const g=GENFM; if(!g||GENREF||!$("#genDlg").open) return; const box=$("#genRefineNote"), ins=box.value.trim();
  if(!ins){ snack("Say what to change first, or pick one of the quick ones."); box.focus(); return; }
  GENREF=true; GENCALL=true; $("#genRefineGo").setAttribute("aria-disabled","true"); genBusy(true);   /* GENCALL: closing or Change settings stops it */
  let res=null; try{ res=await refineAsk({body:g.body,form:g.form,text:g.vers[g.at].text,ins,fromV:g.at+1,toV:g.vers.length+1,status:h=>{ const el=$("#genRefineWork"); if(el&&GENFM===g) putHtml(el,refineStatusHtml(h)); }}); }
  finally{ GENREF=false; GENCALL=false; if(GENFM===g) genBusy(false); $("#genRefineGo")?.removeAttribute("aria-disabled"); }
  if(GENFM!==g||!$("#genDlg").open||!res) return;              /* closed or discarded while it was written, or it failed: nothing changes */
  g.vers.push(res); g.at=g.vers.length-1; g.d=res; if(!g.edited){ g.edited=true; draftStat("forms","edited"); }   /* a refine is an edit of the same draft */
  box.value=""; putHtml($("#genOut"),genFormCard(res,{at:g.at,n:g.vers.length})); box.focus(); }   /* focus stays in the box, so ⌘↵ goes on refining and never regenerates */
export function genVersion(way){ const g=GENFM; if(!g||GENREF) return; const at=g.at+(way==="next"?1:-1); if(at<0||at>=g.vers.length) return;
  g.at=at; g.d=g.vers[at]; putHtml($("#genOut"),genFormCard(g.d,{at,n:g.vers.length})); $("#genOut .drcard")?.focus?.(); }
/* ===== end #110 B ===== */
/* ===== end BL-227 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootDrafts0202(){
DRAFTFEATURES.push(["forms","Write the status in other forms","Generate's Form: a steering note, a three-line update, an email paragraph or a Teams message"]);
Object.assign(DRAFTKIND,{"status-form":"forms"});
$("#genDlg").addEventListener("click",e=>{ const b=e.target.closest("[data-gfdo]"); if(!b||!GENFM) return; e.preventDefault();
  if(b.dataset.gfdo==="discard"){ genReset(); $("#genDays").focus(); return; }
  genFormCopy(b.dataset.gfdo==="rich",b); });
$("#genDlg").addEventListener("close",()=>{ closePicker("owner",false); genReset(); });
/* #110 B: by data attribute, from the dialog or the editor: a starter appends its sentence to its own box; Refine; Back and On */
document.addEventListener("click",e=>{ const st=e.target.closest("[data-rstart]");
  if(st){ const box=st.closest("[data-refine]")?.querySelector("textarea"), x=REFINE_STARTERS.find(a=>a[0]===st.dataset.rstart); if(!box||!x) return;
    const v=box.value.replace(/\s+$/,""); box.value=(v?v+" ":"")+x[2]; box.dispatchEvent(new Event("input",{bubbles:true})); box.focus(); return; }
  const rg=e.target.closest("[data-refinego]"); if(rg){ e.preventDefault(); if(rg.getAttribute("aria-disabled")==="true") return; if(rg.dataset.refinego==="cur") curRefine(); else genRefine(); return; }
  const gv=e.target.closest("[data-gver]"); if(gv){ e.preventDefault(); genVersion(gv.dataset.gver); return; }
  const cv=e.target.closest("[data-cver]"); if(cv){ e.preventDefault(); curVersion(cv.dataset.cver); } });
onCmdEnter("refine",t=>!!(t&&t.closest&&t.closest("[data-refine]")),()=>{ const sc=document.activeElement&&document.activeElement.closest&&document.activeElement.closest("[data-refine]");
  if(!sc) return; if(sc.dataset.refine==="cur") curRefine(); else genRefine(); });
CMDENTER.unshift(CMDENTER.pop());                       /* its own key, before the dialog's "generate" and the editor's save */
}
/* ===== BL-224 (sprint-drafts-writing) ===== Polish the wording's switch and kind (the email modes are in the Draft email block, above) */
/* ===== end BL-224 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootDrafts0203(){
Object.assign(DRAFTKIND,{"report-section":"report-section","minutes-section":"minutes-section"});   /* #90: the sheet's ✦ */
DRAFTFEATURES.push(["report-section","Redraft a report section","The weekly or client report's ✦, and Polish, Shorter, Executive or your own words on one section, from the week's facts (a client report: client-visible facts only)"],
  ["minutes-section","Redraft a minutes section","The minutes' ✦, and Polish, Shorter, Executive or your own words on one section (the distributed version: nothing marked Internal only or withheld)"]);
Object.assign(DRAFTKIND,{polish:"email","polish-help":"email"});   /* BL-298: the chase pane's Polish for Alan's own item */
DRAFTFEATURES.push(["email","Polish the email wording","Draft email's opening paragraph reworded in a warm, neutral or firm tone; the table, subject and addresses are untouched"]);
}
/* ===== BL-220 (sprint-drafts-extraction) ===== Sharpen on capture. When an action is typed (the new-item form, ⌘K's "add an action",
   Quick capture) plain code offers chips, never set until clicked: Owner (a named person from the register, or "I'll…" as you), Due
   (from the words, through parseWhen), Workstream and Milestone (named in the words, else as the closest past item in the project was
   filed) and Priority (urgent, asap, critical; important). A click changes that one field: the peek's own staging (pkCommit), ⌘K's
   pending change, or a clause added to the note's line in Quick capture. A vague title (under four words, or no verb: plain code, as
   extraction.vague) offers Sharpen (drafts.py kind "sharpen", the run engine): a verb-first title beside the original, Use or
   Discard; the original is kept (as_proposed, BL-232, for a proposal). Review marks a vague new action as shaky (BL-208) with Sharpen. */
export const SHVERBS=new Set(("accept add agree align allocate amend analyse analyze appoint approve arrange ask assess assign attend audit book brief build buy "
  +"call cancel capture chase check circulate clarify close collect complete confirm consolidate contact create decide define deliver "
  +"deploy design develop discuss document draft email engage ensure escalate estimate evaluate examine explore extend finalise "
  +"finalize find fix follow forward gather get give hand hire hold identify implement improve inform install integrate investigate "
  +"invite issue launch lead list look make manage map meet merge migrate monitor move negotiate notify obtain onboard organise "
  +"organize outline pay plan prepare present prioritise prioritize produce provide publish raise reach read receive reconcile record "
  +"reduce refine register release remind remove renew replace reply report request research reschedule resolve respond restart "
  +"review revise run schedule scope secure select send set share sign source specify start submit summarise summarize supply "
  +"support test track train transfer update upgrade upload validate verify visit write").split(" "));
export function vagueWhy(t){ const w=String(t||"").match(/[A-Za-z][A-Za-z'-]*/g)||[]; if(w.length<4) return "under four words";
  return w.some(x=>SHVERBS.has(x.toLowerCase())||SHVERBS.has(x.toLowerCase().replace(/s$/,"")))?"":"no verb"; }
export const chWords=t=>new Set((String(t||"").toLowerCase().match(/[a-z0-9]+/g)||[]).filter(w=>w.length>2&&!["the","and","for","with","from","this","that","into","about","will"].includes(w)));
export function chSimilar(t,code){ const mine=chWords(t); let /** @type {any} */ best=null;
  A.filter(a=>a.p===code&&(a.ws||a.ms)).forEach(a=>{ const th=chWords(a.t), n=[...mine].filter(w=>th.has(w)).length, sc=n/Math.max(mine.size,th.size||1); if(n>=2&&sc>=0.4&&(!best||sc>best.sc)) best={a,sc}; });
  return best&&best.a; }
export function chDue(t){ const m=String(t).match(/\b(?:by|on|before|due|until)\s+((?:the\s+)?[\w-]+(?:\s+[\w-]+){0,2})/i)||String(t).match(/\b(today|tomorrow|next week|end of (?:the )?(?:week|month)|eow|eom)\b/i); if(!m) return null;
  const w=m[1].split(/\s+/); for(let n=w.length;n>0;n--){ const iso=parseWhen(w.slice(0,n).join(" "),TODAY,true); if(iso) return iso; } return null; }
export function chOwner(t){ if(/\b(I'll|I will|I'm going to|I am going to|I can)\b/i.test(t)) return S.me; const low=String(t).toLowerCase();
  const hit=personPool().pool.find(p=>[p.name,...(p.aliases||[])].some(n=>n&&n.length>2&&new RegExp(`\\b${n.toLowerCase().replace(/[.*+?^${}()|[\]\\]/g,"\\$&")}\\b`).test(low))); return hit?hit.name:null; }
/* the chips for an action's words in a project: [{f, v, label, why}], only for fields not set yet (have) */
export function capChips(t,code,have={}){ const out=[], low=String(t||"").toLowerCase(), add=(f,v,label,why)=>{ if(v&&String(have[f]||"")!==String(v)&&!(f==="o"&&have.o&&have.o!=="TBC")&&!(f!=="pr"&&f!=="o"&&have[f])) out.push({f,v,label,why}); };
  if(!t||String(t).trim().length<3) return out;
  add("o",chOwner(t),`Owner: ${chOwner(t)}`,"named in the words");
  const due=chDue(t); add("due",due,`Due: ${fd(due)}`,"from the words");
  if(code){ const ws=wsFor(code).find(n=>low.includes(n.toLowerCase())), ms=msChoices(code).find(m=>m[1]&&low.includes(String(m[1]).toLowerCase())), sim=chSimilar(t,code);
    add("ws",ws||(sim&&sim.ws),`Workstream: ${ws||(sim&&sim.ws)}`,ws?"named in the words":`as ${sim&&sim.id} was filed`);
    const msv=ms?ms[0]:sim&&sim.ms; add("ms",msv,`Milestone: ${ms?ms[1]:((D.milestone_names||{})[msv]||[msv])[0]}`,ms?"named in the words":`as ${sim&&sim.id} was filed`); }
  const pr=/\b(urgent|asap|critical|blocker|immediately)\b/.test(low)?"Urgent":/\b(important|high priority)\b/.test(low)?"High":null; add("pr",pr,`Priority: ${pr}`,"from the words");
  return out; }
/* BL-316: the suggested fields are Chip building blocks (class capchip), drawn into their row with drawChips */
export function capChipsDraw(host,chips,onPick){ drawChips(host,chips.map((c,i)=>({cls:"capchip","data-chip":String(i),title:`Suggested ${c.why}; click to set it`,children:`+ ${c.label}`,
  onClick:e=>{ e.preventDefault(); e.stopPropagation(); onPick(c); }}))); }
export function pkChipsDraw(){ const list=$("#pkChips .pkchipl"), x=shared.CUR&&curObj(); if(!list) return; const on=x&&shared.CUR.k==="actions"&&shared.CUR.mode==="new";
  const sb=$("#pkChips [data-draft=sharpen]"), tt=x?String((shared.CUR.mode==="new"?pkNewTitle():"")||x.t||"").trim():""; if(sb) sb.hidden=!tt||!vagueWhy(tt);   /* only while the title is vague */
  capChipsDraw(list,on?capChips(pkNewTitle()||x.t,x.p,{o:x.o===S.me?"":x.o,due:x.due,ws:x.ws,ms:x.ms,pr:x.pr}):[],c=>{ const y=curObj(); if(!y) return; pkCommit(shared.CUR.k,pkCid(),{[c.f]:c.v},PKFL[c.f]||pkLabel(shared.CUR.k,c.f,y),c.f==="due"?fd(y[c.f])||"none":y[c.f]||"none",c.f==="due"?fd(c.v):c.v); }); }
/* Review: a new action with a vague title is shaky (staging marks it); Sharpen opens the proposal and asks */
export function shRvHtml(r){ if(!r||r.done||r.kind!=="actions"||(S.drafting&&S.drafting.sharpen===false)||!(r.inferred||[]).some(x=>x.field==="description")) return "";   /* not draftOn: Review can draw before the scaffold loads */
  return ` · <button type="button" class="linkbtn" data-shrv="${r.n}">Sharpen</button>`; }
/* ⌘K: chips under "add an action" (a click sets that field on the change before Enter stages it), and a note for a vague title */
export function ckChipsHtml(c){ if(c.k!=="actions"||!c.new) return ""; c.chips=capChips(c.new.t,c.new.p,{...c.new,o:c.new.o==="TBC"?"":c.new.o,pr:""}).filter(x=>!(x.f==="pr"&&x.v===c.new.pr));
  const v=vagueWhy(c.new.t);
  return `${c.chips.length?`<div class="ckchips" role="group" aria-label="Suggested fields">${c.chips.map((x,i)=>`<button type="button" class="chip capchip" data-ckchip="${i}" title="Suggested ${esc(x.why)}; click to set it">+ ${esc(x.label)}</button>`).join("")}</div>`:""}${v?`<div class="sub ckvague">The title is vague (${esc(v)}): write what is to be done, or stage it and Sharpen it in the item.</div>`:""}`; }
/* ===== end BL-220 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootDrafts0204(){
Object.assign(DRAFTKIND,{sharpen:"sharpen"});
/* the peek: chips and Sharpen under a new action's title */
{ const host=document.createElement("div"); host.id="pkChips"; host.className="pkchips"; const list=document.createElement("span"); list.className="pkchipl"; list.setAttribute("role","group"); list.setAttribute("aria-label","Suggested fields"); host.append(list); $("#pkTitle").after(host); }
PKDRAW.push(()=>pkChipsDraw());
$("#pkTitle").addEventListener("input",()=>{ if(shared.CUR&&shared.CUR.mode==="new") pkChipsDraw(); });
PKDRBTN.push((x,k,mode)=>k==="actions"&&(mode==="new"||mode==="proposal")&&vagueWhy(mode==="new"?pkNewTitle()||x.t:x.t)?[{f:"t",kind:"sharpen",word:"Sharpen",tip:"This title is vague: suggest a clear, verb-first one beside it"}]:[]);
PKDRBODY.sharpen=x=>{ const t=String($("#pkTitle").textContent||x.t||"").trim(); if(shared.CUR.mode!=="proposal") return {kind:"sharpen",title:t,code:x.p||""};
  const r=pkRev(); return r?{kind:"sharpen",title:t,proposal:{file:r.file,ref:r.ref}}:null; };
PKDRTITLE.sharpen=()=>"Sharpened action";
PKDREXTRA.sharpen=d=>`<div class="drnote"><b>As written:</b> ${esc(d.original||"")}${d.why?` · ${esc(d.why)}`:""}</div>`;
document.addEventListener("click",e=>{ const b=e.target.closest("[data-shrv]"); if(!b) return; e.preventDefault(); e.stopPropagation();
  const why=draftWhyNot("sharpen"); if(why){ snack(why); return; } openProposal(+b.dataset.shrv);
  setTimeout(()=>{ const t=$('#pkChips [data-draft="sharpen"]'); if(t) t.click(); else snack("This title isn't vague any more"); },0); },true);
document.addEventListener("click",e=>{ const b=e.target.closest("#cmdk [data-ckchip]"); if(!b) return; e.preventDefault(); e.stopPropagation();
  const it=shared.CK[shared.CKI], c=it&&it.change, ch=c&&c.chips&&c.chips[+b.dataset.ckchip]; if(!ch||!c.new) return; c.new[ch.f]=ch.v; drawCk(); $("#cmdkIn").focus(); },true);
}
