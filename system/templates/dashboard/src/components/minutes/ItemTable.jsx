// @ts-check
/* ItemTable (#268, Minutes view v2; replaces BL-338's ItemRow): the decisions, risks and issues, and actions of draft minutes as
   aligned tables, one heading per column: Track, the item, Owner, and for risks, issues and actions Due, Priority and
   Workstream (the RAID section is one table per kind: Risks, Issues, Assumptions, Dependencies). No source-arrow column, no
   popup: everything is edited where it stands.
   - Track (track.js): tick = register a work item, cross = remove the line from the minutes, neither = it stays in the
     minutes as a line and no work item is made. Clicking the pressed button clears it. The choice is kept in the page's
     layout; the record follows when the minutes are approved.
   - A risk's or issue's Workstream is a dropdown too (minutes_record.EDITABLE; the server takes only one of the project's
     Active workstreams, or none); a refusal is said on the toast and the row keeps its value. A risk's or issue's Priority
     is worked out from impact and likelihood, so it is shown read only, not picked.
   - The item's words in the one editor (Tiptap, plain, one line, with AI on selected text): Enter or a click away saves,
     Esc puts the words back. Owner, Priority and Workstream are in-row dropdowns; Due opens the deadline popover
     (DeadlinePopover.jsx). Each is one of the record's changes (/api/minutes/save {op}), so the row and its staged item
     change together.
   - Under the words, only what needs a look: "<name> needs details" (#266), Looks like an existing item (Update that one,
     Keep as new), a deadline or a figure the transcript doesn't say; and a read-only "Sensitive" tag on an item marked
     Sensitive, partner-only or excluded (the view's `withheld`; Cap's #268 review L2).
   - Hovering a row lights its transcript turn; hovering a turn lights its rows (stores/minutes.js hoverTurn).
   Show as exported, read-only or filed: the record's own table, as it is exported, without the lines crossed out. */
import { useContext, useRef, useState } from "preact/hooks";
import { openRef } from "../report/Sheet.jsx";
import { SheetEditor } from "../report/SheetText.jsx";
import { Icon } from "../Icon.jsx";
import { CheckMark } from "./Checks.jsx";
import { MinutesCtx } from "./context.js";
import { jumpTo } from "./TranscriptPane.jsx";
import { shortTime } from "./TextLines.jsx";
import { DeadlinePopover } from "./DeadlinePopover.jsx";
import { attnFilter, attnFocus, hiddenBy } from "./Attention.jsx";
import { needsOf, nextTrack, setTrack, trackOf, rowN } from "./track.js";
import { A, DEC, R, wsFor } from "../../core/data.js";
import { go } from "../../core/nav.js";
import { shared } from "../../core/state.js";
import { aiBar } from "../../stores/aiEdit.js";
import { hoverTurn, minutesView, paneTurn } from "../../stores/minutes.js";

/** @typedef {import("../report/Sheet.jsx").SectionCtx} SectionCtx */
/** @typedef {import("./track.js").TrackRow} TrackRow */

const MAIN = { actions: "action", decisions: "decision", raid: "description" };
const ROW_FIELD = { actions: "description", decisions: "decision", raid: "description" };
const KINDS = [["Risk", "Risks"], ["Issue", "Issues"], ["Assumption", "Assumptions"], ["Dependency", "Dependencies"], ["", "Updates"]];
const MN_PRIOS = ["Urgent", "High", "Medium", "Low"];
const ITEM_ID = /\b[A-Z][A-Z0-9]{2,6}-(?:[ADRM]-)?\d{3,}\b/g;
export const PRIO_TIP = "Worked out from impact and likelihood";
/** A risk's or issue's priority from its impact and likelihood (tracker.priority's rule), or "". @param {any} v */
export const raidPriority = v => {
  const i = String((v && v.impact) || ""), l = String((v && v.likelihood) || "");
  if (!i || !l) return "";
  return i === "High" && l === "High" ? "Urgent" : i === "High" || l === "High" ? "High" : i === "Low" && l === "Low" ? "Low" : "Medium";
};
/** The Track control's three choices: key, the word it shows, its icon and what it does (the tooltip). */
const TRACK_KINDS = [["y", "Tracked", "check", "Register a work item"], ["m", "Minutes only", "filetext", "Keep the line in the minutes, no work item"],
  ["n", "Dropped", "x", "Remove the line from the minutes"]];
