// @ts-check
/* BL-301 D (v20-ai-select): AI on selected text, in every editor: the store. One bar over a selection (aiBar) and one suggestion
   at a time (aiSug), since the live server runs one Claude run at a time.

   - aiAttach(h, ai): what creaiteEditor does with its `ai` option (core/editor.js ED_HOOKS.ai): selecting text shows the bar;
     ⌥/ (Alt+/) opens its menu from the keyboard; ⌘A then the bar applies an option to the whole text.
   - aiRun(option, instruction): the selection goes to /api/edit/ai with the option, the place and the project's code (the server
     adds only the project's name, people and open item IDs; Claude has no tools). A confidential text asks once first (aiSend).
     The client sheet also sends its report (`document`, #123), from which the server binds the client place itself.
   - The answer is a suggestion: it changes nothing until aiAccept(), which puts it in place as one transaction (⌘Z undoes it).
     aiDiscard(), aiRetry() and aiChanges() (Show changes: a word-by-word comparison). The notes under it are BL-106's plain-code
     check (edit_ai.py check): every date, number, name or item ID lost or added.
   - Counts only, never text: offered, used (accepted) and rejected (discarded, or replaced by Try again) under the feature "edit"
     in draft-stats.json (/api/draft/stat). */
import { signal } from "@preact/signals";
import { edReplace, edSelection, edRange } from "../core/editor.js";
import { snack, viaServer } from "../core/server.js";
import { shared } from "../core/state.js";
import { draftAsk, draftStat } from "../drafts.js";

export const AI_FEATURE = "edit";
/** Every option (edit_ai.py OPTIONS): id → [name, what it does]. */
export const AI_OPTIONS = /** @type {Record<string, [string, string]>} */ ({
  rewrite: ["Rewrite clearly", "The same points, in plainer words"],
  shorter: ["Shorter", "About half the length; the facts kept"],
  longer: ["Longer", "Fuller sentences; adds no facts"],
  executive: ["Make it executive", "The executive voice: the position and what matters first"],
  spelling: ["Fix spelling and grammar", "British English; nothing else changed"],
  polish: ["Polish", "Spelling, grammar and a lighter touch on the wording; the facts and length kept"],
  format: ["Format nicely", "Sub-headings, lists and bold where they help"],
  checklist: ["Turn into a checklist", "One task a line, to tick off"],
  summary: ["Summarise at the top", "A short summary first; the text kept below it"],
  formal: ["More formal", "A more formal tone for the email"],
  warmer: ["Warmer", "A warmer, friendlier tone for the email"],
  custom: ["Or say what you want…", "Your own instruction"],
});
/** Each place's options, in the menu's order (edit_ai.py PLACES; test_ai_select checks they agree). */
export const AI_PLACES = /** @type {Record<string, string[]>} */ ({
  notes: ["rewrite", "shorter", "longer", "executive", "spelling", "format", "checklist", "summary", "custom"],
  current: ["rewrite", "shorter", "longer", "executive", "spelling", "format", "summary", "custom"],
  plain: ["rewrite", "shorter", "longer", "executive", "spelling", "custom"],
  email: ["rewrite", "shorter", "longer", "formal", "warmer", "spelling", "custom"],
  line: ["rewrite", "shorter", "executive", "spelling", "custom"],
  report: ["shorter", "executive", "polish", "custom"],     // v2.1.0 P5: the A4 sheet, in a report (Find the source is the sheet's own item)
  minutes: ["shorter", "executive", "polish", "custom"],
  client: ["shorter", "executive", "polish", "custom"],      // #123: the client sheet (client-visible facts only; the reply checked)
  readonly: [],                                              // a sheet that can't be edited: only Find the source
});

/** A place's own name for an option (v2.1.0 P5: the sheet's bar says "Shorten", as its mockup does). */
const AI_NAMES = /** @type {Record<string, Record<string, string>>} */ ({ report: { shorter: "Shorten" }, minutes: { shorter: "Shorten" },
  client: { shorter: "Shorten" } });

