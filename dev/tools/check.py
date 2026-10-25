"""creaite's static check: fast, standard library only, development only (never imported by system/).

Run: python3 dev/tools/check.py [--no-js] [--report] [--update-baseline [--allow-worse]]

Hard checks (always fail, no baseline):
  SYNTAX   a file that doesn't parse, or has an invalid escape sequence (a SyntaxError in a later Python)
  PY39     system/scripts uses grammar newer than Python 3.9 (SETUP.md promises 3.9+); and in every file checked, the
           standard library or language that 3.9 lacks and the grammar check can't see: newer keyword arguments
           (write_text(newline=), zip(strict=), dataclass(slots=)…), names (int.bit_count, itertools.pairwise,
           datetime.UTC, tomllib…), an `X | Y` annotation evaluated at run time, and f-strings only 3.12 accepts
  F401     an import that is never used (a line marked `# noqa` is left alone)
  F821     a name that is read but bound nowhere in its file
  F811     a function or class defined twice in one body (the first is silently lost; in a test, so is a test)
  E722     a bare `except:`
  JSDUP    a function declared twice in the dashboard's inline script (the last declaration silently replaces the first
           everywhere: BL-253's evOpen took over BL-207's evidence panel)
  VENDORED system/templates/vendor/tiptap/ (BL-301 A) doesn't match its manifest, was built from older dev/tiptap/
           sources, or (when the pinned Tiptap is in dev/.cache) isn't byte for byte a fresh `tiptap.py vendor` build
  BUILT    system/templates/dashboard.html is out of date with its source in system/templates/dashboard/ (BL-231 step
           2a), or can't be built (step 2b: the pinned esbuild bundles src/); the message says how to rebuild it. The JS
           checks below read the source (each module in src/), and JSDUP also fails a top-level name declared in two
           modules; the compile check compiles the built page's script

Ratchets (dev/check-baseline.json; a number may fall, never rise):
  CC       a function's complexity; a function not in the baseline may score at most NEW_CC
  LEN      a function's length in lines; a new function may be at most NEW_LEN
  LONG     lines over LONG_LINE characters, per file (system/scripts and dev/tools)
  SILENT   `except Exception:` whose whole body is `pass`, per file
  DOC      functions without a docstring, per file (system/scripts and dev/tools; names starting `_` excluded)
  SWALLOW  `except …: pass` or `continue` with no comment giving the reason, per file (system/scripts and dev/tools)
  JS       the dashboard's inline script: `innerHTML` uses, HTML-string sinks (`innerHTML`, `outerHTML`,
           `insertAdjacentHTML`, `document.write`), in-place function wrappers (`const a = f; f = …`) and empty `catch`
           blocks (and, with Chrome, that it compiles)
  OLD      BL-316: the dashboard's own copies of a shared building block (dev/COMPONENTS.md §3), per block: the old
           helpers (newMenu, pkList, drawPicker, snackAdd and the rest) and menus, dialogs, tab lists and status dots
           made by hand outside the block's own file (OLD_HELPERS); each count falls to 0 as screens move onto the blocks.
           Every run prints the total and the count per screen area (OLD_AREAS); only a rise over the baseline fails
  RUFF, BIOME, VULTURE  per-rule counts from those tools when they are installed (dev/tools/check_extras.py); skipped
           without them, and compared only for the version recorded in the baseline
  TSC      the type errors TypeScript's checkJs finds in the dashboard's modules (dev/tools/typecheck.py, BL-231 step 3),
           when Node is installed; "not run" without it

`--update-baseline` rewrites the baseline from today's numbers but refuses to raise any (`--allow-worse` overrides, for
a deliberate decision). Exits 1 on any failure. Prints `file:line: RULE message`, one per line, so a person or an agent
can act on each.
"""
import argparse
import ast
import builtins
import json
import re
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "dev" / "check-baseline.json"
SCRIPTS = "system/scripts"
GROUPS = {"py": ["system/scripts/*.py", "dev/tools/*.py", "dev/tests/*.py"]}
QUALITY = ("system/scripts/", "dev/tools/")          # the DOC, LONG and SILENT ratchets apply here, not to tests
DASHBOARD = ROOT / "system" / "templates" / "dashboard.html"
NEW_CC = 15
NEW_LEN = 100
LONG_LINE = 140
NOQA = re.compile(r"#\s*noqa\b", re.I)
KNOWN = set(dir(builtins)) | {"__file__", "__name__", "__doc__", "__package__", "__spec__", "__path__", "__builtins__"}


def files():
    out = []
    for pat in GROUPS["py"]:
        out += sorted(ROOT.glob(pat))
    return out


def rel(p):
    return str(p.relative_to(ROOT))


