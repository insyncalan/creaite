"""#212: the reading and reporting half of dev/tools/handcheck.py, with no browser anywhere in it.

What it does (handcheck.py calls it for `all`, `--from/--to` and `--list`; dev/tests/test_handcheck_report.py tests it):
- finds the releases that have a hand-check module (dev/tests/handchecks/test_v<release>.py) and orders them;
- reads the Product Manager's sheet for a release (dev/handchecks/<release>.md, or, when told, `git show <ref>:...`) and lists its
  numbered checks, each with the tags it carries ("judgement", "live only");
- scans a test module (as text, without importing it) for the checks it has a test for (`def test_cNN_...`, not marked phase2);
- works out the coverage gaps: a sheet check with no test that is not tagged judgement or live only;
- turns a run's outcomes into counts and a one-screen summary per release, and one table for all of them.

Development only; nothing at run time uses it.
"""
import ast
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SHEETS = REPO / "dev" / "handchecks"
MODULES = REPO / "dev" / "tests" / "handchecks"

TEST_NAME = re.compile(r"^test_c(\d+)_")
NUMBERED = re.compile(r"^(\d+)\. (.+)$")
RELEASE_HEAD = re.compile(r"^##\s+v?(\d+\.\d+\.\d+)\b")
JUDGEMENT = re.compile(r"\bjudgement\b", re.I)
LIVE_ONLY = re.compile(r"\blive[ -]only\b", re.I)


# ── releases ─────────────────────────────────────────────────────────────────

def vkey(v):
    """A release name ("v2.3.2" or "2.3.2") as a sortable tuple."""
    return tuple(int(x) for x in v.lstrip("v").split("."))


def norm(v):
    """"2.3.2" and "v2.3.2" both as "v2.3.2"."""
    v = v.strip()
    return v if v.startswith("v") else "v" + v


def module_release(name):
    """The release a module file is for: test_v232 is v2.3.2, test_v195 v1.9.5 (major, minor, then the rest). None if not one."""
    m = re.fullmatch(r"test_v(\d)(\d)(\d+)", name)
    return f"v{m.group(1)}.{m.group(2)}.{m.group(3)}" if m else None


def module_name(v):
    """The module a release's checks live in: v2.3.2 is test_v232."""
    return "test_v" + norm(v)[1:].replace(".", "")


def releases(modules=MODULES):
    """Every release with a hand-check module, oldest first."""
    found = (module_release(p.stem) for p in Path(modules).glob("test_v*.py"))
    return sorted((v for v in found if v), key=vkey)


def select(avail, first=None, last=None, only=None):
    """The releases to use: those from `first` to `last` inclusive (open-ended when None), then narrowed to `only` (names, if given)."""
    out = [v for v in avail if (not first or vkey(v) >= vkey(first)) and (not last or vkey(v) <= vkey(last))]
    return [v for v in out if v in only] if only else out


def parse_only(text, avail):
    """`--only` in all-mode: "v2.3.2,v2.3.3:1+2" gives ({release: None or {check numbers}}, problem or None). A bare number is a problem."""
    out = {}
    for tok in (t.strip() for t in (text or "").split(",") if t.strip()):
        rel, _, nums = tok.partition(":")
        if not re.fullmatch(r"v?\d+\.\d+\.\d+", rel):
            return {}, f"--only with several releases takes release names (v2.3.2 or v2.3.2:1+2), not '{tok}'"
        rel = norm(rel)
        if rel not in avail:
            return {}, f"no hand checks for {rel} (have {', '.join(avail)})"
        out[rel] = {int(x) for x in nums.split("+") if x.isdigit()} or None
    return out, None


# ── the Product Manager's sheet ──────────────────────────────────────────────

