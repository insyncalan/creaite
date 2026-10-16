// @ts-check
/* PrepShape (BL-286 part C): Shape the meeting, inside the Prep popup (the popup's toolbar shows "Shape this meeting" once this
   has registered itself through stores/prepPopup.js prepShape). While it is open the popup's brief steps aside (#prepDlg.shaping)
   and the header and toolbar stay.
   - The instruction box: a textarea Alan drags larger, with suggestion chips (/api/prep/chips) that add their item to the text.
   - Shape: Claude through the run engine (/api/prep/shape, streamed): progress, Stop, one run at a time.
   - "creaite read this as": the focus as chips, the aim, focus only or focus first; *change* corrects it.
   - Draft notes: Objective, Talking points, Ask, Carried over, each a box Alan edits and drags larger, every line's citation
     under it (an item opens the peek, a file opens through /api/open, mail and Teams by their web link). Regenerate keeps the
     sections he edited; Accept saves to prep-focus.json; Discard counts a rejection.
   - What's in focus: the items and documents linked to the focus (/api/prep/filter), each with why, ticked out with its box,
     "n of N" (N is only those listed), and Show everything instead (focus first).
   A confidential meeting is shaped from Alan's text and the tracker only (the server gives such a run no tools). */
import { render } from "preact";
import { useEffect, useRef, useState } from "preact/hooks";
import { Chip } from "../Chip.jsx";
import { Icon } from "../Icon.jsx";
import { TextEditor } from "../TextEditor.jsx";
import { fd } from "../../core/page.js";
import { viaServer } from "../../core/server.js";
import { draftWhyNot } from "../../drafts.js";
import { kOfId } from "../../work.js";
import { popupRev, prepNow, prepShape } from "../../stores/prepPopup.js";
import { acceptShape, addChip, closeShape, discardShape, editedSections, giveBack, notesNow, openShape, previewFilter, runShape,
  SHAPE_SECTIONS, setReading, shapeAccepted, shapeBusy, shapeChecks, shapeChips, shapeConfidential, shapeDrafted, shapeExcluded,
  shapeFilter, shapeInstruction, shapeKey, shapeMsg, shapeReading, shapeSourcesN, shapeSteps, shapeText, shapeUsed,
  toggleExcluded } from "../../stores/prepShape.js";

const SHAPE_ID_RE = /\b[A-Z][A-Z0-9]{2,6}-(?:[A-Z]-)?\d{3}\b/;
const shPlural = (/** @type {number} */ n, /** @type {string} */ one) => `${n} ${one}${n === 1 ? "" : "s"}`;
/** "2026-10-13 09:30" → "13-10-2026 09:30". @param {string} s */
const stamp = s => s ? `${fd(s.slice(0, 10))}${s.length > 10 ? s.slice(10) : ""}` : "";

/** One typed source as a link: an item opens the peek (data-open), a file through /api/open (data-dropen), mail and Teams by the
    web link the sweep kept; anything else is plain text.
    @param {{s: import("../../stores/prepShape.js").Typed}} props */
export function ShapeSource({ s }) {
  const text = s.label || s.id || s.path || s.type;
  if (s.type === "item" && s.id) {
    const k = kOfId(s.id);
    return k ? <a href="#" class="shcite" data-open={`${k}:${s.id}`} data-tip="Opens the item">{text}</a> : <span class="shcite plain">{text}</span>;
  }
  if (s.type === "file" && s.path) return <a href="#" class="shcite" data-dropen={s.path} data-tip={`Opens ${s.path}`}>{text}</a>;
  if ((s.type === "mail" || s.type === "teams") && s.url && /^https:\/\//.test(s.url)) {
    return <a href={s.url} class="shcite" target="_blank" rel="noopener noreferrer" data-tip={s.type === "mail" ? "Opens in Outlook" : "Opens in Teams"}>{text}</a>;
  }
  return <span class="shcite plain">{text}</span>;
}

