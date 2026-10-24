// @ts-check
/* #312: Your profile. Alan's own entry in the people register (name, email, other ways people write his name, organisation,
   role), read and edited in Settings › Essentials and asked for once on Today's Getting started ("About you").
   - It adds no store of its own. The details are the register entry's, so they are saved like any person's (regEdit: a backup,
     a log line, Undo). Which person is "you" is the setting identity.name (settings.json on this computer), never a column in
     the shared register.
   - The email is a label. Nothing here, or anywhere, treats it as proof of who is using creaite or lets it open anything.
   - "Not now" is remembered in this browser; the Settings card stays. */
import { $, esc, raw, swapHTML } from "./core/dom.js";
import { shared } from "./core/state.js";
import { renderSetup } from "./today.js";
import { go } from "./core/nav.js";
import { snack } from "./core/server.js";
import { S, store } from "./core/page.js";
import { saveSettings } from "./stores/settings.js";
import { askPerson, pBlank, pCell, pFind, pKey, regSave } from "./settings.js";

export const PROFILE_ASKED_KEY = "creaite-profile-asked";
/** The rows in the register you have said are yours, in this browser only (a name that was already someone's asks first). */
export const PROFILE_CLAIMED_KEY = "creaite-profile-claimed";

/** Your name as the register writes it (a "|" or a line break is stored as "/" or a space), so a lookup and a save agree.
    "" when no name is set: the placeholder name the page starts with is never used, never written. */
export const myName = () => S.meSet === false ? "" : pCell(String(S.me || "").trim());
const claimedList = () => { try { const v = store.get(PROFILE_CLAIMED_KEY, []); return Array.isArray(v) ? v : []; } catch (e) { return []; } };
const claimed = (/** @type {string} */ n) => claimedList().includes(pKey(n));
const claim = (/** @type {string} */ n) => { try { store.set(PROFILE_CLAIMED_KEY, [...new Set([...claimedList(), pKey(n)])]); } catch (e) { /* asked again next time */ } };

/** An address as a person's key: trimmed, lower case, the first one when several are listed. Never a name. @param {unknown} e */
export const emailKey = e => String(e || "").split(/[,;]/)[0].trim().toLowerCase();

/** Every address listed, as keys. @param {unknown} e */
export const emailKeys = e => String(e || "").split(/[,;]/).map(x => x.trim().toLowerCase()).filter(Boolean);
/** A row by name, or by one of its other ways of writing the name (the People page treats an alias the same way). @param {any[]} L @param {string} n */
export const pFindOrAlias = (L, n) => pFind(L, n) || L.find(p => (p.aliases || []).some((/** @type {string} */ a) => pKey(a) === pKey(n)));

/** Your own register entry, found by your name or an alias of it (an address is only known once it is in the entry). null when you aren't in the register yet. */
export function profileEntry() {
  const me = myName(); if (!me) return null;
  return pFindOrAlias(shared.REG, me) || null;
}
/** #348: your entry only once you have said it is yours ("this is me", #312 M2). A colleague whose name matches yours is not you:
    nothing of theirs (email, organisation, role) is shown as yours, nor counted as your details being in. null otherwise. */
export function profileMine() {
  const p = profileEntry(); return p && claimed(myName()) ? p : null;
}
/** The details shown: what the register holds for you, once the row is yours (empty strings when it holds nothing or isn't yours yet). */
export function profileDetails() {
  const p = profileMine();
  return { name: myName(), email: p ? String(p.email || "") : "", aliases: p ? (p.aliases || []) : [], org: p ? p.org || "" : "", role: p ? p.role || "" : "" };
}
/** Done when you have a name and an email in your entry. */
export const profileDone = () => { const d = profileDetails(); return !!d.name && !!emailKey(d.email); };

const askedBefore = () => { try { return !!store.get(PROFILE_ASKED_KEY, false); } catch (e) { return false; } };
/** The first-run question is shown until the details are in or "Not now" is pressed. */
export const profileQuestionDue = () => !profileDone() && !askedBefore();

/** Save the details you typed into your register entry (the name itself is a setting). With merge (an entry that is someone
    else's by address): what is there is kept, a field you left empty is never blanked, aliases are added to, and your name is
    added as another way to write theirs so the card finds it.
    @param {{email:string, aliases:string[], org:string, role:string}} f @param {boolean} [merge] */
