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
import bisect
import collections
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
    """The line as it is judged: NFKD, accents (Mn) and invisible (Cf) characters removed, NFKC, look-alikes mapped, lower case."""
    s = line
    if not s.isascii():
        s = unicodedata.normalize("NFKD", s)          # accents split off (š -> s + mark) so an accented label still reads
        s = "".join(c for c in s if unicodedata.category(c) not in ("Cf", "Mn"))
        s = unicodedata.normalize("NFKC", s)
        s = s.translate(_CONFUSABLES)
    s = " ".join(s.lower().split())
    if "." in s:
        s = _DOTTED_LETTERS.sub(lambda m: m.group().replace(".", ""), s)
    return _SPACED_LETTERS.sub(_join_letters, s) if " " in s else s


# E1 pass 2, finding 9: 'P A S S W O R D : 4330' reads as 'password : 4330' (four or more single letters in a row, one space apart)
# (a run of more than 24 letters is text, not a label, and stays as it is)
_SPACED_LETTERS = re.compile(r"(?<![^\W\d_])(?<![^\W\d_] )(?:[^\W\d_] ){3,}[^\W\d_](?![^\W\d_])")


# Cap re-check 2, LOW: 'P.A.S.S.C.O.D.E: 4330' reads as 'passcode: 4330' (four or more single letters, each followed by a dot)
_DOTTED_LETTERS = re.compile(r"(?<![^\W\d_.])(?<![^\W\d_]\.)(?:[^\W\d_]\.){3,}[^\W\d_]\b\.?(?![^\W\d_])")


def _join_letters(m):
    run = m.group()
    return run.replace(" ", "") if len(run) <= 47 else run


_DIV_CHARS = "_-=*~#." + "".join(chr(c) for c in range(0x2500, 0x2580)) + "‐‑‒–—―"


def _is_divider(s):
    """Three or more divider marks and nothing else (spaces allowed). Two marks ('--') are not a divider."""
    t = s.replace(" ", "")
    return len(t) >= 3 and not t.strip(_DIV_CHARS)


# ---------------------------------------------------------------- dates, digit runs, anchors

_DATE = re.compile(r"(?<!\d)(?<!\d[-./])(\d{1,4})([-./])(\d{1,2})\2(\d{1,4})(?![-./]?\d)")
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


_L = r"(?<!\d)(?<!\d[.\-])"            # a shape does not start inside a longer digit chain
_R = r"(?!\d)(?![.\-]\d)"               # ... and does not end inside one
_NUM = r"(?:\d{1,3}(?:[,.' ]\d{3})+|\d+)(?:[.,]\d{1,2})?"
_CUR_PRE = "[£$€¥₹]"
_CUR_POST = (r"(?:[£$€¥₹]|(?:kr|eur|euros?|gbp|usd|sek|nok|dkk|chf|cad|aud|jpy|inr|pounds|dollars|million|billion|mn|bn)"
             r"(?![a-z0-9]))")


def _ok_date(m):
    return _date_parts_ok(m.group(1), m.group(3), m.group(4))


def _ok_clock_range(m):
    a, b, c, d = (int(x) for x in m.groups())
    return a <= 24 and c <= 24 and b <= 59 and d <= 59


def _ok_compact_range(m):
    return _ok_clock_range(m) and (int(m.group(1)), int(m.group(2))) < (int(m.group(3)), int(m.group(4)))


def _ok_year_range(m):
    return int(m.group(1)) < int(m.group(2)) <= int(m.group(1)) + 30


def _ok_build(m):
    parts = m.group(0).split(".")
    if any(len(x) > 1 and x[0] == "0" for x in parts):
        return False                                # '0958', '010': a phone's groups
    return any(len(x) <= 2 for x in parts[1:])      # one short part ('3.14.2.1007'; '12.345.678.901' has none)


# (name, pattern, validator or None, why it is not a secret). A match that passes its validator is replaced by a placeholder before the
# 7-digit rule runs, in this order; one that fails is left for the rule. Added a shape: add its positives and negatives to
# dev/tests/test_invite_filter_numbers.py (SHAPE_CASES).
SHAPES = (
    ("date", _DATE, _ok_date,
     "12-11-2026, 2026-11-12, 12.11.26: a plausible day, month and year (_date_parts_ok)."),
    ("compact_date", re.compile(_L + r"(?:19|20)\d\d(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])(?:t[0-2]\d[0-5]\d[0-5]\dz?)?(?!\d)"), None,
     "20261112 and 20261112T140000Z (ICS, file names): the month and day are real and the year is 1900-2099."),
    ("time_range", re.compile(_L + r"(\d{1,2})[.:](\d{2})\s*[-–—]\s*(\d{1,2})[.:](\d{2})" + _R), _ok_clock_range,
     "14.00 - 15.30, 14.00-15.30: a slot; hours up to 24, minutes up to 59."),
    ("time_range_compact", re.compile(_L + r"(\d{2})(\d{2})\s*[-–—]\s*(\d{2})(\d{2})" + _R), _ok_compact_range,
     "1400-1530: a slot written without a separator; valid hours and minutes, the end after the start (a phone number rarely is)."),
    ("year_range", re.compile(_L + r"((?:19|20)\d\d)\s*[-–—]\s*((?:19|20)\d\d)" + _R), _ok_year_range,
     "2026-2027, 2026 - 2027: a budget or plan span; the end year is later, at most 30 years on."),
    ("money", re.compile(_L + "(?:" + _CUR_PRE + r"\s?" + _NUM + "|" + _NUM + r"\s?" + _CUR_POST + ")" + _R), None,
     "A currency symbol or code on the number (£1250000, 1.250.000 €, 1 250 000 kr): an amount. A bare 1250000 is not set aside."),
    ("build_number", re.compile(r"(?<![\d.+(])[1-9]\d?(?:\.\d{1,5}){3,}(?!\d)(?!\.\d)"), _ok_build,
     "3.14.2.1007: four or more dotted parts, no leading zero, one part of at most two digits (a dotted phone has none)."),
    ("po_ticket", re.compile(r"(?<![a-z0-9])(?:(po|pr|inv|invoice|order|ticket|case|request|req|change|task|incident|sr|wo|quote|contract|"
                             r"job|batch|serial|asset|sku|doc|document)(?:[ .:#-]{1,2}(?:no\.?|nr\.?|number)?[ .:#-]{0,2})"
                             r"|(inc|req|ritm|chg|prb|task|sctask|tkt|rfc|wo|sr|so|po|inv)[-_#]?)\d{6,}" + _R), None,
     "PO 4500123456, Invoice #20261234, INC0012345, REQ0012345: a business reference named by a word of that vocabulary or an "
     "ITSM prefix. 'ref', 'id', 'pin', 'code', 'tel' and any other prefix keep the digit-run rule."),
)


