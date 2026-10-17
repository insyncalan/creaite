// @ts-check
/* core/page.js (BL-231 step 2b): the data block (`D`), dates and formats, `store`, the settings (`S`), the theme, the motion helpers and the theme button.
   Moved from script/ unchanged, apart from `export`, `shared.` for the shared state (state.js) and the steps that ran at load,
   which are now boot…() functions called by src/main.js in today's order. Pieces: 0005-after-bl-158-js-set-helper-tooltip.js, 0006-settings.js, 0008-after-bl-163-js-the-rail.js, 0009-bl-136-sprint-motion.js, 0121-bl-158-sprint-icons.js */
import { $, addHTML, esc, html, ibtn, ICONS, icTick, putHTML, raw, TIP, tipShow } from "./dom.js";
import { shared } from "./state.js";
export const D=JSON.parse(document.getElementById("data").textContent);
shared.LOADING=true;   /* BL-231: true while the page restores the address it was opened at, or opens Help on a first visit (below). That restore ran before later blocks added their steps to the functions it calls; those steps check LOADING, so it runs as it did. */
/* today is the viewer's date, not the build date */
/* #171: TODAY is a live binding, not a load-time constant: a window left open past midnight rolls it (core/dayroll.js calls setToday()),
   and every reader sees the new day because ES imports read the exported variable itself. Never copy it into a module-level const. */
const dayNow=()=>{ const d=new Date(), z=n=>String(n).padStart(2,"0"); return `${d.getFullYear()}-${z(d.getMonth()+1)}-${z(d.getDate())}`; };
export let TODAY=dayNow();
export const setToday=()=>{ const n=dayNow(); if(n===TODAY) return null; const was=TODAY; TODAY=n; return was; };   /* the old day, or null when the day hasn't changed */
export const DATE=/^\d{4}-\d{2}-\d{2}$/, DDATE=/^\d{2}-\d{2}-\d{4}$/;
/* storage and file names: YYYY-MM-DD. Everything shown or typed: DD-MM-YYYY */
export const fd=iso=>iso&&DATE.test(iso.slice(0,10))?`${iso.slice(8,10)}-${iso.slice(5,7)}-${iso.slice(0,4)}${iso.length>10?iso.slice(10):""}`:(iso||"");
export const toIso=dd=>DDATE.test(dd)?`${dd.slice(6,10)}-${dd.slice(3,5)}-${dd.slice(0,2)}`:dd;
/* The typed-date reader the Notes header uses (and any date field may later): DD-MM-YYYY (also / or .), YYYY-MM-DD, today, yesterday,
   tomorrow, in N days, N days ago, and a weekday: "last monday" (the latest one before today), "next friday" (the first one after
   today), "this friday" (this Monday-to-Sunday week's), or a bare "friday" (as next). Weekdays also by their short names. Returns
   YYYY-MM-DD, or null when it cannot read the text. `today` (YYYY-MM-DD) is the laptop's own date unless a test gives one. */
export function readDate(text,today=TODAY){
  const s=String(text??"").trim().toLowerCase().replace(/\s+/g," "); if(!s) return null;
  const z=n=>String(n).padStart(2,"0"), iso=d=>`${d.getFullYear()}-${z(d.getMonth()+1)}-${z(d.getDate())}`, t0=new Date(today+"T12:00:00");
  const add=n=>{ const d=new Date(t0); d.setDate(d.getDate()+n); return iso(d); };
  const real=(y,m,d)=>{ const x=new Date(y,m-1,d,12); return x.getFullYear()===y&&x.getMonth()===m-1&&x.getDate()===d?iso(x):null; };
  let m=s.match(/^(\d{1,2})[-\/.](\d{1,2})[-\/.](\d{4})$/); if(m) return real(+m[3],+m[2],+m[1]);
  m=s.match(/^(\d{4})-(\d{2})-(\d{2})$/); if(m) return real(+m[1],+m[2],+m[3]);
  if(s==="today") return today; if(s==="yesterday") return add(-1); if(s==="tomorrow") return add(1);
  m=s.match(/^in (\d{1,4}) days?$/); if(m) return add(+m[1]);
  m=s.match(/^(\d{1,4}) days? ago$/); if(m) return add(-m[1]);
  m=s.match(/^(last|next|this )?\s*([a-z]{3,9})$/);
  if(m){ const names=["sunday","monday","tuesday","wednesday","thursday","friday","saturday"], w=names.findIndex(n=>n===m[2]||(m[2].length>=3&&n.startsWith(m[2])));
    if(w<0) return null; const cur=t0.getDay(), how=(m[1]||"").trim();
    if(how==="last") return add(-(((cur-w+7)%7)||7));
    if(how==="this"){ const mon=(cur+6)%7, at=(w+6)%7; return add(at-mon); }
    return add(((w-cur+7)%7)||7); }
  return null; }
