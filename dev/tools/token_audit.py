"""Audit creaite's design tokens across its whole UI suite (development only; standard library only).

Run: python3 dev/tools/token_audit.py [--json] [--strict] [--limit N]

Why: every colour on the dashboard is meant to be a token (the colour audit, 1.5.1), nine themes each set their own, and the
same brand and status colours reappear in the guides, the prep page, the offline page, the email drafts and the Word
templates. Nothing checks that those stay in step, so drift is found by eye. This reads every surface, models the theme
cascade the way the browser applies it, and prints a Markdown report (or `--json`) of eight checks:

  1 UNUSED      a token defined but never read (CSS, inline styles, JS)
  2 UNDEFINED   a token read with var() but defined nowhere (with a fallback: P3)
  3 THEMES      THEMES (src/core/page.js) against the CSS palettes; the system-dark block against the explicit-dark one; a
                palette's light-only colours (its light value shows in dark mode); a token read outside any palette's scope
                that some palette never defines
  4 HARDCODED   colour literals outside token definitions (CSS rules, style="" attributes, JS strings); P1 when the literal
                is exactly a token's value in that context ("should be var(--x)")
  5 SCALE       raw against tokenised values of type, radius, shadow, z-index, spacing and timing, and near-duplicate values;
                on a surface with BL-325's one design scale (--fs-* tokens), any font size, radius, shadow, z-index or
                spacing value off that scale, bar the listed exceptions (on_scale)
  6 DUPLICATES  two root tokens with the same or nearly the same colour in one theme (merge or alias candidates)
  7 CONTRAST    WCAG contrast of text and UI token pairs, per palette and mode
  8 SURFACES    the dashboard's default palette against the guides, prep page, offline page, reference, email drafts and Word

How themes are found: a rule is a theme root when each selector is `:root` followed only by `[data-palette="X"]`,
`[data-palette]`, `[data-theme="dark|light"]`, `[data-theme]` or `:not([data-theme="light"])`, under no @media or only
`@media (prefers-color-scheme: …)`. Each palette (the THEMES ids, or the `[data-palette]` values a surface uses) is resolved
in four environments: light, explicit dark (data-theme="dark"), system dark (no attribute, the dark media query) and forced
light (data-theme="light" under system dark), applying the matching rules by specificity and then source order, as the
browser does. The default palette is the one `themeOf` falls back to.

Contrast pairs come from the token names: text tokens (ink, muted, faint, accent, bad, warn, ok) on the grounds (bg, surface,
sunk); `X-ink` on `X`; a status colour on its `-soft` fill; Today's `--day-*` and Help's `--hp-*` equivalents; and UI marks
(focus, saffron, day-sun, day-past) at 3:1. Text below 4.5:1 and UI below 3:1 are P1.

It is an audit, not a gate: it exits 0 unless --strict is given and a P1 is found.
"""
import argparse
import ast
import bisect
import colorsys
import json
import math
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TPL = ROOT / "system" / "templates"
DASH = TPL / "dashboard"
SCRIPTS = ROOT / "system" / "scripts"
CHECKS = {1: "Unused tokens", 2: "Undefined tokens", 3: "Theme completeness", 4: "Hard-coded colours", 5: "Scale drift",
          6: "Near-duplicate tokens", 7: "Contrast", 8: "Cross-surface consistency"}
SEVS = ("P1", "P2", "P3")
ENVS = {"light": (None, False), "dark": ("dark", False), "system-dark": (None, True), "forced-light": ("light", True)}
JND = 2.3            # CIE76 delta E: a just-noticeable difference
NEAR_DE = 2.0        # two tokens of the same kind closer than this are near-duplicates

# ---------- colours ----------
NAMED = {"white": "#ffffff", "black": "#000000", "red": "#ff0000", "green": "#008000", "blue": "#0000ff",
         "yellow": "#ffff00", "orange": "#ffa500", "gray": "#808080", "grey": "#808080", "silver": "#c0c0c0",
         "navy": "#000080", "teal": "#008080", "purple": "#800080", "maroon": "#800000", "olive": "#808000",
         "lime": "#00ff00", "aqua": "#00ffff", "fuchsia": "#ff00ff", "pink": "#ffc0cb", "gold": "#ffd700",
         "brown": "#a52a2a", "crimson": "#dc143c", "coral": "#ff7f50", "tomato": "#ff6347", "salmon": "#fa8072",
         "orchid": "#da70d6", "violet": "#ee82ee", "indigo": "#4b0082", "cyan": "#00ffff", "magenta": "#ff00ff",
         "whitesmoke": "#f5f5f5", "gainsboro": "#dcdcdc", "lightgray": "#d3d3d3", "lightgrey": "#d3d3d3",
         "darkgray": "#a9a9a9", "darkgrey": "#a9a9a9", "dimgray": "#696969", "slategray": "#708090",
         "steelblue": "#4682b4", "royalblue": "#4169e1", "dodgerblue": "#1e90ff", "seagreen": "#2e8b57",
         "firebrick": "#b22222", "darkred": "#8b0000", "darkgreen": "#006400", "darkblue": "#00008b",
         "ivory": "#fffff0", "beige": "#f5f5dc", "linen": "#faf0e6", "snow": "#fffafa", "rebeccapurple": "#663399"}
KEYWORDS = {"transparent", "currentcolor", "inherit", "initial", "unset", "revert", "none"}
SYSTEM_COLOURS = {"canvas", "canvastext", "highlight", "highlighttext", "buttontext", "buttonface", "buttonborder",
                  "linktext", "graytext", "field", "fieldtext", "mark", "marktext", "accentcolor", "accentcolortext"}
COLOUR_PROPS = re.compile(r"^(color|background(-color)?|border(-[a-z]+)*|outline(-color)?|fill|stroke|box-shadow|"
                          r"text-shadow|caret-color|accent-color|text-decoration(-color)?|column-rule(-color)?|"
                          r"scrollbar-color|stop-color|flood-color|lighting-color)$")
HEX = re.compile(r"(?<![\w&-])#([0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![\w-])")
FUNC = re.compile(r"\b(rgba?|hsla?)\(\s*[^()]*\)", re.I)
URL = re.compile(r"url\((?:[^()]|\([^()]*\))*\)", re.I)
WORD = re.compile(r"(?<![\w#.-])([a-zA-Z]+)(?![\w(-])")


def _num(t, scale=255.0):
    t = t.strip()
    if t.endswith("%"):
        return float(t[:-1]) / 100.0 * scale
    return float(t)


def _hex_rgba(h):
    h = h.lstrip("#").lower()
    if len(h) in (3, 4):
        h = "".join(c * 2 for c in h)
    a = int(h[6:8], 16) / 255.0 if len(h) == 8 else 1.0
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def _func_rgba(name, args):
    parts = [p for p in re.split(r"[\s,/]+", args.strip()) if p]
    if len(parts) < 3:
        return None
    a = _num(parts[3], 1.0) if len(parts) > 3 else 1.0
    if name.startswith("rgb"):
        return tuple(round(_num(p)) for p in parts[:3]) + (a,)
    h = float(re.sub(r"deg$", "", parts[0])) / 360.0
    r, g, b = colorsys.hls_to_rgb(h % 1.0, _num(parts[2], 1.0), _num(parts[1], 1.0))
    return (round(r * 255), round(g * 255), round(b * 255), a)


def parse_colour(s):
    """(r, g, b, alpha) for one CSS colour (hex, rgb[a], hsl[a], a common named colour, color-mix in srgb), else None."""
    s = (s or "").strip().lower().replace("!important", "").strip()
    if not s:
        return None
    if re.fullmatch(r"#[0-9a-f]{3,8}", s) and len(s) in (4, 5, 7, 9):
        return _hex_rgba(s)
    m = re.fullmatch(r"(rgba?|hsla?)\((.*)\)", s)
    if m:
        try:
            return _func_rgba(m.group(1), m.group(2))
        except ValueError:
            return None
    if s in NAMED:
        return _hex_rgba(NAMED[s])
    if s.startswith("color-mix("):
        return _colour_mix(s)
    return None


def _colour_mix(s):
    m = re.fullmatch(r"color-mix\(\s*in\s+srgb\s*,(.*)\)", s)
    if not m:
        return None
    args = split_top(m.group(1), ",")
    if len(args) != 2:
        return None
    cols, pcts = [], []
    for a in args:
        pm = re.search(r"\s(\d+(?:\.\d+)?)%\s*$", " " + a)
        pcts.append(float(pm.group(1)) / 100 if pm else None)
        cols.append(parse_colour(a[:pm.start() - 1] if pm else a))
    if None in cols:
        return None
    p1 = pcts[0] if pcts[0] is not None else (1 - pcts[1] if pcts[1] is not None else 0.5)
    mixed = [cols[0][i] * p1 + cols[1][i] * (1 - p1) for i in range(4)]
    return (round(mixed[0]), round(mixed[1]), round(mixed[2]), mixed[3])


