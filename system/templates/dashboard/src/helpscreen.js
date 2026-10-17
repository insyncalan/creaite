// @ts-check
/* helpscreen.js (#158 Help Phase B): Help on the page you are on, without a button. The ? key opens a panel on the right with
   the two to five jobs for the screen (the `Screen:` lines of help.md, built into D.help.screens); a quiet foot line says
   "Press ? for help with <screen>" on the eight screens; a first-visit line says it once per screen, under the title;
   an empty state links to "How <screen> works". The panel and ask creaite are never open together. Nothing here is a
   setting except the first-visit line (help.first_line, Settings › Essentials › Look and help). */
import { closeChat } from "./ask.js";
import { $, $$, esc, putHTML, raw } from "./core/dom.js";
import { go } from "./core/nav.js";
import { S } from "./core/page.js";
import { shared } from "./core/state.js";
import { HD, helpFocusSearch } from "./help.js";

/** The screen a view belongs to (a project's page is Projects, a person's page is People). */
export const SCREEN_OF={today:"today",work:"work",mine:"work",review:"review",projects:"projects",cockpit:"projects",people:"people",person:"people",notes:"notes",inbox:"intake",files:"files"};
/** The eight pages that carry the foot line and the first-visit line (the page itself, not a project's or a person's page). */
const LINE_OF={today:"today",work:"work",mine:"work",review:"review",projects:"projects",people:"people",notes:"notes",inbox:"intake",files:"files"};
const TITLE={today:"#dayHead",work:"#v-work h1",review:"#v-review h1",projects:"#v-projects .hhead",people:"#v-people h1",notes:"#v-notes h1",intake:"#v-inbox h1",files:"#v-files h1"};
const FOOT={today:"#v-today",work:"#v-work .wrapmax",review:"#v-review .wrapmax",projects:"#v-projects .wrapmax",people:"#v-people .wrapmax",notes:"#v-notes",intake:"#v-inbox .wrapmax",files:"#v-files .wrapmax"};

export const screenKey=()=>SCREEN_OF[shared.VIEW]||"";
export const screenInfo=(/** @type {string} */ k)=>HD.screens[k]||null;
export function howLink(/** @type {string} */ k){ const s=screenInfo(k); return s?`<a class="hhow" href="#help-reference-${esc(s.ref)}" data-hhow="${esc(k)}">How ${esc(s.title)} works</a>`:""; }

/* ----- the panel ----- */
let FROM=null;
export const helpPanelOpen=()=>!!$("#helpPanel")&&$("#helpPanel").classList.contains("on");
export function openHelpPanel(/** @type {string} */ key){ const sc=screenInfo(key); if(!sc||!sc.ids.length) return false;
  const from=document.activeElement, p=$("#helpPanel"); closeChat();
  const task=id=>HD.tasks.find(t=>t.id===id), ref=HD.sections.find(x=>x.id===sc.ref);
  putHTML(p,raw(`<div class="hpn-h"><h2 id="hpnT">Help · ${esc(sc.title)}</h2><button type="button" class="iconbtn" id="hpnX" aria-label="Close Help">×</button></div>
    <p class="sub">Esc closes it and you are back where you were.</p>
    <ul class="hpn-jobs">${sc.ids.map(id=>task(id)).filter(Boolean).map(t=>`<li><a href="#help-howto-${esc(t.id)}" data-hpn="howto-${esc(t.id)}"><b>${esc(t.title)}</b>${t.where?`<span>${esc(t.where)}</span>`:""}</a></li>`).join("")}</ul>
    <div class="hpn-f">${ref?`<a href="#help-reference-${esc(ref.id)}" data-hpn="reference-${esc(ref.id)}">How ${esc(sc.title)} works</a>`:""}<button type="button" class="linkbtn" id="hpnFind">Search all of Help</button></div>`));
  p.setAttribute("aria-labelledby","hpnT"); p.classList.add("on");
  FROM=from&&from!==document.body&&!p.contains(from)?from:null;
  firstLineClear(); p.focus(); return true; }
