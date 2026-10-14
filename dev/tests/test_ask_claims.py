"""BL-314 (v1.9.1): ask creaite checks what it says, and says a plain "I can't".

(a) Claims: before a chat's text is shown, the live server runs claims.check on each whole text block: every work-item ID is
looked up through tracker.py's read functions; a title that doesn't match is flagged "doesn't match the tracker: <real title>",
a wrong owner is corrected, an ID of a registered project that isn't there is flagged. Read only: tracker.db is unchanged.
(b) "I can't": a CONFIRM for something the panel can never do (a Microsoft 365 action, the live server) is never offered as Go
ahead; a "cant" event leads with one sentence and a button to where it can be done. A refused Microsoft 365 call leads the same
way. The guard is unchanged (test_guard_pinned, test_reach, test_record_commands).

Run: python3 dev/tests/test_ask_claims.py     (quick tier: no Chrome)
"""
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "system" / "scripts"))
from test_tracker import Vault, action  # noqa: E402
from test_run_read_pinned import HARNESS, assistant, final, text  # noqa: E402
import claims  # noqa: E402

ROOT = HERE.parent.parent
DB = {"FAL-A-007": {"table": "actions", "title": "Confirm data-room access for the client team", "owner": "Omar Haddad"},
      "ABC-A-003": {"table": "actions", "title": "Draft the statement of work (SOW) for phase 2", "owner": "Sara Khan"},
      "ABC-012": {"table": "raid", "title": "Vendor delay on the integration environment", "owner": "Omar Haddad"},
      "ABC-D-004": {"table": "decisions", "title": "Go-live moves to 15 Nov", "owner": "Alan Carter"}}
PEOPLE = [{"name": "Omar Haddad", "aliases": ["OH"]}, {"name": "Sara Khan", "aliases": []}, {"name": "Alan Carter", "aliases": []}]


def look(item_id):
    return DB.get(item_id)


look.project = lambda code: code in ("ABC", "FAL")


def chk(t):
    return claims.check(t, look, PEOPLE)


class Claims(unittest.TestCase):
    def test_the_12_october_reply_is_flagged(self):
        out, found = chk("- **FAL-A-007** · Set up weekly cadence")
        self.assertIn("Set up weekly cadence (⚠ doesn't match the tracker: Confirm data-room access for the client team)", out)
        self.assertEqual([(f["id"], f["kind"]) for f in found], [("FAL-A-007", "title")])

    def test_separators_and_brackets(self):
        for t in ("FAL-A-007: Set up weekly cadence", "FAL-A-007 — Set up weekly cadence, owner Omar",
                  "FAL-A-007 (Set up weekly cadence)", "[FAL-A-007](#work/actions/FAL-A-007) · Set up weekly cadence"):
            with self.subTest(t):
                self.assertEqual([f["kind"] for f in chk(t)[1]], ["title"])

    def test_a_matching_or_shortened_title_is_left_alone(self):
        for t in ("ABC-A-003 · Draft SOW", "ABC-A-003 — Draft the statement of work…", "ABC-012 (Vendor delay) is High",
                  "ABC-D-004: Go-live moves to 15 Nov", "Mark ABC-A-003 done, then chase ABC-012."):
            with self.subTest(t):
                self.assertEqual(chk(t), (t, []))

    def test_a_wrong_owner_is_corrected_inline(self):
        out, found = chk("- ABC-A-003 — Draft SOW (Omar Haddad, due 12-10-2026)")
        self.assertIn("(Sara Khan (corrected from the tracker: the reply said Omar Haddad), due 12-10-2026)", out)
        self.assertEqual(found, [{"id": "ABC-A-003", "kind": "owner", "said": "Omar Haddad", "real": "Sara Khan"}])
        out, found = chk("ABC-A-003: Draft the SOW, owner Omar")
        self.assertIn("owner Sara Khan (corrected from the tracker: the reply said Omar)", out)

    def test_first_name_and_alias_are_the_owner(self):
        for t in ("ABC-A-003 — Draft SOW (Sara)", "ABC-012 · Vendor delay · OH", "ABC-A-003: Draft SOW, owner Sara Khan"):
            with self.subTest(t):
                self.assertEqual(chk(t), (t, []))

    def test_unknown_id_of_a_registered_project_is_flagged(self):
        out, found = chk("ABC-A-099 is overdue; XYZ-A-001 isn't ours.")
        self.assertEqual(out, "ABC-A-099 (⚠ not in the tracker) is overdue; XYZ-A-001 isn't ours.")
        self.assertEqual([f["kind"] for f in found], ["missing"])

    def test_a_table_by_its_header(self):
        t = ("| ID | Action | Owner | Due |\n|---|---|---|---|\n| FAL-A-007 | Set up weekly cadence | Omar | 12-10-2026 |\n"
             "| ABC-A-003 | Draft SOW | Omar Haddad | — |\n| ABC-012 | Vendor delay | Omar Haddad | — |")
        out, found = chk(t)
        rows = out.split("\n")
        self.assertIn("Set up weekly cadence (⚠ doesn't match the tracker: Confirm data-room access for the client team)", rows[2])
        self.assertIn("Sara Khan (corrected from the tracker: the reply said Omar Haddad)", rows[3])
        self.assertEqual(rows[4], "| ABC-012 | Vendor delay | Omar Haddad | — |")
        self.assertEqual([(f["id"], f["kind"]) for f in found], [("FAL-A-007", "title"), ("ABC-A-003", "owner")])

    def test_code_fences_and_no_ids_are_untouched(self):
        for t in ("```\nABC-A-099 · nothing\n```", "Example Programme is At risk.", "", "ISO-9001 and COVID-19"):
            with self.subTest(t):
                self.assertEqual(chk(t), (t, []))

    def test_summary(self):
        self.assertEqual(claims.summary([]), "")
        self.assertEqual(claims.summary([{"kind": "title"}, {"kind": "owner"}, {"kind": "owner"}]),
                         "Checked against the tracker: 1 title didn't match, 2 owners corrected.")


