// @ts-check
/* Notes (v2.1.0 P6, BL-335): the report's words. The summary and This week / Next week (bullets, each with the source tags that
   belong to its line: an item ID, creaite only, never exported), and Current state in two panes ("Where we are", "What happens
   next"; when the second is empty the first takes the full width). Words open for editing on a click (Rich). */
import { Rich } from "./Rich.jsx";

/** @typedef {import("../SheetStub.jsx").SectionCtx} SectionCtx */
const TITLES = ["Where we are", "What happens next"];

/** Words with the section's source tags placed after the lines they name. @param {{ctx: SectionCtx, label: string, empty: string}} props */
export function Words({ ctx, label, empty }) {
  const s = ctx.section, tags = s.tags || [], Tag = ctx.Tag;
  const after = (/** @type {string} */ line) => tags.filter(t => t.text && line.includes(t.text)).map(t => <Tag key={t.ref} tag={{ ref: t.ref, text: t.ref }} />);
  return <Rich ctx={ctx} text={s.text} label={label} empty={empty} after={after} />;
}

/** One pane of Current state, edited in place as plain words. @param {{ctx: SectionCtx, i: number}} props */
function Pane({ ctx, i }) {
  const panes = ctx.section.panes || [], p = panes[i] || { title: "", text: "" };
  const set = (/** @type {string} */ text) => ctx.update({ panes: Object.assign([], panes.length ? panes : [{ title: "", text: "" }], { [i]: { ...p, text } }) }, "Text edited");
  return (
    <div class="wr-pane">
      <div class="wr-panet">{p.title || TITLES[i] || ""}</div>
      {ctx.editing
        ? <textarea class="sheet-text wr-pta" aria-label={p.title || TITLES[i]} value={p.text} placeholder="Say where things stand" onInput={e => set(/** @type {HTMLTextAreaElement} */ (e.currentTarget).value)} />
        : <div class="wr-rich">{String(p.text || "").split(/\n{2,}/).map((t, j) => t.trim() ? <p key={j}>{t.trim()}</p> : null)}</div>}
    </div>);
}

/** Current state, in two panes. @param {{ctx: SectionCtx}} props */
export function CurrentState({ ctx }) {
  const panes = ctx.section.panes || [], second = !!(panes[1] && String(panes[1].text || "").trim());
  const addSecond = () => ctx.update({ panes: [panes[0] || { title: "", text: "" }, { title: "", text: "" }] }, "Second pane added");
  const dropSecond = () => ctx.update({ panes: panes.slice(0, 1) }, "Second pane removed");
  const two = second || (ctx.editing && panes.length > 1);
  return (
    <div class={`wr-two${two ? "" : " single"}`}>
      <Pane ctx={ctx} i={0} />
      {two ? <div><Pane ctx={ctx} i={1} />{ctx.editing && !second ? <button type="button" class="wr-link" onClick={dropSecond}>Remove the second pane</button> : null}</div>
        : ctx.editing ? <div><button type="button" class="wr-link" onClick={addSecond}>+ Add a second pane</button></div> : null}
    </div>);
}