def parse_sheet(text, own):
    """{release: {check number: its lines joined}} from a sheet's text. The checks under "## Checks" belong to the sheet's own
    release (`own`); a later "## v2.3.1 ..." section (a patch's checks, in the same sheet) belongs to that release. Other sections
    (Setup, Results) are skipped, so their numbered lists are not read as checks."""
    out, rel, cur = {}, None, None
    for line in text.splitlines():
        if line.startswith("## "):
            m = RELEASE_HEAD.match(line)
            rel = "v" + m.group(1) if m else own if line.strip().lower() == "## checks" else None
            cur = None
            continue
        if rel is None:
            continue
        m = NUMBERED.match(line)
        if m:
            cur = int(m.group(1))
            out.setdefault(rel, {})[cur] = line
        elif cur is not None and line.strip() and not line.startswith("#"):
            out[rel][cur] += "\n" + line
    return out


def tag_of(text):
    """"live" when a check's lines say live only, else "judgement" when they say judgement, else None."""
    return "live" if LIVE_ONLY.search(text) else "judgement" if JUDGEMENT.search(text) else None


def read_sheet(path_or_ref, repo=REPO):
    """The text of a sheet from a working-tree path, or from `git show <ref>:<path>` when given as (ref, relative path). None if absent."""
    if isinstance(path_or_ref, tuple):
        ref, rel = path_or_ref
        r = subprocess.run(["git", "show", f"{ref}:{rel}"], cwd=repo, capture_output=True, text=True)
        return r.stdout if r.returncode == 0 else None
    p = Path(path_or_ref)
    return p.read_text(encoding="utf-8") if p.exists() else None


def sheet_checks(v, refs=(), sheets=SHEETS, repo=REPO):
    """({check number: its lines} for release `v`, where it was read from) or (None, None) when no sheet has it. Looked for in the
    git refs `refs`, in order, when given (they win: a checkout's own sheet can be an older draft of the Product Manager's), then the
    working tree. For each, dev/handchecks/<v>.md, then the .0 sheet of the same minor release, whose patch sections may hold it."""
    v = norm(v)
    major_minor = ".".join(v[1:].split(".")[:2])
    names = [f"{v}.md"] + ([f"v{major_minor}.0.md"] if not v.endswith(".0") else [])
    for ref_ in (*refs, None):
        for name in names:
            text = read_sheet((ref_, f"dev/handchecks/{name}"), repo) if ref_ else read_sheet(Path(sheets) / name)
            if text:
                found = parse_sheet(text, name[:-3]).get(v)
                if found:
                    return found, (f"{ref_}:" if ref_ else "") + f"dev/handchecks/{name}"
    return None, None


# ── the test module ──────────────────────────────────────────────────────────

def scan_tests(path):
    """{check number: True when the test runs, False when it is marked phase2 (skipped)} from a module's `def test_cNN_...`."""
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    out = {}
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            m = TEST_NAME.match(fn.name)
            if m:
                marked = any("phase2" in ast.dump(d) for d in fn.decorator_list)
                n = int(m.group(1))
                out[n] = out.get(n, False) or not marked
    return out


def module_tags(mod):
    """{check number: "judgement" | "live"} from an imported module's KIND and LIVE_ONLY."""
    tags = {n: "judgement" for n, k in getattr(mod, "KIND", {}).items() if k == "judgement"}
    tags.update({n: "live" for n in getattr(mod, "LIVE_ONLY", {}) if isinstance(n, int)})
    return tags


def coverage(sheet, tests, mod_tags=None):
    """The sheet's checks sorted into: tested (a test runs for it), tagged (no test; "judgement" or "live" by the sheet or the
    module) and gaps (no test, no tag). Returns {"tested": [...], "judgement": [...], "live": [...], "gaps": [...]}."""
    out = {"tested": [], "judgement": [], "live": [], "gaps": []}
    for n in sorted(sheet):
        tag = (mod_tags or {}).get(n) or tag_of(sheet[n])
        if tests.get(n):
            out["tested"].append(n)
        elif tag:
            out[tag].append(n)
        else:
            out["gaps"].append(n)
    return out


# ── counts and the summary ───────────────────────────────────────────────────

def counts_of(outcomes, cov=None):
    """{"pass", "fail", "judgement", "live", "skipped"} from a run's outcomes {n: (status, note)}. When the sheet was read, a check
    with no test that the sheet tags judgement or live only is counted under that tag too."""
    c = dict.fromkeys(("pass", "fail", "judgement", "live", "skipped"), 0)
    for status, _ in outcomes.values():
        c[status if status in c else "skipped"] += 1
    if cov:
        c["judgement"] += len(cov["judgement"])
        c["live"] += len(cov["live"])
    return c


