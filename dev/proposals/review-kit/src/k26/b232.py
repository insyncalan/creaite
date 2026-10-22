"""2.6 area (b): the Intake Process / Refresh routes' calendar saves (#232, #264, #265). What reaches system/staging/calendar.json, and
whether any calendar content reaches a client output. Fictional hosts, numbers and words only (no real meeting link or passcode).
Each case prints:   ### CASE <name> | LEAK|PASS|HELD|CTRL-FAIL|SKIP | evidence
  LEAK  a join link, passcode, meeting ID or dial-in value (letters only too) is left in a saved field or text, or a calendar
        canary (body, attendee, attachment name, organiser, place of a confidential meeting) is in a client output
Usage: python b232.py <tree root> <variant>      variants: scrub (invite_clean on its own), bare (the labels that need a digit: pre-existing), save (sweep.py calendar in a vault),
                                                 body (invite_text), outputs (client report, exports, client one-pager, client drafts),
                                                 idpass (a numbered ID label then a password-family word: the ID must not shelter the letters-only value)
The known HIGH regression of origin/v26-review-fixes 4468986f (invite_clean.scrub keeps a value that has no digit) is the `scrub` and
`save` cases with a letter-only value."""
import json
import os
import re
import subprocess
import sys
import unittest
import zipfile
from datetime import timedelta
from pathlib import Path

ROOT = Path(sys.argv.pop(1))
VARIANT = sys.argv.pop(1)
sys.path.insert(0, str(ROOT / "dev" / "tests"))
sys.path.insert(0, str(ROOT / "system" / "scripts"))
sys.path.insert(0, str(ROOT / "system" / "scripts" / "vendor"))


def case(name, status, ev=""):
    print(f"### CASE {name} | {status} | {str(ev)[:200]}", flush=True)


# (label, text, the values that must not survive)
# Every secret value is unique to its case (a value shared by two cases would make one case's leak look like another's).
LETTER_FIELDS = [
    ("Steering Passcode: kqZxyw", "Steering Passcode: kqZxyw", ["kqZxyw"]),
    ("Meeting ID + Passcode letters", "Meeting ID 123 456 789 Passcode abcdef", ["abcdef", "123 456 789"]),
    ("zoom.us bare number", "Weekly sync zoom.us 98765432101", ["98765432101"]),
    ("passcode no colon", "Weekly sync passcode wqfhzn", ["wqfhzn"]),
    ("password word", "Budget Password swordfish review", ["swordfish"]),
    ("password colon", "Budget (Password: correcthorse)", ["correcthorse"]),
    ("PIN letters", "Budget PIN rtyu", ["rtyu"]),
    ("PIN digits", "Budget (PIN 7391)", ["7391"]),
    ("host key", "Board Host key: ZxCvBn", ["ZxCvBn"]),
    ("access code letters", "Board access code gammadelta", ["gammadelta"]),
    ("join code", "Town hall join code: alphabeta", ["alphabeta"]),
    ("passphrase", "Town hall passphrase tangerine", ["tangerine"]),
    ("pwd", "Sync pwd hunterxyz", ["hunterxyz"]),
    ("meeting id words", "Sync Meeting ID: one two three", ["one two three"]),
    ("dial-in + code letters", "Board dial-in +44 20 7946 0958 code mnopqr", ["mnopqr", "7946"]),
    ("dial-in only", "Dial-in: 020 8946 1128", ["8946", "1128"]),
    ("teams link", "Sync https://teams.microsoft.com/l/meetup-join/19%3ameeting_qzJtkW", ["meetup-join", "qzJtkW"]),
    ("zoom keyed link", "Sync https://zoom.us/j/55512340077?pwd=vBnMlK", ["55512340077", "vBnMlK"]),
    ("short link", "Sync bit.ly/xyzabc", ["xyzabc"]),
    ("webex vanity", "Town hall webex.com/meet/jdoe", ["jdoe"]),
    ("place zoom + passcode", "Zoom: zoom.us/j/12345678901 Passcode lkjhgf", ["lkjhgf", "12345678901"]),
    ("organiser passcode", "Pat Smith (Passcode: bcdfgh)", ["bcdfgh"]),
    ("full-width", "Sync \uff30\uff29\uff2e: poiuyt", ["poiuyt"]),
    ("zero-width inside label", "Sync Pass\u200bcode: asdfgh", ["asdfgh"]),
    ("cyrillic look-alike label", "Sync P\u0430sscode zxcvbn", ["zxcvbn"]),
    ("german", "Sync Passwort: schluessel", ["schluessel"]),
    ("passcode is", "Sync passcode is mkoijn", ["mkoijn"]),
    ("passcode newline", "Sync Passcode\nuhbygv", ["uhbygv"]),
    ("label then letters then more", "Passcode tfcrdx weekly steering", ["tfcrdx"]),
]
BODY_LINES = [
    ("Passcode: kqZxyw", ["kqZxyw"]), ("Passcode wqfhzn", ["wqfhzn"]), ("Passcode\nuhbygv", ["uhbygv"]),
    ("Meeting ID 123 456 789\nPasscode abcdef", ["abcdef", "123 456 789"]), ("Weekly sync zoom.us 98765432101", ["98765432101"]),
    ("Passcode is mkoijn", ["mkoijn"]), ("<p>Pass<b>code</b>: asdfgh</p>", ["asdfgh"]),
    ("<table><tr><td>PIN</td><td>kqzxyw</td></tr></table>", ["kqzxyw"]), ("Join code: alphabeta", ["alphabeta"]),
    ("Host key: ZxCvBn", ["ZxCvBn"]), ("Password swordfish", ["swordfish"]), ("Access code gammadelta", ["gammadelta"]),
    ("Dial in +44 20 7946 0958, then code mnopqr", ["7946", "mnopqr"]), ("https://zoom.us/j/55512340077?pwd=vBnMlK", ["55512340077", "vBnMlK"]),
]
# Labels that need a digit to be read as a key (pre-existing on 2.5.3: "Password swordfish", "PIN abcd" keep the word): their own probe
# (`bare`), so that the regression probes (`scrub`, `body`, `save`) judge only what 2.5.3 cut and 2.6 may have let back.
BARE_LABELS = {"password word", "PIN letters", "full-width"}
BARE_BODY = {"<table><tr><td>PIN</td><td>kqzxyw</td></tr></table>", "Password swordfish"}
BARE = VARIANT == "bare"
LETTER_FIELDS = [f for f in LETTER_FIELDS if (f[0] in BARE_LABELS) == BARE]
BODY_LINES = [b for b in BODY_LINES if (b[0] in BARE_BODY) == BARE]
KEEP = "Agenda: budget"


