"""BL-229 wave 2 (v1.7.0): pin minutes.py stage (cmd_stage) before it is split. A run of meeting specs goes through
`minutes.py stage` in one throwaway vault, in order, and each one's exit code, printout, staged proposal and the mentions it
logged are compared with dev/tests/pinned/stage.json.

The specs reach every branch: a meeting for two projects with a draft and a transcript (new actions, decisions and risks;
an action with no owner or due date; a decision Made and one Pending; an item for a project not in the meeting; guessed
fields; an update, an update to an item that isn't there, an update that changes nothing; an item already open, which
becomes an update; one rejected before; status signals), the same meeting once processed, a quick note, a quick note with
a draft (refused), a transcript with no draft (refused), no project (refused), a transcript already in the project's
transcripts folder (never moved), and a transcript whose name has no date (flagged).

Run: python3 dev/tests/test_stage_pinned.py          (quick tier: no Chrome)
Record (only before the split, or for a reviewed change): CREAITE_PIN_RECORD=1 python3 dev/tests/test_stage_pinned.py
"""
import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import ABC, Vault, make_draft  # noqa: E402
from test_workstreams import add_project  # noqa: E402

PINNED = Path(__file__).resolve().parent / "pinned" / "stage.json"
RECORD = os.environ.get("CREAITE_PIN_RECORD") == "1"
DAY = "2026-10-01"
SRC = f"{ABC}/minutes/2026-09-20 Kick-off.docx — Actions"


def new(n, table, **v):
    return {"n": n, "op": "new", "table": table, "match": "strong", "flags": [], "decision": "approved",
            "values": {"project": "ABC", "source": SRC, **v}}


SEED = [new(1, "actions", description="Send revised SOW to client", owner="Alan Carter", raised="2026-09-20", due_date="2030-06-14"),
        new(2, "decisions", decision="Choose the pilot site", status="Pending", needed_by="2030-06-14"),
        new(3, "raid", type="Issue", description="Test data is late", owner="Omar Haddad", impact="Medium", raised="2026-09-20"),
        {**new(4, "actions", description="Book a team dinner", owner="Alan Carter", raised="2026-09-20"), "decision": "rejected"}]


def item(table, section=None, **values):
    return {"table": table, **({"section": section} if section else {}), "flags": [], "values": values}


MEETING_ITEMS = [
    item("actions", "Actions", project="ABC", description="Book the UAT environment", owner="Sara Example", due_date="2030-06-20"),
    item("actions", "Actions", project="ABC", description="Find a venue for the workshop"),                 # no owner, no due date
    item("decisions", "Decisions", project="ABC", decision="Go with vendor A"),                              # Made: dated the meeting
    item("decisions", "Decisions", project="ABC", decision="Agree the cut-over weekend", status="Pending", date="2026-10-01"),
    item("raid", "Risks", project="ABC", type="Risk", description="Vendor may slip", owner="Sara Example", impact="High", likelihood="Medium"),
    item("actions", "Actions", project="DEF", description="Plan the DEF demo", owner="Alan Carter"),
    item("actions", "Actions", project="XYZ", description="Not this meeting's project", owner="Alan Carter"),
    {**item("actions", "Actions", project="ABC", description="Write the test plan", owner="Omar Haddad"),
     "inferred": {"owner": "Omar said he would"}},
    {"op": "update", "table": "actions", "id": "ABC-A-001", "set": {"status": "Delayed"}, "why": "the client is away"},
    {"op": "update", "table": "actions", "id": "ABC-A-099", "set": {"status": "Closed"}, "why": "no such item"},
    {"op": "update", "table": "raid", "id": "ABC-003", "set": {"owner": "Omar Haddad"}, "why": "not a field minutes change"},
    {"op": "update", "table": "raid", "id": "ABC-003", "set": {"status": "Open"}, "why": "still open"},       # no change
    item("actions", "Actions", project="ABC", description="Send revised SOW to client", owner="Alan Carter", due_date="2030-07-01"),
    item("actions", "Actions", project="ABC", description="Book a team dinner", owner="Alan Carter"),
    item("decisions", "Decisions", project="ABC", decision="Choose the pilot site"),                         # makes the pending one
]


