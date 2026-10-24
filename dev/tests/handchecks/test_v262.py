"""creaite 2.6.2's hand checks, automated against a vault made from the release zip (the fictional demo portfolio: Falcon Data
Platform and the rest). One check per item, `test_cNN_...`, its docstring quoting what the item must do. There is no Product Manager's
sheet for 2.6.2 yet, so the numbers are the items in order and the PM can number them in. F1 (#312, #314) and #250 (transcripts) went to
2.6.3 on 23-10-2026 (Alan); their checks are in test_v263.py.

   1 emit  (#275)        a failing item_events insert rolls apply, undo and undo-changes back whole (rc 1, plain words); a dry run records nothing
   2 discard (#275)      Undo puts back a genuine Discard and refuses a planted file, a symlink, a second hard link, a wrong checksum, a replay
   3 follow              the follow flag is shown in the app, the word VIP never is; a person ticked Follow is alerted
   4 #183  draft         the Outlook draft route fails closed: no hook, a crash, no decision, an injected Bcc, a second create all leave nothing made
   5 #183  setting       Draft email in Outlook is off by default, and while off no run starts
   6 #322                Today hides the Needs attention heading when it is empty, shows it with an item, live (no reload)
   7 small2 review       approve and reject with --expect refuse an item that has changed or moved (the command line and /api/review)
   8 small2 review       a repeated --expect is refused, never the last one taken
   9 small2 inbox        an upload that fails part-way leaves no partial file in inbox/ and says it in plain words
  10 #321                The New note drawer can be widened: a focusable separator handle (keyboard and pointer) up to the page width and
                         never beyond it, remembered per viewer (the page still works when storage throws), a Reset width button, full
                         width at 900 px, and no write to the server for a width change

How a check is wired (every class has a vault of its own, made from the zip, so nothing a check changes reaches another):
  Emit262                         a vault and no server: the engine's own commands, or its code run in the vault
  Discard262, Review262           a vault and its live server (the page's own token), no browser
  Inbox262                        a vault and a live server started with a file-size limit (a write past it fails, as a full disk does)
  Draft262                        a vault and a live server whose Claude is a stand-in that plays the draft run (never Microsoft 365)
  Follow262, Today262, Drawer262  a vault, its live server and Chrome

The guarded parts (emit, discard, follow, #183, small2) are the 2.6.2 chain, dev/proposals/GUARDED-2.6.2.chain.
A check that needs a guarded change this tree does not have is an EXPECTED FAILURE (the convention test_v261_intake307_identity.py
uses): it still runs, is red for the right reason, and turns into an unexpected success (flagged) the moment the change is in. With the
chain applied they are plain checks. #322 and #321 are not guarded and are on the line (check 10 is page-only: it passes with or without the chain).

Run them (from the repository root; a release zip is built from this checkout first):
  python3 dev/tests/handchecks/test_v262.py                         all, with the committed tree (or --dirty: uncommitted engine files)
  python3 dev/tests/handchecks/test_v262.py Emit262.test_c01_...    one check
  python3 dev/tools/handcheck.py v2.6.2 [--dirty] [--only 1,4]      the runner (Results table, run folder)
Standalone, the module builds the zip itself, with the uncommitted engine files when the tree has any (the chain applied but not
committed), and removes its run folder at the end (CREAITE_HC_KEEP=1 keeps it). With CREAITE_HC_BASE, CREAITE_HC_DIR and CREAITE_HC_ZIP
set (what handcheck.py sets) it uses those. Safe at -j 3: every vault, port and folder is new, and every server and Chrome is stopped by
its own process group (proc_guard), never by name.

Never Microsoft 365, never a real model: Claude is the stand-in. Fictional data only (the demo's people).
Live only: the draft actually appearing in Outlook's Drafts folder (check 4 proves nothing is made when it must not be, and what is
asked for when it may be; the real tool needs Alan's live Outlook test).
"""
import base64
import hashlib
import json
import os
import re
import resource
import shutil
import sqlite3
import subprocess
import sys
import unittest
import urllib.error
import urllib.request
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

KIND = {n: "scriptable" for n in range(1, 11)}
LIVE_ONLY = {}        # check 4's last step (the draft in Outlook's Drafts folder) is live only, said in its note; the check itself runs


def _src(name):
    p = SCRIPTS / name
    return p.read_text(encoding="utf-8") if p.is_file() else ""


# What this tree has of the guarded 2.6.2 chain (read from the repository's own files, which the zip is built from)
HAS = {
    "emit": "emit-event-txn" in _src("tracker.py"),
    "discard": "restore-discarded" in _src("review.py") and "/api/review/restore-discarded" in _src("live_server.py"),
    "follow": "creaite follow check" in _src("live_server.py") and "Follow" in _src("propose.py"),
    "draft": "/api/email/draft" in _src("live_server.py") and "hook_settings" in _src("draft_delivery.py"),
    "expect": "_main_with_expect" in _src("review.py") and "--expect" in _src("live_server.py"),
    "inbox": "2.6.2: plain words" in _src("live_server.py"),
    "today": 'attnSec").hidden' in (REPO / "system/templates/dashboard/src/today.js").read_text(encoding="utf-8"),
}
CHAIN = {"emit": "emit-event-txn/tracker.diff", "discard": "discard-undo (review.py, reach.py, live_server.py)",
         "follow": "vip-follow-code and vip-follow-rules", "draft": "draft-delivery/live_server.diff (183h)",
         "expect": "review-expect (review.py, live_server.py)", "inbox": "inbox-upload-oserror/live_server.diff",
         "today": "#322"}


def needs(key):
    """A check that needs a change of the guarded 2.6.2 chain: an expected failure while this tree lacks it, a plain check once it has it."""
    def wrap(fn):
        if HAS[key] or os.environ.get("CREAITE_HC_SHOW_XFAIL"):          # CREAITE_HC_SHOW_XFAIL=1: run it as a plain check to see why it fails
            return fn
        fn.__doc__ = (fn.__doc__ or "") + f" [expected failure: {CHAIN[key]} is not in this tree]"
        return unittest.expectedFailure(fn)
    return wrap


VTT = ("WEBVTT\n\n00:00:01.000 --> 00:00:05.000\n<v Alan Carter>Morning all, first the supplier.</v>\n\n"
       "00:00:05.000 --> 00:00:09.000\n<v Sara Khan>I will send the revised plan next week.</v>\n")


