"""#263: the item panel's Client messaging field gets the client rules on its AI bar (client facts, the client check on the reply).

Run: python3 dev/tests/test_client_messaging_263.py

The field is its own place, `client_message` (the field's name): edit_ai.py binds the client rules from it, never from a page's word
"client". What it proves (test_reports' fictional ABC fixture, the health reason set):
- the place offers the plain field's options (Rewrite clearly, Shorter, Make it executive, Ask…), plain text, spelling fixed;
- Claude is told only the client-visible items, no people, and the client rule;
- a selection that already holds an internal item (any spelling) or VIP is refused before Claude;
- a reply that brings in an internal item, a name, the internal health reason or an internal-only marker is dropped;
  a client-safe reply passes; the result decides from the request's place too, not only the context's;
- no project: refused; the plain place (the other longer fields) is unchanged;
- the page: the Client messaging field mounts with place "client_message", and the page's tables list it like "plain".
"""
import json
import re
import sqlite3
import subprocess
import sys
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_reports as R  # noqa: E402  (its fixture: populate, ReportVault)

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "system" / "templates" / "dashboard" / "src"
REASON = "the vendor contract dispute is still unresolved with procurement"
TEXT = "We need the signed paperwork by Friday so the next step can be planned."
CLIENT_IDS = ("ABC-A-002", "ABC-A-003")
INTERNAL_IDS = ("ABC-A-001", "ABC-A-004", "ABC-005", "ABC-M-001")
DROPPED = "it held something that isn't client-safe"


def edit_ai(root, cmd, body):
    r = subprocess.run([sys.executable, str(root / "system/scripts/edit_ai.py"), cmd], input=json.dumps(body), cwd=root,
                       capture_output=True, text=True, timeout=120)
    if r.returncode:
        raise AssertionError(f"edit_ai.py {cmd} failed:\n{r.stdout}{r.stderr}")
    return json.loads(r.stdout)


def ask(text=TEXT, option="rewrite", place="client_message", code="ABC", **extra):
    return {"option": option, "text": text, "code": code, "place": place, **extra}


