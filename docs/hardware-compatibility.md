# Hardware compatibility

Only results that were actually measured are listed here. "Expected" means
supported by the Debian 13 kernel/firmware packages in the image but **not
tested by M OS**.

## Tested configurations

| Configuration | Firmware | Result | Date / source |
|---|---|---|---|
| QEMU/KVM q35, virtio-vga, 4 GB RAM, 2 vCPU | OVMF UEFI | see `tests/reports/` | CI boot test |
| QEMU/KVM i440fx, virtio-vga, 4 GB RAM, 2 vCPU | SeaBIOS | see `tests/reports/` | CI boot test |

## Primary target — not yet tested

| Component | Model | Driver in M OS | Status |
|---|---|---|---|
| CPU | Intel Core i5-6500 (Skylake, 4C/4T) | kernel + `intel-microcode` | expected |
| Graphics | Intel HD Graphics 530 | `i915` (kernel), Mesa iris, VA-API `intel-media-va-driver` | expected |
| RAM | 8 GB DDR4 | — | M OS Balanced recommended; Performance optional |
| Storage | SATA SSD | AHCI | expected |
| Audio | Realtek HDA (typical on H110/B150 boards) | `snd_hda_intel`, PipeWire | expected |

Please submit a **Hardware compatibility report** issue with your results.

## Firmware and drivers in the image

`firmware-linux-free`, `firmware-misc-nonfree`, `firmware-amd-graphics`,
`firmware-intel-graphics`, `firmware-intel-sound`, `firmware-sof-signed`,
`firmware-iwlwifi`, `firmware-realtek`, `firmware-atheros`,
`firmware-brcm80211`, `firmware-mediatek`, `intel-microcode`,
`amd64-microcode`, Mesa (OpenGL/Vulkan/VA-API), `xserver-xorg-video-all`.

NVIDIA: the open `nouveau` driver is used. The proprietary NVIDIA driver is
not included (it's non-free and needs DKMS/kernel-module signing). It can be
installed after installation from Debian `non-free`. Untested.
