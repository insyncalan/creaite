// @ts-check
/* SneakPeek (BL-322, dev/COMPONENTS.md): change the item open in the peek in words, as drawn in dev/mockups/sneak-peek-mockup.html.
   A small box floats over the bottom of the work-item peek (#panel) or the milestone editor (#mvPeek); the item stays in view.
   The server reads the words (POST /api/sneak/read: plain code, no model call, nothing written; dev/sprints/BL-322-contract.md)
   on every pause in typing and on Enter. The box shows what it understood, marked in the words (a click takes a stretch back out),
   the change card (from → to), a pick list for a name that matches two people, problems, a refusal with where to go instead, a
   quick fact, or a task. Enter makes a plain change through the peek's own save path (panel.js sneakCommit: one dashboard
   proposal with the peek's envelope, applied at once, Undo straight after). The confirm list (amber) takes ⌘⏎ or a click; plain
   Enter never makes it. Closing or cancelling an action offers a closing update. Claude's parts go through /api/draft (Yours
   beside Claude's, Use this or Keep mine); with AI drafts off the card says why and the plain-code part still works.
   Nothing is sent from here, and nobody is labelled a VIP (BL-288). */
import { render } from "preact";
import { useEffect, useRef, useState } from "preact/hooks";
import { MOD } from "../../core/page.js";
import { api, viaServer } from "../../core/server.js";
import { draftAsk, draftStat, draftWhyNot } from "../../drafts.js";

/** @typedef {[string, Record<string, string>][]} SneakShapes  an icon as element data (COMPONENTS.md Q2): [tag, attributes] */

/** The Sneak peek sparkle: a large four-point star and a small one (the mockup's). @type {SneakShapes} */
export const SNEAK_ICON = [["path", { d: "M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8z" }],
  ["path", { d: "M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z" }]];
const SP_DEBOUNCE = 160;          // ms after the last key before the words are read again
/** The last instructions, newest first: ↑ in the empty box brings the latest back (for the next item too). @type {string[]} */
export const SNEAK_HIST = [];
/** ⌘⏎ inside the box: the page's ⌘⏎ handler (core/fields.js CMDENTER) calls the open box's own. @type {{fn: null|(() => void)}} */
export const SNEAK_CMD = { fn: null };

/** @typedef {{id: string, kind: string, table: string, project: string, title: string, type: string|null, updated_at: string}} SneakItem */
/** @typedef {{start: number, end: number, what: string}} SneakMark */
/** @typedef {{field: string, label: string, from: any, to: any, from_shown: string, to_shown: string, confirm?: boolean,
    derived?: boolean}} SneakChange */
/** @typedef {{label: string, items: Record<string, any>[]}} SneakStage */
/** @typedef {{kind: string, why: string, off: boolean, optional?: boolean, request: Record<string, any>|null}} SneakClaude */
/** @typedef {{field: string, typed: string, options: {value: string, label: string}[]}} SneakChoices */
/** @typedef {{why: string, point_to: string, where?: string}} SneakRefused  where: the place in words */
/** @typedef {{kind: string, [k: string]: any}} SneakTask */
/** @typedef {{ok: boolean, message?: string, busy?: boolean, item: SneakItem, by: string, understood: SneakMark[], changes: SneakChange[],
    task: SneakTask|null, stage: SneakStage|null, confirm: false|{why: string}, needs_claude: false|SneakClaude,
    choices: SneakChoices|null, problems: string[], refused: SneakRefused|null, offer_closing_update: boolean}} SneakReply */
/** @typedef {{ok: boolean, message?: string, applyId?: any}} SneakResult  what a commit or an undo comes back with */
/** @typedef {{commit: (stage: SneakStage, item: SneakItem, o: {by: string, said: string}) => Promise<SneakResult>,
    undo: (applyId: any) => Promise<SneakResult>, chase: (pane: Record<string, any>) => void, go: (task: SneakTask, item: SneakItem) => void,
    point: (to: string, text: string) => void, ask: (text: string) => void, current: (field: string) => string,
    people: () => SneakPerson[]}} SneakActs */
/** @typedef {{name: string, org: string, aliases: string[]}} SneakPerson */
/** @typedef {{start: number, end: number, list: SneakPerson[], i: number}} SneakMention  the @ being typed, its matches and the active one */
/** @typedef {{field: string, kind: string, feature: string, was: string, d: {text?: string, [k: string]: any}|null, status: string,
    item: SneakItem}} SneakDraft */
