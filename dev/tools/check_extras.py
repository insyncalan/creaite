"""The optional half of dev/tools/check.py: counts from ruff, Biome, vulture and tsc, when installed (development only).

check.py itself needs only the standard library. This module asks the tools it finds for a few numbers and hands them
back; a tool that isn't installed is skipped with one line on stderr, so CI and a new machine still pass without them.
The numbers are ratcheted by rule in dev/check-baseline.json like the others (a count may fall, never rise), and the
baseline records each tool's version: a count made by another version is shown but not compared, because a new version
can add findings without anyone changing code. Refresh with `check.py --update-baseline` after upgrading.

tsc (BL-231 step 3) is TypeScript's checkJs over the dashboard's modules, run by dev/tools/typecheck.py through Node's
npx; its one number is the total of type errors (`tsc: {"errors": n}`). Without Node it is "not run", as Biome is
without Biome, and never fails the check.

Not run by `import`: the tools are only called through `collect`.
"""
import collections
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYTHON_DIRS = ["system/scripts", "dev/tools", "dev/tests"]
VENDOR = "system/scripts/vendor"
# Rules worth holding rule by rule: real mistakes, not style. Others stay off until someone decides they matter.
RUFF_RULES = ["F", "E9", "B006", "B007", "B008", "B023", "B904"]
BIOME_RULES = ["suspicious/noFunctionAssign", "suspicious/noAssignInExpressions", "suspicious/noControlCharactersInRegex",
               "suspicious/noGlobalIsNan", "suspicious/noSparseArray"]
VULTURE_CONFIDENCE = 80
BIOME_MAX_BYTES = 16_000_000              # Biome's default (1 MiB) is smaller than the dashboard's script: it would skip it
PROBLEMS = []                             # a tool that ran but checked nothing: reported by check.py as a failure
EXTRA_PATHS = [Path.home() / ".local" / "bin", Path.home() / "homebrew" / "bin", Path("/opt/homebrew/bin"), Path("/usr/local/bin")]


def find(name):
    """The tool's path, searching the PATH and the places uv and Homebrew put tools, or None."""
    path = os.pathsep.join([os.environ.get("PATH", "")] + [str(p) for p in EXTRA_PATHS])
    return shutil.which(name, path=path)


def run(cmd, **kw):
    """The completed process, with output as text; never raises on a non-zero exit (linters exit 1 on findings)."""
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, **kw)


def version(exe):
    """The first line of `exe --version`, trimmed."""
    out = (run([exe, "--version"]).stdout or "").strip().splitlines()
    return out[0].strip() if out else "unknown"


def ruff_counts(exe):
    """{rule code: how many} over the Python files, vendor/ left out. A file that doesn't parse counts under `syntax`."""
    r = run([exe, "check", "--isolated", "--no-cache", "--output-format", "json", "--target-version", "py312",
             "--extend-exclude", VENDOR, "--select", ",".join(RUFF_RULES), *PYTHON_DIRS])
    try:
        found = json.loads(r.stdout or "[]")
    except ValueError:
        return {}
    c = collections.Counter(f.get("code") or "syntax" for f in found)
    return dict(sorted(c.items()))


def biome_counts(exe, js):
    """{rule: how many} for the dashboard's script, for BIOME_RULES only. `js` is the script's text, or its source as
    {name: text} (BL-231 step 2b: each module), each linted as its own file."""
    files = js if isinstance(js, dict) else {"dashboard.js": js}
    with tempfile.TemporaryDirectory() as d:
        paths = []
        for name, text in files.items():
            f = Path(d) / name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(text, encoding="utf-8")
            paths.append(str(f))
        cmd = [exe, "lint", "--reporter=json", "--max-diagnostics=none", f"--files-max-size={BIOME_MAX_BYTES}"] + \
            [f"--only={r}" for r in BIOME_RULES] + paths
        r = run(cmd)
    try:
        out = json.loads(r.stdout or "{}")
    except ValueError:
        out = {}
    summary = out.get("summary") or {}
    if not (summary.get("changed", 0) + summary.get("unchanged", 0)):    # nothing was linted: never a count of zero
        size = sum(len(t.encode()) for t in files.values())
        PROBLEMS.append(("biome", f"Biome checked no file ({size} bytes of script); its counts would be meaningless"))
        return None
    found = out.get("diagnostics", [])
    c = collections.Counter(x.get("category", "").replace("lint/", "") for x in found)
    return dict(sorted(c.items()))


def vulture_count(exe):
    """How many unused names vulture is at least VULTURE_CONFIDENCE per cent sure of, in the scripts and tools."""
    r = run([exe, "system/scripts", "dev/tools", "--exclude", f"*/{VENDOR.split('/')[-1]}/*",
             "--min-confidence", str(VULTURE_CONFIDENCE)])
    return {"unused": sum(1 for ln in r.stdout.splitlines() if ln.strip())}


def tsc_counts():
    """{"errors": n}: tsc's type errors over the dashboard's modules; None when Node is missing or tsc couldn't run (say,
    offline before TypeScript is in npx's cache), so the count is "not run", never a failure."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import typecheck
    npx = typecheck.find_npx()
    if not npx:
        return None
    code, output = typecheck.run_tsc(npx)
    errors = typecheck.parse(output)
    if code and not errors:
        return None
    return {"errors": len(errors)}


def collect(js, with_js=True):
    """(counts by tool, versions by tool, tools skipped). `js` is the dashboard's script: its text, or {name: text}."""
    counts, versions, skipped = {}, {}, []
    for name, make in (("ruff", lambda e: ruff_counts(e)), ("vulture", lambda e: vulture_count(e)),
                       ("biome", lambda e: biome_counts(e, js))):
        exe = find(name)
        if not exe or (name == "biome" and (not with_js or not js)):
            skipped.append(name)
            continue
        result = make(exe)
        if result is None:                    # the tool ran but checked nothing (PROBLEMS says why): no counts to compare
            continue
        counts[name] = result
        versions[name] = version(exe)
    if with_js and js:
        result = tsc_counts()
        if result is None:
            skipped.append("tsc")
        else:
            import typecheck
            counts["tsc"], versions["tsc"] = result, typecheck.TYPESCRIPT
    else:
        skipped.append("tsc")
    if skipped:
        print("check: not run (not installed, or skipped): " + ", ".join(skipped), file=sys.stderr)
    return counts, versions, skipped
