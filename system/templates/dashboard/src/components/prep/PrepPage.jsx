// @ts-check
/* PrepPage (BL-286 part D): a meeting's prep page inside creaite, Meetings › Prep (#prep=<key>), in the Briefing layout.
   Everything comes from /api/prep/view (the model prep_view.assemble makes, the same one the Agendas file is rendered from):
   Claude never runs to show it. The header (breadcrumb, title, Internal, chips; Change focus, Refresh research, Draft agenda;
   where it was saved, Open the file, Print; the Prep, Invite and History tabs), then three columns: a sticky outline with
   the series' dates, the centre (the focus band, the work items in focus, the researched notes, the questions) and the context
   rail (dated reporting, this series, the sources as typed links). One column below 1000 px.
   The only writes are the server's own: the focus notes edited in place (/api/prep/focus/save, prep-focus.json) and Refresh
   research (the Prep page run, which stores the content and saves the Agendas file). Items open the peek (data-open), files
   open through /api/open (data-openfile), mail and Teams by the web link the sweep kept. Dates DD-MM-YYYY; projects by name. */
import { render } from "preact";
import { useEffect, useState } from "preact/hooks";
import { Chip } from "../Chip.jsx";
import { Icon } from "../Icon.jsx";
import { StatusDot } from "../StatusDot.jsx";
import { Tabs, panelId, tabId } from "../Tabs.jsx";
import { $ } from "../../core/dom.js";
import { openWork, tabTitle } from "../../core/nav.js";
import { D, fd, mScroll, TODAY } from "../../core/page.js";
import { snack, viaServer } from "../../core/server.js";
import { draftAgenda, hubFor, prepOpen, prepPage } from "../../meetings.js";
import { openPrep } from "../../projects.js";
import { kOfId } from "../../work.js";
import { linesFrom, loadPrep, prepViewKey, prepLoading, prepSaving, prepTab, prepView, saveFocus } from "../../stores/prep.js";


const SECTIONS = [["objective", "Objective"], ["talking_points", "Talking points"], ["ask", "Ask"], ["carried_over", "Carried over"]];
const OUTLINE = [["focus", "Focus and notes"], ["work", "Work items"], ["notes", "Researched notes"], ["questions", "Questions and asks"],
  ["reporting", "Latest reporting"], ["sources", "Sources"], ["series", "This series"]];
const FILEKIND = { word: ["Word", "opens in Word"], excel: ["Excel", "opens in Excel"], pdf: ["PDF", "opens the PDF"],
  transcript: ["Transcript", "opens the transcript"], text: ["Notes", "opens the file"], page: ["Page", "opens the page"], file: ["File", "opens the file"] };
const plural = (n, one, many) => `${n} ${n === 1 ? one : (many || one + "s")}`;
/** The section's element on this page, scrolled to (the address stays the prep page's).
    @param {string} id */
const jump = id => { const el = document.getElementById(`pp-${id}`); if (el) { mScroll(el, { block: "start" }); el.focus({ preventScroll: true }); } };

/** A meeting's calendar entry (for the popup's Change focus and Draft agenda), or null.
    @param {any} mt */
function eventOf(mt) {
  const day = (((D.calendar || {}).days || {})[mt.day] || []);
  return day.find(e => e.start === mt.start && e.title === mt.title) || null;
}

/** The Prep brief's own form of the key: today's meeting undated, any other day dated (as prepKey() in projects.js).
    @param {string} key */
const briefKey = key => key.startsWith(TODAY + "|") ? key.slice(11) : key;

/** One typed source as a link: a file through /api/open, mail or Teams by its web link, an item in the peek; plain text when
    there is nothing to open.
    @param {{s: import("../../stores/prep.js").Typed, label?: string, cite?: boolean}} props */