def _mask_shapes(s):
    """The skeleton with every shape in SHAPES replaced by a placeholder (not a digit, not a separator), in table order."""
    for name, pat, ok, _why in SHAPES:
        if name == "date":
            s = _DATE.sub(_date_sub, s)
        else:
            s = pat.sub(lambda m, ok=ok: _HOLE if ok is None or ok(m) else m.group(0), s)
    return s


def _digit_run(s):
    """Seven or more decimal digits (category Nd) in a chain: digits joined by gaps of at most three spaces, dots or dashes.
    Number shapes (SHAPES: dates, ranges, amounts, builds, references) are set aside first."""
    for m in _CHAIN.finditer(_mask_shapes(s)):
        if m.end() - m.start() >= 7 and sum(1 for c in m.group() if c.isdecimal()) >= 7:
            return True
    return False


# 2.6.9 item 4b: address-style tokens that carry a PIN or a session (narrow on purpose; see dev/proposals/375/DECISIONS-HIGH.md)
_ADDR = re.compile(r"(?<![a-z0-9._+\-])([a-z0-9._+\-]{3,60})@[a-z0-9][a-z0-9.\-]*")
_ADDR_WORD = re.compile(r"join|meet|pin|conf|bridge|dial|pass|code")
_ADDR_DIGITS = re.compile(r"\d{4,}")
_MAILTO_JOIN = re.compile(r"mailto:[^\s@]{0,60}(?:join|meet|pin|conf|bridge|dial|pass|code)[^\s@]{0,40}\d{4}")
_JWT = re.compile(r"(?<![a-z0-9])eyj[a-z0-9_\-]{8,}\.[a-z0-9_\-]{8,}")


def _address_pin(s):
    """A join/meet/pin word and 4 or more digits in the local part of an address (meet-8990@x, join449038@x, pin.1234@x), or a JWT."""
    if "@" in s:
        for m in _ADDR.finditer(s):
            loc = m.group(1)
            if _ADDR_WORD.search(loc) and _ADDR_DIGITS.search(loc):
                return True
        if _MAILTO_JOIN.search(s):
            return True
    return _JWT.search(s) is not None


def _has_anchor(s):
    """Does this skeleton hold a strong anchor: a link, a dial string, seven digits, or (2.6.9) an address that carries a PIN or a JWT?"""
    return bool(_URL.search(s) or _HOSTPATH.search(s) or _DIAL.search(s) or _digit_run(s) or _address_pin(s))


# 2.6.9 HIGH 2: a code in a plain sentence ('Use 6802 to join', 'Pass 4417'): that line only, never its block
_YEAR = re.compile(r"(?:19|20)\d\d")        # a bare year is not taken for a code (2 percent of 4-digit PINs are lost)
_USE_SENTENCE = True        # test hook
_SENT_VERB = re.compile(r"(?<![a-z0-9])(?:use|enter|pass|dial|type|press|quote|key in|passcode|code|pin|password|access code)"
                        r"[:#]?\s+(\d{4,6})(?![\w/%\-]|[.,:]\d)")
_SENT_CTX = frozenset(("join", "dial", "enter", "access", "prompted", "meeting", "call", "bridge", "connect", "login", "sign"))


def _sentence_code(s):
    """A code in a plain sentence: a use/enter/pass/dial/type/press word directly before a 4 to 6 digit number (not a year, date or time)
    in a line of at most 3 words ('Pass 4417') or one that also holds a join/dial/enter/access/prompted/call word ('Use 6802 to join')."""
    if len(s) > 100:
        return False
    m = _SENT_VERB.search(s)
    if not m or _YEAR.fullmatch(m.group(1)) or _is_datetime_token(m.group(1)):
        return False
    words = re.findall(r"[^\W\d_]+", s)
    return len(words) <= 3 or bool(_SENT_CTX & set(words))


# 2.6.9 item 4a: an id written one group per line ('412', '889', '330') or folded over lines
def _digit_group_line(s):
    """Is the skeleton a short digit-only line (1 to 4 decimal digits, nothing else)?"""
    t = s.strip()
    return len(t) <= 4 and t.isdecimal()


def _joined_digit_lines(kinds, skels):
    """Indices of consecutive short digit-only lines (at most 4 digits each) that together make an id: three or more lines with
    6 or more digits, or two lines of 3 or 4 digits each (6 or more: the scrub may already have taken the first group with its
    label). Joined lines are not separated by a blank line or a divider."""
    out, n, i = [], len(kinds), 0
    while i < n:
        if kinds[i] != _TEXT or not _digit_group_line(skels[i]):
            i += 1
            continue
        j = i
        while j < n and kinds[j] == _TEXT and _digit_group_line(skels[j]):
            j += 1
        total = sum(len(skels[k].strip()) for k in range(i, j))
        cnt = j - i
        if (cnt >= 3 and total >= 6) or (cnt >= 2 and total >= 6 and all(len(skels[k].strip()) >= 3 for k in range(i, j))):
            out.extend(range(i, j))
        i = j
    return out


# ---------------------------------------------------------------- shape gate

_ALNUM = re.compile(r"[^\W_]+")
_BLOB = re.compile(r"[a-z0-9+/=_\-%.~]+")
_CONSONANTS = re.compile(r"[^aeiouy]{8,}")
# a lone table cell such as Room204, Level4, Q42026, FY2026, INC0012345: a word of the agenda's own vocabulary and its number. Any other
# letters+digits token (Summer2026, xk9Pq27a, Pin8825) stays an id or a password. A bare run of 5+ digits ('125000', '90210') STAYS dropped
# (a PIN), as does anything that is only digits; a comma- or dot-grouped number or one with a currency sign is not a token and was
# never dropped.
_ORDINARY_ID = re.compile(r"(?:room|rm|floor|level|suite|desk|table|team|sprint|phase|week|wave|build|release|ver|version|rev|"
                          r"ticket|inc|req|chg|"
                          r"task|story|epic|case|po|pr|fy|q[1-4]|h[12]|ref|sr|wo)\d{1,10}|q[1-4]\d{4}|fy\d{2,4}|(?:19|20)\d{6}t\d{6}z?")


# 2.6.9 item 4b: three more one-token shapes (a whole line)
# Summer2026!  (letters, digits, then marks)
_PWD_PUNCT = re.compile(r"(?=[^\W_]*[^\W\d_])(?=[^\W_]*\d)[^\W_]{4,}[!@#$%^&*?+=~]{1,3}(?:[^\W_]{0,3})")
_MEET_CODE = re.compile(r"[a-z]{3}-[a-z]{4}-[a-z]{3}")        # abc-defg-hij (a Google Meet code)
_RUN16 = re.compile(r"[a-z0-9]{16,}")


