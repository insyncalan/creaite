// @ts-check
/* EditorBar (#122 step A): the one formatting toolbar every rich editor shows, drawn from core/editorProfiles.js. A host names
   its profile ("notes", "current"; "plain" and "none" draw nothing) and gives the editor it acts on; the same buttons then show
   and do the same in Notes, the capture drawer and Current state. The few things a host does itself (its [[ @ # pickers, the
   table, the file input for a picture) are `host` callbacks: a button shows only if the host can do it.

   Keys, as Tabs and Menu: the bar is one stop in the Tab order (a roving tabindex); ← → Home End move between the buttons, Enter
   or Space runs one, Esc gives focus back to the editor. Pressing a button with the mouse keeps the cursor in the text. A button that
   does not apply here (Unlink away from a link, Indent outside a list) is aria-disabled; one in force at the cursor is
   aria-pressed.

   The link popover (components/LinkPopover.jsx, #120) opens from the Link button; ⌘⇧K inside a rich editor is the editor's own
   (LinkPopover's attachLink). ⌘K is the command palette everywhere, Shift or not outside an editor (Alan, 15-10-2026). ⌘⇧X is
   strikethrough. Nothing here dispatches on mount, so opening an editor is never an edit.

   #122, Alan's final layout (16-10-2026): the Notes bar is ONE line. Related tools sit in hover menus (Heading, List, Insert: a profile
   entry "m:<key>", core/editorProfiles.js ED_MENUS), drawn with the shared Menu (`hover`): the pointer opens one, it folds about 220 ms
   after the pointer leaves, a click, Enter, Space or ↓ opens it with focus inside, ↑ ↓ move, Esc closes and gives focus back. The menu
   buttons are in the one Tab stop with the other buttons (← → between them); each carries aria-haspopup="menu" and aria-expanded. Items
   that show a state are menuitemradio (ticked when in force). Unlink is not a button there: the link popover has a Remove link button when
   the cursor is in a link. A menu item carries data-cmd=<tool id>, a bar control data-nt. */
import { render } from "preact";
import { useEffect, useRef, useState } from "preact/hooks";
import { profileTools, runTool, ED_TOOLS } from "../core/editorProfiles.js";
import { Menu } from "./Menu.jsx";
import { openLinkForm } from "./LinkPopover.jsx";

/** @typedef {{profile: string, handle: () => (import("../core/editor.js").EdHandle|null|undefined), host?: Record<string, () => void>,
    cls?: string, label?: string, legacyRc?: boolean, extra?: import("preact").ComponentChildren}} BarProps */

/** The bars on the page, so one key handler can find the one a key belongs to. @type {Set<{handle: BarProps["handle"]}>} */
const BARS = new Set();
/** The bar whose editor holds the focused element, if any. @param {EventTarget|null} t */
function editorBarFor(t) {
  const el = /** @type {Element|null} */ (t && /** @type {Element} */ (t).closest ? t : null);
  if (!el) return null;
  for (const b of BARS) { const h = b.handle(); if (h && h.el && (h.el === el || h.el.contains(el) || el.closest(".ProseMirror") === h.editor.view.dom)) return b; }
  return null;
}
let keysOn = false;
/** ⌘⇧X strikes, in an editor that has a bar. (⌘⇧K, the link form, is the editor's own: LinkPopover's attachLink catches it before the palette.) */
function keysInit() {
  if (keysOn) return;
  keysOn = true;
  document.addEventListener("keydown", e => {
    if (e.isComposing || !(e.metaKey || e.ctrlKey) || !e.shiftKey || e.altKey) return;      // not while an input method is composing
    const k = e.key.toLowerCase();
    if (k !== "x") return;
    const b = editorBarFor(e.target);
    if (!b) return;
    e.preventDefault(); e.stopPropagation();
    const h = b.handle(); if (h) runTool(h, "s");
  }, true);
}