def gone(out, values):
    flat = re.sub(r"\s+", " ", out or "").lower()
    return [v for v in values if v.lower() in flat]


class Scrub(unittest.TestCase):
    def test_scrub(self):
        import invite_clean as I
        for label, text, values in LETTER_FIELDS:
            for field, limit in (("title", 140), ("place", 80), ("organiser", 80)):
                out = I.scrub(text, limit)
                left = gone(out, values)
                name = f"scrub {field}: {label}"
                if left:
                    case(name, "LEAK", f"{text!r} -> {out!r} keeps {left}")
                elif I.is_secret(out):
                    case(name, "LEAK", f"{text!r} -> {out!r} is still a secret")
                else:
                    case(name, "PASS" if out else "HELD", f"{text!r} -> {out!r}")
        # clean_row puts a row already saved by an earlier version through the same cleaning
        for label, text, values in LETTER_FIELDS[:12]:
            row = I.clean_row({"id": "e1", "start": "09:00", "end": "10:00", "title": text, "where": text, "organiser": text,
                               "sensitivity": "normal"})
            left = gone(json.dumps(row, ensure_ascii=False), values)
            case(f"clean_row: {label}", "LEAK" if left else "PASS", f"keeps {left}" if left else "no value kept")
        # controls: ordinary titles survive
        for t in ("Code review", "Quarterly business review", "Pilot readiness review", "Key milestones workshop"):
            out = I.scrub(t, 140)
            case(f"scrub control: {t}", "PASS" if out else "CTRL-FAIL", f"-> {out!r}")

    def test_body(self):
        import invite_clean as I
        for line, values in BODY_LINES:
            out = I.invite_text(KEEP + "\n" + line + "\nEnd")
            left = gone(out, values)
            case(f"invite_text: {line[:50]!r}", "LEAK" if left else "PASS", f"keeps {left}: {out!r}" if left else "dropped")
        # attendee and attachment names
        row = I.clean_row({"id": "e2", "start": "09:00", "end": "10:00", "title": "Review", "sensitivity": "normal",
                           "attachments": ["plan Passcode ghjklq.docx", "Agenda.docx", "join zoom.us 33344455566.pdf"],
                           "attendees": [{"name": "Sam Lee Passcode: zaqxsw", "email": "sam@brightwater.example"}, {"name": "Pat Doe"}]})
        left = gone(json.dumps(row), ["ghjklq", "33344455566", "zaqxsw"])
        case("clean_row: attachment and attendee names", "LEAK" if left else "PASS", f"keeps {left}" if left else "names with a key dropped")


