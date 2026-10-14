// @ts-check
/* stores/prepPopup.js (BL-286 parts A and B, BL-256): the Prep popup's state. The meeting itself stays in shared.PREPEV and
   shared.PREPDAY (old code reads them); this store holds what the popup's components draw from: a redraw counter that
   drawPrep() bumps, and the brief the live server works out for the header and the facts line (/api/prep/brief: the
   facts, the series chip and who is invited, with addresses resolved to names through the people register). Without the
   live server the components work the same lines out from the page's own data. */
import { signal } from "@preact/signals";
import { TODAY } from "../core/page.js";
import { api, viaServer } from "../core/server.js";
import { shared } from "../core/state.js";
import { prepKey, prepOf } from "../projects.js";

/** @typedef {{name: string, initials: string, registered: boolean}} BriefPerson */
/** @typedef {{ok: boolean, facts?: {decisions: number, risks: number, issues: number, overdue: number, since: string,
    has_last: boolean, invite_first: number, text: string}, series?: {text: string, cadence: string, nth: number,
    last: string | null}, people?: {organiser: BriefPerson | null, invitees: BriefPerson[], count: number,
    confidential: boolean}}} Brief */

/** Bumped by drawPrep(), so the header and the facts line redraw with the list. */
export const popupRev = signal(0);
/** The live server's brief for the meeting on screen, or null (not asked yet, no server, or it said no). */
export const popupBrief = signal(/** @type {{key: string, data: Brief} | null} */ (null));

let asked = 0;
/** Ask the live server for the meeting's brief; the answer is kept only if that meeting is still the one asked for last.
    @param {string} key */
export async function loadBrief(key) {
  const mine = ++asked;
  if (popupBrief.value && popupBrief.value.key !== key) popupBrief.value = null;
  if (!viaServer() || !key) return;
  let r = null;
  try { r = await api("/api/prep/brief", { key }); } catch (e) { r = null; }   /* the page's own lines stay */
  if (mine === asked && r && r.ok) popupBrief.value = { key, data: r };
}

/** Part C (shaping) registers its opener here; the toolbar shows Shape this meeting only once it has. */
export const prepShape = signal(/** @type {null | ((key: string) => void)} */ (null));

/** The meeting on screen: the calendar event, its day, its Prep brief record (project, series, invite, ranking), its key,
    and the live server's brief when it has come back for this meeting. */
export function prepNow() {
  const e = shared.PREPEV, day = shared.PREPDAY || TODAY;
  const key = e ? prepKey(e, day) : "", b = popupBrief.value;
  return { e, day, key, m: (e && prepOf(e, day)) || {}, brief: b && b.key === key ? b.data : null };
}

/** The address of a meeting's prep page inside creaite (BL-286 D, Meetings › Prep): "#prep=<the dated key, URI-encoded>",
    the dated key being "YYYY-MM-DD|HH:MM|title" so the address names the same meeting on any day.
    @param {string} key @param {string} [day] */
export function prepViewHref(key, day) {
  const k = String(key || ""), dated = /^\d{4}-\d{2}-\d{2}\|/.test(k) ? k : `${day || TODAY}|${k}`;
  return `#prep=${encodeURIComponent(dated)}`;
}
