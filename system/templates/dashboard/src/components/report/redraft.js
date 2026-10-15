// @ts-check
/* The sheet's ✦ (v2.1.0, #90): `onRedraft` for the weekly, client and minutes views. It asks /api/draft for the kind "report-section"
   or "minutes-section" (drafts.py builds the facts, the model words one section, the reply is checked) and gives the Sheet its
   Redraft ({text, panes?, sources}). A suggestion only: the Sheet shows it beside Alan's words, and he keeps his or uses it.
   - A redraft belongs to the section it was asked for: each section's block holds its own suggestion and is keyed by the
     section's id, so a reorder while a redraft is pending can't send it to another section. The server echoes the id it was
     sent; the check below is only a guard against a mixed-up reply, not the protection (#90 review K1).
   - The reply's checks reach the page (#90 review F5): the plain-code notes and each sentence's sources ("No source").
   - Counts (offered is the server's; used, edited and rejected are here): counts only, never text. "Edited" is a used suggestion
     Alan then changed (#90 review K5), so it is counted on top of "used". */
import { draftAsk, draftStat } from "../../drafts.js";

/** @typedef {{id: string, heading: string, type: string, text?: string, panes?: {title: string, text: string}[]}} Sec */
/** @typedef {import("./Sheet.jsx").Redraft} Redraft */

/** The feature (and kind) each place counts under. */
export const REDRAFT_KIND = /** @type {const} */ ({ report: "report-section", minutes: "minutes-section" });

/** The request for one section: its words (or panes) and which section it is; `base` gives the report or the minutes.
    @param {Sec} s @param {Record<string, any>} base @param {string} kind @param {string} [action] @param {string} [instruction] */
export function redraftRequest(s, base, kind, action = "polish", instruction = "") {
  const panes = s.type === "panes" ? (s.panes || []).map(p => ({ title: p.title, text: p.text })) : null;
  return { kind, ...base, section: s.id, heading: s.heading, action, ...(instruction ? { instruction } : {}), ...(panes ? { panes } : { text: s.text || "" }) };
}

/** The Redraft the Sheet shows for /api/draft's answer `r` to section `s`, or throws the words to show.
    @param {any} r @param {Sec} s @returns {Redraft} */
export function redraftAnswer(r, s) {
  if (r.nothing) throw new Error(r.nothing);
  if (!r.ok || !r.text) throw new Error(r.message || "No draft came back");
  if (r.section !== s.id) throw new Error("That draft was for another section, so it wasn't used");
  return { text: r.text, ...(r.panes && r.panes.length ? { panes: r.panes } : {}),
    sources: (r.sources || []).map((/** @type {any} */ x) => ({ ref: x.ref, label: x.text })),
    notes: (r.notes || []).map((/** @type {any} */ n) => ({ id: String(n.id || ""), note: String(n.note || "") })),
    sentences: (r.sentences || []).map((/** @type {any} */ x) => ({ text: String(x.text || ""), refs: x.refs || [], unsourced: !!x.unsourced })) };
}

/** What the Sheet's onRedraft calls: asks for the draft and answers the Redraft, or throws the words to show.
    @param {() => Record<string, any>} base the report or minutes the section is in (read when ✦ is pressed)
    @param {"report"|"minutes"} place @returns {(s: Sec) => Promise<Redraft>} */
export function redrafter(base, place) {
  return async s => redraftAnswer(await draftAsk(redraftRequest(s, base(), REDRAFT_KIND[place]), { label: `Redrafting ${s.heading}` }), s);
}

/** The Sheet's `redraft` event: counted as used, edited or rejected. @param {any} ev @param {"report"|"minutes"} place */
export function countRedraft(ev, place) {
  if (ev.type !== "redraft") return;
  draftStat(REDRAFT_KIND[place], ev.choice === "keep" ? "rejected" : ev.choice === "edited" ? "edited" : "used");
}
