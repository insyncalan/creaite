// @ts-check
/* NotesPage (BL-301 B): a project's Notes tab (#notes=ABC), or the portfolio's notes (#notes=_portfolio, under Portfolio).
   Left: the list (search, Pinned, Recent), collapsible with « and » or ⌘\ (remembered per browser; the note widens). Centre: the
   open note, editable at once (NoteEditor), with its title, tags and flags in the header and "Saved" when the file is written
   (it saves by itself about two seconds after the last key, #119).
   Right: Mentioned in (notes that link here), Linked work (the items it mentions, live) and People. "+ New note" makes one from
   a template (Blank, Stakeholder, Lessons learned, Working session). Text only through JSX. */
import { useEffect, useState } from "preact/hooks";
import { P, pName } from "../../core/data.js";
import { fd, readDate, TODAY } from "../../core/page.js";
import { snack, viaServer } from "../../core/server.js";
import { shared } from "../../core/state.js";
import { addNoteImage, allNotes, closeNote, createNote, loadNotes, noteBodyFrom, noteCopyText, noteCur, noteDiscardAsk, noteDiscardCancel, noteDiscardNow,
  noteDiscarding, noteFind, noteFindP, noteFlush, noteImageSrc, noteLoading, noteHeld, noteMarks, noteMeta, noteRenamed, noteSave, notesCode, notesList,
  notesListOpen, notesMsg, notesQuery, noteTyped, openNote, toggleNotesList } from "../../stores/notes.js";
import { fuHover, fuPath } from "../../stores/findUpdates.js";
import { aiAction } from "../../stores/aiEdit.js";
import { FindUpdates } from "./FindUpdates.jsx";
import { askDeleteNote, DeleteNoteDialog } from "./DeleteNote.jsx";
import { Dialog } from "../Dialog.jsx";
import { Icon } from "../Icon.jsx";
import { Menu } from "../Menu.jsx";
import { NewTile } from "../work/NewTile.jsx";
import { NoteDate, NoteTags } from "./NoteHeader.jsx";
import { ProjectTabs } from "../project/ProjectTabs.jsx";
import { itemOf, itemState, NoteEditor } from "./NoteEditor.jsx";

/** @typedef {import("../../stores/notes.js").NoteSummary} NoteSummary */
/** @typedef {{code: string, onGo: (view: string, arg?: string) => void, onOpenItem: (id: string) => void,
    onOpenFile: (path: string) => void, onAddressChange: () => void}} NotesPageProps */

export const TEMPLATES = [["blank", "Blank", "An empty note"], ["stakeholder", "Stakeholder", "Role, what matters to them, how they work"],
  ["lessons-learned", "Lessons learned", "What happened, what to change"], ["working-session", "Working session", "A conversation: its date and who it was with"]];

/** "Today, 09:42", "11-10-2026" for a note in the list. @param {NoteSummary} n */
function when(n) {
  const m = String(n.mod || ""), d = m.slice(0, 10) || n.updated;
  return d === TODAY ? `Today, ${m.slice(11, 16)}` : fd(d);
}
/** Every note title in this project first, then the rest. @param {string} code */
function titlesFor(code) {
  const all = allNotes(), mine = (all[code] || []).map(n => n.title), rest = Object.entries(all).filter(([c]) => c !== code).flatMap(([, L]) => (L || []).map(n => n.title));
  return [...new Set([...mine, ...rest])];
}
/** The note with this title (this project first). @param {string} code @param {string} title @returns {NoteSummary | null} */
export function noteByTitle(code, title) {
  const t = title.trim().toLowerCase(), all = allNotes();
  const pick = /** @param {NoteSummary[]} L */ L => (L || []).find(n => n.title.toLowerCase() === t || n.file.replace(/\.md$/i, "").toLowerCase() === t);
  return pick(all[code]) || Object.values(all).map(pick).find(Boolean) || null;
}

