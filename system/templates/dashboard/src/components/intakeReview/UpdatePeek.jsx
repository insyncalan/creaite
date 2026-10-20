// @ts-check
/* UpdatePeek (#232-B, release 2.6): what an update proposal shows in the peek, beside the title and the feed panel.js draws. An
   update proposal opens the whole item as it is now, with the changes marked: a changed chip reads `was → now` on a warm
   background, the note says "What changes if you approve", a changed latest update (or response, or reasoning) shows the old text
   struck and the new highlighted, and "Last updated" ends the item. The words all come from core/irUpdate.js's one list, so the
   chips, the note and the "If approved" line in the activity cannot disagree.
   Editable here: Status, Due (their chips open the app's own pickers) and the Latest update (the peek's text field). Every other
   chip shows `was → now` and is read-only (those change through cx-edit). Internal only: client message text is never shown, only
   that it changes. Text goes through JSX only; panel.js puts the chips in place of the peek's own and renders the body.
   Tokens and the app's own classes only (style.css, "#232-B"). */
import { render } from "preact";
import { Chip } from "../Chip.jsx";
import { peekMark } from "../peek/PeekProps.jsx";
import { fd } from "../../core/page.js";
import { EDITABLE, irChanged, irLabel, irNoteText, irPhrase } from "../../core/irUpdate.js";

/** @typedef {{col: string, label: string, was: any, now: any, same: boolean, proposed: boolean}} UpdateChange */
/** @typedef {{f: string, name: string, mark: import("../peek/PeekProps.jsx").PeekMark, was: string, now: string, changed: boolean, editable: boolean, popup?: string, empty?: boolean}} UpdateChip */

/** The conflict's before and after (the app's .cfvs block): the same wording as the Review row.
    @param {{rec: any}} props */
export function ConflictBlock({ rec }) {
  const ch = rec.changes && rec.changes.length ? rec.changes : rec.field ? [{ field: rec.field, from: rec.from, to: rec.to }] : [];
  const v = (/** @type {any} */ x) => (x == null || x === "" ? "(empty)" : /^\d{4}-\d{2}-\d{2}$/.test(String(x)) ? fd(String(x)) : String(x));
  const isCm = (/** @type {any} */ c) => c.col === "client_message" || /^client messag/i.test(String(c.field || ""));      /* the client's wording is never shown: only that it changes */
  return <div class="cfvs">{ch.length ? ch.map((/** @type {any} */ c) => (isCm(c)
    ? <div><span class="cff">{c.field}</span><span class="cfnew">client message: changed (its wording is not shown)</span></div>
    : <div><span class="cff">{c.field}</span><span class="cfnow">Now: <b>{v(c.from)}</b></span><span class="cfnew">This one: <b>{v(c.to)}</b></span></div>
  )) : <div class="sub">Changed in the tracker after this was proposed.</div>}</div>;
}

/** The chips for the item, in the peek's two rows, from the list and the row as it would be.
    @param {string} table
    @param {UpdateChange[]} list
    @param {Record<string, any>} now the row as it would be, under the tracker's column names
    @param {(col: string, v: any) => string} show a value as the peek words it (a project by name, a person by full name)
    @returns {{row1: UpdateChip[], row2: UpdateChip[]}} */
export function updateChips(table, list, now, show) {
  const editable = EDITABLE[table] || [];
  /** @param {string} col @param {string} f @param {string} name @param {import("../peek/PeekProps.jsx").PeekMark} mark @param {string} [popup] @returns {UpdateChip} */
  const chip = (col, f, name, mark, popup) => {
    const c = list.find(x => x.col === col), changed = !!c && !c.same;
    const shownNow = show(col, now[col]);
    return { f, name, mark, was: changed ? show(col, c.was) : shownNow, now: shownNow, changed, editable: editable.includes(col), popup, empty: now[col] == null || now[col] === "" };
  };
  const dueCol = table === "decisions" ? "needed_by" : "due_date", ownerCol = table === "decisions" ? "made_by" : "owner";
  const row1 = [
    chip("status", "st", "Status", { st: String(now.status || "") }),
    chip(ownerCol, "o", table === "decisions" ? "Decision maker" : "Owner", { who: show(ownerCol, now[ownerCol]) === "—" ? "" : show(ownerCol, now[ownerCol]) }),
    chip(dueCol, "due", table === "decisions" ? "Needed by" : "Due date", { icon: "calendar" }, "dialog"),
  ];
  if (table === "actions") row1.push(chip("priority", "pr", "Priority", { pr: String(now.priority || "Medium") }));
  row1.push(chip("project", "p", "Project", { icon: "projects" }));
  /** @type {UpdateChip[]} */
  const row2 = [];
  if (table !== "decisions") row2.push(chip("workstream", "ws", "Workstream", { icon: "layers" }), chip("milestone", "ms", "Milestone", { icon: "flag" }));
  if (table === "raid") row2.push(chip("impact", "imp", "Impact", { icon: "alert" }), chip("likelihood", "lik", "Likelihood", { icon: "alert" }));
  if (table === "decisions" && (now.status === "Made" || list.some(c => c.col === "date"))) row2.push(chip("date", "date", "Date made", { icon: "calendar" }));
  row2.push(chip("client_visible", "client", "Client-visible", { icon: "eye" }));
  return { row1, row2 };
}