class Engine262(HandcheckCase):
    """Checks that need the vault (and sometimes its server) but not a browser. Own vault; no server unless `with_server`."""
    own_vault = True
    with_server = False
    preexec = None                       # a function run in the server's process before it starts (a file-size limit)
    claude = None                        # the path of a stand-in Claude for the server (default: the hand-check vault's)

    # ── the vault and server ──

    @classmethod
    def start_server(cls):
        import handcheck
        s = hcbase.session() or handcheck.Session(os.environ["CREAITE_HC_DIR"])
        if not s.zip and os.environ.get("CREAITE_HC_ZIP"):
            s.zip = Path(os.environ["CREAITE_HC_ZIP"])
        cls._hc, cls.v, cls.proc, cls.base = s, None, None, None
        cls.vault = s.make_vault(f"vault-{cls.__name__}")
        cls.now = os.environ.get("CREAITE_HC_NOW") or s.now
        cls.prepare()
        if cls.with_server:
            cls.proc, cls.base = cls.spawn()

    @classmethod
    def prepare(cls):
        """Anything to put in the vault before its server starts."""

    @classmethod
    def spawn(cls):
        """The live server on a free port, as Session.start_server starts it, with this class's own Claude and limits."""
        import time
        import proc_guard
        from live_browser import free_port
        s, root = cls._hc, cls.vault
        port = free_port()
        base = f"http://127.0.0.1:{port}"
        env = {**os.environ, **s.server_env(root, port)}
        if cls.claude:
            env["CREAITE_CLAUDE"] = str(cls.claude)
        with open(s.dir / f"server-{root.name}.log", "ab") as logf:
            proc = proc_guard.spawn([sys.executable, str(root / "system/scripts/live_server.py")], cwd=root, env=env, stdout=logf,
                                    stderr=subprocess.STDOUT, preexec_fn=cls.preexec)
        deadline = time.time() + 40
        while True:
            try:
                urllib.request.urlopen(base + "/health", timeout=1)
                return proc, base
            except OSError:
                if time.time() > deadline or proc.poll() is not None:
                    proc_guard.stop(proc, grace=5)
                    raise RuntimeError("the live server didn't answer; see " + str(s.dir / f"server-{root.name}.log")) from None
                time.sleep(0.2)

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

    def stage_edit(self, items, name="hc262"):
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
                                                            "due_date": (day + timedelta(days=days)).isoformat(), "source": "hand check 262"}}

    # ── the live server ──

    def page_token(self):
        """The token the open page carries (the server writes it into the page)."""
        html = urllib.request.urlopen(self.base + "/", timeout=30).read().decode("utf-8")
        return json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]

    def post(self, path, body=None, token=True, page=True, host=None):
        """POST as the open page does: (HTTP status, JSON answer). A fault gives its status, never an exception."""
        headers = {"Content-Type": "application/json"}
        if token:
            headers["X-Creaite-Token"] = self.page_token()
        if page:
            headers["Sec-Fetch-Site"] = "same-origin"
            headers["Origin"] = self.base
        if host:
            headers["Host"] = host
        req = urllib.request.Request(self.base + path, data=json.dumps(body if body is not None else {}).encode(), method="POST",
                                     headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            with e:
                raw = e.read()
            try:
                return e.code, json.loads(raw or b"{}")
            except ValueError:
                return e.code, {}

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

    def held_minutes(self, title):
        """Minutes staged by minutes.py (as cx-minutes does) whose transcript then leaves the inbox: Review holds them.
        Returns (the proposal's path, its bytes)."""
        from test_tracker import make_draft
        day = (self.now or str(date.today()))[:10]
        transcript = f"inbox/{day} {title}.vtt"
        (self.vault / transcript).write_text(VTT, encoding="utf-8")
        draft = f"system/staging/drafts/{day} {title}.docx"
        make_draft(self.vault / draft)
        item = {"table": "actions", "section": "Actions", "values": {"project": "FAL", "description": f"Chase the supplier ({title})",
                                                                      "owner": "Sara Khan", "due_date": "2030-06-10"}}
        spec = self.staging("drafts/hc262-meeting.json")
        spec.write_text(json.dumps({"title": title, "date": day, "projects": ["FAL"], "transcript": transcript, "draft": draft,
                                    "items": [item]}), encoding="utf-8")
        before = self.pending()
        code, out = self.run_in_vault("minutes.py", "stage", "system/staging/drafts/hc262-meeting.json")
        self.assertEqual(code, 0, out[-500:])
        new = sorted(self.pending() - before)
        self.assertEqual(len(new), 1, out[-300:])
        prop = self.staging(new[0])
        (self.vault / transcript).unlink()
        return prop, prop.read_bytes()


# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# 1  emit: a failing item_events insert rolls the whole change back
# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

class Emit262(Engine262):
    """Check 1. A vault and no server: a trigger in the vault's own database makes every insert into item_events fail, as a full disk would."""

    def state(self):
        return {"change_log": self.count("change_log"), "applies": self.count("applies"), "actions": self.count("actions"),
                "item_events": self.count("item_events"),
                "undone": self.sql("SELECT count(*) AS n FROM applies WHERE undone_at IS NOT NULL")[0]["n"],
                "orphans": self.sql("SELECT count(*) AS n FROM change_log c WHERE c.field != 'updated_at' AND NOT EXISTS "
                                    "(SELECT 1 FROM item_events e WHERE e.change = c.rowid)")[0]["n"]}

    def trigger(self, name, when=""):
        with closing(sqlite3.connect(self.vault / "system/tracker.db")) as con:
            con.execute(f"CREATE TRIGGER {name} BEFORE INSERT ON item_events {when} BEGIN SELECT RAISE(ABORT, 'disk I/O error'); END")
            con.commit()

    def drop(self, name):
        with closing(sqlite3.connect(self.vault / "system/tracker.db")) as con:
            con.execute(f"DROP TRIGGER IF EXISTS {name}")
            con.commit()

    def plain(self, out):
        self.assertNotIn("Traceback", out)
        self.assertNotIn(str(self.vault), out, "no path in the words")
        self.assertNotIn("sqlite", out.lower())

    @needs("emit")
    def test_c01_emit_a_failing_history_insert_rolls_apply_undo_and_undo_changes_back_whole(self):
        """1. (#275) When the history insert (item_events) fails, `tracker.py apply`, `undo` and `undo-changes` each stop with exit 1 and a
        plain message and write nothing at all (no change_log rows, no applies row, no work item, no event); the proposal is byte for
        byte as it was, so every approval stands. A dry run (`validate`) records nothing, with a healthy history and with a failing one,
        and flags no item invalid. With the fault gone the same proposal applies and undoes."""
        name = self.stage_edit([self.new_action("Confirm the emit check's room")], "hc262-emit")
        prop = self.staging(name)
        raw = prop.read_bytes()

        # a dry run records nothing, healthy
        start = self.state()
        code, out = self.run_in_vault("tracker.py", "validate", f"system/staging/{name}")
        self.assertEqual(code, 0, out[-300:])
        self.assertEqual(self.state(), start, "validate wrote nothing (no change_log rows, no events)")
        self.assertEqual(prop.read_bytes(), raw)

        # a lasting fault: the apply stops whole
        self.trigger("hc_no_events")
        code, out = self.run_in_vault("tracker.py", "validate", f"system/staging/{name}")
        self.assertEqual(self.state(), start, "a dry run with a failing history records nothing")
        self.assertNotIn("invalid", json.loads(prop.read_text(encoding="utf-8"))["items"][0].get("flags", []), "and flags no item invalid")
        self.assertEqual(prop.read_bytes(), raw)
        code, out = self.run_in_vault("tracker.py", "apply")
        self.assertEqual(code, 1, out[-400:])
        self.assertIn("nothing was written", out)
        self.assertNotIn("Held in Review", out, "a database fault is not a fault in each item")
        self.plain(out)
        self.assertEqual(self.state(), start, "apply: nothing written")
        self.assertEqual(prop.read_bytes(), raw, "apply: the proposal is byte for byte as it was")
        self.assertEqual(self.count("applies"), start["applies"])
        self.drop("hc_no_events")

        # the same proposal applies once the fault is gone
        code, out = self.run_in_vault("tracker.py", "apply")
        self.assertEqual(code, 0, out[-400:])
        applied = self.state()
        self.assertGreater(applied["change_log"], start["change_log"])
        self.assertEqual(applied["orphans"], 0, "every change has its event")

        # undo whose own events fail: nothing is reversed
        self.trigger("hc_no_undo_events", "WHEN NEW.route = 'undo'")
        code, out = self.run_in_vault("tracker.py", "undo")
        self.assertEqual(code, 1, out[-400:])
        self.plain(out)
        self.assertEqual(self.state(), applied, "undo: nothing changed, the apply is not marked undone")
        self.drop("hc_no_undo_events")

        # undo-changes of one change, with a failing history: nothing is reversed
        rowid = self.sql("SELECT rowid AS r FROM change_log WHERE field = 'description' AND new_value LIKE '%emit check%'")[0]["r"]
        self.trigger("hc_no_events2")
        code, out = self.run_in_vault("tracker.py", "undo-changes", str(rowid))
        self.assertEqual(code, 1, out[-400:])
        self.plain(out)
        self.assertEqual(self.state(), applied, "undo-changes: nothing changed")
        self.drop("hc_no_events2")

        # the control: with the history working, undo-changes and undo go through
        code, out = self.run_in_vault("tracker.py", "undo-changes", str(rowid))
        self.assertEqual(code, 0, out[-400:])
        code, out = self.run_in_vault("tracker.py", "undo")
        self.assertIn(code, (0, 1), out[-300:])
        self.note(1, "apply, undo and undo-changes each exit 1 with 'nothing was written' and change no row; the proposal is the same bytes; "
                     "a dry run records nothing")


# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# 2  Discard and its Undo
# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

class Discard262(Engine262):
    """Check 2. A vault and its live server: Discard through the page's own route, Undo through the new one."""
    with_server = True

    def discarded(self, title):
        """Held minutes set aside by Discard (POST /api/review, as the page's button does): (the proposal's name, its bytes before, the
        set-aside file's path)."""
        prop, before = self.held_minutes(title)
        # 2.6.3 makes `expect` mandatory on /api/review: send the minutes row's fingerprint, as the page does
        fp = self.py("import build_dashboard as b, json\nd = json.load(open('system/staging/%s'))\nprint(json.dumps(b.block_fp(d['meeting'])))" % prop.name)
        code, res = self.post("/api/review", {"file": prop.name, "ref": "meeting", "decision": "discard", "expect": fp})
        self.assertEqual((code, res.get("ok")), (200, True), res)
        aside = self.staging("discarded") / prop.name
        self.assertTrue(aside.is_file() and not prop.exists(), "Discard set the proposal aside")
        return prop.name, before, aside

    def restore(self, name):
        return self.post("/api/review/restore-discarded", {"file": name})

    def refused(self, name, why):
        """The Undo is refused in words, and nothing moved: the file is still set aside, staging gets nothing."""
        waiting = sorted(p.name for p in self.staging().glob("proposed-*.json"))
        aside = self.staging("discarded") / name
        was = aside.read_bytes() if aside.exists() else None
        code, res = self.restore(name)
        self.assertFalse(res.get("ok"), f"{why}: the Undo was not refused: {res}")
        self.assertTrue(res.get("message"), f"{why}: it says why")
        self.assertNotIn("Traceback", str(res))
        self.assertNotIn(str(self.vault), str(res), f"{why}: no path in the words")
        self.assertEqual(sorted(p.name for p in self.staging().glob("proposed-*.json")), waiting, f"{why}: nothing came back")
        if was is not None:
            self.assertEqual(aside.read_bytes(), was, f"{why}: the set-aside file is untouched")
        return res["message"]

    @needs("discard")
    def test_c02_discard_undo_restores_a_genuine_discard_and_refuses_everything_else(self):
        """2. (#275) Discard on held minutes sets the proposal aside; Undo puts it back byte for byte, in Review again, and writes nothing to
        the record. Undo refuses, in words and moving nothing: a file planted in the set-aside folder, a symlink, a second hard link, a
        file whose checksum differs from the one Discard recorded, and a replay (a second Undo of the same name)."""
        decided = self.count("actions"), self.count("applies")
        # the genuine one
        name, before, aside = self.discarded("Supplier checkpoint")
        ledger = self.staging("discarded-ledger.jsonl")
        self.assertTrue(ledger.is_file(), "Discard keeps a ledger of what it set aside")
        last = json.loads(ledger.read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual((last["name"], last["sha256"]), (aside.name, hashlib.sha256(aside.read_bytes()).hexdigest()),
                         "Discard records the checksum of what it set aside")
        code, res = self.restore(name)
        self.assertEqual((code, res.get("ok")), (200, True), res)
        self.assertEqual(self.staging(name).read_bytes(), before, "the proposal is back, byte for byte")
        self.assertFalse(aside.exists())
        _, rows = self.run_in_vault("review.py", "list", "--json")
        self.assertIn(name, rows, "and Review lists it again")
        self.assertEqual((self.count("actions"), self.count("applies")), decided, "Undo writes nothing to the record")

        # a replay: the same name put into the folder again after its Undo
        shutil.copyfile(self.staging(name), aside)
        self.refused(name, "a replay of an Undo")
        aside.unlink()

        # a second Discard of the same proposal, then the ways the folder can be tampered with
        name2, before2, aside2 = self.discarded("Vendor checkpoint")
        planted = self.staging("discarded") / "proposed-0000-00-00-planted.json"
        planted.write_bytes(aside2.read_bytes())
        self.refused(planted.name, "a file planted with no record of setting it aside")
        planted.unlink()
        forged = self.staging("discarded") / "proposed-0000-00-00-forged.json"
        forged.write_bytes(aside2.read_bytes())
        with open(ledger, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"name": forged.name, "sha256": "0" * 64}) + "\n")
        self.refused(forged.name, "a wrong checksum")
        forged.unlink()
        with open(aside2, "a", encoding="utf-8") as fh:               # edited after Discard
            fh.write(" ")
        self.refused(name2, "a file edited after Discard")

        name3, before3, aside3 = self.discarded("Partner checkpoint")
        outside = self.vault / "hc262-outside.json"                    # a symlink in place of the file
        shutil.copyfile(aside3, outside)
        aside3.unlink()
        os.symlink(outside, aside3)
        self.refused(name3, "a symlink")
        aside3.unlink()
        outside.unlink()

        name4, before4, aside4 = self.discarded("Board checkpoint")
        other = self.vault / "hc262-second-link.json"                  # a second hard link to the same file
        os.link(aside4, other)
        self.refused(name4, "a second hard link")
        other.unlink()
        code, res = self.restore(name4)
        self.assertEqual((code, res.get("ok")), (200, True), "with the second link gone the genuine Undo works: " + str(res))
        self.assertEqual(self.staging(name4).read_bytes(), before4)
        self.note(2, "Undo restored a genuine Discard byte for byte; refused a planted file, a forged checksum, an edited file, a symlink, a "
                     "second hard link and a replay, each in words with nothing moved")


# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# 7, 8  small2: review --expect
# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

class Review262(Engine262):
    """Checks 7 and 8. A vault and its live server: pending mail proposals of the check's own, decided from the command line and through /api/review."""
    with_server = True
    _n = 0

    def sweep_file(self, descs):
        """A pending mail proposal (what cx-sweep stages), one new action per description, numbered 1..n. Returns its name."""
        Review262._n += 1
        day = (self.now or str(date.today()))[:10]
        name = f"proposed-{day}-{10 + Review262._n:02d}00-sweep-hc262-{Review262._n}.json"
        due = (date.fromisoformat(day) + timedelta(days=30)).isoformat()
        mail = ("Email · From: Priya Nair <priya.nair@meridian.example> · Subject: Harbour works · Sent: %s 09:00 · "
                "Link: https://outlook.example.test/owa/?ItemID=hc262-%d" % (day, Review262._n))
        items = [{"n": k, "op": "new", "table": "actions", "match": "strong", "flags": [], "decision": "pending",
                  "values": {"project": "FAL", "description": d, "owner": "Sara Khan", "due_date": due, "source": mail}}
                 for k, d in enumerate(descs, 1)]
        self.staging(name).write_text(json.dumps({"created": f"{day}T09:00:00", "source_run": "cx-sweep", "files": [], "items": items}, indent=2),
                                      encoding="utf-8")
        return name

    def decisions(self, name):
        return {i["n"]: i["decision"] for i in json.loads(self.staging(name).read_text(encoding="utf-8"))["items"]}

    def number(self, name, ref):
        rc, out = self.run_in_vault("review.py", "list", "--json")
        rows = json.loads(out[out.index("["):out.rindex("]") + 1])
        return next(r["n"] for r in rows if r["file"] == name and r["ref"] == ref)

    def fingerprint(self, name, ref):
        return self.py("import build_dashboard as b, json\nd = json.load(open('system/staging/%s'))\n"
                       "print(json.dumps(b.item_fp(next(i for i in d['items'] if i['n'] == %d))))" % (name, ref))

    def review(self, *args):
        return self.run_in_vault("review.py", *args)

    @needs("expect")
    def test_c07_review_expect_approve_and_reject_refuse_an_item_that_changed_or_moved(self):
        """7. (small2, #314) `review.py approve N --expect <fp>` and `reject N --expect <fp>` (and /api/review with `expect`, as the page
        sends it) act only if item N is still the item the caller meant: a matching fingerprint decides that item and no other; an item
        changed under the caller, or renumbered because another was taken out, is refused in one plain line (exit 2, nothing decided,
        no traceback, no path); a call without --expect is unchanged."""
        name = self.sweep_file(["Alpha lantern check", "Bravo anchor weigh", "Charlie gazebo paint"])
        n2, fp2, fp1 = self.number(name, 2), self.fingerprint(name, 2), self.fingerprint(name, 1)
        self.assertNotEqual(fp1, fp2)
        # a match decides that item only
        code, out = self.review("approve", str(n2), f"--expect={fp2}")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.decisions(name), {1: "pending", 2: "approved", 3: "pending"})
        # a mismatch: the number names another item than the caller meant
        n3 = self.number(name, 3)
        for cmd in ("approve", "reject"):
            code, out = self.review(cmd, str(n3), "--expect", fp2)
            self.assertEqual(code, 2, out)
            self.assertIn("has changed since you looked at it", out)
            self.assertNotIn("Traceback", out)
            self.assertNotIn(str(self.vault), out)
        self.assertEqual(self.decisions(name), {1: "pending", 2: "approved", 3: "pending"}, "nothing was decided")
        # renumbered under the caller: the page looked at Bravo (its number); Alpha is taken out; that number now names Charlie
        for cmd in ("reject", "approve"):
            moved = self.sweep_file(["Alpha lantern check", "Bravo anchor weigh", "Charlie gazebo paint"])
            n_bravo, fp_bravo = self.number(moved, 2), self.fingerprint(moved, 2)
            f = self.staging(moved)
            data = json.loads(f.read_text(encoding="utf-8"))
            data["items"] = [i for i in data["items"] if i["values"]["description"] != "Alpha lantern check"]
            for k, it in enumerate(data["items"], 1):
                it["n"] = k
            f.write_text(json.dumps(data), encoding="utf-8")
            code, out = self.review(cmd, str(n_bravo), f"--expect={fp_bravo}")
            self.assertEqual(code, 2, f"{cmd} of a moved item: {out}")
            self.assertIn("has changed since you looked at it", out)
            self.assertEqual(self.decisions(moved), {1: "pending", 2: "pending"}, "Charlie, now in Bravo's place, is not touched")
        # changed under the caller: the same number, new content
        name_b = self.sweep_file(["Delta kettle review", "Echo harbour survey"])
        nd, fpd = self.number(name_b, 1), self.fingerprint(name_b, 1)
        f = self.staging(name_b)
        data = json.loads(f.read_text(encoding="utf-8"))
        data["items"][0]["values"]["description"] = "Delta kettle review (changed behind the page)"
        f.write_text(json.dumps(data), encoding="utf-8")
        code, out = self.review("approve", str(nd), f"--expect={fpd}")
        self.assertEqual(code, 2, out)
        self.assertEqual(self.decisions(name_b), {1: "pending", 2: "pending"})
        # the page's own call
        name_c = self.sweep_file(["Foxtrot ladder count", "Golf meadow plan"])
        fp_f = self.fingerprint(name_c, 1)
        code, res = self.post("/api/review", {"file": name_c, "ref": 2, "decision": "approved", "modes": [], "expect": fp_f})
        self.assertFalse(res.get("ok"), f"/api/review decided item 2 on item 1's fingerprint: {res}")
        self.assertIn("changed since you looked", res.get("message", ""))
        self.assertEqual(self.decisions(name_c), {1: "pending", 2: "pending"})
        code, res = self.post("/api/review", {"file": name_c, "ref": 1, "decision": "approved", "modes": [], "expect": fp_f})
        self.assertTrue(res.get("ok"), res)
        self.assertEqual(self.decisions(name_c), {1: "approved", 2: "pending"})
        code, res = self.post("/api/review", {"file": name_c, "ref": 2, "decision": "rejected", "modes": [], "expect": "not-a-fingerprint"})
        self.assertFalse(res.get("ok"), "a malformed expect is refused, not ignored")
        self.assertEqual(self.decisions(name_c), {1: "approved", 2: "pending"})
        # no --expect: as before
        code, out = self.review("approve", str(self.number(name_c, 2)))
        self.assertEqual(code, 0, out)
        self.assertEqual(self.decisions(name_c), {1: "approved", 2: "approved"})
        self.note(7, "a match decides one item; a changed or moved item is refused (exit 2, 'has changed since you looked at it') by the command "
                     "line and /api/review, nothing decided; no --expect behaves as before")

    @needs("expect")
    def test_c08_review_expect_a_repeated_expect_is_refused_never_the_last_one_taken(self):
        """8. (small2 note 4) `approve N --expect=<wrong> --expect=<right>` and `--expect=<right> --expect=<wrong>` and the same fingerprint
        twice are all refused (exit 2, '--expect goes with …'), in either order, with nothing decided; one --expect with the right
        fingerprint still decides."""
        name = self.sweep_file(["Hotel boat count", "India roof survey"])
        n, right, wrong = self.number(name, 1), self.fingerprint(name, 1), "aaaaaaaaaaaa"
        pairs = ((f"--expect={wrong}", f"--expect={right}"), (f"--expect={right}", f"--expect={wrong}"), (f"--expect={right}", f"--expect={right}"),
                 (f"--expect={wrong}", "--expect", right), ("--expect", right, "--expect", wrong))
        for cmd in ("approve", "reject"):
            for args in pairs:
                with self.subTest(cmd=cmd, args=" ".join(a.replace(right, "RIGHT").replace(wrong, "WRONG") for a in args)):
                    code, out = self.review(cmd, str(n), *args)
                    self.assertEqual(code, 2, out)
                    self.assertIn("--expect goes with", out)
                    self.assertEqual(self.decisions(name), {1: "pending", 2: "pending"}, "nothing decided")
        code, out = self.review("approve", str(n), f"--expect={right}")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.decisions(name), {1: "approved", 2: "pending"})
        self.note(8, "a repeated --expect is refused in every order and form (approve and reject), nothing decided")


# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# 9  small2: inbox upload
# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def _limit_file_size():
    """In the server's process: a write past this many bytes fails (EFBIG), as a full disk does. Python ignores the signal."""
    resource.setrlimit(resource.RLIMIT_FSIZE, (6_000_000, 6_000_000))


class Inbox262(Engine262):
    """Check 9. A vault and a live server with a file-size limit."""
    with_server = True
    preexec = staticmethod(_limit_file_size)

    def upload(self, name, data):
        body = {"name": name, "data": base64.b64encode(data).decode()}
        return self.post("/api/inbox/upload", body)

    def inbox(self):
        return sorted(p.name for p in (self.vault / "inbox").iterdir())

    @needs("inbox")
    def test_c09_inbox_upload_that_fails_part_way_leaves_no_partial_file(self):
        """9. (small2) An upload whose write fails part-way (the disk is full) answers in plain words (no exception text, no path), leaves
        no truncated file in inbox/ for cx-minutes to read, never removes a file it did not make, and a retry that fits is saved under the
        same name, not 'name (2)'. A name of 300 characters says the name is too long."""
        inbox = self.vault / "inbox"
        inbox.mkdir(exist_ok=True)
        (inbox / "kept.vtt").write_bytes(b"WEBVTT\nkept\n")
        start = self.inbox()
        code, res = self.upload("big.vtt", b"x" * 8_000_000)
        self.assertEqual((code, res.get("ok")), (500, False), res)
        self.assertEqual(res.get("message"), "That file couldn't be saved. Try again.")
        for word in ("Errno", "OSError", str(self.vault), "/"):
            self.assertNotIn(word, res.get("message", ""))
        self.assertEqual(self.inbox(), start, "no partial file was left")
        code, res = self.upload("kept.vtt", b"y" * 8_000_000)           # a name that is taken: the failed write must not remove the other file
        self.assertEqual((code, res.get("ok")), (500, False), res)
        self.assertEqual(self.inbox(), start)
        self.assertEqual((inbox / "kept.vtt").read_bytes(), b"WEBVTT\nkept\n", "the file it did not make is untouched")
        code, res = self.upload("big.vtt", b"WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n<v A>fits</v>\n")
        self.assertEqual((code, res.get("ok"), res.get("name")), (200, True, "big.vtt"), "a retry that fits is saved under the same name")
        code, res = self.upload("a" * 300 + ".txt", b"hello")
        self.assertEqual((code, res.get("ok")), (400, False), res)
        self.assertEqual(res.get("message"), "The file name is too long. Rename it and add it again.")
        self.assertNotIn("big (2).vtt", self.inbox())
        self.note(9, "a write that failed part-way left nothing in inbox/; the retry kept the name; plain words, no path")


# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# 4, 5  #183: Draft email into Outlook
# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

