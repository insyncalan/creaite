"""#226: the HTML and PDF export of a weekly or client report is the report page's own "Show as exported" view.

The dashboard draws the report in its exported mode and posts the result with `/api/report/export` as
`page: {html, css, palette, version}`: `html` the page's markup, `css` the style rules that apply to it (the dashboard's own stylesheet,
filtered to what the page uses), `palette` the dashboard's palette name (so the file's colours are the theme's light ones) and `version`
the saved draft it was drawn from. A library: no command line. This module never trusts that post.

  - `build(doc, page, title)`: the file's text, or raises PageRefused. The markup is rebuilt through an allow-list (no script, event
    handler, form control, frame or external address; a picture is a data address only), the style rules are checked (no import, no
    address that isn't a data address), and the page is then checked against the server's own copy of the report: it was drawn from the
    version saved, every section in it is a shown section of `creaite_doc.clean(doc)`, no table has more rows than the report shows,
    and none of the words of the items the report's hidden rows name (read from the tracker: a saved report keeps only their
    references) or of hidden figures appear in it. A hidden section is kept out by its place (its id may not be in the page): a saved
    report keeps nothing of it, so its words can't be compared. A client report's words also go through client_leak.plain_findings, the
    check export and approve already use.
  - The file is fixed to the light theme and A4, with its colours kept in print; Chrome prints that same file for the PDF.

creaite_doc.render stays the fallback for the command line, for minutes and for any export with no page or a page that fails here;
the route then says it made the plain version (`plain: true`)."""
import base64
import html
import json
import re
import sys
import unicodedata
from html.parser import HTMLParser
from urllib.parse import unquote
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import creaite_doc  # noqa: E402
import paths  # noqa: E402,F401  (every script takes its locations from paths.py; this one reads and writes no file: its caller does)

MAX_HTML = 4_000_000
MAX_CSS = 1_500_000
MIN_NEEDLE = 6

DROP_WITH_CONTENT = {"script", "style", "iframe", "frame", "frameset", "object", "embed", "template", "noscript", "textarea",
                     "select", "option", "button", "form", "link", "meta", "base", "title", "head", "audio", "video", "canvas",
                     "applet", "dialog", "math"}
VOID = {"br", "hr", "img", "col", "wbr", "input"}
TAGS = {"div", "span", "section", "header", "footer", "main", "article", "aside", "nav", "h1", "h2", "h3", "h4", "h5", "h6", "p", "ul",
        "ol", "li", "dl", "dt", "dd", "table", "thead", "tbody", "tfoot", "tr", "th", "td", "caption", "colgroup", "col", "b", "i", "em",
        "strong", "u", "s", "del", "ins", "sub", "sup", "small", "mark", "code", "pre", "blockquote", "br", "hr", "img", "figure",
        "figcaption", "abbr", "time", "cite", "q"}
SVG_TAGS = {"svg", "g", "line", "circle", "ellipse", "rect", "path", "polyline", "polygon", "text", "tspan", "title", "desc", "defs",
            "lineargradient", "radialgradient", "stop", "clippath", "mask", "pattern", "marker", "use", "symbol"}
GLOBAL_ATTRS = {"class", "role", "title", "lang", "dir", "colspan", "rowspan", "scope", "span", "headers", "datetime",
                "width", "height", "alt", "aria-label", "aria-hidden", "aria-describedby", "aria-live", "tabindex"}
NEVER_ATTRS = {"href", "xlink:href", "srcset", "action", "formaction", "srcdoc", "ping", "poster", "background"}
# LEAK 1 (p240-leakfix): a CLIENT file keeps only these attributes (anything else could carry a hidden item's words or an item ID);
# the needles still run over every attribute that is kept. `data-id` only as a section's own marker, `data-type` for task lists.
CLIENT_ATTRS = {"class", "id", "colspan", "rowspan", "scope", "span", "width", "height", "role", "lang", "dir", "style", "src",
                "data-id", "data-type", "data-checked"}
