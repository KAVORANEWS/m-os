# M OS developer guide

## Requirements

* A Debian 13 (trixie) host or container. Other hosts are untested.
* About 25 GB of free disk space and 4 GB+ RAM. More CPU cores make squashfs compression faster.
* Packages:

```bash
sudo apt install live-build debootstrap xorriso squashfs-tools mtools dosfstools apt-utils \
  grub-pc-bin grub-efi-amd64-bin dpkg-dev debhelper dh-python lintian fakeroot rsync \
  shellcheck python3-pyqt6 python3-pyflakes desktop-file-utils librsvg2-bin imagemagick \
  fonts-inter qemu-system-x86 qemu-utils ovmf
```

Enable `contrib non-free-firmware` in your APT sources so the package-availability check sees firmware packages.

## Everyday commands

| Task | Command |
|---|---|
| Validate everything (fast) | `./scripts/validate-build.sh` |
| Unit tests | `python3 -m unittest discover -s tests/unit -v` |
| GUI smoke test + screenshots | `QT_QPA_PLATFORM=offscreen python3 tests/integration/gui_smoke.py build/screenshots` |
| Run an app from source | `PYTHONPATH=applications/python python3 -m mos.control_center` |
| Re-render artwork after editing SVGs | `./scripts/render-branding.sh` |
| Build .deb packages | `./scripts/build-packages.sh` then `tests/packaging/test-packages.sh dist/packages` |
| Build the ISO | `sudo ./scripts/build-iso.sh` (≈45–90 min) |
| Verify an ISO | `./scripts/verify-iso.sh dist/M-OS-*.iso` |
| Automated boot test | `tests/boot/boot-test.sh dist/M-OS-*.iso` (needs KVM to run fast) |
| Interactive VM | `./scripts/run-vm.sh [--bios] [--disk 30G] dist/M-OS-*.iso` |

Use a closer mirror with `MOS_MIRROR=http://<mirror>/debian/ sudo -E ./scripts/build-iso.sh`.

## Where to change things

| I want to… | Edit |
|---|---|
| Add or remove software | `build/live-build/config/package-lists/*.list.chroot` |
| Change default desktop settings | `packages/mos-desktop-config/files/etc/xdg/*` |
| Change panel layouts | `packages/mos-branding/files/usr/share/plasma/look-and-feel/org.mos.*/contents/layouts/*.js` |
| Change colours | `desktop/themes/generate_colorschemes.py` |
| Change the GRUB live menu | `build/live-build/config/bootloaders/grub-pc/` |
| Change the installer | `packages/mos-branding/files/etc/calamares/branding/mos/` and hook `0200-mos-installer` |
| Run something inside the image | add `build/live-build/config/hooks/normal/NNNN-name.hook.chroot` |

## Rules

* Build real functions. Don't add buttons that do nothing. If something isn't available, disable it and say why.
* Keep parsing and logic in Qt-free modules (`sysinfo`, `aptparse`, `desktopctl`) and add unit tests.
* Privileged operations go only through a fixed-verb helper with a polkit action.
* Never edit files owned by other packages from maintainer scripts. Use `/etc/xdg`, `.d` directories, or `dpkg-divert`.
* In documentation, keep **implemented**, **tested**, and **planned** separate.
* Run destructive installer tests only against disposable virtual disks (`run-vm.sh --disk`).

## Branching and releases

* Work on `feature/<topic>` branches and open pull requests to `main`.
* `Test` runs on every push and PR. `Build ISO` runs on `main` changes and on demand (Actions → Build ISO → Run workflow, with the *publish* option).
* Release: bump `VERSION` and the `debian/changelog` files, then push tag `v<version>`. The `Release` workflow builds, boot-tests, and publishes.

## Lintian

Accepted tags are listed in `packages/lintian-overrides.txt`. Any lintian error fails `tests/packaging/test-packages.sh`.
