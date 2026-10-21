"""Load or purge a fictional demo portfolio, to see how the dashboard looks with data.

Usage (from the dev repo root):
  python3 dev/tools/demo_data.py load     add four fictional projects (FAL, ORX, MER, TID) and a fictional week of
                                          meetings (the Inbox), and rebuild the dashboard
  python3 dev/tools/demo_data.py purge    remove them again

Development repo only (refuses to run without .creaite-dev). Dates are relative to today, so the demo always looks
current. Tracker rows go in through tracker.py apply as one apply, and purge reverses it with tracker.py undo,
so nothing bypasses the one-writer rule. The Word files are built in system/staging/drafts/ (BL-271: docx_tools.py
writes nowhere else) and filed into the project folders by that same apply's copy operations, as cx-minutes files
minutes (BL-292), so the undo removes them too. Project folders, the other files and staged proposals are created
directly and listed in system/staging/demo.json for purge. The project register is not changed. All data is fictional and git-ignored.
"""
import json
import shutil
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "system" / "scripts"))
import paths  # noqa: E402

STATE = paths.STAGING / "demo.json"
PROPOSAL = paths.STAGING / "proposed-0000-00-00-demo.json"
T = date.today()
CMT = "What it is: \nWhat it means for you: \nWhat is being done: "


def d(n):
    return (T + timedelta(days=n)).isoformat()


def fri(weeks_ago):
    last = T - timedelta(days=(T.weekday() - 4) % 7)
    return (last - timedelta(weeks=weeks_ago)).isoformat()


PROJECTS = [
    {"code": "FAL", "name": "Falcon Data Platform", "client": "Northgate Energy", "sponsor": "Rashid Al Suwaidi",
     "phase": "Build", "health": "Off track", "reason": "Go-live moved 3 weeks after the data access delay",
     "rhythm": "weekly", "trail": ["On track", "On track", "At risk", "At risk", "At risk", "Off track", "Off track", "Off track"],
     "current": "Build is complete for two of three data domains. Production data access from Northgate is three weeks "
                f"late, so go-live has moved to {d(68)}.\n\nA sponsor escalation is set for {d(3)}; the team continues on "
                "masked data meanwhile.",
     "ms": [("Build complete", d(-22), d(-22), "Done"), ("UAT start", d(29), d(29), "Planned"),
            ("Go-live", d(47), d(68), "Planned")]},
    {"code": "ORX", "name": "Orbit Customer App", "client": "Orbit Retail", "sponsor": "James Okafor", "phase": "UAT prep",
     "health": "At risk", "reason": "Two client actions more than 7 days overdue; UAT window under pressure",
     "rhythm": "fortnightly", "trail": ["On track"] * 5 + ["At risk", "On track", "At risk"],
     "current": f"Feature build is on plan. UAT starts {d(8)}, but the test data pack and two client approvals are overdue.",
     "ms": [("Feature freeze", d(-4), d(-4), "Done"), ("UAT start", d(8), d(8), "Planned"),
            ("UAT sign-off", d(19), d(19), "Planned")]},
    {"code": "MER", "name": "Meridian Contact Centre AI", "client": "Meridian Telecom", "sponsor": "Priya Nair",
     "phase": "Pilot", "health": "On track", "reason": "No overdue actions; pilot metrics ahead of target",
     "rhythm": "weekly", "trail": ["At risk"] + ["On track"] * 7,
     "current": "The pilot is live with 40 agents. Average handling time is down 11% against an 8% target.",
     "ms": [("Pilot live", d(-34), d(-34), "Done"), ("Pilot review", d(24), d(24), "Planned")]},
    {"code": "TID", "name": "Tide Billing Migration", "client": "Internal", "sponsor": "Omar Haddad", "phase": "Cut-over",
     "health": "On track", "reason": "Cut-over rehearsal 2 passed", "rhythm": "off", "trail": ["On track"] * 8,
     "current": "The second cut-over rehearsal passed with no severity-1 defects.",
     "ms": [("Rehearsal 2", d(-9), d(-9), "Done"), ("Final rehearsal", d(20), d(20), "Planned"),
            ("Cut-over", d(41), d(41), "Planned")]},
]
FAL_MIN = "projects/FAL Falcon Data Platform/minutes/"
EMAIL_ORX = (f"Email · From: James Okafor <james.okafor@orbitretail.example> · Subject: [ORX] UAT readiness · "
             f"Sent: {d(-13)} 16:48")
