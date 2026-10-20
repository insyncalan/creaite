// @ts-check
/* stores/peopleRegister.js (#247, #248): the people register as the project settings page's People view and the People page read
   it, and the edits both make. Not a Settings module: Settings › People and projects is retired (#246), these two are its homes.

   - Everyone on an item is in the register (Alan, 19-10-2026): a name on an item with no register row yet is shown like anyone
     else, marked "needs details" when its email, organisation or role is missing; saving its details writes its row.
   - A person is on a project when they own an action or RAID item there, made or are asked for one of its decisions, or are one
     of its stakeholders in the project register (D.stakeholders); "Add to this project" and the edit form's "On projects" ticks
     add a project to that, and "Remove from this project" takes one away. Both are kept in the person's own register row, in two
     columns of codes, "Projects" (added) and "Left projects" (taken away), so nothing about an item changes.
   - Email, aliases, organisation and role are one entry per person, the same on every project; only the counts are per project.
   - Followed (the register's VIP column, BL-99) is read here only for the project settings page's People view (BL-288: the star
     and the Follow tick are shown there and nowhere else); `follow` on a field list or a save is that page's alone.
   Every change is one proposal holding the register file (settings.js regSave: logged, applied, with Undo). */
import { A, DEC, open, P, R } from "../core/data.js";
import { D, isMe, S, TODAY } from "../core/page.js";
import { REGPEND, REGTEXT, isHiddenPerson, pBlank, pFind, pKey, peopleParse, regSave, resolver } from "../settings.js";

export const COL_ON = "Projects", COL_OFF = "Left projects";
/** @param {any} v @returns {string[]} */
export const codesOf = v => String(v || "").split(",").map(x => x.trim()).filter(Boolean);
const NO_FOLLOW = /^(no|n|false|0|-)$/i;

/** The register as it is now: the data the page last loaded (an Undo of an applied change reloads it), or, while a change of
    this page is still waiting to be applied, the text it wrote (settings.js REGTEXT). Its rows keep their extra columns (VIP,
    Projects, Left projects…), which the page's own list (shared.REG) does not. */
let regCache = { text: /** @type {string|null} */ (null), list: /** @type {any[]} */ ([]) };
export function regList() {
  const live = D.people_register && typeof D.people_register.text === "string" ? D.people_register.text : null;
  const text = REGPEND === null && live !== null && D.people_register.exists !== false ? live : (REGTEXT || "");
  if (regCache.text !== text) regCache = { text, list: peopleParse(text) };
  return regCache.list;
}
/** @param {string} name @returns {Record<string, string>} */
export function regExtra(name) { const r = pFind(regList(), name); return (r && r.extra) || {}; }
/** @param {Record<string, string>} x */
const followedIn = x => { const v = String(x.VIP || "").trim(); return !!v && !NO_FOLLOW.test(v); };

/** @typedef {{a: number, r: number, d: number, st: boolean}} ProjCounts */
/** @typedef {{n: string, p: any, me: boolean, email: string, org: string, role: string, aliases: string[], followed: boolean,
    it: Record<string, ProjCounts>, derived: string[], on: string[], missing: string[], oa: any[], al: any[], or: any[], dw: any[], late: number, lateItems: any[],
    items: any[]}} PersonRow */

/** @param {Map<string, any>} map @param {string} n */
function rowOf(map, n) {
  if (!map.has(n)) map.set(n, { n, it: {}, oa: [], al: [], or: [], dw: [], items: [] });
  return map.get(n);
}
/** @param {any} x @param {string} c @returns {ProjCounts} */
function countsOf(x, c) { if (!x.it[c]) x.it[c] = { a: 0, r: 0, d: 0, st: false }; return x.it[c]; }

/** Everyone with what the views read: the register (not hidden), every owner and decision maker, and the stakeholders.
    @returns {PersonRow[]} */