export const fdText=s=>String(s??"").replace(/\b(\d{4})-(\d{2})-(\d{2})\b/g,"$3-$2-$1");
/* BL-76: Current state is Markdown. A date inside a link or an image path (images/2026-10-08-plan.png, a web address) is part of
   a name, not a date to show: converting it renamed the image and broke the link, and saving wrote the wrong name back. */
export const fdMd=s=>String(s??"").replace(/(\]\([^)\s]*\))|(\bhttps?:\/\/[^\s)<>]+)|\b(\d{4})-(\d{2})-(\d{2})\b/g,(m,t,u,y,mo,d)=>y?`${d}-${mo}-${y}`:m);
export const MAC=/Mac|iPhone|iPad/.test(navigator.platform||navigator.userAgent), MOD=MAC?"⌘":"Ctrl";
// @ts-expect-error TS2362: a Date minus a Date is the milliseconds between them (valueOf)
export const days=d=>Math.round((new Date(d)-new Date(TODAY))/864e5);
export const rel=d=>{ if(!d) return "No date"; const n=days(d); return n===0?"Today":n===1?"Tomorrow":n===-1?"Yesterday":n<0?`${-n} days late`:`In ${n} days`; };
export const nowStamp=()=>{ const d=new Date(), z=n=>String(n).padStart(2,"0"); return `${TODAY} ${z(d.getHours())}:${z(d.getMinutes())}`; };
/* BL-256: the health icons as element data ([tag, attributes] per shape), so StatusDot draws them with no HTML string;
   HI is the same shapes as markup, for the screens not moved yet. */
/** @type {Record<string, Array<[string, Record<string, string>]>>} */
export const HEALTH_SHAPES={ok:[["circle",{cx:"12",cy:"12",r:"9"}],["path",{d:"m8 12.5 2.8 2.8L16.5 9.5"}]],warn:[["path",{d:"M12 3 2.5 20h19z"}],["path",{d:"M12 10v4M12 17v.5"}]],
  bad:[["circle",{cx:"12",cy:"12",r:"9"}],["path",{d:"M12 7.5v5.5M12 16.2v.4"}]],none:[["circle",{cx:"12",cy:"12",r:"9"}],["path",{d:"M8 12h8"}]]};
