#!/usr/bin/env python3
"""Audit the test vaults: which system/scripts modules a copied script imports (top level or lazy,
inside functions and try blocks) but the fixture never copies. Read only.

  python dev/tools/check_test_vault_modules.py          # report; exit 1 if the main helper misses any
  python dev/tools/check_test_vault_modules.py --all    # also the other fixtures that copy scripts one by one

A missing module that sits inside try/except makes the code look 'unavailable' or fail closed, so a test
can pass without testing anything. This is the check that stops it.
"""
import ast
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "system" / "scripts"
TESTS = REPO / "dev" / "tests"
# modules that are not in the vault's copied list on purpose (not python modules, or dev only)
ALWAYS_OK = {"run"}


def all_modules():
    """Every module in system/scripts/."""
    return {p.stem for p in SCRIPTS.glob("*.py")}


def _names(node, mods):
    """The script modules one import statement names."""
    if isinstance(node, ast.Import):
        found = [a.name.split(".")[0] for a in node.names]
    elif node.level:
        found = [a.name for a in node.names]
    else:
        found = [(node.module or "").split(".")[0]]
    return [n for n in found if n in mods]


def imports_of(name, mods):
    """module -> {imported script module: 'top' | 'lazy'}: 'top' when a plain import statement sits at the top of the file."""
    tree = ast.parse((SCRIPTS / f"{name}.py").read_text(encoding="utf-8"))
    found = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for n in _names(node, mods):
                found.setdefault(n, "lazy")
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for n in _names(node, mods):
                found[n] = "top"
    found.pop(name, None)
    return found


def graph():
    """(all script modules, module -> what it imports)."""
    mods = all_modules()
    return mods, {m: imports_of(m, mods) for m in mods}


def closure(copied, g):
    """Every module a copied script imports, transitively through the copied ones."""
    need, todo = {}, list(copied)
    seen = set(copied)
    while todo:
        m = todo.pop()
        for dep, how in g.get(m, {}).items():
            need.setdefault(dep, set()).add(m)
            if dep not in seen:
                seen.add(dep)
                todo.append(dep)
    return need


def main_helper_list():
    """The script names make_vault copies one by one, read from the source (no import). None: it copies every script."""
    src = (TESTS / "test_tracker.py").read_text(encoding="utf-8")
    fn = next(n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef) and n.name == "make_vault")
    body = ast.get_source_segment(src, fn)
    if "ALL_SCRIPTS" in body:
        return None
    return set(re.findall(r'"([a-z_0-9]+)\.py"', body))


def selective_fixtures():
    """Other test files that copy named scripts one by one: file -> script names they mention near a copy."""
    out = {}
    for p in sorted(TESTS.glob("*.py")):
        t = p.read_text(encoding="utf-8")
        if not re.search(r"copy2?\(", t) or "scripts" not in t:
            continue
        if re.search(r"make_vault\(|\bVault\(|_vault\(|from test_tracker import", t):
            continue      # built on the full helper; its extra copies only add to it
        if re.search(r'copytree\(\s*REPO / "system" / "scripts"', t):
            out[p.name] = None       # whole folder
            continue
        names = set(re.findall(r'copy2?\([^\n]*?["\']([a-z_0-9]+)\.py["\']', t))
        for m in re.finditer(r'for f in \(([^)]*)\)', t, re.S):
            names |= set(re.findall(r'"([a-z_0-9]+)\.py"', m.group(1)))
        if names:
            out[p.name] = names
    return out


def report(label, copied, mods, g):
    """Print what a fixture that copies `copied` misses; return the missing modules."""
    need = closure(copied, g)
    missing = {d: sorted(b) for d, b in need.items() if d not in copied and d not in ALWAYS_OK}
    print(f"{label}: copies {len(copied)} of {len(mods)} scripts; missing {len(missing)}")
    for d, by in sorted(missing.items()):
        lazy = all(g[b][d] == "lazy" for b in by)
        print(f"   - {d}.py   imported by {', '.join(by[:4])}{' ...' if len(by) > 4 else ''}   ({'lazy/guarded' if lazy else 'top level'})")
    return missing


def main():
    """Report; exit status 1 when the main vault helper misses a module."""
    mods, g = graph()
    bad = 0
    mine = main_helper_list()
    if mine is None:
        print("make_vault (test_tracker.py): copies every script (ALL_SCRIPTS); nothing can be missing")
        unknown = set()
    else:
        bad += len(report("make_vault (test_tracker.py)", mine, mods, g))
        unknown = {m for m in mine if m not in mods}
    if unknown:
        print("   copy list names a script that does not exist:", sorted(unknown))
        bad += len(unknown)
    if "--all" in sys.argv:
        for f, names in selective_fixtures().items():
            if names is None:
                print(f"{f}: copies the whole scripts folder")
            else:
                report(f, {n for n in names if n in mods}, mods, g)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
