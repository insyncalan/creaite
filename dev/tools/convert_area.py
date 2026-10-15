"""Move one area's pieces from script/ into an ES module (BL-231 step 2b; development only).

Every area is now a module and script/ is gone (dev/archive/notes/v1.8.0/V18-MODULES-PLAN.md, "After the last area"); this is kept as the
record of how it was done, and test_dashboard_split runs it on a made-up area. A piece it moved today would also need
its boot…() call added to src/main.js by hand.

Run: python3 dev/tools/convert_area.py AREA NNNN [NNNN …] [--dry-run]
     e.g. python3 dev/tools/convert_area.py files 0068 0069

It does the mechanical part of dev/archive/notes/v1.8.0/V18-MODULES-PLAN.md's "How to convert an area", the way core was moved:
  1. joins the pieces, in order, into system/templates/dashboard/src/AREA.js;
  2. marks each top-level declaration `export`;
  3. moves each piece's load-time statements (listeners, first draws, anything that isn't a declaration) into
     `export function boot<Area><NNNN>(){…}` and leaves a stub in script/NNNN-….js that calls it, so they still run in
     today's order; a piece with none is deleted;
  4. turns the area's `let`s listed under `live` in src/core/globals.json into the shared state (`let WT="actions"`
     becomes `shared.WT="actions"`), and writes every use in the module of a name that lives in `shared` as shared.X;
  5. turns a function listed under `seams` into a `let` with a setter in `<area>Seams`;
  6. adds the import lines (build_dashboard_js.imports_for) and uncomments the area's line in src/main.js.
Then it prints what to look at by hand: a shared name used as an object shorthand ({WT}) or declared locally, and a
module-level value that reads a `let` or `const` still in script/ while the module loads (it would read it too early).
--dry-run prints that and the summary without writing anything. Comments and code are moved as they are.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_dashboard_js as bj  # noqa: E402

SRC = bj.SRC
MARKER = re.compile(r"/\* =+\s*(.*?)\s*=+")


def end_of(t):
    """The offset just after token `t`."""
    return t.pos + len(t.text)


def lead_comments(js, s, floor):
    """`s` moved back over the comment-only lines directly above it (never over a block marker, never before `floor`)."""
    line_start = js.rfind("\n", 0, s) + 1
    if js[line_start:s].strip():
        return s
    cur = line_start
    while cur > floor:
        prev = js.rfind("\n", 0, cur - 1) + 1
        line = js[prev:cur].strip()
        if prev < floor or not line or "=====" in line or not (line.startswith("//") or
                                                              line.startswith("/*") and line.endswith("*/")):
            break
        cur = prev
    return cur


def rewrite_let(js, st, live):
    """`let A=1, B=2;` with B shared: `export let A=1; shared.B=2;` (a bare `let B;` needs nothing: state.js has it)."""
    kw, decls, cur, depth = st[0].text, [], [], 0
    for t in st[1:]:
        depth = bj._depth(t, depth)
        if depth == 0 and t.kind == "p" and t.text in (",", ";"):
            decls.append(cur)
            cur = []
            continue
        cur.append(t)
    decls += [cur] if cur else []
    keep, assign = [], []
    for d in decls:
        text = js[d[0].pos:end_of(d[-1])]
        if d[0].text not in live:
            keep.append(text)
        elif len(d) > 1:
            assign.append("shared." + text.strip() + ";")
    return " ".join(([f"export {kw} " + ", ".join(keep) + ";"] if keep else []) + assign)


def seam(text, name):
    """`function f(…){…}` as `export let f = function(…){…};` (async kept)."""
    return re.sub(r"^(async\s+)?function\s+" + re.escape(name) + r"\s*\(",
                  lambda m: f"export let {name} = {m.group(1) or ''}function(", text, count=1) + ";"


def convert_piece(js, boot, live, seams, found=None):
    """(the piece as module text, whether it had load-time statements); the seams it turned into a `let` are added to
    `found`."""
    out, steps, pos = [], [], 0
    for st in bj.statements(bj._lexer().lex(js)):
        s, e = st[0].pos, end_of(st[-1])
        names = bj.declares(st)
        if not names:
            s2 = lead_comments(js, s, pos)
            out.append(js[pos:s2])
            steps.append(js[s2:e].strip("\n"))
            m = re.match(r"[ \t]*\n", js[e:])
            pos = e + (m.end() if m and s2 == js.rfind("\n", 0, s2) + 1 else 0)
            continue
        out.append(js[pos:s])
        text, kind = js[s:e], next(iter(names.values()))
        if kind in ("let", "var") and set(names) & live:
            text = rewrite_let(js, st, live)
        elif kind == "function" and next(iter(names)) in seams:
            text = seam(text, next(iter(names)))
            if found is not None:
                found.append(next(iter(names)))
        else:
            text = "export " + text
        out.append(text)
        pos = e
    body = "".join(out) + js[pos:]
    if steps:
        body = body.rstrip("\n") + (f"\n/* BL-231: what this block did at load, run in today's order by its stub in script/ */\n"
                                    f"export function {boot}(){{\n" + "\n".join(steps) + "\n}\n")
    return body, bool(steps)


def _enclosing(toks):
    """For each token, the innermost bracket it sits in ("(", "[", "{", "${" or "")."""
    out, stack = [], []
    for t in toks:
        out.append(stack[-1] if stack else "")
        if t.kind == "p" and t.text in bj.OPENERS:
            stack.append(t.text)
        elif t.kind == "p" and t.text in bj.CLOSERS and stack:
            stack.pop()
    return out


def _use(toks, i, params, inside):
    """How the shared name at token `i` is used: "key" or "prop" (leave it), "local" (declared here), "short"
    (perhaps an object shorthand) or "use"."""
    prev, nxt = (toks[i - 1] if i else None), (toks[i + 1] if i + 1 < len(toks) else None)
    p, n = (prev.text if prev is not None else ""), (nxt.text if nxt is not None else "")
    if p in (".", "?."):
        return "prop"
    if p in ("{", ",") and n == ":":
        return "key"
    if i in params or p in ("let", "const", "var", "function"):
        return "local"
    return "short" if inside == "{" and p in ("{", ",") and n in ("}", ",") else "use"


def to_shared(js, names):
    """Every use of a name in `names` as shared.X; returns (text, [warnings])."""
    w = bj._lexer()
    toks = w.lex(js)
    _, _, _, params = w.scan(toks)
    edits, notes, inside = [], [], _enclosing(toks)
    for i, t in enumerate(toks):
        if t.kind != "id" or t.text not in names:
            continue
        use, where = _use(toks, i, params, inside[i]), js[max(0, t.pos - 50):t.pos + 40].replace("\n", " ")
        if use == "local":
            notes.append(f"{t.text} is declared locally (it hides the shared one): …{where}…")
        elif use == "short":
            notes.append(f"{t.text} may be an object shorthand ({{{t.text}}} needs {t.text}:shared.{t.text}): …{where}…")
        if use in ("use", "short"):
            edits.append(t.pos)
    for p in reversed(edits):
        js = js[:p] + "shared." + js[p:]
    return js, notes


def eager_reads(js, legacy_values):
    """Names of `let`/`const`/`class` still in script/ that the module reads while it loads (outside any function)."""
    w = bj._lexer()
    toks = w.lex(js)
    deferred, _, _, _ = w.scan(toks)
    found = set()
    for i, t in enumerate(toks):
        if t.kind == "id" and not deferred[i] and t.text in legacy_values and not (i and toks[i - 1].text in (".", "?.")):
            found.add(t.text)
    return sorted(found)


def seams_setters(area, names):
    """`export const <area>Seams = { f: v => { f = v; }, … };`: the setters core/globals.js puts on window."""
    if not names:
        return ""
    sets = ", ".join(f"{n}: v => {{ {n} = v; }}" for n in sorted(names))
    return f"export const {area}Seams = {{ {sets} }};\n"


def stub(path, area, boot):
    """The text left in script/ for a piece whose load-time steps moved into `boot`."""
    first = path.read_text(encoding="utf-8").split("\n", 1)[0]
    m = MARKER.match(first)
    label = m.group(1) if m else path.stem[5:]
    return (f"/* ===== {label} ===== */\n/* BL-231 step 2b: this block is now in src/{area}.js; what it did at load runs here, "
            f"in today's order */\n{boot}();\n")


def uncomment_main(area, folder=SRC):
    """Turn `// export * from "./AREA.js";` in src/main.js into the real line; False if it isn't there."""
    main = folder / "src" / "main.js"
    text = main.read_text(encoding="utf-8")
    line = f'export * from "./{area}.js";'
    if f"// {line}" not in text:
        return line in text
    main.write_text(text.replace(f"// {line}", line, 1), encoding="utf-8")
    return True


