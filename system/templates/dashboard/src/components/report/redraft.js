// @ts-check
/* The sheet's ✦ (v2.1.0, #90): `onRedraft` for the weekly, client and minutes views. It asks /api/draft for the kind "report-section"
   or "minutes-section" (drafts.py builds the facts, the model words one section, the reply is checked) and gives the Sheet its
   Redraft ({text, panes?, sources}). A suggestion only: the Sheet shows it beside Alan's words, and he keeps his or uses it.
   - A redraft belongs to the section it was asked for, by its id: the server echoes the id and the answer is refused if it
     differs, so a reorder while a redraft is pending can't send it to another section (the Sheet keeps it on that section).
   - Counts (offered is the server's; used and rejected are here): counts only, never text. */
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

/** What the Sheet's onRedraft calls: asks for the draft and answers the Redraft, or throws the words to show.
    @param {() => Record<string, any>} base the report or minutes the section is in (read when ✦ is pressed)
    @param {"report"|"minutes"} place @returns {(s: Sec) => Promise<Redraft>} */
export function redrafter(base, place) {
  return async s => {
    const r = await draftAsk(redraftRequest(s, base(), REDRAFT_KIND[place]), { label: `Redrafting ${s.heading}` });
    if (r.nothing) throw new Error(r.nothing);
    if (!r.ok || !r.text) throw new Error(r.message || "No draft came back");
    if (r.section !== s.id) throw new Error("That draft was for another section, so it wasn't used");
    return { text: r.text, ...(r.panes && r.panes.length ? { panes: r.panes } : {}),
      sources: (r.sources || []).map((/** @type {any} */ x) => ({ ref: x.ref, label: x.text })) };
  };
}

/** The Sheet's `redraft` event: counted as used or rejected. @param {any} ev @param {"report"|"minutes"} place */
export function countRedraft(ev, place) {
  if (ev.type !== "redraft") return;
  draftStat(REDRAFT_KIND[place], ev.choice === "keep" ? "rejected" : "used");
}