CLIENT_SVG_ATTRS = {"viewbox", "x", "y", "x1", "y1", "x2", "y2", "cx", "cy", "r", "rx", "ry", "d", "points", "fill", "stroke",
                    "stroke-width", "stroke-dasharray", "stroke-linecap", "stroke-linejoin", "opacity", "fill-opacity",
                    "stroke-opacity", "fill-rule", "transform", "font-size", "font-weight", "font-family", "text-anchor",
                    "dominant-baseline", "preserveaspectratio", "xmlns", "offset", "stop-color", "stop-opacity", "gradientunits",
                    "gradienttransform", "dx", "dy", "letter-spacing", "text-decoration", "class", "style", "width", "height", "id"}
ITEM_ID = re.compile(r"[A-Z0-9]{3,7}-(?:[A-Z]-)?\d+")   # no \b: joined IDs are found too


class _Invisible:
    """Characters that draw as nothing and so hide a word: every Unicode format character (category Cf: zero-width, direction marks and
    isolates, invisible separators such as U+2063, tags, the soft hyphen), the combining grapheme joiner U+034F, the variation
    selectors and Mongolian free variation selectors. `.sub(repl, text)` works like a compiled pattern's."""
    EXTRA = {0x17B4, 0x17B5, 0x2800, 0x034F, 0x180B, 0x180C, 0x180D, 0x180E, 0x115F, 0x1160, 0x3164, 0xFFA0}

    def hides(self, c):
        """Whether the character draws as nothing."""
        o = ord(c)
        return unicodedata.category(c) == "Cf" or o in self.EXTRA or 0xFE00 <= o <= 0xFE0F or 0xE0100 <= o <= 0xE01EF

    def sub(self, repl, text):
        """The text with each invisible character replaced by `repl` (a pattern's `sub`)."""
        return "".join(repl if self.hides(c) else c for c in str(text or ""))


INVISIBLE = _Invisible()
SVG_URI = re.compile(r"data:image/svg\+xml(?:;charset=[\w-]+)?;base64,([A-Za-z0-9+/=\s]+)", re.I)
SVG_MAX = 1_000_000
SVG_ADDR = re.compile(r"data:image/svg\+xml", re.I)
CSS_CONTENT = re.compile(r"content\s*:\s*([^;}]*)", re.I)
ID_OK = re.compile(r"^[A-Za-z][\w:.-]{0,60}$")
DATA_ATTR = re.compile(r"^data-[a-z0-9_.:-]{1,40}$")
SVG_ATTR = re.compile(r"^[a-z][a-z0-9:-]{0,30}$")
SIZE = re.compile(r"^[\d.]+(px|%|em|mm)?$")
DATA_IMAGE = re.compile(r"^data:image/(?:png|jpe?g|gif|webp|svg\+xml)(?:;charset=[\w-]+)?;base64,[A-Za-z0-9+/=\s]+$", re.I)
BAD_STYLE = re.compile(r"expression\s*\(|javascript:|vbscript:|@import|(?<![-\w])behaviou?r\s*:|-moz-binding|</|<!--", re.I)
URL_IN_CSS = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.I | re.S)
NO_FUNCTIONS = re.compile(r"image-set\(|cross-fade\(|(?:-webkit-)?image\(")
CSP = "default-src 'none'; img-src data:; style-src 'unsafe-inline'"
PALETTE = re.compile(r"^[A-Za-z0-9 _-]{1,40}$")
META_KEYS = ("id", "type", "heading", "default_heading", "hidden", "shown", "ref", "key", "source")
ITEM_WORDS = ("title", "description", "decision", "name", "response_action", "owner", "made_by")


class PageRefused(ValueError):
    """The posted page isn't used; the message says why (a reason, never a word of the report)."""


# ── The allow-list ────────────────────────────────────────────────────────────

