"""2.6.8 (Cap's review kit, k26-b-bare): a value with no digit and no capital after Password / PIN / code is still a value.

Run: python3 dev/tests/test_invite_clean_bare.py      (quick tier: plain code and one throwaway vault, no Chrome, no Claude)

Since 2.5.3 `invite_clean` kept "Budget Password swordfish review", "Budget PIN rtyu" and a table's "PIN" / "kqzxyw" in a title, a place, an
organiser, an invite body and the saved calendar (12 of the kit's 27 cases). Now the word straight after those labels is the value and the
whole field (or the line, in a body) goes, except the few ordinary words in ALLOWED below, each with the reason. When unsure it removes.

- BARE: one row per label and value (fictional), each judged in the title, the place and the organiser (`scrub`), the body (`invite_text`),
  a row already saved by an earlier version (`clean_row`) and the saved calendar (`sweep.py calendar`).
- ALLOWED: one row per allow-list entry; the ordinary phrase must survive. Remove an entry from BARE_NEXT and its test fails.
- MUTANTS: the rule switched off, one allow-list entry removed, the rule restricted to Password (no PIN), no "code" label: each makes a
  test above fail, so the table is known to bite.
- NOT COVERED (stated as tests that pin today's behaviour, so a change is noticed): see NOT_COVERED.

All values are made up.
"""
import importlib.util
import json
import sys
import unittest
from datetime import timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parents[1] / "system" / "scripts"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SCRIPTS))
import invite_clean as I  # noqa: E402

