"""#263: the item panel's Client messaging field gets the client rules for AI on selected text. PROPOSAL tests: they run against a
patched scratch copy (the #186 diff, then this one).

Run: python3 dev/tests/test_client_messaging_263.py                (quick tier; the browser classes need Google Chrome)
Fail-first: CM_263_UNPATCHED=1 python3 dev/tests/test_client_messaging_263.py   (the copy gets #186 only: the client-field tests go
            red, the plain-field controls stay green)
Mutations:  CM_263_MUTATE=<name> python3 dev/tests/test_client_messaging_263.py   (one piece of the diff broken; see MUTATIONS)

`edit_ai.py` and `live_server.py` are not changed on this branch: the fix is dev/proposals/client-messaging-263/edit_ai.diff, which
applies on top of #186's dev/proposals/draft-email-client-facts/edit_ai.diff (`patch -p0`, #186 first). Each test vault gets its own
copy of `system/scripts/`, and both diffs are applied there (a diff already in the copy is left; with CM_263_UNPATCHED=1 this one is
taken out with `patch -R`).

What it proves (test_reports' fictional ABC fixture, as test_email_client_facts_186):
- a request naming `field: "client_message"` with the plain place gets the client facts (client-visible items only, no people) and
  the client rule; the selected text holding an internal item is refused; a reply bringing in an internal item, an internal owner,
  the health reason or an internal-only marker is dropped; result() decides again from the request;
- the field with any other place, or any other field name, is refused before Claude; the plain place without a field is unchanged
  (full facts: the other item fields);
- the live server passes `field` through (text of 40 characters at most) and /api/edit/ai/caps lists it in `client_fields`;
- the page: the Client messaging field has no bar until the server lists the field; then the request names it. The other longer fields
  keep their bar.
"""
import os
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_email_client_facts_186 as E  # noqa: E402  (its vault, its #186 patching and its helpers)
import test_reports as R  # noqa: E402

REPO = HERE.parents[1]
DIFF = Path(os.environ.get("CM_263_DIFF") or REPO / "dev" / "proposals" / "client-messaging-263" / "edit_ai.diff")
UNPATCHED = os.environ.get("CM_263_UNPATCHED") == "1"
MUTATE = os.environ.get("CM_263_MUTATE", "")
MARKER = "CLIENT_FIELDS = {"
REFUSED = "That field isn't one creaite can check, so nothing was sent to Claude."

MUTATIONS = {   # (file, what it breaks, old text, new text)
    "no-client-rules": ("edit_ai.py", "the field doesn't get the client rules in context()",
                        "client = place in CLIENT_PLACES or client_field(req, place)", "client = place in CLIENT_PLACES"),
    "no-reply-check": ("edit_ai.py", "the reply isn't checked for the field",
                       "    return ctx.get(\"place\") in CLIENT_PLACES or bool(ctx.get(\"client\")) or \"field\" in req\n",
                       "    return ctx.get(\"place\") in CLIENT_PLACES\n"),
    "ctx-only": ("edit_ai.py", "result() believes the context only",
                 "    return ctx.get(\"place\") in CLIENT_PLACES or bool(ctx.get(\"client\")) or \"field\" in req\n",
                 "    return ctx.get(\"place\") in CLIENT_PLACES or bool(ctx.get(\"client\"))\n"),
    "any-place": ("edit_ai.py", "the field may come with any place",
                  "if req.get(\"field\") not in CLIENT_FIELDS or CLIENT_FIELDS[req.get(\"field\")] != place:",
                  "if req.get(\"field\") not in CLIENT_FIELDS:"),
    "any-field": ("edit_ai.py", "an unknown field is let through as a plain request",
                  "    if req.get(\"field\") not in CLIENT_FIELDS or CLIENT_FIELDS[req.get(\"field\")] != place:\n        raise Refused(NOT_FIELD)\n",
                  "    if req.get(\"field\") not in CLIENT_FIELDS:\n        return False\n    if CLIENT_FIELDS[req.get(\"field\")] != place:\n"
                  "        raise Refused(NOT_FIELD)\n"),
    "server-drops-field": ("live_server.py", "the live server drops the field", "        body[\"field\"] = req[\"field\"]\n", ""),
    "server-no-key": ("live_server.py", "the live server refuses the field key", "\"recipients\", \"field\"}", "\"recipients\"}"),
    "caps-silent": ("live_server.py", "caps doesn't list the field", "\"client_fields\": [\"client_message\"]", "\"client_fields\": []"),
}


def prepare(root):
    """#186 is already in the copy (E.patched_vault); add (or take out) this diff, then mutate."""
    scripts = root / "system" / "scripts"
    has = MARKER in (scripts / "edit_ai.py").read_text(encoding="utf-8")
    if has == UNPATCHED:
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


