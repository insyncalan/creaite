// @ts-check
/* panel.js (BL-231 step 2b), moved from script/ by dev/tools/convert_area.py: 0046-detail-panel.js, 0047-bl-154-sprint-ux.js, 0048-after-bl-154.js, 0049-bl-260-fix-minutes-draft.js, 0050-after-bl-260.js, 0165-bl-176-sprint-peek.js, 0166-bl-176-sprint-peek.js, 0167-bl-176-sprint-peek.js, 0168-bl-176-sprint-peek.js, 0169-bl-176-sprint-peek.js, 0170-bl-250-fix-history-feed.js, 0171-after-bl-250.js, 0173-bl-177-sprint-peek.js, 0174-bl-175-sprint-peek.js, 0175-bl-179-sprint-peek-new.js, 0176-bl-179-sprint-peek-new.js, 0177-bl-179-sprint-peek-new.js, 0178-bl-179-sprint-peek-new.js, 0179-bl-180-sprint-peek-new.js, 0181-bl-185-sprint-peek-new.js, 0182-bl-187-fix-peek-140.js, 0183-bl-188-fix-peek-140.js, 0194-bl-198-sprint-review-work.js, 0197-bl-219-sprint-drafts-fields.js, 0198-bl-225-sprint-drafts-fields.js, 0199-bl-222-sprint-drafts-fields.js, 0200-bl-226-sprint-drafts-fields.js.
   Unchanged apart from `export`, `shared.` for the shared state (core/state.js) and the load-time steps, now in
   boot…() functions that src/main.js calls in today's order. */
import { drawPeekNotes } from "./notes.js";
import { linkWords } from "./core/linkText.js";
import { actHref, actId } from "./activity.js";
import { closeChat, openChat, send } from "./ask.js";
import { A, DEC, open, P, peopleAll, pName, R, REV, wsFor } from "./core/data.js";
import { CHASE_ICON, mountChase, unmountChase } from "./components/peek/ChasePane.jsx";
import { closeMenu, menuOpenFor, openMenu } from "./components/Menu.jsx";
import { closePicker, openPicker, pickerOpenFor } from "./components/Picker.jsx";
import { openNewWorkstream } from "./components/peek/NewWorkstream.jsx";
import { drawTabs } from "./components/Tabs.jsx";
import { statusDotNodes } from "./components/StatusDot.jsx";
import { peekMark, peekPropNodes } from "./components/peek/PeekProps.jsx";
import { $, $$, addHTML, esc, html, ibtn, ic, ICONS, putHTML, raw } from "./core/dom.js";
import { creaiteEditor } from "./core/editor.js";
import { linkAnchor, linkUrl, unescHtml } from "./core/linkUrl.js";
import { typing } from "./core/keys.js";
import { comboboxOpen } from "./components/Combobox.jsx";
import { CALI, DATE_HELP, formProject, itemDatePicker, mountOwnerFields, onCmdEnter, openPath, ownerMatches, parseWhen, projFirst, projPeople, srcHTML, weekendNote, WK, wkAsk, wkMark } from "./core/fields.js";
import { irHold } from "./core/irFold.js";
import { EDITABLE, irChanged, irIfApproved, irLabel, irNowRow, irSaveChanges, irUpdateList, irWord, UI } from "./core/irUpdate.js";
import { drawLast, drawLatestWas, drawUpdateBody, updateChipNodes, updateChips } from "./components/intakeReview/UpdatePeek.jsx";
import { mDotGo } from "./core/motion.js";
import { go, navWrite } from "./core/nav.js";
import { cmdOK, cmHeads, cmOK, CMT, copied, D, DATE, days, DDATE, fd, isMe, MOD, mScroll, nowStamp, OPENST, prio, S, store, TODAY, toIso } from "./core/page.js";
import { api, applyNow, applySoon, DIAG, editProposal, FIELD, memPath, needVault, oneLine, refreshAll, reloadData, replaceCurrent, save, snack, stampFile, stampFull, toDb, undoApply, viaServer, vq, writeProposal } from "./core/server.js";
import { shared } from "./core/state.js";
import { ovAdd, ovDrop, ovReapply, savingIds } from "./core/instant.js";
import { hsAsk, hsCardHtml, hsSparkHtml, hsStat, hsUse } from "./healthSuggest.js";
import { draftAsk, draftBtn, draftCardHtml, draftStat, draftWhyNot } from "./drafts.js";
import { pdDrop, pdKeyOf, pdOffer, pdRaw, pdWhen, pKeysShow } from "./help.js";
import { decisionCheck, decisionFields, decLate, decShort } from "./meetings.js";
import { feedBlock, feedLines, feedListHtml, feedTabItems, mountFeedTabs, msLinked, msPanelSave, msRemove, msSave, projFeedItems } from "./milestones.js";
import { closePanel, curGuard, depFormDraw, depHash, depSugDraw, depSuggest, DRAFTKIND, PK, PKN, pkOn, WARNS, warnsOf, WICO } from "./projects.js";
import { decide, isMin, llNoteHtml, rejectMinutes, rjMenuFor, rtNoteHtml, rvDup, rvRejectOK } from "./review.js";
import { alertStage, alertStaged, isHiddenPerson, nm, ownerFinal, personLink, PKAPPLIED, regAddAlias, row, sl, sw, tx, WS_FIELDS, wsConfirm, WSD, wsNewOf, wsRow, wsSuggest } from "./settings.js";
import { isConflict, pkAdd, plur, renderToday } from "./today.js";
import { bkItems, FX, HL, hlOrder, hlPaint, isStale, items, kOfId, layoutOf, msOpts, NEG, PROJF, rvPaint } from "./work.js";
/* ======================= detail panel ======================= */
shared.CUR=null; shared.EDITING=false;
export const REC=(k,id)=>(k==="actions"?A:k==="raid"?R:DEC).find(x=>x.id===id);
export const RESPL=t=>t==="Issue"?"Resolution action":t==="Assumption"?"Validation action":t==="Dependency"?"Management action":"Mitigation action";
export function fieldsFor(k,x){ const F=(()=>{ const projOpts=P.map(p=>[p.code,p.name]);
  /* optional milestone link (BL-11): blank, or one of the project's milestones */
  const msOpts=msChoices(x.p,x.ms);
  if(k==="actions") return [["t","Action","area"],["p","Project","sel",projOpts],["ws","Workstream","ws"],["o","Owner","owner"],["pr","Priority","sel",["Urgent","High","Medium","Low"]],["due","Due date","date"],["st","Status","sel",["Open","Delayed","Closed","Cancelled"]],["raised","Raised","date"],["closed","Closed","date"],["upd","Latest update","area"],["ms","Milestone","sel",msOpts],["#","Client messaging"],["client","Client-visible","check"],["cm","Client messaging","cm"]];
  if(k==="raid") return [["t","Description","area"],["type","Type","sel",["Risk","Issue","Assumption","Dependency"]],["p","Project","sel",projOpts],["ws","Workstream","ws"],["o","Owner","owner"],["resp",RESPL(x.type),"area"],["imp","Impact","sel",["High","Medium","Low"]],["lik","Likelihood","sel",["High","Medium","Low"]],["pr","Priority","calc"],["due","Due date","date"],["st","Status","sel",["Open","Closed","Cancelled"]],["raised","Raised","date"],["closed","Date closed","date"],["ms","Milestone","sel",msOpts],["#","Client messaging"],["client","Client-visible","check"],["cm","Client messaging","cm"]];
  if(k==="decisions") return decisionFields(x,projOpts);   /* BL-53: status, needed by, reasoning, options, revisit, replaces */
  if(k==="update") return [["target","Item","ro"],["from","Current value","ro"],["to",x.field==="status"?"Status":"Proposed value",x.field==="status"?"sel":"text",["Open","Delayed","Closed","Cancelled"]]];
  if(k==="project") return [["health","Health","sel",["On track","At risk","Off track"]],["reason","Health reason","area"]];
  if(k==="milestone") return shared.CUR.mode==="rebase"?[["fc","New baseline (and forecast)","date"],["with","Agreed with (full names, separated by commas)","text"],["reason","Reason for rebaselining","area"]]
    :[["name","Milestone","text"],["desc","Description","area"],["fc",shared.CUR.mode==="msnew"?"Date (baseline and forecast)":"Forecast date","date"],["st","Status","sel",["Planned","Done"]],["pc","% complete","pct"],["ord","Order","text"],...(shared.CUR.mode==="msnew"?[]:[["base","Baseline","ro"]])];
  return []; })();
  if(!PANELF||!MOREF[k]) return F;
    const more=new Set(MOREF[k]), main=[], rest=[]; let inMore=false;
    for(const f of F){ if(f[0]==="#"){ inMore=f[1]==="Client messaging"||(k==="decisions"&&false); (inMore?rest:main).push(f); continue; } (more.has(f[0])?rest:main).push(f); }
    if(k==="decisions"){ const i=main.findIndex(f=>f[0]==="#"&&f[1]==="Reasoning"); if(i>=0&&!main.slice(i+1).some(f=>f[0]!=="#")) main.splice(i,1); }
    return rest.length?[...main,["#",MOREMARK],...rest]:main; }
/* ===== BL-154 (sprint-ux) ===== the edit panel shows the fields that matter. An action, a RAID item or a decision opens with the
   fields that are changed most; the rest sit under More fields, which opens by itself when one of them has a value (beyond the
   defaults every item has) or a validation message, or when it is the field asked for. The fields keep their order inside each
   part, so the keyboard order is the order on screen; readForm, validation, ⌘↵ and Esc are unchanged (they read every field
   wherever it sits), and inline cell edits are untouched (they don't use the panel).
   Actions: Action, Project, Owner, Priority, Due date, Status, Latest update | Workstream, Raised, Closed, Milestone, Client messaging.
   RAID: Description, Type, Project, Owner, the response, Impact, Likelihood, Priority, Due date, Status | Workstream, Raised,
   Date closed, Milestone, Client messaging. Decisions: Decision, Project, Status, Decision maker, Needed by, Date made, Source,
   Reasoning | Options considered, Revisit, Replaces, Client messaging. */
export const MOREF={actions:["ws","raised","closed","ms","client","cm"],raid:["ws","raised","closed","ms","client","cm"],decisions:["opts","revisit","replaces","rby","client","cmd"]};
export const MOREMARK="⁣More fields";
export let PANELF=false, MOREOPEN={};                 /* MOREOPEN: kept open while the same record is redrawn */
export function moreHasValue(k,x){ const v=n=>x&&x[n]!=null&&x[n]!==""&&x[n]!==false;
  return MOREF[k].some(n=>n==="cm"?(x.client&&x.cm&&x.cm!==CMT):n==="cmd"?!!(x.client&&x.cmd):n==="raised"?false:n==="client"?!!x.client:v(n)); }
export function morePanel(focusField){ const dl=$("#pFields"), k=shared.CUR&&shared.CUR.k; if(!dl||!MOREF[k]) return;
  const mark=[...dl.querySelectorAll(":scope>.fsec")].find(e=>e.textContent===MOREMARK); if(!mark) return;
  const active=document.activeElement, key=`${shared.CUR.mode}:${k}:${shared.CUR.id||shared.CUR.n||"new"}`, x=curObj();
  const det=document.createElement("details"); det.className="morefields"; putHTML(det,html`<summary>More fields</summary>`);
  const box=document.createElement("dl"); box.className="fgrid"; det.appendChild(box);
  for(let n=mark.nextElementSibling;n&&!(n.classList.contains("fsec")&&n.textContent!=="Client messaging"&&n.textContent!==MOREMARK)&&!n.classList.contains("evidence");){ const nx=n.nextElementSibling; box.appendChild(n); n=nx; }
  mark.replaceWith(det);
  const n=[...box.querySelectorAll("dt")].length; det.querySelector("summary").textContent=`More fields (${n})`;
  det.open=!!MOREOPEN[key]||moreHasValue(k,x)||(focusField&&MOREF[k].includes(focusField))||!!box.querySelector(".bad");
  det.querySelector("summary").addEventListener("click",()=>setTimeout(()=>{ MOREOPEN[key]=det.open; }));   /* only Alan's own opening is remembered */
  if(active&&box.contains(active)) active.focus(); }
/* ===== end BL-154 ===== */
export const msName=id=>{ const m=(D.milestone_names||{})[id]; return m?`${m[0]} (${id})${m[1]==="Cancelled"?" (cancelled)":""}`:id; };
/* BL-27: milestone pickers show names (the ID stays the value): the project's own, in timeline order; a linked
   Cancelled one stays visible, marked; alike names get their date */
export function msChoices(code,cur){ const L=(P.find(p=>p.code===code)||{ms:[]}).ms.filter(m=>m[3]).map(m=>[m[3],m[0],m[1]]), N=D.milestone_names||{};
  if(cur&&!L.some(m=>m[0]===cur)&&N[cur]) L.push([cur,N[cur][0]+(N[cur][1]==="Cancelled"?" (cancelled)":""),N[cur][2]]);
  const dup=n=>L.filter(m=>m[1].toLowerCase()===n.toLowerCase()).length>1;
  return [["","None"],...L.map(([id,n,d])=>[id,dup(n)&&d?`${n} · ${fd(d)}`:n])]; }
/* BL-22: Current state is Markdown in CLAUDE.md (paragraphs, **bold**, *italic*, "- " and "1. " lists) */
/* Current state is Markdown in CLAUDE.md (BL-22, BL-47): paragraphs, "### ", "#### " and "##### " headings (#122), "> " quotes, "- " and "1. "
   lists nested two spaces per level, **bold**, *italic*, ~~strikethrough~~ and [links](web or mail address). The same subset is
   rendered here, in the Word reports (docx_tools.py) and read back from Word. */
export const MD_LIST=/^( *)(?:([-*•])|(\d+)[.)])\s+(.*)$/, MD_MAX=3, MD_IMG=/^\s*!\[([^\]\n]*)\]\(([^)\s]+)\)\s*$/;
/* BL-89: Current state's two panes are one message, stored with this line between them; a text without it is the left pane.
   Everything but the editor reads the two as one continuous piece (mdBlocks drops the line). */
export const PANE="<!-- creaite: second pane -->";
/* A marker inside another HTML comment (a note that quotes it, as the project template's guidance does) is text, not a split
   (Alan, 13-10-2026). Comments are counted as they open and close. Kept in step with docx_tools.pane_markers.
   @param {string} t @returns {number[]} where each real marker starts */
export function paneMarkers(t){ t=String(t||""); const out=[]; let depth=0, i=0;
  for(;;){ const o=t.indexOf("<!--",i), c=t.indexOf("-->",i); if(o<0&&c<0) return out;
    if(o>=0&&(c<0||o<c)){ if(!depth&&t.startsWith(PANE,o)){ out.push(o); i=o+PANE.length; continue; } depth++; i=o+4; }
    else { depth=Math.max(0,depth-1); i=c+3; } } }
/** @param {string} t @returns {Set<number>} the lines (split at "\n") that are a real marker standing on its own */
export function paneLines(t){ t=String(t||""); const real=new Set(paneMarkers(t)), out=new Set(); let at=0;
  t.split("\n").forEach((line,n)=>{ if(line.trim()===PANE&&real.has(at+line.indexOf(PANE))) out.add(n); at+=line.length+1; }); return out; }
export function splitPanes(t){ t=String(t||""); const ms=paneMarkers(t); if(!ms.length) return [t.trim(),""];
  const cuts=ms.concat([t.length]); let right=""; for(let k=0;k<ms.length;k++) right+=t.slice(cuts[k]+PANE.length,cuts[k+1]);
  return [t.slice(0,ms[0]).trim(),right.replace(/\n{3,}/g,"\n\n").trim()]; }
export function joinPanes(l,r){ l=String(l||"").trim(); r=String(r||"").trim(); return r?(l?l+"\n\n":"")+PANE+"\n\n"+r:l; }
/* #122 C: a work-item link, `[ABC-A-012 · Action: title](creaite:item/ABC-A-012)`, reads as its words and opens the item; a click is handled by the delegate below */
export function mdInline(t){ const kept=[], keep=h=>{ kept.push(h); return "\u0001"+(kept.length-1)+"\u0001"; };
  /* the emphasis pass (bold, strike, italic); finished links are held out as placeholders so it never reaches an anchor's attributes (#159) */
  const emph=s=>s.replace(/\*\*(.+?)\*\*/g,"<b>$1</b>").replace(/~~(.+?)~~/g,"<s>$1</s>")
    .replace(/(^|[^\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])/g,"$1<i>$2</i>").replace(/(^|[^\w])_(?!\s)(.+?)(?<!\s)_(?!\w)/g,"$1<i>$2</i>");
  const s=esc(String(t??"").split("\u0001").join("")).replace(/\[([^\]\n]+)\]\(creaite:item\/([A-Za-z0-9-]{3,30})\)/g,(m,a,id)=>keep(`<a href="#" class="itemref" data-oi="${id}">${emph(a)}</a>`))
    .replace(/\[([^\]\n]+)\]\(([^)\s]+)\)/g,(m,a,u)=>{ const h=a.includes("\u0001")?null:linkAnchor(unescHtml(u),emph(a)); return h?keep(h):m; });   /* the one validator and anchor: core/linkUrl.js */
  return emph(s).replace(new RegExp("\u0001(\\d+)\u0001","g"),(m,n)=>kept[+n]??""); }
export function mdBlocks(text){ const /** @type {any[]} */ B=[]; let para=[], quote=[];
  const flush=()=>{ if(para.length){ B.push(["p",para.join(" ")]); para=[]; } if(quote.length){ B.push(["q",quote.join(" ")]); quote=[]; } };
  const marks=paneLines(text), lines=String(text||"").split("\n").concat([""]);
  for(let n=0;n<lines.length;n++){ const line=lines[n]; if(marks.has(n)){ flush(); continue; } const im=line.match(MD_IMG); if(im){ flush(); B.push(["img",[im[1].trim(),im[2]]]); continue; } const m=line.match(MD_LIST);
    if(m){ flush(); const item=[Math.min(Math.floor(m[1].length/2),MD_MAX),m[2]===undefined,m[4].trim()], last=B[B.length-1];
      const tops=last&&last[0]==="list"?last[1].filter(i=>i[0]===0):[];
      if(tops.length&&!(item[0]===0&&tops[tops.length-1][1]!==item[1])) last[1].push(item); else B.push(["list",[item]]); }
    else if(!line.trim()) flush();
    else if(line.startsWith("### ")){ flush(); B.push(["h",line.slice(4).trim()]); }
    else if(line.startsWith("#### ")){ flush(); B.push(["h2",line.slice(5).trim()]); }       /* #122: the two deeper levels (Heading 2, Heading 3) */
    else if(line.startsWith("##### ")){ flush(); B.push(["h3",line.slice(6).trim()]); }
    else if(line.trimStart().startsWith(">")){ if(para.length) flush(); quote.push(line.trimStart().slice(1).trim()); }
    else { if(quote.length) flush(); para.push(line.trim()); } }
  return B; }
export function listHtml(items){ let h=""; const stack=[];
  items.forEach(([lv,ord,t])=>{ const tag=ord?"ol":"ul";
    while(stack.length>lv+1) h+=`</li></${stack.pop()}>`;
    if(stack.length===lv+1&&stack[lv]!==tag) h+=`</li></${stack.pop()}>`;
    else if(stack.length===lv+1) h+="</li>";
    while(stack.length<lv+1){ h+=`<${tag}>`; stack.push(tag); }
    h+=`<li>${mdInline(t)}`; });
  while(stack.length) h+=`</li></${stack.pop()}>`; return h; }
/* BL-63: images sit in Current state where Alan placed them; imgs is the project's embedded images ({ref, src}) */
export const imgSrc=(imgs,ref)=>String(ref).startsWith("new:")?((shared.CURED&&shared.CURED.uploads||{})[ref.slice(4)]||{}).src:((imgs||[]).find(i=>i.ref===ref)||{}).src;
export const figHtml=(cap,ref,src)=>`<figure class="cimg" data-ref="${esc(ref)}">${src?`<img src="${src}" alt="${esc(cap)}">`:`<div class="sub">Image not found: ${esc(ref)}</div>`}<figcaption>${esc(cap)}</figcaption></figure>`;
export function mdHtml(text,imgs){ return mdBlocks(text).map(([k,b])=>k==="img"?figHtml(b[0],b[1],imgSrc(imgs,b[1])):k==="p"?`<p>${mdInline(b)}</p>`:k==="h"?`<h3>${mdInline(b)}</h3>`:k==="h2"?`<h4>${mdInline(b)}</h4>`:k==="h3"?`<h5>${mdInline(b)}</h5>`:k==="q"?`<blockquote>${mdInline(b)}</blockquote>`:listHtml(b)).join(""); }
export function htmlToMd(root){ const blocks=[]; let cur="";
  const inl=n=>{ if(n.nodeType===3) return n.nodeValue.replace(/ /g," ").replace(/\s+/g," "); if(n.nodeType!==1) return ""; const tag=n.tagName;
    if(tag==="UL"||tag==="OL") return ""; const inner=[...n.childNodes].map(inl).join("");
    if(tag==="BR") return " "; const w=(m)=>{ const t=inner.trim(); if(!t) return inner; const lead=inner.match(/^\s*/)[0], trail=inner.match(/\s*$/)[0]; return lead+m+t+m+trail; };
    const st=n.style||{};
    if(tag==="A"){ const href=n.getAttribute("href")||""; const u=linkUrl(href); return u&&inner.trim()?`[${inner.trim()}](${u})`:inner; }
    if(tag==="B"||tag==="STRONG"||+st.fontWeight>=600||st.fontWeight==="bold") return w("**");
    if(tag==="I"||tag==="EM"||st.fontStyle==="italic") return w("*");
    if(tag==="S"||tag==="STRIKE"||tag==="DEL"||/line-through/.test(st.textDecoration||"")||/line-through/.test(st.textDecorationLine||"")) return w("~~");
    return inner; };
  const flat=t=>t.replace(/\s+/g," ").trim();
  const listMd=(el,lv,out)=>{ let i=0; for(const c of el.children){
      if(c.tagName==="UL"||c.tagName==="OL"){ listMd(c,lv+1,out); continue; }   /* Chrome's indent: a list beside the items */
      if(c.tagName!=="LI") continue; i++; const t=flat(inl(c)); if(t) out.push("  ".repeat(Math.min(lv,MD_MAX))+(el.tagName==="UL"?"- ":`${i}. `)+t);
      [...c.children].filter(x=>x.tagName==="UL"||x.tagName==="OL").forEach(x=>listMd(x,lv+1,out)); } return out; };
  const flush=()=>{ const t=flat(cur); if(t) blocks.push(t); cur=""; };
  const walk=el=>{ for(const n of el.childNodes){ const tag=n.nodeType===1?n.tagName:"";
    if(tag==="UL"||tag==="OL"){ flush(); const lines=listMd(n,0,[]); if(lines.length) blocks.push(lines.join("\n")); }
    else if(/^H[1-6]$/.test(tag)){ flush(); const t=flat(inl(n)); if(t) blocks.push(("#".repeat(Math.min(+tag[1],3)+2))+" "+t); }   /* #122: H1 is ###, H2 ####, H3 and deeper #####, Current state's three levels */
    else if(tag==="BLOCKQUOTE"){ flush(); const t=flat(inl(n)); if(t) blocks.push("> "+t); }
    else if(tag==="FIGURE"&&n.dataset.ref){ flush(); const c=flat((n.querySelector("figcaption")||{}).textContent||"").replace(/[\[\]]/g,""); blocks.push(`![${c}](${n.dataset.ref})`); }
    else if(/^(P|DIV|LI|SECTION|ARTICLE)$/.test(tag)){ flush(); walk(n); flush(); }
    else cur+=inl(n); } };
  walk(root); flush(); return blocks.join("\n\n"); }
export function viewVal(n,t,v,x){ if(t==="dref") return v?`<a href="#" data-open="decisions:${esc(v)}">${esc(v)}</a>`:'<span class="sub">—</span>'; if(n==="p") return v?esc(pName(v)):'<span class="sub">—</span>'; if(n==="ms") return v?esc(msName(v)):'<span class="sub">None</span>'; if(t==="check") return v?"Yes":"No"; if(t==="date") return v?fd(v):'<span class="sub">—</span>'; if(t==="cmd") return x.client||v?(v?esc(v):'<span class="tag warn">To write</span>'):'<span class="sub">Only needed if client-visible</span>'; if(n==="o") return personLink(v); if(n==="by") return personLink(v,v); if(t==="cm"){ if(!x.client&&!cmOK(v)) return '<span class="sub">Only needed if client-visible</span>'; return esc(v); } if(t==="calc") return esc(prio(x.imp,x.lik)); return v?esc(v):'<span class="sub">—</span>'; }
export function editCtl(n,t,v,opts){ const id="f_"+n;
  if(t==="sel") return `<select name="${n}" id="${id}">${(opts||[]).map(o=>Array.isArray(o)?`<option value="${esc(o[0])}" ${o[0]===(v||"")?"selected":""}>${esc(o[1])}</option>`:`<option ${o===v?"selected":""}>${o}</option>`).join("")}</select>`;   /* [value,label] options show the label */
  if(t==="area") return `<textarea name="${n}" id="${id}">${esc(v)}</textarea>`;
  if(t==="pct") return `<span style="display:flex;gap:8px;align-items:center;flex-wrap:wrap"><input type="number" name="${n}" id="${id}" value="${esc(v??"")}" min="0" max="100" step="5" style="width:90px" placeholder="—"><button type="button" class="mini" id="pcClear">Clear</button><span class="sub" id="pcCalc">${shared.CUR.draft.calc!=null?`Calculated: ${shared.CUR.draft.calc}%`:"No linked actions to calculate from"}</span></span><div class="sub" id="pcHint"></div>`;
  if(t==="file") return `<input type="file" id="${id}" accept="image/png,image/jpeg">`;
  if(t==="cm") return `<textarea name="${n}" id="${id}" rows="4">${esc(v||CMT)}</textarea>`;
  if(t==="cmd") return `<textarea name="${n}" id="${id}" rows="3" placeholder="Plain wording for the client — no fixed headings">${esc(v||"")}</textarea>`;
  if(t==="date") return `<span class="dwrap"><input type="text" name="${n}" id="${id}" value="${esc(v?fd(v):"")}" placeholder="DD-MM-YYYY" autocomplete="off" data-date="1"><button type="button" class="dbtn" data-cal="${id}" aria-label="Choose date">${CALI}</button></span>`;
  if(t==="owner") return `<div class="combohost" data-combo="${n}" data-v="${esc(v&&v!=="TBC"?v:"")}" data-label="${n==="by"?"Decision maker":"Owner"}"></div>`;   /* BL-316: a Combobox, drawn by mountOwnerFields */
  if(t==="ws") return `<input type="text" name="${n}" id="${id}" list="wslist" value="${esc(v||"")}" placeholder="${formProject()?`A ${formProject()} workstream`:"e.g. Data, Testing"}"><datalist id="wslist">${wsFor(formProject()).map(w=>`<option value="${esc(w)}">`).join("")}</datalist>`;   /* BL-57: only this project's */
  if(t==="check") return `<label style="display:flex;gap:8px;align-items:center"><input type="checkbox" name="${n}" id="${id}" ${v?"checked":""}> Include in client reports</label>`;
  if(t==="calc") return `<span id="f_prcalc">${esc(v)}</span>`;
  if(t==="ro") return esc(v);
  return `<input type="text" name="${n}" id="${id}" value="${esc(v||"")}">`; }
