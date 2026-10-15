// @ts-check
/* ClientParts (v2.1.0 P8, BL-336): the client report's own section renderers, on the sheet's slots (dev/sprints/v210-contract.md
   §4.3; SheetStub.jsx until P5's Sheet.jsx). Each is a component (hooks need that), handed the sheet's SectionCtx.
   - Health: the client's flag (click it to change it, with the reason the internal report keeps) and its headline; Match
     internal health takes the internal flag and headline.
   - Tables (risks, overdue, asks, decisions): an eye on each row; rows the client may see show by default; "Not in this report"
     lists what the tracker holds that the report leaves out, with Make client-visible… (the standard peek) and, for a Sensitive
     or partner-only item, the plain reason it can never be shown; Add for a row that became client-visible since.
   - Every section: Matching internal or Edited for the client, and Match internal (clientDoc.matchSection: client-safe).
   Everything drawn here is the client document's own content; the internal report is read only. */
import { useEffect, useRef, useState } from "preact/hooks";
import { cellsFor, FLAGS, flagOf, healthDiff, matchSection, matchState, secOf } from "./clientDoc.js";
import { openRef } from "./SheetStub.jsx";
import { crCheck, crDirty, crDoc, crInternal, runCheck } from "../../stores/clientReport.js";

/** @typedef {import("./SheetStub.jsx").SectionCtx} SectionCtx */
/** @typedef {import("./SheetStub.jsx").SheetDoc} SheetDoc */

/** Take a new client document onto the page. @param {SheetDoc} next */
export function setClientDoc(next) { crDoc.value = next; crDirty.value = true; }

/** Match one section to the internal report. @param {string} id */
export function matchOne(id) {
  const d = crDoc.value, i = crInternal.value;
  if (d && i) setClientDoc(matchSection(d, i, id));
}

/** The line above a section's body: Matching internal or Edited for the client, and Match internal. Only while editing.
    @param {{ctx: SectionCtx}} props */
function MatchBar({ ctx }) {
  const d = crDoc.value, i = crInternal.value;
  if (!ctx.editing || !d || !i || ctx.peer) return null;     // in Side by side the sheet's own Match internal (partner.match) is drawn
  const st = matchState(d, i, ctx.section.id);
  if (!st) return null;
  return (
    <div class="crmatch" data-match={ctx.section.id}>
      <span class={`crmstate ${st}`}>{st === "matching" ? "Matching internal" : "Edited for the client"}</span>
      <button type="button" class="btn sm" data-matchone={ctx.section.id} disabled={st === "matching"} onClick={() => matchOne(ctx.section.id)}>Match internal</button>
    </div>
  );
}

/** A section's body with its match line. @param {{ctx: SectionCtx, children?: any}} props */
function Sec({ ctx, children }) {
  return <div class="crsec"><MatchBar ctx={ctx} />{children}</div>;
}

/** A popover under its anchor: Esc and a click outside close it, with focus back on the button that opened it.
    @param {{label: string, onClose: () => void, anchor: {current: HTMLElement|null}, children?: any}} props */
function Pop({ label, onClose, anchor, children }) {
  const box = useRef(/** @type {HTMLDivElement|null} */ (null));
  useEffect(() => {
    const a = anchor.current;
    const first = box.current && /** @type {HTMLElement|null} */ (box.current.querySelector("button,textarea,input"));
    if (first) first.focus();
    const away = (/** @type {MouseEvent} */ e) => { if (box.current && !box.current.contains(/** @type {Node} */ (e.target)) && !(a && a.contains(/** @type {Node} */ (e.target)))) onClose(); };
    document.addEventListener("mousedown", away);
    return () => { document.removeEventListener("mousedown", away); if (a && a.isConnected) a.focus(); };
  }, []);
  return <div class="crpop" role="dialog" aria-label={label} ref={box} onKeyDown={e => { if (e.key === "Escape") { e.stopPropagation(); onClose(); } }}>{children}</div>;
}

/** The client's health: flag, headline, and the popover that changes them (a reason is required when it differs).
    @param {{ctx: SectionCtx}} props */