export const HI=Object.fromEntries(Object.entries(HEALTH_SHAPES).map(([k,L])=>[k,L.map(([tag,a])=>`<${tag}${Object.entries(a).map(([n,v])=>` ${n}="${v}"`).join("")}/>`).join("")]));
export const hk=h=>h==="On track"?"ok":h==="At risk"?"warn":h==="Off track"?"bad":"none";
export const health=h=>`<span class="health h-${hk(h)}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">${HI[hk(h)]}</svg>${h||"Not set"}</span>`;
/* item-type icons (BL-13): always shown with text, neutral colour */
export const KI={action:'<rect x="4" y="4" width="16" height="16" rx="3"/><path d="m8 12.5 2.8 2.8L16.5 9.5"/>',Risk:'<path d="M12 3 2.5 20h19z"/><path d="M12 10v4M12 17v.5"/>',Issue:'<circle cx="12" cy="12" r="9"/><path d="M12 7.5v5.5M12 16.2v.4"/>',Assumption:'<circle cx="12" cy="12" r="9"/><path d="M9.6 9.4a2.5 2.5 0 1 1 3.4 2.4c-.7.3-1 .9-1 1.6v.4M12 17v.4"/>',Dependency:'<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',decision:'<path d="m13.5 3.5 7 7-3 3-7-7z"/><path d="m11.5 8.5-8 8 4 4 8-8"/>',milestone:'<path d="M5 21V4h11l-2 4 2 4H5"/>'};
export const KL={action:"Action",decision:"Decision",milestone:"Milestone"};
export const kindOf=(t,x)=>t==="actions"?"action":t==="raid"?((x&&x.type)||"Risk"):t==="decisions"?"decision":"milestone";
export const ico=k=>KI[k]?`<span class="ki" title="${KL[k]||k}" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${KI[k]}</svg></span>`:"";
export const revIco=r=>r.kind==="actions"?ico("action"):r.kind==="raid"?ico(r.rec.type||"Risk"):r.kind==="decisions"?ico("decision"):"";
export const store={get:(k,d)=>{ try{ const v=localStorage.getItem(k); return v?JSON.parse(v):d; }catch(e){ return d; } }, set:(k,v)=>{ try{ localStorage.setItem(k,JSON.stringify(v)); }catch(e){} }};
export const CMT="What it is: \nWhat it means for you: \nWhat is being done: ";
export const CMH=["What it is:","What it means for you:","What is being done:"];
export const cmHeads=t=>CMH.every(h=>(t||"").split("\n").some(l=>l.trim().startsWith(h)));
export const cmdOK=t=>(t||"").replace(/[^\p{L}\p{N}]/gu,"").length>=5;
export const cmOK=t=>CMH.every(h=>{ const l=(t||"").split("\n").find(x=>x.trim().startsWith(h)); const r=l&&l.trim().slice(h.length).trim(); return !!r&&r.replace(/[^\p{L}\p{N}]/gu,"").length>=5; });
export const prio=(i,l)=>i==="High"&&l==="High"?"Urgent":(i==="High"||l==="High")?"High":(i==="Low"&&l==="Low")?"Low":"Medium";
export const OPENST=s=>s==="Open"||s==="Delayed";
/* the vault's real path: worked out from where the page is opened (the live server injects it); never stored */
export const VAULT_PATH=D.vault_path||(location.protocol==="file:"?decodeURIComponent(location.pathname).replace(/\/[^/]*$/,""):"~/creaite"), START_CMD=`cd ${VAULT_PATH} && python3 system/scripts/live_server.py`;
export const cmdBox=()=>`<div class="cmdbox"><code>${esc(START_CMD)}</code>${ibtn("copy","Copy the command","data-copycmd","sm")}</div>`;   /* BL-161: the copy icon ticks */
/* BL-231: what this block did at load, run in today's order by src/main.js (piece 0005's place) */
export function bootDevTag(){
if(D.dev){ { const lg=document.querySelector(".rail .logo"); if(lg) addHTML(lg,"beforeend",html`<span class="devtag" title="Development repository: sample data only">DEV</span>`); } document.title="DEV · "+document.title; }
}
/* ======================= settings ======================= */
export const S=Object.assign({me:"Alan Carter",short:"Alan, AC",defPriority:"Medium",defActionView:"open",defRaidView:"open",autoApply:true,theme:"System",palette:"creaite",remindersOn:true,weeklyDay:"Friday",weeklyTime:"12:00",sweepDue:"07:00",catchupSweep:"start",catchupAfter:30,lookback:14,srcInbox:true,srcSent:true,srcChats:true,srcChannels:true,srcCalendar:true,possible:true,staleDays:7,overdueDays:7,slipAtRisk:2,slipOff:2,urgentOff:2,dueSoon:7,dailyBackup:true,port:8765},D.settings);
export const saveS=()=>{};   /* settings are written to settings.json by writeSettings() */
export const meNames=()=>[S.me,...S.short.split(",").map(x=>x.trim()).filter(Boolean)].map(x=>x.toLowerCase());
export const isMe=o=>meNames().includes((o||"").toLowerCase());
export const who=o=>isMe(o)?"You":o;
/* named themes (BL-39): id as stored in settings.json; swatch = background, surface, accent, accent soft (Linear's swatch is its dark set, the design's own; Cursor's is its light set) */
export const THEMES=[{id:"Brightwater",swatch:["#F8F8FF","#1E1F1E","#91FF01","#AE74FF"]},{id:"creaite",swatch:["#F3F6F7","#FFFFFF","#0B6E7F","#DCEFF2"]},{id:"Notion",swatch:["#F6F5F4","#FFFFFF","#0075DE","#E6F1FB"]},{id:"Linear",swatch:["#010102","#0F1011","#5E6AD2","#171A3A"]},{id:"Cursor",swatch:["#F7F7F4","#FFFFFF","#F54E00","#FDEDE4"]},{id:"Claude",swatch:["#FAF9F5","#FFFFFF","#CC785C","#F8ECE5"]},{id:"Apple",swatch:["#F5F5F7","#FFFFFF","#0066CC","#E8F1FB"]},{id:"Retro Arcade",swatch:["#000000","#0B0B1E","#0000FF","#FFFF00"]},{id:"Thermo Scan",swatch:["#050B26","#0B1435","#FFC800","#FF0000"]}];
/* BL-142: the three retired names, and any name this page doesn't know, open as creaite (a saved value from settings.json or an older copy) */
export const THEME_OLD={"creaite standard":"creaite","Minimals":"creaite","creaite teal":"creaite"};
export const themeOf=id=>THEMES.find(t=>t.id===(THEME_OLD[id]||id))||THEMES.find(t=>t.id==="creaite");
export function applyTheme(){ const r=document.documentElement; if(S.theme==="System") delete r.dataset.theme; else r.dataset.theme=S.theme.toLowerCase();
  r.dataset.palette=themeOf(S.palette).id; appTint(); themeIcon(); }
