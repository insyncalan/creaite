// @ts-check
/* UsagePanel (#238, v2.5.1): Activity › Usage. What each Claude run costs and what every run loads before it starts. Read only:
   the panel draws figures it is given (D.usage, from usage_report.py --json, refreshed from GET /api/usage where the live server
   has it) and has no button, field or link. Counts only: it never draws a label, a name or a path from the files, only the fixed
   kinds, skill names the server already cleaned and numbers. Text goes through JSX only; the chart is SVG nodes, not markup strings.
   Tokens loaded at start are what each run reported; the "about tokens" of the always-loaded files are bytes / 4 (said on the page).
   v2.5.3 (#238 delta): Your reviews, the tab's one form. Alan's own dated notes (what he saw, what he decided; one line of at most
   200 characters each, usage_reviews.py) are listed from D.usage.reviews, saved only through POST /api/usage/review (the live
   server's route; the page never writes the file) and downloaded as CSV with the same cells as usage_reviews.csv_text. Until the
   server has the route (D.usage.reviews_save) "Add a review note" is held, with the reason as its tooltip. */
import { render } from "preact";
import { useState } from "preact/hooks";
import { readDate, TODAY } from "../../core/page.js";
import { api, OLDSERVER, snack } from "../../core/server.js";

/** @typedef {{now: number | null, before: number | null, change_pct?: number | null, change?: number | null}} Card */
/** @typedef {{day: string, runs: number, cost_usd: number, start_median: number | null}} Day */
/** @typedef {{kind: string, runs: number, avg_tokens: number, start_median: number | null, cost_usd: number, share_pct: number}} Kind */
/** @typedef {{skill: string, runs: number, cost_usd: number, days_since: number | null, last: string | null}} Skill */
/** @typedef {{file: string, date: string, bytes: number, tokens: number, since: string | null, change_bytes: number | null, change_tokens: number | null}} Ctx */
/** @typedef {{date: string, saw: string, decided: string}} Review */
/** @typedef {{as_of?: string, days?: number, empty?: boolean, error?: string, cards?: Record<string, Card>, by_day?: Day[], by_kind?: Kind[], skills?: Skill[], context?: Ctx[], reviews?: Review[], reviews_save?: boolean}} Usage */

const KIND = { ask: "ask creaite", sweep: "Sweep", generate: "Generate current state", prep: "Prep page", draft: "Drafts",
  check: "Transcript check", load: "Transcript load", vip: "Alert check", process: "Intake processing",
  calendar: "Calendar refresh", reextract: "Read again", other: "Other" };
const FILE = { rules: "Rules (creaite-rules.md)", claude_md: "Your CLAUDE.md", memory: "Project memory and registers",
  skills: "Skill names and descriptions" };

const num = (/** @type {number | null | undefined} */ n) => (n == null ? "–" : Math.round(n).toLocaleString("en-GB"));
const usd = (/** @type {number | null | undefined} */ n) => `$${(n || 0).toFixed(2)}`;
const signed = (/** @type {number} */ n, f = num) => (n > 0 ? "+" : n < 0 ? "−" : "") + f(Math.abs(n));
/** 53 KB, 0.7 KB: one decimal under 10 KB, none above. @param {number} b */
const usageKb = b => { const k = b / 1000; return `${k >= 10 ? Math.round(k) : Number(k.toFixed(1))} KB`; };

/** A card's change on the week before, in words, and whether it is up, down or none.
    @param {Card} c @param {boolean} pct */
function delta(c, pct) {
  const ch = pct ? c.change_pct : c.change;
  if (c.before == null || (pct && !c.before)) return ["nothing to compare with last week", ""];
  if (ch == null || ch === 0) return ["no change on last week", ""];
  return [`${pct ? signed(ch, n => `${n}%`) : signed(ch)} on last week`, ch > 0 ? "up" : "dn"];
}

