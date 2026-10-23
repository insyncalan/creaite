// @ts-check
/* today.js (BL-231 step 2b), moved from script/ by dev/tools/convert_area.py: 0025-today.js, 0026-today-brief-bl-72.js, 0027-bl-149-sprint-ux.js, 0028-after-bl-149.js, 0159-bl-156-sprint-ux.js, 0164-bl-166-sprint-polish-2.js.
   Unchanged apart from `export`, `shared.` for the shared state (core/state.js) and the load-time steps, now in
   boot…() functions that src/main.js calls in today's order. */
import { dcIcon, openChat, say, send } from "./ask.js";
import { linkWords as lw } from "./core/linkText.js";
import { closeMenu, menuOpenFor, openMenu } from "./components/Menu.jsx";
import { openDatePicker } from "./components/Picker.jsx";
import { parseWhen, weekendNote, WK, wkAsk, wkDays } from "./core/fields.js";
import { mountStatusDots } from "./components/StatusDot.jsx";
import { mountFirstThing } from "./components/closeday/FirstThing.jsx";
import { drawDayCurve } from "./components/today/DayCurve.jsx";
import { drawDayMeetings } from "./components/today/DayMeetings.jsx";
import { drawDayTabs } from "./components/today/DayTabs.jsx";
import { drawIntakeLine } from "./components/today/IntakeLine.jsx";
import { drawToDecide } from "./components/today/ToDecide.jsx";
import { drawWeekAhead } from "./components/today/WeekAhead.jsx";
import { A, LASTVISIT, open, overdue, P, pName, R, REMINDERS, REV, soon } from "./core/data.js";
import { $, $$, addHTML, esc, html, ic, putHTML, raw, swapHTML } from "./core/dom.js";
import { canHover, cardGroup } from "./core/hover.js";
import { mDots } from "./core/motion.js";
import { countLink, go, jumpLink, navBlocked, navOf, openWork } from "./core/nav.js";
import { anim, copied, D, DATE, days, fd, fdText, health, isMe, reduced, rel, S, slideDown, store, TODAY, VAULT_PATH, who } from "./core/page.js";
import { linkAnchor } from "./core/linkUrl.js";
import { api, oneLine, onceFor, snack, viaServer, writeSettings, z2 } from "./core/server.js";
import { shared } from "./core/state.js";
import { selDay } from "./stores/today.js";
import { irFreshFiles, irReveal } from "./stores/intakeReview.js";   /* #232-C */
import { openMilestone } from "./milestones.js";
import { draftBtn } from "./drafts.js";
import { checkMeeting, MTG } from "./core/intakeApi.js";
import { irProcessById, irRefreshCalendar } from "./components/intakeReview/actions.js";   /* #232-C2: Today's day line and Refresh calendar go through the Intake page's own actions */
import { decAsked, decLate, decLateWords, decPending, decRank, decShort, dnChase, dnDecide, dnList, prepOpen, prepPageOf, renderDn } from "./meetings.js";
import { decorateWarnings, prepKey, prepOf, undatedWork, WARNS } from "./projects.js";
import { chaseCan, chaseOpen, openRecord, pkCommit, pkUndoLast, REC } from "./panel.js";
import { draftOn } from "./review.js";
import { asQuestionHtml } from "./autostart.js";
import { profileQuestionHtml } from "./profile.js";   /* #312 */
import { nm, row, SA, SETSECTIONS, VIPKIND, VIPQ, VIPR, VIPS, vipWhen } from "./settings.js";
import { applyFilters, applyView, clearAllFilters, colResizer, isStale, items, syncView } from "./work.js";
/* ======================= Today ======================= */
export const dismissedF=()=>store.list("creaite-dismiss"), dismissedS=()=>{ try{ return JSON.parse(sessionStorage.getItem("creaite-dismiss-s")||"[]"); }catch(e){ return []; } };
/* ===== Today brief (BL-72) ===== */
/* Today reads as a brief: numbered sentences with a bold linked title and links inside the sentence, worded from
   templates here (no model call). The data for the Week ahead comes from build_dashboard.py (D.week). */
export const EXPAND=new Set();
export const tl=(n,title,body,end,attrs)=>`<li ${attrs||""}><span class="n">${n}</span><div class="tb">${title}${body?`<p>${body}</p>`:""}</div>${end||""}</li>`;
export const tLink=(attrs,text)=>`<a class="t" href="#" ${attrs}>${text}</a>`, sLink=(attrs,text)=>`<a class="s" href="#" ${attrs}>${text}</a>`;
export const projLink=code=>code?sLink(`data-cock="${code}"`,esc(pName(code))):"";
export const andList=a=>a.length<2?a.join(""):`${a.slice(0,-1).join(", ")} and ${a[a.length-1]}`;
export const plur=(n,w)=>`${n} ${w}${n===1?"":"s"}`;
/* the first `cap` items show; the rest are hidden until "+n more" is pressed */
export function capped(items,cap,key){ const open=EXPAND.has(key), n=items.length-cap;
  return {html:items.map((h,i)=>i<cap?h:h.replace(/^<(\w+)/,`<$1 data-x="${key}"${open?"":" hidden"}`)).join(""),
          more:n>0?`<button class="qa" data-more="${key}" aria-expanded="${open}">${open?"Show fewer":`+${n} more`}</button>`:""}; }
/* Review items are grouped by the meeting or sweep they came from: the proposal file */
export function revGroupTitle(file,items){ const w=file.match(/^proposed-(\d{4}-\d{2}-\d{2})-(\d{2})(\d{2})/), when=w?`${longDay(w[1])}, ${w[2]}:${w[3]}`:esc(file), d=items.find(r=>r.kind==="draft");
  if(d){ const nm=esc(d.rec.t.replace(/^[^:]*:\s*/,"")); return d.ref==="meeting"?`Review the ${nm} minutes`:`Review the ${esc(d.rec.t.split(":")[0].toLowerCase())}: ${nm}`; }
  if(/-sweep(-\d+)?\.json$/.test(file)) return `Review the mail and Teams check of ${when}`;
  if(/-(dashboard|edit)(-\d+)?\.json$/.test(file)) return "Review your pending edits";
  if(/-excel(-\d+)?\.json$/.test(file)) return "Review the Excel import";
  return `Review the suggestions from ${when}`; }
export function attentionItems(){ const out=/** @type {any[]} */([]);   /* BL-319 (Alan, 14-10-2026): proposals are To decide's alone, so Needs attention has no per-meeting groups (nor their Approve n routine).
  #236 (Alan, 19-10-2026): the proposals and memory notes the sweep takes from a followed person's messages, and a private conversation, are Needs attention rows
  (From <name>, never labelled: BL-288; Review still holds the proposals). The conversation cards (BL-334, BL-342) stay in To decide. */
  if(S.remindersOn){ const hide=[...dismissedF(),...dismissedS()];
    REMINDERS.filter(r=>!hide.includes(r.id)).forEach(r=>out.push({reminder:r.id,html:n=>tl(n,
      tLink(r.id.startsWith("client:")?`data-rphub="${r.id.split(":")[1]}||client"`:r.id.startsWith("revisit:")?`data-open="decisions:${r.id.split(":")[1]}"`:r.id.startsWith("weekly:")?(r.id.split(":")[2]?`data-rphub="${r.id.split(":")[2]}|${r.id.split(":")[1]}"`:'data-go="reports"'):'data-go="projects"',esc(longText(r.text))),
      `${remBody(r)}${RUNNING.has(r.id)?' <span class="tag">Running…</span>':""}${r.vip?` ${r.vip} message${r.vip===1?"":"s"} about it not yet seen: check ${r.vip===1?"it":"them"} first.`:""}`,
      `${remBtn(r)}<span class="rm"><button class="dots" type="button" aria-label="Options: ${esc(r.text)}" aria-haspopup="menu" aria-expanded="false">…</button></span>`,
      `class="rem" data-id="${r.id}"`)})); }
  /* Work with no owner (TBC) or, for actions, no due date: one line, counted per project, each count opening Work filtered to it */
  const gap={}; [...A.filter(x=>x.st==="Open"||x.st==="Delayed").map(x=>["actions",x]),...R.filter(r=>r.st==="Open").map(r=>["raid",r])].forEach(([k,x])=>{
    const g=gap[x.p||""]||(gap[x.p||""]={actions:0,raid:0,due:0}); if(!x.o||x.o==="TBC") g[k]++; if(k==="actions"&&!x.due) g.due++; });
  const gl=Object.entries(gap).filter(([,g])=>g.actions||g.raid||g.due).sort(([a],[b])=>pName(a).localeCompare(pName(b)));
  if(gl.length){ const tot=gl.reduce((n,[,g])=>n+g.actions+g.raid+g.due,0), cnt=(p,k,n,one,many)=>n?sLink(`data-gap="${p}|${k}"`,`${n} ${n===1?one:many}`):"";
    out.push({gaps:true,html:n=>tl(n,tLink('data-gap="|actions"',`${tot} work item${tot===1?" is":"s are"} missing an owner or a due date`),
      gl.map(([p,g])=>{ const own=[cnt(p,"actions",g.actions,"action","actions"),cnt(p,"raid",g.raid,"risk or issue","risks and issues")].filter(Boolean),
        parts=[own.length?`${andList(own)} with no owner`:"",g.due?`${cnt(p,"due",g.due,"action","actions")} with no due date`:""].filter(Boolean);
        return `${p?projLink(p):"No project"}: ${parts.join("; ")}`; }).join(". ")+".")}); }
  { const L=decPending().sort(decRank); if(L.length){   /* #313: a decision under Decisions needed is counted here, never named again */
    const mine=L.filter(d=>isMe(d.by)).length, others=L.length-mine, late=L.filter(decLate).length, parts=[], dnIds=new Set(dnList().map(d=>d.id)), rest=L.filter(d=>!dnIds.has(d.id)), above=L.length-rest.length;
    if(others) parts.push(`${plur(others,"decision")} waiting on others`); if(mine) parts.push(others?`${mine} for you`:`${plur(mine,"decision")} for you`);
    const show=rest.slice(0,3).map(d=>`${sLink(`data-open="decisions:${d.id}"`,esc(decShort(d.t,70)))} (${decAsked(d)}${d.due?`, ${decLate(d)?`<span class="late">${decLateWords(d)}</span>`:`by ${fd(d.due).slice(0,5)}`}`:""})`);
    const body=[show.length?`${andList(show)}${rest.length>3?` and ${rest.length-3} more`:""}.`:"",above?(above===L.length?"All of them are listed under Decisions needed.":`${above===1?"1 is":`${above} are`} listed under Decisions needed.`):""].filter(Boolean).join(" ");
    out.unshift({decisions:true,html:n=>tl(n,tLink('data-decpending="1"',parts.join(", ")+(late?`, ${late} late`:"")),body)}); } }
  out.unshift(...msAttention().map(r=>({milestone:r.ms,html:n=>msAttnRow(n,r)})));   /* #251: time-critical, so first, soonest first */
  out.push(...attnAlertItems());   /* #236: after the decisions, the reminders and the gaps line, as the help says (Stark's review: they led the list) */
  return out; }
/* ===== #313 (2.6.1): no item is shown twice on Today. The one-row rule, in one place so it cannot drift =====
   An item is a row in ONE section; every other section counts it or links to it, never lists it again. The order, most urgent
   first: Decisions needed (a pending decision with a decision maker and a needed-by date), Your commitments (Alan's own actions
   due or overdue), Needs attention (a milestone row names the other open items on it, a decisions line names the pending decisions
   that have no decision maker or date), then the Week ahead, which leaves out whatever is already listed above and says how many.
   You owe and Waiting on are promises, with their own IDs. A decision's "If it stays open" line and a Messages card's matched-item
   chip name an ID as context, not as a row. dev/tests/test_today_once.py fails when any two sections list the same ID. */
const todayMineIds=()=>new Set(A.filter(x=>isMe(x.o)&&(overdue(x)||soon(x))).map(x=>x.id));
/** the IDs already listed above the Week ahead, by section @returns {{dn:Set<string>,mine:Set<string>,attn:Set<string>,above:Set<string>}} */
export function todayClaims(){ const dn=new Set(dnList().map(d=>d.id)), mine=todayMineIds(), attn=new Set();
  msAttention().forEach(r=>{ attn.add(r.ms); r.named.slice(0,3).forEach(x=>attn.add(x.id)); });
  decPending().filter(d=>!dn.has(d.id)).sort(decRank).slice(0,3).forEach(d=>attn.add(d.id));
  return {dn,mine,attn,above:new Set([...dn,...mine,...attn])}; }
/* #251 (Alan, 19-10 and 20-10-2026): one Needs attention row per milestone not yet achieved (or dropped) that is due within the
   Due soon window (review.due_soon_days), or already past due, by its forecast date when it has one, else its agreed date, and
   has open work attached that must close for it to hold: open (or delayed) actions and open issues. Risks are left out (a
   risk can stay open and the milestone still lands); decisions have no milestone. No date, no row; nothing attached, no row.
   No dismiss: it goes by itself when the work closes or the milestone is achieved. Built from the page's own data. */
const msLate=x=>!!x.due&&days(x.due)<0;
export function msAttention(){ const out=[];
  for(const p of P) for(const m of p.ms||[]){ const id=m[3], when=m[8]||m[4]; if(!id||!when||m[6]!=="Planned"||days(when)>S.dueSoon) continue;
    const its=[...A.filter(a=>a.ms===id&&open(a)),...R.filter(r=>r.ms===id&&r.type==="Issue"&&r.st==="Open")];
    if(!its.length) continue;
    // @ts-expect-error TS2362: true and false subtract as 1 and 0 (late items first)
    its.sort((a,b)=>(msLate(b)-msLate(a))||(a.due||"9").localeCompare(b.due||"9")||a.id.localeCompare(b.id));
    const mineIds=todayMineIds(), named=its.filter(x=>!mineIds.has(x.id));   /* #313: Alan's own are rows under Your commitments, counted here */
    out.push({ms:id,p:p.code,name:m[0],when,its,named,inMine:its.length-named.length}); }
  return out.sort((a,b)=>a.when.localeCompare(b.when)||pName(a.p).localeCompare(pName(b.p))||a.name.localeCompare(b.name)); }
/* one attached item: "DEF-A-003 Confirm licence count, 1 day late" (red), "…, due Thursday", "…, no due date, no owner" */
export function msItemWords(x){ const n=x.due?days(x.due):null, t=`${esc(x.id)} ${esc(decShort(x.t||"",70))}`, own=!x.o||x.o==="TBC"?", no owner":"";
  if(n!==null&&n<0) return `<span class="late">${t}, ${-n} day${n===-1?"":"s"} late</span>${own}`;
  const due=n===null?"no due date":n===0?"due today":n===1?"due tomorrow":n<7?`due ${longDay(x.due).split(" ")[0]}`:`due ${longDay(x.due)}`;
  return `${t}, ${due}${own}`; }
/* "Open all n in Work": All items, the project, open actions and issues, on the milestone (the Milestone filter), so Work
   lists exactly the items counted */
export function msAttnOpenWork(id){ const r=msAttention().find(x=>x.ms===id); if(!r) return;
  openWork(r.p,"all","open",{st:["Open"],ty:["Action","Issue"],mi:[r.ms]}); }