# (id, text, the value that must not survive). One id per row; the text is a whole title, place, organiser or body line.
BARE = [
    ("password-word", "Budget Password swordfish review", "swordfish"),
    ("password-first", "Password swordfish", "swordfish"),
    ("password-lower", "password hunterxyz", "hunterxyz"),
    ("password-upper", "PASSWORD CORRECTHORSE", "CORRECTHORSE"),
    ("password-quoted", 'Sync Password "tangerine"', "tangerine"),
    ("password-bracket", "Sync (Password tangerine)", "tangerine"),
    ("password-german", "Sync Passwort schluessel", "schluessel"),
    ("password-french", "Sync Mot de passe motsecret", "motsecret"),
    ("password-spanish", "Sync Contrasena clavesecreta", "clavesecreta"),
    ("pin-letters", "Budget PIN rtyu", "rtyu"),
    ("pin-first", "PIN abcd", "abcd"),
    ("pin-number-word", "Sync PIN number abcd", "abcd"),
    ("pin-code-word", "Sync PIN code zxcvbn", "zxcvbn"),
    ("pin-lower", "Board pin qwerty", "qwerty"),
    ("pin-full-width", "Sync ＰＩＮ poiuyt", "poiuyt"),
    ("pin-zero-width", "Sync P​IN lkjhgf", "lkjhgf"),
    ("pin-cyrillic-a", "Sync PіN mnbvcx", "mnbvcx"),
    ("code-word", "Sync Code alphabeta", "alphabeta"),
    ("code-lower", "Town hall code gammadelta", "gammadelta"),
    ("reset-colon", "Password reset: hunter", "hunter"),                      # Full review HIGH 1: an allow-listed word is no shelter
    ("reset-bare", "Password reset hunter", "hunter"),
    ("reset-digits", "Password reset hunter2x", "hunter2x"),
    ("reset-equals", "Password reset = hunter", "hunter"),
    ("entry-bare", "PIN entry swordfish", "swordfish"),
    ("entry-colon", "PIN entry: swordfish", "swordfish"),
    ("policy-bare", "Password policy hunter", "hunter"),
    ("code-of-bare", "Code of hunter", "hunter"),
    ("password-underscore", "Password _swordfish", "swordfish"),
    ("spaced-pin", "Sync P I N abcdq", "abcdq"),
    ("dotted-pin", "Sync P.I.N. abcdq", "abcdq"),
    ("dashed-pin", "Sync P-I-N abcdq", "abcdq"),
    ("token", "Sync Token abcdq", "abcdq"),
    ("secret", "Sync Secret abcdq", "abcdq"),
    ("otp", "Sync OTP abcdq", "abcdq"),
    ("api-key", "Sync API key abcdq", "abcdq"),
    ("pw", "Sync Pw abcdq", "abcdq"),
    ("pswd", "Sync Pswd abcdq", "abcdq"),
    ("passphrase", "Sync Passphrase abcdq", "abcdq"),
    ("rv-00", "Password reset for hunter", "hunter"),   # Full review round 2
    ("rv-01", "Password reset and hunter", "hunter"),   # Full review round 2
    ("rv-02", "Password reset the hunter", "hunter"),   # Full review round 2
    ("rv-03", "Password reset to hunter", "hunter"),   # Full review round 2
    ("rv-04", "Password reset with hunter", "hunter"),   # Full review round 2
    ("rv-05", "Password reset in hunter", "hunter"),   # Full review round 2
    ("rv-06", "Password reset a hunter", "hunter"),   # Full review round 2
    ("rv-07", "Password reset or hunter", "hunter"),   # Full review round 2
    ("rv-08", "Password reset call swordfish", "swordfish"),   # Full review round 2
    ("rv-09", "Password reset sync swordfish", "swordfish"),   # Full review round 2
    ("rv-10", "Password reset plan swordfish", "swordfish"),   # Full review round 2
    ("rv-11", "Password reset update swordfish", "swordfish"),   # Full review round 2
    ("rv-12", "Password reset move swordfish", "swordfish"),   # Full review round 2
    ("rv-13", "Password reset request swordfish", "swordfish"),   # Full review round 2
    ("rv-14", "Code of the swordfish", "swordfish"),   # Full review round 2
    ("rv-15", "Code review of hunter", "hunter"),   # Full review round 2
    ("rv-16", "PIN entry and hunter", "hunter"),   # Full review round 2
    ("rv-17", "PIN pad for hunter", "hunter"),   # Full review round 2
    ("rv-18", "Password audit for hunter", "hunter"),   # Full review round 2
    ("rv-19", "Password change request hunter", "hunter"),   # Full review round 2
    ("rv-20", "Code standards with hunter", "hunter"),   # Full review round 2
    ("rv-21", "Password reset of: hunter", "hunter"),   # Full review round 2
    ("rv-22", "Password reset for: hunter", "hunter"),   # Full review round 2
    ("rv-23", "Password reset to=hunter", "hunter"),   # Full review round 2
    ("rv-24", "Password reset for\nhunter", "hunter"),   # Full review round 2
    ("rv-25", "Password reset for new hires", "hires"),   # Full review round 2
    ("rv-26", "Password reset - hunter", "hunter"),   # Full review round 2
    ("rv-27", "Password reset (hunter)", "hunter"),   # Full review round 2
    ("rv-28", "Pw: hunter", "hunter"),   # Full review round 2
    ("rv-29", "Pswd: hunter", "hunter"),   # Full review round 2
    ("rv-30", "Pw=hunter", "hunter"),   # Full review round 2
    ("rv-31", "Pw - hunter", "hunter"),   # Full review round 2
    ("rv-32", "Password , hunter", "hunter"),   # Full review round 2
    ("rv-33", "Password ; hunter", "hunter"),   # Full review round 2
    ("password-connecting-word", "Password for the room is hunterxyz", "hunterxyz"),   # "for" is taken as the value: fail closed
]
# HTML is read only in an invite body (a title, place or name is plain text from Outlook), so these rows are judged in the body only.
BODY_ONLY = [
    ("pin-table", "<table><tr><td>PIN</td><td>kqzxyw</td></tr></table>", "kqzxyw"),
    ("password-table", "<table><tr><td>Password</td><td>kqzxyw</td></tr></table>", "kqzxyw"),
    ("password-split-tags", "<p>Pass<b>word</b> swordfish</p>", "swordfish"),
]
# (id, the phrase that must survive in a title and in a body line, the allow-list entry it tests as (label, word))
ALLOWED = [
    ("password-reset", "Password reset workshop", ("password", "reset")),          # a common IT topic
    ("password-policy", "Password policy review", ("password", "policy")),         # the policy is not the password
    ("password-manager", "Password manager rollout", ("password", "manager")),     # a product class
    ("password-management", "Password management plan", ("password", "management")),
    ("password-expiry", "Password expiry changes", ("password", "expiry")),
    ("password-rotation", "Password rotation plan", ("password", "rotation")),
    ("password-audit", "Password audit findings", ("password", "audit")),          # a security review topic
    ("password-change", "Password change process", ("password", "change")),
    ("code-walkthrough", "Code walkthrough", ("code", "walkthrough")),
    ("code-standards", "Code standards workshop", ("code", "standards")),
    ("token-refresh", "Token refresh redesign", ("token", "refresh")),
    ("token-expiry", "Token expiry changes", ("token", "expiry")),
    ("token-rotation", "Token rotation plan", ("token", "rotation")),
    ("token-economy", "Token economy workshop", ("token", "economy")),
    ("token-economics", "Token economics workshop", ("token", "economics")),
    ("token-ring", "Token Ring retrospective", ("token", "ring")),
    ("secret-santa", "Secret santa plan", ("secret", "santa")),
    ("secrets-management", "Secrets management review", ("secret", "management")),
    ("secret-manager", "Secret manager rollout", ("secret", "manager")),
    ("secret-rotation", "Secret rotation plan", ("secret", "rotation")),
    ("otp-setup", "OTP setup plan", ("otp", "setup")),
    ("otp-rollout", "OTP rollout plan", ("otp", "rollout")),
    ("otp-enrolment", "OTP enrolment session", ("otp", "enrolment")),
    ("api-key-rotation", "API key rotation plan", ("api", "rotation")),
    ("api-key-management", "API key management review", ("api", "management")),
    ("api-key-review", "API key review", ("api", "review")),
    ("pin-entry", "PIN entry redesign", ("pin", "entry")),                          # a screen
    ("pin-pad", "PIN pad supplier call", ("pin", "pad")),                           # a device
    ("code-review", "Code review", ("code", "review")),
    ("code-reviews", "Code reviews", ("code", "reviews")),
    ("code-of-conduct", "Code of conduct session", ("code", "of")),
    ("code-base", "Code base review", ("code", "base")),
    ("code-freeze", "Code freeze planning", ("code", "freeze")),
    ("code-quality", "Code quality update", ("code", "quality")),
    ("source-code-repository", "Source code repository move", ("code", "repository")),
    ("code-handover", "Source code handover", ("code", "handover")),
]
FOLLOW_ROWS = ["Password reset for staff", "Code of conduct training", "Code review of the supplier SOW", "Code review sync", "Token Ring retrospective", "Password reset request", "Code of conduct session", "Password reset call",
               "Password change update", "PIN entry redesign", "Secret manager rollout", "Code freeze planning", "Code standards workshop"]
