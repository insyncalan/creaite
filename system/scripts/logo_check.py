"""p240-leakfix (LOGO 1 to 3): look inside a logo before it is saved. A library: no command line, no file read or written.

`inspect(raw)` returns (kind, width, height) for a PNG, JPEG or SVG that is what it says it is, or raises LogoRefused with one plain
sentence (never a path or a byte of the file):
  - PNG: the signature, a valid first IHDR chunk, width and height above 0 and no more than MAX_SIDE, every chunk's length and CRC
    intact up to IEND, and nothing after IEND.
  - JPEG: starts with SOI, a frame header giving the size (above 0, at most MAX_SIDE), and ends with EOI with nothing after it.
  - SVG: well-formed XML (no DOCTYPE or entity), an svg root, no script, event handler, foreignObject, frame, object, embed or
    animation element, no web address (an `href` may point only at a part of the same file, `#name`), no `url()` or `@import` to
    anywhere but the same file or a data image, and no declared width or height above MAX_SIDE.
Pixel size is capped so a header that declares a huge picture can't stall a browser or Word."""
import html
import re
import struct
import sys
import zlib
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402,F401  (every script takes its locations from paths.py; this one reads and writes no file)

MAX_SIDE = 4000
PNG_SIG = b"\x89PNG\r\n\x1a\n"
BAD_TAGS = {"script", "foreignobject", "iframe", "frame", "object", "embed", "animate", "animatemotion", "animatetransform", "set",
            "audio", "video", "canvas", "handler", "listener"}
URL_USE = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.I | re.S)


class LogoRefused(ValueError):
    """The logo isn't saved; the message is a plain sentence for Alan."""


def _size_ok(w, h):
    """Raises unless both sides are above 0 and no more than MAX_SIDE."""
    if not (0 < w <= MAX_SIDE and 0 < h <= MAX_SIDE):
        raise LogoRefused(f"That picture is {w} by {h} pixels. A logo must be between 1 and {MAX_SIDE} pixels each way. "
                          "Nothing was saved.")


def png_size(raw):
    """(width, height) of a sound PNG, else raises LogoRefused."""
    bad = LogoRefused("That PNG is damaged or has extra data after it. Nothing was saved.")
    if raw[:8] != PNG_SIG:
        raise bad
    pos, size, first = 8, None, True
    while pos + 12 <= len(raw):
        n = struct.unpack(">I", raw[pos:pos + 4])[0]
        kind, end = raw[pos + 4:pos + 8], pos + 12 + n
        if end > len(raw):
            raise bad
        body = raw[pos + 8:pos + 8 + n]
        if struct.unpack(">I", raw[pos + 8 + n:end])[0] != zlib.crc32(kind + body) & 0xFFFFFFFF:
            raise bad
        if first:
            if kind != b"IHDR" or n != 13:
                raise bad
            size, first = struct.unpack(">II", body[:8]), False
        if kind == b"IEND":
            if end != len(raw):
                raise bad
            _size_ok(*size)
            return size
        pos = end
    raise bad


def jpeg_size(raw):
    """(width, height) of a sound JPEG, else raises LogoRefused."""
    bad = LogoRefused("That JPEG is damaged or has extra data after it. Nothing was saved.")
    if raw[:2] != b"\xff\xd8" or raw[-2:] != b"\xff\xd9":
        raise bad
    pos = 2
    while pos + 4 <= len(raw):
        if raw[pos] != 0xFF:
            raise bad
        marker = raw[pos + 1]
        if marker == 0xFF:
            pos += 1
            continue
        n = struct.unpack(">H", raw[pos + 2:pos + 4])[0]
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            if n < 8 or pos + 9 > len(raw):
                raise bad
            h, w = struct.unpack(">HH", raw[pos + 5:pos + 9])
            _size_ok(w, h)
            return w, h
        if marker == 0xDA:
            break
        pos += 2 + n
    raise bad


def _local(name):
    """An XML name without its namespace, lower case."""
    return name.rsplit("}", 1)[-1].lower()


def _css_ok(text):
    """Whether style text points nowhere but into the file or a data image."""
    if re.search(r"@import|javascript:|expression\s*\(|-moz-binding", text, re.I):
        return False
    return all(m.group(2).strip().startswith("#") or m.group(2).strip().lower().startswith("data:image/")
               for m in URL_USE.finditer(text))


