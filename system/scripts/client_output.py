"""v2.5.1 (#239, c): the check of a client report's OUTPUT, after it is made and before it is kept. A library: no command line.

creaite_doc.export calls check() on every client export it makes (HTML, Word, PDF), and report_doc.stage_client calls
filed_findings() on the file Approve files. It reads what the file actually holds:
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
ATTRS = re.compile(r"""\s[\w:-]+\s*=\s*("[^"]*"|'[^']*')""", re.I)          # every attribute's value (data-id, alt, title, href...)
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
    """An HTML page's text as a reader sees it (its markup without the tags, the style and the data block), and every attribute's
    value (alt, title, href, a section's data-id...), but a picture's data address."""
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

def unescaped(text):
    """The text with JSON's \\uXXXX escapes read as the characters they stand for (the gate reads %- and entity-encoding itself)."""
    return re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), text or "")


def _health_words(doc):
    """The words of a client report's shown health sections (the internal health reason may stand there, as the gate allows)."""
    import creaite_doc
    ids = {s.get("id") for s in doc.get("sections") or [] if isinstance(s, dict) and s.get("type") == "health"}
    if not ids:
        return ""               # no health section (a Word file's other parts, review.word_output_findings): nothing is allowed
    return "\n".join(t for i, _h, t in creaite_doc.sections_text(doc) if i in ids)


OTHER_TEXT = (("raid", "description"), ("decisions", "decision"), ("actions", "description"))


def other_project_findings(con, code, text):
    """Another project's hidden item wording, or a person who owns only another project's items a client report can't show (and
    none this project's report may name), in a client text (the gate's own checks read this project only: known gap B)."""
    import client_leak
    import edit_ai
    low = client_leak.squash(edit_ai.normal(text)).lower()
    found = []
    try:
        mine = {n.lower() for n in client_leak.people(con, code)[0] | client_leak.alans_names() if n}
        for (other,) in con.execute("SELECT code FROM projects WHERE code != ?", (code,)).fetchall():
            for table, col in OTHER_TEXT:
                for i, words in con.execute(f"SELECT id, {col} FROM {table} WHERE project = ? AND client_visible = 0", (other,)):
                    if len(words or "") >= 15 and client_leak.squash(edit_ai.normal(words)).lower() in low:
                        found.append(f"{i} (another project's, not client-visible) has its wording in the file")
            names = {n for n in client_leak.people(con, other)[1] if n.lower() not in mine}
            found += [f"{n} is named but owns only another project's items a client report can't show"
                      for n in sorted(client_leak.named(text, names, every=True))]
    except client_leak.RegisterUnreadable:
        found.append(client_leak.REGISTER_UNREAD)
    return found


LOOSE_SEP = r"[\W_]{0,8}"           # what may stand between an ID's characters: spaces, dashes, dots, any punctuation (up to eight)
DIGIT_SEP = r"[\W_]{0,6}"           # and between its digits (round 2, LOW 6: "/", "," and "·" too, up to six)
INVISIBLE = re.compile("[\u00ad\u180e\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff]")    # zero-width and format characters


def fold_words(text):
    """Text as P16 matches a wording: through the confusables skeleton, lower case, every run of anything that isn't a letter or
    a digit (spaces, hyphens, dots, underscores) one space, so "go-live", "go live" and "go.live" are one form."""
    import confusables
    import edit_ai
    return " ".join(re.split(r"[\W_]+", edit_ai.normal(confusables.skeleton(text)).lower())).strip()


def _number(groups):
    """The number an ID's digits are read as: spaced one by one ("0 0 5") they are one number; otherwise the first run only
    ("ABC-A-001 2026" is 001), so a list of numbers after a code ("ABC 1 2 3 4") is never read as a short ID."""
    return "".join(groups) if all(len(g) == 1 for g in groups) else groups[0]


DATED = re.compile(r"[1-9]\d?[/.:\-]\d")   # a short number (1 or 2 digits, no leading zero), then one fraction, date or time
#                                           # mark and a digit: "4/10", "12.5", "4-10", "4:10"
DATE_MARK = re.compile(r"[/.:\-]")


def _dated(digits, runs):
    """True when an ID's digits are a fraction, a date or a time ("ABC A 4/10 is the review day", "4/10/2026", "12.5"), not an ID:
    the first number is one or two digits with no leading zero, followed straight away by "/", ".", "-" or ":" and a digit, and
    the digits aren't three or more spaced one by one ("1/2/3"). A leading zero or a longer first run stays an ID ("0001/1",
    "001.5", "01/1", "0/0/4"), and so does "ABC A 4." (no digit follows its dot). #259 round 3 (and Cap's HIGH on it)."""
    spaced = all(len(g) == 1 for g in runs) and len(runs) >= 3
    return not spaced and bool(DATED.match(digits))


def _readings(digits, runs):
    """The numbers an ID's digits may be read as: _number's, and, when a fraction, date or time mark follows, every digit before
    the first mark ("0 0 1.5" is 001, as "001.5" is), so a mark can't turn a hidden ID into another number."""
    out = {_number(runs)}
    if DATE_MARK.search(digits):
        out.add(re.sub(r"\D", "", DATE_MARK.split(digits, 1)[0]))
    return {n.lstrip("0") or "0" for n in out if n}