# A value on the NEXT line of an invite body (round 3). Each is judged with invite_text only.
NEXT_LINE = [
    ("nl-finished", "Password reset\nhunter", "hunter"),
    ("nl-finished-pin", "PIN entry\nswordfish", "swordfish"),
    ("nl-blank", "Password reset\n\n\nhunter", "hunter"),
    ("nl-function", "Password reset for\nhunter", "hunter"),
    ("nl-hyphen", "Password reset for -\nhunter", "hunter"),
    ("nl-en-dash", "Password reset for \u2013\nhunter", "hunter"),
    ("nl-em-dash", "Password reset for \u2014\nhunter", "hunter"),
    ("nl-colon", "Password reset for :\nhunter", "hunter"),
    ("nl-equals", "Password reset for =\nhunter", "hunter"),
    ("nl-paren", "Password reset (\nhunter", "hunter"),
    ("nl-bracket", "Password reset [\nhunter", "hunter"),
    ("nl-slash", "Password reset /\nhunter", "hunter"),
    ("nl-pipe", "Password reset |\nhunter", "hunter"),
    ("nl-after-sep-no-function", "Password reset \u2013\nhunter", "hunter"),
    ("nl-code", "Code review\nswordfish", "swordfish"),
    ("nl-token", "Token refresh\nabcdq", "abcdq"),
    ("w-the-plan", "Password reset\nthe plan\nhunter", "hunter"),                          # round 4: plain lines do not end the wait
    ("w-rollout-update", "Password reset\nrollout\nupdate\nhunter", "hunter"),
    ("w-sync", "Password reset\nsync\nhunter", "hunter"),
    ("w-staff-training", "Password reset\nstaff training\nhunter", "hunter"),
    ("w-blanks-5", "Password reset\n\n\n\n\n\nhunter", "hunter"),                      # blank lines are transparent
    ("w-blanks-between", "Password reset\nplan\n\n\n\nsync\n\n\n\nhunter", "hunter"),
    ("w-open-then-plain", "Password reset for\nplan\nsync\nhunter", "hunter"),
    ("w-sep-then-plain", "Password reset \u2013\nplan\nsync\nhunter", "hunter"),
    ("w-restart", "Password reset\nplan\nPIN entry\nsync\nplan\nhunter", "hunter"),        # a label line inside the window starts it again
    ("f-td", "<td>PIN</td><td>kqzxyw</td>", "kqzxyw"),                                    # bare fragments, no <html> or <table>
    ("f-td-rows", "<tr><td>Password</td></tr><tr><td>kqzxyw</td></tr>", "kqzxyw"),
    ("f-li", "<li>Password reset</li><li>hunter</li>", "hunter"),
    ("f-ul", "<ul><li>Password reset</li><li>plan</li><li>hunter</li></ul>", "hunter"),
    ("f-th", "<th>PIN entry</th><td>swordfish</td>", "swordfish"),
]
# The over-removal chosen for the next line (documented in the notes): after a finished label phrase the next line is kept only
# when every word of it is listed (an allow-listed or function word) and it holds no separator.
NEXT_LINE_LOST = ["Team standup at 10", "Agenda: budget", "Room 4", "Review and update", "Plan"]

