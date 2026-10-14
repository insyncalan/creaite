"""BL-246: what run_tests.py needs to share one machine fairly (development only; standard library only).

Three things:
- **Tiers.** A test file is in the Chrome tier when it, or a test helper it imports, drives Chrome (`LiveBrowserCase`,
  `cdp`, `chrome_path`, `--dump-dom`). Everything else is the quick tier. Read from the files, never a hand-kept list.
- **A machine-wide Chrome cap** (Alan, 11-10-2026: about 3 at once, shared by every worktree and session). A slot is a
  lock file in a folder outside any worktree, held with an operating-system lock (`flock`). The lock is passed to the
  test's own process, so it is held until that process ends, and the system lets go of it the moment the process dies:
  a run that crashes, is stopped or is killed never keeps a slot. Without `fcntl` (Windows) there is no machine-wide
  cap; the run's own pool still limits it.
- **A private temporary folder for each test file.** The runner points the file's TMPDIR at a folder of its own inside
  the run's folder, so every vault, Chrome profile and fake home the file makes lands there. The file's folder is
  deleted when it ends, pass or fail; the run's folder when the run ends or is stopped; and the folder of a run whose
  process is gone (killed outright) by the next run that starts. Paths stay short (macOS limits a socket path to 104
  characters, and Chrome puts one under TMPDIR).
"""
import ast
import collections
import functools
import os
import re
import shutil
import signal
import subprocess
import tempfile
import time
from pathlib import Path

try:
    import fcntl
except ImportError:                       # Windows: no machine-wide cap, the run's own pool still limits Chrome
    fcntl = None

CHROME_CAP = int(os.environ.get("CREAITE_CHROME_CAP", "3"))
LOCK_DIR = Path(os.environ.get("CREAITE_CHROME_LOCKS", "/tmp/creaite-chrome-slots" if os.name == "posix" else
                               os.path.join(tempfile.gettempdir(), "creaite-chrome-slots")))
RUN_BASE = Path(os.environ.get("CREAITE_RUN_BASE") or
                ("/tmp" if os.name == "posix" and os.access("/tmp", os.W_OK) else tempfile.gettempdir()))
RUN_PREFIX = "cr"                         # /tmp/cr<pid>/<n>/: short, so Chrome's socket path fits
OLD_STYLE = ("creaite-test-*", "creaite-chrome-*", "creaite-cdp-*")   # BL-247: test folders a run can leave
OLD_STYLE_AGE = 3600                      # removed when over an hour old and not in use
TEST_PROFILE = re.compile(r"--user-data-dir=\S*(creaite-cdp-|creaite-chrome-|/cr\d+/)")
ORPHAN_AGE = 15 * 60                      # an orphan must have run this long: launch.py detaches a test's server on purpose
BROWSERS = ("Google Chrome", "Chromium", "chromium", "Microsoft Edge")
NOT_CHROME = {"run_support", "run_tests", "check", "check_extras", "proc_guard"}   # the runner's own tools name Chrome, never drive it
MARKERS = re.compile(r"LiveBrowserCase|chrome_path|--dump-dom|--headless|Google Chrome|chromium|\bimport cdp\b|\bcdp\.")


# ---------- tiers ----------
def _module(here, name):
    """The dev/tests or dev/tools file for module `name`, or None (the standard library, creaite's scripts)."""
    if name in NOT_CHROME:
        return None
    for d in (here, here.parent / "tools", here.parent / "tests"):
        p = d / f"{name}.py"
        if p.exists():
            return p.resolve()
    return None


@functools.lru_cache(maxsize=None)
def _tree(path):
    src = Path(path).read_text(encoding="utf-8", errors="replace")
    return src, ast.parse(src)


@functools.lru_cache(maxsize=None)
def _name_drives_chrome(path, name):
    """True when `name`, defined at the top of test file `path`, drives Chrome: its own code has a marker, or it is a
    class whose base does (followed through the imports)."""
    src, tree = _tree(path)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Assign)) and name in _defined(node):
            if MARKERS.search(ast.get_source_segment(src, node) or ""):
                return True
            bases = [b.id for b in getattr(node, "bases", []) if isinstance(b, ast.Name)]
            return any(_imported_drives_chrome(path, b) for b in bases) or any(_name_drives_chrome(path, b) for b in bases)
    return _imported_drives_chrome(path, name)


def _defined(node):
    if isinstance(node, ast.Assign):
        return {t.id for t in node.targets if isinstance(t, ast.Name)}
    return {node.name}


