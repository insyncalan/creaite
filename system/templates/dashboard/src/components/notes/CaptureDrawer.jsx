// @ts-check
/* CaptureDrawer (BL-301 C, dev/mockups/wiki-notes-mockup.html "C · Capture drawer"): a note from any page without leaving it.
   ⌘⇧N, ⌘K "New note" and "Note for this meeting" on Today open it at the right of the page (not modal: the page stays usable).
   - The project is guessed by the server from the project register's signals, by cx-minutes' matching rules (capture.py), and
     shown with its reason ("guessed from “Omar Ali” and “data access”"); Alan can change it, and then it stays his choice. No
     guess is Unfiled (the portfolio's notes folder, _Portfolio/08 Notes).
   - The note is the one editor (core/editor.js, features "notes"). What is typed is kept as a draft on the server
     (system/staging/drafts/notes/) as Alan types; Done writes the note file through filechange.py (backed up, logged,
     undoable). Closing keeps the draft: it is listed at the foot, and ⌘⇧N carries on with it.
   - Two endings: Done keeps the note; Done and find updates also opens it in full on its project's Notes tab with Find updates
     (parts B and E: noteRequest in stores/capture.js, and the address's find=1).
   - "Note for this meeting" starts the Working session template with the meeting's title, date and attendees (from the saved
     calendar) and the project Prep matched.
   - Recent notes are listed at the foot. It replaces FR-71's Quick capture form (old quick notes stay in minutes/).
   Text only through JSX. */
import { render } from "preact";
import { useEffect, useRef, useState } from "preact/hooks";
import { signal } from "@preact/signals";
import { P, pName } from "../../core/data.js";
import { creaiteEditor } from "../../core/editor.js";
import { fd, TODAY } from "../../core/page.js";
import { api, oneLine, snack, viaServer } from "../../core/server.js";
import { go } from "../../core/nav.js";
import { capOpen, noteHref, noteRequest } from "../../stores/capture.js";
import { IconButton } from "../IconButton.jsx";

/** @typedef {{id: string, code: string, chosen: boolean, how: string, reason: string, title: string, body: string,
    template: string, date: string, with: string[], confidential: boolean, saved: string, loaded?: string}} Note
    `code` "" is Unfiled. `chosen`: Alan picked the project (the guess stops). `how`: "guess", "meeting", "chosen" or "".
    `loaded`: the title and body as the drawer opened them (a meeting's template), so an untouched note keeps no draft.
    `confidential`: the note's Confidential switch (off unless Alan sets it): written to its front matter, so search, ask creaite,
    Prep pages and client output leave its text out, like other confidential material. */
/** @typedef {{path: string, title: string, code: string, at: string}} Recent */
/** @typedef {{id: string, title: string, code: string, at: string, body: string, template: string, date: string, with: string[], confidential?: boolean}} Draft */

const WAIT = 600;                                    // ms after the last key before the draft is kept and the project guessed
const newId = () => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
/** @returns {Note} */
const blank = () => ({ id: newId(), code: "", chosen: false, how: "", reason: "", title: "", body: "", template: "blank", date: "", with: [], confidential: false, saved: "" });

/** The note in the drawer (kept while the drawer is closed, so ⌘⇧N carries on). */
export const capNote = signal(blank());
const capRecent = signal(/** @type {{notes: Recent[], drafts: Draft[]}} */ ({ notes: [], drafts: [] }));
const capMsg = signal("");
const capBusy = signal(false);

let capHostEl = /** @type {HTMLElement|null} */ (null);
let ed = /** @type {import("../../core/editor.js").EdHandle|null} */ (null);
let timer = 0, opener = /** @type {Element|null} */ (null), seq = 0;

/** A project's name, or Unfiled. @param {string} code */
const where = code => code && code !== "_portfolio" ? pName(code) : "Unfiled";
/** Whether the note holds anything to save. @param {Note} n */
const hasText = n => !!(n.title.trim() || n.body.trim());
/** Whether Alan has typed anything since the drawer opened it (only then is a draft kept). @param {Note} n */
const typed = n => hasText(n) && `${n.title}\u0000${n.body}` !== (n.loaded ?? "\u0000");