export function markSel(){ $$("#workTbl tr[data-row],#v-person tr[data-row],#workBoard .bcard[data-row]").forEach(tr=>tr.classList.toggle("sel",tr.dataset.row===shared.SEL)); }
export function openRecord(k,id,f){ { const k1=k==="all"?kOfId(id):k, x=REC(k1,id);
    if(x&&!curGuard(()=>openRecord(k1,id))){ shared.CUR={mode:"record",k:k1,id}; shared.SEL=id; shared.EDITING=false; if(shared.VIEW==="work"||shared.VIEW==="mine"||shared.VIEW==="person") markSel(); drawPanel(); $("#panel").classList.add("on"); navWrite(false); } }
  if(!shared.LOADING){ $$(`.mnew[data-mk="${CSS.escape(k+":"+id)}"]`).forEach(mDotGo);
  if(f&&pkOn()){ const el=f==="t"?$("#pkTitle"):["upd","resp","why"].includes(f)?$("#pkDesc"):$(`#panel [data-pkp="${f}"]`); el&&el.focus(); } } }
export function openNew(k,how){ (()=>{ if(!PKK.includes(k)) return; if(curGuard(()=>openNew(k,how))) return; closePicker("owner",false);
  const draft=pkNewBlank(k,how); PKN.seq++;
  shared.CUR={mode:"new",k,how:how||"",nid:`nw${PKN.seq}-${Date.now().toString(36)}`,draft,blank:{...draft},staged:null}; shared.SEL=null; markSel(); shared.EDITING=false; PK.wide=false;
  drawPanel(); $("#panel").classList.add("on"); $("#pkTitle").focus(); })();
  if(!shared.CUR||shared.CUR.mode!=="new"||shared.CUR.k!==k) return;
    const key=pkNewKey(), d=pdAll()[key]; if(!d||!d.fields) return; const when=pdWhen(d.at), w=pkNewWord(k);
    if(Date.now()-d.at>PDAGE){ pdDrop(key); PKN.offer=null; pkNewOffer(`<span class="t">An unsaved new ${esc(w)} from ${when} was dropped: it was more than 7 days old.</span><button type="button" class="btn" data-pknd="ok">OK</button>`); return; }
    const t=d.fields.t||"";
    PKN.offer={key}; pkNewOffer(`<span class="t">An unsaved new ${esc(w)} from ${when}${t?`, “${esc(pkShort(t,50))}”`:""}, kept in this browser.</span><button type="button" class="btn primary" data-pknd="restore">Restore</button><button type="button" class="btn" data-pknd="discard">Discard</button>`); }
/* ===== BL-260 (fix-minutes-draft) ===== a minutes row with no Word draft (build_dashboard sets nodraft): Edit says so and opens nothing */
export const NODRAFT_MSG="No Word draft was made for these minutes: Reject them and process the meeting again";
/* ===== end BL-260 ===== */
export function openProposal(n){ const r=REV.find(x=>x.n===n); if(!r) return; if(r.kind==="draft"&&r.nodraft){ snack(NODRAFT_MSG); return; }   /* BL-260 */
  if(r.kind==="draft"&&/\.html$/i.test(r.src||"")){ if(viaServer()){ go("minutes",{file:r.file}); return; } openPath(r.src); snack("Check the minutes, then approve them in Claude Code (the live server isn't running)"); return; }   /* v2.1.0 P4: a minutes record isn't edited in Word; P7: it opens in the minutes view */
  if(r.kind==="draft"){ openPath(r.src); snack(viaServer()?"Edit in Word if needed, close it, then press Approve here":"Edit in Word if needed, close it, then approve it in Claude Code (the live server isn't running)"); return; }   /* BL-149 */
  if(r.kind==="files"){ snack("Ask Claude to change a file change; approve or reject it here"); return; }
  if(r.kind==="update"){ const u=updOpen(r); if(u){ shared.CUR={mode:"proposal",k:u.table,n,draft:u.draft,upd:u.upd}; shared.EDITING=true; drawPanel(); $("#panel").classList.add("on"); return; } }   /* #232-B: an update proposal opens the whole item in the peek; one that can't keeps the old form */
  shared.CUR={mode:"proposal",k:r.kind,n,draft:Object.assign({p:r.p},r.rec)}; shared.EDITING=true; drawPanel(); $("#panel").classList.add("on"); }
/* ===== #232-B (release 2.6) ===== an update proposal in the peek. The item is the live tracker row (REC), with the proposal's
   changes applied to the editable columns (Status, Due, Latest update) in the draft; the other changes are read-only `was → now`.
   core/irUpdate.js holds the rules (the one list of changes, the save); components/intakeReview/UpdatePeek.jsx draws them.
   CUR.upd keeps the row as it was when the peek opened (live), the proposal's own changes, and the editable columns as opened. */
export const updPeekable=r=>{ const rec=(r&&r.rec)||{}; return PKK.includes(rec.table)&&!!REC(rec.table,rec.target)&&(rec.changes||[]).some(c=>c.col); };   /* the item is in the tracker and the changes name their columns */
export function updOpen(r){ const rec=r.rec||{}, t=rec.table, id=rec.target, x=PKK.includes(t)?REC(t,id):null;
  if(!x){ if(PKK.includes(t)) snack(`${id} is no longer in the tracker: its change is shown in the old form`); return null; }
  const cols=(rec.changes||[]).filter(c=>c.col); if(!cols.length) return null;
  const live={...x}, liveDb=toDb(t,live), changes=Object.fromEntries(cols.map(c=>[c.col,c.to])), draft={...live};
  for(const col of [...(EDITABLE[t]||[])]) if(col in changes&&UI[t][col]) draft[UI[t][col]]=changes[col]??"";
  return {table:t,draft,upd:{table:t,id,live,liveDb,changes,opened:toDb(t,draft)}}; }
export function updModel(){ const u=shared.CUR.upd, x=shared.CUR.draft, now=irNowRow(u.table,u.liveDb,u.changes,toDb(u.table,x));
  const list=irUpdateList(u.liveDb,now,Object.keys(u.changes)); return {u,x,now,list,changed:irChanged(list)}; }
/* the peek's own parts are read-only or hidden for an update; every draw puts them right for the proposal on show */
export function pkUpdMount(){ if($("#pkUpd")) return;                                 /* made the first time an update opens, so the peek's own markup is as it was */
  addHTML($("#pkNote"),"afterend",html`<div id="pkUpd"></div>`); addHTML($(".pk-dlrow"),"beforebegin",html`<div id="pkUpdWas"></div>`); addHTML($("#pkDesc"),"afterend",html`<div id="pkUpdLast"></div>`); }
export function pkUpdReset(on){ if(on) pkUpdMount(); const t=$("#pkTitle"), ed=t.cxed&&t.cxed.editor; if(ed&&ed.isEditable===on) ed.setEditable(!on,false);   /* the title is the item's own text: read-only here */
  if(on) t.setAttribute("aria-readonly","true"); else t.removeAttribute("aria-readonly");
  const a=on&&shared.CUR.k==="actions"; $(".pk-dlrow").hidden=on&&!a; $("#pkDesc").hidden=on&&!a;
  const det=$("#pkDetT")?.closest("section"); if(det) det.hidden=on;                       /* Details would edit columns this peek leaves read-only */
  $("#pkPSaveA").hidden=on&&isConflict(pkRev());
  $("#pkDesc").classList.toggle("updnew",false);
  if(!on&&$("#pkUpd")){ drawUpdateBody($("#pkUpd"),null); drawLatestWas($("#pkUpdWas"),null); drawLast($("#pkUpdLast"),null); } }
export function updDraw(x,k,r){ const {u,now,list}=updModel(), t=u.table;
  putHTML($("#pkId"),html`<span>Update proposal</span><span aria-hidden="true">·</span><span>${u.id}</span><span aria-hidden="true">·</span>${x.p?html`<a href="#" class="hlink" data-proj="${x.p}" data-tip="Open the project page">${pName(x.p)??""}</a>`:html`<span>needs a project</span>`}`);
  putHTML($("#pkPropTop"),html`<div class="pk-propline">Editing a proposal — nothing reaches the tracker until it's approved. Changed fields are highlighted.</div>`); $("#pkPropEnd").textContent="";
  const show=(col,v)=>col==="project"?(v?pName(v)||v:"—"):col==="owner"||col==="made_by"?(pkWho(v)||"—"):col==="milestone"?(v?msName(v):"—"):irWord(col,v);
  const {row1,row2}=updateChips(t,list,now,show); $("#pkProps").replaceChildren(...updateChipNodes(row1)); $("#pkProps2").replaceChildren(...updateChipNodes(row2));
  drawUpdateBody($("#pkUpd"),{id:u.id,title:u.live.t||"",table:t,list,rec:r.rec,conflict:isConflict(r),current:u.liveDb});
  const lc=list.find(c=>c.col==="latest_update"), lat=!!lc&&!lc.same;
  drawLatestWas($("#pkUpdWas"),t==="actions"?{was:u.liveDb.latest_update,changed:lat}:null); if(t==="actions"){ $("#pkDescL").textContent=lat?"New latest update":"Latest update"; $("#pkDesc").classList.toggle("updnew",lat); }
  drawLast($("#pkUpdLast"),{id:u.id,at:u.live.upd_at||""}); updFeed(); }
/* the activity: the pending "If approved" line from the same list, then the item's history and the source */
export function updFeed(){ const {u,changed}=updModel(), r=pkRev(), tab=PK.tab||"all"; if(!r||!$("#pkFeed")) return;
  const items=[...feedLines(pkHistory(u.id),ch=>/^created\b/.test(ch)?"src":ch.toLowerCase().startsWith(pkUpdLabel(u.table)+":")?"upd":"act"),{type:"src",who:"Source",html:`<div class="pk-src">${srcHTML(r.src)}</div>`,when:""}];
  const pend=changed.length&&(tab==="all"||tab==="act")?html`<div class="pk-fe pending" data-t="act"><span class="pk-fi" aria-hidden="true">${raw(ic("pencil"))}</span><div><b>If approved</b> · ${irIfApproved(changed)}</div></div>`:html``;
  putHTML($("#pkFeed"),html`${pend}${raw(feedListHtml(items,tab))}`); }
export async function updSave(approve){ const u=shared.CUR.upd, r=pkRev(), x=shared.CUR.draft; if(!r) return;
  const plan=irSaveChanges(u.table,u.changes,u.liveDb,u.opened,toDb(u.table,x));
  if("error" in plan){ pkNote(plan.error); return; }
  if(!plan.edited.length){ closePanel(); if(approve) decide(r.n,"approved",true); else snack("Nothing was changed"); return; }   /* nothing edited: the proposal is as it was */
  if(!await needVault()) return;
  const cols=Object.keys(plan.changes).sort((a,b)=>(a==="status"?-1:0)-(b==="status"?-1:0));        /* status first: the proposal's field is its first change, and the hold reads it */
  const changes=Object.fromEntries(cols.map(c=>[c,plan.changes[c]]));
  try{ await editProposal(r.file,data=>{ const it=(data.items||[]).find(i=>i.n===r.ref); if(!it||it.applied) throw new Error("that proposal has already been applied");
      it.changes=changes; it.edited_in="dashboard"; if(approve){ it.decision="approved"; it.decided_in="dashboard"; } }); }catch(e){ snack("Not saved: "+e.message); return; }
  const was=r.rec.changes||[]; r.rec.changes=cols.map(c=>({field:irLabel(c).toLowerCase(),col:c,from:u.liveDb[c]??null,to:changes[c]}));
  const f=r.rec.changes[0]; r.rec.field=f.col; r.rec.from=f.from; r.rec.to=f.to;
  if(was.length&&String(r.rec.t||"").startsWith(u.id+":")&&!("why" in r.rec)) r.rec.t=`${u.id}: ${cols.map(c=>`${c} → ${irWord(c,changes[c])}`).join(", ")}`;
  r.edited=true; if("hold" in r) r.hold=irHold(r);
  closePanel(); if(approve) decide(r.n,"approved",true); else { refreshAll(); snack(`Proposal updated — still waiting for review`); } }
/* ===== end #232-B ===== */
export function openProject(code,what){ if(curGuard(()=>openProject(code,what))) return; const p=P.find(x=>x.code===code); HSG=null; HSUSED=null; shared.CUR={mode:what,k:"project",code,draft:{health:p.health,reason:p.reason,current:p.current}}; shared.EDITING=true; shared.HBACK=what==="health"&&document.activeElement&&document.activeElement.closest("[data-edproj]")||null; drawPanel(); $("#panel").classList.add("on"); }   /* #109: Esc or Cancel gives focus back to the pencil */
export function curObj(){ return shared.CUR.mode==="record"?REC(shared.CUR.k,shared.CUR.id):shared.CUR.draft; }
export const PKK=["actions","raid","decisions"];   /* declared before drawPanel, which runs at load */
export const pkNew=()=>!!(shared.CUR&&(shared.CUR.mode==="new"||shared.CUR.mode==="msnew"));   /* declared before drawPanel, which runs at load */
export const pdAll=()=>store.get(PDK,{}), pdPut=a=>store.set(PDK,a);   /* declared before drawPanel, which runs at load */
export const PDK="creaite-panel-drafts", PDAGE=7*864e5;   /* declared before drawPanel, which runs at load */
export function drawPanel(focusField){ const fresh=pkIs()&&shared.CUR.mode==="proposal"&&PK.key!=="proposal:"+shared.CUR.k+":rv"+shared.CUR.n;   /* BL-250 A */
  if(!shared.LOADING&&pkIs()&&$("#pkScroll")){
    const pn=$("#panel"); shared.EDITING=false; pn.classList.remove("pwide"); pn.classList.add("peek"); $("#pFields").textContent=""; $("#pFoot").textContent=""; $("#pKeys").textContent="";
    pkWide(PK.wide); pkNav(); pkDraw(); }   /* BL-176: an action, RAID item, decision or proposal is the peek (once the peek is built: an address can open an item earlier in the load) */
  else { if(!shared.LOADING) $("#panel").classList.remove("peek","pkwide","pover");   /* BL-166 */
  const was=shared.PDKEY;   /* BL-169 */
  if(shared.CUR&&shared.CUR.pre&&!shared.EDITING) shared.CUR.pre=null;   /* BL-53 */
  PANELF=true; try{ const x=curObj(), k=shared.CUR.k, F=fieldsFor(k,x); $("#pErr").textContent="";
  const title={record:x.t,new:k==="actions"?"New action":k==="raid"?"New RAID item":"New decision",proposal:`Proposal: ${x.t}`,health:`${pName(shared.CUR.code)} health`,milestone:x.name,msnew:"New milestone",rebase:`Rebaseline: ${x.name}`}[shared.CUR.mode];
  const pl=c=>c?`<a href="#" class="hlink" data-proj="${c}" title="Open the project page">${esc(pName(c))}</a>`:"";   /* BL-38: items → project */
  putHTML($("#pId"),shared.CUR.mode==="milestone"||shared.CUR.mode==="rebase"?html`${shared.CUR.id} · ${raw(pl(shared.CUR.code))}`:shared.CUR.mode==="msnew"?html`Not yet saved · ${raw(pl(shared.CUR.code))}`:shared.CUR.mode==="record"?html`${shared.CUR.id} · ${raw(pl(x.p))}`:shared.CUR.mode==="proposal"?html`Review #${shared.CUR.n} · ${x.p?raw(pl(x.p)):"needs a project"}`:shared.CUR.mode==="new"?html`Not yet saved`:raw(pl(shared.CUR.code)));
  $("#pTitle").textContent=title||"";
  $("#panel").classList.toggle("pwide",!!shared.EDITING);   /* BL-80 */
  $("#panel").classList.toggle("pover",shared.CUR.mode==="health");   /* #109: the health form is over the page, not beside it */
  $("#pBody").classList.toggle("editing",shared.EDITING); $("#editBanner").textContent=shared.CUR.mode==="proposal"?"Editing a proposal — nothing reaches the tracker until it's approved":"Editing — changes apply when you save";
  let h=""; for(const [n,l,t,opts] of F){ if(n==="#"){ h+=`<div class="fsec">${l}</div>`; continue; } const v=shared.CUR.pre&&n in shared.CUR.pre?shared.CUR.pre[n]:x[n];   /* CUR.pre: "Record the decision" fills the form first (BL-53) */
    h+=`<dt>${l}${shared.EDITING?labelAdorn(shared.CUR.k,shared.CUR.mode,n):""}</dt><dd>${shared.EDITING&&t!=="ro"?editCtl(n,t,t==="calc"?prio(x.imp,x.lik):v,opts):viewVal(n,t,v,x)}</dd>`; }
  if(shared.CUR.mode==="proposal"&&!x.p) h=`<div class="cmnote">Choose a project before saving.</div>`+h;
  if(shared.CUR.mode==="record"||shared.CUR.mode==="proposal"){ const src=shared.CUR.mode==="record"?x.src:REV.find(r=>r.n===shared.CUR.n).src; h+=`<div class="fsec">Record</div>${shared.CUR.mode==="record"?`<dt>ID</dt><dd>${shared.CUR.id}</dd>`:""}<dt>Source</dt><dd>${srcHTML(src)}</dd>${shared.CUR.mode==="record"?`<dt>Last updated</dt><dd>${x.upd_at?fd(x.upd_at):"—"}</dd>`:""}`; }
  if(shared.CUR.mode==="proposal"){ const sig=learnable(REV.find(r=>r.n===shared.CUR.n)); if(sig) h+=`<div class="fsec">Learn</div><dt></dt><dd><label style="display:flex;gap:8px;align-items:flex-start"><input type="checkbox" id="f_learn" data-kind="${esc(sig.kind)}" data-value="${esc(sig.value)}"><span id="learnTxt"></span></label></dd>`; }
  if(shared.CUR.mode==="health") h+=`<div class="evidence" id="hEvidence" aria-live="polite"></div>`;
  if(shared.CUR.k==="project") h+=`<dd class="full">${feedBlock("proj",projFeedItems(shared.CUR.code))}</dd>`;   /* BL-250 A: its history, under the fields */
  putHTML($("#pFields"),raw(h)); mountOwnerFields($("#pFields")); mountFeedTabs($("#pFields")); learnLabel(); if(shared.CUR.mode==="health"){ const hs=$("#f_health"); if(hs){ hs.addEventListener("change",showEvidence); showEvidence(); } }
  const foot={record:"",   /* BL-176 (sprint-peek): an action, RAID item or decision is the peek, with no Edit, Save or Cancel */
    proposal:`<button class="btn" id="pCancel">Cancel</button><span class="sp"></span><button class="btn" id="pSave">Save</button><button class="btn primary" id="pSaveA">Save and approve</button>`,
    health:`<button class="btn" id="pCancel">Cancel</button><span class="sp"></span><button class="btn primary" id="pSave">Save</button>`,
    milestone:`<button class="btn" id="msRemove">Remove</button><button class="btn" id="msRebase">Rebaseline</button><span class="sp"></span>${x.st!=="Done"?'<button class="btn" id="msDone">Mark done</button>':""}<button class="btn primary" id="pSave">Save</button>`,
    msnew:`<button class="btn" id="pCancel">Cancel</button><span class="sp"></span><button class="btn primary" id="pSave">Create</button>`,
    rebase:`<button class="btn" id="pCancel">Cancel</button><span class="sp"></span><button class="btn primary" id="pSave">Rebaseline</button>`}[shared.CUR.mode];
  putHTML($("#pFoot"),raw(foot)); $("#pKeys").textContent=shared.EDITING?`${MOD}↵ saves and closes · Esc cancels`:"";   /* BL-78 */
  if($("#pCancel")) $("#pCancel").onclick=()=>closePanel();
  if($("#pcClear")) $("#pcClear").onclick=()=>{ $("#f_pc").value=""; $("#f_pc").dispatchEvent(new Event("input")); };
  if($("#f_pc")) $("#f_pc").oninput=()=>{ putHTML($("#pcHint"),+$("#f_pc").value===100&&$("#f_st")&&$("#f_st").value!=="Done"?html`100% — mark it as Done? Set Status to Done, or use Mark done.`:""); };
  if($("#msRebase")) $("#msRebase").onclick=()=>{ shared.CUR.mode="rebase"; shared.CUR.draft={...shared.CUR.draft,reason:""}; drawPanel("fc"); };
  if($("#msDone")) $("#msDone").onclick=()=>msSave({st:"Done",fc:shared.CUR.draft.fc||TODAY},"done");
  if($("#msRemove")) $("#msRemove").onclick=e=>{ const b=e.currentTarget; if(b.dataset.armed){ msRemove(); return; } b.dataset.armed="1"; const n=msLinked(shared.CUR.id).length; b.textContent="Confirm remove"; b.classList.add("danger"); $("#pErr").textContent=`Removing marks it Cancelled (kept in history)${n?` and unlinks ${n} item${n===1?"":"s"}`:""}.`; };
  if($("#pSave")){ $("#pSave").dataset.key=`${MOD}↵`; $("#pSave").dataset.tip=$("#pSave").textContent; }   /* BL-274 */
  if($("#pSave")) $("#pSave").onclick=()=>savePanel(false); if($("#pSaveA")) $("#pSaveA").onclick=()=>savePanel(true);
  const imp=$("#f_imp"), lik=$("#f_lik"); if(imp&&lik){ const u=()=>$("#f_prcalc").textContent=prio(imp.value,lik.value); imp.onchange=u; lik.onchange=u; }
  const st=$("#f_st"), cl=$("#f_closed"); if(st&&cl) st.onchange=()=>{ if(!OPENST(st.value)&&!cl.value) cl.value=fd(TODAY); if(OPENST(st.value)) cl.value=""; };
  const cb=$("#f_client"), cm=$("#f_cm")||$("#f_cmd"); if(cb&&cm) cb.onchange=()=>{ const ok=cm.id==="f_cmd"?cmdOK(cm.value):cmOK(cm.value); if(cb.checked&&!ok){ cm.focus(); $("#pErr").textContent=cm.id==="f_cmd"?"Write client messaging (a short plain explanation) to make this client-visible.":"Complete client messaging (a few words after each heading) to make this client-visible."; } };
  if(shared.EDITING){ const f=focusField&&$("#f_"+(focusField==="imp"?"imp":focusField)); (f||$("#pFields .rted")||$("#pFields [name]"))?.focus(); } } finally{ PANELF=false; } morePanel(focusField);
  { if(shared.CUR&&shared.CUR.mode==="proposal"){ const r=REV.find(x=>x.n===shared.CUR.n); if(r&&rvDup(r)&&!r.done)
    addHTML($("#pFields"),"afterbegin",raw(llNoteHtml(r))); } }   /* BL-133 */
  depFormDraw();
  { $("#pWarn")?.remove(); const w=shared.CUR&&shared.CUR.mode==="record"?warnsOf(shared.CUR.k,shared.CUR.id):[];
    if(w.length) addHTML($("#pTitle"),"afterend",html`<div class="wnote" id="pWarn">${w.map(x=>html`<div>${raw(WICO.replace("<svg",'<svg width="14" height="14" style="flex:none;margin-top:1px"'))}<span>${x.text}</span></div>`)}</div>`); }   /* BL-51 */
  if(!shared.LOADING){ pKeysShow(pkNew()&&$("#pFields").contains(document.activeElement));   /* BL-157 */
  { const key=pdKeyOf();
    if(was&&!shared.EDITING&&was===key) pdDrop(was);                           /* Save, Cancel or Esc ended this edit */
    shared.PDKEY=shared.EDITING?key:null; shared.PDBASE=shared.EDITING&&key?pdRaw():null; pdOffer(); } } }   /* BL-169 */
    if(shared.LOADING){} else if(pkIs()&&shared.CUR.mode==="proposal"){ shared.EDITING=true; if(fresh) setTimeout(()=>{ if(pkOn()&&shared.CUR&&shared.CUR.mode==="proposal"&&!$("#panel").contains(document.activeElement)) $("#pkScroll").focus({preventScroll:true}); },0); }   /* the keys stay in the panel, as the old form's first field did */
    else $("#panel").classList.remove("pkprop"); }
