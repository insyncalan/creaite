"""#375 E1, slice S2: an invite body (HTML, plain text or markdown) as text LINES with the block structure kept.

Pure plain code, standard library only (html.parser). No I/O, no regular expression that can backtrack on raw input.

    to_lines(html_or_text) -> list[str]     lines; a BLOCK is a run of consecutive non-blank lines; blocks are separated by ONE blank line
    looks_like_html(text) -> bool           True when the text holds a real HTML tag, comment or doctype

Why: flattening table cells first is what split a label from its value in #369. Here the tree is cut into blocks BEFORE it is flattened:

  * a data table (no nested table, more than one cell, no cell with two or more paragraphs or lists) is ONE block: every ROW is one line of
    that block (cells joined by ' | ', header rows too; a row with a multi-line cell keeps one line per cell line), so a label and
    its value (same cell, next cell, next row, a header row and the next row) stay together;
  * a layout table (a table around other content) is cut: each cell is its own run of blocks;
  * p, h1-h6, blockquote, ul/ol (nested lists stay in the outer list's block), pre, hr and a table start and end a block;
  * div, li, tr, td, br and unknown tags start a new LINE; two or more br in a row (an empty line) end the block;
  * script, style, head, title, template, comments and anything hidden (display:none, visibility:hidden, mso-hide:all, hidden) are dropped.

Output rules (they make to_lines idempotent on its own text): every line is stripped, HTML whitespace is collapsed, no line is empty
except the single blank between blocks, none first or last, and no line holds a control character. A "<" that starts a tag-like word in
the output is written as U+2039 so that a decoded "&lt;div&gt;" is not taken for HTML on a second pass. Plain text and markdown pass
through line by line (stripped, runs of blank lines collapsed): a markdown table's rows stay consecutive, so they are one block.

Limits: input is cut to MAX_INPUT characters; the tree stops growing deeper than MAX_DEPTH (deeper tags are read as text-only); linear.
"""
from html.parser import HTMLParser

MAX_INPUT = 1000000
MAX_DEPTH = 120
DIVIDER = "________________"

DROP = frozenset(["script", "style", "head", "title", "template", "xml", "object", "iframe"])
VOID = frozenset(["br", "hr", "img", "meta", "link", "input", "wbr", "col", "area", "base", "embed", "param", "source", "track"])
INLINE = frozenset(["a", "abbr", "acronym", "b", "bdi", "bdo", "big", "cite", "code", "data", "del", "dfn", "em", "font", "i", "ins",
                    "kbd", "label", "mark", "o:p", "q", "s", "samp", "small", "span", "strike", "strong", "sub", "sup", "time", "tt",
                    "u", "var", "wbr", "img", "html", "body", "nobr", "v:textbox", "noscript"])
BLOCK = frozenset(["p", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "ul", "ol", "pre", "menu", "dir"])
LISTS = frozenset(["ul", "ol", "menu", "dir"])
TRANSPARENT = frozenset(["tbody", "thead", "tfoot", "colgroup"])
CELLS = frozenset(["td", "th"])
HIDDEN_STYLES = ("display:none", "visibility:hidden", "mso-hide:all")
CONTROL = dict((i, " ") for i in range(32) if i != 10)
CONTROL[127] = " "
NEWLINES = ("\r\n", "\r", "\x0b", "\x0c", "\x85", " ", " ")
KNOWN_TAGS = frozenset(["html", "body", "head", "div", "p", "br", "table", "tr", "td", "th", "span", "ul", "ol", "li", "a", "b", "i", "u",
                        "strong", "em", "font", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "style", "script", "center", "img", "hr",
                        "meta", "title", "tbody", "thead", "pre", "code", "o:p", "sup", "sub", "small", "section", "article", "o", "v"])


def _tag_at(text, i):
    """The lower-case tag name that starts at text[i] == '<' (after an optional '/'), or '' when it is not a known tag."""
    j = i + 1
    n = len(text)
    if j < n and text[j] in "/":
        j += 1
    k = j
    while k < n and k - j < 12 and (text[k].isalnum() or text[k] in ":"):
        k += 1
    name = text[j:k].lower()
    if name in KNOWN_TAGS and (k >= n or text[k] in " \t\r\n/>"):
        return name
    return ""


