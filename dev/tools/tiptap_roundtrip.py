"""BL-301 part A's gate: Tiptap's Markdown gives back every text creaite will put in it, byte for byte (development only).

Run: python3 dev/tools/tiptap_roundtrip.py [--json] [--upstream] [--group current|minutes|constructs|hard|stable]
       [--vault DIR] [--private]

Each text is loaded into the pinned Tiptap editor (dev/tools/tiptap.py's bundle of dev/tiptap/editor.js) with
`contentType: "markdown"` and saved again by creaite's exact writer (dev/tiptap/writer.js, with the forms source.js keeps),
in headless Chrome (dev/tools/cdp.py: Tiptap needs a DOM). A case passes when what comes back is the same bytes as what
went in (or, for a hard case with an `expect`, exactly that: a known loss, written down so a change shows). Exits 1 if
any case fails, and if the bundle's Tiptap isn't the version tiptap.py pins. `--upstream` saves with Tiptap's own
getMarkdown() instead, for comparison.

The texts, in four groups:
  current     every Current state in the sample vault, as the dashboard's editor receives it: each project's CLAUDE.md
              (the repo's projects/, the four demo projects of dev/tools/demo_data.py written as `load` writes them, and
              the project memory template), its `## Current state` section read by build_dashboard.memory (guidance
              lines dropped, docx_tools.md_normalise), then split into its two panes (BL-89), each pane one case
  fixtures    every Current state in the test fixtures (BL-301 A's gate, "the sample vault and every fixture"): each
              string literal in dev/tests/*.py that holds a "## Current state" section, and each CLAUDE.md under
              dev/tests, read as build_dashboard.memory reads a project's file and split into its panes
  minutes     every text in the sample minutes values (a dict with a "SUMMARY" key in demo_data.py and the minutes
              fixtures in dev/tests): summary paragraphs, update headings and lines, decisions, risks, action texts
  constructs  one case per Markdown form creaite's Current state stores (md_normalise's output: bold, italic, strike,
              links, headings, quotes, nested and numbered lists, images), so a failure names the construct
  hard        dev/tiptap/hard-cases.json: the awkward forms (tables, nested lists, links with brackets, HTML comments
              such as BL-89's pane marker, trailing spaces, Windows line ends, escapes, entities), each with why
  stable      dev/tiptap/stable-cases.json: the notes gate (BL-301, Alan 13-10-2026: Notes use Tiptap's own table and
              checklist form, gated on idempotence). Each case types a table or a checklist through the editor's own
              commands (insertTable, goToNextCell, toggleTaskList, sinkListItem...), saves it, loads what was saved and
              saves again, twice: it passes when the three saves are the same bytes, every save is faithful, and the
              first holds the forms the case names (`contains`). A known loss (`unfaithful`) must be stable and the
              writer must say it can't write it (faithful: false)
Nothing in system/ imports this file, and it changes nothing in system/.

Real data (BL-301, Alan 13-10-2026): `--vault DIR` reads the current group from that vault instead of the sample (each
project's Current state, read as build_dashboard.memory reads it, split into its panes; the projects folder found through
that vault's own settings.json `locations`, as paths.py finds it). It only reads: no file is written, nothing is fetched,
images aren't opened. With `--vault` the default group is current only. `--private` prints no text from the cases: each
case is an id (`ABC pane 1`), pass or fail, its length in bytes and, for a failure, the byte offset of the first
difference, the Markdown construct there and a classification ("escaped `&`", "list indent"); `--json` keeps that rule.
The texts go to headless Chrome in memory (CDP), never to a file.
"""
import argparse
import ast
import contextlib
import json
import re
import string
import sys
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "system" / "scripts"))
import build_dashboard  # noqa: E402
import cdp  # noqa: E402
import demo_data  # noqa: E402
import docx_tools  # noqa: E402
import paths  # noqa: E402
import tiptap  # noqa: E402