/**
 * @typedef {import("../core/editor.js").EdHandle} AiHandle
 * @typedef {import("../core/editor.js").EdAi} AiConf
 * @typedef {import("../core/editor.js").EdRange} AiRange
 * @typedef {{h: AiHandle, ai: AiConf, top: number, left: number, open?: number}} Bar
 * @typedef {{h: AiHandle, ai: AiConf, range: AiRange, option: string, instruction: string, label: string,
 *   status: "ask"|"running"|"ready"|"failed", text?: string, notes?: {id: string, note: string}[], message?: string,
 *   changes?: boolean, steps?: number, top: number, left: number}} Sug
 */
/** @type {import("@preact/signals").Signal<Bar|null>} */
export const aiBar = signal(null);
/** @type {import("@preact/signals").Signal<Sug|null>} */
export const aiSug = signal(null);
/** The confidential texts already asked about on this page (asked once each). */
const AI_ASKED = new Set();

/**
 * The seam for other parts' items on the bar's menu (BL-301 E: "Make this an action…", a risk, a decision, an update): each
 * registers itself with aiAction() and is listed after the place's own options, before "Or say what you want…". Picking one hands
 * it the selection (an EdRange), the editor and its `ai` option; it runs no Claude here and the counts aren't touched.
 * @typedef {{id: string, name: string, line?: string, icon?: string, places?: string[],
 *   run: (range: AiRange, h: AiHandle, ai: AiConf) => void}} AiAction
 */
/** @type {AiAction[]} */
export const AI_ACTIONS = [];
/** Add (or replace, by id) an item on the bar's menu. Its id must not be one of AI_OPTIONS'. @param {AiAction} a */
export function aiAction(a) {
  if (!a || !a.id || AI_OPTIONS[a.id]) return;
  const i = AI_ACTIONS.findIndex(x => x.id === a.id);
  if (i >= 0) AI_ACTIONS[i] = a; else AI_ACTIONS.push(a);
}
/** The registered items a place's bar shows. @param {string} place */
export const aiActionsFor = place => AI_ACTIONS.filter(a => !a.places || a.places.includes(place));
/** Run a registered item on the bar's selection. @param {string} id @returns {boolean} true when `id` was one */
export function aiRunAction(id) {
  const a = AI_ACTIONS.find(x => x.id === id), b = aiBar.value;
  if (!a || !b) return false;
  const range = edSelection(b.h);
  if (!range) { snack("Select some text first (⌘A selects all of it)"); return true; }
  aiBar.value = null;
  a.run(range, b.h, b.ai);
  return true;
}

/** The options a place offers, as the menu lists them, with the registered items before "Or say what you want…".
    @param {string} place @returns {{id: string, name: string, line?: string, icon?: string}[]} */
export const aiItems = place => {
  const own = (AI_PLACES[place] || AI_PLACES.plain).map(id => ({ id, name: (AI_NAMES[place] || {})[id] || AI_OPTIONS[id][0], line: AI_OPTIONS[id][1] }));
  const extra = aiActionsFor(place).map(a => ({ id: a.id, name: a.name, line: a.line, icon: a.icon }));
  const at = own.findIndex(o => o.id === "custom");
  return at < 0 ? own.concat(extra) : [...own.slice(0, at), ...extra, ...own.slice(at)];
};

/** Where the bar (or the card) goes: under the selection, inside the window (fixed, so 320px works).
    @param {AiHandle} h @param {number} from @param {number} to @param {number} [w] */
export function aiPlace(h, from, to, w = 300) {
  const v = h.editor.view;
  let a, b;
  try { a = v.coordsAtPos(from); b = v.coordsAtPos(to); } catch (e) { const r = h.el.getBoundingClientRect(); a = b = { left: r.left, bottom: r.top + 24, top: r.top }; }
  const width = Math.min(w, window.innerWidth - 32), H = window.innerHeight;
  const left = Math.max(16, Math.min(Math.min(a.left, b.left), window.innerWidth - width - 16));
  const below = Math.max(b.bottom, a.bottom) + 6;
  const need = w > 200 ? Math.min(520, H * 0.6) : 340;     // the card's height at most, or the bar with its menu open
  // under the selection when there is room; else above it (the bar), or as low as it still fits (the card)
  const top = H - below >= need ? below : w > 200 ? H - need - 8 : a.top - 40 >= 8 ? a.top - 40 : H - need - 8;
  return { top: Math.max(8, Math.min(top, H - 48)), left };
}

/** Show the bar for `h`'s selection, or hide it when nothing is selected (a suggestion on screen stays).
    @param {AiHandle} h @param {AiConf} ai */
