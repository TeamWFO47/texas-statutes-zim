#!/bin/bash
# Pack the rendered site into a ZIM with zimwriterfs, then run zimcheck on it.
set -euo pipefail
cd "$(dirname "$0")/.."; source ./config.sh
[ -f "$SITE_DIR/index.html" ] || { echo "No site in $SITE_DIR; run build.sh first."; exit 1; }
mkdir -p "$ZIM_DIR"
[ -e "$ZIM_DIR/$ZIM_NAME" ] && { echo "$ZIM_DIR/$ZIM_NAME exists; move it aside first."; exit 1; }
cp assets/illustration_48x48.png "$SITE_DIR/"

LONG="The Texas Constitution and the Texas codes, one page per chapter, with every statute cross-reference rewritten to link inside this archive. Current through $CURRENT_THROUGH. Snapshot date $SNAPSHOT. Law text: Texas Legislative Council (statutes.capitol.texas.gov). Data: OpenStatutes.org, licensed CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Not an official publication."

$DOCKER pull "$ZIM_TOOLS_IMAGE"
start=$(date +%s)
$DOCKER run --rm -u "$(id -u):$(id -g)" -v "$SITE_DIR":/site:ro -v "$ZIM_DIR":/out \
  "$ZIM_TOOLS_IMAGE" zimwriterfs \
    --welcome=index.html \
    --illustration=illustration_48x48.png \
    --language=eng \
    --title='Texas Constitution & Statutes' \
    --description="Texas Constitution and codes, as published by TLC (snapshot $SNAPSHOT)" \
    --longDescription="$LONG" \
    --creator='Texas Legislative Council' \
    --publisher='OpenStatutes.org (CC BY 4.0)' \
    --name='texas-statutes_en_all' \
    --tags='_category:other;law;texas;statutes' \
    --source='https://openstatutes.org/texconst/' \
    /site "/out/$ZIM_NAME" 2>&1 | tee "$ZIM_DIR/zimwriterfs.log"
echo "zimwriterfs took $(( $(date +%s) - start ))s"
$DOCKER run --rm -v "$ZIM_DIR":/out:ro "$ZIM_TOOLS_IMAGE" zimcheck -A "/out/$ZIM_NAME" 2>&1 | tee "$ZIM_DIR/zimcheck.log" | tail -3
sha256sum "$ZIM_DIR/$ZIM_NAME" | tee "$ZIM_DIR/$ZIM_NAME.sha256"
du -h "$ZIM_DIR/$ZIM_NAME"
