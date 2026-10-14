"""Bundle the dashboard's script from its ES modules with the pinned esbuild (BL-231 step 2b; development only).

Run: python3 dev/tools/build_dashboard_js.py            print the page's app script (what `split_dashboard.py build` inlines)
     python3 dev/tools/build_dashboard_js.py globals    rewrite the `tests` list in src/core/globals.json from dev/tests
     python3 dev/tools/build_dashboard_js.py imports FILE [--core]   the import lines FILE needs (--core: from core only)
     python3 dev/tools/build_dashboard_js.py exposes FILE   print what FILE declares that globals.json or tests use
     python3 dev/tools/build_dashboard_js.py order      print any module that reads another's value while it loads, too early

The page's one app <script> is the IIFE: src/main.js and everything it imports, bundled by dev/tools/esbuild.py
(`var CREAITE=(()=>{…})();`). Since BL-231 step 2b's last step, script/ and its prologue are gone: every module
imports what it uses, and main.js runs the load-time steps (the boot…() functions) and the start-up in today's order.

esbuild runs the modules in the order its imports reach them (cycles included), which isn't today's order; that is
safe while no module reads another's value (a `const`, `let` or `var`, or shared.X set at load) while it loads.
`load_order_problems()` checks it, and test_dashboard_split runs it.

esbuild runs with src/ as its working folder, so the output names modules by their path inside src/ and the same
source gives the same bytes wherever it is. Nothing in system/ imports this file or esbuild: the built page is committed
(NFR-12). Standard library only, apart from the esbuild binary.
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import esbuild  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "system" / "templates" / "dashboard"
GLOBAL_NAME = "CREAITE"
# --tsconfig-raw={}: never read a tsconfig.json or jsconfig.json from a folder above the repo (one in a home folder made
# esbuild add "use strict", so the page built differently on laptop 2, 13-10-2026); the build depends on the repo alone.
FLAGS = ["--bundle", "--charset=utf8", "--tree-shaking=false", "--log-level=warning", "--tsconfig-raw={}"]
VENDOR = REPO / "system" / "templates" / "vendor" / "preact"


def preact_flags(folder=SRC):
    """BL-256: JSX through esbuild (the automatic runtime, from Preact), and each library specifier a module may import
    (`preact`, `preact/hooks`, `preact/jsx-runtime`, `@preact/signals`, `@preact/signals-core`) mapped to its vendored
    file, from vendor/preact/manifest.json (dev/tools/vendor_preact.py). Nothing is looked up anywhere else."""
    vendor = folder.parent / "vendor" / "preact"          # beside dashboard/, as in system/templates/
    if not (vendor / "manifest.json").is_file():
        vendor = VENDOR                                    # a copy of dashboard/ alone (a test's): the repo's
    modules = json.loads((vendor / "manifest.json").read_text(encoding="utf-8"))["modules"]
    return ["--jsx=automatic", "--jsx-import-source=preact", "--loader:.jsx=jsx",
            *(f"--alias:{spec}={vendor / path}" for spec, path in sorted(modules.items()))]
WORD = re.compile(r"[A-Za-z_$][\w$]*")
REBUILD_IMPORTS = "python3 dev/tools/build_dashboard_js.py imports"


class BuildError(RuntimeError):
    """esbuild refused the source (a syntax error, a missing import or file); the message is esbuild's."""


def _esbuild(folder, fmt, out, extra=()):
    """Run the pinned esbuild on `folder`/src/main.js with format `fmt`, writing `out`; raise BuildError on failure."""
    args = [*FLAGS, *preact_flags(folder), "main.js", f"--format={fmt}", f"--outfile={out}", *extra]
    r = esbuild.run(args, cwd=folder / "src", capture_output=True, text=True)
    if r.returncode != 0:
        raise BuildError(f"esbuild failed on {folder.name}/src/main.js:\n{r.stderr.strip()}")
    if r.stderr.strip():
        print(r.stderr.strip(), file=sys.stderr)


def bundle(folder=SRC):
    """(the IIFE text, the names main.js exports) for the modules in `folder`/src."""
    with tempfile.TemporaryDirectory() as tmp:
        iife, esm, meta = Path(tmp) / "page.js", Path(tmp) / "esm.js", Path(tmp) / "meta.json"
        _esbuild(folder, "iife", iife, [f"--global-name={GLOBAL_NAME}"])
        _esbuild(folder, "esm", esm, [f"--metafile={meta}"])
        outputs = json.loads(meta.read_text(encoding="utf-8"))["outputs"]
        names = next(o["exports"] for o in outputs.values() if "exports" in o)
        return iife.read_text(encoding="utf-8"), sorted(names)