/** Change the note in the drawer. @param {Partial<Note>} patch */
function patchNote(patch) { capNote.value = { ...capNote.value, ...patch }; }

/** Keep the draft and guess the project, a moment after the last key. */
function capSoon() { clearTimeout(timer); timer = window.setTimeout(() => { keep(); guess(); }, WAIT); }

/** Keep what is typed as a draft on the server. */
async function keep() {
  const n = capNote.value;
  if (!viaServer() || !typed(n)) return;
  const r = await api("/api/notes/capture/draft", { id: n.id, code: n.code, title: n.title, body: n.body, template: n.template, date: n.date, with: n.with, confidential: n.confidential });
  if (capNote.value.id !== n.id) return;
  if (r.ok) patchNote({ saved: r.at || "" }); else capMsg.value = oneLine(r.message || "The draft wasn't kept.");
}

/** Ask the server which project the note is about (unless Alan chose one, or the meeting gave it). */
async function guess() {
  const n = capNote.value;
  if (!viaServer() || n.chosen || n.how === "meeting" || !(n.title.trim() || n.body.trim())) return;
  const mine = ++seq, r = await api("/api/notes/capture/guess", { title: n.title, body: n.body });
  if (mine !== seq || !r.ok || capNote.value.id !== n.id || capNote.value.chosen) return;
  const code = r.code && P.some(p => p.code === r.code) ? r.code : "";
  patchNote({ code, how: "guess", reason: r.reason || "" });
}

/** The newest notes and the drafts kept, for the foot. */
async function loadRecent() {
  if (!viaServer()) { capRecent.value = { notes: [], drafts: [] }; return; }
  const r = await api("/api/notes/capture/recent", {});
  if (r.ok) capRecent.value = { notes: r.notes || [], drafts: r.drafts || [] };
}

/** Put a note into the drawer and its editor. @param {Note} n */
function load(n) {
  capNote.value = { ...n, loaded: n.loaded ?? `${n.title}\u0000${n.body}` };
  capMsg.value = "";
  if (ed) ed.setValue(n.body);
}

/**
 * Open the capture drawer. With `meeting` it starts a Working session note for that meeting (its title, date and attendees);
 * with `body`, a note holding that text. Otherwise it carries on with the note in the drawer, or starts a blank one.
 * @param {{meeting?: {day: string, start: string, title: string}, body?: string}} [o]
 */
export async function openCapture(o = {}) {
  if (!capHostEl) {
    capHostEl = document.createElement("div");
    capHostEl.id = "capHost";
    document.body.appendChild(capHostEl);
    render(<CaptureDrawer />, capHostEl);
  }
  if (!capOpen.value) opener = document.activeElement;
  capOpen.value = true;
  if (o.meeting) {
    const m = o.meeting;
    /** @type {Note} */
    const n = { ...blank(), template: "working-session", title: m.title, date: m.day, how: "", reason: "" };
    if (viaServer()) {
      const r = await api("/api/notes/capture/start", { meeting: m });
      if (r.ok) Object.assign(n, { body: r.body || "", with: r.with || [], date: r.date || m.day, title: r.title || m.title,
        code: r.code && P.some(p => p.code === r.code) ? r.code : "", how: r.code ? "meeting" : "", reason: r.code ? "from the meeting's title" : "" });
      else capMsg.value = oneLine(r.message || "");
    }
    load(n);
    if (!n.code) guess();
  } else if (o.body != null) {
    load({ ...blank(), body: o.body });
    guess();
  }
  loadRecent();
  requestAnimationFrame(() => { if (ed) ed.focus("end"); });
}

/** Close the drawer; what is typed stays as a draft (listed at the foot, and ⌘⇧N carries on with it). */
export function closeCapture() {
  if (!capOpen.value) return;
  clearTimeout(timer);
  const n = capNote.value;
  if (typed(n)) { keep(); snack("Note kept as a draft: ⌘⇧N to carry on"); }
  capOpen.value = false;
  const back = opener;
  opener = null;
  if (back && back instanceof HTMLElement && back.isConnected) back.focus();
}

