// @ts-check
/* AiSelect (BL-301 D, v20-ai-select; #117): AI on selected text, in every editor whose place the place table (stores/aiEdit.js
   AI_PLACE_TABLE) switches on: v2.1.0 Notes and Current state; the Email draft and the plain fields are built and off. Three pieces,
   drawn in one layer (#aiLayer, on the body, fixed, so they sit over whatever page the editor is on), each placed with
   core/caretPlace.js placeAtCaret, the placement the `/` menu has:
   - the sparkle in the margin beside a non-empty selection (AiSpark); a click opens the bar under the selection, Esc or a click
     elsewhere closes both;
   - the bar (AiBar), two zones: FORMATTING (Turn into: instant, no Claude, a toast with Undo; Notes only) apart from the tinted AI zone
     (Format notes for several paragraphs, then the place's groups: Improve, Structure or Tone, Make into, and Ask…, which turns the bar
     into a box for an instruction: Enter asks, Esc goes back). The group menus open on hover and fold when the pointer leaves;
   - the suggestion: the option's name, the suggested text (or, with Show changes, what it takes out and puts in, word by word),
     the plain-code check's notes, and Accept, Discard, Try again and Show changes. Nothing changes until Accept. A confidential
     text asks first, once.
   Keyboard: select text (⌘A for all of it) and press Alt+/ to open the bar with the first AI menu open; ← → move along the bar, ↓ opens a
   menu, Esc folds a menu, then the bar (focus goes back to the text); in the suggestion ⌘↵ accepts and Esc discards. The bar sets its own
   names (data-aibar on the editor, aria-expanded on the sparkle) and none of the `/` menu's (aria-expanded, aria-haspopup, aria-controls
   on the editor), and an input method that is composing is never read. Text only through JSX. The store is stores/aiEdit.js. */
import { render } from "preact";
import { useEffect, useLayoutEffect, useRef, useState } from "preact/hooks";
import { Icon } from "./Icon.jsx";
import { Menu } from "./Menu.jsx";
import { ED_HOOKS, edTurnKind } from "../core/editor.js";
import { placeAtCaret } from "../core/caretPlace.js";
import { AI_GROUPS, AI_OPTIONS, AI_PLACE_TABLE, aiAccept, aiActionsFor, aiAttach, aiBar, aiBarClose, aiChanges, aiDiff, aiDiscard, aiItems, aiName, aiRetry, aiRun,
  aiRunAction, aiSend, aiSug, aiToggle, aiTurn } from "../stores/aiEdit.js";

/** Turn into's kinds, in the menu's order: [id, name]. */
const TURN = [["text", "Text"], ["h1", "Heading 1"], ["h2", "Heading 2"], ["h3", "Heading 3"], ["ul", "Bulleted list"],
  ["ol", "Numbered list"], ["task", "Checklist"], ["quote", "Quote"]];

/** The left edge of a selection (the smaller of its two ends', so a selection that wraps puts the bar at its left). @param {any} view @param {number} from @param {number} to */
const leftOf = (view, from, to) => {
  try { return Math.min(view.coordsAtPos(from).left, view.coordsAtPos(to).left); } catch (e) { return 16; }
};

/** The margin sparkle: appears beside a non-empty selection; a click opens (or folds) the bar. @param {{bar: import("../stores/aiEdit.js").Bar}} props */
export function AiSpark({ bar }) {
  const el = useRef(/** @type {HTMLButtonElement | null} */ (null));
  useLayoutEffect(() => {          /* in the editor's left margin, level with the selection's first line */
    if (!el.current || bar.h.editor.isDestroyed) return undefined;
    return placeAtCaret(bar.h.editor.view, bar.from, el.current, { level: -2, x: () => bar.h.el.getBoundingClientRect().left - 36 });
  }, [bar.h, bar.from, bar.to]);
  return (
    <button type="button" class="aispark" id="aiSpark" ref={el} aria-label="AI and formatting on the selected text" data-tip="AI and formatting on the selected text (Alt+/)"
      aria-expanded={bar.shown ? "true" : "false"} aria-controls="aiBarBox"
      onClick={() => aiToggle()}
      onKeyDown={e => { if (e.key === "Escape" && bar.shown) { e.preventDefault(); e.stopPropagation(); aiBarClose(); } }}>
      <Icon name="spark" />
    </button>
  );
}