def _attr_ok(name, value):
    """Whether one SVG attribute is plain: no handler, no address outside the file, no script."""
    n, v = _local(name), str(value)
    if n.startswith("on") or n in ("src", "action", "formaction", "srcdoc", "ping"):
        return False
    if n == "href":
        return v.strip().startswith("#")
    if n == "style" and not _css_ok(v):
        return False
    return not re.search(r"javascript:|<script", v, re.I)


def _element_ok(el):
    """Whether one SVG element and its attributes are plain (a comment or processing instruction node is not)."""
    if not isinstance(el.tag, str) or _local(el.tag) in BAD_TAGS:
        return False
    if _local(el.tag) == "style" and not _css_ok(el.text or ""):
        return False
    return all(_attr_ok(k, v) for k, v in el.attrib.items())


def svg_size(raw):
    """(width, height) as declared (0, 0 when it declares none) of a clean SVG, else raises LogoRefused."""
    bad = LogoRefused("That SVG can't be used: it must be a plain picture with no script, link or embedded page. Nothing was saved.")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise bad from None
    if re.search(r"<!(?!--)|<\?(?!xml\s)|&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-f]+);)", text, re.I):
        raise bad                                   # a DOCTYPE, entity declaration, processing instruction or unknown entity
    try:
        root = ET.fromstring(text)
    except (ET.ParseError, ValueError):
        raise bad from None
    if _local(root.tag) != "svg" or not all(_element_ok(el) for el in root.iter()):
        raise bad
    dims = []
    for key in ("width", "height"):
        m = re.fullmatch(r"\s*([\d.]+)\s*(px)?\s*", root.get(key) or "")
        dims.append(float(m.group(1)) if m else 0.0)
    if any(d > MAX_SIDE for d in dims):
        raise LogoRefused(f"That SVG declares a size over {MAX_SIDE} pixels. Nothing was saved.")
    return int(dims[0]), int(dims[1])


# ── 2.5.1 M2: an SVG logo rebuilt for a client file ──────────────────────────
SVG_NS = "http://www.w3.org/2000/svg"
DRAWN_TAGS = {"svg", "g", "a", "defs", "path", "rect", "circle", "ellipse", "line", "polyline", "polygon", "lineargradient",
              "radialgradient", "stop", "clippath", "mask", "style", "text", "tspan"}
PAINT = {"fill", "fill-opacity", "fill-rule", "stroke", "stroke-width", "stroke-opacity", "stroke-linecap", "stroke-linejoin",
         "stroke-miterlimit", "stroke-dasharray", "stroke-dashoffset", "opacity", "stop-color", "stop-opacity", "clip-path",
         "clip-rule", "mask", "font-family", "font-size", "font-weight", "font-style", "font-stretch", "text-anchor",
         "letter-spacing", "word-spacing", "dominant-baseline", "alignment-baseline", "baseline-shift", "visibility", "display",
         "color", "paint-order", "vector-effect", "shape-rendering", "text-rendering", "mix-blend-mode", "isolation",
         "transform", "transform-origin"}
SHAPE_ATTRS = PAINT | {"width", "height", "viewbox", "preserveaspectratio", "x", "y", "x1", "y1", "x2", "y2", "cx", "cy", "r", "rx",
                       "ry", "fx", "fy", "fr", "d", "points", "offset", "gradientunits", "gradienttransform", "spreadmethod",
                       "clippathunits", "maskunits", "maskcontentunits", "dx", "dy", "rotate", "textlength", "lengthadjust",
                       "id", "class", "style"}
NOT_DRAWN_INSIDE = {"defs", "clippath", "mask", "lineargradient", "radialgradient"}
PLAIN_VALUE = re.compile(r"[\w\s#.,%()+\-:;'\"/]*\Z")
FONT_VALUE = re.compile(r"[\w\s,'\"-]{0,100}\Z")
URL_REF = re.compile(r"url\(\s*(['\"]?)#([\w.:-]+)\1\s*\)", re.I)
PATH_VALUE = re.compile(r"[MmLlHhVvCcSsQqTtAaZz\d\s.,+\-]*\Z")
POINTS_VALUE = re.compile(r"[\d\s.,+\-]*\Z")
NUMBER = re.compile(r"\s*(-?[\d.]+(?:e-?\d+)?)", re.I)