# Ordinary text with no label near it stays whatever it holds.
CONTROLS = ["Quarterly business review", "Pilot readiness review", "Key milestones workshop", 
            "Passenger numbers", "Zipcode lookup", "Budget sync", "Pass the baton"]
# Titles that lose their whole text to "Meeting" (fail closed; named in the 2.6.8 notes). Each is a documented over-removal.
OVER_REMOVED = ["Pin the roadmap", "Password for all staff", "Code sprint", "Code clinic", "Code Red", "Pin board", "Secret Santa party",
                "Secret sauce", "Token of appreciation", "Secret project Falcon", "Password reset for new hires"]
# What this change does NOT do, pinned so that a change is noticed (each is a text that is still kept today).
NOT_COVERED = [
    ("a value before its label", "swordfish is the password", "swordfish"),
    ("the key label", "Sync Key hunterxyz", "hunterxyz"),
    ("the access label", "Sync Access hunterxyz", "hunterxyz"),
    ("the login label", "Sync Login hunterxyz", "hunterxyz"),
    ("the credentials label", "Sync Credentials hunterxyz", "hunterxyz"),
    ("the pass label", "Sync Pass hunterxyz", "hunterxyz"),
    ("a guest wifi key", "Guest wifi key hunterxyz", "hunterxyz"),
    ("the dial-in label", "Sync Dial-in hunterxyz", "hunterxyz"),
    ("Italian codice", "Sync Codice hunterxyz", "hunterxyz"),
    ("Spanish codigo", "Sync Codigo hunterxyz", "hunterxyz"),
    ("Turkish sifre", "Sync Sifre hunterxyz", "hunterxyz"),
    ("Romanian parola", "Sync Parola hunterxyz", "hunterxyz"),
    ("a letter-by-letter label of other kinds", "Sync P a s s hunterxyz", "hunterxyz"),
]


