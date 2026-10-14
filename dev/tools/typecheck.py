"""Type-check the dashboard's modules with TypeScript's checkJs (BL-231 step 3, development only).

Run: python3 dev/tools/typecheck.py [--list]
Runs `npx --yes -p typescript@5.6.3 tsc -p dev/jsconfig.json` over system/templates/dashboard/src/ (every module, with
the types in dev/types/) and prints the total error count and a count by error code; --list also prints each error.
check.py ratchets the total (`tsc` in dev/check-baseline.json), so it can only fall.
It needs Node (npx) on this development machine; without it, it says how to install it and exits 2. Nothing in system/
depends on TypeScript or Node. Exit: 0 no type errors, 1 errors, 2 no Node or tsc failed.
"""
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CONFIG = REPO / "dev" / "jsconfig.json"
TYPESCRIPT = "typescript@5.6.3"
EXTRA_DIRS = ("~/.local/bin", "~/homebrew/bin", "/opt/homebrew/bin")
ERROR = re.compile(r"^(?P<file>.+?)\((?P<line>\d+),(?P<col>\d+)\): error (?P<code>TS\d+): (?P<msg>.*)$")
NO_NODE = ("typecheck: Node (npx) isn't installed on this machine.\n"
           "Install the official prebuilt Node (development only, allowed by the 11-10-2026 rule; Homebrew builds it from\n"
           "source, which takes hours): download node-vX.Y.Z-darwin-arm64.tar.gz and SHASUMS256.txt from\n"
           "https://nodejs.org/dist/vX.Y.Z/ (a current LTS), check the SHA-256 (shasum -a 256), unpack it to\n"
           "~/.local/node-vX.Y.Z/ and link its bin/node, bin/npm and bin/npx into ~/.local/bin,\n"
           "then run this again. Nothing in system/ needs Node; only this development check does.")


def find_npx(path=None, extra=EXTRA_DIRS):
    """The full path of npx: on PATH (or `path`), then in the usual development folders; None if it isn't anywhere."""
    dirs = (path if path is not None else os.environ.get("PATH", "")).split(os.pathsep)
    dirs += [os.path.expanduser(d) for d in extra]
    return shutil.which("npx", path=os.pathsep.join(d for d in dirs if d))


def parse(output):
    """The tsc errors in `output` as a list of (file, line, code, message), in the order printed."""
    errors = []
    for raw in output.splitlines():
        m = ERROR.match(raw.strip())
        if m:
            errors.append((m["file"], int(m["line"]), m["code"], m["msg"]))
    return errors


def summary(errors, top=None):
    """Printable lines: the total, then the count for each error code, most frequent first (the first `top` codes)."""
    counts = Counter(code for _, _, code, _ in errors)
    lines = [f"typecheck: {len(errors)} type error{'' if len(errors) == 1 else 's'}"]
    for code, n in counts.most_common(top):
        lines.append(f"  {code}  {n}")
    return lines


def run_tsc(npx):
    """Run tsc on dev/jsconfig.json with `npx` and return (exit code, combined output)."""
    env = dict(os.environ)
    env["PATH"] = os.pathsep.join([str(Path(npx).parent), env.get("PATH", "")])
    cmd = [npx, "--yes", "-p", TYPESCRIPT, "tsc", "-p", str(CONFIG), "--pretty", "false"]
    proc = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True, env=env)
    return proc.returncode, proc.stdout + proc.stderr


def main(argv):
    """Run tsc if Node is present and print the counts (and each error with --list)."""
    if any(a != "--list" for a in argv):
        print(__doc__)
        return 2
    npx = find_npx()
    if not npx:
        print(NO_NODE)
        return 2
    code, output = run_tsc(npx)
    errors = parse(output)
    if code and not errors:
        print(output.strip())
        print("typecheck: tsc failed without reporting type errors.")
        return 2
    if "--list" in argv:
        for f, ln, c, msg in errors:
            print(f"{f}:{ln}: {c} {msg}")
    for line in summary(errors):
        print(line)
    return 1 if errors else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