function barFor(h, ai) {
  const s = h.editor.state.selection;
  if (s.empty || h.editor.isDestroyed || !h.editor.state.doc.textBetween(s.from, s.to, " ").trim()) {
    if (aiBar.value && aiBar.value.h === h && !barBusy()) aiBar.value = null;
    return;
  }
  aiHome(h);
  aiBar.value = { h, ai, ...aiPlace(h, s.from, s.to, 120) };
}
/** The layer goes where the editor is: inside its open modal dialog element (the Prep popup), which is in the top layer and makes the
    rest of the page inert, else on the body (COMPONENTS.md: popovers inside a dialog render inside it). @param {AiHandle} h */
export function aiHome(h) {
  const l = document.getElementById("aiLayer");
  if (!l) return;
  const host = /** @type {HTMLElement} */ (h.el.closest("dialog[open]") || document.body);
  if (l.parentElement !== host) host.appendChild(l);
}
/** True while focus is in the AI layer (its menu or box): the bar stays. */
const barBusy = () => { const l = document.getElementById("aiLayer"); return !!(l && l.contains(document.activeElement)); };

/** creaiteEditor's `ai` option (ED_HOOKS.ai): the bar follows the selection; ⌥/ opens its menu; destroying the editor ends both.
    @param {AiHandle} h @param {AiConf} ai */
export function aiAttach(h, ai) {
  const ed = h.editor;
  // after the editor has taken the focus (Tiptap focuses on the next frame), so a selection made with the focus works too
  const update = () => { setTimeout(() => { if (!h.editor.isDestroyed && (h.editor.view.hasFocus() || h.el.contains(document.activeElement))) barFor(h, ai); }, 0); };
  ed.on("selectionUpdate", update);
  ed.on("focus", update);
  h.el.addEventListener("focus", update);
  ed.on("blur", () => { setTimeout(() => { if (aiBar.value && aiBar.value.h === h && !barBusy() && document.activeElement !== h.el) aiBar.value = null; }, 0); });
  h.el.addEventListener("keydown", e => {
    if (e.altKey && !e.metaKey && !e.ctrlKey && (e.code === "Slash" || e.key === "/")) {
      e.preventDefault(); e.stopPropagation();
      if (!edSelection(h)) { snack("Select some text first (⌘A selects all of it), then Alt+/"); return; }
      barFor(h, ai);
      if (aiBar.value) aiBar.value = { ...aiBar.value, open: Date.now() };
    }
  }, true);
  const destroy = h.destroy;
  h.destroy = () => { if (aiBar.value && aiBar.value.h === h) aiBar.value = null; if (aiSug.value && aiSug.value.h === h) aiSug.value = null; destroy(); };
}

/** Run an option on the selection of the editor the bar is over (or `on`, an editor and its ai, with a range of its own).
    @param {string} option @param {string} [instruction] @param {{h: AiHandle, ai: AiConf, range?: AiRange}} [on] */
export function aiRun(option, instruction = "", on) {
  const b = on || aiBar.value;
  if (!b) return;
  const range = (on && on.range) || edSelection(b.h);
  if (!range) { snack("Select some text first (⌘A selects all of it)"); return; }
  if (!AI_OPTIONS[option]) return;
  const where = aiPlace(b.h, range.from, range.to, 480);
  aiHome(b.h);
  aiBar.value = null;
  /** @type {Sug} */
  const s = { h: b.h, ai: b.ai, range, option, instruction, label: option === "custom" ? instruction : AI_OPTIONS[option][0],
    status: "running", ...where };
  const key = b.ai.key ? b.ai.key() : b.ai.place;
  if (b.ai.confidential && b.ai.confidential() && !AI_ASKED.has(key)) { aiSug.value = { ...s, status: "ask" }; return; }
  ask(s);
}
/** "Send to Claude" on a confidential text's question: remembered for the page, then the run. */
export function aiSend() {
  const s = aiSug.value;
  if (!s || s.status !== "ask") return;
  AI_ASKED.add(s.ai.key ? s.ai.key() : s.ai.place);
  ask(s);
}