export function SourceLink({ s, label, cite }) {
  if (!s) return null;
  const text = label || s.label || s.id || "";
  const cls = cite ? "ppcite" : "pplink";
  if (s.type === "file" && s.path) return <a href="#" class={cls} data-openfile={s.path} data-tip={`${FILEKIND[s.kind || "file"]?.[1] || "opens the file"}: ${s.path}`}>{text}</a>;
  if ((s.type === "mail" || s.type === "teams") && s.url) return <a href={s.url} class={cls} target="_blank" rel="noopener noreferrer" data-tip={s.type === "mail" ? "Opens in Outlook" : "Opens in Teams"}>{text}</a>;
  if (s.type === "item" && s.id) { const k = kOfId(s.id); return k ? <a href="#" class={cls} data-open={`${k}:${s.id}`} data-tip="Opens the item">{text}</a> : <span class={cls}>{text}</span>; }
  return <span class={cite ? "ppcite plain" : ""}>{text}</span>;
}

/** The source's icon and the words that say how it opens, for the Sources card.
    @param {import("../../stores/prep.js").Typed} s @returns {[string, string]} */
function ppSrcKind(s) {
  if (s.type === "file") return ["filetext", `${(s.path || "").split("/").slice(-2, -1)[0] || "File"} · ${FILEKIND[s.kind || "file"]?.[1] || "opens the file"}`];
  if (s.type === "mail") return ["mail", s.url ? "Opens in Outlook" : "Mail · no link was kept"];
  if (s.type === "teams") return ["chat", s.url ? "Opens in Teams" : "Teams · no link was kept"];
  if (s.type === "item") return ["work", "Opens the item"];
  if (s.type === "tracker") return ["work", "The tracker"];
  if (s.type === "invite") return ["calendar", "The calendar invite"];
  return ["list", ""];
}

function Header({ v, researching }) {
  const mo = v.model, mt = mo.meeting, people = (mo.brief || {}).people || {}, series = (mo.brief || {}).series || {};
  const hub = hubFor({ day: mt.day, start: mt.start, title: mt.title });
  const ev = eventOf(mt), past = mt.day < TODAY;
  const inv = people.invitees || [];
  const popup = (/** @type {boolean} */ agenda) => {
    if (!ev || past) { snack(past ? "That meeting has passed: prep is for today and the days ahead" : "This meeting isn't in the saved calendar"); return; }
    openPrep(ev, mt.day);
    if (agenda) draftAgenda();
  };
  const refresh = () => {
    if (!viaServer()) { snack("Refreshing the research needs the live server"); return; }
    if (past) { snack("That meeting has passed: prep is for today and the days ahead"); return; }
    const key = prepViewKey.value;
    prepPage(briefKey(key), { quiet: true, status: t => { prepSaving.value = t ? `research:${t}` : ""; }, done: () => loadPrep(key, { keepTab: true }) });
  };
  const printIt = () => { document.documentElement.classList.add("pp-print"); try { window.print(); } finally { document.documentElement.classList.remove("pp-print"); } };
  const tabs = [{ id: "prep", label: "Prep" }, { id: "invite", label: "Invite" },
    { id: "history", label: `History${(mo.series.meetings || []).length > 1 ? ` (${mo.series.meetings.length - 1})` : ""}` }];
  return (
    <header class="pph">
      <nav class="crumb" aria-label="Breadcrumb">
        <a href="#" data-go="today">Today</a> › {hub ? <a href={`#meeting=${hub}`} data-meeting={hub}>Meetings</a> : <span>Meetings</span>} › <span aria-current="page">Prep</span>
      </nav>
      <h1 id="ppTitle">{mt.title}</h1>
      <div class="ppmeta">
        <span class="tag ppint" data-tip="Your preparation: not for the client, never sent">Internal</span>
        <Chip icon="calendar" name="When">{mt.day_shown}{mt.start ? ` · ${mt.start}${mt.end ? ` – ${mt.end}` : ""}` : ""}</Chip>
        {mt.project_name ? <Chip name="Project">{mt.project_name}</Chip> : null}
        {!mt.confidential && series.text ? <Chip icon="history" name="Series">{series.text}</Chip> : null}
        {!mt.confidential && inv.length ? (
          <Chip name="Invited" cls="ppwho">
            <span class="ppavs" aria-hidden="true">{inv.slice(0, 3).map(p => <span class="av" key={p.name}>{p.initials}</span>)}{inv.length > 3 ? <span class="av">+{inv.length - 3}</span> : null}</span>
            {plural(inv.length, "invited", "invited")}
          </Chip>) : null}
      </div>
      <div class="ppacts">
        <button type="button" class="btn ppai" onClick={() => popup(false)} data-tip="Shape this meeting around a focus, in the Prep popup"><Icon name="spark" />Change focus</button>
        <button type="button" class="btn" onClick={refresh} disabled={!!researching} data-tip="Research the meeting again and save a new Agendas page"><Icon name="refresh" />Refresh research</button>
        <button type="button" class="btn" onClick={() => popup(true)} data-tip="Draft the invite text and a timed agenda"><Icon name="filetext" />Draft agenda</button>
        {researching ? <span class="sub pprun" role="status"><span class="spin"></span> {researching} <button type="button" class="mini" data-prepstop>Stop</button></span> : null}
        <span class="ppsp"></span>
        <span class="sub" role="status">{v.saved ? `Saved to Agendas · ${v.saved.at_shown}` : "Not saved to Agendas yet"}</span>
        {v.saved ? <button type="button" class="btn" onClick={() => prepOpen(v.saved.path)} data-tip={v.saved.path}><Icon name="external" />Open the file</button> : null}
        <button type="button" class="btn" onClick={printIt}>Print</button>
      </div>
      <Tabs tabs={tabs} selected={prepTab.value} onSelect={id => { prepTab.value = id; }} label="Prep page" idBase="pp" cls="pptabs" />
    </header>
  );
}

