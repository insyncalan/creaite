"""BL-231 step 1: the inventory of the dashboard's in-place function wrappers, before they are folded (development only).

Run: python3 dev/tools/wrappers.py [--file PATH] [--json PATH | --no-json] [--batch N] [--quiet]

Reads the inline app script of `system/templates/dashboard.html` and prints, for every function wrapped in place
(`const rb=renderBadge; renderBadge=function(){ … }`):
  - the chain in order: the first definition, then each wrapper, with line numbers in dashboard.html;
  - every **early reference**: a place that runs at load (not inside a function body) and takes the function as a value
    (`addEventListener("x", go)`, `const f = go`, `{go}`, `go.bind(…)`) or calls it, before its last wrapper is installed.
    That caller gets an intermediate version today ("sees 2 of 5": the original plus the first two wrappers); folding
    would silently give it the final one, so each is settled by hand before its chain is folded. References inside a
    function body run later, after every wrapper, and are not listed;
  - the matches `check.py` counts that are not wrappers (a value swapped, `const was=LIVE; LIVE=on`, or a function
    swapped inside a function body), so the two figures can be reconciled;
  - a batch plan: about `--batch` wrappers each (20), easiest chains first, with drawPanel, renderWork, renderCockpit
    and go last, each alone.
It writes the same as JSON to `dev/wrappers-inventory.json`. Standard library only; a small JavaScript tokenizer
(strings, templates, regular expressions, comments and brackets), not a parser: it refuses a script whose brackets
don't pair rather than guess.
"""
import argparse
import bisect
import json
import re
import sys
from pathlib import Path

import check

ROOT = Path(__file__).resolve().parents[2]
DASHBOARD = ROOT / "system" / "templates" / "dashboard.html"
INVENTORY = ROOT / "dev" / "wrappers-inventory.json"
SOLO_LAST = ("drawPanel", "renderWork", "renderCockpit", "go")    # BL-231: the hardest chains, one batch each, last
BATCH = 20

WORD = re.compile(r"[A-Za-z_$][\w$]*")
NUMBER = re.compile(r"(?:0[xXbBoO][\da-fA-F_]+|\d[\d_]*\.?[\d_]*(?:[eE][+-]?\d+)?|\.\d[\d_]*(?:[eE][+-]?\d+)?)n?")
PUNCT = re.compile(r">>>=|\.\.\.|===|!==|\*\*=|<<=|>>=|>>>|&&=|\|\|=|\?\?=|=>|\?\.(?!\d)|[-+*/%&|^!=<>]=|&&|\|\||\?\?"
                   r"|\+\+|--|<<|>>|\*\*|[{}()\[\];,.<>+\-*/%&|^!~?:=@#]")
SPACE = re.compile(r"(?:\s+|//[^\n]*|/\*.*?\*/)+", re.S)
SCRIPT = re.compile(r"<script([^>]*)>(.*?)</script>", re.S)
BLOCK = re.compile(r"/\*\s*=====\s*(.*?)\s*=====\s*\*/")
REGEX_AFTER = {"return", "typeof", "instanceof", "in", "of", "new", "delete", "void", "throw", "case", "do", "else",
               "yield", "await"}
CONTROL = {"if", "for", "while", "switch", "catch", "with", "await"}     # `kw(…){` opens a block, not a function body
STATEMENT = {"const", "let", "var", "function", "if", "for", "while", "return", "class", "try"}
CLOSE = {")": "(", "]": "[", "}": "{", "}$": "${"}


class Tok:
    """One token: kind (id, num, str, tmpl, re or p), its text and its offset in the script."""
    __slots__ = ("kind", "text", "pos")

    def __init__(self, kind, text, pos):
        self.kind, self.text, self.pos = kind, text, pos


# ---------- tokenizer ----------
def _string_end(js, i):
    """The offset just after the quoted string starting at `i`."""
    q, j = js[i], i + 1
    while js[j] != q:
        j += 2 if js[j] == "\\" else 1
    return j + 1


