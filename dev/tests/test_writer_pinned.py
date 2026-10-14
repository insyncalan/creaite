"""BL-229 step 1: pin the single writer before it is split. A corpus of proposals runs through `tracker.py apply`
(and `validate`, and `undo`) as it stands today; every data table, the full change_log in order, the applies, the
proposals as apply leaves them, and apply's exit code and output are snapshotted and compared with the saved
expectation in dev/tests/pinned/. The split must leave every one of them byte-for-byte the same.

Run: python3 dev/tests/test_writer_pinned.py                     (quick tier: no Chrome)
Record (only before the split, or for a reviewed, deliberate change):  CREAITE_PIN_RECORD=1 python3 dev/tests/test_writer_pinned.py

What varies from run to run is normalised: every timestamp becomes <TS> (which events land in the same millisecond varies
between runs), today's date becomes <TODAY>, and the vault path becomes <VAULT>. Apply IDs are sequential in a fresh vault.
Fixture dates are far from today (2026 and 2030), so rules that compare with today give the same answer every day.
"""
import json
import os
import re
import sqlite3
import sys
import unittest
from contextlib import closing
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import ABC, Vault, docx_text, make_draft  # noqa: E402

PINNED = Path(__file__).resolve().parent / "pinned"
# The approval stamp an approved draft gets ("Approved by Alan on 12 October 2026") is in the filed Word file, so in its text and
# its hash: the scripts' clock is fixed to the day the expectations were recorded. Everything else apply dates is today's.
STAMP_DAY = "2026-10-12"
os.environ["CREAITE_NOW"] = f"{STAMP_DAY} 09:00"
RECORD = os.environ.get("CREAITE_PIN_RECORD") == "1"
OLD_SQL = PINNED / "old-code.sql"     # a database the code before the split wrote, as SQL text (git ignores *.db files)
SRC = f"{ABC}/minutes/2026-10-01 Steering.docx — Actions"
TABLES_SKIPPED = {"vault_search", "sqlite_sequence"}
TS = re.compile(r"\d{4}-\d\d-\d\d[ T]\d\d:\d\d:\d\d(?:\.\d+)?")


def fresh_vault():
    """A test vault with its database made (`tracker.py init`: the register's projects)."""
    v = Vault()
    v.run("init")
    return v


# ---------- proposals ----------
def new(n, table, **values):
    return {"n": n, "op": "new", "table": table, "values": values, "match": "strong", "flags": [], "decision": "approved"}


def upd(n, table, id_, changes, **extra):
    return {"n": n, "op": "update", "table": table, "id": id_, "changes": changes, "match": "strong", "flags": [],
            "decision": "approved", **extra}


def cancel(n, table, id_):
    return {"n": n, "op": "cancel", "table": table, "id": id_, "match": "strong", "flags": [], "decision": "approved"}


def base_items():
    """One new row in every table a proposal can write, all for ABC."""
    return [
        new(1, "actions", project="ABC", description="Send revised SOW to client", owner="Alan Carter", raised="2026-10-01",
            due_date="2030-06-14", priority="High", source=SRC),
        new(2, "raid", project="ABC", type="Risk", description="Vendor may slip", owner="Sara Khan", impact="High",
            likelihood="Medium", raised="2026-10-01", source=SRC),
        new(3, "raid", project="ABC", type="Issue", description="Test data is late", owner="Omar Haddad", impact="Medium",
            raised="2026-10-01", source=SRC),
        new(4, "decisions", project="ABC", decision="Go with vendor A", date="2026-10-01", status="Made", source=SRC),
        new(5, "decisions", project="ABC", decision="Choose the pilot site", status="Pending", needed_by="2030-06-14",
            source=SRC),
        new(6, "promises", project="ABC", promised_by="Alan Carter", promised_to="Sara Khan", description="Share the plan",
            due_date="2030-06-14", raised="2026-10-01", source=SRC),
        new(7, "milestones", project="ABC", name="Go-live", baseline_date="2030-06-14", forecast_date="2030-06-14",
            source=SRC),
        new(8, "workstreams", project="ABC", name="Data", created="2026-10-01", source="Alan (cx-edit)"),
    ]


# Each case is a list of steps: (label, items). A step's proposal is written just before it is applied, so nothing
# else is pending while it runs. IDs: one number sequence per project across actions, RAID, decisions and promises.
def case_new_each_table():
    return [("new", base_items())]


