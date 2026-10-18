"""#226: the HTML and PDF export of a weekly or client report is the report page's own "Show as exported" view.

The dashboard draws the report in its exported mode, cleans nothing itself and posts the result with `/api/report/export` as
`page: {html, css, palette, version}`: `html` the page's markup, `css` the style rules that apply to it (the dashboard's own stylesheet,
filtered to what the page uses), `palette` the dashboard's palette name (so the file's colours are the theme's light ones) and `version`
the saved draft it was drawn from. A library: no command line. This module never trusts that post.

  - `build(doc, page)`: the file's text, or raises PageRefused. The markup is rebuilt through an allow-list (no script, event handler,
    form control, frame or external address; a picture is a data address only), the style rules are checked (no import, no address
    that isn't a data address), and the page is then checked against the server's own copy of the report: it was drawn from the
    version saved, every section in it is a shown section of `creaite_doc.clean(doc)`, no table has more rows than the report shows,
    and none of the words of the items the report's hidden rows name (read from the tracker: a saved report keeps only their
    references) or of hidden figures appear in it. A hidden section is kept out by its place (its id may not be in the page): a saved
    report keeps nothing of it, so its words can't be compared.
    A client report's words are also run through client_leak.plain_findings, the check export and approve already use.
  - The file is fixed to the light theme and A4, with its colours kept in print; Chrome prints that same file for the PDF.

creaite_doc.render stays the fallback for the command line, for minutes and for any export with no page or a page that fails here;
the route then says it made the plain version (`plain: true`)."""
import html
import json
import re
import sys
from html.parser import HTMLParser
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
GLOBAL_ATTRS = {"class", "id", "role", "title", "lang", "dir", "style", "colspan", "rowspan", "scope", "span", "headers", "datetime",
                "width", "height", "alt", "src", "aria-label", "aria-hidden", "aria-describedby", "aria-live", "tabindex"}
ID_OK = re.compile(r"^[A-Za-z][\w:.-]{0,60}$")
DATA_IMAGE = re.compile(r"^data:image/(?:png|jpe?g|gif|webp|svg\+xml)(?:;charset=[\w-]+)?;base64,[A-Za-z0-9+/=\s]+$", re.I)
BAD_STYLE = re.compile(r"expression\s*\(|javascript:|vbscript:|@import|(?<![-\w])behaviou?r\s*:|-moz-binding|</|<!--", re.I)
URL_IN_CSS = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.I | re.S)
PALETTE = re.compile(r"^[A-Za-z0-9 _-]{1,40}$")
TEXT_TAGS = {"p", "li", "td", "th", "div", "span", "h1", "h2", "h3", "h4", "section", "header", "figcaption", "blockquote", "dd", "dt"}


class PageRefused(ValueError):
    """The posted page isn't used; the message says why (a reason, never a word of the report)."""


# ── The allow-list ────────────────────────────────────────────────────────────

def safe_css_value(v):
    """Whether a style value or a whole stylesheet is free of imports, scripts and any address that isn't a data address or a
    fragment of the file itself."""
    if BAD_STYLE.search(v):
        return False
    for m in URL_IN_CSS.finditer(v):
        a = m.group(2).strip()
        if not (a.startswith("#") or a.lower().startswith("data:image/")):
            return False
    return True


