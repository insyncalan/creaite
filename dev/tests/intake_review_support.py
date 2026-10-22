"""#232-B: shared fixture for the Review side of Intake's browser tests. A real vault, real proposals, the real row
model: one meeting ("Example steering") with routine actions and the items that need a decision, and mail and Teams proposals."""
import json

from test_dashboard import populate
from test_tracker import action

MAIL = "Email · From: Priya Nair <priya.nair@client.example> · Subject: Data residency · Sent: 2026-10-08 09:00 · Link: https://outlook.office365.com/owa/?ItemID=x"
TEAMS = "Teams · Chat: Omar · From: Omar · Sent: 2026-10-08 10:30"
MEETING = {"key": "fp:2026-10-05|steering|abc", "title": "Example steering", "date": "2026-10-05", "transcript": None,
           "projects": ["ABC"], "decision": "pending"}


def pending(item):
    return {**item, "decision": "pending"}


def meeting_items():
    """Four routine actions, a new risk, a new decision and a closing update: the last three need a decision."""
    src = "projects/ABC Example Programme/minutes/2026-10-05 Example steering.html — Actions"
    acts = [pending(action(i + 1, description=f"Steering action {i}", owner="Sara Example", due_date="2026-12-01", source=src)) for i in range(4)]
    return acts + [
        pending({"n": 5, "op": "new", "table": "raid", "match": "strong", "flags": [], "values": {"project": "ABC", "type": "Risk",
                 "description": "Scope creep from the pilot dataset", "owner": "Alan Carter", "impact": "High", "likelihood": "Medium", "source": src}}),
        pending({"n": 6, "op": "new", "table": "decisions", "match": "strong", "flags": [], "values": {"project": "ABC",
                 "decision": "Approve the revised timeline", "made_by": "Sara Example", "date": "2026-10-05", "source": src}}),
        pending({"n": 7, "op": "update", "table": "actions", "id": "ABC-A-001", "match": "strong", "flags": [], "changes": {"status": "Closed"},
                 "why": "Sara said it was sent", "source": src})]


def mail_items():
    return [
        pending({**action(4, description="Share the pilot plan with the client", owner="Sara Example", due_date="2026-11-04", source=MAIL), "flags": ["vip"]}),
        pending({**action(1, description="Confirm data residency with legal", owner="Sara Example", due_date="2026-11-02", source=MAIL), "match": "strong"}),
        pending({"n": 2, "op": "new", "table": "raid", "match": "strong", "flags": [], "values": {"project": "ABC", "type": "Risk",
                 "description": "Supplier may miss the November delivery", "owner": "Omar", "impact": "High", "likelihood": "Medium", "source": TEAMS}}),
        pending({"n": 3, "op": "update", "table": "actions", "id": "ABC-A-001", "match": "strong", "flags": [], "changes": {"status": "Closed"},
                 "why": "Looks done", "source": MAIL,
                 "suggested": {"feature": "done", "strength": "Looks done", "reason": "Sent by the owner",
                               "evidence": {"kind": "mail", "at": "2026-10-09 15:02", "who": "Sara Example", "quote": "attached the SOW", "source": MAIL}}})]


def load(v):
    populate(v)
    v.propose("2026-10-05-0900-steering", meeting_items(), meeting=MEETING)
    p = v.propose("2026-10-08-0900-sweep", mail_items())
    data = json.loads(p.read_text())
    data["source_run"] = "cx-sweep"
    p.write_text(json.dumps(data, indent=2))


def open_meeting(b):
    """Open the page and the one meeting; returns its id."""
    b.eval("irOpen.value=null; go('intake-review')")
    b.wait("!!document.querySelector('#v-intake-review [data-irm]')")
    mid = b.eval("(D.intake_review.meetings.find(m=>m.title==='Example steering')||{}).id")
    assert mid, "the fixture's meeting is not in the model"
    b.eval(f"document.querySelector('[data-irm={mid}] td.title').click()")
    b.wait(f"irOpen.value==={json.dumps(mid)} && !!document.querySelector('#v-intake-review tr.irprop')")
    return mid


def open_page(b):
    """The page with the mail and Teams section drawn."""
    b.eval("go('intake-review')")
    b.wait("!!document.querySelector('#v-intake-review [data-irsec=mail]') && !!document.querySelector('#v-intake-review [data-irsec=mail]').parentElement.querySelector('tr.irprop')")
