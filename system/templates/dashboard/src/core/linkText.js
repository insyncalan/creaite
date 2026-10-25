// @ts-check
/* core/linkText.js (#121): links in PLAIN text. The item panel's free-text fields, Prep's notes and the like store plain text, so a
   link in them is kept as `[words](address)` and shown, everywhere the text is shown, as the words (a link where a link can work).
   This file is the one reader and writer of that form in the dashboard; the address check is core/linkUrl.js's alone (never a second
   one): a `[words](address)` whose address `linkUrl` refuses is NOT a link, it stays the literal text it is, so a hostile address is
   never made into one, whoever wrote it. (system/scripts/linktext.py is the same form for the reports, exports and search; it can only
   be stricter than this check, and dev/tests/test_link_text.py runs both against one set of cases.)

   The form: `[` words `](` address `)`. In the words, `[`, `]` and `\` are written `\[`, `\]` and `\\`. An address has no space and its
   brackets balance one level deep (`a_(b)`); one that does not is percent-encoded when it is written (`%28`, `%29`).

   - linkSegments(text): the text cut into plain pieces and links, [{t, href?}].
   - linkWords(text): the words only, no address (search, sort, matching, a title in a message).
   - linkWithAddress(text): "words (address)" (a plain copy, where a link cannot work).
   - linkHtml(text): safe markup, escaped, a link as <a class="tlink" href target="_blank" rel="noopener noreferrer">.
   - linkWrite(words, href): one link in the stored form. */
import { esc } from "./dom.js";
import { linkUrl } from "./linkUrl.js";
import { SENT_CONFUSABLES } from "./sentConfusables.js";

/** A link as stored. Group 1 the words (escaped), group 2 the address. */
const LINK = /\[((?:[^[\]\\\n]|\\[[\]\\])+)\]\(((?:[^()\s]|\([^()\s]*\))+)\)/g;

/** The words with their escapes taken off. @param {string} s */
const unwords = s => s.replace(/\\([[\]\\])/g, "$1");

/** @typedef {{t: string, href?: string}} Seg */
/** The text cut into plain pieces and links. A link is only where its address is one `linkUrl` accepts.
    @param {unknown} text @returns {Seg[]} */
export function linkSegments(text) {
  const s = typeof text === "string" ? text : text == null ? "" : String(text);
  /** @type {Seg[]} */
  const out = [];
  let at = 0, plain = "";
  for (const m of s.matchAll(LINK)) {
    const href = linkUrl(m[2]);
    if (!href || m.index == null) continue;                              // not an address creaite links: the characters stay as they are
    plain += s.slice(at, m.index);
    if (plain) out.push({ t: plain });
    plain = "";
    out.push({ t: unwords(m[1]), href });
    at = m.index + m[0].length;
  }
  plain += s.slice(at);
  if (plain) out.push({ t: plain });
  return out;
}

/** Whether the text holds a link. @param {unknown} text */
export const hasLink = text => typeof text === "string" && text.includes("](") && linkSegments(text).some(x => x.href);
/** The words only. @param {unknown} text @returns {string} */
export const linkWords = text => (typeof text === "string" && !text.includes("](") ? text : linkSegments(text).map(x => x.t).join(""));
/** "words (address)" for a link, where a link cannot work. @param {unknown} text @returns {string} */
export const linkWithAddress = text => linkSegments(text).map(x => (x.href ? `${x.t} (${x.href.replace(/^mailto:/i, "")})` : x.t)).join("");
/** Safe markup for the text: escaped, a link as an anchor that opens in a new tab and never hands over the opener. @param {unknown} text @returns {string} */
export function linkHtml(text) {
  return linkSegments(text).map(x => (x.href
    ? `<a class="tlink" href="${esc(linkUrl(x.href))}" target="_blank" rel="noopener noreferrer">${esc(x.t)}</a>`
    : esc(x.t))).join("");
}
/** One link in the stored form; null when the address is refused. @param {string} words @param {string} href @returns {string|null} */
export function linkWrite(words, href) {
  const a = linkUrl(href);
  if (!a || !words) return null;
  const addr = /^(?:[^()\s]|\([^()\s]*\))+$/.test(a) ? a : a.replace(/\(/g, "%28").replace(/\)/g, "%29");
  return `[${words.replace(/[[\]\\]/g, "\\$&")}](${addr})`;
}

