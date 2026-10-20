"""#183 (2.6): Draft email delivery, the plain code (system/scripts/draft_delivery.py) and the sweep's Sent Items.

Run: python3 dev/tests/test_draft_delivery.py
The Microsoft 365 call is never made here: the live server's run is stood in for by the stream-json events it would give (a stub
of the create-draft tool's answer). Fictional data only.
"""
import ast
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "system" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import draft_delivery as dd  # noqa: E402
import drafts  # noqa: E402
import permissions  # noqa: E402
from test_tracker import Vault  # noqa: E402

ON = {"draft_email": {"outlook_drafts": True}}
HTML = ('<div style="font-family:Arial;color:#1a1a1a;background:#ffffff;"><p style="margin:0 0 12px 0;">Hi Sara,</p>'
        '<table cellpadding="6" cellspacing="0" border="0"><tbody><tr><td style="color:#B3261E;font-weight:bold;">05-10-2026</td>'
        '<td>Data<br><i style="font-style:normal;color:#5C5D60;">Response: <a href="https://example.com/plan" style="color:#0b5cad;">the plan</a>'
        '</i></td></tr></tbody></table></div>')
PAYLOAD = {"to": "sara@example.com", "subject": "ABC-A-006 · Overdue: a quick reminder", "html": HTML,
           "ids": ["ABC-A-006", "not an id"], "mode": "chase", "name": "Sara Example"}


def stub_run(req, answer=None, error=None, extra_tools=(), args=None):
    """The events a headless run gives when the create-draft tool is called with `args` (the request's own by default)."""
    uses = [{"type": "tool_use", "id": "t1", "name": dd.CREATE_TOOL, "input": args if args is not None else req["args"]}]
    uses += [{"type": "tool_use", "id": f"x{n}", "name": t, "input": {}} for n, t in enumerate(extra_tools)]
    res = {"type": "tool_result", "tool_use_id": "t1", "is_error": bool(error),
           "content": [{"type": "text", "text": error or json.dumps(answer or {})}]}
    return [{"type": "system", "subtype": "init"}, {"type": "assistant", "message": {"content": uses}},
            {"type": "user", "message": {"content": [res]}}, {"type": "result", "result": "{\"ok\": true}"}]


