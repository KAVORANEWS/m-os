#!/usr/bin/env bash
# Verify that every package named in the live-build package lists exists in
# the configured Debian archive. Must run on Debian 13 (or in a debian:trixie
# container) with main, contrib and non-free-firmware enabled in APT.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LISTS="$ROOT/build/live-build/config/package-lists"
missing=0
total=0

available="$(mktemp)"; wanted="$(mktemp)"
trap 'rm -f "$available" "$wanted"' EXIT
apt-cache pkgnames | sort -u > "$available"
cat "$LISTS"/*.list.* | sed -e 's/#.*//' -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' \
    | grep -v '^$' | grep -v '^!' | sort -u > "$wanted"
total=$(wc -l < "$wanted")
while read -r pkg; do
    echo "MISSING: $pkg"
    missing=$((missing + 1))
done < <(comm -23 "$wanted" "$available")

echo "Checked $total packages, $missing missing."
[ "$missing" -eq 0 ]
