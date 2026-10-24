// @ts-check
/* #203: the sparkle that suggests a project's health and its reason (the page half; drafts.py's kind "health", field "suggest", is the
   plain-code half). One request, one reply: {health, reason, differs, current: {health, reason}, evidence: [{ref, text}], audience}.
   A draft only: nothing is saved until Use and then the form's Save, or the card's Save (which uses it and presses the form's Save).
   `audience` "client" asks for wording from client-visible items only (the report's client sheet); the default is internal.
   Counts (offered is the server's; used, edited and rejected are here) go under the feature "reason", as the reason drafts do. */
import { draftAsk, draftStat, draftWhyNot } from "./drafts.js";
import { esc, ic } from "./core/dom.js";
import { itemOf } from "./core/itemLink.js";

export const HS_FEATURE = "reason";
export const HS_NAME = "Suggest health and reason";
export const HS_TIP = "Suggest a fresh draft";
export const HEALTHS = ["On track", "At risk", "Off track"];

/** @typedef {{health: string, reason: string, differs: boolean, current: {health: string, reason: string}, evidence: {ref: string, text: string}[], audience: string}} HealthSuggestion */

/** The reply as the page uses it, or null when it holds no usable health. @param {any} r @returns {HealthSuggestion|null} */
export function hsNorm(r) {
  if (!r || !HEALTHS.includes(String(r.health))) return null;
  const cur = r.current || {}, hv = String(r.health), now = String(cur.health || "");
  return { health: hv, reason: String(r.reason || r.text || ""), differs: typeof r.differs === "boolean" ? r.differs : !!now && now !== hv,
    current: { health: now, reason: String(cur.reason || "") },
    evidence: (Array.isArray(r.evidence) ? r.evidence : []).map((/** @type {any} */ e) => ({ ref: String((e && e.ref) || ""), text: String((e && e.text) || "") })),
    audience: r.audience === "client" ? "client" : "internal" };
}

/** Asks for a suggestion for project `code`. Answers {ok, d}, {nothing} (the tracker holds nothing to go on) or {message}.
    @param {string} code @param {"internal"|"client"} audience @param {{status?: (h: string) => void}} [o]
    @returns {Promise<{ok: boolean, d?: HealthSuggestion, nothing?: string, message?: string}>} */
export async function hsAsk(code, audience, o = {}) {
  const why = draftWhyNot("health");
  if (why) return { ok: false, message: why };
  const res = await draftAsk({ kind: "health", field: "suggest", code, audience }, { label: "Suggesting the health", status: o.status });
  if (res.nothing) return { ok: false, nothing: res.nothing };
  if (!res.ok) return { ok: false, message: res.message || "No draft came back" };
  const d = hsNorm(res);
  return d ? { ok: true, d } : { ok: false, message: "The suggestion couldn't be read; nothing changed" };
}

/** The suggestion compared with the health the page shows (the client sheet's own flag, not the tracker's): "you have" and `differs`
    follow that flag. @param {HealthSuggestion} d @param {string} [shown] @returns {HealthSuggestion} */
export function hsAgainst(d, shown) {
  return shown ? { ...d, differs: shown !== d.health, current: { ...d.current, health: shown } } : d;
}

/** The sentence that flags a difference, or "" when the facts agree. @param {HealthSuggestion} d */
export const hsDiffLine = d => d.differs ? `The facts suggest ${d.health}, you have ${d.current.health || "no health set"}.` : "";
/** The CSS class of a health, for its chip. @param {string} h */
export const hsTone = h => h === "On track" ? "ok" : h === "At risk" ? "warn" : "bad";
/** How a suggestion was used, for the counts: "used" when the reason is as suggested, else "edited". @param {string} a @param {string} b */
export const hsUse = (a, b) => String(a || "").replace(/\s+/g, " ").trim() === String(b || "").replace(/\s+/g, " ").trim() ? "used" : "edited";
/** Counts a suggestion (counts only, never text). @param {"used"|"edited"|"rejected"} event */
export const hsStat = event => draftStat(HS_FEATURE, event);

/** The sparkle button beside the Health label: the app's own icon, plain. */
export function hsSparkHtml() {
  const why = draftWhyNot("health");
  return `<button type="button" class="hspark" data-hsuggest aria-label="${HS_NAME}" data-tip="${esc(why || HS_TIP)}"${why ? ' aria-disabled="true"' : ""}>${ic("spark")}</button>`;
}

/** The evidence list: each item ID a link to the item, as elsewhere. @param {{ref: string, text: string}[]} L */
export function hsEvidenceHtml(L) {
  return `<ul class="hsg-why" aria-label="Evidence">${L.map(e => { const f = itemOf(e.ref);
    return `<li>${f ? `<a href="#" class="hlink" data-open="${f.k}:${esc(e.ref)}">${esc(e.ref)}</a>` : `<b>${esc(e.ref)}</b>`} ${esc(e.text)}</li>`; }).join("")}</ul>`;
}

/** The suggestion card on the project page's health form. @param {HealthSuggestion} d @param {string} reason the reason as edited so far */
export function hsCardHtml(d, reason) {
  const diff = hsDiffLine(d), chip = (/** @type {string} */ h) => `<span class="hsg-chip ${hsTone(h)}">${esc(h)}</span>`;
  return `<div class="drcard hsg" role="region" aria-label="Suggested health and reason" tabindex="-1" id="hsgCard">
    <div class="drhead">${ic("spark")}<b>Suggested: ${chip(d.health)}</b>${d.current.health ? `<span class="sub">now ${chip(d.current.health)}${diff ? "" : " · agrees with you"}</span>` : ""}</div>
    ${diff ? `<div class="hsg-diff" role="note">${esc(diff)}</div>` : ""}
    <textarea id="hsgReason" class="hsg-reason" aria-label="Suggested reason">${esc(reason)}</textarea>
    ${hsEvidenceHtml(d.evidence)}
    <div class="drnote">A draft from your project record. Nothing is saved until you press Save.</div>
    <div class="drfoot"><span class="sp"></span><button type="button" class="btn" data-hsdo="reject">Reject</button><button type="button" class="btn" data-hsdo="use">Use</button><button type="button" class="btn primary" data-hsdo="save">Save</button></div></div>`;
}
