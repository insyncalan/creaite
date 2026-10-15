"""BL-301 E (v20-find-updates): the mockup's catch-up note as a fixture: a Falcon Data Platform project with the items the note talks
about, the note itself, and a stand-in Claude that answers Find updates as the mockup shows. Never a real model call."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import action  # noqa: E402

NOW = "2026-10-13 10:00"
FOLDER = "FAL Falcon Data Platform"
NOTE = f"projects/{FOLDER}/notes/Catch-up with Omar.md"
SRC = f"projects/{FOLDER}/minutes/2026-10-06 Steering.docx — Actions"
BODY = """- Paper draft slipping to Tuesday 20-10. Sara's board is 21-10, so still OK.
- [ ] @Omar Ali to book a 30-minute review of the paper with Sara before 20-10
- Sandbox access granted yesterday.
- Phase 1 go-live probably moves two weeks, to 13-11. Omar to confirm with Jane.
- Test data refresh needs the same security sign-off. If the paper slips again, testing slips with it.
- Omar now reports to Rania Haddad, the new delivery director.
- Omar's team is tired after the cut-over. Worth a thank-you at the steering.
"""
NOTE_TEXT = ("---\ntitle: Catch-up with Omar\ncreated: 2026-10-13\nupdated: 2026-10-13\ntags: []\npinned: false\n"
             "confidential: false\ndate: 2026-10-13\nwith: [Omar Ali]\n---\n\n" + BODY)
PEOPLE = """# People register

## People

| Full name | Email | Aliases | Organisation | Role |
|-----------|-------|---------|--------------|------|
| Omar Ali | omar@enable.example | Omar | Enable | Project manager |
| Sara Khan | sara@enable.example | Sara | Enable | Security lead |
| Jane Doe | jane@enable.example | Jane | Enable | Sponsor |
| Alan Carter | alan@brightwater.example | Alan | Brightwater | Programme manager |
"""

# What the stand-in Claude answers for each line, keyed by words in the line: the mockup's rows.
ROWS = {
    "slipping to Tuesday": [{"kind": "update", "id": "FAL-A-002", "set": {"due_date": "2026-10-20"}, "why": "Draft slipping to Tuesday 20-10"}],
    "to book a 30-minute": [{"kind": "action", "title": "Book a 30-minute review of the classification paper with Sara", "owner": "Omar Ali",
                             "due": "2026-10-19", "why": "“before 20-10” → due the working day before"}],
    "granted yesterday": [{"kind": "done", "id": "FAL-A-001", "strength": "Looks done", "quote": "granted yesterday"}],
    "probably moves": [{"kind": "milestone", "id": "FAL-M-001", "forecast_date": "2026-11-13", "why": "moves two weeks"},
                       {"kind": "action", "title": "Confirm the phase 1 go-live date with Jane", "owner": "Omar Ali", "due": "2026-10-16",
                        "milestone": "FAL-M-001"}],
    "Test data refresh": [{"kind": "risk", "title": "Test data refresh depends on the same security sign-off", "owner": "Sara Khan",
                           "impact": "Medium", "likelihood": "Medium", "related": "FAL-003"}],
    "reports to Rania": [{"kind": "person", "name": "Rania Haddad", "role": "Delivery director", "org": "Enable"},
                         {"kind": "memory", "section": "People", "line": "Omar Ali reports to Rania Haddad from October 2026."}],
}


def reply_for(prompt_text, rows=None):
    """What the stand-in answers for a prompt: the rows for each line it was sent, as a ```json block."""
    import re
    out = []
    for n, t in re.findall(r"^\[p(\d+)\] (.*)$", prompt_text, re.M):
        for k, rs in (rows or ROWS).items():
            if k in t:
                out += [dict(r, p=int(n)) for r in rs]
    return "```json\n" + json.dumps({"rows": out}) + "\n```"


# The stand-in Claude for the live server: it keeps the prompt beside itself and answers with reply_for.
FAKE = r'''#!/usr/bin/env python3
import json, re, sys
ROWS = json.loads(%r)
args = sys.argv[1:]
p = args[args.index("-p") + 1]
open(__file__ + ".prompt", "w", encoding="utf-8").write(p)
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": "sess-n"})
rows = []
for n, t in re.findall(r"^\[p(\d+)\] (.*)$", p, re.M):
    for k, rs in ROWS.items():
        if k in t:
            rows += [dict(r, p=int(n)) for r in rs]
reply = "```json\n" + json.dumps({"rows": rows}) + "\n```"
out({"type": "assistant", "message": {"content": [{"type": "text", "text": reply}]}})
out({"type": "result", "result": reply, "session_id": "sess-n"})
''' % json.dumps(ROWS)


def load(v):
    """The Falcon project, its items and people, and the note."""
    reg = v.root / "projects/_portfolio/project-register.md"
    reg.write_text(reg.read_text().replace("|  |  |  |  |  |  |  |  |",
                                           f"| FAL | Falcon Data Platform | {FOLDER} | Falcon | Omar Ali (PM) | enable.example | FAL core | "
                                           "classification, sandbox |"))
    v.run("init")
    (v.root / "projects/_portfolio/people-register.md").write_text(PEOPLE)
    (v.root / "projects" / FOLDER).mkdir(parents=True, exist_ok=True)
    (v.root / "projects" / FOLDER / "CLAUDE.md").write_text("# FAL — Falcon Data Platform\n\n## Brief\n\n- **Client:** Enable\n\n"
                                                           "## People\n\n- Omar Ali is the client's project manager.\n\n"
                                                           "## Current state\n\nOn track.\n")
    v.propose("seed", [
        {"n": 1, "op": "new", "table": "milestones", "match": "strong", "flags": [], "decision": "approved",
         "values": {"project": "FAL", "name": "Phase 1 go-live", "baseline_date": "2026-10-30", "forecast_date": "2026-10-30",
                    "source": "Alan (cx-edit)"}},
        action(2, project="FAL", description="Request read-only sandbox access", owner="Omar Ali", due_date="2026-10-12",
               raised="2026-10-01", source=SRC),
        action(3, project="FAL", description="Draft the classification paper", owner="Omar Ali", due_date="2026-10-16",
               raised="2026-10-01", source=SRC),
        {"n": 4, "op": "new", "table": "raid", "match": "strong", "flags": [], "decision": "approved",
         "values": {"project": "FAL", "type": "Risk", "description": "Security sign-off for the classification paper is late",
                    "owner": "Sara Khan", "impact": "High", "likelihood": "Medium", "raised": "2026-10-01", "source": SRC}},
    ])
    v.run("apply")
    note = v.root / NOTE
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text(NOTE_TEXT, encoding="utf-8")


def install(v):
    """The stand-in Claude, executable, in the vault; returns its path."""
    fake = v.root / "fake_claude.py"
    fake.write_text(FAKE)
    fake.chmod(0o755)
    return fake

