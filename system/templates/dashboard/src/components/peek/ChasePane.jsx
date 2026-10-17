// @ts-check
/* ChasePane (BL-298, dev/COMPONENTS.md): the Draft email pane inside the work-item peek, as drawn in
   dev/mockups/draft-chase-mockup.html. The server writes the email (POST /api/chase/pane: drafts.py chase_pane, plain code, no
   model call); this pane shows the controls and the email, and asks the server again as Alan changes them, so the preview follows
   what he types. The email is drawn in its own fixed colours (Calibri, the Draft email's palette, DE_COLOURS) whatever the theme,
   with every element styled inline, as Outlook will show it. Copy for Outlook puts that HTML (and the plain text as the fallback)
   on the clipboard; Copy as text the subject and the plain text. Nothing is sent and no Outlook draft is made. "I sent it" records
   the chase (POST /api/chases: the item's ID, the date and the mode, in system/staging/chases.json), so the next one steps up.
   Nobody is labelled a VIP (BL-288). panel.js mounts it into #pkChase (mountChase) and puts the envelope in #pkBar.
   Polish (Alan, 13-10-2026, option A; dev/mockups/draft-chase-polish-mockup.html): one row under the email, in the pane's own Tone.
   It rewords the opening (kind "polish"); on Alan's own item it also suggests To get … done and What I need from you ("polish-help").
   Yours and Claude's side by side; nothing changes until Use this. Changing the tone or those two lines drops the polished wording. */
import { render } from "preact";
import { useEffect, useRef, useState } from "preact/hooks";
import { fd, TODAY } from "../../core/page.js";
import { api, snack, viaServer } from "../../core/server.js";
import { DE_COLOURS, DE_FONT, draftStat, draftWhyNot, POLISH_TONES, polishAsk, sentKindOf, sentLog } from "../../drafts.js";
import { SA } from "../../settings.js";

/** @typedef {[string, Record<string, string>][]} Shapes  an icon as element data (COMPONENTS.md Q2): [tag, attributes] */

/** The Draft email icon: an envelope with an arrow. @type {Shapes} */
export const CHASE_ICON = [["rect", { x: "3", y: "5", width: "14", height: "11", rx: "2" }], ["path", { d: "M3.5 6.5 10 11l6.5-4.5" }],
  ["path", { d: "M15 19h6M18.5 16.5 21 19l-2.5 2.5" }]];
/** @type {Shapes} */
const BACK_ICON = [["path", { d: "M19 12H5M11 18l-6-6 6-6" }]];
/** Polish's mark, the page's spark (ICONS.spark). @type {Shapes} */
const SPARK_ICON = [["path", { d: "M12 1Q12 12 23 12Q12 12 12 23Q12 12 1 12Q12 12 12 1Z", fill: "currentColor", stroke: "none" }]];
const TONES = ["First", "Second", "Firmer"];
/** border="0", which Outlook reads and Preact's types leave out */
const OLD_TABLE = /** @type {any} */ ({ border: "0" });
const DEBOUNCE = 150;          // ms after the last change before the server is asked again (it answers in about 100 ms)

/** @typedef {{id: string, label: string, item: string, owner: string, response: string, update: string, due_label: string,
    due: string, due_words: string, overdue: boolean, priority: string}} ChaseRow */
/** @typedef {{subject: string, greeting: string, opening: string, need_label: string, need: string, outcome: string,
    unblocks: string, row: ChaseRow, ask: string, sign_off: string, from: string, text: string, tone: number}} ChaseDraft */
/** @typedef {{name: string, email: string, org?: string, role?: string, why?: string}} ChasePerson */
/** @typedef {{ok: boolean, message?: string, id: string, mode: "chase"|"help"|"decision", mode_tag: string, mode_line: string,
    project: string, code: string, to: {name: string, email: string, first: string}, suggestions: ChasePerson[],
    anyone: ChasePerson[], defaults: {reply_by: string, tone: number, include_update: boolean, chased: {n: number, last: string}},
    draft: ChaseDraft}} ChaseReply */