def globals_json(folder=SRC):
    """src/core/globals.json as a dict."""
    return json.loads((folder / "src" / "core" / "globals.json").read_text(encoding="utf-8"))


def script(folder=SRC):
    """The page's app script: the IIFE."""
    return bundle(folder)[0]


def module_files(folder=SRC):
    """Every source module (src/**/*.js), sorted by path. The components (.jsx) are component_files()."""
    return sorted((folder / "src").rglob("*.js"))


def component_files(folder=SRC):
    """Every component (src/**/*.jsx, BL-256), sorted by path."""
    return sorted((folder / "src").rglob("*.jsx"))


_JSX_CACHE = {}


def component_js(path, folder=SRC):
    """A component's source with its JSX turned into calls by the pinned esbuild (no bundling: its imports, top-level
    names and code stay as written), for the checks that read code with wrappers.py's lexer, which doesn't read JSX."""
    text = Path(path).read_text(encoding="utf-8")
    key = (str(path), text)
    if key not in _JSX_CACHE:
        # no --format: the exports stay inline (`export function …`), as top_level() reads them
        r = esbuild.run([Path(path).name, "--jsx=automatic", "--jsx-import-source=preact", "--charset=utf8",
                         "--log-level=warning", "--tsconfig-raw={}"],
                        cwd=Path(path).parent, capture_output=True, text=True)
        if r.returncode != 0:
            raise BuildError(f"esbuild failed on {Path(path).name}:\n{r.stderr.strip()}")
        _JSX_CACHE[key] = r.stdout
    return _JSX_CACHE[key]


def analysis_sources(folder=SRC):
    """{path inside src/: code} for every module and component, the components as component_js(): what the checks
    that read declarations, imports and load-time reads see."""
    src = folder / "src"
    out = {p.relative_to(src).as_posix(): p.read_text(encoding="utf-8") for p in module_files(folder)}
    out.update({p.relative_to(src).as_posix(): component_js(p, folder) for p in component_files(folder)})
    return dict(sorted(out.items()))


def source_text(folder=SRC):
    """All the script's source, the modules in path order, for the checks that read text (check.py's JS ratchet): the
    source is what people edit; the bundle is esbuild's reprint of it."""
    return "\n".join(p.read_bytes().decode("utf-8") for p in sorted([*module_files(folder), *component_files(folder)])) + "\n"


# ---------- helpers for converting an area (dev/V18-MODULES-PLAN.md) ----------
OPENERS, CLOSERS = ("(", "[", "{", "${"), (")", "]", "}", "}$")
BLOCK_HEADS = ("function", "class", "if", "for", "while", "try", "switch", "{")
DECLARES = ("function", "class", "const", "let", "var")


def _lexer():
    """dev/tools/wrappers.py's tokenizer (comments dropped; strings, templates and regular expressions kept whole)."""
    import wrappers
    return wrappers


def _depth(t, depth):
    """The bracket depth after token `t`."""
    if t.kind == "p" and t.text in OPENERS:
        return depth + 1
    if t.kind == "p" and t.text in CLOSERS:
        return depth - 1
    return depth


def _ends_block(cur, nxt):
    """Whether a top-level `}` ends the statement `cur` (a function, class or block statement; not `} else`)."""
    head = [t.text for t in cur[:3] if t.text != "export"]
    starts = head[:1] == ["async"] and head[1:2] == ["function"] or head[:1] and head[0] in BLOCK_HEADS
    follows = nxt is not None and nxt.text in ("else", "catch", "finally", ".", "(")
    return bool(starts) and not follows


def statements(toks):
    """The top-level statements of a token list, each a list of tokens (split at `;` and at the `}` that ends a block)."""
    out, cur, depth = [], [], 0
    for k, t in enumerate(toks):
        cur.append(t)
        depth = _depth(t, depth)
        if depth == 0 and t.kind == "p" and (t.text == ";" or t.text == "}" and
                                              _ends_block(cur, toks[k + 1] if k + 1 < len(toks) else None)):
            out.append(cur)
            cur = []
    return out + ([cur] if cur else [])