/** "creaite read this as", and its *change*: the focus entries, the aim, and focus only or focus first. */
function ReadAs() {
  const r = shapeReading.value, [edit, setEdit] = useState(/** @type {import("../../stores/prepShape.js").Reading | null} */ (null));
  const [add, setAdd] = useState("");
  const first = useRef(/** @type {HTMLInputElement | null} */ (null));
  useEffect(() => { if (edit) first.current?.focus(); }, [!!edit]);
  if (!r) return null;
  const showWords = (/** @type {string} */ s) => s === "focus-only" ? "Only the items and documents linked to the focus" : "The focus first, then everything else";
  if (!edit) {
    return (
      <div class="readas" role="group" aria-labelledby="shReadH">
        <div class="sub" id="shReadH">creaite read this as <button type="button" class="linkbtn" data-shchange="1" onClick={() => setEdit({ ...r, focus: [...r.focus] })}>change</button></div>
        <div class="rl">
          <span>Focus</span>
          <span class="shfocus">{r.focus.length ? r.focus.map((f, i) => <Chip key={i} cls={f.id ? "sel" : ""} name={f.id ? `Focus item ${f.id}` : "Focus"}>{f.id && !f.text.includes(f.id) ? `${f.id} · ${f.text}` : f.text}</Chip>) : <span class="sub">Nothing read as the focus</span>}</span>
          <span>Aim</span><span>{r.aim || <span class="sub">No aim read</span>}</span>
          <span>Show</span>
          <span>{showWords(r.show)} · <button type="button" class="linkbtn" data-shshow="1" onClick={() => setReading({ ...r, show: r.show === "focus-only" ? "focus-first" : "focus-only" })}>
            {r.show === "focus-only" ? "show everything instead" : "only the focus instead"}</button></span>
        </div>
      </div>
    );
  }
  const push = () => {
    const t = add.trim();
    if (!t || edit.focus.length >= 12) return;
    const id = (SHAPE_ID_RE.exec(t) || [""])[0];
    setEdit({ ...edit, focus: [...edit.focus, id ? { id, text: t } : { text: t }] });
    setAdd("");
  };
  return (
    <div class="readas editing" role="group" aria-labelledby="shReadE">
      <div class="sub" id="shReadE">Correct how creaite read this, then Regenerate</div>
      <div class="rl">
        <span>Focus</span>
        <span class="shfocus">
          {edit.focus.map((f, i) => (
            <span class="chip shrm" key={i}>{f.text}<button type="button" class="ib" aria-label={`Remove ${f.text}`} data-tip={`Remove ${f.text}`}
              onClick={() => setEdit({ ...edit, focus: edit.focus.filter((_, n) => n !== i) })}><Icon name="x" /></button></span>
          ))}
          <span class="shadd">
            <input ref={first} type="text" value={add} aria-label="Add to the focus: an item ID or a point" placeholder="An item ID or a point"
              onInput={e => setAdd(/** @type {HTMLInputElement} */ (e.currentTarget).value)}
              onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); push(); } }} />
            <button type="button" class="btn shsm" onClick={push}>Add</button>
          </span>
        </span>
        <label for="shAim">Aim</label>
        <input id="shAim" type="text" value={edit.aim} maxLength={600} onInput={e => setEdit({ ...edit, aim: /** @type {HTMLInputElement} */ (e.currentTarget).value })} />
        <span id="shShowL">Show</span>
        <span role="radiogroup" aria-labelledby="shShowL" class="shshow">
          {["focus-only", "focus-first"].map(v => (
            <label key={v}><input type="radio" name="shShow" value={v} checked={edit.show === v} onChange={() => setEdit({ ...edit, show: v })} />{showWords(v)}</label>
          ))}
        </span>
      </div>
      <div class="shrow">
        <span class="sp"></span>
        <button type="button" class="btn shsm" onClick={() => setEdit(null)}>Cancel</button>
        <button type="button" class="btn primary shsm" data-shdone="1" onClick={() => { setReading({ ...edit, aim: edit.aim.trim() }); setEdit(null); }}>Done</button>
      </div>
    </div>
  );
}

