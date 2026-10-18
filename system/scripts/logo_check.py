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
