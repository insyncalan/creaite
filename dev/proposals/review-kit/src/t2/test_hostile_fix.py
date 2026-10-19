import json, sys, time, unittest, zipfile, http.client
from pathlib import Path
sys.path.insert(0, "${REPO_ROOT}/.claude/worktrees/review-sbsfix/dev/tests")
import test_sbs_matchgate as M
INT, CLI, WEEK = M.INT, M.CLI, M.WEEK
HOST = " Xylohostile Budget overrun on phase one is being absorbed. Confirm tester names ABC-A-005 Omar Ali confidential. internal\\-only note."


class Hostile(M.Base):
    def files_with(self, word):
        hits = []
        for p in self.v.root.rglob("*"):
            if p.is_file() and p.suffix in (".html", ".json", ".docx", ".md", ".pdf"):
                try:
                    b = p.read_bytes()
                    if p.suffix == ".docx":
                        with zipfile.ZipFile(p) as z: b = z.read("word/document.xml")
                    if word.encode() in b: hits.append(str(p.relative_to(self.v.root)))
                except Exception: pass
        return hits

    def held_open(self):
        return self.q("(()=>{const d=document.getElementById('crHeldDlg'); return !!d && d.open})()")

    def test_h2_match_all_hostile(self):
        self.open_side()
        self.write(INT, HOST)
        self.press("[data-crmatchall]")
        self.b.wait("(()=>{const d=document.getElementById('crHeldDlg'); return !!d && d.open})()", 15)
        print("H2 dialog:", self.held_dialog()[:400].replace("\n", " | "))
        self.b.pump(3)
        raw = json.dumps(self.client_draft())
        print("H2 client draft holds:", {w: (w in raw) for w in ("Xylohostile", "ABC-A-005", "Omar", "onfidential", "internal")})
        doc = self.api("/api/report/draft", {"kind": "weekly", "code": "ABC", "week_ending": WEEK})["doc"]
        next(x for x in doc["sections"] if x["id"] == "health")["text"] = "UAT start slipped two weeks."
        self.api("/api/report/save", {"doc": doc, "base_version": doc["version"]})
        print("H2 int approve", self.api("/api/report/approve", {"kind": "weekly", "code": "ABC", "week_ending": WEEK, "force": True}).get("ok"))
        for fmt in ("html", "docx", "pdf"):
            r = self.api("/api/report/export", {"kind": "client", "code": "ABC", "week_ending": WEEK, "fmt": fmt, "on_clash": "number"})
            print("H2", fmt, "export ok:", r.get("ok"), str(r.get("message"))[:120])
        c = self.client_draft()
        r = self.api("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "doc": c, "base_version": c.get("version"), "force": True})
        print("H2 client approve ok:", r.get("ok"), str(r.get("message"))[:160])
        print("H2 files with Xylohostile:", self.files_with("Xylohostile"))

    def test_h4_base_finding_masks_new_internal_text(self):
        """The client draft already has a finding ('confidential'); then an internal section with new internal words of the same kind."""
        self.open_side()
        self.write(CLI, " Nothing confidential here.")
        self.b.pump(3)
        self.write(INT, " Zorblexsecret plan for the vendor. This is confidential. internal-only", "next_week")
        self.b.wait(f"!!document.querySelector({json.dumps(self.match_btn('next_week'))})", 10)
        self.press(self.match_btn("next_week"))
        self.b.pump(3)
        print("H4 dialog open:", self.held_open(), self.held_dialog()[:200].replace("\n", " | "))
        raw = json.dumps(self.client_draft()) + self.staging_files_text()
        print("H4 Zorblexsecret on client pane:", "Zorblexsecret" in self.q(f"document.querySelector('{CLI}').innerText"),
              "in client draft/staging:", "Zorblexsecret" in raw)

    def test_h5_route(self):
        self.open_hub()
        base = self.client_draft()
        # audience flipped to internal on a client kind
        d = json.loads(json.dumps(base)); d["audience"] = "internal"
        next(s for s in d["sections"] if s["id"] == "summary")["text"] = "Omar Ali confidential"
        print("R audience-internal:", self.api("/api/report/match-check", {"docs": [d]}))
        # svg data address in a text, backslash-escaped marker
        d2 = json.loads(json.dumps(base))
        next(s for s in d2["sections"] if s["id"] == "summary")["text"] = 'See <span style="background:url(data:image/svg+xml,%3Csvg%3E%3Ctext%3Econfidential%3C/text%3E%3C/svg%3E)">x</span> and internal\\-only'
        print("R svg/backslash:", self.api("/api/report/match-check", {"docs": [d2]}))
        # non-string text, duplicate ids, missing sections, non-dict
        d3 = json.loads(json.dumps(base)); next(s for s in d3["sections"] if s["id"] == "summary")["text"] = ["Omar Ali"]
        d4 = json.loads(json.dumps(base)); d4["sections"].append(dict(d4["sections"][0]))
        d5 = json.loads(json.dumps(base)); d5.pop("sections")
        for name, x in (("nonstr", d3), ("dup", d4), ("nosec", d5), ("notdict", 5), ("null", None)):
            r = self.api("/api/report/match-check", {"docs": [x]})
            print("R", name, str(r)[:160])
        # 60 big docs timing
        big = json.loads(json.dumps(base))
        next(s for s in big["sections"] if s["id"] == "summary")["text"] = ("Quincebrook is on plan for the week. " * 6000)
        t = time.time(); r = self.api("/api/report/match-check", {"docs": [big] * 60}); dt = time.time() - t
        print("R 60 big docs (~%d kB each): ok=%s %.1fs" % (len(json.dumps(big)) // 1024, r.get("ok") if isinstance(r, dict) else r, dt))
        # auth
        origin = self.q("location.host"); tok = self.q("D.token")
        h, p = origin.rsplit(":", 1)
        body = json.dumps({"docs": [base]})
        for name, hdrs, meth in (("no token", {"Host": origin}, "POST"), ("wrong token", {"Host": origin, "X-Creaite-Token": "x"}, "POST"),
                                 ("wrong host", {"Host": "evil.example:" + p, "X-Creaite-Token": tok}, "POST"), ("options", {"Host": origin}, "OPTIONS"),
                                 ("good", {"Host": origin, "X-Creaite-Token": tok}, "POST")):
            c = http.client.HTTPConnection(h, int(p), timeout=30)
            c.request(meth, "/api/report/match-check", body=body, headers={**hdrs, "Content-Type": "application/json"})
            rr = c.getresponse(); print("R auth", name, rr.status, rr.read()[:60]); c.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
