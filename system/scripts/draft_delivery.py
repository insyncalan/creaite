"""creaite Draft email delivery (#183, 2.6): the email put in Alan's Outlook Drafts folder, never sent.

With Settings › Essentials › Draft email › Create drafts in Outlook on (settings.json `draft_email.outlook_drafts`, off by
default), the Draft email popup's Create draft in Outlook asks the live server to make one Outlook draft. This module is the plain
code behind that route; it never calls Microsoft 365 itself and has no way to send anything:

  - `request(payload)`  the popup's payload checked and turned into the one create-draft call: the To addresses as shown
                        (none is allowed: Alan, 19-10-2026, the draft is still made with nothing in To), the subject as shown, and
                        the body exactly as the preview's HTML (bodyType html). Refused when the setting is off, and (for a
                        draft, not a copy) when the body has markup Outlook's create-draft refuses (`markup_problem`).
  - `prompt(req)`       the words for the server's headless run, whose only Microsoft 365 tool is CREATE_TOOL.
  - `check(events,req)` the run's stream-json events: exactly one CREATE_TOOL call, with exactly the request's arguments,
                        and no other tool but ToolSearch; Outlook's answer (the draft's id and web link) or a fixed reason.
  - `record_created`    on a draft made: the chase in system/staging/chases.json (drafts.chase_record, as I sent it did) and
                        one entry in system/staging/drafted.json for the sweep to find in Sent Items.
  - `record_copied`     with the setting on, Copy email instead: an entry only, so the sweep records the chase when it sees the
                        email in Sent Items.
  - `match_sent(msgs)`  the sweep's Sent Items: an entry is matched by subject, recipients and a time window and marked sent;
                        a copied one is recorded as a chase then.
  - `access(events)`    Settings' Outlook access Check: whether the connector's granted scopes let drafts be created.

drafted.json holds references only: item IDs, the mode, times, and SHA-256 fingerprints of the normalised subject and of each
recipient address. Never the subject, an address or any of the email's text. Library and command line (`request`, `prompt`,
`check`, `created`, `copied`, `access`, `sent`: JSON on stdin, JSON out), for the live server's route.
"""
import hashlib
import html.parser
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

M365 = "mcp__claude_ai_Microsoft_365__"
CREATE_TOOL = M365 + "outlook_create_draft"          # the one Microsoft 365 write the route's run may make
ACCESS_TOOL = M365 + "get_granted_scopes"            # a reading tool (permissions.M365_READ): the Check
ALLOWED_EXTRA = ("ToolSearch",)                      # loads deferred tools' schemas only (as in the VIP check)
WRITE_SCOPES = ("mail.readwrite", "mail.readwrite.shared")
DRAFTED = paths.STAGING / "drafted.json"
RECORD_MODES = ("chase", "update")                   # the popup's modes that I sent it records today (deSent)
ENTRY_MODES = ("chase", "update", "followup")
ADDRESS = re.compile(r"^[^@\s<>;,\"]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$")
ID_RE = re.compile(r"^[A-Z][A-Z0-9]{2,6}-(?:[A-Z]-)?\d{3}$")
SUBJECT_MAX, BODY_MAX, TO_MAX = 255, 500_000, 50
WINDOW = timedelta(days=14)                          # a draft sent within two weeks of being made counts
EARLY = timedelta(minutes=5)                         # clocks differ a little between the laptop and Outlook
LINK_HOSTS = ("outlook.office.com", "outlook.office365.com", "outlook.live.com")
OFF = "Create drafts in Outlook is off in Settings › Essentials › Draft email."
REASONS = (  # Outlook's error, as fixed words (never the tool's or the model's own text); the formatting rule first
    (re.compile(r"allowlist|allow list|html|markup", re.I), "Outlook rejected part of the email's formatting"),
    (re.compile(r"permission|denied|forbidden|403|unauthori[sz]ed", re.I), "you don't have permission to write to this mailbox"),
    (re.compile(r"rate|429|throttl|too many", re.I), "Outlook is busy: try again in a minute"),
    (re.compile(r"connect|token|sign.?in|AADSTS|auth", re.I), "Microsoft 365 isn't connected"),
)