/** The bar under a selection: Formatting (Turn into, no AI) apart from the tinted AI zone. @param {{bar: import("../stores/aiEdit.js").Bar}} props */
export function AiBar({ bar }) {
  const [asking, setAsking] = useState(false);
  const [words, setWords] = useState("");
  const box = useRef(/** @type {HTMLDivElement | null} */ (null));
  const input = useRef(/** @type {HTMLInputElement | null} */ (null));
  useEffect(() => { if (asking) input.current?.focus(); }, [asking]);
  useLayoutEffect(() => {          /* under the selection, or above it when the bar and its menu don't fit below; the menus hang off it, so it never scrolls */
    if (!box.current || bar.h.editor.isDestroyed) return undefined;
    const v = bar.h.editor.view;
    return placeAtCaret(v, bar.to, box.current, { from: bar.from, x: () => leftOf(v, bar.from, bar.to), need: 200, scroll: false, gap: 6 });
  }, [bar.h, bar.from, bar.to, asking]);
  useEffect(() => {                                                       // Alt+/ in the editor: the first AI menu opens, focus in it
    if (bar.open) /** @type {HTMLButtonElement | null} */ (box.current?.querySelector(".aiai button[aria-haspopup]") || box.current?.querySelector("button[aria-haspopup]"))?.click();
  }, [bar.open]);
  useEffect(() => {                                                       // a click elsewhere closes the bar and the sparkle
    /** @param {Event} e */
    const away = e => {
      const t = /** @type {Node} */ (e.target), layer = document.getElementById("aiLayer");
      if (layer?.contains(t) || bar.h.el.contains(t)) return;
      aiBar.value = null;
    };
    document.addEventListener("pointerdown", away, true);
    return () => document.removeEventListener("pointerdown", away, true);
  }, [bar.h]);
  const back = () => { setAsking(false); setWords(""); if (!bar.h.editor.isDestroyed) bar.h.focus(); };
  const place = bar.ai.place, row = AI_PLACE_TABLE[place];
  const turnOn = !!row?.turnInto && bar.h.features === "notes";
  const cur = turnOn ? edTurnKind(bar.h) : "";
  /** @param {string} id */
  const pickAi = id => { if (!aiRunAction(id)) aiRun(id, "", { h: bar.h, ai: bar.ai }); };
  /** @type {[string, {id: string, name: string, line?: string, icon?: string}[]][]} */
  const groups = (AI_GROUPS[place] || AI_GROUPS.plain).map(([name, ids]) =>
    [name, ids.map(id => ({ id, name: aiName(place, id), line: AI_OPTIONS[id][1] }))]);
  const into = aiActionsFor(place).map(a => ({ id: a.id, name: a.name, line: a.line, icon: a.icon }));
  if (into.length) groups.push(["Make into", into]);
  /** ← → move along the bar's buttons (a menu's own keys are the menu's). @param {KeyboardEvent} e */
  const move = e => {
    const t = /** @type {HTMLElement} */ (e.target);
    if (t.closest("[role=menu]") || t.closest("input") || !t.closest("button")) return;
    const k = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
    if (!k && e.key !== "Home" && e.key !== "End") return;
    const all = /** @type {HTMLElement[]} */ ([...(box.current?.querySelectorAll("button") || [])].filter(b => !b.closest("[role=menu]")));
    const i = all.indexOf(/** @type {HTMLElement} */ (t.closest("button")));
    const to = e.key === "Home" ? 0 : e.key === "End" ? all.length - 1 : (i + k + all.length) % all.length;
    e.preventDefault(); e.stopPropagation(); all[to]?.focus();
  };
  return (
    <div class="aibar" id="aiBarBox" role="toolbar" aria-label="AI and formatting on the selected text" ref={box}
      onKeyDown={e => {
        if (e.isComposing) return;
        move(e);
        if (e.key === "Escape" && !e.defaultPrevented) { e.preventDefault(); e.stopPropagation(); aiBarClose(); }       /* #119: the bar goes, the selection collapses to its end, focus is in the text */
      }}>
      {asking ? (
        <form class="aiask" onSubmit={e => { e.preventDefault(); if (words.trim()) aiRun("custom", words.trim(), { h: bar.h, ai: bar.ai }); }}>
          <input ref={input} type="text" value={words} maxLength={400} placeholder="Say what you want done with the text"
            aria-label="Say what you want done with the selected text" onInput={e => setWords(/** @type {HTMLInputElement} */ (e.currentTarget).value)}
            onKeyDown={e => {
              if (e.isComposing) return;                                  // an Enter or Esc that ends a composition is the input method's
              if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); back(); }
              else if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) { e.preventDefault(); e.stopPropagation(); if (words.trim()) aiRun("custom", words.trim(), { h: bar.h, ai: bar.ai }); }
            }} />
          <button type="submit" class="btn primary" aria-disabled={words.trim() ? undefined : "true"}>Ask</button>
        </form>
      ) : (
        <>
          {turnOn ? (
            <div class="aizone aifmt" role="group" aria-label="Formatting">
              <Menu label="Turn into" btnCls="btn aibtn" menuLabel="Turn into" tip="Change the type of the selected blocks (no AI)" hover left
                items={TURN.map(([id, name]) => ({ id, name, checked: cur === id, radio: true, data: { turn: id } }))} onPick={aiTurn} />
            </div>
          ) : null}
          <div class="aizone aiai" role="group" aria-label="AI">
            <span class="ailab"><Icon name="spark" /> AI</span>
            {bar.multi && row?.formatNotes ? (
              <button type="button" class="btn aibtn" data-ai="notes" data-tip={AI_OPTIONS.notes[1]} onClick={() => pickAi("notes")}>Format notes</button>
            ) : null}
            {groups.map(([name, items]) => (
              <Menu key={name} label={name} btnCls="btn aibtn" menuLabel={name} tip={`AI: ${name.toLowerCase()}`} hover left
                items={items.map(it => ({ ...it, icon: it.icon || "spark", data: { ai: it.id } }))} onPick={pickAi} />
            ))}
            <button type="button" class="btn aibtn" data-ai="custom" onClick={() => setAsking(true)}>Ask…</button>
          </div>
        </>
      )}
    </div>
  );
}

