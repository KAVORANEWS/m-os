# M OS architecture

M OS is a **Debian-based Linux distribution**. It does not fork the kernel or
the desktop; it puts together maintained open-source components and adds its own
identity, defaults, and system applications.

```
┌──────────────────────────────────────────────────────────────────────┐
│ M OS applications (Python 3 + Qt 6 / PyQt6)          package: mos-apps │
│  Welcome · Control Center · Update Center · System Monitor · About     │
│  mos-desktopctl (layout/theme/accent/profile engine)                   │
│  privileged helpers via pkexec + polkit (fixed verbs only)             │
├──────────────────────────────────────────────────────────────────────┤
│ M OS identity & defaults            packages: mos-branding, mos-desktop-config │
│  os-release (dpkg-divert) · Plasma global themes Modern/Classic        │
│  M OS Dark/Light colour schemes · wallpapers · Plymouth · SDDM         │
│  Calamares branding · sysctl hardening · ufw first-boot · zram         │
├──────────────────────────────────────────────────────────────────────┤
│ KDE Plasma 6 (Debian packages): KWin (Wayland + X11), plasmashell,     │
│ Dolphin, Konsole, Discover, System Settings modules, SDDM              │
├──────────────────────────────────────────────────────────────────────┤
│ Debian 13 "trixie" amd64: linux-image-amd64, systemd, APT, AppArmor,   │
│ firmware (main + non-free-firmware), PipeWire, NetworkManager          │
├──────────────────────────────────────────────────────────────────────┤
│ Boot: GRUB (BIOS + UEFI, signed shim/GRUB) → live-boot → squashfs      │
│ Installer: Calamares 3.3 (Debian package + calamares-settings-debian)  │
└──────────────────────────────────────────────────────────────────────┘
```

## Architecture decisions

| # | Decision | Reason |
|---|---|---|
| AD-1 | Debian 13 stable as the base | Long-term security support, signed archive, huge package set, official `live-build` tooling. |
| AD-2 | KDE Plasma 6 | Supports both a dock layout (Modern) and a taskbar layout (Classic) with a scriptable layout API. Wayland by default with an X11 fallback session. Runs well on Intel HD 530-class hardware. |
| AD-3 | `live-build` for ISO generation | Debian's official live image tool. Reproducible config in git (`build/live-build`). |
| AD-4 | Calamares from Debian packages | Maintained upstream (development moved from GitHub to Codeberg in 2025; the GitHub repo is archived). The Debian package `calamares` 3.3.x with `calamares-settings-debian` has Debian-specific bootloader and offline-repository helpers. M OS only changes branding and hardening through a build hook. |
| AD-5 | Offline bootloader pool on the ISO | `calamares-settings-debian` installs `grub-efi`/`grub-pc` with APT from the live medium. `80-mos-bootloader-efi`, `81-mos-bootloader-bios` and `82-mos-encryption` (`.list.binary`) put these packages (plus shim-signed and LUKS tools) in the ISO pool as separate apt transactions, because grub-pc and grub-efi-amd64 conflict, so installation works without internet. |
| AD-6 | M OS customisation as Debian packages | Branding, defaults and apps are versioned `.deb` packages, so installed systems receive them as normal package updates. They can also be installed on plain Debian 13. |
| AD-7 | System-wide defaults through `/etc/xdg` | Users can still override everything. No files owned by other packages are edited, except `/usr/lib/os-release`, which is diverted with `dpkg-divert` (reversible). |
| AD-8 | `desktop-base` conflicts | Debian's branding package changes the About logo, GRUB/Plymouth themes and `XDG_CONFIG_DIRS`. `mos-desktop-config` declares `Conflicts: desktop-base`, and a build hook makes sure it is removed. Side effect: metapackages that *depend* on desktop-base (e.g. `task-desktop`) can't be installed. |
| AD-9 | Control Center delegates hardware settings to KDE modules (KCMs) | Re-implementing display/network/audio configuration would be less reliable. M OS-specific settings are native. KCM buttons only appear enabled when the module is installed. |
| AD-10 | Privileged actions via pkexec helpers with fixed verbs | `mos-update-helper refresh/upgrade/repair` and `mos-firewall-helper status/enable/disable`. They accept no free-form input, use polkit `auth_admin_keep`, and use `apt-get upgrade --with-new-pkgs` (never removes packages). |
| AD-11 | Python + PyQt6 for M OS apps | Ships in Debian main, needs no compilation, is easy to test. Parsers are Qt-free and unit-tested. |
| AD-12 | zram + performance profile for 4–8 GB RAM | `systemd-zram-generator` (zstd, ≤4 GiB) and `mos-desktopctl profile performance`, which cuts animations, blur/translucency, file indexing and the update notifier. |

## Build pipeline

`scripts/build-iso.sh` runs these steps:

1. Check dependencies.
2. Validate the configuration (`validate-build.sh`).
3. Build the packages (`build-packages.sh`).
4. Copy `build/live-build` to `build/work/live`.
5. Run `lb config` and `lb build`.
6. Run the in-image verification hook (`9100-mos-verify`).
7. Verify the ISO (`verify-iso.sh`).
8. Generate `SHA256SUMS` and `BUILD-REPORT.md`.

CI (`.github/workflows/build-iso.yml`) runs the same script in a privileged
`debian:trixie` container. It then boot-tests the ISO under QEMU/KVM with
OVMF (UEFI) and SeaBIOS using `tests/boot/qemu_boot_test.py`.

## Repository map

| Path | Contents |
|---|---|
| `branding/` | SVG sources, render script outputs (`rendered/`), licence |
| `build/live-build/` | `auto/`, package lists, hooks, GRUB live menu |
| `packages/` | Debian packaging for mos-branding, mos-desktop-config, mos-apps |
| `applications/` | Python package `mos` plus launchers, helpers, polkit policy |
| `desktop/themes/` | Colour scheme generator |
| `scripts/` | build, validate, verify, VM runner, branding render |
| `tests/` | unit, integration (GUI), packaging, boot (QEMU) |
| `docs/` | This documentation |