class Pinned(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.v = Vault()
        add_project(self.v, "DEF", "Digital Enablement")               # a second project for the two-project meeting
        self.v.run("init")
        self.v.propose("seed", SEED)
        self.v.run("apply")

    def tearDown(self):
        self.v.cleanup()

    def spec(self, name, **spec):
        f = self.v.root / "system/staging/drafts" / f"{name}.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(spec), encoding="utf-8")
        return f

    def stage(self, name, **spec):
        before = set((self.v.root / "system/staging").glob("proposed-*.json"))
        r = self.v.run("stage", str(self.spec(name, **spec)), script="minutes.py", ok=False, cwd=self.v.root)
        made = sorted(set((self.v.root / "system/staging").glob("proposed-*.json")) - before)
        proposal = json.loads(made[0].read_text(encoding="utf-8")) if made else None
        if proposal:
            proposal.pop("created", None)                     # when it was staged
            for p in made:
                p.unlink()                                    # each spec on its own: its proposal isn't pending for the next
        return {"spec": name, "exit": r.returncode, "out": r.stdout, "err": r.stderr[-600:], "proposal": proposal}

    def files(self, transcript, draft):
        (self.v.root / transcript).parent.mkdir(parents=True, exist_ok=True)
        (self.v.root / transcript).write_text("WEBVTT\n\n00:00.000 --> 00:02.000\n<v Alan>Welcome</v>\n", encoding="utf-8")
        make_draft(self.v.root / draft)

    def test_stage(self):
        out = []
        draft = "system/staging/drafts/2026-10-01 ABC Steering committee.docx"
        self.files("inbox/Recording 2026-10-01.vtt", draft)
        out.append(self.stage("meeting", date=DAY, title="ABC Steering committee", projects=["ABC", "DEF"],
                              transcript="inbox/Recording 2026-10-01.vtt", draft=draft, items=MEETING_ITEMS,
                              status_signals=["The client is happy with progress"]))
        self.files("inbox/Recording 2026-10-02.vtt", "system/staging/drafts/checkpoint.docx")   # the key reads the file
        key = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, 'system/scripts'); import minutes; "
                              f"print(minutes.meeting_key({DAY!r}, 'ABC Checkpoint', 'inbox/Recording 2026-10-02.vtt', None))"],
                             cwd=self.v.root, capture_output=True, text=True).stdout.strip()
        with open(self.v.root / "system/processed.txt", "a", encoding="utf-8") as f:
            f.write(f"2026-10-02 | {key} | already filed | 3\n")
        out.append(self.stage("processed", date=DAY, title="ABC Checkpoint", projects=["ABC"],
                              transcript="inbox/Recording 2026-10-02.vtt", draft="system/staging/drafts/checkpoint.docx", items=[]))
        note = f"{ABC}/minutes/2026-10-03 Quick note - catch-up.md"
        (self.v.root / note).write_text("# Quick note\n\nSara will send the plan.\n", encoding="utf-8")
        out.append(self.stage("quick note", date="2026-10-03", title="Quick note - catch-up", projects=["ABC"], note=note,
                              items=[item("actions", "Actions", project="ABC", description="Send the plan", owner="Sara Example",
                                          due_date="2030-06-10")]))
        out.append(self.stage("note with a draft", date="2026-10-03", title="Bad note", projects=["ABC"], note=note,
                              draft=draft, items=[]))
        self.files("inbox/Recording 2026-10-04.vtt", "system/staging/drafts/unused.docx")
        out.append(self.stage("transcript without a draft", date="2026-10-04", title="No draft", projects=["ABC"],
                              transcript="inbox/Recording 2026-10-04.vtt", items=[]))
        self.files("inbox/Recording 2026-10-05.vtt", "system/staging/drafts/noproject.docx")
        out.append(self.stage("no project", date="2026-10-05", title="Who is this", projects=[],
                              transcript="inbox/Recording 2026-10-05.vtt", draft="system/staging/drafts/noproject.docx", items=[]))
        inplace = f"{ABC}/transcripts/2026-10-06 ABC Design review.vtt"
        self.files(inplace, "system/staging/drafts/design.docx")
        out.append(self.stage("transcript in place", date="2026-10-06", title="ABC Design review", projects=["ABC"],
                              transcript=inplace, draft="system/staging/drafts/design.docx",
                              items=[item("actions", "Actions", project="ABC", description="Share the design", owner="Omar Haddad",
                                          due_date="2030-06-11")]))
        self.files("inbox/Recording.vtt", "system/staging/drafts/nodate.docx")
        out.append(self.stage("transcript with no date", date="2026-10-07", title="ABC Sync", projects=["ABC"],
                              transcript="inbox/Recording.vtt", draft="system/staging/drafts/nodate.docx",
                              items=[item("actions", "Actions", project="ABC", description="Chase the vendor", owner="Alan Carter",
                                          due_date="2030-06-12")]))
        mentions = self.v.root / "system/staging/mentions.jsonl"
        result = {"steps": out, "mentions": [json.loads(x) for x in mentions.read_text(encoding="utf-8").splitlines()]
                  if mentions.exists() else []}
        text = json.dumps(result, indent=1, sort_keys=True, ensure_ascii=False)
        text = text.replace(str(self.v.root.resolve()), "<VAULT>").replace(str(self.v.root), "<VAULT>")
        text = re.sub(r"proposed-\d{4}-\d\d-\d\d-\d{4}(-\d+)?\.json", "proposed-<STAMP>.json", text)
        text = re.sub(r"\d{4}-\d\d-\d\d[ T]\d\d:\d\d(:\d\d(\.\d+)?)?", "<TS>", text)
        text = re.sub(r"dashboard-\d{4}-\d\d-\d\d\.html", "dashboard-<DAY>.html", text)   # the apply's snapshot: today
        text = re.sub(r'"based_on": "[^"]*"', '"based_on": "<TS>"', text) + "\n"
        if RECORD:
            PINNED.write_text(text, encoding="utf-8")
        self.assertEqual(text, PINNED.read_text(encoding="utf-8"), "minutes.py stage changed")


if __name__ == "__main__":
    unittest.main()