# ---------- complexity ----------
def complexity(fn):
    """McCabe-style: branches, loops, handlers, boolean operands and comprehension clauses, not counting nested defs."""
    n = 1
    stack = list(ast.iter_child_nodes(fn))
    while stack:
        x = stack.pop()
        if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(x, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.IfExp, ast.Assert, ast.comprehension)):
            n += 1
        elif isinstance(x, ast.BoolOp):
            n += len(x.values) - 1
        elif isinstance(x, ast.Try) and x.orelse:
            n += 1
        stack.extend(ast.iter_child_nodes(x))
    return n


def functions(tree):
    """(qualified name, node) for every function, methods and nested functions included."""
    out = []

    def walk(node, prefix):
        for c in ast.iter_child_nodes(node):
            if isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef)):
                q = prefix + c.name
                out.append((q, c))
                walk(c, q + ".")
            elif isinstance(c, ast.ClassDef):
                walk(c, prefix + c.name + ".")
            else:
                walk(c, prefix)
    walk(tree, "")
    return out


# ---------- hard checks ----------
def bound_names(tree):
    names = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
            names.add(n.id)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(n.name)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                names.add((a.asname or a.name).split(".")[0])
        elif isinstance(n, ast.arg):
            names.add(n.arg)
        elif isinstance(n, ast.ExceptHandler) and n.name:
            names.add(n.name)
        elif isinstance(n, (ast.Global, ast.Nonlocal)):
            names.update(n.names)
        elif hasattr(ast, "MatchAs") and isinstance(n, ast.MatchAs) and n.name:
            names.add(n.name)
        elif hasattr(ast, "MatchStar") and isinstance(n, ast.MatchStar) and n.name:
            names.add(n.name)
        elif hasattr(ast, "MatchMapping") and isinstance(n, ast.MatchMapping) and n.rest:
            names.add(n.rest)
    return names


def used_names(tree):
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    for n in ast.walk(tree):               # names in string annotations and __all__
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value.isidentifier():
            used.add(n.value)
    return used


def source_checks(path, src, tree, problems):
    """The hard checks and the Python 3.9 checks the grammar can't make, for one file."""
    hard_checks(path, src, tree, problems)
    problems += [(rel(path), ln, "PY39", msg) for ln, msg in py39_api(src, tree)]


def hard_checks(path, src, tree, problems):
    lines = src.splitlines()
    p = rel(path)

    def noqa(ln):
        return 0 < ln <= len(lines) and NOQA.search(lines[ln - 1])

    star = any(isinstance(n, ast.ImportFrom) and any(a.name == "*" for a in n.names) for n in ast.walk(tree))
    used = used_names(tree)
    for n in ast.walk(tree):
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            if isinstance(n, ast.ImportFrom) and n.module == "__future__":
                continue
            for a in n.names:
                if a.name == "*":
                    continue
                name = (a.asname or a.name).split(".")[0]
                if name not in used and not noqa(n.lineno) and not path.name == "__init__.py":
                    problems.append((p, n.lineno, "F401", f"`{name}` imported but never used"))
        elif isinstance(n, ast.ExceptHandler) and n.type is None:
            problems.append((p, n.lineno, "E722", "bare `except:`; name the exception"))
    if not star:
        bound = bound_names(tree) | KNOWN
        for n in ast.walk(tree):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id not in bound:
                problems.append((p, n.lineno, "F821", f"`{n.id}` is read but never defined in this file"))
    for body_owner in ast.walk(tree):
        body = getattr(body_owner, "body", None)
        if not isinstance(body, list):
            continue
        seen = {}
        for s in body:
            if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not s.decorator_list:
                if s.name in seen and not noqa(s.lineno):
                    problems.append((p, s.lineno, "F811", f"`{s.name}` redefines the one on line {seen[s.name]}"))
                seen[s.name] = s.lineno


# ---------- Python 3.9 (BL-242's floor): what the grammar check can't see ----------
NEW_KWARGS = {  # call name (function or method) -> {keyword: the Python that added it}
    "write_text": {"newline": "3.10"}, "read_text": {"newline": "3.13"}, "zip": {"strict": "3.10"},
    "dataclass": {"slots": "3.10", "kw_only": "3.10", "match_args": "3.10"},
    "glob": {"root_dir": "3.10", "dir_fd": "3.10", "include_hidden": "3.11"}, "iglob": {"root_dir": "3.10", "dir_fd": "3.10"},
    "bisect": {"key": "3.10"}, "bisect_left": {"key": "3.10"}, "bisect_right": {"key": "3.10"}, "insort": {"key": "3.10"},
    "insort_left": {"key": "3.10"}, "insort_right": {"key": "3.10"}, "NamedTemporaryFile": {"delete_on_close": "3.12"},
    "TemporaryDirectory": {"delete": "3.12"}, "rmtree": {"onexc": "3.12"}}
