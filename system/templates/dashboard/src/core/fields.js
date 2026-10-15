// @ts-check
/* core/fields.js (BL-231 step 2b): sources, the calendar picker, dates in words, the owner combobox, ⌘↵, tick boxes, `addEl`, auto-grow and the weekend note.
   Moved from script/ unchanged, apart from `export`, `shared.` for the shared state (state.js) and the steps that ran at load,
   which are now boot…() functions called by src/main.js in today's order. Pieces: 0042-sources.js, 0043-calendar-picker.js, 0044-bl-147-sprint-ux.js, 0045-owner-combobox.js, 0057-bl-274-sprint-ui-sweep.js, 0062-bl-216-sprint-ui-sweep.js, 0099-after-bl-120.js, 0115-bl-146-sprint-ux.js, 0116-after-bl-146.js, 0180-bl-181-sprint-peek-new.js */
import { chatScroll, nowIso, stampMsg, step } from "../ask.js";
import { A, DEC, peopleAll, R, REV, useCount } from "./data.js";
import { $, addHTML, esc, html, ic, putHTML, raw } from "./dom.js";
import { mountCombobox } from "../components/Combobox.jsx";
import { openDatePicker } from "../components/Picker.jsx";
import { D, DATE, DDATE, fd, isMe, S, TODAY, toIso } from "./page.js";
import { api, apply, editProposal, needVault, oneLine, refreshAll, save, snack, split, viaServer } from "./server.js";
import { shared } from "./state.js";
import { hubFor, hubLink } from "../meetings.js";
import { pkCommit, PKDRAW, pkLabel, REC } from "../panel.js";
import { pkOn, saveAndClose, warnsOf, WSIG } from "../projects.js";
import { WKRVF } from "../review.js";
import { isHiddenPerson, ownerFinal, personOf, regAddAlias, regSetHidden, resolvePerson } from "../settings.js";
import { pkAdd } from "../today.js";
import { items } from "../work.js";
/* ======================= sources ======================= */
export function srcParse(x){ if(!x) return null; if(/^(Email|Teams) · /.test(x)){ const parts=x.split(" · "), o={type:parts[0]}; parts.slice(1).forEach(p=>{ const i=p.indexOf(": "); if(i>0) o[p.slice(0,i)]=p.slice(i+2); }); return o; }
  const m=x.match(/^((?:projects|system)\/.+?\.(docx|pdf|vtt|xlsx|txt|md))(?:#p(\d+))?(?: — (.+))?$/);   /* BL-301 E: a note's line, "#p4" */
  if(m) return {type:"File",path:m[1],line:m[3]?+m[3]:0,section:m[4]||(m[3]?`line ${m[3]}`:""),name:m[1].split("/").pop()}; return {type:"Text",text:x}; }
/* BL-301 E: how a note's source ("…/08 Notes/<title>.md#p4") opens: the Notes tab (part B) sets NOTE_OPEN.fn(path, line) to open
   the note at that line, highlighted; until it does, the file opens as any other. */
export const NOTE_OPEN={fn:null};
export const srcShort=x=>{ const o=srcParse(x); if(!o) return "—"; if(o.type==="File") return o.name.replace(/\.[a-z]+$/,""); if(o.type==="Email") return "Email · "+(o.Subject||""); if(o.type==="Teams") return "Teams · "+(o.Channel||o.Chat||""); return o.text; };
export function srcHTML(x){ const o=srcParse(x); if(!o) return "—";
  if(o.type==="File"){ const t=!shared.LOADING&&hubFor({path:o.path}); return `<a href="#" class="srclink" data-openfile="${esc(o.path)}"${o.line?` data-noteline="${o.line}"`:""}>${esc(o.name)}</a>${o.section?` <span class="sub">· ${esc(o.section)}</span>`:""}<div class="sub">${esc(o.path.slice(0,o.path.lastIndexOf("/")))}</div>${t?`<div>${hubLink(t)}</div>`:""}`; }
  if(o.type==="Email") return `<dl class="srcmeta"><dt>From</dt><dd>${esc(o.From||"—")}</dd><dt>Subject</dt><dd>${esc(o.Subject||"—")}</dd><dt>Sent</dt><dd>${esc(fd(o.Sent||"—"))}</dd></dl>${o.Link?`<a href="${esc(o.Link)}" target="_blank" rel="noopener" class="srclink">Open in Outlook</a>`:'<span class="sub">No message link stored</span>'}`;
  if(o.type==="Teams") return `<dl class="srcmeta"><dt>${o.Channel?"Channel":"Chat"}</dt><dd>${esc(o.Channel||o.Chat)}</dd><dt>From</dt><dd>${esc(o.From||"—")}</dd><dt>Sent</dt><dd>${esc(fd(o.Sent||"—"))}</dd></dl>${o.Link?`<a href="${esc(o.Link)}" target="_blank" rel="noopener" class="srclink">Open in Teams</a>`:'<span class="sub">No message link stored</span>'}`;
  return esc(o.text); }
export let openPath = function(p){ if(!p) return; if(viaServer()){ api("/api/open",{path:p.replace(/\/$/,"")}).then(r=>{ if(!r.ok) snack(oneLine(r.message)); }); return; } window.open(p.split("/").map(encodeURIComponent).join("/"),"_blank","noopener"); };
/* BL-231: what this block did at load, run in today's order by src/main.js (piece 0042's place) */
export function bootSources(){
document.addEventListener("click",e=>{ const f=e.target.closest("[data-openfile]"); if(f){ e.preventDefault(); if(f.dataset.noteline&&NOTE_OPEN.fn) NOTE_OPEN.fn(f.dataset.openfile,+f.dataset.noteline); else openPath(f.dataset.openfile); } });
}
/* ======================= calendar picker ======================= */
shared.CAL=null;
export const CALI=ic("calendar")   /* BL-158: the one calendar icon */;
export function closeCal(){ if(shared.CAL){ shared.CAL.remove(); shared.CAL=null; } }
/* The popup works from options on the field (BL-74): data-max ("today" or a YYYY-MM-DD) is the latest day that can be chosen,
   data-noclear hides Clear, and a read-only field (data-pick) opens it when clicked. Arrow keys move by day (up and down
   by week, Home and End within the week, PageUp and PageDown by month), Enter or Space chooses, Escape closes, for every date field. */
export function openCal(inp,btn){ closeCal(); const max=inp.dataset.max==="today"?TODAY:(inp.dataset.max||""), min=inp.dataset.min==="today"?TODAY:(inp.dataset.min||""), noclear=inp.dataset.noclear!==undefined;   /* min (BL-83): the earliest day, as max is the latest */
  let cur=DDATE.test(inp.value)?toIso(inp.value):TODAY; if(max&&cur>max) cur=max; if(min&&cur<min) cur=min; let y=+cur.slice(0,4), m=+cur.slice(5,7)-1; const box=document.createElement("div"); box.className="cal"; box.setAttribute("role","dialog"); box.setAttribute("aria-label","Choose a date"); (inp.closest("dialog")||document.body).appendChild(box); shared.CAL=box;   /* inside an open dialog, else the page behind it is inert */
  const r=btn.getBoundingClientRect(); box.style.left=Math.max(8,Math.min(r.right-252,innerWidth-262))+"px"; box.style.top=(r.bottom+310>innerHeight?Math.max(8,r.top-310):r.bottom+4)+"px";
  const pad=n=>String(n).padStart(2,"0"), isoOf=d=>`${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;
  const draw=(focus)=>{ const f=new Date(y,m,1), st=(f.getDay()+6)%7, dn=new Date(y,m+1,0).getDate(); let g=["Mo","Tu","We","Th","Fr","Sa","Su"].map(d=>`<span>${d}</span>`).join("")+"<span></span>".repeat(st);
    for(let d=1;d<=dn;d++){ const v=`${y}-${pad(m+1)}-${pad(d)}`, off=(max&&v>max)||(min&&v<min); g+=`<button type="button" data-v="${fd(v)}" tabindex="${v===cur?0:-1}" ${off?'disabled aria-disabled="true"':""} aria-label="${fd(v)}" class="${v===TODAY?"today":""} ${v===toIso(inp.value)?"sel":""} ${off?"off":""}">${d}</button>`; }
    putHTML(box,html`<div class="ch"><button type="button" data-n="-1" aria-label="Previous month">‹</button><span>${raw(f.toLocaleString("en-GB",{month:"long"}))} ${raw(y)}</span><button type="button" data-n="1" aria-label="Next month">›</button></div><div class="cg">${raw(g)}</div><div class="cf"><button type="button" data-v="${fd(min&&TODAY<min?min:max&&TODAY>max?max:TODAY)}">Today</button>${noclear?"":html`<button type="button" data-v="">Clear</button>`}</div>`);
    if(focus){ const c=box.querySelector('.cg button[tabindex="0"]'); if(c) c.focus(); } };
  const goTo=(iso)=>{ if(max&&iso>max) iso=max; if(min&&iso<min) iso=min; cur=iso; y=+iso.slice(0,4); m=+iso.slice(5,7)-1; draw(true); };
  draw(true); box.addEventListener("click",e=>{ e.stopPropagation(); const b=e.target.closest("button"); if(!b||b.disabled) return; if(b.dataset.n){ m+=+b.dataset.n; if(m<0){m=11;y--;} if(m>11){m=0;y++;} cur=`${y}-${pad(m+1)}-${pad(Math.min(+cur.slice(8,10),new Date(y,m+1,0).getDate()))}`; if(max&&cur>max) cur=max; if(min&&cur<min) cur=min; draw(false); return; } if("v" in b.dataset){ inp.value=b.dataset.v; inp.dispatchEvent(new Event("input",{bubbles:true})); closeCal(); (inp.readOnly?btn:inp).focus(); } });
  box.addEventListener("keydown",e=>{ if(e.key==="Escape"){ e.preventDefault(); e.stopPropagation(); closeCal(); btn.focus(); return; }
    const d=new Date(cur+"T12:00:00"), step={ArrowLeft:-1,ArrowRight:1,ArrowUp:-7,ArrowDown:7}[e.key];
    if(step!==undefined) d.setDate(d.getDate()+step); else if(e.key==="Home") d.setDate(d.getDate()-((d.getDay()+6)%7)); else if(e.key==="End") d.setDate(d.getDate()+6-((d.getDay()+6)%7));
    else if(e.key==="PageUp"||e.key==="PageDown"){ const day=d.getDate(); d.setDate(1); d.setMonth(d.getMonth()+(e.key==="PageUp"?-1:1)); d.setDate(Math.min(day,new Date(d.getFullYear(),d.getMonth()+1,0).getDate())); } else return;
    e.preventDefault(); goTo(isoOf(d)); });
  if(shared.CAL&&wkField(inp)){ wkMark(shared.CAL); new MutationObserver(()=>wkMark(shared.CAL)).observe(shared.CAL,{childList:true,subtree:true}); } }
   /* BL-147: in a typed field Space types ("next fri") */
/* BL-231: what this block did at load, run in today's order by src/main.js (piece 0043's place) */
export function bootCalendar(){
document.addEventListener("click",e=>{ const b=e.target.closest("[data-cal]"); if(b){ e.stopPropagation(); openCal(document.getElementById(b.dataset.cal),b); return; }
  const f=e.target.closest("input[data-pick]"); if(f){ e.stopPropagation(); openCal(f,f.closest(".dwrap").querySelector("[data-cal]")); return; } if(shared.CAL&&!e.target.closest(".cal")) closeCal(); });
document.addEventListener("keydown",e=>{ const f=e.target.closest&&e.target.closest("input[data-pick]"); if(f&&["Enter"," ","ArrowDown"].includes(e.key)&&!(e.key===" "&&!f.readOnly)){ e.preventDefault(); openCal(f,f.closest(".dwrap").querySelector("[data-cal]")); } });
}
/* ===== BL-147 (sprint-ux) ===== dates typed in plain words. One parser, parseWhen(text,today,due), behind every date field:
   today, tomorrow, yesterday; a weekday ("fri", "friday": the next one, never today; "next fri": the one after that); +3d, +2w,
   +1m (also "3 days", "in 2 weeks"); "next week" (its Monday), "end of week" (Friday), "end of month"; a day and month ("15/10",
   "15-10", "15 oct": this year, or next year when a due date would otherwise be in the past); and DD-MM-YYYY (also with / or .,
   a two-digit year, or YYYY-MM-DD). It returns the day as YYYY-MM-DD, or null. While a date field has the focus a small line
   under it says what it understood ("Friday 16-10-2026") or, in words with two examples, that it didn't; leaving the field,
   Enter or a change puts DD-MM-YYYY in the field before anything else reads it, so every existing check and save works on
   DD-MM-YYYY as before. Stored dates stay YYYY-MM-DD and shown dates DD-MM-YYYY (creaite-rules). */
export const DATE_HELP="Try “fri”, “+3d”, “15-10” or 16-10-2026.";
export const DAYS=["sun","mon","tue","wed","thu","fri","sat"];
export function parseWhen(text,today=TODAY,due=false){ let s=String(text||"").trim().toLowerCase().replace(/\s+/g," ").replace(/[.,]$/,""); if(!s) return null;
  const pad=n=>String(n).padStart(2,"0"), iso=d=>`${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`, t0=new Date(today+"T12:00:00");
  const add=(n,unit)=>{ const d=new Date(t0); if(unit==="m"){ const day=d.getDate(); d.setDate(1); d.setMonth(d.getMonth()+n); d.setDate(Math.min(day,new Date(d.getFullYear(),d.getMonth()+1,0).getDate())); } else d.setDate(d.getDate()+n*(unit==="w"?7:1)); return iso(d); };
  const real=(y,m,d)=>{ if(y<100) y+=2000; const x=new Date(y,m-1,d,12); return x.getFullYear()===y&&x.getMonth()===m-1&&x.getDate()===d?iso(x):null; };
  const dm=(d,m,y)=>{ if(y!=null) return real(+y,+m,+d); const yr=t0.getFullYear(); let r=real(yr,+m,+d); if(r&&due&&r<today) r=real(yr+1,+m,+d); return r; };
  const MON=["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"], mon=w=>{ const i=MON.indexOf(w.slice(0,3)); return i>=0&&("january february march april may june july august september sept october november december".split(" ").some(n=>n.startsWith(w))||w.length===3)?i+1:0; };
  if(s==="today"||s==="now") return today; if(s==="tomorrow"||s==="tmrw"||s==="tmr") return add(1,"d"); if(s==="yesterday") return add(-1,"d");
  let m=s.match(/^(next |this )?([a-z]{3,9})$/);
  if(m){ const w=DAYS.findIndex(d=>m[2].startsWith(d)&&("sunday monday tuesday wednesday thursday friday saturday tues weds thur thurs".split(" ").some(n=>n.startsWith(m[2]))));
    if(w>=0){ const ahead=((w-t0.getDay()+7)%7)||7; return add(ahead+(m[1]==="next "?7:0),"d"); } }
  if(s==="next week") return add(((1-t0.getDay()+7)%7)||7,"d");                                         /* Monday */
  if(s==="end of week"||s==="eow") return add((5-t0.getDay()+7)%7,"d");                                 /* Friday: today on a Friday */
  if(s==="end of month"||s==="eom") return iso(new Date(t0.getFullYear(),t0.getMonth()+1,0,12));
  if(s==="end of next week") return add(((5-t0.getDay()+7)%7)+7,"d");
  m=s.match(/^(?:\+|in )?\s*(\d{1,3}) ?(d|days?|w|wks?|weeks?|m|mos?|months?)$/); if(m) return add(+m[1],m[2][0]);
  m=s.match(/^\+(\d{1,3})$/); if(m) return add(+m[1],"d");
  m=s.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/); if(m) return real(+m[1],+m[2],+m[3]);
  m=s.match(/^(\d{1,2})[\/\-. ](\d{1,2})(?:[\/\-. ](\d{2}|\d{4}))?$/); if(m) return dm(m[1],m[2],m[3]);
  m=s.match(/^(\d{1,2})(?:st|nd|rd|th)? ([a-z]{3,9})(?: (\d{4}))?$/); if(m&&mon(m[2])) return dm(m[1],mon(m[2]),m[3]);
  m=s.match(/^([a-z]{3,9}) (\d{1,2})(?:st|nd|rd|th)?(?: (\d{4}))?$/); if(m&&mon(m[1])) return dm(m[2],mon(m[1]),m[3]);
  return null; }
export const dateSaid=iso=>`${new Date(iso+"T12:00:00").toLocaleDateString("en-GB",{weekday:"long"})} ${fd(iso)}`;
/* which fields: every typed date field (item forms, inline cells, the project page's No due date card, filters' From and To,
   Generate's range, Review's and the change-several bar's due date, the move-date dialog, Quick capture); read-only ones are picker only */
export const isDateField=el=>!!(el&&el.tagName==="INPUT"&&!el.readOnly&&el.matches('[data-date],[placeholder="DD-MM-YYYY"],#bdDate,[data-und]'));
export const dueField=el=>/(^|_)due$/.test(el.name||el.id||"")||el.dataset.cf==="due"||el.dataset.bf==="due"||["rvDate","bdDate","bkDate","deReply"].includes(el.id)||el.dataset.und!=null||el.name==="fc";
export function dateRead(el){ const v=el.value.trim(); if(!v) return {empty:true}; const iso=parseWhen(v,TODAY,dueField(el)); if(!iso) return {bad:true};
  const max=el.dataset.max==="today"?TODAY:el.dataset.max, min=el.dataset.min==="today"?TODAY:el.dataset.min;
  return {iso, late:!!(max&&iso>max), early:!!(min&&iso<min)}; }
export function dateHint(el){ let h=$("#dateHint"); if(!h){ h=document.createElement("div"); h.id="dateHint"; h.className="datehint"; h.setAttribute("role","status"); h.setAttribute("aria-live","polite"); }
  (el.closest("dialog")||document.body).appendChild(h);                                                /* inside an open dialog, as the calendar is */
  const r=dateRead(el); if(r.empty){ h.hidden=true; return; }
  h.classList.toggle("bad",!!(r.bad||r.late||r.early));
  h.textContent=r.bad?`Not a date creaite knows. ${DATE_HELP}`:r.late?`${dateSaid(r.iso)} is after today: choose today or earlier.`:r.early?`${dateSaid(r.iso)} is before today: choose today or later.`:dateSaid(r.iso);
  const b=el.getBoundingClientRect(); h.hidden=false; h.style.left=Math.max(8,Math.min(b.left,innerWidth-h.offsetWidth-8))+"px";
  h.style.top=(b.bottom+h.offsetHeight+6>innerHeight?b.top-h.offsetHeight-4:b.bottom+4)+"px";
  { const h=$("#dateHint"); if(!h||h.hidden||!wkField(el)) return; const d=dateRead(el);
    const n=d&&!d.bad&&d.iso?weekendNote(d.iso):null; if(n) h.textContent=`${dateSaid(d.iso)}: a weekend. You'll be offered the nearest working days.`; } }
export function dateHide(){ const h=$("#dateHint"); if(h) h.hidden=true; }
/* the field then holds DD-MM-YYYY: done first (capturing, registered before every other date handler), so each check and save reads it */
export function dateSettle(el){ const r=dateRead(el); if(r.iso&&el.value.trim()!==fd(r.iso)) el.value=fd(r.iso); }
   /* ↓ opens the calendar, as in a picker field */
/* ===== end BL-147 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js (piece 0044's place) */
export function bootDateWords(){
document.addEventListener("input",e=>{ if(isDateField(e.target)&&document.activeElement===e.target) dateHint(e.target); },true);
document.addEventListener("focusin",e=>{ if(isDateField(e.target)) dateHint(e.target); },true);
document.addEventListener("keydown",e=>{ if(e.key==="Enter"&&isDateField(e.target)){ dateSettle(e.target); dateHint(e.target); } },true);
document.addEventListener("change",e=>{ if(isDateField(e.target)) dateSettle(e.target); },true);
document.addEventListener("keydown",e=>{ const f=e.target; if(e.key==="ArrowDown"&&!e.altKey&&!e.metaKey&&!e.ctrlKey&&isDateField(f)&&!f.hasAttribute("data-pick")){ const b=f.closest(".dwrap")?.querySelector("[data-cal]"); if(b){ e.preventDefault(); dateSettle(f); dateHide(); openCal(f,b); } } });
document.addEventListener("focusout",e=>{ if(isDateField(e.target)){ dateSettle(e.target); dateHide(); } },true);
addEventListener("scroll",()=>{ const a=document.activeElement; if(isDateField(a)&&!$("#dateHint")?.hidden) dateHint(a); },true);
}
/* ======================= owner combobox ======================= */
/* BL-18 A: the project in hand's own people and workstreams come first (derived from its items and the register) */
export const formProject=()=>$("#f_p")?.value||(shared.CUR&&(shared.CUR.draft&&shared.CUR.draft.p||(shared.CUR.mode==="record"&&(REC(shared.CUR.k,shared.CUR.id)||{}).p)||shared.CUR.code))||"";
export const projPeople=code=>{ if(!code) return []; const s=new Set([...A.filter(a=>a.p===code).map(a=>a.o),...R.filter(r=>r.p===code).map(r=>r.o),...DEC.filter(d=>d.p===code).map(d=>d.by),...((D.stakeholders||{})[code]||[])]);
  s.delete("TBC"); s.delete(""); return [...new Set([...s].map(personOf))].filter(n=>n&&!isHiddenPerson(n)).sort((a,b)=>isMe(a)?-1:isMe(b)?1:a.localeCompare(b)); };
export const projFirst=(all,mine)=>{ const m=new Set(mine); return [...mine,...all.filter(n=>!m.has(n))]; };
/* BL-55: aliases and emails find the person; likely matches are offered; a stranger is a new person. BL-187 (fix-peek-140): the one
   matcher, used by this combo and by the peek's owner list. Returns the names that match (L) and what to offer: a name to pick,
   "Is “Sara” Sara Khan?" (alias), or a new person as typed. */
export function ownerMatches(q,pool){ q=String(q||"").trim(); const ql=q.toLowerCase(), rs=q?resolvePerson(q):null;
  const L=pool.filter(n=>!q||n.toLowerCase().includes(ql)); if(rs&&rs.name&&!L.includes(rs.name)&&pool.includes(rs.name)) L.unshift(rs.name);
  const items=L.map(n=>({n,t:"pick"})); if(rs&&rs.status==="likely") rs.candidates.filter(c=>!L.includes(c)).forEach(c=>items.push({n:c,t:"alias",typed:q})); if(q&&rs&&(rs.status==="likely"||rs.status==="unknown")) items.push({n:q,t:"new"});
  return {L,items}; }
/* BL-316: the form's owner field is the Combobox block (components/Combobox.jsx): the project in hand's people first, under its
   name, then everyone else; an alias or an email finds the person; "Is “Sara” Sara Khan?" remembers the alias; a stranger is a
   new person (the details dialog); each name's × hides it from the list. The one matcher is ownerMatches (BL-187). */
export function ownerOptions(q,typed){ const code=formProject(), mine=projPeople(code), pool=projFirst(peopleAll(),mine), split=new Set(mine), {L,items}=ownerMatches(typed?q:"",pool);
  const nMine=L.filter(n=>split.has(n)).length, head=i=>!code||!nMine||nMine===L.length?"":i===0?code:i===nMine?"Everyone else":"";
  return items.map((it,i)=>it.t==="new"?{v:it.n,t:"new",label:`＋ New person “${it.n}”…`,cls:"new",head:head(i)}
    :it.t==="alias"?{v:it.n,t:"alias",typed:it.typed,label:`Is “${it.typed}” ${it.n}?`,sub:"Yes, and remember it",head:head(i)}
    :{v:it.n,t:"pick",label:`${it.n}${isMe(it.n)?" (you)":""}`,fill:it.n,sub:String(useCount(it.n)),head:head(i),removeLabel:`Remove ${it.n} from the list`,remove:()=>regSetHidden(it.n,true)}); }
/** Draw each owner field (`.combohost` placeholders from the form) as a Combobox. @param {Element} root */
export function mountOwnerFields(root){ root.querySelectorAll(".combohost[data-combo]").forEach(host=>{ const h=/** @type {HTMLElement} */(host), n=h.dataset.combo||"o", id="f_"+n;
  mountCombobox(h,{id,name:n,value:h.dataset.v||"",label:h.dataset.label||"Owner",placeholder:"Choose or type a name",options:ownerOptions,
    onPick:async o=>{ const inp=/** @type {HTMLInputElement|null} */(document.getElementById(id)); if(!inp) return false;
      if(o.t==="new"){ const name=await ownerFinal(o.v,{skipMatch:true}); if(name!==null) inp.value=name; return false; }
      if(o.t==="alias"){ if(await regAddAlias(o.v,o.typed)) inp.value=o.v; return false; }
      return true; }}); }); }
/* BL-231: what this block did at load, run in today's order by src/main.js (piece 0045's place) */
export function bootOwnerCombo(){ /* BL-316: the owner field is a Combobox, which carries its own keys and clicks */ }
/* ===== BL-274 (sprint-ui-sweep) ===== one ⌘↵ for every editor in the peek's place. An editor registers when it is the one the
   key is for and the save its Save button runs (which closes it); the one handler runs that save: the same checks, messages,
   staging and Undo. A new editor gets ⌘↵ by registering. Plain Enter keeps its meaning (a new line in a text area, a pick in a
   list); with a picker open (a date list, the people list, a combo), the picker takes the key first and the save follows. */
export const CMDENTER=[];
export function onCmdEnter(name,when,save){ CMDENTER.push({name,when,save}); }
export const cmdEnterPicker=()=>!!document.querySelector(".combo.open,#mvCal:not([hidden]),#mvPop:not([hidden]),.cal:not([hidden]):not(:empty)");
/* ===== end BL-274 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js (piece 0057's place) */
export function bootCmdEnter(){
window.addEventListener("keydown",e=>{ if(!(e.key==="Enter"&&(e.metaKey||e.ctrlKey))) return; const ed=CMDENTER.find(x=>x.when(e.target)); if(!ed) return;
  if(cmdEnterPicker()){ e.preventDefault(); e.stopImmediatePropagation(); if(!e.repeat) setTimeout(()=>ed.save(),0); return; }   /* pick, then save: the key is this handler's alone, so nothing later in the page acts on it too */
  e.preventDefault(); e.stopImmediatePropagation(); if(!e.repeat) ed.save(); },true);
/* the project panel and the forms (project details, health, a proposal): BL-78 */
onCmdEnter("panel",t=>!!shared.CUR&&shared.EDITING&&!pkOn()&&(t===document.body||!!(t.closest&&t.closest("#panel"))),saveAndClose);
}
/* ===== BL-216 (sprint-ui-sweep) ===== a small tick box answers a click anywhere in the 24 by 24 square round it, inside its
   cell (Review's rows and group ticks, Intake's meetings and files, Activity's changes). The box keeps its drawn size. */
export const TICK24="#reviewBody td,#reviewBody .rgroup h2,#mtgBody td,#inboxTbl td,#actTbl td.actck";
export function tickNear(host,x,y){ return [...host.querySelectorAll(":scope>input[type=checkbox]")].find(i=>{ const r=i.getBoundingClientRect(); return Math.abs(x-(r.left+r.width/2))<=12&&Math.abs(y-(r.top+r.height/2))<=12; }); }
/* ===== end BL-216 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js (piece 0062's place) */
export function bootTickBoxes(){
document.addEventListener("click",e=>{ if(!e.isTrusted||e.target.closest("input,button,a,select,textarea,label")) return; const host=e.target.closest(TICK24); if(!host) return;
  const cb=tickNear(host,e.clientX,e.clientY); if(!cb||cb.disabled) return; e.preventDefault(); e.stopPropagation(); cb.focus({preventScroll:true}); cb.click(); },true);
}
export function addEl(cls,h,at){ const d=document.createElement("div"); d.className=cls; putHTML(d,typeof h==="string"?raw(h):h);   /* BL-228 D: callers pass html`…` (or raw() for mdChat and the cards); a string is still taken as markup, as tests and older callers expect */ const first=!$("#chLog").children.length; $("#chLog").appendChild(d); chatScroll(first||cls==="msg u");
  if(cls==="msg u"&&at!==null) stampMsg(d,at||nowIso()); return d; }   /* Alan's bubbles are stamped when made; a saved chat passes its own time, or null for none (BL-108) */
/* ===== BL-146 (sprint-ux) ===== one auto-grow helper for every text box, made from BL-145's chFit (there is only one).
   autoGrow(el,max) sets a textarea's height from its content, between its own minimum (its CSS min-height or its rows, or a
   height Alan dragged it to) and a maximum (60% of the window; the chat box passes its own), and scrolls inside beyond that
   with the cursor in view. The wiring below runs it for every textarea, present and future: on input and paste, whenever code
   sets .value, when one is added to the page (a record opened, a dialog filled), shown or changes width, and on a window,
   theme, density or font change. The drag handle stays. The height changes at once: height never animates (BL-136). */
export const AG_CAP=0.6;
export function autoGrow(el,max){ if(!el||el.tagName!=="TEXTAREA"||!el.isConnected||!el.offsetParent) return;
  const cs=getComputedStyle(el), bdr=parseFloat(cs.borderTopWidth)+parseFloat(cs.borderBottomWidth), minH=Math.max(parseFloat(cs.minHeight)||0,el._agMin||0);
  max=Math.max(minH,max??Math.floor(window.innerHeight*AG_CAP));
  const top=el.scrollTop, atEnd=el.selectionEnd>=el.value.length, focused=document.activeElement===el;
  const keep=[]; for(let a=el.parentElement;a&&a!==document.body;a=a.parentElement) if(a.scrollTop) keep.push([a,a.scrollTop]);   /* the page doesn't jump */
  el.style.height="auto";                                                    /* measure the content at its natural height */
  const need=el.scrollHeight+bdr, h=Math.min(max,Math.max(minH,need));
  el.style.height=h+"px"; el._agH=h; el._agW=el.offsetWidth; el.classList.add("agfit"); el.classList.toggle("agscroll",need>max+1);
  keep.forEach(([a,t])=>a.scrollTop=t);
  if(focused){ el.scrollTop=atEnd?el.scrollHeight:top; if(!atEnd&&need>max+1) chCaret(el); } else el.scrollTop=top;   /* keep the cursor in view */
  return h; }
export function agFit(el){ if(el===$("#chIn")) chFit(); else autoGrow(el); }
export function agFitAll(){ document.querySelectorAll("textarea").forEach(agFit); }
(()=>{ const d=Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,"value");
  Object.defineProperty(HTMLTextAreaElement.prototype,"value",{configurable:true,get(){ return d.get.call(this); },set(v){ d.set.call(this,v); if(this.id!=="chIn") autoGrow(this); }});   /* a record opened, a draft restored, Clear */
  document.addEventListener("input",e=>{ if(e.target.tagName==="TEXTAREA"&&e.target.id!=="chIn") autoGrow(e.target); },true);   /* typing, paste, delete */
  const ro=window.ResizeObserver&&new ResizeObserver(es=>es.forEach(({target:el})=>{
    if(!el.offsetParent) return;
    const wide=()=>Math.abs(el.offsetWidth-(el._agW||0))>0.5;
    if(wide()) return requestAnimationFrame(()=>{ if(wide()) agFit(el); });   /* shown, or a new width: the wrapping changes (next frame, unless already fitted: BL-283) */
    if(el.id!=="chIn"&&el._agH&&Math.abs(el.offsetHeight-el._agH)>1){ el._agMin=el.offsetHeight; el._agH=el.offsetHeight; } }));   /* dragged by hand: that is its new minimum */
  let queued=false; const scan=()=>{ queued=false; document.querySelectorAll("textarea:not([data-ag])").forEach(el=>{ el.dataset.ag="1"; ro&&ro.observe(el); agFit(el); }); };
  new MutationObserver(()=>{ if(!queued){ queued=true; requestAnimationFrame(scan); } }).observe(document.body,{childList:true,subtree:true});
  scan(); window.addEventListener("resize",agFitAll);
  new MutationObserver(()=>requestAnimationFrame(agFitAll)).observe(document.documentElement,{attributes:true,attributeFilter:["data-palette","data-theme","data-density"]});
  document.fonts?.ready?.then(agFitAll); document.fonts?.addEventListener?.("loadingdone",agFitAll); })();
/* ===== end BL-146 ===== */
export function chFit(){ const el=$("#chIn"), chat=$("#chat"); if(!el||!chat||!chat.classList.contains("on")||!el.offsetParent) return;
  autoGrow(el,Math.floor(Math.min(chat.clientHeight,window.innerHeight)*0.5));   /* BL-146: the shared helper, with the chat's own maximum */
  const box=el.closest(".chin"); if(box) box.style.setProperty("--acmax",Math.max(96,Math.min(300,chat.clientHeight-box.offsetHeight-4))+"px"); }   /* the suggestions fit above it */
/* the cursor somewhere in the middle of a long message: scroll just enough to show its line */
export function chCaret(el){ const lh=parseFloat(getComputedStyle(el).lineHeight)||18, before=el.value.slice(0,el.selectionEnd).split("\n").length-1;
  const y=before*lh; if(y<el.scrollTop) el.scrollTop=y; else if(y+lh>el.scrollTop+el.clientHeight) el.scrollTop=y+lh-el.clientHeight+12; }
(()=>{ const el=$("#chIn"), d=Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,"value");
  Object.defineProperty(el,"value",{configurable:true,get(){ return d.get.call(this); },set(v){ d.set.call(this,v); chFit(); }});   /* send, a suggestion, a new chat */
  el.addEventListener("input",chFit);
  if(window.ResizeObserver) new ResizeObserver(()=>requestAnimationFrame(chFit)).observe($("#chat"));   /* opening, the grip, the window, the text size */
  window.addEventListener("resize",chFit);
  new MutationObserver(()=>requestAnimationFrame(chFit)).observe(document.documentElement,{attributes:true,attributeFilter:["data-palette","data-theme","data-density"]});
  document.fonts?.ready?.then(chFit); document.fonts?.addEventListener?.("loadingdone",chFit); })();
/* ===== end BL-145 ===== */
/* ===== BL-181 (sprint-peek-new) ===== a weekend date on a work item always raises an alert, never a block. One helper, weekendNote(iso),
   says whether a day is a weekend (settings.json work.weekend_days, Saturday and Sunday by default) and which working days are nearest;
   wkAsk shows the alert beside the field ("Saturday 17-10-2026 is a weekend." with the Friday and the Monday, and Keep this date),
   and the change waits for the choice: a working day sets that date and saves it, Keep saves the weekend date. Where: the peek's
   due and needed-by chips (and its typed box, checked as it is typed), a decision's Revisit written as a date, the table's date
   cell (BL-123), the bulk bar (BL-124), the Board's date prompt and an undated card's date; every calendar marks weekend days.
   Review notes a proposal's weekend date with the two buttons, which edit the proposal; the "weekend due date" early warning lists
   open items with one (built by build_dashboard.py), and the peek offers the same buttons beside it. Dates that record what
   happened (raised, closed, made, a Quick capture note's date) and milestones are never alerted. */
export const WKNAME=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"];
export const wkDays=()=>new Set(Array.isArray(S.weekendDays)?S.weekendDays:[5,6]);
export const wkDow=iso=>(new Date(iso+"T00:00:00Z").getUTCDay()+6)%7;
export const wkLong=iso=>`${WKNAME[wkDow(iso)]} ${fd(iso)}`;
export function weekendNote(iso){ if(!iso||!DATE.test(String(iso))) return null; const W=wkDays(); if(W.size>=7||!W.has(wkDow(iso))) return null;
  let p=iso, n=iso; do p=pkAdd(p,-1); while(W.has(wkDow(p))); do n=pkAdd(n,1); while(W.has(wkDow(n)));
  return {iso,day:WKNAME[wkDow(iso)],prev:p,next:n,text:`${wkLong(iso)} is a weekend.`}; }
export function weekendHtml(n,extra=""){ return `<div class="wknote" role="status" aria-live="polite"${extra}>${ic("calendar")}<span>${esc(n.text)}</span><span class="wkb"><button type="button" class="mini" data-wkd="${n.prev}">${esc(wkLong(n.prev))}</button><button type="button" class="mini" data-wkd="${n.next}">${esc(wkLong(n.next))}</button><button type="button" class="mini" data-wkd="keep">Keep this date</button></span></div>`; }
export const WK={ask:null,ok:false};
/* the date fields that are a work item's due date: the table cell, the bulk bar, the Board's prompt, an undated card's date (not a
   milestone's, a reply-by date or a note's date) */
export const wkField=el=>!!el&&(el.dataset.cf==="due"||el.dataset.bf==="due"||el.id==="bdDate"||el.id==="bkDate"||el.dataset.und!=null);
export function wkClear(){ if(WK.ask){ WK.ask.box.remove(); WK.ask=null; } }
/* the alert beside `anchor` (inline after it, or a small layer under it); `apply(iso)` runs with the date chosen. true if it asked */
export function wkAsk(iso,anchor,apply,o={}){ const n=weekendNote(iso); if(!n) return false; wkClear();
  const t=document.createElement("div"); putHTML(t,raw(weekendHtml(n))); const box=t.firstElementChild;
  if(o.inline) (o.after||anchor).insertAdjacentElement("afterend",box);
  else { box.classList.add("cal","wkpop"); (anchor.closest("dialog")||document.body).appendChild(box); const r=anchor.getBoundingClientRect();
    box.style.left=Math.max(8,Math.min(r.left,innerWidth-box.offsetWidth-8))+"px"; box.style.top=(r.bottom+box.offsetHeight+8>innerHeight?Math.max(8,r.top-box.offsetHeight-4):r.bottom+4)+"px"; }
  WK.ask={box,apply,iso,anchor}; if(o.focus!==false) box.querySelector("[data-wkd]").focus(); return true; }
/* the calendars: weekend days marked, in their names too */
export function wkMark(root){ if(!root) return; root.querySelectorAll(".cg button[data-v],.pkday[data-d]").forEach(b=>{ const v=b.dataset.d||(b.dataset.v?toIso(b.dataset.v):""); if(!v||!DATE.test(v)||b.classList.contains("wkend")) return;
  if(wkDays().has(wkDow(v))){ b.classList.add("wkend"); b.setAttribute("aria-label",(b.getAttribute("aria-label")||fd(v))+", weekend"); } }); }
/* BL-316: a work item's date from its control: the Picker block's calendar with BL-181's weekend rule. A due or needed-by date
   (`due`) marks the weekend days, says so as one is typed, and waits for the choice of a working day (wkAsk) before onPick. */
/** @param {HTMLElement} anchor @param {{value?: string, label: string, due?: boolean, onPick: (iso: string) => any, onClose?: (how: string) => any}} o */
export function itemDatePicker(anchor,o){ const gate=!!o.due, op=o.onPick;
  return openDatePicker(anchor,{value:o.value||"",label:o.label,parse:t=>parseWhen(t,TODAY,gate),onClose:o.onClose,
    onPick:gate?v=>{ if(v&&!WK.ok&&wkAsk(v,anchor,op)) return; op(v); }:op,
    weekend:gate?iso=>wkDays().has(wkDow(iso)):undefined,
    typedNote:gate?t=>{ const iso=t?parseWhen(t,TODAY,true):null, n=weekendNote(iso); return n?`${n.text} You'll be offered the nearest working days.`:""; }:undefined}); }
/* ===== end BL-181 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js (piece 0180's place) */
export function bootWeekendNote(){
document.addEventListener("click",e=>{ const b=e.target.closest("[data-wkd]"); if(!b||!WK.ask||!WK.ask.box.contains(b)) return; e.preventDefault(); e.stopPropagation();
  const {apply,iso,anchor}=WK.ask, v=b.dataset.wkd==="keep"?iso:b.dataset.wkd; wkClear(); WK.ok=true; try{ apply(v); } finally{ WK.ok=false; } if(anchor&&anchor.isConnected&&anchor.focus) anchor.focus(); },true);
document.addEventListener("keydown",e=>{ if(e.key==="Escape"&&WK.ask&&WK.ask.box.contains(e.target)){ e.preventDefault(); e.stopPropagation(); const a=WK.ask.anchor; wkClear(); a&&a.isConnected&&a.focus&&a.focus(); } },true);
/* the peek: a due or needed-by date waits for the choice; the typed box says so as it is typed */
/* a decision's Revisit written as a date */
/* the table's date cell, the bulk bar, an undated card and the Board's prompt */
/* typed due dates say so while they are typed (BL-147's line under the field) */
/* Review: a proposal's weekend date, with the two working days, which edit the proposal; approving it unchanged keeps the date */
document.addEventListener("click",async e=>{ const b=e.target.closest("[data-wkrv]"); if(!b) return; e.preventDefault(); e.stopPropagation(); const r=REV.find(x=>String(x.n)===b.dataset.wkrv); if(!r||!WKRVF[r.kind]) return;
  const [ui,db]=WKRVF[r.kind], to=b.dataset.to; if(!await needVault()) return;
  try{ await editProposal(r.file,data=>{ const it=(data.items||[]).find(i=>i.n===r.ref); if(!it||it.applied) throw new Error("that proposal has already been applied"); it.values=it.values||{}; it.values[db]=to; it.edited_in="dashboard"; }); }
  catch(err){ snack("Not saved: "+err.message); return; }
  r.rec[ui]=to; r.edited=true; refreshAll(); snack(`Proposal moved to ${wkLong(to)}: still waiting for review`); },true);
/* the early warning: listed with the others (Settings › Health and warnings › Early warnings), and in the peek with the two days */
WSIG.push(["weekend","Open item due on a weekend",null,null]);
PKDRAW.push((x,k)=>{ if(!shared.CUR||shared.CUR.mode!=="record") return; const w=warnsOf(k,shared.CUR.id).find(z=>z.sig==="weekend"), f=k==="decisions"?"due":"due"; const n=w?weekendNote(x[f]):null; if(!n) return;
  const el=$("#pkWarn"); if(!el||el.querySelector("[data-wkw]")) return;
  addHTML(el,"beforeend",html`<div class="pk-warn" data-wkw="1"><span class="wkb" style="display:flex;gap:6px;flex-wrap:wrap"><button type="button" class="mini" data-wkwto="${n.prev}">Move to ${wkLong(n.prev)}</button><button type="button" class="mini" data-wkwto="${n.next}">Move to ${wkLong(n.next)}</button></span></div>`); });
document.addEventListener("click",e=>{ const b=e.target.closest("[data-wkwto]"); if(!b||!shared.CUR||shared.CUR.mode!=="record") return; const x=REC(shared.CUR.k,shared.CUR.id); if(!x) return;
  pkCommit(shared.CUR.k,shared.CUR.id,{due:b.dataset.wkwto},pkLabel(shared.CUR.k,"due",x),fd(x.due)||"none",fd(b.dataset.wkwto)); });
}

/* BL-231: test seams. A test replaces these through window.openPath and the rest (core/globals.js puts the
   accessors on window); the page itself never replaces them, so they are `let`, not function declarations. */
export const fieldsSeams = { openPath: v => { openPath = v; } };
