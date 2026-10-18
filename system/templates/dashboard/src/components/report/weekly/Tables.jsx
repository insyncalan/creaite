// @ts-check
/* Tables (v2.1.0 P6, BL-335): the report's tables as the mockup draws them: What we need from people (with + Add an ask), Risks and
   issues and Overdue actions (an eye on each row; the first rows shown, "Showing 5 of 8" under the table), and the decisions written
   out. Every item ID opens the standard peek (ctx.ItemRef). A row that was hidden and saved keeps only its reference, so showing it
   again makes its cells from the item as it stood (weeklyDoc.cellsFromItem). Hidden rows are faded while editing and are not drawn
   in the exported page. */
import { AddFromTracker, EyeTable } from "../ReportParts.jsx";
import { EyeButton } from "../EyeButton.jsx";
import { Rich } from "./Rich.jsx";
import { cellsFromItem, daysLate } from "./weeklyDoc.js";

/** @typedef {import("../Sheet.jsx").SectionCtx} SectionCtx */
/** @typedef {import("../Sheet.jsx").SheetRow} SheetRow */
/** @typedef {{key: string, label: string, w?: string, num?: boolean, cell: (r: Row) => any}} Col */
/** @typedef {{ctx: SectionCtx, row: SheetRow, i: number, cells: Record<string, string>, item: any}} Row */

const PRIORITY = { Urgent: "r", High: "r", Medium: "a", Low: "g" };

/** A weekly table: the shared eye table with this report's rebuild of a left-out row's cells, and "Add from the tracker" under it.
    @param {{ctx: SectionCtx, cols: Col[], noun: string, extra?: any, empty: string}} props */
function Table({ ctx, cols, noun, extra, empty }) {
  return <EyeTable ctx={ctx} cols={cols} noun={noun} empty={empty} cellsFor={cellsFromItem} extra={<>{extra}<AddFromTracker ctx={ctx} /></>} />;
}

/** The ID cell. @param {Row} r */
const idCell = r => r.row.ref ? <r.ctx.ItemRef id={r.row.ref} /> : null;
/** A cell that edits in place. @param {string} key @param {string} label */
const cellWords = (key, label) => (/** @type {Row} */ r) => <Rich ctx={r.ctx} text={r.cells[key]} row={r.i} col={key} label={label} empty="Click to write" />;

/** What we need from people. @param {{ctx: SectionCtx}} props */
export function Asks({ ctx }) {
  const s = ctx.section, rows = s.rows || [];
  const add = () => ctx.update({ rows: [...rows, { ref: "", shown: true, source: "added", cells: { ask: "", from: "", by: "", why: "" } }] }, "Ask added");
  const cols = [
    { key: "ask", label: "Ask", w: "40%", cell: (/** @type {Row} */ r) => <>
      <Rich ctx={r.ctx} text={r.cells.ask} row={r.i} col="ask" label="Ask" empty="Say what is needed" />
      {r.row.ref ? <div class="wr-src">{r.row.source === "promise" ? "Waiting on a promise to you, " : r.row.source === "decision needed" ? "Decision needed, " : "From "}<r.ctx.ItemRef id={r.row.ref} /></div> : null}</> },
    { key: "from", label: "From", w: "24%", cell: cellWords("from", "From") },
    { key: "by", label: "By", w: "13%", num: true, cell: cellWords("by", "By") },
    { key: "why", label: "Why it matters", cell: cellWords("why", "Why it matters") }];
  return <Table ctx={ctx} cols={cols} noun="asks" empty="Nothing is needed from anyone this week."
    extra={ctx.editing ? <button type="button" class="wr-link" onClick={add}>+ Add an ask</button> : null} />;
}

