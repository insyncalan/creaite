"""BL-76: editing Current state and adding images, in a real browser against the real live server.

Run: python3 dev/tests/test_current_state_live.py   (needs Google Chrome; skipped otherwise)

The other dashboard tests drive the page against a stand-in for the vault's file layer. These don't: each test starts
the real live server in a throwaway vault, drives headless Chrome with real mouse clicks and a real file chosen from
disk (dev/tools/cdp.py), and then reads the files the server wrote. That is the path a person takes, including the
upload route, the proposal, the apply, the images/ folder and the page that is rebuilt afterwards.
"""
import base64
import json
import os
import re
import struct
import sys
import time
import unittest
import zlib
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from test_dashboard import png  # noqa: E402
from live_browser import TEST_PALETTES, LiveBrowserCase  # noqa: E402

# a real 16 x 12 JPEG (made with sips), so the browser can decode what the server accepts
JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQAASABIAAD/4QBMRXhpZgAATU0AKgAAAAgAAYdpAAQAAAABAAAAGgAAAAAAA6ABAAMAAAABAAEAAKACAAQAAAABAAAAEKADAAQAAAABAAAADAAAAAD/7QA4UGhvdG9zaG9wIDMuMAA4QklNBAQAAAAAAAA4QklNBCUAAAAAABDUHYzZjwCyBOmACZjs+EJ+/8AAEQgADAAQAwEiAAIRAQMRAf/EAB8AAAEFAQEBAQEBAAAAAAAAAAABAgMEBQYHCAkKC//EALUQAAIBAwMCBAMFBQQEAAABfQECAwAEEQUSITFBBhNRYQcicRQygZGhCCNCscEVUtHwJDNicoIJChYXGBkaJSYnKCkqNDU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6g4SFhoeIiYqSk5SVlpeYmZqio6Slpqeoqaqys7S1tre4ubrCw8TFxsfIycrS09TV1tfY2drh4uPk5ebn6Onq8fLz9PX29/j5+v/EAB8BAAMBAQEBAQEBAQEAAAAAAAABAgMEBQYHCAkKC//EALURAAIBAgQEAwQHBQQEAAECdwABAgMRBAUhMQYSQVEHYXETIjKBCBRCkaGxwQkjM1LwFWJy0QoWJDThJfEXGBkaJicoKSo1Njc4OTpDREVGR0hJSlNUVVZXWFlaY2RlZmdoaWpzdHV2d3h5eoKDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uLj5OXm5+jp6vLz9PX29/j5+v/bAEMACQkJCQkJEAkJEBYQEBAWHhYWFhYeJh4eHh4eJi4mJiYmJiYuLi4uLi4uLjc3Nzc3N0BAQEBASEhISEhISEhISP/bAEMBCwwMEhESHxERH0szKjNLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS//dAAQAAf/aAAwDAQACEQMRAD8AyKKKK+oPmj//2Q==")
TODAY = date.today().isoformat()


def big_png(min_bytes):
    """A valid PNG whose compressed size is at least `min_bytes` (random pixels don't compress)."""
    w = 600
    h = min_bytes // (w * 3) + 20
    raw = b"".join(b"\x00" + os.urandom(w * 3) for _ in range(h))
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))  # noqa: E731
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + \
        chunk(b"IDAT", zlib.compress(raw, 0)) + chunk(b"IEND", b"")