CREATE = "mcp__claude_ai_Microsoft_365__outlook_create_draft"
M365 = "mcp__claude_ai_Microsoft_365__"
# A stand-in `claude` for the draft run: it plays what Claude Code does with the run's own PreToolUse hook (--settings): the hook is
# asked first, the allow list or the hook's allow decision lets the tool through, and otherwise headless default-deny refuses it. It
# keeps its arguments and counts the drafts it "made". Never a real model, never Microsoft 365. Modes (its .mode file): made, inject
# (a Bcc added by injected text), twice (a second create), nodecision (the hook says nothing), nohook (no --settings: no hook runs),
# crash (the hook cannot run), refused (the tool answers an error).
FAKE = r'''#!/usr/bin/env python3
import json, os, subprocess, sys
args = sys.argv[1:]
here = os.path.abspath(__file__)
open(here + ".argv", "a", encoding="utf-8").write(json.dumps(args) + "\n")
p = args[args.index("--") + 1]
mode = open(here + ".mode").read().strip() if os.path.exists(here + ".mode") else "made"
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init"})
if "access check" in p:
    out({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "a1", "name": "mcp__claude_ai_Microsoft_365__get_granted_scopes", "input": {}}]}})
    out({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "a1", "content": json.dumps(["User.Read", "Mail.Read"])}]}})
else:
    mark = "these arguments, copied byte for byte, the body unchanged: "
    start = p.index(mark) + len(mark)
    a = json.loads(p[start:p.index("\nThen reply")])
    if mode == "inject":
        a = dict(a, bcc=["x@example.com"])
    hook = None
    if "--settings" in args and mode != "nohook":
        hook = json.loads(args[args.index("--settings") + 1])["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        if mode == "crash":
            hook = hook.replace("draft_delivery.py hook", "draft_delivery.py hook-that-does-not-exist", 1)
    def call(i, name, inp):
        out({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": i, "name": name, "input": inp}]}})
        h = subprocess.run(hook, shell=True, input=json.dumps({"tool_name": name, "tool_input": inp}), capture_output=True, text=True) if hook else None
        if h is not None and mode == "nodecision":
            h.stdout = ""
        if h is not None and h.returncode == 2:
            return {"type": "tool_result", "tool_use_id": i, "is_error": True, "content": h.stderr}
        allow = name in args[args.index("--allowedTools") + 1].split(",")
        if not allow and h is not None and h.returncode == 0 and h.stdout.strip():
            try:
                allow = json.loads(h.stdout)["hookSpecificOutput"]["permissionDecision"] == "allow"
            except (ValueError, KeyError, TypeError):
                allow = False
        if not allow:
            return {"type": "tool_result", "tool_use_id": i, "is_error": True, "content": "permission denied"}
        open(here + ".made", "a").write("1\n")
        if mode == "refused":
            return {"type": "tool_result", "tool_use_id": i, "is_error": True, "content": "ErrorAccessDenied: Access is denied."}
        return {"type": "tool_result", "tool_use_id": i, "content": json.dumps({"id": "AAMk1", "webLink": "https://outlook.office365.com/owa/?ItemID=AAMk1"})}
    res = [call("t1", "%s", a)] + ([call("t2", "%s", a)] if mode == "twice" else [])
    out({"type": "user", "message": {"content": res}})
out({"type": "result", "result": "{\"ok\": true}"})
''' % (CREATE, CREATE)
HTML = '<div style="color:#1a1a1a;"><p>Hi Sara,</p><table><tbody><tr><td>FAL-A-001</td></tr></tbody></table></div>'


class Draft262(Engine262):
    """Checks 4 and 5. A vault and a live server whose Claude is the stand-in above."""
    with_server = True

    @classmethod
    def prepare(cls):
        cls.claude = cls.vault / "fake_claude_draft.py"
        cls.claude.write_text(FAKE, encoding="utf-8")
        cls.claude.chmod(0o755)

    def mode(self, m):
        Path(str(self.claude) + ".mode").write_text(m)

    def argv(self):
        """Every run the stand-in was started for (the server starts it for other jobs too), as its argument lists."""
        p = Path(str(self.claude) + ".argv")
        return [json.loads(ln) for ln in p.read_text().splitlines()] if p.exists() else []

    def draft_runs(self):
        """The runs that were asked to create a draft (their prompt carries the arguments to copy)."""
        return [a for a in self.argv() if "--" in a and "these arguments, copied byte for byte" in a[a.index("--") + 1]]

    def access_runs(self):
        return [a for a in self.argv() if "--" in a and "access check" in a[a.index("--") + 1]]

    def made(self):
        p = Path(str(self.claude) + ".made")
        return len(p.read_text().splitlines()) if p.exists() else 0

    def record(self, name):
        p = self.staging(name)
        return p.read_text(encoding="utf-8") if p.exists() else ""

    def body(self, **over):
        item = self.sql("SELECT id FROM actions WHERE status = 'Open' ORDER BY id LIMIT 1")[0]["id"]
        return {"action": "create", "to": "sara.khan@example.com", "subject": f"{item} · a quick reminder", "html": HTML, "ids": [item],
                "mode": "chase", "name": "Sara Khan", **over}

    def nothing_made(self, res, before_made, before_chases, before_drafted, why):
        self.assertFalse(res.get("ok"), f"{why}: reported success: {res}")
        self.assertEqual(self.made(), before_made, f"{why}: a draft was made")
        self.assertEqual(self.record("chases.json"), before_chases, f"{why}: a chase was recorded")
        self.assertEqual(self.record("drafted.json"), before_drafted, f"{why}: a draft was recorded")

    @needs("draft")
    def test_c04_draft_in_outlook_fails_closed_when_the_hook_is_missing_crashes_says_nothing_or_sees_an_injection(self):
        """4. (#183) With Draft email in Outlook on and Claude stood in for, the draft is made only through the run's own hook, once, with
        exactly the arguments asked for. With no hook, a hook that crashes, a hook that gives no decision, an injected Bcc, or a second
        create, nothing is made (or, for a second create, only the one) and nothing is recorded; the run's allow list is ToolSearch alone,
        the send, update and delete tools are denied, and the request file the hook read is removed afterwards. No Microsoft 365 call is made."""
        was = self.set_setting("draft_email", "outlook_drafts", True)
        try:
            self.mode("made")                                                 # the genuine draft
            made = self.made()
            code, res = self.post("/api/email/draft", self.body())
            self.assertEqual(code, 200, res)
            self.assertTrue(res.get("ok"), res)
            self.assertEqual(self.made(), made + 1)
            self.assertIn("outlook.office365.com", res.get("web_link", ""))
            args = self.draft_runs()[-1]
            self.assertEqual(args[args.index("--allowedTools") + 1].split(","), ["ToolSearch"], "the create tool is allowed by the hook alone")
            denied = args[args.index("--disallowedTools") + 1].split(",")
            self.assertNotIn(CREATE, denied)
            for tool in ("outlook_send_draft", "outlook_send_mail", "outlook_update_draft", "outlook_delete_draft", "outlook_email_search"):
                self.assertIn(M365 + tool, denied, tool)
            hook = json.loads(args[args.index("--settings") + 1])["hooks"]["PreToolUse"][0]
            self.assertEqual(hook["matcher"], "*")
            request_file = hook["hooks"][0]["command"].split()[-1].strip("'\"")
            self.assertFalse(Path(request_file).exists(), "the request file is removed when the run ends")
            self.assertTrue(self.record("chases.json"))

            for mode, why in (("nohook", "no hook"), ("crash", "a hook that crashes"), ("nodecision", "a hook that gives no decision"),
                              ("inject", "an injected Bcc")):
                with self.subTest(why):
                    self.mode(mode)
                    before = (self.made(), self.record("chases.json"), self.record("drafted.json"))
                    code, res = self.post("/api/email/draft", self.body())
                    self.nothing_made(res, *before, why)
                    if mode == "inject":
                        self.assertIn("nothing was made", res.get("reason", ""))
                        self.assertFalse(res.get("made"))
            with self.subTest("a second create"):
                self.mode("twice")
                before = self.made()
                code, res = self.post("/api/email/draft", self.body())
                self.assertFalse(res.get("ok"), res)
                self.assertEqual(self.made(), before + 1, "one draft only; the second was refused before it ran")
                self.assertTrue(res.get("made"))
                self.assertIn("delete it unsent", res.get("reason", ""))
            with self.subTest("a refusal from Outlook"):
                self.mode("refused")
                before = (self.made(), self.record("chases.json"), self.record("drafted.json"))
                code, res = self.post("/api/email/draft", self.body())
                self.assertFalse(res.get("ok"))
                self.assertEqual((self.record("chases.json"), self.record("drafted.json")), before[1:], "a refusal records nothing")
            with self.subTest("the access check"):
                self.mode("made")
                code, res = self.post("/api/email/outlook-access", {})
                self.assertEqual(code, 200, res)
                access = self.access_runs()[-1]
                self.assertNotIn("--settings", access, "the access run has no write tool and no hook")
                self.assertEqual(access[access.index("--allowedTools") + 1].split(","), [M365 + "get_granted_scopes", "ToolSearch"])
            with self.subTest("no token"):
                self.assertEqual(self.post("/api/email/draft", self.body(), token=False)[0], 403)
        finally:
            self.set_setting("draft_email", "outlook_drafts", False if was == "__absent__" else was)
        self.note(4, "genuine draft made once through the hook; no hook, a crashing hook, no decision, an injected Bcc and a second create left "
                     "nothing (or one) made and nothing recorded; the real draft in Outlook is live only")

    @needs("draft")
    def test_c05_draft_in_outlook_is_off_by_default_and_while_off_no_run_starts(self):
        """5. (#183) A new vault has Draft email in Outlook off (settings-defaults and the effective setting); a draft request while it is
        off is refused in words before any run starts (the stand-in is never called), and nothing is recorded."""
        defaults = json.loads((self.vault / "system/templates/settings-defaults.json").read_text(encoding="utf-8"))
        self.assertIs(defaults["draft_email"]["outlook_drafts"], False)
        self.assertIs(self.py("import paths\nprint(json.dumps(paths.load_settings()['draft_email']['outlook_drafts']))"), False,
                      "the vault's effective setting is off")
        n, made = len(self.draft_runs()), self.made()
        before = (self.record("chases.json"), self.record("drafted.json"))
        code, res = self.post("/api/email/draft", self.body())
        self.assertFalse(res.get("ok"), res)
        self.assertIn("off in Settings", res.get("reason", ""))
        self.assertEqual(len(self.draft_runs()), n, "no run started")
        self.assertEqual(self.made(), made)
        self.assertEqual((self.record("chases.json"), self.record("drafted.json")), before)
        code, res = self.post("/api/email/draft", self.body(), token=False)
        self.assertEqual(code, 403, "and without the page's token it is refused before anything")
        self.assertEqual(len(self.draft_runs()), n)
        self.note(5, "off in settings-defaults and in the new vault; a create is refused in words before any run; nothing recorded")


# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# 3, 6  in the browser
# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

VIP_WORD = re.compile(r"\bVIPs?\b", re.I)


class Follow262(HandcheckCase):
    """Check 3. Own vault: an alert from a followed person is recorded with the check's own command (sweep.py vip record)."""
    own_vault = True
    CONV = "19:hc262-follow@thread.v2"
    RASHID = "Rashid Al Suwaidi <rashid@northgate.example>"

    def conversation(self):
        day = (self.now or "")[:10]
        due = (date.fromisoformat(day) + timedelta(days=7)).isoformat()
        return {"kind": "teams", "conversation": self.CONV, "title": "Falcon go-live", "from": self.RASHID,
                "people": [self.RASHID, "Lena Fischer"], "last": f"{day} 08:40", "link": "https://teams.microsoft.com/l/chat/hc262",
                "sensitivity": "normal", "attachments": [],
                "items": [{"type": "action", "text": "Take the platform from production to live", "owner": "Rashid Al Suwaidi", "due": due}],
                "summary": "Rashid asks for the go-live date to be confirmed.", "messages": [
                    {"id": "m1", "from": self.RASHID, "at": f"{day} 08:40", "text": "HC262 MESSAGE TEXT NEVER KEPT"}]}

    @needs("follow")
    def test_c03_follow_flag_is_shown_in_the_app_and_the_word_vip_never_is(self):
        """3. (follow) A person ticked Follow in the people register (or in the older VIP column, still read) is alerted when they write; the
        alert is on Today. Nowhere the app shows text — Today, Work, Intake, Files, Activity, Projects, People, Help, Settings, the
        shipped Help and the register template — does the word VIP appear; the app says Follow. The command line's own lines say 'follow'."""
        b = self.b
        code, out = hcbase.vip_found(self.vault, [self.conversation()], f"{(self.now or '')[:10]} 08:50")
        self.assertEqual(code, 0, out[-500:])
        self.assertFalse(VIP_WORD.search(out), f"a line printed by the engine says VIP: {out[-300:]}")
        self.assertRegex(out, r"(?i)follow")
        self.assertTrue((self.vault / "system/staging/vip.json").is_file(), "nothing was alerted: the register's Follow column is not read")
        state = json.loads((self.vault / "system/staging/vip.json").read_text(encoding="utf-8"))
        self.assertTrue(any(a.get("conv") == self.CONV for a in state["alerts"]), "the followed person's message was alerted")
        self.assertNotIn("HC262 MESSAGE TEXT", json.dumps(state), "message text is never kept")
        followed = self.py_json("import propose\nprint(json.dumps([[p['name'], p['kind']] for p in propose.vip_people()]))")
        self.assertIn("Rashid Al Suwaidi", [n for n, _ in followed], "the register's Follow column makes him a followed person")
        self.assertEqual(self.py_json("import propose\nprint(json.dumps([propose.person_vip({'extra': {'Follow': 'yes'}}), propose.person_vip({'extra': {'VIP': 'yes'}}), "
                                      "propose.person_vip({'extra': {'Follow': ''}})]))"), ["yes", "yes", ""], "Follow is read, the older VIP column too")

        b.reload("typeof go==='function' && LIVE")
        b.eval("vipPoll().then(()=>{ go('today'); renderToday(); return true; })")
        shown = {}
        for name in ("today", "work", "intake-review", "files", "activity", "projects", "people", "help", "settings-essentials", "settings-advanced"):
            self.screen(name)
            b.pump(0.4)
            shown[name] = b.eval("document.body.innerText")
        for tab in ("start", "howto", "reference", "whatsnew"):                  # Help is four tabs; the screen opens on the first
            self.screen("help")
            b.eval(f"helpGo({tab!r}); true")
            b.pump(0.4)
            shown[f"help ({tab})"] = b.eval("document.getElementById('helpPane').innerText")
            self.assertGreater(len(shown[f"help ({tab})"]), 500, f"Help's {tab} tab is drawn")
        for name, text in shown.items():
            with self.subTest(screen=name):
                self.assertEqual(VIP_WORD.findall(text), [], f"{name} says VIP: {self.around(text)}")
        self.assertRegex(shown["today"], r"Falcon go-live", "the followed person's conversation is on Today")
        for rel in ("system/templates/help.md", "system/templates/people-register-template.md"):
            text = (self.vault / rel).read_text(encoding="utf-8")
            left = [ln for ln in text.splitlines() if VIP_WORD.search(ln)]
            self.assertTrue(len(left) <= 1 and all("older" in ln for ln in left), f"{rel}: {left[:2]}")
        self.assertEqual(b.errors, [], "no page errors")
        self.note(3, f"{len(shown)} screens read: no VIP; alert recorded with its lines saying follow; Follow and the older VIP column both read")

    @staticmethod
    def around(text):
        m = VIP_WORD.search(text)
        return text[max(0, m.start() - 40):m.end() + 40].replace("\n", " ") if m else ""

    def py_json(self, code):
        r = subprocess.run([sys.executable, "-I", "-c", "import sys, json\nsys.path.insert(0, 'system/scripts')\n" + code], cwd=self.vault,
                           capture_output=True, text=True, env={**os.environ, "CREAITE_NOW": self.now or ""})
        self.assertEqual(r.returncode, 0, r.stderr[-400:])
        return json.loads(r.stdout.strip().splitlines()[-1])