def _template(js, i, toks, braces):
    """Scan template text from `i` to its closing backtick or a `${`; add the tokens; return where scanning resumes."""
    j = i
    while True:
        c = js[j]
        if c == "\\":
            j += 2
        elif c == "`":
            toks.append(Tok("tmpl", js[i:j], i))
            return j + 1
        elif js.startswith("${", j):
            toks.append(Tok("tmpl", js[i:j], i))
            toks.append(Tok("p", "${", j))
            braces.append("t")
            return j + 2
        else:
            j += 1


def _regex_ok(toks):
    """Whether a `/` here starts a regular expression rather than a division."""
    if not toks:
        return True
    prev = toks[-1]
    if prev.kind == "id":
        return prev.text in REGEX_AFTER
    if prev.kind == "p":
        return prev.text not in (")", "]", "}", "}$", "++", "--")
    return False


def _regex_end(js, i):
    """The offset just after the regular expression literal (and its flags) starting at `i`."""
    j, in_class = i + 1, False
    while True:
        c = js[j]
        if c == "\\":
            j += 1
        elif c == "\n":
            raise ValueError(f"unterminated regular expression at offset {i}")
        elif c == "[":
            in_class = True
        elif c == "]":
            in_class = False
        elif c == "/" and not in_class:
            break
        j += 1
    j += 1
    while j < len(js) and (js[j].isalnum() or js[j] == "_"):
        j += 1
    return j


def _word_or_punct(js, i, toks, braces):
    """Add the identifier, number or punctuator at `i`; return the offset after it."""
    for kind, pat in (("id", WORD), ("num", NUMBER), ("p", PUNCT)):
        m = pat.match(js, i)
        if m:
            toks.append(Tok(kind, m.group(), i))
            if m.group() == "{":
                braces.append("b")
            elif m.group() == "}" and braces:
                braces.pop()
            return m.end()
    raise ValueError(f"unexpected character {js[i]!r} at offset {i}")


def lex(js):
    """The script's tokens, comments and whitespace left out."""
    toks, braces, i, n = [], [], 0, len(js)
    while True:
        m = SPACE.match(js, i)
        if m:
            i = m.end()
        if i >= n:
            return toks
        c = js[i]
        if c in "'\"":
            j = _string_end(js, i)
            toks.append(Tok("str", js[i:j], i))
            i = j
        elif c == "`":
            i = _template(js, i + 1, toks, braces)
        elif c == "}" and braces and braces[-1] == "t":
            braces.pop()
            toks.append(Tok("p", "}$", i))
            i = _template(js, i + 1, toks, braces)
        elif c == "/" and _regex_ok(toks):
            j = _regex_end(js, i)
            toks.append(Tok("re", js[i:j], i))
            i = j
        else:
            i = _word_or_punct(js, i, toks, braces)


# ---------- brackets and function bodies ----------
def _opens_function(toks, i, match):
    """Whether the `{` at token `i` opens a function body (after `=>`, or after `(…)` that isn't if/for/while…)."""
    prev = toks[i - 1] if i else None
    if prev is None or prev.kind != "p":
        return False
    if prev.text == "=>":
        return True
    if prev.text != ")":
        return False
    o = match[i - 1]
    before = toks[o - 1] if o else None
    return not (before is not None and before.kind == "id" and before.text in CONTROL)


def _ends_arrow(t):
    """Whether token `t` ends an arrow function's expression body that is open at the top of the stack."""
    if t.kind == "p":
        return t.text in (",", ";", ")", "]", "}", "}$")
    return t.kind == "id" and t.text in STATEMENT


def _params(toks, i, match, params):
    """Add to `params` the parameter tokens of the function whose body or arrow starts at token `i`."""
    prev = toks[i - 1] if i else None
    if prev is not None and _is(prev, "p", ")"):
        params.update(range(match[i - 1] + 1, i - 1))
    elif prev is not None and prev.kind == "id":
        params.add(i - 1)


def _close(toks, i, stack, match):
    """Pair the closing bracket at token `i` with the top of `stack`; return 1 if it closed a function body."""
    x = toks[i].text
    if not stack or stack[-1][1] != CLOSE[x]:
        raise ValueError(f"unpaired {x!r} at offset {toks[i].pos}")
    o, _, fn = stack.pop()
    match[o], match[i] = i, o
    return int(fn)