/* BL-28: after choosing a project for an uncertain item, offer to remember the signal that decided it */
export const KINDL={sender:"sender",domain:"email domain",channel:"Teams channel",alias:"alias",stakeholder:"stakeholder"};
export const learnable=r=>r&&(r.signals||[]).find(s=>s.ok&&!(s.owners||[]).length);
export function learnLabel(){ const cb=$("#f_learn"); if(!cb) return; const code=$("#f_p")?.value||""; cb.closest("dd").previousElementSibling.previousElementSibling.hidden=cb.closest("dd").hidden=!code;
  $("#learnTxt").textContent=`Remember ${cb.dataset.value} (${KINDL[cb.dataset.kind]}) for ${pName(code)}, so items like this match on their own. Added to the register when applied.`; }
export async function learnSignal(code,kind,value){ if(!viaServer()){ snack("Remembering a signal needs the live server; or say it in Claude Code"); return; }
  const res=await api("/api/learn",{code,kind,value}); snack(res.ok?`${value} will be remembered for ${pName(code)} at apply`:oneLine(res.message)||"Not remembered"); if(res.ok&&S.autoApply) applySoon(); }
/* BL-52: health is checked against the evidence (the same criteria as the weekly report, from Settings). A health
   better than the evidence needs a new reason before it saves; creaite never changes health itself. */
export const HRANK={"On track":0,"At risk":1,"Off track":2};
export function healthEvidence(code){ const p=P.find(x=>x.code===code)||{}, off=[], risk=[];
  const overN=A.filter(a=>a.p===code&&open(a)&&a.due&&days(a.due)<-S.overdueDays), urgent=R.filter(r=>r.p===code&&r.st==="Open"&&r.pr==="Urgent"), slip=p.slip||0;
  const nm=((p.ms||[]).find(m=>m[6]==="Planned"&&m[4]&&m[8]&&m[8]>m[4])||[])[0]||"The next milestone";
  if(slip>S.slipOff*7) off.push(`${nm} moved ${slip} days`);
  if(urgent.length>=S.urgentOff) off.push(`${urgent.length} open Urgent risks or issues`);
  if(overN.length) risk.push(`${overN.length} action${overN.length===1?"":"s"} overdue by more than ${S.overdueDays} days`);
  if(urgent.length&&!off.length) risk.push(`an open Urgent risk or issue`);
  if(slip>0&&slip<=S.slipAtRisk*7) risk.push(`${nm} moved ${slip} days`);
  return {suggested:off.length?"Off track":risk.length?"At risk":"On track",reasons:off.length?off:risk}; }
export function showEvidence(){ const el=$("#hEvidence"); if(!el||!shared.CUR){ drHealthDraw(); return; } const ev=healthEvidence(shared.CUR.code), h=$("#f_health").value;
  el.className="evidence"+(HRANK[h]<HRANK[ev.suggested]?" warn":"");
  putHTML(el,HRANK[h]<HRANK[ev.suggested]?html`<b>${h}, but the evidence suggests ${ev.suggested}:</b> ${ev.reasons.join("; ")}. Say why in the reason.`:html`The evidence suggests ${ev.suggested}${ev.reasons.length?raw(": "+esc(ev.reasons.join("; "))):""}.`);
  { const el=$("#hEvidence"), ws=shared.CUR?WARNS().filter(w=>w.p===shared.CUR.code):[];   /* BL-52's evidence */
    if(el&&ws.length) addHTML(el,"beforeend",html`<div class="wnote">Early warnings: ${(ws.map(w=>`${w.k==="projects"?pName(w.id):w.id} ${w.text}`).join("; "))}.</div>`); }
  drHealthDraw(); }
export function readForm(){ const o={}; $$("#pFields [name]").forEach(el=>{ o[el.name]=el.type==="checkbox"?el.checked:el.value.trim(); if(el.dataset.date&&o[el.name]){ o[el.name]=DDATE.test(o[el.name])?toIso(o[el.name]):"BAD:"+o[el.name]; } }); return o; }
export function validate(k,f,isNew,orig){ const m=(()=>{ $$("#pFields .bad").forEach(e=>e.classList.remove("bad")); const bad=(n,msg)=>{ const el=$("#f_"+n); if(el) el.classList.add("bad"); return msg; };
  if("t" in f&&!f.t) return bad("t","Description is required.");
  for(const n of ["due","raised","closed","date"]) if(f[n]&&!DATE.test(f[n])) return bad(n,"Not a date creaite knows. "+DATE_HELP);
  if(f.closed&&f.raised&&f.closed<f.raised) return bad("closed","Closed can't be before Raised.");
  if("cm" in f&&!cmHeads(f.cm)) return bad("cm","Keep the three client messaging headings.");
  if(f.client&&"cm" in f&&!cmOK(f.cm)&&(!orig||!orig.client||f.cm!==orig.cm)) return bad("cm","Client-visible items need complete client messaging: a few words after each heading.");
  if(k==="decisions"&&f.client&&!cmdOK(f.cmd)&&(!orig||!orig.client||f.cmd!==orig.cmd)) return bad("cmd","Client-visible decisions need client messaging: a short plain explanation.");
  if(k==="decisions"&&isNew&&!f.srcIn) return bad("srcIn",f.st==="Pending"?"Record where this decision was raised (meeting, email or document).":"Record where the decision was made (meeting, email or document).");
  if(k==="decisions"){ const e=decisionCheck(f,orig,bad); if(e) return e; }   /* BL-53 */
  if("reason" in f&&!f.reason) return bad("reason","Give a reason for the health rating.");
  if(shared.CUR&&shared.CUR.mode==="health"&&f.health){ const ev=healthEvidence(shared.CUR.code), p=P.find(x=>x.code===shared.CUR.code)||{};
    if(HRANK[f.health]<HRANK[ev.suggested]&&String(f.reason).trim()===String(p.reason||"").trim()) return bad("reason",`${f.health}, but the evidence suggests ${ev.suggested} (${ev.reasons.join("; ")}). Give a reason for rating it better.`); }
  if("p" in f&&!f.p) return "Choose a project.";
  const wsP=f.p||(orig&&orig.p)||(shared.CUR&&shared.CUR.draft&&shared.CUR.draft.p)||"";   /* BL-57: a new workstream is added on purpose, not by a typo */
  if(f.ws&&wsP&&!wsFor(wsP).some(n=>n.toLowerCase()===f.ws.toLowerCase())&&!(orig&&orig.ws===f.ws&&orig.p===wsP)){ const m=wsConfirm(wsP,f.ws); if(m) return bad("ws",m); }   /* BL-58: add it on purpose, with its details */
  return null; })();
  const det=$("#pFields details.morefields"); if(m&&det&&det.querySelector(".bad")) det.open=true; return m; }
export function norm(k,f){ if("o" in f) f.o=f.o||"TBC";
  if("st" in f&&k!=="decisions"){ if(!OPENST(f.st)&&!f.closed) f.closed=TODAY; if(OPENST(f.st)) f.closed=null; } ["due","closed"].forEach(n=>{ if(n in f&&!f[n]) f[n]=null; });
  if(k==="decisions"&&f.st==="Pending") f.date="";   /* BL-53: no date until it is made */
  if(k==="raid") f.pr=prio(f.imp,f.lik); return f; }
export function nextId(k,p){ const pre=k==="actions"?`${p}-A-`:k==="raid"?`${p}-`:`${p}-D-`; /* one number sequence per project across actions, RAID, decisions and promises, as tracker.next_id: promises aren't on the page, so the build gives the highest number at build time (seq) */ const pr=P.find(x=>x.code===p), n=Math.max(0,+(pr&&pr.seq)||0,...[[A,`${p}-A-`],[R,`${p}-`],[DEC,`${p}-D-`]].flatMap(([arr,q])=>arr.filter(x=>x.id.startsWith(q)&&x.id.length===q.length+3&&/^\d{3}$/.test(x.id.slice(-3))).map(x=>+x.id.slice(-3))))+1; return pre+String(n).padStart(3,"0"); }
/* The save of one existing item, shared by the panel's Save and the Work board's moves (BL-103): the fields that changed become one
   proposal (with Undo), applied at once when auto-apply is on. Returns "nochange", or whether it was saved. `label` overrides the message. */
export async function commitRecord(k,id,f,label){ const x=REC(k,id), before={...x}; const same=(a,b)=>String(a??"").trim()===String(b??"").trim();   /* the form trims; stored text may keep a trailing space */
  const ch=Object.keys(f).filter(n=>typeof f[n]==="boolean"?!!x[n]!==f[n]:!same(x[n],f[n])); if(!ch.length) return "nochange";
  const FN={t:"description",o:"owner",st:"status",pr:"priority",due:"due date",ws:"workstream",upd:"latest update",client:"client-visible",cm:"client messaging",cmd:"client messaging",by:"made by",date:"date",why:"reasoning",opts:"options",revisit:"revisit",replaces:"replaces",resp:"response",imp:"impact",lik:"likelihood",raised:"raised",closed:"closed date",type:"type",p:"project",ms:"milestone"}; label=label||`${id} ${[...new Set(ch.filter(n=>n!=="pr"||k!=="raid").map(n=>FN[n]||n))].join(", ")} updated`;
  const changes=toDb(k,Object.fromEntries(ch.filter(n=>!(k==="raid"&&n==="pr")).map(n=>[n,f[n]])));
  return await save(label,[{op:"update",table:k,id,changes,based_on:x.updated_at}],null,()=>{ Object.assign(x,f,{upd_at:nowStamp()}); },()=>{ Object.keys(x).forEach(n=>delete x[n]); Object.assign(x,before); },undefined,{recs:[{k,id,f:Object.fromEntries(ch.map(n=>[n,f[n]]))}]}); }   /* BL-304: on screen at once */
/* a new item's values for its "new" proposal, from the form's fields after validate and norm: shared by the Create form and the
   new item peek (BL-179), so both write the same proposal */
export function newItemOf(k,f){ const id=nextId(k,f.p); const rec=Object.assign({id,upd_at:nowStamp()},f); let source;
  if(k==="decisions"){ source=`${f.srcIn} — recorded by ${S.me} in the dashboard, ${TODAY}`; delete rec.srcIn; } else source=`${S.me} (dashboard), ${TODAY}`; rec.src=source;
  const values=Object.assign(toDb(k,rec),{source}); if(k!=="decisions"&&!values.raised) values.raised=TODAY; return {id,rec,values}; }
export async function savePanel(approve,closeAfter){ if(shared.CUR.k==="milestone") return msPanelSave();   /* closeAfter (BL-78, ⌘↵): an item saved in place closes the panel instead of returning to its read view */ const f=readForm(), k=shared.CUR.k; const err=validate(k,f,shared.CUR.mode==="new",shared.CUR.mode==="record"?REC(k,shared.CUR.id):null); if(err){ $("#pErr").textContent=err; return; } $("#pErr").textContent="";
  for(const n of ["o","by"]) if(n in f&&f[n]&&f[n]!=="TBC"){ const o=await ownerFinal(f[n]); if(o===null) return; f[n]=o; }   /* BL-55: a full name, or ask */
  norm(k,f);
  if(shared.CUR.mode==="record"){ const x=REC(k,shared.CUR.id), id=shared.CUR.id;
    const r=await commitRecord(k,id,f); if(r==="nochange"){ if(closeAfter) closePanel(); else { shared.EDITING=false; drawPanel(); } return; }
    if(r){ if(closeAfter){ if(shared.CUR&&shared.CUR.id===id) closePanel(); } else { shared.EDITING=false; if(shared.CUR&&shared.CUR.id===id){ drawPanel(); $("#pTitle").textContent=x.t; } } } return; }
  /* tidy-up (sprint-milestones): the Create form's branch for new work items is gone; they are the peek (BL-179), staged through newItemOf */
  if(shared.CUR.mode==="proposal"){ const r=REV.find(x=>x.n===shared.CUR.n); const before=JSON.parse(JSON.stringify(r)); if(!await needVault()) return;
    try{ await editProposal(r.file,data=>{ const it=(data.items||[]).find(i=>i.n===r.ref); if(!it||it.applied) throw new Error("that proposal has already been applied");
      if(r.kind==="update"){ it.changes=it.changes||{}; it.changes[r.rec.field]=f.to; }
      else { /* only the fields Alan changed; required dates are never blanked */
        const same=(a,b)=>String(a??"").trim()===String(b??"").trim(), ch={};
        for(const n of Object.keys(f)){ const was=n==="p"?r.p:r.rec[n]; if(typeof f[n]==="boolean"?!!was!==f[n]:!same(was,f[n])) ch[n]=f[n]; }
        const vals=toDb(r.kind,ch); ["raised","date"].forEach(k=>{ if(vals[k]===null) delete vals[k]; });
        it.values=Object.assign(it.values||{},vals); if(f.p&&f.p!==r.p){ it.values.project=f.p; it.match="strong"; if(r.p){ if(it.moved_from===f.p) delete it.moved_from; else it.moved_from=it.moved_from||r.p; } /* BL-200 */ if(it.values.milestone&&!String(it.values.milestone).startsWith(f.p+"-M-")) it.values.milestone=null; } else if(f.p&&!r.p){ it.values.project=f.p; it.match="strong"; } }
      it.edited_in="dashboard"; if(approve){ it.decision="approved"; it.decided_in="dashboard"; } }); }catch(e){ snack("Not saved: "+e.message); return; }
    const lc=$("#f_learn"); if(lc&&lc.checked&&f.p) learnSignal(f.p,lc.dataset.kind,lc.dataset.value);
    if(r.kind==="update") r.rec.to=f.to, r.rec.t=`${r.rec.target} ${r.rec.field}: ${r.rec.from??"—"} → ${f.to}`; else { Object.assign(r.rec,f); if(f.p){ r.p=f.p; } } r.edited=true;
    if("hold" in r) r.hold=irHold(r);   /* #232-B: the server's rule (review.hold_reason) again on what the edit left: an Issue made a Risk is held, a project set clears "need a project" */
    closePanel(); if(approve) decide(r.n,"approved",true); else { refreshAll(); snack(`Proposal updated — still waiting for review`); } return; }
  if(shared.CUR.mode==="health"){ const p=P.find(x=>x.code===shared.CUR.code), before={health:p.health,reason:p.reason}; hsSaved(); closePanel();
    await save(`${p.name} health: ${before.health||"not set"} → ${f.health}`,[{op:"update",table:"projects",id:p.code,changes:{health:f.health,health_reason:f.reason}}],null,()=>Object.assign(p,f),()=>Object.assign(p,before)); return; }
}
/* Current state is saved as a proposal that rewrites the section in the project's CLAUDE.md (undoable) */
export async function saveCurrent(code,md,imgOps=[],added=[],dropped=[]){ const p=P.find(x=>x.code===code), before=p.current, imgsBefore=p.images; if(!await needVault()) return false; let old;
  try{ old=await vq(()=>shared.VW.read(memPath(p.code))); }catch(e){ snack(`Can't read ${memPath(p.code)}: ${e.message}`); return false; }
  const ops=[...imgOps.filter(o=>o.op==="copy"),{op:"write",path:memPath(p.code),content:replaceCurrent(old,md,dropped),previous:old},...imgOps.filter(o=>o.op!=="copy")];
  const extra={file_changes:{title:`${p.name} current state`,project:p.code,file_changes_decision:"approved",file_ops:ops}};
  return await save(`${p.name} current state updated${added.length?` with ${added.length} new image${added.length===1?"":"s"}`:""}`,[],extra,()=>{ p.current=md; p.images=(imgsBefore||[]).filter(i=>!dropped.includes(i.ref)).concat(added); },()=>{ p.current=before; p.images=imgsBefore; }); }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootPanel0050(){
document.addEventListener("change",e=>{ if(e.target.id==="f_p") learnLabel(); });
}
/* ===== BL-176 (sprint-peek) ===== the work item peek: the shell. An action, a RAID item or a decision opens in #panel with the class
   "peek": over the page (CSS above), sliding in over 160ms (none under reduced motion), closed by a click outside, Esc or the close
   arrow, swapped by another row, J and K (BL-122's own keys) or the arrows, and taken to full width by the expand icon. The wrapper
   on drawPanel is the outermost one (this block is last), so for these three kinds it decides how the panel looks; the milestone,
   project health, new item and Review panels keep theirs. */
export function pkIs(){ return !!(shared.CUR&&shared.CUR.mode==="new"&&PKK.includes(shared.CUR.k))||!!(shared.CUR&&(shared.CUR.mode==="record"||shared.CUR.mode==="proposal")&&PKK.includes(shared.CUR.k)); }
/* the list the arrows step through: the same order J and K use (BL-122), on Work, Mine and a person's page */
export function pkOrder(){ if(shared.PKSRC&&(!shared.PKSRC.view||shared.PKSRC.view===shared.VIEW)) return shared.PKSRC.order();   /* #232-B: Intake and Review's peek steps through its own proposals */   /* BL-286 E: the list of the screen the peek was opened from */
  return shared.VIEW==="work"||shared.VIEW==="mine"||shared.VIEW==="person"?hlOrder():[]; }
export function pkNav(){ const L=pkOrder(), i=shared.CUR?L.findIndex(o=>o.id===pkCid()):-1; $("#pkPrev").disabled=i<=0; $("#pkNext").disabled=i<0||i>=L.length-1; }
export function pkStep(n){ const L=pkOrder(), i=L.findIndex(o=>o.id===(shared.CUR&&pkCid())), o=L[i+n]; if(i<0||!o) return;
  if(shared.PKSRC&&(!shared.PKSRC.view||shared.PKSRC.view===shared.VIEW)){ shared.PKSRC.step(o); return; }
  HL.clear(); HL.set(o.id,o.k); shared.HLA=shared.HLC=o.id; openRecord(o.k,o.id); hlPaint();
  const el=$$(layoutOf(shared.WT)==="board"&&shared.VIEW==="work"?"#workBoard .bcard[data-row]":shared.VIEW==="person"?"#v-person table.ptbl tr[data-row]":"#workTbl tr[data-row]").find(e=>e.dataset.row===o.id); el&&el.scrollIntoView({block:"nearest"}); }
export function pkWide(on){ PK.wide=on; $("#panel").classList.toggle("pkwide",on); const b=$("#pkExpand"); if(!b) return; const t=on?"Back to half width":"Expand to full width";
  putHTML(b,raw(ic(on?"shrink":"expand"))); b.setAttribute("aria-label",t); b.dataset.tip=t; b.setAttribute("aria-pressed",String(on)); }
 
/* Esc closes the peek (a picker or a text field first, each in its own handler); from inside ask creaite it closes the chat and
   leaves the peek as it was. A menu, a dialog or the date picker keeps Esc for itself. */
/* ===== end BL-176 (shell) ===== */
/* Whether Esc belongs to something open over the peek (a dialog, the date picker, a combobox, a menu, a popup, the link form): the one
   rule for the panel's own Esc below and for Intake and Review's peek (#232-B), so neither closes the peek over an open menu. */
export function pkEscMenu(a){ return !!(document.querySelector("dialog:modal")||shared.CAL||comboboxOpen()||(a&&a.closest&&a.closest(".ddmenu.on,.keysmenu,[role=menu],#railPop,.cal,.combo,.pkpop,.sp-box,.linkpop"))); }   /* #121: Esc in the link form is the form's own */   /* BL-322: Esc in Sneak peek closes the box only */   /* dialog:modal: BL-286 E's Prep popup is non-modal while the peek is over it */
/* ... and also the chat, a text field being edited and the Draft email pane, each with its own Esc (#232-B). */
export function pkEscBusy(a){ return pkEscMenu(a)||!!(a&&a.closest&&a.closest("#chat"))||!!(a&&a.isContentEditable)||chaseIsOpen(); }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootPanel0165(){
Object.assign(ICONS,{arrowright:'<path d="M5 12h14M13 6l6 6-6 6"/>',expand:'<path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/>',shrink:'<path d="M21 9h-6V3M3 15h6v6M15 9l6-6M9 15l-6 6"/>',
  chevup:'<path d="M6 15l6-6 6 6"/>',link:'<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>'});
addHTML($("#panel .pin"),"afterbegin",html`<div class="pk-bar" id="pkBar">${raw(ibtn("arrowright","Close",'id="pkClose"',"","Esc"))}${raw(ibtn("expand","Expand to full width",'id="pkExpand"'))}<span class="pk-sep" aria-hidden="true"></span>${raw(ibtn("chevup","Previous item",'id="pkPrev"',"","K"))}${raw(ibtn("chevdown","Next item",'id="pkNext"',"","J"))}<span class="sp"></span><span class="pk-save" id="pkSave" role="status" aria-live="polite"></span>${raw(ibtn("link","Copy link",'id="pkLink"'))}</div>`);
$("#pkClose").onclick=()=>closePanel();
$("#pkExpand").onclick=()=>pkWide(!PK.wide);
$("#pkPrev").onclick=()=>pkStep(-1);
$("#pkNext").onclick=()=>pkStep(1);
$("#pkLink").onclick=()=>{ if(!shared.CUR) return; const u=location.origin+location.pathname+actHref(shared.CUR.k,pkCid()), b=$("#pkLink");
  const done=()=>{ copied(b); snack(`Link to ${shared.CUR?pkCid():"the item"} copied`); };
  if(navigator.clipboard) navigator.clipboard.writeText(u).then(done,()=>prompt("Copy this link:",u)); else prompt("Copy this link:",u); };
window.addEventListener("keydown",e=>{ if(e.key!=="Escape"||!pkOn()||shared.EDITING) return;
  const a=document.activeElement;
  if(pkEscMenu(a)) return;
  if(a&&a.closest&&a.closest("#chat")){ if(shared.RUN) return; e.preventDefault(); e.stopImmediatePropagation(); closeChat(); return; }
  if(a&&a.isContentEditable) return;
  if(chaseIsOpen()){ e.preventDefault(); e.stopImmediatePropagation(); chaseClose(true); return; }   /* BL-298: Esc in Draft email goes back to the item first */
  if(HL.size&&(shared.VIEW==="work"||shared.VIEW==="mine"||shared.VIEW==="person")) return;   /* BL-122 first: Esc clears the highlight, the next Esc closes */
  e.preventDefault(); e.stopImmediatePropagation(); closePanel(); },true);
/* opened before this block existed (an address with &item=…): draw it as the peek */
if(shared.CUR&&$("#panel").classList.contains("on")) drawPanel();
}
/* ===== BL-176 (sprint-peek) ===== the title, the key row and the free text. There is no read view and no form: the title and the
   free text are plain text that is the editor (contenteditable, role textbox, named by the field), and the key fields are chips
   that open a picker (a list with arrows, Enter and Esc; the owner list searches; dates open a Monday-first month with quick picks
   and a box that takes DD-MM-YYYY or words, through parseWhen). A value commits when it is picked, on Enter or on leaving the field;
   pkWrite (below, replaced by the staging in the next block) writes it. Empty values are quiet prompts; an overdue date is red with
   an "overdue" tag. Actions: Status, Priority, Owner, Due date. RAID: Status, Priority (calculated), Owner, Due date, then Impact and
   Likelihood, with the Type beside the ID. Decisions: Status, Decision maker, Needed by (Date made once it is made). */
export const pkDescF=k=>k==="actions"?"upd":k==="raid"?"resp":"why";
export const pkDescL=(k,x)=>k==="actions"?"Latest update":k==="raid"?RESPL(x.type):"Reasoning";
export const pkDescPh=(k,x)=>k==="actions"?"Add the latest update…":k==="raid"?`Add the ${RESPL(x.type).toLowerCase()}…`:"Add the reasoning…";
export const pkTitleL=k=>k==="actions"?"Action":k==="raid"?"Description":"Decision";
export const pkOwnF=k=>k==="decisions"?"by":"o", pkOwnL=k=>k==="decisions"?"Decision maker":"Owner";
export const pkStatuses=k=>k==="decisions"?["Pending","Made","Withdrawn"]:k==="raid"?["Open","Closed","Cancelled"]:["Open","Delayed","Closed","Cancelled"];
export const pkLate=(k,x)=>k==="decisions"?decLate(x):!!(OPENST(x.st)&&x.due&&x.due<TODAY);
export const pkWho=n=>!n||n==="TBC"?"":n;
export const PKFL={t:null,upd:"Latest update",resp:null,why:"Reasoning",st:"Status",pr:"Priority",o:"Owner",by:"Decision maker",due:null,date:"Date made",imp:"Impact",lik:"Likelihood",type:"Type",
  p:"Project",ws:"Workstream",ms:"Milestone",opts:"Options considered",revisit:"Revisit",replaces:"Replaces",client:"Client-visible",cm:"Client messaging",cmd:"Client messaging"};
export const pkLabel=(k,f,x)=>f==="t"?pkTitleL(k):f==="resp"?RESPL(x.type):f==="due"?(k==="decisions"?"Needed by":"Due date"):PKFL[f]||f;
/* the marks (a status ring, priority bars, initials) are PeekProps.jsx's (peekMark) */
export const PKDRAW=[];                                   /* later blocks add what they draw (staging, details, activity) */
export function pkNote(msg){ const n=$("#pkNote"); if(!n) return; n.hidden=!msg; n.textContent=msg||""; }
export function pkDrawId(x,k){ putHTML($("#pkId"),html`<span>${pkCid()}</span><span aria-hidden="true">·</span>${x.p?html`<a href="#" class="hlink" data-proj="${x.p}" data-tip="Open the project page">${pName(x.p)}</a>`:html`<span>needs a project</span>`}${k==="raid"?html`<button type="button" class="pk-type" data-pkp="type" aria-haspopup="listbox" aria-label="Type: ${x.type}" data-tip="Type">${x.type}${raw(ic("chevdown"))}</button>`:""}`);
  const w=shared.CUR.mode==="record"?warnsOf(k,pkCid()):[]; putHTML($("#pkWarn"),w.map(z=>html`<div class="pk-warn">${raw(WICO.replace("<svg",'<svg width="14" height="14"'))}<span>${z.text}</span></div>`));
  drawPeekNotes(shared.CUR.mode==="record"?pkCid():"");   /* BL-301 B: "2 notes mention this" */ }