function Outline({ mo }) {
  const earlier = (mo.series.meetings || []).filter(x => !x.this);
  return (
    <nav class="ppoutline" aria-label="On this page">
      {OUTLINE.map(([id, label]) => <a href="#" key={id} onClick={e => { e.preventDefault(); jump(id); }}>{label}</a>)}
      {earlier.length ? <><div class="sub ppolh">This series</div>{earlier.slice(0, 6).map(x => <a href="#" key={x.day} onClick={e => { e.preventDefault(); jump("series"); }}>{x.day_shown}</a>)}</> : null}
    </nav>
  );
}

/** One section's box: the lines as text, saved when the box is left with a change.
    @param {{sec: string, label: string, lines: import("../../stores/prep.js").NoteLine[], onSave: (sec: string, text: string) => void}} props */
function NoteBox({ sec, label, lines, onSave }) {
  const start = lines.map(l => l.text).join("\n");
  const [text, setText] = useState(start);
  useEffect(() => { setText(start); }, [start]);
  const cites = lines.flatMap(l => l.sources || []).filter((s, i, a) => a.findIndex(x => (x.path || x.url || x.id || x.label) === (s.path || s.url || s.id || s.label)) === i);
  return (
    <div class="ppnote">
      <label for={`pp-n-${sec}`}>{label}</label>
      <textarea id={`pp-n-${sec}`} class="ppbox" rows={Math.max(2, lines.length + 1)} value={text}
        onInput={e => setText(/** @type {HTMLTextAreaElement} */ (e.currentTarget).value)}
        onBlur={e => { const now = /** @type {HTMLTextAreaElement} */ (e.currentTarget).value; if (now.trim() !== start.trim()) onSave(sec, now); }} />
      {cites.length ? <div class="ppcites">{cites.slice(0, 6).map((s, i) => <SourceLink key={i} s={s} cite />)}</div> : null}
    </div>
  );
}