def plan(area, nums, folder=SRC):
    """Everything the conversion would write: {"module": text, "stubs": {path: text or None}, "notes": [...]}."""
    paths = [next((folder / "script").glob(f"{n}-*.js")) for n in nums]
    g = bj.globals_json(folder)["names"]
    live, seams = set(g["live"]), set(g["seams"])
    cap = area[:1].upper() + area[1:]
    parts, stubs, found = [], {}, []
    for p in paths:
        body, has_boot = convert_piece(p.read_text(encoding="utf-8"), f"boot{cap}{p.name[:4]}", live, seams, found)
        parts.append(body)
        stubs[p] = stub(p, area, f"boot{cap}{p.name[:4]}") if has_boot else None
    still = [p for p in sorted((folder / "script").glob("*.js")) if p not in stubs]
    legacy_decl = {}
    for p in still:
        legacy_decl.update(bj.top_level(p.read_text(encoding="utf-8")))
    js, notes = to_shared("".join(parts), {n for n in live if n not in legacy_decl})
    early = eager_reads(js, {n for n, k in legacy_decl.items() if k != "function"})
    notes += [f"{n} is read while the module loads, but it is still a `let`/`const` in script/ (not yet set then): "
              "move that use into a boot…() or a function" for n in early]
    head = (f"/* {area}.js (BL-231 step 2b), moved from script/ by dev/tools/convert_area.py: {', '.join(p.name for p in paths)}.\n"
            f"   Unchanged apart from `export`, `shared.` for the shared state (core/state.js) and the load-time steps, now in\n"
            f"   boot…() functions that their stubs in script/ call in today's order. */\n")
    body = js.lstrip("\n")
    if found:
        body = body.rstrip("\n") + "\n" + seams_setters(area, found)
    return {"path": folder / "src" / f"{area}.js", "head": head, "body": body, "stubs": stubs, "notes": notes}