def hexof(c):
    """#RRGGBB (or #RRGGBBAA when not opaque) for an rgba tuple."""
    out = "#%02X%02X%02X" % tuple(max(0, min(255, int(round(v)))) for v in c[:3])
    return out if c[3] >= 0.999 else out + "%02X" % int(round(c[3] * 255))


def _lin(v):
    v /= 255.0
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def lab(c):
    """CIE Lab (D65) of an opaque sRGB colour."""
    r, g, b = (_lin(v) for v in c[:3])
    xyz = (0.4124 * r + 0.3576 * g + 0.1805 * b, 0.2126 * r + 0.7152 * g + 0.0722 * b, 0.0193 * r + 0.1192 * g + 0.9505 * b)
    f = [t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116 for t in (xyz[0] / 0.95047, xyz[1], xyz[2] / 1.08883)]
    return (116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2]))


def delta_e(a, b):
    """CIE76 distance between two colours (alpha ignored)."""
    return math.dist(lab(a), lab(b))


def over(fg, bg):
    """fg composited over an opaque bg."""
    a = fg[3]
    return tuple(fg[i] * a + bg[i] * (1 - a) for i in range(3)) + (1.0,)


def contrast(fg, bg):
    """WCAG 2 contrast ratio of fg (composited) on bg."""
    def _lum(c):
        r, g, b = (_lin(v) for v in c[:3])
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    la, lb = _lum(over(fg, bg)), _lum(bg)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


# ---------- text helpers ----------
def split_top(s, sep):
    """s split on sep where it isn't inside brackets or quotes."""
    out, depth, cur, q = [], 0, [], None
    for ch in s:
        if q:
            q = None if ch == q else q
        elif ch in "\"'":
            q = ch
        elif ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        elif ch == sep and depth == 0:
            out.append("".join(cur))
            cur = []
            continue
        cur.append(ch)
    out.append("".join(cur))
    return out


class Lines:
    """Offset to line number within a text that starts at line `first` of its file."""

    def __init__(self, text, first=1):
        self.nl = [i for i, c in enumerate(text) if c == "\n"]
        self.first = first

    def at(self, off):
        """The file line of character `off`."""
        return self.first + bisect.bisect_right(self.nl, off - 1)


def rel(p):
    """A path relative to the repository, as printed in findings."""
    try:
        return str(Path(p).relative_to(ROOT))
    except ValueError:
        return str(p)


def colour_literals(value, prop=""):
    """[(literal, rgba)] for the colours written into a value (url() skipped; named colours only in colour properties)."""
    v = URL.sub(" ", value)
    out = []
    for m in HEX.finditer(v):
        out.append((m.group(0), _hex_rgba(m.group(0))))
    for m in FUNC.finditer(v):
        c = parse_colour(m.group(0))
        if c:
            out.append((m.group(0), c))
    if COLOUR_PROPS.match(prop) or prop.startswith("--"):
        for m in WORD.finditer(re.sub(r"var\([^)]*\)|\"[^\"]*\"|'[^']*'", " ", v)):
            w = m.group(1).lower()
            if w in NAMED:
                out.append((m.group(1), _hex_rgba(NAMED[w])))
    return out


# ---------- CSS parsing ----------
STRING_OR_COMMENT = re.compile(r"/\*.*?\*/|\"(?:\\.|[^\"\\\n])*\"|'(?:\\.|[^'\\\n])*'", re.S)
GROUPING = ("@media", "@supports", "@container", "@layer", "@document")


def _blank(text, strings):
    def _repl(m):
        s = m.group(0)
        if s.startswith("/*"):
            return re.sub(r"[^\n]", " ", s)
        return s[0] + "x" * (len(s) - 2) + s[-1] if strings else s
    return STRING_OR_COMMENT.sub(_repl, text)


def _close(mask, pos):
    depth = 0
    for m in re.compile(r"[{}]").finditer(mask, pos):
        depth += 1 if m.group(0) == "{" else -1
        if depth == 0:
            return m.start()
    return len(mask)


def _decls(clean, mask, s, e, lines):
    out, depth, start = [], 0, s
    for i in range(s, e + 1):
        ch = mask[i] if i < e else ";"
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == ";" and depth <= 0:
            seg = clean[start:i]
            if ":" in seg and seg.strip():
                k = seg.index(":")
                prop = seg[:k].strip()
                lead = len(seg) - len(seg.lstrip())
                if prop and not re.search(r"[{}]", prop):
                    out.append({"prop": prop if prop.startswith("--") else prop.lower(), "value": seg[k + 1:].strip(),
                                "line": lines.at(start + lead)})
            start, depth = i + 1, 0
    return out


def parse_css(text, path, first=1):
    """Every rule in a stylesheet: {file, line, sel, media (the enclosing @-preludes), at, kf, decls, order}."""
    clean, mask, lines = _blank(text, False), _blank(text, True), Lines(text, first)
    rules = []

    def _walk(s, e, media, kf):
        i = s
        while i < e:
            m = re.compile(r"[{;}]").search(mask, i, e)
            if not m:
                return
            if m.group(0) != "{":
                i = m.end()
                continue
            prelude, close = " ".join(clean[i:m.start()].split()), _close(mask, m.start())
            low = prelude.lower()
            if low.startswith(GROUPING):
                _walk(m.end(), close, media + (prelude,), kf)
            elif low.startswith("@keyframes") or low.startswith("@-webkit-keyframes"):
                _walk(m.end(), close, media, True)
            else:
                off = i + len(clean[i:m.start()]) - len(clean[i:m.start()].lstrip())
                rules.append({"file": rel(path), "line": lines.at(off), "sel": prelude, "media": media,
                              "at": prelude.startswith("@"), "kf": kf, "order": len(rules),
                              "decls": _decls(clean, mask, m.end(), close, lines)})
            i = close + 1
    _walk(0, len(mask), (), False)
    return rules


def inline_decls(style, path, line):
    """Declarations of a style="" attribute (or a style string in JS), all on one line."""
    out = []
    for seg in split_top(style, ";"):
        if ":" in seg:
            k = seg.index(":")
            prop = seg[:k].strip()
            if re.fullmatch(r"-{0,2}[a-zA-Z][\w-]*", prop):
                out.append({"prop": prop if prop.startswith("--") else prop.lower(), "value": seg[k + 1:].strip(),
                            "line": line, "file": rel(path)})
    return out


# ---------- theme roots and the cascade ----------
ROOT_PART = re.compile(r'\[data-(palette|theme)(?:="([^"]*)")?\]|:not\(\[data-theme="(light|dark)"\]\)|\.([\w-]+)')
MEDIA_SCHEME = re.compile(r"@media\s*\(\s*prefers-color-scheme\s*:\s*(dark|light)\s*\)\s*$", re.I)


def root_parts(sel):
    """For a `:root…` selector, its attribute constraints [(kind, value)]; None when it isn't a theme root."""
    sel = sel.strip()
    if not sel.startswith(":root"):
        return None
    rest, parts, pos = sel[5:], [], 0
    for m in ROOT_PART.finditer(rest):
        if m.start() != pos:
            return None
        if m.group(1):
            parts.append((m.group(1), m.group(2)))
        elif m.group(3):
            parts.append(("not-theme", m.group(3)))
        else:
            parts.append(("class", m.group(4)))
        pos = m.end()
    return parts if pos == len(rest) else None


def media_kind(media):
    """'none', 'dark', 'light' (a prefers-color-scheme query alone) or 'other'."""
    if not media:
        return "none"
    kinds = set()
    for q in media:
        m = MEDIA_SCHEME.match(q)
        if not m:
            return "other"
        kinds.add(m.group(1).lower())
    return kinds.pop() if len(kinds) == 1 else "other"


def _part_ok(kind, val, palette, theme):
    if kind == "palette":
        return palette is not None and (val is None or val == palette)
    if kind == "theme":
        return theme is not None and (val is None or val == theme)
    if kind == "not-theme":
        return theme != val
    return False


def root_match(rule, palette, theme, dark):
    """The specificity with which a theme-root rule applies in an environment, or None."""
    if rule["at"] or rule["kf"]:
        return None
    mk = media_kind(rule["media"])
    if mk == "other" or (mk == "dark" and not dark) or (mk == "light" and dark):
        return None
    best = None
    for sel in split_top(rule["sel"], ","):
        parts = root_parts(sel)
        if parts is not None and all(_part_ok(k, v, palette, theme) for k, v in parts):
            best = max(best or 0, 1 + len(parts))
    return best


def is_root_rule(rule):
    """True when every selector of the rule is a theme root and its media is none or a colour-scheme query."""
    if rule["at"] or rule["kf"] or media_kind(rule["media"]) == "other":
        return False
    return all(root_parts(s) is not None for s in split_top(rule["sel"], ","))


def effective(rules, palette, env):
    """{token: {value, file, line}} as the browser resolves the root's custom properties in one environment."""
    theme, dark = ENVS[env]
    hits = []
    for r in rules:
        spec = root_match(r, palette, theme, dark)
        if spec is not None:
            hits.append((spec, r["order"], r))
    out = {}
    for _, _, r in sorted(hits, key=lambda h: (h[0], h[1])):
        for d in r["decls"]:
            if d["prop"].startswith("--"):
                out[d["prop"]] = {"value": d["value"], "file": r["file"], "line": d["line"]}
    return out