/** @typedef {{id: string, onClose: (back: boolean) => void, acts: SneakActs}} SneakProps */

/** An icon from element data, drawn as ic() draws one. @param {{shapes: SneakShapes, size?: number}} props */
export function SneakIcon({ shapes, size }) {
  return (
    <svg class="i" viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" stroke-width="1.8"
      stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      {shapes.map(([tag, a]) => <path {...a} key={tag + a.d} />)}
    </svg>
  );
}

/** Where a refusal points, as the button's words (null: said in words only). @type {Record<string, string|null>} */
const POINT = { draft_chase: "Open Draft email", ask: "Open ask creaite", project_page: "Open the project page", settings: "Open Settings",
  people: "Open People", milestone_form: null, cx_edit: null };
/** A refusal's second sentence, where it points. @type {Record<string, string>} */
const POINT_SAY = { cx_edit: "Say it in Claude Code (cx-edit) instead.", milestone_form: "Use Rebaseline… in the milestone's Dates: a rebaseline also records a decision." };
/** The confirm button's verb for an ending status. @type {Record<string, string>} */
const END_WORD = { Cancelled: "Cancel", Withdrawn: "Withdraw", Dropped: "Drop" };
/** The draft kinds' fields and their words. @type {Record<string, (r: Record<string, any>) => {field: string, word: string}>} */
const DRAFTS = {
  client: () => ({ field: "client_message", word: "Client message" }),
  thinking: r => r.field === "options" ? { field: "options", word: "Options" } : { field: "reasoning", word: "Reasoning" },
  "sneak-update": () => ({ field: "latest_update", word: "Latest update" }),
};

const AT_MAX = 6;            // people shown in the @ list
/** The @ being typed just before the caret, if any: where it starts and the words after it.
    @param {string} t @param {number} caret @returns {{start: number, q: string}|null} */