def case_updates():
    return [("new", base_items()),
            ("update", [
                upd(1, "actions", "ABC-A-001", {"owner": "Sara Khan", "status": "Closed"}),             # closed is set
                upd(2, "raid", "ABC-002", {"likelihood": "High"}),                                     # priority re-derived
                upd(3, "decisions", "ABC-D-005", {"status": "Made", "date": "2026-10-02"}),            # Pending -> Made
                upd(4, "promises", "ABC-P-006", {"status": "Done"}),
                upd(5, "milestones", "ABC-M-001", {"forecast_date": "2030-06-21", "percent_complete": 40}),
                upd(6, "projects", "ABC", {"health": "At risk", "health_reason": "Vendor slip"}),
            ]),
            ("reopen", [upd(1, "actions", "ABC-A-001", {"status": "Open"})])]                         # closed cleared


def case_cancel():
    return [("new", base_items()),
            ("cancel", [cancel(1, "actions", "ABC-A-001"), cancel(2, "raid", "ABC-003"),
                        cancel(3, "workstreams", "ABC-W-001")])]


def case_conflict():
    return [("new", base_items()),
            ("conflict", [upd(1, "actions", "ABC-A-001", {"owner": "Omar Haddad"}, based_on="2026-01-01 00:00:00.000")])]


def case_health_needs_a_reason():
    return [("no reason", [upd(1, "projects", "ABC", {"health": "Off track"})])]


def case_made_decision_back_to_pending():
    return [("new", base_items()),
            ("pending", [upd(1, "decisions", "ABC-D-004", {"status": "Pending"})])]


def case_labels():
    a = new(1, "actions", project="ABC", description="Labelled", owner="Alan Carter", raised="2026-10-01", source=SRC,
            labels=["Sensitive"], label_reason="client names", label_suggested=0)
    return [("labelled", [a]),
            ("relabel", [upd(1, "actions", "ABC-A-001", {"labels": []}, label_reason="cleared")])]


def case_workstream_rename():
    ws = base_items()[7]
    item = base_items()[0]
    item["values"]["workstream"] = "Data"
    return [("workstream", [ws]),
            ("item in it", [item]),
            ("rename", [upd(1, "workstreams", "ABC-W-001", {"name": "Data and migration"})])]


def case_rebaseline():
    return [("new", base_items()),
            ("rebaseline", [upd(1, "milestones", "ABC-M-001", {"baseline_date": "2030-07-12"},
                                rebaseline={"agreed_with": ["Sara Khan"], "reason": "Vendor slip", "source": SRC,
                                            "date": "2026-10-03"})])]


def case_rebaseline_without_its_block():
    return [("new", base_items()),
            ("bare", [upd(1, "milestones", "ABC-M-001", {"baseline_date": "2030-07-12"})])]


def case_batch_with_one_invalid_item():
    bad = new(2, "raid", project="ABC", type="Wish", description="Not a RAID type", raised="2026-10-01", source=SRC)
    return [("batch", [base_items()[0], bad])]


def case_recode():
    return [("new", base_items()),
            ("recode", [{"n": 1, "op": "recode", "table": "projects", "id": "ABC", "changes": {"code": "XYZ"},
                         "match": "strong", "flags": [], "decision": "approved"}])]


def rejected(n, description=None, **extra):
    """A rejected new action; `extra` goes on the item (reject_reason, duplicate_of), not in its values."""
    item = new(n, "actions", project="ABC", description=description or f"Not wanted {n}", owner="Alan Carter",
               raised="2026-10-01", source=SRC)
    return {**item, "decision": "rejected", **extra}


def case_rejected_pending_and_a_repeat():
    keep = base_items()[0]
    later = {**new(3, "actions", project="ABC", description="Decide later", owner="Alan Carter", raised="2026-10-01",
                   source=SRC), "decision": "pending"}
    return [("decide", [keep, rejected(2, reject_reason="Not ours"), later]),
            ("again", [rejected(1, "Not wanted 2", reject_reason="Not ours"),       # the same fingerprint: not stored twice
                       rejected(2, "Copy of the SOW action", duplicate_of="ABC-A-001")])]   # a duplicate, no reason given


DRAFT = "system/staging/drafts/2026-10-01 ABC Steering committee.docx"
TRANSCRIPT = "inbox/Recording 2026-10-01.vtt"
MINUTES = f"{ABC}/minutes/2026-10-01 ABC Steering committee.docx"
FILED_TRANSCRIPT = f"{ABC}/transcripts/2026-10-01 ABC Steering committee.vtt"


