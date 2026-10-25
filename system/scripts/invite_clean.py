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
                   r"mtid|meetingid|meetingnumber|conferenceid|confid|jid|mpwd|"
                   r"(?:meeting|conf|conference|user|session|room|host|join|webinar)[_-]?(?:pwd|passwd|password|passcode|pin|pass)|"
                   r"[a-z]{0,12}pwd)=", re.I)
JOINPATH = re.compile(r"/(?:j|join|joinme|meet|meeting|meetings|webinar|conference|room|rooms|call|invite|video)(?:[/?#]|$)|/\d{9,}",
                      re.I)
JOINWORD = re.compile(r"\b(?:join|dial|webinar|conference|video\s*call|video\s*meeting|meeting\s*link|online\s*meeting|"
                      r"click\s+(?:here\s+)?to)\b", re.I)

# ---- keys: passcodes, PINs, meeting IDs, dial-in numbers ----
# ONE separator class for every label path (a label alone, a bare label, a phrase that stops): any punctuation or symbol (Unicode
# P* and S*, and the rest of what is neither a letter, a digit nor a space) except a sentence end (. , ; ! ?) and the markdown wrappers
# (* ~ `), which are read as spaces in their own view (_DECORATION): "**Password reset**" is a phrase, not a label and a separator.
BARE_SEPARATORS = r"[^\w\s.,;!?*~`]"
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
               r"teilnehmer\s*codes?|code\s+secret|code\s+d.acc[e\u00e8]s|toegangs\s*codes?|vergader\s*codes?|pins?[\s-]*codes?|"
               r"c[o\u00f3]digo\s+(?:de\s+(?:acceso|acesso|reuni[o\u00f3]n)|da\s+reuni[a\u00e3]o)|"
               r"codice\s+(?:di\s+(?:accesso|partecipazione)|riunione)|password\s+(?:della\s+)?riunione|"
               r"one[- ]time[\s-]*(?:pass)?codes?|conference\s+bridge|"
               r"(?:host|moderator|presenter|security|entry|access|meeting|participant|attendee|guest)[\s-]*keys?|"
               r"(?:access|participant|conference|attendee|host|meeting|moderator|presenter|guest|security|entry|"
               r"dial[- ]?in|audio|phone|call[- ]?in|room|webinar|panell?ist|leader)[\s-]*(?:code|pin)s?")
_WITH_VALUE = (r"pass[\s-]*words?|passwort|kennwort|mot\s+de\s+passe|mot-de-passe|contrase[n\u00f1]a|contrasena|senha|wachtwoord|"
               r"clave\s+de\s+acceso|pw|pswd|pins?(?:[\s-]*(?:codes?|numbers?|no\.?))?|toplant[\u0131i]\s+kimli[\u011fg]i|"
               r"(?:meeting|webinar|event|session|conference|conf|meet|video|goto|gotomeeting|call|phone\s+conference|zoom|room|mtg|teams|"
               r"webex)"
               r"[\s-]*(?:ids?|numbers?|no\.?)(?:\s+(?:number|no\.?))?|"
               r"(?:meeting|webinar|conference|conf|event|session|zoom|room|mtg|meet|video|goto)\s*#|join(?:ing)?\s+(?:with\s+)?id")