export function pkDrawProps(x,k){ (()=>{ if(shared.PKPOP&&($("#pkProps").contains(shared.PKPOP.anchor)||$("#pkProps2").contains(shared.PKPOP.anchor)||$("#pkId").contains(shared.PKPOP.anchor))) return;
  /* BL-316: each property is a Chip (components/peek/PeekProps.jsx), drawn afresh as before */
  const o=pkWho(x[pkOwnF(k)]), late=pkLate(k,x), L=/** @type {import("./components/peek/PeekProps.jsx").PeekProp[]} */([{f:"st",name:"Status",mark:{st:x.st},value:x.st||""}]);
  if(k==="actions") L.push({f:"pr",name:"Priority",mark:{pr:x.pr},value:x.pr||"Medium"});
  if(k==="raid"){ const p=prio(x.imp,x.lik); L.push({f:"prc",name:"Priority",mark:{pr:p},value:p,ro:`Priority: ${p}, calculated from impact and likelihood`,roTip:"Priority is calculated from impact and likelihood"}); }
  L.push({f:"o",name:pkOwnL(k),mark:{who:o},value:o||(k==="decisions"?"Add decision maker":"Add owner"),you:!!o&&isMe(o),empty:!o});
  if(k==="decisions"&&x.st==="Made") L.push({f:"date",name:"Date made",popup:"dialog",mark:{icon:"calendar"},value:x.date?fd(x.date):"Date made",nw:!!x.date,empty:!x.date});
  else L.push({f:"due",name:pkLabel(k,"due",x),popup:"dialog",mark:{icon:"calendar"},value:x.due?fd(x.due):pkLabel(k,"due",x),nw:!!x.due,late:!!x.due&&late,empty:!x.due,cls:late?"late":""});
  $("#pkProps").replaceChildren(...peekPropNodes(L));
  $("#pkProps2").replaceChildren(...peekPropNodes(k==="raid"?[{f:"imp",name:"Impact",mark:{icon:"alert"},value:"Impact: "+(x.imp||"Medium")},{f:"lik",name:"Likelihood",mark:{icon:"alert"},value:"Likelihood: "+(x.lik||"Medium")}]:[])); })();
  if(shared.CUR&&shared.CUR.mode==="proposal"&&!(shared.PKPOP&&$("#pkProps").contains(shared.PKPOP.anchor))&&!$('#pkProps [data-pkp="p"]'))
    $("#pkProps").append(...peekPropNodes([{f:"p",name:"Project",mark:{icon:"projects"},value:x.p?pName(x.p):"Choose a project",empty:!x.p}])); }
export function pkDrawText(x,k){ const t=$("#pkTitle"), d=$("#pkDesc"), f=pkDescF(k);
  t.setAttribute("aria-label",pkTitleL(k)); if(document.activeElement!==t) t.textContent=x.t||"";
  $("#pkDescL").textContent=pkDescL(k,x); d.dataset.pkf=f; d.dataset.ph=pkDescPh(k,x); d.setAttribute("aria-label",pkDescL(k,x)); if(document.activeElement!==d) d.textContent=x[f]||""; }
export function pkDraw(){ const x=curObj(), k=shared.CUR.k; if(!x){ closePanel(); return; }
  const key=shared.CUR.mode+":"+k+":"+(pkCid()||shared.CUR.n), fresh=PK.key!==key;
  if(shared.PKPOP&&!fresh){ PK.redraw=true; return; } closePicker("owner",false);
  if(fresh){ PK.key=key; PK.tab="all"; PK.pc=null; pkNote(""); }
  const a=document.activeElement, af=!fresh&&a&&a.closest&&a.closest("#panel [data-pkp]")?a.dataset.pkp:null;   /* a redraw keeps the focus on the same chip */
  pkUpdReset(!!shared.CUR.upd); pkDrawId(x,k); pkDrawProps(x,k); pkDrawText(x,k); PKDRAW.forEach(f=>f(x,k,fresh));
  if(fresh) $("#pkScroll").scrollTop=0;
  if(af&&!document.activeElement.closest("#panel")){ $(`#panel [data-pkp="${af}"]`)?.focus(); } }
/* a field asked for when the item opens (a value clicked in a row): focus its chip or its text */
/* ---- pickers ---- */
shared.PKPOP=null;
/* BL-316: the pickers are the Picker block's (components/Picker.jsx). A picker opened from the peek redraws it when a change
   came in while it was open (PK.redraw), with focus back on the same control. */
export function pkPopDone(anchor){ const f=anchor&&anchor.dataset?anchor.dataset.pkp:null;
  return how=>{ if(!PK.redraw) return false; PK.redraw=false; if(pkOn()) pkDraw(); if(how!=="away"&&f) $(`#panel [data-pkp="${f}"]`)?.focus(); return true; }; }
export const PKMON=["January","February","March","April","May","June","July","August","September","October","November","December"];
export const pkDow=iso=>(new Date(iso+"T00:00:00Z").getUTCDay()+6)%7;
/* ---- committing ---- */
/* v2.3.0 #153: what More › Copy ID and title puts on the clipboard: the ID, two spaces, the item's own title */
export const pkIdText=(id,x)=>`${id}  ${String((x&&x.t)||"").replace(/\s+/g," ").trim()}`.trimEnd();
export const pkSame=(a,b)=>typeof b==="boolean"?!!a===b:String(a??"").trim()===String(b??"").trim();
/* one change to one item: the fields that differ, written by pkWrite. Calls queue (PKQ), so changes are written in the order made. */
shared.PKQ=Promise.resolve();
export function pkCommit(k,id,patch,label,from,to,o={}){ const now=o.now||pkNow(k,id,patch);   /* BL-304: on screen at once; written in turn */
  const run=shared.PKQ.then(()=>pkCommit1(k,id,patch,label,from,to,now?{...o,now}:o)); shared.PKQ=run.catch(()=>false); return run; }
/* BL-304: an existing item's change goes on the record and the screen now, marked as saving, before it waits its turn to be staged */
export function pkNow(k,id,patch){ if(/^(nw|rv)/.test(String(id))) return null; const x=pkX(k,id); if(!x) return null;
  const keys=Object.keys(patch).filter(n=>!pkSame(x[n],patch[n])); if(!keys.length) return null;
  const P2=Object.fromEntries(keys.map(n=>[n,patch[n]])); if("o" in P2&&!P2.o) P2.o="TBC";
  const was=Object.fromEntries(keys.map(n=>[n,x[n]])), ov={k,id,f:P2};
  Object.assign(x,P2); if(k==="raid") x.pr=prio(x.imp,x.lik); ovAdd([ov]); if(shared.CUR&&pkCid()===id) pkSaving("busy"); refreshAll();
  return {P2,was,ov}; }
export async function pkCommit1(k,id,patch,label,from,to,o){ const x=pkX(k,id); if(!x) return false;
  if(o.now){ if(!o.keepNote&&shared.CUR&&pkCid()===id) pkNote(""); const ok=await pkWrite(k,id,o.now.P2,{label,from,to,...o,retry:{patch,label,from,to,o}}); if(!ok&&shared.CUR&&pkCid()===id&&pkOn()) pkDraw(); return ok; }
  const keys=Object.keys(patch).filter(n=>!pkSame(x[n],patch[n])); if(!keys.length) return false;
  const P2=Object.fromEntries(keys.map(n=>[n,patch[n]])); if("o" in P2&&!P2.o) P2.o="TBC";
  if(!o.keepNote&&shared.CUR&&pkCid()===id) pkNote("");   /* a rule's note stays until the next change; o.note goes in the feed */
  const ok=await pkWrite(k,id,P2,{label,from,to,...o}); if(!ok&&shared.CUR&&pkCid()===id&&pkOn()) pkDraw(); return ok; }
/* replaced by the staging below; until then the change is saved through commitRecord, as the panel's Save did */
export async function pkWrite(k,id,P2,o){ const r=await (async()=>{
  if(String(id).startsWith("nw")){
    const x=pkX(k,id); if(!x) return false; const prev=Object.fromEntries(Object.keys(P2).map(n=>[n,x[n]]));
    Object.assign(x,P2); if(k==="raid") x.pr=prio(x.imp,x.lik);
    const r=await pkNewSync(k,id);
    if(r==="fail"){ Object.assign(x,prev); if(k==="raid") x.pr=prio(x.imp,x.lik); } else if(r==="ok"&&o.note) pkNote(o.note);
    if(shared.CUR&&shared.CUR.nid===id&&pkOn()) pkDraw(); pkNewFocus(); return r!=="fail"; }   /* BL-179: a new item */
  if(String(id).startsWith("rv")){
    const x=pkX(k,id); if(!x) return false; Object.assign(x,P2); if(k==="raid") x.pr=prio(x.imp,x.lik); PK.dirty=true; if(o.note) pkNote(o.note); pkDraw(); return true; }   /* BL-250 A: a proposal */
  const x=pkX(k,id), now=o.now;
  /* BL-304: a change already on screen (pkNow) that can't be staged is put back, says why and offers Retry */
  const back=msg=>{ if(now){ ovDrop([now.ov]); for(const n in now.P2) if(pkSame(x&&x[n],now.P2[n])&&x) x[n]=now.was[n]; if(x&&k==="raid") x.pr=prio(x.imp,x.lik); ovReapply(); refreshAll(); }
    pkSaving("fail"); if(msg) snack(msg,now&&o.retry?()=>{ const r=o.retry; pkCommit(k,id,r.patch,r.label,r.from,r.to,{...r.o,now:undefined}); }:null,"Retry"); return false; };
  if(!x) return back(""); if(!await needVault()) return back("");
  const first=!shared.PKS.some(s=>s.k===k&&s.id===id), item={op:"update",table:k,id,changes:toDb(k,P2)}; if(first&&x.updated_at) item.based_on=x.updated_at; if(o.logNote) item.note=o.logNote;   /* v2.3.0 #153: history only (Activity), like a milestone's reason */
  pkSaving("busy"); let name; const items=[...(o.pre||[]),item];   /* BL-187: a new workstream travels ahead of the item, in the same proposal */
  const prev=now?Object.fromEntries(Object.keys(P2).map(n=>[n,now.was[n]??""])):Object.fromEntries(Object.keys(P2).map(n=>[n,x[n]??""]));
  const meta={k,id,patch:P2,prev,label:o.label,from:o.from==null?"":String(o.from),to:o.to==null?"":String(o.to),at:nowStamp(),note:o.note||"",type:o.type||"act",ms:Date.now(),...(o.wsRow?{wsNew:o.wsRow.name,wsP:o.wsRow.p}:{})};   /* BL-188: what every window needs to show it */
  try{ name=await vq(async()=>{ let n=pkFile(); while(await shared.VW.exists("system/staging/"+n)) n=pkFile();
      const data={created:stampFull().replace(" ","T"),source_run:"dashboard",files:[],peek:meta,items:items.map((it,j)=>Object.assign({n:j+1,match:"strong",flags:[],decision:"approved"},it))};
      await shared.VW.write("system/staging/"+n,JSON.stringify(data,null,2)+"\n"); return n; }); }
  catch(e){ return back("Not saved: "+e.message); }
  Object.assign(x,P2); if(k==="raid") x.pr=prio(x.imp,x.lik); if(now) ovDrop([now.ov]);   /* staged: pkReconcile keeps it on screen from here */
  if(o.wsRow) (D.ws_table=D.ws_table||[]).push(o.wsRow);   /* BL-187 */
  shared.PKS.push({name,...meta});
  pkPersist(); pkSaving("ok"); refreshAll(); return true; })();
  if(String(id).startsWith("nw")&&shared.CUR&&shared.CUR.nid===id){ clearTimeout(shared.PKNT); pkNewStore(); } return r; }
export function pkSetStatus(k,id,v){ const x=pkX(k,id); if(!x||x.st===v) return; const patch={st:v}; let n="";
  if(k==="decisions"){ if(x.st==="Made"&&v==="Pending"){ pkNote("A decision that has been made can't go back to pending; record a new one that replaces it."); return; }
    if(v==="Made"&&!x.date){ patch.date=TODAY; n=`Date made set to ${fd(TODAY)}`; } if(v==="Pending"&&x.date){ patch.date=""; n="Date made cleared: it is pending again"; } }
  else if(!OPENST(v)&&OPENST(x.st)){ patch.closed=TODAY; n=`Closed date set to ${fd(TODAY)}`; }
  else if(OPENST(v)&&x.closed){ patch.closed=""; n="Closed date cleared"; }
  return pkCommit(k,id,patch,"Status",x.st,v,{note:n}); }   /* BL-231: the final version (BL-176 rules), folded from its replacement at load */
export function pkStOpt(k,x,s){ return shared.CUR&&shared.CUR.mode==="new"&&k==="decisions"&&s==="Withdrawn"?{disabled:true,hint:"A new decision is pending or made"}:k==="decisions"&&x.st==="Made"&&s==="Pending"?{disabled:true,hint:"A made decision can't go back to pending; record a new one that replaces it"}:{}; }   /* a new decision is pending or made: withdrawing one that doesn't exist yet means not creating it */
export async function pkOwner(k,id,v,typed){ const x=pkX(k,id), f=pkOwnF(k); if(!x) return; let n=v;
  if(typed){ n=await ownerFinal(v); if(n===null) return; }
  return pkCommit(k,id,{[f]:n},pkOwnL(k),pkWho(x[f])||"Unassigned",pkWho(n)||"Unassigned"); }
export function pkOpenProp(f,anchor){ const x=curObj(), k=shared.CUR.k, id=pkCid(); if(!x) return;
  const onClose=pkPopDone(anchor);
  if(f==="st") openPicker(anchor,{label:"Status",value:x.st,onClose,options:pkStatuses(k).map(s=>({v:s,label:s,mark:peekMark({st:s}),...pkStOpt(k,x,s)})),onPick:v=>pkSetStatus(k,id,v)});
  else if(f==="pr") openPicker(anchor,{label:"Priority",value:x.pr,onClose,options:["Urgent","High","Medium","Low"].map(v=>({v,label:v,mark:peekMark({pr:v})})),onPick:v=>pkCommit(k,id,{pr:v},"Priority",x.pr,v)});
  else if(f==="o") pkOwnerList(anchor,x,k,id);   /* BL-187 (fix-peek-140): the list, with the register's suggestions, is below */
  else if(f==="due") itemDatePicker(anchor,{value:x.due,due:true,label:pkLabel(k,"due",x),onClose,onPick:v=>pkCommit(k,id,{due:v},pkLabel(k,"due",x),fd(x.due)||"none",fd(v)||"none")});
  else if(f==="date") itemDatePicker(anchor,{value:x.date,label:"Date made",onClose,onPick:v=>pkSetDate(k,id,v)});
  else if(f==="imp"||f==="lik"){ const nm=PKFL[f]; openPicker(anchor,{label:nm,value:x[f],onClose,options:["High","Medium","Low"].map(v=>({v,label:v})),onPick:v=>pkImpLik(k,id,f,v)}); }
  else if(f==="type") openPicker(anchor,{label:"Type",value:x.type,onClose,options:["Risk","Issue","Assumption","Dependency"].map(v=>({v,label:v,hint:RESPL(v)})),onPick:v=>pkCommit(k,id,{type:v},"Type",x.type,v)});
  else if(PKPROP[f]) PKPROP[f](anchor,x,k,id); }
export const PKPROP={};                                   /* Details' pickers, added below */
export function pkSetDate(k,id,v){ const x=pkX(k,id); if(!x) return; if(!v&&x.st==="Made"){ pkNote("A decision that is made needs the date it was made. Not changed."); return; }
  return pkCommit(k,id,{date:v},"Date made",fd(x.date)||"none",fd(v)||"none"); }
export function pkImpLik(k,id,f,v){ const x=pkX(k,id); if(!x||x[f]===v) return; const before=prio(x.imp,x.lik), after=prio(f==="imp"?v:x.imp,f==="lik"?v:x.lik);
  return pkCommit(k,id,{[f]:v},PKFL[f],x[f],v,{note:after!==before?`Priority recalculated: ${before} → ${after}`:""}); }
export function pkText(k,id,f,el){ { const d=DRPEND[id+"|"+f]; if(d){ delete DRPEND[id+"|"+f]; draftStat(d.feature,drSame(el.textContent,d.text)?"used":"edited"); } }
  const x=pkX(k,id); if(!x) return; const ml=!!el.dataset.pkml, raw=el.textContent.replace(/ /g," "), val=ml?raw.replace(/^\s+|\s+$/g,""):raw.replace(/\s+/g," ").trim();
  if(pkSame(x[f],val)) return; const r=pkTextRule(k,id,f,val,el,x); if(r===false) return;
  return pkCommit(k,id,{[f]:val},pkLabel(k,f,x),x[f]||"",val,{type:f===pkDescF(k)?"upd":"act"}); }
export function pkTextRule(k,id,f,val,el,x){ if(f==="revisit"&&!WK.ok){ const iso=DDATE.test(val)?toIso(val):DATE.test(val)?val:"";
      if(iso&&wkAsk(iso,el,v=>pkCommit(k,id,{revisit:DDATE.test(val)?fd(v):v},"Revisit",x.revisit||"",DDATE.test(val)?fd(v):v))){ el.textContent=x.revisit||""; return false; } }
  if(f==="t"&&!val){ el.textContent=x.t||""; pkNote(`${pkTitleL(k)} is needed, so the old one was kept.`); return false; }
  if(f==="cm"||f==="cmd"){ const ok=pkMsgOK(k,val);
    if(f==="cm"&&val&&!cmHeads(val)){ el.textContent=x.cm||""; pkNote("Keep the three client messaging headings, with a few words after each."); return false; }
    if(PK.pc&&PK.pc.id===id){ if(ok){ PK.pc=null; pkCommit(k,id,{client:true,[f]:val},"Client-visible","No","Yes",{note:"Client messaging written first, as the rule requires"}); }
      else pkNote(k==="decisions"?"Client messaging needs a short plain explanation before this can be client-visible. Nothing saved.":"Client messaging needs a few words after each heading before this can be client-visible. Nothing saved.");
      return false; }
    if(x.client&&!ok){ el.textContent=x[f]||""; pkNote("A client-visible item needs client messaging, so the old wording was kept."); return false; } }
  return true; }
/* ===== end BL-176 (title and key row) ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootPanel0166(){
Object.assign(ICONS,{user:'<path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 20c1-4 4-6 8-6s7 2 8 6"/>',alert:'<path d="M12 8v5M12 17h.01M10.3 4l-8 14a2 2 0 0 0 1.7 3h16a2 2 0 0 0 1.7-3l-8-14a2 2 0 0 0-3.4 0z"/>',
  chevleft:'<path d="M15 6l-6 6 6 6"/>',chevright:'<path d="M9 6l6 6-6 6"/>'});
addHTML($("#pkBar"),"beforeend",raw(ibtn("more","More",'id="pkMore" aria-haspopup="menu"')));
addHTML($("#pkBar"),"afterend",html`<div class="pk-scroll" id="pkScroll"><div class="pk-id" id="pkId"></div><div id="pkWarn"></div>
  <h2 class="pk-title pked" id="pkTitle" data-pkf="t" contenteditable="plaintext-only" role="textbox" spellcheck="true" data-ph="Add a title"></h2>
  <div class="pk-props" id="pkProps" role="group" aria-label="Key fields"></div><div class="pk-props sec" id="pkProps2" role="group" aria-label="Impact and likelihood"></div>
  <div class="pk-note" id="pkNote" role="status" hidden></div>
  <div class="pk-dlrow"><div class="pk-dl" id="pkDescL"></div><span class="pk-dldr" id="pkDescDr"></span></div><div class="pk-desc pked" id="pkDesc" contenteditable="plaintext-only" role="textbox" aria-multiline="true" data-pkml="1" spellcheck="true"></div>
  <div id="pkAfter"></div></div>`);
pkEdMount($("#pkScroll"));
$("#pkScroll").addEventListener("scroll",()=>{ if(shared.PKPOP&&$("#pkScroll").contains(shared.PKPOP.anchor)) closePicker("away"); });   /* a click away and a resize: the block's own */
$("#panel").addEventListener("click",e=>{ const c=e.target.closest("[data-pkp]"); if(!c||!pkOn()||c.classList.contains("ro")) return; e.preventDefault();
  if(pickerOpenFor(c)){ closePicker("owner"); return; } pkOpenProp(c.dataset.pkp,c); });
/* text: commits on leaving the field; Enter ends a one-line field; Esc puts the text back */
document.addEventListener("focusin",e=>{ const el=e.target.closest&&e.target.closest("#panel [data-pkf][contenteditable]"); if(!el||!shared.CUR) return; el.dataset.orig=el.textContent; PK.focus={k:shared.CUR.k,id:pkCid(),f:el.dataset.pkf,el}; });
document.addEventListener("focusout",e=>{ const el=e.target.closest&&e.target.closest("#panel [data-pkf][contenteditable]"); if(!el||!PK.focus||PK.focus.el!==el) return; const {k,id,f}=PK.focus; PK.focus=null;
  if(el.dataset.skip){ delete el.dataset.skip; return; } pkText(k,id,f,el); });
window.addEventListener("keydown",e=>{ const el=e.target.closest&&e.target.closest("#panel [data-pkf][contenteditable]"); if(!el) return;
  if(e.key==="Escape"){ e.preventDefault(); e.stopImmediatePropagation(); el.textContent=el.dataset.orig??el.textContent; el.dataset.skip="1"; el.blur(); return; }
  if(e.key==="Enter"&&!e.shiftKey&&!e.metaKey&&!e.ctrlKey&&!el.dataset.pkml){ e.preventDefault(); el.blur(); } },true);
/* More: mark done (or made), ask creaite about it, copy the ID and title */
$("#pkMore").onclick=()=>{ const x=curObj(), k=shared.CUR.k, id=pkCid(), b=$("#pkMore"); if(menuOpenFor(b)){ closeMenu(); return; }
  const can=k==="decisions"?x.st==="Pending":OPENST(x.st);   /* BL-316: the Menu block's menu (openMenu) */
  openMenu(b,{label:"More",id:"pkMoreMenu",align:"right",items:[{id:"done",name:k==="decisions"?"Mark as made":"Mark done",icon:"check",disabled:!can,line:can?"":"Already complete"},{id:"ask",name:"ask creaite about this",icon:"chat"},{id:"id",name:"Copy ID and title",icon:"copy"}],
    onPick:v=>{ if(v==="done") pkSetStatus(k,id,k==="decisions"?"Made":"Closed");
      if(v==="ask"){ openChat(); setTimeout(()=>{ const t=$("#chIn"); if(t&&!t.value.trim()){ t.value=`About ${id} (${x.t}): `; t.dispatchEvent(new Event("input",{bubbles:true})); t.focus(); } },60); }
      if(v==="id"){ const txt=pkIdText(id,x), done=()=>snack(`Copied ${id} and its title`); if(navigator.clipboard) navigator.clipboard.writeText(txt).then(done,()=>prompt("Copy this ID and title:",txt)); else prompt("Copy this ID and title:",txt); } }}); };   /* v2.3.0 #153: the ID, two spaces, the title */
if(shared.CUR&&$("#panel").classList.contains("on")) drawPanel();
}
/* ===== BL-176 (sprint-peek) ===== staging. Each commit is its own proposal (Alan, 10-10-2026: edits to one item are not merged),
   written to system/staging/ the way the panel's Save wrote one (writeProposal's format: source_run "dashboard", already approved),
   but never applied on the spot, whatever auto-apply says: nothing reaches tracker.db until Apply. The file names sort in the order
   the changes were made (milliseconds), so an apply takes them in that order. Only an item's first staged change carries based_on
   (the row's updated_at); a later one on the same item would otherwise be held as a conflict with the first. PKS lists what is
   staged here (kept in this browser, so a reload brings the pill back; each entry is checked against staging when the page loads
   and after every apply). Undo last removes the newest of them, only while its file is still in staging with nothing applied,
   through /api/fs's existing remove (which allows only the dashboard's own proposals). Apply is the existing apply (/api/apply). */
export const PKSTORE="creaite-peek-staged";
export function pkPersist(){ try{ localStorage.setItem(PKSTORE,JSON.stringify(shared.PKS)); }catch(e){} }
export function pkFile(){ const d=new Date(); return `proposed-${stampFile()}-${String(d.getMilliseconds()).padStart(3,"0")}${String(shared.PKSEQ++%100).padStart(2,"0")}-dashboard.json`; }
export const pkStagedOf=id=>shared.PKS.filter(s=>s.id===id);
export function pkSaving(state,msg){ const el=$("#pkSave"); if(!el) return; el.classList.toggle("fail",state==="fail");
  putHTML(el,state==="busy"?msg||"Saving…":state==="fail"?msg||"Not saved":state==="ok"?html`${raw(ic("check"))}${(msg||"Saved to staging")}`:""); }
export function pkStageDraw(){ const st=$("#pkStage"), n=shared.PKS.length, m=new Set(shared.PKS.map(s=>s.id)).size; st.hidden=!n; document.body.classList.toggle("pkstaged",!!n);
  if(n) $("#pkStN").textContent=`${n} change${n===1?"":"s"} staged on ${m} item${m===1?"":"s"}`; }