def fails(mod, table=None):
    """Names of the BARE rows (and places) that `mod` (an invite_clean module) lets through, and the ALLOWED rows it removes."""
    bad = []
    for rid, text, val in (BARE if table is None else table):
        for field, limit in (("title", 140), ("place", 80), ("organiser", 80)):
            if val.lower() in mod.scrub(text, limit).lower():
                bad.append(f"{rid}:{field}")
        if val.lower() in mod.invite_text("Agenda: budget\n" + text + "\nEnd").lower():
            bad.append(f"{rid}:body")
        row = mod.clean_row({"id": "e1", "start": "09:00", "end": "10:00", "title": text, "where": text, "organiser": text,
                             "body": text, "sensitivity": "normal"})
        if val.lower() in json.dumps(row, ensure_ascii=False).lower():
            bad.append(f"{rid}:clean_row")
    for rid, text, val in BODY_ONLY:
        if val.lower() in mod.invite_text("Agenda: budget\n" + text + "\nEnd").lower():
            bad.append(f"{rid}:body")
    for text in FOLLOW_ROWS:                     # the follow-on words (BARE_FOLLOW) that old titles need
        if mod.scrub(text, 140) != text:
            bad.append("follow:" + text)
    for rid, text, _entry in ALLOWED:
        if mod.scrub(text, 140) != text:
            bad.append(f"allowed:{rid}:title")
        if text not in mod.invite_text("Agenda: budget\n" + text + "\nEnd"):
            bad.append(f"allowed:{rid}:body")
    return bad


def mutant(old, new, count=1):
    """invite_clean's source with one change, loaded under another name (the checkout is never touched)."""
    src = (SCRIPTS / "invite_clean.py").read_text(encoding="utf-8")
    assert src.count(old) >= 1, f"mutant anchor not found: {old!r}"
    spec = importlib.util.spec_from_loader("invite_clean_mutant", loader=None)
    mod = importlib.util.module_from_spec(spec)
    mod.__file__ = str(SCRIPTS / "invite_clean.py")
    exec(compile(src.replace(old, new, count), "invite_clean_mutant", "exec"), mod.__dict__)
    return mod


class Rows(unittest.TestCase):
    """One test per row, made below."""


def _row_test(rid, text, val):
    def t(self):
        self.assertEqual(fails(I, [(rid, text, val)]), [], f"{text!r} keeps {val!r}")
    return t


for _rid, _text, _val in BARE:
    setattr(Rows, "test_removes_" + _rid.replace("-", "_"), _row_test(_rid, _text, _val))


def _body_test(rid, text, val):
    def t(self):
        self.assertNotIn(val.lower(), I.invite_text("Agenda: budget\n" + text + "\nEnd").lower(), text)
    return t


for _rid, _text, _val in BODY_ONLY:
    setattr(Rows, "test_body_removes_" + _rid.replace("-", "_"), _body_test(_rid, _text, _val))


def _allowed_test(rid, text):
    def t(self):
        self.assertEqual(I.scrub(text, 140), text)
        self.assertIn(text, I.invite_text("Agenda: budget\n" + text + "\nEnd"))
        self.assertIn(text, json.dumps(I.clean_row({"id": "e", "start": "09:00", "end": "10:00", "title": text,
                                                                           "sensitivity": "normal"})))
    return t


for _rid, _text, _entry in ALLOWED:
    setattr(Rows, "test_allowed_" + _rid.replace("-", "_"), _allowed_test(_rid, _text))


def _next_test(text, val):
    def t(self):
        out = I.invite_text("Agenda: budget\n" + text + "\nEnd").lower()
        self.assertNotIn(val, out, text)
    return t


for _rid, _text, _val in NEXT_LINE:
    setattr(Rows, "test_next_line_" + _rid.replace("-", "_"), _next_test(_text, _val))


