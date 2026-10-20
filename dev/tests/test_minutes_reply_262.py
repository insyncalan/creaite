"""#262: the Internal minutes sheet's AI reply gets a client check on what it ADDS (the Distributed version is made from it).
PROPOSAL tests: they run against a patched scratch copy (#186's diff, then this one).

Run: python3 dev/tests/test_minutes_reply_262.py
Fail-first: MR_262_UNPATCHED=1 python3 dev/tests/test_minutes_reply_262.py   (the copy gets #186 only: the dropping tests go red, the
            facts and keeping tests stay green)
Mutations:  MR_262_MUTATE=<name> python3 dev/tests/test_minutes_reply_262.py   (see MUTATIONS; each must turn a test red)

`edit_ai.py` is not changed on this branch: the fix is dev/proposals/minutes-reply-262/edit_ai.diff, applied on top of #186's diff.
What it proves (test_reports' fictional ABC fixture):
- the minutes sheet keeps the full facts (it edits the Internal minutes) and its prompt is unchanged;
- a suggestion that adds an item a client may not see (in any spelling), a name the text and the client-visible items don't give,
  the internal health reason, an internal-only marker or VIP is dropped with the minutes' own message;
- what the selected text already held (an internal ID, an owner's name) passes, and so does a client-visible item;
- minutes with no project behind them can't be checked: the suggestion is dropped (fails closed);
- the other sheets (the weekly report's `report` place) are unchanged.
"""
import os
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_email_client_facts_186 as E  # noqa: E402  (its vault, its #186 patching and its helpers)

REPO = HERE.parents[1]
DIFF = Path(os.environ.get("MR_262_DIFF") or REPO / "dev" / "proposals" / "minutes-reply-262" / "edit_ai.diff")
UNPATCHED = os.environ.get("MR_262_UNPATCHED") == "1"
MUTATE = os.environ.get("MR_262_MUTATE", "")
MARKER = "MINUTES_PLACES = {"
DROPPED = "that the Distributed version would carry"
ORIGINAL = "ABC-A-004 is late; Omar Ali is confirming the testers. The statement of work is with the client."

MUTATIONS = {   # (what it breaks, old text, new text), all in edit_ai.py
    "no-minutes-check": ("the minutes reply isn't checked", "MINUTES_PLACES = {\"minutes\"}", "MINUTES_PLACES = set()"),
    "no-exempt": ("what the selection held is not exempt", "    had = set(client_problems(code, original, original))\n", "    had = set()\n"),
    "fail-open": ("a check that couldn't run lets the reply through",
                  "    if any(f in FAIL_CLOSED for f in found):\n        return found\n", ""),
    "plain-message": ("the minutes' own message is not used", "else MINUTES_DROPPED)", "else refusal(bad, True))"),
    # review of 693f0406
    "vip-hides": ("a selection holding VIP hides what the reply adds (the old order)",
                  "    text, original = _unprivate(text), _unprivate(original)\n", ""),
    "vip-added-ok": ("a reply adding VIP passes", " + ([\"something private\"] if added_private else [])", ""),
    "no-untag": ("HTML inside an ID or a name isn't read through", "    return text if bare == text else f\"{text}\\n{bare}\"\n",
                 "    return text\n"),
    "no-ready": ("minutes with no project or an unknown one go to Claude", "    if not code or not _project_known(code):\n",
                 "    if False:\n"),
}


def prepare(root):
    scripts = root / "system" / "scripts"
    has = MARKER in (scripts / "edit_ai.py").read_text(encoding="utf-8")
    if has == UNPATCHED:
        r = subprocess.run(["patch", "-p0", "-s", "-d", str(root), *(["-R"] if has else []), "-i", str(DIFF)],
                           capture_output=True, text=True)
        if r.returncode:
            raise AssertionError(f"patch failed:\n{r.stdout}{r.stderr}")
    if MUTATE and not UNPATCHED:
        _why, old, new = MUTATIONS[MUTATE]
        p = scripts / "edit_ai.py"
        s = p.read_text(encoding="utf-8")
        assert s.count(old) == 1, f"mutation {MUTATE}: its text isn't in edit_ai.py exactly once"
        p.write_text(s.replace(old, new), encoding="utf-8")


