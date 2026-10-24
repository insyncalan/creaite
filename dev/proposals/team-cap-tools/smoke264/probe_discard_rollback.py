"""Discard and its Undo for held minutes, and the all-or-nothing rollback when recording an item's history fails (2.6.4).

  python3 -I probe_discard_rollback.py NEW_ZIP BASE_ZIP WORK_DIR [--label 2.6.4] [--control] [--keep]

Scratch vault (fictional data), live server, headless Chrome (the Undo route is called from the open page with fetch, so it
carries the browser's own same-origin marks; the on-screen buttons are not clicked).
  DU  Minutes whose transcript has gone are "held". Discard sets them aside and writes nothing to the tracker; Undo puts the
      staged file back byte for byte (marker gone, the set-aside copy gone) and the minutes are back in Review; a second Undo
      is refused; Undo is refused when a suggestion of that name is already waiting; Undo refuses a file in discarded/ that
      Discard never set aside (a planted file); the route answers only the open page's own call (a bare POST with the token
      gets HTTP 403).
  ER  A trigger makes every insert into item_events fail. `tracker.py apply` then exits 1 ("nothing was written"), the action,
      change_log, item_events and applies counts are unchanged and the proposal is byte-identical; with the fault removed the same
      proposal applies. `tracker.py undo` under the same fault exits 1 ("nothing was changed") and changes nothing; with the
      fault gone it works.
Expected on 2.6.4 (base 2.6.3): all PASS. These are regression checks: they also PASS on the base (--control), because the
behaviour is in 2.6.3 as well; they prove 2.6.4 kept it, not that 2.6.4 added it.
"""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402
from common import rec, action  # noqa: E402


def main():
    a = C.parse(__doc__)
    v = C.V("pDiscard", identity="Sam Reid", calendar=False)
    try:
        v.start()
        stg = v.vault / "system/staging"
        name = v.r.stage_minutes()
        p = stg / name
        for f in (v.vault / "inbox").glob("*.vtt"):
            f.unlink()
        orig = p.read_bytes()
        v.reload_data()
        mfp = v.fingerprint("block_fp", json.loads(orig)["meeting"])
        counts = lambda: (v.db("select count(*) from actions")[0][0], v.db("select count(*) from decisions")[0][0])  # noqa: E731
        t0 = counts()
        c, r = v.pj("/api/review", {"file": name, "ref": "meeting", "decision": "discard", "expect": mfp})
        disc = stg / "discarded" / name
        rec("DU Discard of held minutes sets them aside and writes nothing", c == 200 and isinstance(r, dict) and r.get("ok") is True and disc.exists() and not p.exists() and counts() == t0,
            f"{c} {str(r.get('message') if isinstance(r, dict) else r)[:140]}")
        code, txt = v.page_post("/api/review/restore-discarded", {"file": name})
        rr = json.loads(txt)
        back = p.read_bytes() if p.exists() else b""
        marker_gone = bool(back) and "discarded" not in json.loads(back.decode())
        rec("DU Undo puts the minutes back as they were", rr.get("ok") is True and back == orig and marker_gone and not disc.exists(),
            f"{code} {rr.get('message')!r}; byte-identical {back == orig}; marker gone {marker_gone}; set-aside copy gone {not disc.exists()}")
        code, txt = v.page_post("/api/review/restore-discarded", {"file": name})
        rec("DU a second Undo is refused", json.loads(txt).get("ok") is False, f"{code} {json.loads(txt).get('message')!r}")
        c, o = v.run("review.py", "list", "--json")
        lst = json.loads(o)
        rec("DU the minutes are back in Review", any(x["file"] == name and x["ref"] == "meeting" for x in lst), f"{len(lst)} entries")
        v.pj("/api/review", {"file": name, "ref": "meeting", "decision": "discard", "expect": v.fingerprint("block_fp", json.loads(p.read_text())["meeting"])})
        if disc.exists():
            shutil.copy2(disc, p)
        code, txt = v.page_post("/api/review/restore-discarded", {"file": name})
        rr3 = json.loads(txt)
        rec("DU Undo is refused when a suggestion of that name is already waiting", rr3.get("ok") is False and disc.exists(), f"{code} {rr3.get('message')!r}")
        planted = stg / "discarded" / "proposed-planted.json"
        planted.write_text(json.dumps({"items": [], "discarded": {"name": "proposed-planted.json"}}))
        code, txt = v.page_post("/api/review/restore-discarded", {"file": "proposed-planted.json"})
        rr4 = json.loads(txt)
        rec("DU Undo refuses a planted file that Discard never set aside", rr4.get("ok") is False and not (stg / "proposed-planted.json").exists(), f"{code} {rr4.get('message')!r}")
        c, t = v.post("/api/review/restore-discarded", {"file": name})
        rec("DU the route answers only the open page's own call", c == 403, f"bare POST with the token -> HTTP {c} {t[:90]}")
        for f in stg.glob("proposed-*.json"):
            f.unlink()

        # ---- emit rollback
        p2 = v.stage("2026-10-20-0900-rb", [action(1, "Rollback probe action", decision="approved")])
        d0q = lambda: {t: v.db(f"select count(*) from {t}")[0][0] for t in ("actions", "change_log", "item_events", "applies")}  # noqa: E731
        v.db_write("CREATE TRIGGER boom BEFORE INSERT ON item_events BEGIN SELECT RAISE(ABORT,'boom'); END")
        d0, b0 = d0q(), p2.read_bytes()
        c, o = v.run("tracker.py", "apply")
        rec("ER apply under a failing item_events insert: exit 1, nothing written", c == 1 and "nothing was written" in o and d0q() == d0 and p2.read_bytes() == b0 and not v.db("select 1 from actions where description='Rollback probe action'"),
            f"exit {c}: {o.strip()[-150:]}; counts {d0q()} vs {d0}; proposal byte-identical {p2.read_bytes() == b0}")
        v.db_write("DROP TRIGGER boom")
        c, o = v.run("tracker.py", "apply")
        rec("ER with the fault removed, the same proposal applies", c == 0 and bool(v.db("select 1 from actions where description='Rollback probe action'")), f"exit {c}: {o.strip()[-120:]}")
        d1 = d0q()
        v.db_write("CREATE TRIGGER boom2 BEFORE INSERT ON item_events BEGIN SELECT RAISE(ABORT,'boom'); END")
        c, o = v.run("tracker.py", "undo")
        rec("ER undo under the same fault: exit 1, nothing changed", c == 1 and "nothing was changed" in o and d0q() == d1, f"exit {c}: {o.strip()[-150:]}; counts {d0q()} vs {d1}")
        v.db_write("DROP TRIGGER boom2")
        c, o = v.run("tracker.py", "undo")
        rec("ER with the fault gone, undo works", c == 0 and not v.db("select 1 from actions where description='Rollback probe action'"), f"exit {c}: {o.strip()[-120:]}")
        print("console errors:", v.b.errors[:3])
    finally:
        v.close()
    return C.finish(a)


if __name__ == "__main__":
    C.run(main)