def _var_end(s, i):
    depth = 0
    for j in range(i, len(s)):
        depth += {"(": 1, ")": -1}.get(s[j], 0)
        if depth == 0:
            return j
    return len(s) - 1


def resolve(value, tokens, depth=0):
    """value with every var() replaced from tokens (fallbacks honoured); None when something can't be resolved."""
    if depth > 12:
        return None
    out, i = [], 0
    while True:
        j = value.find("var(", i)
        if j < 0:
            out.append(value[i:])
            return "".join(out)
        end = _var_end(value, j + 3)
        args = split_top(value[j + 4:end], ",")
        name, fb = args[0].strip(), (",".join(args[1:]).strip() if len(args) > 1 else None)
        if name in tokens:
            sub = resolve(tokens[name]["value"], tokens, depth + 1)
        else:
            sub = resolve(fb, tokens, depth + 1) if fb is not None else None
        if sub is None:
            return None
        out.append(value[i:j] + sub)
        i = end + 1


def token_colour(name, tokens):
    """The rgba of a token in a resolved environment, or None."""
    if name not in tokens:
        return None
    v = resolve(tokens[name]["value"], tokens)
    return parse_colour(v) if v is not None else None


def rule_palettes(rule):
    """The palettes a rule is limited to by `[data-palette="X"]` in every selector, or None when it isn't limited."""
    found = set()
    for sel in split_top(rule.get("sel", ""), ","):
        m = re.search(r'\[data-palette="([^"]+)"\]', sel)
        if not m:
            return None
        found.add(m.group(1))
    return found or None


def rule_dark(rule):
    """True when a rule applies only in dark mode."""
    sel = rule.get("sel", "")
    return '[data-theme="dark"]' in sel or media_kind(rule.get("media", ())) == "dark"


# ---------- surfaces ----------
def new_surface(name, primary):
    """An empty surface: its rules, inline declarations, JS facts and the files it was read from."""
    return {"name": name, "file": rel(primary), "rules": [], "inline": [], "js_uses": [], "js_defs": [],
            "js_colours": [], "palettes": [None], "default": None, "themes_ids": None, "files": []}


STYLE_BLOCK = re.compile(r"<style[^>]*>(.*?)</style>", re.S | re.I)
STYLE_ATTR = re.compile(r"""\bstyle\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.I)


def read_html(surface, path):
    """Adds an HTML file's <style> blocks and style="" attributes to a surface."""
    text = path.read_text(encoding="utf-8")
    lines = Lines(text)
    surface["files"].append(rel(path))
    for m in STYLE_BLOCK.finditer(text):
        css = m.group(1)
        if css.strip() == "/*__SPLIT_CSS__*/":
            continue
        for r in parse_css(css, path, lines.at(m.start(1))):
            r["order"] = len(surface["rules"])
            surface["rules"].append(r)
    for m in STYLE_ATTR.finditer(text):
        surface["inline"] += inline_decls(m.group(1) or m.group(2) or "", path, lines.at(m.start()))


def read_css_file(surface, path):
    """Adds a stylesheet to a surface."""
    surface["files"].append(rel(path))
    for r in parse_css(path.read_text(encoding="utf-8"), path):
        r["order"] = len(surface["rules"])
        surface["rules"].append(r)


def python_css(path):
    """[(name, css, first line)] for the module-level string constants named *CSS in a Python file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id.endswith("CSS"):
                    out.append((t.id, node.value.value, node.value.lineno))
    return out


JS_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)
JS_LINE_COMMENT = re.compile(r"(^|\s)//.*$", re.M)
VAR_USE = re.compile(r"var\(\s*(--[\w-]+)\s*(,)?")
JS_GET = re.compile(r"getPropertyValue\(\s*[\"'`](--[\w-]+)")
JS_SET = re.compile(r"setProperty\(\s*[\"'`](--[\w-]+)")
JS_DEF = re.compile(r"(?<=[\"'`;{\s])(--[a-zA-Z][\w-]*)\s*:(?!:)")
JS_SHORT_HEX = re.compile(r"(?:(?<=:)\s*|(?<==)\s*[\"'`])(#[0-9a-fA-F]{3,4})(?![\w-])")
JS_LONG_HEX = re.compile(r"(?<![\w&-])#([0-9a-fA-F]{8}|[0-9a-fA-F]{6})(?![\w-])")
JS_INTENTIONAL = re.compile(r"\b(THEMES|DE_COLOURS)\s*=|\b(fillStyle|strokeStyle)\s*=")


def read_js(surface, path):
    """Adds a JS module's token reads and writes, inline style strings and colour literals to a surface."""
    raw = path.read_text(encoding="utf-8")
    text = JS_LINE_COMMENT.sub(lambda m: m.group(1), JS_BLOCK_COMMENT.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), raw))
    surface["files"].append(rel(path))
    for n, line in enumerate(text.split("\n"), 1):
        for m in VAR_USE.finditer(line):
            surface["js_uses"].append({"name": m.group(1), "fallback": bool(m.group(2)), "file": rel(path), "line": n})
        for m in JS_GET.finditer(line):
            surface["js_uses"].append({"name": m.group(1), "fallback": True, "file": rel(path), "line": n})
        for rx in (JS_SET, JS_DEF):
            for m in rx.finditer(line):
                surface["js_defs"].append({"name": m.group(1), "file": rel(path), "line": n})
        intentional = bool(JS_INTENTIONAL.search(line))
        lits = [(m.group(0), _hex_rgba(m.group(0))) for m in JS_LONG_HEX.finditer(line)]
        lits += [(m.group(1), _hex_rgba(m.group(1))) for m in JS_SHORT_HEX.finditer(line)]
        lits += [(m.group(0), parse_colour(m.group(0))) for m in FUNC.finditer(line) if parse_colour(m.group(0))]
        for lit, c in lits:
            surface["js_colours"].append({"literal": lit, "rgba": c, "file": rel(path), "line": n, "intentional": intentional})


def load_dashboard():
    """The dashboard: style.css, shell.html and every module in src/, with THEMES and the default palette from page.js."""
    s = new_surface("dashboard", DASH / "style.css")
    read_css_file(s, DASH / "style.css")
    read_html(s, DASH / "shell.html")
    for js in sorted((DASH / "src").rglob("*.js")):
        read_js(s, js)
    page = (DASH / "src" / "core" / "page.js")
    text = page.read_text(encoding="utf-8") if page.exists() else ""
    m = re.search(r"export const THEMES\s*=\s*\[(.*?)\];", text, re.S)
    s["themes_ids"] = re.findall(r'\{id:"([^"]+)"', m.group(1)) if m else None
    d = re.search(r'themeOf=.*?\|\|THEMES\.find\(t=>t\.id==="([^"]+)"\)', text)
    css_palettes = sorted({p for r in s["rules"] if is_root_rule(r) for p in (rule_palettes(r) or ())})
    s["css_palettes"] = css_palettes
    s["palettes"] = s["themes_ids"] or css_palettes or [None]
    s["default"] = d.group(1) if d else (s["palettes"][0])
    return s


def load_surfaces():
    """Every surface creaite produces, keyed by name; missing optional files are skipped."""
    out = {"dashboard": load_dashboard()}
    for name, fn in (("guide-first-day", "guide-first-day.html"), ("guide-how-to", "guide-how-to.html"),
                     ("offline", "app/offline.html")):
        if (TPL / fn).exists():
            out[name] = new_surface(name, TPL / fn)
            read_html(out[name], TPL / fn)
    prep = new_surface("prep-page", SCRIPTS / "prep_page.py")
    for py in (SCRIPTS / "prep_page.py", SCRIPTS / "prep_view.py"):
        if py.exists():
            prep["files"].append(rel(py))
            for _, css, first in python_css(py):
                for r in parse_css(css, py, first):
                    r["order"] = len(prep["rules"])
                    prep["rules"].append(r)
    if prep["rules"]:
        out["prep-page"] = prep
    ref = ROOT / "dev" / "reference" / "dashboard-reference.html"
    if ref.exists():
        out["reference"] = new_surface("reference", ref)
        read_html(out["reference"], ref)
    for s in out.values():
        if s["name"] != "dashboard":
            pals = sorted({p for r in s["rules"] if is_root_rule(r) for p in (rule_palettes(r) or ())})
            s["palettes"] = pals or [None]
            s["default"] = s["palettes"][0]
    return out