TEAMS_MER = f"Teams · Channel: MER pilot · From: Priya Nair · Sent: {d(-18)} 13:31"
# (project, description, workstream, owner, priority, due, status, raised, milestone index or None, source, client, update)
ACTIONS = [
    ("FAL", "Escalate production data access to Northgate CIO", "Data", "Alan Carter", "Urgent", d(3), "Open", d(-4), 2,
     FAL_MIN + f"{d(-4)} Steering committee.docx — Actions", False, f"{d(-3)}: CIO meeting requested"),
    ("FAL", "Confirm revised go-live plan with sponsor", "Governance", "Alan Carter", "High", d(-2), "Open", d(-11), 2,
     FAL_MIN + f"{d(-11)} Weekly delivery.docx — Actions", False, ""),
    ("FAL", "Provide masked sample datasets for domain 3", "Data", "Rashid Al Suwaidi (Northgate)", "High", d(-13), "Open",
     d(-20), 1, f"Email · From: Rashid Al Suwaidi <rashid@northgate.example> · Subject: [FAL] Domain 3 data · "
                f"Sent: {d(-20)} 10:20", True, f"{d(-5)}: chased; promised by {d(1)}"),
    ("FAL", "Complete security review of ingestion pipeline", "Build", "Lena Fischer", "Medium", d(5), "Open", d(-18), None,
     FAL_MIN + f"{d(-18)} Weekly delivery.docx — Actions", False, ""),
    ("ORX", "Deliver UAT test data pack", "Testing", "Mei Tan (Orbit)", "High", d(-11), "Open", d(-13), 1, EMAIL_ORX, True,
     f"{d(-4)}: partial pack this week"),
    ("ORX", "Approve payment-provider sandbox credentials", "Release", "James Okafor (Orbit)", "High", d(-12), "Open",
     d(-13), 1, EMAIL_ORX, False, ""),
    ("ORX", "Send UAT entry criteria to client", "Testing", "Alan Carter", "High", d(0), "Open", d(-6), 1,
     f"projects/ORX Orbit Customer App/minutes/{d(-6)} Project board.docx — Actions", False, ""),
    ("ORX", "Book UAT testers and rooms", "Testing", "Sara Khan", "Medium", d(3), "Open", d(-6), 1,
     f"projects/ORX Orbit Customer App/minutes/{d(-6)} Project board.docx — Actions", False, ""),
    ("MER", "Share week-4 pilot metrics pack", "Adoption", "Dev Patel", "Medium", d(1), "Open", d(-6), 1, TEAMS_MER, True, ""),
    ("MER", "Draft roll-out options paper for the pilot review", "Adoption", "Alan Carter", "Medium", d(15), "Open", d(-18),
     1, TEAMS_MER, False, ""),
    ("MER", "Agree pilot success criteria with Meridian", "Adoption", "Priya Nair (Meridian)", "Medium", d(-20), "Closed",
     d(-34), 0, TEAMS_MER, False, ""),
    ("TID", "Schedule final cut-over rehearsal", "Cut-over", "Omar Haddad", "High", d(4), "Delayed", d(-9), 1,
     f"projects/TID Tide Billing Migration/minutes/{d(-9)} Cut-over rehearsal review.docx — Actions", False, ""),
    ("TID", "Update rollback runbook after rehearsal 2", "Cut-over", "TBC", "Medium", None, "Open", d(-9), None,
     f"projects/TID Tide Billing Migration/minutes/{d(-9)} Cut-over rehearsal review.docx — Actions", False, ""),
]
# (project, type, description, workstream, owner, response, due, impact, likelihood, raised, source)
RAID = [
    ("FAL", "Risk", "Further access delay pushes go-live into Q1", "Data", "Alan Carter",
     f"Escalate to Northgate CIO on {d(3)}; weekly sponsor call; continue on masked data", d(3), "High", "High", d(-24),
     FAL_MIN + f"{d(-18)} Weekly delivery.docx — Risks, Issues, Assumptions & Dependencies"),
    ("FAL", "Issue", "Production data access not granted", "Data", "Rashid Al Suwaidi (Northgate)",
     "Access request re-submitted with security sign-off attached", d(-4), "High", "High", d(-23),
     FAL_MIN + f"{d(-18)} Weekly delivery.docx — Risks, Issues, Assumptions & Dependencies"),
    ("FAL", "Risk", "Domain 3 schema changes arrive late and cause rework", "Build", "Lena Fischer", "", None, "Medium",
     "Medium", d(-22), FAL_MIN + f"{d(-18)} Weekly delivery.docx — Risks, Issues, Assumptions & Dependencies"),
    ("ORX", "Risk", "Late UAT data slips sign-off", "Testing", "Sara Khan",
     "Use synthetic data for UAT week 1 if the client pack is late", d(4), "High", "Medium", d(-13), EMAIL_ORX),
    ("ORX", "Risk", "App store review takes longer than 5 days", "Release", "Sara Khan", "", None, "Medium", "Low", d(-20),
     f"projects/ORX Orbit Customer App/minutes/{d(-20)} Project board.docx — Risks, Issues, Assumptions & Dependencies"),
    ("MER", "Risk", "Agent adoption drops after pilot novelty", "Adoption", "Dev Patel", "", None, "Medium", "Medium",
     d(-18), TEAMS_MER),
    ("TID", "Risk", "Legacy billing freeze window too short", "Cut-over", "Omar Haddad",
     f"Agree an extended freeze window with Finance by {d(10)}", d(10), "High", "Low", d(-9),
     f"projects/TID Tide Billing Migration/minutes/{d(-9)} Cut-over rehearsal review.docx — Risks, Issues, Assumptions & Dependencies"),
    ("TID", "Assumption", "Finance accepts a 2-day reconciliation lag", "Cut-over", "Omar Haddad", "", None, "Low", "Low",
     d(-25), f"Email · From: Omar Haddad <omar.haddad@example.com> · Subject: [TID] Reconciliation · Sent: {d(-25)} 08:55"),
]
DECISIONS = [
    ("FAL", f"Go-live moves to {d(68)}", "Steering committee", d(-4), FAL_MIN + f"{d(-4)} Steering committee.docx — Decisions"),
    ("FAL", "Domain 3 delivered with masked data until access is granted", "Alan Carter", d(-11),
     f"Email · From: Alan Carter <alan.carter@example.com> · Subject: [FAL] Domain 3 approach · Sent: {d(-11)} 18:02"),
    ("ORX", f"UAT runs {d(8)} to {d(19)}", "Project board", d(-6),
     f"projects/ORX Orbit Customer App/minutes/{d(-6)} Project board.docx — Decisions"),
    ("MER", "Pilot extended to 40 agents", "Priya Nair", d(-18), TEAMS_MER),
    ("TID", f"Cut-over date fixed at {d(41)}", "Omar Haddad", d(-25),
     f"Email · From: Omar Haddad <omar.haddad@example.com> · Subject: [TID] Cut-over date confirmed · Sent: {d(-25)} 08:55"),
]
FILES = {  # project: [(subfolder, file name)]
    "FAL": [("minutes", f"{d(-4)} Steering committee.docx"), ("minutes", f"{d(-11)} Weekly delivery.docx"),
            ("transcripts", f"{d(-4)} Steering committee.vtt"), ("reports", f"{fri(1)} Weekly report.docx"),
            ("reports", f"{d(-10)} Client report.docx"), ("documents/Commercial", f"{d(-54)} SOW v2.md"),
            ("documents/Plans", f"{d(-38)} Delivery plan v3.md")],
    "ORX": [("minutes", f"{d(-6)} Project board.docx"), ("transcripts", f"{d(-6)} Project board.vtt"),
            ("reports", f"{fri(1)} Weekly report.docx"), ("reports", f"{d(-9)} Client report.docx"),
            ("documents/Testing", f"{d(-25)} UAT strategy.md")],
    "MER": [("minutes", f"{d(-5)} Pilot check-in.docx"), ("reports", f"{d(-3)} Client report.docx"),
            ("documents/Governance", f"{d(-138)} Pilot charter.md")],
    "TID": [("minutes", f"{d(-9)} Cut-over rehearsal review.docx"), ("reports", f"{fri(1)} Weekly report.docx")],
}


