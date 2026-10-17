"""The client place kept as v2.1.0 shipped it, beside the approved #117 changes (proposal dev/proposals/edit-ai-client).

Run: python3 dev/tests/test_edit_ai_client_place.py

Done when: the integrated edit_ai.py gives, byte for byte,
- for the client sheet (#123's `client` place, gated by bound_place and client_problems): v2.1.0's options, format, Markdown rule,
  client rule and the whole prompt for every option it offers, and v2.1.0's refusals (no document, internal text in, internal text out);
- for the A4 sheet's places (report, minutes): v2.1.0's prompts (#117 leaves them as shipped);
- for every other place (notes, current, plain, email, line): the approved #117 proposal's prompts.

The expected outputs are frozen in dev/tests/snapshots/edit-ai-client-place.json, written only from the two references, never from
the file under test: v2.1.0's edit_ai.py (tag v2.1.0) for the client and sheet places, and the approved #117 file (origin/v220-editor-ai,
byte-identical to dev/proposals/edit-ai-117/edit_ai-combined.diff applied to v220-editor-base) for the rest. When git can show a
reference, the test also runs it and checks the frozen file still matches it. CREAITE_UPDATE_SNAPSHOTS=1 rewrites the frozen file
from the references (both must be available). test_reports' fixture and fixed clock; the data is fictional.
"""
import json
import os
import sqlite3
import subprocess
import sys
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_reports as R  # noqa: E402  (its fixture: populate, ReportVault, NOW)

REPO = Path(__file__).resolve().parents[2]
GOLDEN = Path(__file__).resolve().parent / "snapshots" / "edit-ai-client-place.json"
UPDATE = os.environ.get("CREAITE_UPDATE_SNAPSHOTS") == "1"
FILE = "system/scripts/edit_ai.py"
V210 = "v2.1.0"                                   # the client place as shipped
APPROVED = "origin/v220-editor-ai"                # the approved #117 file (Alan, on v220-editor-base)

DOC = {"kind": "client", "code": "ABC", "week_ending": "2026-10-09", "client": ""}   # the client sheet's report (#123)
TEXT = "Testing could start late.\n\nThe statement of work is signed."
NOTE = "agree the approach with legal\n\nthe uat dates is not confirmed\n\nsend the revised agrement by friday"
ASK = "Make it two sentences."


def cases():
    """Every (name, request) the frozen file holds: each option of each place that offers any."""
    out = []
    for o in ("shorter", "executive", "polish", "custom"):                       # the client sheet, as it sends a request
        out.append((f"client/{o}", {"option": o, "text": TEXT, "code": "ABC", "place": "client", "document": DOC,
                                    **({"instruction": ASK} if o == "custom" else {})}))
    out.append(("client-bound-from-report/polish", {"option": "polish", "text": TEXT, "code": "ABC", "place": "report",
                                                    "document": DOC}))
    for place in ("report", "minutes"):                                          # the A4 sheet: as v2.1.0 shipped it
        for o in ("shorter", "executive", "polish", "custom"):
            out.append((f"{place}/{o}", {"option": o, "text": TEXT, "code": "ABC", "place": place,
                                         **({"instruction": ASK} if o == "custom" else {})}))
    approved = {"notes": ["notes", "rewrite", "shorter", "longer", "executive", "format", "checklist", "summary", "custom"],
                "current": ["notes", "rewrite", "shorter", "longer", "executive", "format", "summary", "custom"],
                "plain": ["rewrite", "shorter", "executive", "custom"],
                "email": ["rewrite", "shorter", "longer", "formal", "warmer", "custom"],
                "line": ["rewrite", "shorter", "executive", "custom"]}
    for place, opts in approved.items():                                         # the #117 places: as approved
        for o in opts:
            text = "the uat start date is not confirmed" if place == "line" else NOTE
            out.append((f"{place}/{o}", {"option": o, "text": text, "code": "ABC", "place": place,
                                         **({"instruction": ASK} if o == "custom" else {})}))
    return out


REFUSALS = [   # the client gate's refusals, before anything goes to Claude
    ("client-no-document", {"option": "polish", "text": TEXT, "code": "ABC", "place": "client"}),
    ("client-internal-id-in", {"option": "polish", "text": "ABC-A-001 is late.", "code": "ABC", "place": "client",
                               "document": DOC}),
    ("client-other-project", {"option": "polish", "text": TEXT, "code": "ABC", "place": "client",
                              "document": {**DOC, "code": "DEF"}}),
]
REPLIES = [    # the client gate on what comes back
    ("client-reply-internal-id", "ABC-A-001 is late; testing could start late."),
    ("client-reply-owner-name", "Omar Ali says testing could start late."),
    ("client-reply-safe", "Testing may start late."),
]
CLIENT_KEYS = ("prompt", "option", "label", "format", "place", "people", "original", "code")
OTHER_KEYS = ("prompt", "option", "label", "format", "place", "people", "original")   # the approved file has no "code" key

