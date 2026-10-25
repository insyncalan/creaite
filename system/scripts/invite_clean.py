"""#265 review M1, M2: what the saved calendar (system/staging/calendar.json) may keep of a meeting invite. Plain code, no I/O.

creaite's rule: attendees, the invite's body as plain text and attachment names are kept; never a join link, meeting ID, passcode,
PIN or dial-in number; a confidential meeting keeps only its title and times; a private one is "Busy". This module is the one
place that decides, for sweep.py's calendar save:

- sensitivity(ev): "private", "confidential" or "normal". It fails closed: any value but empty, "normal" or "none" is
  confidential (restricted, secret, "Strictly Confidential", 2, True...), after case, spacing, zero-width characters and
  look-alike forms (NFKC) are removed; anything that says private or personal is private; a private flag stays "Busy".
- invite_text(body): HTML to plain text, then every line that carries a join link or a key to the meeting is dropped.
- is_secret(text) / scrub(text): the same test for a single field (title, place, organiser); scrub takes out a complete join
  link and drops the whole field when any other secret is left in it (a passcode, password or numbered label, a bare join host
  or scheme, a dial-in number), as 2.5.3 did; flagged(text) for names.

Text is matched after NFKC and with zero-width characters, combining marks and URL or HTML escapes (twice over) removed, so
full-width "PIN", a zero-width space inside "zoom.us", "%3Fpwd%3D" and "https&#58;//" are caught, and look-alike letters from other
alphabets are read as the Latin ones (confusables.py). A label alone on a line takes the line after it too (a table's "PIN" and
its value in the next cell), and "Pass" and "code" split by tags are joined. Not covered: letters spaced out one by one ("P I N")
are not found as a key, and a link to a provider this module does not know with no word of joining near it.
"""
import functools
import html as htmllib
import re
import unicodedata
from urllib.parse import unquote

import confusables
import paths  # noqa: F401  (every script imports paths: doctor's 'Scripts take locations from paths.py' check)

BODY_MAX = 20000
OPEN, CLOSE = "\ue000", "\ue001"               # a link's address is carried beside its text only to be judged, then removed
_MARK = re.compile(OPEN + ".*?" + CLOSE, re.S)
RAW_MAX, LINE_MAX = 60000, 2000                  # how much of a body or a line is looked at (matching time stays small)

# ---- join links: the providers creaite knows, short-link services, and any URL that carries a key ----
HOSTS = re.compile(
    r"(?<![\w-])(?:teams\.microsoft\.com|teams\.live\.com|teams\.cloud\.microsoft|zoom\.us|zoom\.com|zoomgov\.com|"
    r"zoom\.com\.cn|webex\.com|meet\.google\.com|goto\.com|gotomeeting\.com|gotowebinar\.com|gotomeet\.me|bluejeans\.com|"
    r"chime\.aws|amazonchime\.com|whereby\.com|join\.me|meet\.jit\.si|8x8\.vc|ringcentral\.com|skype\.com|gather\.town|"
    r"livestorm\.co|aka\.ms|bit\.ly|tinyurl\.com|t\.co|goo\.gl|ow\.ly|is\.gd|rb\.gy|cutt\.ly|tiny\.cc|lnkd\.in|buff\.ly|"
    r"rebrand\.ly|shorturl\.at|s\.id|v\.gd|t\.ly|bl\.ink)(?![\w-])", re.I)
SCHEME = re.compile(r"(?<![\w-])(?:tel|sip|sips|callto|msteams|zoommtg|zoomus|webex|webexteams|skype|facetime|gotomeeting):", re.I)
URL = re.compile(r"(?:\b[a-z][a-z0-9+.-]{1,12}://|\bwww\.)\S+|\b(?:[a-z0-9-]{1,63}\.){1,8}[a-z]{2,24}(?::\d+)?/\S*", re.I)
KEYED = re.compile(r"[?&;#/](?:pwd|passcode|passwd|pass|password|pin|tk|token|key|secret|sig|signature|auth|code|access_token|otp|"
                   r"mtid|meetingid|meetingnumber|conferenceid|confid|jid)=", re.I)
