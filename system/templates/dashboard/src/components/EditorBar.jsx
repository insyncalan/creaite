// @ts-check
/* EditorBar (#122 step A): the one formatting toolbar every rich editor shows, drawn from core/editorProfiles.js. A host names
   its profile ("notes", "current"; "plain" and "none" draw nothing) and gives the editor it acts on; the same buttons then show
   and do the same in Notes, the capture drawer and Current state. The few things a host does itself (its [[ @ # pickers, the
   table, the file input for a picture) are `host` callbacks: a button shows only if the host can do it.

   Keys, as Tabs and Menu: the bar is one stop in the Tab order (a roving tabindex); ← → Home End move between the buttons, Enter
   or Space runs one, Esc gives focus back to the editor. Pressing a button with the mouse keeps the cursor in the text. A button that
   does not apply here (Unlink away from a link, Indent outside a list) is aria-disabled; one in force at the cursor is
   aria-pressed.

   The link form (address, Add, Cancel; https, http and mailto only, as Current state's always was) opens from the Link button or
   ⌘⇧K inside a rich editor. ⌘K is the command palette everywhere, Shift or not outside an editor (Alan, 15-10-2026). ⌘⇧X is
   strikethrough. The richer link control is #120. Nothing here dispatches on mount, so opening an editor is never an edit. */
import { render } from "preact";
import { useEffect, useRef, useState } from "preact/hooks";
import { profileTools, runTool, ED_TOOLS } from "../core/editorProfiles.js";
import { snack } from "../core/server.js";

/** @typedef {{profile: string, handle: () => (import("../core/editor.js").EdHandle|null|undefined), host?: Record<string, () => void>,
    cls?: string, label?: string, legacyRc?: boolean, extra?: import("preact").ComponentChildren}} BarProps */

/** The bars on the page, so one key handler can find the one a key belongs to. @type {Set<{handle: BarProps["handle"], link: () => void}>} */
const BARS = new Set();
/** The bar whose editor holds the focused element, if any. @param {EventTarget|null} t */
function editorBarFor(t) {
  const el = /** @type {Element|null} */ (t && /** @type {Element} */ (t).closest ? t : null);
  if (!el) return null;
  for (const b of BARS) { const h = b.handle(); if (h && h.el && (h.el === el || h.el.contains(el) || el.closest(".ProseMirror") === h.editor.view.dom)) return b; }
  return null;
}
let keysOn = false;
/** ⌘⇧K opens the link form and ⌘⇧X strikes, in an editor that has a bar. At capture, so the palette (core/keys.js) never sees ⌘⇧K there. */
function keysInit() {
  if (keysOn) return;
  keysOn = true;
  document.addEventListener("keydown", e => {
    if (e.isComposing || !(e.metaKey || e.ctrlKey) || !e.shiftKey || e.altKey) return;      // not while an input method is composing
    const k = e.key.toLowerCase();
    if (k !== "k" && k !== "x") return;
    const b = editorBarFor(e.target);
    if (!b) return;
    e.preventDefault(); e.stopPropagation();
    if (k === "k") b.link();
    else { const h = b.handle(); if (h) runTool(h, "s"); }
  }, true);
}

/** https, http and mailto only. @param {string} u */
const okUrl = u => /^(https?:\/\/|mailto:)\S+$/i.test(u);