MINUTES_SOURCES = ("dev/tools/demo_data.py", "dev/tests/test_minutes_review.py")
HARD_CASES = REPO / "dev" / "tiptap" / "hard-cases.json"
STABLE_CASES = REPO / "dev" / "tiptap" / "stable-cases.json"
GROUPS = ("current", "fixtures", "minutes", "constructs", "hard", "stable")
FIXTURES = REPO / "dev" / "tests"
TEMPLATE = REPO / "system" / "templates" / "project-CLAUDE-template.md"
CONSTRUCTS = (
    ("plain paragraph", "Build is complete for two of three data domains."),
    ("two paragraphs", "First paragraph.\n\nSecond paragraph."),
    ("bold", "Go-live is **at risk** this week."),
    ("italic with stars", "The date is *provisional* for now."),
    ("italic with underscores", "The date is _provisional_ for now."),
    ("strike", "Go-live ~~20 November~~ 11 December."),
    ("link", "See the [plan](https://example.com/plan) for dates."),
    ("heading", "### Next steps"),
    ("quote", "> The sponsor asked for a weekly check-in."),
    ("bullet list", "- Data access is late\n- UAT starts next week"),
    ("nested list", "- Data access\n  - Production is late\n  - Masked data meanwhile\n- UAT"),
    ("numbered list", "1. Escalate to the sponsor\n2. Re-plan UAT"),
    ("image", "![Delivery plan](images/plan.png)"),
    ("numbered list nested", "1. Escalate\n  1. Sponsor first"),
    ("bold italic", "***Both*** at once."),
    ("inline code", "Run `doctor.py` first."),
    ("bare URL", "See https://example.com/plan for dates."),
    ("underscores in a word", "The file is weekly_report_v2.docx."),
    ("ampersand", "Q&A on R&D, and data access delayed → MVP slips."),
    ("less-than and greater-than", "Budget < plan; target > 8%."),
    ("lone asterisk", "Cost is £40k (+10%) — see #3 and ABC-A-003 * maybe."),
    ("HTML comment", "<!-- a note to the next writer -->\n\nText."),
)
# Notes only (BL-301 B: Notes switch everything on); stored as written, not through md_normalise (it has no tables).
NOTES_CONSTRUCTS = (
    ("checklist", "- [ ] Send the SOW\n- [x] Book UAT"),
    ("table", "| Name | Role |\n| --- | --- |\n| Sara Khan | Sponsor |"),
    ("wiki link and mention", "Met [[Stakeholder map]] with @Sara Khan about #ABC-A-003."),
)


@dataclass
class Case:
    """One text for the gate: its group, where it came from, the text and the editor's feature set. With `html`, the
    text is HTML (content typed into the editor, so it has no written form) and `expect` the Markdown it must give."""
    group: str
    source: str
    text: str
    features: str = "current"
    expect: str = None          # what must come back, when it isn't `text` (a known loss); None: `text` itself
    html: bool = False
    script: bool = False        # the notes gate: `text` is JavaScript typing into `editor` (the stable group)
    contains: tuple = ()        # the stable group: forms the first save must hold
    unfaithful: bool = False    # the stable group: a known loss, which the writer must report (faithful: false)

    @property
    def wanted(self):
        """The bytes this case must give back."""
        return self.text if self.expect is None else self.expect