NEW_ATTRS = {("itertools", "pairwise"): "3.10", ("datetime", "UTC"): "3.11", ("enum", "StrEnum"): "3.11",
             ("typing", "Self"): "3.11", ("typing", "TypeAlias"): "3.10", ("typing", "ParamSpec"): "3.10",
             ("contextlib", "aclosing"): "3.10", ("contextlib", "chdir"): "3.11", ("itertools", "batched"): "3.12"}
NEW_METHODS = {"bit_count": "3.10"}                      # on any object: int.bit_count
NEW_NAMES = {"aiter": "3.10", "anext": "3.10", "ExceptionGroup": "3.11", "BaseExceptionGroup": "3.11"}
NEW_MODULES = {"tomllib": "3.11"}


def py39_api(src, tree):
    """(line, message) for each use of the standard library or language newer than Python 3.9 that the grammar check
    (ast.parse with feature_version) can't see."""
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            out += _py39_call(n)
        elif isinstance(n, ast.Attribute):
            out += _py39_attribute(n)
        elif isinstance(n, ast.Name) and n.id in NEW_NAMES and isinstance(n.ctx, ast.Load):
            out.append((n.lineno, f"{n.id} needs Python {NEW_NAMES[n.id]}"))
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            out += _py39_import(n)
    return out + _py39_annotations(tree) + _fstring_312(src, tree)


def _py39_call(n):
    f = n.func
    name = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else None
    return [(n.lineno, f"{name}({kw.arg}=…) needs Python {NEW_KWARGS[name][kw.arg]}")
            for kw in n.keywords if kw.arg in NEW_KWARGS.get(name, {})]


def _py39_attribute(n):
    mod = n.value.id if isinstance(n.value, ast.Name) else None
    if (mod, n.attr) in NEW_ATTRS:
        return [(n.lineno, f"{mod}.{n.attr} needs Python {NEW_ATTRS[(mod, n.attr)]}")]
    if n.attr in NEW_METHODS:
        return [(n.lineno, f".{n.attr} needs Python {NEW_METHODS[n.attr]}")]
    return []


def _py39_import(n):
    if isinstance(n, ast.Import):
        return [(n.lineno, f"module {a.name} needs Python {NEW_MODULES[a.name.split('.')[0]]}")
                for a in n.names if a.name.split(".")[0] in NEW_MODULES]
    out = [(n.lineno, f"module {n.module} needs Python {NEW_MODULES[n.module.split('.')[0]]}")
           ] if n.module and n.module.split(".")[0] in NEW_MODULES else []
    return out + [(n.lineno, f"{a.name} needs Python {NEW_ATTRS[(n.module, a.name)]}")
                  for a in n.names if (n.module, a.name) in NEW_ATTRS]


def _py39_annotations(tree):
    """`X | Y` in an annotation evaluated at run time: signatures, and module- or class-level variables (a local
    variable's annotation never is), unless the file has `from __future__ import annotations`."""
    if any(isinstance(n, ast.ImportFrom) and n.module == "__future__" and any(a.name == "annotations" for a in n.names)
           for n in tree.body):
        return []
    anns = []
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            anns += [a.annotation for a in n.args.args + n.args.kwonlyargs + n.args.posonlyargs] + [n.returns]
        elif isinstance(n, (ast.Module, ast.ClassDef)):
            anns += [s.annotation for s in n.body if isinstance(s, ast.AnnAssign)]
    return [(a.lineno, "an X | Y annotation is evaluated at run time and needs Python 3.10 (or `from __future__ import "
                       "annotations`)") for a in anns
            if a is not None and any(isinstance(x, ast.BinOp) and isinstance(x.op, ast.BitOr) for x in ast.walk(a))]


def _fstring_312(src, tree):
    """f-strings that only Python 3.12 accepts: a backslash, or the f-string's own quote, inside an expression. Only
    checked on 3.12 or later: before it, Python places an f-string's parts unreliably, and doesn't parse such a file at
    all (SYNTAX catches it there)."""
    if sys.version_info < (3, 12):
        return []
    out = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.JoinedStr):
            continue
        body = (ast.get_source_segment(src, n) or "").lstrip("rRbBuUfF")
        quote = body[:3] if body[:3] in ('"""', "'''") else body[:1]
        for v in n.values:
            seg = ast.get_source_segment(src, v.value) or "" if isinstance(v, ast.FormattedValue) else ""
            if "\\" in seg:
                out.append((v.value.lineno, "a backslash inside an f-string's expression needs Python 3.12"))
            elif quote and quote in seg:
                out.append((v.value.lineno, f"the f-string's own quote ({quote}) inside its expression needs Python 3.12"))
    return out


