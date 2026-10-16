// @ts-check
/* ===== #122 step A ===== the editor's chrome profiles: which toolbar each kind of editor shows, and what each button does.
   core/editor.js shares the document (the schema, loading and saving); this file shares what is drawn above it. A host asks
   for a profile (components/EditorBar.jsx draws it) and the same buttons then show, and do the same, wherever that profile is
   used (Alan, 15-10-2026: "all editors should be consistent").

   - notes:   Notes and the capture drawer. Headings 1 to 3, B I S code, lists, checklist, quote, link, [[ @ #, table, image.
   - current: Current state's two panes. The same, minus what its storage can't hold yet: no checklist (v2.2.0), no code (Word can't
              show it), no table, and no [[ @ # (item links come with the shared chips, #122 step C).
   - plain:   item fields, Prep notes, draft boxes. No toolbar at all: they store plain text (decision 2). They get the
              selection bar (#117) and links (v2.2.0), never headings or checklists.
   - none:    a host that sets its own frame (the report sheets) and draws nothing.

   The tools a host does itself (it owns the pickers and the file input) are `host: true`: the bar shows one only when the host
   says it can do it, so the capture drawer, which has no pickers yet, shows the shared buttons alone.

   Heading levels: the editor always has Heading 1 to 3. Where the text is stored decides what they are written as: Notes keeps
   `#`, `##`, `###`; Current state is read to the next `## ` line (build_dashboard.py, report.py), so its levels are written
   `###`, `####`, `#####` (HEAD_SHIFT; creaiteEditor `headShift`; Alan, 15-10-2026).

   ===== #122 step B ===== the `/` menu. Each profile also names the rows its `/` menu offers (`slash`, in order, grouped by ED_SLASH);
   components/SlashMenu.jsx draws it at the caret. A row writes no heading level itself: Heading 1 to 3 are the editor's levels, and
   the host's `headShift` writes them (Notes `#`, Current state `###`). */

/** How many `#` Current state adds to the editor's heading level when it writes them (and takes off when it reads them). */
export const HEAD_SHIFT = 2;

/** @typedef {{id: string, label: string, name: string, tip?: string, keys?: string, rc?: string, host?: boolean,
    run?: (c: any, e: any) => any, on?: (e: any) => boolean, can?: (e: any) => boolean}} ToolDef */
/** The tools. `run` gets a focused Tiptap chain (and the editor) and returns the chain; `on` says whether it is in force at the cursor (aria-pressed).
    `rc` is the name Current state's buttons have always carried in data-rc (kept so the tests and the dashboard spec still find them).
    @type {Record<string, ToolDef>} */
export const ED_TOOLS = {
  h1: { id: "h1", label: "H1", name: "Heading 1", run: c => c.toggleHeading({ level: 1 }), on: e => e.isActive("heading", { level: 1 }) },
  h2: { id: "h2", label: "H2", name: "Heading 2", run: c => c.toggleHeading({ level: 2 }), on: e => e.isActive("heading", { level: 2 }) },
  h3: { id: "h3", label: "H3", name: "Heading 3", run: c => c.toggleHeading({ level: 3 }), on: e => e.isActive("heading", { level: 3 }) },
  b: { id: "b", keys: "Meta+B Control+B", label: "B", name: "Bold", tip: "Bold (⌘B)", rc: "bold", run: c => c.toggleBold(), on: e => e.isActive("bold") },
  i: { id: "i", keys: "Meta+I Control+I", label: "I", name: "Italic", tip: "Italic (⌘I)", rc: "italic", run: c => c.toggleItalic(), on: e => e.isActive("italic") },
  s: { id: "s", keys: "Meta+Shift+X Control+Shift+X", label: "S", name: "Strikethrough", tip: "Strikethrough (⌘⇧X)", rc: "strikeThrough", run: c => c.toggleStrike(), on: e => e.isActive("strike") },
  code: { id: "code", label: "</>", name: "Code", run: c => c.toggleCode(), on: e => e.isActive("code") },
  ul: { id: "ul", label: "•", name: "Bulleted list", rc: "insertUnorderedList", run: c => c.toggleBulletList(), on: e => e.isActive("bulletList") },
  ol: { id: "ol", label: "1.", name: "Numbered list", rc: "insertOrderedList", run: c => c.toggleOrderedList(), on: e => e.isActive("orderedList") },
  task: { id: "task", label: "☑", name: "Checklist", run: c => c.toggleTaskList(), on: e => e.isActive("taskList") },
  outdent: { id: "outdent", keys: "Shift+Tab", label: "⇤", name: "Outdent", tip: "Outdent (⇧Tab)", rc: "outdent", run: (c, e) => c.liftListItem(itemType(e)),
    can: e => e.isActive("listItem") || e.isActive("taskItem") },
  indent: { id: "indent", keys: "Tab", label: "⇥", name: "Indent", tip: "Indent: a nested list (Tab)", rc: "indent", run: (c, e) => c.sinkListItem(itemType(e)),
    can: e => e.isActive("listItem") || e.isActive("taskItem") },
  quote: { id: "quote", label: "❝", name: "Quote", rc: "formatBlock:blockquote", run: c => c.toggleBlockquote(), on: e => e.isActive("blockquote") },
  link: { id: "link", keys: "Meta+Shift+K Control+Shift+K", label: "Link", name: "Link", tip: "Add or edit a link (⌘⇧K)", rc: "link", on: e => e.isActive("link") },
  unlink: { id: "unlink", label: "Unlink", name: "Remove the link", rc: "unlink", run: c => c.extendMarkRange("link").unsetLink(), can: e => e.isActive("link") },
  clear: { id: "clear", label: "Clear", name: "Clear formatting", rc: "removeFormat", run: c => c.unsetAllMarks().clearNodes() },
  note: { id: "note", label: "[[ ]]", name: "Link to a note", tip: "Link to a note ([[)", host: true },
  person: { id: "person", label: "@", name: "Mention a person", tip: "Mention a person (@)", host: true },
  item: { id: "item", label: "#ID", name: "Link a work item", tip: "Link a work item (#)", host: true },
  table: { id: "table", label: "▦", name: "Table", host: true },
  image: { id: "image", label: "Image", name: "Add a picture", tip: "Add a picture here (PNG or JPEG, up to 2 MB)", rc: "image", host: true },
  undo: { id: "undo", keys: "Meta+Z Control+Z", label: "↶", name: "Undo", tip: "Undo (⌘Z)", rc: "undo", run: c => c.undo() },
  redo: { id: "redo", keys: "Meta+Shift+Z Control+Shift+Z", label: "↷", name: "Redo", tip: "Redo (⌘⇧Z)", rc: "redo", run: c => c.redo() },
};
/** @typedef {{id: string, group: string, name: string, desc: string, icon: string, key?: string, host?: boolean, node?: string, is?: string, alias?: string[],
    run?: (c: any, e: any) => any}} SlashDef */