_BARE = r"secret|codes?|keys?|tokens?|otp|access|codice|c[o\u00f3]digo|[s\u015f]ifre|parola"       # a value must follow these
# v2.6.8 (k26-b-bare, Full review x2): after these labels the next word IS the value even with no digit and no capital ("Password
# swordfish", "PIN rtyu", a table's "PIN" then "kqzxyw", "Code alphabeta", "Token abcd"). Fail closed, and as a whole phrase: every
# word after the label, to the end of the field, must be an allow-listed word for that label (BARE_NEXT, each the second word of a
# common phrase) or a word of BARE_FOLLOW (small function and topic words). The first word that is neither is a value and the field
# goes; so do a colon, equals, dash or bracket after the label or after any such word, and punctuation before the value
# ("Password , hunter"). "Password reset", "Password reset request", "Code of conduct" stay; "Password reset for hunter",
# "Password reset for new hires", "PIN entry: swordfish", "Code of the swordfish" go. Tests: dev/tests/test_invite_clean_bare.py.
BARE_NEXT = (
    (r"pass[\s-]*words?|passwort|kennwort|mot\s+de\s+passe|mot-de-passe|contrase[n\u00f1]a|contrasena|senha|wachtwoord|pw|pswd",
     ("reset", "policy", "manager", "management", "expiry", "rotation", "audit", "change")),
    (r"pins?(?:[\s-]*(?:codes?|numbers?|no\.?))?", ("entry", "pad")),                 # "PIN entry", "PIN pad"
    (r"codes?",                                                               # "Code review", "Code of conduct", "Source code repository"
     ("review", "reviews", "of", "base", "freeze", "quality", "repository", "handover", "walkthrough", "standards")),
    (r"tokens?", ("expiry", "rotation", "refresh", "economy", "economics", "ring")),   # "Token refresh", "Token Ring"
    (r"secrets?", ("management", "manager", "rotation", "santa")),            # "Secret santa", "Secrets management"
    (r"otp", ("setup", "rollout", "enrolment")),
    (r"api[\s-]*keys?", ("rotation", "management", "review")),
)
BARE_FOLLOW = ("for", "of", "and", "the", "to", "with", "in", "on", "at", "a", "an", "or", "request", "requests", "process", "plan",
               "planning", "workshop", "session", "review", "rollout", "update", "changes", "findings", "redesign", "supplier", "call",
               "move", "conduct", "sync", "retrospective", "sow", "training", "staff")


# a phrase that ends on one of these has its value on the next line
# A dash glued to a label and a word after it: the word is a value unless it is one the lists already know (the allowed second words of
# BARE_NEXT and BARE_FOLLOW) or one of these compound endings: "Password-based", "PIN-protected", "Code-review", "Key-account".
GLUE_OK = "|".join(dict.fromkeys([*(w for _l, ok in BARE_NEXT for w in ok), *BARE_FOLLOW, "based", "protected", "protection", "enabled",
                                  "less", "free", "account", "accounts", "related", "only", "holder", "holders"]))
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
                   rf"|(?<![\w-])(?:{_EVERYWHERE}|{_WITH_VALUE}|{_BARE}|{_BARE_LABELS})"       # "Passcode-4417", "Passcode- 4417"
                   rf"-(?:\s+|(?!(?:{GLUE_OK})(?![\w-])))[^\W_]"
                   rf"|(?<![\w-])meeting\s*[:=]\s*\d[\d ]{{5,}}|(?<![\w-])ids?\s+(?:is|are)\s+\S*\d"     # "Meeting: 987 654 321"
                   rf"|(?<![\w-])ids?(?![\w-])\s*[.,;!?\u2026]*\s*(?:{BARE_SEPARATORS}\s*)?\S*\d\S*\d\S*\d"   # "ID 4417": 3 digits
                   rf"|(?<![\w-])id\s*[:#=]\s*\d|(?:{_OTHER_ALPHABETS})", re.I)
# a footnote mark "(1)", a separator run, "_", "is" or "are"
_ALONE_ITEM = rf"(?:\s*[(\[]\d{{1,3}}[)\]]|\s*{SEPRUN}|\s*_|\s+(?:is|are)(?![\w-]))"
_ALONE_TAIL = rf"{_ALONE_ITEM}{_ALONE_ITEM}*(?:\s*[.,;!?])?"               # one sentence-end mark may close it, after a separator
LABEL_ALONE = re.compile(rf"(?:(?<![\w-])(?:{_EVERYWHERE}|{_WITH_VALUE})(?!\w)|(?:{_OTHER_ALPHABETS}))(?:{_ALONE_TAIL})?\s*$"
                         rf"|(?<![\w-])(?:{_BARE}|{_BARE_LABELS}|ids?)(?!\w){_ALONE_TAIL}\s*$", re.I)     # "Key:", "Code is": needs one
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


_JOINING_DASH = re.compile(r"(?<=\w)(\W)(?=\w)")                          # one non-word character between two word characters
_KEEP_MARKS = ("\u3099", "\u309a")
_INVISIBLE = frozenset("\u3164\u115f\u1160\uffa0\u2800\u17b4\u17b5")                  # fillers that draw nothing