JOINPATH = re.compile(r"/(?:j|join|joinme|meet|meeting|meetings|webinar|conference|room|rooms|call|invite|video)(?:[/?#]|$)|/\d{9,}",
                      re.I)
JOINWORD = re.compile(r"\b(?:join|dial|webinar|conference|video\s*call|video\s*meeting|meeting\s*link|online\s*meeting|"
                      r"click\s+(?:here\s+)?to)\b", re.I)

# ---- keys: passcodes, PINs, meeting IDs, dial-in numbers ----
# ONE separator class for every label path (a label alone, a bare label, a phrase that stops): any punctuation or symbol (Unicode
# P* and S*, and the rest of what is neither a letter, a digit nor a space) except a sentence end (. , ; ! ?).
BARE_SEPARATORS = r"[^\w\s.,;!?]"
# A separator, with at most ONE sentence-end mark in front of it ("Password.:", "Passcode?:"). Longer runs of marks are first read as one
# ellipsis (a separator itself): _views() does that before any pattern is tried (_SE_RUN), so no pattern needs a repeated group
# round a repeated mark, and none can backtrack catastrophically (2.6.8 review: ". " x 60 froze the old nested form).
# Sentence-end marks alone are NOT a separator ("Password! hunter" is two sentences; a documented trade-off).
SEPRUN = rf"[.,;!?]?{BARE_SEPARATORS}"
_SE_RUN = re.compile(r"[.,;!?](?:\s*[.,;!?])+")                                    # two or more marks, spaces between: one ellipsis
# a label followed by a value: a separator, "is", a word with a digit, or (v2.6 review) a word that switches from a small
# letter to a capital ("Password kqZxyw", "Key kqZxyw"; case-sensitive, so "Password reset" and "Key Dates" stay)
_VAL = rf"(?:\s*(?:{SEPRUN}\s*\S|\b(?:is|are)\b\s*\S)|\s+(?:no\.?\s*)?\S*\d|\s+(?-i:\S*[a-z]\S*[A-Z]))"
_EVERYWHERE = (r"pass[\s-]*codes?|pass[\s-]*phrases?|pass[\s-]*keys?|pwd|passwd|kenn\s*codes?|zugangs\s*codes?|einwahl\s*codes?|"
               r"teilnehmer\s*codes?|code\s+secret|code\s+d.acc[e\u00e8]s|toegangs\s*codes?|vergader\s*codes?|pin\s*codes?|"
               r"c[o\u00f3]digo\s+(?:de\s+(?:acceso|acesso|reuni[o\u00f3]n)|da\s+reuni[a\u00e3]o)|"
               r"codice\s+(?:di\s+(?:accesso|partecipazione)|riunione)|password\s+(?:della\s+)?riunione|"
               r"one[- ]time[\s-]*(?:pass)?codes?|conference\s+bridge|"
               r"(?:host|moderator|presenter|security|entry|access|meeting|participant|attendee|guest)[\s-]*keys?|"
               r"(?:access|participant|conference|attendee|host|meeting|moderator|presenter|guest|security|entry|"
               r"dial[- ]?in|audio|phone|call[- ]?in|room|webinar|panell?ist|leader)[\s-]*(?:code|pin)s?")
_WITH_VALUE = (r"pass\s*words?|passwort|kennwort|mot\s+de\s+passe|mot-de-passe|contrase[n\u00f1]a|contrasena|senha|wachtwoord|"
               r"clave\s+de\s+acceso|pw|pswd|pin(?:\s*(?:code|number|no\.?))?|toplant[\u0131i]\s+kimli[\u011fg]i|"
               r"(?:meeting|webinar|event|session|conference|call|phone\s+conference|zoom|room|mtg|teams|webex)[\s-]*(?:id|number|no\.?)|"
               r"(?:meeting|zoom|room|mtg)\s*#|join(?:ing)?\s+(?:with\s+)?id")
