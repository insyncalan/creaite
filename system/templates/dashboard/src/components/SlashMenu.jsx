// @ts-check
/* SlashMenu (#122 step B): the one `/` menu every rich editor offers, drawn from core/editorProfiles.js (ED_SLASH, ED_SLASH_ROWS).
   `attachSlash(handle, {profile, host})` wires it to an editor and returns what undoes it; Notes and Current state call it, so the
   same rows do the same wherever the profile is used. The rows a host does itself (its [[ @ # pickers, the table, the templates, the
   file input for a picture) are `host` callbacks: a row shows only if the host can do it.

   Opens at the caret when a `/` is TYPED (not on a caret move, a paste or a saved note) at the start of a line or after a space, in a paragraph (never in a code block or code,
   a link, a heading, or inside a word or an address such as and/or or https://x). It is drawn position:fixed from the editor's own
   coordsAtPos (core/caretPlace.js): below the caret, above when there is no room, clamped to the window, moved again on scroll and
   resize. Typing narrows it (name and description); ↑ ↓ move, Enter or Tab insert a sure match (an exact id or alias, or a name prefix at the start of a line or of three letters, or any row after an arrow key; otherwise they close the menu and act as ever), Esc closes and leaves the text; a click on a row
   inserts. The "/query" is removed and the row's block written in its place. A composition (IME) never opens it or is read by it.
   Focus stays in the text; the editor carries aria-activedescendant for the screen reader, and the list is a listbox of groups
   of options. Nothing is written until a row is chosen. */
import { render } from "preact";
import { useEffect, useLayoutEffect, useRef, useState } from "preact/hooks";
import { slashRows, slashRank } from "../core/editorProfiles.js";
import { placeAtCaret } from "../core/caretPlace.js";

/** @typedef {import("../core/editorProfiles.js").SlashDef} SlashDef */
/** @typedef {{from: number, to: number, q: string, rows: SlashDef[], i: number}} SlashState */

let slashSeq = 0;
/** The name of the list the caret is in, the NEAREST one (a bullet list nested in a numbered one is a bullet list), else "". @param {any} editor */
export function nearestList(editor) {
  const $f = editor.state.selection.$from;
  for (let d = $f.depth; d > 0; d--) { const n = $f.node(d).type.name; if (n === "bulletList" || n === "orderedList" || n === "taskList") return n; }
  return "";
}
/** The text before the caret in a paragraph where a `/` menu may open, else null: the "/query" and where it starts. @param {any} editor */
export function slashAt(editor) {
  const s = editor.state.selection;
  if (!s.empty) return null;
  const $f = s.$from;
  if ($f.parent.type.name !== "paragraph") return null;
  if ($f.marks().some(/** @param {any} m */ m => m.type.name === "code" || m.type.name === "link")) return null;
  const before = $f.parent.textBetween(0, $f.parentOffset, undefined, "￼"), m = /(^|\s)\/((?:[\w-]{1,20}(?: [\w-]{0,20})?)?)$/.exec(before);   /* one space is allowed, but only after a query character: "/heading 2", "/bulleted list"; "A / B" and "1 / 2" are prose */
  if (!m) return null;
  return { from: s.from - m[2].length - 1, to: s.from, q: m[2] };
}

