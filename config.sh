# Settings for the Texas statutes ZIM build.
# Edit here, or override any of them from the environment, e.g.
#   TXLAW_WORK=/data/txlaw ./build.sh

# Where downloads, the rendered site and the ZIM go (about 1 GB in total).
TXLAW_WORK="${TXLAW_WORK:-$HOME/texas-statutes-zim-work}"

# OpenStatutes.org release to build from (see https://openstatutes.org/texconst/history/).
SNAPSHOT="${SNAPSHOT:-2026-03-26}"
# Shown on the landing page and in the ZIM description. Update when you change SNAPSHOT.
CURRENT_THROUGH="${CURRENT_THROUGH:-the 89th Legislature, 2nd Called Session, 2025; constitutional amendments approved by voters in November 2025}"

# Docker command. Use DOCKER="sudo docker" if your user is not in the docker group.
DOCKER="${DOCKER:-docker}"
ZIM_TOOLS_IMAGE="${ZIM_TOOLS_IMAGE:-ghcr.io/openzim/zim-tools:latest}"

# Kiwix library folder that ship-zim.sh copies the finished ZIM into.
# The default is where Project N.O.M.A.D. keeps its ZIM files.
KIWIX_LIBRARY="${KIWIX_LIBRARY:-/opt/project-nomad/storage/zim}"

# Sent with every download request. Please keep it identifying and polite.
USER_AGENT="${USER_AGENT:-texas-statutes-zim/1.0 (+https://github.com/TeamWFO47/texas-statutes-zim)}"

# Derived paths; no need to edit.
SRC_DIR="$TXLAW_WORK/source/$SNAPSHOT"
SITE_DIR="$TXLAW_WORK/site"
ZIM_DIR="$TXLAW_WORK/zim"
ZIM_NAME="texas-statutes_en_all_${SNAPSHOT:0:7}.zim"
