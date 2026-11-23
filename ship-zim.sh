#!/bin/bash
# Copy the finished ZIM into a Kiwix library folder (default: Project N.O.M.A.D.'s).
# Run with sudo rights; the library folder is usually owned by root.
set -euo pipefail
cd "$(dirname "$0")"; source ./config.sh
SRC="$ZIM_DIR/$ZIM_NAME"; DST="$KIWIX_LIBRARY/$ZIM_NAME"
[ -f "$SRC" ] || { echo "No ZIM at $SRC; run build.sh first."; exit 1; }
[ -e "$DST" ] && { echo "$DST already exists; not overwriting."; exit 1; }
SUM=$(sha256sum "$SRC" | cut -d' ' -f1)
sudo install -o root -g root -m 644 "$SRC" "$DST"
echo "$SUM  $DST" | sudo sha256sum -c -
ls -l "$DST"
echo "Copied. Now make Kiwix pick it up: in Project N.O.M.A.D., open the Kiwix page and press Rescan Library."
echo "On a plain kiwix-serve, add it to your library.xml (kiwix-manage) or restart kiwix-serve with the new file."