def _open_brace(toks, i, stack, match, fn_open, params):
    """Push the `{` at token `i`; return 1 if it opens a function body."""
    fn = _opens_function(toks, i, match)
    stack.append((i, "{", fn))
    if fn:
        fn_open.add(i)
        if not _is(toks[i - 1], "p", "=>"):
            _params(toks, i, match, params)
    return int(fn)


def scan(toks):
    """(deferred, match, fn_open, params): which tokens sit inside a function body, each bracket's partner, the
    function-body `{`s, and the tokens of parameter lists.

    A deferred token runs when its function is called, not at load. Raises ValueError if the brackets don't pair."""
    stack, deferred, match, fn_open, params, depth = [], [False] * len(toks), {}, set(), set(), 0
    for i, t in enumerate(toks):
        while stack and stack[-1][1] == "=>" and _ends_arrow(t):
            match[stack.pop()[0]] = i - 1
            depth -= 1
        deferred[i] = depth > 0
        x = t.text if t.kind == "p" else ""
        if x in ("(", "[", "${"):
            stack.append((i, x, False))
        elif x == "{":
            depth += _open_brace(toks, i, stack, match, fn_open, params)
        elif x in CLOSE:
            depth -= _close(toks, i, stack, match)
        elif x == "=>":
            _params(toks, i, match, params)
            if i + 1 < len(toks) and toks[i + 1].text != "{":
                stack.append((i, "=>", True))
                depth += 1
    if stack:
        raise ValueError(f"{len(stack)} bracket(s) left open, the first at offset {toks[stack[0][0]].pos}")
    return deferred, match, fn_open, params


# ---------- the script and its lines ----------
class Source:
    """The page, its app scripts' tokens, and line numbers in the page."""

    def __init__(self, html, path):
        self.path, self.html = path, html
        self.starts = [0] + [m.end() for m in re.finditer(r"\n", html)]
        self.toks = []
        for m in SCRIPT.finditer(html):
            if "json" in m.group(1) or "src=" in m.group(1):
                continue
            for t in lex(m.group(2)):
                t.pos += m.start(2)
                self.toks.append(t)
        self.deferred, self.match, self.fn_open, self.params = scan(self.toks)
        self.blocks = [(m.start(), m.group(1)) for m in BLOCK.finditer(html)]

    def line(self, pos):
        """The 1-based line in the page of offset `pos`."""
        return bisect.bisect_right(self.starts, pos)

    def text(self, pos, width=120):
        """The page line holding `pos`, trimmed."""
        ln = self.html[self.starts[self.line(pos) - 1]:].split("\n", 1)[0].strip()
        return ln if len(ln) <= width else ln[:width - 1] + "…"

    def block(self, pos):
        """The `/* ===== … ===== */` block that offset `pos` sits in, or ''."""
        k = bisect.bisect_right([b[0] for b in self.blocks], pos)
        return self.blocks[k - 1][1] if k else ""


# ---------- wrappers and chains ----------
def _is(t, kind, text=None):
    """Whether token `t` has this kind (and text)."""
    return t.kind == kind and (text is None or t.text == text)


def _rhs_kind(toks, j, match):
    """What the assignment at token `j` stores: 'function', 'arrow' or 'value'."""
    if _is(toks[j], "id", "async"):
        j += 1
    t = toks[j]
    if _is(t, "id", "function"):
        return "function"
    if _is(t, "id") and j + 1 < len(toks) and _is(toks[j + 1], "p", "=>"):
        return "arrow"
    if _is(t, "p", "(") and match[j] + 1 < len(toks) and _is(toks[match[j] + 1], "p", "=>"):
        return "arrow"
    return "value"


def _end(src, j):
    """The offset where the function expression starting at token `j` ends."""
    toks = src.toks
    for k in range(j, len(toks)):
        if k in src.fn_open:
            return toks[src.match[k]].pos
        if _is(toks[k], "p", "=>") and k in src.match:
            return toks[src.match[k]].pos
    return toks[j].pos