export async function profileSave(f, merge = false) {
  const name = myName(); if (!name) { snack("Add your name first"); return false; }
  const keys = emailKeys(f.email);
  /* #312 L2: an address, once there is one, is the key (any address listed); the name or an alias only finds the entry before that */
  const ok = await regSave(`Changed ${name} in the people register`, L => {
    let r = (keys.length && L.find(p => emailKeys(p.email).some(k => keys.includes(k)))) || pFindOrAlias(L, name);
    if (!r) { r = pBlank(name); L.push(r); }
    if (!merge) { Object.assign(r, { email: f.email, aliases: f.aliases, org: f.org, role: f.role }); return L; }
    const al = [...(r.aliases || [])];
    for (const a of [...f.aliases, ...(pKey(r.name) === pKey(name) ? [] : [name])]) if (a && pKey(a) !== pKey(r.name) && !al.some((/** @type {string} */ x) => pKey(x) === pKey(a))) al.push(a);
    Object.assign(r, { email: f.email || r.email, aliases: al, org: f.org || r.org, role: f.role || r.role }); return L;
  });
  if (ok) claim(name);
  return ok;
}
/** Open the same details form a person's page uses, for you. */
export async function profileEdit() {
  const name = myName(); if (!name) { snack("Add your name first"); return false; }
  const p = profileEntry();
  /* #312 M2: a row that is already in the register, and that you haven't said is yours, may be a colleague's: ask first */
  if (p && !claimed(name) && !confirm(`“${p.name}” is already in the people register${p.email ? ` (${p.email})` : ""}. Is that row you? Editing it changes it for everyone who uses this register.`)) return false;
  if (p && !claimed(name)) claim(name);                       /* said yes: it is yours from now on, and is not asked again */
  const res = await askPerson(p ? { edit: true, person: p } : { details: true, person: pBlank(name) });
  if (!res || !res.person) return false;
  const { name: _n, ...f } = res.person;
  const keys = emailKeys(f.email);
  const other = keys.length ? shared.REG.find(q => q !== p && emailKeys(q.email).some(k => keys.includes(k))) : null;
  if (other) {
    /* say what will change: the fields you filled in that differ from the row, and your name added to theirs; nothing is blanked */
    const will = [];
    if (f.aliases.some((/** @type {string} */ a) => !(other.aliases || []).some((/** @type {string} */ x) => pKey(x) === pKey(a)))) will.push("other ways of writing the name");
    if (f.org && f.org !== other.org) will.push("organisation");
    if (f.role && f.role !== other.role) will.push("role");
    if (pKey(other.name) !== pKey(name)) will.push(`“${name}” as another way of writing ${other.name}`);
    if (!confirm(`${f.email} is already ${other.name}'s address in the people register. Change ${other.name}'s row? ${will.length ? `It keeps everything already there and adds: ${will.join(", ")}.` : "It keeps everything already there and changes nothing else."}`)) return false;
    return profileSave(f, true);
  }
  return profileSave(f);
}

/** The Settings card. */
export function profileCardHtml() {
  const d = profileDetails(), line = (/** @type {string} */ l, /** @type {string} */ v, /** @type {string} */ id) =>
    `<div class="srow"><div><span id="${id}Lab">${l}</span></div><div><span id="${id}">${v ? esc(v) : '<span class="sub">Not set</span>'}</span></div></div>`;
  return `<div class="card" id="profileCard" data-sec="profile"><h2>Your profile</h2>
   <div class="srow"><div><span id="pfNameLab">Your name</span><small>Which person in the people register is you</small></div><div><input type="text" id="pfName" aria-labelledby="pfNameLab" value="${esc(S.meSet === false ? "" : pCell(String(S.me || "").trim()))}" autocomplete="off"> <button type="button" class="btn" id="pfNameSave">Save name</button></div></div>
   ${line("Email", d.email, "pfEmail")}${line("Other ways people write your name", d.aliases.join(", "), "pfAliases")}${line("Organisation", d.org, "pfOrg")}${line("Role", d.role, "pfRole")}
   <div class="srow"><div><span id="pfDetailsLab">Details</span><small>Saved in the people register, like anyone else's, and you can undo a change</small></div><div><button type="button" class="btn primary" id="pfEdit" ${d.name ? "" : "disabled"}>${profileMine() ? "Edit my details" : "Add my details"}</button></div></div>
   <p class="sub" id="pfNote">Your email is a label only. creaite doesn't check it, and it doesn't give you or anyone else access to anything. Which person is you is kept in this computer's settings, not in the shared register.</p></div>`;
}
/** Draw the card again, in place. */
export function profileRedraw() { const c = $("#profileCard"); if (c) { swapHTML(c, raw(profileCardHtml())); profileWire(); } }
/** Wire the card's buttons (called after it is drawn). */
export function profileWire() {
  const b = $("#pfEdit"); if (b) b.onclick = async () => { await profileEdit(); profileRedraw(); };
  const s = $("#pfNameSave"); if (s) s.onclick = async () => {
    const v = pCell(String(/** @type {HTMLInputElement} */ ($("#pfName")).value || ""));
    if (!v) { snack("Your name can't be empty"); return; }
    if (await saveSettings({ "identity.name": v })) { S.me = v; snack("Your name is saved"); }
    profileRedraw();
  };
}

/** Today's Getting started: the first question, "" when it isn't due. */
export function profileQuestionHtml() {
  return profileQuestionDue() ? `<div class="tb" id="pfQ"><span class="t">About you</span><p>Add your name and email so creaite knows which items are yours. You can change this any time in Settings.</p>
    <span class="rmgo"><button type="button" class="btn primary" data-pfq="yes">Add my details</button> <button type="button" class="btn" data-pfq="no">Not now</button></span></div>` : "";
}

/** The start-up step: the question's two buttons. */
export function bootProfile() {
  document.addEventListener("click", async e => {
    const q = /** @type {HTMLElement|null} */ ((/** @type {HTMLElement} */ (e.target)).closest("[data-pfq]")); if (!q) return;
    e.preventDefault();
    if (q.dataset.pfq === "no") { try { store.set(PROFILE_ASKED_KEY, true); } catch (x) { /* kept for this visit only */ } snack("Okay. Settings › Essentials › Your profile has it when you want it"); if (shared.VIEW === "today") renderSetup(); return; }
    if (!String(S.me || "").trim()) { go("settings", "profile"); return; }
    if (await profileEdit() && shared.VIEW === "today") renderSetup();
  });
}