_BARE = r"secret|codes?|keys?|tokens?|otp|access|codice|c[o\u00f3]digo|[s\u015f]ifre|parola"       # a value must follow these
# v2.6.8 (k26-b-bare, Full review x2): after these labels the next word IS the value even with no digit and no capital ("Password
# swordfish", "PIN rtyu", a table's "PIN" then "kqzxyw", "Code alphabeta", "Token abcd"). Fail closed, and as a whole phrase: every
# word after the label, to the end of the field, must be an allow-listed word for that label (BARE_NEXT, each the second word of a
# common phrase) or a word of BARE_FOLLOW (small function and topic words). The first word that is neither is a value and the field
# goes; so do a colon, equals, dash or bracket after the label or after any such word, and punctuation before the value
# ("Password , hunter"). "Password reset", "Password reset request", "Code of conduct" stay; "Password reset for hunter",
# "Password reset for new hires", "PIN entry: swordfish", "Code of the swordfish" go. Tests: dev/tests/test_invite_clean_bare.py.
BARE_NEXT = (
    (r"pass\s*words?|passwort|kennwort|mot\s+de\s+passe|mot-de-passe|contrase[n\u00f1]a|contrasena|senha|wachtwoord|pw|pswd",
     ("reset", "policy", "manager", "management", "expiry", "rotation", "audit", "change")),
    (r"pin(?:\s*(?:code|number|no\.?))?", ("entry", "pad")),                 # "PIN entry", "PIN pad"
    (r"codes?",                                                               # "Code review", "Code of conduct", "Source code repository"
     ("review", "reviews", "of", "base", "freeze", "quality", "repository", "handover", "walkthrough", "standards")),
    (r"tokens?", ("expiry", "rotation", "refresh", "economy", "economics", "ring")),   # "Token refresh", "Token Ring"
    (r"secrets?", ("management", "manager", "rotation", "santa")),            # "Secret santa", "Secrets management"
    (r"otp", ("setup", "rollout", "enrolment")),
    (r"api\s+keys?", ("rotation", "management", "review")),
)
BARE_FOLLOW = ("for", "of", "and", "the", "to", "with", "in", "on", "at", "a", "an", "or", "request", "requests", "process", "plan",
               "planning", "workshop", "session", "review", "rollout", "update", "changes", "findings", "redesign", "supplier", "call",
               "move", "conduct", "sync", "retrospective", "sow", "training", "staff")


# a phrase that ends on one of these has its value on the next line
BARE_FUNCTION = ("for", "of", "and", "the", "to", "with", "in", "on", "at", "a", "an", "or")





def bare_words(ok):
    """The words that may stand after the first allowed word of a label: its own and BARE_FOLLOW, each ONCE and in order. A word in
    both lists would match two ways in the repeated group below, and the match time would double with every repeat ("Code of of of
    ..." took seconds); dev/tests/test_invite_clean_bare.py checks that the built list has no duplicate."""
    return tuple(dict.fromkeys((*ok, *BARE_FOLLOW)))


def _bare_next(lab, ok):
    okx = "|".join(dict.fromkeys(ok))
    words = "|".join(bare_words(ok))                                            # what may stand after the first allowed word
    run = rf"(?:\s+(?:{words})(?![\w-]))*"
    bad = (rf"(?:\s*{SEPRUN}|\s*[,;.!?]+\s*[\w\"'(\[]|\s+(?!(?:{words})(?![\w-]))[\w\"'(\[])")
    sep = SEPRUN                                                                 # straight after the label too
    return (rf"(?:{lab})(?![\w-])(?:\s*(?:[,;.]+|(?:{sep})+)\s*\w"
            rf"|\s+[\"'(\[]?(?:(?!(?:{okx})(?![\w-]))\w|(?:{okx})(?![\w-]){run}{bad}))")


_BARE_NEXT = "|".join(_bare_next(lab, ok) for lab, ok in BARE_NEXT)
_BARE_LABELS = "|".join(lab for lab, _ok in BARE_NEXT)
BARE_LISTED = frozenset(w for _l, ok in BARE_NEXT for w in ok) | frozenset(BARE_FOLLOW)       # every word a label-free phrase may use
_BARE_RUN = rf"(?<![\w-])(?:{_BARE_LABELS})(?![\w-])(?:\s+(?:{'|'.join(sorted(BARE_LISTED))})(?![\w-]))*"
_BARE_OPEN = re.compile(                                  # a label phrase that stops on a function word or a separator: its value is next
    rf"{_BARE_RUN}(?:\s+(?:{'|'.join(BARE_FUNCTION)})|\s*(?:{SEPRUN})+)\s*[.,;]*\s*$", re.I)
