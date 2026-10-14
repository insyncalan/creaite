// @ts-check
/* PrepFacts (BL-286 part A): the facts line and the invite, at the top of the Prep popup.
   The facts line: "Since the last meeting (29-09-2026): 3 decisions, 1 new risk, 2 actions now overdue", plus how many
   items the invite puts first. The live server's counts (/api/prep/brief) when it has answered; the same counts from the
   page's own data until then, or without it.
   The invite, collapsed to one line: who organised it and who is invited, by name (the people register resolves
   addresses; a name made from an address the register doesn't know is marked), and the invite's text on click. A
   confidential meeting kept only its title and times, and says so. */
import { A, DEC, R } from "../../core/data.js";
import { fd, TODAY } from "../../core/page.js";
import { plur } from "../../today.js";
import { popupRev, prepNow } from "../../stores/prepPopup.js";
import { invitees } from "./PrepHead.jsx";

/** @typedef {{decisions: number, risks: number, issues: number, overdue: number, since: string, has_last: boolean,
    invite_first: number}} Facts */

/** The counts from the page's own data, as prep_view.since_counts works them out on the server.
    @param {any} m @param {string} day @returns {Facts} */
export function localFacts(m, day) {
  const code = m.p, all = code === "_portfolio", inP = (/** @type {any} */ x) => all || x.p === code;
  const since = m.last || m.since || day;
  return {
    decisions: DEC.filter(x => inP(x) && x.st === "Made" && x.date >= since && x.date <= day).length,
    risks: R.filter(x => inP(x) && x.type === "Risk" && (x.raised || "") >= since).length,
    issues: R.filter(x => inP(x) && x.type === "Issue" && (x.raised || "") >= since).length,
    overdue: A.filter(x => inP(x) && (x.st === "Open" || x.st === "Delayed") && x.due && x.due >= since && x.due < day).length,
    since, has_last: !!m.last,
    invite_first: m.invite && m.invite.confidential ? 0 : Object.values(m.rank || {}).reduce((n, o) => n + Object.keys(o || {}).length, 0),
  };
}

/** The line's three parts: its head, what changed, and how many items the invite puts first.
    @param {Facts} f */
export function factsWords(f) {
  const parts = [f.decisions ? plur(f.decisions, "decision") : "", f.risks ? `${f.risks} new risk${f.risks === 1 ? "" : "s"}` : "",
    f.issues ? `${f.issues} new issue${f.issues === 1 ? "" : "s"}` : "", f.overdue ? `${plur(f.overdue, "action")} now overdue` : ""].filter(Boolean);
  return {
    head: f.has_last ? `Since the last meeting (${fd(f.since)})` : `No earlier meeting on record; since ${fd(f.since)}`,
    what: `${parts.length ? parts.join(", ") : "nothing new"}.`,
    first: f.invite_first ? `${plur(f.invite_first, "item")} the invite points to ${f.invite_first === 1 ? "is" : "are"} shown first.` : "",
  };
}

export function PrepFacts() {
  popupRev.value;
  const { e, day, m, brief } = prepNow();
  if (!e || !m.p) return null;
  const f = brief && brief.facts ? brief.facts : localFacts(m, day || TODAY), w = factsWords(f);
  const v = m.invite || {}, conf = !!v.confidential, inv = conf ? [] : invitees(m, brief);
  const org = brief && brief.people && brief.people.organiser ? brief.people.organiser.name
    : v.organiser === true ? "you" : v.organiser ? String(v.organiser) : "";
  const hasInvite = conf || v.body || inv.length || (v.attachments || []).length;
  return (
    <div class="preplead">
      <p class="prepfacts" id="prepFacts">{m.p === "_portfolio" ? "Across every project. " : ""}<b>{w.head}:</b> {w.what}
        {w.first ? <span class="sub"> {w.first}</span> : null}</p>
      {hasInvite ? (
        <details class="prepinv">
          <summary>{conf ? "Invite: confidential, only the title and times are kept"
            : ["Invite", org ? `organised by ${org}` : "", inv.length ? `${inv.length} invited` : ""].filter(Boolean).join(" · ").replace(/^Invite · /, "Invite: ")}
            {inv.length ? <span class="prepnames"> ({inv.map((p, i) => <span key={i}>{i ? ", " : ""}{p.registered ? p.name
              : <span class="unreg" data-tip="Not in the people register">{p.name}<span class="vh"> (not in the people register)</span></span>}</span>)})</span> : null}
            {v.body ? <span class="sub"> · invite text</span> : null}</summary>
          {conf ? <p class="sub">Confidential: only the title and times are kept.</p> : null}
          {v.recurrence ? <p class="sub">{String(v.recurrence)}</p> : null}
          {(v.attendees || []).length ? <p class="sub">Invited: {(v.attendees || []).map((/** @type {any} */ a, /** @type {number} */ i) => (
            <span key={i}>{i ? ", " : ""}{a.name}{a.type === "optional" ? " (optional)" : ""}{a.response && a.response !== "none" ? ` · ${a.response}` : ""}</span>))}</p> : null}
          {(v.attachments || []).length ? <p class="sub">Attached: {(v.attachments || []).join(", ")}</p> : null}
          {v.body ? <div class="prepbodytxt">{String(v.body)}</div> : null}
        </details>
      ) : null}
    </div>
  );
}