/** @param {{days: Day[], fd: (s: string) => string}} p */
function Chart({ days, fd }) {
  const W = 760, H = 150, L = 34, B = 22, n = days.length, bw = (W - L) / n;
  const top = Math.max(1, Math.ceil(Math.max(...days.map(d => d.cost_usd)))), step = top > 6 ? Math.ceil(top / 5) : 1;
  const max = Math.ceil(top / step) * step + (top === Math.ceil(top / step) * step ? step : 0);      /* headroom: the tallest bar never touches the label */
  const starts = days.map(d => d.start_median).filter(v => v != null), lo = starts.length ? Math.min(...starts) : 0, hi = starts.length ? Math.max(...starts) : 0;
  const half = Math.max(hi - lo, hi * 0.15, 1000) * 1.5, mid = (lo + hi) / 2;                         /* the line sits mid-chart; a 1,000 change reads as a slope, not a cliff */
  const y = (/** @type {number} */ v) => H - B - ((H - B - 8) * (v - (mid - half))) / (half * 2);
  const pts = days.map((d, i) => (d.start_median == null ? null : `${L + i * bw + bw / 2},${y(d.start_median)}`)).filter(Boolean).join(" ");
  const grid = []; for (let g = 0; g <= max; g += step) grid.push(g);
  const label = `Cost per day, last ${n} days, and the median tokens a run loaded before it started`;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label}>
      {grid.map(g => { const gy = H - B - ((H - B - 8) * g) / max; return <g key={g}><line class="ugrid" x1={L} x2={W} y1={gy} y2={gy} /><text class="uax" x="2" y={gy + 4}>{`$${g}`}</text></g>; })}
      {days.map((d, i) => { const h = ((H - B - 8) * d.cost_usd) / max; return (
        <g key={d.day}>
          <rect class="ubar" x={L + i * bw + 6} y={H - B - h} width={bw - 12} height={h}><title>{`${fd(d.day)}: ${usd(d.cost_usd)}, ${d.runs} ${d.runs === 1 ? "run" : "runs"}`}</title></rect>
          <text class="uax" x={L + i * bw + bw / 2} y={H - 6} text-anchor="middle">{fd(d.day).slice(0, 5)}</text>
        </g>); })}
      {pts ? <polyline class="uline" points={pts} fill="none" /> : null}
      {starts.length ? <text class="uax uaxl" x={W - 4} y="12" text-anchor="end">{`start load ${num(starts[0])} → ${num(starts[starts.length - 1])} tokens`}</text> : null}
    </svg>
  );
}

/** @param {{u: Usage, fd: (s: string) => string}} p */
function Runs({ u, fd }) {
  const c = u.cards || {}, kinds = u.by_kind || [];
  const cards = [
    ["cost", "Cost this week", usd(c.cost?.now), c.cost && delta(c.cost, true)],
    ["runs", "Runs this week", num(c.runs?.now), c.runs && delta(c.runs, true)],
    ["start", "Tokens a run loads before it starts", num(c.start?.now), c.start && delta(c.start, false)],
    ["avg", "Cost of an average run", usd(c.avg_cost?.now), c.avg_cost && delta(c.avg_cost, true)]];
  return (
    <>
      <div class="usum">
        {cards.map(([k, label, v, d]) => (
          <div class="ucard" key={k}><div class="v">{v}</div><div class="l">{label}</div><div class={`d ${d ? d[1] : ""}`}>{d ? d[0] : ""}</div></div>))}
      </div>
      <div class="uchart"><h2>Cost and what each run loads before it starts, by day</h2><Chart days={u.by_day || []} fd={fd} />
        <p class="sub">Bars: cost in dollars. Line: the median tokens a run loaded before doing anything (the rules file, CLAUDE.md, memory and skill names).</p></div>
      <h2>By kind of run</h2>
      <div class="tbl"><table class="qtab" aria-label="By kind of run">
        <thead><tr><th scope="col">Kind</th><th scope="col">Runs</th><th scope="col">Average tokens</th><th scope="col">Loaded at start (median)</th><th scope="col">Cost</th><th scope="col">Share of cost</th></tr></thead>
        <tbody>{kinds.map(k => <tr key={k.kind}><td>{KIND[k.kind] || KIND.other}</td><td>{num(k.runs)}</td><td>{num(k.avg_tokens)}</td><td>{num(k.start_median)}</td><td>{usd(k.cost_usd)}</td><td>{`${k.share_pct}%`}</td></tr>)}</tbody>
      </table></div>
    </>
  );
}

/** @param {{skills: Skill[]}} p */
function Skills({ skills }) {
  return (
    <>
      <h2>Skills</h2>
      <div class="tbl"><table class="qtab" aria-label="Skills">
        <thead><tr><th scope="col">Skill</th><th scope="col">Runs</th><th scope="col">Cost</th><th scope="col">Last used</th></tr></thead>
        <tbody>{skills.map(s => <tr key={s.skill}><td>{s.skill}</td><td>{num(s.runs)}</td><td>{usd(s.cost_usd)}</td><td>{lastUsed(s)}</td></tr>)}</tbody>
      </table></div>
    </>
  );
}

/** @param {Skill} s */
function lastUsed(s) {
  const ago = s.days_since == null ? "" : s.days_since === 0 ? "today" : s.days_since === 1 ? "yesterday" : `${s.days_since} days ago`;
  if (s.runs > 0) return ago;
  return s.days_since == null ? "never in this period (never run)" : `never in this period (${s.days_since} ${s.days_since === 1 ? "day" : "days"})`;
}

