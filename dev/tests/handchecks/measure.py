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


# ── BL-341 phase 2 (Measured2: checks 6, 7, 8, 9, 16, 19) ──

PAINT_JS = r"""(sel, scope, prop) => {
  const parse = c => { const m = (c||"").match(/[\d.]+/g); if (!m || /^none|url/.test(c||"")) return null; const v = m.map(Number);
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
  const opacity = el => { let o = 1; for (let e = el; e; e = e.parentElement) o *= Number(getComputedStyle(e).opacity || 1); return o; };
  const root = scope ? document.querySelector(scope) : document; if (!root) return [];
  return [...root.querySelectorAll(sel)].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 &&
      getComputedStyle(e).visibility !== "hidden" && !e.closest("[hidden],[inert]"); })
    .map(e => { const s = getComputedStyle(e), bg = behind(e), p0 = parse(s[prop]); if (!p0) return null;
      const o = opacity(e) * (prop === "fill" ? Number(s.fillOpacity || 1) : prop === "stroke" ? Number(s.strokeOpacity || 1) : 1);
      const fg = over({...p0, a: p0.a*o}, bg);
      return {sig: e.tagName.toLowerCase()+(e.id?"#"+e.id:"")+((e.getAttribute("class")||"").trim()?"."+e.getAttribute("class").trim().split(/\s+/).join("."):""),
              text: (e.innerText||e.textContent||"").trim().slice(0, 30), paint: s[prop], opacity: Math.round(o*100)/100,
              background: `rgb(${Math.round(bg.r)}, ${Math.round(bg.g)}, ${Math.round(bg.b)})`,
              ratio: Math.round(ratio(fg, bg)*100)/100, size: parseFloat(s.fontSize), weight: Number(s.fontWeight)}; }).filter(Boolean);
}"""


def paint_contrast(b, selector, prop="color", scope=None):
    """Like contrast(), for any paint: "color" (text), "fill" or "stroke" (SVG marks), against what is behind, with the
    opacity of the element and every ancestor multiplied in (contrast() takes the element's own only). For text WCAG AA is
    4.5 (3 when large); for a mark that has to be seen (a non-text graphic, WCAG 1.4.11) it is 3."""
    return b.eval(f"({PAINT_JS})({json.dumps(selector)}, {json.dumps(scope)}, {json.dumps(prop)})")


def hit_box(b, selector, scope="document"):
    """The pointer target of each visible match: its own box, or its <label>'s when it is inside one or named by one (a
    click on the label works the control). [{sig, w, h, label_w, label_h, text}]: DevTools › Inspect's box, and the label's."""
    return b.eval("""(()=>{ const root=%s==="document"?document:document.querySelector(%s); if(!root) return [];
      const size=e=>{ const r=e.getBoundingClientRect(); return [Math.round(r.width*10)/10, Math.round(r.height*10)/10]; };
      return [...root.querySelectorAll(%s)].filter(e=>{ const r=e.getBoundingClientRect(), s=getComputedStyle(e);
          return r.width>0&&r.height>0&&s.visibility!=="hidden"&&!e.closest("[hidden],[inert]"); })
        .map(e=>{ const [w,h]=size(e), l=e.closest("label")||(e.id&&document.querySelector('label[for="'+CSS.escape(e.id)+'"]'));
          const [lw,lh]=l?size(l):[0,0];
          return {sig:e.tagName.toLowerCase()+(e.id?"#"+e.id:"")+(typeof e.className==="string"&&e.className.trim()?"."+e.className.trim().split(/\\s+/).join("."):""),
                  w, h, label_w:lw, label_h:lh, text:(e.getAttribute("aria-label")||(l&&l.innerText)||"").trim().slice(0,40)}; }); })()"""
                  % (json.dumps(scope), json.dumps(scope), json.dumps(selector)))


STACK_JS = r"""(topSel, underSel) => {
  const vis = e => { if (!e) return false; const r = e.getBoundingClientRect(), s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== "hidden" && s.display !== "none"; };
  const pick = sel => [...document.querySelectorAll(sel)].find(vis) || null;
  const top = pick(topSel), under = pick(underSel); if (!top || !under) return {top: !!top, under: !!under, ok: null};
  const rootZ = e => { let z = 0, at = null; for (let x = e; x && x !== document.documentElement; x = x.parentElement) {
      const s = getComputedStyle(x); if (s.zIndex !== "auto" && s.position !== "static") { z = Number(s.zIndex); at = x; } }
    return {z, at}; };
  const a = top.getBoundingClientRect(), b = under.getBoundingClientRect();
  const l = Math.max(a.left, b.left), r = Math.min(a.right, b.right), t = Math.max(a.top, b.top), bo = Math.min(a.bottom, b.bottom);
  const zt = rootZ(top), zu = rootZ(under);
  const out = {top_z: zt.z, under_z: zu.z};
  if (r - l >= 2 && bo - t >= 2) {
    const x = (l + r) / 2, y = (t + bo) / 2, hit = document.elementFromPoint(x, y);
    out.how = "hit"; out.at = [Math.round(x), Math.round(y)]; out.ok = !!hit && top.contains(hit);
    out.hit = hit ? hit.tagName.toLowerCase() + (hit.id ? "#" + hit.id : "") + (typeof hit.className === "string" && hit.className ? "." + hit.className.trim().split(/\s+/)[0] : "") : null;
  } else {
    out.how = "z";
    out.ok = zt.z > zu.z || (zt.z === zu.z && !!zt.at && !!zu.at && !!(zu.at.compareDocumentPosition(zt.at) & Node.DOCUMENT_POSITION_FOLLOWING));
  }
  return out;
}"""