# ---------- token facts ----------
def definitions(s):
    """[{name, file, line, scope}] for every token a surface defines (root, local, @property, keyframes or JS)."""
    out = []
    for r in s["rules"]:
        if r["at"] and r["sel"].lower().startswith("@property"):
            out.append({"name": r["sel"].split()[1], "file": r["file"], "line": r["line"], "scope": "property"})
            continue
        scope = "root" if is_root_rule(r) else ("keyframes" if r["kf"] else "local")
        for d in r["decls"]:
            if d["prop"].startswith("--"):
                out.append({"name": d["prop"], "file": r["file"], "line": d["line"], "scope": scope, "rule": r})
    out += [{"name": d["prop"], "file": d["file"], "line": d["line"], "scope": "inline"} for d in s["inline"]
            if d["prop"].startswith("--")]
    out += [dict(d, scope="js") for d in s["js_defs"]]
    return out


def uses(s):
    """[{name, fallback, file, line, rule}] for every var() read (CSS, inline styles, JS) and JS getPropertyValue."""
    out = []
    for r in s["rules"]:
        for d in r["decls"]:
            for m in VAR_USE.finditer(d["value"]):
                out.append({"name": m.group(1), "fallback": bool(m.group(2)), "file": r["file"], "line": d["line"], "rule": r})
    for d in s["inline"]:
        for m in VAR_USE.finditer(d["value"]):
            out.append({"name": m.group(1), "fallback": bool(m.group(2)), "file": d["file"], "line": d["line"], "rule": None})
    return out + [dict(u, rule=None) for u in s["js_uses"]]


def env_maps(s):
    """{palette: {env: tokens}} for a surface's palettes in the four environments. A surface whose roots never test
    data-theme (the prep page, the offline page) has only the system's light and dark, so its "dark" is the system's."""
    attr = any("data-theme" in r["sel"] for r in s["rules"] if is_root_rule(r))
    out = {}
    for p in s["palettes"]:
        m = {e: effective(s["rules"], p, e) for e in ENVS}
        if not attr:
            m["dark"], m["forced-light"] = m["system-dark"], m["light"]
        out[p] = m
    return out


def pname(p):
    """A palette's printable name (the surface's own base when it has none)."""
    return p if p is not None else "base"


def finding(check, sev, file, line, msg, surface, **data):
    """One finding."""
    f = {"check": check, "sev": sev, "file": file, "line": line, "msg": msg, "surface": surface}
    if data:
        f["data"] = data
    return f


# ---------- checks 1 and 2 ----------
def check_unused_undefined(s, defs, used):
    """Check 1 (defined, never read) and check 2 (read, never defined) for one surface."""
    out = []
    names_used = {u["name"] for u in used}
    names_def = {d["name"] for d in defs}
    first_def = {}
    for d in defs:
        first_def.setdefault(d["name"], d)
    for name in sorted(names_def - names_used):
        d = first_def[name]
        if SCALE_TOKEN.match(name):
            continue      # BL-325: a step of the declared scale is there to be used, not a leftover

        n = sum(1 for x in defs if x["name"] == name)
        sev = "P3" if d["scope"] in ("js", "inline", "keyframes") else "P2"
        out.append(finding(1, sev, d["file"], d["line"], f"{name} is defined ({n}x, {d['scope']}) but never read", s["name"]))
    seen = set()
    for u in used:
        if u["name"] in names_def or (u["name"], u["fallback"]) in seen:
            continue
        seen.add((u["name"], u["fallback"]))
        n = sum(1 for x in used if x["name"] == u["name"])
        if u["fallback"]:
            out.append(finding(2, "P3", u["file"], u["line"], f"{u['name']} is never defined; its {n} read(s) rely on the fallback",
                               s["name"]))
        else:
            out.append(finding(2, "P1", u["file"], u["line"], f"{u['name']} is read ({n}x) but defined nowhere", s["name"]))
    return out


# ---------- check 3 ----------
def _palette_block_names(s, palette, dark):
    names = set()
    for r in s["rules"]:
        if not is_root_rule(r) or rule_palettes(r) != {palette}:
            continue
        has_dark = rule_dark(r)
        if has_dark == dark:
            names |= {d["prop"] for d in r["decls"] if d["prop"].startswith("--")}
    return names


def _env_diffs(maps, a, b):
    out = []
    for name in sorted(set(maps[a]) | set(maps[b])):
        va, vb = maps[a].get(name, {}).get("value"), maps[b].get(name, {}).get("value")
        if va != vb:
            out.append((name, va, vb))
    return out


def _themes_vs_css(s):
    out = []
    if s.get("themes_ids") is None:
        return out
    ids, css = set(s["themes_ids"]), set(s.get("css_palettes", []))
    for p in sorted(ids - css):
        out.append(finding(3, "P1", "system/templates/dashboard/src/core/page.js", None,
                           f'THEMES lists "{p}" but style.css has no [data-palette="{p}"] token block', s["name"]))
    for p in sorted(css - ids):
        out.append(finding(3, "P2", s["file"], None, f'style.css styles palette "{p}", which THEMES does not offer', s["name"]))
    return out


def _dark_parity(s, maps):
    out = []
    for p, m in maps.items():
        for a, b, what in (("system-dark", "dark", "system dark (prefers-color-scheme) and explicit dark (data-theme)"),
                           ("forced-light", "light", "forced light (data-theme=light under a dark system) and light")):
            diffs = _env_diffs(m, a, b)
            if diffs:
                eg = "; ".join(f"{n} {va} vs {vb}" for n, va, vb in diffs[:4])
                loc = m[a].get(diffs[0][0]) or m[b].get(diffs[0][0])
                out.append(finding(3, "P1", loc["file"], loc["line"],
                                   f"{pname(p)}: {len(diffs)} token(s) differ between {what}: {eg}", s["name"],
                                   tokens=[d[0] for d in diffs]))
    return out


def _light_only(s, maps):
    out = []
    for p in s["palettes"]:
        if p is None:
            continue
        light, dark = _palette_block_names(s, p, False), _palette_block_names(s, p, True)
        if not dark:
            continue
        lone = []
        for n in sorted(light - dark):
            v = maps[p]["light"].get(n)
            if v and "var(" not in v["value"] and parse_colour(resolve(v["value"], maps[p]["light"]) or ""):
                lone.append(n)
        if lone:
            v = maps[p]["light"][lone[0]]
            out.append(finding(3, "P2", v["file"], v["line"],
                               f"{p}: {len(lone)} colour token(s) set for light only, so dark mode shows the light value: "
                               + ", ".join(lone[:8]), s["name"], tokens=lone))
    return out


def _use_missing(u, s, maps):
    pals = (rule_palettes(u["rule"]) if u["rule"] else None) or s["palettes"]
    modes = ("dark",) if u["rule"] and rule_dark(u["rule"]) else ("light", "dark")
    return {f"{pname(p)} {e}" for p in pals if p in maps for e in modes if u["name"] not in maps[p][e]}


def _unscoped_missing(s, maps, defs, used):
    local = {d["name"] for d in defs if d["scope"] != "root"}
    gaps = defaultdict(lambda: {"uses": 0, "where": set(), "first": None})
    defined = {d["name"] for d in defs}
    for u in used:
        if u["fallback"] or u["name"] in local or u["name"] not in defined:
            continue
        miss = _use_missing(u, s, maps)
        if miss:
            g = gaps[u["name"]]
            g["uses"] += 1
            g["where"] |= miss
            g["first"] = g["first"] or u
    out = []
    for name, g in sorted(gaps.items()):
        u = g["first"]
        where = sorted(g["where"])
        out.append(finding(3, "P1", u["file"], u["line"],
                           f"{name} is read with no fallback ({g['uses']}x) but is undefined in {len(where)} palette/mode(s): "
                           + ", ".join(where[:6]) + (" …" if len(where) > 6 else ""), s["name"], missing=where))
    return out


def coverage(s, maps):
    """Per palette: how many root tokens it sets itself (light, dark) and how many it takes from the base."""
    rows = []
    base_names = set(effective(s["rules"], None, "light")) | set(effective(s["rules"], None, "dark"))
    for p in s["palettes"]:
        if p is None:
            continue
        light, dark = _palette_block_names(s, p, False), _palette_block_names(s, p, True)
        inherited = sorted(base_names - light - dark)
        rows.append({"palette": p, "light": len(light), "dark": len(dark), "from_base": len(inherited),
                     "total_light": len(maps[p]["light"]), "total_dark": len(maps[p]["dark"]), "inherited": inherited})
    return rows


def check_themes(s, maps, defs, used):
    """Check 3 for one surface."""
    return _themes_vs_css(s) + _dark_parity(s, maps) + _light_only(s, maps) + _unscoped_missing(s, maps, defs, used)


# ---------- check 4 ----------
def value_index(tokens):
    """{#HEX: [token names]} for the root colour tokens of one environment."""
    idx = defaultdict(list)
    for name in tokens:
        c = token_colour(name, tokens)
        if c:
            idx[hexof(c)].append(name)
    return idx


GROUND_HINT = re.compile(r"(^--(bg|surface|sunk|card|paper|ground|page|band|inverse)\b|-soft$|-page$|-band$)")
INK_HINT = re.compile(r"(ink|muted|faint|fg|text)$")