/** @param {{rows: Ctx[], start: number | null | undefined, fd: (s: string) => string}} p */
function Loads({ rows, start, fd }) {
  const total = rows.reduce((a, r) => a + r.tokens, 0), rules = rows.find(r => r.file === "rules");
  return (
    <>
      <h2>What every run loads</h2>
      <p class="sub">The always-loaded files, measured once a day. Tokens are estimates (bytes ÷ 4); the change is over the last 30 days.</p>
      {rows.length ? (
        <>
          <div class="tbl"><table class="qtab" aria-label="What every run loads">
            <thead><tr><th scope="col">File</th><th scope="col">Now</th><th scope="col">About tokens</th><th scope="col">Change in 30 days</th></tr></thead>
            <tbody>{rows.map(r => <tr key={r.file}><td>{FILE[r.file] || r.file}</td><td>{usageKb(r.bytes)}</td><td>{num(r.tokens)}</td><td>{ctxChange(r, fd)}</td></tr>)}</tbody>
          </table></div>
          <div class="unote"><b>Why this matters:</b>{" "}
            {`Every run starts by loading about ${num(start || total)} tokens${rules && total ? `, and the rules file is about ${Math.round((rules.tokens / total) * 100)}% of the always-loaded files` : ""}. A smaller rules file lowers the cost of every run.`}</div>
        </>
      ) : <p class="sub">Not measured yet. The live server measures these files once a day.</p>}
    </>
  );
}

/** @param {Ctx} r @param {(s: string) => string} fd */
function ctxChange(r, fd) {
  if (r.change_bytes == null || !r.since) return "no earlier measure yet";
  if (r.change_bytes === 0) return "no change";
  const k = Math.abs(r.change_bytes) / 1000;
  return `${r.change_bytes > 0 ? "+" : "−"}${Number((k >= 10 ? Math.round(k) : k).toFixed(1))} KB since ${fd(r.since)}`;
}

/* ===== v2.5.3 (#238 delta): Your reviews ===== */
const REVIEW_ROUTE = "/api/usage/review", MAX_NOTE = 200;
const NEEDS_UPDATE = "Saving reviews needs the next server update", NEEDS_LIVE = "Saving a review note needs the live server";
const FORMULA = /^[=+\-@\t\r]/;          /* a spreadsheet would run a cell starting with one of these (usage_reviews.FORMULA) */
/** One CSV cell: always quoted, quotes doubled, an apostrophe before a formula. @param {unknown} v */
export const csvCell = v => { let s = String(v ?? ""); if (FORMULA.test(s)) s = `'${s}`; return `"${s.replace(/"/g, '""')}"`; };
/** The notes as CSV, newest first, dates DD-MM-YYYY, CRLF (usage_reviews.csv_text, cell for cell).
    @param {Review[]} list @param {(s: string) => string} fd */
export const reviewsCsv = (list, fd) => [["Date", "What you saw", "What you decided"], ...list.slice().reverse().map(r => [fd(r.date), r.saw, r.decided])]
  .map(row => `${row.map(csvCell).join(",")}\r\n`).join("");