_BARE_END = re.compile(rf"{_BARE_RUN}\s*[.,;!?]*\s*$", re.I)           # a finished label phrase ("Password reset"): the next line is judged


_SPACED = re.compile(r"(?<![\w])p[ .\-]{1,2}i[ .\-]{1,2}n\.?(?![\w])", re.I)       # "P I N", "P.I.N.", "P-I-N" read as PIN
_OTHER_ALPHABETS = ("رمز المرور|كلمة المرور|كلمة السر|رمز الدخول|رمز الوصول|رمز الاجتماع|رمز الانضمام|الرقم السري|"
                    "رقم التعريف الشخصي|密码|密碼|口令|访问码|パスコード|パスワード|暗証番号|会議\\s*id|会議番号|ミーティング\\s*id|"
                    "비밀번호|회의\\s*암호|회의\\s*id|암호|пароль|код\\s+доступа|код\\s+конференции|"
                    "идентификатор\\s+(?:конференции|встречи)|пин-код")
LABEL = re.compile(rf"(?<![\w-])(?:{_EVERYWHERE})(?![\w-])|(?<![\w-])(?:{_BARE_NEXT})|(?<![\w-])(?:{_WITH_VALUE}|{_BARE})(?![\w-]){_VAL}"
                   rf"|(?<![\w-])(?:{_EVERYWHERE}|{_WITH_VALUE}|{_BARE}|{_BARE_LABELS})(?![\w-])\s*[.,;!?\u2026]+\s*\S*\d"   # "Code! 4417"
                   rf"|(?<![\w-])meeting\s*[:=]\s*\d[\d ]{{5,}}|(?<![\w-])id\s+(?:is|are)\s+\S*\d"     # "Meeting: 987 654 321"
                   rf"|(?<![\w-])id\s*[:#=]\s*\d|(?:{_OTHER_ALPHABETS})", re.I)
_ALONE_ITEM = rf"(?:\s*{SEPRUN}|\s*_|\s+(?:is|are)(?![\w-]))"                                  # a separator, "is" or "are"
_ALONE_TAIL = rf"{_ALONE_ITEM}{_ALONE_ITEM}*(?:\s*[.,;!?])?"               # one sentence-end mark may close it, after a separator
LABEL_ALONE = re.compile(rf"(?:(?<![\w-])(?:{_EVERYWHERE}|{_WITH_VALUE})(?![\w-])|(?:{_OTHER_ALPHABETS}))(?:{_ALONE_TAIL})?\s*$"
                         rf"|(?<![\w-])(?:{_BARE}|{_BARE_LABELS})(?![\w-]){_ALONE_TAIL}\s*$", re.I)     # "Key:", "Code is": needs one
_PH = r"\+?\(?\d[\d ()./-]{6,40}\d"
DIAL = re.compile(r"(?<!\d)\d{3,}\s*#(?!\w)|,,\s*\d|\d\s*,,"
                  r"|(?<![\w-])(?:dial[- ]?in|dial|toll[- ]?free|call[- ]?in|conference\s+call)(?![\w-])"
                  r"[^\n]{0,60}\+?\(?\d[\d ()./-]{6,40}"
                  rf"|(?<![\w-])(?:tel|telefon|phone|fon|ph|mobile|call)\.?\s*[:.]?\s*{_PH}"
                  r"|(?<!\d)\d[\d ()./-]{5,40}\d\s*(?:ext\.?|extension|x|pause|;)\s*\d{3,}"
                  r"|(?<![\w/])\+\d{1,3}[ .-]?\(?\d[\d ()./-]{6,40}\d", re.I)
# BL-98: the Teams and Outlook joining boilerplate, one line at a time (the lines the keys above do not already catch)
JOIN_LINE = re.compile(
    r"(microsoft teams (meeting|need help)|join (the meeting|on your computer|with a video conferencing|by phone|"
    r"conference)|click (here )?to join|phone conference id|find a local number|"
    r"reset dial[- ]in pin|conference id|for organi[sz]ers: meeting options|learn more( about teams)?\s*(\||$)|meeting options|"
    r"^\s*\+\d[\d ,#()-]{7,}|^\s*_{8,}\s*$|^\s*\.{3,}\s*$|system reference|"
    r"this meeting is being recorded|join microsoft teams meeting)", re.I)