def safe_css_value(v, client=False):
    """Whether a style value or a whole stylesheet is free of imports, scripts and any address that isn't a data address of a picture
    or a fragment of the file itself. A CLIENT file takes no SVG picture in its styles at all; an internal file takes one only if its
    words can be read (css_svg_words), and those are then checked like the page's own."""
    decoded = css_decode(v)
    squashed = re.sub(r"\s+", "", decoded).lower()
    if BAD_STYLE.search(v) or BAD_STYLE.search(decoded):
        return False
    if NO_FUNCTIONS.search(squashed) or re.search(r"(?<![\w-])src\(", decoded, re.I):
        return False     # a picture or address in a string the url() checks never see (image-set, cross-fade, src())
    for text in (v, decoded):       # as written and as the browser reads it (u\72l( is url()
        for m in URL_IN_CSS.finditer(text):
            a = m.group(2).strip()
            if not (a.startswith("#") or DATA_IMAGE.match(a) or SVG_ADDR.match(a)):
                return False
    if client and not metadata_free(v):
        return False
    if SVG_ADDR.search(decoded) or SVG_ADDR.search(v) or SVG_ADDR.search(squashed):
        return not client and css_svg_words(v) is not None
    return True


def svg_payload(addr):
    """The SVG text of a `data:image/svg+xml…` address written base64 or percent-encoded (or as plain text), or None when a base64 one
    can't be read."""
    head, _, body = addr.partition(",")
    if ";base64" in head.lower():
        try:
            return base64.b64decode(re.sub(r"\s+", "", unquote(body)), validate=True).decode("utf-8", "replace")
        except ValueError:
            return None
    return unquote(body)


def css_svg_words(css):
    """The words of every `data:image/svg+xml` picture in style rules (read as the browser reads them: escapes decoded), or None
    when one can't be read or is too large. Over-inclusive on purpose: the percent-decoded rest of the rule is read as words too,
    so a match is only ever likelier."""
    text, words = css_decode(css), []
    for m in SVG_ADDR.finditer(text):
        rest = text[m.start():]
        end = re.search(r"['\")]", rest[len("data:image/svg+xml"):])
        addr = rest[:len("data:image/svg+xml") + (end.start() if end else len(rest))]
        head, _, body = addr.partition(",")
        if len(addr) > SVG_MAX:
            return None
        if ";base64" in head.lower():
            payload = svg_payload(addr)
            if payload is None:
                return None
        else:
            payload = unquote(body)
            words.append(unquote(rest.partition(",")[2]))       # an unquoted address cut short by a ")" in it: the rest too
        payload = html.unescape(payload)
        if len(unquote(payload)) > SVG_MAX:
            return None
        words += [payload, re.sub(r"<[^>]*>", "", payload), unquote(payload)]
        if SVG_ADDR.search(payload) or re.search(r"data\s*:", payload, re.I):
            return None     # a picture inside a picture
    return words


def client_attr_ok(svg, name, value):
    """Whether a CLIENT file may keep this attribute: only the short allow-list, and never a value that holds an item ID."""
    if ITEM_ID.search(value) or not (name in CLIENT_ATTRS or (svg and name in CLIENT_SVG_ATTRS)):
        return False
    return name != "data-id" or bool(ID_OK.match(value))


def svg_words(value, depth=0):
    """The words of a `data:image/svg+xml;base64,…` picture (its text, title, desc and every attribute), or None when it can't be
    read or holds another data address (a picture inside a picture, however it is written): such a picture is not kept. Read like
    the page's own words by the leak checks."""
    m = SVG_URI.fullmatch(value.strip())
    if m is None:
        return None
    try:
        raw = base64.b64decode(re.sub(r"\s+", "", m.group(1)), validate=True)
    except ValueError:
        return None
    if len(raw) > SVG_MAX:
        return None
    text = html.unescape(raw.decode("utf-8", "replace"))
    for form in (text, unquote(text), html.unescape(unquote(text))):
        if re.search(r"data\s*(?::|%3a)", form, re.I):
            return None
    return [text, re.sub(r"<[^>]*>", "", text), unquote(text), re.sub(r"<[^>]*>", "", unquote(text))]


RASTER_ADDR = re.compile(r"^data:image/(?:png|jpe?g)((?:;[\w=-]+)*);base64,([A-Za-z0-9+/=\s]+)$", re.I)


