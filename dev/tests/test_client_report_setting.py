"""H3 of the Reporting hub (#221): the per-project "This project needs a separate client report" setting, its storage, its
defaults, the reminders that follow it, the logo choice and the logo upload route.

Run: python3 dev/tests/test_client_report_setting.py

Brief: dev/sprints/reporting-hub-brief.md, section 6, Rounds 4, 8 and 9, "For Alan answered". The setting is three lines in the
project's CLAUDE.md beside the client report rhythm: `**Client report:** on|off`, `**Client report reminder:** on|off` and
`**Client report logos:** firm, client, partner`. A missing line means on (existing projects), the reminder on and every logo.
A new project is made with the setting off.
"""
import base64
import json
import re
import sys
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
import build_dashboard as bd  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_reports import ABC, ReportRoutes  # noqa: E402
from test_tracker import Vault  # noqa: E402

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")
JPG = (b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
       b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xd9")        # SOI, JFIF, a 1 by 1 frame header, EOI
SVG = b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect width="10" height="10"/></svg>'


def png_of(w, h, trailing=b"", ihdr_only=False):
    """A PNG whose header says w by h (one real row, so its chunks are sound), with `trailing` bytes after IEND."""
    import struct
    import zlib

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    if ihdr_only:
        return b"\x89PNG\r\n\x1a\n"
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\x00\x00")) + chunk(b"IEND", b"") + trailing)


def b64(b):
    return base64.b64encode(b).decode()


def folder_with(text):
    d = Path(tempfile.mkdtemp())
    (d / "CLAUDE.md").write_text("# ABC - X\n\n## Brief\n\n- **Client / partner:** Example Client Ltd\n" + text + "\n")
    return d


class Storage(unittest.TestCase):
    """Storage and defaults, read the way the dashboard reads a project's memory."""

    def test_missing_lines_mean_on_with_reminder_and_every_logo(self):       # existing projects stay on
        m = bd.memory(folder_with("- **Client report rhythm:** weekly"))
        self.assertEqual((m["client_report"], m["client_reminder"], m["logos"]), (True, True, ["firm", "client", "partner"]))

    def test_off_and_on_are_read(self):
        self.assertFalse(bd.memory(folder_with("- **Client report:** off"))["client_report"])
        self.assertTrue(bd.memory(folder_with("- **Client report:** On"))["client_report"])

    def test_the_rhythm_line_is_not_taken_for_the_setting(self):
        m = bd.memory(folder_with("- **Client report rhythm:** off"))
        self.assertEqual((m["client_report"], m["rhythm"]), (True, "Off"))

    def test_reminder_and_logos_lines(self):
        m = bd.memory(folder_with("- **Client report reminder:** off\n- **Client report logos:** firm, partner"))
        self.assertEqual((m["client_reminder"], m["logos"]), (False, ["firm", "partner"]))

    def test_firm_logo_is_always_on(self):
        self.assertEqual(bd.memory(folder_with("- **Client report logos:** client"))["logos"], ["firm", "client"])

    def test_the_template_and_a_new_project_start_off(self):                # default for a NEW project: off (Alan, 18-10-2026)
        text = (Path(__file__).resolve().parents[2] / "system/templates/project-CLAUDE-template.md").read_text()
        self.assertRegex(text, r"\*\*Client report:\*\*\s*off")
        v = Vault()
        self.addCleanup(v.cleanup)
        v.run("init")
        out = v.run("new-project", "--code", "DEF", "--name", "Digital Enablement", script="propose.py").stdout
        spec = v.root / "system/staging/drafts/def.json"
        spec.parent.mkdir(parents=True, exist_ok=True)
        spec.write_text(out)
        v.run("stage", str(spec), script="propose.py")
        v.run("apply")
        self.assertRegex((v.root / "projects/DEF Digital Enablement/CLAUDE.md").read_text(), r"\*\*Client report:\*\*\s*off")


class Reminders(unittest.TestCase):
    """No client reminder for a project with its client report off, or its reminder off; the weekly one stays."""
    SETTINGS = {"reminders": {"enabled": True, "weekly_report_day": "Friday"}}
    NOW = datetime(2026, 10, 16, 13, 0)

    def ids(self, **proj):
        p = {"code": "ABC", "name": "Example Programme", "rhythm": "Weekly", **proj}
        return [r["id"] for r in bd.reminders(self.SETTINGS, [p], [], date(2026, 10, 16), self.NOW)]

    def test_on_reminds(self):
        self.assertTrue([i for i in self.ids() if i.startswith("client:ABC")])
        self.assertTrue([i for i in self.ids(client_report=True, client_reminder=True) if i.startswith("client:ABC")])

    def test_off_has_no_client_reminder_but_keeps_the_weekly_one(self):
        ids = self.ids(client_report=False)
        self.assertFalse([i for i in ids if i.startswith("client:")])
        self.assertTrue([i for i in ids if i.startswith("weekly:")])

    def test_reminder_off_has_no_client_reminder(self):
        self.assertFalse([i for i in self.ids(client_reminder=False) if i.startswith("client:")])


class SessionStart(unittest.TestCase):
    def test_session_start_follows_the_setting(self):
        v = Vault()
        self.addCleanup(v.cleanup)
        populate(v)
        ids = lambda: re.findall(r"say (client report ABC)", v.run("start", "--force", script="session.py").stdout)  # noqa: E731
        mem = v.root / ABC / "CLAUDE.md"
        self.assertTrue(ids())
        mem.write_text(mem.read_text().replace("- **Client report rhythm:**", "- **Client report:** off\n- **Client report rhythm:**"))
        self.assertFalse(ids())


class Routes(unittest.TestCase):
    """The layout's logos follow the project's choice, and the logo upload route (a live server in a throwaway vault)."""
    setUpClass = classmethod(ReportRoutes.setUpClass.__func__)
    tearDownClass = classmethod(ReportRoutes.tearDownClass.__func__)
    post = ReportRoutes.post

    def setUp(self):
        (self.v.root / "system/branding/logos").mkdir(parents=True, exist_ok=True)
        for f in (self.v.root / "system/branding/logos").glob("*"):
            f.unlink()
        mem = self.v.root / ABC / "CLAUDE.md"
        mem.write_text(re.sub(r"- \*\*Client report logos:\*\*[^\n]*\n", "", mem.read_text()))

    def logos(self):
        """The logos the server finds for ABC: {kind: file name}."""
        r = self.post("/api/report/draft", {"kind": "weekly", "code": "ABC", "week_ending": "2026-10-09"})
        return {x["kind"]: Path(x["path"]).name for x in r["logos"]}

    def save(self, kind="client", ext="png", original=PNG, drawn=None, **more):
        return self.post("/api/report/logo/save", {"code": "ABC", "kind": kind, "ext": ext, "original": b64(original),
                                                   **({"drawn": b64(drawn)} if drawn else {}), **more})

    def test_a_new_draft_starts_with_the_project_logo_choice_in_both_reports(self):
        mem = self.v.root / ABC / "CLAUDE.md"
        mem.write_text(mem.read_text().replace("- **Client report rhythm:**", "- **Client report logos:** firm, partner\n- **Client report rhythm:**"))
        for kind, extra in (("weekly", {}), ("client", {})):
            r = self.post("/api/report/draft", {"kind": kind, "code": "ABC", "week_ending": "2026-10-23", **extra})
            self.assertEqual(r["doc"]["layout"]["logos"], ["firm", "partner"], kind)

    def test_upload_saves_the_file_under_the_right_name(self):
        r = self.save("client")
        self.assertTrue(r["ok"], r)
        self.assertEqual((self.v.root / "system/branding/logos/ABC-client.png").read_bytes(), PNG)
        self.assertEqual(self.logos(), {"client": "ABC-client.png"})
        self.assertTrue(self.save("firm")["ok"])
        self.assertTrue((self.v.root / "system/branding/logos/firm.png").is_file())
        self.assertEqual(self.logos(), {"firm": "firm.png", "client": "ABC-client.png"})

    def test_a_trimmed_copy_is_drawn_and_the_original_stays_untouched(self):
        r = self.save("partner", original=JPG, drawn=PNG, ext="jpg")
        self.assertTrue(r["ok"], r)
        d = self.v.root / "system/branding/logos"
        self.assertEqual((d / "ABC-partner.png").read_bytes(), PNG)               # the drawn copy
        self.assertEqual((d / "ABC-partner-original.jpg").read_bytes(), JPG)      # the file chosen, as it was
        self.assertEqual(self.logos(), {"partner": "ABC-partner.png"})            # the original is never drawn

    def test_a_jpeg_says_a_transparent_png_or_svg_sits_better(self):
        self.assertIn("A transparent PNG or SVG sits better", self.save("client", "jpg", JPG)["hint"])
        self.assertNotIn("hint", self.save("client", "png", PNG))

    def test_an_svg_is_kept_as_it_is(self):
        self.assertTrue(self.save("client", "svg", SVG)["ok"])
        self.assertEqual((self.v.root / "system/branding/logos/ABC-client.svg").read_bytes(), SVG)

    def test_changing_the_type_leaves_one_logo(self):
        self.save("client", "png", PNG)
        self.save("client", "svg", SVG)
        self.assertEqual(self.logos(), {"client": "ABC-client.svg"})
        self.assertEqual([p.name for p in (self.v.root / "system/branding/logos").glob("ABC-client.*")], ["ABC-client.svg"])

    def test_refusals_write_nothing(self):
        d = self.v.root / "system/branding/logos"
        for body in (dict(kind="pet"), dict(ext="gif"), dict(original=b"not a picture", ext="png"), dict(original=PNG + b"0" * 400_001)):
            r = self.save(**body)
            self.assertFalse(r["ok"], body)
        self.assertEqual(list(d.glob("*")), [])
        r = self.post("/api/report/logo/save", {"code": "nope", "kind": "client", "ext": "png", "original": b64(PNG)})
        self.assertFalse(r["ok"])

    def test_remove_deletes_the_logo_and_its_original(self):
        self.save("client", "jpg", JPG, drawn=PNG)
        r = self.post("/api/report/logo/remove", {"code": "ABC", "kind": "client"})
        self.assertTrue(r["ok"], r)
        self.assertEqual(list((self.v.root / "system/branding/logos").glob("ABC-client*")), [])
        self.assertEqual(self.logos(), {})

    def test_the_read_route_still_serves_an_uploaded_logo(self):
        self.save("client")
        path = self.post("/api/report/draft", {"kind": "weekly", "code": "ABC", "week_ending": "2026-10-09"})["logos"][0]["path"]
        got = self.post("/api/report/logo", {"code": "ABC", "paths": [path]})["logos"][path]
        self.assertTrue(got.startswith("data:image/png;base64,"))

    # ── p240-leakfix: Team Cap's review of the logo routes ───────────────────────────────────────────────────────
    def test_logo1_logo3_a_picture_is_looked_into_not_just_its_first_bytes(self):
        d = self.v.root / "system/branding/logos"
        bad = {"bare PNG signature": png_of(0, 0, ihdr_only=True), "height 0": png_of(10, 0), "width 0": png_of(0, 10),
               "65535 square": png_of(65535, 65535), "over the cap": png_of(4001, 10),
               "html after IEND": png_of(10, 10, b"<script>1</script>"), "zip after IEND": png_of(10, 10, b"PK\x03\x04"),
               "damaged": png_of(10, 10)[:-3]}
        for why, raw in bad.items():
            r = self.save("client", "png", raw)
            self.assertFalse(r["ok"], why)
            self.assertNotRegex(r["message"], r"/Users|/var/|/private|Traceback", why)
        self.assertTrue(self.save("client", "png", png_of(4000, 4000))["ok"], "the cap itself is allowed")
        for f in d.glob("*"):
            f.unlink()
        for why, raw in {"no frame header": b"\xff\xd8\xff\xe0\x00\x04ab\xff\xd9", "html after EOI": JPG + b"<script>",
                         "no EOI": JPG[:-2], "huge": JPG.replace(b"\x08\x00\x01\x00\x01", b"\x08\xff\xff\xff\xff")}.items():
            self.assertFalse(self.save("client", "jpg", raw)["ok"], why)
        self.assertEqual(list(d.glob("*")), [], "nothing was written")

    def test_logo2_an_svg_with_script_handlers_links_or_a_page_inside_is_refused(self):
        w = 'xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"'
        bad = {"script": f'<svg {w}><script>alert(1)</script></svg>', "onload": f'<svg {w} onload="x()"></svg>',
               "href": f'<svg {w}><a href="http://e.example/"><rect/></a></svg>',
               "xlink": f'<svg {w}><image xlink:href="http://e.example/x.png"/></svg>',
               "foreignObject": f'<svg {w}><foreignObject><p>hi</p></foreignObject></svg>',
               "doctype": f'<!doctype html><svg {w}></svg>', "polyglot": f'<!doctype html><script>1</script><svg {w}></svg>',
               "entity": f'<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY a "aaaa">]><svg {w}>&a;</svg>',
               "not xml": f'<svg {w}><rect></svg>', "iframe": f'<svg {w}><iframe/></svg>',
               "style import": f'<svg {w}><style>@import url(http://e.example/x.css);</style></svg>',
               "style url": f'<svg {w}><rect style="fill:url(http://e.example/x)"/></svg>',
               "huge": f'<svg {w} width="90000" height="90000"></svg>'}
        for why, raw in bad.items():
            self.assertFalse(self.save("client", "svg", raw.encode())["ok"], why)
        self.assertEqual(list((self.v.root / "system/branding/logos").glob("*")), [])
        fine = f'<?xml version="1.0"?><svg {w} viewBox="0 0 9 9"><defs><linearGradient id="g"/></defs><use xlink:href="#g"/></svg>'
        self.assertTrue(self.save("client", "svg", fine.encode())["ok"], "a link to a part of the same file is fine")

    def test_logo5_a_symbolic_link_is_refused_in_plain_words_and_its_target_is_left_alone(self):
        d = self.v.root / "system/branding/logos"
        target = self.v.root / "system/some-system-file.txt"
        target.write_text("keep me")
        (d / "ABC-client.png").symlink_to(target)
        for r in (self.save("client"), self.post("/api/report/logo/remove", {"code": "ABC", "kind": "client"})):
            self.assertFalse(r["ok"], r)
            self.assertIn("symbolic link", r["message"])
            self.assertNotIn(str(self.v.root), r["message"])
        self.assertEqual(target.read_text(), "keep me")
        self.assertTrue((d / "ABC-client.png").is_symlink())

    def test_logo6_the_new_file_is_written_before_a_stale_one_of_another_type_goes(self):
        import json
        self.save("client", "svg", SVG)
        log = self.v.root / "system/config/files-log.jsonl"
        before = len(log.read_text().splitlines()) if log.exists() else 0
        self.assertTrue(self.save("client", "png", PNG)["ok"])
        ops = [(e["op"], Path(e["path"]).name) for e in map(json.loads, log.read_text().splitlines()[before:])]
        self.assertLess(ops.index(("create", "ABC-client.png")), ops.index(("delete", "ABC-client.svg")), ops)
        self.assertEqual(self.logos(), {"client": "ABC-client.png"})

    # ── the per-route body cap (ROUTE_BODY_LIMITS): a logo save is at most 1,200,000 bytes, a remove 4 kB ─────────────────
    def raw_post(self, path, body):
        """(status, answer) of a POST; a server that refuses before reading may close the line while the body is still being sent."""
        import urllib.error
        import urllib.request
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode() or "{}")
        except (urllib.error.URLError, ConnectionError):
            return 0, {}

    def padded_png(self, size):
        """A real PNG made `size` bytes long by a text chunk before its picture data."""
        import struct
        import zlib
        base = png_of(1, 1)
        head, rest = base[:33], base[33:]
        pad = size - len(base) - 12
        text = b"Comment\x00" + b"x" * (pad - 8)
        chunk = struct.pack(">I", len(text)) + b"tEXt" + text + struct.pack(">I", zlib.crc32(b"tEXt" + text) & 0xFFFFFFFF)
        out = head + chunk + rest
        self.assertEqual(len(out), size)
        return out

    def test_body_cap_a_save_of_about_1_3_mb_is_refused_and_writes_nothing(self):
        d = self.v.root / "system/branding/logos"
        status, ans = self.raw_post("/api/report/logo/save", {"code": "ABC", "kind": "client", "ext": "png", "original": "A" * 1_300_000})
        self.assertIn(status, (0, 400), (status, ans))
        if status:
            self.assertFalse(ans.get("ok"), ans)
            self.assertTrue(ans.get("message"), ans)
        self.assertEqual(list(d.glob("*")), [])
        self.assertEqual(self.post("/api/report/logo", {"code": "ABC", "paths": []}).get("ok"), True, "the server still answers")

    def test_body_cap_a_logo_and_its_trimmed_copy_of_400000_bytes_each_still_save(self):
        big = self.padded_png(400_000)
        r = self.save("client", "png", big, drawn=big)
        self.assertTrue(r["ok"], r)
        self.assertEqual((self.v.root / "system/branding/logos/ABC-client.png").stat().st_size, 400_000)

    def test_body_cap_a_remove_with_a_5_kb_body_is_refused(self):
        self.save("client", "png", PNG)
        status, ans = self.raw_post("/api/report/logo/remove", {"code": "ABC", "kind": "client", "pad": "x" * 5000})
        self.assertIn(status, (0, 400), (status, ans))
        self.assertTrue((self.v.root / "system/branding/logos/ABC-client.png").is_file(), "nothing was removed")


if __name__ == "__main__":
    unittest.main()