/** The rows of the `/` menu. `run` gets a focused chain that has already removed the typed "/query". `host` rows are done by the host
    (it owns the pickers, the table's template and the file input) and show only when it can; `node` names a schema node the row needs.
    @type {Record<string, SlashDef>} */
export const ED_SLASH = {
  text: { id: "text", group: "Text", name: "Text", desc: "Plain paragraph", icon: "T", alias: ["paragraph", "plain"], run: c => c.setParagraph() },
  h1: { id: "h1", group: "Text", name: "Heading 1", desc: "Big section heading", icon: "H1", alias: ["h1", "heading1"], run: c => c.setHeading({ level: 1 }) },
  h2: { id: "h2", group: "Text", name: "Heading 2", desc: "Medium section heading", icon: "H2", alias: ["h2", "heading2"], run: c => c.setHeading({ level: 2 }) },
  h3: { id: "h3", group: "Text", name: "Heading 3", desc: "Small section heading", icon: "H3", alias: ["h3", "heading3"], run: c => c.setHeading({ level: 3 }) },
  ul: { id: "ul", group: "Lists", name: "Bulleted list", desc: "A simple list", icon: "•", alias: ["ul", "bullet", "bullets"], is: "bulletList", run: c => c.toggleBulletList() },
  ol: { id: "ol", group: "Lists", name: "Numbered list", desc: "A list with numbers", icon: "1.", alias: ["ol", "num", "number", "numbered"], is: "orderedList", run: c => c.toggleOrderedList() },
  task: { id: "task", group: "Lists", name: "Checklist", desc: "Tick things off", icon: "☑", alias: ["todo", "check", "checkbox"], is: "taskList", node: "taskList", run: c => c.toggleTaskList() },
  quote: { id: "quote", group: "Blocks", name: "Quote", desc: "Set a passage apart", icon: "❝", alias: ["quote", "bq", "blockquote"], is: "blockquote", run: c => c.toggleBlockquote() },
  codeblock: { id: "codeblock", group: "Blocks", name: "Code", desc: "Fixed-width text", icon: "</>", alias: ["code"], node: "codeBlock", run: c => c.toggleCodeBlock() },
  table: { id: "table", group: "Blocks", name: "Table", desc: "Rows and columns", icon: "▦", alias: ["table"], host: true },
  image: { id: "image", group: "Blocks", name: "Image", desc: "PNG or JPEG, up to 2 MB", icon: "▣", alias: ["img", "picture", "photo"], host: true },
  item: { id: "item", group: "Link", name: "Work item", desc: "Link an action, risk, issue or decision", icon: "#", key: "#", host: true },
  person: { id: "person", group: "Link", name: "Person", desc: "Mention someone from the register", icon: "@", key: "@", host: true },
  note: { id: "note", group: "Link", name: "Note", desc: "Link to another note", icon: "[[", key: "[[", host: true },
  "tpl:stakeholder": { id: "tpl:stakeholder", group: "Templates", name: "Stakeholder", desc: "Role, what matters to them, how they work", icon: "◇", host: true },
  "tpl:lessons-learned": { id: "tpl:lessons-learned", group: "Templates", name: "Lessons learned", desc: "What happened, what to change", icon: "◇", host: true },
  "tpl:working-session": { id: "tpl:working-session", group: "Templates", name: "Working session", desc: "A conversation: its date and who it was with", icon: "◇", host: true },
};
/** The `/` menu's rows per profile, in order; a profile with none has no menu (plain: its fields store plain text). @type {Record<string, string[]>} */
export const ED_SLASH_ROWS = {
  notes: ["text", "h1", "h2", "h3", "ul", "ol", "task", "quote", "codeblock", "table", "image", "item", "person", "note",
    "tpl:stakeholder", "tpl:lessons-learned", "tpl:working-session"],
  current: ["text", "h1", "h2", "h3", "ul", "ol", "quote", "image"],
  plain: [], none: [],
};
/** The rows of a profile's `/` menu for a host that can do `hostRows` and an editor whose schema is `schema`, filtered and ranked by what is
    typed (BL-122 B review L3): a row matches its id or short alias (`h1`, `ul`, `ol`, `todo`, `bq`), its name (`heading 2`, one space allowed)
    or its description; best first: an exact id or alias, then a name or alias that starts with it, then a word of the name, then the rest
    (the order of the menu breaks ties). "h" keeps the mockup's rule: the headings first, then every other row with an h in it.
    @param {string} profile @param {string[]} hostRows @param {any} schema @param {string} [q] @returns {SlashDef[]} */
