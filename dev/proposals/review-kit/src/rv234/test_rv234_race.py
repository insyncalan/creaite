"""Scratch review probe for #234 (v250-hiddenrow 4e268455): a late /api/report/reshow answer after switching project. Fictional data."""
import json, sys, unittest
sys.path.insert(0, __import__("os").environ["KIT_CK"] + "/dev/tests")
import test_sbs_matchgate as M
from test_workstreams import add_project
INT, CLI, WEEK = M.INT, M.CLI, M.WEEK
MARK = "Kestrelharbour is on plan for the week."


class Race(M.Base):
    @classmethod
    def load(cls, v):
        M.H.R.populate(v)
        add_project(v, "DEF", "Quiet Project")
        v.run("init")

    def test_late_reshow_after_switch(self):
        self.open_side()
        d = self.api("/api/report/draft", {"kind": "weekly", "code": "ABC", "week_ending": WEEK})["doc"]
        for sec in d["sections"]:
            if sec["id"] in ("overdue", "risks", "decisions"):
                for r in sec.get("rows") or []:
                    r["shown"] = False
            if sec["id"] == "summary":
                sec["text"] = MARK
        print("save", self.api("/api/report/save", {"doc": d, "base_version": d.get("version")}).get("ok"), flush=True)
        back = self.api("/api/report/draft", {"kind": "weekly", "code": "ABC", "week_ending": WEEK})["doc"]
        bare = [(sec["id"], r["ref"]) for sec in back["sections"] if sec["id"] in ("overdue", "risks", "decisions") for r in sec.get("rows") or [] if r.get("ref") not in (back.get("items") or {})]
        print("bare candidates", bare, flush=True)
        sid, ref = sorted(bare, key=lambda x: x[0] != "risks")[0]
        self.open_side()
        print("bare row text:", self.q(f"(document.querySelector('{INT} [data-id={sid}] [data-ref=\"{ref}\"]')||{{textContent:'none'}}).textContent"), flush=True)
        self.q("window.confirm=()=>true; window.alert=()=>{};")
        self.q("""(()=>{const f=window.fetch.bind(window); window.__rs=0; window.fetch=(u,o)=>{ if(String(u).endsWith('/api/report/reshow')){ window.__rs++; return new Promise(r=>setTimeout(()=>r(f(u,o)),6000)); } return f(u,o); };})()""")
        self.q(f"document.querySelector('{INT} [data-id={sid}] [data-ref=\"{ref}\"] .wr-eye').click()")
        self.b.pump(0.3)
        self.q("setTimeout(()=>{ const p=P.find(p=>p.code==='DEF'); if(p) p.cr=true; go('reporting','DEF'); }, 50); 1")
        print("switched", flush=True)
        for k in range(10):
            self.b.pump(1)
            print(k, self.q("location.hash"), self.q("(document.getElementById('hubMeta')||{textContent:''}).textContent"), self.q(f"!!document.querySelector('{INT} [data-ref=\"{ref}\"]')"), "Kestrelharbour" in (self.q(f"(document.querySelector('{INT}')||{{innerText:''}}).innerText") or ""), self.q("window.__rs"), flush=True)
        print("meta", self.q("document.getElementById('hubMeta').textContent"), flush=True)
        print("INT pane has ABC ref:", self.q(f"!!document.querySelector('{INT} [data-ref=\"{ref}\"]')"), "INT has MARK:", "Kestrelharbour" in (self.q(f"(document.querySelector('{INT}')||{{innerText:''}}).innerText") or ""), flush=True)
        if self.q("!!document.querySelector('[data-crmatchall]')"):
            self.q("setTimeout(()=>document.querySelector('[data-crmatchall]').click(),10); 1")
            self.b.pump(6)
        pane = self.q(f"(document.querySelector('{CLI}')||{{innerText:''}}).innerText") or ""
        print("DEF client pane holds MARK:", "Kestrelharbour" in pane, "holds ref:", ref in pane, flush=True)
        self.b.pump(4)
        r = self.api("/api/report/draft", {"kind": "client", "code": "DEF", "week_ending": WEEK})
        print("DEF client draft where", r.get("where"), "holds MARK:", "Kestrelharbour" in json.dumps(r.get("doc")), "ref:", ref in json.dumps(r.get("doc")), flush=True)


if __name__ == "__main__":
    unittest.main()
