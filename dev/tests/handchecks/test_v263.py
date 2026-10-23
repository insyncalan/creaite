"""creaite 2.6.3's hand checks, automated against a vault made from the release zip (the fictional demo portfolio: Falcon Data
Platform and the rest). One check per item, `test_cNN_...`, its docstring quoting what the item must do. There is no Product Manager's
sheet for 2.6.3 yet, so the numbers are the items in order and the PM can number them in. F1 and #250 were in the 2.6.2 line's hand
checks (test_v262.py) until Alan moved them to 2.6.3 (23-10-2026); their checks are these, unchanged but for the number:

   1 F1    (#312, #314)  nullable columns: migrate keeps change_log rowids with a gap, the item_events links, a second migrate is a no-op
   2 #250  transcripts   a confidential meeting's transcript is never fetched, however the two events spell the meeting's URL, in either
                         order of the two event reads (and the transcript read after both)
   3 #250  read order    EXPECTED FAILURE (a known open defect, Team Cap's MEDIUM on #250): the transcript is read BEFORE the confidential
                         event is read (ev-2, then the transcript, then ev-1): nothing may be fetched under ev-2's name

How a check is wired (every class has a vault of its own, made from the zip, so nothing a check changes reaches another):
  F1263, Fetch263        a vault and no server: the engine's own commands, or its code run in the vault

F1 is the guarded 2.6.2 chain's F1 (dev/proposals/GUARDED-2.6.2.chain); #250's engine half (transcripts.py) is not guarded and is on the
line, its live-server half is in the chain. A check that needs a guarded change this tree does not have is an EXPECTED FAILURE (the
convention test_v261_intake_307_identity.py uses): it still runs, is red for the right reason, and turns into an unexpected success
(flagged) the moment the change is in. Check 3 is an expected failure whatever the tree has, until the read-order defect is fixed;
when it is, delete its decorator.

Run them (from the repository root; a release zip is built from this checkout first):
  python3 dev/tests/handchecks/test_v263.py                         all, with the committed tree (or --dirty: uncommitted engine files)
  python3 dev/tests/handchecks/test_v263.py F1263.test_c01_...      one check
  python3 dev/tools/handcheck.py v2.6.3 [--dirty] [--only 1,2]      the runner (Results table, run folder)
Standalone, the module builds the zip itself, with the uncommitted engine files when the tree has any (the chain applied but not
committed), and removes its run folder at the end (CREAITE_HC_KEEP=1 keeps it). With CREAITE_HC_BASE, CREAITE_HC_DIR and CREAITE_HC_ZIP
set (what handcheck.py sets) it uses those. Safe at -j 3: every vault and folder is new.

Never Microsoft 365, never a real model: the reads a sweep makes are stood in for with fixture results. Fictional data only.
"""
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import unittest
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))                  # dev/tests, for the helpers this borrows
import hcbase  # noqa: E402
from hcbase import NOTES, HandcheckCase, db_rows, only  # noqa: E402,F401  (NOTES: read by handcheck.py)

NOTES.clear()

REPO = HERE.parents[2]
SCRIPTS = REPO / "system/scripts"

KIND = {n: "scriptable" for n in range(1, 4)}
LIVE_ONLY = {}


def _src(name):
    p = SCRIPTS / name
    return p.read_text(encoding="utf-8") if p.is_file() else ""


# What this tree has of the guarded 2.6.2 chain (read from the repository's own files, which the zip is built from)
HAS = {"f1": "engine_version" in _src("schema.sql") and "def stamp_apply" in _src("tracker.py")}
CHAIN = {"f1": "F1 (schema.sql, tracker.py)"}


def needs(key):
    """A check that needs a change of the guarded 2.6.2 chain: an expected failure while this tree lacks it, a plain check once it has it."""
    def wrap(fn):
        if HAS[key] or os.environ.get("CREAITE_HC_SHOW_XFAIL"):          # CREAITE_HC_SHOW_XFAIL=1: run it as a plain check to see why it fails
            return fn
        fn.__doc__ = (fn.__doc__ or "") + f" [expected failure: {CHAIN[key]} is not in this tree]"
        return unittest.expectedFailure(fn)
    return wrap