/** @typedef {{to?: string, tone?: number, reply_by?: string, include_update?: boolean, outcome?: string, need?: string,
    cover?: string}} ChaseOpts  cover: a polished opening (Polish), in place of the drafted one */
/** @typedef {{text: string, outcome?: string, need?: string, notes?: string[]}} PolishReply  what draftAsk resolves to, in part */
/** @typedef {{d: PolishReply, tone: number, help: boolean, was: {opening: string, outcome: string, need: string}}} PolishCard */

/** An icon from element data, drawn as ic() draws one.
    @param {{shapes: Shapes}} props */
function ShapesIcon({ shapes }) {
  return (
    <svg class="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"
      aria-hidden="true">
      {shapes.map(([tag, a]) => tag === "rect" ? <rect {...a} /> : tag === "circle" ? <circle {...a} /> : <path {...a} />)}
    </svg>
  );
}

/** The mode line's sentence with its first words bold, as drawn ("<b>Chasing Tom</b>, who owns it. …").
    @param {{mode: string, line: string}} props */
function ModeWords({ mode, line }) {
  const at = mode === "decision" ? line.indexOf(" by its needed-by date") : mode === "help" ? line.indexOf(",") + 1 : line.indexOf(",");
  return at > 0 ? <div><b>{line.slice(0, at)}</b>{line.slice(at)}</div> : <div>{line}</div>;
}

/** The email as Outlook will show it: every element styled inline in the email's own palette (no classes, no variables), the
    item as the Draft email's one-row table. Its DOM is what Copy for Outlook copies.
    @param {{d: ChaseDraft, mailRef: import("preact").RefObject<HTMLDivElement>}} props */
export function ChaseEmail({ d, mailRef }) {
  const C = DE_COLOURS, r = d.row;
  const P = `${DE_FONT}color:${C.ink};margin:0 0 12px 0;`, B = "font-weight:bold;", muted = `color:${C.muted};`;
  const td = (extra = "") => `${DE_FONT}color:${C.ink};border-bottom:1px solid ${C.rule};padding:6px 8px;vertical-align:top;${extra}`;
  const th = (w = "") => `${DE_FONT}color:${C.ink};background:${C.head};border-bottom:1px solid ${C.rule};padding:6px 8px;text-align:left;` +
    `font-weight:bold;${w ? `width:${w};` : ""}`;
  const due = `color:${r.overdue ? C.red : r.due_words ? C.amber : C.ink};${r.overdue ? B : ""}`;
  return (
    <div ref={mailRef} style={`${DE_FONT}color:${C.ink};background:${C.white};`}>
      <p style={P}>{d.greeting}</p>
      <p style={P}>{d.opening}</p>
      {d.need ? <p style={`${P}background:${C.askBg};border-left:3px solid ${C.askRule};padding:6px 9px;`}><b style={B}>{d.need_label}</b> {d.need}</p> : null}
      <table cellPadding="6" cellSpacing="0" {...OLD_TABLE} style={`border-collapse:collapse;width:100%;${DE_FONT}color:${C.ink};`}>
        <tr style="vertical-align:top;"><th align="left" style={th("9%")}>ID</th><th align="left" style={th()}>Item</th>
          <th align="left" style={th("18%")}>{r.due_label}</th><th align="left" style={th("10%")}>Priority</th></tr>
        <tr style="vertical-align:top;">
          <td style={td("white-space:nowrap;")}>{r.id}</td>
          <td style={td()}>{r.label ? <b style={B}>{r.label}</b> : null}{r.label ? " " : ""}{r.item}
            {[r.owner, r.response, r.update].filter(Boolean).map(x => <><br /><span style={muted}>{x}</span></>)}</td>
          <td style={td("white-space:nowrap;")}><span style={due}>{r.due}</span>{r.due_words ? <><br /><span style={due}>{r.due_words}</span></> : null}</td>
          <td style={td("white-space:nowrap;")}>{r.priority === "Urgent" ? <b style={B}>Urgent</b> : r.priority}</td>
        </tr>
      </table>
      <p style={`${P}margin-top:16px;`}>{d.ask}</p>
      <p style={`${P}margin-bottom:0;`}>{d.sign_off}<br />{d.from}</p>
    </div>
  );
}

