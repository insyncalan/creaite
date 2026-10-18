// @ts-check
/* stores/projectSettings.js (#228 part A): the full-page project settings (#project-settings=<CODE>). The page's state, the
   categories, a project's people from the people register, and the partner organisations.

   Partner organisations are one line of the project's CLAUDE.md, "- **Partners:** Org A; Org B", saved with setMemLine (core/server.js:
   the vault, a copy of the file first, a line in settings-log.jsonl, and a refusal when the file changed since it was read), the way
   the client report settings are. A name or a status of the project itself is saved the way the project page saves its health:
   `save` with an update of the projects table, which is applied at once and can be undone. Nothing here writes a file of its own. */
import { signal } from "@preact/signals";
import { A, DEC, P, R } from "../core/data.js";
import { D } from "../core/page.js";
import { go } from "../core/nav.js";
import { liveLines, memPath, needVault, reloadData, save, setMemLine, snack, viaServer, vq } from "../core/server.js";
import { shared } from "../core/state.js";
import { resolver } from "../settings.js";

/** The categories, in the order the page lists them. The third is what the search matches besides the words on the page. */
export const PS_CATS = [
  ["general", "General", "name client code status folder project details"],
  ["people", "People and partners", "people partners partner organisations organisation role register"],
  ["logos", "Logos", "logos firm client partner header picture"],
  ["miles", "Milestones", "milestones plan agreed expected dates add edit"],
  ["rep", "Reporting", "reporting client report how often reminder weekly report day"],
  ["arch", "Archive", "archive close restore project nothing is deleted"],
];

export const psCode = signal("");          // the project the page is open for
export const psCat = signal("general");
export const psQ = signal("");
/** bumped when something the page shows changes */
export const psTick = signal(0);
export const psChanged = () => { psTick.value++; };

/** @param {string} code */
export const psProject = code => /** @type {any} */ (P.find(p => p.code === code));

// ----- the project's own details

export const NAME_MAX = 80;
/** @param {string} v @returns {string} a plain-words problem, or "" */
export function nameProblem(v) {
  const t = String(v || "");
  if (/[\r\n]/.test(t)) return "The name is one line.";
  if (!t.replace(/\s+/g, " ").trim()) return "Type the project's name.";
  if (t.replace(/\s+/g, " ").trim().length > NAME_MAX) return `The name is over ${NAME_MAX} characters.`;
  return "";
}

/** Rename the project: an update of the projects table, applied at once, with Undo. @param {string} code @param {string} name @returns {Promise<boolean>} */
export async function renameProject(code, name) {
  const p = psProject(code); if (!p) return false;
  const bad = nameProblem(name); if (bad) { snack("Not saved: " + bad); return false; }
  const v = String(name).replace(/\s+/g, " ").trim(), old = p.name;
  if (v === old) return true;
  const ok = await save(`${old}: name → ${v}`, [{ op: "update", table: "projects", id: code, changes: { name: v } }], null,
    () => { p.name = v; psChanged(); }, () => { p.name = old; psChanged(); });
  return ok !== false;
}

/** Make the project active or closed: the update the close flow makes (active 0 or 1), applied at once, with Undo.
    @param {string} code @param {boolean} active @returns {Promise<boolean>} */
export async function setProjectActive(code, active) {
  const p = psProject(code); if (!p) return false;
  const was = projectState(code), now = active ? "active" : "closed";
  const ok = await save(`${p.name}: ${active ? "active again" : "closed"}`, [{ op: "update", table: "projects", id: code, changes: { active: active ? 1 : 0 } }], null,
    () => { markState(code, now); psChanged(); }, () => { markState(code, was); psChanged(); });
  return ok !== false;
}
/** @param {string} code @param {string} state */
function markState(code, state) { const s = (D.project_states || []).find((/** @type {any} */ x) => x.code === code); if (s) s.state = state; }
/** @param {string} code @returns {string} active, closed or archived */
export function projectState(code) { const s = (D.project_states || []).find((/** @type {any} */ x) => x.code === code); return s ? s.state : "active"; }

// ----- people

/** The people on a project, from the people register: everyone who owns an item of it or made one of its decisions, with the
    organisation and role the register holds. @param {string} code @returns {{name: string, org: string, role: string}[]} */
export function projectPeople(code) {
  const rs = resolver(), names = new Set();
  const add = (/** @type {string} */ n) => { if (n && n !== "TBC") names.add((rs(n) || {}).name || n); };
  A.forEach(x => x.p === code && add(x.o)); R.forEach(x => x.p === code && add(x.o)); DEC.forEach(x => x.p === code && add(x.by));
  const reg = /** @type {any[]} */ (shared.REG || []);
  return [...names].sort((a, b) => a.localeCompare(b)).map(name => {
    const r = reg.find(x => x.name === name) || {};
    return { name, org: r.org || "", role: r.role || "" };
  });
}

// ----- partner organisations

