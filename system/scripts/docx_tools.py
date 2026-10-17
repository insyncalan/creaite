"""creaite Word tools — fill templates, read documents, clean them before filing (standard library only).

Commands:
  fill <template.docx> <values.json> <out.docx>
        Fill {{PLACEHOLDERS}}. In values.json:
          "NAME": "text"                 replaces the placeholder
          "NAME": ["one", "two"]         repeats the placeholder's paragraph once per entry
                                         (an empty list writes "None recorded.")
                                         an entry may be {"flag": "PRIORITY", "text": "…"} to add a coloured label
          "NAME": [{"md": "Markdown text"}]
                                         Markdown (BL-22): paragraphs, **bold**, *italic*, "- " bullets and
                                         "1. " numbered items, each as its own paragraph
          "NAME": [{"image": "projects/…/images/x.png", "caption": "…"}]
                                         images (PNG or JPEG, scaled to the page width), each with an optional caption;
                                         image and Markdown entries can be mixed in one list, in order (BL-63)
          "NAME": [{"heading": "…", "items": [...]}]
                                         topic groups: repeats the {{NAME_HEADING}} paragraph and, under each
                                         heading, the {{NAME_ITEM}} paragraph once per item (items as above)
          "NAME": [{"A_N": "1", ...}]    repeats the table row holding {{A_N}} once per dict
                                         (the list's key is a label; the dict keys are the placeholders)
        Fails, writing nothing, if any placeholder is left unfilled.
  text <file.docx>     print the document as plain text, with tracked changes accepted (one line per paragraph;
                       table cells joined by " | ")
  build-adhoc <adhoc-template.docx> <spec.json> <out.docx>
        Build a one-off branded document (BL-75), such as a register or a list, from the template's exemplar blocks.
        spec.json: {"title", "subtitle", "status", "when", "source", "landscape": false, "sections": [
          {"heading": "…", "paragraphs": ["…"], "bullets": ["…"],
           "table": {"columns": ["Header" | {"header": "…", "width": 20}], "rows": [["cell", …]]}} ]}
        Any part may be left out; a cell may hold several lines ("\n"). Columns share the width by their weight (or
        by how long their text is). Fails, writing nothing, if a row has the wrong number of cells.
  clean <in.docx> [out.docx]
                       accept all tracked changes and remove all comments (in place if no out); prints counts

fill, build-adhoc and clean write only inside system/staging/drafts/ (BL-271); a project's file changes through
filechange.py, from a new version built there.
  status <file.docx>   print counts of tracked changes and comments, and whether Word has it open
"""
import json
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402,F401  (locations and bundled libraries, as every script does)
import linktext  # noqa: E402  (#121: links in plain text)

PARA = re.compile(r"<w:p(?: [^>]*)?>.*?</w:p>|<w:p(?: [^>]*)?/>", re.S)
ROW = re.compile(r"<w:tr(?: [^>]*)?>.*?</w:tr>", re.S)
TEXT = re.compile(r"(<w:t(?: [^>]*)?>)([^<]*)(</w:t>)")
STORY = re.compile(r"word/(document|header\d*|footer\d*|footnotes|endnotes)\.xml$")
COMMENT_PARTS = re.compile(r"word/comments(Extended|Ids|Extensible)?\.xml$")
CHANGE_TAGS = ("w:ins", "w:del", "w:moveFrom", "w:moveTo", "w:rPrChange", "w:pPrChange", "w:tblPrChange",
               "w:trPrChange", "w:tcPrChange", "w:sectPrChange", "w:tblGridChange", "w:numberingChange")
NONE = "None recorded."
# Status labels: the minutes-adhoc palette (white bold text on a coloured badge)
FLAGS = {
    "BLOCKED": "C0392B", "HIGH RISK": "C0392B",
    "PRIORITY": "D68910", "FLAG": "D68910", "SUPPORT NEEDED": "D68910",
    "ACTION": "2C6FAA", "NEW SCOPE": "2C6FAA", "NEW": "2C6FAA",
    "ON TRACK": "2E7D32", "DONE": "2E7D32",
    "AT RISK": "D68910", "OFF TRACK": "C0392B",          # report health lines
}


def pill(flag):
    """A coloured label (PRIORITY, ACTION, ON TRACK and the rest of FLAGS) as Word runs; an unknown label raises ValueError."""
    if flag not in FLAGS:
        raise ValueError(f"unknown label {flag!r}; use one of: {', '.join(FLAGS)}")
    return ('<w:r><w:rPr><w:rFonts w:ascii="Arial" w:eastAsia="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:b/><w:bCs/>'
            f'<w:color w:val="FFFFFF"/><w:sz w:val="16"/><w:szCs w:val="16"/><w:shd w:val="clear" w:color="auto" '
            f'w:fill="{FLAGS[flag]}"/></w:rPr><w:t xml:space="preserve"> {esc(flag)} </w:t></w:r>'
            '<w:r><w:t xml:space="preserve">  </w:t></w:r>')


IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
MAX_WIDTH_EMU = 5486400                       # 6 inches: the text width of an A4 page with the template's margins


def image_size(data):
    """(width, height) in pixels of a PNG or JPEG."""
    import struct
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", data[16:24])
    i = 2
    while i < len(data) - 9:                  # JPEG: walk the markers to the frame header
        if data[i] != 0xFF:
            i += 1
            continue
        marker, length = data[i + 1], struct.unpack(">H", data[i + 2:i + 4])[0]
        if marker in (0xC0, 0xC1, 0xC2):
            h, w = struct.unpack(">HH", data[i + 5:i + 9])
            return w, h
        i += 2 + length
    raise ValueError("not a PNG or JPEG image")


def drawing(rid, n, w_px, h_px, name):
    """The Word run for an inline image with relationship `rid`, scaled down to the page width when wider."""
    w, h = w_px * 9525, h_px * 9525
    if w > MAX_WIDTH_EMU:
        w, h = MAX_WIDTH_EMU, round(h * MAX_WIDTH_EMU / w)
    return ('<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
            f'<wp:extent cx="{w}" cy="{h}"/><wp:docPr id="{100 + n}" name="{esc(name)}"/>'
            '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            f'<pic:nvPicPr><pic:cNvPr id="{100 + n}" name="{esc(name)}"/><pic:cNvPicPr/></pic:nvPicPr>'
            f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{w}" cy="{h}"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic>'
            '</wp:inline></w:drawing></w:r>')


# ── Markdown (BL-22, BL-47): the subset Current state uses ────────────────────
# Paragraphs, "### ", "#### " and "##### " headings (the editor's Heading 1 to 3, #122), "> " quotes, "- " and "1. " lists
# nested two spaces per level, **bold**, *italic*
# (or _italic_), ~~strikethrough~~ and [links](https://…); a work-item link, [ABC-A-012 · Action: title](creaite:item/ABC-A-012), is
# its words; an image is a line of its own, ![caption](images/x.png)
# (BL-63). Everything else is plain text.
LIST_ITEM = re.compile(r"^( *)(?:([-*•])|(\d+)[.)])\s+(.*)$")
IMAGE_LINE = re.compile(r"^\s*!\[([^\]\n]*)\]\(([^)\s]+)\)\s*$")
LABEL = r"((?:[^\[\]\n]|\[[^\[\]\n]{0,300}\]){1,500})"   # a link's words, one level of [brackets] in them; never crosses a "["
CREAITE_SCHEME = r"(?i:creaite\s{0,5}(?::|%(?:25){0,4}3a|&#0{0,5}58;|&#x0{0,5}3a;|&colon;))"     # as the gate reads it, decoded
EMPHASIS = r"(.{1,1000}?)"      # #127 review: bold, italic or struck words, at most 1000 characters: linear, never quadratic
INLINE = re.compile(r"\[" + LABEL + r"\]\(((?:https?://|mailto:)[^)\s]+)\)|\*\*" + EMPHASIS + r"\*\*|~~" + EMPHASIS + r"~~"
                    r"|(?<![\w*])\*(?!\s)" + EMPHASIS + r"(?<!\s)\*(?![\w*])|(?<!\w)_(?!\s)" + EMPHASIS + r"(?<!\s)_(?!\w)"
                    r"|\[" + LABEL + r"\]\(\s{0,20}<?" + CREAITE_SCHEME + r"[^)\n]{0,500}\)")
