// @ts-check
/* ItemRow (v2.1.0 P7, BL-338 points 6 to 9): a decision, RAID item or action row of the minutes. The rows are the staged items
   themselves (P4: row ref "@n"), so every change here is one of the record's changes (/api/minutes/save {op}) and the row and
   its item change together; nothing needs reconciling.
   - What the row does, as P4 words it (New action, Closes ABC-A-002 · Looks done, Records ABC-D-004 as made, Looks like…); a
     click opens the staged item in the peek, an ID in it opens that item.
   - The words edited in place (saved when the field is left); the owner picked from the people register (an owner the
     register doesn't know can be remembered as an alias, BL-55); the deadline from the deadline popover.
   - Looks like an existing item (BL-221): Update that one (with What changes) or Keep as new.
   - ✕ Remove (the item and its line, or Keep the line only), with Undo on the toast.
   - Internal only, when the distributed version is on.
   Exported or read only: the cells alone. */
import { useContext, useRef, useState } from "preact/hooks";
import { Menu } from "../Menu.jsx";
import { openRef } from "../report/SheetStub.jsx";
import { CheckMark } from "./Checks.jsx";
import { MinutesCtx } from "./context.js";
import { DeadlinePopover } from "./DeadlinePopover.jsx";
import { isInternal, toggleInternal } from "./minutesDoc.js";
import { Pop } from "./Pop.jsx";
import { TimeTag } from "./TextLines.jsx";
import { A, DEC, R } from "../../core/data.js";
import { fd } from "../../core/page.js";
import { shared } from "../../core/state.js";
import { regAddAlias, unknownOwner } from "../../settings.js";

/** @typedef {import("../report/SheetStub.jsx").RowCtx} RowCtx */
/** @typedef {import("./minutesDoc.js").Check} Check */

const MAIN = { actions: "action", decisions: "decision", raid: "description" };
const FIELD = { actions: "description", decisions: "decision", raid: "description" };
const TYPES = ["Risk", "Issue", "Assumption", "Dependency"];
const ID = /\b[A-Z][A-Z0-9]{2,6}-(?:[ADRM]-)?\d{3,}\b/g;

/** A tracker item by its ID (actions, RAID, decisions), or null. @param {string} id */
const recOf = id => A.find(x => x.id === id) || R.find(x => x.id === id) || DEC.find(x => x.id === id) || null;

/** What a row does, its IDs opening the peek. @param {{does: string, row: any, onOpen: (ref: string) => void}} props */
function Does({ does, row, onOpen }) {
  const parts = [], s = String(does || "");
  let i = 0;
  for (const m of s.matchAll(ID)) {
    parts.push(s.slice(i, m.index));
    parts.push(<button key={m.index} type="button" class="linkbtn mnid" onClick={() => openRef(m[0], () => false)}>{m[0]}</button>);
    i = (m.index || 0) + m[0].length;
  }
  parts.push(s.slice(i));
  const done = /^Closes /.test(s);
  return (
    <span class={`mndoes${/^New /.test(s) ? " new" : ""}`}>
      <button type="button" class="linkbtn mnopen" aria-label={`Open the staged item: ${s}`} onClick={() => onOpen(row.ref)}>Open</button>
      <span class="mndoes-t">{parts}{done ? " · Looks done" : ""}</span>
    </span>
  );
}

/** The owner, picked from the people register. @param {{owner: string, label: string, n: number, field: string, check?: Check|null,
    onPick: (name: string) => Promise<boolean>}} props */