export function HealthSection({ ctx }) {
  const [open, setOpen] = useState(false);
  const [pick, setPick] = useState("");
  const [why, setWhy] = useState("");
  const btn = useRef(/** @type {HTMLButtonElement|null} */ (null));
  const d = crDoc.value, internal = crInternal.value;
  const flag = flagOf(d) || "On track", inFlag = flagOf(internal), diff = (((d || {}).meta || {}).health_diff) || null;
  const cls = (FLAGS.find(f => f[0] === flag) || FLAGS[0])[1];
  const edit = ctx.editing;
  const begin = () => { setPick(flag); setWhy(diff ? String(diff.reason || "") : ""); setOpen(true); };
  const save = () => {
    if (!d) return;
    if (pick !== inFlag && !why.trim()) return;
    const next = { ...secOf(d, "health") };
    setClientDoc({ ...d, sections: d.sections.map(s => s.id === "health" ? { ...s, data: { ...(next.data || {}), flag: pick } } : s),
      meta: healthDiff(d, inFlag, pick, why) });
    setOpen(false);
  };
  const matchHealth = () => { matchOne("health"); setOpen(false); };
  const needWhy = pick !== inFlag && !why.trim();
  return (
    <div class="crhealth" data-crhealth>
      <div class="crhcol">
        {edit ? <button type="button" class={`crflag ${cls}`} ref={btn} aria-haspopup="dialog" aria-expanded={open ? "true" : "false"} data-crflag onClick={() => open ? setOpen(false) : begin()}>{flag.toUpperCase()}</button>
          : <span class={`crflag ${cls}`}>{flag.toUpperCase()}</span>}
        {edit && inFlag && flag !== inFlag ? <span class="crdif" title={`Internal: ${inFlag}. ${diff && diff.reason ? diff.reason : ""}`} data-crdif>≠ internal: {inFlag}</span> : null}
      </div>
      <div class="crwhy">
        <MatchBar ctx={ctx} />
        <ctx.Text field="text" label="The client's headline" />
      </div>
      {open ? (
        <Pop label="Client health" anchor={btn} onClose={() => setOpen(false)}>
          <b>Client health</b>
          <div class="cropts" role="group" aria-label="Health">
            {FLAGS.map(([name]) => <button key={name} type="button" aria-pressed={pick === name ? "true" : "false"} data-crpick={name} onClick={() => setPick(name)}>{name}</button>)}
          </div>
          <label class="sub" for="crWhy">{pick !== inFlag ? "Why it differs from the internal health (required; kept internally, never on the client's page)" : "The same as the internal health"}</label>
          <textarea id="crWhy" value={why} disabled={pick === inFlag} onInput={e => setWhy(/** @type {HTMLTextAreaElement} */ (e.currentTarget).value)} />
          <div class="crpopacts">
            <button type="button" class="btn sm" data-crmatchhealth onClick={matchHealth}>Match internal health</button>
            <span><button type="button" class="btn sm" onClick={() => setOpen(false)}>Cancel</button>{" "}
              <button type="button" class="btn sm primary" data-crhsave disabled={needWhy} onClick={save}>Save</button></span>
          </div>
        </Pop>
      ) : null}
    </div>
  );
}

/** The header: the client, the period, the internal week the facts lock to, and which logos show.
    @param {{ctx: SectionCtx}} props */
export function HeaderSection({ ctx }) {
  const d = ctx.doc, h = (ctx.section.data || {}), meta = d.meta || {};
  const logos = (d.layout || {}).logos || ["firm", "client", "partner"];
  const toggle = (/** @type {string} */ k) => {
    const next = logos.includes(k) ? logos.filter((/** @type {string} */ x) => x !== k) : [...logos, k];
    setClientDoc({ ...d, layout: { ...(d.layout || {}), logos: ["firm", "client", "partner"].filter(x => x === "firm" || next.includes(x)) } });
  };
  return (
    <div class="crheader">
      <div><b>{h.client || d.client || "Client"}</b></div>
      <div class="sub">{d.project_name || ""}{h.period_start ? ` · ${h.period_start.slice(8, 10)}-${h.period_start.slice(5, 7)} to ${(h.period_end || "").slice(8, 10)}-${(h.period_end || "").slice(5, 7)}-${(h.period_end || "").slice(0, 4)}` : ""}</div>
      <div class="sub">{meta.facts_week ? `Facts from the internal report for week ending ${meta.facts_week.slice(8, 10)}-${meta.facts_week.slice(5, 7)}-${meta.facts_week.slice(0, 4)}${meta.locked ? ", locked" : ""}` : "Facts as the tracker stands now: they lock when the internal report is approved"}</div>
      {ctx.editing ? (
        <div class="crlogos" role="group" aria-label="Logos on this client's reports">
          {[["firm", "The firm"], ["client", "The client"], ["partner", "The partner"]].map(([k, l]) =>
            <label key={k}><input type="checkbox" checked={logos.includes(k)} disabled={k === "firm"} onChange={() => toggle(k)} /> {l}</label>)}
        </div>
      ) : null}
    </div>
  );
}