class LiveCurrentState(LiveBrowserCase):
    """A fresh vault, live server and browser for every test."""

    width, height = 1280, 900

    def setUp(self):
        super().setUp()
        self.pics = self.v.root / "pics"
        self.pics.mkdir(exist_ok=True)

    # ── helpers ──
    def pic(self, name, data):
        p = self.pics / name
        p.write_bytes(data)
        return p

    def memory(self, code="ABC"):
        return next((self.v.root / "projects").glob(f"{code} */CLAUDE.md"))

    def images(self, code="ABC"):
        return sorted(p.name for p in self.memory(code).parent.glob("images/*"))

    def current_md(self, code="ABC"):
        return re.search(r"## Current state\n(.*?)(?=\n## |\Z)", self.memory(code).read_text(), re.S).group(1)

    def open_editor(self, code="ABC"):
        b = self.b
        b.eval(f"go('cockpit','{code}')")
        b.wait("document.querySelector('#v-cockpit .curcard')")
        b.click("#v-cockpit .curcard [data-edcur]")
        b.wait("document.getElementById('curEd')")

    def add_image(self, path, caption=None):
        b = self.b
        n = b.eval("document.querySelectorAll('#curEd figure.cimg').length")
        b.set_files("#curImgFile", [path])
        b.wait(f"document.querySelectorAll('#curEd figure.cimg').length>{n}", 5)
        if caption:                                           # the new figure's caption has the focus
            b.type(caption)
            b.wait(f"[...document.querySelectorAll('#curEd figure.cimg figcaption')].some(c=>c.textContent.includes({json.dumps(caption)}))", 5)   # #152: it was typed (a timeout says where the focus was)

    def cancel_asks(self, where=""):
        """Press Cancel on a changed editor and wait for the question. #152: on the macOS runner the click landed on a DIV and the
        question never came, with the button still in the page: the editor had laid out again between measuring the button and
        pressing. So the press waits until the button has stopped moving and is the element at its own centre (click exact=True).
        If the page still saw the click somewhere else, it is pressed once more; a click that reached the button and did nothing is
        a real fault and fails at once. A failure says what was at the point, the button's rectangle, the viewport, theme and mode."""
        b = self.b
        b.eval("""window.__cl=[]; if(!window.__clOn){ window.__clOn=true;
            for(const t of ['mousedown','mouseup','click']) addEventListener(t,e=>{ const x=e.target&&e.target.closest?e.target.closest('[data-cure],[data-rc],[data-dis]'):null;
                __cl.push(t+':'+(x?(x.dataset.cure||x.dataset.rc||x.dataset.dis):(e.target.tagName||'?'))); },true); }""")
        up = "document.getElementById('discardBar').classList.contains('on')"
        for attempt in (1, 2):
            b.eval("window.__cl=[]")
            b.click('[data-cure="cancel"]', exact=True)
            try:
                b.wait(up, 3 if attempt == 1 else 5)
                return
            except TimeoutError as e:
                seen = b.eval("({events: __cl, editorOpen: !!document.getElementById('curEd'), dirty: !!(CURED && CURED.dirty)})")
                seen["now"] = b.hit_report('[data-cure="cancel"]')
                reached = "click:cancel" in seen["events"]
                if attempt == 2 or reached:                      # the button got the click and did nothing: a real fault
                    raise AssertionError(f"Cancel on a changed editor did not ask (attempt {attempt}, {where}): {seen}\n{e}") from e

    def save(self):
        b = self.b
        b.eval("document.getElementById('snackT').textContent=''")          # so an earlier message isn't mistaken for this one
        b.click('[data-cure="save"]')
        b.wait("/— saved|Not saved|stopped|only|at most|Only|Saving needs|Can.t read/i.test(document.getElementById('snackT').textContent)", 15)
        return b.eval("document.getElementById('snackT').textContent")

    def card(self, code="ABC"):
        """What the project page shows for Current state: each image with its natural width, or its 'not found' note."""
        return self.b.eval("""[...document.querySelectorAll('#curText figure.cimg')].map(f=>({ref:f.dataset.ref,
          w:f.querySelector('img')?f.querySelector('img').naturalWidth:0, missing:!!f.querySelector('.sub'), cap:f.querySelector('figcaption').textContent}))""")

    def reload_to(self, code="ABC"):
        b = self.b
        b.reload()
        b.wait("typeof go==='function' && LIVE")
        b.eval(f"go('cockpit','{code}')")
        b.wait("document.querySelector('#v-cockpit .curcard')")

    # ── tests ──
    def test_a_new_image_is_filed_shown_and_kept_after_a_reload(self):
        shot = self.pic("Screen Shot 2026-10-08 at 09.15.22.PNG", png(300, 200, (200, 60, 40)))
        self.open_editor()
        self.add_image(shot, "Pipeline view")
        msg = self.save()
        self.assertIn("— saved", msg)
        name = f"{TODAY}-pipeline-view.png"
        self.assertIn(name, self.images())                                   # copied into the project's images/
        self.assertIn(f"![Pipeline view](images/{name})", self.current_md())  # the file's text names that file
        self.assertFalse(list((self.v.root / "system/staging/uploads").glob("*")))   # nothing left staged
        shown = {c["ref"]: c for c in self.card()}
        self.assertTrue(shown[f"images/{name}"]["w"] > 0, shown)               # shown straight away
        self.reload_to()
        shown = {c["ref"]: c for c in self.card()}
        self.assertTrue(shown[f"images/{name}"]["w"] > 0, shown)               # and after reloading the page
        self.assertEqual(self.b.errors, [])

    def test_editing_the_text_keeps_every_image_name_and_every_link(self):
        """The page shows dates as DD-MM-YYYY; a date inside an image path or a link is not a date."""
        mem = self.memory()
        pic = mem.parent / "images" / "2026-10-05-plan-view.png"
        pic.write_bytes(png(200, 100, (10, 90, 160)))
        mem.write_text(mem.read_text().replace("![Delivery plan](images/plan.png)",
                                               "![Plan view](images/2026-10-05-plan-view.png)\n\n"
                                               "[Board pack](https://example.com/2026-10-05/pack.pdf) is the source."))
        self.v.run(script="build_dashboard.py")
        self.b.reload()
        self.b.wait("typeof go==='function' && LIVE")
        self.open_editor()
        self.b.click("#curEd p")
        self.b.type(" Edited.")
        self.assertIn("— saved", self.save())
        md = self.current_md()
        self.assertIn("![Plan view](images/2026-10-05-plan-view.png)", md)
        self.assertIn("(https://example.com/2026-10-05/pack.pdf)", md)
        self.assertNotIn("05-10-2026-plan-view", md)
        self.reload_to()
        shown = {c["ref"]: c for c in self.card()}
        self.assertTrue(shown["images/2026-10-05-plan-view.png"]["w"] > 0, shown)

    def test_a_removed_image_stays_removed(self):
        self.open_editor()
        self.b.click('#curEd figure[data-ref="images/plan.png"] .cimgdel')
        self.assertIn("— saved", self.save())
        self.assertNotIn("images/plan.png", self.current_md())               # not put back at the end
        self.assertIn("plan.png", self.images())                              # the file is never deleted
        self.reload_to()
        self.assertNotIn("images/plan.png", [c["ref"] for c in self.card()])

    def test_the_editor_can_be_used_in_every_theme_and_mode_in_a_small_window(self):
        b = self.b
        b.resize(560, 800)
        for pal in TEST_PALETTES:
            for mode in ("Light", "Dark"):
                b.eval(f"S.palette={json.dumps(pal)}; S.theme={json.dumps(mode)}; applyTheme()")
                self.open_editor()
                self.add_image(self.pic("small.png", png(60, 40, (9, 99, 9))), "Small")
                b.wait("[...document.querySelectorAll('#curEd figure.cimg img')].every(i=>i.complete&&i.naturalWidth>0)", 5)   # #152: laid out at its size before anything is measured
                for sel in ('[data-rc="image"]', '[data-rc="bold"]', "#curEd figure.cimg .cimgdel", '[data-cure="cancel"]', '[data-cure="save"]'):
                    b.click(sel) if sel in ('[data-rc="bold"]',) else self.assertTrue(b.box(sel), f"{sel} is not visible in {pal} {mode}")
                self.cancel_asks(f"{pal} {mode}, 560x800")                          # a change was made: asks first
                b.click('#discardBar [data-dis="go"]')
                b.wait("!document.getElementById('curEd')", 3)
        self.assertEqual(b.errors, [])

    def test_a_drafted_text_keeps_the_images_it_does_not_mention(self):
        b = self.b
        self.open_editor()
        b.eval("genDraft('ABC','A fresh draft with no pictures. {F1}','tracker')")
        b.wait("document.getElementById('curEd').innerText.includes('A fresh draft')", 3)
        self.assertIn("— saved", self.save())
        self.assertIn("A fresh draft with no pictures.", self.current_md())
        self.assertIn("images/plan.png", self.current_md())               # not lost: a drafted text didn't take it out

    def test_png_and_jpeg_both_work_and_a_jpeg_is_filed_as_jpg(self):
        self.open_editor()
        self.add_image(self.pic("photo.jpeg", JPEG), "Site photo")
        self.add_image(self.pic("Chart.PNG", png(120, 80, (20, 20, 20))), "Chart")
        self.assertIn("— saved", self.save())
        self.assertEqual([n for n in self.images() if n.startswith(TODAY)], [f"{TODAY}-chart.png", f"{TODAY}-site-photo.jpg"])
        self.reload_to()
        shown = {c["cap"]: c for c in self.card()}
        self.assertTrue(shown["Site photo"]["w"] > 0 and shown["Chart"]["w"] > 0, shown)

    def test_two_images_with_the_same_name_are_both_kept(self):
        self.open_editor()
        self.add_image(self.pic("same.png", png(100, 60, (1, 2, 3))), "Same")
        self.add_image(self.pic("same-2.png", png(110, 60, (3, 2, 1))), "Same")
        self.assertIn("— saved", self.save())
        self.assertEqual([n for n in self.images() if n.startswith(TODAY)], [f"{TODAY}-same-2.png", f"{TODAY}-same.png"])
        self.assertEqual(len(re.findall(rf"images/{TODAY}-same(-2)?\.png", self.current_md())), 2)
        # a second save, later, with the same caption again: a third name, never an overwrite
        self.open_editor()
        self.add_image(self.pic("same-3.png", png(90, 60, (9, 9, 9))), "Same")
        self.assertIn("— saved", self.save())
        self.assertEqual(len([n for n in self.images() if n.startswith(f"{TODAY}-same")]), 3)

    def test_a_project_with_no_images_folder_gets_one(self):
        folder = next((self.v.root / "projects").glob("DEF *"))
        (folder / "CLAUDE.md").write_text("# DEF — Digital Enablement\n\n## Brief\n\n- **Client / partner:** Example\n"
                                          "- **Client report rhythm:** weekly\n\n## Current state\n\nPilot is planned.\n")
        self.v.run(script="build_dashboard.py")
        self.b.reload()
        self.b.wait("typeof go==='function' && LIVE")
        self.assertFalse((folder / "images").exists())
        self.open_editor("DEF")
        self.add_image(self.pic("first.png", png(80, 80, (5, 5, 5))), "First")
        self.assertIn("— saved", self.save())
        self.assertEqual(self.images("DEF"), [f"{TODAY}-first.png"])
        self.reload_to("DEF")
        self.assertTrue(self.card()[0]["w"] > 0)

    def test_a_project_without_a_memory_file_says_so_and_keeps_the_work(self):
        self.open_editor("DEF")                                           # the demo's DEF has no CLAUDE.md
        self.b.click("#curEd p")
        self.b.type("Some words.")
        self.add_image(self.pic("lost.png", png(40, 40, (4, 4, 4))), "Lost")
        msg = self.save()
        self.assertIn("Can't read", msg)
        self.assertTrue(self.b.eval("!!document.getElementById('curEd')"))
        self.assertIn("Some words.", self.b.eval("document.getElementById('curEd').innerText"))
        self.assertEqual(self.b.eval("document.querySelectorAll('#curEd figure.cimg').length"), 1)
        self.assertEqual(list((self.v.root / "system/staging/uploads").glob("*")), [])    # the staged picture was taken away again

    def test_files_that_are_not_png_or_jpeg_give_a_plain_message(self):
        self.open_editor()
        figs = self.b.eval("document.querySelectorAll('#curEd figure').length")
        for name, data in (("anim.gif", b"GIF89a" + b"\x00" * 40), ("pic.webp", b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"\x00" * 20),
                           ("IMG_0001.HEIC", b"\x00\x00\x00\x18ftypheic" + b"\x00" * 30), ("notes.pdf", b"%PDF-1.4")):
            self.b.eval("document.getElementById('snackT').textContent=''")
            self.b.set_files("#curImgFile", [self.pic(name, data)])
            msg = self.b.wait("document.getElementById('snackT').textContent", 3)
            self.assertEqual(msg, f"{name} can't be added: only PNG or JPEG images")      # names the file
        self.assertEqual(self.b.eval("document.querySelectorAll('#curEd figure').length"), figs)   # nothing added

    def test_a_picture_that_says_png_but_is_not_one_is_refused_and_the_text_is_kept(self):
        self.open_editor()
        self.b.click("#curEd p")
        self.b.type(" My unsaved words.")
        self.add_image(self.pic("really-a-gif.png", b"GIF89a" + b"\x00" * 40), "Fake")
        msg = self.save()
        self.assertIn("Only PNG or JPEG", msg)
        self.assertTrue(self.b.eval("!!document.getElementById('curEd')"))                          # still editing
        self.assertIn("My unsaved words.", self.b.eval("document.getElementById('curEd').innerText"))
        self.assertEqual([n for n in self.images() if n.startswith(TODAY)], [])
        self.assertEqual(list((self.v.root / "system/staging/uploads").glob("*")), [])              # no stray upload

    def test_an_image_over_two_megabytes_is_refused_with_a_message(self):
        self.open_editor()
        figs = self.b.eval("document.querySelectorAll('#curEd figure').length")
        self.b.set_files("#curImgFile", [self.pic("Huge screenshot.png", big_png(2 * 1024 * 1024 + 1000))])
        self.assertEqual(self.b.wait("document.getElementById('snackT').textContent", 5),
                         "Huge screenshot.png is over 2 MB: images can be 2 MB at most (keeps the dashboard small)")
        self.assertEqual(self.b.eval("document.querySelectorAll('#curEd figure').length"), figs)

    def test_cancel_and_escape_ask_before_discarding(self):
        b = self.b
        before = self.memory().read_text()
        self.open_editor()
        b.click('[data-cure="cancel"]')                                  # nothing changed: closes at once
        b.wait("!document.getElementById('curEd')", 3)
        self.open_editor()
        b.click("#curEd p")
        b.type(" Changed.")
        b.click('[data-cure="cancel"]')                                  # changed: asks first
        self.assertTrue(b.wait("document.getElementById('discardBar').classList.contains('on')", 3))
        b.click('#discardBar [data-dis="keep"]')
        self.assertTrue(b.eval("!!document.getElementById('curEd')"))
        self.assertIn("Changed.", b.eval("document.getElementById('curEd').innerText"))
        b.click('[data-cure="cancel"]')
        b.click('#discardBar [data-dis="go"]')
        b.wait("!document.getElementById('curEd')", 3)
        self.assertNotIn("Changed.", b.eval("document.getElementById('curText').innerText"))
        self.assertEqual(self.memory().read_text(), before)              # nothing was written
        self.open_editor()                                               # Esc in a caption does the same
        self.add_image(self.pic("c.png", png(50, 50, (1, 1, 1))), "Cap")
        b.key("Escape")
        self.assertTrue(b.wait("document.getElementById('discardBar').classList.contains('on')", 3))

    def test_leaving_the_page_with_unsaved_changes_asks_first(self):
        b = self.b
        self.open_editor()
        b.click("#curEd p")
        b.type(" Unsaved.")
        b.click('.rail button[data-v="today"]')
        self.assertTrue(b.wait("document.getElementById('discardBar').classList.contains('on')", 3))
        self.assertEqual(b.eval("VIEW"), "cockpit")                       # it has not left yet
        b.click('#discardBar [data-dis="keep"]')
        self.assertTrue(b.eval("!!document.getElementById('curEd')"))

    def test_undo_puts_back_the_text_and_takes_the_image_away(self):
        before = self.memory().read_text()
        self.open_editor()
        self.add_image(self.pic("undo-me.png", png(60, 60, (7, 7, 7))), "Undo me")
        self.assertIn("— saved", self.save())
        self.assertIn(f"{TODAY}-undo-me.png", self.images())
        self.b.click("#snackU")
        self.b.wait("/undone|Undone|undid/i.test(document.getElementById('snackT').textContent)", 10)
        self.assertEqual(self.memory().read_text(), before)
        self.assertNotIn(f"{TODAY}-undo-me.png", self.images())

    def test_saving_with_the_server_stopped_keeps_the_text_and_says_so(self):
        b = self.b
        self.open_editor()
        b.click("#curEd p")
        b.type(" Words I must not lose.")
        self.proc.terminate()
        self.proc.wait(timeout=10)
        b.eval("setLive(false)")
        b.click('[data-cure="save"]')
        time.sleep(1.0)
        self.assertTrue(b.eval("!!document.getElementById('curEd')"), "the editor closed and the text was lost")
        self.assertIn("Words I must not lose.", b.eval("document.getElementById('curEd').innerText"))
        self.assertIn("Not saved", b.eval("document.getElementById('snackT').textContent"))             # and says so


if __name__ == "__main__":
    unittest.main()