class Saved(unittest.TestCase):
    """sweep.py calendar in a throwaway vault: calendar.json, the command's output and the debug log."""

    def setUp(self):
        from test_tracker import Vault
        from test_dashboard import today
        self.v = Vault()
        self.addCleanup(self.v.cleanup)
        self.v.run("init")
        self.day = (today() + timedelta(days=1)).isoformat()

    def save(self, events):
        spec = self.v.root / "system/staging/drafts/calendar.json"
        spec.parent.mkdir(parents=True, exist_ok=True)
        spec.write_text(json.dumps({"days": {self.day: events}}))
        r = self.v.run("calendar", str(spec), script="sweep.py", ok=False)
        cal = self.v.root / "system/staging/calendar.json"
        logs = "".join(f.read_text(encoding="utf-8", errors="ignore") for f in (self.v.root / "system/logs").glob("debug-*.log"))
        return r, (cal.read_text(encoding="utf-8") if cal.is_file() else ""), logs

    def test_save(self):
        evs = []
        for i, (label, text, values) in enumerate(LETTER_FIELDS):
            evs.append({"id": f"s{i}", "start": f"{8 + i // 6:02d}:{(i % 6) * 10:02d}", "end": f"{8 + i // 6:02d}:{(i % 6) * 10 + 5:02d}",
                        "title": text, "where": text, "organiser": text, "teams": True, "sensitivity": "normal",
                        "body": f"{KEEP}\n{text}", "attachments": [text + ".docx"], "attendees": [{"name": text, "email": "a@brightwater.example"}]})
        r, cal, logs = self.save(evs)
        if not cal:
            case("save: calendar.json written", "HELD", (r.stdout + r.stderr)[:160])
            return
        for label, text, values in LETTER_FIELDS:
            left_cal, left_out, left_log = gone(cal, values), gone(r.stdout + r.stderr, values), gone(logs, values)
            where = [n for n, x in (("calendar.json", left_cal), ("the command output", left_out), ("the debug log", left_log)) if x]
            case(f"save: {label}", "LEAK" if where else "PASS", f"{values[0]!r} is in {', '.join(where)}" if where else "no value saved")
        # confidential and private meetings: only the title and times of a confidential one; Busy for a private one
        conf = {"id": "c1", "start": "15:00", "end": "16:00", "title": "Board Meeting ID 246 810 121 Passcode edcrfv", "where": "KITCONFPLACE Room",
                "organiser": "KITCONFORG Person", "teams": True, "sensitivity": "confidential", "body": "KITCONFBODY roadmap",
                "attachments": ["KITCONFATTACH.docx"], "attendees": [{"name": "KITCONFATT Quentin", "email": "q@client.example"}],
                "recurrence": "KITCONFREC weekly", "organiser_email": "org@client.example"}
        priv = {"id": "p1", "start": "17:00", "end": "17:30", "title": "KITPRIVATE dentist", "sensitivity": "private", "body": "KITPRIVBODY",
                "where": "KITPRIVPLACE"}
        odd = {"id": "c2", "start": "18:00", "end": "18:30", "title": "KITODD Strictly Confidential plan", "sensitivity": "Strictly​ Confidential",
               "body": "KITODDBODY", "where": "KITODDPLACE", "attendees": ["KITODDATT Quentin"]}
        for flag in ("restricted", "2", "Secret", "CONFIDENTIAL ", "personal"):
            odd2 = {"id": "c3" + flag, "start": "19:00", "end": "19:30", "title": f"KITFLAG{len(flag)} meeting", "sensitivity": flag,
                    "body": "KITFLAGBODY", "where": "KITFLAGPLACE", "attendees": ["KITFLAGATT Quentin"]}
            evs.append(odd2)
        r, cal, logs = self.save([conf, priv, odd, *evs[-5:]])
        if not cal:
            case("save confidential: calendar.json written", "HELD", (r.stdout + r.stderr)[:160])
            return
        for name, tokens in (("confidential meeting keeps title and times only", ["KITCONFPLACE", "KITCONFORG", "KITCONFBODY", "KITCONFATTACH",
                                                                                 "KITCONFATT", "KITCONFREC", "org@client.example", "q@client.example",
                                                                                 "edcrfv", "246 810 121"]),
                             ("private meeting is Busy", ["KITPRIVATE", "KITPRIVBODY", "KITPRIVPLACE"]),
                             ("odd sensitivity text fails closed", ["KITODDBODY", "KITODDPLACE", "KITODDATT"]),
                             ("restricted/2/secret/personal fail closed", ["KITFLAGBODY", "KITFLAGPLACE", "KITFLAGATT"])):
            left = gone(cal, tokens)
            case(f"save: {name}", "LEAK" if left else "PASS", f"calendar.json holds {left}" if left else "none of it saved")
        left = gone(logs + r.stdout + r.stderr, ["KITCONF", "KITPRIV", "edcrfv", "KITODD", "KITFLAG"])
        case("save: no confidential or private word in the command output or the debug log", "LEAK" if left else "PASS", f"found {left}" if left else "clean")