/** The milestones in the client's words, with an eye on each to pick the list. @param {{ctx: SectionCtx}} props */
export function MilestonesSection({ ctx }) {
  const s = ctx.section, data = s.data || {}, all = /** @type {string[]} */ (data.timeline || []), listed = /** @type {string[]} */ (data.milestones || all);
  const items = ctx.doc.items || {};
  const flip = (/** @type {string} */ ref) => ctx.update({ data: { ...data, milestones: listed.includes(ref) ? listed.filter(x => x !== ref) : all.filter(x => x === ref || listed.includes(x)) } }, "Milestone list changed");
  const rows = ctx.editing ? all : listed;
  if (!all.length) return <Sec ctx={ctx}><p class="sub">No client-visible milestones yet.</p></Sec>;
  return (
    <Sec ctx={ctx}>
      <table class="crtable"><thead><tr>{ctx.editing ? <th class="creye" /> : null}<th>Milestone</th><th>Expected</th><th>State</th></tr></thead><tbody>
        {rows.map(ref => { const it = items[ref] || {}, on = listed.includes(ref);
          return <tr key={ref} class={on ? "" : "crhid"}>
            {ctx.editing ? <td class="creye"><button type="button" class="creyebtn" aria-pressed={on ? "true" : "false"} aria-label={`${on ? "Hide" : "Show"} ${it.title || ref} in the list`} data-crmile={ref} onClick={() => flip(ref)}>{on ? "◉" : "○"}</button></td> : null}
            <td>{it.title || ref}</td><td>{it.shown_date || ""}</td><td><span class="crstate">{it.state || it.status || ""}</span></td></tr>; })}
      </tbody></table>
    </Sec>
  );
}

