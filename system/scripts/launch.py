#!/usr/bin/env python3
"""creaite launcher (BL-86): open creaite as an app window, starting the live server first if it isn't running. Standard library only.

  python3 system/scripts/launch.py                     start the live server if nothing answers on live_mode.port, then open
                                                       creaite in a Chrome app window (--app=…); the default browser if Chrome
                                                       isn't found
  python3 system/scripts/launch.py make-launcher [--where applications|vault] [--dest <folder>] [--replace]
                                                       make something to double-click: a small macOS app named creaite (with the
                                                       creaite icon) in ~/Applications, or creaite.command in the vault. Asks
                                                       nothing itself: cx-setup asks Alan first, because it is outside the vault.
                                                       BL-305: the development repository's is "creaite (dev)", DEV-marked, so
                                                       the two sit side by side; one that opens another vault is replaced only
                                                       with --replace
  python3 system/scripts/launch.py make-launcher --if-present
                                                       BL-320: make again only the launchers that already open this vault (in
                                                       ~/Applications, /Applications, or creaite.command in the vault); none: nothing
  python3 system/scripts/launch.py refresh-icon       BL-320: point the app's manifest at new icon addresses, so Chrome offers to
                                                       update its copy of the app's icon (writes system/staging/app-icon.json only)
  python3 system/scripts/launch.py restart            BL-320: ask this vault's running live server to restart (SIGUSR1); it
                                                       restarts once no job is running. Nothing running: nothing to do
  python3 system/scripts/launch.py agent install|remove|status [--json]
                                                       macOS only: a per-user LaunchAgent (~/Library/LaunchAgents, no admin) that
                                                       starts the live server at login and restarts it if it crashes. Alan runs
                                                       this himself in Terminal; ask creaite cannot (reach.py never list)

A server this script starts is told (CREAITE_LAUNCHED=1) to stop by itself 60 seconds after the last creaite window closes, never
in the middle of a job. A server Alan started in Terminal, or one already running, is left alone. The port is live_mode.port from
settings.json (the development repository uses 8766, a live vault 8765), or CREAITE_PORT, so two vaults can run side by side.
CREAITE_BROWSER names a browser to use instead of Chrome (tests use a stub).

The login agent starts live_server.py itself, without CREAITE_LAUNCHED, so that server never stops when a window closes (like one
started in Terminal); the launcher then finds it running and only opens the window. It lives outside the vault by design, holds
this vault's location and this Python, and is not part of the portable vault: say "agent install" again on a new machine.
CREAITE_AGENT_DIR (tests) replaces ~/Library/LaunchAgents; CREAITE_NO_LAUNCHCTL=1 (tests) writes the file without loading it.
"""
import hashlib
import json
import os
import plistlib
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

CHROME_PATHS = ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/usr/bin/google-chrome", "/usr/bin/chromium",
                "/usr/bin/chromium-browser", r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe")
LOG = paths.STAGING / "live-server.log"


def port():
    """The live server's port: CREAITE_PORT, else live_mode.port in settings (default 8765)."""
    env = os.environ.get("CREAITE_PORT")
    return int(env) if env else int(paths.load_settings().get("live_mode", {}).get("port", 8765))


# ===== BL-212 (sprint-ui-audit) =====
def vault_mark():
    """This vault's fingerprint, as live_server.vault_mark works it out (the two must agree): /health no longer names the
    vault, so the launcher asks whether the server is its own."""
    return hashlib.sha256(str(paths.ROOT.resolve()).encode()).hexdigest()[:16]


def health(p):
    """"this" if this vault's server answers on the port, "other" if another creaite vault's does, None if nothing creaite does."""
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{p}/health", headers={"X-Creaite-Vault": vault_mark()})
        with urllib.request.urlopen(req, timeout=1) as r:
            data = json.loads(r.read())
        if not data.get("ok"):
            return None
        if "vault" in data:                                  # a server from before 1.6.0 still names its vault
            return "this" if data["vault"] == paths.ROOT.name else "other"
        return "other" if data.get("this_vault") is False else "this"
    except (OSError, ValueError):
        return None
# ===== end BL-212 =====


def find_chrome():
    """The Chrome, Chromium or Edge program to open the app window with (CREAITE_BROWSER overrides), or None."""
    env = os.environ.get("CREAITE_BROWSER")
    if env:
        return env if Path(env).exists() or shutil.which(env) else None
    for c in CHROME_PATHS:
        if Path(c).exists():
            return c
    return shutil.which("google-chrome") or shutil.which("chromium")