class Engine263(HandcheckCase):
    """Checks that need the vault but not a server or a browser. Own vault."""
    own_vault = True

    @classmethod
    def start_server(cls):
        import handcheck
        s = hcbase.session() or handcheck.Session(os.environ["CREAITE_HC_DIR"])
        if not s.zip and os.environ.get("CREAITE_HC_ZIP"):
            s.zip = Path(os.environ["CREAITE_HC_ZIP"])
        cls._hc, cls.v, cls.proc, cls.base = s, None, None, None
        cls.vault = s.make_vault(f"vault-{cls.__name__}")
        cls.now = os.environ.get("CREAITE_HC_NOW") or s.now

    def setUp(self):                                                 # no browser
        n = self.check_number()
        if only() and n not in only():
            self.skipTest("not in --only")

    # ── the engine ──

    def run_py(self, code, env=None):
        """Python in the vault (its system/scripts on the path, the clock pinned), isolated; (exit code, output)."""
        r = subprocess.run([sys.executable, "-I", "-c", "import sys, json\nsys.path.insert(0, 'system/scripts')\n" + code], cwd=self.vault,
                           capture_output=True, text=True, env={**os.environ, "CREAITE_NOW": self.now or "", "TZ": "UTC", **(env or {})})
        return r.returncode, r.stdout + r.stderr


    def py(self, code, env=None):
        """The JSON the code prints (its last line)."""
        rc, out = self.run_py(code, env)
        self.assertEqual(rc, 0, out[-600:])
        return json.loads(out.strip().splitlines()[-1])


    def sql(self, query, *args):
        return db_rows(self.vault, query, *args)


    def count(self, table):
        return self.sql(f"SELECT count(*) AS n FROM {table}")[0]["n"]


    def staging(self, name=""):
        return self.vault / "system/staging" / name


    def pending(self):
        return set(hcbase.pending_proposals(self.vault))


    def stage_edit(self, items, name="hc263"):
        """Items as cx-edit stages them (propose.py stage); the new pending proposal's file name."""
        before = self.pending()
        f = self.staging(f"drafts/{name}.json")
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({"source_run": "cx-edit", "items": items}), encoding="utf-8")
        code, out = self.run_in_vault("propose.py", "stage", f"system/staging/drafts/{name}.json")
        self.assertEqual(code, 0, out[-400:])
        new = sorted(self.pending() - before)
        self.assertEqual(len(new), 1, f"{new} {out[-300:]}")
        return new[0]


    def new_action(self, text, owner="Sara Khan", days=40):
        day = date.fromisoformat((self.now or str(date.today()))[:10])
        return {"op": "new", "table": "actions", "values": {"project": "FAL", "description": text, "owner": owner, "raised": day.isoformat(),
                                                            "due_date": (day + timedelta(days=days)).isoformat(), "source": "hand check 263"}}

    # ── the live server ──


    def set_setting(self, *path_and_value):
        """Set a nested setting in the vault's settings.json (the server reads it at each call); returns what it was."""
        *path, value = path_and_value
        f = self.vault / "system/config/settings.json"
        cfg = json.loads(f.read_text(encoding="utf-8"))
        node = cfg
        for k in path[:-1]:
            node = node.setdefault(k, {})
        was = node.get(path[-1], "__absent__")
        node[path[-1]] = value
        f.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
        return was

    # ── minutes held in Review (Discard's input) ──



# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# 1  F1: nullable columns
# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

# The tables as the engine before F1 made them (the 2.6.1 CREATE statements), so the migration has something to migrate
OLD_APPLIES = """CREATE TABLE applies (
  apply_id    INTEGER PRIMARY KEY AUTOINCREMENT,
  at          TEXT NOT NULL DEFAULT (datetime('now')),
  proposals   TEXT NOT NULL,
  file_ops    TEXT,
  undone_at   TEXT
)"""
OLD_CHANGE_LOG = """CREATE TABLE change_log (
  at         TEXT NOT NULL DEFAULT (datetime('now')),
  apply_id   INTEGER REFERENCES applies(apply_id),
  tbl        TEXT NOT NULL,
  item_id    TEXT NOT NULL,
  field      TEXT NOT NULL,
  old_value  TEXT,
  new_value  TEXT,
  op         TEXT NOT NULL DEFAULT 'update' CHECK (op IN ('insert','update','undo')),
  via        TEXT NOT NULL
)"""
OLD_SHAPE = (("applies", OLD_APPLIES, ("apply_id", "at", "proposals", "file_ops", "undone_at")),
             ("change_log", OLD_CHANGE_LOG, ("at", "apply_id", "tbl", "item_id", "field", "old_value", "new_value", "op", "via")))
