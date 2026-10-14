"""BL-100: paste, drop or attach an image in ask creaite.

Run: python3 dev/tests/test_ask_images.py   (the browser part needs Google Chrome; skipped otherwise)
The server runs in a throwaway vault with a stand-in `claude` (CREAITE_CLAUDE) that repeats the message it was given, so no
real Claude call is made.
"""
import base64
import json
import os
import re
import struct
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase, free_port  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_tracker import Vault  # noqa: E402

FAKE = r'''#!/usr/bin/env python3
import json, sys
args = sys.argv[1:]
message = args[args.index("-p") + 1]
allowed = args[args.index("--allowedTools") + 1].split(",")
disallowed = args[args.index("--disallowedTools") + 1].split(",")
system = args[args.index("--append-system-prompt") + 1]
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": "sess-img-%d" % (abs(hash(message)) % 10**6)})
if "echo flags" in message:
    text = "FLAGS " + json.dumps({"allowed": allowed, "disallowed": disallowed, "prompt": system})
else:
    text = "SEEN " + message
out({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}})
out({"type": "result", "session_id": "sess-img-%d" % (abs(hash(message)) % 10**6), "result": text})
'''


def png(w=2, h=2):
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + b"\xff\x00\x00" * w for _ in range(h))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 60


def events(resp):
    out = []
    for raw in resp:
        line = raw.decode().strip()
        if line.startswith("data: "):
            out.append(json.loads(line[6:]))
    return out


class ServerCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = v = Vault()
        populate(v)
        fake = v.root / "fake_claude.py"
        fake.write_text(FAKE)
        fake.chmod(0o755)
        cls.port = free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.proc = subprocess.Popen([sys.executable, str(v.root / "system/scripts/live_server.py")],
                                    env={**os.environ, "CREAITE_PORT": str(cls.port), "CREAITE_CLAUDE": str(fake)},
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            try:
                urllib.request.urlopen(cls.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        html = urllib.request.urlopen(cls.base + "/").read().decode()
        cls.token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]
        cls.uploads = v.root / "system/staging/uploads/ask"

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.v.cleanup()

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def up(self, raw):
        return self.post("/api/ask/image", {"data": base64.b64encode(raw).decode()})

    def ask(self, message, **extra):
        req = urllib.request.Request(self.base + "/api/ask", data=json.dumps({"message": message, **extra}).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, events(r)
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def test_png_and_jpeg_are_stored_by_id(self):
        s, r = self.up(png())
        self.assertEqual(s, 200)
        self.assertRegex(r["id"], r"^[0-9a-f]{16}$")
        self.assertTrue((self.uploads / f"{r['id']}.png").is_file())
        s, r2 = self.up(JPEG)
        self.assertTrue((self.uploads / f"{r2['id']}.jpg").is_file())

    def test_other_types_bad_data_and_big_images_are_refused(self):
        for raw in (b"GIF89a....", b"%PDF-1.4 ...", b"plain text", b""):
            self.assertEqual(self.up(raw)[0], 415, raw)
        self.assertEqual(self.post("/api/ask/image", {"data": "not base64!!"})[0], 400)
        big = png() + b"\0" * (2 * 1024 * 1024)
        self.assertEqual(self.up(big)[0], 413)
        self.assertEqual(self.up(b"\xff\xd8\xff" + b"\0" * (2 * 1024 * 1024 - 3))[0], 200)       # exactly the limit is fine
        self.assertEqual(self.up(b"\xff\xd8\xff" + b"\0" * (2 * 1024 * 1024 - 2))[0], 413)

    def test_a_message_tells_claude_to_read_the_image_and_the_chat_keeps_it(self):
        _, a = self.up(png())
        _, b = self.up(JPEG)
        status, ev = self.ask("what is this?", images=[a["id"], b["id"]])
        text = " ".join(e["text"] for e in ev if e["type"] == "text")
        self.assertIn(f"The user attached an image: system/staging/uploads/ask/{a['id']}.png; read it", text)
        self.assertIn(f"The user attached an image: system/staging/uploads/ask/{b['id']}.jpg; read it", text)
        done = next(e for e in ev if e["type"] == "done")
        chat = self.post("/api/chat", {"chat": done["chat"]})[1]
        you = chat["messages"][0]
        self.assertEqual((you["text"], you["images"]), ("what is this?", [a["id"], b["id"]]))     # the instruction line isn't shown as Alan's words
        self.assertEqual(self.post("/api/ask/image/remove", {"id": a["id"]})[1]["ok"], False)     # it belongs to a chat now
        self.assertTrue((self.uploads / f"{a['id']}.png").is_file())

    def test_no_more_than_four_and_only_uploaded_ones(self):
        ids = [self.up(png())[1]["id"] for _ in range(5)]
        self.assertEqual(self.ask("too many", images=ids)[0], 400)
        self.assertEqual(self.ask("not uploaded", images=["0123456789abcdef"])[0], 400)
        self.assertEqual(self.ask("path trick", images=["../../tracker"])[0], 400)
        self.assertEqual(self.ask("four", images=ids[:4])[0], 200)

    def test_get_returns_the_image_and_remove_takes_back_an_unsent_one(self):
        _, a = self.up(png(3, 3))
        r = self.post("/api/ask/image/get", {"id": a["id"]})[1]
        self.assertEqual((r["type"], base64.b64decode(r["data"])), ("image/png", png(3, 3)))
        self.assertEqual(self.post("/api/ask/image/get", {"id": "../../CLAUDE"})[0], 404)
        self.assertTrue(self.post("/api/ask/image/remove", {"id": a["id"]})[1]["ok"])
        self.assertFalse((self.uploads / f"{a['id']}.png").exists())
        self.assertEqual(self.post("/api/ask/image/get", {"id": a["id"]})[0], 404)

    def test_the_folder_is_read_only_for_the_page_and_for_claude(self):
        _, a = self.up(png())
        rel = f"system/staging/uploads/ask/{a['id']}.png"
        self.assertTrue(self.post("/api/fs", {"op": "exists", "path": rel})[1]["exists"])
        for op in ("write", "append", "remove", "upload"):
            self.assertEqual(self.post("/api/fs", {"op": op, "path": rel, "text": "x", "data": ""})[0], 403, op)
        self.assertEqual(self.post("/api/fs", {"op": "write", "path": "system/staging/uploads/ask/new.png", "text": "x"})[0], 403)
        self.assertTrue((self.uploads / f"{a['id']}.png").is_file())
        ev = self.ask("echo flags")[1]
        flags = json.loads(next(e["text"] for e in ev if e["type"] == "text").replace("SEEN ", "").replace("FLAGS ", ""))
        self.assertIn("Read(system/staging/uploads/ask/**)", flags["allowed"])
        for rule in ("Write(system/staging/uploads/ask/**)", "Edit(system/staging/uploads/ask/**)"):
            self.assertIn(rule, flags["disallowed"])
        self.assertIn("for discussion", flags["prompt"])

    def test_an_image_that_never_reached_a_message_is_cleaned_up_after_a_day(self):
        _, old = self.up(png())
        f = self.uploads / f"{old['id']}.png"
        day = time.time() - 25 * 3600
        os.utime(f, (day, day))
        _, kept = self.up(png())
        self.assertFalse(f.exists())
        self.assertTrue((self.uploads / f"{kept['id']}.png").exists())

    def test_deleting_a_chat_deletes_its_images(self):
        first = None
        imgs = {}
        for n in range(11):
            _, a = self.up(png(n + 1, 1))
            _, ev = self.ask(f"chat number {n} unique {time.time()}", images=[a["id"]])
            chat = next(e for e in ev if e["type"] == "done")["chat"]
            imgs[chat] = a["id"]
            first = first or chat
            time.sleep(1.1)                                           # the history orders by second
        files = {p.stem for p in self.uploads.iterdir()}
        self.assertNotIn(imgs[first], files)                           # the oldest chat is pruned, and its image with it
        self.assertEqual(sum(1 for c, i in imgs.items() if i in files), 10)
        self.assertFalse((self.v.root / "system/staging/ask" / f"{first}.json").exists())


class BrowserCase(LiveBrowserCase):
    shared_server = True

    @classmethod
    def start_server(cls):
        cls.v = Vault()
        populate(cls.v)
        fake = cls.v.root / "fake_claude.py"
        fake.write_text(FAKE)
        fake.chmod(0o755)
        cls.port = free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.proc = subprocess.Popen([sys.executable, str(cls.v.root / "system/scripts/live_server.py")],
                                    env={**os.environ, "CREAITE_PORT": str(cls.port), "CREAITE_CLAUDE": str(fake)},
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                urllib.request.urlopen(cls.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)

    def setUp(self):
        super().setUp()
        self.b.eval("openChat()")
        self.b.wait("document.getElementById('chat').classList.contains('on')")

    FILE = """(w,h,type,name)=>new Promise(res=>{ const c=document.createElement('canvas'); c.width=w; c.height=h; const x=c.getContext('2d');
      for(let i=0;i<400;i++){ x.fillStyle='rgb('+(i*7%255)+','+(i*13%255)+','+(i*29%255)+')'; x.fillRect(Math.random()*w,Math.random()*h,w/8,h/8); }
      c.toBlob(b=>res(new File([b],name,{type})),type); })"""

    def paste(self, w=300, h=200, type_="image/png"):
        self.b.eval(f"""(async()=>{{ const f=await ({self.FILE})({w},{h},{type_!r},'shot.png'); const dt=new DataTransfer(); dt.items.add(f);
          document.getElementById('chIn').dispatchEvent(new ClipboardEvent('paste',{{clipboardData:dt,bubbles:true,cancelable:true}})); }})()""")

    def thumbs(self):
        return self.b.eval("document.querySelectorAll('#chThumbs .chthumb').length")

    def settled(self, n):
        self.b.wait(f"document.querySelectorAll('#chThumbs .chthumb').length==={n} && !document.querySelector('#chThumbs .chthumb.up')", 15)

    def stored(self):
        d = self.v.root / "system/staging/uploads/ask"
        return set(d.iterdir()) if d.is_dir() else set()

    def test_paste_shows_a_thumbnail_and_the_x_removes_it(self):
        before = self.stored()
        self.paste()
        self.settled(1)
        stored = self.stored() - before
        self.assertEqual(len(stored), 1)
        self.b.click("#chThumbs .chthumb .x")
        self.b.wait("document.querySelectorAll('#chThumbs .chthumb').length===0")
        time.sleep(0.5)
        self.assertEqual(self.stored() & stored, set())      # taken back from the server

    def test_attach_with_the_button_a_pasted_jpeg_and_the_limit_of_four(self):
        import tempfile
        d = Path(tempfile.mkdtemp())
        (d / "a.png").write_bytes(png(40, 30))
        self.b.set_files("#chFile", [d / "a.png"])
        self.settled(1)
        self.paste(type_="image/jpeg")
        self.settled(2)
        for _ in range(3):
            self.paste()
        self.b.wait("document.getElementById('snackT').textContent.includes('Up to 4')", 15)
        self.settled(4)

    def test_a_drop_works_and_other_files_are_refused(self):
        self.b.eval(f"""(async()=>{{ const f=await ({self.FILE})(120,90,'image/png','d.png'); const dt=new DataTransfer(); dt.items.add(f);
          document.getElementById('chat').dispatchEvent(new DragEvent('drop',{{dataTransfer:dt,bubbles:true,cancelable:true}})); }})()""")
        self.settled(1)
        self.b.eval("""(()=>{ const dt=new DataTransfer(); dt.items.add(new File(['x'],'a.gif',{type:'image/gif'}));
          document.getElementById('chIn').dispatchEvent(new ClipboardEvent('paste',{clipboardData:dt,bubbles:true,cancelable:true})); })()""")
        self.b.wait("document.getElementById('snackT').textContent.includes('Only PNG or JPEG')", 10)
        self.assertEqual(self.thumbs(), 1)

    def test_a_big_image_is_shrunk_before_it_is_uploaded(self):
        before = self.stored()
        self.paste(3200, 2400)
        self.settled(1)
        f = next(iter(self.stored() - before))
        self.assertLess(f.stat().st_size, 2 * 1024 * 1024)
        raw = f.read_bytes()
        if raw.startswith(b"\x89PNG"):
            w, h = struct.unpack(">II", raw[16:24])
            self.assertLessEqual(max(w, h), 1600)
            self.assertEqual((w, h), (1600, 1200))

    def test_sending_shows_the_thumbnails_in_the_bubble_and_the_history_and_a_larger_view(self):
        self.paste()
        self.settled(1)
        self.b.eval("document.getElementById('chIn').value='what do you see?'")
        self.b.eval("send()")
        self.b.wait("document.querySelectorAll('#chLog .msg.a').length>=2 || [...document.querySelectorAll('#chLog .msg.a')].some(m=>m.textContent.includes('SEEN'))", 30)
        self.b.wait("[...document.querySelectorAll('#chLog .msg.a')].some(m=>m.textContent.includes('The user attached an image'))", 30)
        self.assertEqual(self.thumbs(), 0)                                             # the strip is cleared on send
        self.assertEqual(self.b.eval("document.querySelectorAll('#chLog .msg.u .chthumb').length"), 1)
        self.b.wait("document.querySelector('#chLog .msg.u .chthumb').style.backgroundImage.includes('url')")
        self.b.click("#chLog .msg.u .chthumb")
        self.b.wait("document.getElementById('imgBig').classList.contains('on')")
        self.assertIn("data:image", self.b.eval("document.querySelector('#imgBig img').src"))
        self.b.click("#imgBig")
        self.b.wait("!document.getElementById('imgBig').classList.contains('on')")
        self.b.eval("newChat()")
        chat = self.b.eval("ASKCHAT") or None
        self.b.eval("IMGURL={}")                                                        # force a fresh fetch from the server
        chats = self.b.eval("api('/api/chats').then(r=>r.chats[0].chat)")
        self.b.eval(f"loadChat({chats!r})")
        self.b.wait("document.querySelectorAll('#chLog .msg.u .chthumb').length===1")
        self.b.wait("document.querySelector('#chLog .msg.u .chthumb').style.backgroundImage.includes('data:image')")


if __name__ == "__main__":
    unittest.main()