PENDING_WS = {("FAL", "Commercial"), ("ORX", "Testing"), ("FAL", "Cut-over"), ("FAL", "Data")}   # the pending proposals' workstreams


def run(*args):
    r = subprocess.run([sys.executable, str(ROOT / "system" / "scripts" / args[0]), *args[1:]], cwd=ROOT,
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"{args[0]} {' '.join(args[1:])} failed:\n{r.stdout}\n{r.stderr}")
    return r.stdout


def sample_docx(path, title):
    """Fill the minutes template into `path`, which must be in system/staging/drafts/ (BL-271)."""
    values = {"MEETING_TITLE": title, "STATUS_LINE": "Demo document (fictional).", "MEETING_WHEN": "",
              "ATTENDEES": "Fictional attendees", "SUMMARY": ["Fictional demo content for the dashboard."], "UPDATES": [],
              "DECISIONS": [], "RISKS_ISSUES": [], "ACTIONS": [], "OPEN_QUESTIONS": [], "SOURCE": "Demo data"}
    tmp = paths.STAGING / "demo-values.json"
    tmp.write_text(json.dumps(values))
    run("docx_tools.py", "fill", str(paths.MINUTES_TEMPLATE), str(tmp), str(path))
    tmp.unlink()


def new(table, n, **values):
    return {"n": n, "op": "new", "table": table, "values": values, "match": "strong", "flags": [], "decision": "approved"}