def find_swaps(src):
    """check.py's pattern (`const a = f; f = …`) at token level: dicts with name, assignment token, kind, deferred, pos."""
    toks, out = src.toks, []
    for k in range(len(toks) - 7):
        t = toks[k:k + 7]
        if (t[0].kind == "id" and t[0].text in ("const", "let", "var") and t[1].kind == "id" and _is(t[2], "p", "=")
                and t[3].kind == "id" and _is(t[4], "p", ";") and _is(t[5], "id", t[3].text) and _is(t[6], "p", "=")):
            out.append({"name": t[3].text, "alias": t[1].text, "assign": k + 5, "rhs": _rhs_kind(toks, k + 7, src.match),
                        "deferred": src.deferred[k], "pos": t[0].pos})
    return out


def _capture(src, name, i, since):
    """The token capturing `name` into an alias (`const a = name;` or `…, a = name;`) just before the assignment at
    token `i` and after token `since`, or None."""
    toks = src.toks
    for j in range(i - 1, max(since, i - 60, 1), -1):
        if (_is(toks[j], "id", name) and not src.deferred[j] and _is(toks[j - 1], "p", "=") and toks[j - 2].kind == "id"
                and toks[j + 1].kind == "p" and toks[j + 1].text in (",", ";")):
            return j
    return None


def find_steps(src):
    """Every assignment of a function to a name at load (`f = function…`, `f = (…) => …`), in page order: a wrapper
    when it captured the old `f` into an alias just before, otherwise a replacement (the old one is gone)."""
    toks, steps, last = src.toks, [], {}
    for i in range(len(toks) - 2):
        t = toks[i]
        if t.kind != "id" or src.deferred[i] or not _is(toks[i + 1], "p", "="):
            continue
        if i and toks[i - 1].text in (".", "?.", "let", "var", "const") and toks[i - 1].kind in ("p", "id"):
            continue
        if _rhs_kind(toks, i + 2, src.match) == "value":
            continue
        cap = _capture(src, t.text, i, last.get(t.text, 0))
        last[t.text] = i
        steps.append({"name": t.text, "assign": i, "capture": cap, "kind": "replacement" if cap is None else "wrapper",
                      "alias": "" if cap is None else toks[cap - 2].text, "async": _is(toks[i + 2], "id", "async"),
                      "pos": t.pos if cap is None else toks[cap - 2].pos, "end": _end(src, i + 2)})
    return steps


def _is_call(toks, i):
    """Whether the identifier at token `i` is called here: `f(`, `f?.(`, `f.call(` or `f.apply(`."""
    nt = toks[i + 1].text if i + 1 < len(toks) and toks[i + 1].kind == "p" else ""
    after = toks[i + 2].text if i + 2 < len(toks) else ""
    return nt == "(" or (nt == "?." and after == "(") or (nt == "." and after in ("call", "apply"))


def _ref_kind(toks, i):
    """How the identifier at token `i` is used: None (not a use of the function), or declaration, assignment, call,
    reference."""
    prev = toks[i - 1] if i else None
    nxt = toks[i + 1] if i + 1 < len(toks) else None
    pt = prev.text if prev is not None and prev.kind in ("p", "id") else ""
    nt = nxt.text if nxt is not None and nxt.kind == "p" else ""
    if pt in (".", "?.", "typeof") or (nt == ":" and pt in ("{", ",")):
        return None
    if pt == "function":
        return "declaration"
    if nt == "=":
        return "declaration" if pt in ("let", "var", "const") else "assignment"
    return "call" if _is_call(toks, i) else "reference"


def _uses(src, names, skip):
    """For each name, its uses that run at load: (token index, kind); steps, captures and parameters left out."""
    out = {n: [] for n in names}
    for i, t in enumerate(src.toks):
        if t.kind != "id" or t.text not in out or i in skip or i in src.params or src.deferred[i]:
            continue
        kind = _ref_kind(src.toks, i)
        if kind:
            out[t.text].append((i, kind))
    return out