class Today262(HandcheckCase):
    """Check 6. Own vault; the page's data is emptied and refilled in place, so Needs attention goes and comes with no reload."""
    own_vault = True

    STATE = """(()=>({hidden:document.getElementById('attnSec').hidden,
      shown:document.getElementById('attnSec').getBoundingClientRect().height>0,
      heading:[...document.querySelectorAll('#v-today h2')].filter(e=>e.getClientRects().length&&/Needs attention/.test(e.textContent)).length,
      rows:document.querySelectorAll('#attnList>li').length, none:document.querySelectorAll('#attnList .none').length,
      filler:/Nothing needs your attention/.test(document.getElementById('v-today').innerText),
      named:[...document.querySelectorAll('#v-today *')].filter(e=>e.getClientRects().length&&e.children.length===0&&/Needs attention/.test(e.textContent)).length,
      count:document.getElementById('nAttn').textContent, mark:window.__hc262}))()"""

    @needs("today")
    def test_c06_today_hides_needs_attention_when_empty_and_shows_it_live_with_an_item(self):
        """6. (#322) On Today, with nothing under Needs attention the heading, its count and its list are not drawn at all (no empty section, no
        'Nothing needs your attention' line, nothing left that names it); with one item the heading is back with its count; when it is gone
        again so is the heading; and after the data is read again from the server it is back, all on the same page, with no reload."""
        b = self.b
        self.screen("today")
        b.eval("window.__hc262 = 1; true")
        full = b.eval(self.STATE)
        self.assertGreaterEqual(full["rows"], 2, "the demo's Today has things that need attention to begin with")
        self.assertTrue(full["shown"] and full["heading"] == 1 and not full["hidden"], full)
        before = b.eval("[...document.querySelectorAll('#v-today h2')].filter(e=>e.getClientRects().length).map(e=>e.textContent.trim().replace(/\\s+/g,' '))")

        def empty():
            b.eval("window.__keep = {A: A.slice(), R: R.slice(), rem: S.remindersOn}; A.length = 0; R.length = 0; S.remindersOn = false; renderToday(); true")
            b.pump(0.3)
            return b.eval(self.STATE)

        gone = empty()
        self.assertEqual((gone["hidden"], gone["shown"], gone["heading"], gone["rows"], gone["none"], gone["filler"], gone["named"]),
                         (True, False, 0, 0, 0, False, 0), f"Needs attention is not drawn when empty: {gone}")
        self.assertEqual(gone["mark"], 1, "same page")
        after = b.eval("[...document.querySelectorAll('#v-today h2')].filter(e=>e.getClientRects().length).map(e=>e.textContent.trim().replace(/\\s+/g,' '))")
        self.assertEqual([h for h in before if not h.startswith("Needs attention")], after, "the other headings are all still there, in order")
        overlap = b.eval("""(()=>{ const s=[...document.querySelectorAll('#v-today section.tsec')].filter(e=>e.getClientRects().length).map(e=>e.getBoundingClientRect());
          let bad=0; for (let i=1;i<s.length;i++) if (s[i].top < s[i-1].bottom-1) bad++; return bad; })()""")
        self.assertEqual(overlap, 0, "the sections around it keep their order and do not overlap")
        no_landmark = b.eval("[...document.querySelectorAll('#v-today [aria-labelledby=hAttn]')].filter(e=>e.getClientRects().length).length")
        self.assertEqual(no_landmark, 0, "no empty landmark is left for a screen reader")

        # one item: a work item with no owner (the Work gaps line is a Needs attention row)
        b.eval("""(()=>{ const x = window.__keep.A.find(a => (a.st==='Open'||a.st==='Delayed') && (!a.o || a.o==='TBC' || !a.due));
          window.__one = x ? Object.assign({}, x, {o: 'TBC', due: ''}) : null; return !!x; })()""")
        self.assertTrue(b.eval("!!window.__one"), "the demo has an open work item to use as the one item")
        b.eval("A.push(window.__one); renderToday(); true")
        b.pump(0.3)
        one = b.eval(self.STATE)
        self.assertEqual((one["hidden"], one["shown"], one["heading"], one["rows"], one["count"]), (False, True, 1, 1, "1"), f"one item brings the heading back: {one}")
        self.assertEqual(one["mark"], 1)
        b.eval("A.length = 0; renderToday(); true")
        b.pump(0.3)
        again = b.eval(self.STATE)
        self.assertEqual((again["hidden"], again["shown"], again["heading"], again["filler"]), (True, False, 0, False), f"and it is gone again: {again}")

        # the data read again from the server: back, on the same page
        b.eval("S.remindersOn = window.__keep.rem; window.__done = false; reloadData().then(()=>{ renderToday(); window.__done = true; })")
        b.wait("window.__done === true", 30)
        back = b.eval(self.STATE)
        self.assertEqual((back["hidden"], back["shown"], back["heading"]), (False, True, 1), f"read again, it is back: {back}")
        self.assertGreaterEqual(back["rows"], 2)
        self.assertEqual(back["mark"], 1, "all of it without a reload")
        self.assertEqual(b.errors, [], "no page errors")
        self.note(6, f"{full['rows']} rows shown; emptied: section, heading and filler gone; one item: back with count 1; emptied; read again: back; no reload")


# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# 10  #321: the New note drawer can be widened
# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

# A page whose storage throws, as in a private window or with site data blocked: the accessor and the methods all throw. Run on every
# new document (Page.addScriptToEvaluateOnNewDocument), so it is in place before the page's own scripts.
STORAGE_THROWS = """(()=>{ const boom=()=>{ throw new DOMException('storage is blocked','SecurityError'); };
  try{ Object.defineProperty(window,'localStorage',{configurable:true,get:boom}); }catch(e){}
  try{ for(const m of ['getItem','setItem','removeItem']) Storage.prototype[m]=boom; }catch(e){} })()"""
WIDTH_KEY = "creaite-capture-width"


