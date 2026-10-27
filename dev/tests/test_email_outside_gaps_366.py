"""#366 step 4 (gap fill, part B): the review kit's k26-a probes as tests (the Draft email to an outside recipient, #186; the follow
flag never shown, BL-288).

The kit (team-cap-reviewkit-26d, src/k26/a186.py) sent hostile replies and selections to edit_ai.py for an outside recipient.
test_email_client_facts_186 asserts only part of it; these cover what the step 1 audit found missing, in order of risk:
- the followed-person word (the follow flag's internal word, in the kit's 12 spellings) in the reply and in the selected text of an
  outside email: dropped or refused before Claude. #263 and #262 test it for Client messaging and the minutes only; an outside
  email is the same client-visible leak class;
- the hidden item's ID in all 32 of the kit's spellings in the reply, and 3 in the selection (186 asserts 4);
- the kit's address spoofs 186's SPOOFS lacks, the page-sent `internal` key and the other page-sent keys (each also with a hostile
  reply), the own-domain settings, and 10 spellings of the place with an outside address;
- the health reason written 6 ways, 8 internal-only markers, the hidden owner 8 ways and the hidden item's title.
A mutant (the kit's email_outside_off: email_outside always False, in the throwaway vault's own copy of edit_ai.py, never the
repo's) shows these tests see the leak.

Fictional data (test_reports' ABC fixture via test_email_client_facts_186: ABC-A-004 "Confirm tester names" is not client-visible
and owned by Omar Ali; ABC-A-002 is client-visible; the own domain is brightwater.example). Claude is never called: one subprocess
per batch runs the vault's own copy of edit_ai.py's context and result, as its `context` and `result` commands do.

Run: python3 dev/tests/test_email_outside_gaps_366.py      (quick tier: no Chrome, no Node)
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_email_client_facts_186 import (REASON, REPO, INSIDE, OUTSIDE, TEXT, _Vault,  # noqa: E402  (its vault and checks;
                                         ask, patched_vault)                         # by name, so this file stays quick tier)
HIDDEN, HIDDEN_TITLE, OWNER = "ABC-A-004", "Confirm tester names", "Omar Ali"
DROPPED = "shouldn't go outside your company"            # refusal(suggestion=True, outside=True)
REFUSED = "outside your company"                         # refusal(outside=True), before Claude
HOSTILE = "ABC-A-004 is late; please send the signed paperwork by Friday."
ZW = "​"

# The kit's lists (a186.py), word for word.
FOLLOW_WORDS = ("VIP", "vip", "V.I.P.", "V-I-P", "V_I_P", "V. I. P.", "ＶＩＰ", "VIPs", f"V{ZW}IP", "VІP",
                "ⅤIP", "v.i.p.s")
ID_FORMS = {
    "strict": HIDDEN, "lower": HIDDEN.lower(), "lower unpadded": "abc-a-4", "unpadded": "ABC-A-4",
    "en dash": HIDDEN.replace("-", "–"), "non-breaking hyphen": HIDDEN.replace("-", "‑"),
    "minus sign": HIDDEN.replace("-", "−"), "spaced": "ABC A 004", "letter spaced": "A B C - A - 0 0 4",
    "dotted": "ABC.A.004", "slashed": "ABC/A/004", "bracketed": "ABC (A) 004", "underscored": "ABC_A_004",
    "markdown escape": "ABC\\-A\\-004", "four digits": "ABC-A-0004", "four digits /1": "ABC-A-0004/1", "/1": "ABC-A-004/1",
    "four digits /1 (see)": "ABC-A-0004/1 (see)", "O for zero": "ABC-A-OO4", "html comment split": "ABC<!-- -->-A-004",
    "html bold split": "ABC<b>-A-</b>004", "html span name": "A<span>BC</span>-A-004", "zero width": f"ABC{ZW}-A-{ZW}004",
    "bidi mark": "ABC‎-A-004", "soft hyphen": "ABC­-A-004", "cyrillic ABC": "АВС-A-004",
    "greek A": "ABC-Α-004", "full-width digits": "ABC-A-００４", "arabic-indic digits": "ABC-A-٠٠٤",
    "run on word": "seeABC-A-004", "creaite link": f"[the plan](creaite:item/{HIDDEN})", "combining acute": "ABC-A-0́04",
}
ID_SELECTIONS = {"strict": HIDDEN, "en dash": HIDDEN.replace("-", "–"), "spaced": "ABC A 004"}
REASONS = {"as stored": REASON, "upper": REASON.upper(), "zero width": REASON.replace(" ", f" {ZW}"),
           "hyphens for spaces": REASON.replace(" ", "-"), "html split": REASON.replace("vendor", "ven<b>dor</b>"),
           "nbsp": REASON.replace(" ", " ")}
MARKERS = {"Internal only:": "Internal only: keep this away from the client.", "INTERNAL ONLY": "INTERNAL ONLY note for the team.",
           "Internal-only": "This is internal-only wording.", "(internal only)": "Budget moved (internal only).",
           "Confidential:": "Confidential: the budget moved.", "double space": "Internal  only: the budget moved.",
           "zero width inside": f"Inter{ZW}nal only: the budget moved.", "line break": "Internal\nonly: the budget moved."}
# (the kit's "Client-safe: no" is project-memory syntax, information only: the kit itself claims nothing for it)
OWNER_FORMS = {"as stored": OWNER, "lower": OWNER.lower(), "upper": OWNER.upper(), "double space": OWNER.replace(" ", "  "),
               "nbsp": OWNER.replace(" ", " "), "zero width": OWNER.replace("m", f"m{ZW}"), "html split": "Om<b>ar</b> Ali",
               "cyrillic O": "Оmar Ali"}
# The kit's spoofs that test_email_client_facts_186.TheAddresses.SPOOFS hasn't; each is outside. None: no recipients key at all.
SPOOFS = [["jane@бrightwater.example"], [INSIDE, None], [INSIDE, ["x@client.example"]], [INSIDE, {"a": 1}],
          ["a" * 400 + "@brightwater.example"], {"0": INSIDE}, 42, True, [], [""], None, [f"sam@brightwater.example{ZW}"],
          ["sam@brightwater.example , jane@client.example"], ["sam@brightwater.example%0a"],
          ["<sam@brightwater.example><jane@client.example>"], ["sam@brightwater.example <sam@brightwater.example>"],
          ["Sam <sam@brightwater.example> <jane@client.example>"], ["sam@brightwater.example\\, jane@client.example"]]
PAGE_KEYS = {"internal": True, "internal ": True, "internal list": ["client.example"], "outside": False, "audience": "internal",
             "own_domains": ["client.example"], "ownDomains": ["client.example"], "domains": ["client.example"],
             "identity": {"own_domains": ["client.example"]}}
NOT_EMAIL = "Addresses go only with the Draft email, so nothing was sent to Claude."     # edit_ai.NOT_EMAIL, as Alan reads it
PLACES = ("Email", " email", "email ", "EMAIL", "email\x00", "e-mail", "emaıl", "client", "client_message ", "Client_message")

DRIVER = r'''
import json, sys
sys.path.insert(0, "system/scripts")
import edit_ai
out = []
for job in json.loads(sys.stdin.read()):
    try:
        ctx = edit_ai.context(job["request"])
    except edit_ai.Refused as e:
        out.append({"ctx": {"refused": str(e)}})
        continue
    res = None
    if "reply" in job:
        res = edit_ai.result({"request": job["request"], "context": ctx,
                              "reply": "<<<SUGGESTION\n" + job["reply"] + "\nSUGGESTION>>>"})
    out.append({"ctx": ctx, "out": res})
print(json.dumps(out))
'''


def run(root, jobs):
    """Each job ({request, reply?}) through the vault's own edit_ai.py: its context, then the reply's result."""
    r = subprocess.run([sys.executable, "-c", DRIVER], input=json.dumps(jobs), cwd=root, capture_output=True, text=True, timeout=300)
    if r.returncode:
        raise AssertionError(f"edit_ai driver failed:\n{r.stdout[-500:]}{r.stderr[-1500:]}")
    got = json.loads(r.stdout.strip().splitlines()[-1])
    assert len(got) == len(jobs)
    return got


def reply_jobs():
    """Every hostile reply and selection for an outside email: (label, job, kind) with kind 'reply' or 'selection'."""
    jobs = []
    for w in FOLLOW_WORDS:
        jobs.append((f"followed word {w!r} in the reply", {"request": ask([OUTSIDE]),
                     "reply": f"Please send the signed paperwork by Friday; the {w} contact is waiting."}, "reply"))
        jobs.append((f"followed word {w!r} in the selection", {"request": ask([OUTSIDE], text=f"{w} contact: {TEXT}"),
                     "reply": "Please send the signed paperwork by Friday."}, "selection"))
    jobs.append(("followed word in a sentence, selected", {"request": ask([OUTSIDE], text="Our VIP sponsor agrees."),
                 "reply": "Our sponsor agrees."}, "selection"))
    for label, f in ID_FORMS.items():
        jobs.append((f"hidden ID {label} in the reply", {"request": ask([OUTSIDE]),
                     "reply": f"Please send the signed paperwork by Friday; {f} waits on it."}, "reply"))
    for label, f in ID_SELECTIONS.items():
        jobs.append((f"hidden ID {label} in the selection", {"request": ask([OUTSIDE], text=f"{f} is late; please chase the paperwork."),
                     "reply": "Please send the signed paperwork by Friday."}, "selection"))
    for label, w in REASONS.items():
        jobs.append((f"health reason {label}", {"request": ask([OUTSIDE]),
                     "reply": f"Please send the signed paperwork by Friday: {w}."}, "reply"))
    for label, w in MARKERS.items():
        jobs.append((f"marker {label}", {"request": ask([OUTSIDE]), "reply": f"Please send the signed paperwork by Friday. {w}"}, "reply"))
    for label, w in OWNER_FORMS.items():
        jobs.append((f"owner {label}", {"request": ask([OUTSIDE]), "reply": f"{w} asks that you send the signed paperwork by Friday."},
                     "reply"))
    jobs.append(("hidden item's title", {"request": ask([OUTSIDE]),
                 "reply": f"Please send the signed paperwork by Friday and {HIDDEN_TITLE.lower()}."}, "reply"))
    return jobs


class _Gaps(_Vault):
    def check_dropped(self, label, got, kind):
        ctx, out = got["ctx"], got.get("out")
        if kind == "selection":
            self.assertIn(REFUSED, ctx.get("refused", ""), f"{label}: the selection went to Claude")
            return
        self.assertClientFacts(ctx, label)
        self.assertEqual(out["text"], "", f"{label}: the suggestion came back")
        self.assertIn(DROPPED, out.get("message", ""), label)


class TheHostileReplies(_Gaps):
    """The followed-person word, every hidden ID spelling, the reason, markers, owner and title: dropped or refused before Claude."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.jobs = reply_jobs()
        cls.got = run(cls.root, [j for _l, j, _k in cls.jobs] +
                      [{"request": ask([OUTSIDE]), "reply": "Could you send the signed paperwork by Friday? ABC-A-002 waits on it."},
                       {"request": ask([INSIDE]), "reply": "Please send the signed paperwork by Friday; the VIP contact is waiting."}])

    def _section(self, prefix):
        rows = [(lbl, g, k) for (lbl, _j, k), g in zip(self.jobs, self.got) if lbl.startswith(prefix)]
        self.assertTrue(rows, prefix)
        for lbl, g, k in rows:
            with self.subTest(lbl):
                self.check_dropped(lbl, g, k)
        return rows

    def test_the_followed_person_word_never_reaches_an_outside_email(self):
        rows = self._section("followed word")
        self.assertEqual(len(rows), 2 * len(FOLLOW_WORDS) + 1)

    def test_every_spelling_of_a_hidden_id_is_dropped_or_refused(self):
        self.assertEqual(len(ID_FORMS), 32)
        self.assertEqual(len(self._section("hidden ID")), len(ID_FORMS) + len(ID_SELECTIONS))

    def test_the_health_reason_in_every_spelling_is_dropped(self):
        self._section("health reason")

    def test_internal_only_markers_are_dropped(self):
        self._section("marker")

    def test_the_hidden_owner_and_title_are_dropped(self):
        self._section("owner")
        self._section("hidden item's title")

    def test_controls_a_safe_reply_and_an_inside_email_come_back(self):
        safe, inside = self.got[-2:]
        self.assertIn("ABC-A-002", safe["out"]["text"])               # the checks don't drop everything
        self.assertNotIn("refused", inside["ctx"])
        self.assertFalse(inside["ctx"]["outside"])