RUNNER = r"""
import importlib, json, sys
sys.path.insert(0, 'system/scripts')
m = importlib.import_module(sys.argv[1])
spec = json.loads(sys.stdin.read())
out = {"contexts": {}, "refusals": {}, "replies": {}, "static": {}}
for name, req in spec["cases"]:
    try:
        out["contexts"][name] = m.context(req)
    except m.Refused as e:
        out["contexts"][name] = {"refused": str(e)}
if hasattr(m, "CLIENT_PLACES"):
    for name, req in spec["refusals"]:
        try:
            out["refusals"][name] = m.context(req)
        except m.Refused as e:
            out["refusals"][name] = {"refused": str(e)}
    ctx = m.context(spec["client"])
    for name, reply in spec["replies"]:
        out["replies"][name] = m.result({"context": ctx, "reply": "<<<SUGGESTION\n" + reply + "\nSUGGESTION>>>"})
    fr = m.FORMAT_RULES.get("client") or m.FORMAT_RULES[m.FORMATS["client"]].format(tasks="")
    out["static"] = {"options": m.PLACES["client"], "format": m.FORMATS["client"], "format_rule": fr,
                     "client_rule": m.CLIENT_RULE, "client_places": sorted(m.CLIENT_PLACES),
                     "offered": m.options()["client"]}
print(json.dumps(out))
"""


def git_show(ref):
    """The file at a ref, or None when this clone can't show it (a shallow CI clone, no tags fetched)."""
    r = subprocess.run(["git", "show", f"{ref}:{FILE}"], cwd=REPO, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 and r.stdout else None


class ClientPlaceKept(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = R.ReportVault()
        R.populate(cls.v)
        with closing(sqlite3.connect(cls.v.root / "system/tracker.db")) as con:    # a test vault: set directly
            con.execute("UPDATE projects SET health = 'Off track', health_reason = 'ZEBRAINTERNAL vendor late' WHERE code = 'ABC'")
            con.commit()
        cls.refs = {"v210": git_show(V210), "approved": git_show(APPROVED)}
        for name, src in cls.refs.items():
            if src is not None:
                (cls.v.root / "system/scripts" / f"edit_ai_{name}.py").write_text(src, encoding="utf-8")
        cls.got = {"edit_ai": cls.run_module("edit_ai")}
        for name, src in cls.refs.items():
            if src is not None:
                cls.got[name] = cls.run_module(f"edit_ai_{name}")
        if UPDATE:
            assert all(cls.refs.values()), "both references are needed to rewrite the frozen file"
            cls.write_golden()
        cls.golden = json.loads(GOLDEN.read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    @classmethod
    def run_module(cls, module):
        spec = {"cases": cases(), "refusals": REFUSALS, "replies": REPLIES,
                "client": {"option": "polish", "text": TEXT, "code": "ABC", "place": "client", "document": DOC}}
        r = subprocess.run([sys.executable, "-c", RUNNER, module], input=json.dumps(spec), cwd=cls.v.root,
                           env={**os.environ, "CREAITE_NOW": R.NOW}, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        return json.loads(r.stdout.strip().splitlines()[-1])

    @classmethod
    def write_golden(cls):
        a, b = cls.got["v210"], cls.got["approved"]
        ctxs = {}
        for name, _ in cases():
            place = name.split("/")[0]
            src = a if place.startswith("client") or place in ("report", "minutes") else b
            keys = CLIENT_KEYS if src is a else OTHER_KEYS
            ctxs[name] = {k: src["contexts"][name][k] for k in keys}
        GOLDEN.write_text(json.dumps({"from": {"client and sheet places": V210, "the #117 places": APPROVED},
                                      "static": a["static"], "contexts": ctxs, "refusals": a["refusals"],
                                      "replies": a["replies"]}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    def check(self, got, places, keys=None):
        for name, _ in cases():
            if name.split("/")[0] not in places:
                continue
            want = {k: v for k, v in self.golden["contexts"][name].items() if keys is None or k in keys}
            self.assertEqual({k: got["contexts"][name].get(k) for k in want}, want, name)

    # the file under test (always runs, against the frozen file)
    def test_the_client_place_options_format_rule_and_client_rule_are_v210s(self):
        self.assertEqual(self.got["edit_ai"]["static"], self.golden["static"])

    def test_every_client_option_gives_v210s_prompt_byte_for_byte(self):
        self.check(self.got["edit_ai"], ("client", "client-bound-from-report"))

    def test_the_client_gate_refuses_as_v210_did(self):
        self.assertEqual(self.got["edit_ai"]["refusals"], self.golden["refusals"])
        self.assertEqual(self.got["edit_ai"]["replies"], self.golden["replies"])

    def test_the_a4_sheet_places_keep_v210s_prompts(self):
        self.check(self.got["edit_ai"], ("report", "minutes"))

    def test_the_117_places_give_the_approved_proposals_prompts(self):
        self.check(self.got["edit_ai"], ("notes", "current", "plain", "email", "line"))

    def test_the_client_prompt_has_no_spelling_sentence_and_the_117_places_do(self):
        c = self.got["edit_ai"]["contexts"]
        self.assertNotIn("Also correct any spelling", c["client/shorter"]["prompt"])
        self.assertIn("Also correct any spelling", c["notes/shorter"]["prompt"])

    # the references (when this clone can show them): the frozen file is still theirs
    def test_the_frozen_client_and_sheet_outputs_are_v210s(self):
        if "v210" not in self.got:
            self.skipTest(f"git can't show {V210} here")
        self.assertEqual(self.got["v210"]["static"], self.golden["static"])
        self.assertEqual(self.got["v210"]["refusals"], self.golden["refusals"])
        self.assertEqual(self.got["v210"]["replies"], self.golden["replies"])
        self.check(self.got["v210"], ("client", "client-bound-from-report", "report", "minutes"))

    def test_the_frozen_117_outputs_are_the_approved_files(self):
        if "approved" not in self.got:
            self.skipTest(f"git can't show {APPROVED} here")
        self.check(self.got["approved"], ("notes", "current", "plain", "email", "line", "report", "minutes"), OTHER_KEYS)


if __name__ == "__main__":
    unittest.main()