export const PARTNER_MAX = 80, PARTNERS_LINE_MAX = 400, PARTNERS_MAX = 12;   // the server keeps at most 12 (build_dashboard.PARTNERS_MAX)
/** the Partners line of the project last read */
export const partners = signal({ code: "", list: /** @type {string[]} */ ([]), loaded: false });

/** The partner organisations a project's CLAUDE.md text names (a "**Partners:**" line outside a code fence or a quote).
    @param {string} text @returns {string[]} */
export function partnersFrom(text) {
  const lines = String(text || "").split("\n"), live = liveLines(lines);
  for (let i = 0; i < lines.length; i++) {
    if (!live[i]) continue;
    const m = lines[i].replace(/\r$/, "").match(/^[ \t]*(?:[-*][ \t]+)?\*\*Partners:\*\*[ \t]*([^\n]*?)[ \t]*(?:_\(.*\)_)?$/);
    if (m) return m[1].split(";").map(s => s.replace(/\s+/g, " ").trim()).filter(Boolean);
  }
  return [];
}

/** Read the project's Partners line. @param {string} code */
export async function loadPartners(code) {
  partners.value = { code, list: [], loaded: false };
  if (!viaServer() && shared.VSTATE !== "ok") return;
  try { const text = await vq(() => shared.VW.read(memPath(code))); partners.value = { code, list: partnersFrom(text), loaded: true }; }
  catch (e) { partners.value = { code, list: [], loaded: false }; }
}

const partnerKey = (/** @type {string} */ s) => String(s).replace(/\s+/g, " ").trim().toLowerCase();
/** A partner's name checked for the list: one line, not empty, not too long, no semicolon, not already listed (any capitals).
    @param {string[]} list @param {string} name @param {number} [except] the index being renamed @returns {string} a plain-words problem, or "" */
export function partnerProblem(list, name, except = -1) {
  const t = String(name || "");
  if (/[\r\n]/.test(t)) return "A partner's name is one line.";
  const v = t.replace(/\s+/g, " ").trim();
  if (!v) return "Type the partner organisation's name.";
  if (v.length > PARTNER_MAX) return `A partner's name is over ${PARTNER_MAX} characters.`;
  if (v.includes(";")) return "A partner's name can't contain a semicolon; add each partner on its own.";
  const same = list.find((x, i) => i !== except && partnerKey(x) === partnerKey(v));
  if (same) return `${same} is already listed.`;
  return "";
}

/** Save the whole list (the line's value is the names joined by "; "), then keep it on the page. Returns whether it was saved.
    @param {string} code @param {string[]} list */
async function writePartners(code, list) {
  const v = list.join("; ");
  if (v.length > PARTNERS_LINE_MAX) { snack(`Not saved: the partners' line would be over ${PARTNERS_LINE_MAX} characters.`); return false; }
  if (!await setMemLine(code, "Partners", v, "partners")) return false;
  partners.value = { code, list: [...list], loaded: true };
  await reloadData();       // the server re-derives P[].partners (names and slugs) so the logo tiles and report headers follow now; a slug is never made here
  psChanged(); return true;
}

/** @param {string} code @param {string[]} list the list as it was; Undo puts it back */
const undoer = (code, list) => async () => { if (await writePartners(code, list)) snack("Undone"); };

/** Add a partner organisation. @param {string} code @param {string} name @returns {Promise<string>} "" when saved, otherwise the problem */
export async function addPartner(code, name) {
  const was = partners.peek().list, bad = partnerProblem(was, name);
  if (bad) return bad;
  if (was.length >= PARTNERS_MAX) return `A project lists at most ${PARTNERS_MAX} partner organisations.`;
  const v = String(name).replace(/\s+/g, " ").trim();
  if (!await needVault()) return "Not saved: creaite can't reach the vault.";
  if (!await writePartners(code, [...was, v])) return "Not saved.";
  snack(`${v} added as a partner`, undoer(code, was)); return "";
}

/** Rename a partner organisation. @param {string} code @param {number} i @param {string} name @returns {Promise<string>} */
export async function renamePartner(code, i, name) {
  const was = partners.peek().list, bad = partnerProblem(was, name, i);
  if (bad) return bad;
  const v = String(name).replace(/\s+/g, " ").trim();
  if (v === was[i]) return "";
  if (!await writePartners(code, was.map((x, j) => j === i ? v : x))) return "Not saved.";
  snack(`${was[i]} renamed ${v}`, undoer(code, was)); return "";
}

/** Remove a partner organisation. @param {string} code @param {number} i @returns {Promise<boolean>} */
export async function removePartner(code, i) {
  const was = partners.peek().list, gone = was[i]; if (gone === undefined) return false;
  if (!await writePartners(code, was.filter((_, j) => j !== i))) return false;
  snack(`${gone} removed from the partners`, undoer(code, was)); return true;
}

/** Open the page for a project, at General (the cog, the Projects list and Settings › People and projects all come here).
    @param {string} code */
export function openProjectSettings(code) {
  if (!P.some(p => p.code === code)) { snack("That project isn't open here"); return false; }
  psCat.value = "general"; psQ.value = "";
  return go("psettings", code);
}