def rank_candidates(prop, names):
    """Token names that match a literal, the likeliest first: an ink for color/fill, a ground for background."""
    fore = prop in ("color", "fill", "stroke", "string", "caret-color", "text-decoration-color")
    def _score(n):
        hint = INK_HINT.search(n) if fore else GROUND_HINT.search(n)
        return (0 if hint else 1, n.count("-"), n)
    return sorted(names, key=_score)


def _intentional(rule, prop, rgba):
    media = " ".join(rule.get("media", ())).lower() if rule else ""
    sel = rule.get("sel", "") if rule else ""
    if "print" in media:
        return "print styles"
    if "#deprev" in sel.lower():
        return "the Word preview's own colours"
    if "#imgbig" in sel.lower():
        return "the image viewer's backing and scrim"
    neutral = rgba[:3] in ((0, 0, 0), (255, 255, 255))
    if neutral and (prop in ("box-shadow", "text-shadow", "filter", "drop-shadow") or "shadow" in prop):
        return "a shadow"
    if neutral and rgba[3] < 1 and re.search(r"backdrop|scrim|overlay|dialog|modal", sel, re.I):
        return "a scrim"
    return None


def _colour_finding(s, idx_for, lit, rgba, prop, rule, file, line, where):
    pals = (rule_palettes(rule) if rule else None) or {s["default"]}
    mode = "dark" if rule and rule_dark(rule) else "light"
    cands = rank_candidates(prop, {n for p in pals for n in idx_for(p, mode).get(hexof(rgba), [])})
    why = _intentional(rule, prop, rgba)
    if why:
        return finding(4, "P3", file, line, f"{where} {prop}: {lit} (fixed on purpose: {why})"
                       + (f"; equals {', '.join(cands[:3])}" if cands else ""), s["name"], literal=lit)
    if cands:
        return finding(4, "P1", file, line, f"{where} {prop}: {lit} equals {', '.join(cands[:4])} in "
                       f"{'/'.join(pname(p) for p in sorted(pals, key=str))} {mode}: should be var({cands[0]})",
                       s["name"], literal=lit, candidates=cands)
    return finding(4, "P2", file, line, f"{where} {prop}: {lit} is a literal colour with no matching token", s["name"],
                   literal=lit)


def var_fallbacks(value):
    """(value with every var() removed, the text of their fallbacks): a literal in a fallback is reported apart."""
    kept, fbs, i = [], [], 0
    while True:
        j = value.find("var(", i)
        if j < 0:
            kept.append(value[i:])
            return "".join(kept), " ".join(fbs)
        end = _var_end(value, j + 3)
        args = split_top(value[j + 4:end], ",")
        if len(args) > 1:
            fbs.append(",".join(args[1:]))
        kept.append(value[i:j] + " ")
        i = end + 1


def check_hardcoded(s, maps):
    """Check 4 for one surface: colour literals in rules, inline styles and JS."""
    cache = {}

    def _idx_for(p, mode):
        if (p, mode) not in cache:
            cache[(p, mode)] = value_index(maps[p][mode]) if p in maps else {}
        return cache[(p, mode)]
    out = []
    for r in s["rules"]:
        if any("forced-colors" in q.lower() for q in r["media"]):
            continue
        for d in r["decls"]:
            if d["prop"].startswith("--"):
                continue
            plain, fallback = var_fallbacks(d["value"])
            for lit, c in colour_literals(plain, d["prop"]):
                out.append(_colour_finding(s, _idx_for, lit, c, d["prop"], r, r["file"], d["line"], "rule"))
            for lit, _ in colour_literals(fallback, d["prop"]):
                out.append(finding(4, "P3", r["file"], d["line"], f"rule {d['prop']}: {lit} is a var() fallback (dead while "
                                   "the token is defined; it drifts unseen)", s["name"], literal=lit))
    for d in s["inline"]:
        if not d["prop"].startswith("--"):
            for lit, c in colour_literals(d["value"], d["prop"]):
                out.append(_colour_finding(s, _idx_for, lit, c, d["prop"], None, d["file"], d["line"], 'style=""'))
    fixed = defaultdict(list)
    for j in s["js_colours"]:
        if j["intentional"]:
            fixed[(j["file"], j["line"])].append(j["literal"])
        else:
            out.append(_colour_finding(s, _idx_for, j["literal"], j["rgba"], "string", None, j["file"], j["line"], "JS"))
    for (f, ln), lits in sorted(fixed.items()):
        out.append(finding(4, "P3", f, ln, f"JS: {len(lits)} literal colour(s) in a fixed list or canvas paint (THEMES "
                           "swatches, DE_COLOURS, a canvas fillStyle; by design)", s["name"], literals=lits))
    return out


# ---------- check 5 ----------
SCALES = ("font-size", "font-weight", "line-height", "border-radius", "box-shadow", "z-index", "spacing", "duration")
# BL-325: the one design scale. A surface that defines it (--fs-* among its root tokens) is held to it for these five
# scales: no font size, radius, shadow or z-index outside its tokens and spacing only on the steps below, bar the
# exceptions on_scale() lists. The scale's own tokens are never reported as unused.
ON_SCALE = ("font-size", "border-radius", "box-shadow", "z-index", "spacing")
SPACING_SCALE = {0, 2, 4, 6, 8, 10, 12, 14, 16, 20, 24, 28, 32, 40, 48, 56, 64, 72, 80, 96, 112, 128}
SCALE_TOKEN = re.compile(r"^--(fs|r|z|ctl)-|^--shadow-(sm|md|lg|side)$")
DIST_LIMIT = {"font-size": 8, "font-weight": 5, "line-height": 8, "border-radius": 6, "box-shadow": 6, "z-index": 8,
              "spacing": 20, "duration": 6}
SKIP_VALUES = {"0", "auto", "inherit", "initial", "unset", "none", "normal", "revert", "0px", "0ms", "0s"}
FONT_SIZE = re.compile(r"(?<![\w.#-])(\d*\.?\d+(?:px|r?em|%|pt)|var\([^)]*\))(?:\s*/\s*(\d*\.?\d+(?:px|r?em|%)?|var\([^)]*\)|normal))?")
FONT_WEIGHT = re.compile(r"(?<![\w.-])([1-9]00|bold|bolder|lighter)(?![\w.-])")
DURATION = re.compile(r"(?<![\w.-])(\d*\.?\d+m?s)(?![\w-])|(var\(--[\w-]+\))")


def _scale_items(prop, value):
    """[(scale, raw value or None, token or None)] for one declaration."""
    v = value.replace("!important", "").strip()
    if prop == "font":
        return _font_items(v)
    if prop in ("font-size", "font-weight", "line-height", "z-index", "box-shadow"):
        return [_one(prop, v)]
    if prop == "border-radius" or re.fullmatch(r"border-[a-z-]*radius", prop):
        return [_one("border-radius", p) for p in v.split() if p != "/"]
    if re.fullmatch(r"(margin|padding)(-[a-z-]+)?|gap|row-gap|column-gap", prop):
        return [_one("spacing", p) for p in split_top(v, " ") if p.strip()]
    if prop.startswith("transition") or prop.startswith("animation"):
        return [("duration", m.group(1), None) if m.group(1) else ("duration", None, m.group(2))
                for m in DURATION.finditer(v)]
    return []


def _one(scale, v):
    v = v.strip()
    if v.startswith("env("):
        return (scale, None, None)
    if "var(" in v and not v.startswith("calc"):
        m = re.search(r"var\((--[\w-]+)", v)
        return (scale, None, m.group(1))
    return (scale, v, None)


def _font_items(v):
    if v in SKIP_VALUES or v.startswith("var("):
        return []
    out = []
    m = FONT_SIZE.search(v)
    if m:
        out.append(_one("font-size", m.group(1)))
        if m.group(2):
            out.append(_one("line-height", m.group(2)))
        w = FONT_WEIGHT.search(v[:m.start()])
        if w:
            out.append(("font-weight", w.group(1), None))
    return out


def scale_usage(s):
    """{scale: {"raw": Counter, "tokens": Counter, "where": {value: file:line}}} over a surface's rules and inline styles."""
    out = {k: {"raw": Counter(), "tokens": Counter(), "where": {}} for k in SCALES}
    decls = [(d, r["file"]) for r in s["rules"] if not r["kf"] for d in r["decls"] if not d["prop"].startswith("--")]
    decls += [(d, d["file"]) for d in s["inline"] if not d["prop"].startswith("--")]
    for d, f in decls:
        for scale, raw, tok in _scale_items(d["prop"], d["value"]):
            if tok:
                out[scale]["tokens"][tok] += 1
            elif raw and raw.lower() not in SKIP_VALUES:
                key = " ".join(raw.split())
                out[scale]["raw"][key] += 1
                out[scale]["where"].setdefault(key, f"{f}:{d['line']}")
    return out


def _measure(scale, v):
    m = re.fullmatch(r"(-?\d*\.?\d+)(px|rem|em|%|pt|ms|s)?", v)
    if not m:
        return None
    n, unit = float(m.group(1)), m.group(2) or ""
    if unit == "s":
        n, unit = n * 1000, "ms"
    return (unit, n)