def _token_blob(s):
    """A long token with . _ - joins and a random-looking run of 16+ letters and digits (4+ letter/digit changes): sk-live-... keys."""
    if len(s) < 20 or len(s) > 300 or not _BLOB.fullmatch(s):
        return False
    for m in _RUN16.finditer(s):
        r = m.group()
        changes = sum(1 for a, b in zip(r, r[1:]) if a.isdecimal() != b.isdecimal())
        if sum(c.isdecimal() for c in r) >= 3 and changes >= 4:
            return True
    return False


def _shape_drop(s):
    """The shape gate: is this one-token skeleton an id, a password or an encoded blob? (See the module docstring.)"""
    if " " in s:
        return False
    if len(s) > 300 and _BLOB.fullmatch(s):
        return True
    if _PWD_PUNCT.fullmatch(s) or _MEET_CODE.fullmatch(s) or _token_blob(s):
        return True
    if not _ALNUM.fullmatch(s):
        return False
    if s.isdecimal():
        return len(s) >= 5
    if not s.isascii():
        return False
    if _ORDINARY_ID.fullmatch(s):
        return False
    if s.isalpha():
        return len(s) >= 8 and _CONSONANTS.search(s) is not None
    return len(s) >= 6


def _shape_drop_line(s):
    """The shape gate on a line; a table row ('a | b', #375 1d) is judged cell by cell, as each cell was a line of its own before."""
    if " | " in s:
        return any(_shape_drop(c.strip()) for c in s.split(" | "))
    return _shape_drop(s)


# ---------------------------------------------------------------- layers 1 and 2

_WHOLE_BLOCK = True       # test hooks for the mutation tests; never changed in production
_USE_REGIONS = True


def _mark(drop, kinds, lo, hi):
    """Drop every text line in lo..hi-1 (blank lines and dividers stay)."""
    for k in range(lo, hi):
        if kinds[k] == _TEXT:
            drop[k] = 1


# 2.6.9 item 6: a signature block loses only the lines that hold the number (and its label), not the name and title
_SIGNOFF = frozenset(("regards", "best regards", "kind regards", "warm regards", "with kind regards", "best wishes", "best", "thanks",
                      "thank you", "many thanks", "thanks and regards", "cheers", "sincerely", "yours sincerely", "yours faithfully",
                      "--", "-- ", "---"))
_SIGN_TAIL = " ,.!;:"
_PHONE_LABEL = re.compile(r"(?:m|t|tel|mob|mobile|cell|phone|direct|office|fax|ph|telephone|dd|call)\.?:?")
_USE_SIGNATURE = True       # test hook; never changed in production


def _is_signoff(s):
    t = s.strip(_SIGN_TAIL) if s.strip(_SIGN_TAIL) else s.strip()
    return t in _SIGNOFF or s.strip() in _SIGNOFF


def _block_end(kinds, i):
    j = i
    while j < len(kinds) and kinds[j] == _TEXT:
        j += 1
    return j


def _signature_start(kinds, skels, i, j):
    """Index of the first sign-off line in the block i..j-1 (regards, best, thanks, '--'), or None. The lines before it are the body."""
    for k in range(i, j):
        if _is_signoff(skels[k]):
            return k
    return None


def _signature_drops(strong, drop, skels, sg, j):
    """A signature block (sign-off line sg): drop the anchor lines below it and a phone label line just above one, nothing else."""
    for k in range(sg + 1, j):
        if strong[k]:
            drop[k] = 1
            if k - 1 > sg and not strong[k - 1] and _PHONE_LABEL.fullmatch(skels[k - 1].strip()):
                drop[k - 1] = 1


def _strong_block(kinds, strong, drop, skels, weak, i, j):
    """The block i..j-1 holds a strong anchor: a signature block loses only its anchor lines (and plain links, and a phone label line
    above one); any other block goes whole (or, with _WHOLE_BLOCK off, only its anchor lines). Returns 'sig', 'whole' or 'lines'."""
    sg = _signature_start(kinds, skels, i, j) if (_USE_SIGNATURE and skels is not None) else None
    if sg is not None and sg < next(k for k in range(i, j) if strong[k]):
        _signature_drops(strong, drop, skels, sg, j)
        if weak is not None:
            for k in range(sg + 1, j):
                drop[k] = drop[k] or weak[k]
        return "sig"
    if _WHOLE_BLOCK:
        _mark(drop, kinds, i, j)
        return "whole"
    for k in range(i, j):
        drop[k] = drop[k] or strong[k]
    return "lines"


def _block_drops(kinds, strong, drop, skels=None, weak=None):
    """Drop the whole block (or, with _WHOLE_BLOCK off, only the anchor line) wherever a block holds an anchor.
    A signature block (a sign-off line before the anchor, 2.6.9) loses only the anchor lines and the phone label line just above one.
    weak (E1 pass 2, finding 3): lines whose only anchor is a plain link; in a block with no strong anchor they go alone.
    Returns the set of block starts handled as signatures and the set dropped as a whole."""
    n, i = len(kinds), 0
    sig_blocks, whole = set(), set()
    while i < n:
        if kinds[i] != _TEXT:
            i += 1
            continue
        j = _block_end(kinds, i)
        if any(strong[i:j]):
            how = _strong_block(kinds, strong, drop, skels, weak, i, j)
            if how == "sig":
                sig_blocks.add(i)
            elif how == "whole":
                whole.add(i)
        elif weak is not None:
            for k in range(i, j):
                drop[k] = drop[k] or weak[k]
        i = j
    return sig_blocks, whole


def _region_drops(kinds, strong, drop, skip=None):
    """A divider opens a region that lasts to the next divider; a region holding an anchor is dropped whole.
    skip (2.6.9): indices whose anchor belongs to a signature block and is handled line by line, so it does not condemn the region."""
    start = None
    for i in range(len(kinds) + 1):
        if i < len(kinds) and kinds[i] != _DIVIDER:
            continue
        if start is not None and any(strong[k] and not (skip and k in skip) for k in range(start, i)):
            _mark(drop, kinds, start, i)
        start = i + 1


