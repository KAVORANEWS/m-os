#!/bin/sh
# Run the automated QEMU boot test for BIOS and UEFI.
#   tests/boot/boot-test.sh dist/M-OS-0.1.0-amd64.iso [outdir]
set -eu
ISO="${1:?usage: boot-test.sh <iso> [outdir]}"
OUT="${2:-build/boot-test}"
HERE="$(dirname "$0")"
rc=0
for fw in uefi bios; do
    python3 "$HERE/qemu_boot_test.py" --iso "$ISO" --firmware "$fw" --out "$OUT/$fw" || rc=1
done
exit "$rc"