def ask(text=E.TEXT, option="rewrite", place="plain", **extra):
    return {"option": option, "text": text, "code": "ABC", "place": place, "field": "client_message", **extra}


class _Vault(E._Vault):
    @classmethod
    def setUpClass(cls):
        cls.v = E.patched_vault()
        cls.root = cls.v.root
        prepare(cls.root)

    def assertClientRules(self, ctx, why=""):
        """Client facts and the client rule. The facts are read from "The project:" on: Make it executive's style guide carries a
        fictional example with item IDs of its own, which is the guide, not the tracker's facts."""
        self.assertNotIn("refused", ctx, why)
        facts = ctx["prompt"].split("\nThe project:", 1)[1]
        for i in E.INTERNAL_IDS:
            self.assertNotIn(i, facts, f"{why}: internal {i} in the facts")
        for n in E.OWNERS:
            self.assertNotIn(n, ctx["prompt"], f"{why}: owner {n} in the prompt")
        self.assertIn("Its people: none listed", facts, why)
        for i in E.CLIENT_IDS:
            self.assertIn(i, facts, why)
        self.assertIn("This text is for the client.", ctx["prompt"], why)


class TheField(_Vault):
    """The Client messaging field gets the client facts and checks."""

    def test_the_field_gets_client_facts_and_the_client_rule(self):
        for opt in ("rewrite", "shorter", "executive"):
            self.assertClientRules(self.context(ask(option=opt)), opt)
        self.assertClientRules(self.context(ask(option="custom", instruction="Name who owns each item.")), "custom")

    def test_selected_text_holding_an_internal_item_is_refused(self):
        for text in ("ABC-A-004 is late.", "abc a 4 is late.", "See ABC-005."):
            self.assertIn("isn't client-safe", self.context(ask(text=text)).get("refused", ""), text)

    def test_a_hostile_reply_is_dropped(self):
        ctx = self.context(ask())
        for reply in ("ABC-A-004 is late, so please send the signed paperwork by Friday.",
                      "Omar Ali asks that you send the signed paperwork by Friday.",
                      "Please send the signed paperwork by Friday: " + E.REASON + ".",
                      "Internal only: please send the signed paperwork by Friday."):
            out = E.edit_ai(self.root, "result", {"request": ask(), "context": ctx,
                                                  "reply": f"<<<SUGGESTION\n{reply}\nSUGGESTION>>>"})
            self.assertEqual(out["text"], "", reply)
            self.assertIn("isn't client-safe", out.get("message", ""), reply)

    def test_a_safe_reply_comes_back(self):
        out = E.edit_ai(self.root, "result", {"request": ask(), "context": self.context(ask()),
                                              "reply": "<<<SUGGESTION\nPlease send the signed paperwork by Friday.\nSUGGESTION>>>"})
        self.assertIn("signed paperwork", out["text"])

    def test_result_decides_again_from_the_request(self):
        ctx = self.context({k: v for k, v in ask().items() if k != "field"})   # a context made without the field
        out = E.edit_ai(self.root, "result", {"request": ask(), "context": ctx,
                                              "reply": "<<<SUGGESTION\nABC-A-004 is late.\nSUGGESTION>>>"})
        self.assertEqual(out["text"], "")


class TheBinding(_Vault):
    """The field comes only with its own place; anything else is refused; the plain place without it is unchanged."""

    def test_the_field_with_any_other_place_is_refused(self):
        doc = {"kind": "client", "code": "ABC", "week_ending": "2026-10-09", "client": ""}
        for place in ("line", "notes", "current", "report", "minutes", "readonly", "client", "email"):
            body = ask(option="shorter", place=place, **({"document": doc} if place == "client" else {}))
            self.assertEqual(self.context(body).get("refused"), REFUSED, place)

    def test_any_other_field_name_is_refused(self):
        for field in ("cm", "cmd", "Client_Message", "client_message ", "", "description", "notes"):
            self.assertEqual(self.context(ask(field=field)).get("refused"), REFUSED, repr(field))

    def test_the_plain_place_without_a_field_is_unchanged(self):
        body = {k: v for k, v in ask().items() if k != "field"}
        self.assertFullFacts(self.context(body), "plain")
        self.assertNotIn("This text is for the client.", self.context(body)["prompt"])

    def test_the_live_server_passes_the_field_and_caps_lists_it(self):
        out = E.server(self.root, [ask(), ask(field=7), ask(field="x" * 41)])
        self.assertEqual(out["bodies"][0]["field"], "client_message")
        self.assertEqual(out["bodies"][1:], [None, None])
        self.assertEqual(out["caps"][1]["client_fields"], ["client_message"])


try:
    from live_browser import LiveBrowserCase  # noqa: E402
    import test_ai_117 as t117  # noqa: E402
except Exception:  # noqa: BLE001
    LiveBrowserCase = None

