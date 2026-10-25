"""#375 E1 (2.6.9): the calendar invite body filter. Pure code, no I/O, standard library only.

An invite body is "join boilerplate" plus a few lines Alan's colleague wrote. The old filter (invite_clean) tried to recognise
a secret's label; this one recognises the boilerplate by LANGUAGE-FREE anchors and drops the whole block that holds one.
Lines are only ever dropped: the output is the input lines, in order, byte for byte (P1, subset), and filtering the output
again changes nothing (P2, idempotent). Dropping is decided on a "skeleton" of each line (NFKC, invisible characters removed,
look-alike letters mapped, lower case, spaces collapsed); the skeleton is never output.

Public API
  keep_indices(lines, *, second_layer=True) -> list[int]   ascending indices of the kept input lines
  keep_lines(lines, *, second_layer=True)   -> list[str]   [lines[i] for i in keep_indices(lines)]
  filter_text(text, *, second_layer=True)   -> str         cut to BODY_MAX, split on "\\n", keep_lines, join, then the CAP
  drop_labelled_values(lines)               -> list[int]   the second layer alone (S1b); returns the KEPT indices
  CAP = 1500, BODY_MAX = 20000, VERSION = 1

Layers, in order (each decides a line from the line itself, its block or its region only, so decisions are local):
  1. Anchor layer. A strong anchor is a URL (scheme://, www., host/path, tel: sip: msteams: zoommtg: ...), a dial string
     (",,123456789#", "123456789#"), or a run of 7 or more digits (any Unicode decimal digit, counted across single spaces,
     dots and dashes, a date such as 12-11-2026, 2026-11-12 or 12.11.26 being set aside first). A BLOCK is a run of consecutive
     lines that are neither blank nor a divider; a block holding an anchor is dropped whole. A DIVIDER (three or more of
     _ - = * ~ # . or box-drawing characters, spaces allowed) ends the block above it (even without a blank line) and opens a
     REGION that lasts to the next divider; a region holding an anchor is dropped whole (every block in it). Blank lines and
     dividers are never dropped. No label word is consulted.
  2. Shape gate, on what is left, one line at a time. A line that is a single token (no space) and is: all digits, 5 or more
     (a bare PIN or id; a four-digit number such as a year stays); ASCII letters AND digits only, 6 or more (an id or a
     password); ASCII letters only, 8 or more, with a run of 8 or more consonants (no vowel a e i o u y: not a word); or
     longer than 300 characters of base64/URL-safe characters (an encoded blob). Dates and times (12-11-2026, 14:00), room
     numbers and prices in a sentence fail no gate. Thresholds are deliberately conservative: a miss is covered by layer 3
     or accepted, a false drop costs the reader a line.
  3. Second layer (drop_labelled_values), the safety net for a secret typed into prose. See that function.
"""
import re
import unicodedata

CAP = 1500
BODY_MAX = 20000
VERSION = 1

_BLANK, _DIVIDER, _TEXT = 0, 1, 2

# ---------------------------------------------------------------- skeleton

_CONFUSABLE_PAIRS = (
    "аa еe оo рp сc хx уy іi јj ѕs ԁd ӏl Аa Вb Еe Кk Мm "
    "Нh Оo Рp Сc Тt Хx οo αa νv ρp ιi κK Οo Αa Βb Εe Ζz "
    "Ηh Ιi Κk Μm Νn Ρp Τt Υy Χx"
)
_CONFUSABLES = str.maketrans({p[0]: p[1].lower() for p in _CONFUSABLE_PAIRS.split()})


def _skeleton(line):
    """The line as it is judged: NFKC, invisible (Cf) characters removed, look-alikes mapped, lower case, spaces collapsed."""
    s = line
    if not s.isascii():
        s = unicodedata.normalize("NFKC", s)
        s = "".join(c for c in s if unicodedata.category(c) != "Cf")
        s = s.translate(_CONFUSABLES)
    return " ".join(s.lower().split())


_DIV_CHARS = "_-=*~#." + "".join(chr(c) for c in range(0x2500, 0x2580)) + "‐‑‒–—―"


def _is_divider(s):
    """Three or more divider marks and nothing else (spaces allowed). Two marks ('--') are not a divider."""
    t = s.replace(" ", "")
    return len(t) >= 3 and not t.strip(_DIV_CHARS)


# ---------------------------------------------------------------- dates, digit runs, anchors

_DATE = re.compile(r"(?<!\d)(\d{1,4})([-./])(\d{1,2})\2(\d{1,4})(?![-./]?\d)")
_DATE_WHOLE = re.compile(r"(\d{1,4})([-./])(\d{1,2})\2(\d{1,4})")
_TIME = re.compile(r"\d{1,2}:\d{2}(?::\d{2})?(?:-\d{1,2}:\d{2}(?::\d{2})?)?")
_CHAIN = re.compile(r"\d(?:[ .\-‐-―]{0,3}\d)*")
_URL = re.compile(r"(?<![a-z0-9])(?:[a-z][a-z0-9+.\-]{1,20}://|www\.|(?:sips?|msteams|zoommtg|zoomus|callto|skype):\S|tel:[+\d(])")
_HOSTPATH = re.compile(r"(?<![a-z0-9@._\-])[a-z0-9][a-z0-9\-]*(?:\.[a-z0-9\-]+)*\.[a-z]{2,}/[^\s/]")
_DIAL = re.compile(r"(?<!,),,+ ?[\d#]|(?<!\d)\d{3,}#")
_HOLE = "￼"          # stands where a date was; not a digit, not a separator