/** The draft notes: four boxes, each line's citations under its box, the checks, Regenerate, Discard and Accept. */
function Notes() {
  const drafted = shapeDrafted.value, busy = shapeBusy.value, texts = shapeText.value, checks = shapeChecks.value;
  if (!drafted && !SHAPE_SECTIONS.some(([k]) => (texts[k] || "").trim())) return null;
  const now = notesNow(), edited = new Set(editedSections()), why = draftWhyNot("shape");
  /** BL-301 D: AI on a selection in the notes (plain text), with the meeting's project; a confidential meeting asks once first.
      @type {import("../../core/editor.js").EdAi} */
  const ai = { place: "plain", project: () => prepNow().m.p || "",
    confidential: () => shapeConfidential.value || !!(prepNow().m.invite && prepNow().m.invite.confidential),
    key: () => `shape|${shapeKey.value || ""}` };
  return (
    <div class="shdraft" role="region" aria-label="Draft notes">
      <div class="shdh">
        <span class="tag shai"><Icon name="spark" />Draft from creaite</span>
        <span class="sub">Edit anything; drag a box's corner to make it bigger. Nothing is saved until you accept.</span>
        <span class="sp"></span>
        <button type="button" class="btn shsm" data-shregen="1" aria-disabled={why || busy ? "true" : undefined} data-tip={why || "Draft again; the sections you edited are kept"}
          onClick={() => { if (!why && !busy) runShape(); }}><Icon name="refresh" />Regenerate</button>
        <button type="button" class="btn shsm" data-shdiscard="1" disabled={!!busy} onClick={discardShape}>Discard</button>
        <button type="button" class="btn primary shsm" data-shaccept="1" disabled={!!busy || !shapeReading.value} onClick={() => { acceptShape(); }}>Accept</button>
      </div>
      {checks.length ? (
        <ul class="shchecks" aria-label="Checks on the draft">
          {checks.map((c, i) => <li key={i} class={c.level === "error" ? "bad" : "warn"}>{c.section ? `${c.section}: ` : ""}{c.note}</li>)}
        </ul>) : null}
      {shapeAccepted.value ? <p class="sub shacc" role="status">Accepted {stamp(shapeAccepted.value)}: the notes are on the prep page. Accept again after a change.</p> : null}
      {SHAPE_SECTIONS.map(([k, label]) => {
        const lines = now[k] || [];
        return (
          <div class="shsec" key={k}>
            <div class="shsech">
              <label id={`shN-${k}-l`}>{label}</label>
              {edited.has(k) ? <span class="sub shmine">Your edit, kept on Regenerate · <button type="button" class="linkbtn" onClick={() => giveBack(k)}>let creaite redraft it</button></span> : null}
            </div>
            <TextEditor id={`shN-${k}`} cls="shgrow shbox" rows={Math.max(2, lines.length + 1)} value={texts[k] || ""} labelledBy={`shN-${k}-l`} ai={ai} links
              describedBy={lines.length ? `shC-${k}` : undefined} onInput={t => { shapeText.value = { ...shapeText.value, [k]: t }; }} />
            {lines.length ? (
              <ol class="shcites" id={`shC-${k}`} aria-label={`${label}: each line's source`}>
                {lines.map((l, i) => (
                  <li key={i}>{(l.sources || []).length ? (l.sources || []).map((s, j) => <ShapeSource key={j} s={s} />) : <span class="drtag" role="note">no source</span>}</li>
                ))}
              </ol>) : null}
          </div>
        );
      })}
    </div>
  );
}

/** What's in focus: the items and the documents linked to the focus, each with why, ticked in or out. */
function Scope() {
  const f = shapeFilter.value, r = shapeReading.value;
  if (!f || !r) return null;
  const ex = new Set(shapeExcluded.value);
  return (
    <div class="shscope">
      <section class="card pc" aria-labelledby="shItemsH">
        <h3 id="shItemsH">Work items in focus <span class="sub" data-shcount="1">· {f.n} of {f.N}</span></h3>
        {f.items.length ? f.items.map(i => {
          const k = ["actions", "raid", "decisions"].includes(i.table) ? i.table : kOfId(i.id), off = ex.has(i.id);
          return (
            <div class={`shitem${off ? " off" : ""}`} key={i.id}>
              <input type="checkbox" checked={!off} aria-label={`Include ${i.id}`} onChange={() => toggleExcluded(i.id)} />
              <div class="t" data-open={k ? `${k}:${i.id}` : undefined} tabIndex={k ? 0 : undefined} role={k ? "button" : undefined}>
                <span class="idc">{i.id}</span>{i.text}
                <span class="sub">{[i.type, i.owner || "No owner", i.due ? fd(i.due) : ""].filter(Boolean).join(" · ")}</span>
                <span class="why">Why: {i.why.join("; ")}</span>
              </div>
            </div>);
        }) : <p class="sub">Nothing is linked to the focus yet. Name an item in the instruction, or add one with change.</p>}
        <p class="sub shshowall">{r.show === "focus-only"
          ? <>The prep page shows only these. <button type="button" class="linkbtn" data-shshowall="1" onClick={() => setReading({ ...r, show: "focus-first" })}>Show everything instead</button></>
          : <>The prep page shows these first, then everything else. <button type="button" class="linkbtn" data-shshowall="1" onClick={() => setReading({ ...r, show: "focus-only" })}>Only the focus instead</button></>}</p>
      </section>
      <section class="card pc" aria-labelledby="shDocsH">
        <h3 id="shDocsH">Documents and sources in focus {shapeConfidential.value ? null : <span class="sub">· {f.docs_n} of {f.docs_N}</span>}</h3>
        {shapeConfidential.value ? <p class="sub">A confidential meeting lists no documents.</p>
          : f.documents.length ? f.documents.map(d => {
            const off = ex.has(d.path);
            return (
              <div class={`shitem${off ? " off" : ""}`} key={d.path}>
                <input type="checkbox" checked={!off} aria-label={`Include ${d.name}`} onChange={() => toggleExcluded(d.path)} />
                <Icon name="filetext" />
                <span class="t"><a href="#" data-dropen={d.path} data-tip={`Opens ${d.path}`}>{d.name}</a>
                  <span class="why">Why: {d.why.join("; ")}</span></span>
              </div>);
          }) : <p class="sub">No document is linked to the focus.</p>}
      </section>
    </div>
  );
}