class Isolated(unittest.TestCase):
    """drafted.json and chases.json in a throwaway folder."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self._was = (dd.DRAFTED, drafts.CHASES)
        dd.DRAFTED, drafts.CHASES = self.tmp / "drafted.json", self.tmp / "chases.json"

    def tearDown(self):
        dd.DRAFTED, drafts.CHASES = self._was

    def chases(self):
        return drafts.chases_load()


class SettingAndRequest(Isolated):
    def test_the_setting_is_off_by_default_and_a_request_is_refused_while_off(self):
        defaults = json.loads((REPO / "system/templates/settings-defaults.json").read_text())
        self.assertIs(defaults["draft_email"]["outlook_drafts"], False)
        self.assertFalse(dd.enabled({}))
        self.assertFalse(dd.enabled(defaults))
        with self.assertRaises(dd.Refused) as e:
            dd.request(PAYLOAD, {})
        self.assertIn("off in Settings", str(e.exception))

    def test_the_body_is_the_previews_html_byte_for_byte_with_the_subject_and_to_as_shown(self):
        req = dd.request(PAYLOAD, ON)
        self.assertEqual(req["tool"], dd.CREATE_TOOL)
        self.assertEqual(req["args"], {"subject": PAYLOAD["subject"], "body": HTML, "bodyType": "html", "to": ["sara@example.com"]})
        self.assertEqual(req["ids"], ["ABC-A-006"])
        self.assertFalse(req["no_recipient"])

    def test_no_address_on_record_still_makes_the_draft_with_nothing_in_to(self):
        req = dd.request({**PAYLOAD, "to": ""}, ON)
        self.assertNotIn("to", req["args"])
        self.assertTrue(req["no_recipient"])

    def test_the_followups_name_and_address_list_is_read_and_a_bad_address_refused(self):
        req = dd.request({**PAYLOAD, "to": "Sara Example <sara@example.com>; omar@example.com; SARA@example.com"}, ON)
        self.assertEqual(req["args"]["to"], ["sara@example.com", "omar@example.com"])
        for bad in ("sara at example", "sara@example.com\nBcc: x@y.com"):
            with self.assertRaises(dd.Refused):
                dd.request({**PAYLOAD, "to": bad}, ON)

    def test_an_empty_or_multi_line_subject_and_an_empty_body_are_refused(self):
        for p in ({**PAYLOAD, "subject": ""}, {**PAYLOAD, "subject": "a\nb"}, {**PAYLOAD, "subject": "x" * 256},
                  {**PAYLOAD, "html": ""}, {**PAYLOAD, "html": "x" * (dd.BODY_MAX + 1)}):
            with self.assertRaises(dd.Refused):
                dd.request(p, ON)


class Markup(unittest.TestCase):
    """#183 (Alan, 19-10-2026): a draft's body is only the markup Outlook's create-draft takes; anything else is refused before any run."""

    def test_the_builders_markup_passes(self):
        self.assertIsNone(dd.markup_problem(HTML))
        self.assertEqual(dd.request(PAYLOAD, ON)["args"]["body"], HTML)          # passed through byte for byte, never rewritten

    def test_a_body_with_a_refused_construct_is_refused_with_fixed_words(self):
        cases = {
            '<p><span style="color:#B3261E;">late</span></p>': "a <span> element",
            '<p><font color="#B3261E">late</font></p>': "a <font> element",
            '<p class="x">Hi</p>': "a class attribute",
            '<p id="x">Hi</p>': "an id attribute",
            '<p data-cx-style="color:red">Hi</p>': "a data- attribute",
            '<p onclick="x()">Hi</p>': "an event handler",
            '<style>p{color:red}</style><p>Hi</p>': "a <style> element",
            '<script>x()</script><p>Hi</p>': "a <script> element",
            '<!-- note --><p>Hi</p>': "a comment",
            '<p style="color:var(--red)">Hi</p>': "a style Outlook won't take",
            '<img src="https://example.com/x.png">': "a <img> element",
            '<blockquote>Hi</blockquote>': "a <blockquote> element",
            '<a href="javascript:alert(1)">x</a>': "a link that isn't a web or mail address",
        }
        for body, what in cases.items():
            with self.subTest(body=body):
                self.assertEqual(dd.markup_problem(body), what)
                with self.assertRaises(dd.Refused) as e:
                    dd.request({**PAYLOAD, "html": body}, ON)
                self.assertEqual(str(e.exception), f"The email has formatting Outlook won't take ({what}): copy it instead.")

    def test_a_copy_is_never_refused_for_its_markup(self):
        req = dd.request({**PAYLOAD, "action": "copied", "html": '<p><span style="color:red">x</span></p>'}, ON)
        self.assertEqual(req["mode"], "chase")                                     # the copy's references are still kept for the sweep


    def test_s_is_not_on_outlooks_list_and_strike_is(self):
        """#183 review L2: Outlook's list names strike, not s: an <s> is refused before any run, a <strike> passes."""
        self.assertEqual(dd.markup_problem("<p><s>old</s></p>"), "a <s> element")
        self.assertIsNone(dd.markup_problem("<p><strike>old</strike></p>"))
        self.assertNotIn("s", dd.ALLOWED_TAGS)
        with self.assertRaises(dd.Refused):
            dd.request({**PAYLOAD, "html": "<p><s>old</s></p>"}, ON)


