// @ts-check
/* NoteEditor (BL-301 B): an open note's body on the one editor (core/editor.js, `features: "notes"`: headings, lists, checklists,
   tables, links). It is editable as soon as it opens: no Edit, Save or Cancel. The toolbar shows while the cursor is in the note.
   Each change tells the store (stores/notes.js), which keeps a draft and writes the file once per editing session.

   Pickers, typed in the text: `[[` a note, `@` a person from the people register, `#` a work item, `/` on an empty line an insert
   menu. A note link is written `[[Title]]`, a person `@[Name](creaite:person/<name>)`, a work item `[ABC-A-003](creaite:item/ABC-A-003)`:
   plain Markdown, readable in Finder and OneDrive. Item chips show the item's live state; a click opens it (a note link opens that
   note). Decorations draw them; nothing drawn is written. The picker is a listbox the editor drives (focus stays in the text:
   ↑ ↓ move, Enter or Tab picks, Esc closes). */
import { useEffect, useRef, useState } from "preact/hooks";
import { Decoration, DecorationSet, Extension, Plugin, PluginKey, markdownOf } from "tiptap";
import { creaiteEditor } from "../../core/editor.js";
import { A, DEC, R } from "../../core/data.js";
import { D, fd, TODAY } from "../../core/page.js";
import { shared } from "../../core/state.js";
import { noteCur, noteFlash, noteLines, noteMarks } from "../../stores/notes.js";
import { Icon } from "../Icon.jsx";

/** @typedef {{id: string, label: string, sub?: string, icon?: string}} PickOption */
/** @typedef {{kind: "note"|"person"|"item"|"insert", from: number, to: number, q: string, opts: PickOption[], i: number,
    x: number, y: number}} PickState */
/** @typedef {{markdown: string, code: string, label: string, loadKey: string, noteTitles: () => string[],
    onInput: () => void, onBody: (get: (() => string|null) | null) => void, onOpenNote: (title: string) => void,
    onOpenItem: (id: string) => void, restored?: boolean, toolbarExtra?: import("preact").ComponentChildren,
    path?: string, onHoverLine?: (line: number) => void,
    imageSrc?: (ref: string) => (string|null), onImage?: (file: File) => Promise<string|null>, readOnly?: boolean}} Props */

const ITEM_HREF = /^creaite:item\/(.+)$/, PERSON_HREF = /^creaite:person\//;
const WIKI = /\[\[([^[\]\n|]{1,160})(?:\|[^[\]\n]*)?\]\]/g;

/** The tracker row for an ID and its kind ("actions", "raid", "decisions"), or null. @param {string} id */
export function itemOf(id) {
  const a = A.find(x => x.id === id); if (a) return { k: "actions", x: a };
  const r = R.find(x => x.id === id); if (r) return { k: "raid", x: r };
  const d = DEC.find(x => x.id === id); if (d) return { k: "decisions", x: d };
  return null;
}
/** An item's live state for its chip: the dot's tone ("bad", "warn", "ok", "off") and a few words.
    @param {string} id @returns {{tone: string, words: string, title: string}} */
export function itemState(id) {
  const hit = itemOf(id);
  if (!hit) return { tone: "off", words: "not in the tracker", title: `${id}: not in the tracker` };
  const x = /** @type {any} */ (hit.x), st = String(x.st || ""), open = /^(Open|Delayed|Pending|Proposed)$/i.test(st);
  let tone = open ? "warn" : "ok", words = st;
  if (hit.k === "actions") {
    if (open && x.due && x.due < TODAY) { tone = "bad"; words = `${st}, overdue ${fd(x.due)}`; }
    else if (open && x.due) words = `${st}, due ${fd(x.due)}`;
    if (x.o) words += ` · ${x.o}`;
  } else if (hit.k === "raid") { if (open && x.pr === "Urgent") tone = "bad"; words = `${x.type || "Risk"} · ${st}${x.pr ? ` · ${x.pr}` : ""}`; }
  else words = `Decision · ${st}`;
  return { tone, words, title: `${id} · ${x.t || ""} · ${words}` };
}

