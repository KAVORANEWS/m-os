# Installing M OS

> **M OS 0.1 is a developer preview.** Try it in a virtual machine or the
> live session first. **Back up all important data before you install on a
> real computer.** The installer can erase disks if you tell it to.

## 1. Download and verify

Download `M-OS-<version>-amd64.iso` and `SHA256SUMS` from the
[Releases page](https://github.com/dotsoftwarelk/m-os/releases).

If the release has `*.part0`, `*.part1`, … files (GitHub limits single files
to 2 GiB), join them first:

```bash
cat M-OS-0.1.0-amd64.iso.part* > M-OS-0.1.0-amd64.iso
```

Then verify:

```bash
sha256sum -c SHA256SUMS --ignore-missing
```

On Windows (PowerShell): `Get-FileHash .\M-OS-0.1.0-amd64.iso -Algorithm SHA256`.
Compare the result with the value in `SHA256SUMS`.

## 2. Try it in a virtual machine (recommended first)

**QEMU (Linux):**

```bash
./scripts/run-vm.sh dist/M-OS-0.1.0-amd64.iso                 # UEFI
./scripts/run-vm.sh --bios dist/M-OS-0.1.0-amd64.iso          # legacy BIOS
./scripts/run-vm.sh --disk 30G dist/M-OS-0.1.0-amd64.iso      # with a disposable disk for installing
```

**VirtualBox (Windows/macOS/Linux):**

1. Create a new VM with type Linux, version Debian (64-bit).
2. Give it 4096 MB RAM, 2+ CPUs, and a 30 GB disk.
3. Under Display, choose the **VMSVGA** controller with 128 MB video memory.
4. Optional: enable EFI under System.
5. Attach the ISO as an optical drive and start the VM.

## 3. Create a bootable USB drive

You need a USB stick of 4 GB or more. **Everything on it will be erased.**

* **Windows:** [Rufus](https://rufus.ie) — choose the ISO and use "DD Image" mode if asked. Or use balenaEtcher.
* **Linux/macOS:** balenaEtcher, or:
  ```bash
  lsblk                                   # find the USB device, e.g. /dev/sdX — double-check!
  sudo dd if=M-OS-0.1.0-amd64.iso of=/dev/sdX bs=4M status=progress oflag=sync
  ```

## 4. Boot the live system

1. Plug in the USB drive. Open the boot menu (often F12, F11, F8 or Esc) and pick the USB drive.
   * For the Intel i5-6500 target machine (Skylake desktop boards), F12 or F8 usually opens the boot menu.
2. In the M OS boot menu, choose **Try or Install M OS**. If the screen stays black, pick **safe graphics**.
3. The live desktop starts as user `mos` (password `live`). M OS Welcome opens automatically.

## 5. Install

Click **Install M OS** (desktop icon, M OS Welcome, or the application launcher) and follow these steps:

1. **Language** and **location/time zone**.
2. **Keyboard** layout. You can add Sinhala input later with Ctrl+Space.
3. **Partitions:**
   * *Erase disk* — **deletes everything on the selected disk.**
   * *Install alongside* — shrinks an existing system (for example Windows) to make room. Back up first. In Windows, turn off BitLocker and Fast Startup beforehand, and run `chkdsk`.
   * *Manual partitioning* — for advanced users. UEFI needs an EFI system partition (FAT32, ≥300 MB, mounted at `/boot/efi`).
   * Optional: tick *Encrypt system* (LUKS). Not yet tested by M OS; see `security.md`.
4. **Users:** your name, username, and password (at least 8 characters).
5. **Summary:** check every change. **Nothing is written to disk until you confirm here.**
6. Wait for the installation to finish. Then restart and remove the USB drive.

## 6. After installation

* Open **M OS Update Center** and install updates.
* Change the layout, theme, and performance profile in **M OS Control Center → Personalization**.
* For 4–8 GB RAM computers, choose **M OS Performance**.

## Known installer limitations

* The unattended / automated install path has not been tested yet (see `known-issues.md`).
* Dual-boot with Windows has not been tested on real hardware.
* Btrfs subvolume layouts and LVM come from Calamares defaults and are untested.