/** The list. @param {{code: string, onOpen: (path: string) => void}} props */
function NotesList({ code, onOpen }) {
  const open = notesListOpen.value, q = notesQuery.value.trim().toLowerCase(), cur = noteCur.value;
  const L = notesList.value.filter(n => !q || n.title.toLowerCase().includes(q) || n.tags.some(t => t.toLowerCase().includes(q)));
  const pinned = L.filter(n => n.pinned), recent = L.filter(n => !n.pinned);
  const row = /** @param {NoteSummary} n */ n => (
    <li key={n.path}>
      <button type="button" class={`ni${cur && cur.path === n.path ? " on" : ""}`} aria-current={cur && cur.path === n.path ? "page" : undefined} onClick={() => onOpen(n.path)}>
        <b>{n.pinned ? <span class="pin" aria-hidden="true">◆ </span> : null}{n.title}</b>
        <small>{when(n)}{n.kind ? ` · ${n.kind}` : ""}{n.confidential ? <span class="conf"> · Confidential</span> : null}</small>
      </button>
    </li>);
  const label = open ? "Hide the notes list" : "Show the notes list";
  return (
    <aside class="nlist" aria-label="Notes">
      <div class="lhead">
        <b id="notesListH">Notes</b><span class="sp" />
        <button type="button" class="ib sm col" id="notesCollapse" aria-expanded={open ? "true" : "false"} aria-controls="notesListBody"
          aria-label={label} data-tip={`${label} (⌘\\)`} onClick={() => toggleNotesList()}><Icon name={open ? "chevsleft" : "chevsright"} /></button>
        <span class="vlabel" aria-hidden="true">{notesList.value.length} notes</span>
      </div>
      <div id="notesListBody" hidden={!open}>
        <input class="search nsearch" type="search" placeholder={`Search ${code === "_portfolio" ? "portfolio" : pName(code)} notes`} aria-label="Search notes"
          value={notesQuery.value} onInput={e => { notesQuery.value = /** @type {HTMLInputElement} */ (e.target).value; }} />
        {!L.length ? <p class="sub nnone">{notesList.value.length ? "No note matches." : "No notes yet."}</p> : null}
        {pinned.length ? <><div class="grp" id="ngPinned">Pinned</div><ul class="nul" aria-labelledby="ngPinned">{pinned.map(row)}</ul></> : null}
        {recent.length ? <><div class="grp" id="ngRecent">Recent</div><ul class="nul" aria-labelledby="ngRecent">{recent.map(row)}</ul></> : null}
      </div>
    </aside>);
}