def demo_calendar():
    """A fictional week for the Inbox's Meetings section (BL-42 phase 2): Monday of this week to two days ahead, with
    event IDs and Teams flags, saved through sweep.py calendar as cx-sweep does. Returns the calendar it replaced."""
    before = paths.CALENDAR.read_text(encoding="utf-8") if paths.CALENDAR.exists() else None
    plan = [("FAL Steering committee", "10:00", "11:00", True, True), ("ORX design review", "14:00", "15:00", True, False),
            ("MER pilot check-in", "09:30", "10:00", True, False), ("Coffee with the TID sponsor", "12:30", "13:15", False, False),
            ("Portfolio steering", "16:00", "17:00", True, True), ("Doctor's appointment", "08:00", "09:00", False, False)]
    days, k = {}, 0
    for offset in range(-T.weekday(), 3):
        day = d(offset)
        for j in (0, 1):
            title, start, end, teams, mine = plan[(offset + j * 3) % len(plan)]
            k += 1
            days.setdefault(day, []).append({"id": f"demo-event-{k:03d}", "start": start, "end": end, "title": title,
                                             "where": "Microsoft Teams Meeting" if teams else "Room 4.12",
                                             "teams": teams, "private": title.startswith("Doctor"),
                                             "organiser": True if mine else "Jane Doe"})
    spec = paths.STAGING / "demo-calendar-spec.json"
    spec.write_text(json.dumps({"days": days}), encoding="utf-8")
    run("sweep.py", "calendar", str(spec))
    spec.unlink()
    return before


def project_files(p, folder, file_ops, built):
    """A project's demo files. BL-292: a Word file is built in system/staging/drafts/ (BL-271) and filed by a copy
    operation of the demo's apply (added to `file_ops`, the draft to `built`); the others are written directly."""
    for sub, name in FILES.get(p["code"], []):
        f = folder / sub / name
        f.parent.mkdir(parents=True, exist_ok=True)
        if f.suffix == ".docx":
            draft = paths.DRAFTS / f"demo-{len(built):03d}.docx"
            draft.parent.mkdir(parents=True, exist_ok=True)
            sample_docx(draft, f"{p['code']} {Path(name).stem[11:]} (demo)")
            built.append(draft)
            file_ops.append({"op": "copy", "from": paths.rel(draft), "to": paths.rel(f)})
        else:
            f.write_text("WEBVTT\n\n00:00.000 --> 00:02.000\n<v Demo>Fictional transcript.</v>\n"
                         if f.suffix == ".vtt" else f"# {name}\n\nFictional demo document.\n", encoding="utf-8")