class Clean(HTMLParser):
    """Rebuild markup from an allow-list. `out` is the clean HTML; `text` the words of it; `sections` the data-id of every
    section; `rows` {section id: body rows}. Nothing outside the lists is written."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.text, self.sections, self.rows = [], [], [], {}
        self.skip = 0           # depth inside a dropped element
        self.svg = 0
        self.stack = []         # (tag, written?)
        self.cur = None         # the section being read
        self.body = 0           # inside a tbody

    def attrs_ok(self, tag, attrs):
        """The attributes to keep, as a string."""
        keep = []
        svg = self.svg > 0 or tag == "svg"
        for name, value in attrs:
            name = name.lower()
            value = "" if value is None else value
            if name.startswith("on") or name in ("href", "xlink:href", "srcset", "action", "formaction", "srcdoc", "ping", "poster", "background"):
                continue
            if name == "style":
                if safe_css_value(value):
                    keep.append((name, value))
                continue
            if name == "src":
                if tag == "img" and DATA_IMAGE.match(value):
                    keep.append((name, value))
                continue
            if name == "id":
                if ID_OK.match(value):
                    keep.append((name, value))
                continue
            if name.startswith("data-") and re.match(r"^data-[a-z0-9_.:-]{1,40}$", name):
                keep.append((name, value[:300]))
                continue
            if name in GLOBAL_ATTRS and not (name in ("width", "height") and not re.match(r"^[\d.]+(px|%|em|mm)?$", value)):
                keep.append((name, value[:2000]))
            elif svg and re.match(r"^[a-z][a-z0-9:-]{0,30}$", name) and safe_css_value(value) and "javascript:" not in value.lower():
                keep.append((name, value[:2000]))
        return "".join(f' {n}="{html.escape(v, quote=True)}"' for n, v in keep)

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if self.skip:
            if tag not in VOID:
                self.skip += 1
            return
        if tag in DROP_WITH_CONTENT:
            if tag not in VOID:
                self.skip = 1
            return
        in_svg = self.svg > 0 or tag == "svg"
        allowed = tag in SVG_TAGS if in_svg else tag in TAGS
        if tag == "svg":
            self.svg += 1
        if not allowed:
            self.stack.append((tag, False))
            return
        a = self.attrs_ok(tag, attrs)
        d = dict((n.lower(), v) for n, v in attrs)
        if tag == "section" and d.get("data-id"):
            self.cur = d["data-id"]
            self.sections.append(self.cur)
            self.rows.setdefault(self.cur, 0)
        if tag == "tbody":
            self.body += 1
        if tag == "tr" and self.body and self.cur:
            self.rows[self.cur] += 1
        self.out.append(f"<{tag}{a}>")
        self.stack.append((tag, True))
        if tag in VOID:
            self.stack.pop()
            if tag == "svg":
                self.svg -= 1

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag.lower() not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self.skip:
            if tag not in VOID:
                self.skip -= 1
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                for t, written in reversed(self.stack[i:]):
                    if written:
                        self.out.append(f"</{t}>")
                    if t == "tbody":
                        self.body = max(0, self.body - 1)
                    if t == "svg":
                        self.svg = max(0, self.svg - 1)
                del self.stack[i:]
                return

    def handle_data(self, data):
        if self.skip:
            return
        self.out.append(html.escape(data, quote=False))
        self.text.append(data)

    def close(self):
        super().close()
        for t, written in reversed(self.stack):
            if written:
                self.out.append(f"</{t}>")
        self.stack = []


def clean_markup(markup):
    """(clean HTML, its text, section ids, {section id: body rows}) for posted markup."""
    if not isinstance(markup, str) or not markup.strip():
        raise PageRefused("the page was empty")
    if len(markup) > MAX_HTML:
        raise PageRefused("the page was too large")
    p = Clean()
    p.feed(markup)
    p.close()
    return "".join(p.out), squash(" ".join(p.text)), p.sections, p.rows


def clean_css(css):
    """The posted style rules, or raises PageRefused."""
    if not isinstance(css, str) or not css.strip() or len(css) > MAX_CSS:
        raise PageRefused("the style rules were missing or too large")
    if not safe_css_value(css):
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
        line = re.sub(r"^\s*[-+]\s+", "", line)
        line = squash(line)
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


META_KEYS = ("id", "type", "heading", "default_heading", "hidden", "shown", "ref", "key", "source")
ITEM_WORDS = ("title", "description", "decision", "name", "response_action", "owner", "made_by")


def item_lookup(ref):
    """The tracker's row for an item reference, with a title (report_doc.item), or None. The one place the check reads the tracker;
    a test replaces it."""
    import report_doc
    import tracker
    with tracker.connect() as con:
        return report_doc.item(con, ref)


def hidden_needles(doc):
    """The words that must not be in a page: those of hidden sections, hidden rows, hidden figures and the items only they name,
    leaving out any that the shown part of the report holds too."""
    shown = creaite_doc.clean(doc)
    shown_text = squash(json.dumps([s for s in shown["sections"] if not s.get("hidden")], ensure_ascii=False)
                        + " " + " ".join(strings({k: shown.get(k) for k in ("title", "project_name", "client")})))
    plain_shown = squash(" ".join(plain_words(shown_text)))
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
    # A saved report keeps only the references of what was left out (creaite_doc.save cleans it), so their words come from the tracker.
    for ref in creaite_doc._hidden_refs(doc.get("sections") or []):
        it = (doc.get("items") or {}).get(ref)
        if it and ref not in (shown.get("items") or {}):
            cand += list(strings(it, ("id", "table", "project")))
        try:
            row = item_lookup(ref)
        except Exception as e:        # fails closed: the page can't be compared with the tracker
            raise PageRefused("the tracker couldn't be read to check the page") from e
        cand += [row.get(k) for k in ITEM_WORDS if row and isinstance(row.get(k), str)]
    needles = set()
    for c in cand:
        for line in plain_words(c) if isinstance(c, str) else []:
            if len(line) >= MIN_NEEDLE and line not in shown_text and line not in plain_shown:
                needles.add(line)
    return needles


def check_page(doc, page, markup, text, sections, rows):
    """Raises PageRefused when the page isn't the saved report as the report may be exported."""
    saved = doc.get("version")
    if page.get("version") is not None and int(page.get("version") or 0) != int(saved or 0):
        raise PageRefused("the page was drawn from a different version than the saved report")
    shown = creaite_doc.clean(doc)
    ok_ids = {s["id"] for s in shown["sections"] if not s.get("hidden")}
    for sid in sections:
        if sid not in ok_ids:
            raise PageRefused("the page held a section the report leaves out")
    for s in shown["sections"]:
        if s.get("type") == "table" and not s.get("hidden") and rows.get(s["id"], 0) > sum(1 for r in s.get("rows") or [] if r.get("shown", True)):
            raise PageRefused("a table had more rows than the report shows")
    bare = re.sub(r"\s+", "", text)           # inline marks split words in the markup, so compare without any space
    for n in hidden_needles(doc):
        if re.sub(r"\s+", "", n) in bare:
            raise PageRefused("the page held words the report leaves out")
    if doc.get("kind") == "client" or doc.get("audience") == "client":
        import client_leak
        with client_leak.connect() as con:
            found = client_leak.plain_findings(con, doc.get("project"), text)
        if found:
            raise PageRefused("the page held content a client report must not show")