# ---- idpass: "Meeting ID 12345 - Passcode abcdefg" (a numbered ID label, then a password-family word, then a letters-only value) ----
IDPASS_EXPLICIT = [
    ("Meeting ID 85212345678 - Passcode abcdefg", "abcdefg"), ("Steering Meeting ID 85212345678 – Passcode: Abcdefg", "abcdefg"),
    ("Webinar ID 12 is passcode abcdefg", "abcdefg"), ("PIN 4321 - passcode abcdefg", "abcdefg"), ("Code 2 = passcode abcdefg", "abcdefg"),
    ("Budget Meeting ID 12 - pwd abcdefg", "abcdefg"), ("Conference ID 55 - Passcode abcdefg review", "abcdefg"),
    ("Meeting ID 85212345678: Meeting password abcdefg", "abcdefg"), ("Meeting ID 85212345678 and Password abcdefg", "abcdefg"),
    ("Meeting ID 85212345678 with PIN kqzxyw", "kqzxyw"), ("Meeting ID 85212345678 then Key kqzxyw", "kqzxyw"),
    ("Meeting ID 85212345678: Pass-code: abcdefg", "abcdefg"), ("Meeting ID 85212345678 (PW: abcdefg)", "abcdefg"),
    ("Meeting ID 85212345678, Pass abcdefg", "abcdefg"), ("Meeting ID 12_Passcode abcdefg", "abcdefg"),
    ("Meeting ID 12 _Passcode_ abcdefg", "abcdefg"), ("Meeting ID 123456789 - Passcode1 abcdefg", "abcdefg"),
    ("Meeting ID 85212345678: Mot de passe abcdefg", "abcdefg"), ("Meeting ID 85212345678 and Kennwort abcdefg", "abcdefg"),
    ("Meeting ID 85212345678 and Contraseña abcdefg", "abcdefg"), ("abcdefg passcode", "abcdefg"),
]
ID_LABELS = ["Meeting ID", "Webinar ID", "Conference ID", "Event ID", "Call ID", "Session ID", "PIN", "Code"]
ID_WORDS = ["Passcode", "Pass code", "Passphrase", "Pass-code", "PWD", "PW", "Password", "Kennwort", "Mot de passe", "Contraseña"]
ID_JOINS = [" - ", ": ", " and ", " with ", " then ", ", ", " / ", " (", "_"]
ID_VALUES = ["abcdefg", "kqzxyw"]
ID_NUMBERS = ["85212345678", "852-1234-5678", "12", "4321"]
ID_STEP = 7                    # every 7th of the cross product (5760 cases -> 823): the same cases on every tree, a minute at most


def idpass_sample():
    """(text, value) for every ID_STEP-th case of labels x words x joins x values x numbers, in a fixed order."""
    import itertools
    out = []
    for n, (lab, word, join, val, num) in enumerate(itertools.product(ID_LABELS, ID_WORDS, ID_JOINS, ID_VALUES, ID_NUMBERS)):
        if n % ID_STEP == 0:
            out.append((f"{lab} {num}{join}{word} {val}" + (")" if join.endswith("(") else ""), val))
    return out