/* #310 (Alan, 22-10-2026): the Week ahead's milestone row says how many open work items it depends on: the open actions (Open or
   Delayed, as Work's open filter has it) and open RAID items attached to it, never an archived one; decisions carry no milestone.
   It is exactly the list Work shows for the Milestone filter with open items only. */
export function msOpenItems(id){ const its=[...A.filter(a=>a.ms===id&&open(a)&&!a.ar),...R.filter(r=>r.ms===id&&r.st==="Open"&&!r.ar)];
  return {n:its.length,over:its.filter(x=>!!x.due&&x.due<TODAY).length}; }
export function msItemsOpenWork(id,code){ openWork(code,"all","open",{st:["Open"],mi:[id]}); }
export const msAttnWorkWord=r=>r.its.length===1?"Open in Work":`Open all ${r.its.length} in Work`;
/* #310 + #313 (2.6.1): a milestone is ONE row on Today, in Needs attention if it qualifies there, else in the Week ahead, and the
   open-items count button is on whichever row it has. One source for its words, so the two rows say the same thing. */
export function msCountWords(id,name){ const c=msOpenItems(id); if(!c.n) return undefined; const w=`${c.n} open work item${c.n===1?"":"s"}`;
  return {n:c.n,over:c.over,label:c.over?`${c.n} open`:`${c.n} open item${c.n===1?"":"s"}`,overLabel:c.over?`, ${c.over} overdue`:"",
    tip:`${w} this milestone depends on`,aria:`Milestone ${name}: ${w}${c.over?`, ${c.over} overdue`:""}. Open the list`}; }
export function msAttnRow(n,r){ const k=days(r.when), items="its open work must close";
  const when=k<0?`is overdue by ${-k} day${k===-1?"":"s"} (due ${longDay(r.when)}): ${items} before it can be achieved`
    :`is due ${k===0?"today":k===1?"tomorrow":longDay(r.when)}: ${items} for it to hold`;
  const shown=r.named.slice(0,3).map(msItemWords), more=r.named.length>3?[`and ${r.named.length-3} more`]:[], mineWords=r.inMine?[`${r.inMine===1?"1 is":`${r.inMine} are`} under Your commitments`]:[];
  const cw=msCountWords(r.ms,r.name), cnt=cw?`<button type="button" class="wkcnt" data-wkitems="${esc(r.ms)}" data-p="${esc(r.p)}" aria-label="${esc(cw.aria)}" data-tip="${esc(cw.tip)}">${esc(cw.label)}${cw.overLabel?`<span class="warn">${esc(cw.overLabel)}</span>`:""}</button>`:"";
  return tl(n,tLink(html`data-ms="${r.ms}"`,html`Milestone <u>${r.name}</u> ${raw(when)}`),
    [...shown,...more,...mineWords,projLink(r.p),cnt].filter(Boolean).join(" · "),
    `<span class="rm"><button class="dots" type="button" aria-label="Options: milestone ${esc(r.name)}" aria-haspopup="menu" aria-expanded="false">…</button></span>`,
    html`data-msattn="${r.ms}"`); }
export function msAttnMenu(b,id){ if(menuOpenFor(b)){ closeMenu(); return; } const r=msAttention().find(x=>x.ms===id); if(!r) return;
  openMenu(b,{label:`Options: milestone ${r.name}`,id:"msAttnMenu",align:"right",onPick:d=>{ closeMenu();
      if(d==="ms") openMilestone(r.ms); else if(d==="work") msAttnOpenWork(r.ms); else go("cockpit",r.p); },
    items:[{id:"ms",name:"Open the milestone",data:{d:"ms"}},{id:"work",name:msAttnWorkWord(r).replace(/^Open in Work$/,"Open it in Work"),data:{d:"work"}},{id:"proj",name:`Open ${pName(r.p)}`,data:{d:"proj"}}]}); }
export const dueWords=d=>{ const n=days(d); return n<0?`<span class="late">${-n} day${n===-1?"":"s"} late</span>`:n===0?"due today":n===1?"due tomorrow":`due in ${n} days`; };
/* "Friday 9th October": the Week ahead heading spells its end day out (Alan, 2026-10-09) */
export const ordinal=n=>n+((n%100>=11&&n%100<=13)?"th":["th","st","nd","rd"][n%10]||"th");
/* Every date on Today reads "Thursday 15th October" (Alan, 2026-10-09); the year is added only when it isn't this year */
/* BL-287: beside a meeting's Prep, when creaite has saved a prep page for it, an Open icon that goes straight to the page (Meetings › Prep,
   #prep=<key>, BL-286 D) and the "Prep page made" chip. A real button of its own (never inside Prep), named for the meeting; its tooltip
   says when the page was saved. Without the live server it is shown disabled. */
export function prepGoHtml(e,day){ const pg=prepPageOf(e,day); if(!pg) return ""; const live=viaServer();
  return String(html`<button type="button" class="ib prepgo" data-prepgo="${pg.key}" data-prepgoday="${day}" aria-label="Open the prep page for ${e.title??""}" data-tip="${live?`Prep page saved ${pg.when}`:"creaite isn’t running"}"${raw(live?"":' aria-disabled="true"')}>${raw(ic("external"))}</button><span class="tag ok prepmade">Prep page made</span>`); }
export const longDay=iso=>{ if(!iso||!DATE.test(iso.slice(0,10))) return iso||""; const d=new Date(iso.slice(0,10)+"T12:00:00");
  return `${d.toLocaleDateString("en-GB",{weekday:"long"})} ${ordinal(d.getDate())} ${d.toLocaleDateString("en-GB",{month:"long"})}${iso.slice(0,4)!==TODAY.slice(0,4)?" "+iso.slice(0,4):""}`; };
export const longDate=iso=>{ const d=new Date(iso.slice(0,10)+"T12:00:00"); return `${ordinal(d.getDate())} ${d.toLocaleDateString("en-GB",{month:"long"})} ${iso.slice(0,4)}`; };   /* "8th October 2026" */
export const longText=t=>String(t??"").replace(/\b(\d{2})-(\d{2})-(\d{4})\b/g,(m,dd,mm,yy)=>longDay(`${yy}-${mm}-${dd}`));   /* dates written in text */
export let TVIPSEEN=null;   /* BL-263: the VIP alerts already shown, so only new ones slide in */
export const SETUPID="setup:checklist", SETUPK="creaite-setup-seen";   /* declared before renderToday, which runs at load */
export const swept=()=>!!(D.last_sweep&&D.last_sweep!=="never");   /* declared before renderToday, which runs at load */
export const SU_M365="setup: check Microsoft 365", SU_LAUNCH=()=>`cd ${VAULT_PATH} && python3 system/scripts/launch.py make-launcher`, SU_SETUP="setup";   /* declared before setupSteps, which runs at load (renderSetup) */
export const DC=()=>D.day||{moved:{},promised:[],tomorrow:{meetings:[]}};   /* declared before renderToday, which runs at load */
export const pkAdd=(iso,n)=>{ const d=new Date(iso+"T00:00:00Z"); d.setUTCDate(d.getUTCDate()+n); return d.toISOString().slice(0,10); };   /* declared before renderToday, which runs at load */
export function renderToday(){
  renderDay();   /* BL-293: the date or the day line too */
  const pend=REV.filter(r=>!r.done), mineOver=A.filter(x=>isMe(x.o)&&overdue(x)), mineSoon=A.filter(x=>isMe(x.o)&&soon(x)), off=P.filter(p=>p.health==="Off track");
  putHTML($("#briefText"),html`<b>${pend.length} suggestion${pend.length===1?"":"s"}</b> need${pend.length===1?"s":""} your decision, ${raw(countLink(`${plur(mineOver.length,"overdue action")} of yours`,mineOver.length,"actions:overdue:",{o:["@me"]},`<b>${mineOver.length} of your actions</b>`))} ${mineOver.length===1?"is":"are"} overdue${off.length?html`, and <b>${andList(off.map(p=>p.name))}</b> ${off.length===1?"is":"are"} off track`:""}.`);
  renderDn();   /* BL-210: Decisions needed, ahead of Needs attention */
  const att=attentionItems(), ac=capped(att.map((x,i)=>x.html(i+1)),5,"attn");
  $("#nAttn").textContent=att.length?String(att.length):""; /* #322: nothing to attend to, no section (heading included) */ $("#attnSec").hidden=!ac.html; putHTML($("#attnList"),ac.html?raw(ac.html):html``); putHTML($("#attnMore"),raw(ac.more));
  const mine=[...mineOver,...mineSoon].sort((a,b)=>a.due.localeCompare(b.due)), mc=capped(mine.map((x,i)=>tl(i+1,tLink(html`data-open="actions:${x.id}"`,html`${x.t??""}`),
    html`${raw(dueWords(x.due))} on ${x.p?raw(projLink(x.p)):"no project"}${x.pr==="Urgent"?", marked Urgent":""}${x.upd?`. Latest: ${lw(x.upd).length>140?lw(x.upd).slice(0,139)+"…":lw(x.upd)}`:""}.`,itemActs("actions",x))),5,"mine");
  putHTML($("#nMine"),raw(mine.length?countLink(`${plur(mine.length,"action")} of yours due or overdue`,mine.length,"actions:open:",{st:["Open","Delayed"],due:["overdue","soon"],o:["@me"]}):""));   /* BL-190 */ putHTML($("#mineList"),mc.html?raw(mc.html):html`<li><span class="n"></span><div class="tb"><span class="none">Nothing due from you this week.</span></div></li>`); putHTML($("#mineMore"),raw(mc.more));
  renderPromises();   /* BL-125 A: You owe and Waiting on */
  /* Resolved: items closed since the last visit, from the change log */
  const seen=new Set(), done=shared.ACT.filter(a=>a.at>LASTVISIT&&!a.undone&&(a.tbl==="actions"||a.tbl==="raid")&&/^status: .*→ Closed$/i.test(a.change)&&!seen.has(a.id)&&seen.add(a.id));
  const rc=capped(done.map((a,i)=>{ const x=(a.tbl==="actions"?A:R).find(y=>y.id===a.id), when=a.at.slice(0,10)===TODAY?`at ${a.at.slice(11)} today`:`on ${longDay(a.at.slice(0,10))}`;
    return tl(i+1,tLink(html`data-open="${a.tbl}:${a.id}"`,html`${a.item||a.id}`),html`${x&&x.p?html`${plur(1,a.tbl==="actions"?"action":(x.type||"risk").toLowerCase())} on ${raw(projLink(x.p))}, `:""}closed ${when} — ${a.by.replace(/^You, /,"you, ")}.`); }),5,"res");
  $("#chgTitle").textContent=`${done.length} since ${longDate(LASTVISIT.slice(0,10))}`;   /* BL-319: folded to one line, the count in it */
  putHTML($("#chgList"),rc.html?raw(rc.html):html`<li><span class="n"></span><div class="tb"><span class="none">Nothing has been resolved since ${longDate(LASTVISIT.slice(0,10))}.</span></div></li>`);
  putHTML($("#chgMore"),html`${raw(rc.more)}${rc.more?" · ":""}<a class="s" href="#" data-go="activity">See all activity</a>`);
  renderIntakeLine();   /* #245: Intake, one quiet line at the foot of Your commitments */
  renderToDecide();   /* #245: Messages (BL-334), just above Week ahead */
  renderWeek();   /* BL-319: day by day to next Monday, each row saying why it is there */
  putHTML($("#pfTbl"),raw(portfolioTable("pf",true))); mountStatusDots($("#pfTbl")); pfResize($("#pfTbl"));   /* BL-285; BL-256 */
  decorateWarnings($("#mineList"));   /* BL-49 */
  mountFirstThing(DC().first||null);   /* BL-295: First thing, from the last Close the day */
  if(!shared.LOADING){ { const L=$$("#tdList li.td-message[data-td]"), ids=L.map(x=>x.dataset.td);
    if(TVIPSEEN&&!reduced()) L.filter(x=>!TVIPSEEN.has(x.dataset.td)).forEach(x=>slideDown(x)); TVIPSEEN=new Set(ids); }
  mDots("today");
  renderSetup();   /* BL-155 */
  renderSweepDue();   /* #200 */
  { $("#drStale")?.remove(); const host=$("#mineMore"); if(host&&draftOn("update")){
    const st=A.filter(x=>isStale("actions",x)); if(st.length){
    addHTML(host,"afterend",html`<div class="drstale" id="drStale"><span>${raw(plur(st.length,"open action"))} ${st.length===1?"has":"have"} had no update for ${raw(+S.staleDays||7)} days.</span>${raw(draftBtn("update-bulk","Draft updates","Draft an update for each from what has happened since, as proposals in Review",'data-drstale="1"'))}<span class="drbst" role="status"></span></div>`); } } }   /* AI drafts: stale actions */
  dcIcon(); } }   /* BL-205 */
/* Today's day view: Alan's meetings (saved locally by cx-sweep from Outlook) as a line with a bump per meeting,
   a sun at the current time, and a headline naming the day's shape. Without a calendar the line is flat. */
export const NUMW=["No","One","Two","Three","Four","Five","Six","Seven","Eight","Nine","Ten"];
export const mins=t=>{ const [h,m]=t.split(":").map(Number); return h*60+m; }, hhmm=m=>`${z2(Math.floor(m/60))}:${z2(m%60)}`;
export const nowMins=()=>{ const n=new Date(); return n.getHours()*60+n.getMinutes(); };
/* BL-293: for another day (`day`), with no "still ahead" or "behind you" logic: that is today's alone */
export function dayShape(ev,first,day){ const timed=ev.filter(e=>!e.all_day), n=timed.length, name=first?`, ${first}`:"", today=!day||day===TODAY;
  if(!n) return today?`No meetings today${name}. The day is yours.`:`No meetings on ${longDay(day).split(" ")[0]}${name}.${day>TODAY?" The day is yours.":""}`;
  const busy=timed.map(e=>[mins(e.start),mins(e.end)]).sort((a,b)=>a[0]-b[0]), gaps=[]; let t=8*60;
  busy.forEach(([a,b])=>{ if(a>t) gaps.push([t,Math.min(a,18*60)]); t=Math.max(t,b); }); if(t<18*60) gaps.push([t,18*60]);
  const nw=today?nowMins():0; gaps.forEach(g=>g[0]=Math.max(g[0],nw));   /* only free time still ahead */
  const big=gaps.filter(g=>g[1]-g[0]>=60).sort((a,b)=>(b[1]-b[0])-(a[1]-a[0]))[0], cnt=`${n<=10?NUMW[n]:n} meeting${n===1?"":"s"}${name}`;
  if(today&&n>1&&nowMins()>=busy[busy.length-1][1]) return `${cnt}, and they're all behind you.`;
  if(!big) return gaps.some(g=>g[1]-g[0]>=30)?`${cnt}, with only short gaps between them.`:`${cnt}, back to back.`;
  const [a,b]=big, c=(a+b)/2;
  const part=b-a>=240?(c<13*60?"the morning":"the afternoon"):a>=17*60-1?"the evening":c<10*60?"the early morning":c<12*60?"the late morning":c<13.5*60?"lunchtime":c<15.5*60?"the early afternoon":"the late afternoon";
  return `${cnt}, with ${part} ${part==="lunchtime"?"free":"wide open"}.`; }