def _date_parts_ok(a, b, c):
    """Is a/b/c a plausible day-month-year, year-month-day or month-day-year (digit strings)?"""
    x, y, z = int(a), int(b), int(c)
    if len(a) == 4:
        return 1 <= y <= 12 and 1 <= z <= 31 and len(c) <= 2
    if len(a) <= 2 and len(c) in (2, 4):
        return (1 <= x <= 31 and 1 <= y <= 12) or (1 <= x <= 12 and 1 <= y <= 31)
    return False


def _date_sub(m):
    """re.sub callback: a plausible date becomes the placeholder, anything else is left alone."""
    return _HOLE if _date_parts_ok(m.group(1), m.group(3), m.group(4)) else m.group(0)


def _is_date_token(tok):
    """Is the whole token a date (12-11-2026, 2026-11-12, 12.11.26)?"""
    m = _DATE_WHOLE.fullmatch(tok)
    return bool(m) and _date_parts_ok(m.group(1), m.group(3), m.group(4))


def _is_datetime_token(tok):
    """Is the whole token a date, a time or a time range? Such a token is never a secret value."""
    return _is_date_token(tok) or _TIME.fullmatch(tok) is not None


def _digit_run(s):
    """Seven or more decimal digits (category Nd) in a chain: digits joined by gaps of at most three spaces, dots or dashes."""
    for m in _CHAIN.finditer(_DATE.sub(_date_sub, s)):
        if m.end() - m.start() >= 7 and sum(1 for c in m.group() if c.isdecimal()) >= 7:
            return True
    return False


def _has_anchor(s):
    """Does this skeleton hold a strong anchor: a link, a dial string or seven digits?"""
    return bool(_URL.search(s) or _HOSTPATH.search(s) or _DIAL.search(s) or _digit_run(s))


# ---------------------------------------------------------------- shape gate

_ALNUM = re.compile(r"[^\W_]+")
_BLOB = re.compile(r"[a-z0-9+/=_\-%.~]+")
_CONSONANTS = re.compile(r"[^aeiouy]{8,}")


def _shape_drop(s):
    """The shape gate: is this one-token skeleton an id, a password or an encoded blob? (See the module docstring.)"""
    if " " in s:
        return False
    if len(s) > 300 and _BLOB.fullmatch(s):
        return True
    if not _ALNUM.fullmatch(s):
        return False
    if s.isdecimal():
        return len(s) >= 5
    if not s.isascii():
        return False
    if s.isalpha():
        return len(s) >= 8 and _CONSONANTS.search(s) is not None
    return len(s) >= 6


# ---------------------------------------------------------------- layers 1 and 2

_WHOLE_BLOCK = True       # test hooks for the mutation tests; never changed in production
_USE_REGIONS = True


def _mark(drop, kinds, lo, hi):
    """Drop every text line in lo..hi-1 (blank lines and dividers stay)."""
    for k in range(lo, hi):
        if kinds[k] == _TEXT:
            drop[k] = 1


def _block_drops(kinds, strong, drop):
    """Drop the whole block (or, with _WHOLE_BLOCK off, only the anchor line) wherever a block holds an anchor."""
    n, i = len(kinds), 0
    while i < n:
        if kinds[i] != _TEXT:
            i += 1
            continue
        j = i
        while j < n and kinds[j] == _TEXT:
            j += 1
        if any(strong[i:j]):
            if _WHOLE_BLOCK:
                _mark(drop, kinds, i, j)
            else:
                for k in range(i, j):
                    drop[k] = drop[k] or strong[k]
        i = j


def _region_drops(kinds, strong, drop):
    """A divider opens a region that lasts to the next divider; a region holding an anchor is dropped whole."""
    start = None
    for i in range(len(kinds) + 1):
        if i < len(kinds) and kinds[i] != _DIVIDER:
            continue
        if start is not None and any(strong[start:i]):
            _mark(drop, kinds, start, i)
        start = i + 1


def _anchor_layer(lines):
    """Layers 1 and 2: the kept indices after the anchor drop and the shape gate."""
    skels = [_skeleton(x) for x in lines]
    kinds = [_BLANK if not s else (_DIVIDER if _is_divider(s) else _TEXT) for s in skels]
    strong = [1 if k == _TEXT and _has_anchor(s) else 0 for s, k in zip(skels, kinds)]
    drop = bytearray(len(lines))
    _block_drops(kinds, strong, drop)
    if _USE_REGIONS:
        _region_drops(kinds, strong, drop)
    return [i for i, s in enumerate(skels) if not drop[i] and not (kinds[i] == _TEXT and _shape_drop(s))]