def declares(st):
    """{name: kind} for the names one top-level statement declares (`export` allowed)."""
    toks = st[1:] if st and st[0].text == "export" else st
    head = [t.text for t in toks[:3]]
    if head[:2] == ["async", "function"]:
        toks, head = toks[1:], head[1:]
    if not head or head[0] not in DECLARES:
        return {}
    if head[0] in ("function", "class"):
        name = toks[2] if head[1:2] == ["*"] else toks[1]
        return {name.text: head[0]}
    return {n: head[0] for n in _declarators(toks[1:])}


def _declarators(toks):
    """The names in `a=1, b, c=f(x)` (destructuring patterns are not used at the top level)."""
    names, depth, expect = [], 0, True
    for t in toks:
        if depth == 0 and t.kind == "p" and t.text in (",", "="):
            expect = t.text == ","
        elif expect and depth == 0 and t.kind == "id":
            names.append(t.text)
            expect = False
        depth = _depth(t, depth)
    return names


def top_level(js, exported=False):
    """{name: kind} for the declarations at the top level of `js` (function, class, const, let, var); with
    `exported`, only those marked `export`."""
    out = {}
    for st in statements(_lexer().lex(js)):
        if not exported or st[0].text == "export":
            out.update(declares(st))
    return out


def words(js):
    """The identifiers `js` uses as names: not a property (`a.x`) or an object key (`{x:1}`)."""
    toks = _lexer().lex(js)
    out = set()
    for k, t in enumerate(toks):
        prev = toks[k - 1] if k else None
        nxt = toks[k + 1] if k + 1 < len(toks) else None
        if t.kind != "id" or (prev is not None and prev.kind == "p" and prev.text in (".", "?.")):
            continue
        if prev is not None and prev.text in ("{", ",") and nxt is not None and nxt.text == ":":
            continue
        out.add(t.text)
    return out


def imported(js):
    """The names `js` imports with `import { a, b } from "…";`."""
    toks = _lexer().lex(js)
    out, inside = set(), False
    for k, t in enumerate(toks):
        if t.text == "import" and k + 1 < len(toks) and toks[k + 1].text == "{":
            inside = True
        elif inside and t.text == "}":
            inside = False
        elif inside and t.kind == "id":
            out.add(t.text)
    return out


def exported_by(folder=SRC):
    """{name: module path inside src/} for every name a module exports."""
    out = {}
    for rel, js in analysis_sources(folder).items():
        for n in top_level(js, exported=True):
            out.setdefault(n, rel)
    return out


def imports_for(path, folder=SRC, core_only=False):
    """The import lines `path` needs: each name it uses that another module exports, grouped by module (with
    `core_only`, only core's names)."""
    path = Path(path).resolve()
    js = path.read_text(encoding="utf-8")
    mine, used, want = top_level(js), words(js), {}
    for n, mod in exported_by(folder).items():
        if n in mine or (folder / "src" / mod).resolve() == path or (core_only and not mod.startswith("core/")):
            continue
        if n in used:
            want.setdefault(mod, []).append(n)
    lines = []
    for mod in sorted(want):
        rel = Path(mod)
        spec = "./" + rel.as_posix() if path.parent == (folder / "src").resolve() else _relative(path, folder / "src" / rel)
        lines.append(f"import {{ {', '.join(sorted(want[mod], key=str.lower))} }} from \"{spec}\";")
    return lines


def _relative(frm, to):
    """`to` relative to the folder of `frm`, as an import specifier."""
    import os
    rel = os.path.relpath(to, frm.parent).replace(os.sep, "/")
    return rel if rel.startswith(".") else "./" + rel


def tests_text():
    """Every test file's text, the scripts the tests inject into the page included (ui_probe.js): the names the tests
    use are words in it."""
    tests = REPO / "dev" / "tests"
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted([*tests.glob("*.py"), *tests.glob("*.js")]))


def exposes(path, folder=SRC):
    """What `path` declares that something outside it uses by name: the tests, globals.json lists."""
    js = Path(path).read_text(encoding="utf-8")
    mine = top_level(js)
    test_words = set(WORD.findall(tests_text()))
    g = globals_json(folder)["names"]
    rows = []
    for n, kind in sorted(mine.items()):
        why = [w for w, hit in (("tests", n in test_words), ("live", n in g["live"]),
                                ("seams", n in g["seams"])) if hit]
        if why:
            rows.append(f"{n} ({kind}): {', '.join(why)}")
    return rows


