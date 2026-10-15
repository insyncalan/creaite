// @ts-check
/* Timeline (v2.1.0 P6, BL-335): Milestones as the mockup draws them: a sideways-scrolling timeline of every milestone (today
   marked, a slip drawn from the agreed date to the expected one), tall enough to read or dragged shorter or taller by its bottom
   edge, and under it a milestone list with an eye on each row. The eye chooses which milestones are in the list (what the export
   prints, `section.data.milestones`, and `layout.milestones`); the timeline always shows every milestone. */
import { useLayoutEffect, useRef, useState } from "preact/hooks";
import { editDoc } from "../../../stores/weekly.js";
import { dayNo, wkDm, wkDmy, wkMsState, todayIso, withSection } from "./weeklyDoc.js";

/** @typedef {import("../Sheet.jsx").SectionCtx} SectionCtx */
const MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const PX = 6, H = 92;

/** The milestones of the section, by agreed date. @param {SectionCtx} ctx @returns {any[]} */
function milestones(ctx) {
  const items = ctx.doc.items || {}, refs = (ctx.section.data || {}).timeline || [];
  return refs.map((/** @type {string} */ r) => items[r]).filter((/** @type {any} */ m) => m && m.table === "milestones")
    .sort((/** @type {any} */ a, /** @type {any} */ b) => dayNo(a.baseline_date || a.forecast_date) - dayNo(b.baseline_date || b.forecast_date));
}

/** The drawing: the line, month ticks, today, each milestone and its slip. @param {{ms: any[], today: string, k: number, h: number}} props */
function Drawing({ ms, today, k, h }) {
  const dates = ms.flatMap(m => [m.baseline_date, m.forecast_date, m.actual_date].filter(Boolean)).map(dayNo).concat([dayNo(today)]);
  const lo = Math.min(...dates) - 14, hi = Math.max(...dates) + 21, X = (/** @type {string} */ iso) => 20 + (dayNo(iso) - lo) * PX, W = 40 + (hi - lo) * PX;
  const ticks = [];
  for (let t = Math.ceil(lo); t <= hi; t++) { const d = new Date(t * 864e5); if (d.getUTCDate() === 1) ticks.push({ x: 20 + (t - lo) * PX, name: MON[d.getUTCMonth()] + (d.getUTCMonth() === 0 ? ` ${d.getUTCFullYear()}` : "") }); }
  const tx = X(today), first = MON[new Date(lo * 864e5).getUTCMonth()], last = MON[new Date(hi * 864e5).getUTCMonth()];
  return (
    <svg class="wr-tl" viewBox={`0 0 ${W} ${H}`} style={{ height: `${h}px`, width: `${W * k}px` }} role="img"
      aria-label={`Milestones from ${first} to ${last}: ${ms.map(m => `${m.title || m.name} ${wkDmy(m.forecast_date || m.baseline_date)}`).join("; ")}`}>
      <line x1="10" y1="44" x2={W - 10} y2="44" class="wr-tlline" />
      {ticks.map(t => <g key={t.x}><line x1={t.x} y1="38" x2={t.x} y2="50" class="wr-tlline" /><text x={t.x + 3} y="86" class="wr-tltx">{t.name}</text></g>)}
      <line x1={tx} y1="10" x2={tx} y2="56" class="wr-tltoday" /><text x={tx + 4} y="14" class="wr-tlnow">Today</text>
      {ms.map((m, i) => {
        const st = wkMsState(m), base = m.baseline_date || m.forecast_date, fc = m.forecast_date, done = st.tone === "g" && m.status === "Done" || dayNo(base) < dayNo(today),
          x = X(base), slip = fc && fc !== base && dayNo(fc) > dayNo(base), ly = i % 2 ? 28 : 68, fx = slip ? X(fc) : x;
        return (
          <g key={m.id} class={`wr-ms ${st.tone}`}>
            <circle cx={x} cy="44" r="6" class={done ? "fill" : "hollow"} />
            {slip ? <><line x1={x + 7} y1="44" x2={fx - 8} y2="44" class="wr-slip" /><circle cx={fx} cy="44" r="7" class="wr-slipc" /></> : null}
            <text x={fx} y={ly} class="wr-tllab" text-anchor="middle">{`${m.title || m.name} · ${wkDm(slip ? fc : base)}`}</text>
          </g>);
      })}
    </svg>);
}

