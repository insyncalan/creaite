"""#345: the row fingerprint (`expect`) is required on every route that decides an item, and a stale page decides nothing.

  python3 -I probe_345_expect.py NEW_ZIP BASE_ZIP WORK_DIR [--label 2.6.4] [--control] [--keep]

Real HTTP with the open page's token against the scratch vault's live server. For each of /api/review/reject,
/api/review/rejected (approve instead), /api/review/repeat, /api/review/retarget, /api/review/assign and
/api/minutes/approve:
  - a request with no `expect`, a malformed one ("not-a-fingerprint", short hex, a number) and a stale one (the item changed in
    the file behind the page) is refused in plain words, the staged file is byte-identical afterwards and the tracker's
    action / RAID / rejected counts are unchanged;
  - a two-row reject with one stale row is all or none;
  - a request with the correct fingerprint works (a control that the refusal is not just a broken route);
  - undo of a reject, a retarget undo and the assign preview (dry_run) need no fingerprint.
Then, through the open Intake page: Approve on an item that changed behind the page is turned away and nothing is decided.
Expected on 2.6.4 (base 2.6.3): all PASS. With --control (the base) the refusal checks FAIL (2.6.3 accepts a missing `expect`).
Wording checked is 2.6.4's; if a later release rewords the three refusals, update M_* below before reading a FAIL as a regression.
Note: the "repeat" control only proves the fingerprint check passes; review.py then says the item is not marked as a repeat
(the staged item here has no real repeat marker).
"""
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402
from common import rec, action  # noqa: E402

M_MISSING = "This page didn't say which item it meant, so nothing was changed. Reload the page and try again."
M_BAD = "Review can't check which item that is, so nothing was changed. Look at the list again."
M_CHANGED = "That item has changed since you looked at it, so nothing was changed. Look at the list again."


def msg_of(r):
    return r.get("message") if isinstance(r, dict) else r