export function atQuery(t, caret) {
  const m = /(?:^|[\s,;(])@([^\s@,;]*(?: [^\s@,;]*)?)$/.exec(t.slice(0, caret));
  return m ? { start: caret - m[1].length - 1, q: m[1] } : null;
}
/** The people a query matches: a name or an alias that starts with it, or a word of the name that does; the full name first.
    @param {SneakPerson[]} all @param {string} q @returns {SneakPerson[]} */
export function atMatches(all, q) {
  const w = q.trim().toLowerCase();
  if (!w) return all.slice(0, AT_MAX);
  const rank = (/** @type {SneakPerson} */ p) => { const n = p.name.toLowerCase();
    return n.startsWith(w) ? 0 : n.split(/\s+/).some(x => x.startsWith(w)) ? 1 : p.aliases.some(a => a.toLowerCase().startsWith(w)) ? 2 : 9; };
  return all.map(p => ({ r: rank(p), p })).filter(x => x.r < 9).sort((a, b) => a.r - b.r).map(x => x.p).slice(0, AT_MAX);
}

/** The words with what was understood marked; a click on a mark takes that stretch back out.
    @param {{text: string, marks: SneakMark[], onTake: (m: SneakMark) => void}} props */
function Understood({ text, marks, onTake }) {
  const L = [...marks].filter(m => m.end > m.start && m.end <= text.length).sort((a, b) => a.start - b.start), out = [];
  let at = 0;
  for (const m of L) {
    if (m.start < at) continue;
    if (m.start > at) out.push(<span key={"t" + at}>{text.slice(at, m.start)}</span>);
    const w = text.slice(m.start, m.end);
    out.push(<button type="button" class="sp-mark" key={"m" + m.start} data-tip={`${m.what}. Click to take it out`}
      aria-label={`“${w}”, understood as ${m.what}. Take it out`} onClick={() => onTake(m)}>{w}</button>);
    at = m.end;
  }
  if (at < text.length) out.push(<span key={"t" + at}>{text.slice(at)}</span>);
  return <div class="sp-said" role="group" aria-label="What was understood">{out}</div>;
}

/** The box. @param {SneakProps} props */
export function SneakPeek({ id, onClose, acts }) {
  const [text, setText] = useState("");
  const [reply, setReply] = useState(/** @type {SneakReply|null} */ (null));
  const [picks, setPicks] = useState(/** @type {Record<string, string>} */ ({}));
  const [shown, setShown] = useState(false);            // a full answer (after Enter): "couldn't match" is said then, not while typing
  const [done, setDone] = useState(/** @type {{text: string, ok: boolean, applyId?: any}|null} */ (null));
  const [busy, setBusy] = useState(false);
  const [closing, setClosing] = useState("");
  const [draft, setDraft] = useState(/** @type {SneakDraft|null} */ (null));
  const [flash, setFlash] = useState(false);
  const [at, setAt] = useState(/** @type {SneakMention|null} */ (null));
  const input = useRef(/** @type {HTMLInputElement|null} */ (null)), seq = useRef(0), timer = useRef(0);
  const draftRef = useRef(/** @type {SneakDraft|null} */ (null));
  draftRef.current = draft;

  useEffect(() => { if (input.current) input.current.focus(); }, []);
  useEffect(() => () => { SNEAK_CMD.fn = null; clearTimeout(timer.current); const d = draftRef.current; if (d && d.d) draftStat(d.feature, "rejected"); }, []);

  /** Read the words now; the reply is kept only if nothing newer has been asked.
      @param {string} t @param {Record<string, string>} [pk] @returns {Promise<SneakReply|null>} */
  async function read(t, pk) {
    const n = ++seq.current;
    if (!t.trim()) { setReply(null); return null; }
    if (!viaServer()) { const r = /** @type {any} */ ({ ok: false, message: "Sneak peek needs the live server: start it, then try again." }); setReply(r); return r; }
    const body = { id, text: t, ...(pk && Object.keys(pk).length ? { picks: pk } : {}) };
    let r = /** @type {SneakReply} */ (await api("/api/sneak/read", body));
    for (let i = 0; i < 4 && r && r.busy && n === seq.current; i++) {      // an apply holds the tracker: ask again shortly
      await new Promise(res => setTimeout(res, 300)); r = /** @type {SneakReply} */ (await api("/api/sneak/read", body)); }
    if (n !== seq.current) return null;
    setReply(r); return r;
  }
  /** @param {string} t @param {number} [at0] where the caret is (a pick puts it after the name) */
  function typed(t, at0) {
    const el = input.current, caret = at0 != null ? at0 : el && document.activeElement === el && el.selectionStart != null ? el.selectionStart : t.length;
    const a = atQuery(t, caret), list = a ? atMatches(acts.people(), a.q) : [];
    setAt(a && (list.length || !a.q.includes(" ")) ? { start: a.start, end: caret, list, i: 0 } : null);
    if (a && (list.length || !a.q.includes(" "))) { setText(t); setDone(null); clearTimeout(timer.current); return; }   // read once a name is chosen
    setText(t); setDone(null); setShown(false); setFlash(false); clearTimeout(timer.current);
    if (draftRef.current && !draftRef.current.status) { if (draftRef.current.d) draftStat(draftRef.current.feature, "rejected"); setDraft(null); }
    if (t.trim().length < 2) { seq.current++; setReply(null); return; }
    timer.current = /** @type {any} */ (setTimeout(() => read(t, picks), SP_DEBOUNCE));
  }
  /** Read again with the same words (a pick, a mark taken out). @param {string} t @param {Record<string, string>} pk */
  function again(t, pk) { setText(t); setPicks(pk); setDone(null); setShown(true); clearTimeout(timer.current); read(t, pk); input.current?.focus(); }

  /** Make the staged change. @param {SneakReply} r @param {string} [note] a closing update */
  async function make(r, note) {
    if (busy) return;
    let rr = r;
    if (note && note.trim()) {        // the closing update goes in the same text, read again (contract § 1, offer_closing_update)
      const t2 = `${text.trim().replace(/[.,;]+$/, "")}, add an update: ${note.trim()}`;
      const n = await read(t2, picks); if (!n || !n.stage) { setShown(true); return; }
      rr = n;
    }
    if (!rr.stage) return;
    remember(text);
    setBusy(true);
    const res = await acts.commit(rr.stage, rr.item, { by: rr.by, said: said(rr) });
    setBusy(false);
    if (!res.ok) { setDone({ text: res.message || "Not changed.", ok: false }); return; }
    seq.current++; setText(""); setReply(null); setClosing(""); setPicks({}); setShown(false);
    setDone({ text: said(rr), ok: true, applyId: res.applyId }); input.current?.focus();
  }
  async function undo() {
    if (!done || done.applyId == null) return;
    setBusy(true); const res = await acts.undo(done.applyId); setBusy(false);
    setDone({ text: res.ok ? `Undone. ${id} is back as it was.` : (res.message || "Couldn't undo it: undo it in Activity."), ok: !!res.ok });
    input.current?.focus();
  }
  /** Start Claude's draft. @param {SneakClaude} c @param {SneakItem} item */
  async function claude(c, item) {
    if (c.off || !c.request) return;
    const why = draftWhyNot(c.kind); if (why) { setDone({ text: why, ok: false }); return; }
    const f = (DRAFTS[c.kind] || DRAFTS.client)(c.request), feature = c.kind === "sneak-update" ? "update" : c.kind;
    remember(text);
    /** @type {SneakDraft} */
    const mine = { field: f.field, kind: c.kind, feature, was: acts.current(f.field), d: null, status: "Drafting with Claude…", item };
    setDraft(mine); input.current?.focus();
    const res = await draftAsk(c.request, { label: `Drafting the ${f.word.toLowerCase()}` });
    if (draftRef.current !== mine) { if (res.ok && !res.nothing) draftStat(feature, "rejected"); return; }
    if (res.nothing || !res.ok || !res.text) { setDraft(null); setDone({ text: res.nothing || res.message || "No draft came back.", ok: false }); return; }
    setDraft({ ...mine, d: res, status: "" }); input.current?.focus();          // Enter is Use this
  }
  async function useDraft() {
    const d = draftRef.current; if (!d || !d.d || busy) return;
    const it = d.item, text2 = String(d.d.text || "").trim();
    /** @type {SneakStage} */
    const stage = { label: `${it.id} ${DRAFTS[d.kind] ? (DRAFTS[d.kind](d.kind === "thinking" ? { field: d.field } : {})).word.toLowerCase() : d.field} drafted (Sneak peek)`,
      items: [{ op: "update", table: it.table, id: it.id, changes: { [d.field]: text2 }, ...(it.updated_at ? { based_on: it.updated_at } : {}) }] };
    setBusy(true);
    const res = await acts.commit(stage, it, { by: "claude", said: stage.label });
    setBusy(false);
    if (!res.ok) { setDone({ text: res.message || "Not changed.", ok: false }); return; }
    draftStat(d.feature, "used"); setDraft(null); seq.current++; setText(""); setReply(null);
    const word = (DRAFTS[d.kind] ? DRAFTS[d.kind]({ field: d.field }).word : d.field);
    setDone({ text: `${word} replaced with Claude's draft.`, ok: true, applyId: res.applyId }); input.current?.focus();
  }
  function keepMine() { const d = draftRef.current; if (d && d.d) draftStat(d.feature, "rejected"); setDraft(null); setDone({ text: "Kept yours.", ok: true }); input.current?.focus(); }

  /** @param {string} t */
  function remember(t) { t = t.trim(); if (!t) return; const i = SNEAK_HIST.indexOf(t); if (i >= 0) SNEAK_HIST.splice(i, 1); SNEAK_HIST.unshift(t); SNEAK_HIST.length = Math.min(SNEAK_HIST.length, 20); }

  /** Enter or ⌘⏎: do what the card offers. @param {boolean} cmd */
  async function enter(cmd) {
    clearTimeout(timer.current);
    if (draftRef.current) { if (draftRef.current.d) useDraft(); return; }
    const t = text.trim(); if (!t) return;
    const r = await read(t, picks); setShown(true);
    if (!r || !r.ok || r.refused || r.choices) return;
    const task = r.task;
    if (task && task.kind === "facts") { remember(t); return; }
    if (task && task.kind === "goto") { remember(t); acts.go(task, r.item); return; }
    if (task && task.kind === "chase") { remember(t); acts.chase(task.pane || {}); return; }
    if (r.stage) {
      if (r.confirm && !cmd) { setFlash(true); setTimeout(() => setFlash(false), 900); return; }
      make(r, closing); return;
    }
    if (r.needs_claude && !r.needs_claude.optional) claude(r.needs_claude, r.item);
  }
  /** Put the chosen person in place of the @ being typed. @param {SneakPerson} p */
  function pickPerson(p) {
    if (!at) return;
    const t = `${text.slice(0, at.start)}@${p.name} ${text.slice(at.end).replace(/^ /, "")}`, caret = at.start + p.name.length + 2;
    typed(t, caret); setAt(null);
    setTimeout(() => { const el = input.current; if (el) { el.focus(); el.setSelectionRange(caret, caret); } }, 0);
  }
  /** @param {KeyboardEvent} e */
  function onKey(e) {
    if (at && e.target === input.current) {          // the @ list: ↑ ↓ move, Enter or Tab picks, Esc closes the list only
      const n = at.list.length;
      if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); setAt(null); return; }
      if (n && (e.key === "ArrowDown" || e.key === "ArrowUp")) { e.preventDefault(); e.stopPropagation(); setAt({ ...at, i: (at.i + (e.key === "ArrowDown" ? 1 : n - 1)) % n }); return; }
      if (n && (e.key === "Enter" || e.key === "Tab") && !(e.metaKey || e.ctrlKey)) { e.preventDefault(); e.stopPropagation(); pickPerson(at.list[at.i]); return; }
    }
    if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); onClose(true); return; }
    const el = /** @type {HTMLElement} */ (e.target);
    if (el !== input.current) { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) { e.preventDefault(); e.stopPropagation(); enter(true); } return; }
    if (e.key === "Enter") { e.preventDefault(); e.stopPropagation(); enter(e.metaKey || e.ctrlKey); return; }
    if (e.key === "ArrowUp" && !text && SNEAK_HIST.length) { e.preventDefault(); typed(SNEAK_HIST[0]); }
  }

  SNEAK_CMD.fn = () => { enter(true); };
  const r = reply;
  /** @type {any[]} */
  const out = [];
  if (draft) out.push(<DraftCard key="draft" d={draft} busy={busy} onUse={useDraft} onKeep={keepMine} />);
  else if (r && text.trim()) {
    if (r.understood && r.understood.length && r.ok) out.push(<Understood key="said" text={text} marks={r.understood}
      onTake={m => { const t = (text.slice(0, m.start) + text.slice(m.end)).replace(/\s{2,}/g, " ").replace(/^[\s,;]+|[\s,;]+$/g, "").replace(/^(and|also)\s+/i, "").replace(/\s+(and|also)$/i, ""); again(t, picks); }} />);
    out.push(<Card key="card" r={r} id={id} shown={shown} busy={busy} flash={flash} closing={closing} setClosing={setClosing}
      onMake={() => make(r, closing)} onNot={() => { seq.current++; setReply(null); setText(""); setShown(false); input.current?.focus(); }}
      onPick={(typedWord, value) => again(text, { ...picks, [typedWord.toLowerCase()]: value })}
      onClaude={() => r.needs_claude && claude(r.needs_claude, r.item)} acts={acts} text={text} />);
  }
  if (done && !draft) out.push(<div key="done" class={`sp-done${done.ok ? "" : " fail"}`} role="status">
    {done.ok && done.applyId != null ? "✓ " : ""}{done.text}
    {done.ok && done.applyId != null ? <> <button type="button" id="spUndo" disabled={busy} onClick={undo}>Undo</button></> : null}</div>);

  return (
    <div class="sp-box" id="spBox" role="dialog" aria-label="Sneak peek: change this item in words" onKeyDown={onKey}>
      <div class="sp-out" id="spOut" aria-live="polite">{out}</div>
      <ul class="sp-people" id="spPeople" role="listbox" aria-label="People" hidden={!(at && at.list.length)}>
        {at ? at.list.map((p, i) => <li id={`spP${i}`} key={p.name} role="option" aria-selected={i === at.i ? "true" : "false"}
          class={i === at.i ? "on" : ""} onMouseDown={e => { e.preventDefault(); pickPerson(p); }}>
          <span class="nm">{p.name}</span>{p.org ? <span class="sub">{p.org}</span> : null}</li>) : null}
      </ul>
      {at && !at.list.length ? <div class="sp-nomatch sub" id="spNoMatch">No one in the people register matches “{at ? `@${text.slice(at.start + 1, at.end)}` : ""}”.</div> : null}
      <span class="vh" role="status">{at && at.list.length ? `${at.list.length} ${at.list.length === 1 ? "person" : "people"}: up and down to choose, Enter to pick` : ""}</span>
      <div class="sp-in">
        <SneakIcon shapes={SNEAK_ICON} />
        <label for="spIn" class="vh">Change {id} in words</label>
        <input id="spIn" ref={input} type="text" autocomplete="off" spellcheck={false} value={text} maxLength={1000}
          role="combobox" aria-autocomplete="list" aria-expanded={at && at.list.length ? "true" : "false"} aria-controls="spPeople"
          aria-activedescendant={at && at.list.length ? `spP${at.i}` : undefined}
          placeholder={`Change ${id}… e.g. due Friday, owner to @Sam`} onInput={e => typed(/** @type {HTMLInputElement} */ (e.currentTarget).value)}
          onBlur={() => setTimeout(() => { if (document.activeElement !== input.current) setAt(null); }, 0)} />
        <span class="esc" aria-hidden="true"><kbd>Esc</kbd> close</span>
      </div>
    </div>
  );
}