/** Risks and issues. @param {{ctx: SectionCtx}} props */
export function Risks({ ctx }) {
  const cols = [
    { key: "id", label: "ID", w: "13%", num: true, cell: idCell },
    { key: "risk", label: "Risk or issue", w: "33%", cell: cellWords("risk", "Risk or issue") },
    { key: "priority", label: "Priority", w: "11%", cell: (/** @type {Row} */ r) => r.cells.priority
      ? <span class={`wr-st ${/** @type {Record<string,string>} */ (PRIORITY)[r.cells.priority] || "n"}`}>{r.cells.priority.toUpperCase()}</span> : null },
    { key: "owner", label: "Owner", w: "15%", cell: cellWords("owner", "Owner") },
    { key: "response", label: "Response", cell: (/** @type {Row} */ r) => <span>{(r.item && r.item.response_action) || ""}</span> }];
  return <Table ctx={ctx} cols={cols} noun="risks and issues" empty="No open risks or issues." />;
}

/** Overdue actions. @param {{ctx: SectionCtx}} props */
export function Overdue({ ctx }) {
  const cols = [
    { key: "id", label: "ID", w: "15%", num: true, cell: idCell },
    { key: "action", label: "Action", w: "40%", cell: cellWords("action", "Action") },
    { key: "owner", label: "Owner", w: "17%", cell: cellWords("owner", "Owner") },
    { key: "due", label: "Due", w: "15%", num: true, cell: cellWords("due", "Due") },
    { key: "late", label: "Late", num: true, cell: (/** @type {Row} */ r) => {
      const n = r.item && r.item.due_date ? daysLate(r.item.due_date, r.ctx.doc.date) : 0;
      return n ? <span class="late">{n} day{n === 1 ? "" : "s"}</span> : null; } }];
  return <Table ctx={ctx} cols={cols} noun="overdue actions" empty="Nothing is overdue." />;
}

/** The week's decisions written out, one under another, each with its eye. @param {{ctx: SectionCtx}} props */
export function Decisions({ ctx }) {
  const all = ctx.section.rows || [];
  const rows = all.map((row, i) => ({ row, i })).filter(x => x.row.shown !== false || ctx.editing);
  const flip = (/** @type {number} */ i) => { const on = all[i].shown === false;
    ctx.update({ rows: all.map((x, j) => j !== i ? x : { ...x, shown: on, cells: x.cells || cellsFromItem("decisions", (ctx.doc.items || {})[x.ref || ""], ctx.doc.date) }) }, on ? "Row shown" : "Row hidden"); };
  return (
    <div class="wr-tbl">
      {!rows.length ? <p class="sub">No decisions were made this week.</p> : null}
      <ul class="wr-decs">{rows.map(({ row, i }) => {
        const c = row.cells || cellsFromItem("decisions", (ctx.doc.items || {})[row.ref || ""], ctx.doc.date), off = row.shown === false;
        const bit = (/** @type {string} */ key, /** @type {string} */ label) => ctx.editing
          ? <Rich ctx={ctx} text={c[key]} row={i} col={key} label={label} cls="wr-inl" empty={label} /> : <span>{c[key]}</span>;
        return (
          <li key={row.ref || i} class={off ? "hidrow" : ""} data-ref={row.ref || undefined}>
            {ctx.editing ? <EyeButton on={!off} subject={c.decision || "this decision"} onClick={() => flip(i)} /> : null}
            <div class="wr-decbody">
              <Rich ctx={ctx} text={c.decision} row={i} col="decision" label="Decision" empty="Say what was decided" />
              <div class="wr-meta">Made by {bit("by", "Made by")} on {bit("date", "Date")} · Source: {bit("source", "Source")}{row.ref ? <> · <ctx.ItemRef id={row.ref} /></> : null}
                {ctx.editing && row.source === "added" ? <span class="rs-new" title="Added from the tracker by you">New</span> : null}</div>
            </div>
          </li>);
      })}</ul>
      {ctx.editing && all.length ? <div class="wr-count">Showing {all.filter(r => r.shown !== false).length} of {all.length} decisions. Hidden decisions are left out of the filed report and the exports.</div> : null}
      <AddFromTracker ctx={ctx} />
    </div>);
}
