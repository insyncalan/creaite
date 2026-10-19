"""S-list probes on the logo routes, fictional data only."""
import sys, os, unittest
from pathlib import Path
ROOT = Path(sys.argv.pop(1))
sys.path.insert(0, str(ROOT / "dev" / "tests")); sys.path.insert(0, str(ROOT / "system" / "scripts"))
import test_partner_logos as TP
from test_client_report_setting import PNG, SVG, b64

class S(TP.Routes):
    def test_s(self):
        d = self.d
        firm = d / "firm.png"; firm.write_bytes(PNG); client = d / "ABC-client.png"; client.write_bytes(PNG + b"")
        fb, cb = firm.read_bytes(), client.read_bytes()
        self.partners("Firm; Client; Partner; Con; Nul")
        for k in ["partner:firm", "partner:client", "partner:partner", "partner:con", "partner:nul"]:
            r = self.save(k); print("S6/S8 save", k, r.get("ok"), r.get("message", "")[:60])
        print("S6/S13 firm unchanged:", firm.read_bytes() == fb, "client unchanged:", client.read_bytes() == cb, sorted(self.files()))
        for k in ["partner:", "partner", "partner:x:y", "partner:X", "Partner:x", " partner:x", "partner:x\n", ["partner:x"], {"a": 1}, None, 5,
                  "partner:..", "partner:.", "partner:a/b", "partner:a\\b", "partner:%2e%2e", "partner:..%2f", "partner:a\x00", "partner:" + "a" * 5000,
                  "partner:firm-original", "partner:x-original"]:
            before = self.files()
            try:
                r = self.save(k)
            except Exception as e:
                r = {"ok": "EXC " + type(e).__name__}
            if r.get("ok") is not False or self.files() != before:
                print("S2/S3/S5/S7 NOT REFUSED", repr(k)[:40], r)
        print("S2/S3/S5/S7 batch done")
        # S10 symlink at a partner's file
        self.partners("Acme")
        tgt = Path(self.v.root) / "elsewhere.png"; tgt.write_bytes(PNG)
        link = d / "ABC-partner-acme.png"; os.symlink(tgt, link)
        r = self.save("partner:acme"); print("S10 save over link:", r.get("ok"), r.get("message", "")[:70])
        r = self.remove("partner:acme"); print("S10 remove link:", r.get("ok"), "target kept:", tgt.exists(), "link kept:", link.is_symlink())
        link.unlink()
        # S11 another project's same slug stays
        (d / "DEF-partner-acme.png").write_bytes(PNG)
        self.save("partner:acme"); r = self.remove("partner:acme")
        print("S11 DEF file kept:", (d / "DEF-partner-acme.png").exists(), r.get("ok"))
        # S12 orphan remove, then orphan via a name no longer in line, and an orphan save refused
        self.save("partner:acme"); self.partners("Beta")
        got = self.post("/api/report/logo", {"code": "ABC"}); print("S12 orphans:", [o["kind"] for o in got["orphans"]])
        print("S12 save to orphan refused:", self.save("partner:acme").get("ok") is False)
        print("S12 remove orphan:", self.remove("partner:acme").get("ok"), self.files())
        # another project's orphan via ABC's remove?
        r = self.remove("partner:def"); print("cross-project remove refused:", r.get("ok") is False)
        # firm remove from project settings deletes for all
        r = self.remove("firm"); print("S14 firm remove ok (server, no extra guard):", r.get("ok"), "firm still there:", firm.exists())

if __name__ == "__main__":
    unittest.main(argv=["x", "S.test_s"], verbosity=0)