class _Names:
    """Each id and class of the picture given a plain new name (i1, c1, …), so no word of the old ones reaches the client."""

    def __init__(self):
        self.ids, self.classes = {}, {}

    def id(self, old):
        """The new name of an id."""
        return self.ids.setdefault(old, f"i{len(self.ids) + 1}")

    def cls(self, old):
        """The new name of a class."""
        return self.classes.setdefault(old, f"c{len(self.classes) + 1}")


COLOURS = ("aliceblue antiquewhite aqua aquamarine azure beige bisque black blanchedalmond blue blueviolet brown burlywood cadetblue "
           "chartreuse chocolate coral cornflowerblue cornsilk crimson cyan darkblue darkcyan darkgoldenrod darkgray darkgreen darkgrey "
           "darkkhaki darkmagenta darkolivegreen darkorange darkorchid darkred darksalmon darkseagreen darkslateblue darkslategray "
           "darkslategrey darkturquoise darkviolet deeppink deepskyblue dimgray dimgrey dodgerblue firebrick floralwhite forestgreen "
           "fuchsia gainsboro ghostwhite gold goldenrod gray green greenyellow grey honeydew hotpink indianred indigo ivory khaki "
           "lavender lavenderblush lawngreen lemonchiffon lightblue lightcoral lightcyan lightgoldenrodyellow lightgray lightgreen "
           "lightgrey lightpink lightsalmon lightseagreen lightskyblue lightslategray lightslategrey lightsteelblue lightyellow lime "
           "limegreen linen magenta maroon mediumaquamarine mediumblue mediumorchid mediumpurple mediumseagreen mediumslateblue "
           "mediumspringgreen mediumturquoise mediumvioletred midnightblue mintcream mistyrose moccasin navajowhite navy oldlace olive "
           "olivedrab orange orangered orchid palegoldenrod palegreen paleturquoise palevioletred papayawhip peachpuff peru pink plum "
           "powderblue purple rebeccapurple red rosybrown royalblue saddlebrown salmon sandybrown seagreen seashell sienna silver "
           "skyblue slateblue slategray slategrey snow springgreen steelblue tan teal thistle tomato turquoise violet wheat white "
           "whitesmoke yellow yellowgreen")
KEYWORDS = ("none currentcolor inherit initial unset transparent butt round square miter bevel arcs clip nonzero evenodd normal bold "
            "bolder lighter italic oblique start middle end auto hidden visible collapse inline block url rgb rgba hsl hsla matrix "
            "translate translatex translatey scale scalex scaley rotate skewx skewy userspaceonuse objectboundingbox pad reflect "
            "repeat xmidymid xminymin xmaxymax xmidymin xmidymax xminymid xmaxymid xminymax xmaxymin meet slice spacing "
            "spacingandglyphs alphabetic central mathematical hanging ideographic baseline sub super stroke fill markers "
            "non-scaling-stroke crispedges geometricprecision optimizespeed optimizelegibility multiply screen overlay darken lighten "
            "isolate px em ex pt pc cm mm in rem deg rad grad turn ch vw vh condensed expanded semi-condensed semi-expanded")
FONTS = ("serif sans-serif monospace cursive fantasy system-ui arial helvetica neue verdana tahoma trebuchet ms georgia times new "
         "roman courier garamond palatino segoe ui roboto open sans lato montserrat inter source pro calibri cambria gill futura "
         "avenir next frutiger myriad univers din condensed light medium regular semibold bold black heavy thin")
PLAIN_WORDS = set(COLOURS.split()) | set(KEYWORDS.split())
FONT_WORDS = set(FONTS.split()) | PLAIN_WORDS


def _words_ok(prop, v):
    """Whether a value holds no word: a path's or a point list's numbers and one command letter at a time; anything else only
    colours, keywords, units and numbers (font names for font-family)."""
    if prop in ("d", "points"):
        bare = re.sub(r"(?<=[\d.])[eE](?=[-+]?\d)", "", v)          # an exponent is not a command
        return bool((PATH_VALUE if prop == "d" else POINTS_VALUE).match(bare)) and not re.search(r"[A-Ya-y][A-Za-z]", bare)
    if prop == "font-family" and not FONT_VALUE.match(v):
        return False
    words = FONT_WORDS if prop == "font-family" else PLAIN_WORDS
    rest = re.sub(r"#[0-9a-fA-F]{3,8}\b|\d*\.?\d+(?:e[-+]?\d+)?", " ", URL_REF.sub("url()", v))
    return all(w.lower() in words for w in re.findall(r"[A-Za-z]+(?:-[A-Za-z]+)*", rest))