/** Milestones: the timeline and the list. @param {{ctx: SectionCtx}} props */
export function Timeline({ ctx }) {
  const { doc, section: s } = ctx, ms = milestones(ctx), listed = new Set((s.data || {}).milestones || []);
  const wrap = useRef(/** @type {HTMLDivElement|null} */ (null)), [k, setK] = useState(1), [h, setH] = useState(98), [open, setOpen] = useState(false);
  const today = doc.state === "approved" ? doc.date : todayIso();
  useLayoutEffect(() => {
    const el = wrap.current; if (!el) return;
    const fit = () => { const hh = Math.max(60, el.clientHeight - 6); setH(hh); setK(hh / H); };
    fit(); const ro = new ResizeObserver(fit); ro.observe(el); return () => ro.disconnect();
  }, []);
  useLayoutEffect(() => {      // the line starts with today in view
    const el = wrap.current, dates = ms.map(m => dayNo(m.baseline_date || m.forecast_date)).concat([dayNo(today)]);
    if (el) el.scrollLeft = Math.max(0, (20 + (dayNo(today) - (Math.min(...dates) - 14)) * PX - 60) * k);
  }, [k, ms.length, today]);
  const toggle = (/** @type {string} */ id) => {
    const next = ms.map(m => m.id).filter(r => r === id ? !listed.has(r) : listed.has(r));
    editDoc(withSection(doc, s.id, { data: { ...(s.data || {}), milestones: next } }, { milestones: next }), listed.has(id) ? "Milestone left out of the list" : "Milestone in the list");
  };
  const rows = ctx.exported ? ms.filter(m => listed.has(m.id)) : ms;
  if (!ms.length) return <p class="sub">No milestones are set for this project.</p>;
  const showList = ctx.exported ? rows.length > 0 : open;
  return (
    <div class="wr-timeline">
      <div class="wr-tlwrap" ref={wrap} tabindex={0} aria-label="Milestone timeline; scroll sideways"><Drawing ms={ms} today={today} k={k} h={h} /></div>
      {ctx.editing ? <div class="wr-tlgrab">Drag the bottom edge to change the height</div> : null}
      {!ctx.exported ? <button type="button" class="wr-link" aria-expanded={open ? "true" : "false"} onClick={() => setOpen(!open)}>
        {open ? "Hide the milestone list ▴" : "Show the milestone list ▾"}</button> : null}
      {showList ? (
        <div class="wr-tbl">
          <table class="wr-r"><thead><tr>{ctx.editing ? <th class="eyec"><span class="sr">In the list</span></th> : null}<th>Milestone</th><th>Agreed</th><th>Expected</th><th>Progress</th><th>State</th></tr></thead>
            <tbody>{rows.map(m => {
              const st = wkMsState(m), on = listed.has(m.id), late = m.forecast_date && m.baseline_date && dayNo(m.forecast_date) > dayNo(m.baseline_date);
              return (
                <tr key={m.id} class={on ? "" : "hidrow"}>
                  {ctx.editing ? <td class="eyec"><button type="button" class="wr-eye" aria-pressed={on ? "true" : "false"} onClick={() => toggle(m.id)}
                    aria-label={`${on ? "Leave out of" : "Put in"} the list: ${m.title || m.name}`}
                    data-tip={on ? "In the list: click to leave it out (the timeline is unchanged)" : "Left out of the list: click to show it"}>{on ? "◉" : "○"}</button></td> : null}
                  <td><ctx.ItemRef id={m.id} /> {m.title || m.name}</td><td class="num">{wkDmy(m.baseline_date)}</td>
                  <td class={`num${late ? " late" : ""}`}>{m.actual_date ? `achieved ${wkDm(m.actual_date)}` : `${wkDmy(m.forecast_date || m.baseline_date)}${late ? ` (+${Math.round(dayNo(m.forecast_date) - dayNo(m.baseline_date))})` : ""}`}</td>
                  <td class="num">{m.percent_complete != null ? `${m.percent_complete}%` : ""}</td><td><span class={`wr-st ${st.tone}`}>{st.word}</span></td>
                </tr>);
            })}</tbody></table>
          {ctx.editing ? <div class="wr-count">Showing {ms.filter(m => listed.has(m.id)).length} of {ms.length} milestones in the list. Leaving one out tidies the list only; the timeline always shows every milestone.</div> : null}
        </div>) : null}
    </div>);
}