/** @param {{state: SlashState, id: string, view: any, pick: (r: SlashDef) => void, hover: (i: number) => void}} p */
function SlashList({ state, id, view, pick, hover }) {
  const box = useRef(/** @type {HTMLDivElement|null} */ (null));
  useLayoutEffect(() => {          /* at the caret again after every redraw (the list got shorter or longer) */
    const el = box.current;
    if (!el) return undefined;
    return placeAtCaret(view, state.from, el);
  }, [state.rows.length, state.from, state.q]);
  const none = !state.rows.length;
  const say = none ? "No match" : `${state.rows.length} ${state.rows.length === 1 ? "option" : "options"}`;
  const [spoken, setSpoken] = useState("");          /* the live region goes in empty and is filled a frame later, so a screen reader reads the first text */
  useEffect(() => { const t = requestAnimationFrame(() => setSpoken(say)); return () => cancelAnimationFrame(t); }, [say]);
  const flat = !!state.q.trim();                       /* ranked by a query: no group headers (ranking splits a group into repeated ones); they come back when the query is empty */
  useEffect(() => { const on = box.current && box.current.querySelector(".r.on"); if (on && on.scrollIntoView) on.scrollIntoView({ block: "nearest" }); }, [state.i]);
  /** @type {{g: string, rows: {r: SlashDef, i: number}[]}[]} */
  const groups = [];
  state.rows.forEach((r, i) => { let g = groups[groups.length - 1]; if (!g || g.g !== r.group) { g = { g: r.group, rows: [] }; groups.push(g); } g.rows.push({ r, i }); });
  return (
    <>
    <div ref={box} class="slashmenu" id={id} role="listbox" aria-label="Insert" onMouseDown={e => e.preventDefault()}>
      {state.rows.length && flat ? state.rows.map((r, i) => (
        <div key={r.id} id={`${id}-${i}`} role="option" data-slash={r.id} aria-selected={i === state.i ? "true" : "false"} class={`r${i === state.i ? " on" : ""}`}
          onMouseMove={() => { if (i !== state.i) hover(i); }} onClick={() => pick(r)}>
          <span class="ic" aria-hidden="true">{r.icon}</span>
          <span class="tx"><span class="t">{r.name}</span><span class="d">{r.desc}</span></span>
          {r.key ? <span class="k" aria-hidden="true">{r.key}</span> : null}
        </div>)) : state.rows.length ? groups.map((g, gi) => (
        <div key={`${gi}-${g.g}`} role="group" aria-label={g.g}>
          <div class="g" aria-hidden="true">{g.g}</div>
          {g.rows.map(({ r, i }) => (
            <div key={r.id} id={`${id}-${i}`} role="option" data-slash={r.id} aria-selected={i === state.i ? "true" : "false"} class={`r${i === state.i ? " on" : ""}`}
              onMouseMove={() => { if (i !== state.i) hover(i); }} onClick={() => pick(r)}>
              <span class="ic" aria-hidden="true">{r.icon}</span>
              <span class="tx"><span class="t">{r.name}</span><span class="d">{r.desc}</span></span>
              {r.key ? <span class="k" aria-hidden="true">{r.key}</span> : null}
            </div>))}
        </div>)) : <div class="r none" role="option" aria-disabled="true" aria-selected="false">No match</div>}
      <div class="foot" aria-hidden="true">↑↓ to move · Enter to insert · Esc to close</div>
    </div>
    <div class="slashsr" role="status" aria-live="polite" aria-atomic="true">{spoken}</div>
    </>
  );
}

/** Give an editor its `/` menu. `host` maps a row id to what the host does for it. Returns what takes it away again.
    @param {import("../core/editor.js").EdHandle} h @param {{profile: string, host?: Record<string, () => void>}} o */
