// @ts-check
/* TextLines (v2.1.0 P7, BL-338 points 3 to 5): a text section of the minutes (the summary, updates by topic with their flags,
   open questions, what wasn't covered, the source) drawn line by line, each line drawn from the transcript with its time tag
   (P4's section `tags`: {ref: "transcript", turn, time}). A tag's click scrolls the transcript pane to what was said; ✕ on it
   (shown on hover or focus) takes the tag off. A check's words are underlined in the line. Edit, or a click on a line, opens
   the section in the sheet's Text (the one editor); there is no Done button (#302): edits save as you go, and a click
   away or Esc goes back to the lines.
   #268: one version only, so no line is marked Internal only. The summary is edited where it stands (SummaryText).
   Each topic of Updates is a block with ctx.level.
   Exported or read only: the lines alone, no tags, checks or controls. */
import { useContext, useEffect, useRef, useState } from "preact/hooks";
import { SheetEditor } from "../report/SheetText.jsx";
import { Checked } from "./Checks.jsx";
import { MinutesCtx } from "./context.js";
import { mdLines, lineTag } from "./minutesDoc.js";
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

/** One line, with its flag, its checks underlined and its tag.
    @param {{ctx: SectionCtx, line: Line, i: number, li: boolean, onEdit: () => void}} props */
function TextLine({ ctx, line, i, li, onEdit }) {
  const m = useContext(MinutesCtx), s = ctx.section, live = ctx.editing && !ctx.exported;
  const tags = /** @type {TimeTag[]} */ (s.tags || []), tag = live ? lineTag(line, tags) : null;
  const checks = live && m ? m.checks.filter(c => c.section === s.id && c.line === i) : [];
  const Tag = li ? "li" : "p";
  return (
    <Tag class="mnline" data-line={i}>
      {line.flag ? <b class="mnflag">{line.flag}</b> : null}
      {line.flag ? " " : null}
      {live ? <span class="mntext" onClick={e => { if (!(/** @type {HTMLElement} */ (e.target)).closest("button")) onEdit(); }}><Checked text={line.text} checks={checks} /></span>
        : <span>{line.text}</span>}
      {tag ? <TimeTag tag={tag} onRemove={() => ctx.update({ tags: tags.filter(t => t !== tag) }, "Time tag removed")} /> : null}
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
  const box = useRef(/** @type {HTMLDivElement|null} */ (null));
  const s = ctx.section, { Text } = ctx, open = ctx.editing && ed;
  useEffect(() => {                                    // #302: no Done button: a click away (not on the AI bar or its card) goes back to the lines
    if (!open) return undefined;
    const away = (/** @type {PointerEvent} */ e) => {
      const t = /** @type {HTMLElement|null} */ (e.target);
      if (t && box.current && !box.current.contains(t) && !t.closest("#aiBarBox, .aisug, .ddmenu, .snack, #snack")) setEd(false);
    };
    document.addEventListener("pointerdown", away, true);
    return () => document.removeEventListener("pointerdown", away, true);
  }, [open]);
  if (open) {
    return (
      <div class="mnedit" ref={box} onKeyDown={e => { if (e.key === "Escape" && !e.defaultPrevented) { e.preventDefault(); setEd(false); } }}>
        <Text field="text" rich label={s.heading} />
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

/** #268: the summary, edited where it stands in the one editor (Tiptap, with AI on selected text as elsewhere): every change is
    kept on the page and saved by the sheet; a click away keeps it; Esc puts back the words it had when the editing began.
    Show as exported, read only or filed: its lines. @param {{ctx: SectionCtx}} props */
export function SummaryText({ ctx }) {
  const m = useContext(MinutesCtx);
  const s = ctx.section, [ver, setVer] = useState(0);
  const start = useRef(/** @type {string|null} */ (null));
  const box = useRef(/** @type {HTMLDivElement|null} */ (null));
  if (!ctx.editing || ctx.exported || !m) return <TextLines ctx={ctx} />;
  const text = String(s.text || "");
  const checks = m.checks.map((c, n) => ({ ...c, n })).filter(c => c.section === s.id && c.line == null);
  const ai = { place: "minutes", project: () => m.project, confidential: () => false, key: () => `minutes:${s.id}` };
  return (
    <div class="mnsum-ed" ref={box} data-mnsum=""
      onFocusIn={() => { if (start.current == null) start.current = text; }}
      onFocusOut={e => { const to = /** @type {Node|null} */ (e.relatedTarget); if (!to || !box.current || !box.current.contains(to)) start.current = null; }}
      onKeyDownCapture={e => {
        if (e.key !== "Escape" || start.current == null) return;
        e.preventDefault(); e.stopPropagation();
        const was = start.current;
        start.current = null;
        if (was !== text) ctx.update({ text: was }, "Summary put back");
        setVer(x => x + 1);
        const a = /** @type {HTMLElement|null} */ (document.activeElement); if (a && box.current && box.current.contains(a)) a.blur();
      }}>
      <SheetEditor key={ver} value={text} rich label={s.heading || "Summary"} ai={ai} checks={checks} onText={t => ctx.update({ text: t }, "Summary edited")} />
    </div>
  );
}