export function registerRows() {
  const rs = resolver(), canon = (/** @type {string} */ n) => (rs(n) || {}).name || n, map = new Map();
  regList().forEach(p => { if (!p.hidden) rowOf(map, p.name); });
  const own = (/** @type {any} */ i, /** @type {string} */ owner, /** @type {"a"|"r"|"d"} */ k) => {
    if (!owner || owner === "TBC") return null;
    const x = rowOf(map, canon(owner)); countsOf(x, i.p)[k]++; x.items.push(i); return x;
  };
  A.forEach(a => { const x = own(a, a.o, "a"); if (x && a.st === "Open") x.oa.push(a); if (x && open(a)) x.al.push(a); });   // Actions counts Open; Overdue keeps Delayed
  R.forEach(r => { const x = own(r, r.o, "r"); if (x && open(r)) x.or.push(r); });
  DEC.forEach(d => { const x = own(d, d.by, "d"); if (x && d.st === "Pending") x.dw.push(d); });
  const st = D.stakeholders || {};
  Object.keys(st).forEach(c => (st[c] || []).forEach((/** @type {string} */ s) => { if (s && s !== "TBC") countsOf(rowOf(map, canon(s)), c).st = true; }));
  const codes = new Set(P.map(p => p.code));
  return [...map.values()].filter(x => !isHiddenPerson(x.n)).map(x => finish(x, codes)).sort((a, b) => a.n.localeCompare(b.n));
}

/** @param {any} x @param {Set<string>} codes @returns {PersonRow} */
function finish(x, codes) {
  const p = pFind(regList(), x.n) || null, me = isMe(x.n), extra = regExtra(x.n);
  const derived = Object.keys(x.it).filter(c => codes.has(c));
  const left = new Set(codesOf(extra[COL_OFF]));
  const on = [...new Set([...derived, ...codesOf(extra[COL_ON]).filter(c => codes.has(c))])].filter(c => !left.has(c));
  const email = (p && p.email) || "", org = (p && p.org) || "", role = (p && p.role) || "";
  const missing = me ? [] : [...(email ? [] : ["email"]), ...(org ? [] : ["organisation"]), ...(role ? [] : ["role"])];
  const lateItems = [...x.al, ...x.or].filter(i => i.due && i.due < TODAY);
  return { ...x, p, me, email, org, role, aliases: (p && p.aliases) || [], followed: followedIn(extra), derived, on: P.map(q => q.code).filter(c => on.includes(c)), missing, late: lateItems.length, lateItems };
}

/** "Missing: email, organisation" for the needs-details tag's tooltip. @param {PersonRow} x */
export const missingWords = x => x.missing.length ? `Missing: ${x.missing.join(", ")}` : "";
/** the counts of one project, or of all of them @param {PersonRow} x @param {string} [code] */
export function countsIn(x, code) {
  const cs = code ? [code] : Object.keys(x.it);
  return cs.reduce((s, c) => { const t = x.it[c]; if (t) { s.a += t.a; s.r += t.r; s.d += t.d; } return s; }, { a: 0, r: 0, d: 0 });
}

// ----- the filter (the two-pane picker: WHO and TIDY UP), one state per view

/** @typedef {{q: string, f: Record<string, Set<string>>, pk: string}} PeopleFilterState */
export const PF_FIELDS = ["proj", "inv", "org", "fol", "att"];
/** @returns {PeopleFilterState} */
export const newFilter = () => ({ q: "", f: Object.fromEntries(PF_FIELDS.map(k => [k, new Set()])), pk: "proj" });
/** @param {PeopleFilterState} s */
export function clearFilter(s) { PF_FIELDS.forEach(k => s.f[k].clear()); s.q = ""; }

/** @typedef {[string, string, string, [string, string][], (x: PersonRow, v: string) => boolean, string]} PeopleField
    [key, label, section, choices, hit, the picker's note] */

/** The fields offered. `code`: the project page's project (Project then means its other projects); `follow`: the Followed field
    (the project settings page only, BL-288). A field with no choice is left out.
    @param {PersonRow[]} L @param {PeopleFilterState} s @param {{code?: string, follow?: boolean}} opt @returns {PeopleField[]} */