def all_declared(folder=SRC):
    """Every name the modules export."""
    return set(exported_by(folder))


def eval_order(folder=SRC):
    """The modules (paths inside src/) in the order the bundle runs them: esbuild's, from the imports."""
    iife = bundle(folder)[0]
    seen = [m for m in dict.fromkeys(re.findall(r"^  // (\S+\.jsx?)$", iife, re.M)) if m != "main.js"]
    return seen + ["main.js"]


def _import_spans(toks, deferred):
    """The token indexes inside top-level `import … ;` statements."""
    out, inside = set(), False
    for i, t in enumerate(toks):
        if t.text == "import" and not deferred[i] and (not i or toks[i - 1].text in (";", "}")):
            inside = True
        if inside:
            out.add(i)
            inside = t.text != ";"
    return out


def _load_reads(js):
    """(names read, shared.X read, shared.X set) by `js` while it loads: outside every function, not in an import, not a
    property, an object key, a parameter or an arrow's parameter."""
    w = _lexer()
    toks = w.lex(js)
    deferred, _, _, params = w.scan(toks)
    skip = _import_spans(toks, deferred) | set(params) | {i for i, d in enumerate(deferred) if d}
    reads, sreads, ssets = set(), set(), set()
    for i, t in enumerate(toks):
        if i in skip or t.kind != "id":
            continue
        prev = toks[i - 1].text if i else ""
        nxt = toks[i + 1].text if i + 1 < len(toks) else ""
        if prev in (".", "?."):
            if i >= 2 and toks[i - 2].text == "shared":
                (ssets if nxt == "=" else sreads).add(t.text)
        elif not (prev in ("{", ",") and nxt == ":" or nxt == "=>"):
            reads.add(t.text)
    return reads, sreads, ssets


def _too_early(m, js, scans, kinds, at):
    """load_order_problems() for one module `m`."""
    reads, sreads, _ = scans[m]
    later = [o for o in kinds if o != m and at.get(o, -1) > at[m]]
    out = [f"{m} reads {n} ({kinds[o][n]} in {o}) while it loads, but {o} runs later"
           for n in sorted(reads & imported(js)) for o in later if kinds[o].get(n, "function") != "function"]
    out += [f"{m} reads shared.{n} while it loads, but {o}, which sets it then, runs later"
            for n in sorted(sreads) for o in later if n in scans[o][2]]
    return out


def load_order_problems(folder=SRC):
    """Each read, while a module loads, of another module's value (not a function) or of shared.X that a module
    sets while it loads, where that module runs later: it would read undefined. [] when the order is safe."""
    at = {m: i for i, m in enumerate(eval_order(folder))}
    texts = analysis_sources(folder)
    kinds = {m: top_level(js) for m, js in texts.items()}
    scans = {m: _load_reads(js) for m, js in texts.items()}
    return [x for m, js in texts.items() if m in at for x in _too_early(m, js, scans, kinds, at)]


def test_names(folder=SRC):
    """The page's top-level names that appear in dev/tests (the `tests` list in globals.json)."""
    used = set(WORD.findall(tests_text()))
    return sorted(n for n in all_declared(folder) if n in used)


def write_globals(folder=SRC):
    """Rewrite globals.json's `tests` list from dev/tests; return how many names it holds."""
    path = folder / "src" / "core" / "globals.json"
    g = globals_json(folder)
    g["names"]["tests"] = test_names(folder)
    path.write_text(json.dumps(g, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return len(g["names"]["tests"])


def main(argv):
    """Command line: see the module docstring."""
    cmd = argv[0] if argv else "script"
    try:
        if cmd == "script":
            sys.stdout.write(script())
        elif cmd == "globals":
            print(f"globals.json: {write_globals()} test names.")
        elif cmd == "imports" and len(argv) in (2, 3):
            print("\n".join(imports_for(argv[1], core_only="--core" in argv)))
        elif cmd == "order":
            problems = load_order_problems()
            print("\n".join(problems) or "no module reads another's value too early")
            return 1 if problems else 0
        elif cmd == "exposes" and len(argv) == 2:
            print("\n".join(exposes(argv[1])) or "nothing outside the module uses its names")
        else:
            print(__doc__.split("\n\n")[0], file=sys.stderr)
            return 2
    except (BuildError, esbuild.EsbuildError, subprocess.SubprocessError) as e:
        print(f"build_dashboard_js: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
