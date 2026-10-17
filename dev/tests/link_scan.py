"""#159: a source-level scan for every place the dashboard's code writes an address that can be opened (an `href`, `window.open`,
`location`), used by test_link_renderers.NoBypass. No browser. Not a test itself.

What it does, in order:
1. `strip_comments(text)`: removes // and /* */ comments (and so JSX `{/* */}` comments), leaving strings, templates and regular
   expressions whole, so prose in a comment can neither hide an offender nor vouch for one.
2. `sinks(text)`: finds each place an address is written, in every form the dashboard's code uses or could use:
   `href="…"`, `href='…'`, `href=…` (unquoted), `href={…}` (JSX), `{ href: … }` (an object, as in h("a", { href: … })),
   `x.href = …`, `setAttribute("href", …)`, `window.open(…)` and `location = …`, `location.href = …`, `location.assign(…)`.
   Each comes with the expression that SUPPLIES the address (the quoted text with its `${…}` parts, the braces, or the right-hand side).
3. `offenders_in(text, name, allow)`: a sink is fine when its value starts with "#" (an address inside the page), or when the value
   expression itself calls a validator (`linkUrl(`, `linkAnchor(`, `sourceHref(`, `mailLink(`, `typedLinkUrl(`): a validator named
   elsewhere on the line, or in a comment, does not count. Anything else must be in `allow`, a list of
   (file ending, exact value expression, how many times, reason), and each entry must match exactly that many sinks.
"""
import re

VALIDATORS = re.compile(r"(?<![\w$.])(?:linkUrl|linkAnchor|sourceHref|mailLink|typedLinkUrl)\s*\(")
KEYWORDS_BEFORE_REGEX = ("return", "typeof", "case", "in", "of", "delete", "void", "throw", "yield", "await", "else", "do")
REGEX_AFTER = set("(,=:[!&|?{};+-*%<>~^")


def _skip_string(s, i):
    """The index just after the string or template literal that starts at s[i] (a quote, double quote or back-tick)."""
    q, j, n = s[i], i + 1, len(s)
    while j < n:
        c = s[j]
        if c == "\\":
            j += 2
            continue
        if c == q:
            return j + 1
        if q == "`" and s[j:j + 2] == "${":
            j = _skip_group(s, j + 1)
            continue
        if q != "`" and c == "\n":
            return j
        j += 1
    return n


def _skip_group(s, i):
    """The index just after the bracket group that starts at s[i] ('(' '[' or '{'), skipping strings inside it."""
    depth, j, n = 0, i, len(s)
    while j < n:
        c = s[j]
        if c in "'\"`":
            if c == "'" and j > 0 and (s[j - 1].isalnum() or s[j - 1] == "_"):
                j += 1
                continue
            j = _skip_string(s, j)
            continue
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
            if depth == 0:
                return j + 1
        j += 1
    return n


def _apostrophe(s, i):
    """Whether the quote at s[i] is an apostrophe in a word (JSX text: "Alan's"), not the start of a string."""
    return s[i] == "'" and i > 0 and (s[i - 1].isalnum() or s[i - 1] == "_")


def _regex_end(s, i):
    """The index just after the regular expression literal (and its flags) that starts at s[i]."""
    j, cls, n = i + 1, False, len(s)
    while j < n and s[j] != "\n" and (cls or s[j] != "/"):
        if s[j] == "\\":
            j += 1
        elif s[j] in "[]":
            cls = s[j] == "["
        j += 1
    j += 1
    while j < n and s[j].isalpha():
        j += 1
    return j


class _Stripper:
    """Walks the code once, copying everything but comments into `out`."""

    def __init__(self, s):
        self.s, self.n, self.out = s, len(s), []

    def comment(self, i):
        """Skips the comment at i (// or /*); a block comment leaves its newlines so line numbers stay true. None if not a comment."""
        s = self.s
        if s[i:i + 2] == "//":
            j = s.find("\n", i)
            return self.n if j < 0 else j
        if s[i:i + 2] == "/*":
            j = s.find("*/", i + 2)
            j = self.n if j < 0 else j + 2
            self.out.append(" " + "\n" * s.count("\n", i, j))
            return j
        return None

    def regex_starts(self, last):
        """Whether a '/' here starts a regular expression (it follows an operator, a bracket or a keyword) rather than dividing."""
        word = re.search(r"([A-Za-z]+)$", "".join(self.out[-12:]))
        return not last or last in REGEX_AFTER or bool(word and word.group(1) in KEYWORDS_BEFORE_REGEX)

    def code(self, i, in_expr):
        """Copies code from i; inside a template's ${…} it stops at the closing brace and returns its index."""
        s, depth, last = self.s, 0, ""
        while i < self.n:
            c = s[i]
            j = self.comment(i)
            if j is not None:
                i = j
                continue
            if (c in "'\"" and not _apostrophe(s, i)) or c == "`":
                j = self.template(i) if c == "`" else _skip_string(s, i)
                if c != "`":
                    self.out.append(s[i:j])
                i, last = j, "s"
                continue
            if c == "/" and self.regex_starts(last):
                j = _regex_end(s, i)
                self.out.append(s[i:j])
                i, last = j, "r"
                continue
            depth += (c == "{") - (c == "}")
            if c == "}" and in_expr and depth < 0:
                return i
            self.out.append(c)
            last = last if c.isspace() else c
            i += 1
        return i

    def template(self, i):
        """Copies the template literal at i, its ${…} parts as code (so comments in them go); returns the index after it."""
        s, out = self.s, self.out
        out.append("`")
        i += 1
        while i < self.n:
            c = s[i]
            if c == "`":
                out.append("`")
                return i + 1
            if s[i:i + 2] == "${":
                out.append("${")
                i = self.code(i + 2, True)
                out.append("}")
            else:
                out.append(s[i:i + 2] if c == "\\" else c)
                i += 2 if c == "\\" else 1
                continue
            i += 1
        return i


