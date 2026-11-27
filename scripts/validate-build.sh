#!/usr/bin/env bash
# Static validation of the M OS source tree (no root, no network needed
# except for the optional package-availability check).
#   ./scripts/validate-build.sh            # all checks
#   SKIP_APT_CHECK=1 ./scripts/validate-build.sh
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LB="$ROOT/build/live-build"
fail=0
pass() { printf '  \033[32mPASS\033[0m %s\n' "$*"; }
bad()  { printf '  \033[31mFAIL\033[0m %s\n' "$*"; fail=1; }

echo "M OS build validation"

[ -x "$LB/auto/config" ] && pass "live-build auto/config present" || bad "live-build auto/config missing or not executable"
grep -q -- '--distribution trixie' "$LB/auto/config" && pass "targets Debian 13 trixie" || bad "auto/config does not target trixie"

for hook in "$LB"/config/hooks/normal/*.hook.chroot; do
    [ -x "$hook" ] || bad "hook not executable: $(basename "$hook")"
    sh -n "$hook" || bad "syntax error: $(basename "$hook")"
done
pass "hooks are executable shell scripts"

for f in grub.cfg config.cfg theme.cfg splash.png live-theme/theme.txt; do
    [ -f "$LB/config/bootloaders/grub-pc/$f" ] || bad "bootloader file missing: $f"
done
grep -q '@KERNEL_LIVE@' "$LB/config/bootloaders/grub-pc/grub.cfg" && pass "GRUB menu uses live-build placeholders" \
    || bad "grub.cfg lacks @KERNEL_LIVE@"

if command -v shellcheck >/dev/null; then
    if shellcheck -S warning "$ROOT"/scripts/*.sh "$ROOT"/applications/mos-update-center/mos-update-helper \
        "$ROOT"/applications/mos-control-center/mos-firewall-helper \
        "$ROOT"/packages/mos-desktop-config/files/usr/libexec/mos/mos-firewall-setup \
        "$LB"/config/hooks/normal/*.hook.chroot "$ROOT"/tests/boot/*.sh; then
        pass "shellcheck"
    else
        bad "shellcheck reported problems"
    fi
fi

if python3 -m json.tool "$ROOT/packages/mos-branding/files/usr/share/wallpapers/MOS/metadata.json" >/dev/null \
   && python3 -m json.tool "$ROOT/packages/mos-branding/files/usr/share/plasma/look-and-feel/org.mos.modern.desktop/metadata.json" >/dev/null \
   && python3 -m json.tool "$ROOT/packages/mos-branding/files/usr/share/plasma/look-and-feel/org.mos.classic.desktop/metadata.json" >/dev/null; then
    pass "Plasma package metadata is valid JSON"
else
    bad "invalid Plasma metadata JSON"
fi

if command -v desktop-file-validate >/dev/null; then
    if desktop-file-validate "$ROOT"/applications/*/*.desktop 2>&1 | grep -q 'error:'; then
        bad "desktop-file-validate errors"
    else
        pass "desktop entries"
    fi
fi

if python3 -m py_compile "$ROOT"/applications/python/mos/*.py; then pass "Python byte-compiles"; else bad "Python syntax errors"; fi

if [ -z "${SKIP_APT_CHECK:-}" ] && command -v apt-cache >/dev/null && grep -q trixie /etc/os-release 2>/dev/null; then
    if "$ROOT/scripts/check-package-lists.sh" >/tmp/mos-pkgcheck.log 2>&1; then
        pass "package lists: $(tail -1 /tmp/mos-pkgcheck.log)"
    else
        cat /tmp/mos-pkgcheck.log
        bad "package lists reference unavailable packages"
    fi
else
    echo "  SKIP package availability (not on Debian 13 or SKIP_APT_CHECK set)"
fi

[ "$fail" -eq 0 ] && echo "Validation passed." || echo "Validation FAILED."
exit "$fail"