def near_clusters(scale, counter):
    """Groups of numeric values in one unit that sit within a step of the group's smallest (1px or 8%; 15% for time)."""
    by_unit = defaultdict(list)
    for v, n in counter.items():
        m = _measure(scale, v)
        if m and scale not in ("z-index", "font-weight"):
            by_unit[m[0]].append((m[1], v, n))
    out = []
    for unit, vals in by_unit.items():
        vals.sort()
        group = []
        for x in vals:
            first = group[0][0] if group else None
            lim = (0.15 * abs(first) if scale == "duration" else max(1.0 if unit == "px" else 0.05, 0.08 * abs(first or 0))) \
                if group else 0
            if group and abs(x[0] - first) <= lim + 1e-9:
                group.append(x)
            else:
                if len(group) > 1:
                    out.append(group)
                group = [x]
        if len(group) > 1:
            out.append(group)
    return out


def on_scale(scale, v):
    """BL-325: is a raw value allowed on a surface that defines the one design scale? Font sizes, radii, shadows and
    z-index are written as tokens, bar the listed exceptions; spacing is written in px and must be a step of the scale."""
    v = v.strip()
    if scale == "font-size":
        return bool(re.fullmatch(r"\d*\.?\d+em", v))                 # relative to the text around it (inline code, kbd)
    if scale == "border-radius":
        return v in ("50%", "0")                                       # a circle
    if scale == "box-shadow":
        return "inset" in v or v.startswith("0 0 0 ") or "var(--pixel)" in v   # bars, rings, Retro Arcade's pixel offset
    if scale == "z-index":
        return False
    if scale == "spacing":
        m = re.fullmatch(r"(-?\d*\.?\d+)px", v)
        if not m:
            return True                                                # em, ch, %, calc(): relative by design
        n = abs(float(m.group(1)))
        return n == 1 or n in SPACING_SCALE                            # 1px: a hairline nudge
    return True


def defines_scale(s):
    """True when a surface defines BL-325's scale tokens (the dashboard, and the guides that copy them)."""
    return any(d["prop"].startswith("--fs-") for r in s["rules"] if is_root_rule(r) for d in r["decls"])


def check_scales(s, usage):
    """Check 5 for one surface: values off the declared scale (BL-325), or, where a surface has no scale, too many raw
    values per scale; and near-duplicate values."""
    out = []
    scaled = defines_scale(s)
    for scale in SCALES:
        u = usage[scale]
        raw_n, tok_n = sum(u["raw"].values()), sum(u["tokens"].values())
        if scaled and scale in ON_SCALE:
            off = [(v, n) for v, n in u["raw"].most_common() if not on_scale(scale, v)]
            for v, n in off:
                out.append(finding(5, "P2", s["file"], None, f"{scale}: {v} ({n}) is off the scale"
                                   + (" (write a token)" if scale != "spacing" else " (use a step of the 4px scale)")
                                   + (f", e.g. {u['where'][v]}" if u["where"].get(v) else ""),
                                   s["name"], value=v, example=u["where"].get(v)))
            continue
        if len(u["raw"]) > DIST_LIMIT[scale] and raw_n > tok_n:
            out.append(finding(5, "P2", s["file"], None, f"{scale}: {len(u['raw'])} distinct raw values in {raw_n} uses, "
                               f"against {tok_n} tokenised uses ({len(u['tokens'])} tokens): no scale is being followed",
                               s["name"]))
        for g in near_clusters(scale, u["raw"]):
            keep = max(g, key=lambda x: x[2])
            vals = ", ".join(f"{v} ({n})" for _, v, n in g)
            rare = [v for _, v, n in g if v != keep[1]]
            out.append(finding(5, "P3", s["file"], None, f"{scale} near-duplicates: {vals}; fold into {keep[1]}?",
                               s["name"], values=[v for _, v, _ in g], examples={v: u["where"][v] for v in rare[:3]}))
    return out


# ---------- check 6 ----------
def token_kind(name):
    """'ground' for fills and backgrounds, 'ink' for text and marks: near-duplicates only matter within a kind."""
    if GROUND_HINT.search(name) or name in ("--line", "--line-strong", "--tx-tint", "--knob") or "rule" in name or "hair" in name:
        return "ground"
    return "ink"


def _colour_pairs(toks):
    """(a, b, ΔE or 0 when identical, hex a, hex b) for same-kind opaque colour tokens closer than NEAR_DE."""
    cols = {n: token_colour(n, toks) for n in toks}
    cols = {n: c for n, c in cols.items() if c and c[3] >= 0.999}
    names, out = sorted(cols), []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if token_kind(a) != token_kind(b) or f"var({a})" in toks[b]["value"] or f"var({b})" in toks[a]["value"]:
                continue
            ha, hb = hexof(cols[a]), hexof(cols[b])
            d = 0 if ha == hb else delta_e(cols[a], cols[b])
            if d < NEAR_DE:
                out.append((a, b, d, ha, hb))
    return out


def check_duplicates(s, maps):
    """Check 6 for one surface: root colour tokens with the same or nearly the same value, gathered across themes."""
    same, near = defaultdict(list), defaultdict(list)
    for p, envs in maps.items():
        for e in ("light", "dark"):
            for a, b, d, ca, cb in _colour_pairs(envs[e]):
                if d == 0:
                    same[(a, b)].append(f"{pname(p)} {e}")
                else:
                    near[(a, b)].append(f"{pname(p)} {e} ({ca}/{cb}, ΔE {d:.1f})")
    total = len(maps) * 2
    out = []
    for (a, b), where in sorted(near.items(), key=lambda kv: -len(kv[1])):
        out.append(finding(6, "P2", s["file"], None, f"{a} and {b} are nearly the same in {len(where)}/{total}: "
                           + "; ".join(where[:3]) + (" …" if len(where) > 3 else ""), s["name"], pair=[a, b], where=where))
    for (a, b), where in sorted(same.items(), key=lambda kv: -len(kv[1])):
        if len(where) * 2 >= total:
            out.append(finding(6, "P3", s["file"], None, f"{a} = {b} in {len(where)}/{total} theme-modes: an alias "
                               f"(var({a})) or one token?", s["name"], pair=[a, b], where=where))
    return out


# ---------- check 7 ----------
TEXT_FG = ("ink", "muted", "faint", "accent", "bad", "warn", "ok")
GROUNDS = ("bg", "surface", "sunk")


def contrast_pairs(names):
    """[(fg, bg, need, why)] for the token pairs found in one environment (the pairing logic in the module docstring)."""
    pairs = [(f"--{fg}", f"--{bg}", 4.5, "text on a ground") for fg in TEXT_FG for bg in GROUNDS]
    pairs += _named_pairs(names)
    pairs += [(fg, bg, 4.5, "Today text") for fg in ("--day-ink", "--day-muted") for bg in ("--day-page", "--day-band")]
    pairs += [("--day-past", "--day-page", 3.0, "Today past marks"), ("--day-sun", "--day-page", 3.0, "Today now-line")]
    pairs += [(fg, bg, 4.5, "Help text") for fg in ("--hp-ink", "--hp-soft", "--hp-teal", "--hp-amber", "--hp-green")
              for bg in ("--hp-ground", "--hp-paper")]
    pairs += [("--focus", "--bg", 3.0, "UI mark"), ("--focus", "--surface", 3.0, "UI mark"),
              ("--saffron", "--surface", 3.0, "the wordmark bar on the rail")]
    pairs += [("--ink", "--card", 4.5, "text on a card"), ("--muted", "--card", 4.5, "text on a card"),
              ("--accent", "--card", 4.5, "text on a card"), ("--warn", "--warnbg", 4.5, "status text on its fill")]
    seen, out = set(), []
    for p in pairs:
        if p[:2] not in seen and p[0] in names and p[1] in names:
            seen.add(p[:2])
            out.append(p)
    return out


def _named_pairs(names):
    pairs = []
    for n in names:
        if n.endswith("-ink") and n[:-4] in names and n not in ("--day-ink", "--hp-ink"):
            pairs.append((n, n[:-4], 4.5, "ink on its fill"))
        if n.endswith("-soft") and n[:-5] in names and not n.startswith("--hp-soft"):
            pairs.append((n[:-5], n, 4.5, "status text on its soft fill"))
    return pairs


def check_contrast(s, maps):
    """Check 7 for one surface: (findings, matrix rows of {palette, mode, pairs, fails})."""
    out, rows = [], []
    for p, envs in maps.items():
        for e in ("light", "dark"):
            toks = envs[e]
            fails = 0
            pairs = contrast_pairs(set(toks))
            for fg, bg, need, why in pairs:
                cf, cb = token_colour(fg, toks), token_colour(bg, toks)
                if not cf or not cb or cb[3] < 0.999:
                    continue
                ratio = contrast(cf, cb)
                if ratio < need:
                    fails += 1
                    loc = toks[fg]
                    out.append(finding(7, "P1", loc["file"], loc["line"], f"{pname(p)} {e}: {fg} {hexof(cf)} on {bg} "
                                       f"{hexof(cb)} is {ratio:.2f}:1, needs {need}:1 ({why})", s["name"], ratio=round(ratio, 2)))
            rows.append({"palette": pname(p), "mode": e, "pairs": len(pairs), "fails": fails})
    return out, rows