/** A table section with eyes, the "Not in this report" list and Add. @param {{ctx: SectionCtx}} props */
export function TableSection({ ctx }) {
  const s = ctx.section, rows = s.rows || [], cols = s.columns || [], items = ctx.doc.items || {};
  const check = crCheck.value, group = s.id;
  const left = ctx.editing && check && check.left_out ? check.left_out.items.filter(x => x.group === group && (x.kind === "blocked" || x.kind === "sensitive")) : [];
  const add = ctx.editing && check && check.addable ? check.addable.filter(a => a.section === group) : [];
  const setRows = (/** @type {any[]} */ next, /** @type {string} */ why) => ctx.update({ rows: next }, why);
  const flip = (/** @type {number} */ i) => {
    const r = rows[i], on = r.shown === false;
    setRows(rows.map((x, j) => j !== i ? x : on ? { ...x, shown: true, cells: x.cells || cellsFor(s.id, items[String(x.ref)]) } : { ref: x.ref, shown: false }), on ? "Row shown" : "Row hidden");
  };
  const hiddenN = rows.filter(r => r.shown === false).length;
  const first = cols[0] ? cols[0].key : "";
  return (
    <Sec ctx={ctx}>
      {rows.length ? (
        <table class="crtable" data-crtable={s.id}><thead><tr>{ctx.editing ? <th class="creye" /> : null}{cols.map(c => <th key={c.key}>{c.label}</th>)}</tr></thead><tbody>
          {rows.map((r, i) => {
            const it = items[String(r.ref)] || {}, off = r.shown === false;
            if (off && !ctx.editing) return null;
            const own = s.id === "overdue" && it.client_owned === false;
            return (
              <tr key={String(r.ref) + i} class={off ? "crhid" : ""} data-row={String(r.ref)}>
                {ctx.editing ? <td class="creye"><button type="button" class="creyebtn" aria-pressed={off ? "false" : "true"} aria-label={`${off ? "Show" : "Hide"} ${it.title || r.ref}`} data-creye={String(r.ref)} onClick={() => flip(i)}>{off ? "○" : "◉"}</button></td> : null}
                {off ? <td colSpan={cols.length}>{it.title || cellsFor(s.id, it)[first] || ""} {own ? <span class="crlk">not the client's own</span> : null}</td>
                  : cols.map((c, k) => <td key={c.key}><ctx.Text row={i} col={c.key} label={c.label} />{k === 0 && own ? <span class="crlk">not the client's own</span> : null}</td>)}
              </tr>);
          })}
        </tbody></table>
      ) : <p class="sub">{ctx.editing ? "Nothing client-visible here yet." : ""}</p>}
      {ctx.editing && hiddenN ? <div class="crcount">Showing {rows.length - hiddenN} of {rows.length}. Hidden rows are left out of this client's report.</div> : null}
      {ctx.editing && (left.length || add.length) ? (
        <div class="crnot" data-crnot={group}>
          <div class="crnoth">Not in this report <button type="button" class="linkbtn" data-crrecheck onClick={() => runCheck()}>Check again</button></div>
          <ul>
            {add.map(a => <li key={"a" + a.row.ref}><ctx.ItemRef id={String(a.row.ref)} /> {(a.item && a.item.title) || ""} <span class="crlk ok">now client-visible</span>{" "}
              <button type="button" class="btn sm" data-cradd={String(a.row.ref)} onClick={() => {
                const d = crDoc.value; if (!d) return;
                setClientDoc({ ...d, items: { ...(d.items || {}), [String(a.row.ref)]: a.item }, sections: d.sections.map(x => x.id === s.id ? { ...x, rows: [...(x.rows || []), a.row] } : x) });
              }}>Add</button></li>)}
            {left.map(x => <li key={x.ref} data-crleft={x.ref}><ctx.ItemRef id={x.ref} /> {x.title} <span class={`crlk${x.kind === "sensitive" ? " lock" : ""}`}>{x.kind === "sensitive" ? "⊘ " : ""}{x.why}</span>{" "}
              {x.kind === "blocked" ? <button type="button" class="btn sm" data-crvisible={x.ref} onClick={() => openRef(x.ref, undefined)}>Make client-visible…</button> : null}</li>)}
          </ul>
        </div>
      ) : null}
    </Sec>
  );
}

/** Summary, Progress and Next steps. @param {{ctx: SectionCtx}} props */
export function TextSection({ ctx }) {
  return <Sec ctx={ctx}><ctx.Text rich />{ctx.editing ? (ctx.section.tags || []).map(t => <ctx.Tag key={t.ref} tag={t} />) : null}</Sec>;
}

/** Current state, for the client: the panes are edited here, never the project's own. @param {{ctx: SectionCtx}} props */
export function PanesSection({ ctx }) {
  const panes = ctx.section.panes || [];
  const set = (/** @type {number} */ i, /** @type {string} */ text) => ctx.update({ panes: panes.map((p, j) => j === i ? { ...p, text } : p) }, "Text edited");
  return (
    <Sec ctx={ctx}>
      {panes.map((p, i) => <div key={i}>{p.title ? <h3>{p.title}</h3> : null}
        {ctx.editing ? <textarea class="sheet-text" aria-label={p.title || ctx.section.heading} value={p.text || ""} onInput={e => set(i, /** @type {HTMLTextAreaElement} */ (e.currentTarget).value)} /> : <p>{p.text}</p>}</div>)}
    </Sec>
  );
}

/** At a glance: the client's three figures. @param {{ctx: SectionCtx}} props */
export function FiguresSection({ ctx }) {
  return <div class="figures crfigs">{(ctx.section.figures || []).filter(f => f.shown !== false).map(f =>
    <div key={f.key} class="figure"><b>{f.value}</b>{f.label}{f.note ? <span class="sub"> {f.note}</span> : null}</div>)}</div>;
}

/** The renderers for the client page, by section id. */
export const CLIENT_RENDERERS = {
  byId: {
    header: (/** @type {SectionCtx} */ ctx) => <HeaderSection ctx={ctx} />, health: (/** @type {SectionCtx} */ ctx) => <HealthSection ctx={ctx} />,
    glance: (/** @type {SectionCtx} */ ctx) => <FiguresSection ctx={ctx} />, milestones: (/** @type {SectionCtx} */ ctx) => <MilestonesSection ctx={ctx} />,
    current_state: (/** @type {SectionCtx} */ ctx) => <PanesSection ctx={ctx} />,
  },
  byType: { text: (/** @type {SectionCtx} */ ctx) => <TextSection ctx={ctx} />, table: (/** @type {SectionCtx} */ ctx) => <TableSection ctx={ctx} /> },
};
