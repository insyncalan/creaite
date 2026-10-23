#!/bin/sh
# creaite 2.6.0 post-release smoke test.
#
#   smoke-261.sh <creaite-2.6.0.zip | v2.6.0> [--old <zip|tag>] [--keep] [--work DIR] [--report FILE]
#
# One command: pass the release zip (a file path, or the tag v2.6.0 to download it with `gh release download`).
# It builds a throwaway vault from 2.5.4 in its own run folder, installs the zip with update.py, runs doctor.py and
# build_dashboard.py, starts the live server on a spare 127.0.0.1 port and checks the Intake and Minutes pages in one
# headless Chrome, then stops only the processes it started and deletes the vault. Exit 0 = all steps passed.
# Needs: python3 (3.9+), Google Chrome, lsof, and gh (only when a tag is given or 2.5.4 isn't cached).
# Never touches a live vault, Microsoft 365, git or the network (except the optional gh download).
set -eu
here=$(cd "$(dirname "$0")" && pwd)
py=""
for c in python3.14 python3.13 python3.12 python3.11 python3.10 python3.9 python3; do
  if command -v "$c" >/dev/null 2>&1; then py=$(command -v "$c"); break; fi
done
[ -n "$py" ] || { echo "smoke-261.sh: no python3 on PATH" >&2; exit 2; }
[ $# -ge 1 ] || { sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }
exec "$py" "$here/smoke_driver.py" "$@"
