#!/usr/bin/env bash
# Validate built M OS .deb packages: metadata, required files, maintainer
# script syntax and lintian errors.
#   tests/packaging/test-packages.sh dist/packages
set -uo pipefail
DIR="${1:-dist/packages}"
fail=0
pass() { echo "PASS  $*"; }
bad()  { echo "FAIL  $*"; fail=1; }

declare -A REQUIRED=(
  [mos-branding]="./usr/lib/os-release ./usr/share/wallpapers/MOS/metadata.json ./usr/share/plasma/look-and-feel/org.mos.modern.desktop/metadata.json ./usr/share/plasma/look-and-feel/org.mos.classic.desktop/metadata.json ./usr/share/color-schemes/MOSDark.colors ./usr/share/color-schemes/MOSLight.colors ./usr/share/plymouth/themes/mos/mos.plymouth ./etc/calamares/branding/mos/branding.desc ./usr/share/icons/hicolor/scalable/apps/mos-logo.svg"
  [mos-desktop-config]="./etc/xdg/kdeglobals ./etc/xdg/kwinrc ./etc/sysctl.d/90-mos-hardening.conf ./usr/lib/systemd/system/mos-firewall-setup.service ./usr/libexec/mos/mos-firewall-setup ./etc/xdg/fcitx5/profile"
  [mos-apps]="./usr/bin/mos-welcome ./usr/bin/mos-control-center ./usr/bin/mos-update-center ./usr/bin/mos-system-monitor ./usr/bin/mos-about ./usr/bin/mos-desktopctl ./usr/libexec/mos/mos-update-helper ./usr/share/polkit-1/actions/org.mos.updatecenter.policy ./etc/xdg/autostart/mos-welcome.desktop"
)

for pkg in "${!REQUIRED[@]}"; do
    deb=$(ls "$DIR/${pkg}"_*_all.deb 2>/dev/null | head -1)
    [ -n "$deb" ] || { bad "$pkg: package not built"; continue; }
    [ "$(dpkg-deb -f "$deb" Package)" = "$pkg" ] && pass "$pkg: control metadata" || bad "$pkg: wrong Package field"
    contents=$(dpkg-deb -c "$deb" | awk '{print $6}')
    for f in ${REQUIRED[$pkg]}; do
        grep -qx "$f" <<<"$contents" && pass "$pkg: contains ${f#.}" || bad "$pkg: missing ${f#.}"
    done
    tmp=$(mktemp -d)
    dpkg-deb -e "$deb" "$tmp"
    for s in preinst postinst prerm postrm; do
        [ -f "$tmp/$s" ] || continue
        sh -n "$tmp/$s" && pass "$pkg: $s syntax" || bad "$pkg: $s syntax error"
    done
    rm -rf "$tmp"
    if command -v lintian >/dev/null; then
        if lintian --tag-display-limit 0 "$deb" 2>/dev/null | grep -q '^E:'; then
            lintian "$deb" | grep '^E:'
            bad "$pkg: lintian errors"
        else
            pass "$pkg: no lintian errors"
        fi
    fi
done
grep -q "^mos-desktop-config" <<<"$(dpkg-deb -f "$DIR"/mos-desktop-config_*_all.deb Package)" && \
  dpkg-deb -f "$DIR"/mos-desktop-config_*_all.deb Conflicts | grep -q desktop-base && pass "mos-desktop-config conflicts with desktop-base" || bad "desktop-base conflict missing"
[ "$fail" -eq 0 ] && echo "Package tests PASSED" || echo "Package tests FAILED"
exit "$fail"