def meeting_files(v):
    make_draft(v.root / DRAFT)
    (v.root / TRANSCRIPT).write_text("WEBVTT\n\n00:00.000 --> 00:02.000\n<v Alan>Welcome</v>\n", encoding="utf-8")


def meeting(decision):
    return {"key": "fp:2026-10-01|abc steering committee|abc123", "title": "ABC Steering committee", "date": "2026-10-01",
            "projects": ["ABC"], "draft": DRAFT, "transcript": TRANSCRIPT, "minutes_decision": decision,
            "source_map": {MINUTES: FILED_TRANSCRIPT},
            "file_ops": [{"op": "copy", "from": "draft", "to": MINUTES},
                         {"op": "copy", "from": "transcript", "to": FILED_TRANSCRIPT},
                         {"op": "remove", "path": TRANSCRIPT}, {"op": "remove", "path": DRAFT}]}


def minutes_items():
    item = base_items()[0]
    item["values"]["source"] = f"{MINUTES} — Actions"
    return [item, rejected(2)]


def case_meeting_filed():
    return [("meeting", minutes_items(), {"setup": meeting_files, "source_run": "cx-minutes", "meeting": meeting("approved")})]


def case_meeting_minutes_rejected():
    """No minutes filed: the items cite the filed transcript instead (source_map)."""
    return [("meeting", minutes_items(), {"setup": meeting_files, "source_run": "cx-minutes", "meeting": meeting("rejected")})]


def tamper(sql):
    """Change the database behind the writer's back (the only way a row changes outside an apply)."""
    def run(v):
        with closing(sqlite3.connect(v.root / "system" / "tracker.db")) as con:
            con.execute(sql)
            con.commit()
    return run


def lose_applied_proposals(v):
    for p in (v.root / "system" / "staging" / "applied").glob("proposed-*.json"):
        p.unlink()


def case_undo_skips_a_row_changed_since():
    return [("new", base_items(), {"after": tamper("UPDATE actions SET owner = 'Someone Else' WHERE id = 'ABC-A-001'")})]


def case_undo_with_its_proposal_gone():
    return [("new", base_items(), {"after": lose_applied_proposals})]


CASES = {name[len("case_"):]: fn for name, fn in globals().items() if name.startswith("case_")}


# ---------- snapshots ----------
class Norm:
    """Replaces what varies between runs with stable tokens, the same token for the same value within one case."""

    def __init__(self, root):
        self.root = str(root)
        self.today = date.today().isoformat()

    def text(self, s):
        if not isinstance(s, str):
            return s
        s = s.replace(self.root, "<VAULT>").replace(str(Path(self.root).resolve()), "<VAULT>")
        s = TS.sub("<TS>", s)            # which events share a millisecond varies from run to run: not pinned
        return s.replace(self.today, "<TODAY>")

    def value(self, v):
        if isinstance(v, dict):
            return {k: self.value(x) for k, x in v.items()}
        if isinstance(v, list):
            return [self.value(x) for x in v]
        return self.text(v)


def snapshot(v, norm):
    """Every table (rowid order for change_log, key order for the rest), and the proposals as they are now."""
    out = {}
    with closing(sqlite3.connect(v.root / "system" / "tracker.db")) as con:
        con.row_factory = sqlite3.Row
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        for t in tables:
            if t in TABLES_SKIPPED or t.startswith("vault_search"):
                continue
            order = "rowid" if t in ("change_log", "applies") else "1"
            out[t] = [norm.value(dict(r)) for r in con.execute(f"SELECT * FROM {t} ORDER BY {order}")]
    out["files"] = vault_files(v)
    processed = v.root / "system" / "processed.txt"
    out["processed"] = norm.text(processed.read_text(encoding="utf-8")) if processed.exists() else None
    out["documents"] = {rel: norm.text(" ".join(docx_text(v.root / rel).split()))
                        for rel in out["files"] if rel.endswith(".docx")}
    staging = v.root / "system" / "staging"
    out["proposals"] = {p.relative_to(staging).as_posix(): norm.value(json.loads(p.read_text(encoding="utf-8")))
                        for p in sorted(staging.rglob("proposed-*.json"))}
    return out


NOT_PINNED = ("system/backups", "system/scripts", "system/templates", "system/search", "system/logs", "system/history",
              "system/staging/applied", "system/tracker.db", "dashboard.html", "tracker-view.xlsx", ".claude", "system/config")