MAX_EXPANSION = 4          # no character may stand for more than this many after NFKC / NFKD: a text is at most 4 times as long


@functools.lru_cache(maxsize=None)
def _unit(c):
    """The character itself, or a space when its NFKC or NFKD form is longer than MAX_EXPANSION characters (a ligature such as the 18
    letters of U+FDFA, a fraction, a unit sign). Such a character is never a label letter and a label cannot hide inside one, so
    nothing is lost; without this a hostile invite of 40,000 of them made every read take seconds. The most any label letter
    expands to is 3 (a ligature "ffi", a Hangul syllable); test_invite_clean_expansion.py checks it for every label."""
    if len(unicodedata.normalize("NFKC", c)) > MAX_EXPANSION or len(unicodedata.normalize("NFKD", c)) > MAX_EXPANSION:
        return " "
    return c


def _bounded(text):
    """The text with every character that would expand too far replaced by a space (ASCII is never touched)."""
    return text if text.isascii() else "".join(map(_unit, text))


def normal(text, marks=False):
    """NFKC, with control and private-use characters (but not line breaks) and every format character (zero-width, bidi, soft
    hyphen) removed; `marks` keeps the two link markers. A character that would expand to more than MAX_EXPANSION is a space."""
    t = unicodedata.normalize("NFKC", _bounded(str(text if text is not None else "")))
    return "".join(c for c in t if c in "\n\r\t" or (marks and c in (OPEN, CLOSE))
                   or unicodedata.category(c) not in ("Cf", "Cc", "Co"))


_KEEP_MARKS = ("\u3099", "\u309a")                    # kana voicing marks belong to the letter (パスコード): they are kept


def skeleton(text):
    """What a test matches on: NFKD with every combining mark removed (an accent on a label letter must not hide the label: "Pásscode",
    "Piń", "Passwörd"; NFKC would COMPOSE e + U+0301 first, leaving nothing to strip), recomposed (Hangul, kana), Arabic tatweel removed,
    escapes and URL encoding decoded. Only a copy used for matching: the text that is kept is never changed by this."""
    d = unicodedata.normalize("NFKD", _bounded(normal(text)))
    kept = (c for c in d if (unicodedata.category(c) not in ("Mn", "Me") or c in _KEEP_MARKS) and c != "ـ")
    t = unicodedata.normalize("NFC", "".join(kept))
    for _ in range(3):
        u = unquote(htmllib.unescape(t))
        if u == t:
            break
        t = u
    return t


def _bad_url(url):
    """Whether a URL (already decoded) is a join link: a known provider, a short link, a key in it, or a join-shaped path."""
    return bool(HOSTS.search(url) or KEYED.search(url) or JOINPATH.search(url))


def _ellipsis(m):
    """A run of sentence-end marks read as one ellipsis, except a run of commas alone (a dial-in pause: ",,")."""
    return m.group() if set(m.group().replace(" ", "").replace("\t", "").replace("\n", "")) == {","} else "\u2026"


_MDLINK = re.compile(r"\[([^\[\]]{0,200})\]\([^()\s]{0,500}\)")                  # [Passcode](http://x): the text is the label
_DECORATION = re.compile(r"[_*~`]+")                                          # markdown emphasis and underscores: read as a space


def _views(text):
    """What every test matches on: the skeleton and the same with look-alike letters (a Cyrillic "a") read as the Latin ones, and both
    again with every underscore and markdown wrapper (_ * ~ `) read as a space (2.6.8, #369: `_` is a word character, so "__Passcode:__",
    "_PIN_" and "Meeting_ID" hid their label). Those views come first, so the last view is still the translated original (sensitivity()
    reads it)."""
    s = skeleton(str(text if text is not None else "")[:LINE_MAX + 200])       # every test runs on a bounded text (timing)
    s = _SPACED.sub("PIN", s)
    s = _SE_RUN.sub(_ellipsis, s)
    out = []
    linked = _MDLINK.sub(r" \1 ", s)                       # a markdown link read as its text: [Passcode](http://x) is the label Passcode
    bases = ([linked] if linked != s else []) + [s]
    for base in [_DECORATION.sub(" ", x) for x in bases if _DECORATION.search(x)] + bases:
        out.append(base)
        t = base.translate(confusables.TABLE)
        if t != base:
            out.append(t)
    return out