# ---------- metrics ----------
KINDS = ("complexity", "length", "long_lines", "silent_except", "unexplained_swallow", "missing_docstrings")
# BL-316: what each building block replaces (dev/COMPONENTS.md §3, "Replaces"), counted in the dashboard's source (src/ and
# shell.html, the blocks' own files left out): a name of an old helper (its definition and every use), or markup made by
# hand that a block makes. Per block, the count may fall, never rise; BL-316 is done when every one is 0.
OLD_HELPERS = {
    "Menu": (r"\b(?:newMenu|boardMenu|viewMenu|rvReasonMenu|rvMoveMenu|closeBoardMenu|closeViewMenu|cxOpen)\b",
             r"\b(?:bmenu|dmenu)\b", r"""role(?:=\\?"|:\s*")menu\b"""),
    "Dialog": (r"\.showModal\(", r"<dialog\b", r"\bdeDialog\b"),
    "Picker": (r"\b(?:pkList|pkMk|pkPopClose|pkPlace|pkDate)\b",),
    "Combobox": (r"\b(?:comboDraw|comboClose)\b",),
    "FilterBar": (r"\b(?:renderFilterBar|drawMenu|drawPicker|wfFit|rvFilterBar|actFilter)\b",),
    "Tabs": (r"""role(?:=\\?"|:\s*")tablist\b""", r"\b(?:actTab|feedTabsHtml)\b"),
    "Toast": (r"\b(?:snackAdd|bootSnackUndo|bootSnackKeys)\b",),
    "Peek": (r"\bmvPeekEl\b",),
    "StatusDot": (r"""class=\\?"dot\b""", r"\b(?:hdot|pkDots)\b"),
    "Chip": (r"\b(?:pkChip|chipEls|renderViewChips|depChips)\b",),
}
# BL-316 (v1.9.5 step 2): the screen area each source file belongs to, for the OLD count per area (the screen branches
# split by area: Today, Intake, Review, ask creaite and Help; Projects, Work, Milestones, Files and Settings). The first
# prefix that matches wins; a file matching none is its own area, named by its stem.
OLD_AREAS = (("src/today.js", "Today"), ("src/components/today/", "Today"), ("src/components/closeday/", "Today"),
             ("src/stores/today.js", "Today"), ("src/intake.js", "Intake"), ("src/review.js", "Review"),
             ("src/components/review/", "Review"), ("src/stores/rejects.js", "Review"), ("src/ask.js", "ask creaite"),
             ("src/help.js", "Help"), ("src/projects.js", "Projects"), ("src/components/prep/", "Projects"),
             ("src/stores/prep", "Projects"), ("src/meetings.js", "Meetings"), ("src/work.js", "Work"),
             ("src/components/work/", "Work"), ("src/milestones.js", "Milestones"), ("src/files.js", "Files"),
             ("src/settings.js", "Settings"), ("src/components/settings/", "Settings"), ("src/stores/settings.js", "Settings"),
             ("src/activity.js", "Activity"), ("src/panel.js", "Peek"), ("src/components/peek/", "Peek"),
             ("src/sneak.js", "Peek"), ("src/drafts.js", "Drafts"), ("src/rail.js", "Shell"), ("src/main.js", "Shell"),
             ("src/components/sidebar/", "Shell"), ("src/components/dialogs/", "Shell"), ("src/stores/rail.js", "Shell"),
             ("shell.html", "Shell"), ("src/core/", "Core"), ("src/components/", "Core"))
BLOCK_FILES = {"Menu.jsx", "Dialog.jsx", "Picker.jsx", "Combobox.jsx", "FilterBar.jsx", "Tabs.jsx", "Toast.jsx", "Peek.jsx",
               "StatusDot.jsx", "Chip.jsx", "Icon.jsx", "IconButton.jsx"}
TOOL_KINDS = ("ruff", "biome", "vulture", "tsc")
SINK = re.compile(r"\.innerHTML\s*\+?=|\.outerHTML\s*=|insertAdjacentHTML\(|document\.write\(")
DECLARATION = re.compile(r"\b(?:const|let|var)\s+([^;{}\n]*);")     # one declaration statement, on one line
DECLARATOR = re.compile(r"(?:^|,)\s*([A-Za-z_$][\w$]*)\s*=\s*([A-Za-z_$][\w$]*)\s*(?=,|$)")
BETWEEN = re.compile(r"(?:\s+|/\*.*?\*/|//[^\n]*)*", re.S)             # space and comments between two statements
DEFINED = re.compile(r"(?:\bfunction\s+([A-Za-z_$][\w$]*)\s*\("                       # function f( …
                     r"|\b(?:let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s+)?"            # let f = function…, (a) =>, a =>
                     r"(?:function\b|\([^()]*\)\s*=>|[A-Za-z_$][\w$]*\s*=>))")
