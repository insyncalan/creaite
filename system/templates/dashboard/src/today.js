// @ts-check
/* today.js (BL-231 step 2b), moved from script/ by dev/tools/convert_area.py: 0025-today.js, 0026-today-brief-bl-72.js, 0027-bl-149-sprint-ux.js, 0028-after-bl-149.js, 0159-bl-156-sprint-ux.js, 0164-bl-166-sprint-polish-2.js.
   Unchanged apart from `export`, `shared.` for the shared state (core/state.js) and the load-time steps, now in
   boot…() functions that src/main.js calls in today's order. */
import { dcIcon, openChat, say, send } from "./ask.js";
import { closeMenu, menuOpenFor, openMenu } from "./components/Menu.jsx";
import { openDatePicker } from "./components/Picker.jsx";
import { parseWhen, weekendNote, WK, wkAsk, wkDays } from "./core/fields.js";
import { mountStatusDots } from "./components/StatusDot.jsx";
import { mountFirstThing } from "./components/closeday/FirstThing.jsx";
import { drawDayCurve } from "./components/today/DayCurve.jsx";
import { drawDayMeetings } from "./components/today/DayMeetings.jsx";
import { drawDayTabs } from "./components/today/DayTabs.jsx";
import { drawToDecide } from "./components/today/ToDecide.jsx";
import { drawWeekAhead } from "./components/today/WeekAhead.jsx";
import { A, LASTVISIT, open, overdue, P, pName, R, REMINDERS, REV, soon } from "./core/data.js";
import { $, $$, addHTML, esc, html, ic, putHTML, raw, swapHTML } from "./core/dom.js";
import { mDots } from "./core/motion.js";
import { countLink, go, jumpLink, navBlocked, navOf, openWork, pLink } from "./core/nav.js";
import { anim, copied, D, DATE, days, fd, fdText, health, isMe, reduced, rel, S, slideDown, store, TODAY, VAULT_PATH, who } from "./core/page.js";
import { api, oneLine, onceFor, reviewViaServer, snack, viaServer, writeSettings, z2 } from "./core/server.js";
import { shared } from "./core/state.js";
import { rjGuesses, rjMenu } from "./stores/rejects.js";
import { selDay } from "./stores/today.js";
import { draftBtn } from "./drafts.js";
import { checkMeeting, MRUN, MSEL, MTG, mtgHasTx, processMeetings, refreshCalendar } from "./intake.js";
import { decAsked, decLate, decLateWords, decPending, decRank, decShort, dnChase, dnDecide, prepOpen, prepPageOf, renderDn } from "./meetings.js";
import { decorateWarnings, prepKey, prepOf, undatedWork, WARNS } from "./projects.js";
import { chaseCan, chaseOpen, openRecord, pkCommit, pkUndoLast, REC } from "./panel.js";
import { decide, draftOn, RHL, rjLoadGuesses, rjMenuFor, routineKid } from "./review.js";
import { nm, row, SA, SETSECTIONS, VIPKIND, VIPQ, VIPR, VIPS, vipWhen } from "./settings.js";
import { applyFilters, applyView, clearAllFilters, colResizer, isStale, items, rvPaint, syncView } from "./work.js";
/* ======================= Today ======================= */
export const dismissedF=()=>store.get("creaite-dismiss",[]), dismissedS=()=>{ try{ return JSON.parse(sessionStorage.getItem("creaite-dismiss-s")||"[]"); }catch(e){ return []; } };
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
  if(/-sweep(-\d+)?\.json$/.test(file)) return `Review the sweep of ${when}`;
  if(/-(dashboard|edit)(-\d+)?\.json$/.test(file)) return "Review your pending edits";
  if(/-excel(-\d+)?\.json$/.test(file)) return "Review the Excel import";
  return `Review the proposals from ${when}`; }
