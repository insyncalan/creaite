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
    ? `<a class="tlink" href="${esc(x.href)}" target="_blank" rel="noopener noreferrer">${esc(x.t)}</a>`
    : esc(x.t))).join("");
}
/** One link in the stored form; null when the address is refused. @param {string} words @param {string} href @returns {string|null} */
export function linkWrite(words, href) {
  const a = linkUrl(href);
  if (!a || !words) return null;
  const addr = /^(?:[^()\s]|\([^()\s]*\))+$/.test(a) ? a : a.replace(/\(/g, "%28").replace(/\)/g, "%29");
  return `[${words.replace(/[[\]\\]/g, "\\$&")}](${addr})`;
}