def _chain(src, name, steps, uses):
    """One chain's entry: definitions, its steps (wrappers and replacements) in order, and its early references."""
    toks = src.toks
    order = [s["assign"] for s in steps]
    defs = [{"line": src.line(toks[i].pos), "block": src.block(toks[i].pos)} for i, k in uses if k == "declaration"]
    early, others = [], []
    for i, kind in uses:
        pos = toks[i].pos
        sees = bisect.bisect_left(order, i)
        if kind == "assignment":
            others.append({"line": src.line(pos), "text": src.text(pos)})
        elif kind in ("call", "reference") and sees < len(order):
            early.append({"line": src.line(pos), "kind": kind, "sees": sees, "of": len(order), "text": src.text(pos)})
    return {"name": name, "definitions": defs, "wrappers": sum(s["kind"] == "wrapper" for s in steps),
            "steps": [{"kind": s["kind"], "line": src.line(s["pos"]), "end_line": src.line(s["end"]), "alias": s["alias"],
                       "async": s["async"], "block": src.block(s["pos"])} for s in steps],
            "early_references": early, "other_assignments": others}


def _not_wrapper(src, w):
    """A match of check.py's pattern that is not an in-place wrapper, with the reason."""
    if w["rhs"] == "value":
        why = "stores a value, not a function (a state swap)"
    else:
        why = "inside a function body: swapped when that runs, not at load (a temporary swap; settle by hand)"
    return {"line": src.line(w["pos"]), "name": w["name"], "alias": w["alias"], "reason": why, "text": src.text(w["pos"])}


def plan(chains, size=BATCH):
    """Batches of about `size` wrappers, easiest chains first (no early references, fewest steps, earliest), with
    SOLO_LAST each alone at the end. Returns a list of {"batch", "wrappers", "chains"}."""
    solo = [c for n in SOLO_LAST for c in chains if c["name"] == n]
    rest = sorted((c for c in chains if c["name"] not in SOLO_LAST),
                  key=lambda c: (bool(c["early_references"] or c["other_assignments"]), len(c["steps"]), c["steps"][0]["line"]))
    batches, cur = [], []
    for c in rest:
        if cur and sum(x["wrappers"] for x in cur) + c["wrappers"] > size:
            batches.append(cur)
            cur = []
        cur.append(c)
    batches += [cur] if cur else []
    batches += [[c] for c in solo]
    return [{"batch": k + 1, "wrappers": sum(c["wrappers"] for c in b), "chains": [c["name"] for c in b]}
            for k, b in enumerate(batches)]


def check_py_matches(html):
    """The page offsets of the reassignment's `=` in each wrapper check.py counts (check.wrapper_matches), in the app scripts."""
    out = set()
    for m in SCRIPT.finditer(html):
        if "json" not in m.group(1) and "src=" not in m.group(1):
            out |= {m.start(2) + i for i in check.wrapper_matches(m.group(2))}
    return out


def _summary(src, chains, steps, matched):
    """The headline figures; `matched` holds the `=` offsets check.py's pattern matches."""
    wraps = [s for s in steps if s["kind"] == "wrapper"]
    eq = {src.toks[s["assign"] + 1].pos for s in wraps}
    early = [e for c in chains for e in c["early_references"]]
    return {"check_py_count": len(matched), "wrappers": len(wraps), "chains": len(chains),
            "not_wrappers": len(matched - eq),
            "missed_by_check_py": [src.line(s["pos"]) for s in wraps if src.toks[s["assign"] + 1].pos not in matched],
            "replacements": sum(1 for c in chains for s in c["steps"] if s["kind"] == "replacement"),
            "early_references": len(early), "early_calls": sum(1 for e in early if e["kind"] == "call"),
            "mid_chain_references": sum(1 for e in early if e["sees"] > 0),
            "other_assignments": sum(len(c["other_assignments"]) for c in chains),
            "no_definition": [c["name"] for c in chains if not c["definitions"]],
            "defined_twice": [c["name"] for c in chains if len(c["definitions"]) > 1]}