def skeleton(text):
    """What a test matches on: NFKD with every combining mark removed (an accent on a label letter must not hide the label: "Pásscode",
    "Piń", "Passwörd"; NFKC would COMPOSE e + U+0301 first, leaving nothing to strip), recomposed (Hangul, kana), Arabic tatweel removed,
    escapes and URL encoding decoded. Only a copy used for matching: the text that is kept is never changed by this."""
    d = unicodedata.normalize("NFKD", _bounded(normal(text)))
    kept = (c for c in d if (unicodedata.category(c) not in ("Mn", "Me", "Mc") or c in _KEEP_MARKS) and c != "ـ" and c not in _INVISIBLE)
    t = unicodedata.normalize("NFC", "".join(kept))
    t = _JOINING_DASH.sub(lambda m: "-" if unicodedata.category(m.group(1)) == "Pd" else m.group(1), t)       # "Meeting\u2011ID": a hyphen
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


# [Passcode](http://x), [Passcode](u "t"), [Passcode][1], ![Passcode](x), a URL with one level of parentheses: the text is the label
_MDLINK = re.compile(r"!?\[([^\[\]]{0,200})\](?:\((?:[^()\n]|\([^()\n]{0,200}\)){0,500}\)|\[[^\[\]\n]{0,100}\])")
_DOUBLE = re.compile(r"\[\[([^\[\]]{0,200})\]\]")                                  # [[Meeting ID]](url): one pair of brackets
_DECORATION = re.compile(r"[_*~`]+")                                          # markdown emphasis and underscores: read as a space


_CAMEL = re.compile(r"(?<=[a-z])(?=[A-Z])")


def _compounds(text):
    """The text with a provider glued to a label read as two words: a hyphen before a label becomes a space ("Zoom-Passcode"), and a
    lower-case letter followed by a capital is split ("ZoomPasscode", "TeamsPIN"). "" when nothing changed. Only a matching view."""
    out = _CAMEL.sub(" ", _HYPHEN_LABEL.sub(" ", text))
    return out if out != text else ""


def _views(text):
    """What every test matches on: the skeleton and the same with look-alike letters (a Cyrillic "a") read as the Latin ones, and both
    again with every underscore and markdown wrapper (_ * ~ `) read as a space (2.6.8, #369: `_` is a word character, so "__Passcode:__",
    "_PIN_" and "Meeting_ID" hid their label). Those views come first, so the last view is still the translated original (sensitivity()
    reads it)."""
    s = skeleton(str(text if text is not None else "")[:LINE_MAX + 200])       # every test runs on a bounded text (timing)
    s = _SPACED.sub("PIN", s)
    s = _SE_RUN.sub(_ellipsis, s)
    out = []
    linked = _MDLINK.sub(r" \1 ", _DOUBLE.sub(r"[\1]", s))        # a markdown link read as its text
    bases = ([linked] if linked != s else []) + [s]
    split = [c for c in (_compounds(x) for x in bases + [_DECORATION.sub(" ", x) for x in bases]) if c]      # "Zoom-Passcode", "ZoomPIN"
    for base in [_DECORATION.sub(" ", x) for x in bases if _DECORATION.search(x)] + split + bases:
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
    if is_secret(t):
        return ""
    cut = t[:limit].rstrip()                   # a field cut at the limit never ends on a space, and the cut must not make a secret
    return "" if cut != t and is_secret(cut) else cut          # ("Token refresh" cut to "Token r"): a second scrub is the same


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


_TAG_START = re.compile(r"<(html|body|div|p|br|span|table|a|td|th|tr|li|ul|ol|h[1-6]|b|i|u|em|strong|font|wbr|code|o:p)\b|<!--", re.I)
_INLINE = r"span|b|i|u|em|strong|font|a|small|big|sup|sub|mark|wbr|code|kbd|abbr|cite|q|s|del|ins|bdi|bdo|label|o:p|v:\w{1,20}"


_HTML_TAGS = frozenset(
    "html head body title meta link style script div p span table thead tbody tfoot tr td th ul ol li dl dt dd a b i u em strong font "
    "small big sup sub mark br hr img pre blockquote section article header footer nav center code kbd samp var abbr cite q s del ins "
    "label button form input select option textarea o:p wbr bdi bdo h1 h2 h3 h4 h5 h6".split())


