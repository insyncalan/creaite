// @ts-check
/* core/partners.js (#228 C): what a partner organisation's name may be. One set of rules, said the same in build_dashboard.py
   (partner_name_problem, which reads the Partners line on the server) and here (the page, and the line's write in core/server.js):
   1 to 60 characters; Unicode letters and digits, spaces and . , & ' - ( ) only; no control, separator, bidi or zero-width
   character, no accent mark on its own, no space at either end, no double space; the same name once (capitals, accents and
   punctuation do not make a second one). The names are joined by "; ", so a name can never hold the separator. */

export const PARTNER_NAME_MAX = 60;
export const PARTNERS_MAX = 12;               // the server keeps at most 12 (build_dashboard.PARTNERS_MAX)
export const PARTNERS_LINE_MAX = 800;         // 12 names of 60 and the separators
export const CLIENT_NAME_LIMIT = 80;
const PUNCT = ".,&'()-";

/** The usual tidy-up of a typed name: NFC, runs of spaces made one, none at either end. Nothing else changes. @param {string} text */
export const cleanPartnerName = text => String(text == null ? "" : text).normalize("NFC").replace(/ {2,}/g, " ").replace(/^ +| +$/g, "");

/** A name's problem in plain words, or "". The name is checked as given (clean it first). @param {string} name @returns {string} */
export function partnerNameProblem(name) {
  const t = String(name == null ? "" : name);
  if (!t) return "Type the partner organisation's name.";
  if (/[\r\n]/.test(t)) return "A partner's name is one line.";
  if (t.includes(";")) return "A partner's name can't contain a semicolon; add each partner on its own.";
  if (t.length > PARTNER_NAME_MAX) return `A partner's name is over ${PARTNER_NAME_MAX} characters.`;
  if (t !== t.replace(/^ +| +$/g, "") || t.includes("  ")) return "A partner's name has no space at either end and no double space.";
  if (t !== t.normalize("NFC")) return "A partner's name uses letters and digits only (no separate accent marks).";
  for (const ch of t) if (!(ch === " " || PUNCT.includes(ch) || /^[\p{L}\p{Nd}]$/u.test(ch))) return "A partner's name uses letters, digits, spaces and . , & ' - ( ) only.";
  return "";
}

/** What makes two names the same organisation: letters and digits only, accents and capitals folded (as build_dashboard.partner_key).
    @param {string} name */
export function partnerKey(name) {
  const k = String(name).normalize("NFKD").replace(/[^ -~]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "");
  return k || String(name).toLowerCase();
}

/** A value that may not go into any line of the memory file: a control, line or paragraph separator, bidi or zero-width character.
    @param {string} v */
export function unsafeLineValue(v) {
  for (const ch of String(v)) {
    const c = /** @type {number} */ (ch.codePointAt(0));
    if (c < 0x20 || (c >= 0x7f && c <= 0x9f) || c === 0x2028 || c === 0x2029 || (c >= 0x200b && c <= 0x200f) || (c >= 0x202a && c <= 0x202e)
      || (c >= 0x2060 && c <= 0x2069) || c === 0xfeff) return true;
  }
  return false;
}