def inventory(html, path="system/templates/dashboard.html", size=BATCH):
    """The whole inventory of the page's script, as a dict ready for JSON."""
    src = Source(html, path)
    swaps, steps = find_swaps(src), find_steps(src)
    names = sorted({s["name"] for s in steps if s["kind"] == "wrapper"})
    steps = [s for s in steps if s["name"] in names]
    skip = {s["assign"] for s in steps} | {s["capture"] for s in steps if s["capture"] is not None}
    uses = _uses(src, names, skip)
    chains = [_chain(src, n, [s for s in steps if s["name"] == n], uses[n]) for n in names]
    chains.sort(key=lambda c: c["steps"][0]["line"])
    matched = check_py_matches(html)
    real = {s["assign"] for s in steps if s["kind"] == "wrapper"}
    odd = [w for w in swaps if w["assign"] not in real and src.toks[w["assign"] + 1].pos in matched]
    return {"source": path, "summary": _summary(src, chains, steps, matched), "chains": chains,
            "not_wrappers": [_not_wrapper(src, w) for w in odd], "batches": plan(chains, size)}


# ---------- report ----------
def _report_chains(inv, out):
    """The chains and their early references, in page order."""
    out.append("\nChains (page order): definition → steps (=R a replacement: the earlier versions are dropped)")
    for c in inv["chains"]:
        d = ", ".join(f"L{x['line']}" for x in c["definitions"]) or "no definition found"
        ws = " → ".join(("=R " if s["kind"] == "replacement" else "") + f"L{s['line']}"
                        + (f"-{s['end_line']}" if s["end_line"] != s["line"] else "") for s in c["steps"])
        out.append(f"  {c['name']:<22} {c['wrappers']:>2}  def {d}  →  {ws}")
        for e in c["early_references"]:
            where = "before the first step" if e["sees"] == 0 else f"sees {e['sees']} of {e['of']} steps"
            out.append(f"      ! L{e['line']} {e['kind']} at load, {where}: {e['text']}")
        for a in c["other_assignments"]:
            out.append(f"      ! L{a['line']} assigned a value at load: {a['text']}")


def report(inv):
    """The readable report, as text."""
    s = inv["summary"]
    missed = s["missed_by_check_py"]
    out = [f"Wrapper inventory: {inv['source']}",
           f"  {s['chains']} chains, {s['wrappers']} in-place wrappers, {s['replacements']} replacements; "
           f"{s['early_references']} early references at load ({s['mid_chain_references']} mid-chain, between two steps; "
           f"{s['early_calls']} of them calls)",
           f"  check.py counts {s['check_py_count']}: {s['not_wrappers']} of them are not wrappers"
           + (f"; it misses {len(missed)} (L{', L'.join(map(str, missed))})" if missed else "")]
    if s["no_definition"]:
        out.append("  no definition found: " + ", ".join(s["no_definition"]))
    if s["defined_twice"]:
        out.append("  declared more than once (the last declaration wins): " + ", ".join(s["defined_twice"]))
    _report_chains(inv, out)
    out.append("\nNot wrappers (counted by check.py's pattern):")
    out += [f"  L{x['line']} {x['name']}: {x['reason']}" for x in inv["not_wrappers"]]
    out.append("\nBatch plan (easiest first; the last four alone):")
    for b in inv["batches"]:
        out.append(f"  {b['batch']:>2}. {b['wrappers']:>3} wrappers: " + ", ".join(b["chains"]))
    return "\n".join(out)


def main(argv=None):
    """Print the report and write the JSON inventory."""
    ap = argparse.ArgumentParser(prog="wrappers.py", description="Inventory the dashboard's in-place wrappers (BL-231).")
    ap.add_argument("--file", type=Path, default=DASHBOARD, help="the page to read (default: the dashboard template)")
    ap.add_argument("--json", type=Path, default=INVENTORY, help="where to write the inventory")
    ap.add_argument("--no-json", action="store_true", help="don't write the JSON file")
    ap.add_argument("--batch", type=int, default=BATCH, help="wrappers per batch (default 20)")
    ap.add_argument("--quiet", action="store_true", help="print only the summary line")
    a = ap.parse_args(argv)
    path = a.file.resolve()
    shown = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)
    inv = inventory(path.read_text(encoding="utf-8"), shown, a.batch)
    print("\n".join(report(inv).splitlines()[:3]) if a.quiet else report(inv))
    if not a.no_json:
        a.json.write_text(json.dumps(inv, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