export function pkLast(x,k){ let el=$("#pkLast"); if(!el){ addHTML($("#pkAfter"),"afterbegin",html`<div class="pk-last" id="pkLast"></div>`); el=$("#pkLast"); }
  if(shared.CUR.mode!=="record"){ el.textContent=""; pkSaving(""); return; }
  const s=pkStagedOf(pkCid()), d=shared.PKDONE.filter(e=>e.id===pkCid());
  putHTML(el,html`${raw(ic("history"))}<span>${s.length?html`You edited this ${s[s.length-1].at.slice(11)===nowStamp().slice(11)?"just now":raw("at "+s[s.length-1].at.slice(11))} · ${s.length} change${s.length===1?"":"s"} staged`:d.length?html`Last applied ${fd(d[d.length-1].at)}`:x.upd_at?html`Last updated ${fd(x.upd_at)}`:""}</span>`);
  pkSaving(s.length?"ok":d.length?"ok":"",s.length?"Saved to staging":d.length?"Applied":""); }
/* the dot on a row with something staged: the StatusDot block, named by its word (BL-316) */
export function markStagedRows(){ const ids=new Set([...shared.PKS.map(s=>s.id),...(shared.PENDING||[]).flatMap(p=>p.ids||[])]), sv=savingIds();   /* BL-304: also a change still saving (hollow), and one waiting for Apply */
  $$("#workTbl tr[data-row],#v-person tr[data-row],#workBoard .bcard[data-row]").forEach(r=>{ const id=r.dataset.row, st=sv.has(id)?"saving":ids.has(id)?"staged":"", d=/** @type {HTMLElement|null} */ (r.querySelector(".pkdot"));
    if(d&&d.dataset.st!==st) d.remove(); if(!st||(d&&d.dataset.st===st)) return;
    const x=r.querySelector("td.title>.x"), dot=statusDotNodes({status:"staged",cls:st==="saving"?"pkdot saving":"pkdot",label:st==="saving"?"Saving…":"Staged, not yet applied"});
    /** @type {HTMLElement} */ (dot[0]).dataset.st=st;
    if(x) x.before(...dot); else (r.querySelector("td.title")||r.firstElementChild||r).append(...dot); }); }
/* after any apply or reload: what left staging was applied; what is still there stays staged and is shown again on the fresh data */
export let PKREC=null;
export async function pkReconcile(){ pkFromVault(); const news=shared.PKS.filter(s=>s.isNew), r=await (async()=>{ if(!shared.PKS.length) return; if(PKREC) return PKREC; PKREC=(async()=>{ const keep=[], gone=[];
    for(const s of shared.PKS){ let there=true; try{ there=await shared.VW.exists("system/staging/"+s.name); }catch(e){} (there?keep:gone).push(s); }
    if(gone.length){ PKAPPLIED.add(D.latest_apply); gone.forEach(s=>shared.PKDONE.push({...s,state:"applied",apply_id:D.latest_apply,at:nowStamp()})); }
    shared.PKS=keep; shared.PKS.forEach(s=>{ const x=pkX(s.k,s.id); if(x){ Object.assign(x,s.patch); if(s.k==="raid") x.pr=prio(x.imp,x.lik); } });
    pkPersist(); refreshAll(); return gone.length; })(); try{ return await PKREC; } finally{ PKREC=null; } })();
    for(const s of news){ if(shared.PKS.includes(s)) continue; const id=pkNewFound(s); if(!id) continue; if(!PKNEWIDS.includes(id)) PKNEWIDS.push(id);
      shared.PKDONE.push({...s,id,label:"Created",state:"applied",apply_id:D.latest_apply,at:nowStamp()});
      if(shared.CUR&&shared.CUR.mode==="new"&&shared.CUR.nid===s.id){ shared.CUR={mode:"record",k:s.k,id}; shared.SEL=id; PKN.bad=null; if(shared.VIEW==="work"||shared.VIEW==="mine"||shared.VIEW==="person") markSel(); drawPanel(); navWrite(false); } }
  return r; }
export async function pkApply(){ PKNEWIDS=[]; await shared.PKQ; const n=shared.PKS.length; if(!n) return 0;
  if(!viaServer()){ snack("Applying needs the live server: start it, or say “apply” in Claude Code"); return -1; }
  $("#pkApply").disabled=true; pkSaving("busy","Applying…");
  try{ const r=await applyNow({peek:true}); await pkReconcile();
    if(!r.ok){ pkSaving("fail","Not applied"); snack("Apply stopped: "+oneLine(r.message)); return -1; }
    const done=n-shared.PKS.length; if(shared.CUR&&pkOn()) pkDraw();
    snack(done?`Applied ${done} change${done===1?"":"s"}${PKNEWIDS.length?` (${PKNEWIDS.join(", ")} created)`:""}${shared.PKS.length?`; ${shared.PKS.length} still staged (changed elsewhere since)`:""}. A backup was taken first`:"Nothing applied: "+oneLine(r.message),done?()=>undoApply(r.apply_id):null);   /* BL-179: names what it created */
    return done; } finally{ $("#pkApply").disabled=false; } }
export async function pkUndoLast(only){ await shared.PKQ; const s=only||shared.PKS[shared.PKS.length-1];   /* only: undo exactly this staged entry (#153), not the last one */
  if(only&&!shared.PKS.includes(only)){ snack("Already applied or undone"); return; }
  await (async()=>{ if(!s) return; let ok=false;
  try{ ok=await vq(async()=>{ const path="system/staging/"+s.name; if(!/-dashboard(-\d+)?\.json$/.test(s.name)||!await shared.VW.exists(path)) return false;
      const data=JSON.parse(await shared.VW.read(path)); if(data.source_run!=="dashboard"||(data.items||[]).some(i=>i.applied)) return false;
      await shared.VW.remove(path); return true; }); }catch(e){ ok=false; }
  { const i=shared.PKS.indexOf(s); if(i>=0) shared.PKS.splice(i,1); }
  if(!ok){ pkPersist(); refreshAll(); snack("Already applied: undo it in Activity"); return; }
  const x=pkX(s.k,s.id); if(x){ for(const n in s.prev) if(pkSame(x[n],s.patch[n])) x[n]=s.prev[n]; if(s.k==="raid") x.pr=prio(x.imp,x.lik); }
  pkPersist(); refreshAll(); snack(`Undone: ${s.id} ${String(s.label||"").toLowerCase()}`); })();
    if(s&&s.isNew&&!shared.PKS.includes(s)){ if(shared.CUR&&shared.CUR.mode==="new"&&shared.CUR.nid===s.id){ shared.CUR.staged=null; pkDraw(); } snack(`Undone: the new ${pkNewWord(s.k)} “${pkShort(s.title,40)}” is no longer staged`); }
    if(s&&s.wsNew&&!shared.PKS.includes(s)){ const i=WSD().findIndex(w=>!w.id&&w.p===s.wsP&&w.name===s.wsNew); if(i>=0){ D.ws_table.splice(i,1); refreshAll(); } } }
 
/* ===== end BL-176 (staging) ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootPanel0167(){
/* the pill */
addHTML(document.body,"beforeend",html`<div class="pkstage" id="pkStage" role="region" aria-label="Staged changes" hidden><small>Nothing reaches the tracker until you apply</small><button type="button" class="pkbtn" id="pkUndo">Undo last</button><button type="button" class="pkbtn go" id="pkApply" data-tip="Apply everything staged" data-key="${raw(MOD)}↵">Apply<span class="pkk" aria-hidden="true">${raw(MOD)}↵</span></button></div>`);
$("#pkStage").prepend(...statusDotNodes({status:"staged",wordId:"pkStN",live:true}));   /* BL-316: the StatusDot block; pkStageDraw writes its word */
PKDRAW.push(pkLast);
$("#pkUndo").onclick=()=>pkUndoLast();
$("#pkApply").onclick=()=>pkApply();
/* a reload: what this browser staged comes back if it is still in staging */
(async()=>{ let L=[]; try{ L=JSON.parse(localStorage.getItem(PKSTORE)||"[]"); }catch(e){} if(!Array.isArray(L)) L=[];
  const keep=[]; for(const s of L){ if(!s||!s.name||!s.k||!s.id) continue; let there=true; try{ there=await shared.VW.exists("system/staging/"+s.name); }catch(e){} if(there) keep.push(s); }
  shared.PKS=keep; pkFromVault(); if(!shared.PKS.length) return; shared.PKS.forEach(s=>{ const x=pkX(s.k,s.id); if(x){ Object.assign(x,s.patch); if(s.k==="raid") x.pr=prio(x.imp,x.lik); } }); pkPersist(); refreshAll(); })();
pkStageDraw();
}
/* ===== BL-176 (sprint-peek) ===== the rules, each as the form applied them (validate, norm, decisionCheck), on the one field changed:
   - Status: Closed or Cancelled sets the closed date to today; back to Open or Delayed clears it (said in the feed).
   - Decisions: a made decision can't go back to Pending (the option is disabled, with the reason); Made fills Date made with today
     when it has none; Date made can't be cleared while it is made.
   - Client-visible without client messaging doesn't save: the switch waits, the messaging opens with focus, and both are staged
     together once the messaging is complete (actions and RAID: a few words after each of the three headings; decisions: a short
     plain explanation). Clearing the messaging of a client-visible item is refused and the wording is put back.
   - An empty title is refused and the old one kept. A bad date says how to write one (the date picker).
   - Impact or Likelihood recalculates Priority, said in the feed.
   - ⌘↵ (Ctrl+↵), as before (Alan, 10-10-2026): commits the field the cursor is in, applies everything staged (the pill's Apply) and
     closes the peek; a picker open closes first; an item waiting for its client messaging stays open and says why; with nothing
     staged it closes and says "Nothing to apply". */
export const pkMsgF=k=>k==="decisions"?"cmd":"cm";
export const pkMsgOK=(k,t)=>k==="decisions"?cmdOK(t):cmOK(t);
export const PKMSGNEED=k=>k==="decisions"?"To make this client-visible, write the plain wording the client will see. Nothing is saved until you do.":"To make this client-visible, complete the client messaging: a few words after each of the three headings. Nothing is saved until you do.";
/* the switch (drawn in Details): on waits for the messaging when it isn't complete; off is staged at once */
export function pkClient(k,id,on){ const x=pkX(k,id); if(!x) return;
  if(!on){ if(PK.pc&&PK.pc.id===id){ PK.pc=null; pkNote(""); pkDraw(); return; } return pkCommit(k,id,{client:false},"Client-visible","Yes","No"); }
  if(pkMsgOK(k,x[pkMsgF(k)])) return pkCommit(k,id,{client:true},"Client-visible","No","Yes");
  PK.pc={k,id}; PK.det[id]=true; pkNote(PKMSGNEED(k)); pkDraw(); setTimeout(()=>{ const m=$(`#panel [data-pkf="${pkMsgF(k)}"]`); if(m){ m.focus(); const r=document.createRange(); r.selectNodeContents(m); r.collapse(false); const sel=getSelection(); sel.removeAllRanges(); sel.addRange(r); } },0); }
export async function pkSaveAndClose(){ if(shared.CUR&&shared.CUR.mode==="new"&&!PK.closing){
    closePicker("owner",false); const a=document.activeElement; if(a&&a.matches&&a.matches("#panel [data-pkf][contenteditable]")) a.blur(); await pkQuiet();
    if(shared.CUR&&shared.CUR.mode==="new"&&!shared.CUR.staged&&shared.CUR.draft.t&&!PK.pc){ if(!pkNewCheck(shared.CUR.k,shared.CUR.draft)){ pkNewMarkDraw()?.focus(); return; } await pkNewSync(shared.CUR.k,shared.CUR.nid,true); if(!shared.CUR||!shared.CUR.staged) return; }
    if(shared.CUR&&shared.CUR.mode==="new"&&shared.CUR.alertDone) return alertStaged(); }   /* check 45 (BL-334): made from a message, staged for Review only, never applied here */
  if(shared.CUR&&shared.CUR.mode==="proposal") return pkPropSave(false);
  if(PK.closing) return; PK.closing=true;
  try{ closePicker("owner",false);
    const a=document.activeElement; if(a&&a.matches&&a.matches("#panel [data-pkf][contenteditable]")) a.blur();   /* commits the field (queued) */
    await shared.PKQ;
    if(PK.pc){ pkNote(`${PKMSGNEED(PK.pc.k)} Or turn Client-visible off. Then press ${MOD}↵ again.`); $(`#panel [data-pkf="${pkMsgF(PK.pc.k)}"]`)?.focus(); return; }
    if(!shared.PKS.length){ closePanel(); snack("Nothing to apply"); return; }
    const n=await pkApply(); if(n>=0) closePanel(); } finally{ PK.closing=false; } }
/* ===== end BL-176 (rules) ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootPanel0168(){
/* BL-274: the peek registers its ⌘↵ (BL-176): from the peek, its pop-ups, the staged list, or a row or link in the list behind it */
onCmdEnter("peek",t=>{ if(!pkOn()) return false; const inPage=t.closest&&t.closest(".content")&&!t.closest("input,textarea,select,[contenteditable]");
  return t===document.body||!!inPage||!!(t.closest&&t.closest("#panel,.pkpop,#pkStage")); },()=>pkSaveAndClose());
PK.det={};
}
/* ===== BL-176 (sprint-peek) ===== Details and Activity. Details (BL-154's More fields, renamed) is folded under the free text: Project,
   Workstream and Milestone (actions and RAID), Options considered, Revisit and Replaces (decisions), Raised and Closed (set by
   creaite, read only), Client-visible and Client messaging. It opens by itself for a client-visible item; otherwise it stays as Alan
   left it for that item in this session. A new workstream isn't made here: the list offers the project's own, and a name it doesn't
   have says where to add it. The feed below has All, Activity, Updates and Source (no Comments: Alan, 10-10-2026). It reads the same
   change log lines as the Activity page (ACT, from build_dashboard.activity, with actId), so there is one reading of the history:
   a change staged here shows first, marked "staged", and once applied it is the change log's own line, marked "applied". Updates
   are the changes to the free text (latest update, the response, the reasoning); Source is the item's source and its creation. */
/* BL-301 A: the peek's text fields are the one editor (core/editor.js), as plain text: one paragraph a line, no Markdown, so
   the stored text stays as it was. Their text is read and set by textContent as before (the editor answers for it), so the
   commit on leaving the field, Esc, the rules and the AI drafts are unchanged. */
export function pkEdMount(root){ if(!root) return; root.querySelectorAll(".pked").forEach(el=>{ if(el.cxed) return;
  creaiteEditor(el,{features:"plain",text:el.textContent,multiline:!!el.dataset.pkml,prop:"textContent",links:!!el.dataset.pkml,      /* #121: links in the longer text fields (update, response, reasoning, options, client messaging); not in the title or the one-line fields (keys and short labels) */
    
    ...(el.dataset.pkml||el.id==="pkTitle"?{ai:{place:el.dataset.pkml?"plain":"line",project:()=>{ const x=shared.CUR&&pkX(shared.CUR.k,pkCid()); return (x&&x.p)||""; }}}:{})}); }); }   /* BL-301 D: AI on a selection in the longer fields, and the title (one line: place "line", a suggestion never breaks it) */
export const pkDetOpen=(x,id)=>!!((PK.pc&&PK.pc.id===id)||(id in PK.det?PK.det[id]:!!x.client));
export function pkDetails(x,k){ const id=pkCid(), open=pkDetOpen(x,id), tg=$("#pkDetT"); tg.setAttribute("aria-expanded",String(open)); $("#pkDet").hidden=!open; if(!open) return;
  const body=$("#pkDet"); if(body.contains(document.activeElement)&&document.activeElement.isContentEditable) return;   /* never under the cursor */
  if(shared.PKPOP&&body.contains(shared.PKPOP.anchor)) return;
  const af=body.contains(document.activeElement)?(document.activeElement.dataset.pkp||document.activeElement.dataset.pksw):null;
  const row=(icon,label,val)=>`<div class="pk-drow"><div class="lab">${ic(icon)}<span>${label}</span></div><div>${val}</div></div>`;
  const vb=(f,label,txt,empty)=>`<button type="button" class="pk-vbtn${empty?" empty":""}" data-pkp="${f}" aria-haspopup="listbox" aria-label="${esc(label)}: ${esc(empty?"not set":txt)}">${esc(txt)}</button>`;
  const tx=(f,ph,ml)=>`<div class="pk-vtext pked" contenteditable="plaintext-only" role="textbox" data-pkf="${f}"${ml?' data-pkml="1" aria-multiline="true"':""} data-ph="${esc(ph)}" aria-label="${esc(pkLabel(k,f,x))}">${esc(x[f]||"")}</div>`;
  let h=row("projects","Project",vb("p","Project",pName(x.p)||"Choose a project",!x.p));
  if(k!=="decisions") h+=row("layers","Workstream",vb("ws","Workstream",x.ws||"Add workstream",!x.ws))+row("flag","Milestone",vb("ms","Milestone",x.ms?msName(x.ms):"Add milestone",!x.ms));
  if(k==="decisions"){ h+=row("layers","Options considered",tx("opts","Add the options considered",true))+row("clock","Revisit",tx("revisit","A date, or a trigger in words",false))
      +row("undo","Replaces",vb("replaces","Replaces",x.replaces?`${x.replaces} · ${decShort((DEC.find(d=>d.id===x.replaces)||{t:""}).t,50)}`:"None",!x.replaces));
    if(x.rby) h+=row("undo","Replaced by",`<div class="pk-vro"><a href="#" class="hlink" data-open="decisions:${esc(x.rby)}">${esc(x.rby)}</a></div>`); }
  if(x.raised||k!=="decisions") h+=row("calendar","Raised",`<div class="pk-vro">${x.raised?fd(x.raised):"—"} <span class="sub">· set when it was raised</span></div>`);
  if(k!=="decisions"&&!OPENST(x.st)) h+=row("check","Closed",`<div class="pk-vro">${x.closed?fd(x.closed):"—"} <span class="sub">· set when the status changed</span></div>`);
  const on=!!(x.client||(PK.pc&&PK.pc.id===id));
  h+=row("eye","Client-visible",`<button type="button" class="pk-sw" role="switch" aria-checked="${on}" aria-label="Client-visible" data-pksw="client"></button>`);
  if(on){ const f=pkMsgF(k);   /* actions and RAID: an empty messaging offers its three headings */
    h+=row("msg","Client messaging",`<div class="pk-vtext pked" contenteditable="plaintext-only" role="textbox" data-pkf="${f}" data-pkml="1" aria-multiline="true" data-ph="Plain wording for the client" aria-label="Client messaging">${esc(x[f]||(k==="decisions"?"":CMT))}</div>`); }
  putHTML(body,raw(h)); pkEdMount(body); if(af) body.querySelector(`[data-pkp="${af}"],[data-pksw="${af}"]`)?.focus(); }
/* the feed */
export const PKTABS=[["all","All"],["act","Activity"],["upd","Updates"],["src","Source"]];
export const pkUpdLabel=k=>k==="actions"?"latest update":k==="raid"?"response":"reasoning";
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootPanel0169(){
Object.assign(ICONS,{layers:'<path d="M12 3l9 5-9 5-9-5zM3 13l9 5 9-5"/>',msg:'<path d="M4 5h16v11H9l-5 4z"/>',clock:'<path d="M12 7v5l3 2M3 12a9 9 0 1 0 3-6.7M3 4v4h4"/>'});
addHTML($("#pkAfter"),"beforeend",html`<section aria-label="Details"><button type="button" class="pk-dethead" id="pkDetT" aria-expanded="false" aria-controls="pkDet">${raw(ic("chevright"))}Details</button><div class="pk-det" id="pkDet" hidden></div></section>
  <section aria-label="Activity"><div class="tabhost" id="pkTabsHost"></div><div class="pk-feed" id="pkFeed" role="tabpanel" aria-labelledby="pkTabSel"></div></section>`);
PKDRAW.push(pkDetails);
$("#pkDetT").onclick=()=>{ if(!shared.CUR) return; const x=curObj(), open=pkDetOpen(x,pkCid()); PK.det[pkCid()]=!open; pkDetails(x,shared.CUR.k); };
$("#panel").addEventListener("click",e=>{ const sw=e.target.closest("[data-pksw]"); if(!sw||!pkOn()) return; e.preventDefault(); pkClient(shared.CUR.k,pkCid(),sw.getAttribute("aria-checked")!=="true"); });
/* Details' pickers */
PKPROP.p=(a,x,k,id)=>openPicker(a,{label:"Project",value:x.p,onClose:pkPopDone(a),options:P.filter(p=>p.active!==false||p.code===x.p).map(p=>({v:p.code,label:p.name,icon:"projects"})),onPick:v=>{
  if(v===x.p) return; const patch={p:v}, notes=[];
  if(x.ms&&!String(x.ms).startsWith(v+"-M-")){ patch.ms=""; notes.push("milestone cleared: it belongs to "+pName(x.p)); }
  if(x.ws&&!wsFor(v).some(w=>w.toLowerCase()===String(x.ws).toLowerCase())){ patch.ws=""; notes.push("workstream cleared: "+pName(v)+" has none called "+x.ws); }
  pkCommit(k,id,patch,"Project",pName(x.p),pName(v),{note:notes.join("; ")}); }});
PKPROP.ws=(a,x,k,id)=>openPicker(a,{label:"Workstream",search:true,allowNew:true,value:x.ws||"",onClose:pkPopDone(a),options:[...wsFor(x.p).map(w=>({v:w,label:w,icon:"layers"})),{v:"",label:"None"}],onPick:(v,typed)=>{
  if(typed){ const m=wsFor(x.p).find(w=>w.toLowerCase()===v.toLowerCase()); if(!m){ pkNote(`“${v}” isn't one of ${pName(x.p)}'s workstreams yet. Add it in Settings › People and projects › Workstreams, then choose it here.`); return; } v=m; }
  pkCommit(k,id,{ws:v},"Workstream",x.ws||"none",v||"none"); }});
PKPROP.ms=(a,x,k,id)=>openPicker(a,{label:"Milestone",value:x.ms||"",onClose:pkPopDone(a),options:msChoices(x.p,x.ms).map(([v,l])=>({v,label:l,icon:"flag"})),onPick:v=>pkCommit(k,id,{ms:v},"Milestone",x.ms?msName(x.ms):"none",v?msName(v):"none")});
PKPROP.replaces=(a,x,k,id)=>openPicker(a,{label:"Replaces",search:true,value:x.replaces||"",onClose:pkPopDone(a),options:[{v:"",label:"None"},...DEC.filter(d=>d.p===x.p&&d.id!==x.id).map(d=>({v:d.id,label:`${d.id} · ${decShort(d.t,60)}`,icon:"decision"}))],onPick:v=>pkCommit(k,id,{replaces:v},"Replaces",x.replaces||"none",v||"none")});
}
/* ===== BL-250 (fix-history-feed) ===== an item's whole history: its lines in ACT (a link's or label's line, by `sides`, in each item it
   touches, in that item's words), then its older changes past Activity's 2000-row cap (D.activity_older, from build_dashboard) */
export function pkHistory(id){ const own=a=>actId(a)===id||!!(a.sides&&Object.prototype.hasOwnProperty.call(a.sides,id));
  const O=D.activity_older||{}, by=O.by||[];
  return shared.ACT.filter(own).map(a=>a.sides?{...a,change:a.sides[id]}:a)
    .concat(((O.items||{})[id]||[]).map(([at,change,b,apply_id,un])=>({at,change,by:by[b]||"",apply_id,undone:!!un}))); }
/* ===== end BL-250 ===== */
export function pkFeedItems(x,k){ const id=pkCid(), out=[], ul=pkUpdLabel(k);
  pkStagedOf(id).slice().reverse().forEach(s=>out.push({type:s.type==="upd"?"upd":"act",who:"You",html:`changed ${esc(String(s.label||"").toLowerCase())} <span class="chg"><s>${esc(pkShort(s.from))}</s> → <b>${esc(pkShort(s.to))}</b></span>`,when:s.at,state:"staged",note:s.note}));
  out.push(...feedLines(pkHistory(id),ch=>/^created\b/.test(ch)?"src":ch.toLowerCase().startsWith(ul+":")?"upd":"act"));   /* BL-250 A: shared; B: the whole history */
  if(shared.CUR.mode==="record") out.push({type:"src",who:"Source",html:`<div class="pk-src">${srcHTML(x.src)}</div>`,when:""});
  return out; }
export const pkShort=(s,n=60)=>{ s=linkWords(String(s??"")).replace(/\s+/g," ").trim(); return !s?"empty":s.length>n?s.slice(0,n-1)+"…":s; };
export function pkFeed(x,k){ const tab=PK.tab||"all";
  drawTabs($("#pkTabsHost"),{items:feedTabItems(tab,"pktab","pkTabSel"),selected:tab,onSelect:v=>{ if(!shared.CUR) return; PK.tab=v; pkFeed(curObj(),shared.CUR.k); },
    label:"Activity",className:"pk-tabs",tabClass:"pk-tab",id:"pkTabs",wrap:true});   /* BL-316: the Tabs building block */
  if(shared.CUR&&shared.CUR.upd){ updFeed(); return; }   /* #232-B */
  putHTML($("#pkFeed"),raw(feedListHtml(pkFeedItems(x,k),tab))); }
/* ===== end BL-176 (details and activity) ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootPanel0171(){
PKDRAW.push(pkFeed);
if(shared.CUR&&pkOn()) drawPanel();
}
/* ===== BL-177 (sprint-peek) ===== Review's proposals (openProposal) for an action, a RAID item or a decision open in the same peek: the
   title, key row, free text, Details and Source. Nothing here is in the tracker yet, so the edits are held in the panel (CUR.draft)
   until Alan chooses, and it keeps an explicit footer: Reject, Cancel, Save and Save and approve. Save runs the panel's own save
   for proposals (savePanel: the same validation, owner check, norm and editProposal), given the draft in place of the old form's
   fields; ⌘↵ is Save, as before. The "Editing a proposal" line, the "needs a project" note, the duplicate note and the Learn tick
   stay. EDITING stays on for a proposal, as before, so a click away or leaving the page asks Alan to finish or cancel first. Draft
   minutes, files and update proposals keep their own panels. */