def _secret_in(s):
    """Whether one view of a text carries a join link, a key or a dial-in number."""
    return bool(HOSTS.search(s) or SCHEME.search(s) or LABEL.search(s) or DIAL.search(s)
                or any(_bad_url(m.group()) for m in URL.finditer(s)))


def is_secret(text):
    """Whether text carries a join link, a key (passcode, PIN, meeting ID) or a dial-in number: for one field of a meeting."""
    return any(_secret_in(s) for s in _views(text))


def _drop_line(line):
    """Whether a body line goes: it is a secret, the joining boilerplate, or a link on a line that talks of joining."""
    return any(_secret_in(s) or bool(JOIN_LINE.search(s) or LABEL_ALONE.search(s)) or bool(URL.search(s) and JOINWORD.search(s))
               for s in _views(line.replace(OPEN, " ").replace(CLOSE, " ")))


def flagged(text):
    """Whether a name (attendee, attachment) is dropped altogether."""
    return is_secret(text) or any(JOIN_LINE.search(s) for s in _views(text))


def scrub(text, limit):
    """A title, place or organiser: a complete join link taken out (a known provider, a short link, a keyed or join-shaped URL:
    "Sync https://zoom.us/j/1?pwd=abc" keeps "Sync"), and then the whole field dropped when anything else is a secret, exactly as
    2.5.3 did: a passcode or password label with or without its value, a numbered label (a meeting ID, PIN, "Code 2"), a bare
    join host or scheme ("zoom.us", "msteams:") or a dial-in number, wherever it stands and whatever is beside it ("Sync Passcode:
    4321", "Weekly sync zoom.us", "Code 2 review" and "Budget (PIN 4321)" all give ""). Nothing is cut out of the text around a
    key: the words beside it may be its value, and no list of password words can be complete (v2.6 review H3, fail closed). Only
    the first LINE_MAX characters are looked at (and a field is kept far shorter)."""
    t = normal(str(text if text is not None else "")[:LINE_MAX])
    t = URL.sub(lambda m: "" if _bad_url(skeleton(m.group())) else m.group(), t)
    t = re.sub(r"\s+", " ", t).strip()
    return "" if is_secret(t) else t[:limit]


_HREF = re.compile(r"""\bhref\s*=\s*(?:"([^"]*)"|'([^']*)'|(\S+))""", re.I)
_BLOCK = re.compile(r"<(script|style|head)\b", re.I)
_ENDS = {k: re.compile(rf"</{k}\b[^<>]{{0,200}}>", re.I) for k in ("script", "style", "head")}


def _anchor(m):
    """<a href=…> as the address beside the link text, so a line can be judged by it (removed again after)."""
    h = _HREF.search(m.group(1))
    href = (h.group(1) or h.group(2) or h.group(3) or "") if h else ""
    return f"{OPEN}{href}{CLOSE}" if href else ""


def _strip_blocks(t):
    """The text without its script, style and head blocks (one pass; a block never closed is left, its tags removed later)."""
    out, i, dead = [], 0, set()
    while True:
        m = _BLOCK.search(t, i)
        if not m:
            break
        tag = m.group(1).lower()
        end = None if tag in dead else _ENDS[tag].search(t, m.end())
        if end is None:
            dead.add(tag)                      # no closing tag anywhere after: never look for it again
            out.append(t[i:m.end()])
            i = m.end()
            continue
        out.append(t[i:m.start()] + " ")
        i = end.end()
    return "".join(out) + t[i:]


