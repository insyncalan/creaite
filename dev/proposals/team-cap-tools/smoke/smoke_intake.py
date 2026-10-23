#!/usr/bin/env python3
"""Usage: python3 -I smoke_intake.py <new creaite zip> <old (2.6.0) creaite zip>      (needs Google Chrome)

Extra smoke on the 2.6.1 candidate: autostart/status + item/history routes, and Intake Approve of a staged row through the page.
Reuses smoke_driver.Run (old 2.6.0 vault -> update.py install of the candidate zip -> live server with stand-in claude -> real headless Chrome)."""
import argparse, json, re, sys, time, urllib.request, urllib.error
from datetime import datetime
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE / "lib"))
import smoke_driver as D  # noqa

MAIL = "Email · From: Priya Nair <priya.nair@northgate.example> · Subject: Data residency · Sent: 2026-10-20 09:00 · Link: https://outlook.example/owa/?ItemID=x"

def main():
    new_zip = Path(sys.argv[1]); old_zip = Path(sys.argv[2])
    a = argparse.Namespace(work=str(D.WORK), chain=True)
    r = D.Run(a)
    out = []
    try:
        r.setup_dirs()
        r.make_old_vault(old_zip)
        r.install(new_zip, D.zip_version(new_zip))
        base, port = r.start_server()
        html = urllib.request.urlopen(base + "/").read().decode()
        token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]
        for path in ("/api/autostart/status", "/api/item/history?id=FAL-A-001"):
            post = path.startswith("/api/autostart")
            req = urllib.request.Request(base + path, data=(b"{}" if post else None), method=("POST" if post else "GET"), headers={"X-Creaite-Token": token, "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=20) as resp:
                    out.append(f"{req.get_method()} {path} -> {resp.status} {resp.read().decode()[:160]}")
            except urllib.error.HTTPError as e:
                out.append(f"{req.get_method()} {path} -> HTTP {e.code}")
        # stage one sweep proposal: two mail actions for FAL
        def act(n, text):
            return {"n": n, "op": "new", "table": "actions", "match": "strong", "flags": [], "decision": "pending",
                    "values": {"project": "FAL", "description": text, "owner": "Lena Fischer", "due_date": "2026-11-09", "raised": "2026-10-20", "source": MAIL}}
        p = r.vault / "system/staging/proposed-2026-10-20-0900-sweep.json"
        p.write_text(json.dumps({"created": "2026-10-20T09:00:00", "source_run": "cx-sweep", "files": [],
                                 "items": [act(1, "Confirm data residency with legal"), act(2, "Share the pilot plan with the client")]}, indent=2))
        from cdp import Browser
        b = r.browser = Browser(1400, 1000)
        shots = r.dir / "shots"; shots.mkdir()
        b.goto(base + "/"); b.wait("typeof go==='function' && LIVE", 30); b.pump(0.5)
        b.eval("go('intake-review')")
        b.wait("!!document.querySelector('#v-intake-review [data-irsec=mail]') && !!document.querySelector('#v-intake-review [data-irsec=mail]').parentElement.querySelector('tr.irprop')", 30)
        b.pump(0.5)
        rows_before = b.eval("document.querySelectorAll('#v-intake-review tr.irprop').length")
        out.append(f"Intake mail section drawn with {rows_before} proposal rows")
        b.screenshot(str(shots / "intake-before.png"))
        b.eval("window.__t=[...document.querySelectorAll('#v-intake-review tr.irprop')].find(t=>t.textContent.includes('Confirm data residency')); window.__btn=window.__t&&window.__t.querySelector('[data-ira=approve]'); !!window.__btn")
        if not b.eval("!!window.__btn"):
            raise D.Hard("no Approve button on the row")
        b.eval("window.__btn.click()")
        end = time.time() + 20; snack = ""
        while time.time() < end:
            snack = b.eval("document.getElementById('snack')?document.getElementById('snack').innerText:''") or ""
            if snack.strip(): break
            time.sleep(0.3)
        b.pump(1.5)
        snack2 = b.eval("document.getElementById('snack')?document.getElementById('snack').innerText:''") or ""
        b.screenshot(str(shots / "intake-after.png"))
        d = json.loads(p.read_text())
        decs = {i["values"]["description"]: i.get("decision") for i in d["items"]}
        con = D.sqlite3.connect(f"file:{r.vault / 'system/tracker.db'}?mode=ro", uri=True)
        tr = [x[0] for x in con.execute("select description from actions where description like 'Confirm data residency%'")]
        con.close()
        still = b.eval("[...document.querySelectorAll('#v-intake-review tr.irprop')].some(t=>t.textContent.includes('Confirm data residency') && t.querySelector('[data-ira=approve]'))")
        rows_after = b.eval("document.querySelectorAll('#v-intake-review tr.irprop').length")
        out.append(f"snack after click: {snack!r} / later {snack2!r}")
        out.append(f"staging decisions: {decs}; tracker rows for it: {tr}; approve button still on that row: {still}; proposal rows {rows_before} -> {rows_after}")
        refused = re.search(r"already approved or changed|refus|couldn.t|error", (snack + snack2), re.I)
        out.append(f"console/page errors: {[e[:160] for e in b.errors[:5]]}")
        ok = (decs.get("Confirm data residency with legal") == "approved" or tr) and not refused and not b.errors
        out.append("RESULT: " + ("PASS" if ok else "FAIL"))
    except Exception as e:
        out.append(f"EXCEPTION {type(e).__name__}: {e}"); out.append("RESULT: FAIL")
    finally:
        try: r.cleanup(False)
        except Exception as e: out.append(f"cleanup: {e}")
    print("\n".join(out))
main()
