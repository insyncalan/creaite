"""#265 review M1, M2: what the saved calendar (system/staging/calendar.json) may keep of a meeting invite. Plain code, no I/O.

creaite's rule: attendees, the invite's body as plain text and attachment names are kept; never a join link, meeting ID, passcode,
PIN or dial-in number; a confidential meeting keeps only its title and times; a private one is "Busy". This module is the one
place that decides, for sweep.py's calendar save:

- sensitivity(ev): "private", "confidential" or "normal". It fails closed: any value but empty, "normal" or "none" is
  confidential (restricted, secret, "Strictly Confidential", 2, True...), after case, spacing, zero-width characters and
  look-alike forms (NFKC) are removed; anything that says private or personal is private; a private flag stays "Busy".
- invite_text(body): HTML to plain text, then every line that carries a join link or a key to the meeting is dropped.
- is_secret(text) / scrub(text): the same test for a single field (title, place, organiser); flagged(text) for names.

Text is matched after NFKC and with zero-width characters, combining marks and URL or HTML escapes (twice over) removed, so
full-width "PIN", a zero-width space inside "zoom.us", "%3Fpwd%3D" and "https&#58;//" are caught, and look-alike letters from other
alphabets are read as the Latin ones (confusables.py). A label alone on a line takes the line after it too (a table's "PIN" and
its value in the next cell), and "Pass" and "code" split by tags are joined. Not covered: letters spaced out one by one ("P I N"),
and a link to a provider this module does not know with no word of joining near it.
"""
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
URL = re.compile(r"(?:\b[a-z][a-z0-9+.-]{1,12}://|\bwww\.)\S+|\b(?:[a-z0-9-]+\.)+[a-z]{2,24}(?::\d+)?/\S*", re.I)
KEYED = re.compile(r"[?&;#/](?:pwd|passcode|passwd|pass|password|pin|tk|token|key|secret|sig|signature|auth|code|access_token|otp|"
                   r"mtid|meetingid|meetingnumber|conferenceid|confid|jid)=", re.I)
JOINPATH = re.compile(r"/(?:j|join|joinme|meet|meeting|meetings|webinar|conference|room|rooms|call|invite|video)(?:[/?#]|$)|/\d{9,}",
                      re.I)
JOINWORD = re.compile(r"\b(?:join|dial|webinar|conference|video\s*call|video\s*meeting|meeting\s*link|online\s*meeting|"
                      r"click\s+(?:here\s+)?to)\b", re.I)

# ---- keys: passcodes, PINs, meeting IDs, dial-in numbers ----
_VAL = r"(?:\s*(?:[:=#\-–]\s*\S|\bis\b\s*\S)|\s+(?:no\.?\s*)?\S*\d)"            # a label followed by a value
_EVERYWHERE = (r"pass\s*codes?|pass\s*phrases?|pwd|passwd|kenn\s*codes?|zugangs\s*codes?|einwahl\s*codes?|teilnehmer\s*codes?|"
               r"code\s+secret|code\s+d.acc[eè]s|c[oó]digo\s+de\s+(?:acceso|acesso|reuni[oó]n)|codice\s+di\s+accesso|"
               r"toegangs\s*codes?|(?:access|participant|conference|attendee|host|meeting|moderator|presenter|guest|security|entry|"
               r"dial[- ]?in|audio|phone|call[- ]?in|room|webinar|panell?ist|leader)[\s-]*(?:code|pin)s?")
_WITH_VALUE = (r"pass\s*words?|passwort|kennwort|mot\s+de\s+passe|mot-de-passe|contrase[nñ]a|contrasena|senha|wachtwoord|"
               r"clave\s+de\s+acceso|pin(?:\s*(?:code|number|no\.?))?|meeting\s*(?:id|number|no\.?)|"
               r"(?:phone\s+)?conference\s+id|meeting\s+id")
_OTHER_ALPHABETS = ("رمز المرور|كلمة المرور|كلمة السر|رمز الدخول|رمز الوصول|رمز الاجتماع|رمز الانضمام|الرقم السري|"
                    "رقم التعريف الشخصي|密码|密碼|口令|访问码|パスコード|パスワード|暗証番号|비밀번호|пароль|код\\s+доступа|пин-код")
LABEL = re.compile(rf"(?<![\w-])(?:{_EVERYWHERE})(?![\w-])|(?<![\w-])(?:{_WITH_VALUE}|secret|codes?)(?![\w-]){_VAL}"
                   rf"|(?:{_OTHER_ALPHABETS})", re.I)
