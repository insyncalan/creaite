"""BL-341: the screenshot sheet for the judgement checks: self-contained HTML pages (the screenshots embedded) in the run
folder's sheet/: index.html links one page per theme (light and dark at desktop width) and one for 320 px, each grouped by
check and screen and split into parts above PAGE_LIMIT, for Alan to flick through (like BL-325's before-and-after sheet). The checks add shots with `record(...)`; dev/tools/handcheck.py calls `write(...)` at the end.

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
table{border-collapse:collapse} th,td{padding:4px 12px 4px 0;border-bottom:1px solid var(--line);text-align:left}
"""


PAGE_LIMIT = 6_000_000          # bytes: a page bigger than this is split into parts, so each opens quickly


def _slug(text):
    return "".join(c if c.isalnum() else "-" for c in str(text)).strip("-").lower() or "page"


def _figure(r):
    """One screenshot as an embedded figure (None if its file has gone)."""
    f = Path(r["file"])
    if not f.exists():
        return None
    data = base64.b64encode(f.read_bytes()).decode()
    cap = f"{r['palette']} · {r['mode']} · {r['width']} px" + (f" · {r['note']}" if r.get("note") else "")
    return (f"<figure class='{'narrow' if int(r['width']) < 600 else ''}'><img loading='lazy' alt='{html.escape(cap)}' "
            f"src='data:image/jpeg;base64,{data}'><figcaption>{html.escape(cap)}</figcaption></figure>")


def _page(path, title, body, back=True):
    nav = "<p><a href='index.html'>← All pages</a></p>" if back else ""
    path.write_text("<!doctype html><meta charset='utf-8'>" + f"<title>{html.escape(title)}</title><style>{STYLE}</style>"
                    + nav + f"<h1>{html.escape(title)}</h1>" + "\n".join(body)
                    + "<script>document.addEventListener('click',e=>{if(e.target.tagName==='IMG')e.target.classList.toggle('big')})</script>",
                    encoding="utf-8")
    return path.stat().st_size


def write(out_dir, title="Hand checks: the judgement sheet", checks=None):
    """Write the sheet from the manifest: out_dir/sheet/index.html, linking one page per theme (its light and dark shots at
    desktop width) and one for the 320 px shots, each split into parts above PAGE_LIMIT. Returns the index's path (None when
    nothing was recorded)."""
    m = Path(out_dir) / "shots" / "manifest.jsonl"
    if not m.exists():
        return None
    rows = [json.loads(x) for x in m.read_text(encoding="utf-8").splitlines() if x.strip()]
    groups = {}                                     # page name: rows, in the order recorded
    for r in rows:
        groups.setdefault("320 px" if int(r["width"]) < 600 else str(r["palette"]), []).append(r)
    order = sorted((g for g in groups if g != "320 px"), key=str.lower) + (["320 px"] if "320 px" in groups else [])
    dest = Path(out_dir) / "sheet"
    dest.mkdir(parents=True, exist_ok=True)
    pages = []                                      # (file, label, shots, bytes, checks)
    for g in order:
        by_check = {}
        for r in groups[g]:
            by_check.setdefault(r["check"], {}).setdefault(r["screen"], []).append(r)
        parts, cur, size, n_shots, cur_checks = [], [], 0, 0, []
        for n in sorted(by_check):
            for screen, shots in by_check[n].items():
                figs = [x for x in map(_figure, shots) if x]
                block = [f"<h2 id='c{n}'>Check {n}</h2>" if n not in cur_checks else "",
                         f"<h3>{html.escape(screen)}</h3><div class='grid'>", *figs, "</div>"]
                bytes_ = sum(len(x) for x in block)
                if cur and size + bytes_ > PAGE_LIMIT:
                    parts.append((cur, n_shots, cur_checks))
                    cur, size, n_shots, cur_checks = [], 0, 0, []
                    block[0] = f"<h2 id='c{n}'>Check {n}</h2>"
                cur += block
                size += bytes_
                n_shots += len(figs)
                if n not in cur_checks:
                    cur_checks.append(n)
        if cur:
            parts.append((cur, n_shots, cur_checks))
        for i, (body, k, cs) in enumerate(parts, 1):
            label = g + (f", part {i} of {len(parts)}" if len(parts) > 1 else "")
            name = f"{_slug(g)}{f'-{i}' if len(parts) > 1 else ''}.html"
            what = "320 px, every check's narrow shots" if g == "320 px" else f"theme {g}, light and dark, desktop width"
            intro = [f"<p class='sub'>{html.escape(what)}. Click a picture to enlarge it.</p><nav>"
                     + "".join(f"<a href='#c{n}'>Check {n}</a>" for n in cs) + "</nav>"]
            b = _page(dest / name, f"{title}: {label}", intro + body)
            pages.append((name, label, k, b, cs))
    index = ["<p class='sub'>Made by dev/tools/handcheck.py. Each check below needs your eye: tick Pass or Fail for it in the "
             "Results table. One page per theme (light and dark at desktop width) and one for 320 px; a big page is split into "
             "parts.</p>", "<h2>Pages</h2><table><thead><tr><th>Page</th><th>Shots</th><th>Size</th><th>Checks</th></tr></thead><tbody>"]
    index += [f"<tr><td><a href='{n}'>{html.escape(lab)}</a></td><td>{k}</td><td>{b / 1e6:.1f} MB</td>"
              f"<td>{', '.join(map(str, cs))}</td></tr>" for n, lab, k, b, cs in pages]
    index.append("</tbody></table><h2>Checks</h2>")
    for n in sorted({r["check"] for r in rows}):
        links = " · ".join(f"<a href='{p}#c{n}'>{html.escape(lab)}</a>" for p, lab, _, _, cs in pages if n in cs)
        index.append(f"<h3 id='c{n}'>Check {n}</h3>" + (f"<blockquote>{html.escape(checks[n])}</blockquote>" if checks and n in checks else "")
                     + f"<p>{links}</p>")
    _page(dest / "index.html", title, index, back=False)
    return dest / "index.html"