def _imported_drives_chrome(path, name):
    """True when `name` is imported into `path` from a module that makes it drive Chrome."""
    _, tree = _tree(path)
    here = Path(path).parent
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and any((a.asname or a.name) == name for a in node.names):
            src_name = next(a.name for a in node.names if (a.asname or a.name) == name)
            p = _module(here, node.module)
            return bool(p) and _from_drives_chrome(str(p), src_name)
    return False


def _from_drives_chrome(path, name):
    """A helper module (not a test file) counts whole; from a test file, only the name taken counts."""
    if not Path(path).name.startswith("test_"):
        return _drives_chrome(path)
    return _name_drives_chrome(path, name)


@functools.lru_cache(maxsize=None)
def _drives_chrome(path):
    """True when this file drives Chrome itself, imports a helper module that does, or takes from another test file a
    class or function that does. Importing data helpers (Vault, populate, ABC) from a Chrome test file doesn't count."""
    src, tree = _tree(path)
    if MARKERS.search(src):
        return True
    here = Path(path).parent
    for node in ast.walk(tree):                 # imports inside a test method count too
        if isinstance(node, ast.Import):
            mods = [(a.name, None) for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods = [(node.module, a.name) for a in node.names]
        else:
            continue
        for mod, name in mods:
            p = _module(here, mod)
            if p is None or p == Path(path).resolve():
                continue
            if name is None or not p.name.startswith("test_"):
                if _drives_chrome(str(p)):
                    return True
            elif _name_drives_chrome(str(p), name):
                return True
    return False


def is_chrome(f):
    """Whether the test file `f` belongs to the Chrome tier."""
    return _drives_chrome(str(Path(f).resolve()))


# ---------- the machine-wide Chrome cap ----------
def take_slot(say=print, every=0.5):
    """Wait for one of CHROME_CAP machine-wide slots and return its open, locked file descriptor (or None without
    fcntl). Pass it to the test's process (`pass_fds`) and close it here once the process has ended."""
    if fcntl is None:
        return None
    LOCK_DIR.mkdir(parents=True, exist_ok=True)
    told = False
    while True:
        for n in range(CHROME_CAP):
            fd = os.open(str(LOCK_DIR / f"slot-{n}.lock"), os.O_RDWR | os.O_CREAT, 0o666)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                os.set_inheritable(fd, True)
                return fd
            except OSError:
                os.close(fd)
        if not told:
            say(f"(waiting for a Chrome slot: {CHROME_CAP} in use on this machine)")
            told = True
        time.sleep(every)


def give_slot(fd):
    """Let a slot go (closing the descriptor releases the lock once the test's process has ended too)."""
    if fd is not None:
        os.close(fd)


# ---------- private temporary folders ----------
def _alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:               # someone else's process: alive
        return True
    return True


def _seconds(etime):
    """`ps` elapsed time ([[dd-]hh:]mm:ss) in seconds."""
    days, _, rest = etime.rpartition("-")
    parts = [int(x) for x in rest.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    return int(days or 0) * 86400 + parts[0] * 3600 + parts[1] * 60 + parts[2]


def _ps():
    """[(pid, ppid, seconds running, command)] for every process (POSIX `ps`)."""
    r = subprocess.run(["ps", "-axo", "pid=,ppid=,etime=,command="], capture_output=True, text=True)
    rows = []
    for ln in r.stdout.splitlines():
        parts = ln.split(None, 3)
        if len(parts) == 4 and parts[0].isdigit() and parts[1].isdigit():
            rows.append((int(parts[0]), int(parts[1]), _seconds(parts[2]), parts[3]))
    return rows


def _cwd(pid):
    r = subprocess.run(["lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fn"], capture_output=True, text=True)
    return next((ln[1:] for ln in r.stdout.splitlines() if ln.startswith("n")), "")


def _temp_roots():
    """Where test vaults live, as written and as resolved (/var/folders is /private/var/folders on macOS)."""
    roots = {tempfile.gettempdir(), str(RUN_BASE), "/tmp/", "/private/tmp/"}
    return sorted(roots | {str(Path(r).resolve()) for r in roots})


def orphans(age=ORPHAN_AGE):
    """Test live servers and test Chromes whose parent has gone (re-parented to PID 1) and that have run over `age`
    seconds. Never Alan's own browser or live server: a server must run from a vault in a temporary folder, a Chrome
    must use a test profile or have been started from a dev/tests folder."""
    found = []
    temps = _temp_roots()
    for pid, ppid, secs, cmd in _ps():
        if ppid != 1 or secs < age:
            continue
        if "system/scripts/live_server.py" in cmd and any(t in cmd for t in temps):
            found.append((pid, "test live server"))
        elif any(b in cmd for b in BROWSERS) and (TEST_PROFILE.search(cmd) or _cwd(pid).endswith("/dev/tests")):
            found.append((pid, "test Chrome"))
    return found


def _in_use():
    """Every path a process has open or works in (one `lsof` call)."""
    r = subprocess.run(["lsof", "-Fn"], capture_output=True, text=True)
    return [ln[1:] for ln in r.stdout.splitlines() if ln.startswith("n/")]


def stale_folders(age=OLD_STYLE_AGE):
    """Test folders over `age` seconds old that no process is using, and the folders of runs whose process has gone."""
    found = []
    for d in RUN_BASE.glob(f"{RUN_PREFIX}[0-9]*"):
        pid = d.name[len(RUN_PREFIX):]
        if d.is_dir() and pid.isdigit() and not _alive(int(pid)):
            found.append(d)
    cutoff = time.time() - age
    old = [d for pat in OLD_STYLE for d in Path(tempfile.gettempdir()).glob(pat) if _untouched_since(d, cutoff)]
    if old:
        used = _in_use()
        old = [d for d in old if not any(u.startswith(str(d.resolve()) + "/") or u == str(d.resolve()) for u in used)]
    return found + old


def _untouched_since(d, cutoff):
    """True when `d` is a folder and nothing in it, at any depth, has changed since `cutoff`. A vault in use keeps
    changing (the server's log, the database), even when no file is open at the moment `lsof` looks."""
    try:
        if not d.is_dir() or d.stat().st_mtime >= cutoff:
            return False
        for root, dirs, files in os.walk(d):
            for name in dirs + files:
                if os.lstat(os.path.join(root, name)).st_mtime >= cutoff:
                    return False
    except OSError:
        return False                      # changing under us, or gone: not stale
    return True


def clean(say=print, grace=2, age=ORPHAN_AGE, only=None):
    """BL-247 (`run_tests.py --clean`, and at the start of every run): stop orphaned test servers and Chromes, by PID,
    and remove stale test folders. `only` limits the processes to those PIDs (tests). Returns (stopped, removed)."""
    if os.name != "posix":
        return 0, 0
    procs = [(pid, k) for pid, k in orphans(age) if only is None or pid in only]
    for pid, _ in procs:
        _signal(pid, signal.SIGTERM)
    end = time.time() + grace
    while procs and time.time() < end and any(_alive(pid) for pid, _ in procs):
        time.sleep(0.1)
    for pid, _ in procs:
        _signal(pid, signal.SIGKILL)
    folders = stale_folders()
    for d in folders:
        shutil.rmtree(d, ignore_errors=True)
    _report(procs, folders, say)
    return len(procs), len(folders)


def _report(procs, folders, say):
    if procs or folders:
        kinds = collections.Counter(k for _, k in procs)
        bits = [f"{n} {k}{'s' if n != 1 else ''}" for k, n in sorted(kinds.items())]
        bits += [f"{len(folders)} test folder{'s' if len(folders) != 1 else ''}"] if folders else []
        say("Cleaned up after earlier runs: " + ", ".join(bits) + ".")


def sweep_stale(say=print):
    """Kept for BL-246's callers: the same as `clean`."""
    return sum(clean(say=say))


def _signal(pid, sig):
    try:
        os.kill(pid, sig)
    except OSError:
        pass                              # gone already


class RunDir:
    """This run's folder (/tmp/cr<pid>) with one numbered folder per test file."""

    def __init__(self):
        self.root = RUN_BASE / f"{RUN_PREFIX}{os.getpid()}"
        shutil.rmtree(self.root, ignore_errors=True)
        self.root.mkdir(parents=True)
        self.count = 0

    def for_file(self):
        """A new empty folder for one test file's TMPDIR."""
        self.count += 1
        d = self.root / str(self.count)
        d.mkdir()
        return d

    @staticmethod
    def finish(d):
        """Remove a test file's folder; return how many vaults it left behind (for the BL-172 warning)."""
        left = sum(1 for _ in d.glob("creaite-test-*")) if d.exists() else 0
        shutil.rmtree(d, ignore_errors=True)
        return left

    def close(self):
        """Remove the whole run folder."""
        shutil.rmtree(self.root, ignore_errors=True)