/* BL-86: the installed app's title bar takes the page's own background, in every palette and mode */
export function appTint(){ const m=document.querySelector('meta[name="theme-color"]'); if(!m) return; const c=getComputedStyle(document.documentElement).getPropertyValue("--bg").trim(); if(c) m.setAttribute("content",c); }
/* BL-231: what this block did at load, run in today's order by src/main.js (piece 0008's place) */
export function bootTheme(){
matchMedia("(prefers-color-scheme: dark)").addEventListener?.("change",()=>setTimeout(appTint,0));
applyTheme();
}
/* ===== BL-136 (sprint-motion) ===== motion helpers. Every scripted effect goes through anim(), so reduced motion is honoured in one
   place: reduced() is true when Settings › Appearance › Motion is Reduce, or it is Follow system and the system asks for reduced
   motion (Full overrides the system for creaite's own motion only). Effects never hold state: remove this block's callers and the
   dashboard works exactly as before, and nothing waits for an animation to end. */
export const MQ_REDUCE=matchMedia("(prefers-reduced-motion: reduce)");
export function applyMotion(){ const r=document.documentElement, m=S.motion||"System";
  if(m==="Reduce") r.dataset.motion="reduce"; else if(m==="Full") r.dataset.motion="full"; else delete r.dataset.motion; reduced(); }
/* read live (a media change event can come late), and keep data-reduced, which a few CSS rules read, in step */
export function reduced(){ const m=S.motion||"System", on=m==="Reduce"||(m!=="Full"&&MQ_REDUCE.matches), r=document.documentElement;
  if(on!==r.hasAttribute("data-reduced")){ if(on) r.dataset.reduced="1"; else delete r.dataset.reduced; } return on; }
 
export const mK=()=>parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--k"))||1;
export const EASE={out:"cubic-bezier(.2,.7,.2,1)",inout:"cubic-bezier(.65,0,.35,1)",in:"cubic-bezier(.4,0,1,1)"};
export function anim(el,kf,o={}){ if(!el||!el.animate) return null; const r=reduced();
  try{ return el.animate(kf,{duration:r?1:(o.duration||200)*mK(),easing:EASE[o.easing]||o.easing||EASE.out,fill:o.fill||"backwards",delay:r?0:(o.delay||0)*mK(),...(o.pseudo?{pseudoElement:o.pseudo}:{})}); }catch(e){ return null; } }
/* a number counts up to its final value; the final value is the element's accessible name from the first frame */
export function countUp(el,to,ms=700,dec=0,suf=""){ const fmt=v=>v.toLocaleString("en-GB",{minimumFractionDigits:dec,maximumFractionDigits:dec})+suf;
  el.setAttribute("aria-label",fmt(to)); if(reduced()){ el.textContent=fmt(to); return; }
  const t0=performance.now(), d=ms*mK(); (function f(t){ const p=Math.min(1,(t-t0)/d); el.textContent=fmt(to*(1-Math.pow(1-p,3))); if(p<1) requestAnimationFrame(f); })(t0); }