/** The right column: Mentioned in, Linked work, People. @param {{code: string, onOpen: (path: string) => void, onOpenItem: (id: string) => void}} props */
function NoteContext({ code, onOpen, onOpenItem }) {
  const cur = noteCur.value;
  if (!cur) return <aside class="nctx" aria-label="About this note" />;
  const n = cur.note, t = n.title.toLowerCase(), stem = n.file.replace(/\.md$/i, "").toLowerCase();
  const back = Object.entries(allNotes()).flatMap(([c, L]) => (L || []).filter(x => x.path !== n.path && (x.links || []).some(l => [t, stem].includes(l.toLowerCase()))).map(x => ({ c, x })));
  const people = [...new Set([...(n.with || []), ...(n.people || [])])];
  const reg = /** @type {any[]} */ (shared.REG || []);
  return (
    <aside class="nctx" aria-label="About this note">
      <section class="box" aria-labelledby="nxMent"><h2 id="nxMent">Mentioned in</h2>
        {back.length ? <ul>{back.map(({ c, x }) => <li key={x.path}><button type="button" class="linkbtn" onClick={() => onOpen(x.path)}>{x.title}</button>{c !== code ? <small> · {c === "_portfolio" ? "Portfolio" : pName(c)}</small> : null}</li>)}</ul>
          : <p class="sub">No other note links here yet.</p>}
      </section>
      <section class="box" aria-labelledby="nxWork"><h2 id="nxWork">Linked work</h2>
        {(n.items || []).length ? <ul>{n.items.map(id => { const s = itemState(id), hit = itemOf(id); return (
          <li key={id}>{hit ? <button type="button" class={`nchip ${s.tone}`} aria-label={s.title} data-tip={s.title} onClick={() => onOpenItem(id)}>{id}</button>
            : <span class={`nchip ${s.tone}`}>{id}</span>} <small>{s.words}</small></li>); })}</ul>
          : <p class="sub">No work items mentioned. Type # to link one.</p>}
      </section>
      <section class="box" aria-labelledby="nxPeople"><h2 id="nxPeople">People</h2>
        {people.length ? <ul>{people.map(p => { const r = reg.find(x => x && x.name === p); return <li key={p}>{p}{r && r.role ? <small> · {r.role}</small> : null}</li>; })}</ul>
          : <p class="sub">Nobody mentioned. Type @ to mention someone.</p>}
      </section>
    </aside>);
}

/** BL-301 E: open (or close) Find updates beside the note. The note is written first, so Claude reads what is on screen.
    `p` (BL-301 D's AI › Make this an action…) looks at that one line only. @param {boolean} [open] @param {number} [p] */
export async function toggleFind(open = !noteFind.value, p = 0) {
  if (!open) { noteFind.value = false; noteFindP.value = 0; return; }
  if (!noteCur.value) return;
  await noteFlush();
  noteFindP.value = p || 0;
  noteFind.value = true;
}
/** The note's line (`data-p`, drawn by the editor) a selection starts in, or 0. @param {any} h @param {number} from */
function lineAt(h, from) {
  try {
    const v = h.editor.view, at = v.domAtPos(Math.min(from + 1, v.state.doc.content.size));
    const n = /** @type {any} */ (at.node), el = n && n.nodeType === 1 ? n : n && n.parentElement;
    const b = el && el.closest ? el.closest("[data-p]") : null;
    return b && h.el.contains(b) ? +(b.getAttribute("data-p") || 0) : 0;
  } catch (e) { return 0; }
}
/** The one line a selection is on, or 0 when it is on none (a picture, a table) or spans more than one. @param {any} h
    @param {{from: number, to: number}} range */
export function selectedLine(h, range) {
  const a = lineAt(h, range.from), b = lineAt(h, Math.max(range.from, range.to - 1));
  return a && a === b ? a : 0;
}
/* BL-301 D × E: AI › "Make this an action, a risk, a decision or an update" on a note's selection opens Find updates on its line
   only (never the whole note: a selection on no line, or on more than one, says so and runs nothing) */
aiAction({ id: "fu-line", name: "Make this an action, a risk, a decision or an update", line: "Find updates on this line only",
  icon: "check", places: ["notes"], run: (range, h) => {
    const p = selectedLine(h, range);
    if (!p) { snack("Select text on one line of the note: Find updates looks at that line only"); return; }
    toggleFind(true, p);
  } });
/** ✦ Find updates, in the note's header (the slot part B left for it). */
function FindButton() {
  const on = noteFind.value;
  return <button type="button" class={`btn sm${on ? " on" : ""}`} id="noteFind" aria-expanded={on ? "true" : "false"} aria-controls="noteSide"
    disabled={!viaServer()} data-tip={viaServer() ? "Find the tracker changes this note's new lines state" : "Find updates needs the live server"}
    onClick={() => toggleFind()}><span aria-hidden="true">✦ </span>Find updates</button>;
}
/** The right-hand column: the note's context, or Find updates while it is open. @param {{code: string, onOpen: (path: string) => void, onOpenItem: (id: string) => void}} props */
function NoteSide({ code, onOpen, onOpenItem }) {
  const cur = noteCur.value;
  if (!(noteFind.value && cur)) return <div class="nside" id="noteSide"><NoteContext code={code} onOpen={onOpen} onOpenItem={onOpenItem} /></div>;
  const close = () => {
    fuPath.value = ""; noteMarks.value = { markers: {}, hover: 0 }; noteFind.value = false; noteFindP.value = 0;
    const b = /** @type {HTMLElement|null} */ (document.getElementById("noteFind")); if (b) b.focus();
  };
  return <div class="nside" id="noteSide"><FindUpdates key={`${cur.path}|${noteFindP.value}`} path={cur.path} p={noteFindP.value || undefined} onClose={close}
    onMarks={(markers, hover) => { noteMarks.value = { markers, hover }; }} /></div>;
}

/** The save state, as the header says it (#119): "Saved 14:02" once the file is written, "Editing" from the first key, "Saving…"
    while it goes, "Not saved" when it couldn't be, and a short word for a file that changed outside creaite. The reason is in the
    banner below. */
function SaveLine() {
  const s = noteSave.value;
  const text = s.state === "saved" ? `Saved${s.at ? ` ${s.at}` : ""}` : s.state === "saving" ? "Saving…" : s.state === "typing" ? "Editing" :
    s.state === "conflict" ? "Changed outside creaite" : s.state === "wait" || s.state === "error" ? "Not saved" : "";
  return <span class={`nsave ${s.state}`} id="noteSave" data-save={s.state || undefined} role="status" aria-live="polite">{text}</span>;
}

/** Typing that could not be saved (the file changed outside creaite, an error, a wait): nothing keeps it but the page, so the note
    stays open, the reason is said, and the text can be copied. Discarding it asks first. @param {{conflict: boolean}} props */
function UnsavedBanner({ conflict }) {
  const st = noteSave.value;
  return (
    <div class="nstale" role="alert" data-nbanner={st.state}><span>{st.msg}</span>
      {noteDiscarding.value ? <>
        <span data-ndiscardq>{conflict ? "Show the file's version?" : "Discard what you typed?"} What you typed here goes, unless you copied it.</span>
        <button type="button" class="btn sm" data-ndiscardno onClick={noteDiscardCancel}>Keep editing</button>
        <button type="button" class="btn sm primary" data-ndiscardyes onClick={() => { noteDiscardNow(); }}>{conflict ? "Open the file's version" : "Discard my typing"}</button>
      </> : <>
        <button type="button" class="btn sm" data-ncopy onClick={() => { noteCopyText().then(ok => snack(ok ? "Your text is copied" : "It couldn't be copied: select it in the note instead")); }}>Copy my text</button>
        <button type="button" class="btn sm" data-ndiscard onClick={noteDiscardAsk}>{conflict ? "Open the file's version" : "Discard my typing"}</button>
      </>}
    </div>);
}

/** The open note: header, body, the unsaved-typing banner. @param {{code: string, onOpen: (path: string) => void,
    onOpenItem: (id: string) => void, onNew: (title: string) => void, onOpenFile: (path: string) => void}} props */
function NoteDoc({ code, onOpen, onOpenItem, onNew, onOpenFile }) {
  const cur = noteCur.value;
  if (!cur) return (
    <article class="ndoc empty">
      {noteLoading.value ? <p class="sub">Opening…</p> : <>
        <h2>{notesList.value.length ? "Pick a note on the left, or start a new one" : "No notes yet"}</h2>
        <p class="sub">Notes are your own working thinking: stakeholders, positions, lessons, a conversation. They stay internal and are never extracted on their own.</p>
      </>}
    </article>);
  const m = cur.meta || {}, n = cur.note, tags = /** @type {string[]} */ (m.tags || []);
  const conf = !!m.confidential, pinned = !!m.pinned;
  const created = String(m.created || n.created || "");
  return (
    <article class="ndoc" aria-labelledby="noteTitle">
      <div class="nhead">
        <div class="trow">
          <input class="ntitle" id="noteTitle" aria-label="Title" value={String(m.title ?? n.title)} maxLength={160}
            onInput={e => noteMeta({ title: /** @type {HTMLInputElement} */ (e.target).value })} onBlur={() => { noteFlush(); }} />
          <SaveLine />
          <span class="nslot" id="noteFindSlot" data-slot="find-updates"><FindButton /></span>
          <Menu label="More" btnCls="ib sm bd nmore" menuLabel="Note" left={false} cls="nmorewrap"
            items={[{ id: "pin", name: pinned ? "Unpin" : "Pin", line: pinned ? "Take it off the top of the list" : "Keep it at the top of the list", icon: "flag" },
              { id: "conf", name: conf ? "Not confidential" : "Mark confidential", line: conf ? "Prep pages and Claude may read it again" : "Kept out of Prep pages; asks before its text goes to Claude", icon: "shield" },
              { id: "file", name: "Show the file", line: n.path, icon: "folder" },
              { id: "sep", sep: true }, { id: "del", name: "Delete note…", line: "Moves it to the archive; restore it from Files", icon: "trash", cls: "bad" }]}
            onPick={id => { if (id === "pin") noteMeta({ pinned: !pinned }, true); else if (id === "conf") noteMeta({ confidential: !conf }, true); else if (id === "del") askDeleteNote(); else onOpenFile(n.path); }} />
        </div>
        <div class="meta props">
          {created ? <span>Created {fd(created)}</span> : null}
          {m.date || n.kind === "Working session" ? <WorkingSession key={`ws|${cur.load}`} date={String(m.date || "")} people={/** @type {string[]} */ (m.with || [])} /> : null}
        </div>
        <NoteTags tags={tags} />
      </div>
      {["conflict", "error", "wait"].includes(noteSave.value.state) ? <UnsavedBanner conflict={noteSave.value.state === "conflict"} /> : null}
      {noteHeld.value === cur.path ? (
        <div class="nstale nheld" role="status"><span>Waiting on the approval card in ask creaite to move this note to the archive. It can't be changed until you answer the card.</span></div>) : null}
      <NoteEditor key={`n${cur.load}`} readOnly={noteHeld.value === cur.path} loadKey={`n${cur.load}`} markdown={cur.body} code={code} label={`${n.title}, the note`}
        noteTitles={() => titlesFor(code)} onInput={noteTyped} onBody={noteBodyFrom} path={cur.path} imageSrc={noteImageSrc} onImage={addNoteImage}
        onHoverLine={l => { if (noteFind.value && fuHover.value !== l) fuHover.value = l; }}
        onOpenItem={onOpenItem} onOpenNote={t => { const hit = noteByTitle(code, t); if (hit) onOpen(hit.path); else onNew(t); }} />
    </article>);
}

/** BL-301 B gaps: a Working session's date and who it was with, editable in the note's header after it is made. The date is typed or
    picked (NoteDate); both are saved like the title: a change ends with Enter or leaving the field.
    @param {{date: string, people: string[]}} props */
function WorkingSession({ date, people }) {
  return (
    <>
      <span class="nprop"><span class="nk">Date</span><NoteDate date={date} /></span>
      <span class="nprop"><span class="nk">With</span>
        <input type="text" id="noteWsWith" class="nin who" defaultValue={people.join(", ")} placeholder="Names, separated by commas" aria-label="With, names separated by commas"
          onChange={e => noteMeta({ with: /** @type {HTMLInputElement} */ (e.target).value.split(",").map(x => x.trim()).filter(Boolean) })} /></span>
    </>);
}

/** "+ New note": a template, a title, and for a Working session its date and who it was with.
    @param {{code: string, open: boolean, title: string, onClose: () => void, onMade: () => void}} props */
function NewNote({ code, open, title, onClose, onMade }) {
  const [tpl, setTpl] = useState("blank"), [t, setT] = useState(title), [day, setDay] = useState(fd(TODAY)), [who, setWho] = useState(""), [busy, setBusy] = useState(false);
  useEffect(() => { if (open) { setT(title); setDay(fd(TODAY)); setWho(""); setBusy(false); } }, [open, title]);
  const bad = tpl === "working-session" && day.trim() && !readDate(day);
  const make = async () => {
    if (busy || bad) return;
    setBusy(true);
    const made = await createNote(code, { template: tpl, title: t.trim(), ...(tpl === "working-session" ? { date: readDate(day) || TODAY, with: who.split(",").map(x => x.trim()).filter(Boolean) } : {}) });
    setBusy(false);
    if (made) onMade();
  };
  return (
    <Dialog open={open} onClose={onClose} labelledBy="nnH" id="newNoteDlg" focus="#nnTitle" dirty={!!t.trim()}>
      <form method="dialog" class="nnew" onSubmit={e => { e.preventDefault(); make(); }}>
        <h2 id="nnH">New note{code === "_portfolio" ? " · Portfolio" : ` · ${pName(code)}`}</h2>
        <label class="fl">Title<input id="nnTitle" type="text" value={t} maxLength={160} placeholder="What is it about?" onInput={e => setT(/** @type {HTMLInputElement} */ (e.target).value)} /></label>
        <fieldset class="nntpl"><legend>Template</legend>
          {TEMPLATES.map(([id, name, line]) => (
            <label key={id} class={`nntopt${tpl === id ? " on" : ""}`}><input type="radio" name="nntpl" value={id} checked={tpl === id} onChange={() => setTpl(id)} />
              <span><b>{name}</b><small>{line}</small></span></label>))}
        </fieldset>
        {tpl === "working-session" ? <div class="nnws">
          <label class="fl">Date<input type="text" value={day} placeholder="DD-MM-YYYY, or e.g. last monday" aria-invalid={bad ? "true" : undefined} onInput={e => setDay(/** @type {HTMLInputElement} */ (e.target).value)} /></label>
          <label class="fl">With<input type="text" value={who} placeholder="Names, separated by commas" onInput={e => setWho(/** @type {HTMLInputElement} */ (e.target).value)} /></label>
        </div> : null}
        <p class="sub">Saved in the project's notes folder, named by its title. Internal: never in a client report.</p>
        <div class="nnfoot"><button type="button" class="btn" onClick={onClose}>Cancel</button>
          <button type="submit" class="btn primary" id="nnMake" disabled={busy || !!bad || !viaServer()}>{busy ? "Making…" : "Make the note"}</button></div>
      </form>
    </Dialog>);
}

/** The Notes tab. @param {NotesPageProps} props */
export function NotesPage({ code, onGo, onOpenItem, onOpenFile, onAddressChange }) {
  const [dlg, setDlg] = useState(/** @type {string|null} */ (null));
  const name = code === "_portfolio" ? "Portfolio" : pName(code), proj = P.find(x => x.code === code);
  const openPath = /** @param {string} p */ async p => { if (await openNote(p)) onAddressChange(); };
  const renamed = noteRenamed.value;
  useEffect(() => { if (renamed) onAddressChange(); }, [renamed]);          /* BL-301 B gaps: the address names the renamed file */
  return (
    <div class="wrapmax notespage">
      <nav class="crumb" aria-label="Breadcrumb">
        {code === "_portfolio" ? <><a href="#" data-go="today">Today</a><span aria-hidden="true">›</span><span>Portfolio</span></>
          : <><a href="#" data-go="projects">Projects</a><span aria-hidden="true">›</span><a href="#" data-proj={code}>{name}</a></>}
        <span aria-hidden="true">›</span><span aria-current="page">Notes</span>
      </nav>
      <div class="hhead nhh">
        <div style={{ flex: 1 }}><h1>{code === "_portfolio" ? "Portfolio notes" : name}</h1>
          {code === "_portfolio" ? <div class="sub">Notes that cover several projects, and anything not yet filed under one.</div> : proj && proj.client ? <div class="sub">{proj.client}</div> : null}</div>
        <NewTile id="notesNew" popup="dialog" word="New note" decisions={false} hidden={false} onNew={() => setDlg("")} onDecision={() => {}} />
      </div>
      {code !== "_portfolio" ? <ProjectTabs code={code} selected="notes" count={notesList.value.length} onGo={id => { if (id === "overview") onGo("cockpit", code); }} /> : null}
      {notesMsg.value ? <div class="nmsg" role="status">{notesMsg.value}</div> : null}
      {!viaServer() ? <div class="nmsg" role="status">Notes open and save through the live server. Start it to edit; the list is as of the last build.</div> : null}
      <div class={`nsplit${notesListOpen.value ? "" : " collapsed"}${noteFind.value && noteCur.value ? " finding" : ""}`} id="notesSplit">
        <NotesList code={code} onOpen={openPath} />
        <NoteDoc code={code} onOpen={openPath} onOpenItem={onOpenItem} onNew={t => setDlg(t)} onOpenFile={onOpenFile} />
        <NoteSide code={code} onOpen={openPath} onOpenItem={onOpenItem} />
      </div>
      <DeleteNoteDialog />
      <NewNote code={code} open={dlg !== null} title={dlg || ""} onClose={() => setDlg(null)} onMade={() => { setDlg(null); onAddressChange(); }} />
    </div>);
}

export { closeNote, loadNotes, notesCode };
