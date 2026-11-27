# Changelog

## 0.1.0 — developer preview (unreleased)

### Added
- Debian 13 "trixie" live-build configuration (amd64, GRUB BIOS + UEFI, signed shim/GRUB, xz squashfs).
- KDE Plasma 6 desktop with M OS defaults. Global themes **M OS Modern** (top bar + dock) and **M OS Classic** (taskbar).
- M OS Dark / Light colour schemes, Aurora wallpapers (light/dark), logo, app icons, GRUB menu theme, Plymouth splash, Plasma splash, SDDM background.
- M OS applications: Welcome, Control Center, Update Center, System Monitor, About, `mos-desktopctl`.
- Calamares installer with M OS branding, offline bootloader package pool, 8-character minimum password.
- Security baseline: ufw (deny incoming) on first boot, AppArmor profiles, sysctl hardening, auto screen lock, no SSH, no telemetry.
- zram swap and the M OS Performance profile for 4–8 GB RAM.
- English + Sinhala: fonts, `si_LK` locale, Wijesekara/Singlish input via Fcitx 5, partial Sinhala UI strings.
- Build pipeline (`build-iso.sh`, `validate-build.sh`, `verify-iso.sh`), unit/GUI/packaging tests, QEMU boot test, GitHub Actions (test, build + boot test, release).
