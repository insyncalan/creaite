"""#290, plain words step 2: the guard over user-visible text. A ratchet that only falls.

dev/PLAIN-WORDS.md (step 1, #289) lists the words, path patterns and names a user must never see. This test reads the
strings a user can see and checks each one against that list:

  - the dashboard: every string in the built page's script (system/templates/dashboard.html, one module per
    `// src/...` marker, the vendored libraries skipped) and the text and visible attributes of its shell, with HTML tags
    taken out of a string first (a class name or an id is code, not words);
  - the Help: system/templates/help.md (all but its first comment) and system/templates/help/whats-new.md;
  - the Python messages that reach the dashboard: string values under a message key (`message`, `error`, `problem`,
    `why`…) in a dict or a call or assigned to a variable of that name, `("problem", "…")` pairs, the message of a
    `raise`, and `print` in the scripts whose output the dashboard shows (PRINT_FILES).

Code identifiers, comments, logs, keys, class lists, selectors and addresses are skipped. What's left is a candidate:
a string with two or more words, or one that starts with a capital letter.

The record of today's offenders is dev/tests/plain_words_baseline.json. Each offender is the file, the rule and a
fingerprint of the string (whitespace collapsed), with a count. The test fails when:
  - a string breaks a rule and isn't in the baseline (a NEW offender), or a known one appears more often; or
  - a baseline offender has gone (fixed or reworded): take it out of the baseline so the count can't climb back.
A rule whose severity is "warn" (tracker, until #292 lands Tier 2) reports both kinds and never fails.

Allow-lists live in the same file and are by file or by identifier only, never by word, so a visible string that says
"stage", "valid" or "refused" still fails anywhere else:
  - allow.files: a whole source file (Settings › Diagnostics' own code, doctor.py's health check);
  - allow.identifiers: one function (`settings.js#diagCardHtml`, `live_server.py#some_function`) or one Help section
    (`help.md#Troubleshooting`).

Update the baseline after fixing offenders (or, rarely and on purpose, to accept new ones):
    CREAITE_UPDATE_PLAIN_BASELINE=1 python3 dev/tests/test_plain_words.py
It rewrites only "offenders" and keeps "severity" and "allow" as they are.

Run: python3 dev/tests/test_plain_words.py
"""
import ast
import hashlib
import html.parser
import json
import os
import re
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "dev" / "tests" / "plain_words_baseline.json"
DASHBOARD = ROOT / "system" / "templates" / "dashboard.html"
SHELL = ROOT / "system" / "templates" / "dashboard" / "shell.html"
CSS = ROOT / "system" / "templates" / "dashboard" / "style.css"
HELP = [ROOT / "system" / "templates" / "help.md", ROOT / "system" / "templates" / "help" / "whats-new.md"]
SCRIPTS = ROOT / "system" / "scripts"
UPDATE_ENV = "CREAITE_UPDATE_PLAIN_BASELINE"

# The banned list (dev/PLAIN-WORDS.md, "Banned in user-visible text"). Rule name -> pattern, matched without case.
RULES = {
    "sweep": r"\bsw(?:eep|eeps|ept|eeping)\b",
    "proposal": r"\bpropos(?:al|als|ed)\b",
    "stage": r"\bstag(?:e|ed|es|ing)\b",
    "apply": r"\bappl(?:y|ies|ied|ying)\b",
    "vault": r"\bvaults?\b",
    "live server": r"\blive server\b",
    "extract": r"\b(?:re-)?extract(?:s|ed|ing|ion|ions)?\b",
    "refused": r"\brefus(?:e|es|ed)\b",
    "unknown field": r"\bunknown fields?\b",
    "valid": r"\b(?:in)?valid\b",
    "tracker": r"\btrackers?\b",
    "path": r"(?<![\w.])(?:system|projects|inbox)/|\.claude/|_portfolio\b|\.(?:jsonl?|db|vtt)\b",
    "script": r"\b\w+\.py\b|\bpython3?\b",
    "cx- name": r"\bcx-[a-z]+",
}
PATTERNS = {name: re.compile(p, re.I) for name, p in RULES.items()}