function FocusBand({ mo, saving }) {
  const f = mo.focus || {}, reading = f.reading || {}, notes = f.notes || {};
  const focusText = (reading.focus || []).map(x => x.id ? `${x.id}${x.text && x.text !== x.id ? ` · ${x.text}` : ""}` : x.text).filter(Boolean).join("; ");
  const shaped = SECTIONS.some(([k]) => (notes[k] || []).length);
  const save = (sec, text) => {
    /** @type {Record<string, import("../../stores/prep.js").NoteLine[]>} */
    const all = {};
    SECTIONS.forEach(([k]) => { all[k] = k === sec ? linesFrom(text, notes[k]) : (notes[k] || []); });
    saveFocus({ notes: all }, "notes");
  };
  return (
    <section class="ppfocus" id="pp-focus" tabIndex={-1} aria-labelledby="pp-h-focus">
      <h2 id="pp-h-focus"><Icon name="spark" />{focusText ? `Focus: ${focusText}` : "Focus and notes"}</h2>
      {reading.aim ? <p class="ppaim"><b>Aim:</b> {reading.aim}</p> : null}
      {shaped ? <>
        <div class="ppnotes">{SECTIONS.map(([k, label]) => <NoteBox key={k} sec={k} label={label} lines={notes[k] || []} onSave={save} />)}</div>
        <p class="sub ppstamp" role="status">{saving === "notes" ? "Saving…" : `Your notes${f.accepted_at ? `, accepted ${fd(f.accepted_at)}` : ""} · edit here; drag a box's corner to make it bigger`}</p>
      </> : <p class="sub">Nothing has been shaped for this meeting yet. Change focus to say what it should settle; the notes appear here.</p>}
    </section>
  );
}

function WorkCard({ mo }) {
  const w = mo.work, rows = w.rows || [], code = mo.meeting.project, focus = w.mode !== "all";
  const show = (/** @type {string} */ to) => saveFocus({ reading: { ...((mo.focus || {}).reading || {}), show: to } }, "show");
  return (
    <section class="card pc" id="pp-work" tabIndex={-1} aria-labelledby="pp-h-work">
      <h2 id="pp-h-work">{focus ? "Work items in focus" : "Work items"}
        {focus ? <span class="sub"> · {w.n} of {w.N} · {w.mode === "focus-only"
          ? <button type="button" class="linkbtn" onClick={() => show("focus-first")}>show all</button>
          : <button type="button" class="linkbtn" onClick={() => show("focus-only")}>focus only</button>}</span> : null}
      </h2>
      {rows.length ? (
        <div class="pptblwrap"><table class="ppwi">
          <thead><tr><th scope="col">ID</th><th scope="col">Item</th><th scope="col">Owner</th><th scope="col">Due</th><th scope="col">Why it's here</th></tr></thead>
          <tbody>{rows.map(i => {
            const k = ["actions", "raid", "decisions"].includes(i.table) ? i.table : kOfId(i.id);
            const late = i.due && i.due < TODAY && !/^(Done|Closed|Cancelled|Made|Withdrawn)$/.test(i.status || "");
            const why = (Array.isArray(i.why) ? i.why : [i.why]).filter(Boolean);
            return (
              <tr key={i.id} class={`${k ? "click" : ""}${i.in_focus ? " infocus" : ""}`} data-open={k ? `${k}:${i.id}` : undefined}>
                <td class="ppid">{k ? <a href="#" data-open={`${k}:${i.id}`}>{i.id}</a> : i.id}</td>
                <td>{i.text}<div class="sub">{[i.type, i.p && i.p !== code ? i.p : ""].filter(Boolean).join(" · ")}</div></td>
                <td>{i.owner || <span class="sub">Not set</span>}</td>
                <td class={late ? "late" : ""}>{i.due ? fd(i.due) : "—"}{late ? <div class="sub late">overdue</div> : null}</td>
                <td>{why.map((x, n) => <span class="ppwhy" key={n}>{x}</span>)}</td>
              </tr>);
          })}</tbody>
        </table></div>
      ) : <p class="sub">Nothing is Urgent, overdue or due soon.</p>}
      {!focus && w.not_listed ? <p class="sub">{plural(w.not_listed, "other open item is", "other open items are")} not listed. <button type="button" class="linkbtn" onClick={() => openWork(code === "_portfolio" ? "" : code, "actions", "open")}>Show {w.not_listed === 1 ? "it" : "them"} in Work</button></p> : null}
      {(w.documents || []).filter(d => !d.excluded).length ? <>
        <h3>Documents in focus <span class="sub">· {w.docs_n} of {w.docs_N}</span></h3>
        <ul class="ppdocs">{w.documents.filter(d => !d.excluded).map(d => <li key={d.path}><SourceLink s={{ type: "file", path: d.path, label: d.name, kind: "file" }} /> <span class="sub">{(d.why || []).join("; ")}</span></li>)}</ul>
      </> : null}
    </section>
  );
}