NEW_APPLY_COLS = ("author", "origin", "sequence", "engine_version")
NEW_LOG_COLS = ("author", "origin", "sequence", "base_version", "engine_version")
LINKS = ("SELECT e.event_id, e.change, c.item_id, c.field, c.old_value, c.new_value, c.apply_id FROM item_events e "
         "LEFT JOIN change_log c ON c.rowid = e.change ORDER BY e.event_id")


class F1263(Engine263):
    """Check 1. A vault and no server: the database is taken back to the 2.6.1 shape, then migrated by the engine in the vault."""

    @staticmethod
    def make_old(db):
        """The vault's database as the 2.6.1 engine left it: applies and change_log rebuilt from the old CREATE statements, every row
        and rowid kept (the change_log index put back)."""
        with closing(sqlite3.connect(db)) as con:
            con.execute("PRAGMA foreign_keys = OFF")
            for table, create, cols in OLD_SHAPE:
                lst = ", ".join(cols)
                con.execute(f"CREATE TABLE {table}_keep AS SELECT rowid AS _rid, {lst} FROM {table}")
                con.execute(f"DROP TABLE {table}")
                con.execute(create)
                head = "rowid, " if table == "change_log" else ""
                con.execute(f"INSERT INTO {table} ({head}{lst}) SELECT {'_rid, ' if head else ''}{lst} FROM {table}_keep ORDER BY _rid")
                con.execute(f"DROP TABLE {table}_keep")
            con.execute("CREATE INDEX IF NOT EXISTS change_log_item ON change_log(item_id)")
            con.commit()

    @staticmethod
    def columns(db, table):
        with closing(sqlite3.connect(db)) as con:
            return {r[1]: r for r in con.execute(f"PRAGMA table_info({table})")}

    def dump(self, query):
        with closing(sqlite3.connect(self.vault / "system/tracker.db")) as con:
            return con.execute(query).fetchall()

    @needs("f1")
    def test_c01_f1_migrate_keeps_change_log_rowids_with_a_gap_and_the_item_event_links(self):
        """1. (#312, #314) A 2.6.1 database with a gap in change_log's rowids is migrated by `tracker.py migrate`: every change_log row keeps
        its rowid, so every item_events link and every `revert:<rowids>` still names the same change; the new columns are there and
        nullable; every value is kept; integrity and foreign keys are clean; a second migrate changes nothing (the file is the same
        bytes); a new apply is stamped with the engine's version."""
        db = self.vault / "system/tracker.db"
        events = self.count("item_events")
        self.assertGreater(events, 100, "the demo's history has item_events to point at the log")
        self.make_old(db)
        self.assertNotIn("engine_version", self.columns(db, "applies"), "the fixture is the 2.6.1 shape")
        ids = [r[0] for r in self.dump("SELECT rowid FROM change_log ORDER BY rowid")]
        gap = ids[len(ids) // 3]
        with closing(sqlite3.connect(db)) as con:                    # a hand-made gap in the middle, and the event that named it with it
            con.execute("DELETE FROM change_log WHERE rowid = ?", (gap,))
            con.execute("DELETE FROM item_events WHERE change = ?", (gap,))
            con.commit()
        rows = "SELECT rowid, at, apply_id, tbl, item_id, field, old_value, new_value, op, via FROM change_log ORDER BY rowid"
        before = {"log": self.dump(rows), "links": self.dump(LINKS), "applies": self.dump("SELECT apply_id, at, proposals, file_ops, undone_at FROM applies ORDER BY apply_id"),
                  "actions": self.dump("SELECT * FROM actions ORDER BY id")}
        numbers = [r[0] for r in before["log"]]
        self.assertNotEqual(numbers, list(range(1, len(numbers) + 1)), "the fixture has a gap in the rowids")
        self.assertGreater(len(before["links"]), 100)

        code, out = self.run_in_vault("tracker.py", "migrate")
        self.assertEqual(code, 0, out[-600:])
        self.assertIn("Migrated", out)
        for table, cols in (("applies", NEW_APPLY_COLS), ("change_log", NEW_LOG_COLS)):
            info = self.columns(db, table)
            for c in cols:
                self.assertIn(c, info, f"{table}.{c}")
                self.assertEqual((info[c][3], info[c][4]), (0, None), f"{table}.{c} is nullable with no default")
        self.assertEqual(self.dump(rows), before["log"], "every change_log row keeps its rowid and every value")
        self.assertEqual(self.dump(LINKS), before["links"], "every item_events link still names the same change (item, field, values)")
        self.assertEqual(self.dump("SELECT apply_id, at, proposals, file_ops, undone_at FROM applies ORDER BY apply_id"), before["applies"])
        self.assertEqual(self.dump("SELECT * FROM actions ORDER BY id"), before["actions"], "no work item moved")
        self.assertTrue(all(r[0] is None for r in self.dump(f"SELECT {', '.join(NEW_LOG_COLS)} FROM change_log")), "old rows are NULL in the new columns")
        with closing(sqlite3.connect(db)) as con:
            self.assertEqual(con.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(con.execute("PRAGMA foreign_key_check").fetchall(), [])
        backups = sorted((self.vault / "system/backups").glob("tracker-*-migrate.db"))
        self.assertTrue(backups, "migrate takes a dated copy first")

        was = hashlib.sha256(db.read_bytes()).hexdigest()
        code, out = self.run_in_vault("tracker.py", "migrate")
        self.assertEqual(code, 0, out[-300:])
        self.assertIn("up to date", out)
        self.assertEqual(hashlib.sha256(db.read_bytes()).hexdigest(), was, "the second migrate changes nothing")
        self.assertEqual(sorted((self.vault / "system/backups").glob("tracker-*-migrate.db")), backups, "and takes no new copy")

        self.apply_and_check_stamp()
        self.note(1, f"{len(numbers)} change_log rows, rowid {gap} removed; {len(before['links'])} item_events links identical before and after; "
                     "second migrate: same file bytes")

    def apply_and_check_stamp(self):
        version = (self.vault / "VERSION").read_text(encoding="utf-8").strip()
        self.stage_edit([self.new_action("Book the retrospective room")], "hc263-f1")
        code, out = self.run_in_vault("tracker.py", "apply")
        self.assertEqual(code, 0, out[-400:])
        last = self.sql("SELECT apply_id, engine_version, author, origin, sequence FROM applies ORDER BY apply_id DESC LIMIT 1")[0]
        self.assertEqual((last["engine_version"], last["author"], last["origin"], last["sequence"]), (version, None, None, None))
        top = max(r[0] for r in self.dump("SELECT rowid FROM change_log"))
        self.assertGreater(top, max(r[0] for r in self.dump("SELECT rowid FROM change_log WHERE apply_id IS NOT NULL AND apply_id < %d" % last["apply_id"])),
                           "new rows go after the highest rowid")



# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# 2  #250: fetch transcripts
# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

class FetchBase263(Engine263):
    """A vault and no server: the live server's observer (transcripts.SweepFetch) handed the reads a sweep makes, which are stood in
    for with fixture results. Microsoft 365 is never called. The helpers of checks 2 and 3, which each have a vault of their own (a
    transcript fetched by one must not be there for the other)."""

    def prepare_calendar(self):
        """Yesterday's three online meetings in the saved calendar: ev-1 confidential, ev-2 and ev-3 normal. Returns the day."""
        day = (date.fromisoformat((self.now or str(date.today()))[:10]) - timedelta(days=1)).isoformat()
        rows = [{"id": f"ev-{k}", "start": "09:00", "end": "10:00", "title": f"Harbour review {k}", "teams": True, "all_day": False,
                 "sensitivity": "confidential" if k == 1 else "normal"} for k in (1, 2, 3)]
        cal = self.staging("calendar.json")
        cal.write_text(json.dumps({"fetched": f"{day} 07:00", "days": {day: rows}}), encoding="utf-8")
        self.set_setting("sweep", "fetch_transcripts", True)
        return day

    def observe(self, steps):
        """What the observer fetched, given [(uri, payload, is_error)] read_resource results in order: {event id: outcome}."""
        code = ("import transcripts as T\nj = T.SweepFetch()\n"
                "for u, r, e in json.loads(%r):\n    j.observe(T.M365 + 'read_resource', {'uri': u}, json.dumps(r), e)\n"
                "print(json.dumps(j.outcomes))" % json.dumps(steps))
        return self.py(code)

    def inbox_text(self):
        inbox = self.vault / "inbox"
        return {p.name: p.read_text(encoding="utf-8", errors="replace") for p in inbox.iterdir() if p.suffix in (".vtt", ".txt")}

    @staticmethod
    def event(day, eid, uri, sensitivity="normal"):
        return {"id": eid, "subject": f"Harbour review {eid[-1]}", "isOrganizer": True, "isCancelled": False, "sensitivity": sensitivity,
                "organizer": {"name": "Alan Carter", "address": "alan.carter@example.com"},
                "attendees": [{"name": "Sara Khan", "address": "sara.khan@example.com"}],
                "start": {"dateTime": f"{day}T09:00:00.0000000", "timeZone": "UTC"}, "end": {"dateTime": f"{day}T10:00:00.0000000", "timeZone": "UTC"},
                "onlineMeeting": {"joinUrl": "https://teams.example.test/l/meetup-join/hc263"}, "meetingTranscriptUrl": uri}

    @staticmethod
    def transcript(day, text):
        cue = f"WEBVTT\n\n00:00:01.000 --> 00:00:05.000\n<v Sara Khan>{text}</v>\n"
        return {"meeting": {"id": "m1", "subject": "Harbour review"},
                "transcripts": [{"id": "tr0", "createdDateTime": f"{day}T09:05:30Z", "endDateTime": f"{day}T09:55:00Z", "content": cue}]}

class Fetch263(FetchBase263):
    """Check 2."""

    def test_c02_fetch_a_confidential_meetings_transcript_is_never_fetched_however_its_url_is_written(self):
        """2. (#250) With fetching on, a confidential meeting's transcript is never written to inbox/, and never under another event's name:
        a normal event that names the same meeting by another spelling of its URL (upper case, a trailing slash, a fragment, an extra
        query, percent-encoding, a double slash, another window) ties to nobody, whichever event is read first and whichever of the two
        URLs the transcript is read by. Nothing reaches the tracker, nothing is staged. A lone normal meeting is fetched (the control)."""
        day = self.prepare_calendar()
        secret = "CONFIDENTIAL-HR-TEXT-HC263"
        conf = self.transcript(day, secret)
        base = "meeting-transcript:///events/hc263meetingone"
        window = f"start={day}T09:00:00Z&end={day}T10:00:00Z"
        u = f"{base}?{window}"
        variants = {"upper case": base.replace("meeting-transcript", "MEETING-TRANSCRIPT") + "?" + window, "trailing slash": base + "/?" + window,
                    "a fragment": u + "#frag", "an extra query": u + "&extra=1", "no query": base, "percent-encoded": base.replace("hc263", "%68c263") + "?" + window,
                    "a double slash": base.replace("/events/", "//events/", 1) + "?" + window, "upper-case path": base.upper().replace("MEETING-TRANSCRIPT", "meeting-transcript") + "?" + window}
        applies, staged = self.count("applies"), self.pending()
        ev1 = ("calendar:///events/ev-1", self.event(day, "ev-1", u, "confidential"), False)
        for name, spelling in variants.items():
            ev2 = ("calendar:///events/ev-2", self.event(day, "ev-2", spelling), False)
            for order in ((ev1, ev2), (ev2, ev1)):
                for read_uri in (spelling, u):
                    with self.subTest(spelling=name, first=order[0][0][-4:], read=("its own" if read_uri == spelling else "the confidential one")):
                        got = self.observe([*order, (read_uri, conf, False)])
                        self.assertEqual(got, {}, f"fetched: {got}")
                        leaked = [n for n, t in self.inbox_text().items() if secret in t]
                        self.assertEqual(leaked, [], "the confidential text reached inbox/")
        # the same, with the confidential event read first but never read again, and a transcript read the run never named
        self.assertEqual(self.observe([(f"{base}?{window}", conf, False)]), {}, "a transcript no event read named is never tied")
        self.assertFalse(any(secret in t for t in self.inbox_text().values()))

        # the control: a lone normal meeting, read as the sweep reads it, is fetched into inbox/
        u3 = f"meeting-transcript:///events/hc263meetingthree?{window}"
        got = self.observe([("calendar:///events/ev-3", self.event(day, "ev-3", u3), False), (u3, self.transcript(day, "A normal meeting."), False)])
        self.assertEqual(got, {"ev-3": "fetched"}, "the control: the harness can fetch a normal meeting")
        files = self.inbox_text()
        self.assertTrue(any("A normal meeting." in t for t in files.values()), "and its text is in inbox/")
        self.assertFalse(any(secret in t for t in files.values()))
        self.assertEqual(self.count("applies"), applies, "nothing reached the tracker")
        self.assertEqual(self.pending(), staged, "and nothing was staged")
        self.note(2, f"{len(variants)} spellings x 2 read orders x 2 read URLs: nothing fetched, no confidential text in inbox/; control fetched")


class ReadOrder263(FetchBase263):
    """Check 3 (an expected failure). Its own vault, so nothing fetched by check 2 is there to hide the defect."""

    @unittest.expectedFailure
    def test_c03_fetch_the_transcript_read_before_the_confidential_event_is_never_fetched_under_the_other_events_name(self):
        """3. (#250, Team Cap's MEDIUM on v262-line 88c2a948, "NOT READY") KNOWN OPEN DEFECT, so an expected failure until it is fixed.
        ev-1 (confidential) and ev-2 (normal) name the same meeting. Claude reads ev-2's event, THEN the shared transcript URL, THEN
        ev-1's event (the order cx-sweep prescribes: an event, its transcript, the next meeting). The hold is not known yet when the
        transcript is read, because it is filled only by a confidential event already read; so the transcript is written to inbox/ on
        the read, under ev-2's name. It must not be: nothing may be fetched under ev-2's name and no confidential text may reach inbox/,
        whether ev-2 names the very same URL or the meeting with its own start/end window (the transcript read by ev-2's URL). When the fix lands (writing at the end of the run, or reading the confidential events first) this turns into an
        unexpected success: delete the decorator."""
        day = self.prepare_calendar()
        base = "meeting-transcript:///events/hc263readorder"
        window = f"start={day}T09:00:00Z&end={day}T10:00:00Z"
        u = f"{base}?{window}"
        own_window = f"{base}?start={day}T09:00:00Z&end={day}T09:59:00Z"       # another window, still round the transcript's own times
        applies, staged = self.count("applies"), self.pending()
        failures = []
        for n, (name, ev2_url, read_url) in enumerate((("the same URL", u, u), ("ev-2's own window, read by it", own_window, own_window)), 1):
            secret = f"CONFIDENTIAL-HR-TEXT-HC263-{n}"
            ev1 = ("calendar:///events/ev-1", self.event(day, "ev-1", u, "confidential"), False)
            ev2 = ("calendar:///events/ev-2", self.event(day, "ev-2", ev2_url), False)
            got = self.observe([ev2, (read_url, self.transcript(day, secret), False), ev1])
            leaked = [name_ for name_, t in self.inbox_text().items() if secret in t]
            if got or leaked:
                failures.append(f"{name}: fetched {got}, confidential text in inbox/ as {leaked}")
            for f in (self.vault / "inbox").iterdir():                   # the next form starts clean: a name already taken would hide it
                if f.name in self.inbox_text():
                    f.unlink()
            for state in ("sweep-fetched.json", "transcripts.json"):      # and the record that the meeting was fetched, which would skip it
                if self.staging(state).exists():
                    self.staging(state).unlink()
        self.assertEqual(failures, [], "the transcript was read before the confidential event, and was written under ev-2's name")
        self.assertEqual(self.count("applies"), applies, "nothing reached the tracker")
        self.assertEqual(self.pending(), staged, "and nothing was staged")
        self.note(3, "ev-2, then the shared transcript, then ev-1 (2 forms): nothing fetched, no confidential text in inbox/")


def _uncommitted_engine():
    r = subprocess.run(["git", "status", "--porcelain", "--", "system", ".claude"], cwd=REPO, capture_output=True, text=True)
    return bool(r.stdout.strip())


def _main():
    """Standalone: build the zip once (with the uncommitted engine files when there are any) and point the classes at it."""
    if not os.environ.get("CREAITE_HC_BASE"):
        import atexit
        import handcheck
        s = handcheck.Session(dirty=_uncommitted_engine())
        s.build_zip()
        os.environ.update({"CREAITE_HC_DIR": str(s.dir), "CREAITE_HC_ZIP": str(s.zip), "CREAITE_HC_NOW": s.now, "CREAITE_HC_BASE": "standalone"})
        if not os.environ.get("CREAITE_HC_KEEP"):
            atexit.register(shutil.rmtree, s.dir, ignore_errors=True)
    unittest.main()


if __name__ == "__main__":
    _main()
