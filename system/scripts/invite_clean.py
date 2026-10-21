"""#265 review M1, M2: what the saved calendar (system/staging/calendar.json) may keep of a meeting invite. Plain code, no I/O.

creaite's rule: attendees, the invite's body as plain text and attachment names are kept; never a join link, meeting ID, passcode,
PIN or dial-in number; a confidential meeting keeps only its title and times; a private one is "Busy". This module is the one
place that decides, for sweep.py's calendar save:

- sensitivity(ev): "private", "confidential" or "normal". It fails closed: any value but empty, "normal" or "none" is
  confidential (restricted, secret, "Strictly Confidential", 2, True...), after case, spacing, zero-width characters and
  look-alike forms (NFKC) are removed; anything that says private or personal is private; a private flag stays "Busy".
- invite_text(body): HTML to plain text, then every line that carries a join link or a key to the meeting is dropped.
- is_secret(text) / scrub(text): the same test for a single field (title, place, organiser), which loses only the offending
  words; flagged(text) for names.

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
URL = re.compile(r"(?:\b[a-z][a-z0-9+.-]{1,12}://|\bwww\.)\S+|\b(?:[a-z0-9-]{1,63}\.){1,8}[a-z]{2,24}(?::\d+)?/\S*", re.I)
KEYED = re.compile(r"[?&;#/](?:pwd|passcode|passwd|pass|password|pin|tk|token|key|secret|sig|signature|auth|code|access_token|otp|"
                   r"mtid|meetingid|meetingnumber|conferenceid|confid|jid)=", re.I)
JOINPATH = re.compile(r"/(?:j|join|joinme|meet|meeting|meetings|webinar|conference|room|rooms|call|invite|video)(?:[/?#]|$)|/\d{9,}",
                      re.I)
JOINWORD = re.compile(r"\b(?:join|dial|webinar|conference|video\s*call|video\s*meeting|meeting\s*link|online\s*meeting|"
                      r"click\s+(?:here\s+)?to)\b", re.I)

# ---- keys: passcodes, PINs, meeting IDs, dial-in numbers ----
_VAL = r"(?:\s*(?:[:=#\-\u2013]\s*\S|\bis\b\s*\S)|\s+(?:no\.?\s*)?\S*\d)"            # a label followed by a value
_EVERYWHERE = (r"pass\s*codes?|pass\s*phrases?|pass\s*keys?|pwd|passwd|kenn\s*codes?|zugangs\s*codes?|einwahl\s*codes?|"
               r"teilnehmer\s*codes?|code\s+secret|code\s+d.acc[e\u00e8]s|toegangs\s*codes?|vergader\s*codes?|pin\s*codes?|"
               r"c[o\u00f3]digo\s+(?:de\s+(?:acceso|acesso|reuni[o\u00f3]n)|da\s+reuni[a\u00e3]o)|"
               r"codice\s+(?:di\s+(?:accesso|partecipazione)|riunione)|password\s+(?:della\s+)?riunione|"
               r"one[- ]time[\s-]*(?:pass)?codes?|conference\s+bridge|"
               r"(?:host|moderator|presenter|security|entry|access|meeting|participant|attendee|guest)[\s-]*keys?|"
               r"(?:access|participant|conference|attendee|host|meeting|moderator|presenter|guest|security|entry|"
               r"dial[- ]?in|audio|phone|call[- ]?in|room|webinar|panell?ist|leader)[\s-]*(?:code|pin)s?")
_PASSWORDS = (r"pass\s*words?|passwort|kennwort|mot\s+de\s+passe|mot-de-passe|contrase[n\u00f1]a|contrasena|senha|wachtwoord|"
              r"clave\s+de\s+acceso")
_NUMBERED = (r"pin(?:\s*(?:code|number|no\.?))?|toplant[\u0131i]\s+kimli[\u011fg]i|"
             r"(?:meeting|webinar|event|session|conference|call|phone\s+conference)[\s-]*(?:id|number|no\.?)")
_WITH_VALUE = _PASSWORDS + "|" + _NUMBERED
_BARE = r"secret|codes?|keys?|tokens?|otp|access|codice|c[o\u00f3]digo|[s\u015f]ifre|parola"       # a value must follow these
_OTHER_ALPHABETS = ("رمز المرور|كلمة المرور|كلمة السر|رمز الدخول|رمز الوصول|رمز الاجتماع|رمز الانضمام|الرقم السري|"
                    "رقم التعريف الشخصي|密码|密碼|口令|访问码|パスコード|パスワード|暗証番号|会議\\s*id|会議番号|ミーティング\\s*id|"
                    "비밀번호|회의\\s*암호|회의\\s*id|암호|пароль|код\\s+доступа|код\\s+конференции|"
                    "идентификатор\\s+(?:конференции|встречи)|пин-код")
LABEL = re.compile(rf"(?<![\w-])(?:{_EVERYWHERE})(?![\w-])|(?<![\w-])(?:{_WITH_VALUE}|{_BARE})(?![\w-]){_VAL}"
                   rf"|(?<![\w-])id\s*[:#=]\s*\d|(?:{_OTHER_ALPHABETS})", re.I)
# v2.6 review (Cap, item 5): the one label cut after which the rest of a field may stay: an ID-like label and a value that has a
# digit in it, the whole match ("Code 2 review" keeps "review"; "Board Meeting ID 123 456 789 sync" keeps "Board sync").
LABEL_NUMBER = re.compile(rf"(?<![\w-])(?:{_NUMBERED}|{_BARE})(?![\w-])\s+(?:no\.?\s*)?\S*\d", re.I)
LABEL_ALONE = re.compile(rf"(?:(?<![\w-])(?:{_EVERYWHERE}|{_WITH_VALUE})(?![\w-])|(?:{_OTHER_ALPHABETS}))\s*[:=#]?\s*$", re.I)
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
    s = skeleton(str(text if text is not None else "")[:LINE_MAX + 200])       # every test runs on a bounded text (timing)
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


_VALUE_TAIL = re.compile(r"(?:\s*(?:[:=#\-\u2013]|\bis\b)\s*\S+|\s+\S*\d\S*)?(?:[\s.\-]+\d\S*)*")
SCRUB_ROUNDS = 8


def _secret_span(t):
    """(start, end, rest_ok) of the first key, join link or dial-in found in t as it stands, widened to whole words and, for a
    label, the value after it ("PIN 4321", "Passcode: 4321", "Meeting ID 123 456 789"); None when none is found in t itself.
    rest_ok is True only for an ID-like label whose own match carried a value with a digit (LABEL_NUMBER): after any other cut
    (a host, a scheme, a dial-in, a passcode or password label) the next word may be the value, so the field fails closed."""
    for rx in (HOSTS, SCHEME, LABEL, DIAL):
        m = rx.search(t)
        if not m:
            continue
        a, b = m.start(), m.end()
        while a > 0 and not t[a - 1].isspace():
            a -= 1
        while b < len(t) and not t[b].isspace():
            b += 1
        rest_ok = rx is LABEL and bool(LABEL_NUMBER.fullmatch(m.group()))
        if rx is LABEL:
            b += len(_VALUE_TAIL.match(t, b).group())
        return a, b, rest_ok
    return None


def scrub(text, limit):
    """A title, place or organiser: join links taken out, and (v2.6 review) each key or dial-in taken out with its value, so
    "Budget (PIN 4321)" keeps "Budget" and "Code 2 review" keeps "review". It fails closed: a secret seen only once the text is
    decoded or its look-alike letters read as Latin (no span to cut in the text itself) drops the whole text, and so does any
    text left after a cut other than an ID-like label with a numbered value ("Steering Passcode: kqZxyw", "Weekly sync zoom.us
    98765432101" are dropped whole: the next word may be the value). Only the first
    LINE_MAX characters are looked at (and a field is kept far shorter)."""
    t = normal(str(text if text is not None else "")[:LINE_MAX])
    t = URL.sub(lambda m: "" if _bad_url(skeleton(m.group())) else m.group(), t)
    t = re.sub(r"\s+", " ", t).strip()
    for _ in range(SCRUB_ROUNDS):
        if not is_secret(t):
            return t[:limit]
        span = _secret_span(t)
        if span is None or (not span[2] and t[span[1]:].strip()):
            return ""
        t = re.sub(r"\s+", " ", t[:span[0]] + " " + t[span[1]:]).strip()
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
    if re.search(r"<(html|body|div|p|br|span|table|a)\b", t, re.I):
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


def invite_text(body):
    """An invite body as plain text: HTML removed, every line with a join link or a key to the meeting dropped, and the next
    line with text (up to two blank lines on) after a label that stands alone; blank runs collapsed."""
    t = re.sub(r"(?i)\b(pass)\s+(code|word|phrase)", r"\1\2", plain_text(body))
    kept, waiting, blanks = [], False, 0
    for ln, tail in _lines(t):
        if waiting and not ln:
            blanks += 1
            waiting = blanks <= 2
        elif waiting:
            waiting = False                    # the value of a label that stood alone
            continue
        if ln and (_drop_line(ln) or (tail and _drop_line(tail + " " + ln))):
            waiting, blanks = _alone(ln), 0
            continue
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
