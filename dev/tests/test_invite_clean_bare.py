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
    ("pin-entry", "PIN entry redesign", ("pin", "entry")),                          # a screen
    ("pin-pad", "PIN pad supplier call", ("pin", "pad")),                           # a device
    ("code-review", "Code review", ("code", "review")),
    ("code-reviews", "Code reviews", ("code", "reviews")),
    ("code-of-conduct", "Code of conduct session", ("code", "of")),
    ("code-base", "Code base walkthrough", ("code", "base")),
    ("code-freeze", "Code freeze planning", ("code", "freeze")),
    ("code-quality", "Code quality update", ("code", "quality")),
    ("source-code-repository", "Source code repository move", ("code", "repository")),
    ("code-handover", "Source code handover", ("code", "handover")),
]
# Ordinary text with no label near it stays whatever it holds.
CONTROLS = ["Quarterly business review", "Pilot readiness review", "Key milestones workshop", 
            "Passenger numbers", "Zipcode lookup", "Budget sync", "Pass the baton"]
# What this change does NOT do, pinned so that a change is noticed (each is a text that is still kept today).
NOT_COVERED = [
    ("a value before its label", "swordfish password", "swordfish"),
    ("a value after an allow-listed word", "Password reset hunterxyz", "hunterxyz"),
    ("the key, token and access labels", "Sync Token hunterxyz", "hunterxyz"),
    ("a spaced-out label", "Sync P I N hunterxyz", "hunterxyz"),
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


class Controls(unittest.TestCase):
    def test_ordinary_titles_survive(self):
        for t in CONTROLS:
            self.assertEqual(I.scrub(t, 140), t, t)

    def test_known_over_removal(self):
        """Fail closed costs a few ordinary titles: any word after pin / password / code that is not on the allow-list is a value."""
        for t in ("Pin the roadmap on the wall", "Password for all staff"):
            self.assertEqual(I.scrub(t, 140), "", t)

    def test_every_allow_list_entry_is_tested(self):
        listed = {(lab.split("|")[0].split("\\")[0].split("(")[0], w) for lab, ok in I.BARE_NEXT for w in ok}
        tested = {(lab, w) for _r, _t, (lab, w) in ALLOWED}
        self.assertEqual({w for _l, w in listed}, {w for _l, w in tested}, "an allow-list entry has no row in ALLOWED (or the reverse)")
        self.assertEqual(sum(len(ok) for _l, ok in I.BARE_NEXT), len(ALLOWED))

    def test_allow_list_is_short(self):
        self.assertLessEqual(sum(len(ok) for _l, ok in I.BARE_NEXT), 20)   # never "for", "the", "all" or other function words

    def test_not_covered_is_still_so(self):
        """Pins the gaps the release notes name; if one closes, move its row to BARE."""
        for why, text, val in NOT_COVERED:
            self.assertIn(val, I.scrub(text, 140), why)


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

    def test_fail_open_when_allow_list_is_everything(self):
        self.assertNotEqual(fails(mutant("[^\\W_]", "(?!)")), [])


if __name__ == "__main__":
    unittest.main()