/** @param {BarProps} props */
export function EditorBar({ profile, handle, host, cls, label, legacyRc, extra }) {
  const bar = useRef(/** @type {HTMLDivElement|null} */ (null));
  const form = useRef(/** @type {HTMLSpanElement|null} */ (null));
  const [link, setLink] = useState(/** @type {{from: number, to: number, url: string}|null} */ (null));
  const [cur, setCur] = useState(0);
  const tools = profileTools(profile, Object.keys(host || {}));
  const buttons = /** @type {import("../core/editorProfiles.js").ToolDef[]} */ (tools.filter(t => t !== "|"));

  /** What is in force at the cursor, on the buttons. */
  const refresh = () => {
    const root = bar.current, h = handle();
    if (!root || !h || h.editor.isDestroyed) return;
    for (const b of /** @type {NodeListOf<HTMLElement>} */ (root.querySelectorAll("button[data-nt]"))) {
      const t = ED_TOOLS[b.dataset.nt || ""];
      if (!t) continue;
      if (t.on) b.setAttribute("aria-pressed", t.on(h.editor) ? "true" : "false");
      if (t.can) { if (t.can(h.editor)) b.removeAttribute("aria-disabled"); else b.setAttribute("aria-disabled", "true"); }
    }
  };
  const openLink = () => {
    const h = handle();
    if (!h) return;
    const s = h.editor.state.selection;
    setLink({ from: s.from, to: s.to, url: h.editor.getAttributes("link").href || "" });
  };
  useEffect(() => {
    const me = { handle, link: openLink };
    BARS.add(me); keysInit();
    document.addEventListener("selectionchange", refresh);
    document.addEventListener("focusin", refresh);
    refresh();
    return () => { BARS.delete(me); document.removeEventListener("selectionchange", refresh); document.removeEventListener("focusin", refresh); };
  }, [profile]);
  useEffect(() => { if (link && form.current) { const i = form.current.querySelector("input"); if (i) { i.focus(); i.select(); } } }, [link !== null]);

  /** @param {string} id */
  const run = id => {
    const h = handle(), t = ED_TOOLS[id];
    if (!h || !t) return;
    if (id === "link") { openLink(); return; }
    if (t.host) { const f = host && host[id]; if (f) f(); return; }
    runTool(h, id);
    refresh();
  };
  /** @param {boolean} add */
  const finish = add => {
    const h = handle(), l = link;
    setLink(null);
    if (!h || !l) return;
    const c = h.editor.chain().focus().setTextSelection({ from: l.from, to: l.to }), url = (form.current?.querySelector("input")?.value || "").trim();
    if (add && okUrl(url)) {
      if (l.from === l.to && !h.editor.isActive("link")) c.insertContent({ type: "text", text: url, marks: [{ type: "link", attrs: { href: url } }] }).run();
      else c.extendMarkRange("link").setLink({ href: url }).run();
    } else { c.run(); if (add && url) snack("Use a web (https) or mail (mailto) link"); }
  };
  /** @param {KeyboardEvent} e */
  const keys = e => {
    const t = /** @type {Element} */ (e.target);
    if (t.closest && t.closest(".rtelink")) {
      if (e.key === "Enter" && t.tagName === "INPUT") { e.preventDefault(); finish(true); }
      else if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); finish(false); }
      return;
    }
    const b = /** @type {HTMLElement|null} */ (t.closest ? t.closest("button[data-nt]") : null);
    if (!b) return;
    const i = buttons.findIndex(x => x.id === b.dataset.nt);
    let to = -1;
    if (e.key === "ArrowRight") to = (i + 1) % buttons.length;
    else if (e.key === "ArrowLeft") to = (i + buttons.length - 1) % buttons.length;
    else if (e.key === "Home") to = 0;
    else if (e.key === "End") to = buttons.length - 1;
    else if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); const h = handle(); if (h) h.focus(); return; }
    if (to < 0) return;
    e.preventDefault(); e.stopPropagation();
    setCur(to);
    requestAnimationFrame(() => { const n = bar.current && bar.current.querySelector(`button[data-nt="${buttons[to].id}"]`); if (n) /** @type {HTMLElement} */ (n).focus(); });
  };
  if (!buttons.length) return null;
  /* the tools in their groups (between the dividers): a group wraps as one, so a divider never ends a line */
  const groups = tools.reduce((out, t) => { if (t === "|") out.push([]); else out[out.length - 1].push(t); return out; }, /** @type {any[][]} */ ([[]])).filter(g => g.length);
  return (
    <div ref={bar} class={`rtebar ${cls || ""}`.trim()} role="toolbar" aria-label={label || "Formatting"} data-profile={profile} onKeyDown={keys}
      onMouseDown={e => {          /* keep the cursor in the text; the press itself runs the tool (a click with no mouse, from a key, runs it below) */
        const b = /** @type {HTMLElement|null} */ ((/** @type {Element} */ (e.target)).closest("button[data-nt]"));
        if (!b) return;
        e.preventDefault();
        if (e.button === 0) setCur(Math.max(0, buttons.findIndex(x => x.id === b.dataset.nt)));      // the one Tab stop follows the mouse
        if (e.button === 0 && b.getAttribute("aria-disabled") !== "true") run(b.dataset.nt || "");
      }}
      onClick={e => {
        const b = /** @type {HTMLElement|null} */ ((/** @type {Element} */ (e.target)).closest("button[data-nt]"));
        if (b && e.detail === 0 && b.getAttribute("aria-disabled") !== "true") run(b.dataset.nt || "");
      }}>
      {groups.map((g, gi) => <span key={`g${gi}`} class="rtegrp">
        {gi > 0 && <span class="rtesep" aria-hidden="true" />}
        {g.map(t => <button key={t.id} type="button" data-nt={t.id} {...(legacyRc && t.rc ? { "data-rc": t.rc } : {})} aria-label={t.tip || t.name} data-tip={t.tip || t.name} {...(t.keys ? { "aria-keyshortcuts": t.keys } : {})}
          tabIndex={buttons[cur] && buttons[cur].id === t.id ? 0 : -1} {...(t.on ? { "aria-pressed": "false" } : {})}>{t.label}</button>)}
      </span>)}
      <span class="rtelink" ref={form} hidden={!link}>
        <input type="url" placeholder="Paste a web or mail link" aria-label="Link address" value={link ? link.url : ""} onInput={e => link && setLink({ ...link, url: /** @type {HTMLInputElement} */ (e.currentTarget).value })} />
        <button type="button" data-rl="add" onClick={() => finish(true)}>Add</button>
        <button type="button" data-rl="cancel" onClick={() => finish(false)}>Cancel</button>
      </span>
      {extra}
    </div>
  );
}

/** Draw a bar into `el` (for a host that is not a component: Current state's card). @param {HTMLElement} el @param {BarProps} props */
export function mountEditorBar(el, props) { render(<EditorBar {...props} />, el); }
/** Take a bar out of `el`. @param {HTMLElement} el */
export function unmountEditorBar(el) { render(null, el); }