/** The suggestion, with its check and its four buttons. @param {{s: import("../stores/aiEdit.js").Sug}} props */
export function AiSuggestion({ s }) {
  const card = useRef(/** @type {HTMLDivElement | null} */ (null));
  useEffect(() => {                                                       // focus to the first thing to press, once it's there
    const first = /** @type {HTMLElement | null} */ (card.current?.querySelector("[data-aifirst]"));
    first?.focus();
  }, [s.status]);
  useLayoutEffect(() => {          /* under the selection (above it when there is no room), at its left; again when the card grows (running → ready) */
    if (!card.current || s.h.editor.isDestroyed) return undefined;
    const v = s.h.editor.view;
    return placeAtCaret(v, s.range.to, card.current, { from: s.range.from, x: () => leftOf(v, s.range.from, s.range.to), max: 520, gap: 6, overlap: true });
  }, [s.h, s.range.from, s.range.to, s.status, s.changes]);
  const notes = s.notes || [];
  return (
    <div class="aisug" role="dialog" aria-modal="false" aria-labelledby="aiSugH" ref={card}
      onKeyDown={e => {
        if (e.isComposing) return;
        if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); aiDiscard(); }
        else if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && s.status === "ready") { e.preventDefault(); e.stopPropagation(); aiAccept(); }   // ⌘↵ accepts; the host's own ⌘↵ (save) waits
      }}>
      <div class="aisughd"><Icon name="spark" /><b id="aiSugH">{s.label}</b></div>
      {s.status === "ask" ? (
        <>
          <p>This is confidential. Send the selected text to Claude for a suggestion? You're asked once for it.</p>
          <div class="aiacts"><button type="button" class="btn" onClick={aiDiscard}>Cancel</button>
            <button type="button" class="btn primary" data-aifirst onClick={aiSend}>Send to Claude</button></div>
        </>
      ) : s.status === "running" ? (
        <>
          <p class="aist" role="status"><span class="spin" aria-hidden="true" /> Asking Claude (it sees only this text)…</p>
          <div class="aiacts"><button type="button" class="btn" data-drstop data-aifirst>Stop</button></div>
        </>
      ) : s.status === "failed" ? (
        <>
          <p class="aist" role="alert">{s.message}</p>
          <div class="aiacts"><button type="button" class="btn" onClick={aiDiscard}>Close</button>
            <button type="button" class="btn" data-aifirst onClick={aiRetry}>Try again</button></div>
        </>
      ) : (
        <>
          <p class="sub" role="status">A suggestion: your text is unchanged until you accept it.</p>
          <div class="aitext" tabIndex={0} aria-label={s.changes ? "The changes" : "The suggestion"}>
            {s.changes ? aiDiff(s.range.text, s.text || "").map(([k, t], i) => k === "=" ? <span key={i}>{t}</span>
              : k === "-" ? <del key={i} class="aidel">{t}</del> : <ins key={i} class="aiins">{t}</ins>) : s.text}
          </div>
          {s.option !== "custom" ? <p class="oknote" data-aispell>✓ Spelling and grammar fixed too (British English).</p> : null}
          {notes.length ? <ul class="ainotes" aria-label="Check it">{notes.map(n => <li key={n.id}>{n.note}</li>)}</ul>
            : <p class="oknote">✓ Keeps your dates, numbers, names and item IDs.</p>}
          <div class="aiacts">
            <button type="button" class="btn" aria-pressed={s.changes ? "true" : "false"} onClick={aiChanges}>Show changes</button>
            <button type="button" class="btn" onClick={aiRetry}>Try again</button>
            <span class="sp" />
            <button type="button" class="btn" onClick={aiDiscard}>Discard</button>
            <button type="button" class="btn primary" data-aifirst onClick={aiAccept}>Accept</button>
          </div>
        </>
      )}
    </div>
  );
}