def _value(prop, value, names):
    """A presentation value made safe, or None: plain characters only, every word a colour, keyword or unit (a font name for
    font-family), `url(#id)` pointing into the file (renamed), nothing else."""
    v = str(value).strip()
    if len(v) > (200_000 if prop in ("d", "points") else 2000) or not PLAIN_VALUE.match(v):
        return None
    if prop in ("id", "class") or not _words_ok(prop, v):
        return None
    if "url" in v.lower():
        if re.sub(URL_REF, "", v).lower().count("url"):
            return None
        v = URL_REF.sub(lambda m: f"url(#{names.id(m.group(2))})", v)
    return v


def _declarations(css, names):
    """Style declarations kept from the presentation list, each value made safe, as `prop:value;…`."""
    out = []
    for decl in css.split(";"):
        prop, sep, val = decl.partition(":")
        prop = prop.strip().lower()
        if sep and prop in PAINT:
            v = _value(prop, val, names)
            if v is not None and v:
                out.append(f"{prop}:{v}")
    return ";".join(out)


def _rules(css, names):
    """A <style> element's rules rebuilt: comments and at-rules gone, only element, class and id selectors (renamed), each
    declaration from the presentation list."""
    css = re.sub(r"/\*.*?(\*/|\Z)", "", css, flags=re.S)
    out = []
    for sel, body in re.findall(r"([^{}@;]+)\{([^{}]*)\}", css):
        parts = [_selector(one, names) for one in sel.split(",")]
        decls = _declarations(body, names)
        if parts and None not in parts and decls:
            out.append(f"{','.join(parts)}{{{decls}}}")
    return "".join(out)


def _selector(one, names):
    """One selector of drawn element names, classes and ids (renamed) and combinators, or None for anything else."""
    toks = re.findall(r"([.#]?)([A-Za-z_][\w-]*)|([\s>*+~]+)|(.)", one.strip())
    if not toks or any(t[3] or (not t[0] and t[1] and t[1].lower() not in DRAWN_TAGS) for t in toks):
        return None
    rename = {".": lambda n: "." + names.cls(n), "#": lambda n: "#" + names.id(n), "": lambda n: n}
    return "".join(t[2] or rename[t[0]](t[1]) for t in toks)


def _props(el):
    """{presentation property: value} of one element, its attributes then its style (which wins), lower case."""
    out = {_local(k): str(v).strip().lower() for k, v in el.attrib.items() if "}" not in k}
    for decl in (el.get("style") or "").split(";"):
        prop, sep, val = decl.partition(":")
        if sep:
            out[prop.strip().lower()] = val.strip().lower()
    return out


def _num(v):
    """The leading number of a value, or None."""
    m = NUMBER.match(v or "")
    try:
        return float(m.group(1)) if m else None
    except ValueError:
        return None


def _paints(v):
    """Whether a fill or stroke value draws anything."""
    return v not in ("none", "transparent") and not re.fullmatch(r"(rgba|hsla)\(.*,\s*0(\.0*)?\s*\)", v or "")


def _state(parent, el, scale):
    """The drawing state an element passes to its children: (hidden, fill drawn, stroke drawn, font size)."""
    hidden, fill, stroke, size = parent
    p = _props(el)
    if p.get("display") == "none" or p.get("visibility") in ("hidden", "collapse") or _num(p.get("opacity")) == 0:
        hidden = True
    if "fill" in p:
        fill = _paints(p["fill"])
    if _num(p.get("fill-opacity")) == 0:
        fill = False
    if "stroke" in p:
        stroke = _paints(p["stroke"])
    if _num(p.get("stroke-opacity")) == 0 or _num(p.get("stroke-width")) == 0:
        stroke = False
    if "font-size" in p and _num(p["font-size"]) is not None:
        size = _num(p["font-size"])
    if size is not None and size < scale / 1000:
        hidden = True
    return hidden, fill, stroke, size


def _text_drawn(el, state, box):
    """Whether a text or tspan with this state is drawn where it can be seen."""
    hidden, fill, stroke, _size = state
    if hidden or not (fill or stroke):
        return False
    x0, y0, w, h = box
    for key, lo, span in (("x", x0, w), ("y", y0, h)):
        n = _num(el.get(key))
        if n is not None and not (lo - 10 * span <= n <= lo + 11 * span):
            return False
    return True