/** @param {Sug} s */
async function ask(s) {
  if (!viaServer()) { aiSug.value = { ...s, status: "failed", message: "AI on selected text needs the live server" }; return; }
  if (shared.RUN || shared.GEN.run || shared.BUSY || shared.PREPRUN) { aiSug.value = { ...s, status: "failed", message: "ask creaite is busy; try again when it's finished" }; return; }
  const cur = { ...s, status: /** @type {"running"} */ ("running"), steps: 0 };
  aiSug.value = cur;
  const doc = s.ai.document ? s.ai.document() : null;                 // #123: the client sheet names its report; the server binds the place
  const r = await draftAsk({ option: s.option, instruction: s.instruction, text: s.range.text, place: s.ai.place,
    code: (s.ai.project && s.ai.project()) || "", ...(doc ? { document: doc } : {}) }, { url: "/api/edit/ai", label: `${s.label}, with Claude`, status: () => {} });
  if (aiSug.value !== cur) return;                                     // discarded, or the editor closed, while it ran
  if (r.ok && r.text) { draftStat(AI_FEATURE, "offered"); aiSug.value = { ...cur, status: "ready", text: String(r.text), notes: r.notes || [] }; }
  else aiSug.value = { ...cur, status: "failed", message: r.message || "No suggestion came back" };
}

/** Accept: the suggestion replaces the text it was made from, as one transaction (⌘Z undoes it). */
export function aiAccept() {
  const s = aiSug.value;
  if (!s || s.status !== "ready") return;
  if (!edReplace(s.h, s.range, s.text || "")) { snack("The text has changed since you asked; nothing was changed. Try again."); return; }
  aiSug.value = null;
  draftStat(AI_FEATURE, "used");
  snack("Suggestion used. ⌘Z undoes it.");
}
/** Discard: nothing changes; focus goes back to the text. */
export function aiDiscard() {
  const s = aiSug.value;
  if (!s) return;
  if (s.status === "ready") draftStat(AI_FEATURE, "rejected");
  aiSug.value = null;
  if (!s.h.editor.isDestroyed) s.h.focus();
}
/** Try again: the same option on the same text (the one shown counts as rejected). */
export function aiRetry() {
  const s = aiSug.value;
  if (!s || s.status === "running") return;
  if (s.status === "ready") draftStat(AI_FEATURE, "rejected");
  const range = edRange(s.h, s.range.from, s.range.to);
  if (!range || range.text !== s.range.text) { aiSug.value = null; snack("The text has changed since you asked; select it again."); return; }
  ask({ ...s, text: undefined, notes: undefined, message: undefined, changes: false });
}
/** Show changes, or hide them. */
export function aiChanges() { const s = aiSug.value; if (s && s.status === "ready") aiSug.value = { ...s, changes: !s.changes }; }

/**
 * Word by word, what changed from `a` to `b`: [[kind, text]] with kind "=" (kept), "-" (taken out) or "+" (put in). The
 * spaces go with the words. Over about 40,000 word pairs it is simply the old text out and the new one in.
 * @param {string} a @param {string} b @returns {["=" | "-" | "+", string][]}
 */
export function aiDiff(a, b) {
  const wa = String(a).match(/\s+|[^\s]+/g) || [], wb = String(b).match(/\s+|[^\s]+/g) || [];
  if (wa.length * wb.length > 40000) return /** @type {["-"|"+", string][]} */ ([["-", String(a)], ["+", String(b)]]).filter(x => x[1]);
  const n = wa.length, m = wb.length, L = Array.from({ length: n + 1 }, () => new Uint16Array(m + 1));
  for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) L[i][j] = wa[i] === wb[j] ? L[i + 1][j + 1] + 1 : Math.max(L[i + 1][j], L[i][j + 1]);
  /** @type {["=" | "-" | "+", string][]} */
  const out = [];
  const push = (/** @type {"=" | "-" | "+"} */ k, /** @type {string} */ t) => { const last = out[out.length - 1]; if (last && last[0] === k) last[1] += t; else out.push([k, t]); };
  let i = 0, j = 0;
  while (i < n && j < m) { if (wa[i] === wb[j]) { push("=", wa[i]); i++; j++; } else if (L[i + 1][j] >= L[i][j + 1]) push("-", wa[i++]); else push("+", wb[j++]); }
  while (i < n) push("-", wa[i++]);
  while (j < m) push("+", wb[j++]);
  return out;
}