# 2.6.9 HIGH 1: a short value-only block right after a dropped anchor block belongs to that block (a PIN behind a label we do not list)
# E1 pass 2 (findings 1, 2, 4, 5, 6): the candidate is judged as a WHOLE block of value tokens only (a spaced 984 522 counts, a list
# marker is ignored, a sentence or 'Room 1204' does not), and it may follow ANY line the scrub or the anchor layer removed.
_ORPHAN_MAX_CHARS = 24
_ORPHAN_MAX_TOKENS = 4
_ORPHAN_NUM = re.compile(r"\d{4,8}")
_ORPHAN_MIXED = re.compile(r"(?=[a-z0-9]*\d)(?=[a-z0-9]*[^\W\d_])[a-z0-9]{5,12}")
_ORPHAN_STRIP = ".,;:!?()[]{}\"'|<>=*#"
_ORPHAN_MARKER = re.compile(r"^(?:[-*+\u2022\u00b7\u25e6\u25aa\u2023\u2013\u2014>]|\d{1,2}[.)])\s+")
_ORPHAN_ORDINARY = frozenset(("room", "rm", "floor", "level", "suite", "desk", "table", "team", "sprint", "phase", "week", "wave", "build",
                              "release", "ver", "version", "rev", "ticket", "inc", "req", "chg", "task", "story", "epic", "case", "ext",
                              "extension", "budget", "fy", "item", "step", "page", "slide", "row", "line", "plan", "agenda", "year",
                              "date", "time", "total", "cost", "price", "order", "po", "pr", "invoice", "tel", "phone", "fax", "mob"))
_ORPHAN_SMALL = re.compile(r"\d{2,4}")
_USE_ORPHANS = True         # test hook


def _orphan_value(tok):
    t = tok.strip(_ORPHAN_STRIP)
    if not t:
        return False
    if _ORPHAN_NUM.fullmatch(t) and not _is_datetime_token(t):
        return True
    return _ORPHAN_MIXED.fullmatch(t) is not None and not _is_datetime_token(t)


def _label_only(s):
    """A bare label line: one to three words, no digit, at most 24 characters ('Clave', 'Room key:')."""
    t = s.strip().rstrip(":").strip()
    return bool(t) and len(t) <= _ORPHAN_MAX_CHARS and not any(c.isdecimal() for c in t) and len(t.split()) <= 3 \
        and all(w.strip(_ORPHAN_STRIP).replace("-", "").replace("'", "").isalpha() for w in t.split())


def _orphan_tokens(strs):
    """The tokens of 1 to 2 lines (skeletons) with list markers removed and edge punctuation stripped; None when a line is longer than
    24 characters or the group has more than 4 tokens."""
    toks = []
    for x in strs:
        x = _ORPHAN_MARKER.sub("", x.strip())
        if not x or len(x) > _ORPHAN_MAX_CHARS:
            return None
        toks.extend(x.split())
    if not toks or len(toks) > _ORPHAN_MAX_TOKENS:
        return None
    return [t.strip(_ORPHAN_STRIP) for t in toks]


def _without_lead_words(core):
    """The tokens after one or two label words in front ('gecis kodu wExCzXM7'); an ordinary word (room, ticket, ext ...) is no label."""
    lead = 0
    while lead < 2 and lead < len(core) - 1 and core[lead].isalpha() and 2 <= len(core[lead]) <= 12 \
            and core[lead] not in _ORPHAN_ORDINARY:
        lead += 1
    return core[lead:]


def _spaced_value(core):
    """Two to four short digit groups that make a 4 to 8 digit value together ('984 522'); no group a year."""
    return (len(core) >= 2 and all(_ORPHAN_SMALL.fullmatch(t) for t in core) and 4 <= sum(map(len, core)) <= 8
            and not any(_YEAR.fullmatch(t) for t in core))


def _orphan_lines(strs, allow_year=False):
    """Is this group of 1 to 2 lines VALUE TOKENS ONLY: each token digits or a short letter-digit token, after at most two label words
    (never an ordinary word); with a 4-8 digit number, a letter-digit token or a spaced run (984 522)? A sentence is not one.
    A bare year alone is a value only with allow_year (a label line before it)."""
    core = _orphan_tokens(strs)
    if core is None:
        return False
    core = _without_lead_words(core)
    if not core or not all(t.isdecimal() or _ORPHAN_MIXED.fullmatch(t) for t in core):
        return False
    vals = [t for t in core if _orphan_value(t)]
    if not vals:
        return _spaced_value(core)
    return allow_year or not all(_YEAR.fullmatch(t) for t in core)


def _orphan_block(kinds, skels, i, j, allow_year=False):
    """Is the block i..j-1 a short value-only block (see _orphan_lines)? A label line first and a value line second also counts: the
    year rule then lifts ('Clave\n2026')."""
    if j - i > 2:
        return False
    if j - i == 2 and _label_only(skels[i]):
        return _orphan_lines([skels[i + 1]], True)
    return _orphan_lines([skels[k] for k in range(i, j)], allow_year)


class _Chain:
    """Where the orphan walk stands: armed after a removed line, up to two groups taken, at most one divider between, a bare label seen."""

    def __init__(self):
        self.reset()

    def reset(self):
        """Back to the start."""
        self.armed, self.taken, self.divs, self.label = False, 0, 0, None

    def divider(self):
        """A divider line: a second one in a row ends the chain."""
        self.divs += 1
        if self.divs > 1:
            self.reset()

    def open(self):
        """May another group be taken?"""
        return self.armed and self.taken < 2


def _orphan_drops(kinds, skels, drop, whole):
    """After a block dropped whole for its anchor (blank lines between allowed, one divider allowed), up to two following short
    value-only blocks go too. A bare label line between is passed over, not counted, and goes with the value that follows it."""
    n, i, st = len(kinds), 0, _Chain()
    while i < n:
        if kinds[i] == _BLANK:
            i += 1
            continue
        if kinds[i] == _DIVIDER:
            st.divider()
            i += 1
            continue
        j = _block_end(kinds, i)
        st.divs = 0
        if i in whole:
            st.reset()
            st.armed = True
        elif not st.open() or any(drop[i:j]):
            st.reset()
        elif j - i == 1 and _label_only(skels[i]):
            st.label = (i, j)
        elif _orphan_block(kinds, skels, i, j, st.label is not None):
            _mark(drop, kinds, i, j)
            if st.label is not None:
                _mark(drop, kinds, st.label[0], st.label[1])
            st.taken += 1
            st.label = None
        else:
            st.reset()
        i = j


# E1 pass 2, finding 3: a plain link (a wiki page, a company site) is not a join secret, so it costs its own line, not its block. A link
# that carries a session (digits, a passcode/token query, a long mixed token, a meeting-join path) keeps dropping the block.
_LINK_QUERY = re.compile(r"[?&;#][a-z0-9_.\-]*(?:pwd|pass|token|code|pin|secret|otp|key|sig|auth|session|mtid|meetingid|confid|uid)"
                         r"[a-z0-9_.\-]*=")
_LINK_JOIN = re.compile(r"meetup-join|/join(?:[/?#]|$)|/j/|j\.php|/wc/|/webinar/|/conference/|/meeting/|/meet/|/my/")
_LINK_DIGITS = re.compile(r"(?<!\d)(?!(?:19|20)\d\d(?!\d))\d{4}")       # four digits that are not a year
_LINK_TOKEN = re.compile(r"(?=[a-z0-9_\-]*\d)[a-z0-9_\-]{16,}")