/** @param {BarProps} props */
export function EditorBar({ profile, handle, host, cls, label, legacyRc, extra }) {
  const bar = useRef(/** @type {HTMLDivElement|null} */ (null));
  const [cur, setCur] = useState(0);
  const [, tick] = useState(0);
  const tools = profileTools(profile, Object.keys(host || {}));
  const buttons = /** @type {import("../core/editorProfiles.js").ToolDef[]} */ (tools.filter(t => t !== "|"));

  /** What is in force at the cursor, on the buttons. */
  const refresh = () => {
    const root = bar.current, h = handle();
    if (!root || !h || h.editor.isDestroyed) return;
    tick(n => n + 1);                           // the menus' ticks and greyed items are drawn from the editor's state
    for (const b of /** @type {NodeListOf<HTMLElement>} */ (root.querySelectorAll("button[data-nt]"))) {
      const t = ED_TOOLS[b.dataset.nt || ""];
      if (!t) continue;
      if (t.on) b.setAttribute("aria-pressed", t.on(h.editor) ? "true" : "false");
      if (t.can) { if (t.can(h.editor)) b.removeAttribute("aria-disabled"); else b.setAttribute("aria-disabled", "true"); }
    }
  };
  useEffect(() => {
    const me = { handle };
    BARS.add(me); keysInit();
    document.addEventListener("selectionchange", refresh);
    document.addEventListener("focusin", refresh);
    refresh();
    return () => { BARS.delete(me); document.removeEventListener("selectionchange", refresh); document.removeEventListener("focusin", refresh); };
  }, [profile]);

  /** @param {string} id */
  const run = id => {
    const h = handle(), t = ED_TOOLS[id];
    if (!h || !t) return;
    if (id === "link") { openLinkForm(h); return; }
    if (t.host) { const f = host && host[id]; if (f) f(); return; }
    runTool(h, id);
    refresh();
  };
  /** @param {KeyboardEvent} e */
  const keys = e => {
    const t = /** @type {Element} */ (e.target);
    const b = /** @type {HTMLElement|null} */ (t.closest ? t.closest("button[data-nt]") : null);
    if (!b) return;
    if (e.key === "ArrowDown") tick(n => n + 1);
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
  /* every control's tab stop: the one the bar's roving index names (a menu's button is drawn by Menu, which takes no tabIndex) */
  useEffect(() => {
    const root = bar.current;
    if (!root) return;
    for (const n of /** @type {NodeListOf<HTMLElement>} */ (root.querySelectorAll("button[data-nt]"))) n.tabIndex = buttons[cur] && buttons[cur].id === n.dataset.nt ? 0 : -1;
  });
  if (!buttons.length) return null;
  /** A menu's items, with what is in force at the cursor ticked and what does not apply greyed. @param {import("../core/editorProfiles.js").ToolDef} m */
  const menuItems = m => {
    const e = handle()?.editor, live = e && !e.isDestroyed;
    return /** @type {any[]} */ ((m.items || [])).map((x, i) => x === "|" ? { id: `sep${i}`, sep: true }
      : { id: x.id, name: x.name, ...(x.hint ? { mark: x.hint } : {}), data: { cmd: x.id },
        ...(x.on ? { radio: true, checked: !!(live && x.on(e)) } : {}), ...(x.can && !(live && x.can(e)) ? { disabled: true } : {}) });
  };
  /* the tools in their groups (between the dividers): a group wraps as one, so a divider never ends a line */
  const groups = tools.reduce((out, t) => { if (t === "|") out.push([]); else out[out.length - 1].push(t); return out; }, /** @type {any[][]} */ ([[]])).filter(g => g.length);
  return (
    <div ref={bar} class={`rtebar ${cls || ""}`.trim()} role="toolbar" aria-label={label || "Formatting"} data-profile={profile} onKeyDown={keys}
      onMouseDown={e => {          /* keep the cursor in the text; the press itself runs the tool (a click with no mouse, from a key, runs it below) */
        const el = /** @type {Element} */ (e.target);
        if (el.closest("[role^=menuitem]")) { e.preventDefault(); return; }      // a menu item runs on its click; the cursor stays in the text
        const b = /** @type {HTMLElement|null} */ (el.closest("button[data-nt]"));
        if (!b) return;
        e.preventDefault();
        if (e.button === 0) setCur(Math.max(0, buttons.findIndex(x => x.id === b.dataset.nt)));      // the one Tab stop follows the mouse
        if (e.button === 0 && !b.hasAttribute("aria-haspopup") && b.getAttribute("aria-disabled") !== "true") run(b.dataset.nt || "");
      }}
      onMouseOver={e => { if ((/** @type {Element} */ (e.target)).closest(".rtemenu")) tick(n => n + 1); }}
      onClick={e => {
        const b = /** @type {HTMLElement|null} */ ((/** @type {Element} */ (e.target)).closest("button[data-nt]"));
        if (b && e.detail === 0 && !b.hasAttribute("aria-haspopup") && b.getAttribute("aria-disabled") !== "true") run(b.dataset.nt || "");
      }}>
      {groups.map((g, gi) => <span key={`g${gi}`} class="rtegrp">
        {gi > 0 && <span class="rtesep" aria-hidden="true" />}
        {g.map(t => t.menu ? <Menu key={t.id} hover left cls="rtemenu" btnCls="rtemb" label={t.label} ariaLabel={t.name} menuLabel={t.name} menuCls="rtepop"
          data={{ nt: t.id }} items={menuItems(t)} onPick={id => run(id)} /> : <button key={t.id} type="button" data-nt={t.id} {...(legacyRc && t.rc ? { "data-rc": t.rc } : {})} aria-label={t.tip || t.name} data-tip={t.tip || t.name} {...(t.keys ? { "aria-keyshortcuts": t.keys } : {})}
          tabIndex={buttons[cur] && buttons[cur].id === t.id ? 0 : -1} {...(t.on ? { "aria-pressed": "false" } : {})}>{t.label}</button>)}
      </span>)}
      {extra}
    </div>
  );
}

/** Draw a bar into `el` (for a host that is not a component: Current state's card). @param {HTMLElement} el @param {BarProps} props */
export function mountEditorBar(el, props) { render(<EditorBar {...props} />, el); }
/** Take a bar out of `el`. @param {HTMLElement} el */
export function unmountEditorBar(el) { render(null, el); }