function NotesCard({ v }) {
  const mo = v.model;
  return (
    <section class="card pc" id="pp-notes" tabIndex={-1} aria-labelledby="pp-h-notes">
      <h2 id="pp-h-notes">Researched notes</h2>
      {mo.about ? <p>{mo.about}</p> : null}
      {mo.notes.length ? <ul class="ppnl">{mo.notes.map((n, i) => (
        <li key={i}>{n.text} {n.source && (n.source.type === "file" || n.source.url || n.source.type === "item")
          ? <SourceLink s={n.source} label={`${n.source.label || n.source_text}${n.date_shown ? `, ${n.date_shown}` : ""}`} cite />
          : <span class="ppcite plain">{n.source_text}{n.date_shown ? `, ${n.date_shown}` : ""}</span>}</li>))}</ul>
        : <p class="sub">{v.stored ? "Nothing found." : "Not researched yet. Refresh research reads the minutes, documents, mail and Teams for this meeting."}</p>}
      {(mo.carried || []).length ? <>
        <h3>Not covered last time</h3>
        <ul class="ppnl">{mo.carried.map((c, i) => <li key={i}>{c.point} <span class="sub">{c.title}{c.day ? `, ${fd(c.day)}` : ""}</span></li>)}</ul>
      </> : null}
    </section>
  );
}

/** Questions and asks, editable: one a line, saved when the box is left with a change (prep-focus.json, beside the notes),
    so Refresh research and Regenerate keep them. "Use creaite's questions" gives back the research's.
    @param {{mo: any, saving: string}} props */
function QuestionsCard({ mo, saving }) {
  const start = (mo.questions || []).join("\n");
  const [text, setText] = useState(start);
  useEffect(() => { setText(start); }, [start]);
  return (
    <section class="card pc" id="pp-questions" tabIndex={-1} aria-labelledby="pp-h-questions">
      <h2 id="pp-h-questions">Questions and asks</h2>
      <label class="vh" for="pp-q">Questions and asks, one a line</label>
      <textarea id="pp-q" class="ppbox" rows={Math.max(3, (mo.questions || []).length + 1)} value={text} placeholder="One question or ask a line"
        onInput={e => setText(/** @type {HTMLTextAreaElement} */ (e.currentTarget).value)}
        onBlur={e => { const now = /** @type {HTMLTextAreaElement} */ (e.currentTarget).value; if (now.trim() !== start.trim()) saveFocus({ questions: now.split("\n").map(x => x.trim()).filter(Boolean) }, "questions"); }} />
      <p class="sub ppstamp" role="status">{saving === "questions" ? "Saving…" : mo.questions_edited
        ? <>Your questions · <button type="button" class="linkbtn" onClick={() => saveFocus({ questions: null }, "questions")}>Use creaite's questions</button></>
        : "One a line; edit here, and leaving the box saves them"}</p>
    </section>
  );
}