/* FLIP: measure, change, then glide each element from where it was (transform only) */
export function flip(els,mutate,ms=320){ if(reduced()){ mutate(); return; } const first=new Map(els.map(e=>[e,e.getBoundingClientRect()])); mutate();
  els.forEach(e=>{ if(!e.isConnected) return; const l=e.getBoundingClientRect(), f=first.get(e), dx=f.left-l.left, dy=f.top-l.top;
    if(dx||dy) anim(e,[{transform:`translate(${dx}px,${dy}px)`},{transform:"none"}],{duration:ms,easing:"inout"}); }); }
/* an element arriving: fades and unclips downwards (no height animation) */
export function slideDown(el){ return anim(el,[{opacity:0,transform:"translateY(-4px)",clipPath:"inset(0 0 100% 0)"},{opacity:1,transform:"none",clipPath:"inset(0 0 0 0)"}],{duration:240}); }
/* a script's smooth scroll ignores the CSS rule, so every one goes through here: instant when reduced */
export function mScroll(el,opts={}){ if(el) el.scrollIntoView({...opts,behavior:reduced()?"instant":"smooth"}); }
/* 37: a theme or mode change made by Alan (Settings, the moon button, Cmd+K) cross-fades for about 300ms; never on load,
   and not when code calls applyTheme() itself */
// @ts-expect-error TS2339: the pending timer is kept on the function itself (themeFade.t)
export function themeFade(){ if(reduced()) return; const r=document.documentElement; r.classList.add("themefade"); clearTimeout(themeFade.t);
  // @ts-expect-error TS2339: the pending timer is kept on the function itself (themeFade.t)
  themeFade.t=setTimeout(()=>r.classList.remove("themefade"),300*mK()); }
/* 35 and 6: the drawn tick; a copy's confirmation (the label swaps to the tick and "Copied" for 1.4s, said by a polite live region) */
export const MTICK='<svg class="mtk" viewBox="0 0 14 14" aria-hidden="true"><path d="M2.5 7.5l3 3 6-7"/></svg>';
export function mSay(t){ let l=document.getElementById("mlive"); if(!l){ l=document.createElement("div"); l.id="mlive"; l.setAttribute("role","status"); l.setAttribute("aria-live","polite"); document.body.appendChild(l); }
  // @ts-expect-error TS2339: the pending timer is kept on the function itself (mSay.t)
  l.textContent=""; setTimeout(()=>{ l.textContent=t; },30); clearTimeout(mSay.t); mSay.t=setTimeout(()=>{ l.textContent=""; },3000); }
export function copied(btn,label="Copied"){ mSay(label); if(!btn||!btn.isConnected) return; if(btn.classList.contains("ib")){ icTick(btn); return; }   /* BL-161 */ if(!btn.classList.contains("mcopied")) btn.dataset.mwas=btn.innerHTML;
  btn.classList.add("mcopied"); putHTML(btn,raw(MTICK+esc(label))); clearTimeout(btn._mt);
  btn._mt=setTimeout(()=>{ if(btn.isConnected&&btn.classList.contains("mcopied")){ putHTML(btn,btn.dataset.mwas); btn.classList.remove("mcopied"); delete btn.dataset.mwas; } },1400); }
/* ===== end BL-136 helpers ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js (piece 0009's place) */
export function bootMotion(){
MQ_REDUCE.addEventListener?.("change",applyMotion);
applyMotion();
}
/* ===== BL-158 (sprint-icons) ===== the theme button shows where it will go: the sun in the dark theme, the moon in the light,
   with a tooltip that says so; it follows applyTheme and the system's own change */
export function isDark(){ const r=document.documentElement; return r.dataset.theme?r.dataset.theme==="dark":matchMedia("(prefers-color-scheme: dark)").matches; }
export function themeIcon(){ const b=$("#themeBtn"); if(!b) return; const d=isDark(), w=d?"Switch to light theme":"Switch to dark theme"; const s=b.querySelector("svg");
  if(s&&s.dataset.ic!==(d?"sun":"moon")){ s.dataset.ic=d?"sun":"moon"; putHTML(s,raw(ICONS[s.dataset.ic])); s.dataset.icn=s.dataset.ic; }
  b.setAttribute("aria-label",w); b.dataset.tip=w; if(TIP.el===b) tipShow(b,0); }
 
/* ===== end BL-158 (theme) ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js (piece 0121's place) */
export function bootThemeButton(){
matchMedia("(prefers-color-scheme: dark)").addEventListener("change",themeIcon);
themeIcon();
}
