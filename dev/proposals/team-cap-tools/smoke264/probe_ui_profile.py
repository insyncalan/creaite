"""#312 and #348: Your profile, on first run and when the name matches someone else in the people register.

  python3 -I probe_ui_profile.py NEW_ZIP BASE_ZIP WORK_DIR [--label 2.6.4] [--control] [--keep]

Two scratch vaults (fictional people), headless Chrome at 1400 px.
  #312  Name unset: Today shows "About you"; "Not now" hides it and stays hidden across a reload; Settings search finds
        "Your profile". Saving a name containing a pipe stores it without the pipe (the register is a pipe table), and saving
        the details three times leaves one register row for that person.
  #348  Name set to a colleague who is already in the register (with email, organisation, role): the profile card does not show
        her details as yours (they read "Not set") and the button says "Add my details"; pressing it asks "Is that row you?"
        and the register row is left unchanged.
Expected on 2.6.4 (base 2.6.3): all PASS. With --control only the #348 card check FAILS (2.6.3 shows her email, organisation and
role as yours, with "Edit my details"); the #312 checks and the "Is that row you?" prompt were already there in 2.6.3.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402
from common import rec  # noqa: E402

REG_ROW = "| Lena Fischer | lena.fischer@northgate.example | Lena F | Northgate | Delivery lead |  |  |  |\n"
SEP = "|-----------|-------|---------|--------------|------|--------|-----|--------|\n"


def first_run(a):
    v = C.V("pProfile1", identity=None, calendar=False)
    try:
        v.start(1400, 1000)
        b = v.b
        b.eval("go('today')")
        b.pump(2.0)
        t = v.view_text("v-today")
        about = "About you" in t
        rec("312 first run shows 'About you' on Today when the name is unset", about, f"Not now offered: {'Not now' in t}; Add my details: {'Add my details' in t}")
        if about:
            b.eval("(()=>{const x=[...document.querySelectorAll('#v-today button')].find(e=>/^Not now/.test(e.innerText.trim())); if(x) x.click()})()")
            b.pump(1.0)
            gone = "About you" not in v.view_text("v-today")
            v.reload_page()
            b.eval("go('today')")
            b.pump(1.5)
            gone2 = "About you" not in v.view_text("v-today")
            rec("312 'Not now' on About you is remembered across a reload", gone and gone2, f"hidden after click {gone}, after reload {gone2}")
        b.eval("go('settings')")
        b.pump(1.2)
        v.settings_search("profile")
        rec("312 Your profile card is found by Settings search", "Your profile" in v.view_text("v-settings"), "")
        reg = v.vault / "projects/_portfolio/people-register.md"
        for i in range(3):
            b.eval("(()=>{const i=document.getElementById('pfName'); i.focus(); i.value='Robin | Hale'; i.dispatchEvent(new Event('input',{bubbles:true}));})()")
            b.eval("document.getElementById('pfNameSave').click()")
            b.pump(1.2)
        stored = v.settings().get("identity", {}).get("name")
        rec("312 a pipe in the saved name is not stored", bool(stored) and "|" not in stored, f"stored {stored!r}")
        for k in range(3):
            b.eval("document.getElementById('pfEdit').click()")
            b.pump(1.2)
            b.eval("(()=>{for(const [id,val] of [['pd_email','robin.hale@northgate.example'],['pd_org','Org Three'],['pd_role','Lead %d']]){const e=document.getElementById(id); e.value=val; e.dispatchEvent(new Event('input',{bubbles:true}));}})()" % k)
            b.eval("document.getElementById('pdSave').click()")
            b.pump(1.5)
        rows = [l for l in reg.read_text().splitlines() if "Hale" in l]
        rec("312 saving the details three times leaves one register row", len(rows) == 1, f"{len(rows)} row(s): {[r[:70] for r in rows]}")
        print("console errors:", b.errors[:3])
    finally:
        v.close()


def colleague(a):
    v = C.V("pProfile2", identity="Lena Fischer", calendar=False)
    try:
        reg = v.vault / "projects/_portfolio/people-register.md"
        t = reg.read_text()
        reg.write_text(t.replace(SEP, SEP + REG_ROW, 1))
        before = reg.read_text()
        v.run("build_dashboard.py")
        v.start(1400, 1000)
        b = v.b
        b.eval("go('settings')")
        b.pump(1.2)
        v.settings_search("profile")
        card = b.eval("(()=>{const e=[...document.querySelectorAll('#v-settings .srow, #v-settings section, #v-settings .scard')].find(x=>/Your profile/.test(x.innerText)&&/Organisation/.test(x.innerText)); return e?e.innerText.replace(/\\n+/g,' | '):document.getElementById('v-settings').innerText.replace(/\\n+/g,' | ')})()")
        shows = [w for w in ("lena.fischer@northgate.example", "Northgate", "Delivery lead", "Lena F") if w in card]
        btn = b.eval("[...document.querySelectorAll('#v-settings button')].map(x=>x.innerText.trim()).filter(x=>/my details/i.test(x))")
        rec("348 name matches a colleague: the card does not show her details as yours", not shows and "Add my details" in btn, f"details shown: {shows}; buttons: {btn}")
        asked = b.eval("""(async()=>{ window.__confirms=[]; window.confirm=(m)=>{window.__confirms.push(String(m)); return false};
            const x=[...document.querySelectorAll('#v-settings button')].find(e=>/my details/i.test(e.innerText)); if(x) x.click(); await new Promise(r=>setTimeout(r,800)); return window.__confirms})()""")
        dlg = b.eval("[...document.querySelectorAll('dialog[open],.modal,.dlg,[role=dialog]')].map(e=>e.innerText.replace(/\\n+/g,' | ').slice(0,250))")
        rec("348 Add my details asks 'Is that row you?'", any("row you" in x for x in (asked or []) + (dlg or [])), f"confirm(): {asked}; dialogs: {dlg}")
        rec("348 the colleague's register row is unchanged", reg.read_text() == before, "")
        print("console errors:", b.errors[:3])
    finally:
        v.close()


def main():
    a = C.parse(__doc__)
    first_run(a)
    colleague(a)
    return C.finish(a)


if __name__ == "__main__":
    C.run(main)