class TheAddressesAndPlaces(_Gaps):
    """The kit's spoofs and page-sent keys are outside (client facts, a hostile reply dropped); other place spellings are refused."""

    def test_the_kits_other_spoofs_are_outside(self):
        reqs = [ask() if r is None else ask(r) for r in SPOOFS]
        for r, g in zip(SPOOFS, run(self.root, [{"request": q, "reply": HOSTILE} for q in reqs])):
            with self.subTest(json.dumps(r, ensure_ascii=True)[:70]):
                self.check_dropped(repr(r)[:70], g, "reply")

    def test_page_sent_keys_and_the_internal_key_are_ignored(self):
        reqs = {k: ask([OUTSIDE], **{k.replace(" list", ""): v}) for k, v in PAGE_KEYS.items()}
        for k, g in zip(reqs, run(self.root, [{"request": q, "reply": HOSTILE} for q in reqs.values()])):
            with self.subTest(k):
                self.check_dropped(f"page-sent {k}", g, "reply")
        # result decides again from the request: a context claiming inside (or a notes place) changes nothing
        ctx = run(self.root, [{"request": ask([OUTSIDE])}])[0]["ctx"]
        for forged in (dict(ctx, outside=False), dict(ctx, outside=False, internal=True), dict(ctx, outside=False, place="notes")):
            out = subprocess.run([sys.executable, str(self.root / "system/scripts/edit_ai.py"), "result"], cwd=self.root,
                                 input=json.dumps({"request": ask([OUTSIDE]), "context": forged,
                                                   "reply": f"<<<SUGGESTION\n{HOSTILE}\nSUGGESTION>>>"}),
                                 capture_output=True, text=True, timeout=120)
            self.assertEqual(json.loads(out.stdout)["text"], "", sorted(k for k in forged if forged[k] != ctx.get(k)))

    def test_own_domain_settings_the_page_cannot_widen(self):
        s = self.root / "system/config/settings.json"
        before = s.read_text(encoding="utf-8")
        self.addCleanup(s.write_text, before, encoding="utf-8")
        for label, given in (("missing", ...), ("a string", "brightwater.example"), ("[1]", [1]), ("[]", [])):
            d = json.loads(before)
            if given is ...:
                d["identity"].pop("own_domains", None)
            else:
                d["identity"]["own_domains"] = given
            s.write_text(json.dumps(d), encoding="utf-8")
            with self.subTest(label):
                self.check_dropped(f"own_domains {label}", run(self.root, [{"request": ask([INSIDE]), "reply": HOSTILE}])[0], "reply")

    def test_other_spellings_of_the_place_with_an_outside_address_are_refused(self):
        for sp, g in zip(PLACES, run(self.root, [{"request": {**ask([OUTSIDE]), "place": sp}} for sp in PLACES])):
            with self.subTest(repr(sp)):
                self.assertIn("refused", g["ctx"], f"{sp!r} went to Claude")
                self.assertNotIn(HIDDEN, json.dumps(g["ctx"]))

    def test_addresses_with_a_valid_place_that_is_not_the_draft_email_are_refused_by_that_check(self):
        """Cap's LOW 1: every spelling above is refused by an earlier check, so this reaches NOT_EMAIL itself (edit_ai.request)."""
        for place in ("notes", "minutes"):
            g = run(self.root, [{"request": {**ask([OUTSIDE]), "place": place}}])[0]
            with self.subTest(place):
                self.assertEqual(g["ctx"].get("refused"), NOT_EMAIL, g["ctx"])
                self.assertNotIn(HIDDEN, json.dumps(g["ctx"]))