def write(p, folder=SRC):
    """Write the module (with its imports), the stubs and the main.js line."""
    p["path"].write_text(p["head"] + p["body"], encoding="utf-8")
    for path, text in p["stubs"].items():
        if text is None:
            path.unlink()
        else:
            path.write_text(text, encoding="utf-8")
    imports = bj.imports_for(p["path"], folder, core_only=True)
    p["path"].write_text(p["head"] + "".join(x + "\n" for x in imports) + p["body"], encoding="utf-8")
    return uncomment_main(p["path"].stem, folder)


def main(argv):
    """Command line: see the module docstring."""
    ap = argparse.ArgumentParser(prog="convert_area.py", description=__doc__.split("\n")[0])
    ap.add_argument("area", help="the module's name, as in src/main.js (files, work, review…)")
    ap.add_argument("pieces", nargs="+", help="the pieces' numbers in script/ (0068 0069)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    p = plan(a.area, [n.zfill(4) for n in a.pieces])
    for n in p["notes"]:
        print("check:", n)
    boots = sum(1 for t in p["stubs"].values() if t)
    print(f"{a.area}.js: {len(p['stubs'])} pieces, {boots} with load-time steps (stubs kept), "
          f"{len(p['stubs']) - boots} deleted{' (dry run: nothing written)' if a.dry_run else ''}.")
    if not a.dry_run and not write(p):
        print(f'src/main.js has no line `// export * from "./{a.area}.js";`: add it in today\'s order.')
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