_LINK_MEET = re.compile(r"(?<![a-z0-9])[a-z]{3}-[a-z]{4}-[a-z]{3}(?![a-z0-9])")       # a Google Meet code: abc-defg-hij
_MEET_HOST = re.compile(r"(?<![\w-])meet\.[a-z0-9-]+\.[a-z]{2,}", re.I)


def _meet_link(tok):
    """A Meet code counts only on a Meet host ('meet.google.com/abc-defg-hij', 'meet.example.org/...') or a provider host; an ordinary
    slug of the same shape on a wiki ('wiki.example.org/bid-plan-two', 'sop-hand-off') is not a join secret (Cap re-check 2, MEDIUM)."""
    if not _LINK_MEET.search(tok):
        return False
    mod = _scrub_module()
    return bool(_MEET_HOST.search(tok) or (mod is not None and mod.HOSTS.search(tok)))


def _plain_link(s):
    """Is the line's only anchor a link that carries no session: no digit run, no passcode-like query, no meeting-join path and no long
    mixed token? (The caller has already found it holds an anchor.)"""
    if _DIAL.search(s) or _digit_run(s) or _address_pin(s) or not (_URL.search(s) or _HOSTPATH.search(s)):
        return False
    for tok in s.split():
        if _URL.search(tok) or _HOSTPATH.search(tok):
            if (_LINK_QUERY.search(tok) or _LINK_JOIN.search(tok) or _LINK_TOKEN.search(tok) or _LINK_DIGITS.search(tok)
                    or _meet_link(tok)):
                return False
    return True


def _judge(lines, extras):
    """The skeletons, the line kinds, the strong-anchor flags and (extras) the plain-link flags of the lines."""
    skels = [_skeleton(x) for x in lines]
    kinds = [_BLANK if not s else (_DIVIDER if _is_divider(s) else _TEXT) for s in skels]
    strong = [1 if k == _TEXT and _has_anchor(s) else 0 for s, k in zip(skels, kinds)]
    weak = [0] * len(lines)
    if extras:
        for k in _joined_digit_lines(kinds, skels):      # adjacency changes when a line goes, so only where D loops to a fixpoint
            strong[k] = 1
        for k in range(len(lines)):
            if strong[k] and kinds[k] == _TEXT and _plain_link(skels[k]):
                strong[k], weak[k] = 0, 1
    return skels, kinds, strong, weak


def _context_drops(kinds, skels, drop, whole, orph):
    """The extras: the orphan rule (HIGH 1) and the sentence-code rule (HIGH 2).
    orph (a set) receives the indices the orphan rule dropped."""
    if _USE_ORPHANS:
        before = bytes(drop)
        _orphan_drops(kinds, skels, drop, whole)
        if orph is not None:
            orph.update(i for i in range(len(drop)) if drop[i] and not before[i])
    if _USE_SENTENCE:
        for i, s in enumerate(skels):
            if kinds[i] == _TEXT and not drop[i] and _sentence_code(s):
                drop[i] = 1


def _anchor_layer(lines, _orph=None, extras=False):
    """Layers 1 and 2: the kept indices after the anchor drop and the shape gate.
    _orph (a set) receives the indices the orphan rule dropped.
    extras (2.6.9, off by default so the layer stays label-free and local, P4): the joined digit lines, the orphan rule and the
    sentence-code rule, which look at context and at words. Only the scrub-first-pass body filter turns them on."""
    skels, kinds, strong, weak = _judge(lines, extras)
    drop = bytearray(len(lines))
    sig_blocks, whole = _block_drops(kinds, strong, drop, skels, weak if extras else None)
    if _USE_REGIONS:
        skip = set()
        for s0 in sig_blocks:
            skip.update(range(s0, _block_end(kinds, s0)))
        _region_drops(kinds, strong, drop, skip)
    if extras:
        _context_drops(kinds, skels, drop, whole, _orph)
    return [i for i, s in enumerate(skels) if not drop[i] and not (kinds[i] == _TEXT and _shape_drop_line(s))]


# ---------------------------------------------------------------- layer 3: labelled values (S1b)

_LABELS = ("passcode", "pass code", "password", "pwd", "pin", "otp", "secret", "token", "api key", "access code",
           "meeting id", "conference id", "webinar id", "host key")
# 2.6.9 HIGH 1: more hard labels for the languages the scrub does not list (accents and case folded as the skeleton does);
# used only by the extended label pass (_ext_labelled), never by the E1-minimal second layer.
_LABELS_X = _LABELS + (
    "clave", "contrasena", "hasło", "codigo de acceso", "codigo secreto", "losenord", "atkomstkod", "pinkod", "haslo", "kod dostepu",
    "kod pin",
    "sifre", "parola", "gecis kodu", "codice", "codice segreto", "codice di accesso", "senha", "codigo", "passwort", "kennwort",
    "zugangscode", "mot de passe", "code d'acces", "code secret", "code pin", "toegangscode", "wachtwoord", "pincode",
    "密码", "访问代码", "会议密码", "비밀번호", "암호", "패스코드", "пароль", "код доступа", "пин-код",
    "パスコード", "パスワード", "暗証番号",
    "pass", "passwd", "security code", "entry code", "door code", "verification code", "auth code", "one-time code", "participant code",
    "host code", "moderator pin", "guest pin", "bridge code", "meeting code", "room code", "join code", "dial-in code", "meeting number",
)
# letter-spaced two-word labels lose their word break ('A C C E S S  C O D E' is read as 'accesscode'), so the extended pass also knows each
# two-word label written solid (E1 pass 2, finding 9)
_LABELS_X += tuple(sorted({x.replace(" ", "") for x in _LABELS_X if " " in x and x.isascii()} - set(_LABELS_X)))
_USE_EXT_LABELS = True      # test hook


def _ext_labelled(lines):
    """The kept lines after the extended label pass (labelled value, same line or next line)."""
    return [lines[i] for i in drop_labelled_values(lines, _LABELS_X)]


_SEP = re.compile(r"[:=>\-–—]|(?<![a-z0-9_])is(?![a-z0-9_])")
_SEP_X = re.compile(r"[:=>|\-–—]|(?<![a-z0-9_])is(?![a-z0-9_])")      # the extended pass also reads a table bar as a separator
_SKIP = re.compile(r"[\s:=>\-–—\"'(\[{“‘]*")
_TOK = re.compile(r"\S{0,64}")
_HEX = re.compile(r"[0-9a-f]{6,}")
_TAIL_PUNCT = ".,;:!?)]}\"'”’"


def _label_ends_at(s, j, labels=None):
    """Does a hard label end exactly at s[:j], starting at a word boundary ('Opinion' holds 'pin' but is not it)?"""
    for lab in (labels or _LABELS):
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


