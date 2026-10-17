"""BL-186 (sprint-milestones): a project with the mockup's milestones (dev/mockups/milestones-views-mockup.html, Falcon Data
Platform), on top of test_dashboard.populate, for the Milestones page tests and the screenshots.

`load(v)` gives ABC six more milestones with the mockup's shape: one achieved, one overdue client-owned with a forecast move,
one internal At risk set by hand (with its reason), one client-visible At risk, Go-live rebaselined at steering (a decision) and
then slipped, and Hypercare knocked on. The forecast moves and the rebaseline are real applies; their change_log times are then
spread over the past reporting weeks, so Movement's chart has weeks to draw. Dates are relative to today.
"""
import sqlite3
import sys
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_dashboard import populate, today as pinned_today  # noqa: E402

TODAY = pinned_today()


def d(n):
    return (TODAY + timedelta(days=n)).isoformat()


def ms(n, name, base, fc=None, **v):
    return {"n": n, "op": "new", "table": "milestones", "match": "strong", "flags": [], "decision": "approved",
            "values": {"project": "ABC", "name": name, "baseline_date": base, "forecast_date": fc or base,
                       "source": "Alan (cx-edit), steering pack", **v}}


def up(n, id_, note=None, rebaseline=None, **ch):
    it = {"n": n, "op": "update", "table": "milestones", "id": id_, "changes": ch, "match": "strong", "flags": [], "decision": "approved"}
    if note:
        it["note"] = note
    if rebaseline:
        it["rebaseline"] = rebaseline
    return it


CW = {"cw1": "The build finished on the agreed date.",
      "cw2": "This is needed from the client before user acceptance testing can start.",
      "cw3": "Start depends on production data access.",
      "cw4": "Dates depend on production data access and the Design Authority review.",
      "cw5": "Follows go-live."}


def load(v):
    populate(v)
    v.propose("ms-seed", [
        ms(1, "Build complete (platform)", d(-28), status="Done", actual_date=d(-28), percent_complete=100, owner="Sara Example",
           client_visible=1, client_message=CW["cw1"]),
        ms(2, "Production data access granted", d(-10), owner="Omar Ali", percent_complete=50, client_visible=1, client_message=CW["cw2"],
           internal_note="Request re-submitted with security sign-off attached. Escalated to the sponsor."),
        ms(3, "Security review signed off", d(5), owner="Jane Doe", percent_complete=60, state="At risk",
           state_reason="Open 23 days against our usual 11."),
        ms(4, "UAT ready", d(23), owner="Sara Example", percent_complete=30, state="At risk",
           state_reason="Cannot start until production data access is granted.", client_visible=1, client_message=CW["cw3"]),
        ms(5, "Go-live", d(41), owner="Alan Carter", percent_complete=0, client_visible=1, client_message=CW["cw4"],
           internal_note="Sponsor call weekly until go-live."),
        ms(6, "Hypercare complete", d(111), owner="Omar Ali", percent_complete=0, client_visible=1, client_message=CW["cw5"]),
    ])
    v.run("apply")
    ids = {m: f"ABC-M-{n:03d}" for m, n in (("data", 4), ("golive", 7), ("hyper", 8))}
    # the moves, each its own apply, later dated into past weeks
    v.propose("mv1", [up(1, ids["golive"], note="Production data access not granted. Weekly report", forecast_date=d(55))]); v.run("apply")
    v.propose("mv2", [up(1, ids["golive"], baseline_date=d(62), forecast_date=d(62),
                         rebaseline={"agreed_with": ["Sara Example", "Omar Ali"], "reason": "Agreed with the steering committee",
                                     "source": "Steering minutes"})]); v.run("apply")
    v.propose("mv3", [up(1, ids["data"], note="Request re-submitted with security sign-off attached", forecast_date=d(5))]); v.run("apply")
    v.propose("mv4", [up(1, ids["golive"], note="Security review still open; Design Authority submission pending", forecast_date=d(69)),
                      up(2, ids["hyper"], note="Knock-on from Go-live", forecast_date=d(118))]); v.run("apply")
    spread(v)


def spread(v):
    """Date each apply into the reporting weeks before today: creation five weeks ago, then a week apart."""
    db = v.root / "system/tracker.db"
    with closing(sqlite3.connect(db)) as con:
        applies = [r[0] for r in con.execute("SELECT apply_id FROM applies ORDER BY apply_id")]
        last = applies[-5:]                                       # the seed and the four moves
        for i, a in enumerate(last):
            at = datetime.combine(TODAY - timedelta(days=7 * (len(last) - 1 - i) + 1), datetime.min.time()).replace(hour=10)
            stamp = at.strftime("%Y-%m-%d %H:%M:%S.000")
            con.execute("UPDATE change_log SET at = ? WHERE apply_id = ?", (stamp, a))
            con.execute("UPDATE applies SET at = ? WHERE apply_id = ?", (stamp, a))
        con.commit()
    # BL-327: the server's first page is the last built dashboard.html while the records' version (change_log, applies) is
    # unchanged, and re-dating the history doesn't move it; build the page again so Movement shows the spread weeks
    v.run(script="build_dashboard.py")