class CopiedCommand(unittest.TestCase):
    """#183 review L1: a copy is never refused for its markup, through the command line the live server calls (the route's
    body used to carry no action, so the check always ran)."""

    def test_the_copied_command_accepts_markup_outlook_would_refuse_and_the_request_command_needs_the_action(self):
        v = Vault()
        self.addCleanup(v.cleanup)
        v.run("init")
        env = {**os.environ, "CREAITE_NOW": "2026-10-19 12:00"}
        dd_cmd = [sys.executable, str(v.root / "system/scripts/draft_delivery.py")]
        settings = v.root / "system/config/settings.json"
        s = json.loads(settings.read_text())
        s["draft_email"] = {"outlook_drafts": True}
        settings.write_text(json.dumps(s))
        body = {**PAYLOAD, "html": "<p><span>x</span></p>"}

        def call(cmd, payload):
            r = subprocess.run(dd_cmd + [cmd], input=json.dumps(payload), capture_output=True, text=True, cwd=v.root, env=env)
            return r.returncode, json.loads(r.stdout)

        rc, out = call("copied", body)                                    # no action in the body, as the route sent it
        self.assertEqual((rc, out["ok"]), (0, True), out)
        rc, out = call("request", {**body, "action": "copied"})
        self.assertEqual((rc, out["ok"]), (0, True), out)
        rc, out = call("request", {**body, "action": "create"})
        self.assertEqual((rc, out["ok"]), (1, False))
        self.assertIn("formatting Outlook won't take", out["message"])


class NeverSends(unittest.TestCase):
    def test_the_run_may_use_create_draft_and_tool_search_only(self):
        self.assertEqual(dd.allowed_tools(), ["mcp__claude_ai_Microsoft_365__outlook_create_draft", "ToolSearch"])

    def test_every_other_microsoft_365_action_is_denied_by_name_and_create_draft_is_not(self):
        denied = dd.denied_tools()
        self.assertNotIn(dd.CREATE_TOOL, denied)
        for t in ("outlook_send_draft", "outlook_send_mail", "outlook_update_draft", "outlook_delete_draft", "outlook_forward_mail",
                  "teams_send_chat_message"):
            self.assertIn(permissions.M365 + t, denied)
        self.assertEqual(sorted(denied + [dd.CREATE_TOOL]), sorted(permissions.m365_action_tools()))

    def test_no_send_call_exists_in_the_module(self):
        src = (REPO / "system/scripts/draft_delivery.py").read_text()
        strings = [n.value for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        self.assertFalse([s for s in strings if "send_" in s or "sendMail" in s], "a send tool is named in a string")
        names = {n.id for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Name)} | \
                {n.attr for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Attribute)}
        self.assertFalse({n for n in names if "send" in n.lower()})
        self.assertNotIn("subprocess", src)                 # it starts nothing: the server runs the call
        self.assertNotIn("urllib", src)

    def test_the_prompt_names_only_the_create_tool_and_carries_the_body_unchanged(self):
        req = dd.request(PAYLOAD, {**ON})
        words = dd.prompt(req)
        self.assertIn(dd.CREATE_TOOL, words)
        self.assertIn(json.dumps(req["args"], ensure_ascii=False), words)
        self.assertIn("never send", words)
        self.assertNotIn("send_", words)


