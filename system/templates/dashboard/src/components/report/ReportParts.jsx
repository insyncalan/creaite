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
   - AddFromTracker: "+ Add from your project record" under Risks and issues, Overdue actions and Decisions: a picker over the open items that
     are not in the report yet (the client report is offered client-visible ones only, by the server). Adding changes the report only,
     marks the row New, and nothing is saved before the report is approved except the draft the sheet autosaves.
   Text only through JSX. */
import { useEffect, useRef, useState } from "preact/hooks";
import { api } from "../../core/server.js";
import { crIdentity } from "../../stores/clientReport.js";
import { addTextSection } from "../../stores/textSection.js";
import { wkIdentity } from "../../stores/weekly.js";
import { crLogoFor, crLogoPaths, logoKindName, logoKindsOf, readClientLogos, ticksOf, uploadClientLogo } from "../../stores/reportingSettings.js";
import { EyeButton } from "./EyeButton.jsx";
import { Sheet } from "./Sheet.jsx";
import { blankCells } from "./sheetLib.js";
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

/** A logo's name for the header: Firm, Client, Partner, or a partner's own name (#228 B). @param {string} code @param {string} kind */
const nameOf = (code, kind) => logoKindName(code, kind).replace(/^Partner: /, "");
const LOGO_ACCEPT = "image/png,image/jpeg,image/svg+xml,.png,.jpg,.jpeg,.svg";

/** One logo's place in the header, in edit mode (#233 a): a dashed "Add <name> logo" tile, or the logo as a button "Change <name> logo".
    Both open the cog panel's chooser (reportingSettings.js uploadClientLogo saves it and both reports redraw at once). The firm's
    logo is the same file for every project, so replacing one asks first. @param {{code: string, kind: string, pic: string}} props */
function LogoSlot({ code, kind, pic }) {
  const file = useRef(/** @type {HTMLInputElement|null} */ (null)), btn = useRef(/** @type {HTMLButtonElement|null} */ (null));
  const [ask, setAsk] = useState(false);
  const name = kind.startsWith("partner:") ? nameOf(code, kind) : kind, label = `${pic ? "Change" : "Add"} ${name} logo`;
  const choose = () => file.current && file.current.click();
  const stop = () => { setAsk(false); setTimeout(() => btn.current && btn.current.focus(), 0); };
  /** @param {Event} e */
  const picked = async e => {
    const input = /** @type {HTMLInputElement} */ (e.target), f = input.files && input.files[0];
    if (f) await uploadClientLogo(code, kind, f);
    input.value = "";
  };
  return (
    <span class="wr-logo-slot" onKeyDown={e => { if (ask && e.key === "Escape") { e.stopPropagation(); e.preventDefault(); stop(); } }}>
      <button type="button" ref={btn} data-hdr-logo={kind} class={pic ? "wr-logo-btn" : "wr-logo-add"} aria-label={label} title={label}
        onClick={() => (pic && kind === "firm" ? setAsk(true) : choose())}>
        {pic ? <img src={pic} alt={`${nameOf(code, kind)} logo`} /> : <><b aria-hidden="true">+</b><span>Add {name} logo</span></>}</button>
      {ask ? <span class="wr-logo-ask" role="group" aria-label="Replace the firm logo?">
        <span class="sub" role="alert">This logo is used by all projects. Replace it?</span>
        <button type="button" class="btn sm" data-hdr-logo-yes={kind} onClick={() => { setAsk(false); choose(); }}>Replace</button>
        <button type="button" class="btn sm" data-hdr-logo-no={kind} onClick={stop}>Cancel</button></span> : null}
      <input type="file" hidden ref={file} accept={LOGO_ACCEPT} data-hdr-logo-file={kind} tabIndex={-1} onChange={picked} />
    </span>);
}

/** The one title block of a report with its logos. Logos are the project's files (system/branding/logos/); which of them show is
    this report's `layout.logos`, chosen in the cog's Client report settings panel (the tiles), not on the sheet. In edit mode (never
    in Show as exported) each slot that is on shows its logo as a button or a dashed Add tile (#233 a). @param {{ctx: SectionCtx, logos: {kind: string, path: string}[], data: Record<string, string>}} props */
