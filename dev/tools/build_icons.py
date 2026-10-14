#!/usr/bin/env python3
"""Build the installable app's icons (BL-86) from dev/icon/creaite-icon-stage.svg (Stage, BL-272) with headless Chrome.

  python3 dev/tools/build_icons.py

Writes system/templates/app/icon-192.png, icon-512.png and icon-maskable-512.png (the glyph on a full-bleed graphite square,
kept inside the middle 80% so any mask shape leaves it whole), and a copy of the 512 as dev/icon/creaite-icon-512.png.
BL-305: also icon-dev-512.png, the same icon with a "DEV" band across its top-right corner, for the development repository's
launcher ("creaite (dev).app"), so the Dock shows which is which.
The app icons live in system/templates/ so an update keeps them: dev/ isn't in the release zip.
Needs Google Chrome (or Edge); the PNGs are committed, so this only runs when the icon changes.
"""
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

REPO = HERE.parents[1]
SVG = REPO / "dev" / "icon" / "creaite-icon-stage.svg"
TILE = "#18181B"                                             # the tile's graphite, which the maskable icon fills with
OUT = REPO / "system" / "templates" / "app"


def render(html, size, dest):
    """Screenshot `html` at exactly size x size (a metrics override, since headless Chrome's smallest window is bigger)."""
    from cdp import Browser
    with tempfile.TemporaryDirectory(prefix="creaite-icons-") as tmp:
        page = Path(tmp) / "icon.html"
        page.write_text(html, encoding="utf-8")
        with Browser(size, size) as b:
            b.call("Emulation.setDefaultBackgroundColorOverride", color={"r": 0, "g": 0, "b": 0, "a": 0})
            b.resize(size, size)
            b.goto(page.as_uri())
            b.screenshot(str(dest))


# ===== BL-305 (sprint-launch-apply): the DEV-marked icon =====
DEV_BAND = ('<clipPath id="devclip"><rect width="512" height="512" rx="112"/></clipPath>'
            '<g clip-path="url(#devclip)"><g transform="translate(512 0) rotate(45)">'
            '<rect x="-300" y="112" width="600" height="76" fill="#E11D48"/>'
            '<text x="0" y="167" text-anchor="middle" font-family="Helvetica Neue, Helvetica, Arial, sans-serif" font-size="52" '
            'font-weight="800" letter-spacing="8" fill="#FFFFFF">DEV</text></g></g>')


def dev_icon(svg):
    """The Stage icon with a DEV band across its top-right corner, clipped to the tile."""
    return svg.replace("</svg>", DEV_BAND + "</svg>", 1)
# ===== end BL-305 =====


def main():
    svg = SVG.read_text(encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    page = lambda body, bg="transparent": (f"<!doctype html><meta charset=utf-8><style>html,body{{margin:0;background:{bg};overflow:hidden}}"
                                           f"svg{{display:block;width:100vw;height:100vh}}</style>{body}")
    for size in (192, 512):
        render(page(svg), size, OUT / f"icon-{size}.png")
    glyph = re.sub(r'<rect width="512" height="512"[^>]*/>', "", svg, count=1)   # no rounded tile: the graphite fills the icon
    inner = re.sub(r'viewBox="0 0 512 512"[^>]*>', 'viewBox="-64 -64 640 640">', glyph.split(">", 1)[0] + ">") + glyph.split(">", 1)[1]
    render(page(inner, TILE), 512, OUT / "icon-maskable-512.png")
    render(page(dev_icon(svg)), 512, OUT / "icon-dev-512.png")                    # BL-305
    (REPO / "dev" / "icon" / "creaite-icon-512.png").write_bytes((OUT / "icon-512.png").read_bytes())
    for p in sorted(OUT.glob("*.png")):
        print(p.relative_to(REPO), p.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