export function renderDay(){ const cal=D.calendar, first=(S.me||"").split(" ")[0], on=S.srcCalendar!==false, L=on?dayList():[], iso=dayShown(), isToday=iso===TODAY;
  if(isToday) selDay.value="";
  const rec=L.find(d=>d.date===iso)||synthDay(iso), tabs=L.length>1;   /* BL-293: the day line, when there are days to move between */
  drawDayTabs($("#todayDate"),tabs?{days:L,selected:iso,onSelect:d=>{ goDay(d); },onStep:n=>{ stepDay(n); }}:null,longDay(TODAY));
  const line=$("#dayLine"), meets=$("#dayMeets"); line.hidden=!on; meets.hidden=!on;
  if(tabs){ meets.setAttribute("role","tabpanel"); meets.setAttribute("aria-label",rec.long); } else { meets.removeAttribute("role"); meets.removeAttribute("aria-label"); }
  const v=on?dayView(iso):{known:false,meetings:[],allDay:[]};
  $("#dayHead").textContent=v.known?dayShape(v.meetings,first,iso):v.unread?`${rec.dow} has not been read yet${first?", "+first:""}.`:`Good ${nowMins()<12*60?"morning":nowMins()<18*60?"afternoon":"evening"}${first?", "+first:""}.`;
  if(!on){ drawDayCurve(line,null); drawDayMeetings(meets,null); calFoot(null); return; }
  /* ===== BL-151 (sprint-ux) ===== no calendar for today: the band is one quiet line, "No calendar yet", with Refresh calendar
     (Intake's action) beside it; no empty timeline. When the calendar arrives the band opens as before; a day read with no
     meetings keeps its line and says so ("No meetings today"). BL-270: that line says when it was read. */
  const common={day:iso,dow:rec.dow||synthDay(iso).dow,isToday,past:iso<TODAY,now:nowMins(),live:viaServer(),calendar:!!cal,acts:DAYACTS,onWheel:onDayWheel,meetings:v.meetings,allDay:v.allDay};
  if(!v.known){ line.hidden=true; drawDayCurve(line,null);
    drawDayMeetings(meets,{...common,mode:"none",unread:!!v.unread,lastRead:cal&&cal.fetched?longDay(cal.fetched)+(cal.fetched.length>10?", "+cal.fetched.slice(11,16):""):""}); calFoot(null); return; }
  /* ===== end BL-151 ===== */
  const n=v.meetings.length;
  drawDayCurve(line,{day:iso,timed:v.meetings,now:isToday?nowMins():null,past:iso<TODAY,label:isToday?`Today's meetings: ${n}`:`${rec.long}: ${plur(n,"meeting")}`,width:line.clientWidth,onWheel:onDayWheel});
  drawDayMeetings(meets,{...common,mode:"meetings"}); calFoot(cal); }
/* ===== BL-293: Today moves between the calendar's days =====
   The day line (#todayDate) lists every day of the saved calendar the server sends (D.days, build_dashboard.calendar_days);
   only the band follows the chosen day: the headline, the line and the meetings. Everything below stays as of today. The
   chosen day lives in memory only (stores/today.js), so a reload opens on today. Today's meetings still come from the
   calendar as the page holds it (D.calendar), with what the server worked out for each (its follow-up, Prep and plan). */
const WDAYS=["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"];
export function synthDay(iso){ const d=new Date(iso+"T12:00:00"), dow=WDAYS[d.getDay()]; return {date:iso,dow,short:`${dow.slice(0,3)} ${d.getDate()}`,long:longDay(iso),today:iso===TODAY,past:iso<TODAY,weekend:wkDays().has((d.getDay()+6)%7),week:0,meetings:[],all_day:[]}; }
/** The days the line offers: the server's, with today added when the calendar holds nothing for it. */
export function dayList(){ if(!D.calendar) return []; const L=[...(((D.days||{}).days)||[])];
  if(!L.some(d=>d.date===TODAY)){ L.push(synthDay(TODAY)); L.sort((a,b)=>a.date.localeCompare(b.date)); } return L; }
export const dayShown=()=>{ const s=selDay.value; return s&&s!==TODAY&&dayList().some(d=>d.date===s)?s:TODAY; };
const isConf=e=>String((e&&e.sensitivity)||"").toLowerCase()==="confidential";
/** One day's meetings for the band, from the page's calendar where it has the day (today always), else from D.days. */
export function dayView(iso){ const raw=((D.calendar||{}).days||{})[iso], rec=dayList().find(d=>d.date===iso), srv=(rec&&rec.meetings)||[];
  const extra=m=>({...m,page:m.prep?((SA().prep_pages||{})[m.prep.key]||m.prep.page||null):null,pageWhen:m.prep?((prepPageOf(m,iso)||{}).when||m.prep.page_at_shown||""):"",
    running:m.id?DAYRUN.get(m.id):undefined});
  if(raw){ const timed=raw.filter(e=>!e.all_day);
    return {known:true, allDay:raw.filter(e=>e.all_day).map(e=>({title:e.private?"Busy":e.title??"",p:e.private||isConf(e)?null:e.p||null})),
      meetings:timed.map((e,i)=>{ const priv=!!e.private, s=srv.find(m=>m.start===e.start&&(priv?m.private:m.title===e.title)), conf=!!(s&&s.confidential)||isConf(e);
        const prep=priv?null:(s&&s.prep)||(iso>=TODAY&&prepOf(e,iso)?{key:prepKey(e,iso)}:null);
        return extra({start:e.start,end:e.end,title:e.title??"",private:priv,confidential:conf,id:e.id||(s&&s.id)||null,p:priv||conf?null:(s&&s.p)||e.p||null,
          where:e.where||"",organiser:e.organiser,follow:s&&s.follow,prep,plan:conf?null:(s&&s.plan)||null,ix:i,attendees:conf||priv||!Array.isArray(e.attendees)?undefined:e.attendees.length}); })}; }
  if(rec&&rec.unread) return {known:false,unread:true,meetings:[],allDay:[]};   /* #318: a day beyond what the calendar was read to is "Not read yet", never "no meetings" */
  if(rec&&iso!==TODAY) return {known:true,meetings:srv.map(m=>extra({...m,ix:null})),allDay:(rec.all_day||[]).map(t=>({title:t,p:null}))};
  return {known:false,meetings:[],allDay:[]}; }
/** Show day `iso`, sliding the band in from its side. False when there is no day line. */
export function goDay(iso){ const L=dayList(); if(L.length<2||S.srcCalendar===false) return false;
  const i=L.findIndex(d=>d.date===dayShown()), j=L.findIndex(d=>d.date===iso); if(j<0) return false; if(j===i) return true;
  selDay.value=iso===TODAY?"":iso; renderDay(); daySlide(j>i?1:-1); return true; }
/** One day on (+1) or back (-1); at either end the band nudges and stays. */
export function stepDay(n){ const L=dayList(); if(L.length<2||S.srcCalendar===false) return false;
  const j=L.findIndex(d=>d.date===dayShown())+n; if(j<0||j>=L.length){ dayBump(n); return true; } return goDay(L[j].date); }
const DAYPIECES=()=>["#dayHead","#dayLine","#dayMeets"].map(q=>$(q));
export function daySlide(dir){ if(reduced()) return; DAYPIECES().forEach(el=>anim(el,[{transform:`translateX(${dir*36}px)`,opacity:.2},{transform:"none",opacity:1}],{duration:220})); }
export function dayBump(dir){ if(reduced()) return; DAYPIECES().forEach(el=>anim(el,[{transform:"none"},{transform:`translateX(${-dir*10}px)`,offset:.3},{transform:"none"}],{duration:250})); }
/** [ and ] step, T goes back to today: on Today only, never while typing (keys.js checks) or with a dialog open. */
export function dayKey(e){ if(shared.VIEW!=="today"||document.querySelector("dialog[open]")) return false;
  if(e.key==="["||e.key==="]") return stepDay(e.key==="]"?1:-1);
  if(e.key==="t"||e.key==="T") return goDay(TODAY);
  return false; }
/* A two-finger swipe over the band (wheel deltaX) steps one day per gesture, left for the next: the gesture's momentum tail
   (deltas dying down) is ignored, and a pause, or deltas growing again after they had died down, starts the next one. The
   default is prevented, so Chrome's back gesture never fires over the band (and the band sets overscroll-behavior-x). */
const SWIPE={acc:0,locked:false,idle:0,last:0,min:Infinity,seen:new WeakSet()};
export function onDayWheel(e){ if(SWIPE.seen.has(e)) return; SWIPE.seen.add(e);
  if(shared.VIEW!=="today"||S.srcCalendar===false||dayList().length<2) return;
  const ax=Math.abs(e.deltaX); if(ax<=Math.abs(e.deltaY)) return; e.preventDefault();
  clearTimeout(SWIPE.idle); SWIPE.idle=setTimeout(()=>{ SWIPE.locked=false; SWIPE.acc=0; SWIPE.last=0; SWIPE.min=Infinity; },120);
  if(SWIPE.locked){ SWIPE.min=Math.min(SWIPE.min,ax); if(SWIPE.min<6&&ax>Math.max(10,SWIPE.last*1.8)){ SWIPE.locked=false; SWIPE.acc=0; SWIPE.min=Infinity; } }
  SWIPE.last=ax; if(SWIPE.locked) return; SWIPE.acc+=e.deltaX;
  if(Math.abs(SWIPE.acc)>40){ SWIPE.locked=true; SWIPE.min=ax; stepDay(SWIPE.acc>0?1:-1); SWIPE.acc=0; } }
/* what the band's buttons do */
export const DAYRUN=new Map();   /* a check or a process under way, by calendar ID: "Checking…" */
/** Process an ended meeting's transcript, as Calendar import does (load it unless it is loaded, then cx-minutes). */
export async function dayProcess(m){ const row=MTG().find(x=>x.id===m.id); if(!row){ snack("Open Intake to process this meeting"); return; }
  DAYRUN.set(m.id,"Processing…"); renderDay();
  try{ await irProcessById(m.id); } finally{ DAYRUN.delete(m.id); if(shared.VIEW==="today") renderDay(); } }
/** Look for an ended meeting's transcript (Alan, 13-10-2026: a meeting not checked yet offers Check). */
export async function dayCheck(m){ const row=MTG().find(x=>x.id===m.id)||{id:m.id,title:m.title,day:dayShown(),start:m.start};
  DAYRUN.set(m.id,"Checking…"); renderDay();
  try{ await checkMeeting(row); } finally{ DAYRUN.delete(m.id); if(shared.VIEW==="today") renderDay(); } }
export const DAYACTS={open:p=>{ prepOpen(p); },process:m=>{ dayProcess(m); },check:m=>{ dayCheck(m); },review:()=>go("intake-review"),name:c=>pName(c)};   /* #140: no Note link on the band (BL-301 C's capture drawer opens from elsewhere) */
/* ===== end BL-293 ===== */
/* BL-270 (sprint-ui-sweep): the calendar's read time, when it is from an earlier day, is a footnote at the bottom right of Today */
export function calFoot(cal){ const f=$("#calFoot"); if(!f) return; const old=!!(cal&&cal.fetched&&cal.fetched.slice(0,10)!==TODAY); f.hidden=!old;
  putHTML(f,old?html`Calendar as read on <span class="calold">${fdText(cal.fetched)}</span>.`:html``); }
   /* BL-151 */
/* BL-34: a report reminder can run its report: the command goes to ask creaite, which drafts as usual (confirmed in
   the panel, held for review, filed on approval). The reminder stays until the report is filed. */
export const RUNNING=new Set();
export async function runReminder(r){ if(!r||!r.cmd||!viaServer()||RUNNING.has(r.id)) return; closeMenu();
  if(shared.BUSY){ snack("ask creaite is busy; try again when it's finished"); return; }
  RUNNING.add(r.id); renderToday(); openChat();
  try{ await send(r.cmd); } finally{ RUNNING.delete(r.id); renderToday(); }
  if(r.id.startsWith("weekly:")&&REV.some(x=>!x.done&&x.p&&(!r.id.split(":")[2]||x.p===r.id.split(":")[2]))) await say("A project with items awaiting review is skipped until they're reviewed.",`<button class="mini" data-go="review">Open Intake</button>`); }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootToday0026(){
$("#tBrief").addEventListener("click",async e=>{ const a=e.target.closest('a[href="#"]'); if(a) e.preventDefault();
  const m=e.target.closest("[data-more]"); if(m){ const k=m.dataset.more; EXPAND.has(k)?EXPAND.delete(k):EXPAND.add(k); renderToday(); return; }
  const gp=e.target.closest("[data-gap]"); if(gp){ const [code,k]=gp.dataset.gap.split("|"), wt=k==="raid"?"raid":"actions",
      extra=k==="due"?{st:["Open","Delayed"],due:["none"]}:{st:wt==="raid"?["Open"]:["Open","Delayed"],o:["TBC"]};
    if(code){ openWork(code,wt,"open",extra); return; }
    if(navBlocked()) return; clearAllFilters(); shared.WT=wt; applyView("open"); applyFilters(extra); syncView(); go("work"); return; }
  });
window.addEventListener("resize",()=>{ if(shared.VIEW==="today") renderDay(); });
/* BL-293: swipe and touch drag over the day band move between days */
{ const band=$("#v-today .dayband"); let sx=null, sy=0;
  band.addEventListener("wheel",onDayWheel,{passive:false});
  band.addEventListener("pointerdown",e=>{ if(e.pointerType==="mouse") return; sx=e.clientX; sy=e.clientY; });
  band.addEventListener("pointerup",e=>{ if(sx==null) return; const dx=e.clientX-sx, dy=e.clientY-sy; sx=null;
    if(Math.abs(dx)>50&&Math.abs(dx)>Math.abs(dy)*1.5) stepDay(dx<0?1:-1); });
  band.addEventListener("pointercancel",()=>{ sx=null; }); }
document.addEventListener("click",e=>{ if(e.target.closest("[data-refcal]")) irRefreshCalendar(); });   /* #284: the header's ? is gone (the ? key opens Help) */
}
/* ===== BL-149 (sprint-ux) ===== no dead ends into Claude Code. If the dashboard can do it, it does; the command is a footnote,
   shown only when the live server is down. A reminder gets one primary button on its row (Draft weekly report, Draft client
   report), which does what the … menu's Run report now does (runReminder: the command goes to ask creaite, which asks before
   drafting). A conflicting proposal in Review shows the tracker's current value beside the proposed one, with Keep current
   and Use this one (review.py keep / override through /api/review, then the usual apply and Undo). Approve on a draft already
   goes through review.py (reviewViaServer). Nothing here writes on its own: each change is Alan's click. */
export const PEOPLE_MOVE="setup: move the people still listed in settings.json into the people register";
export function remLabel(r){ return r.id.startsWith("weekly:")?"Draft weekly report":r.id.startsWith("client:")?"Draft client report":"Run it"; }
export function remBody(r){ if(!r.cmd) return ""; return viaServer()?"":`It needs the live server; or say <span data-codeok>“${esc(r.cmd)}”</span> in Claude Code.`; }
export function remBtn(r){ if(!r.cmd) return ""; const run=RUNNING.has(r.id), live=viaServer(), why=run?"Already running":live?"":"creaite isn’t running";
  return `<span class="rmgo tacts">${tib("filetext",run?"Running…":remLabel(r),`${remLabel(r)}: ${r.text}`,`data-d="run"${why?` data-why="${esc(why)}"`:""}`,true,why)}</span>`; }   /* BL-319: an icon, named on hover */