export function pkCid(){ return shared.CUR&&shared.CUR.mode==="new"?shared.CUR.nid:shared.CUR?(shared.CUR.mode==="proposal"?"rv"+shared.CUR.n:shared.CUR.id):null; }
export function pkX(k,id){ if(String(id).startsWith("nw")) return shared.CUR&&shared.CUR.mode==="new"&&shared.CUR.nid===id?shared.CUR.draft:null; if(String(id).startsWith("rv")) return shared.CUR&&shared.CUR.mode==="proposal"&&"rv"+shared.CUR.n===id?shared.CUR.draft:null; return REC(k,id); }
export const pkRev=()=>shared.CUR&&shared.CUR.mode==="proposal"?REV.find(r=>r.n===shared.CUR.n):null;
export function pkPropDraw(x,k){ const on=shared.CUR.mode==="proposal"; $("#panel").classList.toggle("pkprop",on);
  const nav=!!(shared.PKSRC&&shared.PKSRC.view&&shared.PKSRC.view===shared.VIEW);   /* #232-B: Intake and Review's proposals step with Previous and Next */
  ["pkLink","pkMore","pkPrev","pkNext","pkExpand"].forEach(id=>{ const b=$("#"+id); if(b) b.hidden=on&&id!=="pkExpand"&&!(nav&&(id==="pkPrev"||id==="pkNext")); }); if(on&&$("#pkChaseBtn")) $("#pkChaseBtn").hidden=true;   /* BL-298 */
  if(!on){ $("#pkPropTop").textContent=""; $("#pkPropEnd").textContent=""; return; }
  const r=pkRev(); if(!r) return;
  if(shared.CUR.upd){ updDraw(x,k,r); return; }   /* #232-B: an update proposal draws the whole item (updDraw) */
  putHTML($("#pkId"),html`<span>Review #${shared.CUR.n}</span><span aria-hidden="true">·</span>${x.p?html`<a href="#" class="hlink" data-proj="${x.p}" data-tip="Open the project page">${pName(x.p)??""}</a>`:html`<span>needs a project</span>`}${k==="raid"?html`<button type="button" class="pk-type" data-pkp="type" aria-haspopup="listbox" aria-label="Type: ${x.type??""}" data-tip="Type">${x.type??""}${raw(ic("chevdown"))}</button>`:""}`);
  putHTML($("#pkPropTop"),html`<div class="pk-propline">Editing a proposal — nothing reaches the tracker until it's approved</div>${x.p?"":html`<div class="cmnote">Choose a project before saving.</div>`}${rvDup(r)&&!r.done?raw(llNoteHtml(r)):""}${raw(rtNoteHtml(r))}`);   /* BL-297 D */
  const sig=learnable(r), was=$("#f_learn")?.checked;
  putHTML($("#pkPropEnd"),sig&&x.p?html`<label class="pk-learn"><input type="checkbox" id="f_learn" data-kind="${sig.kind??""}" data-value="${sig.value??""}"${was?raw(" checked"):""}><span>Remember ${sig.value??""} (${KINDL[sig.kind]||sig.kind||""}) for ${pName(x.p)??""}, so items like this match on their own. Added to the register when applied.</span></label>`:html``);
  putHTML($("#pkFeed"),html`<div class="pk-fe"><span class="pk-fi" aria-hidden="true">${raw(ic("filetext"))}</span><div><b>Source</b><div class="pk-src">${raw(srcHTML(r.src))}</div></div></div>`); }
/* Save: the draft goes through the panel's own save for proposals (readForm is given the draft for that one call) */
export async function pkPropSave(approve){ if(!shared.CUR||shared.CUR.mode!=="proposal"||PK.closing) return; PK.closing=true;
  try{ closePicker("owner",false); const a=document.activeElement; if(a&&a.matches&&a.matches("#panel [data-pkf][contenteditable]")) a.blur(); await shared.PKQ;
    if(shared.CUR.upd){ await updSave(approve); return; }   /* #232-B: an update proposal saves the columns Alan edited (core/irUpdate.js irSaveChanges) */
    if(PK.pc){ pkNote(PKMSGNEED(PK.pc.k)+" Or turn Client-visible off."); return; }
    const x=shared.CUR.draft, k=shared.CUR.k, F=fieldsFor(k,x).filter(f=>f[0]!=="#"&&!["ro","calc","dref"].includes(f[2])).map(f=>f[0]);
    const form=Object.fromEntries(F.map(n=>[n,typeof x[n]==="boolean"?x[n]:String(x[n]??"")]));
    if("cm" in form&&!x.cm&&!x.client) delete form.cm;                       /* an untouched, empty messaging isn't a change */
    if("cmd" in form&&!x.cmd&&!x.client) delete form.cmd;
    // @ts-expect-error TS2630: readForm is swapped for the form's values while savePanel runs (a module may reassign its own function)
    const rf=readForm; readForm=()=>({...form}); $("#pErr").textContent="";
    // @ts-expect-error TS2630: and put back
    try{ await savePanel(approve); } finally{ readForm=rf; }
    const err=$("#pErr").textContent; if(err&&shared.CUR&&shared.CUR.mode==="proposal") pkNote(err); } finally{ PK.closing=false; } }
 
/* ===== end BL-177 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootPanel0173(){
addHTML($("#pkScroll"),"afterend",html`<div class="pk-foot" id="pkFoot2"><button type="button" class="btn" id="pkReject" aria-haspopup="menu" aria-expanded="false">${raw(ic("x"))}Reject</button><span class="sp"></span><button type="button" class="btn" id="pkCancel">Cancel</button><button type="button" class="btn" id="pkPSave" data-key="${MOD}↵" data-tip="Save">Save</button><button type="button" class="btn primary" id="pkPSaveA">Save and approve</button></div>`);
addHTML($("#pkWarn"),"afterend",html`<div class="pk-propnotes" id="pkPropTop"></div>`);
addHTML($("#pkAfter"),"beforeend",html`<div id="pkPropEnd"></div>`);

PKDRAW.push(pkPropDraw);
$("#pkScroll").tabIndex=-1;
$("#pkPSave").onclick=()=>pkPropSave(false);
$("#pkPSaveA").onclick=()=>pkPropSave(true);
$("#pkCancel").onclick=()=>closePanel();
$("#pkReject").onclick=()=>{ const r=pkRev(); if(!r) return; if(rvRejectOK(r)){ rjMenuFor([r],$("#pkReject"),null,()=>closePanel()); return; } closePanel(); isMin(r)?rejectMinutes(r):decide(r.n,"rejected"); };   /* BL-315: the reasons menu; the peek closes on the pick */
/* while a proposal is open, its keys stay in the panel: Review's own (A, R, X, E, J, K, Enter) act on the list's cursor row */
$("#panel").addEventListener("keydown",e=>{ if(shared.CUR&&shared.CUR.mode==="proposal"&&pkOn()&&e.key!=="Escape") e.stopPropagation(); });
if(shared.CUR&&pkOn()) drawPanel();
}
/* ===== BL-175 (sprint-peek) ===== the Keys chip (BL-155) goes from Work and Review: the keys still work, and Help's keyboard table
   (the ? key) lists them; the hint lines under the lists stay in the page, hidden, as the words' one source. Any menu that opens
   from the toolbars is kept inside the window: once it is open, it is moved left (or right) by as much as it would be cut off. */
export function bl175Clamp(m){ if(!m||m.hidden||!m.offsetParent) return; m.style.translate=""; const r=m.getBoundingClientRect(); let dx=0;
  if(r.right>innerWidth-8) dx=innerWidth-8-r.right; if(r.left+dx<8) dx=8-r.left; if(dx) m.style.translate=`${Math.round(dx)}px 0`; }
/* ===== end BL-175 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootPanel0174(){
{ const seen=new WeakMap(), check=()=>$$("#v-work .toolbar .ddmenu,#v-review .toolbar .ddmenu,#wviews .ddmenu").forEach(m=>{ const vis=!!m.offsetParent&&getComputedStyle(m).display!=="none";
    if(vis&&!seen.get(m)) bl175Clamp(m); seen.set(m,vis); });
  ["#v-work .toolbar","#v-review .toolbar","#wviews"].forEach(s=>{ const el=$(s); if(el) new MutationObserver(()=>requestAnimationFrame(check)).observe(el,{subtree:true,childList:true,attributes:true,attributeFilter:["class","hidden"]}); });
  addEventListener("resize",()=>$$("#v-work .toolbar .ddmenu,#v-review .toolbar .ddmenu,#wviews .ddmenu").forEach(m=>{ if(m.offsetParent) bl175Clamp(m); })); }
}
/* ===== BL-179 (sprint-peek-new) ===== New opens the peek, empty (Alan, 11-10-2026: creating an item looks and works like opening one).
   New action, New RAID item, and the Decisions menu's Record a decision and Ask for a decision open the peek with an empty title (the
   cursor in it) and the chips at their defaults: the project from the page (a project page, or Work filtered to one project; with one
   active project, that one; otherwise "Choose a project"), owner TBC ("Add owner"), status Open, priority from
   defaults.new_action_priority, impact and likelihood Medium, RAID's type from Work's Type filter when it names one (otherwise Risk);
   Record a decision: Made, dated today, by Alan; Ask for a decision: Pending, no date, no decision maker. The project is a chip on the
   ID line (and in Details); a new decision has a Source line (where it was decided or raised), which the Create form asked for too.
   Until it is staged, the new item lives in CUR.draft (mode "new", its own ID "nw…" for the peek's helpers); the chips, pickers and
   text are the peek's own. The Create form is no longer opened for these three kinds; milestones and project health keep theirs. */
export const pkNewWord=k=>k==="actions"?"action":k==="raid"?"RAID item":"decision";
export function pkNewProject(){ const ok=c=>P.some(p=>p.code===c&&p.active!==false);
  if(shared.VIEW==="cockpit"&&shared.COCK&&ok(shared.COCK)) return shared.COCK;
  if((shared.VIEW==="work"||shared.VIEW==="mine")&&PROJF.size===1&&!NEG.has("p")){ const c=[...PROJF][0]; if(ok(c)) return c; }
  const act=P.filter(p=>p.active!==false); return act.length===1?act[0].code:""; }
export function pkNewBlank(k,how){ const p=pkNewProject();
  if(k==="actions") return {t:"",p,ws:"",o:"",pr:S.defPriority||"Medium",due:"",st:"Open",raised:TODAY,closed:null,upd:"",client:false,cm:CMT,ms:""};
  if(k==="raid"){ const ty=FX.ty&&FX.ty.size===1&&!NEG.has("ty")?[...FX.ty][0]:"Risk";
    return {type:["Risk","Issue","Assumption","Dependency"].includes(ty)?ty:"Risk",t:"",p,ws:"",o:"",resp:"",imp:"Medium",lik:"Medium",due:"",st:"Open",raised:TODAY,closed:null,client:false,cm:CMT,ms:""}; }
  const d={t:"",p,by:S.me,date:TODAY,client:false,srcIn:"",cmd:"",st:"Made",due:"",why:"",opts:"",revisit:"",replaces:""};
  if(how==="needed") Object.assign(d,{st:"Pending",date:"",by:""});   /* BL-53: a decision asked for */
  return d; }
export function pkNewDraw(x,k){ const on=shared.CUR.mode==="new", s=$("#pkSrcIn"), sl=$("#pkSrcL"), dec=on&&k==="decisions";
  s.hidden=sl.hidden=!dec; if(dec){ s.dataset.ph=x.st==="Pending"?"Where it was raised: a meeting, an email or a document":"Where it was decided: a meeting, an email or a document"; if(document.activeElement!==s) s.textContent=x.srcIn||""; }
  if(!on) return;
  ["pkLink","pkMore","pkPrev","pkNext"].forEach(id=>{ const b=$("#"+id); if(b) b.hidden=true; });
  const word=k==="raid"?"New "+String(x.type||"RAID item").toLowerCase():"New "+pkNewWord(k);
  putHTML($("#pkId"),html`<span class="pk-new">${word}</span><span aria-hidden="true">·</span><button type="button" class="pk-type${x.p?"":" empty"}" data-pkp="p" aria-haspopup="listbox" aria-label="Project: ${(x.p?pName(x.p):"not set")}" data-tip="Project">${(x.p?pName(x.p):"Choose a project")}${raw(ic("chevdown"))}</button>${k==="raid"?html`<button type="button" class="pk-type" data-pkp="type" aria-haspopup="listbox" aria-label="Type: ${x.type}" data-tip="Type">${x.type}${raw(ic("chevdown"))}</button>`:""}`);
  $("#pkWarn").textContent="";
  putHTML($("#pkFeed"),html`<div class="sub">Nothing here yet.</div>`); }
/* ===== end BL-179 (the empty peek) ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootPanel0175(){
PKFL.srcIn="Source";
addHTML($("#pkNote"),"afterend",html`<div class="pk-dl pk-src-l" id="pkSrcL" hidden>Source</div><div class="pk-desc pked pk-srcin" id="pkSrcIn" data-pkf="srcIn" contenteditable="plaintext-only" role="textbox" spellcheck="true" aria-label="Source" hidden></div>`);
pkEdMount($("#pkScroll"));
PKDRAW.push(pkNewDraw);
if(shared.CUR&&pkOn()) drawPanel();
}
/* ===== BL-179 (sprint-peek-new) ===== the first commit and the one new proposal. Committing the title (Enter or leaving it) with a
   project set runs the Create form's own check on the whole item (validate, then norm: a project, a title, a valid date, a made
   decision's date, a decision's source, client messaging) and, when it passes, stages ONE "new" proposal through the Create form's
   route (newItemOf for the values, writeProposal for the file: source_run "dashboard", already approved). Never applied on the spot,
   as for every peek change. A check that fails says why on the field (the note, and the field marked) and nothing is staged. Until the
   proposal is applied, every further change to the new item rewrites that same proposal's values (the one exception to one edit, one
   proposal: there is no ID to point at yet); a change the check refuses is put back. The pill counts it as one change. ⌘↵ commits the
   field, applies everything staged and closes, as everywhere; with a title that can't be staged yet it stays open and says why. Once
   applied, the item is found in the fresh data (its project, its title, an ID that wasn't there when it was staged) and the peek
   becomes that item's, with its ID, without closing. Undo last on it unstages it and the peek goes back to the unstaged draft. */
export let PKNEWIDS=[];
export function pkNewForm(k,x){ const f={}; Object.keys(FIELD[k]).forEach(n=>{ const v=x[n]; f[n]=typeof v==="boolean"?v:String(v??"").trim(); });
  if(k==="decisions") f.srcIn=String(x.srcIn||"").trim(); return f; }
export function pkNewBadField(k,f){ if(!f.t) return "t"; for(const n of ["due","raised","closed","date"]) if(f[n]&&!DATE.test(f[n])) return n==="date"?"date":"due";
  if(f.client) return k==="decisions"?"cmd":"cm";
  if(k==="decisions"&&!f.srcIn) return "srcIn";
  if(k==="decisions"&&(f.st||"Made")==="Made"&&!f.date) return "date";
  return f.p?null:"p"; }
export function pkNewMarkDraw(){ $$("#panel .pkbad").forEach(e=>{ e.classList.remove("pkbad"); e.removeAttribute("aria-invalid"); });
  const n=shared.CUR&&shared.CUR.mode==="new"?PKN.bad:null; if(!n) return null;
  const el=$(`#panel [data-pkf="${n}"]`)||$(`#panel [data-pkp="${n}"]`); if(el){ el.classList.add("pkbad"); el.setAttribute("aria-invalid","true"); } return el; }
/* the Create form's check on the whole new item: its fields after norm, or null with the message on the field */
export function pkNewCheck(k,x){ const f=pkNewForm(k,x), err=validate(k,f,true,null);
  if(err){ PKN.bad=pkNewBadField(k,f)||null; pkNote(err); pkNewMarkDraw(); return null; }
  PKN.bad=null; pkNewMarkDraw(); return norm(k,f); }
export const pkArr=k=>k==="actions"?A:k==="raid"?R:DEC;
/* "ok" staged (or the proposal rewritten), "wait" kept in the draft with the reason shown, "fail" refused */
export async function pkNewSync(k,id,commit){ if(!shared.CUR||shared.CUR.mode!=="new"||shared.CUR.nid!==id) return "ok"; const x=shared.CUR.draft;
  if(!x.t){ PKN.bad=null; pkNewMarkDraw(); return "wait"; }               /* nothing to stage until it has a title */
  const f=pkNewCheck(k,x); if(!f) return shared.CUR.staged?"fail":"wait";
  if(shared.CUR.alert&&!shared.CUR.staged) return commit?alertStage(k,id,f):"wait";   /* BL-296: made from a message, staged only on Save (the server's route) */
  const {values}=newItemOf(k,f); if(!await needVault()) return shared.CUR.staged?"fail":"wait";
  if(!shared.CUR.staged){ let name; pkSaving("busy");
    const meta={k,id,patch:{},prev:{},label:"Created",from:"",to:f.t,at:nowStamp(),note:"",type:"act",isNew:true,title:f.t,p:f.p,known:pkArr(k).map(r=>r.id),ms:Date.now()};   /* BL-188 */
    try{ name=await writeProposal([...pkWsPre(x),{op:"new",table:k,values}],{peek:meta}); }   /* BL-187: a new workstream rides ahead of it */catch(e){ pkSaving("fail"); snack("Not saved: "+e.message); return "wait"; }
    shared.PKS.push({name,...meta});
    if(shared.CUR&&shared.CUR.nid===id) shared.CUR.staged=name; pdDrop(`new:${k}`); pkPersist(); pkSaving("ok"); refreshAll(); return "ok"; }   /* staged: its browser draft (below) goes */
  pkSaving("busy");
  try{ await editProposal(shared.CUR.staged,data=>{ const it=(data.items||[]).find(i=>i.op==="new"&&i.table===k); if(!it||it.applied) throw new Error("it has already been applied"); it.values=values; pkWsPreSync(data,x); if(data.peek) Object.assign(data.peek,{title:f.t,p:f.p,to:f.t,at:nowStamp()}); }); }   /* BL-187; BL-188: the file says what the item is now */
  catch(e){ pkSaving("fail"); snack("Not saved: "+e.message); return "fail"; }
  const s=shared.PKS.find(e=>e.name===shared.CUR.staged); if(s){ s.title=f.t; s.p=f.p; s.to=f.t; s.at=nowStamp(); pkPersist(); } pkSaving("ok"); return "ok"; }
export function pkNewFocus(){ if(!PKN.bad||(document.activeElement&&document.activeElement!==document.body)) return; pkNewMarkDraw()?.focus(); }   /* only when nothing else has the cursor */
export async function pkQuiet(){ let q; do{ q=shared.PKQ; await q; }while(q!==shared.PKQ); }
/* after an apply (or a reload): a new item that left staging is found in the fresh data, and its peek becomes the item's */
export function pkNewFound(s){ const c=pkArr(s.k).filter(r=>r.p===s.p&&!(s.known||[]).includes(r.id));
  const m=c.filter(r=>pkSame(r.t,s.title)); return (m.length?m[m.length-1]:c.length===1?c[0]:{}).id||null; }
/* the save state, the last-edited line and the feed for a new item */
export function pkNewState(x,k){ if(shared.CUR.mode!=="new") return; const st=!!shared.CUR.staged, w=pkNewWord(k);
  let el=$("#pkLast"); if(el) putHTML(el,html`${raw(ic("history"))}<span>${st?html`Staged · created when you apply`:shared.CUR.alert?html`Not staged yet · Save (${MOD}↵) stages it and dismisses the message`:html`Not staged yet · it is staged once it has a title and a project`}</span>`);
  pkSaving(st?"ok":"",st?"Saved to staging":"");
  putHTML($("#pkFeed"),st?html`<div class="pk-fe"><span class="pk-fi" aria-hidden="true">${raw(ic("pencil"))}</span><div><b>You</b> created this ${w}<span class="pk-pill st">staged</span></div></div>`:html`<div class="sub">Nothing here yet.</div>`);
  pkNewMarkDraw(); }
/* ===== end BL-179 (the first commit) ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootPanel0176(){
/* committing the title when it hasn't changed (Enter after a restore, say) still counts as committing it */
addEventListener("focusout",e=>{ const el=e.target.closest&&e.target.closest("#pkTitle"); if(!el||!shared.CUR||shared.CUR.mode!=="new") return; PKN.esc=!!el.dataset.skip; },true);
document.addEventListener("focusout",e=>{ const el=e.target.closest&&e.target.closest("#pkTitle"); if(!el||!shared.CUR||shared.CUR.mode!=="new"||PKN.esc||shared.CUR.staged) return; const k=shared.CUR.k, id=shared.CUR.nid;
  shared.PKQ=shared.PKQ.then(async()=>{ if(shared.CUR&&shared.CUR.mode==="new"&&shared.CUR.nid===id&&!shared.CUR.staged&&shared.CUR.draft.t){ await pkNewSync(k,id); if(pkOn()) pkDraw(); pkNewFocus(); } }).catch(()=>false); });
PKDRAW.push(pkNewState);
if(shared.CUR&&pkOn()) drawPanel();
}
/* ===== BL-179 (sprint-peek-new) ===== leaving early and reloads. Esc, a click away, the close arrow, another row, New again or Back
   on a new item that isn't staged: with no title, it closes and nothing is staged (and nothing is kept); with a title, the peek asks
   "Keep or Discard" in place. Keep closes it and keeps it in this browser, Discard closes it and drops it; Esc on the question goes
   back to editing. Esc in one of its text fields is leaving too (the text typed is kept in the draft, not put back). A staged new item
   closes like any other: it is in staging, and the pill shows it. A new item not yet staged is kept in this browser as it is typed
   (BL-167's draft store, creaite-panel-drafts, keyed "new:<kind>" as the Create form's draft was), so it survives a reload; opening
   New of that kind offers it back (Restore or Discard). A draft over 7 days old is dropped with a note, as BL-167's are. Staging it
   drops the draft. */
export const pkNewKey=()=>shared.CUR&&shared.CUR.mode==="new"?`new:${shared.CUR.k}`:null;
export function pkNewTitle(){ if(!shared.CUR||shared.CUR.mode!=="new") return ""; const t=$("#pkTitle"); return String(document.activeElement===t?t.textContent:shared.CUR.draft.t||"").trim(); }
export function pkNewStore(){ if(!shared.CUR||shared.CUR.mode!=="new"||shared.CUR.alert) return;   /* BL-296: one made from a message isn't kept */ const key=pkNewKey(), all=pdAll();
  if(shared.CUR.staged){ if(key in all){ delete all[key]; pdPut(all); } return; }
  const x={...shared.CUR.draft}, a=document.activeElement; if(a&&a.matches&&a.matches("#panel [data-pkf][contenteditable]")) x[a.dataset.pkf]=a.textContent;
  const ch={}; for(const n of Object.keys(x)) if(!(n==="pr"&&shared.CUR.k==="raid")&&!pkSame(shared.CUR.blank[n],x[n])) ch[n]=x[n];
  if(!Object.keys(ch).length){ if(!PKN.offer&&key in all){ delete all[key]; pdPut(all); } return; }
  if(PKN.offer){ PKN.offer=null; pkNewOffer(""); }                           /* typing afresh replaces the old draft */
  all[key]={fields:ch,at:Date.now(),base:"",peek:1}; Object.keys(all).sort((p,q)=>all[q].at-all[p].at).slice(30).forEach(k=>delete all[k]); pdPut(all); }
shared.PKNT=null; export const pkNewStoreSoon=()=>{ clearTimeout(shared.PKNT); shared.PKNT=setTimeout(pkNewStore,250); };
                     /* Esc keeps what was typed in a new item */
export function pkNewWhy(){ const f=pkNewForm(shared.CUR.k,{...shared.CUR.draft,t:pkNewTitle()}), n=pkNewBadField(shared.CUR.k,f);
  return {p:"it needs a project",srcIn:"it needs its source",cm:"it needs client messaging",cmd:"it needs client messaging",date:"it needs the date it was made"}[n]||"it hasn't been committed"; }
export function pkNewAsk(retry){ PKN.retry=retry||null; const w=pkNewWord(shared.CUR.k);
  $("#pkAskT").textContent=`This new ${w} isn't staged yet: ${pkNewWhy()}. Keep it in this browser (New offers it back), or discard it?`;
  $("#pkAsk").hidden=false; shared.EDITING=true; $("#pkScroll").scrollTop=0; $('#pkAsk [data-pkask="keep"]').focus(); }   /* EDITING while it asks: a click away or Back waits for the answer */
export function pkNewAskOff(){ if(!$("#pkAsk").hidden) shared.EDITING=false; $("#pkAsk").hidden=true; PKN.retry=null; }
export function pkNewLeave(how){ const retry=PKN.retry, w=shared.CUR?pkNewWord(shared.CUR.k):"item"; pkNewAskOff();
  if(how==="keep"){ pkNewStore(); PKN.keep=true; } PKN.force=true; try{ closePanel(); }finally{ PKN.force=false; PKN.keep=false; }
  snack(how==="keep"?`Kept in this browser: New ${w} offers it back`:`New ${w} discarded`); if(retry) retry(); }
