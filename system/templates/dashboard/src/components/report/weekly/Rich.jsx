// @ts-check
/* Rich (v2.1.0 P6): words on the report page. Shown as the page shows them (paragraphs, bullets, bold, italic); a click, or Enter,
   opens the sheet's Text for those words (the sheet's one editor), and leaving it shows them again.
   Read only (approved, or Show as exported): the words and nothing to click. */
import { useEffect, useRef, useState } from "preact/hooks";
import { wkInline, wkMdBlocks } from "./weeklyDoc.js";

/** @typedef {import("../Sheet.jsx").SectionCtx} SectionCtx */

/** One line with its bold and italic marks. @param {{line: string}} props */
export function RpLine({ line }) {
  return <>{wkInline(line).map((p, i) => p.b ? <b key={i}>{p.s}</b> : p.i ? <i key={i}>{p.s}</i> : p.s)}</>;
}

/** Markdown as blocks. `after(line)` may add something after a bullet or a line (a source tag).
    @param {{text: string|null|undefined, after?: (line: string) => any}} props */
export function Md({ text, after }) {
  return <>{wkMdBlocks(text).map((b, i) => b.t === "ul"
    ? <ul key={i}>{b.lines.map((l, j) => <li key={j}><RpLine line={l} />{after ? after(l) : null}</li>)}</ul>
    : <p key={i}>{b.lines.map((l, j) => <span key={j}><RpLine line={l} />{after ? after(l) : null}{j < b.lines.length - 1 ? " " : ""}</span>)}</p>)}</>;
}

/** Words that open for editing on a click.
    @param {{ctx: SectionCtx, text: string|null|undefined, field?: string, pane?: number, row?: number, col?: string, label?: string, cls?: string,
      empty?: string, after?: (line: string) => any}} props */
export function Rich({ ctx, text, field, pane, row, col, label, cls = "", empty = "Click to write", after }) {
  const [on, setOn] = useState(false), box = useRef(/** @type {HTMLDivElement|null} */ (null));
  useEffect(() => { if (on) /** @type {HTMLElement|null} */ (box.current?.querySelector("textarea,[contenteditable]"))?.focus(); }, [on]);
  const { Text } = ctx;
  if (!ctx.editing) return <div class={`wr-rich ${cls}`}><Md text={text} after={after} /></div>;
  if (on) return (
    <div class={`wr-rich wr-open ${cls}`} ref={box}
      onFocusOut={e => { const to = /** @type {HTMLElement|null} */ (e.relatedTarget); if (!to || !(box.current?.contains(to) || (to.closest && to.closest("#aiLayer, .linkpop")))) setOn(false); }}   /* the AI bar and the link form are the editor's own, outside its box */
      onKeyDown={e => { if (e.key === "Escape") { e.stopPropagation(); setOn(false); } }}>
      <Text field={field} pane={pane} row={row} col={col} label={label} rich />
    </div>);
  return (
    <div class={`wr-rich wr-edit ${cls}`} role="button" tabindex={0} aria-label={`${label || ctx.section.heading}: edit`}
      onClick={e => { if (!(/** @type {HTMLElement} */ (e.target)).closest("button,a")) setOn(true); }}
      onKeyDown={e => { if ((e.key === "Enter" || e.key === " ") && e.target === e.currentTarget) { e.preventDefault(); setOn(true); } }}>
      {String(text || "").trim() ? <Md text={text} after={after} /> : <span class="sub">{empty}</span>}
    </div>);
}
