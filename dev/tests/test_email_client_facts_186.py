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
    "display-name": ("edit_ai.py", "the address is taken from anywhere in the entry (the display name too)",
                     "    m = re.fullmatch(r\"[^<>]*<([^<>]*)>\", s)\n",
                     "    m = re.search(r\"(\\S+@\\S+?)[\\s>\\\"]\", s + \" \")\n"),
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
    "server-cut": ("live_server.py", "the live server cuts a long list instead of refusing it",
                   "len(rc) > 50 or any(", "False or any("),
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
for req in json.loads(sys.stdin.read()):
    out.append(live_server.edit_ai_request(req))
caps = live_server.DRAFT_ROUTES.get("/api/edit/ai/caps")
class H:
    def send(self, code, body):
        return [code, body]
print(json.dumps({"bodies": out, "caps": caps(H(), {}) if caps else None}))
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
        self.assertEqual(out["caps"], [200, {"ok": True, "email_audience": "recipients"}])


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


if __name__ == "__main__":
    unittest.main()