class Cant(unittest.TestCase):
    def test_what_the_panel_can_never_do(self):
        cases = {("Send chase email to Omar", "about ABC-A-003"): ("mail", {"email": "Omar Haddad", "mode": "chase",
                                                                            "label": "Draft email to Omar Haddad"}),
                 ("Book a meeting with Sara", "Thursday 10:00"): ("calendar", {"page": "today", "label": "Open Today"}),
                 ("Accept the invite", "from Sara"): ("calendar", {"page": "today", "label": "Open Today"}),
                 ("Post the update in Teams", "to the channel"): ("teams", {"page": "people", "label": "Open People"}),
                 ("Restart the live server", "it stops and starts"): ("server", {"page": "settings", "arg": "live",
                                                                                 "label": "Open Settings"}),
                 ("Upload the SOW to SharePoint", "x"): ("files", {"page": "files", "label": "Open Files"})}
        for (t, b), (what, go) in cases.items():
            with self.subTest(t):
                c = claims.cant(t, b, PEOPLE)
                self.assertEqual((c["what"], c["go"]), (what, go))
                self.assertTrue(c["line"].startswith("ask creaite can't"))

    def test_what_it_can_do_is_still_offered(self):
        for t, b in (("Apply 3 items", "They go to ABC and need your yes"), ("Undo last apply", "puts it back"),
                     ("Draft an email to Omar", "a draft in the panel"), ("Weekly report ABC", "draft the report"),
                     ("Process the steering meeting minutes", "draft minutes"), ("Send to review", "3 items go to Review"),
                     ("Move ABC go-live", "to 20-11-2026"), ("Client report ABC", "draft"), ("Mark ABC-A-003 done", "x")):
            with self.subTest(t):
                self.assertIsNone(claims.cant(t, b, PEOPLE))

    def test_refused_tools(self):
        m = "mcp__claude_ai_Microsoft_365__"
        c = claims.cant_denied([{"tool_name": "Bash", "tool_input": {"command": "rm -rf x"}},
                                {"tool_name": m + "outlook_send_mail", "tool_input": {"to": "Omar Haddad <o@x.com>"}}], PEOPLE)
        self.assertEqual((c["what"], c["go"]["email"]), ("mail", "Omar Haddad"))
        self.assertEqual(claims.cant_denied([{"tool_name": m + "outlook_create_event", "tool_input": {}}], PEOPLE)["what"],
                         "calendar")
        self.assertEqual(claims.cant_denied([{"tool_name": "Bash", "tool_input": {
            "command": "system/scripts/run live_server.py"}}], PEOPLE)["what"], "server")
        self.assertIsNone(claims.cant_denied([{"tool_name": "Write", "tool_input": {"file_path": "/etc/hosts"}}], PEOPLE))