class TheMutant(unittest.TestCase):
    """The kit's email_outside_off, in a throwaway vault's own copy of edit_ai.py: an outside email then gets the full facts and
    no checks, so the followed-person word, a hidden ID and the reason come back, and these tests would see it."""
    OLD = 'def email_outside(req):\n    """Whether a Draft email request goes to anyone outside (#186)'
    NEW = 'def email_outside(req):\n    return False\n    """Whether a Draft email request goes to anyone outside (#186)'

    def test_mutant_email_outside_off_lets_the_leaks_through(self):
        v = patched_vault()
        self.addCleanup(v.cleanup)
        p = v.root / "system/scripts/edit_ai.py"
        s = p.read_text(encoding="utf-8")
        self.assertEqual(s.count(self.OLD), 1, "the mutant's text isn't in edit_ai.py once")
        p.write_text(s.replace(self.OLD, self.NEW), encoding="utf-8")
        self.assertNotIn(self.NEW, (REPO / "system/scripts/edit_ai.py").read_text(encoding="utf-8"))   # the repo's copy untouched
        jobs = [{"request": ask([OUTSIDE]), "reply": "Please send the signed paperwork by Friday; the VIP contact is waiting."},
                {"request": ask([OUTSIDE], text=f"VIP contact: {TEXT}"), "reply": "Please send the signed paperwork by Friday."},
                {"request": ask([OUTSIDE]), "reply": HOSTILE},
                {"request": ask([OUTSIDE]), "reply": f"Please send the signed paperwork by Friday: {REASON}."}]
        got = run(v.root, jobs)
        self.assertIn("VIP", got[0]["out"]["text"])                    # the followed-person word reaches the outside email
        self.assertNotIn("refused", got[1]["ctx"])                     # the selection goes to Claude
        self.assertIn(HIDDEN, got[1]["ctx"]["prompt"])                 # with the full facts
        self.assertIn(HIDDEN, got[2]["out"]["text"])
        self.assertIn(REASON, got[3]["out"]["text"])


if __name__ == "__main__":
    unittest.main()
