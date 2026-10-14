"""Build the dashboard page from its source, and split a page into pieces and join them back, byte for byte (BL-231).

Run: python3 dev/tools/split_dashboard.py build          rebuild system/templates/dashboard.html from its source
     python3 dev/tools/split_dashboard.py stale          exit 1 if dashboard.html is out of date with its source
     python3 dev/tools/split_dashboard.py split [--file PAGE] [--out DIR]
     python3 dev/tools/split_dashboard.py join [--dir DIR] [--out PAGE]
     python3 dev/tools/split_dashboard.py check [--file PAGE]

Since step 2a the dashboard's source is system/templates/dashboard/ (SRC): edit it there, then run `build`.
system/templates/dashboard.html is the generated page, committed so a release zip and a vault need no build step
(NFR-12); dev/tools/check.py fails when it is out of date with SRC. Never edit dashboard.html itself: `build`
overwrites it.

Since step 2b the app script is built, not joined: dev/tools/build_dashboard_js.py bundles src/main.js with the pinned
esbuild into one IIFE (see its docstring; script/ is gone, every area is a module). `build` puts the
shell, style.css and that script together. `split`, `join` and `check` are step 2a's tools and still work on any page.

A split is a move, not a rewrite: joining the pieces gives back exactly the bytes that were split (every newline, CRLF,
trailing space and the presence or absence of a final newline). Development only, standard library only; nothing in
system/ imports it. `split` and `join` default to dev/scratch-split/, which git ignores.

The pieces:
  shell.html       the page with the CSS replaced by CSS_SLOT and the app script by SCRIPT_SLOT
  style.css        the contents of the first <style> element
  script/NNNN-<slug>.js   the app script (the first inline <script> that has no src and is not application/json),
                   cut at its block markers, in today's order; NNNN numbers them so they sort
  manifest.json    the pieces in order (what `join` and, later, step 2a's build read)

Where the script is cut (exact offsets; no byte is added or removed):
  * An opening marker is a line that starts, in column 0, with `/* =====` and is not an end marker: a new piece starts
    at the start of that line. Section headers (`/* ======================= Today ===…`) are opening markers too.
  * An end marker (`/* ===== end … ===== */` in column 0) never starts a piece; it stays at the foot of the block it
    closes. If code follows it before the next opening marker (an outer block resuming after a nested one, or loose
    code after a closed block), that code becomes its own piece, `after-<slug of the end marker>`, cut at the start
    of the line after the end marker. Blank lines alone stay with the closed block. End markers are not matched to
    their openers: their labels don't reliably match, and the cut is the same either way.
  * Markers that are indented (inside a function) or in mid-line never cut.
  * Text before the first marker is its own piece, `start`; when the script begins with a marker there is none.
"""
import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PAGE = REPO / "system" / "templates" / "dashboard.html"
SRC = REPO / "system" / "templates" / "dashboard"       # step 2a: the page's source; dashboard.html is built from it
OUT = REPO / "dev" / "scratch-split"
REBUILD = "python3 dev/tools/split_dashboard.py build"
CSS_SLOT = "/*__SPLIT_CSS__*/"
SCRIPT_SLOT = "/*__SPLIT_SCRIPT__*/"
MANIFEST = "manifest.json"
OPEN_TAG = re.compile(r"<(script|style)\b([^>]*)>", re.I)
MARKER = re.compile(r"^/\* =====", re.M)
END = re.compile(r"/\* =====\s*end\b", re.I)


# ---------- the page: shell, CSS and app script ----------
def _close(html, name, start):
    """The offset of the `</name` that closes an element whose content starts at `start` (the HTML parser's rule)."""
    m = re.compile(r"</" + name + r"\s*>", re.I).search(html, start)
    if not m:
        raise ValueError(f"<{name}> at offset {start} is never closed")
    return m.start()


def is_app_script(attrs):
    """Whether a <script> tag's attributes describe the inline app script (no src, not a JSON data block)."""
    a = attrs.lower()
    return "src=" not in a and "application/json" not in a


def regions(html):
    """The (start, end) content offsets of the first <style> and the app <script>, skipping other elements' content."""
    css = app = None
    pos = 0
    while css is None or app is None:
        m = OPEN_TAG.search(html, pos)
        if not m:
            break
        name, start = m.group(1).lower(), m.end()
        end = _close(html, name, start)
        if name == "style" and css is None:
            css = (start, end)
        elif name == "script" and app is None and is_app_script(m.group(2)):
            app = (start, end)
        pos = end
    if css is None or app is None:
        raise ValueError("the page needs a <style> element and an inline app <script>")
    return css, app