# Outlook's create-draft takes an HTML body only inside its outbound allowlist (headings, paragraphs, links, lists, b/i/strong/em/strike,
# code, tables, br/hr, div, pre) and rejects, never strips, anything else: span, font, blockquote, images, scripts, event handlers,
# comments and other <!...>/<?...?> markup. Alan, 19-10-2026: the builder writes only that subset, in the copy and the draft alike
# (drafts.js draftEmail), and a body outside it is refused here, before any run, with fixed words.
ALLOWED_TAGS = frozenset("p div h1 h2 h3 h4 h5 h6 a ul ol li b i strong em strike s code pre table thead tbody tfoot tr td th "
                         "caption br hr".split())
ALLOWED_ATTRS = frozenset("style href align valign width cellpadding cellspacing border colspan rowspan bgcolor".split())
BAD_STYLE = re.compile(r"var\(|url\(|expression\(|@import|javascript:|behavior\s*:", re.I)
HREF_OK = re.compile(r"^(https?:|mailto:)", re.I)
MARKUP_REFUSED = "The email has formatting Outlook won't take ({what}): copy it instead."


class _Markup(html.parser.HTMLParser):
    """Collects the first construct outside the allowlist (as fixed words naming it)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.problem = None

    def _say(self, what):
        if self.problem is None:
            self.problem = what

    def handle_starttag(self, tag, attrs):
        if tag not in ALLOWED_TAGS:
            self._say(f"a <{tag}> element" if re.fullmatch(r"[a-z][a-z0-9-]{0,20}", tag) else "an element")
            return
        for name, value in attrs:
            if name.startswith("data-"):
                self._say("a data- attribute")
            elif name.startswith("on"):
                self._say("an event handler")
            elif name not in ALLOWED_ATTRS:
                self._say(f"{'an' if name[:1] in 'aeiou' else 'a'} {name} attribute" if re.fullmatch(r"[a-z][a-z0-9-]{0,20}", name) else "an attribute")
            elif name == "style" and BAD_STYLE.search(value or ""):
                self._say("a style Outlook won't take")
            elif name == "href" and not HREF_OK.match((value or "").strip()):
                self._say("a link that isn't a web or mail address")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_comment(self, data):
        self._say("a comment")

    def handle_decl(self, decl):
        self._say("a <!...> declaration")

    def unknown_decl(self, data):
        self._say("a <!...> declaration")

    def handle_pi(self, data):
        self._say("a <?...?> instruction")


def markup_problem(body):
    """None when every element and attribute of the HTML body is one Outlook's create-draft takes; else what isn't, in fixed words."""
    m = _Markup()
    try:
        m.feed(str(body or ""))
        m.close()
    except Exception:  # noqa: BLE001 - malformed markup is refused, never guessed at
        return "markup creaite can't read"
    return m.problem


class Refused(ValueError):
    """A payload creaite won't turn into a draft; the message is what the popup shows."""


def enabled(settings=None):
    """Whether Create drafts in Outlook is on (settings.json draft_email.outlook_drafts; off when missing)."""
    s = paths.load_settings() if settings is None else settings
    return (s.get("draft_email") or {}).get("outlook_drafts") is True


def _addresses(to):
    """The To addresses as shown ("a; b" or a list), each checked; [] when there are none."""
    raw = to if isinstance(to, list) else re.split(r"[;,]", str(to or ""))
    out = []
    for a in raw:
        a = str(a).strip()
        m = re.search(r"<([^<>]+)>\s*$", a)              # "Name <addr>" as the follow-up shows it
        a = (m.group(1) if m else a).strip()
        if not a:
            continue
        if not ADDRESS.match(a):
            raise Refused("One of the addresses isn't an email address: correct it, or copy the email instead.")
        if a.lower() not in (x.lower() for x in out):
            out.append(a)
    if len(out) > TO_MAX:
        raise Refused(f"Outlook takes at most {TO_MAX} recipients on one draft.")
    return out