export function peopleFields(L, s, opt) {
  const code = opt.code || "", has = (/** @type {(x: PersonRow) => boolean} */ f) => L.some(f);
  const scope = () => code ? [code] : s.f.proj.size ? [...s.f.proj].filter(v => v !== "none") : P.map(p => p.code);
  const others = P.filter(p => p.code !== code && has(x => x.on.includes(p.code)));
  const proj = /** @type {[string, string][]} */ ([...others.map(p => [p.code, code ? `Also on ${p.name}` : p.name]),
    ...(code && has(x => x.on.length === 1) ? [["only", "Only on this project"]] : []), ...(!code && has(x => !x.on.length) ? [["none", "On no project"]] : [])]);
  const inv = /** @type {[string, string][]} */ ([["a", "Owns actions"], ["r", "Owns risks and issues"], ["d", "Decides"], ["named", "Named only"]]);
  const invHit = (/** @type {PersonRow} */ x, /** @type {string} */ v) => scope().some(c => {
    const t = x.it[c]; if (v === "named") return x.on.includes(c) && !(t && (t.a || t.r || t.d));
    return !!t && t[/** @type {"a"|"r"|"d"} */ (v)] > 0; });
  const orgs = [...new Set(L.map(x => x.org).filter(Boolean))].sort();
  /** @type {PeopleField[]} */
  const F = [
    ["proj", code ? "Other projects" : "Project", "Who", proj, (x, v) => v === "only" ? x.on.length === 1 : v === "none" ? !x.on.length : x.on.includes(v),
      code ? "Also on another project, or on this one only." : "Owns an item there, is named on it, or was added to it."],
    ["inv", "How they're involved", "Who", inv.filter(([v]) => has(x => invHit(x, v))), invHit, code ? "In this project." : "In the projects chosen under Project, or in any project."],
    ["org", "Organisation", "Who", [...orgs.map(o => /** @type {[string, string]} */ ([o, o])), ...(has(x => !x.org) ? [/** @type {[string, string]} */ (["—", "No organisation"])] : [])],
      (x, v) => v === "—" ? !x.org : x.org === v, ""],
    ["fol", "Followed", "Who", opt.follow && has(x => x.followed) ? [["yes", "Followed"], ["no", "Not followed"]] : [], (x, v) => v === "yes" ? x.followed : !x.followed, "Set in each person's details."],
    ["att", "Needs attention", "Tidy up", /** @type {[string, string][]} */ ([["email", "No email"], ["organisation", "No organisation"], ["role", "No role"]]).filter(([v]) => has(x => x.missing.includes(v))),
      (x, v) => x.missing.includes(v), "Details worth filling in, so mail and minutes map to the right person."],
  ];
  return F.filter(f => f[3].length);
}

/** @param {PersonRow} x @param {string} q */
export const searchHit = (x, q) => { const t = q.trim().toLowerCase(); return !t || [x.n, x.email, x.org, x.role, ...x.aliases].some(v => v && v.toLowerCase().includes(t)); };
/** Does x show, skipping one field (or "q", the search)? Ticks in a field are "any of"; fields combine with "and".
    @param {PersonRow} x @param {PeopleField[]} F @param {PeopleFilterState} s @param {string} [skip] */
export function personPasses(x, F, s, skip) {
  for (const f of F) {
    const set = s.f[f[0]];
    if (f[0] === skip || !set || !set.size) continue;
    if (![...set].some(v => f[4](x, v))) return false;
  }
  return skip === "q" || searchHit(x, s.q);
}
/** how many fields narrow the list @param {PeopleField[]} F @param {PeopleFilterState} s */
export const filterCount = (F, s) => F.filter(f => s.f[f[0]].size).length;
/** @param {PeopleField[]} F @param {PeopleFilterState} s */
export const filterAny = (F, s) => !!s.q.trim() || filterCount(F, s) > 0;

// ----- saving (each one proposal with Undo, through regSave)

/** The person's register row in a list being changed, made if it is not there yet. @param {any[]} L @param {string} name */
function rowIn(L, name) {
  let r = pFind(L, name);
  if (!r) { r = pBlank(name); L.push(r); }
  r.extra = { ...(r.extra || {}) };
  return r;
}
/** Keep a row's Projects and Left projects so that the person is on exactly `want` (of the open projects).
    @param {any} r @param {string[]} derived @param {string[]} want */