function ReportingCard({ mo }) {
  const many = mo.reporting.length > 1;
  return (
    <section class="card pc" id="pp-reporting" tabIndex={-1} aria-labelledby="pp-h-reporting">
      <h2 id="pp-h-reporting"><Icon name="filetext" />Latest reporting</h2>
      {mo.reporting.length ? mo.reporting.map(r => (
        <div class="pprep" key={r.project}>
          {many ? <div class="pprepname">{r.name}</div> : null}
          <div class="pprephead">{r.week_ending ? <><b>Weekly report</b><span class="sub">week ending {fd(r.week_ending)}</span></> : <span class="sub">No weekly report yet</span>}
            {r.health ? <StatusDot health={r.health} /> : null}</div>
          {r.headline ? <p class="pphl">{r.headline}</p> : r.summary ? <p class="pphl">{r.summary}</p> : null}
          {(r.points || []).length ? <ul>{r.points.map((p, i) => <li key={i}>{p}</li>)}</ul> : null}
          {(r.reports || []).map(x => x.online
            ? <div class="ppsrc" key={x.name}><Icon name="filetext" /><span><span class="nm">{x.kind} · {x.date_shown}</span><span class="sub">{x.name}: online-only, not available</span></span></div>
            : <a href="#" class="ppsrc" key={x.name} data-openfile={x.link.path}><Icon name="filetext" /><span><span class="nm">{x.kind} · {x.date_shown}</span><span class="sub">{x.name}</span></span><span class="go">Open ↗</span></a>)}
        </div>)) : <p class="sub">Nothing found.</p>}
    </section>
  );
}

/** @param {{mo: any, all?: boolean}} props */
function SeriesCard({ mo, all }) {
  const [more, setMore] = useState(false);
  const list = mo.series.meetings || [], cut = all || more ? list : list.slice(0, 4);
  const cad = ((mo.brief || {}).series || {}).cadence;
  return (
    <section class="card pc" id={all ? "pp-history" : "pp-series"} tabIndex={-1} aria-labelledby={all ? "pp-h-history" : "pp-h-series"}>
      <h2 id={all ? "pp-h-history" : "pp-h-series"}><Icon name="history" />This series{cad ? <span class="sub"> · {cad.toLowerCase()}</span> : null}</h2>
      {list.length > 1 ? <ol class="pptl">{cut.map(x => {
        const r = x.raised || {};
        const counts = x.this ? "" : [plural(r.actions || 0, "action"), plural(r.decisions || 0, "decision"), r.raid ? plural(r.raid, "risk or issue", "risks and issues") : ""].filter(Boolean).join(", ") + ` raised · ${x.not_covered || 0} not covered`;
        return (
          <li key={x.day} class={x.this ? "this" : ""}>
            <b>{x.day_shown}{x.this ? " · this one" : ""}</b>
            {counts ? <span class="sub">{counts}</span> : null}
            {x.minutes || (x.prep && !x.this) ? <span class="pptll">
              {x.minutes ? <SourceLink s={x.minutes} label="Minutes ↗" /> : null}
              {x.minutes && x.prep && !x.this ? " · " : null}
              {x.prep && !x.this ? <a href="#" data-mhprep={x.prep}>Prep page ↗</a> : null}
            </span> : null}
          </li>);
      })}</ol> : <p class="sub">No earlier meetings in this series that creaite knows of.</p>}
      {!all && list.length > 4 ? <button type="button" class="linkbtn" aria-expanded={more ? "true" : "false"} onClick={() => setMore(!more)}>{more ? "Fewer" : `${list.length - 4} earlier ›`}</button> : null}
    </section>
  );
}

function SourcesCard({ mo }) {
  return (
    <section class="card pc" id="pp-sources" tabIndex={-1} aria-labelledby="pp-h-sources">
      <h2 id="pp-h-sources"><Icon name="external" />Sources <span class="sub">· select to open</span></h2>
      <ul class="ppsrcs">{mo.sources.map((s, i) => {
        const [icon, how] = ppSrcKind(s);
        const body = <><Icon name={icon} /><span><span class="nm">{s.label || s.id}</span>{how ? <span class="sub">{how}</span> : null}</span></>;
        const k = s.type === "item" && s.id ? kOfId(s.id) : null;
        return <li key={i}>{s.type === "file" && s.path ? <a href="#" class="ppsrc" data-openfile={s.path}>{body}<span class="go">↗</span></a>
          : (s.type === "mail" || s.type === "teams") && s.url ? <a href={s.url} class="ppsrc" target="_blank" rel="noopener noreferrer">{body}<span class="go">↗</span></a>
          : k ? <a href="#" class="ppsrc" data-open={`${k}:${s.id}`}>{body}<span class="go">↗</span></a>
          : s.type === "invite" ? <a href="#" class="ppsrc" onClick={e => { e.preventDefault(); prepTab.value = "invite"; }}>{body}</a>
          : <div class="ppsrc">{body}</div>}</li>;
      })}</ul>
    </section>
  );
}

