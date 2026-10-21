"""#262: the Internal minutes sheet's AI reply gets a client check on what it ADDS (the Distributed version is made from it).

Run: python3 dev/tests/test_minutes_reply_262.py

What it proves (test_reports' fictional ABC fixture, the health reason set):
- the minutes sheet keeps the full facts (it edits the Internal minutes) and its prompt has no client rule;
- a suggestion that adds an item a client may not see (in any spelling), a name the text and the client-visible items don't give,
  the internal health reason, an internal-only marker or VIP is dropped with the minutes' own message (which never says VIP);
- what the selected text already held (an internal ID, an owner's name) passes, and so does a client-visible item;
- a selection holding VIP can't hide what the reply adds; HTML inside an ID or a name is read through;
- minutes with no project, or one the tracker doesn't hold, are refused before Claude; a reply that gets there anyway is dropped;
- the weekly sheet (`report`) is unchanged.
"""
import json
import sqlite3
import subprocess
import sys
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_reports as R  # noqa: E402  (its fixture: populate, ReportVault)

REASON = "the vendor contract dispute is still unresolved with procurement"   # the tracker's internal health reason (fictional)
DROPPED = "that the Distributed version would carry"
ORIGINAL = "ABC-A-004 is late; Omar Ali is confirming the testers. The statement of work is with the client."
SAFE = "The statement of work is with the client."


def vault():
    v = R.ReportVault()
    R.populate(v)
    with closing(sqlite3.connect(v.root / "system" / "tracker.db")) as con:     # a test vault: set directly
        con.execute("UPDATE projects SET health = 'At risk', health_reason = ? WHERE code = 'ABC'", (REASON,))
        con.commit()
    return v


def edit_ai(root, cmd, body):
    r = subprocess.run([sys.executable, str(root / "system/scripts/edit_ai.py"), cmd], input=json.dumps(body), cwd=root,
                       capture_output=True, text=True, timeout=120)
    if r.returncode:
        raise AssertionError(f"edit_ai.py {cmd} failed:\n{r.stdout}{r.stderr}")
    return json.loads(r.stdout)


def ask(text=ORIGINAL, option="polish", place="minutes", code="ABC"):
    return {"option": option, "text": text, "code": code, "place": place}


class TheMinutesSheet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = vault()
        cls.root = cls.v.root

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def context(self, body):
        return edit_ai(self.root, "context", body)

    def reply(self, body, suggestion):
        ctx = self.context(body)
        self.assertNotIn("refused", ctx)
        return edit_ai(self.root, "result", {"request": body, "context": ctx,
                                             "reply": f"<<<SUGGESTION\n{suggestion}\nSUGGESTION>>>"})

    def test_the_sheet_keeps_the_full_facts(self):
        ctx = self.context(ask())
        self.assertNotIn("refused", ctx)
        for i in ("ABC-A-001", "ABC-A-002", "ABC-A-004", "ABC-005"):
            self.assertIn(i, ctx["prompt"])
        self.assertIn("Omar Ali", ctx["prompt"])
        self.assertNotIn("This text is for the client.", ctx["prompt"])

    def test_a_suggestion_adding_something_internal_is_dropped(self):
        for added in ("ABC-005 is also open.", "abc 005 is also open.", "Jane Doe and Omar Ali agreed; ABC-M-001 slips.",
                      "Sara Example will chase.", "Health: " + REASON + ".", "Internal only: budget note.", "The VIP asked."):
            out = self.reply(ask(text=SAFE), SAFE + " " + added)
            self.assertEqual(out["text"], "", added)
            self.assertIn(DROPPED, out.get("message", ""), added)
            self.assertNotIn("VIP", out.get("message", "").upper(), added)        # BL-288

    def test_what_the_selection_held_passes_and_so_do_client_visible_items(self):
        out = self.reply(ask(), "ABC-A-004 is running late, as Omar Ali is still confirming testers. The client has the SOW.")
        self.assertIn("ABC-A-004", out["text"])
        out = self.reply(ask(), ORIGINAL + " ABC-A-002 is with the client.")
        self.assertIn("ABC-A-002", out["text"])
        out = self.reply(ask(text=SAFE), "The client has the statement of work.")
        self.assertIn("statement of work", out["text"])

    def test_minutes_with_no_project_or_an_unknown_one_are_refused_before_claude(self):
        for code in ("", "ZZZ"):
            self.assertIn("no project in the tracker", self.context(ask(code=code)).get("refused", ""), code)
        ctx = {"place": "minutes", "code": "", "original": SAFE, "option": "polish", "format": "markdown"}   # made by hand
        out = edit_ai(self.root, "result", {"request": ask(code=""), "context": ctx,
                                            "reply": f"<<<SUGGESTION\n{SAFE}\nSUGGESTION>>>"})
        self.assertEqual(out["text"], "")

    def test_a_selection_holding_vip_still_has_the_reply_checked(self):
        for vip in ("VIP", "v.i.p", "V.I.P."):
            sel = f"Our {vip} sponsor is happy."
            for added in (" ABC-A-004 is open.", " Omar Ali chases.", " " + REASON + ".", " Internal only.", " ABC-005 waits."):
                out = self.reply(ask(text=sel), sel + added)
                self.assertEqual(out["text"], "", (vip, added))
                self.assertIn(DROPPED, out.get("message", ""), (vip, added))
                self.assertNotIn("VIP", out.get("message", "").upper().replace(" ", ""), (vip, added))   # BL-288
            out = self.reply(ask(text=sel), f"Our {vip} sponsor is very happy.")                          # only repeats it: passes
            self.assertIn("happy", out["text"], vip)

    def test_html_inside_an_id_or_a_name_is_read_through(self):
        for added in (" ABC<!-- -->-A-004 is open.", " <b>ABC</b>-A-004 is open.", " ABC-A-00<b>4</b> is open.",
                      " Om<b>ar</b> Ali chases."):
            out = self.reply(ask(text=SAFE), SAFE + added)
            self.assertEqual(out["text"], "", added)

    def test_the_weekly_sheet_is_unchanged(self):
        out = self.reply(ask(place="report"), ORIGINAL + " ABC-005 is also open.")
        self.assertIn("ABC-005", out["text"])


if __name__ == "__main__":
    unittest.main()
