#!/usr/bin/env python3
"""Usage: python3 -I smoke_post.py <new creaite zip> <old (2.6.0) creaite zip> <work folder>      (needs Google Chrome)
Exit 0 and "RESULT: PASS" = all cases passed. Run it from any folder; the work folder is created if absent.

Post-release 2.6.1 checks on the PUBLISHED zip over a published 2.6.0 vault, through the real page in headless Chrome.
 N1 action WITHOUT raised: Approve saves on the FIRST click.  N2 risk (raid) WITHOUT raised: same.
 H* three staged items A,B,C in ONE file: a held button on B or C, A removed behind the page (file renumbered), with and without
    a records refresh (refreshRecords) before the click: the neighbour is never saved."""
import argparse, json, re, sys, time, urllib.request
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE / "lib"))
import smoke_driver as D  # noqa

MAIL = "Email · From: Priya Nair <priya.nair@northgate.example> · Subject: Data residency · Sent: 2026-10-20 09:00 · Link: https://outlook.example/owa/?ItemID=x"
STALE = "already approved or changed"

def act(n, text):
    return {"n": n, "op": "new", "table": "actions", "match": "strong", "flags": [], "decision": "pending",
            "values": {"project": "FAL", "description": text, "owner": "Lena Fischer", "due_date": "2026-11-09", "source": MAIL}}

def risk(n, text):
    return {"n": n, "op": "new", "table": "raid", "match": "strong", "flags": [], "decision": "pending",
            "values": {"project": "FAL", "type": "Risk", "description": text, "owner": "Lena Fischer", "impact": "High",
                       "likelihood": "Medium", "source": MAIL}}

def main():
    new_zip = Path(sys.argv[1]); old_zip = Path(sys.argv[2]); work = Path(sys.argv[3])
    a = argparse.Namespace(work=str(work), chain=True)
    r = D.Run(a); out = []; res = {}
    def rec(name, ok, note): res[name] = ok; out.append(f"{'PASS' if ok else 'FAIL'} {name}: {note}")
    try:
        r.setup_dirs(); r.make_old_vault(old_zip); out.append("install: " + r.install(new_zip, D.zip_version(new_zip)))
        base, port = r.start_server()
        from cdp import Browser
        b = r.browser = Browser(1400, 1000)
        b.goto(base + "/"); b.wait("typeof go==='function' && LIVE", 30); b.pump(0.5)
        stg = r.vault / "system/staging"
        def tracker(table):
            con = D.sqlite3.connect(f"file:{r.vault / 'system/tracker.db'}?mode=ro", uri=True)
            try: return [x[0] for x in con.execute(f"select description from {table}")]
            finally: con.close()
        def saved(text): return text in tracker("actions") + tracker("raid")
        def staged(): 
            o = {}
            for f in stg.glob("proposed-*.json"):
                for i in json.loads(f.read_text()).get("items", []): o[i["values"]["description"]] = i.get("decision")
            return o
        def decided(text): return saved(text) or staged().get(text) == "approved"
        def stage(name, items):
            p = stg / f"proposed-{name}.json"
            p.write_text(json.dumps({"created": "2026-10-20T09:00:00", "source_run": "cx-sweep", "files": [], "items": items}, indent=2)); return p
        def reload_open():
            b.eval("window.RELOADED=false; reloadData().then(()=>{ window.RELOADED=true; })"); b.wait("window.RELOADED===true", 30)
            b.eval("go('today')"); b.pump(0.3)
            b.eval("go('intake-review')")
            b.wait("!!document.querySelector('#v-intake-review [data-irsec=mail]') && !!document.querySelector('#v-intake-review [data-irsec=mail]').parentElement.querySelector('tr.irprop')", 30); b.pump(0.5)
        def hold(title, button="approve"):
            b.eval("window.HBTN=([...document.querySelectorAll('#v-intake-review tr.irprop')].find(t=>t.textContent.includes(%s))||{querySelector(){return null}}).querySelector('[data-ira=%s]'); !!window.HBTN" % (json.dumps(title), button))
            assert b.eval("!!window.HBTN"), f"no {button} button on {title!r}"
        def snack(): return b.eval("document.getElementById('snack')?document.getElementById('snack').innerText:''") or ""
        def settle(want, secs=14):
            end = time.time() + secs
            while time.time() < end:
                if decided(want) or STALE in snack(): break
                time.sleep(0.25)
            time.sleep(1.5)
        def clear():
            for f in stg.glob("proposed-*.json"): f.unlink()
        # N1 / N2: first click saves
        for nm, mk, txt in (("N1 action without raised", act, "Confirm data residency with legal"), ("N2 risk without raised", risk, "Residency rules could block the pilot")):
            clear(); p = stage("2026-10-20-0900-" + nm[:2].lower(), [mk(1, txt), mk(2, "Neighbour of " + txt)])
            assert "raised" not in json.dumps(json.loads(p.read_text()))
            reload_open(); hold(txt); b.eval("window.HBTN.click()"); settle(txt)
            ok = decided(txt) and STALE not in snack() and not decided("Neighbour of " + txt)
            rec(nm, ok, f"snack={snack()!r}; tracker={saved(txt)}; staged={staged().get(txt)!r}; neighbour decided={decided('Neighbour of ' + txt)}")
        # H: three items in one file, A removed behind the page
        for tag, who, refresh, requery in (("B no-refresh", "B", False, False), ("C no-refresh", "C", False, False),
                                           ("B refresh held-old-button", "B", True, False), ("C refresh held-old-button", "C", True, False),
                                           ("B refresh requeried", "B", True, True), ("C refresh requeried", "C", True, True)):
            clear(); k = re.sub(r"\W", "", tag)
            A, B_, C_ = f"Alpha {k}", f"Bravo {k}", f"Charlie {k}"
            name = f"2026-10-20-1000-h{k}"; p = stage(name, [act(1, A), act(2, B_), act(3, C_)])
            reload_open(); mine = B_ if who == "B" else C_; other = C_ if who == "B" else B_
            hold(mine)
            d = json.loads(p.read_text()); d["items"] = [act(1, B_), act(2, C_)]; p.write_text(json.dumps(d, indent=2))   # Alpha removed, later numbers moved
            if refresh:
                b.eval("window.REFRESHED=false; refreshRecords(['FAL-A-001']).then(()=>{ window.REFRESHED=true; })"); b.wait("window.REFRESHED===true", 30); b.pump(0.5)
                if requery: hold(mine)
            b.eval("window.HBTN.click()"); settle(mine)
            ok = not decided(other) and not decided(A)
            rec(f"H {tag} (button on {who})", ok, f"{who} decided={decided(mine)}; neighbour decided={decided(other)}; Alpha decided={decided(A)}; snack={snack()[:90]!r}")
        out.append(f"console/page errors: {[e[:160] for e in b.errors[:5]]}")
        rec("no console errors", not b.errors, "")
    except Exception as e:
        import traceback; out.append("EXCEPTION " + traceback.format_exc()[-800:]); res["exc"] = False
    finally:
        try: out.append("cleanup: " + r.cleanup(False))
        except Exception as e: out.append(f"cleanup: {e}")
    print("\n".join(out)); print("RESULT:", "PASS" if res and all(res.values()) else "FAIL")
main()