/** Select an element's contents, so Alan can copy them himself when the browser refuses the clipboard.
    @param {Element | null} el */
function selectAll(el) {
  if (!el) return;
  const range = document.createRange(), sel = window.getSelection();
  range.selectNodeContents(el);
  if (sel) { sel.removeAllRanges(); sel.addRange(range); }
}

/** The Draft email pane for one open item.
    start (BL-322): the first choices, from Sneak peek's "chase Tom, firmer" ({tone, to}).
    @param {{id: string, onBack: () => void, start?: ChaseOpts}} props */
export function ChasePane({ id, onBack, start }) {
  const [pane, setPane] = useState(/** @type {ChaseReply | null} */ (null));
  const [err, setErr] = useState("");
  const [opts, setOpts] = useState(/** @type {ChaseOpts} */ ({ ...(start || {}) }));
  const [said, setSaid] = useState({ text: "", ok: true });
  const [busy, setBusy] = useState(false);
  const [polishing, setPolishing] = useState(false);
  const [card, setCard] = useState(/** @type {PolishCard | null} */ (null));
  const [anyOpen, setAnyOpen] = useState(false);
  const [anyQ, setAnyQ] = useState("");
  const sending = useRef(false);
  const viaRef = useRef(/** @type {"email"|"message"} */ ("email"));
  const seq = useRef(0), mail = useRef(/** @type {HTMLDivElement | null} */ (null)), back = useRef(/** @type {HTMLButtonElement | null} */ (null));
  const first = useRef(true);
  const polGen = useRef(0), cardRef = useRef(/** @type {PolishCard | null} */ (null)), alive = useRef(true);
  cardRef.current = card;
  useEffect(() => () => { alive.current = false; if (cardRef.current) draftStat("email", "rejected"); }, []);   // left with a card open

  useEffect(() => { if (back.current) back.current.focus(); }, []);
  useEffect(() => {
    if (!viaServer()) { setErr("Draft email needs the live server: start it, then try again."); return undefined; }
    const n = ++seq.current;
    const t = setTimeout(async () => {
      const r = await api("/api/chase/pane", { id, hour: new Date().getHours(), ...opts });
      if (n !== seq.current) return;                       // a later change has asked again
      if (!r || r.ok === false) { setErr((r && r.message) || "The item couldn't be read."); return; }
      setErr(""); setPane(/** @type {ChaseReply} */ (r));
    }, first.current ? 0 : DEBOUNCE);
    first.current = false;
    return () => clearTimeout(t);
  }, [id, opts]);

  /** @param {keyof ChaseOpts} k @param {any} v */
  const set = (k, v) => { setOpts(o => ({ ...o, [k]: v })); setSaid({ text: "", ok: true }); };
  /** @param {string} text @param {boolean} [ok] */
  const say = (text, ok = true) => setSaid({ text, ok });

  const head = (
    <h2 class="ch-h">
      <button type="button" class="ib" ref={back} aria-label="Back to the item" data-tip="Back to the item" onClick={onBack}><ShapesIcon shapes={BACK_ICON} /></button>
      Draft email · <span class="sub">{id}</span>
    </h2>
  );
  if (!pane) return <div class="chase">{head}<p class="sub" role="status">{err || "Drafting the email…"}</p></div>;

  const d = pane.draft, mode = pane.mode, help = mode === "help";
  const tone = opts.tone ?? pane.defaults.tone, replyBy = opts.reply_by ?? pane.defaults.reply_by;
  const inc = opts.include_update ?? pane.defaults.include_update;
  const outcome = opts.outcome ?? d.outcome, need = opts.need ?? d.need;
  const anyone = anyOpen ? pane.anyone.filter(p => !anyQ.trim() || `${p.name} ${p.org || ""} ${p.role || ""}`.toLowerCase().includes(anyQ.trim().toLowerCase())).slice(0, 8) : [];

  async function copyOutlook() {
    const el = mail.current, text = d.text;
    try {
      if (!el || typeof ClipboardItem === "undefined" || !navigator.clipboard || !navigator.clipboard.write) throw new Error("no rich clipboard");
      const markup = new XMLSerializer().serializeToString(el);
      await navigator.clipboard.write([new ClipboardItem({ "text/html": new Blob([markup], { type: "text/html" }), "text/plain": new Blob([text], { type: "text/plain" }) })]);
      viaRef.current = "email"; say("Copied. Paste into a new Outlook email.");
    } catch (e) { selectAll(el); say("The browser didn't allow copying: the email is selected, so copy it with ⌘C.", false); }
  }
  async function copyText() {
    try {
      if (!navigator.clipboard || !navigator.clipboard.writeText) throw new Error("no clipboard");
      await navigator.clipboard.writeText(`${d.subject}\n\n${d.text}`);
      viaRef.current = "message"; say("Copied as plain text.");
    } catch (e) { selectAll(mail.current); say("The browser didn't allow copying: the email is selected, so copy it with ⌘C.", false); }
  }
  /* Polish (Settings › AI drafts), through the Draft email's machinery (polishAsk). Someone else's item and a decision: the opening
     only. Alan's own item: the opening and the two lines above it. The model never gets the table, subject or addresses. */
  const kind = help ? "polish-help" : "polish", why = draftWhyNot(kind);
  /** Drop a card or a run in progress (a run still going is ignored when it ends); the caller takes the cover out of opts. */
  function dropPolish() {
    polGen.current++;
    if (card) draftStat("email", "rejected");
    setCard(null); setPolishing(false);
  }
  async function polish() {
    const now = draftWhyNot(kind);                     // read again: the switch may have changed since this was drawn
    if (now) { say(now, false); return; }
    const gen = ++polGen.current, t = tone;
    const was = { opening: d.opening, outcome: help ? outcome : "", need: help ? need : "" };
    setCard(null); setPolishing(true); say("");
    // First → warm, Second → neutral, Firmer → firm (POLISH_TONES): Polish's own tones, from the pane's Tone
    const body = help ? { kind, id, text: was.opening, tone: POLISH_TONES[t], outcome: was.outcome, need: was.need }
      : { kind, text: was.opening, tone: POLISH_TONES[t] };
    const res = /** @type {any} */ (await polishAsk(body));
    if (!alive.current || gen !== polGen.current) { if (res && res.ok && !res.nothing) draftStat("email", "rejected"); return; }
    setPolishing(false);
    if (!res || !res.ok || res.nothing || !res.text) { say((res && (res.nothing || res.message)) || "No draft came back", false); return; }
    setCard({ d: res, tone: t, help, was });
  }
  function keepMine() { draftStat("email", "rejected"); setCard(null); say("Kept your wording."); }
  function useThis() {
    const c = card;
    if (!c) return;
    draftStat("email", "used");
    const text = String(c.d.text).trim();
    setOpts(o => ({ ...o, cover: text, ...(c.help ? { outcome: c.d.outcome || c.was.outcome, need: c.d.need || c.was.need } : {}) }));
    setCard(null);
    say("Polished wording in the email. Change the tone or the text to go back to the standard wording.");
  }
  /** The tone changed: the polished wording goes. @param {number} i */
  function setTone(i) {
    if (i === tone) return;
    dropPolish();
    const had = !!(opts.cover || card);
    setOpts(o => { const { cover: _c, ...rest } = o; return { ...rest, tone: i }; });
    setSaid(had ? { text: "Tone changed, so the polished wording was dropped. Polish again if you want it.", ok: true } : { text: "", ok: true });
  }
  /** Alan edits To get … done or What I need from you: the polished wording goes. @param {"outcome"|"need"} k @param {string} v */
  function setLine(k, v) {
    const had = !!(opts.cover || card);
    dropPolish();
    setOpts(o => { const { cover: _c, ...rest } = o; return { ...rest, [k]: v }; });
    setSaid(had ? { text: "You changed the wording, so the polished version was dropped. Polish again if you want it.", ok: true } : { text: "", ok: true });
  }
  /* v2.3.0 #153: record the chase (chases.json, as before), stage a dated Latest update on the item through the peek's own
     staging (one Undo in the toast), and go back to the open item. The button stays disabled once it has gone through, so a second
     press can't log it twice; the pane closes anyway. */
  async function sentIt() {
    if (sending.current) return;                 // a ref, not the state: a second click before the redraw is still caught
    sending.current = true; setBusy(true);
    const r = await api("/api/chases", { ids: [id], mode });
    if (!r || !r.ok) { sending.current = false; setBusy(false); say((r && r.message) || "Not recorded", false); return; }
    SA().chases = r.chases || {};
    const k = sentKindOf(id);
    const who = pane.to.name || pane.to.first || "them";
    let done = 0;
    try { done = k ? await sentLog([{ k, id, need: outcome }], { name: who, mode, replyBy, via: viaRef.current, chases: r.chases || {} }) : 0; }
    catch (err) { sending.current = false; setBusy(false); snack("The update couldn't be logged: press I sent it to try again"); return; }
    if (!done) snack(`Recorded: chased ${pane.to.first || who} on ${fd((r.record && r.record.date) || TODAY)}. The update couldn't be staged.`);
    dropPolish();
    onBack();
  }

  return (
    <div class="chase" role="region" aria-label={`Draft email for ${id}`}>
      {head}
      <div class="ch-mode"><span class={`tag ch-tag${help ? " ok" : ""}`}>{pane.mode_tag}</span><ModeWords mode={mode} line={pane.mode_line} /></div>
      <div class="ch-f">
        <span class="ch-l" id="chToL">To</span>
        <div class="ch-chips" role="group" aria-labelledby="chToL">
          {pane.to.name ? <span class="ch-chip">{pane.to.name}</span> : <span class="sub">Choose someone below</span>}
          <span class="sub">{pane.to.email || (pane.to.name ? "No email recorded" : "")}</span>
        </div>
        {help ? <div class="ch-sugg" role="group" aria-label="Suggested from the item">
          {pane.suggestions.map(s => <button type="button" aria-pressed={s.name === pane.to.name} onClick={() => set("to", s.name)}>{s.name} <small>{s.why}</small></button>)}
          <button type="button" aria-expanded={anyOpen} aria-controls="chAnyone" onClick={() => { setAnyOpen(!anyOpen); setAnyQ(""); }}>+ Anyone</button>
        </div> : null}
        {help && anyOpen ? <div class="ch-any" id="chAnyone">
          <input type="text" aria-label="Find someone in the people register" placeholder="Find someone" value={anyQ} onInput={e => setAnyQ(e.currentTarget.value)} />
          <div class="ch-sugg" role="group" aria-label="People">
            {anyone.length ? anyone.map(p => <button type="button" onClick={() => { set("to", p.name); setAnyOpen(false); }}>{p.name} <small>{p.org || p.role || ""}</small></button>)
              : <span class="sub">No match</span>}
          </div>
        </div> : null}
      </div>
      {help ? <>
        <div class="ch-f"><label class="ch-l" for="chOutcome">To get … done</label>
          <input type="text" id="chOutcome" value={outcome} onInput={e => setLine("outcome", e.currentTarget.value)} /></div>
        <div class="ch-f"><label class="ch-l" for="chNeed">What I need from you</label>
          <textarea id="chNeed" value={need} onInput={e => setLine("need", e.currentTarget.value)} /></div>
      </> : null}
      <div class="ch-row2">
        <div class="ch-f"><label class="ch-l" for="chReplyBy">Reply by</label>
          <input type="date" id="chReplyBy" value={replyBy} onInput={e => { if (e.currentTarget.value) set("reply_by", e.currentTarget.value); }} /></div>
        <div class="ch-f"><span class="ch-l" id="chToneL">Tone</span>
          <div class="ch-seg" role="group" aria-labelledby="chToneL">
            {TONES.map((w, i) => <button type="button" data-tone={String(i)} aria-pressed={i === tone} onClick={() => setTone(i)}>{w}</button>)}
          </div></div>
      </div>
      <label class="ch-inc"><input type="checkbox" id="chIncUpd" checked={inc} onChange={e => set("include_update", e.currentTarget.checked)} /> Include the latest update</label>
      <div class="ch-mailwrap">
        <div class="ch-mailhead"><div><span>To:</span> {pane.to.email || "No email recorded"}</div><div><span>Subject:</span> <b id="chSubj">{d.subject}</b>{opts.cover ? <span class="ch-ptag" id="chPolished">Polished</span> : null}</div></div>
        <div class="ch-mail" id="chMail" role="group" aria-label="The email, as Outlook will show it" style={`background:${DE_COLOURS.white};`}><ChaseEmail d={d} mailRef={mail} /></div>
      </div>
      <div class="ch-pol" role="group" aria-label="Polish the wording">
        <span class="sub">{help ? <>Reword the opening, and suggest the two lines above, in the <b>{TONES[tone]}</b> tone.</>
          : <>Reword the opening paragraph in the <b>{TONES[tone]}</b> tone. The table, subject and addresses stay as they are.</>}</span>
        <button type="button" class="btn ch-polbtn" id="chPolish" disabled={polishing} aria-disabled={why ? "true" : undefined}
          aria-describedby={why ? "chPolWhy" : undefined} data-tip={why || "Polish the wording with AI drafts"} onClick={polish}>
          <ShapesIcon shapes={SPARK_ICON} />{opts.cover ? "Polish again" : "Polish the wording"}</button>
      </div>
      {why && !polishing ? <div class="sub ch-polwhy" id="chPolWhy">{why}</div> : null}
      {polishing ? <div class="drstatus" role="status"><span class="spin" aria-hidden="true"></span><span>Polishing the wording…</span>
        <button type="button" class="mini" data-drstop="1">Stop</button></div> : null}
      {card ? <div class="drcard ch-card" role="region" aria-label="Polished wording">
        <div class="drhead"><ShapesIcon shapes={SPARK_ICON} /><b>Polished, {TONES[card.tone].toLowerCase()}</b><span class="sub">Nothing changes until you press Use this.</span></div>
        <div class="ch-cmpname">Opening</div>
        <div class="ch-cmp" data-part="opening"><div><span class="ch-cmplab">Yours</span>{card.was.opening}</div><div class="new"><span class="ch-cmplab">Polished</span>{card.d.text}</div></div>
        {card.help ? <>
          <div class="ch-cmpname">To get … done</div>
          <div class="ch-cmp" data-part="outcome"><div><span class="ch-cmplab">Yours</span>{card.was.outcome}</div><div class="new"><span class="ch-cmplab">Suggested</span>{card.d.outcome || card.was.outcome}</div></div>
          <div class="ch-cmpname">What I need from you</div>
          <div class="ch-cmp" data-part="need"><div><span class="ch-cmplab">Yours</span>{card.was.need}</div><div class="new"><span class="ch-cmplab">Suggested</span>{card.d.need || card.was.need}</div></div>
        </> : null}
        {card.d.notes && card.d.notes.length ? <div class="drnote"><ul>{card.d.notes.map(n => <li>{n}</li>)}</ul></div> : null}
        <div class="drfoot"><span class="sp"></span><button type="button" class="btn" id="chKeepMine" onClick={keepMine}>Keep mine</button>
          <button type="button" class="btn primary" id="chUseThis" onClick={useThis}>Use this</button></div>
      </div> : null}
      <div class="ch-acts">
        <span class={`ch-said${said.ok ? "" : " fail"}`} role="status" aria-live="polite">{said.text}</span>
        <button type="button" class="btn" id="chCopyText" onClick={copyText}>Copy as text</button>
        <button type="button" class="btn" id="chSent" disabled={busy} data-tip="Log that you sent it: a dated Latest update on the item, and the next one steps up (no email text is kept)" onClick={sentIt}>I sent it</button>
        <button type="button" class="btn primary" id="chCopyHtml" onClick={copyOutlook}>Copy for Outlook</button>
      </div>
    </div>
  );
}

/** Mount the pane for item `id` into `box` (panel.js's #pkChase); `onBack` returns to the item.
    @param {Element} box @param {string} id @param {() => void} onBack @param {ChaseOpts} [start] */
export function mountChase(box, id, onBack, start) { render(null, box); render(<ChasePane id={id} onBack={onBack} start={start} />, box); }

/** Take the pane out of `box`. @param {Element} box */
export function unmountChase(box) { render(null, box); }
