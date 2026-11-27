#!/bin/sh
# Install the staged M OS applications into DESTDIR ($1).
# The source tree is staged into ./src by scripts/build-packages.sh.
set -eu
D="$1"
S="$(dirname "$0")/src"
install -d "$D/usr/lib/python3/dist-packages/mos" "$D/usr/bin" "$D/usr/share/applications" \
    "$D/etc/xdg/autostart" "$D/usr/libexec/mos" "$D/usr/share/polkit-1/actions"
install -m 644 "$S"/python/mos/*.py "$D/usr/lib/python3/dist-packages/mos/"
for app in mos-welcome mos-control-center mos-update-center mos-system-monitor mos-about; do
    install -m 755 "$S/$app/$app" "$D/usr/bin/$app"
    install -m 644 "$S/$app/$app.desktop" "$D/usr/share/applications/$app.desktop"
done
install -m 755 "$S/mos-desktopctl/mos-desktopctl" "$D/usr/bin/mos-desktopctl"
install -m 644 "$S/mos-welcome/mos-welcome-autostart.desktop" "$D/etc/xdg/autostart/mos-welcome.desktop"
install -m 755 "$S/mos-update-center/mos-update-helper" "$D/usr/libexec/mos/mos-update-helper"
install -m 755 "$S/mos-control-center/mos-firewall-helper" "$D/usr/libexec/mos/mos-firewall-helper"
install -m 644 "$S/mos-update-center/org.mos.updatecenter.policy" "$D/usr/share/polkit-1/actions/org.mos.updatecenter.policy"