export function attentionItems(){ const out=/** @type {any[]} */([]);   /* BL-319 (Alan, 14-10-2026): proposals are To decide's alone, so Needs attention has no per-meeting groups (nor their Approve n routine); a followed person's messages lead To decide too (BL-288) */
  if(S.remindersOn){ const hide=[...dismissedF(),...dismissedS()];
    REMINDERS.filter(r=>!hide.includes(r.id)).forEach(r=>out.push({reminder:r.id,html:n=>tl(n,
      tLink(r.id.startsWith("client:")?`data-cock="${r.id.split(":")[1]}"`:r.id.startsWith("revisit:")?`data-open="decisions:${r.id.split(":")[1]}"`:r.id.startsWith("weekly:")?'data-go="reports"':'data-go="projects"',esc(longText(r.text))),
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
  { const L=decPending().sort(decRank); if(L.length){
    const mine=L.filter(d=>isMe(d.by)).length, others=L.length-mine, late=L.filter(decLate).length, parts=[];
    if(others) parts.push(`${plur(others,"decision")} waiting on others`); if(mine) parts.push(others?`${mine} for you`:`${plur(mine,"decision")} for you`);
    const show=L.slice(0,3).map(d=>`${sLink(`data-open="decisions:${d.id}"`,esc(decShort(d.t,70)))} (${decAsked(d)}${d.due?`, ${decLate(d)?`<span class="late">${decLateWords(d)}</span>`:`by ${fd(d.due).slice(0,5)}`}`:""})`);
    out.unshift({decisions:true,html:n=>tl(n,tLink('data-decpending="1"',parts.join(", ")+(late?`, ${late} late`:"")),`${andList(show)}${L.length>3?` and ${L.length-3} more`:""}.`)}); } }
  return out; }
export const dueWords=d=>{ const n=days(d); return n<0?`<span class="late">${-n} day${n===-1?"":"s"} late</span>`:n===0?"due today":n===1?"due tomorrow":`due in ${n} days`; };
/* "Friday 9th October": the Week ahead heading spells its end day out (Alan, 2026-10-09) */
export const ordinal=n=>n+((n%100>=11&&n%100<=13)?"th":["th","st","nd","rd"][n%10]||"th");
/* Every date on Today reads "Thursday 15th October" (Alan, 2026-10-09); the year is added only when it isn't this year */
/* BL-287: beside a meeting's Prep, when creaite has saved a prep page for it, an Open icon that goes straight to the page (Meetings › Prep,
   #prep=<key>, BL-286 D) and the "Prep page made" chip. A real button of its own (never inside Prep), named for the meeting; its tooltip
   says when the page was saved. Without the live server it is shown disabled. */
export function prepGoHtml(e,day){ const pg=prepPageOf(e,day); if(!pg) return ""; const live=viaServer();
  return String(html`<button type="button" class="ib prepgo" data-prepgo="${pg.key}" data-prepgoday="${day}" aria-label="Open the prep page for ${e.title??""}" data-tip="${live?`Prep page saved ${pg.when}`:"Needs the live server"}"${raw(live?"":' aria-disabled="true"')}>${raw(ic("external"))}</button><span class="tag ok prepmade">Prep page made</span>`); }
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
  putHTML($("#briefText"),html`<b>${pend.length} proposal${pend.length===1?"":"s"}</b> need${pend.length===1?"s":""} your decision, ${raw(countLink(`${plur(mineOver.length,"overdue action")} of yours`,mineOver.length,"actions:overdue:",{o:["@me"]},`<b>${mineOver.length} of your actions</b>`))} ${mineOver.length===1?"is":"are"} overdue${off.length?html`, and <b>${andList(off.map(p=>p.name))}</b> ${off.length===1?"is":"are"} off track`:""}.`);
  renderToDecide();   /* BL-319: To decide, first after the band */
  renderDn();   /* BL-210: Decisions needed, ahead of Needs attention */
  const att=attentionItems(), ac=capped(att.map((x,i)=>x.html(i+1)),5,"attn");
  $("#nAttn").textContent=att.length?String(att.length):""; putHTML($("#attnList"),ac.html?raw(ac.html):html`<li><span class="n"></span><div class="tb"><span class="none">Nothing needs your attention.</span></div></li>`); putHTML($("#attnMore"),raw(ac.more));
  const mine=[...mineOver,...mineSoon].sort((a,b)=>a.due.localeCompare(b.due)), mc=capped(mine.map((x,i)=>tl(i+1,tLink(html`data-open="actions:${x.id}"`,html`${x.t??""}`),
    html`${raw(dueWords(x.due))} on ${x.p?raw(projLink(x.p)):"no project"}${x.pr==="Urgent"?", marked Urgent":""}${x.upd?`. Latest: ${x.upd.length>140?x.upd.slice(0,139)+"…":x.upd}`:""}.`,itemActs("actions",x))),5,"mine");
  putHTML($("#nMine"),raw(mine.length?countLink(`${plur(mine.length,"action")} of yours due or overdue`,mine.length,"actions:open:",{st:["Open","Delayed"],due:["overdue","soon"],o:["@me"]}):""));   /* BL-190 */ putHTML($("#mineList"),mc.html?raw(mc.html):html`<li><span class="n"></span><div class="tb"><span class="none">Nothing due from you this week.</span></div></li>`); putHTML($("#mineMore"),raw(mc.more));
  renderPromises();   /* BL-125 A: You owe and Waiting on */
  /* Resolved: items closed since the last visit, from the change log */
  const seen=new Set(), done=shared.ACT.filter(a=>a.at>LASTVISIT&&!a.undone&&(a.tbl==="actions"||a.tbl==="raid")&&/^status: .*→ Closed$/i.test(a.change)&&!seen.has(a.id)&&seen.add(a.id));
  const rc=capped(done.map((a,i)=>{ const x=(a.tbl==="actions"?A:R).find(y=>y.id===a.id), when=a.at.slice(0,10)===TODAY?`at ${a.at.slice(11)} today`:`on ${longDay(a.at.slice(0,10))}`;
    return tl(i+1,tLink(html`data-open="${a.tbl}:${a.id}"`,html`${a.item||a.id}`),html`${x&&x.p?html`${plur(1,a.tbl==="actions"?"action":(x.type||"risk").toLowerCase())} on ${raw(projLink(x.p))}, `:""}closed ${when} — ${a.by.replace(/^You, /,"you, ")}.`); }),5,"res");
  $("#chgTitle").textContent=`${done.length} since ${longDate(LASTVISIT.slice(0,10))}`;   /* BL-319: folded to one line, the count in it */
  putHTML($("#chgList"),rc.html?raw(rc.html):html`<li><span class="n"></span><div class="tb"><span class="none">Nothing has been resolved since ${longDate(LASTVISIT.slice(0,10))}.</span></div></li>`);
  putHTML($("#chgMore"),html`${raw(rc.more)}${rc.more?" · ":""}<a class="s" href="#" data-go="activity">See all activity</a>`);
  renderWeek();   /* BL-319: day by day to next Monday, each row saying why it is there */
  putHTML($("#pfTbl"),raw(portfolioTable("pf",true))); mountStatusDots($("#pfTbl")); pfResize($("#pfTbl"));   /* BL-285; BL-256 */
  decorateWarnings($("#mineList"));   /* BL-49 */
  mountFirstThing(DC().first||null);   /* BL-295: First thing, from the last Close the day */
  if(!shared.LOADING){ { const L=$$("#tdList li.td-message[data-td]"), ids=L.map(x=>x.dataset.td);
    if(TVIPSEEN&&!reduced()) L.filter(x=>!TVIPSEEN.has(x.dataset.td)).forEach(x=>slideDown(x)); TVIPSEEN=new Set(ids); }
  mDots("today");
  renderSetup();   /* BL-155 */
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
  $("#dayHead").textContent=v.known?dayShape(v.meetings,first,iso):`Good ${nowMins()<12*60?"morning":nowMins()<18*60?"afternoon":"evening"}${first?", "+first:""}.`;
  if(!on){ drawDayCurve(line,null); drawDayMeetings(meets,null); calFoot(null); return; }
  /* ===== BL-151 (sprint-ux) ===== no calendar for today: the band is one quiet line, "No calendar yet", with Refresh calendar
     (Intake's action) beside it; no empty timeline. When the calendar arrives the band opens as before; a day read with no
     meetings keeps its line and says so ("No meetings today"). BL-270: that line says when it was read. */
  const common={day:iso,dow:rec.dow||synthDay(iso).dow,isToday,past:iso<TODAY,now:nowMins(),live:viaServer(),calendar:!!cal,acts:DAYACTS,onWheel:onDayWheel,meetings:v.meetings,allDay:v.allDay};
  if(!v.known){ line.hidden=true; drawDayCurve(line,null);
    drawDayMeetings(meets,{...common,mode:"none",lastRead:cal&&cal.fetched?longDay(cal.fetched)+(cal.fetched.length>10?", "+cal.fetched.slice(11,16):""):""}); calFoot(null); return; }
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
export async function dayProcess(m){ const row=MTG().find(x=>x.id===m.id); if(!row){ snack("Open Intake › Calendar import to process this meeting"); return; }
  DAYRUN.set(m.id,"Processing…"); renderDay(); MSEL.clear(); MSEL.add(m.id);
  try{ await processMeetings(); } finally{ DAYRUN.delete(m.id); if(shared.VIEW==="today") renderDay(); } }
/** Look for an ended meeting's transcript (Alan, 13-10-2026: a meeting not checked yet offers Check). */
export async function dayCheck(m){ const row=MTG().find(x=>x.id===m.id)||{id:m.id,title:m.title,day:dayShown(),start:m.start};
  DAYRUN.set(m.id,"Checking…"); renderDay();
  try{ await checkMeeting(row); } finally{ DAYRUN.delete(m.id); if(shared.VIEW==="today") renderDay(); } }
export const DAYACTS={open:p=>{ prepOpen(p); },process:m=>{ dayProcess(m); },check:m=>{ dayCheck(m); },review:()=>go("review"),name:c=>pName(c)};   /* #140: no Note link on the band (BL-301 C's capture drawer opens from elsewhere) */
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
  if(r.id.startsWith("weekly:")&&REV.some(x=>!x.done&&x.p&&(!r.id.split(":")[2]||x.p===r.id.split(":")[2]))) await say("A project with items awaiting review is skipped until they're reviewed.",`<button class="mini" data-go="review">Open Review</button>`); }
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
document.addEventListener("click",e=>{ if(e.target.closest("[data-refcal]")) refreshCalendar(); });
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
export function remBtn(r){ if(!r.cmd) return ""; const run=RUNNING.has(r.id), live=viaServer(), why=run?"Already running":live?"":"Needs the live server";
  return `<span class="rmgo tacts">${tib("filetext",run?"Running…":remLabel(r),`${remLabel(r)}: ${r.text}`,`data-d="run"${why?` data-why="${esc(why)}"`:""}`,true,why)}</span>`; }   /* BL-319: an icon, named on hover */
export const isConflict=r=>!!r&&!r.done&&(r.flags||[]).includes("conflict");
export function conflictHtml(r){ const ch=(r.rec.changes&&r.rec.changes.length?r.rec.changes:r.rec.field?[{field:r.rec.field,from:r.rec.from,to:r.rec.to}]:[]);
  const v=x=>x==null||x===""?"(empty)":esc(DATE.test(String(x).slice(0,10))&&String(x).length===10?fd(x):String(x));
  return `<div class="cfvs">${ch.map(c=>`<div><span class="cff">${esc(c.field)}</span><span class="cfnow">Now: <b>${v(c.from)}</b></span><span class="cfnew">This one: <b>${v(c.to)}</b></span></div>`).join("")||'<div class="sub">Changed in the tracker after this was proposed.</div>'}</div>`; }
/* ===== end BL-149 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootToday0027(){
$("#reviewBody").addEventListener("click",e=>{ const b=e.target.closest('[data-act="ck"],[data-act="co"]'); if(!b) return; e.stopPropagation(); e.preventDefault();
  const r=REV.find(x=>x.n===+b.closest("tr[data-n]").dataset.n); if(!r||r.done) return; b.disabled=true;
  reviewViaServer(r,b.dataset.act==="ck"?"keep":"override",[]); },true);
}
export const kindLabel=r=>({actions:"Action",raid:r.rec.type||"Risk",decisions:"Decision",update:"Update",draft:"Draft",files:"File change"}[r.kind]);
export function evidence(p){ const nw=WARNS().filter(w=>w.p===p.code).length, ov=A.filter(x=>x.p===p.code&&overdue(x)).length, urg=R.filter(r=>r.p===p.code&&r.st==="Open"&&r.pr==="Urgent").length;
  /* BL-190 (sprint-links): each figure is its own link (a zero stays plain); a click on one doesn't also open the row's project page */
  const nd=undatedWork(p.code).length, c=p.code, nm=pName(c);
  return `<span class="ev">${countLink(`${plur(ov,"overdue action")} in ${nm}`,ov,`actions:overdue:${c}`,null,`Overdue <b class="${ov?"bad":""}">${ov}</b>`)} · ${jumpLink(`${plur(nd,"open item")} with no due date in ${nm}`,nd,c,"undated",`No date <b>${nd}</b>`)} · ${countLink(`${plur(urg,"urgent open RAID item")} in ${nm}`,urg,`raid:urgentonly:${c}`,null,`Urgent risks <b class="${urg?"bad":""}">${urg}</b>`)} · ${jumpLink(`Milestone slip of ${p.slip} day${p.slip===1?"":"s"} in ${nm}`,p.slip,c,"ms",`Slip <b class="${p.slip?"bad":""}">${p.slip?p.slip+" days":"none"}</b>`)} · Warnings <b class="${nw?"bad":""}">${nw}</b></span>`; }
export const spark=p=>`<span class="spark" title="Health, last 8 weeks (oldest first)" aria-label="Health trend">${p.trail.map(t=>`<i class="s-${t}"></i>`).join("")}</span>`;
/* BL-285: the Portfolio table. The description is no longer a line under the name: it is the name's tooltip (data-tip), shown on
   hover and on keyboard focus (the name is a button that opens the project), and read by screen readers from a hidden span
   (aria-describedby). The columns resize like Work's (pfResize), remembered under portfolio|<column>. */
export const PFCOLS=[["project","Project"],["health","Health"],["evidence","Evidence"],["trend","8 weeks"],["next","Next milestone"]];
/** @param {string} [id] @param {boolean} [dots] BL-256: Today's health markers are StatusDot components (placeholders, then mountStatusDots). BL-325: the next milestone's relative date is mid-sentence in brackets, so lower case ("(in 24 days)") */
export function portfolioTable(id="pf",dots=false){ return `<table><thead><tr>${PFCOLS.map(([k,l])=>`<th data-col="${k}">${l}</th>`).join("")}</tr></thead><tbody>${P.map(p=>{ const nm=p.ms.find(m=>m[2]!=="done")||p.ms[p.ms.length-1]||["No milestones yet","",""], ds=(p.client||"").trim(), did=`${id}d-${p.code}`;
  return `<tr class="click" data-cock="${p.code}"><td><button type="button" class="pfname"${ds?` data-tip="${esc(ds)}" aria-describedby="${did}"`:""}>${esc(p.name)}</button>${ds?`<span class="vh" id="${did}">${esc(ds)}</span>`:""}</td><td>${dots?`<span data-statusdot="${esc(p.health||"")}"></span>`:health(p.health)}<div class="sub" style="max-width:36ch">${esc(p.reason)}</div></td><td>${evidence(p)}</td><td>${spark(p)}</td><td>${esc(nm[0])}${nm[1]?`<div class="sub ${nm[2]==="slip"?"late":""}">${longDay(nm[1])} (${rel(nm[1]).replace(/^./,c=>c.toLowerCase())})</div>`:""}</td></tr>`; }).join("")}</tbody></table>`; }
export function pfResize(box){ if(box) $$("thead th[data-col]",box).forEach(th=>colResizer(th,"portfolio|"+th.dataset.col)); }
/* BL-316: a reminder's "…" menu is the Menu block's (openMenu): Run report now, Dismiss for this session, Dismiss forever */
export function remMenu(b,id){ if(menuOpenFor(b)){ closeMenu(); return; } const r=REMINDERS.find(x=>x.id===id); if(!r) return; const why=RUNNING.has(id)?"Already running":viaServer()?"":"Needs the live server";
  openMenu(b,{label:`Options: ${r.text}`,id:"remMenu",align:"right",onPick:d=>remPick(id,d),
    items:[...(r.cmd?[{id:"run",name:"Run report now",disabled:!!why,tip:why||undefined,data:{d:"run"}}]:[]),{id:"s",name:"Dismiss for this session",data:{d:"s"}},{id:"f",name:"Dismiss forever",data:{d:"f"}}]}); }
export function remPick(id,d){ if(d==="run"){ runReminder(REMINDERS.find(r=>r.id===id)); return; }
  if(d==="s"){ const a=dismissedS(); a.push(id); sessionStorage.setItem("creaite-dismiss-s",JSON.stringify(a)); } else { const a=dismissedF(); a.push(id); store.set("creaite-dismiss",a); writeSettings({"reminders.dismissed_forever":[...new Set([...(D.dismissed||[]),...a])]}); }
  renderToday(); snack(d==="s"?"Hidden for this session":"Hidden for good (this one)",()=>{ store.set("creaite-dismiss",dismissedF().filter(x=>x!==id)); sessionStorage.setItem("creaite-dismiss-s",JSON.stringify(dismissedS().filter(x=>x!==id))); renderToday(); }); }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootToday0028(){
$("#attnList").addEventListener("click",e=>{ const n=e.target.closest(".rem"); if(!n) return; const b=e.target.closest("button"); if(!b) return; e.stopPropagation();
  if(b.classList.contains("dots")){ remMenu(b,n.dataset.id); return; }
  if(b.dataset.d) remPick(n.dataset.id,b.dataset.d); });
document.addEventListener("click",e=>{ if(e.target.closest&&e.target.closest(".colrz")) return; const r=e.target.closest("[data-cock]"); if(r) go("cockpit",r.dataset.cock); });   /* BL-285: a resize never opens the project */
}
/* ===== BL-156 (sprint-ux) ===== first run: a short checklist on Today. On a vault that hasn't finished set-up (no project, no
   people in the register, or no sweep yet) Today starts with five steps, each with a button that does it or opens where it is
   done, ticked as it is done: Connect Microsoft 365 (ticked by the first sweep, which needs it; the button opens Help's first
   hour), Add a project (Settings › Projects and register), Add people (Settings › People), Run the first sweep (ask creaite,
   "sweep"), Open Review (ticked once Review has been opened in this browser). It goes when all five are ticked, or for good with
   Dismiss (kept with the dismissed reminders, so Settings › Reminders › Restore brings it back). Nothing it does is new. */
export function setupSteps(){ const seen=store.get(SETUPK,{});
  return [["m365","Connect Microsoft 365",swept(),"Show me how","help",swept()?"Connected: the sweep has read your mail":`Connected in Claude itself, so the page can’t: connect it there, then say “${esc(SU_M365)}” in Claude Code. The first sweep confirms it`],
    ["proj","Add a project",P.length>0,"Add a project","proj",`${P.length} project${P.length===1?"":"s"}`],
    ["people","Add people",shared.REG.length>0,"Add people","people",`${shared.REG.length} in the people register`],
    ["sweep","Run the first sweep",swept(),"Run the first sweep","sweep",swept()?`Last swept ${esc(String(D.last_sweep))}`:"Reads mail, Teams and the calendar since the look-back days"],
    ["review","Open Review",!!seen.review,"Open Review","review","Approve what's right; nothing reaches the tracker until you do"]]; }
export function setupShown(){ if([...dismissedF(),...(D.dismissed||[])].includes(SETUPID)) return false;
  const st=setupSteps(), base=st.slice(0,4).some(x=>!x[2]); if(base){ const seen=store.get(SETUPK,{}); if(!seen.shown){ seen.shown=true; store.set(SETUPK,seen); } return true; }
  return !!store.get(SETUPK,{}).shown&&!st[4][2]; }
export function renderSetup(){ let box=$("#setupList"); const on=setupShown();
  if(!on){ if(box) box.remove(); return; }
  if(!box){ addHTML($("#tBrief"),"afterbegin",html`<section class="tsec setupsec" id="setupList" aria-labelledby="hSetup"></section>`); box=$("#setupList"); }
  const st=setupSteps(), done=st.filter(x=>x[2]).length;
  putHTML(box,html`<h2 class="th" id="hSetup">Getting started <span class="cnt">${raw(done)} of ${st.length}</span><button type="button" class="linkbtn setupx" data-setup="dismiss">Dismiss</button></h2><ol class="bl setupbl">${raw(st.map(([k,t,ok,btn,act,note],i)=>`<li class="${ok?"done":""}"><span class="n" aria-hidden="true">${ok?"✓":i+1}</span><div class="tb"><span class="t">${esc(t)}</span>${ok?' <span class="vh">(done)</span>':""}<p>${note}</p></div>${ok?"":`<span class="rmgo"><button type="button" class="btn ${i===st.findIndex(x=>!x[2])?"primary":""}" data-setup="${act}" ${act==="sweep"&&!viaServer()?'disabled title="Needs the live server"':""}>${esc(btn)}</button></span>`}</li>`).join(""))}</ol>`); 
  { const b=$('#setupList [data-setup="help"]'), li=b&&b.closest("li");
    if(li&&!li.classList.contains("done")){ const go=li.querySelector(".rmgo"); putHTML(go,html`<button type="button" class="mini" data-sucopy="m365">Copy</button> <button type="button" class="mini" data-sucheck="m365" ${viaServer()?"":html`disabled title="Needs the live server"`}>Check again</button> <button type="button" class="linkbtn" data-setup="help">How</button>`); }
    if($("#setupList")&&!$("#suMore")) addHTML($("#setupList"),"beforeend",html`<p class="sub" id="suMore">The health check and the launcher are in <a href="#" data-setopen="setup">Settings › System › Set-up</a>.</p>`); }   /* BL-165 */ }
/* ===== end BL-156 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootToday0159(){
document.addEventListener("click",e=>{ const b=e.target.closest("[data-setup]"); if(!b) return; e.preventDefault(); const a=b.dataset.setup;
  if(a==="dismiss"){ const l=dismissedF(); l.push(SETUPID); store.set("creaite-dismiss",l); writeSettings({"reminders.dismissed_forever":[...new Set([...(D.dismissed||[]),...l])]}); renderSetup();
    snack("Checklist dismissed. Settings › Reminders › Restore brings it back",()=>{ store.set("creaite-dismiss",dismissedF().filter(x=>x!==SETUPID)); renderSetup(); }); return; }
  if(a==="help") go("help","start"); else if(a==="proj") go("settings","projects"); else if(a==="people") go("settings","people");
  else if(a==="review") go("review"); else if(a==="sweep"){ if(shared.BUSY){ snack("ask creaite is busy; try again when it's finished"); return; } openChat(); send("sweep"); } });
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
export const suCmd=(text,id,check)=>`<div class="sucmd"><code>${esc(text)}</code><button type="button" class="mini" data-sucopy="${id}">Copy</button>${check?`<button type="button" class="mini" data-sucheck="${id}" ${viaServer()?"":'disabled title="Needs the live server"'}>Check again</button>`:""}</div>`;
export const suText=id=>id==="m365"?SU_M365:id==="launch"?SU_LAUNCH():SU_SETUP;
export function suHealthHtml(){ const h=SU.health; if(!h) return "";
  const li=l=>{ const k=l.slice(0,4); return `<li><span class="k ${k.toLowerCase()}">${k}</span><span>${esc(l.slice(4).trim())}</span></li>`; }, L=h.lines.filter(l=>/^(PASS|WARN|FAIL)\s/.test(l));
  const bad=L.filter(l=>!l.startsWith("PASS")), ok=L.filter(l=>l.startsWith("PASS"));   /* what needs attention first; the passes folded */
  return `<div class="sub" role="status">${esc(h.lines[h.lines.length-1]||"")}</div>${bad.length?`<ul class="sures" aria-label="Needs attention">${bad.map(li).join("")}</ul>`:""}<details class="sures"><summary>${ok.length} passed</summary><ul class="sures">${ok.map(li).join("")}</ul></details>`; }
export function suCardHtml(){ const st=SU.status||{}, live=viaServer(), off=live?"":'disabled title="Needs the live server"';
  const swept=st.swept||(D.last_sweep&&D.last_sweep!=="never"?D.last_sweep:null);
  return `<div class="card" id="suCard" data-sec="setup"><h2>Set-up</h2><p class="sub">The set-up steps the page can do, and the two it can’t. Each runs on your click; nothing here is a new permission.</p>
   ${row("Health check",`<button type="button" class="btn" id="suHealth" ${off}>${SU.busy==="health"?"Checking…":"Run the health check"}</button>`,"The same checks as “health check” in Claude Code (doctor.py): it only reads")}
   ${suHealthHtml()?`<div id="suHealthOut">${suHealthHtml()}</div>`:""}
   ${row("Rebuild the dashboard and Excel view",`<button type="button" class="btn" id="suRebuild" ${off}>${SU.busy==="rebuild"?"Rebuilding…":"Rebuild…"}</button>`,"From the tracker; nothing in the tracker changes")}
   ${SU.confirm?`<div class="sushown" id="suConfirm">This rewrites <code>dashboard.html</code> and <code>tracker-view.xlsx</code> from the tracker. If the workbook has edits you haven’t imported, it is left as it is. <span class="suacts" style="margin-top:6px"><button type="button" class="btn" data-sucancel>Cancel</button><button type="button" class="btn primary" id="suRebuildGo">Rebuild now</button></span></div>`:""}
   ${row("Microsoft 365",swept?`<span class="h-ok">Connected</span>`:`<span class="sub">Not confirmed yet</span>`,swept?`The sweep last read your mail ${esc(fd(String(swept).slice(0,10)))}`:"Connected in Claude itself, so the page can’t do it: connect Microsoft 365 there (Settings › Connectors), then say this in Claude Code. The first sweep confirms it")}
   ${swept?"":suCmd(SU_M365,"m365",true)}
   ${row("Launcher",st.launcher?`<span class="h-ok">Made</span>`:`<span class="sub">Not made yet</span>`,st.launcher?`${esc(st.launcher)}: double-click it to open creaite`:"A small app that opens creaite in its own window and starts the live server. It goes outside the vault, so the page can’t make it: paste this into Terminal")}
   ${st.launcher?"":suCmd(SU_LAUNCH(),"launch",true)}
   ${row("The rest of set-up","","Your name and role, the projects folder, git and the optional schedules are a conversation: in Claude Code say")}${suCmd(SU_SETUP,"setup")}</div>`; }
export function suRedraw(){ const c=$("#suCard"); if(c) swapHTML(c,raw(suCardHtml())); }
export async function suCheck(what,btn){ if(btn) btn.disabled=true; const r=await suStatus(true); if(btn&&btn.isConnected) btn.disabled=false;
  if(!r){ snack("Checking needs the live server"); return; }
  if(what==="m365") snack(r.swept?`Microsoft 365 is connected: the sweep last read your mail ${fd(String(r.swept).slice(0,10))}`:"Not confirmed yet: the first sweep confirms it, as it reads your mail");
  else snack(r.launcher?`The launcher is made: ${r.launcher}`:"No launcher yet: paste the command into Terminal, then check again");
  suRedraw(); if(shared.VIEW==="today") renderSetup(); }
/* ===== end BL-166 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootToday0164(){
SETSECTIONS.splice(SETSECTIONS.findIndex(s=>s.id==="live")+1,0,{id:"setup",cat:"system",title:"Set-up",raw:true,kw:"setup set-up health check doctor launcher microsoft 365 connect rebuild excel first run",
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
   under it, at a 980px reading width, the sections in order and unboxed: To decide, First thing, Decisions needed, Needs
   attention, Your commitments (with You owe and Waiting on), Week ahead, Resolved (folded to one line) and Portfolio. Each
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
/** the bulk rule (FR-81): Approve and save from To decide only for what may be approved on its own row. Never minutes, a report or a
    file change, never a one-at-a-time item (a new decision, a new risk, a closing update …: indiv), nor one that needs a project or
    has a conflict. Those go to Review. */
export const tdApprovable=r=>!!r&&!r.done&&!["draft","files"].includes(r.kind)&&routineKid(r);
const revSrc=r=>/-sweep(-\d+)?\.json$/.test(r.file)?"sweep":/-(dashboard|edit)(-\d+)?\.json$/.test(r.file)?"your edits":/-excel(-\d+)?\.json$/.test(r.file)?"Excel import"
  :REV.some(x=>x.file===r.file&&x.kind==="draft"&&x.ref==="meeting")?"minutes":"proposal";
const tdTag=r=>r.kind==="draft"?(r.ref==="meeting"?"Minutes":"Report"):kindLabel(r)||"Proposal";
/** To decide's rows, newest first: proposals in Review, transcripts ready in Intake, messages from people Alan follows (never labelled) */
export function toDecideRows(){ const live=viaServer(), tdl=/** @type {any[]} */([]);
  REV.filter(r=>!r.done).forEach(r=>{ const at=revAt(r), ok=tdApprovable(r), t=String(r.rec&&r.rec.t||""), acts=[];
    if(ok) acts.push({id:"approve",icon:"check",label:"Approve and save",name:`Approve and save: ${t}`,primary:true});
    else acts.push({id:"review",icon:"review",label:"Open in Review",name:`Open in Review: ${t}`,primary:true});
    if(!["draft","files"].includes(r.kind)) acts.push({id:"reject",icon:"x",label:"Reject, with a reason",name:`Reject, with a reason: ${t}`,haspopup:"menu"});
    const why=!r.p&&r.kind!=="files"?"needs a project":(r.flags||[]).includes("conflict")?"conflicts with a newer change":r.indiv||["draft","files"].includes(r.kind)?"approved on its own, in Review":"";
    tdl.push({key:"rv"+r.n,kind:"review",n:r.n,at,tag:tdTag(r),tone:"acc",t,acts,
      meta:[r.p?pName(r.p):"", `${revSrc(r)}${at?" "+whenWords(at):""}`, why].filter(Boolean).join(" · ")}); });
  MTG().filter(mtgHasTx).forEach(m=>{ const at=`${m.day||""} ${m.end||m.start||""}`.trim(), run=MRUN[m.id], why=run==="processing"||run==="loading"?"Processing…":live?"":"Needs the live server";
    tdl.push({key:"tx"+m.id,kind:"transcript",id:m.id,at,tag:"Transcript",tone:"",t:m.title||"Meeting",
      meta:["Ready in Intake",m.p&&m.p!=="_portfolio"?pName(m.p):"",whenWords(at)].filter(Boolean).join(" · "),
      acts:[{id:"process",icon:"play",label:"Process the transcript",name:`Process the transcript of ${m.title||"the meeting"}`,primary:true,why}]}); });
  VIPS().forEach(a=>{ if("summary" in a&&a.marker!=="private"){ tdl.push(convRow(a)); return; }   /* BL-334: a conversation's card (a confidential one too, marked) */
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
   conversation with nothing for Alan is one quiet line with no buttons. Never labelled (BL-288). ----- */
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
    link:a.link||"",meta:convMeta(a),acts:[]}; }
/** "Mia Hale with Omar Ali: nothing for you" @param {any} a */
export function quietRow(a){ const others=(a.people||[]).filter(/** @param {string} p */p=>p!==a.who);
  return {key:"al"+a.id,kind:"quiet",id:a.id,at:convAt(a),tag:"",tone:"",t:`${a.who||""}${others.length?" with "+others.slice(0,3).join(", "):""}: nothing for you`,
    link:a.link||"",meta:convMeta(a),acts:[]}; }
/** where focus goes after a row's action takes the row away: the same action on the row now in its place, else the heading */
let TDFOCUS=/** @type {{i:number,what:string,at:number}|null} */(null);
export function tdFocusAfter(){ const f=TDFOCUS; if(!f||Date.now()-f.at>8000){ TDFOCUS=null; return; }
  const a=document.activeElement; if(a&&a!==document.body&&a.isConnected) return;
  const L=$$("#tdList > li").filter(l=>!l.hidden), li=L[Math.min(f.i,L.length-1)], b=li&&(li.querySelector(`[data-tdact="${f.what}"]`)||li.querySelector("[data-tdact]"));
  TDFOCUS=null; if(b){ /** @type {HTMLElement} */(b).focus(); return; } const h=$("#hTd")||$("#hAttn"); if(h&&h.offsetParent){ h.tabIndex=-1; h.focus(); } }
export function tdFocusMark(key,what){ const i=$$("#tdList > li").filter(l=>!l.hidden).findIndex(l=>l.dataset.td===key); TDFOCUS={i:Math.max(0,i),what,at:Date.now()}; }
/** a proposal's row in Review, highlighted (as First thing opens one) */
export function tdToReview(n){ go("review"); const r=REV.find(x=>x.n===n&&!x.done); if(!r) return; RHL.clear(); RHL.add(r.n); rvPaint();
  const tr=$(`#reviewBody tr[data-n="${r.n}"]`); if(tr) tr.scrollIntoView({block:"center"}); }
export async function tdProcess(id){ const m=MTG().find(x=>x.id===id); if(!m) return; MSEL.clear(); MSEL.add(id);
  if(shared.VIEW==="today") renderToday(); try{ await processMeetings(); } finally{ if(shared.VIEW==="today") renderToday(); } }
/** a row's action (a message's two run through settings.js's [data-alertdo] handler) */
export async function tdAct(row,act,btn){ tdFocusMark(row.key,act.id);
  if(row.kind==="transcript"&&act.id==="process"){ await tdProcess(row.id); return; }
  if(row.kind!=="review") return; const r=REV.find(x=>x.n===row.n); if(!r||r.done) return;
  if(act.id==="approve"){ if(!tdApprovable(r)){ tdToReview(r.n); return; } await decide(r.n,"approved"); return; }   /* Undo: the apply's (decide) */
  /* BL-315: the same reasons menu as Review (rjMenuFor: the seven reasons, Use each guess, No reason, Duplicate's item), through
     /api/review/reject, with its one message and Undo; the guesses are fetched first, so the row's guess is offered */
  if(act.id==="reject"){ const menu=()=>rjMenuFor([r],btn,()=>{ if(shared.VIEW==="today") renderToday(); }), was=rjGuesses.value;
    menu(); await rjLoadGuesses(); if(rjGuesses.value!==was&&rjMenu.value&&rjMenu.value.anchor===btn) menu(); return; }   /* BL-316: open at once; again with the guesses when they arrive */
  if(act.id==="review") tdToReview(r.n); }
export function tdOpen(row){ if(row.kind==="review") tdToReview(row.n); else if(row.kind==="transcript") go("inbox"); }
export function renderToDecide(){ const sec=$("#tdSec"), body=$("#tdBody"); if(!sec||!body) return;
  const L=toDecideRows(), total=REV.filter(r=>!r.done).length, n=L.filter(r=>r.kind!=="quiet").length; sec.hidden=!L.length;
  $("#nTd").textContent=n?String(n):"";                                          /* BL-334: a quiet line isn't counted */
  drawToDecide(body,{rows:L,total,cap:TDCAP,open:EXPAND.has("td"),onAct:tdAct,onOpen:tdOpen,onReview:()=>go("review"),blocked:why=>snack(why)});
  requestAnimationFrame(tdFocusAfter); }
/* ----- the Week ahead (BL-72, BL-127, BL-235; BL-319: to next Monday, why each row is there, its icon action) ----- */
/** the actions a piece of work offers (Week ahead, Your commitments): the main one first */
export function workActs(k,x){ const mine=isMe(x.o), owner=!!(x.o&&x.o!=="TBC"), t=x.t||x.id, L=[];
  if(k==="actions"){ if(mine) L.push({id:"done",icon:"done",label:"Mark done",name:`Mark done: ${t}`,primary:true});
    else if(owner) L.push({id:"chase",icon:"chasemail",label:"Draft a chase",name:`Draft a chase to ${who(x.o)}: ${t}`,primary:true});
    L.push({id:"move",icon:"calmove",label:"Move the date",name:`Move the date: ${t}`,haspopup:"dialog"}); }
  else if(k==="raid"){ L.push({id:"update",icon:"pencil",label:"Write an update",name:`Write an update: ${t}`,primary:true});
    if(!mine&&owner) L.push({id:"chase",icon:"chasemail",label:"Draft a chase",name:`Draft a chase to ${who(x.o)}: ${t}`}); }
  else if(k==="decisions"){ if(mine) L.push({id:"decide",icon:"flag",label:"Record the decision",name:`Record the decision: ${t}`,primary:true});
    else if(owner) L.push({id:"chase",icon:"chasemail",label:"Draft a chase",name:`Draft a chase to ${who(x.o)}: ${t}`,primary:true}); }
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
export function weekGroups(){ const W=D.week; if(!W) return [];
  const live=viaServer(), out=/** @type {any[]} */([]);
  const mineIds=new Set(A.filter(x=>isMe(x.o)&&(overdue(x)||soon(x))).map(x=>x.id)), quiet=i=>i.kind==="actions"&&mineIds.has(i.id);   /* mine are already under Your commitments */
  const dotOf=i=>i.pr==="Urgent"?"u":i.pr==="High"?"h":"";
  const whyOf=(i,further,undated)=>{ if(undated) return "no date set";
    const w=i.kind==="decisions"?"needed by":i.weekend?"due over the weekend":"due";
    const d=further&&i.date?` ${longDay(i.date)}`:"";
    return i.kind==="milestone"?(further&&i.date?`${longDay(i.date)} · `:"")+(i.slip?"at risk":"on track"):`${w}${d}`; };
  const whoOf=i=>i.kind==="milestone"?"":i.kind==="decisions"?(isMe(i.o)?"yours":i.o?`asked of ${who(i.o)}`:"no one asked"):(isMe(i.o)?"yours":who(i.o)||"no owner");
  const item=(i,key,further,undated=false)=>({key,kind:i.kind,dot:dotOf(i),t:i.t||i.id,open:i.kind==="milestone"?{cock:i.p}:{open:`${i.kind}:${i.id}`},
    who:whoOf(i),p:i.p||"",pname:i.p?pName(i.p):"",why:whyOf(i,further,undated),whyTone:i.kind==="milestone"&&i.slip?"warn":"",
    acts:workActs(i.kind,i).map(a=>({...a,data:{k:i.kind,id:i.id,...(i.kind==="milestone"?{p:i.p}:{})}}))});
  const meeting=(e,day)=>{ const can=day!==TODAY&&!!prepOf(e,day), pg=can?prepPageOf(e,day):null, t=e.title??"", key=prepKey(e,day);
    return {key:`m${day}${e.start}${e.title}`,kind:"meeting",time:e.start||"",t,
      open:can?{prepgo:key,prepgoday:day}:undefined,who:e.where||"",p:e.p||"",pname:e.p?pName(e.p):"",why:"",
      chip:can?{made:!!pg,label:pg?"Prep page made":"Prep",aria:`Open the prep page for ${t}`,key,day,live,title:t,start:e.start||"",where:e.where||"",
        pname:e.p?pName(e.p):"",pageWhen:pg?pg.when:"",page:pg?pg.path:null}:undefined,
      acts:[]}; };
  const group=(key,title,L,note)=>{ if(L.length) out.push({key,title,note:note||"",rows:L,cap:6,open:EXPAND.has(key)}); };
  group("wkund","Urgent, with no date",(W.undated||[]).map((i,n)=>item(i,`u${n}${i.id}`,false,true)));
  (W.days||[]).forEach(d=>{
    group("wk"+d.date,d.date===W.from?"Today":longDay(d.date),[...(d.meetings||[]).map(e=>meeting(e,d.date)),...(d.items||[]).filter(i=>!quiet(i)).map(i=>item(i,`${d.date}${i.kind}${i.id}`,false))]); });
  group("wkfur","Further ahead",(W.further||[]).map(i=>item(i,`f${i.date}${i.kind}${i.id}`,true)),W.further_to?` to ${longDay(W.further_to)}`:"");
  return out; }
/** The open actions that are overdue and owned by others (RAID items, decisions and milestones are not counted, so the count is exactly the Actions tab's list at the address): the quiet line above the days (#112). */
export function othersOverdue(){ const n=[...A].filter(x=>overdue(x)&&!isMe(x.o)).length;
  return {n,nav:navOf("actions:open:",{st:["Open","Delayed"],due:["overdue"],"!o":["@me"]})}; }
const WEEKFOLD="creaite-week-ahead-hidden";   /* #105: per viewer, this browser only (localStorage) */
let weekFoldWired=false;
function wireWeekFold(){ const f=$("#weekFold"); if(!f||weekFoldWired) return; weekFoldWired=true;
  f.open=store.get(WEEKFOLD,false)!==true; f.addEventListener("toggle",()=>store.set(WEEKFOLD,!f.open)); }
export function renderWeek(){ const W=D.week, host=$("#weekList"); if(!host) return; wireWeekFold();
  const groups=weekGroups(), n=groups.reduce((t,g)=>t+g.rows.length,0);
  $("#weekTo").textContent=W?`${plur(n,"item")} to ${longDay(W.to)}`:"";   /* #105: the quiet count and the end date, as Resolved's */
  drawWeekAhead(host,{groups,openFile:p=>{ prepOpen(p); },others:othersOverdue(),empty:`Nothing is due or booked until ${W?longDay(W.to):"next Monday"}.`,
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
