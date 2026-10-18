// @ts-check
/* ReportParts (#221, #217: H2 of the Reporting hub): the pieces of the report sheet that are THE SAME for the internal and the client
   report. The two views differ only in audience (their wording, their smaller set of figures, client-visible-only items, and the
   per-section "Matching internal / Edited for the client" with Match internal); they mount the same ReportSheet and draw these same
   parts, so a change here shows in both and both pass the same tests (dev/tests/test_report_sheet.py).
   - ReportSheet: the Sheet with the page's repeated title block removed (the one header below says what the report is);
   - ReportHeader: the one title block, "Weekly report · Internal" or "Client report · Client", the project, the week or period, and
     the logos at the right (the firm's always; the client's and a partner's when ticked), drawn straight on the page;
   - HealthBlock: the flag, the six-week strip and its two dates, and the Change button, all inside a 96 px indicator;
   - EyeTable: a table with an eye on each row (in the report or left out), "Showing 4 of 5", and a slot under it;
   - AddFromTracker: "+ Add from the tracker" under Risks and issues, Overdue actions and Decisions: a picker over the open items that
     are not in the report yet (the client report is offered client-visible ones only, by the server). Adding changes the report only,
     marks the row New, and nothing is saved before the report is approved except the draft the sheet autosaves.
   Text only through JSX. */
import { useEffect, useRef, useState } from "preact/hooks";
import { api } from "../../core/server.js";
import { addTextSection } from "../../stores/textSection.js";
import { EyeButton } from "./EyeButton.jsx";
import { Sheet } from "./Sheet.jsx";
import { wkDm, wkLongDate, wkTone, wkDmy } from "./weekly/weeklyDoc.js";

/** @typedef {import("./Sheet.jsx").SectionCtx} SectionCtx */
/** @typedef {import("./Sheet.jsx").SheetDoc} SheetDoc */
/** @typedef {import("./Sheet.jsx").SheetRow} SheetRow */
/** @typedef {{key: string, label: string, w?: string, num?: boolean, cell: (r: Row) => any}} Col */
/** @typedef {{ctx: SectionCtx, row: SheetRow, i: number, cells: Record<string, string>, item: any}} Row */

/** The sheet of both reports. `audience` is "internal" or "client"; `addText(sectionId)` is the free-text section's hook (H5): the
    section menu's "Add a text section below" calls it, and it is stores/textSection.js addTextSection (the sheet binds what it does).
    @param {import("./Sheet.jsx").SheetProps & {audience: "internal"|"client", addText?: (sectionId: string) => void}} props */
export function ReportSheet({ audience, addText = addTextSection, ...rest }) {
  return <Sheet {...rest} report={{ audience, addText }} />;
}

const KIND = /** @type {Record<string, string>} */ ({ firm: "Firm", client: "Client", partner: "Partner" });

/** The one title block of a report with its logos. Logos are the project's files (system/branding/logos/); which of them show is
    this report's `layout.logos`, chosen in the cog's Client report settings panel (the tiles), not on the sheet. @param {{ctx: SectionCtx, logos: {kind: string, path: string}[], data: Record<string, string>}} props */
export function ReportHeader({ ctx, logos, data }) {
  const { doc, section: s } = ctx, d = s.data || {}, client = doc.kind === "client";
  const chosen = Array.isArray(doc.layout?.logos) ? doc.layout.logos : ["firm", "client", "partner"];
  const shown = logos.filter(l => l.kind === "firm" || chosen.includes(l.kind));
  const meta = doc.meta || {};
  const period = d.period_start ? `${wkDmy(d.period_start)} to ${wkDmy(d.period_end || doc.date)}` : "";
  return (
    <header class="wr-hd">
      <div class="wr-title">
        <div class="wr-eb">{client ? "Client report · Client" : "Weekly report · Internal"}</div>
        <div class="wr-pn">{doc.project_name}</div>
        <div class="wr-wk">{client && period ? `Period ${period}` : `Week ending ${wkLongDate(doc.date)}`}{d.client ? ` · for ${d.client}` : ""}</div>
        {client && ctx.editing ? <div class="wr-facts sub">{meta.facts_week ? `Facts from the internal report for week ending ${wkDmy(meta.facts_week)}${meta.locked ? ", locked" : ""}`
          : "Facts as the tracker stands now: they lock when the internal report is approved"}</div> : null}
      </div>
      <div class="wr-logos">
        {shown.map((l, i) => <span key={l.kind} class="wr-logo">{i ? <span class="wr-lsep" aria-hidden="true" /> : null}
          {data[l.path] ? <img src={data[l.path]} alt={`${KIND[l.kind] || l.kind} logo`} /> : <span class="sub">{KIND[l.kind] || l.kind}</span>}</span>)}
      </div>
    </header>);
}