def _subject(text):
    """The subject as shown: one line, not empty, at most 255 characters."""
    s = str(text or "").strip()
    if not s:
        raise Refused("The email has no subject: add one first.")
    if "\n" in s or "\r" in s or len(s) > SUBJECT_MAX:
        raise Refused(f"The subject must be one line of at most {SUBJECT_MAX} characters.")
    return s


def _body(html):
    """The preview's HTML exactly as given (no trimming, no rewriting): not empty, not over Outlook's limit."""
    if not isinstance(html, str) or not html.strip():
        raise Refused("The email is empty.")
    if len(html) > BODY_MAX:
        raise Refused("The email is too long for an Outlook draft: copy it instead.")
    return html


def request(payload, settings=None):
    """The one create-draft call for the popup's payload {to, subject, html, ids, mode, name}, or Refused."""
    if not enabled(settings):
        raise Refused(OFF)
    p = payload if isinstance(payload, dict) else {}
    to = _addresses(p.get("to"))
    args = {"subject": _subject(p.get("subject")), "body": _body(p.get("html")), "bodyType": "html"}
    bad = None if p.get("action") == "copied" else markup_problem(args["body"])   # a copy is pasted by Alan, never sent to the tool
    if bad:
        raise Refused(MARKUP_REFUSED.format(what=bad))
    if to:
        args["to"] = to                                  # no address on record: the draft is made with nothing in To
    ids = list(dict.fromkeys(i for i in p.get("ids") or [] if isinstance(i, str) and ID_RE.match(i)))[:50]
    mode = p.get("mode") if p.get("mode") in ENTRY_MODES else "chase"
    return {"tool": CREATE_TOOL, "args": args, "ids": ids, "mode": mode, "no_recipient": not to}


def allowed_tools():
    """The route's run may use these and nothing else: the create-draft tool and ToolSearch."""
    return [CREATE_TOOL, *ALLOWED_EXTRA]


def denied_tools():
    """Every Microsoft 365 action but create-draft, named (the sending ones among them): the route adds the server's own
    built-in and other-connector denies. A deny beats an allow, so create-draft must never be in this list."""
    import permissions
    return [t for t in permissions.m365_action_tools() if t != CREATE_TOOL]


PROMPT = ("creaite draft email. Make one draft in the signed-in user's Outlook Drafts folder and do nothing else: never send, "
          "never call any tool but {tool} (load its schema with ToolSearch "
          "if it is deferred). Call {tool} exactly once with exactly these arguments, copied byte for byte, the body unchanged: "
          "{args}\nThen reply with only one JSON object: {{\"ok\": true}} when the draft was made, or {{\"ok\": false}} when "
          "the tool refused. No other words.")


def prompt(req):
    """The headless run's words (placed after `--` by the server)."""
    return PROMPT.format(tool=req["tool"], args=json.dumps(req["args"], ensure_ascii=False))


def _blocks(events):
    """(tool uses [(id, name, input)], tool results {id: (is_error, text)}) from stream-json events."""
    uses, results = [], {}
    for e in events if isinstance(events, list) else []:
        msg = e.get("message") if isinstance(e, dict) else None
        content = msg.get("content") if isinstance(msg, dict) else None
        for b in content if isinstance(content, list) else []:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_use":
                uses.append((b.get("id"), str(b.get("name") or ""), b.get("input")))
            elif b.get("type") == "tool_result":
                results[b.get("tool_use_id")] = (bool(b.get("is_error")), _text(b.get("content")))
    return uses, results


