"""A small real-browser driver: Google Chrome over the DevTools protocol, standard library only.

Why: the dashboard tests that load a page with `--dump-dom` can't click, can't use a file chooser and can't wait for a
real server (virtual time doesn't advance real I/O). BL-76 and BL-77 need a person's path: real mouse clicks, a real
file chosen from disk, and the live server answering. This drives one headless Chrome tab.

    with Browser() as b:
        b.goto("http://127.0.0.1:8765/")
        b.click("#v-today .btn")
        b.set_files("#curImgFile", ["/path/to/pic.png"])
        b.eval("document.title")

Only for tests and development; nothing at run time uses it.
"""
import base64
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import proc_guard  # noqa: E402

MAC_CHROME_PATHS = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"]


def chrome_path():
    """The one way the tests find a browser: CREAITE_CHROME, then google-chrome / chromium / chromium-browser on the
    PATH (Linux, the release check), then the macOS app paths. None if there isn't one."""
    env = os.environ.get("CREAITE_CHROME")
    if env and os.path.exists(env):
        return env
    for name in ("google-chrome", "chromium", "chromium-browser"):
        found = shutil.which(name)
        if found:
            return found
    return next((p for p in MAC_CHROME_PATHS if os.path.exists(p)), None)


class WebSocket:
    """Just enough RFC 6455 for one local DevTools connection: text frames, masked, fragments joined."""

    def __init__(self, url):
        host, rest = url[len("ws://"):].split("/", 1)
        h, p = host.split(":")
        self.sock = socket.create_connection((h, int(p)), timeout=30)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((f"GET /{rest} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                           f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("DevTools closed the connection during the handshake")
            buf += chunk
        if b" 101 " not in buf.split(b"\r\n", 1)[0]:
            raise ConnectionError(buf.split(b"\r\n", 1)[0].decode())
        self.rest = buf.split(b"\r\n\r\n", 1)[1]

    def send(self, text):
        data = text.encode()
        head = bytearray([0x81])
        n = len(data)
        if n < 126:
            head.append(0x80 | n)
        elif n < 65536:
            head += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            head += bytes([0x80 | 127]) + struct.pack(">Q", n)
        mask = os.urandom(4)
        self.sock.sendall(bytes(head) + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def _read(self, n):
        while len(self.rest) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("DevTools closed the connection")
            self.rest += chunk
        out, self.rest = self.rest[:n], self.rest[n:]
        return out

    def recv(self):
        message = b""
        while True:
            b1, b2 = self._read(2)
            n = b2 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._read(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._read(8))[0]
            payload = self._read(n)
            if b1 & 0x0F in (1, 0):
                message += payload
                if b1 & 0x80:
                    return message.decode()
            elif b1 & 0x0F == 8:
                raise ConnectionError("DevTools closed the page")

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


class Browser:
    def __init__(self, width=1280, height=900, args=(), reduced_motion=True):
        path = chrome_path()
        if not path:
            raise RuntimeError("Google Chrome (or Edge) isn't installed")
        self.profile = tempfile.mkdtemp(prefix="creaite-cdp-")
        try:                                   # BL-172 (sprint-polish-2): a start that fails part-way removes its own profile
            self._start(path, width, height, args, reduced_motion)
        except BaseException:
            self.close()
            raise

    def _start(self, path, width, height, args, reduced_motion):
        self.proc = proc_guard.spawn(          # BL-247: its own process group, with a watchdog
            [path, "--headless=new", "--disable-gpu", f"--user-data-dir={self.profile}", "--remote-debugging-port=0",
             "--no-first-run", "--no-default-browser-check", "--disable-component-update", "--disable-background-networking",
             # ci-macos-hang: on a Mac with no unlocked login keychain (a CI runner, a fresh HOME) Chrome waits on the keychain
             # and Page.navigate never answers; a mock keychain is what Puppeteer and Playwright use there (ignored elsewhere)
             "--use-mock-keychain",
             # headless Chrome on Linux has no pointing device and reports (hover: none), so hover popups stood down on CI
             # (the hover standard stands down on it); say a mouse is attached. The touch tests fire touch events or fake matchMedia
             "--blink-settings=primaryHoverType=2,availableHoverTypes=2,primaryPointerType=4,availablePointerTypes=4",
             f"--window-size={width},{height}", *args, "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        port_file = os.path.join(self.profile, "DevToolsActivePort")
        for _ in range(100):
            if os.path.exists(port_file) and self._port_text(port_file).count("\n") >= 1:
                break
            time.sleep(0.1)
        else:
            self.close()
            raise RuntimeError("Chrome didn't start")
        self.port = int(self._port_text(port_file).split("\n")[0])
        tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json"))
        self.ws = WebSocket(next(t for t in tabs if t["type"] == "page")["webSocketDebuggerUrl"])
        self.n = 0
        self.events = []
        self.errors = []
        for domain in ("Page", "Runtime", "DOM", "Network"):
            self.call(f"{domain}.enable")
        # BL-136: tests and screenshots run with reduced motion, so nothing they check is caught mid-animation. A test of the
        # motion itself turns it back on: call("Emulation.setEmulatedMedia", features=[{"name": "prefers-reduced-motion", ...}]).
        if reduced_motion:
            self.call("Emulation.setEmulatedMedia", features=[{"name": "prefers-reduced-motion", "value": "reduce"}])

    @staticmethod
    def _port_text(path):
        with open(path) as f:
            return f.read()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        if getattr(self, "ws", None):
            self.ws.close()
        proc, self.proc = getattr(self, "proc", None), None
        proc_guard.stop(proc)                  # BL-247: Chrome and all its helpers
        for _ in range(3):                     # BL-172: Chrome's helpers can still be writing as it exits; try again briefly
            shutil.rmtree(self.profile, ignore_errors=True)
            if not os.path.exists(self.profile):
                break
            time.sleep(0.2)

    def call(self, method, **params):
        self.n += 1
        mine = self.n
        self.ws.send(json.dumps({"id": mine, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mine:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error'].get('message')}")
                return msg.get("result", {})
            self._note(msg)

    def _note(self, msg):
        self.events.append(msg)
        if msg.get("method") == "Runtime.exceptionThrown":
            d = msg["params"]["exceptionDetails"]
            self.errors.append((d.get("exception") or {}).get("description") or d.get("text"))
        elif msg.get("method") == "Runtime.consoleAPICalled" and msg["params"]["type"] == "error":
            self.errors.append(" ".join(str(a.get("value", a.get("description", ""))) for a in msg["params"]["args"]))

    def pump(self, seconds=0.05):
        """Read whatever events are waiting, for up to `seconds`."""
        self.ws.sock.settimeout(seconds)
        try:
            while True:
                self._note(json.loads(self.ws.recv()))
        except (socket.timeout, TimeoutError):
            pass
        finally:
            self.ws.sock.settimeout(30)

    def eval(self, js, wait=True):
        """Run JavaScript in the page and return its value (awaiting a promise if `wait`)."""
        r = self.call("Runtime.evaluate", expression=js, awaitPromise=wait, returnByValue=True, userGesture=True)
        if "exceptionDetails" in r:
            d = r["exceptionDetails"]
            raise RuntimeError((d.get("exception") or {}).get("description") or d.get("text"))
        return r["result"].get("value")

    def goto(self, url, wait_for="document.readyState==='complete'", timeout=20):
        self.call("Page.navigate", url=url)
        self.wait(wait_for, timeout)

    def reload(self, wait_for="document.readyState==='complete'", timeout=20):
        self.call("Page.reload", ignoreCache=True)
        time.sleep(0.3)
        self.wait(wait_for, timeout)

    def wait(self, js, timeout=10, every=0.05):
        """Poll until `js` is truthy; return its value, or raise with the page's last errors."""
        end = time.time() + timeout
        last = None
        while time.time() < end:
            try:
                last = self.eval(f"(()=>{{ const v=({js}); return v&&v.nodeType?true:v; }})()", wait=False)   # an element counts as true
            except RuntimeError:
                last = None
            if last:
                return last
            self.pump(every)
        raise TimeoutError(f"timed out waiting for: {js}\npage errors: {self.errors[-3:]}\n{self._where()}")

    WHERE_JS = """(()=>{ const a=document.activeElement, s=getSelection();
      const name=a?a.tagName+(a.id?'#'+a.id:'')+(a.className?'.'+String(a.className).split(' ')[0]:''):null;
      return {platform:navigator.platform, hasFocus:document.hasFocus(), visibility:document.visibilityState, active:name,
              selection:s?{type:s.type, len:String(s).length}:null}; })()"""

    def _where(self):
        """One line of where the page is, for a timeout: platform, focus, visibility, the active element and the selection."""
        try:
            return "page state: " + json.dumps(self.eval(self.WHERE_JS, wait=False))
        except Exception as e:                        # the page may be gone; a timeout still reports what it was waiting for
            return f"page state unavailable ({type(e).__name__})"

    def box(self, selector):
        """The centre of the first element matching `selector`, scrolled into view, or None."""
        return self.eval("""(()=>{ const e=document.querySelector(%s); if(!e) return null; e.scrollIntoView({block:"center",inline:"center"});
          const r=e.getBoundingClientRect(); return r.width&&r.height?{x:r.left+r.width/2,y:r.top+r.height/2}:null; })()""" % json.dumps(selector))

    def click(self, selector, button="left", count=1, modifiers=0):
        """A real mouse click at the element's centre (not element.click()), so overlays and hit-testing count.
        modifiers is Chrome's bit mask: Alt 1, Ctrl 2, Command 4, Shift 8."""
        self.wait(f"!!({json.dumps(selector)} && document.querySelector({json.dumps(selector)}))", 10)
        pos = self.box(selector)
        if not pos:
            raise RuntimeError(f"can't click {selector}: it has no size (hidden?)")
        hit = self.eval("""(()=>{ const e=document.elementFromPoint(%f,%f), t=document.querySelector(%s); return !!(e&&t&&(t===e||t.contains(e)||e.contains(t))); })()""" % (pos["x"], pos["y"], json.dumps(selector)))
        if not hit:
            raise RuntimeError(f"can't click {selector}: something else is on top of it")
        for kind in ("mouseMoved", "mousePressed", "mouseReleased"):
            self.call("Input.dispatchMouseEvent", type=kind, x=pos["x"], y=pos["y"], button=button, clickCount=count, modifiers=modifiers)
        self.pump(0.05)

    def drag(self, from_selector, to_selector, steps=8, release=True, offset=(0, 0)):
        """A real press, move and release with the mouse button held (pointer events, not a synthesised drop): from the centre of one
        element to the centre of another (plus `offset`). With release=False it stops over the target, button still down, so a
        test can look at the drag in progress; finish it with mouse_up()."""
        rect = """(s=>{ const e=document.querySelector(s); if(!e) return null; const r=e.getBoundingClientRect();
          return r.width&&r.height&&r.top>=0&&r.bottom<=innerHeight&&r.left>=0&&r.right<=innerWidth?{x:r.left+r.width/2,y:r.top+r.height/2}:null; })(%s)"""
        b = self.box(to_selector)                                  # scroll the target into view first, then look at both without moving the page
        a = self.eval(rect % json.dumps(from_selector))
        if a is None:
            a = self.box(from_selector)
            b = self.eval(rect % json.dumps(to_selector))
        if not a or not b:
            raise RuntimeError(f"can't drag {from_selector} to {to_selector}: one has no size or they can't both be on screen")
        self.call("Input.dispatchMouseEvent", type="mouseMoved", x=a["x"], y=a["y"], button="none")
        self.call("Input.dispatchMouseEvent", type="mousePressed", x=a["x"], y=a["y"], button="left", buttons=1, clickCount=1)
        for i in range(1, steps + 1):
            x = a["x"] + (b["x"] + offset[0] - a["x"]) * i / steps
            y = a["y"] + (b["y"] + offset[1] - a["y"]) * i / steps
            self.call("Input.dispatchMouseEvent", type="mouseMoved", x=x, y=y, button="left", buttons=1)
            self.pump(0.01)
        self._drag_at = (b["x"] + offset[0], b["y"] + offset[1])
        if release:
            self.mouse_up()

    def mouse_up(self):
        x, y = self._drag_at
        self.call("Input.dispatchMouseEvent", type="mouseReleased", x=x, y=y, button="left", buttons=0, clickCount=1)
        self.pump(0.05)

    def type(self, text):
        """Type into whatever has focus, one key at a time (so input events fire as for a person)."""
        for ch in text:
            if ch == "\n":
                self.key("Enter")
            else:
                self.call("Input.dispatchKeyEvent", type="keyDown", text=ch)
                self.call("Input.dispatchKeyEvent", type="keyUp")
        self.pump(0.05)

    def key(self, name, modifiers=0):
        """modifiers: 1 Alt, 2 Control, 4 Meta (Command), 8 Shift."""
        codes = {"Enter": 13, "Escape": 27, "Backspace": 8, "Tab": 9, "ArrowLeft": 37, "ArrowUp": 38, "ArrowRight": 39,
                 "ArrowDown": 40, "Delete": 46, "Home": 36, "End": 35, "PageUp": 33, "PageDown": 34}
        code = codes.get(name) or ord(name.upper())
        if name.lower() in ("a", "z", "y") and modifiers & 4 and not self.is_mac():
            modifiers = (modifiers & ~4) | 2                # ⌘A, ⌘Z, ⇧⌘Z are Control+A, +Z, +⇧Z elsewhere (Chrome on Linux)
        base = {"key": name if len(name) > 1 else name, "windowsVirtualKeyCode": code, "modifiers": modifiers}
        text = "\r" if name == "Enter" else None
        self.call("Input.dispatchKeyEvent", type="keyDown", **base, **({"text": text} if text else {}))
        self.call("Input.dispatchKeyEvent", type="keyUp", **base)
        self.pump(0.05)

    def is_mac(self):
        """True when this Chrome reports a Mac (its shortcuts use ⌘); read once from the page."""
        if getattr(self, "_mac", None) is None:
            self._mac = bool(self.eval("/Mac/i.test(navigator.platform)"))
        return self._mac

    def set_files(self, selector, files):
        """Choose real files on disk in an <input type=file>, as the file chooser would."""
        root = self.call("DOM.getDocument", depth=0)["root"]["nodeId"]
        node = self.call("DOM.querySelector", nodeId=root, selector=selector)["nodeId"]
        if not node:
            raise RuntimeError(f"no file input matches {selector}")
        self.call("DOM.setFileInputFiles", nodeId=node, files=[str(f) for f in files])   # Chrome fires input and change itself
        self.pump(0.2)

    def resize(self, width, height=900):
        """Make the page this size (a small window)."""
        self.call("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=1, mobile=False)

    def screenshot(self, path):
        with open(path, "wb") as f:
            f.write(base64.b64decode(self.call("Page.captureScreenshot", format="png")["data"]))
