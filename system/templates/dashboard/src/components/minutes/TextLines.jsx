// @ts-check
/* TextLines (v2.1.0 P7, BL-338 points 3 to 5): a text section of the minutes (the summary, updates by topic with their flags,
   open questions, what wasn't covered, the source) drawn line by line, each line drawn from the transcript with its time tag
   (P4's section `tags`: {ref: "transcript", turn, time}). A tag's click scrolls the transcript pane to what was said; ✕ on it
   (shown on hover or focus) takes the tag off. A check's words are underlined in the line. Edit, or a click on a line, opens
   the section in the sheet's Text (the one editor); Done goes back to the lines.
   With the distributed version on, each line can be marked Internal only (kept in the record's layout, so it is saved with
   the page). Each topic of Updates is a block with ctx.level, so Side by side keeps its heading level with its partner's.
   Exported or read only: the lines alone, no tags, checks or controls. */
import { useContext, useState } from "preact/hooks";
import { Checked } from "./Checks.jsx";
import { MinutesCtx } from "./context.js";
import { isInternal, mdLines, lineTag, toggleInternal } from "./minutesDoc.js";
import { jumpTo } from "./TranscriptPane.jsx";

/** @typedef {import("../report/Sheet.jsx").SectionCtx} SectionCtx */
/** @typedef {import("./minutesDoc.js").Line} Line */
/** @typedef {import("./minutesDoc.js").TimeTag} TimeTag */

/** "00:02:11" as "02:11" (hours only when there are some). @param {string} t */
export const shortTime = t => String(t || "").replace(/^00:/, "");

/** A time tag: a click shows what was said; ✕ takes it off. @param {{tag: TimeTag, onRemove?: () => void}} props */
export function TimeTag({ tag, onRemove }) {
  return (
    <span class="mntagw">
      <button type="button" class="mntag" data-turn={tag.turn} aria-label={`Show in the transcript: ${tag.time}`}
        onClick={() => { if (tag.turn) jumpTo(tag.turn); }}>{shortTime(tag.time || "")}</button>
      {onRemove ? <button type="button" class="mntagx" aria-label={`Remove the time tag ${tag.time}`} onClick={onRemove}>✕</button> : null}
    </span>
  );
}

/** One line, with its flag, its checks underlined, its tag and its Internal only mark.
    @param {{ctx: SectionCtx, line: Line, i: number, li: boolean, onEdit: () => void}} props */
function TextLine({ ctx, line, i, li, onEdit }) {
  const m = useContext(MinutesCtx), s = ctx.section, live = ctx.editing && !ctx.exported;
  const tags = /** @type {TimeTag[]} */ (s.tags || []), tag = live ? lineTag(line, tags) : null;
  const checks = live && m ? m.checks.filter(c => c.section === s.id && c.line === i) : [];
  const internal = m ? isInternal(m.doc, s.id, { text: line.text }) : false;
  const Tag = li ? "li" : "p";
  return (
    <Tag class={`mnline${internal ? " internal" : ""}`} data-line={i}>
      {line.flag ? <b class="mnflag">{line.flag}</b> : null}
      {line.flag ? " " : null}
      {live ? <span class="mntext" onClick={e => { if (!(/** @type {HTMLElement} */ (e.target)).closest("button")) onEdit(); }}><Checked text={line.text} checks={checks} /></span>
        : <span>{line.text}</span>}
      {tag ? <TimeTag tag={tag} onRemove={() => ctx.update({ tags: tags.filter(t => t !== tag) }, "Time tag removed")} /> : null}
      {live && m && m.distributed && s.type !== "header" ? (
        <button type="button" class={`mnio${internal ? " on" : ""}`} aria-pressed={internal ? "true" : "false"}
          aria-label={`Internal only: ${line.text.slice(0, 60)}`} onClick={() => m.setDoc(toggleInternal(m.doc, s.id, { text: line.text }), internal ? "Shown to attendees" : "Internal only")}>
          Internal only</button>) : null}
    </Tag>
  );
}

/** Lines grouped into blocks: one per topic (a bold heading and its lines), else one. @param {Line[]} ls */
function blocks(ls) {
  /** @type {{topic: Line|null, items: {line: Line, i: number}[]}[]} */
  const out = [];
  ls.forEach((line, i) => {
    if (line.kind === "topic" || !out.length) out.push({ topic: line.kind === "topic" ? line : null, items: [] });
    if (line.kind !== "topic") out[out.length - 1].items.push({ line, i });
  });
  return out;
}

/** A text section, line by line. @param {{ctx: SectionCtx}} props */
export function TextLines({ ctx }) {
  const [ed, setEd] = useState(false);
  const s = ctx.section, { Text } = ctx;
  if (ctx.editing && ed) {
    return (
      <div class="mnedit">
        <Text field="text" rich label={s.heading} />
        <button type="button" class="btn sm" onClick={() => setEd(false)}>Done</button>
      </div>
    );
  }
  const ls = mdLines(s.text || "");
  return (
    <div class="mnlines">
      {blocks(ls).map((b, k) => {
        const bullets = b.items.some(x => x.line.kind === "bullet");
        const body = b.items.map(({ line, i }) => <TextLine key={i} ctx={ctx} line={line} i={i} li={bullets} onEdit={() => setEd(true)} />);
        return (
          <div key={k} class="mnblock" {...(b.topic ? ctx.level(`topic:${b.topic.text}`) : {})}>
            {b.topic ? <h3 class="mntopic">{b.topic.text}</h3> : null}
            {bullets ? <ul>{body}</ul> : body}
          </div>
        );
      })}
      {ctx.editing ? <button type="button" class="linkbtn mnedbtn" aria-label={`Edit ${s.heading}`} onClick={() => setEd(true)}>Edit</button> : null}
    </div>
  );
}
