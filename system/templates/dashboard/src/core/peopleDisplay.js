// @ts-check
/* core/peopleDisplay.js (#360): the People page's Display menu, as pure rules (no imports, no DOM, no state: dev/tests/test_people_display.py
   runs this file under Node). What a person can be grouped, ordered and shown by is an explicit allow-list of keys here, never the
   keys of a row, so nothing private (a row also says whether someone is followed) can reach a menu, a heading or the browser's
   storage. The state is per viewer (this browser only): never in the register, never in settings.json. */

/** The columns, in their starting order: [key, label, title]. Name is locked on. */
export const PD_COLS = /** @type {[string, string, string?][]} */ ([["name", "Name"], ["email", "Email"], ["org", "Organisation"], ["role", "Role"], ["proj", "Projects"],
  ["oa", "Actions", "Open actions"], ["or", "RAID", "Open risks and issues"], ["dw", "Decisions", "Decisions waiting on them"], ["late", "Overdue"]]);
export const PD_KEYS = PD_COLS.map(c => c[0]);
export const PD_LOCKED = "name";
/** What a heading or Order by can sort on, with the direction it starts in. */
export const PD_SORTS = /** @type {Record<string, "asc"|"desc">} */ ({ name: "asc", email: "asc", org: "asc", role: "asc", oa: "desc", or: "desc", dw: "desc", late: "desc" });
export const PD_DEFAULT_SORT = { col: "late", dir: "desc" };
/** Group by and Sub-group, [key, label]. None first. */
export const PD_GROUPS = /** @type {[string, string][]} */ ([["none", "None"], ["org", "Organisation"], ["proj", "Project"], ["role", "Role"], ["late", "Overdue"], ["details", "Details"]]);
const GROUP_KEYS = PD_GROUPS.map(g => g[0]);

/** @typedef {{group: string, sub: string, cols: string[], collapsed: Record<string, true>}} PdState */
/** The starting state. @returns {PdState} */
export const pdDefault = () => ({ group: "none", sub: "none", cols: [...PD_KEYS], collapsed: {} });

/** A saved state made safe: an unknown group, column or collapsed key is dropped, a missing Name is put back, a duplicate is removed,
    an empty list starts again from the defaults. @param {any} saved @returns {PdState} */
export function pdNormalise(saved) {
  const d = pdDefault(), s = saved && typeof saved === "object" ? saved : {};
  const group = GROUP_KEYS.includes(s.group) ? s.group : d.group;
  const sub = GROUP_KEYS.includes(s.sub) && s.sub !== group ? s.sub : "none";
  let cols = Array.isArray(s.cols) ? s.cols.filter((/** @type {any} */ k, /** @type {number} */ i, /** @type {any[]} */ a) => PD_KEYS.includes(k) && a.indexOf(k) === i) : [];
  if (!cols.length) cols = [...d.cols];
  if (!cols.includes(PD_LOCKED)) cols.unshift(PD_LOCKED);
  /** @type {Record<string, true>} */
  const collapsed = {};
  if (s.collapsed && typeof s.collapsed === "object") for (const k of Object.keys(s.collapsed)) if (s.collapsed[k] === true && typeof k === "string" && k.length < 200) collapsed[k] = true;
  return { group, sub, cols, collapsed };
}

/** A saved sort made safe. @param {any} s @returns {{col: string, dir: "asc"|"desc"}} */
export function pdSort(s) {
  return s && PD_SORTS[s.col] && (s.dir === "asc" || s.dir === "desc") ? { col: s.col, dir: s.dir } : { ...PD_DEFAULT_SORT, dir: "desc" };
}

/** @typedef {{n: string, org: string, role: string, on: string[], late: number, missing: string[]}} PdPerson */
/** The groups of a person under one grouping: [value, label] pairs (several for Project: a person on two projects is under both).
    @param {PdPerson} x @param {string} g @param {(code: string) => string} projectName @returns {[string, string][]} */
export function pdGroupsOf(x, g, projectName) {
  if (g === "org") return [[x.org || "", x.org || "No organisation"]];
  if (g === "role") return [[x.role || "", x.role || "No role"]];
  if (g === "proj") return x.on.length ? x.on.map(c => /** @type {[string, string]} */ ([c, projectName(c)])) : [["", "On no project"]];
  if (g === "late") return x.late > 0 ? [["has", "Has overdue"]] : [["none", "Nothing overdue"]];
  if (g === "details") return x.missing.length ? [["needs", "Needs details"]] : [["complete", "Complete"]];
  return [["", ""]];
}
const FIXED = /** @type {Record<string, string[]>} */ ({ late: ["has", "none"], details: ["needs", "complete"] });

/** The people in groups, in a stable order: fixed groups in their own order, others A to Z with the "no value" group last. Rows keep the
    order they came in. @template T @param {(T & PdPerson)[]} rows @param {string} g @param {(code: string) => string} projectName
    @returns {{key: string, label: string, items: (T & PdPerson)[]}[]} */
export function pdGroup(rows, g, projectName) {
  if (!GROUP_KEYS.includes(g) || g === "none") return [{ key: "", label: "", items: rows }];
  /** @type {Map<string, {key: string, label: string, items: (T & PdPerson)[]}>} */
  const by = new Map();
  for (const x of rows) for (const [v, label] of pdGroupsOf(x, g, projectName)) {
    if (!by.has(v)) by.set(v, { key: v, label, items: [] });
    /** @type {any} */ (by.get(v)).items.push(x);
  }
  const fixed = FIXED[g];
  return [...by.values()].sort((a, b) => fixed ? fixed.indexOf(a.key) - fixed.indexOf(b.key) : (!a.key ? 1 : 0) - (!b.key ? 1 : 0) || a.label.localeCompare(b.label));
}

/** The key a group's collapsed state is kept under: the grouping and the value (an organisation or a project code), never a person.
    @param {string} g @param {string} v @param {string} [sub] @param {string} [sv] */
export const pdKey = (g, v, sub, sv) => `${g}|${v}${sub ? `|${sub}|${sv}` : ""}`;

/** The columns to draw, in order: the saved ones that exist, Name first and always. @param {PdState} st */
export const pdColumns = st => st.cols.filter(k => PD_KEYS.includes(k));

/** The Order by options: [value, label]; the starting sort is named. */
export const PD_ORDER = /** @type {[string, string][]} */ (PD_COLS.map(c => [c[0], c[0] === PD_DEFAULT_SORT.col ? `${c[1]} (default)` : c[1]]).filter(c => c[0] !== "proj"));