PUT_BACK = re.compile(r"(?<![\w$.])([A-Za-z_$][\w$]*)\s*=\s*([A-Za-z_$][\w$]*)\s*[;}\n]")
FUNCTION_VALUE = re.compile(r"\s*=(?!=)\s*(?:async\s+)?(?:function\b|\([^()]*\)\s*=>|[A-Za-z_$][\w$]*\s*=>)")


def wrapper_matches(js):
    """The functions the page wraps in place: `const a = f; f = function…` (or an arrow), the capture and the
    reassignment as consecutive statements, with comments or other declarators allowed between (`const a = x, b = f; f = …`).
    Not counted: a value swapped (`const was = LIVE; LIVE = on`), and a temporary swap that puts the original back
    (`const rf = readForm; readForm = () => …; … readForm = rf`), and a callback passed in, composed inside a function
    (`const d0 = doIt; doIt = () => …`): only a function the page defines (`function f(`, `let f = function…`) is wrapped.
    The same as dev/tools/wrappers.py's inventory. Returns the offset of each reassignment's `=`."""
    defined = {a or b for a, b in DEFINED.findall(js)}
    put_back = {(m.group(1), m.group(2)): m.start() for m in PUT_BACK.finditer(js)}     # the last `f = a` of each pair
    out = []
    for decl in DECLARATION.finditer(js):
        after = BETWEEN.match(js, decl.end()).end()
        for alias, name in DECLARATOR.findall(decl.group(1)):
            if name not in defined or not js.startswith(name, after) or not FUNCTION_VALUE.match(js, after + len(name)):
                continue
            if put_back.get((name, alias), -1) >= after:
                continue                                     # put back later: a temporary swap, not a wrapper
            out.append(js.index("=", after + len(name)))     # the reassignment's `=` (wrappers.py reconciles on it)
    return out


def wrappers(js):
    """How many functions the page wraps in place (see wrapper_matches): the JS ratchet's `wrappers` figure."""
    return len(wrapper_matches(js))


def unexplained_swallows(src, tree):
    """Handlers whose whole body is `pass` or `continue` with no comment on the line before, the handler or its body."""
    lines = src.splitlines()
    n = 0
    for x in ast.walk(tree):
        if isinstance(x, ast.ExceptHandler) and all(isinstance(b, (ast.Pass, ast.Continue)) for b in x.body):
            if not any("#" in ln for ln in lines[max(x.lineno - 2, 0):x.end_lineno]):
                n += 1
    return n


def quality_metrics(p, src, tree, m):
    """The per-file counts that apply to system/scripts and dev/tools only, added to `m` when above zero."""
    counts = {"long_lines": sum(1 for ln in src.splitlines() if len(ln) > LONG_LINE),
              "silent_except": sum(1 for x in ast.walk(tree) if isinstance(x, ast.ExceptHandler)
                                   and isinstance(x.type, ast.Name) and x.type.id == "Exception"
                                   and all(isinstance(b, ast.Pass) for b in x.body)),
              "unexplained_swallow": unexplained_swallows(src, tree),
              "missing_docstrings": sum(1 for q, fn in functions(tree)
                                        if not fn.name.startswith("_") and not ast.get_docstring(fn))}
    for kind, n in counts.items():
        if n:
            m[kind][p] = n


def metrics(path, src, tree):
    p = rel(path)
    m = {k: {} for k in KINDS}
    for q, fn in functions(tree):
        key = f"{p}::{q}"
        m["complexity"][key] = complexity(fn)
        m["length"][key] = fn.end_lineno - fn.lineno + 1
    if p.startswith(QUALITY):
        quality_metrics(p, src, tree, m)
    return m


def page_js():
    """The text of the built dashboard page's inline script (the data block and external scripts left out), or ''."""
    if not DASHBOARD.exists():
        return ""
    scripts = re.findall(r"<script([^>]*)>(.*?)</script>", DASHBOARD.read_text(encoding="utf-8"), re.S)
    return "\n".join(body for attrs, body in scripts if "json" not in attrs and "src=" not in attrs)


def dashboard_sources():
    """{name: text} of the dashboard script's source (BL-231 step 2b): each module in src/. Without the source, the
    built page's script."""
    import build_dashboard_js as bj
    if not (bj.SRC / "src").is_dir():
        return {"dashboard.js": page_js()} if DASHBOARD.exists() else {}
    return {"src/" + rel: js for rel, js in bj.analysis_sources().items()}   # BL-256: components as esbuild turns their JSX into calls


def dashboard_js():
    """The text the JS ratchet counts: the script's source, every module joined (the bundle is esbuild's
    reprint of it, without its comments, so its counts would not be the code people edit)."""
    return "\n".join(dashboard_sources().values())


