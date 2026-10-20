"""#186: the Draft email's AI bar on client facts and client checks for an outside recipient. PROPOSAL tests: they run against a
patched scratch copy.

Run: python3 dev/tests/test_email_client_facts_186.py                (quick tier; the browser class needs Google Chrome)
Fail-first: EMAIL_186_UNPATCHED=1 python3 dev/tests/test_email_client_facts_186.py   (the scratch copy is left without the
            proposal's patch: the outside-recipient tests go red, the internal-recipient and page tests stay green)
Mutations:  EMAIL_186_MUTATE=<name> python3 dev/tests/test_email_client_facts_186.py   (one hunk of the patch reverted or broken; see
            MUTATIONS; each must turn a test red)

`system/scripts/edit_ai.py` (guarded-adjacent) and `live_server.py` are not changed on this branch: the fix is the proposal
dev/proposals/draft-email-client-facts/edit_ai.diff, for Alan to approve and apply. Each test vault gets its own copy of
`system/scripts/` (test_tracker.make_vault) and the diff is applied there with `patch -p0`; edit_ai.py runs in that copy in a
subprocess, as the live server runs it. After Alan applies the diff to the repo the copy is already patched (the marker
`def email_outside` is found) and the same tests keep guarding it; the unpatched copy is then made with `patch -R`.

What it proves (test_reports' fictional ABC fixture: ABC-A-002, ABC-A-003 and ABC-006 are client-visible; ABC-A-001, ABC-A-004,
ABC-005 and ABC-M-001 are not; Omar Ali owns only an internal item; the own domain is brightwater.example):
- an outside recipient: the prompt holds no internal item ID and no owner, and selected text holding an internal item (in any
  spelling) is refused before Claude;
- a hostile reply (an internal ID in any spelling, an internal owner, the health reason, an internal-only marker) is dropped with a
  plain reason, for an outside recipient; an internal recipient still gets the full facts and the reply as before;
- the server decides who is outside from the addresses only: a display name, upper case, a subdomain, a look-alike or punycode
  domain, `+tag`, a comma or semicolon list, a list with one outside, an empty or missing address, no own domains, and an `outside`
  the page sends (ignored by edit_ai.py, a 400 at the live server);
- the live server passes `recipients` through whole (never cut), refuses a malformed list, and answers /api/edit/ai/caps;
- the page (browser): with the patched server the bar is on for an outside recipient, the request carries the addresses, and a
  hostile reply shows the plain reason; with an unpatched server the bar stays off for an outside recipient (test_editor_plain).
Claude is never called: edit_ai.py's context and result run on their own, and the browser uses a stand-in.
"""
import json
import os
import sqlite3
import subprocess
import sys
import unittest
from contextlib import closing
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_reports as R  # noqa: E402  (its fixture: populate, ReportVault)

REPO = HERE.parents[1]
DIFF = Path(os.environ.get("EMAIL_186_DIFF") or REPO / "dev" / "proposals" / "draft-email-client-facts" / "edit_ai.diff")
UNPATCHED = os.environ.get("EMAIL_186_UNPATCHED") == "1"
MUTATE = os.environ.get("EMAIL_186_MUTATE", "")
MARKER = "def email_outside"
REASON = "the vendor contract dispute is still unresolved with procurement"   # the tracker's internal health reason (fictional)
CLIENT_IDS = ("ABC-A-002", "ABC-A-003")
INTERNAL_IDS = ("ABC-A-001", "ABC-A-004", "ABC-005", "ABC-M-001")
OWNERS = ("Omar Ali", "Jane Doe")
INSIDE = "sam.patel@brightwater.example"
OUTSIDE = "jane.doe@client.example"
TEXT = "Please send the signed paperwork by Friday so we can plan the next step."