def _bare_label_value(s, labels):
    """E1 pass 2, finding 7 (the extended pass only): a long, distinctive label (8 characters or more: 'kod dostepu', 'codigo de acceso')
    directly followed by a space and a value of 4 or more characters, with no separator: 'ask for the kod dostepu 7118 at the desk'."""
    for lab in labels:
        pos = s.find(lab) if len(lab) >= 8 else -1
        while pos != -1:
            end = pos + len(lab)
            before_ok = pos == 0 or not (s[pos - 1].isalnum() or s[pos - 1] == "_")
            if before_ok and s[end:end + 1] == " ":
                tok = _first_token(s, end).rstrip(_TAIL_PUNCT)
                if len(tok) >= 4 and _is_value_token(tok):
                    return True
            pos = s.find(lab, pos + 1)
    return False


def _same_line(s, labels=None):
    """Is there 'label, separator, value' on this line? The label is the last word(s) before the separator."""
    for m in (_SEP if labels is None else _SEP_X).finditer(s):
        j = m.start()
        while j > 0 and s[j - 1] == " ":
            j -= 1
        if _label_ends_at(s, j, labels) and _is_value_token(_first_token(s, m.end())):
            return True
    return labels is not None and _bare_label_value(s, labels)


def _ends_with_label(s, labels=None):
    """Does the line end with a hard label (and perhaps a separator): the value, if any, is on the next line?"""
    t = s.rstrip(" :=>-–—|" if labels is not None else " :=>-–—")
    if t.endswith(" is"):
        t = t[:-3].rstrip(" :=>-–—")
    return _label_ends_at(t, len(t), labels)


def drop_labelled_values(lines, labels=None):
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
        if _same_line(s, labels):
            alive[i] = 0
        elif stack and stack[-1][1] and _is_value_token(_first_token(s)):
            alive[stack.pop()[0]] = 0
            alive[i] = 0
        else:
            stack.append((i, _ends_with_label(s, labels)))
    return [i for i in range(n) if alive[i]]


# ---------------------------------------------------------------- the public functions

def keep_indices(lines, *, second_layer=True, extras=False):
    """The ascending indices of the kept input lines: the anchor layer and shape gate, then (second_layer) the label layer."""
    lines = list(lines)
    keep = _anchor_layer(lines, None, extras)
    if second_layer:
        keep = [keep[j] for j in drop_labelled_values([lines[i] for i in keep])]
    return keep


def keep_lines(lines, *, second_layer=True, extras=False):
    """The kept lines: a subsequence of the input, byte for byte (never edited, never new)."""
    lines = list(lines)
    return [lines[i] for i in keep_indices(lines, second_layer=second_layer, extras=extras)]


def _cut(text):
    """Cut a body to BODY_MAX characters at a line end (a half line is dropped, so the output stays a subset)."""
    if len(text) <= BODY_MAX:
        return text
    if text[BODY_MAX] == "\n":
        return text[:BODY_MAX]
    head = text[:BODY_MAX]
    k = head.rfind("\n")
    return head[:k] if k >= 0 else ""


def _fit(lines):
    """THE LONG-LINE RULE: a line longer than CAP can never fit in the cap, so it is dropped whole (fail-closed; never cut, never
    truncated at a space, which would break the subset property). Done before the label layers, so the scrub never judges a fragment."""
    return [ln for ln in lines if len(ln) <= CAP]


def _capped(lines):
    """Whole lines in order while the joined text (with newlines) stays within CAP; the first line that would cross ends it.
    A line over CAP is dropped first (_fit); the output never ends in a blank line, so filtering it again changes nothing."""
    lines = _fit(lines)
    out, total = [], 0
    for ln in lines:
        add = len(ln) + (1 if out else 0)
        if total + add > CAP:
            break
        out.append(ln)
        total += add
    while out and not out[-1].strip():
        out.pop()
    return out


def _blocks_module():
    """invite_blocks, imported on first use; None when it cannot be had (then HTML is not converted)."""
    try:
        import invite_blocks
        return invite_blocks
    except ImportError:
        return None


def blocks_from_html(html_or_text):
    """The plan's name for invite_blocks.blocks: the text as blocks (lists of consecutive non-blank lines)."""
    mod = _blocks_module()
    return mod.blocks(html_or_text) if mod else []


def filter_text(text, *, second_layer=True, html=None):
    """The body filter for stored text: BODY_MAX cut, split on newline, keep_lines, join, then the CAP (whole lines only).

    html=None (auto): text with real tags (invite_blocks.looks_like_html) goes through invite_blocks.to_lines; True: forced; False: never.
    Plain text is split on newline after CRLF and CR become newline (not with html=False). The output is a subsequence of those lines.
    If invite_blocks is missing, HTML is not served (""), never the raw markup."""
    if html is None or html:
        mod = _blocks_module()
        if mod is None:
            if html:
                return ""
        elif html or mod.looks_like_html(text):
            lines = mod.to_lines(text)
            kept = keep_lines(_fit(_cut("\n".join(lines)).split("\n")), second_layer=second_layer)
            return "\n".join(_capped(kept))
    if html is not False:
        text = text.replace("\r\n", "\n").replace("\r", "\n")  # a CR must not hide a line from the rules
    return "\n".join(_capped(keep_lines(_fit(_cut(text).split("\n")), second_layer=second_layer)))


# ---------------------------------------------------------------- option (c): the 2.6.8 scrub as the body label layer (2.6.9)

def _scrub_module():
    """invite_clean, imported on first use; None when it cannot be had (then the label layer is skipped)."""
    try:
        import invite_clean
        return invite_clean
    except ImportError:
        return None


def _scrub_pairs(lines):
    """THE ONE NARROW WRAPPER around the 2.6.8 body scrub (re-point this function when invite_clean's body entry point changes).

    lines -> [(index, text)]: the scrub's output lines, each mapped back to the input line it came from. invite_clean.invite_text
    rewrites (tags, spaces, "pass code" -> "passcode") and drops lines, so every output line is matched, in order, to the next input
    line that equals it after the same normalisation; index is that input line (the caller emits the ORIGINAL, byte for byte). An output
    line no input line matches gets index None and is emitted as the scrub wrote it (the subset property then holds only up to that
    line's normalisation; the tests count these, expected zero on converted lines). Blank lines are kept as ""."""
    mod = _scrub_module()
    lines = list(lines)
    if mod is None:
        return [(i, x) for i, x in enumerate(lines)]
    keys = [_scrub_key(mod, x) for x in lines]
    res, j = [], 0
    for o in mod.invite_text("\n".join(lines)).split("\n"):
        if not o.strip():
            if res and res[-1][1] != "":
                res.append((None, ""))
            continue
        ko = _scrub_key(mod, o)
        k = j
        while k < len(lines) and keys[k] != ko:
            k += 1
        if k < len(lines):
            res.append((k, lines[k]))
            j = k + 1
        else:
            res.append((None, o))
    while res and res[-1][1] == "":
        res.pop()
    return res


