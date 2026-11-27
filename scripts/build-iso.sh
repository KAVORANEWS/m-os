#!/usr/bin/env bash
# Build the M OS live/installer ISO.
#
#   sudo ./scripts/build-iso.sh            # full build
#   sudo MOS_MIRROR=http://<mirror>/debian/ ./scripts/build-iso.sh
#
# Steps: dependency check -> config validation -> package build -> live-build
# -> ISO validation -> SHA256SUMS -> BUILD-REPORT.md. Exits non-zero on any
# failure; success is only reported when the ISO exists and passes verification.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(cat "$ROOT/VERSION")"
WORK="$ROOT/build/work"
LBDIR="$WORK/live"
DIST="$ROOT/dist"
ISO_NAME="M-OS-${VERSION}-amd64.iso"
START=$(date +%s)
BUILD_ID="${MOS_BUILD_ID:-$(date -u +%Y%m%d.%H%M)}"
GIT_COMMIT="$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"

log() { printf '\n\033[1;35m==> %s\033[0m\n' "$*"; }
die() { printf '\033[1;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || die "live-build needs root. Run: sudo $0"

export PATH="/usr/local/sbin:/usr/sbin:/sbin:$PATH"

log "1/9 Checking build dependencies"
missing=()
for cmd in lb debootstrap xorriso mksquashfs unsquashfs dpkg-buildpackage dh python3 sha256sum rsync apt-ftparchive mkfs.vfat mcopy; do
    command -v "$cmd" >/dev/null || missing+=("$cmd")
done
[ "${#missing[@]}" -eq 0 ] || die "missing tools: ${missing[*]}
Install: apt install live-build debootstrap xorriso squashfs-tools dpkg-dev debhelper dh-python rsync apt-utils dosfstools mtools"
grep -q 'trixie\|^13' /etc/debian_version 2>/dev/null || echo "warning: building on a non-Debian-13 host is untested"
avail_gb=$(df --output=avail -BG "$ROOT" | tail -1 | tr -dc '0-9')
[ "$avail_gb" -ge 15 ] || die "at least 15 GB free disk space is required (have ${avail_gb} GB)"

log "2/9 Validating configuration"
"$ROOT/scripts/validate-build.sh"

log "3/9 Building M OS packages"
# Build packages as the invoking user when run through sudo (keeps file ownership sane)
if [ -n "${SUDO_USER:-}" ]; then
    sudo -u "$SUDO_USER" "$ROOT/scripts/build-packages.sh"
else
    "$ROOT/scripts/build-packages.sh"
fi

log "4/9 Preparing live-build tree"
mkdir -p "$WORK" "$DIST"
if [ -d "$LBDIR" ]; then
    (cd "$LBDIR" && lb clean --purge >/dev/null 2>&1) || true
fi
rm -rf "$LBDIR"
mkdir -p "$LBDIR"
rsync -a --exclude 'cache' "$ROOT/build/live-build/" "$LBDIR/"
# Persistent package cache between builds
mkdir -p "$WORK/cache"
ln -sfn "$WORK/cache" "$LBDIR/cache"
# Build identity inside the image
mkdir -p "$LBDIR/config/includes.chroot/usr/share/mos"
cat > "$LBDIR/config/includes.chroot/usr/share/mos/build-info" <<EOF
MOS_VERSION="$VERSION"
BUILD_ID="$BUILD_ID"
BUILD_DATE="$(date -u +%Y-%m-%d)"
GIT_COMMIT="$GIT_COMMIT"
EOF

log "5/9 Configuring live-build (Debian 13 trixie, amd64)"
cd "$LBDIR"
lb config

log "6/9 Building the live system (this takes a while)"
set +e
lb build 2>&1 | tee "$WORK/lb-build.log"
rc=${PIPESTATUS[0]}
set -e
[ "$rc" -eq 0 ] || die "lb build failed (exit $rc); see $WORK/lb-build.log"
grep -q "MOS-VERIFY: all checks passed" "$WORK/lb-build.log" || die "in-image verification hook did not pass"

ISO_BUILT="$(ls -1 "$LBDIR"/*.iso 2>/dev/null | head -1 || true)"
[ -n "$ISO_BUILT" ] && [ -s "$ISO_BUILT" ] || die "lb build finished but no ISO was produced"
mv -f "$ISO_BUILT" "$DIST/$ISO_NAME"
[ -n "${SUDO_USER:-}" ] && chown "$SUDO_USER": "$DIST/$ISO_NAME"
cp "$LBDIR"/chroot.packages.live "$DIST/M-OS-${VERSION}-packages.txt" 2>/dev/null || true

log "7/9 Verifying ISO"
"$ROOT/scripts/verify-iso.sh" "$DIST/$ISO_NAME" | tee "$WORK/verify.log"

log "8/9 Writing checksums"
(cd "$DIST" && sha256sum "$ISO_NAME" > SHA256SUMS && cat SHA256SUMS)

log "9/9 Writing build report"
END=$(date +%s)
ISO_SIZE=$(stat -c %s "$DIST/$ISO_NAME")
PKG_COUNT=$(wc -l < "$DIST/M-OS-${VERSION}-packages.txt" 2>/dev/null || echo "?")
cat > "$DIST/BUILD-REPORT.md" <<EOF
# M OS ${VERSION} build report

| Item | Value |
|---|---|
| ISO | \`${ISO_NAME}\` |
| Size | $(numfmt --to=iec-i --suffix=B "$ISO_SIZE") (${ISO_SIZE} bytes) |
| SHA256 | \`$(cut -d' ' -f1 "$DIST/SHA256SUMS")\` |
| Build ID | ${BUILD_ID} |
| Git commit | ${GIT_COMMIT} |
| Base | Debian 13 (trixie), amd64 |
| Kernel | $(ls "$LBDIR"/chroot/boot/vmlinuz-* 2>/dev/null | sed 's|.*/vmlinuz-||' | head -1) |
| Plasma | $(grep -E '^plasma-workspace\s' "$DIST/M-OS-${VERSION}-packages.txt" 2>/dev/null | awk '{print $2}') |
| Packages in image | ${PKG_COUNT} |
| Build host | $(. /etc/os-release; echo "$PRETTY_NAME"), $(nproc) CPUs |
| Build time | $(( (END-START)/60 )) min $(( (END-START)%60 )) s |

## ISO verification

\`\`\`
$(cat "$WORK/verify.log")
\`\`\`

Boot and installer test results are recorded separately in \`tests/reports/\`.
EOF
[ -n "${SUDO_USER:-}" ] && chown "$SUDO_USER": "$DIST"/SHA256SUMS "$DIST"/BUILD-REPORT.md "$DIST"/*.txt 2>/dev/null || true
log "Build succeeded: $DIST/$ISO_NAME"