# ---------- the script, cut at its markers ----------
def slug(line):
    """A short file-name slug from a marker line (`/* ===== BL-72 (x) ===== …` gives `bl-72-x`)."""
    label = line[2:].strip().strip("=").strip()
    label = re.split(r"=====|\*/", label)[0]
    s = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
    return s[:40].strip("-") or "block"


def _line_end(text, pos):
    """The offset just after the newline that ends the line at `pos` (or the end of `text`)."""
    nl = text.find("\n", pos)
    return len(text) if nl < 0 else nl + 1


def cuts(script):
    """The (offset, name) where each piece of the script starts, in order; the first is always offset 0."""
    found = [(0, "start")]
    marks = [m.start() for m in MARKER.finditer(script)]
    for i, pos in enumerate(marks):
        line = script[pos:_line_end(script, pos)]
        if not END.match(line):
            found.append((pos, slug(line)))
            continue
        after = _line_end(script, pos)
        nxt = marks[i + 1] if i + 1 < len(marks) else len(script)
        if script[after:nxt].strip():
            found.append((after, "after-" + slug(line).replace("end-", "", 1)))
    found = [c for k, c in enumerate(found) if k + 1 == len(found) or found[k + 1][0] != c[0]]
    return found


def cut_script(script):
    """The script as [(file name, text), …]: one piece per block, numbered so they sort, joined back by concatenation."""
    starts = cuts(script)
    bounds = [o for o, _ in starts[1:]] + [len(script)]
    return [(f"{n:04d}-{name}.js", script[o:e]) for n, ((o, name), e) in enumerate(zip(starts, bounds), 1)]


# ---------- split and join ----------
def split(html):
    """Cut a page into its pieces: {"shell": str, "css": str, "script": [(file name, text), …]}."""
    for slot in (CSS_SLOT, SCRIPT_SLOT):
        if slot in html:
            raise ValueError(f"the page already contains {slot}; it can't be split safely")
    (cs, ce), (ss, se) = regions(html)
    first, second = sorted([(cs, ce, CSS_SLOT), (ss, se, SCRIPT_SLOT)])
    shell = html[:first[0]] + first[2] + html[first[1]:second[0]] + second[2] + html[second[1]:]
    return {"shell": shell, "css": html[cs:ce], "script": cut_script(html[ss:se])}


def join(pieces):
    """Put a page back together from split()'s pieces; the result is byte-for-byte the page that was split."""
    script = "".join(text for _, text in pieces["script"])
    first = min(SCRIPT_SLOT, CSS_SLOT, key=pieces["shell"].index)
    second = CSS_SLOT if first == SCRIPT_SLOT else SCRIPT_SLOT
    fill = {CSS_SLOT: pieces["css"], SCRIPT_SLOT: script}
    head, rest = pieces["shell"].split(first, 1)
    middle, tail = rest.split(second, 1)
    return head + fill[first] + middle + fill[second] + tail


# ---------- the directory ----------
def _write(path, text):
    """Write `text` as UTF-8 bytes, so no newline is translated."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def _read(path):
    """Read a file as UTF-8 text without translating newlines."""
    return path.read_bytes().decode("utf-8")


def write_pieces(pieces, out):
    """Write split()'s pieces and the manifest into `out` (old script pieces there are removed first)."""
    for old in (out / "script").glob("*.js"):
        old.unlink()
    _write(out / "shell.html", pieces["shell"])
    _write(out / "style.css", pieces["css"])
    names = []
    for name, text in pieces["script"]:
        _write(out / "script" / name, text)
        names.append("script/" + name)
    manifest = {"about": "BL-231: the dashboard page's pieces, in order. dev/tools/split_dashboard.py build joins them "
                         "into system/templates/dashboard.html.",
                "shell": "shell.html", "css": "style.css", "css_slot": CSS_SLOT, "script_slot": SCRIPT_SLOT,
                "script": names}
    _write(out / MANIFEST, json.dumps(manifest, indent=1) + "\n")