def start_server(p):
    """Start live_server.py on port `p`, detached, logging to system/staging/live-server.log, and wait up to
    15 seconds for it to answer. Marked CREAITE_LAUNCHED, so it stops after the last window closes (BL-86).
    """
    LOG.parent.mkdir(parents=True, exist_ok=True)
    log = open(LOG, "ab")
    env = {**os.environ, "CREAITE_PORT": str(p), "CREAITE_LAUNCHED": "1"}
    kw = {"start_new_session": True} if os.name != "nt" else {"creationflags": 0x00000008 | 0x00000200}   # detached from this window
    proc = subprocess.Popen([sys.executable, str(Path(__file__).resolve().parent / "live_server.py")], cwd=paths.ROOT, env=env,
                            stdin=subprocess.DEVNULL, stdout=log, stderr=log, **kw)
    for _ in range(150):                                                 # up to 15 seconds
        if health(p):
            return True
        if proc.poll() is not None:                                      # BL-329: 0 is "this vault's server was already there"
            return proc.returncode == 0 and health(p) == "this"
        time.sleep(0.1)
    return False


def launch():
    """Start the live server if it isn't running, then open the dashboard in a Chrome app window (BL-86)."""
    p = port()
    seen = health(p)
    starting = None if seen else server_starting(p)
    if starting:                                                         # BL-329: a server is starting: wait for it, start no other
        print(f"The live server is starting on port {p}; waiting for it…")
        seen = wait_for_server(p, pid=starting[0])
    if seen == "other":
        print(f"Port {p} is in use by another creaite vault. Change live_mode.port in this vault's settings, "
              "or stop the other server.")
        return 1
    if seen:
        print(f"The live server is already running on port {p}.")
        if starting and starting[2]:                                     # the launch that started it opens the window
            print("creaite is opening in the window that launch opens.")
            return 0
    else:
        print(f"Starting the live server on port {p}…")
        if not start_server(p):
            print(f"The live server didn't start. See {paths.rel(LOG)}, or run system/scripts/run live_server.py in Terminal.")
            return 1
        print("It stops by itself a minute after the last creaite window closes.")
    url = f"http://127.0.0.1:{p}/"
    chrome = find_chrome()
    if chrome:
        kw = {"start_new_session": True} if os.name != "nt" else {}
        subprocess.Popen([chrome, f"--app={url}"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)
        print(f"Opened creaite in a Chrome app window: {url}")
    else:
        webbrowser.open(url)
        print(f"Chrome wasn't found, so creaite opened in your default browser: {url} (the dashboard needs Chrome or Edge to remember the vault)")
    return 0


# ===== BL-329 (v194-one-server): one server, however quickly creaite is opened twice =====
# A server writes system/staging/live-server-starting.json (its pid and port) once it holds the port, and clears it once it
# answers /health. A launch that finds a server starting waits for it instead of starting another; a server that finds the
# port held by this vault's own server says "already running" and exits 0.
STARTING_FILE = paths.STAGING / "live-server-starting.json"   # written by live_server.py only
STARTING_WAIT = 20                                             # seconds a launch waits for a starting server


def live_server_pid(pid):
    """True if `pid` is a running live_server.py (not a number reused by another program)."""
    if pid <= 1:
        return False
    try:
        os.kill(pid, 0)
    except PermissionError:   # it exists, run by another user: ps says what it is
        pass
    except OSError:
        return False
    if shutil.which("ps"):
        r = subprocess.run(["ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True)
        return "live_server.py" in r.stdout
    return True


def server_starting(p=None):
    """(pid, port, launched) of another of this vault's servers that is starting, else None: the starting mark, or else
    live-server.json while its server restarts in place after an update (the same pid, not answering for a moment). A mark
    left by a server that has gone is ignored."""
    for f in (STARTING_FILE, SERVER_FILE):
        try:
            info = json.loads(f.read_text(encoding="utf-8"))
            pid, sp = int(info["pid"]), int(info["port"])
        except (OSError, ValueError, KeyError, TypeError):  # no mark, or not one: nothing is starting by it
            continue
        if pid != os.getpid() and (p is None or sp == p) and live_server_pid(pid):
            return pid, sp, bool(info.get("launched"))
    return None


def wait_for_server(p, seconds=STARTING_WAIT, pid=None):
    """Wait up to `seconds` for a creaite server on port `p` to answer /health (sooner if the starting server `pid` goes);
    what health() last said."""
    end = time.monotonic() + seconds
    while True:
        seen = health(p)
        if seen or time.monotonic() >= end or (pid and not live_server_pid(pid)):
            return seen
        time.sleep(0.2)
# ===== end BL-329 =====


# ===== BL-248 (sprint-portability): the right Python, natively, however creaite is started =====
# creaite.app starts with launchd's bare PATH (/usr/bin:/bin:/usr/sbin:/sbin), and a shell-script app with no architecture
# preference may run under Rosetta: then `python3` is Apple's /usr/bin/python3 stub, run as x86_64, and xcrun refuses. So
# everything creaite starts gets this Python's folder first on PATH, and the app asks for arm64 on Apple silicon.
def under_rosetta():
    """True when this process is an Intel one translated by Rosetta (sysctl.proc_translated is 1); False otherwise or unknown."""
    if sys.platform != "darwin":
        return False
    try:
        r = subprocess.run(["/usr/sbin/sysctl", "-n", "sysctl.proc_translated"], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return False
    return r.stdout.strip() == "1"


def apple_silicon():
    """True on an Apple silicon Mac, even from a process running under Rosetta."""
    import platform
    return sys.platform == "darwin" and (platform.machine() == "arm64" or under_rosetta())


def run_path(inherited=None, python=None):
    """The PATH for anything creaite starts: this Python's own folder first, then Homebrew, /usr/local/bin and ~/.local/bin
    (where python.org, Homebrew and Claude Code put their commands), then the inherited PATH; no duplicates, no empty entries."""
    first = [str(Path(python or sys.executable).parent), "/opt/homebrew/bin", "/usr/local/bin", str(Path.home() / ".local" / "bin")]
    rest = (os.environ.get("PATH", "") if inherited is None else inherited).split(os.pathsep)
    return os.pathsep.join(dict.fromkeys(d for d in first + rest if d))
# ===== end BL-248 =====


# ===== BL-237 (sprint-portability): the launcher and the login agent start creaite through the wrapper =====
def runner(script):
    """The command that runs one creaite script: system/scripts/run through /bin/sh (it then picks the newest Python 3.9 or later
    each time, so a Python upgrade never breaks a launcher or the agent), or this Python where there is no wrapper or /bin/sh."""
    wrapper = Path(__file__).resolve().parent / "run"
    if os.name != "nt" and Path("/bin/sh").is_file() and wrapper.is_file():
        return ["/bin/sh", str(wrapper), script]
    return [sys.executable, str(Path(__file__).resolve().parent / script)]
# ===== end BL-237 =====


# ===== BL-305 (sprint-launch-apply): one launcher per vault =====
# The live vault makes "creaite.app", the development repository (.creaite-dev) "creaite (dev).app" with the DEV-marked icon and its
# own bundle ID, so the two sit side by side in ~/Applications and the Dock, each opening its own vault's server and port. A launcher
# that already opens another vault is never replaced silently: make-launcher says so and stops, unless --replace (Alan's yes).
LAUNCHER_CD = re.compile(r'^cd "(.+?)" && exec ', re.M)


def is_dev(root=None):
    """Whether `root` (this vault by default) is the development repository."""
    return (Path(root or paths.ROOT) / ".creaite-dev").exists()


def launcher_name(root=None):
    """The launcher's name for a vault: "creaite (dev)" for the development repository, else "creaite"."""
    return "creaite (dev)" if is_dev(root) else "creaite"


def launcher_vault(app):
    """The vault folder a launcher app opens (from its script), or None if it isn't a creaite launcher we can read."""
    try:
        text = (Path(app) / "Contents" / "MacOS" / "creaite").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    m = LAUNCHER_CD.search(text)
    return Path(m.group(1)) if m else None


def launcher_elsewhere(app, root=None):
    """The other vault an existing launcher opens, or None when it opens `root` (this vault) or isn't there."""
    other = launcher_vault(app)
    if other is None:
        return None
    mine = Path(root or paths.ROOT).resolve()
    return None if os.path.realpath(other) == os.path.realpath(mine) else other
# ===== end BL-305 =====


def make_launcher(where, dest, replace=False):
    """A double-clickable launcher, named for this vault (BL-305). It holds this vault's location: it lives outside the vault by
    design. A launcher of the same name that opens another vault is replaced only with `replace`."""
    import shlex
    root = paths.ROOT.resolve()
    name = launcher_name(root)
    # ===== BL-248 (sprint-portability): a PATH that finds this Python's folder first, and arm64 on Apple silicon =====
    front = [str(Path(sys.executable).parent), "/opt/homebrew/bin", "/usr/local/bin"]
    arch = ["/usr/bin/arch", "-arm64"] if apple_silicon() and Path("/usr/bin/arch").exists() else []
    script = (f'#!/bin/bash\nexport PATH={":".join(shlex.quote(d) for d in front)}:"$HOME/.local/bin:$PATH"\n'
              f'cd "{root}" && exec {" ".join(shlex.quote(x) for x in arch + runner("launch.py"))}\n')     # BL-237: through the wrapper
    # ===== end BL-248 =====
    if where == "vault":
        out = Path(dest or root) / "creaite.command"
        out.write_text(script, encoding="utf-8")
        out.chmod(0o755)
        print(f"Made {out}. Double-click it to open creaite.")
        return 0
    app = Path(dest or Path.home() / "Applications") / f"{name}.app"
    other = launcher_elsewhere(app, root)
    if other and not replace:
        print(f"{app} opens another vault ({other}), so it wasn't replaced. To replace it with one for this vault, run "
              f"make-launcher again with --replace.")
        return 1
    if app.exists():
        shutil.rmtree(app)
    (app / "Contents" / "MacOS").mkdir(parents=True)
    (app / "Contents" / "Resources").mkdir()
    exe = app / "Contents" / "MacOS" / "creaite"
    exe.write_text(script, encoding="utf-8")
    exe.chmod(0o755)
    icon = make_icns(app / "Contents" / "Resources", dev=is_dev(root))
    bundle = "app.creaite.launcher" + (".dev" if is_dev(root) else "")      # BL-305: two apps, never one
    (app / "Contents" / "Info.plist").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        f'<plist version="1.0"><dict>\n<key>CFBundleName</key><string>{name}</string>\n<key>CFBundleDisplayName</key><string>{name}</string>\n'
        f'<key>CFBundleIdentifier</key><string>{bundle}</string>\n<key>CFBundleExecutable</key><string>creaite</string>\n'
        '<key>CFBundlePackageType</key><string>APPL</string>\n<key>CFBundleVersion</key><string>1</string>\n'
        '<key>LSArchitecturePriority</key><array><string>arm64</string><string>x86_64</string></array>\n'   # BL-248: never Rosetta
        + ('<key>CFBundleIconFile</key><string>creaite</string>\n' if icon else "") + '<key>LSUIElement</key><true/>\n</dict></plist>\n', encoding="utf-8")
    print(f"Made {app}" + ("" if icon else " (without the icon: sips or iconutil wasn't available)") + ". Double-click it, or drag it to the Dock.")
    return 0


# ===== BL-320 (v192-fixit): Health's Fix it and the after-update steps =====
ICON_STAMP = paths.STAGING / "app-icon.json"         # the icon addresses' version: written by refresh-icon only
SERVER_FILE = paths.STAGING / "live-server.json"     # the running live server's pid and port: written by live_server.py only
ICONS = ("icon-192.png", "icon-512.png", "icon-maskable-512.png")


def icon_hash():
    """A short fingerprint of the app's icon files, so a release with new icons gives them new addresses by itself."""
    h = hashlib.sha256()
    for n in ICONS:
        f = paths.TEMPLATES / "app" / n
        h.update(f.read_bytes() if f.is_file() else b"")
    return h.hexdigest()[:10]


def icon_stamp():
    """The version the manifest puts on its icon addresses (?v=…): the icons' fingerprint, plus the last refresh-icon's mark."""
    try:
        saved = json.loads(ICON_STAMP.read_text(encoding="utf-8"))
        mark = str(saved.get("mark") or "")
    except (OSError, ValueError, AttributeError):
        mark = ""
    mark = mark if re.fullmatch(r"[0-9]{1,12}", mark) else ""
    return icon_hash() + (f"-{mark}" if mark else "")


def refresh_icon():
    """Give the icons new addresses in the manifest: Chrome sees the change and offers to update its copy of the app."""
    from datetime import datetime
    ICON_STAMP.parent.mkdir(parents=True, exist_ok=True)
    mark = str(int(time.time()))
    ICON_STAMP.write_text(json.dumps({"mark": mark, "at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}) + "\n", encoding="utf-8")
    print("Chrome's copy of the app will be offered the current icon: the manifest now points at new icon addresses. "
          "If Chrome asks to update the app, say yes.")
    return 0


def own_launchers(root=None):
    """The launchers that exist and open this vault: [(where, dest folder)], for make_launcher."""
    root = Path(root or paths.ROOT).resolve()
    name = launcher_name(root)
    found = []
    for folder in (Path.home() / "Applications", Path("/Applications")):
        app = folder / f"{name}.app"
        other = launcher_vault(app)
        if other is not None and os.path.realpath(other) == os.path.realpath(root):
            found.append(("applications", folder))
    cmd = root / "creaite.command"
    if cmd.is_file():
        m = LAUNCHER_CD.search(cmd.read_text(encoding="utf-8", errors="replace"))
        if m and os.path.realpath(m.group(1)) == os.path.realpath(root):
            found.append(("vault", root))
    return found


def remake_own_launchers():
    """make-launcher --if-present: make each launcher that already opens this vault again (natively, with today's icon);
    none: say so and change nothing. Never one that opens another vault."""
    found = own_launchers()
    if not found:
        print("There's no launcher for this vault to make again (it's optional).")
        return 0
    worst = 0
    for where, dest in found:
        worst = max(worst, make_launcher(where, str(dest)))
    return worst


def server_running():
    """(pid, port) of this vault's live server when it is running and answers as this vault's, else None."""
    try:
        info = json.loads(SERVER_FILE.read_text(encoding="utf-8"))
        pid, p = int(info["pid"]), int(info["port"])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if pid <= 1 or health(p) != "this":
        return None
    try:
        os.kill(pid, 0)
    except OSError:
        return None
    if shutil.which("ps"):                                # the pid must still be a live server, not a reused number
        r = subprocess.run(["ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True)
        if "live_server.py" not in r.stdout:
            return None
    return pid, p


def restart_server():
    """Ask this vault's running live server to restart (SIGUSR1); it does so once no job is running, so an update run from
    the dashboard finishes its answer first. Open pages are told to reload."""
    got = server_running()
    if not got:
        print("The live server isn't running, so there's nothing to restart.")
        return 0
    if not hasattr(signal, "SIGUSR1"):
        print("Restart the live server yourself to use the new version (this system can't be asked to).")
        return 0
    os.kill(got[0], signal.SIGUSR1)
    print(f"The live server on port {got[1]} restarts on the new version as soon as it's free; open pages reload.")
    return 0
# ===== end BL-320 =====


def agent_slug():
    """This vault's folder name as a label part."""
    return re.sub(r"[^a-z0-9]+", "-", paths.ROOT.name.lower()).strip("-") or "vault"


def agent_label():
    """One label per vault folder name, so two vaults can each have an agent."""
    return "app.creaite." + agent_slug()


def agent_dir():
    """~/Library/LaunchAgents (CREAITE_AGENT_DIR in tests)."""
    return Path(os.environ.get("CREAITE_AGENT_DIR") or Path.home() / "Library" / "LaunchAgents")


def agent_file():
    """Where this vault's login agent plist lives."""
    return agent_dir() / f"{agent_label()}.plist"


def older_agents():
    """This vault's agent under an earlier label (any `<prefix>.creaite.<vault>.plist` but today's), so install and
    remove clear it and two agents never race for the port."""
    if not agent_dir().is_dir():
        return []
    return [f for f in agent_dir().glob(f"*.creaite.{agent_slug()}.plist") if f.name != agent_file().name]


def agent_is_own_server():
    """#300 review H1: whether this process is a server (or a script a server runs) that launchd started from this vault's own
    agent (launchd sets XPC_SERVICE_NAME to the job's label). Unloading that job would stop the very process asking."""
    return os.environ.get("XPC_SERVICE_NAME") == agent_label()


def drop_older_agents():
    """Unload and delete this vault's agent under an earlier label; returns how many."""
    old = older_agents()
    for f in old:
        f.unlink(missing_ok=True)                                           # the file first, so it is gone whatever happens next
        if os.environ.get("XPC_SERVICE_NAME") != f.stem:                    # never unload the job this process is running in
            launchctl("bootout", f"{agent_domain()}/{f.stem}")
    return len(old)


def launchctl(*args):
    """launchctl's result, or None when the tests ask it to be left alone."""
    if os.environ.get("CREAITE_NO_LAUNCHCTL") == "1":
        return None
    return subprocess.run(["launchctl", *args], capture_output=True, text=True)


def agent_domain():
    """The launchd domain for the signed-in user (gui/<uid>)."""
    return f"gui/{os.getuid()}"


def agent_loaded():
    """Whether launchd has the login agent loaded: True, False, or None when launchctl can't be asked."""
    r = launchctl("print", f"{agent_domain()}/{agent_label()}")
    return None if r is None else r.returncode == 0


def agent_install():
    """Write and load this vault's login agent, which starts the live server at login and restarts it
    after a crash (BL-243). Writes ~/Library/LaunchAgents; refuses off macOS and in the development repository.
    """
    if sys.platform != "darwin" and not os.environ.get("CREAITE_AGENT_DIR"):
        print("The login agent is macOS only (a LaunchAgent). On this system start the live server yourself.")
        return 1
    if (paths.ROOT / ".creaite-dev").exists():
        print("This is the development repository, not a live vault: no login agent here.")
        return 1
    f, label = agent_file(), agent_label()
    plist = {
        "Label": label,
        "ProgramArguments": runner("live_server.py"),                                    # BL-237: through the wrapper
        "WorkingDirectory": str(paths.ROOT),
        "EnvironmentVariables": {"PATH": run_path(os.environ.get("PATH", "/usr/bin:/bin"))},   # launchd's own PATH is too short to find `claude` (BL-248: this Python's folder first)
        "RunAtLoad": True,
        "KeepAlive": {"SuccessfulExit": False},                    # restart after a crash; a clean stop (Settings › Stop) stays stopped
        "ThrottleInterval": 60,
        "StandardOutPath": str(LOG),
        "StandardErrorPath": str(LOG),
        "ProcessType": "Interactive",
    }
    LOG.parent.mkdir(parents=True, exist_ok=True)
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".plist.tmp")
    with open(tmp, "wb") as fh:
        plistlib.dump(plist, fh)
    tmp.chmod(0o644)
    if shutil.which("plutil"):                                   # macOS's own check; skipped where plutil is missing
        lint = subprocess.run(["plutil", "-lint", str(tmp)], capture_output=True, text=True)
        if lint.returncode != 0:
            tmp.unlink()
            print(f"The login agent file didn't pass plutil -lint, so nothing was installed: {(lint.stdout + lint.stderr).strip()}")
            return 1
    os.replace(tmp, f)
    if drop_older_agents():
        print("Removed this vault's login agent under its earlier name.")
    p = port()
    seen = health(p)
    if agent_is_own_server():       # #300 review H1: unloading would stop this very server; the new file is read at the next sign-in
        print(f"Login agent installed: {f}\nThis copy of creaite is the one the agent started, so it carries on as it is; "
              "the agent starts it at your next sign-in.")
        return 0
    if agent_loaded():
        launchctl("bootout", f"{agent_domain()}/{label}")
    r = launchctl("bootstrap", agent_domain(), str(f))
    if r is not None and r.returncode != 0:
        print(f"Wrote {f}, but launchctl wouldn't load it: {(r.stderr or r.stdout).strip()}\n"
              "If this Mac blocks background items, check System Settings › General › Login Items & Extensions.")
        return 1
    print(f"Login agent installed: {f}\ncreaite's live server will start at login on port {p} and restart if it crashes. It does not stop when a window closes.")
    if seen:
        print(f"A server is already running on port {p} (started by hand or by the launcher). Stop it (Settings › Stop, or Ctrl+C) so the agent's server can take the port; "
              "until then the agent retries every minute.")
    print("Remove it any time: system/scripts/run launch.py agent remove")
    return 0


def agent_remove():
    """Delete this vault's login agent, then unload it (BL-243). The file goes first (#300 review H1), so it is gone even if the unload
    ends this process; and when this process is the agent's own server the unload is left out: it would stop the server that is
    answering, so that copy carries on and simply isn't started again at the next sign-in."""
    f = agent_file()
    own = agent_is_own_server()
    had = f.exists()
    if had:
        f.unlink()
    old = drop_older_agents()
    if not (had or old):
        print("No login agent for this vault.")
        return 0
    if own:
        print("Login agent removed. This copy of creaite is the one it started, so it carries on until you stop it; "
              "it won't start again when you sign in.")
        return 0
    loaded = agent_loaded()
    if loaded:
        launchctl("bootout", f"{agent_domain()}/{agent_label()}")
    print(("Login agent removed. creaite won't start when you sign in." if had else "Login agent removed (it had an earlier name).")
          + (" The copy it had started has stopped." if loaded else ""))
    return 0


def agent_state():
    """#300: the login agent's real state as plain data, for the page and Health (nothing is written). supported: macOS and not the
    development repository; installed: this vault's plist is there; loaded: launchd has it (None when it can't be asked);
    folder: where this vault is, for the Terminal note. Never raises."""
    dev = (paths.ROOT / ".creaite-dev").exists()
    mac = sys.platform == "darwin" or bool(os.environ.get("CREAITE_AGENT_DIR"))
    try:
        installed = agent_file().exists()
        loaded = agent_loaded() if installed else False
    except OSError:
        installed, loaded = False, None
    return {"supported": mac and not dev, "dev": dev, "mac": mac, "installed": installed, "loaded": loaded,
            "on": bool(installed and loaded is not False), "own": agent_is_own_server(), "folder": str(paths.ROOT)}


def agent_status(as_json=False):
    """Print whether the login agent is installed and loaded, and whether the server answers (as one JSON line with --json, #300)."""
    if as_json:
        print(json.dumps(agent_state()))
        return 0
    f = agent_file()
    loaded = agent_loaded()
    seen = health(port())
    print(f"Agent file: {f if f.exists() else 'not installed'}")
    print(f"Loaded in launchd: {'unknown' if loaded is None else 'yes' if loaded else 'no'}")
    print(f"Server on port {port()}: {'running (' + seen + ')' if seen else 'not answering'}")
    return 0


def make_icns(resources, dev=False):
    """creaite.icns from the 512px icon (the DEV-marked one for the development repository, BL-305), with macOS's own sips and
    iconutil; None where they aren't there."""
    src = paths.TEMPLATES / "app" / ("icon-dev-512.png" if dev else "icon-512.png")
    if not (shutil.which("sips") and shutil.which("iconutil") and src.exists()):
        return None
    iconset = resources / "creaite.iconset"
    iconset.mkdir()
    try:
        for size in (16, 32, 64, 128, 256, 512):
            for scale in (1, 2):
                px = size * scale
                if px > 512:
                    continue
                subprocess.run(["sips", "-z", str(px), str(px), str(src), "--out", str(iconset / f"icon_{size}x{size}{'@2x' if scale == 2 else ''}.png")],
                               check=True, capture_output=True)
        subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(resources / "creaite.icns")], check=True, capture_output=True)
        return resources / "creaite.icns"
    except (subprocess.CalledProcessError, OSError):
        return None
    finally:
        shutil.rmtree(iconset, ignore_errors=True)


def main(argv):
    """Run the command in `argv`: none to launch, make-launcher, or agent install, remove or status."""
    if argv == ["make-launcher", "--if-present"]:        # BL-320: the after-update step
        return remake_own_launchers()
    if argv == ["refresh-icon"]:                         # BL-320
        return refresh_icon()
    if argv == ["restart"]:                              # BL-320
        return restart_server()
    if argv and argv[0] == "make-launcher":
        replace = "--replace" in argv                    # BL-305: Alan's yes to replacing another vault's launcher
        rest = [a for a in argv[1:] if a != "--replace"]
        opts = dict(zip(rest[0::2], rest[1::2]))
        where = opts.get("--where", "applications")
        if where not in ("applications", "vault"):
            print(__doc__)
            return 2
        return make_launcher(where, opts.get("--dest"), replace)
    if argv == ["agent", "status", "--json"]:             # #300: the page's and Health's read of the agent
        return agent_status(True)
    if argv and argv[0] == "agent" and len(argv) == 2 and argv[1] in ("install", "remove", "status"):
        return {"install": agent_install, "remove": agent_remove, "status": agent_status}[argv[1]]()
    if argv:
        print(__doc__)
        return 2
    return launch()


if __name__ == "__main__":
    try:
        import log as debuglog  # BL-102: the debug log (not `log`: some scripts have a function of that name); a script runs without it
    except ImportError:
        debuglog = None
    sys.exit(debuglog.main("launch.py", main, sys.argv[1:]) if debuglog else main(sys.argv[1:]))