def js_metrics(js, compile_too, problems, sources=None):
    """The counts the JS ratchet holds, from the script text; with `compile_too`, Chrome must also compile the built
    page's script. `sources` ({name: text}, the modules) are checked for a name declared in two of them."""
    if not js:
        return {}
    out = {"innerHTML": len(re.findall(r"innerHTML", js)),
           "html_sinks": len(SINK.findall(js)),
           "wrappers": wrappers(js),
           "empty_catch": len(re.findall(r"catch\s*(\([^)]*\))?\s*\{\s*\}", js))}
    for name, lines in duplicate_functions(js).items():
        problems.append((rel(DASHBOARD), 0, "JSDUP", f"function {name} is declared {len(lines)} times (lines {', '.join(map(str, lines))} "
                         "of the script): the last replaces the others everywhere; rename one"))
    for name, files in duplicate_names(sources or {}).items():
        problems.append((rel(DASHBOARD), 0, "JSDUP", f"{name} is declared at the top level of {', '.join(files)}: "
                         "two modules can't share a name; rename one"))
    if compile_too:
        err = compile_js(page_js())
        if err:
            problems.append((rel(DASHBOARD), 0, "JS", f"the inline script does not compile: {err}"))
    return out


def duplicate_functions(js):
    """{name: [script line, …]} for every function declared more than once at the start of a line (`function f(`,
    `async function f(`, either with `export`): JavaScript hoists the last one over the rest, so the first is silently
    lost; across modules, esbuild renames one and `export *` drops both from the page's names."""
    seen = {}
    for m in re.finditer(r"(?m)^(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(", js):
        seen.setdefault(m.group(1), []).append(js.count("\n", 0, m.start()) + 1)
    return {n: ls for n, ls in seen.items() if len(ls) > 1}


def duplicate_names(sources):
    """{name: [file, …]} for every top-level name declared in more than one of `sources` ({name: text})."""
    import build_dashboard_js as bj
    seen = {}
    for name, text in sources.items():
        for n in bj.top_level(text):
            seen.setdefault(n, []).append(name)
    return {n: fs for n, fs in seen.items() if len(fs) > 1}


def compile_js(js):
    """None if Chrome compiles the script, the error text if not; None (skipped) without Chrome."""
    sys.path.insert(0, str(ROOT / "dev" / "tools"))
    try:
        import cdp
        cdp.chrome_path()
    except Exception:
        print("check: no Chrome found, the JavaScript compile check is skipped", file=sys.stderr)
        return None
    with cdp.Browser() as b:
        r = b.call("Runtime.compileScript", expression=js, sourceURL="dashboard.html", persistScript=False)
    d = (r or {}).get("exceptionDetails")
    if d:
        return f"line {d.get('lineNumber', 0) + 1}: {d.get('exception', {}).get('description', d.get('text', ''))}"
    return None


# ---------- ratchet ----------
def tool_ratchet(cur, base, versions, problems):
    """RUFF, BIOME, VULTURE and TSC: each rule's count may not rise, unless the tool is not the version the baseline recorded."""
    for tool in TOOL_KINDS:
        if tool not in cur:
            continue
        was = base.get("tool_versions", {}).get(tool)
        if was and was != versions.get(tool):
            print(f"check: {tool} is {versions.get(tool)}, the baseline was made with {was}; its counts are not compared "
                  f"(refresh with --update-baseline)", file=sys.stderr)
            continue
        for rule, v in sorted(cur[tool].items()):
            limit = base.get(tool, {}).get(rule, 0)
            if v > limit:
                problems.append((tool, 0, tool.upper(), f"{rule} appears {v} times; the limit is {limit}"))


def ratchet(cur, base, problems):
    for kind, label, hint in (("complexity", "CC", "split it, or lower it before adding to it"),
                              ("length", "LEN", "split it")):
        limit_new = NEW_CC if kind == "complexity" else NEW_LEN
        for key, v in sorted(cur[kind].items()):
            limit = base.get(kind, {}).get(key, limit_new)
            if v > limit:
                f, q = key.split("::")
                what = "complexity" if kind == "complexity" else "lines"
                problems.append((f, 0, label, f"{q} has {v} {what}; the limit is {limit} ({hint})"))
    for kind, label, what in (("long_lines", "LONG", f"lines over {LONG_LINE} characters"),
                              ("silent_except", "SILENT", "`except Exception: pass`"),
                              ("unexplained_swallow", "SWALLOW", "swallowed exceptions with no comment giving the reason"),
                              ("missing_docstrings", "DOC", "public functions without a docstring")):
        for f, v in sorted(cur[kind].items()):
            limit = base.get(kind, {}).get(f, 0)
            if v > limit:
                problems.append((f, 0, label, f"{v} {what}; the limit is {limit}"))
    for k, v in cur.get("js", {}).items():
        limit = base.get("js", {}).get(k, 0)
        if v > limit:
            problems.append((rel(DASHBOARD), 0, "JS", f"{k} appears {v} times; the limit is {limit}"))
    for k, v in sorted(cur.get("old_helpers", {}).items()):
        limit = base.get("old_helpers", {}).get(k, 0)
        if v > limit:
            problems.append((rel(DASHBOARD), 0, "OLD", f"{v} copies of the {k} block's job outside {k} (dev/COMPONENTS.md); "
                             f"the limit is {limit}: use the block"))