def one_line(note, width=110):
    """A reason on one line, cut to `width`, without the 'auto (kind): ' prefix."""
    s = " ".join(re.sub(r"[-=]{4,}", " ", str(note)).split())      # unittest's rules of dashes are not a reason
    s = re.sub(r"\b\w+\.py::", "", s)                                   # the test file; its test's name says enough
    s = re.sub(r"^auto \([a-z ]+\):\s*", "", s)
    return s if len(s) <= width else s[:width - 1] + "…"


def summary(v, outcomes, cov=None, seconds=None, error=None, sheet_src=None):
    """The one-screen summary of one release as a list of lines."""
    head = f"{v}  "
    if error:
        return [head + f"NOT RUN: {one_line(error, 100)}"]
    c = counts_of(outcomes, cov)
    took = f"  ({seconds / 60:.0f} min)" if seconds and seconds >= 90 else f"  ({seconds:.0f} s)" if seconds else ""
    lines = [head + f"pass {c['pass']}  fail {c['fail']}  judgement-only {c['judgement']}  live-only {c['live']}"
             + (f"  skipped {c['skipped']}" if c["skipped"] else "") + took]
    lines += [f"  FAIL {n}: {one_line(note)}" for n, (st, note) in sorted(outcomes.items()) if st == "fail"]
    lines += [f"  skipped {n}: {one_line(note, 70)}" for n, (st, note) in sorted(outcomes.items()) if st == "skip"][:3]
    lines += coverage_lines(cov, sheet_src)
    return lines


def coverage_lines(cov, sheet_src=None):
    """The coverage part of a summary: gaps, or that the sheet was not available."""
    if cov is None:
        return ["  coverage: no sheet in this checkout (use --sheets-ref to read one from a git ref)"]
    if cov["gaps"]:
        return [f"  GAP, no test and no tag: {', '.join(map(str, cov['gaps']))}  (sheet {Path(sheet_src or '').name or '?'})"]
    return ["  coverage: every sheet check has a test or is tagged judgement or live only"]


def table(rows):
    """One table for all releases. rows: [(release, counts dict or None, gap list or None, seconds, error)]."""
    out = [f"{'release':<9}{'pass':>5}{'fail':>6}{'judge':>7}{'live':>6}{'skip':>6}  gaps (no test, no tag)", "-" * 62]
    for v, c, gaps, secs, err in rows:
        if err or c is None:
            out.append(f"{v:<9}  not run: {one_line(err or '', 40)}")
            continue
        g = "sheet missing" if gaps is None else ", ".join(map(str, gaps)) or "none"
        out.append(f"{v:<9}{c['pass']:>5}{c['fail']:>6}{c['judgement']:>7}{c['live']:>6}{c['skipped']:>6}  {g}")
    return out


def list_lines(v, tests, cov, tags, sheet_src):
    """What `--list` prints for a release: no browser, nothing run. `tests` is scan_tests()'s answer, `cov` coverage()'s or None."""
    running = sorted(n for n, ok in tests.items() if ok)
    waiting = sorted(n for n, ok in tests.items() if not ok)
    lines = [f"{v}  {module_name(v)}.py: {len(running)} test(s) to run" + (f", {len(waiting)} marked phase 2" if waiting else "")
             + (f"; sheet {Path(sheet_src).name}: {sum(len(x) for x in (cov['tested'], cov['judgement'], cov['live'], cov['gaps']))} checks"
                if cov else "; no sheet in this checkout")]
    if tags:
        lines.append("  tagged in the module: " + ", ".join(f"check {n} {t}" for n, t in sorted(tags.items())))
    if cov:
        for key, label in (("judgement", "judgement-only, no test"), ("live", "live-only, no test")):
            if cov[key]:
                lines.append(f"  {label}: {', '.join(map(str, cov[key]))}")
    lines += coverage_lines(cov, sheet_src)
    return lines