def _scrub_lines(lines):
    """The scrub's kept lines (see _scrub_pairs)."""
    return [t for _, t in _scrub_pairs(lines)]


def _tidy_blanks(lines):
    """No leading blank line, no two blank lines in a row, no trailing blank line (the anchor layer can empty a block between blanks).
    Only drops blank lines, so the result is still a subsequence of its input;
    the scrub does the same, which keeps both orders idempotent."""
    out = []
    for ln in lines:
        if ln.strip() or (out and out[-1].strip()):
            out.append(ln)
    while out and not out[-1].strip():
        out.pop()
    return out


ORDERS = ("scrub_first", "anchors_first", "scrub_raw_first")
# the scrub on the raw body first: 304 leak bodies of 40,000, 4 digit-bearing items, the scrub's own numbers (no E1 order is as low
# on digit-bearing leaks); see dev/proposals/375/PLAN.md section 1d
DEFAULT_ORDER = "scrub_raw_first"


def _label_layer(lines, order=None):
    """The body label layer in one of two orders (both return a subsequence of the input lines, up to the scrub's own blank lines).

    anchors_first: anchor layer and shape gate, then the scrub on the surviving lines (section 1c).
    scrub_first: the scrub on the original converted lines, then the anchor layer and shape gate on what it kept. A label's value is
    still there when the scrub's window runs, so the window cannot eat an innocent neighbour, and a qualified label ("PIN to follow")
    is judged with its value present. See PLAN.md sections 1b and 1c."""
    order = order or DEFAULT_ORDER
    lines = _fit(lines)
    if order == "anchors_first":
        return _tidy_blanks(_scrub_lines(keep_lines(list(lines), second_layer=False)))
    if order == "scrub_first":
        return _tidy_blanks(keep_lines(_scrub_lines(list(lines)), second_layer=False))
    raise ValueError("order must be one of %r" % (ORDERS,))


def _scrub_key(mod, line):
    """A line as the scrub would have left it if it kept it: markup stripped, spaces collapsed, 'pass code' joined."""
    t = re.sub(r"(?i)\b(pass)\s+(code|word|phrase)", r"\1\2", mod.plain_text(line))
    return " ".join(t.split())


def _original_lines(raw):
    """The body's lines before the scrub: invite_blocks' lines for HTML, the text split on newline otherwise (cut as the scrub's output)."""
    mod = _blocks_module()
    if mod is not None and mod.looks_like_html(raw):
        orig = mod.to_lines(raw)
    else:
        orig = raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return _cut("\n".join(orig)).split("\n")


_USE_BOUNDARIES = True      # test hook


def _boundary_kinds(orig):
    """Per original line: 0 text, 1 blank, 2 divider."""
    out = []
    for x in orig:
        s = _skeleton(x)
        out.append(1 if not s else (2 if _is_divider(s) else 0))
    return out


def _boundary_mark(boundary, prev, k, res):
    """The placeholder to put between two matched lines (original indices prev and k): a divider, a blank line, or None."""
    if prev is None or k <= prev + 1 or not res:
        return None
    seen = set(boundary[prev + 1:k])
    if 2 in seen:
        return "____"
    return "" if (1 in seen and res[-1].strip()) else None


def _with_boundaries(raw, out_lines):
    """2.6.9 item 7: the scrub drops dividers and the <p>/<hr>/row boundaries when it turns HTML into text, so a join block and the
    agenda beside it read as ONE block and the anchor layer dropped both. Each scrub line is matched (in order) to the original line
    it came from; where the original had a divider between two matched lines a divider placeholder is put between them, where it had
    a blank line a blank placeholder. Returns (lines, flags): flags[i] is true for a placeholder, which the caller removes again after
    the anchor layer has judged the blocks. An unmatched line adds nothing around it (the old behaviour)."""
    flags = [False] * len(out_lines)
    mod = _scrub_module()
    orig = _original_lines(raw) if (_USE_BOUNDARIES and mod is not None and out_lines) else []
    if len(orig) < 2:
        return list(out_lines), flags
    where = {}
    for k, x in enumerate(orig):
        where.setdefault(_scrub_key(mod, x), []).append(k)
    boundary = _boundary_kinds(orig)
    res, fl = [], []
    prev, j = None, 0
    for o in out_lines:
        cand = where.get(_scrub_key(mod, o), ()) if o.strip() else ()
        pos = bisect.bisect_left(cand, j)
        if pos < len(cand):
            k = cand[pos]
            mark = _boundary_mark(boundary, prev, k, res)
            if mark is not None:
                res.append(mark); fl.append(True)
            prev, j = k, k + 1
        elif o.strip():
            prev = None                # an unmatched line: nothing is known about what lay between its neighbours
        res.append(o); fl.append(False)
    return res, fl


def _kept_origins(mod, orig, kept):
    """For each kept line, in order, the index of the original line it came from (None when none matches)."""
    where = {}
    for k, x in enumerate(orig):
        where.setdefault(_scrub_key(mod, x), []).append(k)
    pos, j = [], 0
    for x in kept:
        cand = where.get(_scrub_key(mod, x), ()) if x.strip() else ()
        p = bisect.bisect_left(cand, j)
        pos.append(cand[p] if p < len(cand) else None)
        if p < len(cand):
            j = cand[p] + 1
    return pos


def _take_orphans(skels, kinds, at, st, k):
    """At original line k (kept, text), how many lines (0, 1 or 2) form a value-only group that goes."""
    if k + 1 < len(kinds) and kinds[k + 1] == _TEXT and k + 1 in at and _orphan_lines([skels[k], skels[k + 1]], st.label is not None):
        return 2
    return 1 if _orphan_lines([skels[k]], st.label is not None) else 0