export const TRACK_TIP = "Tick to register a work item; cross to remove the line from the minutes; neither keeps it in the minutes only";

/** A tracker item by its ITEM_ID, or null. @param {string} id */
const recOf = id => A.find(x => x.id === id) || R.find(x => x.id === id) || DEC.find(x => x.id === id) || null;

/** Words with their item IDs opening the peek. @param {{text: string}} props */
function Linked({ text }) {
  const parts = [], s = String(text || "");
  let i = 0;
  for (const m of s.matchAll(ITEM_ID)) {
    parts.push(s.slice(i, m.index));
    parts.push(<button key={m.index} type="button" class="linkbtn mnid" onClick={() => openRef(m[0], () => false)}>{m[0]}</button>);
    i = (m.index || 0) + m[0].length;
  }
  parts.push(s.slice(i));
  return <span>{parts}</span>;
}

/** The Track control (#302, option D): three icons, the chosen one raised and showing its word. Tick = Tracked (a work item is
    made), document = Minutes only (the line stays, no work item), cross = Dropped (the line leaves the minutes). A click on the
    pressed tick or cross clears it to Minutes only, as before. @param {{t: string, label: string, onPick: (which: "y"|"m"|"n") => void}} props */
function TrackButtons({ t, label, onPick }) {
  const now = t === "y" ? "Tracked" : t === "n" ? "Dropped" : "Minutes only";
  return (
    <span class="mntrk" role="group" aria-label={`Track: ${label}. Now ${now}`}>
      <span class="mntrb">
        {TRACK_KINDS.map(([k, word, icon, tip]) => (
          <button key={k} type="button" class={k} data-trk={k} aria-pressed={(k === (t === "y" || t === "n" ? t : "m")) ? "true" : "false"} aria-label={`${word}: ${tip}`}
            data-tip={tip} onClick={() => onPick(/** @type {"y"|"m"|"n"} */ (k))}><Icon name={icon} /></button>
        ))}
      </span>
      <span class={`mntrw ${t === "y" || t === "n" ? t : "m"}`} aria-hidden="true">{now}</span>
    </span>
  );
}

/** The item's words in the one editor: Enter or a click away saves, Esc puts them back.
    @param {{value: string, label: string, n: number, onSave: (t: string) => Promise<boolean>}} props */
function ItemText({ value, label, n, onSave }) {
  const m = useContext(MinutesCtx);
  const [ver, setVer] = useState(0);
  const draft = useRef(/** @type {string|null} */ (null));
  const box = useRef(/** @type {HTMLDivElement|null} */ (null));
  const back = () => { draft.current = null; setVer(x => x + 1); };
  const commit = async () => {
    const t = draft.current;
    draft.current = null;
    if (t == null || !t.trim() || t.trim() === value) { if (t != null) setVer(x => x + 1); return; }
    if (!(await onSave(t.trim()))) setVer(x => x + 1);
  };
  const ai = m ? { place: "minutes", project: () => m.project, confidential: () => false, key: () => `minutes:item:${n}` } : undefined;
  return (
    <div class="mnit" ref={box}
      onKeyDownCapture={e => {
        if (e.key === "Escape" && aiBar.value) { e.preventDefault(); e.stopPropagation(); aiBar.value = null; return; }   // review LOW: Esc closes AI first, the words stay
        if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); back(); const a = /** @type {HTMLElement|null} */ (document.activeElement); if (a && box.current && box.current.contains(a)) a.blur(); }
        else if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); e.stopPropagation(); const a = /** @type {HTMLElement|null} */ (document.activeElement); if (a) a.blur(); }
      }}
      onFocusOut={e => { const to = /** @type {Node|null} */ (e.relatedTarget); if (!to || !box.current || !box.current.contains(to)) commit(); }}>
      <SheetEditor key={ver} value={value} rich={false} label={label} multiline={false} ai={ai} onText={t => { draft.current = t; }} />
    </div>
  );
}

/** A dropdown in the row; a change the record refuses puts the old value back.
    @param {{value: string, label: string, options: string[], none: string, cls?: string, onPick: (v: string) => Promise<boolean>|void}} props */