def label(path):
    """`path` relative to the repository when it is inside it (for the report), else as given."""
    try:
        return str(Path(path).resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def _panes(source, folder):
    """The Current state cases of one project folder: each non-empty pane of what the dashboard's editor receives."""
    current = build_dashboard.memory(folder)["current"]
    left, right = docx_tools.split_panes(current)
    return [Case("current", f"{source} ({name} pane)", text) for name, text in (("left", left), ("right", right)) if text]


def _demo_memory(p):
    """A demo project's CLAUDE.md exactly as `demo_data.py load` writes it."""
    return (f"# {p['code']} — {p['name']} (demo, fictional)\n\n## Brief\n\n- **Client / partner:** {p['client']}\n"
            f"- **Client report rhythm:** {p['rhythm']}\n\n## Current state\n\n{p['current']}\n")


def current_cases(projects_root=REPO / "projects", demo=True):
    """Every Current state in the sample vault, one case per pane (see the module's docstring). `demo`: include the
    demo projects and the template (a test passes False to read only its own folder)."""
    out = []
    for memory in sorted(projects_root.glob("*/CLAUDE.md")):
        out += _panes(label(memory), memory.parent)
    if not demo:
        return out
    with tempfile.TemporaryDirectory() as tmp:
        for p in demo_data.PROJECTS:
            folder = Path(tmp) / p["code"]
            folder.mkdir()
            (folder / "CLAUDE.md").write_text(_demo_memory(p), encoding="utf-8")
            out += _panes(f"demo_data.py {p['code']}", folder)
        folder = Path(tmp) / "template"
        folder.mkdir()
        (folder / "CLAUDE.md").write_text(TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")
        out += _panes(label(TEMPLATE), folder)
    return out


def fixture_cases(folder=FIXTURES):
    """The fixtures group: every test fixture's Current state, one case per pane. A string literal (not an f-string,
    whose text is built at run time) in a test file counts when it holds a `## Current state` heading; it is read as a
    project's CLAUDE.md. Identical texts are run once."""
    texts = {}
    for path in sorted(Path(folder).glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and re.search(r"^## Current state", node.value, re.M):
                texts.setdefault(node.value, f"{label(path)}:{node.lineno}")
    for path in sorted(Path(folder).rglob("CLAUDE.md")):
        texts.setdefault(path.read_text(encoding="utf-8"), label(path))
    out = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, (text, source) in enumerate(texts.items()):
            sub = Path(tmp) / str(i)
            sub.mkdir()
            (sub / "CLAUDE.md").write_text(text, encoding="utf-8")
            saved = build_dashboard.embed_image
            build_dashboard.embed_image = lambda folder, alt, ref: None     # the text is all the gate needs
            try:
                out += [replace(c, group="fixtures") for c in _panes(source, sub)]
            finally:
                build_dashboard.embed_image = saved
    return out


def _strings(value):
    """Every non-empty string in a minutes value (a string, a list, or a dict's text-like values)."""
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [s for v in value for s in _strings(v)]
    if isinstance(value, dict):
        return [s for k, v in value.items() if k != "flag" for s in _strings(v)]
    return []


def minutes_cases(sources=MINUTES_SOURCES):
    """Every text in each dict literal with a "SUMMARY" key in `sources` (the values a minutes Word file is filled from).
    A value that isn't a literal (built from a variable) is skipped."""
    out = []
    for rel in sources:
        tree = ast.parse((REPO / rel).read_text(encoding="utf-8"))
        rel = label(REPO / rel)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue
            keys = [k.value for k in node.keys if isinstance(k, ast.Constant)]
            if "SUMMARY" not in keys:
                continue
            for k, v in zip(node.keys, node.values):
                try:
                    value = ast.literal_eval(v)
                except ValueError:              # built from a variable (demo_data's title): not a literal text
                    continue
                for i, s in enumerate(_strings(value)):
                    out.append(Case("minutes", f"{rel}:{node.lineno} {k.value}[{i}]", s))
    return out


def construct_cases():
    """One case per Markdown form creaite stores, in md_normalise's canonical form."""
    return ([Case("constructs", name, docx_tools.md_normalise(text)) for name, text in CONSTRUCTS]
            + [Case("constructs", f"{name} (notes)", text, "notes") for name, text in NOTES_CONSTRUCTS])


def hard_cases(path=HARD_CASES):
    """The hard cases: [{name, features, text | html, expect?, why}] in a JSON file (JSON keeps CRLF and trailing
    spaces). A case with `html` is typed content: `expect` is the Markdown creaite's style gives it."""
    out = []
    for c in json.loads(Path(path).read_text(encoding="utf-8")):
        features = c.get("features", "current")
        name = c["name"] + ("" if features == "current" else f" ({features})")
        if "html" in c:
            out.append(Case("hard", name, c["html"], features, c["expect"], html=True))
        else:
            out.append(Case("hard", name, c["text"], features, c.get("expect")))
    return out


def stable_cases(path=STABLE_CASES):
    """The notes gate's cases: [{name, features, script, contains, unfaithful?, why}] in a JSON file. `script` is the
    body of a function given `editor` (an empty editor with those features) that types the content."""
    return [Case("stable", c["name"] + ("" if c.get("features", "notes") == "current" else f" ({c.get('features', 'notes')})"),
                 c["script"], c.get("features", "notes"), script=True, contains=tuple(c.get("contains", ())),
                 unfaithful=bool(c.get("unfaithful")))
            for c in json.loads(Path(path).read_text(encoding="utf-8"))]


@contextlib.contextmanager
def _vault(vault):
    """paths pointed at another vault (its root and its settings.json) for the block, and build_dashboard's image reader
    off (the text is all the gate needs; nothing else is opened, and its notes would print vault paths). Read-only:
    paths' locations, register and folder listing only read. Both are put back afterwards."""
    saved = paths.ROOT, paths.SETTINGS, build_dashboard.embed_image
    paths.ROOT = Path(vault)
    paths.SETTINGS = Path(vault) / "system" / "config" / "settings.json"
    build_dashboard.embed_image = lambda folder, alt, ref: None
    try:
        yield
    finally:
        paths.ROOT, paths.SETTINGS, build_dashboard.embed_image = saved


def vault_cases(vault):
    """The current group from a real vault: each project's Current state (build_dashboard.memory, split_panes), one case
    per non-empty pane, its id the project code and pane number (`ABC pane 1`). Raises RuntimeError naming no vault
    text when the vault or its projects folder can't be read."""
    vault = Path(vault).expanduser().resolve()
    if not vault.is_dir():
        raise RuntimeError("--vault: not a folder")
    out = []
    with _vault(vault):
        if not paths.projects_root().is_dir():
            raise RuntimeError("--vault: the projects folder (locations.projects_root) was not found")
        for code, folder in paths.project_folders():
            if code == "_portfolio":
                continue
            try:
                current = build_dashboard.memory(folder)["current"]
            except Exception as e:                  # an unreadable file: its message could quote the text
                raise RuntimeError(f"--vault: {code}: CLAUDE.md could not be read ({type(e).__name__})") from None
            out += [Case("current", f"{code} pane {n}", text)
                    for n, text in enumerate(docx_tools.split_panes(current), 1) if text]
    return out


def corpus(groups=GROUPS):
    """All the cases of the named groups, in order."""
    make = {"current": current_cases, "fixtures": fixture_cases, "minutes": minutes_cases, "constructs": construct_cases,
            "hard": hard_cases, "stable": stable_cases}
    return [c for g in groups for c in make[g]()]


PAGE = '<!doctype html><meta charset="utf-8"><title>tiptap round-trip</title><body><script>{js}</script>'


UNFAITHFUL = "the writer can't write this document so that it reads back the same (faithful: false)"


class VersionError(Exception):
    """The bundle's Tiptap isn't the pinned one: the gate's result would not be about the version creaite ships."""


# The notes gate (stable group): type, save, then load and save twice. Upstream's saves have no faithfulness (null).
STABLE_JS = """((cases, mode) => cases.map(([features, src]) => {
  const T = CreaiteTiptap;
  try {
    const ed = T.createEditor(null, { features });
    new Function("editor", src)(ed);
    const first = mode === "upstream" ? { markdown: ed.getMarkdown(), faithful: null } : T.markdownOf(ed);
    ed.destroy();
    const second = T.roundTrip(first.markdown, features, mode);
    const third = T.roundTrip(second.markdown, features, mode);
    return { saves: [first.markdown, second.markdown, third.markdown], faithful: [first, second, third].map((r) => r.faithful) };
  } catch (e) { return { error: String((e && e.message) || e) }; }
}))(%s, %s)"""
UNSTABLE_KNOWN = "a known loss the writer no longer reports (expected faithful: false): update stable-cases.json"


def stable_result(case, r, mode="exact"):
    """(case with `expect` set to its first save, the save that differs from it or the last, error) for one stable case's
    browser result `r`: the gate's normal pass rule (no error, out == wanted) then means "stable". `contains` holds
    creaite's style, so it is checked only for the exact writer (`--upstream` judges stability alone)."""
    if "error" in r:
        return case, None, r["error"]
    saves, faithful = r["saves"], r["faithful"]
    out = next((s for s in saves[1:] if s != saves[0]), saves[-1])
    error = None
    if case.unfaithful:
        error = None if faithful[0] in (False, None) else UNSTABLE_KNOWN
    elif False in faithful:
        error = UNFAITHFUL
    missing = sum(1 for needle in case.contains if needle not in saves[0]) if mode == "exact" else 0
    if error is None and missing:
        error = f"the first save lacks {missing} of the {len(case.contains)} forms the case names"
    return replace(case, expect=saves[0]), out, error


def _run_stable(b, cases, idx, mode):
    """[(i, result)] for the stable cases at `idx`, in the open page `b`."""
    if not idx:
        return []
    got = b.eval(STABLE_JS % (json.dumps([[cases[i].features, cases[i].text] for i in idx]), json.dumps(mode)))
    return [(i, stable_result(cases[i], r, mode)) for i, r in zip(idx, got)]


def vendored_js(path=tiptap.VENDOR / tiptap.MODULE):
    """The committed vendored module (what the dashboard bundles, BL-301 A) as a classic script that sets
    window.CreaiteTiptap: its closing `export{a as b,…}` becomes an object of the same names. Needs no cache and no
    network, so the gate runs on exactly what ships."""
    text = Path(path).read_text(encoding="utf-8")
    m = re.search(r"export\{([^}]*)\};?\s*$", text)
    if not m:
        raise ValueError(f"{label(path)}: no export list at its end")
    pairs = [part.strip().split(" as ") for part in m.group(1).split(",") if part.strip()]
    names = ",".join(f"{p[-1]}:{p[0]}" for p in pairs)
    return "(()=>{" + text[:m.start()] + f"window.CreaiteTiptap={{{names}}};}})();"


def run(cases, bundle_js, mode="exact", pinned=None):
    """[(case, out, error)] for each case: the text the editor gives back (or the error), from one headless Chrome page
    that loads `bundle_js` (it must set window.CreaiteTiptap.roundTripAll(texts, features, mode)). `mode`: "exact"
    (creaite's writer) or "upstream" (Tiptap's getMarkdown). `pinned`: the version the bundle must report
    (CreaiteTiptap.PINNED), else VersionError."""
    results = [None] * len(cases)
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "roundtrip.html"
        page.write_text(PAGE.format(js=bundle_js.replace("</script", "<\\/script")), encoding="utf-8")
        with cdp.Browser() as b:
            b.goto(page.as_uri(), wait_for="!!window.CreaiteTiptap")
            if pinned is not None:
                got = b.eval("CreaiteTiptap.PINNED || null")
                if got != pinned:
                    raise VersionError(f"the bundle is Tiptap {got}, the gate is pinned to {pinned}: re-run the gate "
                                       "on the new version and re-check dev/tiptap/source.js and writer.js")
            for i, result in _run_stable(b, cases, [i for i, c in enumerate(cases) if c.script], mode):
                results[i] = result
            for features, html in sorted({(c.features, c.html) for c in cases if not c.script}):
                idx = [i for i, c in enumerate(cases) if (c.features, c.html) == (features, html) and not c.script]
                got = b.eval(f"CreaiteTiptap.roundTripAll({json.dumps([cases[i].text for i in idx])}, "
                             f"{json.dumps(features)}, {json.dumps(mode)}, {json.dumps(html)})")
                for i, r in zip(idx, got):
                    unfaithful = r.get("faithful") is False and UNFAITHFUL   # the writer's own check (exact only)
                    results[i] = (cases[i], r.get("out"), r.get("error") or unfaithful or None)
    return results


def first_difference(a, b):
    """A short description of where `b` first differs from `a`: the offset and a few characters of each."""
    n = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
    return f"at {n}: in {a[max(0, n - 12):n + 20]!r} out {b[max(0, n - 12):n + 20]!r}"


# ── --private: where and how a case differs, with no text from it ──────────────────────────────────────────────────

INLINE = (("image", r"!\[[^\]]*\]\([^)]*\)"), ("link", r"\[[^\]]*\]\([^)]*\)"), ("inline code", r"`[^`]*`"),
          ("bold", r"\*\*.+?\*\*|__.+?__"), ("strike", r"~~.+?~~"), ("italic", r"\*[^*\n]+\*|_[^_\n]+_"),
          ("bare URL", r"https?://\S+"))


def _sym(c):
    """A character as the report may show it: ASCII punctuation (Markdown's own symbols) as itself, anything else only
    by its kind, so no letter, digit or word of the text is ever printed."""
    if c in string.punctuation:
        return f"`{c}`"
    if c == "":
        return "end of text"
    return {" ": "space", "\t": "tab", "\n": "line break"}.get(c, "a letter or digit" if c.isalnum() else "another character")


def construct_at(text, n):
    """The Markdown construct at character `n` of `text`: its block (heading, list item, quote, ...) and, if any, the
    inline form around it."""
    opened = text.rfind("<!--", 0, n + 4)
    closed = text.find("-->", opened) if opened >= 0 else -1
    if opened >= 0 and (closed < 0 or closed + 3 > n):
        return "HTML comment"
    start = text.rfind("\n", 0, n) + 1
    end = text.find("\n", n)
    line = text[start:] if end < 0 else text[start:end]
    indent = len(line) - len(line.lstrip(" "))
    nested = " (nested)" if indent else ""
    blocks = ((r"#{1,6} ", "heading"), (r" *>", "quote"), (r" *[-*+] \[[ xX]\] ", "checklist item" + nested),
              (r" *[-*+] ", "bullet list item" + nested), (r" *\d+[.)] ", "numbered list item" + nested),
              (r" *\|", "table row"), (r" *$", "blank line"))
    block = next((name for rx, name in blocks if re.match(rx, line)), "paragraph")
    col = n - start
    inline = next((name for name, rx in INLINE for m in re.finditer(rx, line) if m.start() <= col < m.end()), "")
    return f"{block}, {inline}" if inline else block


ENTITIES = (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'"))


def _entity(a, b, n):
    """(where it starts, kind) when the difference at `n` is a character written as an HTML entity; else None."""
    for ent, ch in ENTITIES:
        k = next((k for k in range(max(0, n - len(ent) + 1), n + 1) if b.startswith(ent, k) and a.startswith(ch, k)
                  and not a.startswith(ent, k)), None)
        if k is not None:
            return k, f"escaped `{ch}` (written as an entity)"
    return None


def _emphasis(a, n, ca, cb):
    """"italic `_` vs `*`" (or bold, bold italic) by how many of the marker start at `n`."""
    run = len(a[n:]) - len(a[n:].lstrip(ca))
    return f"{ {1: 'italic', 2: 'bold'}.get(run, 'bold italic')} `{ca}` vs `{cb}`"


def _is_space(c):
    """A space or a tab."""
    return c != "" and c in " \t"


def _at_line_end(t, n):
    """Only spaces or tabs from `n` to the end of the line."""
    return t[n:].lstrip(" \t")[:1] in ("\n", "")


def _in_list_indent(a, n):
    """`n` is in the leading space of a list item's line."""
    start = a.rfind("\n", 0, n) + 1
    return not a[start:n].strip() and re.match(r"[ \t]*([-*+]|\d+[.)]) ", a[start:]) is not None


# (test, kind) in order; the first true one names the change. Each test gets (a, b, n, ca, cb).
KINDS = (
    (lambda a, b, n, ca, cb: construct_at(a, n) == "HTML comment", lambda a, b, n, ca, cb: "HTML comment changed or dropped"),
    (lambda a, b, n, ca, cb: not cb, lambda a, b, n, ca, cb: "text dropped at the end"),
    (lambda a, b, n, ca, cb: not ca, lambda a, b, n, ca, cb: "text added at the end"),
    (lambda a, b, n, ca, cb: cb == "\\" != ca, lambda a, b, n, ca, cb: f"escaped {_sym(ca)} (backslash added)"),
    (lambda a, b, n, ca, cb: ca == "\\" != cb, lambda a, b, n, ca, cb: f"backslash dropped before {_sym(a[n + 1:n + 2])}"),
    (lambda a, b, n, ca, cb: ca in "*_" and cb in "*_", lambda a, b, n, ca, cb: _emphasis(a, n, ca, cb)),
    (lambda a, b, n, ca, cb: (_is_space(ca) or _is_space(cb)) and _in_list_indent(a, n),
     lambda a, b, n, ca, cb: "list indent"),
    (lambda a, b, n, ca, cb: _is_space(ca) and _at_line_end(a, n), lambda a, b, n, ca, cb: "trailing space dropped"),
    (lambda a, b, n, ca, cb: _is_space(cb) and _at_line_end(b, n), lambda a, b, n, ca, cb: "trailing space added"),
    (lambda a, b, n, ca, cb: "\n" in (ca, cb), lambda a, b, n, ca, cb: "line break or blank line"),
    (lambda a, b, n, ca, cb: cb == "[" and re.match(r"https?://|www\.", a[n:]) is not None,
     lambda a, b, n, ca, cb: "bare URL written as a link"),
    (lambda a, b, n, ca, cb: _is_space(ca) or _is_space(cb), lambda a, b, n, ca, cb: "spacing"),
    (lambda a, b, n, ca, cb: True, lambda a, b, n, ca, cb: f"{_sym(ca)} became {_sym(cb)}"),
)


def classify(a, b):
    """(byte offset in `a`, construct, kind) of where `b` first differs from `a`; None when they are equal. The kind names
    the change ("escaped `&`", "italic `_` vs `*`", "list indent", "trailing space", ...) without quoting the text."""
    if a == b:
        return None
    n = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
    found = _entity(a, b, n)
    if found:
        n, kind = found
    else:
        ca, cb = a[n:n + 1], b[n:n + 1]
        kind = next(name(a, b, n, ca, cb) for test, name in KINDS if test(a, b, n, ca, cb))
    return len(a[:n].encode("utf-8")), construct_at(a, n), kind


def private_rows(results):
    """One dict per case with no text in it: id, group, pass, bytes in and out, and for a failure where and why."""
    out = []
    for case, got, error in results:
        ok = error is None and got == case.wanted
        row = {"id": case.source, "group": case.group, "pass": ok, "bytes": len(case.text.encode("utf-8"))}
        if error is not None:
            row["error"] = "editor error"           # the browser's message could quote the text
        elif not ok:
            offset, construct, kind = classify(case.wanted, got or "")
            row.update({"out_bytes": len((got or "").encode("utf-8")), "byte_offset": offset, "construct": construct,
                        "kind": kind})
        out.append(row)
    return out


def private_report(results):
    """(lines of text, number failed), like report() but with no text from any case."""
    lines, by_group = [], {}
    for r in private_rows(results):
        g = by_group.setdefault(r["group"], [0, 0])
        g[0] += r["pass"]
        g[1] += 1
        why = ("" if r["pass"] else f"  {r['error']}" if "error" in r else
               f" -> {r['out_bytes']}  at byte {r['byte_offset']}: {r['construct']}: {r['kind']}")
        lines.append(f"{'PASS' if r['pass'] else 'FAIL'} [{r['group']}] {r['id']}  {r['bytes']} bytes{why}")
    failed = sum(n - p for p, n in by_group.values())
    lines.append("round-trip: " + ", ".join(f"{g} {p}/{n} pass" for g, (p, n) in by_group.items())
                 + f"; {failed} failed")
    return lines, failed


def report(results):
    """(lines of text, number failed)."""
    lines, failed = [], 0
    for case, out, error in results:
        ok = error is None and out == case.wanted
        failed += not ok
        why = "" if ok else (f"  error: {error}" if error else f"  {first_difference(case.wanted, out)}")
        lines.append(f"{'PASS' if ok else 'FAIL'} [{case.group}] {case.source}{why}")
    by_group = {}
    for case, out, error in results:
        g = by_group.setdefault(case.group, [0, 0])
        g[0] += error is None and out == case.wanted
        g[1] += 1
    lines.append("round-trip: " + ", ".join(f"{g} {p}/{n} pass" for g, (p, n) in by_group.items())
                 + f"; {failed} failed")
    return lines, failed


def _cases(groups, vault):
    """The cases to run: the named groups (default all; current only with a vault), the current group from `vault`
    when given."""
    groups = tuple(groups or (("current",) if vault else GROUPS))
    if not vault:
        return corpus(groups)
    real = vault_cases(vault)
    return [c for g in groups for c in (real if g == "current" else corpus((g,)))]


def _print_private(results, as_json):
    """Print the --private report (or its JSON); 1 if any case failed, else 0."""
    if as_json:
        print(json.dumps(private_rows(results), indent=1))
        return 0 if all(e is None and o == c.wanted for c, o, e in results) else 1
    lines, failed = private_report(results)
    print("\n".join(lines))
    return 1 if failed else 0


def main(argv=None):
    """Command line: run the gate and print one line per case; exit 1 if any case fails."""
    ap = argparse.ArgumentParser(description="BL-301's Tiptap Markdown round-trip gate (development only).")
    ap.add_argument("--group", action="append", choices=GROUPS)
    ap.add_argument("--json", action="store_true", help="print every case with its text and what came back")
    ap.add_argument("--upstream", action="store_true", help="save with Tiptap's own getMarkdown(), not creaite's writer")
    ap.add_argument("--exact", action="store_true", help="creaite's exact writer: the default (kept so older command "
                                                         "lines still work)")
    ap.add_argument("--vault", metavar="DIR", help="read the current group from this vault (read-only); default group: current")
    ap.add_argument("--vendored", action="store_true", help="run the committed system/templates/vendor/tiptap/ module "
                                                            "(what the dashboard ships; no cache needed), not a fresh build")
    ap.add_argument("--private", action="store_true", help="print no text from the cases: ids, pass or fail, lengths, "
                                                           "and where and how a failure differs")
    a = ap.parse_args(argv)
    try:
        cases = _cases(a.group, a.vault)
    except RuntimeError as e:
        print(e, file=sys.stderr)
        return 2
    try:
        js = vendored_js() if a.vendored else tiptap.bundle().decode("utf-8")
        results = run(cases, js, "upstream" if a.upstream else "exact", tiptap.PINNED)
    except VersionError as e:
        print(f"round-trip: {e}", file=sys.stderr)
        return 1
    if a.private:
        return _print_private(results, a.json)
    if a.json:
        print(json.dumps([{"group": c.group, "source": c.source, "in": c.text, "want": c.wanted, "out": o, "error": e}
                          for c, o, e in results], indent=1, ensure_ascii=False))
        return 0 if all(e is None and o == c.wanted for c, o, e in results) else 1
    lines, failed = report(results)
    print("\n".join(lines))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