export const isConflict=r=>!!r&&!r.done&&(r.flags||[]).includes("conflict");
export function conflictHtml(r){ const ch=(r.rec.changes&&r.rec.changes.length?r.rec.changes:r.rec.field?[{field:r.rec.field,from:r.rec.from,to:r.rec.to}]:[]);
  const v=x=>x==null||x===""?"(empty)":esc(DATE.test(String(x).slice(0,10))&&String(x).length===10?fd(x):String(x));
  return `<div class="cfvs">${ch.map(c=>`<div><span class="cff">${esc(c.field)}</span><span class="cfnow">Now: <b>${v(c.from)}</b></span><span class="cfnew">This one: <b>${v(c.to)}</b></span></div>`).join("")||'<div class="sub">Changed in the tracker after this was proposed.</div>'}</div>`; }
/* ===== end BL-149 ===== */
export const kindLabel=r=>({actions:"Action",raid:r.rec.type||"Risk",decisions:"Decision",update:"Update",draft:"Draft",files:"File change"}[r.kind]);
export function evidence(p){ const nw=WARNS().filter(w=>w.p===p.code).length, ov=A.filter(x=>x.p===p.code&&overdue(x)).length, urg=R.filter(r=>r.p===p.code&&r.st==="Open"&&r.pr==="Urgent").length;
  /* BL-190 (sprint-links): each figure is its own link (a zero stays plain); a click on one doesn't also open the row's project page */
  const nd=undatedWork(p.code).length, c=p.code, nm=pName(c);
  return `<span class="ev">${countLink(`${plur(ov,"overdue action")} in ${nm}`,ov,`actions:overdue:${c}`,null,`Overdue <b class="${ov?"bad":""}">${ov}</b>`)} · ${jumpLink(`${plur(nd,"open item")} with no due date in ${nm}`,nd,c,"undated",`No date <b>${nd}</b>`)} · ${countLink(`${plur(urg,"urgent open RAID item")} in ${nm}`,urg,`raid:urgentonly:${c}`,null,`Urgent risks <b class="${urg?"bad":""}">${urg}</b>`)} · ${jumpLink(`Milestone slip of ${p.slip} day${p.slip===1?"":"s"} in ${nm}`,p.slip,c,"ms",`Slip <b class="${p.slip?"bad":""}">${p.slip?p.slip+" days":"none"}</b>`)} · Warnings <b class="${nw?"bad":""}">${nw}</b></span>`; }
/* #162 (Alan, 16-10-2026): the health trend is six weeks (as the weekly report), oldest first, one bar per week ending Friday. Height is
   health (option B): tall green On track, medium amber At risk, a short red stub Off track, a thin line when no update was
   approved; the colour repeats the height. The strip is one tab stop (Left/Right/Home/End move between weeks, Esc closes the tip);
   a dot under the last bar is this week. Hover or focus shows the week, its health in words, whether it changed, that week's
   reason when one is stored, and the six weeks again. The ? on the column header opens the key. */
const SPN={ok:"On track",warn:"At risk",bad:"Off track","":"No update"};
export const legBtn=()=>`<button type="button" class="legbtn" aria-label="What the health bars mean" aria-haspopup="dialog" aria-expanded="false"></button>`;
export const spark=p=>{ const t=p.trail, last=t[t.length-1];
  return `<span class="spark" tabindex="0" role="group" data-sp="${esc(p.code)}" aria-label="Health, last ${t.length} weeks, oldest first. ${last?SPN[last]:"No update"} this week. Arrow keys move between weeks.">${t.map((x,i)=>`<i class="s-${x}" data-i="${i}"></i>`).join("")}</span>`; };
const sparkWeek=(p,i)=>{ const t=p.trail[i], pv=i?p.trail[i-1]:null, why=(p.trailwhy||[])[i]||"", end=(p.trailend||[])[i]||"";
  const ch=!t?"No update approved this week":pv===null?"First week shown":pv===""?"No update the week before":pv===t?`Unchanged from ${SPN[pv]}`:`Changed from ${SPN[pv]}`;
  return {t,end,ch,why,word:SPN[t]}; };
export function sparkTipHtml(p,i){ const w=sparkWeek(p,i), n=p.trail.length;
  return `<div class="spk-wk">Week ending ${fd(w.end)}${i===n-1?" · this week":""}</div><div class="spk-h">${w.t?`<span class="spk-dot s-${w.t}"></span>`:""}${w.word}</div><div class="spk-ch">${w.ch}</div>${w.why?`<div class="spk-why">${esc(w.why)}</div>`:""}`
   +`<ol class="spk-list" aria-label="The last ${n} weeks">${p.trail.map((x,j)=>`<li${j===i?' class="cur" aria-current="true"':""}><span class="spark mini" aria-hidden="true"><i class="s-${x}"></i></span><span class="spk-d">${fd((p.trailend||[])[j]||"")}</span><span class="spk-w">${SPN[x]}</span></li>`).join("")}</ol>`; }
/** The key (the ? popover): the four bars, drawn as they are in the table. */
export const sparkKeyHtml=()=>`<div class="spk-key" id="sparkLeg" role="dialog" aria-label="What the health bars mean" tabindex="-1"><div class="spk-kt">Health, last 6 weeks</div><div class="spk-ks">One bar a week, oldest to newest, each a week ending Friday. Taller is healthier. Rest on a bar for the week's reason: the week's update summary, shortened to 160 characters.</div>${["ok","warn","bad",""].map(x=>`<div class="spk-kr"><span class="spark mini" aria-hidden="true"><i class="s-${x}"></i></span>${SPN[x]}${x===""?" that week":""}</div>`).join("")}<div class="spk-kr"><span class="spk-kdot" aria-hidden="true"></span>This week</div></div>`;
/* The tip and the key are one element each, appended to the body when first needed (delegated, so every table and the project page share them). */
let sparkAt=null, sparkI=0;
const sparkEl=()=>document.querySelector(`.spark[data-sp="${CSS.escape(sparkAt||"")}"]:not(.mini)`);
function sparkShow(el,i){ const p=P.find(x=>x.code===el.dataset.sp); if(!p) return; sparkAt=p.code; sparkI=i;
  let tip=$("#sparkTip"); if(!tip){ tip=document.createElement("div"); tip.id="sparkTip"; tip.setAttribute("role","tooltip"); tip.setAttribute("aria-live","polite"); document.body.appendChild(tip); }
  putHTML(tip,raw(sparkTipHtml(p,i))); tip.hidden=false; el.setAttribute("aria-describedby","sparkTip");
  [...el.children].forEach((b,j)=>b.classList.toggle("cur",j===i));
  const r=el.children[i].getBoundingClientRect(), h=tip.offsetHeight, w=tip.offsetWidth; let y=r.top-h-10; if(y<8) y=r.bottom+14;
  tip.style.left=Math.round(Math.min(Math.max(8,r.left+r.width/2-w/2),innerWidth-w-8))+"px"; tip.style.top=Math.round(y)+"px"; }
function sparkHide(){ if(cardGroup.current instanceof Element&&cardGroup.current.matches(".spark")) cardGroup.close();   /* #160: the card group lets go too */ const tip=$("#sparkTip"); if(tip) tip.hidden=true; const el=sparkEl(); if(el){ el.removeAttribute("aria-describedby"); [...el.children].forEach(b=>b.classList.remove("cur")); } sparkAt=null; }
function sparkKeyClose(back){ const k=$("#sparkLeg"); if(!k) return; const btn=document.querySelector('.legbtn[aria-expanded="true"]')||$(".legbtn"); k.remove(); document.querySelectorAll(".legbtn").forEach(b=>b.setAttribute("aria-expanded","false")); if(back&&btn) btn.focus(); }
export function wireSpark(){
  const idx=e=>{ const b=e.target.closest&&e.target.closest(".spark:not(.mini) > i"); return b?+b.dataset.i:null; };
  /* #160: the pointer goes through the shared card group (core/hover.js): the delays are the card standard, none of its own */
  let wantI=null;
  const spkH=el=>({ open:()=>sparkShow(el,wantI===null?el.children.length-1:wantI), close:sparkHide });
  document.addEventListener("pointerover",e=>{ const el=e.target.closest&&e.target.closest(".spark[data-sp]"); if(!el||e.pointerType==="touch"||!canHover()) return; const i=idx(e);
    if(sparkAt===el.dataset.sp&&!$("#sparkTip").hidden){ if(i!==null&&i!==sparkI) sparkShow(el,i); cardGroup.enter(el,spkH(el)); return; }
    wantI=i; cardGroup.enter(el,spkH(el)); });
  document.addEventListener("pointerout",e=>{ const el=e.target.closest&&e.target.closest(".spark[data-sp]"); if(!el||el.contains(e.relatedTarget)||e.pointerType==="touch") return; cardGroup.leave(el); });
  document.addEventListener("focusin",e=>{ const el=e.target.closest&&e.target.closest(".spark[data-sp]"); if(el&&e.target===el) sparkShow(el,el.children.length-1); });
  document.addEventListener("focusout",e=>{ const el=e.target.closest&&e.target.closest(".spark[data-sp]"); if(el&&e.target===el) sparkHide(); });
  document.addEventListener("keydown",e=>{ const el=e.target.closest&&e.target.closest(".spark[data-sp]");
    if(el&&e.target===el){ const n=el.children.length; let i=sparkAt===el.dataset.sp?sparkI:n-1;
      if(e.key==="ArrowLeft") i=Math.max(0,i-1); else if(e.key==="ArrowRight") i=Math.min(n-1,i+1); else if(e.key==="Home") i=0; else if(e.key==="End") i=n-1;
      else if(e.key==="Escape"){ if(sparkAt){ e.stopPropagation(); sparkHide(); } return; } else return;
      e.preventDefault(); e.stopPropagation(); sparkShow(el,i); return; }
    if(e.key==="Escape"&&$("#sparkLeg")){ e.stopPropagation(); sparkKeyClose(true); } },true);
  document.addEventListener("click",e=>{ const b=e.target.closest&&e.target.closest(".legbtn");
    if(b){ e.stopPropagation(); if($("#sparkLeg")){ sparkKeyClose(false); return; } addHTML(document.body,"beforeend",raw(sparkKeyHtml()));
      const k=$("#sparkLeg"), r=b.getBoundingClientRect(); k.style.top=Math.round(r.bottom+6)+"px"; k.style.left=Math.round(Math.min(Math.max(8,r.left-20),innerWidth-k.offsetWidth-8))+"px"; b.setAttribute("aria-expanded","true"); k.focus(); return; }
    if($("#sparkLeg")&&!e.target.closest("#sparkLeg")) sparkKeyClose(false); },true);
}
/* BL-285: the Portfolio table. The description is no longer a line under the name: it is the name's tooltip (data-tip), shown on
   hover and on keyboard focus (the name is a button that opens the project), and read by screen readers from a hidden span
   (aria-describedby). The columns resize like Work's (pfResize), remembered under portfolio|<column>. */
export const PFCOLS=[["project","Project"],["health","Health"],["evidence","Evidence"],["trend","6 weeks"],["next","Next milestone"]];
/** @param {string} [id] @param {boolean} [dots] BL-256: Today's health markers are StatusDot components (placeholders, then mountStatusDots). BL-325: the next milestone's relative date is mid-sentence in brackets, so lower case ("(in 24 days)") */
export function portfolioTable(id="pf",dots=false){ return `<table><thead><tr>${PFCOLS.map(([k,l])=>`<th data-col="${k}">${l}${k==="trend"?legBtn():""}</th>`).join("")}</tr></thead><tbody>${P.map(p=>{ const nm=p.ms.find(m=>m[2]!=="done")||p.ms[p.ms.length-1]||["No milestones yet","",""], ds=(p.client||"").trim(), did=`${id}d-${p.code}`;
  return `<tr class="click" data-cock="${p.code}"><td><button type="button" class="pfname"${ds?` data-tip="${esc(ds)}" aria-describedby="${did}"`:""}>${esc(p.name)}</button>${ds?`<span class="vh" id="${did}">${esc(ds)}</span>`:""}</td><td>${dots?`<span data-statusdot="${esc(p.health||"")}"></span>`:health(p.health)}<div class="sub" style="max-width:36ch">${esc(p.reason)}</div></td><td>${evidence(p)}</td><td>${spark(p)}</td><td>${esc(nm[0])}${nm[1]?`<div class="sub ${nm[2]==="slip"?"late":""}">${longDay(nm[1])} (${rel(nm[1]).replace(/^./,c=>c.toLowerCase())})</div>`:""}</td></tr>`; }).join("")}</tbody></table>`; }
export function pfResize(box){ if(box) $$("thead th[data-col]",box).forEach(th=>colResizer(th,"portfolio|"+th.dataset.col)); }
/* BL-316: a reminder's "…" menu is the Menu block's (openMenu): Run report now, Dismiss for this session, Dismiss forever */
export function remMenu(b,id){ if(menuOpenFor(b)){ closeMenu(); return; } const r=REMINDERS.find(x=>x.id===id); if(!r) return; const why=RUNNING.has(id)?"Already running":viaServer()?"":"creaite isn’t running";
  openMenu(b,{label:`Options: ${r.text}`,id:"remMenu",align:"right",onPick:d=>remPick(id,d),
    items:[...(r.cmd?[{id:"run",name:"Run report now",disabled:!!why,tip:why||undefined,data:{d:"run"}}]:[]),{id:"s",name:"Dismiss for this session",data:{d:"s"}},{id:"f",name:"Dismiss forever",data:{d:"f"}}]}); }
export function remPick(id,d){ if(d==="run"){ runReminder(REMINDERS.find(r=>r.id===id)); return; }
  if(d==="s"){ const a=dismissedS(); a.push(id); sessionStorage.setItem("creaite-dismiss-s",JSON.stringify(a)); } else { const a=dismissedF(); a.push(id); store.set("creaite-dismiss",a); writeSettings({"reminders.dismissed_forever":[...new Set([...(D.dismissed||[]),...a])]}); }
  renderToday(); snack(d==="s"?"Hidden for this session":"Hidden for good (this one)",()=>{ store.set("creaite-dismiss",dismissedF().filter(x=>x!==id)); sessionStorage.setItem("creaite-dismiss-s",JSON.stringify(dismissedS().filter(x=>x!==id))); renderToday(); }); }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootToday0028(){
wireSpark();
$("#attnList").addEventListener("click",e=>{ const mb=e.target.closest("li[data-msattn] .dots"); if(mb){ e.stopPropagation(); msAttnMenu(mb,mb.closest("li").dataset.msattn); return; }   /* #251 */
  const mw=e.target.closest("[data-msattnwork]"); if(mw){ e.preventDefault(); e.stopPropagation(); msAttnOpenWork(mw.dataset.msattnwork); return; }
  const n=e.target.closest(".rem"); if(!n) return; const b=e.target.closest("button"); if(!b) return; e.stopPropagation();
  if(b.classList.contains("dots")){ remMenu(b,n.dataset.id); return; }
  if(b.dataset.d) remPick(n.dataset.id,b.dataset.d); });
document.addEventListener("click",e=>{ const b=e.target.closest&&e.target.closest("[data-wkitems]"); if(b){ e.preventDefault(); msItemsOpenWork(b.dataset.wkitems,b.dataset.p||""); return; } });   /* #310 */
document.addEventListener("click",e=>{ if(e.target.closest&&e.target.closest(".colrz")) return; const r=e.target.closest("[data-cock]"); if(r) go("cockpit",r.dataset.cock); });   /* BL-285: a resize never opens the project */
}
/* ===== BL-156 (sprint-ux) ===== first run: a short checklist on Today. On a vault that hasn't finished set-up (no project, no
   people in the register, or no sweep yet) Today starts with five steps, each with a button that does it or opens where it is
   done, ticked as it is done: Connect Microsoft 365 (ticked by the first sweep, which needs it; the button opens Help's first
   hour), Add a project (the Projects page, then ask creaite), Add people (the People page, #248), Run the first sweep (ask creaite,
   "sweep"), Open Intake (ticked once Intake has been opened in this browser). It goes when all five are ticked, or for good with
   Dismiss (kept with the dismissed reminders, so Settings › Reminders › Restore brings it back). Nothing it does is new. */
