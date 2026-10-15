// @ts-check
/* Notes (v2.1.0 P6, BL-335): the report's words. The summary and This week / Next week (bullets, each with the source tags that
   belong to its line: an item ID, creaite only, never exported), and Current state in two panes ("Where we are", "What happens
   next"; when the second is empty the first takes the full width). Words open for editing on a click (Rich). */
import { Rich } from "./Rich.jsx";

/** @typedef {import("../Sheet.jsx").SectionCtx} SectionCtx */
const TITLES = ["Where we are", "What happens next"];

/** Words with the section's source tags placed after the lines they name. @param {{ctx: SectionCtx, label: string, empty: string}} props */
export function Words({ ctx, label, empty }) {
  const s = ctx.section, tags = s.tags || [], Tag = ctx.Tag;
  const after = (/** @type {string} */ line) => tags.filter(t => t.text && line.includes(t.text)).map(t => <Tag key={t.ref} tag={{ ref: t.ref, text: t.ref }} />);
  return <Rich ctx={ctx} text={s.text} label={label} empty={empty} after={after} />;
}

/** One pane of Current state: the words, edited on a click in the sheet's one editor. @param {{ctx: SectionCtx, i: number}} props */
function StatePane({ ctx, i }) {
  const panes = ctx.section.panes || [], p = panes[i] || { title: "", text: "" };
  return (
    <div class="wr-pane">
      <div class="wr-panet">{p.title || TITLES[i] || ""}</div>
      <Rich ctx={ctx} text={p.text} pane={i} label={p.title || TITLES[i]} empty="Say where things stand" />
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
      <StatePane ctx={ctx} i={0} />
      {two ? <div><StatePane ctx={ctx} i={1} />{ctx.editing && !second ? <button type="button" class="wr-link" onClick={dropSecond}>Remove the second pane</button> : null}</div>
        : ctx.editing ? <div><button type="button" class="wr-link" onClick={addSecond}>+ Add a second pane</button></div> : null}
    </div>);
}