/* ===== #153, #368 ===== the dated "I sent it" lines (17-10-2026: Chased Sara by email (reminder 1); ...) are internal: they never go into an email body.
   The same rule as linktext.sent_strip in Python (dev/tests/test_sent_parity_368.py feeds both the same fixtures): fail closed. The text is read on its
   plain form (simple HTML as lines, CRLF as LF, then the form edit_ai.normal makes: NFKC, invisible characters gone, marks gone, look-alike dashes and
   letters plain), in any case and spacing, anywhere on a line, a date in either order, the name allowed to break over one line. The date, its colon,
   the verb and "by email|message" must all be there, so ordinary prose that only says "chased" or "asked" never matches. A line left empty by the cut
   is dropped. */
const SENT_NL = "\\n\\r\\v\\f\\u0085\\u2028\\u2029";
const SENT_DATE = "(?:\\d{2}\\s*-\\s*\\d{2}\\s*-\\s*\\d{4}|\\d{4}\\s*-\\s*\\d{2}\\s*-\\s*\\d{2})";
const SENT_SRC = `(?<!\\d)${SENT_DATE}\\s*:\\s*(?:chased|emailed|asked)\\s+(?:[^${SENT_NL}]*?(?:\\r\\n|[${SENT_NL}])[ \\t]*)?[^${SENT_NL}]*?\\bby\\s+(?:email|message)\\b[^${SENT_NL}]*`;
const SENT_CUT = "\uE000";
const SENT_TAGS = /<\/?(?:p|br|li|ul|ol|div|span|b|i|em|strong)\b[^>]*>/i;
const SENT_LOOK = Object.fromEntries(Object.entries(SENT_CONFUSABLES).flatMap(([to, from]) => [...from].map(c => [c, to])));   /* generated from Python's table */
const SENT_UNSEEN = new RegExp("[\\p{Cf}\\u00ad\\u034f\\u115f\\u1160\\u17b4\\u17b5\\u180b-\\u180f\\u3164\\ufe00-\\ufe0f\\uffa0\\ufff0-\\ufff8\\u{e0000}-\\u{e0fff}\\u0000-\\u0008\\u000e-\\u001f\\u007f-\\u0084\\u0086-\\u009f]", "gu");
const sentLookRe = new RegExp("[" + Object.keys(SENT_LOOK).join("") + "]", "gu");
const sentLook = t => t.replace(sentLookRe, c => SENT_LOOK[c]);
const SENT_LINEISH = new RegExp("[\\u000b\\u000c\\u001c-\\u001e\\u0085]", "g");
const sentUnseen = t => t.replace(SENT_LINEISH, "\n").replace(SENT_UNSEEN, "").replace(/⠀/g, " ");
const sentUnmark = t => t.normalize("NFKD").replace(/\p{M}/gu, "");
const sentNormal = t => {
  t = sentLook(sentUnmark(sentLook(sentUnseen(t))));
  t = sentLook(sentUnseen(t.normalize("NFKC")));
  return t.replace(/\p{Nd}/gu, c => { let x = c.codePointAt(0), d = 0; while (/\p{Nd}/u.test(String.fromCodePoint(x - 1))) { x--; d++; } return String(d % 10); });
};
const sentPlain = text => {
  let t = String(text == null ? "" : text).replace(/\r\n?/g, "\n");
  if (SENT_TAGS.test(t)) t = t.replace(/<\/(?:p|li|div)>|<br\s*\/?>/gi, "\n").replace(/<\/?(?:p|br|li|ul|ol|div|span|b|i|em|strong)\b[^>]*>/gi, "").replace(/&nbsp;/g, " ").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&");
  return sentNormal(t.replace(/ /g, " "));
};
/** Whether a text holds an "I sent it" line. @param {unknown} text */
export function sentHas(text) { return new RegExp(SENT_SRC, "i").test(sentPlain(text)); }
/** @param {unknown} text */
export function sentStrip(text) {
  if (!text) return String(text == null ? "" : text);
  const t = sentPlain(text);
  if (!new RegExp(SENT_SRC, "i").test(t)) return String(text);
  return t.replace(new RegExp(SENT_SRC, "gi"), SENT_CUT).split("\n").filter(l => !(l.includes(SENT_CUT) && !l.replace(/[\uE000 \t\-*•–]/g, ""))).map(l => l.replaceAll(SENT_CUT, "")).join("\n").trim();
}