# One text change per mutation, made on the patched copy: (file, what it breaks, old text, new text)
MUTATIONS = {
    "no-reply-check": ("edit_ai.py", "the reply is checked for the client place only again",
                       "if ctx.get(\"place\") in CLIENT_PLACES or outside else []", "if ctx.get(\"place\") in CLIENT_PLACES else []"),
    "no-input-check": ("edit_ai.py", "the selected text is not checked for an outside email",
                       "bad = client_problems(code, text, text) if client or outside else []",
                       "bad = client_problems(code, text, text) if client else []"),
    "full-facts": ("edit_ai.py", "an outside email gets the full facts", "facts = project_facts(code, client or outside)",
                   "facts = project_facts(code, client)"),
    "trust-flag": ("edit_ai.py", "the page's `outside` is believed",
                   "    given = req.get(\"recipients\") if isinstance(req, dict) else None\n",
                   "    if isinstance(req, dict) and \"outside\" in req:\n        return bool(req[\"outside\"])\n"
                   "    given = req.get(\"recipients\") if isinstance(req, dict) else None\n"),
    "any-inside": ("edit_ai.py", "one inside address is enough", "return not all(address_inside(b, own) for b in parts)",
                   "return not any(address_inside(b, own) for b in parts)"),
    "subdomain": ("edit_ai.py", "a subdomain of an own domain counts as inside", "return bool(m) and m.group(1).lower() in own",
                  "return bool(m) and any(m.group(1).lower() == d or m.group(1).lower().endswith('.' + d) for d in own)"),
    # (round 2: "display-name" is now name-any, name-at and name-ws below)
    "no-split": ("edit_ai.py", "a comma list is read as one address", "bits = re.split(r\"[,;]\", r)", "bits = [r]"),
    "empty-ok": ("edit_ai.py", "an empty address is skipped", "if any(not b.strip() for b in bits):\n            return True",
                 "bits = [b for b in bits if b.strip()]\n        if False:\n            return True"),
    "no-own-inside": ("edit_ai.py", "no own domains reads every address as inside", "    if not own:\n        return True\n",
                      "    if not own:\n        return False\n"),
    "no-recheck": ("edit_ai.py", "result() trusts the context's flag only",
                   "outside = bool(ctx.get(\"outside\")) or (ctx.get(\"place\") in EMAIL_PLACES and "
                   "email_outside(body.get(\"request\") or {}))", "outside = bool(ctx.get(\"outside\"))"),
    # (not a mutation: dropping `if not s.isascii()` changes nothing, the ADDRESS pattern is ASCII-only too; the check says it plainly)
    "server-flag": ("live_server.py", "the live server lets an `outside` key through",
                    "\"document\", \"recipients\"}", "\"document\", \"recipients\", \"outside\"}"),
    "server-cut": ("live_server.py", "the live server takes a list of more than 50", "    if len(rc) > 50:\n", "    if False:\n"),
    # round 2 (the review of bba13f74)
    "place-any": ("edit_ai.py", "addresses with another place get that place's full facts",
                  "if \"recipients\" in req and place not in EMAIL_PLACES:", "if False:"),
    "server-place": ("live_server.py", "the live server lets addresses through with another place",
                     "    if str(req.get(\"place\") or \"\") != \"email\":\n", "    if False:\n"),
    "name-any": ("edit_ai.py", "a display name may hold anything", "if not DISPLAY_NAME.fullmatch(m.group(1)):", "if False:"),
    "name-at": ("edit_ai.py", "a display name may hold an @ or brackets", "DISPLAY_NAME = re.compile(r\"[A-Za-z0-9 .,'\\\"\\-_&]*\")",
                "DISPLAY_NAME = re.compile(r\"[^<>\\n\\t]*\")"),
    "name-ws": ("edit_ai.py", "a display name may hold a line break or tab", "DISPLAY_NAME = re.compile(r\"[A-Za-z0-9 .,'\\\"\\-_&]*\")",
                "DISPLAY_NAME = re.compile(r\"[A-Za-z0-9 .,'\\\"\\-_&\\s]*\")"),
    "plain-message": ("live_server.py", "a refused list gets the generic message",
                      "        return handler.send(400, {\"ok\": False, \"message\": why or ", "        return handler.send(400, {\"ok\": False, \"message\": None or "),
    "no-domains-log": ("edit_ai.py", "a setting that isn't a list says nothing", "        _log_warn(\"identity.own_domains is not a list", "        (\"identity.own_domains is not a list"),
    "caps-state": ("live_server.py", "caps doesn't say the setting isn't a list", "return \"ok\" if isinstance(given, list) else \"not a list\"",
                   "return \"ok\""),
}