/** The shaping panel: shown while a meeting is being shaped and it is the one in the popup. */
export function PrepShape() {
  popupRev.value;
  const key = shapeKey.value, { key: now, e } = prepNow(), on = !!key && !!e && key === now;
  const box = useRef(/** @type {HTMLTextAreaElement | null} */ (null));
  useEffect(() => {
    const d = document.getElementById("prepDlg");
    if (d) d.classList.toggle("shaping", on);
    if (on) box.current?.focus();
  }, [on]);
  useEffect(() => { if (on && shapeFilter.value) previewFilter(); }, [popupRev.value]);   /* an applied edit shows in What's in focus */
  if (!on) return null;
  const busy = shapeBusy.value, why = draftWhyNot("shape"), conf = shapeConfidential.value;
  const chips = shapeChips.value.filter(c => !shapeUsed.value.includes(c.label));
  const hasDraft = !!shapeDrafted.value;
  return (
    <section class="shape" aria-labelledby="shapeH">
      <div class="shfocusbox">
        <div class="shtop">
          <h3 id="shapeH"><Icon name="spark" />Tell creaite how you want to run this meeting</h3>
          <button type="button" class="linkbtn" data-shback="1" onClick={closeShape}>Back to the brief</button>
        </div>
        {conf ? <p class="sub shconf" role="note">Confidential meeting: shaped from your text and the tracker only. creaite doesn't read the invite, minutes or documents.</p> : null}
        <label class="sub" for="shapeTxt">Your focus and aim. Write as much as you like; drag the corner to make the box bigger.</label>
        <textarea id="shapeTxt" ref={box} class="shgrow" rows={4} maxLength={4000} value={shapeInstruction.value}
          placeholder="For example: Focus on the latency risk only. I want Tom to commit to a date for the fix."
          onInput={ev => { shapeInstruction.value = /** @type {HTMLTextAreaElement} */ (ev.currentTarget).value; }} />
        <div class="shrow">
          {chips.length ? <span class="sub">Suggestions:</span> : null}
          {chips.map(c => <Chip key={c.label} cls="shsug" name={`Add ${c.label} to the text`} tip={c.why} onClick={() => addChip(c)}>+ {c.label}</Chip>)}
          <span class="sp"></span>
          <button type="button" class="btn primary" data-shrun="1" aria-disabled={why || busy ? "true" : undefined} data-tip={why || (hasDraft ? "Draft the notes again from the text; the sections you edited are kept" : "creaite reads the text and drafts the notes, each line cited")}
            onClick={() => { if (!why && !busy) runShape(); }}><Icon name="spark" />{hasDraft ? "Shape again" : "Shape"}</button>
        </div>
        {busy === "shape" ? (
          <div class="shrun" role="status"><span class="spin" aria-hidden="true"></span>
            <span>Shaping the meeting{shapeSourcesN.value ? ` from ${shPlural(shapeSourcesN.value, "source")}` : ""}{shapeSteps.value ? ` · ${shPlural(shapeSteps.value, "step")}` : ""}</span>
            <button type="button" class="mini" data-drstop>Stop</button></div>
        ) : null}
        {shapeMsg.value && !busy ? <p class="wnote" role="status">{shapeMsg.value}</p> : null}
        {!viaServer() ? <p class="wnote">Shaping needs the live server.</p> : null}
        <ReadAs />
      </div>
      <Notes />
      <Scope />
    </section>
  );
}

/** Mount the shaping panel into the popup's #prepShape, and register its opener with the toolbar (pressing Shape this meeting
    again goes back to the brief).
    @param {Element} el */
export function mountPrepShape(el) {
  render(<PrepShape />, el);
  prepShape.value = key => { if (shapeKey.value === key) closeShape(); else openShape(key); };
}