def lowered(cur, base):
    """The baseline from today's numbers, and whether any number rose against the old baseline."""
    new, rose = {}, []
    for kind, vals in cur.items():
        new[kind] = {}
        for key, v in vals.items() if isinstance(vals, dict) else []:
            if kind in ("complexity", "length"):
                limit_new = NEW_CC if kind == "complexity" else NEW_LEN
                old = base.get(kind, {}).get(key, limit_new)
                if v <= limit_new:
                    continue                      # inside the limit for a new function: no entry needed
            else:
                old = base.get(kind, {}).get(key, 0)
            # new to the baseline: recorded, not "worse"
            unmeasured = kind not in base or (kind in ("js", "old_helpers") and key not in base[kind])
            if v > old and not unmeasured:
                rose.append(f"{kind} {key}: {old} -> {v}")
            new[kind][key] = v
    return new, rose


def waiver_key(problem):
    """"file RULE name" for a problem, the form the baseline's waived list uses (no backslash in an f-string: Python 3.9)."""
    m = re.search(r"`(\w+)`", problem[3])
    return f"{problem[0]} {problem[2]} {m.group(1) if m else ''}"


def update_baseline(cur, base, versions, allow_worse):
    """Write the baseline from today's numbers. A number that rose is refused (unless allowed); a tool that is missing keeps
    its old entries; a tool whose version changed is re-recorded without the comparison."""
    new, rose = lowered(cur, base)
    if "complexity" not in base:          # no baseline yet: the first one records today as it is
        rose = []
    renewed = {t for t in TOOL_KINDS if t in cur and base.get("tool_versions", {}).get(t) not in (None, versions.get(t))}
    rose = [r for r in rose if r.split()[0] not in renewed]
    if rose and not allow_worse:
        print("Refusing to raise the baseline (use --allow-worse for a deliberate decision):")
        for r in rose:
            print("  " + r)
        return 1
    for t in TOOL_KINDS:
        if t not in cur and t in base:    # not installed here: keep what was recorded
            new[t] = base[t]
    new["tool_versions"] = {**base.get("tool_versions", {}), **versions}
    new["waived"] = base.get("waived", [])
    new["_note"] = "Ratchet for dev/tools/check.py: a number may fall, never rise. Regenerate with --update-baseline."
    BASELINE.write_text(json.dumps(new, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Baseline written: {len(new['complexity'])} complex functions, {len(new['length'])} long"
          + (f"; re-recorded {', '.join(sorted(renewed))}" if renewed else "") + ".")
    return 0


def old_sources():
    """BL-316: {path relative to system/templates/dashboard/: text} of the dashboard's source the OLD count reads (src/ and
    shell.html, the blocks' own files left out)."""
    dash = DASHBOARD.parent / "dashboard"
    out = {f.relative_to(dash).as_posix(): f.read_text(encoding="utf-8") for f in sorted((dash / "src").rglob("*"))
           if f.suffix in (".js", ".jsx") and f.name not in BLOCK_FILES}
    if (dash / "shell.html").exists():
        out["shell.html"] = (dash / "shell.html").read_text(encoding="utf-8")
    return out


def old_area(path):
    """The screen area a dashboard source file belongs to (OLD_AREAS), or its stem."""
    return next((area for prefix, area in OLD_AREAS if path.startswith(prefix)), Path(path).stem)


def old_counts(text):
    """{block: count} of OLD_HELPERS in one text."""
    return {block: sum(len(re.findall(rx, text)) for rx in rxs) for block, rxs in OLD_HELPERS.items()}


def old_helpers():
    """BL-316: {block: count} of the dashboard's own copies of each building block (OLD_HELPERS), in src/ and shell.html."""
    return old_counts("\n".join(old_sources().values()))


def old_by_area():
    """BL-316: {area: {block: count}} of the old helpers, only the non-zero counts, per screen area (OLD_AREAS)."""
    out = {}
    for path, text in old_sources().items():
        area = out.setdefault(old_area(path), {})
        for block, n in old_counts(text).items():
            if n:
                area[block] = area.get(block, 0) + n
    return {a: c for a, c in out.items() if c}


def old_report(counts, by_area, base):
    """The lines check.py always prints for BL-316: the total against the baseline's, then each area's count by block."""
    total, was = sum(counts.values()), sum(base.get("old_helpers", {}).values())
    lines = [f"Old helpers (BL-316, falling to 0): {total} in all (baseline {was}): " + old_line(counts)]
    for area, c in sorted(by_area.items(), key=lambda kv: (-sum(kv[1].values()), kv[0])):
        lines.append(f"  {area}: {sum(c.values())} ({old_line(c)})")
    return lines


def old_line(counts):
    """"Chip 26, Combobox 12, …": the OLD counts on one line, for --report."""
    return ", ".join(f"{k} {v}" for k, v in sorted(counts.items()))


def built_page(problems):
    """BUILT: the committed dashboard.html must be the page its source in system/templates/dashboard/ builds."""
    import split_dashboard
    why = split_dashboard.stale()
    if why:
        problems.append((rel(DASHBOARD), 0, "BUILT", why))


def sent_confusables(problems):
    """GENERATED: the page's look-alike map for the "I sent it" check is what Python's table gives (#368)."""
    import gen_linktext_confusables
    why = gen_linktext_confusables.stale()
    if why:
        problems.append((rel(gen_linktext_confusables.OUT.parent), 0, "GENERATED", why))


def vendored_tiptap(problems):
    """VENDORED: the committed Tiptap editor is the one dev/tiptap/ and the pinned packages build (BL-301 A)."""
    import tiptap
    why = tiptap.stale()
    if why:
        problems.append((rel(tiptap.VENDOR), 0, "VENDORED", why))


def extras(js, with_js, cur, problems):
    """ruff, Biome, vulture and tsc counts into `cur` when installed; a tool that checked nothing is a problem. Their versions."""
    import check_extras
    counts, versions, _ = check_extras.collect(js, with_js)
    cur.update(counts)
    problems += [(tool, 0, tool.upper(), msg) for tool, msg in check_extras.PROBLEMS]
    return versions


def main(argv):
    ap = argparse.ArgumentParser(prog="check.py")
    ap.add_argument("--no-js", action="store_true", help="skip the Chrome compile and Biome on the dashboard script")
    ap.add_argument("--no-extras", action="store_true", help="skip ruff, Biome, vulture and tsc even when installed")
    ap.add_argument("--report", action="store_true", help="also print the ten most complex functions")
    ap.add_argument("--update-baseline", action="store_true")
    ap.add_argument("--allow-worse", action="store_true")
    a = ap.parse_args(argv)

    problems = []
    cur = {k: {} for k in KINDS}
    for path in files():
        src = path.read_text(encoding="utf-8")
        p = rel(path)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", SyntaxWarning)
                tree = ast.parse(src, p)
        except (SyntaxError, SyntaxWarning) as e:
            problems.append((p, getattr(e, "lineno", 0) or 0, "SYNTAX", str(getattr(e, "msg", e))))
            continue
        if p.startswith(SCRIPTS):
            try:
                ast.parse(src, p, feature_version=(3, 9))
            except SyntaxError as e:
                problems.append((p, e.lineno or 0, "PY39", f"{e.msg} (needs a newer Python than 3.9)"))
        source_checks(path, src, tree, problems)
        for kind, vals in metrics(path, src, tree).items():
            cur[kind].update(vals)
    built_page(problems)
    sent_confusables(problems)
    vendored_tiptap(problems)
    sources = dashboard_sources()
    js = "\n".join(sources.values())
    cur["js"] = js_metrics(js, not a.no_js, problems, sources)
    cur["old_helpers"] = old_helpers()
    versions = {} if a.no_extras else extras(sources, not a.no_js, cur, problems)

    base = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else {}
    if a.update_baseline:
        return update_baseline(cur, base, versions, a.allow_worse)
    tool_ratchet(cur, base, versions, problems)
    ratchet(cur, base, problems)
    waived = set(base.get("waived", []))          # "file RULE name": a known hard problem, listed until it is fixed
    problems = [x for x in problems if waiver_key(x) not in waived]

    for f, ln, rule, msg in sorted(problems, key=lambda x: (x[0], x[1], x[2])):
        print(f"{f}:{ln}: {rule} {msg}" if ln else f"{f}: {rule} {msg}")
    print("\n".join(old_report(cur["old_helpers"], old_by_area(), base)))
    if a.report:
        print("Most complex:")
        for key, v in sorted(cur["complexity"].items(), key=lambda kv: -kv[1])[:10]:
            print(f"  {v:3d}  {key}")
    print(f"check: {len(problems)} problem(s)" if problems else "check: OK")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
