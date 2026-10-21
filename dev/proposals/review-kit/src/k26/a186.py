"""2.6 area (a): the Draft email's AI bar for an OUTSIDE recipient (#186), the Client messaging field (#263) and the minutes sheet (#262),
as edit_ai.py's own `context` and `result` commands in a throwaway vault (Claude is never called; the reply is what a hostile model
would send). Fictional data only. Each case prints one line:   ### CASE <name> | LEAK|PASS|HELD|CTRL-FAIL|SKIP | evidence
  LEAK   the prompt for an outside email holds a hidden item, owner or health reason, or a suggestion that brings one in is returned
  HELD   creaite refused or dropped it (the refusal is the pass)         SKIP  this tree has not got the feature
Usage: python a186.py <tree root> <variant>      variants: ids, names, spoof, keys, place
The #186 live_server.diff (guarded, a proposal) is applied to the vault's own COPY of live_server.py when the tree has the diff and
not the route; the checkout is never edited."""
import json
import os
import sqlite3
import subprocess
import sys
import unittest
from contextlib import closing
from pathlib import Path

ROOT = Path(sys.argv.pop(1))
VARIANT = sys.argv.pop(1)
sys.path.insert(0, str(ROOT / "dev" / "tests"))
sys.path.insert(0, str(ROOT / "system" / "scripts"))
sys.path.insert(0, str(ROOT / "system" / "scripts" / "vendor"))
import test_reports as R  # noqa: E402

DIFF = ROOT / "dev" / "proposals" / "draft-ai-186" / "live_server.diff"
REASON = "the vendor contract dispute is still unresolved with procurement"      # the tracker's internal health reason (fictional)
HIDDEN = "ABC-A-004"          # Confirm tester names, owner Omar Ali, client_visible=0
HIDDEN_TITLE = "Confirm tester names"
OWNER = "Omar Ali"
OUTSIDE = "jane.doe@client.example"
INSIDE = "sam.patel@brightwater.example"
TEXT = "Please send the signed paperwork by Friday so we can plan the next step."
HAS_EMAIL_AI = "def email_outside" in (ROOT / "system/scripts/edit_ai.py").read_text(encoding="utf-8")


def case(name, status, ev=""):
    print(f"### CASE {name} | {status} | {str(ev)[:200]}", flush=True)


def ask(recipients=None, text=TEXT, option="rewrite", **extra):
    body = {"option": option, "text": text, "code": "ABC", "place": "email", **extra}
    if recipients is not None:
        body["recipients"] = recipients
    return body