# #127: a creaite: link is its words in Word, never Markdown (any case, %- or entity-encoded scheme, client_leak.SCHEME's reading)
MAX_LEVEL = 3
HEADS = {3: "h", 4: "h2", 5: "h3"}                  # Current state's three heading levels, by their number of #, as stored (#122)
HEADING = re.compile(r"^#{3,5} ")
HASHES = {v: "#" * k for k, v in HEADS.items()}
ITEM_LINK = re.compile(r" ?\[([^\]\n]+)\]\(creaite:item/([A-Za-z0-9-]{3,30})\)")


def drop_item_links(text, keep):
    """The text with every work-item link whose item `keep(id)` refuses taken out whole, its words and its address (a client report:
    the address would otherwise stay in the stored text, and edited words may not name the item); a link `keep` allows stays, so
    its words are read as they were. (#122 C, client path)"""
    return ITEM_LINK.sub(lambda m: m.group(0) if keep(m.group(2)) else "", str(text or ""))


TASK = re.compile(r"^\[([ xX])\](?:\s+|$)")                # #134: a checklist item, "- [ ] text" / "- [x] text" (Current state's checklist)
BOX = {" ": "☐ ", "x": "☑ "}                          # the glyphs Word shows for an unticked and a ticked item
# BL-89: Current state has two writing panes, one message. They are stored in the one `## Current state` section with this line
# between them; a text without it is just the left pane. Every reader except the dashboard's editor sees one continuous
# message: the left pane's content, then the right pane's, with the marker removed and nothing added.
PANE_MARKER = "<!-- creaite: second pane -->"


def pane_markers(text):
    """Where each real pane marker starts. A marker that sits inside another HTML comment (a note that quotes it, as the
    project template's guidance does) is not one (Alan, 13-10-2026): only a marker outside every comment splits the panes.
    Comments are counted as they open and close, so a quoted marker's own "-->" doesn't end the comment around it.
    Kept in step with paneMarkers in the dashboard's panel.js."""
    t, out, depth, i = text or "", [], 0, 0
    while True:
        o, c = t.find("<!--", i), t.find("-->", i)
        if o < 0 and c < 0:
            return out
        if o >= 0 and (c < 0 or o < c):
            if depth == 0 and t.startswith(PANE_MARKER, o):
                out.append(o)
                i = o + len(PANE_MARKER)
                continue
            depth, i = depth + 1, o + 4
        else:
            depth, i = max(0, depth - 1), c + 3


def pane_lines(text):
    """The numbers of the lines (as splitlines gives them) that are a real pane marker standing on its own."""
    real, out, at = set(pane_markers(text)), set(), 0
    for n, (line, raw) in enumerate(zip((text or "").splitlines(), (text or "").splitlines(True))):
        if line.strip() == PANE_MARKER and at + line.index(PANE_MARKER) in real:
            out.add(n)
        at += len(raw)
    return out


def split_panes(text):
    """(left, right) of a Current state text: split at the first real marker (any further one is dropped; one inside another
    comment is text, see pane_markers); no marker: (text, "")."""
    t = text or ""
    ms = pane_markers(t)
    if not ms:
        return t.strip(), ""
    cuts = ms + [len(t)]
    right = "".join(t[a + len(PANE_MARKER):b] for a, b in zip(cuts, cuts[1:]))
    return t[:ms[0]].strip(), re.sub(r"\n{3,}", "\n\n", right).strip()


def join_panes(left, right):
    """The stored text of two panes: the marker between them only when the right pane has content."""
    left, right = (left or "").strip(), (right or "").strip()
    if not right:
        return left
    return (left + "\n\n" if left else "") + PANE_MARKER + "\n\n" + right


def one_message(text):
    """A Current state text as one continuous message (marker removed, nothing added): what every reader but the editor uses."""
    return "\n\n".join(x for x in split_panes(text) if x)


# a line inside a quote that is a heading, a list item or a picture
QUOTE_BLOCK = re.compile(r"^\s*(?:#{3,5} |[-*•]\s|\d+[.)]\s|!\[)")
MAX_QUOTE = 2                                                              # quotes inside quotes: deeper than this are text