/** The project's open work items and the rest, for `#`. @param {string} code @param {string} q @returns {PickOption[]} */
function itemOptions(code, q) {
  const ql = q.toLowerCase(), L = [];
  for (const [rows, icon] of /** @type {[any[], string][]} */ ([[A, "check"], [R, "alert"], [DEC, "flag"]]))
    for (const x of rows) if ((code === "_portfolio" || x.p === code) && (!ql || x.id.toLowerCase().includes(ql) || String(x.t || "").toLowerCase().includes(ql)))
      L.push({ id: x.id, label: x.id, sub: x.t || "", icon, open: /^(Open|Delayed|Pending)$/i.test(x.st || "") });
  return L.sort((a, b) => Number(b.open) - Number(a.open)).slice(0, 8);
}
/** People from the register (never labelled VIP, BL-288), for `@`. @param {string} q @returns {PickOption[]} */
function personOptions(q) {
  const ql = q.toLowerCase(), seen = new Set(), L = [];
  for (const p of /** @type {any[]} */ (shared.REG || [])) {
    if (!p || !p.name || p.hidden || seen.has(p.name)) continue;
    if (ql && !p.name.toLowerCase().includes(ql) && !(p.aliases || []).some(/** @param {string} a */ a => a.toLowerCase().includes(ql))) continue;
    seen.add(p.name); L.push({ id: p.name, label: p.name, sub: [p.role, p.org].filter(Boolean).join(" · "), icon: "people" });
  }
  return L.slice(0, 8);
}
const INSERTS = [["heading", "Sub-heading", "H"], ["checklist", "Checklist", "☑"], ["item", "Work item", "#"], ["person", "Person", "@"],
  ["note", "Link to a note", "[["], ["table", "Table", "▦"], ["tpl:stakeholder", "Template: Stakeholder", "◇"],
  ["tpl:lessons-learned", "Template: Lessons learned", "◇"], ["tpl:working-session", "Template: Working session", "◇"]];

/** The decorations: note links (missing ones marked), item chips with their state, people. Drawn only; never written.
    @param {any} doc @param {() => string[]} titles */
function decorate(doc, titles) {
  const known = new Set(titles().map(t => t.toLowerCase())), out = [];
  doc.descendants((/** @type {any} */ node, /** @type {number} */ pos) => {
    if (!node.isText) return;
    const link = node.marks.find((/** @type {any} */ m) => m.type.name === "link"), href = link ? String(link.attrs.href || "") : "";
    const im = ITEM_HREF.exec(href);
    if (im) { const s = itemState(im[1]); out.push(Decoration.inline(pos, pos + node.nodeSize, { class: `nchip ${s.tone}`, "data-item": im[1], title: `${s.title} (click to open)` })); return; }
    if (PERSON_HREF.test(href)) { out.push(Decoration.inline(pos, pos + node.nodeSize, { class: "nper" })); return; }
    const text = String(node.text || "");
    for (const m of text.matchAll(WIKI)) {
      const t = m[1].trim(), have = known.has(t.toLowerCase()), at = pos + (m.index || 0);
      out.push(Decoration.inline(at, at + m[0].length, { class: have ? "wl" : "wl missing", "data-wl": t,
        title: have ? `Open “${t}”` : `No note called “${t}” yet (click to make it)` }));
    }
  });
  return DecorationSet.create(doc, out);
}

/** Text for matching a block to a line of the Markdown: letters and digits only, a link's address left out. @param {string} t */
const flat = t => String(t || "").replace(/<!--[\s\S]*?-->/g, "").replace(/\[([^\]\n]*)\]\([^)\n]*\)/g, "$1").toLowerCase().replace(/[^\p{L}\p{N}]+/gu, "");
const LISTS = new Set(["bulletList", "orderedList", "taskList"]);
/** BL-301 E: the note's lines (notes.paragraphs) on the document's blocks: [{pos, size, line}]. Each top-level block, and each item
    of a top-level list, takes the first line from where the last one matched that holds its text. @param {any} doc @param {string} md */
function blockLines(doc, md) {
  const lines = noteLines(md).map(flat), out = [];
  let i = 0;
  /** @param {any} node @param {number} pos */
  const take = (node, pos) => {
    const t = flat(node.textContent);
    if (!t) return;
    for (let j = i; j < lines.length; j++) if (lines[j].includes(t) || (t.includes(lines[j]) && lines[j])) { i = j; out.push({ pos, size: node.nodeSize, line: j + 1, key: lines[j] }); return; }
  };
  doc.forEach((/** @type {any} */ node, /** @type {number} */ pos) => {
    if (LISTS.has(node.type.name)) node.forEach((/** @type {any} */ item, /** @type {number} */ off) => take(item, pos + 1 + off));
    else take(node, pos);
  });
  return out;
}
/** BL-301 B, the margin ticks: the lines Find updates already sent (notes.sent_ids, from the server), keyed by their text as
    `flat` reads it, so a line that moves keeps its tick and one edited since loses it. @param {{text: string, ids: string[]}[]} sent */