export function setupSteps(){ const seen=store.get(SETUPK,{});
  return [["m365","Connect Microsoft 365",swept(),"Show me how","help",swept()?"Connected: the mail and Teams check has read your mail":`Connected in Claude itself, so the page can’t: connect it there, then ask Claude to check it. The first mail and Teams check confirms it`],
    ["proj","Add a project",P.length>0,"Add a project","proj",`${P.length} project${P.length===1?"":"s"}`],
    ["people","Add people",shared.REG.length>0,"Add people","people",`${shared.REG.length} in the people register`],
    ["sweep","Run the first check",swept(),"Run the first check","sweep",swept()?`Last checked ${esc(fd(String(D.last_sweep)))}`:"Reads mail, Teams and the calendar since the look-back days"],
    ["review","Open Intake",!!seen.review,"Open Intake","review","Approve what's right; nothing reaches your project record until you do"]]; }
export function setupShown(){ if([...dismissedF(),...(D.dismissed||[])].includes(SETUPID)) return false;
  const st=setupSteps(), base=st.slice(0,4).some(x=>!x[2]); if(base){ const seen=store.get(SETUPK,{}); if(!seen.shown){ seen.shown=true; store.set(SETUPK,seen); } return true; }
  return !!store.get(SETUPK,{}).shown&&!st[4][2]; }
export function renderSetup(){ let box=$("#setupList"); const on=setupShown();
  if(!on){ if(box) box.remove(); return; }
  if(!box){ addHTML($("#tBrief"),"afterbegin",html`<section class="tsec setupsec" id="setupList" aria-labelledby="hSetup"></section>`); box=$("#setupList"); }
  const st=setupSteps(), done=st.filter(x=>x[2]).length;
  putHTML(box,html`<h2 class="th" id="hSetup">Getting started <span class="cnt">${raw(done)} of ${st.length}</span><button type="button" class="linkbtn setupx" data-setup="dismiss">Dismiss</button></h2><ol class="bl setupbl">${raw(st.map(([k,t,ok,btn,act,note],i)=>`<li class="${ok?"done":""}"><span class="n" aria-hidden="true">${ok?"✓":i+1}</span><div class="tb"><span class="t">${esc(t)}</span>${ok?' <span class="vh">(done)</span>':""}<p>${note}</p></div>${ok?"":`<span class="rmgo"><button type="button" class="btn ${i===st.findIndex(x=>!x[2])?"primary":""}" data-setup="${act}" ${act==="sweep"&&!viaServer()?'disabled title="creaite isn’t running"':""}>${esc(btn)}</button></span>`}</li>`).join(""))}</ol>`); 
  { const b=$('#setupList [data-setup="help"]'), li=b&&b.closest("li");
    if(li&&!li.classList.contains("done")){ const go=li.querySelector(".rmgo"); putHTML(go,html`<button type="button" class="mini" data-sucheck="m365" ${viaServer()?"":html`disabled title="creaite isn’t running"`}>Check again</button> <button type="button" class="linkbtn" data-setup="help">How</button>`); }
    if($("#setupList")&&!$("#suMore")) addHTML($("#setupList"),"beforeend",html`<p class="sub" id="suMore">The health check and the launcher are in <a href="#" data-setopen="setup">Settings › System › Set-up</a>.</p>`); }   /* BL-165 */
  /* #300: the one question about starting creaite at sign-in (autostart.js; shown only where the server can do it) */
  { const q=profileQuestionHtml(), box=$("#setupList"), cur=$("#pfQ"); if(cur) cur.remove(); if(q&&box) addHTML(box,"beforeend",raw(q)); }   /* #312: About you, before the sign-in question */
  { const q=asQuestionHtml(), box=$("#setupList"), cur=$("#asQ"); if(cur) cur.remove(); if(q&&box) addHTML(box,"beforeend",raw(q)); } }
/* ===== end BL-156 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
/* #200: "Sweep due since 07:00" with Run sweep, above Today's sections. Shown only when the build says the daily sweep is due, not in the
   development repository, and not while the first-run checklist (which has its own sweep step) is up. The button sends "sweep" to ask
   creaite exactly as the checklist's does. The style hides it while the run badge is up (a run is going) and swaps the button for the
   usual restart hint while the live server isn't reachable. It goes when the sweep has run.
   #243: a quiet x (Dismiss until the next sweep is due) hides it for the rest of the day. This browser keeps the day and the
   last-swept time it was dismissed for (localStorage creaite-sweepdue-dismissed; kept in memory too, so a blocked store still
   hides it for this page load); it comes back the next day, or when the last-swept time changes and the sweep is due again. */
const SDKEY="creaite-sweepdue-dismissed"; let SDMEM=null;
const sdLast=()=>String((D.sweep_due&&D.sweep_due.last)||"");
function sweepDueDismissed(){ const d=SDMEM||store.get(SDKEY,null); return !!(d&&d.day===TODAY&&d.last===sdLast()); }
export function sweepDueShown(){ const sd=D.sweep_due; return !!(sd&&sd.due)&&!D.dev&&!(setupShown()&&!swept())&&!sweepDueDismissed(); }
export function renderSweepDue(){ const box=$("#sweepDue"); if(!box) return; const on=sweepDueShown(); box.hidden=!on;
  if(!on){ putHTML(box,html``); return; }
  putHTML(box,html`<b>Mail and Teams not checked yet today.</b> <span class="sd-last">${D.sweep_due.last?`Last checked ${fd(String(D.sweep_due.last))}.`:"Not checked yet."}</span> <button type="button" class="btn primary sd-run" id="sweepRun">Check now</button><span class="sd-off">creaite isn't running. Reopen the creaite app, then check now.</span><button type="button" class="ib sd-x" id="sweepX" aria-label="Dismiss until the next check is due" data-tip="Dismiss until the next check is due">${raw(ic("x"))}</button>`); }
document.addEventListener("click",e=>{ if(!e.target.closest("#sweepX")) return; e.preventDefault();   /* #243 */
  const box=$("#sweepDue"), had=box&&box.contains(document.activeElement);
  SDMEM={day:TODAY,last:sdLast()}; store.set(SDKEY,SDMEM); renderSweepDue();
  if(had||document.activeElement===document.body){ const v=$("#v-today"), nxt=v&&[...v.querySelectorAll("a[href],button:not([disabled]),input:not([disabled]),select,textarea,[tabindex]:not([tabindex='-1'])")]
      .find(n=>!!(box.compareDocumentPosition(n)&Node.DOCUMENT_POSITION_FOLLOWING)&&n.offsetParent!==null);
    if(nxt) nxt.focus(); else if(v){ if(!v.hasAttribute("tabindex")) v.setAttribute("tabindex","-1"); v.focus(); } } });
document.addEventListener("click",e=>{ if(!e.target.closest("#sweepRun")) return; e.preventDefault();
  if(!viaServer()){ snack("creaite isn't running"); return; }
  if(shared.BUSY){ snack("ask creaite is busy; try again when it's finished"); return; } openChat(); send("sweep"); });
/** v2.6 (the Settings line): Add a project opens the Projects page; there (its empty state's button) it starts “add project ” in
    ask creaite, unsent, as Settings › Projects and register used to say: a project is added in plain English (cx-edit). */
export function addProject(){ if(shared.VIEW!=="projects"){ go("projects"); return; }
  openChat(); const i=/** @type {HTMLTextAreaElement|null} */($("#chIn")); if(i){ if(!i.value.trim()) i.value="add project "; i.focus(); } }
export function bootToday0159(){
document.addEventListener("click",e=>{ const b=e.target.closest("[data-tdrev]"); if(!b) return; e.preventDefault(); const [f,r]=/** @type {HTMLElement} */(b).dataset.tdrev.split("|"); tdToReviewRef(f,r); });   /* #236 */
document.addEventListener("click",e=>{ const b=e.target.closest("[data-setup]"); if(!b) return; e.preventDefault(); const a=b.dataset.setup;
  if(a==="dismiss"){ const l=dismissedF(); l.push(SETUPID); store.set("creaite-dismiss",l); writeSettings({"reminders.dismissed_forever":[...new Set([...(D.dismissed||[]),...l])]}); renderSetup();
    snack("Checklist dismissed. Settings › Reminders › Restore brings it back",()=>{ store.set("creaite-dismiss",dismissedF().filter(x=>x!==SETUPID)); renderSetup(); }); return; }
  if(a==="help") go("help","start"); else if(a==="proj") addProject(); else if(a==="people") go("people","all");   /* #248: the People page, Add a person; v2.6: Add a project, below */
  else if(a==="review") go("intake-review"); else if(a==="sweep"){ if(shared.BUSY){ snack("ask creaite is busy; try again when it's finished"); return; } openChat(); send("sweep"); } });
if(shared.VIEW==="today") renderSetup();
}
/* ===== BL-166 (sprint-polish-2) ===== set-up in the dashboard where it can be. The live server runs the steps that are scripts
   on ask creaite's allow list (/api/setup/run: the health check, doctor.py; Rebuild, build_dashboard.py and the Excel export);
   a step that changes something is shown first and runs on Alan's click. What the page can't do says so in one line with Copy
   (the exact thing to say or paste) and Check again: Microsoft 365 is connected in Claude itself, and the launcher is made
   outside the vault by launch.py, which no allow list runs. Settings › System › Set-up holds them all; the first-run checklist's
   Connect Microsoft 365 row has Copy and Check again. Nothing here is a new permission. */
export const SU={status:null,health:null,confirm:false,busy:""};
const suRead=onceFor(2000,async()=>{ const r=await api("/api/setup/status",{}); if(r&&r.ok){ SU.status=r; if(r.swept&&(!D.last_sweep||D.last_sweep==="never")) D.last_sweep=r.swept; } return SU.status; });   /* #96: one read for callers that arrive together */
export async function suStatus(force){ if(!viaServer()) return null; return suRead(force); }
export async function suCopy(text,btn){ try{ if(!navigator.clipboard) throw 0; await navigator.clipboard.writeText(text); copied(btn); snack("Copied"); }catch(e){ prompt("Copy this:",text); } }
export const suCmd=(text,id,check)=>`<div class="sucmd"><code>${esc(text)}</code><button type="button" class="mini" data-sucopy="${id}">Copy</button>${check?`<button type="button" class="mini" data-sucheck="${id}" ${viaServer()?"":'disabled title="creaite isn’t running"'}>Check again</button>`:""}</div>`;
export const suText=id=>id==="m365"?SU_M365:id==="launch"?SU_LAUNCH():SU_SETUP;
export function suHealthHtml(){ const h=SU.health; if(!h) return "";
  const li=l=>{ const k=l.slice(0,4); return `<li><span class="k ${k.toLowerCase()}">${k}</span><span>${esc(l.slice(4).trim())}</span></li>`; }, L=h.lines.filter(l=>/^(PASS|WARN|FAIL)\s/.test(l));
  const bad=L.filter(l=>!l.startsWith("PASS")), ok=L.filter(l=>l.startsWith("PASS"));   /* what needs attention first; the passes folded */
  return `<div class="sub" role="status">${esc(h.lines[h.lines.length-1]||"")}</div>${bad.length?`<ul class="sures" aria-label="Needs attention">${bad.map(li).join("")}</ul>`:""}<details class="sures"><summary>${ok.length} passed</summary><ul class="sures">${ok.map(li).join("")}</ul></details>`; }
export function suCardHtml(){ const st=SU.status||{}, live=viaServer(), off=live?"":'disabled title="creaite isn’t running"';
  const swept=st.swept||(D.last_sweep&&D.last_sweep!=="never"?D.last_sweep:null);
  return `<div class="card" id="suCard" data-sec="setup"><h2>Set-up</h2><p class="sub">The set-up steps the page can do, and the two it can’t. Each runs on your click; nothing here is a new permission.</p>
   ${row("Health check",`<button type="button" class="btn" id="suHealth" ${off}>${SU.busy==="health"?"Checking…":"Run the health check"}</button>`,"Checks creaite's set-up; it only reads")}
   ${suHealthHtml()?`<div id="suHealthOut">${suHealthHtml()}</div>`:""}
   ${row("Rebuild the dashboard and Excel view",`<button type="button" class="btn" id="suRebuild" ${off}>${SU.busy==="rebuild"?"Rebuilding…":"Rebuild…"}</button>`,"From your project record; nothing in it changes")}
   ${SU.confirm?`<div class="sushown" id="suConfirm">This rebuilds the dashboard and the Excel view from your project record. If the workbook has edits you haven’t imported, it is left as it is. <span class="suacts" style="margin-top:6px"><button type="button" class="btn" data-sucancel>Cancel</button><button type="button" class="btn primary" id="suRebuildGo">Rebuild now</button></span></div>`:""}
   ${row("Microsoft 365",swept?`<span class="h-ok">Connected</span>`:`<span class="sub">Not confirmed yet</span>`,swept?`The mail and Teams check last read your mail ${esc(fd(String(swept).slice(0,10)))}`:"Connected in Claude itself, so the page can’t do it: connect Microsoft 365 there (Settings › Connectors), then ask Claude to check it. The first mail and Teams check confirms it")}
   ${swept?"":`<div class="sucmd"><button type="button" class="mini" data-sucheck="m365" ${viaServer()?"":'disabled title="creaite isn\'t running"'}>Check again</button></div>`}
   ${row("Launcher",st.launcher?`<span class="h-ok">Made</span>`:`<span class="sub">Not made yet</span>`,st.launcher?`${esc(st.launcher)}: double-click it to open creaite`:"A small app that opens creaite in its own window and starts creaite. It goes outside your creaite folder, so the page can’t make it: Settings › Health › Diagnostics has the one step")}
   ${st.launcher?"":`<div class="sucmd"><button type="button" class="mini" data-sucheck="launch" ${viaServer()?"":'disabled title="creaite isn\'t running"'}>Check again</button></div>`}
   ${row("The rest of set-up","","Your name and role are in Settings › Essentials. The projects folder, git and the optional schedules are a conversation: ask Claude to set creaite up.")}</div>`; }
