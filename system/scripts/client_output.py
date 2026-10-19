"""v2.5.1 (#239, c): the check of a client report's OUTPUT, after it is made and before it is kept. A library: no command line.

creaite_doc.export calls check() on every client export it makes (HTML, Word, PDF). It reads what the file actually holds:
  - the text: a Word file's XML text (every paragraph's runs, in every part, and its properties), the HTML's markup text (and its
    attribute values: alt, title, href), a PDF's extracted text (tracker.pdf_text, the bundled pypdf) and the HTML page it was
    printed from;
  - the pictures: every picture embedded in the Word file or the HTML (a data address), which must be one of the allowed set:
    the logos the project ticks now (report_doc.client_logos), the report's own pictures (`_images/<name>` in its text), the firm's
    own pictures in the Word template, or a picture creaite drew itself for this export (the timeline, the health strip, an SVG
    logo drawn to a PNG).
Every text is read through the confusables skeleton (confusables.skeleton: NFKC, invisible characters gone, look-alike letters made
Latin) as well as as it is, and run through the client gate's own checks (client_leak.text_findings, the internal health reason
and markers, the names). Any finding: the caller deletes the file and keeps nothing.
"""
import base64
import hashlib
import html
import json
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402,F401

WORD_PARA = re.compile(r"<w:p(?: [^>]*)?>.*?</w:p>", re.S)
WORD_TEXT = re.compile(r"<w:t(?: [^>]*)?>([^<]*)</w:t>")
TAGS = re.compile(r"<[^>]+>")
ATTRS = re.compile(r"""\s(?:alt|title|href|aria-label|content|value)\s*=\s*("[^"]*"|'[^']*')""", re.I)
DATA_IMG = re.compile(r"""<img\b[^>]*?\ssrc\s*=\s*["']data:image/(?:png|jpeg);base64,([A-Za-z0-9+/=\s]+)["']""", re.I)
IMG_SRC = re.compile(r"""<(?:img|image|source|video|audio|iframe|object|embed)\b[^>]*?\s(?:src|href|data)\s*=""", re.I)
URL_IN_CSS = re.compile(r"url\s*\(|@import", re.I)
PICTURE_REF = re.compile(r"_images/[A-Za-z0-9][A-Za-z0-9._-]{0,120}\.(?:png|jpe?g)", re.I)


def pic_hash(data):
    """The hash a picture is compared by: of its bytes without metadata (as docx_tools fill embeds it); None for one that can't be
    read (never allowed)."""
    import docx_tools
    try:
        return hashlib.sha256(docx_tools.strip_image_metadata(data)).hexdigest()
    except docx_tools.PictureRefused:
        return None


def raw_hash(data):
    """The hash of the bytes as they are (an HTML page embeds a picture's own bytes)."""
    return hashlib.sha256(data).hexdigest()


# ── the text of an output ────────────────────────────────────────────────────

def docx_text(path):
    """A Word file's text: each paragraph's runs joined (a name split over two runs is one name again), one paragraph a line, from
    every XML part (the body, headers, footers, notes, comments), and the document properties' text."""
    lines = []
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if not name.endswith(".xml"):
                continue
            xml = z.read(name).decode("utf-8", "replace")
            if name.startswith("word/"):
                lines += [html.unescape("".join(WORD_TEXT.findall(p))) for p in WORD_PARA.findall(xml)]
            else:
                lines.append(html.unescape(TAGS.sub(" ", xml)))
    return "\n".join(lines)


def html_text(markup):
    """An HTML page's text as a reader sees it (its markup without the tags, the style and the data block), and the attribute values
    a browser shows or follows (alt, title, href)."""
    body = re.sub(r"<style\b.*?</style>", " ", markup or "", flags=re.S | re.I)
    body = re.sub(r"<script\b.*?</script>", " ", body, flags=re.S | re.I)
    attrs = [html.unescape(m.group(1)[1:-1]) for m in ATTRS.finditer(body) if not m.group(1)[1:].startswith("data:")]
    return html.unescape(TAGS.sub("\n", body)) + "\n" + "\n".join(attrs)


def pdf_text(path):
    """A PDF's text (the bundled pypdf, as search reads one); '' when it has none."""
    import tracker
    return tracker.pdf_text(Path(path))


# ── the pictures of an output ────────────────────────────────────────────────

