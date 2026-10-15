// @ts-check
/* Glance (v2.1.0 P6, BL-335): At a glance as a section: the figures in a strip, in the layout's order. While editing, a figure can be
   dragged (or moved with Alt+← and Alt+→) and hidden with its eye; a hidden figure is drawn faded and is left out of the report and
   the exports. The order and what shows go to the layout (`layout.glance`) with the section, as the sheet's contract asks. */
import { useState } from "preact/hooks";
import { editDoc } from "../../../stores/weekly.js";
import { withSection } from "./weeklyDoc.js";

/** @typedef {import("../SheetStub.jsx").SectionCtx} SectionCtx */

/** At a glance. @param {{ctx: SectionCtx}} props */
export function Glance({ ctx }) {
  const { doc, section: s } = ctx, figs = s.figures || [];
  const [drag, setDrag] = useState(/** @type {number|null} */ (null));
  const put = (/** @type {any[]} */ next, /** @type {string} */ why) =>
    editDoc(withSection(doc, s.id, { figures: next }, { glance: next.filter(f => f.shown !== false).map(f => f.key) }), why);
  const move = (/** @type {number} */ from, /** @type {number} */ to) => {
    if (from === to || to < 0 || to >= figs.length) return;
    const next = figs.slice(); const [f] = next.splice(from, 1); next.splice(to, 0, f); put(next, "Figure moved");
  };
  const hide = (/** @type {number} */ i) => put(figs.map((f, j) => j === i ? { ...f, shown: f.shown === false } : f), figs[i].shown === false ? "Figure shown" : "Figure hidden");
  const list = ctx.editing ? figs : figs.filter(f => f.shown !== false);
  return (
    <div>
      <div class="wr-stats" role="list" aria-label={s.heading}>
        {list.map((f, i) => {
          const off = f.shown === false, red = f.key === "overdue" && f.value !== "0";
          return (
            <div key={f.key} role="listitem" class={`wr-stat${off ? " off" : ""}${drag === i ? " dragging" : ""}`} draggable={ctx.editing}
              onDragStart={() => setDrag(i)} onDragEnd={() => setDrag(null)} onDragOver={e => { if (drag != null) e.preventDefault(); }}
              onDrop={e => { e.preventDefault(); if (drag != null) move(drag, i); setDrag(null); }}
              onKeyDown={e => { if (ctx.editing && e.altKey && (e.key === "ArrowLeft" || e.key === "ArrowRight")) { e.preventDefault(); move(i, i + (e.key === "ArrowLeft" ? -1 : 1)); } }}>
              {ctx.editing ? <button type="button" class="wr-eye wr-seye" aria-pressed={off ? "false" : "true"} onClick={() => hide(i)}
                aria-label={`${off ? "Show" : "Hide"} ${f.label}`} data-tip={off ? "Left out of the report: click to show it" : "In the report: click to leave it out"}>{off ? "○" : "◉"}</button> : null}
              <span class={`n${red ? " r" : ""}`}>{f.value}</span>
              <span class="c">{f.label}{f.note ? `, ${f.note}` : ""}</span>
            </div>);
        })}
      </div>
      {ctx.editing ? <div class="wr-count">Drag a figure to reorder it (or Alt with the arrow keys); the eye hides it. Hidden figures are left out of the report and the exports.</div> : null}
    </div>);
}
