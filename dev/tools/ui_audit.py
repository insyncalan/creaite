"""A rendered UI audit of the dashboard: every page, in each theme, at desktop and phone width.

Why: the token audit (token_audit.py) reads the source; this one looks at what a person actually sees. It starts the
live server in a throwaway vault with the tests' small fictional portfolio, drives headless Chrome (cdp.py) to each
page, and records for each page, theme and width:
  - a screenshot;
  - accessibility violations from axe-core (optional: pass --axe with the path to axe.min.js; never bundled);
  - the computed style of what is on screen (colours, type, radii, spacing, shadows), so pages can be compared;
  - a style signature for each kind of control (buttons, inputs, headings, chips, table cells), so the same control
    looking different on two pages shows up.

Usage (from the dev repo root):
  python3 dev/tools/ui_audit.py --out <dir> [--axe <path/to/axe.min.js>] [--themes creaite,Brightwater]
                                [--modes light,dark] [--widths 1400x1000,390x844]

Writes <dir>/rendered.json and <dir>/shots/*.png, and prints a Markdown summary. Development only: nothing at run time
uses it, and it never touches the dev repo's own vault.
"""
import argparse
import collections
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

DEV = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DEV / "tools"))
sys.path.insert(0, str(DEV / "tests"))
import proc_guard  # noqa: E402
from cdp import Browser  # noqa: E402
from live_browser import free_port, theme_names  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_tracker import Vault  # noqa: E402

# go() names for the pages; person and meeting need an item and are reached from People and Today instead
VIEWS = ["today", "work", "review", "projects", "cockpit", "milestones", "inbox", "files", "people", "activity",
         "settings", "help"]

# What each kind of control is, by selector; its style signature should match on every page
CONTROLS = {
    "button": "button, .btn",
    "input": "input:not([type=checkbox]):not([type=radio]):not([type=hidden]), select, textarea",
    "h1": "h1", "h2": "h2", "h3": "h3",
    "chip": ".chip, .pill, .tag, .badge",
    "th": "th", "td": "td",
    "link": "a[href]",
}

COLLECT = r"""(view, controls) => {
  const root = document.getElementById(view==="cockpit"?"v-cockpit":"v-"+view) || document.body;
  const vis = el => { const r = el.getBoundingClientRect(); const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== "hidden" && s.display !== "none"; };
  const els = [...root.querySelectorAll("*")].filter(vis);
  const tally = {}; const add = (k, v) => { if (!v) return; (tally[k] ??= {}); tally[k][v] = (tally[k][v]||0) + 1; };
  for (const el of els) {
    const s = getComputedStyle(el);
    const hasText = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (hasText) { add("color", s.color); add("font-size", s.fontSize); add("font-weight", s.fontWeight);
      add("font-family", s.fontFamily.split(",")[0].trim()); add("line-height", s.lineHeight); }
    if (s.backgroundColor !== "rgba(0, 0, 0, 0)") add("background", s.backgroundColor);
    if (s.borderTopWidth !== "0px" && s.borderTopStyle !== "none") add("border-color", s.borderTopColor);
    if (s.borderTopLeftRadius !== "0px") add("radius", s.borderTopLeftRadius);
    if (s.boxShadow !== "none") add("shadow", s.boxShadow);
    for (const p of ["paddingTop", "paddingLeft", "marginTop", "marginBottom", "rowGap", "columnGap"]) {
      const v = s[p]; if (v && v !== "0px" && v !== "normal") add("spacing", v); }
  }
  const sig = {};
  for (const [kind, sel] of Object.entries(controls)) {
    for (const el of [...root.querySelectorAll(sel)].filter(vis)) {
      const s = getComputedStyle(el); const r = el.getBoundingClientRect();
      const key = [s.fontSize, s.fontWeight, s.fontFamily.split(",")[0].trim(), s.borderTopLeftRadius,
        kind === "button" || kind === "input" ? Math.round(r.height) + "px" : "", s.paddingTop + " " + s.paddingLeft,
        s.textTransform, s.letterSpacing].join(" | ");
      const cls = typeof el.className === "string" && el.className.trim() ? "." + el.className.trim().split(/\s+/)[0]
        : el.tagName.toLowerCase();
      const g = kind + " " + cls; (sig[g] ??= {}); sig[g][key] = (sig[g][key] || 0) + 1;
      if (kind === "button" || kind === "link") { const t = (el.innerText || el.getAttribute("aria-label") || "").trim();
        if (t && t.length < 40) add("label:" + kind, t); }
    }
  }
  // tap targets under 24px (WCAG 2.2 2.5.8 minimum) among interactive elements
  const small = [...root.querySelectorAll("button, a[href], input, select, [role=button], [tabindex='0']")].filter(vis)
    .filter(el => { const r = el.getBoundingClientRect(); return r.width < 24 || r.height < 24; })
    .slice(0, 40).map(el => el.tagName.toLowerCase() + (el.id ? "#" + el.id : "") + " " +
      Math.round(el.getBoundingClientRect().width) + "x" + Math.round(el.getBoundingClientRect().height) + " " +
      (el.getAttribute("aria-label") || el.innerText || "").trim().slice(0, 30));
  const overflow = document.documentElement.scrollWidth > innerWidth + 1;
  return {elements: els.length, tally, sig, small, overflow};
}"""


