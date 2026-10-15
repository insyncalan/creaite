"""A stand-in Claude for the AI-draft tests (sprint-drafts-fields): never a real model call. It keeps the prompt it was given
(beside itself, `.prompt`) and prints a fixed reply for each kind of draft, in the stream-json shape the run engine reads."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_dashboard import d, populate  # noqa: E402

FAKE = r'''#!/usr/bin/env python3
import json, re, sys
args = sys.argv[1:]
p = args[args.index("-p") + 1]
open(__file__ + ".prompt", "w", encoding="utf-8").write(p)
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": "sess-d"})
if p.startswith("Draft the latest update for each action"):
    blocks = re.findall(r"^### (\S+)\n(.*?)(?=^### |\Z)", p, re.S | re.M)
    refs = [re.search(r"S[0-9]+", b).group() for _, b in blocks]
    reply = "\n".join(i + ": Raised again at the weekly sync. [" + r + "]" for (i, _), r in zip(blocks, refs))
elif p.startswith("Draft the latest update"):
    reply = "Jane Doe agreed to raise data access with the CIO. [S1] Escalation is on track."
elif p.startswith("Write the client messaging for each item"):
    ids = re.findall(r"^### (\S+)", p, re.M)
    reply = "\n".join("### " + i + "\nWhat it is: A delay in testing.\nWhat it means for you: Testing starts later.\nWhat is being done: We are escalating it.\nREMOVED:\n- nothing" for i in ids)
elif p.startswith("Write the client messaging"):
    reply = ("What it is: Access to your data for testing is late.\nWhat it means for you: Testing may start 14 days later than planned.\n"
             "What is being done: The team, with Tom, is raising it with your leadership.\nREMOVED:\n- the name Jane Doe\n- an internal code")
elif p.startswith("Suggest a response"):
    reply = ("RESPONSE: Escalate to the client CIO and test on masked data meanwhile. [S2]\nIMPACT: High | UAT cannot start without data [S1]\n"
             "LIKELIHOOD: Medium | access has been promised [S1]")
elif p.startswith("Suggest the options"):
    reply = "OPTIONS:\n- Keep the date and test on masked data. [S1]\n- Move go-live by two weeks. [S1]"
elif p.startswith("Suggest the reasoning"):
    reply = "REASONING:\nData access is late, so testing cannot finish in time. [S1] Nobody objected."
elif p.startswith("Write the reason for a health change"):
    reply = "Two actions are overdue and UAT start has slipped. [S1, S2]"
elif p.startswith("Sharpen one vague action"):
    reply = "TITLE: Confirm who owns the cut-over data extract [S1, S3]\nWHY: No verb or object; made both plain."
elif p.startswith("Write why the forecast"):
    reply = "The data access escalation is overdue, so UAT start moves. [S1]"
# ===== sprint-drafts-writing: BL-223, BL-224, BL-227 =====
elif p.startswith("Write the invite text"):
    reply = ("PURPOSE: Settle the pilot extension before it lapses. [S1]\nOBJECTIVES: Agree the extension and unblock data access. [S1, S3]\n"
             "APPROACH: Decisions first, then the overdue work.\nDELIVERABLES: A decision on the pilot and an owner for data access. [S1, S3]")
elif p.startswith("Write a short, friendly invite"):
    reply = "SUMMARY: A quick session to settle the pilot extension. [S1] Thanks for making the time."
elif p.startswith("Polish the opening of a request for help"):      # BL-298: Polish in the Draft chase pane, Alan's own item
    reply = ("TEXT: I'm picking up the back-to-back commercials and need your input to close them. [S1]\n"
             "OUTCOME: the Northgate commercials agreed on the Kestrel Group terms\nNEED: Tell me whether the Northgate terms can mirror the Kestrel Group contract.")
elif p.startswith("Polish the cover paragraph"):
    reply = "TEXT: A gentle nudge on the items below, which are now overdue. [S1]"
elif p.startswith("Write the project's status as"):
    form = re.search(r"FORM: (\S+)", p).group(1)
    reply = {"three": "UAT is at risk. [S1]\nData access is late. [S2]\nNext: escalate to the CIO. [S1]",
             "teams": "Quick update: UAT is at risk because data access is late. [S1]",
             "email": "UAT is at risk because data access is late. [S1] We are escalating it this week. [S2]",
             "steering": "**UAT is at risk.** [S1]\n- **Why.** Data access is late. [S2]"}.get(form, "Unknown form.")
# ===== v2.1.0 #90: the sheet's ✦ =====
elif p.startswith("Redraft one section"):
    reply = "A fresh draft of the section, in the house voice. [S1]"
# ===== end sprint-drafts-writing =====
else:
    reply = "I don't know this draft."
out({"type": "assistant", "message": {"content": [{"type": "text", "text": reply}]}})
out({"type": "result", "result": reply, "session_id": "sess-d"})
'''

ABC = "projects/ABC Example Programme"


def install(v):
    """The stand-in, executable, in the vault; returns its path."""
    fake = v.root / "fake_claude.py"
    fake.write_text(FAKE)
    fake.chmod(0o755)
    return fake


def prompt(fake):
    p = Path(str(fake) + ".prompt")
    return p.read_text(encoding="utf-8") if p.exists() else ""


def load(v):
    """populate(), and evidence for ABC-A-001 since it was raised: a later meeting that names it (and logged it as raised again),
    and a confidential board paper that names it too (never read)."""
    populate(v)
    (v.root / ABC / "minutes").mkdir(parents=True, exist_ok=True)
    (v.root / ABC / f"minutes/{d(-1)} Weekly sync.md").write_text(
        "# Weekly sync\n\nAttendees: Alan, Jane\n\nABC-A-001: Jane Doe agreed to raise data access with the CIO on Friday.\n\nOther business.\n")
    (v.root / ABC / f"minutes/{d(-1)} Confidential board.md").write_text("Board paper. ABC-A-001: the board secret plan.\n")
    (v.root / "system/staging/mentions.jsonl").write_text(
        f'{{"at": "{d(-1)}", "id": "ABC-A-001", "run": "x", "source": "{ABC}/minutes/{d(-1)} Weekly sync.md — Actions"}}\n')
    os.environ.setdefault("CREAITE_NO_LAUNCH", "1")