export function closeHelpPanel(/** @type {boolean=} */ noReturn){ const p=$("#helpPanel"); if(!p||!p.classList.contains("on")) return;
  p.classList.remove("on"); const t=FROM; FROM=null;
  if(p.contains(document.activeElement)) /** @type {HTMLElement} */ (document.activeElement).blur();
  if(!noReturn&&t&&t.isConnected) /** @type {HTMLElement} */ (t).focus(); }

/* ----- the first-visit line and the foot line ----- */
const MEM=new Set();
const lkey=(/** @type {string} */ k)=>"creaite-help-line-"+k;
export function lineSeen(/** @type {string} */ k){ if(MEM.has(k)) return true; try{ return localStorage.getItem(lkey(k))==="1"; }catch(e){ return false; } }
function lineMark(/** @type {string} */ k){ MEM.add(k); try{ localStorage.setItem(lkey(k),"1"); }catch(e){ /* once per page load */ } }
const blocked=()=>!!($("#panel")?.classList.contains("on")||document.querySelector("dialog[open]")||$("#chat")?.classList.contains("on")||helpPanelOpen()
  ||$("#capDrawer")?.classList.contains("on")||(()=>{ const a=document.activeElement; return !!a&&(/^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName)||/** @type {HTMLElement} */ (a).isContentEditable); })());
function node(/** @type {string} */ id,/** @type {string} */ cls){ let n=$("#"+id); if(!n){ n=document.createElement("p"); n.id=id; n.className=cls; n.hidden=true; document.body.append(n); } return n; }
const kbd='<kbd>?</kbd>';
/** Put the foot line and (when due) the first-visit line where the current screen has them. Cheap; safe to call often. */
export function helpScreenSync(){ const line=node("hFirst","hfirst"), foot=node("hFoot","hfoot"), key=shared.VIEW?LINE_OF[shared.VIEW]:"";
  const sc=key?screenInfo(key):null;
  if(!sc){ line.hidden=true; foot.hidden=true; return; }
  const host=$(FOOT[key]); if(host){ if(host.lastElementChild!==foot) host.append(foot); }
  if(foot.dataset.k!==key){ foot.dataset.k=key; putHTML(foot,raw(`Press ${kbd} for help with ${esc(sc.title)}`)); }
  foot.hidden=!host;
  const title=$(TITLE[key]);
  const due=S.helpLine!==false&&!lineSeen(key)&&!!title&&!blocked();
  if(!due){ if(!line.hidden) line.hidden=true; return; }
  if(title.nextElementSibling!==line) title.after(line);
  if(line.dataset.k!==key){ line.dataset.k=key; putHTML(line,raw(`Press ${kbd} for help with ${esc(sc.title)}`)); }
  line.hidden=false; }
/** Any key or click clears the line and is not touched: it still does its normal job. */
export function firstLineClear(){ const line=$("#hFirst"); if(!line||line.hidden) return; const k=line.dataset.k; line.hidden=true; if(k) lineMark(k); }

/** BL-231: run once by src/main.js. */
export function bootHelpScreen(){
node("hFirst","hfirst"); node("hFoot","hfoot");
document.addEventListener("keydown",e=>{ if(["Shift","Control","Alt","Meta","CapsLock"].includes(e.key)) return; firstLineClear(); },true);
document.addEventListener("pointerdown",()=>firstLineClear(),true);
document.addEventListener("click",e=>{ const t=/** @type {HTMLElement} */ (e.target);
  const a=t.closest("[data-hpn]"); if(a){ e.preventDefault(); closeHelpPanel(true); go("help",/** @type {HTMLElement} */ (a).dataset.hpn); return; }
  if(t.closest("#hpnX")){ closeHelpPanel(); return; }
  if(t.closest("#hpnFind")){ closeHelpPanel(true); go("help"); helpFocusSearch(); return; }
  const h=t.closest("[data-hhow]"); if(h){ e.preventDefault(); const s=screenInfo(/** @type {HTMLElement} */ (h).dataset.hhow||""); if(s) go("help","reference-"+s.ref); } });
window.setInterval(helpScreenSync,300);
}