export function setOn(r, derived, want) {
  const on = new Set(codesOf(r.extra[COL_ON])), off = new Set(codesOf(r.extra[COL_OFF]));
  P.forEach(({ code }) => {
    const yes = want.includes(code), auto = derived.includes(code);
    if (yes) { off.delete(code); if (auto) on.delete(code); else on.add(code); }
    else { on.delete(code); if (auto) off.add(code); else off.delete(code); }
  });
  r.extra[COL_ON] = [...on].join(", "); r.extra[COL_OFF] = [...off].join(", ");
}
/** @param {string} name */
const derivedOf = name => (registerRows().find(x => x.n === name) || { derived: [] }).derived;
/** @param {string} name */
const onOf = name => (registerRows().find(x => x.n === name) || { on: [] }).on;

/** @typedef {{email: string, aliases: string[], org: string, role: string, projects?: string[], follow?: boolean}} PersonFields */

/** Save a person's details (one entry, the same on every project); `projects` the ticked projects; `follow` only from the project
    settings page. A VIP value already set (Management, Client) is kept when the tick stays on. @param {string} name @param {PersonFields} f */
export function savePerson(name, f) {
  const derived = derivedOf(name);
  return regSave(`Changed ${name} in the people register`, L => {
    const r = rowIn(L, name);
    Object.assign(r, { email: f.email, aliases: f.aliases, org: f.org, role: f.role });
    if (f.follow !== undefined) { const cur = String(r.extra.VIP || "").trim(); r.extra.VIP = f.follow ? (cur && !NO_FOLLOW.test(cur) ? cur : "yes") : ""; }
    if (f.projects) setOn(r, derived, f.projects);
    return L;
  });
}
/** A new person (the People page's Add a person). @param {string} name @param {PersonFields} f */
export function addPerson(name, f) {
  return regSave(`Added ${name} to the people register`, L => {
    const r = rowIn(L, name);
    Object.assign(r, { email: f.email, aliases: f.aliases, org: f.org, role: f.role });
    if (f.projects) setOn(r, [], f.projects);
    return L;
  });
}
/** @param {string} name @param {string} code */
export function addToProject(name, code) {
  const derived = derivedOf(name), want = [...new Set([...onOf(name), code])];
  return regSave(`Added ${name} to ${projName(code)}`, L => { setOn(rowIn(L, name), derived, want); return L; });
}
/** The project page's bin: off this project only; their record and their items stay. @param {string} name @param {string} code */
export function removeFromProject(name, code) {
  const derived = derivedOf(name), want = onOf(name).filter(c => c !== code);
  return regSave(`Removed ${name} from ${projName(code)}`, L => { setOn(rowIn(L, name), derived, want); return L; });
}
/** How many items (actions, RAID and decisions, open or closed) name them, by their name or an alias: while any do, Remove from
    the register is refused (#248 M3, Alan, 20-10-2026: reassign them first; nothing is reassigned for him, and the row would
    only come back as "needs details" without its aliases). @param {string} name */
export const ownedItems = name => (registerRows().find(x => pKey(x.n) === pKey(name)) || { items: [] }).items.length;
/** The People page's delete: the person's row leaves the register. Refused (false, nothing written) while they own items.
    Never called from a project page. @param {string} name */
export function removeFromRegister(name) {
  if (ownedItems(name) > 0) return Promise.resolve(false);
  return regSave(`Removed ${name} from the people register`, L => L.filter(p => pKey(p.name) !== pKey(name)));
}
/** @param {string} code */
const projName = code => (P.find(p => p.code === code) || { name: code }).name;
/** Whether a name is in the register file (a name only on items has no row to remove). @param {string} name */
export const inRegister = name => !!pFind(regList(), name);
/** A full name that is already someone (the Add a person form). @param {string} name */
export function nameTaken(name) {
  const r = resolver()(name);
  return r.status === "alias" || r.status === "email" || (r.status === "known" && !!r.registered) || pKey(name) === pKey(S.me);
}