class Controls(unittest.TestCase):
    def test_next_line_over_removal_is_as_documented(self):
        """After a line that ends a label phrase the next three lines with text are lost, plain words or not; the fourth is kept."""
        for ln in NEXT_LINE_LOST:
            out = I.invite_text("Welcome\nPassword reset\n" + ln + "\nSecond\nThird\nFourth line stays")
            self.assertNotIn(ln, out, ln)
            self.assertNotIn("Second", out)
            self.assertNotIn("Third", out)
            self.assertIn("Fourth line stays", out)                  # the line, Second and Third are the three; the fourth stays

    def test_lines_far_from_a_label_are_untouched(self):
        self.assertEqual(I.invite_text("Agenda: budget\nTeam standup at 10\nEnd"), "Agenda: budget\nTeam standup at 10\nEnd")


    def test_ordinary_titles_survive(self):
        for t in CONTROLS:
            self.assertEqual(I.scrub(t, 140), t, t)

    def test_follow_on_words_keep_their_phrase(self):
        for t in ("Code review sync", "Password reset request", "Code of conduct session", "Token Ring retrospective"):
            self.assertEqual(I.scrub(t, 140), t, t)

    def test_known_over_removal(self):
        """Fail closed costs a few ordinary titles: any word after pin / password / code that is not on the allow-list is a value."""
        for t in OVER_REMOVED:
            self.assertEqual(I.scrub(t, 140), "", t)

    def test_every_allow_list_entry_is_tested(self):
        listed = {(lab.split("|")[0].split("\\")[0].split("(")[0], w) for lab, ok in I.BARE_NEXT for w in ok}
        tested = {(lab, w) for _r, _t, (lab, w) in ALLOWED}
        self.assertEqual({w for _l, w in listed}, {w for _l, w in tested}, "an allow-list entry has no row in ALLOWED (or the reverse)")
        self.assertEqual(sum(len(ok) for _l, ok in I.BARE_NEXT), len(ALLOWED))

    def test_allow_list_is_short(self):
        self.assertLessEqual(sum(len(ok) for _l, ok in I.BARE_NEXT), 40)   # never "for", "the", "all" or other function words

    def test_not_covered_is_still_so(self):
        """Pins the gaps the release notes name; if one closes, move its row to BARE."""
        for why, text, val in NOT_COVERED:
            self.assertIn(val, I.scrub(text, 140), why)