def _text(content):
    """A tool result's text, whether a string or a list of text blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(c.get("text") or "") for c in content if isinstance(c, dict))
    return ""


def reason(text):
    """Outlook's refusal in fixed words (the tool's own message is only counted, never shown)."""
    for pat, words in REASONS:
        if pat.search(text or ""):
            return words
    return f"an error from Outlook ({len(text or '')} characters held back)"


def _made(text):
    """The draft's id and web link from the tool's answer ({} when it isn't JSON); a link off Outlook's own hosts is dropped."""
    try:
        got = json.loads(text)
    except (ValueError, TypeError):
        got = {}
    got = got if isinstance(got, dict) else {}
    link = str(got.get("webLink") or got.get("web_link") or "")
    host = re.match(r"^https://([^/]+)/", link)
    return {"id": str(got.get("id") or "")[:400], "web_link": link if host and host.group(1).lower() in LINK_HOSTS else ""}


def check(events, req):
    """What the run did: {ok, made, id, web_link} or {ok: False, made, reason}. `made` says whether a draft may exist (a call that
    went through), so a mismatch is never reported as nothing having happened."""
    uses, results = _blocks(events)
    other = [n for _, n, _ in uses if n not in allowed_tools()]
    calls = [(i, inp) for i, n, inp in uses if n == CREATE_TOOL]
    done = [(i, inp) for i, inp in calls if i in results and not results[i][0]]
    if other:
        return {"ok": False, "made": bool(done), "reason": "the run tried another tool, so creaite stopped it"}
    if not calls:
        return {"ok": False, "made": False, "reason": "Outlook wasn't reached"}
    if len(calls) > 1 or any(inp != req["args"] for _, inp in calls):
        return {"ok": False, "made": bool(done), "reason": "the draft wasn't made exactly as shown: check your Drafts folder"}
    tid = calls[0][0]
    if tid not in results:
        return {"ok": False, "made": False, "reason": "Outlook didn't answer"}
    if results[tid][0]:
        return {"ok": False, "made": False, "reason": reason(results[tid][1])}
    return {"ok": True, "made": True, **_made(results[tid][1])}


def fingerprint(text):
    """A SHA-256 fingerprint (16 hex characters) of normalised text: lower case, spaces collapsed, Re:/Fw: dropped."""
    t = re.sub(r"\s+", " ", str(text or "")).strip().lower()
    t = re.sub(r"^(?:(?:re|fw|fwd)\s*:\s*)+", "", t)
    return hashlib.sha256(t.encode("utf-8")).hexdigest()[:16]


def load():
    """drafted.json's entries; an unreadable file is an empty list."""
    try:
        data = json.loads(DRAFTED.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [e for e in (data.get("drafted") or []) if isinstance(e, dict)] if isinstance(data, dict) else []


def save(entries):
    """Write drafted.json whole (atomic)."""
    DRAFTED.parent.mkdir(parents=True, exist_ok=True)
    tmp = DRAFTED.with_suffix(".tmp")
    tmp.write_text(json.dumps({"drafted": entries}, indent=1) + "\n", encoding="utf-8")
    tmp.replace(DRAFTED)


def _entry(req, via, now, recorded):
    """One drafted.json entry: references and fingerprints only."""
    return {"ids": req["ids"], "mode": req["mode"], "at": now.strftime("%Y-%m-%d %H:%M"), "via": via,
            "subject": fingerprint(req["args"]["subject"]), "to": sorted(fingerprint(a) for a in req["args"].get("to") or []),
            "recorded": recorded, "sent": None}


def _now(now=None):
    """The time to the minute (sweep.now: CREAITE_NOW in tests), unless one is given."""
    if now:
        return now
    import sweep
    return sweep.now()


def record_created(req, now=None):
    """A draft was made: the chase is recorded now (it steps up the next one) and the entry kept for the sweep. Returns
    {chased: [ids], entry}."""
    import drafts
    now = _now(now)
    chased = []
    if req["ids"] and req["mode"] in RECORD_MODES:
        chased = drafts.chase_record(req["ids"], req["mode"], now.strftime("%Y-%m-%d"))["ids"]
    entry = _entry(req, "draft", now, bool(chased) or req["mode"] not in RECORD_MODES)
    save(load() + [entry])
    return {"chased": chased, "entry": entry}


def record_copied(req, now=None):
    """Copy email with the setting on: nothing is recorded yet; the sweep records the chase when it sees the email sent."""
    now = _now(now)
    entry = _entry(req, "copy", now, req["mode"] not in RECORD_MODES or not req["ids"])
    save(load() + [entry])
    return {"entry": entry}


def _when(text):
    """A Sent Items time, "YYYY-MM-DD HH:MM" (or an ISO date-time), or None."""
    try:
        return datetime.strptime(str(text or "")[:16].replace("T", " "), "%Y-%m-%d %H:%M")
    except ValueError:
        return None


def _matches(e, subj, to, at):
    """Whether one unsent entry is this sent message: the same subject, every drafted recipient among its recipients, in time."""
    made = _when(e.get("at"))
    if e.get("sent") or not made or e.get("subject") != subj:
        return False
    if not (made - EARLY <= at <= made + WINDOW):
        return False
    return set(e.get("to") or []) <= to


def _mark(e, at):
    """Mark an entry sent; record the chase if it wasn't yet (Copy instead). Returns 1 when a chase was recorded."""
    import drafts
    e["sent"] = at.strftime("%Y-%m-%d")
    if e.get("recorded") or not e.get("ids") or e.get("mode") not in RECORD_MODES:
        return 0
    drafts.chase_record(e["ids"], e["mode"], e["sent"])
    e["recorded"] = True
    return 1


def match_sent(messages):
    """The sweep's Sent Items [{subject, to, sent|at}]: each matched entry is marked sent (the earliest unsent first). Returns
    counts only: {seen, matched, recorded}."""
    entries, seen, matched, recorded = load(), 0, 0, 0
    for m in messages if isinstance(messages, list) else []:
        if not isinstance(m, dict) or not (at := _when(m.get("sent") or m.get("at"))):
            continue
        seen += 1
        try:
            to = {fingerprint(a) for a in _addresses(m.get("to"))}
        except Refused:
            continue                                    # an address creaite can't read: that message is not one of ours
        subj = fingerprint(m.get("subject"))
        hit = next((e for e in sorted(entries, key=lambda x: str(x.get("at"))) if _matches(e, subj, to, at)), None)
        if hit:
            matched += 1
            recorded += _mark(hit, at)
    if matched:
        save(entries)
    return {"seen": seen, "matched": matched, "recorded": recorded}


def sent_days():
    """{item ID: the last day a drafted email about it was seen in Sent Items}, for the chase counts."""
    out = {}
    for e in (x for x in load() if x.get("sent")):
        for i in e.get("ids") or []:
            out[i] = max(out.get(i, ""), str(e["sent"]))
    return out


def access(events):
    """The Check: {can: True|False|None, at: HH:MM}. True when the granted scopes include Mail.ReadWrite; False when they don't
    or Microsoft refuses; None when the run never reached the tool."""
    uses, results = _blocks(events)
    ids = [i for i, n, _ in uses if n == ACCESS_TOOL]
    at = _now().strftime("%H:%M")
    if not ids or ids[0] not in results:
        return {"can": None, "at": at}
    err, text = results[ids[0]]
    if err:
        return {"can": False, "at": at}
    words = {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z.]+", text)}
    return {"can": any(s in words for s in WRITE_SCOPES), "at": at}


def _cmd(name, body):
    """One command's answer (a dict)."""
    if name == "request":
        return request(body)
    if name == "prompt":
        return {"prompt": prompt(body)}
    if name == "check":
        return check(body.get("events"), body.get("request") or {})
    if name == "created":
        return record_created(body)
    if name == "copied":
        return record_copied(request(body))
    if name == "access":
        return access(body.get("events"))
    if name == "sent":
        return match_sent(body.get("messages"))
    raise Refused("Not a draft_delivery command.")


def main(argv):
    """draft_delivery.py <command>: JSON on stdin, one JSON answer on stdout; exit 1 with {ok: false, message} when refused."""
    try:
        body = json.loads(sys.stdin.read() or "{}")
        out = _cmd(argv[0] if argv else "", body if isinstance(body, dict) else {})
    except (Refused, ValueError) as e:
        print(json.dumps({"ok": False, "message": str(e)}))
        return 1
    print(json.dumps({"ok": True, **out}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