class IdPass(unittest.TestCase):
    """Where does the letters-only value survive: scrub (title, place, organiser), is_secret, invite_text, clean_row, sweep.calendar_row and the
    saved calendar.json. 2.5.3 drops the whole field for every case; a tree that lets the ID label shelter the word keeps the value."""

    def where(self, I, SW, text, val):
        """The places (names) in which val survives for one text."""
        hit = []
        for field, limit in (("title", 140), ("place", 80), ("organiser", 80)):
            out = I.scrub(text, limit)
            if gone(out, [val]):
                hit.append(f"scrub {field} -> {out!r}")
            elif I.is_secret(out):
                hit.append(f"is_secret(scrub {field}) -> {out!r}")
        if not I.is_secret(text):
            hit.append("is_secret(raw) False")
        body = I.invite_text(KEEP + "\n" + text + "\nEnd")
        if gone(body, [val]):
            hit.append(f"invite_text -> {body!r}")
        ev = {"id": "e1", "start": "09:00", "end": "10:00", "title": text, "where": text, "organiser": text, "teams": True, "sensitivity": "normal",
              "body": f"{KEEP}\n{text}", "attachments": [text + ".docx"], "attendees": [{"name": text, "email": "a@brightwater.example"}]}
        row = I.clean_row(dict(ev))
        if gone(json.dumps(row, ensure_ascii=False), [val]):
            hit.append(f"clean_row -> {json.dumps(row, ensure_ascii=False)[:90]}")
        crow = SW.calendar_row(dict(ev), "09:00", "10:00", False)
        if gone(json.dumps(crow, ensure_ascii=False), [val]):
            hit.append(f"calendar_row -> {json.dumps(crow, ensure_ascii=False)[:90]}")
        return hit

    def saved(self, cases):
        """({index: where} for the cases whose value is in the calendar.json that sweep.py calendar writes, the commands' output and the debug log
        as one text); chunks under the 500-meeting limit. (None, reason) when no calendar.json was written."""
        from test_tracker import Vault
        from test_dashboard import today
        v = Vault()
        self.addCleanup(v.cleanup)
        v.run("init")
        day = (today() + timedelta(days=1)).isoformat()
        left, extra = {}, ""
        for lo in range(0, len(cases), 300):
            evs = [{"id": f"i{k}", "start": "09:00", "end": "09:05", "title": t, "where": t, "organiser": t, "teams": True, "sensitivity": "normal",
                    "body": f"{KEEP}\n{t}", "attachments": [t + ".docx"], "attendees": [{"name": t, "email": "a@brightwater.example"}]}
                   for k, (t, _) in enumerate(cases[lo:lo + 300], lo)]
            spec = v.root / "system/staging/drafts/calendar.json"
            spec.parent.mkdir(parents=True, exist_ok=True)
            spec.write_text(json.dumps({"days": {day: evs}}))
            r = v.run("calendar", str(spec), script="sweep.py", ok=False)
            cal = v.root / "system/staging/calendar.json"
            if not cal.is_file():
                return None, (r.stdout + r.stderr)[:160]
            rows = {str(x.get("id")): x for rs in (json.loads(cal.read_text(encoding="utf-8")).get("days") or {}).values() for x in rs}
            for k, (t, val) in enumerate(cases[lo:lo + 300], lo):
                row = rows.get(f"i{k}")
                if row is not None and gone(json.dumps(row, ensure_ascii=False), [val]):
                    left[k] = f"calendar.json -> {json.dumps(row, ensure_ascii=False)[:90]}"
            extra += r.stdout + r.stderr
        extra += "".join(f.read_text(encoding="utf-8", errors="ignore") for f in (v.root / "system/logs").glob("debug-*.log"))
        return left, extra

    def test_idpass(self):
        import invite_clean as I
        import sweep as SW
        sample = idpass_sample()
        cases = [(t, v, f"idpass: {t!r}") for t, v in IDPASS_EXPLICIT] + [(t, v, f"idpass sample {k}: {t!r}") for k, (t, v) in enumerate(sample)]
        saved, extra = self.saved([(t, v) for t, v, _ in cases])
        if saved is None:
            case("idpass: calendar.json written", "HELD", extra)
            saved, extra = {}, ""
        else:
            left = gone(extra, ID_VALUES)
            case("idpass: command output and debug log", "LEAK" if left else "PASS", f"hold {left}" if left else "no value in either")
        leaks, quiet = 0, 0
        for k, (text, val, name) in enumerate(cases):
            hit = self.where(I, SW, text, val)
            if k in saved:
                hit.append(saved[k])
            if hit:
                leaks += 1
                places = ", ".join(h.split(" ->")[0] for h in hit)                       # the evidence is cut at 200 characters: the places first
                case(name, "LEAK", f"{val!r} survives in {places} | {hit[0]}")
            elif k < len(IDPASS_EXPLICIT):
                case(name, "PASS", "no value kept anywhere")
            else:
                quiet += 1
        print(f"idpass: {leaks} of {len(cases)} cases keep the value ({len(IDPASS_EXPLICIT)} listed, {len(sample)} sampled, every {ID_STEP}th of "
              f"{len(ID_LABELS) * len(ID_WORDS) * len(ID_JOINS) * len(ID_VALUES) * len(ID_NUMBERS)})", flush=True)
        if quiet:
            case("idpass: sampled cross product", "PASS", f"{quiet} sampled cases, no value kept in any place")
        for t in ("Code review", "Quarterly business review", "Key milestones workshop"):
            out = I.scrub(t, 140)
            case(f"idpass control: {t}", "PASS" if out else "CTRL-FAIL", f"-> {out!r}")