LABEL_ALONE = re.compile(rf"(?:(?<![\w-])(?:{_EVERYWHERE}|{_WITH_VALUE})(?![\w-])|(?:{_OTHER_ALPHABETS}))\s*[:=#]?\s*$", re.I)
DIAL = re.compile(r"\d{3,}\s*#(?!\w)|,,\s*\d|\d\s*,,|(?<![\w-])(?:dial[- ]?in|dial|toll[- ]?free|call[- ]?in|conference\s+call)(?![\w-])"
                  r"[^\n]{0,60}\+?\(?\d[\d ()./-]{6,}", re.I)
# BL-98: the Teams and Outlook joining boilerplate, one line at a time (the lines the keys above do not already catch)
JOIN_LINE = re.compile(
    r"(microsoft teams (meeting|need help)|join (the meeting|on your computer|with a video conferencing|by phone|"
    r"conference)|click (here )?to join|phone conference id|find a local number|"
    r"reset dial[- ]in pin|conference id|for organi[sz]ers: meeting options|learn more( about teams)?\s*(\||$)|meeting options|"
    r"^\s*\+\d[\d ,#()-]{7,}|^\s*_{8,}\s*$|^\s*\.{3,}\s*$|system reference|"
    r"this meeting is being recorded|join microsoft teams meeting)", re.I)


def normal(text, marks=False):
    """NFKC, with control and private-use characters (but not line breaks) and every format character (zero-width, bidi, soft
    hyphen) removed; `marks` keeps the two link markers."""
    t = unicodedata.normalize("NFKC", str(text if text is not None else ""))
    return "".join(c for c in t if c in "\n\r\t" or (marks and c in (OPEN, CLOSE))
                   or unicodedata.category(c) not in ("Cf", "Cc", "Co"))


def skeleton(text):
    """What a test matches on: normal(), combining marks and Arabic tatweel removed, escapes and URL encoding decoded."""
    t = "".join(c for c in normal(text) if unicodedata.category(c) != "Mn" and c != "ـ")
    for _ in range(3):
        u = unquote(htmllib.unescape(t))
        if u == t:
            break
        t = u
    return t


def _bad_url(url):
    """Whether a URL (already decoded) is a join link: a known provider, a short link, a key in it, or a join-shaped path."""
    return bool(HOSTS.search(url) or KEYED.search(url) or JOINPATH.search(url))


def _views(text):
    """The skeleton, and the same with look-alike letters (a Cyrillic "а" for an "a") read as the Latin ones."""
    s = skeleton(text)
    t = s.translate(confusables.TABLE)
    return [s, t] if t != s else [s]


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
    """A title, place or organiser: join links taken out; the whole text dropped when a key or dial-in is left in it."""
    t = URL.sub(lambda m: "" if _bad_url(skeleton(m.group())) else m.group(), normal(text))
    t = re.sub(r"\s+", " ", t).strip()
    return "" if is_secret(t) else t[:limit]


def _anchor(m):
    """<a href=…>text</a> as text, with the address beside it so a line can be judged by it (removed again after)."""
    href = m.group(1) or m.group(2) or m.group(3) or ""
    return f"{m.group(4)}{OPEN}{href}{CLOSE}" if href else m.group(4)


def plain_text(body):
    """An invite body as text: HTML removed (inline tags without a gap, so "Pass<b>code</b>" is one word), entities decoded."""
    t = normal(str(body or "")[:RAW_MAX])
    if re.search(r"<(html|body|div|p|br|span|table|a)\b", t, re.I):
        t = re.sub(r"(?is)<(script|style|head)\b.*?</\1>", " ", t)
        t = re.sub(r"(?is)<a\b[^>]*?\bhref\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+))[^>]*>(.*?)</a\s*>", _anchor, t)
        t = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|h\d)>", "\n", t)
        t = re.sub(r"(?i)<li\b[^>]*>", "\n- ", t)
        t = re.sub(r"(?i)</?(span|b|i|u|em|strong|font|a|small|big|sup|sub|mark)\b[^>]*>", "", t)
        t = re.sub(r"<[^>]+>", " ", t)
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


def invite_text(body):
    """An invite body as plain text: HTML removed, every line with a join link or a key to the meeting dropped (and the line
    after a label that stands alone), blank runs collapsed."""
    t = re.sub(r"(?i)\b(pass)\s+(code|word|phrase)", r"\1\2", plain_text(body))
    kept, skip_next = [], False
    for ln in (p for x in t.split("\n") for p in _pieces(re.sub(r"[ \t]+", " ", x).strip())):
        if skip_next and ln:
            skip_next = False
            continue
        if _drop_line(ln):
            skip_next = any(LABEL_ALONE.search(s) for s in _views(_MARK.sub(" ", ln)))
            continue
        skip_next = False
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
