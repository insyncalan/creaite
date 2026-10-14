#!/usr/bin/env python3
"""Outline the Stage wordmark (BL-273): "creaite" in IBM Plex Mono SemiBold (600) as SVG paths (development only).

Run: python3 dev/tools/outline_wordmark.py [--zip FILE]

Needs fontTools (`pip install fonttools`, development only: nothing in system/ may depend on it, rule of 11-10-2026) and,
without --zip, the internet. It downloads IBM Plex Mono from IBM's own GitHub release (pinned below), checks the zip's
SHA-256, reads the SemiBold TTF from it in memory and never saves the font. --zip uses a copy already downloaded, checked
the same way.

Writes dev/reference/logo/wordmark-paths.json (one path per letter, the whole word, the view box, advance and metrics) and
dev/reference/logo/wordmark-preview.svg, laid out as the rail draws it (BL-308): the solid word and the saffron bar, with no
dashed draft copy, cropped to them. Colours are theme tokens (var(--ink), var(--accent)), never hex,
so the page's theme decides them. The page ships the paths, not the font: it loads no fonts and works offline.
IBM Plex is under the SIL Open Font License 1.1 (dev/reference/logo/OFL.txt).
"""
import argparse
import hashlib
import io
import json
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "dev" / "reference" / "logo"
TEXT = "creaite"
RELEASE = "@ibm/plex-mono@1.1.0"
URL = "https://github.com/IBM/plex/releases/download/%40ibm/plex-mono%401.1.0/ibm-plex-mono.zip"
SHA256 = "4bfc936d0e1fd19db6327a3786eabdbc3dc0d464500576f6458f6706df68d26c"
MEMBER = "ibm-plex-mono/fonts/complete/ttf/IBMPlexMono-SemiBold.ttf"
# The Short-Stage board's final art (dev/reference/logo/canvas/Short-Stage.dc.html), in its own 330 x 96 units, without the
# dashed draft copy (BL-308, Alan, 13-10-2026) and cropped to the word and the bar, as the rail's view box
ART = {"viewBox": [7, 25, 306, 60], "size": 62, "tracking": -2,
       "word": {"x": 4, "y": 74},
       "bar": {"x": 268, "y": 76, "width": 44, "height": 7, "rx": 2}}
TOKENS = {"word": "var(--ink, currentColor)", "bar": "var(--accent, currentColor)"}


def fetch(zip_path=None):
    """The SemiBold TTF's bytes, from `zip_path` or the pinned release, after the zip's SHA-256 matches."""
    if zip_path:
        data = Path(zip_path).read_bytes()
    else:
        try:
            with urllib.request.urlopen(URL, timeout=60) as r:
                data = r.read()
        except urllib.error.URLError as e:
            if "CERTIFICATE_VERIFY_FAILED" not in str(e):
                raise
            import subprocess  # Python without its certificates: curl uses the system's, verification stays on
            data = subprocess.run(["curl", "-fsSL", "--max-time", "120", URL], capture_output=True, check=True).stdout
    digest = hashlib.sha256(data).hexdigest()
    if digest != SHA256:
        raise SystemExit(f"IBM Plex Mono zip SHA-256 is {digest}, expected {SHA256}: not used.")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        return z.read(MEMBER)