/** One chip. @param {{c: UpdateChip}} props */
function UChip({ c }) {
  const words = c.changed ? <span><s>{c.was}</s> → <b>{c.now}</b></span> : <span>{c.now}</span>;
  const label = c.changed ? `${c.name}: was ${c.was}, now ${c.now}` : `${c.name}: ${c.empty ? "not set" : c.now}`;
  const mark = peekMark(c.changed && c.mark.st != null ? { st: c.now } : c.mark);
  const cls = ["pk-chip", c.changed ? "chg" : "", c.empty && !c.changed ? "empty" : ""].filter(Boolean).join(" ");
  if (!c.editable) return <div class="pk-prop"><Chip cls={`${cls} ro`} role="note" aria-label={label} tip={c.changed ? `${c.name}: changes if approved (read-only here)` : `${c.name} (read-only here)`}>{mark}{words}</Chip></div>;
  return <div class="pk-prop"><Chip button cls={cls} data-pkp={c.f} aria-haspopup={/** @type {any} */ (c.popup || "listbox")} name={label} tip={c.changed ? `${c.name}: changes if approved` : c.name}>{mark}{words}</Chip></div>;
}

/** The chips as new nodes, for panel.js to put in place of the peek's own row.
    @param {UpdateChip[]} chips @returns {ChildNode[]} */
export function updateChipNodes(chips) {
  const box = document.createElement("div");
  render(<>{chips.map(c => <UChip key={c.f} c={c} />)}</>, box);
  return [...box.childNodes];
}

/** The old text struck, the new highlighted (the mockup's .updiff). @param {{label?: string, was: any, now: any}} props */
function TextDiff({ label, was, now }) {
  return (
    <div class="updiff">
      {label ? <div class="pk-dl">{label}</div> : null}
      <div class="old"><span class="icsub">Now</span> {was == null || was === "" ? <i>not set</i> : <s>{String(was)}</s>}</div>
      <div class="new"><span class="tag">New</span> {now == null || now === "" ? <i>not set</i> : String(now)}</div>
    </div>
  );
}

/** The columns whose text is shown as a diff block, with the words of their label: wording that is read-only here, and the
    old latest update above the field that edits the new. Client messaging is never shown, only that it changes. */
const DIFF_TEXT = ["description", "decision", "response_action", "reasoning", "options"];

/** The body between the chips and the description: a conflict, the wording that changes, and the note.
    @param {{id: string, title: string, table: string, list: UpdateChange[], rec: any, conflict: boolean, current: Record<string, any>}} props */
export function UpdateBody({ id, title, table, list, rec, conflict, current }) {
  const changed = irChanged(list), diffs = changed.filter(c => DIFF_TEXT.includes(c.col));
  const plain = (table === "raid" ? "response_action" : table === "decisions" ? "reasoning" : "");
  const shownPlain = plain && !changed.some(c => c.col === plain) && current[plain] ? current[plain] : "";
  const cm = changed.some(c => c.col === "client_message");
  return (
    <>
      {conflict ? <><div class="pk-dl">This proposal and the tracker disagree</div><ConflictBlock rec={rec} /></> : null}
      {diffs.map(c => <TextDiff key={c.col} label={irLabel(c.col)} was={c.was} now={c.now} />)}
      {cm ? <div class="pk-dl">The client messaging changes (its wording is not shown here)</div> : null}
      {shownPlain ? <><div class="pk-dl">{irLabel(plain)}</div><div class="pk-updtext">{String(shownPlain)}</div></> : null}
      <div class="pk-note" id="pkUpdNote" role="status"><NoteWords id={id} title={title} changed={changed} /></div>
    </>
  );
}

/** "What changes if you approve: ABC-A-002 · Book UAT environment: due date 20-10-2026 → 23-10-2026 and the latest update. The
    rest of the item stays as it is." Its text is irNoteText, with the changes in bold (the test compares the two).
    @param {{id: string, title: string, changed: UpdateChange[]}} props */
function NoteWords({ id, title, changed }) {
  const what = [id, title].filter(Boolean).join(" · ");
  if (!changed.length) return <>{irNoteText(id, title, changed)}</>;
  return (
    <>
      <b>What changes if you approve</b>: {what}: {changed.map((c, i) => {
        const p = irPhrase(c);
        return <>{i ? " and " : ""}{p.text ? p.label : <>{p.label} <b>{p.delta}</b></>}</>;
      })}. The rest of the item stays as it is.
    </>
  );
}

/** The old latest update above the field that edits the new one (an action's), when the proposal or Alan changes it.
    @param {{was: any, changed: boolean}} props */
function LatestWas({ was, changed }) {
  return changed ? <div class="updiff"><div class="old"><span class="icsub">Now</span> {was == null || was === "" ? <i>not set</i> : <s>{String(was)}</s>}</div></div> : null;
}

/** "Last updated 10-10-2026 16:20", then the activity's heading. @param {{id: string, at: string}} props */
function Last({ id, at }) {
  return <><div class="pk-dl">Last updated {at ? fd(at) : "—"}</div><div class="pk-dl pk-updact">Activity on {id}</div></>;
}

/** Draw the body into its host (a div panel.js made, which only this renders into).
    @param {Element} host @param {Parameters<typeof UpdateBody>[0] | null} props */
export function drawUpdateBody(host, props) { render(props ? <UpdateBody {...props} /> : null, host); }

/** Draw the old latest update into its host. @param {Element} host @param {{was: any, changed: boolean} | null} props */
export function drawLatestWas(host, props) { render(props ? <LatestWas {...props} /> : null, host); }

/** Draw "Last updated" into its host. @param {Element} host @param {{id: string, at: string} | null} props */
export function drawLast(host, props) { render(props ? <Last {...props} /> : null, host); }