def build_outputs_class():
    import test_client_audience as A
    import test_report_export_save as S

    class Outputs(A.Audience):
        CAN = ["KITBODYCANARY", "Quentin Canary", "q.canary@client.example", "KITATTACH", "KITTITLECANARY", "KITORGCANARY", "KITPLACECANARY",
               "KITCONFBODY", "KITCONFATT"]

        def plant(self):
            from datetime import date
            day = (date.fromisoformat(S.NOW[:10]) + timedelta(days=1)).isoformat()   # the planted day follows the pinned CREAITE_NOW, not the real today (the 23-10 window of #318 left real today+1 outside it)
            ev = [{"id": "o1", "start": "09:00", "end": "10:00", "title": "KITTITLECANARY ABC steering", "where": "KITPLACECANARY room",
                   "organiser": "KITORGCANARY Person", "teams": True, "sensitivity": "normal",
                   "body": "KITBODYCANARY roadmap and budget talk", "attachments": ["KITATTACH-plan.docx"],
                   "attendees": [{"name": "Quentin Canary", "email": "q.canary@client.example"}]},
                  {"id": "o2", "start": "11:00", "end": "12:00", "title": "ABC board", "sensitivity": "confidential", "body": "KITCONFBODY",
                   "attendees": [{"name": "KITCONFATT Person", "email": "c@client.example"}]}]
            spec = self.v.root / "system/staging/drafts/calendar.json"
            spec.parent.mkdir(parents=True, exist_ok=True)
            spec.write_text(json.dumps({"days": {day: ev}}))
            r = subprocess.run([sys.executable, "system/scripts/sweep.py", "calendar", str(spec)], cwd=self.v.root, capture_output=True, text=True,
                               env={**os.environ, "CREAITE_NOW": S.NOW})
            cal = self.v.root / "system/staging/calendar.json"
            if not cal.is_file() or "KITBODYCANARY" not in cal.read_text(encoding="utf-8"):
                raise RuntimeError("calendar not saved with the canaries: " + (r.stdout + r.stderr)[-200:])

        def text_of(self, p):
            if p.suffix in (".docx", ".pptx", ".xlsx"):
                with zipfile.ZipFile(p) as z:
                    return "".join(z.read(n).decode("utf-8", "ignore") for n in z.namelist() if n.endswith(".xml"))
            return p.read_text(encoding="utf-8", errors="ignore")

        def test_outputs(self):
            self.plant()
            r = self.fresh()
            outs = {}
            for fmt in ("html", "docx"):
                e = self.export(fmt, "client", on_clash="number")
                if e.get("ok"):
                    outs["export-" + fmt] = self.text_of(self.v.root / e["path"])
            outs["draft"] = self.draft_file().read_text(encoding="utf-8") if self.draft_file().is_file() else ""
            a = self.post("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": A.WEEK, "force": True})
            if a.get("ok"):
                for f in self.reports.glob("*Client report*"):
                    outs["filed-" + f.suffix] = self.text_of(f)
            if len(outs) <= 1 and not any(outs.values()):
                case("outputs: client report", "HELD", "no client output was made")
            for name, text in outs.items():
                left = [c for c in self.CAN if c.lower() in text.lower()]
                case(f"outputs: client report {name}", "LEAK" if left else "PASS", f"holds {left}" if left else "no calendar content")
            # the client-safe steerco one-pager (Word) from the tracker, and its facts
            spec = self.v.root / "system/staging/drafts/steerco.json"
            spec.write_text(json.dumps({"code": "ABC", "version": "client", "summary": ["The programme is on course."]}))
            env = {**os.environ, "CREAITE_NOW": S.NOW}
            d = subprocess.run([sys.executable, "system/scripts/report.py", "steerco-data", "ABC", "--version", "client"], cwd=self.v.root,
                               capture_output=True, text=True, env=env)
            left = [c for c in self.CAN if c.lower() in d.stdout.lower()]
            case("outputs: steerco-data (client)", "LEAK" if left else "PASS", f"holds {left}" if left else f"{len(d.stdout)} bytes, no calendar content")
            s = subprocess.run([sys.executable, "system/scripts/report.py", "steerco-stage", str(spec)], cwd=self.v.root, capture_output=True, text=True, env=env)
            made = list((self.v.root / "system/staging/drafts").glob("*Steerco one-pager*"))
            if not made:
                case("outputs: client-safe steerco one-pager", "HELD", ((s.stdout + s.stderr).strip().splitlines() or ["nothing made"])[-1][:140])
            for f in made:
                left = [c for c in self.CAN if c.lower() in self.text_of(f).lower()]
                case(f"outputs: client-safe steerco one-pager {f.suffix}", "LEAK" if left else "PASS", f"holds {left}" if left else "no calendar content")
            # AI drafts: client-audience facts and prompts (status form, client wording), and the Draft email's polish
            for label, req in (("status-form client", {"kind": "status-form", "code": "ABC", "form": "email", "audience": "client",
                                                        "length": "short"}),
                               ("polish", {"kind": "polish", "text": "Dear team, a short update on KITTITLECANARY.", "tone": "warm"}),
                               ("client wording", {"kind": "client", "id": "ABC-A-003"})):
                p = subprocess.run([sys.executable, "system/scripts/drafts.py", "context"], input=json.dumps(req), cwd=self.v.root,
                                   capture_output=True, text=True, env=env)
                if p.returncode:
                    case(f"outputs: draft context {label}", "HELD", (p.stderr.strip().splitlines() or ["failed"])[-1][:120])
                    continue
                txt = p.stdout
                left = [c for c in self.CAN[:3] + self.CAN[3:] if c.lower() in txt.lower() and not (label == "polish" and c == "KITTITLECANARY")]
                case(f"outputs: draft context {label}", "LEAK" if left else "PASS", f"holds {left}" if left else "no calendar content")
            # the follow-up email's facts DO carry the invite's attendees (by design, for the meeting's own follow-up): a client
            # report or one-pager never does. Recorded as information, not as a leak.
            fu = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0,'system/scripts')\nimport drafts\n"
                                 "print(json.dumps(drafts.followup_facts({'eid':'o1'})))"], cwd=self.v.root, capture_output=True, text=True, env=env)
            case("outputs: follow-up email facts (information)", "PASS", "attendees from the invite, by design" if "Quentin" in fu.stdout else "no attendees")
    return Outputs


def main():
    if VARIANT in ("scrub", "body"):
        name = {"scrub": "Scrub.test_scrub", "body": "Scrub.test_body"}[VARIANT]
        unittest.main(argv=["x", name], verbosity=0)
    elif VARIANT == "bare":
        unittest.main(argv=["x", "Scrub.test_scrub", "Scrub.test_body", "Saved.test_save"], verbosity=0)
    elif VARIANT == "save":
        unittest.main(argv=["x", "Saved.test_save"], verbosity=0)
    elif VARIANT == "idpass":
        unittest.main(argv=["x", "IdPass.test_idpass"], verbosity=0)
    else:
        globals()["Outputs"] = build_outputs_class()
        unittest.main(argv=["x", "Outputs.test_outputs"], verbosity=0)


if __name__ == "__main__":
    main()