export function suRedraw(){ const c=$("#suCard"); if(c) swapHTML(c,raw(suCardHtml())); }
export async function suCheck(what,btn){ if(btn) btn.disabled=true; const r=await suStatus(true); if(btn&&btn.isConnected) btn.disabled=false;
  if(!r){ snack("Checking needs creaite running"); return; }
  if(what==="m365") snack(r.swept?`Microsoft 365 is connected: the mail and Teams check last read your mail ${fd(String(r.swept).slice(0,10))}`:"Not confirmed yet: the first mail and Teams check confirms it, as it reads your mail");
  else snack(r.launcher?`The launcher is made: ${r.launcher}`:"No launcher yet: Settings › Health › Diagnostics has the one step, then check again");
  suRedraw(); if(shared.VIEW==="today") renderSetup(); }
/* ===== end BL-166 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootToday0164(){
SETSECTIONS.splice(SETSECTIONS.findIndex(s=>s.id==="live")+1,0,{id:"setup",cat:"health",title:"Set-up",raw:true,kw:"setup set-up health check doctor launcher microsoft 365 connect rebuild excel first run",
  render:()=>suCardHtml(),after:()=>{ suStatus().then(()=>{ if(shared.VIEW==="settings") suRedraw(); }); }});
document.addEventListener("click",async e=>{ const t=e.target;
  const cp=t.closest("[data-sucopy]"); if(cp){ e.preventDefault(); suCopy(suText(cp.dataset.sucopy),cp); return; }
  const ck=t.closest("[data-sucheck]"); if(ck){ e.preventDefault(); suCheck(ck.dataset.sucheck,ck); return; }
  if(t.closest("#suHealth")){ if(SU.busy) return; SU.busy="health"; suRedraw(); const r=await api("/api/setup/run",{step:"health"}); SU.busy="";
    if(r&&r.ok){ SU.health=r; snack(r.passed?"Health check passed":"Health check: something needs attention"); } else snack(oneLine(r&&r.message)||"The health check didn't run"); suRedraw(); return; }
  if(t.closest("#suRebuild")){ SU.confirm=true; suRedraw(); $("#suRebuildGo")?.focus(); return; }
  if(t.closest("[data-sucancel]")){ SU.confirm=false; suRedraw(); return; }
  if(t.closest("#suRebuildGo")){ if(SU.busy) return; SU.confirm=false; SU.busy="rebuild"; suRedraw(); const r=await api("/api/setup/run",{step:"rebuild"}); SU.busy=""; suRedraw();
    snack(oneLine(r&&r.message)||"The rebuild didn't run"); return; } });
/* the checklist: Connect Microsoft 365 says why it can't be done here, with Copy and Check again (and How, which opens Help) */
document.addEventListener("click",e=>{ const a=e.target.closest("[data-setopen]"); if(a){ e.preventDefault(); go("settings",a.dataset.setopen); } });
if(viaServer()) suStatus().then(()=>{ if(shared.VIEW==="today") renderSetup(); });
}
/* ===== BL-319 (v1.9.2): Today as one home =====
   (dev/mockups/today-one-home-mockup.html, tab "Today, one home"). The day band stays exactly as BL-293 drew it, at full width;
   under it, at a 980px reading width, the sections in order and unboxed: First thing, Decisions needed, Needs
   attention, Your commitments (with You owe and Waiting on, and #245's one quiet Intake line at its foot), Messages (BL-334; was To decide, then Intake and Review), Week ahead, Resolved (folded to one line) and Portfolio. Each
   row's actions are icons (IconButton, or tib for the rows still drawn as text), named on hover and to a screen reader,
   55% until the row is pointed at or tabbed into; nothing moves. Every change has Undo: an approval or a rejection the
   apply's Undo, a dismissed message its own, Mark done and Move the date the staged change's (Undo last). */
/** an icon button in a text-drawn row: `label` on hover, `name` to a screen reader; `why` blocks it (aria-disabled, the reason as its tooltip) */
export function tib(icon,label,name,attrs="",primary=false,why=""){
  return `<button type="button" class="ib sm${primary?" pri":""}" aria-label="${esc(name||label)}" data-tip="${esc(why||label)}"${why?' aria-disabled="true"':""} ${attrs}>${ic(icon)}</button>`; }
export const TDCAP=5;
/** when a proposal was made ("YYYY-MM-DD HH:MM"), from its file name */
export const revAt=r=>{ const w=String(r.file||"").match(/^proposed-(\d{4}-\d{2}-\d{2})-(\d{2})(\d{2})/); return w?`${w[1]} ${w[2]}:${w[3]}`:""; };
/** "14:02" today, "Monday 12th October, 09:30" before */
export const whenWords=at=>!at?"":at.slice(0,10)===TODAY?at.slice(11,16):`${longDay(at.slice(0,10))}${at.length>10?", "+at.slice(11,16):""}`;
const revSrc=r=>/-sweep(-\d+)?\.json$/.test(r.file)?"sweep":/-(dashboard|edit)(-\d+)?\.json$/.test(r.file)?"your edits":/-excel(-\d+)?\.json$/.test(r.file)?"Excel import"
  :REV.some(x=>x.file===r.file&&x.kind==="draft"&&x.ref==="meeting")?"minutes":"proposal";
/** a meeting whose transcript is ready (Intake's calendar import, #245; the old Intake page's own test, kept here since #232 retired it) */
export const txReady=/** @param {any} m */m=>m.transcript==="available"&&!m.processed&&!m.draft;
const tdTag=r=>r.kind==="draft"?(r.ref==="meeting"?"Minutes":"Report"):kindLabel(r)||"Proposal";
/** the Messages section's rows (BL-319 called it To decide, #168 Intake and Review), newest first: messages from people Alan follows (never labelled) */
export function toDecideRows(){ const live=viaServer(), tdl=/** @type {any[]} */([]); void live;
  /* #208 (Alan, 17-10-2026): proposals in Review and transcripts in Intake are not listed here; #245: intakeParts() counts them, in a line under Your commitments */
  VIPCARDS().forEach(a=>{ if("summary" in a){ tdl.push(convRow(a)); return; }   /* BL-334: a conversation's card (a confidential one too, marked) */
    const at=String(a.sent||"").replace("T"," ").slice(0,16), name=`${a.who??""}, ${a.subject??""}`;
    tdl.push({key:"al"+a.id,kind:"message",id:a.id,at,tag:"Message",tone:"warn",t:`${a.who??""}: ${a.subject??""}`,link:a.link||"",mark:confMark(a),
      meta:[`${VIPKIND[a.kind]||"Message"}${vipWhen(a)?" "+vipWhen(a):""}`,a.p&&a.p!=="_portfolio"?pName(a.p):"no project",confMark(a)?"":a.marker||"",a.found==="start-up"?`found on start-up, received ${vipWhen(a)}`:""].filter(Boolean).join(" · ")+(a.gist?`. ${a.gist}`:""),
      acts:[{id:"make",icon:"plus",label:"Make a work item",name:`Create work item from: ${name}`,data:{alertdo:"make",id:a.id}},
            {id:"dismiss",icon:"dismiss",label:"Dismiss",name:`Dismiss: ${name}`,data:{alertdo:"dismiss",id:a.id}}]}); });
  VIPQ().forEach(a=>tdl.push(quietRow(a)));                                     /* BL-334: nothing for Alan: one quiet line */
  VIPR().forEach(a=>tdl.push(repliedRow(a)));                                   /* BL-342: he answered: one quiet line */
  /* BL-342: a card past its due date first (oldest due first), then everything newest first as before */
  return tdl.map((x,i)=>({x,i})).sort((a,b)=>(a.x.overdue?0:1)-(b.x.overdue?0:1)||(a.x.overdue&&b.x.overdue?a.x.due.localeCompare(b.x.due):0)||b.x.at.localeCompare(a.x.at)||a.i-b.i).map(o=>o.x); }
/* ----- BL-334: a conversation, not a message. One card per conversation: its own title (or the people in it), where it is,
   "updated HH:MM", Claude's summary, then each candidate item with Create work item and Dismiss (Dismiss stages nothing). A
   conversation with nothing for Alan is one quiet line with only Seen (#276). Never labelled (BL-288). ----- */
const CTYPE=/** @type {Record<string,string>} */({action:"Action",decision:"Decision",risk:"Risk"});
/** BL-342: the one thing a thread asks of Alan, as its chip says it */
export const CARDTYPE=/** @type {Record<string,string>} */({action:"Action",decision:"Decision",fyi:"FYI / file",risk:"Risk"});
/** "Confidential" on a confidential conversation's card or message (Alan, 15-10-2026, plan #17): its summary is shown like any
    other, internal only; never the word that says how the sender is followed (BL-288) @param {any} a */
export const confMark=a=>a.confidential||a.marker==="confidential"?"Confidential":"";
const convAt=a=>String(a.last||a.sent||"").replace("T"," ").slice(0,16);
/* "updated" is when the conversation's last message was sent, not when the check recorded it (plan #81); an older record
   without that time falls back to when it was recorded */
const convWhen=a=>String(a.last||a.updated||"").replace("T"," ").slice(0,16);
const convMeta=a=>[`${VIPKIND[a.kind]||"Message"}${convWhen(a)?" · updated "+whenWords(convWhen(a)):""}`,a.p&&a.p!=="_portfolio"?pName(a.p):"no project",
  a.found==="start-up"?"found on start-up":"",a.match&&a.match.logged?`Logged on ${a.match.id}${a.match.logged.state==="applied"?"":", staged for Review"}`:""].filter(Boolean).join(" · ");
/** #236 (Alan, 19-10-2026): the followed-person alerts that are Needs attention rows, not To decide cards: what the sweep pulled out of a
    message (a proposal row, a memory-note row) and a private conversation @param {any} a */
export const attnAlert=a=>a.kind==="proposal"||a.kind==="note"||a.marker==="private";
/** the cards that stay in To decide (BL-334, BL-342) */
export const VIPCARDS=()=>VIPS().filter(a=>!attnAlert(a));
/** the review row of a staged item or block (a note's is the file-change row), by file and item number @param {string} file @param {any} ref */
export const refReview=(file,ref)=>REV.find(x=>x.file===file&&String(x.ref)===String(ref)&&!x.done);
const rvAttr=/** @param {any} r */r=>`data-tdrev="${esc(String(r.file||""))}|${esc(String(r.ref))}"`;
const alWhen=/** @param {any} a */a=>String(a.returned||a.sent||a.updated||"").replace("T"," ").slice(0,16);
/** the rows, newest first @returns {any[]} */
export function attnAlertItems(){ return VIPS().filter(attnAlert).sort((a,b)=>alWhen(b).localeCompare(alWhen(a))).map(a=>({alert:a.id,html:/** @param {number} n */n=>attnAlertHtml(n,a)})); }
/** #236: "From <person>": the proposals the sweep staged from a followed person's mail or chat, or a note about it written into a project's memory.
    Its title, each line and the Open in Review icon go to the proposal or note; Dismiss keeps it gone until the thread adds a new item or changes
    an active one. Never labelled (BL-288). A private conversation, or a private thread, is its title and times only. @param {number} n @param {any} a */
export function attnAlertHtml(n,a){ const refs=/** @type {any[]} */(a.refs||[]), first=refs[0]||{}, t=String(a.title||a.subject||"Conversation"), when=alWhen(a);
  const attrs=`class="alrow" data-al="${esc(a.id)}"`, dis=(name)=>tib("dismiss","Dismiss",name,`data-alertdo="dismiss" data-id="${esc(a.id)}"`);
  if(a.marker==="private"){ const ext=a.link?linkAnchor(a.link,esc(t),"t"):null;
    return tl(n,ext||(first.file?tLink(rvAttr(first),esc(t)):`<span class="t">${esc(t)}</span>`),when?`updated ${esc(whenWords(when))}`:"",`<span class="tacts">${dis(`Dismiss: ${t}`)}</span>`,attrs); }
  const note=a.kind==="note", inRev=refs.filter(r=>refReview(r.file,r.ref)), cnt=refs.length, proj=a.p&&a.p!=="_portfolio"?pName(a.p):"no project";
  const what=note?(inRev.length?`A note for ${proj}'s memory, in Review`:`A note for ${proj}'s memory, waiting: saved at the next save`):`${cnt} suggestion${cnt===1?"":"s"} in Review`;
  const lines=a.marker==="confidential"?[]:refs.map(r=>{ const x=refReview(r.file,r.ref);   /* a confidential thread: the title, the mark and the times, no item words */ return x?`${esc(r.tag?r.tag[0].toUpperCase()+r.tag.slice(1):"Item")}: ${sLink(rvAttr(r),esc(String(x.rec&&x.rec.t||"")))}`:""; }).filter(Boolean);
  const meta=[what,note?"":proj,a.sent?`sent ${whenWords(String(a.sent).replace("T"," ").slice(0,16))}`:"",confMark(a),a.returned?"new since you dismissed it":""].filter(Boolean).map(esc).join(" · ");
  const name=`From ${a.who??""}, ${t}`;
  return tl(n,tLink(rvAttr(first),esc(`From ${a.who??""}: ${t}`)),meta+(lines.length?`. ${lines.join("; ")}`:""),
    `<span class="tacts">${tib("external","Open in Review",`Open in Review: ${name}`,rvAttr(first))}${dis(`Dismiss: ${name}`)}</span>`,attrs); }