# Python: where a string reaches the dashboard.
MESSAGE_KEYS = {"message", "error", "problem", "problems", "why", "reason", "title", "text", "line", "lines", "label",
                "hint", "summary", "detail", "note", "say", "warning", "warnings", "msg", "body", "tip"}
PRINT_FILES = {"session.py", "tracker.py"}       # printed lines the dashboard or Claude shows the user as they are
# JS: strings that are code, by the call they are passed to or the key/attribute they are the value of.
CODE_CALLS = {"querySelector", "querySelectorAll", "$", "$$", "closest", "matches", "getElementById", "api", "fetch",
              "addEventListener", "removeEventListener", "add", "remove", "toggle", "contains", "setAttribute",
              "getAttribute", "removeAttribute", "hasAttribute", "RegExp", "log", "warn", "error", "debug", "info",
              "dlog", "startsWith", "endsWith", "includes", "indexOf", "split", "replace", "go", "openPath",
              "createElement", "dispatchEvent", "Event", "CustomEvent", "postMessage", "getItem", "setItem",
              "removeItem", "require", "import"}
CODE_KEYS = {"kw", "className", "class", "cls", "id", "key", "href", "src", "type", "name", "sel", "q", "route", "url",
             "path", "icon", "cat", "sec", "mode", "kind", "area", "op", "field", "for", "htmlFor", "role", "rel",
             "target", "method", "event", "store", "slot", "ref", "data", "accept", "pattern", "inputMode", "tag",
             "style", "fill", "stroke", "viewBox", "d", "transform", "points", "xmlns"}
VISIBLE_ATTRS = {"title", "aria-label", "placeholder", "alt", "aria-description", "data-tip", "label"}


