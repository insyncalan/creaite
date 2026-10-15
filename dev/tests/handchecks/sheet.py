"""BL-341: the screenshot sheet for the judgement checks: one self-contained HTML file (the screenshots embedded), every theme
× light and dark × 1400 and 320 px, grouped by check and screen, for Alan to flick through (like BL-325's before-and-after
sheet). The checks add shots with `record(...)`; dev/tools/handcheck.py calls `write(...)` at the end.

The sheet and its screenshots stay in the run folder, never in the repository (it is public).
"""
import base64
import html
import json
import os
from pathlib import Path


def run_dir():
    return Path(os.environ.get("CREAITE_HC_DIR") or ".")


def manifest():
    return run_dir() / "shots" / "manifest.jsonl"


def enabled():
    return os.environ.get("CREAITE_HC_SHEET", "1") != "0"


def record(check, screen, palette, mode, width, path, note=""):
    """Note one screenshot for the sheet."""
    m = manifest()
    m.parent.mkdir(parents=True, exist_ok=True)
    with m.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"check": check, "screen": screen, "palette": palette, "mode": mode, "width": width,
                            "file": str(Path(path).resolve()), "note": note}) + "\n")


def shot_path(check, screen, palette, mode, width):
    name = f"c{check:02d}-{screen}-{palette}-{mode}-{width}.jpg".replace(" ", "_")
    return run_dir() / "shots" / name


STYLE = """
:root{--bg:#f6f7f8;--card:#fff;--ink:#16191d;--sub:#5b6570;--line:#d9dee3}
@media (prefers-color-scheme:dark){:root{--bg:#121417;--card:#1b1e22;--ink:#e8eaed;--sub:#9aa3ad;--line:#2c3137}}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;padding:16px 24px}
h1{font-size:20px;margin:0 0 4px} h2{font-size:17px;margin:28px 0 6px} h3{font-size:14px;margin:16px 0 6px;color:var(--sub)}
.sub{color:var(--sub)} blockquote{margin:6px 0 10px;padding:6px 12px;border-left:3px solid var(--line);background:var(--card)}
nav a{margin-right:12px} .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}
figure{margin:0;background:var(--card);border:1px solid var(--line);border-radius:6px;padding:6px}
figure.narrow img{max-width:160px} img{max-width:100%;display:block;border:1px solid var(--line);cursor:zoom-in}
figcaption{font-size:12px;color:var(--sub);margin-top:4px} img.big{position:fixed;inset:2vh 2vw;max-width:96vw;max-height:96vh;
margin:auto;z-index:9;cursor:zoom-out;box-shadow:0 0 0 100vmax rgba(0,0,0,.7)}
"""


def write(out_dir, title="Hand checks: the judgement sheet", checks=None):
    """Write out_dir/sheet.html from the manifest; returns its path (None when nothing was recorded)."""
    m = Path(out_dir) / "shots" / "manifest.jsonl"
    if not m.exists():
        return None
    rows = [json.loads(x) for x in m.read_text(encoding="utf-8").splitlines() if x.strip()]
    by_check = {}
    for r in rows:
        by_check.setdefault(r["check"], {}).setdefault(r["screen"], []).append(r)
    parts = [f"<title>{html.escape(title)}</title><style>{STYLE}</style><h1>{html.escape(title)}</h1>",
             "<p class='sub'>Made by dev/tools/handcheck.py. Each check below needs your eye: tick Pass or Fail for it in the "
             "Results table. Click a picture to enlarge it. Every theme, light and dark, at 1400 and 320 px.</p><nav>"]
    parts += [f"<a href='#c{n}'>Check {n}</a>" for n in sorted(by_check)]
    parts.append("</nav>")
    for n in sorted(by_check):
        parts.append(f"<h2 id='c{n}'>Check {n}</h2>")
        if checks and n in checks:
            parts.append(f"<blockquote>{html.escape(checks[n])}</blockquote>")
        for screen, shots in by_check[n].items():
            parts.append(f"<h3>{html.escape(screen)}</h3><div class='grid'>")
            for r in shots:
                f = Path(r["file"])
                if not f.exists():
                    continue
                data = base64.b64encode(f.read_bytes()).decode()
                cap = f"{r['palette']} · {r['mode']} · {r['width']} px" + (f" · {r['note']}" if r.get("note") else "")
                parts.append(f"<figure class='{'narrow' if int(r['width']) < 600 else ''}'><img loading='lazy' alt='{html.escape(cap)}' "
                             f"src='data:image/jpeg;base64,{data}'><figcaption>{html.escape(cap)}</figcaption></figure>")
            parts.append("</div>")
    parts.append("<script>document.addEventListener('click',e=>{if(e.target.tagName==='IMG')e.target.classList.toggle('big')})</script>")
    dest = Path(out_dir) / "sheet.html"
    dest.write_text("<!doctype html><meta charset='utf-8'>" + "\n".join(parts), encoding="utf-8")
    return dest