def start_server():
    """A throwaway vault with the tests' fictional portfolio, and its live server; returns (vault, process, base URL)."""
    v = Vault()
    populate(v)
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    proc = proc_guard.spawn([sys.executable, str(v.root / "system/scripts/live_server.py")],
                            env={**os.environ, "CREAITE_PORT": str(port)},
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(150):
        try:
            urllib.request.urlopen(base + "/health", timeout=1)
            break
        except OSError:
            time.sleep(0.1)
    return v, proc, base


def run_axe(b, axe_src, view):
    """axe-core's violations for one page's view (None without --axe). The source is evaluated over CDP, past the CSP."""
    if not axe_src:
        return None
    if not b.eval("typeof axe!=='undefined'"):
        b.eval(axe_src + ";true")
    sel = "#v-cockpit" if view == "cockpit" else f"#v-{view}"
    return b.eval("axe.run(document.querySelector(%s)||document, {resultTypes:['violations']})"
                  ".then(r=>r.violations.map(v=>({id:v.id, impact:v.impact, help:v.help, n:v.nodes.length,"
                  " eg:v.nodes.slice(0,3).map(n=>n.target.join(' ')+(n.any[0]?' — '+n.any[0].message:''))})))"
                  % json.dumps(sel))


def render_pages(b, out, axe_src, themes, modes, size):
    """Every page in every theme and mode at one width; one result per page."""
    w = size.split("x")[0]
    results = []
    for theme in themes:
        for mode in modes:
            b.eval("(()=>{const r=document.documentElement; r.dataset.palette=%s; r.dataset.theme=%s;"
                   " return true})()" % (json.dumps(theme), json.dumps(mode)))
            for view in VIEWS:
                row = {"view": view, "theme": theme, "mode": mode, "size": size}
                try:
                    b.eval(f"go({json.dumps(view)})")
                except RuntimeError as e:
                    results.append({**row, "error": str(e)})
                    continue
                time.sleep(0.4)
                shot = out / "shots" / f"{view}-{theme}-{mode}-{w}.png".replace(" ", "_")
                b.screenshot(str(shot))
                data = b.eval(f"({COLLECT})({json.dumps(view)}, {json.dumps(CONTROLS)})")
                # axe on every page in the first theme, and on Today in every theme
                axe = run_axe(b, axe_src, view) if (theme == themes[0] or view == "today") else None
                results.append({**row, "shot": str(shot.relative_to(out)), "axe": axe, **data})
    return results


def audit(args):
    """Run the whole audit, write rendered.json and the screenshots, and print the summary."""
    out = Path(args.out)
    (out / "shots").mkdir(parents=True, exist_ok=True)
    axe_src = Path(args.axe).read_text() if args.axe else None
    known = theme_names()
    themes = list(known) if args.themes == "all" else [t for t in args.themes.split(",") if t in known]
    results = []
    v, proc, base = start_server()
    try:
        for size in args.widths.split(","):
            w, h = (int(x) for x in size.split("x"))
            b = Browser(w, h)
            try:
                b.goto(base + "/")
                b.wait("typeof go==='function' && LIVE", timeout=30)
                b.call("Page.setBypassCSP", enabled=True)
                results += render_pages(b, out, axe_src, themes, args.modes.split(","), size)
                results.append({"meta": "console-errors", "size": size, "errors": list(b.errors)[:50],
                                "viewport": b.eval("innerWidth+'x'+innerHeight")})
            finally:
                b.close()
    finally:
        proc_guard.stop(proc, grace=10)
        v.cleanup()
    (out / "rendered.json").write_text(json.dumps(results, indent=1))
    print(summary(results))


def _values(first):
    """Distinct rendered values of each property across the pages of one theme, mode and width."""
    lines = ["| Property | Distinct | Most used |", "|---|---|---|"]
    for prop in ["color", "background", "border-color", "font-size", "font-weight", "font-family", "line-height",
                 "radius", "shadow", "spacing"]:
        c = collections.Counter()
        for r in first:
            c.update(r["tally"].get(prop, {}))
        lines.append(f"| {prop} | {len(c)} | " + ", ".join(f"`{k}` ×{n}" for k, n in c.most_common(4)) + " |")
    return lines


def _controls(first):
    """Each kind of control, and the classes drawn more than one way across pages."""
    lines = ["A class drawn two ways on different pages is drift; one drawn two ways on one page may be a state.", ""]
    for kind in CONTROLS:
        groups = collections.defaultdict(lambda: collections.defaultdict(set))
        for r in first:
            for g, keys in r["sig"].items():
                if g.split(" ", 1)[0] == kind:
                    for key in keys:
                        groups[g][key].add(r["view"])
        styled = {g: by for g, by in groups.items() if len(by) > 1}
        lines.append(f"- **{kind}**: {len(groups)} classes, {sum(len(by) for by in groups.values())} rendered styles; "
                     f"{len(styled)} classes drawn more than one way")
        for g, by in sorted(styled.items(), key=lambda kv: -len(kv[1]))[:6]:
            lines.append(f"  - `{g.split(' ', 1)[1]}`: {len(by)} styles")
            lines += [f"    - `{key}` on {', '.join(sorted(views))}"
                      for key, views in sorted(by.items(), key=lambda kv: -len(kv[1]))[:4]]
    return lines


def _theme_fonts(pages):
    """Per theme, any font family that isn't the theme's own main one, and the pages it appears on."""
    lines = []
    for theme in sorted({r["theme"] for r in pages}):
        f, where = collections.Counter(), collections.defaultdict(set)
        for r in pages:
            if r["theme"] == theme:
                for k, n in r["tally"].get("font-family", {}).items():
                    f[k] += n
                    where[k].add(r["view"])
        main = f.most_common(1)[0][0] if f else ""
        others = [f"{k} on {', '.join(sorted(where[k]))}" for k, _ in f.most_common()[1:]]
        lines.append(f"- **{theme}** ({main}): " + ("; ".join(others) or "nothing else"))
    return lines


def _axe(pages):
    """axe-core violations merged across renders, worst first."""
    ax = collections.defaultdict(lambda: {"impact": "", "help": "", "n": 0, "where": set(), "eg": []})
    for r in pages:
        for vio in r.get("axe") or []:
            a = ax[vio["id"]]
            a["impact"], a["help"] = vio["impact"], vio["help"]
            a["n"] += vio["n"]
            a["where"].add(r["view"])
            a["eg"] = a["eg"] or vio["eg"]
    order = {"critical": 0, "serious": 1, "moderate": 2, "minor": 3}
    lines = []
    for k, a in sorted(ax.items(), key=lambda kv: (order.get(kv[1]["impact"], 9), -kv[1]["n"])):
        lines.append(f"- **{k}** ({a['impact']}, {a['n']} nodes): {a['help']}. Pages: {', '.join(sorted(a['where']))}")
        lines += [f"  - e.g. `{e[:200]}`" for e in a["eg"][:2]]
    return lines or ["None."]


def _targets(pages):
    """Tap targets under 24px and pages that scroll sideways, in the first theme and mode."""
    return [f"- {r['view']} @ {r['size']}: {len(r['small'])} targets under 24px"
            + (", **page scrolls sideways**" if r["overflow"] else "")
            + (": " + "; ".join(r["small"][:5]) if r["small"] else "")
            for r in pages if (r["small"] or r["overflow"])
            and (r["theme"], r["mode"]) == (pages[0]["theme"], pages[0]["mode"])]


def summary(results):
    """The Markdown summary of a run's results."""
    pages = [r for r in results if "view" in r and "error" not in r]
    if not pages:
        return "# Rendered UI audit\n\nNo page rendered."
    meta = [r for r in results if r.get("meta") == "console-errors"]
    key = (pages[0]["theme"], pages[0]["mode"], pages[0]["size"])
    first = [r for r in pages if (r["theme"], r["mode"], r["size"]) == key]
    lines = ["# Rendered UI audit", "",
             f"{len(pages)} page renders ({len({r['view'] for r in pages})} pages × "
             f"{len({(r['theme'], r['mode']) for r in pages})} theme modes × {len({r['size'] for r in pages})} widths)."
             " Real viewports: " + ", ".join(f"{r['size']} → {r.get('viewport', '?')}" for r in meta) + ".", "",
             f"## Distinct rendered values across pages ({' / '.join(key)})", ""] + _values(first)
    lines += ["", "## Same control, different look (one class, more than one rendered style)", ""] + _controls(first)
    lines += ["", "## Fonts other than the theme's own, by theme", ""] + _theme_fonts(pages)
    lines += ["", "## Accessibility (axe-core)", ""] + _axe(pages)
    lines += ["", "## Small tap targets and horizontal overflow", ""] + _targets(pages)
    return "\n".join(lines + _problems(results, meta))


def _problems(results, meta):
    """Console errors during the run, and any page that would not open."""
    errs = [e for r in meta for e in r["errors"]]
    fails = [r for r in results if "error" in r]
    lines = ["", f"## Console errors during the run: {len(errs)}", ""] + [f"- `{e[:200]}`" for e in errs[:10]]
    if fails:
        lines += ["", "## Pages that would not open", ""] + [f"- {r['view']}: {r['error'][:150]}" for r in fails[:10]]
    return lines


def main():
    """Command line."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--axe")
    ap.add_argument("--themes", default="creaite,Brightwater", help="comma-separated, or all")
    ap.add_argument("--modes", default="light,dark")
    ap.add_argument("--widths", default="1400x1000,390x844")
    audit(ap.parse_args())


if __name__ == "__main__":
    main()