function RowSelect({ value, label, options, none, cls, onPick }) {
  const opts = value && !options.includes(value) ? [value, ...options] : options;
  return (
    <select class={`msel${value ? "" : " empty"}${cls ? " " + cls : ""}`} aria-label={label} value={value || ""}
      onChange={async e => { const el = /** @type {HTMLSelectElement} */ (e.currentTarget), x = el.value;
        if (x !== (value || "") && (await onPick(x)) === false) el.value = value || ""; }}>
      <option value="">{none}</option>
      {opts.map(o => <option key={o} value={o}>{o}</option>)}
    </select>
  );
}

/** A risk's or issue's Priority: a read-only pill (worked out from impact and likelihood, so never picked here); dashed while
    it can't be worked out yet. @param {{v: any, label: string}} props */
function RaidPriority({ v, label }) {
  const pr = String(v.priority || raidPriority(v));
  return <span class={`msel mnro${pr ? ` pr-${pr[0]}` : " empty"}`} tabIndex={0} data-tip={PRIO_TIP} aria-label={`Priority of ${label}: ${pr || "not worked out yet"}. ${PRIO_TIP}`}>{pr || "Priority"}</span>;
}

/** Add details: the person's page with its details form open (as Review's menu on a name does). @param {string} name */
function addDetails(name) {
  go("person", name);
  let k = 0;
  const tick = () => { const b = /** @type {HTMLElement|null} */ (document.getElementById("ppEdit")); if (b) { b.click(); return; } if (++k < 30) requestAnimationFrame(tick); };
  tick();
}

/** Looks like an existing item: Update that one or Keep as new. @param {{item: any, n: number}} props */
function LooksLike({ item, n }) {
  const m = useContext(MinutesCtx);
  const ll = item.looks_like || {}, rec = recOf(ll.id);
  if (!ll.id || ll.kept || ll.merged || !m) return null;
  return (
    <span class="mck mnlooks" data-tip={rec ? `${ll.id}: ${rec.t}` : undefined}>
      <span>Looks like <button type="button" class="linkbtn mnid" onClick={() => openRef(ll.id, () => false)}>{ll.id}</button></span>
      <button type="button" class="linkbtn" data-mnact="update" onClick={() => m.change({ op: "update", n, id: ll.id }, { op: "keep_new", n })}>Update that one</button>
      <button type="button" class="linkbtn" data-mnact="keepnew" onClick={() => m.change({ op: "keep_new", n })}>Keep as new</button>
    </span>
  );
}