function sentKeys(sent) {
  /** @type {Map<string, string[]>} */
  const m = new Map();
  for (const x of sent || []) { const k = flat(x.text); if (k) m.set(k, [...(m.get(k) || []), ...(x.ids || [])]); }
  return m;
}
/** The line decorations: `data-p` on every block that is a line, the Find updates marker (`data-fu-mk`), the hovered line
    (`data-fu-hl`), a line opened from a source link (`nflash`) and a line already sent (`data-sent`: its item IDs, drawn as a tick
    in the margin). Drawn only; never written.
    @param {{pos: number, size: number, line: number, key?: string}[]} L @param {Record<number, number>} markers @param {number} hover
    @param {number} flash @param {Map<string, string[]>} [sent] */
function lineDecos(L, markers, hover, flash, sent) {
  return L.map(({ pos, size, line, key }) => {
    /** @type {Record<string, string>} */
    const a = { "data-p": String(line) };
    const ids = sent && key ? sent.get(key) : null;
    if (ids) a["data-sent"] = ids.join(", ") || "sent";
    if (markers[line]) a["data-fu-mk"] = String(markers[line]);
    if (markers[line] && hover === line) a["data-fu-hl"] = "";
    if (flash === line) a.class = "nflash";
    return Decoration.node(pos, pos + size, a);
  });
}

/** The toolbar's commands. @type {[string, string, string][]} */
const TOOLS = [["h", "H", "Sub-heading"], ["b", "B", "Bold (⌘B)"], ["i", "I", "Italic (⌘I)"], ["s", "S", "Strikethrough"], ["code", "</>", "Code"],
  ["|", "", ""], ["ul", "•", "Bulleted list"], ["ol", "1.", "Numbered list"], ["task", "☑", "Checklist"], ["quote", "❝", "Quote"],
  ["|", "", ""], ["note", "[[ ]]", "Link to a note ([[)"], ["person", "@", "Mention a person (@)"], ["item", "#ID", "Link a work item (#)"],
  ["table", "▦", "Table"], ["image", "Image", "Add a picture here (PNG or JPEG, up to 2 MB)"], ["|", "", ""], ["undo", "↶", "Undo (⌘Z)"], ["redo", "↷", "Redo (⌘⇧Z)"]];

