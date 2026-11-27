#!/usr/bin/env bash
# Boot an M OS ISO in QEMU for manual testing. Never touches physical disks.
#
#   ./scripts/run-vm.sh dist/M-OS-0.1.0-amd64.iso            # UEFI, 4 GB RAM
#   ./scripts/run-vm.sh --bios dist/M-OS-0.1.0-amd64.iso     # legacy BIOS
#   ./scripts/run-vm.sh --disk 30G dist/M-OS-0.1.0-amd64.iso # + disposable virtual disk for install tests
#   ./scripts/run-vm.sh --boot-disk build/vm/mos-test-disk.qcow2   # boot an installed virtual disk
set -euo pipefail

FIRMWARE=uefi
DISK_SIZE=""
BOOT_DISK=""
MEM="${MOS_VM_MEM:-4096}"
CPUS="${MOS_VM_CPUS:-2}"
ISO=""
while [ $# -gt 0 ]; do
    case "$1" in
        --bios) FIRMWARE=bios ;;
        --uefi) FIRMWARE=uefi ;;
        --disk) DISK_SIZE="$2"; shift ;;
        --boot-disk) BOOT_DISK="$2"; shift ;;
        --mem) MEM="$2"; shift ;;
        -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
        *) ISO="$1" ;;
    esac
    shift
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VMDIR="$ROOT/build/vm"
mkdir -p "$VMDIR"
# shellcheck disable=SC2054  # commas are part of QEMU option values
args=(-name "M OS test VM" -m "$MEM" -smp "$CPUS" -device virtio-vga -display "${MOS_VM_DISPLAY:-gtk}"
      -device qemu-xhci -device usb-tablet -nic user,model=virtio-net-pci
      -audiodev none,id=snd0 -device intel-hda -device hda-duplex,audiodev=snd0)

if [ -e /dev/kvm ] && [ -w /dev/kvm ]; then
    args+=(-enable-kvm -cpu host)
else
    echo "warning: KVM not available — the VM will be very slow" >&2
fi

if [ "$FIRMWARE" = uefi ]; then
    CODE=/usr/share/OVMF/OVMF_CODE_4M.fd
    VARS_TEMPLATE=/usr/share/OVMF/OVMF_VARS_4M.fd
    [ -f "$CODE" ] || { echo "OVMF not found; apt install ovmf" >&2; exit 1; }
    cp -n "$VARS_TEMPLATE" "$VMDIR/OVMF_VARS.fd" 2>/dev/null || true
    args+=(-machine q35 -drive "if=pflash,format=raw,readonly=on,file=$CODE"
           -drive "if=pflash,format=raw,file=$VMDIR/OVMF_VARS.fd")
else
    args+=(-machine pc)
fi

if [ -n "$DISK_SIZE" ]; then
    DISK="$VMDIR/mos-test-disk.qcow2"
    [ -f "$DISK" ] || qemu-img create -f qcow2 "$DISK" "$DISK_SIZE"
    args+=(-drive "file=$DISK,if=virtio,format=qcow2")
fi
if [ -n "$BOOT_DISK" ]; then
    args+=(-drive "file=$BOOT_DISK,if=virtio,format=qcow2")
fi
if [ -n "$ISO" ]; then
    [ -f "$ISO" ] || { echo "ISO not found: $ISO" >&2; exit 1; }
    args+=(-drive "file=$ISO,media=cdrom,readonly=on" -boot order=dc)
fi

exec qemu-system-x86_64 "${args[@]}"