/** the proposal or note a followed person's row points at, in Review (highlighted); Review itself when it is not pending there @param {string} file @param {any} ref */
export function tdToReviewRef(file,ref){ const r=refReview(file,ref)||REV.find(x=>x.file===file&&!x.done); if(r) tdToReview(r.n); else go("review"); }
/** BL-342 Part 2: how a thread relates to open work */
const RELCHIP=/** @type {Record<string,string>} */({new:"New",update:"Update",chase:"Chase"});
/** BL-342: a card's due date as the row shows it, and whether it is past @param {any} a */
const cardDue=a=>a.due?{text:`due ${longDay(a.due)}`,over:a.due<TODAY}:null;
/** @param {any} a */
export function convRow(a){ const t=String(a.title||a.subject||"Conversation");
  const cands=(a.candidates||[]).filter(/** @param {any} c */c=>!c.made&&!c.dismissed).map(/** @param {any} c */c=>({key:`c${c.n}`,tag:CTYPE[c.type]||"Item",t:String(c.text||""),
    sub:[c.owner||"",c.due?`due ${fd(c.due)}`:""].filter(Boolean).join(" · "),
    acts:[{id:"make",icon:"plus",label:"Create work item",name:`Create work item: ${c.text}`,data:{alertdo:"make",id:a.id,cand:String(c.n),ctype:c.type}},
          {id:"dismiss",icon:"dismiss",label:"Dismiss",name:`Dismiss: ${c.text}`,data:{alertdo:"dismiss",id:a.id,cand:String(c.n)}}]}));
  /* BL-342: the type chip, the ask, the due date and the owners; Handled on every card, Log on the matched item when there is one */
  const due=cardDue(a), name=`${a.who??""}, ${t}`, acts=[{id:"handled",icon:"done",label:"Handled",name:`Handled: ${name}`,data:{alertdo:"handled",id:a.id}}];
  const m=a.match&&a.match.id&&a.match.relation!=="new"?String(a.match.id):"";
  if(m&&!(a.match&&a.match.logged)) acts.push({id:"log",icon:"filetext",label:`Log on ${m}`,name:`Log on ${m}: ${t}`,data:{alertdo:"log",id:a.id}});
  /* BL-342 Part 2: the New / Update / Chase chip with the matched item, the count of other threads on it, and Chase for its owner */
  const mt=a.match&&a.match.relation?a.match:null, rel=mt?RELCHIP[mt.relation]||"":"", others=mt&&mt.id&&mt.count>1?mt.count-1:0;
  if(mt&&mt.relation==="chase"&&mt.id) acts.push({id:"chase",icon:"chasemail",label:"Chase",name:`Chase the owner of ${mt.id}: ${t}`,data:{alertdo:"chase",id:a.id}});
  /* BL-342 Part 3 B, step 9: "Looks done: close ABC-A-007" beside Log, when the check offered a close the code kept; once
     staged, "Staged for Review" with Undo. Hidden on a private card, a New match or an item no longer open. */
  const cl=cardClose(a,mt);
  if(cl&&!cl.staged) acts.push({id:"close",icon:"checks",label:`Looks done: close ${cl.id}`,name:`Stage a close of ${cl.id} for Review`,data:{alertdo:"close",id:a.id}});
  /* BL-342 Part 5: a promise of the project that looks kept: "Looks kept: mark kept" beside Log; once staged, Staged for Review with Undo */
  const kp=cardKept(a);
  if(kp&&!kp.staged) acts.push({id:"kept",icon:"checks",label:"Looks kept: mark kept",name:`Stage ${kp.id} as kept for Review`,data:{alertdo:"kept",id:a.id}});
  const files=a.type==="fyi"&&(a.attachments||[]).length?`Files: ${(a.attachments||[]).slice(0,4).join(", ")}${a.attachments.length>4?` and ${a.attachments.length-4} more`:""}`:"";
  return {key:"al"+a.id,kind:"message",id:a.id,at:convAt(a),tag:CARDTYPE[a.type]||"Message",tone:"warn",t,link:a.link||"",mark:confMark(a),meta:convMeta(a),summary:String(a.summary||""),cands,acts,
    rel,relId:mt&&mt.id&&mt.relation!=="new"?String(mt.id):"",relT:mt&&mt.id&&mt.relation!=="new"?String(mt.t||""):"",relWhy:mt?String(mt.why||""):"",
    count:others?`also on ${others} other thread${others===1?"":"s"}`:"",ask:String(a.ask||""),due:a.due||"",overdue:!!(due&&due.over),dueText:due?due.text:"",owners:(a.owners||[]).join(", "),files,
    closeWhy:cl?`Looks done: ${confMark(a)?"the thread shows it finished":String(cl.evidence||"").replace(/\.$/,"")}`:"",closeStaged:cl&&cl.staged?String(cl.id):"",closeCard:cl?a.id:"",
    proms:cardPromises(a),keptWhy:kp?`Looks kept: ${kp.id}, ${confMark(a)?"the thread shows it done":String(kp.evidence||"").replace(/\.$/,"")}`:"",keptStaged:kp&&kp.staged?String(kp.id):"",keptCard:kp?a.id:""}; }
/** BL-342 Part 5: the promises Alan made in his own messages in the thread, each with Add a promise and Dismiss (by the card's ID
    and the promise's key, never its position or words); a staged one says so, with Undo. None on a private card. @param {any} a */
export function cardPromises(a){ if(a.marker==="private") return [];
  return (a.promises||[]).filter(/** @param {any} p */p=>p&&p.key&&(p.state==="offered"||p.state==="staged")).map(/** @param {any} p */p=>({key:`p${p.key}`,pkey:String(p.key),card:String(a.id),tag:"Promise",
    t:`You promised ${p.to||"someone"}: ${p.what||""}`,sub:p.due?`by ${fd(p.due)}`:"no date given",staged:p.state==="staged",
    acts:p.state==="staged"?[]:[{id:"padd",icon:"plus",label:"Add a promise",name:`Add a promise: ${p.what||""}`,data:{alertdo:"promise",id:a.id,pkey:String(p.key)}},
      {id:"pdismiss",icon:"dismiss",label:"Dismiss",name:`Dismiss the promise: ${p.what||""}`,data:{alertdo:"promisedismiss",id:a.id,pkey:String(p.key)}}]})); }
/** BL-342 Part 5: the card's kept promise, when it may be shown: not private and the promise still open (the server marks
    open: false once it isn't) @param {any} a */
export function cardKept(a){ const k=a.kept; return k&&k.id&&a.marker!=="private"&&k.open!==false?k:null; }
/** BL-342 Part 3 B: the card's close suggestion, when it may be shown: not private, matched (not New) to that same action, and the
    action still open in the page data @param {any} a @param {any} mt */
export function cardClose(a,mt){ const c=a.closes;
  if(!c||!c.id||a.marker==="private"||!mt||mt.relation==="new"||mt.id!==c.id) return null;
  const it=A.find(x=>x.id===c.id); return it&&open(it)?c:null; }
/** "Mia Hale with Omar Ali: you replied 14:02" @param {any} a */
export function repliedRow(a){ const others=(a.people||[]).filter(/** @param {string} p */p=>p!==a.who);
  return {key:"al"+a.id,kind:"quiet",id:a.id,at:String(a.replied_at||convAt(a)),tag:"Replied",tone:"",t:`${a.who||""}${others.length?" with "+others.slice(0,3).join(", "):""}: you replied ${whenWords(String(a.replied_at||""))}`,
    link:a.link||"",meta:convMeta(a),acts:seenActs(a)}; }
/** #276: a quiet line's one action, Seen (the eye): it clears the line for good (/api/vip/seen), with Undo @param {any} a */
export const seenActs=a=>[{id:"seen",icon:"eye",label:"Seen",name:`Seen: ${a.who||""}${a.title?", "+a.title:""}`,data:{alertdo:"seen",id:a.id}}];
/** "Mia Hale with Omar Ali: nothing for you" @param {any} a */
export function quietRow(a){ const others=(a.people||[]).filter(/** @param {string} p */p=>p!==a.who);
  return {key:"al"+a.id,kind:"quiet",id:a.id,at:convAt(a),tag:"",tone:"",t:`${a.who||""}${others.length?" with "+others.slice(0,3).join(", "):""}: nothing for you`,
    link:a.link||"",meta:convMeta(a),acts:seenActs(a)}; }
/** where focus goes after a row's action takes the row away: the same action on the row now in its place, else the heading */
let TDFOCUS=/** @type {{i:number,what:string,at:number}|null} */(null);
export function tdFocusAfter(){ const f=TDFOCUS; if(!f||Date.now()-f.at>8000){ TDFOCUS=null; return; }
  const a=document.activeElement; if(a&&a!==document.body&&a.isConnected) return;
  const L=$$("#tdList > li").filter(l=>!l.hidden), li=L[Math.min(f.i,L.length-1)], b=li&&(li.querySelector(`[data-tdact="${f.what}"]`)||li.querySelector("[data-tdact]"));
  TDFOCUS=null; if(b){ /** @type {HTMLElement} */(b).focus(); return; } const h=$("#hTd")||$("#hAttn"); if(h&&h.offsetParent){ h.tabIndex=-1; h.focus(); } }
export function tdFocusMark(key,what){ const i=$$("#tdList > li").filter(l=>!l.hidden).findIndex(l=>l.dataset.td===key); TDFOCUS={i:Math.max(0,i),what,at:Date.now()}; }
/** a proposal's row in Review, highlighted (as First thing opens one) */
export function tdToReview(n){ go("intake-review"); const r=REV.find(x=>x.n===n&&!x.done); if(r) irReveal([r.n]); }   /* #232-C: the meeting it came from opens */
/* ----- #245 (v2.5.2): Intake as one quiet line at the foot of Your commitments (replaces the Intake and Review section, its
   fold and #208's line). The counts are the pages': proposals waiting in Review (the rail's badge), the meetings whose transcript is
   ready in Intake's calendar import, and new files in Intake. Counts only: a confidential meeting is counted and never named. ----- */
/** the place a phrase of the line opens (#232, v2.6: Review is part of Intake, one page): proposals go to its "To approve" stage (drafted), meetings and new files to its "Arrived" stage; renderIntakeLine splits the address into a page and a stage */
export const intakeTarget=/** @param {string} key */key=>key==="proposals"?"intake-review&stage=drafted":"intake-review&stage=arrived";
/** @returns {{key:string,n:number,text:string,go:string}[]} meetings first, then proposals, then new files; none at zero */
export function intakeParts(){ const pr=REV.filter(r=>!r.done).length, nTr=MTG().filter(txReady).length, fl=irFreshFiles().ready.length, L=[];   /* the files the rail's badge counts: ready ones, not a transcript already loaded for a meeting */
  if(nTr) L.push({key:"meetings",n:nTr,text:`${nTr} meeting${nTr===1?"":"s"} ready to process`,go:intakeTarget("meetings")});
  if(pr) L.push({key:"proposals",n:pr,text:`${pr} suggestion${pr===1?"":"s"} to approve`,go:intakeTarget("proposals")});
  if(fl) L.push({key:"files",n:fl,text:`${fl} new file${fl===1?"":"s"} to process`,go:intakeTarget("files")});
  return L; }
/* The x hides the line until something new arrives or the next morning. This browser keeps the day and, per kind, which items were
   waiting when it was pressed (localStorage creaite-intakeline-dismissed): never text, only a short hash of each item's id (a
   proposal's file, item and created time, as minutes.py may reuse a file name a minute later; a meeting's calendar key; an Intake
   file's path), at most TQCAP a kind. An item waiting now that is not in its kind's set is new and shows the line again; what has
   gone since needs nothing (a set, not a count, so approving older ones never hides a newer one, and a swap is new). A kind longer
   than TQCAP also keeps one digest of its whole set (order-independent, with its size): the line stays hidden when everything
   waiting is in the kept list or the set is the very one dismissed, and shows otherwise. So a swap is never hidden; the cost of
   the cap is only that, past it, approving one of the items left out of the list can show the line again. Kept in memory too, so a store that can't be read or written still hides it
   for this page load, as the Sweep due banner's x does. */
const TQKEY="creaite-intakeline-dismissed", TQCAP=200, TQKINDS=["meetings","proposals","files"];
/** @typedef {{day:string,ids:Record<string,string[]>,all?:Record<string,string>}} TqKept */
let TQMEM=/** @type {TqKept|null} */(null), TQSTUCK=false;   /* TQSTUCK: the last write failed, so the memory is newer than the store */
/** a short, stable hash of an id (FNV-1a, 32 bits, 8 hex digits): the store holds no title, file name or other text */
const tqHash=/** @param {string} s */s=>{ let h=0x811c9dc5; for(let i=0;i<s.length;i++){ h^=s.charCodeAt(i); h=Math.imul(h,0x01000193); } return (h>>>0).toString(16).padStart(8,"0"); };
/** each kind's waiting ids, hashed: what intakeParts() counts, item by item */
function intakeIds(){ return {
  meetings:MTG().filter(txReady).map(m=>tqHash("m|"+(m.key||m.id||`${m.day}|${m.start}|${m.title}`))),
  proposals:REV.filter(r=>!r.done).map(r=>tqHash("p|"+(r.file!=null?`${r.file}#${r.ref}|${r.made||""}`:`n${r.n}`))),
  files:irFreshFiles().ready.map(f=>tqHash("f|"+(f.path||f.name))) }; }
/* localStorage is the truth on every read, so two tabs agree (what one dismisses the other reads at its next redraw, and at once on a
   storage event); the memory is read instead when the store can't be read, or when this page's last write to it failed (a store
   that reads but won't write). All storage in try/catch. */
function tqRead(){ if(TQSTUCK) return TQMEM; try{ const v=localStorage.getItem(TQKEY); return v?JSON.parse(v):null; }catch(e){ return TQMEM; } }
/** @returns {boolean} whether the store took it (the memory has it either way) */
function tqWrite(d){ TQMEM=d; try{ localStorage.setItem(TQKEY,JSON.stringify(d)); TQSTUCK=false; return true; }catch(e){ TQSTUCK=true; return false; } }
/** one hash of a whole set of hashed ids, whatever their order, with its size: "1a2b3c4d:250" */
const tqDigest=/** @param {string[]} l */l=>`${tqHash([...l].sort().join(","))}:${l.length}`;
/** what the x keeps: today and each kind's ids, the last TQCAP of a longer list (and then the digest of the whole set) */
function tqKeep(){ const now=intakeIds(), ids=/** @type {Record<string,string[]>} */({}), all=/** @type {Record<string,string>} */({});
  TQKINDS.forEach(k=>{ const l=[...new Set(now[k])]; ids[k]=l.slice(-TQCAP); if(l.length>TQCAP) all[k]=tqDigest(l); });
  return Object.keys(all).length?{day:TODAY,ids,all}:{day:TODAY,ids}; }
/* hidden only when, for every kind, each id waiting now is in the kept list, or the set waiting now is the whole set dismissed
   (an older entry's "over" count is not read: such an entry can only show the line, never hide a new item) */
function intakeDismissed(){ const d=tqRead(); if(!d||d.day!==TODAY||!d.ids||typeof d.ids!=="object") return false;
  const now=intakeIds();
  return TQKINDS.every(k=>{ const l=[...new Set(now[k])], kept=new Set(Array.isArray(d.ids[k])?d.ids[k]:[]);
    return l.every(h=>kept.has(h))||(!!d.all&&typeof d.all[k]==="string"&&d.all[k]===tqDigest(l)); }); }
export function renderIntakeLine(){ const host=$("#tdQuietHost"); if(!host) return;
  const parts=intakeParts(), hid=parts.length>0&&intakeDismissed();
  drawIntakeLine(host,hid?[]:parts,pg=>{ const [v,st]=pg.split("&stage="); go(v,st?{stage:st}:undefined); }); }
document.addEventListener("click",e=>{ const x=e.target.closest&&e.target.closest("#tdQx"); if(!x) return; e.preventDefault();
  const host=$("#tdQuietHost"), had=host&&host.contains(document.activeElement);
  tqWrite(tqKeep()); renderIntakeLine();
  if(had||document.activeElement===document.body){ const v=$("#v-today"), nxt=v&&host&&[...v.querySelectorAll("a[href],button:not([disabled]),input:not([disabled]),select,textarea,[tabindex]:not([tabindex='-1'])")]
      .find(n=>!!(host.compareDocumentPosition(n)&Node.DOCUMENT_POSITION_FOLLOWING)&&n.offsetParent!==null);
    if(nxt) nxt.focus(); else if(v){ if(!v.hasAttribute("tabindex")) v.setAttribute("tabindex","-1"); v.focus(); } } });
window.addEventListener("storage",e=>{ if(e.key===TQKEY||e.key===null) renderIntakeLine(); });   /* another tab dismissed it (or cleared the store) */
/** the Messages section (BL-334's cards of messages from people Alan follows); it was Intake and Review's list (#245) */
export function renderToDecide(){ const sec=$("#tdSec"), body=$("#tdBody"); if(!sec||!body) return;
  const L=toDecideRows(), n=L.filter(r=>r.kind!=="quiet").length; sec.hidden=!L.length;
  $("#nTd").textContent=n?String(n):"";                                          /* BL-334: a quiet line isn't counted */
  drawToDecide(body,{rows:L,cap:TDCAP,open:EXPAND.has("td"),blocked:why=>snack(why)});
  requestAnimationFrame(tdFocusAfter); }
