#!/usr/bin/env bash
# Build the M OS Debian packages (mos-branding, mos-desktop-config, mos-apps).
#
# Packages are staged in build/work/packages (sources stay clean), built with
# dpkg-buildpackage, checked with lintian (warnings reported, not fatal) and
# copied to:
#   build/live-build/config/packages.chroot/   (installed into the ISO)
#   dist/packages/                              (release artifacts)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$ROOT/build/work/packages"
OUT_CHROOT="$ROOT/build/live-build/config/packages.chroot"
OUT_DIST="$ROOT/dist/packages"
R="$ROOT/branding/rendered"

for tool in dpkg-buildpackage dh python3; do
    command -v "$tool" >/dev/null || { echo "missing build tool: $tool (apt install dpkg-dev debhelper dh-python)" >&2; exit 1; }
done
[ -d "$R/wallpaper" ] || { echo "branding not rendered; run scripts/render-branding.sh" >&2; exit 1; }

rm -rf "$WORK"
mkdir -p "$WORK" "$OUT_CHROOT" "$OUT_DIST"
rm -f "$OUT_CHROOT"/mos-*.deb "$OUT_DIST"/mos-*.deb

python3 "$ROOT/desktop/themes/generate_colorschemes.py" >/dev/null

stage_branding() {
    local F="$1/files"
    local W="$F/usr/share/wallpapers/MOS/contents"
    mkdir -p "$W/images" "$W/images_dark"
    for res in 3840x2160 1920x1080; do
        cp "$R/wallpaper/light-$res.jpg" "$W/images/$res.jpg"
        cp "$R/wallpaper/dark-$res.jpg" "$W/images_dark/$res.jpg"
    done
    cp "$R/wallpaper/dark-screenshot.jpg" "$W/screenshot.jpg"

    mkdir -p "$F/usr/share/icons/hicolor/scalable/apps" "$F/usr/share/pixmaps"
    cp "$ROOT"/branding/icons/scalable/*.svg "$F/usr/share/icons/hicolor/scalable/apps/"
    for s in 48 128 256; do
        mkdir -p "$F/usr/share/icons/hicolor/${s}x${s}/apps"
        cp "$R/icons/${s}x${s}/"*.png "$F/usr/share/icons/hicolor/${s}x${s}/apps/"
    done
    cp "$R/logos/mos-logo-256.png" "$F/usr/share/pixmaps/mos-logo.png"
    cp "$ROOT/branding/logos/mos-logo.svg" "$F/usr/share/pixmaps/mos-logo.svg"
    mkdir -p "$F/usr/share/mos/branding"
    cp "$R/logos/mos-wordmark.png" "$ROOT/branding/logos/"*.svg "$F/usr/share/mos/branding/"

    cp "$R/plymouth/logo.png" "$R/plymouth/dot.png" "$F/usr/share/plymouth/themes/mos/"
    cp "$R/calamares/logo.png" "$R/calamares/welcome.png" "$R/calamares/slide-bg.png" \
       "$F/etc/calamares/branding/mos/"

    for layout in modern classic; do
        local P="$F/usr/share/plasma/look-and-feel/org.mos.$layout.desktop/contents/previews"
        mkdir -p "$P"
        cp "$R/previews/$layout-preview.png" "$P/preview.png"
        cp "$R/previews/$layout-fullscreenpreview.jpg" "$P/fullscreenpreview.jpg"
    done
}

stage_apps() {
    mkdir -p "$1/src"
    cp -a "$ROOT/applications/." "$1/src/"
    find "$1/src" -name '__pycache__' -prune -exec rm -rf {} +
}

for pkg in mos-branding mos-desktop-config mos-apps; do
    echo "==> Building $pkg"
    cp -a "$ROOT/packages/$pkg" "$WORK/$pkg"
    case "$pkg" in
        mos-branding) stage_branding "$WORK/$pkg" ;;
        mos-apps)     stage_apps "$WORK/$pkg" ;;
    esac
    (cd "$WORK/$pkg" && dpkg-buildpackage -b -us -uc --no-check-builddeps >"$WORK/$pkg.build.log" 2>&1) || {
        echo "Build of $pkg FAILED — log:" >&2
        tail -40 "$WORK/$pkg.build.log" >&2
        exit 1
    }
done

cp "$WORK"/*.deb "$OUT_CHROOT/"
cp "$WORK"/*.deb "$OUT_DIST/"

if command -v lintian >/dev/null; then
    echo "==> lintian (informational)"
    lintian --tag-display-limit 0 --suppress-tags-from-file "$ROOT/packages/lintian-overrides.txt" \
        "$WORK"/*.deb || true
fi

echo "==> Packages:"
for deb in "$OUT_DIST"/*.deb; do
    printf '  %-45s %s\n' "$(basename "$deb")" "$(du -h "$deb" | cut -f1)"
done