def looks_like_html(text):
    """True when text holds a real tag of the kinds mail uses, a comment or a doctype. A bare '<' ('a < b') is not."""
    if not text:
        return False
    if len(text) > MAX_INPUT:
        text = text[:MAX_INPUT]
    last_gt = text.rfind(">")      # a tag start after the last '>' cannot be closed: linear, not quadratic (E1 pass 2, finding 10)
    i = text.find("<")
    while i != -1:
        if text.startswith("<!--", i) or text[i + 1:i + 9].lower() == "!doctype":
            return True
        if i < last_gt and _tag_at(text, i):
            return True
        i = text.find("<", i + 1)
    return False


class _Node(object):
    __slots__ = ("tag", "kids", "hidden", "has_table", "ncells", "multi", "table", "nblock")

    def __init__(self, tag, hidden=False):
        self.tag = tag
        self.kids = []
        self.hidden = hidden
        self.has_table = False
        self.ncells = 0
        self.multi = False
        self.table = None
        self.nblock = 0


def _is_hidden(attrs):
    for name, value in attrs:
        if name == "hidden":
            return True
        if name == "style" and value:
            squashed = "".join(value.lower().split())
            for bad in HIDDEN_STYLES:
                if bad in squashed:
                    return True
    return False


class _Builder(HTMLParser):
    """Builds a small tree, tolerant of broken HTML: unmatched end tags are ignored, open tags are closed at the end, a new p/li/td/tr
    closes the one it implies, and nesting past MAX_DEPTH is read as text only."""

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.root = _Node("#root")
        self.stack = [self.root]
        self.skip = ""

    def _top(self):
        return self.stack[-1]

    def _pop(self):
        node = self.stack.pop()
        parent = self.stack[-1]
        if node.has_table or node.tag == "table":
            parent.has_table = True
        return node

    def _close_to(self, tag, stops):
        """Pop up to and including the nearest open `tag`, but not past a tag in `stops`."""
        for idx in range(len(self.stack) - 1, 0, -1):
            name = self.stack[idx].tag
            if name == tag:
                while len(self.stack) > idx:
                    self._pop()
                return True
            if name in stops:
                return False
        return False

    def _nearest(self, tag):
        for idx in range(len(self.stack) - 1, 0, -1):
            if self.stack[idx].tag == tag:
                return self.stack[idx]
        return None

    def handle_starttag(self, tag, attrs):
        """A start tag: dropped, void, or a new node under the implied closes."""
        tag = tag.lower()
        if self.skip:
            return
        if tag in DROP:
            self.skip = tag
            return
        if tag in TRANSPARENT or tag in VOID and tag not in ("br", "hr"):
            return
        hidden = _is_hidden(attrs)
        if tag in ("br", "hr"):
            self._top().kids.append(_Node(tag, hidden))
            return
        self._implied_close(tag)
        if len(self.stack) >= MAX_DEPTH:
            return
        node = _Node(tag, hidden)
        top = self._top()
        top.kids.append(node)
        self._count(node)
        self.stack.append(node)

    def _count(self, node):
        """Table bookkeeping for the layout test: cells per table, and cells that hold two or more paragraphs or lists."""
        tag = node.tag
        if tag in CELLS:
            node.table = self._nearest("table")
            if node.table is not None:
                node.table.ncells += 1
        if tag in BLOCK or tag == "table":
            cell = self._nearest_cell()
            if cell is not None:
                cell.nblock += 1
                if cell.nblock >= 2 and cell.table is not None:
                    cell.table.multi = True

    def _nearest_cell(self):
        for idx in range(len(self.stack) - 1, 0, -1):
            name = self.stack[idx].tag
            if name in CELLS:
                return self.stack[idx]
            if name == "table":
                return None
        return None

    def _implied_close(self, tag):
        if tag == "li":
            self._close_to("li", LISTS | set(["table"]))
        elif tag in CELLS:
            self._close_to("td", ("table", "tr")) or self._close_to("th", ("table", "tr"))
            if self._nearest("table") is not None and self._top().tag == "table":
                self._start_implied("tr")
        elif tag == "tr":
            self._close_to("td", ("table", "tr"))
            self._close_to("th", ("table", "tr"))
            self._close_to("tr", ("table",))
        elif tag in BLOCK or tag in ("div", "table"):
            # a <p> is closed by a block tag when only inline tags separate them
            idx = len(self.stack) - 1
            while idx > 0 and self.stack[idx].tag in INLINE:
                idx -= 1
            if idx > 0 and self.stack[idx].tag == "p":
                while len(self.stack) > idx:
                    self._pop()

    def _start_implied(self, tag):
        if len(self.stack) < MAX_DEPTH:
            node = _Node(tag)
            self._top().kids.append(node)
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        """A self-closing tag, read as a start tag then an end tag."""
        tag = tag.lower()
        self.handle_starttag(tag, attrs)
        if tag not in VOID and not self.skip and tag not in TRANSPARENT and len(self.stack) > 1 and self._top().tag == tag:
            self._pop()

    def handle_endtag(self, tag):
        """An end tag closes the nearest matching open tag; an unmatched one is ignored."""
        tag = tag.lower()
        if self.skip:
            if tag == self.skip:
                self.skip = ""
            return
        if tag == "br":
            self._top().kids.append(_Node("br"))
            return
        if tag in VOID or tag in TRANSPARENT:
            return
        stops = ()
        if tag in ("td", "th", "tr"):
            stops = ("table",)
        elif tag == "li":
            stops = ("ul", "ol", "table")
        self._close_to(tag, stops)

    def handle_data(self, data):
        """Text (entities already decoded) goes under the open node."""
        if self.skip or not data:
            return
        self._top().kids.append(data)

    def finish(self):
        """Reads the rest of the input and closes every open node; returns the root."""
        try:
            self.close()
        except Exception:  # the parser gave up on the tail of a broken body: what was read so far is still used
            self.skip = ""
        while len(self.stack) > 1:
            self._pop()
        return self.root