def _angle_words(m):
    """"<Passcode>" is not a tag: its words stay; a real tag name goes (and is replaced by a space)."""
    inner = m.group(1)
    return " " if inner.split()[0].lower() in _HTML_TAGS else f" {inner} "


def _strip_tags(t):
    """HTML removed from a text: script, style and head blocks and comments gone, line breaks kept, inline tags without a gap (so
    "Pass<b>code</b>" and "P<wbr>asscode" are one word), any other tag a space. Every pattern is bounded."""
    t = _strip_blocks(t)
    t = re.sub(r"<!--.{0,2000}?-->", "", t, flags=re.S)
    t = re.sub(r"(?i)<a\b([^<>]{0,2000})>", _anchor, t)
    t = re.sub(r"(?i)<br\s{0,20}/?>|</(p|div|li|tr|h\d)>", "\n", t)
    t = re.sub(r"(?i)<li\b[^<>]{0,2000}>", "\n- ", t)
    t = re.sub(rf"(?i)</?(?:{_INLINE})\b[^<>]{{0,2000}}>", "", t)
    t = re.sub(r"<([^<>=/\"'!?]{1,200})>", _angle_words, t)
    return re.sub(r"<[^<>]{1,2000}>", " ", t)


def plain_text(body):
    """An invite body as text: HTML removed (inline tags without a gap, so "Pass<b>code</b>" is one word), entities decoded, and tags that
    were written as entities (&lt;b&gt;) removed too. Every pattern here is bounded (no tag is searched past 2000 characters), so a
    crafted body cannot stall it."""
    t = normal(str(body or "")[:RAW_MAX])
    if _TAG_START.search(t):
        t = _strip_tags(t)
    for _ in range(3):
        u = htmllib.unescape(t)
        if u == t:
            break
        t = u
        if _TAG_START.search(t):
            t = _strip_tags(t)                     # escaped markup: "&lt;b&gt;Passcode&lt;/b&gt;" is the tag it spells
    return normal(t, marks=True).replace("\r\n", "\n").replace("\r", "\n")


def _pieces(line):
    """A line, or a very long one cut into pieces of at most LINE_MAX characters (each is judged on its own): [(piece, glue)], where glue
    is what stood where the line was cut: " " at a space, "" in the middle of a word (so a label cut in two is joined again as it was)."""
    out, glue = [], " "
    while len(line) > LINE_MAX:
        at = line.rfind(" ", 0, LINE_MAX) + 1
        cut = at or LINE_MAX
        out.append((line[:cut].strip(), glue))
        glue = " " if at else ""
        line = line[cut:]
    return out + [(line, glue)]


def _lines(t):
    """(line, tail, glue): each line of the text, a very long one in pieces; a piece after the first carries the end of the one before it
    and the glue to join them with, so a label cut from its value (or cut in two) is still seen."""
    for x in t.split("\n"):
        tail = ""
        for piece, glue in _pieces(re.sub(r"[ \t]+", " ", x).strip()):
            yield piece, tail, glue
            tail = piece[-60:] if piece else ""


def _alone(line):
    """Whether a dropped line is a label with no value (its value is on a later line): a label and a separator, or a header of two or more
    labels ("Meeting ID | Code")."""
    return any(LABEL_ALONE.search(v) or _only_labels(v) for v in _views(_MARK.sub(" ", line)))


_FILLER = re.compile(r"(?:[\W_]|\b(?:and|und|et|is|are|or)\b)+")


def _only_labels(view):
    """Whether a line is nothing but two or more labels and the words and marks between them."""
    found = _LABEL_TOKEN.findall(view)
    return len(found) >= 2 and not _FILLER.sub("", _LABEL_TOKEN.sub(" ", view))


def _views_of(ln):
    return _views(_MARK.sub(" ", ln))


WINDOW = 3                                  # lines (blank ones do not count) that go after a line that ends a label phrase


_PROSE = re.compile(r"[:;,.!?\-\u2013\u2014|()\[\]/]")