def plain_text(body):
    """An invite body as text: HTML removed (inline tags without a gap, so "Pass<b>code</b>" is one word), entities decoded.
    Every pattern here is bounded (no tag is searched past 2000 characters), so a crafted body cannot stall it."""
    t = normal(str(body or "")[:RAW_MAX])
    if re.search(r"<(html|body|div|p|br|span|table|a|td|th|tr|li|ul|ol|h[1-6]|b|i|u|em|strong|font)\b", t, re.I):
        t = _strip_blocks(t)
        t = re.sub(r"(?i)<a\b([^<>]{0,2000})>", _anchor, t)
        t = re.sub(r"(?i)<br\s{0,20}/?>|</(p|div|li|tr|h\d)>", "\n", t)
        t = re.sub(r"(?i)<li\b[^<>]{0,2000}>", "\n- ", t)
        t = re.sub(r"(?i)</?(span|b|i|u|em|strong|font|a|small|big|sup|sub|mark)\b[^<>]{0,2000}>", "", t)
        t = re.sub(r"<[^<>]{1,2000}>", " ", t)
    for _ in range(3):
        u = htmllib.unescape(t)
        if u == t:
            break
        t = u
    return normal(t, marks=True).replace("\r\n", "\n").replace("\r", "\n")


def _pieces(line):
    """A line, or a very long one cut at spaces into pieces of at most LINE_MAX characters (each is judged on its own)."""
    out = []
    while len(line) > LINE_MAX:
        cut = line.rfind(" ", 0, LINE_MAX) + 1 or LINE_MAX
        out.append(line[:cut].strip())
        line = line[cut:]
    return out + [line]


def _lines(t):
    """(line, tail): each line of the text, a very long one in pieces; a piece after the first carries the end of the one before
    it, so a label cut from its value is still seen."""
    for x in t.split("\n"):
        tail = ""
        for piece in _pieces(re.sub(r"[ \t]+", " ", x).strip()):
            yield piece, tail
            tail = piece[-60:] if piece else ""


def _alone(line):
    """Whether a dropped line is a label with no value (its value is on a later line)."""
    return any(LABEL_ALONE.search(s) for s in _views(_MARK.sub(" ", line)))


def _views_of(ln):
    return _views(_MARK.sub(" ", ln))


WINDOW = 3                                  # lines (blank ones do not count) that go after a line that ends a label phrase


def _label_line(ln, dropped):
    """Whether this line ends a bare label phrase whose value may follow: a phrase that stops on a function word or a separator
    (a removed line too), or (a line that is kept) a finished phrase such as "Password reset"."""
    views = _views_of(ln)
    return any(_BARE_OPEN.search(v) for v in views) or (not dropped and any(_BARE_END.search(v) for v in views))


_LABEL_TOKEN = re.compile(rf"(?<![\w-])(?:{_EVERYWHERE}|{_WITH_VALUE})(?![\w-])|(?<![\w-])id(?![\w-])|(?:{_OTHER_ALPHABETS})", re.I)
_KEY_STOP = re.compile(rf"(?<![\w-])(?:{_EVERYWHERE}|{_WITH_VALUE})(?![\w-])\s*[.,;!?\u2026]+\s*$", re.I)


def _label_count(ln):
    """How many labels a line that stands alone holds ("Meeting ID: Passcode:" is two, "ID/Passcode:" two): at least one."""
    return max(1, max(len(_LABEL_TOKEN.findall(v)) for v in _views_of(ln)))


def _ends_on_key_and_stop(ln):
    """Whether a line ends on a join-key label and a sentence end ("Meeting ID."): a number on the next line is its value."""
    return any(_KEY_STOP.search(v) for v in _views_of(ln))


def _pending_after(ln, dropped, pending):
    """The labels standing alone whose value is still to come, after this line."""
    if dropped and _alone(ln):
        return pending + _label_count(ln)      # "Meeting ID: Passcode:" holds two labels: two values follow
    return pending - 1 if pending and not dropped else pending      # a removed line (a link, a line with its own value) is no label's value


