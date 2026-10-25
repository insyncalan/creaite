"""Links in plain text (#121): `[words](address)`, read wherever the text is shown, exported or searched.

The item panel's longer text fields (latest update, response, reasoning, options, client messaging) and Prep's notes are plain text, so a
link in them is kept as `[words](address)` (the dashboard's `core/linkText.js` writes it). Everything that shows or exports that text goes
through this module, so the raw characters never show: the words, as a link where a link can work, as "words (address)" where it cannot,
and the words alone where only the words matter (search, matching, sorting).

The address check is the dashboard's one validator (`core/linkUrl.js`: http, https and mailto, nothing else, in no disguise). This module
cannot call JavaScript, so `valid_address` is that check written again for the Python side; it is deliberately only ever STRICTER (an
address it refuses is shown as the plain text it is, never as a link), and `dev/tests/test_editor_links_plain.py` runs both against one
set of cases to keep it so. Nothing else in Python decides whether an address is a link.

The form: `[` words `](` address `)`. In the words, `[`, `]` and `\\` are written `\\[`, `\\]` and `\\\\`. An address has no space and its
brackets balance one level deep (`a_(b)`); one that does not is percent-encoded when it is written.
"""
import ipaddress
import re
import sys
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402,F401  (the one place locations are defined; every script imports it)

LINK_MAX = 2048
LINK = re.compile(r"\[((?:[^\[\]\\\n]|\\[\[\]\\])+)\]\(((?:[^()\s]|\([^()\s]*\))+)\)")
_BAD = re.compile("[\u0000-\u0020\u007f-\u00a0\u00ad\u061c\u115f\u1160\u1680\u180e\u2000-\u200f\u2028-\u202f"
                  "\u205f-\u206f\u3000\u3164\ufeff\uffa0\ufff9-\ufffb]")             # controls, spaces and invisible marks
_ENTITY = re.compile(r"&(?:#\d|#x[\da-f]|[a-z][a-z\d]*;)", re.I)
_SCHEME = re.compile(r"^([a-z][a-z\d+.-]*):", re.I)
_HOST = re.compile(r"^(?:[a-z\d](?:[a-z\d-]*[a-z\d])?|\[[\da-f:.]+\])(?:\.[a-z\d](?:[a-z\d-]*[a-z\d])?)*(?::(\d{1,5}))?$", re.I | re.A)
_ONE_ADDRESS = re.compile(r"^[^@\s,;]+@[^@\s,;]+$")


def _host_ok(netloc):
    """Beyond the shape: a bracketed host is a real IPv6 address, and a host ending in a number is a real IPv4 one."""
    host = netloc if netloc.endswith("]") else re.sub(r":\d{1,5}$", "", netloc)
    if host.startswith("["):
        try:
            ipaddress.IPv6Address(host[1:-1])
        except ValueError:
            return False
        return True
    last = host.split(".")[-1]
    if last.isdigit() or re.match(r"^0x", last, re.I):
        try:
            ipaddress.IPv4Address(host)
        except ValueError:
            return False
    return True


def _web_address(scheme, rest):
    """The address when it is a well-formed http or https one (a host, a real port, no name and password), else None."""
    a = re.match(r"^//([^/?#]*)", rest)
    if not a or not a.group(1) or "@" in a.group(1):
        return None
    host = _HOST.match(a.group(1))
    if not host or (host.group(1) and int(host.group(1)) > 65535) or not _host_ok(a.group(1)):
        return None
    return scheme + ":" + rest


def _strict_unquote(s):
    """`s` with every percent escape decoded, or None when one is bad (a stray % or bad UTF-8): refused, never left as written."""
    if re.search(r"%(?![\da-f]{2})", s, re.I):
        return None
    try:
        return unquote(s, errors="strict")
    except UnicodeDecodeError:
        return None


def _mail_address(rest):
    """The address when it is mailto: exactly one mailbox, as a mail program decodes it (a list would hide who gets it), and a query
    of subject and body only (bcc and cc would add receivers), else None."""
    if "#" in rest:
        return None
    who, _, query = rest.partition("?")
    who = _strict_unquote(who)
    if who is None or not _ONE_ADDRESS.match(who):
        return None
    for part in (query.split("&") if "?" in rest else []):
        if not part:
            continue
        key, eq, val = part.partition("=")
        key, val = _strict_unquote(key), _strict_unquote(val)
        if key is None or val is None or key.lower() not in ("subject", "body"):
            return None
    return "mailto:" + rest


def valid_address(s):
    """The address to link for `s` (scheme in lower case), or None: http, https and mailto only. Never looser than the dashboard's."""
    if not isinstance(s, str) or not s or len(s) > LINK_MAX:
        return None
    if _BAD.search(s) or _ENTITY.search(s) or re.search(r"[\\<>\"`]", s):
        return None
    m = _SCHEME.match(s)
    if not m:
        return None
    scheme, rest = m.group(1).lower(), s[m.end():]
    if scheme in ("http", "https"):
        return _web_address(scheme, rest)
    return _mail_address(rest) if scheme == "mailto" else None