/** What a change says once it's made. @param {SneakReply} r */
function said(r) {
  const t = r.task;
  if (t && (t.kind === "action" || t.kind === "risk" || t.kind === "promise")) return `New ${t.kind} created, linked to ${r.item.id}.`;
  if (t && t.kind === "link") return `Linked ${t.from_item} and ${t.to_item}.`;
  const L = (r.changes || []).filter(c => !c.derived).map(c => c.label.toLowerCase());
  const uniq = [...new Set(L)];
  return uniq.length ? `Changed ${uniq.length > 1 ? uniq.slice(0, -1).join(", ") + " and " + uniq[uniq.length - 1] : uniq[0]}.` : (r.stage ? r.stage.label + "." : "Changed.");
}

/** Claude's version beside Alan's. @param {{d: SneakDraft, busy: boolean, onUse: () => void, onKeep: () => void}} props */
function DraftCard({ d, busy, onUse, onKeep }) {
  const word = (DRAFTS[d.kind] ? DRAFTS[d.kind]({ field: d.field }).word : d.field);
  if (!d.d) return (
    <div class="sp-card" role="status"><div class="sp-head"><SneakIcon shapes={SNEAK_ICON} size={15} /><b>{d.status}</b>
      <span class="by"><button type="button" class="btn sm" data-drstop>Stop</button></span></div></div>
  );
  return (
    <div class="sp-card" role="region" aria-label={`${word}, drafted`}>
      <div class="sp-head"><SneakIcon shapes={SNEAK_ICON} size={15} /><b>{word}, drafted</b><span class="by">Written by Claude (AI drafts)</span></div>
      <div class="sp-cmp">
        <div><span class="lab">Yours</span><span class="sp-txt">{d.was.trim() ? d.was : "Empty"}</span></div>
        <div class="new"><span class="lab">Drafted</span><span class="sp-txt">{d.d.text}</span></div>
      </div>
      <div class="sp-acts"><span class="sub">Nothing changes until you choose.</span>
        <button type="button" class="btn sm" id="spKeep" onClick={onKeep}>Keep mine</button>
        <button type="button" class="btn sm primary" id="spUse" disabled={busy} onClick={onUse}>Use this <kbd>⏎</kbd></button></div>
    </div>
  );
}