class Check(Isolated):
    def setUp(self):
        super().setUp()
        self.req = dd.request(PAYLOAD, ON)

    def test_a_draft_made_gives_its_id_and_outlook_link(self):
        got = dd.check(stub_run(self.req, {"id": "AAMk1", "webLink": "https://outlook.office365.com/owa/?ItemID=AAMk1"}), self.req)
        self.assertEqual(got, {"ok": True, "made": True, "id": "AAMk1", "web_link": "https://outlook.office365.com/owa/?ItemID=AAMk1"})

    def test_a_link_off_outlooks_own_hosts_is_dropped(self):
        got = dd.check(stub_run(self.req, {"id": "AAMk1", "webLink": "https://evil.example.com/x"}), self.req)
        self.assertEqual(got["web_link"], "")

    def test_a_refusal_is_fixed_words_and_nothing_made(self):
        got = dd.check(stub_run(self.req, error="ErrorAccessDenied: Access is denied. Check credentials and try again. 403"), self.req)
        self.assertEqual(got, {"ok": False, "made": False, "reason": "you don't have permission to write to this mailbox"})
        got = dd.check(stub_run(self.req, error="Body contains <span> which is outside the outbound allowlist"), self.req)
        self.assertEqual(got["reason"], "Outlook rejected part of the email's formatting")
        got = dd.check(stub_run(self.req, error="Something odd happened to Sara's mail"), self.req)
        self.assertNotIn("Sara", got["reason"])

    def test_changed_arguments_or_another_tool_are_never_reported_as_success(self):
        changed = {**self.req["args"], "body": "<p>Simplified</p>"}
        got = dd.check(stub_run(self.req, {"id": "x"}, args=changed), self.req)
        self.assertFalse(got["ok"])
        self.assertTrue(got["made"])
        got = dd.check(stub_run(self.req, {"id": "x"}, extra_tools=[permissions.M365 + "outlook_send_draft"]), self.req)
        self.assertFalse(got["ok"])
        self.assertIn("another tool", got["reason"])
        self.assertEqual(dd.check([{"type": "result", "result": "{}"}], self.req)["reason"], "Outlook wasn't reached")


class Access(unittest.TestCase):
    """Settings' Outlook access Check: the granted scopes, read with the reading tool get_granted_scopes."""

    def events(self, text, error=False, name=dd.ACCESS_TOOL):
        return [{"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "a1", "name": name, "input": {}}]}},
                {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "a1", "is_error": error, "content": text}]}}]

    def test_mail_readwrite_means_drafts_can_be_made(self):
        self.assertTrue(dd.access(self.events('["User.Read", "Mail.Read", "Mail.ReadWrite", "Calendars.Read"]'))["can"])

    def test_read_only_scopes_or_a_refusal_mean_they_cannot_and_no_call_means_unknown(self):
        self.assertFalse(dd.access(self.events('["User.Read", "Mail.Read"]'))["can"])
        self.assertFalse(dd.access(self.events("AADSTS65001: consent required", error=True))["can"])
        self.assertIsNone(dd.access([])["can"])
        self.assertIsNone(dd.access(self.events('["Mail.ReadWrite"]', name=dd.CREATE_TOOL))["can"])

    def test_the_check_uses_a_reading_tool(self):
        self.assertIn(dd.ACCESS_TOOL[len(permissions.M365):], permissions.M365_READ)


class ChaseRecords(Isolated):
    NOW = datetime(2026, 10, 19, 10, 42)

    def test_a_draft_created_records_the_chase_without_i_sent_it(self):
        req = dd.request(PAYLOAD, ON)
        out = dd.record_created(req, self.NOW)
        self.assertEqual(out["chased"], ["ABC-A-006"])
        self.assertEqual(self.chases(), [{"ids": ["ABC-A-006"], "date": "2026-10-19", "mode": "chase"}])
        self.assertEqual(drafts.chase_counts()["ABC-A-006"], {"n": 1, "last": "2026-10-19"})

    def test_drafted_json_holds_references_and_fingerprints_only(self):
        dd.record_created(dd.request(PAYLOAD, ON), self.NOW)
        text = dd.DRAFTED.read_text()
        for secret in ("sara@example.com", "Overdue", "reminder", "Sara", "05-10-2026", "<div"):
            self.assertNotIn(secret, text)
        e = json.loads(text)["drafted"][0]
        self.assertEqual(set(e), {"ids", "mode", "at", "via", "subject", "to", "recorded", "sent"})
        self.assertEqual((e["via"], e["recorded"], e["sent"]), ("draft", True, None))

    def test_a_refused_draft_records_nothing(self):
        req = dd.request(PAYLOAD, ON)
        self.assertFalse(dd.check(stub_run(req, error="403 Forbidden"), req)["ok"])
        self.assertEqual(self.chases(), [])                 # the route records only after check says ok
        self.assertFalse(dd.DRAFTED.exists())