def clean_picture(value):
    """A PNG or JPEG data address with the picture's own metadata (text chunks, EXIF, comments) removed; anything else as it was."""
    import docx_tools
    m = RASTER_ADDR.match(value.strip())
    if m is None:
        return value
    try:
        raw = base64.b64decode(re.sub(r"\s+", "", m.group(2)), validate=True)
    except ValueError:
        return value
    head = value.strip()[:value.strip().index(";base64,")]
    return head + ";base64," + base64.b64encode(docx_tools.strip_image_metadata(raw)).decode("ascii")


def metadata_free(css):
    """Whether every PNG or JPEG address in style rules is already without metadata (a client file takes no other)."""
    for m in URL_IN_CSS.finditer(css):
        a = m.group(2).strip()
        if RASTER_ADDR.match(a) and clean_picture(a) != a:
            return False
    return True


def src_ok(tag, value):
    """Whether an img's src is kept: a data address of a picture, and an SVG one only if it can be read (see svg_words)."""
    return tag == "img" and bool(DATA_IMAGE.match(value)) and (not SVG_URI.match(value) or svg_words(value) is not None)


def keep_attr(tag, svg, name, value, client=False):
    """Whether the attribute `name`="`value`" of an element `tag` (inside an svg when `svg`) is written. In a client file only the
    short allow-list survives, and never a value that holds an item ID."""
    if name.startswith("on") or name in NEVER_ATTRS or (client and not client_attr_ok(svg, name, value)):
        return False
    if name == "style":
        return safe_css_value(value, client)
    if name == "src":
        return src_ok(tag, value)
    if name == "id":
        return bool(ID_OK.match(value))
    if name.startswith("data-"):
        return bool(DATA_ATTR.match(name))
    if name in GLOBAL_ATTRS:
        return not (name in ("width", "height") and not SIZE.match(value))
    return svg and bool(SVG_ATTR.match(name)) and safe_css_value(value) and "javascript:" not in value.lower()


class Clean(HTMLParser):
    """Rebuild markup from an allow-list. `out` is the clean HTML; `text` the words of it; `sections` the data-id of every
    section; `rows` {section id: body rows}. Nothing outside the lists is written."""

    def __init__(self, client=False):
        super().__init__(convert_charrefs=True)
        self.client = client
        self.attr_values = []   # every attribute value that is written (checked like the text)
        self.out, self.text, self.sections, self.rows = [], [], [], {}
        self.skip = 0           # depth inside a dropped element
        self.svg = 0            # depth inside an svg
        self.stack = []         # (tag, written?)
        self.cur = None         # the section being read
        self.body = 0           # depth inside a tbody

    def attrs_of(self, tag, attrs):
        """The attributes to keep, as a string."""
        svg = self.svg > 0 or tag == "svg"
        keep = []
        for name, value in attrs:
            name, value = name.lower(), "" if value is None else value
            if keep_attr(tag, svg, name, value, self.client):
                value = clean_picture(value) if name == "src" else value
                keep.append((name, value[:300] if name.startswith("data-") else value[:2000]))
                if name != "src":
                    self.attr_values.append(keep[-1][1])
                    if name == "style":
                        self.attr_values.extend(css_svg_words(value) or [])
                elif SVG_URI.match(value):
                    self.attr_values.extend(svg_words(value) or [])      # an SVG picture is read like the page: its words and attributes
        return "".join(f' {n}="{html.escape(v, quote=True)}"' for n, v in keep)

    def note_structure(self, tag, attrs):
        """Count a section and the body rows of a table in it."""
        if tag == "section":
            sid = dict((n.lower(), v) for n, v in attrs).get("data-id")
            if sid:
                self.cur = sid
                self.sections.append(sid)
                self.rows.setdefault(sid, 0)
        elif tag == "tbody":
            self.body += 1
        elif tag == "tr" and self.body and self.cur:
            self.rows[self.cur] += 1

    def handle_starttag(self, tag, attrs):
        """Write an allowed element; a dropped one is skipped with what is inside it."""
        tag = tag.lower()
        if self.skip:
            self.skip += tag not in VOID
            return
        if tag in DROP_WITH_CONTENT:
            self.skip = int(tag not in VOID)
            return
        in_svg = self.svg > 0 or tag == "svg"
        if tag == "svg":
            self.svg += 1
        if tag not in (SVG_TAGS if in_svg else TAGS):
            self.stack.append((tag, False))
            return
        self.note_structure(tag, attrs)
        self.out.append(f"<{tag}{self.attrs_of(tag, attrs)}>")
        if tag in VOID:
            self.svg -= tag == "svg"
        else:
            self.stack.append((tag, True))

    def handle_startendtag(self, tag, attrs):
        """A self-closing tag is a start and an end."""
        self.handle_starttag(tag, attrs)
        if tag.lower() not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        """Close the element (and anything left open inside it)."""
        tag = tag.lower()
        if self.skip:
            self.skip -= tag not in VOID
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                for t, written in reversed(self.stack[i:]):
                    self.close_one(t, written)
                del self.stack[i:]
                return

    def close_one(self, tag, written):
        """Write one closing tag and keep the depth counters."""
        if written:
            self.out.append(f"</{tag}>")
        if tag == "tbody":
            self.body = max(0, self.body - 1)
        if tag == "svg":
            self.svg = max(0, self.svg - 1)

    def handle_data(self, data):
        """Text is escaped and kept."""
        if not self.skip:
            self.out.append(html.escape(data, quote=False))
            self.text.append(data)

    def close(self):
        """End of input: close what is still open."""
        super().close()
        for t, written in reversed(self.stack):
            self.close_one(t, written)
        self.stack = []