class InTheServer(unittest.TestCase):
    """The real Run.read, a recorded stream and the real tracker in a throwaway vault."""

    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        cls.v.run("init")
        cls.v.propose("a", [action(1, description="Confirm data-room access for the client team", owner="Alan Carter")])
        cls.v.run("apply")
        cls.db = cls.v.root / "system" / "tracker.db"

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def read(self, spec):
        r = subprocess.run([sys.executable, "-c", HARNESS], input=json.dumps(spec), cwd=self.v.root, capture_output=True,
                           text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_a_wrong_title_is_flagged_before_it_is_shown_and_the_tracker_is_unchanged(self):
        before = hashlib.sha256(self.db.read_bytes()).hexdigest()
        out = self.read({"events": [assistant(text("Open: ABC-A-001 · Set up weekly cadence")), final("x")]})
        shown = [e for e in out["events"] if e["type"] == "text"]
        self.assertEqual(shown[0]["text"], "Open: ABC-A-001 · Set up weekly cadence (⚠ doesn't match the tracker: "
                                           "Confirm data-room access for the client team)")
        self.assertEqual(shown[0]["checked"][0]["kind"], "title")
        self.assertEqual(out["said"], [shown[0]["text"]])               # the chat's history keeps the checked text
        self.assertEqual(hashlib.sha256(self.db.read_bytes()).hexdigest(), before)

    def test_a_right_title_has_no_checked_key(self):
        out = self.read({"events": [assistant(text("ABC-A-001 · Confirm data-room access")), final("x")]})
        self.assertEqual([e for e in out["events"] if e["type"] == "text"],
                         [{"type": "text", "text": "ABC-A-001 · Confirm data-room access"}])

    def test_only_a_chat_is_checked(self):
        out = self.read({"attrs": {"kind": "generate"},
                         "events": [assistant(text("ABC-A-001 · Set up weekly cadence")), final("x")]})
        self.assertEqual([e["text"] for e in out["events"] if e["type"] == "text"], ["ABC-A-001 · Set up weekly cadence"])

    def test_a_confirm_the_panel_cant_do_is_never_go_ahead(self):
        out = self.read({"events": [final("I'll email Omar.\nCONFIRM: Send chase email to Omar | about ABC-A-001")]})
        kinds = [e["type"] for e in out["events"]]
        self.assertNotIn("confirm", kinds)
        cant = next(e for e in out["events"] if e["type"] == "cant")
        self.assertEqual(cant["what"], "mail")
        self.assertTrue(cant["line"].startswith("ask creaite can't send"))
        self.assertIn(cant["line"], out["said"])

    def test_an_ordinary_confirm_is_unchanged(self):
        out = self.read({"events": [final("Three actions.\nCONFIRM: Apply 3 items | They go to ABC and need your yes")]})
        self.assertEqual([e["type"] for e in out["events"]], ["confirm", "done"])

    def test_a_refused_mail_call_leads_with_the_plain_sentence(self):
        out = self.read({"events": [final("I couldn't send it.", denials=[
            {"tool_name": "mcp__claude_ai_Microsoft_365__outlook_send_mail", "tool_input": {"to": "x@y.com"}}])]})
        kinds = [e["type"] for e in out["events"]]
        self.assertLess(kinds.index("cant"), kinds.index("denied"))


class Wiring(unittest.TestCase):
    def test_prompt_and_page(self):
        import live_server
        self.assertIn("checks every ID in your reply against the tracker", live_server.ASK_PROMPT)
        self.assertIn("never ask for it with CONFIRM:", live_server.ASK_PROMPT)
        js = (ROOT / "system/templates/dashboard/src/ask.js").read_text(encoding="utf-8")
        for s in ('ev.type==="cant"', "claimsNote(ev.checked)", "data-cango", "export function cantGo"):
            self.assertIn(s, js)
        page = (ROOT / "system/templates/dashboard.html").read_text(encoding="utf-8")
        self.assertIn("data-cango", page, "rebuild: python3 dev/tools/split_dashboard.py build")


if __name__ == "__main__":
    unittest.main()