/** Open a note in full on its project's Notes tab (parts B and E read noteRequest and the address).
    @param {{code: string, path: string, find: boolean}} r */
export function openNoteFull(r) {
  noteRequest.value = r;
  if (r.code && r.code !== "_portfolio" && P.some(p => p.code === r.code)) go("cockpit", r.code); else go("projects");
  try { history.replaceState(history.state, "", noteHref(r)); } catch (e) { /* a page opened as a file */ }
}

/** Done: write the note through the server (filechange.py); with `find`, open it with Find updates. @param {boolean} find */
export async function captureDone(find) {
  clearTimeout(timer);
  const n = capNote.value;
  if (!viaServer()) { capMsg.value = "Saving a note needs the live server."; return false; }
  if (!hasText(n)) { capMsg.value = "Write the note first."; return false; }
  capBusy.value = true;
  try {
    const r = await api("/api/notes/capture/done", { id: n.id, code: n.code || "_portfolio", title: n.title, body: n.body,
      template: n.template, date: n.date, with: n.with, confidential: n.confidential });
    if (!r.ok) { capMsg.value = oneLine(r.message || "The note wasn't saved."); return false; }
    capNote.value = blank();
    if (ed) ed.setValue("");
    capOpen.value = false;
    opener = null;
    snack(`Note saved: ${r.title} (${where(r.code)})`);
    if (find && r.path) openNoteFull({ code: r.code, path: r.path, find: true });
    return true;
  } finally { capBusy.value = false; }
}

/** Carry on with a draft the server kept. @param {Draft} d */
function resume(d) {
  load({ ...blank(), id: d.id, code: d.code === "_portfolio" ? "" : d.code || "", chosen: !!d.code && d.code !== "_portfolio",
    how: d.code && d.code !== "_portfolio" ? "chosen" : "", reason: "", title: d.title || "", body: d.body || "",
    template: d.template || "blank", date: d.date || "", with: d.with || [], confidential: !!d.confidential, saved: d.at || "", loaded: "" });
  requestAnimationFrame(() => { if (ed) ed.focus("end"); });
}

/** Drop the draft in the drawer and start again. */
async function discard() {
  const n = capNote.value;
  clearTimeout(timer);
  if (viaServer()) await api("/api/notes/capture/discard", { id: n.id });
  load(blank());
  loadRecent();
}

/** A time stamp as the foot shows it: today's as HH:MM, another day's as DD-MM-YYYY. @param {string} at */
const when = at => !at ? "" : at.slice(0, 10) === TODAY ? at.slice(11, 16) : fd(at.slice(0, 10));