class _Emit(object):
    def __init__(self):
        self.out = []
        self.cur = []
        self.want_blank = False
        self.nobreak = 0
        self.pre = 0
        self.after_br = False

    def text(self, s):
        """Adds inline text to the current line."""
        if s:
            self.cur.append(s)
            self.after_br = False

    def line_break(self):
        """Ends the current line (a line of only whitespace is not written)."""
        if self.cur:
            line = " ".join("".join(self.cur).translate(CONTROL).split())
            self.cur = []
            if line:
                self.add(line)

    def add(self, line):
        """Writes one finished line, after a blank line when a block break is waiting."""
        if "<" in line:
            line = _neutralise(line)
        if self.want_blank and self.out and self.out[-1] != "":
            self.out.append("")
        self.want_blank = False
        self.out.append(line)

    def block_break(self):
        """Ends the current line and the block (inside a data table or a list it is only a line break)."""
        self.line_break()
        if self.nobreak:
            return
        self.want_blank = True

    def br(self):
        """A <br>: a line break; a second one in a row ends the block."""
        had = bool(self.cur) and bool("".join(self.cur).strip())
        self.line_break()
        if had:
            self.after_br = True
        elif self.after_br:
            self.want_blank = True
        else:
            # a lone <br> after a div that ended its own line (div, br, div) is an empty line in a mail client: a paragraph break
            if self.out:
                self.want_blank = True
            self.after_br = True


def _neutralise(line):
    """'<' before a letter, '/', '!' or '?' becomes U+2039, so a decoded entity is never read as a tag on a second pass."""
    parts = line.split("<")
    out = [parts[0]]
    for part in parts[1:]:
        if part[:1].isalpha() or part[:1] in ("/", "!", "?"):
            out.append("‹" + part)
        else:
            out.append("<" + part)
    return "".join(out)


def _is_layout(table):
    return table.has_table or table.ncells <= 1 or table.multi


def _render_kids(node, em):
    for kid in node.kids:
        if isinstance(kid, str):
            _render_text(kid, em)
        else:
            _render(kid, em)


def _render_text(s, em):
    if em.pre:
        pieces = s.split("\n")
        for i, piece in enumerate(pieces):
            if i:
                em.line_break()
            em.text(piece)
    else:
        em.text(s.replace("\n", " "))


def _cell_lines(cell):
    """One cell of a data table as its lines (more than one when the cell holds a br or a block)."""
    if cell.hidden:
        return []
    sub = _Emit()
    sub.nobreak = 1
    _render_kids(cell, sub)
    sub.line_break()
    return [x for x in sub.out if x]