/** One row. @param {{r: TrackRow, ctx: SectionCtx, full: boolean}} props */
function MnRow({ r, ctx, full }) {
  const m = /** @type {import("./context.js").MinutesCtxValue} */ (useContext(MinutesCtx));
  const sid = /** @type {keyof typeof MAIN} */ (ctx.section.id), row = r.row, cells = row.cells || {}, n = r.n;
  const item = r.item || {}, v = item.values || {}, isNew = !r.kept && item.op === "new";
  const t = trackOf(ctx.doc, r, m.plan), label = String(cells[MAIN[sid]] || "").slice(0, 80);
  const turn = row.at && row.at.turn ? Number(row.at.turn) : null, hv = hoverTurn.value;
  const lit = !!turn && !!hv && hv.from === "pane" && hv.turn === turn;
  const checks = r.kept ? [] : m.checks.filter(c => c.section === sid && c.n === n);
  const own = checks.find(c => c.kind === "owner" && c.note.endsWith("needs details.")) || null;
  const edit = (/** @type {Record<string, any>} */ values) => m.change({ op: "edit", n, values });
  const ownerField = sid === "decisions" ? "made_by" : "owner";
  const owner = isNew ? String(v[ownerField] || "") : String(cells.owner || cells.by || "");
  const people = shared.REG.filter((/** @type {any} */ p) => !p.hidden).map((/** @type {any} */ p) => String(p.name)).sort();
  const dash = <span class="sub">—</span>;
  const need = t === "y" ? needsOf(ctx.doc, m.plan, m.checks).get(n) : undefined, hide = hiddenBy(need, attnFilter.value);
  const held = row.ref ? ((minutesView.value || {}).withheld || {})[String(row.ref)] || "" : "";    // Cap's #268 review L2: read only
  return (
    <tr class={`mi${lit ? " hl" : ""}${attnFocus.value === n ? " nx" : ""}`} hidden={hide || undefined} data-n={n} data-trk={t} data-ref={row.ref || undefined} data-turn={turn || undefined}
      onMouseEnter={() => { if (turn) hoverTurn.value = { turn, from: "row" }; }} onMouseLeave={() => { if (hoverTurn.value && hoverTurn.value.from === "row") hoverTurn.value = null; }}>
      <td class="mntc"><TrackButtons t={t} label={label} onPick={w => ctx.setDoc(setTrack(ctx.doc, n, w === "m" ? "" : nextTrack(t, w)), "Track")} /></td>
      <td class="mnic">
        {isNew ? <ItemText value={String(v[ROW_FIELD[sid]] || "")} label={`${ctx.section.heading}: ${label}`} n={n} onSave={x => edit({ [ROW_FIELD[sid]]: x })} />
          : <div class="mnit mnit-ro"><Linked text={String(cells[MAIN[sid]] || "")} /></div>}
        {(turn || held || need || own || checks.length || (isNew && item.looks_like) || (!isNew && !r.kept && row.does)) ? (
          <div class="mnrow2">
            {turn ? <button type="button" class={`mntag mnsrc${paneTurn.value === turn ? " on" : ""}`} data-turn={turn} data-mnsrc="1"
              aria-label={`Source: ${row.at.time || ""} in the transcript`} data-tip="Show where this was said" onClick={() => jumpTo(turn)}>{row.at.time ? shortTime(String(row.at.time)) : "Source"}</button> : null}
            {held ? <span class="mck info mnsens" data-tip={`Marked ${held}: shown here as it is; the minutes have one version, so nothing is left out for it`}>
              {held === "Sensitive" ? "Sensitive" : `Sensitive · ${held}`}</span> : null}
            {!isNew && !r.kept && row.does ? <span class="mck info"><Linked text={`${row.does}${/^Closes /.test(row.does) ? " · Looks done" : ""}`} />
              {row.ref ? <button type="button" class="linkbtn mnstaged" data-tip="Open the staged update in Review" onClick={() => m.openItem(String(row.ref))}>Open</button> : null}</span> : null}
            {need && need.owner ? <span class="mnflag2" data-flag="owner">Needs an owner</span> : null}
            {need && need.date ? <span class="mnflag2" data-flag="date">{need.vague ? "Vague date: pick one" : "Needs a date"}</span> : null}
            {own ? <span class="mck" data-check={own.id}><span>{own.quote} needs details</span>
              <button type="button" class="linkbtn" data-ckact="details" onClick={() => addDetails(own.quote)}>Add details</button></span> : null}
            {isNew ? <LooksLike item={item} n={n} /> : null}
            {checks.filter(c => c !== own && !(need && need.owner && c.kind === "owner")).map(c => <CheckMark key={c.id} check={c}>{c.kind === "due" ? "Deadline?" : c.kind === "figure" ? `${c.quote}?` : c.kind === "owner" ? c.note.replace(/\.$/, "") : "Check"}</CheckMark>)}
          </div>) : null}
      </td>
      <td class="mnoc">{isNew ? <RowSelect value={owner} label={`Owner of ${label}`} options={people} none="No owner"
        onPick={x => edit({ [ownerField]: x || null })} /> : owner ? <span>{owner}</span> : dash}</td>
      {full ? <>
        <td class="mndc">{isNew ? <DeadlinePopover due={v.due_date || null} day={m.day} label={label} onSet={w => m.change({ op: "deadline", n, words: w })} />
          : cells.due && cells.due !== "Not set" ? <span>{cells.due}</span> : dash}</td>
        <td class="mnpc">{isNew && sid === "actions" ? <RowSelect value={String(v.priority || "")} label={`Priority of ${label}`} options={MN_PRIOS} none="Priority"
          cls={v.priority ? `pr-${String(v.priority)[0]}` : ""} onPick={x => edit({ priority: x || null })} />
          : sid === "raid" && isNew ? <RaidPriority v={v} label={label} />
          : v.priority ? <span>{v.priority}</span> : dash}</td>
        <td class="mnwc">{isNew && sid !== "decisions" ? <RowSelect value={String(v.workstream || "")} label={`Workstream of ${label}`} options={wsFor(String(v.project || m.project || ""))}
          none="Workstream" onPick={x => edit({ workstream: x || null })} />
          : v.workstream ? <span>{v.workstream}</span> : dash}</td>
      </> : null}
    </tr>
  );
}