/** Hand the viewer a file. @param {string} text @param {string} name */
function saveFile(text, name) {
  const url = URL.createObjectURL(new Blob(["\ufeff", text], { type: "text/csv;charset=utf-8" }));     /* the BOM: Excel reads it as UTF-8 */
  const a = document.createElement("a"); a.href = url; a.download = name; document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** @param {{list: Review[], fd: (s: string) => string, held: string, onSaved: (list: Review[]) => void}} p */
function Reviews({ list, fd, held, onSaved }) {
  const [open, setOpen] = useState(false), [busy, setBusy] = useState(false), [msg, setMsg] = useState("");
  const [day, setDay] = useState(""), [saw, setSaw] = useState(""), [dec, setDec] = useState("");
  const focusAdd = () => setTimeout(() => /** @type {HTMLElement | null} */ (document.querySelector("#uRevAdd"))?.focus(), 0);
  const start = () => { if (held) return; setDay(fd(TODAY)); setSaw(""); setDec(""); setMsg(""); setOpen(true);
    setTimeout(() => /** @type {HTMLElement | null} */ (document.querySelector("#uRevSaw"))?.focus(), 0); };
  const close = () => { setOpen(false); focusAdd(); };
  const save = async () => {
    const date = readDate(day);
    if (!date) return setMsg("Write the date as DD-MM-YYYY.");
    if (!saw.trim() && !dec.trim()) return setMsg("Write what you saw or what you decided.");
    setBusy(true); setMsg("");
    const r = await api(REVIEW_ROUTE, { date, saw, decided: dec }); setBusy(false);
    if (!r || !r.ok) return setMsg(r && r.message === OLDSERVER ? `${NEEDS_UPDATE}.` : (r && r.message) || "Not saved.");
    onSaved(r.reviews || []); setOpen(false); snack("Review note saved"); focusAdd();
  };
  const keys = (/** @type {KeyboardEvent} */ e) => {
    if (e.key === "Enter") { e.preventDefault(); save(); } else if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); close(); } };
  const val = (/** @type {Event} */ e) => /** @type {HTMLInputElement} */ (e.currentTarget).value;
  const rows = list.slice().reverse(), none = !rows.length;
  return (
    <section class="urev" aria-labelledby="uRevH">
      <h2 id="uRevH">Your reviews</h2>
      <p class="sub">Write down what you decided after looking, so the trend has a story. Your own note and a date only; kept on this laptop.</p>
      {none ? <p class="sub uempty" role="status">No review notes yet.</p> : (
        <div class="tbl"><table class="qtab" aria-label="Your reviews">
          <thead><tr><th scope="col">Date</th><th scope="col">What you saw</th><th scope="col">What you decided</th></tr></thead>
          <tbody>{rows.map((r, i) => <tr key={`${r.date}-${i}`}><td>{fd(r.date)}</td><td>{r.saw}</td><td>{r.decided}</td></tr>)}</tbody>
        </table></div>)}
      {open ? (
        <div class="urevform" id="uRevForm" role="group" aria-label="New review note" onKeyDown={keys}>
          <label for="uRevDate">Date</label>
          <input type="text" id="uRevDate" class="urevdate" size={11} maxLength={20} placeholder="DD-MM-YYYY" value={day} onInput={e => setDay(val(e))} />
          <label for="uRevSaw">What you saw</label>
          <input type="text" id="uRevSaw" maxLength={MAX_NOTE} value={saw} onInput={e => setSaw(val(e))} />
          <label for="uRevDec">What you decided</label>
          <input type="text" id="uRevDec" maxLength={MAX_NOTE} value={dec} onInput={e => setDec(val(e))} />
          <span />
          <div class="urevact">
            <button type="button" class="btn primary" id="uRevSave" disabled={busy} onClick={save}>{busy ? "Saving…" : "Save note"}</button>
            <button type="button" class="btn" disabled={busy} onClick={close}>Cancel</button>
            <span class="sub" id="uRevMsg" role="status">{msg}</span>
          </div>
        </div>) : null}
      <div class="urevact">
        {open ? null : <button type="button" class="btn" id="uRevAdd" aria-disabled={held ? "true" : undefined} data-tip={held || undefined}
          aria-label={held ? `Add a review note: ${held.toLowerCase()}` : undefined} onClick={start}>Add a review note</button>}
        <button type="button" class="btn" id="uRevCsv" aria-disabled={none ? "true" : undefined} data-tip={none ? "No review notes yet" : undefined}
          onClick={() => { if (!none) saveFile(reviewsCsv(list, fd), `${TODAY} creaite usage reviews.csv`); }}>Download as CSV</button>
      </div>
    </section>
  );
}
/* ===== end v2.5.3 ===== */

/** @param {{usage: Usage | null | undefined, fd: (s: string) => string, live?: boolean, onReviews?: (list: Review[]) => void}} p */
export function UsagePanel({ usage, fd, live = false, onReviews = () => {} }) {
  const u = usage || {};
  const bad = !usage || usage.error;
  return (
    <>
      <p class="sub">Last {u.days || 14} days, as counted by the live server for each Claude run. Counts only: never the text of a message, a note or a name.
        Internal; nothing leaves this laptop. Tokens loaded at start are what each run reported; the others are estimates (bytes ÷ 4).</p>
      {bad || u.empty ? <p class="sub uempty" role="status">{bad ? "The usage figures couldn't be read." : "No runs yet. Each Claude run the live server makes will be counted here."}</p>
        : <Runs u={u} fd={fd} />}
      <Loads rows={u.context || []} start={u.cards?.start?.now} fd={fd} />
      {bad || u.empty ? null : <Skills skills={u.skills || []} />}
      <Reviews list={u.reviews || []} fd={fd} held={!live ? NEEDS_LIVE : u.reviews_save ? "" : NEEDS_UPDATE} onSaved={onReviews} />
    </>
  );
}

/** @param {Element | null} host @param {{usage: Usage | null | undefined, fd: (s: string) => string, live?: boolean, onReviews?: (list: Review[]) => void}} props */
export function mountUsage(host, props) { if (host) render(<UsagePanel {...props} />, host); }