/** The health indicator: the flag, the six-week strip with its two dates, the Change control, and the reason beside them.
    96 px wide, the strip, its dates and Change inside it, the flag 12 px and on one line.
    `trend` is absent for a client report (its health keeps no weekly history on the page).
    @param {{ctx: SectionCtx, flag: string, trend?: {date: string, flag: string}[]|null, change?: any, why: any, below?: any, flagCls?: string}} props */
export function HealthBlock({ ctx, flag, trend, change, why, below, flagCls = "" }) {
  const t = wkTone(flag), weeks = trend && trend.length ? trend : null;
  const aria = weeks ? `Health over ${weeks.length} weeks: ${weeks.map(w => `${w.flag || "not set"}`).join(", ")}` : "";
  return (
    <div class="wr-health" data-wkTone={t}>
      <div class="wr-hcol">
        <div class={`wr-flag ${t}${flagCls ? " " + flagCls : ""}`}>{(flag || "Not set").toUpperCase()}</div>
        {weeks ? <div class="wr-trend" role="img" aria-label={aria}>{weeks.map((w, i) => <i key={i} class={wkTone(w.flag)} />)}</div> : null}
        {weeks ? <div class="wr-tlbl"><span>{wkDm(weeks[0].date)}</span><span>{wkDm(ctx.doc.date)}</span></div> : null}
        {ctx.editing ? change : null}
        {below}
      </div>
      <div class="wr-why">
        <div class="wr-whytext">{why}</div>
        <ctx.Spark />
      </div>
    </div>);
}

/** The sections whose tables take items from the tracker. */
export const PICKABLE = new Set(["risks", "overdue", "decisions"]);

/** A table with the eye column, shared by every table section of both reports. `cellsFor(item)` rebuilds the cells of a row that was
    left out and kept only its reference. @param {{ctx: SectionCtx, cols: Col[], noun: string, empty: string, cellsFor: (sid: string, item: any, on: string) => Record<string, string>,
    extra?: any, leftOut?: string}} props */
export function EyeTable({ ctx, cols, noun, empty, cellsFor, extra, leftOut = "the filed report and the exports" }) {
  const s = ctx.section, rows = s.rows || [];
  const flip = (/** @type {number} */ i) => {
    const r = rows[i], on = r.shown === false;
    ctx.update({ rows: rows.map((x, j) => j !== i ? x : { ...x, shown: on, cells: x.cells || cellsFor(s.id, (ctx.doc.items || {})[x.ref || ""], ctx.doc.date) }) }, on ? "Row shown" : "Row hidden");
  };
  const shown = rows.filter(r => r.shown !== false).length;
  return (
    <div class="wr-tbl">
      {rows.length ? (
        <table class="wr-r">
          <colgroup>{ctx.editing ? <col class="eyec" /> : null}{cols.map(c => <col key={c.key} style={c.w ? { width: c.w } : undefined} />)}</colgroup>
          <thead><tr>{ctx.editing ? <th class="eyec"><span class="sr">In the report</span></th> : null}{cols.map(c => <th key={c.key}>{c.label}</th>)}</tr></thead>
          <tbody>{rows.map((row, i) => {
            const off = row.shown === false; if (off && !ctx.editing) return null;
            const item = (ctx.doc.items || {})[row.ref || ""] || null, cells = row.cells || cellsFor(s.id, item, ctx.doc.date);
            const isNew = ctx.editing && row.source === "added" && PICKABLE.has(s.id);
            const idLike = (/** @type {string} */ v) => v === row.ref || /^[A-Z][A-Z0-9]{2,6}-[A-Z]-\d+$/.test(v);
            const subject = Object.values(cells || {}).map(v => String(v || "").trim()).find(v => v && !idLike(v)) || "this row";   // the words of the row, never its id
            return (
              <tr key={row.ref || i} class={off ? "hidrow" : ""} data-ref={row.ref || undefined}>
                {ctx.editing ? <td class="eyec"><EyeButton on={!off} subject={subject} onClick={() => flip(i)} /></td> : null}
                {cols.map((c, k) => <td key={c.key} class={c.num ? "num" : ""}>{c.cell({ ctx, row, i, cells, item })}{k === 0 && isNew ? <span class="rs-new" title="Added from the tracker by you">New</span> : null}</td>)}
              </tr>);
          })}</tbody>
        </table>) : <p class="sub">{empty}</p>}
      {ctx.editing && rows.length ? <div class="wr-count">Showing {shown} of {rows.length} {noun}. Hidden rows are left out of {leftOut}.</div> : null}
      {extra}
    </div>);
}

