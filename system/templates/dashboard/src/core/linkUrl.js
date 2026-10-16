// @ts-check
/* core/linkUrl.js (#120): the ONE check on a link's address. This is a security control: an address that comes from anywhere
   (typed in the link popover, pasted, read from a note or Current state, or set by code) is accepted only if `linkUrl` says so,
   and the editor, the popover, load and paste all ask this one function. Nothing here has imports, so it is easy to read and test.

   What is allowed: http, https and mailto, and nothing else. Everything is refused that could run script or reach the machine
   (javascript:, data:, file:, vbscript:, blob:, about:, ftp: and any other scheme, in any mix of upper and lower case), and
   everything that hides what it is: a space, newline, tab or any control or invisible character anywhere (browsers drop tabs and
   newlines inside a scheme, "java\tscript:"), a character-entity (&#106; or &colon;), a backslash, a protocol-relative address
   (//host), a relative one (no scheme), a quote, angle bracket or back-tick, and an address with a name and password in it
   (https://bank.example@evil.example). A leading or trailing space is refused here too: `typedLinkUrl` is the one place that
   trims what a person typed, then asks `linkUrl`.

   `linkUrl(s)` gives the address to store (the scheme in lower case; nothing else is rewritten) or null. */

/** The longest address kept. */
export const LINK_MAX = 2048;

/** Control characters, spaces of every kind, the invisible marks and the line and paragraph separators. */
// eslint-disable-next-line no-control-regex
const BAD_CHARS = /[\u0000-\u0020\u007f-\u00a0\u00ad\u061c\u115f\u1160\u1680\u180e\u2000-\u200f\u2028-\u202f\u205f-\u206f\u3000\u3164\ufeff\uffa0\ufff9-\ufffb]/;
/** A character-entity, numeric or named ("&#106;", "&#x6A;", "&colon;", "&Tab;"). A bare "&" in a query ("a=1&b=2") is fine. */
const ENTITY = /&(?:#\d|#x[\da-f]|[a-z][a-z\d]*;)/i;

/** The address to keep for `s`, or null when it must not be linked.
    @param {unknown} s @returns {string|null} */
export function linkUrl(s) {
  if (typeof s !== "string" || !s || s.length > LINK_MAX) return null;
  if (BAD_CHARS.test(s) || ENTITY.test(s) || /[\\<>"`]/.test(s)) return null;
  const m = /^([a-z][a-z\d+.-]*):/i.exec(s);
  if (!m) return null;                                                   // no scheme: relative, protocol-relative (//host) or bare text
  const scheme = m[1].toLowerCase(), rest = s.slice(m[0].length);
  if (scheme === "http" || scheme === "https") {
    const a = /^\/\/([^/?#]*)/.exec(rest);
    if (!a || !a[1]) return null;                                        // "https:example.com", "https:///x": not an address
    const host = a[1];
    if (host.includes("@")) return null;                                 // a name and password before the host hides where it goes
    if (!/^(?:[a-z\d](?:[a-z\d-]*[a-z\d])?|\[[\da-f:.]+\])(?:\.[a-z\d](?:[a-z\d-]*[a-z\d])?)*(?::\d{1,5})?$/i.test(host) && !/[^\x00-\x7f]/.test(host)) return null;
    try { const u = new URL(scheme + ":" + rest); if (u.protocol !== scheme + ":" || !u.hostname || u.username || u.password) return null; } catch (e) { return null; }
    return scheme + ":" + rest;
  }
  if (scheme === "mailto") {
    const who = rest.split(/[?#]/)[0];
    if (!/^[^@\s,;]+@[^@\s,;]+$/.test(safeDecode(who))) return null;      // one address (no list: it would hide who gets it)
    return "mailto:" + rest;
  }
  return null;
}

/** A percent-decoding that never throws (a bad escape is left as it is). @param {string} s */
function safeDecode(s) { try { return decodeURIComponent(s); } catch (e) { return s; } }

/** Whether `s` is an address `linkUrl` accepts. @param {unknown} s @returns {boolean} */
export const isLinkUrl = s => linkUrl(s) !== null;

/** What a person typed or pasted as an address: surrounding spaces taken off, "example.com" or "www.example.com/x" given https://,
    "name@example.com" given mailto:, then checked by `linkUrl`. Null when it is not an address creaite will link. A scheme the
    person wrote is never guessed at: "javascript:alert(1)" is refused, not turned into a web address.
    @param {unknown} s @returns {string|null} */
export function typedLinkUrl(s) {
  if (typeof s !== "string") return null;
  const t = s.replace(/^[ \t\r\n]+|[ \t\r\n]+$/g, "");
  if (!t) return null;
  if (/^[a-z][a-z\d+.-]*:/i.test(t) && !/^[^/?#@\s]+\.[^/?#@\s]+:\d/.test(t)) return linkUrl(t);          // it names a scheme: judged as it is ("host.com:8080/x" is not a scheme)
  if (t.startsWith("//") || t.startsWith("\\")) return null;
  if (/^[^\s@/?#:]+@[^\s@/?#:]+\.[^\s@/?#:]+$/.test(t)) return linkUrl("mailto:" + t);
  if (/^(?:[a-z\d-]+\.)+[a-z]{2,}(?::\d{1,5})?(?:[/?#]\S*)?$/i.test(t)) return linkUrl("https://" + t);
  return null;
}

/** An address a note keeps for creaite's own links (a work item or a person), which are not web addresses and never open anywhere.
    @param {unknown} s @returns {boolean} */
export const isInternalHref = s => typeof s === "string" && /^creaite:(?:item|person)\/[^\s<>"`\\]+$/.test(s) && !BAD_CHARS.test(s);

/** Whether a link already in a document may stay in it: a web or mail address `linkUrl` accepts, or one of creaite's own.
    @param {unknown} s @returns {boolean} */
export const keepHref = s => isLinkUrl(s) || isInternalHref(s);