def _unwords(s):
    return re.sub(r"\\([\[\]\\])", r"\1", s)


def segments(text):
    """The text cut into pieces: [(text, address or None)]. A piece has an address only when `valid_address` accepts it; any other
    `[words](address)` stays the literal characters it is."""
    s = "" if text is None else str(text)
    out, at, plain = [], 0, ""
    for m in LINK.finditer(s):
        href = valid_address(m.group(2))
        if not href:
            continue
        plain += s[at:m.start()]
        if plain:
            out.append((plain, None))
        plain = ""
        out.append((_unwords(m.group(1)), href))
        at = m.end()
    plain += s[at:]
    if plain:
        out.append((plain, None))
    return out


def has_link(text):
    """Whether the text holds a link creaite would make (an address the check accepts)."""
    return isinstance(text, str) and "](" in text and any(h for _, h in segments(text))


def words(text):
    """The words only: no brackets, no address (search, matching, sorting)."""
    if not isinstance(text, str) or "](" not in text:
        return "" if text is None else str(text)
    return "".join(t for t, _ in segments(text))


def with_address(text):
    """"words (address)" for a link, for a plain copy or anywhere a link cannot work (a mailto address without its scheme)."""
    if not isinstance(text, str) or "](" not in text:
        return "" if text is None else str(text)
    return "".join(f"{t} ({re.sub('^mailto:', '', h, flags=re.I)})" if h else t for t, h in segments(text))


def addresses(text):
    """Every linked address in the text, in order (for a check that must treat the address like text)."""
    return [h for _, h in segments(text) if h] if isinstance(text, str) and "](" in text else []


def checkable(text):
    """The text with each address spelled out after its words, for a check that reads text (a client-safe word, a confidentiality marker):
    the address is judged like the words are, and a marker hidden in either is found."""
    if not isinstance(text, str):
        return "" if text is None else str(text)
    return with_address(text) if "](" in text else text


def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;")


def html(text, cls="tlink"):
    """Safe markup: the text escaped, a link as an anchor that opens in a new tab (target _blank, rel noopener noreferrer)."""
    return "".join(
        f'<a class="{cls}" href="{_esc(h)}" target="_blank" rel="noopener noreferrer">{_esc(t)}</a>' if h else _esc(t)
        for t, h in segments(text))


def write(words_, href):
    """One link in the stored form, or None when the address or the words are refused."""
    a = valid_address(href)
    if not a or not words_:
        return None
    if not re.fullmatch(r"(?:[^()\s]|\([^()\s]*\))+", a):
        a = a.replace("(", "%28").replace(")", "%29")
    return "[" + re.sub(r"[\[\]\\]", lambda m: "\\" + m.group(0), words_) + "](" + a + ")"


# ===== #153 ===== the dated lines "I sent it" writes on an item are INTERNAL. "17-10-2026: Chased Sara Example by email (reminder 1);
# reply asked for by 19-10-2026.", "...: Emailed Tom Reid by message asking for an update.", "...: Asked Chris Dunn for a decision by
# email.". They sit in an action's Latest update, a risk's Response or a decision's Reasoning (drafts.js sentLine writes one fixed
# shape), so plain code recognises them by that shape and no client path carries them; no schema change is needed.
# Fail closed (#368). A sent line wrongly NOT recognised (a false negative) lets Alan's chase log into a client text or an email: a
# leak, and the worse failure. A line wrongly recognised (a false positive) only has a line struck out or a draft held for a look.
# So the recognition is read on the plainest form of the text (HTML tags off, then edit_ai.normal: no-break and full-width spaces,
# a full-width colon, look-alike hyphens and invisible characters made plain), in any case and spacing, anywhere on a line (a bullet or
# a sentence before it), with a date in either order, and the name allowed to break over one line. The date, its colon, the verb and
# "by email|message" must all be there, so ordinary prose that only says "chased" or "asked" is never matched.
_NL = "\n\r\v\f\x85\u2028\u2029"
_SPAN = 400                      # #368 (review): the longest name, or text before "by", one scan allows; bounds the work per date start
_SENT_DATE = r"(?:\d{2}\s{0,50}-\s{0,50}\d{2}\s{0,50}-\s{0,50}\d{4}|\d{4}\s{0,50}-\s{0,50}\d{2}\s{0,50}-\s{0,50}\d{2})"
_NAME_BREAK = rf"(?:[^{_NL}]{{0,{_SPAN}}}?(?:\r\n|[{_NL}])[ \t]{{0,50}})?"
SENT_LINE = re.compile(rf"(?<!\d){_SENT_DATE}\s{{0,50}}:\s{{0,50}}(?:chased|emailed|asked)\s{{1,50}}"
                       rf"{_NAME_BREAK}[^{_NL}]{{0,{_SPAN}}}?\bby\s{{1,50}}(?:email|message)\b[^{_NL}]*", re.I)
