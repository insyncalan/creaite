#!/bin/sh
# BL-256: fetch Preact and signals for vendoring (development only). Alan runs it himself, because downloads are blocked
# in Claude's sessions: sh dev/tools/fetch_preact.sh. It reads the npm registry, downloads three tarballs into
# ~/Downloads/preact-vendor/, checks each against the registry's SHA-512 and prints the version, date and SHA-256 to pin.
# Nothing is installed. The pinned versions and SHA-256s are then recorded in system/templates/vendor/preact/.
set -e
D=~/Downloads/preact-vendor; mkdir -p "$D"; cd "$D"
for p in preact @preact/signals @preact/signals-core; do
  f=$(echo "$p" | tr / _).json
  curl -fsSL "https://registry.npmjs.org/$p" -o "$f"
  # newest stable release at least 14 days old (preact: 10.x only)
  line=$(python3 -I -c '
import json,sys,datetime as dt
d=json.load(open(sys.argv[1])); cut=dt.datetime.now(dt.timezone.utc)-dt.timedelta(days=14)
ok=[(d["time"][v],v) for v in d["versions"] if "-" not in v and (sys.argv[2]!="preact" or v.startswith("10."))
    and dt.datetime.fromisoformat(d["time"][v].replace("Z","+00:00"))<=cut]
t,v=max(ok); x=d["versions"][v]["dist"]; print(v,t,x["tarball"],x["integrity"])' "$f" "$p")
  set -- $line
  echo "$p $1 released $2"
  curl -fsSLO "$3"
  tgz=$(basename "$3")
  got="sha512-$(openssl dgst -sha512 -binary "$tgz" | openssl base64 -A)"
  [ "$got" = "$4" ] && echo "  registry integrity: matches" || { echo "  registry integrity: DOES NOT MATCH"; exit 1; }
  echo "  sha256: $(shasum -a 256 "$tgz" | cut -d' ' -f1)  $tgz"
done
