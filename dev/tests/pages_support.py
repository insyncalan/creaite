"""Shared fixture for the dashboard page tests (test_pages.py, test_pages_panes.py, test_pages_flow.py): the common imports, the report folder, the theme helpers and the page-resize helper."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from live_browser import TEST_PALETTES  # noqa: E402
from test_tracker import ABC  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

DEFAULT_REPORTS = f"{ABC}/reports"


def theme_count():
    """How many named themes the dashboard has (its THEMES list), so theme checks follow new themes by themselves."""
    return len(TEST_PALETTES)


def settle(b, js, timeout=10):
    b.wait(js, timeout)


def resize(b, width, height):
    """Resize, then wait until the page has the new size and the rail has followed it. The renderer takes the new viewport a
    little after Chrome answers, and the rail starts collapsed below 1200px on the media query's change event, at the next frame;
    under load a measurement taken at once saw the old size (two panes side by side at 700px)."""
    b.resize(width, height)
    b.wait(f"innerWidth==={width} && innerHeight==={height} && document.documentElement.classList.contains('railicons')==={str(width < 1200).lower()}")


THEMES = TEST_PALETTES   # creaite and Cursor only (live_browser.TEST_PALETTES; the product has nine themes)


def theme(b, palette, mode):
    b.eval(f"S.palette={json.dumps(palette)}; S.theme={json.dumps(mode)}; applyTheme()")


CONTRAST_JS = """(()=>{ const lum=c=>{ const [r,g,b]=c.match(/[\\d.]+/g).slice(0,3).map(Number).map(v=>{ v/=255; return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4); }); return 0.2126*r+0.7152*g+0.0722*b; };
  window.__ratio=(a,b)=>{ const x=lum(a), y=lum(b); return (Math.max(x,y)+0.05)/(Math.min(x,y)+0.05); };
  window.__bgOf=el=>{ for(let e=el;e;e=e.parentElement){ const c=getComputedStyle(e).backgroundColor; if(!/rgba\\(0, 0, 0, 0\\)|transparent/.test(c)) return c; } return "rgb(255,255,255)"; }; })()"""
