# Testing M OS

## Automated tests

| Level | Command | Runs in CI |
|---|---|---|
| Static validation | `./scripts/validate-build.sh` | `Test` |
| Unit tests | `python3 -m unittest discover -s tests/unit -v` | `Test` |
| Package tests | `./scripts/build-packages.sh && tests/packaging/test-packages.sh dist/packages` | `Test` |
| GUI smoke test | `QT_QPA_PLATFORM=offscreen python3 tests/integration/gui_smoke.py build/screenshots` | `Test` (screenshots uploaded) |
| ISO build + in-image verification | `sudo ./scripts/build-iso.sh` (hook `9100-mos-verify`) | `Build ISO` |
| ISO structure | `./scripts/verify-iso.sh dist/M-OS-*.iso` | `Build ISO` |
| Live boot test, BIOS + UEFI | `tests/boot/boot-test.sh dist/M-OS-*.iso` | `Build ISO` (KVM) |

### What the boot test checks

`tests/boot/qemu_boot_test.py` starts QEMU with OVMF or SeaBIOS. It selects
the default GRUB entry and adds a serial console. Then it logs in as `mos`
over the serial line and checks these things inside the running system:

* os-release
* firmware mode
* SDDM, KWin, and plasmashell running
* the M OS apps installed
* ufw active
* AppArmor enabled
* no listening TCP services, no SSH
* zram swap
* Sinhala font, locale, and input method
* failed systemd units
* Calamares branding

It also takes screenshots of the GRUB menu and the desktop. The results go to
`report.md` / `report.json` in the output directory.

## Manual installer test (disposable virtual disk only)

**Never run installer tests against a physical disk.**

```bash
./scripts/run-vm.sh --disk 30G dist/M-OS-0.1.0-amd64.iso          # UEFI
./scripts/run-vm.sh --bios --disk 30G dist/M-OS-0.1.0-amd64.iso   # BIOS
```

1. Boot **Try or Install M OS** and open **Install M OS**.
2. Choose English (or සිංහල) and the Asia/Colombo time zone. Choose a keyboard layout.
3. Pick **Erase disk** on the 30 GB virtual disk (`build/vm/disk.qcow2`). Choose ext4.
4. Create user `tester`. Check that a 6-character password is rejected and an 8-character one is accepted.
5. Install, then reboot. Boot the installed system with `./scripts/run-vm.sh --boot-disk [--bios]`.
6. Check:
   * GRUB shows M OS
   * SDDM logs in
   * M OS Welcome appears
   * `sudo ufw status` is active
   * `cat /etc/os-release` shows M OS
   * `dpkg -l | grep live-boot` is empty (live packages removed)
   * Update Center check works with network
7. Record the result in `tests/reports/installer-<date>.md`.

## Performance measurement (planned procedure)

On the target machine (i5-6500 / 8 GB / HD 530), record:

* boot time: `systemd-analyze`, `systemd-analyze blame | head`
* idle RAM after login: `free -m`, 2 minutes after login
* `plasmashell` + `kwin_wayland` RSS
* for Balanced and Performance profiles

No such measurements have been published yet.