def clean_markup(markup, client=False, attr_values=None):
    """(clean HTML, its text, section ids, {section id: body rows}) for posted markup. `client`: the short attribute allow-list;
    `attr_values`, a list, receives every attribute value written."""
    if not isinstance(markup, str) or not markup.strip():
        raise PageRefused("the page was empty")
    if len(markup) > MAX_HTML:
        raise PageRefused("the page was too large")
    p = Clean(client)
    p.feed(markup)
    p.close()
    if attr_values is not None:
        attr_values.extend(p.attr_values)
    return "".join(p.out), squash(" ".join(p.text)), p.sections, p.rows


def clean_css(css, client=False):
    """The posted style rules, or raises PageRefused."""
    if not isinstance(css, str) or not css.strip() or len(css) > MAX_CSS:
        raise PageRefused("the style rules were missing or too large")
    if not safe_css_value(css, client):
        raise PageRefused("the style rules held an address or a command")
    return css


# ── Checking the page against the report ──────────────────────────────────────

def squash(t):
    """Text with its whitespace squeezed to single spaces."""
    return re.sub(r"\s+", " ", str(t or "")).strip()


def plain_words(md):
    """The lines of a Markdown text as plain words (marks and link addresses dropped)."""
    out = []
    for line in str(md or "").splitlines():
        line = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", line)
        line = re.sub(r"[*_`~#>]+", "", line)
        line = squash(re.sub(r"^\s*[-+]\s+", "", line))
        if line:
            out.append(line)
    return out


def strings(x, skip=()):
    """Every string inside a value, except under the keys in `skip`."""
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for k, v in x.items():
            if k not in skip:
                yield from strings(v, skip)
    elif isinstance(x, (list, tuple)):
        for v in x:
            yield from strings(v, skip)


def item_lookup(ref):
    """The tracker's row for an item reference, with a title (report_doc.item), or None. The one place the check reads the tracker;
    a test replaces it."""
    import report_doc
    import tracker
    with tracker.connect() as con:
        return report_doc.item(con, ref)


def document_candidates(doc):
    """Strings of what the report leaves out that the document still holds: hidden sections', hidden rows' and hidden figures'."""
    cand = []
    for s in doc.get("sections") or []:
        if s.get("hidden"):
            cand += list(strings(s, META_KEYS))
        for r in s.get("rows") or []:
            if s.get("hidden") or not r.get("shown", True):
                cand += list(strings(r.get("cells") or {}))
        for f in s.get("figures") or []:
            if s.get("hidden") or not f.get("shown", True):
                cand += [f.get("label"), f.get("value"), f.get("note")]
    return cand