def _label_leads(view):
    """Whether a finished label phrase ("Password reset") leads its line: at most three plain words (and a list marker) before it, no
    punctuation. "IT update: password reset" is an agenda item, not a label whose value follows, and opens no window."""
    m = _BARE_END.search(view)
    if not m:
        return False
    before = re.sub(r"^[\s\-*\u2022\d.)(]*", "", view[:m.start()])
    return not _PROSE.search(before) and len(before.split()) <= 3


def _label_kind(ln, dropped):
    """"open" when this line ends a bare label phrase that stops on a function word or a separator (a removed line too): the lines after
    it are its value; "leads" when it is a kept, finished phrase that leads its line ("Password reset"): a value may follow; else ""."""
    views = _views(_DECORATION.sub(" ", _MARK.sub(" ", ln)))          # wrappers read as spaces: "**Password reset**" is the phrase
    if any(_BARE_OPEN.search(v) for v in views):
        return "open"
    return "leads" if not dropped and any(_label_leads(v) for v in views) else ""


_LIST_MARKER = re.compile(r"^\s*(?:\d{1,3}[.)]|[A-Za-z][.)]|[-*\u2022\u2013\u2014\u00b7])\s")


def _looks_like_value(line):
    """Whether a line after a valueless label looks like a value rather than an agenda item: never a numbered or bulleted line; yes for 4 or
    more digits, a token that mixes letters and digits, or a long hex-like string; never a sentence (two words or more, ending in . ! ?);
    else yes for one or two tokens and no for three or more plain words."""
    t = line.strip()
    if _LIST_MARKER.match(re.sub(r"^[\s_*~`>#]+", "", t)):
        return False
    tokens = t.split()
    if sum(c.isdigit() for c in t) >= 4 or any(re.search(r"[^\W\d_]", w) and re.search(r"\d", w) for w in tokens) \
            or any(re.fullmatch(r"[0-9a-fA-F]{8,}", w) for w in tokens):
        return True
    if len(tokens) >= 2 and t[-1:] in ".!?":
        return False
    return len(tokens) <= 2


_HYPHEN_LABEL = re.compile(rf"(?<=\w)[-](?=(?:{_EVERYWHERE}|{_WITH_VALUE}|{_BARE}|{_BARE_LABELS}|ids?)(?!\w))", re.I)
_LABEL_TOKEN = re.compile(rf"(?<![\w-])(?:{_EVERYWHERE}|{_WITH_VALUE}|{_BARE}|{_BARE_LABELS})(?![\w-])|(?<![\w-])ids?(?![\w-])"
                          rf"|(?:{_OTHER_ALPHABETS})", re.I)
_KEY_STOP = re.compile(rf"(?<![\w-])(?:{_EVERYWHERE}|{_WITH_VALUE}|{_BARE}|{_BARE_LABELS}|ids?)(?![\w-])\s*[.,;!?\u2026]+\s*$", re.I)


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


def _is_dropped(ln, tail, glue):
    return bool(ln) and (_drop_line(ln) or bool(tail and _drop_line(tail + glue + ln)))


