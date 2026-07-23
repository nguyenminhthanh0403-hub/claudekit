#!/usr/bin/env bash
#
# Cut a new Mk version of the Bullion map WITHOUT breaking the shared link.
#
# Usage:   ./release.sh <N>        e.g.  ./release.sh 13
#
# What it does (all local — nothing is pushed):
#   1. Copies the CURRENT live version (whatever index.html points at) to
#      bullion_mk<N>.html, freezing the current one as a browsable archive.
#   2. Bumps ONLY the visible version strings (<title>, og:title, <h1>) to Mk<N>
#      — historical "Mk9/Mk10/..." references in the map's prose are left alone.
#   3. Repoints the front door (index.html) at the new file, so the permanent
#      share URL (.../bullion-live-map/) now serves Mk<N>.
#
# Then do your Mk<N> work in bullion_mk<N>.html and:
#   git add bullion_mk<N>.html index.html && git commit -m "Mk<N>: ..." && git push origin main
#
# The daily data pipeline only touches data.json and every version fetches it
# from this same folder, so versioning never affects live data.
set -euo pipefail
cd "$(dirname "$0")"

N="${1:-}"
case "$N" in
  ''|*[!0-9]*) echo "usage: ./release.sh <version-number>   e.g. ./release.sh 13"; exit 1 ;;
esac

CUR=$(grep -oE 'bullion_mk[0-9]+\.html' index.html | head -1)
[ -n "$CUR" ] || { echo "error: could not read the current version from index.html"; exit 1; }
CURVER=$(printf '%s' "$CUR" | grep -oE '[0-9]+')
NEW="bullion_mk${N}.html"

[ "$N" -gt "$CURVER" ] || { echo "error: $N is not newer than the current version (Mk${CURVER})"; exit 1; }
[ -e "$NEW" ]          && { echo "error: $NEW already exists — pick an unused number"; exit 1; }

cp "$CUR" "$NEW"

# Targeted, safe version bumps (these exact phrases only appear in title/og:title/h1,
# never in the map's historical prose which says "Mk9"/"Mk10"/etc.):
sed -i '' -E "s#Bullion Mk${CURVER} #Bullion Mk${N} #g" "$NEW"
sed -i '' -E "s#Mk${CURVER} Column Constellation#Mk${N} Column Constellation#g" "$NEW"

# Point the permanent front door at the new version:
sed -i '' -E "s#${CUR}#${NEW}#g" index.html

echo "Cut ${NEW} from ${CUR}; index.html now serves Mk${N}. (${CUR} kept as the Mk${CURVER} archive.)"
echo "Next:"
echo "  1. make your Mk${N} changes in ${NEW}"
echo "  2. git add ${NEW} index.html && git commit -m \"Mk${N}: <summary>\" && git push origin main"