/* staging drops the draft; a change before it is kept */
/* New offers a kept one back */
export function pkNewOffer(html){ const b=$("#pkDraft"); putHTML(b,raw(html||"")); b.hidden=!html; }
export function pkNewRestore(){ const key=pkNewKey(), d=key&&pdAll()[key]; PKN.offer=null; pkNewOffer(""); if(!d) return;
  const x=shared.CUR.draft, F=d.fields;
  for(const n of Object.keys(F)){ if(!(n in x)) continue; let v=F[n]; if(typeof v==="string"&&DDATE.test(v.trim())) v=toIso(v.trim()); x[n]=v; }   /* the Create form kept a date as typed */
  if(shared.CUR.k==="raid") x.pr=prio(x.imp,x.lik); if(x.client) PK.det[shared.CUR.nid]=true;
  pkDraw(); const t=$("#pkTitle"); t.textContent=x.t||""; t.focus(); const r=document.createRange(); r.selectNodeContents(t); r.collapse(false); const sel=getSelection(); sel.removeAllRanges(); sel.addRange(r);
  snack(`Restored. Press Enter in the title to stage it`); }
/* ===== end BL-179 (leaving and reloads) ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootPanel0177(){
document.addEventListener("input",e=>{ if(!shared.CUR||shared.CUR.mode!=="new"||shared.CUR.staged) return; const el=e.target.closest&&e.target.closest("#panel [data-pkf][contenteditable]"); if(!el) return;
  el.dataset.orig=el.textContent; pkNewStoreSoon(); });
addEventListener("pagehide",()=>{ if(shared.CUR&&shared.CUR.mode==="new") pkNewStore(); });
/* Esc in a text field of an unstaged new item: keep the text in the draft, then leave */
addEventListener("focusout",e=>{ const el=e.target.closest&&e.target.closest("#panel [data-pkf][contenteditable]"); if(!el||!el.dataset.skip||!shared.CUR||shared.CUR.mode!=="new"||shared.CUR.staged) return;
  const ml=!!el.dataset.pkml, raw=el.textContent; shared.CUR.draft[el.dataset.pkf]=ml?raw.replace(/^\s+|\s+$/g,""):raw.replace(/\s+/g," ").trim(); pkNewStore();
  setTimeout(()=>{ if(shared.CUR&&shared.CUR.mode==="new") closePanel(); },0); },true);
/* the question, in the peek */
addHTML($("#pkScroll"),"afterbegin",html`<div class="pk-ask" id="pkAsk" role="alertdialog" aria-labelledby="pkAskT" hidden><span class="t" id="pkAskT"></span><button type="button" class="btn primary" data-pkask="keep">Keep</button><button type="button" class="btn" data-pkask="discard">Discard</button></div><div class="pdraft" id="pkDraft" role="status" hidden></div>`);
$("#pkAsk").addEventListener("click",e=>{ const b=e.target.closest("[data-pkask]"); if(b) pkNewLeave(b.dataset.pkask); });
$("#pkAsk").addEventListener("keydown",e=>{ if(e.key!=="Escape") return; e.preventDefault(); e.stopPropagation(); pkNewAskOff(); $("#pkTitle").focus(); });
document.addEventListener("click",e=>{ const b=e.target.closest("[data-pknd]"); if(!b) return; const a=b.dataset.pknd;
  if(a==="restore") pkNewRestore(); else { if(a==="discard"){ pdDrop(PKN.offer&&PKN.offer.key); snack("Unsaved new item discarded"); } PKN.offer=null; pkNewOffer(""); $("#pkTitle").focus(); } });
}
/* ===== BL-179 (sprint-peek-new) ===== a dependency's suggested milestones in the peek. The Create form offered them under its Milestone
   field (depFormDraw: up to three it could threaten, nearest first, then None needed, remembered until the text changes); the peek has no
   form, so the same suggestions (depSuggest, depHash, the same store) show under the key row of a RAID Dependency with no milestone,
   new or existing. Attach is the milestone chip's own change (staged, or into the new item's draft). Nothing is attached by itself. */
export function pkDepDraw(x,k){ const box=$("#pkDep"); if(!box) return; box.textContent="";
  if(k!=="raid"||x.type!=="Dependency"||x.ms||!x.p||!OPENST(x.st||"Open")) return; const key=shared.CUR.mode==="new"?"new":pkCid();
  if((store.get("creaite-dep-none",{})[key])===depHash(x.t)) return;
  const L=depSuggest(x.p,x.due||""); if(!L.length) return;
  depSugDraw(box,L,"pkdep"); }
/* ===== end BL-179 (dependency suggestions) ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootPanel0178(){
addHTML($("#pkProps2"),"afterend",html`<div id="pkDep"></div>`);
PKDRAW.push(pkDepDraw);
$("#pkDep").addEventListener("click",e=>{ if(!shared.CUR||!pkOn()) return; const a=e.target.closest("[data-pkdep]"), n=e.target.closest("[data-pkdepnone]"), x=curObj(), k=shared.CUR.k, id=pkCid();
  if(a) pkCommit(k,id,{ms:a.dataset.pkdep},"Milestone","none",msName(a.dataset.pkdep));
  else if(n){ const d=store.get("creaite-dep-none",{}); d[shared.CUR.mode==="new"?"new":id]=depHash(x.t); store.set("creaite-dep-none",d); pkDepDraw(x,k); } });
if(shared.CUR&&pkOn()) drawPanel();
}
/* ===== BL-180 (sprint-peek-new) ===== errors: a banner to dismiss or investigate, not a permanent header link. When the debug log
   holds errors from the last day that Alan hasn't seen, a quiet banner under the header (and under the live-server alert) says how
   many ("3 errors in the last day"; repeats of one message are one error: "1 error (30 times)"), what kind ("2 sweep runs failed,
   1 live-server request"), and offers Investigate (Settings › Diagnostics, at the latest errors), ask creaite to look (only with the
   live server: it asks for an explanation and says to change nothing) and Dismiss (×). Dismissing, Investigate or opening Diagnostics
   remembers the newest error seen, in this browser (localStorage creaite-errors-seen); the banner comes back only for an error
   logged after that, counting only the new ones ("1 new error"). Never shown before the log has been read; the log is never changed. */
export const EBKEY="creaite-errors-seen";
export const ebSeen=()=>{ const v=store.get(EBKEY,""); return typeof v==="string"?v:""; };
export function ebMarkSeen(){ if(DIAG.loaded&&DIAG.newest&&DIAG.newest>ebSeen()) store.set(EBKEY,DIAG.newest); }
export const EBAREA={sweep:["sweep run failed","sweep runs failed"],server:["live-server request","live-server requests"],run:["ask creaite or prep run","ask creaite or prep runs"],
  dashboard:["in the page","in the page"],build:["dashboard rebuild failed","dashboard rebuilds failed"]};
export function ebState(){ if(!DIAG.loaded) return null; const seen=ebSeen();
  const G=(DIAG.groups||[]).map(g=>({...g,n:(g.times||[g.last]).filter(t=>t>seen).length})).filter(g=>g.n>0); if(!G.length) return null;
  const errs=G.length, times=G.reduce((a,g)=>a+g.n,0), byArea={};
  G.forEach(g=>{ byArea[g.area]=(byArea[g.area]||0)+1; });
  const kinds=Object.entries(byArea).sort((a,b)=>b[1]-a[1]).map(([a,n])=>{ const w=EBAREA[a]; return w?`${n} ${n===1?w[0]:w[1]}`:`${n} in ${a}`; });
  const head=`${errs} ${seen?"new ":""}error${errs===1?"":"s"}${times>errs?` (${times} times)`:""}${seen?"":" in the last day"}`;
  return {head,kinds:kinds.join(", ")}; }
export function errBanner(){ const b=$("#errBanner"); if(!b) return; const st=ebState();
  if(!st){ b.hidden=true; b.textContent=""; b.dataset.k=""; return; }
  const key=st.head+"|"+st.kinds+"|"+viaServer(); if(b.dataset.k===key&&!b.hidden) return; const was=b.hidden; b.dataset.k=key;
  putHTML(b,html`${raw(ic("alert"))}<span class="eb-w" title="${st.head+" · "+st.kinds}"><span class="eb-t">${st.head}</span> <span class="eb-k">${st.kinds}</span></span><span class="eb-a"><button type="button" class="mini" id="ebInv">Investigate</button>${viaServer()?html`<button type="button" class="mini" id="ebAsk">ask creaite to look</button>`:""}${raw(ibtn("x","Dismiss",'id="ebX"'))}</span>`);   /* fix-peek-140: the words in one line that gives way; the actions together after them */
  b.hidden=false; if(was){ b.classList.remove("fade"); void b.offsetWidth; b.classList.add("fade"); } }
/* ===== end BL-180 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootPanel0179(){
document.addEventListener("click",e=>{ const t=e.target;
  if(t.closest("#ebX")){ ebMarkSeen(); errBanner(); snack("Dismissed: the banner comes back only for a new error"); return; }
  if(t.closest("#ebInv")){ ebMarkSeen(); errBanner(); go("settings","diag"); return; }
  if(t.closest("#ebAsk")){ if(!viaServer()) return; ebMarkSeen(); errBanner(); openChat();
    send("Look at the errors in creaite's debug log from the last day (Settings › Diagnostics, system/logs) and their context, and explain the likely causes in plain words. This is read only: don't change anything."); } });
errBanner();
}
/* ===== BL-185 (sprint-peek-new) ===== the status cockpit refined. The metrics row under the project's status line drops "No due date"
   (the project page's No due date card, FR-95, stays as it is, with its inline dates), shortens its date words ("Due in 7 days" is
   "Due 7d", a slip of "21 days" is "21d"), and marks an alert metric (a count over nothing that is bad: overdue actions, urgent risks,
   a milestone slip, early warnings) with the shared warning icon (ic("alert"), BL-158's set) beside its words. Every metric stays one
   click target to its detail: Milestone slip, which had none, now goes to the Milestones card. */
export function bl185Row(){ const row=$("#v-cockpit .evrow"); if(!row) return;
  row.querySelectorAll(".evbox").forEach(b=>{ const l=b.querySelector(".l"), v=b.querySelector(".v"); if(!l||!v) return; const t=l.textContent.trim();
    if(t==="No due date"){ b.remove(); return; }
    const m=/^Due in (\d+) days?$/.exec(t); if(m) l.textContent=`Due ${m[1]}d`;
    if(t==="Milestone slip"){ v.textContent=v.textContent.replace(/^(\d+) days?$/,"$1d");
      if(!b.classList.contains("click")){ b.classList.add("click"); b.setAttribute("data-msjump",""); b.setAttribute("role","link"); b.tabIndex=0; b.title="Show the milestones"; } }
    if(v.classList.contains("bad")&&!l.querySelector(".evi")){ b.classList.add("alert"); addHTML(l,"afterbegin",raw(ic("alert",{cls:"evi",bare:true}))); } }); }
/* ===== end BL-185 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootPanel0181(){
document.addEventListener("click",e=>{ const b=e.target.closest&&e.target.closest("a.itemref[data-oi]"); if(!b||b.closest(".ProseMirror")) return; e.preventDefault(); openRecord("all",b.dataset.oi); });   /* #122 C: a work-item link in a read view opens the item */
document.addEventListener("click",e=>{ const b=e.target.closest("[data-msjump]"); if(!b) return; e.preventDefault(); const h=[...document.querySelectorAll("#v-cockpit .card h2")].find(x=>x.textContent.trim().startsWith("Milestones")); if(h) mScroll(h.closest(".card"),{block:"start"}); });
document.addEventListener("keydown",e=>{ if(e.key==="Enter"&&e.target.matches&&e.target.matches("[data-msjump]")) e.target.click(); });
}
/* ===== BL-187 (fix-peek-140) ===== the peek's owner and workstream lists get back what the old panel had (BL-55, BL-58).
   Owner: as Alan types, the list comes from the register's one matcher (ownerMatches, shared with the old combo): a name, an alias
   or an email finds the person; a likely match is offered as "Is “Sara” Sara Khan?" (picking it remembers the alias, regAddAlias);
   a stranger is "New person “…”…" (the details dialog, ownerFinal). With nothing typed it lists the project's people first, then
   everyone, Unassigned, and "Open <name>'s page" (kept whatever is typed). Workstream: "Add workstream…" (or "Add “typed” as a
   workstream…") opens a small form with the details suggested from the project's items (wsSuggest, as BL-58's confirm box did). Add
   stages the item's change with the new workstream ahead of it in the same proposal (wsNewOf, the route the old panel's save used),
   so Undo last removes both and nothing reaches the tracker until Apply. A proposal in Review keeps its own route (the row's
   "Add workstream"), so its list is unchanged. */
export function pkOwnerOpts(x,k,q){ const cur=pkWho(x[pkOwnF(k)]), pool=projFirst(peopleAll(),projPeople(x.p));
  const page=cur&&!isHiddenPerson(cur)?[{v:"\u0000page",label:isMe(cur)?"Open My work":`Open ${cur}'s page`,icon:"people"}]:[];   /* BL-56: the name still leads to the person */
  const av=n=>peekMark({who:pkWho(n)||""});
  if(!q) return [...pool.map(n=>({v:n,label:n,mark:av(n),hint:isMe(n)?"you":""})),{v:"",label:k==="decisions"?"No one yet":"Unassigned",mark:av("")},...page];
  return [...ownerMatches(q,pool).items.map(it=>it.t==="alias"?{v:it.n,label:`Is “${it.typed}” ${it.n}?`,hint:"Yes, and remember it",mark:av(it.n),t:"alias",typed:it.typed}
      :it.t==="new"?{v:it.n,label:`New person “${it.n}”…`,icon:"plus",t:"new"}:{v:it.n,label:it.n,mark:av(it.n),hint:isMe(it.n)?"you":""}),...page]; }
export function pkOwnerList(anchor,x,k,id){ const cur=pkWho(x[pkOwnF(k)]);
  openPicker(anchor,{label:pkOwnL(k),search:true,value:cur,onClose:pkPopDone(anchor),options:pkOwnerOpts(x,k,""),filter:q=>pkOwnerOpts(x,k,q),
    onPick:async(v,typed,o)=>{ if(v==="\u0000page"){ closePanel(); isMe(cur)?go("mine"):go("person",cur); return; }
      if(o&&o.t==="alias"){ if(await regAddAlias(v,o.typed)) return pkOwner(k,id,v,false); return; }
      if(o&&o.t==="new"){ const n=await ownerFinal(v,{skipMatch:true}); if(n!==null) return pkOwner(k,id,n,false); return; }
      return pkOwner(k,id,v,false); }}); }
export const pkWsAddOK=()=>!!(shared.CUR&&shared.CUR.mode!=="proposal");
export function pkWsOpts(x,q){ const L=wsFor(x.p), t=String(q||"").toLowerCase(), have=L.some(w=>w.toLowerCase()===t);
  const o=L.filter(w=>!t||w.toLowerCase().includes(t)).map(w=>({v:w,label:w,icon:"layers"}));
  if(!t) o.push({v:"",label:"None"});
  if(!x.p) o.push({v:"\u0000add",label:"Add workstream…",icon:"plus",disabled:true,hint:"Choose a project first"});
  else if(!have) o.push({v:"\u0000add",id:"pkWsAdd",label:q?`Add “${q}” as a workstream…`:"Add workstream…",icon:"plus",name:q});   /* its id: the form's way in (NewWorkstream) */
  return o; }
/* the form: the name and BL-58's details, suggested from the project's items; Add stages it with the item's change */
export function pkWsForm(anchor,x,k,id,name){ const p=x.p, s=name?wsSuggest(p,name):{};
  if(!anchor||!anchor.isConnected) anchor=$('#panel [data-pkp="ws"]')||$("#pkTitle");
  return openNewWorkstream(anchor,{title:`New workstream for ${pName(p)}`,name,fields:/** @type {[string, string][]} */(WS_FIELDS),suggest:nm=>wsSuggest(p,nm),onClose:pkPopDone(anchor),
    note:`${name?`Suggested from ${s.items} item${s.items===1?"":"s"}; change anything.`:"A lead, keywords and aliases help creaite match items to it."} Staged with this item's change.`,
    onAdd:async v=>{ const w=wsRow(p,v.name);
      if(w&&w.st==="Closed") return `“${w.name}” is closed in ${pName(p)}: reopen it in Settings › People and projects › Workstreams, or choose another.`;
      const known=w?w.name:wsFor(p).find(n=>n.toLowerCase()===v.name.toLowerCase());
      closePicker("pick");
      if(known) return void pkCommit(k,id,{ws:known},"Workstream",x.ws||"none",known);   /* it is already there: just use it */
      if(v.lead){ const o=await ownerFinal(v.lead); if(o===null) return; v.lead=o; }
      const {item,row}=wsNewOf({...v,project:p});
      if(String(id).startsWith("nw")&&shared.CUR&&shared.CUR.nid===id){ shared.CUR.wsPre={item,row}; (D.ws_table=D.ws_table||[]).push(row); }   /* a new item carries it in its one proposal */
      pkCommit(k,id,{ws:v.name},"Workstream",x.ws||"none",v.name,{pre:[item],wsRow:String(id).startsWith("nw")?null:row,note:`New workstream “${v.name}” for ${pName(p)}, staged with this change`}); }}); }
/* a new item's one proposal: the new workstream rides ahead of it while its workstream is that one (pkNewSync calls these) */
export const pkWsPre=x=>{ const w=shared.CUR&&shared.CUR.mode==="new"&&shared.CUR.wsPre; return w&&String(x.ws||"").toLowerCase()===w.row.name.toLowerCase()?[w.item]:[]; };
export function pkWsPreSync(data,x){ const main=(data.items||[]).filter(i=>i.table!=="workstreams"||i.applied);
  data.items=[...pkWsPre(x).map(i=>Object.assign({match:"strong",flags:[],decision:"approved"},i)),...main].map((i,j)=>Object.assign(i,{n:j+1})); }
/* Undo last on a change that added a workstream: the row the page showed goes too */
/* ===== end BL-187 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootPanel0182(){
{ const wsOld=PKPROP.ws; PKPROP.ws=(a,x,k,id)=>{ if(!pkWsAddOK()) return wsOld(a,x,k,id);
    openPicker(a,{label:"Workstream",search:true,value:x.ws||"",onClose:pkPopDone(a),options:pkWsOpts(x,""),filter:q=>pkWsOpts(x,q),onPick:(v,typed,o)=>{
      if(v==="\u0000add") return pkWsForm(a,x,k,id,(o&&o.name)||"");
      return pkCommit(k,id,{ws:v},"Workstream",x.ws||"none",v||"none"); }}); }; }
}
/* ===== BL-188 (fix-peek-140) ===== staged peek changes show in every window. Each peek proposal carries a `peek` note (the item,
   the change in the page's own fields, its words, when it was made); build_dashboard's peek_staged lists the unapplied ones from
   system/staging/, so the page's data (on load, and each time it refreshes: after an apply, when the files change, a sweep) says
   what is staged, whichever window staged it. pkFromVault adds the ones this window doesn't know to PKS, so the pill counts them,
   the item's feed marks them "staged", the peek and the lists show the staged values (pkReconcile applies each patch on the fresh
   data), and Apply or Undo last works on them here as on this window's own. Only staged changes are in the files: text being typed
   in another window is never shown. No new route: /api/data and /api/fs as before. */
export function pkFromVault(){ const L=Array.isArray(D.peek_staged)?D.peek_staged:[], have=new Set(shared.PKS.map(s=>s.name)); let n=0;
  for(const m of L){ if(!m||!m.name||!m.k||!m.id||have.has(m.name)) continue; shared.PKS.push({...m,patch:m.patch||{},prev:m.prev||{}}); n++; }
  if(n){ shared.PKS.sort((a,b)=>(a.ms||0)-(b.ms||0)||(a.name<b.name?-1:a.name>b.name?1:0)); pkPersist(); }
  return n; }
/* ===== end BL-188 ===== */
/* ===== BL-198 (sprint-review-work) ===== with the peek open, a single click on another work item shows it in the peek: Work's table
   and Board, a person's page (hlRowClick) and Review's proposal rows. The click still highlights first (BL-122), then does what the
   double click does (hlRowOpen; on Review openProposal). With no peek open, a click only highlights, as before. Settled in the build:
   a Ctrl/⌘ or Shift click is still a selection and leaves the peek alone; a click on a link, a button, a tick box or a cell's editor
   keeps its own job (they never reach these handlers, or return first); text being typed in the peek commits as it loses focus
   (the mousedown blurs it), and a Review proposal with changes not yet saved stays open with a note (its edits live only in the
   panel); a Review row that doesn't open in the peek (minutes, a report, a file change, an update) only highlights; Previous and Next
   and the highlight stay in step (the clicked row is the only one highlighted and the cursor); focus stays where it was. */
export function pkFollowable(e){ return pkOn()&&!e.metaKey&&!e.ctrlKey&&!e.shiftKey&&!e.altKey&&e.button===0; }
export function pkKeepFocus(was,fn){ fn(); setTimeout(()=>{ const a=document.activeElement; if(a&&$("#panel").contains(a)&&!(was&&$("#panel").contains(was))){ if(was&&was!==document.body&&was.isConnected) was.focus({preventScroll:true}); else a.blur(); } },0); }
export function pkFollowRev(e,n){ if(!pkFollowable(e)||(shared.CUR&&shared.CUR.mode==="proposal"&&shared.CUR.n===n)) return; const r=REV.find(x=>x.n===n);
  if(!r||r.done||!PKK.includes(r.kind)) return;
  if(shared.CUR&&shared.CUR.mode==="proposal"&&PK.dirty){ pkNote("Save or cancel this proposal first: its changes aren't saved yet."); return; }
  const was=document.activeElement; pkKeepFocus(was,()=>{ openProposal(n); rvPaint(); }); }
/* ===== end BL-198 ===== */
/* ===== BL-219 (sprint-drafts-fields) ===== Draft the latest update. In the peek, Draft beside an open action's Latest update asks
   for one or two lines from what happened since the last update (drafts.py: its changes, the meetings and sweeps that raised it
   again, the minutes that name it, its linked items; a confidential source is skipped). With nothing new it says "Nothing new
   since …" and asks no model. The draft is a card under the field; Use puts it in the field, unsaved, for Alan to edit and leave
   (the peek's usual staging); Discard drops it. Several at once: Draft updates on Work's change-several bar (actions) and on
   Today's stale line stage one pending update proposal per action in Review (latest update only, each approved on its own), never
   saved in place. The peek's draft host below is shared by BL-222 and BL-225. */
/* ---- the peek's draft host: a button beside a field, the card under it, Use and Discard, and what Alan did, counted ---- */
export const PKDRBTN=[], PKDRBODY={}, PKDRTITLE={}, PKDREXTRA={}, DRPEND={};
export const pkDrHost=f=>["upd","resp","why","t"].includes(f)?"pkAiDraft":"pkAiDraftD";   /* "t": BL-220's Sharpen (sprint-drafts-extraction) */
export function pkDrDraw(){ ["pkAiDraft","pkAiDraftD"].forEach(h=>{ const el=document.getElementById(h); if(!el) return; const c=shared.PKDRC&&shared.PKDRC.key===PK.key&&shared.PKDRC.host===h?shared.PKDRC:null, html=c?c.html:"";
  if(el.innerHTML!==html) putHTML(el,raw(html)); }); }
export function pkDrDrop(){ if(shared.PKDRC&&shared.PKDRC.d) draftStat(shared.PKDRC.feature,"rejected"); shared.PKDRC=null; pkDrDraw(); }
export function pkDrPlace(x,k){ $("#pkDescDr")?.replaceChildren();          /* beside the label, never inside it: the label stays the field's name (BL-214) */
  PKDRBTN.flatMap(fn=>fn(x,k,shared.CUR.upd?"update":shared.CUR.mode)||[])        /* #232-B: an update proposal offers no drafting: its title and wording are the item's own */.forEach(b=>{ const btn=draftBtn(b.kind,b.word,b.tip,`data-drf="${b.f}"`);
    if(["upd","resp","why","t"].includes(b.f)){ const l=b.f==="t"?$("#pkChips"):$("#pkDescDr"); if(l&&!l.querySelector(`[data-drf="${b.f}"]`)) addHTML(l,"beforeend",raw(btn)); return; }   /* "t": Sharpen sits with the chips under the title (BL-220); the rest beside the label, never inside it (BL-214) */
    const fld=$(`#pkDet [data-pkf="${b.f}"]`);                       /* Details: on its own line under the field */
    if(fld&&!fld.parentElement.querySelector(`[data-drf="${b.f}"]`)) addHTML(fld,"afterend",html`<div class="drline">${raw(btn)}</div>`); }); }
/* Use: the text goes into the field, unsaved, with the cursor at its end; leaving the field stages it as any edit does (and the
   rules hold: client messaging, a closed item…). Esc puts the old text back. */
export function pkDrUse(c,text){ const x=curObj(); if(!x) return;
  if(c.host==="pkAiDraftD"&&!$(`#pkDet [data-pkf="${c.f}"]`)){ PK.det[pkCid()]=true; pkDetails(x,shared.CUR.k); }
  const el=$(`#panel [data-pkf="${c.f}"]`); if(!el){ snack("That field isn't shown here"); return; }
  shared.PKDRC=null; pkDrDraw(); el.focus(); el.textContent=text??c.d.text;
  const r=document.createRange(); r.selectNodeContents(el); r.collapse(false); const s=getSelection(); s.removeAllRanges(); s.addRange(r);
  DRPEND[pkCid()+"|"+c.f]={feature:c.feature,text:text??c.d.text};
  pkNote("The draft is in the field, not saved yet. Edit it, then click away to stage it as usual; Esc puts the old text back."); }
export const drSame=(a,b)=>String(a||"").replace(/\s+/g," ").trim()===String(b||"").replace(/\s+/g," ").trim();
   /* Esc: the old text came back */