/** The drawer. */
export function CaptureDrawer() {
  const box = useRef(/** @type {HTMLDivElement|null} */ (null));
  const [, redraw] = useState(0);
  const open = capOpen.value, n = capNote.value, recent = capRecent.value, live = viaServer();
  useEffect(() => {
    const el = box.current;
    if (!el) return undefined;
    ed = creaiteEditor(el, /** @type {any} */ ({ features: "notes", markdown: capNote.value.body }));
    if (capOpen.value) ed.focus("end");
    const input = () => { if (!ed) return; patchNote({ body: ed.value() }); capSoon(); };
    el.addEventListener("input", input);
    return () => { el.removeEventListener("input", input); if (ed) ed.destroy(); ed = null; };
  }, []);
  useEffect(() => { const t = window.setInterval(() => redraw(x => x + 1), 30000); return () => clearInterval(t); }, []);
  /** @param {KeyboardEvent} e */
  const keys = e => {
    if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); closeCapture(); return; }
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) { e.preventDefault(); e.stopPropagation(); captureDone(e.shiftKey); }
  };
  const why = n.chosen ? "chosen by you" : n.reason;
  const off = live ? undefined : "Saving a note needs the live server";
  const meeting = n.template === "working-session";
  const drafts = recent.drafts.filter(d => d.id !== n.id);
  return (
    <aside id="capDrawer" class="capdrawer" role="dialog" aria-modal="false" aria-labelledby="capH" hidden={!open} onKeyDown={keys}>
      <div class="caphead">
        <h2 id="capH">{meeting ? "Note for this meeting" : "New note"}</h2>
        <span class="sp" />
        {typed(n) ? <button type="button" class="linkbtn capdiscard" onClick={() => discard()}>Discard</button> : null}
        <IconButton icon="x" label="Close" name="Close the note (the draft is kept)" onClick={() => closeCapture()} />
      </div>
      <div class="capwhere">
        <label for="capProj">Project</label>
        <select id="capProj" value={n.code} aria-describedby="capWhy"
          onChange={e => { const code = /** @type {HTMLSelectElement} */ (e.currentTarget).value; patchNote({ code, chosen: true, how: "chosen" }); capSoon(); }}>
          <option value="">Unfiled</option>
          {P.map(p => <option value={p.code}>{p.name}</option>)}
        </select>
        <span class="sub" id="capWhy">{why ? why : n.code ? "" : "Unfiled until something names a project"}</span>
      </div>
      {meeting ? <div class="sub capmeet">Working session{n.date ? ` · ${fd(n.date)}` : ""}{n.with.length ? ` · with ${n.with.join(", ")}` : ""}</div> : null}
      <input id="capTitle" class="captitle" type="text" aria-label="Title" placeholder="Title (or the first line)" value={n.title} autocomplete="off"
        onInput={e => { patchNote({ title: /** @type {HTMLInputElement} */ (e.currentTarget).value }); capSoon(); }} />
      <label class="capconf">
        <input type="checkbox" class="switch" role="switch" id="capConf" checked={n.confidential}
          onChange={e => { patchNote({ confidential: /** @type {HTMLInputElement} */ (e.currentTarget).checked }); capSoon(); }} />
        <span>Confidential</span>
        {n.confidential ? <span class="sub">Kept out of prep pages and client reports; Claude reads it only if you say yes</span> : null}
      </label>
      <div ref={box} id="capBody" class="capbody" role="textbox" aria-multiline="true" aria-label="Note" aria-describedby="capSaved"
        data-ph="Type the note: what was said, what you think, who to follow up…" spellcheck />
      <div class="capfoot">
        <span class="sub" id="capSaved" role="status" aria-live="polite">{capMsg.value || (n.saved ? `Draft saved ${when(n.saved)}` : live ? "Saved as you type" : "Notes need the live server")}</span>
        <span class="sp" />
        <button type="button" class="btn ai" id="capFind" disabled={capBusy.value} aria-disabled={off ? "true" : undefined} data-tip={off || "Save it, then open it with Find updates"}
          onClick={() => captureDone(true)}>Done and find updates</button>
        <button type="button" class="btn primary" id="capDone" disabled={capBusy.value} aria-disabled={off ? "true" : undefined} data-tip={off} data-key="⌘↵"
          onClick={() => captureDone(false)}>Done</button>
      </div>
      {drafts.length || recent.notes.length ? (
        <div class="caprecent" aria-labelledby="capRecentH" role="region">
          <h3 id="capRecentH">Recent notes</h3>
          <ul>
            {drafts.map(d => (
              <li><button type="button" class="caprow" onClick={() => resume(d)} aria-label={`Carry on with the draft ${d.title || "Untitled"}`}>
                <b>{d.title || (d.body || "").trim().split("\n")[0].slice(0, 60) || "Untitled"}</b><span class="sp" />
                <span class="sub">Draft · {where(d.code)} · {when(d.at)}</span></button></li>))}
            {recent.notes.map(r => (
              <li><button type="button" class="caprow" onClick={() => { capOpen.value = false; openNoteFull({ code: r.code, path: r.path, find: false }); }}
                aria-label={`Open the note ${r.title}`}>
                <b>{r.title}</b><span class="sp" /><span class="sub">{where(r.code)} · {when(r.at)}</span></button></li>))}
          </ul>
        </div>) : null}
    </aside>
  );
}