class SentItems(Isolated):
    NOW = datetime(2026, 10, 19, 10, 42)
    SENT = {"subject": "RE: ABC-A-006 · Overdue: a quick reminder", "to": ["Sara Example <SARA@example.com>"], "sent": "2026-10-19 11:05"}

    def test_a_drafted_email_seen_in_sent_items_is_marked_sent_once(self):
        dd.record_created(dd.request(PAYLOAD, ON), self.NOW)
        self.assertEqual(dd.match_sent([self.SENT]), {"seen": 1, "matched": 1, "recorded": 0})
        self.assertEqual(drafts.chase_counts()["ABC-A-006"], {"n": 1, "last": "2026-10-19", "sent": "2026-10-19"})
        self.assertEqual(dd.match_sent([self.SENT]), {"seen": 1, "matched": 0, "recorded": 0})
        self.assertEqual(len(self.chases()), 1)

    def test_a_copied_email_is_recorded_when_the_sweep_finds_it_sent(self):
        dd.record_copied(dd.request(PAYLOAD, ON), self.NOW)
        self.assertEqual(self.chases(), [])
        self.assertEqual(dd.match_sent([self.SENT])["recorded"], 1)
        self.assertEqual(self.chases(), [{"ids": ["ABC-A-006"], "date": "2026-10-19", "mode": "chase"}])

    def test_another_subject_recipient_or_time_does_not_match(self):
        dd.record_created(dd.request(PAYLOAD, ON), self.NOW)
        for m in ({**self.SENT, "subject": "ABC-A-006 · Something else"}, {**self.SENT, "to": ["omar@example.com"]},
                  {**self.SENT, "sent": "2026-11-20 09:00"}, {**self.SENT, "sent": "2026-10-18 09:00"}, {**self.SENT, "sent": "soon"}):
            self.assertEqual(dd.match_sent([m])["matched"], 0, m)

    def test_a_draft_with_nothing_in_to_matches_on_its_subject(self):
        dd.record_created(dd.request({**PAYLOAD, "to": ""}, ON), self.NOW)
        self.assertEqual(dd.match_sent([{**self.SENT, "to": ["sara.new@example.com"]}])["matched"], 1)


class SweepStage(unittest.TestCase):
    """sweep.py stage with sent_items: the drafted email is marked sent; counts only are printed."""

    def test_the_sweep_marks_a_drafted_email_sent(self):
        v = Vault()
        self.addCleanup(v.cleanup)
        v.run("init")
        env = {**os.environ, "CREAITE_NOW": "2026-10-19 12:00"}
        dd_cmd = [sys.executable, str(v.root / "system/scripts/draft_delivery.py")]
        settings = v.root / "system/config/settings.json"
        s = json.loads(settings.read_text())
        s["draft_email"] = {"outlook_drafts": True}
        settings.write_text(json.dumps(s))
        req = json.loads(subprocess.run(dd_cmd + ["request"], input=json.dumps(PAYLOAD), capture_output=True, text=True,
                                        cwd=v.root, env=env).stdout)
        self.assertTrue(req.pop("ok"))
        r = subprocess.run(dd_cmd + ["created"], input=json.dumps(req), capture_output=True, text=True, cwd=v.root, env=env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        spec = v.root / "system/staging/drafts/sweep.json"
        spec.parent.mkdir(parents=True, exist_ok=True)
        spec.write_text(json.dumps({"window": {}, "items": [], "sent_items": [
            {"subject": PAYLOAD["subject"], "to": ["sara@example.com"], "sent": "2026-10-19 12:30"}]}))
        r = v.run("stage", str(spec), script="sweep.py", cwd=v.root)
        self.assertIn("Sent Items: 1 drafted email(s) seen sent", r.stdout)
        self.assertNotIn("Overdue", r.stdout)
        drafted = json.loads((v.root / "system/staging/drafted.json").read_text())["drafted"]
        self.assertTrue(drafted[0]["sent"])


if __name__ == "__main__":
    unittest.main()