function OwnerPicker({ owner, label, n, field, check, onPick }) {
  const [open, setOpen] = useState(false), [q, setQ] = useState(""), [remember, setRemember] = useState(true);
  const btn = useRef(/** @type {HTMLButtonElement|null} */ (null));
  const people = shared.REG.filter((/** @type {any} */ p) => !p.hidden).map((/** @type {any} */ p) => p.name).sort();
  const shown = people.filter((/** @type {string} */ p) => !q || p.toLowerCase().includes(q.toLowerCase())).slice(0, 30);
  const unknown = !!owner && owner !== "TBC" && unknownOwner(owner);
  const pick = async (/** @type {string} */ name) => {
    if (!(await onPick(name))) return;
    setOpen(false);
    if (unknown && remember && name !== owner) regAddAlias(name, owner);
  };
  return (
    <span class="mnpopw">
      <button type="button" ref={btn} class={`btn sm mnowner${check ? " mncheck" : ""}`} data-owner={n} aria-haspopup="dialog" aria-expanded={open ? "true" : "false"}
        aria-label={`${field === "made_by" ? "Made by" : "Owner"}: ${owner || "not set"}. Change it for ${label}`} data-tip={check ? check.note : undefined}
        onClick={() => setOpen(!open)}>{owner || "TBC"}</button>
      <Pop open={open} onClose={() => setOpen(false)} label={`Owner for ${label}`} anchor={btn} focus="input">
        <input class="pkq" type="search" aria-label="Find a person in the register" placeholder="Find a person" value={q}
          onInput={e => setQ(/** @type {HTMLInputElement} */ (e.currentTarget).value)}
          onKeyDown={e => { if (e.key === "Enter" && shown.length) { e.preventDefault(); pick(shown[0]); } }} />
        <div role="listbox" aria-label="People in the register">
          {shown.length ? shown.map((/** @type {string} */ p) => (
            <button key={p} type="button" role="option" class="pkopt" aria-selected={p === owner ? "true" : "false"} onClick={() => pick(p)}>{p}</button>))
            : <p class="sub">No match in the people register.</p>}
        </div>
        {unknown ? <label class="mnremember"><input type="checkbox" checked={remember} onChange={e => setRemember(/** @type {HTMLInputElement} */ (e.currentTarget).checked)} />
          Remember “{owner}” as their alias</label> : null}
      </Pop>
    </span>
  );
}

/** Looks like an existing item: Update that one (with What changes) or Keep as new. @param {{item: any, n: number}} props */
function LooksLike({ item, n }) {
  const m = useContext(MinutesCtx);
  const [open, setOpen] = useState(false);
  const btn = useRef(/** @type {HTMLButtonElement|null} */ (null));
  const ll = item.looks_like || {}, rec = recOf(ll.id), v = item.values || {};
  if (!ll.id || ll.kept || ll.merged || !m) return null;
  const changes = [
    `Latest update: “${(v.description || v.decision || "").slice(0, 120)}”`,
    ...(v.due_date && rec && rec.due !== v.due_date ? [`Due date: ${rec.due ? fd(rec.due) : "not set"} → ${fd(v.due_date)}`] : []),
    "Title, owner, priority and response stay as they are",
    "The earlier update is kept in the history",
    "These minutes are added as a source",
  ];
  return (
    <span class="mnlooks">
      <span>Looks like <button type="button" class="linkbtn mnid" onClick={() => openRef(ll.id, () => false)}>{ll.id}</button>{ll.why ? <span class="sub"> · {ll.why}</span> : null}</span>
      <button type="button" class="btn sm" data-mnact="update" onClick={() => m.change({ op: "update", n, id: ll.id }, { op: "keep_new", n })}>Update that one</button>
      <span class="mnpopw">
        <button type="button" ref={btn} class="linkbtn" aria-haspopup="dialog" aria-expanded={open ? "true" : "false"} onClick={() => setOpen(!open)}>What changes</button>
        <Pop open={open} onClose={() => setOpen(false)} label={`What changes on ${ll.id}`} anchor={btn} wide>
          <p class="mnck-note">Updating {ll.id}{rec ? ` (${rec.t})` : ""}:</p>
          <ul class="mnchanges">{changes.map(c => <li key={c}>{c}</li>)}</ul>
        </Pop>
      </span>
      <button type="button" class="btn sm" data-mnact="keepnew" onClick={() => m.change({ op: "keep_new", n })}>Keep as new</button>
    </span>
  );
}

/** A cell's words, edited in place: saved through the record when the field is left changed.
    @param {{value: string, label: string, onSave: (t: string) => Promise<boolean>}} props */
function CellText({ value, label, onSave }) {
  const [t, setT] = useState(/** @type {string|null} */ (null));
  const shown = t == null ? value : t;
  const commit = async () => { if (t != null && t.trim() && t !== value) { if (!(await onSave(t.trim()))) return; } setT(null); };
  return <textarea class="mncell" rows={1} aria-label={label} value={shown} onInput={e => setT(/** @type {HTMLTextAreaElement} */ (e.currentTarget).value)}
    onBlur={commit} onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); /** @type {HTMLTextAreaElement} */ (e.currentTarget).blur(); }
      if (e.key === "Escape" && t != null) { e.preventDefault(); e.stopPropagation(); setT(null); } }} />;
}

/** A row kept as a line only: no item, with the item brought back on request. @param {{rc: RowCtx}} props */
function KeptLine({ rc }) {
  const m = useContext(MinutesCtx), cols = rc.section.columns || [], main = MAIN[/** @type {keyof MAIN} */ (rc.section.id)];
  const n = Number(String(/** @type {any} */ (rc.row).was || "").replace("@", ""));
  return (
    <tr class="mnrow kept" data-n={n}>
      {cols.map(c => <td key={c.key}>{(rc.row.cells || {})[c.key] || ""}
        {c.key === main && rc.editing && m ? <div class="mnbar"><span class="sub">The line only: no item is made.</span>
          <button type="button" class="linkbtn" onClick={() => m.change({ op: "restore", n })}>Make it an item again</button></div> : null}</td>)}
    </tr>
  );
}

