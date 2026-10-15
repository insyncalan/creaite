// @ts-check
/* AiSelect (BL-301 D, v20-ai-select): AI on selected text, in every editor. Two pieces, drawn in one layer (#aiLayer, on the body,
   fixed, so they sit over whatever page the editor is on):
   - the bar over a selection: **AI ▾** (the Menu block) with the place's options and, last, "Or say what you want…", which turns
     the bar into a box for an instruction (Enter asks, Esc goes back);
   - the suggestion: the option's name, the suggested text (or, with Show changes, what it takes out and puts in, word by word),
     the plain-code check's notes, and Accept, Discard, Try again and Show changes. Nothing changes until Accept. A confidential
     text asks first, once.
   Keyboard: select text (⌘A for all of it) and press Alt+/ to open the menu; in the suggestion, Esc discards and focus goes back
   to the text. Text only through JSX. The store is stores/aiEdit.js. */
import { render } from "preact";
import { useEffect, useRef, useState } from "preact/hooks";
import { Icon } from "./Icon.jsx";
import { Menu } from "./Menu.jsx";
import { ED_HOOKS } from "../core/editor.js";
import { AI_OPTIONS, aiAccept, aiAttach, aiBar, aiBarClose, aiChanges, aiDiff, aiDiscard, aiItems, aiRetry, aiRun, aiRunAction, aiSend, aiSug } from "../stores/aiEdit.js";

/** The bar over a selection. @param {{bar: import("../stores/aiEdit.js").Bar}} props */
export function AiBar({ bar }) {
  const [asking, setAsking] = useState(false);
  const [words, setWords] = useState("");
  const box = useRef(/** @type {HTMLDivElement | null} */ (null));
  const input = useRef(/** @type {HTMLInputElement | null} */ (null));
  useEffect(() => { if (asking) input.current?.focus(); }, [asking]);
  useEffect(() => {                                                       // Alt+/ in the editor: the menu opens, focus in it
    if (bar.open) /** @type {HTMLButtonElement | null} */ (box.current?.querySelector("button[aria-haspopup]"))?.click();
  }, [bar.open]);
  const back = () => { setAsking(false); setWords(""); if (!bar.h.editor.isDestroyed) bar.h.focus(); };
  return (
    <div class="aibar" role="toolbar" aria-label="AI on the selected text" ref={box} style={{ top: `${bar.top}px`, left: `${bar.left}px` }}
      onKeyDown={e => { if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); aiBarClose(); } }}>
      {asking ? (
        <form class="aiask" onSubmit={e => { e.preventDefault(); if (words.trim()) aiRun("custom", words.trim(), { h: bar.h, ai: bar.ai }); }}>
          <input ref={input} type="text" value={words} maxLength={400} placeholder="Say what you want done with the text"
            aria-label="Say what you want done with the selected text" onInput={e => setWords(/** @type {HTMLInputElement} */ (e.currentTarget).value)}
            onKeyDown={e => { if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); back(); } }} />
          <button type="submit" class="btn primary" aria-disabled={words.trim() ? undefined : "true"}>Ask</button>
        </form>
      ) : (
        <Menu label="AI" icon="spark" btnCls="btn aibtn" menuLabel="AI on the selected text" tip="AI on the selected text (Alt+/)"
          items={aiItems(bar.ai.place).map(it => ({ ...it, icon: it.icon || (it.id === "custom" ? "msg" : "spark"), data: { ai: it.id } }))}
          onPick={id => { if (id === "custom") setAsking(true); else if (!aiRunAction(id)) aiRun(id, "", { h: bar.h, ai: bar.ai }); }} left />
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
  const notes = s.notes || [];
  return (
    <div class="aisug" role="dialog" aria-modal="false" aria-labelledby="aiSugH" ref={card} style={{ top: `${s.top}px`, left: `${s.left}px` }}
      onKeyDown={e => { if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); aiDiscard(); } }}>
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
  return s ? <AiSuggestion s={s} /> : b ? <AiBar bar={b} key={b.h.el.id || "bar"} /> : null;
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