def _num(v):
    """Two decimals, no trailing zeros, no negative zero."""
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def outline(font_bytes, text=TEXT, size=ART["size"], tracking=ART["tracking"]):
    """Each letter of `text` as an SVG path in px at `size`, origin on the baseline at the word's left edge (y down).

    Letters are placed as SVG lays out text with letter-spacing: each advance plus `tracking`. Returns the letters, the
    word's advance, its ink box [x, y, width, height] and the font's metrics, all in the same units."""
    from fontTools.pens.boundsPen import BoundsPen
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.ttLib import TTFont
    font = TTFont(io.BytesIO(font_bytes))
    upem = font["head"].unitsPerEm
    scale = size / upem
    glyphs, cmap, hmtx = font.getGlyphSet(), font.getBestCmap(), font["hmtx"]
    box = BoundsPen(glyphs)
    letters, x = [], 0.0
    for ch in text:
        name = cmap[ord(ch)]
        pen = SVGPathPen(glyphs, ntos=_num)
        matrix = (scale, 0, 0, -scale, x, 0)
        glyphs[name].draw(TransformPen(pen, matrix))
        glyphs[name].draw(TransformPen(box, matrix))
        adv = hmtx[name][0] * scale
        letters.append({"char": ch, "glyph": name, "x": round(x, 2), "advance": round(adv, 2), "d": pen.getCommands()})
        x += adv + tracking
    x0, y0, x1, y1 = box.bounds
    os2, hhea = font["OS/2"], font["hhea"]
    metrics = {"unitsPerEm": upem, "ascent": round(hhea.ascent * scale, 2), "descent": round(hhea.descent * scale, 2),
               "capHeight": round(getattr(os2, "sCapHeight", 0) * scale, 2),
               "xHeight": round(getattr(os2, "sxHeight", 0) * scale, 2)}
    view = [round(x0, 2), round(y0, 2), round(x1 - x0, 2), round(y1 - y0, 2)]
    return letters, round(x, 2), view, metrics


def build(font_bytes, source=None):
    """The JSON record: per-letter paths, the whole word as one path, the view box, advance, metrics and the art layout."""
    letters, advance, view, metrics = outline(font_bytes)
    return {"text": TEXT, "font": source or {}, "size": ART["size"], "tracking": ART["tracking"],
            "advance": advance, "metrics": metrics,
            "viewBox": view,
            "d": " ".join(g["d"] for g in letters), "glyphs": letters,
            "art": ART, "tokens": TOKENS}


def preview(record):
    """The wordmark drawn from the outlined paths (the word and the bar; BL-308: no dashed draft), colours as theme tokens."""
    a, d = record["art"], record["d"]
    w, b, t = a["word"], a["bar"], record["tokens"]
    vb = " ".join(str(v) for v in a["viewBox"])
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" width="{a["viewBox"][2]}" height="{a["viewBox"][3]}" '
            f'role="img" aria-label="creaite">\n'
            f'  <path transform="translate({w["x"]} {w["y"]})" style="fill:{t["word"]}" d="{d}"/>\n'
            f'  <rect x="{b["x"]}" y="{b["y"]}" width="{b["width"]}" height="{b["height"]}" rx="{b["rx"]}" '
            f'style="fill:{t["bar"]}"/>\n</svg>\n')


def write(record, out_dir=OUT):
    """Write wordmark-paths.json and wordmark-preview.svg into `out_dir`; return their paths."""
    out_dir = Path(out_dir)
    js, svg = out_dir / "wordmark-paths.json", out_dir / "wordmark-preview.svg"
    js.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    svg.write_text(preview(record), encoding="utf-8")
    return js, svg


def main(argv=None):
    """Download (or read) the font, outline the word, write the JSON and the preview, print the sizes."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--zip", help="an ibm-plex-mono.zip already downloaded (checked against the pinned SHA-256)")
    ap.add_argument("--out", default=str(OUT), help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    try:
        import fontTools  # noqa: F401
    except ImportError:
        sys.exit("Needs fontTools (development only): pip install fonttools")
    source = {"family": "IBM Plex Mono", "weight": 600, "release": RELEASE, "url": URL, "sha256": SHA256,
              "file": MEMBER.rsplit("/", 1)[-1], "licence": "SIL Open Font License 1.1 (OFL.txt)"}
    record = build(fetch(args.zip), source)
    js, svg = write(record, args.out)
    print(f"{js.name}: {len(record['glyphs'])} paths, {js.stat().st_size / 1024:.1f} KB")
    print(f"{svg.name}: {svg.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