def vault_files(v):
    """Every file the apply could have filed, moved or removed (not the engine, the views or the backups)."""
    return sorted(p.relative_to(v.root).as_posix() for p in v.root.rglob("*")
                  if p.is_file() and "__pycache__" not in p.parts
                  and not p.relative_to(v.root).as_posix().startswith(NOT_PINNED)
                  and not p.name.startswith("proposed-"))


def run_case(name):
    """Apply each step of the case; snapshot after each, then undo every apply in turn, snapshotting after each."""
    v = fresh_vault()
    try:
        norm = Norm(v.root)
        result = []
        for i, (label, items, *opts) in enumerate(CASES[name]()):
            extra = dict(opts[0]) if opts else {}
            setup, after = extra.pop("setup", None), extra.pop("after", None)
            if setup:
                setup(v)
            proposal = v.propose(f"step{i + 1}", items, **extra)
            r = v.run("apply", str(proposal), ok=False)
            if after:
                after(v)
            result.append({"step": label, "exit": r.returncode, "stdout": norm.text(r.stdout), "stderr": norm.text(r.stderr),
                           "after": snapshot(v, norm)})
        result += undo_all(v, norm)
        return result
    finally:
        v.cleanup()


def undo_all(v, norm, limit=10):
    out = []
    for _ in range(limit):
        r = v.run("undo", ok=False)
        out.append({"step": "undo", "exit": r.returncode, "stdout": norm.text(r.stdout), "stderr": norm.text(r.stderr),
                    "after": snapshot(v, norm)})
        if "Nothing to undo" in r.stdout or r.returncode:
            break
    return out


def validate_writes_nothing():
    """A dry run (`validate`, apply_id None) of a full corpus: its output, and the database before and after."""
    v = fresh_vault()
    try:
        norm = Norm(v.root)
        p = v.propose("dry", base_items())
        before = snapshot(v, norm)
        r = v.run("validate", str(p), ok=False)
        return {"exit": r.returncode, "stdout": norm.text(r.stdout), "before": before, "after": snapshot(v, norm)}
    finally:
        v.cleanup()


# ---------- the test ----------
def expected(name, actual):
    f = PINNED / f"{name}.json"
    if RECORD:
        PINNED.mkdir(exist_ok=True)
        f.write_text(json.dumps(actual, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return json.loads(f.read_text(encoding="utf-8"))


def roundtrip(x):
    return json.loads(json.dumps(x, sort_keys=True, ensure_ascii=False))


class Pinned(unittest.TestCase):
    maxDiff = None

    def check(self, name, actual):
        self.assertEqual(roundtrip(actual), expected(name, actual), f"{name}: the writer's behaviour changed")

    def test_validate_is_a_dry_run(self):
        got = validate_writes_nothing()
        self.assertEqual(got["before"], got["after"])
        self.check("validate", got)

    def test_undo_of_a_database_written_by_the_old_code(self):
        """The saved database was written by the code before the split: undoing it applies by apply must still work."""
        if RECORD:                       # written once, by today's code, in a vault of its own
            maker = fresh_vault()
            try:
                for i, (_, items) in enumerate(case_updates()):
                    maker.run("apply", str(maker.propose(f"step{i + 1}", items)), ok=False)
                with closing(sqlite3.connect(maker.root / "system" / "tracker.db")) as con:
                    OLD_SQL.write_text("\n".join(con.iterdump()) + "\n", encoding="utf-8")
            finally:
                maker.cleanup()
        v = fresh_vault()
        try:
            db = v.root / "system" / "tracker.db"
            db.unlink()
            sql = OLD_SQL.read_text(encoding="utf-8")
            # the dump holds the day it was recorded wherever the old code wrote "today" (raised, updated_at, the applies'
            # times); move that day to today, so the normaliser reads it as <TODAY> on any day, as it did on the day it was made
            written = re.search(r"INSERT INTO \"applies\" VALUES\(1,'(\d{4}-\d\d-\d\d) ", sql).group(1)
            sql = sql.replace(written, date.today().isoformat())
            with closing(sqlite3.connect(db)) as con:
                con.executescript(sql)
            norm = Norm(v.root)
            self.check("old-code-undo", [{"start": snapshot(v, norm)}] + undo_all(v, norm))
        finally:
            v.cleanup()


def _make(name):
    def test(self):
        self.check(name, run_case(name))
    test.__doc__ = f"Pinned: {name.replace('_', ' ')}."
    return test


for _name in CASES:
    setattr(Pinned, f"test_{_name}", _make(_name))


if __name__ == "__main__":
    unittest.main()