/** One item row (a §4.3 row renderer). @param {{rc: RowCtx}} props */
export function ItemRow({ rc }) {
  const m = useContext(MinutesCtx);
  const row = /** @type {any} */ (rc.row), s = rc.section, cols = s.columns || [], sid = /** @type {keyof MAIN} */ (s.id);
  if (row.kept_line) return <KeptLine rc={rc} />;
  if (row.shown === false && !rc.editing) return null;
  const item = rc.item || {}, n = row.n, cells = row.cells || {}, isNew = item.op === "new";
  const live = rc.editing && !rc.exported && !!m && !!item.op;
  if (!live || !m) return <tr class="mnrow" data-n={n}>{cols.map(c => <td key={c.key}>{cells[c.key] || ""}</td>)}</tr>;
  const label = (cells[MAIN[sid]] || "").slice(0, 80), checks = m.checks.filter(c => c.section === s.id && c.n === n);
  const own = checks.find(c => c.field === "owner") || null, internal = isInternal(m.doc, s.id, { ref: row.ref });
  const edit = (/** @type {Record<string, any>} */ values) => m.change({ op: "edit", n, values });
  const remove = (/** @type {string} */ how) => m.change({ op: "remove", n, keep_line: how === "keep" }, { op: "restore", n });
  /** @param {{key: string}} c */
  const cell = c => {
    if (!isNew) return cells[c.key] || "";
    if (c.key === "owner" || c.key === "by") return <OwnerPicker owner={(item.values || {})[c.key === "by" ? "made_by" : "owner"] || ""} label={label} n={n}
      field={c.key === "by" ? "made_by" : "owner"} check={own} onPick={name => edit({ [c.key === "by" ? "made_by" : "owner"]: name })} />;
    if (c.key === "due") return <DeadlinePopover due={(item.values || {}).due_date || null} day={m.day} label={label} onSet={words => m.change({ op: "deadline", n, words })} />;
    if (c.key === "type") return <select class="mntype" aria-label={`Type of ${label}`} value={(item.values || {}).type || "Risk"}
      onChange={e => edit({ type: /** @type {HTMLSelectElement} */ (e.currentTarget).value })}>{TYPES.map(t => <option key={t}>{t}</option>)}</select>;
    if (c.key === MAIN[sid]) return <CellText value={(item.values || {})[FIELD[sid]] || ""} label={`${s.heading}: ${label}`} onSave={t => edit({ [FIELD[sid]]: t })} />;
    return cells[c.key] || "";
  };
  return (
    <tr class={`mnrow${internal ? " internal" : ""}`} data-n={n} data-ref={row.ref}>
      {cols.map(c => (
        <td key={c.key} class={`mncol-${c.key}`}>
          {cell(c)}
          {c.key === MAIN[sid] ? (
            <div class="mnbar">
              <Does does={row.does || ""} row={row} onOpen={m.openItem} />
              {row.at && row.at.time ? <TimeTag tag={{ ref: "transcript", turn: row.at.turn, time: row.at.time, text: "" }} /> : null}
              {isNew ? <LooksLike item={item} n={n} /> : null}
              {checks.filter(c => c.field !== "owner" || !own).map(c => <CheckMark key={c.id} check={c}>{c.kind === "due" ? "Deadline?" : c.kind === "figure" ? `${c.quote}?` : "Check"}</CheckMark>)}
              {own ? <CheckMark check={own}>{own.note}</CheckMark> : null}
              {m.distributed ? <button type="button" class={`mnio${internal ? " on" : ""}`} aria-pressed={internal ? "true" : "false"} aria-label={`Internal only: ${label}`}
                onClick={() => m.setDoc(toggleInternal(m.doc, s.id, { ref: row.ref }), internal ? "Shown to attendees" : "Internal only")}>Internal only</button> : null}
              <Menu label="Remove" icon="x" btnCls="btn sm mnrm" menuLabel={`Remove ${label}`} data={{ mnremove: String(n) }}
                items={[{ id: "remove", name: "Remove the item and its line", line: "Nothing is made; the line leaves the minutes", icon: "x" },
                  { id: "keep", name: "Keep the line only", line: "The words stay in the minutes; no item is made", icon: "list" }]}
                onPick={remove} />
            </div>) : null}
        </td>
      ))}
    </tr>
  );
}