# ---------------------------------------------------------------- layer 3: labelled values (S1b)

_LABELS = ("passcode", "pass code", "password", "pwd", "pin", "otp", "secret", "token", "api key", "access code",
           "meeting id", "conference id", "webinar id", "host key")
_SEP = re.compile(r"[:=>\-–—]|(?<![a-z0-9_])is(?![a-z0-9_])")
_SKIP = re.compile(r"[\s:=>\-–—\"'(\[{“‘]*")
_TOK = re.compile(r"\S{0,64}")
_HEX = re.compile(r"[0-9a-f]{6,}")
_TAIL_PUNCT = ".,;:!?)]}\"'”’"


def _label_ends_at(s, j):
    """Does a hard label end exactly at s[:j], starting at a word boundary ('Opinion' holds 'pin' but is not it)?"""
    for lab in _LABELS:
        k = j - len(lab)
        if k >= 0 and s.startswith(lab, k) and (k == 0 or not (s[k - 1].isalnum() or s[k - 1] == "_")):
            return True
    return False


def _is_value_token(tok):
    """A secret-shaped token: it holds a decimal digit (and is not a date or a time), or is a run of 6 or more hex characters."""
    t = tok.rstrip(_TAIL_PUNCT)
    if not t or _is_datetime_token(t):
        return False
    return any(c.isdecimal() for c in t) or _HEX.fullmatch(t) is not None


def _first_token(s, pos=0):
    """The first token at or after pos, past spaces, separators and opening quotes or brackets (at most 64 characters)."""
    return _TOK.match(s, _SKIP.match(s, pos).end()).group()


def _same_line(s):
    """Is there 'label, separator, value' on this line? The label is the last word(s) before the separator."""
    for m in _SEP.finditer(s):
        j = m.start()
        while j > 0 and s[j - 1] == " ":
            j -= 1
        if _label_ends_at(s, j) and _is_value_token(_first_token(s, m.end())):
            return True
    return False


def _ends_with_label(s):
    """Does the line end with a hard label (and perhaps a separator): the value, if any, is on the next line?"""
    t = s.rstrip(" :=>-–—")
    if t.endswith(" is"):
        t = t[:-3].rstrip(" :=>-–—")
    return _label_ends_at(t, len(t))


def drop_labelled_values(lines):
    """The second layer (S1b). Returns the KEPT indices, ascending. A line goes when its skeleton holds a hard label (passcode,
    pass code, password, pwd, pin, otp, secret, token, api key, access code, meeting id, conference id, webinar id, host key,
    with any provider prefix) as the last word(s) before a separator (: = - en dash em dash > or the word 'is'), followed by a
    value: the first token after the separator holds a decimal digit (a date or a time never counts) or is a run of 6+ hex
    characters. When the label ends the line, the next non-blank line goes as well if its first token is such a value, and that
    one line only. A line is judged on itself; a label's successor is the next non-blank line still standing, so one pass is final
    (the result is stable: running it again changes nothing). Blank lines are never dropped. Words are not values."""
    n = len(lines)
    alive = bytearray(b"\x01") * n
    stack = []                                    # non-blank survivors: [index, ends with a label]
    for i, line in enumerate(lines):
        s = _skeleton(line)
        if not s:
            continue
        if _same_line(s):
            alive[i] = 0
        elif stack and stack[-1][1] and _is_value_token(_first_token(s)):
            alive[stack.pop()[0]] = 0
            alive[i] = 0
        else:
            stack.append((i, _ends_with_label(s)))
    return [i for i in range(n) if alive[i]]


# ---------------------------------------------------------------- the public functions

def keep_indices(lines, *, second_layer=True):
    """The ascending indices of the kept input lines: the anchor layer and shape gate, then (second_layer) the label layer."""
    lines = list(lines)
    keep = _anchor_layer(lines)
    if second_layer:
        keep = [keep[j] for j in drop_labelled_values([lines[i] for i in keep])]
    return keep


def keep_lines(lines, *, second_layer=True):
    """The kept lines: a subsequence of the input, byte for byte (never edited, never new)."""
    lines = list(lines)
    return [lines[i] for i in keep_indices(lines, second_layer=second_layer)]


def _cut(text):
    """Cut a body to BODY_MAX characters at a line end (a half line is dropped, so the output stays a subset)."""
    if len(text) <= BODY_MAX:
        return text
    if text[BODY_MAX] == "\n":
        return text[:BODY_MAX]
    head = text[:BODY_MAX]
    k = head.rfind("\n")
    return head[:k] if k >= 0 else ""


def _capped(lines):
    """Whole lines in order while the joined text (with newlines) stays within CAP; the first line that would cross ends it."""
    out, total = [], 0
    for ln in lines:
        add = len(ln) + (1 if out else 0)
        if total + add > CAP:
            break
        out.append(ln)
        total += add
    return out


def filter_text(text, *, second_layer=True):
    """The body filter for stored text: BODY_MAX cut, split on newline, keep_lines, join, then the CAP (whole lines only)."""
    return "\n".join(_capped(keep_lines(_cut(text).split("\n"), second_layer=second_layer)))