def ask(text=ORIGINAL, option="polish", place="minutes", code="ABC"):
    return {"option": option, "text": text, "code": code, "place": place}


class TheMinutesSheet(E._Vault):
    @classmethod
    def setUpClass(cls):
        cls.v = E.patched_vault()
        cls.root = cls.v.root
        prepare(cls.root)

    def reply(self, body, suggestion):
        return E.edit_ai(self.root, "result", {"request": body, "context": self.context(body),
                                               "reply": f"<<<SUGGESTION\n{suggestion}\nSUGGESTION>>>"})

    def test_the_sheet_keeps_the_full_facts(self):
        ctx = self.context(ask())
        self.assertFullFacts(ctx, "minutes")
        self.assertNotIn("This text is for the client.", ctx["prompt"])

    def test_a_suggestion_adding_something_internal_is_dropped(self):
        for added in ("ABC-005 is also open.", "abc 005 is also open.", "Jane Doe and Omar Ali agreed; ABC-M-001 slips.",
                      "Sara Example will chase.", "Health: " + E.REASON + ".", "Internal only: budget note.", "The VIP asked."):
            body = ask(text="The statement of work is with the client.")
            out = self.reply(body, "The statement of work is with the client. " + added)
            self.assertEqual(out["text"], "", added)
            self.assertIn(DROPPED, out.get("message", ""), added)

    def test_what_the_selection_held_passes_and_so_do_client_visible_items(self):
        out = self.reply(ask(), "ABC-A-004 is running late, as Omar Ali is still confirming testers. The client has the SOW.")
        self.assertIn("ABC-A-004", out["text"])
        out = self.reply(ask(), ORIGINAL + " ABC-A-002 is with the client.")
        self.assertIn("ABC-A-002", out["text"])

    def test_minutes_with_no_project_or_an_unknown_one_are_refused_before_claude(self):
        for code in ("", "ZZZ"):
            self.assertIn("no project in the tracker", self.context(ask(code=code)).get("refused", ""), code)
        # and a reply that gets there anyway (a context made by hand) is still dropped
        ctx = {"place": "minutes", "code": "", "original": "The statement of work is with the client.", "option": "polish"}
        out = E.edit_ai(self.root, "result", {"request": ask(code=""), "context": ctx,
                                              "reply": "<<<SUGGESTION\nThe statement of work is with the client.\nSUGGESTION>>>"})
        self.assertEqual(out["text"], "")

    def test_a_selection_holding_vip_still_has_the_reply_checked(self):
        for vip in ("VIP", "v.i.p", "V.I.P."):
            sel = f"Our {vip} sponsor is happy."
            for added in (" ABC-A-004 is open.", " Omar Ali chases.", " " + E.REASON + ".", " Internal only.", " ABC-005 waits."):
                out = self.reply(ask(text=sel), sel + added)
                self.assertEqual(out["text"], "", (vip, added))
                self.assertIn(DROPPED, out.get("message", ""), (vip, added))
                self.assertNotIn("VIP", out.get("message", "").upper().replace(" ", ""), (vip, added))   # BL-288
            out = self.reply(ask(text=sel), f"Our {vip} sponsor is very happy.")                          # only repeats it: passes
            self.assertIn("happy", out["text"], vip)

    def test_html_inside_an_id_or_a_name_is_read_through(self):
        sel = "The statement of work is with the client."
        for added in (" ABC<!-- -->-A-004 is open.", " <b>ABC</b>-A-004 is open.", " ABC-A-00<b>4</b> is open.", " Om<b>ar</b> Ali chases."):
            out = self.reply(ask(text=sel), sel + added)
            self.assertEqual(out["text"], "", added)

    def test_the_weekly_sheet_is_unchanged(self):
        out = self.reply(ask(place="report"), ORIGINAL + " ABC-005 is also open.")
        self.assertIn("ABC-005", out["text"])


if __name__ == "__main__":
    unittest.main()