def load():
    if STATE.exists():
        sys.exit("The demo is already loaded. Run: python3 dev/tools/demo_data.py purge")
    if not paths.DB.exists():
        run("tracker.py", "init")
    created = []
    items, n = [], 0
    file_ops, built = [], []                       # BL-292: Word files built in drafts, filed by the apply
    ms_ids = {}
    for p in PROJECTS:
        folder = paths.PROJECTS / f"{p['code']} {p['name']}"
        if folder.exists():
            sys.exit(f"{paths.rel(folder)} already exists; not loading the demo over it.")
    for p in PROJECTS:
        folder = paths.PROJECTS / f"{p['code']} {p['name']}"
        for sub in paths.PROJECT_SUBFOLDERS:
            (folder / sub).mkdir(parents=True, exist_ok=True)
        created.append(paths.rel(folder))
        (folder / "CLAUDE.md").write_text(
            f"# {p['code']} — {p['name']} (demo, fictional)\n\n## Brief\n\n- **Client / partner:** {p['client']}\n"
            f"- **Client report rhythm:** {p['rhythm']}\n\n## Current state\n\n{p['current']}\n", encoding="utf-8")
        project_files(p, folder, file_ops, built)
        n += 1
        items.append(new("projects", n, code=p["code"], name=p["name"], sponsor=p["sponsor"], phase=p["phase"],
                         health=p["health"], health_reason=p["reason"]))
        for i, (name, base, fc, status) in enumerate(p["ms"]):
            n += 1
            ms_ids[(p["code"], i)] = f"{p['code']}-M-{i + 1:03d}"
            items.append(new("milestones", n, project=p["code"], name=name, baseline_date=base, forecast_date=fc,
                             status=status, sort_order=i, source="Demo data (fictional)"))
        for w, h in enumerate(reversed(p["trail"])):
            n += 1
            items.append(new("updates", n, week_ending=fri(w), project=p["code"], health=h,
                             summary=f"Demo weekly update ({h.lower()})"))
    # Workstreams belong to their project (BL-58): every one the demo uses exists first, in the same apply, so
    # purge (tracker.py undo) removes them with everything else. PENDING_WS: those only the pending proposals use.
    used = {(a[0], a[2]) for a in ACTIONS if a[2]} | {(r[0], r[3]) for r in RAID if r[3]} | PENDING_WS
    for code, ws in sorted(used):
        n += 1
        items.append(new("workstreams", n, project=code, name=ws, source="Demo data (fictional)"))
    for (code, t, ws, o, pr, due, st, raised, mi, src, client, upd) in ACTIONS:
        n += 1
        v = dict(project=code, description=t, workstream=ws, owner=o, priority=pr, status=st, raised=raised, source=src)
        if due:
            v["due_date"] = due
        if mi is not None:
            v["milestone"] = ms_ids[(code, mi)]
        if upd:
            v["latest_update"] = upd
        if client:
            v.update(client_visible=1, client_message="What it is: An item the client is waiting on.\n"
                                                      "What it means for you: It affects the next milestone.\n"
                                                      "What is being done: We are chasing it weekly.")
        items.append(new("actions", n, **v))
    for (code, typ, t, ws, o, resp, due, imp, lik, raised, src) in RAID:
        n += 1
        v = dict(project=code, type=typ, description=t, workstream=ws, owner=o, impact=imp, likelihood=lik,
                 raised=raised, source=src)
        if resp:
            v["response_action"] = resp
        if due:
            v["due_date"] = due
        items.append(new("raid", n, **v))
    for (code, t, by, when, src) in DECISIONS:
        n += 1
        items.append(new("decisions", n, project=code, decision=t, made_by=by, date=when, source=src))
    PROPOSAL.write_text(json.dumps({"created": f"{T}T07:00:00", "source_run": "cx-edit", "files": [], "items": items,
                                    "file_changes": {"title": "Demo Word files (fictional)", "project": None,
                                                     "file_ops": file_ops, "file_changes_decision": "approved"}},
                                   indent=1), encoding="utf-8")
    try:
        out = run("tracker.py", "apply", str(PROPOSAL))
    finally:
        for f in built:                            # filed (or the apply failed): the drafts have done their job
            f.unlink(missing_ok=True)
    applied = paths.APPLIED / PROPOSAL.name
    apply_id = int(out.split()[1].rstrip(":"))

    # Pending proposals for Review: a sweep result and a set of draft minutes
    draft = paths.DRAFTS / f"{d(-1)} FAL Steering committee.docx"
    draft.parent.mkdir(parents=True, exist_ok=True)
    sample_docx(draft, "FAL Steering committee (demo draft)")
    fal_src = FAL_MIN + f"{d(-1)} Steering committee.docx"
    pending = [
        ("proposed-0000-00-01-demo.json", {"created": f"{T}T07:05:00", "source_run": "cx-sweep", "files": [], "items": [
            {"n": 1, "op": "new", "table": "actions", "match": "possible", "flags": [], "decision": "pending",
             "values": {"project": "FAL", "description": "Send revised data-sharing agreement", "workstream": "Commercial",
                        "owner": "Rashid Al Suwaidi (Northgate)", "priority": "High", "due_date": d(6), "raised": d(-2),
                        "source": f"Email · From: Northgate Legal <legal@northgate.example> · Subject: Data sharing "
                                  f"agreement — revised draft · Sent: {d(-2)} 14:37"}},
            {"n": 2, "op": "update", "table": "actions", "id": "ORX-A-002", "changes": {"status": "Closed"},
             "match": "strong", "flags": [], "decision": "pending"},
            {"n": 3, "op": "new", "table": "actions", "match": "strong", "flags": [], "decision": "pending",
             "values": {"project": "ORX", "description": "Confirm tester access to staging", "workstream": "Testing",
                        "owner": "Sara Khan", "due_date": d(5), "raised": d(-2),
                        "source": f"Teams · Channel: ORX UAT · From: Sara Khan · Sent: {d(-2)} 10:05"}}]}),
        ("proposed-0000-00-02-demo.json", {"created": f"{T}T08:10:00", "source_run": "cx-minutes",
                                           "files": [paths.rel(draft)], "items": [
            {"n": 1, "op": "new", "table": "raid", "match": "strong", "flags": [], "decision": "pending",
             "values": {"project": "FAL", "type": "Risk", "description": "Northgate December change freeze narrows "
                        "the cut-over window", "workstream": "Cut-over", "owner": "Alan Carter", "impact": "High",
                        "likelihood": "Medium", "raised": d(-1), "source": fal_src + " — Risks, Issues, Assumptions & Dependencies"}},
            {"n": 2, "op": "new", "table": "decisions", "match": "strong", "flags": [], "decision": "pending",
             "values": {"project": "FAL", "decision": "Weekly sponsor call until go-live", "made_by": "Steering committee",
                        "date": d(-1), "source": fal_src + " — Decisions"}},
            {"n": 3, "op": "new", "table": "actions", "match": "strong", "flags": ["no-owner", "no-due-date"],
             "decision": "pending", "values": {"project": "FAL", "description": "Share masked domain-3 extract with QA",
                                               "workstream": "Data", "owner": "TBC", "raised": d(-1),
                                               "source": fal_src + " — Actions"}}],
            "meeting": {"key": "demo:fal-steering", "title": "FAL Steering committee", "date": d(-1), "projects": ["FAL"],
                        "draft": paths.rel(draft), "transcript": None, "minutes_decision": "pending", "file_ops": []}}),
    ]
    for name, data in pending:
        (paths.STAGING / name).write_text(json.dumps(data, indent=1), encoding="utf-8")
    (paths.INBOX / "Recording - ORX design review (demo).vtt").write_text("WEBVTT\n", encoding="utf-8")
    calendar_was = demo_calendar()
    STATE.write_text(json.dumps({"apply_id": apply_id, "folders": created, "calendar_was": calendar_was,
                                 "files": [paths.rel(draft), paths.rel(applied)] + [f"system/staging/{n}" for n, _ in pending]
                                 + ["inbox/Recording - ORX design review (demo).vtt"]}, indent=1), encoding="utf-8")
    print(f"Demo loaded (apply {apply_id}): 4 projects, {len(ACTIONS)} actions, {len(RAID)} RAID, "
          f"{len(DECISIONS)} decisions; 6 proposed items and 1 draft waiting in Review.")
    print(run("build_dashboard.py").strip())
    print("Open dashboard.html in Chrome. Remove it all with: python3 dev/tools/demo_data.py purge")