let CLOSE_PICKER = /** @type {null|(() => void)} */ (null);     // the picker that is open: one at a time (a stable closer, not the render's own)
/** "+ Add from the tracker": a picker over the open items that are not in this table yet. Cancel changes nothing; Add puts the ticked
    items in the table (marked New, each with its eye) and changes only the report. @param {{ctx: SectionCtx}} props */
export function AddFromTracker({ ctx }) {
  const s = ctx.section;
  const [open, setOpen] = useState(false);
  const [list, setList] = useState(/** @type {any[]|null} */ (null));
  const [q, setQ] = useState("");
  const [sel, setSel] = useState(/** @type {string[]} */ ([]));
  const [msg, setMsg] = useState("");
  const btn = useRef(/** @type {HTMLButtonElement|null} */ (null));
  const search = useRef(/** @type {HTMLInputElement|null} */ (null));
  const me = useRef(/** @type {null|(() => void)} */ (null));
  const close = () => { if (CLOSE_PICKER === me.current) CLOSE_PICKER = null; setOpen(false); setList(null); setQ(""); setSel([]); setMsg(""); setTimeout(() => btn.current?.focus(), 0); };
  const closeNow = useRef(close); closeNow.current = close;
  useEffect(() => { if (open && search.current) search.current.focus(); }, [open]);     // the search box takes the cursor, so Esc works at once
  if (!ctx.editing || !PICKABLE.has(s.id)) return null;
  const start = async () => {
    if (!me.current) me.current = () => closeNow.current();
    if (CLOSE_PICKER && CLOSE_PICKER !== me.current) CLOSE_PICKER();
    CLOSE_PICKER = me.current;
    setOpen(true); setList(null); setMsg("");
    const r = await api("/api/report/pick", { doc: ctx.doc });
    if (r && r.ok) setList((r.sections || {})[s.id] || []);
    else { setList([]); setMsg(String((r && r.message) || "The tracker couldn't be read").split("\n")[0]); }
  };
  const words = q.trim().toLowerCase();
  const shownList = (list || []).filter(c => !words || `${c.ref} ${c.title} ${c.meta}`.toLowerCase().includes(words));
  const add = () => {
    const picked = (list || []).filter(c => sel.includes(c.ref)), doc = ctx.doc;
    if (!picked.length) return;
    ctx.setDoc({ ...doc, items: { ...(doc.items || {}), ...Object.fromEntries(picked.map(c => [c.ref, c.item])) },
      sections: doc.sections.map(x => x.id === s.id ? { ...x, rows: [...(x.rows || []), ...picked.filter(c => !(x.rows || []).some(r => r.ref === c.ref)).map(c => c.row)] } : x) },
    picked.length === 1 ? "Item added from the tracker" : "Items added from the tracker");
    close();
  };
  const toggle = (/** @type {string} */ ref) => setSel(sel.includes(ref) ? sel.filter(x => x !== ref) : [...sel, ref]);
  return (
    <div class="rs-pick">
      {!open ? <button type="button" class="wr-link rs-pick-open" ref={btn} aria-expanded="false" onClick={start}>+ Add from the tracker</button> : null}
      {open ? (
        <div class="rs-picker" role="group" aria-label={`Add to ${s.heading} from the tracker`} onKeyDown={e => { if (e.key === "Escape") { e.stopPropagation(); close(); } }}>
          <input type="search" class="rs-pick-search" ref={search} aria-label="Search the tracker" placeholder="Search" value={q} onInput={e => setQ(/** @type {HTMLInputElement} */ (e.currentTarget).value)} />
          <div class="rs-pick-list">
            {list === null ? <p class="sub rs-pick-wait" role="status">Looking in the tracker…</p> : null}
            {list !== null && !list.length ? <p class="sub rs-pick-none">{msg || "Nothing else is open that could be added."}</p> : null}
            {list !== null && list.length && !shownList.length ? <p class="sub rs-pick-none">Nothing matches.</p> : null}
            {shownList.map(c => (
              <label key={c.ref} class="rs-pick-row" data-ref={c.ref}>
                <input type="checkbox" checked={sel.includes(c.ref)} onChange={() => toggle(c.ref)} />
                <span class="rs-pick-id">{c.ref}</span><span class="rs-pick-t">{c.title}</span><span class="rs-pick-m">{c.meta}</span>
              </label>))}
          </div>
          <div class="rs-pick-foot">
            <span class="sub">{sel.length ? `${sel.length} ticked` : "Tick the items to include. The tracker is not changed."}</span>
            <button type="button" class="btn sm rs-pick-cancel" onClick={close}>Cancel</button>
            <button type="button" class="btn sm primary rs-pick-add" disabled={!sel.length} onClick={add}>Add to the report</button>
          </div>
        </div>) : null}
    </div>);
}