/* ---- several at once: Work's change-several bar and Today's stale line ---- */
export async function draftBulk(ids,statusEl){ const why=draftWhyNot("update-bulk"); if(why){ snack(why); return; }
  const open=ids.filter(id=>{ const x=REC("actions",id); return x&&OPENST(x.st); }).slice(0,25);
  if(!open.length){ snack("None of these is an open action"); return; }
  const st=h=>{ const el=typeof statusEl==="function"?statusEl():statusEl; if(el) putHTML(el,raw(h)); };
  const res=await draftAsk({kind:"update-bulk",ids:open},{label:`Drafting updates for ${plur(open.length,"action")}`,status:st});
  if(res.nothing){ snack(res.nothing); return; } if(!res.ok){ snack(res.message||"No drafts came back"); return; }
  const n=res.staged||0, skip=(res.skipped||[]).length; await reloadData();
  snack(n?`${plur(n,"drafted update")} in Intake, each approved on its own${skip?`; ${skip} had nothing new`:""}. Nothing was saved in place`:"No drafts came back",n?()=>go("review"):null,"Open Intake"); }
/* ===== end BL-219 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootPanel0197(){
Object.assign(DRAFTKIND,{update:"update","update-bulk":"update"});
addHTML($("#pkDesc"),"afterend",html`<div id="pkAiDraft" class="pkdrhost"></div>`);
addHTML($("#pkDet"),"afterend",html`<div id="pkAiDraftD" class="pkdrhost"></div>`);
PKDRAW.push((x,k,fresh)=>{ if(shared.PKDRC&&shared.PKDRC.key!==PK.key) pkDrDrop(); pkDrPlace(x,k); pkDrDraw(); });
$("#panel").addEventListener("click",async e=>{ const b=e.target.closest("[data-draft][data-drf]"); if(!b||!pkOn()) return; e.preventDefault(); e.stopPropagation();
  const kind=b.dataset.draft, why=draftWhyNot(kind); if(why){ snack(why); return; }
  const f=b.dataset.drf, x=curObj(), k=shared.CUR.k, body=PKDRBODY[kind]&&PKDRBODY[kind](x,k,f); if(!body) return;
  if(shared.PKDRC) pkDrDrop(); if(pkDrHost(f)==="pkAiDraftD") PK.det[pkCid()]=true;
  const /** @type {any} */ mine=shared.PKDRC={key:PK.key,host:pkDrHost(f),f,kind,feature:DRAFTKIND[kind],html:""};
  const res=await draftAsk(body,{label:(PKDRTITLE[kind]?PKDRTITLE[kind](f):"Drafting").replace(/^Draft of/,"Drafting"),status:h=>{ if(shared.PKDRC===mine){ mine.html=h?`<div class="drstatus" role="status">${h}</div>`:""; pkDrDraw(); } }});
  if(shared.PKDRC!==mine){ if(res.ok&&!res.nothing) draftStat(mine.feature,"rejected"); return; }     /* the item was left while it ran */
  if(res.nothing){ mine.html=`<div class="drnone" role="status">${ic("spark")}<span>${esc(res.nothing)}</span></div>`; pkDrDraw(); return; }
  if(!res.ok){ shared.PKDRC=null; pkDrDraw(); snack(res.message||"No draft came back"); return; }
  mine.d=res; mine.html=draftCardHtml(res,{title:PKDRTITLE[kind]?PKDRTITLE[kind](f):"Draft",extra:PKDREXTRA[kind]?PKDREXTRA[kind](res,k):"",use:"Use this",from:kind==="thinking"?"Suggested from":""}); pkDrDraw();
  $(`#${mine.host} .drcard`)?.focus?.(); });
$("#panel").addEventListener("click",e=>{ const a=e.target.closest(".pkdrhost [data-drdo]"); if(!a||!shared.PKDRC||!shared.PKDRC.d) return; e.preventDefault(); e.stopPropagation();
  const c=shared.PKDRC; if(a.dataset.drdo==="discard"){ pkDrDrop(); $(`#panel [data-drf="${c.f}"]`)?.focus(); return; } pkDrUse(c); });
document.addEventListener("focusout",e=>{ const el=e.target.closest&&e.target.closest("#panel [data-pkf][contenteditable]"); if(!el||!shared.CUR) return;
  const key=pkCid()+"|"+el.dataset.pkf, d=DRPEND[key]; if(d){ delete DRPEND[key]; draftStat(d.feature,"rejected"); } });
/* ---- BL-219 in the peek ---- */
PKDRBTN.push((x,k,mode)=>k==="actions"&&mode==="record"&&OPENST(x.st)?[{f:"upd",kind:"update",word:"Draft",tip:"Draft the latest update from what has happened since the last one"}]:[]);
PKDRBODY.update=()=>({kind:"update",id:pkCid()});
PKDRTITLE.update=()=>"Draft of the latest update";
document.addEventListener("click",e=>{ const b=e.target.closest("[data-drbulk],[data-drstale]"); if(!b) return; e.preventDefault();
  if(b.getAttribute("aria-disabled")==="true"){ snack(draftWhyNot("update-bulk")); return; }
  const ids=b.dataset.drbulk?bkItems().map(o=>o.id):A.filter(x=>isStale("actions",x)).map(x=>x.id), where=b.parentElement.querySelector(".drbst");
  draftBulk(ids,where); });
/* ---- Review: a drafted proposal says so, and what Alan decides is counted ---- */
if(shared.VIEW==="today") renderToday();
}
/* ===== BL-225 (sprint-drafts-fields) ===== Draft client wording. Beside Client messaging in the peek's Details (an action, RAID item or
   decision being made client-visible), Draft asks for plain client wording from the item's own text only (report.py's client-safe
   item context: never its source, other items or the people around it; a confidential or restricted item is refused). The card
   lists what was taken out ("Taken out: a cost figure, the name Tom") and status_checks.client_wording's notes (a number, code or
   name that isn't in the item's text, a person's name). Use puts it in the field, unsaved; client-visible stays Alan's switch.
   Several at once: the project page's Client messaging card gets Draft all, which stages client_message proposals in Review,
   each approved on its own (never Approve routine). */
/* ===== end BL-225 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootPanel0198(){
Object.assign(DRAFTKIND,{client:"client","client-bulk":"client"});
PKDRBTN.push((x,k,mode)=>mode==="record"&&(x.client||(PK.pc&&PK.pc.id===pkCid()))?[{f:pkMsgF(k),kind:"client",word:"Draft",tip:"Draft plain client wording from this item's own text"}]:[]);
PKDRBODY.client=()=>({kind:"client",id:pkCid()});
PKDRTITLE.client=()=>"Draft of the client wording";
PKDREXTRA.client=d=>`${(d.removed||[]).length?`<div class="drnote"><b>Taken out:</b> ${esc(d.removed.join("; "))}</div>`:""}${(d.notes||[]).length?`<div class="drnote" role="note"><b>Check before you use it:</b><ul>${d.notes.map(n=>`<li>${esc(n.note)}</li>`).join("")}</ul></div>`:'<div class="drnote">No names, numbers or codes that aren\'t in the item.</div>'}`;
/* the project page's Client messaging card: Draft all */
document.addEventListener("click",async e=>{ const b=e.target.closest("[data-drcmall]"); if(!b) return; e.preventDefault();
  const why=draftWhyNot("client-bulk"); if(why){ snack(why); return; }
  const st=b.parentElement.querySelector(".drbst"), res=await draftAsk({kind:"client-bulk",code:b.dataset.drcmall},{label:"Drafting client wording",status:h=>{ if(st&&st.isConnected) putHTML(st,raw(h)); }});
  if(res.nothing){ snack(res.nothing); return; } if(!res.ok){ snack(res.message||"No drafts came back"); return; }
  const n=res.staged||0; await reloadData();
  snack(n?`${plur(n,"client wording")} drafted, in Intake: each is approved on its own. Nothing was saved in place`:"No drafts came back",n?()=>go("review"):null,"Open Intake"); });
}
/* ===== BL-222 (sprint-drafts-fields) ===== Suggest the thinking fields. Suggest beside a decision's Reasoning and Options considered and
   a RAID item's response: drafts.py reads the item's source passage (its meeting, found by its words) and, for a risk, the closed
   risks with their responses (this project's first, then the portfolio's), skipping anything confidential, and the model words a
   suggestion with sources ("Suggested from…"). For a risk it also judges impact and likelihood: two buttons set them, one click each
   (a staged change, like any edit). A decision's Made and maker are never suggested. In Review, a new risk with no response says
   "Draft a response" on its row and in the proposal's peek, where it works on what is proposed (nothing is in the tracker yet). */
export const PKDRTHINK={resp:"response_action",why:"reasoning",opts:"options"};
/* ===== end BL-222 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function draftResponse(n){ const why=draftWhyNot("thinking"); if(why){ snack(why); return; } openProposal(n);   /* #232-B: Intake and Review's rows use it too */
  setTimeout(()=>{ const t=$('#pkDescDr [data-draft="thinking"][data-drf="resp"]'); if(t) t.click(); },0); }
export function bootPanel0199(){
Object.assign(DRAFTKIND,{thinking:"thinking"});
PKDRBTN.push((x,k,mode)=>{ if(mode!=="record"&&mode!=="proposal") return [];
  if(k==="raid") return [{f:"resp",kind:"thinking",word:!String(x.resp||"").trim()&&mode==="proposal"?"Draft a response":"Suggest",tip:"Suggest a response, with impact and likelihood, from the meeting and closed risks"}];
  if(k==="decisions") return [{f:"why",kind:"thinking",word:"Suggest",tip:"Suggest the reasoning from the meeting where it was decided"},{f:"opts",kind:"thinking",word:"Suggest",tip:"Suggest the options considered, from the meeting"}];
  return []; });
PKDRBODY.thinking=(x,k,f)=>{ const field=PKDRTHINK[f]; if(shared.CUR.mode!=="proposal") return {kind:"thinking",field,id:pkCid()};
  const r=pkRev(); if(!r) return null; return {kind:"thinking",field,proposal:{file:r.file,ref:r.ref},edits:{description:x.t||"",decision:x.t||"",type:x.type||"",response_action:x.resp||"",reasoning:x.why||"",options:x.opts||""}}; };
PKDRTITLE.thinking=f=>f==="resp"?`Suggested ${RESPL((curObj()||{}).type).toLowerCase()}`:({why:"Suggested reasoning",opts:"Suggested options considered"})[f]||"Suggestion";
PKDREXTRA.thinking=(d,k)=>{ if(k!=="raid"||!(d.impact||d.likelihood)) return "";
  const x=curObj()||{}, one=(f,lab,v)=>!v?"":x[f]===v.value?`<div class="drchips"><span>${lab} ${esc(v.value)}, as it is now</span><span class="sub">${esc(v.why||"")}</span></div>`
    :`<div class="drchips"><button type="button" class="btn" data-drset="${f}:${esc(v.value)}">Set ${lab.toLowerCase()} to ${esc(v.value)}</button><span class="sub">${esc(v.why||"")}</span></div>`;
  return one("imp","Impact",d.impact)+one("lik","Likelihood",d.likelihood); };
$("#panel").addEventListener("click",e=>{ const b=e.target.closest(".pkdrhost [data-drset]"); if(!b||!pkOn()) return; e.preventDefault(); e.stopPropagation();
  const [f,v]=b.dataset.drset.split(":"), x=curObj(); if(!x||!["imp","lik"].includes(f)) return; if(x[f]===v){ snack(`${PKFL[f]} is already ${v}`); return; }
  pkImpLik(shared.CUR.k,pkCid(),f,v); b.disabled=true; b.textContent=`${PKFL[f]} set to ${v}`; });
/* Review: a new risk with no response says so on its row, with Draft a response (it opens the proposal and asks) */
$("#reviewBody").addEventListener("click",e=>{ const b=e.target.closest("[data-drrisk]"); if(!b) return; e.preventDefault(); e.stopPropagation();
  draftResponse(+b.dataset.drrisk); },true);
}
/* ===== BL-226 (sprint-drafts-fields) ===== Draft the reason for a health or forecast change. Health: in the health form, Draft the
   reason sends the evidence the form already shows (healthEvidence's reasons, then the project's early warnings: no model in that)
   and the model words one executive sentence in the house voice (executive-style.md). Forecast: in the milestone editor, beside
   "Why is the forecast moving…?", Draft the reason (drafts.py: the overdue work behind the milestone, its dependencies and blockers,
   the pending decisions). Use fills the box; Save is still Alan's. Internal only: neither goes near a client report. Movement's slip
   range gains one sentence from forecast.py's own numbers, by a template (no model). */
export function healthFacts(code){ const ev=healthEvidence(code);
  return [...ev.reasons.map(x=>x[0].toUpperCase()+x.slice(1)),...WARNS().filter(w=>w.p===code).map(w=>`Early warning: ${w.k==="projects"?pName(w.id):w.id} ${w.text}`)]; }
export function drHealthDraw(){ const ev=$("#hEvidence"); if(!ev||!shared.CUR||shared.CUR.mode!=="health") return; let host=$("#hDraft");
  if(!host){ addHTML(ev,"afterend",html`<div id="hDraft" class="pkdrhost"></div>`); host=$("#hDraft"); }
  const c=shared.DRH&&shared.DRH.code===shared.CUR.code?shared.DRH:null;
  putHTML(host,html`<div>${raw(draftBtn("health","Draft the reason","Word the reason from the evidence above, in one executive sentence",'data-drhealth="1"'))}</div>${c?raw(c.html):""}`); hSugDraw(); }
/* ===== #203 ===== the sparkle beside the Health label suggests the health and its reason (healthSuggest.js). The label hook is general:
   FLABEL gets (kind, mode, field) and answers HTML that sits right of the label text. The card sits under the evidence; Use fills the
   two fields (nothing saved), Save uses it and presses the form's Save, Reject (or Esc) clears it and gives the focus back to the sparkle. */
export const FLABEL=[];
export const labelAdorn=(k,mode,n)=>FLABEL.map(f=>f(k,mode,n)).join("");
FLABEL.push((k,mode,n)=>k==="project"&&mode==="health"&&n==="health"?hsSparkHtml():"");
/** @type {any} */ let HSG=null;                         /* {code, html, d, reason} */
export function hSugDraw(){ const ev=$("#hEvidence"); if(!ev||!shared.CUR||shared.CUR.mode!=="health") return; let host=$("#hSug");
  if(!host){ addHTML(ev,"afterend",html`<div id="hSug" class="hsg-host"></div>`); host=$("#hSug"); }
  const c=HSG&&HSG.code===shared.CUR.code?HSG:null;
  putHTML(host,raw(c?(c.d?hsCardHtml(c.d,c.reason):c.html):"")); }
function hsClose(rejected){ if(rejected&&HSG&&HSG.d) hsStat("rejected"); HSG=null; hSugDraw(); const b=$("#pFields [data-hsuggest]"); if(b) b.focus(); }
/** @type {any} */ let HSUSED=null;                       /* {suggested}: Use filled the form; counted when the form is saved, not before */
/** Called by the health form once it has passed validation and is being saved: counts the suggestion that was used (a kept reason counts as used). */
export function hsSaved(){ if(!HSUSED) return; hsStat(HSUSED.kept?"used":hsUse($("#f_reason")?.value,HSUSED.suggested)); HSUSED=null; }
function hsFill(){ const c=HSG; if(!c||!c.d) return false; const hs=$("#f_health"), rs=$("#f_reason"); if(!hs||!rs) return false;
  hs.value=c.d.health; hs.dispatchEvent(new Event("change",{bubbles:true}));
  const kept=rs.value!==c.base;
  if(kept) snack("Your reason was kept: you changed it while the suggestion was being written");   /* never overwritten silently */
  else { rs.value=c.reason; rs.dispatchEvent(new Event("input",{bubbles:true})); }
  HSUSED={suggested:c.d.reason,kept}; HSG=null; hSugDraw(); return true; }
async function hsRun(){ if(!shared.CUR||shared.CUR.mode!=="health") return; const b=$("#pFields [data-hsuggest]");
  if(b&&b.getAttribute("aria-disabled")==="true"){ snack(b.dataset.tip||"Drafting isn't available"); return; }
  const why=draftWhyNot("health"); if(why){ snack(why); return; }
  const code=shared.CUR.code, mine={code,html:"",d:null,reason:"",base:$("#f_reason")?.value??""}; HSG=mine;
  const res=await hsAsk(code,"internal",{status:h=>{ if(HSG===mine){ mine.html=h?`<div class="drstatus" role="status">${h}</div>`:""; hSugDraw(); } }});
  if(HSG!==mine) return;
  if(res.nothing){ mine.html=`<div class="drnone" role="status">${esc(res.nothing)}</div>`; hSugDraw(); return; }
  if(!res.ok||!res.d){ HSG=null; hSugDraw(); snack(res.message||"No draft came back"); return; }
  mine.d=res.d; mine.reason=res.d.reason; hSugDraw(); const card=$("#hsgCard"); if(card) card.querySelector("[data-hsdo=use]")?.focus(); }
/* the forecast */
shared.DRF=null;                                         /* {id, fc, html, d, used} */
export function drFcDraw(){ const w=$("#mvFcWhy"); if(!w||!shared.MV.pend) return; const lab=w.closest(".mv-inl"); if(!lab) return; let host=$("#mvFcDraft");
  if(!host){ addHTML(lab,"afterend",html`<div id="mvFcDraft" class="pkdrhost"></div>`); host=$("#mvFcDraft"); }
  const c=shared.DRF&&shared.DRF.id===shared.MV.pend.id&&shared.DRF.fc===shared.MV.pend.fc?shared.DRF:null;
  putHTML(host,html`<div>${raw(draftBtn("forecast","Draft the reason","Word why it moves from what the tracker shows: overdue work behind it, dependencies, pending decisions",'data-drfc="1"'))}</div>${c?raw(c.html):""}`); }
/* Movement: the slip range in one sentence, from the same numbers (forecast.py's template) */
/* ===== end BL-226 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootPanel0200(){
Object.assign(DRAFTKIND,{health:"reason",forecast:"reason"});
$("#pFields").addEventListener("click",async e=>{ const b=e.target.closest("[data-drhealth]"), u=e.target.closest("#hDraft [data-drdo]");
  if(u&&shared.DRH&&shared.DRH.d){ e.preventDefault(); if(u.dataset.drdo==="discard"){ draftStat("reason","rejected"); shared.DRH=null; drHealthDraw(); return; }
    const t=$("#f_reason"); if(t){ t.value=shared.DRH.d.text; t.dispatchEvent(new Event("input",{bubbles:true})); t.focus(); } shared.DRH.used=shared.DRH.d.text; shared.DRH.html=""; drHealthDraw(); return; }
  if(!b||!shared.CUR||shared.CUR.mode!=="health") return; e.preventDefault(); const why=draftWhyNot("health"); if(why){ snack(why); return; }
  const code=shared.CUR.code, /** @type {any} */ mine=shared.DRH={code,html:""}, to=$("#f_health").value;
  const res=await draftAsk({kind:"health",code,to,facts:healthFacts(code)},{label:"Drafting the reason",status:h=>{ if(shared.DRH===mine){ mine.html=h?`<div class="drstatus" role="status">${h}</div>`:""; drHealthDraw(); } }});
  if(shared.DRH!==mine) return;
  if(res.nothing){ mine.html=`<div class="drnone" role="status">${esc(res.nothing)}</div>`; drHealthDraw(); return; }
  if(!res.ok){ shared.DRH=null; drHealthDraw(); snack(res.message||"No draft came back"); return; }
  mine.d=res; mine.html=draftCardHtml(res,{title:`Draft reason: ${to}`,use:"Use this"}); drHealthDraw(); });
$("#pFields").addEventListener("click",e=>{ const s=e.target.closest("[data-hsuggest]"), u=e.target.closest("#hSug [data-hsdo]");   /* #203 */
  if(s){ e.preventDefault(); hsRun(); return; } if(!u) return; e.preventDefault(); const w=u.dataset.hsdo;
  if(w==="reject"){ hsClose(true); return; }
  if(!HSG||!HSG.d) return; if(hsFill()){ if(w==="save") $("#pSave").click(); else { const t=$("#f_reason"); if(t) t.focus(); } } });
$("#pFields").addEventListener("input",e=>{ if(HSG&&e.target.id==="hsgReason") HSG.reason=e.target.value; });
$("#pFields").addEventListener("keydown",e=>{ if(e.key==="Escape"&&e.target.closest&&e.target.closest("#hSug")&&HSG&&HSG.d){ e.preventDefault(); e.stopPropagation(); hsClose(true); } });
/* counted when the form is saved (used or edited) or left (rejected) */
$("#pFoot").addEventListener("click",e=>{ if(!shared.DRH||!shared.DRH.used||!e.target.closest("#pSave")) return; draftStat("reason",drSame($("#f_reason")?.value,shared.DRH.used)?"used":"edited"); shared.DRH=null; },true);
document.addEventListener("click",async e=>{ const b=e.target.closest("[data-drfc]"), u=e.target.closest("#mvFcDraft [data-drdo]");
  if(u&&shared.DRF&&shared.DRF.d){ e.preventDefault(); e.stopPropagation(); if(u.dataset.drdo==="discard"){ draftStat("reason","rejected"); shared.DRF=null; drFcDraw(); return; }
    const w=$("#mvFcWhy"); if(w){ w.value=shared.DRF.d.text; if(shared.MV.pend) shared.MV.pend.why=shared.DRF.d.text; w.focus(); } shared.DRF.used=shared.DRF.d.text; shared.DRF.html=""; drFcDraw(); return; }
  if(!b||!shared.MV.pend) return; e.preventDefault(); e.stopPropagation(); const why=draftWhyNot("forecast"); if(why){ snack(why); return; }
  const pend=shared.MV.pend, /** @type {any} */ mine=shared.DRF={id:pend.id,fc:pend.fc,html:""};
  const res=await draftAsk({kind:"forecast",id:pend.id,fc:pend.fc},{label:"Drafting the reason",status:h=>{ if(shared.DRF===mine){ mine.html=h?`<div class="drstatus" role="status">${h}</div>`:""; drFcDraw(); } }});
  if(shared.DRF!==mine) return;
  if(res.nothing){ mine.html=`<div class="drnone" role="status">${esc(res.nothing)}</div>`; drFcDraw(); return; }
  if(!res.ok){ shared.DRF=null; drFcDraw(); snack(res.message||"No draft came back"); return; }
  mine.d=res; mine.html=draftCardHtml(res,{title:"Draft reason for the move",use:"Use this"}); drFcDraw(); },true);
}
/* ===== BL-298 (v19-draft-chase) ===== Draft email from the peek. The envelope sits immediately left of Copy link in #pkBar (key C
   while the peek is open), shown for an open action, risk or issue and a pending decision, hidden for closed or cancelled items, a
   proposal and a new item. It opens the chase inside the peek: #pkChase takes #pkScroll's place, so the item stays beside Work, and
   Back (or Esc) returns to the item. The pane is a Preact component (components/peek/ChasePane.jsx); another item, a closed peek or
   an item that is no longer open puts the item back. */
export const chaseIsOpen=()=>{ const b=$("#pkChase"); return !!b&&!b.hidden; };
export function chaseCan(){ const c=shared.CUR; if(!c||c.mode!=="record"||!PKK.includes(c.k)) return false; const x=REC(c.k,c.id);
  return !!x&&(c.k==="decisions"?x.st==="Pending":OPENST(x.st)); }
/* start (BL-322, Sneak peek's "chase Tom, firmer"): the pane's first choices, {tone, to}, as /api/chase/pane takes them */
export function chaseOpen(start){ if(!pkOn()||!chaseCan()) return; const box=$("#pkChase"), id=shared.CUR.id; closePicker("owner",false);
  if(chaseIsOpen()&&box.dataset.id===id&&!start) return;
  box.dataset.id=id; box.hidden=false; $("#pkScroll").hidden=true; $("#pkChaseBtn").setAttribute("aria-pressed","true"); mountChase(box,id,()=>chaseClose(true),start); }
export function chaseClose(focus){ const box=$("#pkChase"); if(!box||box.hidden) return;
  unmountChase(box); box.hidden=true; box.dataset.id=""; $("#pkScroll").hidden=false; $("#pkChaseBtn").setAttribute("aria-pressed","false"); if(focus) $("#pkChaseBtn").focus(); }
export function chaseDraw(x,k,fresh){ const b=$("#pkChaseBtn"); if(!b) return; b.hidden=!chaseCan();
  if(fresh||b.hidden||$("#pkChase").dataset.id!==(shared.CUR&&shared.CUR.id)) chaseClose(false); }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootPanelChase(){
ICONS.chase=CHASE_ICON.map(([tag,a])=>`<${tag}${Object.entries(a).map(([n,v])=>` ${n}="${v}"`).join("")}/>`).join("");   /* the icon's element data (ChasePane.jsx) as ic() takes it */
addHTML($("#pkLink"),"beforebegin",raw(ibtn("chase","Draft email",'id="pkChaseBtn" aria-pressed="false" hidden',"","C")));
addHTML($("#pkScroll"),"afterend",html`<div class="pk-scroll pk-chase" id="pkChase" hidden></div>`);
$("#pkChaseBtn").onclick=()=>chaseIsOpen()?chaseClose(true):chaseOpen();
PKDRAW.push(chaseDraw);
document.addEventListener("keydown",e=>{ if(e.key.toLowerCase()!=="c"||e.metaKey||e.ctrlKey||e.altKey||e.repeat||!pkOn()||typing()) return;
  const a=document.activeElement; if(document.querySelector("dialog[open]")||shared.PKPOP||(a&&a.closest&&a.closest("#chat,[role=menu],.cal,.combo,.pkpop"))) return;
  const b=$("#pkChaseBtn"); if(!b||b.hidden) return; e.preventDefault(); chaseOpen(); });
}
/* ===== end BL-298 ===== */