def patched_vault():
    """test_reports' vault with the health reason set, its scripts patched (or not) as the run asks."""
    v = R.ReportVault()
    R.populate(v)
    with closing(sqlite3.connect(v.root / "system" / "tracker.db")) as con:
        con.execute("UPDATE projects SET health = 'At risk', health_reason = ? WHERE code = 'ABC'", (REASON,))
        con.commit()
    prepare(v.root)
    return v


def prepare(root):
    """Patch (or unpatch) and mutate the vault's copy of the scripts."""
    scripts = root / "system" / "scripts"
    has = MARKER in (scripts / "edit_ai.py").read_text(encoding="utf-8")
    if has == UNPATCHED:                                  # apply the proposal, or take it out of an applied repo's copy
        r = subprocess.run(["patch", "-p0", "-s", "-d", str(root), *(["-R"] if has else []), "-i", str(DIFF)],
                           capture_output=True, text=True)
        if r.returncode:
            raise AssertionError(f"patch failed:\n{r.stdout}{r.stderr}")
    if MUTATE and not UNPATCHED:
        f, _why, old, new = MUTATIONS[MUTATE]
        p = scripts / f
        s = p.read_text(encoding="utf-8")
        assert s.count(old) == 1, f"mutation {MUTATE}: its text isn't in {f} exactly once"
        p.write_text(s.replace(old, new), encoding="utf-8")


def edit_ai(root, cmd, body):
    r = subprocess.run([sys.executable, str(root / "system/scripts/edit_ai.py"), cmd], input=json.dumps(body), cwd=root,
                       capture_output=True, text=True, timeout=120)
    if r.returncode:
        raise AssertionError(f"edit_ai.py {cmd} failed:\n{r.stdout}{r.stderr}")
    return json.loads(r.stdout)


SERVER = r'''
import json, sys
sys.path.insert(0, "system/scripts")
import live_server
out = []
given = json.loads(sys.stdin.read())
for req in given:
    out.append(live_server.edit_ai_request(req))
sys.argv[1:] = [json.dumps(given)]
caps = live_server.DRAFT_ROUTES.get("/api/edit/ai/caps")
class H:
    def send(self, code, body):
        return [code, body]
reqs = json.loads(sys.argv[1]) if len(sys.argv) > 1 else []
print(json.dumps({"bodies": out, "caps": caps(H(), {}) if caps else None,
                  "routes": [live_server.edit_ai_route(H(), r) if live_server.edit_ai_request(r) is None else None for r in reqs]}))
'''


def server(root, reqs):
    r = subprocess.run([sys.executable, "-c", SERVER], input=json.dumps(reqs), cwd=root, capture_output=True, text=True,
                       timeout=120, env={**os.environ, "CREAITE_NO_LAUNCH": "1"})
    if r.returncode:
        raise AssertionError(f"live_server import failed:\n{r.stdout}{r.stderr}")
    return json.loads(r.stdout.strip().splitlines()[-1])


def ask(recipients=None, text=TEXT, option="rewrite", **extra):
    body = {"option": option, "text": text, "code": "ABC", "place": "email", **extra}
    if recipients is not None:
        body["recipients"] = recipients
    return body