export function attachSlash(h, { profile, host }) {
  const id = `slash-${++slashSeq}`, editor = h.editor, view = editor.view, el = h.el;
  const hostRows = Object.keys(host || {});
  if (!slashRows(profile, hostRows, editor.schema).length) return () => {};
  const root = document.createElement("div");
  root.className = "slashroot";
  (el.closest("dialog[open]") || document.body).appendChild(root);
  /** @type {SlashState|null} */
  let st = null;
  let dismissed = -1, typedSlash = false, moved = false;          /* typedSlash: a "/" was just typed (the only thing that opens the menu); moved: an arrow key was pressed in this menu */
  const draw = () => {
    render(st ? <SlashList state={st} id={id} view={view} pick={choose} hover={i => { if (st) { st = { ...st, i }; draw(); } }} /> : null, root);
    const dom = /** @type {HTMLElement} */ (view.dom);
    if (st) { dom.setAttribute("aria-haspopup", "listbox"); dom.setAttribute("aria-controls", id);
      if (st.rows[st.i]) dom.setAttribute("aria-activedescendant", `${id}-${st.i}`); else dom.removeAttribute("aria-activedescendant"); }
    else { dom.removeAttribute("aria-haspopup"); dom.removeAttribute("aria-controls"); dom.removeAttribute("aria-activedescendant"); }
  };
  const close = () => { if (!st) return; st = null; draw(); };
  /** Open, narrow or close the menu from what is at the caret. */
  const look = () => {
    const mayOpen = typedSlash; typedSlash = false;
    if (editor.isDestroyed || view.composing) return;
    const a = slashAt(editor);
    if (!a || a.from === dismissed) { if (!a) dismissed = -1; return close(); }
    if (!st && !mayOpen) return;          /* a caret move, a paste or a saved note never opens it (#122 B review H1, M1); only a typed "/" does */
    if (st && st.from !== a.from && !mayOpen) return close();
    if (a.q.endsWith(" ")) {          /* a trailing space closes the menu unless it can only be the first word of a longer row name ("heading ", "bulleted ") */
      const base = a.q.trim().toLowerCase();
      if (!slashRows(profile, hostRows, editor.schema).some(r => r.name.toLowerCase().startsWith(base + " "))) return close();
    }
    const rows = slashRows(profile, hostRows, editor.schema, a.q);
    if (!rows.length && (!a.q || a.q.includes(" "))) return close();         /* a phrase that names no row is just text: no "No match" nag */
    const fresh = !st || st.from !== a.from;
    st = { ...a, rows, i: st && st.from === a.from ? Math.min(st.i, Math.max(0, rows.length - 1)) : 0 };
    if (fresh) moved = false;
    draw();
  };
  /** @param {SlashDef} r */
  const choose = r => {
    const s = st;
    if (!s) return;
    close();
    const c = editor.chain().focus().deleteRange({ from: s.from, to: s.to });
    if (r.host) { c.run(); const f = host && host[r.id]; if (f) f(); return; }
    if (r.is && (r.is === "blockquote" ? editor.isActive(r.is) : nearestList(editor) === r.is)) { c.run(); return; }          /* already in that block: only the "/query" goes (a toggle would take the line OUT of the list or quote) */
    if (r.run) r.run(c, editor).run();
  };
  /** @param {KeyboardEvent} e */
  const keys = e => {
    if (!st || e.isComposing || view.composing) return;
    const n = st.rows.length;
    if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); e.stopPropagation(); if (n) { moved = true; st = { ...st, i: (st.i + (e.key === "ArrowDown" ? 1 : n - 1)) % n }; draw(); } }
    else if ((e.key === "Enter" || e.key === "Tab") && !e.shiftKey && !e.metaKey && !e.ctrlKey) {
      const row = n ? st.rows[st.i] : null;          /* Enter or Tab picks a row only when it is a sure match (an exact id or alias; a name prefix too at the start of a line or of three letters) or the user moved with the arrows; else the menu closes and the key is an ordinary Enter or Tab, so prose like "Amber /Red" keeps its text */
      const rank = row ? slashRank(row, st.q) : 9, lead = editor.state.doc.resolve(st.from).parentOffset === 0;          /* a name prefix is sure at the start of a line, or after text once it is three letters: "yes /no" and "w /o" are prose, not Note and Numbered list */
      if (row && (moved || rank === 0 || (rank === 1 && (lead || st.q.trim().length >= 3)))) { e.preventDefault(); e.stopPropagation(); choose(row); } else close(); }
    else if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) { e.preventDefault(); e.stopPropagation(); }      /* ⌘↵ waits: the host's save (the capture drawer's Done) and the editor's own ⌘↵ must not fire under an open menu */
    else if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); dismissed = st.from; close(); }
  };
  const blur = () => setTimeout(() => { if (!el.contains(document.activeElement)) close(); }, 120);
  const comp = () => { typedSlash = true; look(); };          /* a composition ended: read the text it left */
  /** @param {InputEvent} e */
  const before = e => { typedSlash = e.inputType === "insertText" || e.inputType.startsWith("deleteContent"); };          /* beforeinput runs before the transaction: typing or deleting arms it (never a paste, a drop or a caret move) */
  editor.on("selectionUpdate", look); editor.on("update", look);
  el.addEventListener("beforeinput", before, true);
  el.addEventListener("keydown", keys, true); el.addEventListener("focusout", blur); el.addEventListener("compositionend", comp);
  const off = () => {
    editor.off("destroy", off);
    editor.off("selectionUpdate", look); editor.off("update", look); el.removeEventListener("beforeinput", before, true);
    el.removeEventListener("keydown", keys, true); el.removeEventListener("focusout", blur); el.removeEventListener("compositionend", comp);
    st = null; render(null, root); root.remove();
    if (!editor.isDestroyed) for (const a of ["aria-expanded", "aria-controls", "aria-activedescendant", "aria-haspopup"]) view.dom.removeAttribute(a);
  };
  editor.on("destroy", off);          /* a host that destroys the editor needs no extra step */
  return off;
}