/** The note's body on the one editor. @param {Props} props */
export function NoteEditor({ markdown, code, label, loadKey, noteTitles, onInput, onBody, onOpenNote, onOpenItem, restored, toolbarExtra, path, onHoverLine, imageSrc, onImage, readOnly }) {
  const box = useRef(/** @type {HTMLDivElement|null} */ (null));
  const fileIn = useRef(/** @type {HTMLInputElement|null} */ (null));
  const ed = useRef(/** @type {import("../../core/editor.js").EdHandle|null} */ (null));
  const [pick, setPick] = useState(/** @type {PickState|null} */ (null));
  const pickRef = useRef(/** @type {PickState|null} */ (null));
  pickRef.current = pick;
  const marks = noteMarks.value, flashAt = noteFlash.value;
  const cur = noteCur.value, sentList = cur && path && cur.path === path ? cur.sent : null;
  const lineState = useRef({ markers: marks.markers, hover: marks.hover, flash: 0, doc: /** @type {any} */ (null), L: /** @type {any[]} */ ([]),
    sentList: /** @type {any} */ (null), sent: /** @type {Map<string, string[]>} */ (new Map()) });
  lineState.current.markers = marks.markers; lineState.current.hover = marks.hover;
  if (lineState.current.sentList !== sentList) { lineState.current.sentList = sentList; lineState.current.sent = sentKeys(sentList || []); }
  const flashDone = useRef(/** @type {any} */ (null));
  const props = useRef({ onInput, onOpenNote, onOpenItem, noteTitles, code, onHoverLine, path });
  props.current = { onInput, onOpenNote, onOpenItem, noteTitles, code, onHoverLine, path };

  /** What the cursor has just typed: a picker to open, or none. @param {any} editor */
  const look = editor => {
    const s = editor.state.selection;
    if (!s.empty) return setPick(null);
    const $f = s.$from, before = $f.parent.textBetween(0, $f.parentOffset, undefined, "￼"), start = s.from - $f.parentOffset;
    let kind = /** @type {PickState["kind"]|null} */ (null), q = "", at = 0;
    const mn = /\[\[([^[\]\n]{0,60})$/.exec(before), mp = /(^|\s)@([\w .'’-]{0,40})$/.exec(before),
      mi = /(^|\s)#([A-Za-z0-9-]{0,20})$/.exec(before), ms = /^\/(\w{0,20})$/.exec(before);
    if (mn) { kind = "note"; q = mn[1]; at = mn.index; }
    else if (mp && !/\s{2}$/.test(mp[2])) { kind = "person"; q = mp[2]; at = mp.index + mp[1].length; }
    else if (mi) { kind = "item"; q = mi[2]; at = mi.index + mi[1].length; }
    else if (ms && $f.parent.type.name === "paragraph") { kind = "insert"; q = ms[1]; at = 0; }
    if (!kind) return setPick(null);
    const opts = optionsFor(kind, q);
    if (!opts.length && kind !== "note") return setPick(null);
    const c = editor.view.coordsAtPos(s.from), host = box.current ? box.current.closest(".ndoc") : null, hb = host ? host.getBoundingClientRect() : { left: 0, top: 0 };
    const prev = pickRef.current;
    setPick({ kind, from: start + at, to: s.from, q, opts, i: prev && prev.kind === kind ? Math.min(prev.i, Math.max(0, opts.length - 1)) : 0,
      x: Math.max(0, c.left - hb.left), y: c.bottom - hb.top + 4 });
  };
  /** @param {PickState["kind"]} kind @param {string} q @returns {PickOption[]} */
  const optionsFor = (kind, q) => {
    const ql = q.toLowerCase();
    if (kind === "note") {
      /** @type {PickOption[]} */
      const L = props.current.noteTitles().filter(t => !ql || t.toLowerCase().includes(ql)).slice(0, 7).map(t => ({ id: t, label: t, icon: "filetext" }));
      if (q.trim() && !L.some(o => o.label.toLowerCase() === ql.trim())) L.push({ id: "\u0000" + q.trim(), label: `Link to “${q.trim()}”`, sub: "a new note, made when you click it", icon: "plus" });
      return L;
    }
    if (kind === "person") return personOptions(q);
    if (kind === "item") return itemOptions(props.current.code, q);
    return INSERTS.filter(([, l]) => !ql || l.toLowerCase().includes(ql)).map(([id, l, k]) => ({ id, label: l, sub: k }));
  };

  /** Put the chosen option in the text, in place of what was typed. @param {PickOption} o */
  const choose = o => {
    const h = ed.current, p = pickRef.current;
    if (!h || !p) return;
    setPick(null);
    const c = h.editor.chain().focus().deleteRange({ from: p.from, to: p.to });
    if (p.kind === "note") { const t = o.id.startsWith("\u0000") ? o.id.slice(1) : o.id; c.insertContent(`[[${t}]] `).run(); return; }
    if (p.kind === "person") { c.insertContent([{ type: "text", text: "@" }, { type: "text", text: o.id, marks: [{ type: "link", attrs: { href: `creaite:person/${encodeURIComponent(o.id)}` } }] }, { type: "text", text: " " }]).run(); return; }
    if (p.kind === "item") { c.insertContent([{ type: "text", text: o.id, marks: [{ type: "link", attrs: { href: `creaite:item/${o.id}` } }] }, { type: "text", text: " " }]).run(); return; }
    c.run();
    insert(o.id);
  };
  /** The `/` menu and the toolbar's inserts. @param {string} what */
  const insert = what => {
    const h = ed.current;
    if (!h) return;
    const c = h.editor.chain().focus();
    if (what === "heading") c.toggleHeading({ level: 2 }).run();
    else if (what === "checklist") c.toggleTaskList().run();
    else if (what === "table") c.insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run();
    else if (what === "item" || what === "person" || what === "note") c.insertContent(what === "item" ? "#" : what === "person" ? "@" : "[[").run();
    else if (what.startsWith("tpl:")) { const t = /** @type {any} */ (D).note_templates?.[what.slice(4)]; if (t) c.insertContent(t, { contentType: "markdown" }).run(); }
  };
  /** @param {string} cmd */
  const tool = cmd => {
    const h = ed.current;
    if (!h) return;
    const c = h.editor.chain().focus();
    ({ h: () => c.toggleHeading({ level: 2 }), b: () => c.toggleBold(), i: () => c.toggleItalic(), s: () => c.toggleStrike(), code: () => c.toggleCode(),
      ul: () => c.toggleBulletList(), ol: () => c.toggleOrderedList(), task: () => c.toggleTaskList(), quote: () => c.toggleBlockquote(),
      undo: () => c.undo(), redo: () => c.redo() })[cmd]?.().run();
    if (["note", "person", "item", "table"].includes(cmd)) insert(cmd);
    if (cmd === "image" && fileIn.current) fileIn.current.click();
  };
  /** BL-301 B gaps: pictures, as BL-63's in Current state (the image node shown as creaite's figure, the caption its alt text).
      Each is filed in the notes folder's _images/ as it is added, then put after the block holding the cursor (else at the end),
      and its caption gets the focus. @param {FileList|null} files */
  const addImages = async files => {
    for (const f of [...(files || [])]) {
      const ref = onImage ? await onImage(f) : null, h = ed.current;
      if (!ref || !h) continue;
      const st = h.editor.state, end = st.doc.content.size, $p = st.doc.resolve(Math.min(st.selection.from, end)), after = $p.depth ? $p.after(1) : end;
      h.editor.chain().insertContentAt(after, [{ type: "image", attrs: { src: ref, alt: "" } }, ...(after >= end ? [{ type: "paragraph" }] : [])]).run();
      const cap = /** @type {HTMLElement|null} */ (box.current ? box.current.querySelector(`figure[data-ref="${CSS.escape(ref)}"] figcaption`) : null);
      if (cap) cap.focus();
    }
  };

  useEffect(() => {
    const el = box.current;
    if (!el) return undefined;
    const deco = Extension.create({ name: "cxNoteDeco", addProseMirrorPlugins: () => [new Plugin({ key: new PluginKey("cxNoteDeco"),
      props: { decorations: state => {
        const ls = lineState.current;
        /* the Markdown of this state's doc: the handle's value() still answers the loaded text during the first edit's redraw */
        if (ls.doc !== state.doc) { ls.doc = state.doc; ls.L = blockLines(state.doc, ed.current ? markdownOf(ed.current.editor, state.doc.toJSON()).markdown : markdown); }
        const d = decorate(state.doc, () => props.current.noteTitles());
        return d.add(state.doc, lineDecos(ls.L, ls.markers, ls.hover, ls.flash, ls.sent));
      } } })] });
    /* BL-301 D: AI on selected text, the notes' options; a confidential note asks once (per note) before its text goes to Claude */
    const ai = { place: "notes", project: () => props.current.code,
      confidential: () => { const c = noteCur.value; return !!(c && c.path === props.current.path && c.meta && c.meta.confidential); },
      key: () => `note:${props.current.path || ""}` };
    const h = creaiteEditor(el, { features: "notes", markdown, extensions: [deco], ai, imageSrc: ref => (imageSrc ? imageSrc(ref) : null), editorProps: {
      handleKeyDown: (/** @type {any} */ _v, /** @type {KeyboardEvent} */ e) => {
        const p = pickRef.current;
        if (!p) return false;
        if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); const n = p.opts.length || 1; setPick({ ...p, i: (p.i + (e.key === "ArrowDown" ? 1 : n - 1)) % n }); return true; }
        if ((e.key === "Enter" || e.key === "Tab") && p.opts[p.i]) { e.preventDefault(); choose(p.opts[p.i]); return true; }
        if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); setPick(null); return true; }
        return false;
      },
      handleClick: (/** @type {any} */ _v, /** @type {number} */ _pos, /** @type {MouseEvent} */ e) => {
        if (e.altKey) return false;
        const t = /** @type {Element} */ (e.target), item = t.closest && t.closest("[data-item]"), wl = t.closest && t.closest("[data-wl]");
        if (item) { props.current.onOpenItem(item.getAttribute("data-item") || ""); return true; }
        if (wl) { props.current.onOpenNote(wl.getAttribute("data-wl") || ""); return true; }
        return false;
      } } });
    ed.current = h;
    const input = () => { props.current.onInput(); };
    el.addEventListener("input", input);
    h.editor.on("selectionUpdate", () => look(h.editor));
    h.editor.on("update", () => look(h.editor));
    const blur = () => setTimeout(() => { if (!el.contains(document.activeElement)) setPick(null); }, 150);
    el.addEventListener("blur", blur);
    /** @param {MouseEvent} e */
    const over = e => { const f = props.current.onHoverLine; if (!f) return; const t = /** @type {Element} */ (e.target), b = t && t.closest ? t.closest("[data-p]") : null; f(b && el.contains(b) ? +(b.getAttribute("data-p") || 0) : 0); };
    const out = () => { const f = props.current.onHoverLine; if (f) f(0); };
    el.addEventListener("mouseover", over);
    el.addEventListener("mouseleave", out);
    onBody(() => (h.touched() || restored ? h.value() : null));
    return () => { el.removeEventListener("input", input); el.removeEventListener("blur", blur); el.removeEventListener("mouseover", over);
      el.removeEventListener("mouseleave", out); onBody(null); h.destroy(); ed.current = null; lineState.current.doc = null; };
  }, [loadKey]);

  useEffect(() => {          /* #124: read only while its Delete note waits on the approval card */
    const h = ed.current;
    if (h && h.editor) h.editor.setEditable(!readOnly);
  }, [readOnly, loadKey]);

  useEffect(() => {          /* BL-301 E: a note opened at a line (a source link): that line in view, highlighted for a few seconds */
    const h = ed.current, el = box.current;
    if (!h || !el || !path || flashAt.path !== path || !flashAt.line || flashDone.current === flashAt) return;
    flashDone.current = flashAt;
    const line = flashAt.line;
    lineState.current.flash = line;
    h.editor.view.dispatch(h.editor.state.tr.setMeta("cxNoteDecoRedraw", true).setMeta("addToHistory", false));
    const at = /** @type {HTMLElement|null} */ (el.querySelector(`[data-p="${line}"]`));
    if (at) at.scrollIntoView({ block: "center", behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
    setTimeout(() => { if (lineState.current.flash !== line) return; lineState.current.flash = 0; const e2 = ed.current;
      if (e2) e2.editor.view.dispatch(e2.editor.state.tr.setMeta("cxNoteDecoRedraw", true).setMeta("addToHistory", false)); }, 4000);
  }, [flashAt, loadKey, path]);

  useEffect(() => {          /* the item chips' state and the note links follow the data */
    const h = ed.current;
    if (h) h.editor.view.dispatch(h.editor.state.tr.setMeta("cxNoteDecoRedraw", true).setMeta("addToHistory", false));
  });

  const optId = /** @param {number} i */ i => `ntp-${loadKey.replace(/[^\w-]/g, "")}-${i}`;
  return (
    <div class="ned">
      <div class="rtebar nbar" role="toolbar" aria-label="Formatting" onMouseDown={e => { if (/** @type {Element} */ (e.target).closest("button")) e.preventDefault(); }}>
        {TOOLS.map(([id, txt, name], i) => id === "|" ? <span key={`s${i}`} class="rtesep" aria-hidden="true" /> :
          <button key={id} type="button" data-nt={id} aria-label={name} data-tip={name} onClick={() => tool(id)}>{txt}</button>)}
        {toolbarExtra}
        <input ref={fileIn} type="file" class="nimgfile" accept="image/png,image/jpeg" multiple hidden aria-hidden="true" tabIndex={-1}
          onChange={async e => { const i = /** @type {HTMLInputElement} */ (e.target); await addImages(i.files); i.value = ""; }} />
      </div>
      <div ref={box} class="nbody rted" role="textbox" aria-multiline="true" aria-label={label} spellcheck data-ph="Write here… [[ links a note, @ a person, # a work item, / inserts"
        aria-controls={pick ? "ntpick" : undefined} aria-activedescendant={pick && pick.opts[pick.i] ? optId(pick.i) : undefined} />
      {pick ? (
        <div class="ntpick" id="ntpick" role="listbox" aria-label={{ note: "Link to a note", person: "Mention a person", item: "Link a work item", insert: "Insert" }[pick.kind]}
          style={{ left: `${pick.x}px`, top: `${pick.y}px` }} onMouseDown={e => e.preventDefault()}>
          <div class="h" aria-hidden="true">{{ note: "Link to a note", person: "People", item: "Work items", insert: "Insert" }[pick.kind]}</div>
          {pick.opts.length ? pick.opts.map((o, i) => (
            <div key={o.id} id={optId(i)} role="option" aria-selected={i === pick.i ? "true" : "false"} class={`r${i === pick.i ? " on" : ""}`} onClick={() => choose(o)}>
              {o.icon ? <Icon name={o.icon} /> : null}<span class="l">{o.label}</span>{o.sub ? <small>{o.sub}</small> : null}
            </div>)) : <div class="r none">No match</div>}
        </div>) : null}
    </div>
  );
}