def _loose_refs(con, text):
    """{item ID} of the IDs `text` holds in the forms edit_ai.loose_ids doesn't read (#259, P16): the code's letters spaced or
    dotted ("A B C - 0 0 5"), the digits spaced, more zeros ("ABC-0005") or fewer ("ABC-5"), any case. Only IDs the tracker holds."""
    import edit_ai
    import tracker
    t = edit_ai.normal(text).lower()
    out = set()
    for (code,) in con.execute("SELECT code FROM projects"):
        letters = LOOSE_SEP.join(re.escape(c) for c in str(code).lower())
        pat = rf"(?<![a-z0-9]){letters}{LOOSE_SEP}(?:([a-z]){LOOSE_SEP})?(\d(?:{DIGIT_SEP}\d)*)(?!{DIGIT_SEP}\d)"
        for m in re.finditer(pat, t):
            runs = re.split(r"[\W_]+", m.group(2))
            if _dated(m.group(2), runs):
                continue
            for num in _readings(m.group(2), runs):
                ref = f"{code}-{m.group(1).upper()}-{num.zfill(3)}" if m.group(1) else f"{code}-{num.zfill(3)}"
                if len(num) <= 3 and tracker.item_table(ref) and edit_ai.in_tracker(con, ref):
                    out.add(ref)
    return out


def loose_findings(con, code, text, skip=()):
    """v2.5.3 (#259, P16): what the gate's own reading misses in a client output's text: an item a client report can't show, by
    its ID however it is written (_loose_refs), or by its wording with hyphens, dots, underscores or spaces for one another
    (fold_words; the whole wording, 15 characters or more, as the gate matches wordings). `skip`: items a finding already names."""
    import client_leak
    found, skip = [], set(skip)
    blocking = client_leak.blocking_labels(con)
    for ref in sorted(_loose_refs(con, text) - skip):
        why = f"{ref} belongs to another project" if ref.split("-")[0] != code else client_leak.item_problem(con, ref, blocking)
        if why:
            found.append(f"{why}, but its ID appears")
    # round 2 (LOW 6): a zero-width or format character may stand for a space as well as inside a word, so both readings are matched
    words = f" {fold_words(text)} | {fold_words(INVISIBLE.sub(' ', text))} "
    for table, col in OTHER_TEXT:
        for i, w in con.execute(f"SELECT id, {col} FROM {table} WHERE client_visible = 0"):
            if i not in skip and len((w or "").strip()) >= 15 and f" {fold_words(w)} " in words:
                found.append(f"{i} isn't client-visible but its wording appears: “{w[:80]}”")
    return found


def text_findings(doc, text, con=None):
    """The client gate's checks on an output's text, read as it is and through the confusables skeleton."""
    import client_leak
    import confusables
    import drafts
    con = con or client_leak.connect()
    code = str(doc.get("project") or "")
    t = client_leak.joined(text, confusables.skeleton(text), unescaped(text))
    found = client_leak.text_findings(con, code, t)
    found += [f"it holds {w}" for w in drafts.internal_findings(con, code, client_leak.with_addresses(t), _health_words(doc))]
    if client_leak.marked(t) and "it holds an internal-only marker" not in found:
        found.append("it holds an internal-only marker")
    found += other_project_findings(con, code, t)
    found += loose_findings(con, code, t, {f.split(" ", 1)[0] for f in found})      # v2.5.3 (#259, P16)
    return found + client_leak.name_findings(con, code, t, client_leak.blocking_labels(con))


def check(doc, fmt, out, page=None, drawn=(), allowed=None):
    """[finding] for a client export made at `out` (fmt html, docx or pdf; `page`: the HTML a PDF was printed from; `drawn`: the
    hashes of the pictures this export drew itself). [] when what the file holds is safe. v2.5.1 step 2: `allowed`, the hashes of
    the snapshot's picture and logo tables (client_snapshot.tables), are then the only pictures of the report's own an output may
    hold (with the ones it drew and the template's), in place of what the folders hold now."""
    found = []
    allowed = set(allowed) | set(drawn) if allowed is not None else allowed_pictures(doc, drawn)
    if fmt == "docx":
        text = docx_text(out)
        found += picture_findings(docx_pictures(out), allowed | template_pictures(doc))
    else:
        markup = Path(out).read_text(encoding="utf-8", errors="replace") if fmt == "html" else (page or "")
        pics, bad = html_pictures(markup)
        found += bad + picture_findings(pics, allowed)
        text = html_text(markup) + ("\n" + pdf_text(out) if fmt == "pdf" else "")
    return list(dict.fromkeys(text_findings(doc, text) + found))


def _strings(x):
    """Every string value in decoded JSON (keys aside)."""
    if isinstance(x, str):
        return [x]
    if isinstance(x, dict):
        return [s for v in x.values() for s in _strings(v)]
    return [s for v in x for s in _strings(v)] if isinstance(x, list) else []


def filed_findings(doc, content):
    """[finding] for the file Approve is about to file for a client report (`content`: the page with its data block): the page's
    text and every string of its data block, and the page's pictures, checked as an export's are. [] when it is safe."""
    import creaite_doc
    m = creaite_doc.BLOCK.search(content or "")
    block = "\n".join(_strings(json.loads(m.group(1)))) if m else ""
    page = creaite_doc.BLOCK.sub("", content or "")
    pics, found = html_pictures(page)
    found += picture_findings(pics, allowed_pictures(doc))
    return list(dict.fromkeys(text_findings(doc, html_text(page) + "\n" + block) + found))
