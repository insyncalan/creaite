// @ts-check
/* PeekProps (BL-316, dev/COMPONENTS.md §3): the peek's key row of property buttons (Status, Priority, Owner, Due date …,
   Impact and Likelihood, a proposal's Project), each a Chip: a full name ("Owner: not set"), aria-haspopup="listbox" for its
   picker, the field's name as the tooltip and data-pkp, which panel.js's click handler, focus keeping and checks read. A RAID
   item's calculated priority is a read-only chip (role="note"). The marks beside the words (a status ring, priority bars,
   initials) are drawn here as elements; the pickers' options use the same marks (peekMark).
   panel.js draws the row afresh each time, as before (peekPropNodes): the nodes are new on every draw, so nothing another
   piece of code marks on a chip (a check's .pkbad, Sneak peek's flash) outlives the draw. Text goes through JSX only. */
import { render } from "preact";
import { Chip } from "../Chip.jsx";
import { Icon } from "../Icon.jsx";

/** @typedef {{st?: string, pr?: string, who?: string, icon?: string}} PeekMark  one of: a status, a priority, a person, an icon
    @typedef {{f: string, name: string, mark: PeekMark, value: string, empty?: boolean, cls?: string, nw?: boolean,
      you?: boolean, late?: boolean, ro?: string, roTip?: string, popup?: string}} PeekProp
    `value` is the words; `nw` keeps them on one line (a date); `you` adds "(you)"; `late` adds the overdue tag; `ro` makes
    it a read-only note with that accessible name (and `roTip` as its tooltip); `popup` what it opens (default "listbox"; a
    date's calendar is a "dialog"). */

const ST_COLOUR = /** @type {Record<string, string>} */ ({ Open: "var(--accent)", Delayed: "var(--warn)", Closed: "var(--ok)",
  Cancelled: "var(--faint)", Pending: "var(--muted)", Made: "var(--ok)", Withdrawn: "var(--faint)" });
const TICK = "M8 12.5l3 3 5-6", CROSS = "M9 9l6 6M15 9l-6 6";
const ST_INNER = /** @type {Record<string, any>} */ ({ Open: { d: "M12 4a8 8 0 0 1 0 16z", fill: "currentColor", stroke: "none" },
  Delayed: { d: "M12 8v4l2.5 1.5" }, Closed: { d: TICK }, Cancelled: { d: CROSS }, Made: { d: TICK }, Withdrawn: { d: CROSS } });
const PR_N = /** @type {Record<string, number>} */ ({ Urgent: 4, High: 3, Medium: 2, Low: 1 });
const PR_COLOUR = /** @type {Record<string, string>} */ ({ Urgent: "var(--bad)", High: "var(--warn)", Medium: "var(--accent)", Low: "var(--faint)" });

/** The status ring. @param {{st: string}} props */
function StatusRing({ st }) {
  const inner = ST_INNER[st];
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" style={`color:${ST_COLOUR[st] || "var(--muted)"}`}
      stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="8" stroke-dasharray={st === "Pending" ? "3 3" : undefined} />{inner ? <path {...inner} /> : null}
    </svg>
  );
}

/** The priority bars. @param {{pr: string}} props */
function PriorityBars({ pr }) {
  const n = PR_N[pr] || 0, c = PR_COLOUR[pr] || "var(--faint)";
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      {[0, 1, 2, 3].map(i => <rect key={i} x={String(3 + i * 5)} y={String(16 - i * 4)} width="3.4" height={String(4 + i * 4)} rx="1" fill={c} opacity={i < n ? "1" : ".25"} />)}
    </svg>
  );
}

/** A person's initials, or the person icon when nobody is set. @param {{who: string}} props */
function Initials({ who }) {
  if (!who) return <Icon name="user" />;
  const i = who.split(/\s+/).map(w => w[0] || "").join("").slice(0, 2).toUpperCase();
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <circle cx="12" cy="12" r="10" fill="var(--accent-soft)" />
      <text x="12" y="15.5" text-anchor="middle" font-size="9.5" font-weight="600" fill="var(--accent)" font-family="inherit">{i}</text>
    </svg>
  );
}

/** @param {{mark: PeekMark}} props */
function Mark({ mark }) {
  if (mark.st != null) return <StatusRing st={mark.st} />;
  if (mark.pr != null) return <PriorityBars pr={mark.pr} />;
  if (mark.who != null) return <Initials who={mark.who} />;
  return <Icon name={mark.icon || "pencil"} />;
}

/** One property: `<div class="pk-prop">` holding its chip.
    @param {{p: PeekProp}} props */
function Prop({ p }) {
  const words = <span>{p.nw ? <span class="nw">{p.value}</span> : p.value}{p.you ? <> <small class="sub">(you)</small></> : null}{p.late ? <> <em>overdue</em></> : null}</span>;
  const plain = `${p.value}${p.you ? " (you)" : ""}${p.late ? " overdue" : ""}`;
  if (p.ro) return <div class="pk-prop"><Chip cls="pk-chip ro" role="note" aria-label={p.ro} tip={p.roTip}><Mark mark={p.mark} />{words}</Chip></div>;
  return (
    <div class="pk-prop">
      <Chip button cls={["pk-chip", p.empty ? "empty" : "", p.cls || ""].filter(Boolean).join(" ")} data-pkp={p.f} aria-haspopup={/** @type {any} */ (p.popup || "listbox")}
        name={`${p.name}: ${p.empty ? "not set" : plain}`} tip={p.name}><Mark mark={p.mark} />{words}</Chip>
    </div>
  );
}

/** A mark as a vnode, for the Picker's options (a status ring, priority bars, initials or an icon). @param {PeekMark} mark */
export function peekMark(mark) { return <Mark mark={mark} />; }

/** The properties as new nodes, for panel.js to put in place of the old ones.
    @param {PeekProp[]} list @returns {ChildNode[]} */
export function peekPropNodes(list) {
  const box = document.createElement("div");
  render(<>{list.map(p => <Prop key={p.f} p={p} />)}</>, box);
  return [...box.childNodes];
}