def _without_orphans(raw, kept):
    """2.6.9 HIGH 1 for the raw-first order: the scrub has already removed the join block, so the anchor layer on its output cannot see
    that a block was dropped. Each kept line is matched, in order, to the ORIGINAL line it came from; an original line that did not
    survive is a removed line (the scrub's or the anchor layer's). A value-only group (see _orphan_lines: 1 to 2 consecutive lines, value
    tokens only) that stands next to a removed line (blank lines and one divider between allowed, a bare label line passed over, which
    goes with its value) goes too, up to two groups in a row."""
    mod = _scrub_module()
    orig = _original_lines(raw)
    if mod is None or not orig:
        return kept
    at = {o: i for i, o in enumerate(_kept_origins(mod, orig, kept)) if o is not None}
    skels = [_skeleton(x) for x in orig]
    kinds = [_BLANK if not s else (_DIVIDER if _is_divider(s) else _TEXT) for s in skels]
    drop, st, k = set(), _Chain(), 0
    while k < len(orig):
        step = 1
        if kinds[k] == _DIVIDER:
            st.divider()
        elif kinds[k] == _TEXT:
            st.divs = 0
            if k not in at:                      # a line that did not survive
                st.reset()
                st.armed = True
            elif st.open() and _label_only(skels[k]):
                st.label = k                     # a bare label: the value after it goes with it, and may be a year
            else:
                step = _take_group(skels, kinds, at, st, k, drop)
        k += step
    return [x for i, x in enumerate(kept) if i not in drop]


def _take_group(skels, kinds, at, st, k, drop):
    """A kept text line k: take the value-only group starting here when the chain is open. Returns how many original lines were consumed."""
    n = _take_orphans(skels, kinds, at, st, k) if st.open() else 0
    if not n:
        st.reset()
        return 1
    drop.update(at[k + t] for t in range(n))
    if st.label is not None:
        drop.add(at[st.label])
    st.taken += 1
    st.label = None
    return n


def _line_breaks(text):
    """E1 pass 2, finding 8: CR, VT, FF, NEL, U+2028 and U+2029 are line breaks (invite_blocks.NEWLINES, which the HTML path already
    uses), so a plain-text body that uses them is split into lines before the scrub. The properties of D (idempotence, every output line a
    line of the body) are stated against the body as normalised here."""
    mod = _blocks_module()
    for nl in (mod.NEWLINES if mod is not None else ("\r\n", "\r", "\x0b", "\x0c", "\x85", "\u2028", "\u2029")):
        text = text.replace(nl, "\n")
    return text


_BREAKS = ("\x0b", "\x0c", "\x85", "\u2028", "\u2029")


def _own_value_drop(scrub, piece):
    """A piece that drops on its own AND carries its own value ('Passcode: 8825'). A bare label ('Passcode:', 'Meeting ID') drops alone
    too, but its value is in a sibling piece, so it explains nothing (Cap re-check 2, HIGH 1). Known gap, stated: a word-only value after
    a break ('Passcode: 8825<NEL>zejumud') keeps the word."""
    return not scrub.invite_text(piece).strip() and not _ends_with_label(_skeleton(piece)) and not _label_only(piece)


def _original_pieces(text, scrub):
    """Cap review of group C: the scrub also runs on the plain-text body AS WRITTEN, where a break inside a label's window keeps the
    label and the line after it together ('Zoom passcode:' / 'Decisions <NEL>log' / 'mupiwoc'). Returns a Counter of the keys of the
    pieces to drop from the normalised pass: the pieces of a line (or a line) that the original pass dropped when none of its
    pieces drops on its own (a piece that does, 'Passcode: 8825', explains the original drop and the rest stays).
    None when the body has no extra break or is HTML."""
    mod = _blocks_module()
    if not any(b in text for b in _BREAKS) or (mod is not None and mod.looks_like_html(text)):
        return None
    mod = _scrub_module()
    kept_o = collections.Counter(_scrub_key(mod, o) for o in _cut(scrub.invite_text(text)).split("\n") if o.strip())
    drop = collections.Counter()
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if not line.strip():
            continue
        if kept_o[_scrub_key(mod, line)] > 0:
            kept_o[_scrub_key(mod, line)] -= 1
            continue
        pieces = [x for x in _line_breaks(line).split("\n") if x.strip()]
        if not any(_own_value_drop(scrub, x) for x in pieces):       # no piece drops on its own VALUE: the original drop was the window's
            drop.update(_scrub_key(mod, x) for x in pieces)
    return drop


def _union_drops(lines, pieces):
    """Drop, from the normalised pass, the lines _original_pieces names."""
    if not pieces:
        return lines
    mod, out = _scrub_module(), []
    for x in lines:
        if x.strip():
            k = _scrub_key(mod, x)
            if pieces[k] > 0:
                pieces[k] -= 1
                continue
        out.append(x)
    return out


def _is_html(text):
    mod = _blocks_module()
    return mod is not None and mod.looks_like_html(text)


def _raw_first(text):
    """Composition D: the scrub on the raw body, the block boundaries it removed put back for the anchor layer, the orphan and sentence
    rules, the extended label pass (repeated until nothing changes, so the result is stable), then the CAP."""
    scrub = _scrub_module()
    if scrub is None:
        return ""
    asked = text[:BODY_MAX * 5]
    html = _is_html(asked)
    raw = asked if html else _line_breaks(asked)      # HTML keeps its breaks as written: the scrub and invite_blocks treat them as white space
    scrubbed = [x.strip() for x in _cut(scrub.invite_text(raw)).split("\n")]
    scrubbed = _union_drops(scrubbed, _original_pieces(asked, scrub))
    aug, flags = _with_boundaries(raw, _fit(scrubbed))
    kept = _tidy_blanks([aug[i] for i in keep_indices(aug, second_layer=False, extras=True) if not flags[i]])
    kept = _tidy_blanks(_without_orphans(raw, kept))
    for _ in range(4):
        before = kept
        if _USE_EXT_LABELS:
            kept = _tidy_blanks(_ext_labelled(kept))
        kept = _tidy_blanks(keep_lines(kept, second_layer=False, extras=True))
        if kept == before:
            break
    return "\n".join(_capped(kept))


def filter_text_with_scrub(text, html=None, order=None):
    """Option (c), the 2.6.9 body filter: html/blocks conversion, the anchor layer and shape gate (second_layer=False), then the
    2.6.8 scrub (via _scrub_pairs) as the label layer on the surviving lines, then the CAP.
    Same conversion rules as filter_text. order: see _label_layer (default DEFAULT_ORDER).
    order="scrub_raw_first" (D): the scrub runs on the RAW body (it reads the HTML itself), then the anchor layer, shape gate and CAP
    on the lines it kept. Its lines are the scrub's, not invite_blocks' (so not a subset of the converted lines), but still whole
    lines of the body as the scrub left them."""
    if order is not None and order not in ORDERS:
        raise ValueError("order must be one of %r" % (ORDERS,))
    if (order or DEFAULT_ORDER) == "scrub_raw_first":
        return _raw_first(text)
    mod = _blocks_module()
    if html is None or html:
        if mod is None:
            if html:
                return ""
        elif html or mod.looks_like_html(text):
            lines = mod.to_lines(text)
            kept = _label_layer(_cut("\n".join(lines)).split("\n"), order)
            return "\n".join(_capped(kept))
    if html is not False:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(_capped(_label_layer(_cut(text).split("\n"), order)))
