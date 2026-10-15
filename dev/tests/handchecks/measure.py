"""BL-341: measuring helpers for the automated hand checks, over the DevTools protocol (dev/tools/cdp.py's Browser).

Standard library only; nothing is vendored or installed. Each helper takes a cdp Browser `b` and returns plain data, so a
check states what it measured in its note. What they stand in for:
- media(b, dark=…, forced=…)      DevTools › Rendering's prefers-color-scheme and forced colours (Emulation.setEmulatedMedia)
- theme(b, palette, mode)         Settings › Appearance (palette, and light, dark or System), in the page only: nothing is saved
- width(b, w)                     the Device toolbar at w px (Emulation.setDeviceMetricsOverride)
- overflow_x(b) / overflow_y(b)   "no sideways scroll" (scrollWidth against innerWidth) and BL-333's "doesn't scroll past its
                                  bottom" (document.scrollingElement.scrollHeight against innerHeight)
- boxes(b, selector)              DevTools › Inspect's box: rendered width and height of each visible match
- contrast(b, selector)           a WCAG 2 contrast ratio from computed colours: the text colour against the first opaque
                                  background behind it, compositing translucent layers; background images and gradients are
                                  not seen (say so in a note when it matters). Not axe: axe-core would need a licence decision.
- ax_unnamed(b, scope) / ax_node(b, selector)   Accessibility.getFullAXTree / getPartialAXTree: role, name and value as
                                  Chrome's accessibility tree has them. An approximation of VoiceOver, not VoiceOver: it shows
                                  what a screen reader is given, not what it says.
- shot(b, path, …)                a screenshot for the judgement sheet (sheet.py), with its labels.
"""
import base64
import json
from pathlib import Path

INTERACTIVE = {"button", "link", "checkbox", "textbox", "combobox", "slider", "tab", "switch", "menuitem", "menuitemcheckbox",
               "option", "radio", "searchbox", "spinbutton", "listbox", "separator"}


def media(b, dark=None, forced=None, reduced=True, contrast=None):
    """Emulate the system's settings. dark: True (dark), False (light) or None (as the machine is); forced: forced colours."""
    f = []
    if reduced:
        f.append({"name": "prefers-reduced-motion", "value": "reduce"})        # BL-136: as cdp.Browser starts
    if dark is not None:
        f.append({"name": "prefers-color-scheme", "value": "dark" if dark else "light"})
    if forced is not None:
        f.append({"name": "forced-colors", "value": "active" if forced else "none"})
    if contrast:
        f.append({"name": "prefers-contrast", "value": contrast})
    b.call("Emulation.setEmulatedMedia", features=f)
    b.pump(0.1)


def theme(b, palette, mode):
    """Palette (THEMES' id) and mode ("light", "dark" or "system"), as Settings › Appearance applies them, in the page only."""
    b.eval("(()=>{ S.palette=%s; S.theme=%s; applyTheme(); return true; })()"
           % (json.dumps(palette), json.dumps("System" if mode == "system" else mode.capitalize())))
    b.pump(0.1)


def themes(b):
    return b.eval("THEMES.map(t=>t.id)")


def width(b, w, h=900):
    b.resize(w, h)
    b.pump(0.2)


def overflow_x(b):
    """Sideways scroll: the page's scrollWidth against the window's innerWidth."""
    r = b.eval("({sw:document.scrollingElement.scrollWidth, iw:innerWidth})")
    r["ok"] = r["sw"] <= r["iw"]
    return r


def overflow_y(b):
    """BL-333: the page's scrollHeight against innerHeight (equal when it never scrolls past its bottom)."""
    r = b.eval("({sh:document.scrollingElement.scrollHeight, ih:innerHeight})")
    r["ok"] = r["sh"] == r["ih"]
    return r


def boxes(b, selector, scope="document"):
    """Each visible match's rendered size and a short signature: [{sig, w, h, text}]."""
    return b.eval("""(()=>{ const root=%s==="document"?document:document.querySelector(%s); if(!root) return [];
      return [...root.querySelectorAll(%s)].filter(e=>{ const r=e.getBoundingClientRect(), s=getComputedStyle(e);
        return r.width>0&&r.height>0&&s.visibility!=="hidden"&&!e.closest("[hidden],[inert]"); })
      .map(e=>{ const r=e.getBoundingClientRect();
        return {sig:e.tagName.toLowerCase()+(e.id?"#"+e.id:"")+(typeof e.className==="string"&&e.className.trim()?"."+e.className.trim().split(/\\s+/).join("."):""),
                w:Math.round(r.width*10)/10, h:Math.round(r.height*10)/10, text:(e.innerText||e.getAttribute("aria-label")||"").trim().slice(0,40)}; }); })()"""
                  % (json.dumps(scope), json.dumps(scope), json.dumps(selector)))