def main():
    a = C.parse(__doc__)
    v = C.V("p345", identity="Sam Reid", calendar=False)
    try:
        v.start()
        stg = v.vault / "system/staging"

        def item_fp(i):
            return v.fingerprint("item_fp", i)

        def block_fp(b):
            return v.fingerprint("block_fp", b)

        def clear():
            for f in stg.glob("proposed-*.json"):
                f.unlink()

        def state(p):
            return p.read_bytes() if p.exists() else None

        def trk():
            return (v.db("select count(*) from actions")[0][0], v.db("select count(*) from raid")[0][0], v.db("select count(*) from rejected")[0][0])

        def body_edit(p, n, key, val):
            if not p.exists():
                return
            d = json.loads(p.read_text())
            for i in d["items"]:
                if i["n"] == n and "values" in i:
                    i["values"][key] = val
            p.write_text(json.dumps(d, indent=2))

        def check_route(label, path, mk_body, p, mutate):
            res = []
            for case, e, words in (("missing", None, M_MISSING), ("malformed", "not-a-fingerprint", M_BAD), ("short-hex", "abc123", M_BAD), ("number", 12345, M_BAD)):
                before, t0 = state(p), trk()
                body = mk_body(e)
                if e is None:
                    body.pop("expect", None)
                c, r = v.pj(path, body)
                ok = isinstance(r, dict) and r.get("ok") is False and msg_of(r) == words and state(p) == before and trk() == t0
                res.append((case, ok, f"{c} {msg_of(r)!r}"))
            if mutate:
                old = item_fp(json.loads(p.read_text())["items"][0]) if p.exists() else "0" * 12
                mutate(p)
                before, t0 = state(p), trk()
                c, r = v.pj(path, mk_body(old))
                ok = isinstance(r, dict) and r.get("ok") is False and msg_of(r) == M_CHANGED and state(p) == before and trk() == t0
                res.append(("stale", ok, f"{c} {msg_of(r)!r}"))
            rec(f"345 {label}: missing/malformed/stale refused, decides nothing", all(x[1] for x in res),
                "; ".join(f"{n}={'ok' if ok else 'FAIL ' + note}" for n, ok, note in res))

        # reject
        clear()
        p = v.stage("2026-10-20-0900-rj", [action(1, "Reject me one"), action(2, "Reject me two")])
        name = p.name
        check_route("reject", "/api/review/reject", lambda e: {"rows": [{"file": name, "ref": 1, "expect": e}], "reason": "other"}, p,
                    lambda p: body_edit(p, 1, "description", "Reject me one (changed)"))
        d = json.loads(p.read_text())
        g1 = item_fp(d["items"][0])
        before = state(p)
        c, r = v.pj("/api/review/reject", {"rows": [{"file": name, "ref": 1, "expect": g1}, {"file": name, "ref": 2, "expect": "0" * 12}], "reason": "other"})
        rec("345 reject all-or-none (one valid, one stale)", isinstance(r, dict) and r.get("ok") is False and msg_of(r) == M_CHANGED and state(p) == before,
            f"{msg_of(r)!r}; file unchanged {state(p) == before}")
        d = json.loads(p.read_text())
        c, r = v.pj("/api/review/reject", {"rows": [{"file": name, "ref": i["n"], "expect": item_fp(i)} for i in d["items"]], "reason": "other"})
        rec("345 reject with correct fingerprints works (control)", c == 200 and isinstance(r, dict) and r.get("ok") is True, f"{c} {msg_of(r)!r}")
        # approve instead (the rejected route)
        d = json.loads(p.read_text())
        rows = [{"file": name, "ref": i["n"]} for i in d["items"]]
        check_route("approve-instead (rejected route)", "/api/review/rejected", lambda e: {"how": "approve", "rows": [dict(rows[0], expect=e)]}, p,
                    lambda p: body_edit(p, 1, "description", "Reject me one (changed again)"))
        d = json.loads(p.read_text())
        c, r = v.pj("/api/review/rejected", {"how": "approve", "rows": [dict(rows[0], expect=item_fp(d["items"][0]))]})
        rec("345 approve-instead with the correct fingerprint works (control)", c == 200 and isinstance(r, dict) and r.get("ok") is True, f"{c} {str(r)[:140]}")
        c, r = v.pj("/api/review/rejected", {"how": "undo", "rows": [dict(rows[1])]})
        rec("345 undo of a reject needs no fingerprint", c == 200 and isinstance(r, dict) and r.get("ok") is True, f"{c} {msg_of(r)!r}")
        # repeat
        clear()
        ex = v.db("select id from actions where project='FAL' and status!='Done' limit 1")
        exid = ex[0][0] if ex else "FAL-A-001"
        p = v.stage("2026-10-20-0910-rp", [action(1, "Repeat candidate", repeats=exid, flags=["repeat"])])
        name = p.name
        check_route("repeat (merge/keep)", "/api/review/repeat", lambda e: {"file": name, "ref": 1, "how": "keep", "expect": e}, p,
                    lambda p: body_edit(p, 1, "description", "Repeat candidate changed"))
        f = item_fp(json.loads(p.read_text())["items"][0])
        c, r = v.pj("/api/review/repeat", {"file": name, "ref": 1, "how": "keep", "expect": f})
        rec("345 repeat with the correct fingerprint passes the check (control)", c == 200 and isinstance(r, dict) and msg_of(r) not in (M_MISSING, M_BAD, M_CHANGED, None), f"{c} {str(r)[:140]}")
        # retarget
        clear()
        p = v.stage("2026-10-20-0920-rt", [action(1, "Retarget candidate")])
        name = p.name
        check_route("retarget (make it an update)", "/api/review/retarget", lambda e: {"file": name, "ref": 1, "id": exid, "expect": e}, p,
                    lambda p: body_edit(p, 1, "description", "Retarget candidate changed"))
        f = item_fp(json.loads(p.read_text())["items"][0])
        c, r = v.pj("/api/review/retarget", {"file": name, "ref": 1, "id": exid, "expect": f})
        rec("345 retarget with the correct fingerprint works (control)", c == 200 and isinstance(r, dict) and r.get("ok") is True, f"{c} {str(r)[:140]}")
        c, r = v.pj("/api/review/retarget", {"file": name, "ref": 1, "undo": True})
        rec("345 retarget undo needs no fingerprint", c == 200 and isinstance(r, dict) and msg_of(r) not in (M_MISSING, M_BAD, M_CHANGED), f"{c} {str(r)[:140]}")
        # assign
        clear()
        p = v.stage("2026-10-20-0930-as", [action(1, "Assign candidate")])
        name = p.name
        other = v.db("select code from projects where code!='FAL' limit 1")[0][0]
        c, r = v.pj("/api/review/assign", {"file": name, "ref": 1, "code": other, "dry_run": True})
        rec("345 assign preview (dry_run) needs no fingerprint", c == 200 and isinstance(r, dict) and r.get("ok") is True, f"{c} {str(r)[:120]}")
        check_route("assign (move to another project)", "/api/review/assign", lambda e: {"file": name, "ref": 1, "code": other, "expect": e}, p,
                    lambda p: body_edit(p, 1, "description", "Assign candidate changed"))
        f = item_fp(json.loads(p.read_text())["items"][0])
        c, r = v.pj("/api/review/assign", {"file": name, "ref": 1, "code": other, "expect": f})
        now = json.loads(p.read_text())["items"][0]["values"]["project"]
        rec("345 assign with the correct fingerprint moves the item (control)", c == 200 and isinstance(r, dict) and r.get("ok") is True and now == other, f"{c}; project now {now}")
        # Approve minutes
        clear()
        mname = v.r.stage_minutes()
        p = stg / mname
        d = json.loads(p.read_text())
        mfp = block_fp(d["meeting"])
        ifps = {str(i["n"]): item_fp(i) for i in d["items"]}
        own = [d["items"][0]["n"]]
        check_route("Approve minutes (minutes fingerprint)", "/api/minutes/approve", lambda e: {"file": mname, "expect": e, "expects": ifps, "own": own, "group": True}, p, None)
        before, t0 = state(p), trk()
        c, r1 = v.pj("/api/minutes/approve", {"file": mname, "expect": mfp, "own": own, "group": True})
        ok1 = isinstance(r1, dict) and r1.get("ok") is False and msg_of(r1) == M_MISSING and state(p) == before and trk() == t0
        bad = dict(ifps)
        bad[str(own[0])] = "0" * 12
        c, r2 = v.pj("/api/minutes/approve", {"file": mname, "expect": mfp, "expects": bad, "own": own, "group": True})
        ok2 = isinstance(r2, dict) and r2.get("ok") is False and msg_of(r2) == M_CHANGED and state(p) == before and trk() == t0
        body_edit(p, own[0], "description", "Changed after the page drew it")
        before = state(p)
        c, r3 = v.pj("/api/minutes/approve", {"file": mname, "expect": block_fp(json.loads(p.read_text())["meeting"]), "expects": ifps, "own": own, "group": True})
        ok3 = isinstance(r3, dict) and r3.get("ok") is False and msg_of(r3) == M_CHANGED and state(p) == before and trk() == t0
        rec("345 Approve minutes with an item missing / wrong / changed behind the page: refused, decides nothing", ok1 and ok2 and ok3, f"missing={ok1}; wrong={ok2}; changed={ok3}")
        d = json.loads(p.read_text())
        c, r4 = v.pj("/api/minutes/approve", {"file": mname, "expect": block_fp(d["meeting"]), "expects": {str(i["n"]): item_fp(i) for i in d["items"]}, "own": own, "group": True})
        rec("345 Approve minutes with the correct fingerprints approves (control)", c == 200 and isinstance(r4, dict) and r4.get("ok") is True, f"{c} {str(r4)[:160]}; actions now {trk()[0]}")

        # the open page: Approve on an item that changed behind it
        clear()
        p = v.stage("2026-10-20-0900-st", [action(1, "Stale page item"), action(2, "Neighbour item")])
        v.reload_data()
        v.b.eval("go('today')")
        v.b.pump(0.3)
        v.b.eval("go('intake-review')")
        v.b.wait("!!document.querySelector('#v-intake-review [data-irsec=mail]') && !!document.querySelector('#v-intake-review [data-irsec=mail]').parentElement.querySelector('tr.irprop')", 30)
        v.b.pump(0.5)
        d = json.loads(p.read_text())
        d["items"][0]["values"]["description"] = "Stale page item CHANGED behind the page"
        p.write_text(json.dumps(d, indent=2))
        n0 = v.db("select count(*) from actions")[0][0]
        clicked = v.b.eval("(()=>{const tr=[...document.querySelectorAll('#v-intake-review tr.irprop')].find(t=>t.textContent.includes('Stale page item')); const x=tr&&tr.querySelector('[data-ira=approve]'); if(!x) return false; x.click(); return true})()")
        time.sleep(3)
        snack = v.b.eval("document.getElementById('snack')?document.getElementById('snack').innerText:''")
        staged = {i["values"]["description"]: i["decision"] for i in json.loads(p.read_text())["items"]}
        rec("345 page: Approve on an item changed behind the page is turned away in plain words, nothing decided",
            clicked and re.search(r"already approved or changed|changed since you looked", snack) and all(x == "pending" for x in staged.values()) and v.db("select count(*) from actions")[0][0] == n0,
            f"clicked={clicked}; message={snack!r}; staged={staged}")
        print("console errors:", v.b.errors[:3])
    finally:
        v.close()
    return C.finish(a)


if __name__ == "__main__":
    C.run(main)