class _Reader:
    """The state of invite_text: the lines kept so far; the hard window of a label phrase that stops on a function word or a separator
    (the next three lines are its value); the soft window of a finished phrase that leads its line ("Password reset"), which removes only
    the lines among the next three that LOOK like a value; the labels standing alone whose value is still to come; and the "Meeting ID."
    rule that takes the next number. A kept label line whose window removed a line is removed too (a tombstone), so a later pass finds
    no label and removes nothing more; a label line whose window removed nothing stays."""

    def __init__(self):
        self.kept, self.window, self.pending, self.digit_wait, self.anchors = [], 0, 0, False, []
        self.soft = []                             # the open soft windows: [lines left, the kept heading that opened it]

    def feed(self, ln, tail, glue):
        """Take the next line (and the end of the piece before it, with the glue between them)."""
        dropped = _is_dropped(ln, tail, glue)
        if not ln or (not dropped and not re.search(r"[^\W_]", ln)):
            self.kept.append(ln)               # a blank or symbols-only line is transparent: any number, for a label alone as for a window
            return
        value = self._takes_number(ln, dropped)
        reach = self.window > 0 or value                           # a hard window or a value rule reaches this line
        self._tombstone(reach)
        kind = _label_kind(ln, dropped)
        heading = kind == "leads"                  # a heading is not the value of a label standing alone: it opens its own window
        soft = self._soft_step(ln, dropped, reach)
        consumed = (self.pending > 0 and not heading) or reach or dropped or soft
        self._advance(ln, dropped or soft or heading, kind, consumed, reach, value)

    def _takes_number(self, ln, dropped):
        """The "Meeting ID." rule: the next line with a digit is the value (not a removed line, not one a label standing alone takes)."""
        return self.digit_wait and not dropped and not self.pending and bool(re.search(r"\d", ln))

    def _tombstone(self, reach):
        if self.anchors and reach:
            for at in self.anchors:            # a line was removed after these label lines: the labels go too (idempotence)
                self.kept[at] = None
            self.anchors = []

    def _soft_step(self, ln, dropped, reach):
        """The soft windows look at this line: every line counts towards the three of each, except a label line that a later value may
        remove (it would vanish and shift the count). A line a window removes, or any line another rule removes inside it, takes that
        window's heading with it. Returns whether a window itself removed the line (it looks like a value)."""
        if not self.soft:
            return False
        taken = dropped or reach or self.pending > 0
        label = not taken and (bool(_label_kind(ln, False)) or _ends_on_key_and_stop(ln))
        looks = not taken and not label and _looks_like_value(ln)
        for window in self.soft:
            if not label:
                window[0] -= 1
            if taken or looks:
                self.kept[window[1]] = None    # a line of the heading's window was removed (by any rule): the heading goes too
        self.soft = [w for w in self.soft if w[0] > 0]
        return looks

    def _advance(self, ln, removed, kind, consumed, reach, value):
        self.window = WINDOW if kind == "open" else (max(self.window - 1, 0) if consumed else 0)
        self.pending = _pending_after(ln, removed, self.pending)
        # a "Meeting ID." rule stays alive across a removed line (a link, a passcode line) until its number comes or an ordinary line does
        self.digit_wait = _ends_on_key_and_stop(ln) or bool(consumed and self.digit_wait and not value)
        if not consumed:
            self.kept.append(_MARK.sub("", ln))
            self.anchors = [*self.anchors, len(self.kept) - 1] if (kind == "open" or self.digit_wait) else []      # a chain of label lines
            if kind == "leads":
                self.soft.append([WINDOW, len(self.kept) - 1])      # a kept, finished phrase: the next three lines are looked at
        elif not reach and not (consumed and self.digit_wait):
            self.anchors = []                  # (a removed line between "Meeting ID." and its number keeps the chain)


def invite_text(body):
    """An invite body as plain text: HTML removed (also a bare table cell or list item), every line with a join link or a key to the
    meeting dropped; the next line with text (any number of blank lines on) after a label that stands alone
    (after k such labels in a row, the next k lines); and after a line that ends a
    bare label phrase ("Password reset", "Password reset for", "Password reset -", also one that was itself removed) the next WINDOW
    lines with text, blank lines skipped and not counted. A label line inside the window starts it again. Blank runs collapsed.

    IDEMPOTENT: invite_text(invite_text(x)) == invite_text(x). A label line that is KEPT and whose window then removed an ordinary line is
    itself removed (a tombstone), so a later pass finds no label to open a window on and cannot eat more lines. A finished phrase opens a
    window only when it leads its line ("Password reset", not "IT update: password reset"). Lines made only of symbols (a table rule, a
    lone colon) are transparent, like blank lines."""
    t = re.sub(r"(?i)\b(pass)\s+(code|word|phrase)", r"\1\2", plain_text(body))
    reader = _Reader()
    for ln, tail, glue in _lines(t):
        reader.feed(ln, tail, glue)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(k for k in reader.kept if k is not None)).strip()[:BODY_MAX]


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
            person = {k: a[k] for k in ("email", "registered", "type", "response") if isinstance(a.get(k), (str, bool))}
            people.append({**{k: (v[:120] if isinstance(v, str) else v) for k, v in person.items()}, "name": name[:80]})
    return files, people


