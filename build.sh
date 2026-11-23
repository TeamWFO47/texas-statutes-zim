#!/bin/bash
# One-command build: download -> render -> verify -> link check -> ZIM.
# Set DOCKER="sudo docker" if your user cannot run docker directly. Set SKIP_ZIM=1 to stop before the ZIM.
set -euo pipefail
cd "$(dirname "$0")"; source ./config.sh
echo "== 1/5 download (release $SNAPSHOT into $SRC_DIR)"
scripts/download.sh
echo "== 2/5 render (into $SITE_DIR)"
rm -rf "$SITE_DIR"
python3 -I scripts/render.py --src "$SRC_DIR" --codes "$SRC_DIR/StatuteCodes.json" --out "$SITE_DIR" \
  --snapshot "$SNAPSHOT" --current-through "$CURRENT_THROUGH" --mode hybrid --log "$TXLAW_WORK/render-log.json"
echo "== 3/5 verify every page against TLC's text"
python3 -I scripts/verify.py "$SRC_DIR" "$SITE_DIR"
echo "== 4/5 check every internal link"
python3 -I scripts/linkcheck.py "$SITE_DIR"
if [ "${SKIP_ZIM:-0}" = 1 ]; then echo "SKIP_ZIM=1: site is ready in $SITE_DIR"; exit 0; fi
echo "== 5/5 build the ZIM"
scripts/make-zim.sh