class Timing(unittest.TestCase):
    def test_long_lines_stay_fast(self):
        import time
        for unit in ("Password reset ", "PIN entry: ", "Code of conduct ", "P I N ", "Token ", "a" * 50 + " ", "pass " * 3, "- . "):
            text = (unit * (2000 // len(unit) + 1))[:2000]
            t0 = time.time()
            I.scrub(text, 140)
            I.invite_text("Agenda\n" + text)
            self.assertLess(time.time() - t0, 2.0, unit)


class Saved(unittest.TestCase):
    """The calendar the sweep saves (sweep.py calendar in a throwaway vault): no row's value is in calendar.json, and a calendar saved
    by an earlier version is cleaned by clean_row when it is read again (below)."""

    def test_saved_calendar_holds_no_value(self):
        from test_tracker import Vault
        from test_dashboard import today
        v = Vault()
        self.addCleanup(v.cleanup)
        v.run("init")
        day = (today() + timedelta(days=1)).isoformat()
        evs = []
        for i, (_rid, text, _val) in enumerate(BARE):
            evs.append({"id": f"b{i}", "start": f"{8 + i // 6:02d}:{(i % 6) * 10:02d}", "end": f"{8 + i // 6:02d}:{(i % 6) * 10 + 5:02d}",
                        "title": text, "where": text, "organiser": text, "teams": True, "sensitivity": "normal", "body": f"Agenda: budget\n{text}",
                        "attachments": [text + ".docx"], "attendees": [{"name": text, "email": "a@brightwater.example"}]})
        spec = v.root / "system/staging/drafts/calendar.json"
        spec.parent.mkdir(parents=True, exist_ok=True)
        spec.write_text(json.dumps({"days": {day: evs}}))
        r = v.run("calendar", str(spec), script="sweep.py", ok=False)
        cal = (v.root / "system/staging/calendar.json").read_text(encoding="utf-8").lower()
        logs = "".join(f.read_text(encoding="utf-8", errors="ignore") for f in (v.root / "system/logs").glob("debug-*.log")).lower()
        out = (r.stdout + r.stderr).lower()
        for rid, _text, val in BARE:
            self.assertNotIn(val.lower(), cal, f"{rid} is in calendar.json")
            self.assertNotIn(val.lower(), out, f"{rid} is in the command output")
            self.assertNotIn(val.lower(), logs, f"{rid} is in the debug log")
        self.assertIn("agenda: budget", cal)

    def test_old_saved_entry_is_cleaned_at_session_start(self):
        """An entry saved by 2.5.3 to 2.6.7 that kept a value (any day, not only a past one) is cleaned once by sweep.rescrub_calendar,
        which session.py start runs; a clean calendar is not rewritten."""
        from test_tracker import Vault
        v = Vault()
        self.addCleanup(v.cleanup)
        v.run("init")
        old = {"id": "o1", "start": "09:00", "end": "10:00", "title": "Budget Password swordfish review", "where": "Room PIN rtyu",
               "organiser": "Pat Doe", "sensitivity": "normal", "body": "Agenda: budget\nPassword swordfish"}
        cal = v.root / "system/staging/calendar.json"
        cal.write_text(json.dumps({"fetched": "2026-10-20 08:00", "days": {"2026-10-26": [old]}}), encoding="utf-8")
        code = ("import sys; sys.path.insert(0, 'system/scripts')\nimport sweep\nprint(sweep.rescrub_calendar(), sweep.rescrub_calendar())")
        import subprocess
        r = subprocess.run([sys.executable, "-c", code], cwd=v.root, capture_output=True, text=True)
        self.assertEqual(r.stdout.split(), ["1", "0"], r.stdout + r.stderr)      # cleaned once, then nothing more to do
        flat = cal.read_text(encoding="utf-8").lower()
        self.assertNotIn("swordfish", flat)
        self.assertNotIn("rtyu", flat)
        self.assertIn("agenda: budget", flat)
        self.assertIn("rescrub_calendar", (SCRIPTS / "session.py").read_text(encoding="utf-8"))


class Mutants(unittest.TestCase):
    """Each change to the rule must make the table fail (so the table is known to bite)."""

    def test_baseline_passes(self):
        self.assertEqual(fails(I), [])

    def test_rule_off(self):
        self.assertNotEqual(fails(mutant('|(?<![\\w-])(?:{_BARE_NEXT})|', "|")), [])

    def test_only_password(self):
        # the pin and code labels dropped from the rule: the PIN and code rows must fail
        bad = fails(mutant('    (r"pin(?:\\s*(?:code|number|no\\.?))?", ("entry", "pad")),', ""))
        self.assertTrue(any(b.startswith("pin") for b in bad), bad)

    def test_no_code_label(self):
        bad = fails(mutant('    (r"codes?",', '    (r"nevermatch99",'))
        self.assertTrue(any(b.startswith("code") for b in bad), bad)

    def test_each_allow_entry_removed(self):
        for _lab, ok in I.BARE_NEXT:
            for w in ok:
                src_old = f'"{w}"'
                m = mutant(src_old, '"zzznever"')
                self.assertNotEqual(fails(m), [], f"removing {w!r} from the allow-list changed nothing")

    def test_whole_phrase_check_removed(self):
        """The rule that every word to the end must be listed: with a single following word looked at (the old rule), the round-2 examples live."""
        bad = fails(mutant("|\\s+(?!(?:{words})(?![\\w-]))[\\w\\\"'(\\[])", ")"))
        self.assertTrue(any(b.startswith("rv-") for b in bad), bad)

    def test_function_word_exemption(self):
        """Any word allowed after the first listed word (the exemption widened to everything) lets the round-2 examples through."""
        bad = fails(mutant('words = "|".join((*ok, *BARE_FOLLOW))', 'words = r"\\w+"'))
        self.assertTrue(any(b.startswith("rv-") for b in bad), bad)

    def test_punctuation_check_off(self):
        bad = fails(mutant("\\s*[:=\\-\\u2013\\u2014(\\[]|", ""))
        self.assertTrue(any(b in ("rv-21:title", "rv-22:title", "rv-26:title", "rv-27:title") or b.startswith(("rv-21", "rv-26")) for b in bad), bad)

    def next_line_bad(self, m):
        return [rid for rid, text, val in NEXT_LINE if val in m.invite_text("Agenda: budget\n" + text + "\nEnd").lower()]

    def test_window_off(self):
        m = mutant("WINDOW = 3 ", "WINDOW = 0 ")
        self.assertTrue({"nl-finished", "nl-function", "w-the-plan"} <= set(self.next_line_bad(m)), self.next_line_bad(m))

    def test_window_shortened(self):
        m = mutant("WINDOW = 3 ", "WINDOW = 2 ")
        bad = self.next_line_bad(m)
        self.assertIn("w-rollout-update", bad)
        self.assertNotIn("nl-finished", bad)                       # one and two lines are still caught: only the third leaks

    def test_blank_lines_consume_the_window(self):
        m = mutant("            alone = alone and blanks <= 2\n", "            alone = alone and blanks <= 2\n            window = max(window - 1, 0)\n")
        self.assertTrue({"w-blanks-5", "w-blanks-between"} <= set(self.next_line_bad(m)), self.next_line_bad(m))

    def test_fragment_conversion_off(self):
        m = mutant("a|td|th|tr|li|ul|ol|h[1-6]|b|i|u|em|strong|font)", "a)")
        self.assertTrue({"f-td", "f-li", "f-ul", "f-th"} <= set(self.next_line_bad(m)), self.next_line_bad(m))

    def test_label_line_inside_the_window_does_not_restart_it(self):
        m = mutant("window = WINDOW if label else (max(window - 1, 0) if consumed else 0)", "window = max(window - 1, 0) if consumed else 0")
        self.assertIn("w-restart", self.next_line_bad(m))

    def test_finished_phrase_rule_off(self):
        m = mutant("or (not dropped and any(_BARE_END.search(v) for v in views))", "")
        self.assertIn("nl-finished", self.next_line_bad(m))

    def test_open_phrase_rule_off(self):
        m = mutant("return any(_BARE_OPEN.search(v) for v in views) or", "return False or")
        self.assertTrue({"nl-hyphen", "nl-function", "nl-slash"} & set(self.next_line_bad(m)), self.next_line_bad(m))

    def test_each_separator_removed(self):
        need = {r"\-": "nl-hyphen", r"\u2013": "nl-en-dash", r"\u2014": "nl-em-dash", ":": "nl-colon", "=": "nl-equals", "(": "nl-paren",
                r"\[": "nl-bracket", "/": "nl-slash", "|": "nl-pipe"}
        base = r'[\-\u2013\u2014:=(\[/|]"  '
        for ch, rid in need.items():
            m = mutant(base, base.replace(ch, "", 1))
            self.assertIn(rid, self.next_line_bad(m), f"removing {ch!r} from the separators changed nothing for {rid}")

    def test_pw_pswd_separator_rule_off(self):
        bad = fails(mutant("clave\\s+de\\s+acceso|pw|pswd|pin", "clave\\s+de\\s+acceso|pin"))
        self.assertTrue(any(b.startswith(("rv-28", "rv-29", "rv-30", "rv-31")) for b in bad), bad)

    def test_punctuation_before_value_off(self):
        bad = fails(mutant("(?:\\s*[,;.]+\\s*\\w|\\s+[", "(?:\\s+["))
        self.assertTrue(any(b.startswith(("rv-32", "rv-33")) for b in bad), bad)

    def test_follow_list_entry_removed(self):
        for w in ("workshop", "rollout", "conduct", "supplier", "sync", "retrospective", "sow", "training", "staff"):
            self.assertNotEqual(fails(mutant(f'"{w}"', '"zzznever"', 3)), [], w)

    def test_spaced_pin_off(self):
        bad = fails(mutant('    s = _SPACED.sub("PIN", s)\n', ""))
        self.assertTrue(any("spaced" in b or "dotted" in b or "dashed" in b for b in bad), bad)

    def test_each_new_label_removed(self):
        for lab in ("tokens?", "secrets?", "otp", "api"):
            bad = fails(mutant(f'(r"{lab}', '(r"neverx9'))
            self.assertTrue(bad, lab)

    def test_fail_open_when_allow_list_is_everything(self):
        self.assertNotEqual(fails(mutant("(?:(?!(?:{okx})(?![\\w-]))\\w", "(?:(?!)\\w")), [])


if __name__ == "__main__":
    unittest.main()