def on_top(b, top, under):
    """Is the first visible match of `top` drawn over the first visible match of `under`? Where their boxes overlap, the
    point in the middle of the overlap is hit-tested (what is really on top there); where they don't, their stacking order
    decides: the z-index of each one's outermost positioned ancestor with a z-index (the root stacking context), a tie going
    to the later one in the page. {ok, how: "hit" | "z", top_z, under_z, at?, hit?}; ok None when either isn't showing."""
    return b.eval(f"({STACK_JS})({json.dumps(top)}, {json.dumps(under)})")
# ── BL-333: scrolling to the bottom (checks 21 and 22) ──

# How far a scroll box can scroll, and where its last visible content ends, both in its own scroll coordinates (as
# dev/tests/test_ui_sweep.py's ScrollEnd measures it): every rendered descendant but visually hidden text (.vh) and fixed
# layers, by its margin box; a descendant that clips counts by its own box. Chrome ends the scrollable area at that content
# plus the box's bottom padding.
SCROLL_END_JS = """(sel=>{ const box=document.querySelector(sel); if(!box) return null; const B=box.getBoundingClientRect(), s=getComputedStyle(box);
  const top=B.top+parseFloat(s.borderTopWidth)-box.scrollTop; let end=0, last='';
  const walk=el=>{ for(const c of el.children){ if(c.matches('.vh')) continue; const cs=getComputedStyle(c);
      if(cs.display==='none'||cs.position==='fixed'||!c.getClientRects().length) continue;
      const r=c.getBoundingClientRect(), b=r.bottom+Math.max(0,parseFloat(cs.marginBottom)||0)-top;
      if(r.height>0&&b>end){ end=b; last=c.tagName+(c.id?'#'+c.id:''); }
      if(cs.overflowY==='visible'&&cs.overflowX==='visible') walk(c); } };
  walk(box);
  return {sh:box.scrollHeight, ch:box.clientHeight, top:Math.round(box.scrollTop), end:Math.ceil(end+parseFloat(s.paddingBottom)), last}; })"""


def scroll_end(b, selector):
    """A scroll box's scrollHeight, clientHeight, scrollTop and where its last visible content ends ({sh, ch, top, end, last}),
    or None when there is no such box. It "stops at the last content" when sh <= end + 1 (or it doesn't scroll at all)."""
    return b.eval(f"({SCROLL_END_JS})({json.dumps(selector)})")


def rect(b, selector):
    """The first match's bounding box ({top, left, width, height}), or None."""
    return b.eval("(()=>{ const e=document.querySelector(%s); if(!e) return null; const r=e.getBoundingClientRect();"
                  " return {top:Math.round(r.top), left:Math.round(r.left), width:Math.round(r.width), height:Math.round(r.height)}; })()"
                  % json.dumps(selector))


def wheel_to_bottom(b, selector, step=500, most=80):
    """Turn the mouse wheel over the middle of `selector` (real wheel events, as a hand on the mouse) until nothing moves any
    more. Returns {steps, top, window_top}: how many turns, the box's scrollTop and the window's scrollY at the end."""
    pos = b.eval("""(()=>{ const e=document.querySelector(%s); if(!e) return null; const r=e.getBoundingClientRect();
      return {x:r.left+Math.min(r.width/2, 200), y:r.top+Math.min(r.height/2, innerHeight/2)}; })()""" % json.dumps(selector))
    if not pos:
        return None
    where = "[(document.querySelector(%s)||{}).scrollTop||0, scrollY]" % json.dumps(selector)
    last, n = None, 0
    while n < most:
        n += 1
        b.call("Input.dispatchMouseEvent", type="mouseWheel", x=pos["x"], y=pos["y"], deltaX=0, deltaY=step)
        b.pump(0.06)
        now = b.eval(where)
        if now == last:
            break
        last = now
    b.pump(0.2)
    top, wy = b.eval(where)
    return {"steps": n, "top": round(top), "window_top": round(wy)}