if LiveBrowserCase is not None:
    LAYER = "#aiLayer"
    FIELDS = """(()=>{ document.getElementById('cmFix')?.remove(); const box=document.createElement('div'); box.id='cmFix';
      box.style.cssText='position:fixed;top:60px;left:140px;width:560px;z-index:100;background:var(--surface);padding:8px;color:var(--ink)';
      box.innerHTML=`<div class="pk-desc pked" id="pkDesc" data-pkml="1" contenteditable="plaintext-only" style="display:block;min-height:24px">The statement of work needs legal sign-off first.</div>
        <div class="pk-vtext pked" id="pkCm" data-pkf="cm" data-pkml="1" aria-label="Client messaging" contenteditable="plaintext-only" style="display:block;min-height:24px">We need the signed paperwork by Friday.</div>`;
      CUR={mode:"new",nid:"nw1",k:"actions",draft:{p:"ABC"}};
      window.SENT=[]; const f0=window.__f0||(window.__f0=window.fetch); window.fetch=(u,o)=>{ if(String(u).endsWith("/api/edit/ai")) SENT.push(JSON.parse(o.body)); return f0(u,o); };
      document.body.appendChild(box); pkEdMount(box); return true; })()"""

    class _Page(LiveBrowserCase):
        shared_server = True
        width, height = 1400, 900
        patched = True

        @classmethod
        def load(cls, v):
            R.populate(v)
            E.prepare(v.root)                                            # #186
            if cls.patched:
                prepare(v.root)                                          # #263
            elif MARKER in (v.root / "system/scripts/edit_ai.py").read_text(encoding="utf-8"):
                subprocess.run(["patch", "-p0", "-s", "-R", "-d", str(v.root), "-i", str(DIFF)], check=True)
            cls.fake = v.root / "fake_claude.py"
            cls.fake.write_text(t117.FAKE)
            cls.fake.chmod(0o755)

        @classmethod
        def server_env(cls):
            return {"CREAITE_CLAUDE": str(cls.fake)}

        def tearDown(self):
            if self.b:
                self.b.eval("aiSug.value=null; aiBar.value=null; document.getElementById('cmFix')?.remove(); CUR=null; true")
            super().tearDown()

        def select(self, sel):
            b = self.b
            b.click(sel)
            b.key("a", 4)
            b.pump(0.4)

        def sparked(self):
            return bool(self.b.eval(f"!!document.querySelector('{LAYER} .aispark')"))

        def mount(self):
            b = self.b
            b.eval(FIELDS)
            b.wait("!!document.querySelector('#cmFix #pkCm.ProseMirror')")
            self.select("#cmFix #pkCm")                                  # the first selection asks the server
            b.pump(0.6)
            b.key("Escape")

    class ThePagePatched(_Page):
        """With the diff: the Client messaging field has the bar, and its request names the field."""

        def test_the_field_has_the_bar_and_names_itself(self):
            if UNPATCHED:
                self.skipTest("without the diff the field has no bar (ThePageOldServer)")
            b = self.b
            self.mount()
            self.select("#cmFix #pkCm")
            self.assertTrue(self.sparked())
            Path(str(self.fake) + ".reply").write_text("ABC-A-004 is late; Omar Ali will chase.", encoding="utf-8")
            b.click(f"{LAYER} .aispark")
            b.wait(f"document.querySelector('{LAYER} .aibar')")
            b.click(f'{LAYER} .aibar button[data-tip="AI: improve"]')
            b.wait(f"document.querySelector('{LAYER} [role=menu]')")
            b.click(f"{LAYER} [role=menu] [data-ai=rewrite]")
            b.wait(f"document.querySelector('{LAYER} .aisug .aitext')||document.querySelector('{LAYER} .aisug [role=alert]')", 30)
            said = b.eval(f"document.querySelector('{LAYER} .aisug').textContent")
            self.assertIn("isn't client-safe", said)
            self.assertEqual((b.eval("SENT.at(-1).field"), b.eval("SENT.at(-1).place")), ("client_message", "plain"))
            prompt = Path(str(self.fake) + ".prompt").read_text(encoding="utf-8")
            for i in E.INTERNAL_IDS:
                self.assertNotIn(i, prompt)
            self.assertNotIn("Omar Ali", prompt)

    class ThePageOldServer(_Page):
        """Without the diff (#186 only: caps lists no client fields): the field has no bar; the other longer fields keep theirs."""
        patched = False

        def test_the_field_has_no_bar_and_the_others_keep_theirs(self):
            self.mount()
            self.select("#cmFix #pkCm")
            self.assertFalse(self.sparked(), "Client messaging: no bar on an older server")
            self.b.key("Escape")
            self.select("#cmFix #pkDesc")
            self.assertTrue(self.sparked(), "the description keeps its bar")


if __name__ == "__main__":
    unittest.main()