_TAGS = re.compile(r"</?(?:p|br|li|ul|ol|div|span|b|i|em|strong)\b[^>]*>", re.I)
_BREAKS = re.compile(r"</(?:p|li|div)>|<br\s*/?>", re.I)
# Printable ASCII passes at once, except the markdown marks the check drops (* _ ~ ` and the backslash of an escape) and the table
# bar (read as a space), so "Cha*sed*", "17\\-10\\-2026" and "| Chased Sara | by email |" are read as their words (#368, fail closed).
_PLAIN_RUN = re.compile(r"[\x20-\x29\x2b-\x5b\x5d-\x5e\x61-\x7b\x7d\t\n]+")
_MARKS = "*_~`\\"
_FRONT = "*_~`\\| \t"              # marks, table bars and spaces directly before a cut line go with it


def _sent_norm(text):
    """Simple HTML as plain lines, CRLF as LF, no-break spaces as spaces (what the recognition reads first)."""
    t = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    if _TAGS.search(t):
        import html
        t = html.unescape(_TAGS.sub("", _BREAKS.sub("\n", t)))
    return t.replace("\u00a0", " ")


_NORM1 = {}


def _norm1(c):
    """edit_ai.normal of one character, remembered (a long text repeats few characters)."""
    r = _NORM1.get(c)
    if r is None:
        import edit_ai
        if len(_NORM1) > 20000:
            _NORM1.clear()
        r = _NORM1[c] = edit_ai.normal(c)
    return r


def _link_pieces(plain):
    """[(start, end)] of the link markup a [words](address) adds round its words: the opening bracket and "](address)"; and
    [(first word, link start)] to take a cut back to the start of its link."""
    cuts, starts = [], []
    if "](" not in plain:
        return cuts, starts
    for m in LINK.finditer(plain):
        cuts.append((m.start(), m.start() + 1))      # any address: a link the export shows as literal text hides a line too
        cuts.append((m.start(2) - 2, m.end()))
        starts.append((m.start() + 1, m.end(1), m.start()))
    return cuts, starts


def _sent_map(plain):
    """(form, at): the plain text on edit_ai.normal's form, one character at a time, and for each character of the form the position
    in `plain` it came from. Link markup, markdown marks and escapes are left out and a table bar is a space; printable ASCII passes
    as it is, so a long text is read quickly."""
    cuts = _link_pieces(plain)[0]
    out, at, pos, ci, n_all = [], [], 0, 0, len(plain)
    while pos < n_all:
        if ci < len(cuts) and pos >= cuts[ci][0]:
            pos = max(pos, cuts[ci][1])
            ci += 1
            continue
        limit = cuts[ci][0] if ci < len(cuts) else n_all
        m = _PLAIN_RUN.match(plain, pos, limit)
        if m:
            out.append(m.group())
            at.extend(range(pos, m.end()))
            pos = m.end()
            continue
        c = plain[pos]
        n = "" if c in _MARKS else " " if c == "|" else _norm1(c)
        out.append(n)
        at.extend([pos] * len(n))
        pos += 1
    return "".join(out), at


def sent_has(text):
    """Whether a text holds an "I sent it" line, however it is spaced, cased or written (links, markdown marks and a table's bars
    included)."""
    return bool(SENT_LINE.search(_sent_map(_sent_norm(text))[0]))


def sent_strip(text):
    """The text without its "I sent it" lines (and the blank lines they leave). A text without one comes back as it was. A text with
    one loses only that line, cut from its date to the line's end (fail closed: the rest of that line goes too); the rest keeps its own
    characters (accents, other scripts), with HTML as lines and CRLF as LF."""
    if not text:
        return text
    plain = _sent_norm(text)
    form, at = _sent_map(plain)
    starts = _link_pieces(plain)[1]
    spans = []
    for m in SENT_LINE.finditer(form):
        a = at[m.start()]
        for w0, w1, ls in starts:
            if w0 <= a < w1:
                a = ls                                                # inside a link's words: take the whole link
                break
        while a > 0 and plain[a - 1] in _FRONT and (not spans or a - 1 >= spans[-1][1]):
            a -= 1
        b = at[m.end()] if m.end() < len(form) else len(plain)       # the match runs to the line's end: take what the form left out
        spans.append((a, b))
    if not spans:
        return text
    t, last = [], 0
    for a, b in spans:
        t.append(plain[last:a])
        t.append("\x00")
        last = b
    t = "".join(t) + plain[last:]
    out = []
    for line in t.split("\n"):
        if "\x00" in line and not re.sub(r"[\x00 \t\-*\u2022\u2013]", "", line):
            continue                                                  # the line held only the cut line (and a bullet)
        out.append(line.replace("\x00", ""))
    return "\n".join(out).strip()
# ===== end #153 =====