# ---------- check 8 ----------
ROLES = ("bg", "surface", "ink", "muted", "line", "accent", "bad", "warn", "ok")
ROLE_TOKENS = {"bg": ("--bg", "--hp-ground"), "surface": ("--surface", "--card", "--hp-paper"),
               "ink": ("--ink", "--hp-ink"), "muted": ("--muted", "--hp-soft"), "line": ("--line", "--hp-hair"),
               "accent": ("--accent", "--hp-teal"), "bad": ("--bad",), "warn": ("--warn", "--hp-amber"),
               "ok": ("--ok", "--hp-green")}
FONT_ROLES = {"body": ("--font", "--hp-body"), "display": ("--display", "--hp-display"), "mono": ("--mono", "--hp-mono")}


def first_family(v):
    """The first family of a font-family list or `font` shorthand, unquoted."""
    if not v:
        return None
    v = re.sub(r"^(?:(?:italic|normal|bold|[1-9]00)\s+)*\d*\.?\d+(?:px|r?em|pt|%)(?:\s*/\s*\S+)?\s+", "", v.strip())
    fam = split_top(v, ",")[0].strip().strip("\"'")
    return fam or None


def _roles_from_tokens(toks, body_font=None):
    out = {}
    for role, names in ROLE_TOKENS.items():
        for n in names:
            c = token_colour(n, toks)
            if c:
                out[role] = c
                break
    fonts = {}
    for role, names in FONT_ROLES.items():
        for n in names:
            if n in toks:
                fonts[role] = first_family(resolve(toks[n]["value"], toks))
                break
    if body_font and "body" not in fonts:
        fonts["body"] = body_font
    return out, fonts


def _body_font(s):
    for r in s["rules"]:
        if re.fullmatch(r"body|html|body,\s*html", r["sel"].strip()) and not r["media"]:
            for d in r["decls"]:
                if d["prop"] in ("font", "font-family"):
                    return first_family(d["value"])
    return None


def web_roles(s, maps, palette):
    """{mode: (colours by role, fonts by role)} for a web surface in one palette."""
    if palette not in maps:
        return {}
    bf = _body_font(s)
    return {e: _roles_from_tokens(maps[palette][e], bf) for e in ("light", "dark")}


def _docx_flags():
    path = SCRIPTS / "docx_tools.py"
    if not path.exists():
        return {}, None
    text = path.read_text(encoding="utf-8")
    flags = dict(re.findall(r'"([A-Z ]+)":\s*"([0-9A-F]{6})"', text))
    line = next((i for i, ln in enumerate(text.split("\n"), 1) if ln.startswith("FLAGS")), None)
    roles = {}
    for role, key in (("bad", "BLOCKED"), ("warn", "PRIORITY"), ("ok", "ON TRACK"), ("accent", "ACTION")):
        if key in flags:
            roles[role] = _hex_rgba(flags[key])
    return roles, line


def word_facts():
    """Colours, fonts and sizes of each Word template, and the status label colours docx_tools.py writes."""
    out = {"templates": {}}
    for f in sorted(TPL.glob("*.docx")):
        with zipfile.ZipFile(f) as z:
            names = set(z.namelist())
            theme = z.read("word/theme/theme1.xml").decode("utf-8", "replace") if "word/theme/theme1.xml" in names else ""
            styles = z.read("word/styles.xml").decode("utf-8", "replace") if "word/styles.xml" in names else ""
            doc = z.read("word/document.xml").decode("utf-8", "replace") if "word/document.xml" in names else ""
        defaults = re.search(r"<w:docDefaults>.*?</w:docDefaults>", styles, re.S)
        dflt = defaults.group(0) if defaults else ""
        heads = {m.group(1): re.findall(r'w:color w:val="([0-9A-Fa-f]{6})"', m.group(0))
                 for m in re.finditer(r'<w:style [^>]*w:styleId="([^"]+)".*?</w:style>', styles, re.S)}
        out["templates"][f.name] = {
            "theme_colours": dict(re.findall(r"<a:(dk1|lt1|dk2|lt2|accent\d|hlink)>.*?(?:srgbClr val|lastClr)=\"([0-9A-F]{6})\"",
                                             theme, re.S)),
            "theme_fonts": dict(re.findall(r'<a:(major|minor)Font><a:latin typeface="([^"]*)"', theme)),
            "default_font": (re.findall(r'w:ascii="([^"]+)"', dflt) or [None])[0],
            "default_colour": (re.findall(r'w:color w:val="([0-9A-Fa-f]{6})"', dflt) or [None])[0],
            "default_size_pt": (int(re.findall(r'<w:sz w:val="(\d+)"', dflt)[0]) / 2) if re.findall(r'<w:sz w:val="(\d+)"', dflt)
            else None,
            "style_colours": {k: v for k, v in heads.items() if v},
            "styles_used": sorted(set(re.findall(r'<w:pStyle w:val="([^"]+)"', doc))),
            "doc_colours": dict(Counter(re.findall(r'w:color w:val="([0-9A-Fa-f]{6})"', doc))),
            "doc_fills": dict(Counter(re.findall(r'w:fill="([0-9A-Fa-f]{6})"', doc))),
            "doc_sizes_pt": sorted({int(x) / 2 for x in re.findall(r'<w:sz w:val="(\d+)"', doc)})}
    out["flags"], out["flags_line"] = _docx_flags()
    return out


def email_roles(dash):
    """The email drafts' fixed colours (DE_COLOURS) and font (DE_FONT) from drafts.js, as roles."""
    path = DASH / "src" / "drafts.js"
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    m = re.search(r"DE_COLOURS\s*=\s*\{(.*?)\}", text)
    cols = dict(re.findall(r'(\w+):"(#[0-9A-Fa-f]{6})"', m.group(1))) if m else {}
    roles = {r: _hex_rgba(cols[k]) for r, k in (("bad", "red"), ("warn", "amber"), ("ink", "ink"), ("muted", "muted"),
                                                ("line", "rule")) if k in cols}
    f = re.search(r'DE_FONT\s*=\s*"font-family:([^;]+);', text)
    return {"light": (roles, {"body": first_family(f.group(1)) if f else None})}


def surface_roles(surfaces, maps, word):
    """{surface label: {mode: (colours, fonts), "file": path}} for every surface, the dashboard's default palette first."""
    dash = surfaces["dashboard"]
    out = {f"dashboard ({dash['default']})": dict(web_roles(dash, maps["dashboard"], dash["default"]), file=dash["file"])}
    if "Brightwater" in maps["dashboard"]:
        out["dashboard (Brightwater)"] = dict(web_roles(dash, maps["dashboard"], "Brightwater"), file=dash["file"])
    for name, s in surfaces.items():
        if name != "dashboard":
            out[name] = dict(web_roles(s, maps[name], s["default"]), file=s["file"])
    em = email_roles(dash)
    if em:
        out["email drafts"] = dict(em, file="system/templates/dashboard/src/drafts.js")
    if word["templates"]:
        t = next(iter(word["templates"].values()))
        cols = dict(word["flags"])
        if t["default_colour"]:
            cols["ink"] = _hex_rgba(t["default_colour"])
        fill = max(t["doc_fills"], key=t["doc_fills"].get) if t["doc_fills"] else None
        if fill:
            cols["inverse"] = _hex_rgba(fill)
        out["Word"] = {"light": (cols, {"body": t["default_font"], "display": t["theme_fonts"].get("major")}),
                       "file": "system/scripts/docx_tools.py"}
    return out


def _role_diffs(label, modes, mode, ref):
    cols, fonts = modes[mode]
    rcols, rfonts = ref
    out = []
    for role in ROLES:
        if role in cols and role in rcols:
            d = delta_e(cols[role], rcols[role])
            if d > JND:
                sev = "P2" if role in ("bad", "warn", "ok", "accent") else "P3"
                out.append(finding(8, sev, modes["file"], None, f"{label} {mode} {role} {hexof(cols[role])} differs "
                                   f"from the dashboard's {hexof(rcols[role])} (ΔE {d:.1f})", label, role=role))
    for role, fam in (fonts.items() if mode == "light" else ()):
        if fam and rfonts.get(role) and fam.lower() != rfonts[role].lower():
            out.append(finding(8, "P2", modes["file"], None, f"{label} {role} font is {fam}; the dashboard's is "
                               f"{rfonts[role]}", label, role=role))
    return out


# Surfaces kept in their own brand on purpose: shown in the table, never compared with the dashboard (their own checks stay)
OWN_BRAND = {"Word": "Word stays in the Brightwater brand (Alan, 14-10-2026)"}