# ── The file ──────────────────────────────────────────────────────────────────

PRINT_CSS = """
/* the file's own frame: light, A4, one card on a grey ground; the dashboard's rules above draw the report itself */
html{background:#e9eaee;color-scheme:light}
body{margin:0;padding:24px 0;background:#e9eaee;color:#1d2433;-webkit-print-color-adjust:exact;print-color-adjust:exact}
.export-view{display:block!important;overflow:visible!important;padding:0!important;margin:0 auto!important;background:none!important;
  height:auto!important;min-height:0!important;max-width:none!important;width:210mm}
.export-view .wrview,.export-view .crview,.export-view .wrsheet,.export-view .crsheet,.export-view .sheet-root,.export-view .sheet-area,
.export-view .sheet-scroll,.export-view .sheet-one,.export-view .sheet-fit{display:block!important;position:static!important;width:auto!important;
  height:auto!important;min-height:0!important;overflow:visible!important;padding:0!important;margin:0!important;background:none!important;
  flex:none!important;transform:none!important}
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
    markup, text, sections, rows = clean_markup(page.get("html"))
    css = clean_css(page.get("css"))
    check_page(doc, page, markup, text, sections, rows)
    palette = str(page.get("palette") or "")
    attr = f' data-palette="{html.escape(palette, quote=True)}"' if PALETTE.match(palette) else ""
    return (f'<!doctype html>\n<html lang="en-GB" data-theme="light"{attr}><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width"><meta name="generator" content="creaite export page">'
            f"<title>{creaite_doc.esc(title)}</title><style>{css}</style><style>{PRINT_CSS}</style></head>\n"
            f"<body>{markup}</body></html>\n")