class P(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = R.ReportVault()
        R.populate(cls.v)
        cls.root = cls.v.root
        with closing(sqlite3.connect(cls.root / "system/tracker.db")) as con:
            con.execute("UPDATE projects SET health = 'At risk', health_reason = ? WHERE code = 'ABC'", (REASON,))
            con.commit()
            cls.hidden = [r[0] for r in con.execute("SELECT id FROM actions WHERE project='ABC' AND client_visible=0")] + \
                         [r[0] for r in con.execute("SELECT id FROM raid WHERE project='ABC' AND client_visible=0")]
            cls.owners = [r[0] for r in con.execute("SELECT DISTINCT owner FROM actions WHERE project='ABC' AND client_visible=0 "
                                                    "AND owner <> ''")]
        cls.diff_applied = False
        live = cls.root / "system/scripts/live_server.py"
        if live.is_file() and "def edit_ai_caps_route" not in live.read_text(encoding="utf-8") and DIFF.is_file():
            r = subprocess.run(["patch", "-p0", "-s", "-d", str(cls.root), "-i", str(DIFF)], capture_output=True, text=True)
            cls.diff_applied = r.returncode == 0

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    # ── helpers ──────────────────────────────────────────────────────────────────────────────────────────────────────────
    def edit_ai(self, cmd, body):
        r = subprocess.run([sys.executable, str(self.root / "system/scripts/edit_ai.py"), cmd], input=json.dumps(body), cwd=self.root,
                           capture_output=True, text=True, timeout=120)
        if r.returncode:
            raise RuntimeError(f"edit_ai.py {cmd} failed: {r.stdout[-200:]}{r.stderr[-300:]}")
        return json.loads(r.stdout)

    def reply(self, request, ctx, text):
        return self.edit_ai("result", {"request": request, "context": ctx, "reply": f"<<<SUGGESTION\n{text}\nSUGGESTION>>>"})

    def prompt_leaks(self, ctx):
        p = ctx.get("prompt") or ""
        return [x for x in [*self.hidden, *self.owners, REASON] if x in p]

    def need(self):
        if not HAS_EMAIL_AI:
            case(f"{VARIANT}: the Draft email AI bar", "SKIP", "this tree has no edit_ai.email_outside (2.5.3: the email gets the full facts by design)")
            return False
        return True

    def settings(self, mutate):
        s = self.root / "system/config/settings.json"
        before = s.read_text(encoding="utf-8")
        d = json.loads(before)
        mutate(d)
        s.write_text(json.dumps(d), encoding="utf-8")
        return lambda: s.write_text(before, encoding="utf-8")

    def judge(self, name, request, reply_text, expect_dropped=True, tag=""):
        """An outside email: the reply must be dropped (HELD) rather than returned (LEAK)."""
        ctx = self.edit_ai("context", request)
        if "refused" in ctx:
            case(name, "HELD", "refused before Claude: " + ctx["refused"][:100])
            return
        bad = self.prompt_leaks(ctx)
        if bad:
            case(name, "LEAK", f"the prompt for an outside email holds {bad[:3]}")
            return
        out = self.reply(request, ctx, reply_text)
        if out.get("text"):
            case(name, "LEAK", f"a suggestion with {tag or 'internal material'} came back: {out['text'][:80]!r}")
        else:
            case(name, "HELD", (out.get("message") or "dropped")[:100])

    # ── variants ─────────────────────────────────────────────────────────────────────────────────────────────────────────
    def test_ids(self):
        if not self.need():
            return
        n = HIDDEN
        zw = "​"
        forms = {
            "strict": n, "lower": n.lower(), "lower unpadded abc-a-4": "abc-a-4", "unpadded ABC-A-4": "ABC-A-4",
            "en dash": n.replace("-", "–"), "non-breaking hyphen": n.replace("-", "‑"), "minus sign": n.replace("-", "−"),
            "spaced": "ABC A 004", "letter spaced": "A B C - A - 0 0 4", "dotted": "ABC.A.004", "slashed": "ABC/A/004",
            "bracketed": "ABC (A) 004", "underscored": "ABC_A_004", "markdown escape": "ABC\\-A\\-004",
            "four digits ABC-A-0004": "ABC-A-0004", "ABC-A-0004/1": "ABC-A-0004/1", "ABC-A-004/1": "ABC-A-004/1", "ABC-A-0001/1 form": "ABC-A-0004/1 (see)",
            "O for zero": "ABC-A-OO4", "html comment split": "ABC<!-- -->-A-004", "html bold split": "ABC<b>-A-</b>004",
            "html span name": "A<span>BC</span>-A-004", "zero width": f"ABC{zw}-A-{zw}004", "bidi mark": "ABC‎-A-004",
            "soft hyphen": "ABC­-A-004", "cyrillic ABC": "АВС-A-004", "greek A": "ABC-Α-004",
            "full-width digits": "ABC-A-００４", "arabic-indic digits": "ABC-A-٠٠٤",
            "run on word": "seeABC-A-004", "creaite link": f"[the plan](creaite:item/{n})", "combining acute": "ABC-A-0́04",
        }
        for label, form in forms.items():
            self.judge(f"ids: hidden ID as {label}", ask([OUTSIDE]), f"Please send the signed paperwork by Friday; {form} waits on it.",
                       tag=f"the hidden ID as {label}")
        for label, form in (("strict", n), ("en dash", n.replace("-", "–")), ("spaced", "ABC A 004")):
            self.judge(f"ids: hidden ID in the SELECTED text, {label}", ask([OUTSIDE], text=f"{form} is late; please chase the paperwork."),
                       "Please send the signed paperwork by Friday.", tag="a reply to a selection holding it")
        # control: a client-visible ID still comes back
        ctx = self.edit_ai("context", ask([OUTSIDE]))
        out = self.reply(ask([OUTSIDE]), ctx, "Could you send the signed paperwork by Friday? ABC-A-002 waits on it.")
        case("ids control: a client-visible ID passes", "PASS" if out.get("text") else "CTRL-FAIL",
             "" if out.get("text") else (out.get("message") or "")[:100])

    def test_names(self):
        if not self.need():
            return
        zw = "​"
        reasons = {"health reason": REASON, "health reason upper": REASON.upper(), "health reason zero width": REASON.replace(" ", f" {zw}"),
                   "health reason hyphens for spaces": REASON.replace(" ", "-"), "health reason html split": REASON.replace("vendor", "ven<b>dor</b>"),
                   "health reason nbsp": REASON.replace(" ", " ")}
        markers = {"Internal only:": "Internal only: keep this away from the client.", "INTERNAL ONLY": "INTERNAL ONLY note for the team.",
                   "Internal-only": "This is internal-only wording.", "(internal only)": "Budget moved (internal only).",
                   "Confidential:": "Confidential: the budget moved.", "Client-safe: no": "Client-safe: no, the budget moved.",
                   "internal  only double space": "Internal  only: the budget moved.", "zero-width inside": f"Inter{zw}nal only: the budget moved.",
                   "internal\\nonly": "Internal\nonly: the budget moved."}
        owner_forms = {"owner": OWNER, "owner lower": OWNER.lower(), "owner double space": OWNER.replace(" ", "  "),
                       "owner nbsp": OWNER.replace(" ", " "), "owner zero width": OWNER.replace("m", f"m{zw}"),
                       "owner html split": "Om<b>ar</b> Ali", "owner cyrillic O": "Оmar Ali", "owner upper": OWNER.upper()}
        for label, w in reasons.items():
            self.judge(f"names: {label}", ask([OUTSIDE]), f"Please send the signed paperwork by Friday: {w}.", tag=label)
        for label, w in markers.items():
            if label == "Client-safe: no":       # project-memory syntax (CLAUDE.md lines), not an internal-only marker drafts.internal_findings claims
                ctx = self.edit_ai("context", ask([OUTSIDE]))
                out = self.reply(ask([OUTSIDE]), ctx, f"Please send the signed paperwork by Friday. {w}")
                case(f"names: memory-file marker {label} (information, not claimed)", "PASS", "returned" if out.get("text") else "dropped")
                continue
            self.judge(f"names: marker {label}", ask([OUTSIDE]), f"Please send the signed paperwork by Friday. {w}", tag="an internal-only marker")
        for label, w in owner_forms.items():
            self.judge(f"names: {label}", ask([OUTSIDE]), f"{w} asks that you send the signed paperwork by Friday.", tag="a hidden item's owner")
        self.judge("names: hidden item title", ask([OUTSIDE]), f"Please send the signed paperwork by Friday and {HIDDEN_TITLE.lower()}.",
                   tag="a hidden item's title")
        # a followed person's word, in the selection and in the reply, in many spellings
        for sp in ("VIP", "vip", "V.I.P.", "V-I-P", "V_I_P", "V. I. P.", "ＶＩＰ", "VIPs", "V​IP", "VІP", "ⅤIP", "v.i.p.s"):
            self.judge(f"names: followed-person word {sp!r} in the reply", ask([OUTSIDE]),
                       f"Please send the signed paperwork by Friday; the {sp} contact is waiting.", tag="the word VIP")
            self.judge(f"names: followed-person word {sp!r} in the selection", ask([OUTSIDE], text=f"{sp} contact: {TEXT}"),
                       "Please send the signed paperwork by Friday.", tag="a reply to a selection holding the word VIP")

    def test_spoof(self):
        if not self.need():
            return
        spoofs = [
            ['"sam.patel@brightwater.example" <jane@client.example>'], ["sam.patel@brightwater.example <jane@client.example>"],
            ["Jane <jane@client.example> sam@brightwater.example"], ["x@client.example\nSam <sam@brightwater.example>"],
            ["Sam (x@client.example) <sam@brightwater.example>"], ["Sam\x00 <sam@brightwater.example>"],
            ["Sam\r\nBcc: x@client.example <sam@brightwater.example>"], ["undisclosed-recipients:;"], ["Team: sam@brightwater.example;"],
            ["jane@mail.brightwater.example"], ["jane@brightwater.example.client.example"], ["jane@brightwater-example.com"],
            ["jane@xn--brghtwater-l7a.example"], ["jane@brіghtwater.example"], ["jane@бrightwater.example"],
            ["jane＠brightwater.example"], ["jane@brightwater.example."], ["jane@client.example@brightwater.example"],
            ["sam@brightwater.example, jane@client.example"], ["sam@brightwater.example; jane@client.example"], [INSIDE, OUTSIDE],
            [INSIDE, ""], ["sam@brightwater.example,"], ["brightwater.example"], ["sam@brightwater"], "sam@brightwater.example",
            [INSIDE, 7], [INSIDE, None], [INSIDE, ["x@client.example"]], [INSIDE, {"a": 1}], [INSIDE] * 51, ["a" * 400 + "@brightwater.example"],
            {"0": INSIDE}, 42, True, [], [""], None, ["sam@brightwater.example​"], ["sam@brightwater.example , jane@client.example"],
            ["sam@brightwater.example%0a"], ["<sam@brightwater.example><jane@client.example>"], ["sam@brightwater.example <sam@brightwater.example>"],
            ["Sam <sam@brightwater.example> <jane@client.example>"], ["sam@brightwater.example\\, jane@client.example"],
        ]
        for r in spoofs:
            name = f"spoof: recipients {json.dumps(r, ensure_ascii=True)[:70]}"
            req = ask(r) if r is not None else ask()
            self.judge(name, req, "ABC-A-004 is late; please send the signed paperwork by Friday.", tag="a hidden ID after an address spoof")
        # settings: no own domains, a non-list, a list of non-strings (all outside), and a request that names its own domains (ignored)
        for label, mut in (("own_domains missing", lambda d: d["identity"].pop("own_domains", None)),
                           ("own_domains a string", lambda d: d["identity"].__setitem__("own_domains", "brightwater.example")),
                           ("own_domains [1]", lambda d: d["identity"].__setitem__("own_domains", [1])),
                           ("own_domains []", lambda d: d["identity"].__setitem__("own_domains", []))):
            undo = self.settings(mut)
            try:
                self.judge(f"spoof: settings {label}", ask([INSIDE]), "ABC-A-004 is late; please send the signed paperwork by Friday.",
                           tag="a hidden ID with no usable own domain")
            finally:
                undo()
        for key in ("own_domains", "ownDomains", "domains", "identity", "audience", "outside", "internal"):
            val = {"own_domains": ["client.example"]} if key == "identity" else (False if key in ("outside",) else ["client.example"])
            self.judge(f"spoof: page-sent {key}", ask([OUTSIDE], **{key: val}), "ABC-A-004 is late; please send the signed paperwork by Friday.",
                       tag="a hidden ID after a page-sent key")
        # controls: plain inside addresses keep the full facts (not a leak either way)
        for r in ([INSIDE], ["Sam Patel <sam.patel@brightwater.example>"], ["SAM@BrightWater.Example"], ["  sam@brightwater.example  "]):
            ctx = self.edit_ai("context", ask(r))
            case(f"spoof control: inside {r[0]!r}", "PASS" if "refused" not in ctx else "CTRL-FAIL",
                 "full facts, as before" if "refused" not in ctx else ctx["refused"][:100])

    def test_keys(self):
        live = self.root / "system/scripts/live_server.py"
        if "def edit_ai_caps_route" not in live.read_text(encoding="utf-8"):
            case("keys: the /api/edit/ai route", "SKIP", "the tree has no #186 route and no live_server.diff to apply to a copy")
            return
        reqs = [ask([INSIDE]), ask([OUTSIDE], outside=False), ask([OUTSIDE], outside=True), ask([OUTSIDE], field="client_message"),
                ask([OUTSIDE], field="email"), ask([OUTSIDE], outside="false"), ask([OUTSIDE], audience="internal"),
                ask([OUTSIDE], own_domains=["client.example"]), ask([OUTSIDE], internal=True), ask([OUTSIDE], recipients_ok=True),
                ask([OUTSIDE], Outside=False), ask([OUTSIDE], **{"outside ": False}), ask([OUTSIDE], document={"kind": "client", "code": "ABC",
                "week_ending": "2026-10-09", "client": "", "outside": False}), {**ask([OUTSIDE]), "place": "plain"},
                {**ask([OUTSIDE]), "place": "client_message"}, ask("x@y.example"), ask([INSIDE] * 51), ask([INSIDE, 7]), ask(["a" * 321 + "@b.example"])]
        code = r'''
import json, sys
sys.path.insert(0, "system/scripts")
import live_server
class H:
    def send(self, code, body):
        return [code, body]
given = json.loads(sys.stdin.read())
out = []
for req in given:
    body = live_server.edit_ai_request(req)
    out.append({"body_keys": sorted(body) if isinstance(body, dict) else None, "recipients": body.get("recipients") if isinstance(body, dict) else None,
                "route": live_server.edit_ai_route(H(), req)[0] if body is None else None})
print(json.dumps(out))
'''
        r = subprocess.run([sys.executable, "-c", code], input=json.dumps(reqs), cwd=self.root, capture_output=True, text=True, timeout=120,
                           env={**os.environ, "CREAITE_NO_LAUNCH": "1"})
        if r.returncode:
            raise RuntimeError("live_server import failed: " + r.stderr[-300:])
        out = json.loads(r.stdout.strip().splitlines()[-1])
        for i, (req, o) in enumerate(zip(reqs, out)):
            extra = sorted(set(req) - {"option", "text", "code", "place", "recipients", "instruction", "document"})
            label = f"keys: {i} extra={extra or '-'} place={req.get('place')} recipients={type(req.get('recipients')).__name__}"
            accepted = o["body_keys"] is not None
            if i == 0:                                   # the control: a plain Draft email request is taken
                case(label, "PASS" if accepted else "CTRL-FAIL", "taken, as it should" if accepted else f"refused: {o['route']}")
            elif accepted:
                case(label, "LEAK", f"the route accepted the request and passes {o['body_keys']} on")
            else:
                case(label, "HELD", f"a {o['route']} from the route")
        if not self.diff_applied:
            case("keys: the route was in the tree", "PASS", "no diff was needed")
        else:
            case("keys: the route came from live_server.diff applied to the vault's copy", "PASS", "the checkout was not edited")

    def test_place(self):
        if not self.need():
            return
        hid = "ABC-A-004 is late, so please send the signed paperwork by Friday."
        # the client_message field: client facts, the reply checked from the request; addresses with it are refused
        base = {"option": "rewrite", "text": TEXT, "code": "ABC", "place": "client_message"}
        ctx = self.edit_ai("context", base)
        case("place: client_message prompt holds only client facts", "LEAK" if self.prompt_leaks(ctx) else "PASS",
             f"holds {self.prompt_leaks(ctx)[:3]}" if self.prompt_leaks(ctx) else "no hidden ID, owner or reason")
        for label, w in (("hidden ID", hid), ("health reason", REASON), ("owner", f"{OWNER} will send it."), ("marker", "Internal only: send it."),
                         ("VIP", "The VIP contact needs it."), ("en-dash ID", hid.replace("-", "–"))):
            out = self.reply(base, ctx, w)
            case(f"place: client_message reply with {label}", "LEAK" if out.get("text") else "HELD", (out.get("message") or "dropped")[:100])
        c2 = self.edit_ai("context", {**base, "recipients": [OUTSIDE]})
        case("place: client_message with addresses", "HELD" if "refused" in c2 else "LEAK", str(c2.get("refused") or c2.get("prompt", ""))[:100])
        # an email context reused for the client_message place (and the reverse): the result decides again from the request
        inside = self.edit_ai("context", ask([INSIDE]))
        out = self.reply({**ask([INSIDE]), "place": "client_message"}, inside, hid)
        case("place: an inside-email context reused for client_message", "LEAK" if out.get("text") else "HELD", (out.get("message") or "dropped")[:100])
        outside = self.edit_ai("context", ask([OUTSIDE]))
        out = self.reply(ask([INSIDE]), dict(outside, outside=False), hid)
        case("place: an outside context says inside, the request names an inside address", "PASS", "an inside recipient keeps the full facts: " +
             ("returned" if out.get("text") else "dropped"))
        out = self.reply(ask([OUTSIDE]), dict(outside, outside=False, place="notes"), hid)
        case("place: context place rewritten to notes, request still outside", "LEAK" if out.get("text") else "HELD", (out.get("message") or "dropped")[:100])
        out = self.reply({**ask([OUTSIDE]), "place": "notes"}, dict(outside, outside=False, place="notes"), hid)
        case("place: request and context both say notes (a different place)", "PASS", "not an email any more: " + ("returned" if out.get("text") else "dropped"))
        # place spellings: only the exact word 'email' is the email place; nothing else may pick up the full facts and an outside address
        for sp in ("Email", " email", "email ", "EMAIL", "email\x00", "e-mail", "emaıl", "client", "client_message ", "Client_message"):
            c3 = self.edit_ai("context", {**ask([OUTSIDE]), "place": sp})
            name = f"place: spelling {sp!r} with an outside address"
            if "refused" in c3:
                case(name, "HELD", c3["refused"][:90])
            else:
                case(name, "LEAK" if self.prompt_leaks(c3) else "PASS", f"prompt holds {self.prompt_leaks(c3)[:3]}" if self.prompt_leaks(c3) else "client facts only")
        # a minutes sheet: the full facts, but a reply that ADDS a hidden item is dropped; the word VIP too
        mb = {"option": "shorter", "text": TEXT, "code": "ABC", "place": "minutes"}
        mctx = self.edit_ai("context", mb)
        for label, w in (("hidden ID", hid), ("VIP", "The VIP contact needs it."), ("reason", REASON), ("en-dash ID", hid.replace("-", "–"))):
            out = self.reply(mb, mctx, w)
            case(f"place: minutes reply with {label}", "LEAK" if out.get("text") else "HELD", (out.get("message") or "dropped")[:100])


if __name__ == "__main__":
    test = {"ids": "test_ids", "names": "test_names", "spoof": "test_spoof", "keys": "test_keys", "place": "test_place"}[VARIANT]
    unittest.main(argv=["x", f"P.{test}"], verbosity=0)