def check_surfaces(surfaces, maps, word):
    """Check 8: each surface's role colours and fonts against the dashboard's default palette in the same mode."""
    roles = surface_roles(surfaces, maps, word)
    ref_label = next(iter(roles))
    ref = roles[ref_label]
    out = []
    for label, modes in roles.items():
        if label in (ref_label, "dashboard (Brightwater)") or label in OWN_BRAND:
            continue
        for mode in ("light", "dark"):
            if mode not in modes or mode not in ref:
                continue
            out += _role_diffs(label, modes, mode, ref[mode])
    out += _word_extras(word)
    return out, roles


def _word_extras(word):
    styles, used, aptos = defaultdict(set), defaultdict(set), []
    for name, t in word["templates"].items():
        for sid, cols in t["style_colours"].items():
            if sid.startswith("Heading") or sid == "Hyperlink":
                styles[(sid, ", ".join("#" + c for c in cols))].add(name)
                if sid in t["styles_used"]:
                    used[sid].add(name)
        if t["theme_fonts"].get("minor", "").startswith("Aptos"):
            aptos.append(name)
    out = []
    n = len(word["templates"])
    for (sid, cols), names in sorted(styles.items()):
        u = sorted(used.get(sid, ()))
        out.append(finding(8, "P2" if u else "P3", "system/templates/" + sorted(names)[0], None,
                           f"Word style {sid} keeps Word's default colour {cols} in {len(names)}/{n} templates"
                           + (f"; used in {', '.join(u)}" if u else " (not used in any template body; a report that adds "
                              "headings will show it)"), "Word", templates=sorted(names)))
    if aptos:
        t = word["templates"][aptos[0]]
        out.append(finding(8, "P3", "system/templates/" + aptos[0], None,
                           f"Word theme fonts are {t['theme_fonts'].get('major')}/{t['theme_fonts'].get('minor')} (the Office "
                           f"default) in {len(aptos)}/{n} templates while the body is {t['default_font']}; the Brightwater "
                           "palette's note says never Aptos", "Word", templates=aptos))
    return out


# ---------- running and reporting ----------
def run():
    """Every check over every surface: {findings, coverage, contrast, scales, roles, word, surfaces}."""
    surfaces = load_surfaces()
    maps = {n: env_maps(s) for n, s in surfaces.items()}
    findings, extra = [], {"coverage": {}, "contrast": {}, "scales": {}}
    for name, s in surfaces.items():
        defs, used = definitions(s), uses(s)
        findings += check_unused_undefined(s, defs, used)
        findings += check_themes(s, maps[name], defs, used)
        findings += check_hardcoded(s, maps[name])
        findings += check_duplicates(s, maps[name])
        f7, rows = check_contrast(s, maps[name])
        findings += f7
        extra["contrast"][name] = rows
        if name in ("dashboard", "prep-page"):
            usage = scale_usage(s)
            findings += check_scales(s, usage)
            extra["scales"][name] = {k: {"raw": dict(v["raw"].most_common()), "tokens": dict(v["tokens"].most_common())}
                                     for k, v in usage.items()}
        extra["coverage"][name] = coverage(s, maps[name])
    word = word_facts()
    f8, roles = check_surfaces(surfaces, maps, word)
    findings += f8
    findings.sort(key=lambda f: (f["check"], f["sev"], f["surface"], f["file"] or "", f["line"] or 0))
    extra["roles"] = {k: {m: ({r: hexof(c) for r, c in v[0].items()}, v[1]) for m, v in modes.items() if m != "file"}
                      for k, modes in roles.items()}
    extra["word"] = word
    extra["surfaces"] = {n: {"files": s["files"], "palettes": [pname(p) for p in s["palettes"]], "default": pname(s["default"]),
                             "rules": len(s["rules"]), "tokens_defined": len({d["name"] for d in definitions(s)})}
                         for n, s in surfaces.items()}
    return {"findings": findings, **extra}


def summary(findings):
    """{check: {P1, P2, P3}} counts."""
    out = {c: {s: 0 for s in SEVS} for c in CHECKS}
    for f in findings:
        out[f["check"]][f["sev"]] += 1
    return out


def _loc(f):
    if not f["file"]:
        return ""
    return f"`{f['file']}:{f['line']}`" if f["line"] else f"`{f['file']}`"


def _md_findings(fs, limit):
    lines = []
    for f in fs[:limit]:
        loc = _loc(f)
        lines.append(f"- **{f['sev']}** [{f['surface']}] {f['msg']}" + (f" — {loc}" if loc else ""))
    if len(fs) > limit:
        lines.append(f"- … and {len(fs) - limit} more (all are in `--json`)")
    return lines


def _md_scales(scales):
    lines = []
    for surf, data in scales.items():
        lines.append(f"\n**{surf}** — raw values (count) and tokens used\n")
        lines.append("| Scale | Raw uses | Distinct raw | Token uses | Raw values |")
        lines.append("|---|---:|---:|---:|---|")
        for k, v in data.items():
            raw = ", ".join(f"{x} ({n})" for x, n in v["raw"].items())
            if len(raw) > 600:
                raw = raw[:600].rsplit(",", 1)[0] + ", …"
            lines.append(f"| {k} | {sum(v['raw'].values())} | {len(v['raw'])} | {sum(v['tokens'].values())} | {raw or '—'} |")
    return lines


def _md_coverage(cov):
    lines = []
    for surf, rows in cov.items():
        if not rows:
            continue
        lines.append(f"\n**{surf}** — root tokens each palette sets itself, and how many it takes from the base\n")
        lines.append("| Palette | Own (light) | Own (dark) | From base | Effective light | Effective dark |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for r in rows:
            lines.append(f"| {r['palette']} | {r['light']} | {r['dark']} | {r['from_base']} | {r['total_light']} | {r['total_dark']} |")
    return lines


def _md_roles(roles):
    labels = list(roles)
    lines = ["\n| Role | " + " | ".join(labels) + " |", "|---|" + "---|" * len(labels)]
    for mode in ("light", "dark"):
        for role in ROLES + ("inverse",):
            cells = [roles[lb].get(mode, ({}, {}))[0].get(role, "") for lb in labels]
            if any(cells):
                lines.append(f"| {role} ({mode}) | " + " | ".join(cells) + " |")
        for role in FONT_ROLES:
            cells = [str(roles[lb].get(mode, ({}, {}))[1].get(role) or "") for lb in labels]
            if any(cells):
                lines.append(f"| font {role} ({mode}) | " + " | ".join(cells) + " |")
    return lines


def _md_extras(c, res):
    if c == 3:
        return _md_coverage(res["coverage"]) + [""]
    if c == 5:
        return _md_scales(res["scales"]) + [""]
    if c == 7:
        rows = [r for rs in res["contrast"].values() for r in rs if r["pairs"]]
        return [f"{len(rows)} palette-modes checked, {sum(r['pairs'] for r in rows)} pairs, "
                f"{sum(r['fails'] for r in rows)} below threshold.", ""]
    if c == 8:
        return ["Each surface's role colours and fonts (the first column is the reference):"] + _md_roles(res["roles"]) + [""]
    return []


def markdown(res, limit):
    """The report as Markdown: the summary table, then one section per check."""
    sm = summary(res["findings"])
    out = ["# creaite design-token audit", "",
           "Surfaces: " + "; ".join(f"**{n}** ({v['rules']} rules, {v['tokens_defined']} tokens, palettes: "
                                    f"{', '.join(v['palettes'])}; default {v['default']})" for n, v in res["surfaces"].items()),
           "", "| # | Check | P1 | P2 | P3 | Total |", "|---:|---|---:|---:|---:|---:|"]
    for c, name in CHECKS.items():
        out.append(f"| {c} | {name} | {sm[c]['P1']} | {sm[c]['P2']} | {sm[c]['P3']} | {sum(sm[c].values())} |")
    tot = {s: sum(sm[c][s] for c in CHECKS) for s in SEVS}
    out.append(f"| | **All** | **{tot['P1']}** | **{tot['P2']}** | **{tot['P3']}** | **{sum(tot.values())}** |")
    for c, name in CHECKS.items():
        fs = sorted([f for f in res["findings"] if f["check"] == c], key=lambda f: SEVS.index(f["sev"]))
        out += ["", f"## {c}. {name} ({len(fs)})", ""] + _md_extras(c, res)
        out += _md_findings(fs, limit) or ["None."]
    return "\n".join(out) + "\n"


def main(argv=None):
    """Prints the audit; exits 1 only with --strict and a P1."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--strict", action="store_true", help="exit 1 when any P1 is found")
    ap.add_argument("--limit", type=int, default=40, help="findings listed per check in Markdown (default 40)")
    a = ap.parse_args(argv)
    res = run()
    if a.json:
        res["summary"] = {CHECKS[c]: v for c, v in summary(res["findings"]).items()}
        print(json.dumps(res, indent=1, default=lambda o: sorted(o) if isinstance(o, set) else str(o)))
    else:
        sys.stdout.write(markdown(res, a.limit))
    return 1 if a.strict and any(f["sev"] == "P1" for f in res["findings"]) else 0


if __name__ == "__main__":
    sys.exit(main())