export function ReportHeader({ ctx, logos, data }) {
  const { doc, section: s } = ctx, d = s.data || {}, client = doc.kind === "client";
  const code = String(doc.project || ""), edit = ctx.editing && !ctx.exported && !ctx.readOnly && !!code;
  useEffect(() => { if (edit) readClientLogos(code); }, [edit, code]);
  const every = logoKindsOf(code), chosen = Array.isArray(doc.layout?.logos) ? doc.layout.logos : every;       // a bare "partner" is every partner
  const shown = logos.filter(l => ticksOf([l.kind], chosen).length);
  const slots = edit ? ticksOf(every, chosen) : [];
  const live = crLogoFor.value === code;                        // once read, the files the cog panel changed are the truth
  /** @param {string} k */
  const pathOf = k => (live ? crLogoPaths.value[k] : (shown.find(l => l.kind === k) || {}).path) || "";
  const meta = doc.meta || {};
  const period = d.period_start ? `${wkDmy(d.period_start)} to ${wkDmy(d.period_end || doc.date)}` : "";
  return (
    <header class="wr-hd">
      <div class="wr-title">
        <div class="wr-eb">{client ? "Client report · Client" : "Weekly report · Internal"}</div>
        <div class="wr-pn">{doc.project_name}</div>
        <div class="wr-wk">{client && period ? `Period ${period}` : `Week ending ${wkLongDate(doc.date)}`}{d.client ? ` · for ${d.client}` : ""}</div>
        {client && ctx.editing ? <div class="wr-facts sub">{meta.facts_week ? `Facts from the internal report for week ending ${wkDmy(meta.facts_week)}${meta.locked ? ", locked" : ""}`
          : "Facts as your project record stands now: they lock when the internal report is approved"}</div> : null}
      </div>
      <div class="wr-logos">
        {edit ? slots.map((k, i) => <span key={k} class="wr-logo">{i ? <span class="wr-lsep" aria-hidden="true" /> : null}
          <LogoSlot code={code} kind={k} pic={data[pathOf(k)] || ""} /></span>)
          : shown.map((l, i) => <span key={l.kind} class="wr-logo">{i ? <span class="wr-lsep" aria-hidden="true" /> : null}
            {data[l.path] ? <img src={data[l.path]} alt={`${nameOf(code, l.kind)} logo`} /> : <span class="sub">{nameOf(code, l.kind)}</span>}</span>)}
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

/** The sections whose tables take items from your project record. */
export const PICKABLE = new Set(["risks", "overdue", "decisions"]);

/** Whether a row has nothing the page can show (#234): it was left out and saved, so it holds only its reference and the document
    no longer has its item, or its cells are all empty (a row turned back on before the fix). It is drawn as left out, an export leaves
    it out, and its eye fills it from your project record. @param {SheetRow} row @param {SheetDoc} doc */
export const bareRow = (row, doc) => !!row.ref && (row.cells ? blankCells(row.cells, row.ref) : !(doc.items || {})[row.ref]);

/** Show a bare row again (#234): its cells come from your project record through the server (/api/report/reshow, read only; a client report
    gets only its client-safe facts there), never from the page. `live` holds the section's latest ctx, so an edit made while the
    tracker is read is kept. Answers "" when the row is back in the report, else the reason it stays left out.
    @param {{current: SectionCtx}} live @param {string} ref @returns {Promise<string>} */
export async function reshowRow(live, ref) {
  const sid = live.current.section.id, asked = live.current.doc;
  const ident = (/** @type {SheetDoc|undefined} */ d) => asked.kind === "client" ? crIdentity(d) : wkIdentity(d);
  const opened = ident();
  if (!opened || opened !== ident(asked)) return "";       // #234: only the report that is open now is ever filled
  const r = await api("/api/report/reshow", { doc: asked, section: sid, refs: [ref] });
  if (ident() !== opened) return "";                       // another report (or this one again) opened while the tracker was read: dropped
  const got = r && r.ok ? (r.rows || {})[ref] : null;
  if (!got || !got.row || !got.row.cells) return String((r && r.ok ? (r.missing || {})[ref] : r && r.message) || "your project record couldn't be read").split("\n")[0];
  const ctx = live.current, doc = ctx.doc, sec = doc.sections.find(x => x.id === sid);
  if (ident(doc) !== opened || !sec || !(sec.rows || []).some(x => x.ref === ref && bareRow(x, doc))) return "";       // changed meanwhile: nothing to fill
  ctx.setDoc({ ...doc, items: { ...(doc.items || {}), [ref]: got.item },
    sections: doc.sections.map(x => x.id !== sid ? x : { ...x, rows: (x.rows || []).map(y => y.ref === ref && bareRow(y, doc) ? { ...y, shown: true, cells: got.row.cells } : y) }) }, "Row shown");
  return "";
}

/** A bare row's own words while editing: its reference and that it is left out, never an empty cell to write in (#234). `why` says
    why it can't come back, once that is known. @param {{ctx: SectionCtx, row: SheetRow, why?: string}} props */
export function LeftOutNote({ ctx, row, why }) {
  return <><ctx.ItemRef id={String(row.ref)} /> <span class="crlk wr-leftout">Left out</span>
    <span class="wr-leftwhy">{why ? `Can't be shown again: ${why}.` : "Click the eye to put it back from your project record."}</span></>;
}

/** The eye's click on a row: hide it; show it with its cells (made again from the item the document holds), or, for a bare row,
    from your project record (reshowRow). @param {{current: SectionCtx}} live @param {(sid: string, item: any, on: string) => Record<string, string>} cellsFor
    @param {number} i @param {(ref: string, why: string) => void} setWhy */
export function flipRow(live, cellsFor, i, setWhy) {
  const ctx = live.current, s = ctx.section, rows = s.rows || [], r = rows[i], on = r.shown === false;
  if (bareRow(r, ctx.doc)) { reshowRow(live, String(r.ref)).then(why => setWhy(String(r.ref), why)); return; }   // drawn left out: its eye puts it back
  ctx.update({ rows: rows.map((x, j) => j !== i ? x : { ...x, shown: on, cells: x.cells || cellsFor(s.id, (ctx.doc.items || {})[x.ref || ""], ctx.doc.date) }) }, on ? "Row shown" : "Row hidden");
}

/** A table with the eye column, shared by every table section of both reports. `cellsFor(item)` rebuilds the cells of a row that was
    left out and kept only its reference. @param {{ctx: SectionCtx, cols: Col[], noun: string, empty: string, cellsFor: (sid: string, item: any, on: string) => Record<string, string>,
    extra?: any, leftOut?: string}} props */
export function EyeTable({ ctx, cols, noun, empty, cellsFor, extra, leftOut = "the filed report and the exports" }) {
  const s = ctx.section, rows = s.rows || [];
  const live = useRef(ctx); live.current = ctx;
  const [whys, setWhys] = useState(/** @type {Record<string, string>} */ ({}));
  const setWhy = (/** @type {string} */ ref, /** @type {string} */ why) => setWhys(w => ({ ...w, [ref]: why }));
  const flip = (/** @type {number} */ i) => flipRow(live, cellsFor, i, setWhy);
  const shown = rows.filter(r => r.shown !== false && !bareRow(r, ctx.doc)).length;
  return (
    <div class="wr-tbl">
      {rows.length ? (
        <table class="wr-r">
          <colgroup>{ctx.editing ? <col class="eyec" /> : null}{cols.map(c => <col key={c.key} style={c.w ? { width: c.w } : undefined} />)}</colgroup>
          <thead><tr>{ctx.editing ? <th class="eyec"><span class="sr">In the report</span></th> : null}{cols.map(c => <th key={c.key}>{c.label}</th>)}</tr></thead>
          <tbody>{rows.map((row, i) => {
            const bare = bareRow(row, ctx.doc), off = row.shown === false || bare; if (off && !ctx.editing) return null;
            if (bare) return (
              <tr key={row.ref || i} class="hidrow wr-bare" data-ref={row.ref || undefined}>
                <td class="eyec"><EyeButton on={false} subject={String(row.ref)} onClick={() => flip(i)} /></td>
                <td colSpan={cols.length}><LeftOutNote ctx={ctx} row={row} why={whys[String(row.ref)]} /></td>
              </tr>);
            const item = (ctx.doc.items || {})[row.ref || ""] || null, cells = row.cells || cellsFor(s.id, item, ctx.doc.date);
            const isNew = ctx.editing && row.source === "added" && PICKABLE.has(s.id);
            const idLike = (/** @type {string} */ v) => v === row.ref || /^[A-Z][A-Z0-9]{2,6}-[A-Z]-\d+$/.test(v);
            const subject = Object.values(cells || {}).map(v => String(v || "").trim()).find(v => v && !idLike(v)) || "this row";   // the words of the row, never its id
            return (
              <tr key={row.ref || i} class={off ? "hidrow" : ""} data-ref={row.ref || undefined}>
                {ctx.editing ? <td class="eyec"><EyeButton on={!off} subject={subject} onClick={() => flip(i)} /></td> : null}
                {cols.map((c, k) => <td key={c.key} class={c.num ? "num" : ""}>{c.cell({ ctx, row, i, cells, item })}{k === 0 && isNew ? <span class="rs-new" title="Added from your project record by you">New</span> : null}</td>)}
              </tr>);
          })}</tbody>
        </table>) : <p class="sub">{empty}</p>}
      {ctx.editing && rows.length ? <div class="wr-count">Showing {shown} of {rows.length} {noun}. Hidden rows are left out of {leftOut}.</div> : null}
      {extra}
    </div>);
}

const CLOSE_PICKER = /** @type {Map<Element|null, () => void>} */ (new Map());   // the picker open on each page: one at a time per page (a stable closer, not the render's own); in Side by side each pane has its own
/** "+ Add from your project record": a picker over the open items that are not in this table yet. Cancel changes nothing; Add puts the ticked
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
  const pageOf = () => (btn.current && btn.current.closest(".page")) || null;
  const mine = useRef(/** @type {Element|null} */ (null));
  const close = () => { if (CLOSE_PICKER.get(mine.current) === me.current) CLOSE_PICKER.delete(mine.current); setOpen(false); setList(null); setQ(""); setSel([]); setMsg(""); setTimeout(() => btn.current?.focus(), 0); };
  const closeNow = useRef(close); closeNow.current = close;
  useEffect(() => { if (open && search.current) search.current.focus(); }, [open]);     // the search box takes the cursor, so Esc works at once
  if (!ctx.editing || !PICKABLE.has(s.id)) return null;
  const start = async () => {
    if (!me.current) me.current = () => closeNow.current();
    mine.current = pageOf();
    const other = CLOSE_PICKER.get(mine.current);
    if (other && other !== me.current) other();
    CLOSE_PICKER.set(mine.current, me.current);
    setOpen(true); setList(null); setMsg("");
    const r = await api("/api/report/pick", { doc: ctx.doc });
    if (r && r.ok) setList((r.sections || {})[s.id] || []);
    else { setList([]); setMsg(String((r && r.message) || "Your project record couldn't be read").split("\n")[0]); }
  };
  const words = q.trim().toLowerCase();
  const shownList = (list || []).filter(c => !words || `${c.ref} ${c.title} ${c.meta}`.toLowerCase().includes(words));
  const add = () => {
    const picked = (list || []).filter(c => sel.includes(c.ref)), doc = ctx.doc;
    if (!picked.length) return;
    ctx.setDoc({ ...doc, items: { ...(doc.items || {}), ...Object.fromEntries(picked.map(c => [c.ref, c.item])) },
      sections: doc.sections.map(x => x.id === s.id ? { ...x, rows: [...(x.rows || []), ...picked.filter(c => !(x.rows || []).some(r => r.ref === c.ref)).map(c => c.row)] } : x) },
    picked.length === 1 ? "Item added from your project record" : "Items added from your project record");
    close();
  };
  const toggle = (/** @type {string} */ ref) => setSel(sel.includes(ref) ? sel.filter(x => x !== ref) : [...sel, ref]);
  return (
    <div class="rs-pick">
      {!open ? <button type="button" class="wr-link rs-pick-open" ref={btn} aria-expanded="false" onClick={start}>+ Add from your project record</button> : null}
      {open ? (
        <div class="rs-picker" role="group" aria-label={`Add to ${s.heading} from your project record`} onKeyDown={e => { if (e.key === "Escape") { e.stopPropagation(); close(); } }}>
          <input type="search" class="rs-pick-search" ref={search} aria-label="Search your project record" placeholder="Search" value={q} onInput={e => setQ(/** @type {HTMLInputElement} */ (e.currentTarget).value)} />
          <div class="rs-pick-list">
            {list === null ? <p class="sub rs-pick-wait" role="status">Looking in your project record…</p> : null}
            {list !== null && !list.length ? <p class="sub rs-pick-none">{msg || "Nothing else is open that could be added."}</p> : null}
            {list !== null && list.length && !shownList.length ? <p class="sub rs-pick-none">Nothing matches.</p> : null}
            {shownList.map(c => (
              <label key={c.ref} class="rs-pick-row" data-ref={c.ref}>
                <input type="checkbox" checked={sel.includes(c.ref)} onChange={() => toggle(c.ref)} />
                <span class="rs-pick-id">{c.ref}</span><span class="rs-pick-t">{c.title}</span><span class="rs-pick-m">{c.meta}</span>
              </label>))}
          </div>
          <div class="rs-pick-foot">
            <span class="sub">{sel.length ? `${sel.length} ticked` : "Tick the items to include. Your project record is not changed."}</span>
            <button type="button" class="btn sm rs-pick-cancel" onClick={close}>Cancel</button>
            <button type="button" class="btn sm primary rs-pick-add" disabled={!sel.length} onClick={add}>Add to the report</button>
          </div>
        </div>) : null}
    </div>);
}