export function slashRows(profile, hostRows, schema, q = "") {
  const ql = q.trim().toLowerCase().replace(/\s+/g, " ");
  const avail = (ED_SLASH_ROWS[profile] || []).map(id => ED_SLASH[id]).filter(r => r && (!r.host || hostRows.includes(r.id)) && (!r.node || !schema || schema.nodes[r.node]));
  if (!ql) return avail;
  const typed = ql.split(" ");
  /** @param {string} name @returns {boolean} */
  const inOrder = name => { const w = name.split(" "); let at = 0; return typed.every(t => { while (at < w.length && !w[at].startsWith(t)) at++; return at++ < w.length; }); };
  /** @param {SlashDef} r @returns {number} 0 best, 9 no match */
  const rank = r => {
    const name = r.name.toLowerCase(), ids = [r.id, ...(r.alias || [])];
    if (ids.includes(ql)) return 0;
    if (ids.some(x => x.startsWith(ql)) || name.startsWith(ql)) return 1;
    if (typed.length > 1 && inOrder(name)) return 1;                 /* "head 2" is Heading 2, "bull l" is Bulleted list: each typed word starts a word of the name, in order */
    if (name.split(" ").some(w => w.startsWith(ql))) return 2;
    if (name.includes(ql) || r.desc.toLowerCase().includes(ql)) return 3;
    return 9;
  };
  return avail.map((r, i) => ({ r, i, k: rank(r) })).filter(x => x.k < 9).sort((a, b) => a.k - b.k || a.i - b.i).map(x => x.r);
}

/** The list-item node a sink or lift acts on at the cursor: a checklist's item in a checklist, else a list's. @param {any} e */
function itemType(e) { return e.isActive("taskItem") ? "taskItem" : "listItem"; }

/** @typedef {{tools: string[], tip: string}} Profile */
/** Each profile's toolbar, in order ("|" is a divider). What a profile leaves out is left out on purpose (see the top).
    @type {Record<string, Profile>} */
export const ED_PROFILES = {
  notes: { tip: "Notes and the capture drawer",
    tools: ["h1", "h2", "h3", "|", "b", "i", "s", "code", "|", "ul", "ol", "task", "outdent", "indent", "quote", "|", "link", "unlink", "clear", "|",
      "note", "person", "item", "table", "image", "|", "undo", "redo"] },
  current: { tip: "Current state",
    tools: ["h1", "h2", "h3", "|", "b", "i", "s", "|", "ul", "ol", "outdent", "indent", "quote", "image", "|", "link", "unlink", "clear", "|", "undo", "redo"] },
  plain: { tip: "item fields, Prep notes, draft boxes: plain text, no toolbar", tools: [] },
  none: { tip: "a host that draws its own frame (the report sheets)", tools: [] },
};

/** The tools a profile shows, with the dividers tidied (none first, last or doubled), for a host that can do `hostTools`.
    @param {string} profile @param {string[]} [hostTools] @returns {(ToolDef|"|")[]} */
export function profileTools(profile, hostTools = []) {
  const want = (ED_PROFILES[profile] || ED_PROFILES.none).tools.filter(id => id === "|" || (ED_TOOLS[id] && (!ED_TOOLS[id].host || hostTools.includes(id))));
  /** @type {(ToolDef|"|")[]} */
  const out = [];
  for (const id of want) {
    if (id === "|") { if (out.length && out[out.length - 1] !== "|") out.push("|"); } else out.push(ED_TOOLS[id]);
  }
  while (out.length && out[out.length - 1] === "|") out.pop();
  return out;
}

/** Run a shared tool on an editor: true when it was one. A link is the bar's own form, so `link` is left to the caller.
    @param {{editor: any}} h @param {string} id */
export function runTool(h, id) {
  const t = ED_TOOLS[id];
  if (!h || !t || !t.run) return false;
  const e = h.editor;
  t.run(e.chain().focus(), e).run();
  return true;
}