/** The layer: the bar while text is selected, else the suggestion when there is one. */
export function AiLayer() {
  const s = aiSug.value, b = aiBar.value;
  return s ? <AiSuggestion s={s} /> : b ? <><AiSpark bar={b} />{b.shown ? <AiBar bar={b} key={b.h.el.id || "bar"} /> : null}</> : null;
}

/** AI ▾ as a plain menu button for a place's own row of buttons (Current state's, beside Save), acting on the whole text of the
    editor the cursor was last in. `onExecutive` (Current state: BL-106's Make it executive, with its facts and evidence) takes
    that option over. @param {{place: string, target: () => ({h: import("../core/editor.js").EdHandle, ai: import("../core/editor.js").EdAi} | null),
    onExecutive?: () => void}} props */
export function AiMenu({ place, target, onExecutive }) {
  return (
    <Menu label="AI" icon="spark" menuLabel="AI on the whole text" tip="AI on the whole text, or select some text for AI on just that"
      items={aiItems(place).filter(it => it.id !== "custom" && AI_OPTIONS[it.id]).map(it => ({ ...it, icon: "spark", data: it.id === "executive" && onExecutive ? { exec: "1" } : { ai: it.id } }))}
      onPick={id => {
        if (id === "executive" && onExecutive) { onExecutive(); return; }
        const t = target();
        if (!t || t.h.editor.isDestroyed) return;
        t.h.editor.commands.selectAll();                                 // the whole text, as ⌘A then the bar
        aiRun(id, "", t);
      }} />
  );
}

/** Put AiMenu into `el` (Current state's action row is drawn as HTML). @param {Element} el @param {Parameters<typeof AiMenu>[0]} props */
export function mountAiMenu(el, props) { render(<AiMenu {...props} />, el); }

/** At start-up: the layer on the body, and the editors' `ai` option wired to it. */
export function bootAiSelect() {
  ED_HOOKS.ai = aiAttach;
  if (document.getElementById("aiLayer")) return;
  const box = document.createElement("div");
  box.id = "aiLayer";
  document.body.appendChild(box);
  render(<AiLayer />, box);
}