def purge():
    if not STATE.exists():
        sys.exit("No demo is loaded.")
    state = json.loads(STATE.read_text(encoding="utf-8"))
    out = run("tracker.py", "read", "applies")
    latest = max((a for a in json.loads(out) if not a["undone_at"]), key=lambda a: a["apply_id"], default=None)
    if not latest or latest["apply_id"] != state["apply_id"]:
        sys.exit("Something was applied after the demo was loaded, so it can't be undone cleanly. Undo the later "
                 "apply first (tracker.py undo), then purge.")
    print(run("tracker.py", "undo").strip())
    for f in state["files"]:
        (ROOT / f).unlink(missing_ok=True)
    (paths.STAGING / PROPOSAL.name).unlink(missing_ok=True)   # undo moved it back from applied/
    for folder in state["folders"]:
        shutil.rmtree(ROOT / folder, ignore_errors=True)
    if "calendar_was" in state:                                  # put back the calendar the demo replaced
        if state["calendar_was"] is None:
            paths.CALENDAR.unlink(missing_ok=True)
        else:
            paths.CALENDAR.write_text(state["calendar_was"], encoding="utf-8")
    STATE.unlink()
    print(run("build_dashboard.py").strip())
    print("Demo purged.")


if __name__ == "__main__":
    if not (ROOT / ".creaite-dev").exists():
        sys.exit("demo_data.py runs only in the development repo.")
    {"load": load, "purge": purge}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: print(__doc__))()