# exactly what sweep.calendar_row writes; anything else in a saved row is dropped
ROW_KEYS = ("id", "start", "end", "all_day", "title", "where", "teams", "private", "organiser", "sensitivity", "organiser_email",
            "recurrence", "body", "attendees", "attachments")
_EMAIL = re.compile(r"^[^@\s<>]{1,64}@[^@\s<>]{1,190}$")


def _row_head(row, sens, private):
    out = {}
    if "id" in row:
        out["id"] = str(row["id"])[:512]
    for k in ("start", "end"):
        if k in row:
            out[k] = str(row[k])[:12]
    if "all_day" in row:
        out["all_day"] = bool(row["all_day"])
    out.update(title="Busy" if private else scrub(row.get("title"), 140) or "Meeting", where="", private=private, organiser=False,
               teams=bool(row.get("teams")) and sens != "confidential")
    return out


def _row_details(row):
    """The details of a meeting that is neither private nor confidential, each cleaned."""
    org = row.get("organiser")
    out = {"where": scrub(row.get("where"), 80), "sensitivity": "normal",
           "organiser": (scrub(org, 80) or False) if isinstance(org, str) else bool(org)}
    addr = row.get("organiser_email")
    if isinstance(addr, str) and _EMAIL.match(addr.strip()) and not flagged(addr):
        out["organiser_email"] = addr.strip()[:254]
    rec = scrub(row.get("recurrence"), 40) if isinstance(row.get("recurrence"), str) else ""
    if rec:
        out["recurrence"] = rec
    body = invite_text(str(row.get("body") or "")[:BODY_MAX])        # a saved body is already cut to BODY_MAX
    files, people = _clean_names(row)
    out.update({k: v for k, v in (("body", body), ("attachments", files), ("attendees", people)) if v})
    return out


def clean_row(row):
    """A meeting already in the saved calendar (written by an earlier version) put through today's cleaning: the sensitivity
    read again (fails closed), the title, place and organiser scrubbed, the body cleaned of join links and keys, and names
    that carry them dropped. Only the keys in ROW_KEYS survive (a description, joinUrl, location or anything else a foreign or
    older file holds is dropped, not copied). A cleaned row cleans to itself."""
    sens = sensitivity({"sensitivity": row.get("sensitivity"), "private": row.get("private")})
    private = sens == "private"
    out = _row_head(row, sens, private)
    if sens == "confidential":
        out["sensitivity"] = "confidential"
    elif not private:
        out.update(_row_details(row))
    return out


_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def clean_calendar(cal):
    """A saved calendar (calendar.json as loaded) as a reader may use it: only "fetched", "to" and "days" (a dict of YYYY-MM-DD to a list)
    survive; every day that is not a list and every row that is not a dict is dropped; every meeting goes through clean_row. Whatever the
    file holds (a list, a string day, a string row, a top-level note), the result has the same shape and no reader can fail on it.
    A cleaned calendar cleans to itself."""
    if not isinstance(cal, dict):
        return {"days": {}}
    days = cal.get("days")
    out = {k: cal[k] for k in ("fetched", "to") if isinstance(cal.get(k), str)}
    out["days"] = {d: [clean_row(r) for r in rows if isinstance(r, dict)] for d, rows in (days if isinstance(days, dict) else {}).items()
                   if isinstance(d, str) and _DAY.match(d) and isinstance(rows, list)}
    return out


_CAL_CACHE = {}


def read_calendar(path):
    """clean_calendar(the file's JSON), cached per path while the file is unchanged (modified time, size and inode, read again after the
    file is read: a file that changed meanwhile is not cached). What is cached is the CLEANED output of that exact content, so a changed
    file always misses and nothing unscrubbed is ever served. Returns a copy; raises OSError or ValueError as the plain read did."""
    import copy
    import json
    key = str(path)
    st = path.stat()
    sig = (st.st_mtime_ns, st.st_size, st.st_ino)
    hit = _CAL_CACHE.get(key)
    if hit and hit[0] == sig:
        return copy.deepcopy(hit[1])
    cal = clean_calendar(json.loads(path.read_text(encoding="utf-8")))
    st2 = path.stat()
    if (st2.st_mtime_ns, st2.st_size, st2.st_ino) == sig:
        _CAL_CACHE[key] = (sig, cal)
    return copy.deepcopy(cal)