def docx_pictures(path):
    """[(part name, bytes)] of every picture in a Word file."""
    with zipfile.ZipFile(path) as z:
        return [(n, z.read(n)) for n in z.namelist() if n.startswith("word/media/") or n.lower().endswith(
            (".png", ".jpg", ".jpeg", ".gif", ".svg", ".bmp", ".tif", ".tiff", ".emf", ".wmf"))]


def allowed_pictures(doc, drawn=()):
    """The hashes of the pictures a client export may hold (see the module's description): stripped and raw, so a Word file
    (stripped) and an HTML page (as the file is) are each compared the way they embed."""
    import creaite_doc
    import report_doc
    out = set(drawn)
    files = [paths.resolve(x["path"]) for x in report_doc.client_logos(str(doc.get("project") or ""), doc.get("layout"))]
    text = json.dumps(doc.get("sections") or [], ensure_ascii=False)
    files += [f for f in (creaite_doc.text_image(doc, ref) for ref in set(PICTURE_REF.findall(text))) if f is not None]
    for f in files:
        try:
            data = Path(f).read_bytes()
        except OSError:
            continue        # a picture that can't be read can't have been drawn either
        out |= {h for h in (pic_hash(data), raw_hash(data)) if h}
    return out


def template_pictures(doc):
    """The hashes of the firm's own pictures in the Word template the export is filled from (its wordmark)."""
    import creaite_doc
    tpl = paths.TEMPLATES / creaite_doc.TEMPLATES[doc.get("kind") or "client"]
    return {h for _n, data in docx_pictures(tpl) for h in (raw_hash(data), pic_hash(data)) if h}


def picture_findings(pictures, allowed):
    """A finding for each picture not in the allowed set."""
    bad = [n for n, data in pictures if not ({pic_hash(data), raw_hash(data)} & allowed)]
    return [f"a picture that isn't one of the report's own (its logos or pictures) is in the file ({len(bad)})"] if bad else []


def html_pictures(markup):
    """([("img n", bytes)] of the data-address pictures, [finding]) of an HTML page: a picture or resource from anywhere else (a
    file, a web address) is a finding."""
    pics, found = [], []
    for n, m in enumerate(DATA_IMG.finditer(markup or "")):
        try:
            pics.append((f"img {n + 1}", base64.b64decode(re.sub(r"\s", "", m.group(1)), validate=True)))
        except ValueError:
            found.append("a picture that can't be read is in the page")
    if len(IMG_SRC.findall(markup or "")) != len(pics) or URL_IN_CSS.search(re.sub(r"<style\b.*?</style>", "", markup or "",
                                                                                    flags=re.S | re.I)):
        found.append("the page loads a picture or a resource from outside itself")
    return pics, found


# ── the checks ───────────────────────────────────────────────────────────────

def _health_words(doc):
    """The words of a client report's shown health sections (the internal health reason may stand there, as the gate allows)."""
    import creaite_doc
    ids = {s.get("id") for s in doc.get("sections") or [] if isinstance(s, dict) and s.get("type") == "health"}
    return "\n".join(t for i, _h, t in creaite_doc.sections_text(doc) if i in ids)


def text_findings(doc, text, con=None):
    """The client gate's checks on an output's text, read as it is and through the confusables skeleton."""
    import client_leak
    import confusables
    import drafts
    con = con or client_leak.connect()
    code = str(doc.get("project") or "")
    t = client_leak.joined(text, confusables.skeleton(text))
    found = client_leak.text_findings(con, code, t)
    found += [f"it holds {w}" for w in drafts.internal_findings(con, code, client_leak.with_addresses(t), _health_words(doc))]
    if client_leak.marked(t) and "it holds an internal-only marker" not in found:
        found.append("it holds an internal-only marker")
    return found + client_leak.name_findings(con, code, t, client_leak.blocking_labels(con))


def check(doc, fmt, out, page=None, drawn=()):
    """[finding] for a client export made at `out` (fmt html, docx or pdf; `page`: the HTML a PDF was printed from; `drawn`: the
    hashes of the pictures this export drew itself). [] when what the file holds is safe."""
    found, allowed = [], allowed_pictures(doc, drawn)
    if fmt == "docx":
        text = docx_text(out)
        found += picture_findings(docx_pictures(out), allowed | template_pictures(doc))
    else:
        markup = Path(out).read_text(encoding="utf-8", errors="replace") if fmt == "html" else (page or "")
        pics, bad = html_pictures(markup)
        found += bad + picture_findings(pics, allowed)
        text = html_text(markup) + ("\n" + pdf_text(out) if fmt == "pdf" else "")
    return list(dict.fromkeys(text_findings(doc, text) + found))