def strip_comments(s):
    """`s` without // and /* */ comments. Strings, templates (with their ${…} code) and regular expressions are kept whole."""
    w = _Stripper(s)
    w.code(0, False)
    return "".join(w.out)


SINK = re.compile(r"""(?P<attr>(?<![\w$-])href['"`]?\s*(?P<op>[=:])(?![=>:]))|(?P<set>\bsetAttribute\(\s*['"`]href['"`]\s*,)|"""
                  r"""(?P<open>\b(?:window|globalThis|self|top|parent)\.open\()|(?P<loc>\b(?:window\.)?location\.(?:assign|replace)\()|"""
                  r"""(?P<locset>\b(?:window\.)?location(?:\.href)?\s*=(?![=>]))""")


def _expr_to(s, i, stops):
    """The expression that starts at s[i], up to a stop character outside any string or bracket."""
    j, n = i, len(s)
    while j < n:
        c = s[j]
        if c in "'\"`":
            j = _skip_string(s, j)
            continue
        if c in "([{":
            j = _skip_group(s, j)
            continue
        if c in stops or c in ")]}":
            break
        j += 1
    return s[i:j]


def _unquoted(s, i):
    """An unquoted attribute value that starts at s[i]: up to a space or the end of the tag."""
    j = i
    while j < len(s) and not s[j].isspace() and s[j] != ">":
        j = _skip_group(s, j) if s[j] in "([{" else j + 1
    return s[i:j]


def _attr_value(s, m):
    """(kind, value) for an `href` sink m, or None when it is not an address being written (a variable, a ternary, a comparison)."""
    before = s[:m.start()].rstrip("'\"` ").rstrip()          # what comes before the word, quote and spaces aside
    if re.search(r"\b(?:const|let|var)$", before):
        return None                                            # `const href = …` declares a variable
    op, i = m.group("op"), m.end()
    spaced = s[i - 2:i - 1].isspace() or s[i:i + 1].isspace()
    while i < len(s) and s[i] in " \t":
        i += 1
    if op == ":":                                              # `{ href: x }` and `, href: x`; not a ternary's `? href : y`
        return ("expr", _expr_to(s, i, ",;\n")) if before[-1:] in ("{", ",") else None
    i += s[i:i + 1] == "\\"                                    # href=\"#\" inside an escaped string
    c = s[i:i + 1]
    if c in ("'", '"'):
        return ("attr", _quoted(s, i))
    if c == "{":
        return ("jsx", s[i + 1:_skip_group(s, i) - 1])
    if s[i:i + 2] == "${":
        return ("attr", s[i:_skip_group(s, i + 1)])
    if before[-1:] == ".":                                     # `a.href = x`
        return ("expr", _expr_to(s, i, ";\n"))
    if not spaced:                                             # `<a href=${x}>`, `<a href=x>`: an unquoted attribute
        return ("attr", _unquoted(s, i))
    return None                                                # a variable called href being assigned: not an address being written


def sinks(text):
    """[(kind, value expression, line number)] for every place the code writes an address that can be opened, comments ignored."""
    s = strip_comments(text)
    found = []
    for m in SINK.finditer(s):
        line, i = s.count("\n", 0, m.start()) + 1, m.end()
        if m.group("attr"):
            r = _attr_value(s, m)
        elif m.group("set"):
            r = ("expr", _expr_to(s, i, ""))
        elif m.group("open") or m.group("loc"):
            r = ("expr", _expr_to(s, i, ",)"))
        else:
            r = ("expr", _expr_to(s, i, ";\n"))
        if r:
            found.append((r[0], r[1], line))
    return [(k, " ".join(v.split()), ln) for k, v, ln in found]


def _quoted(s, i):
    """The text of the quoted attribute value that starts at s[i] (the quote), `${…}` parts whole."""
    q, j = s[i], i + 1
    while j < len(s) and s[j] != q:
        if s[j] == "\\":
            j += 2
        elif s[j:j + 2] == "${":
            j = _skip_group(s, j + 1)
        else:
            j += 1
    return s[i + 1:j]


def vouched(kind, value):
    """Whether a sink's value is safe by itself: an address inside the page ("#…"), or built by a validator."""
    v = value.strip().strip("\"'`").strip()
    return v.startswith("#") or bool(VALIDATORS.search(value))


def offenders_in(text, name, allow=(), used=None):
    """Messages for the sinks in `text` that nothing vouches for. `allow` is [(file ending, exact value, count, reason)];
    `used` (a dict) counts how often each allowed entry was met."""
    used = {} if used is None else used
    bad = []
    for kind, value, line in sinks(text):
        if vouched(kind, value):
            continue
        key = next((a for a in allow if name.endswith(a[0]) and a[1] == value), None)
        if key is not None:
            used[key[:2]] = used.get(key[:2], 0) + 1
            if used[key[:2]] <= key[2]:
                continue
        bad.append(f"{name}:{line}: {kind} {value[:90]}")
    return bad