def tracker_candidates(doc):
    """The words of every item a hidden row names, from the document's items and the tracker (a saved report keeps only the reference)."""
    cand = []
    shown_items = creaite_doc.clean(doc).get("items") or {}
    for ref in creaite_doc._hidden_refs(doc.get("sections") or []):
        it = (doc.get("items") or {}).get(ref)
        if it and ref not in shown_items:
            cand += list(strings(it, ("id", "table", "project")))
        try:
            row = item_lookup(ref)
        except Exception as e:        # fails closed: the page can't be compared with the tracker
            raise PageRefused("the tracker couldn't be read to check the page") from e
        cand += [row.get(k) for k in ITEM_WORDS if row and isinstance(row.get(k), str)]
    return cand


def hidden_candidates(doc):
    """Strings that belong to what the report leaves out."""
    return document_candidates(doc) + tracker_candidates(doc)


def hidden_needles(doc):
    """The words that must not be in a page, leaving out any that the shown part of the report holds too."""
    shown = creaite_doc.clean(doc)
    meta = {k: shown.get(k) for k in ("title", "project_name", "client")}
    shown_text = squash(json.dumps([s for s in shown["sections"] if not s.get("hidden")], ensure_ascii=False)
                        + " " + " ".join(strings(meta)))
    plain_shown = squash(" ".join(plain_words(shown_text)))
    needles = set()
    for c in hidden_candidates(doc):
        for line in plain_words(c) if isinstance(c, str) else []:
            if len(line) >= MIN_NEEDLE and line not in shown_text and line not in plain_shown:
                needles.add(line)
    return needles


def check_sections(doc, sections, rows):
    """Raises PageRefused for a section the report leaves out, or a table with more body rows than the report shows."""
    shown = creaite_doc.clean(doc)
    ok_ids = {s["id"] for s in shown["sections"] if not s.get("hidden")}
    if any(sid not in ok_ids for sid in sections):
        raise PageRefused("the page held a section the report leaves out")
    for s in shown["sections"]:
        n = sum(1 for r in s.get("rows") or [] if r.get("shown", True))
        if s.get("type") == "table" and not s.get("hidden") and rows.get(s["id"], 0) > n:
            raise PageRefused("a table had more rows than the report shows")


def fold(t):
    """Text for comparing words: Unicode-normalised, lower case, with no whitespace (inline marks split words in the markup)."""
    return re.sub(r"\s+", "", INVISIBLE.sub("", unicodedata.normalize("NFKC", str(t or ""))).casefold())


def is_client(doc):
    """True for a client report."""
    return doc.get("kind") == "client" or doc.get("audience") == "client"


def css_decode(css):
    """Style rules read as the browser reads them: comments gone, escapes decoded (\\0057 and \\57 are W) and quote marks dropped, so
    "Wal" "rus" and "\\0057alrus" read as the word they draw. An escape followed by more hex letters ("\\0057alrus") is read by the
    standard as one long number; a hand-written one may mean four or two digits, so those readings are added too (extra words can
    only make a match likelier, never hide one)."""
    t = re.sub(r"/\*.*?\*/", "", str(css or ""), flags=re.S)
    out = []
    for digits in ("1,6", "4", "2"):
        d = re.sub(r"\\([0-9a-fA-F]{%s})\s?" % digits, lambda m: chr(int(m.group(1), 16)) if 0 < int(m.group(1), 16) <= 0x10FFFF else "", t)
        out.append(re.sub(r"\\(.)", r"\1", d, flags=re.S).replace('"', "").replace("'", ""))
    return "\n".join(out)


def css_strings(css):
    """The words a stylesheet can draw with `content:` (read as the browser reads them)."""
    return " ".join(m.group(1) for m in CSS_CONTENT.finditer(css_decode(css)))