def _attr(n, v, names):
    """One kept attribute's value (ids and classes renamed, style declarations filtered), or None when it is left out."""
    if n == "id":
        return names.id(v) if re.fullmatch(r"[\w.:-]{1,80}", v) else None
    if n == "class":
        return " ".join(names.cls(c) for c in v.split() if re.fullmatch(r"[A-Za-z_][\w-]{0,80}", c)) or None
    if n == "style":
        return _declarations(v, names) or None
    return _value(n, v, names)


def _attrs(el, names):
    """An element's attributes from the allow-list (none in another namespace), written out."""
    out = []
    for k, v in el.attrib.items():
        val = None if "}" in k or _local(k) not in SHAPE_ATTRS else _attr(_local(k), v, names)
        if val is not None:
            out.append(f' {k}="{html.escape(val, quote=True)}"')
    return "".join(out)


def _own_text(el, tag, names):
    """What an element holds as its own text in the rebuilt picture: a style's rules, a text's or tspan's words, nothing else."""
    if tag == "style":
        return html.escape(_rules(el.text or "", names), quote=False)
    return html.escape(el.text or "", quote=False) if tag in ("text", "tspan") else ""


def _rebuild(el, names, state, box, scale, inside, out):
    """Write `el` (and what is under it) from the allow-lists into `out`."""
    tag = _local(el.tag)
    ns = el.tag[1:].split("}", 1)[0] if el.tag.startswith("{") else SVG_NS
    if ns != SVG_NS or tag not in DRAWN_TAGS:
        return
    state = _state(state, el, scale)
    tail = html.escape(el.tail or "", quote=False) if tag == "tspan" else ""     # a tspan's tail is its text's words
    if tag in ("text", "tspan") and (inside or not _text_drawn(el, state, box)):
        out.append(tail)
        return
    name = el.tag.rsplit("}", 1)[-1] if tag != "a" else "g"
    out.append(f"<{name}{_attrs(el, names)}>{_own_text(el, tag, names)}")
    for child in el:
        _rebuild(child, names, state, box, scale, inside or tag in NOT_DRAWN_INSIDE, out)
    out.append(f"</{name}>{tail}")


def clean_svg(raw):
    """2.5.1 M2: the SVG logo `raw` (bytes) rebuilt for a client file from an allow-list of drawn shapes, or None when it can't be
    read. Comments, processing instructions, title, desc, metadata, editor elements and attributes (any namespace but SVG's), links,
    scripts, pictures, text that isn't drawn (hidden, transparent, of no size, far off the picture, or inside defs, a clip or a mask)
    and every word in an id or class name are left out; shapes, gradients, styles and drawn text keep their values, so a logo of
    plain shapes draws the same."""
    try:
        text = raw.decode("utf-8")
    except (UnicodeDecodeError, AttributeError):
        return None
    if len(text) > 1_000_000 or re.search(r"<!(?!--)|<\?(?!xml\s)|&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-f]+);)", text, re.I):
        return None
    try:
        root = ET.fromstring(text)                  # comments and processing instructions are not kept by the parser
    except (ET.ParseError, ValueError):
        return None
    if _local(root.tag) != "svg":
        return None
    vb = [_num(x) for x in re.split(r"[\s,]+", (root.get("viewBox") or "").strip()) if x]
    if len(vb) == 4 and None not in vb and vb[2] > 0 and vb[3] > 0:
        box = tuple(vb)
    else:
        box = (0.0, 0.0, _num(root.get("width")) or 300.0, _num(root.get("height")) or 150.0)
    out = []
    _rebuild(root, _Names(), (False, True, False, None), box, max(box[2], box[3]), False, out)
    if not out:
        return None
    out[0] = out[0].replace("<svg", f'<svg xmlns="{SVG_NS}"', 1)
    return "".join(out).encode("utf-8")


def kind_of(raw):
    """"png", "jpg", "svg" or None from the file's own first bytes."""
    if raw[:8] == PNG_SIG:
        return "png"
    if raw[:3] == b"\xff\xd8\xff":
        return "jpg"
    if b"<svg" in raw[:2000].lower():
        return "svg"
    return None


def inspect(raw):
    """(kind, width, height) of a sound logo, or raises LogoRefused."""
    kind = kind_of(raw or b"")
    if kind is None:
        raise LogoRefused("That isn't a PNG, JPEG or SVG picture. Nothing was saved.")
    w, h = {"png": png_size, "jpg": jpeg_size, "svg": svg_size}[kind](raw)
    return kind, w, h