class TheClientMessagingField(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = R.ReportVault()
        R.populate(cls.v)
        with closing(sqlite3.connect(cls.v.root / "system" / "tracker.db")) as con:     # a test vault: set directly
            con.execute("UPDATE projects SET health = 'At risk', health_reason = ? WHERE code = 'ABC'", (REASON,))
            con.commit()
        cls.root = cls.v.root

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def context(self, body):
        return edit_ai(self.root, "context", body)

    def reply(self, body, suggestion, ctx=None):
        ctx = ctx or self.context(body)
        self.assertNotIn("refused", ctx)
        return edit_ai(self.root, "result", {"request": body, "context": ctx,
                                             "reply": f"<<<SUGGESTION\n{suggestion}\nSUGGESTION>>>"})

    def test_the_place_offers_the_plain_fields_options(self):
        r = subprocess.run([sys.executable, str(self.root / "system/scripts/edit_ai.py"), "options"], cwd=self.root,
                           capture_output=True, text=True, timeout=60)
        offered = json.loads(r.stdout)
        self.assertEqual([o["id"] for o in offered["client_message"]], ["rewrite", "shorter", "executive", "custom"])
        ctx = self.context(ask())
        self.assertEqual(ctx["format"], "plain")
        self.assertIn("plain text", ctx["prompt"])
        self.assertIn("spelling, grammar and punctuation", ctx["prompt"])

    def test_claude_gets_only_client_facts(self):
        for opt, extra in (("rewrite", {}), ("shorter", {}), ("executive", {}),
                           ("custom", {"instruction": "Say who owns each item."})):
            ctx = self.context(ask(option=opt, **extra))
            self.assertNotIn("refused", ctx, opt)
            p = ctx["prompt"][ctx["prompt"].index("\nThe project: "):]      # the facts (the executive voice's own example has IDs)
            for i in INTERNAL_IDS:
                self.assertNotIn(i, p, opt)
            for n in ("Omar Ali", "Jane Doe", "Alan Carter"):
                self.assertNotIn(n, p, opt)
            self.assertNotIn(REASON, p, opt)
            self.assertIn("none listed", p, opt)
            for i in CLIENT_IDS:
                self.assertIn(i, p, opt)
            self.assertIn("This text is for the client.", ctx["prompt"], opt)

    def test_a_selection_holding_something_internal_is_refused_before_claude(self):
        for sel in ("ABC-A-004 is late.", "abc a 4 is late.", "ABC/A/004 is late.", "Our VIP sponsor agrees."):
            self.assertIn("isn't client-safe", self.context(ask(text=sel)).get("refused", ""), sel)

    def test_a_reply_bringing_in_something_internal_is_dropped(self):
        for added in ("ABC-A-004 is also late.", "abc 005 waits.", "Omar Ali is confirming testers.", "Health: " + REASON + ".",
                      "Internal only: budget note.", "Sara Example will chase."):
            out = self.reply(ask(), TEXT + " " + added)
            self.assertEqual(out["text"], "", added)
            self.assertIn(DROPPED, out.get("message", ""), added)

    def test_a_client_safe_reply_passes(self):
        out = self.reply(ask(), "Please send the signed paperwork by Friday; ABC-A-002 tracks it.")
        self.assertIn("ABC-A-002", out["text"])

    def test_the_result_decides_from_the_request_too(self):
        ctx = self.context(ask())
        out = self.reply(ask(), TEXT + " ABC-A-004 is late.", ctx={**ctx, "place": "plain"})   # a context that lost its place
        self.assertEqual(out["text"], "")

    def test_no_project_is_refused(self):
        self.assertIn("no project", self.context(ask(code="")).get("refused", ""))

    def test_the_plain_place_is_unchanged(self):
        ctx = self.context(ask(place="plain"))
        self.assertIn("ABC-A-004", ctx["prompt"])
        self.assertIn("Omar Ali", ctx["prompt"])
        self.assertNotIn("This text is for the client.", ctx["prompt"])
        out = self.reply(ask(place="plain"), TEXT + " ABC-A-004 is late.")
        self.assertIn("ABC-A-004", out["text"])


class ThePage(unittest.TestCase):
    def test_the_client_messaging_field_mounts_with_its_own_place(self):
        src = (SRC / "panel.js").read_text(encoding="utf-8")
        mount = src[src.index("export function pkEdMount"):]
        mount = mount[:mount.index("\nexport const pkDetOpen")]
        self.assertIn('"client_message"', mount)
        self.assertIn("pkClientMsg", mount)
        self.assertIn('export const pkClientMsg=el=>el.dataset.pkf==="cm"||el.dataset.pkf==="cmd";', src)
        self.assertIn('place:pkClientMsg(el)?"client_message":', mount)
        self.assertEqual(src.count('data-pkf="${f}" data-pkml="1" aria-multiline="true" data-ph="Plain wording for the client"'), 1)

    def test_the_page_tables_list_the_place_like_plain(self):
        src = (SRC / "stores" / "aiEdit.js").read_text(encoding="utf-8")
        self.assertRegex(src, r'client_message: \["rewrite", "shorter", "executive", "custom"\]')
        self.assertRegex(src, r'client_message: \[\["Improve", \["rewrite", "shorter", "executive"\]\]\]')
        self.assertRegex(src, r"client_message: \{ ai: true, turnInto: false, formatNotes: false, improveOnly: true \}")

    def test_the_built_dashboard_carries_it(self):
        html = (REPO / "system" / "templates" / "dashboard.html").read_text(encoding="utf-8")
        self.assertTrue(re.search(r"pkClientMsg", html))
        self.assertIn("client_message", html)


if __name__ == "__main__":
    unittest.main()