def check_page(doc, page, text, sections, rows, attrs=(), css=""):
    """Raises PageRefused when the page isn't the saved report as the report may be exported. `attrs` are the attribute values the
    file keeps and `css` its style rules: they are read like the text (LEAK 1); the version is required (LEAK 5); words are
    matched without case or accents-as-written (LEAK 6)."""
    try:
        sent = int(page.get("version"))
    except (TypeError, ValueError):
        raise PageRefused("the page didn't say which version of the report it was drawn from") from None
    if sent != int(doc.get("version") or 0):
        raise PageRefused("the page was drawn from a different version than the saved report")
    check_sections(doc, sections, rows)
    bare = fold(" ".join([text] + list(attrs) + [css_decode(a) for a in attrs]) + " " + str(css or "") + " " + css_decode(css)
                + " " + " ".join(css_svg_words(css) or []))
    if any(fold(n) in bare for n in hidden_needles(doc)):
        raise PageRefused("the page held words the report leaves out")
    if is_client(doc):
        import client_leak
        everything = INVISIBLE.sub("", "\n".join([text] + list(attrs) + [css_decode(a) for a in attrs] + [css_strings(css)]))
        with client_leak.connect() as con:
            if client_leak.plain_findings(con, doc.get("project"), everything):
                raise PageRefused("the page held content a client report must not show")


# ── The file ──────────────────────────────────────────────────────────────────

PRINT_CSS = """
/* the file's own frame: light, A4, one card on a grey ground; the dashboard's rules above draw the report itself */
html{background:#e9eaee;color-scheme:light}
body{margin:0;padding:24px 0;background:#e9eaee;color:#1d2433;-webkit-print-color-adjust:exact;print-color-adjust:exact}
.export-view{display:block!important;overflow:visible!important;padding:0!important;margin:0 auto!important;background:none!important;
  height:auto!important;min-height:0!important;max-width:none!important;width:210mm}
.export-view .wrview,.export-view .crview,.export-view .wrsheet,.export-view .crsheet,.export-view .sheet-root,.export-view .sheet-area,
.export-view .sheet-scroll,.export-view .sheet-one,.export-view .sheet-fit{display:block!important;position:static!important;
  width:auto!important;height:auto!important;min-height:0!important;overflow:visible!important;padding:0!important;margin:0!important;
  background:none!important;flex:none!important;transform:none!important}
.export-view .sheet-a4{position:static!important;transform:none!important;width:210mm!important}
.export-view .page{margin:0 auto!important;box-shadow:0 1px 4px rgba(0,0,0,.15)}
section{break-inside:avoid-page;break-inside:avoid}
.wr-tlwrap{resize:none!important}
tr,.wr-stat,.wr-health{break-inside:avoid}
@media print{
  html,body{background:#fff!important;padding:0!important}
  .export-view{width:auto!important}
  .export-view .sheet-a4{width:auto!important}
  .export-view .page{box-shadow:none!important;width:auto!important;min-height:0!important;padding:0!important;margin:0!important;
    background:#fff!important}
  .wr-tlwrap{overflow:visible!important;height:auto!important;max-height:none!important}
  .wr-tl{width:100%!important;height:auto!important}
}
@page{size:A4;margin:16mm}
"""


def build(doc, page, title):
    """The finished HTML file for the report `doc` (the saved draft or filed report, as creaite_doc.read gives it) drawn as `page`.
    Raises PageRefused."""
    if not isinstance(page, dict):
        raise PageRefused("no page was sent")
    attrs = []
    markup, text, sections, rows = clean_markup(page.get("html"), is_client(doc), attrs)
    css = clean_css(page.get("css"), is_client(doc))
    check_page(doc, page, text, sections, rows, attrs, css)
    palette = str(page.get("palette") or "")
    attr = f' data-palette="{html.escape(palette, quote=True)}"' if PALETTE.match(palette) else ""
    return (f'<!doctype html>\n<html lang="en-GB" data-theme="light"{attr}><head><meta charset="utf-8">'
            f'<meta http-equiv="Content-Security-Policy" content="{CSP}">'
            f'<meta name="viewport" content="width=device-width"><meta name="generator" content="creaite export page">'
            f"<title>{creaite_doc.esc(title)}</title><style>{css}</style><style>{PRINT_CSS}</style></head>\n"
            f"<body>{markup}</body></html>\n")
