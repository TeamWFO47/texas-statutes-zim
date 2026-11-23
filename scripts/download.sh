#!/bin/bash
# Download one OpenStatutes.org texconst release (JSON + TLC chapter HTML zips) and
# TLC's official list of code names, then verify every file against SHA256SUMS.
# Requests are serial with a 1 second pause. Already-verified files are not re-downloaded.
set -euo pipefail
cd "$(dirname "$0")/.."; source ./config.sh
BASE="https://data.openstatutes.org/texconst/${SNAPSHOT//-//}"
mkdir -p "$SRC_DIR"; cd "$SRC_DIR"
get() { curl -sSf --retry 3 -A "$USER_AGENT" -o "$2" "$1"; sleep 1; }

get "$BASE/SHA256SUMS" SHA256SUMS
get "$BASE/meta.json"  meta.json
get "https://statutes.capitol.texas.gov/assets/StatuteCodes.json" StatuteCodes.json

# The file list comes from the release's own meta.json: one JSON and one HTML zip per code.
mapfile -t FILES < <(python3 -I -c '
import json,sys
for d in json.load(open("meta.json"))["datasets"]:
    for k in ("json","htmzip"):
        print(d["files"][k]["name"])')
echo "release $SNAPSHOT: ${#FILES[@]} files"

grep -E "  ($(IFS='|'; echo "${FILES[*]}" | sed 's/\./\\./g'))\$" SHA256SUMS > want.sums
for f in "${FILES[@]}"; do
  if [ -f "$f" ] && grep -F "  $f" want.sums | sha256sum -c --quiet - 2>/dev/null; then continue; fi
  echo "  downloading $f"; get "$BASE/$f" "$f"
done
sha256sum -c --quiet want.sums && echo "all ${#FILES[@]} files match SHA256SUMS"
python3 -I -c 'import json; json.load(open("StatuteCodes.json"))' && echo "StatuteCodes.json OK"