def md_blocks(text, panes=False, _depth=0):
    """[("p", text) | ("h" | "h2" | "h3", text) (### #### #####) | ("q", text) | ("qb", [blocks]) | ("list", [(level, ordered, text)])
    | ("img", (caption, ref))].
    List items stay together across blank lines; a quote's lines join into one paragraph, or, when it holds a heading, a list or a
    picture (#134), are read again as blocks inside the quote (a "qb"); an image is its own block.
    The pane marker ends the paragraph before it and is dropped (a ("pane", None) block with panes=True, for md_normalise)."""
    blocks, para, quote = [], [], []
    marks = pane_lines(text)

    def flush():
        """End the paragraph or quote being built and add it to the blocks."""
        if para:
            blocks.append(("p", " ".join(para)))
            para.clear()
        if quote:
            if _depth < MAX_QUOTE and any(QUOTE_BLOCK.match(x) for x in quote):
                blocks.append(("qb", md_blocks("\n".join(quote), _depth=_depth + 1)))
            else:
                blocks.append(("q", " ".join(quote)))
            quote.clear()
    for n, line in enumerate((text or "").splitlines() + [""]):
        if n in marks:
            flush()
            if panes:
                blocks.append(("pane", None))
            continue
        im = IMAGE_LINE.match(line)
        if im:
            flush()
            blocks.append(("img", (im.group(1).strip(), im.group(2))))
            continue
        m = LIST_ITEM.match(line)
        if m:
            flush()
            item = (min(len(m.group(1)) // 2, MAX_LEVEL), m.group(2) is None, m.group(4).strip())
            tops = [i for i in blocks[-1][1] if i[0] == 0] if blocks and blocks[-1][0] == "list" else []
            if tops and not (item[0] == 0 and tops[-1][1] != item[1]):   # a new top-level type is a new list
                blocks[-1][1].append(item)
            else:
                blocks.append(("list", [item]))
        elif not line.strip():
            flush()
        elif HEADING.match(line):                           # #122: three levels ("## " would end the section)
            flush()
            blocks.append((HEADS[len(line.split(" ")[0])], line.split(" ", 1)[1].strip()))
        elif line.lstrip().startswith(">"):
            if para:
                flush()
            quote.append(line.lstrip()[1:].strip())
        else:
            if quote:
                flush()
            para.append(line.strip())
    return blocks


def task_split(text):
    """(state, rest) of a checklist item's text: state " " or "x" and the text after "[ ] "; (None, text) for any other item."""
    m = TASK.match(text or "")
    return (m.group(1).lower(), text[m.end():]) if m else (None, text)


def list_prefixes(items):
    """The marker Word shows for each list item: "• ", "N. " (numbered per level) or, for a checklist item, "☐ " / "☑ "."""
    counters, kinds, out = [0] * (MAX_LEVEL + 1), [None] * (MAX_LEVEL + 1), []
    for level, ordered, _ in items:
        counters[level + 1:], kinds[level + 1:] = [0] * (MAX_LEVEL - level), [None] * (MAX_LEVEL - level)
        counters[level] = counters[level] + 1 if kinds[level] == ordered else 1
        kinds[level] = ordered
        box = None if ordered else task_split(items[len(out)][2])[0]
        out.append(f"{counters[level]}. " if ordered else BOX[box] if box else "• ")
    return out


def block_md(kind, body):
    """One block as its canonical Markdown (a quote that holds blocks has each of its lines marked with "> ")."""
    if kind == "p":
        return body
    if kind in HASHES:
        return HASHES[kind] + " " + body
    if kind == "q":
        return "> " + body
    if kind == "qb":
        return "\n".join(("> " + x).rstrip() for x in "\n\n".join(block_md(k, b) for k, b in body).splitlines())
    if kind == "img":
        return f"![{body[0]}]({body[1]})"
    return "\n".join("  " * level + (pre if ordered else "- ") + t
                     for pre, (level, ordered, t) in zip(list_prefixes(body), body))


def md_normalise(text):
    """The canonical Markdown for a text (as stored in a project's CLAUDE.md)."""
    out, seen, last = [], False, None
    for kind, body in md_blocks(text, panes=True):
        if kind == "pane":                                  # the first marker is kept, any other dropped (BL-89)
            if not seen:
                out.append(PANE_MARKER)
                last = len(out)
            seen = True
            continue
        out.append(block_md(kind, body))
    if last is not None and last == len(out):             # a marker with nothing after it is just the left pane
        out.pop()
    return "\n\n".join(out)


SPECIAL = re.compile(r"[\[*_~`]")
STAR_CLOSE = re.compile(r"(?<![\s*])\*(?![\w*])")             # a lone * that can close an italic (not part of a ** or ***)
UNDER_CLOSE = re.compile(r"(?<!\s)_(?!\w)")
MAX_NEST = 5                                                  # marks inside marks: deeper than this stays as typed


class _Frame:
    """What one reading of a stretch of text keeps: where it is, the marks and address open, the plain text so far and what has failed."""
    __slots__ = ("lo", "hi", "marks", "url", "depth", "buf", "failed")

    def __init__(self, lo, hi, marks, url, depth):
        self.lo, self.hi, self.marks, self.url, self.depth = lo, hi, marks, url, depth
        self.buf = []
        self.failed = {}                                       # kind of closer -> a start from which none exists before `hi`


class _Reader:
    """Inline Markdown read as a tree and flattened to runs: [text, bold, italic, strike, url, code] (see md_spans)."""

    def __init__(self, text):
        self.s = str(text or "")
        self.out = []

    def read(self):
        """The runs of the whole text."""
        self.run(_Frame(0, len(self.s), (False, False, False), None, 0))
        return [tuple(r) for r in self.out if r[0]]

    def add(self, f, text, code=False, marks=None, url=False):
        """A run of `text` with the frame's marks (or `marks`, and its address unless `url` says another)."""
        self.out.append([text, *(marks or f.marks), f.url if url is False else url, code])

    def flush(self, f):
        """The plain text read so far, as one run."""
        if f.buf:
            self.add(f, "".join(f.buf))
            f.buf.clear()

    def run(self, f):
        """Read s[f.lo:f.hi]: plain text up to the next mark, then whatever the mark opens."""
        s, i = self.s, f.lo
        while i < f.hi:
            m = SPECIAL.search(s, i, f.hi)
            if not m:
                f.buf.append(s[i:f.hi])
                break
            p = m.start()
            f.buf.append(s[i:p])
            end = getattr(self, "open_" + {"[": "link", "*": "star", "_": "under", "~": "tilde", "`": "code"}[m.group()])(f, p)
            if end is None:
                f.buf.append(m.group())
                end = p + 1
            i = end
        self.flush(f)

    def nest(self, f, a, b, marks=None, url=False):
        """s[a:b] read as a stretch of its own, with more marks open (deeper than MAX_NEST it stays as typed)."""
        self.flush(f)
        inner = tuple(x or y for x, y in zip(marks or (False,) * 3, f.marks))
        if f.depth < MAX_NEST:
            self.run(_Frame(a, b, inner, f.url if url is False else url, f.depth + 1))
        else:
            self.add(f, self.s[a:b])

    def close(self, f, kind, start):
        """Where the closer of `kind` is, searching from `start` (one character of content at least), or -1. A failed search is
        remembered: no later opener of that kind can find a closer where this one could not."""
        if kind in f.failed and start >= f.failed[kind]:
            return -1
        s = self.s
        if kind in ("**", "~~", "***"):
            q = s.find(kind, start, f.hi)
        else:
            m = (STAR_CLOSE if kind == "*" else UNDER_CLOSE).search(s, start, f.hi)
            q = m.start() if m else -1
        if q < 0:
            f.failed[kind] = start
        return q

    def open_code(self, f, p):
        """`code`: its words, plain. Returns where to go on from, or None when the backtick has no partner."""
        q = self.s.find("`", p + 2, f.hi)
        if q < 0:
            return None
        self.flush(f)
        self.add(f, self.s[p + 1:q], code=True)
        return q + 1

    def open_link(self, f, p):
        """[words](https:// or mailto: address), its words read for marks; a creaite: link (an item, a person; the scheme in any case,
        %- or entity-encoded), its words only. Read with the client gate's own INLINE (#127), so the links Word draws are the links
        the gate reads: one level of [brackets] in the words, every pattern bounded (linear in the text's length)."""
        m = INLINE.match(self.s, p, f.hi)
        if m and m.group(7) is not None:                       # #127: a creaite: link is its words, never a hyperlink
            self.flush(f)
            self.add(f, m.group(7))
            return m.end()
        if m and m.group(1) is not None:
            n = len(self.out)
            self.nest(f, m.start(1), m.end(1), url=None)
            if len(self.out) > n:
                self.out[-1][4] = m.group(2)                   # the address follows the link's last words only
            return m.end()
        return None

    def open_star(self, f, p):
        """*** bold italic, ** bold or * italic."""
        s = self.s
        if s.startswith("***", p):
            q = self.close(f, "***", p + 4)
            if q > 0:
                self.nest(f, p + 3, q, (True, True, False))
                return q + 3
        if s.startswith("**", p):
            q = self.close(f, "**", p + 3)
            if q > 0:
                self.nest(f, p + 2, q, (True, False, False))
                return q + 2
            f.buf.append("**")
            return p + 2
        before, after = s[p - 1] if p else "", s[p + 1] if p + 1 < f.hi else " "
        if not (before.isalnum() or before in ("_", "*")) and not after.isspace() and after != "*":
            q = self.close(f, "*", p + 2)
            if q > 0:
                self.nest(f, p + 1, q, (False, True, False))
                return q + 1
        return None

    def open_under(self, f, p):
        """_italic_ (not inside a word)."""
        s = self.s
        before, after = s[p - 1] if p else "", s[p + 1] if p + 1 < f.hi else " "
        if not (before.isalnum() or before == "_") and not after.isspace():
            q = self.close(f, "_", p + 2)
            if q > 0:
                self.nest(f, p + 1, q, (False, True, False))
                return q + 1
        return None

    def open_tilde(self, f, p):
        """~~strikethrough~~."""
        if not self.s.startswith("~~", p):
            return None
        q = self.close(f, "~~", p + 3)
        if q > 0:
            self.nest(f, p + 2, q, (False, False, True))
            return q + 2
        f.buf.append("~~")
        return p + 2


def md_spans(text):
    """[(text, bold, italic, strike, url, code)]: inline Markdown read as a tree and flattened, so the marks nest (**bold with
    ~~strike~~ inside**, _italic **and bold**_, a link whose words are bold, `code`) and every mark that is paired is gone from the
    text. One reader for Word (md_runs) and for HTML/PDF (prep_page.md_inline), so the two agree. Each opener looks for its closer
    once (a failed search is remembered), and nesting is capped at MAX_NEST, so the work is linear in the text's length times the
    cap. A mark with no partner stays as typed."""
    return _Reader(text).read()


def md_runs(text):
    """[(text, bold, italic, strike, url)]: md_spans without the code flag (a code span is its words, plain)."""
    return [r[:5] for r in md_spans(text)]


def plain(text):
    """Inline Markdown as Word shows it: markers removed; a link as "text (url)"."""
    return "".join(t + (f" ({u})" if u else "") for t, _, _, _, u in md_runs(text))


def md_lines(text):
    """Each block or list item as plain text, as Word shows it ("• item", "1. item"; headings and quotes as text)."""
    return block_lines(md_blocks(text))


def block_lines(blocks):
    """md_lines for blocks already read (a quote's own blocks are shown line by line, like any others)."""
    lines = []
    for kind, body in blocks:
        if kind == "list":
            lines += [pre + plain(task_split(t)[1] if pre in BOX.values() else t) for pre, (_, _, t) in zip(list_prefixes(body), body)]
        elif kind == "img":
            continue          # the picture and its caption aren't text to compare (review.py leaves captions out too)
        elif kind == "qb":
            lines += block_lines(body)
        else:
            lines.append(plain(body))
    return lines


def md_from_lines(lines):
    """Word paragraphs back to Markdown: "• " becomes "- ", list items stay together, paragraphs blank-separated.
    (Formatting edited in Word, nesting, headings and quotes come back as plain lines.)"""
    out = []
    for line in lines:
        text = re.sub(r"^\s*•\s+", "- ", line.strip())
        text = re.sub(r"^[☐☑](?:\s+|$)", lambda m: "- [x] " if "☑" in m.group() else "- [ ] ", text).rstrip()   # #134: back to a checklist
        kind = "ul" if text.startswith("- ") else "ol" if re.match(r"^\d+[.)] ", text) else None
        last = out[-1].splitlines()[-1] if out else ""
        if kind and kind == ("ul" if last.startswith("- ") else "ol" if re.match(r"^\d+[.)] ", last) else None):
            out[-1] += "\n" + text
        else:
            out.append(text)
    return "\n\n".join(out)


PPR_AFTER_IND = r"<w:(?:contextualSpacing|mirrorIndents|suppressOverlap|jc|textDirection|textAlignment|" \
                r"textboxTightWrap|outlineLvl|divId|cnfStyle|rPr|sectPr|pPrChange)\b"


def with_indent(para, left=360, hanging=360):
    """The paragraph with a left (and hanging) indent, w:ind in its schema position."""
    ind = f'<w:ind w:left="{left}" w:hanging="{hanging}"/>' if hanging else f'<w:ind w:left="{left}"/>'
    para = re.sub(r"<w:ind\b[^>]*/>", "", para)
    if "<w:pPr>" not in para and not re.search(r"<w:pPr\b", para):
        return re.sub(r"(<w:p(?: [^>]*)?>)", r"\1<w:pPr>" + ind + "</w:pPr>", para, count=1)
    m = re.search(r"<w:pPr\b[^>]*>(.*?)</w:pPr>", para, re.S)
    inner = m.group(1)
    nxt = re.search(PPR_AFTER_IND, inner)
    inner = inner[:nxt.start()] + ind + inner[nxt.start():] if nxt else inner + ind
    return para[:m.start(1)] + inner + para[m.end(1):]


def styled_run(rpr, text, bold, italic, strike=False):
    """One Word text run in the template's run style `rpr`, with bold, italic and strikethrough as asked."""
    rpr = re.sub(r"<w:(?:b|i|bCs|iCs|strike)(?: [^>]*)?/>", "", rpr or "<w:rPr></w:rPr>")
    marks = ("<w:b/>" if bold else "") + ("<w:i/>" if italic else "") + ("<w:strike/>" if strike else "")
    if marks:
        m = re.search(r"<w:rFonts\b[^>]*/>|<w:rStyle\b[^>]*/>", rpr)
        at = m.end() if m else rpr.index(">") + 1
        rpr = rpr[:at] + marks + rpr[at:]
    if rpr == "<w:rPr></w:rPr>":
        rpr = ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{esc(text)}</w:t></w:r>'


STYLES = {}   # style samples taken from {{STYLE_<NAME>}} paragraphs in the template being filled (BL-47)


def md_paras(para, name, text):
    """Paragraphs for one Markdown entry, from the template paragraph holding {{NAME}}. A sub-heading uses the
    template's STYLE_TOPIC sample (the minutes' topic heading) when it has one, else bold text."""
    marker = "\ue000MD\ue000"          # private-use characters: esc keeps them (it strips the \x00 this was; #127 round 6)

    def shell(template, key):
        """(the template paragraph with its placeholder marked, the run holding the mark, that run's style) for one placeholder."""
        base = replace_in(template, {key: marker})
        run = next(m for m in re.finditer(r"<w:r(?: [^>]*)?>.*?</w:r>", base, re.S) if marker in m.group())
        return base, run, (re.search(r"<w:rPr>.*?</w:rPr>", run.group(), re.S) or [None])[0]
    base_shell, run, rpr = shell(para, name)

    def one(prefix, body, shape=None, level=0, italic=False, use=None, base=0):
        """One Markdown block as a Word paragraph in the given shell: its runs styled, indented for a list item or a quote."""
        b, rn, rp = use or (base_shell, run, rpr)
        runs = ([(prefix, False, False, False, None)] if prefix else []) + md_runs(body)
        xml = "".join(styled_run(rp, t + (f" ({u})" if u else ""), bo, it or italic, st) for t, bo, it, st, u in runs)
        p = b[:rn.start()] + xml + b[rn.end():]
        if shape == "list":
            p = with_indent(p, base + 360 * (level + 1), 360)
        elif shape == "quote":
            p = with_indent(p, 567, 0)
        return p
    topic = shell(STYLES["STYLE_TOPIC"], "STYLE_TOPIC") if "STYLE_TOPIC" in STYLES else None

    def draw_one(kind, body, inq):
        """The paragraph(s) for one block; inside a quote (#134) each is italic and indented, a list further in."""
        shape = "quote" if inq else None
        if kind == "p":
            return one("", body, shape, italic=inq)
        if kind == "h":
            return one("", body, use=topic) if topic and not inq else one("", f"**{body}**", shape, italic=inq)
        if kind in ("h2", "h3"):            # #122: the second level, bold; the third, bold italic: each a step quieter than the one above
            return one("", f"**{body}**", shape, italic=inq or kind == "h3")
        if kind == "q":
            return one("", body, "quote", italic=True)
        if kind == "qb":
            return draw(body, True)
        if kind == "img":                   # images are filled as image entries (current_entries); a stray one shows its caption
            return one("", body[0], shape, italic=inq) if body[0] else ""
        return "".join(one(pre, task_split(t)[1] if pre in BOX.values() else t, "list", level, italic=inq, base=567 if inq else 0)
                       for pre, (level, _, t) in zip(list_prefixes(body), body))

    def draw(blocks, inq=False):
        """The paragraphs for these blocks."""
        return "".join(draw_one(kind, body, inq) for kind, body in blocks)
    return draw(md_blocks(text)) or replace_in(para, {name: NONE})


def item_para(para, name, entry):
    """One paragraph from a template paragraph; entry is text, {"flag": …, "text": …}, {"md": …} or a prepared image."""
    if isinstance(entry, dict) and "md" in entry:
        return md_paras(para, name, entry["md"])
    if isinstance(entry, dict) and "drawing" in entry:
        out = replace_in(para, {name: ""})
        m = re.search(r"</w:pPr>", out)
        at = m.end() if m else re.match(r"<w:p(?: [^>]*)?>", out).end()
        out = out[:at] + entry["drawing"] + out[at:]
        if entry.get("caption"):
            out += replace_in(para, {name: entry["caption"]})
        return out
    if isinstance(entry, dict):
        out = replace_in(para, {name: entry.get("text", "")})
        if entry.get("flag"):
            m = re.search(r"</w:pPr>", out)
            at = m.end() if m else re.match(r"<w:p(?: [^>]*)?>", out).end()
            out = out[:at] + pill(entry["flag"]) + out[at:]
        return out
    return replace_in(para, {name: entry})


# #127 round 6: the characters XML 1.0 doesn't allow (control characters other than tab, line feed and carriage return; U+FFFE,
# U+FFFF; a lone surrogate): one of them in document.xml and Word won't open the file. Those a line could break at are a space.
NOT_XML = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff\ud800-\udfff]")


def esc(s):
    """Text escaped for Word XML (&, < and >), without the characters XML doesn't allow (NOT_XML; #127 round 6)."""
    s = NOT_XML.sub(lambda m: " " if m.group() in "\x0b\x0c\x1c\x1d\x1e" else "", str(s))
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ===== #121: a link in a text value is a real Word hyperlink =====
# A value holding `[words](address)` is filled with the words marked by control characters (\x01 index \x02 words \x03: none can occur in
# Word text), and finish_links turns each mark into a <w:hyperlink> run once the whole part is filled, adding the relationship to the rels.
# Only an address linktext.valid_address accepts is ever marked; anything else stays the literal characters.
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
LINKS = []                                          # the addresses of the marks of the fill in progress
MARK = re.compile("\x01(\\d+)\x02([^\x01\x02\x03]*)\x03")
RUN = re.compile(r"(<w:r(?: [^>]*)?>)(<w:rPr>.*?</w:rPr>)?(<w:t(?: [^>]*)?>)([^<]*\x01[^<]*)(</w:t>)(</w:r>)", re.S)
# the run properties that follow <w:u> in the schema, and those that follow <w:color>
RPR_AFTER_U = "effect|bdr|shd|fitText|vertAlign|rtl|cs|em|lang|eastAsianLayout|specVanish|oMath"
RPR_AFTER_COLOR = r"<w:(?:spacing|w|kern|position|sz|szCs|highlight|u|" + RPR_AFTER_U + r")\b"
RPR_AFTER_U = r"<w:(?:" + RPR_AFTER_U + r")\b"


def esc_links(value):
    """A value escaped for Word XML, its links marked for finish_links (a value with none is escaped as always)."""
    text = re.sub("[\x01-\x03]", "", str(value))
    if "](" not in text:
        return esc(text)
    segs = linktext.segments(text)
    if not any(h for _, h in segs):
        return esc(text)
    out = []
    for t, h in segs:
        if h:
            LINKS.append(h)
            out.append(f"\x01{len(LINKS) - 1}\x02{esc(t)}\x03")
        else:
            out.append(esc(t))
    return "".join(out)


def link_rpr(rpr):
    """A run's properties in the hyperlink look (blue, underlined), in the order Word's schema wants them."""
    rpr = re.sub(r"<w:(?:color|u)\b[^>]*/>", "", rpr or "<w:rPr></w:rPr>")
    m = re.search(RPR_AFTER_COLOR, rpr)
    at = m.start() if m else rpr.rindex("</w:rPr>")
    rpr = rpr[:at] + '<w:color w:val="0563C1"/>' + rpr[at:]
    m = re.search(RPR_AFTER_U, rpr)
    at = m.start() if m else rpr.rindex("</w:rPr>")
    return rpr[:at] + '<w:u w:val="single"/>' + rpr[at:]


def finish_links(xml, rels):
    """Turn the marks in a filled part into hyperlinks. `rels` collects (relationship id, address) for the document's rels part (None: the
    part has no rels to add to, and a mark is left as its plain words). A mark inside a run of more than plain text is left as its words."""
    def hyperlink(m, rpr):
        """One mark as a <w:hyperlink> run, its relationship recorded."""
        rid = f"rIdCreaiteLink{len(rels) + 1}"
        rels.append((rid, LINKS[int(m.group(1))]))
        return (f'<w:hyperlink r:id="{rid}" w:history="1"><w:r>{link_rpr(rpr)}'
                f'<w:t xml:space="preserve">{m.group(2)}</w:t></w:r></w:hyperlink>')

    def run(m):
        """One text run split at its marks: plain runs in the run's own look, a hyperlink for each mark."""
        if rels is None:
            return m.group(0)
        rpr = m.group(2) or ""
        out, at, text = "", 0, m.group(4)

        def plain(t):
            """The run's look with some of its text (nothing for an empty piece)."""
            return f'<w:r>{rpr}<w:t xml:space="preserve">{t}</w:t></w:r>' if t else ""
        for k in MARK.finditer(text):
            out += plain(text[at:k.start()]) + hyperlink(k, rpr)
            at = k.end()
        return out + plain(text[at:])
    xml = RUN.sub(run, xml)
    return MARK.sub(lambda k: k.group(2), xml).replace("\x01", "").replace("\x02", "").replace("\x03", "")


def unesc(s):
    """Word XML text back to plain text."""
    return s.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&apos;", "'").replace("&amp;", "&")


def read_parts(path):
    """Every part of a .docx as (zip info, bytes), in order."""
    with zipfile.ZipFile(path) as z:
        return [(i, z.read(i.filename)) for i in z.infolist()]


def write_parts(parts, out):
    """Write the parts as a .docx at `out`, through a temporary file so a failure leaves the old one whole."""
    tmp = Path(str(out) + ".tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for info, raw in parts:
            z.writestr(info, raw)
    tmp.replace(out)


# ── fill ──────────────────────────────────────────────────────────────────────

def replace_in(xml, values):
    """Replace each {{NAME}} in the XML's text runs with its value, escaped; a placeholder not in `values` is left."""
    def sub(m):
        """One text run with its placeholders filled."""
        text = re.sub(r"\{\{(\w+)\}\}", lambda p: esc_links(values[p.group(1)]) if p.group(1) in values else p.group(0),
                      m.group(2))
        return m.group(1) + text + m.group(3)
    return TEXT.sub(sub, xml)


# ===== BL-229 (v1.7.0): fill_xml in its four steps, run in the order they always ran (test_fill_xml_pinned.py) =====
def fill_xml(xml, values):
    """Fill a Word document's XML: style samples out, then table rows, topic groups and paragraph lists, then the plain
    placeholders."""
    xml = _take_style_samples(xml)
    xml = _fill_table_rows(xml, values)
    xml = _fill_topic_groups(xml, values)
    xml = _fill_paragraph_lists(xml, values)
    return replace_in(xml, {k: v for k, v in values.items() if not isinstance(v, list)})


def _take_style_samples(xml):
    """Style samples ({{STYLE_<NAME>}} paragraphs) are taken out first and used by Markdown entries (BL-47)."""
    STYLES.clear()
    for m in list(PARA.finditer(xml)):
        names = re.findall(r"\{\{(STYLE_\w+)\}\}", m.group())
        if names:
            STYLES[names[0]] = m.group()
    for sample in STYLES.values():
        xml = xml.replace(sample, "", 1)
    return xml


def _is_table(rows):
    """A list of plain dicts (not topic groups or entries) fills a table row, once per dict."""
    if not (isinstance(rows, list) and (not rows or isinstance(rows[0], dict))):
        return False
    return not (rows and ("heading" in rows[0] or "text" in rows[0] or "md" in rows[0]))


def _table_row_for(xml, label, rows, row, keys):
    """True when this table row is the one `label` fills: it holds the rows' placeholders, or (an empty list) only
    placeholders sharing the label's initial, e.g. ACTIONS → {{A_…}}, and the label isn't a paragraph list."""
    names = set(re.findall(r"\{\{(\w+)\}\}", row))
    empty_match = not rows and names and all(n.startswith(label[0] + "_") for n in names) \
        and "{{%s}}" % label not in xml and "{{%s_HEADING}}" % label not in xml   # a paragraph list isn't a table
    return bool(names) and bool(names & set(keys) or empty_match)


def _fill_table_rows(xml, values):
    """Table rows: a list of dicts repeats the row holding its placeholders; an empty list leaves one row saying None."""
    for label, rows in values.items():
        if not _is_table(rows):
            continue
        keys = sorted({k for r in rows for k in r}) if rows else []
        for m in list(ROW.finditer(xml)):
            row = m.group()
            if not _table_row_for(xml, label, rows, row, keys):
                continue
            names = set(re.findall(r"\{\{(\w+)\}\}", row))
            if rows:
                new = "".join(replace_in(row, {**{n: "" for n in names}, **r}) for r in rows)
            else:
                first = sorted(names, key=row.index)[0] if names else None
                new = replace_in(row, {n: (NONE if n == first else "") for n in names})
            xml = xml[:m.start()] + new + xml[m.end():]
            break
    return xml


def _is_groups(name, groups, xml):
    return (isinstance(groups, list) and groups and isinstance(groups[0], dict) and "heading" in groups[0]) \
        or (isinstance(groups, list) and not groups and "{{%s_HEADING}}" % name in xml)


def _fill_topic_groups(xml, values):
    """Topic groups: a heading paragraph followed by item paragraphs, repeated per group."""
    for name, groups in values.items():
        if not _is_groups(name, groups, xml):
            continue
        paras = list(PARA.finditer(xml))
        hi = next((i for i, m in enumerate(paras) if "{{%s_HEADING}}" % name in m.group()), None)
        ii = next((i for i, m in enumerate(paras) if "{{%s_ITEM}}" % name in m.group()), None)
        if hi is None or ii is None:
            continue
        head_p, item_p = paras[hi].group(), paras[ii].group()
        new = ""
        for g in groups:
            new += replace_in(head_p, {f"{name}_HEADING": g["heading"]})
            new += "".join(item_para(item_p, f"{name}_ITEM", e) for e in (g.get("items") or [NONE]))
        if not groups:
            new = replace_in(item_p, {f"{name}_ITEM": NONE})
        start, end = min(paras[hi].start(), paras[ii].start()), max(paras[hi].end(), paras[ii].end())
        xml = xml[:start] + new + xml[end:]
    return xml


def _is_paragraph_list(items):
    if not isinstance(items, list):
        return False
    if items and isinstance(items[0], dict) and "heading" in items[0]:
        return False
    return not (items and isinstance(items[0], dict) and not {"text", "drawing", "md"} & set(items[0]))


def _fill_paragraph_lists(xml, values):
    """Paragraph lists: a list repeats the placeholder's paragraph (entries may carry a label)."""
    for name, items in values.items():
        if not _is_paragraph_list(items):
            continue
        for m in list(PARA.finditer(xml)):
            if "{{%s}}" % name in m.group():
                para = m.group()
                new = "".join(item_para(para, name, i) for i in items) if items else replace_in(para, {name: NONE})
                xml = xml[:m.start()] + new + xml[m.end():]
                break
    return xml
# ===== end BL-229 (fill_xml) =====


def fill_story(name, raw, values, link_rels):
    """One story part filled: (its bytes, the {{PLACEHOLDERS}} left in it). Links become hyperlinks, listed in `link_rels`."""
    xml = finish_links(fill_xml(raw.decode("utf-8"), values), link_rels if name == "word/document.xml" else None)
    if name == "word/document.xml" and link_rels and "xmlns:r=" not in xml[:2000]:
        xml = xml.replace("<w:document ", f'<w:document xmlns:r="{REL_NS}" ', 1)
    left = set(re.findall(r"\{\{(\w+)\}\}", "".join(t for _, t, _ in TEXT.findall(xml))))
    return xml.encode("utf-8"), left


def add_relationships(parts, media, link_rels):
    """The parts with the pictures (`media`) and hyperlinks (`link_rels`) added to the document's relationships and the picture types to
    the content types; the pictures themselves follow the parts."""
    image, hyper = f"{REL_NS}/image", f"{REL_NS}/hyperlink"
    out_parts = []
    for info, raw in parts:
        if info.filename == "word/_rels/document.xml.rels":
            raw = raw.decode("utf-8").replace("</Relationships>", "".join(
                f'<Relationship Id="{rid}" Type="{image}" Target="{name[5:]}"/>' for name, _, rid in media)
                + "".join(f'<Relationship Id="{rid}" Type="{hyper}" Target="{esc(href)}" TargetMode="External"/>'
                          for rid, href in link_rels) + "</Relationships>").encode("utf-8")
        elif info.filename == "[Content_Types].xml":
            ct = raw.decode("utf-8")
            for ext, mime in (("png", "image/png"), ("jpg", "image/jpeg"), ("jpeg", "image/jpeg")):
                if media and any(name.endswith("." + ext) for name, _, _ in media) and f'Extension="{ext}"' not in ct:
                    ct = ct.replace("<Default ", f'<Default Extension="{ext}" ContentType="{mime}"/><Default ', 1)
            raw = ct.encode("utf-8")
        out_parts.append((info, raw))
    return out_parts + [(zipfile.ZipInfo(name), data) for name, data, _ in media]


def cmd_fill(template, values_file, out):
    """The fill command: fill a template's {{PLACEHOLDERS}} from values.json (text, lists, Markdown, images, topic groups, table rows) and
    write out.docx. Returns 1, writing nothing, if any is left unfilled."""
    values = json.loads(Path(values_file).read_text(encoding="utf-8"))
    media = []                                  # (part name, bytes, rel id) for images
    for key, items in values.items():
        if isinstance(items, list) and any(isinstance(e, dict) and "image" in e for e in items):
            prepared = []
            for entry in items:
                if not (isinstance(entry, dict) and "image" in entry):    # Markdown between images (BL-63)
                    prepared.append(entry)
                    continue
                f = Path(entry["image"])
                f = f if f.is_absolute() else paths.resolve(f.as_posix())
                if not f.is_file() or f.suffix.lower() not in IMAGE_TYPES:
                    print(f"Note: image not found or not PNG/JPEG, left out: {entry['image']}")
                    continue
                data = f.read_bytes()
                w, h = image_size(data)
                n = len(media) + 1
                rid = f"rIdCreaiteImg{n}"
                media.append((f"word/media/creaite-{n}{f.suffix.lower()}", data, rid))
                prepared.append({"drawing": drawing(rid, n, w, h, f.name), "caption": entry.get("caption", "")})
            values[key] = prepared
    parts = []
    left = set()
    LINKS.clear()
    link_rels = []                              # (relationship id, address) of the hyperlinks made (#121)
    for info, raw in read_parts(template):
        if STORY.match(info.filename):
            raw, unfilled = fill_story(info.filename, raw, values, link_rels)
            left |= unfilled
        parts.append((info, raw))
    if left:
        print("Not filled: " + ", ".join(sorted(left)) + ". Nothing was written.")
        return 1
    if media or link_rels:
        parts = add_relationships(parts, media, link_rels)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    write_parts(parts, out)
    print(f"Wrote {out}")
    paths.consume_draft(values_file)                    # BL-118: filled, so the values have done their job (only a .json file in drafts/)
    return 0


# ── text ──────────────────────────────────────────────────────────────────────

def accept_xml(xml):
    """Accept every tracked change in one story part. Returns (xml, number of changes)."""
    n = 0

    def opening(tag):  # an opening tag, not a self-closing marker like <w:del .../>
        """A pattern for the tag's opening tag, never a self-closing one."""
        return rf"<{tag}(?:\s[^>]*)?(?<!/)>"

    for tag in ("w:del", "w:moveFrom"):  # deleted or moved-away content goes
        xml, k = re.subn(rf"{opening(tag)}.*?</{tag}>", "", xml, flags=re.S)
        n += k
    for tag in ("w:ins", "w:moveTo"):    # inserted or moved-in content stays; only the wrapper goes
        xml, k = re.subn(opening(tag), "", xml)
        xml = xml.replace(f"</{tag}>", "")
        n += k
    for tag in ("w:rPrChange", "w:pPrChange", "w:tblPrChange", "w:trPrChange", "w:tcPrChange",
                "w:sectPrChange", "w:tblGridChange", "w:numberingChange"):
        xml, k = re.subn(rf"{opening(tag)}.*?</{tag}>|<{tag}(?:\s[^>]*)?/>", "", xml, flags=re.S)
        n += k
    xml = re.sub(r"<w:(moveFrom|moveTo)Range(Start|End)(?:\s[^>]*)?/>", "", xml)
    # Paragraph marks: an inserted mark just loses its marker…
    xml, k = re.subn(r"<w:ins(?:\s[^>]*)?/>", "", xml)
    n += k
    # …a deleted mark joins the paragraph to the next one (or drops it if nothing is left in it)
    while True:
        m = next((p for p in PARA.finditer(xml)
                  if re.search(r"<w:del(?:\s[^>]*)?/>", (re.search(r"<w:pPr>.*?</w:pPr>", p.group(), re.S)
                                                         or re.match("", "")).group())), None)
        if not m:
            break
        n += 1
        para = m.group()
        body = re.sub(r"^<w:p(?:\s[^>]*)?>(?:<w:pPr>.*?</w:pPr>)?", "", para, flags=re.S)[:-len("</w:p>")]
        rest = xml[m.end():]
        nxt = PARA.search(rest)
        if nxt and "".join(t for _, t, _ in TEXT.findall(body)).strip():
            np = nxt.group()
            head = re.match(r"^<w:p(?:\s[^>]*)?>(?:<w:pPr>.*?</w:pPr>)?", np, re.S).group()
            xml = xml[:m.start()] + rest[:nxt.start()] + head + body + np[len(head):] + rest[nxt.end():]
        else:
            xml = xml[:m.start()] + rest
    return xml, n


def story_text(xml):
    """A story part's plain text: one line per paragraph, a table row's cells joined by " | "."""
    lines = []
    pos = 0
    for m in re.finditer(r"<w:tbl>.*?</w:tbl>|<w:p(?: [^>]*)?>.*?</w:p>", xml, re.S):
        if m.start() < pos:
            continue
        pos = m.end()
        block = m.group()
        if block.startswith("<w:tbl>"):
            for row in ROW.findall(block):
                cells = re.findall(r"<w:tc>.*?</w:tc>", row, re.S)
                lines.append(" | ".join(" ".join(unesc("".join(t for _, t, _ in TEXT.findall(p)))
                                                 for p in PARA.findall(c)).strip() for c in cells))
        else:
            lines.append(unesc("".join(t for _, t, _ in TEXT.findall(block))))
    return "\n".join(lines)


def show_links(xml, rels):
    """A story part with each hyperlink followed by its address in brackets ("the plan (https://…)"), so a text preview of a report shows
    where a link goes (#121). `rels` is the document's relationships part as text."""
    where = {m.group(1): unesc(m.group(2))
             for m in re.finditer(r'<Relationship\b[^>]*?\bId="([^"]+)"[^>]*?\bTarget="([^"]*)"[^>]*?/>', rels or "")}

    def address(m):
        """The hyperlink with its address after its words (a link the rels do not know is left as it is)."""
        if m.group(2) not in where:
            return m.group(0)
        shown = esc(re.sub("^mailto:", "", where[m.group(2)], flags=re.I))
        return m.group(1) + f'<w:r><w:t xml:space="preserve"> ({shown})</w:t></w:r>' + m.group(3)
    return re.sub(r'(<w:hyperlink\b[^>]*?\br:id="([^"]+)"[^>]*>.*?)(</w:hyperlink>)', address, xml, flags=re.S)


def cmd_text(path):
    """The text command: print the document's body as plain text, tracked changes accepted, a hyperlink followed by its address."""
    parts = read_parts(path)
    rels = next((raw.decode("utf-8") for info, raw in parts if info.filename == "word/_rels/document.xml.rels"), "")
    for info, raw in parts:
        if info.filename == "word/document.xml":
            xml, _ = accept_xml(raw.decode("utf-8"))
            print(story_text(show_links(xml, rels)))
    return 0


# ── clean ─────────────────────────────────────────────────────────────────────

def count_comments(parts):
    """How many comments the document's parts hold."""
    for info, raw in parts:
        if info.filename == "word/comments.xml":
            return len(re.findall(r"<w:comment ", raw.decode("utf-8")))
    return 0


def clean_parts(parts):
    """The parts with tracked changes accepted, comments removed and change tracking off: (parts, changes accepted, comments removed)."""
    changes = 0
    comments = count_comments(parts)
    out = []
    for info, raw in parts:
        name = info.filename
        if COMMENT_PARTS.match(name) or name == "word/_rels/comments.xml.rels":
            continue
        if STORY.match(name):
            xml, n = accept_xml(raw.decode("utf-8"))
            changes += n
            xml = re.sub(r"<w:comment(RangeStart|RangeEnd)(?: [^>]*)?/>", "", xml)
            xml = re.sub(r"<w:r(?: [^>]*)?>(?:(?!</w:r>).)*<w:commentReference[^>]*/>(?:(?!</w:r>).)*</w:r>", "", xml,
                         flags=re.S)
            raw = xml.encode("utf-8")
        elif name == "word/_rels/document.xml.rels":
            raw = re.sub(r'<Relationship [^>]*Target="comments(Extended|Ids|Extensible)?\.xml"[^>]*/>', "",
                         raw.decode("utf-8")).encode("utf-8")
        elif name == "[Content_Types].xml":
            raw = re.sub(r'<Override [^>]*PartName="/word/comments(Extended|Ids|Extensible)?\.xml"[^>]*/>', "",
                         raw.decode("utf-8")).encode("utf-8")
        elif name == "word/settings.xml":
            raw = re.sub(r"<w:trackRevisions(?: [^>]*)?/>", "", raw.decode("utf-8")).encode("utf-8")
        out.append((info, raw))
    return out, changes, comments


def is_open(path):
    """Whether Word has the file open (its ~$ lock file is beside it)."""
    p = Path(path)
    return (p.parent / ("~$" + p.name[2:])).exists() or (p.parent / ("~$" + p.name)).exists()


def cmd_clean(src, out=None):
    """The clean command: accept tracked changes and remove comments, into `out` or in place (inside system/staging/drafts/ only, BL-271).
    Returns 3, changing nothing, while Word has it open."""
    if is_open(src):
        print(f"{Path(src).name} is open in Word. Close it, then try again. Nothing was changed.")
        return 3
    parts, changes, comments = clean_parts(read_parts(src))
    write_parts(parts, out or src)
    print(f"Accepted {changes} tracked change{'s' if changes != 1 else ''} and removed {comments} "
          f"comment{'s' if comments != 1 else ''}.")
    return 0


def cmd_status(path):
    """The status command: print {tracked_changes, comments, open_in_word} as JSON. Writes nothing."""
    parts = read_parts(path)
    changes = sum(accept_xml(raw.decode("utf-8"))[1] for info, raw in parts if STORY.match(info.filename))
    print(json.dumps({"tracked_changes": changes, "comments": count_comments(parts), "open_in_word": is_open(path)}))
    return 0


# ── build-adhoc (BL-75) ───────────────────────────────────────────────────────

ADHOC_BLOCKS = {"title": "{{TITLE}}", "subtitle": "{{SUBTITLE}}", "status": "{{STATUS_LINE}}", "when": "{{WHEN}}",
                "heading": "{{HEADING}}", "para": "{{PARA}}", "bullet": "{{BULLET}}", "source": "{{SOURCE}}"}


def put_text(para, text):
    """The paragraph with its text replaced: the first text run keeps its formatting, the others go. Newlines become
    line breaks."""
    runs = re.findall(r"<w:r>(?:(?!</w:r>).)*?<w:t(?: [^>]*)?>[^<]*</w:t>(?:(?!</w:r>).)*?</w:r>", para, re.S)
    if not runs:
        raise ValueError("the template paragraph has no text run to fill")
    body = esc(text).replace("\n", '</w:t><w:br/><w:t xml:space="preserve">')
    first = re.sub(r"<w:t(?: [^>]*)?>[^<]*</w:t>", lambda m: f'<w:t xml:space="preserve">{body}</w:t>', runs[0], count=1)
    para = para.replace(runs[0], first, 1)
    for r in runs[1:]:
        para = para.replace(r, "", 1)
    return re.sub(r"<w:lastRenderedPageBreak/>", "", para)


def adhoc_table(blocks, columns, rows, total):
    """The template's table with len(columns) columns and a row per entry in rows."""
    table = blocks["table"]
    trs = re.findall(r"<w:tr>.*?</w:tr>", table, re.S)
    head_cell = re.search(r"<w:tc>.*?</w:tc>", trs[0], re.S).group()
    data_cell = re.search(r"<w:tc>.*?</w:tc>", trs[1], re.S).group()
    weights = []
    for i, c in enumerate(columns):
        w = c.get("width") if isinstance(c, dict) else None
        if not w:
            longest = max([len(str(r[i])) for r in rows] + [0])
            avg = sum(len(str(r[i])) for r in rows) / len(rows) if rows else 0
            w = min(60, max(len(c["header"]) + 3, 8, (avg + longest) / 2 if rows else 8))
        weights.append(float(w))
    widths = [round(total * w / sum(weights)) for w in weights]

    def cell(template, width, text):
        """One table cell from the template cell, at `width`, holding `text`."""
        c = re.sub(r'<w:tcW w:w="\d+"', f'<w:tcW w:w="{width}"', template, count=1)
        para = re.search(r"<w:p>.*?</w:p>", c, re.S).group()
        return c.replace(para, put_text(para, text), 1)

    def row(template_row, template_cell, texts):
        """One table row from the template row: a cell per text, at the columns' widths."""
        return template_row[:template_row.index("<w:tc>")] + "".join(
            cell(template_cell, w, t) for w, t in zip(widths, texts)) + "</w:tr>"
    tbl_head = table[:table.index("<w:tblGrid>")]
    grid = "<w:tblGrid>" + "".join(f'<w:gridCol w:w="{w}"/>' for w in widths) + "</w:tblGrid>"
    tbl_head = re.sub(r'(<w:tblW w:w=")\d+(")', rf"\g<1>{total}\2", tbl_head, count=1)
    return (tbl_head + grid + row(trs[0], head_cell, [c["header"] for c in columns])
            + "".join(row(trs[1], data_cell, [str(x) if x is not None else "" for x in r]) for r in rows) + "</w:tbl>")


def build_adhoc(template, spec, out):
    """Write a branded one-off document: the template's wordmark and styles, the spec's title block and sections.
    Returns the number of tables made."""
    parts = read_parts(template)
    xml = next(raw for info, raw in parts if info.filename == "word/document.xml").decode("utf-8")
    head, body = xml[:xml.index("<w:body>") + len("<w:body>")], xml[xml.index("<w:body>") + len("<w:body>"):]
    sect = re.findall(r"<w:sectPr.*?</w:sectPr>", body, re.S)[-1]
    found = re.findall(r"<w:p(?: [^>]*)?>.*?</w:p>|<w:tbl>.*?</w:tbl>", body, re.S)
    text = lambda b: "".join(re.findall(r"<w:t[^>]*>([^<]*)", b))  # noqa: E731
    blocks = {k: next((b for b in found if text(b) == v), None) for k, v in ADHOC_BLOCKS.items()}
    blocks["table"] = next((b for b in found if b.startswith("<w:tbl>")), None)
    blocks["wordmark"] = next((b for b in found if "<w:drawing" in b), "")
    blocks["spacer"] = next((b for b in found if not re.search(r"<w:t[ >]", b) and "<w:drawing" not in b
                             and not b.startswith("<w:tbl>")), "<w:p/>")
    missing = [k for k, b in blocks.items() if b is None]
    if missing:
        raise ValueError(f"{Path(template).name} is missing its {', '.join(missing)} block; rebuild it with "
                         "dev/tools/build_templates.py adhoc")
    if spec.get("landscape"):
        margins = re.search(r'<w:pgMar [^>]*w:left="(\d+)"[^>]*w:right="(\d+)"', sect) or \
            re.search(r'<w:pgMar [^>]*w:right="(\d+)"[^>]*w:left="(\d+)"', sect)
        side = sum(int(g) for g in margins.groups()) if margins else 2880
        sect = re.sub(r"<w:pgSz [^>]*/>", '<w:pgSz w:w="16838" w:h="11906" w:orient="landscape"/>', sect, count=1)
        total = 16838 - side
    else:
        total = 9350
    out_blocks, tables = [blocks["wordmark"]], 0
    for key in ("title", "subtitle", "status", "when"):
        if spec.get(key):
            out_blocks.append(put_text(blocks[key], spec[key]))
    for sec in spec.get("sections") or []:
        if sec.get("heading"):
            out_blocks.append(put_text(blocks["heading"], sec["heading"]))
        out_blocks += [put_text(blocks["para"], t) for t in sec.get("paragraphs") or []]
        out_blocks += [put_text(blocks["bullet"], t) for t in sec.get("bullets") or []]
        tb = sec.get("table")
        if tb:
            columns = [c if isinstance(c, dict) else {"header": str(c)} for c in tb.get("columns") or []]
            rows = tb.get("rows") or []
            bad = [n for n, r in enumerate(rows, 1) if len(r) != len(columns)]
            if not columns or bad:
                raise ValueError("a table needs columns, and every row one cell per column"
                                 + (f" (row {bad[0]} has {len(rows[bad[0] - 1])} cells for {len(columns)} columns)" if bad else ""))
            out_blocks += [adhoc_table(blocks, columns, rows, total), blocks["spacer"]]
            tables += 1
        if sec.get("note"):
            out_blocks.append(put_text(blocks["para"], sec["note"]))
    if spec.get("source"):
        out_blocks.append(put_text(blocks["source"], spec["source"]))
    doc = head + "".join(out_blocks) + sect + "</w:body></w:document>"
    result = []
    for info, raw in parts:
        if info.filename == "word/document.xml":
            raw = doc.encode("utf-8")
        elif info.filename == "docProps/core.xml" and spec.get("title"):
            raw = re.sub(r"(<dc:title>)[^<]*(</dc:title>)", lambda m: m.group(1) + esc(spec["title"]) + m.group(2),
                         raw.decode("utf-8")).encode("utf-8")
        result.append((info, raw))
    write_parts(result, Path(out))
    return tables


def cmd_build_adhoc(template, spec_file, out):
    """The build-adhoc command: a one-off branded document (BL-75) from spec.json into out.docx. Returns 1, writing nothing, on a bad
    spec."""
    try:
        tables = build_adhoc(template, json.loads(Path(spec_file).read_text(encoding="utf-8")), out)
    except ValueError as e:
        print(f"creaite: {e}")
        return 1
    print(f"Wrote {out} ({tables} table{'s' if tables != 1 else ''}).")
    return 0


def outside_drafts(out):
    """Why the command line won't write `out`, or None (BL-271): fill, build-adhoc and clean write only inside
    system/staging/drafts/. A project's file changes through filechange.py (a backup, the log, an undo and, when it is
    sensitive, Alan's card), from a new version built here."""
    import os
    real = Path(os.path.realpath(paths.resolve(str(out)) if not Path(out).is_absolute() else out))
    drafts = Path(os.path.realpath(paths.DRAFTS))
    if real == drafts or drafts in real.parents:
        return None
    return (f"docx_tools.py writes only inside {paths.rel(paths.DRAFTS)}/; nothing was written. To change {out}, build the "
            f"new version there, then run system/scripts/run filechange.py edit \"{out}\" --from <that file> --why \"…\"")


WRITES = {"fill": 2, "build-adhoc": 2, "clean": -1}   # the command line's written file: its argument (clean: out, or in place)


def refused_write(cmd, args):
    """True (and says why) when this command would write outside system/staging/drafts/ (BL-271)."""
    if cmd not in WRITES or not args:
        return False
    why = outside_drafts(args[WRITES[cmd]] if len(args) > WRITES[cmd] else args[-1])
    if why:
        print(f"creaite: {why}")
    return bool(why)


def main(argv):
    """The command line: fill, text, clean, status and build-adhoc. A command that would write outside system/staging/drafts/ is refused
    first (BL-271)."""
    cmd, args = (argv[0], argv[1:]) if argv else ("", [])
    if refused_write(cmd, args):
        return 2
    if cmd == "build-adhoc" and len(args) == 3:
        return cmd_build_adhoc(*args)
    if cmd == "fill" and len(args) == 3:
        return cmd_fill(*args)
    if cmd == "text" and len(args) == 1:
        return cmd_text(args[0])
    if cmd == "clean" and len(args) in (1, 2):
        return cmd_clean(*args)
    if cmd == "status" and len(args) == 1:
        return cmd_status(args[0])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