/* ----- the Week ahead (BL-72, BL-127, BL-235; BL-319: to next Monday, why each row is there, its icon action) ----- */
/** the actions a piece of work offers (Week ahead, Your commitments): the main one first */
export function workActs(k,x){ const mine=isMe(x.o), owner=!!(x.o&&x.o!=="TBC"), t=x.t||x.id, L=[];
  if(k==="actions"){ if(mine) L.push({id:"done",icon:"done",label:"Mark done",name:`Mark done: ${t}`,primary:true});
    else if(owner) L.push({id:"chase",icon:"chasemail",label:"Draft email",name:`Draft email to ${who(x.o)}: ${t}`,primary:true});
    L.push({id:"move",icon:"calmove",label:"Move the date",name:`Move the date: ${t}`,haspopup:"dialog"}); }
  else if(k==="raid"){ L.push({id:"update",icon:"pencil",label:"Write an update",name:`Write an update: ${t}`,primary:true});
    if(!mine&&owner) L.push({id:"chase",icon:"chasemail",label:"Draft email",name:`Draft email to ${who(x.o)}: ${t}`}); }
  else if(k==="decisions"){ if(mine) L.push({id:"decide",icon:"flag",label:"Record the decision",name:`Record the decision: ${t}`,primary:true});
    else if(owner) L.push({id:"chase",icon:"chasemail",label:"Draft email",name:`Draft email to ${who(x.o)}: ${t}`,primary:true}); }
  else if(k==="milestone") L.push({id:"open",icon:"external",label:"Open the project",name:`Open ${pName(x.p)}, for ${t}`});
  return L; }
/** the same actions as icon buttons in a text-drawn row (Your commitments) */
export function itemActs(k,x){ return `<span class="tacts">${workActs(k,x).map(a=>tib(a.icon,a.label,a.name,`data-tdo="${a.id}" data-k="${k}" data-id="${esc(x.id)}"${a.haspopup?` aria-haspopup="${a.haspopup}"`:""}`,a.primary)).join("")}</span>`; }
/** do one: each change is staged with Undo; a chase, an update and a decision open where they are written */
export async function workAct(k,id,what,btn){ const x=REC(k,id); if(!x&&what!=="open") return;
  if(what==="done"){ const was=x.st; if(!await pkCommit(k,id,{st:"Closed",closed:TODAY},"Status",was,"Closed")) return;
    snack(`${id} marked done. Staged: nothing reaches the tracker until you apply`,()=>pkUndoLast()); return; }
  if(what==="move"){ const commit=async v=>{ if(!v||v===x.due) return; const was=x.due;   /* BL-316: the Picker block's calendar */
      if(!await pkCommit(k,id,{due:v},"Due date",fd(was)||"none",fd(v)||"none")) return;
      snack(`${id} moved to ${longDay(v)}. Staged until you apply`,()=>pkUndoLast()); };
    openDatePicker(btn,{value:x.due||"",label:`Due date of ${id}`,parse:t=>parseWhen(t,TODAY,true),weekend:iso=>!!weekendNote(iso),
      error:"Use DD-MM-YYYY, for example 14-10-2026, or words like fri or +3d.",
      typedNote:t=>{ const n=weekendNote(t?parseWhen(t,TODAY,true):null); return n?`${n.text} You'll be offered the nearest working days.`:""; },
      onPick:v=>{ if(v&&!WK.ok&&wkAsk(v,btn,commit)) return; commit(v); }}); return; }
  if(what==="chase"){ if(k==="decisions"){ dnChase(id); return; } openRecord(k,id); if(chaseCan()) chaseOpen(); return; }
  if(what==="update"){ openRecord(k,id,k==="raid"?"resp":"upd"); return; }
  if(what==="decide"){ dnDecide(id); return; }
  if(what==="open"&&btn&&btn.dataset.p) go("cockpit",btn.dataset.p); }
/** the Week ahead's groups: Urgent with no date, each day, Further ahead.
    #112 (Alan, 16-10-2026): calm rows. Overdue work is not here (it is in Your commitments when it is Alan's, and in the quiet
    line above the days when it is someone else's); nothing already under Your commitments is repeated. */
export function weekGroups(){ const W=D.week; if(!W) return Object.assign(/** @type {any[]} */([]),{above:0});
  const live=viaServer(), out=/** @type {any[]} */([]);
  const above=todayClaims().above, quiet=i=>above.has(i.id);   /* #313: whatever is already listed above (Your commitments, Decisions needed, Needs attention) is not a row again */
  let hidden=0; const only=L=>L.filter(i=>{ if(quiet(i)){ hidden++; return false; } return true; });
  const dotOf=i=>i.pr==="Urgent"?"u":i.pr==="High"?"h":"";
  const whyOf=(i,further,undated)=>{ if(undated) return "no date set";
    const w=i.kind==="decisions"?"needed by":i.weekend?"due over the weekend":"due";
    const d=further&&i.date?` ${longDay(i.date)}`:"";
    return i.kind==="milestone"?(further&&i.date?`${longDay(i.date)} · `:"")+(i.slip?"at risk":"on track"):`${w}${d}`; };
  const msItems=i=>{ const w=msCountWords(i.id,i.t); return w?{ms:i.id,p:i.p,...w}:undefined; };
  const whoOf=i=>i.kind==="milestone"?"":i.kind==="decisions"?(isMe(i.o)?"yours":i.o?`asked of ${who(i.o)}`:"no one asked"):(isMe(i.o)?"yours":who(i.o)||"no owner");
  const item=(i,key,further,undated=false)=>({key,kind:i.kind,type:i.type||"",dot:dotOf(i),t:i.t||i.id,open:i.kind==="milestone"?{ms:i.id}:{open:`${i.kind}:${i.id}`},
    who:whoOf(i),p:i.p||"",pname:i.p?pName(i.p):"",why:whyOf(i,further,undated),whyTone:i.kind==="milestone"&&i.slip?"warn":"",
    items:i.kind==="milestone"?msItems(i):undefined,
    acts:workActs(i.kind,i).map(a=>({...a,data:{k:i.kind,id:i.id,...(i.kind==="milestone"?{p:i.p}:{})}}))});
  const meeting=(e,day)=>{ const can=day!==TODAY&&!!prepOf(e,day), pg=can?prepPageOf(e,day):null, t=e.title??"", key=prepKey(e,day);
    return {key:`m${day}${e.start}${e.title}`,kind:"meeting",time:e.start||"",t,
      open:can?{prepgo:key,prepgoday:day}:undefined,who:e.where||"",p:e.p||"",pname:e.p?pName(e.p):"",why:"",
      chip:can?{made:!!pg,label:pg?"Prep page made":"Prep",aria:`Open the prep page for ${t}`,key,day,live,title:t,start:e.start||"",where:e.where||"",
        pname:e.p?pName(e.p):"",pageWhen:pg?pg.when:"",page:pg?pg.path:null}:undefined,
      acts:[]}; };
  const group=(key,title,L,note)=>{ if(L.length) out.push({key,title,note:note||"",rows:L,cap:6,open:EXPAND.has(key)}); };
  group("wkund","Urgent, with no date",only(W.undated||[]).map((i,n)=>item(i,`u${n}${i.id}`,false,true)));
  (W.days||[]).forEach(d=>{
    group("wk"+d.date,d.date===W.from?"Today":longDay(d.date),[...(d.meetings||[]).map(e=>meeting(e,d.date)),...only(d.items||[]).map(i=>item(i,`${d.date}${i.kind}${i.id}`,false))]); });
  group("wkfur","Further ahead",only(W.further||[]).map(i=>item(i,`f${i.date}${i.kind}${i.id}`,true)),W.further_to?` to ${longDay(W.further_to)}`:"");
  return Object.assign(out,{above:hidden}); }   /* #313: `above` counts the rows left out because they are listed above */
/** The open actions that are overdue and owned by others (RAID items, decisions and milestones are not counted, so the count is exactly the Actions tab's list at the address): the quiet line above the days (#112). */
export function othersOverdue(){ const n=[...A].filter(x=>overdue(x)&&!isMe(x.o)).length;
  return {n,nav:navOf("actions:open:",{st:["Open","Delayed"],due:["overdue"],"!o":["@me"]})}; }
const WEEKFOLD="creaite-week-ahead-hidden";   /* #105: per viewer, this browser only (localStorage) */
let weekFoldWired=false;
function wireWeekFold(){ const f=$("#weekFold"); if(!f||weekFoldWired) return; weekFoldWired=true;
  f.open=store.get(WEEKFOLD,false)!==true; f.addEventListener("toggle",()=>store.set(WEEKFOLD,!f.open)); }
export function renderWeek(){ const W=D.week, host=$("#weekList"); if(!host) return; wireWeekFold();
  const groups=weekGroups(), n=groups.reduce((t,g)=>t+g.rows.length,0);
  const above=groups.above||0;   /* #313: the rows left out because they are listed above are counted, not dropped silently */
  $("#weekTo").textContent=W?`${plur(n,"item")} to ${longDay(W.to)}${above?` · ${above} more listed above`:""}`:"";   /* #105: the quiet count and the end date, as Resolved's */
  drawWeekAhead(host,{groups,openFile:p=>{ prepOpen(p); },others:othersOverdue(),empty:above?`The rest of what is due until ${W?longDay(W.to):"next Monday"} is listed above.`:`Nothing is due or booked until ${W?longDay(W.to):"next Monday"}.`,
    onAct:(r,a,btn)=>{ if(a.data&&a.data.id) workAct(a.data.k,a.data.id,a.id,btn); },blocked:why=>snack(why)}); }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootToday319(){
/* a text-drawn row's icon (Your commitments): the same actions as the Week ahead's */
$("#tBrief").addEventListener("click",e=>{ const b=/** @type {HTMLElement|null} */(e.target.closest("[data-tdo]")); if(!b) return; e.preventDefault(); e.stopPropagation();
  if(b.getAttribute("aria-disabled")==="true"){ snack(b.dataset.tip||"Not now"); return; } workAct(b.dataset.k,b.dataset.id,b.dataset.tdo,b); });
/* a reminder's run icon, when it can't run, says why */
$("#tBrief").addEventListener("click",e=>{ const b=/** @type {HTMLElement|null} */(e.target.closest('.rem [data-d="run"][aria-disabled="true"]')); if(!b) return; e.preventDefault(); e.stopPropagation(); snack(b.dataset.why||"Not now"); },true);
}
/* ===== end BL-319 ===== */
/* ===== BL-125 A (v19-promises-data): promises, "You owe" and "Waiting on" =====
   D.promises (build_dashboard.promises_data) holds the open promises on active projects made by you or to you; its `list` is
   tracker.promise_lists's answer, so the page, `tracker.py read promises --list` and the weekly report agree. Today shows
   You owe (yours, soonest due first) and Waiting on (made to you and overdue, most overdue first, with how long each has
   been quiet: since it was raised or last raised again in a meeting or message). A section with nothing in it is hidden.
   A person's page lists what they promised you and what you promised them (personPromises). People are named, never
   labelled (BL-288: no VIP chip). */
/** @typedef {{id:string,p:string,t:string,by:string,to:string,due:?string,raised:?string,src:?string,od:number,quiet:number,list:string}} PromiseRow */
/** @returns {PromiseRow[]} */
export const PROMS=()=>D.promises||[];
/** a person in a promise, linked to their page (yours goes to Mine) */
export const promWho=(/** @type {string} */n)=>sLink(String(html`data-person="${n||""}"`),esc(who(n)||"someone"));
/** "due in 2 days", "3 days late" (flagged), or "no date given" */
export const promDue=(/** @type {PromiseRow} */x)=>x.due?dueWords(x.due):"no date given";
export const promQuiet=(/** @type {PromiseRow} */x)=>x.quiet?`, quiet for ${plur(x.quiet,"day")}`:"";
/** You owe soonest due first (undated last); Waiting on most overdue first */
export const promOwe=()=>PROMS().filter(x=>x.list==="owe").sort((a,b)=>(a.due||"9999").localeCompare(b.due||"9999")||a.id.localeCompare(b.id));
export const promWaiting=()=>PROMS().filter(x=>x.list==="waiting").sort((a,b)=>b.od-a.od||a.id.localeCompare(b.id));
/** one promise as a Today line: the promise in bold, then who, where and when */
export function promLi(/** @type {PromiseRow} */x,/** @type {number} */n,/** @type {boolean} */waiting){
  const title=String(html`<span class="t pt" data-promise="${x.id}">${x.t??""}</span>`);
  return tl(n,title,waiting?String(html`From ${raw(promWho(x.by))} on ${raw(projLink(x.p))}: ${raw(promDue(x))}${promQuiet(x)}.`)
    :String(html`To ${raw(promWho(x.to))} on ${raw(projLink(x.p))}: ${raw(promDue(x))}.`)); }
export function renderPromises(){
  /** @param {string} sec @param {string} key @param {PromiseRow[]} L @param {boolean} waiting */
  const draw=(sec,key,L,waiting)=>{ const el=$("#"+sec); if(!el) return; el.hidden=!L.length; if(!L.length) return;
    const late=L.filter(x=>x.od>0).length, c=capped(L.map((x,i)=>promLi(x,i+1,waiting)),S.listCap||10,key);
    putHTML($(`#n${key[0].toUpperCase()+key.slice(1)}`),html`${L.length}${late&&!waiting?html` · <span class="late">${late} overdue</span>`:""}`);
    putHTML($(`#${key}List`),raw(c.html)); putHTML($(`#${key}More`),raw(c.more)); };
  draw("tOwe","owe",promOwe(),false); draw("tWait","wait",promWaiting(),true); }
/** a person's page: the open promises between them and you, both ways, overdue flagged */
export function personPromises(/** @type {string} */name,/** @type {(n:string)=>string} */same){
  const L=PROMS(), theirs=L.filter(x=>same(x.by)===name&&isMe(x.to)).sort((a,b)=>b.od-a.od||(a.due||"9999").localeCompare(b.due||"9999")),
    yours=L.filter(x=>isMe(x.by)&&same(x.to)===name).sort((a,b)=>(a.due||"9999").localeCompare(b.due||"9999"));
  if(!theirs.length&&!yours.length) return null;
  const first=name.split(/\s+/)[0], li=(/** @type {PromiseRow} */x,/** @type {boolean} */w)=>html`<div class="li" data-promise="${x.id}"><div class="t">${x.t??""}</div><div class="m">${raw(projLink(x.p))} · ${raw(promDue(x))}${w&&x.od>0?promQuiet(x):""}</div></div>`;
  const part=(/** @type {string} */h,/** @type {PromiseRow[]} */L2,/** @type {boolean} */w)=>L2.length?html`<h3>${h} <span class="sub">· ${L2.length}</span></h3><div class="mini-list">${L2.map(x=>li(x,w))}</div>`:"";
  return html`<div class="card ppcard" id="ppPromises"><h2>Promises</h2>${part(`${first} promised you`,theirs,true)}${part(`You promised ${first}`,yours,false)}</div>`; }
/* ===== end BL-125 A ===== */