class _Vault(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = patched_vault()
        cls.root = cls.v.root

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def context(self, body):
        return edit_ai(self.root, "context", body)

    def assertClientFacts(self, ctx, why=""):
        self.assertNotIn("refused", ctx, why)
        p = ctx["prompt"]
        for i in INTERNAL_IDS:
            self.assertNotIn(i, p, f"{why}: internal {i} in the prompt")
        for n in OWNERS:
            self.assertNotIn(n, p, f"{why}: owner {n} in the prompt")
        self.assertNotIn(REASON, p, why)
        self.assertIn("Its people: none listed", p, why)
        for i in CLIENT_IDS:
            self.assertIn(i, p, why)

    def assertFullFacts(self, ctx, why=""):
        self.assertNotIn("refused", ctx, why)
        p = ctx["prompt"]
        for i in INTERNAL_IDS[:3] + CLIENT_IDS:
            self.assertIn(i, p, why)
        self.assertIn("Omar Ali", p, why)


class TheOutsideEmail(_Vault):
    """An outside recipient gets the client facts and the client checks."""

    def test_an_outside_recipient_gets_only_client_visible_ids_and_no_people(self):
        for opt in ("rewrite", "shorter", "longer", "formal", "warmer"):
            self.assertClientFacts(self.context(ask([OUTSIDE], option=opt)), opt)
        ctx = self.context(ask([OUTSIDE], option="custom", instruction="Mention who owns each item."))
        self.assertClientFacts(ctx, "custom")
        self.assertIn("outside Alan's company", ctx["prompt"])

    def test_no_recipients_at_all_is_outside(self):
        self.assertClientFacts(self.context(ask()), "no recipients key")
        self.assertClientFacts(self.context(ask([])), "empty list")
        self.assertClientFacts(self.context(ask([""])), "a person with no address")

    def test_selected_text_holding_something_internal_is_refused_before_claude(self):
        # an item a client may not see, however it is written (a name, the health reason or a marker Alan typed himself is his own
        # wording and goes, as on the client sheet: client_problems exempts what the original holds; the reply is checked for new ones)
        for text in ("ABC-A-004 is late; please chase.", "abc a 4 is late.", "See ABC‑005 and ABC-M-001.", "ABC/A/001 waits."):
            ctx = self.context(ask([OUTSIDE], text=text))
            self.assertIn("refused", ctx, text)
            self.assertIn("outside your company", ctx["refused"], text)

    def test_a_hostile_reply_is_dropped_with_a_plain_reason(self):
        ctx = self.context(ask([OUTSIDE]))
        for reply in ("ABC-A-004 is late, so please send the signed paperwork by Friday.",
                      "Please send the signed paperwork (see ABC‑A‑004) by Friday.",
                      "Please send the signed paperwork by Friday; abc a 4 waits on it.",
                      "Please send the signed paperwork by Friday. ABC-005 is the risk.",
                      "Omar Ali asks that you send the signed paperwork by Friday.",
                      "Please send the signed paperwork by Friday: " + REASON + ".",
                      "Internal only: please send the signed paperwork by Friday."):
            out = edit_ai(self.root, "result", {"request": ask([OUTSIDE]), "context": ctx,
                                                "reply": f"<<<SUGGESTION\n{reply}\nSUGGESTION>>>"})
            self.assertEqual(out["text"], "", reply)
            self.assertIn("shouldn't go outside your company", out.get("message", ""), reply)

    def test_a_safe_reply_comes_back(self):
        ctx = self.context(ask([OUTSIDE]))
        out = edit_ai(self.root, "result", {"request": ask([OUTSIDE]), "context": ctx,
                                            "reply": "<<<SUGGESTION\nCould you send the signed paperwork by Friday? ABC-A-002 waits "
                                                     "on it.\nSUGGESTION>>>"})
        self.assertIn("signed paperwork", out["text"])

    def test_result_decides_again_from_the_request_whatever_the_context_says(self):
        ctx = dict(self.context(ask([INSIDE])), outside=False)       # a context that says inside
        out = edit_ai(self.root, "result", {"request": ask([OUTSIDE]), "context": ctx,
                                            "reply": "<<<SUGGESTION\nABC-A-004 is late.\nSUGGESTION>>>"})
        self.assertEqual(out["text"], "")

    def test_the_page_saying_inside_is_ignored(self):
        self.assertClientFacts(self.context(ask([OUTSIDE], outside=False)), "outside:false")
        self.assertClientFacts(self.context(ask(outside=False)), "outside:false, no recipients")
        self.assertClientFacts(self.context(ask([OUTSIDE], audience="internal")), "audience")


class TheInternalEmail(_Vault):
    """An email whose every recipient is on an own domain is unchanged: the full facts, the reply as before."""

    def test_an_internal_recipient_still_gets_the_full_facts(self):
        for r in ([INSIDE], [INSIDE, "lee@brightwater.example"], ["SAM.PATEL@BRIGHTWATER.EXAMPLE"], ["sam+chase@brightwater.example"],
                  ["Sam Patel <sam.patel@brightwater.example>"], ["sam@brightwater.example, lee@brightwater.example"],
                  ["  sam@BrightWater.Example  "]):
            ctx = self.context(ask(r))
            self.assertFullFacts(ctx, repr(r))
            self.assertNotIn("outside Alan's company", ctx["prompt"], repr(r))

    def test_an_internal_reply_with_an_internal_id_comes_back(self):
        ctx = self.context(ask([INSIDE]))
        out = edit_ai(self.root, "result", {"request": ask([INSIDE]), "context": ctx,
                                            "reply": "<<<SUGGESTION\nABC-A-004 is late; Omar Ali will chase.\nSUGGESTION>>>"})
        self.assertIn("ABC-A-004", out["text"])


class TheAddresses(_Vault):
    """Who is outside is the server's, from the addresses: every one of these is outside."""

    SPOOFS = [
        ['"sam.patel@brightwater.example" <jane@client.example>'],      # the display name says inside, the address isn't
        ["sam.patel@brightwater.example <jane@client.example>"],
        ["Jane <jane@client.example> sam@brightwater.example"],        # text after the brackets: not one address
        # round 2: a display name holding another address, a line break, a tab, brackets or group syntax
        ["x@client.example\nSam <sam@brightwater.example>"],
        ["x@client.example\tSam <sam@brightwater.example>"],
        ["x@client.example Sam <sam@brightwater.example>"],
        ["Sam (x@client.example) <sam@brightwater.example>"],
        ["Sam (client) <sam@brightwater.example>"],
        ["Sam\x00 <sam@brightwater.example>"],
        ["Sam\nPatel <sam@brightwater.example>"],                     # a line break or tab in the name alone: refused too
        ["Sam\tPatel <sam@brightwater.example>"],
        ["Sam\r\nBcc: x@client.example <sam@brightwater.example>"],
        ["undisclosed-recipients:;"],
        ["Team: sam@brightwater.example;"],
        ["Team: sam@brightwater.example"],
        ["Team: <sam@brightwater.example>"],
        ["jane@mail.brightwater.example"],                             # a subdomain of an own domain
        ["jane@brightwater.example.client.example"],
        ["jane@brightwater-example.com"],
        ["jane@xn--brghtwater-l7a.example"],                           # punycode: another domain
        ["jane@brіghtwater.example"],                                  # a Cyrillic і
        ["jane＠brightwater.example"],                                  # a full-width @
        ["jane@brightwater.example."],                                 # a trailing dot
        ["jane@client.example@brightwater.example"],                   # two @
        ["sam@brightwater.example, jane@client.example"],               # a comma list with one outside
        ["sam@brightwater.example; jane@client.example"],
        [INSIDE, OUTSIDE],                                             # a list with one outside
        [INSIDE, ""],                                                  # an attendee with no address
        ["sam@brightwater.example,"],                                  # an empty part
        ["brightwater.example"],
        ["sam@brightwater"],
        "sam@brightwater.example",                                     # not a list
        [INSIDE, 7],                                                   # not a string
        [INSIDE] * 51,                                                 # more than the server takes
    ]

    def test_every_spoof_is_outside(self):
        for r in self.SPOOFS:
            self.assertClientFacts(self.context(ask(r)), repr(r)[:80])

    def test_display_names_of_plain_words_still_read_as_inside(self):
        for r in (["Sam Patel <sam.patel@brightwater.example>"], ['"Sam Patel" <sam.patel@brightwater.example>'],
                  ["O'Neill-Smith Jr. <sam.patel@brightwater.example>"], ["<sam.patel@brightwater.example>"]):
            self.assertFullFacts(self.context(ask(r)), repr(r))

    def test_own_domains_come_from_settings_never_the_request(self):
        for key in ("own_domains", "ownDomains", "own_email_domains", "ownEmailDomains", "domains"):
            self.assertClientFacts(self.context(ask([OUTSIDE], **{key: ["client.example"]})), key)
        self.assertClientFacts(self.context(ask([OUTSIDE], identity={"own_domains": ["client.example"]})), "identity")
        out = server(self.root, [ask([OUTSIDE], own_domains=["client.example"]), ask([OUTSIDE], ownDomains=["client.example"])])
        self.assertEqual(out["bodies"], [None, None])

    def test_a_setting_that_isnt_a_list_is_outside_and_said_in_the_log_and_caps(self):
        s = self.root / "system/config/settings.json"
        before = s.read_text(encoding="utf-8")
        self.addCleanup(s.write_text, before, encoding="utf-8")
        d = json.loads(before)
        d["identity"]["own_domains"] = "brightwater.example"
        s.write_text(json.dumps(d), encoding="utf-8")
        self.assertClientFacts(self.context(ask([INSIDE])), "own_domains as a string")
        logs = "".join(f.read_text(encoding="utf-8") for f in (self.root / "system/logs").glob("debug-*.log"))
        self.assertIn("own_domains is not a list", logs)
        self.assertNotIn("brightwater.example", logs)                    # counts and what is wrong only, never the domains
        self.assertEqual(server(self.root, [])["caps"][1]["own_domains"], "not a list")

    def test_no_own_domains_means_everyone_is_outside(self):
        s = self.root / "system/config/settings.json"
        before = s.read_text(encoding="utf-8")
        self.addCleanup(s.write_text, before, encoding="utf-8")
        d = json.loads(before)
        d["identity"]["own_domains"] = []
        s.write_text(json.dumps(d), encoding="utf-8")
        self.assertClientFacts(self.context(ask([INSIDE])), "no own domains")
        s.write_text("{not json", encoding="utf-8")
        self.assertClientFacts(self.context(ask([INSIDE])), "settings can't be read")


class TheLiveServer(_Vault):
    """live_server.edit_ai_request passes the addresses through whole and refuses anything else; the caps route answers."""

    def test_recipients_pass_through_whole_and_a_bad_list_is_refused(self):
        many = [INSIDE] * 50
        out = server(self.root, [ask([INSIDE, OUTSIDE]), ask(many), ask([INSIDE] * 51), ask([INSIDE, 7]), ask("x@y.example"),
                                 ask([INSIDE], outside=False), ask(["a" * 321 + "@brightwater.example"])])
        b = out["bodies"]
        self.assertEqual(b[0]["recipients"], [INSIDE, OUTSIDE])
        self.assertEqual(b[1]["recipients"], many)
        for i in range(2, 7):
            self.assertIsNone(b[i], i)                                 # a 400: nothing goes to edit_ai.py or Claude
        self.assertEqual(out["caps"], [200, {"ok": True, "email_audience": "recipients", "own_domains": "ok"}])

    def test_addresses_with_any_other_place_are_refused(self):
        doc = {"kind": "client", "code": "ABC", "week_ending": "2026-10-09", "client": ""}
        for place in ("plain", "notes", "line", "current", "report", "minutes", "client", "readonly"):
            for r in ([OUTSIDE], [INSIDE], []):
                body = {**ask(r, option="shorter"), "place": place, **({"document": doc} if place == "client" else {})}
                ctx = self.context(body)
                self.assertEqual(ctx.get("refused"), "Addresses go only with the Draft email, so nothing was sent to Claude.",
                                 (place, r))
        out = server(self.root, [{**ask([OUTSIDE]), "place": "plain"}, {**ask([INSIDE]), "place": "notes"}])
        self.assertEqual(out["bodies"], [None, None])
        self.assertIn("only with the Draft email", out["routes"][0][1]["message"])

    def test_a_refused_list_gets_a_plain_message(self):
        out = server(self.root, [ask([INSIDE] * 51), ask([INSIDE, 7])])
        self.assertEqual(out["routes"][0][0], 400)
        self.assertIn("too many recipients", out["routes"][0][1]["message"])
        self.assertIn("couldn't be read", out["routes"][1][1]["message"])


try:
    from live_browser import LiveBrowserCase  # noqa: E402
    import test_ai_117 as t117  # noqa: E402
except Exception:  # noqa: BLE001  no browser support here
    LiveBrowserCase = None

if LiveBrowserCase is not None:
    PREP = r"""
      S.ownDomains=["brightwater.example"]; S.me="Alan Carter";
      const mk=(id,t,due,client)=>({id,p:"ABC",t,ws:"",o:"Jane Doe",pr:"Medium",due,st:"Open",raised:"2026-09-01",closed:null,upd:"",client:!!client,cm:"",src:"x"});
      A.length=0; R.length=0; A.push(mk("ABC-A-002","Sign the statement of work","2026-10-02",true));
      REG.length=0; REG.push({name:"Jane Doe",email:%s,aliases:[],org:"",role:"",extra:{}});
      window.SENT=[]; const f0=window.__f0||(window.__f0=window.fetch); window.fetch=(u,o)=>{ if(String(u).endsWith("/api/edit/ai")) SENT.push(JSON.parse(o.body)); return f0(u,o); };
      true"""
    LAYER = "#aiLayer"

    class ThePage(LiveBrowserCase):
        """The Draft email's bar with the patched server: on for an outside recipient, the addresses sent, a hostile reply refused."""
        shared_server = True
        width, height = 1400, 900

        @classmethod
        def load(cls, v):
            R.populate(v)
            prepare(v.root)
            cls.fake = v.root / "fake_claude.py"
            cls.fake.write_text(t117.FAKE)
            cls.fake.chmod(0o755)

        @classmethod
        def server_env(cls):
            return {"CREAITE_CLAUDE": str(cls.fake)}

        def setUp(self):
            super().setUp()
            Path(str(self.fake) + ".reply").unlink(missing_ok=True)
            Path(str(self.fake) + ".prompt").unlink(missing_ok=True)

        def open_email(self, address):
            b = self.b
            b.eval(PREP % json.dumps(address))
            b.eval('openDraftEmail("Jane Doe"); true')
            b.wait("!!document.querySelector('#dePrev.ProseMirror')")
            b.pump(0.5)                                                  # the caps answer, and the rebuild it brings
            b.wait("!!document.querySelector('#dePrev.ProseMirror')")

        def select(self, words):
            b = self.b
            b.click("#dePrev")
            b.eval("""((w)=>{ const h=edOf(document.querySelector('#dePrev')); let at=-1; h.editor.state.doc.descendants((n,pos)=>{ if(at<0&&n.isText){ const i=n.text.indexOf(w); if(i>=0) at=pos+i; } });
              h.focus(); h.editor.commands.setTextSelection({from:at,to:at+w.length}); })(%s)""" % json.dumps(words))
            b.pump(0.35)

        def sparked(self):
            return bool(self.b.eval(f"!!document.querySelector('{LAYER} .aispark')"))

        def run_rewrite(self):
            b = self.b
            b.wait(f"document.querySelector('{LAYER} .aispark')")
            b.click(f"{LAYER} .aispark")
            b.wait(f"document.querySelector('{LAYER} .aibar')")
            b.click(f'{LAYER} .aibar button[data-tip="AI: improve"]')
            b.wait(f"document.querySelector('{LAYER} [role=menu]')")
            b.click(f"{LAYER} [role=menu] [data-ai=rewrite]")
            b.wait(f"document.querySelector('{LAYER} .aisug .aitext')||document.querySelector('{LAYER} .aisug [role=alert]')", 30)
            return b.eval(f"document.querySelector('{LAYER} .aisug').textContent")

        def tearDown(self):
            if self.b:
                self.b.eval("aiSug.value=null; aiBar.value=null; document.getElementById('deDlg')?.close(); true")
            super().tearDown()

        def test_outside_the_bar_is_on_the_addresses_go_and_the_prompt_is_client_only(self):
            if UNPATCHED:
                self.skipTest("the bar stays off without the proposal (test_editor_plain's interim test)")
            b = self.b
            self.open_email(OUTSIDE)
            self.assertTrue(b.eval("DE.outside"))
            self.assertTrue(b.eval("deAiSafe()"))
            self.select("I hope you")
            self.assertTrue(self.sparked(), "outside, patched server: the bar is there")
            self.reply("Please send the signed paperwork by Friday.")
            self.run_rewrite()
            self.assertEqual(b.eval("SENT.at(-1).recipients"), [OUTSIDE])
            self.assertNotIn("outside", b.eval("Object.keys(SENT.at(-1))"))   # the page's own flag is never sent
            prompt = Path(str(self.fake) + ".prompt").read_text(encoding="utf-8")
            for i in INTERNAL_IDS:
                self.assertNotIn(i, prompt)
            self.assertNotIn("Omar Ali", prompt)

        def test_outside_a_hostile_reply_shows_the_plain_reason(self):
            if UNPATCHED:
                self.skipTest("the bar stays off without the proposal")
            self.open_email(OUTSIDE)
            self.select("I hope you")
            self.reply("ABC-A-004 is late; Omar Ali will chase.")
            said = self.run_rewrite()
            self.assertIn("shouldn't go outside your company", said)
            self.assertNotIn("ABC-A-004", said)

        def test_inside_the_addresses_go_and_the_full_facts_are_kept(self):
            b = self.b
            self.open_email(INSIDE)
            self.assertFalse(b.eval("DE.outside"))
            self.select("I hope you")
            self.reply("Fine.")
            self.run_rewrite()
            prompt = Path(str(self.fake) + ".prompt").read_text(encoding="utf-8")
            self.assertIn("ABC-A-004", prompt)
            if not UNPATCHED:
                self.assertEqual(b.eval("SENT.at(-1).recipients"), [INSIDE])
            else:
                self.assertIsNone(b.eval("SENT.at(-1).recipients ?? null"))   # an older server is never sent the addresses

        def reply(self, text):
            Path(str(self.fake) + ".reply").write_text(text, encoding="utf-8")


if LiveBrowserCase is not None:
    class ThePageOldServer(LiveBrowserCase):
        """An older server (the diff not applied): /api/edit/ai/caps is a 404, so the bar stays off for an outside recipient, no
        addresses are sent, and the page asks once, not on every redraw (round 2: the no is kept a minute)."""
        shared_server = True
        width, height = 1400, 900

        @classmethod
        def load(cls, v):
            R.populate(v)
            ls = v.root / "system/scripts/edit_ai.py"
            if MARKER in ls.read_text(encoding="utf-8"):             # the repo has the diff: take it out of this vault's copy
                subprocess.run(["patch", "-p0", "-s", "-R", "-d", str(v.root), "-i", str(DIFF)], check=True)

        def test_an_old_server_keeps_the_bar_off_and_is_asked_once(self):
            b = self.b
            b.eval("""window.CAPS=0; const f1=window.__f1||(window.__f1=window.fetch); window.fetch=(u,o)=>{ if(String(u).endsWith("/api/edit/ai/caps")) CAPS++; return f1(u,o); }; true""")
            b.eval(PREP % json.dumps(OUTSIDE))
            for _ in range(4):                                           # four opens, each a redraw
                b.eval('openDraftEmail("Jane Doe"); true')
                b.wait("!!document.querySelector('#dePrev.ProseMirror')")
                b.pump(0.4)
            self.assertFalse(b.eval("deAiSafe()"))
            self.assertEqual(b.eval("CAPS"), 1)
            b.click("#dePrev")
            b.key("a", 4)
            b.pump(0.4)
            self.assertFalse(b.eval(f"!!document.querySelector('{LAYER} .aispark')"), "an old server: no bar for an outside email")
            b.eval("document.getElementById('deDlg')?.close(); true")


if __name__ == "__main__":
    unittest.main()
