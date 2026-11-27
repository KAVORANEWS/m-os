#!/usr/bin/env bash
# Verify the structure and contents of an M OS ISO image.
#   ./scripts/verify-iso.sh dist/M-OS-0.1.0-amd64.iso
set -uo pipefail

ISO="${1:?usage: verify-iso.sh <iso>}"
[ -s "$ISO" ] || { echo "ISO not found: $ISO" >&2; exit 1; }
command -v xorriso >/dev/null || { echo "xorriso required" >&2; exit 1; }

fail=0
pass() { echo "PASS  $*"; }
bad()  { echo "FAIL  $*"; fail=1; }
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

size=$(stat -c %s "$ISO")
echo "ISO: $(basename "$ISO") — $(numfmt --to=iec-i --suffix=B "$size")"
[ "$size" -lt $((4 * 1024 * 1024 * 1024)) ] && pass "size below 4 GiB (fits FAT32 USB tools and DVD-DL)" || bad "ISO larger than 4 GiB"

xorriso -indev "$ISO" -find / -type f 2>/dev/null > "$TMP/files"
need() { grep -qE "$1" "$TMP/files" && pass "$2" || bad "$2 (pattern $1)"; }
need "^'?/live/vmlinuz" "live kernel present"
need "^'?/live/initrd" "live initramfs present"
need "^'?/live/filesystem.squashfs" "root filesystem (squashfs) present"
need "^'?/boot/grub/grub.cfg" "GRUB configuration present"
need "^'?/EFI/boot/bootx64.efi" "UEFI boot loader (EFI/boot/bootx64.efi) present"
need "^'?/boot/grub/i386-pc/" "BIOS GRUB modules present"
need "^'?/pool/.*/grub-efi-amd64-signed_" "signed GRUB in installer pool (offline UEFI install)"
need "^'?/pool/.*/grub-pc_" "grub-pc in installer pool (offline BIOS install)"
need "^'?/pool/.*/shim-signed_" "shim in installer pool (Secure Boot chain)"

xorriso -indev "$ISO" -report_el_torito plain 2>/dev/null > "$TMP/eltorito"
grep -qi "BIOS" "$TMP/eltorito" && pass "El Torito BIOS boot entry" || bad "no El Torito BIOS boot entry"
grep -qi "UEFI" "$TMP/eltorito" && pass "El Torito UEFI boot entry" || bad "no El Torito UEFI boot entry"

xorriso -osirrox on -indev "$ISO" -extract /boot/grub/grub.cfg "$TMP/grub.cfg" >/dev/null 2>&1
grep -q "Try or Install M OS" "$TMP/grub.cfg" && pass "GRUB menu is M OS branded" || bad "GRUB menu not branded"
grep -qE "@[A-Z_]+@" "$TMP/grub.cfg" && bad "unsubstituted placeholders in grub.cfg" || pass "GRUB placeholders substituted"

if command -v unsquashfs >/dev/null; then
    xorriso -osirrox on -indev "$ISO" -extract /live/filesystem.squashfs "$TMP/fs.squashfs" >/dev/null 2>&1
    unsquashfs -l "$TMP/fs.squashfs" 2>/dev/null | sed 's|^squashfs-root||' > "$TMP/sqlist"
    for f in /usr/bin/mos-welcome /usr/bin/mos-control-center /usr/bin/mos-update-center \
             /usr/bin/mos-system-monitor /usr/bin/mos-about /usr/bin/mos-desktopctl \
             /usr/bin/plasmashell /usr/bin/sddm /usr/bin/calamares /usr/sbin/ufw /usr/bin/dolphin \
             /usr/bin/konsole /usr/bin/firefox-esr /usr/share/wallpapers/MOS/metadata.json \
             /etc/calamares/branding/mos/branding.desc /usr/share/plymouth/themes/mos/mos.plymouth; do
        grep -qx "$f" "$TMP/sqlist" && pass "image contains $f" || bad "image missing $f"
    done
    unsquashfs -d "$TMP/x" "$TMP/fs.squashfs" usr/lib/os-release etc/calamares/settings.conf >/dev/null 2>&1
    grep -q '^NAME="M OS"' "$TMP/x/usr/lib/os-release" 2>/dev/null && pass "os-release identifies M OS" || bad "os-release is not M OS"
    grep -q '^branding: mos' "$TMP/x/etc/calamares/settings.conf" 2>/dev/null && pass "installer uses M OS branding" || bad "installer branding not applied"
    grep -qx "/usr/share/desktop-base" "$TMP/sqlist" && bad "Debian desktop-base still installed" || pass "desktop-base removed"
    echo "squashfs: $(numfmt --to=iec-i --suffix=B "$(stat -c %s "$TMP/fs.squashfs")"), $(wc -l < "$TMP/sqlist") entries"
fi

[ "$fail" -eq 0 ] && echo "ISO verification PASSED" || echo "ISO verification FAILED"
exit "$fail"