/** One aligned table. @param {{ctx: SectionCtx, rows: TrackRow[], kind: string, full: boolean}} props */
function MnTable({ ctx, rows, kind, full }) {
  const m = useContext(MinutesCtx);
  if (attnFilter.value && m) {                      // a chip is pressed: a table with no row to show leaves too
    const need = needsOf(ctx.doc, m.plan, m.checks);
    if (rows.every(r => hiddenBy(need.get(r.n), attnFilter.value))) return null;
  }
  return (
    <table class="mnt">
      <colgroup><col class="c-trk" /><col />{full ? <><col class="c-own" /><col class="c-due" /><col class="c-pri" /><col class="c-ws" /></> : <col class="c-by" />}</colgroup>
      <thead><tr>
        <th scope="col" data-tip={TRACK_TIP} aria-description={TRACK_TIP} tabIndex={0}>Track</th>
        <th scope="col">{kind}</th><th scope="col">{full ? "Owner" : "Made by"}</th>
        {full ? <><th scope="col">Due</th><th scope="col">Priority</th><th scope="col">Workstream</th></> : null}
      </tr></thead>
      <tbody>{rows.map(r => <MnRow key={r.n} r={r} ctx={ctx} full={full} />)}</tbody>
    </table>
  );
}

/** The record's own table, as it is exported (Show as exported, read only, filed): crossed lines left out while a draft.
    @param {{ctx: SectionCtx}} props */
function Plain({ ctx }) {
  const m = useContext(MinutesCtx);
  const s = /** @type {any} */ (ctx.section), cols = s.columns || [], draft = ctx.doc.state === "draft";
  const rows = (s.rows || []).filter((/** @type {any} */ row) => {
    if (row.shown === false) return false;
    const n = rowN(row);
    if (!draft || n == null || !m) return true;
    return trackOf(ctx.doc, { n, section: s.id, row, item: row.ref ? (ctx.doc.items || {})[row.ref] || null : null, kept: !!row.kept_line }, m.plan) !== "n";
  });
  if (!rows.length) return <p>{s.text || "None recorded."}</p>;
  return (
    <table>
      <thead><tr>{cols.map((/** @type {any} */ c) => <th key={c.key}>{c.label}</th>)}</tr></thead>
      <tbody>{rows.map((/** @type {any} */ row, /** @type {number} */ i) => <tr key={row.ref || i} class="mnrow" data-n={rowN(row) ?? undefined}>
        {cols.map((/** @type {any} */ c) => <td key={c.key}>{(row.cells || {})[c.key] || ""}</td>)}</tr>)}</tbody>
    </table>
  );
}

/** A decisions, RAID or actions section (a §4.3 section renderer, byId). @param {{ctx: SectionCtx}} props */
export function ItemTable({ ctx }) {
  const m = useContext(MinutesCtx);
  const s = /** @type {any} */ (ctx.section), sid = s.id;
  const live = ctx.editing && !ctx.exported && !!m && ctx.doc.state === "draft";
  if (!live || !m) return <Plain ctx={ctx} />;
  /** @type {TrackRow[]} */
  const rows = [];
  for (const row of s.rows || []) {
    const n = rowN(row);
    if (n == null || (!row.ref && !row.kept_line) || row.shown === false) continue;
    rows.push({ n, section: sid, row, item: row.ref ? (ctx.doc.items || {})[row.ref] || null : null, kept: !!row.kept_line });
  }
  if (!rows.length) return <p class="sub">{s.text || "None recorded."}</p>;
  if (sid === "decisions") return <MnTable ctx={ctx} rows={rows} kind="Decision" full={false} />;
  if (sid === "actions") return <MnTable ctx={ctx} rows={rows} kind="Action" full />;
  const typeOf = (/** @type {TrackRow} */ r) => {
    const it = r.item || {};
    if (it.op === "update") return "";
    const ty = String((it.values || {}).type || (r.row.cells || {}).type || "");
    return KINDS.some(k => k[0] === ty) ? ty : "Risk";
  };
  return (
    <div class="mnraid">
      {KINDS.map(([ty, many]) => {
        const these = rows.filter(r => typeOf(r) === ty);
        if (!these.length) return null;
        return (
          <div key={many} class="mnkind" data-kind={ty || "update"}>
            <h3 class="mnh3">{many} <span class="n">{these.length}</span></h3>
            <MnTable ctx={ctx} rows={these} kind={ty || "Update"} full />
          </div>
        );
      })}
    </div>
  );
}