def invite_text(body):
    """An invite body as plain text: HTML removed (also a bare table cell or list item), every line with a join link or a key to the
    meeting dropped; the next line with text (any number of blank lines on) after a label that stands alone
    (after k such labels in a row, the next k lines); and after a line that ends a
    bare label phrase ("Password reset", "Password reset for", "Password reset -", also one that was itself removed) the next WINDOW
    lines with text, blank lines skipped and not counted. A label line inside the window starts it again. Blank runs collapsed."""
    t = re.sub(r"(?i)\b(pass)\s+(code|word|phrase)", r"\1\2", plain_text(body))
    kept, window, pending, digit_wait = [], 0, 0, False      # pending: labels standing alone whose value is not seen yet
    for ln, tail in _lines(t):
        if not ln:
            kept.append(ln)                    # a blank line is transparent: any number, for a label alone as for a window
            continue
        dropped = _drop_line(ln) or bool(tail and _drop_line(tail + " " + ln))
        label = _label_line(ln, dropped)
        value = digit_wait and bool(re.search(r"\d", ln))       # "Meeting ID." then "987 654 321": the number is the value
        consumed = pending > 0 or window > 0 or dropped or value
        window = WINDOW if label else (max(window - 1, 0) if consumed else 0)
        pending = _pending_after(ln, dropped, pending)
        digit_wait = _ends_on_key_and_stop(ln)
        if not consumed:
            kept.append(_MARK.sub("", ln))
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()[:BODY_MAX]


def _flag(value):
    """A private flag: a real boolean, or text such as "true"; "false", "0", "no" and "" are off."""
    if isinstance(value, str):
        return normal(value).strip().lower() not in ("", "false", "0", "no", "none", "null", "off")
    return bool(value)


def sensitivity(ev):
    """"private", "confidential" or "normal" for an event. Fails closed: anything but empty, normal or none is confidential."""
    if _flag(ev.get("private")):
        return "private"
    raw = ev.get("sensitivity")
    v = re.sub(r"\s+", " ", _views(raw if raw is not None else "")[-1]).strip().lower()
    if v in ("", "normal", "none"):
        return "confidential" if _flag(ev.get("confidential")) else "normal"
    return "private" if ("private" in v or "personal" in v) else "confidential"


def _clean_names(row):
    """A saved row's attachment and attendee names with any that carry a join link or a key dropped."""
    files = [f for f in (row.get("attachments") or []) if isinstance(f, str) and not flagged(f)]
    people = []
    for a in row.get("attendees") or []:
        if not isinstance(a, dict):
            continue
        name = a.get("name") if isinstance(a.get("name"), str) and not flagged(a["name"]) else str(a.get("email") or "")
        if name and not flagged(name):
            people.append({**a, "name": name[:80]})
    return files, people


def clean_row(row):
    """A meeting already in the saved calendar (written by an earlier version) put through today's cleaning: the sensitivity
    read again (fails closed), the title, place and organiser scrubbed, the body cleaned of join links and keys, and names
    that carry them dropped. A cleaned row cleans to itself."""
    sens = sensitivity({"sensitivity": row.get("sensitivity"), "private": row.get("private")})
    private = sens == "private"
    out = {k: row[k] for k in ("id", "start", "end", "all_day") if k in row}
    out.update(title="Busy" if private else scrub(row.get("title"), 140) or "Meeting", where="", private=private, organiser=False,
               teams=bool(row.get("teams")) and sens != "confidential")
    if sens == "confidential":
        out["sensitivity"] = "confidential"
    elif not private:
        org = row.get("organiser")
        out.update({k: v for k, v in row.items() if k not in out and k not in ("body", "attachments", "attendees")},
                   where=scrub(row.get("where"), 80), sensitivity="normal",
                   organiser=(scrub(org, 80) or False) if isinstance(org, str) else bool(org))
        body = invite_text(row.get("body"))
        files, people = _clean_names(row)
        out.update({k: v for k, v in (("body", body), ("attachments", files), ("attendees", people)) if v})
    return out


def clean_calendar(cal):
    """A saved calendar (calendar.json as loaded) with every meeting put through clean_row, so a reader never sees what an earlier
    version kept (2.6.8). A cleaned row cleans to itself; anything that is not a day of meetings is returned as it is."""
    days = cal.get("days") if isinstance(cal, dict) else None
    if isinstance(days, dict):
        cal = {**cal, "days": {d: ([clean_row(r) if isinstance(r, dict) else r for r in rows] if isinstance(rows, list) else rows)
                              for d, rows in days.items()}}
    return cal