/** @typedef {{r: SneakReply, id: string, text: string, shown: boolean, busy: boolean, flash: boolean, closing: string,
    setClosing: (v: string) => void, onMake: () => void, onNot: () => void, onPick: (typed: string, value: string) => void,
    onClaude: () => void, acts: SneakActs}} CardProps */
/** The answer to the words: a change, a task, a question, a pick, a problem or a refusal. @param {CardProps} props */
function Card({ r, id, text, shown, busy, flash, closing, setClosing, onMake, onNot, onPick, onClaude, acts }) {
  if (!r.ok) return <div class="sp-card warn" role="alert"><div class="sp-msg">{r.message || "That couldn't be read."}</div></div>;
  if (r.refused) {
    const btn = POINT[r.refused.point_to], to = r.refused.point_to;
    return (
      <div class="sp-card" id="spRefused"><div class="sp-msg">{r.refused.why}{POINT_SAY[to] ? " " + POINT_SAY[to] : ""}
        {r.refused.where ? <span class="sub" id="spWhere">Instead: {r.refused.where}.</span> : null}
        {btn ? <div class="sp-acts"><button type="button" class="btn sm primary" data-point={to} onClick={() => acts.point(to, text)}>{btn}
          {to === "draft_chase" ? <kbd>C</kbd> : to === "ask" ? <kbd>/</kbd> : null}</button></div> : null}</div></div>
    );
  }
  if (r.choices) {
    const c = r.choices;
    return (
      <div class="sp-card" id="spChoices"><div class="sp-msg">There are {c.options.length} people called “{c.typed}” in the people register. Which one?
        <div class="pick" role="group" aria-label={`Which ${c.typed}`}>{c.options.map(o => <button type="button" class="btn sm" key={o.value}
          onClick={() => onPick(c.typed, o.value)}>{o.label}</button>)}</div></div></div>
    );
  }
  const t = r.task, nc = r.needs_claude;
  if (t && t.kind === "facts") return (
    <div class="sp-card" id="spFacts">{(t.rows || []).map((/** @type {{label: string, text: string}} */ x, i) =>
      <div class="ans" key={i}><span class="k">{x.label} · read only</span><span>{x.text}</span></div>)}</div>
  );
  if (t && t.kind === "goto") {
    const w = t.target === "source" ? "Open the source" : t.target === "milestone" ? `Open the milestone ${t.ref || ""}`.trim() : t.target === "project" ? "Open the project page" : "Open ask creaite";
    return (
      <div class="sp-card"><div class="sp-msg">{t.target === "ask" ? `That needs more than this item's own facts. ask creaite can answer it, with ${id} attached.`
        : t.target === "source" ? `The source: ${t.ref || "not recorded"}.` : `${w}.`}
        <div class="sp-acts"><button type="button" class="btn sm primary" id="spGo" onClick={() => acts.go(t, r.item)}>{w} <kbd>⏎</kbd></button></div></div></div>
    );
  }
  if (t && t.kind === "chase") {
    const tone = t.pane && t.pane.tone != null ? ["First", "Second", "Firmer"][t.pane.tone] : null;
    return (
      <div class="sp-card"><div class="sp-msg">Opens Draft email for {id}{t.pane && t.pane.to ? `, to ${t.pane.to}` : ""}, {tone ? `in the ${tone} tone` : "in the tone from how often it was chased"}, ready to copy. Nothing is sent.
        <div class="sp-acts"><button type="button" class="btn sm primary" id="spChase" onClick={() => acts.chase(t.pane || {})}>Open Draft email <kbd>⏎</kbd></button></div></div></div>
    );
  }
  const rows = (r.changes || []);
  const made = !!r.stage, conf = !!r.confirm;
  if (!made) {
    if (nc && !nc.optional) return (
      <div class={`sp-card${nc.off ? " warn" : ""}`} id="spClaude"><div class="sp-head"><SneakIcon shapes={SNEAK_ICON} size={15} /><b>{(DRAFTS[nc.kind] ? DRAFTS[nc.kind](nc.request || {}).word : "A draft")} by Claude</b>
        <span class="by">AI drafts</span></div>
        {r.problems.map((p, i) => <div class="sp-msg" key={i}>{p}</div>)}
        {nc.off || !nc.request ? <div class="sp-msg" id="spOff">{nc.why || "AI drafts are off for this."} The plain changes still work.</div>
          : <div class="sp-acts"><span class="sub">{nc.why || "Claude drafts it; you choose."}</span><button type="button" class="btn sm primary" id="spDraft" onClick={onClaude}>Draft it <kbd>⏎</kbd></button></div>}
      </div>
    );
    if (r.problems.length) return (
      <div class="sp-card warn" id="spProblems" role="alert">{r.problems.map((p, i) => <div class="sp-msg" key={i}>{p}</div>)}</div>
    );
    if (!shown) return null;
    return <div class="sp-card"><div class="sp-msg">I couldn't match that to {id}. Try “due Friday”, “owner to Sam”, “close it”, “add an update: …”, “blocked by ABC-012” or “what does this block?”.</div></div>;
  }
  const isNew = t && (t.kind === "action" || t.kind === "risk" || t.kind === "promise");
  const v = isNew ? t.values || {} : {};
  const head = isNew ? `New ${t.kind} from ${id}` : t && t.kind === "link" ? `Link ${id}` : `Change ${id}`;
  const stop = rows.find(c => c.confirm && c.field === "status" && END_WORD[String(c.to)]), issue = rows.find(c => c.confirm && c.field === "type");
  const okWord = conf ? (stop ? `${END_WORD[String(stop.to)]} ${id}` : issue ? "Make it an issue" : "Confirm the change")
    : isNew ? `Create the ${t.kind}` : "Make the change";
  return (
    <div class={`sp-card${conf ? " warn" : ""}`} id="spCard">
      <div class="sp-head"><SneakIcon shapes={SNEAK_ICON} size={15} /><b>{head}</b><span class="by" id="spBy">{r.by === "claude" ? "Read by Claude" : "Understood in plain code"}</span></div>
      {rows.map((c, i) => <div class="chgrow" key={i}><span class="k">{c.label}</span>
        <span>{c.from_shown !== "" && c.from_shown != null ? <><span class="old">{c.from_shown}</span> → </> : null}<span class="to">{c.to_shown}</span>{c.derived ? <span class="sub"> (worked out)</span> : null}</span></div>)}
      {t && t.kind === "link" ? <div class="chgrow"><span class="k">Link</span><span><span class="to">{t.from_item === id ? `${id} blocks ${t.to_item}` : `${id} is blocked by ${t.from_item}`}</span>{t.other && t.other.title ? <span class="sub"> · {t.other.title}</span> : null}</span></div> : null}
      {isNew ? <div class="newitem"><span class="sub"><b>New {t.kind}</b> · ID given when applied</span><span class="to">{v.description || ""}</span>
        <span class="sub">{t.kind === "risk" ? `Owner ${v.owner || "not set"} · impact ${v.impact || "Medium"} × likelihood ${v.likelihood || "Medium"} (change them after)`
          : t.kind === "promise" ? `Promised by ${v.promised_by || "you"} to ${v.promised_to || "—"} · by ${v.due_date ? dmyShown(v.due_date) : "no date"}`
          : `Owner ${v.owner || "not set"} · due ${v.due_date ? dmyShown(v.due_date) : "not set"}`} · linked to {id}</span></div> : null}
      {r.offer_closing_update ? <div class="chgrow"><label class="k" for="spClose">Closing update</label>
        <input type="text" id="spClose" placeholder="Optional" value={closing} onInput={e => setClosing(/** @type {HTMLInputElement} */ (e.currentTarget).value)}
          onKeyDown={e => { if (e.key === "Enter" && !(e.metaKey || e.ctrlKey) && !conf) { e.preventDefault(); e.stopPropagation(); onMake(); } }} /></div> : null}
      {r.problems.length ? <div class="sub" id="spLeft">{r.problems.join(" ")}</div> : null}
      {nc && nc.optional ? <div class="sub" id="spWord">{nc.off || !nc.request ? (nc.why || "AI drafts are off for this.")
        : <button type="button" class="btn sm" id="spWordBtn" onClick={onClaude}><SneakIcon shapes={SNEAK_ICON} size={13} /> Word the update with Claude</button>}</div> : null}
      <div class="sp-acts">
        {conf ? <span class={`need${flash ? " flash" : ""}`} id="spNeed">{typeof r.confirm === "object" && r.confirm.why ? r.confirm.why + " " : ""}Needs a confirm: <kbd>{MOD}</kbd><kbd>⏎</kbd> or click</span>
          : <span class="sub">You can undo it.</span>}
        <button type="button" class="btn sm" onClick={onNot}>Not now</button>
        <button type="button" class="btn sm primary" id="spMake" disabled={busy} onClick={onMake}>{okWord} <kbd>{conf ? `${MOD}⏎` : "⏎"}</kbd></button>
      </div>
    </div>
  );
}

/** YYYY-MM-DD as DD-MM-YYYY. @param {string} iso */
function dmyShown(iso) { const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso)); return m ? `${m[3]}-${m[2]}-${m[1]}` : String(iso); }

/** Mount the box for item `id` into `host`. @param {Element} host @param {string} id @param {(back: boolean) => void} onClose
    @param {SneakActs} acts */
export function mountSneak(host, id, onClose, acts) { render(null, host); render(<SneakPeek id={id} onClose={onClose} acts={acts} />, host); }

/** Take the box out of `host`. @param {Element} host */
export function unmountSneak(host) { render(null, host); }