def _render_row(row, em):
    """A data table's row as ONE line, cells joined by ' | ' (a label and its value, or a header row, stay on one line).
    A row with a cell of two or more lines (label br value) keeps one line per cell line, as before."""
    cells = []
    multi = False
    extra = []
    for cell in row.kids:
        if isinstance(cell, str):
            if cell.strip():
                cells.append(" ".join(cell.split()))
        elif cell.tag in CELLS:
            ls = _cell_lines(cell)
            if len(ls) > 1:
                multi = True
            cells.extend(ls)
        else:
            extra.append(cell)
    em.line_break()
    if multi:
        for c in cells:
            em.text(c)
            em.line_break()
    elif cells:
        em.text(" | ".join(cells))
        em.line_break()
    for node in extra:
        _render(node, em)


def _render_table(table, em):
    em.block_break()
    layout = _is_layout(table)
    if not layout:
        em.nobreak += 1
    for child in table.kids:
        if isinstance(child, str):
            em.line_break()
            em.text(child)
            em.line_break()
        elif child.tag == "tr":
            if layout:
                _row_break(em, layout)
                for cell in child.kids:
                    if isinstance(cell, str):
                        em.line_break()
                        em.text(cell)
                        em.line_break()
                    elif cell.tag in CELLS:
                        _render_cell(cell, em, layout)
                    else:
                        _render(cell, em)
            else:
                _render_row(child, em)
        elif child.tag in CELLS:
            _row_break(em, layout)
            _render_cell(child, em, layout)
        else:
            _render(child, em)
    if not layout:
        em.nobreak -= 1
    em.block_break()


def _row_break(em, layout):
    if layout:
        em.block_break()
    else:
        em.line_break()


def _render_cell(cell, em, layout):
    if cell.hidden:
        return
    if layout:
        em.block_break()
    else:
        em.line_break()
    _render_kids(cell, em)
    if layout:
        em.block_break()
    else:
        em.line_break()


def _render(node, em):
    tag = node.tag
    if node.hidden:
        return
    if tag == "br":
        em.br()
    elif tag == "hr":
        em.block_break()
        em.add(DIVIDER)
        em.want_blank = not em.nobreak
    elif tag in INLINE:
        _render_kids(node, em)
    elif tag == "table":
        _render_table(node, em)
    elif tag in ("tr",) or tag in CELLS:
        em.line_break()
        _render_kids(node, em)
        em.line_break()
    elif tag in BLOCK:
        em.block_break()
        if tag in LISTS:
            em.nobreak += 1
        if tag == "pre":
            em.pre += 1
        _render_kids(node, em)
        if tag == "pre":
            em.pre -= 1
        if tag in LISTS:
            em.nobreak -= 1
        em.block_break()
    else:
        em.line_break()
        _render_kids(node, em)
        em.line_break()


def _html_lines(text):
    try:
        builder = _Builder()
        builder.feed(text)
        root = builder.finish()
        em = _Emit()
        _render_kids(root, em)
        em.line_break()
        return em.out
    except Exception:
        # last resort for input the parser cannot read: drop everything between < and >, then treat as text
        return _plain_lines(_strip_tags(text))


def _strip_tags(text):
    out = []
    depth_in = False
    for ch in text:
        if ch == "<":
            depth_in = True
            out.append("\n")
        elif ch == ">" and depth_in:
            depth_in = False
        elif not depth_in:
            out.append(ch)
    return "".join(out)


def _plain_lines(text):
    for nl in NEWLINES:
        text = text.replace(nl, "\n")
    out = []
    for raw in text.split("\n"):
        line = raw.translate(CONTROL).strip()
        if line:
            out.append(line)
        elif out and out[-1] != "":
            out.append("")
    while out and out[-1] == "":
        out.pop()
    return out


def to_lines(html_or_text):
    """Text lines with the block structure kept (see the module docstring). Never raises; None or '' gives []."""
    if not html_or_text or not isinstance(html_or_text, str):
        return []
    text = html_or_text[:MAX_INPUT]
    if looks_like_html(text):
        lines = _html_lines(text)
        # one more pass of the plain rules guarantees the output rules whatever the tree gave (and is idempotent)
        return _plain_lines("\n".join(lines))
    return _plain_lines(text)


def blocks(html_or_text):
    """The same lines as a list of blocks (lists of consecutive non-blank lines)."""
    out = []
    cur = []
    for line in to_lines(html_or_text):
        if line:
            cur.append(line)
        elif cur:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out