class Drawer262(HandcheckCase):
    """Check 10. Own vault, the live server and Chrome: the New note drawer is opened as a person opens it (⌘⇧N) and widened with the keys
    and the mouse. Page only; nothing here needs the guarded chain."""
    own_vault = True
    DEFAULT = 440

    STATE = """(()=>{ const d=document.getElementById('capDrawer'), h=document.getElementById('capResize'), r=d.getBoundingClientRect();
      const hr=h&&h.getBoundingClientRect(), x=document.getElementById('capWidthReset'), done=document.getElementById('capDone');
      let kept=null; try{ kept=localStorage.getItem(%s); }catch(e){ kept='THROWS'; }
      const dr=done&&done.getBoundingClientRect();
      return {open:!d.hidden, w:Math.round(r.width), left:Math.round(r.left), right:Math.round(r.right), iw:innerWidth,
        sw:document.scrollingElement.scrollWidth, hx:hr&&Math.round(hr.left+hr.width/2), hy:hr&&Math.round(hr.top+hr.height/2),
        role:h&&h.getAttribute('role'), tab:h&&h.tabIndex, name:h&&h.getAttribute('aria-label'), orient:h&&h.getAttribute('aria-orientation'),
        min:h&&Number(h.getAttribute('aria-valuemin')), max:h&&Number(h.getAttribute('aria-valuemax')), now:h&&Number(h.getAttribute('aria-valuenow')),
        kept:kept, reset:!!x&&x.getClientRects().length>0, resetText:x?x.textContent.trim():null, focus:!!h&&document.activeElement===h,
        doneIn:!!dr&&dr.width>0&&dr.left>=0&&dr.right<=innerWidth}; })()""" % json.dumps(WIDTH_KEY)

    def state(self):
        return self.b.eval(self.STATE)

    def open_drawer(self):
        """⌘⇧N (Ctrl+Shift+N off a Mac), as a person opens it, from wherever the page is."""
        b = self.b
        b.eval("document.body.focus(); true")
        b.key("N", (4 if b.is_mac() else 2) | 8)
        b.wait("(()=>{ const d=document.getElementById('capDrawer'); return !!d && !d.hidden && !!document.getElementById('capResize'); })()", 15)
        b.pump(0.3)
        return self.state()

    def press(self, key, modifiers=0):
        self.b.key(key, modifiers)
        return self.state()

    def pointer_drag(self, to_x, steps=6, release=True):
        """A real mouse press on the handle, a move to `to_x` (clientX) and the release: pointer events, hit-tested."""
        b = self.b
        s = self.state()
        x0, y0 = s["hx"], s["hy"]
        top = b.eval("(()=>{ const e=document.elementFromPoint(%d,%d); return e&&e.id; })()" % (x0, y0))
        self.assertEqual(top, "capResize", "the handle is what the pointer meets on the drawer's edge")
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=x0, y=y0, button="none")
        b.call("Input.dispatchMouseEvent", type="mousePressed", x=x0, y=y0, button="left", buttons=1, clickCount=1)
        for i in range(1, steps + 1):
            b.call("Input.dispatchMouseEvent", type="mouseMoved", x=x0 + (to_x - x0) * i / steps, y=y0, button="left", buttons=1)
            b.pump(0.01)
        if release:
            b.call("Input.dispatchMouseEvent", type="mouseReleased", x=to_x, y=y0, button="left", buttons=0, clickCount=1)
        b.pump(0.15)
        return self.state()

    def writes_since(self, mark):
        """The requests the page has made since `mark` (an index into the browser's events) that could change something on the server."""
        self.b.pump(0.3)
        return [(e["params"]["request"]["method"], e["params"]["request"]["url"]) for e in self.b.events[mark:]
                if e.get("method") == "Network.requestWillBeSent" and e["params"]["request"]["method"] not in ("GET", "HEAD", "OPTIONS")]

    def boot(self, why):
        try:
            self.b.reload("typeof go==='function' && LIVE", timeout=30)
        except TimeoutError as e:
            self.fail(f"{why}: the page did not start ({str(e)[:200]})")

    def test_c10_new_note_drawer_can_be_widened_remembered_and_reset(self):
        """10. (#321) The New note drawer opens at its default width (440 px). Its left edge is a separator handle (role separator, an
        accessible name, focusable) that widens it with the arrow keys (Shift for bigger steps, End for the page width, Home or Enter back
        to the default) and with a mouse drag, up to the page width and never beyond it, at 1400 px and at 900 px. The width is remembered
        for this viewer only: a reload keeps it, and a page whose storage throws still starts, opens the drawer and widens it. The Reset
        width button (shown only when the width is not the default) and a double-click on the handle return it to the default and forget
        the remembered width. A width
        change makes no request that writes (no POST), and changes nothing in the vault's settings."""
        b = self.b
        W = self.DEFAULT
        settings = self.vault / "system/config/settings.json"
        settings0 = settings.read_bytes()
        writes = []

        # the default
        s = self.open_drawer()
        self.assertTrue(s["open"], s)
        self.assertEqual((s["w"], s["right"], s["left"]), (W, s["iw"], s["iw"] - W), f"the drawer opens at its default width: {s}")
        self.assertIsNone(s["kept"], "nothing is remembered yet")
        self.assertFalse(s["reset"], "Reset width is not offered at the default")
        self.assertEqual((s["role"], s["tab"], s["orient"]), ("separator", 0, "vertical"), s)
        self.assertTrue((s["name"] or "").strip(), "the handle has an accessible name")
        self.assertEqual((s["min"], s["now"], s["max"]), (W, W, s["iw"]), "the handle says its range and where it is")
        self.assertTrue(abs(s["hx"] - (s["iw"] - W)) <= 1, f"the handle sits on the drawer's left edge: {s}")
        b.eval("document.getElementById('capResize').focus(); true")
        self.assertTrue(self.state()["focus"], "the handle takes keyboard focus")
        iw = s["iw"]

        # the keys
        mark = len(b.events)
        s = self.press("ArrowLeft")
        self.assertEqual((s["w"], s["now"], s["kept"]), (W + 24, W + 24, str(W + 24)), f"ArrowLeft widens by one step and remembers it: {s}")
        self.assertEqual((s["left"], s["right"]), (iw - W - 24, iw))
        self.assertTrue(s["reset"] and s["resetText"] == "Reset width", f"Reset width is offered once the width is not the default: {s}")
        self.assertTrue(abs(s["hx"] - s["left"]) <= 1, "the handle moved with the edge")
        self.assertTrue(s["focus"], "and keeps focus")
        s = self.press("ArrowLeft", 8)
        self.assertEqual((s["w"], s["kept"]), (W + 24 + 96, str(W + 120)), f"Shift+ArrowLeft takes four steps: {s}")
        s = self.press("ArrowRight")
        self.assertEqual((s["w"], s["now"]), (W + 96, W + 96), f"ArrowRight narrows by one step: {s}")
        s = self.press("End")
        self.assertEqual((s["w"], s["now"], s["kept"], s["left"]), (iw, iw, str(iw), 0), f"End goes to the page width: {s}")
        self.assertLessEqual(s["sw"], iw, "no sideways scroll at the full width")
        for _ in range(2):
            s = self.press("ArrowLeft", 8)
        self.assertEqual((s["w"], s["now"], s["kept"]), (iw, iw, str(iw)), f"past the page width the key goes no further: {s}")
        s = self.press("Home")
        self.assertEqual((s["w"], s["kept"], s["reset"]), (W, None, False), f"Home is the default again and forgets the remembered width: {s}")
        s = self.press("ArrowRight")
        self.assertEqual((s["w"], s["now"]), (W, W), f"and it is not narrower than the default: {s}")
        s = self.press("ArrowLeft")
        s = self.press("Enter")
        self.assertEqual((s["w"], s["kept"]), (W, None), f"Enter is the default too: {s}")
        writes += self.writes_since(mark)

        # the mouse
        mark = len(b.events)
        s = self.pointer_drag(iw - 700)
        self.assertEqual((s["w"], s["now"], s["kept"]), (700, 700, "700"), f"a drag to 700 px from the right edge: {s}")
        self.assertTrue(abs(s["hx"] - (iw - 700)) <= 1)
        s = self.pointer_drag(0)
        self.assertEqual((s["w"], s["kept"], s["left"]), (iw, str(iw), 0), f"a drag to the left edge of the page is the page width: {s}")
        self.assertLessEqual(s["sw"], iw)
        s = self.pointer_drag(-300)
        self.assertEqual((s["w"], s["now"], s["kept"]), (iw, iw, str(iw)), f"a drag beyond the page is held at the page width, in the page and in what is kept: {s}")
        self.assertLessEqual(s["sw"], iw)
        s = self.pointer_drag(iw - 100)
        self.assertEqual(s["w"], W, f"a drag narrower than the default stops at the default: {s}")
        s = self.pointer_drag(iw - 650)
        self.assertEqual((s["w"], s["kept"]), (650, "650"), s)
        writes += self.writes_since(mark)

        # remembered for this viewer: a reload keeps it
        self.boot("reload with a remembered width")
        s = self.open_drawer()
        self.assertEqual((s["w"], s["kept"], s["reset"]), (650, "650", True), f"a reload keeps the width: {s}")

        # Reset width: a real click
        mark = len(b.events)
        b.click("#capWidthReset")
        b.pump(0.2)
        s = self.state()
        self.assertEqual((s["w"], s["kept"], s["reset"]), (W, None, False), f"Reset width returns to the default, forgets it and goes away: {s}")
        writes += self.writes_since(mark)
        self.boot("reload after Reset width")
        s = self.open_drawer()
        self.assertEqual((s["w"], s["kept"]), (W, None), f"and a reload stays at the default: {s}")

        # a double-click on the handle is the same
        mark = len(b.events)
        b.eval("document.getElementById('capResize').focus(); true")
        self.press("ArrowLeft", 8)
        self.assertEqual(self.state()["w"], W + 96)
        b.click("#capResize", count=2)
        b.pump(0.2)
        s = self.state()
        self.assertEqual((s["w"], s["kept"]), (W, None), f"a double-click on the handle puts the width back: {s}")
        writes += self.writes_since(mark)

        # storage that throws: the page starts, the drawer opens at the default and still widens, and Reset works
        errors0 = len(b.errors)
        ident = b.call("Page.addScriptToEvaluateOnNewDocument", source=STORAGE_THROWS)["identifier"]
        try:
            self.boot("storage that throws")
            self.assertTrue(b.eval("(()=>{ try{ localStorage.getItem('x'); return false; }catch(e){ return true; } })()"), "the stand-in storage throws")
            s = self.open_drawer()
            self.assertEqual(s["w"], W, f"with unreadable storage the drawer opens at the default: {s}")
            mark = len(b.events)
            b.eval("document.getElementById('capResize').focus(); true")
            s = self.press("ArrowLeft")
            self.assertEqual((s["w"], s["now"]), (W + 24, W + 24), f"and widens with the keys: {s}")
            s = self.pointer_drag(iw - 600)
            self.assertEqual(s["w"], 600, f"and with the mouse: {s}")
            b.click("#capWidthReset")
            b.pump(0.2)
            self.assertEqual(self.state()["w"], W, "and Reset width works")
            writes += self.writes_since(mark)
            self.assertEqual(b.errors[errors0:], [], "no page error from storage that throws")
        finally:
            b.call("Page.removeScriptToEvaluateOnNewDocument", identifier=ident)

        # 900 px: the page width is the limit
        self.boot("back to working storage")
        b.resize(900, 800)
        s = self.open_drawer()
        self.assertEqual((s["iw"], s["w"]), (900, W), s)
        mark = len(b.events)
        b.eval("document.getElementById('capResize').focus(); true")
        s = self.press("End")
        self.assertEqual((s["w"], s["now"], s["kept"], s["left"]), (900, 900, "900", 0), f"at 900 px End is 900 px: {s}")
        self.assertLessEqual(s["sw"], 900)
        s = self.pointer_drag(-200)
        self.assertEqual((s["w"], s["kept"]), (900, "900"), f"and a drag past the edge is held at 900 px: {s}")
        writes += self.writes_since(mark)

        # nothing was written: no request that writes, and the settings file is as it was
        self.assertEqual(writes, [], f"a width change made requests that write: {writes}")
        self.assertEqual(settings.read_bytes(), settings0, "the settings file is untouched")
        # the watcher itself works: a POST from the page is seen
        mark = len(b.events)
        b.eval("fetch('/api/hc262-width-probe', {method: 'POST', body: '{}'}).then(r => r.status).catch(() => 0)")
        self.assertTrue(any(m == "POST" and u.endswith("/api/hc262-width-probe") for m, u in self.writes_since(mark)), "the watcher sees a POST")
        self.note(10, "440 default; keys (step 24, Shift 96, End, Home, Enter) and mouse drag held between the default and the page width at "
                      "1400 and 900 px; kept for a reload (650) and forgotten by Reset width and a double-click; unreadable storage "
                      "starts the page and widens; 0 requests that write")


# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

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