def fingerprint(text):
    """A short stable id for a string: whitespace collapsed, then SHA-1."""
    return hashlib.sha1(" ".join(text.split()).encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------------------------------------------------------- JS
REGEX_BEFORE = set("(,=:[!&|?{};+-*%<>~^") | {""}
REGEX_WORDS = {"return", "typeof", "case", "in", "of", "delete", "void", "throw", "new", "else", "do", "instanceof"}


def js_strings(src):
    """Every string literal in JavaScript `src` as (text, offset); a template's parts are joined with {} and the strings
    inside its ${…} are returned on their own. Comments and regular expressions are skipped."""
    out = []
    _lex(src, 0, len(src), out, stop_at_brace=False)
    return out


def _prev_sig(src, i):
    j = i - 1
    while j >= 0 and src[j] in " \t\r\n":
        j -= 1
    if j < 0:
        return ""
    if src[j].isalnum() or src[j] in "_$":
        k = j
        while k >= 0 and (src[k].isalnum() or src[k] in "_$"):
            k -= 1
        word = src[k + 1:j + 1]
        return word if word in REGEX_WORDS else "a"
    return src[j]


def _skip_slash(src, i, n):
    """Past the comment or regular expression that starts with the / at i; i + 1 for a division."""
    if src.startswith("//", i):
        j = src.find("\n", i)
        return n if j < 0 else j
    if src.startswith("/*", i):
        j = src.find("*/", i + 2)
        return n if j < 0 else j + 2
    p = _prev_sig(src, i)
    return _skip_regex(src, i + 1, n) if (p in REGEX_BEFORE or p in REGEX_WORDS) else i + 1


def _lex(src, i, n, out, stop_at_brace):
    """Lex src[i:n]; with stop_at_brace, stop at the `}` that closes a template's ${ and return its index."""
    depth = 0
    while i < n:
        c = src[i]
        if c == "/":
            i = _skip_slash(src, i, n)
        elif c in "'\"":
            j, text = _quoted(src, i, c, n)
            out.append((text, i))
            i = j
        elif c == "`":
            i = _template(src, i, n, out)
        elif c == "}" and stop_at_brace and depth == 0:
            return i
        else:
            depth += {"{": 1, "}": -1}.get(c, 0)
            i += 1
    return n


def _skip_regex(src, i, n):
    in_class = False
    while i < n:
        c = src[i]
        if c == "\\":
            i += 2
            continue
        if c == "\n":
            return i
        if in_class:
            in_class = c != "]"
        elif c == "[":
            in_class = True
        elif c == "/":
            return i + 1
        i += 1
    return n


def _unescape(raw):
    try:
        return json.loads('"' + raw.replace('"', '\\"').replace("\\'", "'").replace("\\`", "`").replace("\\$", "$") + '"')
    except ValueError:
        return raw


def _quoted(src, i, q, n):
    j = i + 1
    while j < n and src[j] != q:
        if src[j] == "\\":
            j += 1
        elif src[j] == "\n":
            break
        j += 1
    return j + 1, _unescape(src[i + 1:j])


def _template(src, i, n, out):
    parts, j, start = [], i + 1, i + 1
    while j < n:
        c = src[j]
        if c == "\\":
            j += 2
            continue
        if c == "`":
            parts.append(src[start:j])
            out.append(("{}".join(_unescape(p) for p in parts), i))
            return j + 1
        if c == "$" and src.startswith("${", j):
            parts.append(src[start:j])
            j = _lex(src, j + 2, n, out, stop_at_brace=True) + 1
            start = j
            continue
        j += 1
    return n


class _Visible(html.parser.HTMLParser):
    """The text a reader sees in a piece of HTML: text outside script and style, plus the visible attributes."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.bits, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        for k, v in attrs:
            if k in VISIBLE_ATTRS and v:
                self.bits.append(v)

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.bits.append(data)


def visible_html(text):
    """`text` with its HTML tags taken out (their visible attributes kept); plain text comes back as it is."""
    if "<" not in text or not re.search(r"<[a-zA-Z/!]", text):
        return [text]
    p = _Visible()
    try:
        p.feed(text)
        p.close()
    except Exception:                                    # a broken fragment: fall back to stripping tags by hand
        return [re.sub(r"<[^>]*>", " ", text)]
    return p.bits


def css_classes():
    """Every class name style.css defines: a lower-case string made only of these is a class list, not words."""
    return set(re.findall(r"\.([a-zA-Z][\w-]*)", CSS.read_text(encoding="utf-8")))


WORDS = re.compile(r"[A-Za-z][A-Za-z'’-]*")


def is_candidate(text, classes):
    """True for a string a person could read: two or more words, or one capitalised word."""
    t = text.replace("{}", " ").strip()
    if not t or not re.search(r"[A-Za-z]", t):
        return False
    if re.match(r"^(?:/api/|https?:|#|\.|data:|mailto:)", t):
        return False
    tokens = t.split()
    if len(tokens) == 1:
        return bool(re.match(r"^[A-Z][a-z]", t)) and not re.search(r"[._/]\w", t)
    if all(re.fullmatch(r"[a-z0-9_-]+", tok) for tok in tokens) and all(tok in classes for tok in tokens):
        return False
    if re.search(r"[\[\]>]", t) and re.fullmatch(r"[\w\s.#\[\]=\"':>*~+(),-]+", t) and not re.search(r"\s[a-z]{3,}\s", t):
        return False                                     # a CSS selector
    return len(WORDS.findall(t)) >= 2


def _context_is_code(src, at):
    """True when the string at `at` is passed to a code call or is the value of a code key or attribute."""
    before = src[max(0, at - 60):at]
    m = re.search(r"([\w$.-]+)\s*\(\s*(?:[^()]*,\s*)?$", before)
    if m and m.group(1).split(".")[-1] in CODE_CALLS:
        return True
    m = re.search(r"([\w$-]+)\s*[:=]\s*$", before)
    if m and (m.group(1) in CODE_KEYS or m.group(1).startswith(("data-", "on"))):
        return True
    return bool(re.search(r"(?:===?|!==?)\s*$", before))


TOP = re.compile(r"^  (?:async )?function\*? ?([\w$]+)|^  (?:var|let|const) ([\w$]+)", re.M)


def _ident_at(tops, at):
    """The top-level name (function or variable) declared last before offset `at`."""
    ident = ""
    for pos, nm in tops:
        if pos > at:
            break
        ident = nm
    return ident


def _module_strings(name, body, classes):
    """(module, identifier, text) for the visible strings in one bundled module."""
    tops = [(t.start(), t.group(1) or t.group(2)) for t in TOP.finditer(body)]
    found = []
    for text, at in js_strings(body):
        if not _context_is_code(body, at):
            found += [(name, _ident_at(tops, at), bit) for bit in visible_html(text) if is_candidate(bit, classes)]
    return found


def dashboard_strings(classes):
    """(file, identifier, text) for every visible string in the built dashboard and its shell."""
    page = DASHBOARD.read_text(encoding="utf-8")
    found = []
    for script in re.findall(r"<script[^>]*>(.*?)</script>", page, re.S):
        marks = list(re.finditer(r"^  // (\S+\.jsx?)$", script, re.M))
        for k, m in enumerate(marks):
            if "vendor/" in m.group(1) or "node_modules" in m.group(1):
                continue
            body = script[m.end():marks[k + 1].start() if k + 1 < len(marks) else len(script)]
            found += _module_strings(m.group(1), body, classes)
    p = _Visible()
    p.feed(re.sub(r"<!--.*?-->", " ", SHELL.read_text(encoding="utf-8"), flags=re.S))
    found += [("shell.html", "", b) for b in p.bits if is_candidate(b, classes)]
    return found


# -------------------------------------------------------------------------------------------------------------- Help
def help_strings():
    """(file, section title, line) for every line of the Help a reader sees."""
    found = []
    for f in HELP:
        text = f.read_text(encoding="utf-8")
        if f.name == "help.md":
            text = re.sub(r"\A\s*<!--.*?-->", "", text, flags=re.S)
        section = ""
        for line in text.splitlines():
            if line.startswith("#"):
                section = line.lstrip("#").strip()
            if not line.strip() or line.startswith(("Screen:", "Jobs:")) or re.fullmatch(r"\s*-{3,}\s*", line):
                continue
            found.append((f.name, section, line.strip()))
    return found


# ------------------------------------------------------------------------------------------------------------ Python
def _binop_parts(node):
    left, right = _str_parts(node.left), _str_parts(node.right)
    if left and right and isinstance(node.op, ast.Add):
        return [left[0] + "{}" + right[0]] + left[1:] + right[1:]
    return left + right


def _call_parts(node):
    f = node.func
    if not (isinstance(f, ast.Attribute) and f.attr in ("join", "format")):
        return []
    base = _str_parts(f.value) if f.attr == "format" else []
    return base + [s for a in node.args for s in _str_parts(a)]


_PARTS = {
    ast.Constant: lambda n: [n.value] if isinstance(n.value, str) else [],
    ast.JoinedStr: lambda n: ["".join(v.value if isinstance(v, ast.Constant) else "{}" for v in n.values)],
    ast.BinOp: lambda n: _binop_parts(n) if isinstance(n.op, (ast.Add, ast.Mod)) else [],
    ast.IfExp: lambda n: _str_parts(n.body) + _str_parts(n.orelse),
    ast.List: lambda n: [s for e in n.elts for s in _str_parts(e)],
    ast.Tuple: lambda n: [s for e in n.elts for s in _str_parts(e)],
    ast.Call: _call_parts,
}


def _str_parts(node):
    """The literal text of a string expression: a constant, an f-string (holes as {}), + or % of them, a list of them,
    either side of a conditional, or a join or format of them."""
    fn = _PARTS.get(type(node))
    return fn(node) if fn else []


def _owners(tree):
    """{id(node): the name of the innermost function holding it}."""
    owner = {}
    # The innermost function wins: walk functions outermost first and overwrite.
    for fn in sorted((f for f in ast.walk(tree) if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))),
                     key=lambda f: (f.lineno, -(f.end_lineno or f.lineno))):
        for sub in ast.walk(fn):
            owner[id(sub)] = fn.name
    return owner


def _from_dict(node, fname):
    return [v for k, v in zip(node.keys, node.values) if isinstance(k, ast.Constant) and k.value in MESSAGE_KEYS]


def _from_call(node, fname):
    out = [kw.value for kw in node.keywords if kw.arg in MESSAGE_KEYS]
    if isinstance(node.func, ast.Name) and node.func.id == "print" and fname in PRINT_FILES:
        out += node.args
    return out


def _from_assign(node, fname):                           # msg = f"…", later returned or raised
    return [node.value] if any(isinstance(t, ast.Name) and t.id in MESSAGE_KEYS for t in node.targets) else []


def _from_raise(node, fname):
    return node.exc.args[:1] if isinstance(node.exc, ast.Call) else []


def _from_tuple(node, fname):                            # ("problem", "…")
    e = node.elts
    ok = len(e) == 2 and isinstance(e[0], ast.Constant) and e[0].value in ("problem", "note", "error", "refused")
    return [e[1]] if ok else []


_MESSAGES = {ast.Dict: _from_dict, ast.Call: _from_call, ast.Assign: _from_assign, ast.Raise: _from_raise,
             ast.Tuple: _from_tuple}


def _message_nodes(tree, fname):
    """(node, function name) for every expression in `tree` whose text goes to the dashboard."""
    owner = _owners(tree)
    out = []
    for node in ast.walk(tree):
        fn = _MESSAGES.get(type(node))
        if fn:
            out += fn(node, fname)
    return [(n, owner.get(id(n), "")) for n in out]


def python_strings(classes):
    """(file, function, text) for every message string in system/scripts that can reach the dashboard."""
    found = []
    for f in sorted(SCRIPTS.glob("*.py")):
        tree = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
        for node, fn in _message_nodes(tree, f.name):
            for text in _str_parts(node):
                if is_candidate(text, classes):
                    found.append((f.name, fn, text))
    return found


# -------------------------------------------------------------------------------------------------------- The scan
def load_baseline():
    return json.loads(BASELINE.read_text(encoding="utf-8"))


def scan(data=None):
    """{"file | rule | fingerprint": {"count": n, "text": first 100 characters}} for every string that breaks a rule,
    the allow-lists applied."""
    data = data or load_baseline()
    allow_files = set(data.get("allow", {}).get("files", {}))
    allow_ids = set(data.get("allow", {}).get("identifiers", {}))
    classes = css_classes()
    hits = {}
    for fname, ident, text in dashboard_strings(classes) + help_strings() + python_strings(classes):
        if fname in allow_files or (ident and f"{fname}#{ident}" in allow_ids):
            continue
        fp = fingerprint(text)
        for rule, pat in PATTERNS.items():
            if pat.search(text):
                key = f"{fname} | {rule} | {fp}"
                h = hits.setdefault(key, {"count": 0, "text": " ".join(text.split())[:100]})
                h["count"] += 1
    return hits


def rule_of(key):
    return key.split(" | ")[1]


def compare(found, data):
    """(failures, warnings): each a list of lines, new offenders and stale baseline entries, by the rule's severity."""
    base = data.get("offenders", {})
    severity = data.get("severity", {})
    fails, warns = [], []
    for key in sorted(set(found) | set(base)):
        now, was = found.get(key, {}).get("count", 0), base.get(key, {}).get("count", 0)
        if now == was:
            continue
        text = (found.get(key) or base.get(key))["text"]
        if now > was:
            line = f"NEW   {key} ({was} -> {now}): {text}"
        else:
            line = f"GONE  {key} ({was} -> {now}): fixed? take it out of the baseline ({UPDATE_ENV}=1): {text}"
        (warns if severity.get(rule_of(key), "fail") == "warn" else fails).append(line)
    return fails, warns


def counts(found):
    c = Counter()
    for key, v in found.items():
        c[rule_of(key)] += v["count"]
    return c


def report(found, data):
    severity = data.get("severity", {})
    c = counts(found)
    lines = ["Plain words: offenders per rule (the baseline may only fall)"]
    for rule in RULES:
        if c[rule]:
            lines.append(f"  {rule:<14} {c[rule]:>5}{'  (warn)' if severity.get(rule) == 'warn' else ''}")
    fail_total = sum(n for r, n in c.items() if severity.get(r, "fail") != "warn")
    lines.append(f"  {'total':<14} {sum(c.values()):>5}  ({fail_total} that fail, {sum(c.values()) - fail_total} warn)")
    return "\n".join(lines)


def update_baseline(found):
    data = load_baseline()
    data["offenders"] = {k: found[k] for k in sorted(found)}
    BASELINE.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


class PlainWords(unittest.TestCase):
    """New offenders fail; fixed offenders still in the baseline fail; warn-only rules print."""

    def test_allow_lists_name_files_or_identifiers_never_words(self):
        data = load_baseline()
        for f in data["allow"].get("files", {}):
            self.assertRegex(f, r"^[\w./-]+\.(?:py|jsx?|md|html)$", f"allow.files must name a file: {f!r}")
        for i in data["allow"].get("identifiers", {}):
            self.assertRegex(i, r"^[\w./-]+\.(?:py|jsx?|md|html)#.+$", f"allow.identifiers must be file#name: {i!r}")
        for rule in data.get("severity", {}):
            self.assertIn(rule, RULES, f"severity names an unknown rule: {rule!r}")
            self.assertIn(data["severity"][rule], ("warn", "fail"))

    def test_the_lexer_finds_text_not_code(self):
        src = ('  // components/x.jsx\n  function card() {\n    const a = 1 / 2; const re = /sweep "x"/g;\n'
               '    // Run sweep in a comment\n    $(".sweep-row");\n'
               '    return `<div class="sweepdue">Run the ${n} sweep now</div>` + "Staged for review";\n  }\n')
        texts = [t for t, at in js_strings(src) if not _context_is_code(src, at)]
        self.assertIn('<div class="sweepdue">Run the {} sweep now</div>', texts)
        self.assertIn("Staged for review", texts)
        self.assertNotIn(".sweep-row", texts)
        self.assertFalse(any("comment" in t or '"x"' in t for t in texts))
        self.assertEqual(visible_html('<div class="sweepdue" title="Sweep due">Run the {} sweep</div>'),
                         ["Sweep due", "Run the {} sweep"])

    def test_the_ratchet(self):
        data = load_baseline()
        found = scan(data)
        if os.environ.get(UPDATE_ENV) == "1":
            update_baseline(found)
            print(f"Baseline rewritten: {BASELINE.relative_to(ROOT)}")
            data = load_baseline()
        print("\n" + report(found, data))
        fails, warns = compare(found, data)
        if warns:
            print(f"\nWarnings ({len(warns)}, not failures: severity warn):")
            print("\n".join("  " + w for w in warns[:40]) + ("\n  …" if len(warns) > 40 else ""))
        self.assertFalse(fails, "\nPlain words (dev/PLAIN-WORDS.md): use the agreed words, or, once an offender is "
                         f"fixed, rewrite the baseline with {UPDATE_ENV}=1.\n" + "\n".join(fails[:60])
                         + (f"\n… and {len(fails) - 60} more" if len(fails) > 60 else ""))


if __name__ == "__main__":
    unittest.main(argv=sys.argv[:1] + sys.argv[1:], verbosity=1)