def read_pieces(folder):
    """Read the pieces back from a directory written by write_pieces(), in the manifest's order."""
    manifest = json.loads(_read(folder / MANIFEST))
    script = [(Path(rel).name, _read(folder / rel)) for rel in manifest["script"]]
    return {"shell": _read(folder / manifest["shell"]), "css": _read(folder / manifest["css"]), "script": script}


# ---------- the source in system/templates/dashboard/ ----------
def built(folder=SRC):
    """The page built from the source in `folder` (the shell, the CSS and the bundled script), as UTF-8 bytes."""
    import build_dashboard_js
    manifest = json.loads(_read(folder / MANIFEST))
    pieces = {"shell": _read(folder / manifest["shell"]), "css": _read(folder / manifest["css"]),
              "script": [("app.js", build_dashboard_js.script(folder))]}
    return join(pieces).encode("utf-8")


def readable_page(folder=SRC):
    """The page as people wrote it: the shell and the CSS with the app script's source in place of the bundle (every
    module in src/), as text. For the tests that look for a piece of code in the page: the
    bundle is esbuild's reprint, with its own spacing and quotes and without comments. Never served or shipped."""
    import build_dashboard_js
    manifest = json.loads(_read(folder / MANIFEST))
    return join({"shell": _read(folder / manifest["shell"]), "css": _read(folder / manifest["css"]),
                 "script": [("source.js", build_dashboard_js.source_text(folder))]})


def stale(folder=SRC, page=PAGE):
    """Why `page` is out of date with its source in `folder` (a sentence), or '' when it is up to date or has no source."""
    if not (folder / MANIFEST).is_file():
        return ""
    import build_dashboard_js
    try:
        fresh = built(folder)
    except (build_dashboard_js.BuildError, build_dashboard_js.esbuild.EsbuildError, OSError) as e:
        return f"{page.name} could not be checked against its source: the build failed ({e})"
    if not page.is_file() or page.read_bytes() != fresh:
        shown = folder.relative_to(REPO).as_posix() if REPO in folder.parents else str(folder)
        return (f"{page.name} is out of date with its source in {shown}/: edit the "
                f"source there, then rebuild with: {REBUILD}")
    return ""


def cmd_build(folder, page):
    """Join the source in `folder` into `page` (written only when it changes)."""
    data = built(folder)
    if page.is_file() and page.read_bytes() == data:
        print(f"{page.name} is up to date.")
        return 0
    page.write_bytes(data)
    print(f"Built {page.name} from {folder.name}/.")
    return 0


# ---------- command line ----------
def cmd_split(page, out):
    """Split `page` into `out` and say how many pieces it made."""
    pieces = split(_read(page))
    write_pieces(pieces, out)
    print(f"Split {page.name} into {out}: shell, CSS and {len(pieces['script'])} script pieces.")
    return 0


def cmd_join(folder, out):
    """Join the pieces in `folder` into the page `out`."""
    _write(out, join(read_pieces(folder)))
    print(f"Joined {folder} into {out}.")
    return 0


def cmd_check(page):
    """Split `page` into a temporary directory, join it back and say whether the bytes match (exit 1 if not)."""
    original = page.read_bytes()
    with tempfile.TemporaryDirectory() as tmp:
        write_pieces(split(original.decode("utf-8")), Path(tmp))
        same = join(read_pieces(Path(tmp))).encode("utf-8") == original
    print(f"{page.name}: the joined page is {'identical' if same else 'DIFFERENT'}.")
    return 0 if same else 1


def main(argv):
    """Parse the command line and run build, stale, split, join or check."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("split")
    s.add_argument("--file", type=Path, default=PAGE)
    s.add_argument("--out", type=Path, default=OUT)
    j = sub.add_parser("join")
    j.add_argument("--dir", type=Path, default=OUT)
    j.add_argument("--out", type=Path, default=None, help="default: DIR/dashboard.html")
    c = sub.add_parser("check")
    c.add_argument("--file", type=Path, default=PAGE)
    sub.add_parser("build")
    sub.add_parser("stale")
    a = ap.parse_args(argv)
    if a.cmd == "build":
        return cmd_build(SRC, PAGE)
    if a.cmd == "stale":
        why = stale()
        print(why or f"{PAGE.name} is up to date.")
        return 1 if why else 0
    if a.cmd == "split":
        return cmd_split(a.file, a.out)
    if a.cmd == "join":
        return cmd_join(a.dir, a.out or a.dir / "dashboard.html")
    return cmd_check(a.file)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