CONTRAST_JS = r"""(sel, scope) => {
  const parse = c => { const m = (c||"").match(/[\d.]+/g); if (!m) return null; const v = m.map(Number);
    return {r:v[0], g:v[1], b:v[2], a:v.length > 3 ? v[3] : 1}; };
  const over = (top, under) => { const a = top.a + under.a*(1-top.a); if (!a) return {r:0,g:0,b:0,a:0};
    const mix = k => (top[k]*top.a + under[k]*under.a*(1-top.a))/a; return {r:mix("r"), g:mix("g"), b:mix("b"), a}; };
  const lum = c => { const f = u => { u/=255; return u<=0.03928 ? u/12.92 : ((u+0.055)/1.055)**2.4; };
    return 0.2126*f(c.r) + 0.7152*f(c.g) + 0.0722*f(c.b); };
  const ratio = (x, y) => { const [lo, hi] = [lum(x), lum(y)].sort((p, q) => p - q); return (hi+0.05)/(lo+0.05); };
  const behind = el => { const layers = []; for (let e = el; e; e = e.parentElement) { const c = parse(getComputedStyle(e).backgroundColor);
      if (c && c.a > 0) { layers.push(c); if (c.a >= 1) break; } }
    let bg = parse(getComputedStyle(document.documentElement).backgroundColor); if (!bg || bg.a < 1) bg = {r:255,g:255,b:255,a:1};
    for (const c of layers.reverse()) bg = over(c, bg); return bg; };
  const root = scope ? document.querySelector(scope) : document; if (!root) return [];
  return [...root.querySelectorAll(sel)].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 &&
      getComputedStyle(e).visibility !== "hidden" && !e.closest("[hidden],[inert]"); })
    .map(e => { const s = getComputedStyle(e), bg = behind(e), fg0 = parse(s.color), fg = over({...fg0, a: fg0.a*Number(s.opacity||1)}, bg);
      return {sig: e.tagName.toLowerCase()+(e.id?"#"+e.id:"")+(typeof e.className==="string"&&e.className.trim()?"."+e.className.trim().split(/\s+/)[0]:""),
              text: (e.innerText||"").trim().slice(0, 30), color: s.color, background: `rgb(${Math.round(bg.r)}, ${Math.round(bg.g)}, ${Math.round(bg.b)})`,
              ratio: Math.round(ratio(fg, bg)*100)/100, size: parseFloat(s.fontSize), weight: Number(s.fontWeight)}; });
}"""


def contrast(b, selector, scope=None):
    """WCAG contrast of each visible match's text against what is behind it: [{sig, text, color, background, ratio, size,
    weight}]. AA is 4.5 (3 for large text: 24 px, or 18.66 px bold)."""
    return b.eval(f"({CONTRAST_JS})({json.dumps(selector)}, {json.dumps(scope)})")


def large(row):
    return row["size"] >= 24 or (row["size"] >= 18.66 and row["weight"] >= 700)


def ax_tree(b):
    """Chrome's full accessibility tree (nodes as CDP gives them)."""
    b.call("Accessibility.enable")
    return b.call("Accessibility.getFullAXTree")["nodes"]


def _v(node, key):
    return ((node.get(key) or {}).get("value"))


def ax_unnamed(b, scope=None):
    """Interactive nodes with no accessible name (VoiceOver would say only "button"): [{role, backend}], within `scope`
    (a selector) if given. An approximation of VoiceOver."""
    nodes = ax_tree(b)
    inside = None
    if scope:
        root = b.call("DOM.getDocument", depth=0)["root"]["nodeId"]
        nid = b.call("DOM.querySelector", nodeId=root, selector=scope)["nodeId"]
        if nid:
            desc = b.call("DOM.describeNode", nodeId=nid, depth=-1)["node"]
            inside = set()
            stack = [desc]
            while stack:
                d = stack.pop()
                inside.add(d.get("backendNodeId"))
                stack.extend(d.get("children") or [])
    out = []
    for n in nodes:
        if n.get("ignored") or _v(n, "role") not in INTERACTIVE:
            continue
        if inside is not None and n.get("backendDOMNodeId") not in inside:
            continue
        if _v(n, "role") == "separator" and not any(p.get("name") == "focusable" for p in n.get("properties") or []):
            continue
        if not (_v(n, "name") or "").strip():
            out.append({"role": _v(n, "role"), "backend": n.get("backendDOMNodeId")})
    return out


def ax_node(b, selector):
    """Role, name, value and properties of the first match, as the accessibility tree has them (None if no match)."""
    b.call("Accessibility.enable")
    root = b.call("DOM.getDocument", depth=0)["root"]["nodeId"]
    nid = b.call("DOM.querySelector", nodeId=root, selector=selector)["nodeId"]
    if not nid:
        return None
    nodes = b.call("Accessibility.getPartialAXTree", nodeId=nid, fetchRelatives=False)["nodes"]
    n = nodes[0] if nodes else {}
    return {"role": _v(n, "role"), "name": _v(n, "name"), "value": _v(n, "value"),
            "props": {p["name"]: (p.get("value") or {}).get("value") for p in n.get("properties") or []}}


def shot(b, path, quality=72):
    """A JPEG screenshot (small enough to embed several dozen in one sheet). Returns the path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = b.call("Page.captureScreenshot", format="jpeg", quality=quality)["data"]
    path.write_bytes(base64.b64decode(data))
    return path