function InvitePanel({ mo }) {
  const mt = mo.meeting, people = (mo.brief || {}).people || {}, org = people.organiser;
  if (mt.confidential) return <section class="card pc"><p>Confidential meeting: only its title and times are kept, so the invite isn't shown.</p></section>;
  return (
    <section class="card pc ppinv">
      <h2>Invite</h2>
      <p class="sub">{mt.day_shown}{mt.start ? `, ${mt.start}${mt.end ? ` – ${mt.end}` : ""}` : ""}{mt.where ? ` · ${mt.where}` : ""}</p>
      {org ? <p><b>Organiser:</b> {org.name}{org.registered ? "" : <span class="sub"> (not in the people register)</span>}</p> : null}
      {(people.invitees || []).length ? <>
        <p><b>Invited ({people.count}):</b></p>
        <ul class="ppppl">{people.invitees.map((p, i) => <li key={i}><span class="av" aria-hidden="true">{p.initials}</span>{p.name}{p.registered ? null : <span class="sub"> · not in the people register</span>}</li>)}</ul>
      </> : <p class="sub">No one else is invited.</p>}
      {mt.body ? <div class="prepbodytxt">{mt.body}</div> : <p class="sub">The invite has no text.</p>}
    </section>
  );
}

/** The whole screen, drawn from the store. */
export function PrepPage() {
  const v = prepView.value, tab = prepTab.value, saving = prepSaving.value;
  if (!v) return <div class="pp"><p class="sub pploading" role="status">{prepLoading.value ? "Loading the prep page…" : ""}</p></div>;
  if (!v.ok) return (
    <div class="pp"><div class="phead"><h1>Prep</h1></div>
      <div class="card"><p>{v.message || "Couldn't load the prep page."}</p><button type="button" class="btn" data-go="today">Back to Today</button></div></div>);
  const mo = v.model, researching = saving.startsWith("research:") ? saving.slice(9) : "";
  return (
    <div class="pp">
      <Header v={v} researching={researching} />
      <div role="tabpanel" id={panelId("pp", "prep")} aria-labelledby={tabId("pp", "prep")} hidden={tab !== "prep"}>
        <div class="ppb">
          <Outline mo={mo} />
          <div class="ppc">
            {!v.stored ? <p class="ppnew" role="status">creaite hasn't researched this meeting yet. <b>Refresh research</b> drafts the notes and questions and saves the page in the project's Agendas folder.</p> : null}
            <FocusBand mo={mo} saving={saving} />
            <WorkCard mo={mo} />
            <NotesCard v={v} />
            <QuestionsCard mo={mo} saving={saving} />
          </div>
          <aside class="pprail" aria-label="Context">
            <ReportingCard mo={mo} />
            <SeriesCard mo={mo} />
            <SourcesCard mo={mo} />
          </aside>
        </div>
      </div>
      <div role="tabpanel" id={panelId("pp", "invite")} aria-labelledby={tabId("pp", "invite")} hidden={tab !== "invite"} class="ppone">
        {tab === "invite" ? <InvitePanel mo={mo} /> : null}
      </div>
      <div role="tabpanel" id={panelId("pp", "history")} aria-labelledby={tabId("pp", "history")} hidden={tab !== "history"} class="ppone">
        {tab === "history" ? <SeriesCard mo={mo} all /> : null}
      </div>
    </div>
  );
}

let pageMounted = false;
/** Show a meeting's prep page in #v-prep (go("prep", key) calls this): mount the screen once, then load the view.
    @param {string} key */
export function renderPrep(key) {
  const el = $("#v-prep");
  if (!el) return;
  if (!pageMounted) { render(<PrepPage />, el); pageMounted = true; }
  if (key) loadPrep(key).then(() => tabTitle());
}
